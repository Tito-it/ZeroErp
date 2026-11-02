# ------------------------------------------------------------
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: P-10 del brief `brief-db-il-trattenuto-passa-lo-stesso` §8.4 — il
#        RIEPILOGO della lista gruppi ESCLUDE i gruppi trattenuti da un lotto in
#        gioco e ne DICHIARA il numero, mentre il totale di PERIMETRO non cambia.
#
# ⭐ PERCHE' STA IN DJANGO E NON IN pgTAP: quel numero non viene da una vista, lo
#    calcola una query del backend (`get_dash_competenza_gruppi_accessori`, che
#    tiene i due perimetri — `filtrato` per il riepilogo, `base` per le facet e
#    il conteggio di perimetro). Il presidio va dove sta il calcolo.
#
# ⛔ PERCHE' SERVE, ed e' il difetto da cui nasce il cantiere: la card diceva
#    «4 da emettere» mentre la lista sotto ne mostrava 3, perche' una riga era
#    trattenuta da un lotto vivo. Due cifre sulla stessa schermata, entrambe
#    plausibili, che descrivevano perimetri diversi — e l'operatore decideva
#    sulla piu' grande. ⚠️ Un numero che cala senza dire di quanto e' un numero
#    che non si sa leggere: per questo si asserisce ANCHE `n_gruppi_trattenuti`,
#    e non solo che il totale sia sceso.
#
# ⭐ IL CASO SI COSTRUISCE, non si cerca fra i lotti di oggi. Su un database
#    ricostruito da zero — cioe' in CI — un testimone «trovato» non esiste, e il
#    test diventerebbe verde smettendo di verificare (AGENTS.md, regola zero).
#    Qui si prende un gruppo LIBERO e lo si fa PRENDERE IN CARICO da un lotto
#    in gioco: il verdetto nasce dalla mossa, e le due misure attorno a essa
#    sono l'una il contrario dell'altra.
#
# ⚠️ IL LEGAME DI COMPETENZA E' CUMULATIVO e non un'uguaglianza: un lotto di
#    settembre trattiene anche agosto, non ottobre. La vista
#    `vw_documenti_trattenuti_da_lotto` non conosce la competenza della riga che
#    la interroga — lega chi aggancia, con `lotto_competenza_mese >= competenza`.
#    Per questo il gruppo si cerca a competenza MINORE O UGUALE a quella del
#    lotto: con un `=` copiato dal LATERAL dell'esito il caso non si formerebbe
#    e il test passerebbe a vuoto.
#
# ⚠️ RICHIEDE IL DB VERO, opt-in `ZEROERP_TEST_DB_E2E=1` (accesa in CI).
#    NON LASCIA NIENTE: tutto in transazione annullata.
#
# Indice test:
#   1. test_il_riepilogo_esclude_e_dichiara_il_trattenuto
# ------------------------------------------------------------

from __future__ import annotations

from datetime import date
from unittest import TestCase
from uuid import uuid4

from django.db import connection, transaction

from apps.core.tests.db_e2e import apri_contesto_operatore, richiedi_db_provvisto
from apps.vendite.db.vendite_repository import (
    STATI_ESECUZIONE_LOTTO,
    STATO_ESECUZIONE_ESCLUSO,
    VenditeRepository,
)

# ⛔ UNO STATO QUALSIASI PURCHE' NON `ESCLUSO`, e si prende dal VOCABOLARIO
#    invece di cablare `'PENDING'`: la sola condizione che
#    `vw_documenti_trattenuti_da_lotto` pone sull'esito e' `<> 'ESCLUSO'`.
#    ⭐ Scritto cosi' il test dice la REGOLA e non un esempio di essa, e il
#    giorno che il vocabolario cambia segue il modello invece di rompersi su
#    una stringa che nessuno collega a questo file.
_ESITO_CHE_TRATTIENE = next(
    s for s in STATI_ESECUZIONE_LOTTO if s != STATO_ESECUZIONE_ESCLUSO
)


