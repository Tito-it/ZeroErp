# ------------------------------------------------------------
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2025 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Orchestrazione per grouping e generazione righe fattura.
# ------------------------------------------------------------


import json
from datetime import date
from decimal import Decimal

from django.db import transaction

from apps.core.services.error_manager import ErrorManager
from apps.vendite.db.pipeline_repository import GroupAttivitaInput, VenditePipelineRepository
from apps.vendite.types import GroupAttivitaKey

# Servizio applicativo che porta in Python il grouping e la generazione righe fattura.


class FattureRigheService:
    # Scopo: Inizializza la istanza.
    def __init__(self, repository: VenditePipelineRepository | None = None) -> None:
        self.repository = repository or VenditePipelineRepository()

    # Scopo: Gestisce `group_attivita_fatturabili` nel flusso applicativo del modulo.
    def group_attivita_fatturabili(self, attivita_id: int) -> GroupAttivitaKey:
        ErrorManager.require(
            attivita_id is not None,
            code="E_GROUP_ATTIVITA_VALIDATION",
            message="Parametro attivita non valido.",
            detail="attivita_id obbligatorio",
            context={"attivita_id": attivita_id},
            function_name="vendite.fatture_righe_service.group_attivita_fatturabili",
            log_to_db=True,
        )
        assert attivita_id is not None
        row = self.repository.get_group_attivita_input(attivita_id)
        ErrorManager.require(
            row is not None,
            code="E_GROUP_ATTIVITA_NOT_FOUND",
            message="Attivita fatturabile non trovata.",
            detail=f"Attivita non trovata: {attivita_id}",
            context={"attivita_id": attivita_id},
            function_name="vendite.fatture_righe_service.group_attivita_fatturabili",
            log_to_db=True,
        )
        assert row is not None
        ErrorManager.require(
            row.dest_billing_account_id is not None,
            code="E_GROUP_ATTIVITA_INVALID_DATA",
            message="Dati attivita non validi per grouping.",
            detail=f"dest_billing_account_id mancante per attivita: {attivita_id}",
            context={"attivita_id": attivita_id},
            function_name="vendite.fatture_righe_service.group_attivita_fatturabili",
            log_to_db=True,
        )
        return self._build_group_key(row)

    # Scopo: Costruisce GroupAttivitaKey da un GroupAttivitaInput con logica competenza.
    @staticmethod
    def _build_group_key(row: GroupAttivitaInput) -> GroupAttivitaKey:
        use_competenza = (
            row.competenza_dal is not None
            and row.competenza_al is not None
            and (
                row.competenza_dal != row.competenza_al
                or row.competenza_dal != row.data_attivita
            )
        )
        assert row.dest_billing_account_id is not None
        return {
            "articolo_id": row.articolo_id,
            "dest_billing_account_id": int(row.dest_billing_account_id),
            "uom_id": row.uom_id,
            "prezzo_unitario": _to_float(row.prezzo_unitario),
            "iva_id": row.iva_id,
            "competenza_dal": _to_iso(row.competenza_dal) if use_competenza else None,
            "competenza_al": _to_iso(row.competenza_al) if use_competenza else None,
            "visibilita_componenti": row.visibilita_componenti,
            "calcolo_qta_padre": row.calcolo_qta_padre,
            "arrotondamento_importi_dec": row.arrotondamento_importi_dec,
            "arrotondamento_quantita_dec": row.arrotondamento_quantita_dec,
            "metodo_arrotondamento_importi": row.metodo_arrotondamento_importi,
            "metodo_arrotondamento_quantita": row.metodo_arrotondamento_quantita,
        }

    # Scopo: Genera righe fattura per il lotto usando operazioni batch.
    # Riduce i round-trip DB da 5N (per attivita) a 4 totali:
    #   1. batch group inputs   2. batch header creation
    #   3. batch max riga_nrs   4. batch INSERT + UPDATE (CTE)
    def generate_fatture_righe(self, lotto_id: int, *, dry_run: bool = False) -> int:
        ErrorManager.require(
            lotto_id is not None,
            code="E_GENERATE_FATTURE_RIGHE_VALIDATION",
            message="Parametro lotto non valido.",
            detail="lotto_id obbligatorio",
            context={"lotto_id": lotto_id},
            function_name="vendite.fatture_righe_service.generate_fatture_righe",
            log_to_db=True,
        )
        assert lotto_id is not None

        attivita_list = self.repository.list_attivita_da_fatturare(lotto_id)

        # In dry_run si conta solo: nessuna creazione testata, riga o aggiornamento stato.
        if dry_run:
            return len(attivita_list)

        if not attivita_list:
            return 0

        attivita_ids = [a.id for a in attivita_list]
        fn = "vendite.fatture_righe_service.generate_fatture_righe"

        with transaction.atomic():
            # 1. Batch fetch group inputs (1 round-trip).
            group_inputs = self.repository.batch_get_group_attivita_inputs(attivita_ids)

            # Validazione per-attivita sui group inputs.
            group_keys: dict[int, GroupAttivitaKey] = {}
            for aid in attivita_ids:
                gi = group_inputs.get(aid)
                ErrorManager.require(
                    gi is not None,
                    code="E_GROUP_ATTIVITA_NOT_FOUND",
                    message="Attivita fatturabile non trovata.",
                    detail=f"Attivita non trovata: {aid}",
                    context={"attivita_id": aid},
                    function_name=fn,
                    log_to_db=True,
                )
                assert gi is not None
                ErrorManager.require(
                    gi.dest_billing_account_id is not None,
                    code="E_GROUP_ATTIVITA_INVALID_DATA",
                    message="Dati attivita non validi per grouping.",
                    detail=f"dest_billing_account_id mancante per attivita: {aid}",
                    context={"attivita_id": aid},
                    function_name=fn,
                    log_to_db=True,
                )
                group_keys[aid] = self._build_group_key(gi)

            # 2. Batch header creation (1 round-trip, N function calls server-side).
            header_map = self.repository.batch_get_or_create_fattura_headers(
                lotto_id, attivita_ids
            )

            # 3. Batch max riga_nr per fattura (1 round-trip).
            distinct_fattura_ids = list(set(header_map.values()))
            max_riga_nrs = self.repository.get_max_riga_nrs(distinct_fattura_ids)
            riga_nr_counters: dict[int, int] = {
                fid: max_riga_nrs.get(fid, 0) + 1 for fid in distinct_fattura_ids
            }

            # 4. Preparazione array paralleli per batch INSERT + UPDATE.
            b_attivita_ids: list[int] = []
            b_fattura_ids: list[int] = []
            b_riga_nrs: list[int] = []
            b_articolo_ids: list[str] = []  # uuid (catalogo.articoli.id), non int
            b_descrizioni: list[str | None] = []
            b_uom_ids: list[int | None] = []
            b_qtas: list[Decimal | None] = []
            b_prezzi: list[Decimal | None] = []
            b_iva_ids: list[int | None] = []
            b_dest_ba_ids: list[int] = []
            b_sorg_tipo_ids: list[int | None] = []
            b_sorg_uids: list[str | None] = []
            b_sorg_righe: list[int | None] = []
            b_metas: list[str | None] = []

            for attivita in attivita_list:
                fid = header_map[attivita.id]
                gk = group_keys[attivita.id]
                riga_nr = riga_nr_counters[fid]
                riga_nr_counters[fid] = riga_nr + 1

                b_attivita_ids.append(attivita.id)
                b_fattura_ids.append(fid)
                b_riga_nrs.append(riga_nr)
                b_articolo_ids.append(attivita.articolo_id)
                b_descrizioni.append(attivita.articolo_descrizione)
                b_uom_ids.append(gk["uom_id"])
                b_qtas.append(attivita.quantita)
                b_prezzi.append(attivita.prezzo_unitario)
                b_iva_ids.append(gk["iva_id"])
                b_dest_ba_ids.append(gk["dest_billing_account_id"])
                b_sorg_tipo_ids.append(attivita.sorgente_tipo_id)
                b_sorg_uids.append(attivita.sorgente_uid)
                b_sorg_righe.append(attivita.sorgente_riga)
                b_metas.append(json.dumps({"group_key": gk}))

            # 5. Batch INSERT righe + UPDATE attivita (1 round-trip CTE).
            self.repository.batch_insert_righe_and_mark(
                attivita_ids=b_attivita_ids,
                fattura_ids=b_fattura_ids,
                riga_nrs=b_riga_nrs,
                articolo_ids=b_articolo_ids,
                descrizioni=b_descrizioni,
                uom_ids=b_uom_ids,
                qtas=b_qtas,
                prezzi_unitari=b_prezzi,
                iva_ids=b_iva_ids,
                dest_billing_account_ids=b_dest_ba_ids,
                sorgente_tipo_ids=b_sorg_tipo_ids,
                sorgente_uids=b_sorg_uids,
                sorgente_righe=b_sorg_righe,
                metas=b_metas,
            )

        return len(attivita_list)


# Scopo: Gestisce `_to_float` nel flusso applicativo del modulo.
def _to_float(value: Decimal | None) -> float | None:
    if value is None:
        return None
    return float(value)


# Scopo: Gestisce `_to_iso` nel flusso applicativo del modulo.
def _to_iso(value: date | None) -> str | None:
    if value is None:
        return None
    return value.isoformat()
