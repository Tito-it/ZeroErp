# ------------------------------------------------------------
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Il vocabolario dell'esito di esecuzione dentro un lotto
#        (`STATI_ESECUZIONE_LOTTO`) deve coincidere con i `CHECK` che lo
#        possiedono — su ENTRAMBI i livelli.
#
# ⚠️ Rev 2026-09-07: l'esito del documento ha cambiato casa. Stava sulle colonne
#    del PERIMETRO (`fatturazione_lotti_gruppi`), che i giri di massa non
#    scrivono; ora vive in `fatturazione_lotti_esiti`, dove la riga NASCE quando
#    c'e' qualcosa da dire. ⭐ Il vocabolario e' rimasto identico, e questo
#    cancello e' il posto che lo dimostra invece di darlo per fatto.
#
# ⛔ PERCHE' DUE TABELLE E NON UNA. La D-2 di `brief-db-esito-gruppo-lotto`
#    decide che l'esito di un DOCUMENTO PRESO IN CARICO
#    (`fatturazione_lotti_esiti`) e quello della FATTURA prodotta
#    (`fatturazione_lotti_fatture`) parlano la stessa lingua: «due colonne che
#    rispondono alla stessa domanda a due livelli non possono parlare due
#    lingue». Finora quella decisione viveva in un documento; qui diventa un
#    cancello. Se i due CHECK divergessero, il backend ne seguirebbe uno solo e
#    sull'altra tabella scriverebbe valori rifiutati.
#
# ⚠️ E IL DIFETTO CHE UN MIRROR SBAGLIATO PRODUCE E' MUTO, in tre modi diversi:
#      · in LETTURA il filtro rifiuta un valore che il database ammette
#        (400 su una domanda legittima);
#      · in SCRITTURA `_marca_esito_gruppi` scrive un valore che il CHECK
#        rifiuta — e lo fa dentro un gestore d'eccezione, cioe' proprio dove
#        l'errore vero verrebbe coperto. ⚠️ E ora la riga si CREA: un valore
#        fuori vocabolario non fallisce piu' un `UPDATE` su zero righe, fa
#        fallire un `INSERT`;
#      · nell'ORDINAMENTO di `list_lotto_gruppi` il confronto «e' un errore?»
#        smette di agganciare, le righe rosse tornano in fondo e non fallisce
#        niente.
#
# 🔴 UN PRECEDENTE, sullo stesso vocabolario e trovato il 2026-09-06: la mappa
#    cromatica del frontend diceva `PRONTA` / `ELABORATA` / `ESCLUSA` — valori
#    che nessuno dei due CHECK ammette — e un documento `COMPLETED` usciva
#    GRIGIO invece che verde. Nessun errore: il ripiego di `resolveSeverity` e'
#    silenzioso di proposito. Il gemello frontend di questa costante
#    (`STATO_ESECUZIONE_LOTTO` in `vendite/constants.js`) resta allineato a
#    mano — `core/` non puo' importare da un dominio — ed e' il lato che questo
#    cancello NON copre.
#
# ⚠️ RICHIEDE IL DB VERO, opt-in `ZEROERP_TEST_DB_E2E=1` (accesa in CI).
#    NON SCRIVE NULLA.
# ------------------------------------------------------------

from __future__ import annotations

from unittest import TestCase

from apps.core.tests.db_e2e import richiedi_db_provvisto, valori_check
from apps.vendite.db.vendite_repository import (
    STATI_ESECUZIONE_DOCUMENTO,
    STATI_ESECUZIONE_LOTTO,
    STATO_ESECUZIONE_COMPLETED,
    STATO_ESECUZIONE_ERRORE,
    STATO_ESECUZIONE_ESCLUSO,
)


