# ------------------------------------------------------------
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: `create_with_constraint_mapping` dopo l'unificazione del 2026-08-08.
#
#        PERCHE' ESISTE, ED E' LA PARTE UTILE. Questa funzione e
#        `map_integrity_error` facevano lo stesso riconoscimento — «quale
#        vincolo DB ha protestato?» — in due copie separate. **E le due copie
#        non erano identiche**: qui il match era un `in` nudo, quindi `uq_foo`
#        matchava anche `uq_foo_bar` e a decidere quale voce vincesse era
#        l'ordine del dizionario. L'altra copia quel difetto l'aveva gia'
#        corretto con la word boundary, ma nessuno poteva accorgersi che questa
#        era rimasta indietro: non c'era niente che legasse le due.
#
#        Ora il riconoscimento e' uno solo (`vincolo_violato`). Questi test
#        tengono ferme le due cose che l'unificazione doveva dare — la word
#        boundary e il campo — e la sola che NON doveva toccare: la politica di
#        ripiego, che qui e' RILANCIARE e non mascherare.
#
#        Gira SENZA database.
# ------------------------------------------------------------

"""Indice test previsti.

 1) test_il_campo_arriva_nel_context
 2) test_senza_campo_il_context_resta_vuoto
 3) test_nome_vincolo_non_matcha_per_sottostringa   <- il difetto corretto
 4) test_nessun_match_senza_default_rilancia        <- la politica da NON toccare
 5) test_nessun_match_con_default_maschera
 6) RifiutoIntegritaTest (2026-10-07): lo SQLSTATE decide, non il chiamante —
    unicita' → duplicato; FK → E_ANAG_FK; CHECK → validazione; NOT NULL →
    validazione col campo; il default di `create_with_constraint_mapping` non
    maschera una FK da duplicato
"""

from __future__ import annotations

from unittest import TestCase

from django.db import IntegrityError

from apps.anagrafiche.services._validators import (
    create_with_constraint_mapping,
    create_with_dedup,
    update_with_dedup,
)
from apps.core.services.service_errors import ServiceError
from apps.core.tests.db_error_fakes import (
    SQLSTATE_CHECK,
    SQLSTATE_FK,
    SQLSTATE_NOT_NULL,
    SQLSTATE_UNICITA,
    make_integrity_error,
)


# Scopo: una funzione che fallisce con l'errore dato (di default un'unicita').
def _fallisce_con(vincolo: str, sqlstate: str = SQLSTATE_UNICITA, colonna: str | None = None):
    def _fn():
        raise make_integrity_error(sqlstate, vincolo=vincolo, colonna=colonna)
    return _fn


