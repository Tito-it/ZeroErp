# ------------------------------------------------------------
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Cricchetto sui rilievi di drf-spectacular — lo schema OpenAPI che
#        descrive l'API a chi la consuma (Swagger, integratori, portali).
#        Due difetti che non danno nessun errore all'applicazione:
#
#        - W002, «non so cosa entra e cosa esce»: la view non dichiara il
#          serializer (`@extend_schema`), e nello schema l'endpoint c'e' ma e'
#          VUOTO. Viola la regola di `api.md` §Test («ogni APIView ha
#          `@extend_schema` su ogni metodo»).
#        - W001, «due endpoint con lo stesso nome»: due operazioni sullo stesso
#          `operationId`, e drf-spectacular aggiunge `_2` alla seconda in ordine
#          ALFABETICO di percorso — un nome che dice un numero, e che si sposta
#          se un percorso nuovo si ordina in mezzo. Le coppie lista/dettaglio le
#          separa l'hook `nomi_lista_dettaglio` (openapi_extensions.py): qui
#          arrivano solo le collisioni che una regola non sa nominare.
#
#        I rilievi di oggi stanno in `openapi_schema.baseline.json`, PER NOME
#        (view e operationId), non per conto: un conto resta uguale quando una
#        view viene sanata e un'altra si rompe. Il registro e' a cricchetto:
#        rosso se entra un nome nuovo, rosso anche se un nome esce senza che
#        la riga venga tolta — un registro che non cala smette di essere un
#        debito e diventa il posto in cui si mettono le cose per farle passare.
#
# Note: ⭐ Nato il 2026-09-26 (registro migliorie BE/FE, D3-b): il passo CI
#       `check --deploy` gira `--tag security` e non vede drf-spectacular, e il
#       registro senza verso era cresciuto da 66 a 73 W002 in due settimane.
#       ⭐ Lo schema si genera in memoria come fa il check di drf-spectacular
#       (`drf_spectacular.checks.schema_check`), senza DB — e comprese le rotte
#       di `ROTTE_CONDIZIONALI` a flag spenta: in CI l'AI e' spenta, e una view
#       AI nuova senza schema resterebbe invisibile proprio dove si presidia.
#       ⚠️ `GENERATOR_STATS` e' uno stato GLOBALE del modulo: si azzera prima
#       e dopo, o i rilievi di una generazione precedente entrano nel conto.
#       ⚠️ Limite dichiarato: drf-spectacular emette il W002 per VIEW, non per
#       metodo, e basta un metodo senza request o response dichiarati. Una
#       view gia' nel registro puo' quindi peggiorare su un altro metodo
#       senza che questo test lo veda: e' protetta per intero solo dal giorno
#       in cui esce dal registro. (Scoperto provandolo per mutazione:
#       `ChangePasswordView` ha `@extend_schema` ma non il corpo della POST,
#       e togliere il decoratore non cambiava niente.)
# ------------------------------------------------------------
"""
Indice test (0..N):
 0. test_lo_schema_comprende_le_rotte_condizionali
 1. test_nessun_rilievo_di_forma_sconosciuta
 2. test_nessuna_view_senza_serializer_fuori_registro
 3. test_nessuna_collisione_di_operation_id_fuori_registro
 4. test_il_registro_cala_quando_una_voce_e_sanata
"""

from __future__ import annotations

import importlib
import json
import re
from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path

from django.conf import settings
from django.test import SimpleTestCase
from django.urls import get_resolver, include, path
from drf_spectacular.drainage import GENERATOR_STATS
from drf_spectacular.settings import spectacular_settings

_REGISTRO = Path(__file__).with_name("openapi_schema.baseline.json")

# Le due forme di messaggio che drf-spectacular emette oggi. Un messaggio che
# non ha nessuna delle due e' una forma NUOVA: tolleranza zero (test 1).
_RE_SENZA_SERIALIZER = re.compile(
    r"^(?P<file>\S+?): Error \[(?P<view>\w+)\]: unable to guess serializer\."
)
_RE_COLLISIONE = re.compile(r'^Warning: operationId "(?P<op>[^"]+)" has collisions ')


# Scopo: i rilievi di una generazione dello schema, gia' ridotti a NOMI.
@dataclass
class Rilievi:
    senza_serializer: set[str] = field(default_factory=set)
    collisioni: set[str] = field(default_factory=set)
    sconosciuti: list[str] = field(default_factory=list)
    percorsi: set[str] = field(default_factory=set)


# Scopo: i pattern dell'URLconf radice piu' le rotte condizionali a flag
#        spenta, montate con lo stesso prefisso con cui `urls.py` le monta.
def _pattern_con_rotte_condizionali() -> list:
    radice = importlib.import_module(settings.ROOT_URLCONF)
    patterns = list(get_resolver().url_patterns)
    for prefisso, urlconf, flag in getattr(radice, "ROTTE_CONDIZIONALI", ()):
        if not getattr(settings, flag, False):
            patterns.append(path(prefisso, include(urlconf)))
    return patterns


