# ------------------------------------------------------------
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: IL BERSAGLIO dell'errore, dal campo strutturato `DATATYPE`
#        dell'eccezione DB fino all'envelope che il client legge.
#        Risposta al brief `brief-db-bersaglio-errore.md` §7-bis (B1..B4).
# ------------------------------------------------------------

"""Indice test previsti.

La LETTURA del canale (`structured_db_error_target`):
 1) test_un_bersaglio
 2) test_due_bersagli_in_ordine
 3) test_canale_vuoto_nessun_bersaglio       (il caso normale)
 4) test_canale_assente_nessun_bersaglio
 5) test_sqlstate_non_p0001_ignora_il_canale (PostgreSQL riempie DATATYPE da se')
 6) test_elemento_storto_scartato_gli_altri_restano
 7) test_tetto_di_cinque
 8) test_id_uuid_ammesso

Il TRASPORTO — un test per ciascuno dei CINQUE punti di traduzione, che e'
il difetto che il piano ha trovato (il quinto e' emerso il 2026-08-24, col
roll-out del terzo scaglione: era rimasto indietro):
 9) test_punto_1_database_error_nudo_arriva_nellenvelope
10) test_punto_2_translate_db_errors_non_perde_il_bersaglio
11) test_punto_3_raise_from_database_error_non_perde_il_bersaglio
12) test_punto_4_service_error_porta_il_bersaglio_nellenvelope
13) test_punto_5_pratiche_non_perde_il_bersaglio

Le REGOLE dell'envelope:
14) test_envelope_parla_inglese                 (`type`/`id`, non `tipo`/`id`)
15) test_tupla_vuota_non_finisce_nellenvelope   (una chiave vuota non dice niente)
16) test_su_un_tecnico_il_bersaglio_non_esce    (Q-E, dal lato che consegna)
17) test_su_un_rimediabile_il_bersaglio_esce    (il verso opposto del 16)
18) test_il_campo_da_correggere_viaggia_con_lui (il difetto gia' vivo, sanato)
19) test_il_campo_esplicito_vince_su_quello_derivato

End-to-end su DB reale (OPT-IN `ZEROERP_TEST_DB_E2E=1`):
20) test_e2e_il_canale_porta_il_bersaglio
"""

from __future__ import annotations

import json
from unittest import TestCase

from django.db import DatabaseError

from apps.core.api.error_responses import exception_to_error_response
from apps.core.services.db_error_fields import (
    Bersaglio,
    structured_db_error_target,
)
from apps.core.services.error_manager import ErrorManager
from apps.core.services.error_translator import ErrorTranslator
from apps.core.services.payload_helpers import translate_db_errors
from apps.core.services.service_errors import ServiceError
from apps.core.tests.db_e2e import richiedi_db_provvisto
from apps.core.tests.db_error_fakes import make_db_error


# Scopo: L'errore pilota del cantiere, nella forma in cui il database lo
#        solleva davvero — codice sul canale CONSTRAINT, campo su COLUMN,
#        bersaglio su DATATYPE. Un finto che non li porta tutti e tre fa
#        passare il test per la ragione sbagliata.
#
#        ⚠️ FORMA AGGIORNATA AL `T-3b` (changeSet `20260824-13`, 2026-08-24):
#        la frase non porta piu' nessun id — porta il CONTEGGIO dei bloccanti —
#        e il bersaglio ne ha DUE, nell'ordine che il database scrive: prima il
#        documento DA NUMERARE (835, quello su cui l'errore e' successo), poi i
#        padri bloccanti visibili (820). ⛔ Un finto a un bersaglio solo
#        riprodurrebbe una forma che il database non solleva piu', e i test di
#        trasporto smetterebbero di provare che il SECONDO elemento arriva.
def _errore_pilota(
    *, bersaglio: str | None = "FATTURA:835,FATTURA:820"
) -> DatabaseError:
    return make_db_error(
        "Non si puo' numerare il documento: rettifica righe di altri documenti"
        " che non risultano ancora numerati. Documenti da numerare prima: 1.",
        codice="E_FATTURA_RETTIFICATA_SENZA_NUMERO",
        campo="numero",
        hint="Numerare prima i documenti che questo rettifica, poi ripetere.",
        bersaglio=bersaglio,
    )


