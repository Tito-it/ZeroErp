# ------------------------------------------------------------
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Presidio del CABLAGGIO della ristampa fedele sui 6 domini sorgente
#        (brief-ristampa-fedele-documenti, 2026-08-03).
#
#        Perche' un test dedicato invece di fidarsi della factory: le view
#        vengono da `build_documenti_sorgente_views`, ma l'export nel modulo
#        di dominio e la `path()` nel file urls sono **scritti a mano, sei
#        volte**. Una dimenticanza non rompe nulla — semplicemente quella
#        sorgente non ha la ristampa, e ce ne accorgeremmo solo il giorno in
#        cui serve, su un documento che non si puo' piu' riprodurre. E' il
#        tipo di buco che il brief stesso descrive: il modello mantiene la
#        promessa, manca chi la esercita.
#
#        Non usa il DB: `reverse()` interroga la sola tabella delle rotte.
#
# Indice test (0..N):
#   0. ristampa_cablata_su_tutti_i_domini
#   1. ristampa_url_coerente_col_pattern_di_famiglia
# ------------------------------------------------------------

from __future__ import annotations

from django.test import SimpleTestCase
from django.urls import NoReverseMatch, reverse

# I 6 domini sorgente della famiglia documentale + il nome della rotta di
# ristampa. I nomi seguono le convenzioni gia' divergenti dei singoli file
# urls (alcuni singolari, altri plurali): sono elencati com'e', non come
# vorremmo che fossero — il test presidia il cablaggio, non li rinomina.
_ROTTE_RISTAMPA: tuple[tuple[str, str], ...] = (
    ("preventivo", "vendite-preventivi-documenti-ristampa"),
    ("offerta", "vendite-offerta-documento-ristampa"),
    ("contratto", "vendite-contratti-documenti-ristampa"),
    ("ordine", "vendite-ordine-documenti-ristampa"),
    ("ddt", "vendite-ddt-documenti-ristampa"),
    ("fattura", "vendite-fattura-documenti-ristampa"),
)


class RistampaFedeleRoutingTests(SimpleTestCase):
    """La ristampa fedele esiste su TUTTI i domini, non solo su quelli provati."""

    # 0. Ogni dominio ha la sua rotta di ristampa risolvibile.
    def test_ristampa_cablata_su_tutti_i_domini(self) -> None:
        mancanti: list[str] = []
        for dominio, nome_rotta in _ROTTE_RISTAMPA:
            try:
                reverse(nome_rotta, kwargs={"sorgente_id": 1, "documento_id": 2})
            except NoReverseMatch:
                mancanti.append(f"{dominio} ({nome_rotta})")
        self.assertEqual(
            mancanti, [],
            "domini senza rotta di ristampa fedele: per questi documenti "
            "l'originale non e' riproducibile. Aggiungere l'export "
            "`_views.ristampa` nel modulo `<dominio>_documenti_views.py` e la "
            "`path(...)` nel file urls del dominio.",
        )

    # 1. L'URL segue il pattern di famiglia degli endpoint nested del
    #    documento (`.../documenti/<documento_id>/<azione>/`): e' cio' che
    #    rende prevedibile il client FE, che compone i path da una sola
    #    factory (`buildSorgenteClient`).
    def test_ristampa_url_coerente_col_pattern_di_famiglia(self) -> None:
        for dominio, nome_rotta in _ROTTE_RISTAMPA:
            with self.subTest(dominio=dominio):
                url = reverse(
                    nome_rotta, kwargs={"sorgente_id": 7, "documento_id": 42},
                )
                self.assertTrue(
                    url.endswith("/documenti/42/ristampa/"),
                    f"URL fuori pattern per {dominio}: {url}",
                )
                self.assertIn("/7/", url)
