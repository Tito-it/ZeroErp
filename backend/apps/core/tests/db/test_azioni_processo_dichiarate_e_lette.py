# ------------------------------------------------------------
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: I tre presidi delle azioni di processo (brief-be-azioni-di-processo-
#        chi-le-legge §3): ogni azione dichiarata la valuta qualcuno, esiste a
#        catalogo attiva, e ogni azione attiva ha chi la legge.
#        - P-1: una view che `ZeroERPPermission` non valuta non dichiara
#          `<chiave>_permission` ne' `<chiave>_passaggio`; e una view che la
#          catena valuta li dichiara solo sulle chiavi che serve (il metodo
#          HTTP che implementa, o l'action del viewset);
#        - P-2: ogni azione dichiarata (`<chiave>_permission`) e ogni azione
#          passata a `PermissionResolver.check_azione` e' un
#          `permission_codename` attivo del seed `config/azioni_processo.csv`;
#        - P-3: ogni azione attiva ha almeno un lettore: il backend (P-2), una
#          riga di matrice di transizioni, il corpo di una funzione del DB, o
#          una riga del registro `_SEDE_PER_DOPO`, col motivo.
#
# ⛔ PERCHE' ESISTE. Nessuno dei tre difetti da' errore:
#    - un `post_permission` su una `AdminAPIView` sembra un cancello e non lo
#      valuta nessuno (`IsAdminZeroERP` risponde solo «SUPER_ADMIN o no»);
#    - un'azione letta e non a catalogo: `check_azione` dice «no» a tutti
#      tranne il SUPER_ADMIN, e nessun amministratore puo' concederla, perche'
#      non esiste la riga a cui appenderla;
#    - un'azione a catalogo che nessuno legge: il pannello la offre, e
#      concederla non cambia niente.
#    E' lo stesso difetto che `test_aree_dichiarate_a_catalogo` presidia per le
#    aree, e `test_catalogo_oggetti_rotte` per gli oggetti.
#
# ⭐ LE VIEW SI LEGGONO DAL PERCORSO REALE (`apps.core.api.rotte`,
#    `anche_condizionali=True`), con `getattr` come la catena: vede le classi
#    delle factory, gli attributi ereditati e le rotte montate a condizione.
# ⭐ LE CHIAMATE A `check_azione` SI LEGGONO DAL SORGENTE (AST), e l'argomento
#    si risolve come lo risolve Python: un letterale, o un nome di modulo letto
#    con `getattr` sul modulo importato (le costanti `AZIONE_*`). Un argomento
#    che non si risolve cosi' (una variabile, un parametro) e' un difetto,
#    salvo che la funzione che lo contiene stia in `_INOLTRI`, che dice da dove
#    arrivano i valori: un inoltro nuovo non passa in silenzio.
# ⭐ P-1 e P-2 non usano il DB: il catalogo si legge dal seed (BB `seed_csv`),
#    e il test va rosso nella PR che rompe l'allineamento, non all'apply.
# ⚠️ P-3 RICHIEDE IL DB VERO, opt-in `ZEROERP_TEST_DB_E2E=1` (accesa in CI).
#    Solo letture. Le matrici si trovano per NOME DI COLONNA
#    (`azione_processo_codename` in `information_schema.columns`), non da un
#    elenco: una matrice nuova entra da sola.
# ------------------------------------------------------------

"""Indice test.

AzioniDichiarateTests (senza DB):
 0. test_la_scansione_vede_view_e_chiamate
 1. test_p1_nessuna_azione_dove_non_la_valuta_nessuno
 2. test_p1_si_vede_rosso_su_una_view_finta
 2b. test_p1_nessuna_azione_su_una_chiave_che_la_view_non_serve
 2c. test_p1_chiave_si_vede_rosso_su_una_view_finta
 3. test_p2_ogni_azione_dichiarata_e_a_catalogo_attiva
 4. test_p2_si_vede_rosso_su_un_azione_inventata
 5. test_ogni_argomento_di_check_azione_si_risolve
 6. test_il_registro_inoltri_non_ha_righe_morte
 7. test_il_registro_sede_per_dopo_ha_il_motivo_e_azioni_attive
 8. test_il_registro_si_vede_rosso_su_una_riga_senza_motivo

AzioniLetteTests (opt-in `ZEROERP_TEST_DB_E2E=1`):
 9. test_le_matrici_si_trovano_e_hanno_righe
10. test_p3_ogni_azione_attiva_ha_un_lettore
11. test_il_registro_sede_per_dopo_esce_quando_l_azione_ha_un_lettore
"""

from __future__ import annotations

import ast
import importlib
from collections.abc import Iterable
from dataclasses import dataclass
from pathlib import Path
from unittest import TestCase

from django.db import connection
from django.test import SimpleTestCase
from rest_framework.viewsets import ViewSetMixin

from apps.core.api.base_views import AdminAPIView, DomainAPIView
from apps.core.api.permissions import PassaggioDocumento, ZeroERPPermission
from apps.core.api.rotte import classi_view
from apps.core.tests._repo import repo_root
from apps.core.tests._seed_csv import seed_csv
from apps.core.tests.db_e2e import richiedi_db_provvisto

_CATALOGO_CSV = "config/azioni_processo.csv"
_BACKEND = repo_root() / "backend"
_APPS = _BACKEND / "apps"

# ⏳ Azioni seminate PRIMA del loro verbo: a catalogo, attive, senza lettore
#    per scelta. Ogni riga col motivo. Il test 11 pretende che la riga esca il
#    giorno in cui l'azione trova un lettore (stessa strada di
#    `_IN_ATTESA_DI_CATALOGO` in `test_catalogo_oggetti_rotte`).
_SEDE_PER_DOPO: dict[str, str] = {
    "processo_avvia": (
        "«Esegui ora» dei processi e' una AdminAPIView (solo SUPER_ADMIN, "
        "brief-db-avvio-manuale-di-un-processo §8.5): la riga e' la sede per "
        "il giorno in cui il verbo si apre agli operatori"
    ),
}

# Le funzioni che passano a `check_azione` un valore che non e' un letterale
# ne' una costante di modulo, e da dove arriva quel valore:
# - un nome di parametro: i valori sono gli argomenti delle chiamate a quella
#   funzione nello stesso modulo (letterali, costanti, o liste di questi);
# - `None`: e' la catena dei permessi, che legge `<chiave>_permission` e
#   `<chiave>_passaggio` dalla view — i valori sono quelli che P-2 raccoglie
#   dalle view, e quelli delle matrici, che P-3 legge dal DB.
_INOLTRI: dict[tuple[str, str], str | None] = {
    ("apps.core.api.permissions", "valuta"): None,
    ("apps.ui.api.views_admin", "_require_any_action"): "codenames",
}


# Scopo: un punto del codice che nomina un'azione, per i messaggi.
@dataclass(frozen=True)
class Lettore:
    azione: object
    dove: str


# ----------------------------------------------------------------- catalogo

# Scopo: `permission_codename -> attivo` dal seed, letto come lo legge il
#        caricatore.
def _catalogo_seed() -> dict[str, bool]:
    righe = seed_csv(_CATALOGO_CSV)
    assert righe, f"catalogo vuoto: {_CATALOGO_CSV}"
    return {r["permission_codename"]: r["attivo"] == "t" for r in righe}


# --------------------------------------------------------------- le view

# Scopo: le dichiarazioni d'azione di una view, come le legge la catena:
#        `<chiave>_permission` (escluso `model_permission`, che e' un oggetto)
#        e `<chiave>_passaggio`. Gli attributi richiamabili non sono
#        dichiarazioni (`has_permission` e simili).
def _dichiarazioni(cls: type) -> list[tuple[str, object]]:
    trovate: list[tuple[str, object]] = []
    for nome in dir(cls):
        if nome == "model_permission":
            continue
        if not nome.endswith(("_permission", "_passaggio")):
            continue
        valore = getattr(cls, nome, None)
        if valore is None or (callable(valore) and not isinstance(valore, PassaggioDocumento)):
            continue
        trovate.append((nome, valore))
    return trovate


def _nome_view(cls: type) -> str:
    return f"{cls.__module__}.{cls.__qualname__}"


def _valutata_dalla_catena(cls: type) -> bool:
    return ZeroERPPermission in getattr(cls, "permission_classes", ())


# Scopo: P-1 su un insieme di classi: le dichiarazioni che nessuno valuta.
def _difetti_p1(classi: Iterable[type]) -> list[str]:
    difetti: list[str] = []
    for cls in classi:
        if _valutata_dalla_catena(cls):
            continue
        for nome, _ in _dichiarazioni(cls):
            classi_permesso = [p.__name__ for p in getattr(cls, "permission_classes", ())]
            difetti.append(f"{_nome_view(cls)}.{nome} con permission_classes={classi_permesso}")
    return sorted(difetti)


_AZIONI_STANDARD_VIEWSET: dict[str, str] = {
    "list": "list", "create": "create", "retrieve": "retrieve",
    "update": "update", "partial_update": "partial_update", "destroy": "destroy",
}


# Scopo: le chiavi che la catena puo' chiedere a una view: `action` per un
#        viewset (le standard che la classe implementa e le `@action`),
#        altrimenti il metodo HTTP in minuscolo, se la classe lo implementa.
def _chiavi_servite(cls: type) -> set[str]:
    chiavi = {m for m in getattr(cls, "http_method_names", ()) if hasattr(cls, m)}
    if issubclass(cls, ViewSetMixin):
        chiavi |= {a for a, metodo in _AZIONI_STANDARD_VIEWSET.items() if hasattr(cls, metodo)}
        chiavi |= {a.__name__ for a in cls.get_extra_actions()}
    return chiavi


# Scopo: P-1 sulle view della catena: una dichiarazione con una chiave che la
#        view non serve (`post_permission` su una view che serve solo DELETE)
#        non la chiede nessuno, e il gesto ricade sul livello d'area.
def _difetti_p1_chiave(classi: Iterable[type]) -> list[str]:
    difetti: list[str] = []
    for cls in classi:
        if not _valutata_dalla_catena(cls):
            continue
        servite = _chiavi_servite(cls)
        for nome, _ in _dichiarazioni(cls):
            chiave = nome.rsplit("_", 1)[0]
            if chiave not in servite:
                difetti.append(f"{_nome_view(cls)}.{nome}: la view serve {sorted(servite)}")
    return sorted(difetti)


# Scopo: le azioni dichiarate dalle view (`<chiave>_permission`).
def _azioni_delle_view() -> list[Lettore]:
    lettori: list[Lettore] = []
    for cls in classi_view(anche_condizionali=True):
        for nome, valore in _dichiarazioni(cls):
            if nome.endswith("_permission"):
                lettori.append(Lettore(valore, f"{_nome_view(cls)}.{nome}"))
    return lettori


# ------------------------------------------------- le chiamate a check_azione

def _moduli_backend() -> list[tuple[str, Path]]:
    moduli: list[tuple[str, Path]] = []
    for file in sorted(_APPS.rglob("*.py")):
        parti = file.relative_to(_BACKEND).with_suffix("").parts
        if "tests" in parti or "migrations" in parti:
            continue
        moduli.append((".".join(parti), file))
    assert moduli, f"nessun modulo sotto {_APPS}"
    return moduli


def _nome_chiamato(nodo: ast.Call) -> str | None:
    if isinstance(nodo.func, ast.Attribute):
        return nodo.func.attr
    if isinstance(nodo.func, ast.Name):
        return nodo.func.id
    return None


# Scopo: l'argomento di posizione `indice` o di nome `nome` di una chiamata.
def _argomento(nodo: ast.Call, indice: int, nome: str) -> ast.expr | None:
    for kw in nodo.keywords:
        if kw.arg == nome:
            return kw.value
    return nodo.args[indice] if len(nodo.args) > indice else None


_NON_RISOLTO = object()


# Scopo: il valore di un'espressione come lo vedrebbe Python a runtime, se e'
#        un letterale o un nome di modulo; `_NON_RISOLTO` altrimenti.
def _risolvi(espr: ast.expr, modulo: str) -> object:
    if isinstance(espr, ast.Constant):
        return espr.value
    if isinstance(espr, ast.Name):
        mod = importlib.import_module(modulo)
        return getattr(mod, espr.id, _NON_RISOLTO)
    return _NON_RISOLTO


# Scopo: la funzione (o il metodo) che contiene ogni nodo di un albero.
def _funzione_di(albero: ast.AST) -> dict[ast.AST, str | None]:
    funzione: dict[ast.AST, str | None] = {}

    def visita(nodo: ast.AST, dentro: str | None) -> None:
        for figlio in ast.iter_child_nodes(nodo):
            nome = (
                figlio.name
                if isinstance(figlio, (ast.FunctionDef, ast.AsyncFunctionDef))
                else dentro
            )
            funzione[figlio] = nome
            visita(figlio, nome)

    visita(albero, None)
    return funzione


@dataclass(frozen=True)
class ChiamateCheckAzione:
    lettori: list[Lettore]
    non_risolte: list[str]
    inoltri_usati: set[tuple[str, str]]


# Scopo: le azioni passate a `check_azione` nel backend. Un argomento non
#        risolvibile va in `non_risolte`, salvo che la funzione che lo
#        contiene sia in `_INOLTRI`: allora si leggono le chiamate a lei.
def _chiamate_check_azione() -> ChiamateCheckAzione:
    lettori: list[Lettore] = []
    non_risolte: list[str] = []
    usati: set[tuple[str, str]] = set()
    for modulo, file in _moduli_backend():
        testo = file.read_text(encoding="utf-8")
        if "check_azione" not in testo:
            continue
        albero = ast.parse(testo, filename=str(file))
        funzione = _funzione_di(albero)
        definizioni = {
            n.name: n for n in ast.walk(albero)
            if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))
        }
        for nodo in ast.walk(albero):
            if not isinstance(nodo, ast.Call) or _nome_chiamato(nodo) != "check_azione":
                continue
            # La definizione stessa (`def check_azione`) non e' una chiamata;
            # qui si guardano solo le chiamate.
            dove = f"{file.relative_to(repo_root())}:{nodo.lineno}"
            espr = _argomento(nodo, 1, "permission_codename")
            valore = _NON_RISOLTO if espr is None else _risolvi(espr, modulo)
            if valore is not _NON_RISOLTO:
                lettori.append(Lettore(valore, dove))
                continue
            chiave = (modulo, funzione.get(nodo) or "")
            if chiave not in _INOLTRI:
                non_risolte.append(f"{dove} (in {chiave[1] or 'modulo'})")
                continue
            usati.add(chiave)
            parametro = _INOLTRI[chiave]
            if parametro is None:
                continue
            lettori.extend(_argomenti_dell_inoltro(
                albero, modulo, file, definizioni[chiave[1]], parametro, non_risolte,
            ))
    return ChiamateCheckAzione(lettori, non_risolte, usati)


