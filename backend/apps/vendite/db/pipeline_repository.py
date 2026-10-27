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
from collections.abc import Mapping
from typing import Any, cast

from django.db import connection, transaction

from apps.core.api.constants import DEFAULT_LIMIT, DEFAULT_LIMIT_EVENTI, MAX_LIMIT
from apps.core.db._helpers import (
    predicato_giorno_operativo,
    limiti_pagina,
    call_jsonb_fn,
    coerce_jsonb_dict,
    conta_con_perimetro,
    fetch_paged_with_total,
    fetchone_scalar,
    iso_or_none,
    jsonb_out,
    row_to_dict,
    rows_to_list,
    sql_order_clause,
)
from apps.core.db.emittente_scope_helpers import (
    add_emittente_scope_condition,
    add_emittente_scope_condition_risolta,
)
from apps.core.services.error_manager import ErrorManager
from apps.vendite.db._event_log_repo_mixin import EventLogRepositoryMixin
from apps.vendite.db.commesse_repository import (
    TIPO_MOVIMENTO_NORMALE,
)
from apps.core.api.payload_validators import optional_bool
from apps.core.services.value_normalizer import empty_to_none
from apps.vendite.db._data_documento_sql import (
    SQL_DATA_DOCUMENTO_CORRENTE,
    costruisci_perimetro_lotti_numerabili,
)
from apps.vendite.types import (
    AnnullaLottoDaDraftResult,
    EsclusioneDocumentoDaGiroResult,
    EsitoMarcaturaGruppi,
    EsitoDataDocumento,
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
# PAGINA (`LOTTO_LISTE_PAGINA_MAX`) resta quello di sempre: sono due limiti per
# due usi diversi, e confonderli significa o una pagina enorme o un file
# troncato in silenzio.
_DRAWER_EXPORT_MAX_ROWS = 10_000

# Il tetto di PAGINA dei due elenchi del drawer lotto (segnalazioni e task run).
# ⚠️ NON e' `MAX_LIMIT` di core: e' il contratto delle due funzioni DB che li
#    leggono (`fn_list_lotto_segnalazioni`, `fn_list_lotto_task_runs`:
#    `LEAST(GREATEST(p_limit, 1), 500)`), e qui lo si rispecchia per validare
#    prima di chiamarle. Una sede in Python: prima era scritto quattro volte
#    (repository e service), e il presidio della paginazione non lo vedeva.
LOTTO_LISTE_PAGINA_MAX = 500

# Le colonne del riepilogo segnalazioni che NON sono conteggi: oggi il solo
# verdetto `fermo` (`20260919-02`). Il riepilogo si legge per nome e si
# tipizza per chiave, cosi' un booleano non finisce a video come `1`/`0` e il
# ripiego a riga assente risponde `false`, non zero.
_SUMMARY_CHIAVI_BOOL: frozenset[str] = frozenset({"fermo"})


# Scopo: tipizza un valore del riepilogo segnalazioni per chiave — `bool` sul
#        verdetto, `int` sui conteggi; con `None` (riga assente) il neutro del
#        tipo (`False` / 0).
def _valore_summary(chiave: str, valore: Any) -> bool | int:
    if chiave in _SUMMARY_CHIAVI_BOOL:
        return bool(valore)
    return int(valore or 0)


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
    # ⚠️ NOT NULL a DB (`attivita_fatturabili.billing_account_id`,
    #    `.data_attivita`): fino al 2026-10-09 erano dichiarati opzionali, e il
    #    chiamante faceva `int(ba_id)` su un tipo che diceva «puo' mancare».
    dest_billing_account_id: int
    uom_id: int | None
    prezzo_unitario: Decimal | None
    competenza_dal: date | None
    competenza_al: date | None
    data_attivita: date
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
    # Il periodo della riga rettificata: la nota di credito lo copia come
    # copia prezzo e IVA (`fatture_righe.competenza_dal/_al` NOT NULL dal
    # 2026-10-02, brief-db-bom-flag-quantita-e-kit-in-fattura R-BE-B1).
    rett_competenza_dal: date | None = None
    rett_competenza_al: date | None = None
    # ── L'atto ───────────────────────────────────────────────────────────────
    # Il contratto a cui l'attivita' appartiene. `None` su tutto cio' che nasce
    # fuori da un contratto, che oggi e' la maggior parte del traffico.
    contratto_id: int | None = None


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
    # ⭐ Il CODICE dell'articolo, e serve a una cosa sola: ordinare le righe del
    # documento in un modo che una PERSONA sappia leggere. Fino al 2026-08-31 si
    # ordinava per `articolo_id`, che e' un UUID — deterministico per la
    # macchina, rumore per chi guarda la fattura.
    # ⚠️ `codice` e non `codice_interno`, di proposito: per convenzione di
    # progetto il primo e' l'etichetta che l'utente vede e puo' cambiare, il
    # secondo la chiave immutabile. Qui l'ordinamento serve a chi LEGGE, e chi
    # legge vede il `codice`.
    articolo_codice: str | None = None
    # `meta` dell'attivita': porta lo snapshot kit gia' risolto dal push
    # (`segment_key`, `componente_di`, `esposizione`). Nessuna
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
# frontend, valore = espressione SQL qualificata. Direzione, NULLS e tiebreak li
# mette il BB `sql_order_clause` (2026-09-26: prima il segnaposto `{dir}` portava
# un `NULLS LAST` fisso in entrambi i versi e il tiebreak era `c.id DESC` fisso —
# una seconda regola accanto a quella di Tid del 2026-07-19/08-03).
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
    # Nullable: il numero e` NULL finche` la fattura e` in bozza — in DESC il
    # BB lo manda in coda (NULL come valore minimo).
    "fattura_numero": "f.numero",
    "emittente_codice": "ef.codice",
    "operatore": "c.user_insert",
    "stato": "c.stato",
    # ⭐ QUANDO LA STAMPA E' ENTRATA IN CODA, ed e' il default dal 2026-09-07 —
    #    simmetrico alla coda lavori, che lo ha adottato lo stesso giorno.
    #    ⚠️ Prima il default era `c.data_update`, e funzionava per COINCIDENZA:
    #    su una riga mai toccata vale quanto `data_insert`, quindi una riga in
    #    attesa restava in testa. Ma «ultimo tocco» e «immesso» sono due domande
    #    diverse, e un'ordinabilita' che regge finche' nessuno aggiorna la riga
    #    e' una proprieta' dei dati, non del modello.
    "data_insert": "c.data_insert",
    # Nullable: lotto_id e` NULL per le stampe fuori lotto (es. ristampe
    # singole) — in DESC il BB le manda in coda.
    "lotto_id": "c.lotto_id",
    "data_update": "c.data_update",
    # `archiviato_il` (2026-09-04, brief-db-archiviazione-righe-code): a
    # catalogo e` `ordinabile = t`, e seed e whitelist sono confrontati da
    # `test_liste_configurabili_seed` — accenderla la` senza metterla qui
    # sarebbe una colonna che il frontend offre e il backend rifiuta con un
    # 400. Nullable: la data e` NULL su ogni riga NON archiviata.
    "archiviato_il": "c.archiviato_il",
}

# Le colonne DATA della whitelist: senza direzione indicata partono DESC (regola
# Tid 2026-09-02, `colonne_desc` di `sql_order_clause`). Coincidono con le date
# ordinabili del seed — lo verifica `test_liste_configurabili_seed`.
CODA_STAMPA_SORT_COLONNE_DATA: frozenset[str] = frozenset(
    {"data_insert", "data_update", "archiviato_il"}
)


# Proiezione e mapping di `GroupAttivitaInput`, in un posto solo.
#
# 🔴 PERCHE' ESISTE. Le due letture — singola (`get_group_attivita_input`) e
# batch (`batch_get_group_attivita_inputs`) — proiettavano le STESSE colonne
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
                    -- ⛔ `art.iva_id` E' USCITA DA QUI il 2026-08-31 (`I4`), e non
                    --    e' una semplificazione: era la NONA risposta autonoma
                    --    alla domanda «che IVA ha questa riga». L'aliquota
                    --    dell'articolo e' lo stadio A1 del risolutore, che la
                    --    ritorna con `origine = 'ARTICOLO'` — quindi qui non si
                    --    perde niente, e si smette di scavalcare gli stadi B
                    --    (i titoli documentati del cliente) e l'uso della
                    --    fornitura. Leggerla di nuovo qui vorrebbe dire
                    --    applicare l'IVA piena a un esportatore abituale, in
                    --    silenzio.
                    a.competenza_dal,
                    a.competenza_al,
                    a.data_attivita,
                    COALESCE(r.calcolo_qta_padre, 'fissa') AS calcolo_qta_padre,
                    -- ⭐ Decimali e metodo dell'IMPORTO dal BB del DB
                    --    `vendite.fn_parametri_importo_riga` (brief-db-modelli-
                    --    documento-standard §10.9 R-3): la regola dell'articolo,
                    --    se no i parametri effettivi dell'emittente per l'utility
                    --    della fattura — la stessa catena del trigger della riga
                    --    e del ricalcolo dei totali. ⛔ Fino al 2026-10-21 qui
                    --    c'erano i letterali `COALESCE(…, 2)` / `'HALF_UP'`: un
                    --    emittente con parametri suoi raggruppava a 2 decimali e
                    --    il DB arrotondava la riga coi suoi.
                    --    Le QUANTITA' restano qui (3 / HALF_UP): e' la copia unica.
                    pi.arrotondamento_importi_dec,
                    COALESCE(r.arrotondamento_quantita_dec, 3) AS arrotondamento_quantita_dec,
                    pi.metodo_arrotondamento_importi,
                    COALESCE(r.metodo_arrotondamento_quantita, 'HALF_UP')
                        AS metodo_arrotondamento_quantita,
                    a.tipo_movimento,
                    a.fattura_riga_rettificata_id,
                    fr.prezzo_unitario     AS rett_prezzo_unitario,
                    fr.sconto_percentuale  AS rett_sconto_percentuale,
                    fr.iva_id              AS rett_iva_id,
                    -- L'ATTO a cui l'attivita' appartiene. Sta qui e non in un
                    -- JOIN perche' `attivita_fatturabili` lo porta gia' sulla
                    -- riga (FK `fk_attivita_fatturabili_contratto`): risalire
                    -- alla commessa per rileggerlo sarebbe una seconda fonte
                    -- per lo stesso fatto.
                    a.contratto_id,
                    fr.competenza_dal      AS rett_competenza_dal,
                    fr.competenza_al       AS rett_competenza_al
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
                -- Emittente e utility della FATTURA che l'attivita' produrra':
                -- dal resolver che usa la chiave della testata
                -- (`fn_build_fattura_key`), col BA della riga — non ricopiati
                -- qui. Il tipo di documento non serve per questi due anelli
                -- (NULL: il resolver non solleva, lascia il registro vuoto).
                LEFT JOIN LATERAL vendite.fn_resolve_registro_documento(
                    p_billing_account_id_riga => a.billing_account_id,
                    p_tipo_doc_fiscale_id     => NULL
                ) rr ON true
                LEFT JOIN LATERAL vendite.fn_parametri_importo_riga(
                    a.articolo_id, rr.emittente_soggetto_ruolo_id, rr.utility_id
                ) pi ON true
