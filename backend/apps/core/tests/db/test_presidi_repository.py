# ------------------------------------------------------------
# SPDX-License-Identifier: GPL-3.0-or-later
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
"""

from __future__ import annotations

from contextlib import contextmanager
from typing import Any
from unittest.mock import MagicMock, patch

from django.test import SimpleTestCase

from apps.core.db import presidi_repository as modulo
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


class PresidiPannelloTests(SimpleTestCase):
    """Il giro del pannello, senza database: chi entra, chi resta fuori."""

    # Scopo: un repository vero con i tre lettori sostituiti — cosi' si prova il
    #        GIRO (chi si guarda, cosa si chiede, come si racconta un errore) e
    #        non il contenuto del dbdev di oggi.
    def _repo(self, catalogo, conteggi, righe=None):
        repo = PresidiRepository()
        righe = righe or {}

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
        self.assertEqual(len(stato), 3, "gli altri due presidi restano guardati")
        # E la connessione si rimette a posto, ma solo se e' inutilizzabile:
        # questo giro sta dentro una richiesta web.
        finta.close_if_unusable_or_obsolete.assert_called_once()
        finta.close.assert_not_called()
