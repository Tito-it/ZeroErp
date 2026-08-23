# ------------------------------------------------------------
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2025 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Accesso DB per pipeline vendite.
# ------------------------------------------------------------


from dataclasses import dataclass
from datetime import date
from decimal import Decimal
import json
import logging
from typing import Any

from django.db import connection, transaction

from apps.core.db._helpers import (
    LIST_MAX_LIMIT,
    coerce_jsonb_dict,
    fetch_paged_with_total,
    iso_or_none,
    jsonb_out,
    rows_to_list,
)
from apps.core.db.emittente_scope_helpers import add_emittente_scope_condition
from apps.core.services.error_manager import ErrorManager
from apps.vendite.db._event_log_repo_mixin import EventLogRepositoryMixin
from apps.vendite.db.commesse_repository import (
    TIPO_MOVIMENTO_NORMALE,
    TIPO_MOVIMENTO_RETTIFICA,
)
from apps.core.services.value_normalizer import as_bool, empty_to_none
from apps.vendite.types import (
    AnnullaLottoDaDraftResult,
    EliminaFatturaDaLottoResult,
    LottoPipelineMeta,
    LottoSegnalazioneRow,
    LottoSegnalazioniSummary,
    LottoTaskRunRow,
    RiportaLottoADraftResult,
)

logger = logging.getLogger(__name__)

# Firma delle segnalazioni scritte dal BACKEND sulle fatture (marcatura di
# fallimento di un task per-fattura). Serve a distinguerle da quelle dei task
# DB al momento del ritiro: «chi alza la bandiera la abbassa» vale per padrone,
# non per tabella.
_ORIGINE_SEGNALAZIONE_BE = "BE_PIPELINE"

# Il tetto delle righe ESPORTABILI dei due elenchi del drawer lotto. Il tetto di
# PAGINA (500) resta quello di sempre: sono due limiti per due usi diversi, e
# confonderli significa o una pagina enorme o un file troncato in silenzio.
_DRAWER_EXPORT_MAX_ROWS = 10_000

# Repository SQL: incapsula accesso DB per orchestrazione pipeline vendite.

# Chiave nel `meta` jsonb del lotto che porta la corsia (filtro fatturazione_immediata)
# decisa dal driver/management command. Contratto condiviso col command: usare SEMPRE
# questa costante per scrivere/leggere il valore, evitando stringa magica duplicata.
LOTTO_META_KEY_FATTURAZIONE_IMMEDIATA = "fatturazione_immediata"


@dataclass(frozen=True)
class LottoContext:
    competenza_mese: date
    tipo_doc_fiscale_id: int | None
    utility_id: int | None
    billing_account_id: int | None
    lock_batch_id: str | None
    emittente_soggetto_ruolo_id: int | None = None
    # Corsia driver: filtro fatturazione_immediata propagato dal management command
    # via meta del lotto (True=immediata, False=differita, None=tutte/storico).
    fatturazione_immediata: bool | None = None
    # Perimetro dell'EMISSIONE MIRATA (brief emissione mirata, D-3): chiavi dei
    # gruppi fatturabili che questo lotto ha il permesso di lavorare, lette da
    # `vendite.fatturazione_lotti_gruppi`. `None` = NESSUNA restrizione = il
    # comportamento storico del giro schedulato.
    #
    # ⚠️ Perche' sta QUI e non nei parametri di chiamata: gli step ricevono solo
    # `lotto_id` e ricostruiscono tutto da questo contesto. Un criterio passato
    # "allo step" non esiste — e un rerun/avanza step su lotto esistente
    # allargherebbe in silenzio il perimetro di un lotto mirato.
    gruppi: tuple[str, ...] | None = None


@dataclass(frozen=True)
class PipelineStep:
    stato_doc_fiscale_id: int
    descrizione: str | None
    ordine: int | None


@dataclass(frozen=True)
class GroupAttivitaInput:
    attivita_id: int
    articolo_id: str  # uuid (catalogo.articoli.id)
    dest_billing_account_id: int | None
    uom_id: int | None
    prezzo_unitario: Decimal | None
    iva_id: int | None
    competenza_dal: date | None
    competenza_al: date | None
    data_attivita: date | None
    calcolo_qta_padre: str
    arrotondamento_importi_dec: int
    arrotondamento_quantita_dec: int
    metodo_arrotondamento_importi: str
    metodo_arrotondamento_quantita: str
    # ── Rettifica (nota di credito) ──────────────────────────────────────────
    # `tipo_movimento` e' il CARTELLINO: dice cos'e' la riga (NORMALE, ONERE,
    # RETTIFICA). Il numero lo porta la quantita', che su una rettifica e' gia'
    # NEGATIVA a monte (D-NC-2): qui non si cambia nessun segno.
    tipo_movimento: str = TIPO_MOVIMENTO_NORMALE
    fattura_riga_rettificata_id: int | None = None
    # I tre valori COPIATI dalla riga di fattura rettificata. Non sono i valori
    # dell'attivita': su una rettifica il prezzo e' quello con cui la merce e'
    # stata fatturata, letto dal DOCUMENTO e mai ricalcolato (N-1). Oggi
    # coincidono con quelli dell'attivita' per costruzione — ed e' precisamente
    # il motivo per cui prendere i secondi non darebbe nessun sintomo finche'
    # non divergono.
    rett_prezzo_unitario: Decimal | None = None
    rett_sconto_percentuale: Decimal | None = None
    rett_iva_id: int | None = None


@dataclass(frozen=True)
class AttivitaDaFatturare:
    id: int
    articolo_id: str  # uuid (catalogo.articoli.id)
    quantita: Decimal | None
    prezzo_unitario: Decimal | None
    uom_id: int | None
    sorgente_tipo_id: int | None
    sorgente_uid: str | None
    sorgente_riga: int | None
    articolo_descrizione: str | None
    # `meta` dell'attivita': porta lo snapshot kit gia' risolto dal push
    # (`segment_key`, `componente_di`, `esposto_in_fattura`). Nessuna
    # risoluzione di distinta base a valle: lo stesso componente puo'
    # appartenere a piu' kit, solo il documento sorgente sa quale e' stato
    # venduto. Vedi brief-fix-importi-riga-fattura-zero §4.7-bis (D5).
    meta: dict[str, Any] | None = None
    # Il cartellino della riga, letto qui per l'aggregazione: una RETTIFICA non
    # si fonde con una riga normale nemmeno se prezzo, articolo e IVA
    # coincidessero — sono due fatti diversi dentro lo stesso documento.
    tipo_movimento: str = TIPO_MOVIMENTO_NORMALE


@dataclass(frozen=True)
class SdiPayloadRow:
    fattura_sdi_id: int
    fattura_id: int
    tentativo_num: int
    stato_sdi_id: int
    codice_documento: str | None
    numero_fattura: int | None
    data_fattura: date | None
    billing_account_id: int
    emittente_soggetto_ruolo_id: int
    valuta_id: int | None
    totale_a_pagare: Decimal | None


@dataclass(frozen=True)
class TaskRunResult:
    task_run_id: int
    tentativo: int


@dataclass(frozen=True)
class TaskExecutionMode:
    execution_mode: str  # RUN | SKIP | RESUME | RESET_REQUIRED
    annullabile: bool
    resume_mode: str
    last_task_stato: str | None
    last_tentativo: int | None
    policy_meta: dict[str, Any]
    run_meta: dict[str, Any]


# Whitelist ORDER BY della coda stampa: chiave = `campo_sorgente` inviato dal
# frontend, valore = espressione SQL qualificata. `{dir}` solo dove serve NULLS
# LAST (la direzione va PRIMA della clausola).
#
# ⚠️ A livello MODULO, non attributo di classe: il gate del service ne DERIVA
# l'elenco, e una whitelist raggiungibile solo attraverso la classe diventa
# vuota appena un test mocka il repository — il gate finirebbe per dipendere dal
# mock invece che dal codice.
#
# Aggiunte il 2026-08-02: `stato` e `fattura_numero` sono NUCLEO sempre
# ordinabile (a video il numero e' composto da `fatturaLabel`, ma cio' che si
# ordina e' il numero della fattura); `id`, `emittente_codice` e `operatore`
# completano le colonne gia' mostrate dalla pagina.
CODA_STAMPA_SORT_SQL: dict[str, str] = {
    "id": "c.id",
    "fattura_id": "c.sorgente_id",
    # NULLS LAST esplicito: il numero e` NULL finche` la fattura e` in bozza —
    # in DESC finirebbe in testa.
    "fattura_numero": "f.numero {dir} NULLS LAST",
    "emittente_codice": "ef.codice {dir} NULLS LAST",
    "operatore": "c.user_insert",
    "stato": "c.stato",
    # NULLS LAST esplicito: lotto_id e` NULL per le stampe fuori lotto (es.
    # ristampe singole) — in DESC finirebbero in testa.
    "lotto_id": "c.lotto_id {dir} NULLS LAST",
    "data_update": "c.data_update",
}


# Proiezione e mapping di `GroupAttivitaInput`, in un posto solo.
#
# 🔴 PERCHE' ESISTE. Le due letture — singola (`get_group_attivita_input`) e
# batch (`batch_get_group_attivita_inputs`) — proiettavano le STESSE 19 colonne
# in due SELECT copiate, con due mapping riga->dataclass scritti a mano. E le due
# copie erano gia' DIVERSE: quella singola faceva `articolo_id=int(row[1])` su
# una colonna che e' un UUID, cioe' sollevava `ValueError` a ogni chiamata.
# Nessun test lo vedeva (i test mockano il repository) e nessun percorso vivo la
# invocava, quindi il difetto e' rimasto la' a aspettare il primo chiamante.
# Con una proiezione e un mapper soli il difetto non e' "corretto in due punti":
# non ha piu' due punti in cui esistere.
_GROUP_ATTIVITA_SELECT = """
                SELECT
                    a.id,
                    a.articolo_id,
                    a.billing_account_id AS dest_billing_account_id,
                    COALESCE(a.uom_id, art.uom_id) AS uom_id,
                    a.prezzo_unitario,
                    art.iva_id,
                    a.competenza_dal,
                    a.competenza_al,
                    a.data_attivita,
                    COALESCE(r.calcolo_qta_padre, 'fissa') AS calcolo_qta_padre,
                    COALESCE(r.arrotondamento_importi_dec, 2) AS arrotondamento_importi_dec,
                    COALESCE(r.arrotondamento_quantita_dec, 3) AS arrotondamento_quantita_dec,
                    COALESCE(r.metodo_arrotondamento_importi, 'HALF_UP')
                        AS metodo_arrotondamento_importi,
                    COALESCE(r.metodo_arrotondamento_quantita, 'HALF_UP')
                        AS metodo_arrotondamento_quantita,
                    a.tipo_movimento,
                    a.fattura_riga_rettificata_id,
                    fr.prezzo_unitario     AS rett_prezzo_unitario,
                    fr.sconto_percentuale  AS rett_sconto_percentuale,
                    fr.iva_id              AS rett_iva_id
                FROM vendite.attivita_fatturabili a
                JOIN catalogo.articoli art
                  ON art.id = a.articolo_id
                LEFT JOIN vendite.articolo_regole_fatturazione r
                  ON r.articolo_id = a.articolo_id
                -- La riga di fattura RETTIFICATA: e' da qui che una nota di
                -- credito prende prezzo, sconto e IVA (N-1, mai ricalcolati).
                -- LEFT perche' il puntatore e' NULL su tutto cio' che non e'
                -- una rettifica, cioe' sul caso normale.
                LEFT JOIN vendite.fatture_righe fr
                  ON fr.id = a.fattura_riga_rettificata_id
"""


# Scopo: Costruisce un `GroupAttivitaInput` da una riga di `_GROUP_ATTIVITA_SELECT`.
#        Unico mapping: le due letture non possono divergere.
def _group_attivita_input_da_row(row: tuple[Any, ...]) -> GroupAttivitaInput:
    return GroupAttivitaInput(
        attivita_id=int(row[0]),
        # ⚠️ `str`, non `int`: e' un UUID (catalogo.articoli.id).
        articolo_id=None if row[1] is None else str(row[1]),
        dest_billing_account_id=None if row[2] is None else int(row[2]),
        uom_id=None if row[3] is None else int(row[3]),
        prezzo_unitario=row[4],
        iva_id=None if row[5] is None else int(row[5]),
        competenza_dal=row[6],
        competenza_al=row[7],
        data_attivita=row[8],
        calcolo_qta_padre=row[9],
        arrotondamento_importi_dec=int(row[10]),
        arrotondamento_quantita_dec=int(row[11]),
        metodo_arrotondamento_importi=row[12],
        metodo_arrotondamento_quantita=row[13],
        tipo_movimento=row[14] or TIPO_MOVIMENTO_NORMALE,
        fattura_riga_rettificata_id=None if row[15] is None else int(row[15]),
        rett_prezzo_unitario=row[16],
        rett_sconto_percentuale=row[17],
        rett_iva_id=None if row[18] is None else int(row[18]),
    )


