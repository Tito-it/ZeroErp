# ------------------------------------------------------------
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: «Leggi prima la testata» sulla PAGINA delle righe di ognuno dei sette
#        documenti di vendita (preventivo, ordine, DDT, reso, fattura,
#        contratto, offerta — quest'ultima dal 2026-10-05): con la testata che non si vede il service risponde il 404
#        del dominio e NON legge le righe.
# Note: §9.6 punto 1 del brief-db-liste-righe-documento (2026-10-04). Fino a
#       quel giorno nessun test lo provava: togliere la lettura della testata
#       da un service lasciava la suite verde, e un documento fuori perimetro
#       diventava una lista vuota (le righe stanno dietro RLS e viste
#       `security_invoker`). Il BB `pagina_dopo_testata` ha il suo test in
#       core; qui c'e' un caso per CONSUMATORE, perche' ognuno passa la sua
#       testata e il suo repository.
# ------------------------------------------------------------

"""
Indice test eseguiti:
1) test_testata_assente_404_e_nessuna_riga_letta  (sette documenti)
2) test_testata_presente_la_pagina_riceve_le_opzioni (sette documenti)
"""

from __future__ import annotations

import unittest
from collections.abc import Callable, Iterator
from contextlib import contextmanager
from typing import Any
from unittest.mock import MagicMock, patch

from apps.core.services.service_errors import ServiceError
from apps.vendite.services import (
    contratti_service,
    ddt_service,
    offerte_service,
    ordini_service,
    preventivi_service,
    resi_service,
    vendite_service,
)

_OPZIONI = {"search": "abc", "order_by": "descrizione", "order_dir": "asc", "limit": 10, "offset": 20}


# Scopo: un documento da provare: dove si sostituiscono il repository della
#        testata e quello delle righe, come si fa sparire la testata, come si
#        chiama la pagina e il codice del 404 atteso.
class _Caso:
    def __init__(
        self,
        nome: str,
        *,
        repo_testata: str,
        getter: str,
        repo_righe: str,
        pagina: Callable[..., Any],
        codice: str,
    ) -> None:
        self.nome = nome
        self.repo_testata = repo_testata
        self.getter = getter
        self.repo_righe = repo_righe
        self.pagina = pagina
        self.codice = codice


_CASI = (
    _Caso("preventivo", repo_testata="apps.vendite.services.preventivi_service.PreventiviRepository",
          getter="get_preventivo", repo_righe="apps.vendite.services.preventivi_service.PreventiviRepository",
          pagina=preventivi_service.list_righe_pagina, codice="E_PREV_NOT_FOUND"),
    _Caso("ordine", repo_testata="apps.vendite.services.ordini_service.OrdiniRepository",
          getter="get_ordine", repo_righe="apps.vendite.services.ordini_service.OrdiniRepository",
          pagina=ordini_service.list_righe_pagina, codice="E_ORD_NOT_FOUND"),
    _Caso("ddt", repo_testata="apps.vendite.services.ddt_service.DdtRepository",
          getter="get_ddt", repo_righe="apps.vendite.services.ddt_service.DdtRepository",
          pagina=ddt_service.list_righe_pagina, codice="E_DDT_NOT_FOUND"),
    _Caso("reso", repo_testata="apps.vendite.services.resi_service.ResiRepository",
          getter="get_reso", repo_righe="apps.vendite.services.resi_service.ResiRepository",
          pagina=resi_service.list_righe_pagina, codice="E_RESO_NOT_FOUND"),
    _Caso("fattura", repo_testata="apps.vendite.services.vendite_service.VenditeRepository",
          getter="get_fattura_testata", repo_righe="apps.vendite.services.vendite_service.FattureRepository",
          pagina=vendite_service.list_fattura_righe_pagina, codice="E_FATTURA_NON_TROVATA"),
    _Caso("contratto", repo_testata="apps.vendite.services.contratti_service.ContrattiRepository",
          getter="get_stato_codice", repo_righe="apps.vendite.services.contratti_service.ContrattoRigheListaRepository",
          pagina=lambda doc_id, **kw: contratti_service.ContrattiService().list_righe_pagina(doc_id, **kw),
          codice="E_VENDITE_NOT_FOUND"),
    # Gemella del contratto (2026-10-05): la lista 106 sulla stessa funzione comune.
    _Caso("offerta", repo_testata="apps.vendite.services.offerte_service.OfferteRepository",
          getter="get_stato_codice", repo_righe="apps.vendite.services.offerte_service.OffertaRigheListaRepository",
          pagina=lambda doc_id, **kw: offerte_service.OfferteService().list_righe_pagina(doc_id, **kw),
          codice="E_VENDITE_NOT_FOUND"),
)


# Scopo: sostituisce i repository della testata e delle righe. ⚠️ Per i
#        quattro documenti con tabella sono lo STESSO repository: una patch
#        sola, o la seconda scavalcherebbe la prima.
@contextmanager
def _repository(caso: _Caso) -> Iterator[tuple[MagicMock, MagicMock]]:
    if caso.repo_testata == caso.repo_righe:
        with patch(caso.repo_testata) as cls:
            yield cls, cls
    else:
        with patch(caso.repo_testata) as testata_cls, patch(caso.repo_righe) as righe_cls:
            yield testata_cls, righe_cls


class RighePaginaDopoTestataTests(unittest.TestCase):

    def test_testata_assente_404_e_nessuna_riga_letta(self) -> None:
        for caso in _CASI:
            with self.subTest(documento=caso.nome), _repository(caso) as (testata_cls, righe_cls):
                getattr(testata_cls.return_value, caso.getter).return_value = None
                with self.assertRaises(ServiceError) as ctx:
                    caso.pagina(7, **_OPZIONI)
                self.assertEqual(ctx.exception.code, caso.codice)
                righe_cls.return_value.list_righe_pagina.assert_not_called()

    def test_testata_presente_la_pagina_riceve_le_opzioni(self) -> None:
        for caso in _CASI:
            with self.subTest(documento=caso.nome), _repository(caso) as (testata_cls, righe_cls):
                getattr(testata_cls.return_value, caso.getter).return_value = MagicMock()
                righe_cls.return_value.list_righe_pagina.return_value = ([{"id": 1}], 1)
                self.assertEqual(caso.pagina(7, **_OPZIONI), ([{"id": 1}], 1))
                righe_cls.return_value.list_righe_pagina.assert_called_once_with(7, **_OPZIONI)
