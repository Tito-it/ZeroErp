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
from dataclasses import dataclass
from decimal import ROUND_HALF_UP, Decimal, InvalidOperation
from typing import Any, Callable, NoReturn

from django.db import transaction

from apps.anagrafiche.db.billing_account_repository import BillingAccountRepository
from apps.core.db._helpers import coerce_jsonb_dict
from apps.core.services.error_manager import ErrorManager
from apps.core.services.parameter_service import ParameterService
from apps.core.services.payload_helpers import PayloadValidator
from apps.core.services.permissions_resolver import PermissionResolver
from apps.core.services.utente_per_id import utente_per_id
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
# (qui) e il prezzo di una riga di commessa (`prezzo_riga_commessa`), una sede.
# ⚠️ La PATCH dei componenti NON la scrive piu' (2026-11-14): sul prezzo
#    cambiato la provenienza la fa decadere il trigger del DB
#    (`_componenti_service_helpers.dati_patch_componente`).
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
#        override manuale del prezzo (SUPER_ADMIN compreso, dal check). Se auth_user_id
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
    user = utente_per_id(auth_user_id)
    if user is None:
        ErrorManager.raise_error(
            code="E_PRICING_OVERRIDE_NON_AUTORIZZATO",
            message="Override prezzo non autorizzato.",
            detail="Utente non trovato.",
            function_name=function_name,
        )
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
#    col messaggio suo e un bypass trattato in un altro modo: due risposte
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
#        (utente, BA, emittente) attraverso la cascata user → categoria_cliente
#        → group → emittente → default. Centralizza il pattern usato da
#        entrambi i gate L2 (riga e variazione globale). Il lookup
#        BA→categoria avviene solo se `ba_id` e' fornito.
# ⭐ L'emittente e' quello del DOCUMENTO, passato dal chiamante: la soglia e'
#    dell'azienda che vende, non di chi scrive. ⛔ Fino al 2026-11-25 veniva
#    dall'utente (`get_emittente_fiscale_id_for_user`), che al super admin
#    rispondeva il gestore globale: su un documento dell'emittente X il gate
#    applicava la soglia di un'altra azienda (E1-3 di brief-be-fe-BB-audit §6.1).
#    Senza default: un chiamante che non lo passa non compila la chiamata.
#
#        Restituisce la soglia come Decimal. Solleva
#        E_PARAMETER_VALIDATION se il parametro DB e' malformato (stato
#        inconsistente che l'admin deve correggere).
def _resolve_soglia_variazione_pct(
    *,
    auth_user_id: int,
    param_code: str,
    ba_id: int | None,
    emittente_fiscale_id: int | None,
) -> Decimal:
    categoria_cliente_id: int | None = None
    if ba_id is not None:
        categoria_cliente_id = BillingAccountRepository().get_categoria_cliente_id(
            int(ba_id),
        )
    return ParameterService().get_parameter_decimal(
        param_code,
        django_user_id=auth_user_id,
        emittente_fiscale_id=emittente_fiscale_id,
        categoria_cliente_id=categoria_cliente_id,
    )


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
    emittente_fiscale_id: int | None,
    accept_for_approval: bool = False,
    ba_id: int | None = None,
) -> dict[str, Any] | None:
    if prezzo_resolver is None or prezzo_resolver == 0:
        return None  # Nessun riferimento per calcolare la percentuale.

    if auth_user_id is None:
        return None  # L1 ha gia' bloccato; unreachable difensivo.

    user = utente_per_id(auth_user_id)
    if user is None:
        return None  # L1 avrebbe gia' bloccato.

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
        emittente_fiscale_id=emittente_fiscale_id,
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
#        `auth_user_id=None` salta il gate (L1 ha gia' deciso): e' un gate di
#        SCRITTURA, non un perimetro, dichiarato fuori dal rifiuto del `None`
#        (brief-db-porte-aperte-dalla-sola-guc §4.7). Il bypass del
#        superuser non c'e' piu' dal 2026-11-24 (D-J).
def check_limite_variazione_globale(
    *,
    auth_user_id: int | None,
    tipo_variazione: str | None,
    valore_variazione,  # Decimal | None
    function_name: str,
    emittente_fiscale_id: int | None,
    accept_for_approval: bool = False,
    ba_id: int | None = None,
) -> dict[str, Any] | None:
    if valore_variazione is None:
        return None  # Rimozione variazione: niente da gating.
    if tipo_variazione != "PERCENTUALE":
        return None  # VALORE_FISSO non e' un %.
    if auth_user_id is None:
        return None  # Contesto utente richiesto per cascata.

    user = utente_per_id(auth_user_id)
    if user is None:
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
        emittente_fiscale_id=emittente_fiscale_id,
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


