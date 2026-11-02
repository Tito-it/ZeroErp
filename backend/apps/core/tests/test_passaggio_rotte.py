# ------------------------------------------------------------
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Presidio delle dichiarazioni `<metodo>_passaggio = PassaggioDocumento`
#        sulle rotte servite (M-3, brief-modello-documento-vendita §7.6). Un
#        refuso non da' errore: con un `documento_kwarg` che la rotta non ha,
#        `PassaggioDocumento.azione` risponde None e il passaggio protetto
#        dall'azione passerebbe col solo livello sul documento — fino al
#        rifiuto del verbo, dopo la transazione. Lo stesso per una testata la
#        cui matrice non dichiara l'azione.
# Note: la parte sul catalogo chiede il DB provvisto; quella sulle rotte no.
# ------------------------------------------------------------
"""
Indice test eseguiti:
1) PassaggioRotteTests.test_il_parametro_e_nel_percorso — il kwarg c'e' nella rotta
2) PassaggioRotteTests.test_esclusivo_con_permission — mai le due fonti sullo stesso metodo
3) PassaggioRotteTests.test_le_rotte_attese_dichiarano — DDT, reso, preventivo, ordine, contratto, offerta, commessa, lotto e versione di listino sul modello
4) PassaggioRotteTests.test_emetti_chiede_lo_stato_al_vocabolario — «Emetti» senza stato fissato
5) PassaggioTestataDbTests.test_la_testata_e_sul_modello — mappa + matrice con l'azione
6) PassaggioTestataDbTests.test_emetti_ha_lo_stato_di_emissione — ogni «Emetti» sul modello si emette
7) PassaggioTestataDbTests.test_iniziale_ha_lo_stato_iniziale — ogni rotta verso lo stato iniziale lo trova
"""
from __future__ import annotations

import unittest

from django.db import connection
from django.test import SimpleTestCase

from apps.core.api.permissions import PassaggioDocumento, ZeroERPPermission
from apps.core.api.rotte import Rotta, rotte_servite
from apps.core.db.documento_modello_repository import DocumentoModelloRepository
from apps.core.tests.db_e2e import richiedi_db_provvisto

# Le chiavi che la catena legge (`<chiave>_passaggio`), dalla catena stessa:
# un metodo o un'action nuovi non restano fuori in silenzio.
_CHIAVI: tuple[str, ...] = (
    *ZeroERPPermission.ACTION_REQUIRES,
    *(metodo.lower() for metodo in ZeroERPPermission.METHOD_REQUIRES),
)


# Scopo: le coppie (rotta, metodo, dichiarazione) di tutte le rotte servite.
def _dichiarazioni() -> list[tuple[Rotta, str, PassaggioDocumento]]:
    trovate = []
    for rotta in rotte_servite(anche_condizionali=True):
        for metodo in _CHIAVI:
            passaggio = getattr(rotta.view, f"{metodo}_passaggio", None)
            if isinstance(passaggio, PassaggioDocumento):
                trovate.append((rotta, metodo, passaggio))
    return trovate


