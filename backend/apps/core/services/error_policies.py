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
        "E_CONTRATTO_MODALITA_C_SENZA_RIGHE": ErrorPolicy(
            code="E_CONTRATTO_MODALITA_C_SENZA_RIGHE",
            http_status=400,
            ui_action="show_error_banner",
            user_message="Contratto in modalita' C senza righe: aggiungere almeno una riga prima di attivare.",
        ),
        "E_CONTRATTO_MODALITA_C_RIGHE_INCOMPLETE": ErrorPolicy(
            code="E_CONTRATTO_MODALITA_C_RIGHE_INCOMPLETE",
            http_status=400,
            ui_action="show_error_banner",
            user_message="Contratto in modalita' C: ogni riga deve avere un prezzo unitario prima di attivare.",
        ),
        "E_CONTRATTO_MODALITA_C_RIGA_SENZA_PREZZO": ErrorPolicy(
            code="E_CONTRATTO_MODALITA_C_RIGA_SENZA_PREZZO",
            http_status=400,
            ui_action="highlight_form_fields",
            user_message="Su contratto attivo in modalita' C la riga deve avere prezzo unitario.",
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
        # ── Catalogo BoM — duplica versione (Fase 3 refactor catalogo) ──
        # Codici sollevati da catalogo.fn_duplica_componente_versione() via
        # script.fn_log_and_raise_error (SQLSTATE P0001). Contratto:
        # docs/it/dbzero/catalogo/manual/fn_duplica_componente_versione.md.
        "E_BOM_VERSIONE_OVERLAP": ErrorPolicy(
            code="E_BOM_VERSIONE_OVERLAP",
            http_status=409,
            ui_action="show_error_banner",
            user_message=(
                "Esiste gia' una versione futura per lo stesso prodotto/componente: "
                "scegliere una data di chiusura precedente o rivedere il piano versioni."
            ),
        ),
        "E_BOM_SORGENTE_GIA_CHIUSA": ErrorPolicy(
            code="E_BOM_SORGENTE_GIA_CHIUSA",
            http_status=409,
            ui_action="show_error_banner",
            user_message=(
                "La riga sorgente e' gia' chiusa: selezionare la versione corrente "
                "(senza data di fine) come sorgente per la duplicazione."
            ),
        ),
        "E_BOM_RIGA_NOT_FOUND": ErrorPolicy(
            code="E_BOM_RIGA_NOT_FOUND",
            http_status=404,
            ui_action="show_empty_state",
            user_message="Riga BoM non trovata: aggiornare la lista e riprovare.",
        ),
        "E_BOM_PRODOTTO_MISMATCH": ErrorPolicy(
            code="E_BOM_PRODOTTO_MISMATCH",
            http_status=400,
            ui_action="show_error_banner",
            user_message=(
                "La riga selezionata appartiene a un altro articolo: "
                "aggiornare la lista componenti corrente e riprovare."
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
        "E_PRATICHE_TRANSIZIONE_NON_AMMESSA": ErrorPolicy(
            code="E_PRATICHE_TRANSIZIONE_NON_AMMESSA",
            http_status=409,
            ui_action="show_error_banner",
            user_message="Transizione di stato pratica non ammessa.",
        ),
        "E_FLUSSI_TRANSIZIONE_NON_AMMESSA": ErrorPolicy(
            code="E_FLUSSI_TRANSIZIONE_NON_AMMESSA",
            http_status=409,
            ui_action="show_error_banner",
            user_message="Transizione di stato flusso non ammessa.",
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
        # ── Clienti / Fornitori — normalize+guard payload pagamento/fiscali ──
        # Fase 2 refactor anagrafiche (landed 2026-04-27). Trigger DB:
        # anagrafiche.trgfn_clienti_normalize_giorni_scadenza (raise se
        # tipo_gg_scadenza_ft IN ('G','F') AND nr_giorni_scadenza IS NULL/<=0).
        # Pattern simmetrico al gemello fornitori (raise se ritenuta_acconto=true
        # AND ritenuta_aliquota IS NULL/<=0). Codici seedati in
        # config.messaggi_errore (id 397, 398).
        "E_CLIENTI_GIORNI_SCADENZA_OBBLIGATORI": ErrorPolicy(
            code="E_CLIENTI_GIORNI_SCADENZA_OBBLIGATORI",
            http_status=400,
            ui_action="highlight_form_fields",
            user_message=(
                "Numero giorni scadenza obbligatorio quando il tipo calcolo "
                "scadenza e' G (somma giorni) o F (fine mese + somma)."
            ),
        ),
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
        "E_PREZZO_LISTINO_NON_TROVATO": ErrorPolicy(
            code="E_PREZZO_LISTINO_NON_TROVATO",
            http_status=404,
            ui_action="show_empty_state",
            user_message="Prezzo listino non trovato.",
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
        "E_PREV_OVERRIDE_NON_AUTORIZZATO": ErrorPolicy(
            code="E_PREV_OVERRIDE_NON_AUTORIZZATO",
            http_status=403,
            ui_action="show_error_banner",
            user_message=(
                "Modifica manuale del prezzo non autorizzata. Usa il prezzo "
                "suggerito dal listino o richiedi l'autorizzazione al responsabile."
            ),
        ),
        "E_PREV_SCONTO_ECCESSIVO": ErrorPolicy(
            code="E_PREV_SCONTO_ECCESSIVO",
            http_status=403,
            ui_action="show_error_banner",
            user_message=(
                "Sconto oltre il limite consentito per il tuo ruolo. "
                "Richiedi approvazione o rientra nel limite ammesso."
            ),
        ),
        "E_PREV_MAGGIORAZIONE_ECCESSIVA": ErrorPolicy(
            code="E_PREV_MAGGIORAZIONE_ECCESSIVA",
            http_status=403,
            ui_action="show_error_banner",
            user_message=(
                "Maggiorazione oltre il limite consentito per il tuo ruolo. "
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