class RiepilogoEscludeTrattenuti(TestCase):
    """Il riepilogo toglie i trattenuti e dice quanti; il perimetro no."""

    @classmethod
    def setUpClass(cls) -> None:
        super().setUpClass()
        richiedi_db_provvisto()

    # Scopo: il GRUPPO su cui misurare — libero, cioe' non gia' trattenuto.
    # ⚠️ QUESTO SI TROVA E NON SI COSTRUISCE, ed e' una scelta dichiarata: un
    #    gruppo e' l'innesto di commessa, attivita' e documento in una
    #    competenza, cioe' una fixture di dominio grande quanto un cantiere a
    #    parte. E' MATERIALE su cui misurare, non il fenomeno da provare — se
    #    non ce n'e' nessuno non c'e' neanche una cella da guardare, e lo `skip`
    #    dice il vero. ⛔ Il fenomeno — il lotto che trattiene — quello si
    #    fabbrica, ed e' il metodo qui sotto.
    def _gruppo_libero(self, cur) -> tuple[str, date, str]:
        # ⛔ `classe_emittibilita = 'PRONTA'`, e non basta «non trattenuto».
        #    `vw_commesse_attivita_emittibilita` decide con una CASE ORDINATA:
        #    EMESSA, ANNULLATA, RIFIUTATA e NON_APPROVATA si fermano PRIMA del
        #    ramo TRATTENUTA. Su un gruppo in uno di quegli stati il lotto puo'
        #    anche prenderselo — la classe non cambia, il verdetto non si
        #    accende e il test misurerebbe zero differenze credendo di aver
        #    provato qualcosa.
        # ⇒ PRONTA e' esattamente «diventerebbe TRATTENUTA se un lotto vivo lo
        #    prendesse»: e' il solo materiale su cui la mossa ha effetto.
        cur.execute(
            """
            SELECT g.gruppo_key, g.competenza_mese, g.stadio
              FROM vendite.vw_dash_competenza_gruppi g
              JOIN vendite.vw_commesse_attivita_emittibilita e
                ON e.gruppo_key = g.gruppo_key
               AND e.competenza_mese = g.competenza_mese
             WHERE g.emissione_blocco_reason IS NULL
               AND g.stadio IS NOT NULL
               AND e.classe_emittibilita = 'PRONTA'
             ORDER BY g.competenza_mese DESC
             LIMIT 1
            """
        )
        riga = cur.fetchone()
        if riga is None:
            self.skipTest(
                "nessun gruppo PRONTA: non c'e' materiale su cui la mossa "
                "avrebbe effetto"
            )
        return str(riga[0]), riga[1], str(riga[2])

    # Scopo: ⭐ IL LOTTO IN GIOCO SI FABBRICA, e qui sta la correzione che vale.
    # 🔴 La prima stesura lo CERCAVA (`vw_lotti_fase WHERE in_gioco`), e il
    #    2026-09-09 e' bastato mezz'ora per vedere il difetto: fra due
    #    esecuzioni i lotti vivi erano spariti — vengono chiusi e annullati di
    #    continuo. Con la ricerca il test avrebbe fatto `skipTest` e detto «ok»,
    #    cioe' sarebbe diventato verde smettendo di verificare. Su un database
    #    ricostruito da zero — la CI — non ne troverebbe MAI uno.
    # ⇒ E' esattamente cio' che il brief vieta al §8.4: «i casi si costruiscono,
    #    non si cercano fra i lotti di oggi».
    # ⚠️ Tipo documento ed emittente si prendono da un lotto esistente: sono
    #    riferimenti obbligatori e sceglierli a mano significherebbe indovinare
    #    due FK: qui non sono il soggetto della prova, sono l'impalcatura.
    def _crea_lotto_in_gioco(self, cur, competenza: date) -> int:
        # ⛔ SI CHIEDE LA PROPRIETA', NON IL NOME. `vw_lotti_fase` deriva
        #    `in_gioco` da `NOT congela_fiscale`: qualunque stato che non
        #    congela va bene, e nominare `DRAFT` legherebbe il test a UNO dei
        #    due stati che oggi soddisfano la regola invece che alla regola.
        cur.execute(
            "SELECT id FROM config.stati_doc_fiscale "
            "WHERE NOT congela_fiscale ORDER BY id LIMIT 1"
        )
        stato = cur.fetchone()
        cur.execute(
            "SELECT tipo_doc_fiscale_id, emittente_soggetto_ruolo_id "
            "FROM vendite.fatturazione_lotti ORDER BY id LIMIT 1"
        )
        impalcatura = cur.fetchone()
        if stato is None or impalcatura is None:
            self.skipTest(
                "manca uno stato non congelante a catalogo, o un lotto da cui "
                "prendere tipo documento ed emittente: non e' fabbricabile"
            )
        cur.execute(
            """
            INSERT INTO vendite.fatturazione_lotti
                        (codice, competenza_mese, stato_doc_fiscale_id,
                         tipo_doc_fiscale_id, emittente_soggetto_ruolo_id)
                 VALUES (%s, %s, %s, %s, %s)
              RETURNING id
            """,
            # ⚠️ CODICE UNICO PER ESECUZIONE e non un letterale fisso:
            #    `uq_fatturazione_lotti_codice` e' unico, e un residuo di un
            #    giro precedente — o due esecuzioni in parallelo — farebbero
            #    fallire l'INSERT con un errore che parla di un duplicato
            #    invece che del presidio. Il test non deve dipendere da cosa
            #    c'e' gia' nel database: e' la stessa regola per cui il caso si
            #    costruisce invece di cercarlo.
            [f"LTF-TEST-P10-{uuid4().hex[:8]}", competenza,
             stato[0], impalcatura[0], impalcatura[1]],
        )
        creato = cur.fetchone()
        assert creato is not None, "INSERT ... RETURNING senza riga"
        lotto_id = int(creato[0])
        # ⛔ Si VERIFICA che sia davvero in gioco invece di darlo per fatto: se
        #    un domani il default dello stato cambiasse, il test misurerebbe un
        #    lotto che non trattiene e tutte le differenze verrebbero zero —
        #    verde, e per la ragione sbagliata.
        cur.execute(
            "SELECT in_gioco FROM vendite.vw_lotti_fase WHERE lotto_id = %s",
            [lotto_id],
        )
        fase = cur.fetchone()
        self.assertIsNotNone(
            fase, "il lotto appena creato non compare in vw_lotti_fase",
        )
        assert fase is not None
        self.assertTrue(
            fase[0],
            "il lotto appena creato non risulta IN GIOCO: senza, non trattiene "
            "niente e la prova non avrebbe soggetto",
        )
        return lotto_id

    # Scopo: le tre cifre che il contorno della lista produce per quella cella.
    def _misura(self, competenza: date, stadio: str) -> tuple[int, int, int]:
        acc = VenditeRepository().get_dash_competenza_gruppi_accessori(
            competenza_mese=competenza, stadio=stadio,
        )
        return (
            int(acc["riepilogo"]["n_gruppi"]),
            int(acc["riepilogo"]["n_gruppi_trattenuti"]),
            int(acc["n_gruppi_perimetro"]),
        )

    # 1) ⭐ Una mossa sola, tre verifiche — e la terza e' il contrario delle
    #    prime due: se il perimetro calasse insieme al riepilogo, il numero
    #    «quanti ne ho in tutto» smetterebbe di essere l'altro numero e le due
    #    cifre tornerebbero a dire la stessa cosa, che e' il difetto di partenza.
    def test_il_riepilogo_esclude_e_dichiara_il_trattenuto(self) -> None:
        with transaction.atomic():
            with connection.cursor() as cur:
                apri_contesto_operatore(cur)
                gruppo_key, competenza, stadio = self._gruppo_libero(cur)
                # ⭐ Il lotto nasce sulla STESSA competenza del gruppo: la
                #    regola e' cumulativa (`lotto >= riga`), e l'uguaglianza e'
                #    il caso piu' stretto che la soddisfa.
                lotto_id = self._crea_lotto_in_gioco(cur, competenza)

                prima_n, prima_trat, prima_perim = self._misura(competenza, stadio)

                # ⭐ LA MOSSA — e va fatta sugli ESITI, non sul perimetro.
                # ⛔ La prima stesura scriveva in `fatturazione_lotti_gruppi` e
                #    il test falliva senza che il verdetto si accendesse: e' il
                #    perimetro DICHIARATO, cioe' cosa il lotto si propone di
                #    lavorare. `vw_documenti_trattenuti_da_lotto` legge invece
                #    `fatturazione_lotti_esiti` — cosa il lotto ha PRESO IN
                #    CARICO — con `stato_esecuzione <> 'ESCLUSO'` e il lotto
                #    `in_gioco`. Sono due domande diverse, e a trattenere e'
                #    la seconda: un documento dichiarato ma mai preso resta
                #    disponibile per un altro giro.
                # ⚠️ Si scrivono ENTRAMBE perche' e' la forma che un lotto vero
                #    produce — dichiara e poi prende — e un caso costruito a
                #    meta' proverebbe una situazione che il sistema non genera.
                cur.execute(
                    """
                    INSERT INTO vendite.fatturazione_lotti_gruppi
                                (lotto_id, gruppo_key)
                         VALUES (%s, %s)
                    ON CONFLICT ON CONSTRAINT uq_fatturazione_lotti_gruppi_lotto_key
                    DO NOTHING
                    """,
                    [lotto_id, gruppo_key],
                )
                cur.execute(
                    """
                    INSERT INTO vendite.fatturazione_lotti_esiti
                                (lotto_id, gruppo_key, stato_esecuzione)
                         VALUES (%s, %s, %s)
                    """,
                    [lotto_id, gruppo_key, _ESITO_CHE_TRATTIENE],
                )

                dopo_n, dopo_trat, dopo_perim = self._misura(competenza, stadio)

            # ⛔ IL ROLLBACK ESPLICITO, e NON e' una formalita'.
            # 🔴 Senza questa riga il test SCRIVE sul database di sviluppo:
            #    `transaction.atomic()` dentro una `unittest.TestCase` — che non
            #    e' la `TestCase` di Django e non avvolge niente — COMMITTA se il
            #    blocco esce senza eccezione. Costato il 2026-09-09: un giro
            #    verde ha lasciato in giro un lotto `LTF-TEST-P10` vivo, che
            #    tratteneva un documento vero e lo faceva sparire dalla card.
            # ⚠️ E il difetto era invisibile finche' il test FALLIVA — li'
            #    l'eccezione annullava tutto. Si e' visto al primo verde: un
            #    presidio che sporca solo quando passa e' il modo peggiore.
            # ⭐ E' l'idioma di casa: `test_lotto_gruppi_ordine` e
            #    `test_pull_tutte_fallite_scrittura_reale` fanno cosi'.
            transaction.set_rollback(True)

            # ⚠️ Prima di asserire le differenze si controlla che la mossa abbia
            #    prodotto un effetto: senza, un predicato che non aggancia mai
            #    renderebbe tutte le uguaglianze vere e il test verde a vuoto.
            self.assertEqual(
                dopo_trat, prima_trat + 1,
                "il riepilogo non DICHIARA il gruppo trattenuto: un totale che "
                "cala senza dire di quanto e' un numero che non si sa leggere",
            )
            self.assertEqual(
                dopo_n, prima_n - 1,
                "il riepilogo non ESCLUDE il gruppo trattenuto: la card "
                "tornerebbe a contare lavoro che l'operatore non puo' prendere",
            )
            # ⛔ Il conteggio di perimetro legge l'insieme `base` e NON deve
            #    muoversi: risponde a «quanti ne ho in questa cella», non a
            #    «quanti ne posso prendere». Farlo calare insieme all'altro e'
            #    la scorciatoia che riporta le due cifre a dire la stessa cosa.
            self.assertEqual(
                dopo_perim, prima_perim,
                "il totale di perimetro e' calato: e' l'ALTRO numero, e deve "
                "restare quello di tutta la cella",
            )
