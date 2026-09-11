# ------------------------------------------------------------
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Test unitari colonne lineage nelle 7 liste documento (Fase B
#        brief-be-fe-lineage + la SESTA SORELLA `vendite.resi`, 2026-08-25 +
#        la SETTIMA `vendite.fatture`, 2026-08-29): whitelist ORDER BY estesa a
#        pratica/fase, NON-ridecodifica del tipo della frontiera (dal
#        20260829-02 la porta la vista) e prop del chip transito nei `.vue`.
# ------------------------------------------------------------

"""
Indice test eseguiti:
1) LineageListeOrderWhitelistTests.test_pratica_e_fase_ordinabili_su_tutte_le_liste
2) LineageListeOrderWhitelistTests.test_frontiera_non_ordinabile
3) LineageListeFrontieraDecodeTests.test_nessuna_lista_ridecodifica_il_tipo_della_frontiera
4) LineageListeChipPropTests.test_ogni_lista_col_transito_passa_la_natura_al_chip

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
from apps.core.tests.test_naming_codice_interno_python import _sorgente_senza_commenti

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
# repository che le possiede — serve al test 3, che ne legge il sorgente.
_WHITELISTS = {
    "preventivi": (preventivi_repository, preventivi_repository._ORDER_COLS_PREVENTIVI),
    "offerte": (offerte_repository, offerte_repository._ORDER_COLS_OFFERTE),
    "ordini": (ordini_repository, ordini_repository._ORDER_COLS_ORDINI),
    "contratti": (contratti_repository, contratti_repository._ORDER_COLS_CONTRATTI),
    "ddt": (ddt_repository, ddt_repository._ORDER_COLS_DDT),
    # ⭐ La sesta sorella (2026-08-25): `vw_resi_lista` prende `fase` + le nove
    #    colonne di genealogia, e su un reso la frontiera e' la NOTA DI CREDITO
    #    che lo accredita (arco S).
    "resi": (resi_repository, resi_repository._ORDER_COLS_RESI),
    # ⭐ La settima (2026-08-29): `vw_fatture_lista` porta le stesse quattro
    #    colonne `frontiera_*` delle sorelle, e il suo repository decodifica
    #    gia' il tipo della frontiera. ⚠️ Non monta (ancora) il chip «Transito»
    #    e la colonna non e' a catalogo: entra qui perche' il contratto che
    #    questi tre test presidiano — pratica/fase ordinabili, frontiera no,
    #    tipo decodificato — lo rispetta gia' tutto, e restarne fuori
    #    significherebbe solo che nessuno se ne accorge quando smettera'.
    "fatture": (fatture_repository, fatture_repository._ORDER_COLS_FATTURE),
}


class LineageListeOrderWhitelistTests(TestCase):
    # Scopo: pratica_numero e fase sono ordinabili su tutte e 7 le liste,
    #        mappate sulle colonne della vista (seed ui.lista_colonna:
    #        pratica.ordinabile=true, fase.ordinabile=true).
    def test_pratica_e_fase_ordinabili_su_tutte_le_liste(self):
        for nome, (_modulo, wl) in _WHITELISTS.items():
            with self.subTest(lista=nome):
                self.assertEqual(wl.get("pratica_numero"), "v.pratica_numero")
                self.assertEqual(wl.get("fase"), "v.fase")

    # Scopo: la frontiera (chip transito) NON e' ordinabile — nessuna colonna
    #        di ordinamento la espone (seed transito.ordinabile=false).
    def test_frontiera_non_ordinabile(self):
        for nome, (_modulo, wl) in _WHITELISTS.items():
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
    #        ⭐ Dal changeSet 20260829-02 il codice lo porta LA VISTA
    #        (`frontiera_tipo_codice_interno`), quindi le sette copie sono
    #        sparite e questo presidio si ribalta: nessuno deve RIMETTERLE.
    #        ⚠️ Il lato positivo — «la vista espone davvero la colonna» — NON e'
    #        piu' presidiabile da qui, e non e' scoperto: sta nel pgTAP
    #        `db/pgtap/vendite/test-colonne-lineage-liste-v1.sql`, test 40..46,
    #        che le enumera per nome su tutte e sette. Un test Python non puo'
    #        guardare il database (regola CI: nessuna dipendenza da un DB vero).
    def test_nessuna_lista_ridecodifica_il_tipo_della_frontiera(self):
        for nome, (modulo, _wl) in _WHITELISTS.items():
            with self.subTest(lista=nome):
                sorgente = _sorgente_senza_commenti(inspect.getsource(modulo))
                # ⚠️ Il join si cerca col suo alias `v` (la vista di lista) e con
                #    gli spazi liberi: `preventivi_repository` ha altri join
                #    LEGITTIMI a `config.sorgenti` — le sorgenti della pratica —
                #    e un `assertNotIn("config.sorgenti")` li boccerebbe a caso.
                self.assertNotRegex(
                    sorgente,
                    r"config\.sorgenti\s+\w+\s+ON\s+\w+\.id\s*=\s*v\.frontiera_tipo_id",
                    f"{nome}: la decodifica del tipo frontiera e' tornata nel "
                    "repository. La porta la vista: sette copie della stessa "
                    "riga sono il difetto che questo file esiste per fermare.",
                )
                # ⚠️ `\b` dopo il nome, non un `\n`: una regressione si riscrive
                #    quasi sempre con la virgola (`AS frontiera_tipo_codice,`) e
                #    un ancoraggio al fine-riga la lascerebbe passare. Il
                #    confine di parola non matcha `frontiera_tipo_codice_interno`,
                #    che e' il nome giusto.
                self.assertNotRegex(
                    sorgente, r"\bAS\s+frontiera_tipo_codice\b",
                    f"{nome}: alias locale su frontiera_tipo_codice — il nome "
                    "canonico e' `frontiera_tipo_codice_interno` e viaggia con "
                    "`v.*`; un alias qui ricrea un secondo nome per lo stesso "
                    "valore.",
                )


# Regex del montaggio di `<ListaConfigurabile codice="X">`, gemella di quella
# del presidio trasversale: si cerca `codice="..."` entro una finestra dal nome
# del tag invece di pretendere di sapere dove il tag finisce.
_RE_LISTA_CONFIGURABILE = re.compile(
    r"<ListaConfigurabile\b.{0,400}?(?<![:@\w-])codice=\"([^\"]+)\"", re.S
)


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
def _vue_per_lista() -> dict[str, list[tuple[str, str]]]:
    mappa: dict[str, list[tuple[str, str]]] = {}
    for percorso in sorted((repo_root() / "frontend" / "src").rglob("*.vue")):
        testo = _senza_commenti(percorso.read_text(encoding="utf-8"))
        for codice in set(_RE_LISTA_CONFIGURABILE.findall(testo)):
            mappa.setdefault(codice, []).append((percorso.name, testo))
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
            "20260829-02 la vista espone `frontiera_tipo_codice_interno` e il "
            "chip resterebbe muto.",
        )
