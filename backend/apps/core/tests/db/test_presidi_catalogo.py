# ------------------------------------------------------------
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: IL CANCELLO FRA IL CATALOGO DEI PRESIDI E IL BACKEND — i tre vocabolari
#        specchiati in `apps.core.db.presidi_repository` devono seguire i `CHECK`
#        di `dbops.presidi`, e il debito delle viste ancora da iscrivere deve
#        calare.
# Note: ⚠️ RICHIEDE IL DB VERO, opt-in `ZEROERP_TEST_DB_E2E=1` (accesa in CI): il
#        catalogo vive nel database. NON SCRIVE NULLA.
#        ⭐ Perche' i mirror sono presidiati e non «tenuti allineati a mano»: un
#        valore in meno qui non fa fallire niente — fa sparire un presidio da un
#        elenco. Il digest smetterebbe di guardare una natura nuova, e il modo
#        in cui te ne accorgi e' il guasto che non ti hanno riferito.
# ------------------------------------------------------------

"""Indice test previsti (opt-in `ZEROERP_TEST_DB_E2E=1`).

1. test_i_mirror_delle_nature_seguono_il_check
2. test_i_mirror_delle_cadenze_seguono_il_check
3. test_i_mirror_dei_perimetri_seguono_il_check
4. test_il_catalogo_si_legge_e_ogni_riga_ha_il_suo_vocabolario
5. test_una_cadenza_del_digest_non_porta_mai_un_inventario_o_un_cancello
     ⭐ Il filtro del digest e' la CADENZA, non un elenco di nature: qui si prova
     che il `CHECK chk_presidi_fuori_digest_cadenza_mai` regge quella scelta.
5-bis. test_ogni_cadenza_del_catalogo_tranne_mai_e_guardata_dal_digest
     ⭐ Il verso opposto: una cadenza nuova a catalogo deve finire in una corsa,
     o le sue viste escono dal digest in silenzio.
6. test_ogni_vista_a_catalogo_esiste_davvero
7. test_il_debito_delle_viste_in_attesa_e_rientrato
     Il verso che chiude il debito: quando il team DB iscrive la vista, questo
     diventa rosso e dice di cancellare la riga dal backend.
     ⚠️ Dal 2026-09-10 `_IN_ATTESA_DI_CATALOGO` e' VUOTA — il debito e' in pari,
     quindi questo test oggi gira a vuoto. E' la condizione giusta, non una
     copertura che manca: si riaccende da se' alla prossima vista in attesa.
8. test_i_mirror_di_chi_agisce_seguono_il_check
9. test_ogni_presidio_che_si_accende_arriva_col_testo_per_chi_agisce
     ⭐ 2026-10-06: il join su `dbops.presidi_testi` GIRA sul database vero e
     porta il testo. La completezza del catalogo la garantisce il pgTAP
     `dbops/test-presidi-testi-v1`; qui si prova il TRASPORTO fino al Python.
9-bis. test_il_testo_del_presidio_e_quello_senza_variante
     ⛔ 2026-10-09: dove il catalogo dichiara `colonna_variante` la stessa
     (vista, lingua) porta anche i testi per causa; il testo del presidio e'
     quello con `variante IS NULL`.
9-ter. test_ogni_causa_arriva_col_suo_testo
     ⭐ 2026-10-10: `testi_delle_cause` gira sul database vero e porta, per
     ogni causa del catalogo, chi agisce e il testo.
9-quater. test_il_conteggio_per_causa_si_legge_come_tabella
     ⭐ 2026-10-10 (R-2): `conta_per_variante` gira sul database vero e consegna
     coppie (variante, conteggio), con varianti che il catalogo delle cause
     conosce. Che la somma sia `fn_conta_presidio` lo garantisce il DB per
     costruzione (pgTAP `test-conta-presidio-per-variante-v1` 9): qui si prova
     il TRASPORTO — letta come `SELECT fn(…)` la tupla arriverebbe in un campo.
10. test_una_lingua_senza_testo_ripiega_su_it
"""

from __future__ import annotations

from unittest import TestCase

from django.db import connection

