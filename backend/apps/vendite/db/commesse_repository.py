# ------------------------------------------------------------
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Accesso DB per dominio commesse (CRUD + pull AF + push sorgenti).
# ------------------------------------------------------------

from dataclasses import dataclass
from datetime import date
from decimal import Decimal
import json
from typing import Any

from django.db import connection

from apps.core.services.error_manager import ErrorManager
from apps.vendite.types import CommessaEmitResult, CommessaPushLogRow, CommessaStatoResult

# Repository SQL: incapsula accesso DB per commesse, commesse_attivita e push log.


# --- Mapping codice sorgente → fn SQL da chiamare ---
_SORGENTE_FN_MAP: dict[str, str] = {
    "PREVENTIVO": "vendite.fn_list_preventivi_da_pushare",
    "ORDINE_VENDITA": "vendite.fn_list_ordini_da_pushare",
    "ATTIVITA_CONSUMI": "vendite.fn_list_consumi_da_pushare",
    "CONTRATTO": "vendite.fn_list_contratti_da_pushare",
    "DDT_VENDITA": "vendite.fn_list_ddt_da_pushare",
}

# Nomi delle 25 colonne condivise da tutte le fn_list_*_da_pushare.
_PUSHABLE_SHARED_COLS = (
    "billing_account_id",
    "utility_id",
    "emittente_soggetto_ruolo_id",
    "competenza_dal",
    "competenza_al",
    "fatturazione_immediata",
    "sorgente_tipo_id",
    "sorgente_uid",
    "segment_key",
    "articolo_id",
    "istanza_utility_id",
    "data_attivita",
    "uom_id",
    "quantita",
    "qta_operativa",
    "uom_operativa_id",
    "factor_to_base",
    "competenza_mese",
    "prezzo_snapshot",
    "prezzo_bloccato",
    "pricing_mode",
    "tipo_movimento",
    "tipo_consumo",
    "valuta_id",
    "meta",
    "tipo_doc_fiscale_id",
)


@dataclass(frozen=True)
class CommessaAttivitaInput:
    """Input per fn_upsert_commessa_attivita — tutti i campi della riga operativa.

    Campi obbligatori (senza default) prima; opzionali (con default) dopo.
    I default sono allineati ai DEFAULT della fn_upsert_commessa_attivita.
    """

    # === Campi obbligatori (sempre presenti dalle fn_list) ===
    commessa_id: int
    segment_key: str
    quantita: Decimal
    competenza_mese: date
    articolo_id: Any | None  # UUID dal DB; None per consumi (handler risolve)
    prezzo_snapshot: Decimal | None  # None per consumi (calcolato da listino)

    # === Campi con default — allineati a fn_upsert_commessa_attivita ===
    uom_id: int | None = None  # #3: nullable (handler risolve da catalogo)
    tipo_doc_fiscale_id: int | None = None  # #4: default da config
    valuta_id: int | None = None  # None per consumi/contratti
    prezzo_bloccato: bool = False
    pricing_mode: str = "FIXED"
    prezzo_da_riallineare: bool = False  # #5: default False
    stato_approvazione: str = "BOZZA"  # #10: default BOZZA
    stato_emissione: str = "NON_EMESSA"  # #10: default NON_EMESSA
    tipo_movimento: str = "NORMALE"
    tipo_consumo: str = "CONGUAGLIO"

    # === Campi opzionali ===
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


@dataclass(frozen=True)
class PushableRow:
    """Riga normalizzata da fn_list_*_da_pushare — 25 colonne condivise."""

    billing_account_id: int
    utility_id: int | None
    emittente_soggetto_ruolo_id: int
    competenza_dal: date | None
    competenza_al: date | None
    fatturazione_immediata: bool
    sorgente_tipo_id: int
    sorgente_uid: str
    segment_key: str
    articolo_id: Any  # UUID o None (consumi)
    istanza_utility_id: int | None
    data_attivita: date | None
    uom_id: int | None
    quantita: Decimal | None
    qta_operativa: Decimal | None
    uom_operativa_id: int | None
    factor_to_base: Decimal
    competenza_mese: date
    prezzo_snapshot: Decimal | None
    prezzo_bloccato: bool
    pricing_mode: str
    tipo_movimento: str
    tipo_consumo: str
    valuta_id: int | None
    meta: dict[str, Any]
    tipo_doc_fiscale_id: int | None


