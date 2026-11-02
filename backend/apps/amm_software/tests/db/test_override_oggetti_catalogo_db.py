# ------------------------------------------------------------
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Il catalogo degli oggetti personalizzabili, letto e applicato dal
#        backend sul DB vero (brief-db-be-fe-catalogo-oggetti-permessi
#        §3.1-bis, «Al BE» punti 2 e 3).
#
# ⭐ PERCHE' SUL DB VERO. Il riservato e' una COLONNA del catalogo
#    (`area_model_overrides.riservato`, `20260928-01`) e il rifiuto e' una FK
#    composita (`fk_user_override_oggetti_catalogo`, `20260928-02`). I test
#    dell'API mockano il repository: non vedono ne' il nome della colonna ne'
#    come il 23503 della FK attraversa il service. Un errore qui sarebbe un
#    lookup che dice «personalizzabile» a un oggetto del kernel, o un 500.
#
# ⚠️ CASI COSTRUITI in una transazione SEMPRE annullata: l'operatore se lo
#    fabbrica il test (`dbops.fn_pgtap_crea_emittente_operatore`). L'oggetto
#    fuori catalogo e' `('magazzino', 'causali')`: una chiave del pannello di
#    configurazione, che per la D-2 vale come la sua area e non e' a catalogo
#    per decisione, non per caso.
#
# Indice test (opt-in `ZEROERP_TEST_DB_E2E=1`):
#   1. il lookup legge `riservato` dalla colonna: `can_override` e' la sua
#      negazione, riga per riga
#   2. i permessi effettivi non mostrano gli oggetti riservati
#   3. un override su un oggetto a catalogo e non riservato si scrive
#   4. ⛔ un override che il controllo del service lascia passare (catalogo
#      cambiato fra lettura e scrittura) lo ferma la FK, ed esce come
#      `E_AMM_VALIDAZIONE`, non come 500
#   5. ⛔ lo stesso per un oggetto riservato: la FK rifiuta anche quello
# ------------------------------------------------------------

from __future__ import annotations

from unittest import TestCase
from unittest.mock import patch

from django.db import connection, transaction

from apps.amm_software.db.amm_software_repository import AmmSoftwareRepository
from apps.amm_software.services.amm_software_service import E_AMM_VALIDAZIONE, AmmSoftwareService
from apps.core.services.permissions_resolver import PermissionResolver
from apps.core.services.service_errors import ServiceError
from apps.core.tests.db_e2e import apri_transazione_annullata, richiedi_db_provvisto


class OverrideOggettiCatalogoDbTests(TestCase):

    @classmethod
    def setUpClass(cls) -> None:
        super().setUpClass()
        richiedi_db_provvisto()

    def setUp(self) -> None:
        apri_transazione_annullata(self)
        with connection.cursor() as cur:
            # ⛔ Un OPERATORE UMANO, non l'utente di `fn_pgtap_crea_emittente_operatore`:
            #    quello e' di categoria SISTEMA, e dal 2026-10-20 le rotte
            #    `operatori/{id}/override-*` lo rifiutano (404), come tutte le
            #    `operatori/{id}/`. Il test scriveva override su una credenziale
            #    che un operatore non era — il difetto che la guardia chiude.
            cur.execute("SELECT auth_user_id FROM dbops.fn_pgtap_crea_operatore_umano('override oggetti')")
            self.uid = int(cur.fetchone()[0])
        self.svc = AmmSoftwareService()
        # La cache dei permessi non e' materia di questi test.
        patcher = patch("apps.amm_software.services.amm_software_service.invalidate_user")
        patcher.start()
        self.addCleanup(patcher.stop)

    # Scopo: Le coppie `riservato = t` del catalogo, lette dal DB.
    def _riservati_a_db(self) -> set[tuple[str, str]]:
        with connection.cursor() as cur:
            cur.execute(
                "SELECT app_label, model_name FROM config.area_model_overrides WHERE riservato"
            )
            return {(a, m) for a, m in cur.fetchall()}

    # Scopo: Esegue il PUT del service e ne ritorna il codice del ServiceError.
    def _codice_put(self, items: list[dict]) -> str | None:
        try:
            with transaction.atomic():
                self.svc.put_override_oggetti(self.uid, items)
        except ServiceError as exc:
            return exc.code
        return None

    # 1.
    def test_il_lookup_legge_il_riservato_dalla_colonna(self) -> None:
        righe = AmmSoftwareRepository().list_model_overrides()
        riservati = self._riservati_a_db()
        self.assertTrue(riservati, "il catalogo non dichiara nessun riservato")
        for riga in righe:
            chiave = (riga["app_label"], riga["model_name"])
            with self.subTest(oggetto=chiave):
                self.assertNotIn("riservato", riga)
                self.assertIs(riga["can_override"], chiave not in riservati)
                self.assertEqual(
                    riga["reason"],
                    "amm.model_override_reason_riservato" if chiave in riservati else None,
                )

    # 2.
    def test_i_permessi_effettivi_non_mostrano_i_riservati(self) -> None:
        mappa = PermissionResolver.list_model_overrides_grouped()
        mostrati = {
            (m["app_label"], m["model_name"]) for modelli in mappa.values() for m in modelli
        }
        self.assertTrue(mostrati, "nessun oggetto personalizzabile a catalogo")
        self.assertFalse(mostrati & self._riservati_a_db())

    # 3.
    def test_un_oggetto_a_catalogo_si_personalizza(self) -> None:
        esito = self.svc.put_override_oggetti(self.uid, [
            {"app_label": "anagrafiche", "model_name": "cliente", "livello": "LETTURA"},
        ])
        self.assertEqual(
            [(r["app_label"], r["model_name"], r["livello"]) for r in esito],
            [("anagrafiche", "cliente", "LETTURA")],
        )

    # 4.
    def test_fuori_catalogo_lo_ferma_la_fk_come_validazione(self) -> None:
        catalogo_finto = [{"app_label": "magazzino", "model_name": "causali", "can_override": True}]
        with patch.object(self.svc._repo, "list_model_overrides", return_value=catalogo_finto):
            codice = self._codice_put([
                {"app_label": "magazzino", "model_name": "causali", "livello": "TUTTO"},
            ])
        self.assertEqual(codice, E_AMM_VALIDAZIONE)

    # 5.
    def test_un_riservato_lo_ferma_la_fk_come_validazione(self) -> None:
        catalogo_finto = [
            {"app_label": "config", "model_name": "user_override_oggetti", "can_override": True},
        ]
        with patch.object(self.svc._repo, "list_model_overrides", return_value=catalogo_finto):
            codice = self._codice_put([
                {"app_label": "config", "model_name": "user_override_oggetti", "livello": "TUTTO"},
            ])
        self.assertEqual(codice, E_AMM_VALIDAZIONE)
