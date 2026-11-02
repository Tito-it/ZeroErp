# ------------------------------------------------------------
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Il pannello «Gestione tabelle» scrive col verbo
#        `config.fn_pannello_scrivi` (brief-db-pannello-config-verbo-generico
#        §6): il percorso nuovo, dal service vero al DB vero.
#
# ⭐ PERCHE' SUL DB VERO. Fino al 2026-09-25 nessun test scriveva davvero dal
#    pannello, e il binding col verbo (firma, cast del payload in jsonb, codici
#    dei rifiuti che attraversano `translate_db_errors`) i mock non lo vedono.
#    E la porta chiusa su `magazzino.causali` si prova solo come app.
#
# ⚠️ CASI COSTRUITI in una transazione SEMPRE annullata: la causale il test se
#    la fabbrica. Il contesto e' quello di un superuser (`apri_contesto_operatore`);
#    dove il DB non concede il livello a quel contesto il test lo dichiara.
# ------------------------------------------------------------

"""Indice test (opt-in `ZEROERP_TEST_DB_E2E=1`).

1. test_l_app_non_scrive_le_causali_da_sola
     la porta: l'app ha solo SELECT su `magazzino.causali` (P-4).
2. test_crea_e_modifica_una_causale_col_verbo
     il verbo scrive dove l'app non puo', ritorna `id` e i campi del form, e
     la riga si rilegge.
3. test_un_campo_che_non_si_scrive_e_rifiutato_col_suo_nome
     D-P3: `E_PANNELLO_CAMPO_NON_AMMESSO`, non piu' scartato in silenzio.
4. test_la_riga_che_non_c_e
     `E_PANNELLO_RIGA_NON_TROVATA`, in modifica come in lettura.
5. test_una_tabella_del_solo_lookup_non_si_scrive
     D-P2: le tabelle con RLS restano nelle tendine, non nel pannello.
6. test_lettura_sulle_causali_legge_e_non_scrive
     i DUE punti di applicazione (catena del backend, D-P7, e verbo) sullo
     stesso operatore costruito: LETTURA sull'AREA `magazzino` della riga.
7. test_tutto_sulle_causali_scrive
     lo stesso operatore con TUTTO sull'area: la catena e il verbo passano.
"""

from __future__ import annotations

import uuid
from unittest import TestCase

from django.db import connection, transaction

from apps.core.api.permissions import MotivoDiniego, ZeroERPPermission
from apps.core.api.views_config_crud import ConfigTableRecordsView
from apps.core.services.config_crud_service import ConfigCrudService
from apps.core.services.service_errors import ServiceError
from apps.core.tests.db_e2e import apri_contesto_operatore, apri_transazione_annullata, richiedi_db_provvisto

_REL = "magazzino.causali"


class PannelloVerboDbTests(TestCase):

    @classmethod
    def setUpClass(cls) -> None:
        super().setUpClass()
        richiedi_db_provvisto()

    def setUp(self) -> None:
        apri_transazione_annullata(self)
        with connection.cursor() as cur:
            apri_contesto_operatore(cur)
        self.svc = ConfigCrudService()

    # Scopo: Esegue `azione` in un savepoint e ne ritorna il codice del ServiceError.
    def _codice(self, azione) -> str | None:
        try:
            with transaction.atomic():
                azione()
        except ServiceError as exc:
            return exc.code
        return None

    def _nuova(self) -> dict:
        codice = f"T{uuid.uuid4().hex[:8].upper()}"
        return self.svc.create_record(
            _REL, {"codice": codice, "descrizione": "Causale del test", "segno": 1},
        )

    # 1.
    def test_l_app_non_scrive_le_causali_da_sola(self) -> None:
        with connection.cursor() as cur:
            cur.execute(
                "SELECT pg_has_role(current_user, c.relowner, 'USAGE'),"
                "       has_table_privilege(current_user, c.oid, 'INSERT'),"
                "       has_table_privilege(current_user, c.oid, 'UPDATE')"
                "  FROM pg_class c WHERE c.oid = %s::regclass",
                [_REL],
            )
            e_owner, insert, update = cur.fetchone()
        if e_owner:
            self.skipTest("connessi come proprietario: la porta si prova solo come app")
        self.assertFalse(insert)
        self.assertFalse(update)

    # 2.
    def test_crea_e_modifica_una_causale_col_verbo(self) -> None:
        riga = self._nuova()
        self.assertIsInstance(riga["id"], int)
        self.assertEqual(riga["segno"], 1)
        self.assertNotIn("data_insert", riga)
        # La riga scritta porta `id` e i campi del form, non altro: e' la
        # stessa funzione che il metadata legge (§6.1).
        with connection.cursor() as cur:
            cur.execute("SELECT config.fn_pannello_colonne_scrivibili(%s)", [_REL])
            scrivibili = cur.fetchone()[0]
        self.assertEqual(set(riga), {"id", *scrivibili})

        esito = self.svc.update_record(_REL, riga["id"], {"descrizione": "Riscritta"})
        self.assertEqual(esito, {"updated": True})
        self.assertEqual(self.svc.get_record(_REL, riga["id"])["descrizione"], "Riscritta")

    # 3.
    def test_un_campo_che_non_si_scrive_e_rifiutato_col_suo_nome(self) -> None:
        riga = self._nuova()
        for campo in ("non_esiste", "data_insert", "id"):
            with self.subTest(campo=campo):
                self.assertEqual(
                    self._codice(
                        lambda campo=campo: self.svc.update_record(_REL, riga["id"], {campo: "x"})
                    ),
                    "E_PANNELLO_CAMPO_NON_AMMESSO",
                )
        self.assertEqual(
            self._codice(lambda: self.svc.update_record(_REL, riga["id"], {})),
            "E_PANNELLO_DATI_VUOTI",
        )

    # 4.
    def test_la_riga_che_non_c_e(self) -> None:
        with connection.cursor() as cur:
            cur.execute(f"SELECT COALESCE(max(id), 0) + 1000000 FROM {_REL}")
            assente = cur.fetchone()[0]
        self.assertEqual(
            self._codice(lambda: self.svc.update_record(_REL, assente, {"descrizione": "x"})),
            "E_PANNELLO_RIGA_NON_TROVATA",
        )
        self.assertEqual(
            self._codice(lambda: self.svc.get_record(_REL, assente)),
            "E_PANNELLO_RIGA_NON_TROVATA",
        )

    # 5.
    def test_una_tabella_del_solo_lookup_non_si_scrive(self) -> None:
        self.assertEqual(
            self._codice(lambda: self.svc.create_record("pagamenti.enti_incasso", {"codice": "X"})),
            "E_CORE_VALIDATION",
        )


