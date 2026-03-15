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
        # ── Amministrazione software ──
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
    }

    # Scopo: Gestisce `resolve` nel flusso applicativo del modulo.
    @classmethod
    def resolve(cls, code: str) -> ErrorPolicy:
        return cls._POLICIES.get(code, cls._POLICIES["E_GENERICO"])
