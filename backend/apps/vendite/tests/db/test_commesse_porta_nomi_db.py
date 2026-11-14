# ------------------------------------------------------------
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: I NOMI con cui il backend parla alla porta delle righe di commessa,
#        confrontati col DB vero: ogni `p_… =>` di `upsert_attivita` è un
#        parametro di `vendite.fn_upsert_commessa_attivita`, e ogni chiave che
#        `batch_upsert_attivita` mette in una riga è letta da
#        `vendite.fn_batch_upsert_commessa_attivita`.
# Note: ⛔ Sono i due punti di TRASPORTO del push, e un nome sbagliato si
#        comporta in due modi diversi: nella madre (argomenti per nome) è un
#        errore a runtime; nel batch è una chiave che nessuno legge, cioè un
#        NULL passato in silenzio. I test coi mock vedono il testo che il
#        backend scrive, non quello che il DB si aspetta: lo sa solo il
#        catalogo. Nato col giro K.1 di brief-db-sorgente-documento-e-riga
#        (2026-11-07), che ha rinominato `p_sorgente_uid` in
#        `p_sorgente_chiave` e la chiave del batch `sorgente_uid` in
#        `sorgente_chiave`. Il terzo punto (la LETTURA delle colonne dei
#        cinque lister del push) col giro K.2 (2026-11-08, BE-K.2-a), che ha
#        rinominato la colonna `sorgente_uid` in `sorgente_chiave`.
# ------------------------------------------------------------
"""Indice test (su DB provvisto, `ZEROERP_TEST_DB_E2E=1`).

1. test_parametri_della_madre
     ogni argomento per nome di `upsert_attivita` esiste nella firma.
2. test_chiavi_del_batch
     ogni chiave di una riga del batch è letta dal wrapper (`v_row ->> '…'`).
3. test_colonne_dei_lister
     ogni colonna che `fetch_pushable_rows` legge per nome esce dai cinque
     `fn_list_*_da_pushare`; le opzionali da almeno uno.
4. test_argomenti_posizionali_dei_lister
     gli argomenti che `fetch_pushable_rows` passa PER POSIZIONE sono, in
     ordine, competenza, billing account, limite, id del documento (e
     `p_righe_ids` dove il repository lo passa).
5. test_proiezione_dei_componenti_per_il_push
     la proiezione dei componenti con la provenienza (K-4 di
     brief-db-provenienza-prezzo-segue-il-prezzo) gira sulle cinque tabelle e
     restituisce ogni colonna `prov_*` che il push legge.
"""

from __future__ import annotations

import re
from datetime import date
from decimal import Decimal
from unittest import TestCase
from unittest.mock import MagicMock, patch

from django.db import connection

from apps.core.tests.db_e2e import richiedi_db_provvisto
from apps.vendite.db._provenienza_prezzo import COLONNA_DEL_LISTER, PREFISSO_COMPONENTE
from apps.vendite.db.contratti_repository import ContrattiRepository
from apps.vendite.db.ddt_repository import DdtRepository
from apps.vendite.db.offerte_repository import OfferteRepository
from apps.vendite.db.ordini_repository import OrdiniRepository
from apps.vendite.db.preventivi_repository import PreventiviRepository
from apps.vendite.db.commesse_repository import (
    _PUSHABLE_OPTIONAL_COLS,
    _PUSHABLE_SHARED_COLS,
    _SORGENTE_SUPPORTA_RIGHE_IDS,
    _SORGENTE_FN_MAP,
    CommessaAttivitaInput,
    CommesseRepository,
)

_MADRE = (
    "vendite.fn_upsert_commessa_attivita"
)
_BATCH = "vendite.fn_batch_upsert_commessa_attivita(jsonb)"

# Una riga qualsiasi: si guardano i NOMI, non i valori.
_INPUT = CommessaAttivitaInput(
    commessa_id=1, segment_key="K", quantita=Decimal("1"),
    competenza_mese=date(2026, 6, 1), articolo_id=None, prezzo_snapshot=None,
    sorgente_tipo_id=1, sorgente_chiave="1", sorgente_riga=1,
)