class CreateWithConstraintMappingTest(TestCase):
    # Scopo: il campo dichiarato dalla mappa arriva nel context, da dove il
    #        translator lo mette nell'envelope e il client accende l'input.
    def test_il_campo_arriva_nel_context(self):
        with self.assertRaises(ServiceError) as ctx:
            create_with_constraint_mapping(
                _fallisce_con("uq_fornitori_codice"),
                {"uq_fornitori_codice": ("Codice fornitore duplicato.", "codice")},
            )
        self.assertEqual(ctx.exception.context, {"field": "codice"})
        self.assertEqual(ctx.exception.message, "Codice fornitore duplicato.")

    # Scopo: la forma vecchia (solo messaggio) continua a valere e NON inventa
    #        un campo. E' la forma giusta dove il campo non e' vero — un vincolo
    #        su una colonna che l'operatore non compila.
    def test_senza_campo_il_context_resta_vuoto(self):
        with self.assertRaises(ServiceError) as ctx:
            create_with_constraint_mapping(
                _fallisce_con("uq_fornitori_soggetto_ruolo_id"),
                {"uq_fornitori_soggetto_ruolo_id": "Esiste gia' un fornitore."},
            )
        self.assertEqual(ctx.exception.context, {})

    # Scopo: ⭐ IL DIFETTO CORRETTO DALL'UNIFICAZIONE. Col match a sottostringa
    #        `uq_tab_codice` veniva riconosciuto dentro `uq_tab_codice_interno`,
    #        e la voce che vinceva era la prima del dizionario: l'operatore si
    #        vedeva il messaggio dell'altro vincolo — e, da oggi, si vedrebbe
    #        accendere l'altro campo.
    def test_nome_vincolo_non_matcha_per_sottostringa(self):
        mappa = {
            "uq_tab_codice": ("Codice duplicato.", "codice"),
            "uq_tab_codice_interno": ("Codice interno duplicato.", "codice_interno"),
        }
        with self.assertRaises(ServiceError) as ctx:
            create_with_constraint_mapping(_fallisce_con("uq_tab_codice_interno"), mappa)
        self.assertEqual(ctx.exception.message, "Codice interno duplicato.")
        self.assertEqual(ctx.exception.context, {"field": "codice_interno"})

    # Scopo: ⚠️ LA POLITICA CHE L'UNIFICAZIONE NON DOVEVA TOCCARE. Senza match e
    #        senza default questa funzione RILANCIA l'IntegrityError invece di
    #        mascherarlo — al contrario di `map_integrity_error`, che ha sempre
    #        un `fallback_code`. Non sono due copie della stessa decisione: sono
    #        due decisioni diverse, e vanno tenute distinte.
    def test_nessun_match_senza_default_rilancia(self):
        with self.assertRaises(IntegrityError):
            create_with_constraint_mapping(
                _fallisce_con("uq_qualcosa_altro"),
                {"uq_tab_codice": ("Codice duplicato.", "codice")},
            )

    # Scopo: col `default_message` invece maschera, come prima.
    def test_nessun_match_con_default_maschera(self):
        with self.assertRaises(ServiceError) as ctx:
            create_with_constraint_mapping(
                _fallisce_con("uq_qualcosa_altro"),
                {"uq_tab_codice": ("Codice duplicato.", "codice")},
                default_message="Violazione di unicita'.",
            )
        self.assertEqual(ctx.exception.message, "Violazione di unicita'.")


class RifiutoIntegritaTest(TestCase):
    """Lo SQLSTATE decide la traduzione (E-7, parte fuori perimetro, 2026-10-07)."""

    def test_unicita_e_duplicato(self):
        with self.assertRaises(ServiceError) as ctx:
            create_with_dedup(_fallisce_con("uq_x"), "Gia' esistente.")
        self.assertEqual(ctx.exception.code, "E_ANAG_DUPLICATO")
        self.assertEqual(ctx.exception.message, "Gia' esistente.")

    def test_fk_non_e_duplicato(self):
        with self.assertRaises(ServiceError) as ctx:
            create_with_dedup(_fallisce_con("fk_x", SQLSTATE_FK), "Gia' esistente.")
        self.assertEqual(ctx.exception.code, "E_ANAG_FK")

    def test_check_e_validazione(self):
        with self.assertRaises(ServiceError) as ctx:
            update_with_dedup(_fallisce_con("chk_x", SQLSTATE_CHECK), "Gia' esistente.", "Non trovato.")
        self.assertEqual(ctx.exception.code, "E_ANAG_VALIDAZIONE")
        self.assertNotEqual(ctx.exception.message, "Gia' esistente.")

    def test_not_null_porta_il_campo(self):
        with self.assertRaises(ServiceError) as ctx:
            create_with_dedup(
                _fallisce_con(None, SQLSTATE_NOT_NULL, colonna="descrizione"), "Gia' esistente.",
            )
        self.assertEqual(ctx.exception.code, "E_ANAG_VALIDAZIONE")
        self.assertEqual(ctx.exception.fields, ("descrizione",))

    def test_default_non_maschera_una_fk(self):
        with self.assertRaises(ServiceError) as ctx:
            create_with_constraint_mapping(
                _fallisce_con("fk_x", SQLSTATE_FK),
                {"uq_tab_codice": ("Codice duplicato.", "codice")},
                default_message="Violazione di unicita'.",
            )
        self.assertEqual(ctx.exception.code, "E_ANAG_FK")
