# ------------------------------------------------------------
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2025 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Facade applicativa per preventivi vendita (CRUD, stato, righe, integrazione).
# ------------------------------------------------------------

# Orchestrazione preventivi vendita: validazione, guard su stato,
# delega a repository per accesso DB, gestione transizioni e integrazione
# con commesse e pratiche.

import json
import logging
from datetime import date
from decimal import ROUND_HALF_UP, Decimal, InvalidOperation
from typing import Any

from django.contrib.auth import get_user_model
from django.contrib.auth.models import AbstractBaseUser, AnonymousUser
from django.db import DatabaseError, transaction

from apps.anagrafiche.db.billing_account_repository import BillingAccountRepository
from apps.anagrafiche.db.istanze_utility_repository import IstanzeUtilityRepository
from apps.core.services.error_manager import ErrorManager
from apps.core.services.parameter_service import ParameterService
from apps.core.services.permissions_resolver import PermissionResolver
from apps.core.services.value_normalizer import empty_to_none
from apps.documenti.db.documenti_repository import DocumentiRepository
from apps.documenti.services.document_generation_service import (
    DocumentGenerationService,
)
from apps.vendite.db.preventivi_repository import PreventiviRepository
from apps.vendite.services._approvazioni_prezzo_constants import (
    AZIONE_OVERRIDE_PREZZO,
    STATO_APPROVAZIONE_APPROVED,
    STATO_APPROVAZIONE_PENDING,
    STATO_APPROVAZIONE_REJECTED,
)
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

# Codice sorgente PREVENTIVO in `config.sorgenti` — usato dal motore
# documentale per scegliere il template e tracciare l'origine del PDF.
# Coerente con la stessa costante in `preventivi_documenti_views`.
_CODICE_SORGENTE_PREVENTIVO = "PREVENTIVO"


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
    # Summary leggero: count per stato_approvazione_prezzo + totale, single
    # SELECT GROUP BY (no scan dell'elenco righe completo). Le righe vere
    # passano dall'endpoint /righe/ autonomo, evitando payload pesanti su
    # lista detail e mismatch coi totali ricalcolati dai trigger DB.
    counts = repo.count_righe_per_stato_approvazione(preventivo_id)
    righe_count = counts["TOTAL"]
    # Sprint E (autorizzazioni prezzi L3): se almeno una riga e' in stato
    # PENDING o REJECTED, il preventivo e' "congelato" — niente transizioni
    # di avanzamento (Emetti/Accetta) e niente edit testata. Razionale:
    #  - PENDING → richiesta in attesa di esito, non si puo' avanzare
    #  - REJECTED → il responsabile ha rifiutato il prezzo: il prezzo
    #    proposto e' invalidato, l'operatore deve correggere la riga
    #    (modificarne il prezzo o eliminarla) prima di poter procedere.
    #    L'edit della singola riga resta abilitato (can_edit_righe=true)
    #    proprio per permettere la correzione: l'aggiorna_riga al nuovo
    #    prezzo accettabile resetta automaticamente il flag REJECTED → null
    #    e il preventivo torna lavorabile.
    # Defense-in-depth: cambia_stato_preventivo solleva
    # E_PREVENTIVO_RIGHE_PRICING_PENDENTI; qui filtriamo le capability
    # spedite al FE per disabilitare i pulsanti a monte (UX).
    pending_count = counts[STATO_APPROVAZIONE_PENDING]
    rejected_count = counts[STATO_APPROVAZIONE_REJECTED]
    if pending_count > 0 or rejected_count > 0:
        capabilities = {
            **capabilities,
            "available_actions": [],
            "can_edit_testata": False,
            # can_edit_righe RESTA TRUE quando ci sono solo REJECTED:
            # l'operatore deve poter correggere il prezzo o eliminare la
            # riga rifiutata. Lo blocchiamo solo per PENDING (in attesa
            # esito: defense-in-depth replica trgfn DB lato preventivi_righe).
            "can_edit_righe": rejected_count > 0 and pending_count == 0,
            "frozen_for_pending_pricing": pending_count > 0,
            "frozen_for_rejected_pricing": rejected_count > 0,
            "pending_pricing_count": pending_count,
            "rejected_pricing_count": rejected_count,
        }
    else:
        capabilities = {
            **capabilities,
            "frozen_for_pending_pricing": False,
            "frozen_for_rejected_pricing": False,
            "pending_pricing_count": 0,
            "rejected_pricing_count": 0,
        }
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
    user: AbstractBaseUser | AnonymousUser | None = None,
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

    # Hook atomico emissione: la transizione *->EMESSO genera il PDF
    # canonico v1 nella stessa transazione del cambio stato. Se il
    # rendering fallisce (template/versione invalida, builder fail, ...)
    # l'eccezione propaga -> rollback totale -> il preventivo resta nello
    # stato precedente. Invariante: EMESSO => almeno una versione PDF
    # esiste in documenti.documenti_generati.
    if nuovo_stato == "EMESSO":
        with transaction.atomic():
            result = repo.cambia_stato(preventivo_id, nuovo_stato, "django_api")
            _genera_pdf_emissione(preventivo_id, user=user)
        return result

    result = repo.cambia_stato(preventivo_id, nuovo_stato, "django_api")
    return result


