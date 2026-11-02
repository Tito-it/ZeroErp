# ------------------------------------------------------------
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Repository delle tre ANAGRAFICHE dello schema `magazzino` — magazzini
#        (l'ancora del perimetro RLS), ubicazioni (figlie del magazzino, con
#        gerarchia `parent_id`) e lotti (figli dell'articolo, senza RLS).
#        Liste offset-based con display field via JOIN, dettaglio, INSERT e
#        UPDATE per delta.
# Note: ⭐ Q-7 (Tid, 2026-09-21): le TRE anagrafiche stanno in UN file, con la
#       forma `anagrafiche_magazzino_*` — AGENTS.md «non frammentare per
#       entita'», e `magazzino_repository.py` e' di fatto il repository del
#       documento interno (1000 righe) e non va gonfiato.
#       Piano: piano-be-fe-magazzino-anagrafiche-fuori-dal-pannello-config §4-6.
#
#       🔴 `magazzini` e `ubicazioni` hanno la row security accesa: il
#       perimetro e' l'emittente del magazzino, e lo scope applicativo si SOMMA
#       (`add_emittente_scope_condition` su `m.emittente_fiscale_id`). Un
#       dettaglio fuori perimetro e' `None`, indistinguibile dall'inesistente
#       (404 no-leak, di proposito). ⛔ `lotti` NON ha RLS: un lotto e'
#       dell'articolo (brief Lotto 1 §4.3), e la lista lo pretende come filtro.
#
#       ⚠️ I display field arrivano con LEFT JOIN, non JOIN: la RLS su
#       `emittenti_fiscali`/`soggetti` puo' nascondere la decodifica, e una
#       riga che sparisce dalla lista perche' non si legge il NOME del suo
#       emittente sarebbe un difetto silenzioso — meglio la colonna vuota.
#
#       ⚠️ Le SQL interpolano SOLO identificatori dalle whitelist di questo
#       modulo (colonne scrivibili, ordinamento); i VALORI viaggiano nei `params`.
#
#       ⭐ 2026-09-26: le scritture passano dai BB core (`execute_dynamic_insert`
#       / `execute_dynamic_update` / `sql_set_clause`); i privati `_inserisci`,
#       `_aggiorna`, `_segnaposto`, `_valore` sono ritirati. ⛔ La whitelist e'
#       RIGIDA: una chiave fuori dalle `*_COLONNE` e' `RuntimeError` (500), non
#       piu' uno scarto silenzioso — il contratto dell'operatore lo chiude il
#       service (`validate_allowed_keys`, 400) prima di arrivare qui.
# ------------------------------------------------------------

from __future__ import annotations

import json
from typing import Any, cast

from django.db import connection

from apps.core.db._helpers import (
    RicercaFull,
    add_ricerca_full_condition,
    rows_to_list,
    sql_order_clause,
)
from apps.core.db.emittente_scope_helpers import add_emittente_scope_condition
from apps.core.db.sql_write_helpers import (
    execute_dynamic_insert,
    execute_dynamic_update,
    sql_set_clause,
)
from apps.magazzino.db._helpers import guard_canale_sistema, lista_paginata, meta_mai_null
from apps.magazzino.types import LottoRow, MagazzinoRow, UbicazioneRow

_FN = "magazzino.anagrafiche_magazzino_repository"


# ══════════════════════════════════════════════════════════════════
#  Whitelist di ordinamento — chiavate sul `campo_sorgente` FISICO
# ══════════════════════════════════════════════════════════════════

MAGAZZINI_SORT_COLUMNS: dict[str, str] = {
    "codice": "codice",
    "descrizione": "descrizione",
    "emittente_codice": "emittente_codice",
    # Nucleo sempre ordinabile delle liste con l'emittente in riga (regola del
    # generatore di seed): la ragione sociale ordina, anche se in lista parte
    # nascosta.
    "emittente_ragione_sociale": "emittente_ragione_sociale",
    "indirizzo_normalizzato": "indirizzo_normalizzato",
    "usa_ubicazioni": "usa_ubicazioni",
    "predefinito": "predefinito",
    "attivo": "attivo",
    "ubicazioni_count": "ubicazioni_count",
    "data_insert": "data_insert",
    "id": "id",
}
MAGAZZINI_SORT_COLONNE_DATA: frozenset[str] = frozenset({"data_insert"})

