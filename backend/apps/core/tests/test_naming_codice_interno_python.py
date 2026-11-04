# ------------------------------------------------------------
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Il GEMELLO PYTHON del guardrail di naming `codice_interno`/`codice`.
#        Applica le stesse tre regole di `scripts/sql/check_naming_stato_codice.sql`
#        all'SQL scritto dentro i repository Python — cioe' al lato che quel
#        guardrail NON puo' vedere.
# ------------------------------------------------------------

"""Indice test:

1. test_il_debito_non_cresce
   Nessun `codice_interno AS <x>_codice` (e gemelli) nuovo, e nessuno in piu'
   su una voce che il registro gia' conosce.

2. test_le_regole_sono_ancora_quelle_del_guardrail_sql
   Le tre regex vengono dal guardrail SQL: se quello cambia, questo file deve
   diventare rosso invece di presidiare una regola che non esiste piu'.

3. test_il_registro_si_aggiorna_quando_il_debito_cala
   Il verso opposto: una voce sanata, anche solo in parte, va aggiornata. Un
   registro che non cala smette di essere un debito e diventa una lista di
   eccezioni permanenti.

⛔ PERCHE' ESISTE, ed e' una lezione pagata due volte.
   La regola (`linee-guida-sql` §6c) dice: `codice_interno` -> `*_codice_interno`
   (e' un valore di LOGICA: ci si instrada, ci si compone una chiave i18n);
   `codice` -> `*_codice` (e' DISPLAY). Il guardrail CI che la presidia scansiona
   `pg_views`, `pg_matviews` e `pg_proc`: le definizioni VIVE del database.
   ⛔ Un `AS stato_codice` scritto dentro una stringa SQL in Python e' invisibile
   a quella scansione — non fa rosso e non lo fara' mai.
   ⚠️ E non e' teoria: e' la sede in cui, per mesi, sono sopravvissute le undici
   decodifiche del tipo del lineage, e in cui il 2026-08-29 e' rimasta una
   ri-aliasatura che rendeva lo stesso valore `frontiera_tipo_codice_interno`
   sulle sette liste e `frontiera_tipo_codice` sul drawer «Passaggi». Segnalata
   dal team DB, che dal suo lato non poteva farci niente.

⚠️ IL REGISTRO E' UN DEBITO, NON UN ELENCO DI ECCEZIONI. Le 18 voci nate con
   questo file sono il pregresso misurato il 2026-08-29, non un permesso. Vanno
   guardate una per una quando si tocca quel codice: alcune sono probabilmente
   mislabel veri (`natura_doc_codice` che e' un `codice_interno`), almeno una e'
   plausibilmente legittima e va semmai promossa a esclusione DICHIARATA, come
   fa il guardrail SQL con le sue due.
   ⛔ Il registro NON e' chiavato sul numero di riga: una riga che si sposta
   farebbe rosso per il motivo sbagliato, e un presidio che boccia a caso viene
   spento. E' chiavato su (file, nome dell'alias).
"""

import re
from collections import Counter
from unittest import TestCase
from apps.core.tests._repo import repo_root, sorgente_senza_commenti


# Scopo: sorgente Python (e SQL dentro le sue stringhe) ripulito dai COMMENTI.
# ⛔ Serve, e non e' prudenza: un presidio che cerca una STRINGA nel sorgente si
#    accende sulla PROSA che spiega il difetto. E' successo in questo repo il
#    2026-08-26 su `test_liste_configurabili_seed`: un commento che citava
#    `#cell-azioni` per spiegare il difetto ha fatto diventare rosso il test che
#    quel difetto presidia. Qui il rischio e' identico: chi documenta un alias
#    rimosso lo scrive per esteso.
# ⚠️ Due forme, perche' in questi file convivono: `#` (Python) e `--` (SQL dentro
#    le stringhe della query). Solo a inizio riga, che e' come sono scritte qui.


# Percorso del guardrail SQL di cui questo file e' il gemello.
_GUARDRAIL_SQL = "scripts/sql/check_naming_stato_codice.sql"

