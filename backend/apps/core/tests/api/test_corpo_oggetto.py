# ------------------------------------------------------------
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Test del BB `corpo_oggetto` (F-9): il corpo di una richiesta DRF e'
#        un oggetto, o un 400 E_VALIDATION_INPUT nell'envelope — mai un 500,
#        mai un `{}` al posto del corpo sbagliato.
# ------------------------------------------------------------

"""
Indice test eseguiti:
1) test_oggetto_passa_com_e
2) test_form_passa
3) test_lista_rifiutata
4) test_lista_di_coppie_rifiutata
5) test_json_illeggibile_rifiutato
6) test_patch_con_lista_e_un_400_nell_envelope
7) test_patch_put_senza_modalita_forte_leggono_corpo_oggetto
8) test_nessuna_copia_del_corpo
"""

from unittest import TestCase

from rest_framework.parsers import FormParser, JSONParser
from rest_framework.request import Request
from rest_framework.test import APIRequestFactory

from apps.core.api.payload_validators import corpo_oggetto
from apps.core.services.service_errors import ServiceError


# Scopo: Una Request DRF col corpo dato (JSON grezzo o form).
def _richiesta(corpo: str, content_type: str = "application/json") -> Request:
    grezza = APIRequestFactory().post("/api/v1/x/", corpo, content_type=content_type)
    return Request(grezza, parsers=[JSONParser(), FormParser()])


class CorpoOggettoTests(TestCase):

    def test_oggetto_passa_com_e(self):
        self.assertEqual(corpo_oggetto(_richiesta('{"a": 1}')), {"a": 1})

    # Scopo: Un form (`QueryDict`) e' un dict: non si rifiuta.
    def test_form_passa(self):
        corpo = corpo_oggetto(_richiesta("a=1", "application/x-www-form-urlencoded"))
        self.assertEqual(corpo.get("a"), "1")

    def test_lista_rifiutata(self):
        with self.assertRaises(ServiceError) as ctx:
            corpo_oggetto(_richiesta("[1, 2]"))
        self.assertEqual(ctx.exception.code, "E_VALIDATION_INPUT")
        self.assertIn("oggetto JSON", ctx.exception.message)

    # Scopo: `dict([["refresh", "x"]])` diventava un oggetto, in silenzio.
    def test_lista_di_coppie_rifiutata(self):
        with self.assertRaises(ServiceError):
            corpo_oggetto(_richiesta('[["refresh", "x"]]'))

    def test_json_illeggibile_rifiutato(self):
        with self.assertRaises(ServiceError) as ctx:
            corpo_oggetto(_richiesta("{non json"))
        self.assertEqual(ctx.exception.code, "E_VALIDATION_INPUT")
        self.assertIn("JSON valido", ctx.exception.message)


class PatchCorpoListaTests(TestCase):

    # Scopo: F-9 dal percorso vero: PATCH di un articolo con una lista nel
    # corpo. Era un 500 (`request.data.get` su una lista). Il rifiuto arriva
    # PRIMA del servizio, quindi niente database.
    # ⚠️ Fino al 2026-09-28 il percorso vero era il logout: da quel giorno il
    #    logout non legge piu' il corpo (il refresh sta nel cookie, brief
    #    sicurezza §2), e il presidio si e' spostato su una view che lo legge.
    def test_patch_con_lista_e_un_400_nell_envelope(self):
        import uuid
        from unittest.mock import MagicMock

        from apps.catalogo.api.views import ApiArticoloDetail
        from apps.core.api.error_responses import exception_to_error_response

        request = _richiesta('[{"descrizione": "x"}]')
        request.user = MagicMock(id=1)
        with self.assertRaises(ServiceError) as ctx:
            ApiArticoloDetail().patch(request, uuid.uuid4())
        risposta = exception_to_error_response(ctx.exception)
        self.assertEqual(risposta.status_code, 400)
        self.assertIn(b"E_VALIDATION_INPUT", risposta.content)


class DialettoPatchPutTests(TestCase):

    # Scopo: ⛔ Una regola, un modo (Tid, 2026-10-25, api.md §«Quando usare
    # handle_post_json»): una PATCH/PUT legge il corpo con `corpo_oggetto`;
    # `handle_post_json` solo con la modalita' forte. Fino a quel giorno 16
    # view parlavano l'altro dialetto (e `handle_detail_patch`, ritirato).
    # ⚠️ Il presidio legge il CODICE: una view nuova scritta col vecchio
    #    dialetto funziona uguale, e la copia rientrerebbe senza errore.
    def test_patch_put_senza_modalita_forte_leggono_corpo_oggetto(self):
        import ast
        from pathlib import Path

        apps = Path(__file__).resolve().parents[3]
        trovate = []
        for f in apps.rglob("*.py"):
            if "tests" in f.parts:
                continue
            sorgente = f.read_text(errors="ignore")
            for nodo in ast.walk(ast.parse(sorgente)):
                if not (isinstance(nodo, ast.FunctionDef) and nodo.name in ("patch", "put")):
                    continue
                for chiamata in ast.walk(nodo):
                    if (
                        isinstance(chiamata, ast.Call)
                        and getattr(chiamata.func, "id", None) == "handle_post_json"
                        and not any(
                            k.arg == "require_idempotency_key"
                            and isinstance(k.value, ast.Constant) and k.value.value is True
                            for k in chiamata.keywords
                        )
                    ):
                        trovate.append(f"{f.relative_to(apps)}:{chiamata.lineno}")
        self.assertEqual(trovate, [])

    # ⛔ `corpo_oggetto` restituisce gia' un dict: `dict(corpo_oggetto(...))` e'
    #    una seconda forma della stessa riga (ritirata il 2026-10-25, 30 copie,
    #    ok Tid). Unica eccezione: il corpo multipart degli asset, dove `dict()`
    #    su un `QueryDict` serve a tenere le liste di valori.
    def test_nessuna_copia_del_corpo(self):
        import re
        from pathlib import Path

        apps = Path(__file__).resolve().parents[3]
        copia = re.compile(r"dict\(corpo_oggetto\(")
        ammessi = {"documenti/api/views.py"}
        trovate = [
            f"{f.relative_to(apps)}:{n}"
            for f in apps.rglob("*.py")
            if "tests" not in f.parts
            for n, riga in enumerate(f.read_text(errors="ignore").splitlines(), 1)
            if copia.search(riga) and str(f.relative_to(apps)) not in ammessi
        ]
        self.assertEqual(trovate, [])
