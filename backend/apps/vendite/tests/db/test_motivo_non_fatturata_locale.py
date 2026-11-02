# ------------------------------------------------------------
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: IL PATTO A TRE LIVELLI SUI MOTIVI DELLA DASHBOARD COMPETENZA — ogni
#        valore che il DATABASE (o il backend) emette come `motivo` deve avere
#        la sua etichetta nei locales del frontend, e ogni etichetta deve
#        appartenere a un valore che qualcuno emette davvero.
#
#        PERCHE' ESISTE. Il frontend risolve le etichette costruendo la chiave
#        dal codice — `vendite.dashboard_competenza.motivo_<codice>` in
#        `motivoLabel` ed `etichettaMotivo` di `DashboardCompetenzaView.vue` —
#        con ripiego sul codice grezzo (`labelOrCode`). E' fail-visible per
#        scelta, ma NESSUN presidio lo guarda: `scripts/check_i18n_keys.py`
#        vede le chiavi scritte per esteso, non quelle costruite (le dichiara
#        «punto cieco»). Quindi:
#          - un valore NUOVO a database esce a video come codice macchina e
#            nessun test diventa rosso;
#          - una chiave MORTA resta nei locales per sempre. E' successo:
#            `motivo_in_attesa_lotto` e' sopravvissuta al ritiro del valore
#            `IN_ATTESA_LOTTO` (changeSet `20260912-36`) finche' qualcuno non
#            l'ha cercata a mano (brief rilancio-step §11.7).
#
#        ⚠️ SI LEGGONO GLI OGGETTI REALI. Il vocabolario della vista si legge
#        dal `CASE` che PostgreSQL restituisce con `pg_get_viewdef` — non da
#        una copia scritta qui, o il test proverebbe se stesso. Il vocabolario
#        del backend si legge dalle costanti `MOTIVO_*` del modulo che
#        classifica i gruppi non serviti. I locales si leggono dai JSON.
#
#        ⚠️ RICHIEDE IL DB VERO: opt-in `ZEROERP_TEST_DB_E2E=1` (accesa in CI
#        da `ci-validate.yaml`), guard sullo schema in `setUpClass`. NON
#        SCRIVE NULLA.
#
#        ⛔ La forma della chiave (`motivo_` + codice in minuscolo) e' il
#        CONTRATTO di trasporto fra i tre livelli, ed e' scritta qui una
#        seconda volta di proposito: se `motivoLabel` cambia forma, questo
#        test diventa rosso e dice dove guardare.
# ------------------------------------------------------------

"""Indice test previsti (tutti opt-in `ZEROERP_TEST_DB_E2E=1`).

 1) test_ogni_valore_della_vista_ha_la_sua_etichetta
       verso diretto, lato DB: ogni letterale del `CASE` di
       `vw_dash_competenza_attivita.motivo_non_fatturata` ha la chiave in
       it.json E in en.json.
 2) test_ogni_motivo_del_backend_ha_la_sua_etichetta
       verso diretto, lato BE: ogni costante `MOTIVO_*` di
       `_fatturazione_job_helpers` (i gruppi non serviti, stesso prefisso di
       chiave) ha la chiave in entrambi i locales.
 3) test_nessuna_etichetta_orfana
       IL CONTRARIO: ogni chiave `motivo_*` del namespace e' prodotta da uno
       dei due vocabolari. E' il verso che avrebbe preso `motivo_in_attesa_lotto`.
 4) test_il_perimetro_del_backend_e_un_valore_della_vista
       la costante con cui il backend filtra i residui e conta `n_residui`
       (`MOTIVO_NON_FATTURATA_RESIDUO`) deve essere un valore che la vista
       emette: altrimenti lista vuota e card a zero, senza errore.
 5) test_la_misura_non_e_degradata
       sanity sui tre insiemi: un lettore che smette di leggere renderebbe
       verde tutto il resto per sottrazione.
"""

from __future__ import annotations

import json
import re
from unittest import TestCase

from django.db import connection

from apps.core.tests._repo import repo_root
from apps.core.tests.db_e2e import richiedi_db_provvisto
from apps.vendite.db.vendite_repository import MOTIVO_NON_FATTURATA_RESIDUO
from apps.vendite.services import _fatturazione_job_helpers

