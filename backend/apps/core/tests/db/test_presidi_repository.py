# ------------------------------------------------------------
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Le GUARDIE del lettore del catalogo dei presidi
#        (`apps.core.db.presidi_repository`), provate SENZA database.
# Note: ⭐ I casi si COSTRUISCONO, non si cercano nella popolazione. Un test che
#        scorresse le righe di oggi proverebbe i soli casi che il dbdev per caso
#        contiene, e passerebbe a vuoto su un database ricostruito da zero —
#        cioe' in CI (`.codex/AGENTS.md` §corollario sui test).
#        ⛔ `SimpleTestCase` e non `unittest.TestCase`: il secondo PERMETTE al
#        codice sotto test di parlare col database, quindi un mock dimenticato
#        non farebbe rosso — parlerebbe col DB di sviluppo.
# ------------------------------------------------------------

"""Indice test previsti (nessun database).

1. test_il_conteggio_passa_dalla_funzione_del_database
     ⭐ La prova del TRASPORTO: che il numero arrivi da `dbops.fn_conta_presidio`
     e non da un `count(*)` scritto nel repository — dove il filtro
     (colonna_stato, stato_atteso) non ci sarebbe e le tre viste in row level
     security tornerebbero zero per cecita'.
2. test_il_debito_in_attesa_si_conta_diretto
     L'unica eccezione, e muore da se': la funzione RIFIUTA una vista che il
     catalogo non conosce.
3. test_su_perimetro_definer_non_si_elencano_righe
     Il guard sta nel repository, non nel chiamante.
4. test_una_vista_con_un_nome_storto_viene_rifiutata
     Il nome finisce interpolato nell'SQL: il secondo giro di chiave.
5. test_il_debito_dichiarato_e_una_riga_di_catalogo_completa
     Le righe in attesa hanno la stessa forma delle altre: a video non si
     distinguono per un motivo che non c'entra col loro contenuto.
     ⚠️ Dal 2026-09-10 il registro e' A ZERO (debito pagato, brief §10.2),
     quindi questo test gira a VUOTO. ⭐ Il ramo che serve NON resta scoperto:
     lo copre il test 2, che si costruisce la riga invece di pescarla dal
     registro — ed e' il motivo per cui era scritto cosi'.
6. test_il_pannello_guarda_le_sole_viste_zero
     ⭐ La decisione di Tid del 2026-09-10: gli allarmi sono le `ZERO`. Una coda
     con righe e' lavoro in corso, e un pannello che mostra righe verdi insegna
     a leggere il verde come debito.
7. test_un_presidio_non_letto_diventa_una_riga_che_lo_dice
     ⛔ Non un 500 che spegne la schermata intera, e non uno zero che direbbe
     «tutto a posto» proprio mentre non si e' visto niente.
8. test_la_lettura_leggera_non_chiede_le_righe
     ⭐ Il pallino della topbar (2026-09-18): `con_righe=False` fa lo STESSO
     giro — stesse viste, stessi conteggi, stesso isolamento — e non chiama mai
     `prime_righe`. E' un parametro e non una copia del giro.
9. test_il_testo_per_chi_agisce_si_legge_per_vista_con_ripiego_su_it
     ⭐ 2026-10-06: il join e' su `vista` (non sull'id) e la lingua si sceglie
     come per `config.messaggi_errore` — la GUC della richiesta, poi `it`.
10. test_il_pannello_consegna_il_testo_per_chi_agisce
11. test_un_presidio_non_letto_non_consegna_un_azione
     ⛔ L'azione rimedia a righe accese: su un presidio che non si e' letto
     direbbe di sistemare una cosa che nessuno ha visto.
12. test_il_testo_delle_cause_si_cerca_per_causa_con_ripiego_nella_causa
     ⛔ 2026-10-10 (brief-db-presidio-processi-testo-per-causa §5.4.2): il testo
     di una causa e' quello con `variante = causa`, e la lingua ripiega DENTRO
     la causa — mai sul testo generico del presidio.
13. test_il_pannello_consegna_le_righe_per_causa
     ⭐ Il nome della colonna si legge da `colonna_variante`; un presidio senza
     variante consegna `cause` vuoto e non interroga il catalogo delle cause.
14. test_il_conteggio_per_causa_passa_dalla_sede_del_database   R-2, 10-10
     `SELECT … FROM dbops.fn_conta_presidio_per_variante(%s)`, non
     `SELECT fn(…)` (che consegna la tupla in un campo solo).
15. test_le_cause_partono_dai_conteggi_e_non_dal_campione   ⭐ R-2, 10-10
     §6.4.2: ogni causa accesa arriva col suo conteggio, anche senza righe nel
     campione; una riga accesa fra le due letture non si perde, e nessun
     gruppo conta meno delle righe che mostra.
16. test_su_perimetro_definer_le_cause_arrivano_coi_numeri   R-2, 10-10
     Le righe non si elencano, i conteggi per causa si'.
17. test_la_lettura_leggera_non_chiede_le_cause
"""

