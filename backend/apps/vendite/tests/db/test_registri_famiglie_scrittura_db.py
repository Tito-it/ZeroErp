# ------------------------------------------------------------
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Le scritture di REGISTRI e FAMIGLIE DI DOCUMENTO migrate sui BB core
#        (`execute_dynamic_insert` / `sql_set_clause` /
#        `execute_dynamic_update`, 2026-09-26), sul DATABASE VERO.
#
# ⭐ IL PUNTO E' `letterali=`. I BB strippano ogni stringa; `prefisso`,
#    `suffisso` (registri) e `prefisso_default` (famiglie) no, perche' sono
#    pezzi del numero stampato e uno spazio ai bordi li' e' contenuto. Il
#    service NON strippa (`empty_to_none` guarda solo se la stringa e' vuota):
#    quindi uno spazio spedito dal client arriva fino alla colonna — e qui si
#    prova che ci resta, mentre `descrizione` esce strippata.
#
# ⛔ IL RIFIUTO (classe senza DB): una chiave fuori whitelist e' `RuntimeError`
#    PRIMA di toccare il database. Il 400 educato lo danno i service
#    (`_verifica_chiavi`), coperti dai test unitari.
#
# ⚠️ Il mondo si COSTRUISCE: l'emittente da `fn_pgtap_crea_emittente`. Le
#    famiglie sono SEED (contratto, non fotografia): se ne ritocca una, in
#    transazione ANNULLATA come tutto il resto.
# ------------------------------------------------------------
"""
Indice test eseguiti:
Rifiuto (senza DB):
1) RifiutoChiaviRegistriFamiglieTests.test_chiave_estranea_e_runtime_error
Opt-in `ZEROERP_TEST_DB_E2E=1`:
2) ScritturaRegistriFamiglieDbTests.test_registro_create_e_update_prefisso_letterale
   create dal service (emittente dal contesto), prefisso/suffisso con spazi
   ai bordi conservati, descrizione strippata; update con scope emittente
   (fuori scope -> 0 righe).
3) ScritturaRegistriFamiglieDbTests.test_famiglia_update_prefisso_default_letterale
"""
from __future__ import annotations

import unittest

from django.db import connection, transaction

from apps.config.sorgenti import SORGENTE_DDT_VENDITA
from apps.core.tests.db_e2e import Annulla, apri_contesto_operatore, richiedi_db_provvisto
from apps.vendite.db.famiglie_repository import FamiglieDocumentoRepository
from apps.vendite.db.registri_repository import RegistriRepository


class RifiutoChiaviRegistriFamiglieTests(unittest.TestCase):
    """⛔ Una chiave fuori whitelist e' `RuntimeError`, mai uno scarto."""

    # 1. Le colonne si verificano PRIMA di aprire il cursore: niente DB.
    #    `serie_default`/`reset_policy` in modifica e `attivo` sulla famiglia
    #    sono proprio le chiavi che fino al 2026-09-26 sparivano in silenzio.
    def test_chiave_estranea_e_runtime_error(self):
        reg, fam = RegistriRepository(), FamiglieDocumentoRepository()
        casi = (
            ("create_registro", lambda: reg.create_registro(1, {"codice": "X", "meta": {}})),
            ("update_registro", lambda: reg.update_registro(1, None, {"serie_default": "B"})),
            ("update_registro reset", lambda: reg.update_registro(1, None, {"reset_policy": "NESSUNA"})),
            ("update_famiglia", lambda: fam.update_famiglia(1, {"attivo": False})),
        )
        for nome, chiama in casi:
            with self.subTest(nome), self.assertRaises(RuntimeError) as ctx:
                chiama()
            self.assertIn("colonne non ammesse", str(ctx.exception), nome)


