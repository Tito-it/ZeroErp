# ------------------------------------------------------------
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Presidi del service dei titoli IVA (I7 / D10).
#        ⭐ Nessuno di questi e' un test di copertura: ognuno prova la cosa che,
#        se sbagliata, NON darebbe nessun sintomo.
# ------------------------------------------------------------

from __future__ import annotations

from decimal import Decimal
from unittest import TestCase
from unittest.mock import MagicMock, patch

from apps.core.services.service_errors import ServiceError

REPO = "apps.anagrafiche.services.titoli_iva_service.TitoliIvaRepository"

SOGG = "11111111-1111-1111-1111-111111111111"
ALTRO_SOGG = "22222222-2222-2222-2222-222222222222"


def _titolo(**over):
    base = {
        "id": 7,
        "soggetto_id": SOGG,
        "emittente_fiscale_id": 3,
        "tipo_titolo_iva_id": 1,
        "tipo_ha_plafond": True,
        "iva_id": 18,
        "ambito": "TUTTO",
        "plafond": Decimal("1000.00"),
        "imponibile_utilizzato": Decimal("250.00"),
        "residuo": Decimal("750.00"),
        "ambiti_count": 0,
        "attivo": True,
    }
    base.update(over)
    return base


# =================================================================
# Q3 — dall'API si scrive SOLO `FORZATURA`
# =================================================================

class TitoliIvaMovimentiTests(TestCase):

    @patch(REPO)
    def test_movimento_fattura_rifiutato(self, repo_cls):
        """⭐ Il test piu' importante di questa voce.

        Un POST che riuscisse a scrivere un movimento `FATTURA` consumerebbe
        plafond SENZA una fattura: il CHECK di DB pretende `fattura_id NOT NULL`
        sui tipi non-forzatura, quindi basterebbe passare l'id di una fattura
        vera e `uq_stiva_movimenti_documento` non proteggerebbe piu' niente —
        la riga sarebbe formalmente valida. Il numero che ne esce e' quello che
        l'Agenzia delle Entrate verifica.
        E' l'unico test che si accorge se qualcuno riapre quella porta.
        """
        repo_cls.return_value.get_titolo.return_value = _titolo()
        from apps.anagrafiche.services.titoli_iva_service import TitoliIvaService
        with self.assertRaises(ServiceError) as ctx:
            TitoliIvaService().create_forzatura(SOGG, 7, {
                "tipo_movimento": "FATTURA",
                "imponibile": "100.00",
                "data_movimento": "2026-08-29",
                "motivo": "x",
            })
        self.assertEqual(ctx.exception.code, "E_ANAG_VALIDAZIONE")
        repo_cls.return_value.create_forzatura.assert_not_called()

    @patch(REPO)
    def test_forzatura_senza_motivo_rifiutata(self, repo_cls):
        """Il motivo e' la traccia del perche' (D5): senza, resta un numero che
        qualcuno ha messo li'. Lo pretende anche un CHECK, ma qui si nomina il
        CAMPO invece di uno SQLSTATE."""
        repo_cls.return_value.get_titolo.return_value = _titolo()
        from apps.anagrafiche.services.titoli_iva_service import TitoliIvaService
        with self.assertRaises(ServiceError):
            TitoliIvaService().create_forzatura(SOGG, 7, {
                "imponibile": "100.00", "data_movimento": "2026-08-29",
                "motivo": "   ",
            })
        repo_cls.return_value.create_forzatura.assert_not_called()

    @patch(REPO)
    def test_forzatura_zero_rifiutata(self, repo_cls):
        """Un movimento che non muove niente non e' una correzione: e' rumore
        nel registro. Lo rifiuta anche `chk_stiva_movimenti_segno`."""
        repo_cls.return_value.get_titolo.return_value = _titolo()
        from apps.anagrafiche.services.titoli_iva_service import TitoliIvaService
        with self.assertRaises(ServiceError):
            TitoliIvaService().create_forzatura(SOGG, 7, {
                "imponibile": "0", "data_movimento": "2026-08-29", "motivo": "x",
            })

    @patch(REPO)
    def test_forzatura_negativa_ammessa(self, repo_cls):
        """⭐ Il lato che nessuno prova: una forzatura corregge in ENTRAMBE le
        direzioni. Un guard scritto largo sul segno bloccherebbe la correzione
        in diminuzione, che e' proprio il caso piu' frequente."""
        repo_cls.return_value.get_titolo.return_value = _titolo()
        repo_cls.return_value.create_forzatura.return_value = 42
        from apps.anagrafiche.services.titoli_iva_service import TitoliIvaService
        out = TitoliIvaService().create_forzatura(SOGG, 7, {
            "imponibile": "-50.00", "data_movimento": "2026-08-29",
            "motivo": "storno fattura extra-sistema",
        })
        self.assertEqual(out["id"], 42)
        kwargs = repo_cls.return_value.create_forzatura.call_args.kwargs
        # ⚠️ Decimal e non float: e' un importo fiscale su una colonna numeric.
        self.assertEqual(kwargs["imponibile"], Decimal("-50.00"))
        self.assertIsInstance(kwargs["imponibile"], Decimal)

    @patch(REPO)
    def test_forzatura_imponibile_non_numerico_e_un_400_col_campo(self, repo_cls):
        """⭐ Il punto che traduce (2026-09-18): la coercizione e' del BB
        `PayloadValidator`, ma che il codice del dominio e il CAMPO arrivino
        all'envelope resta scritto qui. `True` e `NaN` sono i due valori che la
        copia locale lasciava passare — un bool sarebbe entrato come 1, un NaN
        sarebbe arrivato fino alla colonna `numeric` di un registro fiscale."""
        repo_cls.return_value.get_titolo.return_value = _titolo()
        from apps.anagrafiche.services.titoli_iva_service import TitoliIvaService
        for raw in (None, "", "cento", True, "NaN"):
            with self.subTest(raw=raw):
                with self.assertRaises(ServiceError) as ctx:
                    TitoliIvaService().create_forzatura(SOGG, 7, {
                        "imponibile": raw, "data_movimento": "2026-08-29", "motivo": "x",
                    })
                self.assertEqual(ctx.exception.code, "E_ANAG_VALIDAZIONE")
                self.assertEqual(ctx.exception.context["field"], "imponibile")
        repo_cls.return_value.create_forzatura.assert_not_called()


