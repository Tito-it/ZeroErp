# ------------------------------------------------------------
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Il verbo della scelta a mano sull'accensione di un processo
#        (`ProcessiService.imposta_accensione`) e la sua capability nel
#        dettaglio, con i repository finti — brief-db-processi-accensione-per-
#        ambiente §6.0 punto 5. Il giro sul database vero e' in
#        `tests/db/test_processi_accensione_db.py`.
# Note: ⛔ `SimpleTestCase`: un mock dimenticato deve FALLIRE, non parlare
#        col dbdev.
# ------------------------------------------------------------
"""Indice test.

1. test_acceso_va_detto_anche_null        assente o non booleano -> 400 campo acceso
2. test_il_motivo_e_obbligatorio_sempre    anche per «torna al default» -> campo motivo
3. test_processo_inesistente               404, nessuna scrittura
4. test_i_tre_gesti_arrivano_al_verbo      true / false / null, motivo ripulito
5. test_capability_dal_catalogo            spegnibile -> si'; non spegnibile e
                                           senza sveglia -> no, col codice del guard
"""

from __future__ import annotations

from unittest.mock import MagicMock

from django.test import SimpleTestCase

from apps.core.services.processi_service import (
    E_MOTIVO_OBBLIGATORIO,
    E_NOT_FOUND,
    E_PROCESSO_NON_SPEGNIBILE,
    E_PROCESSO_SENZA_SVEGLIA,
    ProcessiService,
    _con_capability_accensione,
)
from apps.core.services.service_errors import E_VALIDATION_INPUT, ServiceError


# Scopo: il service con il repository dei processi finto.
def _service(*, esiste: bool = True):
    repo = MagicMock()
    repo.get_processo.return_value = {"codice": "p"} if esiste else None
    repo.accensione_processo.return_value = {"acceso": False, "spegnibile": True}
    return ProcessiService(repo=repo, presidi=MagicMock(), coda=MagicMock()), repo


class ImpostaAccensioneTests(SimpleTestCase):
    # 1. `acceso` va detto: un campo assente non vale «torna al default».
    def test_acceso_va_detto_anche_null(self) -> None:
        for payload in ({"motivo": "m"}, {"acceso": "no", "motivo": "m"}, {"acceso": 0, "motivo": "m"}):
            with self.subTest(payload=payload):
                svc, repo = _service()
                with self.assertRaises(ServiceError) as cm:
                    svc.imposta_accensione("p", payload, attore="a")
                self.assertEqual(cm.exception.code, E_VALIDATION_INPUT)
                self.assertEqual(cm.exception.context.get("field"), "acceso")
                repo.imposta_accensione.assert_not_called()

    # 2. Il motivo per tutti e tre i gesti: per «torna al default» il DB non
    #    lascia traccia, e il motivo e' l'unica cosa che resta.
    def test_il_motivo_e_obbligatorio_sempre(self) -> None:
        for acceso in (True, False, None):
            for motivo in (None, "", "   ", 7):
                with self.subTest(acceso=acceso, motivo=motivo):
                    svc, repo = _service()
                    with self.assertRaises(ServiceError) as cm:
                        svc.imposta_accensione("p", {"acceso": acceso, "motivo": motivo}, attore="a")
                    self.assertEqual(cm.exception.code, E_MOTIVO_OBBLIGATORIO)
                    self.assertEqual(cm.exception.context.get("field"), "motivo")
                    repo.imposta_accensione.assert_not_called()

    # 3. Processo inesistente: 404 di dominio, niente scrittura.
    def test_processo_inesistente(self) -> None:
        svc, repo = _service(esiste=False)
        with self.assertRaises(ServiceError) as cm:
            svc.imposta_accensione("x", {"acceso": False, "motivo": "m"}, attore="a")
        self.assertEqual(cm.exception.code, E_NOT_FOUND)
        repo.imposta_accensione.assert_not_called()

    # 4. I tre gesti arrivano al verbo com'erano, col motivo ripulito; la
    #    risposta e' l'accensione rinfrescata, con la capability.
    def test_i_tre_gesti_arrivano_al_verbo(self) -> None:
        for acceso in (True, False, None):
            with self.subTest(acceso=acceso):
                svc, repo = _service()
                esito = svc.imposta_accensione("p", {"acceso": acceso, "motivo": "  perche' si  "}, attore="a")
                repo.imposta_accensione.assert_called_once_with("p", acceso=acceso, motivo="perche' si")
                self.assertIs(esito["acceso"], False)
                self.assertTrue(esito["can_imposta_accensione"])


class CapabilityAccensioneTests(SimpleTestCase):
    # 5. Il flag discende dal catalogo come il guard che rifiuterebbe.
    def test_capability_dal_catalogo(self) -> None:
        casi = (
            (True, True, None),
            (False, False, E_PROCESSO_NON_SPEGNIBILE),
            (None, False, E_PROCESSO_SENZA_SVEGLIA),
        )
        for spegnibile, flag, reason in casi:
            with self.subTest(spegnibile=spegnibile):
                riga = _con_capability_accensione({"acceso": True, "spegnibile": spegnibile})
                assert riga is not None
                self.assertIs(riga["can_imposta_accensione"], flag)
                self.assertIs(riga["ha_sveglia"], spegnibile is not None)
                self.assertEqual(riga["can_imposta_accensione_reason"], reason)
        self.assertIsNone(_con_capability_accensione(None))