# Le tre regole, TRASCRITTE da `_GUARDRAIL_SQL`.
# ⛔ Sono DUE TRASCRIZIONI DELLA STESSA REGOLA, e due trascrizioni divergono:
#    e' il difetto che questo cantiere ha passato tre giorni a togliere. Dirlo in
#    un commento non basta — i commenti non li rilegge nessuno. Per questo il
#    test 2 rilegge il FILE SQL e pretende che le tre righe siano ancora quelle:
#    se la regola cambia di la', questo file diventa ROSSO invece di restare
#    indietro in silenzio, presidiando una regola che non esiste piu'.
# ⚠️ La sorgente SQL e' la sede AUTOREVOLE: in caso di divergenza si allinea
#    questo file, non quello.
_REGOLE = (
    # A) `codice_interno AS <x>_codice`  (immutabile col nome del mutabile)
    ("A", re.compile(r"codice_interno[ \t]+AS[ \t]+([a-z_]*codice)(?![_a-z])", re.I)),
    # B) `<x>codice AS <y>_codice_interno`  (mutabile col nome dell'immutabile)
    ("B", re.compile(r"[^_a-z]codice[ \t]+AS[ \t]+([a-z_]*codice_interno)", re.I)),
    # C) chiave jsonb `'<x>_codice'` valorizzata con `<rel>.codice_interno`
    ("C", re.compile(r"'([a-z_]*codice)'[ \t]*,[^,)]*\.codice_interno", re.I)),
)

# ⛔ REGISTRO DEL DEBITO — 9 occorrenze in 7 punti, contate il 2026-11-04 (il
#    15 in 12 scritto qui prima era rimasto indietro rispetto alle uscite).
#    Chiave: (percorso relativo, nome dell'alias) -> QUANTE volte. DEVE CALARE.
# ⚠️ Il CONTEGGIO, e non il solo insieme, ed e' una correzione fatta lo stesso
#    giorno: con il solo insieme, sanare due occorrenze su tre nello stesso file
#    e con lo stesso alias non si vedeva — il registro restava «vivo» e il debito
#    sembrava fermo. Un registro che non sa calare non e' un debito, e' una lista
#    di eccezioni con un altro nome.
# ⛔ E NON e' chiavato sul numero di riga: una riga che si sposta farebbe rosso
#    per il motivo sbagliato, e un presidio che boccia a caso viene spento.
_DEBITO: dict[tuple[str, str], int] = {
    ("apps/anagrafiche/db/soggetti_repository.py", "codice"): 1,
    # ⭐ `codice` e `fallback_codice` di `lookup_repository` (le due matrici
    #    degli indirizzi) sono USCITE il 2026-11-04 insieme ai gemelli che il
    #    `COALESCE(codice_interno, codice)` nascondeva a questo test
    #    (brief-be-codice-maiuscolo §7.4, decisione di Tid): ora sono
    #    `codice_interno` / `fallback_codice_interno`, e cosi' `ruolo_codice_interno`
    #    in `soggetti_repository`. ⚠️ Non erano «il contratto della lookup
    #    generica», come diceva la nota di qui: erano le matrici.
    ("apps/pagamenti/db/pagamenti_repository.py", "stato_codice"): 2,
    ("apps/pratiche/db/pratiche_repository.py", "tipo_allegato_codice"): 1,
    ("apps/pratiche/db/pratiche_repository.py", "tipo_nota_codice"): 1,
    # ⭐ `tipo_indirizzo_codice` (anagrafiche 1, vendite 2) e
    #    `origine_tipo_indirizzo_codice` (vendite 1) sono USCITE il 2026-11-01,
    #    insieme alla chiave d'ingresso delle madri (regola C, lato DB): ora
    #    sono `*_codice_interno`, e `tipo_indirizzo_codice` resta il display
    #    (`ti.codice`) delle viste e della matrice per ruolo.
    # ⭐ `natura_doc_codice` era qui con 3, poi 1, e il 2026-08-29 e' USCITA:
    #    le prime due (`get_fattura_testata`, `_legame_rettifiche`) si potevano
    #    muovere da sole, la terza (`list_lotto_fatture`) no — la legava il
    #    `campo_sorgente` del seed `ui.lista_colonna` id 494. Le due meta' sono
    #    andate insieme, seed dal team DB e alias da qui.
    #    ⛔ La voce si toglie, non si mette a 0: un registro che tiene gli zeri
    #    e' un elenco di eccezioni con l'aria di un debito.
    ("apps/vendite/db/vendite_repository.py", "pagamento_termine_codice"): 1,
    ("apps/vendite/db/vendite_repository.py", "stato_doc_fiscale_codice"): 2,
    ("apps/vendite/db/vendite_repository.py", "tipo_doc_fiscale_codice"): 1,
}

