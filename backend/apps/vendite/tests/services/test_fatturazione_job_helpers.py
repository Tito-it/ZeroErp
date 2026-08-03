# ------------------------------------------------------------
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Test unit della diagnostica «perche' questo gruppo non e' stato
#        fatturato» (`classifica_gruppo_non_servito` + messaggio all'operatore).
#        Nasce dal caso del 2026-08-03: emissione mirata su un ordine di giugno
#        con esito «fatto» e zero lotti, senza che nulla dicesse che la commessa
#        era rimasta in BOZZA.
#
#        La classificazione legge una FOTOGRAFIA (conteggi per stato), non
#        ricalcola l'ammissibilita': l'ordine dei rami e' la sola regola sotto
#        test, ed e' quello che decide quale causa viene raccontata quando ce
#        n'e' piu' d'una.
#
# Indice test (0..N):
#   0. gruppo_senza_righe_e_sconosciuto
#   1. righe_pronte_e_testata_bloccata_dice_stato_e_lavoro_fermo
#   1-bis. concordanza_singolare
#   2. righe_pronte_e_testata_ok_non_inventa_una_causa
#   3. righe_non_approvate
#   4. tipo_doc_mancante
#   5. fuori_competenza_suggerisce_il_mese_recente
#   6. gia_emesse
#   6-bis. gia_emesse_con_annullate
#   6-ter. rifiutate_distinte_dalle_non_approvate
#   6-quater. tutte_annullate
#   7. priorita_testata_sopra_le_righe
#   8. messaggio_singolo_gruppo
#   9. messaggio_molti_gruppi_tronca_e_conta
# ------------------------------------------------------------

from __future__ import annotations

from django.test import SimpleTestCase

from apps.vendite.services._fatturazione_job_helpers import (
    MOTIVO_COMMESSA_NON_EMITTIBILE,
    MOTIVO_FUORI_COMPETENZA,
    MOTIVO_GIA_EMESSE,
    MOTIVO_GRUPPO_SCONOSCIUTO,
    MOTIVO_NON_DETERMINATO,
    MOTIVO_RIGHE_ANNULLATE,
    MOTIVO_RIGHE_NON_APPROVATE,
    MOTIVO_RIGHE_RIFIUTATE,
    MOTIVO_TIPO_DOC_MANCANTE,
    classifica_gruppo_non_servito,
    messaggio_gruppi_non_serviti,
    spiega_gruppi_non_serviti,
)


# Scopo: fotografia di gruppo con i soli conteggi valorizzati dal caso in esame.
def _foto(**kwargs) -> dict:
    base = {
        "gruppo_key": "ORDINE_VENDITA:abc",
        "commessa_codice": "CMM-001",
        "stato_commessa": "PRONTA_FATTURAZIONE",
        "commessa_emittibile": True,
        "n_righe": 0, "n_emesse": 0, "n_annullate": 0, "n_rifiutate": 0,
        "n_non_approvate": 0, "n_senza_tipo_doc": 0, "n_fuori_competenza": 0,
        "n_pronte": 0,
    }
    base.update(kwargs)
    return base


