# ------------------------------------------------------------
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: I presidi del COMANDO del digest — il pezzo che decide **se un'email
#        parte**, e a chi.
# Note: ⭐ Perche' esiste un file per tre metodi: il precedente
#        `VENDITE_APPROVAZIONE_PREZZO_RECIPIENT_EMAIL` non e' MAI partito, e non
#        e' mai fallito niente — il destinatario non era configurato e l'unica
#        traccia era un `logger.info`. Un invio che non parte in silenzio e'
#        esattamente cio' che questo cantiere combatte, e il pezzo che lo decide
#        senza prove sue e' il posto in cui rientrerebbe dalla finestra.
#        ⛔ Nessun database: `EmailRepository` e' un doppio, e le decisioni si
#        provano sulla loro forma.
# ------------------------------------------------------------

"""Indice test previsti (nessun database).

1. test_niente_da_dire_niente_invio
2. test_senza_destinatario_configurato_non_si_invia_e_lo_si_dichiara   ⭐
3. test_con_destinatario_il_digest_viene_accodato_sulla_porta_di_sistema
4. test_piu_indirizzi_il_primo_e_destinatario_gli_altri_in_copia
5. test_un_indirizzo_solo_non_produce_una_lista_di_copie_vuota
6. test_il_contesto_della_mail_non_dice_di_non_essere_stata_inviata
"""

from __future__ import annotations

from typing import Any
from unittest.mock import MagicMock, patch

from django.test import SimpleTestCase, override_settings

from apps.core.services import presidi_digest
from apps.core.management.commands.digest_presidi import (
    INVIO_ACCODATO,
    INVIO_NON_CONFIGURATO,
    INVIO_NON_RICHIESTO,
    Command,
    separa_destinatari,
)
from apps.core.services.email_constants import AMBITO_SISTEMA


# Scopo: un digest finto — al comando servono solo `da_inviare`, `cadenza` e il
#        riepilogo, e costruirne uno vero vorrebbe dire un catalogo intero.
def _digest(*, da_inviare: bool = True) -> Any:
    finto = MagicMock()
    finto.da_inviare = da_inviare
    finto.cadenza = "GIORNALIERA"
    finto.riepilogo.return_value = {
        "cadenza": "GIORNALIERA", "allarmi": 1, "righe_in_allarme": 3,
        "registri": 0, "lavorazioni": 0, "non_letti": 0, "corsie_ferme": [],
    }
    return finto


_MESSAGGIO = ("oggetto", "corpo testo", "<p>corpo html</p>")