UBICAZIONI_SORT_COLUMNS: dict[str, str] = {
    "codice": "codice",
    "descrizione": "descrizione",
    "tipo_codice": "tipo_codice",
    "parent_codice": "parent_codice",
    "area": "area",
    "corsia": "corsia",
    "scaffale": "scaffale",
    "piano": "piano",
    "posizione": "posizione",
    "attivo": "attivo",
    "data_insert": "data_insert",
    "id": "id",
}
UBICAZIONI_SORT_COLONNE_DATA: frozenset[str] = frozenset({"data_insert"})

LOTTI_SORT_COLUMNS: dict[str, str] = {
    "codice": "codice",
    "data_arrivo": "data_arrivo",
    "data_scadenza": "data_scadenza",
    "attivo": "attivo",
    "data_insert": "data_insert",
    "id": "id",
}
# Le date: verso naturale DESC (regola di Tid del 2026-09-02).
LOTTI_SORT_COLONNE_DATA: frozenset[str] = frozenset({"data_arrivo", "data_scadenza", "data_insert"})

# Cosa si PUO' cercare in ogni lista; cosa si cerca lo dice il catalogo
# (`add_ricerca_full_condition`, brief-be-ricerca-full-liste-residue §2).
_RICERCA_MAGAZZINI = RicercaFull("magazzino.magazzini", ("codice", "descrizione"))
_RICERCA_UBICAZIONI = RicercaFull("magazzino.ubicazioni", ("codice", "descrizione"))
_RICERCA_LOTTI = RicercaFull("magazzino.lotti", ("codice",))


# ══════════════════════════════════════════════════════════════════
#  Colonne SCRIVIBILI — quelle che una persona compila. Fuori: `id`, `uid`,
#  audit, `tx_id`, `storicizza`, e le identita' che il DB decide da solo
#  (`emittente_fiscale_id` lo mette `trgfn_default_emittente_fiscale`;
#  `magazzino_id` dell'ubicazione e `articolo_id` del lotto si scelgono alla
#  nascita e sono nel path / nel payload di CREATE, non fra i campi del PATCH).
# ══════════════════════════════════════════════════════════════════

MAGAZZINI_COLONNE: frozenset[str] = frozenset(
    {"codice", "descrizione", "indirizzo_dettaglio_id", "usa_ubicazioni", "predefinito", "attivo", "meta"}
)
UBICAZIONI_COLONNE: frozenset[str] = frozenset(
    {"codice", "descrizione", "tipo_id", "parent_id", "area", "corsia", "scaffale", "piano", "posizione", "attivo", "meta"}
)
LOTTI_COLONNE: frozenset[str] = frozenset({"codice", "data_arrivo", "data_scadenza", "attivo", "meta"})

# Le colonne jsonb dichiarate ai BB di scrittura (in lettura le decodifica il
# lettore comune, `rows_to_list`) — un dict va da solo, una STRINGA e' testo JSON (regola jsonb di
# Tid del 2026-09-26). Il `None` su `meta` (NOT NULL) lo sistema `meta_mai_null`.
_JSONB_COLS = ("meta",)
# I campi opzionali che la madre `fn_crea_magazzino` riceve in `p_campi`:
# codice, descrizione e indirizzo sono suoi argomenti, `attivo` non si sceglie
# alla nascita.
_CAMPI_MADRE_MAGAZZINO = ("usa_ubicazioni", "predefinito", "meta")
# L'uuid dell'articolo del lotto viaggia come stringa (`str(articolo_id)`):
# cast esplicito nel segnaposto dell'INSERT.
_CASTS_LOTTO: dict[str, str] = {"articolo_id": "uuid"}


# ══════════════════════════════════════════════════════════════════
#  Le proiezioni
# ══════════════════════════════════════════════════════════════════

_MAGAZZINI_SELECT = """
    SELECT m.id, m.uid, m.codice, m.descrizione,
           m.emittente_fiscale_id,
           ef.codice                     AS emittente_codice,
           s_ef.ragione_sociale_completa AS emittente_ragione_sociale,
           -- Il SOGGETTO dell'emittente: il drawer sceglie l'indirizzo del
           -- magazzino fra gli indirizzi dell'azienda (Q-2 del piano).
           sr_ef.soggetto_id             AS emittente_soggetto_id,
           m.indirizzo_dettaglio_id,
           idet.indirizzo_normalizzato,
           m.usa_ubicazioni, m.predefinito, m.attivo,
           (SELECT COUNT(*) FROM magazzino.ubicazioni u
             WHERE u.magazzino_id = m.id AND u.attivo IS TRUE) AS ubicazioni_count,
           m.meta, m.data_insert, m.user_insert, m.data_update, m.user_update
      FROM magazzino.magazzini m
      LEFT JOIN anagrafiche.emittenti_fiscali ef ON ef.id = m.emittente_fiscale_id
      LEFT JOIN anagrafiche.soggetti_ruoli sr_ef ON sr_ef.id = ef.soggetto_ruolo_id
      LEFT JOIN anagrafiche.soggetti s_ef ON s_ef.id = sr_ef.soggetto_id
      LEFT JOIN anagrafiche.indirizzi_dettaglio idet ON idet.id = m.indirizzo_dettaglio_id
"""