from __future__ import annotations

from contextlib import contextmanager
from typing import Any
from unittest.mock import MagicMock, patch

from django.test import SimpleTestCase

from apps.core.db import presidi_repository as modulo
from apps.core.middleware.user_language_middleware import (
    DEFAULT_LANGUAGE,
    GUC_NAME,
)
from apps.core.db.presidi_repository import (
    _IN_ATTESA_DI_CATALOGO,
    CADENZE,
    NATURE,
    PERIMETRI,
    PERIMETRO_DEFINER,
    PERIMETRO_LIBERO,
    PresidiRepository,
    RigaPresidio,
)


# Scopo: una riga di catalogo minima, con i soli campi che la guardia guarda.
#        Il resto e' riempito con valori validi per non far passare un caso
#        grazie a un campo mancante.
def _riga(**override: Any) -> RigaPresidio:
    base: dict[str, Any] = {
        "vista": "dbops.vw_finta",
        "natura": "ZERO",
        "colonna_stato": None,
        "stato_atteso": None,
        "registro": None,
        "presidiato_da": None,
        "cadenza": "GIORNALIERA",
        "perimetro": PERIMETRO_LIBERO,
        "nota": "riga di prova",
        "colonna_variante": None,
        # ⚠️ Senza testo per chi agisce, di default: e' il ripiego, e i casi
        #    col testo se lo costruiscono.
        "chi_agisce": None,
        "significato": None,
        "azione": None,
        "descrizione": None,
        "esiste": True,
        "a_catalogo": True,
    }
    base.update(override)
    return base  # type: ignore[return-value]


# Scopo: sostituisce la CONNESSIONE del repository con una finta, e ne espone il
#        cursore per leggere l'SQL eseguito.
# ⚠️ Si sostituisce l'intera `connection` del modulo, non il suo attributo
#    `cursor`: `SimpleTestCase` ci mette sopra il proprio blocco anti-database e
#    lo ritira a `tearDownClass` leggendone il wrapper — sfilarglielo da sotto fa
#    fallire lo smontaggio della classe, con cinque test verdi e un errore che
#    sembra di un altro. E' anche la convenzione gia' in uso nel progetto.
@contextmanager
def _cursore_finto(risposta: tuple = (7,)):
    cursore = MagicMock()
    cursore.fetchone.return_value = risposta
    cursore.__enter__ = MagicMock(return_value=cursore)
    cursore.__exit__ = MagicMock(return_value=False)
    finta = MagicMock()
    finta.cursor.return_value = cursore
    with patch.object(modulo, "connection", finta):
        yield cursore


