# ------------------------------------------------------------
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Contratto dell'hook `nomi_lista_dettaglio` (openapi_extensions.py):
#        la lista `/x/` prende `x_list` SOLO quando collide col suo dettaglio
#        `/x/{id}/`, e un nome che non si puo' dare senza inventarlo non si da'.
# Note: Lo schema e' un dizionario costruito a mano: l'hook lavora sul
#       risultato, non sulle view. Il comportamento sullo schema VERO lo tiene
#       `test_schema_openapi_registro.py` (le collisioni rimaste sono a registro).
# ------------------------------------------------------------
"""
Indice test (0..N):
 0. test_lista_e_dettaglio_in_collisione_si_separano
 1. test_senza_collisione_non_si_rinomina_niente
 2. test_un_nome_conteso_da_due_liste_non_si_assegna
 3. test_un_nome_gia_esistente_non_si_assegna
 4. test_solo_get_e_solo_parametro_finale
"""

from django.test import SimpleTestCase

from apps.core.api.openapi_extensions import nomi_lista_dettaglio


# Scopo: uno schema minimo da {percorso: {metodo: operationId}}.
def _schema(voci: dict[str, dict[str, str]]) -> dict:
    return {
        "paths": {
            percorso: {metodo: {"operationId": op} for metodo, op in metodi.items()}
            for percorso, metodi in voci.items()
        }
    }


# Scopo: rilegge {percorso: {metodo: operationId}} dallo schema.
def _nomi(schema: dict) -> dict[str, dict[str, str]]:
    return {
        percorso: {metodo: op["operationId"] for metodo, op in metodi.items()}
        for percorso, metodi in schema["paths"].items()
    }


class NomiListaDettaglioTest(SimpleTestCase):

    # Scopo: il caso per cui esiste — 51 coppie il 2026-09-26.
    def test_lista_e_dettaglio_in_collisione_si_separano(self):
        schema = _schema({
            "/api/v1/x/": {"get": "x_retrieve", "post": "x_create"},
            "/api/v1/x/{id}/": {"get": "x_retrieve", "delete": "x_destroy"},
        })
        self.assertEqual(_nomi(nomi_lista_dettaglio(schema)), {
            "/api/v1/x/": {"get": "x_list", "post": "x_create"},
            "/api/v1/x/{id}/": {"get": "x_retrieve", "delete": "x_destroy"},
        })

    # Scopo: una lista senza dettaglio, o un dettaglio con un nome suo, restano.
    def test_senza_collisione_non_si_rinomina_niente(self):
        voci = {
            "/api/v1/me/": {"get": "me_retrieve"},
            "/api/v1/y/": {"get": "y_retrieve"},
            "/api/v1/y/{id}/": {"get": "y_dettaglio"},
        }
        self.assertEqual(_nomi(nomi_lista_dettaglio(_schema(voci))), voci)

    # Scopo: `/t/`, `/t/{rel}/`, `/t/{rel}/{id}/` — due liste vorrebbero
    #        `t_list`: nessuna lo prende, la collisione resta e si vede.
    def test_un_nome_conteso_da_due_liste_non_si_assegna(self):
        voci = {
            "/api/v1/t/": {"get": "t_retrieve"},
            "/api/v1/t/{rel}/": {"get": "t_retrieve"},
            "/api/v1/t/{rel}/{id}/": {"get": "t_retrieve"},
        }
        self.assertEqual(_nomi(nomi_lista_dettaglio(_schema(voci))), voci)

    # Scopo: se `x_list` esiste gia' altrove, non si crea una seconda collisione.
    def test_un_nome_gia_esistente_non_si_assegna(self):
        voci = {
            "/api/v1/x/": {"get": "x_retrieve"},
            "/api/v1/x/{id}/": {"get": "x_retrieve"},
            "/api/v1/altro/": {"get": "x_list"},
        }
        self.assertEqual(_nomi(nomi_lista_dettaglio(_schema(voci))), voci)

    # Scopo: un parametro in MEZZO al percorso non fa un dettaglio
    #        (`/a/lookup/` contro `/a/{id}/lookup/`), e i metodi non GET non
    #        entrano nella regola.
    def test_solo_get_e_solo_parametro_finale(self):
        voci = {
            "/api/v1/a/lookup/": {"get": "a_lookup_retrieve"},
            "/api/v1/a/{id}/lookup/": {"get": "a_lookup_retrieve"},
            "/api/v1/b/": {"put": "b_update"},
            "/api/v1/b/{id}/": {"put": "b_update"},
        }
        self.assertEqual(_nomi(nomi_lista_dettaglio(_schema(voci))), voci)
