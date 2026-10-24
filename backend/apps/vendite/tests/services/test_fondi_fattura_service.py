# ------------------------------------------------------------
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Test unitari service elenco «fondi fattura da decidere» (mock repository).
# ------------------------------------------------------------

"""
Indice test eseguiti:
1) FondiFatturaDaDecidereServiceTests.test_ok_envelope_paginato
2) FondiFatturaDaDecidereServiceTests.test_senza_filtri_passthrough_none
3) FondiFatturaDaDecidereServiceTests.test_tutti_i_motivi_della_vista_sono_validi
4) FondiFatturaDaDecidereServiceTests.test_motivo_fuori_vocabolario
5) FondiFatturaDaDecidereServiceTests.test_ordinamento_inoltrato
6) FondiFatturaDaDecidereServiceTests.test_order_by_non_valido
7) FondiFatturaDaDecidereServiceTests.test_order_dir_non_valido
8) FondiFatturaDaDecidereServiceTests.test_envelope_pagina_dall_offset
10) FondiFatturaDaDecidereServiceTests.test_auth_user_id_inoltrato_defense_in_depth
11) FondiFatturaDaDecidereServiceTests.test_limit_offset_arrivano_al_repository
11-bis) FondiFatturaDaDecidereServiceTests.test_export_salta_la_paginazione
11-ter) FondiFatturaDaDecidereServiceTests.test_export_max_rows_non_positivo
11-quater) CancellaFondoFatturaServiceTests.test_ok_conteggi_dalla_madre
11-quinquies) CancellaFondoFatturaServiceTests.test_id_non_valido_rifiutato
11-sexies) CancellaFondoFatturaServiceTests.test_codice_del_db_arriva_intero
11-septies) CancellaFondoFatturaServiceTests.test_codice_nuovo_non_previsto_passa_lo_stesso
11-octies) CancellaFondoFatturaRepositoryTests.test_canale_di_sistema_rifiutato
12) FondiFatturaVocabolarioTests.test_configurazione_incompleta_non_e_un_motivo
13) FondiFatturaVistaGuardrailTests.test_motivi_misurati_dalla_vista_viva (e2e, opt-in)
14) CancellaFondoFatturaBindingTests.test_binding_reale_su_id_inesistente (e2e, opt-in)
"""

import re
from unittest import TestCase
from unittest.mock import patch

from django.db import DatabaseError

from apps.core.services.service_errors import ServiceError
from apps.core.tests.db_e2e import richiedi_db_provvisto
from apps.vendite.db.vendite_repository import FONDI_DA_DECIDERE_MOTIVI
from apps.vendite.services import vendite_service
from apps.vendite.services.vendite_service import fn_fondi_fattura_da_decidere
from apps.core.api.constants import DEFAULT_LIMIT

# Riga del ramo NON_PIU_CAPIENTE: e' l'unico dei quattro motivi in cui le
# colonne dell'ATTO sono valorizzate — negli altri tre l'atto non esiste ancora.
_ROW_NON_PIU_CAPIENTE = {
    "motivo": "NON_PIU_CAPIENTE",
    "fattura_sorgente_id": 42,
    "fondo_source_id": 7,
    "origine": "AUTOMATICA",
    "stato_atto": "DISPONIBILE",
    "importo_atto": "8.00",
    "capienza_attuale": "3.00",
    "importo_proposto": None,
}


