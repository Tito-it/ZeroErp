# ------------------------------------------------------------
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Test unitari del service delle ANAGRAFICHE di magazzino — la
#        validazione del payload (chiavi ammesse, obbligatori, tipi), il
#        DELTA del PATCH (solo le chiavi presenti arrivano al repository, il
#        `null` azzera i nullable), i 404 di dominio, la traduzione di un
#        IntegrityError col campo, il contratto letto dal DB (le colonne
#        ammesse: una divergenza coi lettori e' un `RuntimeError`).
#        Repository mockato: CI-safe, nessun DB. La giuntura col database
#        vero, e le liste vere, sono in `tests/db/test_anagrafiche_magazzino_db.py`.
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
9) LottiServiceTests.test_la_nascita_passa_articolo_e_obbligatori_come_argomenti
10) ContrattoServiceTests.test_db_e_lettori_divergenti_sono_un_allarme
11) ContrattoServiceTests.test_ogni_testo_si_ferma_alla_lunghezza_della_sua_colonna
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

# Le colonne ammesse come le dice il DB (`fn_<tabella>_colonne_ammesse`), letto
# il 2026-11-22. ⚠️ Una copia di fixture: la verita' la confronta
# `tests/db/test_anagrafiche_magazzino_db.py` col catalogo vero.
_AMMESSE: dict[tuple[str, str], frozenset[str]] = {
    ("magazzini", "crea"): frozenset({"codice", "descrizione", "indirizzo_dettaglio_id", "predefinito", "meta", "usa_ubicazioni"}),
    ("magazzini", "modifica"): frozenset({"codice", "descrizione", "indirizzo_dettaglio_id", "attivo", "predefinito", "meta", "usa_ubicazioni"}),
    ("ubicazioni", "crea"): frozenset({"codice", "descrizione", "tipo_id", "parent_id", "area", "corsia", "scaffale", "piano", "posizione", "meta"}),
    ("ubicazioni", "modifica"): frozenset({"codice", "descrizione", "tipo_id", "parent_id", "area", "corsia", "scaffale", "piano", "posizione", "attivo", "meta"}),
    ("lotti", "crea"): frozenset({"codice", "data_arrivo", "data_scadenza", "meta"}),
    ("lotti", "modifica"): frozenset({"codice", "data_arrivo", "data_scadenza", "attivo", "meta"}),
}


# Scopo: il repository finto risponde le colonne ammesse come il DB.
def _contratto(repo) -> None:
    repo.return_value.colonne_ammesse.side_effect = lambda tabella, gesto: _AMMESSE[(tabella, gesto)]


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
            _contratto(repo)
            e = _rifiuto(lambda: svc.crea_magazzino({"codice": "A", "emittente_fiscale_id": 1}))
            self.assertEqual(e.code, svc.E_VALIDAZIONE)
            e = _rifiuto(lambda: svc.crea_magazzino({"codice": "A", "descrizione": "d"}))
            self.assertEqual((e.code, e.context.get("field")), (svc.E_VALIDAZIONE, "indirizzo_dettaglio_id"))
            repo.return_value.create_magazzino.assert_not_called()

    # 2. `attivo` non si sceglie alla nascita; l'emittente lo mette il DB.
    def test_crea_non_manda_attivo_ne_emittente(self):
        with patch(_REPO, autospec=True) as repo:
            _contratto(repo)
            repo.return_value.create_magazzino.return_value = 3
            repo.return_value.get_magazzino.return_value = _MAG
            e = _rifiuto(lambda: svc.crea_magazzino({"codice": "A", "descrizione": "d", "indirizzo_dettaglio_id": 4, "attivo": False}))
            self.assertEqual(e.code, svc.E_VALIDAZIONE)
            out = svc.crea_magazzino({"codice": " A ", "descrizione": "d", "indirizzo_dettaglio_id": 4, "predefinito": True})
            self.assertEqual(out, _MAG)
            # Gli obbligatori come argomenti del verbo, il resto nei campi.
            self.assertEqual(repo.return_value.create_magazzino.call_args.kwargs, {
                "codice": "A", "descrizione": "d", "indirizzo_dettaglio_id": 4, "campi": {"predefinito": True},
            })

    # 3.
    def test_aggiorna_manda_solo_il_delta(self):
        with patch(_REPO, autospec=True) as repo:
            _contratto(repo)
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
            _contratto(repo)
            repo.return_value.get_magazzino.return_value = None
            self.assertEqual(_rifiuto(lambda: svc.get_magazzino(99)).code, svc.E_MAGAZZINO_NON_TROVATO)
            self.assertEqual(_rifiuto(lambda: svc.aggiorna_magazzino(99, {"descrizione": "x"})).code, svc.E_MAGAZZINO_NON_TROVATO)
            self.assertEqual(_rifiuto(lambda: svc.list_ubicazioni(99, limit=10)).code, svc.E_MAGAZZINO_NON_TROVATO)
            repo.return_value.list_ubicazioni.assert_not_called()

    # 5.
    def test_duplicato_arriva_col_campo(self):
        with patch(_REPO, autospec=True) as repo:
            _contratto(repo)
            repo.return_value.create_magazzino.side_effect = IntegrityError(
                'duplicate key value violates unique constraint "uq_magazzini_codice"'
            )
            e = _rifiuto(lambda: svc.crea_magazzino({"codice": "A", "descrizione": "d", "indirizzo_dettaglio_id": 4}))
            self.assertEqual((e.code, e.context.get("field")), (svc.E_DUPLICATO, "codice"))


