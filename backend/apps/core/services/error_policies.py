# ------------------------------------------------------------
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2025 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Policy errori per mapping HTTP/UI.
# ------------------------------------------------------------


from dataclasses import dataclass

# Registro centrale mapping errore -> comportamento API/UI.


@dataclass(frozen=True)
class ErrorPolicy:
    code: str
    http_status: int
    ui_action: str
    user_message: str


class ErrorPolicyRegistry:
    """Policy centralizzate per evitare mapping duplicato nei moduli API."""

    _POLICIES: dict[str, ErrorPolicy] = {
        "E_PIPELINE": ErrorPolicy(
            code="E_PIPELINE",
            http_status=400,
            ui_action="show_error_banner",
            user_message="Errore nella pipeline di fatturazione.",
        ),
        "E_PIPELINE_VALIDATION": ErrorPolicy(
            code="E_PIPELINE_VALIDATION",
            http_status=400,
            ui_action="highlight_form_fields",
            user_message="Parametri pipeline non validi.",
        ),
        "E_IDEMPOTENCY_KEY_REQUIRED": ErrorPolicy(
            code="E_IDEMPOTENCY_KEY_REQUIRED",
            http_status=400,
            ui_action="highlight_form_fields",
            user_message="Idempotency-Key obbligatoria per questa operazione.",
        ),
        "E_IDEMPOTENCY_IN_PROGRESS": ErrorPolicy(
            code="E_IDEMPOTENCY_IN_PROGRESS",
            http_status=409,
            ui_action="show_retry_dialog",
            user_message="Operazione gia` in elaborazione con la stessa Idempotency-Key.",
        ),
        "E_PIPELINE_LOTTO_NOT_FOUND": ErrorPolicy(
            code="E_PIPELINE_LOTTO_NOT_FOUND",
            http_status=404,
            ui_action="show_empty_state",
            user_message="Lotto non trovato.",
        ),
        "E_PIPELINE_NOT_FOUND": ErrorPolicy(
            code="E_PIPELINE_NOT_FOUND",
            http_status=404,
            ui_action="show_error_banner",
            user_message="Configurazione pipeline non trovata.",
        ),
        "E_TASK_NOT_ALLOWED": ErrorPolicy(
            code="E_TASK_NOT_ALLOWED",
            http_status=400,
            ui_action="show_error_banner",
            user_message="Task pipeline non autorizzato.",
        ),
        "E_TASK_NOT_IMPLEMENTED": ErrorPolicy(
            code="E_TASK_NOT_IMPLEMENTED",
            http_status=501,
            ui_action="show_error_banner",
            user_message="Task pipeline non implementato.",
        ),
        "E_CORE_VALIDATION": ErrorPolicy(
            code="E_CORE_VALIDATION",
            http_status=400,
            ui_action="highlight_form_fields",
            user_message="Parametri non validi.",
        ),
        # Guard catalogo obsoleto (dbops.trgfn_child_requires_non_obsolete_parent):
        # tentata creazione/ri-aggancio di un'istanza su una voce di catalogo con
        # obsoleto_dal <= oggi. Conflitto di stato del catalogo → 409 (come gli
        # altri guard). Messaggio parlante dal DB (messaggi_errore id 500).
        "E_CATALOGO_OBSOLETO_NUOVA_ISTANZA": ErrorPolicy(
            code="E_CATALOGO_OBSOLETO_NUOVA_ISTANZA",
            http_status=409,
            ui_action="show_error_banner",
            user_message="Voce di catalogo obsoleta: non selezionabile per nuove istanze.",
        ),
        # Pratica preventivi: completamento SMISTAMENTO senza aver smistato la
        # merce (nessun ordine, residuo merce). 422: lo step non e' processabile
        # finche' l'operatore non genera l'ordine dal Pannello Smistamento.
        "E_VENDITA_SMISTAMENTO_NON_ESEGUITO": ErrorPolicy(
            code="E_VENDITA_SMISTAMENTO_NON_ESEGUITO",
            http_status=422,
            ui_action="show_error_banner",
            user_message="Esegui lo smistamento della merce (genera ordine) prima di completare lo step.",
        ),
        # Preventivo non agganciato a una pratica: azioni del percorso pratica
        # (es. completa_smistamento) richiedono il legame pratiche_sorgenti ROOT.
        # Gia' usato dagli handler di dominio (post_smistamento/accetta/push).
        "E_VENDITA_PREVENTIVO_NON_COLLEGATO": ErrorPolicy(
            code="E_VENDITA_PREVENTIVO_NON_COLLEGATO",
            http_status=422,
            ui_action="show_error_banner",
            user_message="Il preventivo non e' collegato a una pratica: azione non disponibile.",
        ),
        # ── Building block note partizionate (apps/core/services/partitioned_note_service.py) ──
        # Codici cross-area: il service in apps/core/ scrive su qualunque partizione
        # di vendite.note (PREVENTIVO/CONTRATTO/ORDINE/DDT/FATTURA/ATTIVITAFT) e in
        # prospettiva su tabelle note di altri schemi che adotteranno lo stesso pattern.
        "E_NOTA_VALIDATION": ErrorPolicy(
            code="E_NOTA_VALIDATION",
            http_status=400,
            ui_action="highlight_form_fields",
            user_message="Dati nota non validi.",
        ),
        "E_NOTA_NOT_FOUND": ErrorPolicy(
            code="E_NOTA_NOT_FOUND",
            http_status=404,
            ui_action="show_empty_state",
            user_message="Nota non trovata.",
        ),
        "E_NOTA_PARENT_NOT_FOUND": ErrorPolicy(
            code="E_NOTA_PARENT_NOT_FOUND",
            http_status=404,
            ui_action="show_empty_state",
            user_message="Documento di riferimento non trovato.",
        ),
        "E_NOTA_RIGA_INCOERENTE": ErrorPolicy(
            code="E_NOTA_RIGA_INCOERENTE",
            http_status=400,
            ui_action="highlight_form_fields",
            user_message="La riga indicata non appartiene al documento.",
        ),
        "E_NOTA_FK": ErrorPolicy(
            code="E_NOTA_FK",
            http_status=400,
            ui_action="highlight_form_fields",
            user_message="Riferimento non valido: stile, lingua o riga non esistenti.",
        ),
        "E_NOTA_DUPLICATO": ErrorPolicy(
            code="E_NOTA_DUPLICATO",
            http_status=409,
            ui_action="show_error_banner",
            user_message="Nota gia' esistente (violato vincolo di univocita').",
        ),
        "E_NOTA_CHECK_VIOLATION": ErrorPolicy(
            code="E_NOTA_CHECK_VIOLATION",
            http_status=400,
            ui_action="highlight_form_fields",
            user_message="Valore non ammesso per anchor_tipo, posizione, seq o testo.",
        ),
        # Sollevato da dbops.fn_get_lookup_codici (migration 20260520-04+06)
        # quando la tabella passata non ha la struttura attesa
        # (id + codice/codice_interno + descrizione) e non esiste override
        # dichiarativo in dbops.automation_overrides_cols (CODICE_COL/CODICE_INTERNO_COL).
        # E' un errore di configurazione/sviluppo (rel whitelistato in dbops_repository
        # senza colonne compatibili, o override mancante per tabella custom):
        # utente finale non puo' rimediarlo, va corretto dal team.
        "E_LOOKUP_STRUTTURA_TABELLA_INVALIDA": ErrorPolicy(
            code="E_LOOKUP_STRUTTURA_TABELLA_INVALIDA",
            http_status=500,
            ui_action="show_error_banner",
            user_message=(
                "Configurazione lookup non valida: la tabella richiesta non e' "
                "compatibile col formato lookup standard. Contattare l'amministratore."
            ),
        ),
        "E_VENDITE_VALIDATION": ErrorPolicy(
            code="E_VENDITE_VALIDATION",
            http_status=400,
            ui_action="highlight_form_fields",
            user_message="Parametri non validi.",
        ),
        # ── Vendite / promo articoli (F2-BE-03) ──
        "E_VENDITE_NOT_FOUND": ErrorPolicy(
            code="E_VENDITE_NOT_FOUND",
            http_status=404,
            ui_action="show_empty_state",
            user_message="Record vendite non trovato.",
        ),
        "E_VENDITE_DUPLICATO": ErrorPolicy(
            code="E_VENDITE_DUPLICATO",
            http_status=409,
            ui_action="show_error_banner",
            user_message="Record gia' esistente (violato vincolo di univocita').",
        ),
        "E_VENDITE_FK": ErrorPolicy(
            code="E_VENDITE_FK",
            http_status=400,
            ui_action="highlight_form_fields",
            user_message="Riferimento non valido: l'entita' indicata non esiste.",
        ),
        "E_VENDITE_PROMO_OVERLAP": ErrorPolicy(
            code="E_VENDITE_PROMO_OVERLAP",
            http_status=409,
            ui_action="show_error_banner",
            user_message="Esiste gia' una promo attiva per questo "
                         "(articolo, unita' di misura) nel periodo indicato.",
        ),
        # Pattern simmetrico a `E_VENDITE_CONTRATTO_OVERLAP` / `E_VENDITE_PROMO_OVERLAP`:
        # `ex_listini_versioni_no_overlap` (EXCLUDE GIST con WHERE attivo+stato=ATTIVA)
        # blocca sovrapposizioni di versioni listino ATTIVE. La risoluzione richiede
        # chiusura della versione precedente (valido_al = nuova_valido_dal - 1).
        "E_VENDITE_LISTINO_VERSIONE_OVERLAP": ErrorPolicy(
            code="E_VENDITE_LISTINO_VERSIONE_OVERLAP",
            http_status=409,
            ui_action="show_error_banner",
            user_message=(
                "Esiste gia' una versione ATTIVA sovrapposta per il listino. "
                "Chiudi la vecchia (valido_al = nuova_valido_dal - 1) e poi "
                "attiva la nuova: la nuova decorrenza deve essere almeno 1 "
                "giorno dopo l'inizio della precedente."
            ),
        ),
        # Ripristino enforcement EXCLUDE parziale su listini_righe_componenti
        # (migration 20260602-01). Pattern simmetrico a E_VENDITE_PROMO_OVERLAP /
        # E_VENDITE_LISTINO_VERSIONE_OVERLAP: due righe bundle ATTIVE sovrapposte
        # sullo stesso (versione, padre, componente) nel periodo di validita'.
        "E_VENDITE_LISTINO_RIGA_COMP_OVERLAP": ErrorPolicy(
            code="E_VENDITE_LISTINO_RIGA_COMP_OVERLAP",
            http_status=409,
            ui_action="show_error_banner",
            user_message=(
                "Esiste gia' un prezzo bundle attivo sovrapposto per questo "
                "componente nel periodo indicato. Disattiva o chiudi quello "
                "esistente prima di salvare il nuovo prezzo."
            ),
        ),
        # Guard Profilo A promo data-driven (vendite.promo_articoli):
        # le date governano lo stato (FUTURA / INIZIATA / SCADUTA) e vincolano
        # i campi modificabili. Pattern simmetrico a Profilo A contratti
        # (E_CONTRATTO_NON_MODIFICABILE) ma data-driven invece che stato-driven.
        # Defense-in-depth: trigger DB applica le stesse regole su bypass via psql.
        "E_PROMO_RETROATTIVA": ErrorPolicy(
            code="E_PROMO_RETROATTIVA",
            http_status=400,
            ui_action="highlight_form_fields",
            user_message=(
                "Le date della promo non possono essere retroattive: "
                "valido_dal deve essere successivo a oggi e valido_al "
                "non puo' essere antecedente a oggi."
            ),
        ),
        "E_PROMO_INIZIATA_CAMPI_RISTRETTI": ErrorPolicy(
            code="E_PROMO_INIZIATA_CAMPI_RISTRETTI",
            http_status=409,
            ui_action="show_toast_error",
            user_message=(
                "Promo gia' iniziata: solo descrizione e data fine sono "
                "modificabili. Per cambiare prezzo o periodo, chiudere "
                "questa promo (data fine = oggi) e crearne una nuova."
            ),
        ),
        "E_PROMO_SCADUTA_IMMUTABILE": ErrorPolicy(
            code="E_PROMO_SCADUTA_IMMUTABILE",
            http_status=409,
            ui_action="show_toast_error",
            user_message=(
                "Promo scaduta: non modificabile. Per riproporla creare "
                "una nuova promo."
            ),
        ),
        # ── Contratti v5 (F2-BE-05/06) ──
        # Codici sollevati dai trigger DB trgfn_contratti_guard_modalita_c_*
        # e trgfn_contratti_utilities_guard_tipo_classe.
        "E_VENDITE_CONTRATTO_OVERLAP": ErrorPolicy(
            code="E_VENDITE_CONTRATTO_OVERLAP",
            http_status=409,
            ui_action="show_error_banner",
            user_message="Esiste gia' un contratto sovrapposto per questo "
                         "cliente/istanza/utility/ambito nel periodo indicato.",
        ),
        # ── Codici contratto refactor modalita 2026-05-15 ──
        # Sostituiscono i vecchi guard di "modalita C" rimossi col modello
        # unificato. Mappati dal team DB nel CSV `messaggi_errore` (450-454).
        "E_CONTRATTO_NEGOZIATO_PURO_SENZA_RIGHE": ErrorPolicy(
            code="E_CONTRATTO_NEGOZIATO_PURO_SENZA_RIGHE",
            http_status=422,
            ui_action="show_error_banner",
            user_message=(
                "Contratto senza listino di riferimento: aggiungere almeno "
                "un'AGGIUNTA con prezzo valorizzato prima di attivare."
            ),
        ),
        "E_CONTRATTO_AGGIUNTA_GIA_IN_LISTINO": ErrorPolicy(
            code="E_CONTRATTO_AGGIUNTA_GIA_IN_LISTINO",
            http_status=422,
            ui_action="highlight_form_fields",
            user_message=(
                "L'articolo e' gia' presente nel listino di riferimento: "
                "usare OVERRIDE per modificarne il prezzo, non AGGIUNTA."
            ),
        ),
        "E_ARTICOLO_ESCLUSO_DA_CONTRATTO": ErrorPolicy(
            code="E_ARTICOLO_ESCLUSO_DA_CONTRATTO",
            http_status=422,
            ui_action="show_error_banner",
            user_message=(
                "L'articolo e' stato escluso dal contratto e non puo' essere "
                "venduto a questo cliente."
            ),
        ),
        "E_CONTRATTO_CAMPI_BLOCCATI_POST_ATTIVAZIONE": ErrorPolicy(
            code="E_CONTRATTO_CAMPI_BLOCCATI_POST_ATTIVAZIONE",
            http_status=409,
            ui_action="show_error_banner",
            user_message=(
                "Il contratto e' ATTIVO: listino, versione listino, "
                "variazione globale ed eccezioni sono congelati. Per "
                "modifiche sostanziali creare un nuovo contratto."
            ),
        ),
        "E_CONTRATTO_LISTINO_RIMOZIONE_CON_ECCEZIONI": ErrorPolicy(
            code="E_CONTRATTO_LISTINO_RIMOZIONE_CON_ECCEZIONI",
            http_status=422,
            ui_action="show_error_banner",
            user_message=(
                "Impossibile rimuovere il listino di riferimento dal "
                "contratto: rimuovi prima le eccezioni OVERRIDE/ESCLUSIONE "
                "associate o sostituiscile con AGGIUNTA."
            ),
        ),
        # Refactor 2026-05-20: lock cambio `listino_id` (aggiunta o
        # sostituzione) su contratto DRAFT con righe persistite. Il listino
        # definisce il contesto pricing — cambiarlo con righe gia' caricate
        # causa drift semantico silente. La rimozione resta gestita dal
        # check piu' fine `E_CONTRATTO_LISTINO_RIMOZIONE_CON_ECCEZIONI`.
        "E_CONTRATTO_CAMPI_BLOCCATI_CON_RIGHE": ErrorPolicy(
            code="E_CONTRATTO_CAMPI_BLOCCATI_CON_RIGHE",
            http_status=422,
            ui_action="show_error_banner",
            user_message=(
                "Modifica del listino bloccata: ci sono righe gia' caricate "
                "contro questo contesto pricing. Elimina prima le righe "
                "oppure annulla il contratto e creane uno nuovo."
            ),
        ),
        # Refactor 2026-05-20: annullamento logico contratto (soft-delete via
        # stato ANNULLATO). Transizione DRAFT → ANNULLATO sempre ammessa;
        # ATTIVO → ANNULLATO bloccata se esistono attivita_fatturabili gia'
        # fatturate (fattura_riga_id IS NOT NULL) — la traccia contabile e'
        # immutabile, in quel caso l'unica via e' CESSATO con valido_al
        # opportuna. Sollevato dal trigger DB (id errore DB 457) e
        # intercettato lato BE via marker in `_KNOWN_DB_ERROR_MARKERS`.
        "E_CONTRATTO_ANNULLATO_CON_FATTURE": ErrorPolicy(
            code="E_CONTRATTO_ANNULLATO_CON_FATTURE",
            http_status=409,
            ui_action="show_error_banner",
            user_message=(
                "Impossibile annullare il contratto: esistono attivita' gia' "
                "fatturate. Per chiudere il contratto usa la cessazione "
                "(stato CESSATO con data di fine validita')."
            ),
        ),
        # Refactor 2026-05-18 (decisione §4.4 refactor-contratti-modalita):
        # un listino senza versione ATTIVA non e' selezionabile come
        # riferimento di un contratto. In assenza di una versione attiva non
        # ci sono righe da applicare, quindi il contratto sarebbe formalmente
        # "con listino" ma operativamente vuoto. Il vincolo si applica sia
        # in CREATE che in UPDATE (PATCH `listino_id`): l'errore parlante
        # arriva PRIMA del save evitando il flag `listino_senza_versione_oggi`
        # come zona grigia.
        "E_CONTRATTO_LISTINO_SENZA_VERSIONE_ATTIVA": ErrorPolicy(
            code="E_CONTRATTO_LISTINO_SENZA_VERSIONE_ATTIVA",
            http_status=422,
            ui_action="show_error_banner",
            user_message=(
                "Il listino selezionato non ha una versione ATTIVA. "
                "Solo i listini con almeno una versione pubblicata e attiva "
                "possono essere associati a un contratto. Attiva una "
                "versione del listino in gestione listini prima di tornare "
                "a selezionarlo qui."
            ),
        ),
        "E_CONTRATTO_ESCLUSIONE_FIGLIO_BUNDLE_VIETATA": ErrorPolicy(
            code="E_CONTRATTO_ESCLUSIONE_FIGLIO_BUNDLE_VIETATA",
            http_status=422,
            ui_action="show_error_banner",
            user_message=(
                "L'articolo e' un componente di un bundle: l'esclusione "
                "si applica al bundle padre, non al singolo componente. "
                "Per un bundle parziale crea un nuovo bundle in catalogo."
            ),
        ),
        "E_CONTRATTO_UTILITY_TIPO_CLASSE_OBBLIGATORI": ErrorPolicy(
            code="E_CONTRATTO_UTILITY_TIPO_CLASSE_OBBLIGATORI",
            http_status=400,
            ui_action="highlight_form_fields",
            user_message="Per questa utility tipo e classe utenza sono obbligatori.",
        ),
        "E_CONTRATTO_CLASSE_TIPO_INCOERENTE": ErrorPolicy(
            code="E_CONTRATTO_CLASSE_TIPO_INCOERENTE",
            http_status=400,
            ui_action="highlight_form_fields",
            user_message="La classe utenza scelta non appartiene al tipo utenza indicato.",
        ),
        "E_CONTRATTO_UTILITY_SENZA_DIMENSIONE_TIPO_CLASSE_VIETATI": ErrorPolicy(
            code="E_CONTRATTO_UTILITY_SENZA_DIMENSIONE_TIPO_CLASSE_VIETATI",
            http_status=400,
            ui_action="highlight_form_fields",
            user_message="Per questa utility tipo e classe utenza non vanno valorizzati.",
        ),
        # ── Pricing v5 resolver (F2-BE-09/10) ──
        # Codici di dominio sollevati dal DB via script.fn_log_and_raise_error.
        # Policy UI: operatore/admin vede messaggio business-safe; detail tecnico
        # nel payload solo se DJANGO_API_EXPOSE_TECHNICAL_DETAILS=1.
        "E_VENDITE_PRICING_FAILED": ErrorPolicy(
            code="E_VENDITE_PRICING_FAILED",
            http_status=400,
            ui_action="show_error_banner",
            user_message="Impossibile risolvere il prezzo listino.",
        ),
        "E_PREZZO_LISTINO_NON_TROVATO": ErrorPolicy(
            code="E_PREZZO_LISTINO_NON_TROVATO",
            http_status=404,
            ui_action="show_empty_state",
            user_message="Nessun prezzo listino risolto per l'articolo richiesto.",
        ),
        "E_PREZZO_LISTINO_RIGA_NON_TROVATA": ErrorPolicy(
            code="E_PREZZO_LISTINO_RIGA_NON_TROVATA",
            http_status=404,
            ui_action="show_empty_state",
            user_message="Riga listino non trovata per articolo/uom alla data.",
        ),
        "E_CATEGORIA_LISTINO_NON_MAPPATA": ErrorPolicy(
            code="E_CATEGORIA_LISTINO_NON_MAPPATA",
            http_status=404,
            ui_action="show_empty_state",
            user_message="Categoria cliente non mappata a listino per la quadrupla indicata.",
        ),
        "E_ARTICOLO_NON_NEGOZIATO_SU_CONTRATTO_C": ErrorPolicy(
            code="E_ARTICOLO_NON_NEGOZIATO_SU_CONTRATTO_C",
            http_status=400,
            ui_action="show_error_banner",
            user_message="Articolo non negoziato sul contratto in modalita' C.",
        ),
        "E_VENDITE_LISTINO_NOT_FOUND": ErrorPolicy(
            code="E_VENDITE_LISTINO_NOT_FOUND",
            http_status=404,
            ui_action="show_empty_state",
            user_message="Listino non trovato.",
        ),
        "E_VENDITE_LISTINO_VERSIONE_NOT_FOUND": ErrorPolicy(
            code="E_VENDITE_LISTINO_VERSIONE_NOT_FOUND",
            http_status=404,
            ui_action="show_empty_state",
            user_message="Versione listino non trovata.",
        ),
        "E_VENDITE_LISTINO_RIGA_NOT_FOUND": ErrorPolicy(
            code="E_VENDITE_LISTINO_RIGA_NOT_FOUND",
            http_status=404,
            ui_action="show_empty_state",
            user_message="Riga listino non trovata.",
        ),
        "E_VENDITE_LISTINO_ASSOCIAZIONE_NOT_FOUND": ErrorPolicy(
            code="E_VENDITE_LISTINO_ASSOCIAZIONE_NOT_FOUND",
            http_status=404,
            ui_action="show_empty_state",
            user_message="Associazione listino non trovata.",
        ),
        # Trigger DB immutabilita' v5 su listini_righe / listini_righe_componenti
        # (script.fn_log_and_raise_error, P0001): blocca INS/UPD/DLT quando
        # la versione listino non e' in BOZZA. Solleva il service
        # `fn_save_bundle` quando l'admin tenta di modificare prezzi bundle
        # su versione ATTIVA/CHIUSA.
        "E_RIGA_LISTINO_VERSIONE_CHIUSA": ErrorPolicy(
            code="E_RIGA_LISTINO_VERSIONE_CHIUSA",
            http_status=409,
            ui_action="show_error_banner",
            user_message=(
                "Modifica righe listino non consentita: la versione non e' "
                "in stato BOZZA."
            ),
        ),
        # Trigger DB guard coerenza BoM su listini_righe_componenti: blocca
        # prezzi bundle riferiti a componenti non presenti nella BoM corrente
        # del padre composito (o fuori dal range di validita' della BoM).
        "E_LISTINO_RIGA_COMP_BOM_INCOERENTE": ErrorPolicy(
            code="E_LISTINO_RIGA_COMP_BOM_INCOERENTE",
            http_status=400,
            ui_action="show_error_banner",
            user_message=(
                "Prezzo bundle riferito a un componente non presente nella "
                "distinta base del padre composito."
            ),
        ),
        # Resolver pricing v5 (fn_resolve_prezzo_listino_v2, rev 2026-05-13
        # bundle-prioritario): versione listino non trovata o non attiva
        # alla data del documento. Indica un mismatch fra il listino eletto
        # (contratto o categoria) e la disponibilita' di una versione
        # operativa per quel periodo.
        "E_LISTINO_VERSIONE_NON_ATTIVA": ErrorPolicy(
            code="E_LISTINO_VERSIONE_NON_ATTIVA",
            http_status=404,
            ui_action="show_error_banner",
            user_message=(
                "Listino senza versione attiva alla data del documento. "
                "Verificare le versioni del listino o la data di riferimento."
            ),
        ),
        # Guard cessazione contratti (trgfn_contratti_guard_transizione_stato,
        # rev 2026-05-14): la transizione manuale ATTIVO -> CESSATO non ammette
        # valido_al retroattivo. Il job notturno pgAgent (`fn_apply_chiusura
        # _scadenze` via GUC `app.cessazione_automatica`) e' invece autorizzato
        # a cessare con valido_al passato.
        "E_CONTRATTO_VALIDO_AL_RETROATTIVO": ErrorPolicy(
            code="E_CONTRATTO_VALIDO_AL_RETROATTIVO",
            http_status=409,
            ui_action="show_error_banner",
            user_message=(
                "Cessazione contratto non ammessa con data retroattiva. La "
                "data di fine validita' deve essere oggi o futura."
            ),
        ),
        # Guard Profilo A contratti: in stati post-DRAFT (ATTIVO/CESSATO)
        # le modifiche sono limitate o vietate. La testata ammette solo
        # `valido_al` e `meta` in ATTIVO; CESSATO immutabile. Le sotto
        # -entita' (righe override, utility 1:1) sono CRUD-able solo in
        # DRAFT. Per modifiche sostanziali post-DRAFT serve creare un
        # nuovo contratto (eventualmente con parent_contratto_id).
        "E_CONTRATTO_NON_MODIFICABILE": ErrorPolicy(
            code="E_CONTRATTO_NON_MODIFICABILE",
            http_status=409,
            ui_action="show_toast_error",
            user_message=(
                "Modifica non consentita: il contratto e' in uno stato che "
                "limita le operazioni. Per modifiche sostanziali creare un "
                "nuovo contratto."
            ),
        ),
        # Guard DB transizione stato contratti (trgfn_contratti_a10_guard_
        # transizione_stato, landed 2026-04-26). Rifiuta transizioni non
        # ammesse: DRAFT->ATTIVO consentita; ATTIVO->CESSATO consentita
        # SOLO con valido_al < CURRENT_DATE; CESSATO terminale; altre vietate.
        # Il service applicativo ha la stessa regola fail-safe data-driven:
        # se l'utente sceglie data futura nel dialog "Cessa contratto", il
        # service NON chiama update_stato (cessazione programmata) — il job
        # notturno applica CESSATO quando la data scade. Questo trigger
        # interviene su bypass del service (UPDATE diretto via psql).
        "E_CONTRATTO_STATO_TRANSIZIONE_INVALIDA": ErrorPolicy(
            code="E_CONTRATTO_STATO_TRANSIZIONE_INVALIDA",
            http_status=409,
            ui_action="show_toast_error",
            user_message=(
                "Transizione stato contratto non consentita. Per cessare "
                "un contratto utilizzare il pulsante Cessa che gestisce "
                "automaticamente la data e la transizione."
            ),
        ),
        # Errore configurazione automazione chiusura (job pgAgent
        # chiusura_scadenze_daily): scatta quando la lookup di codici
        # interni in config.stati_doc_contratti / stati_doc_versione
        # fallisce (seed mancante o codice rimosso). Errore raro,
        # tipicamente indica problema di consistenza ambiente.
        "E_AUTOMAZIONE_CHIUSURA_CONFIG_INVALIDA": ErrorPolicy(
            code="E_AUTOMAZIONE_CHIUSURA_CONFIG_INVALIDA",
            http_status=500,
            ui_action="show_toast_error",
            user_message=(
                "Errore configurazione automazione chiusura. "
                "Contattare l'amministratore di sistema."
            ),
        ),
        # Guard DB defense-in-depth: rifiuta la transizione manuale
        # ATTIVA -> CHIUSA (brief-db-listini-stato-chiusa-sync). La chiusura
        # si esegue via PATCH valido_al; lo stato CHIUSA viene poi sincronizzato
        # dal job notturno a finestra scaduta. Policy speculare a quella
        # applicativa nel service listini_service._validate_versione_state_transition.
        "E_VERSIONE_STATO_TRANSIZIONE_INVALIDA": ErrorPolicy(
            code="E_VERSIONE_STATO_TRANSIZIONE_INVALIDA",
            http_status=409,
            ui_action="show_toast_error",
            user_message=(
                "Chiusura versione non consentita via cambio stato. "
                "Per chiudere impostare valido_al (PATCH); la chiusura "
                "avviene automaticamente a finestra scaduta."
            ),
        ),
        "E_VENDITE_RIGA_GIA_PROPAGATA": ErrorPolicy(
            code="E_VENDITE_RIGA_GIA_PROPAGATA",
            http_status=409,
            ui_action="show_toast_error",
            user_message="Riga gia` propagata in commessa o fatturabile. Usare clone versione.",
        ),
        "E_CATALOGO_VALIDATION": ErrorPolicy(
            code="E_CATALOGO_VALIDATION",
            http_status=400,
            ui_action="highlight_form_fields",
            user_message="Parametri catalogo non validi.",
        ),
        "E_CATALOGO_ARTICOLO_NOT_FOUND": ErrorPolicy(
            code="E_CATALOGO_ARTICOLO_NOT_FOUND",
            http_status=404,
            ui_action="show_empty_state",
            user_message="Articolo non trovato.",
        ),
        "E_CATALOGO_UOM_NOT_FOUND": ErrorPolicy(
            code="E_CATALOGO_UOM_NOT_FOUND",
            http_status=404,
            ui_action="show_empty_state",
            user_message="UoM operativa non trovata.",
        ),
        "E_CATALOGO_UOM_TIPO_NOT_FOUND": ErrorPolicy(
            code="E_CATALOGO_UOM_TIPO_NOT_FOUND",
            http_status=404,
            ui_action="show_empty_state",
            user_message="Tipologia UoM non trovata.",
        ),
        "E_CATALOGO_COMPONENTE_NOT_FOUND": ErrorPolicy(
            code="E_CATALOGO_COMPONENTE_NOT_FOUND",
            http_status=404,
            ui_action="show_empty_state",
            user_message="Componente non trovato.",
        ),
        "E_CATALOGO_NOTA_NOT_FOUND": ErrorPolicy(
            code="E_CATALOGO_NOTA_NOT_FOUND",
            http_status=404,
            ui_action="show_empty_state",
            user_message="Nota non trovata.",
        ),
        # ── Catalogo BoM — guard immutabilita' struttura ──
        # E_BOM_MODIFICA_VIETATA e E_BOM_VALIDO_AL_INVALIDO sono sollevati
        # dal trigger catalogo.trgfn_articoli_componenti_block_modifica_struttura
        # come defense-in-depth oltre lo schema (pattern chiudi+inserisci).
        "E_BOM_MODIFICA_VIETATA": ErrorPolicy(
            code="E_BOM_MODIFICA_VIETATA",
            http_status=409,
            ui_action="show_error_banner",
            user_message=(
                "Struttura BoM immutabile: i campi di struttura non sono "
                "modificabili. Per correggere, chiudere la riga e inserirne "
                "una nuova versione."
            ),
        ),
        "E_BOM_VALIDO_AL_INVALIDO": ErrorPolicy(
            code="E_BOM_VALIDO_AL_INVALIDO",
            http_status=400,
            ui_action="highlight_form_fields",
            user_message=(
                "Data di chiusura non valida: deve essere uguale o successiva alla "
                "data di inizio della riga."
            ),
        ),
        "E_DATABASE": ErrorPolicy(
            code="E_DATABASE",
            http_status=400,
            ui_action="show_error_banner",
            user_message="Errore durante l'operazione database.",
        ),
        "E_DATABASE_RETRYABLE": ErrorPolicy(
            code="E_DATABASE_RETRYABLE",
            http_status=409,
            ui_action="show_retry_dialog",
            user_message="Conflitto transazionale, riprovare l'operazione.",
        ),
        "E_ATTIVITA_PIPELINE": ErrorPolicy(
            code="E_ATTIVITA_PIPELINE",
            http_status=400,
            ui_action="show_error_banner",
            user_message="Errore nella pipeline attivita fatturabili.",
        ),
        "E_ATTIVITA_VALIDATION": ErrorPolicy(
            code="E_ATTIVITA_VALIDATION",
            http_status=400,
            ui_action="highlight_form_fields",
            user_message="Parametri pipeline attivita non validi.",
        ),
        "E_ATTIVITA_LOTTO_NOT_FOUND": ErrorPolicy(
            code="E_ATTIVITA_LOTTO_NOT_FOUND",
            http_status=404,
            ui_action="show_empty_state",
            user_message="Lotto attivita non trovato.",
        ),
        "E_COMMESSA_VALIDATION": ErrorPolicy(
            code="E_COMMESSA_VALIDATION",
            http_status=400,
            ui_action="highlight_form_fields",
            user_message="Parametri commessa non validi.",
        ),
        "E_COMMESSA_NOT_FOUND": ErrorPolicy(
            code="E_COMMESSA_NOT_FOUND",
            http_status=404,
            ui_action="show_empty_state",
            user_message="Commessa non trovata.",
        ),
        "E_COMMESSA_AZIONE_NON_AMMESSA": ErrorPolicy(
            code="E_COMMESSA_AZIONE_NON_AMMESSA",
            http_status=409,
            ui_action="show_error_banner",
            user_message="Azione di stato non ammessa nello stato corrente della commessa.",
        ),
        "E_COMMESSA_PUSH_LOG_NOT_FOUND": ErrorPolicy(
            code="E_COMMESSA_PUSH_LOG_NOT_FOUND",
            http_status=404,
            ui_action="show_empty_state",
            user_message="Push log commesse non trovato.",
        ),
        "E_COMMESSA_ATTIVITA_NOT_FOUND": ErrorPolicy(
            code="E_COMMESSA_ATTIVITA_NOT_FOUND",
            http_status=404,
            ui_action="show_empty_state",
            user_message="Attivita` commessa non trovata.",
        ),
        # --- Immutabilita' quantita' + porta oneri (guard DB 550-554) ---
        # I due guard di immutabilita' sono 409: non e' un input da correggere,
        # e' un fatto che non si modifica (si corregge con una riga nuova).
        "E_COMMESSA_ATTIVITA_QUANTITA_IMMUTABILE": ErrorPolicy(
            code="E_COMMESSA_ATTIVITA_QUANTITA_IMMUTABILE",
            http_status=409,
            ui_action="show_error_banner",
            user_message=(
                "Riga di commessa gia` emessa: la quantita` non si modifica. "
                "Correggere aggiungendo una riga nuova."
            ),
        ),
        "E_ATTIVITA_FATTURABILE_QUANTITA_IMMUTABILE": ErrorPolicy(
            code="E_ATTIVITA_FATTURABILE_QUANTITA_IMMUTABILE",
            http_status=409,
            ui_action="show_error_banner",
            user_message=(
                "La quantita` dell`attivita` fatturabile deve specchiare quella "
                "della commessa: modifica non consentita."
            ),
        ),
        # Race sul progressivo segment_key degli oneri (guard DB 557,
        # brief-db-race-segment-key-onere §5): NON e' un input da correggere
        # ma un conflitto di concorrenza ritentabile → 409 come la famiglia
        # immutabilita', non 400. Nota: perche' questo codice ARRIVI qui e non
        # cada sul fallback E_COMMESSA_VALIDATION, deve essere anche nei
        # `_ONERE_DB_ERROR_MARKERS` del service (catena di traduzione).
        "E_ONERE_SEGMENT_DUPLICATO": ErrorPolicy(
            code="E_ONERE_SEGMENT_DUPLICATO",
            http_status=409,
            ui_action="show_error_banner",
            user_message="Onere non creato per una modifica concorrente. Riprovare.",
        ),
        "E_ONERE_IMPORTO_NON_VALIDO": ErrorPolicy(
            code="E_ONERE_IMPORTO_NON_VALIDO",
            http_status=400,
            ui_action="highlight_form_fields",
            user_message="Importo onere non valido: deve essere maggiore di zero.",
        ),
        "E_ONERE_CAUSALE_NON_VALIDA": ErrorPolicy(
            code="E_ONERE_CAUSALE_NON_VALIDA",
            http_status=400,
            ui_action="highlight_form_fields",
            user_message="Causale onere non valida o non attiva.",
        ),
        "E_ONERE_ARTICOLO_MANCANTE": ErrorPolicy(
            code="E_ONERE_ARTICOLO_MANCANTE",
            http_status=400,
            ui_action="highlight_form_fields",
            user_message=(
                "Articolo-onere non valido: inesistente, non attivo o senza "
                "causale associata."
            ),
        ),
        "E_COMMESSA_ATTIVITA_TIPO_DOC_OBBLIGATORIO": ErrorPolicy(
            code="E_COMMESSA_ATTIVITA_TIPO_DOC_OBBLIGATORIO",
            http_status=400,
            ui_action="highlight_form_fields",
            user_message="Tipo documento fiscale obbligatorio sulla riga emittibile.",
        ),
        "E_COMMESSA_PUSH_PARZIALE_VIETATO": ErrorPolicy(
            code="E_COMMESSA_PUSH_PARZIALE_VIETATO",
            http_status=422,
            ui_action="show_toast_error",
            user_message="Push fallito: nessuna riga inviata.",
        ),
        "E_VENDITE_VARIAZIONE_PREZZO_NON_AMMESSA": ErrorPolicy(
            code="E_VENDITE_VARIAZIONE_PREZZO_NON_AMMESSA",
            http_status=409,
            ui_action="show_toast_error",
            user_message="Operazione prezzo non ammessa sullo stato corrente.",
        ),
        "E_VENDITE_SBLOCCO_PREZZO_NON_AMMESSO": ErrorPolicy(
            code="E_VENDITE_SBLOCCO_PREZZO_NON_AMMESSO",
            http_status=409,
            ui_action="show_toast_error",
            user_message="Sblocco prezzo non ammesso: il prezzo non e` bloccato.",
        ),
        "E_VENDITE_RIALLINEAMENTO_VERSIONE_CAMBIATA": ErrorPolicy(
            code="E_VENDITE_RIALLINEAMENTO_VERSIONE_CAMBIATA",
            http_status=409,
            ui_action="show_toast_error",
            user_message="Riallineamento richiede conferma: la versione listino e` cambiata.",
        ),
        # Guard di uscita commessa (brief-db-guard-uscita-commessa 558/559):
        # transizione terminale IRREVERSIBILE bloccata → conflitto di stato (409),
        # come la famiglia immutabilita`. Banner: e` un blocco d'azione grave.
        "E_COMMESSA_ANNULLA_CON_RIGHE_EMESSE": ErrorPolicy(
            code="E_COMMESSA_ANNULLA_CON_RIGHE_EMESSE",
            http_status=409,
            ui_action="show_error_banner",
            user_message="Annullamento non consentito: la commessa ha righe gia` emesse.",
        ),
        "E_COMMESSA_CHIUSURA_CON_RIGHE_PENDENTI": ErrorPolicy(
            code="E_COMMESSA_CHIUSURA_CON_RIGHE_PENDENTI",
            http_status=409,
            ui_action="show_error_banner",
            user_message="Chiusura non consentita: restano righe approvate non ancora emesse.",
        ),
        # Annullamento riga MANUALE di commessa (guard DB 564-567,
        # brief-annullamento-righe-manuali-commessa §4d). Quattro codici
        # DISTINTI e non uno generico: ogni causa porta l'operatore a un'azione
        # diversa. In particolare `GIA_ANNULLATA` esiste separato da
        # `GIA_EMESSA` perche' dire «e` entrata nella catena di fatturazione» a
        # chi ha semplicemente cliccato due volte e` FALSO, e lo manda a cercare
        # una fattura che non esiste.
        # 409 sui tre conflitti di stato (non e` un input da correggere, e` un
        # fatto), 400 sul motivo mancante (campo del form).
        "E_RIGA_COMMESSA_GIA_ANNULLATA": ErrorPolicy(
            code="E_RIGA_COMMESSA_GIA_ANNULLATA",
            http_status=409,
            ui_action="show_toast_error",
            user_message="La riga era gia` stata annullata.",
        ),
        "E_RIGA_COMMESSA_NON_MANUALE": ErrorPolicy(
            code="E_RIGA_COMMESSA_NON_MANUALE",
            http_status=409,
            ui_action="show_error_banner",
            user_message=(
                "La riga nasce da un documento e non si annulla qui: "
                "il rimedio e` sul documento sorgente."
            ),
        ),
        "E_RIGA_COMMESSA_GIA_EMESSA": ErrorPolicy(
            code="E_RIGA_COMMESSA_GIA_EMESSA",
            http_status=409,
            ui_action="show_error_banner",
            user_message=(
                "Riga gia` entrata nella catena di fatturazione: "
                "la correzione passa dalla nota di credito."
            ),
        ),
        "E_RIGA_COMMESSA_MOTIVO_OBBLIGATORIO": ErrorPolicy(
            code="E_RIGA_COMMESSA_MOTIVO_OBBLIGATORIO",
            http_status=400,
            ui_action="highlight_form_fields",
            user_message="Motivo obbligatorio per annullare la riga.",
        ),
        # ── Pratiche ──
        "E_PRATICA_VALIDATION": ErrorPolicy(
            code="E_PRATICA_VALIDATION",
            http_status=400,
            ui_action="highlight_form_fields",
            user_message="Parametri pratica non validi.",
        ),
        "E_PRATICA_NOT_FOUND": ErrorPolicy(
            code="E_PRATICA_NOT_FOUND",
            http_status=404,
            ui_action="show_empty_state",
            user_message="Pratica non trovata.",
        ),
        # Edizioni workflow versionate (Slice 2): definizione o step non trovato
        # / fuori dallo scope della definizione (ownership) → 404 esplicito
        # (il codice generico E_NOT_FOUND non è in policy → ricadrebbe in 400).
        "E_DEFINIZIONE_NOT_FOUND": ErrorPolicy(
            code="E_DEFINIZIONE_NOT_FOUND",
            http_status=404,
            ui_action="show_empty_state",
            user_message="Edizione di workflow o step non trovato.",
        ),
        # Guard di dominio delle edizioni di workflow versionate: marker DB SENZA
        # prefisso E_ (substring stabili del catalogo, mappati in
        # pratiche_service._KNOWN_DB_ERROR_MARKERS). Senza policy esplicita il
        # fallback E_* non li copre → cadrebbero sul 500 generico invece del
        # banner 4xx parlante atteso dall'editor (api.md §Errori).
        "DEFINIZIONE_NON_TROVATA": ErrorPolicy(
            code="DEFINIZIONE_NON_TROVATA",
            http_status=404,
            ui_action="show_error_banner",
            user_message="Nessuna definizione di workflow pubblicata per questo tipo.",
        ),
        "FLUSSI_TEMPLATE_FUORI_DEFINIZIONE": ErrorPolicy(
            code="FLUSSI_TEMPLATE_FUORI_DEFINIZIONE",
            http_status=409,
            ui_action="show_error_banner",
            user_message="Lo step non appartiene alla definizione della pratica.",
        ),
        "DEFINIZIONE_NON_PUBBLICABILE": ErrorPolicy(
            code="DEFINIZIONE_NON_PUBBLICABILE",
            http_status=422,
            ui_action="show_error_banner",
            user_message="La bozza non e' pubblicabile: servono almeno uno step "
                         "attivo e nessun ciclo di prerequisiti.",
        ),
        "DEFINIZIONE_PUBBLICATA_IMMUTABILE": ErrorPolicy(
            code="DEFINIZIONE_PUBBLICATA_IMMUTABILE",
            http_status=409,
            ui_action="show_error_banner",
            user_message="Edizione non modificabile nello stato corrente.",
        ),
        "DEFINIZIONE_TRANSIZIONE_NON_AMMESSA": ErrorPolicy(
            code="DEFINIZIONE_TRANSIZIONE_NON_AMMESSA",
            http_status=409,
            ui_action="show_error_banner",
            user_message="Transizione di stato dell'edizione non ammessa.",
        ),
        "DEFINIZIONE_BOZZA_ESISTENTE": ErrorPolicy(
            code="DEFINIZIONE_BOZZA_ESISTENTE",
            http_status=409,
            ui_action="show_error_banner",
            user_message="Esiste gia' una bozza di edizione per questo scope "
                         "(tipo prestazione + emittente).",
        ),
        "DEFINIZIONE_NO_PUBBLICATA": ErrorPolicy(
            code="DEFINIZIONE_NO_PUBBLICATA",
            http_status=409,
            ui_action="show_error_banner",
            user_message="Nuova versione non ammessa: manca un'edizione "
                         "pubblicata da cui derivare.",
        ),
        "TEMPLATE_DEFINIZIONE_CONGELATA": ErrorPolicy(
            code="TEMPLATE_DEFINIZIONE_CONGELATA",
            http_status=409,
            ui_action="show_error_banner",
            user_message="Edizione per-emittente gia' emessa: la struttura non e' "
                         "piu' modificabile (solo la descrizione e' correggibile).",
        ),
        # Sospensioni con data manuale (catalogo DB id 498/499):
        # EXCLUDE ex_sospensioni_no_overlap (23P01) e guard a10 data non futura.
        "E_SOSPENSIONE_OVERLAP": ErrorPolicy(
            code="E_SOSPENSIONE_OVERLAP",
            http_status=409,
            ui_action="show_error_banner",
            user_message="Esiste gia' una sospensione che copre questo periodo "
                         "per la stessa pratica o lo stesso flusso.",
        ),
        "E_SOSPENSIONE_DATA_FUTURA": ErrorPolicy(
            code="E_SOSPENSIONE_DATA_FUTURA",
            http_status=422,
            ui_action="show_error_banner",
            user_message="La data della sospensione non puo' essere nel futuro.",
        ),
        # CHECK chk_sospensioni_data_fine: data_fine di riattivazione anteriore
        # all'inizio della sospensione (data manuale retroattiva incoerente).
        "E_SOSPENSIONE_DATA_FINE": ErrorPolicy(
            code="E_SOSPENSIONE_DATA_FINE",
            http_status=422,
            ui_action="show_error_banner",
            user_message="La data di riattivazione deve essere successiva "
                         "all'inizio della sospensione.",
        ),
        "E_FLUSSO_VALIDATION": ErrorPolicy(
            code="E_FLUSSO_VALIDATION",
            http_status=400,
            ui_action="highlight_form_fields",
            user_message="Parametri flusso non validi.",
        ),
        "E_FLUSSO_NOT_FOUND": ErrorPolicy(
            code="E_FLUSSO_NOT_FOUND",
            http_status=404,
            ui_action="show_empty_state",
            user_message="Flusso non trovato.",
        ),
        "E_FLUSSO_OWNERSHIP": ErrorPolicy(
            code="E_FLUSSO_OWNERSHIP",
            http_status=400,
            ui_action="show_error_banner",
            user_message="Flusso non appartiene alla pratica indicata.",
        ),
        "E_SOSPENSIONE_NOT_FOUND": ErrorPolicy(
            code="E_SOSPENSIONE_NOT_FOUND",
            http_status=404,
            ui_action="show_empty_state",
            user_message="Sospensione non trovata o gia' chiusa.",
        ),
        # Guard transizione pratiche/flussi: codici del catalogo DB (301/302)
        # sollevati dai trigger trgfn_pratiche/flussi_guard_transizione via
        # script.fn_log_and_raise_error. Chiave SENZA prefisso E_ = codice DB
        # verbatim (allineata al resto della famiglia pratiche workflow v2 sotto:
        # il service li intercetta via marker e rilancia ServiceError con lo
        # stesso codice). Con prefisso E_ ricadevano in E_GENERICO 500.
        "PRATICHE_TRANSIZIONE_NON_AMMESSA": ErrorPolicy(
            code="PRATICHE_TRANSIZIONE_NON_AMMESSA",
            http_status=409,
            ui_action="show_error_banner",
            user_message="Transizione di stato pratica non ammessa.",
        ),
        "FLUSSI_TRANSIZIONE_NON_AMMESSA": ErrorPolicy(
            code="FLUSSI_TRANSIZIONE_NON_AMMESSA",
            http_status=409,
            ui_action="show_error_banner",
            user_message="Transizione di stato flusso non ammessa.",
        ),
        "FLUSSI_ESITO_OBBLIGATORIO": ErrorPolicy(
            code="FLUSSI_ESITO_OBBLIGATORIO",
            http_status=409,
            ui_action="show_error_banner",
            user_message="Esito obbligatorio per completare il flusso.",
        ),
        # ── Presa in carico flusso: eligibilita' reparto-first (20260618-05) ──
        # Casi A/D (skill-lock): l'operatore non ha competenza attiva per il tipo
        # di step. Caso B (reparto, no skill): l'operatore non appartiene al
        # reparto anagrafico instradato. Entrambi sollevati da
        # pratiche.fn_prendi_in_carico_flusso e tradotti via marker nel service.
        "FLUSSI_COMPETENZA_MANCANTE": ErrorPolicy(
            code="FLUSSI_COMPETENZA_MANCANTE",
            http_status=409,
            ui_action="show_error_banner",
            user_message="Operatore non abilitato per questo tipo di flusso.",
        ),
        "FLUSSI_PRESA_NON_ELIGIBILE": ErrorPolicy(
            code="FLUSSI_PRESA_NON_ELIGIBILE",
            http_status=409,
            ui_action="show_error_banner",
            user_message="Presa in carico non consentita: il flusso e' instradato a un altro reparto.",
        ),
        # ── Pratiche workflow v2 (D1/D3/D4, analisi-pratiche-workflow-v2) ──
        # Codici del catalogo DB (messaggi_errore 483/484/485) sollevati dai
        # guard via script.fn_log_and_raise_error; il service li intercetta
        # via marker e rilancia ServiceError con lo stesso codice del DB.
        "PRATICHE_FLUSSO_NON_RIPETIBILE": ErrorPolicy(
            code="PRATICHE_FLUSSO_NON_RIPETIBILE",
            http_status=409,
            ui_action="show_error_banner",
            user_message="Il flusso non e' ripetibile in questa pratica.",
        ),
        "PRATICHE_LISTA_CONTESTO_PARAMETRI_ESCLUSIVI": ErrorPolicy(
            code="PRATICHE_LISTA_CONTESTO_PARAMETRI_ESCLUSIVI",
            http_status=400,
            ui_action="show_error_banner",
            user_message="Indicare una sola lente di contesto: ruolo soggetto, istanza utility o solo interne.",
        ),
        "PRATICHE_CHIUSURA_FLUSSI_OBBLIGATORI_MANCANTI": ErrorPolicy(
            code="PRATICHE_CHIUSURA_FLUSSI_OBBLIGATORI_MANCANTI",
            http_status=409,
            ui_action="show_error_banner",
            user_message="Impossibile chiudere la pratica: flussi obbligatori non completati.",
        ),
        # D1 hardening (brief-db-chiusura-pratica-nessun-lavoro-pendente, errore
        # catalogo 501): chiusura pratica con flussi ISTANZIATI ancora aperti (non
        # terminali). Guard condiviso chiusura manuale + auto-chiusura.
        "PRATICHE_CHIUSURA_FLUSSI_APERTI": ErrorPolicy(
            code="PRATICHE_CHIUSURA_FLUSSI_APERTI",
            http_status=409,
            ui_action="show_error_banner",
            user_message="Impossibile chiudere la pratica: ci sono flussi ancora aperti. Completali o annullali, poi riprova.",
        ),
        "PRATICHE_PREREQUISITI_NON_SODDISFATTI": ErrorPolicy(
            code="PRATICHE_PREREQUISITI_NON_SODDISFATTI",
            http_status=409,
            ui_action="show_error_banner",
            user_message="Flusso non ancora eseguibile: prerequisiti non soddisfatti.",
        ),
        "PRATICHE_TERMINALE_NUOVO_FLUSSO_BLOCCATO": ErrorPolicy(
            code="PRATICHE_TERMINALE_NUOVO_FLUSSO_BLOCCATO",
            http_status=409,
            ui_action="show_error_banner",
            user_message="Impossibile creare un flusso: la pratica e' in stato terminale.",
        ),
        "PRATICHE_TERMINALE_FLUSSO_NON_MODIFICABILE": ErrorPolicy(
            code="PRATICHE_TERMINALE_FLUSSO_NON_MODIFICABILE",
            http_status=409,
            ui_action="show_error_banner",
            user_message="Impossibile modificare il flusso: la pratica e' in stato terminale.",
        ),
        "PRATICHE_CHIUSURA_FLUSSO_PREMATURO": ErrorPolicy(
            code="PRATICHE_CHIUSURA_FLUSSO_PREMATURO",
            http_status=409,
            ui_action="show_error_banner",
            user_message="Impossibile completare il flusso di chiusura: restano altri flussi obbligatori da completare.",
        ),
        "E_SOSPENSIONI_FLUSSO_NON_COERENTE": ErrorPolicy(
            code="E_SOSPENSIONI_FLUSSO_NON_COERENTE",
            http_status=400,
            ui_action="show_error_banner",
            user_message="Il flusso non appartiene alla pratica della sospensione.",
        ),
        "E_CONFIG_MANCANTE": ErrorPolicy(
            code="E_CONFIG_MANCANTE",
            http_status=500,
            ui_action="show_error_banner",
            user_message="Configurazione mancante nel sistema.",
        ),
        # ── Config / Matrice utilities x tipi_ruolo ──
        "E_CONFIG_VALIDATION": ErrorPolicy(
            code="E_CONFIG_VALIDATION",
            http_status=400,
            ui_action="highlight_form_fields",
            user_message="Parametri di configurazione non validi.",
        ),
        "E_CONFIG_MATRICE_NOT_FOUND": ErrorPolicy(
            code="E_CONFIG_MATRICE_NOT_FOUND",
            http_status=404,
            ui_action="show_empty_state",
            user_message="Riga matrice utilities/ruoli non trovata.",
        ),
        "E_CONFIG_MATRICE_DUPLICATA": ErrorPolicy(
            code="E_CONFIG_MATRICE_DUPLICATA",
            http_status=409,
            ui_action="show_error_banner",
            user_message="Esiste gia' una riga matrice per questa coppia utility/tipo ruolo.",
        ),
        "E_CONFIG_MATRICE_FK": ErrorPolicy(
            code="E_CONFIG_MATRICE_FK",
            http_status=400,
            ui_action="highlight_form_fields",
            user_message="Utility o tipo ruolo inesistente.",
        ),
        "E_VALIDATION_INPUT": ErrorPolicy(
            code="E_VALIDATION_INPUT",
            http_status=400,
            ui_action="highlight_form_fields",
            user_message="Parametro di input non valido.",
        ),
        "E_INVALID_ID": ErrorPolicy(
            code="E_INVALID_ID",
            http_status=400,
            ui_action="highlight_form_fields",
            user_message="ID non valido.",
        ),
        "E_GENERICO": ErrorPolicy(
            code="E_GENERICO",
            http_status=500,
            ui_action="show_error_banner",
            user_message="Errore non gestito.",
        ),
        # ── Profilo utente ──
        "E_CORE_PROFILE_NOT_FOUND": ErrorPolicy(
            code="E_CORE_PROFILE_NOT_FOUND",
            http_status=404,
            ui_action="show_error_banner",
            user_message="Profilo utente non trovato.",
        ),
        # ── Permessi e autorizzazioni ──
        "E_USER_DISABILITATO": ErrorPolicy(
            code="E_USER_DISABILITATO",
            http_status=403,
            ui_action="show_error_banner",
            user_message="Utente disabilitato. Contattare l'amministratore.",
        ),
        "E_PERMESSO_NEGATO": ErrorPolicy(
            code="E_PERMESSO_NEGATO",
            http_status=403,
            ui_action="show_error_banner",
            user_message="Non hai i permessi per questa operazione.",
        ),
        "E_REPARTO_SENZA_PROFILO": ErrorPolicy(
            code="E_REPARTO_SENZA_PROFILO",
            http_status=403,
            ui_action="show_error_banner",
            user_message="Il reparto non ha ancora un profilo permessi configurato.",
        ),
        "E_VESTE_NON_ATTIVA": ErrorPolicy(
            code="E_VESTE_NON_ATTIVA",
            http_status=403,
            ui_action="show_error_banner",
            user_message="Non hai accesso a questo canale.",
        ),
        "E_JWT_SENZA_IDENTITA": ErrorPolicy(
            code="E_JWT_SENZA_IDENTITA",
            http_status=401,
            ui_action="redirect_login",
            user_message="Sessione scaduta: effettua nuovamente l'accesso.",
        ),
        "E_IDENTITA_NON_ATTIVA": ErrorPolicy(
            code="E_IDENTITA_NON_ATTIVA",
            http_status=401,
            ui_action="redirect_login",
            user_message="Sessione non piu' valida: effettua nuovamente l'accesso.",
        ),
        # ── Sessioni utente ──
        "E_LOGOUT_NO_TOKEN": ErrorPolicy(
            code="E_LOGOUT_NO_TOKEN",
            http_status=400,
            ui_action="show_error_banner",
            user_message="Token di refresh richiesto per il logout.",
        ),
        "E_SESSIONE_NOT_FOUND": ErrorPolicy(
            code="E_SESSIONE_NOT_FOUND",
            http_status=404,
            ui_action="show_error_banner",
            user_message="Sessione non trovata o gia' revocata.",
        ),
        "E_SESSIONE_REVOCA_CORRENTE": ErrorPolicy(
            code="E_SESSIONE_REVOCA_CORRENTE",
            http_status=400,
            ui_action="show_error_banner",
            user_message="Non puoi revocare la sessione corrente. Usa il logout.",
        ),
        # ── Anagrafiche / Gestione geografica ──
        "E_ANAG_VALIDAZIONE": ErrorPolicy(
            code="E_ANAG_VALIDAZIONE",
            http_status=400,
            ui_action="highlight_form_fields",
            user_message="Parametri anagrafiche non validi.",
        ),
        "E_ANAG_DUPLICATO": ErrorPolicy(
            code="E_ANAG_DUPLICATO",
            http_status=409,
            ui_action="show_error_banner",
            user_message="Record gia' esistente.",
        ),
        "E_ANAG_NOT_FOUND": ErrorPolicy(
            code="E_ANAG_NOT_FOUND",
            http_status=404,
            ui_action="show_empty_state",
            user_message="Record non trovato.",
        ),
        # ── Matrice categorie_clienti_listini (sviluppo-listini v5 §4.2) ──
        "E_ANAG_FK": ErrorPolicy(
            code="E_ANAG_FK",
            http_status=400,
            ui_action="highlight_form_fields",
            user_message="Riferimento non valido: l'entita' indicata non esiste.",
        ),
        "E_ANAG_MATRICE_OVERLAP": ErrorPolicy(
            code="E_ANAG_MATRICE_OVERLAP",
            http_status=409,
            ui_action="show_error_banner",
            user_message="Esiste gia' una riga attiva che si sovrappone per "
                         "questa combinazione di dimensioni nel periodo indicato.",
        ),
        # ── Refactor operatore-emittenti (Q6 + D3) ──
        "E_BA_ADMIN_GLOBALE_VIETATO": ErrorPolicy(
            code="E_BA_ADMIN_GLOBALE_VIETATO",
            http_status=403,
            ui_action="show_error_banner",
            user_message="Un amministratore globale non puo' creare billing "
                         "account quando esistono emittenti fiscali. Operare "
                         "come operatore di un emittente specifico.",
        ),
        "E_EMITTENTE_NON_MODIFICABILE": ErrorPolicy(
            code="E_EMITTENTE_NON_MODIFICABILE",
            http_status=400,
            ui_action="show_error_banner",
            user_message="L'emittente fiscale di un operatore e' immutabile. "
                         "Per cambiare l'associazione disattivare l'utente e "
                         "crearne uno nuovo per l'altro emittente.",
        ),
        "E_USER_EMITTENTE_DELETE_VIETATO": ErrorPolicy(
            code="E_USER_EMITTENTE_DELETE_VIETATO",
            http_status=400,
            ui_action="show_error_banner",
            user_message="Eliminazione vietata: l'associazione utente-emittente "
                         "puo' essere rimossa solo come parte della "
                         "disattivazione utente.",
        ),
        # ── Fornitori — normalize+guard payload pagamento/fiscali ──
        # Fase 2 refactor anagrafiche (landed 2026-04-27). Trigger DB:
        # anagrafiche.trgfn_fornitori_guard_normalize (raise se
        # ritenuta_acconto=true AND ritenuta_aliquota IS NULL/<=0). Codice
        # seedato in config.messaggi_errore (id 398).
        # Il gemello clienti (E_CLIENTI_GIORNI_SCADENZA_OBBLIGATORI) e' stato
        # RITIRATO il 2026-07-31 con la DROP del trigger normalize e delle
        # colonne tipo_gg_scadenza_ft/nr_giorni_scadenza (riforma D-I,
        # piano-db-satelliti 3a.5): le condizioni di pagamento cliente passano
        # da config.termini_pagamento e il guard non e' piu' raggiungibile.
        "E_FORNITORI_RITENUTA_ALIQUOTA_OBBLIGATORIA": ErrorPolicy(
            code="E_FORNITORI_RITENUTA_ALIQUOTA_OBBLIGATORIA",
            http_status=400,
            ui_action="highlight_form_fields",
            user_message=(
                "Aliquota ritenuta obbligatoria (> 0) quando ritenuta d'acconto "
                "e' attiva."
            ),
        ),
        # ── Contatti inline (Fase 5 refactor anagrafiche, 2026-04-28) ──
        # Sollevato dal classify centralizzato apps/anagrafiche/services/
        # contatti_service.py::classify_contatto_payload quando il payload
        # contatto inline (in create cliente/fornitore/soggetto) e' parziale
        # (almeno un campo valorizzato, ma mancano nominativo o
        # tipo_contatto_id). Sostituisce il vecchio "silent skip" che
        # faceva perdere dati senza preavviso.
        "E_CONTATTO_INCOMPLETO": ErrorPolicy(
            code="E_CONTATTO_INCOMPLETO",
            http_status=400,
            ui_action="highlight_form_fields",
            user_message=(
                "Contatto incompleto: hai inserito qualche dato ma mancano i "
                "campi obbligatori (nominativo e tipo contatto). Completa il "
                "contatto oppure svuota tutti i campi."
            ),
        ),
        # ── Anagrafiche / Soggetti e trigger ──
        "E_INDIRIZZO_OBBLIGATORIO_MANCANTE": ErrorPolicy(
            code="E_INDIRIZZO_OBBLIGATORIO_MANCANTE",
            http_status=400,
            ui_action="show_error_banner",
            user_message="Indirizzo obbligatorio mancante per questo tipo soggetto.",
        ),
        "E_SOGGETTO_NO_CONTATTI": ErrorPolicy(
            code="E_SOGGETTO_NO_CONTATTI",
            http_status=400,
            ui_action="show_error_banner",
            user_message="Il soggetto deve avere almeno un contatto.",
        ),
        "E_DATI_SOCIETARI_REQUIRED_MANCANTI": ErrorPolicy(
            code="E_DATI_SOCIETARI_REQUIRED_MANCANTI",
            http_status=400,
            ui_action="show_error_banner",
            user_message="Dati societari obbligatori mancanti per questo tipo soggetto.",
        ),
        "E_RUOLO_NATURA_NON_AMMESSA": ErrorPolicy(
            code="E_RUOLO_NATURA_NON_AMMESSA",
            http_status=400,
            ui_action="show_error_banner",
            user_message="Tipo soggetto non ammesso per questo ruolo.",
        ),
        "E_CF_OBBLIGATORIO": ErrorPolicy(
            code="E_CF_OBBLIGATORIO",
            http_status=400,
            ui_action="highlight_form_fields",
            user_message="Codice fiscale obbligatorio.",
        ),
        "E_PIVA_OBBLIGATORIA": ErrorPolicy(
            code="E_PIVA_OBBLIGATORIA",
            http_status=400,
            ui_action="highlight_form_fields",
            user_message="Partita IVA obbligatoria.",
        ),
        "E_ADMIN_CF_DUPLICATO": ErrorPolicy(
            code="E_ADMIN_CF_DUPLICATO",
            http_status=409,
            ui_action="show_error_banner",
            user_message="Codice fiscale gia' presente in anagrafica.",
        ),
        "E_ADMIN_PIVA_DUPLICATA": ErrorPolicy(
            code="E_ADMIN_PIVA_DUPLICATA",
            http_status=409,
            ui_action="show_error_banner",
            user_message="Partita IVA gia' presente in anagrafica.",
        ),
        "E_ADMIN_USERNAME_DUPLICATO": ErrorPolicy(
            code="E_ADMIN_USERNAME_DUPLICATO",
            http_status=409,
            ui_action="show_error_banner",
            user_message="Username gia' in uso.",
        ),
        "E_ADMIN_EMAIL_DUPLICATA": ErrorPolicy(
            code="E_ADMIN_EMAIL_DUPLICATA",
            http_status=409,
            ui_action="show_error_banner",
            user_message="Email gia' in uso.",
        ),
        "E_ATTIVO_BLOCK_CHILDREN_EXIST": ErrorPolicy(
            code="E_ATTIVO_BLOCK_CHILDREN_EXIST",
            http_status=409,
            ui_action="show_error_banner",
            user_message="Impossibile disattivare: esistono record collegati ancora attivi.",
        ),
        "E_DEFAULT_CONTATTO_MISSING": ErrorPolicy(
            code="E_DEFAULT_CONTATTO_MISSING",
            http_status=400,
            ui_action="show_error_banner",
            user_message="Contatto principale obbligatorio.",
        ),
        # ── Profilo utente / login guard ──
        "E_UTENTE_DISABILITATO": ErrorPolicy(
            code="E_UTENTE_DISABILITATO",
            http_status=403,
            ui_action="show_error_banner",
            user_message="Account disabilitato. Contattare l'amministratore.",
        ),
        "E_UTENTE_NON_ATTIVO": ErrorPolicy(
            code="E_UTENTE_NON_ATTIVO",
            http_status=403,
            ui_action="show_error_banner",
            user_message="Account non ancora attivo.",
        ),
        "E_UTENTE_SCADUTO": ErrorPolicy(
            code="E_UTENTE_SCADUTO",
            http_status=403,
            ui_action="show_error_banner",
            user_message="Account scaduto. Contattare l'amministratore.",
        ),
        # ── Amministrazione software ──
        "E_ADMIN_VALIDAZIONE": ErrorPolicy(
            code="E_ADMIN_VALIDAZIONE",
            http_status=400,
            ui_action="highlight_form_fields",
            user_message="Parametri non validi.",
        ),
        "E_AMM_VALIDAZIONE": ErrorPolicy(
            code="E_AMM_VALIDAZIONE",
            http_status=400,
            ui_action="highlight_form_fields",
            user_message="Parametri amministrazione non validi.",
        ),
        "E_AMM_UTENTE_NOT_FOUND": ErrorPolicy(
            code="E_AMM_UTENTE_NOT_FOUND",
            http_status=404,
            ui_action="show_empty_state",
            user_message="Utente non trovato.",
        ),
        "E_ADMIN_ULTIMO": ErrorPolicy(
            code="E_ADMIN_ULTIMO",
            http_status=409,
            ui_action="show_error_banner",
            user_message="Impossibile disabilitare l'ultimo amministratore.",
        ),
        # Multi-face: code sollevato dal trigger DB
        # `trgfn_profili_accesso_bindings_guard_ultimo_super_admin` quando
        # un'operazione (disabilita identita, demote SUPER_ADMIN, delete
        # binding) lascerebbe il sistema senza alcun super admin attivo.
        # Sostituisce E_ADMIN_ULTIMO post-cutover (Fase 1 multi-face); il
        # service preserva il code originale del DB anche quando il preview
        # `can_disable` lato detail aveva valutato true (race tra sessioni).
        "E_PROFILO_ULTIMO_SUPER_ADMIN": ErrorPolicy(
            code="E_PROFILO_ULTIMO_SUPER_ADMIN",
            http_status=409,
            ui_action="show_error_banner",
            user_message="Impossibile rimuovere l'ultimo super admin attivo.",
        ),
        # Fase 2 multi-face: payload `scope_mode` non ammesso per il
        # contratto attuale (es. MULTI post Q2, oppure SINGLE con array
        # vuoto/multi-elemento). Errore di validazione client-side, non
        # di stato del sistema.
        "E_AMM_SCOPE_NON_AMMESSO": ErrorPolicy(
            code="E_AMM_SCOPE_NON_AMMESSO",
            http_status=400,
            ui_action="show_error_banner",
            user_message="Scope emittenti non ammesso per la richiesta.",
        ),
        # Fase 5 audit hardening — codici stabili dal team DB.
        # I primi 3 sono per gli endpoint audit-summary/audit-sources/audit-log,
        # il quarto e' il refactor del guard scope di Fase 2 (prima passava per
        # RAISE EXCEPTION 22023 generico, ora ha codice stabile dal DB).
        "E_AUDIT_SUMMARY_PARAM_NON_VALIDO": ErrorPolicy(
            code="E_AUDIT_SUMMARY_PARAM_NON_VALIDO",
            http_status=400,
            ui_action="show_error_banner",
            user_message="Parametri audit non validi.",
        ),
        "E_AUDIT_SOURCE_NON_TROVATO": ErrorPolicy(
            code="E_AUDIT_SOURCE_NON_TROVATO",
            http_status=400,
            ui_action="show_error_banner",
            user_message="Sorgente audit non valida.",
        ),
        "E_AUDIT_SNAPSHOT_NON_TROVATO": ErrorPolicy(
            code="E_AUDIT_SNAPSHOT_NON_TROVATO",
            http_status=404,
            ui_action="show_empty_state",
            user_message="Snapshot audit non trovato.",
        ),
        "E_OPERATORE_SCOPE_PARAM_NON_VALIDO": ErrorPolicy(
            code="E_OPERATORE_SCOPE_PARAM_NON_VALIDO",
            http_status=400,
            ui_action="show_error_banner",
            user_message="Parametri scope operatore non validi.",
        ),
        "E_UTENTE_BLOCCATO": ErrorPolicy(
            code="E_UTENTE_BLOCCATO",
            http_status=423,
            ui_action="show_error_banner",
            user_message="Account temporaneamente bloccato per troppi tentativi.",
        ),
        # ── Vendite / Pipeline ──
        "E_PIPELINE_DOMINIO": ErrorPolicy(code="E_PIPELINE_DOMINIO", http_status=400, ui_action="show_error_banner", user_message="Errore dominio pipeline."),
        "E_PIPELINE_DOMINIO_NOT_FOUND": ErrorPolicy(code="E_PIPELINE_DOMINIO_NOT_FOUND", http_status=404, ui_action="show_empty_state", user_message="Dominio pipeline non trovato."),
        "E_PIPELINE_LOTTO_CRITICAL": ErrorPolicy(code="E_PIPELINE_LOTTO_CRITICAL", http_status=400, ui_action="show_error_banner", user_message="Lotto con segnalazioni critiche."),
        "E_PIPELINE_LOTTO_IN_ESECUZIONE": ErrorPolicy(code="E_PIPELINE_LOTTO_IN_ESECUZIONE", http_status=409, ui_action="show_error_banner", user_message="Lotto gia' in esecuzione."),
        "E_PIPELINE_MARK_ERROR": ErrorPolicy(code="E_PIPELINE_MARK_ERROR", http_status=400, ui_action="show_error_banner", user_message="Errore marcatura pipeline."),
        "E_PIPELINE_SCOPE_INCOMPLETE": ErrorPolicy(code="E_PIPELINE_SCOPE_INCOMPLETE", http_status=400, ui_action="highlight_form_fields", user_message="Scope pipeline incompleto."),
        "E_PIPELINE_STATO_LOTTO": ErrorPolicy(code="E_PIPELINE_STATO_LOTTO", http_status=409, ui_action="show_error_banner", user_message="Stato lotto non compatibile con l'operazione."),
        "E_PIPELINE_TASK": ErrorPolicy(code="E_PIPELINE_TASK", http_status=400, ui_action="show_error_banner", user_message="Errore task pipeline."),
        "E_PIPELINE_TASK_HANDLER_NOT_FOUND": ErrorPolicy(code="E_PIPELINE_TASK_HANDLER_NOT_FOUND", http_status=404, ui_action="show_error_banner", user_message="Handler task non trovato."),
        "E_RESET_LOTTO_VALIDATION": ErrorPolicy(code="E_RESET_LOTTO_VALIDATION", http_status=400, ui_action="highlight_form_fields", user_message="Parametri reset lotto non validi."),
        "E_RESET_LOTTO_FATTURA_VALIDATION": ErrorPolicy(code="E_RESET_LOTTO_FATTURA_VALIDATION", http_status=400, ui_action="highlight_form_fields", user_message="Parametri reset fattura non validi."),
        "E_GENERATE_FATTURE_RIGHE_VALIDATION": ErrorPolicy(code="E_GENERATE_FATTURE_RIGHE_VALIDATION", http_status=400, ui_action="highlight_form_fields", user_message="Parametri generazione righe non validi."),
        "E_TASK": ErrorPolicy(code="E_TASK", http_status=400, ui_action="show_error_banner", user_message="Errore esecuzione task."),
        "E_TASK_FATTURA": ErrorPolicy(code="E_TASK_FATTURA", http_status=400, ui_action="show_error_banner", user_message="Errore task fattura."),
        "E_TASK_IMPLEMENTATION_NOT_FOUND": ErrorPolicy(code="E_TASK_IMPLEMENTATION_NOT_FOUND", http_status=404, ui_action="show_error_banner", user_message="Implementazione task non trovata."),
        "E_TASK_RESET_REQUIRED": ErrorPolicy(code="E_TASK_RESET_REQUIRED", http_status=409, ui_action="show_error_banner", user_message="Reset necessario prima di rieseguire."),
        "E_TIPO_FONDO_NOT_FOUND": ErrorPolicy(code="E_TIPO_FONDO_NOT_FOUND", http_status=404, ui_action="show_empty_state", user_message="Tipo fondo non trovato."),
        # ── Commesse ──
        "E_COMMESSA_SORGENTE_SCONOSCIUTA": ErrorPolicy(code="E_COMMESSA_SORGENTE_SCONOSCIUTA", http_status=400, ui_action="show_error_banner", user_message="Sorgente commessa sconosciuta."),
        "E_PULL_COMMESSA": ErrorPolicy(code="E_PULL_COMMESSA", http_status=400, ui_action="show_error_banner", user_message="Errore pull commessa."),
        "E_PULL_COMMESSA_ALL_FAILED": ErrorPolicy(code="E_PULL_COMMESSA_ALL_FAILED", http_status=400, ui_action="show_error_banner", user_message="Tutti i pull commessa falliti."),
        "E_GROUP_ATTIVITA_VALIDATION": ErrorPolicy(code="E_GROUP_ATTIVITA_VALIDATION", http_status=400, ui_action="highlight_form_fields", user_message="Parametri gruppo attivita non validi."),
        "E_GROUP_ATTIVITA_NOT_FOUND": ErrorPolicy(code="E_GROUP_ATTIVITA_NOT_FOUND", http_status=404, ui_action="show_empty_state", user_message="Gruppo attivita non trovato."),
        "E_GROUP_ATTIVITA_INVALID_DATA": ErrorPolicy(code="E_GROUP_ATTIVITA_INVALID_DATA", http_status=400, ui_action="show_error_banner", user_message="Dati gruppo attivita non validi."),
        # ── Generazione righe fattura: kit (brief-fix-importi-riga-fattura-zero §4.7-bis) ──
        # Dati incoerenti a monte, non input dell'utente: 409 e banner, perche' la
        # correzione sta sul documento sorgente e non su questa schermata.
        "E_ATTIVITA_KIT_SENZA_PADRE": ErrorPolicy(code="E_ATTIVITA_KIT_SENZA_PADRE", http_status=409, ui_action="show_error_banner", user_message="Componente di kit senza articolo padre: correggere il documento di origine."),
        "E_KIT_QUANTITA_DISOMOGENEE": ErrorPolicy(code="E_KIT_QUANTITA_DISOMOGENEE", http_status=409, ui_action="show_error_banner", user_message="Componenti dello stesso kit con quantita diverse: la fattura non e' rappresentabile."),
        # Difetto di programmazione, non condizione di dominio: 500.
        "E_BATCH_ARRAY_DISALLINEATI": ErrorPolicy(code="E_BATCH_ARRAY_DISALLINEATI", http_status=500, ui_action="show_error_banner", user_message="Errore interno nella generazione delle righe."),
        # ── Autenticazione ──
        "E_AUTHENTICATION_FAILED": ErrorPolicy(code="E_AUTHENTICATION_FAILED", http_status=401, ui_action="show_error_banner", user_message="Autenticazione fallita."),
        "E_NOT_AUTHENTICATED": ErrorPolicy(code="E_NOT_AUTHENTICATED", http_status=401, ui_action="show_error_banner", user_message="Non autenticato."),
        "E_PERMISSION_DENIED": ErrorPolicy(code="E_PERMISSION_DENIED", http_status=403, ui_action="show_error_banner", user_message="Permesso negato."),
        # ── Ricerca universale ──
        "E_SEARCH_VALIDATION": ErrorPolicy(
            code="E_SEARCH_VALIDATION",
            http_status=400,
            ui_action="highlight_form_fields",
            user_message="Parametri ricerca non validi.",
        ),
        "E_SEARCH_NOT_FOUND": ErrorPolicy(
            code="E_SEARCH_NOT_FOUND",
            http_status=404,
            ui_action="show_empty_state",
            user_message="Nessun risultato trovato.",
        ),
        # ── Assistente AI ──
        "E_AI_DISABLED": ErrorPolicy(
            code="E_AI_DISABLED",
            http_status=501,
            ui_action="show_error_banner",
            user_message="Funzionalita' assistente AI non attiva.",
        ),
        "E_AI_PROVIDER_UNKNOWN": ErrorPolicy(
            code="E_AI_PROVIDER_UNKNOWN",
            http_status=500,
            ui_action="show_error_banner",
            user_message="Provider AI non riconosciuto.",
        ),
        "E_AI_PROVIDER_ERROR": ErrorPolicy(
            code="E_AI_PROVIDER_ERROR",
            http_status=502,
            ui_action="show_error_banner",
            user_message="Errore nella comunicazione con il provider AI.",
        ),
        "E_AI_QUERY_EMPTY": ErrorPolicy(
            code="E_AI_QUERY_EMPTY",
            http_status=400,
            ui_action="highlight_form_fields",
            user_message="Il messaggio non puo' essere vuoto.",
        ),
        "E_AI_QUERY_TOO_LONG": ErrorPolicy(
            code="E_AI_QUERY_TOO_LONG",
            http_status=400,
            ui_action="highlight_form_fields",
            user_message="Il messaggio supera la lunghezza massima consentita.",
        ),
        # ── Shop B2C (stub PR-C) ──
        # §8.4.3/§8.4.4/§8.4.5: endpoint shop rispondono 501 finche' PR-C
        # non porta il MVP. Codice dedicato (non E_TASK_NOT_IMPLEMENTED
        # che e' del dominio pipeline fatturazione).
        "E_SHOP_NON_DISPONIBILE": ErrorPolicy(
            code="E_SHOP_NON_DISPONIBILE",
            http_status=501,
            ui_action="show_info_banner",
            user_message="Shop non ancora disponibile. In arrivo con PR-C.",
        ),
        "E_AI_TOOL_NOT_FOUND": ErrorPolicy(
            code="E_AI_TOOL_NOT_FOUND",
            http_status=500,
            ui_action="show_error_banner",
            user_message="Strumento AI richiesto non disponibile.",
        ),
        "E_AI_TOOL_DENIED": ErrorPolicy(
            code="E_AI_TOOL_DENIED",
            http_status=403,
            ui_action="show_error_banner",
            user_message="Non hai i permessi per questo strumento AI.",
        ),
        "E_AI_CONFIRMATION_REQUIRED": ErrorPolicy(
            code="E_AI_CONFIRMATION_REQUIRED",
            http_status=428,
            ui_action="show_error_banner",
            user_message="Operazione in scrittura: conferma esplicita richiesta.",
        ),
        # --- Autenticazione: token, email, invito, cambio/reset password ---
        "E_TOKEN": ErrorPolicy(
            code="E_TOKEN",
            http_status=400,
            ui_action="show_error_banner",
            user_message="Token non valido, scaduto o gia' utilizzato.",
        ),
        "E_EMAIL": ErrorPolicy(
            code="E_EMAIL",
            http_status=400,
            ui_action="show_error_banner",
            user_message="Errore configurazione email.",
        ),
        "E_OUTBOX": ErrorPolicy(
            code="E_OUTBOX",
            http_status=400,
            ui_action="show_error_banner",
            user_message="Errore gestione bozza email.",
        ),
        "E_INVITO_OPERATORE": ErrorPolicy(
            code="E_INVITO_OPERATORE",
            http_status=400,
            ui_action="show_error_banner",
            user_message="Operatore non invitabile.",
        ),
        "E_CHANGE_PASSWORD": ErrorPolicy(
            code="E_CHANGE_PASSWORD",
            http_status=400,
            ui_action="show_error_banner",
            user_message="Errore cambio password.",
        ),
        "E_RESET_PASSWORD": ErrorPolicy(
            code="E_RESET_PASSWORD",
            http_status=400,
            ui_action="show_error_banner",
            user_message="Errore reset password.",
        ),
        "E_ATTIVAZIONE": ErrorPolicy(
            code="E_ATTIVAZIONE",
            http_status=400,
            ui_action="show_error_banner",
            user_message="Errore attivazione account.",
        ),
        "E_INVITO_PORTALE": ErrorPolicy(
            code="E_INVITO_PORTALE",
            http_status=400,
            ui_action="show_error_banner",
            user_message="Invito portale non inviabile.",
        ),
        "E_ATTIVAZIONE_PORTALE": ErrorPolicy(
            code="E_ATTIVAZIONE_PORTALE",
            http_status=400,
            ui_action="show_error_banner",
            user_message="Errore attivazione account portale.",
        ),
        # B1 §13.7: codici dedicati attivazione shop (simmetrici al portale).
        "E_ATTIVAZIONE_SHOP": ErrorPolicy(
            code="E_ATTIVAZIONE_SHOP",
            http_status=400,
            ui_action="show_error_banner",
            user_message="Errore attivazione account shop.",
        ),
        "E_ATTIVAZIONE_SHOP_CROSS": ErrorPolicy(
            code="E_ATTIVAZIONE_SHOP_CROSS",
            http_status=400,
            ui_action="show_error_banner",
            user_message="Errore attivazione veste shop dal profilo portale.",
        ),
        # ── Codici cross-schema da refactor E_GENERICO (31 marzo 2026) ──
        # --- Validazione parametri (400) ---
        "E_PARAMETRO_INVALIDO": ErrorPolicy(
            code="E_PARAMETRO_INVALIDO",
            http_status=400,
            ui_action="highlight_form_fields",
            user_message="Parametro obbligatorio mancante o non valido.",
        ),
        "E_VALORE_MANCANTE": ErrorPolicy(
            code="E_VALORE_MANCANTE",
            http_status=400,
            ui_action="highlight_form_fields",
            user_message="Valore obbligatorio mancante.",
        ),
        "E_CODICE": ErrorPolicy(
            code="E_CODICE",
            http_status=400,
            ui_action="show_error_banner",
            user_message="Codice di configurazione non trovato.",
        ),
        "E_DATA_AL_MINORE_DAL": ErrorPolicy(
            code="E_DATA_AL_MINORE_DAL",
            http_status=400,
            ui_action="highlight_form_fields",
            user_message="La data 'al' non puo' essere anteriore alla data 'dal'.",
        ),
        "E_TIPI_RUOLI_ENTITA_INVALIDA": ErrorPolicy(
            code="E_TIPI_RUOLI_ENTITA_INVALIDA",
            http_status=400,
            ui_action="show_error_banner",
            user_message="Configurazione tipo ruolo non valida.",
        ),
        # --- Coerenza dati (400) ---
        "E_PDP_OBBLIGATORIO": ErrorPolicy(
            code="E_PDP_OBBLIGATORIO",
            http_status=400,
            ui_action="show_error_banner",
            user_message="Piano dati precontrattuali obbligatorio.",
        ),
        "E_PDP_UTILITY_MISMATCH": ErrorPolicy(
            code="E_PDP_UTILITY_MISMATCH",
            http_status=400,
            ui_action="show_error_banner",
            user_message="Utility non coerente con il piano dati precontrattuali.",
        ),
        "E_CLIENTE_UTILITY_MISMATCH_BA": ErrorPolicy(
            code="E_CLIENTE_UTILITY_MISMATCH_BA",
            http_status=400,
            ui_action="show_error_banner",
            user_message="Utility non coerente con il billing account del cliente.",
        ),
        "E_BILLING_ACCOUNT_UTILITY_NULL": ErrorPolicy(
            code="E_BILLING_ACCOUNT_UTILITY_NULL",
            http_status=400,
            ui_action="show_error_banner",
            user_message="Billing account senza utility associata.",
        ),
        "E_UTILITY_RUOLO_NON_AMMESSO": ErrorPolicy(
            code="E_UTILITY_RUOLO_NON_AMMESSO",
            http_status=400,
            ui_action="show_error_banner",
            user_message="Tipo ruolo non ammesso per questa utility.",
        ),
        "E_LOTTO_PARAMETRO_NON_COERENTE": ErrorPolicy(
            code="E_LOTTO_PARAMETRO_NON_COERENTE",
            http_status=400,
            ui_action="show_error_banner",
            user_message="Parametri lotto non coerenti.",
        ),
        "E_COMMESSA_ATTIVITA_NON_COERENTE": ErrorPolicy(
            code="E_COMMESSA_ATTIVITA_NON_COERENTE",
            http_status=400,
            ui_action="show_error_banner",
            user_message="Attivita' non coerente con la commessa.",
        ),
        "E_RIGA_GIA_FATTURATA": ErrorPolicy(
            code="E_RIGA_GIA_FATTURATA",
            http_status=409,
            ui_action="show_error_banner",
            user_message="Riga gia' fatturata.",
        ),
        "E_PREZZO_LISTINO_AMBIGUO": ErrorPolicy(
            code="E_PREZZO_LISTINO_AMBIGUO",
            http_status=409,
            ui_action="show_error_banner",
            user_message="Piu' prezzi trovati per lo stesso articolo/listino.",
        ),
        # --- Not found (404) ---
        "E_FATTURA_NON_TROVATA": ErrorPolicy(
            code="E_FATTURA_NON_TROVATA",
            http_status=404,
            ui_action="show_empty_state",
            user_message="Fattura non trovata.",
        ),
        "E_LOTTO_NON_TROVATO": ErrorPolicy(
            code="E_LOTTO_NON_TROVATO",
            http_status=404,
            ui_action="show_empty_state",
            user_message="Lotto non trovato.",
        ),
        # C-4: «Rendi definitive» su lotto non in EMESSA (gate fiscale I-7):
        # conflitto di stato (409), non un semplice bad-request.
        "E_LOTTO_NON_NUMERABILE": ErrorPolicy(
            code="E_LOTTO_NON_NUMERABILE",
            http_status=409,
            ui_action="show_error_banner",
            user_message="Il lotto non e` in stato EMESSA: numerazione non applicabile.",
        ),
        # C-8: ristampa massiva su lotto non DEFINITIVA (I-7: niente numerazione
        # backdoor via ristampa): conflitto di stato (409).
        "E_LOTTO_NON_RISTAMPABILE": ErrorPolicy(
            code="E_LOTTO_NON_RISTAMPABILE",
            http_status=409,
            ui_action="show_error_banner",
            user_message=(
                "Il lotto non e` definitivo: la ristampa massiva richiede fatture "
                "numerate (Rendi definitive)."
            ),
        ),
        # C-3: polling di un giro (job coda) inesistente o non di proprieta`
        # dell'operatore → 404 (senza registrazione cadrebbe sul fallback 400).
        "E_JOB_NON_TROVATO": ErrorPolicy(
            code="E_JOB_NON_TROVATO",
            http_status=404,
            ui_action="show_empty_state",
            user_message="Lavoro non trovato.",
        ),
        # UI gestione code (BE-7): annullo di un job non piu` PENDING →
        # conflitto di stato (il worker lo ha gia` preso, o e` terminato).
        "E_JOB_NON_ANNULLABILE": ErrorPolicy(
            code="E_JOB_NON_ANNULLABILE",
            http_status=409,
            ui_action="show_error_banner",
            user_message="Il lavoro non e` piu` in attesa: annullo non possibile.",
        ),
        # UI gestione code (BE-7): requeue di un job non IN_CORSO/ERRORE →
        # conflitto di stato (solo i bloccati/terminali si riaccodano).
        "E_JOB_NON_RIACCODABILE": ErrorPolicy(
            code="E_JOB_NON_RIACCODABILE",
            http_status=409,
            ui_action="show_error_banner",
            user_message="Il lavoro non e` riaccodabile nello stato corrente.",
        ),
        # Coda lavori generica (worker): codici sollevati durante il dispatch/
        # esecuzione dei job. Non attraversano HTTP nel flusso normale (finiscono
        # in `ultimo_errore` del job), ma la regola è: registrati prima dell'uso.
        "E_CODA_SCOPE_OPERATORE_INVALIDO": ErrorPolicy(
            code="E_CODA_SCOPE_OPERATORE_INVALIDO",
            http_status=400,
            ui_action="show_error_banner",
            user_message="Lavoro accodato con scope operatore incompleto.",
        ),
        "E_CODA_IDENTITA_NON_ATTIVA": ErrorPolicy(
            code="E_CODA_IDENTITA_NON_ATTIVA",
            http_status=409,
            ui_action="show_error_banner",
            user_message="Identità operatore non più attiva: lavoro non eseguibile.",
        ),
        "E_CODA_HANDLER_NON_REGISTRATO": ErrorPolicy(
            code="E_CODA_HANDLER_NON_REGISTRATO",
            http_status=500,
            ui_action="show_error_banner",
            user_message="Tipo di lavoro non cablato nel sistema.",
        ),
        "E_EMITTENTE_DEFAULT_MISSING": ErrorPolicy(
            code="E_EMITTENTE_DEFAULT_MISSING",
            http_status=404,
            ui_action="show_error_banner",
            user_message="Emittente fiscale default non configurato.",
        ),
        # --- Conflitto / azione bloccata (409) ---
        "E_LOTTO_NON_RIUTILIZZABILE": ErrorPolicy(
            code="E_LOTTO_NON_RIUTILIZZABILE",
            http_status=409,
            ui_action="show_error_banner",
            user_message="Lotto non riutilizzabile.",
        ),
        "E_CHIUDE_LOTTO_SINGLETON": ErrorPolicy(
            code="E_CHIUDE_LOTTO_SINGLETON",
            http_status=409,
            ui_action="show_error_banner",
            user_message="Un solo stato puo' avere il flag chiude_lotto attivo.",
        ),
        "E_EMITTENTE_DEFAULT_SINGLETON": ErrorPolicy(
            code="E_EMITTENTE_DEFAULT_SINGLETON",
            http_status=409,
            ui_action="show_error_banner",
            user_message="Un solo emittente fiscale puo' essere impostato come default.",
        ),
        "E_EMITTENTE_DISATTIVAZIONE_BLOCCATA": ErrorPolicy(
            code="E_EMITTENTE_DISATTIVAZIONE_BLOCCATA",
            http_status=409,
            ui_action="show_error_banner",
            user_message="Impossibile disattivare l'emittente fiscale: esistono entita' collegate.",
        ),
        "E_RESELLER_DISATTIVAZIONE_BLOCCATA": ErrorPolicy(
            code="E_RESELLER_DISATTIVAZIONE_BLOCCATA",
            http_status=409,
            ui_action="show_error_banner",
            user_message="Impossibile disattivare il reseller: esistono entita' collegate.",
        ),
        "E_COMMESSA_ROOT_CONFLITTO": ErrorPolicy(
            code="E_COMMESSA_ROOT_CONFLITTO",
            http_status=409,
            ui_action="show_error_banner",
            user_message="Conflitto: commessa root gia' esistente per questa sorgente.",
        ),
        # ── Preventivi vendita ──
        "E_PREV_NOT_FOUND": ErrorPolicy(
            code="E_PREV_NOT_FOUND",
            http_status=404,
            ui_action="show_empty_state",
            user_message="Preventivo non trovato.",
        ),
        "E_PREV_VALIDAZIONE": ErrorPolicy(
            code="E_PREV_VALIDAZIONE",
            http_status=400,
            ui_action="highlight_form_fields",
            user_message="Parametri preventivo non validi.",
        ),
        "E_PRICING_OVERRIDE_NON_AUTORIZZATO": ErrorPolicy(
            code="E_PRICING_OVERRIDE_NON_AUTORIZZATO",
            http_status=403,
            ui_action="show_error_banner",
            user_message=(
                "Modifica manuale del prezzo non autorizzata. Usa il prezzo "
                "suggerito dal listino o richiedi l'autorizzazione al responsabile."
            ),
        ),
        # Refactor 2026-05-20: user_message generico "Variazione prezzo" per
        # entrambi i codici. La distinzione SCONTO/MAGGIORAZIONE resta nel
        # codice errore + nel detail tecnico (segno della variazione) — utile
        # per workflow approvazione, dashboard e log, ma non per l'utente.
        # L'UX vede la direzione esplicita nel detail ("in diminuzione" /
        # "in aumento") generato da `_raise_or_return_violazione_l2`.
        "E_PRICING_SCONTO_ECCESSIVO": ErrorPolicy(
            code="E_PRICING_SCONTO_ECCESSIVO",
            http_status=403,
            ui_action="show_error_banner",
            user_message=(
                "Variazione prezzo oltre il limite consentito per il tuo ruolo. "
                "Richiedi approvazione o rientra nel limite ammesso."
            ),
        ),
        "E_PRICING_MAGGIORAZIONE_ECCESSIVA": ErrorPolicy(
            code="E_PRICING_MAGGIORAZIONE_ECCESSIVA",
            http_status=403,
            ui_action="show_error_banner",
            user_message=(
                "Variazione prezzo oltre il limite consentito per il tuo ruolo. "
                "Richiedi approvazione o rientra nel limite ammesso."
            ),
        ),
        # L3 Sprint E (sviluppo-listini-v5 §14.6) — workflow approvazione
        # prezzo out-of-policy. Codici sollevati da preventivi_service +
        # approvazioni_prezzo_service e dai trigger DB DB-E-4/E-5.
        "E_PREVENTIVO_RIGHE_PRICING_PENDENTI": ErrorPolicy(
            code="E_PREVENTIVO_RIGHE_PRICING_PENDENTI",
            http_status=409,
            ui_action="show_error_banner",
            user_message=(
                "Esistono righe con prezzo in attesa di approvazione. "
                "Attendi esito o annulla la richiesta prima di accettare il preventivo."
            ),
        ),
        "E_RIGA_PREZZO_PENDENTE": ErrorPolicy(
            code="E_RIGA_PREZZO_PENDENTE",
            http_status=409,
            ui_action="show_error_banner",
            user_message=(
                "La riga e' in attesa di approvazione: solo lo stato di approvazione "
                "e i campi audit sono modificabili."
            ),
        ),
        "E_APPROVAZIONE_PREZZO_NON_AMMESSA": ErrorPolicy(
            code="E_APPROVAZIONE_PREZZO_NON_AMMESSA",
            http_status=409,
            ui_action="show_error_banner",
            user_message="Operazione di approvazione prezzo non ammessa nello stato corrente.",
        ),
        "E_PREV_STATO_TRANSIZIONE": ErrorPolicy(
            code="E_PREV_STATO_TRANSIZIONE",
            http_status=409,
            ui_action="show_error_banner",
            user_message="Transizione di stato preventivo non ammessa.",
        ),
        # Ordini di vendita (scheletro CRUD + conferma + push singolo). Famiglia
        # speculare a E_PREV_*. I codici trigger DB (E_ORDINE_*) passano invece
        # via regex in ordini_service._db_errors.
        "E_ORD_NOT_FOUND": ErrorPolicy(
            code="E_ORD_NOT_FOUND",
            http_status=404,
            ui_action="show_empty_state",
            user_message="Ordine non trovato.",
        ),
        "E_ORD_VALIDAZIONE": ErrorPolicy(
            code="E_ORD_VALIDAZIONE",
            http_status=400,
            ui_action="highlight_form_fields",
            user_message="Parametri ordine non validi.",
        ),
        # Cliente (billing_account_id/soggetto_ruolo_id) immutabile post-create.
        # Sollevato sia dal guard BE (ordini_service.aggiorna_ordine) sia, come
        # difesa finale, dal lock-columns DB (automation_lock_columns,
        # DB-ORD-LOCK 2026-06-04, codice DB messaggi_errore id 469).
        "E_ORD_CLIENTE_IMMUTABILE": ErrorPolicy(
            code="E_ORD_CLIENTE_IMMUTABILE",
            http_status=400,
            ui_action="show_error_banner",
            user_message=(
                "Cliente immutabile dopo la creazione: per cambiare cliente "
                "crea un nuovo ordine."
            ),
        ),
        # Corsia di instradamento non piu' modificabile: il documento e' gia'
        # stato inviato in commessa, dove il flag entra nella chiave di dedup —
        # cambiarlo dopo non sposta nulla, sarebbe solo un campo che INGANNA.
        # Sollevato dal guard DB `trgfn_guard_fatturazione_immediata_immutabile`
        # su ordini/contratti/DDT/preventivi (codice DB messaggi_errore 561).
        # Trasversale ai 4 domini: il codice e' uno solo, come lo e' la regola.
        "E_FATT_IMMEDIATA_NON_MODIFICABILE": ErrorPolicy(
            code="E_FATT_IMMEDIATA_NON_MODIFICABILE",
            http_status=409,
            ui_action="show_error_banner",
            user_message=(
                "La fatturazione immediata non e` piu` modificabile: il "
                "documento e` gia` stato inviato in commessa. Per fatturare "
                "subito questo lavoro usa l'emissione mirata dal cruscotto "
                "Competenza."
            ),
        ),
        "E_ORD_STATO_TRANSIZIONE": ErrorPolicy(
            code="E_ORD_STATO_TRANSIZIONE",
            http_status=409,
            ui_action="show_error_banner",
            user_message="Operazione non ammessa nello stato corrente dell'ordine.",
        ),
        "E_ORD_NESSUNA_RIGA": ErrorPolicy(
            code="E_ORD_NESSUNA_RIGA",
            http_status=409,
            ui_action="show_error_banner",
            user_message="L'ordine non ha righe eleggibili per l'operazione.",
        ),
        # Conversione upstream (preventivo/offerta → ordine, §7.4): il documento
        # di origine non è in uno stato che ammette la generazione di un ordine
        # (es. preventivo non ancora ACCETTATO).
        "E_ORD_ORIGINE_NON_CONVERTIBILE": ErrorPolicy(
            code="E_ORD_ORIGINE_NON_CONVERTIBILE",
            http_status=409,
            ui_action="show_error_banner",
            user_message=(
                "Il documento di origine non è in uno stato che consente di "
                "generare un ordine."
            ),
        ),
        # Univocità 1:1 offerta→ordine (reversal parziale di A1, solo OFFERTA):
        # un'offerta genera al massimo un ordine. Sollevato dal guard BE
        # (ordini_service.crea_ordine_da_offerta) e, come rete sulla race, dalla
        # violazione dell'UNIQUE parziale uq_ordini_v_documento_origine_offerta.
        # Specchio applicativo della guard data-driven can_genera_ordine in
        # script.fn_available_actions_offerta (il bottone sparisce a conversione
        # avvenuta; questo errore copre il click concorrente cross-tab).
        "E_ORD_OFFERTA_GIA_CONVERTITA": ErrorPolicy(
            code="E_ORD_OFFERTA_GIA_CONVERTITA",
            http_status=409,
            ui_action="show_error_banner",
            user_message="Un ordine è già stato generato da questa offerta.",
        ),
        # DDT di vendita (CRUD + emissione + macchina a stati + evasione da
        # ordine + push singolo). Famiglia speculare a E_ORD_*. I codici trigger
        # DB (E_STATO_DDT_*, E_COMPONENTE_PREZZO_PENDENTE, E_QTA_SUPERA_RESIDUO)
        # passano invece via regex in ddt_service._db_errors: registrati qui per
        # fissare lo status/ui_action lato FE.
        "E_DDT_NOT_FOUND": ErrorPolicy(
            code="E_DDT_NOT_FOUND",
            http_status=404,
            ui_action="show_empty_state",
            user_message="DDT non trovato.",
        ),
        "E_DDT_VALIDAZIONE": ErrorPolicy(
            code="E_DDT_VALIDAZIONE",
            http_status=400,
            ui_action="highlight_form_fields",
            user_message="Parametri DDT non validi.",
        ),
        # Indirizzi documento (BB _indirizzi_documento_helpers, 5 domini):
        # sollevato da script.fn_snapshot_indirizzo (flusso picker) quando
        # origine_indirizzo_id non esiste piu' in anagrafiche.indirizzi.
        "E_INDIRIZZO_SNAPSHOT_NOT_FOUND": ErrorPolicy(
            code="E_INDIRIZZO_SNAPSHOT_NOT_FOUND",
            http_status=404,
            ui_action="show_error_banner",
            user_message=(
                "Indirizzo anagrafico non trovato: ricaricare gli indirizzi "
                "del cliente."
            ),
        ),
        # Trigger whitelist tipi indirizzo per ambito documento
        # (trgfn_tipi_indirizzi_only_allowed, fail-closed): ri-sollevato da
        # _db_errors del BB col codice originale del RAISE.
        "E_TIPO_INDIRIZZO": ErrorPolicy(
            code="E_TIPO_INDIRIZZO",
            http_status=400,
            ui_action="show_error_banner",
            user_message=(
                "Tipo indirizzo non ammesso per questo documento."
            ),
        ),
        # Guard DB all'emissione DDT (tipi obbligatori dell'ambito mancanti):
        # il FE previene (Conferma disabilitata), il trigger resta la fonte
        # di verita'.
        "E_INDIRIZZO_DOC_OBBLIGATORIO": ErrorPolicy(
            code="E_INDIRIZZO_DOC_OBBLIGATORIO",
            http_status=422,
            ui_action="show_error_banner",
            user_message=(
                "Indirizzo obbligatorio mancante: impostare l'indirizzo di "
                "consegna prima dell'emissione."
            ),
        ),
        # Cliente (billing_account_id/destinatario) immutabile post-create:
        # cambiare cliente = nuovo DDT (mirror E_ORD_CLIENTE_IMMUTABILE).
        "E_DDT_CLIENTE_IMMUTABILE": ErrorPolicy(
            code="E_DDT_CLIENTE_IMMUTABILE",
            http_status=400,
            ui_action="show_error_banner",
            user_message=(
                "Cliente immutabile dopo la creazione: per cambiare cliente "
                "crea un nuovo DDT."
            ),
        ),
        "E_DDT_STATO_TRANSIZIONE": ErrorPolicy(
            code="E_DDT_STATO_TRANSIZIONE",
            http_status=409,
            ui_action="show_error_banner",
            user_message="Operazione non ammessa nello stato corrente del DDT.",
        ),
        "E_DDT_NESSUNA_RIGA": ErrorPolicy(
            code="E_DDT_NESSUNA_RIGA",
            http_status=409,
            ui_action="show_error_banner",
            user_message="Il DDT non ha righe eleggibili per l'operazione.",
        ),
        # Evasione da ordine (fn_genera_ddt_da_ordine): l'ordine sorgente non
        # esiste, non e' in uno stato evadibile, o non ha residuo da evadere.
        "E_DDT_ORDINE_NOT_FOUND": ErrorPolicy(
            code="E_DDT_ORDINE_NOT_FOUND",
            http_status=404,
            ui_action="show_empty_state",
            user_message="Ordine di origine non trovato.",
        ),
        "E_DDT_ORDINE_STATO_NON_EVADIBILE": ErrorPolicy(
            code="E_DDT_ORDINE_STATO_NON_EVADIBILE",
            http_status=409,
            ui_action="show_error_banner",
            user_message=(
                "L'ordine non e' in uno stato che consente l'evasione (genera DDT)."
            ),
        ),
        "E_DDT_NIENTE_DA_EVADERE": ErrorPolicy(
            code="E_DDT_NIENTE_DA_EVADERE",
            http_status=409,
            ui_action="show_error_banner",
            user_message="Nessuna quantita' residua da evadere sull'ordine.",
        ),
        # Gate solo-trasporto all'emissione (trgfn_ddt_guard_causale_emissione,
        # DL-28): la causale di trasporto dichiara se la merce e' una vendita
        # da fatturare; obbligatoria a DRAFT->EMESSO, e se fatturabile ogni
        # riga attiva deve avere un prezzo risolvibile (proprio o ereditato
        # dall'ordine via fulfillment).
        "E_DDT_CAUSALE_OBBLIGATORIA": ErrorPolicy(
            code="E_DDT_CAUSALE_OBBLIGATORIA",
            http_status=409,
            ui_action="show_error_banner",
            user_message=(
                "Causale di trasporto obbligatoria per emettere il DDT."
            ),
        ),
        "E_DDT_PREZZO_NON_RISOLVIBILE": ErrorPolicy(
            code="E_DDT_PREZZO_NON_RISOLVIBILE",
            http_status=409,
            ui_action="show_error_banner",
            user_message=(
                "Causale fatturabile ma una riga del DDT non ha un prezzo "
                "risolvibile (proprio o ereditato dall'ordine)."
            ),
        ),
        # Codice sollevato dal trigger guard transizioni DDT
        # (trgfn_ddt_guard_transizione): la coppia (stato_attuale, stato_target)
        # non e' nella matrice config.transizioni_stati_ddt.
        "E_STATO_DDT_TRANSIZIONE_NON_VALIDA": ErrorPolicy(
            code="E_STATO_DDT_TRANSIZIONE_NON_VALIDA",
            http_status=409,
            ui_action="show_error_banner",
            user_message="Transizione di stato non ammessa per il DDT.",
        ),
        # Over-shipping: la quantita' da evadere supera il residuo dell'ordine.
        # Sollevato dal guard fulfillment DB (trgfn_ordini_ful_guard_consistenza)
        # in evasione multi-DDT (brief DB C2).
        "E_QTA_SUPERA_RESIDUO": ErrorPolicy(
            code="E_QTA_SUPERA_RESIDUO",
            http_status=409,
            ui_action="show_error_banner",
            user_message=(
                "La quantita' da evadere supera il residuo disponibile "
                "sull'ordine."
            ),
        ),
        # Gate emissione documento (trigger guard approvazione componenti BoM,
        # trgfn_*_guard_transizione_approvazione — DDT/ordini/preventivi):
        # transizione a EMESSO/CONFERMATO bloccata da componenti CASO A con
        # approvazione prezzo PENDING o prezzo non valorizzato. Conflitto di
        # stato → 409 (coerente con E_STATO_DDT_TRANSIZIONE_NON_VALIDA).
        "E_COMPONENTE_PREZZO_PENDENTE": ErrorPolicy(
            code="E_COMPONENTE_PREZZO_PENDENTE",
            http_status=409,
            ui_action="show_error_banner",
            user_message=(
                "Impossibile emettere: componenti con approvazione prezzo "
                "in corso (PENDING)."
            ),
        ),
        "E_DOC_COMPONENTI_PENDING_VALORIZZAZIONE": ErrorPolicy(
            code="E_DOC_COMPONENTI_PENDING_VALORIZZAZIONE",
            http_status=409,
            ui_action="show_error_banner",
            user_message=(
                "Impossibile emettere: componenti senza prezzo valorizzato."
            ),
        ),
        # Resi di vendita (motore resi su DDT: CRUD + conferma/annullo +
        # ri-consegna). Famiglia speculare a E_DDT_*. I codici dei guard/fn DB
        # (messaggi_errore 530-541) passano via regex in
        # resi_service._db_errors: registrati qui per fissare status/ui_action
        # lato FE (il messaggio parlante DB vince su user_message).
        "E_RESO_NOT_FOUND": ErrorPolicy(
            code="E_RESO_NOT_FOUND",
            http_status=404,
            ui_action="show_empty_state",
            user_message="Reso non trovato.",
        ),
        "E_RESO_VALIDAZIONE": ErrorPolicy(
            code="E_RESO_VALIDAZIONE",
            http_status=400,
            ui_action="highlight_form_fields",
            user_message="Parametri reso non validi.",
        ),
        "E_RESO_STATO_TRANSIZIONE": ErrorPolicy(
            code="E_RESO_STATO_TRANSIZIONE",
            http_status=409,
            ui_action="show_error_banner",
            user_message="Operazione non ammessa nello stato corrente del reso.",
        ),
        # Guard trigger transizioni reso (trgfn_resi_guard_transizione): la
        # coppia di stati non e' nella matrice config.transizioni_stati_reso.
        "E_STATO_RESO_TRANSIZIONE_NON_VALIDA": ErrorPolicy(
            code="E_STATO_RESO_TRANSIZIONE_NON_VALIDA",
            http_status=409,
            ui_action="show_error_banner",
            user_message="Transizione di stato non ammessa per il reso.",
        ),
        # Over-return: Σ qta rese (resi non annullati) sulla stessa riga DDT
        # supererebbe il consegnato (trgfn_resi_righe_guard_quantita, lock).
        "E_RESO_QTA_SUPERA_CONSEGNATO": ErrorPolicy(
            code="E_RESO_QTA_SUPERA_CONSEGNATO",
            http_status=409,
            ui_action="show_error_banner",
            user_message=(
                "La quantita' resa supera la quantita' consegnata residua "
                "della riga DDT."
            ),
        ),
        # Guard ponte ri-consegna (trgfn_resi_riconsegne_guard): aggancio
        # ammesso solo su righe con tipo_reso.riapre_residuo = true.
        "E_RESO_RICONSEGNA_TIPO_NON_VALIDO": ErrorPolicy(
            code="E_RESO_RICONSEGNA_TIPO_NON_VALIDO",
            http_status=409,
            ui_action="show_error_banner",
            user_message=(
                "Ri-spedizione ammessa solo su righe reso di tipo ri-consegna."
            ),
        ),
        # Over-ri-spedizione: Σ qta ri-spedite sulla riga reso supererebbe la
        # quantita' resa (guard ponte, lock FOR UPDATE).
        "E_RESO_RICONSEGNA_SUPERA_RESO": ErrorPolicy(
            code="E_RESO_RICONSEGNA_SUPERA_RESO",
            http_status=409,
            ui_action="show_error_banner",
            user_message=(
                "La quantita' ri-spedita supera la quantita' resa da "
                "ri-consegnare."
            ),
        ),
        # Gemello del precedente sull'ALTRA uscita della stessa copertura
        # (id 560): ri-spedizioni e rinunce condividono il residuo
        # `quantita - Sigma ric - Sigma rin`, quindi anche la rinuncia puo'
        # eccederlo. Causa tipica: due operatori sulla stessa riga reso, uno
        # ri-spedisce e l'altro dichiara definitiva la quota -> 409, conflitto
        # di stato, non errore di validazione del payload.
        "E_RESO_RINUNCIA_SUPERA_RESO": ErrorPolicy(
            code="E_RESO_RINUNCIA_SUPERA_RESO",
            http_status=409,
            ui_action="show_error_banner",
            user_message=(
                "La quantita' dichiarata definitiva supera la quantita' resa "
                "ancora da ri-consegnare."
            ),
        ),
        # fn_conferma_reso: conferma ammessa solo da DRAFT / con righe attive.
        "E_RESO_STATO_NON_CONFERMABILE": ErrorPolicy(
            code="E_RESO_STATO_NON_CONFERMABILE",
            http_status=409,
            ui_action="show_error_banner",
            user_message="Il reso non e' in bozza: non e' confermabile.",
        ),
        "E_RESO_SENZA_RIGHE": ErrorPolicy(
            code="E_RESO_SENZA_RIGHE",
            http_status=409,
            ui_action="show_error_banner",
            user_message="Il reso non ha righe: aggiungere almeno una riga "
                         "prima della conferma.",
        ),
        # fn_genera_ddt_riconsegna: reso non CONFERMATO / nessuna copertura
        # residua da ri-spedire.
        "E_RESO_NON_CONFERMATO": ErrorPolicy(
            code="E_RESO_NON_CONFERMATO",
            http_status=409,
            ui_action="show_error_banner",
            user_message=(
                "Confermare il reso prima di generare la ri-spedizione."
            ),
        ),
        "E_RESO_NESSUNA_RICONSEGNA_PENDENTE": ErrorPolicy(
            code="E_RESO_NESSUNA_RICONSEGNA_PENDENTE",
            http_status=409,
            ui_action="show_error_banner",
            user_message=(
                "Nessuna riga di ri-consegna pendente da ri-spedire per "
                "questo reso."
            ),
        ),
        # fn_annulla_reso: annullo ammesso da DRAFT/CONFERMATO; bloccato se il
        # reso e' gia' stato ri-spedito (storno ri-spedizione fuori perimetro).
        "E_RESO_STATO_NON_ANNULLABILE": ErrorPolicy(
            code="E_RESO_STATO_NON_ANNULLABILE",
            http_status=409,
            ui_action="show_error_banner",
            user_message="Il reso non e' in uno stato che ammette l'annullo.",
        ),
        "E_RESO_ANNULLO_CON_RICONSEGNE": ErrorPolicy(
            code="E_RESO_ANNULLO_CON_RICONSEGNE",
            http_status=409,
            ui_action="show_error_banner",
            user_message="Il reso e' gia' stato ri-spedito: non e' annullabile.",
        ),
        # Guard DB sorgente reso (trgfn_resi_guard_ddt_consegnato, a10 INSERT):
        # il reso richiede il DDT sorgente in CONSEGNATO. Il service ha il
        # guard gemello parlante (crea_reso); questo copre le scritture non-BE.
        "E_RESO_DDT_NON_CONSEGNATO": ErrorPolicy(
            code="E_RESO_DDT_NON_CONSEGNATO",
            http_status=409,
            ui_action="show_error_banner",
            user_message=(
                "Il DDT sorgente non e' in stato CONSEGNATO: reso non ammesso."
            ),
        ),
        # Guard emittente<->BA sul reso (trgfn_resi_guard_emittente_ba, z10).
        "E_RESO_EMITTENTE_BA_INCOERENTE": ErrorPolicy(
            code="E_RESO_EMITTENTE_BA_INCOERENTE",
            http_status=400,
            ui_action="show_error_banner",
            user_message=(
                "Emittente fiscale non coerente col cliente del reso."
            ),
        ),
        # Mutua esclusività offerta → (contratto XOR ordine): la stessa offerta si
        # materializza in UNA sola forma. Famiglia "già materializzato" = conflitto
        # di stato → 409 uniforme (coerente con E_ORD_OFFERTA_GIA_CONVERTITA sopra).
        # Entrambi i codici sono sollevati sia da DB (fn_push_offerta_a_contratto)
        # sia da BE (guard incrociati): la registrazione qui fissa lo status, che
        # altrimenti cadrebbe sul fallback 400 dei codici E_* non registrati.
        #  - CONTRATTO_GIA_GENERATO: blocca la generazione ordine se esiste già un
        #    contratto (guard BE crea_ordine_da_offerta) ED è il codice idempotenza
        #    del push duplicato (fn_push_offerta_a_contratto, UNIQUE offerta_id).
        #  - ORDINE_GIA_GENERATO: blocca il push a contratto se esiste già un ordine
        #    (guard DB fn_push_offerta_a_contratto, mutua esclusività).
        "E_OFFERTA_CONTRATTO_GIA_GENERATO": ErrorPolicy(
            code="E_OFFERTA_CONTRATTO_GIA_GENERATO",
            http_status=409,
            ui_action="show_error_banner",
            user_message="Questa offerta ha già generato un contratto.",
        ),
        "E_OFFERTA_ORDINE_GIA_GENERATO": ErrorPolicy(
            code="E_OFFERTA_ORDINE_GIA_GENERATO",
            http_status=409,
            ui_action="show_error_banner",
            user_message="Questa offerta ha già generato un ordine.",
        ),
        # Codici DB del flusso offerta (emissione/transizione/push/revisione) e del
        # push a contratto. Senza registrazione cadevano sul fallback 400, mentre
        # la convenzione del progetto per "operazione non ammessa nello stato /
        # precondizione di transizione / overlap" è 409 (gemelli già registrati:
        # E_ORD_STATO_TRANSIZIONE, E_PREV_STATO_TRANSIZIONE,
        # E_CONTRATTO_STATO_TRANSIZIONE_INVALIDA, E_VENDITE_*_OVERLAP). Registrati
        # qui per fissare lo status corretto (il messaggio parlante DB vince
        # comunque su user_message). Pulizia 2026-06-08.
        "E_OFFERTA_EMISSIONE_SENZA_VERSIONE_LISTINO": ErrorPolicy(
            code="E_OFFERTA_EMISSIONE_SENZA_VERSIONE_LISTINO",
            http_status=409,
            ui_action="show_error_banner",
            user_message=(
                "Impossibile emettere: l'offerta non ha una versione di listino."
            ),
        ),
        "E_OFFERTA_EMISSIONE_VERSIONE_LISTINO_NON_ATTIVA": ErrorPolicy(
            code="E_OFFERTA_EMISSIONE_VERSIONE_LISTINO_NON_ATTIVA",
            http_status=409,
            ui_action="show_error_banner",
            user_message=(
                "Impossibile emettere: la versione di listino non è attiva."
            ),
        ),
        "E_OFFERTA_TRANSIZIONE_NON_AMMESSA": ErrorPolicy(
            code="E_OFFERTA_TRANSIZIONE_NON_AMMESSA",
            http_status=409,
            ui_action="show_error_banner",
            user_message="Transizione di stato non ammessa per l'offerta.",
        ),
        "E_OFFERTA_REVISIONE_STATO_NON_AMMESSO": ErrorPolicy(
            code="E_OFFERTA_REVISIONE_STATO_NON_AMMESSO",
            http_status=409,
            ui_action="show_error_banner",
            user_message=(
                "Revisione non ammessa nello stato corrente dell'offerta."
            ),
        ),
        "E_OFFERTA_PUSH_STATO_NON_AMMESSO": ErrorPolicy(
            code="E_OFFERTA_PUSH_STATO_NON_AMMESSO",
            http_status=409,
            ui_action="show_error_banner",
            user_message=(
                "Push a contratto non ammesso: l'offerta deve essere ACCETTATA."
            ),
        ),
        "E_CONTRATTO_OVERLAP_ESISTENTE": ErrorPolicy(
            code="E_CONTRATTO_OVERLAP_ESISTENTE",
            http_status=409,
            ui_action="show_error_banner",
            user_message=(
                "Esiste già un contratto attivo sovrapposto per questa utility."
            ),
        ),
        # Date di successione incoerenti: dato semanticamente non processabile
        # (non un conflitto di stato) → 422.
        "E_CONTRATTO_SUCCESSIONE_DATA_INVALIDA": ErrorPolicy(
            code="E_CONTRATTO_SUCCESSIONE_DATA_INVALIDA",
            http_status=422,
            ui_action="show_error_banner",
            user_message="Date di successione del contratto non valide.",
        ),
        # Codice sollevato da vendite.fn_crea_revisione_preventivo quando esiste
        # gia' una revisione in DRAFT per lo stesso numero. Conflitto di stato:
        # l'utente deve completare/annullare la DRAFT esistente prima di crearne
        # un'altra. Senza questa policy il codice DB era mascherato in E_DATABASE.
        "PREV_REVISIONE_BOZZA_ESISTENTE": ErrorPolicy(
            code="PREV_REVISIONE_BOZZA_ESISTENTE",
            http_status=409,
            ui_action="show_error_banner",
            user_message=(
                "Esiste gia' una revisione in BOZZA per questo preventivo. "
                "Completa o annulla la BOZZA esistente prima di crearne una nuova."
            ),
        ),
        "E_PREV_STATO_NON_MODIFICABILE": ErrorPolicy(
            code="E_PREV_STATO_NON_MODIFICABILE",
            http_status=409,
            ui_action="show_error_banner",
            user_message="Preventivo non modificabile nello stato corrente.",
        ),
        "E_PREV_RIGA_NOT_FOUND": ErrorPolicy(
            code="E_PREV_RIGA_NOT_FOUND",
            http_status=404,
            ui_action="show_empty_state",
            user_message="Riga preventivo non trovata.",
        ),
        "E_PREV_COMPONENTE_NOT_FOUND": ErrorPolicy(
            code="E_PREV_COMPONENTE_NOT_FOUND",
            http_status=404,
            ui_action="show_empty_state",
            user_message="Componente preventivo non trovato.",
        ),
        # Cross-dominio (script.fn_<sorgente>_riga_componenti_init): sollevato
        # quando il pricing resolver non trova un listino mappato per uno dei
        # componenti BoM CASO A. Decisione di dominio 2026-05-12 (opzione A):
        # blocco esplicito invece di fallback prezzo=0 (vincolo dominio
        # `chk_prevrighe_comp_prezzo_nonneg = <> 0`). L'operatore deve
        # configurare il listino del componente prima di creare la riga.
        # Detail context (jsonb) contiene `componente_codice` / `componente_id`
        # / `data_riferimento` + dettaglio dal resolver per il log.
        "E_DOC_COMPONENTE_LISTINO_MANCANTE": ErrorPolicy(
            code="E_DOC_COMPONENTE_LISTINO_MANCANTE",
            http_status=422,
            ui_action="show_error_banner",
            user_message=(
                "Listino non configurato per uno dei componenti esposti in "
                "fattura. Configura il listino del componente prima di creare "
                "la riga."
            ),
        ),
        "E_PREV_NESSUNA_RIGA": ErrorPolicy(
            code="E_PREV_NESSUNA_RIGA",
            http_status=400,
            ui_action="show_error_banner",
            user_message="Nessuna riga attiva nel preventivo.",
        ),
        "E_PREV_GIA_IN_COMMESSA": ErrorPolicy(
            code="E_PREV_GIA_IN_COMMESSA",
            http_status=409,
            ui_action="show_error_banner",
            user_message="Preventivo gia' inviato a fatturazione.",
        ),
        "E_PREV_REVISIONE_ATTIVA": ErrorPolicy(
            code="E_PREV_REVISIONE_ATTIVA",
            http_status=409,
            ui_action="show_error_banner",
            user_message="Esiste gia' una revisione attiva per questo preventivo.",
        ),
        "E_PREV_PRATICA_STATO": ErrorPolicy(
            code="E_PREV_PRATICA_STATO",
            http_status=409,
            ui_action="show_error_banner",
            user_message="Stato preventivo non ammette generazione pratica.",
        ),
        # ── Preventivi: istanza obbligatoria + emittente da operatore (rev2 brief DB) ──
        # Codici sollevati dai trigger DB landed su `vendite.preventivi`:
        #   _a10_default_emittente_ins: setta emittente_fiscale_id da GUC
        #     app.current_user_id; raise se utente senza EF e payload non
        #     specifica emittente (caso admin globale).
        #   _a10_guard_utility_istanza_coerenza_ins_upd: verifica coerenza
        #     coppia (istanza_utility_id, utility_id) via fn generica
        #     script.fn_check_utility_istanza_coerenza (BA o IDP o cliente
        #     matching post Strategia C).
        #   istanze_utilities _a90_require_utility_dichiarata (DEFERRED):
        #     ogni nuova istanza deve avere almeno un satellite (BA, IDP,
        #     cliente) entro la transazione.
        #   automation_lock_columns su preventivi.emittente_fiscale_id:
        #     immutabile post-create. Codice senza prefisso E_ perche'
        #     coerente con il pattern lock_columns del DB.
        "E_PREV_EMITTENTE_NON_RISOLTO": ErrorPolicy(
            code="E_PREV_EMITTENTE_NON_RISOLTO",
            http_status=400,
            ui_action="highlight_form_fields",
            user_message=(
                "Operatore senza emittente fiscale assegnato: specificare "
                "l'emittente esplicitamente nel payload."
            ),
        ),
        "E_PREV_UTILITY_ISTANZA_INCOERENTE": ErrorPolicy(
            code="E_PREV_UTILITY_ISTANZA_INCOERENTE",
            http_status=409,
            ui_action="highlight_form_fields",
            user_message="Utility non coerente con l'istanza selezionata.",
        ),
        # ── Guard coerenza emittente↔billing account (trigger DB, 5 domini) ──
        # Sollevati da trgfn_<dominio>_guard_emittente_ba quando
        # emittente_fiscale_id diverge da fn_get_emittente_fiscale_pk(BA)
        # (skip se BA NULL). Ordini/contratti esistevano gia' (mai registrati:
        # gap sanato); DDT/preventivi/offerte aggiunti dal DB team 2026-07-13
        # (brief emittente-user-e-etichetta-soggetto).
        "E_ORDINE_EMITTENTE_BA_INCOERENTE": ErrorPolicy(
            code="E_ORDINE_EMITTENTE_BA_INCOERENTE",
            http_status=409,
            ui_action="highlight_form_fields",
            user_message=(
                "Emittente fiscale non coerente col cliente selezionato."
            ),
        ),
        "E_CONTRATTO_EMITTENTE_BA_INCOERENTE": ErrorPolicy(
            code="E_CONTRATTO_EMITTENTE_BA_INCOERENTE",
            http_status=409,
            ui_action="highlight_form_fields",
            user_message=(
                "Emittente fiscale non coerente col cliente selezionato."
            ),
        ),
        "E_DDT_EMITTENTE_BA_INCOERENTE": ErrorPolicy(
            code="E_DDT_EMITTENTE_BA_INCOERENTE",
            http_status=409,
            ui_action="highlight_form_fields",
            user_message=(
                "Emittente fiscale non coerente col cliente selezionato."
            ),
        ),
        "E_PREV_EMITTENTE_BA_INCOERENTE": ErrorPolicy(
            code="E_PREV_EMITTENTE_BA_INCOERENTE",
            http_status=409,
            ui_action="highlight_form_fields",
            user_message=(
                "Emittente fiscale non coerente col cliente selezionato."
            ),
        ),
        "E_OFFERTA_EMITTENTE_BA_INCOERENTE": ErrorPolicy(
            code="E_OFFERTA_EMITTENTE_BA_INCOERENTE",
            http_status=409,
            ui_action="highlight_form_fields",
            user_message=(
                "Emittente fiscale non coerente col cliente selezionato."
            ),
        ),
        "E_ISTANZA_UTILITY_SENZA_UTILITY": ErrorPolicy(
            code="E_ISTANZA_UTILITY_SENZA_UTILITY",
            http_status=409,
            ui_action="show_error_banner",
            user_message=(
                "Istanza utility senza utility dichiarata: serve almeno un "
                "riferimento (billing account, dati precontrattuali, cliente)."
            ),
        ),
        "EMITTENTE_NON_MODIFICABILE": ErrorPolicy(
            code="EMITTENTE_NON_MODIFICABILE",
            http_status=409,
            ui_action="show_error_banner",
            user_message=(
                "L'emittente fiscale del preventivo non puo' essere modificato "
                "dopo la creazione. Crea una revisione per cambiarlo."
            ),
        ),
        # ── Parametri di sistema ──
        "E_PARAMETER_NOT_FOUND": ErrorPolicy(
            code="E_PARAMETER_NOT_FOUND",
            http_status=404,
            ui_action="show_error_banner",
            user_message="Parametro di sistema non trovato.",
        ),
        "E_PARAMETER_VALIDATION": ErrorPolicy(
            code="E_PARAMETER_VALIDATION",
            http_status=400,
            ui_action="show_error_banner",
            user_message="Valore parametro non valido.",
        ),
        # Framework FK-surrogata config.parameter_fk_surrogate (DB 2026-05-02):
        # dispatcher su parameters/parameter_overrides che valida default_value
        # contro la chiave naturale stabile (di norma codice_interno) della
        # tabella di catalogo target. Sostituisce il guard ad-hoc deprecato
        # E_PARAMETER_DEFAULT_TIPO_SOGGETTO_INVALID (mantenuto a livello DB
        # per retro-compat ma non mappato qui: i nuovi inserimenti finiscono
        # sempre sui codici 422/423 del framework).
        "E_PARAMETER_DEFAULT_VALUE_INVALID": ErrorPolicy(
            code="E_PARAMETER_DEFAULT_VALUE_INVALID",
            http_status=400,
            ui_action="show_error_banner",
            user_message="Valore di default parametro non valido: deve esistere nella tabella di catalogo associata.",
        ),
        "E_PARAMETER_OVERRIDE_VALUE_INVALID": ErrorPolicy(
            code="E_PARAMETER_OVERRIDE_VALUE_INVALID",
            http_status=400,
            ui_action="show_error_banner",
            user_message="Override parametro non valido: il valore deve esistere nella tabella di catalogo associata.",
        ),
        # ── Conversioni UoM ──
        "E_CATALOGO_CONV_NOT_FOUND": ErrorPolicy(
            code="E_CATALOGO_CONV_NOT_FOUND",
            http_status=404,
            ui_action="show_error_banner",
            user_message="Conversione unita' di misura non trovata.",
        ),
        # ── Documenti — motore documentale parametrico ──
        # Decisioni 30/31/72/76. I codici 410-417 sono riservati agli errori
        # applicativi Fase A (template/asset/versioni); i codici 425-426
        # sono i guard append-only del trigger DB su documenti_generati_eventi.
        "E_DOCUMENTI_VALIDATION": ErrorPolicy(
            code="E_DOCUMENTI_VALIDATION",
            http_status=400,
            ui_action="highlight_form_fields",
            user_message="Parametri documento non validi.",
        ),
        "E_DOCUMENTI_NOT_FOUND": ErrorPolicy(
            code="E_DOCUMENTI_NOT_FOUND",
            http_status=404,
            ui_action="show_empty_state",
            user_message="Documento o template non trovato.",
        ),
        "E_DOCUMENTI_DENIED": ErrorPolicy(
            code="E_DOCUMENTI_DENIED",
            http_status=403,
            ui_action="show_error_banner",
            user_message="Operazione documentale non consentita.",
        ),
        "E_DOCUMENTI_RENDER_FAILED": ErrorPolicy(
            code="E_DOCUMENTI_RENDER_FAILED",
            http_status=500,
            ui_action="show_error_banner",
            user_message="Generazione PDF documento fallita.",
        ),
        "E_DOCUMENTI_STORAGE_FAILED": ErrorPolicy(
            code="E_DOCUMENTI_STORAGE_FAILED",
            http_status=500,
            ui_action="show_error_banner",
            user_message="Errore lettura/scrittura file documento.",
        ),
        # ── Documenti — guard timeline append-only (Decisione 76) ──
        # Sollevati dai trigger DB trgfn_documenti_generati_eventi_a10_*.
        "E_EVENTO_DOCUMENTO_DELETE_VIETATA": ErrorPolicy(
            code="E_EVENTO_DOCUMENTO_DELETE_VIETATA",
            http_status=409,
            ui_action="show_error_banner",
            user_message="Eliminazione eventi documento non consentita: timeline append-only.",
        ),
        "E_EVENTO_DOCUMENTO_UPDATE_VIETATA": ErrorPolicy(
            code="E_EVENTO_DOCUMENTO_UPDATE_VIETATA",
            http_status=409,
            ui_action="show_error_banner",
            user_message="Modifica eventi documento non consentita: timeline append-only.",
        ),
        # ── Documenti — guard ciclo vita versioni (Tranche F) ──
        # Sollevati dai trigger DB Fase A
        # (trgfn_template_documenti_versioni_protect_pubblicata,
        # trgfn_template_documenti_versioni_block_delete).
        "E_DOCUMENTI_VERSIONE_PUBBLICATA_IMMUTABILE": ErrorPolicy(
            code="E_DOCUMENTI_VERSIONE_PUBBLICATA_IMMUTABILE",
            http_status=409,
            ui_action="show_error_banner",
            user_message="Versione PUBBLICATA non modificabile. Crea o clona una nuova versione BOZZA.",
        ),
        "E_DOCUMENTI_VERSIONE_DELETE_BLOCKED": ErrorPolicy(
            code="E_DOCUMENTI_VERSIONE_DELETE_BLOCKED",
            http_status=409,
            ui_action="show_error_banner",
            user_message="Eliminazione versione non consentita: stato non BOZZA o gia' usata da documenti generati.",
        ),
        # EXCLUDE GIST parziale WHERE attivo+stato=PUBBLICATA (ripristino
        # enforcement 2026-06-02, migration 20260602-05). Pattern simmetrico agli
        # altri overlap (E_VENDITE_PROMO_OVERLAP / E_VENDITE_LISTINO_VERSIONE_OVERLAP):
        # codice 409 dedicato invece del generico E_DOCUMENTI_VALIDATION (400).
        "E_DOCUMENTI_VERSIONE_OVERLAP": ErrorPolicy(
            code="E_DOCUMENTI_VERSIONE_OVERLAP",
            http_status=409,
            ui_action="show_error_banner",
            user_message=(
                "Le date di validita' si sovrappongono con un'altra versione "
                "PUBBLICATA attiva del template. Chiudi quella esistente prima "
                "di pubblicare la nuova."
            ),
        ),
        # ── Documenti — guard asset (Tranche G) ──
        # Sollevati dai trigger DB Fase A
        # (trgfn_template_asset_block_delete, trgfn_template_asset_protect_file).
        "E_DOCUMENTI_ASSET_DELETE_BLOCKED": ErrorPolicy(
            code="E_DOCUMENTI_ASSET_DELETE_BLOCKED",
            http_status=409,
            ui_action="show_error_banner",
            user_message="Eliminazione asset non consentita. Disattivare l'asset impostando valido_al.",
        ),
        "E_DOCUMENTI_ASSET_FILE_IMMUTABILE": ErrorPolicy(
            code="E_DOCUMENTI_ASSET_FILE_IMMUTABILE",
            http_status=409,
            ui_action="show_error_banner",
            user_message="File asset immutabile: storage_key/sha256/file_size/mime/file_name non modificabili. Crea un nuovo asset.",
        ),
        # ── UI — personalizzazioni liste (schema ui, sviluppo-personalizzazioni-liste.md) ──
        # E_UI_LISTA_NON_TROVATA: sollevato da fn_resolve_lista_config quando il codice
        # lista non esiste o e' attivo=false (seedato in messaggi_errore.csv id 427).
        # Gli E_UI_VISTA_SQL_NON_TROVATA / E_UI_CAMPO_SORGENTE_NON_TROVATO sono guard
        # admin-only dei trigger B1/B2: l'utente finale non li vede in flussi normali.
        "E_UI_LISTA_NON_TROVATA": ErrorPolicy(
            code="E_UI_LISTA_NON_TROVATA",
            http_status=404,
            ui_action="show_empty_state",
            user_message="Lista non trovata.",
        ),
        # E_UI_DASHBOARD_NON_TROVATA: gemello del precedente per le
        # dashboard configurabili — sollevato da fn_resolve_dashboard_config
        # quando il codice dashboard non esiste o e' attivo=false.
        "E_UI_DASHBOARD_NON_TROVATA": ErrorPolicy(
            code="E_UI_DASHBOARD_NON_TROVATA",
            http_status=404,
            ui_action="show_empty_state",
            user_message="Dashboard non trovata.",
        ),
        "E_UI_VISTA_SQL_NON_TROVATA": ErrorPolicy(
            code="E_UI_VISTA_SQL_NON_TROVATA",
            http_status=400,
            ui_action="show_error_banner",
            user_message="Vista SQL della lista non trovata nel database.",
        ),
        "E_UI_CAMPO_SORGENTE_NON_TROVATO": ErrorPolicy(
            code="E_UI_CAMPO_SORGENTE_NON_TROVATO",
            http_status=400,
            ui_action="show_error_banner",
            user_message="Campo sorgente colonna non trovato nella vista SQL.",
        ),
        "E_UI_PREFERENZA_VALIDAZIONE": ErrorPolicy(
            code="E_UI_PREFERENZA_VALIDAZIONE",
            http_status=400,
            ui_action="highlight_form_fields",
            user_message="Preferenza lista non valida.",
        ),
        # DEF-2 "preset aggiornato": l'endpoint POST /preferenza/ignore-preset-update/
        # solleva quando l'utente non ha ancora una preferenza salvata sulla lista
        # (banner non dovrebbe essere visibile, ma l'errore lato BE e' parlante).
        "E_UI_PREFERENZA_NON_TROVATA": ErrorPolicy(
            code="E_UI_PREFERENZA_NON_TROVATA",
            http_status=404,
            ui_action="show_empty_state",
            user_message="Preferenza utente non trovata per questa lista.",
        ),
        # Blocco F (admin CRUD ui.*): codici dedicati per preset e permessi colonna.
        # Le validazioni di scoperto/duplicato vengono mappate via map_integrity_error
        # da nomi vincolo DB (uq_ui_lista_preset_lista_codice, chk_ui_lista_preset_ambito_refs).
        "E_UI_PRESET_VALIDAZIONE": ErrorPolicy(
            code="E_UI_PRESET_VALIDAZIONE",
            http_status=400,
            ui_action="highlight_form_fields",
            user_message="Preset lista non valido.",
        ),
        "E_UI_PRESET_NON_TROVATO": ErrorPolicy(
            code="E_UI_PRESET_NON_TROVATO",
            http_status=404,
            ui_action="show_empty_state",
            user_message="Preset lista non trovato.",
        ),
        "E_UI_PERMESSO_VALIDAZIONE": ErrorPolicy(
            code="E_UI_PERMESSO_VALIDAZIONE",
            http_status=400,
            ui_action="highlight_form_fields",
            user_message="Permesso colonna non valido.",
        ),
        "E_UI_PERMESSO_NON_TROVATO": ErrorPolicy(
            code="E_UI_PERMESSO_NON_TROVATO",
            http_status=404,
            ui_action="show_empty_state",
            user_message="Permesso colonna non trovato.",
        ),
        # Blocco F Fase 2 (DEF-5b): CRUD `ui.lista_definizione` e
        # `ui.lista_colonna`. SUPER_ADMIN-only. La cancellazione di una
        # definizione e' bloccata dalle FK RESTRICT (preferenze utente,
        # colonne, preset): il messaggio E_UI_DEFINIZIONE_IN_USO e'
        # mappato dal service via map_integrity_error.
        "E_UI_DEFINIZIONE_VALIDAZIONE": ErrorPolicy(
            code="E_UI_DEFINIZIONE_VALIDAZIONE",
            http_status=400,
            ui_action="highlight_form_fields",
            user_message="Definizione lista non valida.",
        ),
        "E_UI_DEFINIZIONE_NON_TROVATA": ErrorPolicy(
            code="E_UI_DEFINIZIONE_NON_TROVATA",
            http_status=404,
            ui_action="show_empty_state",
            user_message="Definizione lista non trovata.",
        ),
        "E_UI_DEFINIZIONE_IN_USO": ErrorPolicy(
            code="E_UI_DEFINIZIONE_IN_USO",
            http_status=409,
            ui_action="show_error_banner",
            user_message=(
                "La definizione lista e' in uso (preferenze utente, "
                "colonne o preset). Disattivala con attivo=false invece "
                "di eliminarla."
            ),
        ),
        # CRUD ui.lista_colonna (DEF-5b T2). E_UI_COLONNA_IN_USO viene
        # sollevato sia da FK RESTRICT (lista_preset_colonna,
        # lista_colonna_permesso) sia dal soft-block applicativo che
        # conta le preferenze utente che referenziano la colonna nel
        # JSONB `configurazione->colonne`.
        "E_UI_COLONNA_VALIDAZIONE": ErrorPolicy(
            code="E_UI_COLONNA_VALIDAZIONE",
            http_status=400,
            ui_action="highlight_form_fields",
            user_message="Colonna lista non valida.",
        ),
        "E_UI_COLONNA_NON_TROVATA": ErrorPolicy(
            code="E_UI_COLONNA_NON_TROVATA",
            http_status=404,
            ui_action="show_empty_state",
            user_message="Colonna lista non trovata.",
        ),
        "E_UI_COLONNA_IN_USO": ErrorPolicy(
            code="E_UI_COLONNA_IN_USO",
            http_status=409,
            ui_action="show_error_banner",
            user_message=(
                "La colonna e' in uso (preferenze utente, preset o "
                "permessi). Disattivala con attivo=false invece di "
                "eliminarla."
            ),
        ),
        # DEF-1: export CSV/Excel delle liste configurabili. Hard cap
        # sincrono 10.000 righe (decisione 3) -> 422 con messaggio
        # parlante "raffinare i filtri". Format invalido -> 400.
        "E_UI_EXPORT_LIMIT_EXCEEDED": ErrorPolicy(
            code="E_UI_EXPORT_LIMIT_EXCEEDED",
            http_status=422,
            ui_action="show_error_banner",
            user_message=(
                "L'export supera il limite di righe consentito. "
                "Raffina i filtri e riprova."
            ),
        ),
        "E_UI_EXPORT_FORMAT_INVALID": ErrorPolicy(
            code="E_UI_EXPORT_FORMAT_INVALID",
            http_status=400,
            ui_action="show_error_banner",
            user_message="Formato export non supportato (ammessi: csv, xlsx).",
        ),
        "E_UI_EXPORT_FAILED": ErrorPolicy(
            code="E_UI_EXPORT_FAILED",
            http_status=500,
            ui_action="show_error_banner",
            user_message="Generazione export non riuscita.",
        ),
        # Fallback per DatabaseError non riconosciute dai marker noti
        # nello schema `ui` (allineato a E_VENDITE_PRICING_FAILED).
        "E_UI_GENERIC_FAILED": ErrorPolicy(
            code="E_UI_GENERIC_FAILED",
            http_status=400,
            ui_action="show_error_banner",
            user_message="Errore configurazione lista.",
        ),
    }

    # Scopo: Risolve la policy per un codice errore. Per codici applicativi
    # (E_*) non registrati usa fallback 400 con messaggio dal DB, non 500 generico.
    @classmethod
    def resolve(cls, code: str) -> ErrorPolicy:
        policy = cls._POLICIES.get(code)
        if policy:
            return policy
        # Codici applicativi E_* non registrati: errore business (400), non tecnico (500)
        if code.startswith("E_") and code != "E_GENERICO":
            return ErrorPolicy(
                code=code,
                http_status=400,
                ui_action="show_error_banner",
                user_message="Errore di validazione.",
            )
        return cls._POLICIES["E_GENERICO"]

    # Scopo: Verifica se un codice errore ha una policy registrata.
    @classmethod
    def has(cls, code: str) -> bool:
        return code in cls._POLICIES
