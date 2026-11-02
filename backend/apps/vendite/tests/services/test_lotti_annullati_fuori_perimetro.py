# ------------------------------------------------------------
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: I lotti ANNULLATI stanno FUORI dal perimetro del registro lotti —
#        lista, chip per stato, calendario dei mesi ed export — e la risposta
#        dichiara quanti ne nasconde (decisione di Tid, 2026-09-12).
#
#        ⭐ PERCHE' UN PRESIDIO. L'annullo di un lotto e' un rollback: cancella
#        le fatture pre-fiscali, rimette le attivita' «da emettere», chiude i
#        task run e lascia un guscio col fiscale ANNULLATA. Ma i chip sono per
#        `stato_lotto` (operativo), che l'annullo di proposito NON tocca (rev
#        2026-09-07): un lotto annullato restava sotto «Errore» o «Completato».
#        Misurato il 2026-09-12 sul database di sviluppo: settembre diceva 35
#        lotti e ne aveva 2 vivi, il chip «Errore» diceva 29 ed erano 16, e un
#        lotto annullato risultava «In esecuzione». Nessun errore, mai — solo
#        numeri che non tornavano con quello che l'operatore trovava aprendo.
#
#        ⛔ Il criterio e' il flag di catalogo `stati_doc_fiscale.is_abortito`,
#        mai `codice_interno = 'ANNULLATA'`; e vive in UNA sede (il costruttore
#        condiviso), tranne il calendario — che ha un perimetro suo (l'anno) e
#        condivide il FRAMMENTO. Il test 3 e' quello che tiene le due sedi
#        insieme.
#
# Note: unita' a mock (nessun DB) + un ramo su DB provvisto che prova il
#       contratto PER INTERO — i tre valori dell'enum — sotto `EXPLAIN`, e la
#       quadratura: mostrati + nascosti = tutti.
# ------------------------------------------------------------
"""Indice test (0..N):

0. test_di_default_gli_annullati_sono_fuori
   Il predicato sull'abortito c'e' nel `WHERE` della lista, e usa il flag di
   catalogo con il `COALESCE` (un lotto senza stato fiscale non e' abortito).

1. test_inclusi_toglie_il_predicato_solo_toglie_il_resto_no
   I tre valori: `inclusi` non filtra, `solo` rovescia la condizione e tiene
   tutto il resto del perimetro (mese, stato, scope). Un valore inventato e'
   un errore, non un elenco vuoto.

2. test_i_chip_seguono_lo_stesso_interruttore
   Il breakdown per stato passa dallo stesso costruttore con lo stesso flag:
   e' cosi' che «Errore 29» torna a essere «Errore 16».

3. test_il_calendario_usa_lo_stesso_frammento_e_la_stessa_join
   `count_lotti_per_mese` non passa dal costruttore (perimetro = anno), ma
   chiede la condizione alla stessa sede della lista (`_condizione_annullati`)
   e la `JOIN` su `sdf` e' la stessa costante (`_LOTTI_JOIN_SDF`): nel suo SQL
   compaiono identici. E con `includi_annullati=True` il frammento sparisce.

4. test_il_conteggio_dei_nascosti_rovescia_la_sola_condizione
   `count_lotti_annullati` passa a `conta_con_perimetro` il `FROM` della lista
   e le condizioni col solo abortito rovesciato — stato compreso: e' «quante
   righe QUESTO filtro lascia fuori».

5. test_l_envelope_dichiara_i_nascosti_e_zero_se_mostrati
   `annullati_count` c'e' sempre; a interruttore acceso vale 0 e non si paga.

6. test_la_view_legge_annullati_e_lo_inoltra_a_lista_export_e_mensile
   `?annullati=true` arriva a `fn_list_lotti`, a `fn_export_lotti` (e finisce
   nell'intestazione del file) e a `fn_lotti_mensile`.

7. test_i_tre_valori_producono_sql_valido_e_i_numeri_quadrano  [DB provvisto]
   `EXPLAIN` su lista e chip per ognuno dei tre valori, sul mensile nei due
   versi; poi mostrati + nascosti = tutti, per lista e calendario.
"""

from __future__ import annotations

import unittest
from datetime import date
from unittest.mock import patch

from django.db import connection, transaction
from django.test import SimpleTestCase

from apps.core.services.fuso_aziendale import oggi_aziendale
from apps.core.tests.db_e2e import apri_contesto_operatore, richiedi_db_provvisto
from apps.vendite.db import vendite_repository as vr
from apps.vendite.db.vendite_repository import VenditeRepository
from apps.vendite.services import vendite_service
from apps.vendite.tests._helpers.mock_cursor import mock_cursor as _mock_cursor

_BASE = {
    "competenza_mese": date(2026, 9, 1),
    "utility_id": None,
    "stato_lotto": None,
    "area_geografica_id": None,
    "tipo_doc_fiscale_id": None,
    "emittente_soggetto_ruolo_id": None,
    "auth_user_id": None,
    "solo_recuperi_mese": False,
}


