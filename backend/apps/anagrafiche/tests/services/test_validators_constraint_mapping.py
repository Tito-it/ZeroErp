# ------------------------------------------------------------
# SPDX-License-Identifier: GPL-3.0-or-later
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
"""

from __future__ import annotations

from unittest import TestCase

from django.db import IntegrityError

from apps.anagrafiche.services._validators import create_with_constraint_mapping
from apps.core.services.service_errors import ServiceError


def _fallisce_con(vincolo: str):
    def _fn():
        raise IntegrityError(
            f'duplicate key value violates unique constraint "{vincolo}"'
        )
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
