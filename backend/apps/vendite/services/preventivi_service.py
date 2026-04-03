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

from apps.core.services.error_manager import ErrorManager
from apps.core.services.value_normalizer import empty_to_none
from apps.vendite.db.preventivi_repository import PreventiviRepository
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
def gestisci_riga(preventivo_id: int, payload: dict[str, Any]) -> dict[str, Any]:
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

    result = repo.create_riga(
        preventivo_id=preventivo_id,
        articolo_id=articolo_id,
        descrizione=payload.get("descrizione"),
        quantita=payload.get("quantita"),
        qta_operativa=payload.get("qta_operativa"),
        uom_operativa_id=payload.get("uom_operativa_id"),
        factor_to_base=payload.get("factor_to_base"),
        prezzo_unitario=payload.get("prezzo_unitario"),
        sconto_percentuale=payload.get("sconto_percentuale"),
        iva_id=payload.get("iva_id"),
        ordine=payload.get("ordine"),
        meta=payload.get("meta"),
    )
    # Ricalcolo totali gestito da trigger DB AFTER su preventivi_righe
    return result


# Scopo: Aggiorna riga esistente con guard su stato + ricalcolo totali.
def aggiorna_riga(
    preventivo_id: int, riga_id: int, payload: dict[str, Any]
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
