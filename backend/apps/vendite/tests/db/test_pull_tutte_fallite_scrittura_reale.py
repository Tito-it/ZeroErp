# ------------------------------------------------------------
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: P-3 di `brief-db-esito-gruppo-lotto` — il ramo «TUTTE le commesse
#        fallite» provato SENZA mockare il repository che scrive.
#
# 🔴 PERCHE' ESISTE, e la ragione e' un difetto sfuggito ai test che c'erano.
#    Il 2026-09-06 la marcatura dei documenti caduti spariva proprio nel caso
#    peggiore: quel ramo SOLLEVAVA, e il `transaction.atomic()` che
#    `run_pipeline` tiene attorno al ciclo degli step faceva rollback portandosi
#    via i segni appena scritti. ⛔ Nessun test lo vedeva, e non per distrazione:
#    provavano che la CHIAMATA avvenisse — su un repository mockato — non che la
#    RIGA restasse. E' la differenza fra verificare un'intenzione e verificare
#    un effetto.
#
# ⭐ COSA E' MOCKATO E COSA NO, ed e' la scelta portante di questo file:
#      · `commesse_repository` e' finto, e lo dev'essere: serve a COSTRUIRE il
#        caso (tutte le commesse falliscono), che con dati veri non si produce
#        a comando;
#      · `repository` (`VenditePipelineRepository`) e' VERO, e li' sta il punto:
#        e' lui che scrive l'esito. Con un mock al suo posto questo test
#        tornerebbe a provare l'intenzione.
#
# ⚠️ CHE COSA NON PROVA. Non prova che la scrittura sopravviva a un rollback —
#    perche' NON sopravvive, e non deve: la riga e' un `INSERT` normale nella
#    transazione del chiamante. Cio' che protegge i segni e' che quel ramo non
#    sollevi piu' (P-5, decisione di Tid 2026-09-06). ⇒ Il presidio vero e' il
#    primo test: se qualcuno rimettesse il `raise`, diventa rosso.
#
# ⚠️ RICHIEDE IL DB VERO, opt-in `ZEROERP_TEST_DB_E2E=1` (accesa in CI).
#    NON LASCIA NIENTE: tutto in transazione annullata.
#
# Indice test:
#   1. test_il_ramo_tutte_fallite_non_solleva
#   2. test_la_riga_dell_esito_resta_scritta
# ------------------------------------------------------------

from __future__ import annotations

from unittest import TestCase
from unittest.mock import create_autospec

from django.db import connection, transaction

from apps.core.tests.db_e2e import apri_contesto_operatore, richiedi_db_provvisto
from apps.vendite.db.commesse_repository import CommesseRepository
from apps.vendite.db.pipeline_repository import VenditePipelineRepository
from apps.vendite.services.pipeline_step_executor import (
    PipelineStepExecutor,
    TaskEsitoParziale,
)

_TASK = "pull_attivita_da_commessa"


# Scopo: il finto che COSTRUISCE il caso — ogni commessa cade.
#
# ⛔ Non e' un mock del percorso di SCRITTURA, che resta vero: e' il modo di
#    produrre «tutte fallite» senza sporcare dati veri.
# ⭐ `create_autospec` e non una classe scritta a mano, ed e' la differenza che
#    conta: il finto prende la firma da `CommesseRepository`, quindi il giorno
#    in cui quel metodo cambia parametri questo test diventa rosso invece di
#    continuare a passare su una chiamata che in produzione non esiste piu'.
#    Un finto scritto a mano con `**kwargs` accetta qualunque cosa — cioe' e'
#    cieco proprio al difetto per cui i mock sono pericolosi.
def _commesse_che_falliscono(commessa_ids: list[int]):
    # ⛔ Una funzione che solleva, non un generator-throw dentro una lambda: la
    #    frase e' il MOTIVO che finisce sul documento, e va letta a colpo d'occhio.
    def cade(commessa_id, **_kwargs):
        raise RuntimeError(f"ROOT source mancante per commessa {commessa_id}")

    finto = create_autospec(CommesseRepository, instance=True)
    finto.list_commesse_emittibili.return_value = list(commessa_ids)
    finto.emit_attivita_fatturabili.side_effect = cade
    return finto