class CommessePortaNomiDbTests(TestCase):

    @classmethod
    def setUpClass(cls) -> None:
        super().setUpClass()
        richiedi_db_provvisto(_BATCH)

    # 1. Gli argomenti per nome della chiamata alla madre, catturati dal
    #    repository vero con un cursore finto, contro `proargnames`.
    def test_parametri_della_madre(self) -> None:
        finto = MagicMock()
        cur = finto.cursor.return_value.__enter__.return_value
        cur.fetchone.return_value = (1, True)
        with patch("apps.vendite.db.commesse_repository.connection", finto):
            CommesseRepository().upsert_attivita(_INPUT)
        sql = cur.execute.call_args[0][0]
        inviati = set(re.findall(r"\b(p_[a-z0-9_]+)\s*=>", sql))
        self.assertIn("p_sorgente_chiave", inviati)

        with connection.cursor() as c:
            c.execute(
                "SELECT DISTINCT unnest(p.proargnames) FROM pg_proc p"
                " WHERE p.oid = %s::regproc",
                [_MADRE],
            )
            firma = {r[0] for r in c.fetchall()}
        self.assertTrue(firma, "firma della madre vuota: il catalogo non risponde")
        self.assertEqual(inviati - firma, set(), "argomenti che la madre non ha")

    # 2. Le chiavi di una riga del batch contro le chiavi che il corpo del
    #    wrapper legge. ⛔ Una chiave inviata e non letta è il difetto che non
    #    dà errore. (Il contrario, una chiave letta e non inviata, è un default
    #    della madre, ed è ammesso.)
    def test_chiavi_del_batch(self) -> None:
        inviate = set(CommesseRepository()._inp_to_jsonb_row(_INPUT))
        self.assertIn("sorgente_chiave", inviate)

        with connection.cursor() as c:
            c.execute("SELECT pg_get_functiondef(%s::regprocedure)", [_BATCH])
            corpo = c.fetchone()[0]
        lette = set(re.findall(r"v_row\s*->>?\s*'([a-z0-9_]+)'", corpo))
        self.assertTrue(lette, "nessuna chiave letta: il corpo ha cambiato forma")
        self.assertEqual(inviate - lette, set(), "chiavi che il batch non legge")

    # 3. Le colonne dei lister contro la RETURNS TABLE del catalogo. ⛔ Il
    #    binding le cerca per nome e la whitelist `_PUSHABLE_SHARED_COLS` è il
    #    cancello: una colonna obbligatoria che il lister non ha più rompe
    #    ogni riga del push (`KeyError`); un'opzionale che nessun lister ha è
    #    un None passato in silenzio. I test coi mock vedono la lista che il
    #    backend si è scritto da sé.
    def test_colonne_dei_lister(self) -> None:
        # Un'opzionale fuori dalla whitelist non entrerebbe mai in `col_map`.
        self.assertLessEqual(_PUSHABLE_OPTIONAL_COLS, set(_PUSHABLE_SHARED_COLS))
        obbligatorie = set(_PUSHABLE_SHARED_COLS) - _PUSHABLE_OPTIONAL_COLS
        self.assertIn("sorgente_chiave", obbligatorie)
        uscite_da_qualcuno: set[str] = set()
        for codice, fn in _SORGENTE_FN_MAP.items():
            schema, nome = fn.split(".")
            with connection.cursor() as c:
                c.execute(
                    "SELECT a.nome FROM pg_proc p"
                    " JOIN pg_namespace n ON n.oid = p.pronamespace,"
                    " LATERAL unnest(p.proargnames, p.proargmodes::text[])"
                    "   AS a(nome, modo)"
                    " WHERE n.nspname = %s AND p.proname = %s AND a.modo = 't'",
                    [schema, nome],
                )
                colonne = {r[0] for r in c.fetchall()}
            with self.subTest(sorgente=codice):
                self.assertTrue(colonne, f"{fn}: RETURNS TABLE vuota o fn assente")
                self.assertEqual(
                    obbligatorie - colonne, set(),
                    f"{fn}: colonne lette dal backend che il lister non restituisce",
                )
            uscite_da_qualcuno |= colonne
        self.assertEqual(
            _PUSHABLE_OPTIONAL_COLS - uscite_da_qualcuno, set(),
            "colonne opzionali che nessun lister restituisce",
        )

    # 4. ⛔ Gli argomenti per POSIZIONE: il 4° ha un nome diverso per lister
    #    (`p_preventivo_id`, `p_ordine_id`, …) e il repository non può
    #    nominarlo. Un ordine cambiato a DB manderebbe l'id del documento in
    #    un altro filtro senza errore, se il tipo combacia.
    def test_argomenti_posizionali_dei_lister(self) -> None:
        for codice, fn in _SORGENTE_FN_MAP.items():
            schema, nome = fn.split(".")
            with connection.cursor() as c:
                c.execute(
                    "SELECT a.nome, format_type(a.tipo, NULL) FROM pg_proc p"
                    " JOIN pg_namespace n ON n.oid = p.pronamespace,"
                    " LATERAL unnest(p.proargnames[1:p.pronargs], p.proargtypes::oid[])"
                    "   WITH ORDINALITY AS a(nome, tipo, pos)"
                    " WHERE n.nspname = %s AND p.proname = %s ORDER BY a.pos",
                    [schema, nome],
                )
                argomenti = c.fetchall()
            with self.subTest(sorgente=codice):
                self.assertGreaterEqual(len(argomenti), 4, f"{fn}: meno di 4 argomenti")
                self.assertEqual(
                    [a[0] for a in argomenti[:3]],
                    ["p_competenza_mese", "p_billing_account_id", "p_limit"],
                    f"{fn}: i primi tre argomenti non sono quelli che il repository passa",
                )
                quarto, tipo_quarto = argomenti[3]
                self.assertRegex(quarto, r"^p_[a-z_]+_id$", f"{fn}: il 4° non è l'id del documento")
                self.assertEqual(tipo_quarto, "bigint", f"{fn}: il 4° non è un id")
                if codice in _SORGENTE_SUPPORTA_RIGHE_IDS:
                    self.assertGreaterEqual(len(argomenti), 5, f"{fn}: manca p_righe_ids")
                    self.assertEqual(argomenti[4], ("p_righe_ids", "bigint[]"))

    # 5. La proiezione dei componenti per il push, eseguita davvero: il
    #    `LATERAL` sul BB del DB e i nomi delle sue colonne li vede solo il DB.
    #    Una riga che non c'e' basta: si guardano le colonne della risposta.
    def test_proiezione_dei_componenti_per_il_push(self) -> None:
        attese = {PREFISSO_COMPONENTE + c for c in COLONNA_DEL_LISTER.values()}
        for repo_cls in (
            PreventiviRepository, OrdiniRepository, ContrattiRepository,
            DdtRepository, OfferteRepository,
        ):
            with self.subTest(repository=repo_cls.__name__):
                with patch(
                    "apps.vendite.db._componenti_repo_mixin.rows_to_list",
                    side_effect=lambda cur: [{d[0] for d in cur.description}],
                ):
                    (colonne,) = repo_cls().list_componenti_riga(-1, con_provenienza=True)
                self.assertEqual(attese - colonne, set(), "colonne prov_* mancanti")
                self.assertIn("origine_prezzo", colonne)
