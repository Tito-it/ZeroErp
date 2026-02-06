# ------------------------------------------------------------
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2025 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Orchestrazione per grouping e generazione righe fattura.
# ------------------------------------------------------------


from datetime import date
from decimal import Decimal

from django.db import transaction

from apps.core.services.error_manager import ErrorManager
from apps.vendite.db.pipeline_repository import VenditePipelineRepository
from apps.vendite.types import GroupAttivitaKey

# Servizio applicativo che porta in Python il grouping e la generazione righe fattura.


class FattureRigheService:
    def __init__(self, repository: VenditePipelineRepository | None = None) -> None:
        self.repository = repository or VenditePipelineRepository()

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
        assert row.dest_billing_account_id is not None

        use_competenza = (
            row.competenza_dal is not None
            and row.competenza_al is not None
            and (
                row.competenza_dal != row.competenza_al
                or row.competenza_dal != row.data_attivita
            )
        )

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

        count = 0
        with transaction.atomic():
            for attivita in self.repository.list_attivita_da_fatturare(lotto_id):
                fattura_id = self.repository.get_or_create_fattura_header(lotto_id, attivita.id)
                group_key = self.group_attivita_fatturabili(attivita.id)

                if dry_run:
                    count += 1
                    continue

                riga_nr = self.repository.get_next_fattura_riga_nr(fattura_id)
                fattura_riga_id = self.repository.insert_fattura_riga(
                    fattura_id=fattura_id,
                    riga_nr=riga_nr,
                    articolo_id=attivita.articolo_id,
                    descrizione=attivita.articolo_descrizione,
                    uom_id=group_key["uom_id"],
                    qta=attivita.quantita,
                    prezzo_unitario=attivita.prezzo_unitario,
                    iva_id=group_key["iva_id"],
                    dest_billing_account_id=group_key["dest_billing_account_id"],
                    sorgente_tipo_id=attivita.sorgente_tipo_id,
                    sorgente_uid=attivita.sorgente_uid,
                    sorgente_riga=attivita.sorgente_riga,
                    meta={"group_key": group_key},
                )
                self.repository.mark_attivita_fatturata(attivita.id, fattura_riga_id)
                count += 1
        return count


def _to_float(value: Decimal | None) -> float | None:
    if value is None:
        return None
    return float(value)


def _to_iso(value: date | None) -> str | None:
    if value is None:
        return None
    return value.isoformat()
