# ------------------------------------------------------------
# SPDX-License-Identifier: AGPL-3.0-or-later
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
3b) IndirizziRuoloDbTests.test_un_indirizzo_singolo_dalla_madre — `fn_crea_indirizzo_ruolo`: forma estera,
   la riga al client, lo stesso tipo due volte `E_ANAG_DUPLICATO` (R-DB-16b, 2026-10-19)
3b-bis) IndirizziRuoloDbTests.test_la_lista_del_ruolo_porta_il_codice_interno — la GET del ruolo:
   `tipo_indirizzo_codice_interno` uguale al catalogo, livello soggetto e livello ruolo (2026-11-01)
3c) IndirizziSoggettoPluraleDbTests.test_gli_obbligatori_copiati_dal_primo — `fn_crea_indirizzi_soggetto`
   dalla creazione del soggetto; il guard differito passa
3d) IndirizziSoggettoPluraleDbTests.test_senza_auto_clone_solo_quello_dato — `auto_clone: false`
3e) IstanzaDelloStessoSoggettoDbTests.test_creare_con_l_istanza_di_un_altro_soggetto — 400
   `E_ISTANZA_ALTRO_SOGGETTO` sul campo `istanza_utility_id`; l'istanza dello stesso soggetto passa (R-DB-17a)
3f) IstanzaDelloStessoSoggettoDbTests.test_spostare_sull_istanza_di_un_altro_soggetto — la modifica, lo stesso rifiuto
4) VestePortaleDbTests.test_veste_portale_dalla_madre — spenta come la crea l'invito; una veste
   OPERATORE non nasce da qui
5) PreferenzeDbTests.test_emittente_attivo_dalla_madre — la scelta e il suo cambio, una riga
6) PreferenzeDbTests.test_override_valido_dal_null_resta_null — la chiave viaggia sempre: null e'
   «senza inizio», non il DEFAULT della data operativa
7) IndirizzoLiberoSoggettoDbTests.test_indirizzo_libero_italiano_del_soggetto_nasce — comune e CAP
   arrivano alla madre `fn_crea_indirizzo_soggetto`
8) IndirizzoLiberoSoggettoDbTests.test_indirizzo_libero_estero_del_soggetto_nasce — la forma estera
   (localita', codice postale) passa dalla firma jsonb della madre (2026-10-18, D-4)
9) IndirizzoLiberoSoggettoDbTests.test_forma_incompleta_rifiutata_col_campo — il guard dice il campo:
   400 `E_INDIRIZZO_LIBERO_INCOMPLETO` sul campo, non piu' `E_DATABASE`
10) StatiLookupDbTests.test_la_tendina_dice_forma_e_stato_proposto — `catalogo_comuni_completo` per
    stato e uno e un solo stato `proposto`, quello di `fn_stato_proposto_id`
