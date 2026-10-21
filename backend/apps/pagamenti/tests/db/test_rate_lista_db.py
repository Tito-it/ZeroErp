# ------------------------------------------------------------
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Presidi sul DATABASE PROVVISTO per la lista delle rate (pezzo C di
#        D19, `GET /pagamenti/rate/`): il numero e' un confronto ESATTO (101
#        non porta 1010), i saldi arrivano dal nucleo `fn_get_saldi_rate` per
#        OGNI rata della pagina, «solo aperte» toglie la rata esaurita, e ogni
#        colonna della whitelist ordina in entrambi i versi — compresa la
#        coppia `(numero, serie)`, che un mock non saprebbe rifiutare.
#        ⭐ E il verbo «righe da rate» (pezzo D), provato PER INTERO contro il
#        guard vero: due rate, la seconda con un importo oltre la banda ⇒
#        esito PARZIALE, la prima inserita, la seconda in `falliti` con
#        `ui_action = confirm_and_retry`; poi il secondo giro con `forzata`
#        che la fa entrare. E' il presidio della regola «venti righe buone non
#        si perdono per una».
# Note: ⚠️ Il mondo si COSTRUISCE, non si cerca (guida pgtap §79): su un
#       database ricostruito dai changelog le anagrafiche sono a zero e una
#       fixture che «cerca» esce vuota, con copertura zero. Qui l'azienda, il
#       cliente, DUE fatture numerate (101 e 1010, stessa serie) e le loro
#       rate nascono dai BB `dbops.fn_pgtap_crea_*`, in transazione ANNULLATA
#       e col contesto operatore.
# ------------------------------------------------------------
"""
Indice test eseguiti:
1) RateListaDbTests.test_il_numero_e_un_confronto_esatto
2) RateListaDbTests.test_i_saldi_arrivano_per_ogni_rata_della_pagina
3) RateListaDbTests.test_solo_aperte_toglie_la_rata_esaurita
4) RateListaDbTests.test_ogni_ordinamento_della_whitelist_esegue
5) RateListaDbTests.test_la_ricerca_libera_trova_il_cliente_e_il_documento
5-bis) RateListaDbTests.test_la_bozza_esce_dal_perimetro_in_entrambi_i_rami
6) RigheDaRateDbTests.test_parziale_poi_il_secondo_tempo_per_riga
7) RicercaListeDbTests.test_la_ricerca_trova_ogni_colonna_accesa
"""
from __future__ import annotations

import unittest
from decimal import Decimal

from django.db import connection, transaction

from apps.core.services.error_policies import ErrorPolicyRegistry
from apps.core.tests.db_e2e import richiedi_db_provvisto, verifica_ricerca_colonna_per_colonna
from apps.pagamenti.db.pagamenti_repository import RATE_SORT_COLUMNS, PagamentiRepository
from apps.pagamenti.services import pagamenti_service, saldi_service, sistemazioni_service

# Il mondo: azienda con operatore (PRIMA del contesto), poi il contesto, poi
# un cliente fatturabile e due fatture numerate nella stessa serie — 101 e
# 1010 — con una rata ciascuna. La seconda rata e' gia' SALDATA da un
# movimento registrato: e' la rata «esaurita» che «solo aperte» deve togliere.
_FIXTURE: tuple[str, ...] = (
    """
    CREATE TEMP TABLE _mondo AS
    SELECT m.* FROM dbops.fn_pgtap_crea_emittente_operatore() m
    """,
    """
    SELECT script.fn_pgtap_set_contesto_operatore((SELECT auth_user_id FROM _mondo))
    """,
    """
    CREATE TEMP TABLE _cli AS
    SELECT c.* FROM dbops.fn_pgtap_crea_cliente_ba('lista rate') c
    """,
    """
    CREATE TEMP TABLE _refs AS
    SELECT script.fn_pgtap_registro_fattura(m.soggetto_ruolo_id) AS registro_id,
           (SELECT billing_account_id FROM _cli)                 AS billing_account_id,
           (SELECT utility_id FROM _cli)                         AS utility_id,
           (SELECT id FROM config.tipi_doc_fiscale WHERE attivo IS TRUE ORDER BY id LIMIT 1)
                                                                  AS tipo_doc_fiscale_id,
           (SELECT id FROM config.valute ORDER BY id LIMIT 1)    AS valuta_id,
           m.soggetto_ruolo_id                                   AS emittente_soggetto_ruolo_id,
           (SELECT c.id FROM pagamenti.centri_riscossione c
             WHERE c.attivo IS TRUE AND c.codice_interno = 'BANCA' ORDER BY c.id LIMIT 1)
                                                                  AS centro_banca_id,
           (SELECT s.id FROM pagamenti.vendite_contabili_righe_stati s
             WHERE s.codice_interno = 'ABBINATA' ORDER BY s.id LIMIT 1) AS stato_abbinata_id,
           (SELECT s.id FROM pagamenti.vendite_contabili_stati s
             WHERE s.codice_interno = 'VALIDATA' ORDER BY s.id LIMIT 1) AS stato_validata_id
      FROM _mondo m
    """,
    # Due fatture nella stessa serie — 101 e 1010 — col totale che il posting
    # confronta. Il numero si SCRIVE dalla fixture (nessun guard di numerazione
    # sull'UPDATE diretto: e' la fixture, non il verbo), come nel pgTAP della
    # vista fatture.
    """
    CREATE TEMP TABLE _fat AS
    WITH ins AS (
        INSERT INTO vendite.fatture
            (registro_id, data, emittente_soggetto_ruolo_id, billing_account_id,
             tipo_doc_fiscale_id, valuta_id, utility_id, totale_a_pagare, meta)
        SELECT r.registro_id, script.fn_data_operativa(), r.emittente_soggetto_ruolo_id,
               r.billing_account_id, r.tipo_doc_fiscale_id, r.valuta_id, r.utility_id,
               400.00, jsonb_build_object('test_scope', 'be_lista_rate', 'n', v.n)
          FROM _refs r, (VALUES (1), (2)) AS v(n)
        RETURNING id, (meta ->> 'n')::int AS n
    )
    SELECT id AS fattura_id, n FROM ins
    """,
    """
    UPDATE vendite.fatture f
       SET numero = CASE x.n WHEN 1 THEN 101 ELSE 1010 END, serie = 'A', anno = 2026
      FROM _fat x WHERE f.id = x.fattura_id
    """,
    """
    CREATE TEMP TABLE _rate AS
    WITH ins AS (
        INSERT INTO vendite.fatture_scadenze (fattura_id, numero_rata, data_scadenza, importo)
        SELECT fattura_id, 1, script.fn_data_operativa() + 30, 400.00 FROM _fat
        RETURNING id, fattura_id
    )
    SELECT i.id AS scadenza_id, i.fattura_id, x.n FROM ins i JOIN _fat x USING (fattura_id)
    """,
    # La rata della 1010 si SALDA per intero registrando una distinta: riga
    # ABBINATA sulla rata, testata validata, posting — il movimento lo scrive
    # la madre, non la fixture.
    """
    CREATE TEMP TABLE _dist AS
    SELECT pagamenti.fn_get_or_create_vendite_contabile(
        p_centro_riscossione_id => (SELECT centro_banca_id FROM _refs),
        p_data_contabile        => script.fn_data_operativa(),
        p_data_registrazione    => script.fn_data_operativa(),
        p_codice_stato_interno  => 'BOZZA',
        p_meta                  => '{"test_scope": "be_lista_rate"}'::jsonb,
        p_origine               => 'MANUALE'
      ) AS contabile_id
    """,
    """
    INSERT INTO pagamenti.vendite_contabili_righe
        (contabile_id, riferimento_ente, data_pagamento, importo, fattura_id,
         billing_account_id, scadenza_id, stato_id, meta)
    SELECT d.contabile_id, 'BE_LISTA_RATE_1010', script.fn_data_operativa(), 400.00,
           r.fattura_id, x.billing_account_id, r.scadenza_id, x.stato_abbinata_id,
           '{"test_scope": "be_lista_rate"}'::jsonb
      FROM _dist d, _refs x, _rate r
     WHERE r.n = 2
    """,
    """
    UPDATE pagamenti.vendite_contabili c
       SET stato_id = (SELECT stato_validata_id FROM _refs)
     WHERE c.id = (SELECT contabile_id FROM _dist)
    """,
    """
    SELECT * FROM pagamenti.fn_posta_contabile((SELECT contabile_id FROM _dist))
    """,
)


class _MondoRateDbTests(unittest.TestCase):
    """La base SENZA test: il mondo costruito e i due helper, ereditati dalle
    due classi sotto. ⚠️ Non un `TestCase` con test da nascondere nelle
    sottoclassi: un attributo `test_x = None` passa la discovery per un
    dettaglio del loader (`callable`), e chi legge crede che quei test siano
    stati spenti."""

    @classmethod
    def setUpClass(cls) -> None:
        richiedi_db_provvisto()

    # Scopo: monta il mondo e consegna `{n: scadenza_id}` e il billing account.
    # ⭐ Il contesto operatore e' quello dell'azienda COSTRUITA
    #    (`fn_pgtap_set_contesto_operatore` nella fixture), non un utente
    #    pescato: su `zeroerp_ci` non ce n'e' nessuno da pescare.
    def _mondo(self, cur) -> tuple[dict[int, int], int]:
        for passo in _FIXTURE:
            cur.execute(passo)
        cur.execute("SELECT n, scadenza_id FROM _rate ORDER BY n")
        rate = {int(n): int(sid) for n, sid in cur.fetchall()}
        cur.execute("SELECT billing_account_id FROM _cli")
        row = cur.fetchone()
        assert row is not None
        return rate, int(row[0])

    # Scopo: esegue `azione(cur, rate, ba_id)` nel mondo costruito, in una
    #        transazione SEMPRE annullata.
    def _nel_mondo(self, azione):
        with transaction.atomic():
            try:
                with connection.cursor() as cur:
                    rate, ba_id = self._mondo(cur)
                    return azione(cur, rate, ba_id)
            finally:
                transaction.set_rollback(True)



class RateListaDbTests(_MondoRateDbTests):
    """La lista delle rate (pezzo C) sul mondo costruito."""

    # Scopo: ⛔ `fattura_numero=101` porta la 101 e NON la 1010: e' un `=`, non
    #        un `ILIKE` (brief DB §8, la trappola del lookup).
    def test_il_numero_e_un_confronto_esatto(self):
        def _prova(cur, rate, ba_id):
            esito = saldi_service.list_rate(
                auth_user_id=None, limit=50, billing_account_id=ba_id, fattura_numero=101,
            )
            return esito["count"], [r["scadenza_id"] for r in esito["results"]]
        count, ids = self._nel_mondo(_prova)
        self.assertEqual(count, 1)
        self.assertEqual(len(ids), 1)

    # Scopo: ⭐ Pagina prima, saldo dopo: le due rate del cliente escono ENTRAMBE
    #        coi tre numeri della base unica, letti dal nucleo con l'array della
    #        pagina — la saldata a residuo zero e `has_movimenti`, l'aperta a
    #        residuo pieno.
    def test_i_saldi_arrivano_per_ogni_rata_della_pagina(self):
        def _prova(cur, rate, ba_id):
            esito = saldi_service.list_rate(
                auth_user_id=None, limit=50, billing_account_id=ba_id,
            )
            return rate, {int(r["scadenza_id"]): r for r in esito["results"]}
        rate, per_id = self._nel_mondo(_prova)
        self.assertEqual(set(per_id), set(rate.values()))
        aperta, saldata = per_id[rate[1]], per_id[rate[2]]
        for campo in saldi_service.CAMPI_SALDO:
            self.assertIn(campo, aperta)
            self.assertIn(campo, saldata)
        self.assertEqual(aperta["residuo"], Decimal("400.00"))
        self.assertIs(aperta["has_movimenti"], False)
        self.assertEqual(saldata["residuo"], Decimal("0.00"))
        self.assertIs(saldata["has_movimenti"], True)
        # Il documento arriva com'e' scritto: numero parlante dalla sede unica.
        self.assertEqual(aperta["numero_documento"], "101 - A")

    # Scopo: «aperta» = `residuo <> 0` (Q-B): col filtro resta la sola rata
    #        della 101, e i saldi escono dalla stessa query del `WHERE`.
    def test_solo_aperte_toglie_la_rata_esaurita(self):
        def _prova(cur, rate, ba_id):
            esito = saldi_service.list_rate(
                auth_user_id=None, limit=50, billing_account_id=ba_id, solo_aperte=True,
            )
            return rate, esito["count"], esito["results"]
        rate, count, results = self._nel_mondo(_prova)
        self.assertEqual(count, 1)
        self.assertEqual(int(results[0]["scadenza_id"]), rate[1])
        self.assertEqual(results[0]["residuo"], Decimal("400.00"))

    # Scopo: ogni colonna della whitelist, nei DUE versi e in ENTRAMBI i rami
    #        (con e senza `solo_aperte`), produce SQL che PARTE — compresa la
    #        coppia `(numero, serie)`, che non e' una colonna.
    def test_ogni_ordinamento_della_whitelist_esegue(self):
        def _prova(cur, rate, ba_id):
            repo = PagamentiRepository()
            for colonna in RATE_SORT_COLUMNS:
                for verso in ("asc", "desc"):
                    for solo_aperte in (False, True):
                        righe, _tot = repo.list_rate_paginata(
                            auth_user_id=None, billing_account_id=ba_id,
                            solo_aperte=solo_aperte,
                            order_by=colonna, order_dir=verso, limit=5, offset=0,
                        )
                        self.assertTrue(righe, f"{colonna} {verso} solo_aperte={solo_aperte}")
            return True
        self.assertTrue(self._nel_mondo(_prova))

    # Scopo: la ricerca libera cerca il CLIENTE **e il documento** (Tid,
    #        2026-09-23, brief-be-ricerca-full-liste-residue §7) — e resta una
    #        cosa DIVERSA dal filtro esatto `fattura_numero`: «101» come
    #        `search` porta la 101 E la 1010 (e' un `ILIKE`), «101» come
    #        `fattura_numero` porta la sola 101 (test 1).
    # ⭐ Provata nei DUE rami, perche' il BB sta dentro `_condizioni(alias)`:
    #    con `solo_aperte` la ricerca cade anche sul PERIMETRO (`p`) del
    #    nucleo, e la 1010 — saldata — esce anche se il termine la trova.
    # ⚠️ Fino al 24-09 questo test fissava il contrario («mai il numero»):
    #    rovesciato col passaggio della lista al catalogo.
    def test_la_ricerca_libera_trova_il_cliente_e_il_documento(self):
        def _prova(cur, rate, ba_id):
            cur.execute(
                "SELECT ba.codice FROM anagrafiche.billing_account ba WHERE ba.id = %s", [ba_id]
            )
            row = cur.fetchone()
            assert row is not None

            # Scopo: gli id delle rate che la ricerca porta, nel cliente del mondo.
            def _ids(termine: str, **filtri) -> set[int]:
                esito = saldi_service.list_rate(
                    auth_user_id=None, limit=50, billing_account_id=ba_id,
                    search=termine, **filtri,
                )
                return {int(r["scadenza_id"]) for r in esito["results"]}

            per_ba = saldi_service.list_rate(auth_user_id=None, limit=50, search=str(row[0]))
            return (
                rate,
                per_ba["count"],
                _ids("101"),
                _ids("1010"),
                _ids("101", solo_aperte=True),
                _ids("1010", solo_aperte=True),
            )
        rate, per_ba, per_101, per_1010, aperte_101, aperte_1010 = self._nel_mondo(_prova)
        self.assertEqual(per_ba, 2)
        self.assertEqual(per_101, {rate[1], rate[2]})
        self.assertEqual(per_1010, {rate[2]})
        self.assertEqual(aperte_101, {rate[1]})
        self.assertEqual(aperte_1010, set())


    # Scopo: ⛔ La rata della BOZZA resta fuori DA SOLA (rilievo di Tid, 18/09;
    #        perimetro dal 23/09) — e resta fuori in ENTRAMBI i rami, perche' il
    #        predicato sta nella funzione dell'alias: senza `solo_aperte`
    #        restano le due numerate; con `solo_aperte` resta la sola 101 (la
    #        1010 e' saldata e la bozza non e' numerata).
    # ⭐ IL CASO CHE CONTA E' IL PRIMO, e dal 23/09 dice il contrario di prima:
    #        chiamando SENZA dire niente la bozza NON c'e'. E' la decisione di
    #        Tid — `solo_numerate` e' un perimetro di dominio, non un filtro che
    #        il client deve ricordarsi di mandare. Per vederla si chiede
    #        `solo_numerate=False`, e allora c'e': la vista la porta apposta
    #        (P-2, «una rata su una bozza compare»), quindi il perimetro e' una
    #        scelta del backend e non un'assenza di dati.
    # ⚠️ La bozza si COSTRUISCE qui e non nella fixture condivisa: gli altri
    #    test contano DUE rate per il cliente, e una terza nella fixture li
    #    farebbe raccontare un'altra storia.
    # ⚠️ DUE istruzioni, non una CTE: la policy di `fatture_scadenze` fa
    #    `EXISTS` sulla testata, e dentro la stessa istruzione la riga scritta
    #    dalla CTE non e' ancora visibile alla sotto-query della policy — la
    #    rata viene rifiutata «per riga» su una fattura che c'e' (provato).
    def test_solo_numerate_toglie_la_bozza_in_entrambi_i_rami(self):
        def _prova(cur, rate, ba_id):
            cur.execute(
                """
                INSERT INTO vendite.fatture
                    (registro_id, data, emittente_soggetto_ruolo_id, billing_account_id,
                     tipo_doc_fiscale_id, valuta_id, utility_id, totale_a_pagare, meta)
                SELECT r.registro_id, script.fn_data_operativa(), r.emittente_soggetto_ruolo_id,
                       r.billing_account_id, r.tipo_doc_fiscale_id, r.valuta_id,
                       r.utility_id, 250.00,
                       '{"test_scope": "be_lista_rate", "n": 3}'::jsonb
                  FROM _refs r
                RETURNING id
                """
            )
            row = cur.fetchone()
            assert row is not None
            cur.execute(
                """
                INSERT INTO vendite.fatture_scadenze (fattura_id, numero_rata, data_scadenza, importo)
                VALUES (%s, 1, script.fn_data_operativa() + 30, 250.00)
                RETURNING id
                """,
                [int(row[0])],
            )
            row = cur.fetchone()
            assert row is not None
            bozza = int(row[0])

            def _ids(**kw):
                esito = saldi_service.list_rate(
                    auth_user_id=None, limit=50, billing_account_id=ba_id, **kw,
                )
                return esito["count"], {int(r["scadenza_id"]) for r in esito["results"]}

            return (
                bozza,
                _ids(solo_numerate=False),
                _ids(),
                _ids(solo_aperte=True),
            )

        bozza, con_bozze, perimetro, perimetro_aperte = self._nel_mondo(_prova)
        # Chiedendo ESPLICITAMENTE anche le bozze, la bozza c'e' (ed e' senza
        # numero): il perimetro e' una scelta, non un dato che manca.
        self.assertEqual(con_bozze[0], 3)
        self.assertIn(bozza, con_bozze[1])
        # Senza dire niente vale la regola: restano le due numerate.
        self.assertEqual(perimetro[0], 2)
        self.assertNotIn(bozza, perimetro[1])
        # ...e nel ramo di `solo_aperte` resta la sola 101, senza che il
        # perimetro vada ripetuto: il predicato e' nella funzione dell'alias.
        self.assertEqual(perimetro_aperte[0], 1)
        self.assertNotIn(bozza, perimetro_aperte[1])


class RigheDaRateDbTests(_MondoRateDbTests):
    """Il verbo D contro il guard vero. Eredita il mondo (azienda, cliente, le
    due rate: la 101 aperta a 400, la 1010 saldata) e apre UNA distinta nuova
    in bozza su cui scrivere."""

    # Scopo: una distinta MANUALE in bozza per il giro, dalla madre.
    def _distinta_nuova(self, cur) -> int:
        cur.execute(
            """
            SELECT pagamenti.fn_get_or_create_vendite_contabile(
                p_centro_riscossione_id => (SELECT centro_banca_id FROM _refs),
                p_data_contabile        => script.fn_data_operativa() - 1,
                p_data_registrazione    => script.fn_data_operativa(),
                p_codice_stato_interno  => 'BOZZA',
                p_meta                  => '{"test_scope": "be_righe_da_rate"}'::jsonb,
                p_origine               => 'MANUALE'
            )
            """
        )
        row = cur.fetchone()
        assert row is not None
        return int(row[0])

    # Scopo: 🔴 PARZIALE, poi il SECONDO TEMPO per riga. La rata della 101 ha
    #        400 di spazio e quella della 1010 e' SALDATA: 300 sulla prima
    #        entrano, 50 sulla seconda no — il guard della capienza rifiuta la
    #        SOLA seconda riga, «confermabile», e la prima resta scritta. Il
    #        secondo giro rimanda quella sola, forzata col motivo, e la riga
    #        entra con la forzatura SCRITTA (e' cio' che `rate/fuori-capienza/`
    #        legge per esistere).
    # ⚠️ Due rate DIVERSE e non due righe sulla stessa: la stessa rata due volte
    #    in un giro e' un duplicato, che il verbo rifiuta PRIMA di partire
    #    (400 col campo) — provato nel test unitario.
    def test_parziale_poi_il_secondo_tempo_per_riga(self):
        def _prova(cur, rate, ba_id):
            contabile_id = self._distinta_nuova(cur)
            rata_aperta = rate[1]
            comuni = {"data_pagamento": "2026-09-17", "riferimento_ente": "BE_DA_RATE"}
            primo = pagamenti_service.crea_righe_da_rate(
                contabile_id,
                {**comuni, "righe": [
                    {"scadenza_id": rata_aperta, "importo": "300.00"},
                    {"scadenza_id": rate[2], "importo": "50.00"},
                ]},
            )
            secondo = pagamenti_service.crea_righe_da_rate(
                contabile_id,
                {**comuni, "righe": [
                    {"scadenza_id": rate[2], "importo": "50.00",
                     "forzata": True, "motivo_forzatura": "pagato due volte"},
                ]},
            )
            cur.execute(
                """
                SELECT scadenza_id, importo, forzata, motivo_forzatura
                  FROM pagamenti.vendite_contabili_righe
                 WHERE contabile_id = %s AND attivo IS TRUE
                 ORDER BY id
                """,
                [contabile_id],
            )
            return primo, secondo, cur.fetchall()

        primo, secondo, righe = self._nel_mondo(_prova)
        # Primo giro: la riga sulla rata aperta entra, quella sulla saldata no.
        self.assertEqual(primo["esito"], "PARZIALE")
        self.assertEqual((primo["richieste"], primo["riuscite"]), (2, 1))
        self.assertEqual(primo["creati"][0]["indice"], 0)
        fallita = primo["falliti"][0]
        self.assertEqual(fallita["indice"], 1)
        self.assertEqual(fallita["errore"]["code"], "E_RIGA_CONTABILE_CAPIENZA_SUPERATA")
        self.assertEqual(fallita["errore"]["ui_action"], "confirm_and_retry")
        self.assertEqual(
            ErrorPolicyRegistry.resolve(fallita["errore"]["code"]).ui_action,
            "confirm_and_retry",
        )
        # Secondo giro: la sola riga rimasta, forzata, entra.
        self.assertEqual(secondo["esito"], "COMPLETATO")
        self.assertEqual(secondo["riuscite"], 1)
        # A database: due righe attive, la seconda con la forzatura scritta.
        self.assertEqual(len(righe), 2)
        self.assertEqual((righe[0][1], righe[0][2]), (Decimal("300.00"), False))
        self.assertEqual((righe[1][1], righe[1][2], righe[1][3]),
                         (Decimal("50.00"), True, "pagato due volte"))


# Il pagamento OLTRE il dovuto, sulla 101: 900 su una rata da 400, forzato col
# motivo e registrato. La rata esce dalla banda (fuori capienza, SOVRA_INCASSATA)
# e la fattura resta in credito (eccedenza). Piu' una riga SOSPESA in una
# distinta in bozza, per la coda.
_FIXTURE_RICERCA: tuple[str, ...] = (
    """
    CREATE TEMP TABLE _dist_extra AS
    SELECT pagamenti.fn_get_or_create_vendite_contabile(
        p_centro_riscossione_id => (SELECT centro_banca_id FROM _refs),
        p_data_contabile        => script.fn_data_operativa(),
        p_data_registrazione    => script.fn_data_operativa(),
        p_codice_stato_interno  => 'BOZZA',
        p_meta                  => '{"test_scope": "be_ricerca_rate"}'::jsonb,
        p_origine               => 'MANUALE'
      ) AS contabile_id
    """,
    """
    INSERT INTO pagamenti.vendite_contabili_righe
        (contabile_id, riferimento_ente, data_pagamento, importo, fattura_id,
         billing_account_id, scadenza_id, stato_id, forzata, motivo_forzatura, meta)
    SELECT d.contabile_id, 'BE_RICERCA_OLTRE', script.fn_data_operativa(), 900.00,
           r.fattura_id, x.billing_account_id, r.scadenza_id, x.stato_abbinata_id,
           TRUE, 'pagato doppio', '{"test_scope": "be_ricerca_rate"}'::jsonb
      FROM _dist_extra d, _refs x, _rate r
     WHERE r.n = 1
    """,
    """
    UPDATE pagamenti.vendite_contabili c
       SET stato_id = (SELECT stato_validata_id FROM _refs)
     WHERE c.id = (SELECT contabile_id FROM _dist_extra)
    """,
    """
    SELECT * FROM pagamenti.fn_posta_contabile((SELECT contabile_id FROM _dist_extra))
    """,
    """
    CREATE TEMP TABLE _dist_coda AS
    SELECT pagamenti.fn_get_or_create_vendite_contabile(
        p_centro_riscossione_id => (SELECT centro_banca_id FROM _refs),
        p_data_contabile        => script.fn_data_operativa(),
        p_data_registrazione    => script.fn_data_operativa(),
        p_codice_stato_interno  => 'BOZZA',
        p_meta                  => '{"test_scope": "be_ricerca_coda"}'::jsonb,
        p_origine               => 'MANUALE'
      ) AS contabile_id
    """,
    """
    CREATE TEMP TABLE _riga_coda AS
    WITH ins AS (
        INSERT INTO pagamenti.vendite_contabili_righe
            (contabile_id, riferimento_ente, data_pagamento, importo, fattura_id,
             billing_account_id, scadenza_id, stato_id, motivo_sospeso, meta)
        SELECT d.contabile_id, 'BE_RICERCA_CODA', script.fn_data_operativa(), 10.00,
               r.fattura_id, x.billing_account_id, r.scadenza_id,
               (SELECT s.id FROM pagamenti.vendite_contabili_righe_stati s
                 WHERE s.codice_interno = 'SOSPESA' ORDER BY s.id LIMIT 1),
               'da verificare', '{"test_scope": "be_ricerca_coda"}'::jsonb
          FROM _dist_coda d, _refs x, _rate r
         WHERE r.n = 1
        RETURNING id
    )
    SELECT id AS riga_id FROM ins
    """,
)


class RicercaListeDbTests(_MondoRateDbTests):
    """La ricerca libera delle sei liste di pagamenti (brief-be-ricerca-full-
    liste-residue §5.3, e `pagamenti.rate` dal passo 7): per ogni colonna che
    il CATALOGO accende, il valore di una riga costruita la trova
    (`verifica_ricerca_colonna_per_colonna`). Le liste non hanno `vista_sql`:
    questo e' il loro esercizio sul DB vero (`test_ricerca_full_db` lo
    nomina)."""

    def test_la_ricerca_trova_ogni_colonna_accesa(self):
        def _prova(cur, rate, ba_id):
            for passo in _FIXTURE_RICERCA:
                cur.execute(passo)
            cur.execute("SELECT contabile_id FROM _dist")
            dist = int(cur.fetchone()[0])
            cur.execute("SELECT codice FROM pagamenti.vendite_contabili WHERE id = %s", [dist])
            dist_codice = cur.fetchone()[0]
            cur.execute("SELECT id FROM pagamenti.vendite_contabili_righe WHERE contabile_id = %s", [dist])
            riga_1010 = int(cur.fetchone()[0])
            cur.execute("SELECT riga_id FROM _riga_coda")
            riga_coda = int(cur.fetchone()[0])
            cur.execute(
                "SELECT c.codice FROM pagamenti.vendite_contabili c WHERE c.id = (SELECT contabile_id FROM _dist_coda)"
            )
            coda_codice = cur.fetchone()[0]
            cur.execute(
                "SELECT ba.codice, s.ragione_sociale_completa "
                "  FROM anagrafiche.billing_account ba "
                "  JOIN anagrafiche.soggetti_ruoli sr ON sr.id = ba.soggetto_ruolo_id "
                "  JOIN anagrafiche.soggetti s ON s.id = sr.soggetto_id WHERE ba.id = %s",
                [ba_id],
            )
            ba_codice, cliente = cur.fetchone()
            cur.execute("SELECT fattura_id FROM _rate WHERE n = 1")
            fattura_101 = int(cur.fetchone()[0])

            verifica_ricerca_colonna_per_colonna(
                self, cur, "pagamenti.distinte", dist, {"codice": dist_codice},
                lambda t: pagamenti_service.list_distinte(search=t, limit=200)["results"],
            )
            verifica_ricerca_colonna_per_colonna(
                self, cur, "pagamenti.distinta_righe", riga_1010,
                {"riferimento_ente": "BE_LISTA_RATE_1010", "billing_account_descrizione": cliente,
                 "fattura_numero_documento": "1010 - A", "billing_account_codice": ba_codice},
                lambda t: pagamenti_service.list_righe(dist, search=t, limit=200)["results"],
            )
            verifica_ricerca_colonna_per_colonna(
                self, cur, "pagamenti.righe", riga_coda,
                {"riferimento_ente": "BE_RICERCA_CODA", "billing_account_descrizione": cliente,
                 "fattura_numero": "101", "contabile_codice": coda_codice},
                lambda t: pagamenti_service.list_coda_righe(search=t, limit=200)["results"],
            )
            verifica_ricerca_colonna_per_colonna(
                self, cur, "pagamenti.rate_fuori_capienza", rate[1],
                {"fattura_numero": "101", "numero_documento": "101 - A"},
                lambda t: pagamenti_service.list_rate_fuori_capienza(search=t, limit=200)["results"],
                chiave="scadenza_id",
            )
            # ⭐ Le rate (dal 24-09 sul catalogo): i valori si leggono dalla
            #    VISTA che la lista mostra, sulla rata della 101 costruita qui —
            #    si cerca su cio' che si mostra. ⚠️ Un valore NULL non sarebbe
            #    una prova (un `ILIKE` su NULL non trova niente e il rosso
            #    direbbe «ricerca rotta» per una fixture vuota): si pretende.
            cur.execute(
                "SELECT numero_documento, ragione_sociale_completa, ba_codice, "
                "       id_fiscale_univoco_cf_piva "
                "  FROM vendite.vw_fatture_scadenze_lista WHERE scadenza_id = %s",
                [rate[1]],
            )
            valori_rata = dict(zip(
                ("numero_documento", "ragione_sociale_completa", "ba_codice",
                 "id_fiscale_univoco_cf_piva"),
                cur.fetchone(), strict=True,
            ))
            self.assertTrue(all(valori_rata.values()), f"rata della 101 senza un valore: {valori_rata}")
            verifica_ricerca_colonna_per_colonna(
                self, cur, "pagamenti.rate", rate[1], valori_rata,
                lambda t: saldi_service.list_rate(
                    auth_user_id=None, search=t, limit=200,
                )["results"],
                chiave="scadenza_id",
            )
            verifica_ricerca_colonna_per_colonna(
                self, cur, "pagamenti.eccedenze", fattura_101,
                {"cliente_ragione_sociale": cliente, "fattura_numero": "101"},
                lambda t: sistemazioni_service.list_eccedenze(search=t, limit=200)["results"],
                chiave="fattura_id",
            )
        self._nel_mondo(_prova)