class BersaglioLetturaTest(TestCase):
    """Il canale `DATATYPE` letto come il database lo scrive."""

    # Scopo: Verifica il caso `test_un_bersaglio`.
    def test_un_bersaglio(self):
        exc = make_db_error("x", codice="E_X", bersaglio="FATTURA:820")
        self.assertEqual(
            structured_db_error_target(exc), (Bersaglio(tipo="FATTURA", id="820"),)
        )

    # Scopo: Verifica il caso `test_due_bersagli_in_ordine`.
    #        L'ordine e' quello che il database ha scritto: e' l'ordine in cui
    #        il frontend disegnera' i pulsanti.
    def test_due_bersagli_in_ordine(self):
        exc = make_db_error("x", codice="E_X", bersaglio="FATTURA:835,FATTURA:820")
        self.assertEqual(
            structured_db_error_target(exc),
            (Bersaglio(tipo="FATTURA", id="835"), Bersaglio(tipo="FATTURA", id="820")),
        )

    # Scopo: ⭐ IL CASO NORMALE, e non e' un difetto. La stragrande maggioranza
    #        degli errori un bersaglio non ce l'ha: il canale esce come stringa
    #        VUOTA (non None), esattamente come gia' succede per il codice e per
    #        il campo quando nascono da un'espressione NULL.
    def test_canale_vuoto_nessun_bersaglio(self):
        self.assertEqual(structured_db_error_target(_errore_pilota(bersaglio="")), ())

    # Scopo: Verifica il caso `test_canale_assente_nessun_bersaglio`.
    def test_canale_assente_nessun_bersaglio(self):
        self.assertEqual(structured_db_error_target(_errore_pilota(bersaglio=None)), ())
        self.assertEqual(structured_db_error_target(ValueError("niente")), ())

    # Scopo: ⛔ IL GUARD CHE SERVE, ed e' l'asimmetria da capire. Su `COLUMN` il
    #        guard sullo SQLSTATE non c'e' apposta (una colonna e' sempre una
    #        colonna); su `DATATYPE` serve, perche' fuori da `P0001` quel campo
    #        lo riempie PostgreSQL da se': su un `22P02` contiene il nome di un
    #        TIPO PostgreSQL. Senza questo guard si manderebbe l'operatore ad
    #        «aprire un integer».
    def test_sqlstate_non_p0001_ignora_il_canale(self):
        exc = make_db_error(
            'invalid input syntax for type integer: "abc"',
            sqlstate="22P02",
            bersaglio="integer",
        )
        self.assertEqual(structured_db_error_target(exc), ())

    # Scopo: ⚠️ Un elemento storto NON fa perdere gli altri. E' la stessa
    #        disciplina della meta' che scrive: la funzione che serve a
    #        RIPORTARE un errore non puo' essere quella che lo distrugge.
    def test_elemento_storto_scartato_gli_altri_restano(self):
        casi = {
            "tipo minuscolo": "fattura:820,FATTURA:835",
            "senza separatore": "FATTURA,FATTURA:835",
            "id con spazi": "FATTURA:8 20,FATTURA:835",
            "id vuoto": "FATTURA:,FATTURA:835",
            # ⚠️ La regex del database ammetterebbe un `-` nudo: qui no, o si
            #    offrirebbe un pulsante «Apri Fattura -» che apre il vuoto.
            "id senza cifre": "FATTURA:-,FATTURA:835",
        }
        for nome, canale in casi.items():
            with self.subTest(nome=nome):
                exc = make_db_error("x", codice="E_X", bersaglio=canale)
                self.assertEqual(
                    structured_db_error_target(exc),
                    (Bersaglio(tipo="FATTURA", id="835"),),
                )

    # Scopo: ⛔ Il tetto e' CINQUE, ed e' lo stesso numero scritto dentro
    #        `script.fn_log_and_raise_error`: oltre, il frontend non disegna
    #        piu' un gesto ma un elenco.
    def test_tetto_di_cinque(self):
        canale = ",".join(f"FATTURA:{n}" for n in range(1, 9))
        exc = make_db_error("x", codice="E_X", bersaglio=canale)
        self.assertEqual(len(structured_db_error_target(exc)), 5)

    # Scopo: ⚠️ L'identificativo non e' sempre un intero: `config.tipi_entita`
    #        dichiara `key_selector` = `id` | `uid`, e `anagrafiche.soggetti.id`
    #        e' un uuid. Chi legge non deve sapere quale dei due sia — deve solo
    #        non far rimbalzare testo arbitrario al client.
    def test_id_uuid_ammesso(self):
        uid = "0f8c1d42-9a3b-4c11-8e77-2b6d5a4c9e01"
        exc = make_db_error("x", codice="E_X", bersaglio=f"PREVENTIVO:{uid}")
        self.assertEqual(
            structured_db_error_target(exc), (Bersaglio(tipo="PREVENTIVO", id=uid),)
        )


