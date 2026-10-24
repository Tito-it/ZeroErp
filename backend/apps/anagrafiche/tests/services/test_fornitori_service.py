# ------------------------------------------------------------
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Test unitari per FornitoriService — creazione, lista,
#        dettaglio, aggiornamento, validazioni.
#        Mock repository, CI-compatible (no DB reale).
# ------------------------------------------------------------

"""
Indice test eseguiti:
 1) test_list_fornitori_ok — happy path lista paginata
 2) test_get_fornitore_ok — dettaglio completo
 3) test_get_fornitore_not_found — id inesistente → E_ANAG_NOT_FOUND
 4) test_crea_fornitore_ok — creazione dalla madre del DB (fn_crea_fornitore)
 5) test_crea_fornitore_con_dati_opzionali — i campi pagamento/fiscale alla madre
 5b) test_crea_fornitore_contatto_inline — VALID ripulito, PARTIAL rifiutato prima di scrivere
 6) test_crea_fornitore_missing_soggetto — soggetto_id mancante → E_ANAG_VALIDAZIONE
 7) test_crea_fornitore_duplicato — IntegrityError UNIQUE ruolo → E_ANAG_DUPLICATO
 7b) test_crea_fornitore_duplicato_codice — UNIQUE codice → messaggio 'codice' (no mascheramento)
 7c) test_crea_fornitore_integrity_non_mappato_rilancia — vincolo non mappato → rilanciato
 8) test_update_fornitore_ok — aggiorna campi editabili
 9) test_update_fornitore_not_found — id inesistente → E_ANAG_NOT_FOUND
 9b) test_update_fornitore_vuoto_e_400 — PATCH vuoto su fornitore esistente → 400, non 404 (2026-10-14)
"""

from unittest import TestCase
from unittest.mock import patch

from django.db import IntegrityError

from apps.core.services.service_errors import ServiceError


FORN_REPO = "apps.anagrafiche.services.fornitori_service.FornitoriRepository"

FAKE_UUID = "019bac81-3f96-7ce8-a086-7e0bd0a2fec1"


# --- Fixture helpers ---

def _fornitore_detail():
    return {
        "id": 1, "uid": "019bac81-0000-0000-0000-000000000001",
        "codice": "FO-001", "attivo": True,
        "soggetto_ruolo_id": 50, "stato_fornitore_id": 2,
        "soggetto_id": FAKE_UUID,
        "ragione_sociale_completa": "Acme Srl",
        "codice_fiscale": "01234567890", "partita_iva": "01234567890",
        "valuta_id": 1, "valuta_iso": "EUR",
        "modalita_pagamento_id": None, "modalita_pagamento_descrizione": None,
        "termine_pagamento_id": None, "termine_pagamento_descrizione": None,
        "giorni_pagamento": 30, "fine_mese": True,
        "split_payment": False, "ritenuta_acconto": False,
        "ritenuta_aliquota": None, "regime_fiscale": "RF01",
        "bollo_esente": False, "canale_fe": "0000000", "pec_email": "acme@pec.it",
        "rating": 80, "qualifica_scadenza": None,
        "stato_codice_interno": "AT", "stato_codice": "AT", "stato_descrizione": "Attivo", "blocca_ordini": False,
        "note": None, "data_insert": "2026-01-01", "data_update": "2026-01-01",
    }


def _base_payload(**overrides):
    payload = {"soggetto_id": FAKE_UUID}
    payload.update(overrides)
    return payload


# =================================================================
# Lista e dettaglio
# =================================================================

class TestFornitoriListDetail(TestCase):

    @patch(FORN_REPO)
    def test_list_fornitori_ok(self, mock_repo):
        """Happy path: lista paginata fornitori."""
        mock_repo.return_value.list_fornitori.return_value = (
            [{"id": 1, "ragione_sociale_completa": "Acme Srl", "codice": "FO-001"}], 1
        )
        from apps.anagrafiche.services.fornitori_service import FornitoriService
        results, total = FornitoriService().list_fornitori()
        self.assertEqual(total, 1)
        self.assertEqual(len(results), 1)

    @patch(FORN_REPO)
    def test_get_fornitore_ok(self, mock_repo):
        """Happy path: dettaglio completo fornitore."""
        mock_repo.return_value.get_fornitore.return_value = _fornitore_detail()
        from apps.anagrafiche.services.fornitori_service import FornitoriService
        result = FornitoriService().get_fornitore(1)
        self.assertEqual(result["codice"], "FO-001")

    @patch(FORN_REPO)
    def test_get_fornitore_not_found(self, mock_repo):
        """Fornitore inesistente → E_ANAG_NOT_FOUND."""
        mock_repo.return_value.get_fornitore.return_value = None
        from apps.anagrafiche.services.fornitori_service import FornitoriService
        with self.assertRaises(ServiceError) as ctx:
            FornitoriService().get_fornitore(999)
        self.assertEqual(ctx.exception.code, "E_ANAG_NOT_FOUND")


