# ------------------------------------------------------------
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Presidi sul DATABASE PROVVISTO per il seguito del terzo collaudo
#        in-app (D20, brief-db-validata-e-registrazione-tardiva §5): la terna
#        del verbo «valida» e le righe per stato nel dettaglio, i fatti della
#        testata nella coda, le scartate fuori di default e contate, e la
#        registrazione TARDIVA provata PER INTERO — service → madre → guard →
#        ricevuta — contro il database vero.
# Note: ⚠️ I mock non vedono l'SQL: un nome di colonna sbagliato nella
#       LATERAL della check o un parametro rinominato sulla madre e' un 500
#       sul primo «Abbina e registra», non un test rosso. Qui si parla col
#       database vero, in transazione ANNULLATA e col contesto dell'operatore
#       dell'azienda COSTRUITA dalla fixture (regola zero: il mondo si
#       costruisce, non si cerca — la stessa forma del pgTAP della madre).
# ------------------------------------------------------------

"""
Indice test eseguiti:
1)  DettaglioTests.test_con_righe_da_lavorare_la_terna_dice_perche_e_il_guard_rifiuta_uguale
2)  DettaglioTests.test_senza_righe_da_lavorare_si_puo_validare
3)  DettaglioTests.test_le_scartate_stanno_in_quadratura_e_nelle_righe_per_stato
4)  DettaglioTests.test_il_catalogo_marca_registrabile_lo_stato_in_cui_si_entra_validando
5)  CodaTests.test_la_coda_porta_i_fatti_della_testata
6)  ScartateTests.test_le_scartate_sono_fuori_di_default_e_contate
7)  TardivaTests.test_la_madre_si_pianifica
8)  TardivaTests.test_la_tardiva_per_intero_sotto_una_distinta_registrata
9)  TardivaTests.test_sotto_una_validata_e_un_rifiuto_409_non_un_esito
10) AnnullataTests.test_le_righe_di_un_annullata_escono_dalla_coda
11) AnnullataTests.test_nel_drawer_restano_e_si_leggono_soltanto
12) AnnullataTests.test_una_distinta_non_manuale_non_si_annulla
"""

from __future__ import annotations

import unittest
from decimal import Decimal

from django.db import connection, transaction

from apps.core.services.error_manager import ServiceError
from apps.core.services.error_policies import ErrorPolicyRegistry
from apps.core.tests.db_e2e import apri_contesto_operatore, richiedi_db_provvisto
from apps.pagamenti.db import pagamenti_repository as repo_mod
from apps.pagamenti.db.pagamenti_repository import PagamentiRepository
from apps.pagamenti.services import pagamenti_service

_COLONNE_TESTATA_CODA = (
    "contabile_stato_codice_interno",
    "contabile_is_final",
    "contabile_righe_lavorabili",
    "contabile_registrata",
)

# Il MONDO: un'azienda col suo operatore, e il contesto aperto su di lui —
# PRIMA che nasca il cliente, perche' il guard del billing account lo pretende.
_FIXTURE_MONDO: tuple[str, ...] = (
    """
    CREATE TEMP TABLE _mondo AS
    SELECT m.* FROM dbops.fn_pgtap_crea_emittente_operatore() m
    """,
    """
    SELECT script.fn_pgtap_set_contesto_operatore((SELECT auth_user_id FROM _mondo))
    """,
    """
    CREATE TEMP TABLE _cli_vt AS
    SELECT c.* FROM dbops.fn_pgtap_crea_cliente_ba('validata e tardiva') c
    """,
    # Una fattura F con DUE rate: R1 da 100 (la riga abbinata la riempie), R2
    # da 200 (lo spazio per la tardiva).
    """
    CREATE TEMP TABLE _fat_vt AS
    WITH ins AS (
        INSERT INTO vendite.fatture
            (registro_id, emittente_soggetto_ruolo_id, billing_account_id, meta)
        SELECT script.fn_pgtap_registro_fattura(m.soggetto_ruolo_id), m.soggetto_ruolo_id,
               c.billing_account_id, '{"test_scope": "be_validata_tardiva"}'::jsonb
          FROM _mondo m, _cli_vt c
        RETURNING id
    )
    SELECT id AS fattura_id FROM ins
    """,
    """
    CREATE TEMP TABLE _rate_vt AS
    WITH ins AS (
        INSERT INTO vendite.fatture_scadenze (fattura_id, numero_rata, data_scadenza, importo, meta)
        SELECT f.fattura_id, v.n, script.fn_data_operativa() + v.n, v.importo,
               jsonb_build_object('rata', v.et)
          FROM _fat_vt f, (VALUES (1, 100.00, 'R1'), (2, 200.00, 'R2')) AS v(n, importo, et)
        RETURNING id, meta ->> 'rata' AS etichetta
    )
    SELECT * FROM ins
    """,
    """
    CREATE TEMP TABLE _dist_vt AS
    SELECT pagamenti.fn_get_or_create_vendite_contabile(
        p_centro_riscossione_id => (SELECT c.id FROM pagamenti.centri_riscossione c
                                     WHERE c.attivo IS TRUE AND c.codice_interno = 'BANCA'
                                     ORDER BY c.id LIMIT 1),
        p_data_contabile        => script.fn_data_operativa(),
        p_data_registrazione    => script.fn_data_operativa(),
        p_codice_stato_interno  => 'BOZZA',
        p_meta                  => '{"test_scope": "be_validata_tardiva"}'::jsonb,
        p_origine               => 'MANUALE'
    ) AS contabile_id
    """,
)