# Scopo: Genera e persiste il PDF canonico del preventivo emesso (v1
#        della numerazione `progressivo_sorgente`). Chiamato dentro la
#        transazione di `cambia_stato` quando lo stato passa a EMESSO:
#        un fallimento solleva ServiceError che rollbacka l'intera
#        transizione di stato. Su rigenerazioni successive (in stato
#        EMESSO, click utente sul pulsante PDF) il caller chiama
#        direttamente `DocumentGenerationService.genera_documento` via
#        l'endpoint dedicato `ApiPreventivoDocumentoGenera`: questa
#        funzione e' specifica per il bootstrap one-shot all'emissione.
def _genera_pdf_emissione(
    preventivo_id: int,
    *,
    user: AbstractBaseUser | AnonymousUser | None,
) -> None:
    repo = PreventiviRepository()
    preventivo = repo.get_preventivo(preventivo_id)
    ErrorManager.require(
        preventivo is not None,
        code="E_PREV_NOT_FOUND",
        message="Preventivo non trovato per emissione PDF.",
        detail=f"preventivo_id={preventivo_id}",
        function_name=f"{_FN}._genera_pdf_emissione",
    )
    assert preventivo is not None

    doc_repo = DocumentiRepository()
    sorgente = doc_repo.get_sorgente_tipo_id_by_codice(_CODICE_SORGENTE_PREVENTIVO)
    ErrorManager.require(
        sorgente is not None and sorgente.get("attivo"),
        code="E_DOCUMENTI_VALIDATION",
        message="Sorgente 'PREVENTIVO' non configurata o non attiva.",
        function_name=f"{_FN}._genera_pdf_emissione",
    )
    assert sorgente is not None

    DocumentGenerationService().genera_documento(
        user,
        emittente_fiscale_id=int(preventivo["emittente_fiscale_id"]),
        sorgente_tipo_id=int(sorgente["id"]),
        sorgente_id=int(preventivo["id"]),
        sorgente_uid=str(preventivo["uid"]),
    )


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

    # Gating L1 sui componenti_overrides (form atomic 2026-05-12): se il
    # payload contiene overrides ma l'operatore non ha l'azione
    # prezzo_override_manuale, solleva 403 prima di toccare DB.
    _validate_componenti_overrides_authorization(
        payload, auth_user_id, function_name=f"{_FN}.gestisci_riga",
    )

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
    merged_meta = _coerce_meta_to_dict(payload.get("meta"))
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
        stato_approvazione = STATO_APPROVAZIONE_PENDING

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

    # Init componenti BoM CASO A (refactor componenti, 2026-05-11).
    # La fn DB e' idempotente e gestisce il caso "articolo non composito"
    # come no-op (ritorna 0). La fn DB richiede emittente_sr_id NOT NULL.
    #
    # Risoluzione emittente in 2 step (precedenza preventivo > operatore):
    #  1) Se il preventivo ha `emittente_fiscale_id` esplicito (caso admin
    #     globale che ha settato l'emittente nel payload, o operatore che
    #     ha cambiato emittente del preventivo), uso quello. Altrimenti:
    #  2) Fallback all'emittente assegnato all'operatore (operatore singolo
    #     emittente: il preventivo eredita).
    # Senza emittente da nessuna fonte (admin globale + preventivo senza
    # emittente esplicito) lo skip silenzioso resta — caso edge per cui
    # non sappiamo come pricing.
    # Il prezzo_unitario della riga padre verra' immediatamente
    # sovrascritto dal trigger DB di ricalcolo se almeno un componente
    # viene creato (CASO A). CASO B: prezzo padre invariato.
    # Vedi guida `gestione-listini.md` §5.2.1 e brief DB.
    riga_id_created = result.get("id")
    data_riferimento_str = testata.get("data")
    if riga_id_created is not None and data_riferimento_str is not None:
        emittente_sr_id = _resolve_emittente_sr_id_for_preventivo(
            repo, testata, auth_user_id,
        )
        if emittente_sr_id is not None:
            # Form atomic (decisione di dominio 2026-05-12): il FE invia
            # `componenti_overrides` raccolti nel drawer riga in 2 step.
            # Mappa {componente_id_uuid: prezzo}. Il caller deve aver
            # gia' applicato il gating L1 (prezzo_override_manuale): vedi
            # _validate_componenti_overrides_authorization sopra. Senza
            # overrides equivale al comportamento strict (resolver mancante
            # -> raise E_DOC_COMPONENTE_LISTINO_MANCANTE).
            componenti_overrides = _normalize_componenti_overrides(
                payload.get("componenti_overrides"),
                function_name=f"{_FN}.gestisci_riga",
            )
            repo.init_componenti_riga(
                riga_id=int(riga_id_created),
                emittente_soggetto_ruolo_id=emittente_sr_id,
                data_riferimento=date.fromisoformat(str(data_riferimento_str)),
                componenti_overrides=componenti_overrides,
            )

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
            # Lookup mirato per id: evita di caricare l'intero elenco
            # righe del preventivo (vecchio pattern list_righe + filter).
            riga_esistente = repo.get_riga(riga_id) or False
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
            # `meta` puo' arrivare come dict (caso normale: psycopg deserializza
            # jsonb) o come stringa JSON (regressione di adapter / payload FE
            # serializzato). _coerce_meta_to_dict normalizza entrambi i casi
            # ed evita il classico ValueError "dictionary update sequence
            # element #0 has length 1; 2 is required".
            base = update_fields.get("meta")
            if not base:
                base = riga_esistente.get("meta")
            merged_meta = _coerce_meta_to_dict(base)
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
            update_fields["stato_approvazione_prezzo"] = STATO_APPROVAZIONE_PENDING
            update_fields["pratica_approvazione_prezzo_id"] = pratica_id_l3
        else:
            # Auto-reset stato approvazione: l'operatore ha modificato il prezzo
            # e il nuovo valore non richiede approvazione (resolver applicabile
            # o override entro L2). Se la riga era REJECTED/APPROVED il flag
            # era riferito al prezzo precedente — non e' piu' valido. Il reset
            # sblocca il preventivo (vedi get_preventivo `frozen_for_pending_pricing`,
            # esteso al match REJECTED) e permette di emettere senza che il
            # vecchio rifiuto resti come blocco fantasma.
            #
            # Cleanup denormalizzato meta: rimuoviamo `approvazione_rifiuto`
            # (motivazione precedente irrilevante post-correzione).
            stato_attuale = riga_esistente.get("stato_approvazione_prezzo") if riga_esistente else None
            if stato_attuale in {STATO_APPROVAZIONE_REJECTED, STATO_APPROVAZIONE_APPROVED}:
                update_fields["stato_approvazione_prezzo"] = None
                update_fields["pratica_approvazione_prezzo_id"] = None
                cleanup_meta = update_fields.get("meta")
                if isinstance(cleanup_meta, dict) and "approvazione_rifiuto" in cleanup_meta:
                    cleanup_meta.pop("approvazione_rifiuto", None)
                    update_fields["meta"] = cleanup_meta

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
    #
    # Cambio articolo padre: NON gestito qui per design. `articolo_id` non
    # e' nella whitelist `update_fields` sopra — la regola del dominio e'
    # "articolo immutabile post-create" (l'operatore elimina + ricrea la
    # riga). Quindi i componenti CASO A iniziali dell'init (gestisci_riga)
    # restano coerenti per tutta la vita della riga.

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


