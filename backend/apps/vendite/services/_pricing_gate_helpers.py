# ------------------------------------------------------------
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Building block condiviso per i gate del sistema "autorizzazioni
#        prezzi" (L1 permesso + L2 soglia variazione + workflow L3 escalation).
#        Centralizza la logica usata da `preventivi_service` (gate riga) e
#        `contratti_service` (gate variazione globale e — in futuro — gate
#        riga sui contratti).
#
#        Storia:
#        - Sprint D (2026-04-??): gate L1+L2 nascono in `preventivi_service`
#          come funzioni private `_check_permesso_override_prezzo` e
#          `_check_limite_variazione_prezzo`.
#        - Sprint E (2026-04-??): workflow L3 con flag `accept_for_approval`.
#        - 2026-05-15 (refactor modalita contratti §3-bis-E): introdotto
#          `_check_limite_variazione_globale` su contratti — duplicava ~80%
#          della logica preventivi.
#        - 2026-05-15 (questo modulo): estrazione in BB condiviso pre-
#          implementazione 3 gate sulle righe contratto.
#
#        Le funzioni sono **pubbliche** del modulo: nominate senza underscore
#        prefix (cross-service BB). I caller di preventivi/contratti le
#        importano e le chiamano direttamente.
# ------------------------------------------------------------

from __future__ import annotations

from collections.abc import Mapping
from decimal import ROUND_HALF_UP, Decimal, InvalidOperation
from typing import Any, Callable

from django.contrib.auth import get_user_model
from django.db import transaction

from apps.anagrafiche.db.billing_account_repository import BillingAccountRepository
from apps.core.services.error_manager import ErrorManager
from apps.core.services.parameter_service import ParameterService
from apps.core.services.payload_helpers import PayloadValidator
from apps.core.services.permissions_resolver import PermissionResolver
from apps.vendite.services._approvazioni_prezzo_constants import AZIONE_OVERRIDE_PREZZO
from apps.vendite.services.pricing_service import (
    PARAM_MAX_MAGGIORAZIONE_PCT,
    PARAM_MAX_SCONTO_PCT,
)

# Il codice azione del gate L1 (override manuale prezzo) sta nel modulo delle
# costanti delle approvazioni, accanto a `AZIONE_APPROVA_PREZZO` (regola del 2,
# ok Tid 2026-11-14: qui ce n'era una copia). Quel modulo non importa niente,
# quindi non chiude cicli: la ragione della copia non c'e' piu'.

# L'origine di un prezzo scritto a mano: la scrivono il gate prezzi di riga
# (qui) e la PATCH dei componenti (`_componenti_service_helpers`), una sede.
# ⚠️ Sta QUI e non nel modulo dei componenti: quello importa il gate L1 da
#    questo modulo, e la costante nell'altro verso faceva un ciclo.
ORIGINE_PREZZO_MANUALE = "MANUALE"


# Scopo: Guard generico su uom_id intero positivo, riusato dagli entry point
#        pricing module-level (`suggerisci_prezzo_riga` preventivi,
#        `contratti_suggerisci_prezzo_riga` contratti). Solleva ServiceError
#        col codice di dominio fornito dal caller — il messaggio e' fisso
#        ("uom_id obbligatorio (intero positivo).") per coerenza UX.
def guard_uom_id_positive(
    uom_id: Any, *, error_code: str, function_name: str,
) -> None:
    ErrorManager.require(
        uom_id is not None and isinstance(uom_id, int) and uom_id > 0,
        code=error_code,
        message="uom_id obbligatorio (intero positivo).",
        function_name=function_name,
    )


