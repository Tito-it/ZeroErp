# ------------------------------------------------------------
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Test del cancello di perimetro emittente montato su `DomainAPIView`
#        via l'attributo dichiarativo `lista_codice`.
# Tutti i test usano mock — nessuna dipendenza da DB reale (CI-compatible).
#
# ⚠️ Perche' il cancello sta sulla BASE VIEW e non dentro ogni `get`: e' la
#        stessa forma di `area_funzionale` e `post_permission` — la view
#        dichiara COSA SERVE, non cosa controllare. La forma alternativa (una
#        chiamata riga per riga in ogni endpoint) e' quella che qualcuno
#        dimentica alla settima lista, e una regola che si dimentica non e' un
#        presidio.
#
# ⚠️ E il cancello lato server non e' ridondante rispetto al pannello a video:
#        un pannello nel browser non protegge niente, lo salta chiunque chiami
#        l'API direttamente.
# ------------------------------------------------------------

"""
Indice test eseguiti:
 1) view_senza_lista_codice_non_chiama_il_guard  — l'attributo e' inerte se None
 2) view_con_lista_codice_chiama_il_guard        — e passa il codice dichiarato
 3) rifiuto_del_guard_non_viene_inghiottito      — l'errore arriva al chiamante
 4) utente_anonimo_non_chiama_il_guard           — prima viene l'autenticazione
 5) il_guard_precede_il_metodo_http              — nessun dato servito se rifiuta
 6) vale_anche_per_il_post                       — non solo per le letture
"""

from contextlib import ExitStack, contextmanager
from unittest import TestCase
from unittest.mock import MagicMock, patch

from rest_framework.test import APIRequestFactory, force_authenticate

from apps.core.api.base_views import DomainAPIView
from apps.core.services.service_errors import ServiceError

_GUARD = "apps.core.api.base_views.perimetro_emittente.guard_lista_per_codice"


class _ViewSenzaLista(DomainAPIView):
    area_funzionale = "vendite"


class _ViewConLista(DomainAPIView):
    area_funzionale = "vendite"
    lista_codice = "vendite.dash_competenza_gruppi"


# Scopo: neutralizza i pezzi di `APIView.initial()` che non c'entrano col
#        cancello — autenticazione, permessi, throttling, versione e
#        negoziazione del contenuto — lasciando in piedi SOLO cio' che si vuole
#        verificare.
# ⚠️ Scritto una volta e riusato: il primo giro lo aveva ricopiato in tre
#        punti, e una catena di patch duplicata e' esattamente il posto in cui
#        due test smettono di provare la stessa cosa senza che si veda.
@contextmanager
def _catena_drf_neutralizzata():
    with ExitStack() as stack:
        for metodo, ritorno in (
            ("perform_authentication", None),
            ("check_permissions", None),
            ("check_throttles", None),
            ("determine_version", (None, None)),
            ("perform_content_negotiation", (MagicMock(), MagicMock())),
        ):
            stack.enter_context(
                patch.object(DomainAPIView, metodo, return_value=ritorno)
            )
        yield


# Scopo: costruisce una request finta con l'identita' richiesta.
def _request(*, autenticato=True, metodo="GET"):
    request = MagicMock()
    request.method = metodo
    request.user = MagicMock()
    request.user.is_authenticated = autenticato
    return request


# Scopo: invoca `initial()` — il punto della catena DRF in cui il cancello vive:
#        autenticazione e permessi sono gia' risolti, nessun `get`/`post` e'
#        ancora partito.
def _esegui_initial(view_class, *, autenticato=True, metodo="GET"):
    request = _request(autenticato=autenticato, metodo=metodo)
    with _catena_drf_neutralizzata():
        view_class().initial(request)
    return request