# Scopo: i valori passati, nello stesso modulo, al `parametro` della funzione
#        che inoltra a `check_azione`. Un valore non risolvibile e' un difetto.
def _argomenti_dell_inoltro(
    albero: ast.AST,
    modulo: str,
    file: Path,
    definizione: ast.FunctionDef | ast.AsyncFunctionDef,
    parametro: str,
    non_risolte: list[str],
) -> list[Lettore]:
    nomi = [a.arg for a in definizione.args.args]
    assert parametro in nomi, f"{definizione.name} non ha il parametro {parametro}"
    indice = nomi.index(parametro)
    lettori: list[Lettore] = []
    chiamate = 0
    for nodo in ast.walk(albero):
        if not isinstance(nodo, ast.Call) or _nome_chiamato(nodo) != definizione.name:
            continue
        chiamate += 1
        dove = f"{file.relative_to(repo_root())}:{nodo.lineno}"
        espr = _argomento(nodo, indice, parametro)
        elementi = espr.elts if isinstance(espr, (ast.List, ast.Tuple, ast.Set)) else [espr]
        for elemento in elementi:
            valore = _NON_RISOLTO if elemento is None else _risolvi(elemento, modulo)
            if valore is _NON_RISOLTO:
                non_risolte.append(f"{dove} (argomento di {definizione.name})")
            else:
                lettori.append(Lettore(valore, dove))
    if not chiamate:
        non_risolte.append(f"{definizione.name}: inoltro senza chiamate in {modulo}")
    return lettori


