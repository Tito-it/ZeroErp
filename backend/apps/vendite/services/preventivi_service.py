# ------------------------------------------------------------
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2025 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Facade applicativa per preventivi vendita (CRUD, stato, righe, integrazione).
# ------------------------------------------------------------

# Orchestrazione preventivi vendita: validazione, guard su stato,
# delega a repository per accesso DB, gestione transizioni e integrazione
# con commesse e pratiche.

from datetime import date
from typing import Any

from django.contrib.auth import get_user_model

from apps.core.services.error_manager import ErrorManager
from apps.core.services.parameter_service import ParameterService
from apps.core.services.permissions_resolver import PermissionResolver
from apps.core.services.value_normalizer import empty_to_none
from apps.vendite.db.preventivi_repository import PreventiviRepository
from apps.vendite.services.pricing_service import (
    PARAM_MAX_MAGGIORAZIONE_PCT,
    PARAM_MAX_SCONTO_PCT,
)
from apps.core.api.payload_validators import paginated_envelope


# ── Costanti di validazione ──

_STATI_MODIFICABILI: frozenset[str] = frozenset({"DRAFT"})
_STATI_RIGHE_MODIFICABILI: frozenset[str] = frozenset({"DRAFT"})
_STATI_FATTURABILI: frozenset[str] = frozenset({"ACCETTATO"})
_STATI_GENERA_PRATICA: frozenset[str] = frozenset({"ACCETTATO"})
_FN = "vendite.preventivi_service"


# ══════════════════════════════════════════════════════════
#  LETTURE
# ══════════════════════════════════════════════════════════


# Scopo: Lista preventivi paginata con filtri e scope emittente.
def list_preventivi(
    *,
    stato_codice: str | None = None,
    billing_account_id: int | None = None,
    utility_id: int | None = None,
    data_da: date | None = None,
    data_al: date | None = None,
    search: str | None = None,
    auth_user_id: int | None = None,
    page: int = 1,
    page_size: int = 50,
) -> dict[str, object]:
    ErrorManager.require(
        page >= 1 and 1 <= page_size <= 200,
        code="E_PREV_VALIDAZIONE",
        message="Parametri paginazione non validi.",
        function_name=f"{_FN}.list_preventivi",
    )
    offset = (page - 1) * page_size
    repo = PreventiviRepository()
    results, total_count = repo.list_preventivi(
        stato_codice=stato_codice,
        billing_account_id=billing_account_id,
        utility_id=utility_id,
        data_da=data_da,
        data_al=data_al,
        search=search,
        auth_user_id=auth_user_id,
        limit=page_size,
        offset=offset,
    )
    return paginated_envelope(results, total_count, page, page_size)


# Scopo: Dettaglio preventivo completo (testata + righe + indirizzi).
def get_preventivo(preventivo_id: int) -> dict[str, object]:
    repo = PreventiviRepository()
    testata = repo.get_preventivo(preventivo_id)
    ErrorManager.require(
        testata is not None,
        code="E_PREV_NOT_FOUND",
        message="Preventivo non trovato.",
        detail=f"preventivo_id={preventivo_id}",
        function_name=f"{_FN}.get_preventivo",
    )
    assert testata is not None
    righe = repo.list_righe(preventivo_id)
    indirizzi = repo.list_indirizzi(preventivo_id)
    return {
        **testata,
        "righe": righe,
        "indirizzi": indirizzi,
    }


# Scopo: Lista righe di un preventivo.
def list_righe(preventivo_id: int) -> list[dict[str, Any]]:
    repo = PreventiviRepository()
    return repo.list_righe(preventivo_id)


# Scopo: Lista indirizzi di un preventivo.
def list_indirizzi(preventivo_id: int) -> list[dict[str, Any]]:
    repo = PreventiviRepository()
    return repo.list_indirizzi(preventivo_id)


