# ------------------------------------------------------------
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Il prerequisito comune ai test che hanno bisogno del DB VERO — quello
#        configurato, con lo schema Liquibase completo — e non di un database
#        usa-e-getta creato dal test runner.
#
#        PERCHE' UN POSTO SOLO. Questo guard non e' tre righe di comodo: e' il
#        punto in cui il progetto paga una dipendenza implicita, e il giorno in
#        cui quella dipendenza cadra' va sanato **una volta**, non cercandone le
#        copie. Chi lo usa oggi:
#          · apps/core/tests/services/test_db_error_fields.py  (3 e2e)
#          · apps/core/tests/test_error_codes_db_policy_guardrail.py (cancello)
#
#        ⚠️ LA DIPENDENZA IMPLICITA, in breve. Django crea il database di test
#        usa-e-getta SOLO se almeno un test dichiara di averne bisogno
#        (`django.test.TestCase`, `TransactionTestCase`, o `databases = [...]`).
#        Oggi in `backend/apps` nessuno lo dichiara, quindi il runner stampa
#        «Skipping setup of unused database(s)» e la connessione dei test resta
#        quella CONFIGURATA — un database con lo schema Liquibase completo, dove
#        le funzioni PL/pgSQL esistono davvero. Il primo test che dichiarera' un
#        database fara' creare al runner un DB con le sole migration Django, per
#        TUTTA la suite: li' `script.fn_log_and_raise_error` non esiste.
#        Vedi `.codex/AGENTS.md` §Regole test Django e
#        `brief-be-e2e-db-error-fields-skip-schema.md`.
#
#        ⚠️ NIENTE CONTATTO COL DB A IMPORT TIME. Questo modulo non apre
#        connessioni quando viene importato, e le funzioni qui dentro vanno
#        chiamate da `setUpClass`, mai da un decoratore. La prima versione del
#        guard usava `@skipUnless(_db_raggiungibile(), ...)`: l'argomento si
#        valuta all'import, quindi il probe apriva una connessione durante la
#        *discovery*, prima che il runner predisponesse i database — e 469 test
#        di altre app diventavano rossi. Un test che rompe i test degli altri e'
#        peggio di un test che manca.
# ------------------------------------------------------------

from __future__ import annotations

import os
import re
import unittest

# Interruttore unico: i test che hanno bisogno del DB vero sono spenti di
# default (in CI e' `ci-validate.yaml` ad accenderlo, sullo step «Django tests»,
# dove il database e' appena stato provvisto da Liquibase).
FLAG_DB_E2E = "ZEROERP_TEST_DB_E2E"

# Sonda dello schema Liquibase: se questa funzione non c'e', il database dei
# test non e' quello configurato ma uno usa-e-getta creato dal runner.
SONDA_SCHEMA_LIQUIBASE = "script.fn_log_and_raise_error(text,text,text,jsonb,uuid,text[])"


# Scopo: prerequisito dei test che interrogano il database vero. Solleva
#        `unittest.SkipTest` — e non un fallimento — nei tre casi in cui il
#        database non e' quello previsto: flag spenta, DB irraggiungibile,
#        schema Liquibase assente. Va chiamata da `setUpClass`, mai a import
#        time (vedi l'header). Non apre transazioni e non scrive nulla.
#
#        ⚠️ Skip, non fallimento, ed e' una scelta: in tutti e tre i casi il
#        difetto non e' nel codice sotto test ma nell'ambiente, e un rosso li'
#        cadrebbe addosso a chi non c'entra — tipicamente l'autore del primo
#        test che dichiara un database, in una PR che non parla di questo.
#        Quello che NON deve saltare e' il caso «schema c'e', ma manca
#        l'oggetto che il test presidia»: quello e' un difetto vero e va
#        verificato dal chiamante, dopo questa chiamata (vedi
#        `test_error_codes_db_policy_guardrail`).
def richiedi_db_provvisto(sonda: str = SONDA_SCHEMA_LIQUIBASE) -> None:
    if os.environ.get(FLAG_DB_E2E) != "1":
        raise unittest.SkipTest(
            f"test su DB reale disattivo: esporta {FLAG_DB_E2E}=1 "
            "(in CI e' acceso su ogni PR)"
        )
    from django.db import connection

    try:
        connection.ensure_connection()
    except Exception as exc:  # noqa: BLE001 — qualunque errore = DB non usabile
        raise unittest.SkipTest(f"DB non raggiungibile: {exc}") from exc

    # ⚠️ Raggiungibile != provvisto: un database c'e', ma potrebbe essere quello
    # usa-e-getta, che ha solo le migration Django.
    with connection.cursor() as cur:
        cur.execute("SELECT to_regprocedure(%s) IS NOT NULL", [sonda])
        row = cur.fetchone()
    assert row is not None
    if not row[0]:
        raise unittest.SkipTest(
            f"schema Liquibase assente nel database dei test ({sonda} non "
            "trovata): il runner ne ha creato uno usa-e-getta perche' qualche "
            "test dichiara un database. Vedi brief-be-e2e-db-error-fields-skip-schema.md"
        )


