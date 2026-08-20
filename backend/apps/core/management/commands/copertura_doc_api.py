# ------------------------------------------------------------
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Management command — MISURA la copertura della documentazione API:
#        quali rotte esistono nel codice e non compaiono in nessun `.md` di
#        `docs/it/backend` («scoperte»), e quali path la doc nomina senza che
#        una rotta li serva («fantasmi»).
#
#          ./manage-env.sh copertura_doc_api                  # tutte le aree
#          ./manage-env.sh copertura_doc_api --aree vendite,core
#          ./manage-env.sh copertura_doc_api --aree ui --dettaglio
#
#        ⚠️ MISURA LA COPERTURA, NON LA CORRETTEZZA. «Documentata» qui vuol dire
#        solo «il path e' nominato da qualche parte»: una rotta puo' risultare
#        coperta e avere una pagina che descrive l'API di tre mesi fa. La
#        verifica di sostanza si fa per dominio, leggendo il codice.
#
#        LE ROTTE ARRIVANO DAL RESOLVER, non da una regex sui `urls.py`: sono i
#        path veri, coi metodi HTTP letti dalla view.
#
#        ⚠️ TRE TRAPPOLE, tutte incontrate misurando davvero il 2026-08-19
#        (analisi-copertura-doc-api-vendite-core.md). Sono la ragione per cui
#        questo file esiste invece di uno script buttato via:
#
#         1. **le citazioni nella doc hanno tre forme** — assoluta
#            (`/api/v1/vendite/resi/export/`), relativa (`POST /<id>/conferma/`,
#            che vale sulla base del file) e troncata (`…/export/`). Contando
#            solo le assolute, `api_resi.md` risultava non documentare i verbi
#            che invece documenta;
#         2. **il jolly `{}` vale nei DUE versi.** Una pagina cross-dominio
#            scrive `/api/v1/vendite/<dominio>/{id}/emetti/` e copre sei rotte
#            concrete: al confronto letterale risultavano tutte scoperte, cioe'
#            la misura PUNIVA la doc scritta bene. E applicando il jolly solo
#            alla copertura, quella stessa pagina produceva 16 fantasmi: una
#            misura asimmetrica inventa difetti;
#         3. **una lapide non e' un fantasma.** Una sezione «⛔ … non esiste
#            piu'» nomina il path apposta: senza escluderla, correggere un
#            fantasma non lo fa sparire dal conteggio — e una misura che non
#            premia le correzioni smette di servire.
#
#        E una quarta, piu' banale ma la piu' costosa: molte pagine scrivono
#        ESEMPI (`/emittenti-fiscali/1/utilities`) invece di template. Un
#        segmento tutto cifre o fatto come un uuid vale come segnaposto:
#        senza questa regola `anagrafiche` risultava con 19 fantasmi inesistenti.
# ------------------------------------------------------------

from __future__ import annotations

import re
from collections import defaultdict
from pathlib import Path
from typing import Any

from django.conf import settings
from django.core.management.base import BaseCommand
from django.urls import get_resolver

# Radice della documentazione backend: e' li' che si cercano le citazioni.
DOCS = Path(settings.BASE_DIR).parent / "docs" / "it" / "backend"

# `<int:pk>`, `<uuid:id>`, `{id}`, `:id` -> segnaposto.
PARAM = re.compile(r"<[^>/]+>|\{[^}/]+\}|(?<=/):[A-Za-z_][A-Za-z0-9_]*")
ASSOLUTA = re.compile(r"/api/[A-Za-z0-9_\-/{}<>:.]+")
RELATIVA = re.compile(r"[…]?/[A-Za-z0-9_\-/{}<>:]{2,}")
FILE_SORGENTE = re.compile(r"\.(py|js|vue|md|ts|json|yaml|sql)$")
# Trappola 4: valori di esempio al posto dei segnaposto.
VALORE_ESEMPIO = re.compile(r"^(\d+|[0-9a-f]{4,}(-[0-9a-f.]+)+|[0-9a-f-]{8,}\.\.\.)$", re.I)
# Trappola 3: le righe che dichiarano una rimozione.
LAPIDE = re.compile(r"⛔|RIMOSS|non esiste piu|non esistono piu", re.I)


