# ------------------------------------------------------------
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: La regola ATTIVO sulle FK il cui nome non finisce in `_id`
#        (brief-db-attivo-fk-senza-suffisso-id §6, giro DB del 2026-11-22),
#        dal service vero al DB vero: i due codici arrivano al chiamante col
#        loro nome, e il require col CAMPO, che qui e' una colonna senza `_id`
#        (`causale_magazzino`). E' cio' che il FE lega all'input
#        (`campiErrati.includes(col.name)` nel drawer del pannello).
#
# ⭐ PERCHE' SUL DB VERO. Il `campo` viaggia nel canale `COLUMN`
#    dell'eccezione, e il codice in `CONSTRAINT`: un mock dell'eccezione
#    proverebbe solo che il test sa scrivere un'eccezione. Qui la solleva il
#    trigger generato, e la leggono i punti di traduzione veri.
#
# ⛔ `SET CONSTRAINTS ALL IMMEDIATE`. Il require e' un constraint trigger
#    DIFFERITO al commit, e la transazione del test non arriva mai al commit:
#    senza, il caso 1 sarebbe verde perche' il controllo non scatta. In
#    produzione l'app gira in autocommit (`ATOMIC_REQUESTS` spento), quindi il
#    commit e' quello dell'istruzione, dentro il `try` del service: IMMEDIATE
#    riproduce quel punto.
#
# ⚠️ CASI COSTRUITI in una transazione SEMPRE annullata: le causali il test se
#    le fabbrica, col verbo del pannello (l'app da sola non scrive
#    `magazzino.causali`).
# ------------------------------------------------------------

"""Indice test (opt-in `ZEROERP_TEST_DB_E2E=1`).

1. test_la_figlia_su_un_padre_spento_e_rifiutata_col_campo
     pannello: una causale di trasporto su una causale di magazzino spenta e'
     `E_ATTIVO_PADRE_NON_ATTIVO`, col campo `causale_magazzino`.
2. test_il_padre_in_uso_non_si_spegne
     pannello: la causale di magazzino usata da una causale di trasporto accesa
     e' `E_ATTIVO_BLOCK_CHILDREN_ACTIVE`; spenta la figlia, il padre si spegne.
3. test_il_rifiuto_attraversa_il_traduttore_di_pratiche
     l'editor dei workflow traduce con `_mapped_db_errors`, che riconosce solo
     i codici del suo dominio e rilancia gli altri: il rifiuto vero arriva
     all'envelope col codice e col campo (`fields`), non come `E_DATABASE`.
"""

from __future__ import annotations

import uuid
from unittest import TestCase

from django.db import DatabaseError, connection, transaction

from apps.core.services.error_translator import ErrorTranslator
from apps.core.services.service_errors import ServiceError
from apps.core.tests.db_e2e import apri_operatore_con_aree, apri_transazione_annullata, richiedi_db_provvisto

_PADRE = "magazzino.causali"
_FIGLIA = "config.causali_trasporto"


