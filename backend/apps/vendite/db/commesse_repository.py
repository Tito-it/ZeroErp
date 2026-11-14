# ------------------------------------------------------------
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Accesso DB per dominio commesse (CRUD + pull AF + push sorgenti).
# ------------------------------------------------------------

from dataclasses import dataclass
from datetime import date
from decimal import Decimal
import json
from typing import Any, cast

from django.db import connection, transaction

from apps.config.sorgenti import (
    SORGENTE_ATTIVITA_CONSUMI,
    SORGENTE_CONTRATTO,
    SORGENTE_DDT_VENDITA,
    SORGENTE_ORDINE_VENDITA,
    SORGENTE_PREVENTIVO,
)
from apps.core.api.constants import DEFAULT_LIMIT, DEFAULT_LIMIT_EVENTI
from apps.core.db._helpers import call_jsonb_fn, jsonb_out, row_to_dict, limiti_pagina
from apps.core.db.sql_write_helpers import execute_dynamic_update
from apps.core.services.error_manager import ErrorManager
from apps.vendite.db._event_log_repo_mixin import EventLogRepositoryMixin
from apps.vendite.db._provenienza_prezzo import (
    COLONNA_DEL_LISTER,
    COLONNE_PROVENIENZA_PREZZO,
    PROVENIENZA_VUOTA,
    ProvenienzaPrezzo,
    provenienza_da_colonne,
)
from apps.vendite.db.vendite_repository import DASH_STADIO_DA_APPROVARE
from apps.vendite.types import (
    CommessaEmitResult,
    CommessaEmittibileLane,
    CommessaPushLogRow,
    CommessaRegistroEventoRow,
    CommessaStatoResult,
    CommessaTestataRow,
    GruppoDiagnosi,
    GruppoEsitoGiro,
)

# Le colonne di PROVENIENZA del prezzo di una riga di commessa, che
# `update_attivita_prezzo` scrive con il prezzo. ⭐ Sede unica dal 2026-11-14:
# la forma `ProvenienzaPrezzo` (`_provenienza_prezzo`), che il push riceve dai
# lister e passa alla riga di commessa; il building block
# `apps/vendite/services/prezzo_riga_commessa.py` le importa da qui
# (`CAMPI_PROVENIENZA`). Le prime nove esistono anche su
# `attivita_fatturabili`; `listino_versione_id` solo sulla riga di commessa.
# ⭐ `listino_riga_id` (2026-10-09, brief-db-riga-listino-propagata-dalla-
# commessa): la riga di listino che ha dato il prezzo. Scriverla la rende
# «propagata», cioe' immutabile (`trgfn_listini_righe_guard_stato`), finche'
# una riga la cita ADESSO (D-1 del brief).

# Repository SQL: incapsula accesso DB per commesse, commesse_attivita e push log.


# --- Mapping codice sorgente → fn SQL da chiamare ---
_SORGENTE_FN_MAP: dict[str, str] = {
    SORGENTE_PREVENTIVO: "vendite.fn_list_preventivi_da_pushare",
    SORGENTE_ORDINE_VENDITA: "vendite.fn_list_ordini_da_pushare",
    SORGENTE_ATTIVITA_CONSUMI: "vendite.fn_list_consumi_da_pushare",
    SORGENTE_CONTRATTO: "vendite.fn_list_contratti_da_pushare",
    SORGENTE_DDT_VENDITA: "vendite.fn_list_ddt_da_pushare",
}

# Sorgenti la cui fn_list_*_da_pushare espone il 5o parametro `p_righe_ids`
# (smistamento selettivo per sottoinsieme righe). Oggi solo PREVENTIVO
# (brief-db-smistamento-preventivi.md C); aggiungere qui quando le altre fn
# acquisiranno il parametro (sviluppo concentrico: la whitelist e' il punto
# unico di espansione).
_SORGENTE_SUPPORTA_RIGHE_IDS: frozenset[str] = frozenset({SORGENTE_PREVENTIVO})

# Colonne ordinabili della lista attivita' commessa: specchio della whitelist
# CHIUSA dentro vendite.fn_list_commessa_attivita (changeset 20260802-26), dove
# vivono ordine e paginazione — ordinare a valle ordinerebbe la sola pagina
# estratta. Il service valida qui (fail-fast, un solo round-trip); la fn resta
# l'autorita' e solleva E_PARAMETRO_INVALIDO su un nome fuori mappa.
# Livello modulo, non ClassVar: e' un dato, e un test che mocka la classe non
# deve poterla svuotare.
# Vocabolario di `commesse_attivita.tipo_movimento`, filtro della lista attivita
# (changeSet 20260820-09). ⚠️ E' uno SPECCHIO, non l'autorita': a enforcare e'
# il CHECK `chk_commesse_attivita_tipo_movimento`, e la fn ha la sua copia con
# una preCondition che si ferma se il CHECK cresce. Vale qui per la stessa
# ragione di ATTIVITA_SORT_COLUMNS: un valore fuori vocabolario si rifiuta
# PRIMA di spendere un round-trip, e l'utente vede un 400 dal posto giusto.
ATTIVITA_SORT_COLUMNS: frozenset[str] = frozenset({
    "id",
    "data_attivita",
    "competenza_mese",
    "segment_key",
    "quantita",
    "prezzo_snapshot",
    "stato_approvazione",
    "stato_emissione",
    # Aggiunte con le sette colonne del 2026-08-16 (changeSet 20260816-04):
    # `fatturata_il` e' la domanda da cui e' nata la richiesta — «fatturata
    # ieri o tre mesi fa» — e senza ordinamento la si risponde solo a occhio.
    "fatturata_il",
    "fattura_numero",
    # Sei nomi nuovi (changeSet 20260820-05). ⚠️ Questa whitelist e' lo SPECCHIO
    # di quella CHIUSA dentro la fn: una colonna dichiarata ordinabile a
    # catalogo su un nome che il DB non conosce non da' una freccia inerte,
    # ROMPE la lista al primo click (`E_PARAMETRO_INVALIDO`). Verificati uno per
    # uno contro il corpo della funzione, non contro il nome della colonna.
    "tipo_movimento",
    "articolo_codice",
    "articolo_descrizione",
    # ⭐ Dal 2026-10-21 (20261021-20, brief-db-grammatica-unica-documenti §13.6)
    # si ordina per ETICHETTA, quella che la colonna «Tipo origine» mostra: era
    # `sorgente_codice` (`config.sorgenti.codice`, il nome modificabile), uscito.
    "sorgente_etichetta",
    "sorgente_documento_numero",
    "gruppo_key",
})

# Nomi delle colonne condivise da tutte le fn_list_*_da_pushare.
# La colonna opzionale `riga_id` (presente in preventivi/ordini/contratti/ddt,
# assente in consumi) e' aggiunta al col_map a runtime dentro
# `fetch_pushable_rows` e mappata su `PushableRow.riga_sorgente_id`
# (refactor componenti 2026-05-11).
_PUSHABLE_SHARED_COLS = (
    "billing_account_id",
    "utility_id",
    "emittente_soggetto_ruolo_id",
    "competenza_dal",
    "competenza_al",
    "fatturazione_immediata",
    "sorgente_tipo_id",
    "sorgente_chiave",
    "segment_key",
    "articolo_id",
    "istanza_utility_id",
    "data_attivita",
    "uom_id",
    "quantita",
    "qta_operativa",
    "uom_operativa_id",
    "factor_to_base",
    "competenza_mese",
    "prezzo_snapshot",
    "prezzo_bloccato",
    "pricing_mode",
    "tipo_movimento",
    # ⛔ `tipo_consumo` ritirato dal DB il 2026-10-13 (20261013-60…-67,
    #    decisione A di Tid): due significati nella stessa colonna — il
    #    contratto ci metteva l'EROGAZIONE (UNA_TANTUM…), la madre accettava solo
    #    ACCONTO/CONGUAGLIO/STORNO, e nessuna riga di contratto entrava in
    #    commessa. L'erogazione del contratto viaggia in `meta.tipo_erogazione`.
    "valuta_id",
    "meta",
    "tipo_doc_fiscale_id",
    # Condizioni di pagamento del documento sorgente (contratto di push rev
    # 2026-08-03, changeset 20260803-02). ⚠️ Questa whitelist E' il cancello
    # del binding: una colonna esposta dalla fn ma assente qui non entra mai
    # in `col_map`, e il `col_map.get` a valle resta None IN SILENZIO — e'
    # successo davvero (smoke-push-termine-documento-commessa, test 0).
    "termine_pagamento_id",
    "modalita_pagamento_id",
    # La causale della riga ONERE (20261103-38/-40, brief-db-addebito-trasporto-
    # ordine §9.3): gli oneri sono righe di ordine e bolla, e la madre vuole
    # ONERE <=> causale. Solo ordini e bolle la espongono; per gli altri lister
    # resta None, ed e' giusto: le loro righe non sono ONERE.
    "causale_onere_id",
    # La provenienza del prezzo, in coda a ogni lister (giro 2 di brief-db-
    # provenienza-prezzo-segue-il-prezzo, `20261113-16 … -20`): obbligatoria,
    # anche per i consumi, che la restituiscono vuota (R-5).
    *COLONNA_DEL_LISTER.values(),
)

# Le colonne della whitelist che non ogni lister espone: `_map_pushable_row`
# le legge con tolleranza (assenti -> None) e SOLO loro; tutte le altre sono
# obbligatorie (`_col`, KeyError se mancano). Una sede per il binding e per il
# presidio sul catalogo (`test_commesse_porta_nomi_db`), che ne prova la forma
# contro le RETURNS TABLE dei cinque lister.
_PUSHABLE_OPTIONAL_COLS: frozenset[str] = frozenset({
    "termine_pagamento_id",
    "modalita_pagamento_id",
    "causale_onere_id",
})


# --- Risultati upsert ---


@dataclass(frozen=True)
class UpsertAttivitaResult:
    """Risultato singolo di fn_upsert_commessa_attivita (attivita_id, is_new)."""

    attivita_id: int
    is_new: bool


@dataclass(frozen=True)
class ErroreBatchAttivita:
    """Il rifiuto di UNA riga di fn_batch_upsert_commessa_attivita.

    Scopo: la forma dell'errore che il batch del DB consegna (20261112-26), letta
           una volta qui e non a chiavi sparse nei consumatori. `index`,
           `segment_key` ed `error` (la frase) ci sono sempre; `sqlstate` sempre
           dal 2026-11-12; `codice` e `campo` solo per un errore di DOMINIO
           (`script.fn_codice_dominio`: P0001 col CONSTRAINT). Un errore tecnico
           (un cast, un vincolo) ha `codice` e `campo` a None: e' un caso del
           modello, non un difetto.
    """

    index: int | None
    segment_key: str | None
    error: str
    sqlstate: str | None = None
    codice: str | None = None
    campo: str | None = None

    # Scopo: un elemento dell'array `errors` del DB → record. Le chiavi assenti
    #        (il DB le toglie con jsonb_strip_nulls) diventano None.
    @classmethod
    def da_jsonb(cls, raw: dict) -> "ErroreBatchAttivita":
        index = raw.get("index")
        return cls(
            index=int(index) if index is not None else None,
            segment_key=raw.get("segment_key"),
            error=str(raw.get("error") or ""),
            sqlstate=raw.get("sqlstate"),
            codice=raw.get("codice"),
            campo=raw.get("campo"),
        )


@dataclass(frozen=True)
class BatchUpsertResult:
    """Risultato batch di fn_batch_upsert_commessa_attivita."""

    total_rows: int
    inserted: int
    updated: int
    errors: list[ErroreBatchAttivita]


# --- Costanti dominio commesse (valori allineati ai DEFAULT delle fn SQL) ---
TIPO_COMMESSA_AUTO = "AUTO"
POLICY_FATTURAZIONE_DA_DOCUMENTO = "DA_DOCUMENTO"
PRIORITA_OPERATIVA_NORMALE = "NORMALE"
PRICING_MODE_FIXED = "FIXED"
STATO_APPROVAZIONE_BOZZA = "BOZZA"
STATO_EMISSIONE_NON_EMESSA = "NON_EMESSA"
TIPO_MOVIMENTO_NORMALE = "NORMALE"
# Vocabolario di `tipo_movimento`, presidiato dai CHECK `chk_*_tipo_movimento` su
# ENTRAMBE le tabelle della catena (commesse_attivita e attivita_fatturabili):
# NORMALE | RETTIFICA | ONERE. La rettifica e' la riga della nota di credito —
# quantita' NEGATIVA, prezzo copiato dalla riga di fattura rettificata.
TIPO_MOVIMENTO_RETTIFICA = "RETTIFICA"

# Il vocabolario intero, per il filtro della lista attivita' (changeSet
# 20260820-09). ⚠️ E' uno SPECCHIO, non l'autorita': a enforcare e' il CHECK, e
# la fn ha la sua copia con una preCondition che si ferma se il CHECK cresce.
# Vale qui per la stessa ragione di ATTIVITA_SORT_COLUMNS: un valore fuori
# vocabolario si rifiuta PRIMA di spendere un round-trip.
TIPO_MOVIMENTO_VALUES: frozenset[str] = frozenset(
    {"NORMALE", TIPO_MOVIMENTO_RETTIFICA, "ONERE"}
)