# Scopo: Upsert indirizzo preventivo (uno per tipo).
def upsert_indirizzo(preventivo_id: int, payload: dict[str, Any]) -> dict[str, Any]:
    repo = PreventiviRepository()

    tipo_indirizzo_id = payload.get("tipo_indirizzo_id")
    ErrorManager.require(
        tipo_indirizzo_id is not None,
        code="E_PREV_VALIDAZIONE",
        message="tipo_indirizzo_id obbligatorio.",
        function_name=f"{_FN}.upsert_indirizzo",
    )

    return repo.upsert_indirizzo(
        preventivo_id=preventivo_id,
        tipo_indirizzo_id=int(tipo_indirizzo_id),
        snapshot=dict(payload.get("snapshot", {})),
        origine_indirizzo_id=payload.get("origine_indirizzo_id"),
        origine_soggetto_ruolo_id=payload.get("origine_soggetto_ruolo_id"),
    )


# ══════════════════════════════════════════════════════════
#  SCRITTURE — Testata
# ══════════════════════════════════════════════════════════


# Scopo: Crea un nuovo preventivo in stato BOZZA.
# Obiettivo: validazione input, risoluzione stato BOZZA, INSERT, restituisce id+uid+numero.
def crea_preventivo(payload: dict[str, Any]) -> dict[str, Any]:
    repo = PreventiviRepository()

    utility_id = payload.get("utility_id")
    ErrorManager.require(
        utility_id is not None,
        code="E_PREV_VALIDAZIONE",
        message="utility_id obbligatorio.",
        function_name=f"{_FN}.crea_preventivo",
    )

    stato_bozza_id = repo.get_stato_bozza_id()
    ErrorManager.require(
        stato_bozza_id is not None,
        code="E_CONFIG_MANCANTE",
        message="Stato BOZZA non configurato in config.stati_doc_preventivi.",
        function_name=f"{_FN}.crea_preventivo",
    )
    assert stato_bozza_id is not None

    result = repo.create_preventivo(
        billing_account_id=payload.get("billing_account_id"),
        utility_id=utility_id,
        istanza_utility_id=payload.get("istanza_utility_id"),
        valuta_id=payload.get("valuta_id"),
        termine_pagamento_id=payload.get("termine_pagamento_id"),
        validita_dal=payload.get("validita_dal"),
        validita_al=payload.get("validita_al"),
        competenza_mese=payload.get("competenza_mese"),
        fatturazione_immediata=payload.get("fatturazione_immediata", False),
        stato_doc_preventivo_id=stato_bozza_id,
        meta=payload.get("meta"),
    )
    return result


# Scopo: Aggiorna testata preventivo con guard su stato modificabile.
def aggiorna_preventivo(preventivo_id: int, payload: dict[str, Any]) -> dict[str, Any]:
    repo = PreventiviRepository()
    testata = repo.get_preventivo(preventivo_id)
    ErrorManager.require(
        testata is not None,
        code="E_PREV_NOT_FOUND",
        message="Preventivo non trovato.",
        function_name=f"{_FN}.aggiorna_preventivo",
    )
    assert testata is not None
    ErrorManager.require(
        testata["stato_codice_interno"] in _STATI_MODIFICABILI,
        code="E_PREV_STATO_NON_MODIFICABILE",
        message="Preventivo non modificabile nello stato corrente.",
        detail=f"stato={testata['stato_codice_interno']}",
        function_name=f"{_FN}.aggiorna_preventivo",
    )

    # Campi aggiornabili in BOZZA
    update_fields: dict[str, Any] = {}
    for key in (
        "billing_account_id", "utility_id", "istanza_utility_id",
        "valuta_id", "termine_pagamento_id",
        "validita_dal", "validita_al", "competenza_mese",
        "fatturazione_immediata", "meta",
    ):
        if key in payload:
            val = payload[key]
            update_fields[key] = empty_to_none(val) if isinstance(val, str) else val

    if update_fields:
        repo.update_preventivo(preventivo_id, **update_fields)

    return {"status": "ok", "preventivo_id": preventivo_id}


# Scopo: Cambia stato preventivo delegando alla funzione DB.
def cambia_stato(preventivo_id: int, nuovo_stato: str) -> dict[str, Any]:
    repo = PreventiviRepository()
    result = repo.cambia_stato(preventivo_id, nuovo_stato, "django_api")
    return result


# Scopo: Crea nuova revisione del preventivo delegando alla funzione DB.
def crea_revisione(preventivo_id: int) -> dict[str, Any]:
    repo = PreventiviRepository()
    result = repo.crea_revisione(preventivo_id, "django_api")
    return result