class BaseViewPerimetroEmittenteTests(TestCase):
    @patch(_GUARD)
    def test_view_senza_lista_codice_non_chiama_il_guard(self, mock_guard) -> None:
        """L'attributo e' additivo e INERTE: le view che non lo dichiarano
        (cioe' quasi tutte) non pagano nemmeno una chiamata."""
        _esegui_initial(_ViewSenzaLista)
        mock_guard.assert_not_called()

    @patch(_GUARD)
    def test_view_con_lista_codice_chiama_il_guard(self, mock_guard) -> None:
        request = _esegui_initial(_ViewConLista)
        mock_guard.assert_called_once_with(
            user=request.user,
            lista_codice="vendite.dash_competenza_gruppi",
        )

    @patch(_GUARD, side_effect=ServiceError(
        code="E_UI_LISTA_EMITTENTE_DA_SCEGLIERE", message="scegli un emittente",
    ))
    def test_rifiuto_del_guard_non_viene_inghiottito(self, _mock_guard) -> None:
        """⚠️ L'errore deve USCIRE da `initial()`.

        Se una futura `try/except` lo assorbisse, il cancello resterebbe in
        piedi nel codice e spento nei fatti — e nessun test lo direbbe, perche'
        la richiesta continuerebbe a rispondere 200.
        """
        with self.assertRaises(ServiceError) as ctx:
            _esegui_initial(_ViewConLista)
        self.assertEqual(ctx.exception.code, "E_UI_LISTA_EMITTENTE_DA_SCEGLIERE")

    @patch(_GUARD)
    def test_utente_anonimo_non_chiama_il_guard(self, mock_guard) -> None:
        """Senza identita' non c'e' scope da risolvere.

        La richiesta e' comunque gia' stata respinta dalla catena permessi:
        chiamare il guard qui produrrebbe solo una query inutile su un utente
        che non esiste.
        """
        _esegui_initial(_ViewConLista, autenticato=False)
        mock_guard.assert_not_called()

    @patch(_GUARD, side_effect=ServiceError(
        code="E_UI_LISTA_EMITTENTE_DA_SCEGLIERE", message="scegli un emittente",
    ))
    def test_il_guard_precede_il_metodo_http(self, _mock_guard) -> None:
        """⭐ Il punto dell'intero cancello: nessun dato deve essere servito.

        ⚠️ Si esercita `dispatch()`, cioe' la CATENA VERA, e non `initial()`
        seguito da una chiamata a mano: un test che invoca i due passi in
        sequenza dimostra soltanto che il primo solleva prima del secondo —
        cosa che sarebbe vera anche se `dispatch` non li chiamasse in
        quell'ordine. Qui il `get` e' raggiungibile davvero, e non viene
        raggiunto.
        """
        chiamate: list[str] = []

        class _View(DomainAPIView):
            area_funzionale = "vendite"
            lista_codice = "vendite.dash_competenza_gruppi"

            def get(self, request):  # pragma: no cover - non deve girare
                chiamate.append("get")
                return MagicMock()

        # ⚠️ `dispatch` pretende una HttpRequest vera (DRF la wrappa): il
        #    MagicMock usato dagli altri test qui non basta, e va bene cosi' —
        #    e' il prezzo per esercitare la catena invece di simularla.
        request = APIRequestFactory().get("/api/v1/vendite/x/")
        force_authenticate(request, user=MagicMock(is_authenticated=True))
        with _catena_drf_neutralizzata():
            # DRF ri-solleva cio' che non sa tradurre: `ServiceError` esce da
            # `dispatch` e la traduzione in envelope 422 la fa il middleware,
            # che qui non e' in catena.
            with self.assertRaises(ServiceError):
                _View().dispatch(request)
        self.assertEqual(
            chiamate, [],
            "il metodo HTTP e' stato eseguito nonostante il rifiuto del cancello",
        )

    @patch(_GUARD)
    def test_vale_anche_per_il_post(self, mock_guard) -> None:
        """Non solo letture: un endpoint di lista che espone un'azione massiva
        la eseguirebbe sullo STESSO perimetro ambiguo che si rifiuta di
        mostrare."""
        _esegui_initial(_ViewConLista, metodo="POST")
        mock_guard.assert_called_once()