# =================================================================
# Q6 — si elimina solo un titolo che non ha consumato niente
# =================================================================

class TitoliIvaDeleteTests(TestCase):

    @patch(REPO)
    def test_delete_con_movimenti_rifiutato(self, repo_cls):
        """Un registro e' la traccia di cio' che e' stato consumato, e un DELETE
        che se la porta via cancella la prova. Il DB lo regge gia' (la FK dei
        movimenti non ha CASCADE) ma lo direbbe con un 23503 che nomina un
        vincolo: qui si dice la cosa vera, e cosa fare al posto."""
        repo = repo_cls.return_value
        repo.get_titolo.return_value = _titolo()
        repo.count_movimenti.return_value = 3
        from apps.anagrafiche.services.titoli_iva_service import TitoliIvaService
        with self.assertRaises(ServiceError) as ctx:
            TitoliIvaService().delete_titolo(SOGG, 7)
        self.assertEqual(ctx.exception.code, "E_ANAG_VALIDAZIONE")
        self.assertIn("disattiva", ctx.exception.message)
        repo.delete_titolo.assert_not_called()

    @patch(REPO)
    def test_delete_senza_movimenti_ok(self, repo_cls):
        """Il verso gemello: senza movimenti si cancella davvero. Senza questo,
        il guard sopra passerebbe anche se rifiutasse SEMPRE."""
        repo = repo_cls.return_value
        repo.get_titolo.return_value = _titolo()
        repo.count_movimenti.return_value = 0
        from apps.anagrafiche.services.titoli_iva_service import TitoliIvaService
        self.assertTrue(TitoliIvaService().delete_titolo(SOGG, 7)["deleted"])
        repo.delete_titolo.assert_called_once_with(7)


# =================================================================
# Q5 — l'emittente destinatario non si sposta
# =================================================================

class TitoliIvaEmittenteTests(TestCase):

    @patch(REPO)
    def test_patch_emittente_rifiutata(self, repo_cls):
        """Spostare il destinatario sposterebbe sotto un altro fornitore anche
        il plafond gia' consumato: i movimenti sono attaccati al TITOLO, non
        all'emittente (D10-bis)."""
        repo_cls.return_value.get_titolo.return_value = _titolo()
        from apps.anagrafiche.services.titoli_iva_service import TitoliIvaService
        with self.assertRaises(ServiceError) as ctx:
            TitoliIvaService().update_titolo(SOGG, 7, {"emittente_fiscale_id": 9})
        self.assertEqual(ctx.exception.code, "E_ANAG_VALIDAZIONE")
        repo_cls.return_value.update_titolo.assert_not_called()


# =================================================================
# Ownership: le rotte sono annidate, l'id nel path deve combaciare
# =================================================================

