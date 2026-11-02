# ------------------------------------------------------------
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: L'ACCENSIONE dei processi dal lato del backend, sul database vero:
#        le letture (`ProcessiRepository.accensione_processo`,
#        `MaintenanceRepository.sveglia_accesa`) e il verbo della scelta a
#        mano (`ProcessiService.imposta_accensione`), contro le funzioni del
#        giro 1 di brief-db-processi-accensione-per-ambiente.
# Note: ⭐ Perche' sul DB vero: sono funzioni nuove chiamate per nome e con i
#        loro argomenti, e un mock non vedrebbe una firma sbagliata
#        (feedback «binding provato con una chiamata reale»).
#        ⛔ I casi si costruiscono sul CONTRATTO del seed (`processi.csv`:
#        chi e' spegnibile, il default per ambiente), non contando la
#        popolazione: un processo spegnibile, uno che non si spegne mai.
#        ⚠️ Ogni scrittura sta in una transazione annullata: la scelta a mano
#        e' un dato di MACCHINA, e il test non deve lasciarne.
#        ⚠️ L'ambiente deve essere dichiarato (la CI e lo scratch sono
#        `SVILUPPO`, dbdev pure): su un database non dichiarato il test lo dice
#        e si ferma, invece di provare un'altra cosa.
# ------------------------------------------------------------
"""Indice test previsti (su DB provvisto, `ZEROERP_TEST_DB_E2E=1`).

1. test_la_lettura_porta_stato_default_e_ambiente
     forma della lettura sul seed: spegnibile, i due default, l'ambiente, e
     `acceso` uguale al default dell'ambiente quando non c'e' scelta a mano.
2. test_spegnere_e_tornare_al_default
     ⭐ il verbo spegne (la scelta a mano col motivo, la sveglia systemd la
     legge spenta), poi `null` toglie la scelta e torna il default.
3. test_un_non_spegnibile_rifiuta_col_suo_codice
     il guard del DB rifiuta, e il service porta il SUO codice, non un
     generico.
4. test_acceso_processo_e_la_stessa_risposta
     la lettura di chi decide da' lo stesso `acceso` del dettaglio, e un
     codice inesistente solleva invece di rispondere None.
5. test_accendere_legge_il_predicato_del_guard
     ⭐ R-BE-5: la capability di «Accendi» e' la risposta di
     `dbops.fn_accensione_a_mano_ammessa_su_valori`, chiamata per nome. In
     SVILUPPO (la CI, dbdev) e' ammesso anche lo smoke notturno, che in
     PRODUZIONE non lo e': il ramo PRODUZIONE lo prova il pgTAP sui valori
     (`test-processi-accensione-v1`), qui si prova il binding e la lettura.
"""

from __future__ import annotations

from unittest import TestCase

from django.db import transaction

from apps.core.db.maintenance_repository import MaintenanceRepository
from apps.core.db.processi_repository import ProcessiRepository
from apps.core.services.processi import PROCESSO_SMOKE_NOTTURNO
from apps.core.services.processi_service import (
    E_PROCESSO_NON_ACCENDIBILE_IN_PRODUZIONE,
    ProcessiService,
)
from apps.core.services.service_errors import ServiceError
from apps.core.tests.db_e2e import richiedi_db_provvisto

# Dal SEED (`80_data/sql/dbops/processi.csv`, contratto del giro 1):
# - la coda stampa si spegne, ed e' accesa di default in tutti e due gli ambienti;
# - il listener dei permessi non si spegne mai (A-5).
_SPEGNIBILE = "draina_coda_stampa"
_NON_SPEGNIBILE = "listen_permessi"
# - lo smoke notturno non si accende a mano in PRODUZIONE (R-BE-5).
_NON_ACCENDIBILE_IN_PRODUZIONE = PROCESSO_SMOKE_NOTTURNO