class FondiFatturaDaDecidereServiceTests(TestCase):
    # Scopo: Envelope paginato standard con i risultati del repository.
    @patch.object(
        vendite_service.VenditeRepository,
        "list_fondi_fattura_da_decidere",
        return_value=([_ROW_NON_PIU_CAPIENTE], 1),
    )
    def test_ok_envelope_paginato(self, mock_repo):
        data = fn_fondi_fattura_da_decidere(motivo="NON_PIU_CAPIENTE")
        self.assertEqual(data["count"], 1)
        self.assertEqual(data["page"], 1)
        self.assertEqual(data["page_size"], DEFAULT_LIMIT)
        self.assertEqual(data["total_pages"], 1)
        self.assertEqual(data["results"], [_ROW_NON_PIU_CAPIENTE])
        self.assertEqual(mock_repo.call_args.kwargs["motivo"], "NON_PIU_CAPIENTE")

    # Scopo: Senza filtri il motivo resta None (tutti) e l'ordinamento arriva
    #        al repository con i DEFAULT gia' risolti (data, desc): la
    #        risoluzione vive nel service, il repository non deve indovinare.
    @patch.object(
        vendite_service.VenditeRepository,
        "list_fondi_fattura_da_decidere",
        return_value=([], 0),
    )
    def test_senza_filtri_passthrough_none(self, mock_repo):
        fn_fondi_fattura_da_decidere()
        kwargs = mock_repo.call_args.kwargs
        self.assertIsNone(kwargs["motivo"])
        self.assertEqual(kwargs["order_by"], "data")
        self.assertEqual(kwargs["order_dir"], "desc")

    # Scopo: TUTTI e quattro i motivi che la vista puo' produrre devono passare.
    #        Un motivo rifiutato qui sarebbe una riga di elenco non filtrabile:
    #        l'operatore la vede nel totale e non riesce a isolarla.
    @patch.object(
        vendite_service.VenditeRepository,
        "list_fondi_fattura_da_decidere",
        return_value=([], 0),
    )
    def test_tutti_i_motivi_della_vista_sono_validi(self, mock_repo):
        for motivo in FONDI_DA_DECIDERE_MOTIVI:
            with self.subTest(motivo=motivo):
                fn_fondi_fattura_da_decidere(motivo=motivo)
                self.assertEqual(mock_repo.call_args.kwargs["motivo"], motivo)

    # Scopo: Il vocabolario e' CHIUSO (letterali nei rami della UNION): un motivo
    #        inventato e' 400, non una lista vuota. Su un vocabolario chiuso il
    #        silenzio sarebbe indistinguibile da «non c'e' niente da decidere».
    def test_motivo_fuori_vocabolario(self):
        with self.assertRaises(ServiceError) as ctx:
            fn_fondi_fattura_da_decidere(motivo="CONFIGURAZIONE_INCOMPLETA")
        self.assertEqual(ctx.exception.code, "E_VENDITE_VALIDATION")

    # Scopo: Ordinamento inoltrato tale e quale al repository (la whitelist
    #        vive li', il service la presidia).
    @patch.object(
        vendite_service.VenditeRepository,
        "list_fondi_fattura_da_decidere",
        return_value=([], 0),
    )
    def test_ordinamento_inoltrato(self, mock_repo):
        fn_fondi_fattura_da_decidere(order_by="totale_a_pagare", order_dir="asc")
        kwargs = mock_repo.call_args.kwargs
        self.assertEqual(kwargs["order_by"], "totale_a_pagare")
        self.assertEqual(kwargs["order_dir"], "asc")

    # Scopo: Colonna fuori whitelist -> 400 (mai interpolata nell'ORDER BY).
    def test_order_by_non_valido(self):
        with self.assertRaises(ServiceError) as ctx:
            fn_fondi_fattura_da_decidere(order_by="importo_atto; DROP TABLE")
        self.assertEqual(ctx.exception.code, "E_VENDITE_VALIDATION")

    # Scopo: Direzione fuori {asc, desc} -> 400.
    def test_order_dir_non_valido(self):
        with self.assertRaises(ServiceError) as ctx:
            fn_fondi_fattura_da_decidere(order_dir="alfabetico")
        self.assertEqual(ctx.exception.code, "E_VENDITE_VALIDATION")

    # Scopo: l'envelope resta quello delle liste paginate: la pagina si
    #        ricava dall'offset (`offset // limit + 1`), riportata all'ultima
    #        se l'offset e' oltre il totale.
    @patch.object(
        vendite_service.VenditeRepository,
        "list_fondi_fattura_da_decidere",
        return_value=([], 120),
    )
    def test_envelope_pagina_dall_offset(self, _mock_repo):
        data = fn_fondi_fattura_da_decidere(limit=25, offset=50)
        self.assertEqual((data["page"], data["page_size"], data["total_pages"]), (3, 25, 5))
        data = fn_fondi_fattura_da_decidere(limit=25, offset=500)
        self.assertEqual(data["page"], 5)

    # Scopo: `auth_user_id` arriva al repository. La vista e' security_invoker e
    #        la RLS filtra da se', ma il filtro applicativo resta come
    #        defense-in-depth: se sparisce, l'elenco dipende da un solo cancello.
    @patch.object(
        vendite_service.VenditeRepository,
        "list_fondi_fattura_da_decidere",
        return_value=([], 0),
    )
    def test_auth_user_id_inoltrato_defense_in_depth(self, mock_repo):
        fn_fondi_fattura_da_decidere(auth_user_id=99)
        self.assertEqual(mock_repo.call_args.kwargs["auth_user_id"], 99)

    # Scopo: L'offset si deriva dalla pagina (page-based), non dal chiamante.
    @patch.object(
        vendite_service.VenditeRepository,
        "list_fondi_fattura_da_decidere",
        return_value=([], 0),
    )
    def test_limit_offset_arrivano_al_repository(self, mock_repo):
        # ⛔ Dal 2026-10-20 la lista pagina con `limit`/`offset` (§A4): prima
        #    con `page`/`page_size`, unica fra le liste di vendite.
        fn_fondi_fattura_da_decidere(limit=25, offset=50)
        kwargs = mock_repo.call_args.kwargs
        self.assertEqual(kwargs["limit"], 25)
        self.assertEqual(kwargs["offset"], 50)

    # Scopo: `max_rows` (export) SALTA la paginazione invece di violarne il
    #        tetto: limit=max_rows, offset=0 — anche con una `page` addosso, che
    #        e' il caso reale (il FE inoltra all'export gli stessi filtri della
    #        lista). Se la pagina vincesse, l'export conterrebbe la SOLA pagina
    #        a video mentre il file promette il perimetro intero.
    @patch.object(
        vendite_service.VenditeRepository,
        "list_fondi_fattura_da_decidere",
        return_value=([], 0),
    )
    def test_export_salta_la_paginazione(self, mock_repo):
        fn_fondi_fattura_da_decidere(limit=25, offset=75, max_rows=10_001)
        kwargs = mock_repo.call_args.kwargs
        self.assertEqual(kwargs["limit"], 10_001)
        self.assertEqual(kwargs["offset"], 0)

    # Scopo: `max_rows` non positivo -> 400. Un limite <= 0 non e' «tutto»:
    #        e' una query che non torna niente, e il file sarebbe vuoto senza
    #        che nulla lo dica.
    def test_export_max_rows_non_positivo(self):
        with self.assertRaises(ServiceError) as ctx:
            fn_fondi_fattura_da_decidere(max_rows=0)
        self.assertEqual(ctx.exception.code, "E_VENDITE_VALIDATION")