"""
from __future__ import annotations

import json
import unittest
import uuid
from decimal import Decimal

from django.contrib.auth.models import User
from django.db import DatabaseError, connection, transaction

from apps.core.services.db_error_fields import diagnostica_db, structured_db_error_code
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

    # Scopo: Uno stato senza catalogo dei comuni: la forma estera, la localita'
    #        (dal 2026-10-18 la forma la decide lo stato, D-2 di Tid). Salta se
    #        non c'e'. Sede unica per i test di questo file (2026-10-19).
    def _stato_estero(self) -> int:
        with connection.cursor() as cur:
            cur.execute(
                "SELECT id FROM config.stati WHERE NOT catalogo_comuni_completo ORDER BY id LIMIT 1"
            )
            riga = cur.fetchone()
        if riga is None:
            self.skipTest("Nessuno stato senza catalogo dei comuni.")
        return int(riga[0])

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
        stato_id = self._stato_estero()
        # Un indirizzo in forma libera, estero (`chk_indirizzi_free_requirements`).
        scritti = SoggettiService().create_indirizzi_ruolo(sr_id, [{
            "tipo_indirizzo_codice_interno": primo, "indirizzo_libero": "Via di prova 1",
            "stato_id": stato_id, "locality": "Prova", "postal_code": "PB1",
            "administrative_area": "Area", "scala": "  ",
        }])
        obbligatori, presenti = self._tipi(sr_id)
        self.assertEqual(len(obbligatori), scritti)
        self.assertEqual(obbligatori, presenti)
        self.assertEqual(0, SoggettiService().create_indirizzi_ruolo(sr_id, [{
            "tipo_indirizzo_codice_interno": primo, "indirizzo_libero": "Via di prova 2",
            "stato_id": stato_id, "locality": "Prova", "postal_code": "PB2", "sublocality": "Sub",
        }]))
        # Il COMMIT: il guard differito trova gli obbligatori.
        with connection.cursor() as cur:
            cur.execute("SET CONSTRAINTS ALL IMMEDIATE")

    # Scopo: UN indirizzo del ruolo dalla madre singolare
    #        `fn_crea_indirizzo_ruolo` (R-DB-16b, 2026-10-19): la forma estera
    #        arriva (la INSERT di prima non la conosceva), la riga torna al
    #        client, lo stesso tipo una seconda volta e' il duplicato del vincolo
    #        tradotto per SQLSTATE anche se sollevato DENTRO la funzione.
    def test_un_indirizzo_singolo_dalla_madre(self):
        from apps.anagrafiche.services.soggetti_service import SoggettiService

        sr_id = self._ruolo_fornitore()
        obbligatori, _ = self._tipi(sr_id)
        if not obbligatori:
            self.skipTest("La matrice del ruolo FO non ha tipi obbligatori.")
        primo = sorted(obbligatori)[0]
        stato_id = self._stato_estero()
        payload = {
            "tipo_indirizzo_codice_interno": primo, "indirizzo_libero": "Via singola 1",
            "stato_id": stato_id, "locality": "Prova", "postal_code": "PS1", "scala": "",
        }
        riga = SoggettiService().create_indirizzo_ruolo(sr_id, dict(payload))
        self.assertEqual((sr_id, None, "Via singola 1", stato_id), (
            riga["soggetto_ruolo_id"], riga["istanza_utility_id"],
            riga["indirizzo_libero"], riga["stato_id"],
        ))
        with connection.cursor() as cur:
            cur.execute(
                "SELECT ti.codice_interno, i.locality, i.postal_code"
                "  FROM anagrafiche.indirizzi i"
                "  JOIN config.tipi_indirizzi ti ON ti.id = i.tipo_indirizzo_id"
                " WHERE i.id = %s",
                [riga["id"]],
            )
            self.assertEqual((primo, "Prova", "PS1"), cur.fetchone())

        doppio = self._rifiuto(lambda: SoggettiService().create_indirizzo_ruolo(sr_id, dict(payload)))
        self.assertEqual("E_ANAG_DUPLICATO", doppio.code)

    # Scopo: La lista del ruolo (`RuoloIndirizziView.get`, SQL nella view sulle
    #        resolved derivate) porta `tipo_indirizzo_codice_interno` in OGNI
    #        livello della cascata, uguale al catalogo: il drawer in contesto
    #        ruolo la confronta col `codice` della matrice e la rimanda alla
    #        madre per «sostituisci». Fino al 2026-11-01 le viste `_ruolo` e
    #        `_soggetto` davano solo `tipo_indirizzo_codice`, il display. Due
    #        viste, due livelli: il soggetto prima (nessun tipo del ruolo lo
    #        copre ancora), poi il ruolo.
    def test_la_lista_del_ruolo_porta_il_codice_interno(self):
        from types import SimpleNamespace

        from apps.anagrafiche.api.views_indirizzi_ruolo import RuoloIndirizziView
        from apps.anagrafiche.services.soggetti_service import SoggettiService

        sr_id = self._ruolo_fornitore()
        obbligatori, _ = self._tipi(sr_id)
        if not obbligatori:
            self.skipTest("La matrice del ruolo FO non ha tipi obbligatori.")
        stato_id = self._stato_estero()
        with connection.cursor() as cur:
            cur.execute("SELECT soggetto_id FROM anagrafiche.soggetti_ruoli WHERE id = %s", [sr_id])
            soggetto_id = str(cur.fetchone()[0])

        def _lista() -> dict:
            resp = RuoloIndirizziView().get(SimpleNamespace(query_params={}), sr_id)
            return json.loads(resp.content)["data"]

        def _attesi(righe: list[dict]) -> dict[int, str]:
            with connection.cursor() as cur:
                cur.execute(
                    "SELECT id, codice_interno FROM config.tipi_indirizzi WHERE id = ANY(%s)",
                    [[r["tipo_indirizzo_id"] for r in righe]],
                )
                return dict(cur.fetchall())

        SoggettiService().create_indirizzo_soggetto(soggetto_id, {
            "tipo_indirizzo_codice_interno": "FATT", "indirizzo_libero": "Hauptstrasse 5",
            "stato_id": stato_id, "locality": "Berlin", "postal_code": "10115",
        })
        del_soggetto = _lista()["indirizzi_soggetto"]
        self.assertTrue(del_soggetto)
        self.assertEqual(
            _attesi(del_soggetto),
            {r["tipo_indirizzo_id"]: r["tipo_indirizzo_codice_interno"] for r in del_soggetto},
        )

        SoggettiService().create_indirizzi_ruolo(sr_id, [{
            "tipo_indirizzo_codice_interno": sorted(obbligatori)[0], "indirizzo_libero": "Via lista 1",
            "stato_id": stato_id, "locality": "Prova", "postal_code": "PL1",
        }])
        del_ruolo = _lista()["indirizzi_ruolo"]
        self.assertEqual(obbligatori, {r["tipo_indirizzo_codice_interno"] for r in del_ruolo})
        self.assertEqual(
            _attesi(del_ruolo),
            {r["tipo_indirizzo_id"]: r["tipo_indirizzo_codice_interno"] for r in del_ruolo},
        )


class IndirizziSoggettoPluraleDbTests(_MondoCostruito):
    """Gli indirizzi della creazione del soggetto dalla madre plurale
    `fn_crea_indirizzi_soggetto` (R-DB-16b, 2026-10-19): fino ad allora la copia
    degli obbligatori e il ciclo delle righe erano una saga del backend."""

    # Scopo: Un tipo di soggetto PF con almeno un tipo d'indirizzo obbligatorio
    #        (seed: contratto) e i suoi obbligatori. PF: la PG vorrebbe anche i
    #        dati societari, che qui non c'entrano.
    def _tipo_pf_con_obbligatori(self) -> tuple[int, set[str]]:
        with connection.cursor() as cur:
            cur.execute(
                """
                SELECT tsd.id, array_agg(ti.codice_interno ORDER BY ti.codice_interno)
                  FROM config.tipi_soggetto_dettaglio tsd
                  JOIN config.tipi_soggetto ts ON ts.id = tsd.tipo_soggetto_id
                  JOIN config.tipi_soggetto_dettaglio_tipi_indirizzo m
                    ON m.tipo_soggetto_dettaglio_id = tsd.id AND m.attivo AND m.obbligatorio
                  JOIN config.tipi_indirizzi ti ON ti.id = m.tipo_indirizzo_id
                 WHERE ts.natura_soggetto::text = 'PF'
                 GROUP BY tsd.id
                 ORDER BY count(*) DESC, tsd.id
                 LIMIT 1
                """
            )
            riga = cur.fetchone()
        if riga is None:
            self.skipTest("Nessun tipo di soggetto PF con indirizzi obbligatori.")
        return int(riga[0]), set(riga[1])

    def _crea(self, tipo_id: int, primo: str, **extra) -> str:
        from apps.anagrafiche.services.soggetti_service import SoggettiService

        with connection.cursor() as cur:
            cur.execute("SELECT dbops.fn_pgtap_cf_libero()")
            cf = str(cur.fetchone()[0])
            cur.execute("SELECT id FROM config.tipi_contatti ORDER BY id LIMIT 1")
            tipo_contatto = cur.fetchone()[0]
        stato_id = self._stato_estero()
        return SoggettiService().create_soggetto({
            "tipo_soggetto_dettaglio_id": tipo_id,
            # `M`: il CF del builder e' maschile (congruenza CF/sesso del BE).
            "cognome": "Plurale", "nome": "Indirizzi", "sesso": "M",
            "codice_fiscale": cf,
            "contatto": {
                "nominativo": "Indirizzi plurale", "tipo_contatto_id": tipo_contatto,
                "email": "indirizzi.plurale@test.invalid",
            },
            "indirizzi": [{
                "tipo_indirizzo_codice_interno": primo, "indirizzo_libero": "Via plurale 1",
                "stato_id": stato_id, "locality": "Prova", "postal_code": "PP1", "scala": "",
            }],
            **extra,
        })["id"]

    @staticmethod
    def _presenti(soggetto_id: str) -> set[str]:
        with connection.cursor() as cur:
            cur.execute(
                "SELECT ti.codice_interno FROM anagrafiche.indirizzi_soggetti i"
                "  JOIN config.tipi_indirizzi ti ON ti.id = i.tipo_indirizzo_id"
                " WHERE i.soggetto_id = %s::uuid",
                [soggetto_id],
            )
            return {r[0] for r in cur.fetchall()}

    def test_gli_obbligatori_copiati_dal_primo(self):
        tipo_id, obbligatori = self._tipo_pf_con_obbligatori()
        soggetto_id = self._crea(tipo_id, sorted(obbligatori)[0])
        self.assertEqual(obbligatori, self._presenti(soggetto_id))
        # Il COMMIT: il guard differito trova gli obbligatori.
        with connection.cursor() as cur:
            cur.execute("SET CONSTRAINTS ALL IMMEDIATE")

    def test_senza_auto_clone_solo_quello_dato(self):
        tipo_id, obbligatori = self._tipo_pf_con_obbligatori()
        primo = sorted(obbligatori)[0]
        soggetto_id = self._crea(tipo_id, primo, auto_clone=False)
        self.assertEqual({primo}, self._presenti(soggetto_id))


class IstanzaDelloStessoSoggettoDbTests(_MondoCostruito):
    """L'istanza di un indirizzo di ruolo e' del soggetto del ruolo (R-BE-15,
    guard del DB dal 2026-10-19): il rifiuto arriva dal percorso del backend
    col codice e il campo, e il middleware ne fa un 400 sul campo (R-DB-17a)."""

    # ⚠️ Il mondo come nei test di `pagamenti`: azienda e operatore, il
    #    contesto di QUELL'operatore (il BA vuole un emittente su cui lavorare,
    #    e la sua RLS lo legge dal contesto), poi i due clienti.
    def setUp(self) -> None:
        apri_transazione_annullata(self)
        with connection.cursor() as cur:
            cur.execute(
                "CREATE TEMP TABLE _mondo_istanza AS"
                " SELECT m.* FROM dbops.fn_pgtap_crea_emittente_operatore() m"
            )
            cur.execute(
                "SELECT script.fn_pgtap_set_contesto_operatore("
                "(SELECT auth_user_id FROM _mondo_istanza))"
            )
            cur.execute(
                "SELECT soggetto_ruolo_id, istanza_utility_id"
                "  FROM dbops.fn_pgtap_crea_cliente_ba('e2e istanza stesso soggetto A')"
            )
            self.sr_a, self.ist_a = cur.fetchone()
            cur.execute(
                "SELECT istanza_utility_id FROM dbops.fn_pgtap_crea_cliente_ba('e2e istanza stesso soggetto B')"
            )
            self.ist_b = cur.fetchone()[0]
            # Un indirizzo libero italiano nella forma che il guard pretende.
            cur.execute(
                "SELECT to_jsonb(fm) FROM dbops.fn_pgtap_indirizzo_libero_forma("
                "script.fn_stato_id_da_iso2('IT')) fm"
            )
            forma = {k: v for k, v in json.loads(cur.fetchone()[0]).items() if v is not None}
            cur.execute("SELECT script.fn_stato_id_da_iso2('IT')")
            self.indirizzo = {
                "tipo_indirizzo_codice_interno": "POSTA", "indirizzo_libero": "Via e2e istanza 1",
                "stato_id": cur.fetchone()[0], **forma,
            }

    # Scopo: il rifiuto come lo vede il client: codice, status e campo.
    def _rifiuto_sul_campo(self, azione) -> None:
        from apps.core.services.error_translator import ErrorTranslator

        with self.assertRaises(DatabaseError) as ctx, transaction.atomic():
            azione()
        errore = ErrorTranslator.to_api_error(ctx.exception)
        self.assertEqual(
            ("E_ISTANZA_ALTRO_SOGGETTO", 400, ["istanza_utility_id"]),
            (errore.code, ErrorTranslator.get_http_status(errore), list(errore.fields or [])),
        )

    def test_creare_con_l_istanza_di_un_altro_soggetto(self):
        from apps.anagrafiche.services.soggetti_service import SoggettiService

        self._rifiuto_sul_campo(lambda: SoggettiService().create_indirizzo_ruolo(
            self.sr_a, {**self.indirizzo, "istanza_utility_id": self.ist_b},
        ))
        riga = SoggettiService().create_indirizzo_ruolo(
            self.sr_a, {**self.indirizzo, "istanza_utility_id": self.ist_a},
        )
        self.assertEqual(self.ist_a, riga["istanza_utility_id"])

    def test_spostare_sull_istanza_di_un_altro_soggetto(self):
        from apps.anagrafiche.services.soggetti_service import SoggettiService

        riga = SoggettiService().create_indirizzo_ruolo(
            self.sr_a, {**self.indirizzo, "istanza_utility_id": self.ist_a},
        )
        self._rifiuto_sul_campo(lambda: SoggettiService().update_indirizzo_ruolo(
            self.sr_a, riga["id"], {"istanza_utility_id": self.ist_b},
        ))


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
            "tipo_indirizzo_codice_interno": "FATT", "indirizzo_libero": "Localita' Prova snc",
            "stato_id": stato_id, "comune_id": comune_id, "codice_postale_id": cap_id,
        })
        with connection.cursor() as cur:
            cur.execute(
                "SELECT indirizzo_libero, comune_id, codice_postale_id"
                "  FROM anagrafiche.indirizzi_soggetti WHERE id = %s",
                [esito["id"]],
            )
            self.assertEqual(("Localita' Prova snc", comune_id, cap_id), cur.fetchone())

    def test_indirizzo_libero_estero_del_soggetto_nasce(self):
        from apps.anagrafiche.services.soggetti_service import SoggettiService

        stato_id = self._stato_estero()
        soggetto_id = self._soggetto_pg("Soggetto e2e indirizzo estero")
        esito = SoggettiService().create_indirizzo_soggetto(soggetto_id, {
            "tipo_indirizzo_codice_interno": "FATT", "indirizzo_libero": "Hauptstrasse 5",
            "stato_id": stato_id, "locality": "Berlin", "postal_code": "10115",
        })
        with connection.cursor() as cur:
            cur.execute(
                "SELECT stato_id, locality, postal_code, comune_id"
                "  FROM anagrafiche.indirizzi_soggetti WHERE id = %s",
                [esito["id"]],
            )
            self.assertEqual((stato_id, "Berlin", "10115", None), cur.fetchone())

    def test_forma_incompleta_rifiutata_col_campo(self):
        from apps.anagrafiche.services.soggetti_service import SoggettiService

        stato_id = self._stato_estero()
        soggetto_id = self._soggetto_pg("Soggetto e2e indirizzo incompleto")
        # L'errore di dominio del guard sale come `DatabaseError` e lo traduce il
        # middleware (`ErrorTranslator`): qui si legge come lo legge lui.
        with self.assertRaises(DatabaseError) as ctx, transaction.atomic():
            SoggettiService().create_indirizzo_soggetto(soggetto_id, {
                "tipo_indirizzo_codice_interno": "FATT", "indirizzo_libero": "Hauptstrasse 5",
                "stato_id": stato_id,
            })
        diagnostica = diagnostica_db(ctx.exception)
        self.assertEqual("E_INDIRIZZO_LIBERO_INCOMPLETO", diagnostica.codice)
        self.assertEqual("locality", diagnostica.campo)


class StatiLookupDbTests(unittest.TestCase):
    """La tendina degli stati per il form dell'indirizzo (2026-10-18)."""

    @classmethod
    def setUpClass(cls) -> None:
        richiedi_db_provvisto()

    def test_la_tendina_dice_forma_e_stato_proposto(self):
        from apps.anagrafiche.db.geo_repository import CHI_STATI_LOOKUP
        from apps.anagrafiche.services.geo_service import GeoService

        righe = GeoService().lookup_stati()
        self.assertTrue(righe)
        self.assertTrue(all(isinstance(r["catalogo_comuni_completo"], bool) for r in righe))
        proposti = [r["id"] for r in righe if r["proposto"]]
        with connection.cursor() as cur:
            # Lo stesso `p_chi` della tendina: oggi pesa sull'override (R-BE-13).
            cur.execute("SELECT script.fn_stato_proposto_id(%s)", [CHI_STATI_LOOKUP])
            self.assertEqual([cur.fetchone()[0]], proposti)