_UBICAZIONI_SELECT = """
    SELECT u.id, u.magazzino_id, u.codice, u.descrizione,
           u.tipo_id,
           tu.codice      AS tipo_codice,
           tu.descrizione AS tipo_descrizione,
           u.parent_id,
           p.codice       AS parent_codice,
           u.area, u.corsia, u.scaffale, u.piano, u.posizione,
           u.attivo, u.meta,
           u.data_insert, u.user_insert, u.data_update, u.user_update
      FROM magazzino.ubicazioni u
      LEFT JOIN config.tipi_ubicazione tu ON tu.id = u.tipo_id
      LEFT JOIN magazzino.ubicazioni p ON p.id = u.parent_id
"""

_LOTTI_SELECT = """
    SELECT l.id, l.articolo_id, l.codice, l.data_arrivo, l.data_scadenza,
           l.attivo, l.meta,
           l.data_insert, l.user_insert, l.data_update, l.user_update
      FROM magazzino.lotti l
"""


# Scopo: Il filtro `attivo`: `None` = tutti.
def _filtro_attivo(conditions: list[str], params: list[Any], alias: str, attivo: bool | None) -> None:
    if attivo is not None:
        conditions.append(f"{alias}.attivo IS %s")
        params.append(bool(attivo))


# Scopo: La `WHERE` dalle condizioni raccolte.
def _where(conditions: list[str]) -> str:
    return ("WHERE " + " AND ".join(conditions)) if conditions else ""


