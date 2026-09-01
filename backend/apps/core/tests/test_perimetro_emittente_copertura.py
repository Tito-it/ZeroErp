# ------------------------------------------------------------
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Presidio di COPERTURA del cancello di perimetro emittente: ogni lista
#        configurabile deve avere una view che dichiara `lista_codice`, oppure
#        stare nel registro delle esenzioni **con la sua ragione**.
#
#        Senza questo test «tutte le liste» significa «tutte quelle del giorno
#        in cui qualcuno le ha censite»: la 44ª nasce scoperta e nessuno lo
#        dice. E' lo stesso mestiere di
#        `test_liste_configurabili_seed.test_registro_copre_tutte_le_liste_
#        montate_dal_frontend`, applicato al cancello invece che al registro.
#
# Legge il codice sorgente con `ast` — nessun DB, nessun import delle view
# (che tirerebbero dentro mezza applicazione): gira in CI come tutti gli altri.
# ------------------------------------------------------------

"""
Indice test (0..N):
 0. test_ogni_lista_configurabile_ha_il_suo_cancello
 1. test_le_esenzioni_sono_tutte_ancora_necessarie
 2. test_nessun_lista_codice_punta_a_una_lista_inesistente
 3. test_lista_ed_export_stanno_o_cadono_insieme
 4. test_il_codice_citato_dal_frontend_esiste_a_catalogo

🕳️ **Buco dichiarato, e vale la pena saperlo**: qui NON c'e' un presidio che
   leghi la riga di catalogo al MAPPING del repository — «la colonna emittente
   dichiarata a catalogo arriva davvero nella riga?». Ci ho provato due volte,
   e nessuna delle due reggeva: la prima cercava la chiave in tutti i
   repository concatenati (verde anche togliendola da uno), la seconda contava
   le occorrenze (12 liste attese contro 15 mapping: il margine la rende cieca).
   Il presidio vero richiede una mappa lista → repository che oggi non esiste —
   il legame passa dalla view, e non e' ispezionabile staticamente.
   Quello che copre il rischio oggi: `test_liste_configurabili_seed` lega
   catalogo e whitelist di ORDINAMENTO per lista (ed e' vero, non un
   conteggio), e sulla lista pilota
   `test_ogni_campo_sorgente_di_catalogo_e_una_chiave_della_riga` apre il
   catalogo davvero. Sulle altre cinque il mapping e' stato verificato
   ESEGUENDO le query contro il database (Fase E, 2026-08-18).
"""

import ast
import csv
import re
import unittest
from functools import lru_cache
from pathlib import Path

from apps.core.tests.test_liste_configurabili_seed import (
    _LISTE,
    _colonne_attive,
    _seed,
)


# Scopo: root del repo, cercata risalendo (vedi test_liste_configurabili_seed).
def _repo_root() -> Path:
    for cartella in Path(__file__).resolve().parents:
        if (cartella / "db" / "changelog").is_dir():
            return cartella
    raise AssertionError("root del repo non trovata")


_APPS = _repo_root() / "backend/apps"
_USE_API_HANDLER = _repo_root() / "frontend/src/core/composables/useApiHandler.js"

# ⛔ Liste che NON possono avere il cancello, con la ragione. Non e' una lista
#    di comodo: sono tutte servite da `AdminAPIView`, e il cancello vive su
#    `DomainAPIView` per una decisione esplicita (brief perimetro-emittente,
#    passo C-2).
#
#    **Perche' l'amministrazione resta fuori**: sbarrare queste schermate
#    significherebbe chiedere al super admin di scegliere un emittente proprio
#    mentre sta configurando il sistema — e in due casi (`emittenti_fiscali`,
#    `emittente_billing_account`) mentre sta configurando **gli emittenti
#    stessi**, cioe' la cosa che gli si chiede di scegliere.
#
# ⚠️ Questo registro deve restare CORTO e motivato. Una lista di dominio che
#    finisse qui per far passare il test sarebbe un buco, non un'esenzione.
_ESENZIONI: dict[str, str] = {
    "anagrafiche.categorie_clienti": "AdminAPIView — configurazione anagrafica",
    "anagrafiche.categorie_clienti_listini": "AdminAPIView — configurazione pricing",
    "anagrafiche.emittente_billing_account": "AdminAPIView — configura la mappatura BA→emittente",
    "anagrafiche.emittenti_fiscali": "AdminAPIView — e' l'elenco degli emittenti stessi",
    "anagrafiche.operatori": "AdminAPIView — gestione utenti",
    "config.email_account": "AdminAPIView — configurazione tecnica",
    "config.email_log": "AdminAPIView — diario tecnico di sistema",
    "config.email_template": "AdminAPIView — configurazione tecnica",
    "config.tipi_ruolo_tipi_indirizzo": "AdminAPIView — matrice di configurazione",
    "config.utilities_tipi_ruolo": "AdminAPIView — matrice di configurazione",
}


