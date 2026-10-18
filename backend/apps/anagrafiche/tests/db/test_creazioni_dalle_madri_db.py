# ------------------------------------------------------------
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Le creazioni del backend che dal 2026-10-18 passano dalle MADRI del
#        DB (2b-2 di brief-db-processi-accensione-per-ambiente), provate sul
#        DATABASE VERO: il binding della chiamata (firma, jsonb dei campi) e la
#        traduzione per nome dei vincoli, che una violazione sollevata DENTRO
#        la funzione deve conservare. I mock non vedono nessuna delle due cose.
# Note: ⚠️ Opt-in `ZEROERP_TEST_DB_E2E=1` (acceso in CI). Il mondo si
#       COSTRUISCE coi builder `dbops.fn_pgtap_*`, in transazione ANNULLATA.
# ------------------------------------------------------------
"""
Indice test eseguiti (opt-in `ZEROERP_TEST_DB_E2E=1`):
1) EmittenteDbTests.test_crea_emittente_dalla_madre — ruolo EF, riga, campi
2) EmittenteDbTests.test_duplicati_tradotti_per_nome — codice e soggetto gia' emittenti
3) IndirizziRuoloDbTests.test_un_indirizzo_e_gli_obbligatori_clonati — uno dal payload, gli
   obbligatori della matrice del ruolo clonati; una seconda corsa non scrive niente; il
   guard differito passa
4) VestePortaleDbTests.test_veste_portale_dalla_madre — spenta come la crea l'invito; una veste
   OPERATORE non nasce da qui
5) PreferenzeDbTests.test_emittente_attivo_dalla_madre — la scelta e il suo cambio, una riga
6) PreferenzeDbTests.test_override_valido_dal_null_resta_null — la chiave viaggia sempre: null e'
   «senza inizio», non il DEFAULT della data operativa
7) IndirizzoLiberoSoggettoDbTests.test_indirizzo_libero_italiano_del_soggetto_nasce — comune e CAP
   arrivano alla madre `fn_crea_indirizzo_soggetto`
"""
from __future__ import annotations

import unittest
import uuid
from decimal import Decimal

from django.contrib.auth.models import User
from django.db import DatabaseError, connection, transaction

from apps.core.services.db_error_fields import structured_db_error_code
from apps.core.services.service_errors import ServiceError
from apps.core.tests.db_e2e import apri_contesto_operatore, apri_transazione_annullata, richiedi_db_provvisto


