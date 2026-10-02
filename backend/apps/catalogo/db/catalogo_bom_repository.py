# ------------------------------------------------------------
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Accesso DB specializzato per BoM articoli e note catalogo.
# ------------------------------------------------------------

from __future__ import annotations

from datetime import date
from typing import Any
from uuid import UUID

from django.db import connection

from apps.core.api.constants import MAX_LIMIT
from apps.core.db._helpers import (
    RicercaFull,
    add_ricerca_full_condition,
    fetch_paged_with_total,
    limiti_pagina,
    row_to_dict,
    rows_to_list,
    sql_order_clause,
)
from apps.core.db.sql_write_helpers import execute_dynamic_insert, sql_set_clause

# Colonne SCRIVIBILI di una riga BoM: whitelist RIGIDA del BB di scrittura
# (2026-09-26 — prima mappa nome -> tipo per `sql_placeholder`/`to_write_param`,
# ritirati). `meta` (jsonb) arriva dal service come dict o None: il BB lo
# casta da solo, `jsonb=` non serve. `prodotto_id` NON e' qui: lo scrive il
# repository dal path (`create_componente`), mai il payload.
COMPONENTE_WRITE_COLUMNS: frozenset[str] = frozenset({
    "componente_id",
    "coeff_qta",
    # `partecipa_qta` e `determina_qta_padre` ritirati il 2026-10-02: nessuna
    # logica li leggeva (brief-db-bom-flag-quantita-e-kit-in-fattura, D-1).
    "obbligatorio",
    "valido_dal",
    "valido_al",
    "attivo",
    # Il modo di esposizione in fattura (NASCOSTO / DESCRITTIVO / VALORIZZATO,
    # `config.esposizioni_componente`): il valore lo giudica la FK, un codice
    # fuori catalogo torna 23503 (brief-db-esposizione-componenti-kit-in-fattura).
    "esposizione_in_fattura",
    "meta",
})

# ⭐ LE RIGHE DELLA DISTINTA SI LEGGONO DALLA VISTA, e solo da li'
#    (brief-db-liste-righe-documento, D-8.5, 2026-09-28).
#    `catalogo.vw_articoli_componenti_dettaglio` e' la sede unica della
#    proiezione e della capability di chiusura (`puo_chiudersi`,
#    `data_min_chiusura`, `data_default_chiusura`, `motivo_non_chiudibile`).
#    Fino a quel giorno questo modulo la ricopiava in Python
#    (`COMPONENTE_DETAIL_COLUMNS`, con il commento «aggiornare ENTRAMBI»), e le
#    due copie erano gia' divergite: la vista non aveva `esposto_in_fattura` ne'
#    `determina_qta_padre`. Il DB le ha portate al pari, qui la copia si ritira.
#    ⛔ La vista non filtra e non ordina (per progetto, dal suo `COMMENT`):
#    l'ordine lo mette il repository.
_VISTA_COMPONENTI = "catalogo.vw_articoli_componenti_dettaglio"

# La lista configurabile `catalogo.articolo_componenti` (lista 101): la ricerca
# sulle colonne `ricercabile_full = t` del seed, il codice e la descrizione del
# componente. `test_ricerca_full_seed` legge questa costante.
_RICERCA_COMPONENTI = RicercaFull(
    "catalogo.articolo_componenti", ("componente_codice", "componente_descrizione"),
)

# Whitelist di ordinamento della lista 101: le colonne `ordinabile = t` del
# seed, chiavate sul `campo_sorgente` (lo manda `<ListaConfigurabile>`).
# ⭐ `valido_al` si ordina con `COALESCE(…, 'infinity')`: una riga senza fine
#    e' la piu' «lontana», non una data mancante (regola delle date di
#    validita'). Costante di MODULO, come vuole il presidio
#    `test_liste_configurabili_seed` (mockare la classe non la svuota).
COMPONENTI_SORT_COLUMNS: dict[str, str] = {
    "componente_codice": "v.componente_codice",
    "componente_descrizione": "v.componente_descrizione",
    "coeff_qta": "v.coeff_qta",
    "valido_dal": "v.valido_dal",
    "valido_al": "COALESCE(v.valido_al, 'infinity'::date)",
    # La colonna «In fattura» mostra il CODICE del modo, e si ordina su quello
    # (dal 2026-10-01 non e' piu' un booleano).
    "esposizione_in_fattura_codice": "v.esposizione_in_fattura_codice",
}
# Le date partono DESC quando nessuno chiede un verso (regola di Tid del
# 2026-09-02).
COMPONENTI_SORT_COLONNE_DATA: frozenset[str] = frozenset({"valido_dal", "valido_al"})
# L'ordine della distinta quando nessuno chiede altro: la versione piu' recente
# in cima, com'era la lettura completa (e il preset della lista 101).
_ORDINE_DISTINTA = "v.valido_dal DESC"

