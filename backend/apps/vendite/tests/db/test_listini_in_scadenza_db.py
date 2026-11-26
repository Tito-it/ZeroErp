# ------------------------------------------------------------
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Le scadenze dei listini lette dalle DUE liste sul DB vero, coi casi
#        COSTRUITI: la lista listini (`in_scadenza`, il filtro del badge) e la
#        lista versioni (`giorni_alla_scadenza`). ⭐ Dal 2026-10-31 la regola e'
#        del DB (`vendite.fn_listini_in_scadenza_senza_successore`, la prova
#        intera e' il suo pgTAP): qui si prova che il backend la LEGGE — il
#        LEFT JOIN, il filtro e la colonna, che i test con i mock non vedono.
#        Nato il 2026-10-21 (brief-be-verifica-documentazione-api §C1) sulla
#        query del repository `listini_in_scadenza`, ritirata; il difetto di
#        allora resta il caso da presidiare:
#        `validita` e' `daterange(valido_dal, valido_al, '[]')`, che PostgreSQL
#        normalizza in `[)`: `upper(validita)` e' `valido_al + 1`. La query
#        leggeva la scadenza e il successore da `upper()`, quindi:
#          - un successore CONTIGUO (`valido_dal = valido_al + 1`, il caso
#            normale) non contava, perche' `valido_dal > upper()` e' falso: la
#            versione risultava «in scadenza senza successore»;
#          - `valido_al` e `giorni_rimanenti` uscivano con un giorno in piu'.
#        ⚠️ Scadenza a 5 giorni: dentro il preavviso del seed
#        (`LISTINI_SCADENZA_PREAVVISO_GIORNI` = 15).
#        ⚠️ Opt-in `ZEROERP_TEST_DB_E2E=1`; tutto in una transazione annullata.
# ------------------------------------------------------------
"""
Indice test eseguiti:
1) ListiniInScadenzaDbTests.test_senza_successore_e_in_scadenza_col_giorno_giusto
2) ListiniInScadenzaDbTests.test_il_successore_contiguo_la_toglie_dall_alert
3) ListiniInScadenzaDbTests.test_il_filtro_non_in_scadenza_e_il_complemento
   Il ramo `in_scadenza=False` (`s.listino_id IS NULL`): il listino con il
   successore c'e', quello senza no — e il listino senza fine c'e' sempre.
4) ListiniInScadenzaDbTests.test_valido_al_vuoto_e_la_versione_piu_lontana
   `order_by=valido_al` delle versioni: la fine vuota ordina come il massimo,
   in fondo crescendo e in cima calando. Lo dichiara il catalogo della lista
   (`vuoto_ordinato_come_massimo`, brief-db-lista-colonna-vuoto-in-ordine),
   letto qui dal DB vero come lo legge la base view.
5) ListiniInScadenzaDbTests.test_chi_non_scade_va_in_fondo_crescendo
   `order_by=giorni_alla_scadenza` dei listini: il NULL («non in scadenza»)
   e' la scadenza piu' lontana, non la minima. Lo dichiara il catalogo della
   lista (D-5 di brief-db-lista-colonna-vuoto-in-ordine), letto dal DB vero
   come per le versioni.
"""
from __future__ import annotations

import unittest
from collections.abc import Callable
from typing import Any, TypeVar
from uuid import uuid4

from django.db import connection, transaction

from apps.core.db.lista_catalogo_repository import fetch_colonne_vuoto_massimo
from apps.core.services.request_context import imposta_vuoti_come_massimo
from apps.core.tests.db_e2e import richiedi_db_provvisto
from apps.vendite.db.listini_repository import ListiniRepository

T = TypeVar("T")


# Scopo: legge `leggi()` con la dichiarazione «vuoto come il massimo» del
#        catalogo di `lista`, letta dal DB vero e registrata come la registra
#        la base view (`applica_vuoti_come_massimo`).
def _con_la_dichiarazione(lista: str, leggi: Callable[[], T]) -> T:
    imposta_vuoti_come_massimo(lambda: fetch_colonne_vuoto_massimo(lista))
    try:
        return leggi()
    finally:
        imposta_vuoti_come_massimo(None)


class ListiniInScadenzaDbTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        richiedi_db_provvisto()

    # Scopo: un listino con la versione ATTIVA che scade fra 5 giorni; se
    #        `successore`, una BOZZA che parte il giorno dopo e non finisce.
    #        Accanto, un secondo listino della stessa utility che non finisce
    #        (fine vuota: non scade, `giorni_alla_scadenza` NULL). Ritorna le
    #        letture delle due liste, prese nella transazione annullata.
    def _letture(self, *, successore: bool) -> dict[str, Any]:
        etichetta = f"scadenza {uuid4().hex[:8]}"
        with transaction.atomic():
            try:
                with connection.cursor() as cur:
                    cur.execute(
                        "SELECT m.utility_id, (SELECT script.fn_data_operativa()) AS oggi"
                        "  FROM dbops.fn_pgtap_crea_mondo_cliente(%s) m",
                        [etichetta],
                    )
                    utility_id, oggi = cur.fetchone()
                    cur.execute(
                        "SELECT * FROM dbops.fn_pgtap_crea_listino(%s, %s, %s::date - 10, %s::date + 5)",
                        [utility_id, etichetta, oggi, oggi],
                    )
                    listino_id, versione_id, _tipologia = cur.fetchone()
                    cur.execute(
                        "SELECT * FROM dbops.fn_pgtap_crea_listino(%s, %s, %s::date - 10, NULL)",
                        [utility_id, f"{etichetta} aperto", oggi],
                    )
                    aperto_id = cur.fetchone()[0]
                    successore_id = None
                    if successore:
                        # Nasce BOZZA (lo stato iniziale, giro 12): lo stato
                        # non si scrive.
                        cur.execute(
                            "INSERT INTO vendite.listini_versioni"
                            " (listino_id, codice_versione, valido_dal, valido_al)"
                            " VALUES (%s, 'PGTAP_V2', %s::date + 6, NULL) RETURNING id",
                            [listino_id, oggi],
                        )
                        successore_id = cur.fetchone()[0]
                repo = ListiniRepository()
                nostri = (listino_id, aperto_id)

                # I listini della utility (solo i due del test, nell'ordine
                # della pagina) per ogni valore del filtro, con la
                # dichiarazione del catalogo della lista.
                def listini(**kw: Any) -> list[dict]:
                    righe, _ = _con_la_dichiarazione("vendite.listini", lambda: repo.list_listini(
                        utility_id=utility_id, tipologia_id=None, attivo=None, search=None,
                        limit=500, offset=0, **{"order_by": "codice", "order_dir": None, **kw},
                    ))
                    return [r for r in righe if r["id"] in nostri]

                # Gli id delle versioni del listino, nell'ordine della pagina,
                # con la dichiarazione del catalogo della lista.
                def versioni(**kw: Any) -> list[int]:
                    return _con_la_dichiarazione(
                        "vendite.listini_versioni",
                        lambda: [v["id"] for v in repo.list_versioni_pagina(listino_id, **kw)[0]],
                    )

                tutte, _ = repo.list_versioni_pagina(listino_id)
                return {
                    "listino_id": listino_id,
                    "aperto_id": aperto_id,
                    "versione_id": versione_id,
                    "successore_id": successore_id,
                    "in_scadenza": listini(in_scadenza=True),
                    "non_in_scadenza": listini(in_scadenza=False),
                    "giorni": {v["id"]: v["giorni_alla_scadenza"] for v in tutte},
                    "versioni_valido_al": {
                        verso: versioni(order_by="valido_al", order_dir=verso)
                        for verso in ("asc", "desc", None)
                    },
                    "listini_giorni": {
                        verso: [
                            r["id"] for r in listini(order_by="giorni_alla_scadenza", order_dir=verso)
                        ]
                        for verso in ("asc", "desc")
                    },
                }
            finally:
                transaction.set_rollback(True)

    def test_senza_successore_e_in_scadenza_col_giorno_giusto(self) -> None:
        letture = self._letture(successore=False)
        righe = letture["in_scadenza"]
        self.assertEqual([r["id"] for r in righe], [letture["listino_id"]])
        self.assertEqual(righe[0]["giorni_alla_scadenza"], 5)
        self.assertEqual(letture["giorni"], {letture["versione_id"]: 5})

    def test_il_successore_contiguo_la_toglie_dall_alert(self) -> None:
        letture = self._letture(successore=True)
        self.assertEqual(letture["in_scadenza"], [])
        self.assertIsNone(letture["giorni"][letture["versione_id"]])

    # ⭐ Il ramo `False` del filtro e' il complemento del `True`, non «tutti»:
    #    il listino col successore e' fra i non in scadenza (e non fra gli
    #    altri), quello senza successore no; il listino aperto c'e' sempre.
    def test_il_filtro_non_in_scadenza_e_il_complemento(self) -> None:
        con = self._letture(successore=True)
        self.assertEqual(
            {r["id"] for r in con["non_in_scadenza"]}, {con["listino_id"], con["aperto_id"]},
        )
        self.assertTrue(all(r["giorni_alla_scadenza"] is None for r in con["non_in_scadenza"]))
        senza = self._letture(successore=False)
        self.assertEqual([r["id"] for r in senza["non_in_scadenza"]], [senza["aperto_id"]])

    # La versione senza fine (il successore) e' la piu' lontana: ultima
    # crescendo, prima calando; senza verso la colonna va crescente (dal
    # 2026-11-24 nessuna data ha un verso di partenza proprio). Senza la
    # dichiarazione del catalogo il NULL sarebbe il minimo del BB e i due versi
    # si scambierebbero.
    def test_valido_al_vuoto_e_la_versione_piu_lontana(self) -> None:
        letture = self._letture(successore=True)
        attesa = [letture["versione_id"], letture["successore_id"]]
        ordini = letture["versioni_valido_al"]
        self.assertEqual(ordini["asc"], attesa)
        self.assertEqual(ordini["desc"], attesa[::-1])
        self.assertEqual(ordini[None], attesa)

    # Il listino che scade fra 5 giorni prima di quello che non scade: il NULL
    # crescendo va in fondo, calando in cima. Senza la dichiarazione del
    # catalogo il NULL sarebbe il minimo del BB e i due versi si scambierebbero.
    def test_chi_non_scade_va_in_fondo_crescendo(self) -> None:
        letture = self._letture(successore=False)
        attesa = [letture["listino_id"], letture["aperto_id"]]
        self.assertEqual(letture["listini_giorni"]["asc"], attesa)
        self.assertEqual(letture["listini_giorni"]["desc"], attesa[::-1])