class AnagraficheMagazzinoRepository:
    """Accesso dati delle anagrafiche di `magazzino`: magazzini, ubicazioni, lotti."""

    # ══════════════════════════════════════════════════════════════
    #  Magazzini
    # ══════════════════════════════════════════════════════════════

    # Scopo: L'elenco paginato dei magazzini del perimetro (RLS + scope).
    def list_magazzini(
        self,
        *,
        auth_user_id: int | None,
        search: str | None = None,
        attivo: bool | None = None,
        order_by: str | None = None,
        order_dir: str | None = None,
        limit: int,
        offset: int,
    ) -> tuple[list[MagazzinoRow], int]:
        guard_canale_sistema(f"{_FN}.list_magazzini")
        conditions: list[str] = []
        params: list[Any] = []
        add_emittente_scope_condition(
            conditions, params, auth_user_id=auth_user_id, column="m.emittente_fiscale_id",
        )
        add_ricerca_full_condition(conditions, params, search, _RICERCA_MAGAZZINI, alias="m")
        _filtro_attivo(conditions, params, "m", attivo)
        ordinamento = sql_order_clause(
            order_by, order_dir,
            colonne=MAGAZZINI_SORT_COLUMNS, default="codice", tiebreak="id",
            colonne_desc=MAGAZZINI_SORT_COLONNE_DATA,
        )
        rows, total = lista_paginata(
            select_sql=f"{_MAGAZZINI_SELECT} {_where(conditions)}",
            params=params, order_clause=ordinamento, limit=limit, offset=offset,
        )
        return [cast(MagazzinoRow, r) for r in rows], total

    # Scopo: Il magazzino, se esiste ed e' nel perimetro; `None` altrimenti.
    #        ⚠️ Anche SPENTO: il dettaglio di un'anagrafica disattivata si legge
    #        (e si riattiva). Chi vuole «attivo» e' `MagazzinoRepository.get_magazzino`.
    def get_magazzino(self, magazzino_id: int) -> MagazzinoRow | None:
        with connection.cursor() as cursor:
            cursor.execute(f"{_MAGAZZINI_SELECT} WHERE m.id = %s", [int(magazzino_id)])
            rows = rows_to_list(cursor)
        return rows[0] if rows else None  # type: ignore[return-value]

    # Scopo: Crea il magazzino con la madre del DB `magazzino.fn_crea_magazzino`:
    #        `codice`, `descrizione`, `indirizzo_dettaglio_id` e i campi
    #        opzionali (`usa_ubicazioni`, `predefinito`, `meta`; gli assenti al
    #        DEFAULT). `emittente_fiscale_id` NON viaggia: lo mette il DB dalla
    #        GUC (`trgfn_default_emittente_fiscale('SOLLEVA')`).
    # ⭐ Dal 2026-10-18 (2b-2, lotto 7): era una INSERT del BB di scrittura.
    def create_magazzino(self, valori: dict[str, Any]) -> int:
        # ⛔ Una chiave che la creazione non conosce e' un allarme tecnico (500),
        #    mai uno scarto: il service sceglie le chiavi per nome.
        estranee = set(valori) - {"codice", "descrizione", "indirizzo_dettaglio_id", *_CAMPI_MADRE_MAGAZZINO}
        if estranee:
            raise RuntimeError(f"create_magazzino: chiavi non ammesse {sorted(estranee)}")
        campi = {k: v for k, v in meta_mai_null(valori).items() if k in _CAMPI_MADRE_MAGAZZINO}
        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT magazzino.fn_crea_magazzino(%s, %s, %s::bigint, %s::jsonb)",
                [valori["codice"], valori["descrizione"], valori["indirizzo_dettaglio_id"],
                 json.dumps(campi, default=str)],
            )
            row = cursor.fetchone()
        assert row is not None
        return int(row[0])

    # Scopo: Aggiorna il magazzino per delta. Il lock su `codice` e i guard
    #        (`usa_ubicazioni` a registro vuoto, disattivazione con figli) sono
    #        del DB: qui si esegue e si riporta. `False` = la riga non c'e' (o
    #        non e' visibile), o `campi` vuoto.
    def update_magazzino(self, magazzino_id: int, campi: dict[str, Any]) -> bool:
        return execute_dynamic_update(
            "magazzino.magazzini", int(magazzino_id), meta_mai_null(campi),
            allowed=MAGAZZINI_COLONNE, jsonb=_JSONB_COLS,
        )

    # ══════════════════════════════════════════════════════════════
    #  Ubicazioni (figlie del magazzino)
    # ══════════════════════════════════════════════════════════════

    # Scopo: Le ubicazioni di UN magazzino, paginate. Il perimetro e' la
    #        testata: il service ha gia' letto il magazzino (404 prima).
    def list_ubicazioni(
        self,
        *,
        magazzino_id: int,
        search: str | None = None,
        attivo: bool | None = None,
        parent_id: int | None = None,
        order_by: str | None = None,
        order_dir: str | None = None,
        limit: int,
        offset: int,
    ) -> tuple[list[UbicazioneRow], int]:
        guard_canale_sistema(f"{_FN}.list_ubicazioni")
        conditions: list[str] = ["u.magazzino_id = %s"]
        params: list[Any] = [int(magazzino_id)]
        add_ricerca_full_condition(conditions, params, search, _RICERCA_UBICAZIONI, alias="u")
        _filtro_attivo(conditions, params, "u", attivo)
        if parent_id is not None:
            conditions.append("u.parent_id = %s")
            params.append(int(parent_id))
        ordinamento = sql_order_clause(
            order_by, order_dir,
            colonne=UBICAZIONI_SORT_COLUMNS, default="codice", tiebreak="id",
            colonne_desc=UBICAZIONI_SORT_COLONNE_DATA,
        )
        rows, total = lista_paginata(
            select_sql=f"{_UBICAZIONI_SELECT} {_where(conditions)}",
            params=params, order_clause=ordinamento, limit=limit, offset=offset,
        )
        return [cast(UbicazioneRow, r) for r in rows], total

    # Scopo: L'ubicazione DEL magazzino, o `None` (inesistente, di un altro
    #        magazzino, o fuori perimetro: la coppia e' la risorsa dell'URL).
    def get_ubicazione(self, magazzino_id: int, ubicazione_id: int) -> UbicazioneRow | None:
        with connection.cursor() as cursor:
            cursor.execute(
                f"{_UBICAZIONI_SELECT} WHERE u.id = %s AND u.magazzino_id = %s",
                [int(ubicazione_id), int(magazzino_id)],
            )
            rows = rows_to_list(cursor)
        return rows[0] if rows else None  # type: ignore[return-value]

    # Scopo: Crea l'ubicazione nel magazzino del path. Padre dello stesso
    #        magazzino e niente cicli: lo decide `trgfn_ubicazioni_guard_parent`.
    def create_ubicazione(self, magazzino_id: int, valori: dict[str, Any]) -> int:
        # Il padre viene dal path e VINCE su un eventuale `magazzino_id` nel
        # payload (il service non lo ammette fra le chiavi comunque).
        riga = execute_dynamic_insert(
            "magazzino.ubicazioni",
            meta_mai_null({**valori, "magazzino_id": int(magazzino_id)}),
            allowed=UBICAZIONI_COLONNE | {"magazzino_id"},
            jsonb=_JSONB_COLS,
        )
        return int(riga["id"])

    # Scopo: Aggiorna l'ubicazione per delta, legata al SUO magazzino nella
    #        `WHERE`: un id di un altro magazzino e' zero righe, cioe' 404 —
    #        per questo il SET dal BB `sql_set_clause` e il WHERE scritto qui.
    def update_ubicazione(self, magazzino_id: int, ubicazione_id: int, campi: dict[str, Any]) -> bool:
        if not campi:
            return False
        set_sql, params = sql_set_clause(meta_mai_null(campi), allowed=UBICAZIONI_COLONNE, jsonb=_JSONB_COLS)
        sql = f"UPDATE magazzino.ubicazioni SET {set_sql} WHERE id = %s AND magazzino_id = %s"  # noqa: S608 — SET da sql_set_clause (colonne verificate sulla whitelist UBICAZIONI_COLONNE), valori come parametri
        with connection.cursor() as cursor:
            cursor.execute(sql, [*params, int(ubicazione_id), int(magazzino_id)])
            return cursor.rowcount > 0

    # ══════════════════════════════════════════════════════════════
    #  Lotti (figli dell'articolo)
    # ══════════════════════════════════════════════════════════════

    # Scopo: I lotti di UN articolo, paginati. ⚠️ Niente RLS ne' scope: un
    #        lotto e' dell'articolo, e `articolo_id` e' obbligatorio (lo
    #        pretende il service).
    def list_lotti(
        self,
        *,
        articolo_id: str,
        search: str | None = None,
        attivo: bool | None = None,
        order_by: str | None = None,
        order_dir: str | None = None,
        limit: int,
        offset: int,
    ) -> tuple[list[LottoRow], int]:
        conditions: list[str] = ["l.articolo_id = %s::uuid"]
        params: list[Any] = [str(articolo_id)]
        add_ricerca_full_condition(conditions, params, search, _RICERCA_LOTTI, alias="l")
        _filtro_attivo(conditions, params, "l", attivo)
        ordinamento = sql_order_clause(
            order_by, order_dir,
            colonne=LOTTI_SORT_COLUMNS, default="data_arrivo", tiebreak="id",
            default_desc=True, colonne_desc=LOTTI_SORT_COLONNE_DATA,
        )
        rows, total = lista_paginata(
            select_sql=f"{_LOTTI_SELECT} {_where(conditions)}",
            params=params, order_clause=ordinamento, limit=limit, offset=offset,
        )
        return [cast(LottoRow, r) for r in rows], total

    # Scopo: Il lotto, o `None`.
    def get_lotto(self, lotto_id: int) -> LottoRow | None:
        with connection.cursor() as cursor:
            cursor.execute(f"{_LOTTI_SELECT} WHERE l.id = %s", [int(lotto_id)])
            rows = rows_to_list(cursor)
        return rows[0] if rows else None  # type: ignore[return-value]

    # Scopo: Crea il lotto dell'articolo. Articolo attivo, chiave (articolo,
    #        codice), scadenza >= arrivo: li decide il DB.
    def create_lotto(self, articolo_id: str, valori: dict[str, Any]) -> int:
        riga = execute_dynamic_insert(
            "magazzino.lotti",
            meta_mai_null({**valori, "articolo_id": str(articolo_id)}),
            allowed=LOTTI_COLONNE | {"articolo_id"},
            jsonb=_JSONB_COLS,
            casts=_CASTS_LOTTO,
        )
        return int(riga["id"])

    # Scopo: Aggiorna il lotto per delta. ⛔ `articolo_id` non e' fra le
    #        colonne: un lotto nasce del suo articolo.
    def update_lotto(self, lotto_id: int, campi: dict[str, Any]) -> bool:
        return execute_dynamic_update(
            "magazzino.lotti", int(lotto_id), meta_mai_null(campi), allowed=LOTTI_COLONNE, jsonb=_JSONB_COLS,
        )
