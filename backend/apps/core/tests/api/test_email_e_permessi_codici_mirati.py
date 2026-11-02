# ------------------------------------------------------------
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: I codici mirati di brief-db-codici-non-trovato-email-e-permessi
#        (R-1, R-2): i «non trovato» dell'email dell'operatore escono col
#        codice dell'entita' (404) invece di `E_EMAIL_OP` (400), il file perso
#        sullo storage e' un guasto (500), e le tre permission «riservate»
#        portano il loro codice fino all'envelope invece di
#        `E_PERMISSION_DENIED`.
# Note: Repository e resolver mockati, nessun DB. Le permission si provano sul
#       percorso DRF intero (permission → `PermissionDenied` →
#       `drf_exception_handler`), non sul solo attributo `code`.
# ------------------------------------------------------------

"""
Indice test eseguiti:
1) test_bozza_inesistente_e_404_dalle_letture — dettaglio e lista allegati → E_EMAIL_BOZZA_NOT_FOUND
2) test_le_view_dei_verbi_non_rileggono_la_bozza — modifica/invio/annullo/upload: la lettura e' del service
3) test_allegato_inesistente_e_404 — download e rimozione → E_EMAIL_ALLEGATO_NOT_FOUND
4) test_file_dell_allegato_perso_e_500 — riga presente, file assente → E_EMAIL_ALLEGATO_FILE_MANCANTE
5) test_le_permission_riservate_portano_il_codice_nell_envelope — admin, portale, shop → 403 col codice mirato
6) test_bozza_senza_azienda_attiva_e_emittente_non_risolto — «Tutti gli emittenti» → 400 E_EMITTENTE_NON_RISOLTO, nessuna bozza
"""

import json
import tempfile
from contextlib import contextmanager
from unittest.mock import MagicMock, patch

from django.test import SimpleTestCase, override_settings
from rest_framework.response import Response
from rest_framework.test import APIRequestFactory, force_authenticate
from rest_framework.views import APIView

from apps.core.api.email_views import (
    EmailAllegatoDeleteView,
    EmailAllegatoDownloadView,
    EmailAllegatoListView,
    EmailAllegatoUploadView,
    EmailOutboxCancelView,
    EmailOutboxDetailView,
    EmailOutboxSendView,
    EmailPrepareView,
)
from apps.core.api.permissions import IsAdminZeroERP, PortaleBasePermission, ShopBasePermission
from apps.core.services.error_manager import ServiceError
from apps.core.services.error_policies import ErrorPolicyRegistry

_REPO_VIEW = "apps.core.api.email_views.EmailRepository"
_REPO_SERVICE = "apps.core.services.email_outbox_service.EmailRepository"
_SERVICE_VIEW = "apps.core.api.email_views.EmailOutboxService"


# Scopo: La view senza il cancello dei permessi: qui si prova cosa risponde
#        dopo, non chi entra.
def _view(cls):
    view = cls()
    view.check_permissions = MagicMock()
    return view


