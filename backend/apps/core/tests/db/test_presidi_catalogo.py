# ------------------------------------------------------------
# SPDX-License-Identifier: GPL-3.0-or-later
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
"""

from __future__ import annotations

from unittest import TestCase

from apps.core.db.presidi_repository import (
    _IN_ATTESA_DI_CATALOGO,
    CADENZA_MAI,
    CADENZE,
    NATURA_CANCELLO,
    NATURA_INVENTARIO,
    NATURE,
    PERIMETRI,
    PresidiRepository,
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
