# ------------------------------------------------------------
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Presidio dei DOCUMENTI PRESI IN CARICO da un lotto — la lista che
#        mostra anche quelli che una fattura non sono mai diventati
#        (`fn_list_lotto_gruppi` + `VenditeRepository.list_lotto_gruppi`).
#
# ⛔ PERCHE' ESISTE, ed e' un caso vero (lotto LTF-0009578, 2026-09-06). Il
#    lotto prendeva in carico tre documenti e ne fatturava due. Il terzo cadeva
#    PRIMA di diventare fattura, quindi non aveva nessuna riga in
#    `fatturazione_lotti_fatture` a cui appendersi: spariva dalla scheda, e
#    nella competenza restava fra quelli da emettere senza un segno.
#
# ⚠️ Tutti i test girano su query MOCKATE: provano la forma della domanda e la
#    proiezione della risposta, non che il database risponda. Il giro sul
#    database vero e' stato fatto a mano in transazione annullata, ed e'
#    l'unico modo di provare che la marcatura si veda: qui il repository non
#    parla con nessuno.
#
# Indice test:
#   1. test_il_cancello_di_scope_e_la_testata
#   2. test_l_identita_si_legge_dalla_vista_non_si_ricostruisce
#   3. test_default_mette_i_falliti_in_cima
#   4. test_ordinamento_fuori_whitelist_rifiutato
#   5. test_stato_esecuzione_fuori_vocabolario_rifiutato
#   6. test_filtro_stato_entra_come_parametro
#   7. test_mapping_consegna_esito_identita_e_commessa
#   8. test_esito_assente_resta_none
#   9. test_commessa_multipla_non_si_sceglie
#  10. test_nessun_flag_sul_perimetro_nella_risposta
#  11. test_export_non_pagina
#  12. test_ogni_campo_sorgente_di_catalogo_e_una_chiave_della_riga
#  13. test_pagina_vuota_ha_un_conteggio_di_riserva
#  14. test_il_motivo_del_blocco_si_legge_dalla_vista_non_si_compone
#  15. test_i_trascinati_si_leggono_dalla_vista
# ------------------------------------------------------------

from __future__ import annotations

from datetime import UTC, datetime
from unittest.mock import patch

from django.test import SimpleTestCase

from apps.core.services.error_manager import ServiceError
from apps.vendite.db.vendite_repository import (
    STATO_ESECUZIONE_ERRORE,
    VenditeRepository,
)
from apps.vendite.services.vendite_service import fn_list_lotto_gruppi


# Riga finta nella forma che `fetch_paged_with_total` consegna: un DIZIONARIO,
# non una tupla. ⭐ E' il motivo per cui questa lista non ha il presidio di
# larghezza della sorella dei gruppi in competenza — l'accesso e' per NOME, e
# una colonna inserita a meta' proiezione non sposta niente.
def _riga(**override):
    riga = {
        "gruppo_key": "ORDINE_VENDITA:01a06ce4-b46a-7a49-a72f-c07c29de47bb",
        "stato_esecuzione": "ERRORE",
        "errore_codice": "E_PULL_COMMESSA",
        "errore_messaggio": "ROOT source mancante per commessa 34137",
        "errore_quando": datetime(2026, 9, 6, 17, 12, tzinfo=UTC),
        "riferimento": "ORD0036005",
        "tipo_gruppo": "ORDINE_VENDITA",
        "documento_apribile": True,
        "documento_id": 43927,
        "commessa_id": 34137,
        "commessa_codice": "CMM-PGTAPEF202-2026-000000004",
        "commesse_n": 1,
        # ═══ L'uscita dal giro (2026-09-08) ═══
        # Il documento e' ancora DENTRO: le tre colonne dell'uscita sono vuote.
        "uscita_motivo": None,
        "uscita_quando": None,
        "uscita_da": None,
        # ⚠️ `None` sul blocco = l'azione e' AMMESSA su questa riga (e' in
        #    ERRORE, che e' la sola condizione da cui si esce — D-4). Coerente
        #    con `n_trascinati` valorizzato: il conteggio si chiede solo dove
        #    l'azione e' viva.
        "uscita_blocco_reason": None,
        "uscita_blocco_reason_key": None,
        "n_trascinati": 0,
    }
    riga.update(override)
    return riga


