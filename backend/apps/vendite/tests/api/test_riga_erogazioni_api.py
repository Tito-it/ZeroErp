# ------------------------------------------------------------
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: la lettura «come si puo' erogare questo articolo su una riga» di
#        contratto e offerta (`GET contratti/<id>/righe/erogazioni/`,
#        `GET offerte/<id>/righe/erogazioni/`) e i due service che la servono
#        (brief-db-offerta-emissione-ed-erogazione B-R4, 2026-10-07). Mock di
#        repository e service: nessun accesso DB (CI-compatible).
# ------------------------------------------------------------

"""⛔ PERCHE' QUESTO FILE ESISTE.

Il form delle righe legge `data.results` (envelope dei lookup): una lista nuda
farebbe sparire le tendine senza nessun errore (api.md §«L'envelope di un
lookup»). E il service legge PRIMA la testata: la funzione del DB, su un
documento che l'operatore non vede, risponde zero righe — cioe' «l'articolo non
si vende qui» invece di «non lo vedi».
⭐ Contratto e offerta girano gli STESSI test (classe base): sono due
dichiarazioni della stessa base `RigaErogazioniView`.

Indice test (contratto e offerta, ciascuno):

 1) test_risponde_con_l_envelope_results_e_passa_il_documento_del_percorso
 2) test_col_permesso_del_documento
 3) test_service_fuori_perimetro_404_senza_leggere_le_combinazioni
 4) test_service_articolo_non_uuid_e_un_400_col_campo
 5) test_service_legge_col_selettore_del_documento
"""

from unittest import TestCase
from unittest.mock import Mock, patch

from django.core.cache import cache
from django.test import Client
from django.urls import resolve

from apps.core.services.service_errors import ServiceError
from apps.core.tests._helpers.jwt_mock import JwtMockedApiTest
from apps.vendite.services.contratti_service import ContrattiService
from apps.vendite.services.offerte_service import OfferteService

_AUTH = "rest_framework_simplejwt.authentication.JWTAuthentication.authenticate"
_ARTICOLO = "019d5449-3dd2-7301-afeb-057b60c5b791"
_COMBINAZIONE = {
    "tipo_erogazione": "UNA_TANTUM", "fonte_quantita_attesa": "FISSA",
    "e_default": True, "origine": "TIPOLOGIA",
}


class _RigaErogazioniApiBase:
    """I test di view comuni; le sottoclassi dicono service, percorso e permesso."""

    service: str
    base: str
    model_permission: tuple[str, str]

    def setUp(self) -> None:
        super().setUp()  # type: ignore[misc]  # il TestCase della sottoclasse
        self.client = Client()
        cache.clear()

    def test_risponde_con_l_envelope_results_e_passa_il_documento_del_percorso(self) -> None:
        with patch(_AUTH, return_value=(Mock(), None)), patch(self.service) as svc:
            svc.return_value.list_erogazioni_riga.return_value = [_COMBINAZIONE]
            resp = self.client.get(f"{self.base}?articolo_id={_ARTICOLO}")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json()["data"], {"results": [_COMBINAZIONE]})
        svc.return_value.list_erogazioni_riga.assert_called_once_with(42, _ARTICOLO)

    def test_col_permesso_del_documento(self) -> None:
        view = resolve(self.base).func.view_class
        self.assertEqual(view.model_permission, self.model_permission)


class TestContrattoRigaErogazioniApi(_RigaErogazioniApiBase, JwtMockedApiTest):
    service = "apps.vendite.api.views_contratti.ContrattiService"
    base = "/api/v1/vendite/contratti/42/righe/erogazioni/"
    model_permission = ("vendite", "contratto")


class TestOffertaRigaErogazioniApi(_RigaErogazioniApiBase, JwtMockedApiTest):
    service = "apps.vendite.api.views_offerte.OfferteService"
    base = "/api/v1/vendite/offerte/42/righe/erogazioni/"
    model_permission = ("vendite", "offerta_commerciale")


class _RigaErogazioniServiceBase:
    """I test di service comuni; le sottoclassi dicono modulo, service e selettore."""

    modulo: str
    repository: str
    documento: str

    def _service(self):  # pragma: no cover - sovrascritto
        raise NotImplementedError

    def test_service_fuori_perimetro_404_senza_leggere_le_combinazioni(self) -> None:
        with patch(f"{self.modulo}.{self.repository}") as repo, \
                patch(f"{self.modulo}.list_erogazioni_riga") as lettura:
            repo.return_value.get_stato_codice.return_value = None
            with self.assertRaises(ServiceError) as ctx:  # type: ignore[attr-defined]
                self._service().list_erogazioni_riga(42, _ARTICOLO)
        self.assertEqual(ctx.exception.code, "E_VENDITE_NOT_FOUND")  # type: ignore[attr-defined]
        lettura.assert_not_called()

    def test_service_articolo_non_uuid_e_un_400_col_campo(self) -> None:
        with patch(f"{self.modulo}.{self.repository}"), \
                patch(f"{self.modulo}.list_erogazioni_riga") as lettura:
            for valore in (None, "non-un-uuid"):
                with self.subTest(articolo_id=valore):  # type: ignore[attr-defined]
                    with self.assertRaises(ServiceError) as ctx:  # type: ignore[attr-defined]
                        self._service().list_erogazioni_riga(42, valore)
                    self.assertEqual(ctx.exception.code, "E_VENDITE_VALIDATION")  # type: ignore[attr-defined]
                    self.assertEqual(ctx.exception.context.get("field"), "articolo_id")  # type: ignore[attr-defined]
        lettura.assert_not_called()

    def test_service_legge_col_selettore_del_documento(self) -> None:
        with patch(f"{self.modulo}.{self.repository}") as repo, \
                patch(f"{self.modulo}.list_erogazioni_riga") as lettura:
            repo.return_value.get_stato_codice.return_value = "BOZZA"
            lettura.return_value = [_COMBINAZIONE]
            esito = self._service().list_erogazioni_riga(42, _ARTICOLO.upper())
        self.assertEqual(esito, [_COMBINAZIONE])  # type: ignore[attr-defined]
        lettura.assert_called_once_with(self.documento, 42, _ARTICOLO)


class ContrattoRigaErogazioniServiceTests(_RigaErogazioniServiceBase, TestCase):
    modulo = "apps.vendite.services.contratti_service"
    repository = "ContrattiRepository"
    documento = "CONTRATTO"

    def _service(self):
        return ContrattiService()


class OffertaRigaErogazioniServiceTests(_RigaErogazioniServiceBase, TestCase):
    modulo = "apps.vendite.services.offerte_service"
    repository = "OfferteRepository"
    documento = "OFFERTA_COMMERCIALE"

    def _service(self):
        return OfferteService()