# Scopo: tutte le azioni nominate dal backend (view e chiamate).
def _lettori_backend() -> list[Lettore]:
    return _azioni_delle_view() + _chiamate_check_azione().lettori


# Scopo: P-2 su un insieme di lettori: chi nomina un'azione che non e' a
#        catalogo, o non e' attiva, o non e' una stringa.
def _difetti_p2(lettori: Iterable[Lettore], catalogo: dict[str, bool]) -> list[str]:
    difetti: list[str] = []
    for lettore in lettori:
        azione = lettore.azione
        if not isinstance(azione, str) or not azione:
            difetti.append(f"{lettore.dove}: non e' un codename ({azione!r})")
        elif azione not in catalogo:
            difetti.append(f"{lettore.dove}: {azione!r} non e' a catalogo")
        elif not catalogo[azione]:
            difetti.append(f"{lettore.dove}: {azione!r} e' a catalogo ma non attiva")
    return sorted(difetti)


# Scopo: le righe del registro senza motivo, o su azioni non attive.
def _difetti_registro(registro: dict[str, str], catalogo: dict[str, bool]) -> list[str]:
    difetti: list[str] = []
    for azione, motivo in registro.items():
        if not motivo or not motivo.strip():
            difetti.append(f"{azione}: riga senza motivo")
        if not catalogo.get(azione):
            difetti.append(f"{azione}: non e' un'azione attiva a catalogo")
    return sorted(difetti)