# Scopo: forma canonica di un path, uguale per rotte e citazioni.
def norma(p: str) -> str:
    p = p.split("?")[0].split("#")[0].replace("…", "")
    p = PARAM.sub("{}", p)
    p = "/".join("{}" if VALORE_ESEMPIO.match(seg) else seg for seg in p.split("/"))
    p = re.sub(r"/+", "/", p).rstrip("/").lower()
    return p.replace("$", "").replace("^", "")


# Scopo: tutte le rotte servite, dal resolver, con i metodi HTTP della view.
def leggi_rotte() -> dict[str, tuple[str, list[str]]]:
    def cammina(resolver: Any, prefisso: str = "") -> list[tuple[str, list[str]]]:
        fuori: list[tuple[str, list[str]]] = []
        for pattern in resolver.url_patterns:
            testo = prefisso + str(pattern.pattern)
            if hasattr(pattern, "url_patterns"):
                fuori += cammina(pattern, testo)
                continue
            cb = pattern.callback
            cls = getattr(cb, "cls", None) or getattr(cb, "view_class", None)
            metodi = [
                m.upper() for m in ("get", "post", "put", "patch", "delete")
                if cls is not None and hasattr(cls, m)
            ]
            fuori.append(("/" + testo, metodi))
        return fuori

    return {
        norma(path): (path, metodi)
        for path, metodi in cammina(get_resolver())
        if path.startswith("/api/")
    }


# Scopo: i path che la documentazione nomina. Ritorna due mappe: TUTTE le
#        citazioni (per dire «coperta») e le sole ASSOLUTE (per dire
#        «fantasma» — una relativa risolta su una base non prova che manchi).
def leggi_citazioni() -> tuple[dict[str, set[str]], dict[str, set[str]]]:
    tutte: dict[str, set[str]] = defaultdict(set)
    assolute: dict[str, set[str]] = defaultdict(set)
    for f in sorted(DOCS.rglob("*.md")):
        testo = f.read_text(errors="ignore")
        vive = "\n".join(r for r in testo.splitlines() if not LAPIDE.search(r))
        trovate = [
            norma(x) for x in ASSOLUTA.findall(vive) if not FILE_SORGENTE.search(x)
        ]
        for p in trovate:
            assolute[p].add(f.name)
            tutte[p].add(f.name)
        # Basi del file: i prefissi che cita, a due profondita'.
        # ⚠️ Serve anche quella corta `/api/v1/<area>`: una pagina che elenca
        # `GET /admin/definizioni/` in tabella e cita l'area altrove documenta
        # eccome — attaccare la coda alla sola base lunga darebbe
        # `/api/v1/ui/admin/admin/definizioni`, e la rotta risulterebbe scoperta.
        basi = {
            "/" + "/".join(p.strip("/").split("/")[:n])
            for p in trovate
            for n in (3, 4)
            if len(p.strip("/").split("/")) >= n
        }
        for x in RELATIVA.findall(testo):
            if x.startswith("/api") or FILE_SORGENTE.search(x):
                continue
            coda = x.lstrip("…").lstrip("/")
            # La citazione grezza serve alla regola della CODA (trappola 5):
            # attaccata alla base darebbe `/definizioni/definizioni/...`.
            tutte[norma("/" + coda)].add(f.name)
            for base in basi:
                tutte[norma(base + "/" + coda)].add(f.name)
    return tutte, assolute


# Scopo: `{}` vale come UN segmento qualunque, nei due versi (trappola 2).
def _regex(path: str) -> re.Pattern[str]:
    return re.compile("^" + re.escape(path).replace(r"\{\}", "[^/]+") + "$")