# Scopo: Gate L1 — verifica che l'operatore abbia l'azione di processo per
#        override manuale del prezzo. Bypass per superuser. Se auth_user_id
#        None (chiamata non autenticata, es. script interni) -> blocca
#        conservativamente.
def check_permesso_override_prezzo(
    auth_user_id: int | None, *, function_name: str,
) -> None:
    ErrorManager.require(
        auth_user_id is not None,
        code="E_PRICING_OVERRIDE_NON_AUTORIZZATO",
        message="Override prezzo non autorizzato.",
        detail="Chiamata senza contesto utente — override bloccato conservativamente.",
        function_name=function_name,
    )
    assert auth_user_id is not None
    user_model = get_user_model()
    try:
        user = user_model.objects.get(pk=auth_user_id)
    except user_model.DoesNotExist:
        ErrorManager.raise_error(
            code="E_PRICING_OVERRIDE_NON_AUTORIZZATO",
            message="Override prezzo non autorizzato.",
            detail="Utente non trovato.",
            function_name=function_name,
        )
    if getattr(user, "is_superuser", False):
        return
    abilitato = PermissionResolver.check_azione(user, AZIONE_OVERRIDE_PREZZO)
    ErrorManager.require(
        abilitato,
        code="E_PRICING_OVERRIDE_NON_AUTORIZZATO",
        message="Modifica manuale del prezzo non autorizzata.",
        detail=(
            "Usa il prezzo suggerito dal listino o richiedi l'autorizzazione "
            "'prezzo_override_manuale' al tuo responsabile."
        ),
        function_name=function_name,
    )


# Scopo: Gate L1 sugli override manuali dei PREZZI dei COMPONENTI BoM passati
#        nel payload (`componenti_overrides`). Estratto da preventivi_service
#        (era il privato `_validate_componenti_overrides_authorization`) e
#        promosso a BB condiviso (regola del 2): usato da preventivi, contratti
#        e offerte. Se il payload non porta override → no-op. Altrimenti
#        richiede l'azione di processo `prezzo_override_manuale`, come il gate
#        L1 sul prezzo riga (`check_permesso_override_prezzo`).
#
# ⛔ Il gate L1 e' UNO: questa funzione delega a `check_permesso_override_prezzo`
#    (2026-10-20, regola del 2). Fino a quel giorno ne era una seconda copia,
#    col messaggio suo e il superuser trattato in un altro modo: due risposte
#    alla stessa domanda «puo' scrivere un prezzo a mano?».
def validate_componenti_overrides_authorization(
    payload: dict[str, Any],
    auth_user_id: int | None,
    *,
    function_name: str,
) -> None:
    if not payload.get("componenti_overrides"):
        return
    check_permesso_override_prezzo(auth_user_id, function_name=function_name)


# Scopo: Helper privato. Risolve la soglia % di variazione applicabile a
#        (utente, BA) attraverso la cascata user → categoria_cliente → group
#        → emittente → default. Centralizza il pattern usato da entrambi i
#        gate L2 (riga e variazione globale). Il lookup BA→categoria avviene
#        solo se `ba_id` e' fornito.
#
#        Restituisce la soglia come Decimal. Solleva
#        E_PARAMETER_VALIDATION se il parametro DB e' malformato (stato
#        inconsistente che l'admin deve correggere).
def _resolve_soglia_variazione_pct(
    *,
    auth_user_id: int,
    param_code: str,
    ba_id: int | None,
) -> Decimal:
    param_service = ParameterService()
    emittente_fiscale_id = param_service.get_emittente_fiscale_id_for_user(
        auth_user_id,
    )
    categoria_cliente_id: int | None = None
    if ba_id is not None:
        categoria_cliente_id = BillingAccountRepository().get_categoria_cliente_id(
            int(ba_id),
        )
    return param_service.get_parameter_decimal(
        param_code,
        django_user_id=auth_user_id,
        emittente_fiscale_id=emittente_fiscale_id,
        categoria_cliente_id=categoria_cliente_id,
    )


# Scopo: Helper privato. Restituisce l'utente Django dato `auth_user_id` o
#        None se non trovato (chiamata non autenticata / utente cancellato).
def _get_user_or_none(auth_user_id: int):
    user_model = get_user_model()
    try:
        return user_model.objects.get(pk=auth_user_id)
    except user_model.DoesNotExist:
        return None


