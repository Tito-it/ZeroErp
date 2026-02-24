# ------------------------------------------------------------
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Accesso DB per dominio commesse (CRUD + pull AF).
# ------------------------------------------------------------

from dataclasses import dataclass
from datetime import date
from decimal import Decimal
import json
from typing import Any

from django.db import connection

from apps.vendite.types import CommessaEmitResult, CommessaPushLogRow, CommessaStatoResult

# Repository SQL: incapsula accesso DB per commesse, commesse_attivita e push log.


@dataclass(frozen=True)
class CommessaAttivitaInput:
    """Input per fn_upsert_commessa_attivita — tutti i campi della riga operativa."""

    commessa_id: int
    segment_key: str
    articolo_id: int
    uom_id: int
    quantita: Decimal
    competenza_mese: date
    prezzo_snapshot: Decimal
    tipo_doc_fiscale_id: int
    valuta_id: int
    prezzo_bloccato: bool
    pricing_mode: str  # FIXED | FORMULA | SCAGLIONI
    prezzo_da_riallineare: bool
    stato_approvazione: str  # BOZZA | APPROVATA | RIFIUTATA
    stato_emissione: str  # NON_EMESSA | EMESSA | ANNULLATA
    tipo_movimento: str  # NORMALE | ...
    tipo_consumo: str  # ACCONTO | ...
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
    sorgente_tipo_id: int | None = None
    sorgente_uid: str | None = None
    meta: dict[str, Any] | None = None


