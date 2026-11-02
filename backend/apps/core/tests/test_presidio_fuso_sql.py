# ------------------------------------------------------------
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: PRESIDIO — nel codice del backend (fuori dai test) nessun SQL prende
#        «oggi» o «adesso» dal fuso della SESSIONE: `CURRENT_DATE`,
#        `LOCALTIMESTAMP`, `LOCALTIME`, `now()::date`. L'oggi e'
#        `script.fn_data_operativa()` (in un'istruzione:
#        `(SELECT script.fn_data_operativa())`), lato Python `oggi_aziendale()`.
#        Gemello lato BE del pgTAP `dbops/test-oggi-dal-fuso-aziendale-v1`
#        (D-8), che guarda il catalogo del DB. Brief un-solo-fuso-aziendale B-9.
#        Il presidio sulle colonne istante (che vuole il catalogo) sta in
#        `apps/core/tests/db/test_presidio_fuso_sql_db.py`.
# Note: Scansione TESTUALE delle righe di codice (i commenti `#` esclusi):
#        trova le forme che conosce, e la controprova prova che le vede.
# ------------------------------------------------------------
"""Indice test.

1. test_nessun_sql_prende_oggi_dalla_sessione
2. test_la_scansione_vede_le_forme_vietate (controprova)
3. test_nessun_test_prende_oggi_dalla_sessione   (T-5, gemello del guardrail pgTAP)
"""

from __future__ import annotations

import re
from collections.abc import Iterator
from pathlib import Path

from django.conf import settings
from django.test import SimpleTestCase

# Le forme che danno il giorno o l'ora della SESSIONE PostgreSQL. ⚠️ Non
# preceduta da un punto: `timezone.localtime(...)` e' Python, non SQL.
OGGI_DELLA_SESSIONE = re.compile(
    r"(?<!\.)\b(?:CURRENT_DATE|LOCALTIMESTAMP|LOCALTIME)\b"
    r"|\bnow\(\)\s*::\s*date\b|\bcurrent_timestamp\s*::\s*date\b",
    re.IGNORECASE,
)


# I due file di presidio nominano le forme vietate apposta (controprova).
_PRESIDI = (
    "apps/core/tests/test_presidio_fuso_sql.py",
    "apps/core/tests/db/test_presidio_fuso_sql_db.py",
)


# Scopo: (percorso relativo, numero, testo) di ogni riga di CODICE del backend
#        — fuori dai test, o dei soli test con `dei_test=True` — : i commenti
#        `#` non contano, la storia di cio' che si e' tolto ci sta legittimamente.
def righe_di_codice(*, dei_test: bool = False) -> Iterator[tuple[str, int, str]]:
    radice = Path(settings.BASE_DIR)
    for percorso in sorted((radice / "apps").rglob("*.py")):
        relativo = str(percorso.relative_to(radice))
        if ("/tests/" in relativo) != dei_test or relativo in _PRESIDI:
            continue
        for numero, riga in enumerate(percorso.read_text().split("\n"), start=1):
            if riga.strip().startswith("#"):
                continue
            # Commento in coda alla riga: fuori dalla scansione.
            codice = riga.split("  # ", 1)[0]
            yield relativo, numero, codice


class OggiNonDallaSessioneTests(SimpleTestCase):
    """L'oggi del backend e' quello dell'azienda."""

    # 1. Zero righe di codice con un «oggi» della sessione.
    def test_nessun_sql_prende_oggi_dalla_sessione(self) -> None:
        trovate = [
            f"{p}:{n}: {r.strip()}" for p, n, r in righe_di_codice() if OGGI_DELLA_SESSIONE.search(r)
        ]
        self.assertEqual(trovate, [], "usa script.fn_data_operativa() / oggi_aziendale()")

    # 2. Controprova: le forme vietate si vedono, la forma giusta no.
    def test_la_scansione_vede_le_forme_vietate(self) -> None:
        for vietata in (
            "AND v.validita @> CURRENT_DATE",
            "COALESCE(%s, current_date)",
            "WHERE x < now()::date",
            "SELECT LOCALTIMESTAMP",
        ):
            with self.subTest(vietata=vietata):
                self.assertIsNotNone(OGGI_DELLA_SESSIONE.search(vietata))
        self.assertIsNone(OGGI_DELLA_SESSIONE.search("v.validita @> (SELECT script.fn_data_operativa())"))
        self.assertIsNone(OGGI_DELLA_SESSIONE.search("timezone.localtime(value, fuso_aziendale())"))
        self.assertTrue(any(True for _ in righe_di_codice()))

    # 3. Anche l'SQL dei TEST prende «oggi» dall'azienda: un test che scrive
    #    `CURRENT_DATE` confronta il giorno della SESSIONE (UTC) col DEFAULT
    #    aziendale, ed e' verde solo finche' i due coincidono. Col parametro
    #    ostile della CI (T-5) erano cinque rossi; e' il gemello del guardrail
    #    che il team DB applica ai pgTAP (`guardrail_pgtap_preambolo.py`).
    def test_nessun_test_prende_oggi_dalla_sessione(self) -> None:
        trovate = [
            f"{p}:{n}: {r.strip()}"
            for p, n, r in righe_di_codice(dei_test=True)
            if OGGI_DELLA_SESSIONE.search(r)
        ]
        self.assertEqual(trovate, [], "nei test l'oggi e' script.fn_data_operativa() / oggi_aziendale()")
        self.assertTrue(any(True for _ in righe_di_codice(dei_test=True)))