# Scopo: Gate L2 sulla variazione % fra prezzo manuale e prezzo risolto
#        dal resolver (caso classico riga preventivo/contratto). Se sconto
#        (delta < 0) confronta con VENDITE_MAX_SCONTO_PCT; se maggiorazione
#        (delta > 0) con VENDITE_MAX_MAGGIORAZIONE_PCT.
#        Skip se prezzo_resolver e' None o 0 (non calcolabile / safe-fail).
#        Superuser bypass. Parametri risolti via cascata estesa user →
#        categoria_cliente → group → emittente → default.
#
#        `ba_id` opzionale: se fornito alimenta il livello categoria_cliente.
#        Lookup DB avviene DOPO gli early-return per non sprecare round-trip.
#
#        `accept_for_approval`: workflow L3 (Sprint E). Se True, una violazione
#        non solleva ma ritorna il dict di violazione — il caller orchestrera'
#        la creazione della pratica di approvazione.
#
#        Restituisce:
#          - None se variazione entro limite (L2 OK)
#          - dict {tipo_violazione, variazione_abs_pct, limite_pct, kind_label}
#            se violazione + accept_for_approval=True
#
#        Solleva ServiceError L2 (E_PRICING_SCONTO_ECCESSIVO /
#        E_PRICING_MAGGIORAZIONE_ECCESSIVA, retryable=True) se violazione +
#        accept_for_approval=False.
def check_limite_variazione_prezzo(
    *,
    auth_user_id: int | None,
    prezzo_resolver,  # Decimal | None
    prezzo_manuale,   # Decimal
    function_name: str,
    accept_for_approval: bool = False,
    ba_id: int | None = None,
) -> dict[str, Any] | None:
    if prezzo_resolver is None or prezzo_resolver == 0:
        return None  # Nessun riferimento per calcolare la percentuale.

    if auth_user_id is None:
        return None  # L1 ha gia' bloccato; unreachable difensivo.

    user = _get_user_or_none(auth_user_id)
    if user is None:
        return None  # L1 avrebbe gia' bloccato.
    if getattr(user, "is_superuser", False):
        return None

    delta = prezzo_manuale - prezzo_resolver
    if delta == 0:
        return None  # Edge case: L1 avrebbe gia' fatto early-return.

    delta_pct = (delta / prezzo_resolver) * Decimal("100")
    is_sconto = delta_pct < 0
    param_code = PARAM_MAX_SCONTO_PCT if is_sconto else PARAM_MAX_MAGGIORAZIONE_PCT
    variazione_abs = -delta_pct if is_sconto else delta_pct

    limite = _resolve_soglia_variazione_pct(
        auth_user_id=auth_user_id,
        param_code=param_code,
        ba_id=ba_id,
    )

    if variazione_abs <= limite:
        return None

    return _raise_or_return_violazione_l2(
        is_sconto=is_sconto,
        variazione_abs=variazione_abs,
        limite=limite,
        accept_for_approval=accept_for_approval,
        function_name=function_name,
    )


# Scopo: Gate L2 sulla variazione globale di una testata (es. variazione
#        globale contratto). Il valore stesso e' un delta% (refactor 2026-
#        05-15 §3-bis-E) — niente delta vs resolver. Si applica solo a
#        tipo_variazione = PERCENTUALE; VALORE_FISSO skippa silenziosamente
#        (non comparabile con soglia%, decisione brief DB).
#        Superuser bypass + auth_user_id None bypass.
def check_limite_variazione_globale(
    *,
    auth_user_id: int | None,
    tipo_variazione: str | None,
    valore_variazione,  # Decimal | None
    function_name: str,
    accept_for_approval: bool = False,
    ba_id: int | None = None,
) -> dict[str, Any] | None:
    if valore_variazione is None:
        return None  # Rimozione variazione: niente da gating.
    if tipo_variazione != "PERCENTUALE":
        return None  # VALORE_FISSO non e' un %.
    if auth_user_id is None:
        return None  # Contesto utente richiesto per cascata.

    user = _get_user_or_none(auth_user_id)
    if user is None:
        return None
    if getattr(user, "is_superuser", False):
        return None

    try:
        valore_decimal = Decimal(str(valore_variazione))
    except (InvalidOperation, ValueError, TypeError):
        # Coerce upstream ha gia' bloccato (`PayloadValidator.optional_decimal`
        # in `_build_update_data_testata` di contratti, che rifiuta anche NaN:
        # qui un NaN farebbe sollevare `InvalidOperation` sul `<=` piu' sotto).
        # Eccezioni piu' generiche (`Exception`) maschererebbero bug
        # strutturali: restringiamo.
        return None
    if valore_decimal == 0:
        return None  # 0% = nessuna variazione, niente soglia da controllare.

    is_sconto = valore_decimal < 0
    param_code = PARAM_MAX_SCONTO_PCT if is_sconto else PARAM_MAX_MAGGIORAZIONE_PCT
    variazione_abs = -valore_decimal if is_sconto else valore_decimal

    limite = _resolve_soglia_variazione_pct(
        auth_user_id=auth_user_id,
        param_code=param_code,
        ba_id=ba_id,
    )

    if variazione_abs <= limite:
        return None

    return _raise_or_return_violazione_l2(
        is_sconto=is_sconto,
        variazione_abs=variazione_abs,
        limite=limite,
        accept_for_approval=accept_for_approval,
        function_name=function_name,
    )