# Le righe: A ABBINATA 100 su R1, S1 SOSPESA 60, K SCARTATA 5 — e, a
# richiesta, D DA_ABBINARE 30 (la riga che nessuno ha guardato).
_RIGA_SQL = """
    INSERT INTO pagamenti.vendite_contabili_righe
        (contabile_id, riferimento_ente, data_pagamento, importo,
         fattura_id, billing_account_id, scadenza_id, stato_id, motivo_sospeso, meta)
    SELECT d.contabile_id, 'BE_VT_' || %(et)s, script.fn_data_operativa(), %(importo)s,
           CASE WHEN %(et)s = 'A' THEN (SELECT fattura_id FROM _fat_vt) END,
           CASE WHEN %(et)s = 'A' THEN (SELECT billing_account_id FROM _cli_vt) END,
           CASE WHEN %(et)s = 'A' THEN (SELECT id FROM _rate_vt WHERE etichetta = 'R1') END,
           (SELECT s.id FROM pagamenti.vendite_contabili_righe_stati s
             WHERE s.codice_interno = %(stato)s ORDER BY s.id LIMIT 1),
           CASE WHEN %(stato)s = 'SOSPESA' THEN 'da capire di chi e''' END,
           jsonb_build_object('et', %(et)s)
      FROM _dist_vt d
    RETURNING id
"""
_RIGHE_BASE = (
    ("A", Decimal("100.00"), "ABBINATA"),
    ("S1", Decimal("60.00"), "SOSPESA"),
    ("K", Decimal("5.00"), "SCARTATA"),
)
_RIGA_DA_LAVORARE = ("D", Decimal("30.00"), "DA_ABBINARE")


# Scopo: monta il mondo e le righe; consegna `{contabile_id, fattura_id,
#        r1, r2, righe: {et: id}}`.
def _monta(cur, *, con_riga_da_lavorare: bool) -> dict:
    for passo in _FIXTURE_MONDO:
        cur.execute(passo)
    righe: dict[str, int] = {}
    elenco = _RIGHE_BASE + ((_RIGA_DA_LAVORARE,) if con_riga_da_lavorare else ())
    for et, importo, stato in elenco:
        cur.execute(_RIGA_SQL, {"et": et, "importo": importo, "stato": stato})
        row = cur.fetchone()
        assert row is not None
        righe[et] = int(row[0])
    cur.execute("SELECT contabile_id FROM _dist_vt")
    contabile_id = int(cur.fetchone()[0])  # type: ignore[index]
    cur.execute("SELECT fattura_id FROM _fat_vt")
    fattura_id = int(cur.fetchone()[0])  # type: ignore[index]
    cur.execute("SELECT etichetta, id FROM _rate_vt")
    rate = {et: int(rid) for et, rid in cur.fetchall()}
    return {
        "contabile_id": contabile_id, "fattura_id": fattura_id,
        "r1": rate["R1"], "r2": rate["R2"], "righe": righe,
    }