# ══════════════════════════════════════════════════════════
#  SCRITTURE — Righe
# ══════════════════════════════════════════════════════════


# Scopo: Aggiunge riga al preventivo con guard su stato + ricalcolo totali.
#        Auto-fill prezzo da resolver v5 (Sprint 2 B+L1): se il payload non
#        specifica `prezzo_unitario`, viene risolto automaticamente tramite
#        `PricingService.resolve_prezzo`. Se il caller passa un prezzo
#        diverso dal suggerito, serve il permesso di azione processo
#        `prezzo_override_manuale`; altrimenti `E_PREV_OVERRIDE_NON_AUTORIZZATO`.
#        Tracciamento sempre in `meta.prezzo_resolver_context`.
def gestisci_riga(
    preventivo_id: int,
    payload: dict[str, Any],
    *,
    auth_user_id: int | None = None,
) -> dict[str, Any]:
    repo = PreventiviRepository()
    testata = repo.get_preventivo(preventivo_id)
    ErrorManager.require(
        testata is not None,
        code="E_PREV_NOT_FOUND",
        message="Preventivo non trovato.",
        function_name=f"{_FN}.gestisci_riga",
    )
    assert testata is not None
    ErrorManager.require(
        testata["stato_codice_interno"] in _STATI_RIGHE_MODIFICABILI,
        code="E_PREV_STATO_NON_MODIFICABILE",
        message="Righe non modificabili nello stato corrente.",
        detail=f"stato={testata['stato_codice_interno']}",
        function_name=f"{_FN}.gestisci_riga",
    )

    articolo_id = payload.get("articolo_id")
    ErrorManager.require(
        articolo_id is not None,
        code="E_PREV_VALIDAZIONE",
        message="articolo_id obbligatorio.",
        function_name=f"{_FN}.gestisci_riga",
    )

    uom_id = payload.get("uom_operativa_id")
    payload_prezzo = payload.get("prezzo_unitario")
    prezzo_finale, prezzo_meta = _resolve_or_check_override_prezzo(
        testata=testata,
        articolo_id=articolo_id,
        uom_id=uom_id,
        payload_prezzo=payload_prezzo,
        auth_user_id=auth_user_id,
        function_name=f"{_FN}.gestisci_riga",
    )

    # Merge meta esistente del payload con audit prezzo.
    merged_meta = dict(payload.get("meta") or {})
    if prezzo_meta is not None:
        merged_meta.update(prezzo_meta)

    result = repo.create_riga(
        preventivo_id=preventivo_id,
        articolo_id=articolo_id,
        descrizione=payload.get("descrizione"),
        quantita=payload.get("quantita"),
        qta_operativa=payload.get("qta_operativa"),
        uom_operativa_id=uom_id,
        factor_to_base=payload.get("factor_to_base"),
        prezzo_unitario=prezzo_finale,
        sconto_percentuale=payload.get("sconto_percentuale"),
        iva_id=payload.get("iva_id"),
        ordine=payload.get("ordine"),
        meta=merged_meta or None,
    )
    # Ricalcolo totali gestito da trigger DB AFTER su preventivi_righe
    return result