# ══════════════════════════════════════════════════════════════════════
#  I VOCABOLARI SPECCHIATI — Python contro il CHECK che li possiede
# ══════════════════════════════════════════════════════════════════════
#
# ⭐ PERCHE' STA QUI E NON IN UN TEST. Il backend tiene piu' di una copia
#    dichiarata di un vocabolario che vive in un `CHECK` del database: i canali e
#    le classi di `dbops.processi` (per rifiutare un filtro senza senso con un
#    400 parlante) e gli ambiti di `config.email_outbox` (per non far nascere una
#    bozza che la policy di lettura non sa classificare). Sono mirror LEGITTIMI —
#    servono a parlare all'operatore, non a decidere la regola — ma un mirror che
#    nessuno confronta con l'originale e' solo una copia che invecchia.
#
# ⚠️ E' GIA' SUCCESSO, due volte in un giorno (2026-09-05): `CODA_AUTOMATICA` e'
#    entrato nel CHECK dei canali e `_CANALI` ne aveva tre — un filtro legittimo
#    avrebbe preso un 400; e `ambito` usava `SISTEMA` come default, cioe' un
#    valore di ripiego davanti a una policy di sicurezza.
#
# ⚠️ LA SECONDA COPIA SAREBBE GIA' DIVERGENTE, ed e' la ragione dell'estrazione
#    (regola del 2, ok di Tid): i due CHECK scrivono i letterali con cast
#    DIVERSI — `'PGAGENT'::text` su una colonna `text`, `'SISTEMA'::character
#    varying` su una `varchar`. Due regex scritte a mesi di distanza avrebbero
#    coperto un caso ciascuna, e la seconda sarebbe stata verde per sottrazione.

# Il blocco `ARRAY[...]` di un CHECK di appartenenza, e i letterali dentro.
# ⛔ Si pretende la forma `= ANY (ARRAY[...])`: puntare questo strumento a un
#    CHECK di ALTRA natura (per dire `chk_email_outbox_ambito_emittente`, che e'
#    un `OR`) tornerebbe un insieme plausibile e SBAGLIATO. Meglio fermarsi.
_CHECK_ARRAY_RE = re.compile(r"ARRAY\[(.*?)\]", re.S)
_CHECK_LITERAL_RE = re.compile(r"'([^']*)'::")


# Scopo: i valori ammessi da un CHECK di appartenenza, letti dal CATALOGO del
#        database. E' la sola fonte: l'elenco non si riscrive nel test, o il
#        test proverebbe se stesso e un valore nuovo che nessuno dei due lati
#        conosce passerebbe verde.
#
# Param: `tabella` qualificata (`dbops.processi`), `conname` il nome del vincolo.
# ⚠️ Solleva invece di tornare un insieme vuoto: un vocabolario vuoto renderebbe
#    verde qualunque confronto.
def valori_check(tabella: str, conname: str) -> set[str]:
    from django.db import connection

    with connection.cursor() as cur:
        cur.execute(
            "SELECT pg_get_constraintdef(oid) FROM pg_constraint "
            "WHERE conrelid = %s::regclass AND conname = %s",
            [tabella, conname],
        )
        riga = cur.fetchone()
    assert riga is not None, f"CHECK {conname} assente su {tabella}"
    definizione = riga[0]
    blocco = _CHECK_ARRAY_RE.search(definizione)
    assert blocco is not None, (
        f"{conname} non e' un CHECK di appartenenza (nessun ARRAY[...]): "
        f"{definizione}"
    )
    valori = set(_CHECK_LITERAL_RE.findall(blocco.group(1)))
    assert valori, f"CHECK {conname} senza letterali interpretabili: {definizione}"
    return valori
