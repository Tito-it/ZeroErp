# ------------------------------------------------------------
# SPDX-License-Identifier: AGPL-3.0-or-later
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
#
#        ⚠️ DUE ALTRE, trovate rimisurando il 2026-09-12 — e sono di verso
#        OPPOSTO, il che e' la ragione per cui vanno tenute insieme:
#
#         7. **la QUARTA forma di citazione: il path in un blocco di codice
#            SENZA slash iniziale** — `soggetti/{id}/titoli-iva/`, `GET
#            processi/` — tipica delle tabelle che dichiarano la base
#            nell'intestazione. `RELATIVA` pretende lo slash, quindi catturava
#            `/{id}/titoli-iva/` perdendo il primo segmento: **sei rotte** di
#            anagrafiche risultavano scoperte con la loro pagina gia' scritta.
#            La misura puniva la doc scritta bene, per la seconda volta;
#         8. **una citazione che dopo `/api/v1/<area>` NON NOMINA NIENTE non
#            documenta niente.** `/api/v1/vendite/<dominio>/{id}/` e' una frase
#            che dice DOVE si e' — e col jolly della trappola 2 copriva OGNI
#            rotta a due segmenti di vendite: `famiglie/{id}/` risultava
#            documentata senza che nessuna pagina la nominasse. **Nove rotte**
#            contate coperte da nessuno. ⛔ E' il verso PERMISSIVO, l'unico in
#            cui una misura marcisce senza che nessuno se ne accorga: una rotta
#            nuova nasceva gia' «documentata». L'eccezione legittima e' il
#            dettaglio della risorsa radice di un'area
#            (`/api/v1/pratiche/<pratica_id>/`): si riconosce perche' e' citato
#            per intero e il suo segnaposto e' un IDENTIFICATIVO, non un
#            dominio — da qui i due segnaposto `{}` e `{*}`.
#
#        Presidio: `apps/core/tests/test_copertura_doc_api.py`.
# ------------------------------------------------------------

from __future__ import annotations

import re
from collections import defaultdict
from collections.abc import Callable
from pathlib import Path
from typing import Any

from django.conf import settings
from apps.core.management.comando_aziendale import ComandoAziendale

from apps.core.api.rotte import rotte_servite

# Radice della documentazione backend: e' li' che si cercano le citazioni.
DOCS = Path(settings.BASE_DIR).parent / "docs" / "it" / "backend"

# `<int:pk>`, `<uuid:id>`, `{id}`, `:id` -> segnaposto.
PARAM = re.compile(r"<[^>/]+>|\{[^}/]+\}|(?<=/):[A-Za-z_][A-Za-z0-9_]*")
# Dentro le graffe vale anche l'alternanza `{approva,rifiuta}-prezzo`: e' un
# segnaposto come gli altri (PARAM la collassa), e troncarla alla virgola
# faceva di tre coppie di rotte sei fantasmi e sei scoperte.
ASSOLUTA = re.compile(r"/api/(?:\{[^}\s]*\}|[A-Za-z0-9_\-/<>:.])+")
RELATIVA = re.compile(r"[…]?/[A-Za-z0-9_\-/{}<>:]{2,}")
# Trappola 7: il path dentro un blocco di codice, senza slash iniziale e con
# un eventuale verbo HTTP davanti (`GET processi/`, `soggetti/{id}/titoli-iva/`).
CODICE = re.compile(r"`([^`\n]+)`")
NUDA = re.compile(
    r"^(?:(?:GET|POST|PUT|PATCH|DELETE)[ /]+)*"
    r"([A-Za-z0-9_\-{}<>:]+(?:/[A-Za-z0-9_\-{}<>:]*)+)$"
)
FILE_SORGENTE = re.compile(r"\.(py|js|vue|md|ts|json|yaml|sql)$")
# Trappola 4: valori di esempio al posto dei segnaposto.
VALORE_ESEMPIO = re.compile(r"^(\d+|[0-9a-f]{4,}(-[0-9a-f.]+)+|[0-9a-f-]{8,}\.\.\.)$", re.I)
# Trappola 3: le righe che dichiarano una rimozione — anche quando lo dicono
# in prosa («il vecchio path …», «il path legacy …»).
# ⭐ Dal 2026-10-21 anche le forme che la doc usa davvero per un endpoint
# ritirato: il titolo barrato (`~~POST …~~ — Ritirato`), «ritirato/ritirata», e
# la prosa storica («esistevano solo …»). Senza, le lapidi scritte bene
# risultavano fantasmi (brief-be-verifica-documentazione-api §E).
# ⚠️ Una lapide esce anche dalla copertura: se una di queste parole finisce su
# una riga che cita una rotta VIVA, quella rotta risulta scoperta — il verso
# prudente, che si vede.
LAPIDE = re.compile(
    r"⛔|RIMOSS|non esiste piu|non esistono piu|vecchio path|path legacy"
    r"|ritirat|~~|esistevano",
    re.I,
)
# Trappola 9 (2026-10-21, brief-be-verifica-documentazione-api §E): una riga
# che DICHIARA di non documentare («queste rotte non sono documentate») nomina
# i path apposta, e contarla come copertura e' il verso PERMISSIVO — la rotta
# risultava documentata proprio dalla frase che dice che non lo e'. Quelle
# citazioni non coprono; non sono nemmeno fantasmi (la rotta esiste).
NON_DOCUMENTA = re.compile(r"non\s+(?:sono\s+|e'\s+|è\s+|ancora\s+)*documentat", re.I)
# Trappola 8: i segnaposto che stanno per una RISORSA, non per un
# identificativo. E' una lista CHIUSA e corta di proposito: un nome fuori da
# qui resta `{}`, cioe' il caso conservativo.
RISORSA_JOLLY = frozenset({"dominio", "sorgente", "risorsa", "area", "modulo", "entita"})
# `{}` un identificativo · `{*}` una risorsa · `{**}` «un prefisso qualunque»,
# cioe' i puntini di una citazione TRONCATA (`.../{titolo_id}/ambiti/`),
# ancorati all'area del file: la coda vale per una rotta di QUELL'area.
JOLLY = ("{}", "{*}", "{**}")