class BersaglioTrasportoTest(TestCase):
    """⭐ I CINQUE PUNTI DI TRADUZIONE, uno per test.

    E' il difetto che il piano ha trovato misurando (2026-08-24): i punti in cui
    un `DatabaseError` diventa un `ServiceError` sono CINQUE, e quattro su
    cinque buttavano via la diagnostica strutturata prima dell'envelope.

    ⚠️ Il quinto (`pratiche`) e' emerso DOPO gli altri, col roll-out del terzo
    scaglione — ed e' esattamente perche' c'e' un test per punto: il prossimo
    che si aggiungesse senza il suo test tornerebbe a perdere il bersaglio in
    silenzio, che e' il modo in cui questo difetto e' nato.
    """

    # Scopo: Punto 1 — il `DatabaseError` che arriva NUDO al middleware.
    #        E' l'unico che gia' funzionava, e proprio per questo e' l'unico che
    #        non dimostrava niente sugli altri quattro.
    def test_punto_1_database_error_nudo_arriva_nellenvelope(self):
        errore = ErrorTranslator.to_api_error(_errore_pilota())
        self.assertEqual(
            errore.targets,
            (Bersaglio(tipo="FATTURA", id="835"), Bersaglio(tipo="FATTURA", id="820")),
        )

    # Scopo: Punto 2 — `translate_db_errors`, 46 punti di chiamata nei domini.
    #        ⚠️ Prima del 2026-08-24 questo trasportava il solo `hint`.
    def test_punto_2_translate_db_errors_non_perde_il_bersaglio(self):
        with self.assertRaises(ServiceError) as ctx:
            with translate_db_errors(
                context={"op": "test.numera"},
                fallback_code="E_TEST",
                fallback_message="fallita",
            ):
                raise _errore_pilota()
        errore = ErrorTranslator.to_api_error(ctx.exception)
        self.assertEqual(errore.code, "E_FATTURA_RETTIFICATA_SENZA_NUMERO")
        self.assertEqual(
            errore.targets,
            (Bersaglio(tipo="FATTURA", id="835"), Bersaglio(tipo="FATTURA", id="820")),
        )

    # Scopo: Punto 3 — `raise_from_database_error`, 9 punti di chiamata.
    #        ⚠️ Prima del 2026-08-24 questo non trasportava nulla: ne' `hint`,
    #        ne' il campo, ne' il bersaglio.
    def test_punto_3_raise_from_database_error_non_perde_il_bersaglio(self):
        with self.assertRaises(ServiceError) as ctx:
            ErrorManager.raise_from_database_error(
                _errore_pilota(),
                known_markers=(("E_FATTURA_RETTIFICATA_SENZA_NUMERO", ()),),
                fallback_code="E_TEST",
                message="non numerabile",
                log_to_db=False,
            )
        errore = ErrorTranslator.to_api_error(ctx.exception)
        self.assertEqual(
            errore.targets,
            (Bersaglio(tipo="FATTURA", id="835"), Bersaglio(tipo="FATTURA", id="820")),
        )
        # ⭐ E con lui la SOLUZIONE a catalogo, che da questa strada non era mai
        #    uscita: dice all'operatore cosa fare, ed e' meta' del gesto.
        self.assertIn("Numerare prima", errore.hint or "")

    # Scopo: Punto 5 — `pratiche._raise_known_db_error`, **12 punti di chiamata**.
    #        ⚠️ Era rimasto indietro rispetto agli altri quattro, ed e' quello che
    #        porta il TERZO SCAGLIONE del roll-out (`E_FLUSSI_*`,
    #        `E_DEFINIZIONE_BOZZA_ESISTENTE`): senza, il caso che il brief chiama
    #        «il piu' netto dell'intero roll-out» sarebbe arrivato senza gesto.
    def test_punto_5_pratiche_non_perde_il_bersaglio(self):
        from apps.pratiche.services.pratiche_service import _raise_known_db_error

        exc = make_db_error(
            "Esiste gia' una bozza di edizione workflow per lo scope"
            " (tipo prestazione 12, emittente 32).",
            codice="E_DEFINIZIONE_BOZZA_ESISTENTE",
            hint="Aprire la bozza esistente e completarla, oppure eliminarla.",
            bersaglio="DEFINIZIONE_WORKFLOW:77",
        )
        with self.assertRaises(ServiceError) as ctx:
            _raise_known_db_error(exc, function_name="test")
        errore = ErrorTranslator.to_api_error(ctx.exception)
        self.assertEqual(errore.code, "E_DEFINIZIONE_BOZZA_ESISTENTE")
        self.assertEqual(
            errore.targets, (Bersaglio(tipo="DEFINIZIONE_WORKFLOW", id="77"),)
        )

    # Scopo: Punto 4 — il `ServiceError` costruito a mano dai service (e dal
    #        giro per-fattura della pipeline, che e' la strada del PILOTA).
    def test_punto_4_service_error_porta_il_bersaglio_nellenvelope(self):
        exc = ServiceError(
            code="E_FATTURA_RETTIFICATA_SENZA_NUMERO",
            message="Non si puo' numerare il documento: rettifica righe di"
            " altri documenti che non risultano ancora numerati.",
            targets=(
                Bersaglio(tipo="FATTURA", id="835"),
                Bersaglio(tipo="FATTURA", id="820"),
            ),
        )
        errore = ErrorTranslator.to_api_error(exc)
        self.assertEqual(
            errore.targets,
            (Bersaglio(tipo="FATTURA", id="835"), Bersaglio(tipo="FATTURA", id="820")),
        )