class PullTutteFalliteScritturaReale(TestCase):
    """Il ramo peggiore, con il repository che scrive davvero."""

    @classmethod
    def setUpClass(cls) -> None:
        super().setUpClass()
        richiedi_db_provvisto()

    # Scopo: contesto operatore + materiale. ⚠️ Senza le GUC le tabelle sotto
    #        RLS rispondono ZERO righe e sembrerebbe assenza di dati: e' il modo
    #        classico in cui questo test diventerebbe verde per sottrazione.
    def _prepara(self):
        with connection.cursor() as cur:
            apri_contesto_operatore(cur)
            # ⭐ Un lotto SENZA perimetro: e' il caso che prima di oggi non
            #    aveva dove essere marcato, quindi quello che vale la pena
            #    provare. `NOT EXISTS` e non «tipo_lotto = MASSIVO»: il
            #    discriminante e' l'assenza di righe, non il nome del tipo.
            cur.execute(
                """
                SELECT l.id FROM vendite.fatturazione_lotti l
                WHERE NOT EXISTS (SELECT 1 FROM vendite.fatturazione_lotti_gruppi g
                                   WHERE g.lotto_id = l.id)
                ORDER BY l.id DESC LIMIT 1
                """
            )
            lotto = cur.fetchone()
            if lotto is None:
                self.skipTest("nessun lotto senza perimetro su cui provare il ramo")
            # Una commessa con attivita': senza, la funzione DB non ricava
            # nessuna chiave e scriverebbe zero righe — il test proverebbe il
            # nulla invece del caso.
            cur.execute(
                """
                SELECT ca.commessa_id FROM vendite.commesse_attivita ca
                GROUP BY ca.commessa_id ORDER BY ca.commessa_id LIMIT 1
                """
            )
            commessa = cur.fetchone()
            if commessa is None:
                self.skipTest(
                    "nessuna commessa con attivita': il ritrovamento delle "
                    "chiavi non e' esercitabile, e un esito a zero righe "
                    "proverebbe il nulla"
                )
            # ⭐ LO STATO DI PARTENZA SI FABBRICA, come nel test dell'ordine: se
            #    un giro vero e' gia' passato di qui il lotto porta i suoi
            #    esiti, e l'asserzione «tutte le righe sono ERRORE» misurerebbe
            #    la STORIA invece del ramo appena eseguito.
            # ⛔ La cancellazione vive nella transazione annullata come tutto il
            #    resto: non lascia niente.
            cur.execute(
                "DELETE FROM vendite.fatturazione_lotti_esiti WHERE lotto_id = %s",
                [int(lotto[0])],
            )
        return int(lotto[0]), [int(commessa[0])]

    # Scopo: esegue il ramo com'e' eseguito in produzione — con l'`atomic` che
    #        `run_pipeline` tiene attorno al passo — e restituisce
    #        `(esito, eccezione)`.
    # ⭐ L'`atomic` interno NON e' decorativo: e' lo specchio del confine di
    #    transazione che il 2026-09-06 si portava via le marcature. Con il
    #    `raise` rimesso, qui l'eccezione uscirebbe e il savepoint annullerebbe
    #    le righe — cioe' entrambi i test diventerebbero rossi, ognuno per la
    #    sua meta'.
    def _esegui(self, lotto_id: int, commesse: list[int]):
        executor = PipelineStepExecutor(
            repository=VenditePipelineRepository(),
            commesse_repository=_commesse_che_falliscono(commesse),
        )
        context = executor.repository.get_lotto_context(lotto_id)
        self.assertIsNotNone(context, f"lotto {lotto_id} senza contesto")
        # ⛔ Lo STATO del documento fiscale, non il TIPO: sono due cataloghi
        #    diversi (`config.stati_doc_fiscale` e `config.tipi_doc_fiscale`) e
        #    questo valore finisce in `stato_doc_fiscale_id` sul log d'errore.
        #    ⚠️ `LottoContext` il primo non ce l'ha — passare `tipo_doc_fiscale_id`
        #    perche' «era li'» scriveva un id del catalogo sbagliato: un numero
        #    plausibile nella colonna sbagliata non fallisce da nessuna parte.
        stato_doc = executor.repository.get_lotto_stato_doc_fiscale_id(lotto_id)
        try:
            with transaction.atomic():
                esito = executor._handle_pull_attivita_da_commessa_task(
                    task=_TASK,
                    fn_name=None,
                    lotto_id=lotto_id,
                    stato_doc_fiscale_id=stato_doc,
                    context=context,
                    params={},
                    dry_run=False,
                )
        except Exception as exc:  # e' esattamente cio' che si misura
            return None, exc
        return esito, None

    # 1) ⭐ IL PRESIDIO VERO: quel ramo non solleva. E' cio' che protegge i
    #    segni — non una scrittura durevole, che non esiste.
    def test_il_ramo_tutte_fallite_non_solleva(self) -> None:
        with transaction.atomic():
            lotto_id, commesse = self._prepara()
            esito, eccezione = self._esegui(lotto_id, commesse)
            self.assertIsNone(
                eccezione,
                "il ramo «tutte fallite» ha sollevato: il rollback dello step "
                "si porta via le marcature dei documenti caduti, e il caso "
                "peggiore torna a essere l'unico senza traccia (P-5).",
            )
            # E il giro resta dichiarato FALLITO: non si esce in COMPLETATO.
            self.assertIsInstance(esito, TaskEsitoParziale)
            self.assertEqual(esito.error_code, "E_PULL_COMMESSA")
            self.assertEqual(esito.meta["ok"], 0)
            self.assertEqual(esito.meta["falliti"], esito.meta["totale"])
            transaction.set_rollback(True)

    # 2) ⭐ E LA RIGA C'E' DAVVERO. Il repository non e' mockato, quindi qui si
    #    legge cio' che e' stato scritto — non che qualcuno abbia chiamato
    #    qualcosa. E' la meta' che mancava ai test del 2026-09-06.
    def test_la_riga_dell_esito_resta_scritta(self) -> None:
        with transaction.atomic():
            lotto_id, commesse = self._prepara()
            _esito, eccezione = self._esegui(lotto_id, commesse)
            self.assertIsNone(eccezione)
            with connection.cursor() as cur:
                cur.execute(
                    """
                    SELECT stato_esecuzione, errore_codice, errore_messaggio
                    FROM vendite.fatturazione_lotti_esiti
                    WHERE lotto_id = %s
                    """,
                    [lotto_id],
                )
                righe = cur.fetchall()
            self.assertTrue(
                righe,
                "nessun esito scritto: la marcatura non e' arrivata a nessun "
                "documento. ⚠️ Su un lotto SENZA perimetro questo era il "
                "comportamento fino al 2026-09-07 — la riga non veniva creata.",
            )
            for stato, codice, messaggio in righe:
                self.assertEqual(stato, "ERRORE")
                self.assertEqual(codice, "E_PULL_COMMESSA")
                # ⛔ Un errore muto non si scrive: il vincolo di tabella pretende
                #    almeno una fra causa e frase, e qui ci sono entrambe.
                self.assertIn("ROOT source mancante", messaggio or "")
            transaction.set_rollback(True)