# Scopo: il segnaposto canonico di un parametro di path: `{*}` se il nome dice
#        una risorsa (`<dominio>`), `{}` in ogni altro caso (`<int:id>`, `{pk}`).
def _segnaposto(m: re.Match[str]) -> str:
    nome = m.group(0).strip("<>{}:").split(":")[-1].strip().lower()
    return "{*}" if nome in RISORSA_JOLLY else "{}"


# Scopo: forma canonica di un path, uguale per rotte e citazioni.
def norma(p: str) -> str:
    p = p.split("?")[0].split("#")[0].replace("…", "")
    # `/api/v1/core/...` e' un prefisso, `…/utility/.` e' un punto di prosa:
    # ne' l'uno ne' l'altro sono un segmento.
    p = re.sub(r"(/\.\.\.|\.)+$", "", p)
    p = PARAM.sub(_segnaposto, p)
    p = "/".join("{}" if VALORE_ESEMPIO.match(seg) else seg for seg in p.split("/"))
    p = re.sub(r"/+", "/", p).rstrip("/").lower()
    return p.replace("$", "").replace("^", "")


# Scopo: trappola 8 — vero se la citazione, dopo `/api/v1/<area>`, non nomina
#        nessun segmento. Una cosi' copre tutto e documenta niente. L'unica
#        forma che si salva e' il dettaglio radice dell'area citato per intero
#        con un identificativo (`/api/v1/pratiche/{}`): una `{*}` la condanna,
#        e una sintetizzata da base + coda relativa (`/{id}/`) pure — non e'
#        la doc che l'ha scritta, e' la misura che l'ha composta.
def generica(citazione: str, *, assoluta: bool) -> bool:
    seg = citazione.strip("/").split("/")
    if len(seg) < 4 or seg[0] != "api":
        return False
    coda = seg[3:]
    if any(s not in JOLLY for s in coda):
        return False
    return "{*}" in coda or not assoluta


# Scopo: tutte le rotte che esistono nel codice, con i metodi HTTP della view.
#        Il cammino e' il BB `apps.core.api.rotte` (estratto il 2026-09-25,
#        regola del 2), comprese le rotte montate a condizione: la
#        documentazione copre il prodotto, non le flag di questa macchina.
def leggi_rotte() -> dict[str, tuple[str, list[str]]]:
    fuori: dict[str, tuple[str, list[str]]] = {}
    for rotta in rotte_servite(anche_condizionali=True):
        path = "/" + rotta.percorso
        if not path.startswith("/api/"):
            continue
        metodi = [
            m.upper() for m in ("get", "post", "put", "patch", "delete")
            if rotta.view is not None and hasattr(rotta.view, m)
        ]
        fuori[norma(path)] = (path, metodi)
    return fuori