class AccensioneProcessiDbTests(TestCase):
    """Letture e verbo dell'accensione, contro le funzioni del DB."""

    @classmethod
    def setUpClass(cls) -> None:
        super().setUpClass()
        richiedi_db_provvisto()
        cls.repo = ProcessiRepository()

    # Scopo: l'ambiente dichiarato, o il test si ferma dicendolo.
    def _ambiente(self) -> str:
        lettura = self.repo.accensione_processo(_SPEGNIBILE)
        self.assertIsNotNone(lettura, f"{_SPEGNIBILE} non e' nel catalogo")
        assert lettura is not None
        ambiente = lettura["ambiente"]
        self.assertIn(
            ambiente, ("SVILUPPO", "PRODUZIONE"),
            "ambiente dell'installazione non dichiarato: provision_zeroerp.sql "
            "fase post con -v ambiente=…",
        )
        return ambiente

    # 1. La lettura sul seed.
    def test_la_lettura_porta_stato_default_e_ambiente(self) -> None:
        ambiente = self._ambiente()
        with transaction.atomic():
            # Nessuna scelta a mano: si toglie quella che la macchina avesse.
            # ⚠️ Col motivo: dal giro 2a (2026-10-17) anche «torna al default»
            #    lo vuole, e la riga resta con `acceso` NULL (chi, quando,
            #    perche'), che la lettura tratta come «nessuna scelta».
            self.repo.imposta_accensione(_SPEGNIBILE, acceso=None, motivo="pulizia del test")
            lettura = self.repo.accensione_processo(_SPEGNIBILE)
            assert lettura is not None
            self.assertTrue(lettura["spegnibile"])
            self.assertIsNone(lettura["scelta_a_mano"])
            default = (
                lettura["acceso_in_sviluppo"] if ambiente == "SVILUPPO"
                else lettura["acceso_in_produzione"]
            )
            self.assertIs(lettura["acceso"], default)
            transaction.set_rollback(True)
        self.assertIsNone(self.repo.accensione_processo("processo_che_non_esiste"))

    # 2. ⭐ Spegnere, e la sveglia lo vede; poi tornare al default.
    def test_spegnere_e_tornare_al_default(self) -> None:
        self._ambiente()
        svc = ProcessiService()
        with transaction.atomic():
            spento = svc.imposta_accensione(
                _SPEGNIBILE, {"acceso": False, "motivo": "prova del test"}, attore="test",
            )
            self.assertIs(spento["acceso"], False)
            self.assertEqual(spento["scelta_a_mano"]["motivo"], "prova del test")
            self.assertIs(spento["scelta_a_mano"]["acceso"], False)
            self.assertTrue(spento["can_imposta_accensione"])
            # La sveglia systemd legge la stessa cosa (`e_dovuto`).
            self.assertIs(MaintenanceRepository().sveglia_accesa(_SPEGNIBILE), False)

            di_nuovo = svc.imposta_accensione(
                _SPEGNIBILE, {"acceso": None, "motivo": "fine prova"}, attore="test",
            )
            self.assertIsNone(di_nuovo["scelta_a_mano"])
            self.assertIs(
                di_nuovo["acceso"],
                MaintenanceRepository().sveglia_accesa(_SPEGNIBILE),
            )
            transaction.set_rollback(True)

    # 3. Il guard del DB rifiuta un non spegnibile, col suo codice; e la
    #    capability lo aveva gia' detto.
    def test_un_non_spegnibile_rifiuta_col_suo_codice(self) -> None:
        self._ambiente()
        svc = ProcessiService()
        lettura = svc.get_processo(_NON_SPEGNIBILE)["accensione"]
        self.assertFalse(lettura["can_imposta_accensione"])
        self.assertEqual(lettura["can_imposta_accensione_reason"], "E_PROCESSO_NON_SPEGNIBILE")
        self.assertIs(lettura["acceso"], True)
        with transaction.atomic():
            with self.assertRaises(ServiceError) as cm:
                with transaction.atomic():
                    svc.imposta_accensione(
                        _NON_SPEGNIBILE, {"acceso": False, "motivo": "prova"}, attore="test",
                    )
            self.assertEqual(cm.exception.code, "E_PROCESSO_NON_SPEGNIBILE")
            transaction.set_rollback(True)

    # 4. La lettura di chi DECIDE («Esegui ora», l'handler) e quella di chi
    #    DESCRIVE (il drawer) danno la stessa risposta; l'inesistente solleva.
    def test_acceso_processo_e_la_stessa_risposta(self) -> None:
        self._ambiente()
        for codice in (_SPEGNIBILE, _NON_SPEGNIBILE):
            with self.subTest(codice=codice):
                lettura = self.repo.accensione_processo(codice)
                assert lettura is not None
                self.assertIs(self.repo.acceso_processo(codice), lettura["acceso"])
        with self.assertRaises(LookupError):
            self.repo.acceso_processo("processo_che_non_esiste")

    # 5. ⭐ «Accendi» legge il predicato del guard, non una regola del backend.
    def test_accendere_legge_il_predicato_del_guard(self) -> None:
        ambiente = self._ambiente()
        svc = ProcessiService()
        for codice in (_SPEGNIBILE, _NON_ACCENDIBILE_IN_PRODUZIONE):
            with self.subTest(codice=codice):
                lettura = svc.get_processo(codice)["accensione"]
                self.assertNotIn("accendere_ammesso", lettura)
                if ambiente == "SVILUPPO" or codice == _SPEGNIBILE:
                    self.assertTrue(lettura["can_accendere"])
                    self.assertIsNone(lettura["can_accendere_reason"])
                else:
                    self.assertFalse(lettura["can_accendere"])
                    self.assertEqual(
                        lettura["can_accendere_reason"], E_PROCESSO_NON_ACCENDIBILE_IN_PRODUZIONE,
                    )