class ScritturaRegistriFamiglieDbTests(unittest.TestCase):
    def setUp(self):
        richiedi_db_provvisto("dbops.fn_pgtap_crea_emittente(character varying)")

    # 2. Registro: create e update, prefisso/suffisso LETTERALI.
    def test_registro_create_e_update_prefisso_letterale(self):
        from apps.vendite.services.registri_service import RegistriService

        try:
            with transaction.atomic(), connection.cursor() as cur:
                apri_contesto_operatore(cur)
                cur.execute("SELECT soggetto_ruolo_id FROM dbops.fn_pgtap_crea_emittente()")
                emittente_sr = cur.fetchone()[0]
                # ⚠️ Il builder PROVVEDE gia' un registro per famiglia
                #    (utility NULL): il nuovo si distingue per utility, come
                #    vuole `uq_registri_fatturazione_famiglia_emittente_utility`.
                #    La stessa utility che sceglie `fn_pgtap_crea_cliente_ba`.
                cur.execute("SELECT id FROM config.utilities ORDER BY id LIMIT 1")
                utility_id = cur.fetchone()[0]
                svc = RegistriService()

                registro = svc.create_registro(emittente_sr, {
                    "codice": "  SCRREG1  ",
                    "descrizione": "  Registro scrittura BB  ",
                    "famiglia_documento": SORGENTE_DDT_VENDITA,
                    "utility_id": utility_id,
                    "prefisso": "DDT ",
                    "suffisso": " /A",
                })
                cur.execute(
                    """
                    SELECT codice, descrizione, prefisso, suffisso,
                           emittente_soggetto_ruolo_id
                      FROM vendite.registri_fatturazione WHERE id = %s
                    """,
                    [registro["id"]],
                )
                codice, descrizione, prefisso, suffisso, emittente = cur.fetchone()
                self.assertEqual(emittente, emittente_sr)
                # ⚠️ Cambio di semantica dichiarato (2026-09-26): prima il
                #    repository scriveva le stringhe COSI' COME ARRIVAVANO.
                self.assertEqual(codice, "SCRREG1")
                self.assertEqual(descrizione, "Registro scrittura BB")
                # ⭐ I pezzi del numero restano come li ha scritti l'operatore.
                self.assertEqual(prefisso, "DDT ")
                self.assertEqual(suffisso, " /A")

                repo = RegistriRepository()
                # Fuori scope: nessuna riga toccata, nessun errore.
                self.assertEqual(
                    repo.update_registro(registro["id"], [-1], {"prefisso": "NO"}), 0,
                )
                self.assertEqual(
                    repo.update_registro(
                        registro["id"], [emittente_sr],
                        {"prefisso": " B-", "descrizione": " Nuova "},
                    ),
                    1,
                )
                cur.execute(
                    "SELECT prefisso, descrizione FROM vendite.registri_fatturazione WHERE id = %s",
                    [registro["id"]],
                )
                self.assertEqual(cur.fetchone(), (" B-", "Nuova"))
                # Niente da aggiornare: niente UPDATE (sarebbe SQL non valido).
                self.assertEqual(repo.update_registro(registro["id"], None, {}), 0)
                raise Annulla
        except Annulla:
            pass

    # 3. Famiglia: update di una famiglia seed, prefisso_default LETTERALE.
    def test_famiglia_update_prefisso_default_letterale(self):
        try:
            with transaction.atomic(), connection.cursor() as cur:
                apri_contesto_operatore(cur)
                cur.execute("SELECT id FROM vendite.famiglie_documento ORDER BY id LIMIT 1")
                famiglia_id = cur.fetchone()[0]
                repo = FamiglieDocumentoRepository()
                self.assertEqual(repo.update_famiglia(famiglia_id, {
                    "prefisso_default": "FT ",
                    "descrizione": "  Famiglia scrittura BB  ",
                }), 1)
                cur.execute(
                    "SELECT prefisso_default, descrizione FROM vendite.famiglie_documento WHERE id = %s",
                    [famiglia_id],
                )
                self.assertEqual(cur.fetchone(), ("FT ", "Famiglia scrittura BB"))
                self.assertEqual(repo.update_famiglia(famiglia_id, {}), 0)
                self.assertEqual(repo.update_famiglia(-1, {"descrizione": "X"}), 0)
                raise Annulla
        except Annulla:
            pass