class FondiFatturaVocabolarioTests(TestCase):
    # Scopo: documenta una decisione, non misura niente (la misura sta nel
    #        guardrail sotto). CONFIGURAZIONE_INCOMPLETA era il quinto motivo
    #        previsto dal piano ed e' morto alla nascita: dopo il CHECK
    #        chk_emittenti_fiscali_utilities_soglie_coppia (D-0) una
    #        configurazione a meta' non e' piu' salvabile, e una riga di elenco
    #        che non puo' accadere insegna una cosa falsa.
    def test_configurazione_incompleta_non_e_un_motivo(self):
        self.assertNotIn("CONFIGURAZIONE_INCOMPLETA", FONDI_DA_DECIDERE_MOTIVI)


class FondiFatturaVistaGuardrailTests(TestCase):
    """Il mirror BE<->vista, MISURATO sulla vista viva.

    La tupla `FONDI_DA_DECIDERE_MOTIVI` e' una copia dei letterali nei rami
    della UNION di `vw_fondi_fattura_da_decidere` — in PostgreSQL un CHECK su
    una vista non esiste, quindi il vocabolario non ha un vincolo suo. Un test
    che confrontasse la tupla con una SECONDA copia hardcoded qui sarebbe
    autoreferenziale: verificherebbe la propria ipotesi, non il sistema
    (memoria `feedback_whitelist_dal_percorso_reale`). Questo guardrail estrae
    i motivi da `pg_get_viewdef` sul DB provvisto: se il team DB aggiunge un
    quinto ramo, qui diventa rosso — senza, la riga nuova sarebbe visibile nel
    totale ma NON filtrabile (il filtro `motivo` la rifiuterebbe con 400).
    """

    # Scopo: prerequisito DB reale (stesso protocollo del guardrail codici
    #        errore): skip su flag spenta/DB assente, FAIL se lo schema c'e'
    #        ma la vista no — quello e' un difetto, non una condizione
    #        d'ambiente.
    @classmethod
    def setUpClass(cls) -> None:
        super().setUpClass()
        richiedi_db_provvisto()

    # Scopo: estrae i letterali della colonna `motivo` da ogni ramo della
    #        UNION e li confronta con la tupla BE. Il parsing sfrutta il fatto
    #        che `motivo` e' la PRIMA colonna di output di ogni ramo: il testo
    #        fra l'ultimo `SELECT` e ` AS motivo` e' esattamente l'espressione
    #        del motivo (letterale secco o CASE). Se il DB ristruttura la vista
    #        e il parsing non trova piu' nulla, il test fallisce comunque:
    #        rumoroso, mai silenziosamente verde.
    def test_motivi_misurati_dalla_vista_viva(self):
        from django.db import connection

        with connection.cursor() as cur:
            cur.execute(
                "SELECT to_regclass('vendite.vw_fondi_fattura_da_decidere') IS NOT NULL"
            )
            row = cur.fetchone()
            assert row is not None
            self.assertTrue(
                row[0],
                "vw_fondi_fattura_da_decidere assente su schema provvisto: "
                "Fase C non applicata o vista rinominata (difetto, non ambiente)",
            )
            cur.execute(
                "SELECT pg_get_viewdef('vendite.vw_fondi_fattura_da_decidere'::regclass)"
            )
            row = cur.fetchone()
            assert row is not None
            viewdef = str(row[0])

        misurati: set[str] = set()
        pezzi = viewdef.split(" AS motivo")
        for pezzo in pezzi[:-1]:
            inizio = pezzo.rfind("SELECT")
            self.assertGreaterEqual(
                inizio, 0, "parsing della vista fallito: nessun SELECT prima di AS motivo"
            )
            misurati.update(re.findall(r"'([A-Z_]+)'::text", pezzo[inizio:]))

        self.assertTrue(misurati, "parsing della vista fallito: nessun motivo estratto")
        self.assertEqual(
            misurati,
            set(FONDI_DA_DECIDERE_MOTIVI),
            "vocabolario motivi divergente fra vista e BE: allineare "
            "FONDI_DA_DECIDERE_MOTIVI (vendite_repository) alla vista — una "
            "riga con motivo non in tupla e' visibile nel totale ma non "
            "filtrabile (400 sul filtro)",
        )