# Scopo: Il chiamante della catena: un operatore non superuser, con l'id
#        dell'auth_user costruito dal test.
class _Utente:
    is_authenticated = True
    is_superuser = False

    def __init__(self, auth_user_id: int) -> None:
        self.id = auth_user_id
        self.pk = auth_user_id


class PannelloDuePuntiDiApplicazioneDbTests(TestCase):
    """La catena del backend (D-P7) e il verbo chiedono la STESSA cosa: il
    livello sull'oggetto della riga di lista, con l'area di
    `fn_area_di_oggetto`. Se divergessero, il 403 del backend e il rifiuto del
    DB darebbero risposte diverse alla stessa scrittura.

    ⚠️ L'operatore e' COSTRUITO (`dbops.fn_pgtap_crea_emittente_operatore`:
    identita' OPERATORE, non super admin, nessun livello) e il livello glielo
    da' un override sull'AREA `magazzino`, come il test 12 del pgTAP di
    `fn_pannello_scrivi`. Non il superuser del contesto degli altri test:
    quello passerebbe per bypass, e non proverebbe niente.

    ⛔ Fino al 2026-09-28 il livello lo dava un override sull'oggetto
    `('magazzino', 'causali')`. Per la D-2 (brief-db-be-fe-catalogo-oggetti-
    permessi) le chiavi del pannello NON sono oggetti personalizzabili: valgono
    come la loro area, e dal `20260928-02` la FK
    `fk_user_override_oggetti_catalogo` rifiuta quell'override (23503)."""

    @classmethod
    def setUpClass(cls) -> None:
        super().setUpClass()
        richiedi_db_provvisto()

    def setUp(self) -> None:
        apri_transazione_annullata(self)
        with connection.cursor() as cur:
            cur.execute("SELECT auth_user_id FROM dbops.fn_pgtap_crea_emittente_operatore()")
            self.uid = int(cur.fetchone()[0])
            cur.execute("SELECT script.fn_pgtap_set_contesto_operatore(%s)", [self.uid])
        self.svc = ConfigCrudService()

    # Scopo: Da' all'operatore costruito `livello` sull'area della riga
    #        (`fn_area_di_oggetto('magazzino', 'causali')` = `magazzino`).
    def _livello_sull_area_magazzino(self, livello: str) -> None:
        with connection.cursor() as cur:
            cur.execute(
                "INSERT INTO config.user_override_aree (auth_user_id, area_id, livello, motivo)"
                " SELECT %s, af.id, %s, 'Fixture test pannello'"
                "   FROM config.aree_funzionali af WHERE af.schema_db = 'magazzino'",
                [self.uid, livello],
            )
            self.assertEqual(cur.rowcount, 1, "area `magazzino` assente dal catalogo aree")

    def _catena(self, metodo: str):
        view = ConfigTableRecordsView()
        view.kwargs = {"rel": _REL}
        return ZeroERPPermission.valuta(_Utente(self.uid), view, method=metodo, cache={})

    def _crea(self) -> dict:
        codice = f"T{uuid.uuid4().hex[:8].upper()}"
        return self.svc.create_record(
            _REL, {"codice": codice, "descrizione": "Causale del test", "segno": 1},
        )

    # 6.
    def test_lettura_sulle_causali_legge_e_non_scrive(self) -> None:
        self._livello_sull_area_magazzino("LETTURA")
        self.assertTrue(self._catena("GET").consentito)
        esito = self._catena("POST")
        self.assertFalse(esito.consentito)
        self.assertIs(esito.motivo, MotivoDiniego.LIVELLO_INSUFFICIENTE)
        self.assertEqual(esito.area, "magazzino")
        # Il verbo, raggiunto senza passare dalla catena, rifiuta lo stesso.
        with self.assertRaises(ServiceError) as ctx, transaction.atomic():
            self._crea()
        self.assertEqual(ctx.exception.code, "E_PERMESSO_NEGATO")

    # 7.
    def test_tutto_sulle_causali_scrive(self) -> None:
        self._livello_sull_area_magazzino("TUTTO")
        self.assertTrue(self._catena("POST").consentito)
        self.assertIsInstance(self._crea()["id"], int)