# I vocabolari di emissione e approvazione di una riga di commessa, per i
# filtri della lista attivita': SPECCHI dei CHECK
# `chk_commesse_attivita_stato_emissione` / `_stato_approvazione`, che il
# guardrail `test_specchi_dei_check_db` confronta col database (2026-10-20:
# prima il filtro andava nel WHERE senza controllo, e un valore sbagliato
# rispondeva lista vuota).
STATI_EMISSIONE_ATTIVITA: tuple[str, ...] = (STATO_EMISSIONE_NON_EMESSA, "EMESSA", "ANNULLATA")
STATI_APPROVAZIONE_ATTIVITA: tuple[str, ...] = (STATO_APPROVAZIONE_BOZZA, "APPROVATA", "RIFIUTATA")

# Il tetto della lista attivita': quello che la fn DB applica da se' su
# `p_limit`. Il tetto di PAGINA (`MAX_LIMIT`) NON sta qui — vive nel service, dove e'
# un errore parlante invece di un troncamento muto.
_ATTIVITA_EXPORT_MAX_ROWS = 10_000

# Tetto della QUERY del registro. ⚠️ Non e' il tetto di PAGINA (200, nel service):
# quello risponde 400 e DICE il limite a chi ha chiesto troppo, questo clampa in
# silenzio ed esiste solo perche' un chiamante interno non possa tirare fuori
# l'intero log di una commessa grande in un colpo. Due regole diverse, due sedi.
# ⛔ Aveva un nome? No: era un `500` scritto in mezzo alla lista dei parametri,
# dove un tetto non si vede e nessuno lo trova quando serve cambiarlo.
_REGISTRO_QUERY_MAX_ROWS = 500


@dataclass(frozen=True)
class CommessaAttivitaInput:
    """Input per fn_upsert_commessa_attivita — tutti i campi della riga operativa.

    Campi obbligatori (senza default) prima; opzionali (con default) dopo.
    I default sono allineati ai DEFAULT della fn_upsert_commessa_attivita.
    """

    # === Campi obbligatori (sempre presenti dalle fn_list) ===
    commessa_id: int
    segment_key: str
    quantita: Decimal
    competenza_mese: date
    articolo_id: Any | None  # UUID dal DB; None per consumi (handler risolve)
    prezzo_snapshot: Decimal | None  # None per consumi (calcolato da listino)

    # === Campi con default — allineati a fn_upsert_commessa_attivita ===
    uom_id: int | None = None  # #3: nullable (handler risolve da catalogo)
    tipo_doc_fiscale_id: int | None = None  # #4: default da config
    valuta_id: int | None = None  # None per consumi/contratti
    prezzo_bloccato: bool = False
    pricing_mode: str = PRICING_MODE_FIXED
    prezzo_da_riallineare: bool = False  # #5: default False
    stato_approvazione: str = STATO_APPROVAZIONE_BOZZA
    stato_emissione: str = STATO_EMISSIONE_NON_EMESSA
    tipo_movimento: str = TIPO_MOVIMENTO_NORMALE
    # Valorizzata se e solo se tipo_movimento = ONERE (guard della madre).
    causale_onere_id: int | None = None

    # === Campi opzionali ===
    istanza_utility_id: int | None = None
    data_attivita: date | None = None
    competenza_dal: date | None = None
    competenza_al: date | None = None
    qta_operativa: Decimal | None = None
    uom_operativa_id: int | None = None
    factor_to_base: Decimal | None = None
    posticipa_al: date | None = None
    area_geografica_id: int | None = None
    listino_versione_id: int | None = None
    listino_riga_id: int | None = None  # la riga di listino del prezzo (la rende «propagata»)
    sorgente_tipo_id: int | None = None
    # ⭐ La chiave del documento d'origine COME LA HA CHI CHIAMA, in testo: l'id
    #    o l'uid, secondo il tipo. La madre la traduce nella colonna del suo
    #    `key_selector` (`script.fn_sorgente_chiave`). Fino al giro K.1 di
    #    brief-db-sorgente-documento-e-riga (2026-11-07) si chiamava
    #    `sorgente_uid`, come il parametro della madre: un nome che diceva
    #    «uid» anche quando portava un id.
    sorgente_chiave: str | None = None
    # ⭐ La RIGA del documento d'origine (dal giro C.3 di
    #    brief-db-sorgente-documento-e-riga, BE-C.3-a). None = provenienza dal
    #    documento intero (consumi, quote fisse del listino di un contratto):
    #    il guard la ammette, ma una riga che ce l'ha e non la passa perde la
    #    sua provenienza.
    sorgente_riga: int | None = None
    meta: dict[str, Any] | None = None

    # === Snapshot pricing v5 (F2-BE-11) ===
    # Firma fn_upsert_commessa_attivita li dichiara obbligatori: vanno passati
    # sempre, anche come NULL esplicito quando la dimensione non si applica
    # (es. classe_utenza per utility commercio, contratto per origine CATEGORIA).
    # La popolazione effettiva e' a carico di F2-BE-12 (wiring pricing_service
    # nei source handlers); per ora i caller passano None.
    prezzo_base_snapshot: Decimal | None = None
    origine_prezzo: str | None = None  # PROMO|CONTRATTO_OVERRIDE|CONTRATTO_LISTINO|CATEGORIA|MANUALE
    tipo_variazione_applicata: str | None = None  # PERCENTUALE|VALORE_FISSO|PREZZO_FISSO|NESSUNA
    valore_variazione_applicata: Decimal | None = None
    promo_id: int | None = None
    contratto_id: int | None = None
    categoria_cliente_id_snapshot: int | None = None
    classe_utenza_id_snapshot: int | None = None


@dataclass(frozen=True)
class PushableRow:
    """Riga normalizzata da fn_list_*_da_pushare — le colonne condivise."""

    billing_account_id: int
    utility_id: int | None
    emittente_soggetto_ruolo_id: int
    competenza_dal: date | None
    competenza_al: date | None
    fatturazione_immediata: bool
    sorgente_tipo_id: int
    # La chiave del documento d'origine come la restituisce il lister (l'uid
    # del documento in testo, per ogni tipo), con lo stesso nome della colonna
    # (giro K.2 di brief-db-sorgente-documento-e-riga, BE-K.2-a), del campo di
    # `CommessaAttivitaInput` e della chiave del batch: un nome solo, nessun
    # punto che traduce.
    sorgente_chiave: str
    segment_key: str
    articolo_id: Any  # UUID o None (consumi)
    istanza_utility_id: int | None
    data_attivita: date | None
    uom_id: int | None
    quantita: Decimal | None
    qta_operativa: Decimal | None
    uom_operativa_id: int | None
    factor_to_base: Decimal | None
    competenza_mese: date
    prezzo_snapshot: Decimal | None
    prezzo_bloccato: bool
    pricing_mode: str
    tipo_movimento: str
    valuta_id: int | None
    meta: dict[str, Any]
    tipo_doc_fiscale_id: int | None
    # ID della riga sorgente (es. `preventivi_righe.id`, `ordini_righe.id`).
    # Popolato dalle fn DB che lo espongono — None per sorgenti che non
    # hanno granularita' riga (es. CONSUMI) o nei test legacy senza override.
    # Usato dal BoMComponentExpander per leggere componenti pre-popolati su
    # `<sorgente>_righe_componenti` (refactor componenti 2026-05-11) invece
    # di chiamare il resolver al push. Default None per backward compat.
    riga_sorgente_id: int | None = None
    # Condizioni di pagamento del DOCUMENTO SORGENTE, propagate alla commessa
    # (D-R: il termine vive sulla commessa ed entra nella sua chiave).
    # ⚠️ Oggi `fn_list_*_da_pushare` NON le espone (verificato 2026-08-03: 29
    # colonne, nessuna delle due), quindi restano None e la propagazione e'
    # INERTE: si accende da se' quando il DB aggiungera' le colonne, senza
    # altre modifiche qui. Il default None e' quindi voluto, non difensivo.
    # NON si risolvono in Python: qui si COPIA il valore del documento, non si
    # percorre la cascata — un secondo risolutore divergerebbe in silenzio
    # (brief scadenze §8).
    termine_pagamento_id: int | None = None
    modalita_pagamento_id: int | None = None
    # La causale della riga ONERE (righe-onere di ordini e bolle). None per i
    # lister che non la espongono: preventivi, contratti e consumi.
    causale_onere_id: int | None = None
    # ⭐ La provenienza del prezzo, come la dice la riga del documento (K-1):
    #    il push la copia nella riga di commessa, non la ricostruisce. Un
    #    componente di kit ha la sua (`BoMComponentExpander`).
    provenienza: ProvenienzaPrezzo = PROVENIENZA_VUOTA


def _map_pushable_row(col_map: dict[str, int], row: tuple) -> PushableRow:
    """Scopo: converte una tupla cursor in PushableRow usando la mappa colonne per nome."""
    def _col(name: str) -> Any:
        return row[col_map[name]]

    meta_raw = jsonb_out(_col("meta")) or {}

    # Guard: sorgente_chiave e segment_key devono essere non-null dal DB.
    raw_sorgente_chiave = _col("sorgente_chiave")
    raw_segment_key = _col("segment_key")
    if raw_sorgente_chiave is None or raw_segment_key is None:
        raise ValueError(
            f"sorgente_chiave o segment_key NULL dal DB: "
            f"sorgente_chiave={raw_sorgente_chiave!r}, segment_key={raw_segment_key!r}"
        )

    # ⛔ Il fattore passa COM'E', anche NULL (BE23 di brief-db-revisione-catalogo,
    #    D26, 2026-11-11). Fino a quel giorno qui un NULL diventava 1: giusto
    #    quando la quantita' e' gia' nella base, ma una riga senza fattore in
    #    un'altra unita' passava come se lo fosse (3 cartoni -> 3 pezzi), senza
    #    rifiuto. Lo decide il DB (`vendite.trgfn_attivita_fattore_alla_data`):
    #    il fattore scritto si rispetta, senza si legge alla data dell'attivita',
    #    e senza nemmeno quello e' `E_UOM_MISSING`.
    factor_to_base = _col("factor_to_base")

    # riga_sorgente_id mappato dalla colonna `riga_id` se presente nella fn DB.
    # Le fn `fn_list_preventivi_da_pushare`/`fn_list_ordini_da_pushare`/etc.
    # lo espongono; CONSUMI no -> None default. `col_map.get` evita KeyError.
    riga_sorgente_id_raw = (
        row[col_map["riga_id"]] if "riga_id" in col_map else None
    )

    # Condizioni di pagamento del documento sorgente. La lettura tollerante
    # (`nome not in col_map` -> None) resta per le fn che non esponessero la
    # colonna, ma NON basta da sola: `col_map` contiene solo i nomi in
    # `_PUSHABLE_SHARED_COLS`, quindi ogni colonna nuova del contratto va
    # aggiunta ANCHE alla whitelist o il binding resta muto (lezione del
    # 2026-08-03: la prima stesura si fermo' qui e lo smoke la scopri').
    def _opt_int(nome: str) -> int | None:
        # Una lettura tollerante fuori dall'elenco renderebbe muta una colonna
        # obbligatoria: il presidio sul catalogo non la vedrebbe.
        if nome not in _PUSHABLE_OPTIONAL_COLS:
            raise RuntimeError(f"colonna {nome!r} letta come opzionale ma non dichiarata tale")
        if nome not in col_map:
            return None
        valore = row[col_map[nome]]
        return int(valore) if valore is not None else None

    return PushableRow(
        billing_account_id=_col("billing_account_id"),
        utility_id=_col("utility_id"),
        emittente_soggetto_ruolo_id=_col("emittente_soggetto_ruolo_id"),
        competenza_dal=_col("competenza_dal"),
        competenza_al=_col("competenza_al"),
        fatturazione_immediata=bool(_col("fatturazione_immediata")),
        sorgente_tipo_id=_col("sorgente_tipo_id"),
        sorgente_chiave=str(raw_sorgente_chiave),
        riga_sorgente_id=(
            int(riga_sorgente_id_raw) if riga_sorgente_id_raw is not None else None
        ),
        segment_key=str(raw_segment_key),
        articolo_id=_col("articolo_id"),
        istanza_utility_id=_col("istanza_utility_id"),
        data_attivita=_col("data_attivita"),
        uom_id=_col("uom_id"),
        quantita=_col("quantita"),
        qta_operativa=_col("qta_operativa"),
        uom_operativa_id=_col("uom_operativa_id"),
        factor_to_base=factor_to_base,
        competenza_mese=_col("competenza_mese"),
        prezzo_snapshot=_col("prezzo_snapshot"),
        prezzo_bloccato=bool(_col("prezzo_bloccato")),
        pricing_mode=str(_col("pricing_mode")),
        tipo_movimento=str(_col("tipo_movimento")),
        valuta_id=_col("valuta_id"),
        meta=meta_raw,
        tipo_doc_fiscale_id=_col("tipo_doc_fiscale_id"),
        termine_pagamento_id=_opt_int("termine_pagamento_id"),
        modalita_pagamento_id=_opt_int("modalita_pagamento_id"),
        causale_onere_id=_opt_int("causale_onere_id"),
        provenienza=provenienza_da_colonne(_col),
    )


