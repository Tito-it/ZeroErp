# ------------------------------------------------------------
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Il cliente del contratto si cambia in bozza e la scheda di fornitura
#        lo segue, dal service vero al DATABASE VERO (brief-db-indirizzi-
#        documento-seguono-il-cliente §8.3, R-BE-5, R-BE-7): cio' che i test di
#        servizio, col repository mockato, non vedono.
#          · il binding di `vendite.fn_get_fornitura_da_anagrafica` e il suo
#            arrivo nei form-defaults (R-BE-5);
#          · il cambio di coppia passa il lock di testata, e la scheda la rifa'
#            il trigger: quella del form non le si scrive sopra (R-BE-6/7);
#          · senza cambio di coppia la scheda del form si scrive (il difetto
#            della PATCH che non la portava);
#          · il BB `risolvi_cliente_coppia` col repository vero: BA d'altri;
#          · utility ed emittente non si cambiano in modifica (§8.7, R-BE-9 e
#            R-BE-10): l'offerta cambia cliente con la utility della testata, e
#            le due chiavi sono un 400 sul campo su offerta e contratto.
# Note: ⚠️ Il mondo si COSTRUISCE, come il pgTAP del team DB
#       (`test-fornitura-documento-segue-cliente-v1`): emittente e operatore da
#       `dbops.fn_pgtap_crea_emittente_operatore`, due clienti da
#       `fn_pgtap_crea_cliente_ba` su una utility senza tipi d'uso, e i loro dati
#       precontrattuali scritti qui. Transazione SEMPRE annullata. Opt-in
#       `ZEROERP_TEST_DB_E2E=1` (acceso in CI).
# ------------------------------------------------------------
"""
Indice test eseguiti (opt-in `ZEROERP_TEST_DB_E2E=1`):
1) ContrattoClienteFornituraDbTests.test_la_scheda_dell_anagrafica_si_legge
2) ContrattoClienteFornituraDbTests.test_form_defaults_portano_la_scheda_del_ba
3) ContrattoClienteFornituraDbTests.test_cambio_cliente_la_scheda_la_rifa_il_db
4) ContrattoClienteFornituraDbTests.test_stesso_cliente_la_scheda_del_form_si_scrive
5) ContrattoClienteFornituraDbTests.test_ba_di_un_altra_istanza_rifiutato_sul_ba
6) ContrattoClienteFornituraDbTests.test_offerta_cambio_cliente_senza_utility_nel_payload — R-BE-9: la utility
   della coppia viene dalla testata (2026-10-19)
7) ContrattoClienteFornituraDbTests.test_utility_ed_emittente_rifiutati_sul_campo — offerta e contratto:
   400 sul campo con la frase del lock del DB, la testata non cambia (R-BE-9, R-BE-10)
"""
from __future__ import annotations

import unittest
from typing import Any

from django.db import connection

from apps.core.db._helpers import row_to_dict
from apps.core.services.error_policies import ErrorPolicyRegistry
from apps.core.services.service_errors import ServiceError
from apps.core.tests.db_e2e import apri_transazione_annullata, richiedi_db_provvisto
from apps.vendite.db._documento_eccezioni_repo import fornitura_da_anagrafica
from apps.vendite.db.offerte_repository import OfferteRepository
from apps.vendite.services.contratti_service import ContrattiService
from apps.vendite.services.offerte_service import OfferteService
from apps.vendite.services.vendite_form_defaults_service import fn_get_contratto_form_defaults