class UbicazioniServiceTests(SimpleTestCase):
    # 6.
    def test_padre_nullo_azzera_e_il_magazzino_si_legge_prima(self):
        with patch(_REPO, autospec=True) as repo:
            _contratto(repo)
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
            _contratto(repo)
            e = _rifiuto(lambda: svc.list_lotti(auth_user_id=7, articolo_id=None, limit=10))
            self.assertEqual((e.code, e.context.get("field")), (svc.E_VALIDAZIONE, "articolo_id"))
            e = _rifiuto(lambda: svc.list_lotti(auth_user_id=7, articolo_id="abc", limit=10))
            self.assertEqual(e.code, svc.E_VALIDAZIONE)
            repo.return_value.list_lotti.assert_not_called()
            repo.return_value.list_lotti.return_value = ([], 0)
            svc.list_lotti(auth_user_id=7, articolo_id=_UUID, limit=10)
            # Il perimetro dell'azienda arriva al repository (il lotto e' dell'azienda).
            kwargs = repo.return_value.list_lotti.call_args.kwargs
            self.assertEqual((kwargs["articolo_id"], kwargs["auth_user_id"]), (_UUID, 7))

    # 8.
    def test_scadenza_nulla_la_toglie(self):
        with patch(_REPO, autospec=True) as repo:
            _contratto(repo)
            repo.return_value.get_lotto.return_value = _LOTTO
            svc.aggiorna_lotto(5, {"data_scadenza": None, "data_arrivo": "2026-09-01"})
            repo.return_value.update_lotto.assert_called_once_with(
                5, {"data_arrivo": date(2026, 9, 1), "data_scadenza": None},
            )
            e = _rifiuto(lambda: svc.aggiorna_lotto(5, {"articolo_id": _UUID}))
            self.assertEqual(e.code, svc.E_VALIDAZIONE)

    # 9. L'articolo e gli obbligatori sono argomenti del verbo; l'azienda non
    #    viaggia (la mette la sessione), e non si puo' mandare.
    def test_la_nascita_passa_articolo_e_obbligatori_come_argomenti(self):
        with patch(_REPO, autospec=True) as repo:
            _contratto(repo)
            repo.return_value.create_lotto.return_value = 5
            repo.return_value.get_lotto.return_value = _LOTTO
            svc.crea_lotto({"articolo_id": _UUID, "codice": " L1 ", "data_arrivo": "2026-09-01", "meta": None})
            call = repo.return_value.create_lotto.call_args
            self.assertEqual(str(call.args[0]), _UUID)
            self.assertEqual(call.kwargs, {"codice": "L1", "data_arrivo": date(2026, 9, 1), "campi": {"meta": {}}})
            e = _rifiuto(lambda: svc.crea_lotto(
                {"articolo_id": _UUID, "codice": "L1", "data_arrivo": "2026-09-01", "emittente_fiscale_id": 1},
            ))
            self.assertEqual(e.code, svc.E_VALIDAZIONE)
            e = _rifiuto(lambda: svc.crea_lotto({"codice": "L1", "data_arrivo": "2026-09-01"}))
            self.assertEqual((e.code, e.context.get("field")), (svc.E_VALIDAZIONE, "articolo_id"))


class ContrattoServiceTests(SimpleTestCase):
    # 10. Il DB ammette una colonna che il backend non sa leggere (o il
    #     contrario): allarme tecnico, mai uno scarto silenzioso del campo.
    def test_db_e_lettori_divergenti_sono_un_allarme(self):
        with patch(_REPO, autospec=True) as repo:
            repo.return_value.colonne_ammesse.side_effect = (
                lambda tabella, gesto: _AMMESSE[(tabella, gesto)] | {"colonna_nuova"}
            )
            repo.return_value.get_magazzino.return_value = _MAG
            with self.assertRaises(RuntimeError):
                svc.aggiorna_magazzino(3, {"descrizione": "x"})
            with self.assertRaises(RuntimeError):
                svc.crea_magazzino({"codice": "A", "descrizione": "d", "indirizzo_dettaglio_id": 4})
            repo.return_value.update_magazzino.assert_not_called()
            repo.return_value.create_magazzino.assert_not_called()

    # 11. Il limite di ogni testo e' quello della SUA colonna: al limite passa,
    #     oltre e' un 400 col campo (non un 22001 del DB), e un codice di
    #     ubicazione o di lotto fino a 64 non e' rifiutato. Il confronto col
    #     catalogo vero e' in `tests/db/test_anagrafiche_magazzino_db.py` (11).
    def test_ogni_testo_si_ferma_alla_lunghezza_della_sua_colonna(self):
        casi = (
            ("magazzino", "codice", 32, lambda p: svc.aggiorna_magazzino(3, p)),
            ("magazzino", "descrizione", 120, lambda p: svc.aggiorna_magazzino(3, p)),
            ("ubicazione", "codice", 64, lambda p: svc.aggiorna_ubicazione(3, 9, p)),
            ("ubicazione", "descrizione", 120, lambda p: svc.aggiorna_ubicazione(3, 9, p)),
            ("ubicazione", "corsia", 32, lambda p: svc.aggiorna_ubicazione(3, 9, p)),
            ("lotto", "codice", 64, lambda p: svc.aggiorna_lotto(5, p)),
        )
        with patch(_REPO, autospec=True) as repo:
            _contratto(repo)
            repo.return_value.get_magazzino.return_value = _MAG
            repo.return_value.get_ubicazione.return_value = _UBI
            repo.return_value.get_lotto.return_value = _LOTTO
            for entita, campo, limite, chiama in casi:
                with self.subTest(entita=entita, campo=campo):
                    chiama({campo: "X" * limite})
                    troppo = {campo: "X" * (limite + 1)}
                    e = _rifiuto(lambda chiama=chiama, troppo=troppo: chiama(troppo))
                    self.assertEqual((e.code, e.context.get("field")), (svc.E_VALIDAZIONE, campo))
