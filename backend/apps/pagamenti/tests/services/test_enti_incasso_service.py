# ------------------------------------------------------------
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Test dei canali di incasso — la configurazione da cui dipende il
#        perimetro degli incassi.
# Note: 🔴 Qui il difetto non e' un errore: e' un canale agganciato al conto
#        sbagliato, che sposta il denaro nel perimetro di un altro emittente
#        senza che niente lo dica. I test guardano proprio quello.
# ------------------------------------------------------------

"""
Indice test eseguiti:
1)  ContiIncassoTests.test_solo_i_conti_di_incasso
2)  ContiIncassoTests.test_elenco_vuoto_lo_dichiara
3)  ContiIncassoTests.test_elenco_pieno_non_lo_dichiara
4)  CreaEnteTests.test_il_conto_e_obbligatorio_su_tutti_i_tipi
5)  CreaEnteTests.test_banca_pretende_la_filiale
6)  CreaEnteTests.test_gli_altri_tipi_vietano_la_filiale
7)  CreaEnteTests.test_tipo_inventato_rifiutato
8)  CreaEnteTests.test_tipo_normalizzato_maiuscolo
9)  CreaEnteTests.test_codice_e_descrizione_obbligatori
10) PatchTests.test_codice_interno_non_e_aggiornabile
11) PatchTests.test_patch_vuoto_rifiutato
12) PatchTests.test_canale_inesistente_404
13) ListaTests.test_tipo_fuori_vocabolario_rifiutato
14) ListaTests.test_ordinamento_fuori_whitelist_rifiutato
15) ListaTests.test_default_per_codice_crescente
"""

from unittest import TestCase
from unittest.mock import MagicMock, patch

from apps.core.services.error_manager import ServiceError
from apps.core.services.error_policies import ErrorPolicyRegistry
from apps.pagamenti.services import enti_incasso_service

_ENTE = {"id": 4, "codice": "BANCA-1", "tipo": "BANCA", "conto_iban": "IT00…"}


def _repo() -> MagicMock:
    repo = MagicMock()
    repo.get_ente_incasso.return_value = dict(_ENTE)
    repo.create_ente_incasso.return_value = 4
    repo.update_ente_incasso.return_value = 1
    repo.list_enti_incasso.return_value = ([], 0)
    repo.list_conti_incasso.return_value = [
        {"soggetto_ruolo_conto_bancario_id": 312, "iban": "IT22…", "predefinito": True}
    ]
    # ⛔ Il perimetro NON si prova qui: e' una domanda al database (le GUC
    #    dell'identita'), e un doppio non ha un perimetro — risponderebbe
    #    quello che gli si dice. La prova vera sta in
    #    `tests/db/test_perimetro_conti_incasso.py`, contro il DB provvisto.
    repo.emittente_nel_perimetro.return_value = True
    return repo


class _Base(TestCase):
    # Scopo: Sostituisce il repository con un doppio.
    def setUp(self) -> None:
        self.repo = _repo()
        patcher = patch.object(
            enti_incasso_service, "PagamentiRepository", return_value=self.repo
        )
        patcher.start()
        self.addCleanup(patcher.stop)


class ContiIncassoTests(_Base):
    # Scopo: 🔴 BE-8. Il database rifiuta un conto che non e' di incasso, ma un
    #        elenco che lo propone fa sbagliare — e chi sbaglia se ne accorge
    #        dopo aver compilato tutto il resto.
    def test_solo_i_conti_di_incasso(self):
        enti_incasso_service.list_conti_incasso(72)
        self.repo.list_conti_incasso.assert_called_once_with(72)

    # Scopo: ⚠️ Un elenco vuoto NON e' un guasto: quel soggetto non ha ancora un
    #        conto di incasso censito a livello di RUOLO. E' la condizione
    #        voluta (si fallisce alla configurazione), e la risposta la dichiara
    #        — un menu vuoto senza spiegazione sembra un errore dell'applicazione.
    def test_elenco_vuoto_lo_dichiara(self):
        self.repo.list_conti_incasso.return_value = []
        esito = enti_incasso_service.list_conti_incasso(72)
        self.assertTrue(esito["nessun_conto_di_incasso"])
        self.assertEqual(esito["count"], 0)

    def test_elenco_pieno_non_lo_dichiara(self):
        esito = enti_incasso_service.list_conti_incasso(64)
        self.assertFalse(esito["nessun_conto_di_incasso"])