_RADICE_APPS = "backend/apps"


# Scopo: tutte le violazioni delle tre regole nell'SQL scritto in Python.
#        Ritorna (percorso relativo a `backend/`, alias, regola, riga).
def _violazioni() -> list[tuple[str, str, str, int]]:
    radice = repo_root() / _RADICE_APPS
    trovate: list[tuple[str, str, str, int]] = []
    for percorso in sorted(radice.rglob("*.py")):
        rel = percorso.relative_to(radice.parent).as_posix()
        testo = sorgente_senza_commenti(percorso.read_text(encoding="utf-8"))
        for numero, riga in enumerate(testo.splitlines(), 1):
            for nome, rx in _REGOLE:
                m = rx.search(riga)
                if m:
                    trovate.append((rel, m.group(1), nome, numero))
    return trovate


class NamingCodiceInternoPythonTests(TestCase):
    # Scopo: nessun alias mislabel oltre a quelli nel registro, e nessuno IN
    #        PIU' su una voce che il registro gia' conosce.
    def test_il_debito_non_cresce(self):
        conteggi = Counter((f, a) for f, a, _k, _n in _violazioni())
        cresciute = sorted(
            (k, conteggi[k], _DEBITO.get(k, 0))
            for k in conteggi
            if conteggi[k] > _DEBITO.get(k, 0)
        )
        self.assertEqual(
            cresciute, [],
            "alias di naming nuovi o cresciuti (linee-guida-sql §6c): "
            + "; ".join(f"{f} -> «{a}»: {ora} (registro: {prima})"
                        for (f, a), ora, prima in cresciute)
            + ". Regola: `codice_interno` -> `*_codice_interno` (e' LOGICA: chiave "
            "i18n, instradamento); `codice` -> `*_codice` (display). Il guardrail "
            "SQL non vede il Python: questo test e' il suo gemello.",
        )

    # Scopo: le tre regex sono copiate dal guardrail SQL. Se quello cambia e
    #        questo no, il gemello smette di essere un gemello.
    # ⚠️ Non confronta le regex COMPILATE (POSIX di la', Python di qua: sono
    #    due sintassi diverse) ma le RIGHE SORGENTE del file SQL, che sono il
    #    testo che una persona modifica.
    def test_le_regole_sono_ancora_quelle_del_guardrail_sql(self):
        sorgente = (repo_root() / _GUARDRAIL_SQL).read_text(encoding="utf-8")
        attese = (
            r"'codice_interno[ \t]+AS[ \t]+[a-z_]*codice([^_a-z]|$)'",
            r"'[^_a-z]codice[ \t]+AS[ \t]+[a-z_]*codice_interno'",
            r"'''[a-z_]*codice''[ \t]*,[^,)]*\.codice_interno'",
        )
        mancanti = [a for a in attese if a not in sorgente]
        self.assertEqual(
            mancanti, [],
            f"le regole di {_GUARDRAIL_SQL} sono cambiate e questo gemello e' "
            f"rimasto indietro: {mancanti}. La sede autorevole e' il file SQL: "
            "si allineano le regex di questo file, e si rileggono le voci del "
            "registro, che potrebbero non essere piu' violazioni.",
        )

    # Scopo: il registro CALA. Una voce sanata — del tutto o in parte — va
    #        aggiornata, altrimenti il debito residuo risulta piu' grande del
    #        vero e l'eccezione diventa permanente.
    def test_il_registro_si_aggiorna_quando_il_debito_cala(self):
        conteggi = Counter((f, a) for f, a, _k, _n in _violazioni())
        calate = sorted(
            (k, conteggi.get(k, 0), _DEBITO[k])
            for k in _DEBITO
            if conteggi.get(k, 0) < _DEBITO[k]
        )
        self.assertEqual(
            calate, [],
            "il debito e' calato e il registro non lo sa: "
            + "; ".join(f"{f} -> «{a}»: ora {ora}, registro {prima}"
                        for (f, a), ora, prima in calate)
            + ". Aggiornare (o togliere) la voce: un registro che non cala non e' "
            "un debito, e' una lista di eccezioni con un altro nome.",
        )