# Scopo: Normalizza `meta` a dict, accettando dict (caso normale: psycopg
#        deserializza jsonb), stringa JSON (caso regressione adapter o
#        payload FE serializzato in stringa) o None/falsy (→ dict vuoto).
#        Senza questa normalizzazione, `dict("...")` su una stringa solleva
#        ValueError "dictionary update sequence element #0 has length 1;
#        2 is required" che il middleware traduce in E_VALIDATION_INPUT,
#        mascherando il vero problema (un meta serializzato non riconosciuto).
def _coerce_meta_to_dict(value: Any) -> dict[str, Any]:
    if value is None or value == "" or value == {}:
        return {}
    if isinstance(value, dict):
        return dict(value)
    if isinstance(value, str):
        # Tentativo di parsing JSON. Stringa malformata → dict vuoto:
        # non bloccante, il merge col prezzo_meta avviene comunque.
        try:
            parsed = json.loads(value)
        except (ValueError, TypeError):
            return {}
        return parsed if isinstance(parsed, dict) else {}
    # Tipo inatteso (lista, numero, bool): fallback dict vuoto.
    return {}


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
    # Cascata user → group → emittente → default: senza derivazione EF
    # gli override impostati per emittente non sarebbero mai applicati.
    # Coerente con `PricingLimitiUtenteView` che alimenta l'hint FE.
    emittente_fiscale_id = param_service.get_emittente_fiscale_id_for_user(
        auth_user_id,
    )
    limite = param_service.get_parameter_decimal(
        param_code,
        django_user_id=auth_user_id,
        emittente_fiscale_id=emittente_fiscale_id,
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
# Scopo: Variante non-raise di `_resolve_emittente_sr_id_or_raise`. Ritorna
#        None per admin globale (no emittenti assegnati) o utente
#        inesistente, invece di sollevare. Usata dal flusso init componenti
#        CASO A in `gestisci_riga` dove l'init e' opzionale: se l'utente
#        non ha emittente non c'e' modo di chiamare il resolver, ma cio'
#        non deve bloccare la create di righe non-CASO-A.
def _resolve_emittente_sr_id_safe(auth_user_id: int | None) -> int | None:
    if auth_user_id is None:
        return None
    user_model = get_user_model()
    try:
        user = user_model.objects.get(pk=auth_user_id)
    except user_model.DoesNotExist:
        return None
    emittenti_sr = PermissionResolver.get_emittenti_sr_ids(user) or []
    if not emittenti_sr:
        return None
    return int(emittenti_sr[0])


# Scopo: Risolve l'emittente_soggetto_ruolo_id per le operazioni che dipendono
#        dal contesto preventivo (init componenti CASO A, preview componenti).
#        Precedenza: emittente esplicito sulla testata > emittente operatore.
#        Ritorna None se nessuna fonte: il caller decide se sollevare (preview,
#        path strict) o procedere skip silenzioso (init in gestisci_riga, caso
#        admin globale + preventivo senza emittente). Pattern estratto per
#        evitare duplicazione fra gestisci_riga e preview_componenti_riga.
def _resolve_emittente_sr_id_for_preventivo(
    repo: PreventiviRepository,
    testata: dict[str, Any],
    auth_user_id: int | None,
) -> int | None:
    emittente_fiscale_id_prev = testata.get("emittente_fiscale_id")
    if emittente_fiscale_id_prev is not None:
        sr_id = repo.get_emittente_sr_id_by_fiscale_id(
            int(emittente_fiscale_id_prev),
        )
        if sr_id is not None:
            return sr_id
    return _resolve_emittente_sr_id_safe(auth_user_id)


# Scopo: Valida e normalizza `componenti_overrides` (form atomic 2026-05-12).
#        Forma attesa: {componente_id_uuid: numero}. Decimal-safe: scarta a
#        monte boolean/oggetti/stringhe non numeriche che fallirebbero al
#        CAST::numeric lato fn DB con un errore poco parlante. Restituisce
#        un dict normalizzato a {str: str(Decimal)} (None/{} -> None).
#        Solleva E_PREV_VALIDAZIONE su valori invalidi.
def _normalize_componenti_overrides(
    overrides: Any,
    *,
    function_name: str,
) -> dict[str, str] | None:
    if overrides is None or overrides == {}:
        return None
    ErrorManager.require(
        isinstance(overrides, dict),
        code="E_PREV_VALIDAZIONE",
        message="componenti_overrides deve essere un oggetto JSON.",
        function_name=function_name,
    )
    assert isinstance(overrides, dict)
    normalized: dict[str, str] = {}
    for k, v in overrides.items():
        ErrorManager.require(
            v is not None and v != "",
            code="E_PREV_VALIDAZIONE",
            message=f"Prezzo override mancante per componente {k!r}.",
            function_name=function_name,
        )
        try:
            dec = Decimal(str(v))
        except (InvalidOperation, TypeError, ValueError) as exc:
            ErrorManager.require(
                False,
                code="E_PREV_VALIDAZIONE",
                message=(
                    f"Prezzo override non valido per componente {k!r}: {v!r}."
                ),
                function_name=function_name,
            )
            raise AssertionError("unreachable") from exc
        normalized[str(k)] = format(dec, "f")
    return normalized or None


# Scopo: Gating L1 sugli override prezzo componenti (form atomic 2026-05-12).
#        Solleva `E_PREV_OVERRIDE_NON_AUTORIZZATO` (esistente) se il payload
#        contiene `componenti_overrides` non vuoti e l'operatore non ha
#        l'azione `prezzo_override_manuale`. Stesso pattern del gating su
#        prezzo override della riga padre: la fn DB accetta gli overrides
#        senza check (responsabilita' BE), defense-in-depth contro bypass
#        via curl/DevTools.
def _validate_componenti_overrides_authorization(
    payload: dict[str, Any],
    auth_user_id: int | None,
    *,
    function_name: str,
) -> None:
    overrides = payload.get("componenti_overrides")
    if not overrides:
        return
    user_model = get_user_model()
    user = None
    if auth_user_id is not None:
        try:
            user = user_model.objects.get(pk=auth_user_id)
        except user_model.DoesNotExist:
            user = None
    authorized = (
        user is not None
        and PermissionResolver.check_azione(user, AZIONE_OVERRIDE_PREZZO)
    )
    ErrorManager.require(
        authorized,
        code="E_PREV_OVERRIDE_NON_AUTORIZZATO",
        message="Override prezzo componenti richiede autorizzazione 'prezzo_override_manuale'.",
        detail="L'operatore non ha l'azione `prezzo_override_manuale` necessaria per inserire prezzi manuali sui componenti.",
        function_name=function_name,
    )


# Scopo: Estrae l'unico (o primo) emittente_soggetto_ruolo_id autorizzato
#        per l'utente. Helper privato condiviso da `suggerisci_prezzo_riga`
#        (flusso resolver prezzo) e da altri ingressi che richiedono
#        emittente obbligatorio. Solleva E_PREV_VALIDAZIONE se l'utente non
#        e' trovato o non ha emittenti. Modello operatore-emittenti 1-a-1:
#        in pratica la lista ha sempre 1 elemento (a parte admin globali
#        che non passano per qui).
def _resolve_emittente_sr_id_or_raise(
    auth_user_id: int | None, *, function_name: str,
) -> int:
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
    return int(emittenti_sr[0])


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
    emittente_sr_id = _resolve_emittente_sr_id_or_raise(
        auth_user_id, function_name=function_name,
    )

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
#  Componenti BoM CASO A — service pubblico
# ══════════════════════════════════════════════════════════
# Refactor componenti 2026-05-11. Vedi `refactor-componenti.md` +
# `gestione-listini.md` §5.2.1. I componenti vivono in
# `vendite.preventivi_righe_componenti`; `init_componenti_riga` e' chiamato
# automaticamente da `gestisci_riga` / `aggiorna_riga` (cambio articolo).
# Qui le API di consultazione + modifica fine ai singoli componenti.


# Scopo: Preview componenti CASO A per il drawer riga (form atomic
#        2026-05-12). Read-only: il FE invoca PRIMA del save di una riga
#        composita per ottenere i prezzi suggeriti dei componenti esposti.
#        Per ogni componente: prezzo_suggerito + origine_prezzo, oppure
#        NULL + resolver_error_reason se il listino manca. Il FE pre-popola
#        la tabella editabile; l'operatore valorizza i NULL prima del save.
#        Il payload del save include `componenti_overrides` con i prezzi
#        manuali (vedi `gestisci_riga` + gating L1).
#
#        Risoluzione emittente: stesso pattern di `gestisci_riga`
#        (precedenza emittente del preventivo > operatore).
#        Solleva 404 se preventivo non esiste, 422 se data preventivo NULL
#        o emittente non risolvibile.
def preview_componenti_riga(
    preventivo_id: int,
    *,
    articolo_id: str,
    uom_operativa_id: int | None,
    quantita,
    auth_user_id: int | None = None,
) -> list[dict[str, Any]]:
    repo = PreventiviRepository()
    testata = repo.get_preventivo(preventivo_id)
    ErrorManager.require(
        testata is not None,
        code="E_PREV_NOT_FOUND",
        message="Preventivo non trovato.",
        function_name=f"{_FN}.preview_componenti_riga",
    )
    assert testata is not None
    data_riferimento_str = testata.get("data")
    ErrorManager.require(
        data_riferimento_str is not None,
        code="E_PREV_VALIDAZIONE",
        message="Data preventivo obbligatoria per preview componenti.",
        function_name=f"{_FN}.preview_componenti_riga",
    )
    emittente_sr_id = _resolve_emittente_sr_id_for_preventivo(
        repo, testata, auth_user_id,
    )
    ErrorManager.require(
        emittente_sr_id is not None,
        code="E_PREV_VALIDAZIONE",
        message="Impossibile risolvere l'emittente fiscale per la preview.",
        function_name=f"{_FN}.preview_componenti_riga",
    )
    assert emittente_sr_id is not None
    # Guard utility_id: la preview ha senso solo con utility nota (il
    # resolver deriva listino/categoria da (utility, data)). Senza guard
    # un utility_id NULL sarebbe coerciato silenziosamente a 0 e farebbe
    # esplodere la fn DB con un errore poco parlante.
    utility_id_raw = testata.get("utility_id")
    ErrorManager.require(
        utility_id_raw is not None,
        code="E_PREV_VALIDAZIONE",
        message="Utility preventivo obbligatoria per preview componenti.",
        function_name=f"{_FN}.preview_componenti_riga",
    )
    assert utility_id_raw is not None

    return repo.preview_componenti_riga(
        articolo_id=articolo_id,
        uom_id=uom_operativa_id,
        quantita_padre=quantita,
        data_riferimento=date.fromisoformat(str(data_riferimento_str)),
        ba_id=testata.get("billing_account_id"),
        utility_id=int(utility_id_raw),
        emittente_soggetto_ruolo_id=emittente_sr_id,
    )


# Scopo: Lista componenti CASO A di una riga padre composita per la UI.
#        Filtra solo i componenti `attivo=TRUE`. Guard di esistenza:
#        riga padre deve esistere ed appartenere al preventivo richiesto.
def list_componenti_riga(preventivo_id: int, riga_id: int) -> list[dict[str, Any]]:
    repo = PreventiviRepository()
    riga = repo.get_riga(riga_id)
    ErrorManager.require(
        riga is not None,
        code="E_PREV_RIGA_NOT_FOUND",
        message="Riga preventivo non trovata.",
        detail=f"riga_id={riga_id}",
        function_name=f"{_FN}.list_componenti_riga",
    )
    assert riga is not None
    ErrorManager.require(
        riga.get("preventivo_id") == preventivo_id,
        code="E_PREV_RIGA_NOT_FOUND",
        message="Riga preventivo non trovata.",
        detail=f"riga_id={riga_id} non appartiene a preventivo_id={preventivo_id}",
        function_name=f"{_FN}.list_componenti_riga",
    )
    return repo.list_componenti_riga(riga_id)


# Scopo: Helper privato condiviso da update/delete componente. Esegue le 3
#        query di guard + scope check + stato preventivo e ritorna le 3
#        entita' fetchate. Evita duplicazione del pattern in update_componente
#        e delete_componente. Solleva ServiceError (404 / 422 a seconda).
#        Scope check sia su `riga_id` URL (anti-tampering) che su
#        `preventivo_id`: due livelli di defense-in-depth contro URL forgiati.
def _load_componente_for_modification(
    repo: PreventiviRepository,
    *,
    preventivo_id: int,
    riga_id: int,
    componente_id: int,
    function_name: str,
) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    componente = repo.get_componente(componente_id)
    ErrorManager.require(
        componente is not None,
        code="E_PREV_COMPONENTE_NOT_FOUND",
        message="Componente non trovato.",
        detail=f"componente_id={componente_id}",
        function_name=function_name,
    )
    assert componente is not None

    # Anti-tampering URL: il `riga_id` dalla rotta deve matchare la riga
    # padre reale del componente. Altrimenti l'utente potrebbe forgiare
    # una URL `/preventivi/1/righe/999/componenti/50/` con riga falsa.
    ErrorManager.require(
        int(componente["riga_preventivo_id"]) == riga_id,
        code="E_PREV_COMPONENTE_NOT_FOUND",
        message="Componente non trovato.",
        detail=(
            f"componente_id={componente_id} non appartiene a "
            f"riga_id={riga_id} (riga reale={componente['riga_preventivo_id']})"
        ),
        function_name=function_name,
    )

    riga_padre = repo.get_riga(int(componente["riga_preventivo_id"]))
    ErrorManager.require(
        riga_padre is not None and riga_padre.get("preventivo_id") == preventivo_id,
        code="E_PREV_COMPONENTE_NOT_FOUND",
        message="Componente non trovato.",
        detail=f"componente_id={componente_id} fuori scope preventivo_id={preventivo_id}",
        function_name=function_name,
    )
    assert riga_padre is not None

    testata = repo.get_preventivo(preventivo_id)
    assert testata is not None  # garantito da get_riga ok sopra
    ErrorManager.require(
        testata["stato_codice_interno"] in _STATI_RIGHE_MODIFICABILI,
        code="E_PREV_STATO_NON_MODIFICABILE",
        message="Componenti non modificabili nello stato corrente.",
        detail=f"stato={testata['stato_codice_interno']}",
        function_name=function_name,
    )
    return componente, riga_padre, testata


# Scopo: Modifica componente esistente. Guard stato preventivo modificabile
#        + esistenza componente + match URL anti-tampering. Whitelist campi
#        via repo.
#        TODO (post-smoke iniziale): L1/L2/L3 sui componenti come per la
#        riga padre. Oggi accettiamo qualsiasi `prezzo_unitario` se il
#        preventivo e' modificabile — sufficiente per UI di test (3.4.A/B/C
#        in `sviluppo-listini-v5-test-ui.md`). Il trigger DB di guard
#        PENDING `trgfn_preventivi_righe_componenti_guard_pending` resta
#        come safety net.
def update_componente(
    preventivo_id: int,
    riga_id: int,
    componente_id: int,
    payload: dict[str, Any],
    *,
    auth_user_id: int | None = None,  # noqa: ARG001 — riservato a L1/L2/L3 futuro
) -> dict[str, Any]:
    repo = PreventiviRepository()
    _load_componente_for_modification(
        repo,
        preventivo_id=preventivo_id, riga_id=riga_id, componente_id=componente_id,
        function_name=f"{_FN}.update_componente",
    )

    # Solo campi della whitelist repo finiscono nell'UPDATE (defense-in-depth).
    # Il prezzo_unitario del padre verra' ricalcolato dal trigger DB.
    updated = repo.update_componente(componente_id, **payload)
    ErrorManager.require(
        updated,
        code="E_PREV_COMPONENTE_NOT_FOUND",
        message="Nessun campo aggiornato sul componente.",
        detail="Payload vuoto o senza campi nella whitelist.",
        function_name=f"{_FN}.update_componente",
    )
    return {"status": "ok", "componente_id": componente_id}


# Scopo: Soft delete componente (`attivo=FALSE`). Guard stato + esistenza
#        + match URL anti-tampering. Il trigger DB di ricalcolo padre
#        esclude i componenti inattivi dalla SUM, quindi il prezzo padre
#        si aggiorna in automatico.
def delete_componente(
    preventivo_id: int, riga_id: int, componente_id: int,
) -> dict[str, Any]:
    repo = PreventiviRepository()
    _load_componente_for_modification(
        repo,
        preventivo_id=preventivo_id, riga_id=riga_id, componente_id=componente_id,
        function_name=f"{_FN}.delete_componente",
    )
    deleted = repo.delete_componente(componente_id)
    # idempotenza: se gia' soft-deleted ritorna False — non e' errore qui.
    return {"status": "ok", "componente_id": componente_id, "deleted": deleted}


# ══════════════════════════════════════════════════════════
#  INTEGRAZIONE — Commesse / Fatturazione
# ══════════════════════════════════════════════════════════


# Scopo: Push preventivo accettato in commessa per pipeline fatturazione.
# Obiettivo: guard stato ACCETTATO + discovery righe eleggibili, poi delega
# al CommessaPushOrchestrator filtrato sul singolo preventivo
# (`pr_run_commesse_push_one(sorgente_codice='PREVENTIVO', sorgente_uid=preventivo_id)`).
# Perimetro: questa fn copre solo la Fase 1 (commesse_attivita); l'emit
# verso attivita_fatturabili (Fase 3) per preventivi `fatturazione_immediata=TRUE`
# e' tracciato in PR2 (vedi WIP sviluppo-push-singolo-preventivo §9).
# Idempotente via segment_key sul layer DB (lo gestisce fn_upsert_commessa_attivita).
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

    # Delega al CommessaPushOrchestrator filtrato: scrive commesse + righe
    # via fn DB esistenti, logga su commesse_push_log + event_log.
    # Import locale per evitare ciclo (commesse_service importa repo che importa
    # preventivi_repository in altri punti).
    from apps.vendite.services.commesse_service import pr_run_commesse_push_one

    report = pr_run_commesse_push_one(
        sorgente_codice="PREVENTIVO",
        sorgente_uid=preventivo_id,
    )

    # Transizione automatica ACCETTATO → EVASO se push completato.
    # La transizione e' seedata in `config.transizioni_stati_preventivi`
    # con `meta.manuale=false` (vedi brief DB
    # docs/it/dev/work-in-progress/brief-db-stato-preventivo-evaso.md).
    # Se PARZIALE/ERRORE/SKIPPED il preventivo resta ACCETTATO:
    # serve un ri-push per completare prima di poter evadere.
    # Robustezza al deploy parziale: se la fn DB rifiuta la transizione
    # (es. seed non ancora atterrato), logga warning e prosegue — il
    # push e' gia' avvenuto, lo stato si allineera' al re-run successivo.
    if report["stato"] == "COMPLETATO":
        try:
            repo.cambia_stato(preventivo_id, "EVASO", "django_api")
        except DatabaseError as exc:
            logging.getLogger(__name__).warning(
                "preventivi.push.transizione_evaso_skipped preventivo_id=%s reason=%s",
                preventivo_id, str(exc),
            )

    return {
        "preventivo_id": preventivo_id,
        "stato": report["stato"],
        "push_log_id": report["push_log_id"],
        "durata_ms": report["durata_ms"],
        "handlers": report["handlers"],
        # Diagnostico pre-push: utile a confronto con il delta operato dall'orchestrator.
        "righe_pushable": righe_count,
        # Flag testata necessario al FE per decidere se mostrare l'hint
        # "fatturazione immediata: emit AF avverra' al prossimo run pipeline lotto"
        # (PR2 implementera' il servizio emissione immediata).
        "fatturazione_immediata": bool(testata.get("fatturazione_immediata")),
    }


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