# La testata nella mappa del modello del documento (`script.fn_doc_stato_modello`),
# come `TESTATA_<DOC>` degli altri repository.
TESTATA_COMMESSE = "vendite.commesse"


class CommesseRepository(EventLogRepositoryMixin):
    """Wrapper SQL a basso livello per il dominio commesse."""

    @staticmethod
    def _to_jsonb_param(value: Any) -> str | None:
        if value is None:
            return None
        return json.dumps(value)

    # --- Gruppo 0: Fetch righe sorgente per push ---

    @staticmethod
    def validate_sorgente_map() -> list[str]:
        """Verifica _SORGENTE_FN_MAP contro config.sorgenti (scope=PUSH_COMMESSA).

        Restituisce lista di warning (vuota = tutto OK).
        Utile come safety-net a startup o nei test di integrazione.
        """
        warnings: list[str] = []
        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT COALESCE(codice_interno, codice) AS codice FROM config.sorgenti"
                " WHERE scope = 'PUSH_COMMESSA' AND attivo = true"
            )
            db_codici = {row[0] for row in cursor.fetchall()}

        map_codici = set(_SORGENTE_FN_MAP.keys())
        missing = db_codici - map_codici
        extra = map_codici - db_codici
        if missing:
            warnings.append(
                f"Sorgenti PUSH_COMMESSA nel DB ma non in _SORGENTE_FN_MAP: {sorted(missing)}"
            )
        if extra:
            warnings.append(
                f"Codici in _SORGENTE_FN_MAP ma non nel DB (scope PUSH_COMMESSA): {sorted(extra)}"
            )
        return warnings

    @staticmethod
    def list_active_push_sources() -> list[str]:
        """Codici sorgente attivi per scope PUSH_COMMESSA, ordinati per id registrazione."""
        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT COALESCE(codice_interno, codice) AS codice FROM config.sorgenti"
                " WHERE scope = 'PUSH_COMMESSA' AND attivo = true"
                " ORDER BY id"
            )
            return [row[0] for row in cursor.fetchall()]

    # Scopo: invoca la fn_list_<sorgente>_da_pushare parametrizzata e restituisce
    # le righe normalizzate come PushableRow. Unico punto di accesso per tutti gli handler.
    # `sorgente_id` (opzionale) restringe la query alla riga sorgente del documento
    # specifico (es. preventivo_id per sorgente PREVENTIVO): None = lista globale del
    # batch orchestrator, valorizzato = push singolo UI-driven. Allinea col 4o param
    # `p_<sorgente>_id DEFAULT NULL` aggiunto alle fn DB lato `dev/db-tid` (vedi
    # docs/it/dev/work-in-progress/brief-db-fn-list-preventivi-push-singolo.md).
    def fetch_pushable_rows(
        self,
        sorgente_codice: str,
        *,
        competenza_mese: date | None = None,
        billing_account_id: int | None = None,
        limit: int | None = None,
        sorgente_id: int | None = None,
        righe_ids: list[int] | None = None,
    ) -> list[PushableRow]:
        """Chiama fn_list_<sorgente>_da_pushare e restituisce PushableRow normalizzati."""
        fn_name = _SORGENTE_FN_MAP.get(sorgente_codice)
        ErrorManager.require(
            fn_name is not None,
            code="E_COMMESSA_SORGENTE_SCONOSCIUTA",
            message=f"Sorgente '{sorgente_codice}' non supportata per push",
        )
        assert fn_name is not None
        # `righe_ids` (sottoinsieme righe, smistamento selettivo dal Pannello
        # Smistamento): 5o parametro `p_righe_ids` disponibile solo sulle fn
        # delle sorgenti in _SORGENTE_SUPPORTA_RIGHE_IDS (oggi PREVENTIVO,
        # brief-db-smistamento-preventivi.md C). Guard esplicito: estendere la
        # whitelist quando le altre fn acquisiranno il parametro.
        ErrorManager.require(
            righe_ids is None or sorgente_codice in _SORGENTE_SUPPORTA_RIGHE_IDS,
            code="E_COMMESSA_VALIDATION",
            message="Filtro righe non supportato per questa sorgente.",
            detail=f"sorgente_codice={sorgente_codice} non supporta righe_ids",
        )

        # 4 param posizionali base (il 4o e' il filtro per id sorgente,
        # DEFAULT NULL lato DB se omesso ma qui sempre passato) + 5o
        # `p_righe_ids` SOLO quando valorizzato: le fn delle altre sorgenti
        # hanno 4 parametri e il 5o le romperebbe.
        placeholders = "%s, %s, %s, %s"
        params: list = [competenza_mese, billing_account_id, limit, sorgente_id]
        if righe_ids is not None:
            placeholders += ", %s::bigint[]"
            params.append(righe_ids)

        with connection.cursor() as cursor:
            cursor.execute(
                f"SELECT * FROM {fn_name}({placeholders})",  # noqa: S608 — fn_name da whitelist
                params,
            )
            # Costruisce mappa colonna → indice per estrarre solo le 25 condivise.
            col_names = [desc[0] for desc in cursor.description]
            col_map = {name: idx for idx, name in enumerate(col_names) if name in _PUSHABLE_SHARED_COLS}
            # Include `riga_id` opzionalmente: alcune fn lo espongono
            # (preventivi/ordini/contratti/ddt), CONSUMI no. Serve al
            # BoMComponentExpander per leggere componenti pre-popolati
            # nelle tabelle `<sorgente>_righe_componenti` (refactor 2026-05-11).
            if "riga_id" in col_names:
                col_map["riga_id"] = col_names.index("riga_id")
            rows = cursor.fetchall()

        return [_map_pushable_row(col_map, row) for row in rows]

    # --- Gruppo 1: Commessa ---

    # Scopo: risolve o crea una commessa. Restituisce commessa_id.
    # Default allineati a fn_get_or_create_commessa.
    def get_or_create_commessa(
        self,
        *,
        billing_account_id: int,
        utility_id: int | None = None,
        tipo_commessa: str = TIPO_COMMESSA_AUTO,
        policy_fatturazione: str = POLICY_FATTURAZIONE_DA_DOCUMENTO,
        fatturazione_immediata: bool = False,
        priorita_operativa: str = PRIORITA_OPERATIVA_NORMALE,
        competenza_dal: date | None = None,
        competenza_al: date | None = None,
        meta: dict | None = None,
        force_new: bool = False,
        termine_pagamento_id: int | None = None,
        modalita_pagamento_id: int | None = None,
    ) -> int:
        """Risolve o crea una commessa. Restituisce commessa_id.

        `termine_pagamento_id`/`modalita_pagamento_id` sono le condizioni di
        pagamento del DOCUMENTO SORGENTE: la commessa le POSSIEDE (D-R) e da
        li' la catena `fn_resolve_termini_pagamento` le porta in fattura.
        `fn_get_or_create_commessa` accettava gia' i due parametri; il BE non
        li passava, ed e' il difetto che faceva uscire ogni fattura col
        termine del CLIENTE anche quando l'ordine ne dichiarava un altro.

        ⭐ L'EMITTENTE NON SI PASSA, e dal 2026-08-26 non si puo' nemmeno:
        `p_emittente_soggetto_ruolo_id` e' stato tolto dalla firma della
        funzione (changeSet `20260826-52`). Non e' un attributo della
        commessa ma la sua CHIAVE DI PERIMETRO — ci si appoggiano la RLS
        della tabella e il filtro di scope delle viste — e si deriva sempre
        dal billing account (`anagrafiche.fn_get_emittente_fiscale_id`).
        Il valore che il BE ri-passava era quello che il database gli aveva
        appena dato dalle `fn_list_*_da_pushare`: un giro in piu' che, con
        il guard emittente <-> BA in servizio (dal 2026-10-10 il BB
        `script.trgfn_doc_guard_emittente_ba`), poteva
        solo essere ridondante o sbagliato.
        Piano: `brief-db-emittente-commessa-invariante` (D-2, lotto L5).
        """
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT vendite.fn_get_or_create_commessa(
                    p_billing_account_id => %s,
                    p_utility_id => %s,
                    p_tipo_commessa => %s,
                    p_policy_fatturazione => %s,
                    p_fatturazione_immediata => %s,
                    p_priorita_operativa => %s,
                    p_competenza_dal => %s,
                    p_competenza_al => %s,
                    p_meta => %s::jsonb,
                    p_force_new => %s,
                    p_termine_pagamento_id => %s,
                    p_modalita_pagamento_id => %s
                )
                """,
                [
                    billing_account_id,
                    utility_id,
                    tipo_commessa,
                    policy_fatturazione,
                    fatturazione_immediata,
                    priorita_operativa,
                    competenza_dal,
                    competenza_al,
                    self._to_jsonb_param(meta),
                    force_new,
                    termine_pagamento_id,
                    modalita_pagamento_id,
                ],
            )
            row = cursor.fetchone()
        assert row is not None
        return int(row[0])

    def approva_commessa_attivita(
        self,
        *,
        commessa_id: int,
        righe_ids: list[int] | None = None,
        user: str | None = None,
    ) -> int:
        """Porta le righe commessa BOZZA→APPROVATA (righe_ids NULL = tutte le
        NON_EMESSA). Idempotente. Restituisce il numero di righe approvate.
        Wrapper di vendite.fn_approva_commessa_attivita (macchina transizioni)."""
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT vendite.fn_approva_commessa_attivita(
                    p_commessa_id => %s,
                    p_righe_ids => %s,
                    p_user => %s
                )
                """,
                [commessa_id, righe_ids, user],
            )
            row = cursor.fetchone()
        assert row is not None
        return int(row[0])

    # Scopo: Wrapper 1:1 della madre DB `vendite.fn_aggiungi_onere_commessa`
    #        (riga onere APPROVATA+NON_EMESSA + audit in una SELECT atomica).
    def aggiungi_onere(
        self,
        *,
        commessa_id: int,
        istanza_utility_id: int,
        articolo_onere_id: str,
        importo: Decimal,
        tipo_doc_fiscale_id: int,
        motivo: str | None = None,
        data_attivita: date | None = None,
    ) -> int:
        """Porta oneri: crea una riga di puro valore sulla commessa (qta=1,
        tipo_movimento=ONERE, gia' APPROVATA, sourceless) e restituisce
        l'attivita_id. Wrapper 1:1 della madre DB
        `vendite.fn_aggiungi_onere_commessa` (brief-db-immutabilita-quantita-e-
        porta-oneri §4c): causale, uom e IVA sono derivate dall'articolo-onere
        dalla fn, non dal Python — qui nessuna regola di dominio duplicata.

        Un'unica SELECT di funzione madre = unita' atomica per costruzione
        (riga + log audit dentro la stessa fn): niente transaction.atomic nel
        service (api.md §Atomicita' e composizione di scritture)."""
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT vendite.fn_aggiungi_onere_commessa(
                    p_commessa_id => %s,
                    p_istanza_utility_id => %s,
                    p_articolo_onere_id => %s::uuid,
                    p_importo => %s,
                    p_tipo_doc_fiscale_id => %s,
                    p_motivo => %s,
                    p_data_attivita => %s
                )
                """,
                [commessa_id, istanza_utility_id, articolo_onere_id, importo,
                 tipo_doc_fiscale_id, motivo, data_attivita],
            )
            row = cursor.fetchone()
        assert row is not None
        return int(row[0])

    # Scopo: Wrapper 1:1 della madre DB `vendite.fn_annulla_commessa_attivita`
    #        (UPDATE stato -> ANNULLATA + INSERT evento di log, atomici).
    def annulla_attivita(self, *, attivita_id: int, motivo: str) -> int:
        """Annulla una riga MANUALE di commessa: non cancella nulla, porta
        `stato_emissione` ad `ANNULLATA` e scrive l'evento
        `RIGA_MANUALE_ANNULLATA` su `commesse_attivita_log`. Restituisce
        l'`attivita_id`.

        La madre applica i propri guard (gia' annullata / non manuale / gia'
        emessa / motivo obbligatorio) sotto `SELECT ... FOR UPDATE`, quindi e'
        anche la difesa contro due annullamenti concorrenti. Una sola SELECT di
        funzione = unita' atomica per costruzione: niente `transaction.atomic`
        nel service (api.md §Atomicita' e composizione di scritture).

        NB: la madre NON conosce la commessa — lo scoping riga<->commessa
        (l'`id` nell'URL) e' a carico del service."""
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT vendite.fn_annulla_commessa_attivita(
                    p_commessa_attivita_id => %s,
                    p_motivo => %s
                )
                """,
                [attivita_id, motivo],
            )
            row = cursor.fetchone()
        assert row is not None
        return int(row[0])

    # Scopo: Attivita' in stadio DA_APPROVARE del mese di competenza, raggruppate
    #        per commessa, per l'approvazione massiva A-2 (WYSIWYG con la card).
    def list_da_approvare_per_competenza(
        self,
        *,
        competenza_mese: date,
        commessa_ids: list[int] | None = None,
    ) -> list[tuple[int, list[int]]]:
        """Attivita' in stadio DA_APPROVARE per il mese di competenza, raggruppate
        per commessa: [(commessa_id, [attivita_ids]), ...].

        Legge vendite.vw_dash_competenza_attivita — la STESSA vista del drill-down
        della Lente 1 — cosi' l'approvazione massiva copre esattamente cio' che la
        card DA_APPROVARE mostra (WYSIWYG) e lo scope emittente e' applicato
        in-vista (GUC app.current_user_id, security_invoker)."""
        where_clauses = [
            "stadio = %s",
            "competenza_mese = date_trunc('month', %s::date)::date",
        ]
        params: list[Any] = [DASH_STADIO_DA_APPROVARE, competenza_mese]
        if commessa_ids:
            where_clauses.append("commessa_id = ANY(%s)")
            params.append(commessa_ids)
        where_sql = " AND ".join(where_clauses)
        with connection.cursor() as cursor:
            cursor.execute(
                f"""
                SELECT commessa_id,
                       array_agg(commessa_attivita_id ORDER BY commessa_attivita_id)
                FROM vendite.vw_dash_competenza_attivita
                WHERE {where_sql}
                GROUP BY commessa_id
                ORDER BY commessa_id
                """,  # noqa: S608 — where_clauses da letterali interni parametrizzati
                params,
            )
            raw = cursor.fetchall()
        return [(int(r[0]), [int(i) for i in r[1]]) for r in raw]

    # Scopo: Il verbo del cambio di stato della commessa
    #        (`vendite.fn_cambia_stato_commessa`, brief-modello-documento-
    #        vendita §14): la prima riga comune (stato che ha gia', passaggio di
    #        processo, azione della riga), poi la scrittura attraverso la
    #        porta; matrice e condizioni le giudica il guard. Senza `p_user`
    #        (C-4): chi scrive lo dice l'audit dalla sessione.
    # Ritorna: {commessa_id, stato_da, stato_a} (codici).
    def cambia_stato_commessa(self, *, commessa_id: int, nuovo_stato: str) -> dict[str, Any]:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT commessa_id, stato_da, stato_a
                FROM vendite.fn_cambia_stato_commessa(
                    p_commessa_id => %s,
                    p_stato => %s
                )
                """,
                [commessa_id, nuovo_stato],
            )
            row = cursor.fetchone()
        assert row is not None
        return {"commessa_id": int(row[0]), "stato_da": row[1], "stato_a": row[2]}

    # Scopo: Annulla la commessa via il verbo DB `vendite.fn_annulla_commessa`
    #        (brief-db-annullo-a-valle-riapre-a-monte D-1/D-2): prima cio' che
    #        vieta (righe EMESSA: E_COMMESSA_ANNULLA_CON_RIGHE_EMESSE), poi la
    #        conferma — con righe NON_EMESSA `legami_confermati` dichiara quanti
    #        legami l'operatore ha visto; se non corrisponde,
    #        E_DOC_ANNULLO_CON_LEGAMI — poi il ritiro (il documento o il consumo
    #        tornano da mandare, il reso da accreditare, gli oneri si annullano)
    #        e lo stato ANNULLATA. Una transazione, a DB.
    # Ritorna: i legami confermati (0 se non ce n'erano).
    def annulla(self, commessa_id: int, legami_confermati: int | None) -> int:
        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT vendite.fn_annulla_commessa(%s, %s)",
                [int(commessa_id), legami_confermati],
            )
            row = cursor.fetchone()
            return int(row[0]) if row and row[0] is not None else 0

    # Scopo: Dopo un invio in commessa, approva le righe dell'invio e porta la
    #        commessa a PRONTA_FATTURAZIONE: madre DB
    #        `vendite.fn_rendi_commessa_emittibile` (D-10, R-9 di
    #        brief-db-annullo-a-valle-riapre-a-monte). `righe_ids`: None =
    #        nessun filtro; [] = nessuna riga di questo invio, niente
    #        approvazione ma la testata va comunque pronta; pieno = le sole
    #        righe dell'invio. Gia' pronta: la madre non ritenta; CHIUSA o
    #        ANNULLATA: la matrice rifiuta forte.
    # Ritorna: le righe approvate.
    def rendi_commessa_emittibile(
        self,
        *,
        commessa_id: int,
        righe_ids: list[int] | None = None,
        user: str | None = None,
    ) -> int:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT vendite.fn_rendi_commessa_emittibile(
                    p_commessa_id => %s,
                    p_righe_ids => %s::bigint[],
                    p_user => %s
                )
                """,
                [commessa_id, righe_ids, user],
            )
            row = cursor.fetchone()
        assert row is not None
        return int(row[0] or 0)

    def get_commessa_viva_by_sorgente(
        self,
        *,
        sorgente_codice: str,
        sorgente_id: int | None = None,
        sorgente_uid: str | None = None,
    ) -> int | None:
        """La commessa APERTA in cui sta un documento sorgente, o None.

        Wrapper di `vendite.fn_commessa_viva_di_sorgente`: un documento puo'
        avere piu' link (quelli verso commesse chiuse o annullate restano
        come storia, D-12 di brief-db-annullo-a-valle-riapre-a-monte), e
        quale conta lo dice il DB. Il documento si nomina con le sue DUE
        chiavi, come le tiene il link dal giro C.2 di
        brief-db-sorgente-documento-e-riga (BE-C.2-a): `sorgente_uid` per i
        tipi a uid (il preventivo), `sorgente_id` per ordine, contratto, bolla
        e consumi. Chi ha il documento può passarle entrambe: l'incontro lo fa
        la funzione, con la regola del modello. Fino a quel giorno era una
        chiave testuale sola (`sorgente_chiave`).

        ⛔ Niente `SELECT` propria su `commesse_sorgenti`: quella di prima
        (`LIMIT 1` senza stato) con due link poteva dare la commessa morta.

        Codice sorgente sconosciuto → `E_COMMESSA_SORGENTE_SCONOSCIUTA`, non
        None: «nessuna commessa aperta» e «sorgente sbagliata» non si
        confondono (un codice errato farebbe saltare l'aggancio in silenzio)."""
        sql = """
            SELECT vendite.fn_commessa_viva_di_sorgente(s.id, %s::bigint, %s::uuid)
            FROM config.sorgenti s
            WHERE s.codice_interno = %s
        """
        with connection.cursor() as cursor:
            cursor.execute(sql, [
                None if sorgente_id is None else int(sorgente_id),
                sorgente_uid,
                sorgente_codice,
            ])
            row = cursor.fetchone()
        ErrorManager.require(
            row is not None,
            code="E_COMMESSA_SORGENTE_SCONOSCIUTA",
            message=f"Sorgente '{sorgente_codice}' non presente in config.sorgenti",
        )
        assert row is not None
        return int(row[0]) if row[0] is not None else None

    def get_commessa_stato(self, commessa_id: int) -> CommessaStatoResult | None:
        """Stato testata + flag di governance + contatori della commessa in un
        round-trip. Espone tutti i campi prodotti da `fn_get_commessa_stato`
        (flag chiude/emittibile/modificabile, config testata, contatori righe):
        servono alla UI commesse per stato e azioni senza chiamate extra."""

        def _int(v: Any) -> int | None:
            return int(v) if v is not None else None

        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT stato_commessa_id, stato_commessa,
                       chiude_commessa, emittibile, modificabile,
                       policy_fatturazione, fatturazione_immediata, priorita_operativa,
                       billing_account_id, utility_id, emittente_soggetto_ruolo_id,
                       total_attivita, total_approvate, total_non_approvate,
                       total_emesse, total_non_emesse, total_prezzo_da_riallineare,
                       last_update, commessa_codice, cliente_display
                FROM vendite.fn_get_commessa_stato(%s)
                """,
                [commessa_id],
            )
            row = cursor.fetchone()
        if not row:
            return None
        return CommessaStatoResult(
            stato_commessa_id=int(row[0]),
            stato_commessa=row[1],
            chiude_commessa=bool(row[2]),
            emittibile=bool(row[3]),
            modificabile=bool(row[4]),
            policy_fatturazione=row[5],
            fatturazione_immediata=(None if row[6] is None else bool(row[6])),
            priorita_operativa=row[7],
            billing_account_id=_int(row[8]),
            utility_id=_int(row[9]),
            emittente_soggetto_ruolo_id=_int(row[10]),
            total_attivita=int(row[11]),
            total_approvate=int(row[12]),
            total_non_approvate=int(row[13]),
            total_emesse=int(row[14]),
            total_non_emesse=int(row[15]),
            total_prezzo_da_riallineare=int(row[16]),
            last_update=(row[17].isoformat() if row[17] is not None else None),
            commessa_codice=row[18],
            cliente_display=row[19],
        )

    def get_commessa_stato_codice(self, commessa_id: int) -> str | None:
        """`codice_interno` dello stato corrente della testata commessa, o None
        se inesistente. Usato dall'orchestratore CONFERMA_VENDITA per lo skip
        idempotente della transizione a PRONTA_FATTURAZIONE quando una commessa
        multi-sorgente è già stata portata pronta da una sorgente precedente, e
        come lettore leggero dell'esistenza (404) da `get_legami` e
        `cambia_stato_commessa` del service."""
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT sc.codice_interno
                  FROM vendite.commesse c
                  JOIN vendite.stati_commessa sc ON sc.id = c.stato_commessa_id
                 WHERE c.id = %s
                """,
                [commessa_id],
            )
            row = cursor.fetchone()
        return row[0] if row else None

    # Scopo: Capability data-driven della commessa per il detail/stato API.
    #        Wrapper su `script.fn_available_actions_commessa` (matrice
    #        `vendite.transizioni_stati_commessa`): ritorna jsonb con
    #        available_actions (transizioni manuali utente con UI hints),
    #        can_change_state, can_edit_righe, is_emittibile, stato_codice.
    #        Blob opaco lato Python (passato intatto al FE). Pattern gemello di
    #        ordini/preventivi/offerte/contratti. {} se la fn ritorna NULL
    #        (commessa inesistente — il caller verifica a monte con get_commessa_stato).
    def get_capabilities(self, commessa_id: int) -> dict[str, Any]:
        return call_jsonb_fn("script.fn_available_actions_commessa", commessa_id)

    # Scopo: La TESTATA LEGGIBILE della commessa (Blocco C di brief-db-modifiche-
    #        certe-ciclo-vendita-e-articolo, P-4): `descrizione`, `data_apertura`
    #        e il responsabile — id + nome della persona. Separata da
    #        `get_commessa_stato` perche' quella e' `fn_get_commessa_stato`, che
    #        le tre colonne non le espone: il service le fonde nello stesso payload.
    # ⭐ Il nome della persona viene dalla VISTA MODELLO
    #        `anagrafiche.vw_risorse_umane_dettaglio`, la stessa del lookup
    #        (`AnagraficheRepository._risorse_umane_lookup`): la catena
    #        risorsa -> soggetto vive nella vista, e il picker e il dettaglio
    #        chiamano la persona nello stesso modo per costruzione.
    # ⚠️ Legge `vendite.commesse`, che ha la RLS: fuori scope risponde None
    #        come `get_commessa_stato`, e il service ha gia' detto 404 prima.
    def get_commessa_testata(self, commessa_id: int) -> CommessaTestataRow | None:
        sql = """
            SELECT c.descrizione,
                   c.data_apertura,
                   c.responsabile_risorsa_umana_id,
                   ru.ragione_sociale_completa AS responsabile_display
              FROM vendite.commesse c
              LEFT JOIN anagrafiche.vw_risorse_umane_dettaglio ru
                     ON ru.risorsa_umana_id = c.responsabile_risorsa_umana_id
             WHERE c.id = %s
        """
        with connection.cursor() as cursor:
            cursor.execute(sql, [commessa_id])
            row = row_to_dict(cursor)
            return cast(CommessaTestataRow, row) if row else None

    # Colonne di testata scrivibili dall'operatore. ⛔ `data_apertura` NON c'e':
    # la scrive il default (`script.fn_data_operativa()`) alla nascita, e a
    # video e' in sola lettura (brief §5.5, voce 4).
    TESTATA_UPDATE_COLUMNS: frozenset[str] = frozenset({
        "descrizione", "responsabile_risorsa_umana_id",
    })

    # Scopo: Aggiorna i campi di testata della commessa (whitelist sopra).
    #        `None` AZZERA (PATCH dei documenti vendite): togliere il
    #        responsabile e' un gesto legittimo. Ritorna True se ha toccato
    #        una riga; il require sul padre attivo (`trg_commesse_a10_risorse_
    #        umane_require_attivo_ins_upd`, nato da ci_apply) rifiuta una
    #        persona disattivata — il service traduce e passa.
    def update_commessa_testata(self, commessa_id: int, dati: dict[str, Any]) -> bool:
        return execute_dynamic_update(
            "vendite.commesse", commessa_id, dati,
            allowed=self.TESTATA_UPDATE_COLUMNS,
        )

    # --- Gruppo 2: Attività commessa ---

    def upsert_attivita(self, inp: CommessaAttivitaInput) -> UpsertAttivitaResult:
        """Inserisce o aggiorna una riga operativa sulla commessa (idempotente su segment_key).
        Restituisce UpsertAttivitaResult(attivita_id, is_new)."""
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT attivita_id, is_new FROM vendite.fn_upsert_commessa_attivita(
                    p_commessa_id => %s,
                    p_segment_key => %s,
                    p_articolo_id => %s,
                    p_istanza_utility_id => %s,
                    p_data_attivita => %s,
                    p_uom_id => %s,
                    p_quantita => %s,
                    p_competenza_mese => %s,
                    p_competenza_dal => %s,
                    p_competenza_al => %s,
                    p_prezzo_snapshot => %s,
                    p_prezzo_base_snapshot => %s,
                    p_origine_prezzo => %s,
                    p_tipo_variazione_applicata => %s,
                    p_valore_variazione_applicata => %s,
                    p_promo_id => %s,
                    p_contratto_id => %s,
                    p_categoria_cliente_id_snapshot => %s,
                    p_classe_utenza_id_snapshot => %s,
                    p_qta_operativa => %s,
                    p_uom_operativa_id => %s,
                    p_factor_to_base => %s,
                    p_posticipa_al => %s,
                    p_tipo_doc_fiscale_id => %s,
                    p_valuta_id => %s,
                    p_area_geografica_id => %s,
                    p_listino_versione_id => %s,
                    p_prezzo_bloccato => %s,
                    p_pricing_mode => %s,
                    p_prezzo_da_riallineare => %s,
                    p_stato_approvazione => %s,
                    p_stato_emissione => %s,
                    p_sorgente_tipo_id => %s,
                    p_sorgente_chiave => %s,
                    p_tipo_movimento => %s,
                    p_meta => %s::jsonb,
                    p_causale_onere_id => %s,
                    p_listino_riga_id => %s,
                    p_sorgente_riga => %s
                )
                """,
                [
                    inp.commessa_id,
                    inp.segment_key,
                    inp.articolo_id,
                    inp.istanza_utility_id,
                    inp.data_attivita,
                    inp.uom_id,
                    inp.quantita,
                    inp.competenza_mese,
                    inp.competenza_dal,
                    inp.competenza_al,
                    inp.prezzo_snapshot,
                    inp.prezzo_base_snapshot,
                    inp.origine_prezzo,
                    inp.tipo_variazione_applicata,
                    inp.valore_variazione_applicata,
                    inp.promo_id,
                    inp.contratto_id,
                    inp.categoria_cliente_id_snapshot,
                    inp.classe_utenza_id_snapshot,
                    inp.qta_operativa,
                    inp.uom_operativa_id,
                    inp.factor_to_base,
                    inp.posticipa_al,
                    inp.tipo_doc_fiscale_id,
                    inp.valuta_id,
                    inp.area_geografica_id,
                    inp.listino_versione_id,
                    inp.prezzo_bloccato,
                    inp.pricing_mode,
                    inp.prezzo_da_riallineare,
                    inp.stato_approvazione,
                    inp.stato_emissione,
                    inp.sorgente_tipo_id,
                    inp.sorgente_chiave,
                    inp.tipo_movimento,
                    self._to_jsonb_param(inp.meta),
                    inp.causale_onere_id,
                    inp.listino_riga_id,
                    inp.sorgente_riga,
                ],
            )
            row = cursor.fetchone()
        assert row is not None
        return UpsertAttivitaResult(attivita_id=int(row[0]), is_new=bool(row[1]))

    # --- Gruppo 2b: Batch upsert attività ---

    @staticmethod
    def _inp_to_jsonb_row(inp: CommessaAttivitaInput) -> dict:
        """Serializza CommessaAttivitaInput in dict JSONB-safe per fn_batch_upsert."""
        def _date(v: date | None) -> str | None:
            return v.isoformat() if v else None

        def _decimal(v: Decimal | None) -> str | None:
            return str(v) if v is not None else None

        return {
            "commessa_id": inp.commessa_id,
            "segment_key": inp.segment_key,
            "articolo_id": str(inp.articolo_id) if inp.articolo_id else None,
            "istanza_utility_id": inp.istanza_utility_id,
            "data_attivita": _date(inp.data_attivita),
            "uom_id": inp.uom_id,
            "quantita": _decimal(inp.quantita),
            "competenza_mese": _date(inp.competenza_mese),
            "competenza_dal": _date(inp.competenza_dal),
            "competenza_al": _date(inp.competenza_al),
            "prezzo_snapshot": _decimal(inp.prezzo_snapshot),
            "qta_operativa": _decimal(inp.qta_operativa),
            "uom_operativa_id": inp.uom_operativa_id,
            "factor_to_base": _decimal(inp.factor_to_base),
            "posticipa_al": _date(inp.posticipa_al),
            "tipo_doc_fiscale_id": inp.tipo_doc_fiscale_id,
            "valuta_id": inp.valuta_id,
            "area_geografica_id": inp.area_geografica_id,
            "listino_versione_id": inp.listino_versione_id,
            "listino_riga_id": inp.listino_riga_id,
            "prezzo_bloccato": inp.prezzo_bloccato,
            "pricing_mode": inp.pricing_mode,
            "prezzo_da_riallineare": inp.prezzo_da_riallineare,
            "stato_approvazione": inp.stato_approvazione,
            "stato_emissione": inp.stato_emissione,
            "sorgente_tipo_id": inp.sorgente_tipo_id,
            # La chiave del documento (id o uid in testo): la legge il wrapper
            # batch come `sorgente_chiave` dal giro K.1. ⛔ Con la chiave vecchia
            # (`sorgente_uid`) la riga passerebbe la chiave NULL, senza errore.
            "sorgente_chiave": inp.sorgente_chiave,
            # La riga del documento: la legge il wrapper batch (giro C.3).
            "sorgente_riga": inp.sorgente_riga,
            "tipo_movimento": inp.tipo_movimento,
            # Chiave facoltativa del wrapper (20261103-49): senza, ogni riga
            # ONERE del push e' rifiutata dalla madre.
            "causale_onere_id": inp.causale_onere_id,
            "meta": inp.meta or {},
            # Snapshot pricing v5 (F2-BE-11). Il wrapper batch DB deve
            # estrarre queste chiavi e passarle a fn_upsert_commessa_attivita
            # (dipendenza DB: estensione `fn_batch_upsert_commessa_attivita`).
            "prezzo_base_snapshot": _decimal(inp.prezzo_base_snapshot),
            "origine_prezzo": inp.origine_prezzo,
            "tipo_variazione_applicata": inp.tipo_variazione_applicata,
            "valore_variazione_applicata": _decimal(inp.valore_variazione_applicata),
            "promo_id": inp.promo_id,
            "contratto_id": inp.contratto_id,
            "categoria_cliente_id_snapshot": inp.categoria_cliente_id_snapshot,
            "classe_utenza_id_snapshot": inp.classe_utenza_id_snapshot,
        }

    # Scopo: Risolve gli id attivita` dalle coppie (commessa_id, segment_key)
    #        per il ponte di approvazione post-push (dettagli nel docstring).
    def list_attivita_ids_by_segments(
        self, pairs: list[tuple[int, str]],
    ) -> dict[int, list[int]]:
        """Risolve gli id delle righe attivita` dalle coppie (commessa_id,
        segment_key) appena upsertate. Serve al ponte di approvazione post-push:
        `fn_batch_upsert_commessa_attivita` restituisce solo i contatori, non gli
        id, ma il push deve approvare **le proprie righe** e non tutte le
        NON_EMESSA della commessa (che possono includere righe di terzi, es. un
        onere manuale in attesa). La coppia (commessa_id, segment_key) e` la
        chiave naturale della riga (indice unico), quindi il lookup e` esatto.

        Le coppie fallite le esclude il CHIAMANTE (handler) prima di arrivare
        qui: per gli INSERT falliti la riga non esiste e non tornerebbe
        comunque, ma per gli UPDATE falliti la riga preesistente esiste ancora
        e senza esclusione verrebbe approvata coi valori stali.
        Restituisce {commessa_id: [attivita_id, ...]}."""
        if not pairs:
            return {}
        commessa_ids = [p[0] for p in pairs]
        segment_keys = [p[1] for p in pairs]
        with connection.cursor() as cursor:
            # unnest delle due liste in coppie: un solo round-trip, niente IN
            # gigante costruito a stringa.
            cursor.execute(
                """
                SELECT ca.commessa_id, ca.id
                  FROM vendite.commesse_attivita ca
                  JOIN unnest(%s::bigint[], %s::varchar[]) AS t(commessa_id, segment_key)
                    ON t.commessa_id = ca.commessa_id
                   AND t.segment_key = ca.segment_key
                """,
                [commessa_ids, segment_keys],
            )
            rows = cursor.fetchall()
        out: dict[int, list[int]] = {}
        for commessa_id, attivita_id in rows:
            out.setdefault(int(commessa_id), []).append(int(attivita_id))
        return out

    def batch_upsert_attivita(self, inputs: list[CommessaAttivitaInput]) -> BatchUpsertResult:
        """Upsert batch di righe attivita in una sola chiamata DB.
        Restituisce BatchUpsertResult con contatori e errori per riga."""
        if not inputs:
            return BatchUpsertResult(total_rows=0, inserted=0, updated=0, errors=[])
        rows_json = json.dumps([self._inp_to_jsonb_row(inp) for inp in inputs])
        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT * FROM vendite.fn_batch_upsert_commessa_attivita(%s::jsonb)",
                [rows_json],
            )
            row = cursor.fetchone()
        assert row is not None
        errors_raw = jsonb_out(row[3]) or []
        return BatchUpsertResult(
            total_rows=int(row[0]),
            inserted=int(row[1]),
            updated=int(row[2]),
            errors=[
                ErroreBatchAttivita.da_jsonb(e)
                for e in (errors_raw if isinstance(errors_raw, list) else [])
                if isinstance(e, dict)
            ],
        )

    # --- Gruppo 3: Emit attività fatturabili (pull) ---

    def emit_attivita_fatturabili(
        self,
        commessa_id: int,
        *,
        only_approved: bool = True,
        dry_run: bool = False,
        gruppi: tuple[str, ...] | list[str] | None = None,
        emit_batch_id: str | None = None,
    ) -> CommessaEmitResult:
        """Pull commessa → attivita_fatturabili (step 0 pipeline fatturazione).
        Idempotente. Restituisce contatori candidati/inseriti/aggiornati.

        NB: la fn DB non ha più `p_lotto_attivita_id` (sottosistema lotto-attività
        deprecato, changeset 20260227-16).

        `gruppi` (emissione mirata, A3): restringe il pull ai soli gruppi
        fatturabili richiesti — senza, le righe degli altri gruppi della stessa
        commessa passerebbero a `stato_emissione = EMESSA` uscendo dalla card
        «Da emettere» pur non essendo state chieste. None = nessuna
        restrizione (comportamento storico).

        ⭐ `emit_batch_id` è L'IDENTITÀ DEL GIRO che sta chiedendo il pull, e da
        essa dipende se il giro fattura qualcosa (changeSet 20260904-31/-32/-50,
        brief-residuo-fatturabili-e-bandiere-esito-parziale D1+D2). Il pull
        FIRMA con questo valore le righe che accetta — su entrambi i rami,
        insert e update — e `fn_select_attivita_fatturabili` sceglie poi per
        quel marchio invece che per sole coordinate. Il perimetro lo CONSEGNA
        chi lo ha calcolato, così una commessa respinta non può farsi fatturare
        da una riga rimasta libera da un giro precedente.

        🔴 Passarlo NULL non è un default innocuo: la firma resta vuota, la
        select non trova nulla e il giro emette ZERO fatture SENZA nessun
        errore. Il chiamante di pipeline deve passare `context.lock_batch_id`.
        Resta `None` solo per gli usi fuori pipeline (backfill, riconciliazioni),
        dove il DB tiene il marchio che la riga aveva già."""
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT total_candidate, inserted_rows, updated_rows
                FROM vendite.fn_emit_attivita_fatturabili_da_commessa(
                    p_commessa_id => %s,
                    p_only_approved => %s,
                    p_dry_run => %s,
                    p_gruppi => %s::text[],
                    p_emit_batch_id => %s::uuid
                )
                """,
                # ⚠️ `if gruppi` e non `is not None`: una lista VUOTA diventerebbe
                # `'{}'::text[]`, e `= ANY('{}')` e' sempre falso → zero righe.
                # Vuoto e assente devono collassare entrambi su NULL = nessuna
                # restrizione (convenzione DB dell'emissione mirata). Stessa
                # forma nelle due discovery sotto.
                [commessa_id, only_approved, dry_run,
                 list(gruppi) if gruppi else None,
                 emit_batch_id],
            )
            row = cursor.fetchone()
        assert row is not None
        return CommessaEmitResult(
            total_candidate=int(row[0]),
            inserted_rows=int(row[1]),
            updated_rows=int(row[2]),
        )

    # Scopo: Restituisce le commesse emittibili nel perimetro del contesto lotto.
    def list_commesse_emittibili(
        self,
        *,
        competenza_mese: date | None = None,
        billing_account_id: int | None = None,
        utility_id: int | None = None,
        emittente_soggetto_ruolo_id: int | None = None,
        fatturazione_immediata: bool | None = None,
        limit: int = 1000,
        gruppi: tuple[str, ...] | list[str] | None = None,
        emit_batch_id: str | None = None,
    ) -> list[int]:
        """Chiama vendite.fn_list_commesse_emittibili e restituisce i commessa_id.
        `fatturazione_immediata`: True=solo immediate, False=solo differite,
        None=tutte (storico). Filtro usato per separare le corsie del driver.

        `gruppi` (emissione mirata, A6): visita solo le commesse che contengono
        almeno uno dei gruppi richiesti. None = nessuna restrizione.

        ⭐ `emit_batch_id` è L'IDENTITÀ DEL GIRO, lo STESSO parametro che si
        consegna all'emit (changeSet `20260912-15`, brief
        `brief-db-rilancio-step-non-rivede-le-proprie-commesse` D1). Al
        rilancio di un pull fallito i PROPRI documenti risultano `TRATTENUTA`
        dal lotto che sta riprovando: con l'identità la discovery li vede come
        `PRONTA` e visita la commessa, così l'emit — che ha la stessa eccezione
        — può riprenderli. È il cancello a MONTE dell'emit: senza identità la
        commessa non viene nemmeno visitata, e l'eccezione dell'emit resta
        corretta e irraggiungibile.

        🔴 `None` non è un default innocuo per il pull: la discovery scarta i
        propri documenti IN SILENZIO, il giro visita zero commesse e chiude
        `COMPLETATO` senza aver emesso niente (LTF-0010972, 2026-09-12). Il
        chiamante di pipeline fa il guard su `lock_batch_id` PRIMA di
        chiamare questo metodo. Resta `None` solo fuori pipeline, dove non
        c'è un lotto proprio da cui auto-escludersi."""
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT commessa_id
                FROM vendite.fn_list_commesse_emittibili(
                    p_competenza_mese => %s,
                    p_billing_account_id => %s,
                    p_utility_id => %s,
                    p_emittente_soggetto_ruolo_id => %s,
                    p_fatturazione_immediata => %s,
                    p_limit => %s,
                    p_gruppi => %s::text[],
                    p_emit_batch_id => %s::uuid
                )
                """,
                [competenza_mese, billing_account_id, utility_id,
                 emittente_soggetto_ruolo_id, fatturazione_immediata, limit,
                 list(gruppi) if gruppi else None,
                 emit_batch_id],
            )
            return [row[0] for row in cursor.fetchall()]

    def list_emittibili_lane(
        self,
        *,
        competenza_mese: date | None = None,
        billing_account_id: int | None = None,
        utility_id: int | None = None,
        emittente_soggetto_ruolo_id: int | None = None,
        fatturazione_immediata: bool | None = None,
        limit: int = 10000,
        gruppi: tuple[str, ...] | list[str] | None = None,
    ) -> list[CommessaEmittibileLane]:
        """Terne distinte `(emittente, tipo_doc_fiscale, utility)` con lavoro pronto da
        fatturare, via vendite.fn_list_emittibili_lane. Usato dal driver batch per creare
        UN lotto per terna: il lotto è identificato da (emittente, tipo_doc, utility,
        competenza) e la numerazione fattura è per emittente.

        Ogni lane porta:
        - `utility_id`: asse di segregazione del lotto (NOT NULL a monte → mai NULL);
        - `competenza_mese`: max delle righe candidate, con cui creare il lotto
          (la select cattura poi via `<=` anche gli arretrati);
        - `total_candidate`: righe APPROVATA+NON_EMESSA candidate, per il dry-run.

        `competenza_mese` in input è un **bound superiore** (`<=`, cumulativo). Le righe
        con tipo_doc_fiscale NULL sono escluse a monte dalla funzione DB. `limit` è il cap
        sulle TERNE restituite.

        `gruppi` (emissione mirata, A5): restituisce solo le terne dei gruppi
        richiesti. Senza, un giro mirato farebbe nascere un lotto VUOTO per ogni
        altra terna del perimetro. None = nessuna restrizione.

        `gruppi_coperti` (rev DB 2026-08-15): per ogni terna, QUALI gruppi
        fatturabili copre — chiavi da fn_build_gruppo_fatturabile_key, unica
        fonte. Un gruppo multi-tipo-doc compare su più terne (G15)."""
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT emittente_soggetto_ruolo_id, tipo_doc_fiscale_id,
                       utility_id, competenza_mese, total_candidate,
                       gruppi_coperti
                FROM vendite.fn_list_emittibili_lane(
                    p_competenza_mese => %s,
                    p_billing_account_id => %s,
                    p_utility_id => %s,
                    p_emittente_soggetto_ruolo_id => %s,
                    p_fatturazione_immediata => %s,
                    p_limit => %s,
                    p_gruppi => %s::text[]
                )
                """,
                [competenza_mese, billing_account_id, utility_id,
                 emittente_soggetto_ruolo_id, fatturazione_immediata, limit,
                 list(gruppi) if gruppi else None],
            )
            return [
                CommessaEmittibileLane(
                    emittente_soggetto_ruolo_id=(None if row[0] is None else int(row[0])),
                    tipo_doc_fiscale_id=int(row[1]),
                    utility_id=int(row[2]),
                    competenza_mese=row[3],
                    total_candidate=int(row[4]),
                    # text[] → list[str] (psycopg lo consegna gia' come str);
                    # il NULL difensivo diventa lista vuota, mai None a valle.
                    gruppi_coperti=list(row[5] or []),
                )
                for row in cursor.fetchall()
            ]

    # Scopo: Fotografia dei gruppi fatturabili richiesti — quante righe hanno,
    #        in che stato sono, e in che stato e' la testata della commessa.
    #        Diagnostica, non decisione: descrive i FATTI e lascia la
    #        classificazione (la prosa) al service. L'ammissibilita' resta della
    #        sola `fn_list_emittibili_lane`.
    #
    #        Nasce dal caso reale del 2026-08-03: un'emissione mirata su un
    #        ordine di giugno ha prodotto zero lotti in silenzio perche' la
    #        commessa era rimasta in BOZZA (non emittibile). L'operatore leggeva
    #        «nessun lotto prodotto» senza sapere che cosa lo bloccasse.
    #
    #        🟢 Dal 2026-08-15 e' un WRAPPER su `vendite.fn_diagnostica_gruppi_fatturabili`
    #        (changeSet `20260815-29`, brief emittibilita' §9.7 punto 3). Prima
    #        erano ~90 righe di SQL qui dentro che riproducevano i filtri della
    #        lane: era l'ultima copia della regola di emittibilita' fuori dal DB.
    #
    #        ⚠️ Due cambi di contratto, entrambi voluti (§9.7):
    #        - la grana e' `(gruppo_key, commessa_id)`, non piu' `gruppo_key`.
    #          La chiave di un documento sorgente NON contiene la commessa: se
    #          lo stesso documento alimentasse due commesse, il vecchio
    #          `bool_or(emittibile)` avrebbe detto «emittibile» perche' UNA lo
    #          era, e la diagnosi sarebbe caduta in NON_DETERMINATO invece di
    #          dire «commessa in BOZZA». Oggi quei casi sono zero: si chiude
    #          perche' e' gratis a DB, non perche' e' successo;
    #        - `n_senza_tipo_doc` non c'e' piu': dopo la validazione del CHECK
    #          (`20260815-30`) una riga emittibile senza tipo documento non puo'
    #          esistere, e un contatore che non puo' accendersi e' un ramo morto.
    #
    #        ⚠️ Chiamata dal giro VUOTO e dal giro PARZIALE (per i soli gruppi
    #        non serviti). In entrambi i casi la fotografia regge; il vecchio
    #        contratto diceva «solo a giro vuoto» ed era gia' infranto nello
    #        stesso file (F6 del brief).
    #        `competenza_mese` e' lo stesso bound superiore passato alla discovery.
    def diagnostica_gruppi(
        self,
        *,
        gruppi: tuple[str, ...] | list[str],
        competenza_mese: date | None = None,
    ) -> list[GruppoDiagnosi]:
        chiavi = [k for k in (str(g).strip() for g in gruppi) if k]
        if not chiavi:
            return []
        bound = None if competenza_mese is None else competenza_mese.replace(day=1)
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT gruppo_key, commessa_id, commessa_codice,
                       commessa_stato_codice_interno, commessa_stato_descrizione,
                       commessa_emittibile,
                       n_righe, n_emesse, n_annullate, n_rifiutate,
                       n_non_approvate, n_fuori_competenza, n_pronte,
                       terne_pronte
                FROM vendite.fn_diagnostica_gruppi_fatturabili(
                    p_gruppi => %s::text[],
                    p_competenza_mese => %s
                )
                """,
                [chiavi, bound],
            )
            return [
                GruppoDiagnosi(
                    gruppo_key=row[0],
                    commessa_id=None if row[1] is None else int(row[1]),
                    commessa_codice=row[2],
                    commessa_stato_codice_interno=row[3],
                    commessa_stato_descrizione=row[4],
                    commessa_emittibile=bool(row[5]) if row[5] is not None else None,
                    n_righe=int(row[6]),
                    n_emesse=int(row[7]),
                    n_annullate=int(row[8]),
                    n_rifiutate=int(row[9]),
                    n_non_approvate=int(row[10]),
                    n_fuori_competenza=int(row[11]),
                    n_pronte=int(row[12]),
                    # ⚠️ jsonb: su questa connessione psycopg lo consegna come
                    # STRINGA (misurato sul DB vero il 2026-08-16: scritto
                    # `list(valore or [])`, `'[]'` diventava `['[', ']']` — e i
                    # mock non potevano vederlo, consegnano gia' una lista).
                    # Si decodifica con `jsonb_out` (lettura per posizione);
                    # il NULL vale «nessuna terna».
                    terne_pronte=jsonb_out(row[13]) or [],
                )
                for row in cursor.fetchall()
            ]

    # Scopo: Il REGISTRO delle righe di una commessa — gli eventi che il
    #        database scrive su `vendite.commesse_attivita_log`. Risponde a
    #        «perche' questa riga e' cosi'»: chi, quando, e con quale motivo.
    # Perimetro: sola lettura. Ordine cronologico INVERSO (l'ultimo fatto in
    #        cima), paginato. `commessa_attivita_id` opzionale restringe a una
    #        riga sola — e' il caso d'uso del kebab di riga.
    # Risultato: tuple (eventi, conteggio totale).
    #
    # ⛔ LO SCOPE STA SULLA RIGA DI COMMESSA, NON SUL LOG.
    #    `vendite.commesse_attivita_log` **non ha row level security**;
    #    `vendite.commesse_attivita` si'. Leggere il log da solo sarebbe
    #    **fail-open**: si vedrebbero gli eventi di commesse fuori perimetro, coi
    #    loro motivi in chiaro. Il `JOIN` su `ca` non e' una decorazione per
    #    prendere due colonne — **e' il cancello**, ed e' la stessa lezione gia'
    #    pagata su `attivita_fatturabili` col verbo «Riporta da emettere».
    #
    # ⚠️ Il vocabolario degli eventi e' APERTO e lo possiede il database: oggi
    #    sono sei (ONERE_AGGIUNTO, RIGA_MANUALE_ANNULLATA, RIGA_RITIRATA_DA_SORGENTE,
    #    RIGA_RIPORTATA_DA_EMETTERE, ACCREDITO_RICHIESTO, ACCREDITO_ANNULLATO).
    #    Qui non se ne nomina NESSUNO e non si filtra: un evento nuovo deve
    #    comparire da se'. Chi rende lo risolve con ripiego sul codice grezzo.
    #
    # ⚠️ `dettaglio` esce COM'E' (jsonb), piu' `motivo` estratto a parte perche'
    #    e' l'unica chiave che tre eventi su sei condividono ed e' la frase che
    #    l'operatore cerca. Non si appiattisce il resto in una stringa qui: la
    #    forma di ogni evento e' diversa, e deciderla nel repository
    #    significherebbe rifarla a ogni evento nuovo.
    def list_registro_attivita(
        self,
        commessa_id: int,
        *,
        commessa_attivita_id: int | None = None,
        limit: int = DEFAULT_LIMIT_EVENTI,
        offset: int = 0,
    ) -> tuple[list[CommessaRegistroEventoRow], int]:
        where = ["ca.commessa_id = %s"]
        params: list[Any] = [commessa_id]
        if commessa_attivita_id is not None:
            where.append("l.commessa_attivita_id = %s")
            params.append(commessa_attivita_id)
        where_sql = " AND ".join(where)

        with connection.cursor() as cursor:
            cursor.execute(
                f"""
                SELECT count(*)
                  FROM vendite.commesse_attivita_log l
                  JOIN vendite.commesse_attivita ca ON ca.id = l.commessa_attivita_id
                 WHERE {where_sql}
                """,  # noqa: S608 - where_sql da letterali, i valori sono bind
                params,
            )
            row = cursor.fetchone()
            total = int(row[0]) if row else 0

            cursor.execute(
                f"""
                SELECT
                    l.id,
                    l.commessa_attivita_id,
                    l.evento,
                    l.dettaglio,
                    l.dettaglio ->> 'motivo'    AS motivo,
                    l.data_insert,
                    l.user_insert,
                    ca.segment_key,
                    ca.stato_emissione,
                    ca.tipo_movimento,
                    art.codice                  AS articolo_codice,
                    art.descrizione             AS articolo_descrizione
                  FROM vendite.commesse_attivita_log l
                  JOIN vendite.commesse_attivita ca ON ca.id = l.commessa_attivita_id
                  LEFT JOIN catalogo.articoli art ON art.id = ca.articolo_id
                 WHERE {where_sql}
                 ORDER BY l.data_insert DESC, l.id DESC
                 LIMIT %s OFFSET %s
                """,  # noqa: S608 - idem
                [*params, *limiti_pagina(limit, offset, tetto=_REGISTRO_QUERY_MAX_ROWS)],
            )
            eventi: list[CommessaRegistroEventoRow] = []
            for r in cursor.fetchall():
                # ⚠️ Lettura per posizione: il `jsonb` arriva come STRINGA, e
                #    passarlo cosi' al frontend gli farebbe rendere caratteri
                #    invece di campi (`jsonb_out`).
                dettaglio = jsonb_out(r[3])
                eventi.append(
                    {
                        "id": int(r[0]),
                        "commessa_attivita_id": int(r[1]),
                        "evento": str(r[2]),
                        "dettaglio": dettaglio or {},
                        "motivo": None if r[4] is None else str(r[4]),
                        "data_insert": r[5].isoformat() if r[5] is not None else None,
                        "user_insert": None if r[6] is None else str(r[6]),
                        "segment_key": None if r[7] is None else str(r[7]),
                        "stato_emissione": None if r[8] is None else str(r[8]),
                        "tipo_movimento": None if r[9] is None else str(r[9]),
                        "articolo_codice": None if r[10] is None else str(r[10]),
                        "articolo_descrizione": None if r[11] is None else str(r[11]),
                    }
                )
        return eventi, total

    # Scopo: CONSUNTIVO di un giro di fatturazione — quali gruppi fatturabili
    #        hanno prodotto righe fatturate davvero, quali no, e quali sono
    #        stati fatturati da un altro giro. Wrapper su
    #        `vendite.fn_esito_gruppi_giro` (changeSet `20260815-27`, brief
    #        emittibilita' §9.7 punto 1).
    #
    #        ⚠️ Prende SOLO i lotti prodotti, e non e' una svista: i gruppi
    #        RICHIESTI sono gia' persistiti su `fatturazione_lotti_gruppi` (il
    #        runner ci scrive l'intera tupla su ogni lotto del giro), quindi
    #        richiesti e serviti sono ENTRAMBI misurati dalla stessa funzione.
    #        Un parametro «gruppi richiesti» avrebbe riaperto la porta a
    #        passare la PREVISIONE (`gruppi_coperti` della discovery) al posto
    #        della misura — che e' esattamente il difetto che questo sostituisce.
    #
    #        🔒 Un lotto fuori scope RLS fa sollevare `E_LOTTO_NON_TROVATO` a
    #        DB, invece di produrre un falso «non servito»: la catena e'
    #        asimmetrica (il richiesto e' leggibile da chiunque, il servito no)
    #        e zero non e' una misura.
    def esito_gruppi_giro(self, lotto_ids: list[int]) -> list[GruppoEsitoGiro]:
        ids = [int(i) for i in (lotto_ids or [])]
        if not ids:
            return []
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT gruppo_key, richiesto, esito,
                       n_attivita_fatturate, n_attivita_residue,
                       lotti_serventi, lotti_altrui
                FROM vendite.fn_esito_gruppi_giro(%s::bigint[])
                """,
                [ids],
            )
            return [
                GruppoEsitoGiro(
                    gruppo_key=row[0],
                    richiesto=bool(row[1]),
                    esito=str(row[2]),
                    n_attivita_fatturate=int(row[3]),
                    n_attivita_residue=int(row[4]),
                    lotti_serventi=[int(x) for x in (row[5] or [])],
                    lotti_altrui=[int(x) for x in (row[6] or [])],
                )
                for row in cursor.fetchall()
            ]

    # --- Gruppo 3b: Lista attività commessa (paginata) ---

    # Colonne restituite da vendite.fn_list_commessa_attivita.
    _ATTIVITA_COLS = (
        "id", "commessa_id", "segment_key", "articolo_id",
        "istanza_utility_id", "data_attivita", "uom_id", "quantita",
        "competenza_mese", "competenza_dal", "competenza_al",
        "prezzo_snapshot", "prezzo_bloccato", "prezzo_da_riallineare",
        "stato_approvazione", "stato_emissione", "sorgente_tipo_id",
        # ⭐ `sorgente_codice_interno` dal 2026-10-21 (20261021-20, brief-db-
        # grammatica-unica-documenti §13.6), al posto di `sorgente_codice`, che
        # era `config.sorgenti.codice`, il nome MODIFICABILE: il tipo del
        # documento d'origine e' quello immutabile (G-1), ed e' da qui che il
        # frontend apre il documento.
        "sorgente_codice_interno", "meta", "data_update",
        # In coda alla RETURNS TABLE (changeset 20260724-07): EXISTS di un'AF
        # con fattura_riga_id valorizzato = specchio esatto del guard BE
        # `_assert_non_fatturata`. Il FE lo usa per nascondere le azioni prezzo
        # su riga già fatturata. Bool nativo: nessuna decodifica speciale.
        "fatturata",
        # Sette colonne additive (changeSet 20260816-04): la riga porta a valle
        # QUANDO e' stata portata in fattura, QUALE fattura e QUALE documento
        # di origine — tre informazioni che prima si fermavano al database.
        #
        # ⚠️ `fatturata_il` e' `fatture_righe.data_insert`, NON il `data_update`
        # dell'attivita': il momento in cui la riga e' stata portata in fattura
        # e' un fatto che nessuna modifica successiva puo' spostare. Sulle 37
        # righe gia' fatturate le due colonne divergono gia' in 10 casi.
        #
        # ⚠️ `fattura_*` e `sorgente_documento_id` sono NULL anche quando il
        # documento esiste ma NON e' visibile a chi chiede (RLS su
        # `vendite.fatture`). `fatturata` resta invece calcolato su
        # `attivita_fatturabili`, che RLS non ce l'ha: chi non vede la fattura
        # legge comunque `fatturata=true` con le colonne documento a NULL — sa
        # che e' fatturata e sa di non poterci navigare. Derivare il flag dalla
        # join lo renderebbe FALSO per quell'utente, cioe' una riga fatturata
        # si presenterebbe come da fatturare.
        "fatturata_il",
        "fattura_id", "fattura_numero", "fattura_stato",
        # `sorgente_apribile` (dal 2026-10-20, brief-db-grammatica-unica-documenti
        # 2d / L2d-1) al posto di `sorgente_area`, il plurale ritirato: dice se
        # il documento d'origine ha una pagina; quale sia, lo dice la sorgente.
        "sorgente_uid", "sorgente_apribile", "sorgente_documento_id",
        # Cinque colonne additive (changeSet 20260820-05): la riga dice
        # finalmente COSA e' e DA DOVE VIENE. Prima l'unica traccia della
        # provenienza era `segment_key`, una chiave tecnica — rilievo in-app di
        # Tid del 2026-08-20: «per capire da dove viene e' un terno al lotto».
        #
        # ⚠️ `sorgente_documento_numero` e le altre colonne d'origine sono VUOTE
        # sulle righe RETTIFICA e ONERE, e non e' un dato sporco:
        # `fn_accredita_riga_reso` scrive la rettifica con la sorgente a NULL, e
        # un CHECK impone la coppia tutta-vuota o tutta-piena. Sono esattamente
        # le righe di nota di credito — cioe' quelle per cui la colonna era
        # stata chiesta. Chi mostra «Origine» deve sapere che li' non c'e'.
        #
        # ⭐ Per quelle righe la domanda ha risposta su `gruppo_key`, che e'
        # un'ALTRA domanda: il gruppo fatturabile di una rettifica non e' il
        # DDT ma `MAN:<commessa_id>` (il gruppo oneri). Il segmento porta il
        # DDT, il gruppo no — e le due colonne non sono intercambiabili.
        # Il documento resta comunque separato: `fn_build_fattura_key` porta la
        # natura, quindi una rettifica non finisce nella fattura ordinaria.
        "tipo_movimento",
        "articolo_codice", "articolo_descrizione",
        "sorgente_documento_numero", "gruppo_key",
        # In coda alla RETURNS TABLE (20261021-20): il nome del tipo a video
        # («Ordine», non `ORDINE_VENDITA`), che la lista mostra e ordina.
        "sorgente_etichetta",
    )
    # Type mapping per serializzazione colonne attivita.
    _ATTIVITA_DATE_COLS = frozenset({
        "data_attivita", "competenza_mese", "competenza_dal", "competenza_al", "data_update",
        "fatturata_il",
    })
    _ATTIVITA_JSONB_COLS = frozenset({"meta"})
    _ATTIVITA_UUID_COLS = frozenset({"articolo_id"})

    def list_commessa_attivita(
        self,
        commessa_id: int,
        *,
        stato_emissione: str | None = None,
        stato_approvazione: str | None = None,
        competenza_mese: date | None = None,
        limit: int = DEFAULT_LIMIT,
        offset: int = 0,
        order_by: str | None = None,
        order_dir: str = "asc",
        tipo_movimento: str | None = None,
        max_rows: int | None = None,
    ) -> dict:
        """Lista paginata attività di una commessa via vendite.fn_list_commessa_attivita.

        order_by/order_dir passano alla fn DB (whitelist ATTIVITA_SORT_COLUMNS,
        validata a monte dal service); None = ordine storico ca.id.
        Restituisce {"count": <total_righe_filtrate>, "results": [dict, ...]}.
        """
        # `max_rows` = percorso EXPORT: salta la paginazione, come i `fetch`
        # dei cruscotti (`build_dash_export_response`). Senza, il file uscirebbe
        # con le righe di UNA PAGINA su una commessa che ne ha mille — troncato
        # in silenzio, il modo peggiore di sbagliare un file scaricato.
        #
        # ⚠️ UN SOLO TETTO QUI, ed e' quello della fn (10.000, che `p_limit`
        # clampa da se'). Il tetto di PAGINA (200) vive nel service, dove e' un
        # `require` che risponde 400 e DICE il limite: averlo anche qui era una
        # seconda copia della stessa regola — e proprio la copia silenziosa, che
        # avrebbe tagliato l'export a 200 righe senza dirlo a nessuno.
        # ⭐ Il guard sul limite vero e' a monte (`build_export_response`) e
        # confronta il `count` ESATTO, non le righe estratte: quindi il clamp
        # della fn non puo' far passare per completo un export che non lo e'.
        safe_limit, safe_offset = limiti_pagina(max_rows or limit, offset, tetto=_ATTIVITA_EXPORT_MAX_ROWS)

        # Parametri WHERE condivisi tra count e data query.
        where_params: list = [commessa_id]
        where_clauses = ["ca.commessa_id = %s"]
        if stato_emissione is not None:
            where_clauses.append("ca.stato_emissione = %s")
            where_params.append(stato_emissione)
        if stato_approvazione is not None:
            where_clauses.append("ca.stato_approvazione = %s")
            where_params.append(stato_approvazione)
        if competenza_mese is not None:
            where_clauses.append("ca.competenza_mese = date_trunc('month', %s::date)::date")
            where_params.append(competenza_mese)
        # ⚠️ Il COUNT vive su una query SUA, sulla tabella: ogni filtro passato
        # alla fn va ripetuto QUI o il totale del paginatore conta righe che la
        # lista non mostra — «1 di 98» con 3 righe a video. La tolleranza su
        # spazi/maiuscole e' la stessa della fn, per non contare diversamente da
        # come si filtra.
        if tipo_movimento is not None:
            where_clauses.append("ca.tipo_movimento = upper(btrim(%s))")
            where_params.append(tipo_movimento)
        where_sql = " AND ".join(where_clauses)

        _cols_sql = ", ".join(self._ATTIVITA_COLS)
        with connection.cursor() as cursor:
            # Total count (stessi filtri, senza LIMIT/OFFSET).
            cursor.execute(
                f"SELECT COUNT(*) FROM vendite.commesse_attivita ca WHERE {where_sql}",  # noqa: S608 — WHERE da clausole letterali con %s, valori come parametri
                where_params,
            )
            count_row = cursor.fetchone()
            total_count = int(count_row[0]) if count_row else 0

            # Data query paginata.
            cursor.execute(
                f"""
                SELECT {_cols_sql}
                FROM vendite.fn_list_commessa_attivita(
                    p_commessa_id => %s,
                    p_stato_emissione => %s,
                    p_stato_approvazione => %s,
                    p_competenza_mese => %s,
                    p_limit => %s,
                    p_offset => %s,
                    p_order_by => %s,
                    p_order_dir => %s,
                    p_tipo_movimento => %s
                )
                """,  # noqa: S608 — colonne da costante _ATTIVITA_COLS
                [commessa_id, stato_emissione, stato_approvazione,
                 competenza_mese, safe_limit, safe_offset,
                 order_by, order_dir, tipo_movimento],
            )
            raw_rows = cursor.fetchall()

        rows = []
        for raw in raw_rows:
            row_dict: dict[str, Any] = {}
            for idx, col in enumerate(self._ATTIVITA_COLS):
                val = raw[idx]
                if col in self._ATTIVITA_JSONB_COLS:
                    val = jsonb_out(val) or {}
                elif col in self._ATTIVITA_DATE_COLS and val is not None:
                    val = val.isoformat()
                elif col in self._ATTIVITA_UUID_COLS and val is not None:
                    val = str(val)
                row_dict[col] = val
            rows.append(row_dict)

        return {"count": total_count, "results": rows}

    # --- Gruppo 4: Push log ---

    # ⭐ IL GIRO SI APRE E SI CHIUDE, e non e' una preferenza di stile: e' il
    #    modo in cui un giro INTERROTTO smette di sparire (consegna BE-3b,
    #    decisione D-3). Fino al 2026-08-22 la riga nasceva a fine corsa con
    #    `fn_log_commessa_push_run` — che per questo ⛔ **non esiste piu'**, e
    #    il changeSet 69 l'ha tolta.
    #
    #    Ne discendono tre cose, tutte gratis:
    #      1. l'`id` del giro esiste dal primo istante (era lo zero di
    #         `PUSH_STARTED`, che non era un segnaposto ma un id **che non
    #         esisteva ancora**);
    #      2. il `correlation_id` ha dove stare **prima** che il giro produca
    #         qualcosa;
    #      3. un push che muore a meta' lascia una riga `IN_ESECUZIONE`, che e'
    #         l'unica prova che qualcosa e' partito e non e' tornato.
    #
    # ⚠️ La coppia va usata SEMPRE insieme. Chi apre e non chiude lascia un
    #    giro che ogni conteggio leggera' come in corso; chi chiude due volte
    #    prende `E_COMMESSA_PUSH_RUN_NON_APERTO`, ed e' voluto — il secondo
    #    esito verrebbe da un'altra corsa, e a perdersi sarebbe la storia di
    #    entrambe.

    # Scopo: Apre il giro di push — riga `IN_ESECUZIONE` in testa alla corsa —
    #        e restituisce il `push_log_id` che il chiamante conserva per la
    #        chiusura.
    def start_push_run(
        self,
        *,
        dry_run: bool = False,
        source_types: list[str] | None = None,
        correlation_id: str | None = None,
    ) -> int:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT vendite.fn_start_commessa_push_run(
                    p_dry_run => %s,
                    p_source_types => %s,
                    p_correlation_id => %s::uuid
                )
                """,
                [dry_run, source_types, correlation_id],
            )
            row = cursor.fetchone()
        assert row is not None
        return int(row[0])

    # Scopo: Chiude il giro aperto da `start_push_run` con il suo esito, il
    #        risultato per handler e la durata.
    #
    # ⚠️ `stato` ammette solo i tre esiti FINALI (COMPLETATO | PARZIALE |
    #    ERRORE): `IN_ESECUZIONE` e' lo stato di un giro aperto, non un esito,
    #    e la funzione lo rifiuta con `E_COMMESSA_PUSH_RUN_STATO_NON_FINALE`.
    # ⚠️ `source_types` si ripassa solo se cambia: a DB c'e' un `COALESCE`, cosi'
    #    chiudere senza ripeterli non cancella quelli dichiarati all'apertura.
    def close_push_run(
        self,
        *,
        push_log_id: int,
        stato: str,
        risultato: dict[str, Any] | None = None,
        durata_ms: int | None = None,
        source_types: list[str] | None = None,
    ) -> None:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT vendite.fn_close_commessa_push_run(
                    p_id => %s,
                    p_stato => %s,
                    p_risultato => %s::jsonb,
                    p_durata_ms => %s,
                    p_source_types => %s
                )
                """,
                [
                    push_log_id,
                    stato,
                    self._to_jsonb_param(risultato),
                    durata_ms,
                    source_types,
                ],
            )

    def get_push_log(self, push_log_id: int) -> CommessaPushLogRow | None:
        """Legge un record di push log per id."""
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT id, run_at, dry_run, source_types,
                       risultato, stato, durata_ms
                FROM vendite.commesse_push_log
                WHERE id = %s
                """,
                [push_log_id],
            )
            row = cursor.fetchone()
        if not row:
            return None
        risultato_raw: Any = jsonb_out(row[4])
        return CommessaPushLogRow(
            id=int(row[0]),
            run_at=row[1].isoformat() if row[1] else "",
            dry_run=bool(row[2]),
            source_types=list(row[3]) if row[3] else None,
            risultato=risultato_raw if isinstance(risultato_raw, dict) else None,
            stato=str(row[5]),
            durata_ms=None if row[6] is None else int(row[6]),
        )

    # --- Gruppo 5: Pricing operations (N5, N7, N7-sblocco) ---

    # Scopo: Blocca l'attivita` commessa con FOR UPDATE per prevenire race condition
    #        durante operazioni pricing (N5, N7, N7-sblocco).
    def lock_attivita_for_update(self, attivita_id: int) -> bool:
        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT id FROM vendite.commesse_attivita WHERE id = %s FOR UPDATE",
                [attivita_id],
            )
            return cursor.fetchone() is not None

    # Scopo: Restituisce l'attivita` di una commessa con dati pricing e stato fatturazione.
    def get_attivita_pricing(self, commessa_id: int, attivita_id: int) -> dict[str, Any] | None:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT
                    ca.id,
                    ca.commessa_id,
                    ca.prezzo_snapshot,
                    ca.prezzo_bloccato,
                    ca.listino_versione_id,
                    ca.listino_riga_id,
                    ca.pricing_mode,
                    ca.prezzo_da_riallineare,
                    ca.articolo_id,
                    ca.uom_id,
                    ca.data_attivita,
                    -- Il ripiego della data per il listino quando manca
                    -- `data_attivita` (BB `prezzo_riga_commessa`, come nel push).
                    ca.competenza_mese,
                    ca.meta,
                    -- Identita' e stato della riga: servono ai guard
                    -- dell'annullamento riga manuale (brief-annullamento-righe-
                    -- manuali-commessa §5-bis G3). `sorgente_tipo_id IS NULL`
                    -- e' il discriminante di "riga manuale" (sourceless, cfr.
                    -- fn_build_gruppo_fatturabile_key); `stato_emissione`
                    -- distingue NON_EMESSA / EMESSA / ANNULLATA. Zero costo:
                    -- sono colonne di `ca`, gia' in join.
                    ca.stato_emissione,
                    ca.sorgente_tipo_id,
                    ca.tipo_movimento,
                    sc.codice_interno AS commessa_stato,
                    sc.modificabile AS commessa_modificabile,
                    c.billing_account_id,
                    c.utility_id,
                    c.emittente_soggetto_ruolo_id,
                    af.id AS af_id,
                    af.prezzo_unitario AS af_prezzo_unitario,
                    af.prezzo_bloccato AS af_prezzo_bloccato,
                    af.fattura_riga_id
                  FROM vendite.commesse_attivita ca
                  JOIN vendite.commesse c ON c.id = ca.commessa_id
                  JOIN vendite.stati_commessa sc ON sc.id = c.stato_commessa_id
                  LEFT JOIN vendite.attivita_fatturabili af
                    ON af.commessa_attivita_id = ca.id
                 WHERE ca.commessa_id = %s
                   AND ca.id = %s
                """,
                [commessa_id, attivita_id],
            )
            from apps.core.db._helpers import row_to_dict
            return row_to_dict(cursor)

    # Scopo: Aggiorna prezzo snapshot su commessa_attivita + prezzo_unitario su
    #        attivita_fatturabili, e con il prezzo la sua PROVENIENZA
    #        (`provenienza`: le colonne di `COLONNE_PROVENIENZA_PREZZO`, dal
    #        building block `prezzo_riga_commessa`).
    #        ⭐ Dal 2026-10-08 prezzo e provenienza si scrivono INSIEME: prima si
    #        scriveva il solo prezzo, e la riga riallineata diceva un prezzo
    #        nuovo con la versione di listino, l'origine e la base del prezzo
    #        vecchio. Le nove colonne che `attivita_fatturabili` ha in comune si
    #        propagano con il prezzo, alle stesse condizioni (riga non ancora
    #        in fattura).
    #        ⛔ `provenienza` deve avere ESATTAMENTE quelle colonne: una chiave
    #        in meno lascerebbe in piedi un pezzo della provenienza vecchia
    #        senza che nessuno se ne accorga, quindi si rifiuta.
    def update_attivita_prezzo(
        self,
        attivita_id: int,
        prezzo: str,
        prezzo_bloccato: bool,
        meta: dict[str, Any] | None,
        *,
        provenienza: dict[str, Any],
    ) -> None:
        if set(provenienza) != set(COLONNE_PROVENIENZA_PREZZO):
            raise ValueError(
                "update_attivita_prezzo: provenienza con colonne "
                f"{sorted(provenienza)}, attese {sorted(COLONNE_PROVENIENZA_PREZZO)}"
            )
        parametri = {
            **provenienza,
            "att_id": attivita_id,
            "prezzo": prezzo,
            "bloccato": prezzo_bloccato,
            "meta": json.dumps(meta) if meta else None,
        }
        # Guardrail atomicità (review 2026-07-08): 2 UPDATE sequenziali (commesse_attivita
        # + attivita_fatturabili) resi self-atomici. Il docstring dichiarava "caller gestisce
        # transazione": ora e' self-safe (nested=savepoint se il caller ha gia' un atomic).
        with transaction.atomic(), connection.cursor() as cursor:
            cursor.execute(
                """
                UPDATE vendite.commesse_attivita
                   SET prezzo_snapshot = %(prezzo)s::numeric,
                       prezzo_bloccato = %(bloccato)s,
                       prezzo_da_riallineare = FALSE,
                       prezzo_base_snapshot = %(prezzo_base_snapshot)s,
                       origine_prezzo = %(origine_prezzo)s,
                       tipo_variazione_applicata = %(tipo_variazione_applicata)s,
                       valore_variazione_applicata = %(valore_variazione_applicata)s,
                       promo_id = %(promo_id)s,
                       contratto_id = %(contratto_id)s,
                       categoria_cliente_id_snapshot = %(categoria_cliente_id_snapshot)s,
                       classe_utenza_id_snapshot = %(classe_utenza_id_snapshot)s,
                       listino_riga_id = %(listino_riga_id)s,
                       listino_versione_id = %(listino_versione_id)s,
                       meta = %(meta)s::jsonb
                 WHERE id = %(att_id)s
                """,
                parametri,
            )
            # Propaga su attivita_fatturabili (se esiste la riga collegata)
            cursor.execute(
                """
                UPDATE vendite.attivita_fatturabili
                   SET prezzo_unitario = %(prezzo)s::numeric,
                       prezzo_bloccato = %(bloccato)s,
                       prezzo_base_snapshot = %(prezzo_base_snapshot)s,
                       origine_prezzo = %(origine_prezzo)s,
                       tipo_variazione_applicata = %(tipo_variazione_applicata)s,
                       valore_variazione_applicata = %(valore_variazione_applicata)s,
                       promo_id = %(promo_id)s,
                       contratto_id = %(contratto_id)s,
                       categoria_cliente_id_snapshot = %(categoria_cliente_id_snapshot)s,
                       classe_utenza_id_snapshot = %(classe_utenza_id_snapshot)s,
                       listino_riga_id = %(listino_riga_id)s
                 WHERE commessa_attivita_id = %(att_id)s
                   AND fattura_riga_id IS NULL
                """,
                parametri,
            )

    # --- Gruppo 6: Event log ---
    #
    # `log_event` NON sta piu' qui: e' il building block
    # `EventLogRepositoryMixin` (`_event_log_repo_mixin.py`), estratto con la
    # consegna BE-6 perche' era copia carbone in questo repository e in
    # `pipeline_repository`. La firma e' passata da nove parametri a SEI.

