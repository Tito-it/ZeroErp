# ------------------------------------------------------------
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: L'ordine di apertura della scheda «Presi in carico» — i documenti
#        FALLITI in cima — provato su un caso COSTRUITO, non sui dati di oggi.
#
# 🔴 PERCHE' ESISTE, ed e' un difetto misurato il 2026-09-07. La clausola era
#    `ORDER BY (stato_esecuzione = 'ERRORE') DESC`, e sembra dire quello che
#    serve. Ma in PostgreSQL `DESC` implica `NULLS FIRST`, e su un documento MAI
#    TENTATO il confronto vale `NULL` — quindi i mai guardati finivano SOPRA i
#    falliti. La scheda prometteva «quale documento non e' passato» e in cima
#    metteva quelli che nessuno aveva ancora provato.
#
# ⚠️ E con l'unione perimetro+esiti il caso e' la NORMA, non un'eccezione: ogni
#    documento dichiarato e non ancora tentato ha esito `NULL`. Su un lotto con
#    quaranta documenti, quello caduto finiva in fondo — invisibile senza
#    scorrere, e senza nessun errore da nessuna parte.
#
# ⭐ IL CASO SI COSTRUISCE, non si cerca — E LO STATO DI PARTENZA ANCHE.
# 🔴 La prima stesura si limitava a marcare un documento e a dare per scontato
#    che gli altri fossero mai tentati. E' durata poche ore: il 2026-09-07 e'
#    girato il primo lotto vero, i suoi documenti hanno preso un esito, e il
#    test ha cominciato a fallire su un ordine CORRETTO — perche' fra due
#    documenti in ERRORE vince il riferimento, e quello marcato non era piu' il
#    primo. Un test che dipende dalla popolazione di oggi e' esattamente cio'
#    che AGENTS.md vieta.
# ⇒ Adesso lo stato di partenza si fabbrica: si cancellano gli esiti del lotto
#    dentro la transazione annullata, cosi' la mescolanza «uno fallito, gli
#    altri mai tentati» esiste per costruzione e non per fortuna.
#
# ⚠️ RICHIEDE IL DB VERO, opt-in `ZEROERP_TEST_DB_E2E=1` (accesa in CI).
#    NON LASCIA NIENTE: tutto in transazione annullata.
#
# Indice test:
#   1. test_il_fallito_sta_in_cima_anche_con_documenti_mai_tentati
# ------------------------------------------------------------

from __future__ import annotations

from unittest import TestCase

from django.db import connection, transaction

from apps.core.tests.db_e2e import apri_contesto_operatore, richiedi_db_provvisto
from apps.vendite.services.vendite_service import fn_list_lotto_gruppi


