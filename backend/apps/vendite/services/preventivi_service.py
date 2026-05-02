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
from decimal import ROUND_HALF_UP, Decimal
from typing import Any

from django.contrib.auth import get_user_model
from django.db import transaction

from apps.anagrafiche.db.billing_account_repository import BillingAccountRepository
from apps.anagrafiche.db.istanze_utility_repository import IstanzeUtilityRepository
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
    solo_revisione_attiva: bool = True,
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
        solo_revisione_attiva=solo_revisione_attiva,
        auth_user_id=auth_user_id,
        limit=page_size,
        offset=offset,
    )
    return paginated_envelope(results, total_count, page, page_size)


# Scopo: Dettaglio preventivo testata + summary + indirizzi + capabilities.
#        Le righe NON sono incluse: il FE le legge separatamente via
#        `GET /preventivi/<id>/righe/` (Fase 3.F6 refactor frontend vendite,
#        decisione C2). I totali_* sono nella testata via trigger DB; aggiungiamo
#        `righe_count` come summary leggero (badge UX). Le capability
#        (available_actions, can_edit_*, can_push_commessa, can_create_revisione,
#        non_editable_fields) sono calcolate da script.fn_available_actions_preventivo
#        e spalmate nel detail per consumo diretto dal frontend.
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
    indirizzi = repo.list_indirizzi(preventivo_id)
    capabilities = repo.get_capabilities(preventivo_id)
    # Summary leggero: numero righe totali (badge UX). Le righe vere passano
    # dall'endpoint /righe/ autonomo, evitando payload pesanti su lista detail
    # e mismatch coi totali ricalcolati dai trigger DB.
    righe_count = len(repo.list_righe(preventivo_id))
    return {
        **testata,
        **capabilities,
        "indirizzi": indirizzi,
        "righe_count": righe_count,
    }


# Scopo: Lista righe di un preventivo.
def list_righe(preventivo_id: int) -> list[dict[str, Any]]:
    repo = PreventiviRepository()
    return repo.list_righe(preventivo_id)