class TitoliIvaOwnershipTests(TestCase):

    @patch(REPO)
    def test_titolo_di_altro_soggetto_non_trovato(self, repo_cls):
        """⛔ Senza questo controllo, l'id di un titolo di un ALTRO soggetto —
        dentro lo stesso perimetro emittente, quindi visibile alla RLS — sarebbe
        modificabile passando dal soggetto sbagliato. La RLS dice cosa si puo'
        vedere; l'ownership dice che path e riga combaciano."""
        repo_cls.return_value.get_titolo.return_value = _titolo(soggetto_id=ALTRO_SOGG)
        from apps.anagrafiche.services.titoli_iva_service import TitoliIvaService
        with self.assertRaises(ServiceError) as ctx:
            TitoliIvaService().get_titolo(SOGG, 7)
        self.assertEqual(ctx.exception.code, "E_ANAG_NOT_FOUND")


# =================================================================
# Q2 — l'ambito ristretto senza righe si dichiara, non si blocca
# =================================================================

class TitoliIvaAmbitoTests(TestCase):

    @patch(REPO)
    def test_ristretto_senza_righe_e_dichiarato(self, repo_cls):
        """Il DB ammette quello stato apposta (si costruisce in due istruzioni).
        L'API lo DICHIARA, cosi' il frontend avvisa senza ri-derivare la regola
        in un template."""
        repo = repo_cls.return_value
        # ⚠️ `(righe, totale)`: dal 2026-09-02 il repository consegna la pagina
        #    e il totale nella stessa valutazione.
        repo.list_titoli_soggetto.return_value = ([
            _titolo(id=1, ambito="RISTRETTO", ambiti_count=0),
            _titolo(id=2, ambito="RISTRETTO", ambiti_count=2),
            _titolo(id=3, ambito="TUTTO", ambiti_count=0),
        ], 3)
        from apps.anagrafiche.services.titoli_iva_service import TitoliIvaService
        out = TitoliIvaService().list_titoli_soggetto(SOGG)
        self.assertEqual(
            [t["ambito_incompleto"] for t in out["results"]], [True, False, False],
        )
        # ⛔ Il totale NON e' `len(results)`: e' quello che la query ha
        #    dichiarato. Su una pagina il secondo e' un pezzo del primo.
        self.assertEqual(out["count"], 3)
        # ⭐ E nessun giro extra: il conteggio arriva dalla stessa query.
        repo.list_ambiti.assert_not_called()

    @patch(REPO)
    def test_ambito_livello_senza_oggetto_rifiutato(self, repo_cls):
        """Livello dichiarato e oggetto mancante: senza il guard sarebbe un
        23514 che nomina un vincolo invece del campo lasciato vuoto."""
        repo_cls.return_value.get_titolo.return_value = _titolo()
        from apps.anagrafiche.services.titoli_iva_service import TitoliIvaService
        with self.assertRaises(ServiceError):
            TitoliIvaService().create_ambito(SOGG, 7, {"livello": "ARTICOLO"})

    @patch(REPO)
    def test_ambito_azzera_gli_altri_livelli(self, repo_cls):
        """⭐ Il payload puo' portarsi dietro i residui di una scelta precedente
        (il form cambia livello e non ripulisce). `chk_..._ambiti_livello`
        pretende che le altre due colonne siano NULL: il normalizzatore le
        azzera, o il salvataggio diventa un 23514 muto."""
        repo = repo_cls.return_value
        repo.get_titolo.return_value = _titolo()
        repo.create_ambito.return_value = 5
        from apps.anagrafiche.services.titoli_iva_service import TitoliIvaService
        TitoliIvaService().create_ambito(SOGG, 7, {
            "livello": "gruppo_voce", "gruppo_voce_id": 4,
            "articolo_id": "33333333-3333-3333-3333-333333333333",
            "tipo_voce_id": 9,
        })
        dati = repo.create_ambito.call_args.args[1]
        self.assertEqual(dati["livello"], "GRUPPO_VOCE")
        self.assertEqual(dati["gruppo_voce_id"], 4)
        self.assertIsNone(dati.get("articolo_id"))
        self.assertIsNone(dati.get("tipo_voce_id"))


# =================================================================
# Q4 — il residuo si legge, non si ricalcola
# =================================================================

class TitoliIvaResiduoTests(TestCase):

    @patch(REPO)
    def test_residuo_non_risommato_dal_registro(self, repo_cls):
        """⭐ `imponibile_utilizzato` lo tiene il trigger dell'accumulatore come
        SOMMA del registro (D5): ri-sommare le righe qui creerebbe una seconda
        verita' sullo stesso numero — il difetto che D5 esiste per evitare.
        Il test lo prova nel modo che discrimina: il registro e' VUOTO e il
        residuo resta quello della colonna."""
        repo = repo_cls.return_value
        repo.get_titolo.return_value = _titolo()
        # ⚠️ `(righe, totale)`: dal 2026-09-02 anche queste due sotto-liste
        #    consegnano la pagina e il totale nella stessa valutazione.
        repo.list_ambiti.return_value = ([], 0)
        repo.list_movimenti.return_value = ([], 0)
        from apps.anagrafiche.services.titoli_iva_service import TitoliIvaService
        out = TitoliIvaService().get_titolo(SOGG, 7)
        self.assertEqual(out["residuo"], Decimal("750.00"))
        self.assertEqual(out["imponibile_utilizzato"], Decimal("250.00"))

