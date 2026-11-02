# ------------------------------------------------------------
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Test unitari colonne lineage nelle 7 liste documento (Fase B
#        brief-be-fe-lineage + la SESTA SORELLA `vendite.resi`, 2026-08-25 +
#        la SETTIMA `vendite.fatture`, 2026-08-29): whitelist ORDER BY estesa a
#        pratica/fase, NON-ridecodifica del tipo della frontiera (dal
#        20260829-02 la porta il grafo), prop del chip transito nei `.vue` e,
#        dal 2026-10-11, la sintesi lineage unita da ogni lista
#        (brief-db-lineage-seminata-per-chiave B1).
# ------------------------------------------------------------

"""
Indice test eseguiti:
1) LineageListeOrderWhitelistTests.test_pratica_e_fase_ordinabili_su_tutte_le_liste
2) LineageListeOrderWhitelistTests.test_frontiera_non_ordinabile
3) LineageListeFrontieraDecodeTests.test_nessuna_lista_ridecodifica_il_tipo_della_frontiera
4) LineageListeChipPropTests.test_ogni_lista_col_transito_passa_la_natura_al_chip
5) LineageListeSintesiTests.test_ogni_lista_unisce_la_sintesi_col_suo_tipo
6) LineageListeSintesiTests.test_ogni_lista_col_transito_e_servita_dalla_sintesi

⛔ QUESTO FILE ERA ANCORATO A CINQUE LISTE, ed e' la stessa trappola che il
   brief dell'arco S ha isolato sul lato pgTAP (§5 DB-F.3: i test ancorati a
   `lista_id IN (4..8)` restavano VERDI smettendo di coprire la lista nuova).
   Aggiungendo `vendite.resi` al seed senza toccare `_WHITELISTS` qui non ci
   sarebbe stato nessun rosso: la copertura sparisce in silenzio, che e' la
   forma peggiore perche' nessuno la va a cercare.
   ⭐ Regola: una lista documento nuova si aggiunge a `_WHITELISTS`, e i tre
   test la coprono senza scriverne uno nuovo.
   ⛔ 2026-08-29 — ED ERA ANCORA CORTO DI UNA. `vendite.fatture` (lista 48,
   `vw_fatture_lista`) porta le stesse quattro colonne `frontiera_*` delle
   sorelle e `fatture_repository` decodifica GIA' `frontiera_tipo_codice` —
   cioe' paga gia' il costo — ma stava fuori da questo registro. Non e' «una
   lista che non c'entra»: e' una lista dentro per meta' e fuori dal presidio.
   Oggi il chip «Transito» non e' montato sulla sua schermata e la colonna non
   e' a catalogo, quindi il difetto non si vede; il giorno in cui qualcuno la
   aggiungera', il chip nasce con l'etichetta sbagliata proprio dove nessuno
   guarda. ⭐ Entra per SIMMETRIA del modello, non perche' costi poco: e' una
   riga qui, e i tre test la coprono da sole.
"""

import inspect
import re
from unittest import TestCase

# ⭐ Riuso, non copia: `repo_root` (helper `_repo`), `_seed` e `_senza_commenti` esistono gia'
#    nel presidio trasversale delle liste configurabili e sono la stessa
#    identica esigenza (leggere il seed e i `.vue` distinguendo chi USA da chi
#    NOMINA). Importarli tiene UNA sede sola.
# ⚠️ MA LA SEDE E' SBAGLIATA, ed e' un debito dichiarato: sono nomi privati di
#    un MODULO DI TEST di un'altra app, e questo file si rompe se quel modulo
#    viene rinominato. La sede giusta e' un helper di test condiviso
#    (`apps/core/tests/_helpers.py` o simile). ⛔ Non estratto qui di
#    iniziativa: la regola del progetto e' dichiarare l'estrazione e aspettare
#    l'ok, e questo commento e' la dichiarazione.
from apps.core.tests._repo import repo_root
from apps.core.tests.test_liste_configurabili_seed import _seed, _senza_commenti

# ⭐ E lo spogliatore di commenti per il sorgente PYTHON vive dove sta il suo
#    presidio: il gemello Python del guardrail di naming, in `apps/core`. Era
#    nato qui in copia locale il 2026-08-29 ed e' durato un'ora — la terza
#    occorrenza della stessa esigenza («togli i commenti prima di cercare») ha
#    trovato una sede vera invece di diventare la terza copia.
from apps.core.tests._repo import sorgente_senza_commenti

from apps.vendite.services.vendite_service import LINEAGE_TIPI_DOCUMENTO
from apps.vendite.db import (
    contratti_repository,
    ddt_repository,
    fatture_repository,
    offerte_repository,
    ordini_repository,
    preventivi_repository,
    resi_repository,
)

# Le 7 whitelist ORDER BY delle liste documento (chiave FE campo_sorgente ->
# colonna SQL sull'alias `v` della vista canonica), accanto al modulo del
# repository che le possiede — serve ai test 3 e 5, che ne leggono il sorgente —
# e al tipo del documento nel grafo (`config.sorgenti.codice_interno`), che il
# repository passa alla sintesi lineage (test 5, dal 2026-10-11).
_WHITELISTS = {
    "preventivi": (preventivi_repository, preventivi_repository._ORDER_COLS_PREVENTIVI, "PREVENTIVO"),
    "offerte": (offerte_repository, offerte_repository._ORDER_COLS_OFFERTE, "OFFERTA_COMMERCIALE"),
    "ordini": (ordini_repository, ordini_repository._ORDER_COLS_ORDINI, "ORDINE_VENDITA"),
    "contratti": (contratti_repository, contratti_repository._ORDER_COLS_CONTRATTI, "CONTRATTO"),
    "ddt": (ddt_repository, ddt_repository._ORDER_COLS_DDT, "DDT_VENDITA"),
    # ⭐ La sesta sorella (2026-08-25): `vw_resi_lista` prende `fase` + le nove
    #    colonne di genealogia, e su un reso la frontiera e' la NOTA DI CREDITO
    #    che lo accredita (arco S).
    "resi": (resi_repository, resi_repository._ORDER_COLS_RESI, "RESO_VENDITA"),
    # ⭐ La settima (2026-08-29): `vw_fatture_lista` porta le stesse quattro
    #    colonne `frontiera_*` delle sorelle, e il suo repository decodifica
    #    gia' il tipo della frontiera. ⚠️ Non monta (ancora) il chip «Transito»
    #    e la colonna non e' a catalogo: entra qui perche' il contratto che
    #    questi tre test presidiano — pratica/fase ordinabili, frontiera no,
    #    tipo decodificato — lo rispetta gia' tutto, e restarne fuori
    #    significherebbe solo che nessuno se ne accorge quando smettera'.
    "fatture": (fatture_repository, fatture_repository._ORDER_COLS_FATTURE, "FATTURA"),
}


class LineageListeOrderWhitelistTests(TestCase):
    # Scopo: pratica_numero e fase sono ordinabili su tutte e 7 le liste,
    #        mappate sulle colonne della vista (seed ui.lista_colonna:
    #        pratica.ordinabile=true, fase.ordinabile=true).
    def test_pratica_e_fase_ordinabili_su_tutte_le_liste(self):
        for nome, (_modulo, wl, _tipo) in _WHITELISTS.items():
            with self.subTest(lista=nome):
                self.assertEqual(wl.get("pratica_numero"), "v.pratica_numero")
                self.assertEqual(wl.get("fase"), "v.fase")

    # Scopo: la frontiera (chip transito) NON e' ordinabile — nessuna colonna
    #        di ordinamento la espone (seed transito.ordinabile=false).
    def test_frontiera_non_ordinabile(self):
        for nome, (_modulo, wl, _tipo) in _WHITELISTS.items():
            with self.subTest(lista=nome):
                self.assertNotIn("frontiera_codice", wl)
                self.assertNotIn("transito", wl)


class LineageListeFrontieraDecodeTests(TestCase):
    # Scopo: ⛔ LO STESSO DIFETTO, PRESO DAL VERSO OPPOSTO. Fino al 2026-08-29
    #        questo test pretendeva che ogni repository DECODIFICASSE
    #        `frontiera_tipo_id` per conto suo, perche' il grafo esponeva solo
    #        l'id e il FE parla per `codice_interno`. Era la cura giusta per il
    #        difetto sbagliato: la decodifica era la STESSA riga ricopiata in
    #        sette repository, e dimenticarla non dava errore — spegneva la
    #        cella «Transito» in silenzio (successo il 25/08 sulla lista resi
    #        appena nata: colonna a catalogo, dato a DB, niente a video).
    #        ⭐ Dal changeSet 20260829-02 il codice lo porta il GRAFO
    #        (`frontiera_tipo_codice_interno`: prima la vista di lista, dal
    #        2026-10-11 la sintesi lineage unita dopo la paginazione), quindi le
    #        sette copie sono sparite e questo presidio si ribalta: nessuno deve
    #        RIMETTERLE.
    #        ⚠️ Il lato positivo — «la sintesi espone davvero la colonna» — NON
    #        e' presidiabile da qui: sta nei pgTAP
    #        `db/pgtap/vendite/test-colonne-lineage-liste-v1.sql` e
    #        `test-documento-lineage-v1.sql`. Un test Python non puo' guardare il
    #        database (regola CI: nessuna dipendenza da un DB vero). Che ogni
    #        lista CHIAMI la sintesi lo presidia il test 5.
    def test_nessuna_lista_ridecodifica_il_tipo_della_frontiera(self):
        for nome, (modulo, _wl, _tipo) in _WHITELISTS.items():
            with self.subTest(lista=nome):
                sorgente = sorgente_senza_commenti(inspect.getsource(modulo))
                # ⚠️ Il join si cerca col suo alias `v` (la vista di lista) e con
                #    gli spazi liberi: `preventivi_repository` ha altri join
                #    LEGITTIMI a `config.sorgenti` — le sorgenti della pratica —
                #    e un `assertNotIn("config.sorgenti")` li boccerebbe a caso.
                self.assertNotRegex(
                    sorgente,
                    r"config\.sorgenti\s+\w+\s+ON\s+\w+\.id\s*=\s*v\.frontiera_tipo_id",
                    f"{nome}: la decodifica del tipo frontiera e' tornata nel "
                    "repository. La porta la sintesi lineage: sette copie della "
                    "stessa riga sono il difetto che questo file esiste per fermare.",
                )
                # ⚠️ `\b` dopo il nome, non un `\n`: una regressione si riscrive
                #    quasi sempre con la virgola (`AS frontiera_tipo_codice,`) e
                #    un ancoraggio al fine-riga la lascerebbe passare. Il
                #    confine di parola non matcha `frontiera_tipo_codice_interno`,
                #    che e' il nome giusto.
                self.assertNotRegex(
                    sorgente, r"\bAS\s+frontiera_tipo_codice\b",
                    f"{nome}: alias locale su frontiera_tipo_codice — il nome "
                    "canonico e' `frontiera_tipo_codice_interno` e arriva dalla "
                    "sintesi lineage; un alias qui ricrea un secondo nome per lo "
                    "stesso valore.",
                )


# Regex del montaggio di `<ListaConfigurabile codice="X">`, gemella di quella
# del presidio trasversale: si cerca `codice="..."` entro una finestra dal nome
# del tag invece di pretendere di sapere dove il tag finisce.
# ⛔ Anche `<DrawerTabLista codice="X">` (2026-09-26): e' il contenitore delle
#    liste dentro un drawer, e inoltra il `codice` a `<ListaConfigurabile>`.
#    Senza, una lista montata in un drawer sfuggiva al presidio — il drawer dei
#    contratti del cliente non era mai stato guardato.
_RE_LISTA_CONFIGURABILE = re.compile(
    r"<(?:ListaConfigurabile|DrawerTabLista|ListaPaginaSemplice)\b.{0,400}?(?<![:@\w-])codice=\"([^\"]+)\"", re.S
)

# Import di un componente `.vue` con percorso relativo: (nome, percorso).
_RE_IMPORT_VUE = re.compile(r"""import\s+(\w+)(?:\s*,\s*\{[^}]*\})?\s+from\s+['"](\.{1,2}/[^'"]+\.vue)['"]""")


# Scopo: il componente `nome` e' montato DENTRO uno slot `cell-*` del file —
#        `#cell-x` o il dinamico `#[`cell-${c}`]` — entro una finestra che non
#        scavalca la chiusura della `<template>` (stessa tecnica «a finestra»
#        di `_RE_LISTA_CONFIGURABILE`).
def _montato_in_cella(testo: str, nome: str) -> bool:
    return re.search(
        r"#(?:cell-[\w-]+|\[`cell-[^`]*`\])[^>]*>(?:(?!</template>).){0,400}?<"
        + re.escape(nome) + r"[\s/>]",
        testo, re.S,
    ) is not None


# Scopo: le liste che DICHIARANO a catalogo la colonna «transito»
#        (`ui.lista_colonna`, seed CSV). ⭐ Si deriva dal SEED e non da un
#        elenco scritto qui: il seed e' il contratto, e una lista nuova entra da
#        sola invece di dover aggiornare un numero.
def _liste_con_colonna_transito() -> set[str]:
    ids = {
        r["lista_id"] for r in _seed("lista_colonna.csv")
        if r["codice"] == "transito" and r["attivo"] == "t"
    }
    return {
        r["codice"] for r in _seed("lista_definizione.csv")
        if r["id"] in ids and r["attivo"] == "t"
    }


# Scopo: codice lista -> TUTTI i `.vue` che la montano. Chi scrive
#        `<ListaConfigurabile codice="X">` dichiara di rendere X.
# ⚠️ Una lista, in linea di principio, puo' essere montata da piu' di un
#    componente: con un `dict[codice] = file` l'ultimo vincerebbe in silenzio e
#    il presidio guarderebbe UNO dei due a caso. Si tengono tutti e si
#    verificano tutti — se un giorno succede, il difetto si vede invece di
#    nascondersi dietro l'ordine alfabetico dei file.
# ⭐ Il testo di un montaggio comprende anche i componenti `.vue` che il file
#    IMPORTA direttamente (un livello) E MONTA IN UNO SLOT `cell-*`: le celle
#    di una lista possono stare in un componente condiviso — `ContrattoCella`,
#    per la schermata Contratti e per i contratti del cliente — e il chip si
#    monta li'. Senza, il presidio avrebbe chiesto di ricopiare le celle in
#    ogni file che monta la lista.
# ⛔ Solo quelli montati in cella, non tutti gli import: un drawer importato
#    che contiene un chip suo farebbe passare una lista che la cella
#    «transito» non la monta affatto — verde per addizione.
def _vue_per_lista() -> dict[str, list[tuple[str, str]]]:
    mappa: dict[str, list[tuple[str, str]]] = {}
    for percorso in sorted((repo_root() / "frontend" / "src").rglob("*.vue")):
        testo = _senza_commenti(percorso.read_text(encoding="utf-8"))
        codici = set(_RE_LISTA_CONFIGURABILE.findall(testo))
        if not codici:
            continue
        importati = [
            _senza_commenti((percorso.parent / rel).resolve().read_text(encoding="utf-8"))
            for nome, rel in _RE_IMPORT_VUE.findall(testo)
            if _montato_in_cella(testo, nome) and (percorso.parent / rel).resolve().is_file()
        ]
        completo = "\n".join([testo, *importati])
        for codice in codici:
            mappa.setdefault(codice, []).append((percorso.name, completo))
    return mappa


class LineageListeChipPropTests(TestCase):
    """⛔ Il presidio della PROP DIMENTICATA, che vive nei `.vue`.

    Il gemello che il brief chiedeva («come `test_ogni_lista_decodifica_...`»)
    non era scrivibile in quella forma: la natura arriva alle liste con `v.*`,
    quindi nel sorgente del repository non compare NIENTE da cercare — un test
    scritto per analogia sarebbe stato verde a vuoto.
    Il punto in cui la cosa puo' rompersi e' un altro: `LineageFrontieraChip`
    dichiara `naturaCodice`, e una lista che non la passa continua a scrivere
    «Fattura» sopra una nota di credito **senza nessun errore**. Una prop
    dichiarata e non passata e' un cancello che sembra esserci.

    ⭐ I DUE ESTREMI SI DERIVANO ENTRAMBI, e non c'e' nessun numero scritto qui:
    le liste attese vengono dal SEED (chi dichiara la colonna «transito»), i
    montaggi dai `.vue`. Cosi' il presidio prende anche il caso opposto — una
    lista che la colonna ce l'ha a catalogo e il chip non lo monta affatto, che
    e' il difetto del 25/08 visto dall'altra parte.
    """

    # Scopo: ogni lista che dichiara «transito» a catalogo monta il chip e gli
    #        passa la natura, coi nomi canonici delle colonne della vista.
    def test_ogni_lista_col_transito_passa_la_natura_al_chip(self):
        attese = _liste_con_colonna_transito()
        # ⚠️ Un insieme vuoto qui sarebbe verde per sottrazione: il test
        #    passerebbe smettendo di verificare (seed spostato, colonna
        #    rinominata). Si dichiara che almeno una ci deve essere.
        self.assertTrue(
            attese,
            "nessuna lista dichiara la colonna «transito» nel seed: il presidio "
            "sta guardando nel posto sbagliato, non e' il catalogo a essere vuoto.",
        )
        montaggi = _vue_per_lista()
        for codice in sorted(attese):
            with self.subTest(lista=codice):
                self.assertIn(
                    codice, montaggi,
                    f"{codice}: dichiara la colonna «transito» a catalogo ma "
                    "nessun .vue monta <ListaConfigurabile> per questa lista.",
                )
                for nome, testo in montaggi[codice]:
                    self._verifica_montaggio(nome, testo)

    # Scopo: le tre asserzioni su UN montaggio del chip (una lista puo' essere
    #        montata da piu' componenti: valgono per tutti, non per il primo).
    def _verifica_montaggio(self, nome: str, testo: str) -> None:
        # ⚠️ Confine dopo il nome del tag, non `assertIn` secco: la sottostringa
        #    direbbe di si' anche a un `<LineageFrontieraChipV2>`, cioe' a un
        #    componente diverso con lo stesso prefisso — proprio il caso in cui
        #    il contratto delle props puo' essere un altro.
        self.assertRegex(
            testo, r"<LineageFrontieraChip[\s/>]",
            f"{nome}: la lista ha la colonna «transito» a catalogo ma non monta "
            "il chip — la cella resterebbe vuota, senza errore.",
        )
        self.assertRegex(
            testo, r":natura-codice=\"data\.frontiera_natura_doc_codice_interno\"",
            f"{nome}: monta LineageFrontieraChip senza passargli la natura — la "
            "colonna «Transito» chiamerebbe «Fattura» ogni nota di credito, "
            "senza errore.",
        )
        self.assertRegex(
            testo, r":tipo-codice=\"data\.frontiera_tipo_codice_interno\"",
            f"{nome}: legge ancora il nome vecchio del tipo frontiera; dal "
            "20260829-02 il grafo espone `frontiera_tipo_codice_interno` e il "
            "chip resterebbe muto.",
        )


class LineageListeSintesiTests(TestCase):
    """Le colonne del grafo arrivano alle liste dalla sintesi lineage.

    Dal `20261011-97` le viste di lista non portano piu' frontiera, discendenti
    e transito: li unisce `unisci_sintesi_lineage` dopo la paginazione. Una
    lista che non la chiama non da' errore — il chip «Transito» esce VUOTO, e
    con lui la colonna dell'export, che chiama gli stessi metodi.
    """

    # Scopo: ogni lista del registro chiama la sintesi, col SUO tipo del
    #        grafo — un tipo sbagliato (ordini col tipo dei DDT) non trova i
    #        nodi e lascia le colonne a NULL, anche qui senza errore. Il tipo
    #        si passa con la costante di `apps.config.sorgenti`
    #        (`SORGENTE_<codice>`), che il suo presidio lega al seed.
    def test_ogni_lista_unisce_la_sintesi_col_suo_tipo(self):
        tipi = [tipo for _modulo, _wl, tipo in _WHITELISTS.values()]
        self.assertEqual(len(tipi), len(set(tipi)), "due liste col tipo del grafo uguale")
        for nome, (modulo, _wl, tipo) in _WHITELISTS.items():
            with self.subTest(lista=nome):
                self.assertIn(tipo, LINEAGE_TIPI_DOCUMENTO)
                sorgente = sorgente_senza_commenti(inspect.getsource(modulo))
                self.assertRegex(
                    sorgente,
                    r"unisci_sintesi_lineage\(\s*results\s*,\s*tipo_codice_interno\s*=\s*"
                    + re.escape(f"SORGENTE_{tipo}") + r"\s*\)",
                    f"{nome}: la lista non unisce la sintesi lineage col tipo "
                    f"{tipo}: frontiera e transito uscirebbero vuoti.",
                )

    # Scopo: ogni lista che dichiara «transito» a catalogo e' servita da un
    #        repository del registro (cioe' da uno che unisce la sintesi). La
    #        guardia del catalogo (`20261011-99`) accetta un `campo_sorgente`
    #        della sintesi su QUALUNQUE lista: senza questo presidio una lista
    #        nuova con la colonna passerebbe il seed e mostrerebbe la cella
    #        vuota. ⭐ Le liste attese vengono dal SEED, non da un elenco qui.
    def test_ogni_lista_col_transito_e_servita_dalla_sintesi(self):
        attese = _liste_con_colonna_transito()
        self.assertTrue(attese, "nessuna lista dichiara «transito» nel seed")
        for codice in sorted(attese):
            with self.subTest(lista=codice):
                self.assertIn(
                    codice.removeprefix("vendite."), _WHITELISTS,
                    f"{codice}: ha la colonna «transito» a catalogo ma il suo "
                    "repository non e' nel registro delle liste che uniscono la "
                    "sintesi lineage.",
                )
