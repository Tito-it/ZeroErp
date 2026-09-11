# ------------------------------------------------------------
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Presidio TRASVERSALE del contratto `Idempotency-Key` fra i due lati:
#        una rotta che dichiara `require_idempotency_key=True` e un chiamante
#        frontend che l'header non lo manda.
#
# 🔴 NASCE DA UN DIFETTO REALE, visto a video il 2026-09-08 e da nessun test.
#    Il verbo «togli dal giro» era completo — servizio, rotta, permesso, dialog,
#    esito a tre stati, 11 test verdi — e `escludiDocumentiDaGiro` non passava
#    l'header. Il backend rispondeva `E_IDEMPOTENCY_KEY_REQUIRED` e il verbo NON
#    PARTIVA: l'operatore scopriva il guasto dopo aver scritto il motivo, cioe'
#    dopo l'unico lavoro che quella dialog gli chiede.
#
# ⚠️ E PERCHE' NESSUN TEST LO VEDEVA, che e' la parte da ricordare: i test del
#    servizio chiamano la funzione Python, quelli della vista costruiscono la
#    richiesta a mano. L'header vive nel client `.js`, due strati piu' su di
#    entrambi — l'unico punto che nessuna delle due batterie attraversa. Un
#    difetto di CUCITURA non si trova stringendo i test dei pezzi.
#
# ⛔ IL PRESIDIO STA QUI E NON NEL FRONTEND, come il gemello sullo slot
#    `#actions` in `test_liste_configurabili_seed`: la meta' che sa QUALI rotte
#    pretendono l'header e' Python, e un cancello che vive dove sta solo meta'
#    del contratto non e' un cancello.
#
# ⚠️ Nessun database: legge i sorgenti dei due lati, quindi gira in CI.
# ------------------------------------------------------------
"""Indice test:

1. test_ogni_chiamata_frontend_a_una_rotta_che_pretende_l_header_lo_manda
   Il contratto: se il backend chiede l'header su quel metodo, il client lo
   manda. Il difetto che chiude e' un 400 a video, non un dato sbagliato.

2. test_il_rilevamento_non_e_rotto
   ⛔ Un presidio che non trova niente PASSA, e passa per sempre. Qui si
   pretende che i due lati siano stati visti davvero: rotte che chiedono
   l'header, e chiamate del frontend che lo mandano.
"""

from __future__ import annotations

import re
from unittest import TestCase
from apps.core.tests._repo import repo_root

_METODI = ("get", "post", "put", "patch", "delete")


_BACKEND = repo_root() / "backend/apps"
_FRONTEND = repo_root() / "frontend/src"


# Scopo: il testo della chiamata `api.<metodo>(...)` che comincia a `inizio`,
#        bilanciando le parentesi.
# ⚠️ Bilanciata e non «fino alla prima `)`»: queste chiamate contengono oggetti,
#    template string e altre chiamate annidate, e tagliare alla prima chiusura
#    perderebbe proprio il terzo argomento — quello con l'header.
def _chiamata(testo: str, inizio: int) -> str:
    profondita = 0
    for i in range(inizio, len(testo)):
        if testo[i] == "(":
            profondita += 1
        elif testo[i] == ")":
            profondita -= 1
            if profondita == 0:
                return testo[inizio:i + 1]
    return testo[inizio:]


# Scopo: un percorso confrontabile fra i due lati — i segmenti VARIABILI
#        diventano un segnaposto unico.
# ⚠️ `<int:lotto_id>` di Django e `${lottoId}` del client sono lo stesso buco
#    scritto in due lingue: senza normalizzarli, i due lati non si toccano mai e
#    il presidio direbbe sempre «tutto a posto».
def _normalizza(percorso: str) -> str:
    percorso = re.sub(r"<[^>]+>", "{}", percorso)
    percorso = re.sub(r"\$\{[^}]+\}", "{}", percorso)
    return percorso.strip("/")


# Scopo: le rotte che PRETENDONO l'header, per (percorso, metodo).
#
# ⛔ PER METODO E NON PER CLASSE, ed e' la correzione che rende il presidio
#    utile: una `APIView` puo' avere la `put` che passa da `handle_post_json`
#    con `require_idempotency_key=True` e la `delete` che scrive da se' senza
#    chiedere niente. Guardando la CLASSE si accusano chiamate legittime — due
#    false accuse su `ui-api.js` alla prima stesura — e un presidio che grida al
#    lupo viene disattivato, non corretto.
def _rotte_che_pretendono_header() -> dict[tuple[str, str], str]:
    per_vista: dict[str, set[str]] = {}
    for sorgente in _BACKEND.rglob("*.py"):
        if "/tests/" in str(sorgente):
            continue
        testo = sorgente.read_text(errors="ignore")
        if "require_idempotency_key" not in testo:
            continue
        classi = list(re.finditer(r"^class\s+(\w+)\s*\(", testo, re.M))
        for indice, classe in enumerate(classi):
            fine = classi[indice + 1].start() if indice + 1 < len(classi) else len(testo)
            corpo = testo[classe.start():fine]
            # Il corpo di ogni metodo HTTP, fino al successivo `def` di pari livello.
            metodi = list(re.finditer(r"^    def\s+(\w+)\s*\(", corpo, re.M))
            for i, metodo in enumerate(metodi):
                if metodo.group(1) not in _METODI:
                    continue
                fine_m = metodi[i + 1].start() if i + 1 < len(metodi) else len(corpo)
                if re.search(
                    r"require_idempotency_key\s*=\s*True", corpo[metodo.start():fine_m],
                ):
                    per_vista.setdefault(classe.group(1), set()).add(metodo.group(1))

    rotte: dict[tuple[str, str], str] = {}
    for sorgente in _BACKEND.rglob("urls*.py"):
        testo = sorgente.read_text(errors="ignore")
        for m in re.finditer(r'path\(\s*"([^"]*)"\s*,\s*(\w+)\.as_view\(\)', testo):
            for metodo in per_vista.get(m.group(2), ()):
                rotte[(_normalizza(m.group(1)), metodo)] = m.group(2)
    return rotte


