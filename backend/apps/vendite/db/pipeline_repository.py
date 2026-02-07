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
from typing import Any

from django.db import connection

from apps.core.services.value_normalizer import as_bool, empty_to_none
from apps.vendite.types import LottoPipelineMeta

# Repository SQL: incapsula accesso DB per orchestrazione pipeline vendite.

@dataclass(frozen=True)
class LottoContext:
    competenza_mese: date
    tipo_doc_fiscale_id: int | None
    utility_id: int | None
    billing_account_id: int | None
    lock_batch_id: str | None


@dataclass(frozen=True)
class PipelineStep:
    stato_doc_fiscale_id: int
    descrizione: str | None
    ordine: int | None


@dataclass(frozen=True)
class GroupAttivitaInput:
    attivita_id: int
    articolo_id: int
    dest_billing_account_id: int | None
    uom_id: int | None
    prezzo_unitario: Decimal | None
    iva_id: int | None
    competenza_dal: date | None
    competenza_al: date | None
    data_attivita: date | None
    visibilita_componenti: str
    calcolo_qta_padre: str
    arrotondamento_importi_dec: int
    arrotondamento_quantita_dec: int
    metodo_arrotondamento_importi: str
    metodo_arrotondamento_quantita: str


@dataclass(frozen=True)
class AttivitaDaFatturare:
    id: int
    articolo_id: int
    quantita: Decimal | None
    prezzo_unitario: Decimal | None
    uom_id: int | None
    sorgente_tipo_id: int | None
    sorgente_uid: str | None
    sorgente_riga: int | None
    articolo_descrizione: str | None