# Scopo: Aggiorna riga esistente con guard su stato + ricalcolo totali.
#        L1 override prezzo: se il payload modifica `prezzo_unitario`,
#        verifica che il valore passato sia il prezzo resolver o che
#        l'operatore abbia permesso di override (azione
#        `prezzo_override_manuale`). La verifica viene fatta solo se
#        `prezzo_unitario` e' esplicitamente nel payload (campo modificato).
def aggiorna_riga(
    preventivo_id: int,
    riga_id: int,
    payload: dict[str, Any],
    *,
    auth_user_id: int | None = None,
) -> dict[str, Any]:
    repo = PreventiviRepository()
    testata = repo.get_preventivo(preventivo_id)
    ErrorManager.require(
        testata is not None,
        code="E_PREV_NOT_FOUND",
        message="Preventivo non trovato.",
        function_name=f"{_FN}.aggiorna_riga",
    )
    assert testata is not None
    ErrorManager.require(
        testata["stato_codice_interno"] in _STATI_RIGHE_MODIFICABILI,
        code="E_PREV_STATO_NON_MODIFICABILE",
        message="Righe non modificabili nello stato corrente.",
        function_name=f"{_FN}.aggiorna_riga",
    )

    update_fields: dict[str, Any] = {}
    for key in (
        "descrizione", "quantita", "qta_operativa", "uom_operativa_id",
        "factor_to_base", "prezzo_unitario", "sconto_percentuale",
        "iva_id", "ordine", "meta",
    ):
        if key in payload:
            update_fields[key] = payload[key]

    # L1 check + audit meta se prezzo toccato esplicitamente. Serve contesto
    # riga esistente per articolo_id/uom_id non sempre presenti nel payload.
    if "prezzo_unitario" in update_fields:
        righe = repo.list_righe(preventivo_id)
        riga_esistente = next((r for r in righe if r.get("id") == riga_id), None)
        ErrorManager.require(
            riga_esistente is not None,
            code="E_PREV_RIGA_NOT_FOUND",
            message="Riga preventivo non trovata.",
            detail=f"riga_id={riga_id}",
            function_name=f"{_FN}.aggiorna_riga",
        )
        assert riga_esistente is not None
        articolo_id = riga_esistente["articolo_id"]
        uom_id = update_fields.get("uom_operativa_id") or riga_esistente.get("uom_operativa_id")
        prezzo_finale, prezzo_meta = _resolve_or_check_override_prezzo(
            testata=testata,
            articolo_id=articolo_id,
            uom_id=uom_id,
            payload_prezzo=update_fields["prezzo_unitario"],
            auth_user_id=auth_user_id,
            function_name=f"{_FN}.aggiorna_riga",
        )
        update_fields["prezzo_unitario"] = prezzo_finale
        if prezzo_meta is not None:
            merged_meta = dict(update_fields.get("meta") or riga_esistente.get("meta") or {})
            merged_meta.update(prezzo_meta)
            update_fields["meta"] = merged_meta

    if update_fields:
        updated = repo.update_riga(riga_id, **update_fields)
        ErrorManager.require(
            updated,
            code="E_PREV_RIGA_NOT_FOUND",
            message="Riga preventivo non trovata.",
            detail=f"riga_id={riga_id}",
            function_name=f"{_FN}.aggiorna_riga",
        )
        # Ricalcolo totali gestito da trigger DB AFTER su preventivi_righe

    return {"status": "ok", "riga_id": riga_id}