# Il codice del 409 della provenienza dichiarata e smentita dal listino (D-5,
# R-8 di brief-db-provenienza-prezzo-segue-il-prezzo §8.11): lo solleva il BE,
# qui e solo qui. Policy generata, ripiego in `error_messages_fallback`.
E_PRICING_PROVENIENZA_SUPERATA = "E_PRICING_PROVENIENZA_SUPERATA"

# La chiave del corpo con cui il form di riga DICHIARA la provenienza del
# prezzo che rimanda (K-6): l'oggetto `{origine_prezzo, listino_versione_id,
# listino_riga_id}` ricevuto dall'endpoint di pricing. ⛔ Non e' una colonna:
# la legge `provenienza_dichiarata`, che la toglie dal corpo prima che il
# dominio componga i campi da scrivere.
CHIAVE_PROVENIENZA_DICHIARATA = "provenienza_prezzo"
_CHIAVI_DICHIARAZIONE: frozenset[str] = frozenset(
    {"origine_prezzo", "listino_versione_id", "listino_riga_id"}
)

# Le quattro colonne della provenienza del prezzo su ogni riga di documento di
# vendita (e sui componenti), coi nomi delle tabelle. ⭐ Il gate le scrive TUTTE
# o nessuna: una sola scritta lascerebbe le altre del prezzo di prima, e il
# CHECK `chk_<tabella>_provenienza_prezzo` rifiuterebbe un MANUALE che cita il
# listino.
COLONNE_PROVENIENZA_RIGA: tuple[str, ...] = (
    "origine_prezzo", "listino_versione_id", "listino_riga_id", "prezzo_resolver_context",
)
PROVENIENZA_MANUALE_RIGA: Mapping[str, Any] = {
    "origine_prezzo": ORIGINE_PREZZO_MANUALE,
    "listino_versione_id": None,
    "listino_riga_id": None,
    "prezzo_resolver_context": None,
}


# Scopo: la provenienza che il form dichiara per il prezzo che rimanda (D-5).
#        La dichiarazione si VERIFICA (`resolve_or_check_override_prezzo`):
#        da sola non rende un prezzo «da listino».
@dataclass(frozen=True)
class ProvenienzaDichiarata:
    origine_prezzo: str
    listino_versione_id: int | None
    listino_riga_id: int | None


# Scopo: legge e TOGLIE dal corpo la provenienza dichiarata
#        (`CHIAVE_PROVENIENZA_DICHIARATA`). `None` se il corpo non la porta,
#        cioe' un prezzo scritto a mano o nessun prezzo. Forma sbagliata = 400
#        col codice del dominio e il campo.
def provenienza_dichiarata(
    payload: dict[str, Any], *, error_code: str, function_name: str,
) -> ProvenienzaDichiarata | None:
    raw = payload.pop(CHIAVE_PROVENIENZA_DICHIARATA, None)
    if raw is None:
        return None
    ErrorManager.require(
        isinstance(raw, dict),
        code=error_code,
        message="La provenienza del prezzo dev'essere un oggetto.",
        context={"field": CHIAVE_PROVENIENZA_DICHIARATA},
        function_name=function_name,
    )
    assert isinstance(raw, dict)
    v = PayloadValidator(validation_code=error_code)
    v.validate_allowed_keys(
        raw, allowed=_CHIAVI_DICHIARAZIONE,
        message="Provenienza del prezzo non valida.", function_name=function_name,
    )
    return ProvenienzaDichiarata(
        origine_prezzo=v.require_string(raw, "origine_prezzo", function_name=function_name).strip(),
        listino_versione_id=v.optional_positive_int(
            raw, "listino_versione_id", function_name=function_name,
        ),
        listino_riga_id=v.optional_positive_int(
            raw, "listino_riga_id", function_name=function_name,
        ),
    )


