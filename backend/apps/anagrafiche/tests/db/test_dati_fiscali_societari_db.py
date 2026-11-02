# ------------------------------------------------------------
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: I dati fiscali e societari del soggetto, dal service vero al DATABASE
#        VERO (brief-db-dati-fiscali-e-societari-del-soggetto, §5 e §8.3): cio'
#        che i test di servizio, col repository mockato, non vedono — il binding
#        del verbo `fn_scrivi_dati_societari` (parametri nominati, cast agli
#        enum), l'ORDINE «prima la natura, poi il verbo», i guard che arrivano
#        al client col campo da accendere, e i due lookup che leggono i
#        predicati dei guard.
# Note: ⛔ Il backend NON controlla le regole: stanno nei guard (natura → flag
#       PA/split, natura → forma, forma → REA e capitale, natura → titoli).
#       Qui si prova che i rifiuti arrivano col codice del catalogo e il campo,
#       passando da `ErrorTranslator.to_api_error` (lo stesso punto del
#       middleware).
#       ⚠️ Il mondo si COSTRUISCE (le societa' da `fn_pgtap_crea_soggetto_pg`,
#       il privato dal service), in transazione ANNULLATA; ogni rifiuto in un
#       SAVEPOINT. Il guard forma/natura e' DIFFERITO al COMMIT, che qui non
#       arriva mai: lo si fa scattare con `SET CONSTRAINTS ALL IMMEDIATE`.
#       Opt-in `ZEROERP_TEST_DB_E2E=1` (acceso in CI).
# ------------------------------------------------------------
"""
Indice test eseguiti (opt-in `ZEROERP_TEST_DB_E2E=1`):
1) DatiFiscaliSocietariDbTests.test_lookup_tipi_espone_le_ammissioni_pa_split
2) DatiFiscaliSocietariDbTests.test_privato_cliente_pa_rifiutato_col_campo
3) DatiFiscaliSocietariDbTests.test_societa_split_payment_accettato
4) DatiFiscaliSocietariDbTests.test_patch_dati_societari_scrive_col_verbo
5) DatiFiscaliSocietariDbTests.test_patch_codice_sdi_non_valido_accende_il_campo
6) DatiFiscaliSocietariDbTests.test_patch_forma_non_ammessa_accende_il_campo
7) DatiFiscaliSocietariDbTests.test_patch_solo_dati_societari_soggetto_inesistente
8) DatiFiscaliSocietariDbTests.test_cambio_natura_e_forma_nella_stessa_patch
9) DatiFiscaliSocietariDbTests.test_cambio_natura_senza_forma_rifiutato_al_commit
10) DatiFiscaliSocietariDbTests.test_lookup_forme_solo_ammesse_dalla_natura
11) DatiFiscaliSocietariDbTests.test_lookup_tipi_titolo_per_natura_societa
12) DatiFiscaliSocietariDbTests.test_lookup_tipi_titolo_per_natura_privato
13) DatiFiscaliSocietariDbTests.test_patch_rea_di_un_altro_soggetto_accende_il_campo
14) DatiFiscaliSocietariDbTests.test_lookup_e_risolutore_leggono_la_stessa_natura
15) DatiFiscaliSocietariDbTests.test_creazione_rea_di_un_altro_soggetto_accende_il_campo
16) DatiFiscaliSocietariDbTests.test_risolutore_ruolo_senza_default_dichiarato
17) DatiFiscaliSocietariDbTests.test_creazione_societa_con_data_di_costituzione
18) DatiFiscaliSocietariDbTests.test_creazione_ditta_individuale_con_la_sezione
19) DatiFiscaliSocietariDbTests.test_creazione_privato_con_la_sezione_rifiutata
"""
from __future__ import annotations

import unittest
from collections.abc import Callable
from decimal import Decimal
from typing import Any

from django.db import connection, transaction

from apps.core.services.error_translator import ErrorTranslator
from apps.core.tests.db_e2e import apri_contesto_operatore, apri_transazione_annullata, richiedi_db_provvisto

