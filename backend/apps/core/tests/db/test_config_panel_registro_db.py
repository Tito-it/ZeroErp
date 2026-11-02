# ------------------------------------------------------------
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: ⭐ CIO' CHE IL PANNELLO CONFIG DICHIARA SI PROVA PER INTERO
#        (`feedback_contratto_dichiarato_provalo_intero`): per OGNI riga di
#        `config.tabelle_gestibili` con `pannello` la lista risponde (passa dal
#        lookup generico), il metadata risponde con le colonne del verbo, ogni
#        colonna ha la sua etichetta in it.json E en.json, ogni FK nomina una
#        relazione che esiste e il flag `references_lookup` dice il vero. Nasce
#        il 2026-09-21 dal caso `magazzino.lotti`: dichiarata nel registro,
#        senza `descrizione`, rifiutata dal lookup con un 400 che il pannello
#        ingoiava — a video «lista vuota», e nessun presidio lo vedeva.
#        Dal 2026-09-28 il registro del frontend (`config-tables.js`) non c'e'
#        piu' (D-P5, brief-db-pannello-config-verbo-generico): il pannello
#        elenca `GET /core/config/tables/`, cioe' la lista a DB, e qui si legge
#        quella.
# Note: ⚠️ Le chiavi delle etichette sono COSTRUITE dal nome della colonna
#       (`config_panel.campi.<col>`): `check_i18n_keys.py` non le vede, e a
#       video il ripiego e' il nome grezzo — cioe' il difetto che questo
#       cantiere ha chiuso. Questo test e' l'unico che se ne accorge.
#       Gira sul DB provvisto (`richiedi_db_provvisto`): le etichette sono del
#       FE, tabelle e colonne del DB, e la giuntura la vede solo chi li legge
#       insieme.
# ------------------------------------------------------------
#
# Indice test:
#  1. il metadata di ogni rel offre `id` e le colonne che il verbo scrive
#     (`config.fn_pannello_colonne_scrivibili`), non altre: la sede unica
#     della regola (§6.1). Un campo in piu' nel form e' un salvataggio respinto
#  2. ogni rel risponde alla lista (`fn_list_lookup_codici`, i parametri del pannello)
#  3. ogni colonna del metadata ha l'etichetta in it.json e en.json; `uid` mai
#  4. ogni `references` e' una relazione esistente; `references_column` e' la
#     colonna referenziata; `references_lookup` e' vero sse la relazione e' fra
#     quelle del lookup (`config.tabelle_gestibili.lookup`) — e in quel caso la colonna e' una che il lookup porta
#     (`LOOKUP_COLONNE_VALORE`), altrimenti la `LookupSelect` salverebbe `undefined`
#  5. ogni rel del pannello ha l'etichetta `config_panel.tabelle.<schema>.<tabella>`
#     in it.json e en.json (a video il ripiego e' la rel grezza)
#  6. ogni rel che il FRONTEND passa al lookup generico (letta dal sorgente)
#     e' nel lookup a DB

from __future__ import annotations

import json
import re
from pathlib import Path
from unittest import TestCase

from django.db import connection, transaction

from apps.core.db.config_metadata_repository import ConfigMetadataRepository
from apps.core.db.dbops_repository import LOOKUP_COLONNE_VALORE
from apps.core.db.tabelle_gestibili_repository import TabelleGestibiliRepository
from apps.core.services.lookup_service import fn_list_lookup_codici
from apps.core.tests.db_e2e import apri_contesto_operatore, richiedi_db_provvisto

_ROOT = Path(__file__).resolve().parents[5]
_LOCALES = _ROOT / "frontend" / "src" / "locales"
_PREFISSO = "config_panel.campi"


# Le forme con cui il frontend passa una rel al LOOKUP GENERICO: la prop `rel`
# di LookupSelect (e `rel:` negli oggetti di configurazione), il parametro
# `?rel=` di un URL, e i tre composable che lo chiamano.
# ⛔ Non `useGlobalLookup(chiave, fetcher)`: la chiave e' un nome di cache, e il
#    fetcher e' spesso un endpoint dedicato (`amm.audit_sources`,
#    `anagrafiche.risorse_umane`), non il lookup generico.
# ⚠️ `:rel="espressione"` e' un binding Vue, non una rel: conta solo se dentro
#    c'e' un letterale (`:rel="'config.iva'"`).
_RE_REL_FRONTEND = re.compile(
    r"""(?:(?<!:)\brel\s*[=:]\s*['"]|:rel\s*=\s*"'|[?&]rel="""
    r"""|\b(?:useLookupCodici|useLookupEtichettato|lookupCodici)\(\s*['"])"""
    r"""([a-z_]+\.[a-z_]+)"""
)