class EsitoEsecuzioneLottoGuardrail(TestCase):
    """Il mirror del vocabolario contro i CHECK che lo possiedono."""

    @classmethod
    def setUpClass(cls) -> None:
        super().setUpClass()
        richiedi_db_provvisto()

    # ⚠️ I letterali hanno cast diversi sulle due tabelle (`text` sui gruppi,
    #    `character varying` sulle fatture): la lettura sta nel building block
    #    condiviso proprio perche' una regex scritta per un caso e' cieca
    #    sull'altro.
    # ⭐ Ogni livello col SUO vocabolario, dal 2026-09-08: il documento preso in
    #    carico puo' essere `ESCLUSO`, la fattura prodotta no. Prima la costante
    #    era una sola e questa mappa la confrontava con entrambi i CHECK.
    _PER_TABELLA = {
        "vendite.fatturazione_lotti_esiti": (
            "chk_fatturazione_lotti_esiti_stato", STATI_ESECUZIONE_DOCUMENTO,
        ),
        "vendite.fatturazione_lotti_fatture": (
            "chk_fatturazione_lf_stato_esecuzione", STATI_ESECUZIONE_LOTTO,
        ),
    }

    # Scopo: il vocabolario Python di ogni livello e' esattamente quello del suo
    #        CHECK.
    def test_il_vocabolario_coincide_coi_check(self) -> None:
        for tabella, (conname, atteso) in self._PER_TABELLA.items():
            with self.subTest(tabella=tabella):
                self.assertEqual(
                    set(atteso), valori_check(tabella, conname),
                    f"il vocabolario Python non coincide col CHECK di "
                    f"{tabella}: un valore in meno rifiuta una domanda buona, "
                    "uno in piu' fa scrivere una riga che il vincolo respinge.",
                )

    # ⭐ LA D-2 RESA CANCELLO: i due livelli parlano la stessa lingua **a meno
    #    del surplus DICHIARATO**.
    #
    # ⚠️ Rev 2026-09-08: l'invariante era «identici», ed e' diventata rossa
    #    quando il DB ha aggiunto `ESCLUSO` al solo lato esito
    #    (brief-db-uscita-documento-dal-giro §7-bis). ⭐ E la divergenza e'
    #    LEGITTIMA: `ESCLUSO` dice «l'operatore ha tolto questo DOCUMENTO dal
    #    giro», e una FATTURA quello stato non lo puo' avere — quando un
    #    documento esce, la sua bozza viene cancellata e la riga di ponte
    #    sparisce. Non esiste una fattura «esclusa ma ancora li'».
    #
    # ⛔ E il test NON e' stato indebolito a un confronto vago: e' la stessa
    #    forma decisa dal team DB per il pgTAP gemello. Si asserisce la
    #    differenza nei DUE VERSI, e resta rosso in tutti e tre i casi che
    #    contano — il lato fattura acquista uno stato, il lato esito ne acquista
    #    uno non dichiarato, oppure `ESCLUSO` sparisce. ⚠️ Un `esiti - {ESCLUSO}
    #    == fatture` sarebbe stato piu' corto e avrebbe mancato il terzo.
    def test_i_due_livelli_parlano_la_stessa_lingua(self) -> None:
        vocabolari = {
            tabella: valori_check(tabella, conname)
            for tabella, (conname, _) in self._PER_TABELLA.items()
        }
        esiti = vocabolari["vendite.fatturazione_lotti_esiti"]
        fatture = vocabolari["vendite.fatturazione_lotti_fatture"]
        self.assertEqual(
            esiti - fatture, {STATO_ESECUZIONE_ESCLUSO},
            "il livello DOCUMENTO diverge dal livello FATTURA oltre il surplus "
            "dichiarato: l'unico valore in piu' ammesso e' ESCLUSO.",
        )
        self.assertEqual(
            fatture - esiti, set(),
            "il livello FATTURA ha un valore che il livello DOCUMENTO non "
            "ammette: la D-2 di brief-db-esito-gruppo-lotto li vuole nella "
            "stessa lingua, perche' due colonne che rispondono alla stessa "
            "domanda a due livelli non possono parlare due lingue.",
        )

    # ⚠️ I due valori che il codice NOMINA devono stare nell'elenco. Sembra
    #    tautologico — la tupla li riusa — e infatti e' il presidio di quella
    #    scelta: se un domani qualcuno riscrivesse le stringhe a mano, questo
    #    e' il punto in cui la seconda sede si vedrebbe.
    def test_i_valori_nominati_sono_nel_vocabolario(self) -> None:
        self.assertIn(STATO_ESECUZIONE_ERRORE, STATI_ESECUZIONE_LOTTO)
        self.assertIn(STATO_ESECUZIONE_COMPLETED, STATI_ESECUZIONE_LOTTO)