"""


# Scopo: Costruisce un `GroupAttivitaInput` da una riga di `_GROUP_ATTIVITA_SELECT`.
#        Unico mapping: le due letture non possono divergere.
def _group_attivita_input_da_row(row: tuple[Any, ...]) -> GroupAttivitaInput:
    # ⚠️ Decimali e metodo dell'importo NULL = il BB non ha da dove prenderli:
    #    niente regole dell'articolo e nessuna utility risolta (il BA della riga
    #    non visibile sotto RLS). Come il trigger della riga, non si indovina:
    #    E_CONFIG_MANCANTE, invece del `int(None)` che sarebbe un 500 muto.
    ErrorManager.require(
        row[9] is not None and row[11] is not None,
        code="E_CONFIG_MANCANTE",
        message="Parametri di arrotondamento dell'importo non risolti per l'attivita'.",
        detail=f"attivita_id={row[0]} articolo_id={row[1]}",
        context={"attivita_id": row[0]},
        function_name="vendite.pipeline_repository._group_attivita_input_da_row",
    )
    return GroupAttivitaInput(
        attivita_id=int(row[0]),
        # ⚠️ `str`, non `int`: e' un UUID (catalogo.articoli.id).
        articolo_id=str(row[1]),
        dest_billing_account_id=int(row[2]),
        uom_id=None if row[3] is None else int(row[3]),
        prezzo_unitario=row[4],
        competenza_dal=row[5],
        competenza_al=row[6],
        data_attivita=row[7],
        calcolo_qta_padre=row[8],
        arrotondamento_importi_dec=int(row[9]),
        arrotondamento_quantita_dec=int(row[10]),
        metodo_arrotondamento_importi=row[11],
        metodo_arrotondamento_quantita=row[12],
        tipo_movimento=row[13] or TIPO_MOVIMENTO_NORMALE,
        fattura_riga_rettificata_id=None if row[14] is None else int(row[14]),
        rett_prezzo_unitario=row[15],
        rett_sconto_percentuale=row[16],
        rett_iva_id=None if row[17] is None else int(row[17]),
        contratto_id=None if row[18] is None else int(row[18]),
        rett_competenza_dal=row[19],
        rett_competenza_al=row[20],
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
        # `None` = implementazione PYTHON. Il consumo del plafond non e' una
        # sola chiamata SQL: e' un giro che ordina le fatture (`P5`), risolve,
        # chiama `fn_consuma_plafond_titolo_iva_righe` per gruppo (un kit, o
        # una riga sciolta: D-5) e spezza le righe. La madre DB fa la parte che
        # DEVE stare sotto lock; l'ordine e la spezzatura stanno qui.
        "consuma_plafond_lotto": None,
    }

    # Scopo: Gestisce `_to_jsonb_param` nel flusso applicativo del modulo.
    @staticmethod
    def _to_jsonb_param(value: Mapping[str, Any] | None) -> str | None:
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
    # Include fatture_stato_esecuzione_errore_count dalla funzione DB (6° colonna)
    # e, dal 2026-09-12, il decimo numero `esiti_stato_esecuzione_errore_count`
    # (`20260912-16`, D2): i documenti presi in carico il cui ultimo esito e'
    # `ERRORE`, che entra nel verdetto del lotto.
    # ⭐ E dal 2026-09-19 l'UNDICESIMA colonna, `fermo` (`20260919-02`, D-V1 di
    #    Tid: «la regola va a DB»): il VERDETTO del lotto, calcolato in una
    #    sede sola — `vendite.vw_lotti_segnalazioni_summary`, la stessa che
    #    legge il presidio `dbops.vw_lotti_fermi_da_guardare`. Il backend lo
    #    LEGGE (`LottoSegnalazioniService`) e non lo ricalcola dai tre addendi.
    # ⭐ LE CHIAVI VIVONO IN UNA SEDE SOLA: la SELECT. Fino al 2026-09-12 erano
    #    scritte TRE volte — SELECT, ripiego a riga assente, mapping `row[N]` —
    #    e la decima colonna e' entrata in tutte e tre a mano, cioe' nella forma
    #    che il commento della funzione DB dichiara pericolosa («un lettore
    #    posizionale sbagliato non protesta»). Ora i nomi arrivano dal cursore
    #    (`row_to_dict`) e la SELECT e' il contratto: una colonna in piu' o
    #    rinominata si vede nel test del repository, non a video.
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
                    fatture_stato_esecuzione_errore_count,
                    -- ⭐ I TRE NUMERI DEL BANNER (`20260908-33`): contano GESTI,
                    --    non allarmi. I sei qui sopra contano SEGNALAZIONI, e un
                    --    documento con tre critiche resta un documento solo —
                    --    «3 segnalazioni bloccanti» e' un numero vero che
                    --    descrive la cosa sbagliata.
                    -- ⛔ `critiche_giro_count` non e' un di piu': su un lotto
                    --    fermo per un emittente non risolto le altre due
                    --    direbbero «0 documenti su 4», cioe' che non c'e'
                    --    niente da fare mentre il giro e' bloccato.
                    -- ⚠️ Descrivono il solo canale LOTTO, dove vive la
                    --    `gruppo_key`. Gli altri due canali parlano per FATTURA
                    --    e una bozza puo' coprire piu' documenti: NON si
                    --    sommano a questi senza scommettere.
                    -- ⭐ Letti per NOME e non per posizione: la funzione li
                    --    aggiunge in coda proprio perche' un lettore posizionale
                    --    sbagliato non protesta — qui il rischio non si corre.
                    documenti_bloccanti_count,
                    documenti_presi_in_carico_count,
                    critiche_giro_count,
                    -- ⭐ IL DECIMO NUMERO (`20260912-16`, D2): i documenti presi
                    --    in carico il cui ULTIMO esito e' `ERRORE`. A differenza
                    --    dei tre qui sopra, questo ENTRA nel verdetto
                    --    (`LottoSegnalazioniService.is_error`): un lotto con un
                    --    documento in ERRORE non e' a posto per sottrazione.
                    --    `ESCLUSO` non conta — e' la via d'uscita.
                    esiti_stato_esecuzione_errore_count,
                    -- ⭐ IL VERDETTO (`20260919-02`, D-V1): `fermo` e' vero
                    --    quando (fatture_critical + lotto_critical) > 0, o
                    --    fatture_stato_esecuzione_errore > 0, o
                    --    esiti_stato_esecuzione_errore > 0 — ma la formula
                    --    NON sta qui: sta nella vista, e qui si legge. Un
                    --    addendo nuovo entra nella vista e il banner, il
                    --    runner, il digest e il pallino lo vedono insieme.
                    fermo
                FROM vendite.fn_get_lotto_segnalazioni_summary(%s)
                """,
                [lotto_id],
            )
            riga = row_to_dict(cursor)
            # Riga assente (difensivo: la funzione risponde sempre una riga):
            # tutti i conteggi a zero e il verdetto a `false`, con gli STESSI
            # nomi della SELECT.
            if riga is None:
                return cast(
                    LottoSegnalazioniSummary,
                    {c.name: _valore_summary(c.name, None) for c in cursor.description},
                )
        return cast(
            LottoSegnalazioniSummary,
            {chiave: _valore_summary(chiave, valore) for chiave, valore in riga.items()},
        )

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
        limit: int = MAX_LIMIT,
        offset: int = 0,
        order_by: str | None = None,
        order_dir: str = "desc",
        max_rows: int | None = None,
    ) -> tuple[list[LottoSegnalazioneRow], int, int]:
        tetto = _DRAWER_EXPORT_MAX_ROWS if max_rows else LOTTO_LISTE_PAGINA_MAX
        safe_limit, safe_offset = limiti_pagina(max_rows or limit, offset, tetto=tetto)
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT
                    s.riga_key, s.origine, s.data_ora, s.livello, s.messaggio,
                    s.error_code, s.fase, s.fattura_id, s.documento_display,
                    s.importo, s.disabilitato, s.job_corrente, s.total_count,
                    s.fuori_job_count, s.target,
                    -- ⭐ DI QUALE DOCUMENTO PARLA LA RIGA (`20260908-08`). E' la
                    --    colonna che divide questa scheda in DUE FAMIGLIE con vie
                    --    d'uscita diverse: la critica di un documento si toglie
                    --    dal giro, quella del GIRO (`NULL`) si corregge e basta.
                    --    Senza, le due sono indistinguibili — ed e' la ragione
                    --    per cui l'unica proposta a video era «annulla tutto».
                    s.gruppo_key,
                    -- ⭐ Il motivo del pulsante spento, dalla STESSA funzione che
                    --    la madre chiama per rifiutare (§12.5.2).
                    -- ⛔ IL GUARD E' UN `CASE`, NON UNA `WHERE`, ed e' una
                    --    lezione pagata: il check SOLLEVA `E_PARAMETRO_INVALIDO`
                    --    su una chiave vuota, e le righe del GIRO ce l'hanno
                    --    vuota per costruzione. Una `WHERE s.gruppo_key IS NOT
                    --    NULL` dentro la LATERAL NON protegge — la sottoquery
                    --    viene APPIATTITA e la chiamata risale nella proiezione
                    --    esterna, dove gira su tutte le righe. Provato: apriva la
                    --    scheda Critiche con un errore, e a fallire era la LISTA,
                    --    non l'azione.
                    -- ⭐ `CASE` invece garantisce che il ramo non preso non venga
                    --    valutato: e' il meccanismo documentato per proteggere una
                    --    funzione che puo' sollevare.
                    -- ⚠️ Sulle righe del giro le due colonne restano `NULL`, che
                    --    NON vuol dire «si puo' fare»: li' il verbo non ha
                    --    oggetto, e chi rende lo distingue dalla `gruppo_key`.
                    chk.motivi -> 0 ->> 'reason'     AS uscita_blocco_reason,
                    chk.motivi -> 0 ->> 'reason_key' AS uscita_blocco_reason_key,
                    -- ⭐ IL DOCUMENTO COME LO LEGGE UNA PERSONA (`20260908-32`):
                    --    `ORD0036004` invece di `ORDINE_VENDITA:<uuid>`. Non
                    --    sostituisce la chiave, che resta in riga: la chiave la
                    --    vuole il PULSANTE — `fn_escludi_documento_da_giro` la
                    --    riceve — il riferimento e' per l'occhio, ed e' l'unico
                    --    dei due che si vede (la colonna della chiave e' spenta
                    --    a catalogo, D-7).
                    -- ⛔ IN CODA a questa proiezione, e non accanto alla chiave
                    --    dove starebbe meglio: il mapper qui sotto legge per
                    --    POSIZIONE, e infilare una colonna in mezzo sposta tutte
                    --    quelle dopo — un indice sbagliato legge la colonna
                    --    VICINA e non fallisce. E' il difetto gia' pagato su
                    --    `riaperto` il 2026-08-25.
                    s.riferimento
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
                ) s
                LEFT JOIN LATERAL (
                    SELECT CASE WHEN s.gruppo_key IS NOT NULL
                                THEN script.fn_check_documento_escludibile_da_giro(
                                         %s, s.gruppo_key)
                           END AS motivi
                ) chk ON TRUE
                """,
                [
                    int(lotto_id), origine, livello,
                    bool(solo_attive), bool(solo_job_corrente),
                    safe_limit, safe_offset, order_by or None, order_dir,
                    # ⚠️ Secondo passaggio dello stesso id: la LATERAL non puo'
                    #    leggerlo da `s`, perche' la funzione non lo espone fra le
                    #    colonne. L'ordine e' quello TESTUALE dell'SQL.
                    int(lotto_id),
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
                # ⭐ DI CHI E' LA SEGNALAZIONE. `None` = e' del GIRO, ed e' un
                # valore: quella riga non ha un documento da togliere, e il
                # frontend spegne l'azione dicendolo.
                "gruppo_key": row[15],
                # ⚠️ `None` su una riga CON documento = azione ammessa; su una
                # riga del giro non vuol dire niente — li' non e' stato chiesto.
                "uscita_blocco_reason": row[16],
                "uscita_blocco_reason_key": row[17],
                # ⭐ Il documento leggibile. ⚠️ `None` = la segnalazione e' del
                # GIRO, lo stesso NULL di `gruppo_key` e non un'identita' che non
                # si e' risolta: senza chiave non c'e' niente da nominare.
                "riferimento": row[18],
                # ⭐ IL BERSAGLIO: su quale cosa l'errore punta, per offrire un
                # gesto invece di far ricopiare un id. Forma `[{type, id}]`,
                # **byte-identica** a quella dell'envelope d'errore: la scheda e
                # il toast usano lo stesso resolver senza convertire niente.
                #
                # ⛔ NON E' `fattura_id`, che pure sta due righe piu' su. Quello
                # e' il documento che ha FALLITO — nel collaudo la 19563, che
                # l'operatore sta gia' guardando in questa lista; il bersaglio e'
                # dove deve ANDARE, la 835. Sono due entita' diverse, e usare la
                # prima darebbe un pulsante che riporta dove si e' gia'.
                #
                # ⚠️ `jsonb_out`: da un cursore RAW psycopg non decodifica i
                # jsonb, arrivano come stringa. NULL resta NULL = nessun
                # bersaglio, che e' il caso normale e non un difetto.
                "target": jsonb_out(row[14]),
            }
            for row in rows
        ]
        return risultato, total_count, fuori_job

    # Scopo: Restituisce i task run runtime del lotto ordinati dal più recente per consultazione API/UI.
    def list_lotto_task_runs(
        self,
        lotto_id: int,
        *,
        limit: int = DEFAULT_LIMIT_EVENTI,
        offset: int = 0,
        order_by: str | None = None,
        order_dir: str = "desc",
        solo_attivi: bool = True,
        solo_giro_corrente: bool = False,
        task_stato: list[str] | None = None,
        max_rows: int | None = None,
    ) -> tuple[list[LottoTaskRunRow], int, int]:
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
        # sarebbe la terza verita'. ⭐ Vale identico per `task_stato`: uno stato
        # che la funzione non conosce non aggiunge e non toglie nulla, e il
        # vocabolario dei task lo possiede il DB.
        #
        # ⭐ I DUE FILTRI del `20260824-11`, e sono in coda alla firma apposta:
        # le chiamate posizionali precedenti valgono invariate.
        # ⚠️ `esclusi_count` NON e' un accessorio: e' cio' che dice al lettore
        # che sta guardando una FETTA. Invariante garantita dal DB:
        # `total_count + esclusi_count` = le righe che il lotto ha davvero.
        # ⛔ Per questo il metodo torna una TERNA e non piu' una coppia: chi
        # legge il totale filtrato deve avere sotto mano anche cio' che manca.
        tetto = _DRAWER_EXPORT_MAX_ROWS if max_rows else LOTTO_LISTE_PAGINA_MAX
        safe_limit, safe_offset = limiti_pagina(max_rows or limit, offset, tetto=tetto)
        # Lista vuota trattata come assente: «nessuno stato scelto» e «tutti gli
        # stati» sono la stessa domanda, e un array vuoto a DB non lo sarebbe.
        stati = [s for s in (task_stato or []) if s] or None
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT
                    id, lotto_id, pipeline_id, stato_doc_fiscale_id,
                    task_code, fase, tentativo, task_stato,
                    started_at, ended_at, error_code, error_message,
                    meta, giro_corrente, total_count, esclusi_count
                FROM vendite.fn_list_lotto_task_runs(
                    p_lotto_id           => %s,
                    p_solo_attivi        => %s,
                    p_limit              => %s,
                    p_offset             => %s,
                    p_order_by           => %s,
                    p_order_dir          => %s,
                    p_solo_giro_corrente => %s,
                    p_task_stato         => %s
                )
                """,
                [
                    int(lotto_id),
                    bool(solo_attivi),
                    safe_limit,
                    safe_offset,
                    order_by or None,
                    order_dir,
                    bool(solo_giro_corrente),
                    stati,
                ],
            )
            rows = cursor.fetchall()

        total_count = int(rows[0][14]) if rows else 0
        # ⚠️ Su zero righe non c'e' nessuna riga da cui leggere gli esclusi:
        # vale zero per costruzione, come il totale.
        esclusi_count = int(rows[0][15]) if rows else 0
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
                # «Questa riga appartiene all'ultima passata?» ⚠️ Passata, NON
                # azione dell'operatore: `until_done` ne incatena piu' d'una e
                # ognuna scrive il proprio `PIPELINE_STARTED`, che e' l'ancora.
                "giro_corrente": bool(row[13]),
            }
            for row in rows
        ]
        return result, total_count, esclusi_count

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

    # Scopo: Scrive lo stato del JOB del lotto (`stato_lotto`) con la nota in `meta`.
    #
    # ⭐ LA REGOLA DEI PASSAGGI NON STA PIU' QUI (brief-modello-documento-vendita
    #    §15.8 punto 2, F-4, 2026-10-27). La giudica il guard DB
    #    `vendite.trgfn_fatturazione_lotti_guard_stato_job` sulla matrice
    #    `config.transizioni_stati_lotto_job` (`E_LOTTO_PARAMETRO_NON_COERENTE`,
    #    parametro `transizione_stato_lotto`); un valore fuori vocabolario lo
    #    rifiuta la FK sul codice. Qui restavano i tre valori e i passaggi
    #    ricopiati in Python: una seconda sede della stessa regola, ritirata.
    # ⚠️ Un valore fuori vocabolario NON arriva alla FK: il guard (BEFORE)
    #    lo rifiuta prima, come passaggio fuori matrice, col suo codice
    #    (`E_LOTTO_PARAMETRO_NON_COERENTE`). Tradurre qui il 23503 sarebbe
    #    codice morto (provato sul DB: `tests/db/test_lotto_job_stato_db`).
    #
    # ⭐ `COMPLETATO -> ERRORE` e' ammessa (decisione di Tid del 2026-08-24, lotto
    #    6260): «e' andata male» e' un FATTO OSSERVATO e va registrato anche su un
    #    lotto gia' COMPLETATO; «e' andata bene» invece si guadagna con un giro, che
    #    passa da IN_ESECUZIONE. Ora e' una riga della matrice, non un `if` qui.
    def set_lotto_job_stato(self, lotto_id: int, stato: str, messaggio: str) -> None:
        stato_input = (stato or "").strip().upper()
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
            # Stesso stato: nessuna scrittura, cosi' la nota in `meta` resta quella
            # del passaggio che l'ha scritta.
            stato_corrente = str(row[0]) if row[0] is not None else ""
            if stato_corrente == stato_input:
                return
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

    # Scopo: Porta il lotto nello stato fiscale dello step della pipeline.
    #
    # ⭐ Dal verbo di processo del DB, non con un `UPDATE` (brief-modello-documento-
    #    vendita §15.8 punto 1, 2026-10-27): la porta `trgfn_doc_stato_solo_dal_verbo`
    #    rifiuta ogni scrittura dello stato che non passi da un verbo.
    #    `vendite.fn_lotto_proietta_stato_step` e' un passaggio di processo (lo
    #    scrive il giro, che ne e' la causa, senza permesso dell'operatore);
    #    rifiuta uno stato che non sia di uno step del tipo del lotto, e la matrice
    #    la giudica il guard di transizione. Stessi momenti di prima: il processo
    #    dei lotti non cambia (F-4).
    def update_lotto_stato_doc(self, lotto_id: int, stato_doc_fiscale_id: int) -> None:
        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT vendite.fn_lotto_proietta_stato_step(%s, %s)",
                [lotto_id, stato_doc_fiscale_id],
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
        # `Mapping`: si serializza e basta, anche un TypedDict (`PipelineStepLogMeta`).
        meta: Mapping[str, Any] | None,
        gruppo_key: str | None = None,
    ) -> None:
        # ⭐ `gruppo_key` = DI QUALE DOCUMENTO parla questa segnalazione
        #    (changeSet `20260908-20`). `None` = e' del GIRO, ed e' un valore, non
        #    un'assenza: una segnalazione del giro deve fermare il giro, mentre
        #    quella di un documento smette di contare quando il documento esce
        #    (brief-db-uscita-documento-dal-giro, D-6).
        #
        # ⚠️ PARAMETRI PER NOME e non piu' posizionali, ed e' necessario, non
        #    estetico: la `gruppo_key` e' l'OTTAVO parametro e il settimo
        #    (`p_error_code`) qui non si passa — posizionalmente non si puo'
        #    saltare un buco. Per nome, il default del settimo resta quello che
        #    era e il comportamento non cambia di una virgola.
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT vendite.fn_log_pipeline_fase(
                    p_lotto_id             => %s,
                    p_stato_doc_fiscale_id => %s,
                    p_fase                 => %s,
                    p_status               => %s,
                    p_messaggio            => %s,
                    p_meta                 => %s::jsonb,
                    p_gruppo_key           => %s
                )
                """,
                [
                    lotto_id,
                    stato_doc_fiscale_id,
                    fase,
                    status,
                    messaggio,
                    self._to_jsonb_param(meta),
                    gruppo_key,
                ],
            )

    # Scopo: i DOCUMENTI che una commessa alimenta dentro un lotto — la
    #        conversione che serve a chi fallisce al pull, dove si ha in mano la
    #        COMMESSA e non il documento.
    #
    # ⛔ NON SI RISCRIVE IN PYTHON, ed e' la ragione per cui questa funzione DB
    #    esiste (`20260908-18`, chiesta dal backend). Cio' che si copierebbe non
    #    e' il calcolo della chiave — quello e' gia' una funzione — ma DA QUALE
    #    TABELLA SI LEGGE: su `attivita_fatturabili` invece che su
    #    `commesse_attivita` la chiave esce come `COMMESSA:<hash>` e non aggancia
    #    niente. Misurato dal team DB: zero corrispondenze su quattro, e nessun
    #    errore.
    #
    # ⚠️ E' 1:N — una commessa puo' alimentare piu' documenti — e il perimetro
    #    del lotto e' parte della domanda, non un filtro in piu'.
    # ⚠️ `[]` E' UNA RISPOSTA: «questo fallimento non ha un proprietario in
    #    questo lotto». Chi legge scrive UNA riga senza `gruppo_key`, non zero
    #    righe.
    # ⚠️ Fail-loud sui parametri: la funzione SOLLEVA su un id <= 0, perche' qui
    #    e' il backend a chiamarla diretta e un id storto e' un chiamante rotto.
    def gruppi_di_commessa_nel_lotto(
        self, lotto_id: int, commessa_id: int,
    ) -> list[str]:
        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT script.fn_gruppi_di_commessa_nel_lotto(%s, %s)",
                [lotto_id, commessa_id],
            )
            # ⛔ `jsonb_out` NON E' DIFENSIVO, e' NECESSARIO: fuori dall'ORM
            #    psycopg 3 consegna i `jsonb` come STRINGA. Senza, il chiamante
            #    riceve `'["ORDINE_VENDITA:01a0…"]'` e — poiche' una stringa e'
            #    iterabile — il ciclo «una riga per documento» gira una volta per
            #    CARATTERE.
            # 🔴 Non e' un timore: e' successo, e la chiamata vera l'ha mostrato.
            #    Cinquantacinque segnalazioni critiche su un lotto, una per
            #    lettera della chiave, senza nessun errore. I mock non lo vedono
            #    — restituiscono liste — ed e' il motivo per cui questo giro va
            #    fatto sul database.
            payload = jsonb_out(fetchone_scalar(cursor))
        # ⛔ E DECODIFICARE NON BASTA: si pretende una LISTA. Un JSON scalare
        #    resterebbe una stringa iterabile e rifarebbe lo stesso danno.
        # ⚠️ Sulla forma sbagliata si ripiega su `[]` — che il chiamante legge
        #    come «nessun proprietario» e traduce in UNA riga senza `gruppo_key`,
        #    cioe' una segnalazione che BLOCCA il giro. E' il verso sicuro: un
        #    contratto rotto deve fermare il lotto, non inventargli documenti.
        # ⚠️ Ma si DICHIARA: un ripiego muto qui sarebbe un lotto che si blocca
        #    per una ragione che nessuno sa leggere.
        if not isinstance(payload, list):
            logging.getLogger(__name__).warning(
                "gruppi_di_commessa_nel_lotto.forma_inattesa lotto_id=%s "
                "commessa_id=%s tipo=%s — la segnalazione restera' senza "
                "proprietario e fermera' il giro",
                lotto_id, commessa_id, type(payload).__name__,
            )
            return []
        return [str(k) for k in payload]

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
                """,  # noqa: S608 — SELECT sorgente letterale dai due chiamanti privati, valori come parametri
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
        lock = optional_bool(params, "lock", default=False)
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
                    p_data_fatturazione => COALESCE(%s, (SELECT script.fn_data_operativa())),
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
                    a.tipo_movimento,
                    art.codice
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
                # NOT NULL a DB (`attivita_fatturabili.articolo_id`).
                articolo_id=str(row[1]),
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
                articolo_codice=row[11],
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

    # Scopo: Le fatture del lotto nell'ORDINE in cui il plafond va consumato.
    # ⛔ L'ORDINE E' UN REQUISITO FISCALE, non una comodita' (`P5` / `D15-bis`).
    #    Il lock di riga sul titolo impedisce a due transazioni di portare il
    #    plafond sotto zero insieme, ma NON sa che esiste una fattura
    #    ANTERIORE non ancora arrivata: senza quest'ordine, a plafond quasi
    #    esaurito e' la FORTUNA a decidere quale cliente resta scoperto.
    # ⚠️ `numero` e' NULL per tutte quando questo giro parte — la numerazione
    #    viene dopo — quindi a discriminare e' la DATA, e l'`id` e' il
    #    pareggio stabile. La colonna resta nell'ORDER BY perche' la regola e'
    #    «data, poi numero»: il giorno che il task girasse su documenti gia'
    #    numerati direbbe ancora la cosa giusta, invece di dipendere da quando
    #    e' stato scritto.
    def list_fatture_by_lotto_ordinate(
        self, lotto_id: int, *, limit: int = 50000
    ) -> list[int]:
        safe_limit = max(1, min(int(limit), 100000))
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT f.id
                FROM vendite.fatturazione_lotti_fatture lf
                JOIN vendite.fatture f
                  ON f.id = lf.fattura_id
                WHERE lf.lotto_id = %s
                ORDER BY f.data, f.numero NULLS FIRST, f.id
                LIMIT %s
                """,
                [lotto_id, safe_limit],
            )
            rows = cursor.fetchall()
        if len(rows) == safe_limit:
            logger.warning(
                "list_fatture_by_lotto_ordinate: risultato troncato al limit=%s "
                "per lotto_id=%s",
                safe_limit, lotto_id,
            )
        return [int(row[0]) for row in rows]

    # Scopo: Le righe di una fattura che il consumo del plafond deve guardare,
    #        con quanto serve a spezzarle.
    # ⚠️ Si escludono le righe che sono GIA' una parte (`riga_capofila_id`
    #    valorizzata): spezzare una parte darebbe la catena che il guard
    #    `E_FATTURA_RIGA_CAPOFILA_INCOERENTE` rifiuta, e il giro dev'essere
    #    ripetibile senza moltiplicare le righe.
    # ⚠️ Si escludono le RETTIFICHE: la loro IVA viene dal documento che
    #    correggono (`N-1`) e non si ri-risolve.
    # ⭐ Porta le colonne kit (R-BE-P1, brief-db-bom-flag-quantita-e-kit-in-
    #    fattura §11): i componenti di un kit si consumano come un gruppo
    #    (D-5), e la parte di un componente le copia dalla capofila.
    def list_righe_per_plafond(self, fattura_id: int) -> list[dict[str, Any]]:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT r.id, r.riga_nr, r.articolo_id, r.descrizione, r.uom_id,
                       r.qta, r.prezzo_unitario, r.sconto_percentuale, r.iva_id,
                       r.imponibile_riga, r.dest_billing_account_id,
                       r.sorgente_tipo_id, r.sorgente_uid, r.sorgente_riga,
                       r.kit_key, r.kit_esposizione, r.kit_articolo_padre_id,
                       r.kit_descrizione_padre, r.kit_qta, r.kit_uom_id,
                       r.meta
                  FROM vendite.fatture_righe r
                 WHERE r.fattura_id = %s
                   AND r.riga_capofila_id IS NULL
                   AND r.riga_rettificata_id IS NULL
                   AND r.articolo_id IS NOT NULL
                 ORDER BY r.riga_nr, r.id
                """,
                [fattura_id],
            )
            righe = rows_to_list(cursor)
        # ⛔ Il driver restituisce `jsonb` come STRINGA. Senza questa coercion
        #    il servizio farebbe `dict("{...}")` sul `meta` e — a seconda della
        #    stringa — o solleverebbe un `ValueError` grezzo in mezzo a un giro
        #    fiscale, o produrrebbe un dizionario di CARATTERI. E' la stessa
        #    trappola gia' pagata su `list_attivita_da_fatturare`, dove il
        #    commento la racconta: i test mockati non la vedono, perche'
        #    iniettano gia' dei dict.
        for riga in righe:
            riga["meta"] = coerce_jsonb_dict(riga.get("meta"))
        return righe

    # Scopo: La SECONDA parte di una riga spezzata dal plafond.
    # ⛔ `riga_capofila_id` punta alla capofila, che e' essa stessa la prima
    #    parte. La FK e' COMPOSITA `(riga_capofila_id, fattura_id)`: una parte
    #    che puntasse a una riga di un altro documento non viene scritta — non
    #    per sorveglianza, per vincolo.
    # ⭐ La parte di un componente di kit COPIA le colonne kit dalla capofila
    #    (R-BE-P5): senza, usciva dal kit come riga sciolta. Solo `kit_qta` si
    #    passa, perche' e' la sua quota di kit (D-5). Su una riga sciolta le
    #    colonne copiate sono NULL e `kit_qta` arriva `None`: il CHECK
    #    `chk_fatture_righe_kit_coerente` vuole le due cose insieme.
    def insert_parte_plafond(
        self,
        *,
        riga_capofila_id: int,
        riga_nr: int,
        qta: Decimal,
        iva_id: int | None,
        kit_qta: Decimal | None,
        meta: dict[str, Any] | None,
    ) -> int:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                INSERT INTO vendite.fatture_righe (
                    fattura_id, riga_nr, articolo_id, descrizione, uom_id,
                    qta, prezzo_unitario, sconto_percentuale, iva_id,
                    dest_billing_account_id, sorgente_tipo_id, sorgente_uid,
                    sorgente_riga, riga_capofila_id, competenza_dal,
                    competenza_al, kit_key, kit_esposizione,
                    kit_articolo_padre_id, kit_descrizione_padre, kit_uom_id,
                    kit_qta, meta
                )
                SELECT c.fattura_id, %s, c.articolo_id, c.descrizione, c.uom_id,
                       %s, c.prezzo_unitario, c.sconto_percentuale, %s,
                       c.dest_billing_account_id, c.sorgente_tipo_id,
                       c.sorgente_uid, c.sorgente_riga, c.id,
                       -- La parte e' la stessa riga spezzata per IVA: stesso
                       -- periodo della capofila.
                       c.competenza_dal, c.competenza_al,
                       -- E lo stesso kit: la vista la rimette sotto il suo
                       -- padre, nel ramo della sua aliquota.
                       c.kit_key, c.kit_esposizione, c.kit_articolo_padre_id,
                       c.kit_descrizione_padre, c.kit_uom_id,
                       %s, %s::jsonb
                  FROM vendite.fatture_righe c
                 WHERE c.id = %s
                RETURNING id
                """,
                [riga_nr, qta, iva_id, kit_qta, self._to_jsonb_param(meta),
                 riga_capofila_id],
            )
            row = cursor.fetchone()
            assert row is not None
        return int(row[0])

    # Scopo: aggiorna la CAPOFILA dopo la spezzatura: la sua quantita' scende
    #        alla quota coperta e la sua IVA diventa quella del titolo.
    # ⚠️ `storicizza` si accende QUI e solo sulle righe spezzate (`P10`): il
    #    rubinetto dello storico e' PER RIGA, e accenderlo su tutte darebbe
    #    l'archivio sproporzionato che la decisione di Tid esclude.
    # ⭐ `kit_qta` si scrive sempre (R-BE-P4): su un componente spezzato e' la
    #    quota di kit della capofila, su una copertura piena il valore di
    #    prima, su una riga sciolta `None` (era gia' NULL).
    def aggiorna_capofila_plafond(
        self,
        *,
        riga_id: int,
        qta: Decimal,
        iva_id: int | None,
        kit_qta: Decimal | None,
        meta: dict[str, Any] | None,
    ) -> None:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                UPDATE vendite.fatture_righe
                   SET qta = %s,
                       iva_id = %s,
                       kit_qta = %s,
                       storicizza = TRUE,
                       meta = %s::jsonb
                 WHERE id = %s
                """,
                [qta, iva_id, kit_qta, self._to_jsonb_param(meta), riga_id],
            )

    # Scopo: Wrapper su `anagrafiche.fn_consuma_plafond_titolo_iva_righe`: il
    #        consumo per un GRUPPO di righe che si spezzano insieme (i
    #        componenti di un kit, D-5; una riga sciolta e' un gruppo di uno).
    # ⭐ E' la funzione che PRENDE IL LOCK di riga sul titolo (`D15-bis`) e
    #    ritorna la ripartizione EFFETTIVA: il backend non la calcola, la
    #    riceve. Il risolutore e' `STABLE` e proietta; questa consuma.
    # ⚠️ Ritorna una riga per riga passata, NELL'ORDINE passato, con la
    #    `frazione` effettiva del gruppo: e' quella che divide anche la
    #    quantita' del kit (R-BE-P3, P4).
    def consuma_plafond_titolo_righe(
        self,
        *,
        titolo_iva_id: int,
        fattura_id: int,
        fattura_riga_ids: list[int],
        imponibili: list[Decimal],
        data_movimento: date,
    ) -> list[dict[str, Any]]:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT fattura_riga_id, imponibile, quota_coperta,
                       quota_ordinaria, frazione, residuo_dopo, movimento_id
                  FROM anagrafiche.fn_consuma_plafond_titolo_iva_righe(
                           %s, %s, %s::bigint[], %s::numeric[], %s)
                """,
                [titolo_iva_id, fattura_id, list(fattura_riga_ids),
                 list(imponibili), data_movimento],
            )
            return rows_to_list(cursor)

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

    # ------------------------------------------------------------------
    # La DATA DOCUMENTO (brief numerazione §4, DB-4/DB-10/DB-11)
    # ------------------------------------------------------------------

    # Scopo: Da quale data in poi le fatture non ancora numerate del lotto
    #        possono prendere un numero — il MASSIMO dei pavimenti dei sezionali
    #        che il lotto tocca. `None` = nessun pavimento (sezionale vergine).
    # ⚠️ E' una TARGA, non un lucchetto: `fn_get_data_minima_numerabile_lotto` e'
    #    SECURITY INVOKER su `vendite.fatture`, che ha la RLS, quindi sotto un
    #    perimetro ristretto il minimo esce PIU' BASSO del vero (fail-open, e la
    #    funzione DB lo dichiara). Serve a dare al DatePicker un `minDate`
    #    sensato; il rifiuto vero resta del cancello in
    #    `fn_get_next_progressivo`, che legge il contatore — tabella senza RLS.
    def get_data_minima_numerabile_lotto(self, lotto_id: int) -> date | None:
        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT vendite.fn_get_data_minima_numerabile_lotto(%s)",
                [int(lotto_id)],
            )
            row = cursor.fetchone()
        return None if not row else row[0]

    # Scopo: La data che i documenti ANCORA DA NUMERARE portano OGGI — la piu'
    #        VECCHIA fra loro, cioe' quella che il cancello incontrera' per
    #        prima. `None` = nel perimetro non c'e' niente da numerare.
    # ⭐ Serve al dialog per due cose che il pavimento da solo non dice: quale
    #    data proporre quando va gia' bene (non si tocca niente) e, quando NON
    #    va bene, DA COSA a cosa si sta spostando. Un DatePicker che mostra solo
    #    il minimo ammesso non fa vedere che sta per cambiare una data.
    # ⚠️ `min` e non `max`: se il perimetro contiene documenti di date diverse,
    #    quello che rischia il rifiuto e' il piu' vecchio.
    # ⚠️ Stessa `WHERE` di `list_lotti_numerabili` sul ramo competenza: si misura
    #    cio' che l'atto toccherebbe, non tutto il mese.
    # ⛔ Guard esplicito sul perimetro, e non e' burocrazia: senza, una chiamata
    #    senza argomenti cadrebbe nel ramo competenza con `competenza_mese`
    #    NULL, non troverebbe nessun lotto e risponderebbe `None` — cioe'
    #    «niente da numerare», che a video diventa un messaggio tranquillo su
    #    una domanda mai posta. Un errore di chiamante non deve poter uscire
    #    come un dato.
    def get_data_documento_corrente(
        self,
        *,
        lotto_id: int | None = None,
        competenza_mese: date | None = None,
        lotti_ids: list[int] | None = None,
        stato_doc_fiscale_id: int | None = None,
    ) -> date | None:
        # ⛔ TRE perimetri, esattamente uno. Il guard non e' burocrazia: senza,
        #    una chiamata senza argomenti cadrebbe in un ramo con i parametri a
        #    NULL, non troverebbe nessun lotto e risponderebbe `None` — cioe'
        #    «niente da numerare», che a video diventa un messaggio tranquillo
        #    su una domanda mai posta. Un errore di chiamante non deve poter
        #    uscire come un dato.
        scelti = [p for p in (lotto_id, competenza_mese, lotti_ids) if p is not None]
        if len(scelti) != 1:
            raise ValueError(
                "get_data_documento_corrente: indicare ESATTAMENTE uno fra "
                "lotto_id, competenza_mese e lotti_ids "
                f"(lotto_id={lotto_id!r} competenza_mese={competenza_mese!r} "
                f"lotti_ids={lotti_ids!r})"
            )
        if lotto_id is not None:
            sql = SQL_DATA_DOCUMENTO_CORRENTE.format(lotto="%s")
            params: list[Any] = [int(lotto_id)]
        else:
            perimetro, params = costruisci_perimetro_lotti_numerabili(
                lotti_alias="fl_p",
                stato_doc_fiscale_id=stato_doc_fiscale_id,
                competenza_mese=competenza_mese,
                lotti_ids=lotti_ids,
            )
            sql = """
                SELECT min(f_p.data)
                  FROM vendite.fatturazione_lotti fl_p
                  JOIN vendite.fatturazione_lotti_fatture lf_p ON lf_p.lotto_id = fl_p.id
                  JOIN vendite.fatture f_p ON f_p.id = lf_p.fattura_id
                 WHERE {perimetro}
                   AND f_p.numero IS NULL
            """.format(perimetro=perimetro)  # noqa: S608 — perimetro da costruisci_perimetro_lotti_numerabili (alias letterale + %s), valori come parametri
        with connection.cursor() as cursor:
            cursor.execute(sql, params)
            row = cursor.fetchone()
        return None if not row else row[0]

    # Scopo: Lo stesso pavimento, ma per l'ATTO su un mese di competenza
    #        («Rendi definitive competenza»), che tocca N lotti: il piu'
    #        restrittivo fra i loro, cioe' l'unica data che li accontenta tutti.
    # ⭐ CHIAMA LA FUNZIONE DB UNA VOLTA PER LOTTO dentro UNA sola istruzione,
    #    invece di ricopiarne la regola in un JOIN scritto qui. La regola —
    #    «max(ultima_data) sui sezionali delle fatture senza numero», con la
    #    serie risolta come la risolve chi numera — vive in un posto solo: una
    #    seconda copia qui divergerebbe alla prima modifica, e in silenzio.
    # ⚠️ I lotti sono quelli che l'atto numererebbe davvero (stessa `WHERE` di
    #    `list_lotti_numerabili`): un pavimento calcolato su lotti che non
    #    verranno toccati sarebbe piu' alto del necessario.
    # ⚠️ Vale per ENTRAMBI i perimetri, e sulla selezione conta di piu': il
    #    pavimento e' di ogni SEZIONALE, e spuntando lotti di registri diversi il
    #    piu' restrittivo puo' essere molto piu' avanti degli altri. `max` resta
    #    la risposta giusta — e' l'unica data che li accontenta tutti — ma e' la
    #    ragione per cui il dialog deve ricalcolarlo MENTRE la selezione cambia,
    #    non una volta all'apertura.
    def get_data_minima_numerabile_perimetro(
        self,
        *,
        stato_doc_fiscale_id: int,
        competenza_mese: date | None = None,
        lotti_ids: list[int] | None = None,
    ) -> date | None:
        perimetro, par_perimetro = costruisci_perimetro_lotti_numerabili(
            lotti_alias="fl_p",
            stato_doc_fiscale_id=stato_doc_fiscale_id,
            competenza_mese=competenza_mese,
            lotti_ids=lotti_ids,
        )
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT max(vendite.fn_get_data_minima_numerabile_lotto(fl_p.id))
                  FROM vendite.fatturazione_lotti fl_p
                 WHERE {perimetro}
                """.format(perimetro=perimetro),  # noqa: S608 — perimetro da costruisci_perimetro_lotti_numerabili (alias letterale + %s), valori come parametri
                par_perimetro,
            )
            row = cursor.fetchone()
        return None if not row else row[0]

    # Scopo: Dichiara la data documento del lotto delegando alla funzione MADRE
    #        `vendite.fn_imposta_data_documento_lotto`, che in un atto solo
    #        scrive la data sul lotto, la propaga alle fatture non ancora
    #        numerate e RIGENERA i loro piani rate.
    # ⛔ Non si scompone in tre chiamate da qui: le scadenze si calcolano da
    #    `fatture.data` e il guard D-K verifica la SOMMA delle rate — che non
    #    cambia. Una data nuova con le rate vecchie passerebbe in silenzio, ed e'
    #    esattamente il difetto che quella funzione esiste per impedire.
    # ⚠️ Le fatture gia' numerate si SALTANO e si contano: il caso «lotto
    #    numerato a meta'» esiste nei dati.
    def imposta_data_documento_lotto(
        self, *, lotto_id: int, data_documento: date,
    ) -> EsitoDataDocumento:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT aggiornate, saltate_numerate, rate_rigenerate
                  FROM vendite.fn_imposta_data_documento_lotto(%s, %s)
                """,
                [int(lotto_id), data_documento],
            )
            row = cursor.fetchone()
            assert row is not None
        return {
            "aggiornate": int(row[0]),
            "saltate_numerate": int(row[1]),
            "rate_rigenerate": int(row[2]),
        }

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
    #        fattura del lotto (outbox stampa, Fase C C-2c), col tipo di
    #        documento da stampare quando il chiamante lo conosce (C-1,
    #        brief-db-modelli-documento-standard §9): NULL = lo deduce la
    #        risoluzione al drenaggio, se la sorgente ne ha uno solo.
    #        Idempotente (vincolo di esclusione ex_fatture_stampa_coda_vivo:
    #        una riga viva per fattura e tipo, una col tipo NULL esclude le
    #        altre). Ritorna il numero di righe accodate.
    def accoda_stampe_lotto(
        self, lotto_id: int, tipo_documento_output_id: int | None = None,
    ) -> int:
        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT vendite.fn_accoda_stampe_lotto(%s, %s)",
                [lotto_id, tipo_documento_output_id],
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
    #        ri-accodamento, ex_fatture_stampa_coda_vivo). `data_update = now()`
    #        = claimed_at per il reaper (la tabella non ha trigger audit).
    #        Ordine per id (indice parziale ix_fatture_stampa_coda_da_lavorare).
    #        Il render avviene FUORI da qui: la connessione non tiene il lock
    #        durante l'I/O (I-4b). Ritorna i work-item claimati (lista dict),
    #        col tipo di documento da stampare (NULL = lo deduce la
    #        risoluzione).
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
                      c.lotto_id, c.template_documento_id,
                      c.tipo_documento_output_id, c.tentativi
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
    #        Filtri opzionali stati/lotto/intervallo `data_insert` (giorni
    #        dell'AZIENDA, `data_a` incluso: BB `predicato_giorno_operativo`).
    #        Ordinamento (2026-07-23, richiesta Tid): `sort_by`/`sort_dir` da
    #        whitelist `CODA_STAMPA_SORT_SQL` — il service valida, qui controllo
    #        esplicito di defense-in-depth (BB `sql_order_clause` rigido).
    #        Default `data_update DESC` («aggiornato»: la riga lavorata piu` di
    #        recente in testa); tiebreaker `c.id` allineato alla direzione
    #        (regola 2026-08-03) per un ordine stabile. E` una lista di monitoraggio, non la corsia
    #        del worker. Ritorna `{items, total, archiviate}` via BB
    #        `fetch_paged_with_total` (fallback pagina-stantia: la coda si
    #        auto-svuota sotto l'utente a ogni drain).
    #
    #        ⭐ ARCHIVIAZIONE (2026-09-04, brief-db-archiviazione-righe-code),
    #        gemella della coda lavori parola per parola. Le righe archiviate
    #        sono NASCOSTE di default; `includi_archiviate=True` le chiede.
    #        ⛔ La bandiera la legge SOLO questa lista: claim, reaper, `marca_*`
    #        e soprattutto `count_coda_stampa_per_stato` — i conteggi del
    #        pannello «Esiti fatturazione», che sono la RAGIONE per cui la
    #        bandiera esiste — non la nominano.
    #        ⚠️ `archiviate` dice quante ne restano fuori: senza quel numero
    #        «coda pulita» e «tre righe messe via» si leggono uguali.
    def elenca_coda_stampa(
        self,
        *,
        operatore: str | None = None,
        caller_username: str | None = None,
        stati: list[str] | None = None,
        lotto_id: int | None = None,
        data_da: date | None = None,
        data_a: date | None = None,
        includi_archiviate: bool = False,
        limit: int = DEFAULT_LIMIT,
        offset: int = 0,
        sort_by: str = "data_update",
        sort_dir: str = "DESC",
    ) -> dict[str, Any]:
        # `base_*` = il perimetro SENZA la bandiera: frammento condiviso fra le
        # righe e il conteggio delle archiviate, che devono avere lo stesso
        # perimetro (scritto due volte, divergerebbe).
        base_conditions: list[str] = []
        base_params: list[Any] = []
        if stati:
            base_conditions.append("c.stato = ANY(%s)")
            base_params.append(list(stati))
        if lotto_id is not None:
            base_conditions.append("c.lotto_id = %s")
            base_params.append(int(lotto_id))
        giorno_sql, giorno_params = predicato_giorno_operativo("c.data_insert", data_da, data_a)
        base_conditions.append(giorno_sql)
        base_params.extend(giorno_params)
        if operatore is not None:
            base_conditions.append("c.user_insert = %s")
            base_params.append(str(operatore))
        conditions = list(base_conditions)
        params = list(base_params)
        if not includi_archiviate:
            conditions.append("NOT c.archiviato")
        where = ("WHERE " + " AND ".join(conditions)) if conditions else ""
        safe_limit, safe_offset = limiti_pagina(limit, offset)
        # Whitelist prima dell'SQL: BB `sql_order_clause` RIGIDO — sort_by o
        # sort_dir fuori lista sono `ValueError`, mai il default.
        order_by = sql_order_clause(
            sort_by, sort_dir,
            colonne=CODA_STAMPA_SORT_SQL, default="c.data_insert",
            default_desc=True, colonne_desc=CODA_STAMPA_SORT_COLONNE_DATA,
            tiebreak="c.id",
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
                   c.archiviato, c.archiviato_il, c.archiviato_da,
                   c.user_insert AS operatore,
                   (c.user_insert = %s) AS is_mio,
                   COUNT(*) OVER() AS total_count
              {from_join}
              {where}
             ORDER BY {order_by}
             LIMIT %s OFFSET %s
        """  # where/order da whitelist chiuse (nessun input libero)
        rows, total = fetch_paged_with_total(
            data_sql,
            # `caller_username` per primo: è il parametro dell'is_mio nella
            # SELECT, che precede il WHERE. '' quando None: non matcha nessun
            # user reale → is_mio False, mai NULL.
            [caller_username or "", *params, safe_limit, safe_offset],
            fallback_count_sql=(
                f"SELECT COUNT(*) {from_join} {where}"
            ),
            fallback_params=list(params),
            offset=safe_offset,
        )
        # Le nascoste, con lo STESSO perimetro della lista meno la bandiera —
        # `from_join` e' lo stesso frammento della query di pagina, non una
        # copia riscritta. Zero quando sono incluse: li' non c'e' niente di
        # nascosto da dichiarare.
        archiviate = 0 if includi_archiviate else conta_con_perimetro(
            from_join, [*base_conditions, "c.archiviato"], base_params,
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
                "archiviato": bool(r["archiviato"]),
                "archiviato_il": iso_or_none(r["archiviato_il"]),
                "archiviato_da": r["archiviato_da"],
            }
            for r in rows
        ]
        return {"items": items, "total": int(total), "archiviate": archiviate}

    # Scopo: alza o abbassa la bandiera `archiviato` di una riga della coda
    #        stampa — l'ARCHIVIAZIONE, che toglie la riga dall'ELENCO senza
    #        toccarne lo stato (brief-db-archiviazione-righe-code). Ritorna
    #        True se la riga esiste ED è nel perimetro del chiamante (0 righe =
    #        inesistente o fuori scope, indistinguibili → 404 no-leak).
    #
    #        ⚠️ È la PRIMA scrittura dell'operatore su questa tabella. Dal
    #        2026-09-04 la difende anche la policy RLS
    #        `rls_fatture_stampa_coda_ef_whitelist`, ma il filtro applicativo
    #        va messo lo stesso: la RLS si SOMMA ai filtri, non li sostituisce.
    #        Lo scope vive sulla FATTURA (la coda non ha colonna emittente),
    #        quindi passa dal JOIN — stessa forma di
    #        `count_coda_stampa_per_stato`.
    #        ⛔ Il criterio «solo una riga non viva si archivia» NON si ricopia
    #        qui: vive nel trigger `trg_fatture_stampa_coda_a10_archiviazione_upd`
    #        (`E_CODA_ARCHIVIAZIONE_NON_AMMESSA`, 409) e nel `CHECK`. Una copia
    #        in Python sarebbe un secondo elenco di stati destinato a sfilarsi.
    #        ⛔ `archiviato_il`/`archiviato_da` le deriva il trigger dalla GUC
    #        `app.jwt_user`: da qui non si scrivono.
    #        ⚠️ Il perimetro arriva GIA' RISOLTO (`emittenti_sr_ids`) e non come
    #        `auth_user_id`, ed e' la differenza fra un metodo isolato e uno
    #        dentro un giro: questo lavora su UNA riga ma viene chiamato N volte
    #        per una sola richiesta, e risolvere il perimetro a ogni giro
    #        sarebbe una query per riga per un dato che dentro la richiesta non
    #        cambia. Lo risolve una volta chi apre il giro.
    #        Semantica invariata: `None` = nessuna restrizione, `[]` =
    #        fail-closed (`= ANY('{}')` non matcha nulla).
    def imposta_archiviato_stampa(
        self, coda_id: int, *, archiviato: bool, emittenti_sr_ids: list[int] | None,
    ) -> bool:
        conditions: list[str] = ["c.id = %s", "f.id = c.sorgente_id"]
        params: list[Any] = [bool(archiviato), int(coda_id)]
        add_emittente_scope_condition_risolta(
            conditions, params,
            scope_ids=emittenti_sr_ids,
            column="f.emittente_soggetto_ruolo_id",
        )
        where = " AND ".join(conditions)
        with connection.cursor() as cursor:
            cursor.execute(
                f"""
                UPDATE vendite.fatture_stampa_coda c
                   SET archiviato = %s
                  FROM vendite.fatture f
                 WHERE {where}
                """,  # noqa: S608 — where da condizioni whitelisted
                params,
            )
            return cursor.rowcount > 0

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

    # Scopo: Il contesto che il risolutore IVA vuole, per un batch di testate
    #        fattura: billing account del CLIENTE, PK dell'emittente e data.
    # Perimetro: sola lettura, un round-trip. Le testate fuori dal perimetro RLS
    #        non compaiono, ed e' la stessa risposta che dara' la scrittura.
    #
    # ⛔ `fn_get_emittente_fiscale_pk` E NON `f.emittente_soggetto_ruolo_id`.
    #    La testata porta il SOGGETTO-RUOLO dell'emittente; il risolutore vuole
    #    la PK di `anagrafiche.emittenti_fiscali`. I due numeri si somigliano
    #    abbastanza da passare inosservati e il difetto sarebbe MUTO: con l'id
    #    sbagliato la funzione non trova l'emittente, quindi non trova i suoi
    #    titoli, e risponde con l'aliquota ORDINARIA senza sollevare — cioe'
    #    l'IVA piena a un esportatore abituale, su una fattura.
    #    (`feedback_emittente_pk_vs_soggetto_ruolo`, gia' pagato tre volte.)
    #
    # ⚠️ Il BA e' quello della TESTATA, cioe' il cliente, non il
    #    `dest_billing_account_id` della riga (che e' la destinazione della
    #    merce): la domanda fiscale — titoli, esigibilita', split — e' del
    #    soggetto che paga.
    def batch_get_fattura_iva_context(
        self, fattura_ids: list[int]
    ) -> dict[int, dict[str, Any]]:
        if not fattura_ids:
            return {}
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT
                    f.id,
                    f.billing_account_id,
                    anagrafiche.fn_get_emittente_fiscale_pk(f.billing_account_id),
                    f.data
                FROM vendite.fatture f
                WHERE f.id = ANY(%s)
                """,
                [fattura_ids],
            )
            rows = cursor.fetchall()
        return {
            int(r[0]): {
                "billing_account_id": int(r[1]),
                "emittente_fiscale_id": None if r[2] is None else int(r[2]),
                "data_riferimento": r[3],
            }
            for r in rows
        }

    # Scopo: Gestisce `build_fattura_key` nel flusso applicativo del modulo.
    def build_fattura_key(self, attivita_id: int) -> dict[str, Any]:
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

    # Scopo: toglie UN documento dal giro di fatturazione — una SELECT sola
    #        sulla funzione MADRE, che e' atomica per costruzione.
    #
    # ⛔ NESSUNA ORCHESTRAZIONE QUI, ed e' il §6.2 del brief: la cancellazione
    #    della bozza, il ritiro delle attivita', la marcatura dell'uscita e la
    #    riapertura dei documenti trascinati stanno TUTTE dentro la funzione.
    #    Ricomporle in Python vorrebbe dire una seconda sede della sequenza — e
    #    una sequenza in due sedi si interrompe a meta' il giorno che una delle
    #    due cambia.
    #
    # ⚠️ E nemmeno il RIFIUTO: la madre chiama `fn_check_documento_escludibile_da_giro`
    #    e solleva il codice del PRIMO motivo. Il ServiceError arriva da li',
    #    col codice giusto (409) e la frase a catalogo.
    def escludi_documento_da_giro(
        self, lotto_id: int, gruppo_key: str, motivo: str,
    ) -> EsclusioneDocumentoDaGiroResult:
        payload = call_jsonb_fn(
            "vendite.fn_escludi_documento_da_giro", lotto_id, gruppo_key, motivo,
        )
        return {
            "lotto_id": int(payload["lotto_id"]),
            "gruppo_escluso": str(payload["gruppo_escluso"]),
            "fatture_cancellate": int(payload.get("fatture_cancellate") or 0),
            "attivita_riemesse": int(payload.get("attivita_riemesse") or 0),
            # ⚠️ `list(...)` e non il valore com'e': psycopg adatta il jsonb a
            #    liste Python, ma un `null` a catalogo diventerebbe `None` e il
            #    chiamante conterebbe `len(None)`.
            "gruppi_riaperti": list(payload.get("gruppi_riaperti") or []),
            "n_gruppi_riaperti": int(payload.get("n_gruppi_riaperti") or 0),
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
        righe_kit_esposizioni: list[str | None],
        righe_kit_articolo_padre_ids: list[str | None],  # uuid
        righe_kit_qtas: list[Decimal | None],
        righe_kit_uom_ids: list[int | None],
        righe_competenze_dal: list[date],
        righe_competenze_al: list[date],
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
        righe: dict[str, list[Any]] = {
            "fattura_ids": righe_fattura_ids, "nrs": righe_nrs,
            "articolo_ids": righe_articolo_ids, "descrizioni": righe_descrizioni,
            "uom_ids": righe_uom_ids, "qtas": righe_qtas,
            "prezzi": righe_prezzi_unitari, "iva_ids": righe_iva_ids,
            "dest_ba_ids": righe_dest_billing_account_ids,
            "kit_keys": righe_kit_keys, "kit_esposizioni": righe_kit_esposizioni,
            "kit_padri": righe_kit_articolo_padre_ids, "metas": righe_metas,
            # Le due colonne della rettifica entrano nel guard come tutte le
            # altre: sono esattamente il tipo di array che si dimentica di
            # allineare, ed `unnest` non lo direbbe.
            "sconti": righe_sconti, "rettificate": righe_rettificate,
            "kit_qtas": righe_kit_qtas, "kit_uom_ids": righe_kit_uom_ids,
            "competenze_dal": righe_competenze_dal,
            "competenze_al": righe_competenze_al,
        }
        att: dict[str, list[Any]] = {
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
                        %s::varchar[],
                        %s::uuid[],
                        %s::numeric[],
                        %s::bigint[],
                        %s::numeric[],
                        %s::bigint[],
                        %s::date[],
                        %s::date[],
                        %s::jsonb[]
                    ) AS t(
                        fattura_id, riga_nr, articolo_id, descrizione,
                        uom_id, qta, prezzo_unitario, iva_id,
                        dest_billing_account_id,
                        kit_key, kit_esposizione, kit_articolo_padre_id,
                        sconto_percentuale, riga_rettificata_id,
                        kit_qta, kit_uom_id, competenza_dal, competenza_al,
                        meta
                    )
                ),
                inserted AS (
                    INSERT INTO vendite.fatture_righe (
                        fattura_id, riga_nr, articolo_id, descrizione,
                        uom_id, qta, prezzo_unitario, iva_id,
                        dest_billing_account_id,
                        sorgente_tipo_id, sorgente_uid, sorgente_riga,
                        kit_key, kit_esposizione,
                        kit_articolo_padre_id, kit_descrizione_padre,
                        sconto_percentuale, riga_rettificata_id,
                        kit_qta, kit_uom_id, competenza_dal, competenza_al,
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
                        d.kit_key, d.kit_esposizione,
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
                        -- Quantita' e UoM della riga padre del kit (NULL fuori
                        -- dal kit: lo pretende chk_fatture_righe_kit_coerente)
                        -- e il periodo della riga, NOT NULL e senza default.
                        d.kit_qta, d.kit_uom_id,
                        d.competenza_dal, d.competenza_al,
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
                -- ⛔ `fatturato` NON si scrive: dal 20260826-33 e' una colonna
                --    GENERATED ALWAYS AS (fattura_riga_id IS NOT NULL) STORED,
                --    e scriverla e' un errore (SQLSTATE 428C9), non un no-op.
                --    Il timbro si deriva da `fattura_riga_id`, che sta gia' in
                --    questo stesso SET: era un doppione, e finche' i due dati
                --    erano autonomi potevano — e il 2026-07 lo hanno fatto —
                --    smettere di dire la stessa cosa. Ora il disaccordo non e'
                --    piu' rappresentabile.
                --    Piano: brief-db-lavoro-che-non-torna-indietro, L3b.
                UPDATE vendite.attivita_fatturabili a
                SET fattura_riga_id = c.fattura_riga_id,
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
                    righe_kit_esposizioni,
                    righe_kit_articolo_padre_ids,
                    # ⚠️ L'ordine di questa lista È il contratto con l'`unnest`:
                    # le due nuove vanno PRIMA di `righe_metas`, come nella
                    # clausola. Invertirle non solleverebbe — produrrebbe righe
                    # con lo sconto al posto del puntatore.
                    righe_sconti,
                    righe_rettificate,
                    righe_kit_qtas,
                    righe_kit_uom_ids,
                    righe_competenze_dal,
                    righe_competenze_al,
                    righe_metas,
                    att_ids,
                    att_fattura_ids,
                    att_riga_nrs,
                ],
            )
            return cursor.rowcount

    # Scopo: Appende a un gruppo del lotto l'ESITO della sua lavorazione —
    #        `COMPLETED` oppure `ERRORE` col motivo. Ritorna quanti gruppi la
    #        funzione ha marcato.
    #
    # ⭐ PERCHE' PASSA DAL DATABASE E NON DA UN `UPDATE` QUI. La regola non
    #    banale e' UNA: quale riga marcare quando si ha in mano una commessa e
    #    non un gruppo — la funzione ritrova il gruppo **dentro quel lotto**.
    #    Riscriverla in Python vorrebbe dire due sedi della stessa regola, e la
    #    seconda e' quella che diverge.
    # ⚠️ Si passa il gruppo OPPURE la commessa: chi fallisce ha in mano la
    #    seconda.
    # ⛔ La funzione NON solleva mai, di proposito: sta annotando un fallimento
    #    gia' avvenuto, e un errore su di se' coprirebbe quello vero. ⇒ Il
    #    valore di ritorno E' il segnale, e va guardato: `0` vuol dire «non l'ho
    #    appeso a niente», cioe' il lotto continuera' a raccontare un errore su
    #    un documento che non mostra.
    def segna_esito_gruppo_lotto(
        self,
        lotto_id: int,
        stato: str,
        *,
        gruppo_key: str | None = None,
        commessa_id: int | None = None,
        errore_codice: str | None = None,
        errore_messaggio: str | None = None,
    ) -> EsitoMarcaturaGruppi:
        # ⛔ `SELECT * FROM`, non `SELECT fn(...)`: dal changeSet `20260909-20`
        #    la funzione e' una `RETURNS TABLE` a TRE colonne, e chiamata come
        #    scalare consegnerebbe la tupla intera in un campo solo — un valore
        #    plausibile e sbagliato, non un errore.
        # ⭐ TRE numeri perche' lo zero del marcatore aveva tre cause e ne
        #    raccontava una: nessun documento appeso, tutti gia' usciti dal
        #    giro, oppure fuori dal perimetro di questo lotto.
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT marcati, usciti, fuori_perimetro
                FROM vendite.fn_segna_esito_gruppo_lotto(
                    p_lotto_id         => %s,
                    p_stato            => %s,
                    p_gruppo_key       => %s,
                    p_commessa_id      => %s,
                    p_errore_codice    => %s,
                    p_errore_messaggio => %s)
                """,
                [lotto_id, stato, gruppo_key, commessa_id,
                 errore_codice, errore_messaggio],
            )
            row = cursor.fetchone()
        # ⚠️ Nessuna riga non capita — la funzione ne torna sempre una — ma lo
        #    zero e' la risposta sicura: fa scattare l'avviso del chiamante
        #    invece di far passare un giro muto.
        if not row:
            return {"marcati": 0, "usciti": 0, "fuori_perimetro": 0}
        return {
            "marcati": int(row[0] or 0),
            "usciti": int(row[1] or 0),
            "fuori_perimetro": int(row[2] or 0),
        }
