# ------------------------------------------------------------
# SPDX-License-Identifier: GPL-3.0-or-later
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
# ------------------------------------------------------------

from __future__ import annotations

import json
from typing import Any

from django.db import connection

from apps.core.db._helpers import (
    RicercaFull,
    add_ricerca_full_condition,
    fetchone_scalar,
    jsonb_out,
    rows_to_list,
    sql_order_clause,
)
from apps.core.db.emittente_scope_helpers import add_emittente_scope_condition
from apps.magazzino.db._helpers import guard_canale_sistema, lista_paginata
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

_JSONB_COLS = ("meta",)
# I cast espliciti dei segnaposto: il jsonb e l'uuid dell'articolo (il driver
# consegna stringhe, e `articolo_id = 'abc'` senza cast sarebbe un confronto
# text/uuid rifiutato dal planner).
_CAST: dict[str, str] = {"meta": "::jsonb", "articolo_id": "::uuid"}


# Scopo: Il segnaposto della colonna, col suo cast.
def _segnaposto(col: str) -> str:
    return "%s" + _CAST.get(col, "")


# Scopo: Il valore della colonna come lo vuole il driver (jsonb serializzato).
def _valore(col: str, val: Any) -> Any:
    return json.dumps(val or {}) if col in _JSONB_COLS else val


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

    # Scopo: Decodifica i jsonb della riga (il driver li consegna come `str`).
    @staticmethod
    def _shape(row: dict[str, Any]) -> dict[str, Any]:
        for col in _JSONB_COLS:
            if col in row:
                row[col] = jsonb_out(row[col]) or {}
        return row

    # Scopo: `INSERT … RETURNING id` sulle sole colonne ammesse; `meta` come jsonb.
    # ⚠️ `tabella` e le chiavi di `valori` sono identificatori di questo modulo,
    #    filtrati dalla whitelist della tabella: mai input utente.
    @staticmethod
    def _inserisci(tabella: str, valori: dict[str, Any], ammesse: frozenset[str]) -> int:
        colonne = [c for c in valori if c in ammesse]
        segnaposto = [_segnaposto(c) for c in colonne]
        params = [_valore(c, valori[c]) for c in colonne]
        sql = f"INSERT INTO {tabella} ({', '.join(colonne)}) VALUES ({', '.join(segnaposto)}) RETURNING id"  # noqa: S608
        with connection.cursor() as cursor:
            cursor.execute(sql, params)
            return int(fetchone_scalar(cursor))

    # Scopo: `UPDATE` per DELTA sulle sole colonne ammesse. Zero righe = la riga
    #        non c'e' (o non e' visibile). `extra_where` lega la figlia al padre
    #        (l'ubicazione al SUO magazzino).
    @staticmethod
    def _aggiorna(
        tabella: str, riga_id: int, campi: dict[str, Any], ammesse: frozenset[str],
        *, extra_where: str = "", extra_params: list[Any] | None = None,
    ) -> int:
        set_parts: list[str] = []
        params: list[Any] = []
        for col, val in campi.items():
            if col not in ammesse:
                continue
            set_parts.append(f"{col} = {_segnaposto(col)}")
            params.append(_valore(col, val))
        if not set_parts:
            return 0
        params.append(int(riga_id))
        params.extend(extra_params or [])
        sql = f"UPDATE {tabella} SET {', '.join(set_parts)} WHERE id = %s {extra_where}"  # noqa: S608
        with connection.cursor() as cursor:
            cursor.execute(sql, params)
            return cursor.rowcount

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
        return [self._shape(r) for r in rows], total  # type: ignore[return-value]

    # Scopo: Il magazzino, se esiste ed e' nel perimetro; `None` altrimenti.
    #        ⚠️ Anche SPENTO: il dettaglio di un'anagrafica disattivata si legge
    #        (e si riattiva). Chi vuole «attivo» e' `MagazzinoRepository.get_magazzino`.
    def get_magazzino(self, magazzino_id: int) -> MagazzinoRow | None:
        with connection.cursor() as cursor:
            cursor.execute(f"{_MAGAZZINI_SELECT} WHERE m.id = %s", [int(magazzino_id)])
            rows = rows_to_list(cursor)
        return self._shape(rows[0]) if rows else None  # type: ignore[return-value]

    # Scopo: Crea il magazzino. `emittente_fiscale_id` NON viaggia: lo mette il
    #        DB dalla GUC (`trgfn_default_emittente_fiscale('SOLLEVA')`).
    def create_magazzino(self, valori: dict[str, Any]) -> int:
        return self._inserisci("magazzino.magazzini", valori, MAGAZZINI_COLONNE)

    # Scopo: Aggiorna il magazzino per delta. Il lock su `codice` e i guard
    #        (`usa_ubicazioni` a registro vuoto, disattivazione con figli) sono
    #        del DB: qui si esegue e si riporta.
    def update_magazzino(self, magazzino_id: int, campi: dict[str, Any]) -> int:
        return self._aggiorna("magazzino.magazzini", magazzino_id, campi, MAGAZZINI_COLONNE)

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
        return [self._shape(r) for r in rows], total  # type: ignore[return-value]

    # Scopo: L'ubicazione DEL magazzino, o `None` (inesistente, di un altro
    #        magazzino, o fuori perimetro: la coppia e' la risorsa dell'URL).
    def get_ubicazione(self, magazzino_id: int, ubicazione_id: int) -> UbicazioneRow | None:
        with connection.cursor() as cursor:
            cursor.execute(
                f"{_UBICAZIONI_SELECT} WHERE u.id = %s AND u.magazzino_id = %s",
                [int(ubicazione_id), int(magazzino_id)],
            )
            rows = rows_to_list(cursor)
        return self._shape(rows[0]) if rows else None  # type: ignore[return-value]

    # Scopo: Crea l'ubicazione nel magazzino del path. Padre dello stesso
    #        magazzino e niente cicli: lo decide `trgfn_ubicazioni_guard_parent`.
    def create_ubicazione(self, magazzino_id: int, valori: dict[str, Any]) -> int:
        # Il padre viene dal path e VINCE su un eventuale `magazzino_id` nel
        # payload; il filtro sulle colonne ammesse lo fa `_inserisci`.
        return self._inserisci(
            "magazzino.ubicazioni",
            {**valori, "magazzino_id": int(magazzino_id)},
            UBICAZIONI_COLONNE | {"magazzino_id"},
        )

    # Scopo: Aggiorna l'ubicazione per delta, legata al SUO magazzino nella
    #        `WHERE`: un id di un altro magazzino e' zero righe, cioe' 404.
    def update_ubicazione(self, magazzino_id: int, ubicazione_id: int, campi: dict[str, Any]) -> int:
        return self._aggiorna(
            "magazzino.ubicazioni", ubicazione_id, campi, UBICAZIONI_COLONNE,
            extra_where="AND magazzino_id = %s", extra_params=[int(magazzino_id)],
        )

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
        return [self._shape(r) for r in rows], total  # type: ignore[return-value]

    # Scopo: Il lotto, o `None`.
    def get_lotto(self, lotto_id: int) -> LottoRow | None:
        with connection.cursor() as cursor:
            cursor.execute(f"{_LOTTI_SELECT} WHERE l.id = %s", [int(lotto_id)])
            rows = rows_to_list(cursor)
        return self._shape(rows[0]) if rows else None  # type: ignore[return-value]

    # Scopo: Crea il lotto dell'articolo. Articolo attivo, chiave (articolo,
    #        codice), scadenza >= arrivo: li decide il DB.
    def create_lotto(self, articolo_id: str, valori: dict[str, Any]) -> int:
        return self._inserisci(
            "magazzino.lotti",
            {**valori, "articolo_id": str(articolo_id)},
            LOTTI_COLONNE | {"articolo_id"},
        )

    # Scopo: Aggiorna il lotto per delta. ⛔ `articolo_id` non e' fra le
    #        colonne: un lotto nasce del suo articolo.
    def update_lotto(self, lotto_id: int, campi: dict[str, Any]) -> int:
        return self._aggiorna("magazzino.lotti", lotto_id, campi, LOTTI_COLONNE)