class LottoGruppiOrdineDiApertura(TestCase):
    """I falliti in cima, anche in mezzo ai mai tentati."""

    @classmethod
    def setUpClass(cls) -> None:
        super().setUpClass()
        richiedi_db_provvisto()

    # Scopo: un lotto che dichiara ALMENO DUE documenti nel perimetro — con uno
    #        solo la mescolanza «uno fallito, gli altri mai tentati» non esiste.
    # ⚠️ Non si chiede che siano MAI TENTATI: quello lo fabbrica il test.
    # ⚠️ Le GUC prima di tutto: senza contesto operatore le tabelle sotto RLS
    #        rispondono zero righe e il test si spegnerebbe da solo credendo di
    #        non avere materiale.
    def _lotto_con_piu_documenti(self) -> tuple[int, list[str]]:
        with connection.cursor() as cur:
            apri_contesto_operatore(cur)
            cur.execute(
                """
                SELECT lg.lotto_id, array_agg(lg.gruppo_key ORDER BY lg.gruppo_key)
                FROM vendite.fatturazione_lotti_gruppi lg
                JOIN vendite.fatturazione_lotti l ON l.id = lg.lotto_id
                GROUP BY lg.lotto_id
                HAVING count(*) >= 2
                ORDER BY lg.lotto_id DESC
                LIMIT 1
                """
            )
            riga = cur.fetchone()
        if riga is None:
            self.skipTest(
                "nessun lotto con almeno due documenti nel perimetro: la "
                "mescolanza «uno fallito, gli altri mai tentati» non e' "
                "costruibile"
            )
        return int(riga[0]), [str(k) for k in riga[1]]

    # 1) ⭐ Si marca UNO solo, e dev'essere il primo della lista.
    def test_il_fallito_sta_in_cima_anche_con_documenti_mai_tentati(self) -> None:
        with transaction.atomic():
            lotto_id, chiavi = self._lotto_con_piu_documenti()
            # ⚠️ Si sceglie l'ULTIMO in ordine di chiave, non il primo: se
            #    l'ordinamento non funzionasse, un documento gia' primo per
            #    alfabeto passerebbe il test per caso.
            caduto = chiavi[-1]
            with connection.cursor() as cur:
                # ⭐ LO STATO DI PARTENZA SI FABBRICA: nessun esito su questo
                #    lotto. Senza, un giro vero passato di qui lascia documenti
                #    gia' in ERRORE, e fra due falliti vince il riferimento —
                #    il test fallirebbe su un ordine giusto.
                # ⛔ La cancellazione vive nella transazione annullata come tutto
                #    il resto: non tocca niente.
                cur.execute(
                    "DELETE FROM vendite.fatturazione_lotti_esiti WHERE lotto_id = %s",
                    [lotto_id],
                )
                # ⚠️ SI CHIAMA COME TABLE FUNCTION, e non e' uno stile: dal
                #    `20260909-20` `fn_segna_esito_gruppo_lotto` ritorna
                #    `TABLE(marcati, usciti, fuori_perimetro)`, non piu' uno
                #    scalare. In contesto SELECT scalare il record esce INTERO
                #    e `fetchone()[0]` restituisce la stringa `('1','0','0')` —
                #    che non e' 1 e non lo sara' mai, ma nemmeno solleva.
                # ⭐ Cosi' e' anche il modo in cui la chiama la produzione
                #    (`pipeline_repository.list_...`, `FROM vendite.fn_...`):
                #    il test esercita la stessa forma del chiamante vero.
                cur.execute(
                    """
                    SELECT marcati FROM vendite.fn_segna_esito_gruppo_lotto(
                        %s, 'ERRORE', %s, NULL, 'E_PULL_COMMESSA',
                        'Prova: documento caduto')
                    """,
                    [lotto_id, caduto],
                )
                scritti = cur.fetchone()[0]
            self.assertEqual(
                scritti, 1,
                "la marcatura non ha scritto: senza il caso costruito questo "
                "test non prova niente",
            )

            righe = fn_list_lotto_gruppi(lotto_id=lotto_id)["results"]
            self.assertGreaterEqual(len(righe), 2, "serve la mescolanza")
            # ⛔ IL FALLITO E' IL PRIMO. Senza `NULLS LAST` qui uscivano prima
            #    tutti i mai tentati, perche' `NULL = 'ERRORE'` vale NULL e
            #    `DESC` mette i NULL davanti.
            self.assertEqual(
                righe[0]["gruppo_key"], caduto,
                "il documento fallito non e' in cima: l'ordine di apertura "
                "della scheda promette «quale documento non e' passato» e sta "
                "mostrando per primi quelli che nessuno ha ancora provato.",
            )
            self.assertEqual(righe[0]["stato_esecuzione"], "ERRORE")
            # E gli altri restano quello che sono: mai tentati, non «riusciti».
            self.assertTrue(
                all(r["stato_esecuzione"] is None for r in righe[1:]),
                "gli altri documenti non erano mai stati tentati: un esito "
                "diverso da `None` vorrebbe dire che il caso costruito non e' "
                "quello che si crede",
            )
            transaction.set_rollback(True)