# Colonne SCRIVIBILI di una nota catalogo: whitelist RIGIDA del BB di
# scrittura (2026-09-26, come COMPONENTE_WRITE_COLUMNS). `target_tipo` e
# `target_id` NON sono qui: li decide il repository (partizione e padre).
# ⚠️ `testo`/`testo_md`: il BB strippa le stringhe, ma il service le ha gia'
#    strippate (`_extract_string` -> `extract_optional_string`): nessun
#    cambio. `meta` e' NOT NULL a DB (DEFAULT '{}'): un `null` esplicito
#    fallisce al vincolo, oggi come prima.
NOTA_WRITE_COLUMNS: frozenset[str] = frozenset({
    "target_riga_id",
    "anchor_tipo",
    "posizione",
    "seq",
    "testo",
    "testo_md",
    "id_stile",
    "id_lingua",
    "visibile",
    "solo_stampa",
    "meta",
})

NOTE_RESOLVE_COLUMNS: tuple[str, ...] = (
    "n.id AS nota_id",
    "n.target_tipo AS nota_target_tipo",
    "n.target_id AS nota_target_id",
    "n.target_riga_id AS nota_target_riga_id",
    "n.anchor_tipo AS nota_anchor_tipo",
    "n.posizione AS nota_posizione",
    "n.seq AS nota_seq",
    "n.testo AS nota_testo",
    "n.testo_md AS nota_testo_md",
    "n.id_stile AS stile_id",
    "n.id_lingua AS lingua_id",
    "n.visibile AS nota_visibile",
    "n.solo_stampa AS nota_solo_stampa",
    "n.meta AS nota_meta",
    "n.data_insert AS nota_data_insert",
    "n.user_insert AS nota_user_insert",
    "n.data_update AS nota_data_update",
    "n.user_update AS nota_user_update",
)

# Frammento SQL riusato dalle 4 query nota arricchita (list/get articolo +
# list/get componente). Alias senza prefisso `nota_*` per allineare lo shape
# al pattern partizionato vendite (`PartitionedNoteRepository._SELECT_COLUMNS`),
# consumato dal building block FE `NoteDrawer` + `useNote` (che leggono
# `n.id`, `n.testo_md`, `n.anchor_tipo`, ...). Le view sottostanti
# (`vw_articoli_note`, `vw_articoli_componenti_note`) conservano i nomi
# originali col prefisso `nota_*` per eventuali altri consumer; l'alias resta
# confinato al repo. Refactor 2026-05-22 (Fase 2.B.2).
_NOTA_PARTITIONED_COLUMNS = """
    vn.nota_id           AS id,
    vn.nota_target_tipo  AS target_tipo,
    vn.nota_target_id    AS target_id,
    vn.nota_target_riga_id AS target_riga_id,
    vn.nota_anchor_tipo  AS anchor_tipo,
    vn.nota_posizione    AS posizione,
    vn.nota_seq          AS seq,
    vn.nota_testo        AS testo,
    vn.nota_testo_md     AS testo_md,
    vn.nota_visibile     AS visibile,
    vn.nota_solo_stampa  AS solo_stampa,
    vn.nota_meta         AS meta,
    vn.nota_data_insert  AS data_insert,
    vn.nota_user_insert  AS user_insert,
    vn.nota_data_update  AS data_update,
    vn.nota_user_update  AS user_update,
    vn.stile_id          AS id_stile,
    vn.stile_codice,
    vn.stile_descrizione,
    vn.lingua_id         AS id_lingua,
    vn.lingua_codice_iso,
    vn.lingua_descrizione,
    vn.lingua_descrizione_locale
""".strip()