def _map_pushable_row(col_map: dict[str, int], row: tuple) -> PushableRow:
    """Scopo: converte una tupla cursor in PushableRow usando la mappa colonne per nome."""
    def _col(name: str) -> Any:
        return row[col_map[name]]

    meta_raw = _col("meta")
    if isinstance(meta_raw, str):
        try:
            meta_raw = json.loads(meta_raw)
        except json.JSONDecodeError:
            meta_raw = {}
    if not isinstance(meta_raw, dict):
        meta_raw = {}

    return PushableRow(
        billing_account_id=_col("billing_account_id"),
        utility_id=_col("utility_id"),
        emittente_soggetto_ruolo_id=_col("emittente_soggetto_ruolo_id"),
        competenza_dal=_col("competenza_dal"),
        competenza_al=_col("competenza_al"),
        fatturazione_immediata=bool(_col("fatturazione_immediata")),
        sorgente_tipo_id=_col("sorgente_tipo_id"),
        sorgente_uid=str(_col("sorgente_uid")),
        segment_key=str(_col("segment_key")),
        articolo_id=_col("articolo_id"),
        istanza_utility_id=_col("istanza_utility_id"),
        data_attivita=_col("data_attivita"),
        uom_id=_col("uom_id"),
        quantita=_col("quantita"),
        qta_operativa=_col("qta_operativa"),
        uom_operativa_id=_col("uom_operativa_id"),
        factor_to_base=_col("factor_to_base") or Decimal(1),
        competenza_mese=_col("competenza_mese"),
        prezzo_snapshot=_col("prezzo_snapshot"),
        prezzo_bloccato=bool(_col("prezzo_bloccato")),
        pricing_mode=str(_col("pricing_mode")),
        tipo_movimento=str(_col("tipo_movimento")),
        tipo_consumo=str(_col("tipo_consumo")),
        valuta_id=_col("valuta_id"),
        meta=meta_raw,
        tipo_doc_fiscale_id=_col("tipo_doc_fiscale_id"),
    )


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

    # --- Gruppo 0: Fetch righe sorgente per push ---

    @staticmethod
    def validate_sorgente_map() -> list[str]:
        """Verifica _SORGENTE_FN_MAP contro config.sorgenti (scope=PUSH_COMMESSA).

        Restituisce lista di warning (vuota = tutto OK).
        Utile come safety-net a startup o nei test di integrazione.
        """
        warnings: list[str] = []
        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT codice FROM config.sorgenti"
                " WHERE scope = 'PUSH_COMMESSA' AND attivo = true"
            )
            db_codici = {row[0] for row in cursor.fetchall()}

        map_codici = set(_SORGENTE_FN_MAP.keys())
        missing = db_codici - map_codici
        extra = map_codici - db_codici
        if missing:
            warnings.append(
                f"Sorgenti PUSH_COMMESSA nel DB ma non in _SORGENTE_FN_MAP: {sorted(missing)}"
            )
        if extra:
            warnings.append(
                f"Codici in _SORGENTE_FN_MAP ma non nel DB (scope PUSH_COMMESSA): {sorted(extra)}"
            )
        return warnings

    # Scopo: invoca la fn_list_<sorgente>_da_pushare parametrizzata e restituisce
    # le righe normalizzate come PushableRow. Unico punto di accesso per tutti gli handler.
    def fetch_pushable_rows(
        self,
        sorgente_codice: str,
        *,
        competenza_mese: date | None = None,
        billing_account_id: int | None = None,
        limit: int | None = None,
    ) -> list[PushableRow]:
        """Chiama fn_list_<sorgente>_da_pushare e restituisce PushableRow normalizzati."""
        fn_name = _SORGENTE_FN_MAP.get(sorgente_codice)
        ErrorManager.require(
            fn_name is not None,
            code="COMMESSE_SORGENTE_SCONOSCIUTA",
            message=f"Sorgente '{sorgente_codice}' non supportata per push",
        )
        assert fn_name is not None

        with connection.cursor() as cursor:
            cursor.execute(
                f"SELECT * FROM {fn_name}(%s, %s, %s)",  # noqa: S608 — fn_name da whitelist
                [competenza_mese, billing_account_id, limit],
            )
            # Costruisce mappa colonna → indice per estrarre solo le 25 condivise.
            col_names = [desc[0] for desc in cursor.description]
            col_map = {name: idx for idx, name in enumerate(col_names) if name in _PUSHABLE_SHARED_COLS}
            rows = cursor.fetchall()

        return [_map_pushable_row(col_map, row) for row in rows]

    # --- Gruppo 1: Commessa ---

    # Scopo: risolve o crea una commessa. Restituisce commessa_id.
    # Default allineati a fn_get_or_create_commessa.
    def get_or_create_commessa(
        self,
        *,
        billing_account_id: int,
        utility_id: int | None = None,
        tipo_commessa: str = "AUTO",
        policy_fatturazione: str = "DA_DOCUMENTO",
        fatturazione_immediata: bool = False,
        priorita_operativa: str = "NORMALE",
        emittente_soggetto_ruolo_id: int | None = None,
        competenza_dal: date | None = None,
        competenza_al: date | None = None,
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

    # Scopo: Restituisce le commesse emittibili nel perimetro del contesto lotto.
    def list_commesse_emittibili(
        self,
        *,
        competenza_mese: date | None = None,
        utility_id: int | None = None,
        billing_account_id: int | None = None,
        emittente_soggetto_ruolo_id: int | None = None,
    ) -> list[int]:
        """Stub: fn DB fn_list_commesse_emittibili non ancora disponibile."""
        return []

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
