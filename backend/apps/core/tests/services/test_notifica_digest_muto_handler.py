# ------------------------------------------------------------
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Test dell'handler `NOTIFICA_DIGEST_MUTO` — la guardia reciproca del
#        digest dei presidi: il job pgAgent `guardiano_digest` accoda, il
#        drenatore spedisce alla persona che aspetta gli allarmi.
#
# ⚠️ Database MOCKATO (`EmailRepository`): qui si prova cio' che l'handler
#    DECIDE — a chi scrive, che cosa scrive, e che cosa fa quando non c'e'
#    nessuno a cui scrivere. Che il binding col seed regga contro il catalogo
#    vero lo prova `tests/db/test_coda_lavori_tipi_handler_guardrail.py`.
#
# Indice test:
#   1) con un destinatario configurato accoda UNA email di SISTEMA a lui, con
#      le copie a parte e il contesto che dice chi ha visto e di chi si parla
#   2) ⛔ senza destinatario FALLISCE, e fallisce TERMINALE (`E_CONFIG_MANCANTE`
#      + `terminale`): «ho visto e non ho potuto dirlo» resta visibile
#   3) il messaggio porta i fatti del payload — da quanto, l'ultimo segno, il
#      contratto — e l'oggetto dice da quanto senza aprire
#   4) i valori del payload finiscono nell'HTML escapati
#   5) l'handler e' registrato sotto l'`handler_code` del seed
#   6) un payload vuoto non fa fallire l'avviso: si avvisa comunque, coi
#      trattini al posto dei fatti che mancano
# ------------------------------------------------------------

from __future__ import annotations

import html
from unittest.mock import patch

from django.test import SimpleTestCase, override_settings

from apps.core.services.coda_lavori.drain_engine import CONTEXT_KEY_TERMINALE
from apps.core.services.coda_lavori.notifica_digest_muto_handler import (
    HANDLER_CODE,
    componi_avviso_digest_muto,
    notifica_digest_muto_handler,
    register,
)
from apps.core.services.email_constants import AMBITO_SISTEMA
from apps.core.services.processi import PROCESSO_DIGEST_PRESIDI
from apps.core.services.service_errors import ServiceError
from apps.core.services.sveglie import sveglie_di_processo

# ⚠️ Il doppio di `EmailRepository` si mette dove sta la chiamata: in
#    `presidi_digest.accoda_email_presidi`, la sede condivisa col command.
_EMAIL_REPO = "apps.core.services.presidi_digest.EmailRepository"

# Il payload come lo scrive `dbops.fn_guardiano_digest` (§10.8 del brief).
_PAYLOAD = {
    "processo_codice": "digest_presidi",
    "tolleranza_minuti": 11520,
    "ultimo_segno_di_vita": "2026-09-02T07:00:32+02:00",
    "muto_da": "9 days 02:15:00",
}


