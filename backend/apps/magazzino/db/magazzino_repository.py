# ------------------------------------------------------------
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Repository dello schema `magazzino` — il documento interno (inventario
#        / rettifica, UNA implementazione parametrica sulla famiglia), il piano
#        di un inventario, la porta sul registro (`fn_posta_*`), i tre lookup
#        di riga e la consultazione (disponibilita', movimenti).
# Note: ⛔ Un repository PER SCHEMA e non uno per entita' (AGENTS.md
#       §repository): inventari, rettifiche, righe, piano e registro stanno
#       insieme finche' non nasce un sottodominio con orchestrazione propria.
#
#       🔴 TUTTE le tabelle di `magazzino` hanno la row security accesa (Lotto
#       1 + Lotto 2): il perimetro e' l'emittente del MAGAZZINO, e le testate,
#       le righe, i movimenti e le viste `security_invoker` lo ereditano. Un
#       percorso che le tocchi senza la GUC dell'operatore non vede niente e
#       non scrive niente. ⛔ Per la stessa ragione questi metodi NON vanno
#       chiamati da un canale di sistema (ruolo BYPASSRLS): li' il perimetro
#       non filtra e le liste mostrerebbero i magazzini di tutti gli
#       emittenti. Il guard e' esplicito nelle letture di lista.
#
#       ⭐ E lo scope applicativo si SOMMA (api.md §Enforcement RLS,
#       defense-in-depth): `add_emittente_scope_condition` su
#       `m.emittente_fiscale_id` (il magazzino, che e' l'ancora del perimetro:
#       le testate non hanno l'emittente in colonna).
#
#       ⚠️ Le SQL interpolano SOLO identificatori dalla configurazione della
#       famiglia (`db/famiglie.py`, validati da regex all'import) e dalle
#       whitelist di ordinamento; i VALORI viaggiano nei `params`.
#
#       ⭐ 2026-09-26: testate e righe si scrivono coi BB core
#       (`execute_dynamic_insert` / `execute_dynamic_update` /
#       `sql_set_clause`). ⛔ Whitelist RIGIDA: una colonna fuori da
#       `_COLONNE_TESTATA_AGGIORNABILI` / `_colonne_riga` (o `descrizione` su
#       una famiglia che non la ha) e' `RuntimeError`, non piu' uno scarto
#       silenzioso — il contratto dell'operatore lo chiude il service
#       (`validate_allowed_keys`, 400) prima di arrivare qui.
# ------------------------------------------------------------

from __future__ import annotations

from datetime import date
from typing import Any, cast

from django.db import connection

from apps.core.db._helpers import (
    colonna_ordinamento,
    sql_order_direction_lista,
    predicato_giorno_operativo,
    pattern_contiene,
    RicercaFull,
    add_ricerca_full_condition,
    call_jsonb_fn,
    fetchone_scalar,
    jsonb_out,
    rows_to_list,
    sql_order_clause,
    sql_tiebreak_direction,
)
from apps.core.db.emittente_scope_helpers import add_emittente_scope_condition
from apps.core.db.sql_write_helpers import (
    execute_dynamic_insert,
    execute_dynamic_update,
    sql_set_clause,
)
from apps.magazzino.db._helpers import guard_canale_sistema, lista_paginata, meta_mai_null
from apps.magazzino.db.famiglie import FAMIGLIE, INVENTARI, RETTIFICHE, FamigliaDocumentoInterno
from apps.magazzino.types import (
    BloccoRow,
    DisponibilitaArticoloRow,
    DisponibilitaRow,
    DocumentoInternoRow,
    MovimentoPostato,
    MovimentoRow,
    PianoRiepilogo,
    PianoRigaRow,
    RigaDocumentoInternoRow,
)

_FN = "magazzino.magazzino_repository"

# Il guard di parametro del dominio (`E_MAG_CHIAMATA_NON_VALIDA`, TECNICO)
# vive in `db/_helpers.py` dal 2026-09-21, col guard che lo solleva.


# ══════════════════════════════════════════════════════════════════
#  Whitelist di ordinamento — chiavate sul `campo_sorgente` FISICO
# ══════════════════════════════════════════════════════════════════

# Le testate (inventari e rettifiche condividono la proiezione, quindi la
# whitelist). `stato` e' lo stato grezzo: si ordina per codice.
DOCUMENTI_SORT_COLUMNS: dict[str, str] = {
    "data": "data",
    "stato": "stato",
    "magazzino_codice": "magazzino_codice",
    "magazzino_descrizione": "magazzino_descrizione",
    "descrizione": "descrizione",
    "righe_count": "righe_count",
    "data_insert": "data_insert",
    "user_insert": "user_insert",
    "id": "id",
}
DOCUMENTI_SORT_COLONNE_DATA: frozenset[str] = frozenset({"data", "data_insert"})

# Le righe: una whitelist PER FAMIGLIA. ⛔ Il nome della quantita' e' fisico
# e diverso (`qta_contata` / `qta_delta`), e una whitelist unica che le
# portasse entrambe dichiarerebbe ammessa su ogni famiglia una colonna che la
# sua SELECT non ha — cioe' un 500 su un valore «ammesso»
# (`feedback_contratto_dichiarato_provalo_intero`; il presidio
# `test_ogni_ordinamento_dichiarato_produce_sql_valido` l'ha trovato alla
# prima stesura). Il comune sta in `_RIGHE_SORT_COMUNI`, il resto e' di dato.
_RIGHE_SORT_COMUNI: dict[str, str] = {
    "id": "id",
    "articolo_codice": "articolo_codice",
    "articolo_descrizione": "articolo_descrizione",
    "costo_unitario": "costo_unitario",
    "ubicazione_codice": "ubicazione_codice",
    "lotto_codice": "lotto_codice",
    "asset_seriale": "asset_seriale",
}


# Scopo: la whitelist delle righe della famiglia — letta dalla config, non da
#        un `if` sul codice. E' la SEDE UNICA: le due costanti qui sotto ne
#        sono la lettura per nome (seed delle liste, `gen_seed_lista.py`), non
#        una seconda copia che possa divergere.
def righe_sort_columns(f: FamigliaDocumentoInterno) -> dict[str, str]:
    colonne = dict(_RIGHE_SORT_COMUNI)
    colonne[f.col_qta] = f.col_qta
    if f.ha_piano:
        colonne["qta_sistema"] = "qta_sistema"
    if f.con_motivo:
        colonne["motivo"] = "motivo"
    return colonne


INVENTARIO_RIGHE_SORT_COLUMNS: dict[str, str] = righe_sort_columns(INVENTARI)
RETTIFICA_RIGHE_SORT_COLUMNS: dict[str, str] = righe_sort_columns(RETTIFICHE)

# Il piano. ⚠️ Nessun `id`: le posizioni `NON_CONTATA` non sono righe.
PIANO_SORT_COLUMNS: dict[str, str] = {
    "articolo_codice": "articolo_codice",
    "articolo_descrizione": "articolo_descrizione",
    "ubicazione_codice": "ubicazione_codice",
    "lotto_codice": "lotto_codice",
    "asset_seriale": "asset_seriale",
    "qta_contata": "qta_contata",
    "qta_sistema": "qta_sistema",
    "delta": "delta",
    "esito": "esito",
}

DISPONIBILITA_SORT_COLUMNS: dict[str, str] = {
    "articolo_codice": "articolo_codice",
    "articolo_descrizione": "articolo_descrizione",
    "magazzino_codice": "magazzino_codice",
    "magazzino_descrizione": "magazzino_descrizione",
    "giacenza": "giacenza",
    "bloccata": "bloccata",
    "disponibile": "disponibile",
    "n_blocchi": "n_blocchi",
}

DISPONIBILITA_ARTICOLI_SORT_COLUMNS: dict[str, str] = {
    "articolo_codice": "articolo_codice",
    "articolo_descrizione": "articolo_descrizione",
    "giacenza": "giacenza",
    "bloccata": "bloccata",
    "disponibile": "disponibile",
    "n_magazzini": "n_magazzini",
}

MOVIMENTI_SORT_COLUMNS: dict[str, str] = {
    "id": "id",
    "data_mov": "data_mov",
    "articolo_codice": "articolo_codice",
    "articolo_descrizione": "articolo_descrizione",
    "magazzino_codice": "magazzino_codice",
    "qta": "qta",
    "costo_unitario": "costo_unitario",
    "causale_codice": "causale_codice",
    "causale_descrizione": "causale_descrizione",
    "ubicazione_codice": "ubicazione_codice",
    "lotto_codice": "lotto_codice",
    "asset_seriale": "asset_seriale",
    "sorgente_codice_interno": "sorgente_codice_interno",
    "data_insert": "data_insert",
}
MOVIMENTI_SORT_COLONNE_DATA: frozenset[str] = frozenset({"data_mov", "data_insert"})


# ══════════════════════════════════════════════════════════════════
#  Frammenti SQL
# ══════════════════════════════════════════════════════════════════

# La decodifica di articolo, ubicazione, lotto e seriale di una riga (o di una
# posizione del piano, o di un movimento): la STESSA per le tre letture.
_DECODIFICA_POSIZIONE_JOIN = """
    JOIN catalogo.articoli a ON a.id = {alias}.articolo_id
    LEFT JOIN magazzino.ubicazioni u ON u.id = {alias}.ubicazione_id
    LEFT JOIN magazzino.lotti l ON l.id = {alias}.lotto_id
    LEFT JOIN magazzino.assets s ON s.id = {alias}.asset_id
"""

_DECODIFICA_POSIZIONE_COLONNE = """
    a.codice            AS articolo_codice,
    a.descrizione       AS articolo_descrizione,
    u.codice            AS ubicazione_codice,
    l.codice            AS lotto_codice,
    s.seriale           AS asset_seriale
"""

# Il magazzino, ancora del perimetro: codice/descrizione a video e il flag che
# decide il campo ubicazione nel form di riga.
_MAGAZZINO_JOIN = "JOIN magazzino.magazzini m ON m.id = {alias}.magazzino_id"
_MAGAZZINO_COLONNE = """
    m.codice            AS magazzino_codice,
    m.descrizione       AS magazzino_descrizione,
    m.usa_ubicazioni    AS magazzino_usa_ubicazioni
"""


# Scopo: la SELECT di testata di una famiglia — testata + magazzino + conteggio
#        righe. ⚠️ `descrizione` e' `NULL` sulla rettifica, che la colonna non
#        ce l'ha: la proiezione resta UNA per le due famiglie.
def _documento_select(f: FamigliaDocumentoInterno) -> str:
    descrizione = "t.descrizione" if f.ha_descrizione else "NULL::varchar"
    return f"""
        SELECT
            t.id, t.uid, t.data,
            t.{f.col_stato}     AS stato,
            t.magazzino_id,
            {_MAGAZZINO_COLONNE},
            {descrizione}       AS descrizione,
            (SELECT count(*)::int FROM {f.tabella_righe} r
              WHERE r.{f.fk_riga} = t.id) AS righe_count,
            t.sorgente_tipo_id, t.sorgente_id, t.sorgente_riga, t.sorgente_uid,
            t.meta, t.data_insert, t.user_insert, t.data_update, t.user_update
          FROM {f.tabella} t
          {_MAGAZZINO_JOIN.format(alias='t')}
    """  # noqa: S608 — tabelle/colonne dal registro frozen FAMIGLIE (famiglie.py), frammenti costanti del modulo


# Scopo: la SELECT delle righe di una famiglia, decodificate.
def _righe_select(f: FamigliaDocumentoInterno) -> str:
    qta_sistema = "r.qta_sistema," if f.ha_piano else ""
    motivo = "r.motivo," if f.con_motivo else ""
    return f"""
        SELECT
            r.id, r.{f.fk_riga}, r.articolo_id,
            {_DECODIFICA_POSIZIONE_COLONNE},
            a.requires_lotto    AS articolo_requires_lotto,
            a.requires_serial   AS articolo_requires_serial,
            r.{f.col_qta},
            {qta_sistema}
            {motivo}
            r.costo_unitario, r.ubicazione_id, r.lotto_id, r.asset_id,
            r.meta, r.data_insert, r.user_insert, r.data_update
          FROM {f.tabella_righe} r
          {_DECODIFICA_POSIZIONE_JOIN.format(alias='r')}
    """  # noqa: S608 — tabelle/colonne dal registro frozen FAMIGLIE (famiglie.py), frammenti costanti del modulo


# ⭐ `chiave_riga`: la CHIAVE STABILE di una riga che non ha un `id` — il piano
#    (`riga_id` e' NULL sulle posizioni NON_CONTATA) e le due disponibilita'
#    (letture di vista). `<ListaConfigurabile>` chiava le righe su `dataKey`:
#    senza, tutte le righe avrebbero chiave `undefined`, con le righe rese in
#    ordine sbagliato al cambio pagina e un'espansione sola per tutte — senza
#    nessun errore. ⚠️ `concat` e non `concat_ws`: il NULL deve restare una
#    posizione vuota (`A|5||` e `A||5|` sono due chiavi), non sparire.
_PIANO_SELECT = f"""
    SELECT
        concat(p.articolo_id, '|', p.ubicazione_id, '|', p.lotto_id, '|', p.asset_id)
                            AS chiave_riga,
        p.riga_id, p.articolo_id, p.ubicazione_id, p.lotto_id, p.asset_id,
        {_DECODIFICA_POSIZIONE_COLONNE},
        p.qta_contata, p.qta_sistema, p.delta, p.causale_codice_interno,
        p.esito, p.posting_blocco_reason, p.posting_blocco_reason_key
      FROM magazzino.fn_inventario_piano(%s) p
      {_DECODIFICA_POSIZIONE_JOIN.format(alias='p')}
"""  # noqa: S608 — frammenti costanti del modulo (_DECODIFICA_POSIZIONE_*), valori come parametri

# Cosa si PUO' cercare in ogni lista; cosa si cerca lo dice il catalogo
# (`add_ricerca_full_condition`, brief-be-ricerca-full-liste-residue §2).
# ⭐ Mappe `campo_sorgente → espressione`: il valore e' la STESSA espressione che
#    la `SELECT` proietta con quel nome — si cerca su cio' che si mostra.
# ⭐ Testate e righe: una dichiarazione per famiglia, DERIVATA dal registro
#    `FAMIGLIE` coi flag che la famiglia gia' porta (`ha_descrizione`,
#    `con_motivo`) — le stesse che decidono la `SELECT`. ⛔ Non una voce scritta
#    a mano per famiglia: una terza famiglia «e' una riga in `famiglie.py`»
#    (il contratto del registro), e una mappa cablata le darebbe un `KeyError`
#    su ogni apertura di lista, anche senza cercare.
_RICERCA_ARTICOLO: dict[str, str] = {
    "articolo_codice": "a.codice",
    "articolo_descrizione": "a.descrizione",
}
_RICERCA_DOCUMENTI: dict[str, RicercaFull] = {
    f.lista_codice: RicercaFull(f.lista_codice, {
        "magazzino_codice": "m.codice",
        "magazzino_descrizione": "m.descrizione",
        **({"descrizione": "t.descrizione"} if f.ha_descrizione else {}),
    })
    for f in FAMIGLIE.values()
}
_RICERCA_RIGHE: dict[str, RicercaFull] = {
    f.lista_righe_codice: RicercaFull(f.lista_righe_codice, {
        **_RICERCA_ARTICOLO,
        **({"motivo": "r.motivo"} if f.con_motivo else {}),
    })
    for f in FAMIGLIE.values()
}
_RICERCA_PIANO = RicercaFull("magazzino.inventario_piano", _RICERCA_ARTICOLO)
_RICERCA_MOVIMENTI = RicercaFull("magazzino.movimenti", _RICERCA_ARTICOLO)
_RICERCA_DISPONIBILITA = RicercaFull("magazzino.disponibilita", {
    **_RICERCA_ARTICOLO,
    "magazzino_codice": "m.codice",
})
_RICERCA_DISPONIBILITA_ARTICOLI = RicercaFull("magazzino.disponibilita_articoli", _RICERCA_ARTICOLO)

_DISPONIBILITA_SELECT = f"""
    SELECT
        concat(d.articolo_id, '|', d.magazzino_id) AS chiave_riga,
        d.articolo_id,
        a.codice            AS articolo_codice,
        a.descrizione       AS articolo_descrizione,
        a.requires_lotto    AS articolo_requires_lotto,
        a.requires_serial   AS articolo_requires_serial,
        d.magazzino_id,
        {_MAGAZZINO_COLONNE},
        d.giacenza, d.bloccata, d.disponibile, d.n_blocchi::int AS n_blocchi
      FROM magazzino.vw_disponibilita d
      JOIN catalogo.articoli a ON a.id = d.articolo_id
      {_MAGAZZINO_JOIN.format(alias='d')}
"""  # noqa: S608 — frammenti costanti del modulo (_MAGAZZINO_*)

_DISPONIBILITA_ARTICOLI_SELECT = """
    SELECT
        d.articolo_id::text AS chiave_riga,
        d.articolo_id,
        a.codice            AS articolo_codice,
        a.descrizione       AS articolo_descrizione,
        d.giacenza, d.bloccata, d.disponibile, d.n_magazzini::int AS n_magazzini
      FROM magazzino.vw_disponibilita_articolo d
      JOIN catalogo.articoli a ON a.id = d.articolo_id
"""

# I blocchi: gli attesi APERTA in USCITA — lo stesso filtro di
# `vw_disponibilita` (che li conta), qui uno per uno.
_BLOCCHI_SELECT = """
    SELECT
        x.id, x.qta, x.data_prevista,
        c.codice            AS causale_codice,
        c.descrizione       AS causale_descrizione,
        sg.codice_interno   AS sorgente_codice_interno,
        x.sorgente_id, x.sorgente_riga, x.sorgente_dettaglio, x.sorgente_uid,
        x.soggetto_ruolo_id,
        sr.ragione_sociale_completa AS soggetto_ragione_sociale,
        x.nota, x.data_insert
      FROM magazzino.movimenti_attesi x
      JOIN magazzino.causali c ON c.id = x.causale_id
      LEFT JOIN config.sorgenti sg ON sg.id = x.sorgente_tipo_id
      LEFT JOIN anagrafiche.vw_soggetti_ruoli_dettaglio sr
             ON sr.soggetto_ruolo_id = x.soggetto_ruolo_id
     WHERE x.stato = 'APERTA' AND x.qta < 0
       AND x.articolo_id = %s AND x.magazzino_id = %s
     ORDER BY x.data_prevista NULLS LAST, x.id
"""

_MOVIMENTI_SELECT = f"""
    SELECT
        mv.id, mv.data_mov, mv.articolo_id,
        {_DECODIFICA_POSIZIONE_COLONNE},
        mv.magazzino_id,
        {_MAGAZZINO_COLONNE},
        mv.qta, mv.costo_unitario,
        mv.causale_id,
        c.codice            AS causale_codice,
        c.descrizione       AS causale_descrizione,
        c.segno             AS causale_segno,
        mv.ubicazione_id, mv.lotto_id, mv.asset_id,
        mv.sorgente_tipo_id,
        sg.codice_interno   AS sorgente_codice_interno,
        mv.sorgente_id, mv.sorgente_riga, mv.sorgente_dettaglio,
        mv.sorgente_uid, mv.transfer_uid,
        mv.storno_di_movimento_id, mv.data_insert, mv.user_insert
      FROM magazzino.movimenti mv
      {_DECODIFICA_POSIZIONE_JOIN.format(alias='mv')}
      {_MAGAZZINO_JOIN.format(alias='mv')}
      JOIN magazzino.causali c ON c.id = mv.causale_id
      LEFT JOIN config.sorgenti sg ON sg.id = mv.sorgente_tipo_id
"""  # noqa: S608 — frammenti costanti del modulo (_DECODIFICA_POSIZIONE_*, _MAGAZZINO_*)

# Le colonne di testata che il PATCH puo' toccare. ⛔ `magazzino_id` NO: si
# sceglie alla nascita (R-4 lo difendera' a DB). `descrizione` solo sulla
# famiglia che ce l'ha — lo decide il service dalla config.
_COLONNE_TESTATA_AGGIORNABILI = frozenset({"data", "descrizione", "meta"})
# Le colonne jsonb scritte dal dominio (`meta`, NOT NULL: `meta_mai_null`).
_JSONB_COLS = ("meta",)

# Le colonne di riga che si scrivono (create e PATCH). La quantita' e il
# motivo variano per famiglia e li aggiunge `_colonne_riga`.
_COLONNE_RIGA_COMUNI = frozenset(
    {"articolo_id", "costo_unitario", "ubicazione_id", "lotto_id", "asset_id", "meta"}
)


def _colonne_riga(f: FamigliaDocumentoInterno) -> frozenset[str]:
    extra = {f.col_qta}
    if f.con_motivo:
        extra.add("motivo")
    return _COLONNE_RIGA_COMUNI | extra


class MagazzinoRepository:
    """Accesso dati dello schema `magazzino`."""

    # ══════════════════════════════════════════════════════════════
    #  Guard strutturale + lista paginata: `db/_helpers.py` (condivisi con
    #  `anagrafiche_magazzino_repository` dal 2026-09-21)
    # ══════════════════════════════════════════════════════════════

    # ══════════════════════════════════════════════════════════════
    #  Magazzini (l'ancora del perimetro)
    # ══════════════════════════════════════════════════════════════

    # Scopo: Il magazzino, se esiste, e' attivo ed e' nel perimetro di chi
    #        legge (RLS). `None` altrimenti — e i tre casi restano
    #        indistinguibili al chiamante, di proposito.
    def get_magazzino(self, magazzino_id: int) -> dict[str, Any] | None:
        sql = """
            SELECT m.id, m.codice, m.descrizione, m.usa_ubicazioni,
                   m.emittente_fiscale_id, m.attivo
              FROM magazzino.magazzini m
             WHERE m.id = %s AND m.attivo IS TRUE
        """
        with connection.cursor() as cursor:
            cursor.execute(sql, [int(magazzino_id)])
            rows = rows_to_list(cursor)
        return rows[0] if rows else None

    # ══════════════════════════════════════════════════════════════
    #  Documento interno — lettura
    # ══════════════════════════════════════════════════════════════

    # Scopo: L'elenco paginato delle testate di una famiglia.
    # Perimetro: RLS (invoker) + scope applicativo sull'emittente del magazzino.
    def list_documenti(
        self,
        f: FamigliaDocumentoInterno,
        *,
        auth_user_id: int | None,
        magazzino_id: int | None = None,
        stato: str | None = None,
        data_da: date | None = None,
        data_a: date | None = None,
        search: str | None = None,
        order_by: str | None = None,
        order_dir: str | None = None,
        limit: int,
        offset: int,
    ) -> tuple[list[DocumentoInternoRow], int]:
        guard_canale_sistema(f"{_FN}.list_documenti")
        conditions: list[str] = []
        params: list[Any] = []
        add_emittente_scope_condition(
            conditions, params, auth_user_id=auth_user_id, column="m.emittente_fiscale_id",
        )
        if magazzino_id is not None:
            conditions.append("t.magazzino_id = %s")
            params.append(int(magazzino_id))
        if stato is not None:
            conditions.append(f"t.{f.col_stato} = %s")
            params.append(stato)
        if data_da is not None:
            conditions.append("t.data >= %s")
            params.append(data_da)
        if data_a is not None:
            conditions.append("t.data <= %s")
            params.append(data_a)
        add_ricerca_full_condition(conditions, params, search, _RICERCA_DOCUMENTI[f.lista_codice])
        where = ("WHERE " + " AND ".join(conditions)) if conditions else ""

        ordinamento = sql_order_clause(
            order_by, order_dir,
            colonne=DOCUMENTI_SORT_COLUMNS,
            default="data",
            tiebreak="id",
            default_desc=True,
            colonne_desc=DOCUMENTI_SORT_COLONNE_DATA,
        )
        rows, total = lista_paginata(
            select_sql=f"{_documento_select(f)} {where}",
            params=params,
            order_clause=ordinamento,
            limit=limit,
            offset=offset,
        )
        return [cast(DocumentoInternoRow, r) for r in rows], total

    # Scopo: La testata, o `None` se non esiste / non e' visibile.
    def get_documento(
        self, f: FamigliaDocumentoInterno, doc_id: int
    ) -> DocumentoInternoRow | None:
        sql = f"{_documento_select(f)} WHERE t.id = %s"
        with connection.cursor() as cursor:
            cursor.execute(sql, [int(doc_id)])
            rows = rows_to_list(cursor)
        return rows[0] if rows else None  # type: ignore[return-value]

    # Scopo: La capability del documento per il dettaglio API: quali azioni di
    #        stato proporre, se «Registra» e' acceso e — se no — il primo
    #        motivo, che cosa e' ancora modificabile, la nota dello stato
    #        chiuso. Wrapper sull'involucro della famiglia
    #        (`script.fn_available_actions_inventario` / `_rettifica`).
    # ⛔ Blob OPACO: il backend TRASPORTA, non deduce (api.md §Capability). Le
    #    azioni vengono dalla matrice che il guard fa rispettare e la terna di
    #    «registra» dal primo motivo della check che le madri del posting
    #    chiamano: ricalcolarle qui sarebbe la seconda sede di due regole.
    # ⚠️ `{}` se la funzione torna NULL (documento fuori perimetro RLS o
    #    inesistente): il 404 no-leak lo da' il service sulla TESTATA, letta
    #    prima — una capability non solleva.
    def get_capabilities(self, f: FamigliaDocumentoInterno, doc_id: int) -> dict[str, Any]:
        return call_jsonb_fn(f.fn_capability, int(doc_id))

    # Scopo: Il riepilogo del piano di un inventario: quanti esiti di ogni
    #        specie, in una lettura sola (`count(*) FILTER`).
    def piano_riepilogo(self, inventario_id: int) -> PianoRiepilogo:
        sql = """
            SELECT
                count(*)::int                                            AS n_righe,
                count(*) FILTER (WHERE p.esito IN ('INV_INIZIALE', 'RETT_POS', 'RETT_NEG'))::int
                                                                         AS n_con_delta,
                count(*) FILTER (WHERE p.esito = 'INVARIATA')::int       AS n_invariate,
                count(*) FILTER (WHERE p.esito = 'NON_CONTATA')::int     AS n_non_contate,
                count(*) FILTER (WHERE p.esito = 'NON_POSTABILE')::int   AS n_non_postabili
              FROM magazzino.fn_inventario_piano(%s) p
        """
        with connection.cursor() as cursor:
            cursor.execute(sql, [int(inventario_id)])
            rows = rows_to_list(cursor)
        return rows[0]  # type: ignore[return-value]

    # Scopo: Il piano di un inventario, paginato e decodificato.
    # ⚠️ L'ordine chiude con la CATENA delle chiavi naturali della posizione
    #    (articolo, ubicazione, lotto, asset), non con `riga_id`: sulle
    #    posizioni `NON_CONTATA` `riga_id` e' NULL e non spareggerebbe niente
    #    — e' uno dei casi che `sql_order_clause` non descrive di proposito
    #    (catalogo BB §Ordinamento: «catena di chiavi naturali»).
    def list_piano(
        self,
        inventario_id: int,
        *,
        search: str | None = None,
        order_by: str | None = None,
        order_dir: str | None = None,
        limit: int,
        offset: int,
    ) -> tuple[list[PianoRigaRow], int]:
        conditions: list[str] = []
        params: list[Any] = [int(inventario_id)]
        add_ricerca_full_condition(conditions, params, search, _RICERCA_PIANO)
        where = ("WHERE " + " AND ".join(conditions)) if conditions else ""
        colonna = colonna_ordinamento(order_by, PIANO_SORT_COLUMNS) or "articolo_codice"
        direzione = sql_order_direction_lista(order_by, order_dir, colonne=PIANO_SORT_COLUMNS)
        rows, total = lista_paginata(
            select_sql=f"{_PIANO_SELECT} {where}",
            params=params,
            order_clause=(
                f"{colonna} {direzione}, articolo_id, ubicazione_id, lotto_id, asset_id"
            ),
            limit=limit,
            offset=offset,
        )
        return rows, total  # type: ignore[return-value]

    # ══════════════════════════════════════════════════════════════
    #  Documento interno — scrittura
    # ══════════════════════════════════════════════════════════════

    # Scopo: Crea la BOZZA di una famiglia. L'app scrive le testate: sono sotto
    #        RLS (`WITH CHECK`), non dietro la porta della primitiva.
    def create_documento(
        self,
        f: FamigliaDocumentoInterno,
        *,
        magazzino_id: int,
        data: date | None,
        descrizione: str | None,
        meta: dict[str, Any] | None,
    ) -> int:
        # Chiavi LETTERALI (`allowed=None`). `skip_none`: `data` assente lascia
        # il DEFAULT del DB (oggi), `descrizione` assente resta NULL; `meta`
        # viaggia sempre (`{}` se None, la colonna e' NOT NULL).
        valori: dict[str, Any] = {"magazzino_id": int(magazzino_id), "meta": meta or {}, "data": data}
        if f.ha_descrizione:
            valori["descrizione"] = descrizione
        riga = execute_dynamic_insert(f.tabella, valori, allowed=None, skip_none=True, jsonb=_JSONB_COLS)
        return int(riga["id"])

    # Scopo: Aggiorna i campi di testata che una persona compila.
    # ⚠️ `None` AZZERA il campo nullable (la semantica dei documenti): `data`
    #    e' NOT NULL e il service non la manda a `None`; `meta` None vale `{}`.
    # ⛔ `descrizione` su una famiglia senza la colonna (rettifica) e' fuori
    #    whitelist: `RuntimeError`, non piu' scartata (il service non la ammette).
    def update_documento(
        self, f: FamigliaDocumentoInterno, doc_id: int, campi: dict[str, Any]
    ) -> bool:
        ammesse = _COLONNE_TESTATA_AGGIORNABILI
        if not f.ha_descrizione:
            ammesse = ammesse - {"descrizione"}
        return execute_dynamic_update(
            f.tabella, int(doc_id), meta_mai_null(campi), allowed=ammesse, jsonb=_JSONB_COLS,
        )

    # Scopo: Chiede al database il cambio di stato: `UPDATE … SET <stato>` e il
    #        guard decide (`E_MAG_DOCUMENTO_TRANSIZIONE_NON_AMMESSA`, la porta
    #        `POSTED`). Zero righe = la testata non c'e' (o non e' visibile).
    def set_stato_documento(
        self, f: FamigliaDocumentoInterno, doc_id: int, stato: str
    ) -> int:
        sql = f"UPDATE {f.tabella} SET {f.col_stato} = %s WHERE id = %s"  # noqa: S608 — tabella e colonna di stato dal registro FAMIGLIE, valori come parametri
        with connection.cursor() as cursor:
            cursor.execute(sql, [stato, int(doc_id)])
            return cursor.rowcount

    # Scopo: Elimina una testata. Il DB decide (`E_MAG_DOCUMENTO_NON_ELIMINABILE`
    #        fuori da `DRAFT`); le righe cascano.
    def delete_documento(self, f: FamigliaDocumentoInterno, doc_id: int) -> int:
        sql = f"DELETE FROM {f.tabella} WHERE id = %s"  # noqa: S608 — tabella dal registro FAMIGLIE, valori come parametri
        with connection.cursor() as cursor:
            cursor.execute(sql, [int(doc_id)])
            return cursor.rowcount

    # Scopo: IL POSTING — una sola `SELECT` sulla funzione madre, atomica per
    #        costruzione (api.md §Atomicita'). Rifiuta non-`CONFIRM`, senza
    #        righe, righe non postabili, fuori perimetro: il repository passa.
    def posta_documento(
        self, f: FamigliaDocumentoInterno, doc_id: int
    ) -> list[MovimentoPostato]:
        sql = f"SELECT movimento_id, riga_id, qta FROM {f.fn_posta}(%s)"  # noqa: S608 — funzione di posting dal registro FAMIGLIE, valori come parametri
        with connection.cursor() as cursor:
            cursor.execute(sql, [int(doc_id)])
            return rows_to_list(cursor)  # type: ignore[return-value]

    # ══════════════════════════════════════════════════════════════
    #  Blocchi manuali (Lotto 3 D-L3-j, R-5): due verbi DEFINER con
    #  `fn_guard_azione(…, 'blocca_merce')` nella prima riga; l'app non
    #  scrive `movimenti_attesi`.
    # ══════════════════════════════════════════════════════════════

    # Scopo: Apre un blocco (una promessa: pezzi riservati a qualcuno, che
    #        fermano gli scarichi degli altri). Ritorna l'id del blocco.
    def apri_blocco(
        self, *, magazzino_id: int, articolo_id: str, qta: Any,
        soggetto_ruolo_id: int | None, nota: str | None,
        lotto_id: int | None, asset_id: int | None, ubicazione_id: int | None,
    ) -> int:
        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT magazzino.fn_apri_blocco(%s, %s::uuid, %s, %s, %s, %s, %s, %s)",
                [magazzino_id, articolo_id, qta, soggetto_ruolo_id, nota,
                 lotto_id, asset_id, ubicazione_id],
            )
            row = cursor.fetchone()
        assert row is not None
        return int(row[0])

    # Scopo: Libera un blocco con un atto (autore, momento e nota: M-3).
    def libera_blocco(self, blocco_id: int, nota: str | None) -> None:
        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT magazzino.fn_libera_blocco(%s, %s)", [int(blocco_id), nota],
            )

    # ══════════════════════════════════════════════════════════════
    #  Righe
    # ══════════════════════════════════════════════════════════════

    # Scopo: Le righe di una testata, paginate e decodificate.
    def list_righe(
        self,
        f: FamigliaDocumentoInterno,
        doc_id: int,
        *,
        search: str | None = None,
        order_by: str | None = None,
        order_dir: str | None = None,
        limit: int,
        offset: int,
    ) -> tuple[list[RigaDocumentoInternoRow], int]:
        ordinamento = sql_order_clause(
            order_by, order_dir,
            colonne=righe_sort_columns(f),
            default="id",
            tiebreak="id",
        )
        conditions: list[str] = [f"r.{f.fk_riga} = %s"]
        params: list[Any] = [int(doc_id)]
        add_ricerca_full_condition(conditions, params, search, _RICERCA_RIGHE[f.lista_righe_codice])
        rows, total = lista_paginata(
            select_sql=f"{_righe_select(f)} WHERE {' AND '.join(conditions)}",
            params=params,
            order_clause=ordinamento,
            limit=limit,
            offset=offset,
        )
        return [cast(RigaDocumentoInternoRow, r) for r in rows], total

    # Scopo: Una riga DELLA testata indicata: la coppia (documento, riga) e'
    #        la risorsa dell'URL, e una riga di un altro documento non c'e'.
    def get_riga(
        self, f: FamigliaDocumentoInterno, doc_id: int, riga_id: int
    ) -> RigaDocumentoInternoRow | None:
        sql = f"{_righe_select(f)} WHERE r.id = %s AND r.{f.fk_riga} = %s"
        with connection.cursor() as cursor:
            cursor.execute(sql, [int(riga_id), int(doc_id)])
            rows = rows_to_list(cursor)
        return rows[0] if rows else None  # type: ignore[return-value]

    # Scopo: Inserisce una riga. Il guard di famiglia (`E_MAG_DOCUMENTO_
    #        RIGHE_CONGELATE`), i CHECK e l'UNIQUE di posizione rispondono da
    #        soli: qui si scrive e basta.
    def create_riga(
        self, f: FamigliaDocumentoInterno, doc_id: int, campi: dict[str, Any]
    ) -> int:
        # La FK verso la testata viene dall'argomento e VINCE sul payload.
        riga = execute_dynamic_insert(
            f.tabella_righe,
            meta_mai_null({**campi, f.fk_riga: int(doc_id)}),
            allowed=_colonne_riga(f) | {f.fk_riga},
            jsonb=_JSONB_COLS,
        )
        return int(riga["id"])

    # Scopo: Aggiorna una riga della testata indicata. `None` azzera un campo
    #        nullable (togliere il lotto, l'ubicazione, il costo). Legata alla
    #        SUA testata nella `WHERE`: per questo il SET dal BB e il WHERE qui.
    def update_riga(
        self, f: FamigliaDocumentoInterno, doc_id: int, riga_id: int, campi: dict[str, Any]
    ) -> bool:
        if not campi:
            return False
        set_sql, params = sql_set_clause(meta_mai_null(campi), allowed=_colonne_riga(f), jsonb=_JSONB_COLS)
        sql = (
            f"UPDATE {f.tabella_righe} SET {set_sql} "  # noqa: S608 — tabella/FK dal registro FAMIGLIE, SET da sql_set_clause (colonne verificate sulla whitelist _colonne_riga), valori come parametri
            f"WHERE id = %s AND {f.fk_riga} = %s"
        )
        with connection.cursor() as cursor:
            cursor.execute(sql, [*params, int(riga_id), int(doc_id)])
            return cursor.rowcount > 0

    # Scopo: Elimina una riga della testata indicata (il guard di famiglia
    #        decide se lo stato lo ammette).
    def delete_riga(self, f: FamigliaDocumentoInterno, doc_id: int, riga_id: int) -> int:
        sql = f"DELETE FROM {f.tabella_righe} WHERE id = %s AND {f.fk_riga} = %s"  # noqa: S608 — tabella e FK dal registro FAMIGLIE, valori come parametri
        with connection.cursor() as cursor:
            cursor.execute(sql, [int(riga_id), int(doc_id)])
            return cursor.rowcount

    # Scopo: I motivi per cui una riga NON sarebbe scrivibile a registro —
    #        `script.fn_check_riga_magazzino` cosi' com'e': la stessa funzione
    #        che la primitiva e il piano usano (§12.5.2, «cio' che si vede e'
    #        cio' che verra' scritto»). `[]` = tutto bene.
    def check_riga(
        self,
        *,
        magazzino_id: int,
        articolo_id: str,
        lotto_id: int | None,
        asset_id: int | None,
        ubicazione_id: int | None,
    ) -> list[dict[str, Any]]:
        sql = "SELECT script.fn_check_riga_magazzino(%s, %s::uuid, %s, %s, %s)"
        with connection.cursor() as cursor:
            cursor.execute(
                sql, [int(magazzino_id), str(articolo_id), lotto_id, asset_id, ubicazione_id],
            )
            esito = jsonb_out(fetchone_scalar(cursor))
        return list(esito or [])

    # ══════════════════════════════════════════════════════════════
    #  I lookup di riga (ubicazioni del magazzino, lotti e seriali dell'articolo)
    # ══════════════════════════════════════════════════════════════

    # Scopo: Le ubicazioni ATTIVE di un magazzino (filtrate dalla RLS).
    def lookup_ubicazioni(self, magazzino_id: int) -> list[dict[str, Any]]:
        sql = """
            SELECT u.id, u.codice, u.descrizione, u.tipo_id,
                   tu.codice AS tipo_codice, u.parent_id
              FROM magazzino.ubicazioni u
              JOIN config.tipi_ubicazione tu ON tu.id = u.tipo_id
             WHERE u.magazzino_id = %s AND u.attivo IS TRUE
             ORDER BY u.codice, u.id
        """
        with connection.cursor() as cursor:
            cursor.execute(sql, [int(magazzino_id)])
            return rows_to_list(cursor)

    # Scopo: I lotti ATTIVI di un articolo, con ricerca libera sul codice.
    # ⚠️ `magazzino.lotti` non ha RLS ne' emittente: un lotto e' dell'articolo.
    def lookup_lotti(self, articolo_id: str, search: str | None) -> list[dict[str, Any]]:
        conditions = ["l.articolo_id = %s::uuid", "l.attivo IS TRUE"]
        params: list[Any] = [str(articolo_id)]
        # La guardia legge il PATTERN, non il termine grezzo: «  » e' un
        # termine assente, e con `if search:` diventava `ILIKE NULL` (zero righe).
        pattern = pattern_contiene(search)
        if pattern is not None:
            conditions.append("l.codice ILIKE %s")
            params.append(pattern)
        sql = f"""
            SELECT l.id, l.codice, l.data_arrivo, l.data_scadenza
              FROM magazzino.lotti l
             WHERE {' AND '.join(conditions)}
             ORDER BY l.data_arrivo DESC, l.codice, l.id
        """  # noqa: S608 — WHERE da condizioni letterali, valori come parametri
        with connection.cursor() as cursor:
            cursor.execute(sql, params)
            return rows_to_list(cursor)

    # Scopo: I seriali ATTIVI di un articolo, dell'EMITTENTE del magazzino
    #        indicato (la primitiva rifiuta l'asset di un altro emittente:
    #        proporlo sarebbe una riga `NON_POSTABILE` annunciata). La RLS su
    #        `assets` fa il resto.
    def lookup_assets(self, articolo_id: str, magazzino_id: int) -> list[dict[str, Any]]:
        sql = """
            SELECT s.id, s.seriale, s.stato_id, s.attivo
              FROM magazzino.assets s
              JOIN magazzino.magazzini m ON m.id = %s
             WHERE s.articolo_id = %s::uuid
               AND s.attivo IS TRUE
               AND s.emittente_fiscale_id = m.emittente_fiscale_id
             ORDER BY s.seriale, s.id
        """
        with connection.cursor() as cursor:
            cursor.execute(sql, [int(magazzino_id), str(articolo_id)])
            return rows_to_list(cursor)

    # ══════════════════════════════════════════════════════════════
    #  Consultazione — disponibilita' e registro
    # ══════════════════════════════════════════════════════════════

    # Scopo: La disponibilita' per articolo e magazzino (`vw_disponibilita`,
    #        `security_invoker`: si legge CON la connessione dell'utente).
    # ⚠️ Due chiavi di spareggio (articolo, magazzino): la vista non ha un
    #    `id`, e la coppia e' la sua chiave — un caso che `sql_order_clause`
    #    non descrive di proposito.
    def list_disponibilita(
        self,
        *,
        auth_user_id: int | None,
        articolo_id: str | None = None,
        magazzino_id: int | None = None,
        solo_negativa: bool = False,
        solo_con_giacenza: bool = False,
        search: str | None = None,
        order_by: str | None = None,
        order_dir: str | None = None,
        limit: int,
        offset: int,
    ) -> tuple[list[DisponibilitaRow], int]:
        guard_canale_sistema(f"{_FN}.list_disponibilita")
        conditions: list[str] = []
        params: list[Any] = []
        add_emittente_scope_condition(
            conditions, params, auth_user_id=auth_user_id, column="m.emittente_fiscale_id",
        )
        if articolo_id is not None:
            conditions.append("d.articolo_id = %s::uuid")
            params.append(str(articolo_id))
        if magazzino_id is not None:
            conditions.append("d.magazzino_id = %s")
            params.append(int(magazzino_id))
        if solo_negativa:
            conditions.append("d.disponibile < 0")
        if solo_con_giacenza:
            conditions.append("d.giacenza <> 0")
        add_ricerca_full_condition(conditions, params, search, _RICERCA_DISPONIBILITA)
        where = ("WHERE " + " AND ".join(conditions)) if conditions else ""

        colonna = colonna_ordinamento(order_by, DISPONIBILITA_SORT_COLUMNS) or "articolo_codice"
        direzione = sql_order_direction_lista(order_by, order_dir, colonne=DISPONIBILITA_SORT_COLUMNS)
        spareggio = sql_tiebreak_direction(direzione)
        rows, total = lista_paginata(
            select_sql=f"{_DISPONIBILITA_SELECT} {where}",
            params=params,
            order_clause=f"{colonna} {direzione}, articolo_id {spareggio}, magazzino_id {spareggio}",
            limit=limit,
            offset=offset,
        )
        return rows, total  # type: ignore[return-value]

    # Scopo: La disponibilita' per articolo, somma sui magazzini VISIBILI
    #        (`vw_disponibilita_articolo` aggrega `vw_disponibilita`, quindi
    #        la RLS entra nel conto).
    # ⚠️ Lo scope applicativo qui NON si somma: la vista aggregata non porta
    #    il magazzino, e un filtro a valle sommerebbe comunque tutti i
    #    magazzini visibili — il perimetro e' la RLS (invoker) per costruzione.
    def list_disponibilita_articoli(
        self,
        *,
        articolo_id: str | None = None,
        solo_negativa: bool = False,
        solo_con_giacenza: bool = False,
        search: str | None = None,
        order_by: str | None = None,
        order_dir: str | None = None,
        limit: int,
        offset: int,
    ) -> tuple[list[DisponibilitaArticoloRow], int]:
        guard_canale_sistema(f"{_FN}.list_disponibilita_articoli")
        conditions: list[str] = []
        params: list[Any] = []
        if articolo_id is not None:
            conditions.append("d.articolo_id = %s::uuid")
            params.append(str(articolo_id))
        if solo_negativa:
            conditions.append("d.disponibile < 0")
        if solo_con_giacenza:
            conditions.append("d.giacenza <> 0")
        add_ricerca_full_condition(conditions, params, search, _RICERCA_DISPONIBILITA_ARTICOLI)
        where = ("WHERE " + " AND ".join(conditions)) if conditions else ""
        ordinamento = sql_order_clause(
            order_by, order_dir,
            colonne=DISPONIBILITA_ARTICOLI_SORT_COLUMNS,
            default="articolo_codice",
            tiebreak="articolo_id",
        )
        rows, total = lista_paginata(
            select_sql=f"{_DISPONIBILITA_ARTICOLI_SELECT} {where}",
            params=params,
            order_clause=ordinamento,
            limit=limit,
            offset=offset,
        )
        return rows, total  # type: ignore[return-value]

    # Scopo: I blocchi (attesi APERTA in uscita) su (articolo, magazzino):
    #        il drill-down di `n_blocchi`. Elenco intero: e' il dettaglio di una
    #        cella, e il conteggio lo dice gia' la lista.
    def list_blocchi(self, *, articolo_id: str, magazzino_id: int) -> list[BloccoRow]:
        with connection.cursor() as cursor:
            cursor.execute(_BLOCCHI_SELECT, [str(articolo_id), int(magazzino_id)])
            return rows_to_list(cursor)  # type: ignore[return-value]

    # Scopo: Il registro dei movimenti, paginato e decodificato. Sola lettura
    #        per costruzione: si scrive solo dalla porta (`fn_scrivi_movimento`).
    # ⭐ `documento_sorgente` = (famiglia, id): i movimenti di QUEL documento —
    #    il tipo del documento (letto da `config.sorgenti` per `codice_interno`,
    #    mai l'id) e la sua chiave in `sorgente_id`.
    #    ⛔ Fino al giro M.1 di brief-db-sorgente-documento-e-riga (2026-11-08)
    #    il movimento portava il tipo della RIGA e qui c'era un `EXISTS` sulle
    #    righe del documento: dall'apply quel filtro tornava vuoto, senza errore.
    def list_movimenti(
        self,
        *,
        auth_user_id: int | None,
        magazzino_id: int | None = None,
        articolo_id: str | None = None,
        causale_id: int | None = None,
        data_da: date | None = None,
        data_a: date | None = None,
        sorgente_codice_interno: str | None = None,
        documento_sorgente: tuple[FamigliaDocumentoInterno, int] | None = None,
        search: str | None = None,
        order_by: str | None = None,
        order_dir: str | None = None,
        limit: int,
        offset: int,
    ) -> tuple[list[MovimentoRow], int]:
        guard_canale_sistema(f"{_FN}.list_movimenti")
        conditions: list[str] = []
        params: list[Any] = []
        add_emittente_scope_condition(
            conditions, params, auth_user_id=auth_user_id, column="m.emittente_fiscale_id",
        )
        if magazzino_id is not None:
            conditions.append("mv.magazzino_id = %s")
            params.append(int(magazzino_id))
        if articolo_id is not None:
            conditions.append("mv.articolo_id = %s::uuid")
            params.append(str(articolo_id))
        if causale_id is not None:
            conditions.append("mv.causale_id = %s")
            params.append(int(causale_id))
        # Giorni dell'AZIENDA, `data_a` incluso (BB, brief un-solo-fuso-aziendale B-4).
        giorno_sql, giorno_params = predicato_giorno_operativo("mv.data_mov", data_da, data_a)
        conditions.append(giorno_sql)
        params.extend(giorno_params)
        if sorgente_codice_interno is not None:
            conditions.append("sg.codice_interno = %s")
            params.append(sorgente_codice_interno)
        if documento_sorgente is not None:
            f, doc_id = documento_sorgente
            conditions.append("sg.codice_interno = %s AND mv.sorgente_id = %s")
            params.extend([f.sorgente_codice_interno, int(doc_id)])
        add_ricerca_full_condition(conditions, params, search, _RICERCA_MOVIMENTI)
        where = ("WHERE " + " AND ".join(conditions)) if conditions else ""

        ordinamento = sql_order_clause(
            order_by, order_dir,
            colonne=MOVIMENTI_SORT_COLUMNS,
            default="data_mov",
            tiebreak="id",
            default_desc=True,
            colonne_desc=MOVIMENTI_SORT_COLONNE_DATA,
        )
        rows, total = lista_paginata(
            select_sql=f"{_MOVIMENTI_SELECT} {where}",
            params=params,
            order_clause=ordinamento,
            limit=limit,
            offset=offset,
        )
        return rows, total  # type: ignore[return-value]