# Scopo: Helper finale comune. Una violazione L2 puo' (a) ritornare il dict
#        per il workflow L3 oppure (b) sollevare un ServiceError L2.
#        Centralizzato qui per evitare duplicazione fra i due gate L2.
def _raise_or_return_violazione_l2(
    *,
    is_sconto: bool,
    variazione_abs: Decimal,
    limite: Decimal,
    accept_for_approval: bool,
    function_name: str,
) -> dict[str, Any] | None:
    # Refactor 2026-05-20: messaggio generico "Variazione prezzo" con
    # direzione esplicita ("in diminuzione" / "in aumento") nel detail.
    # Pattern coerente con la realta' UX: l'utente vede una variazione
    # numerica e l'errore deve riportare quel segno senza assumere il
    # ruolo commerciale ("sconto" presuppone intenzionalita' che il
    # gate L2 non puo' inferire). Codici errore stabili — `*_SCONTO_*` e
    # `*_MAGGIORAZIONE_*` restano per discriminazione downstream
    # (approvazioni, dashboard, log) e per backward compatibility.
    direzione_label = "in diminuzione" if is_sconto else "in aumento"
    kind_label = "Sconto" if is_sconto else "Maggiorazione"  # backcompat dict
    if accept_for_approval:
        return {
            "tipo_violazione": "SCONTO" if is_sconto else "MAGGIORAZIONE",
            "variazione_abs_pct": str(variazione_abs.quantize(Decimal("0.01"))),
            "limite_pct": str(limite),
            "kind_label": kind_label,
        }

    # Fase 5.B2: retryable=True esplicito → semantica "puoi riprovare con
    # flag richiesta_approvazione=true" (workflow L3).
    error_code = (
        "E_PRICING_SCONTO_ECCESSIVO" if is_sconto
        else "E_PRICING_MAGGIORAZIONE_ECCESSIVA"
    )
    ErrorManager.raise_error(
        code=error_code,
        message="Variazione prezzo oltre il limite consentito.",
        detail=(
            f"Variazione richiesta {direzione_label}: "
            f"{variazione_abs.quantize(Decimal('0.01'))}% — "
            f"massimo ammesso: {limite}%."
        ),
        retryable=True,
        function_name=function_name,
    )


# Tolleranza confronto prezzi: il resolver ritorna Decimal a 10 decimali
# (max_digits=22, decimal_places=10), ma il round-trip BE -> JSON -> JS Number
# (53-bit float, ~15-17 cifre significative) -> InputNumber mode="currency"
# -> JSON -> BE perde precisione sull'ultima cifra. Quantizziamo entrambi a 4
# decimali (precisione abbondante per prezzi commerciali EUR) per il
# confronto: se uguali, salviamo il prezzo resolver originale (full
# precision) — il valore "che l'utente vede" era gia' un'approssimazione
# del valore canonico DB.
_PRICE_COMPARE_QUANTIZE = Decimal("0.0001")