# ══════════════════════════════════════════════════════════════════
#  BE-4 — la cancellazione dell'atto (D-21)
#  brief-db-fondo-fattura-ricalcolo-e-governo §9.3
# ══════════════════════════════════════════════════════════════════


class CancellaFondoFatturaServiceTests(TestCase):
    # Scopo: il service non ricalcola niente — inoltra l'id e restituisce i
    #        contatori della madre DB, piu' lo stato del gesto.
    @patch.object(
        vendite_service.VenditeRepository,
        "cancella_fondo_fattura",
        return_value={"deleted_righe": 1, "deleted_fondi": 1, "deleted_source": 1},
    )
    def test_ok_conteggi_dalla_madre(self, mock_repo):
        data = vendite_service.fn_cancella_fondo_fattura(fondo_source_id=7)
        self.assertEqual(data["status"], "deleted")
        self.assertEqual(data["fondo_source_id"], 7)
        self.assertEqual(data["deleted_source"], 1)
        mock_repo.assert_called_once_with(7)

    # Scopo: un id non positivo si ferma PRIMA del database. Non e' pedanteria:
    #        la madre solleverebbe comunque (`E_VENDITE_CHIAMATA_NON_VALIDA`,
    #        TECNICO), ma un errore di chiamante non deve arrivare a video come
    #        un guasto tecnico del database.
    def test_id_non_valido_rifiutato(self):
        # ⚠️ `True` c'e' perche' in Python `isinstance(True, int)` e' VERO:
        #    senza il guard esplicito sarebbe finito al database come booleano.
        for valore in (0, -1, None, "7", True, 1.0):
            with self.subTest(valore=valore):
                with self.assertRaises(ServiceError) as ctx:
                    vendite_service.fn_cancella_fondo_fattura(fondo_source_id=valore)
                self.assertEqual(ctx.exception.code, "E_VENDITE_VALIDATION")

    # Scopo: ⭐ il CONTRATTO di questo endpoint. Il codice che il database
    #        dichiara deve arrivare all'operatore COM'E' — non appiattito sul
    #        fallback — perche' e' cio' che distingue «il denaro si e' mosso»
    #        da «lo trattiene una sistemazione», che hanno due rimedi diversi.
    #        ⚠️ Si prova su OGNI ramo dichiarato, non su uno solo: un codice non
    #        tradotto non da' un errore educato, da' il messaggio sbagliato.
    def test_codice_del_db_arriva_intero(self):
        rami = [
            "E_FONDO_NON_TROVATO",
            "E_FONDO_NON_CANCELLABILE",
            "E_FONDO_FIGLIA_CONGELATA",
            "E_FONDO_TRATTENUTO_DA_SISTEMAZIONE",
        ]
        for codice in rami:
            with self.subTest(codice=codice):
                with patch.object(
                    vendite_service.VenditeRepository,
                    "cancella_fondo_fattura",
                    side_effect=DatabaseError(f"{codice}: il database ha rifiutato."),
                ):
                    with self.assertRaises(ServiceError) as ctx:
                        vendite_service.fn_cancella_fondo_fattura(fondo_source_id=7)
                self.assertEqual(ctx.exception.code, codice)

    # Scopo: ⭐ la ragione per cui qui NON c'e' un elenco locale di codici
    #        ammessi. Il predicato ha gia' avuto sei motivi dove il piano ne
    #        prevedeva quattro: un codice che il backend non conosce deve
    #        passare lo stesso, o il giorno che il team DB ne conia uno
    #        l'operatore leggerebbe un messaggio generico al posto del suo.
    def test_codice_nuovo_non_previsto_passa_lo_stesso(self):
        with patch.object(
            vendite_service.VenditeRepository,
            "cancella_fondo_fattura",
            side_effect=DatabaseError("E_FONDO_MOTIVO_CHE_NON_ESISTE_ANCORA: nuovo."),
        ):
            with self.assertRaises(ServiceError) as ctx:
                vendite_service.fn_cancella_fondo_fattura(fondo_source_id=7)
        self.assertEqual(ctx.exception.code, "E_FONDO_MOTIVO_CHE_NON_ESISTE_ANCORA")