class ClassificaGruppoNonServitoTests(SimpleTestCase):

    # 0. Nessuna riga per la chiave: chiave sconosciuta, non «già emesse».
    def test_gruppo_senza_righe_e_sconosciuto(self) -> None:
        motivo, testo = classifica_gruppo_non_servito(_foto(n_righe=0))
        self.assertEqual(motivo, MOTIVO_GRUPPO_SCONOSCIUTO)
        self.assertIn("nessuna attività", testo)

    # 1. Il caso reale: righe pronte, testata non emittibile. Il testo deve dire
    #    lo STATO che blocca e quanto lavoro resta fermo — è ciò che l'operatore
    #    legge nel toast.
    def test_righe_pronte_e_testata_bloccata_dice_stato_e_lavoro_fermo(self) -> None:
        motivo, testo = classifica_gruppo_non_servito(_foto(
            n_righe=5, n_pronte=5, commessa_emittibile=False,
            stato_commessa="BOZZA", commessa_codice="CMM-108",
        ))
        self.assertEqual(motivo, MOTIVO_COMMESSA_NON_EMITTIBILE)
        self.assertIn("BOZZA", testo)
        self.assertIn("5 attività pronte", testo)
        # Il codice commessa NON sta nel testo del motivo: lo antepone il
        # compositore del messaggio (altrimenti compare due volte di fila).
        self.assertNotIn("CMM-108", testo)

    # 2. Righe pronte e testata emittibile: la fotografia NON spiega
    #    l'esclusione (es. commessa senza emittente) → si dichiara, non si
    #    inventa una causa plausibile.
    def test_righe_pronte_e_testata_ok_non_inventa_una_causa(self) -> None:
        motivo, _ = classifica_gruppo_non_servito(_foto(
            n_righe=3, n_pronte=3, commessa_emittibile=True,
        ))
        self.assertEqual(motivo, MOTIVO_NON_DETERMINATO)

    # 3. Nessuna riga pronta perché non approvate.
    def test_righe_non_approvate(self) -> None:
        motivo, testo = classifica_gruppo_non_servito(_foto(
            n_righe=4, n_non_approvate=4,
        ))
        self.assertEqual(motivo, MOTIVO_RIGHE_NON_APPROVATE)
        self.assertIn("4", testo)

    # 3-bis. Concordanza al singolare: i conteggi valgono spesso 1.
    def test_concordanza_singolare(self) -> None:
        _, testo = classifica_gruppo_non_servito(_foto(
            n_righe=1, n_pronte=1, commessa_emittibile=False, stato_commessa="BOZZA",
        ))
        self.assertIn("1 attività pronta in attesa", testo)
        _, testo_non_appr = classifica_gruppo_non_servito(_foto(
            n_righe=1, n_non_approvate=1,
        ))
        self.assertIn("non è ancora approvata", testo_non_appr)

    # 4. Approvate ma senza tipo documento fiscale (il lotto lo richiede).
    def test_tipo_doc_mancante(self) -> None:
        motivo, _ = classifica_gruppo_non_servito(_foto(
            n_righe=2, n_senza_tipo_doc=2,
        ))
        self.assertEqual(motivo, MOTIVO_TIPO_DOC_MANCANTE)

    # 5. Competenza oltre il bound: il consiglio pratico (la selezione è
    #    cumulativa: si rilancia sul mese più recente) fa parte del messaggio.
    def test_fuori_competenza_suggerisce_il_mese_recente(self) -> None:
        motivo, testo = classifica_gruppo_non_servito(_foto(
            n_righe=2, n_fuori_competenza=2,
        ))
        self.assertEqual(motivo, MOTIVO_FUORI_COMPETENZA)
        self.assertIn("cumulativa", testo)

    # 6. Tutte già emesse: il gruppo è stato preso da un giro precedente.
    def test_gia_emesse(self) -> None:
        motivo, _ = classifica_gruppo_non_servito(_foto(n_righe=3, n_emesse=3))
        self.assertEqual(motivo, MOTIVO_GIA_EMESSE)

    # 6-bis. Le annullate non contano come lavoro mancante: 3 emesse + 1
    #        annullata = gruppo interamente evaso, non «nessuna candidabile».
    def test_gia_emesse_con_annullate(self) -> None:
        motivo, testo = classifica_gruppo_non_servito(_foto(
            n_righe=4, n_emesse=3, n_annullate=1,
        ))
        self.assertEqual(motivo, MOTIVO_GIA_EMESSE)
        self.assertIn("annullate", testo)

    # 6-ter. Rifiutate ≠ «non ancora approvate»: la rifiutata non è in attesa
    #        di nessuno, e il messaggio non deve dire di aspettare.
    def test_rifiutate_distinte_dalle_non_approvate(self) -> None:
        motivo, testo = classifica_gruppo_non_servito(_foto(
            n_righe=2, n_rifiutate=2,
        ))
        self.assertEqual(motivo, MOTIVO_RIGHE_RIFIUTATE)
        self.assertIn("rifiutate", testo)

    # 6-quater. Gruppo interamente annullato.
    def test_tutte_annullate(self) -> None:
        motivo, _ = classifica_gruppo_non_servito(_foto(n_righe=2, n_annullate=2))
        self.assertEqual(motivo, MOTIVO_RIGHE_ANNULLATE)

    # 7. Più cause insieme: vince la TESTATA. Con righe pronte il blocco è lì,
    #    e dire «alcune righe non sono approvate» manderebbe l'operatore a
    #    sistemare la cosa sbagliata.
    def test_priorita_testata_sopra_le_righe(self) -> None:
        motivo, _ = classifica_gruppo_non_servito(_foto(
            n_righe=8, n_pronte=5, n_non_approvate=3,
            commessa_emittibile=False, stato_commessa="BOZZA",
        ))
        self.assertEqual(motivo, MOTIVO_COMMESSA_NON_EMITTIBILE)


class MessaggioGruppiNonServitiTests(SimpleTestCase):

    # 8. Un solo gruppo: forma singolare, niente «1 gruppi su 1».
    def test_messaggio_singolo_gruppo(self) -> None:
        spiegazioni = spiega_gruppi_non_serviti([_foto(
            n_righe=5, n_pronte=5, commessa_emittibile=False,
            stato_commessa="BOZZA", commessa_codice="CMM-108",
        )])
        msg = messaggio_gruppi_non_serviti(spiegazioni, totale_richiesti=1)
        self.assertIn("il gruppo richiesto non è fatturabile", msg)
        self.assertIn("CMM-108", msg)

    # 9. Molti gruppi: i primi tre per esteso, il resto contato (un toast non
    #    regge un elenco: il dettaglio resta nell'esito strutturato).
    def test_messaggio_molti_gruppi_tronca_e_conta(self) -> None:
        spiegazioni = spiega_gruppi_non_serviti([
            _foto(commessa_codice=f"CMM-{i}", n_righe=1, n_emesse=1)
            for i in range(5)
        ])
        msg = messaggio_gruppi_non_serviti(spiegazioni, totale_richiesti=7)
        self.assertIn("5 gruppi su 7", msg)
        self.assertIn("e altri 2", msg)
        self.assertIn("CMM-0", msg)
        self.assertNotIn("CMM-4", msg)
