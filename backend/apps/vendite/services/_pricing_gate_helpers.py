# ------------------------------------------------------------
# SPDX-License-Identifier: GPL-3.0-or-later
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

from decimal import Decimal, InvalidOperation
from typing import Any

from django.contrib.auth import get_user_model

from apps.anagrafiche.db.billing_account_repository import BillingAccountRepository
from apps.core.services.error_manager import ErrorManager
from apps.core.services.parameter_service import ParameterService
from apps.core.services.permissions_resolver import PermissionResolver
from apps.vendite.services.pricing_service import (
    PARAM_MAX_MAGGIORAZIONE_PCT,
    PARAM_MAX_SCONTO_PCT,
)

# Codice azione di processo per il gate L1 (override manuale prezzo).
# Storicamente importato come `AZIONE_OVERRIDE_PREZZO` da
# _approvazioni_prezzo_constants. Mantenuto qui come constante locale per
# evitare cicli di import (questo modulo e' importato sia da preventivi che
# da contratti, mentre il modulo originale dipendeva da `apps.vendite.services`).
AZIONE_OVERRIDE_PREZZO = "prezzo_override_manuale"


# Scopo: Gate L1 — verifica che l'operatore abbia l'azione di processo per
#        override manuale del prezzo. Bypass per superuser. Se auth_user_id
#        None (chiamata non autenticata, es. script interni) -> blocca
#        conservativamente.
def check_permesso_override_prezzo(
    auth_user_id: int | None, *, function_name: str,
) -> None:
    ErrorManager.require(
        auth_user_id is not None,
        code="E_PREV_OVERRIDE_NON_AUTORIZZATO",
        message="Override prezzo non autorizzato.",
        detail="Chiamata senza contesto utente — override bloccato conservativamente.",
        function_name=function_name,
    )
    user_model = get_user_model()
    try:
        user = user_model.objects.get(pk=auth_user_id)
    except user_model.DoesNotExist:
        ErrorManager.raise_error(
            code="E_PREV_OVERRIDE_NON_AUTORIZZATO",
            message="Override prezzo non autorizzato.",
            detail="Utente non trovato.",
            function_name=function_name,
        )
    if getattr(user, "is_superuser", False):
        return
    abilitato = PermissionResolver.check_azione(user, AZIONE_OVERRIDE_PREZZO)
    ErrorManager.require(
        abilitato,
        code="E_PREV_OVERRIDE_NON_AUTORIZZATO",
        message="Modifica manuale del prezzo non autorizzata.",
        detail=(
            "Usa il prezzo suggerito dal listino o richiedi l'autorizzazione "
            "'prezzo_override_manuale' al tuo responsabile."
        ),
        function_name=function_name,
    )


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
#        Solleva ServiceError L2 (E_PREV_SCONTO_ECCESSIVO /
#        E_PREV_MAGGIORAZIONE_ECCESSIVA, retryable=True) se violazione +
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
        # Coerce upstream avrebbe gia' bloccato (`_coerce_decimal` nel
        # `_build_update_data_testata`). Eccezioni piu' generiche
        # (`Exception`) maschererebbero bug strutturali: restringiamo.
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
    kind_label = "Sconto" if is_sconto else "Maggiorazione"
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
        "E_PREV_SCONTO_ECCESSIVO" if is_sconto
        else "E_PREV_MAGGIORAZIONE_ECCESSIVA"
    )
    ErrorManager.raise_error(
        code=error_code,
        message=f"{kind_label} oltre il limite consentito.",
        detail=(
            f"{kind_label} richiesto: {variazione_abs.quantize(Decimal('0.01'))}% — "
            f"massimo ammesso: {limite}%."
        ),
        retryable=True,
        function_name=function_name,
    )
    raise AssertionError("unreachable")  # pragma: no cover