from apps.core.db.presidi_repository import (
    _IN_ATTESA_DI_CATALOGO,
    CADENZA_MAI,
    CADENZE,
    CHI_AGISCE,
    NATURA_CANCELLO,
    NATURA_INVENTARIO,
    NATURE,
    PERIMETRI,
    PresidiRepository,
)
from apps.core.middleware.user_language_middleware import (
    DEFAULT_LANGUAGE as LINGUA_DEFAULT,
    GUC_NAME,
)
from apps.core.services.presidi_digest import CADENZE_DEL_DIGEST
from apps.core.tests.db_e2e import richiedi_db_provvisto, valori_check


class PresidiCatalogoGuardrail(TestCase):
    """I mirror del backend contro i CHECK del catalogo."""

    @classmethod
    def setUpClass(cls) -> None:
        super().setUpClass()
        richiedi_db_provvisto()
        # ⚠️ Schema presente e tabella assente NON e' una condizione d'ambiente:
        #    e' un difetto, e si fallisce invece di saltare (`db_e2e` §uso).
        cls.repo = PresidiRepository()
        cls.catalogo = cls.repo.list_catalogo()

    # 1-3. I tre vocabolari, letti dal loro `CHECK`. ⛔ Il confronto e' di
    #      UGUAGLIANZA e non di inclusione: un valore in piu' nel backend e' un
    #      elenco che nomina una natura che il database non ammette — cioe' un
    #      ramo che non si accendera' mai, e che sembra coperto.
    def test_i_mirror_delle_nature_seguono_il_check(self) -> None:
        self.assertEqual(
            set(NATURE), valori_check("dbops.presidi", "chk_presidi_natura"),
            "il vocabolario delle nature nel backend non segue il CHECK del "
            "catalogo: una natura nuova non finirebbe in nessun elenco del "
            "digest, in silenzio.",
        )

    def test_i_mirror_delle_cadenze_seguono_il_check(self) -> None:
        self.assertEqual(
            set(CADENZE), valori_check("dbops.presidi", "chk_presidi_cadenza"),
            "il vocabolario delle cadenze nel backend non segue il CHECK: una "
            "cadenza nuova a catalogo non verrebbe guardata da nessuna corsa.",
        )

    def test_i_mirror_dei_perimetri_seguono_il_check(self) -> None:
        self.assertEqual(
            set(PERIMETRI), valori_check("dbops.presidi", "chk_presidi_perimetro"),
            "il vocabolario dei perimetri nel backend non segue il CHECK: e' il "
            "campo che decide se le righe si possono ELENCARE.",
        )

    # 4. Il catalogo si legge e ogni riga porta valori del vocabolario. ⚠️ La
    #    prima asserzione protegge le altre: su un catalogo vuoto il ciclo non
    #    verificherebbe niente e il test sarebbe verde per sottrazione.
    def test_il_catalogo_si_legge_e_ogni_riga_ha_il_suo_vocabolario(self) -> None:
        self.assertTrue(
            self.catalogo,
            "dbops.presidi non ha righe attive: il digest non guarderebbe "
            "niente e ogni confronto qui sotto passerebbe a vuoto.",
        )
        for riga in self.catalogo:
            with self.subTest(vista=riga["vista"]):
                self.assertIn(riga["natura"], NATURE)
                self.assertIn(riga["cadenza"], CADENZE)
                self.assertIn(riga["perimetro"], PERIMETRI)
                # ⛔ La `nota` e' il MOTIVO, ed e' NOT NULL a database: se
                #    arrivasse vuota qui, il digest mostrerebbe una riga senza
                #    dire perche' e' li'.
                self.assertTrue((riga["nota"] or "").strip())

    # 5. ⭐ IL FILTRO DEL DIGEST E' LA CADENZA. Il backend non tiene un elenco di
    #    nature da escludere perche' il `CHECK chk_presidi_fuori_digest_cadenza_mai`
    #    lo garantisce a database. Questo test prova quella dipendenza: se il
    #    CHECK cambiasse, il digest comincerebbe a spedire inventari da duemila
    #    righe — e sarebbe il difetto che il cantiere esiste per evitare.
    def test_una_cadenza_del_digest_non_porta_mai_un_inventario_o_un_cancello(self) -> None:
        # ⚠️ Le cadenze del digest si CHIEDONO al digest e non si riscrivono:
        #    una cadenza nuova deve entrare in questo confronto da se', o il
        #    test coprirebbe le sole due di oggi.
        del_digest = self.repo.list_catalogo(cadenze=CADENZE_DEL_DIGEST)
        self.assertTrue(del_digest, "nessuna riga da guardare a nessuna cadenza")
        fuori_posto = sorted(
            f"{r['vista']} ({r['natura']}, {r['cadenza']})"
            for r in del_digest
            if r["natura"] in (NATURA_INVENTARIO, NATURA_CANCELLO)
        )
        self.assertEqual(
            fuori_posto, [],
            "un INVENTARIO o un CANCELLO ha una cadenza diversa da MAI: "
            "finirebbe nel digest, che e' esattamente il rumore per cui il "
            "digest verrebbe ignorato al secondo invio.",
        )
        # E il verso opposto: cio' che ha cadenza MAI non e' nell'elenco del digest.
        con_mai = [r for r in self.catalogo if r["cadenza"] == CADENZA_MAI]
        self.assertTrue(con_mai, "nessuna riga con cadenza MAI: confronto a vuoto")
        nomi_digest = {r["vista"] for r in del_digest}
        self.assertEqual(
            sorted(r["vista"] for r in con_mai if r["vista"] in nomi_digest), [],
        )

    # 5-bis. ⭐ LE CADENZE DEL DIGEST SONO TUTTE QUELLE DEL CATALOGO TRANNE
    #        `MAI`. Non e' una tautologia sulla derivazione in Python: e' la
    #        prova che il vocabolario da cui si deriva e' quello VERO del
    #        database. Se il catalogo ne ammettesse una nuova, deve finire in una
    #        corsa — o le sue viste uscirebbero dal digest in silenzio.
    def test_ogni_cadenza_del_catalogo_tranne_mai_e_guardata_dal_digest(self) -> None:
        dal_database = valori_check("dbops.presidi", "chk_presidi_cadenza")
        self.assertEqual(
            set(CADENZE_DEL_DIGEST), dal_database - {CADENZA_MAI},
            "una cadenza ammessa dal catalogo non e' guardata da nessuna corsa "
            "del digest: le sue viste uscirebbero dal digest senza che niente "
            "fallisca.",
        )

    # 6. Una riga di catalogo che nomina una vista sparita e' un difetto da
    #    DIRE. Il lettore non esplode (un digest che muore su una riga stantia
    #    smette di riferire tutte le altre): e' questo test a farlo vedere.
    def test_ogni_vista_a_catalogo_esiste_davvero(self) -> None:
        fantasmi = sorted(r["vista"] for r in self.catalogo if not r["esiste"])
        self.assertEqual(
            fantasmi, [],
            "righe di catalogo che nominano una vista inesistente: il digest le "
            "riporta come «non lette», ma la riga va tolta dal catalogo o la "
            "vista ricreata.",
        )

    # 7. ⭐ IL DEBITO CHE DEVE CALARE. `_IN_ATTESA_DI_CATALOGO` tiene il posto
    #    alle viste gia' decise e non ancora iscritte (brief §8.4). Il giorno in
    #    cui il team DB applica la riga, questo test diventa rosso: e' il segnale
    #    che la copia nel backend va cancellata, non un incidente.
    # ⭐ E' successo davvero il 2026-09-10 con `maintenance.vw_job_run_da_guardare`
    #    (brief §10.2): il test si e' acceso, ha nominato la riga, la riga e'
    #    stata tolta. Da allora il registro e' A ZERO e questo confronto gira a
    #    VUOTO — che e' l'esito corretto di un debito pagato.
    # ⛔ Non si aggiunge un'asserzione «la tupla dev'essere vuota»: renderebbe
    #    rosso il prossimo debito legittimo, cioe' punirebbe l'uso corretto del
    #    meccanismo. Qui si presidia il RIENTRO, non l'assenza.
    def test_il_debito_delle_viste_in_attesa_e_rientrato(self) -> None:
        a_catalogo = {r["vista"] for r in self.catalogo if r["a_catalogo"]}
        rientrate = sorted(
            r["vista"] for r in _IN_ATTESA_DI_CATALOGO if r["vista"] in a_catalogo
        )
        self.assertEqual(
            rientrate, [],
            "queste viste sono ORA a catalogo: togliere la riga corrispondente "
            "da `_IN_ATTESA_DI_CATALOGO` in apps/core/db/presidi_repository.py "
            f"— il debito e' pagato ({rientrate}).",
        )

    # 8. Il quarto vocabolario: chi spegne il presidio. ⭐ Il suo ordine decide
    #    i gruppi del digest, ma il confronto col CHECK e' sull'insieme.
    def test_i_mirror_di_chi_agisce_seguono_il_check(self) -> None:
        self.assertEqual(
            set(CHI_AGISCE), valori_check("dbops.presidi", "chk_presidi_chi_agisce"),
            "il vocabolario di chi agisce nel backend non segue il CHECK: un "
            "valore nuovo finirebbe nel gruppo «senza indicazione» del digest e "
            "senza badge nel pannello.",
        )

    # 9. ⭐ IL TRASPORTO DEL TESTO. Il modello dice che un presidio che si
    #    accende (non INVENTARIO) ha chi agisce (`chk_presidi_chi_agisce_se_allarma`)
    #    e la riga `it` (pgTAP): qui si prova che il join del repository li
    #    porta davvero fino al Python — un join sulla colonna sbagliata
    #    tornerebbe NULL per tutti, e il pannello ripiegherebbe in silenzio.
    def test_ogni_presidio_che_si_accende_arriva_col_testo_per_chi_agisce(self) -> None:
        si_accendono = [r for r in self.catalogo if r["natura"] != NATURA_INVENTARIO]
        self.assertTrue(si_accendono, "nessun presidio che si accende: confronto a vuoto")
        scoperti = sorted(
            r["vista"] for r in si_accendono
            if not (r["chi_agisce"] and r["significato"] and r["azione"])
        )
        self.assertEqual(
            scoperti, [],
            "presidi che si accendono senza testo per chi agisce: il pannello e "
            "il digest ripiegherebbero sulla prosa tecnica.",
        )

    # 9-bis. ⛔ IL TESTO DEL PRESIDIO E' QUELLO SENZA VARIANTE, sul database
    #     vero (brief-db-presidio-processi-testo-per-causa §5.4). Dove il
    #     catalogo dichiara `colonna_variante`, la stessa (vista, lingua) porta
    #     anche i testi per causa: un join che non li esclude ne restituisce uno
    #     a caso, e il test 9 resterebbe verde perche' un testo c'e'.
    #     ⭐ Si confronta col seed (contratto in `80_data`), non con le righe di
    #     una vista: vale anche su un database ricostruito da zero.
    #     ⚠️ E' un PRESIDIO DELLA GIUNTURA, non la prova del filtro: senza
    #     `variante IS NULL` il `LIMIT 1` sceglie per ordine fisico, e il
    #     2026-10-10 sul dbdev pescava proprio il generico (mutazione provata:
    #     verde). La prova che morde e' il test 9 di `test_presidi_repository`,
    #     che legge l'SQL; questo prova che la colonna c'e' e che la query gira.
    def test_il_testo_del_presidio_e_quello_senza_variante(self) -> None:
        with connection.cursor() as cur:
            cur.execute(
                """
                SELECT vista, significato
                  FROM dbops.presidi_testi
                 WHERE lingua = %s AND variante IS NULL
                """,
                [LINGUA_DEFAULT],
            )
            generico = dict(cur.fetchall())
        confrontati = [r for r in self.catalogo if r["vista"] in generico]
        self.assertTrue(confrontati, "nessun presidio con testo: confronto a vuoto")
        self.assertEqual(
            sorted(r["vista"] for r in confrontati
                   if r["significato"] != generico[r["vista"]]),
            [],
        )

    # 9-ter. ⭐ IL TESTO DELLE CAUSE GIRA SUL DATABASE VERO: per ogni presidio
    #     che dichiara `colonna_variante`, ogni causa del catalogo arriva col
    #     suo «chi agisce» e il suo testo. La completezza la garantisce il pgTAP
    #     (`test-presidi-testi-v1` 16-17); qui si prova il TRASPORTO — un join
    #     sulla colonna sbagliata tornerebbe NULL per tutte, e pannello e
    #     digest direbbero «nessun testo per questa causa» ovunque.
    def test_ogni_causa_arriva_col_suo_testo(self) -> None:
        a_varianti = [r for r in self.catalogo if r["colonna_variante"]]
        if not a_varianti:
            self.skipTest("nessun presidio a catalogo dichiara colonna_variante")
        with connection.cursor() as cur:
            cur.execute("SELECT vista, causa FROM dbops.presidi_cause")
            attese = cur.fetchall()
        repo = self.repo
        scoperte = []
        for riga in a_varianti:
            testi = repo.testi_delle_cause(riga["vista"])
            for vista, causa in attese:
                if vista != riga["vista"]:
                    continue
                t = testi.get(causa)
                if not (t and t["chi_agisce"] and t["significato"] and t["azione"]):
                    scoperte.append((vista, causa))
        self.assertEqual(scoperte, [])

    # 9-quater. ⭐ IL CONTEGGIO PER CAUSA SI LEGGE COME TABELLA, sul database
    #     vero. ⚠️ Le righe dipendono da cosa e' acceso adesso, e zero righe e'
    #     una risposta legittima: il test prova la FORMA di cio' che arriva e
    #     che ogni variante non NULL sia a catalogo, non quante ce ne sono.
    def test_il_conteggio_per_causa_si_legge_come_tabella(self) -> None:
        a_varianti = [r for r in self.catalogo if r["colonna_variante"]]
        if not a_varianti:
            self.skipTest("nessun presidio a catalogo dichiara colonna_variante")
        with connection.cursor() as cur:
            cur.execute("SELECT vista, causa FROM dbops.presidi_cause")
            a_catalogo = set(cur.fetchall())
        for riga in a_varianti:
            with self.subTest(vista=riga["vista"]):
                for gruppo in self.repo.conta_per_variante(riga):
                    self.assertEqual(set(gruppo), {"variante", "conteggio"})
                    self.assertIsInstance(gruppo["conteggio"], int)
                    self.assertGreater(gruppo["conteggio"], 0)
                    if gruppo["variante"] is not None:
                        self.assertIn((riga["vista"], gruppo["variante"]), a_catalogo)

    # 10. ⭐ IL RIPIEGO SULLA LINGUA, sul database vero: con la GUC su una
    #     lingua diversa da `it` il testo arriva comunque — la riga `it` e'
    #     obbligatoria, le altre no. Senza ripiego un operatore in inglese
    #     vedrebbe il pannello tornare alla prosa tecnica.
    # ⛔ Una lingua che il catalogo NON PUO' avere, non `en`: il giorno in cui
    #    arrivano le righe inglesi il test passerebbe leggendo quelle, e il
    #    ripiego non lo proverebbe piu' nessuno — sempre verde.
    # ⚠️ La GUC e' di sessione: si rimette com'era, come fa il middleware.
    def test_una_lingua_senza_testo_ripiega_su_it(self) -> None:
        with connection.cursor() as cur:
            cur.execute("SELECT set_config(%s, 'zz', false)", [GUC_NAME])
        try:
            catalogo = PresidiRepository().list_catalogo()
        finally:
            with connection.cursor() as cur:
                cur.execute("SELECT set_config(%s, '', false)", [GUC_NAME])
        si_accendono = [r for r in catalogo if r["natura"] != NATURA_INVENTARIO]
        self.assertTrue(si_accendono, "nessun presidio che si accende: confronto a vuoto")
        self.assertEqual(
            sorted(r["vista"] for r in si_accendono if not r["significato"]), [],
        )