# Scopo: Helper condiviso gestisci_riga / aggiorna_riga per la risoluzione
#        del prezzo via resolver v5 + check L1 override + costruzione meta
#        audit. Vive qui per evitare duplicazione tra create e update.
#
#        Comportamento:
#        - se payload_prezzo e' None -> auto-fill dal resolver, origine
#          = valore del resolver (PROMO/CONTRATTO_*/CATEGORIA)
#        - se payload_prezzo == resolver_prezzo -> OK, origine resolver
#        - se payload_prezzo != resolver_prezzo -> check azione
#          prezzo_override_manuale; se negato E_PREV_OVERRIDE_NON_AUTORIZZATO
#        - meta audit sempre popolato con prezzo_resolver_context
#
#        Ritorna (prezzo_finale: Decimal|str, meta_patch: dict|None).
#        Se articolo_id/uom_id mancano, salta il resolver e ritorna il
#        prezzo del payload (retrocompatibilita': non tutti i preventivi
#        hanno UoM configurata — il resolver e' best-effort).
def _resolve_or_check_override_prezzo(
    *,
    testata: dict[str, Any],
    articolo_id: Any,
    uom_id: Any,
    payload_prezzo: Any,
    auth_user_id: int | None,
    function_name: str,
) -> tuple[Any, dict[str, Any] | None]:
    from decimal import Decimal

    # Requisiti minimi per invocare il resolver. Se mancano (payload
    # semplificato, BA/utility non impostati sul preventivo), skippiamo
    # il wiring e ritorniamo il prezzo del payload senza meta audit.
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
    # L'override non e' controllato perche' non c'e' nulla da confrontare.
    prezzo_resolver: Decimal | None = None
    resolver_context: dict[str, Any] | None = None
    try:
        resolver_result = suggerisci_prezzo_riga(
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

    # Confronto: stesso prezzo -> nessun override, meta = resolver.
    try:
        payload_decimal = Decimal(str(payload_prezzo))
    except Exception:
        ErrorManager.raise_error(
            code="E_PREV_VALIDAZIONE",
            message="Prezzo unitario non numerico.",
            detail=f"prezzo_unitario={payload_prezzo!r}",
            function_name=function_name,
        )
        raise AssertionError("unreachable")  # pragma: no cover

    if prezzo_resolver is not None and payload_decimal == prezzo_resolver:
        return payload_decimal, {
            "origine_prezzo": resolver_context.get("origine") if resolver_context else None,
            "prezzo_resolver_context": resolver_context,
        }

    # Override: L1 richiesta azione processo prezzo_override_manuale.
    _check_permesso_override_prezzo(auth_user_id, function_name=function_name)

    # L2: limite percentuale sconto/maggiorazione (autorizzazioni prezzi Sprint D).
    # Se resolver non ha prezzo o e' 0 skip (non calcolabile); altrimenti
    # confronta delta_pct firmato con il parametro appropriato risolto per
    # l'utente (default 0 = nessuna variazione ammessa).
    _check_limite_variazione_prezzo(
        auth_user_id=auth_user_id,
        prezzo_resolver=prezzo_resolver,
        prezzo_manuale=payload_decimal,
        function_name=function_name,
    )

    meta_patch: dict[str, Any] = {
        "origine_prezzo": "MANUALE",
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
    return payload_decimal, meta_patch


# Scopo: Verifica che l'operatore abbia l'azione processo per override
#        manuale del prezzo (livello L1 del sistema autorizzazioni prezzi).
#        Bypass per superuser. Se auth_user_id None (chiamata non
#        autenticata, es. script interni) -> blocca conservativamente.
def _check_permesso_override_prezzo(
    auth_user_id: int | None, *, function_name: str
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
    abilitato = PermissionResolver.check_azione(user, "prezzo_override_manuale")
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


# Scopo: Verifica che la variazione % fra prezzo manuale e prezzo risolto
#        rientri nei limiti configurati per l'utente (L2 autorizzazioni
#        prezzi). Se sconto (delta < 0) confronta con VENDITE_MAX_SCONTO_PCT;
#        se maggiorazione (delta > 0) con VENDITE_MAX_MAGGIORAZIONE_PCT.
#        Skip se prezzo_resolver e' None o 0 (non calcolabile / safe-fail).
#        Superuser bypass. Parametri risolti via ParameterService con
#        scope user -> group -> emittente -> default.
def _check_limite_variazione_prezzo(
    *,
    auth_user_id: int | None,
    prezzo_resolver,  # Decimal | None
    prezzo_manuale,   # Decimal
    function_name: str,
) -> None:
    from decimal import Decimal

    if prezzo_resolver is None or prezzo_resolver == 0:
        return  # Nessun riferimento per calcolare la percentuale.

    if auth_user_id is None:
        return  # L1 ha gia' bloccato; unreachable difensivo.

    user_model = get_user_model()
    try:
        user = user_model.objects.get(pk=auth_user_id)
    except user_model.DoesNotExist:
        return  # L1 avrebbe gia' bloccato.
    if getattr(user, "is_superuser", False):
        return

    delta = prezzo_manuale - prezzo_resolver
    if delta == 0:
        return  # Edge case: L1 avrebbe gia' fatto early-return.

    delta_pct = (delta / prezzo_resolver) * Decimal("100")

    # Sconto se delta negativo, maggiorazione se positivo. Per ogni caso
    # risolviamo UNA sola chiave parametro dedicata e la confrontiamo con
    # il valore assoluto del delta. get_parameter_decimal raise
    # E_PARAMETER_VALIDATION se il parametro e' malformato: stato
    # inconsistente che l'admin deve correggere (no silent fallback).
    param_service = ParameterService()
    is_sconto = delta_pct < 0
    param_code = PARAM_MAX_SCONTO_PCT if is_sconto else PARAM_MAX_MAGGIORAZIONE_PCT
    variazione_abs = -delta_pct if is_sconto else delta_pct
    limite = param_service.get_parameter_decimal(
        param_code, django_user_id=auth_user_id,
    )

    if variazione_abs <= limite:
        return

    error_code = "E_PREV_SCONTO_ECCESSIVO" if is_sconto else "E_PREV_MAGGIORAZIONE_ECCESSIVA"
    kind_label = "Sconto" if is_sconto else "Maggiorazione"
    ErrorManager.raise_error(
        code=error_code,
        message=f"{kind_label} oltre il limite consentito.",
        detail=(
            f"{kind_label} richiesto: {variazione_abs.quantize(Decimal('0.01'))}% — "
            f"massimo ammesso: {limite}%."
        ),
        function_name=function_name,
    )


# Scopo: Suggerisce il prezzo della riga preventivo delegando al resolver
#        pricing v5. Non modifica nulla: solo lettura. L'operatore ottiene
#        il prezzo "di default" dal listino/contratto/categoria del BA
#        associato al preventivo, alla data del preventivo, per l'utility
#        del preventivo. L'emittente_soggetto_ruolo_id e' derivato dal JWT
#        operatore via PermissionResolver.
#
#        Uso tipico: chiamata FE all'apertura del drawer riga per
#        pre-compilare il campo prezzo. L'operatore puo' accettare il
#        suggerito o fornire un override (controllato da permesso L1 in
#        gestisci_riga).
#
#        Riferimento: docs/it/dev/work-in-progress/sviluppo-autorizzazioni-prezzi.md
def suggerisci_prezzo_riga(
    preventivo_id: int,
    *,
    articolo_id: str,
    uom_id: int,
    auth_user_id: int | None,
) -> dict[str, Any]:
    from apps.vendite.services.pricing_service import PricingService

    function_name = f"{_FN}.suggerisci_prezzo_riga"

    ErrorManager.require(
        articolo_id is not None and str(articolo_id).strip() != "",
        code="E_PREV_VALIDAZIONE",
        message="articolo_id obbligatorio.",
        function_name=function_name,
    )
    ErrorManager.require(
        uom_id is not None and isinstance(uom_id, int) and uom_id > 0,
        code="E_PREV_VALIDAZIONE",
        message="uom_id obbligatorio (intero positivo).",
        function_name=function_name,
    )
    ErrorManager.require(
        auth_user_id is not None,
        code="E_PREV_VALIDAZIONE",
        message="auth_user_id obbligatorio per risolvere l'emittente.",
        function_name=function_name,
    )

    repo = PreventiviRepository()
    testata = repo.get_preventivo(preventivo_id)
    ErrorManager.require(
        testata is not None,
        code="E_PREV_NOT_FOUND",
        message="Preventivo non trovato.",
        function_name=function_name,
    )
    assert testata is not None
    ErrorManager.require(
        testata.get("billing_account_id") is not None,
        code="E_PREV_VALIDAZIONE",
        message="Preventivo senza billing_account: impossibile risolvere il prezzo.",
        function_name=function_name,
    )
    ErrorManager.require(
        testata.get("utility_id") is not None,
        code="E_PREV_VALIDAZIONE",
        message="Preventivo senza utility: impossibile risolvere il prezzo.",
        function_name=function_name,
    )

    # Emittente dell'operatore: PermissionResolver ritorna lista (o None=admin).
    # Prendiamo il primo disponibile: per operatori 1-a-1 e' sempre univoco.
    user_model = get_user_model()
    try:
        user = user_model.objects.get(pk=auth_user_id)
    except user_model.DoesNotExist:
        ErrorManager.raise_error(
            code="E_PREV_VALIDAZIONE",
            message="Utente non trovato.",
            detail=f"auth_user_id={auth_user_id}",
            function_name=function_name,
        )
    emittenti_sr = PermissionResolver.get_emittenti_sr_ids(user) or []
    ErrorManager.require(
        len(emittenti_sr) > 0,
        code="E_PREV_VALIDAZIONE",
        message="Impossibile risolvere l'emittente fiscale dell'operatore.",
        detail="L'operatore non ha emittenti autorizzati.",
        function_name=function_name,
    )
    emittente_sr_id = int(emittenti_sr[0])

    # Data di riferimento: data del preventivo (il resolver la usa per
    # selezionare la versione listino attiva, il contratto nel periodo
    # corretto e le promo in vigore).
    data_riferimento_str = testata.get("data")
    ErrorManager.require(
        data_riferimento_str is not None,
        code="E_PREV_VALIDAZIONE",
        message="Preventivo senza data: impossibile risolvere il prezzo.",
        function_name=function_name,
    )
    assert data_riferimento_str is not None
    data_riferimento = date.fromisoformat(str(data_riferimento_str))

    # Delega al building block centrale. Gli errori di dominio
    # (E_PREZZO_LISTINO_NON_TROVATO ecc.) sono tradotti dal service
    # e propagati al chiamante come ServiceError.
    result = PricingService().resolve_prezzo(
        articolo_id=articolo_id,
        uom_id=int(uom_id),
        data_riferimento=data_riferimento,
        ba_id=int(testata["billing_account_id"]),
        utility_id=int(testata["utility_id"]),
        emittente_soggetto_ruolo_id=emittente_sr_id,
    )

    # Normalizzazione valori Decimal/date in stringhe per stabilita' JSON.
    from decimal import Decimal
    def _normalize(v: Any) -> Any:
        if isinstance(v, Decimal):
            return str(v)
        if isinstance(v, date):
            return v.isoformat()
        return v

    return {k: _normalize(v) for k, v in result.items()}


# Scopo: Elimina riga (soft delete) con guard su stato + ricalcolo totali.
def elimina_riga(preventivo_id: int, riga_id: int) -> dict[str, Any]:
    repo = PreventiviRepository()
    testata = repo.get_preventivo(preventivo_id)
    ErrorManager.require(
        testata is not None,
        code="E_PREV_NOT_FOUND",
        message="Preventivo non trovato.",
        function_name=f"{_FN}.elimina_riga",
    )
    assert testata is not None
    ErrorManager.require(
        testata["stato_codice_interno"] in _STATI_RIGHE_MODIFICABILI,
        code="E_PREV_STATO_NON_MODIFICABILE",
        message="Righe non eliminabili nello stato corrente.",
        function_name=f"{_FN}.elimina_riga",
    )

    deleted = repo.delete_riga(riga_id)
    ErrorManager.require(
        deleted,
        code="E_PREV_RIGA_NOT_FOUND",
        message="Riga preventivo non trovata.",
        function_name=f"{_FN}.elimina_riga",
    )
    # Ricalcolo totali gestito da trigger DB AFTER su preventivi_righe
    return {"status": "ok", "riga_id": riga_id}


# ══════════════════════════════════════════════════════════
#  INTEGRAZIONE — Commesse / Fatturazione
# ══════════════════════════════════════════════════════════


# Scopo: Push preventivo accettato in commessa per pipeline fatturazione.
# Obiettivo: guard stato ACCETTATO, discovery righe eleggibili, creazione/upsert commessa.
# Perimetro: invoca fn DB esistenti; idempotente via segment_key.
def push_a_commessa(preventivo_id: int) -> dict[str, Any]:
    repo = PreventiviRepository()
    testata = repo.get_preventivo(preventivo_id)
    ErrorManager.require(
        testata is not None,
        code="E_PREV_NOT_FOUND",
        message="Preventivo non trovato.",
        function_name=f"{_FN}.push_a_commessa",
    )
    assert testata is not None
    ErrorManager.require(
        testata["stato_codice_interno"] in _STATI_FATTURABILI,
        code="E_PREV_STATO_TRANSIZIONE",
        message="Solo preventivi ACCETTATI possono essere inviati a fatturazione.",
        detail=f"stato={testata['stato_codice_interno']}",
        function_name=f"{_FN}.push_a_commessa",
    )
    righe_count = repo.count_righe_pushable(preventivo_id)
    ErrorManager.require(
        righe_count > 0,
        code="E_PREV_NESSUNA_RIGA",
        message="Nessuna riga eleggibile per fatturazione.",
        detail=f"preventivo_id={preventivo_id}",
        function_name=f"{_FN}.push_a_commessa",
    )
    # TODO: invocare CommessePushOrchestrator per push singolo preventivo.
    # Per ora restituisce il conteggio righe eleggibili.
    return {"righe_pushable": righe_count, "preventivo_id": preventivo_id}


# Scopo: Stato fatturazione del preventivo nel pipeline downstream.
# Usa la vista aggregata vw_preventivi_stato_fatturazione (filtra per preventivo_id).
def stato_fatturazione(preventivo_id: int) -> dict[str, Any]:
    repo = PreventiviRepository()
    result = repo.stato_fatturazione(preventivo_id)
    if result is None:
        return {
            "preventivo_id": preventivo_id,
            "righe_totali": 0,
            "righe_in_commessa": 0,
            "righe_emesse_af": 0,
            "righe_fatturate": 0,
        }
    return result


# ══════════════════════════════════════════════════════════
#  INTEGRAZIONE — Pratiche
# ══════════════════════════════════════════════════════════


# Scopo: Genera pratica esecutiva da preventivo accettato.
# Obiettivo: guard stato, creazione pratica via BB pratiche_service.crea_pratica,
#   link via pratiche_sorgenti. Risolve contesto anagrafico dal preventivo/BA.
# Perimetro: crea pratica + link; non gestisce flussi (quelli si scelgono in UI pratica).
def genera_pratica(
    preventivo_id: int,
    tipo_prestazione_id: int,
    priorita_id: int,
    descrizione: str | None = None,
) -> dict[str, Any]:
    repo = PreventiviRepository()
    testata = repo.get_preventivo(preventivo_id)
    ErrorManager.require(
        testata is not None,
        code="E_PREV_NOT_FOUND",
        message="Preventivo non trovato.",
        function_name=f"{_FN}.genera_pratica",
    )
    assert testata is not None
    ErrorManager.require(
        testata["stato_codice_interno"] in _STATI_GENERA_PRATICA,
        code="E_PREV_PRATICA_STATO",
        message="Stato preventivo non ammette generazione pratica.",
        detail=f"stato={testata['stato_codice_interno']}",
        function_name=f"{_FN}.genera_pratica",
    )
    ErrorManager.require(
        testata["billing_account_id"] is not None,
        code="E_PREV_VALIDAZIONE",
        message="Preventivo senza billing account: impossibile derivare contesto pratica.",
        function_name=f"{_FN}.genera_pratica",
    )

    sorgente_tipo_id = repo.get_sorgente_tipo_preventivo_id()
    ErrorManager.require(
        sorgente_tipo_id is not None,
        code="E_CONFIG_MANCANTE",
        message="Tipo sorgente PREVENTIVO non configurato in config.sorgenti.",
        function_name=f"{_FN}.genera_pratica",
    )
    assert sorgente_tipo_id is not None

    # Risolve contesto anagrafico dal preventivo → BA → soggetto
    contesto = repo.resolve_contesto_pratica(preventivo_id)
    ErrorManager.require(
        contesto is not None,
        code="E_PREV_PRATICA_STATO",
        message="Impossibile derivare contesto anagrafico dal preventivo.",
        detail=f"preventivo_id={preventivo_id}",
        function_name=f"{_FN}.genera_pratica",
    )
    assert contesto is not None

    # Creazione pratica via building block pratiche_service.crea_pratica
    from apps.pratiche.services.pratiche_service import crea_pratica
    pratica_id = crea_pratica(
        emittente_fiscale_id=contesto["emittente_fiscale_id"],
        tipo_prestazione_id=tipo_prestazione_id,
        soggetto_id=contesto["soggetto_id"],
        soggetto_ruolo_id=contesto["soggetto_ruolo_id"],
        istanza_utility_id=testata["istanza_utility_id"],
        priorita_id=priorita_id,
        descrizione=descrizione,
    )

    # Link pratica → preventivo via pratiche_sorgenti
    repo.link_pratica(
        pratica_id=pratica_id,
        sorgente_tipo_id=sorgente_tipo_id,
        sorgente_uid=testata["uid"],
    )

    return {
        "pratica_id": pratica_id,
        "preventivo_id": preventivo_id,
    }


# Scopo: Lista pratiche collegate al preventivo.
# Usa la vista vw_preventivi_pratiche (filtra per preventivo_id).
def list_pratiche(preventivo_id: int) -> list[dict[str, Any]]:
    repo = PreventiviRepository()
    return repo.list_pratiche(preventivo_id)