# Scopo: Orchestratore dei 3 gate prezzo (L1 permesso + L2 soglia + L3
#        escalation) per la modifica manuale del prezzo unitario su righe
#        documento (preventivi, contratti, in futuro ordini/ddt).
#
#        Pattern simmetrico per tutte le sorgenti che ammettono override
#        prezzo: il caller passa la propria funzione di resolver
#        (`resolver_fn`) che sa come derivare il prezzo suggerito dato il
#        contesto documento, e il codice errore di validazione applicabile
#        al dominio (`error_code_validazione`).
#
#        Comportamento:
#          1. Se mancano dati per il resolver (BA / utility / data /
#             articolo_id / uom_id) → ritorna payload_prezzo + None
#             (skip wiring, accept manuale).
#          2. Chiama `resolver_fn(documento_id, articolo_id=, uom_id=,
#             auth_user_id=)` dentro savepoint (best-effort: se fallisce,
#             accetta payload manuale senza meta).
#          3. Auto-fill: se payload_prezzo None → ritorna resolver con meta.
#          4. Confronto payload vs resolver con tolleranza 4 decimali:
#             se uguali → no override, meta = resolver.
#          5. Override (payload != resolver):
#             - Gate L1: `check_permesso_override_prezzo` (azione
#               `prezzo_override_manuale`)
#             - Gate L2: `check_limite_variazione_prezzo` (soglia % via
#               cascata user → categoria → group → emittente → default)
#             - Gate L3: se `richiesta_approvazione=True`, eventuale
#               violazione L2 viene ritornata in meta come
#               `richiesta_approvazione_pending=True` invece di sollevare;
#               il caller orchestrera' la creazione della pratica.
#
#        Ritorna (prezzo_finale: Decimal | Any, meta_patch: dict | None):
#          - meta_patch include `origine_prezzo`, `prezzo_resolver_context`,
#            e per override anche `prezzo_applicato`, `override_user_id`,
#            `prezzo_base_resolver`, `delta_override`, `delta_override_pct`,
#            opzionalmente `richiesta_approvazione_pending` + `violazione_l2`.
#
#        Parametri:
#          - `testata`: dict con almeno `id`, `billing_account_id`,
#            `utility_id`, `data`. Usato per skip-context e per propagare
#            `billing_account_id` come BA per la cascata L2.
#          - `resolver_fn`: callable con signature
#            `(documento_id: int, *, articolo_id: str, uom_id: int,
#             auth_user_id: int | None) -> dict[str, Any]`.
#            Deve ritornare un dict con almeno `prezzo_finale` (None se non
#            risolto); opzionalmente `origine`, `listino_id`, `contratto_id`,
#            `promo_id`, `tipo_variazione_applicata`,
#            `valore_variazione_applicata` per il resolver_context.
#          - `error_code_validazione`: codice ServiceError di dominio
#            (es. `E_PREV_VALIDAZIONE` per preventivi,
#            `E_VENDITE_VALIDATION` per contratti). Usato solo se il payload
#            di prezzo non e' numerico.
#          - `richiesta_approvazione`: flag L3 escalation (Sprint E).
def resolve_or_check_override_prezzo(
    *,
    testata: Mapping[str, Any],
    articolo_id: Any,
    uom_id: Any,
    payload_prezzo: Any,
    auth_user_id: int | None,
    function_name: str,
    resolver_fn: Callable[..., dict[str, Any]],
    error_code_validazione: str,
    richiesta_approvazione: bool = False,
) -> tuple[Any, dict[str, Any] | None]:
    # Requisiti minimi per invocare il resolver. Se mancano, skippiamo il
    # wiring e ritorniamo il prezzo del payload senza meta audit.
    missing_resolver_ctx = (
        not articolo_id
        or not uom_id
        or testata.get("billing_account_id") is None
        or testata.get("utility_id") is None
        or testata.get("data") is None
    )
    if missing_resolver_ctx:
        return payload_prezzo, None

    # Resolver best-effort: se qualunque errore applicativo (es.
    # E_CATEGORIA_LISTINO_NON_MAPPATA) accettiamo il prezzo manuale.
    # Savepoint annidato: le RAISE EXCEPTION dentro il resolver DB marcano
    # la tx PostgreSQL come aborted; senza savepoint l'INSERT successivo
    # fallirebbe con InFailedSqlTransaction → mascherato in E_DATABASE
    # generico. Il savepoint isola l'errore e mantiene integra la tx esterna.
    prezzo_resolver: Decimal | None = None
    resolver_context: dict[str, Any] | None = None
    try:
        with transaction.atomic():
            resolver_result = resolver_fn(
                int(testata["id"]),
                articolo_id=str(articolo_id),
                uom_id=int(uom_id),
                auth_user_id=auth_user_id,
            )
            if resolver_result.get("prezzo_finale") is not None:
                prezzo_resolver = Decimal(str(resolver_result["prezzo_finale"]))
                resolver_context = {
                    "origine": resolver_result.get("origine"),
                    "listino_id": resolver_result.get("listino_id"),
                    "contratto_id": resolver_result.get("contratto_id"),
                    "promo_id": resolver_result.get("promo_id"),
                    "tipo_variazione": resolver_result.get("tipo_variazione_applicata"),
                    "valore_variazione": resolver_result.get("valore_variazione_applicata"),
                }
    except Exception:
        # Best-effort: se il resolver non trova prezzo, accettiamo il
        # payload manuale (se presente). Se payload_prezzo e' None in
        # questo ramo, il DB dara' NOT NULL sulla colonna oppure il
        # default del trigger — non e' responsabilita' di questo helper.
        return payload_prezzo, None

    # Auto-fill: payload senza prezzo -> uso il resolver.
    if payload_prezzo is None:
        return prezzo_resolver, {
            "origine_prezzo": resolver_context.get("origine") if resolver_context else None,
            "prezzo_resolver_context": resolver_context,
        }

    # Confronto: payload numerico atteso. La coercizione (da `str`, bool e
    # NaN rifiutati) e' del BB `PayloadValidator`, col codice del dominio
    # chiamante e il campo che il form accende.
    payload_decimal = PayloadValidator(validation_code=error_code_validazione).coerce_decimal(
        payload_prezzo,
        field="prezzo_unitario",
        message="Prezzo unitario non numerico.",
        function_name=function_name,
    )

    # Confronto con tolleranza 4 decimali (vedi _PRICE_COMPARE_QUANTIZE).
    if prezzo_resolver is not None:
        payload_q = payload_decimal.quantize(
            _PRICE_COMPARE_QUANTIZE, rounding=ROUND_HALF_UP,
        )
        resolver_q = prezzo_resolver.quantize(
            _PRICE_COMPARE_QUANTIZE, rounding=ROUND_HALF_UP,
        )
        if payload_q == resolver_q:
            return prezzo_resolver, {
                "origine_prezzo": resolver_context.get("origine") if resolver_context else None,
                "prezzo_resolver_context": resolver_context,
            }

    # Override: L1 richiesta azione processo prezzo_override_manuale.
    check_permesso_override_prezzo(auth_user_id, function_name=function_name)

    # L2: limite percentuale sconto/maggiorazione (Sprint D).
    # Se resolver non ha prezzo o e' 0 skip (non calcolabile); altrimenti
    # confronta delta_pct firmato con il parametro appropriato risolto per
    # l'utente. Cascata estesa (2026-05-15): la categoria cliente del BA
    # destinatario entra come livello fra user e group. Il lookup BA →
    # categoria avviene DENTRO `check_limite_variazione_prezzo` dopo gli
    # early-return (superuser bypass / delta=0 / resolver nullo) per non
    # sprecare round-trip DB quando L2 non si applica.
    # L3 (Sprint E): se chiamante chiede `richiesta_approvazione`, l'eventuale
    # violazione non solleva ma ritorna dict; il chiamante orchestrera' la
    # creazione pratica.
    violazione_l2 = check_limite_variazione_prezzo(
        auth_user_id=auth_user_id,
        prezzo_resolver=prezzo_resolver,
        prezzo_manuale=payload_decimal,
        function_name=function_name,
        accept_for_approval=richiesta_approvazione,
        ba_id=testata.get("billing_account_id"),
    )

    meta_patch: dict[str, Any] = {
        "origine_prezzo": ORIGINE_PREZZO_MANUALE,
        "prezzo_resolver_context": resolver_context,
        "prezzo_applicato": str(payload_decimal),
        "override_user_id": auth_user_id,
    }
    if prezzo_resolver is not None:
        delta = payload_decimal - prezzo_resolver
        meta_patch["prezzo_base_resolver"] = str(prezzo_resolver)
        meta_patch["delta_override"] = str(delta)
        if prezzo_resolver != 0:
            meta_patch["delta_override_pct"] = str((delta / prezzo_resolver) * Decimal("100"))

    # Hook L3: violazione L2 in modalita' "richiesta approvazione" → segnala
    # al chiamante per orchestrazione pratica + salvataggio riga PENDING.
    if violazione_l2 is not None:
        meta_patch["richiesta_approvazione_pending"] = True
        meta_patch["violazione_l2"] = violazione_l2

    return payload_decimal, meta_patch
