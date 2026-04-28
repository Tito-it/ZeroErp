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
from apps.core.db.sql_write_helpers import sql_placeholder, to_write_param

COMPONENTE_WRITE_COLUMNS: dict[str, str] = {
    "componente_id": "uuid",
    "coeff_qta": "numeric",
    "partecipa_qta": "bool",
    "determina_qta_padre": "bool",
    "obbligatorio": "bool",
    "valido_dal": "date",
    "valido_al": "date",
    "attivo": "bool",
    "esposto_in_fattura": "bool",
    "meta": "jsonb",
}

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

NOTA_WRITE_COLUMNS: dict[str, str] = {
    "target_riga_id": "uuid",
    "anchor_tipo": "text",
    "posizione": "text",
    "seq": "int",
    "testo": "text",
    "testo_md": "text",
    "id_stile": "int",
    "id_lingua": "int",
    "visibile": "bool",
    "solo_stampa": "bool",
    "meta": "jsonb",
}

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
    def create_componente(self, articolo_id: UUID | str, data: dict[str, Any]) -> UUID:
        fields = [("prodotto_id", articolo_id), *[(key, value) for key, value in data.items() if key in COMPONENTE_WRITE_COLUMNS]]

        column_names = [field_name for field_name, _ in fields]
        placeholders = ", ".join(
            "%s" if field_name == "prodotto_id" else sql_placeholder(COMPONENTE_WRITE_COLUMNS[field_name])
            for field_name, _ in fields
        )
        params = [
            field_value if field_name == "prodotto_id" else to_write_param(field_value, COMPONENTE_WRITE_COLUMNS[field_name])
            for field_name, field_value in fields
        ]

        with connection.cursor() as cursor:
            cursor.execute(
                f"""
                INSERT INTO catalogo.articoli_componenti ({", ".join(column_names)})
                VALUES ({placeholders})
                RETURNING id
                """,
                params,
            )
            row = cursor.fetchone()

        assert row is not None
        return row[0]

    # Scopo: Aggiorna un componente BoM soltanto se appartiene al prodotto indicato.
    def update_componente(
        self,
        articolo_id: UUID | str,
        componente_row_id: UUID | str,
        data: dict[str, Any],
    ) -> bool:
        fields = [(key, value) for key, value in data.items() if key in COMPONENTE_WRITE_COLUMNS]
        if not fields:
            return False

        set_clause = ", ".join(
            f"{field_name} = {sql_placeholder(COMPONENTE_WRITE_COLUMNS[field_name])}"
            for field_name, _ in fields
        )
        params = [
            to_write_param(field_value, COMPONENTE_WRITE_COLUMNS[field_name])
            for field_name, field_value in fields
        ]
        params.extend([articolo_id, componente_row_id])

        with connection.cursor() as cursor:
            cursor.execute(
                f"""
                UPDATE catalogo.articoli_componenti
                SET {set_clause}
                WHERE prodotto_id = %s
                  AND id = %s
                """,
                params,
            )
            return cursor.rowcount > 0

    # Scopo: Duplica atomicamente la versione corrente di un componente BoM.
    #        Wrapper su catalogo.fn_duplica_componente_versione (Fase 3): la fn DB
    #        chiude la sorgente con valido_al=p_chiudi_al (default oggi) e
    #        inserisce una nuova riga con valido_dal=p_chiudi_al+1, copia
    #        verbatim della struttura. Tutto in singola TX con advisory lock
    #        per articolo. Eventuali raise P0001 (E_BOM_*) propagano via
    #        DatabaseError e vengono tradotti dal service.
    #        Ritorna l'UUID della nuova riga inserita.
    def duplica_versione(
        self,
        articolo_id: UUID | str,
        componente_row_id: UUID | str,
        chiudi_al: object | None,
    ) -> UUID:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT catalogo.fn_duplica_componente_versione(%s::uuid, %s::uuid, %s::date)
                """,
                [str(articolo_id), str(componente_row_id), chiudi_al],
            )
            row = cursor.fetchone()
        assert row is not None
        return row[0]

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
                """
                SELECT
                    vn.articolo_id,
                    vn.articolo_codice,
                    vn.articolo_descrizione,
                    vn.nota_id,
                    vn.nota_target_tipo,
                    vn.nota_target_id,
                    vn.nota_target_riga_id,
                    vn.nota_anchor_tipo,
                    vn.nota_posizione,
                    vn.nota_seq,
                    vn.nota_testo,
                    vn.nota_testo_md,
                    vn.nota_visibile,
                    vn.nota_solo_stampa,
                    vn.nota_meta,
                    vn.nota_data_insert,
                    vn.nota_user_insert,
                    vn.nota_data_update,
                    vn.nota_user_update,
                    vn.stile_id,
                    vn.stile_codice,
                    vn.stile_descrizione,
                    vn.lingua_id,
                    vn.lingua_codice_iso,
                    vn.lingua_descrizione,
                    vn.lingua_descrizione_locale
                FROM catalogo.vw_articoli_note vn
                WHERE vn.articolo_id = %s
                ORDER BY vn.nota_anchor_tipo ASC, vn.nota_posizione ASC, vn.nota_seq ASC, vn.nota_id ASC
                """,
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
                """
                SELECT
                    vn.articolo_id,
                    vn.articolo_codice,
                    vn.articolo_descrizione,
                    vn.nota_id,
                    vn.nota_target_tipo,
                    vn.nota_target_id,
                    vn.nota_target_riga_id,
                    vn.nota_anchor_tipo,
                    vn.nota_posizione,
                    vn.nota_seq,
                    vn.nota_testo,
                    vn.nota_testo_md,
                    vn.nota_visibile,
                    vn.nota_solo_stampa,
                    vn.nota_meta,
                    vn.nota_data_insert,
                    vn.nota_user_insert,
                    vn.nota_data_update,
                    vn.nota_user_update,
                    vn.stile_id,
                    vn.stile_codice,
                    vn.stile_descrizione,
                    vn.lingua_id,
                    vn.lingua_codice_iso,
                    vn.lingua_descrizione,
                    vn.lingua_descrizione_locale
                FROM catalogo.vw_articoli_note vn
                WHERE vn.articolo_id = %s
                  AND vn.nota_id = %s
                """,
                [articolo_id, nota_id],
            )
            return row_to_dict(cursor)

    # Scopo: Restituisce una singola nota componente dalla vista arricchita.
    def get_nota_componente(self, nota_id: int) -> dict[str, Any] | None:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT
                    vn.articolo_componente_id,
                    vn.prodotto_id,
                    vn.prodotto_codice,
                    vn.prodotto_descrizione,
                    vn.componente_id,
                    vn.componente_codice,
                    vn.componente_descrizione,
                    vn.nota_id,
                    vn.nota_target_tipo,
                    vn.nota_target_id,
                    vn.nota_target_riga_id,
                    vn.nota_anchor_tipo,
                    vn.nota_posizione,
                    vn.nota_seq,
                    vn.nota_testo,
                    vn.nota_testo_md,
                    vn.nota_visibile,
                    vn.nota_solo_stampa,
                    vn.nota_meta,
                    vn.nota_data_insert,
                    vn.nota_user_insert,
                    vn.nota_data_update,
                    vn.nota_user_update,
                    vn.stile_id,
                    vn.stile_codice,
                    vn.stile_descrizione,
                    vn.lingua_id,
                    vn.lingua_codice_iso,
                    vn.lingua_descrizione,
                    vn.lingua_descrizione_locale
                FROM catalogo.vw_articoli_componenti_note vn
                WHERE vn.nota_id = %s
                """,
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
                """
                SELECT vn.nota_id, vn.nota_target_tipo, vn.nota_target_id,
                       vn.nota_anchor_tipo, vn.nota_posizione, vn.nota_seq,
                       vn.nota_testo, vn.nota_testo_md,
                       vn.nota_visibile, vn.nota_solo_stampa, vn.nota_meta,
                       vn.nota_data_insert, vn.nota_user_insert,
                       vn.stile_id AS id_stile, vn.stile_codice, vn.stile_descrizione
                FROM catalogo.vw_articoli_componenti_note vn
                WHERE vn.articolo_componente_id = %s
                ORDER BY vn.nota_anchor_tipo ASC, vn.nota_posizione ASC,
                         vn.nota_seq ASC, vn.nota_id ASC
                """,
                [str(componente_id)],
            )
            return rows_to_list(cursor)

    # Scopo: Inserisce una nota nella partizione indicata da target_tipo.
    def create_nota(self, target_tipo: str, target_id: str | UUID, data: dict[str, Any]) -> int:
        fields = [
            ("target_tipo", target_tipo),
            ("target_id", str(target_id)),
            *[(key, value) for key, value in data.items() if key in NOTA_WRITE_COLUMNS],
        ]

        column_names = [field_name for field_name, _ in fields]
        placeholders = ", ".join(
            "%s"
            if field_name in {"target_tipo", "target_id"}
            else sql_placeholder(NOTA_WRITE_COLUMNS[field_name])
            for field_name, _ in fields
        )
        params = [
            field_value
            if field_name in {"target_tipo", "target_id"}
            else to_write_param(field_value, NOTA_WRITE_COLUMNS[field_name])
            for field_name, field_value in fields
        ]

        with connection.cursor() as cursor:
            cursor.execute(
                f"""
                INSERT INTO catalogo.note ({", ".join(column_names)})
                VALUES ({placeholders})
                RETURNING id
                """,
                params,
            )
            row = cursor.fetchone()

        assert row is not None
        return int(row[0])

    # Scopo: Aggiorna una nota in modo sicuro usando anche il target_tipo come discriminante.
    def update_nota(self, nota_id: int, target_tipo: str, data: dict[str, Any]) -> bool:
        fields = [(key, value) for key, value in data.items() if key in NOTA_WRITE_COLUMNS]
        if not fields:
            return False

        set_clause = ", ".join(
            f"{field_name} = {sql_placeholder(NOTA_WRITE_COLUMNS[field_name])}"
            for field_name, _ in fields
        )
        params = [
            to_write_param(field_value, NOTA_WRITE_COLUMNS[field_name])
            for field_name, field_value in fields
        ]
        params.extend([target_tipo, nota_id])

        with connection.cursor() as cursor:
            cursor.execute(
                f"""
                UPDATE catalogo.note
                SET {set_clause}
                WHERE target_tipo = %s
                  AND id = %s
                """,
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