# =================================================================
# Creazione
# =================================================================

class TestFornitoriCreazione(TestCase):

    @patch(FORN_REPO)
    def test_crea_fornitore_ok(self, mock_repo):
        """Happy path: creazione fornitore minimale."""
        mock_repo.return_value.crea_fornitore.return_value = (1, 50)
        from apps.anagrafiche.services.fornitori_service import FornitoriService
        result = FornitoriService().crea_fornitore(_base_payload())
        self.assertEqual(result["id"], 1)
        self.assertEqual(result["soggetto_ruolo_id"], 50)

    @patch(FORN_REPO)
    def test_crea_fornitore_con_dati_opzionali(self, mock_repo):
        """Creazione con campi opzionali pagamento/fiscale."""
        mock_repo.return_value.crea_fornitore.return_value = (2, 50)
        from apps.anagrafiche.services.fornitori_service import FornitoriService
        payload = _base_payload(
            valuta_id=1, modalita_pagamento_id=3,
            ritenuta_acconto=True, ritenuta_aliquota=20.0,
            canale_fe="0000000", pec_email="test@pec.it",
        )
        result = FornitoriService().crea_fornitore(payload)
        self.assertEqual(result["id"], 2)
        # La madre riceve i campi opzionali; nessun contatto, nessun indirizzo.
        soggetto, campi, contatto, indirizzi = mock_repo.return_value.crea_fornitore.call_args.args
        self.assertEqual(soggetto, FAKE_UUID)
        self.assertEqual(campi["valuta_id"], 1)
        self.assertTrue(campi["ritenuta_acconto"])
        self.assertIsNone(contatto)
        self.assertEqual(indirizzi, [])

    @patch(FORN_REPO)
    def test_crea_fornitore_contatto_inline(self, mock_repo):
        """Contatto VALIDO → alla madre ripulito; PARTIAL → E_CONTATTO_INCOMPLETO
        prima di scrivere; vuoto → nessun contatto."""
        mock_repo.return_value.crea_fornitore.return_value = (1, 50)
        from apps.anagrafiche.services.fornitori_service import FornitoriService
        FornitoriService().crea_fornitore(_base_payload(
            contatto={"nominativo": " Ufficio ", "tipo_contatto_id": 2, "email": ""},
        ))
        self.assertEqual(
            mock_repo.return_value.crea_fornitore.call_args.args[2],
            {"nominativo": "Ufficio", "tipo_contatto_id": 2},
        )
        mock_repo.return_value.crea_fornitore.reset_mock()
        with self.assertRaises(ServiceError) as ctx:
            FornitoriService().crea_fornitore(_base_payload(contatto={"email": "a@b.it"}))
        self.assertEqual(ctx.exception.code, "E_CONTATTO_INCOMPLETO")
        mock_repo.return_value.crea_fornitore.assert_not_called()

    @patch(FORN_REPO)
    def test_crea_fornitore_missing_soggetto(self, mock_repo):
        """soggetto_id mancante → E_ANAG_VALIDAZIONE."""
        from apps.anagrafiche.services.fornitori_service import FornitoriService
        with self.assertRaises(ServiceError) as ctx:
            FornitoriService().crea_fornitore({})
        self.assertEqual(ctx.exception.code, "E_ANAG_VALIDAZIONE")

    @patch(FORN_REPO)
    def test_crea_fornitore_duplicato(self, mock_repo):
        """IntegrityError UNIQUE ruolo → E_ANAG_DUPLICATO."""
        mock_repo.return_value.crea_fornitore.side_effect = IntegrityError(
            "uq_fornitori_soggetto_ruolo_id"
        )
        from apps.anagrafiche.services.fornitori_service import FornitoriService
        with self.assertRaises(ServiceError) as ctx:
            FornitoriService().crea_fornitore(_base_payload())
        self.assertEqual(ctx.exception.code, "E_ANAG_DUPLICATO")

    @patch(FORN_REPO)
    def test_crea_fornitore_duplicato_codice(self, mock_repo):
        """UNIQUE codice → messaggio specifico 'codice', NON 'soggetto' (no mascheramento)."""
        mock_repo.return_value.crea_fornitore.side_effect = IntegrityError(
            'duplicate key value violates unique constraint "uq_fornitori_codice"'
        )
        from apps.anagrafiche.services.fornitori_service import FornitoriService
        with self.assertRaises(ServiceError) as ctx:
            FornitoriService().crea_fornitore(_base_payload())
        self.assertEqual(ctx.exception.code, "E_ANAG_DUPLICATO")
        self.assertIn("codice", ctx.exception.message)
        self.assertNotIn("soggetto", ctx.exception.message)

    @patch(FORN_REPO)
    def test_crea_fornitore_integrity_non_mappato_rilancia(self, mock_repo):
        """IntegrityError su vincolo non mappato (es. uid) → RILANCIATO, non mascherato."""
        mock_repo.return_value.crea_fornitore.side_effect = IntegrityError(
            'duplicate key value violates unique constraint "uq_fornitori_uid"'
        )
        from apps.anagrafiche.services.fornitori_service import FornitoriService
        with self.assertRaises(IntegrityError):
            FornitoriService().crea_fornitore(_base_payload())


