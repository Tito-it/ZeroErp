# ------------------------------------------------------------
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Test unitari colonne lineage nelle 6 liste documento (Fase B
#        brief-be-fe-lineage + la SESTA SORELLA `vendite.resi`, 2026-08-25):
#        whitelist ORDER BY estesa a pratica/fase e decodifica del tipo della
#        frontiera.
# ------------------------------------------------------------

"""
Indice test eseguiti:
1) LineageListeOrderWhitelistTests.test_pratica_e_fase_ordinabili_su_tutte_le_liste
2) LineageListeOrderWhitelistTests.test_frontiera_non_ordinabile
3) LineageListeFrontieraDecodeTests.test_ogni_lista_decodifica_il_tipo_della_frontiera

⛔ QUESTO FILE ERA ANCORATO A CINQUE LISTE, ed e' la stessa trappola che il
   brief dell'arco S ha isolato sul lato pgTAP (§5 DB-F.3: i test ancorati a
   `lista_id IN (4..8)` restavano VERDI smettendo di coprire la lista nuova).
   Aggiungendo `vendite.resi` al seed senza toccare `_WHITELISTS` qui non ci
   sarebbe stato nessun rosso: la copertura sparisce in silenzio, che e' la
   forma peggiore perche' nessuno la va a cercare.
   ⭐ Regola: una lista documento nuova si aggiunge a `_WHITELISTS`, e i tre
   test la coprono senza scriverne uno nuovo.
"""

import inspect
from unittest import TestCase

from apps.vendite.db import (
    contratti_repository,
    ddt_repository,
    offerte_repository,
    ordini_repository,
    preventivi_repository,
    resi_repository,
)

# Le 6 whitelist ORDER BY delle liste documento (chiave FE campo_sorgente ->
# colonna SQL sull'alias `v` della vista canonica), accanto al modulo del
# repository che le possiede — serve al test 3, che ne legge il sorgente.
_WHITELISTS = {
    "preventivi": (preventivi_repository, preventivi_repository._ORDER_COLS_PREVENTIVI),
    "offerte": (offerte_repository, offerte_repository._ORDER_COLS_OFFERTE),
    "ordini": (ordini_repository, ordini_repository._ORDER_COLS_ORDINI),
    "contratti": (contratti_repository, contratti_repository._ORDER_COLS_CONTRATTI),
    "ddt": (ddt_repository, ddt_repository._ORDER_COLS_DDT),
    # ⭐ La sesta sorella (2026-08-25): `vw_resi_lista` prende `fase` + le nove
    #    colonne di genealogia, e su un reso la frontiera e' la NOTA DI CREDITO
    #    che lo accredita (arco S).
    "resi": (resi_repository, resi_repository._ORDER_COLS_RESI),
}


class LineageListeOrderWhitelistTests(TestCase):
    # Scopo: pratica_numero e fase sono ordinabili su tutte e 6 le liste,
    #        mappate sulle colonne della vista (seed ui.lista_colonna:
    #        pratica.ordinabile=true, fase.ordinabile=true).
    def test_pratica_e_fase_ordinabili_su_tutte_le_liste(self):
        for nome, (_modulo, wl) in _WHITELISTS.items():
            with self.subTest(lista=nome):
                self.assertEqual(wl.get("pratica_numero"), "v.pratica_numero")
                self.assertEqual(wl.get("fase"), "v.fase")

    # Scopo: la frontiera (chip transito) NON e' ordinabile — nessuna colonna
    #        di ordinamento la espone (seed transito.ordinabile=false).
    def test_frontiera_non_ordinabile(self):
        for nome, (_modulo, wl) in _WHITELISTS.items():
            with self.subTest(lista=nome):
                self.assertNotIn("frontiera_codice", wl)
                self.assertNotIn("transito", wl)


class LineageListeFrontieraDecodeTests(TestCase):
    # Scopo: ⛔ IL PRESIDIO DEL DIFETTO SILENZIOSO. Le `vw_*_lista` espongono
    #        `frontiera_tipo_id` (il grafo parla per id) e mai il codice; il
    #        FE parla per `codice_interno`. Ogni repository di lista deve
    #        quindi decodificare l'id nella propria SELECT.
    #        Senza, `LineageFrontieraChip` — che ha il gate su
    #        `isTransitato && tipoCodice` — rende «—», cioe' «non transitato»,
    #        proprio sulla riga che HA transitato: nessun errore, nessun log,
    #        solo la colonna «Transito» muta.
    #        Difetto reale trovato il 2026-08-25 sulla lista resi appena nata
    #        sesta sorella: la colonna c'era a catalogo, il dato a DB, e a
    #        video non sarebbe comparso niente.
    def test_ogni_lista_decodifica_il_tipo_della_frontiera(self):
        for nome, (modulo, _wl) in _WHITELISTS.items():
            with self.subTest(lista=nome):
                sorgente = inspect.getsource(modulo)
                self.assertIn(
                    "AS frontiera_tipo_codice", sorgente,
                    f"{nome}: la lista proietta frontiera_tipo_id senza decodificarlo — "
                    "il chip transito resterebbe muto.",
                )
                self.assertIn(
                    "config.sorgenti s ON s.id = v.frontiera_tipo_id", sorgente,
                    f"{nome}: la decodifica del tipo frontiera deve venire da "
                    "config.sorgenti, non da una mappa scritta a mano.",
                )