# Scopo: nome stabile di una view senza serializer — file relativo a
#        `backend/` + classe (il file assoluto cambia da macchina a macchina).
def _nome_view(file: str, view: str) -> str:
    try:
        file = Path(file).resolve().relative_to(settings.BASE_DIR).as_posix()
    except ValueError:
        pass
    return f"{file}:{view}"


# Scopo: genera lo schema una volta e classifica ogni rilievo per forma.
@lru_cache(maxsize=1)
def rilievi_dello_schema() -> Rilievi:
    GENERATOR_STATS.reset()
    try:
        with GENERATOR_STATS.silence():
            schema = spectacular_settings.DEFAULT_GENERATOR_CLASS(
                patterns=_pattern_con_rotte_condizionali(),
            ).get_schema(request=None, public=True)
        messaggi = list(GENERATOR_STATS._warn_cache) + list(GENERATOR_STATS._error_cache)
    finally:
        GENERATOR_STATS.reset()

    rilievi = Rilievi(percorsi=set(schema.get("paths", {})))
    for messaggio in messaggi:
        if m := _RE_SENZA_SERIALIZER.match(messaggio):
            rilievi.senza_serializer.add(_nome_view(m["file"], m["view"]))
        elif m := _RE_COLLISIONE.match(messaggio):
            rilievi.collisioni.add(m["op"])
        else:
            rilievi.sconosciuti.append(messaggio)
    return rilievi


# Scopo: il registro dei rilievi ammessi, come insiemi di nomi.
def _registro() -> tuple[set[str], set[str]]:
    dati = json.loads(_REGISTRO.read_text(encoding="utf-8"))
    return set(dati["senza_serializer"]), set(dati["operation_id_in_collisione"])


class SchemaOpenApiRegistroTest(SimpleTestCase):

    # Scopo: prova che la scansione guarda anche le rotte a flag spenta —
    #        altrimenti i test sotto sarebbero verdi per sottrazione.
    def test_lo_schema_comprende_le_rotte_condizionali(self):
        percorsi = rilievi_dello_schema().percorsi
        self.assertTrue(
            any(p.startswith("/api/v1/ai-assistant/") for p in percorsi),
            "Lo schema non contiene le rotte dell'assistente AI: la scansione "
            "non monta ROTTE_CONDIZIONALI e presidia meno di quanto dichiara.",
        )

    # Scopo: un rilievo che non e' ne' un W002 «senza serializer» ne' una
    #        collisione e' una forma nuova: oggi sono zero, e restano zero.
    def test_nessun_rilievo_di_forma_sconosciuta(self):
        sconosciuti = rilievi_dello_schema().sconosciuti
        self.assertEqual(
            sconosciuti, [],
            "drf-spectacular segnala rilievi di una forma che il registro non "
            "conosce: vanno sanati, non registrati.\n  " + "\n  ".join(sconosciuti),
        )

    # Scopo: una view nuova senza serializer dichiarato non entra.
    def test_nessuna_view_senza_serializer_fuori_registro(self):
        ammesse, _ = _registro()
        nuove = sorted(rilievi_dello_schema().senza_serializer - ammesse)
        self.assertEqual(
            nuove, [],
            "View senza serializer nello schema OpenAPI (drf_spectacular.W002): "
            "dichiarare `@extend_schema(request=..., responses=...)` su ogni "
            "metodo HTTP. Non si aggiungono al registro.\n  " + "\n  ".join(nuove),
        )

    # Scopo: una collisione nuova di operationId non entra.
    def test_nessuna_collisione_di_operation_id_fuori_registro(self):
        _, ammesse = _registro()
        nuove = sorted(rilievi_dello_schema().collisioni - ammesse)
        self.assertEqual(
            nuove, [],
            "operationId in collisione nello schema OpenAPI "
            "(drf_spectacular.W001), che l'hook lista/dettaglio non risolve: "
            "dare a una delle due `@extend_schema(operation_id=...)` esplicito. "
            "Non si aggiungono "
            "al registro.\n  " + "\n  ".join(nuove),
        )

    # Scopo: chi sana una voce toglie la sua riga — il registro scende davvero.
    def test_il_registro_cala_quando_una_voce_e_sanata(self):
        view_ammesse, op_ammessi = _registro()
        rilievi = rilievi_dello_schema()
        sanate = sorted(view_ammesse - rilievi.senza_serializer) + sorted(
            op_ammessi - rilievi.collisioni
        )
        self.assertEqual(
            sanate, [],
            f"Voci del registro che lo schema non segnala piu': toglierle da "
            f"{_REGISTRO.name}.\n  " + "\n  ".join(sanate),
        )