# Un uuid che nessun soggetto ha.
_SOGGETTO_INESISTENTE = "00000000-0000-0000-0000-000000000000"


class DatiFiscaliSocietariDbTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        richiedi_db_provvisto()

    def setUp(self) -> None:
        apri_transazione_annullata(self)
        with connection.cursor() as cur:
            apri_contesto_operatore(cur)
            cur.execute("SELECT codice_interno, id FROM config.tipi_soggetto_dettaglio")
            self.tipo = dict(cur.fetchall())
            cur.execute("SELECT codice, id FROM config.forme_giuridiche")
            self.forma = dict(cur.fetchall())
            cur.execute("SELECT id FROM config.tipi_contatti ORDER BY id LIMIT 1")
            self.tipo_contatto = cur.fetchone()[0]

    # Scopo: una societa' completa (dati societari col verbo, forma ammessa).
    # ⚠️ La fixture chiude con `SET CONSTRAINTS ALL IMMEDIATE` (verifica la sua
    #    saga), e l'effetto dura fino a fine transazione. Il guard forma/natura e'
    #    INITIALLY DEFERRED come in una richiesta vera: lo si rimette com'e'
    #    dichiarato, o il test 8 proverebbe un ordine che l'app non ha.
    def _pg(self, codice_tipo: str) -> str:
        with connection.cursor() as cur:
            cur.execute(
                "SELECT dbops.fn_pgtap_crea_soggetto_pg(%s, %s)",
                [f"Dati fiscali {codice_tipo}", self.tipo[codice_tipo]],
            )
            soggetto_id = str(cur.fetchone()[0])
            cur.execute(
                "SET CONSTRAINTS anagrafiche.trg_soggetti_def_guard_forma_giuridica_natura_upd DEFERRED"
            )
            return soggetto_id

    # Scopo: un privato, dal service.
    # ⚠️ Senza indirizzo: il guard differito degli indirizzi obbligatori non
    #    scatta, perche' la transazione si annulla. Quindi MAI nello stesso test
    #    di una societa': la sua fixture chiude con `SET CONSTRAINTS ALL
    #    IMMEDIATE`, che verifica i vincoli in sospeso e li rende immediati fino
    #    a fine transazione. Qui si provano i dati fiscali, non la completezza
    #    del soggetto.
    def _privato(self) -> str:
        from apps.anagrafiche.services.soggetti_service import SoggettiService

        with connection.cursor() as cur:
            cur.execute("SELECT dbops.fn_pgtap_cf_libero()")
            cf = str(cur.fetchone()[0])
        creato = SoggettiService().create_soggetto({
            "tipo_soggetto_dettaglio_id": self.tipo["PR"],
            "cognome": "Fiscali", "nome": "Dati", "sesso": "M",
            "codice_fiscale": cf,
            "contatto": {
                "nominativo": "Dati fiscali", "tipo_contatto_id": self.tipo_contatto,
                "email": "dati.fiscali@test.invalid",
            },
        })
        return str(creato["id"])

    @staticmethod
    def _dati_societari(soggetto_id: str) -> dict[str, Any] | None:
        from apps.anagrafiche.db.soggetti_repository import SoggettiRepository

        return SoggettiRepository().get_dati_societari(soggetto_id)

    # Scopo: lo stato intero della sezione com'e' oggi, da sovrapporre.
    def _stato(self, soggetto_id: str, **sovrapposti: Any) -> dict[str, Any]:
        ds = self._dati_societari(soggetto_id) or {}
        stato = {
            k: ds.get(k) for k in (
                "forma_giuridica_id", "id_prov_iscri_rea", "iscrizione_rea",
                "capitale_sociale", "socio_unico", "liquidazione",
                "destinatario_fe", "pec_fatturazione", "codice_sdi", "data_costituzione",
            )
        }
        if stato["capitale_sociale"] is not None:
            stato["capitale_sociale"] = str(stato["capitale_sociale"])
        stato.update(sovrapposti)
        return stato

    # Scopo: il rifiuto atteso, tradotto come lo traduce il middleware.
    def _rifiuto(
        self, fn: Callable[[], Any], codice: str, campo: str | None, status: int = 400,
    ) -> None:
        try:
            with transaction.atomic():
                fn()
        except Exception as exc:  # la strada e' cio' che si prova
            api = ErrorTranslator.to_api_error(exc)
            self.assertEqual(api.code, codice, f"{api.message} — {exc!r}")
            if campo:
                self.assertIn(campo, api.fields or (), f"campo {campo} non acceso")
            self.assertEqual(ErrorTranslator.get_http_status(api), status)
            return
        self.fail(f"atteso {codice}, accettato")

    # 1. Il form legge le due ammissioni dal lookup, coi valori del seed (A-2).
    def test_lookup_tipi_espone_le_ammissioni_pa_split(self):
        from apps.core.db.lookup_repository import LookupRepository

        ammessi = {
            t["codice_interno"]: (t["cliente_pa_ammesso"], t["split_payment_ammesso"])
            for t in LookupRepository().list_tipi_soggetto_dettaglio()
        }
        self.assertEqual(ammessi["PR"], (False, False))
        self.assertEqual(ammessi["DI"], (False, False))
        self.assertEqual(ammessi["SC"], (False, True))
        self.assertEqual(ammessi["ENC"], (True, True))

    # 2. Parte A: un privato non e' mai una PA — lo dice il guard, col campo.
    def test_privato_cliente_pa_rifiutato_col_campo(self):
        from apps.anagrafiche.services.soggetti_service import SoggettiService

        pr = self._privato()
        self._rifiuto(
            lambda: SoggettiService().update_soggetto(pr, {"cliente_pa": "S"}),
            "E_CLIENTE_PA_NON_AMMESSO", "cliente_pa",
        )

    # 3. Parte A: sulla societa' di capitali lo split payment e' ammesso.
    def test_societa_split_payment_accettato(self):
        from apps.anagrafiche.services.soggetti_service import SoggettiService

        sc = self._pg("SC")
        SoggettiService().update_soggetto(sc, {"split_payment": "s"})
        with connection.cursor() as cur:
            cur.execute("SELECT split_payment FROM anagrafiche.soggetti WHERE id = %s", [sc])
            self.assertEqual(cur.fetchone()[0], "S")

    # 4. Parte B: la PATCH scrive i dati societari col verbo, stato intero
    #    (prima del 2026-10-10 il drawer diceva «salvato» e non scriveva niente).
    def test_patch_dati_societari_scrive_col_verbo(self):
        from apps.anagrafiche.services.soggetti_service import SoggettiService

        sc = self._pg("SC")
        SoggettiService().update_soggetto(sc, {"dati_societari": self._stato(
            sc, destinatario_fe="C", codice_sdi="ABC1234", pec_fatturazione=None,
            capitale_sociale="25000.50", liquidazione="LS", data_costituzione="2020-03-15",
        )})
        ds = self._dati_societari(sc)
        assert ds is not None
        self.assertEqual(
            (ds["destinatario_fe"], ds["codice_sdi"], ds["capitale_sociale"],
             ds["liquidazione"], ds["data_costituzione"]),
            ("C", "ABC1234", Decimal("25000.50"), "LS", "2020-03-15"),
        )

    # 5. Il guard del canale FE accende `codice_sdi` (brief §5, voce B).
    def test_patch_codice_sdi_non_valido_accende_il_campo(self):
        from apps.anagrafiche.services.soggetti_service import SoggettiService

        sc = self._pg("SC")
        payload = {"dati_societari": self._stato(sc, destinatario_fe="C", codice_sdi="x")}
        self._rifiuto(
            lambda: SoggettiService().update_soggetto(sc, payload),
            "E_DATI_SOCIETARI_CODICE_SDI_NON_VALIDO", "codice_sdi",
        )

    # 6. Parte C: una forma che la natura non ammette (la ditta individuale su
    #    una societa' di capitali) e' rifiutata sul campo.
    def test_patch_forma_non_ammessa_accende_il_campo(self):
        from apps.anagrafiche.services.soggetti_service import SoggettiService

        sc = self._pg("SC")
        payload = {"dati_societari": self._stato(
            sc, forma_giuridica_id=self.forma["DI"],
            id_prov_iscri_rea=None, iscrizione_rea=None, capitale_sociale=None,
        )}
        self._rifiuto(
            lambda: SoggettiService().update_soggetto(sc, payload),
            "E_FORMA_GIURIDICA_NON_AMMESSA_PER_TIPO_SOGGETTO", "forma_giuridica_id",
        )

    # 7. Con i soli dati societari il «non trovato» lo dice il verbo, non un
    #    UPDATE vuoto del soggetto.
    def test_patch_solo_dati_societari_soggetto_inesistente(self):
        from apps.anagrafiche.services.soggetti_service import SoggettiService

        payload = {"dati_societari": {"forma_giuridica_id": self.forma["SRL"]}}
        self._rifiuto(
            lambda: SoggettiService().update_soggetto(_SOGGETTO_INESISTENTE, payload),
            "E_DATI_SOCIETARI_SOGGETTO_NON_TROVATO", None, status=404,
        )

    # 8. L'ORDINE: natura e forma cambiano nella stessa PATCH (SC → SP con la
    #    SNC). Il verbo gira DOPO l'update del soggetto, quindi il guard della
    #    forma confronta la SNC con la natura nuova; al COMMIT il guard
    #    differito vede le due scritture insieme.
    def test_cambio_natura_e_forma_nella_stessa_patch(self):
        from apps.anagrafiche.services.soggetti_service import SoggettiService

        sc = self._pg("SC")
        SoggettiService().update_soggetto(sc, {
            "tipo_soggetto_dettaglio_id": self.tipo["SP"],
            "dati_societari": self._stato(
                sc, forma_giuridica_id=self.forma["SNC"], capitale_sociale=None,
            ),
        })
        with connection.cursor() as cur:
            cur.execute("SET CONSTRAINTS ALL IMMEDIATE")
            cur.execute(
                "SELECT tsd.codice_interno, fg.codice "
                "  FROM anagrafiche.soggetti s "
                "  JOIN config.tipi_soggetto_dettaglio tsd ON tsd.id = s.tipo_soggetto_dettaglio_id "
                "  JOIN anagrafiche.dati_societari ds ON ds.soggetto_id = s.id "
                "  JOIN config.forme_giuridiche fg ON fg.id = ds.forma_giuridica_id "
                " WHERE s.id = %s",
                [sc],
            )
            self.assertEqual(cur.fetchone(), ("SP", "SNC"))

    # 9. Natura cambiata e forma lasciata: lo rifiuta il guard al COMMIT.
    def test_cambio_natura_senza_forma_rifiutato_al_commit(self):
        from apps.anagrafiche.services.soggetti_service import SoggettiService

        sc = self._pg("SC")

        def cambia() -> None:
            SoggettiService().update_soggetto(sc, {"tipo_soggetto_dettaglio_id": self.tipo["SP"]})
            with connection.cursor() as cur:
                cur.execute("SET CONSTRAINTS ALL IMMEDIATE")

        self._rifiuto(cambia, "E_TIPO_SOGGETTO_FORMA_GIURIDICA_NON_AMMESSA", "forma_giuridica_id")

    # 10. Parte C: il lookup delle forme legge il predicato del guard.
    def test_lookup_forme_solo_ammesse_dalla_natura(self):
        from apps.core.db.lookup_repository import LookupRepository

        forme = {f["id"] for f in LookupRepository().list_forme_giuridiche(self.tipo["SC"])}
        self.assertIn(self.forma["SRL"], forme)
        self.assertNotIn(self.forma["DI"], forme)
        with connection.cursor() as cur:
            cur.execute(
                "SELECT bool_and(anagrafiche.fn_forma_giuridica_ammessa("
                "           fg_id, %s, script.fn_giorno_operativo(now())))"
                "  FROM unnest(%s::bigint[]) AS fg_id",
                [self.tipo["SC"], list(forme)],
            )
            self.assertTrue(cur.fetchone()[0])

    # Scopo: i codici dei tipi di titolo che il lookup offre al soggetto.
    @staticmethod
    def _tipi_titolo(soggetto_id: str) -> set[str]:
        from apps.anagrafiche.services.titoli_iva_service import TitoliIvaService

        return {
            t["codice_interno"]
            for t in TitoliIvaService().list_tipi_ammessi(soggetto_id)["results"]
        }

    # 11. Parte D: il lookup dei tipi di titolo segue la natura del soggetto —
    #     la societa' ha l'intento e non l'agevolazione 104, il soggetto che
    #     non esiste non ha niente.
    def test_lookup_tipi_titolo_per_natura_societa(self):
        sc_codici = self._tipi_titolo(self._pg("SC"))
        self.assertIn("INTENTO", sc_codici)
        self.assertNotIn("AGEVOLATA_104", sc_codici)
        self.assertEqual(self._tipi_titolo(_SOGGETTO_INESISTENTE), set())

    # 12. Parte D: il privato ha la sola agevolazione 104 (D-3).
    def test_lookup_tipi_titolo_per_natura_privato(self):
        self.assertEqual(self._tipi_titolo(self._privato()), {"AGEVOLATA_104"})

    # 13. Il REA di un'altra societa' (`uq_ds_prov_cea`): rifiuto di
    #     duplicato col campo `iscrizione_rea` acceso, non un banner muto.
    def test_patch_rea_di_un_altro_soggetto_accende_il_campo(self):
        from apps.anagrafiche.services.soggetti_service import SoggettiService

        primo, secondo = self._pg("SC"), self._pg("SC")
        rea = self._stato(primo)
        self.assertIsNotNone(rea["iscrizione_rea"], "la fixture non ha il REA")
        payload = {"dati_societari": self._stato(
            secondo,
            id_prov_iscri_rea=rea["id_prov_iscri_rea"], iscrizione_rea=rea["iscrizione_rea"],
        )}
        self._rifiuto(
            lambda: SoggettiService().update_soggetto(secondo, payload),
            "E_ANAG_DUPLICATO", "iscrizione_rea", status=409,
        )

    # 14. BB `SQL_TIPI_SOGGETTO_DETTAGLIO` (regola del 2): il lookup generico e
    #     il risolutore per ruolo alimentano lo stesso form e danno la STESSA
    #     riga. Prima divergevano sull'ente: `ENC` (il codice) contro `ENTE`
    #     (l'enum). `natura_soggetto` e' l'enum, ovunque — anche nel dettaglio.
    # ⚠️ Il ruolo e' il cliente: il risolutore pretende il parametro
    #    `DEFAULT_TIPO_SOGGETTO_DETTAGLIO_<ruolo>`, che il seed da' a CL e FO.
    def test_lookup_e_risolutore_leggono_la_stessa_natura(self):
        from apps.anagrafiche.db.soggetti_repository import SoggettiRepository
        from apps.core.db.lookup_repository import LookupRepository

        repo = SoggettiRepository()
        lookup = {t["id"]: t for t in LookupRepository().list_tipi_soggetto_dettaglio()}
        conf = repo.get_config_resolver("CL")
        assert conf is not None
        self.assertTrue(conf["tipi_soggetto_dettaglio"])
        for d in conf["tipi_soggetto_dettaglio"]:
            self.assertEqual(d, lookup[d["id"]], f"tipo {d['id']}")
        with connection.cursor() as cur:
            cur.execute("SELECT id, natura_soggetto::text FROM config.tipi_soggetto")
            natura_di = dict(cur.fetchall())
        for t in lookup.values():
            self.assertEqual(t["natura_soggetto"], natura_di[t["tipo_soggetto_id"]])
        self.assertTrue(set(conf["nature_ammesse"]) <= set(natura_di.values()))
        sc = self._pg("SC")
        dettaglio = repo.get_soggetto(sc)
        assert dettaglio is not None
        self.assertEqual(
            dettaglio["natura_soggetto"],
            lookup[dettaglio["tipo_soggetto_dettaglio_id"]]["natura_soggetto"],
        )

    # 15. Anche in CREAZIONE il REA di un'altra societa' e' il REA, non «CF/PIVA
    #     duplicata»: la creazione scrive due tabelle, e il DB dice quale
    #     vincolo e' violato.
    # ⚠️ Tutte e due le societa' dal service, e NON dalla fixture `_pg`: quella
    #    lascia i vincoli IMMEDIATE, e la seconda creazione cadrebbe sui guard
    #    «obbligatori» (dati societari, contatti, indirizzi) prima del REA.
    def test_creazione_rea_di_un_altro_soggetto_accende_il_campo(self):
        from apps.anagrafiche.services.soggetti_service import SoggettiService

        with connection.cursor() as cur:
            cur.execute("SELECT id FROM config.province ORDER BY id LIMIT 1")
            provincia = cur.fetchone()[0]

        def societa(nome: str) -> dict[str, Any]:
            with connection.cursor() as cur:
                cur.execute("SELECT dbops.fn_pgtap_piva_libera()")
                piva = str(cur.fetchone()[0])
            return {
                "tipo_soggetto_dettaglio_id": self.tipo["SC"],
                "ragione_sociale": nome,
                # Per una societa' il codice fiscale e' la partita IVA.
                "codice_fiscale": piva, "partita_iva": piva,
                "contatto": {
                    "nominativo": nome, "tipo_contatto_id": self.tipo_contatto,
                    "email": "rea.duplicato@test.invalid",
                },
                "dati_societari": {
                    "forma_giuridica_id": self.forma["SRL"],
                    "id_prov_iscri_rea": provincia, "iscrizione_rea": "REA-DUP-1",
                    "capitale_sociale": "10000",
                },
            }

        SoggettiService().create_soggetto(societa("REA primo"))
        secondo = societa("REA secondo")
        self._rifiuto(
            lambda: SoggettiService().create_soggetto(secondo),
            "E_ANAG_DUPLICATO", "iscrizione_rea", status=409,
        )

    # 16. Il default di natura per ruolo e' FACOLTATIVO: un ruolo senza
    #     `DEFAULT_TIPO_SOGGETTO_DETTAGLIO_<ruolo>` ha il risolutore, col
    #     default a None. Fino al 2026-10-11 il risolutore sollevava
    #     `E_ERRORE_PARAMETRI_TABELLA` (RIS_UMANA, EF), e il FE lo ingoiava.
    # ⚠️ Il ruolo si legge dalla configurazione (contratto, non popolazione):
    #    se ogni ruolo avesse il parametro il caso non esisterebbe, e lo si dice.
    def test_risolutore_ruolo_senza_default_dichiarato(self):
        from apps.anagrafiche.db.soggetti_repository import SoggettiRepository

        with connection.cursor() as cur:
            cur.execute(
                "SELECT COALESCE(tr.codice_interno, tr.codice) FROM config.tipi_ruoli tr"
                " WHERE NOT EXISTS (SELECT 1 FROM config.parameters p WHERE p.code ="
                "   'DEFAULT_TIPO_SOGGETTO_DETTAGLIO_' || COALESCE(tr.codice_interno, tr.codice))"
                " ORDER BY tr.id LIMIT 1"
            )
            riga = cur.fetchone()
        if riga is None:
            self.skipTest("ogni ruolo dichiara il suo default: il caso non e' costruibile")
        conf = SoggettiRepository().get_config_resolver(riga[0])
        assert conf is not None
        self.assertIsNone(conf["default_tipo_soggetto_dettaglio_id"])

    # Scopo: un soggetto che nasce dal service vero, col contatto obbligatorio.
    # ⚠️ Dal service e NON dalla fixture `_pg`, per la ragione del test 15.
    def _crea(self, **campi: Any) -> str:
        from apps.anagrafiche.services.soggetti_service import SoggettiService

        creato = SoggettiService().create_soggetto({
            **campi,
            "contatto": {
                "nominativo": "Nascita", "tipo_contatto_id": self.tipo_contatto,
                "email": "dati.nascita@test.invalid",
            },
        })
        return str(creato["id"])

    @staticmethod
    def _libero(funzione: str) -> str:
        with connection.cursor() as cur:
            cur.execute(f"SELECT dbops.{funzione}()")
            return str(cur.fetchone()[0])

    # 17. La data di costituzione si scrive alla NASCITA, col resto della
    #     sezione (brief-db-dati-societari-in-creazione §6): fino al 2026-10-22
    #     la porta la passava al verbo a NULL, e il FE la offriva solo in
    #     modifica.
    def test_creazione_societa_con_data_di_costituzione(self):
        piva = self._libero("fn_pgtap_piva_libera")
        with connection.cursor() as cur:
            cur.execute("SELECT id FROM config.province ORDER BY id LIMIT 1")
            provincia = cur.fetchone()[0]
        sc = self._crea(
            tipo_soggetto_dettaglio_id=self.tipo["SC"], ragione_sociale="Nascita SRL",
            codice_fiscale=piva, partita_iva=piva,
            dati_societari={
                "forma_giuridica_id": self.forma["SRL"], "capitale_sociale": "10000",
                "id_prov_iscri_rea": provincia, "iscrizione_rea": "REA-NASCITA-1",
                "data_costituzione": "2020-03-15",
            },
        )
        ds = self._dati_societari(sc)
        assert ds is not None
        self.assertEqual(
            (ds["forma_giuridica_id"], ds["data_costituzione"]),
            (self.forma["SRL"], "2020-03-15"),
        )

    # 18. La ditta individuale nasce con la sua sezione (§1.1): fino al
    #     2026-10-22 `_create_pf` non la leggeva e la porta delle persone
    #     fisiche non la riceveva — «creato», e la sezione vuota.
    def test_creazione_ditta_individuale_con_la_sezione(self):
        di = self._crea(
            tipo_soggetto_dettaglio_id=self.tipo["DI"], cognome="Nascita", nome="Ditta",
            codice_fiscale=self._libero("fn_pgtap_cf_libero"),
            partita_iva=self._libero("fn_pgtap_piva_libera"),
            dati_societari={
                "forma_giuridica_id": self.forma["DI"], "destinatario_fe": "P",
                "pec_fatturazione": "ditta.nascita@pec.test.invalid",
                "data_costituzione": "2010-11-12",
            },
        )
        ds = self._dati_societari(di)
        assert ds is not None
        self.assertEqual(
            (ds["forma_giuridica_id"], ds["destinatario_fe"], ds["pec_fatturazione"],
             ds["data_costituzione"]),
            (self.forma["DI"], "P", "ditta.nascita@pec.test.invalid", "2010-11-12"),
        )

    # 19. Un privato (policy NONE) con la sezione: la rifiuta il guard della
    #     natura, non sparisce. Senza forma, o parlerebbe prima il guard della
    #     forma (pgTAP `test-dati-societari-alla-nascita-v1`, test 17).
    def test_creazione_privato_con_la_sezione_rifiutata(self):
        cf = self._libero("fn_pgtap_cf_libero")
        self._rifiuto(
            lambda: self._crea(
                tipo_soggetto_dettaglio_id=self.tipo["PR"], cognome="Nascita",
                nome="Privato", sesso="M", codice_fiscale=cf,
                dati_societari={"data_costituzione": "2015-01-01"},
            ),
            "E_DATI_SOCIETARI_TIPO_SOGGETTO_NON_AMMESSO", None,
        )