class PresidiRepositoryGuardieTests(SimpleTestCase):
    """Le guardie del lettore, senza database."""

    def setUp(self) -> None:
        self.repo = PresidiRepository()

    # 1. ⭐ IL TRASPORTO. Il filtro «diverso dallo stato atteso» e l'attraversamento
    #    della row level security vivono DENTRO `dbops.fn_conta_presidio`: un
    #    `count(*)` scritto qui sarebbe la seconda sede del primo e la cecita'
    #    del secondo, e nessuno dei due difetti farebbe rosso da solo.
    def test_il_conteggio_passa_dalla_funzione_del_database(self) -> None:
        with _cursore_finto((3,)) as cursore:
            self.assertEqual(self.repo.conta(_riga()), 3)
        sql, params = cursore.execute.call_args[0]
        self.assertIn("dbops.fn_conta_presidio", sql)
        self.assertNotIn("count(*)", sql)
        self.assertEqual(params, ["dbops.vw_finta"])

    # 2. L'unica eccezione: il debito dichiarato. La funzione rifiuta una vista
    #    che il catalogo non conosce, quindi li' si conta diretto — e il ramo
    #    sparisce il giorno dell'iscrizione.
    def test_il_debito_in_attesa_si_conta_diretto(self) -> None:
        with _cursore_finto((1,)) as cursore:
            self.assertEqual(self.repo.conta(_riga(a_catalogo=False)), 1)
        sql = cursore.execute.call_args[0][0]
        self.assertIn("count(*)", sql)
        self.assertNotIn("fn_conta_presidio", sql)

    # 3. ⛔ Su `DEFINER` non si elencano righe, e non si arriva nemmeno al
    #    database: il conteggio onesto lo da' una funzione che le righe non le
    #    restituisce apposta, ed elencarle da un'altra strada consegnerebbe
    #    righe fuori perimetro.
    def test_su_perimetro_definer_non_si_elencano_righe(self) -> None:
        finta = MagicMock()
        with patch.object(modulo, "connection", finta):
            righe = self.repo.prime_righe(_riga(perimetro=PERIMETRO_DEFINER))
        self.assertEqual(righe, [])
        finta.cursor.assert_not_called()

    # 4. Il nome della vista viene da una TABELLA e finisce interpolato: un
    #    refuso non da' un errore di sintassi, da' una query su un'altra cosa.
    def test_una_vista_con_un_nome_storto_viene_rifiutata(self) -> None:
        for storto in ("dbops.presidi; DROP TABLE x", "senza_schema", "", "Dbops.Vw"):
            with self.subTest(vista=storto):
                finta = MagicMock()
                with patch.object(modulo, "connection", finta):
                    with self.assertRaises(ValueError):
                        self.repo.conta(_riga(vista=storto))
                finta.cursor.assert_not_called()

    # 5. Le righe in attesa di iscrizione devono avere la forma di una riga di
    #    catalogo: a video non si distinguono, ed e' voluto — l'unica differenza
    #    e' `a_catalogo`, che decide come si contano.
    # ⚠️ Dal 2026-09-10 il registro e' vuoto e questo ciclo non gira: e' un
    #    presidio DI FORMA, e senza righe non ha forma da guardare. Si riaccende
    #    da se' alla prossima vista in attesa — e non si trasforma in
    #    «la tupla dev'essere vuota», che punirebbe l'uso corretto del registro.
    def test_il_debito_dichiarato_e_una_riga_di_catalogo_completa(self) -> None:
        for riga in _IN_ATTESA_DI_CATALOGO:
            with self.subTest(vista=riga["vista"]):
                self.assertFalse(riga["a_catalogo"])
                self.assertIn(riga["natura"], NATURE)
                self.assertIn(riga["cadenza"], CADENZE)
                self.assertIn(riga["perimetro"], PERIMETRI)
                # ⛔ La nota e' NOT NULL a database per una ragione (la guida dei
                #    presidi §2): una voce senza motivo scritto non si aggiunge.
                #    Vale anche per la copia che tiene il posto.
                self.assertTrue(riga["nota"].strip())


    # 9. ⭐ Il TRASPORTO del testo per chi agisce. Il join e' su `vista` — la
    #    chiave della FK, non l'id, che vale su una macchina sola — e la lingua
    #    ha la stessa cascata di `script.fn_get_messaggio`: la GUC impostata dal
    #    middleware, poi `it`. ⚠️ SQL letta, non eseguita: che la query GIRI sul
    #    database vero lo prova `test_presidi_catalogo` (e2e).
    def test_il_testo_per_chi_agisce_si_legge_per_vista_con_ripiego_su_it(self) -> None:
        with _cursore_finto() as cursore:
            cursore.description = []
            cursore.fetchall.return_value = []
            self.repo.list_catalogo()
        sql, params = cursore.execute.call_args[0]
        self.assertIn("dbops.presidi_testi", sql)
        self.assertIn("pt.vista = p.vista", sql)
        # ⛔ Il testo del presidio e' quello SENZA variante: le varianti sono i
        #    testi per causa, e il `LIMIT 1` ne pescherebbe una a caso.
        self.assertIn("pt.variante IS NULL", sql)
        self.assertIn("current_setting(%s, true)", sql)
        self.assertEqual(params[:3], [GUC_NAME, DEFAULT_LANGUAGE, DEFAULT_LANGUAGE])
        for colonna in ("p.chi_agisce", "t.significato", "t.azione"):
            self.assertIn(colonna, sql)