# Scopo: i path che la documentazione nomina. Ritorna due mappe: TUTTE le
#        citazioni (per dire «coperta») e le sole ASSOLUTE (per dire
#        «fantasma» — una relativa risolta su una base non prova che manchi).
def leggi_citazioni() -> tuple[dict[str, set[str]], dict[str, set[str]]]:
    tutte: dict[str, set[str]] = defaultdict(set)
    assolute: dict[str, set[str]] = defaultdict(set)
    for f in sorted(DOCS.rglob("*.md")):
        testo = f.read_text(errors="ignore")
        vive = [r for r in testo.splitlines() if not LAPIDE.search(r)]
        trovate = [
            norma(x) for x in ASSOLUTA.findall("\n".join(vive)) if not FILE_SORGENTE.search(x)
        ]
        for p in trovate:
            assolute[p].add(f.name)
        # La copertura no dalle righe che dichiarano di NON documentare
        # (trappola 9): i fantasmi si', la rotta citata li' esiste.
        for riga in vive:
            if NON_DOCUMENTA.search(riga):
                continue
            for x in ASSOLUTA.findall(riga):
                if not FILE_SORGENTE.search(x):
                    tutte[norma(x)].add(f.name)
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
        # Le relative si leggono RIGA PER RIGA: la forma troncata
        # ``(+ `/export/`)`` vale sul path assoluto scritto accanto, e una base
        # corta del file non lo raggiunge (`lotti/{id}/gruppi/` e' a cinque
        # segmenti, le basi si fermano a quattro).
        aree = {b for b in basi if len(b.strip("/").split("/")) == 3}
        for riga in testo.splitlines():
            if NON_DOCUMENTA.search(riga):
                continue
            sulla_riga = {
                norma(x) for x in ASSOLUTA.findall(riga) if not FILE_SORGENTE.search(x)
            }
            # (coda, troncata): `…/export/` e' troncata, `/export/` no.
            relative = [
                (x.lstrip("…"), x.startswith("…")) for x in RELATIVA.findall(riga)
                if not x.startswith("/api") and not FILE_SORGENTE.search(x)
            ]
            # Trappola 7: la stessa cosa, ma scritta senza lo slash iniziale
            # dentro un blocco di codice (`soggetti/{id}/titoli-iva/`,
            # `GET processi/`) — e la variante troncata coi puntini ASCII
            # (`.../{titolo_id}/ambiti/`), che RELATIVA prende senza sapere che
            # e' troncata. Quelle con lo slash e senza puntini le ha gia' prese.
            for blocco in CODICE.findall(riga):
                s = blocco.strip()
                troncata = s.startswith(("…", "..."))
                s = s.lstrip("…").lstrip(".")
                if FILE_SORGENTE.search(s):
                    continue
                if s.startswith("/"):
                    if troncata:
                        relative.append((s, True))
                    continue
                m = NUDA.match(s)
                if m:
                    relative.append((m.group(1), troncata))
            for x, troncata in relative:
                coda = norma("/" + x.lstrip("/"))
                seg = coda.strip("/").split("/")
                # ⛔ Una coda di SOLI segnaposto non nomina niente, e attaccata
                # a una base coprirebbe tutto cio' che le sta sotto:
                # `400/409/404` (tre codici HTTP in un blocco di codice)
                # diventa `/{}/{}/{}` e rendeva «documentata» ogni rotta a tre
                # segmenti sotto `lotti/`. L'unica che vale e' il singolo
                # `/{id}/`: e' il dettaglio della base, cioe' la forma relativa
                # di `api_resi.md` (`GET /<id>/`).
                if all(s in JOLLY for s in seg) and len(seg) != 1:
                    continue
                # La citazione grezza serve alla regola della CODA (trappola
                # 5): attaccata alla base darebbe `/definizioni/definizioni/…`.
                tutte[coda].add(f.name)
                for base in basi | sulla_riga:
                    tutte[norma(base + coda)].add(f.name)
                # I puntini dicono «il prefisso e' quello sopra»: la coda vale
                # per una rotta dell'AREA del file, qualunque sia il prefisso.
                # ⛔ Ma con ALMENO DUE segmenti: `…/export/` da solo e' la frase
                # «il path e' …/export/ in coda alla lista» di
                # `api_export_liste.md`, e ancorata all'area copriva ogni export
                # di ogni area — tre del lotto che nessuna pagina nomina. Un
                # segmento solo vive sulla base di RIGA (`GET /x/ (+ …/export/)`).
                # ⚠️ Non si passa da `norma`, che leggerebbe `{**}` come un id.
                if troncata and len(seg) >= 2:
                    for area in aree:
                        tutte[f"{area}/{{**}}{coda}"].add(f.name)
    return tutte, assolute


# Scopo: `{}` e `{*}` valgono come UN segmento qualunque, nei due versi
#        (trappola 2); `{**}` come uno o piu'. La differenza fra `{}` e `{*}`
#        la fa `generica`, non il match.
def _pattern(path: str) -> str:
    return (
        re.escape(path)
        .replace(r"\{\*\*\}", ".+")
        .replace(r"\{\*\}", "[^/]+")
        .replace(r"\{\}", "[^/]+")
    )


