# ------------------------------------------------------------
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2025 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Tipi condivisi core per tracciamento processi, task registry, audit e job.
# ------------------------------------------------------------

from typing import Any, TypedDict


# --- Audit Log (dbops.audit_log) ---

class AuditLogRow(TypedDict):
    id: int
    function_name: str
    executed_by: str
    executed_at: str
    status: str
    message: str | None
    duration_ms: int | None
    tx_id: str | None
    exec_mode: str | None
    rule_type: str | None
    dry_run: bool | None
    rows_affected: int | None
    params: dict[str, Any] | None
    result: dict[str, Any] | None


# --- Error Log (dbops.error_log) — la consultazione dei tecnici (pezzo E) ---

class ErrorLogRow(TypedDict):
    id: int
    occurred_at: str
    area: str
    function_name: str
    # Dal catalogo (`config.messaggi_errore` + `config.codici_errore`), per JOIN:
    # la frase e la soluzione A CATALOGO, non ricostruite.
    codice: str
    classe: str | None
    messaggio: str
    causa: str | None
    soluzione: str | None
    # NOT NULL a DB (`trgfn_tx_id_managed` lo garantisce): e' il ponte verso il
    # giornale di dominio della stessa transazione.
    tx_id: str
    # ⚠️ Gli appunti del tecnico, com'erano: niente pulizia, niente riscrittura
    #    (vincolo del Passo A dell'osservabilita'). NOT NULL DEFAULT '{}' a DB.
    context: dict[str, Any]


# --- Task Registry (dbops.domini_task / pipeline_task_registry / pipeline_task_registry_impl) ---

class DominioTaskRow(TypedDict):
    id: int
    codice: str
    descrizione: str | None
    attivo: bool


class TaskRegistryRow(TypedDict):
    id: int
    dominio_id: int
    dominio_codice: str
    task_code: str
    descrizione: str | None
    attivo: bool


class TaskRegistryImplRow(TypedDict):
    id: int
    task_registry_id: int
    task_code: str
    implementation_key: str
    handler_code: str
    is_default: bool
    attivo: bool


# --- Email Account (config.email_account) ---

class EmailAccountRow(TypedDict):
    id: int
    codice: str
    descrizione: str
    unita_organizzativa_id: int | None
    smtp_host: str
    smtp_port: int
    smtp_use_tls: bool
    smtp_use_ssl: bool
    smtp_username: str
    smtp_password_encrypted: str
    email_from: str
    email_reply_to: str | None
    attivo: bool


class EmailAccountResolvedRow(TypedDict):
    """Risultato di fn_resolve_email_account — senza meta/audit."""
    id: int
    codice: str
    smtp_host: str
    smtp_port: int
    smtp_use_tls: bool
    smtp_use_ssl: bool
    smtp_username: str
    smtp_password_encrypted: str
    email_from: str
    email_reply_to: str | None


# --- Email Template (config.email_template) ---

class EmailTemplateRow(TypedDict):
    id: int
    codice: str
    unita_organizzativa_id: int | None
    tipo_prestazione_id: int | None
    lingua: str
    oggetto: str
    corpo_html: str
    corpo_testo: str | None
    variabili_disponibili: list[str]
    attivo: bool


class EmailTemplateResolvedRow(TypedDict):
    """Risultato di fn_resolve_email_template — solo campi per rendering."""
    id: int
    codice: str
    oggetto: str
    corpo_html: str
    corpo_testo: str | None
    variabili_disponibili: list[str]
    lingua: str


# --- Email Log (config.email_log) ---

class EmailLogRow(TypedDict):
    id: int
    email_account_id: int | None
    email_template_id: int | None
    destinatario: str
    destinatari_cc: list[str] | None
    oggetto: str
    corpo_inviato_html: str | None
    corpo_inviato_testo: str | None
    stato: str
    errore: str | None
    tentativi: int
    max_tentativi: int
    prossimo_tentativo: str | None
    inviato_at: str | None
    ambito: str
    unita_organizzativa_id: int | None
    pratica_id: int | None
    auth_user_id: int | None
    contesto_json: dict[str, Any]
    data_insert: str


# --- Token Monouso (config.token_monouso) ---

class TokenMonousoRow(TypedDict):
    id: int
    token_hash: str
    tipo: str
    auth_user_id: int
    scadenza: str
    utilizzato: bool
    utilizzato_at: str | None
    ip_utilizzo: str | None
    meta: dict[str, Any]
    data_insert: str


# --- Email Outbox (config.email_outbox) ---

class EmailOutboxRow(TypedDict):
    id: int
    email_account_id: int | None
    email_template_id: int | None
    ambito: str
    unita_organizzativa_id: int | None
    pratica_id: int | None
    destinatario: str
    destinatari_cc: list[str] | None
    oggetto: str
    corpo_html: str
    corpo_testo: str | None
    stato: str
    contesto_json: dict[str, Any]
    auth_user_id: int | None
    creato_da_user_id: int | None
    inviato_at: str | None
    email_log_id: int | None
    data_insert: str


# --- Email Allegato (config.email_allegato) ---

class EmailAllegatoRow(TypedDict):
    id: int
    email_outbox_id: int | None
    email_log_id: int | None
    nome_file: str
    mime_type: str
    dimensione_bytes: int
    file_path: str
    origine: str
    data_insert: str


# --- Job Run Log (maintenance.job_run_log) ---

class JobRunLogRow(TypedDict):
    id: int
    jobname: str
    stepname: str | None
    started_at: str
    ended_at: str | None
    ok: bool | None
    rows_affected: int | None
    message: str | None
    error_code: str | None
    error_detail: str | None
    agent_host: str | None
    run_uuid: str
    # Corsa saltata per lock occupato: chiusa e senza esito (`ok` None).
    saltata: bool