# =================================================================
# Aggiornamento
# =================================================================

class TestFornitoriUpdate(TestCase):

    @patch(FORN_REPO)
    def test_update_fornitore_ok(self, mock_repo):
        """Happy path: aggiorna campi editabili."""
        mock_repo.return_value.get_fornitore.return_value = _fornitore_detail()
        mock_repo.return_value.update_fornitore.return_value = True
        from apps.anagrafiche.services.fornitori_service import FornitoriService
        result = FornitoriService().update_fornitore(1, {"rating": 90})
        self.assertTrue(result["updated"])

    @patch(FORN_REPO)
    def test_update_fornitore_not_found(self, mock_repo):
        """Fornitore inesistente → E_ANAG_NOT_FOUND."""
        mock_repo.return_value.get_fornitore.return_value = None
        from apps.anagrafiche.services.fornitori_service import FornitoriService
        with self.assertRaises(ServiceError) as ctx:
            FornitoriService().update_fornitore(999, {"rating": 90})
        self.assertEqual(ctx.exception.code, "E_ANAG_NOT_FOUND")

    @patch(FORN_REPO)
    def test_update_fornitore_vuoto_e_400(self, mock_repo):
        """⛔ PATCH vuoto su un fornitore che esiste: 400 prima della scrittura.
        Fino al 2026-10-14 il rowcount zero usciva 404 «non trovato»."""
        mock_repo.return_value.get_fornitore.return_value = _fornitore_detail()
        from apps.anagrafiche.services.fornitori_service import FornitoriService
        with self.assertRaises(ServiceError) as ctx:
            FornitoriService().update_fornitore(1, {})
        self.assertEqual(ctx.exception.code, "E_ANAG_VALIDAZIONE")
        mock_repo.return_value.update_fornitore.assert_not_called()


class TestResolveFiltriExportLabel(TestCase):
    """DEF-1: traduzione filtri attivi in label leggibili per header export."""

    @patch(FORN_REPO)
    def test_resolve_filtri_export_label_completo(self, mock_repo):
        """Mapping completo (la ricerca la dichiara `filtri_export_con_ricerca`): stato_fornitore_id."""
        repo = mock_repo.return_value
        repo.get_stato_fornitore_descrizione.return_value = "Attivo"

        from apps.anagrafiche.services.fornitori_service import FornitoriService
        result = FornitoriService().resolve_filtri_export_label(
            stato_fornitore_id=3,
        )

        self.assertEqual(result, {"Stato": "Attivo"})
        repo.get_stato_fornitore_descrizione.assert_called_once_with(3)

    @patch(FORN_REPO)
    def test_resolve_filtri_export_label_fallback_id(self, mock_repo):
        """Lookup descrizione mancante (id obsoleto): fallback 'id=N'."""
        repo = mock_repo.return_value
        repo.get_stato_fornitore_descrizione.return_value = None

        from apps.anagrafiche.services.fornitori_service import FornitoriService
        result = FornitoriService().resolve_filtri_export_label(
            stato_fornitore_id=999,
        )

        self.assertEqual(result, {"Stato": "id=999"})

    @patch(FORN_REPO)
    def test_resolve_filtri_export_label_vuoto(self, mock_repo):
        """Nessun filtro attivo: dict vuoto."""
        from apps.anagrafiche.services.fornitori_service import FornitoriService
        result = FornitoriService().resolve_filtri_export_label()

        self.assertEqual(result, {})
        mock_repo.return_value.get_stato_fornitore_descrizione.assert_not_called()
