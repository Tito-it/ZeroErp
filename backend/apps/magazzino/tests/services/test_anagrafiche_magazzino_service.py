# ------------------------------------------------------------
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Test unitari del service delle ANAGRAFICHE di magazzino — la
#        validazione del payload (chiavi ammesse, obbligatori, tipi), il
#        DELTA del PATCH (solo le chiavi presenti arrivano al repository, il
#        `null` azzera i nullable), i 404 di dominio, la traduzione di un
#        IntegrityError col campo. Repository mockato: CI-safe, nessun DB.
#        La giuntura col database vero e' in `tests/db/test_anagrafiche_magazzino_db.py`.
# ------------------------------------------------------------
"""
Indice test eseguiti:
1) MagazziniServiceTests.test_crea_rifiuta_chiavi_ignote_e_obbligatori_mancanti
2) MagazziniServiceTests.test_crea_non_manda_attivo_ne_emittente
3) MagazziniServiceTests.test_aggiorna_manda_solo_il_delta
4) MagazziniServiceTests.test_dettaglio_assente_e_404_di_dominio
5) MagazziniServiceTests.test_duplicato_arriva_col_campo
6) UbicazioniServiceTests.test_padre_nullo_azzera_e_il_magazzino_si_legge_prima
7) LottiServiceTests.test_articolo_obbligatorio_e_uuid
8) LottiServiceTests.test_scadenza_nulla_la_toglie
"""
from __future__ import annotations

from datetime import date
from unittest.mock import patch

from django.db import IntegrityError
from django.test import SimpleTestCase

from apps.core.services.service_errors import ServiceError
from apps.magazzino.services import anagrafiche_magazzino_service as svc

_REPO = "apps.magazzino.services.anagrafiche_magazzino_service.AnagraficheMagazzinoRepository"
_MAG = {"id": 3, "codice": "A", "descrizione": "d", "attivo": True, "ubicazioni_count": 0}
_UBI = {"id": 9, "magazzino_id": 3, "codice": "U", "parent_id": 1, "attivo": True}
_LOTTO = {"id": 5, "articolo_id": "0190a1b2-0000-7000-8000-000000000001", "codice": "L", "attivo": True}
_UUID = "0190a1b2-0000-7000-8000-000000000001"


# Scopo: cattura il ServiceError di una chiamata che deve fallire.
def _rifiuto(fn) -> ServiceError:
    try:
        fn()
    except ServiceError as e:
        return e
    raise AssertionError("atteso un rifiuto")


class MagazziniServiceTests(SimpleTestCase):
    # 1.
    def test_crea_rifiuta_chiavi_ignote_e_obbligatori_mancanti(self):
        with patch(_REPO, autospec=True) as repo:
            e = _rifiuto(lambda: svc.crea_magazzino({"codice": "A", "emittente_fiscale_id": 1}))
            self.assertEqual(e.code, svc.E_VALIDAZIONE)
            e = _rifiuto(lambda: svc.crea_magazzino({"codice": "A", "descrizione": "d"}))
            self.assertEqual((e.code, e.context.get("field")), (svc.E_VALIDAZIONE, "indirizzo_dettaglio_id"))
            repo.return_value.create_magazzino.assert_not_called()

    # 2. `attivo` non si sceglie alla nascita; l'emittente lo mette il DB.
    def test_crea_non_manda_attivo_ne_emittente(self):
        with patch(_REPO, autospec=True) as repo:
            repo.return_value.create_magazzino.return_value = 3
            repo.return_value.get_magazzino.return_value = _MAG
            e = _rifiuto(lambda: svc.crea_magazzino({"codice": "A", "descrizione": "d", "indirizzo_dettaglio_id": 4, "attivo": False}))
            self.assertEqual(e.code, svc.E_VALIDAZIONE)
            out = svc.crea_magazzino({"codice": " A ", "descrizione": "d", "indirizzo_dettaglio_id": 4, "predefinito": True})
            self.assertEqual(out, _MAG)
            valori = repo.return_value.create_magazzino.call_args.args[0]
            self.assertEqual(valori, {"codice": "A", "descrizione": "d", "indirizzo_dettaglio_id": 4, "predefinito": True})

    # 3.
    def test_aggiorna_manda_solo_il_delta(self):
        with patch(_REPO, autospec=True) as repo:
            repo.return_value.get_magazzino.return_value = _MAG
            svc.aggiorna_magazzino(3, {"descrizione": "nuova", "attivo": False})
            repo.return_value.update_magazzino.assert_called_once_with(3, {"descrizione": "nuova", "attivo": False})
            # Un boolean a `null` in un PATCH non e' un valore.
            e = _rifiuto(lambda: svc.aggiorna_magazzino(3, {"attivo": None}))
            self.assertEqual((e.code, e.context.get("field")), (svc.E_VALIDAZIONE, "attivo"))
            # Payload vuoto: 400, nessuna scrittura (Tid, 2026-10-20, §A2).
            repo.return_value.update_magazzino.reset_mock()
            self.assertEqual(_rifiuto(lambda: svc.aggiorna_magazzino(3, {})).code, svc.E_VALIDAZIONE)
            repo.return_value.update_magazzino.assert_not_called()

    # 4.
    def test_dettaglio_assente_e_404_di_dominio(self):
        with patch(_REPO, autospec=True) as repo:
            repo.return_value.get_magazzino.return_value = None
            self.assertEqual(_rifiuto(lambda: svc.get_magazzino(99)).code, svc.E_MAGAZZINO_NON_TROVATO)
            self.assertEqual(_rifiuto(lambda: svc.aggiorna_magazzino(99, {"descrizione": "x"})).code, svc.E_MAGAZZINO_NON_TROVATO)
            self.assertEqual(_rifiuto(lambda: svc.list_ubicazioni(99, limit=10)).code, svc.E_MAGAZZINO_NON_TROVATO)
            repo.return_value.list_ubicazioni.assert_not_called()

    # 5.
    def test_duplicato_arriva_col_campo(self):
        with patch(_REPO, autospec=True) as repo:
            repo.return_value.create_magazzino.side_effect = IntegrityError(
                'duplicate key value violates unique constraint "uq_magazzini_codice"'
            )
            e = _rifiuto(lambda: svc.crea_magazzino({"codice": "A", "descrizione": "d", "indirizzo_dettaglio_id": 4}))
            self.assertEqual((e.code, e.context.get("field")), (svc.E_DUPLICATO, "codice"))