class CommesseRepository:
    """Wrapper SQL a basso livello per il dominio commesse."""

    @staticmethod
    def _to_jsonb_param(value: Any) -> str | None:
        if value is None:
            return None
        return json.dumps(value)

    @staticmethod
    def _decode_jsonb(value: Any, default: Any) -> Any:
        if isinstance(value, (list, dict)):
            return value
        if isinstance(value, str):
            try:
                return json.loads(value)
            except json.JSONDecodeError:
                pass
        return default

    # --- Gruppo 1: Commessa ---

    def get_or_create_commessa(
        self,
        *,
        billing_account_id: int,
        utility_id: int | None,
        tipo_commessa: str,
        policy_fatturazione: str,
        fatturazione_immediata: bool,
        priorita_operativa: str,
        emittente_soggetto_ruolo_id: int,
        competenza_dal: date,
        competenza_al: date,
        meta: dict | None = None,
        force_new: bool = False,
    ) -> int:
        """Risolve o crea una commessa. Restituisce commessa_id."""
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
                    p_emittente_soggetto_ruolo_id => %s,
                    p_competenza_dal => %s,
                    p_competenza_al => %s,
                    p_meta => %s::jsonb,
                    p_force_new => %s
                )
                """,
                [
                    billing_account_id,
                    utility_id,
                    tipo_commessa,
                    policy_fatturazione,
                    fatturazione_immediata,
                    priorita_operativa,
                    emittente_soggetto_ruolo_id,
                    competenza_dal,
                    competenza_al,
                    self._to_jsonb_param(meta),
                    force_new,
                ],
            )
            row = cursor.fetchone()
        assert row is not None
        return int(row[0])

    def link_sorgente(
        self,
        *,
        commessa_id: int,
        sorgente_tipo_id: int,
        sorgente_uid: str,
        sorgente_riga: int | None = None,
        meta: dict | None = None,
    ) -> int:
        """Collega la sorgente ROOT alla commessa. Idempotente su stesso sorgente_uid.
        Restituisce il link_id."""
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT vendite.fn_link_commessa_sorgente(
                    p_commessa_id => %s,
                    p_sorgente_tipo_id => %s,
                    p_sorgente_uid => %s,
                    p_sorgente_riga => %s,
                    p_meta => %s::jsonb
                )
                """,
                [
                    commessa_id,
                    sorgente_tipo_id,
                    sorgente_uid,
                    sorgente_riga,
                    self._to_jsonb_param(meta or {}),
                ],
            )
            row = cursor.fetchone()
        assert row is not None
        return int(row[0])

    def get_commessa_stato(self, commessa_id: int) -> CommessaStatoResult | None:
        """Stato e contatori della commessa in un round-trip."""
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT total_attivita, total_approvate, total_emesse
                FROM vendite.fn_get_commessa_stato(%s)
                """,
                [commessa_id],
            )
            row = cursor.fetchone()
        if not row:
            return None
        return CommessaStatoResult(
            total_attivita=int(row[0]),
            total_approvate=int(row[1]),
            total_emesse=int(row[2]),
        )

    # --- Gruppo 2: Attività commessa ---

    def upsert_attivita(self, inp: CommessaAttivitaInput) -> int:
        """Inserisce o aggiorna una riga operativa sulla commessa (idempotente su segment_key).
        Restituisce commessa_attivita_id."""
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT vendite.fn_upsert_commessa_attivita(
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
                    p_sorgente_uid => %s,
                    p_tipo_movimento => %s,
                    p_tipo_consumo => %s,
                    p_meta => %s::jsonb
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
                    inp.sorgente_uid,
                    inp.tipo_movimento,
                    inp.tipo_consumo,
                    self._to_jsonb_param(inp.meta),
                ],
            )
            row = cursor.fetchone()
        assert row is not None
        return int(row[0])

    # --- Gruppo 3: Emit attività fatturabili (pull) ---

    def emit_attivita_fatturabili(
        self,
        commessa_id: int,
        *,
        lotto_attivita_id: int | None = None,
        only_approved: bool = True,
        dry_run: bool = False,
    ) -> CommessaEmitResult:
        """Pull commessa → attivita_fatturabili (step 0 pipeline fatturazione).
        Idempotente. Restituisce contatori candidati/inseriti/aggiornati."""
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT total_candidate, inserted_rows, updated_rows
                FROM vendite.fn_emit_attivita_fatturabili_da_commessa(
                    p_commessa_id => %s,
                    p_lotto_attivita_id => %s,
                    p_only_approved => %s,
                    p_dry_run => %s
                )
                """,
                [commessa_id, lotto_attivita_id, only_approved, dry_run],
            )
            row = cursor.fetchone()
        assert row is not None
        return CommessaEmitResult(
            total_candidate=int(row[0]),
            inserted_rows=int(row[1]),
            updated_rows=int(row[2]),
        )

    # --- Gruppo 4: Push log ---

    def log_push_run(
        self,
        *,
        stato: str,
        dry_run: bool = False,
        source_types: list[str] | None = None,
        risultato: dict[str, Any] | None = None,
        durata_ms: int | None = None,
        user_run: str | None = None,
    ) -> int:
        """Registra il risultato di un run dell'orchestratore push.
        Restituisce push_log_id."""
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT vendite.fn_log_commessa_push_run(
                    p_dry_run => %s,
                    p_source_types => %s,
                    p_risultato => %s::jsonb,
                    p_stato => %s,
                    p_durata_ms => %s,
                    p_user_run => %s
                )
                """,
                [
                    dry_run,
                    source_types,
                    self._to_jsonb_param(risultato),
                    stato,
                    durata_ms,
                    user_run,
                ],
            )
            row = cursor.fetchone()
        assert row is not None
        return int(row[0])

    def get_push_log(self, push_log_id: int) -> CommessaPushLogRow | None:
        """Legge un record di push log per id."""
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT id, run_at, dry_run, source_types,
                       risultato, stato, durata_ms, user_run
                FROM vendite.commesse_push_log
                WHERE id = %s
                """,
                [push_log_id],
            )
            row = cursor.fetchone()
        if not row:
            return None
        risultato_raw: Any = self._decode_jsonb(row[4], None)
        return CommessaPushLogRow(
            id=int(row[0]),
            run_at=row[1].isoformat() if row[1] else "",
            dry_run=bool(row[2]),
            source_types=list(row[3]) if row[3] else None,
            risultato=risultato_raw if isinstance(risultato_raw, dict) else None,
            stato=str(row[5]),
            durata_ms=None if row[6] is None else int(row[6]),
            user_run=row[7],
        )