def _where(**kwargs):
    return VenditeRepository()._lotti_where(**{**_BASE, **kwargs})


# ⚠️ Nei test che leggono l'SQL si patcha il NOME `connection` del modulo, non
#    `connection.cursor`: quel nome e' locale al modulo e `patch` lo ripristina
#    con `setattr`; `.cursor` sta sull'oggetto dietro il proxy di Django, `patch`
#    lo ritiene non locale e all'uscita fa `delattr` — togliendo l'involucro che
#    `SimpleTestCase` mette per vietare il database, e il `tearDownClass` cade.
class LottiAnnullatiPerimetroTests(SimpleTestCase):
    # Scopo: test 0.
    def test_di_default_gli_annullati_sono_fuori(self):
        where, _ = _where()
        self.assertIn(vr._LOTTI_COND_NON_ABORTITO, where)
        self.assertIn("is_abortito", vr._LOTTI_COND_NON_ABORTITO)
        self.assertIn("COALESCE", vr._LOTTI_COND_NON_ABORTITO)
        self.assertNotIn("ANNULLATA", where)

    # Scopo: test 1.
    def test_inclusi_toglie_il_predicato_solo_toglie_il_resto_no(self):
        inclusi, _ = _where(annullati=vr.LOTTI_ANNULLATI_INCLUSI)
        self.assertNotIn("is_abortito", inclusi)
        self.assertIn("fl.competenza_mese = %s", inclusi)

        solo, params = _where(annullati=vr.LOTTI_ANNULLATI_SOLO, stato_lotto="ERRORE")
        self.assertIn(vr._LOTTI_COND_ABORTITO, solo)
        self.assertNotIn(vr._LOTTI_COND_NON_ABORTITO, solo)
        self.assertIn("fl.competenza_mese = %s", solo)
        self.assertIn("fl.stato_lotto = %s", solo)
        self.assertEqual(params, [date(2026, 9, 1), "ERRORE"])

        with self.assertRaises(ValueError):
            _where(annullati="tutti")

    # Scopo: test 2.
    def test_i_chip_seguono_lo_stesso_interruttore(self):
        repo = VenditeRepository()
        with patch("apps.vendite.db.vendite_repository.connection") as conn:
            cur = conn.cursor.return_value = _mock_cursor(fetchall=[("ERRORE", 16)])
            repo.count_lotti_per_stato(competenza_mese=date(2026, 9, 1))
            sql_esclusi = cur.execute.call_args[0][0]
            repo.count_lotti_per_stato(
                competenza_mese=date(2026, 9, 1), includi_annullati=True,
            )
            sql_inclusi = cur.execute.call_args[0][0]
        self.assertIn(vr._LOTTI_COND_NON_ABORTITO, sql_esclusi)
        self.assertNotIn("is_abortito", sql_inclusi)

    # Scopo: test 3 — le due sedi del predicato sono UNA.
    def test_il_calendario_usa_lo_stesso_frammento_e_la_stessa_join(self):
        repo = VenditeRepository()
        with patch("apps.vendite.db.vendite_repository.connection") as conn:
            cur = conn.cursor.return_value = _mock_cursor(fetchall=[(9, 2)])
            repo.count_lotti_per_mese(anno=2026)
            sql_esclusi = cur.execute.call_args[0][0]
            repo.count_lotti_per_mese(anno=2026, includi_annullati=True)
            sql_inclusi = cur.execute.call_args[0][0]
        self.assertIn(vr._LOTTI_COND_NON_ABORTITO, sql_esclusi)
        self.assertIn(vr._LOTTI_JOIN_SDF, sql_esclusi)
        self.assertIn(vr._LOTTI_JOIN_SDF, VenditeRepository._LOTTO_JOINS)
        self.assertNotIn("is_abortito", sql_inclusi)

    # Scopo: test 4.
    def test_il_conteggio_dei_nascosti_rovescia_la_sola_condizione(self):
        with patch(
            "apps.vendite.db.vendite_repository.conta_con_perimetro", return_value=43,
        ) as conta:
            n = VenditeRepository().count_lotti_annullati(
                competenza_mese=date(2026, 9, 1), stato_lotto="ERRORE",
            )
        self.assertEqual(n, 43)
        from_sql, conditions, params = conta.call_args[0]
        self.assertTrue(from_sql.startswith("FROM vendite.fatturazione_lotti fl"))
        self.assertIn("config.stati_doc_fiscale sdf", from_sql)
        self.assertIn(vr._LOTTI_COND_ABORTITO, conditions)
        self.assertNotIn(vr._LOTTI_COND_NON_ABORTITO, conditions)
        self.assertIn("fl.stato_lotto = %s", conditions)
        self.assertEqual(params, [date(2026, 9, 1), "ERRORE"])

    # Scopo: test 5.
    def test_l_envelope_dichiara_i_nascosti_e_zero_se_mostrati(self):
        with (
            patch.object(VenditeRepository, "list_lotti", return_value=([], 2)),
            patch.object(VenditeRepository, "count_lotti_per_stato", return_value={}),
            patch.object(VenditeRepository, "count_lotti_annullati", return_value=33) as conta,
        ):
            nascosti = vendite_service.fn_list_lotti(competenza_mese=date(2026, 9, 1))
            mostrati = vendite_service.fn_list_lotti(
                competenza_mese=date(2026, 9, 1), includi_annullati=True,
            )
        self.assertEqual(nascosti["annullati_count"], 33)
        self.assertEqual(mostrati["annullati_count"], 0)
        # A interruttore acceso il conteggio non si paga: una sola chiamata.
        self.assertEqual(conta.call_count, 1)

    # Scopo: test 6.
    def test_la_view_legge_annullati_e_lo_inoltra_a_lista_export_e_mensile(self):
        from django.test import RequestFactory

        from apps.vendite.api import views

        rf = RequestFactory()
        with (
            patch.object(views, "fn_list_lotti", return_value={"results": []}) as lista,
            patch.object(views, "get_scope_user_id", return_value=None),
        ):
            views.ApiLottiList().get(_drf(rf.get("/x/?annullati=true")))
            views.ApiLottiList().get(_drf(rf.get("/x/")))
        self.assertTrue(lista.call_args_list[0].kwargs["includi_annullati"])
        self.assertFalse(lista.call_args_list[1].kwargs["includi_annullati"])

        with (
            patch.object(views, "fn_export_lotti", return_value=([], 0)) as export,
            patch.object(views, "build_export_response", return_value=None) as build,
            patch.object(views, "get_scope_user_id", return_value=None),
        ):
            views.ApiLottiExportView().get(_drf(rf.get("/x/?annullati=true&formato=csv")))
        self.assertTrue(export.call_args.kwargs["includi_annullati"])
        self.assertEqual(build.call_args.kwargs["filtri_applicati"]["annullati"], "True")

        with (
            patch.object(views, "fn_lotti_mensile", return_value={}) as mensile,
            patch.object(views, "get_scope_user_id", return_value=None),
        ):
            views.ApiLottiMensile().get(_drf(rf.get("/x/?anno=2026&annullati=true")))
        self.assertTrue(mensile.call_args.kwargs["includi_annullati"])