# Scopo: le rel che il frontend passa al lookup generico, con il primo file
#        che le nomina (per il messaggio del rosso).
def _rel_del_frontend() -> dict[str, str]:
    trovate: dict[str, str] = {}
    for file in sorted((_ROOT / "frontend" / "src").rglob("*")):
        if file.suffix not in (".vue", ".js") or not file.is_file():
            continue
        for rel in _RE_REL_FRONTEND.findall(file.read_text(encoding="utf-8")):
            trovate.setdefault(rel, str(file.relative_to(_ROOT)))
    return trovate


# Scopo: il blocco `config_panel` di un locale.
def _config_panel(locale: str) -> dict:
    dati = json.loads((_LOCALES / f"{locale}.json").read_text(encoding="utf-8"))
    return dati["config_panel"]


# Scopo: le chiavi `config_panel.campi.*` di un locale.
def _etichette(locale: str) -> set[str]:
    return set(_config_panel(locale)["campi"])


# Scopo: le rel con etichetta `config_panel.tabelle.<schema>.<tabella>` di un locale.
def _etichette_tabelle(locale: str) -> set[str]:
    tabelle = _config_panel(locale).get("tabelle", {})
    return {f"{schema}.{tab}" for schema, tabs in tabelle.items() for tab in tabs}