class NotificaDigestMutoHandlerTests(SimpleTestCase):

    # 1. Il caso normale: una email di SISTEMA al destinatario, copie a parte.
    @override_settings(PRESIDI_DIGEST_DESTINATARIO="chi.guarda@example.test; copia@example.test")
    def test_accoda_una_email_di_sistema_al_destinatario(self) -> None:
        with patch(_EMAIL_REPO) as repo_cls:
            esito = notifica_digest_muto_handler(dict(_PAYLOAD), scope=None)

        repo_cls.return_value.insert_log.assert_called_once()
        kw = repo_cls.return_value.insert_log.call_args.kwargs
        self.assertEqual(kw["destinatario"], "chi.guarda@example.test")
        self.assertEqual(kw["destinatari_cc"], ["copia@example.test"])
        self.assertEqual(kw["ambito"], AMBITO_SISTEMA)
        self.assertIsNone(kw["email_account_id"])
        self.assertIsNone(kw["email_template_id"])
        # Il contesto dice CHI ha visto e DI CHI si parla: due processi.
        self.assertEqual(kw["contesto_json"]["processo"], "guardiano_digest")
        self.assertEqual(kw["contesto_json"]["riguarda"], "digest_presidi")
        self.assertEqual(kw["contesto_json"]["muto_da"], "9 days 02:15:00")
        # E l'esito del lavoro racconta la stessa cosa, per il drawer del job.
        self.assertEqual(esito["destinatario"], "chi.guarda@example.test")
        self.assertEqual(esito["copie"], 1)
        self.assertEqual(esito["riguarda"], "digest_presidi")
        self.assertEqual(
            esito["email_log_id"], repo_cls.return_value.insert_log.return_value,
        )

    # 2. ⛔ Senza destinatario il lavoro FALLISCE, terminale. Un `return`
    #    verde qui sarebbe un FATTO su un avviso che nessuno ha ricevuto — e il
    #    job in ERRORE e' esattamente cio' che `vw_coda_lavori_da_guardare`
    #    mostra nel pannello.
    @override_settings(PRESIDI_DIGEST_DESTINATARIO="")
    def test_senza_destinatario_fallisce_terminale(self) -> None:
        with patch(_EMAIL_REPO) as repo_cls:
            with self.assertRaises(ServiceError) as ctx:
                notifica_digest_muto_handler(dict(_PAYLOAD))
        repo_cls.return_value.insert_log.assert_not_called()
        self.assertEqual(ctx.exception.code, "E_CONFIG_MANCANTE")
        self.assertTrue(ctx.exception.context.get(CONTEXT_KEY_TERMINALE))
        self.assertIn("ZEROERP_PRESIDI_DIGEST_DESTINATARIO", ctx.exception.message)

    # 3. Il messaggio porta i fatti, e l'oggetto dice da quanto.
    def test_il_messaggio_porta_i_fatti_del_payload(self) -> None:
        oggetto, testo, corpo_html = componi_avviso_digest_muto(dict(_PAYLOAD))
        self.assertIn("MUTO da 9 days 02:15:00", oggetto)
        # ⭐ Le unit nel messaggio sono QUELLE DICHIARATE per il processo in
        #    `sveglie.json` — lette, non ricopiate: se una corsia cambia nome,
        #    la mail la segue da sola.
        unit_dichiarate = [s.unit for s in sveglie_di_processo(PROCESSO_DIGEST_PRESIDI)]
        self.assertGreater(len(unit_dichiarate), 0, "il digest non ha sveglie dichiarate")
        attesi = [
            "digest_presidi",
            "2026-09-02T07:00:32+02:00",
            "ogni 11520 minuti",
            "9 days 02:15:00",
            "run-command.sh digest_presidi --secco",
            *(f"journalctl -u {u}.service" for u in unit_dichiarate),
            *(f"systemctl list-timers '{u}.timer'" for u in unit_dichiarate),
        ]
        for atteso in attesi:
            with self.subTest(atteso=atteso):
                self.assertIn(atteso, testo)
                self.assertIn(atteso, html.unescape(corpo_html))

    # 4. Cio' che arriva dal payload finisce nell'HTML escapato: e' la regola,
    #    non la fiducia nel produttore.
    def test_i_valori_del_payload_sono_escapati_nell_html(self) -> None:
        payload = dict(_PAYLOAD, muto_da="<script>alert(1)</script>")
        _oggetto, _testo, corpo_html = componi_avviso_digest_muto(payload)
        self.assertNotIn("<script>", corpo_html)
        self.assertIn("&lt;script&gt;", corpo_html)

    # 5. Il binding col seed: `handler_code` e' la chiave del dispatch.
    def test_si_registra_sotto_il_codice_del_seed(self) -> None:
        with patch(
            "apps.core.services.coda_lavori.handler_registry.register_handler"
        ) as reg:
            register()
        reg.assert_called_once_with(HANDLER_CODE, notifica_digest_muto_handler)
        self.assertEqual(HANDLER_CODE, "notifica_digest_muto_default")

    # 6. Un payload vuoto non e' una ragione per tacere: l'avviso parte con i
    #    trattini dove i fatti mancano. Meglio un avviso monco di nessun avviso.
    @override_settings(PRESIDI_DIGEST_DESTINATARIO="chi.guarda@example.test")
    def test_un_payload_vuoto_avvisa_comunque(self) -> None:
        with patch(_EMAIL_REPO) as repo_cls:
            esito = notifica_digest_muto_handler({})
        kw = repo_cls.return_value.insert_log.call_args.kwargs
        self.assertIn("MUTO", kw["oggetto"])
        self.assertIn("mai registrato", kw["corpo_inviato_testo"])
        self.assertEqual(esito["riguarda"], "digest_presidi")
        self.assertIsNone(esito["muto_da"])
