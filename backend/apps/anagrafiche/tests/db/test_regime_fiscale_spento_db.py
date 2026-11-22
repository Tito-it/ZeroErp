# ------------------------------------------------------------
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Un regime fiscale spento non si assegna (D-6 «a» e D-7 «2» di
#        brief-db-fornitore-doppioni-del-soggetto, changeSet 20261121-10…15),
#        provato sul DATABASE VERO dal lato del BE: che il rifiuto del require
#        ATTIVO attraversi i service del fornitore e dell'emittente senza
#        essere inghiottito o tradotto male, e arrivi all'envelope come 409
#        `E_ATTIVO_PADRE_NON_ATTIVO` col campo `regime_fiscale_rf`, quello che
#        i due drawer accendono (`campiErrati`). La regola in se' la collauda
#        il pgTAP `test-automazione-attivo-inclusioni-v1`; qui si prova il
#        TRASPORTO, che un mock non vede.
# Note: ⚠️ I trigger require sono DEFERRABLE INITIALLY DEFERRED: in una
#       richiesta vera (autocommit, `ATOMIC_REQUESTS` spento) giudicano alla
#       fine dell'istruzione, cioe' dentro la chiamata al repository. La
#       transazione del test non fa mai COMMIT: `SET CONSTRAINTS … IMMEDIATE`
#       sui SOLI due require del regime, prima della chiamata, riproduce quel
#       punto, e non `ALL`: il rifiuto atteso e' quello del regime, non un
#       altro guard differito. I fornitori nascono coi loro indirizzi
#       obbligatori (quelli che il picker segna, come in
#       `test_clienti_fornitori_scrittura_db`), con `SET CONSTRAINTS ALL
#       DEFERRED` subito prima della madre: il builder del soggetto richiude la
#       finestra differita all'uscita. I trigger si cercano per funzione e argomenti, non
#       per nome (i nomi lunghi sono hashati).
#       ⚠️ I due regimi li COSTRUISCE il test (RF93 acceso, RF94 spento),
#       in transazione ANNULLATA: spegnere un regime del catalogo dipenderebbe
#       da chi lo usa oggi (regola zero). L'app il catalogo lo legge e basta
#       (D-8, `20261121-16`): i regimi nascono dalla porta di prova
#       `dbops.fn_crea_regime_fiscale_di_prova` (D-9, `20261121-17`), che si
#       apre solo in `SVILUPPO`, scrive solo righe nuove col segno
#       `meta.di_prova` e non spegne. Il regime spento quindi NASCE spento, e
#       lo spegnimento di un regime in uso resta al pgTAP
#       `test-automazione-attivo-inclusioni-v1`, come owner.
#       Opt-in `ZEROERP_TEST_DB_E2E=1`.
# ------------------------------------------------------------
"""
Indice test eseguiti (opt-in `ZEROERP_TEST_DB_E2E=1`):
1) RegimeFiscaleSpentoDbTests.test_patch_fornitore_regime_spento_409_sul_campo
2) RegimeFiscaleSpentoDbTests.test_crea_fornitore_regime_spento_409_sul_campo
3) RegimeFiscaleSpentoDbTests.test_riaccendere_fornitore_col_regime_spento_409_sul_campo
4) RegimeFiscaleSpentoDbTests.test_patch_emittente_regime_spento_409_sul_campo
5) RegimeFiscaleSpentoDbTests.test_regime_acceso_si_assegna
6) RegimeFiscaleSpentoDbTests.test_patch_fornitore_regime_fuori_catalogo_400_sul_campo
7) RegimeFiscaleSpentoDbTests.test_crea_fornitore_regime_fuori_catalogo_400_sul_campo
8) RegimeFiscaleSpentoDbTests.test_dettagli_portano_il_codice_a_video_del_regime
"""
from __future__ import annotations

import unittest

from django.db import DatabaseError, connection, transaction

from apps.core.services.service_errors import ServiceError
from apps.core.tests.db_e2e import (
    apri_contesto_operatore,
    apri_transazione_annullata,
    richiedi_db_provvisto,
)

_ACCESO = "RF93"
_SPENTO = "RF94"
_CAMPO = "regime_fiscale_rf"
# Un codice che il catalogo non ha: lo stesso di `test_regime_fiscale_conferma_db`.
_FUORI_CATALOGO = "RF99"


class RegimeFiscaleSpentoDbTests(unittest.TestCase):

    def setUp(self):
        apri_transazione_annullata(self)
        richiedi_db_provvisto()
        with connection.cursor() as cur:
            apri_contesto_operatore(cur)
            for codice_interno, descrizione, attivo in (
                (_ACCESO, "Regime e2e acceso", True),
                (_SPENTO, "Regime e2e spento", False),
            ):
                cur.execute(
                    "SELECT dbops.fn_crea_regime_fiscale_di_prova(%s, %s, %s, %s)",
                    [codice_interno, f"E2E-{codice_interno}", descrizione, attivo],
                )

    def _fornitori(self):
        from apps.anagrafiche.services.fornitori_service import FornitoriService
        return FornitoriService()

    def _emittenti(self):
        from apps.anagrafiche.services.emittenti_fiscali_service import (
            EmittentiFiscaliService,
        )
        return EmittentiFiscaliService()

    def _soggetto(self, nome: str) -> str:
        with connection.cursor() as cur:
            cur.execute("SELECT dbops.fn_pgtap_crea_soggetto_pg(%s)", [nome])
            return str(cur.fetchone()[0])

    # Scopo: Gli indirizzi obbligatori del ruolo FO per il soggetto, in forma
    #        libera su uno stato senza catalogo dei comuni.
    def _indirizzi(self, soggetto_id: str) -> list[dict]:
        from apps.core.db.lookup_repository import LookupRepository

        with connection.cursor() as cur:
            cur.execute(
                "SELECT id FROM config.stati WHERE NOT catalogo_comuni_completo ORDER BY id LIMIT 1"
            )
            stato = cur.fetchone()
        if stato is None:
            self.skipTest("Nessuno stato senza catalogo dei comuni.")
        return [
            {
                "tipo_indirizzo_codice_interno": r["codice_interno"],
                "indirizzo_libero": "Via regime 1", "stato_id": int(stato[0]),
                "locality": "Prova", "postal_code": "RF1",
            }
            for r in LookupRepository().list_tipi_indirizzo_proponibili_tipo_ruolo("FO", soggetto_id)
            if r["obbligatorio"]
        ]

    # Scopo: Il payload del drawer, e la finestra differita aperta DOPO il
    #        builder del soggetto, come la apre la saga del fornitore.
    def _payload_fornitore(self, nome: str) -> dict:
        soggetto_id = self._soggetto(nome)
        payload = {"soggetto_id": soggetto_id, "indirizzi": self._indirizzi(soggetto_id)}
        with connection.cursor() as cur:
            cur.execute("SET CONSTRAINTS ALL DEFERRED")
        return payload

    def _fornitore(self, regime: str | None = _ACCESO) -> int:
        payload = self._payload_fornitore("Fornitore e2e regime spento")
        if regime is not None:
            payload[_CAMPO] = regime
        fornitore_id = int(self._fornitori().crea_fornitore(payload)["id"])
        # Il COMMIT della richiesta vera: gli eventi del regime in coda si
        # giudicano ORA, sullo stato di adesso. Lasciati in coda, li
        # giudicherebbe il primo `IMMEDIATE` dopo, sul regime ormai spento.
        self._require_regime_immediati()
        return fornitore_id

    def _regime_di(self, tabella: str, riga_id: int) -> str | None:
        with connection.cursor() as cur:
            cur.execute(
                f"SELECT regime_fiscale_rf FROM anagrafiche.{tabella} WHERE id = %s",
                [riga_id],
            )
            return cur.fetchone()[0]

    # Scopo: I due require del regime giudicano subito, come in autocommit.
    #        Se non sono due, il test misurerebbe il vuoto: e' rosso.
    def _require_regime_immediati(self) -> None:
        with connection.cursor() as cur:
            cur.execute(
                "SELECT quote_ident(n.nspname) || '.' || quote_ident(t.tgname)"
                "  FROM pg_trigger t"
                "  JOIN pg_class c ON c.oid = t.tgrelid"
                "  JOIN pg_namespace n ON n.oid = c.relnamespace"
                "  JOIN pg_proc p ON p.oid = t.tgfoid"
                " WHERE p.proname = 'trgfn_child_requires_active_parent'"
                "   AND position('\\000regimi_fiscali\\000' IN encode(t.tgargs, 'escape')) > 0"
                "   AND position('\\000regime_fiscale_rf\\000' IN encode(t.tgargs, 'escape')) > 0"
                " ORDER BY 1"
            )
            nomi = [r[0] for r in cur.fetchall()]
            self.assertEqual(2, len(nomi), f"require del regime attesi su fornitori ed emittenti: {nomi}")
            cur.execute(f"SET CONSTRAINTS {', '.join(nomi)} IMMEDIATE")

    # Scopo: La chiamata in un savepoint, coi require del regime immediati.
    #        Ritorna l'errore come lo vede il client, e il suo status HTTP.
    def _rifiuto(self, chiamata):
        from apps.core.services.error_translator import ErrorTranslator

        self._require_regime_immediati()
        with self.assertRaises(DatabaseError) as ctx, transaction.atomic():
            chiamata()
        errore = ErrorTranslator.to_api_error(ctx.exception)
        return errore, ErrorTranslator.get_http_status(errore)

    def _assert_rifiuto_sul_campo(self, chiamata) -> None:
        errore, status = self._rifiuto(chiamata)
        self.assertEqual("E_ATTIVO_PADRE_NON_ATTIVO", errore.code)
        self.assertEqual(409, status)
        self.assertEqual((_CAMPO,), errore.fields)

    # 1. PATCH del drawer: passa da `regime_nel_catalogo`, che deve
    #    rilanciare l'errore (non e' la FK) e non tradurlo in «fuori catalogo».
    def test_patch_fornitore_regime_spento_409_sul_campo(self):
        fornitore_id = self._fornitore()
        self._assert_rifiuto_sul_campo(
            lambda: self._fornitori().update_fornitore(fornitore_id, {_CAMPO: _SPENTO}),
        )
        self.assertEqual(_ACCESO, self._regime_di("fornitori", fornitore_id))

    # 2. Creazione: la madre `fn_crea_fornitore` attraversa anche
    #    `create_with_constraint_mapping`, che non deve mascherarlo.
    def test_crea_fornitore_regime_spento_409_sul_campo(self):
        payload = self._payload_fornitore("Fornitore e2e nasce col regime spento")
        payload[_CAMPO] = _SPENTO
        self._assert_rifiuto_sul_campo(lambda: self._fornitori().crea_fornitore(payload))

    # 3. Il caso che a video si incontra davvero (la tendina propone i soli
    #    accesi): un fornitore spento col regime spento, e riaccenderlo e'
    #    rifiutato sul campo del regime. Il regime non si spegne qui (l'app
    #    non lo puo'): e' il fornitore spento a prendere il regime gia' spento,
    #    che un figlio spento puo' citare.
    def test_riaccendere_fornitore_col_regime_spento_409_sul_campo(self):
        fornitore_id = self._fornitore()
        self._fornitori().update_fornitore(fornitore_id, {"attivo": False})
        self._require_regime_immediati()
        self._fornitori().update_fornitore(fornitore_id, {_CAMPO: _SPENTO})
        self.assertEqual(_SPENTO, self._regime_di("fornitori", fornitore_id))
        self._assert_rifiuto_sul_campo(
            lambda: self._fornitori().update_fornitore(fornitore_id, {"attivo": True}),
        )

    # 4. L'emittente, l'altro ruolo che referenzia il catalogo.
    def test_patch_emittente_regime_spento_409_sul_campo(self):
        with connection.cursor() as cur:
            cur.execute("SELECT emittente_fiscale_id FROM dbops.fn_pgtap_crea_emittente()")
            emittente_id = int(cur.fetchone()[0])
        self._assert_rifiuto_sul_campo(
            lambda: self._emittenti().update_emittente(emittente_id, {_CAMPO: _SPENTO}),
        )

    # 5. Il controcampione: col giudizio immediato un regime acceso si assegna,
    #    quindi i rifiuti sopra sono dello stato del regime, non del percorso.
    def test_regime_acceso_si_assegna(self):
        fornitore_id = self._fornitore(regime=None)
        self._require_regime_immediati()
        self._fornitori().update_fornitore(fornitore_id, {_CAMPO: _ACCESO})
        self.assertEqual(_ACCESO, self._regime_di("fornitori", fornitore_id))

    # 6. Il codice fuori catalogo e' la FK `fk_fornitori_regimi_fiscali`, che il
    #    service nomina per testo (BB `regime_nel_catalogo`): solo il DB vero
    #    prova che il nome esca da libpq com'e' scritto. Gemello del caso 6 di
    #    `test_regime_fiscale_conferma_db` per l'emittente. Savepoint: la FK
    #    abortisce la sola sotto-transazione.
    def test_patch_fornitore_regime_fuori_catalogo_400_sul_campo(self):
        fornitore_id = self._fornitore()
        with self.assertRaises(ServiceError) as ctx, transaction.atomic():
            self._fornitori().update_fornitore(fornitore_id, {_CAMPO: _FUORI_CATALOGO})
        self.assertEqual("E_ANAG_VALIDAZIONE", ctx.exception.code)
        self.assertEqual(_CAMPO, ctx.exception.context.get("field"))
        self.assertEqual(_ACCESO, self._regime_di("fornitori", fornitore_id))

    # 7. Lo stesso in creazione, dove la FK attraversa la madre e
    #    `create_with_constraint_mapping`, che deve rilanciarla e non mascherarla.
    def test_crea_fornitore_regime_fuori_catalogo_400_sul_campo(self):
        payload = self._payload_fornitore("Fornitore e2e regime fuori catalogo")
        payload[_CAMPO] = _FUORI_CATALOGO
        with self.assertRaises(ServiceError) as ctx, transaction.atomic():
            self._fornitori().crea_fornitore(payload)
        self.assertEqual("E_ANAG_VALIDAZIONE", ctx.exception.code)
        self.assertEqual(_CAMPO, ctx.exception.context.get("field"))

    # 8. I due dettagli portano `regime_fiscale_codice`, il codice A VIDEO del
    #    catalogo, che la combo dei drawer mostra (BB FE `voceRegimeFiscale`).
    #    Il regime di prova ha `codice` diverso da `codice_interno`: nel seed di
    #    oggi coincidono, e una lettura che li scambiasse resterebbe verde.
    def test_dettagli_portano_il_codice_a_video_del_regime(self):
        fornitore_id = self._fornitore()
        dettaglio = self._fornitori().get_fornitore(fornitore_id)
        self.assertEqual(_ACCESO, dettaglio["regime_fiscale_rf"])
        self.assertEqual("E2E-RF93", dettaglio["regime_fiscale_codice"])

        with connection.cursor() as cur:
            cur.execute("SELECT emittente_fiscale_id FROM dbops.fn_pgtap_crea_emittente()")
            emittente_id = int(cur.fetchone()[0])
        self._require_regime_immediati()
        self._emittenti().update_emittente(emittente_id, {_CAMPO: _ACCESO})
        dettaglio = self._emittenti().get_emittente(emittente_id)
        self.assertEqual(_ACCESO, dettaglio["regime_fiscale_rf"])
        self.assertEqual("E2E-RF93", dettaglio["regime_fiscale_codice"])
