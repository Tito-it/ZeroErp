# ------------------------------------------------------------
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Accesso DB specializzato per BoM articoli e note catalogo.
# ------------------------------------------------------------

from __future__ import annotations

from typing import Any
from uuid import UUID

from django.db import connection

from apps.core.db._helpers import row_to_dict, rows_to_list
from apps.core.db.sql_write_helpers import execute_dynamic_insert, sql_set_clause

# Colonne SCRIVIBILI di una riga BoM: whitelist RIGIDA del BB di scrittura
# (2026-09-26 — prima mappa nome -> tipo per `sql_placeholder`/`to_write_param`,
# ritirati). `meta` (jsonb) arriva dal service come dict o None: il BB lo
# casta da solo, `jsonb=` non serve. `prodotto_id` NON e' qui: lo scrive il
# repository dal path (`create_componente`), mai il payload.
COMPONENTE_WRITE_COLUMNS: frozenset[str] = frozenset({
    "componente_id",
    "coeff_qta",
    "partecipa_qta",
    "determina_qta_padre",
    "obbligatorio",
    "valido_dal",
    "valido_al",
    "attivo",
    "esposto_in_fattura",
    "meta",
})

COMPONENTE_DETAIL_COLUMNS: tuple[str, ...] = (
    "ac.id",
    "ac.prodotto_id",
    "ac.componente_id",
    "ac.coeff_qta",
    "ac.partecipa_qta",
    "ac.determina_qta_padre",
    "ac.obbligatorio",
    "ac.valido_dal",
    "ac.valido_al",
    "ac.esposto_in_fattura",
    "ac.meta",
    "ac.user_insert",
    "ac.user_update",
    "ac.data_insert",
    "ac.data_update",
    "ac.tx_id",
    "ac.storicizza",
    "ac.attivo",
    "ac.note_target_tipo",
    "ac.note_id",
    "ap.codice AS prodotto_codice",
    "ap.descrizione AS prodotto_descrizione",
    "acmp.codice AS componente_codice",
    "acmp.descrizione AS componente_descrizione",
    # Capability di chiusura riga BoM (Fase 2 refactor catalogo).
    # La stessa logica e' replicata in `catalogo.vw_articoli_componenti_dettaglio`
    # (migration 20260428-03). Single source of truth: il dominio "una riga e'
    # chiudibile finche' valido_al IS NULL". Se la regola cambia in DB,
    # aggiornare ENTRAMBI: vista + COMPONENTE_DETAIL_COLUMNS qui.
    # `data_min_chiusura` / `data_default_chiusura` sono NULL su righe gia'
    # chiuse (autodocumentante: il FE non puo' aprire dialog su NULL).
    "(ac.valido_al IS NULL) AS puo_chiudersi",
    "CASE WHEN ac.valido_al IS NULL THEN ac.valido_dal END AS data_min_chiusura",
    "CASE WHEN ac.valido_al IS NULL THEN GREATEST(ac.valido_dal, CURRENT_DATE) END AS data_default_chiusura",
    "CASE WHEN ac.valido_al IS NULL THEN NULL ELSE 'RIGA_GIA_CHIUSA' END AS motivo_non_chiudibile",
)

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

    # Scopo: Restituisce la proiezione SQL esplicita per dettaglio componente.
    @staticmethod
    def _componente_projection() -> str:
        return ",\n                    ".join(COMPONENTE_DETAIL_COLUMNS)

    # Scopo: Restituisce la proiezione minima per risolvere una nota via tabella padre.
    @staticmethod
    def _nota_resolve_projection() -> str:
        return ",\n                    ".join(NOTE_RESOLVE_COLUMNS)

    # Scopo: Lista i componenti BoM di un prodotto con dati arricchiti del componente.
    def list_componenti(self, articolo_id: UUID | str) -> list[dict[str, Any]]:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT
                    {projection}
                FROM catalogo.articoli_componenti ac
                LEFT JOIN catalogo.articoli ap
                  ON ap.id = ac.prodotto_id
                LEFT JOIN catalogo.articoli acmp
                  ON acmp.id = ac.componente_id
                WHERE ac.prodotto_id = %s
                ORDER BY ac.valido_dal DESC, ac.id ASC
                """.format(projection=self._componente_projection()),
                [articolo_id],
            )
            return rows_to_list(cursor)

    # Scopo: Restituisce il singolo componente BoM con ownership sul prodotto.
    def get_componente(
        self,
        articolo_id: UUID | str,
        componente_row_id: UUID | str,
    ) -> dict[str, Any] | None:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT
                    {projection}
                FROM catalogo.articoli_componenti ac
                LEFT JOIN catalogo.articoli ap
                  ON ap.id = ac.prodotto_id
                LEFT JOIN catalogo.articoli acmp
                  ON acmp.id = ac.componente_id
                WHERE ac.prodotto_id = %s
                  AND ac.id = %s
                """.format(projection=self._componente_projection()),
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
