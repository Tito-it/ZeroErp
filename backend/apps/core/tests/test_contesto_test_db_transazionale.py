# ------------------------------------------------------------
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Il contesto dei test sul DB vero si apre per la sola transazione
#        (brief-be-accessi-credenziale-e-vesti §4, 2026-11-27):
#        - il BB `esegui_fixture` (`apps/core/tests/db_e2e.py`) esegue i passi
#          in fila e apre il contesto di un `ContestoSu` col BB
#          `apri_contesto_su`, senza DB (cursore finto);
#        - il PRESIDIO sui sorgenti: nessun test Django, e nessuno smoke
#          Python di `backend/scripts/tests/` (dal 2026-11-27), chiama
#          `script.fn_pgtap_set_contesto_operatore`.
# Note: ⛔ Perche' il presidio. Quella funzione scrive le GUC per la SESSIONE
#       (`set_config(…, false)`), giusto nei pgTAP, dove ogni file ha la sua.
#       Nei test Django la connessione e' condivisa: chiamata fuori da una
#       transazione, il contesto resta sulla connessione e il test dopo gira
#       con l'utente del test prima. Dentro un `atomic` annullato invece la GUC
#       si annulla (provato il 2026-11-27): il rischio e' la chiamata fuori
#       transazione, che `apri_contesto_su` rifiuta e la funzione no.
#       ⚠️ Il presidio legge i sorgenti SENZA i commenti: la prosa che spiega
#       il divieto nomina la funzione, e non deve accenderlo.
#
# Indice test eseguiti (senza DB):
# 1) EseguiFixtureTests.test_i_passi_si_eseguono_in_fila_coi_parametri
# 2) EseguiFixtureTests.test_contesto_su_apre_il_contesto_sull_utente_del_mondo
# 3) EseguiFixtureTests.test_contesto_su_vuole_una_riga
# 4) EseguiFixtureTests.test_contesto_su_rifiuta_un_nome_che_non_e_una_tabella
# 5) EseguiFixtureTests.test_contesto_su_fuori_transazione_fallisce
# 6) NessunContestoDiSessioneNeiTestTests.test_nessun_test_django_chiama_il_contesto_di_sessione
# ------------------------------------------------------------

from __future__ import annotations

from unittest.mock import MagicMock, call, patch

from django.test import SimpleTestCase

from apps.core.tests._repo import repo_root, sorgente_senza_commenti
from apps.core.tests.db_e2e import ContestoSu, esegui_fixture

_FUNZIONE_DI_SESSIONE = "fn_pgtap_set_contesto_operatore"


@patch("django.db.connection", MagicMock(in_atomic_block=True))
class EseguiFixtureTests(SimpleTestCase):
    # 1. Le stringhe si eseguono in fila; coi parametri, ognuna li riceve.
    def test_i_passi_si_eseguono_in_fila_coi_parametri(self) -> None:
        cur = MagicMock()
        esegui_fixture(cur, ("SELECT 1", "SELECT %(sfx)s"), {"sfx": "x"})
        self.assertEqual(
            cur.execute.call_args_list,
            [call("SELECT 1", {"sfx": "x"}), call("SELECT %(sfx)s", {"sfx": "x"})],
        )
        cur = MagicMock()
        esegui_fixture(cur, ("SELECT 1",))
        self.assertEqual(cur.execute.call_args_list, [call("SELECT 1")])

    # 2. `ContestoSu` legge l'utente dalla tabella del mondo e apre le due GUC
    #    con `SET LOCAL`; i passi dopo vengono dopo.
    def test_contesto_su_apre_il_contesto_sull_utente_del_mondo(self) -> None:
        cur = MagicMock()
        cur.fetchall.return_value = [(42,)]
        esegui_fixture(cur, ("CREATE TEMP TABLE _m AS SELECT 42 AS auth_user_id", ContestoSu("_m"), "SELECT 2"))
        sql = [c.args[0] for c in cur.execute.call_args_list]
        self.assertEqual(sql[1], "SELECT auth_user_id FROM _m")
        self.assertTrue(sql[2].startswith("SET LOCAL app.ruolo_applicativo"), sql)
        self.assertTrue(sql[3].startswith("SET LOCAL app.current_user_id"), sql)
        self.assertEqual(cur.execute.call_args_list[3].args[1], ["42"])
        self.assertEqual(sql[4], "SELECT 2")

    # 3. ⛔ Zero o piu' righe: un mondo costruito male, non un utente a caso.
    def test_contesto_su_vuole_una_riga(self) -> None:
        for righe in ([], [(1,), (2,)]):
            with self.subTest(righe=righe):
                cur = MagicMock()
                cur.fetchall.return_value = righe
                with self.assertRaises(AssertionError):
                    esegui_fixture(cur, (ContestoSu("_mondo"),))
                self.assertFalse(any("SET LOCAL" in c.args[0] for c in cur.execute.call_args_list))

    # 4. Il nome finisce nel testo della query: solo un identificatore.
    def test_contesto_su_rifiuta_un_nome_che_non_e_una_tabella(self) -> None:
        cur = MagicMock()
        with self.assertRaises(AssertionError):
            esegui_fixture(cur, (ContestoSu("_mondo; DROP TABLE x"),))
        cur.execute.assert_not_called()

    # 5. Fuori da una transazione il contesto non si apre (`apri_contesto_su`).
    def test_contesto_su_fuori_transazione_fallisce(self) -> None:
        cur = MagicMock()
        cur.fetchall.return_value = [(42,)]
        with patch("django.db.connection", MagicMock(in_atomic_block=False)), \
                self.assertRaises(AssertionError):
            esegui_fixture(cur, (ContestoSu("_mondo"),))
        self.assertFalse(any("SET LOCAL" in c.args[0] for c in cur.execute.call_args_list))


class NessunContestoDiSessioneNeiTestTests(SimpleTestCase):
    # 6. ⛔ Nessun file di test Django chiama la funzione del contesto di
    #    sessione: il contesto passa da `apri_contesto_su` o da `ContestoSu`.
    #    ⭐ Dal 2026-11-27 (ok di Tid) anche gli smoke Python in-process
    #    (`backend/scripts/tests/`): girano in una transazione annullata, e il
    #    contesto si apre coi BB di `db_e2e` come nei test.
    def test_nessun_test_django_chiama_il_contesto_di_sessione(self) -> None:
        backend_dir = repo_root() / "backend"
        apps_dir = backend_dir / "apps"
        smoke_dir = backend_dir / "scripts" / "tests"
        test_django = [p for p in apps_dir.rglob("*.py") if "tests" in p.parts]
        smoke = list(smoke_dir.rglob("*.py"))
        # ⛔ Contro il verde per sottrazione: un percorso sbagliato troverebbe
        #    zero file e il presidio passerebbe a vuoto.
        self.assertGreater(len(test_django), 100, f"pochi file di test sotto {apps_dir}")
        self.assertGreater(len(smoke), 10, f"pochi smoke sotto {smoke_dir}")
        colpevoli = sorted(
            str(p.relative_to(backend_dir))
            for p in test_django + smoke
            if p.name != "test_contesto_test_db_transazionale.py"
            and _FUNZIONE_DI_SESSIONE in sorgente_senza_commenti(p.read_text(encoding="utf-8"))
        )
        self.assertEqual(
            colpevoli, [],
            f"chiamano `{_FUNZIONE_DI_SESSIONE}` (GUC di sessione): usate `apri_contesto_su` "
            "o un passo `ContestoSu` di `esegui_fixture` (apps/core/tests/db_e2e.py)",
        )
