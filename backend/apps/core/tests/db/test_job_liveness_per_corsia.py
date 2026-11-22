# ------------------------------------------------------------
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: La CORSIA — la coppia `(processo_codice, jobname)` — come chiave dei
#        lettori del giornale per corsia: `job_liveness`, `list_job_summary`,
#        e il filtro di `list_job_runs`.
# Note: ⭐ Perche' esiste. Il modello non lega un `jobname` a un processo solo
#        (ritocco 1 del §8.8 di brief-db-giornale-corse-indici). Fino al
#        2026-11-22 la liveness si poteva chiedere per soli nomi (il badge dei
#        drainer) e il riepilogo raggruppava per nome: due processi con una
#        corsia dello stesso nome si mescolavano senza errore. Strada (a) di
#        Tid (§11.3): la chiave e' la coppia, ovunque. Il caso si COSTRUISCE
#        (test 7): oggi nessun processo condivide un nome di corsia, e un test
#        che guardasse i dati di oggi sarebbe verde per sottrazione.
#        ⛔ Il processo obbligatorio si prova SENZA database: e' quello che
#        impedisce a una chiamata senza chiave di rispondere la liveness
#        dell'INTERO giornale — un errore che non fallisce, restituisce solo la
#        cosa sbagliata.
#        Fino al 2026-11-22 il file era `test_job_liveness_due_chiavi.py`.
# ------------------------------------------------------------

"""Indice test previsti.

Senza database:
  1. test_senza_processo_si_ferma
  2. test_i_jobnames_restringono_dentro_il_processo
  3. test_senza_jobnames_le_corsie_vengono_dal_giornale_del_processo
  4. test_una_lista_di_jobname_vuota_non_interroga_il_giornale

Su DB provvisto (`ZEROERP_TEST_DB_E2E=1`):
  5. test_la_liveness_per_processo_gira_sul_database_vero
  5-bis. test_la_liveness_per_processo_vede_ogni_corsia
  6. test_una_corsa_aperta_non_e_un_esito_e_la_conclusa_porta_la_sua_data   ⭐ 14-09
  7. test_due_processi_con_una_corsia_dello_stesso_nome_non_si_mescolano    ⭐ 22-11
"""

from __future__ import annotations

import uuid
from unittest import TestCase
from unittest.mock import MagicMock, patch

from django.db import connection, transaction
from django.test import SimpleTestCase

from apps.core.db import maintenance_repository as modulo
from apps.core.db.maintenance_repository import MaintenanceRepository
from apps.core.services.job_run import ORIGINE_COMMAND
from apps.core.services.processi import PROCESSO_DIGEST_PRESIDI, PROCESSO_DRAINA_CODA_LAVORI
from apps.core.tests.db_e2e import richiedi_db_provvisto


def _connessione_finta() -> tuple[MagicMock, MagicMock]:
    cursore = MagicMock()
    cursore.fetchall.return_value = []
    cursore.__enter__ = MagicMock(return_value=cursore)
    cursore.__exit__ = MagicMock(return_value=False)
    finta = MagicMock()
    finta.cursor.return_value = cursore
    return finta, cursore