class AzioniDichiarateTests(SimpleTestCase):

    # 0) Una scansione che non vede niente farebbe passare tutto a vuoto.
    def test_la_scansione_vede_view_e_chiamate(self) -> None:
        self.assertTrue(_azioni_delle_view(), "nessuna <chiave>_permission sulle view")
        chiamate = _chiamate_check_azione()
        self.assertTrue(chiamate.lettori, "nessuna chiamata a check_azione risolta")
        # Le tre forme che il presidio deve saper leggere: una dichiarazione
        # di view, una costante di modulo, un inoltro con la lista.
        dove = {lettore.dove.split(":")[0] for lettore in chiamate.lettori}
        self.assertIn("backend/apps/core/services/coda_lavori/gestione_service.py", dove)
        self.assertIn("backend/apps/ui/api/views_admin.py", dove)

    def test_p1_nessuna_azione_dove_non_la_valuta_nessuno(self) -> None:
        difetti = _difetti_p1(classi_view(anche_condizionali=True))
        self.assertEqual(
            difetti, [],
            "view che dichiarano un'azione di processo senza ZeroERPPermission: "
            "la dichiarazione sembra un cancello e non la valuta nessuno\n"
            + "\n".join(difetti),
        )

    def test_p1_si_vede_rosso_su_una_view_finta(self) -> None:
        class FintaAdminConAzione(AdminAPIView):
            post_permission = "genera_fatture_lotti"

        class FintaAdminConPassaggio(AdminAPIView):
            post_passaggio = PassaggioDocumento("vendite.ordini", "ordine_id")

        class FintaDellaCatena(AdminAPIView):
            permission_classes = (ZeroERPPermission,)
            post_permission = "genera_fatture_lotti"

        difetti = _difetti_p1([FintaAdminConAzione, FintaAdminConPassaggio, FintaDellaCatena])
        self.assertEqual(len(difetti), 2, difetti)
        self.assertIn("FintaAdminConAzione.post_permission", difetti[0])
        self.assertIn("FintaAdminConPassaggio.post_passaggio", difetti[1])

    # 2b) Sulle view della catena la dichiarazione si legge con la chiave della
    #     richiesta: su una chiave che la view non serve non la chiede nessuno.
    #     L'ha trovata la revisione del 2026-11-14 su `ApiFondoFatturaDelete`.
    def test_p1_nessuna_azione_su_una_chiave_che_la_view_non_serve(self) -> None:
        difetti = _difetti_p1_chiave(classi_view(anche_condizionali=True))
        self.assertEqual(
            difetti, [],
            "dichiarazioni su una chiave che la view non serve: la catena non "
            "le chiede, e il gesto passa col livello d'area\n" + "\n".join(difetti),
        )

    def test_p1_chiave_si_vede_rosso_su_una_view_finta(self) -> None:
        class FintaSoloDelete(DomainAPIView):
            permission_classes = (ZeroERPPermission,)
            post_permission = "governa_fondo_fattura"

            def delete(self, request):  # pragma: no cover - mai chiamata
                return None

        class FintaGiusta(DomainAPIView):
            permission_classes = (ZeroERPPermission,)
            delete_permission = "governa_fondo_fattura"

            def delete(self, request):  # pragma: no cover - mai chiamata
                return None

        difetti = _difetti_p1_chiave([FintaSoloDelete, FintaGiusta])
        self.assertEqual(len(difetti), 1, difetti)
        self.assertIn("FintaSoloDelete.post_permission", difetti[0])

    def test_p2_ogni_azione_dichiarata_e_a_catalogo_attiva(self) -> None:
        difetti = _difetti_p2(_lettori_backend(), _catalogo_seed())
        self.assertEqual(
            difetti, [],
            f"azioni nominate dal backend fuori da {_CATALOGO_CSV} (o non attive): "
            "check_azione risponde no a tutti tranne il SUPER_ADMIN\n"
            + "\n".join(difetti),
        )

    def test_p2_si_vede_rosso_su_un_azione_inventata(self) -> None:
        catalogo = {"vera": True, "spenta": False}
        difetti = _difetti_p2(
            [
                Lettore("vera", "a"),
                Lettore("inventata", "b"),
                Lettore("spenta", "c"),
                Lettore(None, "d"),
            ],
            catalogo,
        )
        self.assertEqual(len(difetti), 3, difetti)
        self.assertIn("'inventata' non e' a catalogo", difetti[0])
        self.assertIn("'spenta' e' a catalogo ma non attiva", difetti[1])
        self.assertIn("non e' un codename", difetti[2])

    # 5) Un argomento che il presidio non sa leggere e' un'azione che P-2 non
    #    vede: si dichiara l'inoltro, o si passa una costante.
    def test_ogni_argomento_di_check_azione_si_risolve(self) -> None:
        non_risolte = _chiamate_check_azione().non_risolte
        self.assertEqual(
            non_risolte, [],
            "chiamate a check_azione con un argomento che non e' un letterale "
            "ne' una costante di modulo, fuori da _INOLTRI\n" + "\n".join(non_risolte),
        )

    def test_il_registro_inoltri_non_ha_righe_morte(self) -> None:
        usati = _chiamate_check_azione().inoltri_usati
        self.assertEqual(sorted(set(_INOLTRI) - usati), [])

    def test_il_registro_sede_per_dopo_ha_il_motivo_e_azioni_attive(self) -> None:
        self.assertEqual(_difetti_registro(_SEDE_PER_DOPO, _catalogo_seed()), [])

    def test_il_registro_si_vede_rosso_su_una_riga_senza_motivo(self) -> None:
        difetti = _difetti_registro({"vera": " ", "assente": "motivo"}, {"vera": True})
        self.assertEqual(
            difetti,
            ["assente: non e' un'azione attiva a catalogo", "vera: riga senza motivo"],
        )