class CancellaFondoFatturaRepositoryTests(TestCase):
    # Scopo: 🔴 il guard di canale, ed e' il presidio che pesa di piu' di tutto
    #        questo passo. La madre e' SECURITY INVOKER e si appoggia alla row
    #        security accesa da D-20: su un ruolo BYPASSRLS il perimetro
    #        emittente sparisce, e qui non si LEGGEREBBE l'atto di un altro
    #        emittente — lo si CANCELLEREBBE. Un conteggio non lo troverebbe:
    #        l'operazione riuscirebbe.
    @patch("apps.vendite.db.vendite_repository.connection_role_bypasses_rls",
           return_value=True)
    def test_canale_di_sistema_rifiutato(self, _mock_bypass):
        from apps.vendite.db.vendite_repository import VenditeRepository

        with self.assertRaises(ServiceError) as ctx:
            VenditeRepository().cancella_fondo_fattura(7)
        self.assertEqual(ctx.exception.code, "E_VENDITE_VALIDATION")


class CancellaFondoFatturaBindingTests(TestCase):
    """Il binding con la madre DB, provato con una CHIAMATA VERA (e2e, opt-in).

    ⭐ Perche' esiste, quando i test sopra girano su mock: un mock non vede la
    FIRMA. Se `fn_cancella_fondo_fattura` cambiasse nome, numero di parametri o
    colonne di ritorno, tutti i test mockati resterebbero verdi e l'endpoint
    sarebbe rotto in produzione — e' la memoria
    `feedback_rinomina_db_binding_mockato`, gia' pagata su questo progetto.
    ⛔ L'id e' inesistente di proposito: prova la firma e la traduzione senza
    toccare un solo dato.
    """

    @classmethod
    def setUpClass(cls) -> None:
        super().setUpClass()
        richiedi_db_provvisto()

    # Scopo: la madre risponde, e risponde con il codice giusto tradotto in
    #        ServiceError. Prova in un colpo: firma, tipo dei parametri, nomi
    #        delle colonne di ritorno, `fn_log_and_raise_error` e la catena di
    #        traduzione fino al codice di dominio.
    def test_binding_reale_su_id_inesistente(self):
        from django.db import connection

        with connection.cursor() as cur:
            cur.execute(
                "SELECT to_regprocedure("
                "'vendite.fn_cancella_fondo_fattura(bigint)') IS NOT NULL"
            )
            row = cur.fetchone()
            assert row is not None
            self.assertTrue(
                row[0],
                "vendite.fn_cancella_fondo_fattura(bigint) assente sullo schema "
                "provvisto: D-21 non applicato o firma cambiata (difetto, non "
                "condizione d'ambiente)",
            )

        with self.assertRaises(ServiceError) as ctx:
            vendite_service.fn_cancella_fondo_fattura(fondo_source_id=999_999_999)
        self.assertEqual(
            ctx.exception.code,
            "E_FONDO_NON_TROVATO",
            "il codice del database non arriva intero al service: rotta la "
            "catena fn_log_and_raise_error -> translate_db_errors",
        )