# Scopo: UNA sola passata su `apps/`, che produce insieme le due cose che
#        servono: i `lista_codice` dichiarati e i nomi di tutte le classi.
# ⚠️ Il risultato e' memorizzato con `lru_cache`: la prima stesura riparsava
#        l'intero albero DENTRO un ciclo sulle classi, e i quattro test
#        impiegavano 34 secondi invece di uno. Un presidio lento e' un presidio
#        che qualcuno prima o poi toglie dalla corsa veloce.
@lru_cache(maxsize=1)
def _scansione() -> tuple[dict[str, tuple[str, ...]], frozenset[str]]:
    cancelli: dict[str, list[str]] = {}
    classi: set[str] = set()
    for percorso in _APPS.rglob("*.py"):
        if "/tests/" in str(percorso):
            continue
        try:
            albero = ast.parse(percorso.read_text(encoding="utf-8"))
        except SyntaxError:  # pragma: no cover - file non parsabile
            continue
        # ⚠️ Le costanti di MODULO prima delle classi, ed e' la differenza fra
        #    vedere un cancello e non vederlo: `lista_codice = _LISTA_CODICE`
        #    e' una dichiarazione come `lista_codice = "..."`, ma per `ast` e'
        #    un `Name` e `literal_eval` la scarta. Il presidio diceva quindi
        #    «`vendite.registri_numerazione` non ha nessun cancello» mentre il
        #    cancello c'era, dichiarato via costante — un rosso su una cosa
        #    giusta, che e' il modo piu' rapido di far disattivare un test.
        costanti: dict[str, str] = {}
        for stmt in albero.body:
            if (
                isinstance(stmt, ast.Assign)
                and len(stmt.targets) == 1
                and isinstance(stmt.targets[0], ast.Name)
                and isinstance(stmt.value, ast.Constant)
                and isinstance(stmt.value.value, str)
            ):
                costanti[stmt.targets[0].id] = stmt.value.value

        for nodo in ast.walk(albero):
            if not isinstance(nodo, ast.ClassDef):
                continue
            classi.add(nodo.name)
            for stmt in nodo.body:
                if (
                    isinstance(stmt, ast.Assign)
                    and isinstance(stmt.targets[0], ast.Name)
                    and stmt.targets[0].id == "lista_codice"
                ):
                    if isinstance(stmt.value, ast.Name):
                        # Costante dello stesso modulo: piu' in la' non si va
                        # (un import da un altro file resterebbe invisibile, e
                        # va saputo) — ma il caso vero e' questo.
                        codice = costanti.get(stmt.value.id)
                    else:
                        try:
                            codice = ast.literal_eval(stmt.value)
                        except ValueError:  # pragma: no cover - valore dinamico
                            continue
                    if isinstance(codice, str):
                        cancelli.setdefault(codice, []).append(nodo.name)
    return ({k: tuple(v) for k, v in cancelli.items()}, frozenset(classi))


# Scopo: `lista_codice` dichiarati nelle view, per codice -> nomi delle classi.
def _cancelli_dichiarati() -> dict[str, tuple[str, ...]]:
    return _scansione()[0]


# Suffissi con cui il progetto nomina le view di lista e i loro export. Non
# sono uniformi (`...List`, `...View`, `...Export`, `...ExportView`): la radice
# e' cio' che resta togliendoli, ed e' quella che accoppia le gemelle.
_SUFFISSI = ("ExportView", "Export", "ListView", "List", "View")