# Scopo: l'esito del gate per una riga. `provenienza` sono le quattro colonne
#        da scrivere (`COLONNE_PROVENIENZA_RIGA`), `None` se il gate non ha
#        niente da dire e la provenienza la decide il trigger del DB
#        (`trgfn_riga_documento_provenienza_prezzo`). `meta` sono le sole chiavi
#        d'audit dell'override (prezzo applicato, utente, delta, L3): ⛔ la
#        provenienza non sta piu' nel `meta` (K-5). `esito_codice` e' il motivo
#        per cui il resolver non ha dato un prezzo, quando lo dice (il DDT lo
#        conserva).
@dataclass(frozen=True)
class EsitoPrezzoRiga:
    prezzo: Any
    provenienza: Mapping[str, Any] | None = None
    meta: Mapping[str, Any] | None = None
    esito_codice: str | None = None

    @property
    def richiesta_approvazione_pending(self) -> bool:
        return bool(self.meta and self.meta.get("richiesta_approvazione_pending"))

    # Scopo: scrive l'esito sui campi della riga da salvare: il prezzo (se il
    #        gate ne ha uno), le quattro colonne della provenienza, l'audit
    #        fuso sul `meta` (quello dei campi, altrimenti `meta_base`, il
    #        `meta` della riga esistente in modifica: senza, l'audit nuovo
    #        cancellerebbe le chiavi che la riga ha gia').
    # ⭐ Una sede per i cinque documenti: era ricopiata nei gate di preventivo
    #    (due volte), contratto e offerta.
    def applica(self, campi: dict[str, Any], *, meta_base: Any = None) -> None:
        if self.prezzo is not None:
            campi["prezzo_unitario"] = self.prezzo
        if self.provenienza is not None:
            campi.update(self.provenienza)
        if self.meta:
            fuso = dict(coerce_jsonb_dict(campi.get("meta") or meta_base))
            fuso.update(self.meta)
            campi["meta"] = fuso


# Scopo: le quattro colonne dal risultato del resolver: l'origine, la versione
#        e la riga che hanno dato il prezzo, e il contesto calcolato dal DB
#        (`vendite.fn_prezzo_resolver_contesto`, letto dal repository del
#        resolver: la regola di cosa entra nel contesto non si ricopia qui).
def _provenienza_dal_resolver(risultato: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "origine_prezzo": risultato.get("origine"),
        "listino_versione_id": risultato.get("listino_versione_id"),
        "listino_riga_id": risultato.get("listino_riga_id"),
        "prezzo_resolver_context": risultato.get("prezzo_resolver_context"),
    }


def _q(valore: Any) -> Decimal:
    return Decimal(str(valore)).quantize(_PRICE_COMPARE_QUANTIZE, rounding=ROUND_HALF_UP)