# =================================================================
# Campi obbligatori e non annullabili — i serializer NON validano
# =================================================================

class TitoliIvaCampiRichiestiTests(TestCase):
    """⚠️ In questo progetto i serializer di `extend_schema` servono lo SCHEMA
    OpenAPI e NON validano: `handle_post_json` passa il payload grezzo al
    service. Senza questi guard un campo mancante o svuotato arriva come
    violazione di NOT NULL — un errore che nomina una COLONNA a chi ha lasciato
    vuoto un CAMPO."""

    _BASE = {
        "emittente_fiscale_id": 3, "tipo_titolo_iva_id": 1,
        "iva_id": 18, "valido_dal": "2026-01-01",
    }

    @patch(REPO)
    def test_create_senza_obbligatori_rifiutata(self, repo_cls):
        from apps.anagrafiche.services.titoli_iva_service import (
            _CREATE_OBBLIGATORI, TitoliIvaService,
        )
        for campo in _CREATE_OBBLIGATORI:
            with self.subTest(campo=campo):
                payload = {k: v for k, v in self._BASE.items() if k != campo}
                with self.assertRaises(ServiceError) as ctx:
                    TitoliIvaService().create_titolo(SOGG, payload)
                self.assertEqual(ctx.exception.code, "E_ANAG_VALIDAZIONE")
                repo_cls.return_value.create_titolo.assert_not_called()

    @patch(REPO)
    def test_update_non_puo_svuotare_i_not_null(self, repo_cls):
        """L'altro verso dello stesso guard: la create pretende che ci siano,
        l'update che restino (`feedback_normalize_guard_simmetrico`)."""
        from apps.anagrafiche.services.titoli_iva_service import (
            _NON_ANNULLABILI, TitoliIvaService,
        )
        repo_cls.return_value.get_titolo.return_value = _titolo()
        for campo in sorted(_NON_ANNULLABILI):
            with self.subTest(campo=campo):
                with self.assertRaises(ServiceError):
                    TitoliIvaService().update_titolo(SOGG, 7, {campo: ""})
                repo_cls.return_value.update_titolo.assert_not_called()

    @patch(REPO)
    def test_update_puo_svuotare_la_fine_validita(self, repo_cls):
        """⭐ Il lato che nessuno prova: un guard scritto largo bloccherebbe
        anche `valido_al`, che e' nullable e il cui svuotamento significa «senza
        scadenza» — un'operazione legittima e frequente."""
        repo = repo_cls.return_value
        repo.get_titolo.return_value = _titolo()
        repo.update_titolo.return_value = True
        from apps.anagrafiche.services.titoli_iva_service import TitoliIvaService
        TitoliIvaService().update_titolo(SOGG, 7, {"valido_al": ""})
        self.assertIsNone(repo.update_titolo.call_args.args[1]["valido_al"])


# =================================================================
# ⭐ Guardrail: i TRE anelli della PATCH restano allineati
# =================================================================