def _regex(path: str) -> re.Pattern[str]:
    return re.compile("^" + _pattern(path) + "$")


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
    if len(segmenti) < 3 or sum(1 for s in segmenti if s not in JOLLY) < 2:
        return None
    return re.compile(_pattern(path) + "$")


# Scopo: il predicato «questa rotta e' coperta» costruito dalle citazioni.
#        Sta fuori da `handle` perche' e' la parte che ha sbagliato due volte
#        (trappole 2 e 8), e va provata su casi costruiti, non sulla doc di oggi.
def matcher_copertura(
    tutte: dict[str, set[str]], assolute: dict[str, set[str]],
) -> Callable[[str], bool]:
    utili = [c for c in tutte if not generica(c, assoluta=c in assolute)]
    citazioni = [_regex(c) for c in utili]
    code = [rx for rx in (_regex_coda(c) for c in utili) if rx is not None]

    def coperta(path: str) -> bool:
        if any(rx.match(path) for rx in citazioni):
            return True
        return any(rx.search(path) for rx in code)

    return coperta


# I valori che riempiono il segnaposto di un converter Django. Fuori da qui
# (`str`, `slug`, `path`, un converter del progetto) vale un segmento qualunque.
_VALORE_DEL_CONVERTER = {
    "int": r"\d+",
    "uuid": r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}",
}
_CONVERTER = re.compile(r"<(?:(\w+):)?\w+>")


# Scopo: la regex delle ISTANZE di una rotta, dal path ORIGINALE (`valore[0]`
#        di `leggi_rotte`), che conserva i converter. Senza originale, o con
#        un path a regex (`re_path`), resta il segmento qualunque di `_regex`.
def _regex_istanza(normata: str, valore: Any) -> re.Pattern[str]:
    originale = valore[0] if isinstance(valore, tuple) and valore and valore[0] else ""
    if not originale or "(?" in originale:
        return _regex(normata)
    marcatori: list[str] = []

    def marca(m: re.Match[str]) -> str:
        marcatori.append(_VALORE_DEL_CONVERTER.get((m.group(1) or "str").lower(), "[^/]+"))
        return f"zzconv{len(marcatori) - 1}zz"

    forma = norma(_CONVERTER.sub(marca, originale))
    pattern = _pattern(forma)
    for i, valore_rx in enumerate(marcatori):
        pattern = pattern.replace(f"zzconv{i}zz", valore_rx)
    return re.compile("^" + pattern + "$")


# Scopo: il predicato «questa citazione e' servita da una rotta» (il contrario
#        di un fantasma). Fuori da `handle` per la stessa ragione di
#        `matcher_copertura`: si prova su casi costruiti.
def matcher_servita(rotte: dict[str, Any]) -> Callable[[str], bool]:
    # Trappola 4-bis (2026-10-21, §E del brief-be-verifica-documentazione-
    # api): un ESEMPIO non e' solo un numero o un uuid. `ruoli/CL/…`,
    # `processi/digest_presidi/…` scrivono un codice al posto del
    # segnaposto, e `VALORE_ESEMPIO` non puo' riconoscerli dalla forma.
    # Si guarda allora l'altro verso: la citazione e' un'ISTANZA di una
    # rotta se ogni suo segmento e' quello della rotta o ne riempie un
    # segnaposto. ⚠️ Solo per i fantasmi: un esempio non documenta la
    # rotta, e in copertura resta il verso prudente.
    # ⛔ E un segnaposto lo riempie solo un valore del suo CONVERTER: un
    #    `<int:pk>` vuole cifre, un `<uuid:…>` un uuid. Col solo `[^/]+` un
    #    fantasma letterale (`/ordini/esporta`) passava per un'istanza di
    #    `/ordini/<int:pk>` e spariva — il verso permissivo.
    istanze_di = [_regex_istanza(r, v) for r, v in rotte.items()]

    def servita(citazione: str) -> bool:
        rx = _regex(citazione)
        if any(rx.match(r) for r in rotte):
            return True
        if any(rx_rotta.match(citazione) for rx_rotta in istanze_di):
            return True
        # Trappola 6: una citazione di PREFISSO non e' un fantasma.
        # «Tutti gli endpoint sono sotto `/api/v1/core/tracciamento/`» non e'
        # una rotta mancante: e' una pagina che dice dove si e'.
        prefisso = re.compile("^" + _pattern(citazione) + "/")
        return any(prefisso.match(r) for r in rotte)

    return servita


class Command(ComandoAziendale):
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
        coperta = matcher_copertura(doc_tutte, doc_assolute)

        servita = matcher_servita(rotte)

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