# Scopo: una modifica di riga che rimanda il prezzo che la riga ha gia', con
#        la stessa unita' di misura, non cambia il prezzo: non c'e' niente da
#        autorizzare ne' da verificare, e la provenienza resta quella che e'.
#        Il chiamante toglie il prezzo dai campi e non chiama il gate.
#        ⭐ Senza, chi corregge la sola quantita' di una riga ripasserebbe dal
#        gate col prezzo di prima: un 403 a chi non ha l'override su un prezzo
#        scritto da un altro, o un 409 su un prezzo da listino che nel
#        frattempo il listino ha cambiato.
#        La tolleranza e' quella del trasporto (`_PRICE_COMPARE_QUANTIZE`).
def prezzo_invariato(campi: Mapping[str, Any], riga_esistente: Mapping[str, Any]) -> bool:
    if "prezzo_unitario" not in campi:
        return False
    if (
        "uom_operativa_id" in campi
        and campi["uom_operativa_id"] is not None
        and riga_esistente.get("uom_operativa_id") is not None
        and int(campi["uom_operativa_id"]) != int(riga_esistente["uom_operativa_id"])
    ):
        return False
    nuovo, vecchio = campi["prezzo_unitario"], riga_esistente.get("prezzo_unitario")
    if nuovo is None or vecchio is None:
        return nuovo is None and vecchio is None
    if isinstance(nuovo, bool):
        return False
    try:
        return _q(nuovo) == _q(vecchio)
    except (InvalidOperation, ValueError):
        # Un prezzo malformato lo rifiuta il gate, col suo codice e il campo.
        return False


# Scopo: il 409 di una provenienza dichiarata che il listino di adesso non
#        conferma, o che non si puo' verificare (D-5, R-8): la riga non si
#        salva. `listino` = cio' che il listino da' oggi, se lo si e' chiesto.
#        Una sede: la usano il gate (`resolve_or_check_override_prezzo`) e i
#        wrapper di offerta e contratto, che senza listino non lo chiamano.
def rifiuta_provenienza_dichiarata(
    dichiarata: ProvenienzaDichiarata, *, dettaglio: str, function_name: str,
    listino: Mapping[str, Any] | None = None,
) -> NoReturn:
    ErrorManager.raise_error(
        code=E_PRICING_PROVENIENZA_SUPERATA,
        message="Il prezzo del listino è cambiato dopo che la riga è stata compilata.",
        detail=dettaglio,
        context={
            "field": "prezzo_unitario",
            "dichiarata": {
                "origine_prezzo": dichiarata.origine_prezzo,
                "listino_versione_id": dichiarata.listino_versione_id,
                "listino_riga_id": dichiarata.listino_riga_id,
            },
            "listino": dict(listino) if listino is not None else None,
        },
        function_name=function_name,
    )


