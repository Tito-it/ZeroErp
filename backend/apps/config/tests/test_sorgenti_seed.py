# ------------------------------------------------------------
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Presidio dei codici di `config.sorgenti` nominati dal backend
#        (`apps/config/sorgenti.py`): esistono e sono attivi nel seed, il nome
#        della costante e' il codice, e nessun modulo se ne riscrive una copia
#        locale.
# ------------------------------------------------------------
"""
Indice test eseguiti:
1) test_ogni_costante_e_un_codice_attivo_del_seed
2) test_il_nome_della_costante_e_il_codice
3) test_nessun_modulo_ricopia_un_codice_sorgente_in_una_costante_locale
4) test_nessun_modulo_riusa_il_nome_di_una_costante_con_un_altro_valore
"""

import csv
import re

from django.test import SimpleTestCase

from apps.config import sorgenti
from apps.core.tests._repo import repo_root, sorgente_senza_commenti

_SEED = repo_root() / "db" / "changelog" / "migrations_v2" / "80_data" / "sql" / "config" / "sorgenti.csv"


# Scopo: le costanti del modulo, nome -> valore.
def _costanti() -> dict[str, str]:
    return {
        nome: valore for nome, valore in vars(sorgenti).items()
        if nome.startswith("SORGENTE_") and isinstance(valore, str)
    }


class SorgentiSeedTests(SimpleTestCase):
    """I codici di config.sorgenti del backend, contro il seed."""

    # Scopo: un codice che il seed non ha (o ha spento) non da' errore a chi lo
    #        legge per codice: da' una lista vuota o una colonna NULL. Il rosso
    #        deve arrivare qui, non in app.
    def test_ogni_costante_e_un_codice_attivo_del_seed(self) -> None:
        with _SEED.open(newline="", encoding="utf-8") as fh:
            seed = {r["codice_interno"]: r["attivo"] for r in csv.DictReader(fh)}
        costanti = _costanti()
        # ⚠️ Un modulo senza costanti renderebbe il test verde a vuoto.
        self.assertTrue(costanti, "nessuna costante SORGENTE_* in apps.config.sorgenti")
        for nome, codice in costanti.items():
            with self.subTest(costante=nome):
                self.assertIn(codice, seed, f"{codice} non esiste in config/sorgenti.csv")
                self.assertEqual(seed[codice], "t", f"{codice} non e' attivo nel seed")

    # Scopo: `SORGENTE_DDT_VENDITA = "ORDINE_VENDITA"` sarebbe un codice valido
    #        sotto il nome sbagliato, e il seed non se ne accorgerebbe.
    def test_il_nome_della_costante_e_il_codice(self) -> None:
        for nome, codice in _costanti().items():
            with self.subTest(costante=nome):
                self.assertEqual(nome, f"SORGENTE_{codice}")

    # Scopo: la sede e' una. Una costante locale di modulo che assegna un
    #        codice di config.sorgenti a un nome `*SORGENTE*` e' la copia che
    #        questo modulo esiste per ritirare (`_SORGENTE_DDT` era scritto due
    #        volte, in due service diversi).
    # ⚠️ Si cerca solo la forma «costante di modulo col nome della sorgente»,
    #    non ogni letterale: le stesse parole vivono legittimamente in altri
    #    vocabolari (note, legami, tipi_entita, log) — vedi il modulo.
    def test_nessun_modulo_ricopia_un_codice_sorgente_in_una_costante_locale(self) -> None:
        codici = "|".join(re.escape(c) for c in _costanti().values())
        copia = re.compile(
            rf"""^_?[A-Z_]*SORGENTE[A-Z_]*\s*(?::\s*str\s*)?=\s*["']({codici})["']""", re.M,
        )
        app = repo_root() / "backend" / "apps"
        trovate = []
        for percorso in sorted(app.rglob("*.py")):
            if "tests" in percorso.parts or percorso.name == "sorgenti.py" and percorso.parent.name == "config":
                continue
            testo = sorgente_senza_commenti(percorso.read_text(encoding="utf-8"))
            trovate += [f"{percorso.relative_to(app)}: {m.group(0)}" for m in copia.finditer(testo)]
        self.assertEqual(trovate, [], "copie locali di codici di config.sorgenti: usare apps.config.sorgenti")

    # Scopo: il caso che il test 3 non vede, perche' cerca il VALORE: lo stesso
    #        NOME con un valore diverso. `_approvazioni_prezzo_constants` aveva
    #        `SORGENTE_CONTRATTO = "contratto"` (il meta della pratica), e un
    #        modulo che importava le due costanti teneva quella dell'ultimo
    #        import, senza errore (2026-10-19, brief-db-grammatica-unica-documenti).
    def test_nessun_modulo_riusa_il_nome_di_una_costante_con_un_altro_valore(self) -> None:
        nomi = "|".join(re.escape(n) for n in _costanti())
        omonimo = re.compile(rf"^({nomi})\b\s*(?::[^=\n]*)?=", re.M)
        app = repo_root() / "backend" / "apps"
        trovati = []
        for percorso in sorted(app.rglob("*.py")):
            if "tests" in percorso.parts or percorso.name == "sorgenti.py" and percorso.parent.name == "config":
                continue
            testo = sorgente_senza_commenti(percorso.read_text(encoding="utf-8"))
            trovati += [f"{percorso.relative_to(app)}: {m.group(1)}" for m in omonimo.finditer(testo)]
        self.assertEqual(trovati, [], "nomi delle costanti di apps.config.sorgenti riusati altrove")