class _MondoCostruito(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        richiedi_db_provvisto()

    def setUp(self) -> None:
        apri_transazione_annullata(self)
        with connection.cursor() as cur:
            apri_contesto_operatore(cur)

    # P.IVA libera dal builder: una fissa collide coi dati.
    @staticmethod
    def _soggetto_pg(nome: str) -> str:
        with connection.cursor() as cur:
            cur.execute("SELECT dbops.fn_pgtap_crea_soggetto_pg(%s)", [nome])
            return str(cur.fetchone()[0])

    # Scopo: Esegue `azione` in un savepoint e ne restituisce il ServiceError.
    def _rifiuto(self, azione) -> ServiceError:
        with self.assertRaises(ServiceError) as ctx, transaction.atomic():
            azione()
        return ctx.exception


class EmittenteDbTests(_MondoCostruito):

    @staticmethod
    def _codice() -> str:
        return "MD" + uuid.uuid4().hex[:8].upper()

    @staticmethod
    def _servizio():
        from apps.anagrafiche.services.emittenti_fiscali_service import EmittentiFiscaliService

        return EmittentiFiscaliService()

    def test_crea_emittente_dalla_madre(self):
        soggetto_id = self._soggetto_pg("Emittente e2e madre")
        esito = self._servizio().crea_emittente({
            "soggetto_id": soggetto_id, "codice": self._codice(),
            "bollo_auto": False, "bollo_soglia": "77.47",
        })
        with connection.cursor() as cur:
            cur.execute(
                """
                SELECT sr.soggetto_id::text, tr.codice_interno, ef.bollo_auto, ef.bollo_soglia
                  FROM anagrafiche.emittenti_fiscali ef
                  JOIN anagrafiche.soggetti_ruoli sr ON sr.id = ef.soggetto_ruolo_id
                  JOIN config.tipi_ruoli tr ON tr.id = sr.tipo_ruolo_id
                 WHERE ef.id = %s AND ef.soggetto_ruolo_id = %s
                """,
                [esito["id"], esito["soggetto_ruolo_id"]],
            )
            riga = cur.fetchone()
        self.assertEqual((soggetto_id, "EF", False), riga[:3])
        self.assertEqual(Decimal("77.47"), riga[3])

    def test_duplicati_tradotti_per_nome(self):
        codice = self._codice()
        self._servizio().crea_emittente({"soggetto_id": self._soggetto_pg("Emittente e2e A"), "codice": codice})

        stesso_codice = self._rifiuto(lambda: self._servizio().crea_emittente(
            {"soggetto_id": self._soggetto_pg("Emittente e2e B"), "codice": codice},
        ))
        self.assertEqual("E_ANAG_DUPLICATO", stesso_codice.code)
        self.assertIn("codice", stesso_codice.message)

        soggetto_id = self._soggetto_pg("Emittente e2e C")
        self._servizio().crea_emittente({"soggetto_id": soggetto_id, "codice": self._codice()})
        stesso_soggetto = self._rifiuto(lambda: self._servizio().crea_emittente(
            {"soggetto_id": soggetto_id, "codice": self._codice()},
        ))
        self.assertEqual("E_ANAG_DUPLICATO", stesso_soggetto.code)
        self.assertIn("soggetto", stesso_soggetto.message)


class IndirizziRuoloDbTests(_MondoCostruito):

    # Scopo: Un ruolo FO nuovo, senza indirizzi. La finestra differita: il
    #        guard degli indirizzi obbligatori li pretende al COMMIT.
    #        ⚠️ Il soggetto PRIMA della finestra: il builder chiude con
    #        `SET CONSTRAINTS ALL IMMEDIATE`.
    def _ruolo_fornitore(self) -> int:
        soggetto_id = self._soggetto_pg("Fornitore e2e indirizzi")
        with connection.cursor() as cur:
            cur.execute("SET CONSTRAINTS ALL DEFERRED")
            cur.execute(
                "SELECT script.fn_get_or_create_soggetto_ruolo(%s::uuid, 'FO')",
                [soggetto_id],
            )
            return int(cur.fetchone()[0])

    # Scopo: I codici dei tipi obbligatori della matrice del ruolo (seed:
    #        contratto, non popolazione) e quelli presenti sul ruolo.
    @staticmethod
    def _tipi(soggetto_ruolo_id: int) -> tuple[set[str], set[str]]:
        with connection.cursor() as cur:
            cur.execute(
                """
                SELECT ti.codice_interno
                  FROM config.tipi_ruolo_tipi_indirizzo m
                  JOIN config.tipi_indirizzi ti ON ti.id = m.tipo_indirizzo_id
                  JOIN anagrafiche.soggetti_ruoli sr ON sr.tipo_ruolo_id = m.tipo_ruolo_id
                 WHERE sr.id = %s AND m.attivo AND m.obbligatorio
                """,
                [soggetto_ruolo_id],
            )
            obbligatori = {r[0] for r in cur.fetchall()}
            cur.execute(
                """
                SELECT ti.codice_interno
                  FROM anagrafiche.indirizzi i
                  JOIN config.tipi_indirizzi ti ON ti.id = i.tipo_indirizzo_id
                 WHERE i.soggetto_ruolo_id = %s
                """,
                [soggetto_ruolo_id],
            )
            return obbligatori, {r[0] for r in cur.fetchall()}

    def test_un_indirizzo_e_gli_obbligatori_clonati(self):
        from apps.anagrafiche.services.soggetti_service import SoggettiService

        sr_id = self._ruolo_fornitore()
        obbligatori, _ = self._tipi(sr_id)
        if not obbligatori:
            self.skipTest("La matrice del ruolo FO non ha tipi obbligatori: niente da clonare.")
        primo = sorted(obbligatori)[0]
        with connection.cursor() as cur:
            cur.execute("SELECT id FROM config.stati ORDER BY id LIMIT 1")
            stato_id = cur.fetchone()[0]
        # Un indirizzo in forma libera, estero (`chk_indirizzi_free_requirements`).
        scritti = SoggettiService().create_indirizzi_ruolo(sr_id, [{
            "tipo_indirizzo_codice": primo, "indirizzo_libero": "Via di prova 1",
            "stato_id": stato_id, "locality": "Prova", "postal_box": "PB1",
            "administrative_area": "Area", "scala": "  ",
        }])
        obbligatori, presenti = self._tipi(sr_id)
        self.assertEqual(len(obbligatori), scritti)
        self.assertEqual(obbligatori, presenti)
        self.assertEqual(0, SoggettiService().create_indirizzi_ruolo(sr_id, [{
            "tipo_indirizzo_codice": primo, "indirizzo_libero": "Via di prova 2",
            "stato_id": stato_id, "locality": "Prova", "postal_box": "PB2", "sublocality": "Sub",
        }]))
        # Il COMMIT: il guard differito trova gli obbligatori.
        with connection.cursor() as cur:
            cur.execute("SET CONSTRAINTS ALL IMMEDIATE")


class VestePortaleDbTests(unittest.TestCase):
    """La veste dei portali dalla madre `fn_crea_veste_portale` (lotto 6)."""

    @classmethod
    def setUpClass(cls) -> None:
        richiedi_db_provvisto("dbops.fn_pgtap_crea_mondo_cliente(text,character varying)")

    def setUp(self) -> None:
        apri_transazione_annullata(self)

    def test_veste_portale_dalla_madre(self):
        from apps.portale.db.portale_repository import PortaleRepository

        with connection.cursor() as cur:
            cur.execute(
                "SELECT cliente_soggetto_ruolo_id FROM dbops.fn_pgtap_crea_mondo_cliente('MDVESTE')"
            )
            sr_id = int(cur.fetchone()[0])
        utente = User.objects.create_user(username=f"e2e_veste_{uuid.uuid4().hex[:10]}")
        repo = PortaleRepository()
        identita_id = repo.create_identita_portale(
            auth_user_id=utente.id, soggetto_ruolo_id=sr_id,
            ruolo_applicativo="CLIENTE_PORTALE", attivo=False,
        )
        with connection.cursor() as cur:
            cur.execute(
                "SELECT auth_user_id, soggetto_ruolo_id, ruolo_applicativo::text, attivo"
                "  FROM anagrafiche.identita_digitali WHERE id = %s",
                [identita_id],
            )
            self.assertEqual((utente.id, sr_id, "CLIENTE_PORTALE", False), cur.fetchone())

        with self.assertRaises(DatabaseError) as ctx, transaction.atomic():
            repo.create_identita_portale(
                auth_user_id=utente.id, soggetto_ruolo_id=sr_id,
                ruolo_applicativo="OPERATORE", attivo=True,
            )
        self.assertEqual("E_SCRIPT_CHIAMATA_NON_VALIDA", structured_db_error_code(ctx.exception))


class PreferenzeDbTests(unittest.TestCase):
    """Emittente attivo e override degli oggetti dalle madri di `config` (lotto 9)."""

    @classmethod
    def setUpClass(cls) -> None:
        richiedi_db_provvisto()

    def setUp(self) -> None:
        apri_transazione_annullata(self)
        self.utente = User.objects.create_user(username=f"e2e_pref_{uuid.uuid4().hex[:10]}")

    def test_emittente_attivo_dalla_madre(self):
        from apps.core.db.emittente_attivo_repository import EmittenteAttivoRepository

        with connection.cursor() as cur:
            cur.execute("SELECT emittente_fiscale_id FROM dbops.fn_pgtap_crea_emittente()")
            primo = int(cur.fetchone()[0])
            cur.execute("SELECT emittente_fiscale_id FROM dbops.fn_pgtap_crea_emittente()")
            secondo = int(cur.fetchone()[0])
        repo = EmittenteAttivoRepository()
        repo.set_preferenza(self.utente.id, primo)
        repo.set_preferenza(self.utente.id, secondo)
        self.assertEqual(secondo, repo.get_preferenza(self.utente.id))
        with connection.cursor() as cur:
            cur.execute(
                "SELECT count(*) FROM config.user_emittente_attivo WHERE auth_user_id = %s",
                [self.utente.id],
            )
            self.assertEqual(1, cur.fetchone()[0])

    def test_override_valido_dal_null_resta_null(self):
        from apps.amm_software.db.amm_software_repository import AmmSoftwareRepository

        with connection.cursor() as cur:
            cur.execute(
                "SELECT app_label, model_name FROM config.area_model_overrides"
                " WHERE NOT riservato ORDER BY id LIMIT 1"
            )
            riga = cur.fetchone()
        if riga is None:
            self.skipTest("Nessun oggetto non riservato a catalogo.")
        app_label, model_name = riga
        AmmSoftwareRepository().put_override_oggetti(self.utente.id, [{
            "app_label": app_label, "model_name": model_name, "livello": "BLOCCATO",
            "motivo": "e2e", "valido_dal": None, "valido_al": None,
        }])
        with connection.cursor() as cur:
            cur.execute(
                "SELECT livello::text, valido_dal FROM config.user_override_oggetti"
                " WHERE auth_user_id = %s",
                [self.utente.id],
            )
            self.assertEqual([("BLOCCATO", None)], cur.fetchall())


class IndirizzoLiberoSoggettoDbTests(_MondoCostruito):
    """L'indirizzo libero del soggetto (2026-10-18): fino a quel giorno il
    backend non passava comune e CAP alla madre, che li pretende, e un
    indirizzo libero del soggetto non poteva nascere."""

    def test_indirizzo_libero_italiano_del_soggetto_nasce(self):
        from apps.anagrafiche.services.soggetti_service import SoggettiService

        with connection.cursor() as cur:
            cur.execute(
                "SELECT cp.comune_id, cp.id, r.stato_id"
                "  FROM config.codici_postali cp"
                "  JOIN config.comuni c ON c.id = cp.comune_id"
                "  JOIN config.province p ON p.id = c.provincia_id"
                "  JOIN config.regioni r ON r.id = p.regione_id"
                " ORDER BY cp.id LIMIT 1"
            )
            riga = cur.fetchone()
        if riga is None:
            self.skipTest("Nessun CAP a catalogo.")
        comune_id, cap_id, stato_id = riga
        soggetto_id = self._soggetto_pg("Soggetto e2e indirizzo libero")
        esito = SoggettiService().create_indirizzo_soggetto(soggetto_id, {
            "tipo_indirizzo_codice": "FATT", "indirizzo_libero": "Localita' Prova snc",
            "stato_id": stato_id, "comune_id": comune_id, "codice_postale_id": cap_id,
        })
        with connection.cursor() as cur:
            cur.execute(
                "SELECT indirizzo_libero, comune_id, codice_postale_id"
                "  FROM anagrafiche.indirizzi_soggetti WHERE id = %s",
                [esito["id"]],
            )
            self.assertEqual(("Localita' Prova snc", comune_id, cap_id), cur.fetchone())