class BersaglioEnvelopeTest(TestCase):
    """Le regole di cio' che esce dal confine."""

    # Scopo: ⚠️ L'envelope parla INGLESE — `type`/`id`. La chiave del `context`
    #        del database si chiama `bersaglio` per una collisione che
    #        nell'envelope non esiste, e la traduzione avviene in UN posto solo
    #        (`Bersaglio.to_envelope`).
    def test_envelope_parla_inglese(self):
        risposta = exception_to_error_response(_errore_pilota())
        payload = json.loads(risposta.content)
        self.assertEqual(
            payload["error"]["targets"],
            [{"type": "FATTURA", "id": "835"}, {"type": "FATTURA", "id": "820"}],
        )

    # Scopo: ⚠️ Una tupla VUOTA non deve diventare `"targets": []`. Una chiave
    #        presente e vuota non dice «nessun bersaglio»: dice «guardami», e
    #        chi la riceve deve interrogarla prima di usarla. L'assenza si
    #        esprime togliendo la chiave — stessa disciplina del `meta` che
    #        persiste l'errore e del `CASE` che il team DB ha scritto nel pilota.
    def test_tupla_vuota_non_finisce_nellenvelope(self):
        exc = ServiceError(code="E_X", message="x", targets=())
        payload = json.loads(exception_to_error_response(exc).content)
        self.assertNotIn("targets", payload["error"])

    # Scopo: ⛔ Q-E letta dal lato che consegna: su un errore TECNICO il
    #        bersaglio non esce. Su un 500 l'operatore non ha niente da fare,
    #        quindi non c'e' nessun gesto da offrirgli — ed e' la stessa logica
    #        con cui `_sanitize_public_detail` gia' nasconde il dettaglio.
    #        ⚠️ Il database non ce lo mette; questo e' il punto in cui si decide
    #        cosa vede il client, e una regola presidiata da una parte sola e'
    #        presidiata a meta'.
    def test_su_un_tecnico_il_bersaglio_non_esce(self):
        # ⚠️ DUE CODICI, e servono entrambi perche' le due misure del guard non
        #    si contengono: `E_ALLEGATO_INSERT` e' di CLASSE `TECNICO` (500) —
        #    e' il caso della regola Q-E, 79 codici; `E_DATABASE` invece e' di
        #    classe `DATO_ERRATO` (400) e viene preso solo da
        #    `is_technical_code`. Un test su uno solo dei due lascerebbe passare
        #    meta' del difetto — ed e' esattamente com'era scritto prima.
        for codice in ("E_ALLEGATO_INSERT", "E_DATABASE"):
            with self.subTest(codice=codice):
                exc = ServiceError(
                    code=codice,
                    message="rotto",
                    targets=(Bersaglio(tipo="FATTURA", id="820"),),
                )
                self.assertIsNone(ErrorTranslator.to_api_error(exc).targets)

    # Scopo: ⚠️ Il verso opposto, o il test sopra passerebbe anche se il
    #        bersaglio non uscisse MAI. Su un rimediabile (409) deve uscire.
    def test_su_un_rimediabile_il_bersaglio_esce(self):
        exc = ServiceError(
            code="E_FATTURA_RETTIFICATA_SENZA_NUMERO",
            message="x",
            targets=(Bersaglio(tipo="FATTURA", id="820"),),
        )
        self.assertEqual(
            ErrorTranslator.to_api_error(exc).targets,
            (Bersaglio(tipo="FATTURA", id="820"),),
        )

    # Scopo: ⭐ IL DIFETTO GIA' VIVO, sanato dallo stesso lavoro. Il canale
    #        `COLUMN` viaggia dall'08/08 ed e' valorizzato da quasi tutti i punti
    #        di sollevamento del database — ma `fields` arrivava all'envelope
    #        SOLO dalla strada del `DatabaseError` nudo. Su un errore tradotto da
    #        un service i 136 binding di `campiErrati` non si illuminavano mai.
    def test_il_campo_da_correggere_viaggia_con_lui(self):
        with self.assertRaises(ServiceError) as ctx:
            with translate_db_errors(
                context={"op": "test.numera"},
                fallback_code="E_TEST",
                fallback_message="fallita",
            ):
                raise _errore_pilota()
        self.assertEqual(ErrorTranslator.to_api_error(ctx.exception).fields, ("numero",))

    # Scopo: ⚠️ Il `context={"field": ...}` scritto a mano dal service VINCE sul
    #        campo derivato dal database: e' l'esplicito del chiamante contro un
    #        ripiego, la stessa precedenza che il DB da' a `campo` su `parametro`.
    def test_il_campo_esplicito_vince_su_quello_derivato(self):
        exc = ServiceError(
            code="E_X",
            message="x",
            context={"field": "scelto_dal_service"},
            fields=("derivato_dal_db",),
        )
        self.assertEqual(
            ErrorTranslator.to_api_error(exc).fields, ("scelto_dal_service",)
        )


