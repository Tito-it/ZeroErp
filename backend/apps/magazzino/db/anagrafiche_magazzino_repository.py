# ------------------------------------------------------------
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Repository delle tre ANAGRAFICHE dello schema `magazzino` — magazzini
#        (l'ancora del perimetro RLS), ubicazioni (figlie del magazzino, con
#        gerarchia `parent_id`) e lotti (dell'articolo e dell'azienda).
#        Liste offset-based con display field via JOIN, dettaglio, INSERT e
#        UPDATE per delta.
# Note: ⭐ Q-7 (Tid, 2026-09-21): le TRE anagrafiche stanno in UN file, con la
#       forma `anagrafiche_magazzino_*` — AGENTS.md «non frammentare per
#       entita'», e `magazzino_repository.py` e' di fatto il repository del
#       documento interno (1000 righe) e non va gonfiato.
#       Piano: piano-be-fe-magazzino-anagrafiche-fuori-dal-pannello-config §4-6.
#
#       🔴 Le tre tabelle hanno la row security accesa: il perimetro e'
#       l'emittente del magazzino (per le ubicazioni, via il magazzino) e del
#       lotto, e lo scope applicativo si SOMMA (`add_emittente_scope_condition`
#       su `m.emittente_fiscale_id` / `l.emittente_fiscale_id`). Un dettaglio
#       fuori perimetro e' `None`, indistinguibile dall'inesistente (404
#       no-leak, di proposito). ⭐ Il lotto e' dell'AZIENDA dal 2026-11-22
#       (brief-db-magazzino-lotto-dell-azienda, D-L1): il codice e' unico per
#       (emittente, articolo, codice), e la lista resta per articolo.
#
#       ⚠️ I display field arrivano con LEFT JOIN, non JOIN: la RLS su
#       `emittenti_fiscali`/`soggetti` puo' nascondere la decodifica, e una
#       riga che sparisce dalla lista perche' non si legge il NOME del suo
#       emittente sarebbe un difetto silenzioso — meglio la colonna vuota.
#
#       ⚠️ Le SQL interpolano SOLO identificatori dalle whitelist di questo
#       modulo (ordinamento, funzioni delle colonne ammesse); i VALORI viaggiano
#       nei `params`.
#
#       ⭐ 2026-11-22 (R-1 di brief-db-magazzino-tutte-le-scritture-dal-verbo):
#       le scritture passano dai VERBI del DB — `magazzino.fn_aggiungi_*`
#       (nascita) e `fn_modifica_*` (delta in jsonb), DEFINER, col livello
#       `TUTTO` sull'oggetto controllato nella prima riga. L'app non ha piu'
#       `INSERT`/`UPDATE` su magazzini, ubicazioni e lotti (`42501`). Le colonne
#       ammesse le dice il DB (`magazzino.fn_<tabella>_colonne_ammesse(gesto)`,
#       D-M4): le costanti `*_COLONNE` e `_CAMPI_MADRE_MAGAZZINO` sono ritirate.
#       Una chiave fuori lista la rifiuta il verbo (`E_CAMPO_NON_AMMESSO`), il
#       riga fuori perimetro risponde «non trovata» (no-leak).
# ------------------------------------------------------------

from __future__ import annotations

from datetime import date
from typing import Any, cast

from django.db import connection

from apps.core.db._helpers import (
    RicercaFull,
    add_ricerca_full_condition,
    rows_to_list,
    sql_order_clause,
)
from apps.core.db.emittente_scope_helpers import add_emittente_scope_condition
from apps.core.db.sql_write_helpers import campi_jsonb as _jsonb, esegui_verbo as _verbo
from apps.magazzino.db._helpers import (
    guard_canale_sistema,
    lista_paginata,
)
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
#  Le colonne AMMESSE stanno a DB (D-M4): una funzione per anagrafica, col
#  gesto (`'crea'` / `'modifica'`). Il nome della funzione viene da qui, mai
#  dalla richiesta. Fuori lista, per costruzione: l'emittente (lo mette il DB
#  dalla GUC) e le identita' della nascita (`magazzino_id` dell'ubicazione,
#  `articolo_id` del lotto: argomenti del verbo, non campi).
# ══════════════════════════════════════════════════════════════════