class UbicazioniServiceTests(SimpleTestCase):
    # 6.
    def test_padre_nullo_azzera_e_il_magazzino_si_legge_prima(self):
        with patch(_REPO, autospec=True) as repo:
            repo.return_value.get_magazzino.return_value = _MAG
            repo.return_value.get_ubicazione.return_value = _UBI
            svc.aggiorna_ubicazione(3, 9, {"parent_id": None, "corsia": "", "descrizione": "x"})
            repo.return_value.update_ubicazione.assert_called_once_with(
                3, 9, {"descrizione": "x", "corsia": None, "parent_id": None},
            )
            # `magazzino_id` non e' una chiave del PATCH.
            e = _rifiuto(lambda: svc.aggiorna_ubicazione(3, 9, {"magazzino_id": 4}))
            self.assertEqual(e.code, svc.E_VALIDAZIONE)
            # Il magazzino si legge PRIMA della figlia: fuori perimetro = 404 del padre.
            repo.return_value.get_magazzino.return_value = None
            self.assertEqual(_rifiuto(lambda: svc.get_ubicazione(3, 9)).code, svc.E_MAGAZZINO_NON_TROVATO)


class LottiServiceTests(SimpleTestCase):
    # 7.
    def test_articolo_obbligatorio_e_uuid(self):
        with patch(_REPO, autospec=True) as repo:
            e = _rifiuto(lambda: svc.list_lotti(articolo_id=None, limit=10))
            self.assertEqual((e.code, e.context.get("field")), (svc.E_VALIDAZIONE, "articolo_id"))
            e = _rifiuto(lambda: svc.list_lotti(articolo_id="abc", limit=10))
            self.assertEqual(e.code, svc.E_VALIDAZIONE)
            repo.return_value.list_lotti.assert_not_called()
            repo.return_value.list_lotti.return_value = ([], 0)
            svc.list_lotti(articolo_id=_UUID, limit=10)
            self.assertEqual(repo.return_value.list_lotti.call_args.kwargs["articolo_id"], _UUID)

    # 8.
    def test_scadenza_nulla_la_toglie(self):
        with patch(_REPO, autospec=True) as repo:
            repo.return_value.get_lotto.return_value = _LOTTO
            svc.aggiorna_lotto(5, {"data_scadenza": None, "data_arrivo": "2026-09-01"})
            repo.return_value.update_lotto.assert_called_once_with(
                5, {"data_arrivo": date(2026, 9, 1), "data_scadenza": None},
            )
            e = _rifiuto(lambda: svc.aggiorna_lotto(5, {"articolo_id": _UUID}))
            self.assertEqual(e.code, svc.E_VALIDAZIONE)
