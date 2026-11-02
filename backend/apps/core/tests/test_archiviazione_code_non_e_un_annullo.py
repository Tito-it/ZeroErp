# ------------------------------------------------------------
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Presidio del §3 di `brief-db-archiviazione-righe-code`: la bandiera
#        `archiviato` la legge SOLO chi mostra l'elenco. Claim, drainer, reaper,
#        `mark_*` e `count_*` non la devono nemmeno nominare.
#
# ⛔ PERCHE' ESISTE, ed e' scritto nel brief che lo chiede (§15): quel contratto
#    oggi e' rispettato, ma non lo presidia niente — e' una frase in prosa. I
#    test esistenti coprono il verso POSITIVO («le archiviate sono nascoste
#    dall'elenco») e non quello NEGATIVO, che e' l'unico che conta qui:
#    **nessun altro le nasconde**.
#
# 🔴 IL DIFETTO CHE PREVIENE non e' un errore, e' un CAMBIO DI SIGNIFICATO. Il
#    giorno che qualcuno aggiunge `AND NOT archiviato` a un `claim` «per
#    coerenza», l'archiviazione smette di essere una preferenza di vista e
#    diventa un ANNULLAMENTO SILENZIOSO: la riga resta nei conteggi, sembra viva,
#    e non la lavora piu' nessuno. ⚠️ Cioe' peggio della cancellazione che questa
#    richiesta esiste per evitare — e nessun test diventerebbe rosso.
#
# ⭐ E' UNA WHITELIST, non un elenco di colpevoli: si dichiarano i metodi che la
#    bandiera PUO' nominare, e ogni altro deve tacere. Un elenco di metodi
#    proibiti resterebbe indietro al primo metodo nuovo — che e' esattamente
#    quando il difetto entra.
#
# ⚠️ Nessun database: legge il sorgente dei due repository, quindi gira in CI.
# ------------------------------------------------------------
"""Indice test:

1. test_solo_l_elenco_nomina_la_bandiera
   Il contratto: fuori dalla whitelist la parola non compare.

2. test_la_whitelist_nomina_metodi_che_esistono
   ⛔ Una whitelist che elenca metodi scomparsi e' un presidio che non presidia:
   il metodo rinominato esce dal controllo senza che niente fallisca.

3. test_l_elenco_la_nomina_davvero
   ⛔ Il verso positivo, che tiene onesto il rilevamento: se il filtro sparisse
   dall'elenco, il test 1 resterebbe verde — e sarebbe verde su un'applicazione
   che mostra le archiviate a tutti.
"""

from __future__ import annotations

import ast
import re
from pathlib import Path
from unittest import TestCase
from apps.core.tests._repo import repo_root

# ⭐ Ogni forma della parola: `archiviato`, `archiviate`, `includi_archiviate`,
#    `archiviato_il`, `archiviato_da`. Il contratto e' sulla COSA, non su una
#    grafia — e cercare il solo `archiviato` lascerebbe passare il conteggio.
_PAROLA = re.compile(r"archiviat", re.IGNORECASE)


# ⭐ I DUE REPOSITORY DELLE CODE, e per ciascuno i metodi che la bandiera puo'
#    nominare. Sono TRE per file, e ognuno ha la sua ragione:
#      · `elenca*`            — la lista: e' il solo posto dove archiviare
#                               significa qualcosa;
#      · `imposta_archiviato*`— il verbo che alza e abbassa la bandiera;
#      · `get_dettaglio`      — il dettaglio di UNA riga chiesta per id.
#        ⚠️ Non filtra e non deve: nascondere a un operatore la riga che ha
#           appena archiviato — o che apre da un link — sarebbe la stessa
#           sparizione che il §3 vieta. Sta in whitelist perche' la PROIETTA,
#           non perche' la filtri.
_WHITELIST: dict[str, set[str]] = {
    "backend/apps/core/services/coda_lavori/repository.py": {
        "elenca", "imposta_archiviato", "get_dettaglio",
    },
    "backend/apps/vendite/db/pipeline_repository.py": {
        "elenca_coda_stampa", "imposta_archiviato_stampa",
    },
}