_FN_COLONNE_AMMESSE: dict[str, str] = {
    "magazzini": "magazzino.fn_magazzini_colonne_ammesse",
    "ubicazioni": "magazzino.fn_ubicazioni_colonne_ammesse",
    "lotti": "magazzino.fn_lotti_colonne_ammesse",
}
GESTI: frozenset[str] = frozenset({"crea", "modifica"})


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
    SELECT l.id, l.articolo_id, l.emittente_fiscale_id,
           l.codice, l.data_arrivo, l.data_scadenza,
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

    # Scopo: Le colonne che il DB ammette per `tabella` nel `gesto`
    #        (`magazzino.fn_<tabella>_colonne_ammesse`). Tabella o gesto fuori
    #        elenco: `RuntimeError`, e' un errore del chiamante.
    def colonne_ammesse(self, tabella: str, gesto: str) -> frozenset[str]:
        funzione = _FN_COLONNE_AMMESSE.get(tabella)
        if funzione is None or gesto not in GESTI:
            raise RuntimeError(f"colonne_ammesse: tabella {tabella!r} o gesto {gesto!r} fuori elenco")
        return frozenset(_verbo(f"SELECT {funzione}(%s)", [gesto]) or ())

    # Scopo: Crea il magazzino col verbo `magazzino.fn_aggiungi_magazzino`:
    #        gli obbligatori come argomenti, i facoltativi in `campi` (gli
    #        assenti al DEFAULT). `emittente_fiscale_id` NON viaggia: lo mette
    #        il DB dalla GUC (`trgfn_default_emittente_fiscale('SOLLEVA')`).
    def create_magazzino(
        self, *, codice: str, descrizione: str, indirizzo_dettaglio_id: int, campi: dict[str, Any],
    ) -> int:
        return int(_verbo(
            "SELECT magazzino.fn_aggiungi_magazzino(%s, %s, %s::bigint, %s::jsonb)",
            [codice, descrizione, int(indirizzo_dettaglio_id), _jsonb(campi)],
        ))

    # Scopo: Aggiorna il magazzino per delta col verbo
    #        `magazzino.fn_modifica_magazzino` (una chiave a `None` svuota, una
    #        assente resta). Il lock su `codice` e i guard (`usa_ubicazioni` a
    #        registro vuoto, disattivazione con figli) sono del DB. Ritorna la
    #        riga che il verbo restituisce (id e colonne modificabili).
    def update_magazzino(self, magazzino_id: int, campi: dict[str, Any]) -> dict[str, Any]:
        return cast(dict[str, Any], _verbo(
            "SELECT magazzino.fn_modifica_magazzino(%s, %s::jsonb)", [int(magazzino_id), _jsonb(campi)],
        ))

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

    # Scopo: Crea l'ubicazione nel magazzino del path col verbo
    #        `magazzino.fn_aggiungi_ubicazione`. Il magazzino fuori perimetro o
    #        inesistente: `E_MAG_MAGAZZINO_NON_TROVATO` (no-leak). Padre dello
    #        stesso magazzino e niente cicli: `trgfn_ubicazioni_guard_parent`.
    def create_ubicazione(
        self, magazzino_id: int, *, codice: str, tipo_id: int, campi: dict[str, Any],
    ) -> int:
        return int(_verbo(
            "SELECT magazzino.fn_aggiungi_ubicazione(%s::bigint, %s, %s::bigint, %s::jsonb)",
            [int(magazzino_id), codice, int(tipo_id), _jsonb(campi)],
        ))

    # Scopo: Aggiorna l'ubicazione per delta col verbo
    #        `magazzino.fn_modifica_ubicazione`, legata al SUO magazzino: la
    #        coppia e' la risorsa, e un id di un altro magazzino e'
    #        `E_MAG_UBICAZIONE_NON_TROVATA`.
    def update_ubicazione(self, magazzino_id: int, ubicazione_id: int, campi: dict[str, Any]) -> dict[str, Any]:
        return cast(dict[str, Any], _verbo(
            "SELECT magazzino.fn_modifica_ubicazione(%s, %s, %s::jsonb)",
            [int(magazzino_id), int(ubicazione_id), _jsonb(campi)],
        ))

    # ══════════════════════════════════════════════════════════════
    #  Lotti (figli dell'articolo)
    # ══════════════════════════════════════════════════════════════

    # Scopo: I lotti di UN articolo nel perimetro (RLS + scope sull'emittente
    #        del lotto), paginati. `articolo_id` e' obbligatorio (lo pretende
    #        il service).
    def list_lotti(
        self,
        *,
        auth_user_id: int | None,
        articolo_id: str,
        search: str | None = None,
        attivo: bool | None = None,
        order_by: str | None = None,
        order_dir: str | None = None,
        limit: int,
        offset: int,
    ) -> tuple[list[LottoRow], int]:
        guard_canale_sistema(f"{_FN}.list_lotti")
        conditions: list[str] = ["l.articolo_id = %s::uuid"]
        params: list[Any] = [str(articolo_id)]
        add_emittente_scope_condition(
            conditions, params, auth_user_id=auth_user_id, column="l.emittente_fiscale_id",
        )
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

    # Scopo: Il lotto, se esiste ed e' nel perimetro; `None` altrimenti.
    def get_lotto(self, lotto_id: int) -> LottoRow | None:
        with connection.cursor() as cursor:
            cursor.execute(f"{_LOTTI_SELECT} WHERE l.id = %s", [int(lotto_id)])
            rows = rows_to_list(cursor)
        return rows[0] if rows else None  # type: ignore[return-value]

    # Scopo: Crea il lotto dell'articolo col verbo `magazzino.fn_aggiungi_lotto`.
    #        L'azienda del lotto la mette il DB dalla GUC; articolo attivo,
    #        unicita' (emittente, articolo, codice), scadenza >= arrivo: li
    #        decide il DB.
    def create_lotto(
        self, articolo_id: str, *, codice: str, data_arrivo: date, campi: dict[str, Any],
    ) -> int:
        return int(_verbo(
            "SELECT magazzino.fn_aggiungi_lotto(%s::uuid, %s, %s::date, %s::jsonb)",
            [str(articolo_id), codice, data_arrivo, _jsonb(campi)],
        ))

    # Scopo: Aggiorna il lotto per delta col verbo `magazzino.fn_modifica_lotto`:
    #        il lotto fuori dal perimetro dell'azienda e' `E_MAG_LOTTO_NON_TROVATO`.
    #        ⛔ `articolo_id` non e' fra le colonne: un lotto nasce del suo articolo.
    def update_lotto(self, lotto_id: int, campi: dict[str, Any]) -> dict[str, Any]:
        return cast(dict[str, Any], _verbo(
            "SELECT magazzino.fn_modifica_lotto(%s, %s::jsonb)", [int(lotto_id), _jsonb(campi)],
        ))
