# ------------------------------------------------------------
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: I presidi della derivazione per classe (passi B-2/B-3/B-4 del
#        `piano-be-classe-codici-errore.md`).
#
#        COSA SORVEGLIA, E PERCHE' PROPRIO QUESTO. Dal 2026-08-07 lo status HTTP
#        non e' piu' scritto codice per codice: si DERIVA dalla classe. Il
#        guadagno — otto regole invece di 659 righe — si paga con tre modi nuovi
#        di rompersi, che prima non esistevano:
#          1. una classe che nessuna tabella di questo backend sa tradurre
#             (arriva dal DB una classe nuova, o `AVVISO`);
#          2. un modulo che si sfila dagli altri (un override o un messaggio per
#             un codice che il generatore non produce piu');
#          3. un default che smette di essere il default.
#        I test qui sotto sono uno per ciascuno di quei modi.
#
#        ⚠️ IL SECONDO DIVENTERA' IL PIU' IMPORTANTE, e oggi non lo sembra.
#        Finche' `error_policies_generated.py` e' scritto a mano un orfano non
#        nasce; dal passo B-5 quel file lo riscrive un generatore che legge il
#        database, e un codice ritirato a catalogo se ne va in silenzio
#        lasciando dietro il suo override.
#
#        Gira SENZA database: e' derivazione pura su dizionari Python.
# ------------------------------------------------------------

"""Indice test previsti.

 1) test_ogni_classe_usata_e_nel_vocabolario
 2) test_ogni_classe_del_vocabolario_ha_status_e_ui_tranne_avviso
 3) test_classe_senza_status_solleva            <- la garanzia del passo B-2
 4) test_avviso_non_ha_uno_status_per_progetto
 5) test_i_cinque_fuori_vocabolario_tengono_il_loro_status
 6) test_nessun_override_orfano
 7) test_nessun_messaggio_orfano
 8) test_ogni_codice_registrato_ha_un_messaggio_di_ripiego
 9) test_nessun_override_ripete_il_default_della_classe
10) test_i_messaggi_di_ripiego_non_hanno_segnaposto
11) test_ripiego_codice_e_non_registrato
12) test_ripiego_codice_senza_prefisso_non_registrato
13) test_policy_morta_prev_stato_non_modificabile_rimossa   <- passo B-1
14) test_resolve_e_has_dicono_la_stessa_cosa
"""

from __future__ import annotations

from unittest import TestCase, mock

from apps.core.services.error_messages_fallback import USER_MESSAGE_FALLBACK
from apps.core.services.error_policies import (
    CLASSI_ERRORE,
    HTTP_PER_CLASSE,
    HTTP_PER_CODICE,
    UI_ACTION_PER_CLASSE,
    ClasseErroreSenzaStatus,
    ErrorPolicyRegistry,
)
from apps.core.services.error_policies_generated import CLASSE_PER_CODICE
from apps.core.services.error_ui_overrides import UI_ACTION_OVERRIDE

# L'unica classe del vocabolario che non ha uno status, e non e' una lacuna:
# un avviso non rifiuta niente e non raggiunge mai un client (brief §4.2).
_CLASSE_SENZA_STATUS = "AVVISO"


class ErrorPoliciesClassiTest(TestCase):
    # Scopo: un codice non puo' dichiarare una classe che non esiste. E' il
    #        primo modo in cui il file generato puo' arrivare storto dal DB.
    def test_ogni_classe_usata_e_nel_vocabolario(self):
        ignote = sorted({c for c in CLASSE_PER_CODICE.values() if c not in CLASSI_ERRORE})
        self.assertEqual(
            ignote,
            [],
            "classi non nel vocabolario di error_policies.py: o il DB ne ha "
            "aggiunta una e va tradotta qui, o e' un refuso nel seed",
        )

    # Scopo: il vocabolario e le due tabelle di traduzione devono coprirsi.
    #        Una classe senza status non e' traducibile in una risposta HTTP.
    def test_ogni_classe_del_vocabolario_ha_status_e_ui_tranne_avviso(self):
        attese = CLASSI_ERRORE - {_CLASSE_SENZA_STATUS}
        self.assertEqual(set(HTTP_PER_CLASSE), attese)
        self.assertEqual(set(UI_ACTION_PER_CLASSE), attese)

    # Scopo: ⭐ LA GARANZIA DEL PASSO B-2, e prima del 2026-08-07 non c'era.
    #        `resolve` non falliva mai: aveva due ripieghi, e per un codice che
    #        non cominciasse per `E_` — cioe' per ogni avviso `W_` — ripiegava
    #        su `E_GENERICO`, quindi su un 500 tecnico col messaggio soppresso.
    #        Un avviso sfuggito al cancello (E) del guardrail SQL sarebbe
    #        diventato esattamente il difetto `E_DATABASE` da cui e' nato tutto
    #        il filone. Ora solleva.
    def test_classe_senza_status_solleva(self):
        codice = "W_TEST_AVVISO_FINTO"
        registro = dict(CLASSE_PER_CODICE, **{codice: _CLASSE_SENZA_STATUS})
        with mock.patch.dict(
            "apps.core.services.error_policies.CLASSE_PER_CODICE", registro, clear=True
        ):
            with self.assertRaises(ClasseErroreSenzaStatus) as ctx:
                ErrorPolicyRegistry.resolve(codice)
        # Il messaggio deve nominare il codice e la classe: un'eccezione che non
        # dice su quale voce e' inciampata costringe a cercarla fra 658.
        self.assertIn(codice, str(ctx.exception))
        self.assertIn(_CLASSE_SENZA_STATUS, str(ctx.exception))

    # Scopo: l'assenza di `AVVISO` dalle due tabelle e' una decisione, non una
    #        dimenticanza — se qualcuno gli dara' uno status «per far tornare
    #        una mappa» questo test glielo dira'.
    def test_avviso_non_ha_uno_status_per_progetto(self):
        self.assertIn(_CLASSE_SENZA_STATUS, CLASSI_ERRORE)
        self.assertNotIn(_CLASSE_SENZA_STATUS, HTTP_PER_CLASSE)
        self.assertNotIn(_CLASSE_SENZA_STATUS, UI_ACTION_PER_CLASSE)

    # Scopo: i cinque codici fuori dal vocabolario di dominio (401 x4, 502)
    #        prendono lo status dalla mappa per codice e non dalla classe. Se
    #        domani il DB cambiasse loro la classe, la risposta non deve
    #        muoversi: e' quello che li tiene fuori dal percorso.
    def test_i_cinque_fuori_vocabolario_tengono_il_loro_status(self):
        for codice, status in HTTP_PER_CODICE.items():
            with self.subTest(codice=codice):
                self.assertIn(codice, CLASSE_PER_CODICE, "codice non registrato")
                self.assertEqual(ErrorPolicyRegistry.resolve(codice).http_status, status)

    # Scopo: un override per un codice che il generatore non produce piu' e'
    #        una decisione di interfaccia rimasta senza il suo errore. Non fa
    #        danno — non la legge nessuno — ed e' esattamente per questo che
    #        marcisce senza che nessuno se ne accorga.
    def test_nessun_override_orfano(self):
        orfani = sorted(c for c in UI_ACTION_OVERRIDE if c not in CLASSE_PER_CODICE)
        self.assertEqual(orfani, [], "override senza il codice corrispondente")

    # Scopo: idem per i messaggi di ripiego.
    def test_nessun_messaggio_orfano(self):
        orfani = sorted(c for c in USER_MESSAGE_FALLBACK if c not in CLASSE_PER_CODICE)
        self.assertEqual(orfani, [], "messaggi di ripiego senza il codice corrispondente")

    # Scopo: il verso opposto. Un codice senza messaggio di ripiego non rompe
    #        niente (c'e' una frase neutra), ma mostra all'operatore una frase
    #        che non parla del suo problema: e' il degrado silenzioso.
    def test_ogni_codice_registrato_ha_un_messaggio_di_ripiego(self):
        senza = sorted(c for c in CLASSE_PER_CODICE if c not in USER_MESSAGE_FALLBACK)
        self.assertEqual(senza, [], "codici registrati senza messaggio di ripiego")

    # Scopo: un override che ripete il default e' una riga che non decide
    #        niente. Sono 176 righe da rileggere quando cambia una scelta di
    #        interfaccia: ognuna deve valere la lettura.
    def test_nessun_override_ripete_il_default_della_classe(self):
        inutili = sorted(
            codice
            for codice, azione in UI_ACTION_OVERRIDE.items()
            if azione == UI_ACTION_PER_CLASSE.get(CLASSE_PER_CODICE.get(codice, ""))
        )
        self.assertEqual(inutili, [], "override uguali al default della classe")

    # Scopo: e' la definizione stessa del modulo `error_messages_fallback`.
    #        Questi messaggi si mostrano QUANDO GLI ARGOMENTI NON CI SONO: uno
    #        con `%s` dentro arriverebbe a video con il segnaposto in chiaro.
    #        Misurato alla nascita del modulo: 0 su 658, contro 371 a catalogo.
    def test_i_messaggi_di_ripiego_non_hanno_segnaposto(self):
        con_segnaposto = sorted(c for c, m in USER_MESSAGE_FALLBACK.items() if "%s" in m)
        self.assertEqual(con_segnaposto, [], "messaggi di ripiego con segnaposto")

    # Scopo: il primo dei due ripieghi storici, che il passo B-2 NON tocca: e'
    #        cio' che tiene in piedi i codici nuovi che il team DB sta creando
    #        mentre il generatore non e' ancora in servizio.
    def test_ripiego_codice_e_non_registrato(self):
        policy = ErrorPolicyRegistry.resolve("E_CODICE_CHE_NON_ESISTE_ANCORA")
        self.assertEqual(policy.http_status, 400)
        self.assertEqual(policy.ui_action, "show_error_banner")

    # Scopo: il secondo ripiego — tutto cio' che non comincia per `E_` cade su
    #        `E_GENERICO`, cioe' 500.
    def test_ripiego_codice_senza_prefisso_non_registrato(self):
        policy = ErrorPolicyRegistry.resolve("CODICE_FUORI_CONVENZIONE_NON_REGISTRATO")
        self.assertEqual(policy.http_status, 500)

    # Scopo: passo B-1. `PREV_STATO_NON_MODIFICABILE` senza prefisso era una
    #        policy orfana: il gemello vivo e' `E_PREV_STATO_NON_MODIFICABILE`,
    #        e la riga senza prefisso il DB l'ha cancellata dal catalogo il
    #        2026-08-05 (`20260805-16`). Il test serve a non farla tornare col
    #        primo giro del generatore.
    def test_policy_morta_prev_stato_non_modificabile_rimossa(self):
        self.assertFalse(ErrorPolicyRegistry.has("PREV_STATO_NON_MODIFICABILE"))
        self.assertTrue(ErrorPolicyRegistry.has("E_PREV_STATO_NON_MODIFICABILE"))

    # Scopo: `has` e `resolve` devono guardare lo stesso registro. Se `has`
    #        dicesse di si' e `resolve` ripiegasse, il cancello del terzo lato
    #        sarebbe verde su un codice che risponde col ripiego.
    def test_resolve_e_has_dicono_la_stessa_cosa(self):
        for codice in CLASSE_PER_CODICE:
            with self.subTest(codice=codice):
                self.assertTrue(ErrorPolicyRegistry.has(codice))
                self.assertEqual(ErrorPolicyRegistry.resolve(codice).code, codice)
                self.assertIsNotNone(ErrorPolicyRegistry.classe_di(codice))