class PresidiPannelloTests(SimpleTestCase):
    """Il giro del pannello, senza database: chi entra, chi resta fuori."""

    # Scopo: un repository vero con i tre lettori sostituiti — cosi' si prova il
    #        GIRO (chi si guarda, cosa si chiede, come si racconta un errore) e
    #        non il contenuto del dbdev di oggi.
    def _repo(self, catalogo, conteggi, righe=None, per_causa=None):
        repo = PresidiRepository()
        righe = righe or {}
        per_causa = per_causa or {}

        def _conta(riga):
            valore = conteggi[riga["vista"]]
            if isinstance(valore, Exception):
                raise valore
            return valore

        repo.list_catalogo = lambda **_kw: list(catalogo)  # type: ignore[method-assign]
        repo.conta = _conta  # type: ignore[method-assign]
        repo.prime_righe = (  # type: ignore[method-assign]
            lambda riga, **_kw: righe.get(riga["vista"], [])
        )
        repo.conta_per_variante = (  # type: ignore[method-assign]
            lambda riga: [
                {"variante": v, "conteggio": n}
                for v, n in per_causa.get(riga["vista"], [])
            ]
        )
        return repo

    # 6. ⭐ Il pannello guarda le `ZERO` e basta.
    def test_il_pannello_guarda_le_sole_viste_zero(self) -> None:
        repo = self._repo(
            [
                _riga(vista="dbops.vw_zero", natura="ZERO"),
                _riga(vista="dbops.vw_coda", natura="LAVORAZIONE"),
                _riga(vista="dbops.vw_inventario", natura="INVENTARIO"),
                _riga(vista="dbops.vw_cancello", natura="CANCELLO"),
                _riga(vista="dbops.vw_registro", natura="REGISTRO"),
            ],
            {"dbops.vw_zero": 2, "dbops.vw_coda": 9, "dbops.vw_inventario": 2035,
             "dbops.vw_cancello": 508, "dbops.vw_registro": 779},
            {"dbops.vw_zero": [{"x": 1}]},
        )
        stato = repo.stato_presidi()
        self.assertEqual([p["vista"] for p in stato], ["dbops.vw_zero"])
        self.assertEqual(stato[0]["conteggio"], 2)
        # Una riga su due: `troncato` lo dice, o «una» si leggerebbe come «tutte».
        self.assertTrue(stato[0]["troncato"])
        self.assertIsNone(stato[0]["errore"])
        # ⭐ «Chiede un occhio» viaggia nella riga: il pannello lo LEGGE, non
        #    lo ricalcola (2026-09-15).
        self.assertTrue(stato[0]["da_guardare"])

    # 7. ⛔ Un presidio che non si legge e' una riga che LO DICE.
    def test_un_presidio_non_letto_diventa_una_riga_che_lo_dice(self) -> None:
        repo = self._repo(
            [
                _riga(vista="dbops.vw_prima", natura="ZERO"),
                _riga(vista="dbops.vw_cade", natura="ZERO"),
                _riga(vista="dbops.vw_dopo", natura="ZERO"),
            ],
            {
                "dbops.vw_prima": 0,
                "dbops.vw_cade": RuntimeError("connessione persa"),
                "dbops.vw_dopo": 0,
            },
        )
        finta = MagicMock()
        with patch.object(modulo, "connection", finta):
            stato = repo.stato_presidi()
        caduta = next(p for p in stato if p["vista"] == "dbops.vw_cade")
        # ⛔ `None` e non `0`: «non letto» e «zero righe» sono opposti, e su questa
        #    schermata lo zero e' il verde.
        self.assertIsNone(caduta["conteggio"])
        self.assertIn("connessione persa", caduta["errore"])
        # Non letto = da guardare; i due letti a zero no.
        self.assertTrue(caduta["da_guardare"])
        self.assertFalse(
            next(p for p in stato if p["vista"] == "dbops.vw_prima")["da_guardare"],
        )
        self.assertEqual(len(stato), 3, "gli altri due presidi restano guardati")
        # E la connessione si rimette a posto, ma solo se e' inutilizzabile:
        # questo giro sta dentro una richiesta web.
        finta.close_if_unusable_or_obsolete.assert_called_once()
        finta.close.assert_not_called()

    # 8. ⭐ La lettura leggera: stesso giro, zero `prime_righe`.
    def test_la_lettura_leggera_non_chiede_le_righe(self) -> None:
        repo = self._repo(
            [
                _riga(vista="dbops.vw_zero", natura="ZERO"),
                _riga(vista="dbops.vw_cade", natura="ZERO"),
                _riga(vista="dbops.vw_coda", natura="LAVORAZIONE"),
            ],
            {"dbops.vw_zero": 2, "dbops.vw_cade": RuntimeError("giu'"),
             "dbops.vw_coda": 9},
            {"dbops.vw_zero": [{"x": 1}]},
        )
        chiamate = MagicMock(return_value=[{"x": 1}])
        repo.prime_righe = chiamate  # type: ignore[method-assign]
        with patch.object(modulo, "connection", MagicMock()):
            leggera = repo.stato_presidi(con_righe=False)
        chiamate.assert_not_called()
        # Stesse viste (le sole ZERO), stesso conteggio, stessa riga «non letta».
        self.assertEqual(
            [(p["vista"], p["conteggio"], bool(p["errore"])) for p in leggera],
            [("dbops.vw_zero", 2, False), ("dbops.vw_cade", None, True)],
        )
        # Senza righe non c'e' niente di «troncato», e le righe sono vuote.
        acceso = next(p for p in leggera if p["vista"] == "dbops.vw_zero")
        self.assertEqual(acceso["righe"], [])
        self.assertFalse(acceso["troncato"])
        self.assertTrue(acceso["da_guardare"])

    # 10. ⭐ Il pannello consegna i tre campi del testo per chi agisce, cosi'
    #     come il catalogo li ha letti: e' il FE a decidere l'ordine a video, ma
    #     non a ricostruirli.
    def test_il_pannello_consegna_il_testo_per_chi_agisce(self) -> None:
        repo = self._repo(
            [_riga(vista="dbops.vw_zero", natura="ZERO", chi_agisce="AMMINISTRATORE",
                   significato="cosa vuol dire", azione="cosa fare")],
            {"dbops.vw_zero": 1},
        )
        acceso = repo.stato_presidi()[0]
        self.assertEqual(
            (acceso["significato"], acceso["azione"], acceso["chi_agisce"]),
            ("cosa vuol dire", "cosa fare", "AMMINISTRATORE"),
        )
        # ⚠️ La descrizione resta: e' il «dettaglio tecnico» e il ripiego.
        self.assertIn("descrizione", acceso)

    # 11. ⛔ Non letto: il significato resta (dice COSA non si e' guardato),
    #     l'azione e chi agisce no.
    def test_un_presidio_non_letto_non_consegna_un_azione(self) -> None:
        repo = self._repo(
            [_riga(vista="dbops.vw_cade", natura="ZERO", chi_agisce="AMMINISTRATORE",
                   significato="cosa vuol dire", azione="cosa fare")],
            {"dbops.vw_cade": RuntimeError("giu'")},
        )
        with patch.object(modulo, "connection", MagicMock()):
            caduto = repo.stato_presidi()[0]
        self.assertEqual(caduto["significato"], "cosa vuol dire")
        self.assertIsNone(caduto["azione"])
        self.assertIsNone(caduto["chi_agisce"])

    # 13. ⭐ Le righe per causa, col testo e il «chi agisce» della causa. La
    #     colonna si chiama apposta `motivo`: il nome viene dal catalogo.
    def test_il_pannello_consegna_le_righe_per_causa(self) -> None:
        repo = self._repo(
            [
                _riga(vista="dbops.vw_a", natura="ZERO", colonna_variante="motivo"),
                _riga(vista="dbops.vw_b", natura="ZERO"),
            ],
            {"dbops.vw_a": 2, "dbops.vw_b": 1},
            {"dbops.vw_a": [{"id": 1, "motivo": "X"}, {"id": 2, "motivo": "Y"}],
             "dbops.vw_b": [{"id": 3}]},
            {"dbops.vw_a": [("X", 1), ("Y", 1)]},
        )
        chieste: list[str] = []

        def _testi(vista):
            chieste.append(vista)
            return {"X": {"causa": "X", "chi_agisce": "SVILUPPO",
                          "significato": "s-x", "azione": "a-x"}}

        repo.testi_delle_cause = _testi  # type: ignore[method-assign]
        a, b = repo.stato_presidi()
        self.assertEqual(
            [(c["causa"], c["chi_agisce"], c["azione"], [r["id"] for r in c["righe"]])
             for c in a["cause"]],
            [("X", "SVILUPPO", "a-x", [1]), ("Y", None, None, [2])],
        )
        self.assertEqual(b["cause"], [])
        self.assertEqual(chieste, ["dbops.vw_a"])

    # 15. ⭐ Dai CONTEGGI (§6.4.2). `Z` non ha righe nel campione e arriva lo
    #     stesso; `W` ha una riga ma i conteggi non la conoscono (accesa fra le
    #     due letture): arriva in coda, contata almeno quanto mostra. `X` conta
    #     meno delle righe mostrate: sale al loro numero.
    def test_le_cause_partono_dai_conteggi_e_non_dal_campione(self) -> None:
        repo = self._repo(
            [_riga(vista="dbops.vw_a", natura="ZERO", colonna_variante="motivo")],
            {"dbops.vw_a": 9},
            {"dbops.vw_a": [{"id": 1, "motivo": "X"}, {"id": 2, "motivo": "X"},
                            {"id": 3, "motivo": "W"}]},
            {"dbops.vw_a": [("X", 1), ("Z", 7), (None, 1)]},
        )
        repo.testi_delle_cause = lambda vista: {}  # type: ignore[method-assign]
        (a,) = repo.stato_presidi()
        self.assertEqual(
            [(c["causa"], c["conteggio"], len(c["righe"])) for c in a["cause"]],
            [("X", 2, 2), ("Z", 7, 0), (None, 1, 0), ("W", 1, 1)],
        )

    # 16. Perimetro DEFINER: nessuna riga, ma le cause e i loro numeri si'.
    def test_su_perimetro_definer_le_cause_arrivano_coi_numeri(self) -> None:
        repo = self._repo(
            [_riga(vista="dbops.vw_a", natura="ZERO", colonna_variante="motivo",
                   perimetro=PERIMETRO_DEFINER)],
            {"dbops.vw_a": 3},
            per_causa={"dbops.vw_a": [("X", 3)]},
        )
        repo.testi_delle_cause = lambda vista: {}  # type: ignore[method-assign]
        (a,) = repo.stato_presidi()
        self.assertEqual(a["righe"], [])
        self.assertEqual([(c["causa"], c["conteggio"]) for c in a["cause"]], [("X", 3)])

    # 17. Il pallino della topbar non consegna le cause: e' un numero solo. Su
    #     un presidio a cause quel numero e' la somma per causa, e si legge una
    #     volta sola (nessun `conta` accanto).
    def test_la_lettura_leggera_non_consegna_le_cause(self) -> None:
        repo = self._repo(
            [_riga(vista="dbops.vw_a", natura="ZERO", colonna_variante="motivo")],
            {"dbops.vw_a": RuntimeError("seconda lettura")},
            per_causa={"dbops.vw_a": [("X", 2), ("Y", 1)]},
        )
        (a,) = repo.stato_presidi(con_righe=False)
        self.assertIsNone(a["errore"])
        self.assertEqual(a["conteggio"], 3)
        self.assertEqual(a["cause"], [])

    # 18. ⭐ Il totale di un presidio a cause E' la somma per causa: una
    #     lettura, e le due cifre non possono dire cose diverse. Senza cause,
    #     o fuori catalogo, resta `conta`.
    def test_il_totale_di_un_presidio_a_cause_e_la_somma_per_causa(self) -> None:
        repo = self._repo(
            [
                _riga(vista="dbops.vw_a", natura="ZERO", colonna_variante="motivo"),
                _riga(vista="dbops.vw_b", natura="ZERO"),
                _riga(vista="dbops.vw_c", natura="ZERO", colonna_variante="motivo",
                      a_catalogo=False),
            ],
            {"dbops.vw_a": 99, "dbops.vw_b": 4, "dbops.vw_c": 5},
            per_causa={"dbops.vw_a": [("X", 2), (None, 1)]},
        )
        self.assertEqual(repo.conta_presidio(_riga(vista="dbops.vw_a", colonna_variante="motivo")),
                         (3, [{"variante": "X", "conteggio": 2},
                              {"variante": None, "conteggio": 1}]))
        self.assertEqual(repo.conta_presidio(_riga(vista="dbops.vw_b")), (4, None))
        self.assertEqual(
            repo.conta_presidio(_riga(vista="dbops.vw_c", colonna_variante="motivo",
                                      a_catalogo=False)),
            (5, None),
        )