# Scopo: Riepilogo IVA aggregato del preventivo (una riga per aliquota +
#        eventuali natura/esigibilita/split). Calcolo fiscalmente corretto
#        gia' applicato in DB via fn_ricalcola_riepilogo_iva_preventivo:
#        il service legge la vista denormalizzata, nessun ricalcolo Python.
#        Usato dal FE per il pannello "Riepilogo IVA" del drawer preventivo
#        e (futuro) come builder per fatture emesse dal preventivo.
def list_riepilogo_iva(preventivo_id: int) -> list[dict[str, Any]]:
    repo = PreventiviRepository()
    return repo.list_riepilogo_iva(preventivo_id)


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
#
# Regole di dominio post brief DB rev2 (2026-05-01):
#  - utility_id obbligatorio
#  - istanza_utility_id obbligatorio (allinea preventivi al pattern di
#    commesse_attivita / attivita_fatturabili). Se il payload ha solo BA,
#    deriva istanza dal BA (FK NOT NULL su billing_account.istanza_utility_id).
#  - coerenza coppia (istanza_utility_id, utility_id) verificata pre-trigger
#    via script.fn_check_utility_istanza_coerenza per UX rapida con errore
#    parlante. Defense-in-depth: il trigger DB
#    trgfn_preventivi_guard_utility_istanza_coerenza applica la stessa regola.
#  - emittente_fiscale_id: opzionale nel payload. Se None il trigger DB
#    trgfn_preventivi_default_emittente lo valorizza da GUC app.current_user_id.
#    Specificarlo esplicito solo per admin globale (utente senza emittente
#    assegnato che sceglie l'emittente del documento).
def crea_preventivo(payload: dict[str, Any]) -> dict[str, Any]:
    repo = PreventiviRepository()
    ba_repo = BillingAccountRepository()
    iu_repo = IstanzeUtilityRepository()

    utility_id = payload.get("utility_id")
    ErrorManager.require(
        utility_id is not None,
        code="E_PREV_VALIDAZIONE",
        message="utility_id obbligatorio.",
        function_name=f"{_FN}.crea_preventivo",
    )

    billing_account_id = payload.get("billing_account_id")
    istanza_utility_id = payload.get("istanza_utility_id")

    # Conveniencia: se BA presente ma istanza no, deriva istanza dal BA.
    # Permette al FE di non duplicare l'informazione quando seleziona il BA.
    if billing_account_id is not None and istanza_utility_id is None:
        istanza_utility_id = ba_repo.get_istanza_utility_id(int(billing_account_id))
        ErrorManager.require(
            istanza_utility_id is not None,
            code="E_PREV_VALIDAZIONE",
            message="Billing account non trovato.",
            detail=f"billing_account_id={billing_account_id}",
            function_name=f"{_FN}.crea_preventivo",
        )

    # Istanza obbligatoria (regola dominio post landing DB rev2).
    ErrorManager.require(
        istanza_utility_id is not None,
        code="E_PREV_VALIDAZIONE",
        message="istanza_utility_id obbligatorio.",
        detail=(
            "Specificare l'istanza utility (direttamente o via billing account)."
        ),
        function_name=f"{_FN}.crea_preventivo",
    )
    assert istanza_utility_id is not None

    # Pre-check coerenza utility/istanza: errore parlante prima del trigger DB.
    coerente = iu_repo.check_utility_istanza_coerenza(
        int(istanza_utility_id), int(utility_id),
    )
    ErrorManager.require(
        coerente,
        code="E_PREV_UTILITY_ISTANZA_INCOERENTE",
        message="Utility non coerente con l'istanza selezionata.",
        detail=(
            f"istanza_utility_id={istanza_utility_id} non e' dichiarata "
            f"per utility_id={utility_id} (no billing account, dati "
            "precontrattuali o cliente matching)."
        ),
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
        billing_account_id=billing_account_id,
        utility_id=utility_id,
        istanza_utility_id=istanza_utility_id,
        emittente_fiscale_id=payload.get("emittente_fiscale_id"),
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


# Scopo: Elimina (hard-delete) preventivo BOZZA orfano.
# Obiettivo: supporto al pattern "abbandono bozza" del drawer FE — quando
# l'operatore apre create, si crea automaticamente la BOZZA per abilitare
# subito l'inserimento righe (master-detail inline), ma esce senza inserire
# righe. La BOZZA orfana viene cancellata su conferma utente.
#
# Guard di dominio (defense-in-depth: il caller FE filtra gia' su righe_count=0,
# qui ricontrolliamo per sicurezza):
#  - preventivo deve esistere
#  - stato == BOZZA (DRAFT)
#  - zero righe attive
#  - zero pratiche collegate
# Non ammessa per preventivi gia' propagati a commessa o con stato avanzato:
# in quei casi la "cancellazione" semantica e' cambia_stato → ANNULLATO.
def elimina_preventivo(preventivo_id: int) -> dict[str, Any]:
    repo = PreventiviRepository()
    testata = repo.get_preventivo(preventivo_id)
    ErrorManager.require(
        testata is not None,
        code="E_PREV_NOT_FOUND",
        message="Preventivo non trovato.",
        detail=f"preventivo_id={preventivo_id}",
        function_name=f"{_FN}.elimina_preventivo",
    )
    assert testata is not None
    # Eliminabili solo i preventivi nello stesso stato in cui sono modificabili
    # (BOZZA / DRAFT). Qualsiasi stato successivo (EMESSO/ACCETTATO/...) richiede
    # cambia_stato → ANNULLATO invece dell'hard-delete.
    ErrorManager.require(
        testata["stato_codice_interno"] in _STATI_MODIFICABILI,
        code="E_PREV_STATO_NON_MODIFICABILE",
        message="Solo i preventivi in stato BOZZA possono essere eliminati.",
        detail=f"stato={testata['stato_codice_interno']}",
        function_name=f"{_FN}.elimina_preventivo",
    )
    righe_count = len(repo.list_righe(preventivo_id))
    ErrorManager.require(
        righe_count == 0,
        code="E_PREV_STATO_NON_MODIFICABILE",
        message="Impossibile eliminare un preventivo con righe. Eliminare prima le righe.",
        detail=f"righe_count={righe_count}",
        function_name=f"{_FN}.elimina_preventivo",
    )
    pratiche_count = len(repo.list_pratiche(preventivo_id))
    ErrorManager.require(
        pratiche_count == 0,
        code="E_PREV_STATO_NON_MODIFICABILE",
        message="Impossibile eliminare un preventivo con pratiche collegate.",
        detail=f"pratiche_count={pratiche_count}",
        function_name=f"{_FN}.elimina_preventivo",
    )
    deleted = repo.delete_preventivo(preventivo_id)
    return {"status": "ok" if deleted else "noop", "preventivo_id": preventivo_id}


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

    # Campi aggiornabili in BOZZA. utility_id e' immutabile per regola di
    # dominio (vedi script.fn_available_actions_preventivo: non_editable_fields
    # include sempre utility_id) e quindi NON e' nella whitelist: per cambiarla
    # serve creare un nuovo preventivo.
    update_fields: dict[str, Any] = {}
    for key in (
        "billing_account_id", "istanza_utility_id",
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
#
# Caso speciale EMESSO → ACCETTATO (transizione "accettazione"):
#   l'operatore deve specificare la modalita' di fatturazione del preventivo
#   (proprieta' di processo, NON visibili in form testata BOZZA — vedi
#   sviluppo-preventivi.md). Parametri:
#     - fatturazione_immediata (bool obbligatorio)
#     - competenza_mese (date YYYY-MM-01, obbligatorio se immediata=False)
#   Regola di priorita': se immediata=True → competenza_mese forzata a oggi
#   (primo del mese corrente), il valore eventuale passato dal caller viene
#   ignorato. Per ora la regola e' applicata qui (BE service); future
#   defense-in-depth via trigger DB se servira'.
#
# Le altre transizioni (DRAFT→EMESSO, EMESSO→RIFIUTATO, *→ANNULLATO, ...)
# ignorano i 2 parametri.
def cambia_stato(
    preventivo_id: int,
    nuovo_stato: str,
    *,
    fatturazione_immediata: bool | None = None,
    competenza_mese: date | None = None,
) -> dict[str, Any]:
    repo = PreventiviRepository()

    # Gate accettazione: applichiamo la regola SOLO sulla transizione
    # EMESSO → ACCETTATO. Su ACCETTATO → ACCETTATO (no-op stato) consentiamo
    # update dei 2 campi finche' il preventivo e' fatturabile (vedi
    # _STATI_FATTURABILI). Su altre transizioni i parametri sono ignorati.
    if nuovo_stato == "ACCETTATO":
        testata = repo.get_preventivo(preventivo_id)
        ErrorManager.require(
            testata is not None,
            code="E_PREV_NOT_FOUND",
            message="Preventivo non trovato.",
            detail=f"preventivo_id={preventivo_id}",
            function_name=f"{_FN}.cambia_stato",
        )
        assert testata is not None
        stato_attuale = testata["stato_codice_interno"]
        # Solo EMESSO → ACCETTATO (e ACCETTATO no-op) richiedono i parametri.
        if stato_attuale in ("EMESSO", "ACCETTATO"):
            ErrorManager.require(
                fatturazione_immediata is not None,
                code="E_PREV_VALIDAZIONE",
                message="Modalita' di fatturazione obbligatoria per accettare il preventivo.",
                detail="fatturazione_immediata: bool obbligatorio.",
                function_name=f"{_FN}.cambia_stato",
            )
            # Regola di priorita': immediata=True ⇒ competenza = primo giorno
            # del mese corrente (snapshot tx-time). Eventuale valore esplicito
            # passato dal caller viene sovrascritto (immediata ha priorita').
            if fatturazione_immediata:
                competenza_mese = date.today().replace(day=1)
            else:
                ErrorManager.require(
                    competenza_mese is not None,
                    code="E_PREV_VALIDAZIONE",
                    message=(
                        "Mese di competenza obbligatorio quando fatturazione "
                        "non e' immediata."
                    ),
                    function_name=f"{_FN}.cambia_stato",
                )
            # Update testata PRIMA del cambio stato, in transazione atomica
            # di cambia_stato (la fn DB sotto e' atomic per natura: un solo
            # statement INSERT/UPDATE con trigger). Per multi-statement
            # atomic serve transaction.atomic, ma qui sono 2 UPDATE
            # consecutivi: avvolgiamo entrambe.
            with transaction.atomic():
                repo.update_preventivo(
                    preventivo_id,
                    fatturazione_immediata=bool(fatturazione_immediata),
                    competenza_mese=competenza_mese,
                )
                result = repo.cambia_stato(preventivo_id, nuovo_stato, "django_api")
            return result

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
#
#        L3 (Sprint E): se payload contiene `richiesta_approvazione=true`
#        e il prezzo viola L2, la riga viene salvata con
#        `stato_approvazione_prezzo='PENDING'` collegata a una pratica
#        di approvazione (workflow vendite §14.6) invece di sollevare errore.
@transaction.atomic
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

    # Validazione vincoli economici (prezzo >= 0, quantita > 0) prima del
    # resolver: anticipa i CHECK DB con messaggio parlante.
    _validate_riga_economic(payload, function_name=f"{_FN}.gestisci_riga")

    uom_id = payload.get("uom_operativa_id")
    payload_prezzo = payload.get("prezzo_unitario")
    richiesta_approvazione = bool(payload.get("richiesta_approvazione", False))
    prezzo_finale, prezzo_meta = _resolve_or_check_override_prezzo(
        testata=testata,
        articolo_id=articolo_id,
        uom_id=uom_id,
        payload_prezzo=payload_prezzo,
        auth_user_id=auth_user_id,
        function_name=f"{_FN}.gestisci_riga",
        richiesta_approvazione=richiesta_approvazione,
    )

    # Merge meta esistente del payload con audit prezzo.
    merged_meta = dict(payload.get("meta") or {})
    if prezzo_meta is not None:
        merged_meta.update(prezzo_meta)

    # Workflow L3: se la chiamata ha attivato richiesta_approvazione e il
    # prezzo viola L2, crea la pratica PRIMA dell'INSERT riga per ottenere
    # pratica_id da inserire come FK. Tutto in transazione atomica del
    # decorator: failure post-pratica annulla anche la riga.
    pratica_id_l3: int | None = None
    stato_approvazione: str | None = None
    if prezzo_meta and prezzo_meta.get("richiesta_approvazione_pending"):
        pratica_id_l3 = _orchestrate_l3_request(
            preventivo_id=preventivo_id,
            articolo_id=articolo_id,
            prezzo_finale=prezzo_finale,
            prezzo_meta=prezzo_meta,
            auth_user_id=auth_user_id,
            # riga_id non noto: link post-create_riga.
        )
        stato_approvazione = "PENDING"

    # Derivazione qta_operativa + factor_to_base: il FE invia solo `quantita`
    # (UX semplice: una sola quantita' per riga). Il DB richiede pero'
    # qta_operativa NOT NULL (guard E_QTA_MISSING) come quantita' nell'UoM
    # base, derivata dalla UoM operativa scelta. Lookup factor_to_base su
    # catalogo.articoli_uom_operativa; default 1 se la UoM non e' mappata
    # (caso edge: articolo con sola UoM base).
    qta_operativa, factor_to_base = _derive_qta_operativa(
        repo=repo,
        articolo_id=articolo_id,
        uom_id=uom_id,
        quantita=payload.get("quantita"),
        qta_operativa_payload=payload.get("qta_operativa"),
        factor_to_base_payload=payload.get("factor_to_base"),
    )

    result = repo.create_riga(
        preventivo_id=preventivo_id,
        articolo_id=articolo_id,
        descrizione=payload.get("descrizione"),
        quantita=payload.get("quantita"),
        qta_operativa=qta_operativa,
        uom_operativa_id=uom_id,
        factor_to_base=factor_to_base,
        prezzo_unitario=prezzo_finale,
        sconto_percentuale=payload.get("sconto_percentuale"),
        iva_id=payload.get("iva_id"),
        ordine=payload.get("ordine"),
        meta=merged_meta or None,
        stato_approvazione_prezzo=stato_approvazione,
        pratica_approvazione_prezzo_id=pratica_id_l3,
    )
    # L3: registra riga_id nel meta della pratica per permettere all'approver
    # di risalire alla riga dalla coda (UI ApprovazioniPrezzoListView).
    # Update post-create_riga: la pratica esisteva gia' ma riga_id non era noto.
    if pratica_id_l3 is not None and result.get("id"):
        from apps.vendite.services.approvazioni_prezzo_service import (
            link_riga_a_pratica,
        )
        link_riga_a_pratica(pratica_id=pratica_id_l3, riga_id=int(result["id"]))
    # Ricalcolo totali gestito da trigger DB AFTER su preventivi_righe
    return result


# Note: gestisci_riga e aggiorna_riga condividono la fase di orchestrazione
# L3 (creazione pratica + salvataggio PENDING). Per la create il pratica_id
# viene ottenuto PRIMA di create_riga (FK necessaria) e il link riga<->pratica
# avviene DOPO (riga_id non noto prima dell'insert). Per la update il
# riga_id e' gia' noto: link_riga_a_pratica puo' essere invocato subito.
# Vedi _orchestrate_l3_request sopra.


# Scopo: Aggiorna riga esistente con guard su stato + ricalcolo totali.
#        L1 override prezzo: se il payload modifica `prezzo_unitario`,
#        verifica che il valore passato sia il prezzo resolver o che
#        l'operatore abbia permesso di override (azione
#        `prezzo_override_manuale`). La verifica viene fatta solo se
#        `prezzo_unitario` e' esplicitamente nel payload (campo modificato).
#
#        L3 (Sprint E): se payload contiene `richiesta_approvazione=true`
#        e il nuovo prezzo viola L2, la riga viene aggiornata con
#        `stato_approvazione_prezzo='PENDING'` e collegata a una pratica
#        di approvazione. Una riga gia' PENDING e' bloccata dal trigger DB
#        (DB-E-5): l'admin deve attendere esito o annullare la richiesta.
@transaction.atomic
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

    # Validazione vincoli economici: anticipa i CHECK DB con messaggio
    # parlante. In update i campi possono essere assenti: il helper li
    # ignora se non presenti nel payload.
    _validate_riga_economic(payload, function_name=f"{_FN}.aggiorna_riga")

    richiesta_approvazione = bool(payload.get("richiesta_approvazione", False))
    update_fields: dict[str, Any] = {}
    for key in (
        "descrizione", "quantita", "qta_operativa", "uom_operativa_id",
        "factor_to_base", "prezzo_unitario", "sconto_percentuale",
        "iva_id", "ordine", "meta",
    ):
        if key in payload:
            update_fields[key] = payload[key]

    pratica_id_l3: int | None = None

    # Riga esistente — fetch lazy condiviso tra blocco prezzo e blocco quantita
    # per evitare 2 round-trip DB quando entrambi i campi sono nel payload.
    # None = non ancora fetchata, False = fetchata e non trovata.
    riga_esistente: dict[str, Any] | None | bool = None

    def _get_riga_esistente() -> dict[str, Any]:
        nonlocal riga_esistente
        if riga_esistente is None:
            righe = repo.list_righe(preventivo_id)
            riga_esistente = next((r for r in righe if r.get("id") == riga_id), False)
        ErrorManager.require(
            riga_esistente is not False,
            code="E_PREV_RIGA_NOT_FOUND",
            message="Riga preventivo non trovata.",
            detail=f"riga_id={riga_id}",
            function_name=f"{_FN}.aggiorna_riga",
        )
        return riga_esistente  # type: ignore[return-value]

    # L1 check + audit meta se prezzo toccato esplicitamente. Serve contesto
    # riga esistente per articolo_id/uom_id non sempre presenti nel payload.
    if "prezzo_unitario" in update_fields:
        riga_esistente = _get_riga_esistente()
        articolo_id = riga_esistente["articolo_id"]
        uom_id = update_fields.get("uom_operativa_id") or riga_esistente.get("uom_operativa_id")
        prezzo_finale, prezzo_meta = _resolve_or_check_override_prezzo(
            testata=testata,
            articolo_id=articolo_id,
            uom_id=uom_id,
            payload_prezzo=update_fields["prezzo_unitario"],
            auth_user_id=auth_user_id,
            function_name=f"{_FN}.aggiorna_riga",
            richiesta_approvazione=richiesta_approvazione,
        )
        update_fields["prezzo_unitario"] = prezzo_finale
        if prezzo_meta is not None:
            merged_meta = dict(update_fields.get("meta") or riga_esistente.get("meta") or {})
            merged_meta.update(prezzo_meta)
            update_fields["meta"] = merged_meta

        # Workflow L3: violazione L2 + flag richiesta_approvazione=true
        # -> crea pratica e salva PENDING. Helper condiviso con gestisci_riga.
        # Per update il riga_id e' gia' noto: link riga<->pratica eseguito dentro l'helper.
        if prezzo_meta and prezzo_meta.get("richiesta_approvazione_pending"):
            pratica_id_l3 = _orchestrate_l3_request(
                preventivo_id=preventivo_id,
                articolo_id=articolo_id,
                prezzo_finale=prezzo_finale,
                prezzo_meta=prezzo_meta,
                auth_user_id=auth_user_id,
                riga_id_for_link=riga_id,
            )
            update_fields["stato_approvazione_prezzo"] = "PENDING"
            update_fields["pratica_approvazione_prezzo_id"] = pratica_id_l3

    # Coerenza qta_operativa quando l'utente cambia `quantita` in edit
    # senza mandare qta_operativa: ricalcolo dalla UoM operativa della
    # riga esistente (o nuova, se l'edit la sta cambiando insieme).
    # Stesso pattern di gestisci_riga (helper _derive_qta_operativa).
    # Riusa `_get_riga_esistente()`: lazy + cache nella stessa transazione.
    if (
        "quantita" in update_fields
        and "qta_operativa" not in update_fields
    ):
        # Fallback per articolo + UoM solo se NON nel payload (caso normale:
        # edit modifica solo prezzo/quantita'). Evita fetch inutile quando
        # il payload li esplicita gia'.
        if "articolo_id" not in update_fields or "uom_operativa_id" not in update_fields:
            ref_riga = _get_riga_esistente()
        else:
            ref_riga = {}
        articolo_id_eff = update_fields.get("articolo_id") or ref_riga.get("articolo_id")
        uom_id_eff = update_fields.get("uom_operativa_id") or ref_riga.get("uom_operativa_id")
        qta_op, factor_eff = _derive_qta_operativa(
            repo=repo,
            articolo_id=articolo_id_eff,
            uom_id=uom_id_eff,
            quantita=update_fields["quantita"],
            qta_operativa_payload=None,
            factor_to_base_payload=update_fields.get("factor_to_base"),
        )
        if qta_op is not None:
            update_fields["qta_operativa"] = qta_op
        if "factor_to_base" not in update_fields and factor_eff is not None:
            update_fields["factor_to_base"] = factor_eff

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

    # Nota: il link riga<->pratica e' gia' stato eseguito dentro
    # _orchestrate_l3_request (riga_id_for_link=riga_id).

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
# Scopo: orchestra la creazione pratica L3 + link riga<->pratica per i flussi
#        di gestisci_riga e aggiorna_riga. Centralizza l'unica logica
#        Sprint E condivisa tra create e update riga (stessa transazione
#        atomica del chiamante: failure annulla anche la riga).
#
#        Restituisce pratica_id (per inserimento FK in create_riga).
#        Per update_riga, riga_id e' gia' noto: passare apply_link=True
#        per fare update meta pratica con riga_preventivo_id.
def _orchestrate_l3_request(
    *,
    preventivo_id: int,
    articolo_id: Any,
    prezzo_finale: Any,
    prezzo_meta: dict[str, Any],
    auth_user_id: int | None,
    riga_id_for_link: int | None = None,
) -> int:
    from apps.vendite.services.approvazioni_prezzo_service import (
        crea_richiesta_approvazione,
        link_riga_a_pratica,
    )
    pratica_id = crea_richiesta_approvazione(
        preventivo_id=preventivo_id,
        articolo_id=str(articolo_id),
        prezzo_resolver=Decimal(prezzo_meta["prezzo_base_resolver"])
        if prezzo_meta.get("prezzo_base_resolver") else None,
        prezzo_manuale=Decimal(str(prezzo_finale)),
        violazione=prezzo_meta["violazione_l2"],
        auth_user_id=auth_user_id,
    )
    if riga_id_for_link is not None:
        link_riga_a_pratica(pratica_id=pratica_id, riga_id=riga_id_for_link)
    return pratica_id


# Scopo: Deriva qta_operativa + factor_to_base dalla UoM operativa selezionata
#        quando il payload FE non li espone. Pattern: il FE invia solo `quantita`
#        nell'UoM scelta dall'operatore; il BE consulta il fattore di conversione
#        UoM-operativa -> UoM-base e calcola la quantita' nell'UoM base.
#        Output: tupla (qta_operativa, factor_to_base) come stringhe Decimal-safe.
#        Pass-through dei valori payload se gia' valorizzati (rispetto override).
def _derive_qta_operativa(
    *,
    repo: "PreventiviRepository",
    articolo_id: Any,
    uom_id: Any,
    quantita: Any,
    qta_operativa_payload: Any,
    factor_to_base_payload: Any,
) -> tuple[Any, Any]:
    from decimal import Decimal

    # Pass-through: se il payload li espone, niente lookup.
    if qta_operativa_payload is not None and factor_to_base_payload is not None:
        return qta_operativa_payload, factor_to_base_payload

    # Senza articolo+uom o senza quantita non possiamo derivare nulla:
    # ritorna i valori payload (None) e lascia che la guard DB sollevi
    # un errore parlante (E_QTA_MISSING / E_UOM_MISSING).
    if not articolo_id or not uom_id or quantita is None:
        return qta_operativa_payload, factor_to_base_payload

    factor_db = repo.get_articolo_uom_factor(str(articolo_id), int(uom_id))
    # Articolo senza UoM operativa mappata (edge case): assumiamo factor=1
    # cosi' qta_operativa = quantita. La guard DB sull'esistenza UoM e' altrove.
    factor = Decimal(str(factor_db)) if factor_db is not None else Decimal("1")
    factor_str = factor_to_base_payload if factor_to_base_payload is not None else str(factor)
    if qta_operativa_payload is not None:
        return qta_operativa_payload, factor_str
    qta_op = Decimal(str(quantita)) * factor
    return str(qta_op), factor_str


# Scopo: Validazione lato BE dei vincoli economici di una riga preventivo
#        prima del resolver/INSERT/UPDATE. Anticipa i CHECK constraint DB
#        (`chk_prevrighe_quantita_prezzo`: prezzo >= 0 AND quantita > 0)
#        per restituire un errore parlante invece dell'E_DATABASE generico
#        che il middleware mostrerebbe sul violation Postgres.
#        Chiamata sia da gestisci_riga (create) sia da aggiorna_riga (update).
#        Salta i campi assenti dal payload: in update non tutti i campi
#        passano sempre.
def _validate_riga_economic(payload: dict[str, Any], *, function_name: str) -> None:
    if "prezzo_unitario" in payload and payload["prezzo_unitario"] is not None:
        try:
            prezzo = Decimal(str(payload["prezzo_unitario"]))
        except Exception:
            ErrorManager.raise_error(
                code="E_PREV_VALIDAZIONE",
                message="Prezzo unitario non numerico.",
                detail=f"prezzo_unitario={payload['prezzo_unitario']!r}",
                function_name=function_name,
            )
            raise AssertionError("unreachable")  # pragma: no cover
        ErrorManager.require(
            prezzo >= 0,
            code="E_PREV_VALIDAZIONE",
            message="Il prezzo unitario non puo' essere negativo.",
            detail=f"prezzo_unitario={payload['prezzo_unitario']!r}",
            function_name=function_name,
        )

    if "quantita" in payload and payload["quantita"] is not None:
        try:
            quantita = Decimal(str(payload["quantita"]))
        except Exception:
            ErrorManager.raise_error(
                code="E_PREV_VALIDAZIONE",
                message="Quantita' non numerica.",
                detail=f"quantita={payload['quantita']!r}",
                function_name=function_name,
            )
            raise AssertionError("unreachable")  # pragma: no cover
        ErrorManager.require(
            quantita > 0,
            code="E_PREV_VALIDAZIONE",
            message="La quantita' deve essere maggiore di zero.",
            detail=f"quantita={payload['quantita']!r}",
            function_name=function_name,
        )


def _resolve_or_check_override_prezzo(
    *,
    testata: dict[str, Any],
    articolo_id: Any,
    uom_id: Any,
    payload_prezzo: Any,
    auth_user_id: int | None,
    function_name: str,
    richiesta_approvazione: bool = False,
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
    #
    # Savepoint annidato (transaction.atomic interno): le `RAISE EXCEPTION`
    # dentro fn_resolve_prezzo_listino_v2 marcano la tx PostgreSQL come
    # aborted; senza savepoint l'INSERT di create_riga fallirebbe con
    # InFailedSqlTransaction → mascherato in E_DATABASE generico. Il
    # savepoint isola l'errore e mantiene integra la tx esterna.
    prezzo_resolver: Decimal | None = None
    resolver_context: dict[str, Any] | None = None
    try:
        with transaction.atomic():
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

    # Confronto con tolleranza: il resolver ritorna prezzo a 10 decimali
    # (max_digits=22, decimal_places=10), ma il round-trip BE -> JSON ->
    # JS Number (53-bit float, ~15-17 cifre significative) -> InputNumber
    # mode="currency" -> JSON -> BE perde precisione sull'ultima cifra.
    # Quantizziamo entrambi a 4 decimali (precisione abbondante per prezzi
    # commerciali EUR) per il confronto: se uguali, salviamo il prezzo
    # resolver originale (full precision) — il valore "che l'utente vede"
    # era gia' un'approssimazione del valore canonico DB.
    _PRICE_COMPARE_QUANTIZE = Decimal("0.0001")
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
    _check_permesso_override_prezzo(auth_user_id, function_name=function_name)

    # L2: limite percentuale sconto/maggiorazione (autorizzazioni prezzi Sprint D).
    # Se resolver non ha prezzo o e' 0 skip (non calcolabile); altrimenti
    # confronta delta_pct firmato con il parametro appropriato risolto per
    # l'utente (default 0 = nessuna variazione ammessa).
    # L3 (Sprint E): se chiamante chiede richiesta_approvazione, l'eventuale
    # violazione non solleva ma ritorna dict; il chiamante orchestrera'
    # la creazione pratica.
    violazione_l2 = _check_limite_variazione_prezzo(
        auth_user_id=auth_user_id,
        prezzo_resolver=prezzo_resolver,
        prezzo_manuale=payload_decimal,
        function_name=function_name,
        accept_for_approval=richiesta_approvazione,
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

    # Hook L3: violazione L2 in modalita' "richiesta approvazione" -> segnala
    # al chiamante per orchestrazione pratica + salvataggio riga PENDING.
    if violazione_l2 is not None:
        meta_patch["richiesta_approvazione_pending"] = True
        meta_patch["violazione_l2"] = violazione_l2

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
#
#        Restituisce:
#          - None se variazione entro limite (caso normale L2 OK)
#          - dict {tipo_violazione, variazione_abs_pct, limite_pct} se
#            violazione + accept_for_approval=True (workflow L3 Sprint E)
#
#        Solleva ServiceError L2 (E_PREV_SCONTO_ECCESSIVO /
#        E_PREV_MAGGIORAZIONE_ECCESSIVA) se violazione + accept_for_approval=False.
def _check_limite_variazione_prezzo(
    *,
    auth_user_id: int | None,
    prezzo_resolver,  # Decimal | None
    prezzo_manuale,   # Decimal
    function_name: str,
    accept_for_approval: bool = False,
) -> dict[str, Any] | None:
    from decimal import Decimal

    if prezzo_resolver is None or prezzo_resolver == 0:
        return None  # Nessun riferimento per calcolare la percentuale.

    if auth_user_id is None:
        return None  # L1 ha gia' bloccato; unreachable difensivo.

    user_model = get_user_model()
    try:
        user = user_model.objects.get(pk=auth_user_id)
    except user_model.DoesNotExist:
        return None  # L1 avrebbe gia' bloccato.
    if getattr(user, "is_superuser", False):
        return None

    delta = prezzo_manuale - prezzo_resolver
    if delta == 0:
        return None  # Edge case: L1 avrebbe gia' fatto early-return.

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
        return None

    # Violazione L2. Se la chiamata e' nel contesto di richiesta approvazione
    # L3, restituiamo i dettagli della violazione invece di sollevare:
    # il chiamante orchestrera' la creazione della pratica.
    kind_label = "Sconto" if is_sconto else "Maggiorazione"
    if accept_for_approval:
        return {
            "tipo_violazione": "SCONTO" if is_sconto else "MAGGIORAZIONE",
            "variazione_abs_pct": str(variazione_abs.quantize(Decimal("0.01"))),
            "limite_pct": str(limite),
            "kind_label": kind_label,
        }

    # Caso normale L2: solleva errore (FE banner attiva pulsante "richiedi
    # approvazione" che ri-tentera' con accept_for_approval=True).
    # Fase 5.B2: retryable=True esplicito → semantica "puoi riprovare con
    # flag richiesta_approvazione=true" (workflow L3). L1
    # E_PREV_OVERRIDE_NON_AUTORIZZATO resta retryable=False (default ServiceError):
    # senza permesso prezzo_override_manuale non c'e' niente da ritentare.
    error_code = "E_PREV_SCONTO_ECCESSIVO" if is_sconto else "E_PREV_MAGGIORAZIONE_ECCESSIVA"
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
