# ------------------------------------------------------------
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: ⭐ CIO' CHE IL REGISTRO DEL PANNELLO CONFIG DICHIARA SI PROVA PER
#        INTERO (`feedback_contratto_dichiarato_provalo_intero`): per OGNI riga
#        di `frontend/src/core/config-tables.js` la lista risponde (passa dal
#        lookup generico), il metadata risponde, ogni colonna ha la sua
#        etichetta in it.json E en.json, ogni FK nomina una relazione che esiste
#        e il flag `references_lookup` dice il vero. Nasce il 2026-09-21 dal
#        caso `magazzino.lotti`: dichiarata nel registro, senza `descrizione`,
#        rifiutata dal lookup con un 400 che il pannello ingoiava — a video
#        «lista vuota», e nessun presidio lo vedeva.
# Note: ⚠️ Le chiavi delle etichette sono COSTRUITE dal nome della colonna
#       (`config_panel.campi.<col>`): `check_i18n_keys.py` non le vede, e a
#       video il ripiego e' il nome grezzo — cioe' il difetto che questo
#       cantiere ha chiuso. Questo test e' l'unico che se ne accorge.
#       Gira sul DB provvisto (`richiedi_db_provvisto`): il registro e' del FE,
#       le colonne sono del DB, e la giuntura la vede solo chi li legge insieme.
# ------------------------------------------------------------
#
# Indice test:
#  1. ogni rel del registro FE e' in `_REL_CONSENTITE` (la lista del pannello
#     passa dal lookup generico: fuori whitelist = 400 a video)
#  2. ogni rel risponde alla lista (`fn_list_lookup_codici`, i parametri del pannello)
#  3. ogni colonna del metadata ha l'etichetta in it.json e en.json; `uid` mai
#  4. ogni `references` e' una relazione esistente; `references_column` e' la
#     colonna referenziata; `references_lookup` e' vero sse la relazione e' in
#     `_REL_CONSENTITE` — e in quel caso la colonna e' una che il lookup porta
#     (`LOOKUP_COLONNE_VALORE`), altrimenti la `LookupSelect` salverebbe `undefined`

from __future__ import annotations

import json
import re
from pathlib import Path
from unittest import TestCase

from django.db import connection, transaction

from apps.core.db.config_metadata_repository import ConfigMetadataRepository
from apps.core.db.dbops_repository import LOOKUP_COLONNE_VALORE, _REL_CONSENTITE
from apps.core.services.lookup_service import fn_list_lookup_codici
from apps.core.tests.db_e2e import apri_contesto_operatore, richiedi_db_provvisto

_ROOT = Path(__file__).resolve().parents[5]
_REGISTRO = _ROOT / "frontend" / "src" / "core" / "config-tables.js"
_LOCALES = _ROOT / "frontend" / "src" / "locales"
_PREFISSO = "config_panel.campi"


# Scopo: le rel dichiarate dal registro FE, lette dal sorgente (e' un file di
#        dati con una riga per tabella: la regex e' il suo parser).
def _rel_del_registro() -> list[str]:
    return re.findall(r"rel: '([a-z_]+\.[a-z_]+)'", _REGISTRO.read_text(encoding="utf-8"))


# Scopo: le chiavi `config_panel.campi.*` di un locale.
def _etichette(locale: str) -> set[str]:
    dati = json.loads((_LOCALES / f"{locale}.json").read_text(encoding="utf-8"))
    return set(dati["config_panel"]["campi"])


class ConfigPanelRegistroDbTests(TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        super().setUpClass()
        richiedi_db_provvisto()
        cls.rels = _rel_del_registro()
        assert cls.rels, "registro FE vuoto o non letto"

    # 1.
    def test_ogni_rel_del_registro_e_ammessa_al_lookup(self) -> None:
        fuori = sorted(set(self.rels) - _REL_CONSENTITE)
        self.assertEqual(fuori, [], "rel nel registro FE ma non in _REL_CONSENTITE: la lista del pannello e' un 400")

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
                            attivo_only=False, page=1, page_size=1,
                        )
                        self.assertIsInstance(dati["count"], int, rel)
                except Exception as exc:  # noqa: BLE001 — si raccoglie, si asserisce sotto
                    rotte[rel] = str(exc).splitlines()[0]
            transaction.set_rollback(True)
        self.assertEqual(rotte, {}, "rel del registro FE che la lista del pannello non sa servire")

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
                    ammessa = target in _REL_CONSENTITE
                    if ammessa:
                        self.assertIn(
                            col["references_column"], LOOKUP_COLONNE_VALORE,
                            f"{rel}.{col['name']} → {target}({col['references_column']}): tabella ammessa al lookup "
                            "ma la colonna referenziata non e' nel suo payload — la LookupSelect non puo' montarla",
                        )
                    self.assertEqual(col["references_lookup"], ammessa, f"{rel}.{col['name']}")