class CatalogoBomRepository:
    """Repository specializzato per componenti BoM e note catalogo."""

    # Scopo: Restituisce la proiezione minima per risolvere una nota via tabella padre.
    @staticmethod
    def _nota_resolve_projection() -> str:
        return ",\n                    ".join(NOTE_RESOLVE_COLUMNS)

    # Scopo: TUTTE le righe della distinta di un prodotto, nell'ordine della
    #        distinta: per chi le usa insieme (il dettaglio dell'articolo, i
    #        controlli del service). ⛔ Non e' la lista a video: quella e'
    #        `list_componenti_pagina`.
    def list_componenti(self, articolo_id: UUID | str) -> list[dict[str, Any]]:
        with connection.cursor() as cursor:
            cursor.execute(
                f"""
                SELECT v.*
                  FROM {_VISTA_COMPONENTI} v
                 WHERE v.prodotto_id = %s
                 ORDER BY {_ORDINE_DISTINTA}, v.id
                """,  # noqa: S608 — vista e ordine sono costanti di modulo; valori come parametri
                [articolo_id],
            )
            return rows_to_list(cursor)

    # Scopo: UNA PAGINA della distinta di un prodotto, per la lista
    #        configurabile `catalogo.articolo_componenti`: ricerca dal
    #        catalogo, ordinamento dalla whitelist, filtro di validita'.
    #        Ritorna `(righe, totale)`, totale indipendente dalle righe
    #        consegnate (BB `fetch_paged_with_total`).
    # ⭐ `valido_al` e' il filtro «in vigore al»: tiene le righe che a quella
    #    data NON sono ancora chiuse — senza fine, o con la fine da quel giorno
    #    in poi — comprese quelle che iniziano dopo. E' la stessa regola che il
    #    drawer applicava sulle righe gia' caricate, portata qui con la
    #    paginazione (il filtro locale avrebbe filtrato solo la pagina).
    #    `None` = tutte le versioni.
    # ⚠️ `max_limit`: la lista resta a `MAX_LIMIT`; l'export passa il suo tetto.
    def list_componenti_pagina(
        self,
        articolo_id: UUID | str,
        *,
        valido_al: date | None = None,
        search: str | None = None,
        order_by: str | None = None,
        order_dir: str | None = None,
        limit: int,
        offset: int = 0,
        max_limit: int = MAX_LIMIT,
    ) -> tuple[list[dict[str, Any]], int]:
        ordinamento = sql_order_clause(
            order_by, order_dir,
            colonne=COMPONENTI_SORT_COLUMNS,
            default_clause=_ORDINE_DISTINTA,
            tiebreak="v.id",
            colonne_desc=COMPONENTI_SORT_COLONNE_DATA,
        )
        safe_limit, safe_offset = limiti_pagina(limit, offset, tetto=max_limit)
        conditions = ["v.prodotto_id = %s"]
        params: list[Any] = [articolo_id]
        if valido_al is not None:
            conditions.append("(v.valido_al IS NULL OR v.valido_al >= %s)")
            params.append(valido_al)
        add_ricerca_full_condition(conditions, params, search, _RICERCA_COMPONENTI)
        from_where = f"FROM {_VISTA_COMPONENTI} v WHERE {' AND '.join(conditions)}"
        return fetch_paged_with_total(
            f"""
            SELECT v.*, COUNT(*) OVER () AS total_count
            {from_where}
            ORDER BY {ordinamento}
            LIMIT %s OFFSET %s
            """,  # ORDER BY da sql_order_clause su whitelist, WHERE da condizioni letterali e dal BB della ricerca, valori come parametri
            params + [safe_limit, safe_offset],
            fallback_count_sql=f"SELECT COUNT(*) {from_where}",  # stesso FROM/WHERE della pagina
            fallback_params=params,
            offset=safe_offset,
        )

    # Scopo: Restituisce il singolo componente BoM con ownership sul prodotto.
    def get_componente(
        self,
        articolo_id: UUID | str,
        componente_row_id: UUID | str,
    ) -> dict[str, Any] | None:
        with connection.cursor() as cursor:
            cursor.execute(
                f"""
                SELECT v.*
                  FROM {_VISTA_COMPONENTI} v
                 WHERE v.prodotto_id = %s
                   AND v.id = %s
                """,  # noqa: S608 — vista costante di modulo; valori come parametri
                [articolo_id, componente_row_id],
            )
            return row_to_dict(cursor)

    # Scopo: Inserisce un componente BoM sul prodotto indicato.
    # ⛔ Dal 2026-09-26 una chiave fuori `COMPONENTE_WRITE_COLUMNS` e'
    #    `RuntimeError` (BB), non piu' scartata: il 400 lo da' il service
    #    (`_extract_componente_payload`). Il padre viene dal path e si scrive
    #    PER ULTIMO, quindi VINCE: il payload non puo' spostare la riga su un
    #    altro prodotto (e il service `prodotto_id` non lo ammette).
    def create_componente(self, articolo_id: UUID | str, data: dict[str, Any]) -> UUID:
        riga = execute_dynamic_insert(
            "catalogo.articoli_componenti",
            {**data, "prodotto_id": articolo_id},
            allowed=COMPONENTE_WRITE_COLUMNS | {"prodotto_id"},
        )
        return riga["id"]

    # Scopo: Aggiorna un componente BoM soltanto se appartiene al prodotto indicato.
    #        Il WHERE (perimetro del padre) lo scrive il metodo: SET dal BB
    #        `sql_set_clause`, whitelist RIGIDA. Payload vuoto -> False.
    def update_componente(
        self,
        articolo_id: UUID | str,
        componente_row_id: UUID | str,
        data: dict[str, Any],
    ) -> bool:
        if not data:
            return False
        set_clause, params = sql_set_clause(data, allowed=COMPONENTE_WRITE_COLUMNS)
        params.extend([articolo_id, componente_row_id])

        with connection.cursor() as cursor:
            cursor.execute(
                f"""
                UPDATE catalogo.articoli_componenti
                SET {set_clause}
                WHERE prodotto_id = %s
                  AND id = %s
                """,  # noqa: S608 — SET da sql_set_clause (colonne verificate sulla whitelist COMPONENTE_WRITE_COLUMNS), valori come parametri
                params,
            )
            return cursor.rowcount > 0

    # Scopo: Elimina un componente BoM con ownership check sul prodotto.
    def delete_componente(self, articolo_id: UUID | str, componente_row_id: UUID | str) -> bool:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                DELETE FROM catalogo.articoli_componenti
                WHERE prodotto_id = %s
                  AND id = %s
                """,
                [articolo_id, componente_row_id],
            )
            return cursor.rowcount > 0

    # Scopo: Lista le note articolo con dati arricchiti di stile e lingua.
    def list_note_articolo(self, articolo_id: UUID | str) -> list[dict[str, Any]]:
        with connection.cursor() as cursor:
            cursor.execute(
                f"""
                SELECT
                    vn.articolo_id,
                    vn.articolo_codice,
                    vn.articolo_descrizione,
                    {_NOTA_PARTITIONED_COLUMNS}
                FROM catalogo.vw_articoli_note vn
                WHERE vn.articolo_id = %s
                ORDER BY vn.nota_anchor_tipo ASC, vn.nota_posizione ASC, vn.nota_seq ASC, vn.nota_id ASC
                """,  # noqa: S608 — proiezione dalla costante _NOTA_PARTITIONED_COLUMNS, valori come parametri
                [articolo_id],
            )
            return rows_to_list(cursor)

    # Scopo: Restituisce una singola nota articolo dalla vista arricchita.
    def get_nota_articolo(
        self,
        articolo_id: UUID | str,
        nota_id: int,
    ) -> dict[str, Any] | None:
        with connection.cursor() as cursor:
            cursor.execute(
                f"""
                SELECT
                    vn.articolo_id,
                    vn.articolo_codice,
                    vn.articolo_descrizione,
                    {_NOTA_PARTITIONED_COLUMNS}
                FROM catalogo.vw_articoli_note vn
                WHERE vn.articolo_id = %s
                  AND vn.nota_id = %s
                """,  # noqa: S608 — proiezione dalla costante _NOTA_PARTITIONED_COLUMNS, valori come parametri
                [articolo_id, nota_id],
            )
            return row_to_dict(cursor)

    # Scopo: Restituisce una singola nota componente dalla vista arricchita.
    def get_nota_componente(self, nota_id: int) -> dict[str, Any] | None:
        with connection.cursor() as cursor:
            cursor.execute(
                f"""
                SELECT
                    vn.articolo_componente_id,
                    vn.prodotto_id,
                    vn.prodotto_codice,
                    vn.prodotto_descrizione,
                    vn.componente_id,
                    vn.componente_codice,
                    vn.componente_descrizione,
                    {_NOTA_PARTITIONED_COLUMNS}
                FROM catalogo.vw_articoli_componenti_note vn
                WHERE vn.nota_id = %s
                """,  # noqa: S608 — proiezione dalla costante _NOTA_PARTITIONED_COLUMNS, valori come parametri
                [nota_id],
            )
            return row_to_dict(cursor)

    # Scopo: Risolve la nota dal parent partizionato, rilevando il target reale.
    def resolve_nota(self, nota_id: int) -> list[dict[str, Any]]:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT
                    {projection}
                FROM catalogo.note n
                WHERE n.id = %s
                ORDER BY n.target_tipo ASC
                LIMIT 2
                """.format(projection=self._nota_resolve_projection()),
                [nota_id],
            )
            return rows_to_list(cursor)

    # Scopo: Lista le note di un componente articolo con dati arricchiti.
    def list_note_componente(self, componente_id: str | UUID) -> list[dict[str, Any]]:
        with connection.cursor() as cursor:
            cursor.execute(
                f"""
                SELECT
                    {_NOTA_PARTITIONED_COLUMNS}
                FROM catalogo.vw_articoli_componenti_note vn
                WHERE vn.articolo_componente_id = %s
                ORDER BY vn.nota_anchor_tipo ASC, vn.nota_posizione ASC,
                         vn.nota_seq ASC, vn.nota_id ASC
                """,  # noqa: S608 — proiezione dalla costante _NOTA_PARTITIONED_COLUMNS, valori come parametri
                [str(componente_id)],
            )
            return rows_to_list(cursor)

    # Scopo: Inserisce una nota nella partizione indicata da target_tipo.
    # ⛔ Whitelist RIGIDA dal 2026-09-26 (vedi `create_componente`): il 400
    #    lo da' il service (`_extract_nota_payload`). `target_tipo`/`target_id`
    #    li decide il repository, scritti PER ULTIMI: vincono sul payload.
    def create_nota(self, target_tipo: str, target_id: str | UUID, data: dict[str, Any]) -> int:
        riga = execute_dynamic_insert(
            "catalogo.note",
            {**data, "target_tipo": target_tipo, "target_id": str(target_id)},
            allowed=NOTA_WRITE_COLUMNS | {"target_tipo", "target_id"},
        )
        return int(riga["id"])

    # Scopo: Aggiorna una nota in modo sicuro usando anche il target_tipo come discriminante.
    #        SET dal BB `sql_set_clause` (whitelist RIGIDA), WHERE del metodo.
    def update_nota(self, nota_id: int, target_tipo: str, data: dict[str, Any]) -> bool:
        if not data:
            return False
        set_clause, params = sql_set_clause(data, allowed=NOTA_WRITE_COLUMNS)
        params.extend([target_tipo, nota_id])

        with connection.cursor() as cursor:
            cursor.execute(
                f"""
                UPDATE catalogo.note
                SET {set_clause}
                WHERE target_tipo = %s
                  AND id = %s
                """,  # noqa: S608 — SET da sql_set_clause (colonne verificate sulla whitelist NOTA_WRITE_COLUMNS), valori come parametri
                params,
            )
            return cursor.rowcount > 0

    # Scopo: Elimina una nota usando il discriminante target_tipo della PK composita.
    def delete_nota(self, nota_id: int, target_tipo: str) -> bool:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                DELETE FROM catalogo.note
                WHERE target_tipo = %s
                  AND id = %s
                """,
                [target_tipo, nota_id],
            )
            return cursor.rowcount > 0
