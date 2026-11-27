# ------------------------------------------------------------
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Le eccezioni utente su aree e azioni scritte dai verbi del DB, sul DB
#        vero (giro 10-quater, brief-db-porte-aperte-dalla-sola-guc §15.7):
#        `config.fn_imposta_override_aree` e `config.fn_imposta_override_azioni`,
#        DEFINER col guard del SUPER_ADMIN, al posto del `DELETE` e degli
#        `INSERT` diretti del repository.
#
# ⭐ PERCHE' SUL DB VERO. I test dell'API mockano il repository: non vedono il
#    nome del verbo, le chiavi che gli arrivano, ne' il permesso che chiede.
#    Un errore qui sarebbe un 500 alla schermata dei permessi, o una data
#    `valido_dal` scritta dove l'amministratore l'aveva lasciata vuota.
#
# ⚠️ CASI COSTRUITI in una transazione SEMPRE annullata: l'operatore e il
#    SUPER_ADMIN se li fabbrica il test. Area e azione sono le prime del
#    catalogo (seed), non dati.
#
# Indice test (opt-in `ZEROERP_TEST_DB_E2E=1`):
#   1. il SUPER_ADMIN sostituisce l'elenco delle aree: `valido_dal` null resta
#      null, e le chiavi in piu' della voce (quelle della GET, che il pannello
#      rimanda) non arrivano al verbo
#   2. lo stesso per le azioni
#   3. ⛔ un operatore che non e' SUPER_ADMIN e' rifiutato dal verbo
#      (`E_PERMESSO_NEGATO`), e niente si scrive
#   4. ⛔ la stessa area due volte: il vincolo `uq_user_override_aree_user_area`
#      attraversa il verbo ed esce `E_AMM_VALIDAZIONE`, non come 500
# ------------------------------------------------------------

from __future__ import annotations

from unittest import TestCase
from unittest.mock import patch

from django.db import connection, transaction

from apps.amm_software.services.amm_software_service import E_AMM_VALIDAZIONE, AmmSoftwareService
from apps.core.services.service_errors import ServiceError
from apps.core.tests.db_e2e import (
    apri_contesto_operatore,
    apri_super_admin_costruito,
    apri_transazione_annullata,
    richiedi_db_provvisto,
)


class OverrideAreeAzioniDbTests(TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        super().setUpClass()
        richiedi_db_provvisto("config.fn_imposta_override_aree(integer, jsonb)")

    def setUp(self) -> None:
        apri_transazione_annullata(self)
        with connection.cursor() as cur:
            # Un OPERATORE UMANO: le rotte `operatori/{id}/` rifiutano gli altri.
            cur.execute("SELECT auth_user_id FROM dbops.fn_pgtap_crea_operatore_umano('override aree azioni')")
            self.uid = int(cur.fetchone()[0])
            cur.execute("SELECT id FROM config.aree_funzionali ORDER BY id LIMIT 1")
            self.area_id = int(cur.fetchone()[0])
            cur.execute("SELECT id FROM config.azioni_processo ORDER BY id LIMIT 1")
            self.azione_id = int(cur.fetchone()[0])
        self.svc = AmmSoftwareService()
        # La cache dei permessi non e' materia di questi test.
        patcher = patch("apps.amm_software.services.amm_software_service.invalidate_user")
        patcher.start()
        self.addCleanup(patcher.stop)

    def _come_super_admin(self) -> None:
        with connection.cursor() as cur:
            apri_super_admin_costruito(cur, etichetta="override aree azioni admin")

    def _codice(self, azione) -> str | None:
        try:
            with transaction.atomic():
                azione()
        except ServiceError as exc:
            return exc.code
        return None

    # 1.
    def test_il_super_admin_sostituisce_le_aree(self) -> None:
        self._come_super_admin()
        esito = self.svc.put_override_aree(self.uid, [{
            "id": 999999, "area_codice": "dalla GET",
            "area_id": self.area_id, "livello": "LETTURA", "motivo": "e2e",
            "valido_dal": None, "valido_al": None,
        }])
        self.assertEqual(
            [(r["area_id"], r["livello"], r["motivo"], r["valido_dal"]) for r in esito],
            [(self.area_id, "LETTURA", "e2e", None)],
        )
        # Sostituire con l'elenco vuoto le toglie.
        self.assertEqual(self.svc.put_override_aree(self.uid, []), [])

    # 2.
    def test_il_super_admin_sostituisce_le_azioni(self) -> None:
        self._come_super_admin()
        esito = self.svc.put_override_azioni(self.uid, [{
            "id": 999999, "permission_codename": "dalla GET",
            "azione_id": self.azione_id, "abilitata": False, "motivo": "e2e",
            "valido_dal": None, "valido_al": None,
        }])
        self.assertEqual(
            [(r["azione_id"], r["abilitata"], r["valido_dal"]) for r in esito],
            [(self.azione_id, False, None)],
        )

    # 3.
    def test_un_operatore_non_scrive_le_eccezioni(self) -> None:
        with connection.cursor() as cur:
            apri_contesto_operatore(cur)
        voce = {"area_id": self.area_id, "livello": "TUTTO"}
        self.assertEqual(self._codice(lambda: self.svc.put_override_aree(self.uid, [voce])), "E_PERMESSO_NEGATO")
        with connection.cursor() as cur:
            cur.execute("SELECT count(*) FROM config.user_override_aree WHERE auth_user_id = %s", [self.uid])
            self.assertEqual(cur.fetchone()[0], 0)

    # 4.
    def test_la_stessa_area_due_volte_e_una_validazione(self) -> None:
        self._come_super_admin()
        voce = {"area_id": self.area_id, "livello": "TUTTO"}
        self.assertEqual(self._codice(lambda: self.svc.put_override_aree(self.uid, [voce, voce])), E_AMM_VALIDAZIONE)
