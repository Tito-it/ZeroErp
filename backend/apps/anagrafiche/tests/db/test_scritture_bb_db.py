# ------------------------------------------------------------
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Le scritture dinamiche di anagrafiche migrate sui BB di
#        `apps.core.db.sql_write_helpers` (2026-09-26), provate sul DATABASE
#        VERO: cio' che i test di servizio, che mockano il repository, non
#        possono vedere — il binding dei parametri e cio' che resta scritto.
# Note: ⛔ `create_categoria` con `meta` NON funzionava prima della
#       migrazione: il dict arrivava nudo al cursore e psycopg 3 rispondeva
#       «cannot adapt type 'dict'» (500). Il BB lo serializza in `::jsonb`.
#       ⚠️ `update_soggetto` scrive `WHERE id = %s` senza `::uuid` (il BB non
#       casta l'id): lo prova qui il binding reale.
#       ⚠️ Il mondo si COSTRUISCE (builder `dbops.fn_pgtap_crea_*`), in
#       transazione ANNULLATA. Opt-in `ZEROERP_TEST_DB_E2E=1` (acceso in CI).
# ------------------------------------------------------------
"""
Indice test eseguiti (opt-in `ZEROERP_TEST_DB_E2E=1`):
1) ScrittureBbAnagraficheDbTests.test_update_soggetto_id_uuid_e_strip
2) ScrittureBbAnagraficheDbTests.test_update_contatto_con_ownership_soggetto
3) ScrittureBbAnagraficheDbTests.test_create_categoria_con_meta_dict
4) ScrittureBbAnagraficheDbTests.test_update_emittente_stringa_vuota_diventa_null
"""
from __future__ import annotations

import unittest

from django.db import connection, transaction

from apps.core.tests.db_e2e import Annulla, apri_contesto_operatore, richiedi_db_provvisto


class ScrittureBbAnagraficheDbTests(unittest.TestCase):

    def setUp(self):
        richiedi_db_provvisto()

    # 1. L'UPDATE per id uuid passa senza cast esplicito, e la stringa arriva
    #    strippata (convenzione del BB).
    def test_update_soggetto_id_uuid_e_strip(self):
        from apps.anagrafiche.db.soggetti_repository import SoggettiRepository

        try:
            with transaction.atomic(), connection.cursor() as cur:
                apri_contesto_operatore(cur)
                cur.execute("SELECT dbops.fn_pgtap_crea_soggetto_pg('Soggetto scrbbsog')")
                soggetto_id = str(cur.fetchone()[0])
                aggiornato = SoggettiRepository().update_soggetto(
                    soggetto_id, {"ragione_sociale": "  Soggetto scrbbsog due  "},
                )
                self.assertTrue(aggiornato)
                cur.execute(
                    "SELECT ragione_sociale FROM anagrafiche.soggetti WHERE id = %s",
                    [soggetto_id],
                )
                self.assertEqual("Soggetto scrbbsog due", cur.fetchone()[0])
                raise Annulla
        except Annulla:
            pass

    # 2. SET dal BB + WHERE di ownership scritto dal metodo: il contatto del
    #    soggetto si aggiorna, quello di un altro soggetto no.
    def test_update_contatto_con_ownership_soggetto(self):
        from apps.anagrafiche.db.soggetti_repository import SoggettiRepository

        try:
            with transaction.atomic(), connection.cursor() as cur:
                apri_contesto_operatore(cur)
                cur.execute("SELECT dbops.fn_pgtap_crea_soggetto_pg('Soggetto scrbbcon')")
                soggetto_id = str(cur.fetchone()[0])
                cur.execute("SELECT dbops.fn_pgtap_crea_soggetto_pg('Soggetto scrbbalt')")
                altro_id = str(cur.fetchone()[0])
                repo = SoggettiRepository()
                contatti = repo.get_soggetto_contatti(soggetto_id)
                self.assertTrue(contatti, "il builder crea il contatto del soggetto")
                contatto_id = contatti[0]["id"]

                self.assertFalse(repo.update_contatto(
                    contatto_id, {"nominativo": "scrbb estraneo"}, soggetto_id=altro_id,
                ))
                self.assertTrue(repo.update_contatto(
                    contatto_id, {"nominativo": "scrbb nominativo", "note": None},
                    soggetto_id=soggetto_id,
                ))
                cur.execute(
                    "SELECT nominativo, note FROM anagrafiche.contatti WHERE id = %s",
                    [contatto_id],
                )
                self.assertEqual(("scrbb nominativo", None), cur.fetchone())
                raise Annulla
        except Annulla:
            pass

    # 3. `meta` dict -> jsonb OGGETTO (non uno scalare stringa), e
    #    `codice_interno` = `codice`.
    def test_create_categoria_con_meta_dict(self):
        from apps.anagrafiche.db.categorie_clienti_repository import (
            CategorieClientiRepository,
        )

        try:
            with transaction.atomic(), connection.cursor() as cur:
                apri_contesto_operatore(cur)
                nuovo_id = CategorieClientiRepository().create_categoria({
                    "codice": "SCRBBCAT",
                    "descrizione": "Categoria scrbb",
                    "meta": {"origine": "scrbb"},
                })
                cur.execute(
                    "SELECT codice_interno, jsonb_typeof(meta), meta->>'origine' "
                    "  FROM anagrafiche.categorie_clienti WHERE id = %s",
                    [nuovo_id],
                )
                self.assertEqual(("SCRBBCAT", "object", "scrbb"), cur.fetchone())
                raise Annulla
        except Annulla:
            pass

    # 4. La normalizzazione '' -> NULL resta del repository e precede il BB.
    def test_update_emittente_stringa_vuota_diventa_null(self):
        from apps.anagrafiche.db.emittenti_fiscali_repository import (
            EmittentiFiscaliRepository,
        )

        try:
            with transaction.atomic(), connection.cursor() as cur:
                cur.execute("SELECT * FROM dbops.fn_pgtap_crea_emittente()")
                emittente = dict(zip([c.name for c in cur.description], cur.fetchone(), strict=True))
                apri_contesto_operatore(cur)
                emittente_id = emittente["emittente_fiscale_id"]
                self.assertTrue(EmittentiFiscaliRepository().update_emittente(
                    emittente_id, {"rounding_policy": "  ", "bollo_auto": True},
                ))
                cur.execute(
                    "SELECT rounding_policy, bollo_auto "
                    "  FROM anagrafiche.emittenti_fiscali WHERE id = %s",
                    [emittente_id],
                )
                self.assertEqual((None, True), cur.fetchone())
                raise Annulla
        except Annulla:
            pass
