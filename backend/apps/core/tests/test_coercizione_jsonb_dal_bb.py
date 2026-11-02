# ------------------------------------------------------------
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Il cancello sulla COERCIZIONE DEI JSONB letti da un cursor RAW.
#        Il backend Django per psycopg 3 non decodifica i `jsonb` fuori
#        dall'ORM: arrivano come `str`. I due building block che lo sanno
#        vivono in `apps/core/db/_helpers.py` — `jsonb_out` e
#        `coerce_jsonb_dict` — e questo test vieta di riscriverli a mano.
#        Gira SENZA database.
# ------------------------------------------------------------

"""Indice test previsti.

1. test_nessuna_coercizione_jsonb_scritta_a_mano
   Nessuna delle tre forme vietate nei sorgenti applicativi. Registro a ZERO.
2. test_i_due_building_block_esistono_ancora
   Il verso opposto: se i BB sparissero o cambiassero nome, questo file
   presidierebbe una regola senza sede. Rosso, non silenzio.

⛔ PERCHE' ESISTE, e non e' teoria: e' un difetto che ha fallito in produzione.
   `dbops.fn_apply_chiusura_scadenze()` dichiara `RETURNS jsonb`, e il suo
   handler faceva `dict(riga[0])`. Su una **stringa** quel `dict()` itera i
   CARATTERI ⇒ `ValueError: dictionary update sequence element #0 has length 1;
   2 is required`. Il job notturno ha fallito **quattro notti di fila**
   (5-8 settembre 2026), due volte per notte, tentativi esauriti.
   ⚠️ E il rimedio non era da inventare: `coerce_jsonb_dict` esisteva dal
   2026-06-11 e la sua docstring descrive quella condizione. Il call site era
   stato scritto DOPO l'estrazione del building block, e non l'aveva cercato.
   ⭐ E' la forma esatta di `feedback_bb_legge_non_trasporta`: *un BB unifica la
   lettura, ma i punti che la riscrivono si CERCANO — non si aspettano.*

⭐ IL REGISTRO NASCE A ZERO, come il cancello di `ruff`. Le otto copie
   sopravvissute (2026-09-09: `ui/db/dashboard_repository`, `ui/db/ui_repository`,
   `core/db/{auth,search,email}_repository`, `anagrafiche/.../invito_operatore_service`)
   sono state convertite prima di accendere il cancello. ⛔ Un presidio che nasce
   con un arretrato dentro insegna che l'arretrato e' ammesso.

⚠️ QUALE DEI DUE BB, perche' NON sono intercambiabili — e sceglierne uno a caso
   e' come non usarli:
     · `jsonb_out`          -> NULL resta NULL, un JSON illeggibile ESPLODE.
                               E' il default: conserva la semantica di un
                               `RETURNS jsonb`, dove un decode error e' un bug.
     · `coerce_jsonb_dict`  -> None/malformato/non-oggetto diventano `{}`.
                               SOLO per percorsi di lettura/display, dove un
                               dizionario vuoto e' una risposta accettabile.
   ⛔ Il caso che decide, misurato il 2026-09-09: `auth_repository`
   `.registra_tentativo_login` torna `{bloccato, minuti_rimanenti, tentativi}` e
   il chiamante fa `result.get("bloccato")`. Con `coerce_jsonb_dict` un JSON
   illeggibile darebbe `{}` ⇒ `None` ⇒ *falsy* ⇒ **account non bloccato**: un
   fail-OPEN silenzioso su un percorso di autenticazione. Li' serve esplodere.
"""

import re
from unittest import TestCase
from apps.core.tests._repo import repo_root, sorgente_senza_commenti


# ⛔ I sorgenti si leggono SENZA commenti (`sorgente_senza_commenti`, in
#    `_repo.py`): un presidio che cerca una stringa si accende sulla PROSA che
#    spiega il difetto, e qui il rischio e' certo — il commento del job notturno
#    CITA per esteso la forma che vietiamo.