class PresidiTestiCauseTests(SimpleTestCase):
    """Il testo delle cause: quale riga di `presidi_testi`, in che lingua."""

    # 14. Il conteggio per causa: la sede a database, letta come tabella.
    def test_il_conteggio_per_causa_passa_dalla_sede_del_database(self) -> None:
        with _cursore_finto() as cursore:
            cursore.fetchall.return_value = [("A", 2), (None, 1)]
            esito = PresidiRepository().conta_per_variante(_riga())
        sql, params = cursore.execute.call_args[0]
        self.assertIn("FROM dbops.fn_conta_presidio_per_variante(%s)", sql)
        self.assertEqual(params, ["dbops.vw_finta"])
        self.assertEqual(
            esito, [{"variante": "A", "conteggio": 2}, {"variante": None, "conteggio": 1}],
        )

    # 12. ⛔ `variante = causa`, lingua richiesta poi `it` della STESSA causa.
    #     ⚠️ SQL letta, non eseguita: che giri sul database vero lo prova
    #     `test_presidi_catalogo`.
    def test_il_testo_delle_cause_si_cerca_per_causa_con_ripiego_nella_causa(self) -> None:
        with _cursore_finto() as cursore:
            cursore.description = []
            cursore.fetchall.return_value = []
            PresidiRepository().testi_delle_cause("dbops.vw_a")
        sql, params = cursore.execute.call_args[0]
        self.assertIn("dbops.presidi_cause c", sql)
        self.assertIn("pt.variante = c.causa", sql)
        self.assertNotIn("variante IS NULL", sql)
        self.assertEqual(params, [GUC_NAME, DEFAULT_LANGUAGE, DEFAULT_LANGUAGE, "dbops.vw_a"])