# ----------------------------------------------------------------- P-3, il DB

# Scopo: le tabelle con una colonna `azione_processo_codename`, trovate per
#        nome: una matrice nuova entra da sola.
# ⚠️ Solo le TABELLE: una vista con quella colonna non e' una matrice, e una
#    vista che la proiettasse dal catalogo darebbe un lettore a ogni azione.
def _matrici(cur) -> list[tuple[str, str]]:
    cur.execute(
        """
        SELECT c.table_schema, c.table_name
          FROM information_schema.columns c
          JOIN information_schema.tables t USING (table_schema, table_name)
         WHERE c.column_name = 'azione_processo_codename'
           AND t.table_type = 'BASE TABLE'
           AND c.table_schema NOT IN ('pg_catalog', 'information_schema')
         ORDER BY 1, 2
        """
    )
    return [(r[0], r[1]) for r in cur.fetchall()]


# Scopo: azione -> le matrici che la nominano su una riga.
def _lettori_matrici(cur) -> dict[str, list[str]]:
    lettori: dict[str, list[str]] = {}
    for schema, tabella in _matrici(cur):
        cur.execute(
            f'SELECT DISTINCT azione_processo_codename FROM "{schema}"."{tabella}" '
            "WHERE azione_processo_codename IS NOT NULL"
        )
        for (azione,) in cur.fetchall():
            lettori.setdefault(azione, []).append(f"{schema}.{tabella}")
    return lettori