# Scopo: ogni scrittura del frontend — percorso, metodo, e se porta l'header.
#
# ⚠️ L'header si riconosce in DUE forme, e la seconda non e' un dettaglio:
#    `pagamenti.js` lo passa con un helper `idem()`, e un presidio che cerca
#    solo la stringa letterale accuserebbe undici chiamate corrette. La forma
#    con l'helper e' quella BUONA — la stringa scritta a mano venti volte e' la
#    ventunesima che si dimentica.
# ⚠️ La `const BASE` si risolve: senza, il percorso del client resta `{}/…` e
#    non tocca mai quello del backend — il presidio passerebbe sempre, che e' il
#    modo in cui un cancello diventa un ornamento.
def _scritture_frontend() -> list[tuple[str, str, bool, str]]:
    trovate: list[tuple[str, str, bool, str]] = []
    for sorgente in _FRONTEND.rglob("*.js"):
        testo = sorgente.read_text(errors="ignore")
        basi = dict(re.findall(r"const\s+(\w+)\s*=\s*['\"]([^'\"]+)['\"]", testo))
        helper = set(re.findall(
            r"function\s+(\w+)\s*\([^)]*\)\s*\{\s*return\s*\{[^}]*Idempotency-Key",
            testo,
        ))
        for m in re.finditer(r"api\.(get|post|put|patch|delete)\s*\(", testo):
            if m.group(1) == "get":
                continue
            chiamata = _chiamata(testo, m.end() - 1)
            url = re.search(r"`([^`]*)`|'([^']*)'|\"([^\"]*)\"", chiamata)
            if url is None:
                continue
            grezzo = next(g for g in url.groups() if g is not None)
            for nome, valore in basi.items():
                grezzo = grezzo.replace("${" + nome + "}", valore)
            porta = "Idempotency-Key" in chiamata or any(
                f"{h}()" in chiamata for h in helper
            )
            riga = testo[:m.start()].count("\n") + 1
            trovate.append((
                _normalizza(grezzo), m.group(1), porta,
                f"{sorgente.relative_to(_FRONTEND)}:{riga}",
            ))
    return trovate


class IdempotencyKeyContrattoFeBe(TestCase):
    """Il contratto dell'header, guardato dai due lati insieme."""

    # 1. ⛔ Se il backend chiede l'header su quel metodo, il client lo manda.
    #    Il difetto non e' un dato sbagliato: e' un verbo che non parte, e lo
    #    scopre l'operatore invece di un rosso.
    def test_ogni_chiamata_frontend_a_una_rotta_che_pretende_l_header_lo_manda(
        self,
    ) -> None:
        rotte = _rotte_che_pretendono_header()
        colpevoli = sorted(
            f"{metodo.upper()} {percorso} → {rotte[(rotta, metodo)]} ({dove})"
            for percorso, metodo, porta, dove in _scritture_frontend()
            if not porta
            for rotta in [r for (r, m) in rotte if m == metodo and percorso.endswith(r)]
        )
        self.assertEqual(
            colpevoli, [],
            "chiamata frontend a una rotta che dichiara "
            "`require_idempotency_key=True` senza l'header `Idempotency-Key`: "
            "il backend risponde `E_IDEMPOTENCY_KEY_REQUIRED` e il verbo non "
            "parte affatto. Si passa come terzo argomento, "
            "`{ headers: { 'Idempotency-Key': generateIdempotencyKey() } }`: "
            f"{colpevoli}",
        )

    # 2. ⛔ UN PRESIDIO CHE NON TROVA NIENTE PASSA, e passa per sempre. Le due
    #    meta' del rilevamento sono fragili in modo diverso — le rotte si
    #    leggono da `urls*.py`, le chiamate da un client `.js` — e basta che una
    #    smetta di agganciare perche' questo file diventi un ornamento verde.
    # ⚠️ Le soglie sono BASSE di proposito: non contano quante ce ne sono, dicono
    #    che il rilevamento e' vivo. Un numero preciso qui sarebbe un test che
    #    fallisce a ogni rotta nuova, e che quindi si allenta invece di reggere.
    def test_il_rilevamento_non_e_rotto(self) -> None:
        rotte = _rotte_che_pretendono_header()
        self.assertGreater(
            len(rotte), 20,
            "quasi nessuna rotta risulta pretendere l'header: il rilevamento "
            "lato backend e' rotto, non e' che il contratto sia sparito.",
        )
        scritture = _scritture_frontend()
        con_header = [s for s in scritture if s[2]]
        self.assertGreater(
            len(con_header), 20,
            "quasi nessuna chiamata frontend risulta portare l'header: il "
            "rilevamento lato client e' rotto (o la `const BASE` non si "
            "risolve piu'), e in quello stato il test 1 passerebbe sempre.",
        )