class BersaglioE2ETest(TestCase):
    """Il canale contro la funzione VERA. Opt-in: `ZEROERP_TEST_DB_E2E=1`.

    ⚠️ Un finto puo' sbagliare forma e passare lo stesso; qui a scrivere il
    canale e' `script.fn_log_and_raise_error`, cioe' la meta' che il backend non
    controlla. E' l'unico test che dimostra che le due meta' si parlano.
    """

    # Scopo: Salta se il DB non e' provvisto dallo schema Liquibase.
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        richiedi_db_provvisto()

    # Scopo: Verifica il caso `test_e2e_il_canale_porta_il_bersaglio`.
    def test_e2e_il_canale_porta_il_bersaglio(self):
        from django.db import connection

        with self.assertRaises(DatabaseError) as ctx:
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    SELECT script.fn_log_and_raise_error(
                        'test', 'test_bersaglio_e2e',
                        'E_FATTURA_RETTIFICATA_SENZA_NUMERO',
                        jsonb_build_object(
                            'campo', 'numero',
                            'bersaglio', jsonb_build_array(
                                jsonb_build_object('tipo', 'FATTURA', 'id', '835'),
                                jsonb_build_object('tipo', 'FATTURA', 'id', '820'))),
                        NULL::uuid, '835', '820')
                    """
                )
        errore = ErrorTranslator.to_api_error(ctx.exception)
        self.assertEqual(errore.code, "E_FATTURA_RETTIFICATA_SENZA_NUMERO")
        self.assertEqual(
            errore.targets,
            (Bersaglio(tipo="FATTURA", id="835"), Bersaglio(tipo="FATTURA", id="820")),
        )
        # I tre canali insieme: il codice, il campo, il bersaglio.
        self.assertEqual(errore.fields, ("numero",))