VISTA = "vendite.vw_dash_competenza_attivita"
COLONNA = "motivo_non_fatturata"
NAMESPACE = ("vendite", "dashboard_competenza")
PREFISSO_CHIAVE = "motivo_"
LOCALES = ("it", "en")

# Chiavi `motivo_*` del namespace che NON sono l'etichetta di un valore di
# vocabolario: frasi COMPOSTE dal frontend e citate per esteso in un `t()`,
# quindi gia' presidiate da `check_i18n_keys.py`. Registro dichiarato, non
# lista di eccezioni: una voce entra qui solo con la sua citazione statica.
CHIAVI_COMPOSTE = frozenset({
    # `DashboardCompetenzaView.vue`: «{n} gruppi non serviti per piu' motivi».
    "motivo_non_servito_misto",
})

# I letterali che il CASE RESTITUISCE: solo dopo `THEN`/`ELSE`. Quelli nelle
# condizioni (`WHEN x = 'COMPLETED'`) non sono valori della colonna.
_RE_LETTERALE_RESTITUITO = re.compile(
    r"\b(?:THEN|ELSE)\s+'([A-Za-z0-9_]+)'::(?:text|character varying)"
)
_RE_CASE_END = re.compile(r"\b(CASE|END)\b")
# Fra l'`END` che chiude e l'`AS colonna` puo' stare solo un cast.
_RE_CODA_CASE = re.compile(r"END(?:::[a-z ]+)?\s*$")


# Scopo: la chiave i18n di un codice di motivo, nella forma che il frontend
#        costruisce (`motivo_${String(codice).toLowerCase()}`).
def _chiave(codice: str) -> str:
    return f"{PREFISSO_CHIAVE}{codice.lower()}"


# Scopo: i valori che la colonna `colonna` della vista `vista` puo' emettere,
#        letti dal `CASE` vivo che la definisce. Pretende che l'espressione
#        della colonna SIA un `CASE` (anche annidato) e solleva su ogni altra
#        forma: isolare l'espressione sbagliata darebbe un insieme plausibile
#        e falso, preso dalla colonna precedente.
#        ⚠️ Prima occorrenza: vive qui. Alla seconda va accanto a
#        `valori_check` in `apps/core/tests/db_e2e.py`, di cui e' il gemello
#        per le colonne di vista (regola del 2).
def _valori_case_colonna(vista: str, colonna: str) -> set[str]:
    with connection.cursor() as cur:
        cur.execute("SELECT pg_get_viewdef(%s::regclass, true)", [vista])
        riga = cur.fetchone()
    assert riga is not None, f"vista {vista} assente"
    definizione: str = riga[0]

    alias = re.search(rf"\bAS {re.escape(colonna)}\b", definizione)
    assert alias is not None, f"{vista}: nessuna colonna `{colonna}`"
    prima_dell_alias = definizione[: alias.start()]

    # Si risale a ritroso: ogni END apre un livello, ogni CASE ne chiude uno;
    # il CASE che porta la profondita' a zero e' l'inizio dell'espressione.
    marcatori = list(_RE_CASE_END.finditer(prima_dell_alias))
    assert marcatori and marcatori[-1].group(1) == "END" and _RE_CODA_CASE.search(
        prima_dell_alias[marcatori[-1].start():]
    ), f"{vista}.{colonna} non e' un CASE (l'espressione non termina in END)"
    profondita, inizio = 0, None
    for m in reversed(marcatori):
        profondita += 1 if m.group(1) == "END" else -1
        if profondita == 0:
            inizio = m.start()
            break
    assert inizio is not None, f"{vista}.{colonna}: CASE senza inizio"

    valori = set(_RE_LETTERALE_RESTITUITO.findall(prima_dell_alias[inizio:]))
    assert valori, f"{vista}.{colonna}: CASE senza letterali interpretabili"
    return valori


# Scopo: le costanti `MOTIVO_*` del modulo che classifica i gruppi non serviti,
#        cioe' il secondo produttore di codici sullo stesso prefisso di chiave.
def _motivi_del_backend() -> set[str]:
    return {
        valore
        for nome, valore in vars(_fatturazione_job_helpers).items()
        if nome.startswith("MOTIVO_") and isinstance(valore, str)
    }