class TitoliIvaCatenaUpdateTests(TestCase):
    """La catena e':

        _UPDATE_KEYS  →  _normalizza_titolo  →  _TITOLO_UPDATE_COLS
        (cosa si accetta)  (cosa si mappa)     (cosa si scrive)

    ⛔ Basta che una colonna manchi in UNO SOLO dei tre e la PATCH risponde 200
    senza scrivere quel campo — senza errore, perche' il payload ne contiene
    altri e il guard «nessun campo aggiornabile» non scatta.

    ⚠️ Non e' un timore teorico: questo progetto ha gia' pagato questo difetto su
    `vendite.contratti` (`fatturazione_immediata`, 2026-07-27) e di nuovo il
    2026-08-29 sui riferimenti dell'atto — dove il mapper era stato agganciato al
    builder sbagliato. Il guardrail gemello sta in
    `apps/vendite/tests/services/test_contratti_service.py`.
    """

    _CAMPIONI: dict[str, object] = {
        "tipo_titolo_iva_id": 2,
        "iva_id": 18,
        "ambito": "TUTTO",
        "valido_dal": "2026-03-01",
        "valido_al": "2026-12-31",
        "protocollo": "PROT/2026/9",
        "data_ricezione": "2026-02-01",
        "riferimento": "RIF-9",
        "plafond": "1500.00",
        "attivo": False,
        "note": "nota",
    }

    def test_ogni_chiave_accettata_ha_un_campione(self) -> None:
        from apps.anagrafiche.services.titoli_iva_service import _UPDATE_KEYS
        senza = sorted(set(_UPDATE_KEYS) - set(self._CAMPIONI))
        self.assertEqual(
            senza, [],
            f"Chiavi in _UPDATE_KEYS senza campione qui: {senza}. Aggiungerne "
            f"uno valido e verificare che _normalizza_titolo le legga davvero.",
        )

    @patch(REPO)
    def test_ogni_chiave_attraversa_il_mapper(self, repo_cls) -> None:
        from apps.anagrafiche.services.titoli_iva_service import (
            _UPDATE_KEYS, TitoliIvaService,
        )
        repo = repo_cls.return_value
        repo.get_titolo.return_value = _titolo()
        repo.update_titolo.return_value = True
        for chiave in sorted(_UPDATE_KEYS):
            with self.subTest(chiave=chiave):
                repo.update_titolo.reset_mock()
                TitoliIvaService().update_titolo(
                    SOGG, 7, {chiave: self._CAMPIONI[chiave]},
                )
                self.assertTrue(repo.update_titolo.called, f"{chiave} non arriva al repo")
                dati = repo.update_titolo.call_args.args[1]
                self.assertIn(chiave, dati, f"{chiave} accettata ma NON mappata")

    def test_ogni_chiave_mappata_e_scrivibile(self) -> None:
        """Anello 2 → 3: cio' che il mapper produce dev'essere scrivibile dal
        repository, o l'UPDATE lo scarta in silenzio."""
        from apps.anagrafiche.db.titoli_iva_repository import _TITOLO_UPDATE_COLS
        from apps.anagrafiche.services.titoli_iva_service import _UPDATE_KEYS
        non_scrivibili = sorted(set(_UPDATE_KEYS) - set(_TITOLO_UPDATE_COLS))
        self.assertEqual(
            non_scrivibili, [],
            f"Chiavi accettate dal service che il repository non scrive: "
            f"{non_scrivibili}.",
        )


# Scopo: esegue una chiamata di repository con un cursore FINTO e restituisce
#        `(sql, params)` della PRIMA `execute`.
#
# ⭐ Estratto il 2026-09-02 alla seconda copia (regola del 2), e le due
#    divergevano gia': una registrava l'ULTIMA `execute` e non aveva
#    `fetchone`. Non e' un dettaglio di stile — con `offset > 0` e zero righe
#    parte anche il conteggio di RIPIEGO, quindi quella versione verificava la
#    query sbagliata e, sul percorso del ripiego, sollevava `AttributeError`
#    invece di misurare. La copia rimasta indietro e' quella che sbaglia in
#    direzione «verde» (`feedback_duplicazione_nasconde_il_bug`).
#
# ⚠️ Si guarda il SQL perche' e' li' che vivono i difetti di questa famiglia:
#    un ORDER BY sbagliato non solleva niente, ordina e basta.
def _cattura_sql(chiamata) -> tuple[str, list]:
    from apps.anagrafiche.db import titoli_iva_repository as m

    catturato: dict = {}

    class _Cursore:
        description = ()

        def execute(self, sql, params=None):
            catturato.setdefault("sql", sql)
            catturato.setdefault("params", params)

        def fetchall(self):
            return []

        # Il conteggio di ripiego legge una riga sola: senza questo metodo il
        # percorso «pagina stantia» non si potrebbe nemmeno esercitare.
        def fetchone(self):
            return (0,)

        def __enter__(self):
            return self

        def __exit__(self, *a):
            return False

    with patch.object(m.connection, "cursor", return_value=_Cursore()):
        chiamata(m.TitoliIvaRepository())
    return catturato["sql"], catturato["params"]