# Scopo: i metodi di un file che nominano la bandiera, col numero di riga.
# ⚠️ Si guardano le sole FUNZIONI: le mappe di ordinamento a livello di modulo
#    (`archiviato_il` come colonna ordinabile) sono un'altra cosa — dichiarano
#    che la lista puo' ordinarci sopra, che e' proprio il percorso ammesso.
def _metodi_che_la_nominano(percorso: Path) -> dict[str, int]:
    # ⚠️ Il sorgente si legge UNA volta e si passa: `get_source_segment` lo vuole
    #    per ogni nodo, e rileggerlo dentro il ciclo faceva un accesso al disco
    #    per METODO — su questi due file sono centinaia, e per giunta il
    #    presidio finirebbe per confrontare parti di due letture diverse se il
    #    file cambiasse a meta' corsa.
    sorgente = percorso.read_text()
    albero = ast.parse(sorgente)
    trovati: dict[str, int] = {}
    for nodo in ast.walk(albero):
        if not isinstance(nodo, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        if _PAROLA.search(ast.get_source_segment(sorgente, nodo) or ""):
            trovati[nodo.name] = nodo.lineno
    return trovati


class ArchiviazioneCodeNonEUnAnnullo(TestCase):
    """La bandiera `archiviato` la legge solo chi mostra l'elenco."""

    # 1. ⛔ Fuori dalla whitelist, la parola non compare.
    def test_solo_l_elenco_nomina_la_bandiera(self) -> None:
        colpevoli: list[str] = []
        for relativo, ammessi in _WHITELIST.items():
            percorso = repo_root() / relativo
            for metodo, riga in _metodi_che_la_nominano(percorso).items():
                if metodo not in ammessi:
                    colpevoli.append(f"{relativo}:{riga} {metodo}()")
        self.assertEqual(
            sorted(colpevoli), [],
            "un percorso di LAVORO nomina `archiviato`: la bandiera e' una "
            "preferenza di VISTA (§3 di brief-db-archiviazione-righe-code) e "
            "fuori dall'elenco non deve esistere. Nel claim, nel drainer, nel "
            "reaper o in un `mark_*` trasforma l'archiviazione in un "
            "annullamento silenzioso — la riga resta nei conteggi, sembra viva, "
            f"e non la lavora piu' nessuno: {sorted(colpevoli)}",
        )

    # 2. ⛔ La whitelist parla di metodi che esistono. Un nome rinominato la
    #    farebbe scivolare fuori dal controllo **senza** far fallire il test 1.
    def test_la_whitelist_nomina_metodi_che_esistono(self) -> None:
        for relativo, ammessi in _WHITELIST.items():
            percorso = repo_root() / relativo
            albero = ast.parse(percorso.read_text())
            definiti = {
                n.name for n in ast.walk(albero)
                if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))
            }
            fantasmi = sorted(ammessi - definiti)
            self.assertEqual(
                fantasmi, [],
                f"la whitelist di {relativo} ammette metodi che non esistono "
                f"piu': rinominati o tolti, e con loro il presidio: {fantasmi}",
            )

    # 3. ⛔ IL VERSO POSITIVO, che tiene onesto il rilevamento. Senza, cancellare
    #    il filtro dall'elenco lascerebbe il test 1 verde — su un'applicazione
    #    che mostra le archiviate a chiunque.
    def test_l_elenco_la_nomina_davvero(self) -> None:
        for relativo, ammessi in _WHITELIST.items():
            percorso = repo_root() / relativo
            nominanti = set(_metodi_che_la_nominano(percorso))
            elenco = {m for m in ammessi if m.startswith("elenca")}
            self.assertTrue(
                elenco & nominanti,
                f"in {relativo} l'elenco NON nomina piu' `archiviato`: o il "
                "filtro e' sparito — e le righe archiviate si vedono tutte — "
                "oppure il rilevamento di questo presidio e' rotto.",
            )
