# ------------------------------------------------------------
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Il vocabolario di `config.email_outbox.ambito` che il backend usa per
#        VALIDARE (`AMBITI_OUTBOX`) deve coincidere col `CHECK` del database.
#
# ⛔ PERCHE' CONTA PIU' DI UN NORMALE ELENCO. Su quella colonna il database monta
#    una policy di lettura che tratta `SISTEMA` come segreto di sistema (reset
#    password, alert) e tutto il resto come materiale d'azienda. Un valore in
#    meno nel mirror e' un 400 su una richiesta legittima; uno in piu' e' una
#    bozza che nasce con un'etichetta che la policy non sa classificare.
#
# ⚠️ E il default e' gia' stato il difetto una volta: fino al 2026-09-05 l'API
#    metteva `SISTEMA` quando il client taceva, cioe' usava un valore di RIPIEGO
#    come cancello di sicurezza. La firma senza default e' presidiata in
#    `apps/core/tests/services/test_email_outbox_service.py`; qui si guarda il
#    vocabolario.
#
# ⚠️ RICHIEDE IL DB VERO, opt-in `ZEROERP_TEST_DB_E2E=1` (accesa in CI).
#    NON SCRIVE NULLA.
# ------------------------------------------------------------

from __future__ import annotations

from unittest import TestCase

from apps.core.api.email_views import AMBITI_OUTBOX
from apps.core.tests.db_e2e import richiedi_db_provvisto, valori_check
from apps.core.tests._repo import repo_root


class EmailOutboxAmbitoGuardrail(TestCase):
    """Il mirror del vocabolario contro il CHECK che lo possiede."""

    @classmethod
    def setUpClass(cls) -> None:
        super().setUpClass()
        richiedi_db_provvisto()

    # ⭐ La lettura del CHECK sta nel building block condiviso: qui i letterali
    #    hanno cast `character varying`, sui processi `text` — una regex scritta
    #    apposta per questo caso sarebbe stata cieca sull'altro.
    # ⚠️ DUE TABELLE, UN VOCABOLARIO: `ambito` esiste su `email_outbox` (le
    #    bozze) e su `email_log` (la coda di invio), con lo stesso `CHECK`. Il
    #    backend ne tiene UNA costante, quindi si prova contro entrambi: se i due
    #    CHECK divergessero, la costante ne seguirebbe uno solo e sull'altra
    #    tabella scriverebbe valori rifiutati.
    def test_il_vocabolario_coincide_coi_check(self) -> None:
        per_tabella = {
            "config.email_outbox": "chk_email_outbox_ambito",
            "config.email_log": "chk_email_log_ambito",
        }
        for tabella, conname in per_tabella.items():
            with self.subTest(tabella=tabella):
                self.assertEqual(
                    set(AMBITI_OUTBOX), valori_check(tabella, conname),
                    f"`AMBITI_OUTBOX` non coincide col CHECK di {tabella}: un "
                    "valore in meno rifiuta una richiesta buona, uno in piu' fa "
                    "nascere una riga che la policy di lettura non sa "
                    "classificare.",
                )

    # ⛔ IL DIFETTO CHE QUESTO TEST HA TROVATO, il 2026-09-05, e che non si vede
    #    da nessun'altra parte: `approvazioni_prezzo_service` accodava con
    #    `ambito="WORKFLOW_APPROVAZIONE_PREZZO"` — fuori vocabolario, quindi
    #    violazione di `chk_email_log_ambito`. E la chiamata sta dentro un
    #    `except Exception: log + continue`, quindi la notifica all'approvatore
    #    NON partiva e a dirlo c'era una riga di log.
    # ⭐ Si guarda il CODICE, non il database: le righe sbagliate non esistono —
    #    il vincolo le ha sempre rifiutate — quindi un test sui dati sarebbe
    #    verde per sottrazione. L'unica traccia del difetto e' nel sorgente.
    #
    # ⚠️ IL PERIMETRO E' STRETTO DI PROPOSITO, e la prima stesura sbagliava:
    #    cercava `ambito=` in TUTTO il backend e pescava un'omonimia completa —
    #    `ui.lista_preset.ambito` ('ruolo', 'emittente_fiscale', 'sistema'), che
    #    non ha niente a che vedere con le email. ⛔ Un presidio che grida su
    #    righe sane viene spento, e con lui sparisce anche il caso vero.
    #    ⇒ Si guardano SOLO i file che parlano davvero col percorso email, e si
    #    saltano i commenti (dove questa stessa nota cita il valore sbagliato).
    _SEGNALI_EMAIL = (
        "EmailDispatchService", "EmailOutboxService",
        "EmailRepository", "email_service",
    )

    def test_nessun_chiamante_inventa_un_ambito(self) -> None:
        import re

        radice = repo_root() / "backend/apps"
        assegnazione = re.compile(r"""\bambito\s*=\s*["']([^"']+)["']""")
        inventati: list[str] = []
        esaminati = 0
        for sorgente in radice.rglob("*.py"):
            if "/tests/" in str(sorgente) or sorgente.name.startswith("test_"):
                continue
            testo = sorgente.read_text(encoding="utf-8")
            if not any(s in testo for s in self._SEGNALI_EMAIL):
                continue
            esaminati += 1
            for n, riga in enumerate(testo.splitlines(), 1):
                if riga.lstrip().startswith("#"):
                    continue
                trovato = assegnazione.search(riga)
                if trovato and trovato.group(1) not in AMBITI_OUTBOX:
                    inventati.append(
                        f"{sorgente.relative_to(radice)}:{n} → {trovato.group(1)!r}"
                    )
        # ⛔ Non un `assert` sul solo esito: se il filtro smettesse di trovare
        #    file — un rename dei service — il test resterebbe verde avendo
        #    smesso di guardare.
        self.assertGreater(
            esaminati, 0,
            "nessun file del percorso email trovato: il filtro `_SEGNALI_EMAIL` "
            "non aggancia piu' niente e questo test non sta provando nulla.",
        )
        self.assertEqual(
            inventati, [],
            "ambito fuori vocabolario: la scrittura viola il CHECK, e se la "
            "chiamata e' best-effort l'email semplicemente non parte.",
        )