# Scopo: Orchestratore dei gate prezzo per una riga documento (preventivo,
#        offerta, contratto, ordine, DDT): la provenienza del prezzo e, sul
#        prezzo scritto a mano, i gate L1 permesso + L2 soglia + L3 escalation.
#
#        Il caller passa la propria funzione di resolver (`resolver_fn`), che
#        sa derivare il prezzo dal contesto del documento, e il codice errore
#        di validazione del dominio (`error_code_validazione`).
#
#        I TRE CASI (D-5 di brief-db-provenienza-prezzo-segue-il-prezzo §8.11):
#          1. Payload senza prezzo → il prezzo e la provenienza del resolver.
#          2. Prezzo CON la provenienza dichiarata dal form (`dichiarata`) → si
#             rilancia il resolver: se origine, versione, riga e prezzo
#             coincidono con quello che il listino da' adesso, la riga e' da
#             listino, con le colonne scritte dal resolver; altrimenti 409
#             `E_PRICING_PROVENIENZA_SUPERATA` e non si salva.
#          3. Prezzo SENZA dichiarazione → MANUALE: gate L1
#             (`prezzo_override_manuale`), L2 (soglia %), L3 se
#             `richiesta_approvazione` (la violazione L2 torna nel `meta` come
#             `richiesta_approvazione_pending` invece di sollevare).
#        ⛔ Non si deduce piu' «viene dal listino» da un prezzo uguale a
#           quello del resolver (§2, §8.1): un operatore che riscrive lo
#           stesso numero ha scritto un prezzo a mano.
#        Fuori dai tre casi:
#          - mancano dati per il resolver (BA / utility / data / articolo /
#            uom) → senza prezzo, nessun prezzo (la provenienza la decide il
#            DB); col prezzo, MANUALE con L1 (non L2/L3: non c'e' un listino da
#            cui misurare, R-1 del 2026-11-15); con una dichiarazione, 409;
#          - il resolver solleva → con un prezzo nel payload come sopra
#            (savepoint); senza, l'errore risale.
#
#        Parametri:
#          - `testata`: dict con almeno `id`, `billing_account_id`,
#            `utility_id`, `data`, `emittente_fiscale_id` (la soglia L2 e'
#            dell'azienda del documento, dal 2026-11-25).
#          - `resolver_fn`: `(documento_id, *, articolo_id, uom_id,
#            auth_user_id) -> dict` con `prezzo_finale` (None se non risolto),
#            `origine`, `listino_versione_id`, `listino_riga_id`,
#            `prezzo_resolver_context`, e per il DDT `esito_codice`.
#          - `dichiarata`: la provenienza dichiarata dal form
#            (`provenienza_dichiarata`), o None.
#          - `error_code_validazione`: il codice del payload di prezzo non
#            numerico.
#          - `richiesta_approvazione`: flag L3.
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
    dichiarata: ProvenienzaDichiarata | None = None,
) -> EsitoPrezzoRiga:
    def _smentita(dettaglio: str, listino: Mapping[str, Any] | None = None) -> NoReturn:
        assert dichiarata is not None
        rifiuta_provenienza_dichiarata(
            dichiarata, dettaglio=dettaglio, listino=listino, function_name=function_name,
        )

    # Una dichiarazione vale solo per un prezzo: senza prezzo il caso e' il 1.
    if payload_prezzo is None:
        dichiarata = None

    # Il prezzo a mano quando il listino non risponde (manca il contesto, o il
    # resolver solleva): L1 si applica lo stesso, L2 e L3 no (non c'e' un
    # prezzo di listino da cui misurare lo scostamento). ⛔ Fino al 2026-11-15
    # qui il prezzo passava senza L1: chi non ha l'override poteva prezzare a
    # piacere un articolo fuori listino (R-1 della revisione, decisione (a) di
    # Tid del 2026-11-15).
    def _a_mano_senza_listino() -> EsitoPrezzoRiga:
        prezzo = PayloadValidator(validation_code=error_code_validazione).coerce_decimal(
            payload_prezzo,
            field="prezzo_unitario",
            message="Prezzo unitario non numerico.",
            function_name=function_name,
        )
        check_permesso_override_prezzo(auth_user_id, function_name=function_name)
        return EsitoPrezzoRiga(
            prezzo=prezzo,
            provenienza=PROVENIENZA_MANUALE_RIGA,
            meta={"prezzo_applicato": str(prezzo), "override_user_id": auth_user_id},
        )

    missing_resolver_ctx = (
        not articolo_id
        or not uom_id
        or testata.get("billing_account_id") is None
        or testata.get("utility_id") is None
        or testata.get("data") is None
    )
    if missing_resolver_ctx:
        if dichiarata is not None:
            _smentita("Manca il contesto per chiedere il prezzo al listino.")
        if payload_prezzo is None:
            return EsitoPrezzoRiga(prezzo=None)
        return _a_mano_senza_listino()

    # Resolver best-effort, in un savepoint: le RAISE EXCEPTION del resolver DB
    # marcano la transazione come abortita, e senza savepoint l'INSERT
    # successivo fallirebbe con InFailedSqlTransaction (mascherato in
    # E_DATABASE). Il savepoint isola l'errore e tiene integra la transazione.
    risultato: dict[str, Any]
    prezzo_resolver: Decimal | None = None
    try:
        with transaction.atomic():
            risultato = resolver_fn(
                int(testata["id"]),
                articolo_id=str(articolo_id),
                uom_id=int(uom_id),
                auth_user_id=auth_user_id,
            )
    except Exception:
        # Senza prezzo nel payload non c'e' niente da accettare: l'errore del
        # listino RISALE col suo codice (il guscio del resolver solleva quando
        # non risolve, ed e' cio' che ferma il prezzo assente; il nucleo del
        # DDT non solleva). ⚠️ Fino al 2026-11-15 si inghiottiva anche qui, e
        # il chiamante riceveva un prezzo None da spiegare con un messaggio suo.
        if payload_prezzo is None:
            raise
        # Il listino non da' un prezzo: quello del payload, a mano (con L1).
        if dichiarata is not None:
            _smentita("Il listino non da' un prezzo per questo articolo e unita' di misura.")
        return _a_mano_senza_listino()
    if risultato.get("prezzo_finale") is not None:
        prezzo_resolver = Decimal(str(risultato["prezzo_finale"]))

    # 1. Payload senza prezzo → il resolver, prezzo e provenienza.
    if payload_prezzo is None:
        return EsitoPrezzoRiga(
            prezzo=prezzo_resolver,
            provenienza=_provenienza_dal_resolver(risultato) if prezzo_resolver is not None else None,
            esito_codice=risultato.get("esito_codice"),
        )

    # Payload numerico atteso. La coercizione (da `str`, bool e NaN rifiutati)
    # e' del BB `PayloadValidator`, col codice del dominio chiamante e il campo
    # che il form accende.
    payload_decimal = PayloadValidator(validation_code=error_code_validazione).coerce_decimal(
        payload_prezzo,
        field="prezzo_unitario",
        message="Prezzo unitario non numerico.",
        function_name=function_name,
    )

    # 2. La provenienza dichiarata, verificata sul listino di adesso.
    if dichiarata is not None:
        listino = {
            "origine_prezzo": risultato.get("origine"),
            "listino_versione_id": risultato.get("listino_versione_id"),
            "listino_riga_id": risultato.get("listino_riga_id"),
            "prezzo_unitario": str(prezzo_resolver) if prezzo_resolver is not None else None,
        }
        coincide = (
            prezzo_resolver is not None
            and listino["origine_prezzo"] == dichiarata.origine_prezzo
            and listino["listino_versione_id"] == dichiarata.listino_versione_id
            and listino["listino_riga_id"] == dichiarata.listino_riga_id
            and _q(payload_decimal) == _q(prezzo_resolver)
        )
        if not coincide:
            _smentita(
                "La riga dichiara un prezzo preso dal listino, ma oggi il listino "
                "da' un'altra provenienza o un altro prezzo.",
                listino,
            )
        return EsitoPrezzoRiga(
            prezzo=prezzo_resolver, provenienza=_provenienza_dal_resolver(risultato),
        )

    # 3. Prezzo scritto a mano.
    # L1: azione di processo prezzo_override_manuale.
    check_permesso_override_prezzo(auth_user_id, function_name=function_name)

    # L2: limite percentuale sconto/maggiorazione (Sprint D). Se il resolver
    # non ha prezzo o e' 0 si salta (non calcolabile). Cascata estesa
    # (2026-05-15): la categoria cliente del BA destinatario entra fra user e
    # group; il lookup BA → categoria avviene DENTRO
    # `check_limite_variazione_prezzo`, dopo gli early-return.
    # L3 (Sprint E): con `richiesta_approvazione` la violazione non solleva
    # ma torna nel `meta`; il chiamante orchestra la pratica.
    violazione_l2 = check_limite_variazione_prezzo(
        auth_user_id=auth_user_id,
        prezzo_resolver=prezzo_resolver,
        prezzo_manuale=payload_decimal,
        function_name=function_name,
        accept_for_approval=richiesta_approvazione,
        ba_id=testata.get("billing_account_id"),
        # La soglia dell'azienda del documento (E1-3, 2026-11-25). Indicizzato,
        # non `.get()`: una testata senza emittente e' un difetto del loader, e
        # un None qui salterebbe il livello emittente in silenzio.
        emittente_fiscale_id=testata["emittente_fiscale_id"],
    )

    meta_patch: dict[str, Any] = {
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

    return EsitoPrezzoRiga(
        prezzo=payload_decimal, provenienza=PROVENIENZA_MANUALE_RIGA, meta=meta_patch,
    )