class JobLivenessGuardTests(SimpleTestCase):
    """La chiave della liveness, senza database."""

    def setUp(self) -> None:
        self.repo = MaintenanceRepository()

    # 1. ⛔ Il processo e' obbligatorio: senza, la query leggerebbe il giornale
    #    intero e risponderebbe la liveness di tutto. Mancante e' un
    #    `TypeError` della firma; vuoto e' un `ValueError`, prima del cursore.
    def test_senza_processo_si_ferma(self) -> None:
        finta = MagicMock()
        with patch.object(modulo, "connection", finta):
            with self.assertRaises(TypeError):
                self.repo.job_liveness(soglia_minuti=10)  # type: ignore[call-arg]
            with self.assertRaises(ValueError):
                self.repo.job_liveness(processo_codice="", soglia_minuti=10)
        finta.cursor.assert_not_called()

    # 2. Con `jobnames` le chiavi sono le corsie dette, DENTRO il processo: la
    #    `LATERAL` cerca per coppia, e nessun nome si cerca da solo.
    def test_i_jobnames_restringono_dentro_il_processo(self) -> None:
        finta, cursore = _connessione_finta()
        with patch.object(modulo, "connection", finta):
            self.repo.job_liveness(
                processo_codice="un_processo", jobnames=["una_corsia"], soglia_minuti=90,
            )
        sql, params = cursore.execute.call_args[0]
        self.assertIn("unnest(%s::text[])", sql)
        self.assertEqual(
            sql.count("WHERE processo_codice = k.processo_codice AND jobname = k.jobname"), 2,
        )
        self.assertNotIn("WHERE jobname = k.jobname", sql)
        self.assertIn("USING (processo_codice, jobname)", sql)
        self.assertEqual(params, ["un_processo", ["una_corsia"], 90])

    # 3. Senza `jobnames` le corsie del processo vengono dal giornale, con la
    #    discesa ricorsiva, poi una `LATERAL … LIMIT 1` per corsia, mai un
    #    `DISTINCT ON` sul giornale.
    def test_senza_jobnames_le_corsie_vengono_dal_giornale_del_processo(self) -> None:
        finta, cursore = _connessione_finta()
        with patch.object(modulo, "connection", finta):
            self.repo.job_liveness(processo_codice="un_processo", soglia_minuti=90)
        sql, params = cursore.execute.call_args[0]
        self.assertNotIn("unnest(%s::text[])", sql)
        self.assertIn("WITH RECURSIVE", sql)
        self.assertNotIn("DISTINCT ON", sql)
        self.assertEqual(sql.count("LIMIT 1"), 2)
        self.assertEqual(
            sql.count("WHERE processo_codice = k.processo_codice AND jobname = k.jobname"), 2,
        )
        # ⚠️ Il processo va due volte nella discesa delle corsie, una nelle
        #    chiavi, poi la soglia: e' l'ordine dei `%s` nel testo, e un
        #    parametro fuori posto qui non fallisce — filtra sulla cosa sbagliata.
        self.assertEqual(params, ["un_processo"] * 3 + [90])

    # 4. Una lista vuota non e' «nessun filtro»: e' «nessuna corsia», e la
    #    risposta e' vuota senza interrogare niente.
    def test_una_lista_di_jobname_vuota_non_interroga_il_giornale(self) -> None:
        finta = MagicMock()
        with patch.object(modulo, "connection", finta):
            self.assertEqual(
                self.repo.job_liveness(processo_codice="p", jobnames=[], soglia_minuti=10), {},
            )
        finta.cursor.assert_not_called()