class PassaggioRotteTests(SimpleTestCase):

    def test_il_parametro_e_nel_percorso(self) -> None:
        for rotta, metodo, passaggio in _dichiarazioni():
            with self.subTest(rotta=rotta.percorso, metodo=metodo):
                self.assertIn(f"<int:{passaggio.documento_kwarg}>", rotta.percorso)

    def test_esclusivo_con_permission(self) -> None:
        for rotta, metodo, _ in _dichiarazioni():
            with self.subTest(rotta=rotta.percorso, metodo=metodo):
                self.assertIsNone(getattr(rotta.view, f"{metodo}_permission", None))

    # Il presidio non deve passare a vuoto: le rotte dei giri 5-12 ci sono.
    # ⚠️ Il contratto (giro 8) era sul modello ma non in questo elenco: entrato
    #    col giro 9 (brief-modello-documento-vendita §13.6). La commessa (giro
    #    10) non si emette: ha la sola rotta dello stato.
    def test_le_rotte_attese_dichiarano(self) -> None:
        percorsi = {r.percorso for r, _, _ in _dichiarazioni()}
        for coda in ("<int:ddt_id>/cambia-stato/", "ddt/<int:sorgente_id>/emetti/",
                     "<int:reso_id>/conferma/", "<int:reso_id>/annulla/",
                     "<int:preventivo_id>/stato/", "da-pratica/<int:pratica_id>/stato/",
                     "preventivi/<int:sorgente_id>/emetti/",
                     "<int:ordine_id>/cambia-stato/", "ordini/<int:sorgente_id>/emetti/",
                     "<int:contratto_id>/cambia-stato/", "contratti/<int:sorgente_id>/emetti/",
                     "<int:offerta_id>/registra-esito/", "<int:offerta_id>/annulla/",
                     "offerte/<int:sorgente_id>/emetti/",
                     "commesse/<int:commessa_id>/stato/",
                     # giro 11, il lotto (§15.8 punto 3, §15.13)
                     "lotti/<int:lotto_id>/numera/", "<int:lotto_id>/riporta-a-draft/",
                     "lotti/<int:lotto_id>/reset-draft/",
                     # giro 12, la versione di listino (§16.5, BE-L2)
                     "<int:listino_id>/versioni/<int:ver_id>/stato/"):
            with self.subTest(coda=coda):
                self.assertTrue(any(p.endswith(coda) for p in percorsi), coda)

    # ⭐ Il presidio dell'emissione, generico sui documenti della factory
    #    (B-5, brief-modello-documento-vendita §8.11): ogni «Emetti» che legge
    #    il passaggio chiede lo stato di emissione al vocabolario, nessuno lo
    #    fissa. Un documento nuovo portato al modello entra da solo.
    def test_emetti_chiede_lo_stato_al_vocabolario(self) -> None:
        emetti = [(r, p) for r, _, p in _dichiarazioni() if r.percorso.endswith("/emetti/")]
        self.assertGreaterEqual(len(emetti), 5)  # bolla, preventivo, ordine, contratto, offerta
        for rotta, passaggio in emetti:
            with self.subTest(rotta=rotta.percorso):
                self.assertEqual(passaggio.stato_del_modello, "emissione")
                self.assertIsNone(passaggio.stato_chiesto)


class PassaggioTestataDbTests(unittest.TestCase):

    @classmethod
    def setUpClass(cls) -> None:
        richiedi_db_provvisto("script.fn_doc_stato_codice(regclass,bigint)")

    # `fn_doc_passaggio` rifiuta una testata fuori mappa o una matrice senza
    # `azione_processo_codename` (E_SCRIPT_CHIAMATA_NON_VALIDA): chiamata con
    # stati NULL non legge righe, prova solo che la testata e' sul modello.
    def test_la_testata_e_sul_modello(self) -> None:
        testate = sorted({p.testata for _, _, p in _dichiarazioni()})
        self.assertTrue(testate)
        with connection.cursor() as cur:
            for testata in testate:
                with self.subTest(testata=testata):
                    cur.execute(
                        "SELECT count(*) FROM script.fn_doc_passaggio(%s::regclass, NULL, NULL)",
                        [testata],
                    )
                    self.assertEqual(cur.fetchone()[0], 0)

    # Lo stato che «Emetti» chiede esiste per ogni testata che lo dichiara:
    # un documento senza emissione dietro un «Emetti» sarebbe un 500 a ogni
    # richiesta (E_CONFIG_MANCANTE).
    def test_emetti_ha_lo_stato_di_emissione(self) -> None:
        testate = sorted({p.testata for _, _, p in _dichiarazioni() if p.stato_del_modello == "emissione"})
        self.assertTrue(testate)
        repo = DocumentoModelloRepository()
        for testata in testate:
            with self.subTest(testata=testata):
                self.assertIsNotNone(repo.stato_di_emissione(testata))

    # Lo stato iniziale che «riporta in bozza» chiede esiste per ogni testata
    # che lo dichiara (§15.13): senza, `PassaggioDocumento` risponderebbe None
    # e il passaggio passerebbe col solo livello sul documento.
    def test_iniziale_ha_lo_stato_iniziale(self) -> None:
        testate = sorted({p.testata for _, _, p in _dichiarazioni() if p.stato_del_modello == "iniziale"})
        self.assertTrue(testate)
        repo = DocumentoModelloRepository()
        for testata in testate:
            with self.subTest(testata=testata):
                self.assertIsNotNone(repo.stato_iniziale(testata))