class _DbTestCase(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        richiedi_db_provvisto()

    # Scopo: esegue `azione(cursor)` col contesto operatore, in una transazione
    #        che viene SEMPRE annullata.
    def _con_operatore(self, azione):
        with transaction.atomic():
            try:
                with connection.cursor() as cur:
                    apri_contesto_operatore(cur)
                    return azione(cur)
            finally:
                transaction.set_rollback(True)

    # Scopo: i nomi delle colonne che una SELECT proietta, a zero righe.
    def _colonne(self, sql: str, params: list) -> set[str]:
        def _leggi(cur):
            cur.execute(sql, params)
            return {c[0] for c in cur.description}
        return self._con_operatore(_leggi)


class DettaglioTests(_DbTestCase):
    # Scopo: 🔴 IL CUORE DI §12.5: con una riga che nessuno ha guardato il
    #        dettaglio dice `can_validare = false` col motivo, e il guard di
    #        validazione rifiuta con il CODICE di quello stesso motivo. Tooltip
    #        e 409 non «coincidono»: vengono dalla stessa check.
    def test_con_righe_da_lavorare_la_terna_dice_perche_e_il_guard_rifiuta_uguale(self):
        def _prova(cur):
            m = _monta(cur, con_riga_da_lavorare=True)
            d = pagamenti_service.get_distinta(m["contabile_id"])["distinta"]
            with self.assertRaises(ServiceError) as ctx, transaction.atomic():
                pagamenti_service.cambia_stato_distinta(
                    m["contabile_id"], {"nuovo_stato": "VALIDATA"}
                )
            return d, ctx.exception.code
        d, codice = self._con_operatore(_prova)
        self.assertIs(d["can_validare"], False)
        self.assertEqual(d["validazione_blocco_reason"], "RIGHE_NON_LAVORATE")
        self.assertEqual(
            d["validazione_blocco_reason_key"],
            "pagamenti.distinte.validazione_reason.righe_non_lavorate",
        )
        # Il dettaglio e' DECODIFICATO (non una stringa jsonb) e porta i nomi
        # dei parametri della frase i18n.
        self.assertIsInstance(d["validazione_blocco_dettaglio"], dict)
        self.assertEqual(d["validazione_blocco_dettaglio"]["quante"], 1)
        self.assertEqual(codice, "E_CONTABILE_VALIDAZIONE_RIGHE_NON_LAVORATE")
        self.assertEqual(ErrorPolicyRegistry.resolve(codice).http_status, 409)
        # In BOZZA non si registra: lo dice il catalogo, non il nome.
        self.assertIs(d["stato_is_registrabile"], False)

    # Scopo: con sole ABBINATA/SOSPESA/SCARTATA la distinta si puo' validare —
    #        la terna e' vuota e il flag e' vero (D20-a: sospese e scartate
    #        sono state guardate).
    def test_senza_righe_da_lavorare_si_puo_validare(self):
        def _prova(cur):
            m = _monta(cur, con_riga_da_lavorare=False)
            d = pagamenti_service.get_distinta(m["contabile_id"])["distinta"]
            esito = pagamenti_service.cambia_stato_distinta(
                m["contabile_id"], {"nuovo_stato": "VALIDATA"}
            )["distinta"]
            return d, esito
        prima, dopo = self._con_operatore(_prova)
        self.assertIs(prima["can_validare"], True)
        self.assertIsNone(prima["validazione_blocco_reason"])
        self.assertIsNone(prima["validazione_blocco_reason_key"])
        self.assertIsNone(prima["validazione_blocco_dettaglio"])
        self.assertEqual(dopo["stato_codice"], "VALIDATA")
        # Da VALIDATA si registra: la bandiera del catalogo lo dice.
        self.assertIs(dopo["stato_is_registrabile"], True)

    # Scopo: ⭐ D20-c — le righe per stato sono l'array ORDINATO dal catalogo,
    #        decodificato, e la quadratura porta «di cui non nostre».
    def test_le_scartate_stanno_in_quadratura_e_nelle_righe_per_stato(self):
        def _prova(cur):
            m = _monta(cur, con_riga_da_lavorare=True)
            return pagamenti_service.get_distinta(m["contabile_id"])["distinta"]
        d = self._con_operatore(_prova)
        per_stato = {r["stato_codice_interno"]: r for r in d["righe_per_stato"]}
        self.assertEqual(
            set(per_stato), {"ABBINATA", "SOSPESA", "SCARTATA", "DA_ABBINARE"}
        )
        self.assertEqual(per_stato["SCARTATA"]["righe"], 1)
        self.assertEqual(Decimal(str(per_stato["SCARTATA"]["importo"])), Decimal("5.00"))
        self.assertEqual(d["righe_scartate"], 1)
        self.assertEqual(d["totale_scartate"], Decimal("5.00"))
        # Il totale delle righe le conta TUTTE, scartata compresa (D12-e).
        self.assertEqual(Decimal(str(d["totale_righe"])), Decimal("195.00"))

    # Scopo: il CONTRATTO del catalogo (D20-d, seed): `is_registrabile` marca
    #        il solo stato in cui si entra validando. E' il flag con cui il
    #        frontend riconosce «Porta a VALIDATA» senza un letterale.
    def test_il_catalogo_marca_registrabile_lo_stato_in_cui_si_entra_validando(self):
        stati = self._con_operatore(lambda _c: PagamentiRepository().list_stati_distinta())
        registrabili = {s["codice_interno"] for s in stati if s["is_registrabile"]}
        self.assertEqual(registrabili, {"VALIDATA"})


class CodaTests(_DbTestCase):
    # Scopo: BE-4 — la riga della coda porta stato, finalita' e «registrata»
    #        della sua distinta: e' da qui che il frontend sceglie fra «Abbina»
    #        e «Abbina e registra».
    def test_la_coda_porta_i_fatti_della_testata(self):
        colonne = self._colonne(f"{repo_mod._RIGA_CODA_SELECT} WHERE r.id = %s", [-1])
        for nome in _COLONNE_TESTATA_CODA:
            self.assertIn(nome, colonne)


class ScartateTests(_DbTestCase):
    # Scopo: BE-2 — di default la scartata NON e' nella lista e la risposta
    #        dice che ne nasconde una; con l'interruttore acceso c'e', e il
    #        conteggio e' zero. Il perimetro del conteggio e' quello della
    #        lista: contro il database, non contro un mock.
    def test_le_scartate_sono_fuori_di_default_e_contate(self):
        def _prova(cur):
            m = _monta(cur, con_riga_da_lavorare=False)
            nascoste = pagamenti_service.list_righe(m["contabile_id"], limit=50)
            mostrate = pagamenti_service.list_righe(m["contabile_id"], limit=50, scartate=True)
            return m["righe"]["K"], nascoste, mostrate
        k_id, nascoste, mostrate = self._con_operatore(_prova)
        self.assertNotIn(k_id, {r["id"] for r in nascoste["results"]})
        self.assertEqual(nascoste["count"], 2)
        self.assertEqual(nascoste["scartate_count"], 1)
        self.assertIn(k_id, {r["id"] for r in mostrate["results"]})
        self.assertEqual(mostrate["count"], 3)
        self.assertEqual(mostrate["scartate_count"], 0)


class TardivaTests(_DbTestCase):
    # Scopo: la chiamata alla madre si PIANIFICA — parametri nominati e arita'
    #        come li dichiara la funzione. Un nome rinominato qui e' un 500 sul
    #        primo «Abbina e registra», e i mock non lo vedono.
    def test_la_madre_si_pianifica(self):
        def _prova(cur):
            cur.execute(f"EXPLAIN {repo_mod._POSTA_RIGA_TARDIVA}", [-1, -1, -1, None, False, None])
            return cur.fetchall()
        piano = self._con_operatore(_prova)
        self.assertTrue(piano)

    # Scopo: ⭐ D20-b PER INTERO dal backend: validata, registrata, poi la
    #        sospesa si «abbina e registra» dal service — movimento nato, riga
    #        POSTATA, distinta ancora CHIUSA con la conferma INVARIATA, somma
    #        delle righe invariata, e nel dettaglio di una CHIUSA la terna del
    #        verbo «valida» e' azzerata (VALIDATA non e' fra le uscite).
    def test_la_tardiva_per_intero_sotto_una_distinta_registrata(self):
        def _prova(cur):
            m = _monta(cur, con_riga_da_lavorare=False)
            cid = m["contabile_id"]
            pagamenti_service.cambia_stato_distinta(cid, {"nuovo_stato": "VALIDATA"})
            ricevuta = pagamenti_service.registra_distinta(cid, {})
            prima = pagamenti_service.get_distinta(cid)["distinta"]
            esito = pagamenti_service.registra_riga_tardiva(
                m["righe"]["S1"], {"fattura_id": m["fattura_id"], "scadenza_id": m["r2"]}
            )
            dopo = pagamenti_service.get_distinta(cid)["distinta"]
            cur.execute(
                "SELECT meta ->> 'origine', scadenza_id FROM pagamenti.vendite_movimenti WHERE id = %s",
                [esito["movimento_id"]],
            )
            movimento = cur.fetchone()
            return ricevuta, prima, esito, dopo, movimento
        ricevuta, prima, esito, dopo, movimento = self._con_operatore(_prova)
        # La registrazione ha postato la sola ABBINATA e lasciato indietro le
        # altre due (la sospesa e la scartata).
        self.assertEqual(ricevuta["esito"], "POSTATA")
        self.assertEqual((ricevuta["righe_postate"], ricevuta["righe_saltate"]), (1, 2))
        self.assertEqual(prima["stato_codice"], "CHIUSA")
        self.assertIsNotNone(prima["data_conferma"])
        # La tardiva: movimento nato con la sua origine e la rata, riga POSTATA.
        self.assertEqual(esito["esito"], "POSTATA")
        self.assertEqual(Decimal(str(esito["importo"])), Decimal("60.00"))
        self.assertEqual(esito["riga"]["stato_codice"], "POSTATA")
        self.assertIsNotNone(movimento)
        self.assertEqual(movimento[0], "POSTING_TARDIVO")
        # La distinta NON e' cambiata: stato, conferma, somma delle righe.
        self.assertEqual(dopo["stato_codice"], "CHIUSA")
        self.assertEqual(dopo["data_conferma"], prima["data_conferma"])
        self.assertEqual(dopo["totale_righe"], prima["totale_righe"])
        # Su una CHIUSA il verbo «valida» non si propone: la terna e' azzerata.
        self.assertIsNone(dopo["can_validare"])
        self.assertIsNone(dopo["validazione_blocco_reason_key"])

    # Scopo: ⛔ Sotto una VALIDATA (non registrata) la tardiva e' un RIFIUTO
    #        della madre — 409 col suo codice — non un esito «nulla da
    #        postare»: c'e' il giro normale, e la frase lo dice. Il rifiuto
    #        arriva intatto dal traduttore del service.
    def test_sotto_una_validata_e_un_rifiuto_409_non_un_esito(self):
        def _prova(cur):
            m = _monta(cur, con_riga_da_lavorare=False)
            pagamenti_service.cambia_stato_distinta(m["contabile_id"], {"nuovo_stato": "VALIDATA"})
            with self.assertRaises(ServiceError) as ctx, transaction.atomic():
                pagamenti_service.registra_riga_tardiva(
                    m["righe"]["S1"], {"fattura_id": m["fattura_id"], "scadenza_id": m["r2"]}
                )
            cur.execute(
                "SELECT rs.codice_interno FROM pagamenti.vendite_contabili_righe r "
                "JOIN pagamenti.vendite_contabili_righe_stati rs ON rs.id = r.stato_id "
                "WHERE r.id = %s",
                [m["righe"]["S1"]],
            )
            return ctx.exception.code, cur.fetchone()[0]  # type: ignore[index]
        codice, stato = self._con_operatore(_prova)
        self.assertEqual(codice, "E_RIGA_CONTABILE_TARDIVA_DISTINTA_NON_REGISTRATA")
        self.assertEqual(ErrorPolicyRegistry.resolve(codice).http_status, 409)
        # E non ha scritto niente: la riga e' ancora sospesa.
        self.assertEqual(stato, "SOSPESA")


class AnnullataTests(_DbTestCase):
    """
    ANNULLATA vuol dire «non e' mai successa», e le sue righe si leggono
    soltanto (brief-db-righe-distinta-annullata-fuori-dalle-code, D-1…D-5).
    ⭐ I soggetti si COSTRUISCONO: la distinta della fixture e' MANUALE (R-4:
    il default della colonna e' GENERATA, che da D-4 non si annulla) e la
    riga DA_ABBINARE nasce qui. ⚠️ Ogni asserzione «esce» ha il suo
    controcampo «prima c'era»: un filtro che toglie tutto passerebbe da solo.
    """

    _CODA_DI_LAVORO = ("DA_ABBINARE", "SOSPESA")

    # Scopo: gli id dell'INTERA coda, pagina per pagina.
    # ⚠️ Non una pagina sola: su un database con piu' righe in coda di quante
    #    ne stiano in una pagina, le righe della fixture potrebbero cadere
    #    fuori — e «non c'e'» passerebbe per la popolazione, non per il filtro.
    def _coda(self) -> set[int]:
        repo, ids, offset, pagina = PagamentiRepository(), set(), 0, 500
        while True:
            righe, totale = repo.list_righe_coda(
                stati=self._CODA_DI_LAVORO,
                order_by="data_pagamento", order_dir="desc",
                limit=pagina, offset=offset,
            )
            ids.update(r["id"] for r in righe)
            offset += pagina
            if not righe or offset >= totale:
                return ids

    # Scopo: 🔴 IL DIFETTO DEL COLLAUDO — una DA_ABBINARE e una SOSPESA sotto
    #        una distinta annullata escono dalla coda, e il dettaglio lo dice
    #        con la bandiera del catalogo (non con «finale e non registrata»).
    def test_le_righe_di_un_annullata_escono_dalla_coda(self):
        def _prova(cur):
            m = _monta(cur, con_riga_da_lavorare=True)
            cid = m["contabile_id"]
            prima_coda = self._coda()
            prima = pagamenti_service.get_distinta(cid)["distinta"]
            pagamenti_service.cambia_stato_distinta(cid, {"nuovo_stato": "ANNULLATA"})
            return m["righe"], prima_coda, prima, self._coda(), (
                pagamenti_service.get_distinta(cid)["distinta"]
            )
        righe, prima_coda, prima, dopo_coda, dopo = self._con_operatore(_prova)
        mie = {righe["D"], righe["S1"]}
        self.assertEqual(mie & prima_coda, mie)
        self.assertEqual(mie & dopo_coda, set())
        self.assertIs(prima["stato_righe_lavorabili"], True)
        self.assertEqual(dopo["stato_codice"], "ANNULLATA")
        self.assertIs(dopo["stato_righe_lavorabili"], False)

    # Scopo: nel DRAWER le righe restano (e' il documento, non una coda), ma
    #        sono congelate (D-3): il cestino e' spento col motivo nuovo della
    #        check, e un cambio di stato e' un 409 col codice proprio (D-2).
    def test_nel_drawer_restano_e_si_leggono_soltanto(self):
        def _prova(cur):
            m = _monta(cur, con_riga_da_lavorare=True)
            cid = m["contabile_id"]
            pagamenti_service.cambia_stato_distinta(cid, {"nuovo_stato": "ANNULLATA"})
            righe = pagamenti_service.list_righe(cid, limit=50)["results"]
            with self.assertRaises(ServiceError) as ctx, transaction.atomic():
                pagamenti_service.cambia_stato_riga(
                    m["righe"]["D"], {"nuovo_stato": "SOSPESA"}
                )
            return m["righe"], righe, ctx.exception.code
        mie, righe, codice = self._con_operatore(_prova)
        per_id = {r["id"]: r for r in righe}
        self.assertIn(mie["D"], per_id)
        d = per_id[mie["D"]]
        self.assertIs(d["can_eliminare"], False)
        self.assertEqual(d["elimina_blocco_reason"], "DISTINTA_ANNULLATA")
        self.assertEqual(
            d["elimina_blocco_reason_key"],
            "pagamenti.righe.elimina_reason.distinta_annullata",
        )
        self.assertEqual(codice, "E_RIGA_CONTABILE_DISTINTA_ANNULLATA")
        self.assertEqual(ErrorPolicyRegistry.resolve(codice).http_status, 409)

    # Scopo: D-4 — l'annullo e' un gesto della MANUALE: su una GENERATA il
    #        guard rifiuta col codice proprio (D-5), e il service lo porta
    #        come 409, non come 500.
    def test_una_distinta_non_manuale_non_si_annulla(self):
        def _prova(cur):
            m = _monta(cur, con_riga_da_lavorare=False)
            cid = m["contabile_id"]
            pagamenti_service.cambia_stato_distinta(cid, {"nuovo_stato": "VALIDATA"})
            cur.execute(
                "UPDATE pagamenti.vendite_contabili SET origine = 'GENERATA' WHERE id = %s",
                [cid],
            )
            with self.assertRaises(ServiceError) as ctx, transaction.atomic():
                pagamenti_service.cambia_stato_distinta(cid, {"nuovo_stato": "ANNULLATA"})
            return ctx.exception.code
        codice = self._con_operatore(_prova)
        self.assertEqual(codice, "E_CONTABILE_ANNULLO_NON_MANUALE")
        self.assertEqual(ErrorPolicyRegistry.resolve(codice).http_status, 409)