class AttivoFkSenzaSuffissoDbTests(TestCase):

    @classmethod
    def setUpClass(cls) -> None:
        super().setUpClass()
        richiedi_db_provvisto("dbops.fn_attivo_fk_esclusa(text, text, text)")

    def setUp(self) -> None:
        from apps.core.services.config_crud_service import ConfigCrudService

        apri_transazione_annullata(self)
        with connection.cursor() as cur:
            # ⭐ Un operatore COSTRUITO col livello sulle due aree delle tabelle
            #    (D-AH, 2026-11-27): fino ad allora il primo operatore del DB, che
            #    su dbdev e' SUPER_ADMIN, e il verde dipendeva da lui.
            apri_operatore_con_aree(cur, aree=("config", "magazzino"), motivo="attivo fk senza suffisso")
            cur.execute("SET CONSTRAINTS ALL IMMEDIATE")
        self.svc = ConfigCrudService()

    # Scopo: Esegue `azione` in un savepoint e ne ritorna il ServiceError.
    def _rifiuto(self, azione) -> ServiceError:
        try:
            with transaction.atomic():
                azione()
        except ServiceError as exc:
            return exc
        self.fail("l'operazione doveva essere rifiutata")

    # Scopo: Una causale di magazzino nuova, col suo `codice_interno` (la
    #        colonna che la FK della causale di trasporto referenzia).
    def _causale_magazzino(self) -> dict:
        # ⚠️ `codice_interno` e' facoltativo e non ha default: senza, la
        #    causale non e' referenziabile, e il pannello lo lascia scrivere.
        codice = f"T{uuid.uuid4().hex[:8].upper()}"
        return self.svc.create_record(
            _PADRE,
            {"codice": codice, "codice_interno": codice, "descrizione": "Causale del test", "segno": 1},
        )

    # Scopo: Il messaggio italiano del codice in `config.messaggi_errore`.
    #        ⚠️ Frase chiusa: dei tre codici ATTIVO nessuno ha segnaposti, il
    #        padre e la figlia viaggiano nel contesto e nel bersaglio.
    @staticmethod
    def _messaggio_a_catalogo(codice: str) -> str:
        with connection.cursor() as cur:
            cur.execute(
                "SELECT messaggio FROM config.messaggi_errore WHERE codice = %s AND lingua = 'it'",
                [codice],
            )
            riga = cur.fetchone()
        assert riga is not None, codice
        return str(riga[0])

    def _causale_trasporto(self, causale_magazzino: str) -> dict:
        codice = f"T{uuid.uuid4().hex[:6].upper()}"
        return self.svc.create_record(
            _FIGLIA,
            {"codice": codice, "descrizione": "Trasporto del test", "causale_magazzino": causale_magazzino},
        )

    # 1.
    def test_la_figlia_su_un_padre_spento_e_rifiutata_col_campo(self) -> None:
        padre = self._causale_magazzino()
        self.svc.update_record(_PADRE, padre["id"], {"attivo": False})

        exc = self._rifiuto(lambda: self._causale_trasporto(padre["codice_interno"]))

        self.assertEqual(exc.code, "E_ATTIVO_PADRE_NON_ATTIVO")
        self.assertEqual(exc.message, self._messaggio_a_catalogo("E_ATTIVO_PADRE_NON_ATTIVO"))
        api = ErrorTranslator.to_api_error(exc)
        self.assertEqual(api.fields, ("causale_magazzino",))
        self.assertEqual(ErrorTranslator.get_http_status(api), 409)

    # 2.
    def test_il_padre_in_uso_non_si_spegne(self) -> None:
        padre = self._causale_magazzino()
        figlia = self._causale_trasporto(padre["codice_interno"])

        exc = self._rifiuto(lambda: self.svc.update_record(_PADRE, padre["id"], {"attivo": False}))
        self.assertEqual(exc.code, "E_ATTIVO_BLOCK_CHILDREN_ACTIVE")
        # Il testo e' quello del CATALOGO (letto dal DB, non ricopiato qui),
        # non il ripiego del service («Il record viola un vincolo…»).
        self.assertEqual(exc.message, self._messaggio_a_catalogo("E_ATTIVO_BLOCK_CHILDREN_ACTIVE"))

        # Figli prima, padre poi (api.md §Disattivazione record).
        self.svc.update_record(_FIGLIA, figlia["id"], {"attivo": False})
        self.assertEqual(
            self.svc.update_record(_PADRE, padre["id"], {"attivo": False}),
            {"updated": True},
        )

    # 3.
    def test_il_rifiuto_attraversa_il_traduttore_di_pratiche(self) -> None:
        from apps.pratiche.services.definizioni_service import _mapped_db_errors

        padre = self._causale_magazzino()
        self.svc.update_record(_PADRE, padre["id"], {"attivo": False})

        catturata: Exception | None = None
        try:
            with transaction.atomic(), _mapped_db_errors("test.attivo_fk_senza_suffisso"):
                with connection.cursor() as cur:
                    # La scrittura nuda, come quella di `execute_dynamic_insert`
                    # nel repository delle definizioni: l'errore e' del DB.
                    cur.execute(
                        f"INSERT INTO {_FIGLIA} (codice, descrizione, causale_magazzino) VALUES (%s, %s, %s)",  # tabella costante, valori come parametri
                        [f"T{uuid.uuid4().hex[:6].upper()}", "Trasporto del test", padre["codice_interno"]],
                    )
        except (ServiceError, DatabaseError) as exc:
            catturata = exc
        self.assertIsNotNone(catturata, "la scrittura doveva essere rifiutata")
        assert catturata is not None

        api = ErrorTranslator.to_api_error(catturata)
        self.assertEqual(api.code, "E_ATTIVO_PADRE_NON_ATTIVO")
        self.assertEqual(api.fields, ("causale_magazzino",))
        self.assertEqual(ErrorTranslator.get_http_status(api), 409)