# Le tre forme vietate. ⚠️ STRETTE di proposito: un cancello che capisce un caso
# su cinque boccia a caso, e dopo due blocchi sbagliati qualcuno lo spegne — e un
# presidio spento e' peggio di uno assente. Qui si vieta solo cio' che e'
# inequivocabilmente una riscrittura dei due BB.
_FORME_VIETATE = (
    # A) `dict(riga[0])` — il difetto vero: su una str itera i caratteri.
    ("A", re.compile(r"\bdict\(\s*\w+\[\d+\]\s*\)")),
    # B) `x if isinstance(x, dict) else json.loads(x)` — `jsonb_out` a mano.
    #    ⚠️ Con una parentesi facoltativa dopo `else`: `else (json.loads(x) if x
    #    else None)` e' la stessa forma, e fino al 2026-09-19 passava — due
    #    copie in `dbops_repository.list_audit_logs` sono vissute sotto un
    #    cancello a registro zero.
    ("B", re.compile(r"isinstance\([^)]*,\s*dict\s*\)\s*else\s+\(?\s*json\.loads")),
    # C) `json.loads(x) if isinstance(x, str) else x` — lo stesso, al contrario.
    ("C", re.compile(r"json\.loads\([^)]*\)\s*if\s+isinstance\([^)]*,\s*str\s*\)")),
)

# ⛔ REGISTRO DEL DEBITO — **zero voci**, e deve restare tale.
#    Chiave: (percorso relativo, lettera della forma) -> quante volte.
#    ⚠️ Non chiavato sul numero di riga: una riga che si sposta farebbe rosso per
#    il motivo sbagliato.
_DEBITO: dict[tuple[str, str], int] = {}

# La sede dei due building block: e' l'unico file che le forme le CONTIENE
# per mestiere.
_SEDE_BB = "backend/apps/core/db/_helpers.py"


class CoercizioneJsonbDalBuildingBlockTests(TestCase):

    # Scopo: I sorgenti applicativi da scandire. ⚠️ I `tests/` restano FUORI:
    #        li' i finti costruiscono di proposito le forme che il codice vero
    #        non deve avere.
    def _sorgenti(self):
        root = repo_root()
        for percorso in sorted((root / "backend" / "apps").rglob("*.py")):
            rel = percorso.relative_to(root).as_posix()
            if "/tests/" in rel or rel == _SEDE_BB:
                continue
            yield rel, percorso

    # 1. Il cancello.
    def test_nessuna_coercizione_jsonb_scritta_a_mano(self):
        trovate: dict[tuple[str, str], int] = {}
        dettaglio: list[str] = []
        for rel, percorso in self._sorgenti():
            testo = sorgente_senza_commenti(percorso.read_text(encoding="utf-8"))
            for numero, riga in enumerate(testo.splitlines(), 1):
                for nome, rx in _FORME_VIETATE:
                    if rx.search(riga):
                        chiave = (rel, nome)
                        trovate[chiave] = trovate.get(chiave, 0) + 1
                        dettaglio.append(f"  {rel}:{numero} [forma {nome}] {riga.strip()}")

        nuove = {k: n for k, n in trovate.items() if n > _DEBITO.get(k, 0)}
        self.assertFalse(
            nuove,
            "Coercizione jsonb scritta a mano: usare `jsonb_out` (default) oppure"
            " `coerce_jsonb_dict` (solo percorsi di lettura/display) da"
            " `apps.core.db._helpers`. Quale dei due, e perche' non sono"
            " intercambiabili, e' scritto in testa a questo file.\n"
            + "\n".join(dettaglio),
        )

    # 2. ⚠️ Il verso opposto: se i due BB sparissero o cambiassero nome, questo
    #    file resterebbe verde presidiando una regola senza sede — la forma di
    #    «verde per sottrazione» che `AGENTS.md` insegue.
    def test_i_due_building_block_esistono_ancora(self):
        sede = (repo_root() / _SEDE_BB).read_text(encoding="utf-8")
        for nome in ("def jsonb_out(", "def coerce_jsonb_dict("):
            self.assertIn(
                nome,
                sede,
                f"{nome} non esiste piu' in {_SEDE_BB}: questo cancello sta"
                " presidiando una regola che non ha piu' una sede.",
            )