class TitoliSfondatiPaginazioneTests(TestCase):
    """La lista di presidio, paginata dal 2026-09-02.

    ⭐ Prima restituiva i primi 500 e non lo diceva: dal 501-esimo caso in poi
    una forzatura non si vedeva, su una lista che esiste per non farne sfuggire
    nessuna. Questi test presidiano le due meta' della correzione.
    """

    def _servizio(self, righe, totale):
        from apps.anagrafiche.services.titoli_iva_service import TitoliIvaService

        repo = MagicMock()
        # ⭐ Il repository ritorna (righe, totale) da UNA valutazione: il totale
        #    non e' una seconda query, ed e' il motivo per cui non puo'
        #    divergere dalla pagina.
        repo.list_titoli_sfondati.return_value = (righe, totale)
        # ⚠️ `TitoliIvaService` costruisce il proprio repository e non lo accetta
        #    iniettato: si sostituisce l'attributo, come fanno gli altri test di
        #    questo modulo. Cambiare la firma del service per i test sarebbe
        #    farsi dettare il progetto dalla prova.
        svc = TitoliIvaService()
        svc._repo = repo
        return svc, repo

    # Scopo: i parametri di pagina arrivano al repository come li ha dati la
    #        view — se si perdessero per strada la lista tornerebbe a mostrare
    #        sempre la prima pagina, e sembrerebbe che i casi siano quelli.
    def test_i_parametri_di_pagina_arrivano_al_repository(self) -> None:
        svc, repo = self._servizio([{"id": 1}], 1)
        svc.list_titoli_sfondati(
            limit=25, offset=50, order_by="eccedenza", order_dir="desc",
        )
        repo.list_titoli_sfondati.assert_called_once_with(
            limit=25, offset=50, order_by="eccedenza", order_dir="desc",
        )

    # Scopo: il `count` NON e' `len(results)`. E' il numero che dice quanti casi
    #        esistono davvero: derivarlo dalla pagina lo farebbe coincidere con
    #        la pagina, cioe' rifarebbe esattamente il difetto corretto.
    def test_il_totale_non_e_la_lunghezza_della_pagina(self) -> None:
        svc, _ = self._servizio([{"id": 1}, {"id": 2}], 700)
        esito = svc.list_titoli_sfondati(limit=2, offset=0)
        self.assertEqual(len(esito["results"]), 2)
        self.assertEqual(esito["count"], 700)

    # Scopo: la whitelist e' chiavata sui `campo_sorgente` FISICI, che sono i
    #        nomi che `<ListaConfigurabile>` manda in `order_by`. Chiavarla sui
    #        codici logici e' il difetto trovato su `vendite.lotti` il 07-31.
    def test_whitelist_chiavata_sui_campi_fisici(self) -> None:
        from apps.anagrafiche.db.titoli_iva_repository import _ORDER_COLS_SFONDATI

        self.assertIn("eccedenza", _ORDER_COLS_SFONDATI)
        self.assertIn("imponibile_utilizzato", _ORDER_COLS_SFONDATI)
        # ⛔ Nessuna chiave "logica" che il frontend non manderebbe mai.
        self.assertNotIn("utilizzato", _ORDER_COLS_SFONDATI)


class TitoliSfondatiOrdinamentoSQLTests(TestCase):
    """L'ORDER BY generato, letto dal SQL invece che dedotto.

    🔴 Nasce da un difetto REALE introdotto e corretto il 2026-09-02: la view
    passava `parse_list_params()["order_dir"]`, che normalizza l'assenza ad
    `"asc"` e non e' mai `None` — quindi il `default_desc=True` del repository
    non veniva mai raggiunto e la lista di presidio si ordinava dalla eccedenza
    PIU' PICCOLA. Nessun errore: solo il caso piu' grave in ultima pagina, su
    una schermata che esiste per metterlo davanti.
    ⭐ Il test guarda il SQL perche' e' li' che il difetto viveva: qualunque
    prova sui soli valori di ritorno sarebbe passata.
    """

    def _sql_di(self, **kwargs) -> str:
        return _cattura_sql(
            lambda repo: repo.list_titoli_sfondati(limit=25, offset=0, **kwargs),
        )[0]

    # Scopo: senza indicazioni si ordina dalla PIU' GRAVE. E' il difetto sopra.
    def test_senza_order_dir_ordina_decrescente(self) -> None:
        sql = self._sql_di(order_by=None, order_dir=None)
        self.assertIn("DESC NULLS LAST", sql)
        self.assertNotIn("ASC NULLS FIRST", sql)

    # Scopo: e se l'operatore chiede il contrario, lo ottiene.
    def test_order_dir_esplicito_vince(self) -> None:
        self.assertIn("ASC NULLS FIRST", self._sql_di(order_by=None, order_dir="asc"))

    # Scopo: il tiebreak segue la direzione primaria (decisione Tid 2026-08-03),
    #        non un `DESC` inchiodato: a parita' di eccedenza l'elenco non deve
    #        andare al contrario di come e' stato chiesto.
    def test_il_tiebreak_segue_la_direzione(self) -> None:
        self.assertRegex(self._sql_di(order_by=None, order_dir="asc"), r"t\.id ASC")
        self.assertRegex(self._sql_di(order_by=None, order_dir="desc"), r"t\.id DESC")

    # Scopo: pagina e conteggio condividono lo STESSO frammento FROM+WHERE.
    #        Se divergessero, il totale mentirebbe rispetto alle righe e il guard
    #        anti-troncamento del frontend suonerebbe (o tacerebbe) a sproposito.
    def test_pagina_e_conteggio_hanno_lo_stesso_perimetro(self) -> None:
        from apps.anagrafiche.db.titoli_iva_repository import _SFONDATI_FROM_WHERE

        sql = self._sql_di(order_by=None, order_dir=None)
        self.assertIn(_SFONDATI_FROM_WHERE, sql)

