# ------------------------------------------------------------
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: la chiusura di un legame di distinta coi suoi prezzi bundle (BE19 di
#        brief-db-revisione-catalogo, giro 3), dal service fino alla risposta
#        che riceve il client, sul database vero: il lettore della finestra
#        (`fn_get_chiusura_componente` → `vendite.fn_prezzi_legame_oltre_la_fine`)
#        e il verbo (`fn_chiudi_componente` → `catalogo.fn_chiudi_legame_distinta`).
# Note: ⭐ Il mondo si COSTRUISCE (azienda con operatore, listino, kit, legame,
#       prezzo bundle in una bozza) in una transazione annullata, come il pgTAP
#       `catalogo/test-chiudi-legame-con-prezzi-v1`: niente dipende dai dati.
#       I rami che il verbo giudica (altre aziende, prezzi che cominciano dopo,
#       permessi) li prova quel pgTAP; qui il binding, il giro della conferma e
#       la forma della risposta.
#       Opt-in `ZEROERP_TEST_DB_E2E=1` (acceso in CI).
# ------------------------------------------------------------
"""
Indice test eseguiti (opt-in `ZEROERP_TEST_DB_E2E=1`):
1) ChiusuraLegamePrezziDbTests.test_la_finestra_elenca_il_prezzo
2) ChiusuraLegamePrezziDbTests.test_senza_conferma_chiede_di_confermare
3) ChiusuraLegamePrezziDbTests.test_con_la_conferma_chiude_legame_e_prezzo
4) ChiusuraLegamePrezziDbTests.test_conferma_che_non_corrisponde_richiede
5) ChiusuraLegamePrezziDbTests.test_legame_di_un_altro_articolo
6) ChiusuraLegamePrezziDbTests.test_conferma_non_intera
7) ChiusuraLegamePrezziDbTests.test_legame_senza_prezzi_si_chiude_al_primo_colpo
"""
from __future__ import annotations

import unittest
from datetime import date, timedelta
from decimal import Decimal
from uuid import uuid4

from django.db import DatabaseError, connection, transaction

from apps.catalogo.services.catalogo_service import fn_chiudi_componente, fn_get_chiusura_componente
from apps.core.services.error_translator import ErrorTranslator
from apps.core.services.service_errors import ServiceError
from apps.core.tests.db_e2e import apri_transazione_annullata, richiedi_db_provvisto


class ChiusuraLegamePrezziDbTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        richiedi_db_provvisto("catalogo.fn_chiudi_legame_distinta(uuid,date,integer)")

    def setUp(self) -> None:
        apri_transazione_annullata(self)
        sfx = uuid4().hex[:6].upper()
        with connection.cursor() as cur:
            cur.execute("SELECT auth_user_id FROM dbops.fn_pgtap_crea_emittente_operatore()")
            utente = cur.fetchone()[0]
            cur.execute("SELECT script.fn_pgtap_set_contesto_operatore(%s)", [utente])
            # I due diritti del verbo (Q21): TUTTO sul catalogo e sui listini,
            # come li scrive il pannello dei permessi. L'operatore costruito
            # non ha il catalogo, e sulle vendite ha gia' la sua riga.
            cur.execute(
                "INSERT INTO config.user_override_aree (auth_user_id, area_id, livello, motivo)"
                " SELECT %s, af.id, 'TUTTO'::config.livello_accesso, 'test BE19: chiusura del legame'"
                "   FROM config.aree_funzionali af WHERE af.schema_db IN ('catalogo', 'vendite')"
                " ON CONFLICT (auth_user_id, area_id) DO UPDATE SET livello = EXCLUDED.livello",
                [utente],
            )
            cur.execute("SELECT script.fn_data_operativa()")
            self.oggi: date = cur.fetchone()[0]
            cur.execute(
                "SELECT min(u.id) FROM config.utilities u"
                " WHERE EXISTS (SELECT 1 FROM config.listini_tipologie_utilities ltu"
                "                WHERE ltu.utility_id = u.id AND ltu.attivo)"
            )
            utility = cur.fetchone()[0]
            if utility is None:
                raise unittest.SkipTest("nessuna utility con una tipologia di listino nel seed")
            cur.execute(
                "SELECT listino_id, tipologia_id FROM dbops.fn_pgtap_crea_listino(%s, 'py legame', %s, %s)",
                [utility, self._giorni(-200), self._giorni(-150)],
            )
            listino, tipologia = cur.fetchone()
            art = {}
            for sigla in ("K", "F", "G", "S"):
                cur.execute(
                    "SELECT dbops.fn_pgtap_crea_articolo(%s, p_listino_tipologia_id => %s::smallint,"
                    " p_is_composito => %s)::text",
                    [f"PYCLP-{sigla}-{sfx}", tipologia, sigla == "K"],
                )
                art[sigla] = cur.fetchone()[0]
            self.kit, self.altro = art["K"], art["S"]
            legami = {}
            for figlio in ("F", "G"):
                cur.execute(
                    "INSERT INTO catalogo.articoli_componenti (prodotto_id, componente_id, coeff_qta, valido_dal)"
                    " VALUES (%s, %s, 2, %s) RETURNING id::text",
                    [self.kit, art[figlio], self._giorni(-100)],
                )
                legami[figlio] = cur.fetchone()[0]
            # Il legame F ha un prezzo bundle in una bozza; G nessuno.
            self.legame, self.legame_senza_prezzi = legami["F"], legami["G"]
            cur.execute(
                "INSERT INTO vendite.listini_versioni (listino_id, codice_versione, valido_dal)"
                " VALUES (%s, %s, %s) RETURNING id",
                [listino, f"PYCLP{sfx}", self._giorni(-50)],
            )
            versione = cur.fetchone()[0]
            cur.execute(
                "SELECT dbops.fn_pgtap_listino_aggiungi_articoli(%s, ARRAY[%s::uuid], 10)",
                [versione, art["S"]],
            )
            cur.execute(
                "INSERT INTO vendite.listini_righe_componenti"
                " (listino_versione_id, articolo_componente_id, articolo_padre_id, articolo_figlio_id,"
                "  prezzo, valido_dal)"
                " SELECT %s, ac.id, ac.prodotto_id, ac.componente_id, 11, %s"
                "   FROM catalogo.articoli_componenti ac WHERE ac.id = %s",
                [versione, self._giorni(-50), self.legame],
            )

    # ⚠️ Dal giorno AZIENDALE letto dal DB in `setUp` (`self.oggi`), mai dal
    #    giorno di sistema: i guard della distinta giudicano su quello.
    def _giorni(self, n: int) -> date:
        return self.oggi + timedelta(days=n)

    def _chiudi(self, **extra) -> dict:
        return fn_chiudi_componente(self.kit, self.legame, {"valido_al": self.oggi.isoformat(), **extra})

    # 1. La finestra: il prezzo, l'importo sul kit (prezzo per coefficiente) e
    #    l'esito; `prezzi` e' il numero da dichiarare.
    def test_la_finestra_elenca_il_prezzo(self) -> None:
        dati = fn_get_chiusura_componente(self.kit, self.legame, {"valido_al": self.oggi.isoformat()})
        self.assertEqual(dati["prezzi"], 1)
        riga = dati["righe"][0]
        self.assertEqual(riga["esito"], "CHIUDE")
        self.assertTrue(riga["nel_perimetro"])
        self.assertEqual(riga["prezzo"], Decimal("11"))
        self.assertEqual(riga["importo_per_kit"], Decimal("22"))

    # 2. Il primo tentativo, senza dichiarazione: il verbo chiede di
    #    confermare, e il client riceve il rifiuto CONFERMABILE (409,
    #    `confirm_and_retry`) col campo della data.
    def test_senza_conferma_chiede_di_confermare(self) -> None:
        with self.assertRaises(DatabaseError) as ctx, transaction.atomic():
            self._chiudi()
        errore = ErrorTranslator.to_api_error(ctx.exception)
        self.assertEqual(errore.code, "E_BOM_CHIUSURA_CON_PREZZI")
        self.assertEqual(ErrorTranslator.get_http_status(errore), 409)
        self.assertEqual(errore.ui_action, "confirm_and_retry")
        self.assertEqual(errore.fields, ("valido_al",))

    # 3. La conferma col numero letto dalla finestra: legame e prezzo chiusi
    #    alla stessa data.
    def test_con_la_conferma_chiude_legame_e_prezzo(self) -> None:
        prezzi = fn_get_chiusura_componente(
            self.kit, self.legame, {"valido_al": self.oggi.isoformat()},
        )["prezzi"]
        esito = self._chiudi(prezzi_confermati=prezzi)
        self.assertEqual(esito["prezzi_chiusi"], 1)
        self.assertEqual(esito["prezzi_tolti"], 0)
        self.assertEqual(esito["componente"]["valido_al"], self.oggi)
        with connection.cursor() as cur:
            cur.execute(
                "SELECT valido_al FROM vendite.listini_righe_componenti WHERE articolo_componente_id = %s",
                [self.legame],
            )
            self.assertEqual(cur.fetchone()[0], self.oggi)

    # 4. Una dichiarazione che non e' il numero di adesso: la domanda torna.
    def test_conferma_che_non_corrisponde_richiede(self) -> None:
        with self.assertRaises(DatabaseError) as ctx, transaction.atomic():
            self._chiudi(prezzi_confermati=5)
        self.assertEqual(ErrorTranslator.to_api_error(ctx.exception).code, "E_BOM_CHIUSURA_CON_PREZZI")

    # 5. Il legame dell'URL e' di un altro articolo: 404, e il verbo non parte.
    def test_legame_di_un_altro_articolo(self) -> None:
        with self.assertRaises(ServiceError) as ctx:
            fn_chiudi_componente(self.altro, self.legame, {"valido_al": self.oggi.isoformat()})
        self.assertEqual(ctx.exception.code, "E_CATALOGO_COMPONENTE_NOT_FOUND")

    # 6. Una dichiarazione che non e' un intero: 400 col campo, non un 500 dal cast.
    def test_conferma_non_intera(self) -> None:
        with self.assertRaises(ServiceError) as ctx:
            self._chiudi(prezzi_confermati="tanti")
        self.assertEqual(ctx.exception.code, "E_CATALOGO_VALIDATION")
        self.assertEqual(ctx.exception.context.get("field"), "prezzi_confermati")

    # 7. Un legame senza prezzi: chiuso al primo tentativo, senza conferma.
    def test_legame_senza_prezzi_si_chiude_al_primo_colpo(self) -> None:
        esito = fn_chiudi_componente(
            self.kit, self.legame_senza_prezzi, {"valido_al": self.oggi.isoformat()},
        )
        self.assertEqual((esito["prezzi_chiusi"], esito["prezzi_tolti"]), (0, 0))
        self.assertEqual(esito["componente"]["valido_al"], self.oggi)