# Scopo: le azioni (fra quelle date) nominate come letterale nel corpo di una
#        funzione del database.
# ⚠️ Fuori: le funzioni delle estensioni (non sono codice del progetto) e gli
#    helper dei pgTAP (`fn_pgtap_*`), che costruiscono fixture: un'azione
#    nominata da un helper di test non ha un lettore.
def _lettori_funzioni(cur, azioni: list[str]) -> dict[str, list[str]]:
    cur.execute(
        """
        WITH corpi AS (
            SELECT n.nspname || '.' || p.proname AS nome,
                   pg_get_functiondef(p.oid) AS corpo
              FROM pg_proc p
              JOIN pg_namespace n ON n.oid = p.pronamespace
             WHERE p.prokind IN ('f', 'p')
               AND n.nspname NOT IN ('pg_catalog', 'information_schema')
               AND n.nspname NOT LIKE 'pg\\_%%'
               AND p.proname NOT LIKE 'fn\\_pgtap\\_%%'
               AND NOT EXISTS (
                   SELECT 1 FROM pg_depend d
                    WHERE d.classid = 'pg_proc'::regclass
                      AND d.objid = p.oid
                      AND d.deptype = 'e'
               )
        )
        SELECT a.azione, array_agg(DISTINCT c.nome ORDER BY c.nome)
          FROM unnest(%s::text[]) AS a(azione)
          JOIN corpi c ON strpos(c.corpo, quote_literal(a.azione)) > 0
         GROUP BY a.azione
        """,
        [azioni],
    )
    return {azione: list(nomi) for azione, nomi in cur.fetchall()}