class TitoliSoggettoPaginazioneTests(TestCase):
    """La lista dei titoli di UN soggetto, paginata dal 2026-09-02.

    ⭐ Prima consegnava TUTTI i titoli in un colpo e il conteggio veniva da una
    query separata. Due valutazioni dello stesso predicato possono non
    concordare — una riga che entra fra l'una e l'altra fa dire al totale una
    popolazione diversa da quella mostrata. Ora sono la stessa valutazione.
    """

    def _sql_di(self, **kwargs) -> tuple[str, list]:
        return _cattura_sql(lambda repo: repo.list_titoli_soggetto(SOGG, **kwargs))

    # Scopo: senza `limit` NON si impagina — e' il secondo consumatore
    #        (`soggetti_service`, che incorpora i titoli nel dettaglio).
    # ⛔ Se comparisse un LIMIT di default, il dettaglio del soggetto mostrerebbe
    #    i primi N titoli e nessuno lo direbbe: e' esattamente il difetto
    #    corretto sulla lista degli sfondati.
    def test_senza_limit_non_impagina(self) -> None:
        sql, params = self._sql_di()
        self.assertNotIn("LIMIT", sql)
        self.assertEqual(params, [SOGG])

    def test_con_limit_impagina(self) -> None:
        sql, params = self._sql_di(limit=25, offset=50)
        self.assertIn("LIMIT %s OFFSET %s", sql)
        self.assertEqual(params, [SOGG, 25, 50])

    # Scopo: il totale viene dalla stessa valutazione della pagina.
    def test_il_totale_viaggia_con_la_pagina(self) -> None:
        sql, _ = self._sql_di(limit=25)
        self.assertIn("COUNT(*) OVER ()", sql)

    # Scopo: l'ordinamento STORICO regge se nessuno chiede altro. Questo metodo
    #        ha un secondo consumatore che non passa ordinamento: cambiargli il
    #        default sotto i piedi riordinerebbe il dettaglio del soggetto.
    def test_senza_order_by_resta_l_ordinamento_storico(self) -> None:
        sql, _ = self._sql_di()
        self.assertIn("COALESCE(t.valido_al, 'infinity'::date) DESC", sql)

    # Scopo: ⛔ una colonna fuori whitelist e' un 400 (`order_by_invalid`), e
    #        non arriva all'SQL (dal 2026-10-20, brief-be-verifica-documentazione-api §A1).
    def test_order_by_fuori_whitelist_e_rifiutato(self) -> None:
        with self.assertRaisesRegex(ValueError, "order_by_invalid"):
            self._sql_di(order_by="drop_table; --")

    # Scopo: `residuo` si ordina per ALIAS, non per l'espressione riscritta:
    #        e' un CASE che vale NULL sui tipi senza tetto, e una riscrittura
    #        darebbe un numero dove il residuo non significa niente — l'elenco
    #        si ordinerebbe diversamente da come si legge.
    def test_residuo_si_ordina_per_alias(self) -> None:
        from apps.anagrafiche.db.titoli_iva_repository import (
            _ORDER_COLS_TITOLI_SOGGETTO,
        )

        self.assertEqual(_ORDER_COLS_TITOLI_SOGGETTO["residuo"], "residuo")

    def test_il_tiebreak_segue_la_direzione(self) -> None:
        self.assertRegex(self._sql_di(order_by="iva_codice", order_dir="asc")[0],
                         r"t\.id ASC")
        self.assertRegex(self._sql_di(order_by="iva_codice", order_dir="desc")[0],
                         r"t\.id DESC")

    # Scopo: pagina e conteggio di ripiego condividono lo STESSO FROM+WHERE.
    def test_pagina_e_ripiego_hanno_lo_stesso_perimetro(self) -> None:
        from apps.anagrafiche.db.titoli_iva_repository import (
            _TITOLI_SOGGETTO_FROM_WHERE,
        )

        sql, _ = self._sql_di(limit=25)
        self.assertIn(_TITOLI_SOGGETTO_FROM_WHERE, sql)

    # Scopo: l'envelope del service e' `results` + `count`, come ogni altra
    #        lista configurabile — il frontend monta lo stesso scaffolding.
    def test_envelope_results_e_count(self) -> None:
        from apps.anagrafiche.services.titoli_iva_service import TitoliIvaService

        repo = MagicMock()
        repo.list_titoli_soggetto.return_value = ([_titolo(id=1)], 700)
        svc = TitoliIvaService()
        svc._repo = repo
        esito = svc.list_titoli_soggetto(SOGG, limit=1, offset=0)
        self.assertEqual(len(esito["results"]), 1)
        # ⛔ 700, non 1: il totale non e' la lunghezza della pagina.
        self.assertEqual(esito["count"], 700)
        repo.list_titoli_soggetto.assert_called_once_with(
            SOGG, limit=1, offset=0, order_by=None, order_dir=None,
        )