class LottoGruppiRepositoryTests(SimpleTestCase):
    # 1) 🔒 `fatturazione_lotti_gruppi` NON ha RLS, `fatturazione_lotti` si':
    #    leggere la figlia da sola sarebbe fail-open. Il JOIN sulla CTE del
    #    lotto E' il cancello, e vale anche per il conteggio — un totale senza
    #    cancello direbbe «3 documenti» mostrandone zero.
    @patch("apps.vendite.db.vendite_repository.fetch_paged_with_total")
    def test_il_cancello_di_scope_e_la_testata(self, mock_fetch):
        mock_fetch.return_value = ([], 0)
        VenditeRepository().list_lotto_gruppi(lotto_id=10657, limit=25, offset=0)
        sql = mock_fetch.call_args.args[0]
        self.assertIn("FROM vendite.fatturazione_lotti l", sql)
        # ⚠️ ENTRAMBE le figlie passano dalla CTE del lotto: e' li' che vive il
        #    cancello, e una sola delle due agganciata sarebbe fail-open a meta'.
        self.assertIn("JOIN lotto ON lotto.id = lg.lotto_id", sql)
        self.assertIn("JOIN lotto ON lotto.id = le.lotto_id", sql)

    # 2) ⛔ La `gruppo_key` NON si spezza in Python. La derivazione da chiave a
    #    documento vive in `fn_build_gruppo_fatturabile_key` /
    #    `vw_dash_competenza_gruppi`: rifarla qui sarebbe la seconda sede della
    #    stessa regola, e il giorno in cui la chiave cambia forma le due
    #    dissentirebbero in silenzio.
    # ⚠️ Il legame passa dal MESE del lotto: senza, un gruppo omonimo di un
    #    altro mese porterebbe il nome sbagliato.
    @patch("apps.vendite.db.vendite_repository.fetch_paged_with_total")
    def test_l_identita_si_legge_dalla_vista_non_si_ricostruisce(self, mock_fetch):
        mock_fetch.return_value = ([], 0)
        VenditeRepository().list_lotto_gruppi(lotto_id=10657, limit=25, offset=0)
        sql = mock_fetch.call_args.args[0]
        self.assertIn("FROM vendite.vw_dash_competenza_gruppi g", sql)
        self.assertIn("JOIN lotto ON lotto.competenza_mese = g.competenza_mese", sql)
        # ⛔ Nessuno split della chiave: né in SQL né in Python.
        self.assertNotIn("split_part", sql)
        self.assertNotIn("fn_build_gruppo_fatturabile_key", sql)

    # 3) ⭐ IL DEFAULT NON E' ALFABETICO, ed e' la domanda con cui la scheda si
    #    apre: «quale documento non e' passato?». `ERRORE` in ordine alfabetico
    #    verrebbe DOPO `COMPLETED`, cioe' il caso che interessa finirebbe in
    #    fondo — su un lotto lungo, nell'ultima pagina.
    # ⛔ E il valore viaggia come PARAMETRO, non come letterale nell'SQL: una
    #    stringa scritta a mano dentro la query sarebbe la seconda sede del
    #    vocabolario, e il giorno in cui il CHECK rinomina il valore
    #    l'ordinamento smetterebbe di funzionare SENZA fallire — le righe rosse
    #    tornerebbero in fondo e nessuno se ne accorgerebbe.
    @patch("apps.vendite.db.vendite_repository.fetch_paged_with_total")
    def test_default_mette_i_falliti_in_cima(self, mock_fetch):
        mock_fetch.return_value = ([], 0)
        VenditeRepository().list_lotto_gruppi(lotto_id=10657, limit=25, offset=0)
        sql, params = mock_fetch.call_args.args[0], mock_fetch.call_args.args[1]
        # 🔴 `NULLS LAST` e' la meta' che mancava: `DESC` implica `NULLS FIRST`
        #    e `NULL = 'ERRORE'` vale NULL, quindi senza di esso i documenti MAI
        #    TENTATI finivano sopra quelli falliti — l'ordinamento prometteva il
        #    contrario di quello che faceva.
        self.assertIn("ORDER BY (stato_esecuzione = %s) DESC NULLS LAST", sql)
        self.assertNotIn("'ERRORE'", sql)
        # Il valore e' quello del vocabolario, non una stringa a caso.
        self.assertIn(STATO_ESECUZIONE_ERRORE, params)
        # Tiebreak sulla chiave e non sul riferimento: quello puo' non
        # risolversi, e senza un tiebreak stabile la paginazione salta righe.
        self.assertIn("gruppo_key ASC", sql)

    # 13) ⚠️ IL FALLBACK DEL CONTEGGIO. `COUNT(*) OVER ()` non puo' dire il
    #     totale su una pagina VUOTA: senza il conteggio di riserva, una pagina
    #     stantia — l'elenco si e' accorciato sotto le mani di chi guarda —
    #     tornerebbe `count = 0`, e la scheda direbbe «nessun documento preso in
    #     carico» su un lotto che ne ha tre. ⛔ Qui non c'e' il clamp dei
    #     cruscotti: la lista del drawer serve la pagina CHIESTA.
    @patch("apps.vendite.db.vendite_repository.fetch_paged_with_total")
    def test_pagina_vuota_ha_un_conteggio_di_riserva(self, mock_fetch):
        mock_fetch.return_value = ([], 7)
        VenditeRepository().list_lotto_gruppi(lotto_id=10657, limit=25, offset=50)
        kwargs = mock_fetch.call_args.kwargs
        conteggio = kwargs.get("fallback_count_sql")
        self.assertIsNotNone(conteggio)
        self.assertEqual(kwargs.get("offset"), 50)
        # ⛔ E CONTA LA STESSA CTE che la lista consegna, non un perimetro
        #    «uguale»: il frammento e' condiviso, non riscritto. Due copie
        #    divergerebbero al primo che ne tocca una, e in modo MUTO — il
        #    paginatore direbbe un totale che non descrive le righe.
        self.assertTrue(conteggio.rstrip().endswith("SELECT COUNT(*) FROM gruppi"))
        # ⚠️ La prova che e' davvero lo stesso: tutto cio' che precede il
        #    `SELECT COUNT` compare identico nella query di pagina.
        perimetro = conteggio.rsplit("SELECT COUNT(*) FROM gruppi", 1)[0]
        self.assertIn(perimetro.rstrip(), mock_fetch.call_args.args[0])

    # 6) Il filtro esito viaggia come PARAMETRO, mai interpolato.
    @patch("apps.vendite.db.vendite_repository.fetch_paged_with_total")
    def test_filtro_stato_entra_come_parametro(self, mock_fetch):
        mock_fetch.return_value = ([], 0)
        VenditeRepository().list_lotto_gruppi(
            lotto_id=10657, stato_esecuzione="ERRORE", limit=25, offset=0,
        )
        sql, params = mock_fetch.call_args.args[0], mock_fetch.call_args.args[1]
        self.assertIn("esito.stato_esecuzione = %s", sql)
        self.assertIn("ERRORE", params)
        self.assertNotIn("'ERRORE'", sql.split("ORDER BY")[0])

    # 7) Il mapping consegna le tre cose che servono a chi guarda: com'e'
    #    andata, quale documento e QUALE COMMESSA correggere.
    @patch("apps.vendite.db.vendite_repository.fetch_paged_with_total")
    def test_mapping_consegna_esito_identita_e_commessa(self, mock_fetch):
        mock_fetch.return_value = ([_riga()], 1)
        righe, totale = VenditeRepository().list_lotto_gruppi(
            lotto_id=10657, limit=25, offset=0,
        )
        self.assertEqual(totale, 1)
        riga = righe[0]
        # ⛔ Nessun `id`: la riga e' l'unione di due fatti, non una riga di
        #    tabella. L'identita' e' il documento dentro il lotto.
        self.assertNotIn("id", riga)
        self.assertEqual(riga["gruppo_key"], _riga()["gruppo_key"])
        self.assertEqual(riga["stato_esecuzione"], "ERRORE")
        self.assertEqual(riga["errore_codice"], "E_PULL_COMMESSA")
        self.assertEqual(riga["riferimento"], "ORD0036005")
        self.assertEqual(riga["documento_id"], 43927)
        self.assertEqual(riga["commessa_id"], 34137)
        self.assertTrue(riga["errore_quando"].startswith("2026-09-06T17:12"))

    # 8) ⚠️ `None` = «nessuno l'ha detto», NON «e' andata bene»: e' la verita' di
    #    ogni gruppo che nessun giro ha ancora lavorato. Un `"None"` stringa
    #    sarebbe un esito inventato qui.
    @patch("apps.vendite.db.vendite_repository.fetch_paged_with_total")
    def test_esito_assente_resta_none(self, mock_fetch):
        mock_fetch.return_value = ([_riga(
            stato_esecuzione=None, errore_codice=None,
            errore_messaggio=None, errore_quando=None,
        )], 1)
        righe, _ = VenditeRepository().list_lotto_gruppi(
            lotto_id=10657, limit=25, offset=0,
        )
        for chiave in ("stato_esecuzione", "errore_codice", "errore_messaggio",
                       "errore_quando"):
            self.assertIsNone(righe[0][chiave], chiave)

    # 12) ⛔ OGNI `campo_sorgente` del catalogo dev'essere una chiave della riga
    #     che il repository consegna. La lista ha `vista_sql = NULL`, quindi il
    #     catalogo non puo' pescare i campi da se': li compone questo SELECT, e
    #     se le due parti divergono la colonna **si spunta e resta VUOTA** —
    #     senza che nessun errore lo dica.
    # ⚠️ Il `campo_sorgente` si LEGGE DAL CSV, non si scrive qui: un test che
    #     asserisse le stringhe a mano resterebbe verde proprio nel caso che
    #     dichiara di presidiare (il seed che cambia nome a un campo).
    @patch("apps.vendite.db.vendite_repository.fetch_paged_with_total")
    def test_ogni_campo_sorgente_di_catalogo_e_una_chiave_della_riga(self, mock_fetch):
        from apps.core.tests.test_liste_configurabili_seed import _colonne_attive

        attese = sorted(
            r["campo_sorgente"]
            for r in _colonne_attive("vendite.lotto_gruppi")
            if r["tipo_colonna"] != "azione" and r["campo_sorgente"]
        )
        self.assertTrue(attese, "il catalogo della lista e' vuoto: seed mancante.")

        mock_fetch.return_value = ([_riga()], 1)
        righe, _ = VenditeRepository().list_lotto_gruppi(
            lotto_id=10657, limit=25, offset=0,
        )
        mancanti = [c for c in attese if c not in righe[0]]
        self.assertEqual(
            mancanti, [],
            "campi dichiarati a catalogo che il repository non consegna: la "
            "colonna si spunta e resta vuota a video.",
        )

    # 9) ⛔ Due commesse sullo stesso documento sono AMMESSE per costruzione (la
    #    chiave di un gruppo-documento non contiene la commessa). In quel caso
    #    il backend non ne sceglie una: `commesse_n` dice quante sono, e il
    #    frontend scrive «sono più di una» invece di offrire una scommessa.
    @patch("apps.vendite.db.vendite_repository.fetch_paged_with_total")
    def test_commessa_multipla_non_si_sceglie(self, mock_fetch):
        mock_fetch.return_value = ([_riga(
            commessa_id=None, commessa_codice=None, commesse_n=2,
        )], 1)
        righe, _ = VenditeRepository().list_lotto_gruppi(
            lotto_id=10657, limit=25, offset=0,
        )
        self.assertIsNone(righe[0]["commessa_id"])
        self.assertEqual(righe[0]["commesse_n"], 2)