# Trappola 5: una citazione relativa puo' RIPETERE un pezzo del path
# (`POST /definizioni/<id>/archi/<kind>/` in una pagina la cui base e' gia'
# `/api/v1/pratiche/definizioni`). Attaccarla alla base produce un path che non
# esiste; leggerla come CODA della rotta funziona. Minimo tre segmenti, o
# `/{}/note` coprirebbe mezzo applicativo.
def _regex_coda(path: str) -> re.Pattern[str] | None:
    segmenti = path.strip("/").split("/")
    # ⚠️ Servono almeno DUE segmenti che dicano un nome. Con la sola regola dei
    # «tre segmenti» una citazione spazzatura come `/{}/{}/{}` — che nella doc
    # esiste — copriva TUTTE le 538 rotte e il conto usciva 100%: una coda
    # identifica qualcosa solo se nomina qualcosa.
    if len(segmenti) < 3 or sum(1 for s in segmenti if s != "{}") < 2:
        return None
    return re.compile(re.escape(path).replace(r"\{\}", "[^/]+") + "$")


class Command(BaseCommand):
    help = "Copertura della documentazione API: rotte scoperte e path fantasma."

    def add_arguments(self, parser: Any) -> None:
        parser.add_argument(
            "--aree", default="",
            help="Aree separate da virgola (es. vendite,core). Vuoto = tutte.",
        )
        parser.add_argument(
            "--dettaglio", action="store_true",
            help="Elenca le rotte scoperte e le citazioni fantasma.",
        )

    def handle(self, *args: Any, **opts: Any) -> None:
        rotte = leggi_rotte()
        doc_tutte, doc_assolute = leggi_citazioni()
        citazioni = [(_regex(c), c) for c in doc_tutte]
        code = [rx for rx in (_regex_coda(c) for c in doc_tutte) if rx is not None]

        def coperta(path: str) -> bool:
            if any(rx.match(path) for rx, _ in citazioni):
                return True
            return any(rx.search(path) for rx in code)

        def servita(citazione: str) -> bool:
            rx = _regex(citazione)
            if any(rx.match(r) for r in rotte):
                return True
            # Trappola 6: una citazione di PREFISSO non e' un fantasma.
            # «Tutti gli endpoint sono sotto `/api/v1/core/tracciamento/`» non e'
            # una rotta mancante: e' una pagina che dice dove si e'.
            prefisso = re.compile(
                "^" + re.escape(citazione).replace(r"\{\}", "[^/]+") + "/",
            )
            return any(prefisso.match(r) for r in rotte)

        aree_richieste = [a.strip() for a in opts["aree"].split(",") if a.strip()]
        aree = sorted({
            p.strip("/").split("/")[2] for p in rotte if p.startswith("/api/v1/")
        })
        if aree_richieste:
            aree = [a for a in aree if a in aree_richieste]

        self.stdout.write(
            f"{'area':16}{'rotte':>7}{'documentate':>14}{'scoperte':>10}{'fantasmi':>10}"
        )
        tot_r = tot_d = tot_f = 0
        for area in aree:
            pref = f"/api/v1/{area}/"
            sue = {p: v for p, v in rotte.items() if p.startswith(pref)}
            if not sue:
                continue
            coperte = {p for p in sue if coperta(p)}
            scoperte = sorted(set(sue) - coperte)
            fantasmi = sorted(
                p for p in doc_assolute
                if p.startswith(pref) and not servita(p)
                and len(p.strip("/").split("/")) > 3
            )
            tot_r += len(sue)
            tot_d += len(coperte)
            tot_f += len(fantasmi)
            pct = 100 * len(coperte) // len(sue)
            self.stdout.write(
                f"{area:16}{len(sue):>7}{len(coperte):>9} ({pct:>3}%)"
                f"{len(scoperte):>10}{len(fantasmi):>10}"
            )
            if not opts["dettaglio"]:
                continue
            for p in scoperte:
                reale, metodi = sue[p]
                self.stdout.write(f"    SCOPERTA  {','.join(metodi) or '?':<18} {reale}")
            for p in fantasmi:
                dove = ", ".join(sorted(doc_assolute[p]))
                self.stdout.write(f"    FANTASMA  {p}   <- {dove}")

        if tot_r:
            self.stdout.write(
                f"{'TOTALE':16}{tot_r:>7}{tot_d:>9} ({100 * tot_d // tot_r:>3}%)"
                f"{tot_r - tot_d:>10}{tot_f:>10}"
            )