class AmbitiEMovimentiPaginazioneTests(TestCase):
    """Le due sotto-liste di `TitoloIvaDrawer`, paginate dal 2026-09-02.

    ⭐ Sono le liste 64 e 65 del catalogo, e il loro contratto DIVERGE di
    proposito: gli ambiti sono limitati per modello (montati `paginata: false`,
    dove il totale e' l'asserzione che le righe siano tutte), il registro dei
    movimenti CRESCE a ogni fattura e va impaginato. Un contratto solo per due
    nature diverse sarebbe comodo e sbagliato.
    """

    def test_ambiti_senza_limit_non_impaginano(self) -> None:
        sql, params = _cattura_sql(lambda repo: repo.list_ambiti(7))
        self.assertNotIn("LIMIT", sql)
        self.assertEqual(params, [7])

    def test_ambiti_dichiarano_il_totale(self) -> None:
        # ⛔ Il totale viene dalla query, non da `len(results)`: senza, il guard
        #    anti-troncamento del BB confronterebbe le righe con se stesse.
        sql, _ = _cattura_sql(lambda repo: repo.list_ambiti(7))
        self.assertIn("COUNT(*) OVER ()", sql)

    def test_ambiti_pagina_e_ripiego_stesso_perimetro(self) -> None:
        from apps.anagrafiche.db.titoli_iva_repository import _AMBITI_FROM_WHERE

        sql, _ = _cattura_sql(lambda repo: repo.list_ambiti(7, limit=25))
        self.assertIn(_AMBITI_FROM_WHERE, sql)

    def test_movimenti_impaginano_con_limit(self) -> None:
        sql, params = _cattura_sql(
            lambda repo: repo.list_movimenti(7, limit=25, offset=50),
        )
        self.assertIn("LIMIT %s OFFSET %s", sql)
        self.assertEqual(params, [7, 25, 50])

    # Scopo: senza `limit` il registro arriva INTERO, ed e' il caso dei due
    #        consumatori interni — il dettaglio del titolo e il controllo di
    #        appartenenza dell'annullo, che su una pagina guarderebbe meta'
    #        delle righe.
    def test_movimenti_senza_limit_arrivano_tutti(self) -> None:
        sql, params = _cattura_sql(lambda repo: repo.list_movimenti(7))
        self.assertNotIn("LIMIT", sql)
        self.assertEqual(params, [7])

    # Scopo: il default resta «il piu' recente per primo» — come si legge un
    #        registro. E' l'ordine che i due consumatori interni si aspettano.
    def test_movimenti_default_dal_piu_recente(self) -> None:
        sql, _ = _cattura_sql(lambda repo: repo.list_movimenti(7))
        self.assertIn("m.data_movimento DESC", sql)

    def test_movimenti_pagina_e_ripiego_stesso_perimetro(self) -> None:
        from apps.anagrafiche.db.titoli_iva_repository import _MOVIMENTI_FROM_WHERE

        sql, _ = _cattura_sql(lambda repo: repo.list_movimenti(7, limit=25))
        self.assertIn(_MOVIMENTI_FROM_WHERE, sql)

    # Scopo: gli envelope del service, che il frontend monta con lo stesso
    #        scaffolding delle altre liste.
    def test_envelope_results_e_count(self) -> None:
        from apps.anagrafiche.services.titoli_iva_service import TitoliIvaService

        repo = MagicMock()
        repo.get_titolo.return_value = _titolo()
        repo.list_ambiti.return_value = ([{"id": 1}], 3)
        repo.list_movimenti.return_value = ([{"id": 9}], 700)
        svc = TitoliIvaService()
        svc._repo = repo
        ambiti = svc.list_ambiti(SOGG, 7)
        movimenti = svc.list_movimenti(SOGG, 7, limit=1, offset=0)
        # ⛔ 3 e 700, non 1 e 1: il totale non e' la lunghezza della pagina.
        self.assertEqual((len(ambiti["results"]), ambiti["count"]), (1, 3))
        self.assertEqual((len(movimenti["results"]), movimenti["count"]), (1, 700))