class ConfigPanelRegistroDbTests(TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        super().setUpClass()
        richiedi_db_provvisto()
        lista = TabelleGestibiliRepository()
        cls.rels = [v["rel"] for v in lista.voci_pannello()]
        # ⚠️ Vuota = seed non caricato: i test sotto passerebbero a vuoto.
        assert cls.rels, "config.tabelle_gestibili senza righe `pannello`: seed non caricato?"
        cls.rel_lookup = lista.rel_lookup()

    # 1. ⭐ Il form e il verbo rispondono dalla STESSA funzione: si confronta il
    #    metadata con la funzione, tabella per tabella, e anche l'ordine (e'
    #    l'ordine dei campi a video).
    def test_il_metadata_offre_le_colonne_che_il_verbo_scrive(self) -> None:
        meta = ConfigMetadataRepository()
        diverse: dict[str, tuple] = {}
        with connection.cursor() as cur:
            for rel in self.rels:
                schema, tabella = rel.split(".", 1)
                cur.execute("SELECT config.fn_pannello_colonne_scrivibili(%s)", [rel])
                riga = cur.fetchone()
                assert riga is not None
                attese = riga[0] or []
                colonne = meta.get_table_columns(schema, tabella)
                offerte = [c["name"] for c in colonne if not c["is_pk"]]
                chiavi = [c["name"] for c in colonne if c["is_pk"]]
                if offerte != attese or chiavi != ["id"]:
                    diverse[rel] = (chiavi + offerte, ["id", *attese])
        self.assertEqual(diverse, {}, "metadata (offerte) diverso dalle colonne scrivibili del verbo (attese)")

    # 2. Ogni rel in un savepoint: si vogliono TUTTE le rotte in un giro, non
    #    la prima (il 21-09 erano tre — lotti, stati, titoli_cortesia — e una
    #    per corsa le avrebbe fatte scoprire in tre corse).
    def test_ogni_rel_risponde_alla_lista_del_pannello(self) -> None:
        rotte: dict[str, str] = {}
        with transaction.atomic():
            with connection.cursor() as cur:
                apri_contesto_operatore(cur)
            for rel in self.rels:
                try:
                    with transaction.atomic():
                        dati = fn_list_lookup_codici(
                            rel=rel, search=None, order_col="descrizione", order_dir="asc",
                            attivo_only=False, limit=1, offset=0,
                        )
                        self.assertIsInstance(dati["count"], int, rel)
                except Exception as exc:  # si raccoglie, si asserisce sotto
                    rotte[rel] = str(exc).splitlines()[0]
            transaction.set_rollback(True)
        self.assertEqual(rotte, {}, "rel del pannello che la lista non sa servire")

    # 3.
    def test_ogni_colonna_ha_l_etichetta_in_entrambi_i_locales(self) -> None:
        it, en = _etichette("it"), _etichette("en")
        meta = ConfigMetadataRepository()
        senza_it: set[str] = set()
        senza_en: set[str] = set()
        for rel in self.rels:
            schema, tabella = rel.split(".", 1)
            for col in meta.get_table_columns(schema, tabella):
                self.assertNotEqual(col["name"], "uid", f"{rel}: `uid` la scrive il DB, non l'operatore")
                if col["is_pk"]:
                    continue
                if col["name"] not in it:
                    senza_it.add(col["name"])
                if col["name"] not in en:
                    senza_en.add(col["name"])
        self.assertEqual(sorted(senza_it), [], f"colonne senza `{_PREFISSO}.*` in it.json")
        self.assertEqual(sorted(senza_en), [], f"colonne senza `{_PREFISSO}.*` in en.json")

    # 4. ⚠️ Una FK verso una tabella AMMESSA che punta a una colonna fuori da
    #    `LOOKUP_COLONNE_VALORE` e' un errore da vedere, non un degrado: il BE
    #    la renderebbe «valore a mano» in silenzio su una tabella che il lookup
    #    sa servire. Il 21-09 quattro FK del registro puntavano a
    #    `esiti_flussi_pratiche(codice_interno)`, non a `id`.
    def test_ogni_fk_nomina_una_relazione_esistente_e_il_flag_dice_il_vero(self) -> None:
        meta = ConfigMetadataRepository()
        with connection.cursor() as cur:
            for rel in self.rels:
                schema, tabella = rel.split(".", 1)
                for col in meta.get_table_columns(schema, tabella):
                    target = col["references"]
                    if target is None:
                        self.assertIsNone(col["references_column"], f"{rel}.{col['name']}")
                        self.assertFalse(col["references_lookup"], f"{rel}.{col['name']}")
                        continue
                    cur.execute("SELECT to_regclass(%s)", [target])
                    riga = cur.fetchone()
                    assert riga is not None
                    self.assertIsNotNone(riga[0], f"{rel}.{col['name']} → {target} non esiste")
                    cur.execute(
                        "SELECT 1 FROM pg_attribute WHERE attrelid = %s::regclass AND attname = %s",
                        [target, col["references_column"]],
                    )
                    self.assertIsNotNone(cur.fetchone(), f"{rel}.{col['name']} → {target}.{col['references_column']} non esiste")
                    ammessa = target in self.rel_lookup
                    if ammessa:
                        self.assertIn(
                            col["references_column"], LOOKUP_COLONNE_VALORE,
                            f"{rel}.{col['name']} → {target}({col['references_column']}): tabella ammessa al lookup "
                            "ma la colonna referenziata non e' nel suo payload — la LookupSelect non puo' montarla",
                        )
                    self.assertEqual(col["references_lookup"], ammessa, f"{rel}.{col['name']}")

    # 5.
    def test_ogni_rel_ha_l_etichetta_di_tabella_in_entrambi_i_locales(self) -> None:
        for locale in ("it", "en"):
            senza = sorted(set(self.rels) - _etichette_tabelle(locale))
            self.assertEqual(senza, [], f"rel senza `config_panel.tabelle.*` in {locale}.json (a video la rel grezza)")

    # 6. Le rel che il frontend passa al lookup generico: la lista e' un dato
    #    del DB, e un seed che ne perdesse una darebbe un 400 a video.
    # ⭐ L'elenco si LEGGE dal sorgente, non si ricopia: fino al 2026-09-25
    #    questo test ne nominava due a mano, e le altre ottanta tendine non
    #    avevano presidio.
    def test_le_rel_nominate_dal_frontend_sono_nel_lookup(self) -> None:
        nominate = _rel_del_frontend()
        self.assertGreater(len(nominate), 0, "nessuna rel trovata: la regex non legge piu' il frontend")
        fuori = {rel: dove for rel, dove in nominate.items() if rel not in self.rel_lookup}
        self.assertEqual(fuori, {}, "rel passate al lookup generico ma fuori da config.tabelle_gestibili.lookup")