class JobLivenessSulDatabaseTests(TestCase):
    """La query per processo, contro il database vero (sola lettura)."""

    @classmethod
    def setUpClass(cls) -> None:
        super().setUpClass()
        richiedi_db_provvisto()

    # 5. ⚠️ Non si asserisce su QUANTE corse ci siano — sarebbe una misura sulla
    #    popolazione di oggi, che in CI e' un'altra. Si prova che la query LEGA:
    #    la colonna esiste, il filtro compila, e la forma della risposta e'
    #    quella che il chiamante si aspetta.
    def test_la_liveness_per_processo_gira_sul_database_vero(self) -> None:
        esito = MaintenanceRepository().job_liveness(
            processo_codice=PROCESSO_DIGEST_PRESIDI, soglia_minuti=1440,
        )
        self.assertIsInstance(esito, dict)
        for jobname, corsa in esito.items():
            with self.subTest(jobname=jobname):
                self.assertIn("last_run_at", corsa)
                self.assertIn("attivo", corsa)
                self.assertIn("in_corso", corsa)
                self.assertIn("ultima_conclusa", corsa)
                # ⭐ Il jobname porta la corsia: e' la forma che il battito
                #    ritrova, ed e' il motivo per cui la chiave e' il processo.
                self.assertTrue(jobname.startswith(PROCESSO_DIGEST_PRESIDI))

    # 5-bis. Le corsie di un processo nessuna tabella le elenca: `job_liveness`
    #    le ricava dal giornale con una discesa ricorsiva «salta al jobname
    #    successivo» (2026-11-22). Una discesa che si fermasse al primo passo
    #    risponderebbe una corsia sola, e il test 5 resterebbe verde. Qui le
    #    corsie si COSTRUISCONO — due, sotto lo stesso processo, piu' quelle
    #    vere — e si ritirano: tutte e due devono comparire, con la loro corsa.
    def test_la_liveness_per_processo_vede_ogni_corsia(self) -> None:
        sigla = uuid.uuid4().hex[:8]
        corsie = [f"{PROCESSO_DIGEST_PRESIDI}:test-a-{sigla}", f"{PROCESSO_DIGEST_PRESIDI}:test-b-{sigla}"]
        with transaction.atomic():
            with connection.cursor() as cur:
                for corsia in corsie:
                    cur.execute(
                        "SELECT id FROM script.fn_job_run_start(%s, %s, %s, %s, %s, %s, %s)",
                        [corsia, ORIGINE_COMMAND, "test", None, "test", PROCESSO_DIGEST_PRESIDI, None],
                    )
            esito = MaintenanceRepository().job_liveness(
                processo_codice=PROCESSO_DIGEST_PRESIDI, soglia_minuti=60,
            )
            for corsia in corsie:
                with self.subTest(corsia=corsia):
                    self.assertIn(corsia, esito, "la discesa delle corsie ne ha saltata una")
                    self.assertTrue(esito[corsia]["in_corso"])
            transaction.set_rollback(True)

    # 6. ⛔ `ok` ha TRE facce — true, false, NULL = corsa ancora aperta — e
    #    una corsa aperta NON e' un esito. Fino al 2026-09-14 (mattina) la riga
    #    piu' recente dava l'esito: il digest, componendo la mail dentro la
    #    propria corsa, si chiamava «FALLITA». La correzione della mattina
    #    prese l'esito dall'ultima CONCLUSA — ma lascio' la DATA sulla riga piu'
    #    recente: «09:47:32 (ok)», l'ora della corsa in esecuzione con l'ok di
    #    quella delle 07:30 (nota del team DB, sera). Qui il caso si
    #    COSTRUISCE, con le stesse funzioni con cui il giornale si scrive
    #    davvero (`script.fn_job_run_start/_end`, SECURITY DEFINER), e si
    #    ritira: una corsa chiusa ok = true, poi una corsa APERTA sullo stesso
    #    jobname. Entrambe le sedi — `job_liveness` e `list_job_summary` —
    #    devono dire `in_corso`, la liveness deve vedere la corsa aperta come
    #    segno di vita, e `ultima_conclusa` deve portare l'esito CON LA DATA
    #    DELLA PRIMA corsa — non quella dell'aperta.
    def test_una_corsa_aperta_non_e_un_esito_e_la_conclusa_porta_la_sua_data(self) -> None:
        jobname = "test-liveness-corsa-aperta:" + uuid.uuid4().hex[:8]

        def apri(cur) -> int:
            cur.execute(
                "SELECT id FROM script.fn_job_run_start(%s, %s, %s, %s, %s, %s, %s)",
                [jobname, ORIGINE_COMMAND, "test", None, "test", PROCESSO_DIGEST_PRESIDI, None],
            )
            riga = cur.fetchone()
            assert riga is not None
            return int(riga[0])

        with transaction.atomic():
            with connection.cursor() as cur:
                prima = apri(cur)
                cur.execute(
                    "SELECT script.fn_job_run_end(%s, %s, %s, %s, %s, %s, %s::jsonb, %s)",
                    [prima, True, "conclusa", 0, None, None, None, None],
                )
                seconda = apri(cur)  # resta APERTA: ok NULL, ended_at NULL
                # ⚠️ La premessa si ASSERISCE, non si presume: due righe, una
                #    aperta, e l'aperta e' la PIU' RECENTE (`started_at` e'
                #    `clock_timestamp()`, quindi cresce anche dentro una
                #    transazione) — e' esattamente la riga che il difetto leggeva.
                cur.execute(
                    "SELECT count(*), count(*) FILTER (WHERE ended_at IS NULL), "
                    "       (ARRAY_AGG(ended_at IS NULL ORDER BY started_at DESC))[1] "
                    "  FROM maintenance.job_run_log WHERE jobname = %s",
                    [jobname],
                )
                totale, aperte, recente_aperta = cur.fetchone()
                # Le due date, per confrontarle con cio' che le sedi rispondono.
                cur.execute(
                    "SELECT started_at FROM maintenance.job_run_log WHERE id = %s", [prima],
                )
                avvio_prima = cur.fetchone()[0].isoformat()
                cur.execute(
                    "SELECT started_at FROM maintenance.job_run_log WHERE id = %s", [seconda],
                )
                avvio_seconda = cur.fetchone()[0].isoformat()
            self.assertEqual((totale, aperte), (2, 1), "il caso non e' stato costruito")
            self.assertTrue(recente_aperta, "la riga piu' recente doveva essere quella aperta")
            self.assertNotEqual(avvio_prima, avvio_seconda)

            liveness = MaintenanceRepository().job_liveness(
                processo_codice=PROCESSO_DIGEST_PRESIDI, jobnames=[jobname], soglia_minuti=60,
            )
            corsa = liveness[jobname]
            self.assertTrue(corsa["attivo"], "una corsa aperta e' un segno di vita")
            self.assertTrue(corsa["in_corso"], "la riga piu' recente e' aperta, e va detto")
            self.assertEqual(corsa["last_run_at"], avvio_seconda)
            conclusa = corsa["ultima_conclusa"]
            self.assertIsNotNone(conclusa)
            self.assertIs(conclusa["ok"], True, "la corsa aperta e' stata letta come esito")
            # ⛔ La cucitura: l'esito della prima con la data della seconda.
            self.assertEqual(
                conclusa["started_at"], avvio_prima,
                "l'esito viaggia con la data di un'altra corsa",
            )
            self.assertIsNotNone(conclusa["ended_at"])

            righe, _totale = MaintenanceRepository().list_job_summary(
                processo_codice=PROCESSO_DIGEST_PRESIDI, limit=100, offset=0,
            )
            # Le corsie vere del processo stanno accanto a quella del test:
            # si guarda la propria.
            righe = [r for r in righe if r["jobname"] == jobname]
            self.assertEqual(len(righe), 1)
            self.assertTrue(righe[0]["in_corso"], "la seconda sede non vede la corsa aperta")
            self.assertIs(righe[0]["ultima_conclusa"]["ok"], True)
            self.assertEqual(
                righe[0]["ultima_conclusa"]["started_at"], avvio_prima,
                "la seconda sede ha ancora la cucitura",
            )
            transaction.set_rollback(True)

    # 7. ⭐ Il controesempio della strada (a) (2026-11-22): due processi, una
    #    corsia dello stesso nome. Nel primo la corsa e' APERTA, nel secondo
    #    CONCLUSA e riuscita. Per solo nome la liveness del primo avrebbe preso
    #    l'esito del secondo, e il riepilogo avrebbe sommato le due in una riga.
    #    Si costruisce con le funzioni con cui il giornale si scrive davvero, e
    #    si ritira.
    def test_due_processi_con_una_corsia_dello_stesso_nome_non_si_mescolano(self) -> None:
        nome = "test-corsia-condivisa:" + uuid.uuid4().hex[:8]
        primo, secondo = PROCESSO_DIGEST_PRESIDI, PROCESSO_DRAINA_CODA_LAVORI
        repo = MaintenanceRepository()

        with transaction.atomic():
            with connection.cursor() as cur:
                def apri(processo: str) -> int:
                    cur.execute(
                        "SELECT id FROM script.fn_job_run_start(%s, %s, %s, %s, %s, %s, %s)",
                        [nome, ORIGINE_COMMAND, "test", None, "test", processo, None],
                    )
                    riga = cur.fetchone()
                    assert riga is not None
                    return int(riga[0])

                apri(primo)  # resta APERTA
                chiusa = apri(secondo)
                cur.execute(
                    "SELECT script.fn_job_run_end(%s, %s, %s, %s, %s, %s, %s::jsonb, %s)",
                    [chiusa, True, "conclusa", 0, None, None, None, None],
                )
                # La premessa si ASSERISCE: lo stesso nome, due processi.
                cur.execute(
                    "SELECT count(DISTINCT processo_codice) FROM maintenance.job_run_log"
                    " WHERE jobname = %s",
                    [nome],
                )
                self.assertEqual(cur.fetchone()[0], 2, "il caso non e' stato costruito")

            # La liveness: ogni processo vede la SUA corsa.
            del_primo = repo.job_liveness(
                processo_codice=primo, jobnames=[nome], soglia_minuti=60,
            )[nome]
            self.assertTrue(del_primo["in_corso"])
            self.assertIsNone(
                del_primo["ultima_conclusa"],
                "la conclusa e' dell'altro processo: per solo nome si mescolava",
            )
            del_secondo = repo.job_liveness(
                processo_codice=secondo, jobnames=[nome], soglia_minuti=60,
            )[nome]
            self.assertFalse(del_secondo["in_corso"])
            self.assertIs(del_secondo["ultima_conclusa"]["ok"], True)

            # Il riepilogo senza filtri: DUE righe, una per corsia.
            righe, _ = repo.list_job_summary(limit=200, offset=0)
            righe = {(r["processo_codice"], r["jobname"]): r for r in righe if r["jobname"] == nome}
            self.assertEqual(set(righe), {(primo, nome), (secondo, nome)})
            self.assertEqual(righe[(primo, nome)]["total_runs"], 1)
            self.assertTrue(righe[(primo, nome)]["in_corso"])
            self.assertEqual(righe[(secondo, nome)]["ok_count"], 1)

            # Le corse: per nome tutte e due, ognuna col suo processo; per
            # corsia una sola.
            per_nome, _ = repo.list_job_runs(jobname=nome)
            self.assertEqual({r["processo_codice"] for r in per_nome}, {primo, secondo})
            per_corsia, _ = repo.list_job_runs(processo_codice=primo, jobname=nome)
            self.assertEqual([r["processo_codice"] for r in per_corsia], [primo])
            transaction.set_rollback(True)