# Scopo: una `Request` DRF con `query_params`, come la vede la view.
def _drf(request):
    from rest_framework.request import Request

    return Request(request)


# ⚠️ `unittest.TestCase`, NON `django.test.TestCase`: il primo test che
#    dichiarasse un database farebbe creare al runner un DB usa-e-getta per
#    TUTTA la suite, vuoto — dove queste tabelle non esistono (AGENTS.md).
class LottiAnnullatiSulDatabaseTests(unittest.TestCase):
    """Il contratto per intero, sul database vero (opt-in ZEROERP_TEST_DB_E2E)."""

    @classmethod
    def setUpClass(cls) -> None:
        super().setUpClass()
        richiedi_db_provvisto()

    # Scopo: test 7 — ogni valore dell'enum e' SQL valido, e i numeri quadrano.
    def test_i_tre_valori_producono_sql_valido_e_i_numeri_quadrano(self):
        repo = VenditeRepository()
        with transaction.atomic():
            with connection.cursor() as cur:
                uid = apri_contesto_operatore(cur)
                for val in (
                    vr.LOTTI_ANNULLATI_ESCLUSI, vr.LOTTI_ANNULLATI_INCLUSI, vr.LOTTI_ANNULLATI_SOLO,
                ):
                    where, params = repo._lotti_where(
                        **{**_BASE, "auth_user_id": uid, "annullati": val}
                    )
                    cur.execute(
                        f"EXPLAIN SELECT {repo._LOTTO_SELECT_COLS} "
                        f"FROM vendite.fatturazione_lotti fl {repo._LOTTO_JOINS} {where} "
                        "ORDER BY fl.data_insert DESC, fl.id DESC LIMIT 1",
                        params,
                    )
                    cur.execute(
                        "EXPLAIN SELECT fl.stato_lotto, COUNT(*) "
                        f"FROM vendite.fatturazione_lotti fl {repo._LOTTO_JOINS} {where} "
                        "GROUP BY 1",
                        params,
                    )
            comuni = {k: v for k, v in _BASE.items() if k != "competenza_mese"}
            comuni["auth_user_id"] = uid
            _, tutti = repo.list_lotti(
                competenza_mese=None, **comuni, limit=1, offset=0, includi_annullati=True,
            )
            _, vivi = repo.list_lotti(competenza_mese=None, **comuni, limit=1, offset=0)
            nascosti = repo.count_lotti_annullati(competenza_mese=None, auth_user_id=uid)
            self.assertEqual(tutti - vivi, nascosti)
            anno = oggi_aziendale().year
            mese_tutti = repo.count_lotti_per_mese(
                anno=anno, auth_user_id=uid, includi_annullati=True,
            )
            mese_vivi = repo.count_lotti_per_mese(anno=anno, auth_user_id=uid)
            for mese, n in mese_tutti.items():
                self.assertGreaterEqual(n, mese_vivi.get(mese, 0))
            transaction.set_rollback(True)