class AzioniLetteTests(TestCase):

    @classmethod
    def setUpClass(cls) -> None:
        super().setUpClass()
        richiedi_db_provvisto()

    @staticmethod
    def _attive(cur) -> list[str]:
        cur.execute(
            "SELECT permission_codename FROM config.azioni_processo WHERE attivo ORDER BY 1"
        )
        return [r[0] for r in cur.fetchall()]

    # Scopo: azione attiva -> chi la legge, da tutte le fonti tranne il registro.
    def _lettori(self) -> tuple[list[str], dict[str, list[str]]]:
        with connection.cursor() as cur:
            attive = self._attive(cur)
            # Un catalogo letto vuoto (RLS, schema sbagliato) farebbe fallire
            # tutto per il motivo sbagliato: lo si dice prima.
            self.assertTrue(attive, "config.azioni_processo letta vuota")
            lettori: dict[str, list[str]] = {}
            for azione, dove in _lettori_matrici(cur).items():
                lettori.setdefault(azione, []).extend(dove)
            for azione, dove in _lettori_funzioni(cur, attive).items():
                lettori.setdefault(azione, []).extend(dove)
        for lettore in _lettori_backend():
            lettori.setdefault(str(lettore.azione), []).append(lettore.dove)
        return attive, lettori

    # 9) Una ricerca delle matrici che non trova niente farebbe passare P-3
    #    solo grazie alle altre fonti.
    def test_le_matrici_si_trovano_e_hanno_righe(self) -> None:
        with connection.cursor() as cur:
            matrici = _matrici(cur)
            self.assertIn(("config", "transizioni_stati_ordini"), matrici)
            self.assertTrue(_lettori_matrici(cur), "nessuna riga di matrice con un'azione")

    def test_p3_ogni_azione_attiva_ha_un_lettore(self) -> None:
        attive, lettori = self._lettori()
        senza = [a for a in attive if a not in lettori and a not in _SEDE_PER_DOPO]
        self.assertEqual(
            senza, [],
            "azioni attive che nessuno legge: il pannello le offre e concederle "
            "non cambia niente (o il lettore va dichiarato in _SEDE_PER_DOPO, col "
            f"motivo): {senza}",
        )

    def test_il_registro_sede_per_dopo_esce_quando_l_azione_ha_un_lettore(self) -> None:
        _, lettori = self._lettori()
        gia_lette = {a: lettori[a] for a in _SEDE_PER_DOPO if a in lettori}
        self.assertEqual(
            gia_lette, {},
            f"righe di _SEDE_PER_DOPO che hanno trovato un lettore: vanno tolte {gia_lette}",
        )