class VenditePipelineRepository:
    """Wrapper SQL a basso livello per l'orchestrazione pipeline vendite."""

    # `fn` nei JSON task e` mantenuto come token di compatibilita` SQL legacy.
    ALLOWED_TASK_FUNCTIONS = {
        "select_attivita": "vendite.fn_select_attivita_fatturabili",
        "generate_fatture_righe": "vendite.fn_generate_fatture_righe",
    }

    @staticmethod
    def _to_jsonb_param(value: LottoPipelineMeta | None) -> str | None:
        if value is None:
            return None
        # Serializza esplicitamente per evitare errori adapter psycopg su dict/list.
        return json.dumps(value)

    def get_or_create_lotto(
        self,
        lotto_id: int | None,
        competenza_mese: date | None,
        tipo_doc_fiscale_id: int | None,
        utility_id: int | None,
        billing_account_id: int | None,
        lock_batch_id: str | None,
        meta: LottoPipelineMeta | None,
        tipo_lotto: str | None,
    ) -> int:
        # Delega al DB la risoluzione/creazione lotto per mantenere coerenza funzionale.
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT vendite.fn_get_or_create_lotto(
                    %s, %s, %s, %s, %s, %s::uuid, %s::jsonb, %s::text
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
                ],
            )
            row = cursor.fetchone()
            assert row is not None
        return int(row[0])

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

    def get_stato_doc_fiscale_id(self, codice: str) -> int | None:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT id
                FROM config.stati_doc_fiscale
                WHERE codice = %s
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

    def set_lotto_job_stato(self, lotto_id: int, stato: str, messaggio: str) -> None:
        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT vendite.fn_set_fatturazione_lotto_stato(%s, %s, %s)",
                [lotto_id, stato, messaggio],
            )

    def list_pipeline_steps(self, tipo_lotto: str) -> list[PipelineStep]:
        # Ordina gli step con config.stati_doc_fiscale.ordine come nella pipeline SQL.
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT fp.stato_doc_fiscale_id, fp.descrizione, sd.ordine
                FROM vendite.fatturazione_pipeline fp
                JOIN config.stati_doc_fiscale sd
                  ON sd.id = fp.stato_doc_fiscale_id
                WHERE fp.attivo IS TRUE
                  AND fp.tipo_lotto = %s
                  AND COALESCE(sd.applica_lotto, false) IS TRUE
                ORDER BY sd.ordine
                """,
                [tipo_lotto],
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

    def close_giornaliero_lotto(self, lotto_id: int, inviata_id: int) -> None:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT vendite.fn_close_giornaliero_lotto(%s, %s)
                """,
                [lotto_id, inviata_id],
            )

    def log_pipeline_fase(
        self,
        lotto_id: int,
        stato_doc_fiscale_id: int,
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

    def get_lotto_context(self, lotto_id: int) -> LottoContext | None:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT competenza_mese,
                       tipo_doc_fiscale_id,
                       utility_id,
                       billing_account_id,
                       lock_batch_id
                FROM vendite.fatturazione_lotti
                WHERE id = %s
                """,
                [lotto_id],
            )
            row = cursor.fetchone()
        if not row:
            return None
        return LottoContext(
            competenza_mese=row[0],
            tipo_doc_fiscale_id=row[1],
            utility_id=row[2],
            billing_account_id=row[3],
            lock_batch_id=row[4],
        )

    def get_step_processes(
        self,
        stato_doc_fiscale_id: int,
        *,
        tipo_lotto: str,
        rollback: bool,
    ) -> list[dict[str, Any]]:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT CASE WHEN %s THEN rollback ELSE processi END
                FROM vendite.fatturazione_pipeline
                WHERE stato_doc_fiscale_id = %s
                  AND tipo_lotto = %s
                  AND attivo IS TRUE
                LIMIT 1
                """,
                [rollback, stato_doc_fiscale_id, tipo_lotto],
            )
            row = cursor.fetchone()

        if not row:
            return []

        value = row[0]
        if isinstance(value, list):
            return value
        return []

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
        emittente_id = empty_to_none(params.get("emittente_soggetto_ruolo_id"))
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
                    p_limit => %s
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
                ],
            )

    def get_group_attivita_input(self, attivita_id: int) -> GroupAttivitaInput | None:
        with connection.cursor() as cursor:
            cursor.execute(
                """
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
                    COALESCE(r.visibilita_componenti, 'solo_padre') AS visibilita_componenti,
                    COALESCE(r.calcolo_qta_padre, 'fissa') AS calcolo_qta_padre,
                    COALESCE(r.arrotondamento_importi_dec, 2) AS arrotondamento_importi_dec,
                    COALESCE(r.arrotondamento_quantita_dec, 3) AS arrotondamento_quantita_dec,
                    COALESCE(r.metodo_arrotondamento_importi, 'HALF_UP') AS metodo_arrotondamento_importi,
                    COALESCE(r.metodo_arrotondamento_quantita, 'HALF_UP') AS metodo_arrotondamento_quantita
                FROM vendite.attivita_fatturabili a
                JOIN catalogo.articoli art
                  ON art.id = a.articolo_id
                LEFT JOIN vendite.articolo_regole_fatturazione r
                  ON r.articolo_id = a.articolo_id
                WHERE a.id = %s
                """,
                [attivita_id],
            )
            row = cursor.fetchone()
        if not row:
            return None
        return GroupAttivitaInput(
            attivita_id=int(row[0]),
            articolo_id=int(row[1]),
            dest_billing_account_id=None if row[2] is None else int(row[2]),
            uom_id=None if row[3] is None else int(row[3]),
            prezzo_unitario=row[4],
            iva_id=None if row[5] is None else int(row[5]),
            competenza_dal=row[6],
            competenza_al=row[7],
            data_attivita=row[8],
            visibilita_componenti=row[9],
            calcolo_qta_padre=row[10],
            arrotondamento_importi_dec=int(row[11]),
            arrotondamento_quantita_dec=int(row[12]),
            metodo_arrotondamento_importi=row[13],
            metodo_arrotondamento_quantita=row[14],
        )

    def list_attivita_da_fatturare(self, lotto_id: int) -> list[AttivitaDaFatturare]:
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
                    art.descrizione
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
                """,
                [lotto_id],
            )
            rows = cursor.fetchall()
        return [
            AttivitaDaFatturare(
                id=int(row[0]),
                articolo_id=int(row[1]),
                quantita=row[2],
                prezzo_unitario=row[3],
                uom_id=None if row[4] is None else int(row[4]),
                sorgente_tipo_id=None if row[5] is None else int(row[5]),
                sorgente_uid=row[6],
                sorgente_riga=row[7],
                articolo_descrizione=row[8],
            )
            for row in rows
        ]

    def get_or_create_fattura_header(self, lotto_id: int, attivita_id: int) -> int:
        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT vendite.fn_get_or_create_fattura_header(%s, %s)",
                [lotto_id, attivita_id],
            )
            row = cursor.fetchone()
            assert row is not None
        return int(row[0])

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