class CreaEnteTests(_Base):
    _OK = {
        "codice": "BANCA-1",
        "descrizione": "Conto principale",
        "tipo": "POSTE",
        "soggetto_ruolo_conto_bancario_id": 312,
    }

    # Scopo: 🔴 Il conto e' obbligatorio su TUTTI i tipi, non solo su BANCA: un
    #        canale POSTE, PSP o ALTRO senza conto sarebbe lo stesso difetto
    #        travestito, con la coda invisibile spostata su un altro tipo.
    def test_il_conto_e_obbligatorio_su_tutti_i_tipi(self):
        for tipo in enti_incasso_service.TIPI:
            payload = {**self._OK, "tipo": tipo}
            payload.pop("soggetto_ruolo_conto_bancario_id")
            if tipo == enti_incasso_service.TIPO_BANCA:
                payload["bank_branch_id"] = 1
            with self.assertRaises(ServiceError, msg=f"tipo {tipo}"):
                enti_incasso_service.crea_ente_incasso(payload)
        self.repo.create_ente_incasso.assert_not_called()

    # Scopo: La filiale e' un fatto DIVERSO dal conto e vale solo per la banca.
    def test_banca_pretende_la_filiale(self):
        with self.assertRaises(ServiceError):
            enti_incasso_service.crea_ente_incasso({**self._OK, "tipo": "BANCA"})

    def test_gli_altri_tipi_vietano_la_filiale(self):
        with self.assertRaises(ServiceError):
            enti_incasso_service.crea_ente_incasso(
                {**self._OK, "tipo": "POSTE", "bank_branch_id": 1}
            )

    def test_tipo_inventato_rifiutato(self):
        with self.assertRaises(ServiceError):
            enti_incasso_service.crea_ente_incasso({**self._OK, "tipo": "CONTANTI"})

    def test_tipo_normalizzato_maiuscolo(self):
        enti_incasso_service.crea_ente_incasso({**self._OK, "tipo": "poste"})
        self.assertEqual(
            self.repo.create_ente_incasso.call_args.args[0]["tipo"], "POSTE"
        )

    def test_codice_e_descrizione_obbligatori(self):
        for chiave in ("codice", "descrizione"):
            payload = {k: v for k, v in self._OK.items() if k != chiave}
            with self.assertRaises(ServiceError):
                enti_incasso_service.crea_ente_incasso(payload)


class PatchTests(_Base):
    # Scopo: ⛔ `codice_interno` e' la chiave stabile con cui il resto del
    #        sistema nomina il canale: cambiarla romperebbe i riferimenti senza
    #        che niente lo dica.
    def test_codice_interno_non_e_aggiornabile(self):
        with self.assertRaises(ServiceError):
            enti_incasso_service.aggiorna_ente_incasso(4, {"codice_interno": "X"})
        self.repo.update_ente_incasso.assert_not_called()

    # ⛔ Un PATCH senza campi e' un 400 (Tid, 2026-10-20, §A2), e non scrive.
    def test_patch_vuoto_rifiutato(self):
        with self.assertRaises(ServiceError):
            enti_incasso_service.aggiorna_ente_incasso(4, {})
        self.repo.update_ente_incasso.assert_not_called()

    # Scopo: un canale inesistente risponde 404, e lo si verifica sullo STATO
    #        risolto — non sul nome del codice.
    # Note: ⚠️ Fino al 2026-08-27 questo test confrontava `exception.code` con
    #        `E_ENTE_NON_TROVATO`, cioe' con la costante che il codice stesso
    #        legge: una tautologia, verde anche mentre il ripiego rispondeva
    #        **400**. Il nome del test prometteva un 404 che nessuna asserzione
    #        guardava. Lo stato lo decide la CLASSE del codice a catalogo, ed e'
    #        quello il fatto che questo test deve tenere fermo.
    def test_canale_inesistente_404(self):
        self.repo.get_ente_incasso.return_value = None
        with self.assertRaises(ServiceError) as ctx:
            enti_incasso_service.aggiorna_ente_incasso(999, {"descrizione": "x"})
        self.assertEqual(ctx.exception.code, enti_incasso_service.E_ENTE_NON_TROVATO)
        self.assertEqual(ErrorPolicyRegistry.resolve(ctx.exception.code).http_status, 404)


class ListaTests(_Base):
    def test_tipo_fuori_vocabolario_rifiutato(self):
        with self.assertRaises(ServiceError):
            enti_incasso_service.list_enti_incasso(tipo="CONTANTI")
        self.repo.list_enti_incasso.assert_not_called()

    def test_ordinamento_fuori_whitelist_rifiutato(self):
        with self.assertRaises(ServiceError):
            enti_incasso_service.list_enti_incasso(order_by="codice; DROP")
        self.repo.list_enti_incasso.assert_not_called()

    # Scopo: Un elenco di configurazione si legge in ordine alfabetico, non dal
    #        piu' recente: qui non c'e' una cronologia da scorrere.
    def test_default_per_codice_crescente(self):
        enti_incasso_service.list_enti_incasso()
        kwargs = self.repo.list_enti_incasso.call_args.kwargs
        self.assertEqual(kwargs["order_by"], "codice")
        self.assertEqual(kwargs["order_dir"], "asc")