class ContrattoClienteFornituraDbTests(unittest.TestCase):

    @classmethod
    def setUpClass(cls) -> None:
        # La sonda e' la lettura della scheda: senza, il test non ha materia.
        richiedi_db_provvisto("vendite.fn_get_fornitura_da_anagrafica(bigint,integer)")

    def setUp(self) -> None:
        apri_transazione_annullata(self)
        with connection.cursor() as cur:
            cur.execute("SELECT * FROM dbops.fn_pgtap_crea_emittente_operatore()")
            mondo = row_to_dict(cur)
            assert mondo is not None
            cur.execute("SELECT script.fn_pgtap_set_contesto_operatore(%s)", [mondo["auth_user_id"]])
            # Una utility senza tipi d'uso: la scheda non chiede la classe.
            cur.execute(
                """
                SELECT u.id FROM config.utilities u
                 WHERE NOT EXISTS (SELECT 1 FROM config.tipi_utenze t WHERE t.utility_id = u.id)
                 ORDER BY u.id LIMIT 1
                """
            )
            riga = cur.fetchone()
            assert riga is not None, "nessuna utility senza tipi d'uso nel seed"
            utility_id = int(riga[0])
            self.clienti: dict[str, dict[str, Any]] = {}
            for lato in ("A", "B"):
                cur.execute(
                    "SELECT * FROM dbops.fn_pgtap_crea_cliente_ba(%s, %s)",
                    [f"cliente e fornitura {lato}", utility_id],
                )
                cliente = row_to_dict(cur)
                assert cliente is not None
                cur.execute(
                    """
                    INSERT INTO anagrafiche.istanze_dati_precontrattuali
                           (istanza_utility_id, utility_id, param_2_txt, meta)
                    VALUES (%s, %s, %s, '{}'::jsonb)
                    """,
                    [cliente["istanza_utility_id"], cliente["utility_id"], f"E2E-{lato}"],
                )
                self.clienti[lato] = cliente
        self.emittente_fiscale_id: int = mondo["emittente_fiscale_id"]

    def _contratto_di(self, lato: str) -> int:
        c = self.clienti[lato]
        return int(ContrattiService().create_contratto({
            "billing_account_id": c["billing_account_id"],
            "istanza_utility_id": c["istanza_utility_id"],
            "utility_id": c["utility_id"],
            "emittente_fiscale_id": self.emittente_fiscale_id,
            "valido_dal": "2061-01-01",
            "valido_al": "2061-12-31",
        })["id"])

    @staticmethod
    def _scheda(contratto_id: int) -> dict[str, Any]:
        with connection.cursor() as cur:
            cur.execute(
                "SELECT istanza_utility_id, param_2_txt FROM vendite.contratti_utilities"
                " WHERE contratto_id = %s",
                [contratto_id],
            )
            scheda = row_to_dict(cur)
        assert scheda is not None, "il contratto non ha la scheda di fornitura"
        return scheda

    # 1. Il binding della lettura: la scheda dell'anagrafica della coppia.
    def test_la_scheda_dell_anagrafica_si_legge(self) -> None:
        a = self.clienti["A"]
        scheda = fornitura_da_anagrafica(a["istanza_utility_id"], a["utility_id"])
        assert scheda is not None
        self.assertEqual(scheda["param_2_txt"], "E2E-A")

    # 2. R-BE-5: i form-defaults del contratto, col BA, portano la stessa scheda.
    def test_form_defaults_portano_la_scheda_del_ba(self) -> None:
        defaults = fn_get_contratto_form_defaults(billing_account_id=self.clienti["A"]["billing_account_id"])
        self.assertEqual(defaults["fornitura"]["param_2_txt"], "E2E-A")

    # 3. Il cliente cambia in bozza: BA e istanza di B sulla testata, e la scheda
    #    e' quella dell'anagrafica di B — non quella del form, che e' di A.
    def test_cambio_cliente_la_scheda_la_rifa_il_db(self) -> None:
        cid = self._contratto_di("A")
        b = self.clienti["B"]
        testata = ContrattiService().update_contratto(cid, {
            "billing_account_id": b["billing_account_id"],
            "utility": {"param_2_txt": "DAL-FORM"},
        })
        self.assertEqual(testata["billing_account_id"], b["billing_account_id"])
        self.assertEqual(testata["istanza_utility_id"], b["istanza_utility_id"])
        self.assertEqual(
            self._scheda(cid),
            {"istanza_utility_id": b["istanza_utility_id"], "param_2_txt": "E2E-B"},
        )

    # 4. Stesso cliente: la scheda del form si scrive (prima la PATCH non la
    #    portava e il drawer diceva «salvato»).
    def test_stesso_cliente_la_scheda_del_form_si_scrive(self) -> None:
        cid = self._contratto_di("A")
        ContrattiService().update_contratto(cid, {"utility": {"param_2_txt": "DAL-FORM"}})
        self.assertEqual(self._scheda(cid)["param_2_txt"], "DAL-FORM")

    # 5. Il BB col repository vero: il BA di B con l'istanza di A non e' una
    #    coppia. Errore sul BA, prima della FK composta.
    def test_ba_di_un_altra_istanza_rifiutato_sul_ba(self) -> None:
        cid = self._contratto_di("A")
        with self.assertRaises(ServiceError) as ctx:
            ContrattiService().update_contratto(cid, {
                "billing_account_id": self.clienti["B"]["billing_account_id"],
                "istanza_utility_id": self.clienti["A"]["istanza_utility_id"],
            })
        self.assertEqual(ctx.exception.code, "E_VENDITE_VALIDATION")
        self.assertEqual(ctx.exception.context.get("field"), "billing_account_id")

    # Scopo: un'offerta in bozza sul cliente del lato, col listino della sua
    #        utility (builder, dell'emittente di chi agisce).
    def _offerta_di(self, lato: str) -> int:
        c = self.clienti[lato]
        with connection.cursor() as cur:
            cur.execute(
                "SELECT listino_id FROM dbops.fn_pgtap_crea_listino(%s, 'e2e colonne ferme')",
                [c["utility_id"]],
            )
            listino_id = cur.fetchone()[0]
        repo = OfferteRepository()
        return int(repo.create_offerta({
            "emittente_fiscale_id": self.emittente_fiscale_id,
            "billing_account_id": c["billing_account_id"],
            "istanza_utility_id": c["istanza_utility_id"],
            "utility_id": c["utility_id"],
            "listino_id": listino_id,
            "validita_dal": "2061-01-01",
        }))

    # 6. R-BE-9: il cliente dell'offerta cambia dentro la utility della testata,
    #    che il payload non porta piu' (il drawer non la manda in modifica).
    def test_offerta_cambio_cliente_senza_utility_nel_payload(self) -> None:
        oid = self._offerta_di("A")
        b = self.clienti["B"]
        OfferteService().aggiorna_offerta(oid, {"billing_account_id": b["billing_account_id"]})
        coppia = OfferteRepository().get_coppia(oid)
        assert coppia is not None
        self.assertEqual(
            (coppia["billing_account_id"], coppia["istanza_utility_id"], coppia["utility_id"]),
            (b["billing_account_id"], b["istanza_utility_id"], b["utility_id"]),
        )

    # 7. R-BE-9 e R-BE-10: utility ed emittente in modifica sono un 400 sul
    #    campo, con la frase del codice del lock del DB; la testata non cambia.
    def test_utility_ed_emittente_rifiutati_sul_campo(self) -> None:
        oid = self._offerta_di("A")
        cid = self._contratto_di("A")
        casi = (
            ("offerta", lambda chiave: OfferteService().aggiorna_offerta(oid, {chiave: 1})),
            ("contratto", lambda chiave: ContrattiService().update_contratto(cid, {chiave: 1})),
        )
        for chiave, codice_db in (
            ("utility_id", "E_DOC_UTILITY_IMMUTABILE"),
            ("emittente_fiscale_id", "E_DOC_EMITTENTE_IMMUTABILE"),
        ):
            for documento, azione in casi:
                with self.subTest(documento=documento, chiave=chiave):
                    with self.assertRaises(ServiceError) as ctx:
                        azione(chiave)
                    self.assertEqual(
                        (ctx.exception.code, ctx.exception.context.get("field"), ctx.exception.message),
                        ("E_VENDITE_VALIDATION", chiave, ErrorPolicyRegistry.resolve(codice_db).user_message),
                    )
        coppia = OfferteRepository().get_coppia(oid)
        assert coppia is not None
        self.assertEqual(coppia["utility_id"], self.clienti["A"]["utility_id"])

