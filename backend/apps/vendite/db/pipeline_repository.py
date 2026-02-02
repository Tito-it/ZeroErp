from dataclasses import dataclass
from datetime import date
from typing import Any

from django.db import connection

# Repository SQL: incapsula accesso DB per orchestrazione pipeline vendite.

@dataclass(frozen=True)
class LottoContext:
    competenza_mese: date
    tipo_doc_fiscale_id: int | None
    utility_id: int | None
    billing_account_id: int | None
    lock_batch_id: int | None


@dataclass(frozen=True)
class PipelineStep:
    stato_doc_fiscale_id: int
    descrizione: str | None
    ordine: int | None


class VenditePipelineRepository:
    """Wrapper SQL a basso livello per l'orchestrazione pipeline vendite."""

    ALLOWED_TASK_FUNCTIONS = {
        "select_attivita": "vendite.fn_select_attivita_fatturabili",
    }

    def get_or_create_lotto(
        self,
        lotto_id: int | None,
        competenza_mese: date | None,
        tipo_doc_fiscale_id: int | None,
        utility_id: int | None,
        billing_account_id: int | None,
        lock_batch_id: int | None,
        meta: dict[str, Any] | None,
        tipo_lotto: str | None,
    ) -> int:
        # Delega al DB la risoluzione/creazione lotto per mantenere coerenza funzionale.
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT vendite.fn_get_or_create_lotto(
                    %s, %s, %s, %s, %s, %s, %s, %s
                )
                """,
                [
                    lotto_id,
                    competenza_mese,
                    tipo_doc_fiscale_id,
                    utility_id,
                    billing_account_id,
                    lock_batch_id,
                    meta,
                    tipo_lotto,
                ],
            )
            row = cursor.fetchone()
        return int(row[0])

    def get_lotto_tipo(self, lotto_id: int) -> str | None:
        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT tipo_lotto FROM vendite.fatturazione_lotti WHERE id = %s",
                [lotto_id],
            )
            row = cursor.fetchone()
        return None if not row else row[0]

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
        return None if not row else int(row[0])

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
                UPDATE vendite.fatturazione_lotti
                SET stato_operativo = 'CHIUSO',
                    data_update = now(),
                    user_update = current_user
                WHERE id = %s
                """,
                [lotto_id],
            )
            cursor.execute(
                """
                UPDATE vendite.fatture f
                SET stato_doc_fiscale_id = %s,
                    data_update = now(),
                    user_update = current_user
                FROM vendite.fatturazione_lotti_fatture lf
                WHERE lf.lotto_id = %s
                  AND lf.fattura_id = f.id
                """,
                [inviata_id, lotto_id],
            )

    def log_pipeline_fase(
        self,
        lotto_id: int,
        stato_doc_fiscale_id: int,
        fase: str,
        status: str,
        messaggio: str | None,
        meta: dict[str, Any] | None,
    ) -> None:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT vendite.fn_log_pipeline_fase(
                    %s, %s, %s, %s, %s, %s
                )
                """,
                [lotto_id, stato_doc_fiscale_id, fase, status, messaggio, meta],
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

    def get_step_processes(self, stato_doc_fiscale_id: int, rollback: bool) -> list[dict[str, Any]]:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT CASE WHEN %s THEN rollback ELSE processi END
                FROM vendite.fatturazione_pipeline
                WHERE stato_doc_fiscale_id = %s
                  AND attivo IS TRUE
                """,
                [rollback, stato_doc_fiscale_id],
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
        # Normalizza i parametri JSON prima della chiamata alla funzione SQL.
        lock = self._as_bool(params.get("lock"), default=False)
        data_fatturazione = self._empty_to_none(params.get("data_fatturazione"))
        valuta_id = self._empty_to_none(params.get("valuta_id"))
        emittente_id = self._empty_to_none(params.get("emittente_soggetto_ruolo_id"))
        limit_value = self._empty_to_none(params.get("limit"))

        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT vendite.fn_select_attivita_fatturabili(
                    p_competenza_mese => %s,
                    p_tipo_doc_fiscale_id => %s,
                    p_lock_batch_id => %s,
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

    @staticmethod
    def _as_bool(value: Any, default: bool = False) -> bool:
        if value is None:
            return default
        if isinstance(value, bool):
            return value
        return str(value).strip().lower() in {"1", "true", "t", "yes", "y", "on"}

    @staticmethod
    def _empty_to_none(value: Any) -> Any:
        if value is None:
            return None
        if isinstance(value, str) and value.strip() == "":
            return None
        return value