# Scopo: radice del nome di una view (`ApiDdtExportView` -> `ApiDdt`).
# Ritorna "" per i nomi che non finiscono con nessuno dei suffissi noti: non
# sono view di lista, e accoppiarli produrrebbe rumore.
def _radice(nome: str) -> str:
    for suffisso in _SUFFISSI:
        if nome.endswith(suffisso):
            return nome[: -len(suffisso)]
    return ""


class PerimetroEmittenteCoperturaTests(unittest.TestCase):
    def test_ogni_lista_configurabile_ha_il_suo_cancello(self) -> None:
        """Il cancello esiste su tutte le liste, o l'assenza e' dichiarata."""
        registro = {codice for codice, _ in _LISTE}
        coperte = set(_cancelli_dichiarati())
        # ⚠️ Un'esenzione per una lista che non esiste piu' resterebbe qui per
        #    sempre, e il registro smetterebbe di descrivere la realta'.
        fantasmi = sorted(set(_ESENZIONI) - registro)
        self.assertEqual(
            fantasmi, [],
            "esenzioni per liste che non sono (piu') a catalogo: togliere.",
        )
        scoperte = sorted(registro - coperte - set(_ESENZIONI))
        self.assertEqual(
            scoperte, [],
            "liste configurabili senza `lista_codice` su nessuna view: chi ha "
            "piu' di un emittente davanti le apre senza che nulla gli dica da "
            "quale emittente arrivano le righe. Aggiungere l'attributo alla "
            "view che le serve, o — se e' amministrazione — a `_ESENZIONI` "
            "con la ragione.",
        )

    def test_le_esenzioni_sono_tutte_ancora_necessarie(self) -> None:
        """Un'esenzione che ha ottenuto il suo cancello va TOLTA da qui.

        ⚠️ Il verso opposto conta quanto il primo: un registro che non cala
        smette di essere un elenco di eccezioni motivate e diventa il posto
        dove si mettono le cose per farle passare.
        """
        coperte = set(_cancelli_dichiarati())
        superate = sorted(set(_ESENZIONI) & coperte)
        self.assertEqual(
            superate, [],
            "liste esentate che ORA hanno il cancello: togliere la riga da "
            "`_ESENZIONI`, il debito e' pagato.",
        )

    def test_nessun_lista_codice_punta_a_una_lista_inesistente(self) -> None:
        """Un codice scritto male non sbarra niente e non lo dice.

        ⚠️ A runtime `guard_lista_per_codice` solleva `E_UI_LISTA_NON_TROVATA`
        — ma solo per chi ha lo scope multiplo, cioe' quasi nessuno: il difetto
        resterebbe invisibile per mesi. Qui si vede il giorno stesso.
        """
        a_catalogo = {r["codice"] for r in _seed("lista_definizione.csv")}
        fantasmi = sorted(set(_cancelli_dichiarati()) - a_catalogo)
        self.assertEqual(
            fantasmi, [],
            "`lista_codice` che non esiste in ui.lista_definizione.csv.",
        )

    def test_lista_ed_export_stanno_o_cadono_insieme(self) -> None:
        """Una lista e il suo export hanno lo stesso trattamento, nei DUE versi.

        ⚠️ **Il verso che si dimentica e' il secondo, ed e' il peggiore.**
        Il test 0 conta i CODICI: finche' anche una sola view dichiara
        `vendite.ddt`, quella lista risulta «coperta» — anche se il cancello e'
        rimasto solo sull'export e la lista a video passa. Verificato: togliendo
        `lista_codice` da `ApiDdtList` e lasciandolo sull'export, la prima
        stesura di questo file restava **verde**. E' verde per sottrazione, sul
        difetto peggiore dei due: i dati escono dalla porta larga, non da quella
        stretta.

        ⚠️ L'export e' la porta piu' larga (fino a 10.000 righe in una
        richiesta): rifiutare a video quello che si concede in un file e' il
        modo peggiore di avere un presidio. Il legame si riconosce dal NOME
        della classe — l'unica cosa che lega staticamente una lista al suo
        export.
        """
        cancelli, tutte_le_classi = _scansione()
        con_cancello = {c for classi in cancelli.values() for c in classi}

        # Coppie (lista, export) presenti nel codice, comunque dichiarate.
        # ⚠️ L'accoppiamento va fatto sulla RADICE del nome, non per prefisso:
        #    `X.startswith(base)` legava `ApiDashboardAperto` (che e' il
        #    riepilogo, non una lista) a `ApiDashboardApertoDocumentiExport`,
        #    che e' la gemella di tutt'altra classe — cinque falsi positivi.
        #    E i suffissi reali non sono uniformi: `ApiDdtList`/`ApiDdtExportView`,
        #    `ApiResiList`/`ApiResiExport`, `ClientiView`/`ClientiExportView`.
        per_radice: dict[str, dict[str, str]] = {}
        for classe in sorted(tutte_le_classi):
            radice = _radice(classe)
            if not radice:
                continue
            per_radice.setdefault(radice, {})[
                "export" if "Export" in classe else "lista"
            ] = classe
        coppie = [
            (v["lista"], v["export"])
            for v in per_radice.values()
            if "lista" in v and "export" in v
        ]
        squilibrate = [
            f"{base} ({'con' if base in con_cancello else 'SENZA'} cancello) "
            f"e {gemella} ({'con' if gemella in con_cancello else 'SENZA'})"
            for base, gemella in coppie
            if (base in con_cancello) != (gemella in con_cancello)
        ]
        self.assertEqual(
            squilibrate, [],
            "lista ed export trattati in modo diverso: "
            + "; ".join(squilibrate),
        )

    def test_il_codice_citato_dal_frontend_esiste_a_catalogo(self) -> None:
        """I codici che il frontend sopprime devono esistere davvero.

        `useApiHandler` non mostra il toast per alcuni codici, perche' a video
        c'e' gia' una schermata che dice la stessa cosa (oggi: il pannello del
        cancello di perimetro). Quel codice e' scritto a mano in un file
        JavaScript, e nessuno lo lega al catalogo.

        ⚠️ Il degrado sarebbe **benigno** — un codice rinominato fa ricomparire
        il toast, non nasconde un errore — ma il verso opposto no: una riga
        aggiunta li' dentro per un codice che non esiste **sembra** un presidio
        e non sopprime niente. E' lo stesso mestiere di
        `scripts/check_i18n_keys.py`, che lega le chiavi emesse dal DB alle
        traduzioni del frontend.
        """
        if not _USE_API_HANDLER.exists():  # pragma: no cover - repo parziale
            self.skipTest("frontend non presente")
        sorgente = _USE_API_HANDLER.read_text(encoding="utf-8")
        blocco = re.search(
            r"CODICI_SENZA_TOAST\s*=\s*new Set\(\[(.*?)\]\)", sorgente, re.S,
        )
        self.assertIsNotNone(
            blocco,
            "`CODICI_SENZA_TOAST` non trovato in useApiHandler.js: se e' stato "
            "rinominato o tolto, questo presidio va aggiornato o rimosso — non "
            "lasciato a cercare una cosa che non c'e'.",
        )
        assert blocco is not None
        citati = set(re.findall(r"'([A-Z_][A-Z0-9_]*)'", blocco.group(1)))
        self.assertTrue(citati, "nessun codice nel Set: presidio a vuoto.")
        a_catalogo = {
            r["codice"]
            for r in _seed_config("codici_errore.csv")
        }
        fantasmi = sorted(citati - a_catalogo)
        self.assertEqual(
            fantasmi, [],
            "codici soppressi dal frontend che non esistono in "
            "config/codici_errore.csv.",
        )


# Scopo: righe di un CSV di seed della cartella `config` (i codici errore).
#        `_seed` del modulo gemello legge la cartella `ui`: qui serve un'altra
#        cartella, non un'altra logica.
def _seed_config(nome: str) -> list[dict[str, str]]:
    percorso = (
        _repo_root() / "db/changelog/migrations_v2/80_data/sql/config" / nome
    )
    with percorso.open(newline="", encoding="utf-8") as fh:
        return list(csv.DictReader(fh))