class VenditePipelineRepository(EventLogRepositoryMixin):
    """Wrapper SQL a basso livello per l'orchestrazione pipeline vendite."""

    DOMINIO_CODE = "FATTURAZIONE"

    # Mappa dichiarativa task -> funzione SQL che il task esegue. NON e' una
    # allowlist di sicurezza e non guida il dispatch: ogni handler in
    # `pipeline_step_executor` chiama un metodo repository esplicito. Serve a
    # due cose: documentare dove vive l'implementazione di ogni task, e
    # intercettare una config di pipeline che dichiari un `fn` diverso da quello
    # atteso. Quel controllo, oggi, non scatta mai — nessuna riga di
    # `vendite.fatturazione_pipeline` valorizza la chiave `fn` (verificato:
    # 0 su 8), quindi `_validate_task_function_name` riceve sempre `fn_name=None`.
    #
    # `None` = il task NON ha una funzione SQL: l'implementazione e' Python.
    # Un `fn` dichiarato in config per un task a `None` e' respinto con
    # E_TASK_NOT_ALLOWED (config stale): vedi `_validate_task_function_name`.
    ALLOWED_TASK_FUNCTIONS = {
        "select_attivita": "vendite.fn_select_attivita_fatturabili",
        # `vendite.fn_generate_fatture_righe` e' stata RIMOSSA il 2026-07-28
        # (changeset 20260728-21): l'implementazione in esercizio e'
        # `FattureRigheService.generate_fatture_righe`. Lasciare qui il nome di
        # una funzione inesistente e' precisamente cio' che ha fatto scrivere
        # due requisiti di aggregazione su codice non eseguito.
        "generate_fatture_righe": None,
        # R-3: i due giri passano dalle MADRI per lotto, non piu' dalle
        # funzioni per-scope (che restano, chiamate dalle madri).
        "genera_fondi_source_lotto": "vendite.fn_genera_fondi_fattura_lotto",
        "applica_fondi_lotto": "vendite.fn_applica_fondi_lotto",
        "ricalcola_iva_lotto": "vendite.fn_ricalcola_riepiloghi_iva_lotto",
        "prepare_sdi_payload_lotto": "vendite.fn_prepare_sdi_payload",
        "numera_fatture": "vendite.fn_numera_fattura_opz_emessa",
        "close_lotto": None,
        "reset_lotto_draft": "vendite.fn_annulla_lotto_da_draft",
        "pull_attivita_da_commessa": "vendite.fn_emit_attivita_fatturabili_da_commessa",
        # Il `task_code` resta `snapshot_indirizzi_lotto` (seed, handler, policy
        # e registry non si muovono); la funzione SQL e' stata rinominata dal
        # team DB in `fn_snapshot_fattura_lotto` quando ha iniziato a scrivere
        # anche l'intestazione — il nome vecchio ne diceva meta' (brief
        # snapshot-intestazione §10.8).
        "snapshot_indirizzi_lotto": "vendite.fn_snapshot_fattura_lotto",
        # Fase 4 del piano DB satelliti (changeSet `20260801-09`). Il task vive
        # nello step EMESSA e va DOPO `ricalcola_iva_lotto`: la base di
        # ripartizione e' `totale_a_pagare`, che prima del ricalcolo non esiste
        # ancora — l'ordine e' presidiato da `_TASK_ORDER_DEPENDENCIES` in
        # `pipeline_step_executor`, non lasciato alla sola configurazione.
        "genera_scadenze_lotto": "vendite.fn_genera_scadenze_lotto",
        # Legame documentale delle note di credito (N10 + BE-8). Vive nello step
        # DEFINITIVA e va DOPO `numera_fatture`: prima della numerazione il reset
        # di lotto puo' ancora passare, e `fn_cleanup_fatture_by_ids` non
        # cancella `vendite.fatture_rettifiche` — la FK non e' ON DELETE CASCADE,
        # quindi il reset sbatterebbe su una violazione grezza dentro una
        # funzione che i suoi chiamanti danno per infallibile. L'ordine e'
        # presidiato da `_TASK_ORDER_DEPENDENCIES`, non lasciato al solo seed.
        "popola_fatture_rettifiche": "vendite.fn_popola_fatture_rettifiche",
    }

    # Scopo: Gestisce `_to_jsonb_param` nel flusso applicativo del modulo.
    @staticmethod
    def _to_jsonb_param(value: LottoPipelineMeta | None) -> str | None:
        if value is None:
            return None
        # Serializza esplicitamente per evitare errori adapter psycopg su dict/list.
        return json.dumps(value)

    # Scopo: Risolve o crea il lotto di fatturazione delegando al DB la logica di consistenza dominio.
    def get_or_create_lotto(
        self,
        lotto_id: int | None,
        competenza_mese: date | None,
        tipo_doc_fiscale_id: int | None,
        utility_id: int | None,
        billing_account_id: int | None,
        emittente_soggetto_ruolo_id: int | None,
        lock_batch_id: str | None,
        meta: LottoPipelineMeta | None,
        tipo_lotto: str | None,
    ) -> int:
        # Delega al DB la risoluzione/creazione lotto per mantenere coerenza funzionale.
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT vendite.fn_get_or_create_lotto(
                    %s, %s, %s, %s, %s, %s::uuid, %s::jsonb, %s::text, %s
                )
                """,
                [
                    lotto_id,
                    competenza_mese,
                    tipo_doc_fiscale_id,
                    utility_id,
                    billing_account_id,
                    lock_batch_id,
                    self._to_jsonb_param(meta),
                    tipo_lotto,
                    emittente_soggetto_ruolo_id,
                ],
            )
            row = cursor.fetchone()
            assert row is not None
        return int(row[0])

    # Scopo: Recupera `lotto_tipo` dal contesto applicativo o dal database.
    def get_lotto_tipo(self, lotto_id: int) -> str | None:
        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT tipo_lotto FROM vendite.fatturazione_lotti WHERE id = %s",
                [lotto_id],
            )
            row = cursor.fetchone()
        if not row:
            return None
        return row[0]

    # Scopo: Recupera `lotto_job_stato` dal contesto applicativo o dal database.
    def get_lotto_job_stato(self, lotto_id: int) -> str | None:
        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT stato_lotto FROM vendite.fatturazione_lotti WHERE id = %s",
                [lotto_id],
            )
            row = cursor.fetchone()
        if not row:
            return None
        return row[0]

    # Scopo: Determina in modo univoco se il lotto e` in errore basandosi su stato_lotto persistito.
    def is_lotto_in_errore(self, lotto_id: int) -> bool:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT (stato_lotto = 'ERRORE')
                FROM vendite.fatturazione_lotti
                WHERE id = %s
                """,
                [lotto_id],
            )
            row = cursor.fetchone()
        if not row:
            return False
        return bool(row[0])

    # Scopo: Restituisce il riepilogo segnalazioni attive del lotto per severita` e sorgente (fatture/lotto).
    # Include fatture_stato_esecuzione_errore_count dalla funzione DB (6° colonna).
    def get_lotto_segnalazioni_summary(self, lotto_id: int) -> LottoSegnalazioniSummary:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT
                    fatture_critical_count,
                    fatture_warning_count,
                    lotto_critical_count,
                    lotto_warning_count,
                    lotto_info_count,
                    fatture_stato_esecuzione_errore_count
                FROM vendite.fn_get_lotto_segnalazioni_summary(%s)
                """,
                [lotto_id],
            )
            row = cursor.fetchone()
        if not row:
            return {
                "fatture_critical_count": 0,
                "fatture_warning_count": 0,
                "lotto_critical_count": 0,
                "lotto_warning_count": 0,
                "lotto_info_count": 0,
                "fatture_stato_esecuzione_errore_count": 0,
            }
        return {
            "fatture_critical_count": int(row[0]),
            "fatture_warning_count": int(row[1]),
            "lotto_critical_count": int(row[2]),
            "lotto_warning_count": int(row[3]),
            "lotto_info_count": int(row[4]),
            "fatture_stato_esecuzione_errore_count": int(row[5]),
        }

    # Scopo: L'ELENCO delle segnalazioni del lotto — quello che il riepilogo
    #        conta soltanto.
    #
    # ⭐ LA SORGENTE E' `vendite.fn_list_lotto_segnalazioni` (L2 del brief liste
    #    drawer lotto). La prima versione di questo metodo era una UNION scritta
    #    a mano qui: funzionava, ma era una SECONDA verita' sullo stesso elenco
    #    — e la funzione DB fa di piu' (documento gia' composto, importo, job
    #    corrente, chiave di riga) e tiene la whitelist di ordinamento dove sta
    #    anche la paginazione.
    #
    # ⚠️ `total_count` e `fuori_job_count` arrivano RIPETUTI su ogni riga: e' la
    #    forma della funzione. Si leggono dalla prima; su zero righe non c'e'
    #    nessuna riga da cui leggerli, quindi valgono zero per costruzione.
    # ⚠️ `order_by` NON si valida qui: la funzione ha la sua whitelist e su un
    #    nome ignoto ripiega sul default. Ricopiarla sarebbe la terza verita'.
    def list_lotto_segnalazioni(
        self,
        *,
        lotto_id: int,
        livello: str | None = None,
        origine: str | None = None,
        solo_attive: bool = True,
        solo_job_corrente: bool = False,
        limit: int = 200,
        offset: int = 0,
        order_by: str | None = None,
        order_dir: str = "desc",
        max_rows: int | None = None,
    ) -> tuple[list[LottoSegnalazioneRow], int, int]:
        tetto = _DRAWER_EXPORT_MAX_ROWS if max_rows else 500
        safe_limit = max(1, min(int(max_rows or limit), tetto))
        safe_offset = max(0, int(offset))
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT
                    riga_key, origine, data_ora, livello, messaggio, error_code,
                    fase, fattura_id, documento_display, importo,
                    disabilitato, job_corrente, total_count, fuori_job_count
                FROM vendite.fn_list_lotto_segnalazioni(
                    p_lotto_id          => %s,
                    p_origine           => %s,
                    p_livello           => %s,
                    p_solo_attive       => %s,
                    p_solo_job_corrente => %s,
                    p_limit             => %s,
                    p_offset            => %s,
                    p_order_by          => %s,
                    p_order_dir         => %s
                )
                """,
                [
                    int(lotto_id), origine, livello,
                    bool(solo_attive), bool(solo_job_corrente),
                    safe_limit, safe_offset, order_by or None, order_dir,
                ],
            )
            rows = cursor.fetchall()

        total_count = int(rows[0][12]) if rows else 0
        fuori_job = int(rows[0][13]) if rows else 0
        risultato: list[LottoSegnalazioneRow] = [
            {
                "riga_key": str(row[0]),
                "origine": str(row[1]),
                "data_ora": row[2].isoformat() if row[2] is not None else None,
                "livello": str(row[3]),
                "messaggio": row[4],
                "error_code": row[5],
                "fase": row[6],
                "fattura_id": None if row[7] is None else int(row[7]),
                "documento_display": row[8],
                "importo": str(row[9]) if row[9] is not None else None,
                "disabilitato": bool(row[10]),
                "job_corrente": bool(row[11]),
            }
            for row in rows
        ]
        return risultato, total_count, fuori_job

    # Scopo: Restituisce i task run runtime del lotto ordinati dal più recente per consultazione API/UI.
    def list_lotto_task_runs(
        self,
        lotto_id: int,
        *,
        limit: int = 100,
        offset: int = 0,
        order_by: str | None = None,
        order_dir: str = "desc",
        solo_attivi: bool = True,
        max_rows: int | None = None,
    ) -> tuple[list[LottoTaskRunRow], int]:
        # ⭐ LA SORGENTE E' LA FUNZIONE DB, non una query nostra (BE-2 del brief
        # liste drawer lotto, 2026-08-22). Prima c'erano DUE verita' sullo
        # stesso elenco: una `SELECT` qui, con ordine inchiodato e senza
        # paginazione, e la funzione paginata a DB — e quella a video non era
        # quella dichiarata. La whitelist di ordinamento vive ora in un posto
        # solo, dentro la funzione, dove il presidio del DB la sa leggere.
        #
        # ⚠️ Ritorna la COPPIA (righe, totale): il totale arriva come colonna
        # `total_count` ripetuta su ogni riga — e' la forma della funzione — e
        # va letto dalla prima. Su zero righe non c'e' nessuna riga da cui
        # leggerlo, quindi il totale e' zero per costruzione.
        # ⚠️ `order_by` NON si valida qui: la funzione ha la sua whitelist e su
        # un nome sconosciuto ripiega sul default. Ricopiarla nel backend
        # sarebbe la terza verita'.
        tetto = _DRAWER_EXPORT_MAX_ROWS if max_rows else 500
        safe_limit = max(1, min(int(max_rows or limit), tetto))
        safe_offset = max(0, int(offset))
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT
                    id, lotto_id, pipeline_id, stato_doc_fiscale_id,
                    task_code, fase, tentativo, task_stato,
                    started_at, ended_at, error_code, error_message,
                    meta, total_count
                FROM vendite.fn_list_lotto_task_runs(
                    p_lotto_id   => %s,
                    p_solo_attivi => %s,
                    p_limit      => %s,
                    p_offset     => %s,
                    p_order_by   => %s,
                    p_order_dir  => %s
                )
                """,
                [
                    int(lotto_id),
                    bool(solo_attivi),
                    safe_limit,
                    safe_offset,
                    order_by or None,
                    order_dir,
                ],
            )
            rows = cursor.fetchall()

        total_count = int(rows[0][13]) if rows else 0
        result: list[LottoTaskRunRow] = [
            {
                "id": int(row[0]),
                "lotto_id": int(row[1]),
                "pipeline_id": None if row[2] is None else int(row[2]),
                "stato_doc_fiscale_id": None if row[3] is None else int(row[3]),
                "task_code": str(row[4]),
                "fase": row[5],
                "tentativo": int(row[6]),
                "task_stato": str(row[7]),
                "started_at": None if row[8] is None else row[8].isoformat(),
                "ended_at": None if row[9] is None else row[9].isoformat(),
                "error_code": row[10],
                "error_message": row[11],
                # ⚠️ `jsonb` dal cursore RAW arriva come STRINGA (psycopg 3 non
                # lo decodifica fuori dall'ORM): senza questa conversione il
                # consumatore farebbe `str.get(...)`.
                "meta": jsonb_out(row[12]) or {},
            }
            for row in rows
        ]
        return result, total_count

    # Scopo: Recupera `lotto_stato_doc_fiscale_id` dal contesto applicativo o dal database.
    def get_lotto_stato_doc_fiscale_id(self, lotto_id: int) -> int | None:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT stato_doc_fiscale_id
                FROM vendite.fatturazione_lotti
                WHERE id = %s
                """,
                [lotto_id],
            )
            row = cursor.fetchone()
        if not row or row[0] is None:
            return None
        return int(row[0])

    # Scopo: Risolve l'identificativo dominio task attivo a partire dal codice richiesto.
    def get_dominio_id(self, codice: str | None = None) -> int:
        dominio_code = codice or self.DOMINIO_CODE
        ErrorManager.require(
            bool(dominio_code and str(dominio_code).strip()),
            code="E_PIPELINE_DOMINIO",
            message="Dominio pipeline non valido.",
            detail="codice dominio obbligatorio",
            context={"codice": dominio_code},
            function_name="vendite.pipeline_repository.get_dominio_id",
            log_to_db=True,
        )
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT id
                FROM dbops.domini_task
                WHERE codice = %s
                  AND attivo IS TRUE
                ORDER BY id
                LIMIT 1
                """,
                [dominio_code],
            )
            row = cursor.fetchone()
        if not row:
            ErrorManager.raise_error(
                code="E_PIPELINE_DOMINIO_NOT_FOUND",
                message="Dominio pipeline non trovato.",
                detail=f"Dominio non trovato: {dominio_code}",
                context={"codice": dominio_code},
                function_name="vendite.pipeline_repository.get_dominio_id",
                log_to_db=True,
            )
        return int(row[0])

    # Scopo: Risolve dal registry DB l'handler effettivo per task e implementation_key richiesti.
    def get_task_handler_code(
        self,
        *,
        task_code: str,
        implementation_key: str | None,
        dominio_code: str | None = None,
    ) -> str:
        ErrorManager.require(
            bool(task_code and str(task_code).strip()),
            code="E_PIPELINE_TASK",
            message="Task pipeline non valido.",
            detail="task_code obbligatorio",
            context={"task_code": task_code},
            function_name="vendite.pipeline_repository.get_task_handler_code",
            log_to_db=True,
        )
        dominio_id = self.get_dominio_id(dominio_code)
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT handler_code
                FROM dbops.fn_get_pipeline_task_implementation(%s, %s, %s)
                """,
                [dominio_id, task_code, implementation_key],
            )
            row = cursor.fetchone()
        if not row:
            ErrorManager.raise_error(
                code="E_PIPELINE_TASK_HANDLER_NOT_FOUND",
                message="Handler task non trovato.",
                detail=(
                    "Nessun handler per task "
                    f"{task_code} (implementation_key={implementation_key})"
                ),
                context={
                    "dominio_id": dominio_id,
                    "task_code": task_code,
                    "implementation_key": implementation_key,
                },
                function_name="vendite.pipeline_repository.get_task_handler_code",
                log_to_db=True,
            )
        return str(row[0])

    # Scopo: Recupera `stato_doc_fiscale_id` dal contesto applicativo o dal database.
    def get_stato_doc_fiscale_id(self, codice: str) -> int | None:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT id
                FROM config.stati_doc_fiscale
                WHERE COALESCE(codice_interno, codice) = %s
                  AND attivo IS TRUE
                ORDER BY ordine
                LIMIT 1
                """,
                [codice],
            )
            row = cursor.fetchone()
        if not row:
            return None
        return int(row[0])

    # Scopo: Verifica se lo stato documento corrente richiede la chiusura operativa del lotto.
    def is_stato_doc_chiude_lotto(self, stato_doc_fiscale_id: int) -> bool:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT COALESCE(chiude_lotto, false)
                FROM config.stati_doc_fiscale
                WHERE id = %s
                  AND attivo IS TRUE
                """,
                [stato_doc_fiscale_id],
            )
            row = cursor.fetchone()
        if not row:
            return False
        return bool(row[0])

    # Scopo: Aggiorna `lotto_job_stato` con i valori richiesti dal flusso corrente.
    def set_lotto_job_stato(self, lotto_id: int, stato: str, messaggio: str) -> None:
        stato_input = (stato or "").strip().upper()
        if stato_input not in {"IN_ESECUZIONE", "COMPLETATO", "ERRORE"}:
            ErrorManager.raise_error(
                code="E_PIPELINE_STATO_LOTTO",
                message="stato_lotto non valido.",
                detail=f"stato_lotto non valido: {stato}",
                context={"lotto_id": lotto_id, "stato_lotto": stato},
                function_name="vendite.pipeline_repository.set_lotto_job_stato",
                log_to_db=True,
            )
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT stato_lotto
                FROM vendite.fatturazione_lotti
                WHERE id = %s
                FOR UPDATE
                """,
                [lotto_id],
            )
            row = cursor.fetchone()
            if not row:
                ErrorManager.raise_error(
                    code="E_PIPELINE_LOTTO_NOT_FOUND",
                    message="Lotto pipeline non trovato.",
                    detail=f"Lotto non trovato: {lotto_id}",
                    context={"lotto_id": lotto_id},
                    function_name="vendite.pipeline_repository.set_lotto_job_stato",
                    log_to_db=True,
                )
            stato_corrente = str(row[0]) if row[0] is not None else ""
            if stato_corrente == stato_input:
                return
            if stato_corrente == "IN_ESECUZIONE" and stato_input not in {"COMPLETATO", "ERRORE"}:
                ErrorManager.raise_error(
                    code="E_PIPELINE_STATO_LOTTO",
                    message="Transizione stato_lotto non ammessa.",
                    detail=f"Transizione non ammessa: {stato_corrente} -> {stato_input}",
                    context={
                        "lotto_id": lotto_id,
                        "stato_corrente": stato_corrente,
                        "stato_target": stato_input,
                    },
                    function_name="vendite.pipeline_repository.set_lotto_job_stato",
                    log_to_db=True,
                )
            if stato_corrente == "ERRORE" and stato_input != "IN_ESECUZIONE":
                ErrorManager.raise_error(
                    code="E_PIPELINE_STATO_LOTTO",
                    message="Transizione stato_lotto non ammessa.",
                    detail=f"Transizione non ammessa: {stato_corrente} -> {stato_input}",
                    context={
                        "lotto_id": lotto_id,
                        "stato_corrente": stato_corrente,
                        "stato_target": stato_input,
                    },
                    function_name="vendite.pipeline_repository.set_lotto_job_stato",
                    log_to_db=True,
                )
            if stato_corrente == "COMPLETATO" and stato_input != "IN_ESECUZIONE":
                ErrorManager.raise_error(
                    code="E_PIPELINE_STATO_LOTTO",
                    message="Transizione stato_lotto non ammessa.",
                    detail=f"Transizione non ammessa: {stato_corrente} -> {stato_input}",
                    context={
                        "lotto_id": lotto_id,
                        "stato_corrente": stato_corrente,
                        "stato_target": stato_input,
                    },
                    function_name="vendite.pipeline_repository.set_lotto_job_stato",
                    log_to_db=True,
                )
            cursor.execute(
                """
                UPDATE vendite.fatturazione_lotti
                SET stato_lotto = %s,
                    meta = CASE
                              WHEN %s IS NULL THEN meta
                              ELSE jsonb_set(
                                COALESCE(meta, '{}'::jsonb),
                                '{note_stato}',
                                to_jsonb(%s::text),
                                true
                              )
                           END,
                    data_update = now(),
                    user_update = current_user
                WHERE id = %s
                """,
                [stato_input, messaggio, messaggio, lotto_id],
            )

    # Scopo: Recupera gli step pipeline applicabili con fallback per tipo lotto, utility e tipo documento.
    def list_pipeline_steps(
        self,
        tipo_lotto: str,
        utility_id: int | None,
        tipo_doc_fiscale_id: int | None,
    ) -> list[PipelineStep]:
        # Delega al DB la risoluzione step con fallback e precedenza.
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT stato_doc_fiscale_id, descrizione, ordine
                FROM vendite.fn_list_fatturazione_pipeline_steps(%s, %s, %s)
                """,
                [tipo_lotto, utility_id, tipo_doc_fiscale_id],
            )
            rows = cursor.fetchall()
        return [
            PipelineStep(
                stato_doc_fiscale_id=int(row[0]),
                descrizione=row[1],
                ordine=row[2],
            )
            for row in rows
        ]

    # Scopo: Recupera pipeline_id risolto per lo step indicato via fn_resolve_fatturazione_pipeline_step.
    def get_pipeline_id_for_step(
        self,
        tipo_lotto: str,
        stato_doc_fiscale_id: int,
        utility_id: int | None,
        tipo_doc_fiscale_id: int | None,
    ) -> int | None:
        # Riusa fn_resolve_fatturazione_pipeline_step: pipeline_id è la prima colonna restituita.
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT pipeline_id
                FROM vendite.fn_resolve_fatturazione_pipeline_step(
                    p_tipo_lotto => %s,
                    p_stato_doc_fiscale_id => %s,
                    p_utility_id => %s,
                    p_tipo_doc_fiscale_id => %s,
                    p_rollback => false
                )
                """,
                [tipo_lotto, stato_doc_fiscale_id, utility_id, tipo_doc_fiscale_id],
            )
            row = cursor.fetchone()
        if not row or row[0] is None:
            return None
        return int(row[0])

    # Scopo: Verifica se esiste una policy attiva per il task indicato nel pipeline dato.
    def task_policy_exists(self, pipeline_id: int, task_code: str) -> bool:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT EXISTS (
                    SELECT 1
                    FROM vendite.fatturazione_pipeline_task_policy
                    WHERE pipeline_id = %s
                      AND task_code = %s
                      AND attivo IS TRUE
                )
                """,
                [pipeline_id, task_code],
            )
            row = cursor.fetchone()
        if not row:
            return False
        return bool(row[0])

    # Scopo: Risolve la modalità di esecuzione task (RUN/SKIP/RESUME/RESET_REQUIRED) delegando al DB.
    def resolve_lotto_task_execution_mode(
        self,
        lotto_id: int,
        pipeline_id: int,
        stato_doc_fiscale_id: int,
        task_code: str,
    ) -> TaskExecutionMode:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT execution_mode, annullabile, resume_mode,
                       last_task_stato, last_tentativo, policy_meta, run_meta
                FROM vendite.fn_resolve_lotto_task_execution_mode(%s, %s, %s, %s)
                """,
                [lotto_id, pipeline_id, stato_doc_fiscale_id, task_code],
            )
            row = cursor.fetchone()
        assert row is not None
        policy_meta: Any = row[5]
        run_meta: Any = row[6]
        if isinstance(policy_meta, str):
            try:
                policy_meta = json.loads(policy_meta)
            except json.JSONDecodeError:
                policy_meta = {}
        if isinstance(run_meta, str):
            try:
                run_meta = json.loads(run_meta)
            except json.JSONDecodeError:
                run_meta = {}
        return TaskExecutionMode(
            execution_mode=str(row[0]),
            annullabile=bool(row[1]),
            resume_mode=str(row[2]) if row[2] is not None else "",
            last_task_stato=row[3],
            last_tentativo=None if row[4] is None else int(row[4]),
            policy_meta=policy_meta if isinstance(policy_meta, dict) else {},
            run_meta=run_meta if isinstance(run_meta, dict) else {},
        )

    # Scopo: Apre un nuovo task run in stato IN_ESECUZIONE delegando al DB.
    #
    # ⚠️ ARGOMENTI NOMINATI, e non e' cosmesi. Il changeSet 67 ha aggiunto
    #    `p_correlation_id` e ha DROPpato la firma a sei nello stesso giro,
    #    perche' `CREATE OR REPLACE` con un parametro in PIU' non sostituisce:
    #    crea una funzione nuova e lascia viva la vecchia, e una chiamata a sei
    #    argomenti le soddisfa **entrambe** («la funzione non e' unica»). Con i
    #    nomi, un'altra revisione della firma si vede in fase di chiamata invece
    #    di scivolare su un parametro adiacente dello stesso tipo.
    def start_lotto_task_run(
        self,
        *,
        lotto_id: int,
        pipeline_id: int,
        stato_doc_fiscale_id: int,
        task_code: str,
        fase: str | None,
        meta: LottoPipelineMeta | None,
        correlation_id: str | None = None,
    ) -> TaskRunResult:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT task_run_id, tentativo
                FROM vendite.fn_start_lotto_task_run(
                    p_lotto_id => %s,
                    p_pipeline_id => %s,
                    p_stato_doc_fiscale_id => %s,
                    p_task_code => %s,
                    p_fase => %s,
                    p_meta => %s::jsonb,
                    p_correlation_id => %s::uuid
                )
                """,
                [
                    lotto_id,
                    pipeline_id,
                    stato_doc_fiscale_id,
                    task_code,
                    fase,
                    self._to_jsonb_param(meta),
                    correlation_id,
                ],
            )
            row = cursor.fetchone()
        assert row is not None
        return TaskRunResult(
            task_run_id=int(row[0]),
            tentativo=int(row[1]),
        )

    # Scopo: Chiude un task run con esito COMPLETATO delegando al DB.
    def complete_lotto_task_run(
        self,
        task_run_id: int,
        meta: LottoPipelineMeta | None = None,
    ) -> None:
        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT vendite.fn_complete_lotto_task_run(%s, %s::jsonb)",
                [task_run_id, self._to_jsonb_param(meta)],
            )

    # Scopo: Chiude un task run con esito ERRORE delegando al DB.
    def fail_lotto_task_run(
        self,
        task_run_id: int,
        error_code: str,
        error_message: str,
        meta: LottoPipelineMeta | None = None,
    ) -> None:
        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT vendite.fn_fail_lotto_task_run(%s, %s, %s, %s::jsonb)",
                [task_run_id, error_code, error_message, self._to_jsonb_param(meta)],
            )

    # Scopo: Gestisce `update_lotto_stato_doc` nel flusso applicativo del modulo.
    def update_lotto_stato_doc(self, lotto_id: int, stato_doc_fiscale_id: int) -> None:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                UPDATE vendite.fatturazione_lotti
                SET stato_doc_fiscale_id = %s,
                    data_update = now(),
                    user_update = current_user
                WHERE id = %s
                """,
                [stato_doc_fiscale_id, lotto_id],
            )

    # Scopo: Gestisce `close_giornaliero_lotto` nel flusso applicativo del modulo.
    def close_giornaliero_lotto(self, lotto_id: int, inviata_id: int) -> None:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT vendite.fn_close_giornaliero_lotto(%s, %s)
                """,
                [lotto_id, inviata_id],
            )

    # Scopo: Chiude il lotto a livello operativo senza forzare transizioni stato documento.
    def close_lotto_operativo(self, lotto_id: int) -> None:
        # Chiusura operativa lotto senza vincolare lo stato documentale.
        with connection.cursor() as cursor:
            cursor.execute(
                """
                UPDATE vendite.fatturazione_lotti
                SET stato_operativo = 'CHIUSO',
                    data_update = now(),
                    user_update = current_user
                WHERE id = %s
                """,
                [lotto_id],
            )

    # Scopo: Scrive il log di fase lotto su tabella/funzione dominio con metadati strutturati.
    def log_pipeline_fase(
        self,
        lotto_id: int,
        stato_doc_fiscale_id: int | None,
        fase: str,
        status: str,
        messaggio: str | None,
        meta: LottoPipelineMeta | None,
    ) -> None:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT vendite.fn_log_pipeline_fase(
                    %s, %s, %s, %s, %s, %s::jsonb
                )
                """,
                [
                    lotto_id,
                    stato_doc_fiscale_id,
                    fase,
                    status,
                    messaggio,
                    self._to_jsonb_param(meta),
                ],
            )

    # Scopo: Scrive un log puntuale su singola fattura in `vendite.fatture_log`.
    def log_fattura(
        self,
        *,
        fattura_id: int,
        status: str,
        messaggio: str,
        critical: bool,
        meta: LottoPipelineMeta | None = None,
    ) -> None:
        # Inserisce un log funzionale puntuale su singola fattura.
        self._insert_fatture_log(
            fattura_id_select_sql="SELECT %s::bigint AS fattura_id",
            fattura_id_select_params=[fattura_id],
            status=status,
            messaggio=messaggio,
            meta=meta,
        )

    # Scopo: Marca UNA fattura del lotto come fallita (`stato_esecuzione='ERRORE'`)
    #        e ci attacca il messaggio, in `vendite.fatture_log`.
    #
    # ⭐ IL VALORE 'ERRORE' ESISTE NEL MODELLO DA SEMPRE — CHECK della tabella e
    #    contatore `fatture_stato_esecuzione_errore_count` nella summary — e
    #    NESSUNO LO SCRIVEVA MAI: misurato il 2026-08-21, 16 righe su 16 a
    #    'COMPLETED', comprese quelle di un lotto il cui documento era stato
    #    rifiutato. Il posto per raccontarlo c'era; mancava chi lo riempisse.
    #
    # ⚠️ SI CHIAMA FUORI DALLA TRANSAZIONE DELLO STEP, ed è tutto il punto: il
    #    giro per-fattura è fail-fast, quindi lo step viene annullato: una riga
    #    scritta dentro sparirebbe col rollback insieme all'errore che
    #    descrive. È il motivo per cui, fino al 2026-08-21, un fallimento non
    #    lasciava traccia da nessuna parte — né sulla riga, né in testata.
    # ⚠️ `atomic()`: la marcatura sul ponte e il messaggio sul log sono la
    # stessa informazione in due tabelle — una spia accesa senza il suo motivo
    # e' peggio di nessuna spia, ed e' proprio il difetto che questo metodo
    # esiste per chiudere.
    def marca_fattura_in_errore(
        self,
        *,
        lotto_id: int,
        fattura_id: int,
        code: str,
        messaggio: str,
        meta: LottoPipelineMeta | None = None,
    ) -> None:
        with transaction.atomic():
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    UPDATE vendite.fatturazione_lotti_fatture
                       SET stato_esecuzione = 'ERRORE'
                     WHERE lotto_id = %s
                       AND fattura_id = %s
                    """,
                    [int(lotto_id), int(fattura_id)],
                )
            self.log_fattura(
                fattura_id=fattura_id,
                status="C",
                messaggio=messaggio,
                critical=True,
                # ⭐ `origine` FIRMA la riga: e' cio' che permette al giro
                # successivo di ritirare le SUE bandiere senza toccare quelle
                # alzate dai task DB, che hanno un altro padrone e un'altra vita.
                meta={
                    **(meta or {}),
                    # ⚠️ `error_code` e NON `code`: e' la chiave che scrivono
                    # le quattro funzioni DB (D-7) ed e' quella che la lista 47
                    # dichiara come `campo_sorgente`. Con `code` le righe del
                    # backend sarebbero rimaste invisibili nella colonna
                    # «codice» — presenti in tabella e vuote a video, che e' il
                    # modo peggiore di sbagliare.
                    "error_code": code,
                    "lotto_id": lotto_id,
                    "scritto_da": _ORIGINE_SEGNALAZIONE_BE,
                },
            )

    # Scopo: Gestisce `log_lotto_esito_fatture` nel flusso applicativo del modulo.
    def log_lotto_esito_fatture(self, lotto_id: int) -> None:
        # Deriva severita` lotto da fatture_log (C > W > I) e scrive su fatturazione_lotti_log.
        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT vendite.fn_log_lotto_esito_fatture(%s)",
                [lotto_id],
            )

    # `log_event` NON sta piu' qui: e' il building block
    # `EventLogRepositoryMixin` (`_event_log_repo_mixin.py`), estratto con la
    # consegna BE-6 perche' era copia carbone in questo repository e in
    # `commesse_repository`. La firma e' passata da nove parametri a SEI.

    # Scopo: Scrive un log massivo su tutte le fatture collegate al lotto.
    def log_fatture_lotto(
        self,
        *,
        lotto_id: int,
        status: str,
        messaggio: str,
        meta: LottoPipelineMeta | None = None,
    ) -> None:
        # Logga un messaggio tecnico su tutte le fatture collegate al lotto.
        self._insert_fatture_log(
            fattura_id_select_sql="""
                SELECT lf.fattura_id
                FROM vendite.fatturazione_lotti_fatture lf
                WHERE lf.lotto_id = %s
            """,
            fattura_id_select_params=[lotto_id],
            status=status,
            messaggio=messaggio,
            meta=meta,
        )

    # Scopo: Inserisce righe su `vendite.fatture_log` usando una SELECT sorgente dei fattura_id.
    def _insert_fatture_log(
        self,
        *,
        fattura_id_select_sql: str,
        fattura_id_select_params: list[Any],
        status: str,
        messaggio: str,
        meta: LottoPipelineMeta | None,
    ) -> None:
        # Helper unico INSERT fatture_log; la SELECT fattura_id proviene solo da SQL interno.
        with connection.cursor() as cursor:
            cursor.execute(
                f"""
                INSERT INTO vendite.fatture_log (
                    fattura_id,
                    data_ora,
                    messaggio,
                    status,
                    disabilitato,
                    meta
                )
                SELECT
                    src.fattura_id,
                    now(),
                    %s,
                    %s,
                    false,
                    COALESCE(%s::jsonb, '{{}}'::jsonb)
                FROM (
                    {fattura_id_select_sql}
                ) AS src
                """,
                [
                    messaggio,
                    status,
                    self._to_jsonb_param(meta),
                    *fattura_id_select_params,
                ],
            )

    # Scopo: Recupera `lotto_context` dal contesto applicativo o dal database.
    #        Include il PERIMETRO MIRATO (`gruppi`) letto dalla tabella figlia
    #        `fatturazione_lotti_gruppi`: e' l'unico canale con cui il criterio
    #        raggiunge gli step, che ricevono solo `lotto_id` (brief emissione
    #        mirata, D-3). Nessuna riga = nessuna restrizione (`gruppi=None`).
    def get_lotto_context(self, lotto_id: int) -> LottoContext | None:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT l.competenza_mese,
                       l.tipo_doc_fiscale_id,
                       l.utility_id,
                       l.billing_account_id,
                       l.lock_batch_id,
                       l.emittente_soggetto_ruolo_id,
                       (l.meta->>%s)::boolean,
                       (
                           SELECT array_agg(g.gruppo_key ORDER BY g.gruppo_key)
                           FROM vendite.fatturazione_lotti_gruppi g
                           WHERE g.lotto_id = l.id
                       )
                FROM vendite.fatturazione_lotti l
                WHERE l.id = %s
                """,
                [LOTTO_META_KEY_FATTURAZIONE_IMMEDIATA, lotto_id],
            )
            row = cursor.fetchone()
        if not row:
            return None
        # array_agg su zero righe ritorna NULL, non un array vuoto: la
        # distinzione «nessuna riga» -> None e' proprio la convenzione DB
        # (assenza di criterio = comportamento odierno). Un array vuoto
        # significherebbe «nessun gruppo ammesso» ed e' il contrario.
        gruppi_raw = row[7]
        return LottoContext(
            competenza_mese=row[0],
            tipo_doc_fiscale_id=row[1],
            utility_id=row[2],
            billing_account_id=row[3],
            lock_batch_id=row[4],
            emittente_soggetto_ruolo_id=None if row[5] is None else int(row[5]),
            fatturazione_immediata=row[6],
            gruppi=None if not gruppi_raw else tuple(str(g) for g in gruppi_raw),
        )

    # Scopo: Persiste il PERIMETRO MIRATO del lotto in
    #        `vendite.fatturazione_lotti_gruppi`. Da chiamare nella STESSA
    #        transazione della creazione del lotto (contratto BE §8-bis del
    #        brief DB): il criterio non e' un parametro di chiamata, e' uno
    #        stato del lotto, e un lotto creato senza i suoi gruppi sarebbe un
    #        giro di massa mascherato da giro mirato.
    # Perimetro: solo INSERT idempotente (UNIQUE lotto_id+gruppo_key). Non
    #        cancella nulla: il perimetro di un lotto non si riscrive.
    # Risultato: numero di righe EFFETTIVAMENTE inserite (`rowcount`, non le
    #        chiavi richieste: con ON CONFLICT DO NOTHING i duplicati non
    #        producono riga e dichiararli scritti sarebbe un conteggio falso).
    def set_lotto_gruppi(self, lotto_id: int, gruppi: tuple[str, ...] | list[str]) -> int:
        # Normalizzazione allineata a `fn_build_gruppo_fatturabile_key`: una
        # chiave con spazi in coda non combacerebbe MAI con quella costruita
        # dal DB e filtrerebbe zero righe senza dirlo. Lo strip sta qui e non
        # solo nel validatore d'ingresso perche' questo metodo e' pubblico.
        chiavi = [k for k in (str(g).strip() for g in gruppi) if k]
        if not chiavi:
            return 0
        with connection.cursor() as cursor:
            cursor.execute(
                """
                INSERT INTO vendite.fatturazione_lotti_gruppi (lotto_id, gruppo_key)
                SELECT %s, k
                FROM unnest(%s::text[]) AS k
                ON CONFLICT (lotto_id, gruppo_key) DO NOTHING
                """,
                [lotto_id, chiavi],
            )
            return cursor.rowcount

    # Scopo: Recupera i task JSON dello step (processi o rollback) e normalizza il payload in lista Python.
    def get_step_processes(
        self,
        stato_doc_fiscale_id: int,
        *,
        tipo_lotto: str,
        utility_id: int | None,
        tipo_doc_fiscale_id: int | None,
        rollback: bool,
    ) -> list[dict[str, Any]]:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT processi
                FROM vendite.fn_resolve_fatturazione_pipeline_step(
                    p_tipo_lotto => %s,
                    p_stato_doc_fiscale_id => %s,
                    p_utility_id => %s,
                    p_tipo_doc_fiscale_id => %s,
                    p_rollback => %s
                )
                """,
                [
                    tipo_lotto,
                    stato_doc_fiscale_id,
                    utility_id,
                    tipo_doc_fiscale_id,
                    rollback,
                ],
            )
            row = cursor.fetchone()

        if not row:
            return []

        value = row[0]
        if isinstance(value, list):
            return value
        if isinstance(value, str):
            # In alcuni ambienti il jsonb puo` arrivare serializzato come stringa.
            try:
                decoded = json.loads(value)
            except json.JSONDecodeError:
                return []
            if isinstance(decoded, list):
                return decoded
            return []
        return []

    # Scopo: Gestisce `has_step_processes` nel flusso applicativo del modulo.
    def has_step_processes(
        self,
        *,
        stato_doc_fiscale_id: int,
        tipo_lotto: str,
        utility_id: int | None,
        tipo_doc_fiscale_id: int | None,
        rollback: bool,
    ) -> bool:
        return bool(
            self.get_step_processes(
                stato_doc_fiscale_id,
                tipo_lotto=tipo_lotto,
                utility_id=utility_id,
                tipo_doc_fiscale_id=tipo_doc_fiscale_id,
                rollback=rollback,
            )
        )

    # Scopo: Invoca la funzione SQL di selezione attivita fatturabili normalizzando i parametri runtime.
    def run_select_attivita_task(
        self,
        context: LottoContext,
        params: dict[str, Any],
    ) -> None:
        assert context is not None
        # Normalizza i parametri JSON prima della chiamata alla funzione SQL.
        lock = as_bool(params.get("lock"), default=False)
        data_fatturazione = empty_to_none(params.get("data_fatturazione"))
        valuta_id = empty_to_none(params.get("valuta_id"))
        # Emittente: fonte primaria e` il lotto persistito (context); i params JSON non lo sovrascrivono.
        emittente_id = context.emittente_soggetto_ruolo_id
        limit_value = empty_to_none(params.get("limit"))

        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT vendite.fn_select_attivita_fatturabili(
                    p_competenza_mese => %s,
                    p_tipo_doc_fiscale_id => %s,
                    p_lock_batch_id => %s::uuid,
                    p_lock => %s,
                    p_data_fatturazione => COALESCE(%s, CURRENT_DATE),
                    p_billing_account_id => %s,
                    p_utility_id => %s,
                    p_valuta_id => %s,
                    p_emittente_soggetto_ruolo_id => %s,
                    p_limit => %s,
                    p_gruppi => %s::text[]
                )
                """,
                [
                    context.competenza_mese,
                    context.tipo_doc_fiscale_id,
                    context.lock_batch_id if lock else None,
                    lock,
                    data_fatturazione,
                    context.billing_account_id,
                    context.utility_id,
                    valuta_id,
                    emittente_id,
                    limit_value,
                    # Perimetro mirato: e' il punto DECISIVO. Il filtro sul pull
                    # non basta — qui si filtrano le AF GIA' ESISTENTI (residui di
                    # giri interrotti, reset, giro schedulato a meta'), che
                    # altrimenti un lotto mirato rastrellerebbe.
                    # ⚠️ `if context.gruppi` e non `is not None`: una tupla VUOTA
                    # diventerebbe `'{}'::text[]`, e `= ANY('{}')` e' sempre
                    # falso → zero righe. Vuoto e assente devono collassare
                    # entrambi su NULL = nessuna restrizione (convenzione DB).
                    list(context.gruppi) if context.gruppi else None,
                ],
            )

    # Scopo: Recupera `group_attivita_input` dal contesto applicativo o dal database.
    def get_group_attivita_input(self, attivita_id: int) -> GroupAttivitaInput | None:
        with connection.cursor() as cursor:
            cursor.execute(_GROUP_ATTIVITA_SELECT + " WHERE a.id = %s", [attivita_id])
            row = cursor.fetchone()
        if not row:
            return None
        return _group_attivita_input_da_row(row)

    # Scopo: Fetch batch di GroupAttivitaInput per una lista di attivita_id.
    # Singola query con ANY(%s) al posto di N query singole.
    def batch_get_group_attivita_inputs(
        self, attivita_ids: list[int]
    ) -> dict[int, GroupAttivitaInput]:
        if not attivita_ids:
            return {}
        with connection.cursor() as cursor:
            cursor.execute(
                _GROUP_ATTIVITA_SELECT + " WHERE a.id = ANY(%s)", [attivita_ids]
            )
            rows = cursor.fetchall()
        return {int(row[0]): _group_attivita_input_da_row(row) for row in rows}

    # Scopo: Restituisce elenco `attivita_da_fatturare` in base ai filtri disponibili.
    # Safety-net: LIMIT con default alto per evitare memory explosion su lotti massivi.
    def list_attivita_da_fatturare(
        self, lotto_id: int, *, limit: int = 50000
    ) -> list[AttivitaDaFatturare]:
        safe_limit = max(1, min(int(limit), 100000))
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT
                    a.id,
                    a.articolo_id,
                    a.quantita,
                    a.prezzo_unitario,
                    a.uom_id,
                    a.sorgente_tipo_id,
                    a.sorgente_uid,
                    a.sorgente_riga,
                    art.descrizione,
                    a.meta,
                    a.tipo_movimento
                FROM vendite.attivita_fatturabili a
                JOIN catalogo.articoli art
                  ON art.id = a.articolo_id
                WHERE a.lock_batch_id = (
                        SELECT fl.lock_batch_id
                        FROM vendite.fatturazione_lotti fl
                        WHERE fl.id = %s
                      )
                  AND a.fatturato IS FALSE
                  AND COALESCE(a.lock_in_fatturazione, false) IS TRUE
                ORDER BY a.id
                LIMIT %s
                """,
                [lotto_id, safe_limit],
            )
            rows = cursor.fetchall()
        if len(rows) == safe_limit:
            logger.warning(
                "list_attivita_da_fatturare: risultato troncato al limit=%s per lotto_id=%s",
                safe_limit, lotto_id,
            )
        return [
            AttivitaDaFatturare(
                id=int(row[0]),
                articolo_id=None if row[1] is None else str(row[1]),
                quantita=row[2],
                prezzo_unitario=row[3],
                uom_id=None if row[4] is None else int(row[4]),
                sorgente_tipo_id=None if row[5] is None else int(row[5]),
                sorgente_uid=row[6],
                sorgente_riga=row[7],
                articolo_descrizione=row[8],
                # Il driver restituisce `jsonb` come STRINGA: senza coercion
                # lo snapshot kit a valle farebbe `str.get(...)`. I test
                # mockati non lo vedono, iniettano gia' dei dict.
                meta=coerce_jsonb_dict(row[9]),
                tipo_movimento=row[10] or TIPO_MOVIMENTO_NORMALE,
            )
            for row in rows
        ]

    # Scopo: Restituisce elenco `fatture_by_lotto` in base ai filtri disponibili.
    # Safety-net: LIMIT con default alto per evitare memory explosion su lotti massivi.
    # 📌 L'`ORDER BY f.id` serve alla stabilita' del risultato (due chiamanti, e il
    # troncamento al limit deve tagliare sempre dalla stessa parte). NON e' il
    # presidio dell'ordine di numerazione: quel requisito vive dove serve, in
    # `_handle_numera_fatture_task`, che riordina per conto suo.
    def list_fatture_by_lotto(self, lotto_id: int, *, limit: int = 50000) -> list[int]:
        safe_limit = max(1, min(int(limit), 100000))
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT f.id
                FROM vendite.fatturazione_lotti_fatture lf
                JOIN vendite.fatture f
                  ON f.id = lf.fattura_id
                WHERE lf.lotto_id = %s
                ORDER BY f.id
                LIMIT %s
                """,
                [lotto_id, safe_limit],
            )
            rows = cursor.fetchall()
        if len(rows) == safe_limit:
            logger.warning(
                "list_fatture_by_lotto: risultato troncato al limit=%s per lotto_id=%s",
                safe_limit, lotto_id,
            )
        return [int(row[0]) for row in rows]

    # Scopo: Genera i fondi source di tutto il lotto con UNA chiamata alla madre
    #        DB `fn_genera_fondi_fattura_lotto`. Ritorna i conteggi del giro
    #        (fatture nello scope, chiavi distinte, fondi creati) per il diario.
    # ⭐ R-3 APPLICATO (brief fondo fattura §8.3, DB 2026-08-15): il repository
    # non conosce piu' la pseudo-chiave a cinque parametri ne' l'SQL dello scope
    # — erano due cose di DOMINIO che vivevano in un repository. Ora una
    # `SELECT` sola: atomica per costruzione (una funzione = uno statement = una
    # transazione), qualunque sia il chiamante.
    # ⚠️ Il codice interno del tipo fondo si passa COSI' COM'E': la madre lo
    # risolve da se'. Il lookup Python e' sparito, ed era il round-trip in piu'
    # che impediva «una SELECT per task».
    # 🔴 E la madre gira una volta per CHIAVE, non per fattura: la vecchia query
    # Python faceva `SELECT DISTINCT` con l'id della fattura in proiezione,
    # quindi il DISTINCT non deduplicava nulla e su un lotto di 500 fatture
    # dello stesso emittente riscandiva le stesse sorgenti 500 volte per
    # crearle una volta (l'atto unico bloccava le altre 499). Difetto trovato
    # dal team DB scrivendo la madre: *chi itera sulle fatture per passare una
    # chiave sta iterando sull'oggetto sbagliato.*
    def run_genera_fondi_source_lotto_task(
        self,
        *,
        lotto_id: int,
        tipo_fondo_codice_interno: str = "F_F_ADD_ACC",
    ) -> dict[str, int]:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT fatture_count, chiavi_count, fondi_creati
                FROM vendite.fn_genera_fondi_fattura_lotto(%s, %s)
                """,
                [lotto_id, tipo_fondo_codice_interno],
            )
            row = cursor.fetchone()
        assert row is not None
        esito = {
            "fatture_count": int(row[0]),
            "chiavi_count": int(row[1]),
            "fondi_creati": int(row[2]),
        }
        logger.info(
            "genera_fondi_source_lotto: lotto_id=%s fatture=%s chiavi=%s creati=%s",
            lotto_id, esito["fatture_count"], esito["chiavi_count"], esito["fondi_creati"],
        )
        return esito

    # Scopo: Applica i fondi DISPONIBILE alle fatture del lotto con UNA chiamata
    #        alla madre DB `fn_applica_fondi_lotto`. Ritorna i conteggi del giro
    #        (fatture nello scope, fondi applicati).
    # ⚠️ La madre itera per FATTURA e non per chiave come la sorella di
    # generazione, e non e' un'asimmetria da correggere: le sorgenti si trovano
    # per chiave e non appartengono al lotto, mentre ogni figlia riceve i SUOI
    # fondi e cambia il proprio totale — deduplicare per chiave qui vorrebbe
    # dire assegnare tutto a una figlia sola e lasciare le altre a secco.
    # ⭐ Qui il parziale costava piu' che altrove: ogni chiamata riuscita ha gia'
    # portato una source ad ASSEGNATO e cambiato il totale di una fattura, e un
    # lotto in cui alcune figlie hanno il fondo e altre no non ha nessuna meta'
    # sbagliata di per se' — quindi niente lo segnalerebbe.
    def run_applica_fondi_lotto_task(
        self,
        *,
        lotto_id: int,
        tipo_fondo_codice_interno: str = "F_F_ADD_ACC",
    ) -> dict[str, int]:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT fatture_count, fondi_applicati
                FROM vendite.fn_applica_fondi_lotto(%s, %s)
                """,
                [lotto_id, tipo_fondo_codice_interno],
            )
            row = cursor.fetchone()
        assert row is not None
        esito = {"fatture_count": int(row[0]), "fondi_applicati": int(row[1])}
        logger.info(
            "applica_fondi_lotto: lotto_id=%s fatture=%s applicati=%s",
            lotto_id, esito["fatture_count"], esito["fondi_applicati"],
        )
        return esito

    # Scopo: Avvia il ricalcolo IVA del lotto con aggiornamento riepiloghi/totali via funzione SQL.
    def run_ricalcola_iva_lotto_task(
        self,
        *,
        lotto_id: int,
        batch_size: int = 1000,
    ) -> None:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT * FROM vendite.fn_ricalcola_riepiloghi_iva_lotto(%s, %s)
                """,
                [lotto_id, batch_size],
            )

    # Scopo: Esegue lo snapshot dei satelliti «di intestazione» delle fatture
    #        del lotto delegando a `vendite.fn_snapshot_fattura_lotto` (Fase 2.2
    #        piano DB satelliti). Il wrapper DB chiama due funzioni sorelle —
    #        indirizzi (`fatture_indirizzi`) e intestazione fiscale
    #        (`fatture.emittente_snapshot` / `cliente_snapshot`) — nella stessa
    #        transazione, ed e' il motivo per cui i contatori sono sei:
    #        `intestazioni_scritte` misura il lavoro che le righe di indirizzo
    #        non descrivono (brief snapshot-intestazione §10.1).
    #        La funzione NON solleva per la singola fattura difettosa (D-Q: le
    #        altre ricevono il loro lavoro; la difettosa e' marcata 'C' su
    #        fatture_log dal DB): l'esito arriva nei contatori, e
    #        `failed_rows > 0` e' il segnale che l'handler traduce in task_run
    #        ERRORE — altrimenti il rilancio dello step salterebbe il task
    #        (COMPLETATO → SKIP) e la correzione non verrebbe mai riletta.
    #        Il nome del metodo segue il `task_code`, non la funzione SQL: il
    #        task e' l'ancora stabile del registry, la funzione e' dietro il
    #        wrapper.
    def run_snapshot_indirizzi_lotto_task(
        self,
        *,
        lotto_id: int,
        batch_size: int = 1000,
    ) -> dict[str, int]:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT fatture_count, inserted_rows, updated_rows,
                       intestazioni_scritte, skipped_rows, failed_rows
                FROM vendite.fn_snapshot_fattura_lotto(%s, %s)
                """,
                [lotto_id, batch_size],
            )
            row = cursor.fetchone()
        assert row is not None  # la fn ritorna sempre una riga di contatori
        return {
            "fatture_count": int(row[0]),
            "inserted_rows": int(row[1]),
            "updated_rows": int(row[2]),
            "intestazioni_scritte": int(row[3]),
            "skipped_rows": int(row[4]),
            "failed_rows": int(row[5]),
        }

    # Scopo: Genera il piano rate delle fatture del lotto delegando a
    #        `vendite.fn_genera_scadenze_lotto` (Fase 4.2 piano DB satelliti).
    #        Perimetro: le sole fatture LAVORABILI (DRAFT o EMESSA e senza un
    #        critico attivo di un ALTRO task); risultato atteso: sei contatori,
    #        di cui `deleted_rows`/`inserted_rows` misurano il DELETE+INSERT del
    #        generatore — un rilancio su piano invariato torna `del=N ins=N`,
    #        non zero, quindi non sono un indicatore di «lavoro nuovo».
    #        I due motivi di salto restano SEPARATI e non vanno sommati:
    #        `skipped_rows` sono fatture oltre EMESSA (chiuse: nessun lavoro da
    #        fare, D-F), `skipped_errore_rows` sono fatture con un critico
    #        altrui (rotte a monte, D-Q). Per il cockpit sono l'opposto, e un
    #        totale unico direbbe «cinque saltate» confondendo i due casi.
    #        Come la gemella degli indirizzi la funzione NON solleva per la
    #        singola fattura difettosa: l'esito sta in `failed_rows`, che
    #        l'handler traduce in task_run ERRORE.
    def run_genera_scadenze_lotto_task(
        self,
        *,
        lotto_id: int,
        batch_size: int = 1000,
    ) -> dict[str, int]:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT fatture_count, deleted_rows, inserted_rows,
                       skipped_rows, skipped_errore_rows, failed_rows
                FROM vendite.fn_genera_scadenze_lotto(%s, %s)
                """,
                [lotto_id, batch_size],
            )
            row = cursor.fetchone()
        assert row is not None  # la fn ritorna sempre una riga di contatori
        return {
            "fatture_count": int(row[0]),
            "deleted_rows": int(row[1]),
            "inserted_rows": int(row[2]),
            "skipped_rows": int(row[3]),
            "skipped_errore_rows": int(row[4]),
            "failed_rows": int(row[5]),
        }

    # Scopo: Ritira le segnalazioni critiche di LOTTO alzate dal BE (D-Q p.2:
    #        «chi alza la bandiera la abbassa»). Due famiglie, riconoscibili dal
    #        meta e MAI le righe altrui:
    #        - gli errori pipeline scritti da PipelineErrorLogger scope LOTTO
    #          (`meta->>'scope' = 'LOTTO'`);
    #        - gli esiti derivati da `fn_log_lotto_esito_fatture`
    #          (`meta->>'source' = 'fatture_log'`): sono FOTOGRAFIE dei log
    #          fatture — la pipeline ne scrive una fresca a fine step, quindi le
    #          vecchie sono stale per costruzione. Senza questo ritiro un lotto
    #          resterebbe bloccato per sempre dalla fotografia di un problema
    #          gia' risolto (i log fatture li ritira il task DB al successo, ma
    #          nessuno ritirava la loro copia derivata).
    #        Chiamata DENTRO la transazione dello step: se lo step fallisce, il
    #        rollback ripristina le bandiere — e' cio' che rende il ritiro
    #        equivalente a «solo al successo» senza logica in piu'.
    #        Ritorna il numero di righe disattivate (telemetria/test).
    def disattiva_segnalazioni_lotto_be(self, lotto_id: int) -> int:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                UPDATE vendite.fatturazione_lotti_log
                   SET disabilitato = TRUE,
                       data_update = now(),
                       user_update = current_user
                 WHERE lotto_id = %s
                   AND disabilitato IS FALSE
                   AND status = 'C'
                   AND (meta->>'scope' = 'LOTTO' OR meta->>'source' = 'fatture_log')
                """,
                [lotto_id],
            )
            return cursor.rowcount

    # Scopo: RITIRA le marcature di fallimento che il BE ha messo sulle fatture
    #        di questo lotto — la bandiera per riga, gemella di
    #        `disattiva_segnalazioni_lotto_be` che fa lo stesso sul lotto.
    #
    # ⭐ «CHI ALZA LA BANDIERA LA ABBASSA», e senza questo pezzo la regola era
    #    rotta a meta': dal 2026-08-21 il BE ALZA `stato_esecuzione='ERRORE'` e
    #    scrive un log critico quando un documento fallisce — ma nessuno li
    #    toglieva piu'. Il primo fallimento rendeva quindi il lotto
    #    definitivamente non avanzabile: la guardia unificata (PRE-1) conta sia
    #    i log critici sia le righe in ERRORE, quindi il tentativo successivo
    #    trovava `blocks_next_step` e si fermava con «Lotto bloccato per
    #    segnalazioni critiche» — cioe' con un messaggio che parla d'altro,
    #    dopo che l'operatore aveva corretto la causa. Una porta a senso unico.
    #
    # ⚠️ Ritira SOLO cio' che ha scritto il BE (`meta->>'scritto_da'`): le
    #    segnalazioni dei task DB hanno un altro padrone e le ritira lui quando
    #    il suo problema e' risolto. Spegnerle qui vorrebbe dire nascondere un
    #    problema che nessuno ha toccato.
    # ⚠️ `stato_esecuzione` torna a 'COMPLETED' e non a 'PENDING': e' il valore
    #    che quelle righe avevano prima del fallimento — il ponte descrive
    #    l'esito dell'ULTIMO giro, e il giro nuovo non e' ancora andato male.
    # ⚠️ E si sblocca SOLO cio' che questo ritiro ha davvero in carico: le
    #    fatture con una marcatura firmata BE. Una riga in 'ERRORE' messa da un
    #    task DB non e' nostra e resta dov'e' — il filtro sull'origine c'era sui
    #    log e mancava sul ponte, un'asimmetria che nessun test avrebbe visto
    #    finche' i task DB non cominciano a scrivere 'ERRORE' (oggi non lo
    #    fanno, domani si').
    # ⚠️ Le due scritture sono UNA cosa sola: ritirare i log senza rimettere a
    # posto il ponte (o viceversa) lascerebbe il lotto in uno stato che la
    # guardia PRE-1 legge a meta' — bloccato da una sorgente e libero
    # dall'altra. `atomic()` qui e' un savepoint quando siamo dentro una
    # transazione e una transazione vera quando non lo siamo: in entrambi i
    # casi le due righe stanno o cadono insieme.
    def ritira_marcature_fatture_be(self, lotto_id: int) -> int:
        with transaction.atomic(), connection.cursor() as cursor:
            cursor.execute(
                """
                UPDATE vendite.fatture_log fl
                   SET disabilitato = TRUE,
                       data_update = now(),
                       user_update = current_user
                  FROM vendite.fatturazione_lotti_fatture lf
                 WHERE lf.lotto_id = %s
                   AND fl.fattura_id = lf.fattura_id
                   AND fl.disabilitato IS FALSE
                   AND fl.status = 'C'
                   AND fl.meta->>'scritto_da' = %s
                """,
                [int(lotto_id), _ORIGINE_SEGNALAZIONE_BE],
            )
            ritirate = cursor.rowcount
            cursor.execute(
                """
                UPDATE vendite.fatturazione_lotti_fatture
                   SET stato_esecuzione = 'COMPLETED'
                 WHERE lotto_id = %s
                   AND stato_esecuzione = 'ERRORE'
                """,
                [int(lotto_id)],
            )
        return ritirate

    # Scopo: Prepara e restituisce il dataset SDI del lotto mappato in oggetti tipizzati.
    def run_prepare_sdi_payload_lotto_task(
        self,
        *,
        lotto_id: int,
        stato_sdi_codice_interno: str = "DA_INVIARE",
        force_new_tentativo: bool = False,
    ) -> list[SdiPayloadRow]:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT *
                FROM vendite.fn_prepare_sdi_payload(%s, %s, %s)
                """,
                [lotto_id, stato_sdi_codice_interno, force_new_tentativo],
            )
            rows = cursor.fetchall()
        # Il payload viene preparato lato DB e qui reso disponibile all'applicazione.
        return [
            SdiPayloadRow(
                fattura_sdi_id=int(row[0]),
                fattura_id=int(row[1]),
                tentativo_num=int(row[2]),
                stato_sdi_id=int(row[3]),
                codice_documento=row[4],
                numero_fattura=None if row[5] is None else int(row[5]),
                data_fattura=row[6],
                billing_account_id=int(row[7]),
                emittente_soggetto_ruolo_id=int(row[8]),
                valuta_id=None if row[9] is None else int(row[9]),
                totale_a_pagare=row[10],
            )
            for row in rows
        ]

    # Scopo: Gestisce `numera_fattura_opz_emessa` nel flusso applicativo del modulo.
    def numera_fattura_opz_emessa(self, fattura_id: int) -> None:
        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT vendite.fn_numera_fattura_opz_emessa(%s)",
                [fattura_id],
            )

    # Scopo: Proietta il legame documentale di UNA fattura via
    #        `vendite.fn_popola_fatture_rettifiche`: da cio' che le righe gia'
    #        dicono (`fatture_righe.riga_rettificata_id`, scritto dal generatore
    #        righe) alla coppia documento-a-documento `vendite.fatture_rettifiche`,
    #        che serve al blocco `DatiFattureCollegate` di una TD04.
    #        Ritorna quante coppie ha aggiunto.
    # ⭐ Idempotente (`ON CONFLICT DO NOTHING`) e non cancella mai: rieseguirla su
    #    un documento gia' proiettato non ha effetti. E' la proprieta' su cui si
    #    appoggia il RESUME del task — senza, un rilancio raddoppierebbe.
    def popola_fatture_rettifiche(self, fattura_id: int) -> int:
        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT vendite.fn_popola_fatture_rettifiche(%s)",
                [int(fattura_id)],
            )
            row = cursor.fetchone()
        assert row is not None
        return int(row[0])

    # Scopo: Accoda in vendite.fatture_stampa_coda una riga PENDING per ogni
    #        fattura del lotto (outbox stampa, Fase C C-2c).
    #        Idempotente (indice unico parziale sui work-item vivi).
    #        Ritorna il numero di righe accodate.
    def accoda_stampe_lotto(self, lotto_id: int) -> int:
        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT vendite.fn_accoda_stampe_lotto(%s)",
                [lotto_id],
            )
            row = cursor.fetchone()
        assert row is not None
        return int(row[0])

    # ══════════════════════════════════════════════════════════
    #  CODA STAMPA — drenaggio worker (outbox, Fase C C-2b/C-2d)
    #  `accoda_stampe_lotto` (sopra) POPOLA la coda; questi metodi la
    #  DRENANO. Owner unico del vocabolario stati coda (costanti sotto,
    #  CHECK chk_fatture_stampa_coda_stato).
    #  ⚠️ La tabella NON ha trigger audit (verificato sul DDL G1): ogni
    #  UPDATE di stato setta data_update/user_update ESPLICITAMENTE —
    #  data_update è anche il claimed_at su cui ragiona il reaper.
    # ══════════════════════════════════════════════════════════

    # Stati della coda stampa (CHECK chk_fatture_stampa_coda_stato). Unica
    # fonte dei letterali: il service drainer importa da qui, mai stringhe
    # inline cross-file.
    STAMPA_STATO_PENDING = "PENDING"
    STAMPA_STATO_IN_CORSO = "IN_CORSO"
    STAMPA_STATO_FATTO = "FATTO"
    STAMPA_STATO_ERRORE = "ERRORE"

    # Scopo: Reaper delle righe rimaste IN_CORSO oltre `stale_minuti` (worker
    #        morto a metà render). `data_update` di una riga IN_CORSO == istante
    #        del claim (settato esplicitamente dal claim, nessun trigger audit
    #        sulla tabella), quindi funge da claimed_at. Soglia larga (≫ tempo
    #        di un render) → nessun doppio-render su un worker semplicemente
    #        lento. Ogni recupero INCREMENTA `tentativi` (il render interrotto È
    #        un tentativo consumato): una riga il cui render uccide il worker —
    #        e che quindi non passa mai da `marca_stampa_errore` — non può
    #        ciclare all'infinito: oltre `soglia_tentativi` → ERRORE terminale
    #        (con `ultimo_errore` parlante), altrimenti → PENDING. Ritorna il
    #        numero di righe recuperate (entrambi i rami).
    def reset_stale_stampe_in_corso(
        self, stale_minuti: int, *, soglia_tentativi: int,
    ) -> int:
        errore_json = json.dumps({
            "code": "E_STAMPA_JOB_STANTIO",
            "message": (
                "Render interrotto (worker morto o kill): "
                "recuperato dal reaper."
            ),
        })
        with connection.cursor() as cursor:
            cursor.execute(
                """
                UPDATE vendite.fatture_stampa_coda
                   SET tentativi = tentativi + 1,
                       ultimo_errore = %s::jsonb,
                       stato = CASE
                                 WHEN tentativi + 1 >= %s THEN %s
                                 ELSE %s
                               END,
                       data_update = now(),
                       user_update = CURRENT_USER
                 WHERE stato = %s
                   AND data_update < now() - make_interval(mins => %s)
                """,
                [
                    errore_json,
                    int(soglia_tentativi),
                    self.STAMPA_STATO_ERRORE,
                    self.STAMPA_STATO_PENDING,
                    self.STAMPA_STATO_IN_CORSO,
                    int(stale_minuti),
                ],
            )
            return cursor.rowcount

    # Scopo: Claim atomico di un batch di work-item PENDING per il worker
    #        drainer. `FOR UPDATE SKIP LOCKED` → più worker in parallelo non si
    #        pestano (ognuno prende righe diverse); il flip a IN_CORSO nella
    #        stessa istruzione le sottrae ai claim successivi (e al
    #        ri-accodamento, uq_fatture_stampa_coda_vivo). `data_update = now()`
    #        = claimed_at per il reaper (la tabella non ha trigger audit).
    #        Ordine per id (indice parziale ix_fatture_stampa_coda_da_lavorare).
    #        Il render avviene FUORI da qui: la connessione non tiene il lock
    #        durante l'I/O (I-4b). Ritorna i work-item claimati (lista dict).
    def claim_stampe_pending(self, limit: int) -> list[dict[str, Any]]:
        safe_limit = max(1, int(limit))
        sql = """
            WITH claimed AS (
                SELECT id
                  FROM vendite.fatture_stampa_coda
                 WHERE stato = %s
                 ORDER BY id
                 FOR UPDATE SKIP LOCKED
                 LIMIT %s
            )
            UPDATE vendite.fatture_stampa_coda c
               SET stato = %s,
                   data_update = now(),
                   user_update = CURRENT_USER
              FROM claimed
             WHERE c.id = claimed.id
            RETURNING c.id, c.sorgente_tipo_id, c.sorgente_id, c.sorgente_uid,
                      c.lotto_id, c.template_documento_id, c.tentativi
        """
        with connection.cursor() as cursor:
            cursor.execute(sql, [
                self.STAMPA_STATO_PENDING, safe_limit, self.STAMPA_STATO_IN_CORSO,
            ])
            return rows_to_list(cursor)

    # Scopo: C-2d — backstop numerazione: garantisce che la fattura sia
    #        numerata PRIMA del render (rende impossibile un PDF non numerato,
    #        D-1 al livello più forte). Delega a `fn_numera_fattura_opz_emessa`,
    #        già idempotente (fattura già numerata → no-op che ritorna i valori
    #        correnti). Vive nel worker, NON in DocumentGenerationService (che
    #        resta generico e stupido, I-4).
    def numera_fattura_backstop(self, fattura_id: int) -> None:
        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT * FROM vendite.fn_numera_fattura_opz_emessa(%s)",
                [int(fattura_id)],
            )
            cursor.fetchall()  # drena il result set TABLE (invocazione)

    # Scopo: Marca una riga di coda come completata (FATTO) col documento
    #        prodotto; azzera `ultimo_errore` (esito pulito dopo eventuali
    #        tentativi precedenti falliti). data_update esplicito (no trigger).
    def marca_stampa_fatto(self, coda_id: int, documento_id: int) -> None:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                UPDATE vendite.fatture_stampa_coda
                   SET stato = %s,
                       documento_id = %s,
                       ultimo_errore = NULL,
                       data_update = now(),
                       user_update = CURRENT_USER
                 WHERE id = %s
                """,
                [self.STAMPA_STATO_FATTO, int(documento_id), int(coda_id)],
            )

    # Scopo: Registra il fallimento del render di una riga: incrementa
    #        `tentativi`, salva `ultimo_errore` (jsonb, `default=str` per non
    #        far mai fallire la registrazione dell'errore su detail esotici) e
    #        decide lo stato risultante — `ERRORE` (terminale) raggiunta la
    #        soglia, altrimenti `PENDING` (riprovabile al PROSSIMO giro del
    #        worker, non nello stesso). data_update esplicito (no trigger).
    #        Ritorna lo stato risultante ('ERRORE'|'PENDING').
    def marca_stampa_errore(
        self, coda_id: int, *, errore: dict[str, Any], soglia_tentativi: int,
    ) -> str:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                UPDATE vendite.fatture_stampa_coda
                   SET tentativi = tentativi + 1,
                       ultimo_errore = %s::jsonb,
                       stato = CASE
                                 WHEN tentativi + 1 >= %s THEN %s
                                 ELSE %s
                               END,
                       data_update = now(),
                       user_update = CURRENT_USER
                 WHERE id = %s
                RETURNING stato
                """,
                [
                    json.dumps(errore, default=str),
                    int(soglia_tentativi),
                    self.STAMPA_STATO_ERRORE,
                    self.STAMPA_STATO_PENDING,
                    int(coda_id),
                ],
            )
            row = cursor.fetchone()
            assert row is not None
            return str(row[0])

    # Scopo: Contatori della coda stampa per il monitoraggio (C-5) — conteggi
    #        per stato, opzionalmente ristretti a un lotto o a un mese di
    #        competenza. La coda NON ha colonna emittente (brief §5): per la
    #        lettura OPERATORE lo scope emittente si deriva via **JOIN a
    #        vendite.fatture** su `sorgente_id` + il BB
    #        `add_emittente_scope_condition` (convenzione SR). Con
    #        `auth_user_id=None` (worker/sistema) nessuno scope → conta tutto.
    #        Ritorna dict {stato: n} dei soli stati presenti.
    #
    # `competenza_mese` (2026-07-23): restringe al mese di competenza del LOTTO
    # a cui la riga di coda appartiene (`c.lotto_id` -> `fatturazione_lotti`).
    # Senza, i conteggi sono cumulativi da sempre: «Fatte: 7» cresce all'infinito
    # e non dice nulla su cosa si sta fatturando ora — stesso difetto per cui i
    # contatori dei worker sono stati tolti dal pannello esiti.
    # JOIN interno di proposito: una riga senza lotto non è attribuibile a un
    # mese e non deve entrare in un conteggio di periodo.
    def count_coda_stampa_per_stato(
        self,
        *,
        lotto_id: int | None = None,
        auth_user_id: int | None = None,
        competenza_mese: date | None = None,
    ) -> dict[str, int]:
        conditions: list[str] = []
        params: list[Any] = []
        # Lista e non stringa singola: i join sono più d'uno e si accumulano
        # (assegnarla sovrascriverebbe silenziosamente quello già impostato).
        joins: list[str] = []
        if lotto_id is not None:
            conditions.append("c.lotto_id = %s")
            params.append(int(lotto_id))
        if auth_user_id is not None:
            # La coda è un satellite di fatture: lo scope emittente vive sulla
            # fattura, non sulla coda → JOIN + scope applicativo (defense-in-depth).
            joins.append("JOIN vendite.fatture f ON f.id = c.sorgente_id")
            add_emittente_scope_condition(
                conditions, params,
                auth_user_id=auth_user_id,
                column="f.emittente_soggetto_ruolo_id",
                convention="sr",
            )
        if competenza_mese is not None:
            joins.append(
                "JOIN vendite.fatturazione_lotti l ON l.id = c.lotto_id"
            )
            conditions.append("l.competenza_mese = %s")
            params.append(competenza_mese.replace(day=1))
        where = ("WHERE " + " AND ".join(conditions)) if conditions else ""
        sql = f"""
            SELECT c.stato, COUNT(*)::int
              FROM vendite.fatture_stampa_coda c
              {" ".join(joins)}
              {where}
             GROUP BY c.stato
        """  # noqa: S608 — join/where da condizioni whitelisted (nessun input libero)
        with connection.cursor() as cursor:
            cursor.execute(sql, params)
            return {str(row[0]): int(row[1]) for row in cursor.fetchall()}

    # Scopo: Elenco paginato della coda stampa per la UI di gestione code
    #        (brief-be-fe-gestione-code-lavori-stampa BE-6). JOIN a
    #        vendite.fatture (numero/anno/serie — la coda e` un satellite di
    #        fatture) + emittenti_fiscali (codice, colonna informativa).
    #
    #        Ambito PER-OPERATORE come la coda lavori (2026-07-23, decisione
    #        Tid — la vecchia semantica per-emittente del «miei» si leggeva
    #        come filtro rotto): `operatore` filtra su `c.user_insert`
    #        (l'identita` GUC di chi ha innescato l'accodamento); None = tutte
    #        le righe (vista «Tutti», aperta a ogni operatore).
    #        `caller_username` serve SOLO a calcolare `is_mio` (tag «mio» in
    #        colonna), mai a filtrare — stessa separazione owner/caller della
    #        coda lavori.
    #        Filtri opzionali stati/lotto/intervallo `data_insert` (`data_a`
    #        bound ESCLUSIVO: il chiamante passa gia` il giorno+1).
    #        Ordinamento (2026-07-23, richiesta Tid): `sort_by`/`sort_dir` da
    #        whitelist `CODA_STAMPA_SORT_SQL` — il service valida, qui assert
    #        di defense-in-depth. Default `data_update DESC` («aggiornato»: la
    #        riga lavorata piu` di recente in testa); tiebreaker `c.id DESC`
    #        per un ordine stabile. E` una lista di monitoraggio, non la corsia
    #        del worker. Ritorna `{items, total}` via BB
    #        `fetch_paged_with_total` (fallback pagina-stantia: la coda si
    #        auto-svuota sotto l'utente a ogni drain).
    def elenca_coda_stampa(
        self,
        *,
        operatore: str | None = None,
        caller_username: str | None = None,
        stati: list[str] | None = None,
        lotto_id: int | None = None,
        data_da: Any = None,
        data_a: Any = None,
        limit: int = 50,
        offset: int = 0,
        sort_by: str = "data_update",
        sort_dir: str = "DESC",
    ) -> dict[str, Any]:
        conditions: list[str] = []
        params: list[Any] = []
        if stati:
            conditions.append("c.stato = ANY(%s)")
            params.append(list(stati))
        if lotto_id is not None:
            conditions.append("c.lotto_id = %s")
            params.append(int(lotto_id))
        if data_da is not None:
            conditions.append("c.data_insert >= %s")
            params.append(data_da)
        if data_a is not None:
            conditions.append("c.data_insert < %s")
            params.append(data_a)
        if operatore is not None:
            conditions.append("c.user_insert = %s")
            params.append(str(operatore))
        where = ("WHERE " + " AND ".join(conditions)) if conditions else ""
        safe_limit = max(1, min(int(limit), LIST_MAX_LIMIT))
        safe_offset = max(0, int(offset))
        sort_expr = CODA_STAMPA_SORT_SQL.get(sort_by)
        assert sort_expr is not None, f"sort_by non in whitelist: {sort_by!r}"
        assert sort_dir in ("ASC", "DESC"), f"sort_dir non valido: {sort_dir!r}"
        order_by = (
            sort_expr.format(dir=sort_dir)
            if "{dir}" in sort_expr
            else f"{sort_expr} {sort_dir}"
        )
        from_join = """
              FROM vendite.fatture_stampa_coda c
              JOIN vendite.fatture f ON f.id = c.sorgente_id
              LEFT JOIN anagrafiche.emittenti_fiscali ef
                ON ef.soggetto_ruolo_id = f.emittente_soggetto_ruolo_id
        """
        data_sql = f"""
            SELECT c.id, c.sorgente_id AS fattura_id,
                   f.numero AS fattura_numero, f.anno AS fattura_anno,
                   f.serie AS fattura_serie,
                   ef.codice AS emittente_codice,
                   c.lotto_id, c.stato, c.tentativi, c.ultimo_errore,
                   c.documento_id, c.data_insert, c.data_update,
                   c.user_insert AS operatore,
                   (c.user_insert = %s) AS is_mio,
                   COUNT(*) OVER() AS total_count
              {from_join}
              {where}
             ORDER BY {order_by}, c.id DESC
             LIMIT %s OFFSET %s
        """  # noqa: S608 — where/order da whitelist chiuse (nessun input libero)
        rows, total = fetch_paged_with_total(
            data_sql,
            # `caller_username` per primo: è il parametro dell'is_mio nella
            # SELECT, che precede il WHERE. '' quando None: non matcha nessun
            # user reale → is_mio False, mai NULL.
            [caller_username or "", *params, safe_limit, safe_offset],
            fallback_count_sql=(
                f"SELECT COUNT(*) {from_join} {where}"  # noqa: S608
            ),
            fallback_params=list(params),
            offset=safe_offset,
        )
        items = [
            {
                "id": int(r["id"]),
                "fattura_id": int(r["fattura_id"]),
                "fattura_numero": r["fattura_numero"],
                "fattura_anno": r["fattura_anno"],
                "fattura_serie": r["fattura_serie"],
                "emittente_codice": r["emittente_codice"],
                "lotto_id": None if r["lotto_id"] is None else int(r["lotto_id"]),
                "stato": str(r["stato"]),
                "tentativi": int(r["tentativi"]),
                "ultimo_errore": jsonb_out(r["ultimo_errore"]),
                "documento_id": (
                    None if r["documento_id"] is None else int(r["documento_id"])
                ),
                "data_insert": iso_or_none(r["data_insert"]),
                "data_update": iso_or_none(r["data_update"]),
                # Operatore che ha innescato l'accodamento: l'audit trigger
                # scrive in `user_insert` l'identità dalla GUC (es. 'tid'),
                # mentre `user_update` è il worker che ha stampato — per la
                # colonna «Operatore» conta chi ha lanciato il processo.
                # («operatore» e non «utente»: nel dominio utente è ambiguo,
                # può indicare il cliente/utenza — glossario di progetto.)
                "operatore": r["operatore"],
                "is_mio": bool(r["is_mio"]),
            }
            for r in rows
        ]
        return {"items": items, "total": int(total)}

    # Scopo: Gestisce `sync_lotto_fatture_stato` nel flusso applicativo del modulo.
    def sync_lotto_fatture_stato(
        self,
        *,
        lotto_id: int,
        stato_doc_fiscale_id: int | None = None,
    ) -> None:
        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT vendite.fn_sync_lotto_fatture_stato(%s, %s)",
                [lotto_id, stato_doc_fiscale_id],
            )

    # Scopo: Recupera `or_create_fattura_header` dal contesto applicativo o dal database.
    def get_or_create_fattura_header(self, lotto_id: int, attivita_id: int) -> int:
        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT vendite.fn_get_or_create_fattura_header(%s, %s)",
                [lotto_id, attivita_id],
            )
            row = cursor.fetchone()
            assert row is not None
        return int(row[0])

    # Scopo: Risolve o crea le testate fattura per un batch di attivita in un solo round-trip.
    # La funzione DB fn_get_or_create_fattura_header viene chiamata N volte server-side
    # ma in un singolo viaggio client-server.
    def batch_get_or_create_fattura_headers(
        self, lotto_id: int, attivita_ids: list[int]
    ) -> dict[int, int]:
        if not attivita_ids:
            return {}
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT
                    t.id AS attivita_id,
                    vendite.fn_get_or_create_fattura_header(%s, t.id) AS fattura_id
                FROM unnest(%s::int[]) AS t(id)
                """,
                [lotto_id, attivita_ids],
            )
            rows = cursor.fetchall()
        return {int(row[0]): int(row[1]) for row in rows}

    # Scopo: Gestisce `build_fattura_key` nel flusso applicativo del modulo.
    def build_fattura_key(self, attivita_id: int) -> dict[str, object]:
        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT vendite.fn_build_fattura_key(%s)",
                [attivita_id],
            )
            row = cursor.fetchone()
            assert row is not None
        return row[0]

    # Scopo: ANNULLA un lotto che si trova in DRAFT: porta il lotto ad
    #        ANNULLATA/CHIUSO, elimina le sue fatture pre-fiscali (non
    #        numerate) e libera le attivita'. Non «riporta a bozza»: il nome
    #        vecchio (`reset_lotto_draft`) diceva il contrario di cio' che fa,
    #        ed e' la ragione di D-L. ⚠️ Il `task_code` di pipeline resta
    #        `reset_lotto_draft` (seed CSV, immutabile) e cosi' il
    #        `post_permission`: qui cambia solo il nome della funzione.
    def annulla_lotto_da_draft(self, lotto_id: int) -> AnnullaLottoDaDraftResult:
        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT updated_lotti, updated_attivita, deleted_fatture, deleted_righe "
                "FROM vendite.fn_annulla_lotto_da_draft(%s)",
                [lotto_id],
            )
            row = cursor.fetchone()
            assert row is not None
        return {
            "updated_lotti": int(row[0]),
            "updated_attivita": int(row[1]),
            "deleted_fatture": int(row[2]),
            "deleted_righe": int(row[3]),
        }

    # Scopo: RIPORTA A BOZZA un lotto gia' lavorato perche' si possa correggere
    #        a monte e rifare il giro (Fase 6, brief DB→BE ritorno-lotto-a-draft).
    #        E' un ROLLBACK, non una riapertura: le fatture si CANCELLANO e il
    #        rilancio le rigenera. Distinto da `annulla_lotto_da_draft`, che
    #        invece chiude il lotto (ANNULLATA) e non lo rimette in gioco.
    # Perimetro (guard nella fn): lotti MASSIVO o GIORNALIERO in DRAFT o EMESSA.
    #        ⚠️ Rifiuta se anche UNA sola fattura ha gia' un numero — guarda il
    #        numero, non lo stato: un numero fiscale assegnato non si ritira.
    # Effetto laterale che conta: riporta `commesse_attivita.stato_emissione` a
    #        NON_EMESSA. Senza, il lotto ripartirebbe senza NIENTE da emettere
    #        (la selezione scarta le gia' emesse) e il cruscotto competenza
    #        continuerebbe a contarle come fatturate.
    def riporta_lotto_a_draft(self, lotto_id: int) -> RiportaLottoADraftResult:
        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT updated_lotti, updated_attivita, deleted_fatture, "
                "       deleted_righe, riemesse_attivita, annullati_task_run "
                "FROM vendite.fn_riporta_lotto_a_draft(%s)",
                [lotto_id],
            )
            row = cursor.fetchone()
            assert row is not None
        return {
            "updated_lotti": int(row[0]),
            "updated_attivita": int(row[1]),
            "deleted_fatture": int(row[2]),
            "deleted_righe": int(row[3]),
            "riemesse_attivita": int(row[4]),
            "annullati_task_run": int(row[5]),
        }

    # Scopo: Il lotto e' stato riportato a bozza e non ha ancora rifatto il giro?
    #        E' il TERZO motivo per rifare lo step corrente invece di avanzare
    #        (gli altri due: rerun in errore, primo run). Deliberatamente una
    #        DATA e non un booleano: si spiega da sola e si ordina.
    # ⚠️ Nessun vincolo sul `tipo_lotto`, a differenza di `is_lotto_in_errore`
    #        che vale solo per i MASSIVO: la fn di ritorno a bozza ammette anche
    #        i GIORNALIERO, e un giornaliero riaperto deve rifare lo step come
    #        gli altri.
    def is_lotto_riaperto(self, lotto_id: int) -> bool:
        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT (riaperto_il IS NOT NULL) FROM vendite.fatturazione_lotti"
                " WHERE id = %s",
                [lotto_id],
            )
            row = cursor.fetchone()
        return bool(row[0]) if row else False

    # Scopo: Spegne il segnale di riapertura dopo che il giro l'ha onorato.
    #        Senza, il lotto rifarebbe lo stesso step all'infinito (§3 del brief).
    #        Idempotente: un secondo azzeramento non fa nulla.
    def azzera_riaperto_il(self, lotto_id: int) -> None:
        with connection.cursor() as cursor:
            cursor.execute(
                "UPDATE vendite.fatturazione_lotti SET riaperto_il = NULL"
                " WHERE id = %s AND riaperto_il IS NOT NULL",
                [lotto_id],
            )

    # Scopo: Elimina UNA fattura dal lotto, liberandone le attivita'. ⚠️ Passa
    #        `NULL` come `lock_batch_id` alla primitiva di cleanup: passare
    #        quello del lotto libererebbe l'INTERO batch invece della sola
    #        fattura (C-22/D-L.3, misurato dal team DB: 15 attivita' liberate
    #        contro 0).
    #        Rinominata il 2026-08-04 insieme alla funzione SQL (slice 6-B): il
    #        «draft» era riferito al LOTTO, che ora basta sia pre-fiscale
    #        (DRAFT o EMESSA) — lo stesso confine delle due sorelle. Il nome
    #        vecchio aveva smesso di dire la verita'.
    def elimina_fattura_da_lotto(
        self,
        lotto_id: int,
        fattura_id: int,
    ) -> EliminaFatturaDaLottoResult:
        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT updated_attivita, deleted_fatture, deleted_righe, riemesse_attivita "
                "FROM vendite.fn_elimina_fattura_da_lotto(%s, %s)",
                [lotto_id, fattura_id],
            )
            row = cursor.fetchone()
            assert row is not None
        return {
            "updated_attivita": int(row[0]),
            "deleted_fatture": int(row[1]),
            "deleted_righe": int(row[2]),
            "riemesse_attivita": int(row[3]),
        }

    # Scopo: Recupera `next_fattura_riga_nr` dal contesto applicativo o dal database.
    def get_next_fattura_riga_nr(self, fattura_id: int) -> int:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT COALESCE(MAX(riga_nr), 0) + 1
                FROM vendite.fatture_righe
                WHERE fattura_id = %s
                """,
                [fattura_id],
            )
            row = cursor.fetchone()
            assert row is not None
        return int(row[0])

    # Scopo: Restituisce MAX(riga_nr) corrente per ogni fattura_id in un singolo round-trip.
    # Usato dal batch per calcolare i riga_nr in Python senza N query singole.
    def get_max_riga_nrs(self, fattura_ids: list[int]) -> dict[int, int]:
        if not fattura_ids:
            return {}
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT fattura_id, COALESCE(MAX(riga_nr), 0)
                FROM vendite.fatture_righe
                WHERE fattura_id = ANY(%s)
                GROUP BY fattura_id
                """,
                [fattura_ids],
            )
            rows = cursor.fetchall()
        return {int(row[0]): int(row[1]) for row in rows}

    # Scopo: Gestisce `insert_fattura_riga` nel flusso applicativo del modulo.
    def insert_fattura_riga(
        self,
        *,
        fattura_id: int,
        riga_nr: int,
        articolo_id: int,
        descrizione: str | None,
        uom_id: int | None,
        qta: Decimal | None,
        prezzo_unitario: Decimal | None,
        iva_id: int | None,
        dest_billing_account_id: int,
        sorgente_tipo_id: int | None,
        sorgente_uid: str | None,
        sorgente_riga: int | None,
        meta: LottoPipelineMeta | None,
    ) -> int:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                INSERT INTO vendite.fatture_righe (
                    fattura_id,
                    riga_nr,
                    articolo_id,
                    descrizione,
                    uom_id,
                    qta,
                    prezzo_unitario,
                    iva_id,
                    dest_billing_account_id,
                    sorgente_tipo_id,
                    sorgente_uid,
                    sorgente_riga,
                    meta
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s::jsonb)
                RETURNING id
                """,
                [
                    fattura_id,
                    riga_nr,
                    articolo_id,
                    descrizione,
                    uom_id,
                    qta,
                    prezzo_unitario,
                    iva_id,
                    dest_billing_account_id,
                    sorgente_tipo_id,
                    sorgente_uid,
                    sorgente_riga,
                    self._to_jsonb_param(meta),
                ],
            )
            row = cursor.fetchone()
            assert row is not None
        return int(row[0])

    # Scopo: Gestisce `mark_attivita_fatturata` nel flusso applicativo del modulo.
    def mark_attivita_fatturata(self, attivita_id: int, fattura_riga_id: int) -> None:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                UPDATE vendite.attivita_fatturabili
                SET fattura_riga_id = %s,
                    fatturato = TRUE,
                    data_update = now(),
                    user_update = current_user
                WHERE id = %s
                """,
                [fattura_riga_id, attivita_id],
            )

    # Scopo: Marca come RUNNING le attivita' lockate sul lotto, prima della
    #        generazione righe. Chiude il passo centrale del ciclo di vita
    #        `stato_esecuzione` (select -> PENDING, generazione -> RUNNING ->
    #        COMPLETED, reset -> NULL), che fino al 2026-07-28 non avveniva mai
    #        sul percorso Python: tutte le attivita' fatturate restavano PENDING.
    def mark_attivita_running(self, lotto_id: int) -> int:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                UPDATE vendite.attivita_fatturabili a
                   SET stato_esecuzione = 'RUNNING',
                       data_update = now(),
                       user_update = current_user
                 WHERE a.lock_batch_id = (
                           SELECT fl.lock_batch_id
                           FROM vendite.fatturazione_lotti fl
                           WHERE fl.id = %s
                       )
                   AND a.fatturato IS FALSE
                   AND COALESCE(a.lock_in_fatturazione, false) IS TRUE
                   AND (a.stato_esecuzione IS NULL
                        OR a.stato_esecuzione IN ('PENDING', 'RUNNING'))
                """,
                [lotto_id],
            )
            return cursor.rowcount

    # Scopo: Inserisce in un solo round-trip le righe fattura AGGREGATE e collega
    #        a ciascuna le *n* attivita' che l'hanno prodotta, marcandole
    #        fatturate e COMPLETED.
    #        Perimetro e risultato atteso: gli array `righe_*` descrivono UNA
    #        riga di fattura ciascuno (gia' aggregata dal servizio); gli array
    #        `att_*` descrivono UNA attivita' ciascuno e portano le coordinate
    #        (fattura_id, riga_nr) della riga di destinazione. La correlazione
    #        e' quindi *n*->1 e non piu' 1:1 come prima del 2026-07-28
    #        (brief-fix-importi-riga-fattura-zero §4.6, requisito D4).
    #        `imponibile_riga` NON viene passato: lo calcola il trigger
    #        `a20_importo`, e un valore esterno verrebbe comunque sovrascritto.
    #        `kit_descrizione_padre` e' risolta qui con una sottoquery per
    #        congelarla senza un round-trip aggiuntivo.
    def batch_insert_righe_and_mark(
        self,
        *,
        righe_fattura_ids: list[int],
        righe_nrs: list[int],
        righe_articolo_ids: list[str],  # uuid — cast ::uuid[] nell'unnest
        righe_descrizioni: list[str | None],
        righe_uom_ids: list[int | None],
        righe_qtas: list[Decimal | None],
        righe_prezzi_unitari: list[Decimal | None],
        righe_iva_ids: list[int | None],
        righe_dest_billing_account_ids: list[int],
        righe_kit_keys: list[str | None],
        righe_kit_esposti: list[bool | None],
        righe_kit_articolo_padre_ids: list[str | None],  # uuid
        righe_sconti: list[Decimal | None],
        righe_rettificate: list[int | None],
        righe_metas: list[str | None],
        att_ids: list[int],
        att_fattura_ids: list[int],
        att_riga_nrs: list[int],
    ) -> int:
        if not att_ids:
            return 0

        # ⚠️ `unnest(a, b, c)` con array di lunghezze diverse NON solleva: riempie
        # di NULL i piu' corti. Un disallineamento fra questi array produrrebbe
        # quindi righe di fattura silenziosamente sbagliate — non un errore.
        # Verificato su PG 18: `unnest(ARRAY[1,2,3], ARRAY[10,20])` -> 3 righe.
        righe = {
            "fattura_ids": righe_fattura_ids, "nrs": righe_nrs,
            "articolo_ids": righe_articolo_ids, "descrizioni": righe_descrizioni,
            "uom_ids": righe_uom_ids, "qtas": righe_qtas,
            "prezzi": righe_prezzi_unitari, "iva_ids": righe_iva_ids,
            "dest_ba_ids": righe_dest_billing_account_ids,
            "kit_keys": righe_kit_keys, "kit_esposti": righe_kit_esposti,
            "kit_padri": righe_kit_articolo_padre_ids, "metas": righe_metas,
            # Le due colonne della rettifica entrano nel guard come tutte le
            # altre: sono esattamente il tipo di array che si dimentica di
            # allineare, ed `unnest` non lo direbbe.
            "sconti": righe_sconti, "rettificate": righe_rettificate,
        }
        att = {
            "att_ids": att_ids, "att_fattura_ids": att_fattura_ids,
            "att_riga_nrs": att_riga_nrs,
        }
        for gruppo, atteso in ((righe, len(righe_nrs)), (att, len(att_ids))):
            disallineati = {k: len(v) for k, v in gruppo.items() if len(v) != atteso}
            ErrorManager.require(
                not disallineati,
                code="E_BATCH_ARRAY_DISALLINEATI",
                message="Array batch di lunghezza incoerente.",
                detail=f"attesa={atteso} disallineati={disallineati}",
                context={"attesa": atteso, "disallineati": disallineati},
                function_name="vendite.pipeline_repository.batch_insert_righe_and_mark",
                log_to_db=True,
            )

        with connection.cursor() as cursor:
            cursor.execute(
                """
                WITH righe_input AS (
                    -- ⚠️ Ogni cast dichiara il tipo della COLONNA di
                    -- destinazione, non «un intero qualsiasi»: `fattura_id`,
                    -- `uom_id` e `dest_billing_account_id` sono bigint, e un
                    -- `int[]` li avrebbe fatti fallire con «integer out of
                    -- range» il giorno in cui una sequenza supera 2.1 miliardi.
                    -- La distanza e' enorme (gli id di oggi sono decine di
                    -- migliaia) e non e' un difetto in esercizio — ma il cast
                    -- giusto costa lo stesso di quello sbagliato, e questo
                    -- documenta la colonna invece di indovinarla.
                    -- `riga_nr` e `iva_id` restano `int[]`: lo sono davvero.
                    SELECT *
                    FROM unnest(
                        %s::bigint[],
                        %s::int[],
                        %s::uuid[],
                        %s::text[],
                        %s::bigint[],
                        %s::numeric[],
                        %s::numeric[],
                        %s::int[],
                        %s::bigint[],
                        %s::text[],
                        %s::boolean[],
                        %s::uuid[],
                        %s::numeric[],
                        %s::bigint[],
                        %s::jsonb[]
                    ) AS t(
                        fattura_id, riga_nr, articolo_id, descrizione,
                        uom_id, qta, prezzo_unitario, iva_id,
                        dest_billing_account_id,
                        kit_key, kit_esposto_in_fattura, kit_articolo_padre_id,
                        sconto_percentuale, riga_rettificata_id,
                        meta
                    )
                ),
                inserted AS (
                    INSERT INTO vendite.fatture_righe (
                        fattura_id, riga_nr, articolo_id, descrizione,
                        uom_id, qta, prezzo_unitario, iva_id,
                        dest_billing_account_id,
                        sorgente_tipo_id, sorgente_uid, sorgente_riga,
                        kit_key, kit_esposto_in_fattura,
                        kit_articolo_padre_id, kit_descrizione_padre,
                        sconto_percentuale, riga_rettificata_id,
                        meta
                    )
                    SELECT
                        d.fattura_id, d.riga_nr, d.articolo_id, d.descrizione,
                        d.uom_id, d.qta, d.prezzo_unitario, d.iva_id,
                        d.dest_billing_account_id,
                        -- La riga aggrega n attivita' con n sorgenti: nessuna
                        -- singola da dichiarare. La tracciabilita' passa dal
                        -- puntatore attivita_fatturabili.fattura_riga_id (D4).
                        NULL, NULL, NULL,
                        d.kit_key, d.kit_esposto_in_fattura,
                        d.kit_articolo_padre_id,
                        CASE WHEN d.kit_articolo_padre_id IS NULL THEN NULL
                             ELSE (SELECT art.descrizione
                                     FROM catalogo.articoli art
                                    WHERE art.id = d.kit_articolo_padre_id)
                        END,
                        -- ⚠️ COALESCE e non il valore nudo: `sconto_percentuale`
                        -- ha DEFAULT 0 a DB, e finora la colonna non era
                        -- NOMINATA nella INSERT — quindi il default si
                        -- applicava. Nominarla passando NULL la porterebbe a
                        -- NULL su OGNI riga di fattura: un cambio silenzioso di
                        -- comportamento su tutto lo storico futuro, per una
                        -- colonna che serve alle sole note di credito.
                        COALESCE(d.sconto_percentuale, 0),
                        -- La riga di fattura gemella (§12.6-bis). NULL fuori
                        -- dalla rettifica, ed e' la stragrande maggioranza.
                        d.riga_rettificata_id,
                        d.meta
                    FROM righe_input d
                    RETURNING id, fattura_id, riga_nr
                ),
                att_input AS (
                    -- Come sopra: `attivita_fatturabili.id` e `fattura_id` sono
                    -- bigint, `riga_nr` e' integer.
                    SELECT *
                    FROM unnest(%s::bigint[], %s::bigint[], %s::int[])
                      AS t(attivita_id, fattura_id, riga_nr)
                ),
                correlated AS (
                    SELECT i.id AS fattura_riga_id, a.attivita_id
                    FROM inserted i
                    JOIN att_input a
                      ON a.fattura_id = i.fattura_id AND a.riga_nr = i.riga_nr
                )
                UPDATE vendite.attivita_fatturabili a
                SET fattura_riga_id = c.fattura_riga_id,
                    fatturato = TRUE,
                    stato_esecuzione = 'COMPLETED',
                    data_update = now(),
                    user_update = current_user
                FROM correlated c
                WHERE a.id = c.attivita_id
                """,
                [
                    righe_fattura_ids,
                    righe_nrs,
                    righe_articolo_ids,
                    righe_descrizioni,
                    righe_uom_ids,
                    righe_qtas,
                    righe_prezzi_unitari,
                    righe_iva_ids,
                    righe_dest_billing_account_ids,
                    righe_kit_keys,
                    righe_kit_esposti,
                    righe_kit_articolo_padre_ids,
                    # ⚠️ L'ordine di questa lista È il contratto con l'`unnest`:
                    # le due nuove vanno PRIMA di `righe_metas`, come nella
                    # clausola. Invertirle non solleverebbe — produrrebbe righe
                    # con lo sconto al posto del puntatore.
                    righe_sconti,
                    righe_rettificate,
                    righe_metas,
                    att_ids,
                    att_fattura_ids,
                    att_riga_nrs,
                ],
            )
            return cursor.rowcount