class LottoGruppiServiceTests(SimpleTestCase):
    # Il cancello di perimetro (`_lotto_perimetro`) legge la testata prima della
    # lista: qui il lotto e' visibile, il caso contrario ha il suo test.
    def setUp(self) -> None:
        patcher = patch.object(VenditeRepository, "get_lotto", return_value={"id": 1})
        patcher.start()
        self.addCleanup(patcher.stop)

    # 4) Una colonna fuori whitelist non ordina in silenzio: rifiuta.
    def test_ordinamento_fuori_whitelist_rifiutato(self):
        with self.assertRaises(ServiceError):
            fn_list_lotto_gruppi(lotto_id=1, order_by="errore_messaggio")

    # 5) Il vocabolario dell'esito e' chiuso: uno stato inventato non filtra
    #    zero righe in silenzio — dice che non esiste.
    def test_stato_esecuzione_fuori_vocabolario_rifiutato(self):
        with self.assertRaises(ServiceError):
            fn_list_lotto_gruppi(lotto_id=1, stato_esecuzione="ELABORATA")

    # 10) ⭐ UNA SOLA LETTURA, e nessun campo in più. Il flag
    #     `perimetro_dichiarato` è sparito col problema che risolveva: serviva
    #     perché la lista leggeva il solo PERIMETRO, che i giri di massa non
    #     scrivono, e zero righe voleva dire due cose. Ora la lista legge anche
    #     gli ESITI e zero righe ne vuol dire una sola.
    # ⛔ Il test guarda che il campo NON ci sia: un campo che non discrimina più
    #     niente, lasciato «per compatibilità», è peggio di un campo assente —
    #     chi lo legge crede che discrimini.
    @patch.object(VenditeRepository, "list_lotto_gruppi", return_value=([], 0))
    def test_nessun_flag_sul_perimetro_nella_risposta(self, mock_lista):
        out = fn_list_lotto_gruppi(lotto_id=10452)
        self.assertEqual(out["count"], 0)
        self.assertNotIn("perimetro_dichiarato", out)
        # E una lettura sola: il conteggio non si chiede a nessun altro.
        mock_lista.assert_called_once()

    # 11) L'export si ferma all'envelope minimo, come tutte le liste
    #     esportabili: chi costruisce il file legge `results` e `count`.
    @patch.object(VenditeRepository, "list_lotto_gruppi", return_value=([_riga()], 1))
    def test_export_non_pagina(self, mock_lista):
        fn_list_lotto_gruppi(lotto_id=10657, max_rows=10_001)
        self.assertEqual(mock_lista.call_args.kwargs["max_rows"], 10_001)

    # 14) ⭐ IL MOTIVO DEL PULSANTE SPENTO SI LEGGE DALLA SUPERFICIE DEL DB, e la
    #     query non lo compone (brief-modello-documento-vendita §15.11.1, BE-2).
    #     La vista `vendite.vw_lotti_gruppi_azioni` chiama la STESSA check che la
    #     madre usa per RIFIUTARE, e lo verifica il presidio del registro
    #     `config.azioni_riga`: tooltip ed errore non possono divergere.
    # ⛔ Se la query tornasse a chiamare la check da se', la colonna avrebbe due
    #    sedi, e una delle due il presidio del DB non la vede.
    # ⛔ E la colonna NOMINA IL VERBO (§12.5.4): su questa riga esiste gia' un
    #    esito con il suo `errore_codice`, che risponde a un'ALTRA domanda.
    @patch("apps.vendite.db.vendite_repository.fetch_paged_with_total")
    def test_il_motivo_del_blocco_si_legge_dalla_vista_non_si_compone(
        self, mock_fetch,
    ):
        mock_fetch.return_value = ([], 0)
        VenditeRepository().list_lotto_gruppi(lotto_id=10657, limit=25, offset=0)
        sql = mock_fetch.call_args.args[0]
        self.assertIn("vendite.vw_lotti_gruppi_azioni", sql)
        self.assertIn("az.uscita_blocco_reason,", sql)
        self.assertIn("az.uscita_blocco_reason_key,", sql)
        self.assertNotIn("fn_check_documento_escludibile_da_giro(", sql)
        # ⛔ Nessun motivo scritto a mano nella query: se comparisse un
        #    letterale, sarebbe la seconda sede del vocabolario dei motivi.
        for reason in ("GIA_USCITO", "DOCUMENTO_NON_IN_ERRORE", "SENZA_ESITO"):
            self.assertNotIn(reason, sql)

    # 15) ⚠️ I TRASCINATI arrivano dalla stessa vista, che li conta solo dove
    #     l'azione e' viva (`None` = «non e' stato chiesto», distinto da `0`).
    #     La query non chiama piu' la catena delle righe da se'.
    def test_i_trascinati_si_leggono_dalla_vista(self):
        with patch(
            "apps.vendite.db.vendite_repository.fetch_paged_with_total",
        ) as mock_fetch:
            mock_fetch.return_value = ([], 0)
            VenditeRepository().list_lotto_gruppi(lotto_id=10657, limit=25, offset=0)
            sql = mock_fetch.call_args.args[0]
        self.assertIn("az.n_trascinati,", sql)
        self.assertNotIn("fn_gruppi_trascinati_da_uscita(", sql)