# Scopo: le chiavi `motivo_*` del namespace in un locale.
def _chiavi_motivo(locale: str) -> set[str]:
    percorso = repo_root() / "frontend" / "src" / "locales" / f"{locale}.json"
    with percorso.open(encoding="utf-8") as fh:
        blocco = json.load(fh)
    for segmento in NAMESPACE:
        blocco = blocco[segmento]
    return {k for k in blocco if k.startswith(PREFISSO_CHIAVE)}


class MotivoNonFatturataLocaleTests(TestCase):
    """Il patto DB/BE -> FE sulle etichette dei motivi della dashboard."""

    @classmethod
    def setUpClass(cls) -> None:
        super().setUpClass()
        richiedi_db_provvisto()
        cls.valori_vista = _valori_case_colonna(VISTA, COLONNA)
        cls.motivi_backend = _motivi_del_backend()
        cls.chiavi = {locale: _chiavi_motivo(locale) for locale in LOCALES}

    # Scopo: ogni codice di un vocabolario ha la sua chiave in TUTTI i locales.
    def _assert_etichettati(self, codici: set[str], origine: str) -> None:
        mancanti = sorted(
            f"  - {codice} -> {_chiave(codice)} manca in {locale}.json"
            for codice in codici
            for locale in LOCALES
            if _chiave(codice) not in self.chiavi[locale]
        )
        self.assertFalse(
            mancanti,
            f"valori di {origine} senza etichetta (a video uscirebbe il codice "
            "macchina, e niente lo segnalerebbe):\n" + "\n".join(mancanti),
        )

    # Scopo: 🔴 verso diretto, lato DB.
    def test_ogni_valore_della_vista_ha_la_sua_etichetta(self) -> None:
        self._assert_etichettati(self.valori_vista, f"{VISTA}.{COLONNA}")

    # Scopo: 🔴 verso diretto, lato BE (stesso prefisso di chiave).
    def test_ogni_motivo_del_backend_ha_la_sua_etichetta(self) -> None:
        self._assert_etichettati(
            self.motivi_backend, "_fatturazione_job_helpers.MOTIVO_*"
        )

    # Scopo: 🔴 IL CONTRARIO. Una chiave che nessun vocabolario produce e' una
    #        frase che a video non compare mai: e' il modo in cui
    #        `motivo_in_attesa_lotto` e' sopravvissuta al proprio valore.
    def test_nessuna_etichetta_orfana(self) -> None:
        prodotte = {_chiave(c) for c in self.valori_vista | self.motivi_backend}
        for locale in LOCALES:
            with self.subTest(locale=locale):
                orfane = sorted(self.chiavi[locale] - prodotte - CHIAVI_COMPOSTE)
                self.assertFalse(
                    orfane,
                    f"chiavi `{'.'.join(NAMESPACE)}.motivo_*` in {locale}.json che "
                    "nessun valore di vista o costante del backend produce "
                    "(chiave morta, oppure una frase composta da dichiarare in "
                    f"CHIAVI_COMPOSTE con la sua citazione): {orfane}",
                )

    # Scopo: 🔴 la costante con cui il backend filtra i residui e conta
    #        `n_residui` deve essere un valore che la vista emette. Se il DB
    #        lo rinominasse, lista vuota e card a zero — senza nessun errore.
    def test_il_perimetro_del_backend_e_un_valore_della_vista(self) -> None:
        self.assertIn(
            MOTIVO_NON_FATTURATA_RESIDUO,
            self.valori_vista,
            f"il perimetro dei residui ({MOTIVO_NON_FATTURATA_RESIDUO!r}) non e' "
            f"fra i valori che {VISTA}.{COLONNA} emette: {sorted(self.valori_vista)}",
        )

    # Scopo: sanity. Un lettore che smette di leggere renderebbe i test sopra
    #        verdi per sottrazione: si pretende che ogni insieme sia popolato
    #        oltre il banale.
    def test_la_misura_non_e_degradata(self) -> None:
        self.assertGreaterEqual(len(self.valori_vista), 2, sorted(self.valori_vista))
        self.assertGreaterEqual(len(self.motivi_backend), 2, sorted(self.motivi_backend))
        for locale in LOCALES:
            with self.subTest(locale=locale):
                self.assertGreaterEqual(len(self.chiavi[locale]), 2)