class EmailOperatoreNonTrovatoTests(SimpleTestCase):

    def _richiesta(self) -> MagicMock:
        request = MagicMock()
        request.query_params = {}
        return request

    # Scopo: Le due letture senza verbo passano da `get_bozza`: 404 col codice
    #        della bozza, non il 400 di `E_EMAIL_OP`.
    @patch("apps.core.services.email_outbox_service.EmailDispatchService")
    @patch(_REPO_SERVICE)
    def test_bozza_inesistente_e_404_dalle_letture(self, mock_repo, _dispatch):
        mock_repo.return_value.get_outbox.return_value = None
        letture = {
            "dettaglio": lambda: _view(EmailOutboxDetailView).get(self._richiesta(), 9),
            "lista_allegati": lambda: _view(EmailAllegatoListView).get(self._richiesta(), 9),
        }
        for nome, chiama in letture.items():
            with self.subTest(lettura=nome):
                with self.assertRaises(ServiceError) as ctx:
                    chiama()
                self.assertEqual(ctx.exception.code, "E_EMAIL_BOZZA_NOT_FOUND")
                self.assertEqual(
                    ErrorPolicyRegistry.resolve(ctx.exception.code).http_status, 404,
                )

    # Scopo: ⛔ Le view dei verbi non leggono la bozza: il controllo e' del
    #        verbo del service (`get_bozza`), e una seconda lettura nella view
    #        sarebbe una seconda copia della regola (regola del 2, 2026-10-09).
    @patch(_SERVICE_VIEW)
    @patch(_REPO_VIEW)
    def test_le_view_dei_verbi_non_rileggono_la_bozza(self, mock_repo, mock_service):
        service = mock_service.return_value
        service.update_draft.return_value = {}
        service.confirm_and_send.return_value = {}
        service.cancel_draft.return_value = {}
        service.add_attachment.return_value = {}

        modifica = self._richiesta()
        modifica.data = {"oggetto": "x"}
        _view(EmailOutboxDetailView).patch(modifica, 9)
        _view(EmailOutboxSendView).post(self._richiesta(), 9)
        _view(EmailOutboxCancelView).post(self._richiesta(), 9)
        upload = self._richiesta()
        upload.FILES = {"file": MagicMock(name="f", content_type="application/pdf")}
        _view(EmailAllegatoUploadView).post(upload, 9)

        mock_repo.return_value.get_outbox.assert_not_called()
        service.get_bozza.assert_not_called()
        service.update_draft.assert_called_once()
        service.confirm_and_send.assert_called_once_with(9)
        service.cancel_draft.assert_called_once_with(9)
        service.add_attachment.assert_called_once()

    # Scopo: Allegato inesistente (o fuori perimetro: la stessa risposta) →
    #        404 dalla sede unica, e la rimozione non tocca niente.
    @patch(_SERVICE_VIEW)
    @patch(_REPO_VIEW)
    def test_allegato_inesistente_e_404(self, mock_repo, mock_service):
        mock_repo.return_value.get_allegato.return_value = None
        verbi = {
            "download": lambda: _view(EmailAllegatoDownloadView).get(self._richiesta(), 9),
            "rimozione": lambda: _view(EmailAllegatoDeleteView).delete(self._richiesta(), 9),
        }
        for nome, chiama in verbi.items():
            with self.subTest(verbo=nome):
                with self.assertRaises(ServiceError) as ctx:
                    chiama()
                self.assertEqual(ctx.exception.code, "E_EMAIL_ALLEGATO_NOT_FOUND")
                self.assertEqual(
                    ErrorPolicyRegistry.resolve(ctx.exception.code).http_status, 404,
                )
        mock_service.return_value.remove_attachment.assert_not_called()

    # Scopo: La riga c'e', il file sullo storage no: e' un guasto, 500 — un 404
    #        manderebbe l'operatore a cercare un allegato che per lui esiste.
    @patch(_REPO_VIEW)
    def test_file_dell_allegato_perso_e_500(self, mock_repo):
        with tempfile.TemporaryDirectory() as radice:
            mock_repo.return_value.get_allegato.return_value = {
                "id": 9, "file_path": "2026/10/perso.pdf",
                "mime_type": "application/pdf", "nome_file": "perso.pdf",
            }
            with override_settings(EMAIL_ATTACHMENTS_ROOT=radice):
                with self.assertRaises(ServiceError) as ctx:
                    _view(EmailAllegatoDownloadView).get(self._richiesta(), 9)
        self.assertEqual(ctx.exception.code, "E_EMAIL_ALLEGATO_FILE_MANCANTE")
        self.assertEqual(ErrorPolicyRegistry.resolve(ctx.exception.code).http_status, 500)

    # Scopo: Senza azienda attiva (modalita' «Tutti gli emittenti»: nessun
    #        claim) una bozza che non e' di sistema si rifiuta col codice del
    #        catalogo per questa condizione — lo stesso di ordini e contratti —
    #        e non arriva al service.
    @patch(_SERVICE_VIEW)
    def test_bozza_senza_azienda_attiva_e_emittente_non_risolto(self, mock_service):
        request = MagicMock()
        request.method = "POST"
        request.auth = None
        request.user = MagicMock(id=5)
        request.body = json.dumps({
            "codice_template": "T", "destinatario": "a@b.it", "ambito": "OPERATORE",
        }).encode("utf-8")

        response = _view(EmailPrepareView).post(request)

        self.assertEqual(response.status_code, 400)
        self.assertEqual(json.loads(response.content)["error"]["code"], "E_EMITTENTE_NON_RISOLTO")
        mock_service.return_value.prepare_draft.assert_not_called()


@contextmanager
def _cache_vuota(_request):
    yield {}


class PermissionRiservateTests(SimpleTestCase):

    # Scopo: Il percorso intero: la permission nega, DRF solleva
    #        `PermissionDenied(code=…)`, l'handler del progetto scrive
    #        l'envelope. 403 col codice mirato e il messaggio della SUA policy.
    @patch("apps.core.api.permissions.cache_permessi_richiesta", _cache_vuota)
    @patch("apps.core.api.permissions.PermissionResolver")
    def test_le_permission_riservate_portano_il_codice_nell_envelope(self, mock_resolver):
        mock_resolver.is_super_admin.return_value = False
        # Una veste che non e' ne' portale ne' shop: tutte e tre negano.
        mock_resolver.get_ruolo_applicativo.return_value = "OPERATORE"
        casi = {
            IsAdminZeroERP: "E_ACCESSO_RISERVATO_ADMIN",
            PortaleBasePermission: "E_ACCESSO_RISERVATO_PORTALE",
            ShopBasePermission: "E_ACCESSO_RISERVATO_SHOP",
        }
        user = MagicMock(id=5, is_authenticated=True, is_superuser=False)
        for permission, codice in casi.items():
            with self.subTest(permission=permission.__name__):

                class _Porta(APIView):
                    permission_classes = [permission]
                    authentication_classes: list = []
                    throttle_classes: list = []

                    def get(self, request):
                        return Response({})

                request = APIRequestFactory().get("/porta/")
                force_authenticate(request, user=user)
                response = _Porta.as_view()(request)

                self.assertEqual(response.status_code, 403)
                errore = response.data["error"]
                self.assertEqual(errore["code"], codice)
                self.assertEqual(
                    errore["message"], ErrorPolicyRegistry.resolve(codice).user_message,
                )
                json.dumps(response.data)  # l'envelope e' serializzabile
