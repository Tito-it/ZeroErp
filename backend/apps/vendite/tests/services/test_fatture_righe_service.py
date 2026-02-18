"""
Indice test eseguiti:
1) FattureRigheServiceUnitTests.test_group_attivita_returns_group_key
2) FattureRigheServiceUnitTests.test_group_attivita_requires_id
3) FattureRigheServiceUnitTests.test_generate_fatture_righe_dry_run_counts_only
4) FattureRigheServiceUnitTests.test_generate_fatture_righe_writes_rows
"""

from contextlib import nullcontext
from datetime import date
from decimal import Decimal
from unittest.mock import patch

from django.test import SimpleTestCase

from apps.core.services.service_errors import ServiceError
from apps.vendite.db.pipeline_repository import AttivitaDaFatturare, GroupAttivitaInput
from apps.vendite.services.fatture_righe_service import FattureRigheService


class FattureRigheServiceUnitTests(SimpleTestCase):
    class _RepoMock:
        # Scopo: Inizializza la istanza.
        def __init__(self):
            self.insert_calls = 0
            self.mark_calls = 0

        # Scopo: Recupera `group_attivita_input` dal contesto applicativo o dal database.
        def get_group_attivita_input(self, attivita_id):
            return GroupAttivitaInput(
                attivita_id=attivita_id,
                articolo_id=100,
                dest_billing_account_id=200,
                uom_id=3,
                prezzo_unitario=Decimal("10.50"),
                iva_id=22,
                competenza_dal=date(2026, 1, 1),
                competenza_al=date(2026, 1, 31),
                data_attivita=date(2026, 1, 10),
                visibilita_componenti="solo_padre",
                calcolo_qta_padre="fissa",
                arrotondamento_importi_dec=2,
                arrotondamento_quantita_dec=3,
                metodo_arrotondamento_importi="HALF_UP",
                metodo_arrotondamento_quantita="HALF_UP",
            )

        # Scopo: Restituisce elenco `attivita_da_fatturare` in base ai filtri disponibili.
        def list_attivita_da_fatturare(self, lotto_id):
            return [
                AttivitaDaFatturare(
                    id=11,
                    articolo_id=100,
                    quantita=Decimal("2.0"),
                    prezzo_unitario=Decimal("10.50"),
                    uom_id=3,
                    sorgente_tipo_id=1,
                    sorgente_uid="SRC-1",
                    sorgente_riga=1,
                    articolo_descrizione="Articolo test",
                )
            ]

        # Scopo: Recupera `or_create_fattura_header` dal contesto applicativo o dal database.
        def get_or_create_fattura_header(self, lotto_id, attivita_id):
            return 500

        # Scopo: Recupera `next_fattura_riga_nr` dal contesto applicativo o dal database.
        def get_next_fattura_riga_nr(self, fattura_id):
            return 7

        # Scopo: Gestisce `insert_fattura_riga` nel flusso applicativo del modulo.
        def insert_fattura_riga(self, **kwargs):
            self.insert_calls += 1
            return 900

        # Scopo: Gestisce `mark_attivita_fatturata` nel flusso applicativo del modulo.
        def mark_attivita_fatturata(self, attivita_id, fattura_riga_id):
            self.mark_calls += 1

    # Scopo: Verifica il caso `test_group_attivita_returns_group_key`.
    def test_group_attivita_returns_group_key(self):
        service = FattureRigheService(repository=self._RepoMock())
        result = service.group_attivita_fatturabili(11)
        self.assertEqual(result["articolo_id"], 100)
        self.assertEqual(result["dest_billing_account_id"], 200)
        self.assertEqual(result["competenza_dal"], "2026-01-01")
        self.assertEqual(result["competenza_al"], "2026-01-31")

    # Scopo: Verifica il caso `test_group_attivita_requires_id`.
    def test_group_attivita_requires_id(self):
        service = FattureRigheService(repository=self._RepoMock())
        with self.assertRaises(ServiceError) as exc:
            service.group_attivita_fatturabili(None)  # type: ignore[arg-type]
        self.assertEqual(exc.exception.code, "E_GROUP_ATTIVITA_VALIDATION")

    # Scopo: Verifica il caso `test_generate_fatture_righe_dry_run_counts_only`.
    def test_generate_fatture_righe_dry_run_counts_only(self):
        repo = self._RepoMock()
        service = FattureRigheService(repository=repo)
        with patch(
            "apps.vendite.services.fatture_righe_service.transaction.atomic",
            return_value=nullcontext(),
        ):
            result = service.generate_fatture_righe(99, dry_run=True)
        self.assertEqual(result, 1)
        self.assertEqual(repo.insert_calls, 0)
        self.assertEqual(repo.mark_calls, 0)

    # Scopo: Verifica il caso `test_generate_fatture_righe_writes_rows`.
    def test_generate_fatture_righe_writes_rows(self):
        repo = self._RepoMock()
        service = FattureRigheService(repository=repo)
        with patch(
            "apps.vendite.services.fatture_righe_service.transaction.atomic",
            return_value=nullcontext(),
        ):
            result = service.generate_fatture_righe(99, dry_run=False)
        self.assertEqual(result, 1)
        self.assertEqual(repo.insert_calls, 1)
        self.assertEqual(repo.mark_calls, 1)