class DigestPresidiInvioTests(SimpleTestCase):
    """Se un'email parte, a chi, e cosa si dichiara quando non parte."""

    def setUp(self) -> None:
        # ⚠️ Dal 2026-09-11 la chiamata a `insert_log` vive in
        #    `presidi_digest.accoda_email_presidi` (una sede per il command e per
        #    l'handler del guardiano): il doppio si mette dove sta la chiamata.
        patcher = patch.object(presidi_digest, "EmailRepository", autospec=True)
        self.repo_email = patcher.start()
        self.addCleanup(patcher.stop)
        self.comando = Command()

    # 1. Niente da dire e non e' la cadenza del battito: non si spedisce, e non
    #    e' un difetto — e' la forma che impedisce al digest di diventare la
    #    posta che si archivia senza aprire.
    @override_settings(PRESIDI_DIGEST_DESTINATARIO="chi.guarda@example.test")
    def test_niente_da_dire_niente_invio(self) -> None:
        esito = self.comando._invia(_digest(da_inviare=False), _MESSAGGIO)
        self.assertEqual(esito, INVIO_NON_RICHIESTO)
        self.repo_email.assert_not_called()

    # 2. ⭐ NESSUN DESTINATARIO: non si invia, e l'esito lo DICE. ⛔ I tre esiti
    #    sono tre di proposito: «non c'era niente da dire» e «non c'e' nessuno a
    #    cui dirlo» sono opposti, e appiattirli su «non inviato» nasconderebbe
    #    proprio la configurazione che manca.
    @override_settings(PRESIDI_DIGEST_DESTINATARIO="")
    def test_senza_destinatario_configurato_non_si_invia_e_lo_si_dichiara(self) -> None:
        esito = self.comando._invia(_digest(), _MESSAGGIO)
        self.assertEqual(esito, INVIO_NON_CONFIGURATO)
        self.assertNotEqual(esito, INVIO_NON_RICHIESTO)
        self.repo_email.assert_not_called()

    # 3. Con un destinatario si accoda, e si accoda sulla PORTA DI SISTEMA:
    #    `config.email_log` ha la row level security e questo comando non ha ne'
    #    sessione ne' identita' — un INSERT diretto verrebbe rifiutato.
    @override_settings(PRESIDI_DIGEST_DESTINATARIO="chi.guarda@example.test")
    def test_con_destinatario_il_digest_viene_accodato_sulla_porta_di_sistema(self) -> None:
        esito = self.comando._invia(_digest(), _MESSAGGIO)
        self.assertEqual(esito, INVIO_ACCODATO)
        _args, kwargs = self.repo_email.return_value.insert_log.call_args
        self.assertEqual(kwargs["destinatario"], "chi.guarda@example.test")
        self.assertEqual(kwargs["ambito"], AMBITO_SISTEMA)
        self.assertEqual(kwargs["oggetto"], "oggetto")
        self.assertEqual(kwargs["corpo_inviato_testo"], "corpo testo")

    # 4. ⭐ Piu' indirizzi si scrivono come si scrivono ovunque. Senza questo,
    #    «a@x, b@y» finirebbe INTERO nel campo destinatario e l'invio
    #    fallirebbe a valle, dentro la coda email: un guasto che si scopre
    #    guardando `config.email_log`, cioe' tardi e per caso.
    def test_piu_indirizzi_il_primo_e_destinatario_gli_altri_in_copia(self) -> None:
        for scritto in (
            "a@example.test, b@example.test ,c@example.test",
            "a@example.test; b@example.test; c@example.test",
            "a@example.test\nb@example.test,c@example.test",
        ):
            with self.subTest(scritto=scritto):
                self.assertEqual(
                    separa_destinatari(scritto),
                    ("a@example.test", ["b@example.test", "c@example.test"]),
                )
        self.assertEqual(separa_destinatari(None), ("", []))
        self.assertEqual(separa_destinatari("  ,  ; "), ("", []))

    # 5. ⚠️ `None` e non `[]` sulle copie: la colonna e' un `text[]` nullable, e
    #    una lista vuota direbbe «copie: nessuna» invece di «non si applica».
    @override_settings(PRESIDI_DIGEST_DESTINATARIO="uno@example.test")
    def test_un_indirizzo_solo_non_produce_una_lista_di_copie_vuota(self) -> None:
        self.comando._invia(_digest(), _MESSAGGIO)
        _args, kwargs = self.repo_email.return_value.insert_log.call_args
        self.assertIsNone(kwargs["destinatari_cc"])

    # 6. ⛔ Il contesto che viaggia con la riga non deve contenere l'esito
    #    dell'invio: sarebbe un campo che si contraddice da solo — «non
    #    inviato», scritto mentre l'invio sta avvenendo.
    @override_settings(PRESIDI_DIGEST_DESTINATARIO="uno@example.test")
    def test_il_contesto_della_mail_non_dice_di_non_essere_stata_inviata(self) -> None:
        self.comando._invia(_digest(), _MESSAGGIO)
        _args, kwargs = self.repo_email.return_value.insert_log.call_args
        contesto = kwargs["contesto_json"]
        self.assertNotIn("inviato", contesto)
        # ⭐ Ma il contesto dice QUALE giro l'ha prodotta: chi legge il giornale
        #    delle email non deve aprirla per saperlo.
        self.assertEqual(contesto["processo"], "digest_presidi")
        self.assertEqual(contesto["cadenza"], "GIORNALIERA")
