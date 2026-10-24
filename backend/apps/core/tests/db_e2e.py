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
#        l'oggetto che il test presidia»: quello e' un difetto vero.
#
#        ⛔ `sonda` = l'oggetto che il test presidia, e se manca FALLISCE.
#        Lo schema si riconosce SEMPRE dalla sonda di default; la sonda del
#        chiamante si guarda solo dopo, su uno schema presente, e la sua
#        assenza e' un AssertionError. Fino al 2026-10-25 le due cose erano
#        una sola: la sonda del chiamante decideva anche lo skip, quindi ogni
#        cambio di firma di un builder spegneva in silenzio il test che lo
#        usava (tre test, uno da un brief prima: brief-modello-documento-vendita
#        §4-octies, BE-1). Un presidio che si spegne da solo e' «verde per
#        sottrazione».
def richiedi_db_provvisto(sonda: str = SONDA_SCHEMA_LIQUIBASE) -> None:
    if os.environ.get(FLAG_DB_E2E) != "1":
        raise unittest.SkipTest(
            f"test su DB reale disattivo: esporta {FLAG_DB_E2E}=1 "
            "(in CI e' acceso su ogni PR)"
        )
    from django.db import connection

    try:
        connection.ensure_connection()
    except Exception as exc:  # qualunque errore = DB non usabile
        raise unittest.SkipTest(f"DB non raggiungibile: {exc}") from exc

    # ⚠️ Raggiungibile != provvisto: un database c'e', ma potrebbe essere quello
    # usa-e-getta, che ha solo le migration Django.
    with connection.cursor() as cur:
        cur.execute(
            "SELECT to_regprocedure(%s) IS NOT NULL, to_regprocedure(%s) IS NOT NULL",
            [SONDA_SCHEMA_LIQUIBASE, sonda],
        )
        row = cur.fetchone()
    assert row is not None
    schema_presente, sonda_presente = row
    if not schema_presente:
        raise unittest.SkipTest(
            f"schema Liquibase assente nel database dei test ({SONDA_SCHEMA_LIQUIBASE} "
            "non trovata): il runner ne ha creato uno usa-e-getta perche' qualche "
            "test dichiara un database. Vedi brief-be-e2e-db-error-fields-skip-schema.md"
        )
    if not sonda_presente:
        raise AssertionError(
            f"schema Liquibase presente, ma {sonda} non esiste: la funzione che "
            "questo test presidia manca o ha cambiato firma. Si allinea la sonda "
            "alla firma vera (doc auto-generata, o `to_regprocedure` sul DB), "
            "e con lei le chiamate del test."
        )


# Scopo: prerequisito dei test che provano che la RLS NASCONDE qualcosa (il
#        404 no-leak dell'altro emittente, la lista vuota): il ruolo con cui il
#        test e' connesso deve essere SOGGETTO alla RLS su `tabella`. Fallisce
#        parlando — non salta — quando non lo e'.
#
# ⛔ PERCHE' ESISTE. L'owner di una tabella e un ruolo `BYPASSRLS` (o superuser)
#    SALTANO la RLS finche' non c'e' `FORCE ROW LEVEL SECURITY`, che il repo
#    rifiuta apposta (20260829-27). Con quel ruolo un test no-leak non prova
#    niente e va rosso con «atteso un rifiuto, e' passato» — che non dice
#    PERCHE'. Successo il 2026-09-19: in CI lo step «Django tests» ereditava
#    `DB_USER: zeroerp` (l'owner, l'utente di Liquibase e di `manage.py
#    migrate`), mentre in sviluppo `.env.systemd` connette `zeroerp_app`. Il
#    test era verde da una parte e rosso dall'altra, e il messaggio del rosso
#    accusava la RLS invece del ruolo.
#
# ⚠️ FALLISCE, non salta, ed e' una scelta diversa da `richiedi_db_provvisto`:
#    li' la condizione mancante e' d'ambiente e il test non ha senso; qui il
#    database c'e' ed e' provvisto, e' la CONFIGURAZIONE del passo di test a
#    essere sbagliata — uno skip la nasconderebbe e il no-leak resterebbe
#    non provato con la suite verde (verde per sottrazione).
#
# ⚠️ `pg_has_role(..., 'USAGE')` e non `relowner = current_user`: PostgreSQL
#    riconosce come owner anche chi EREDITA il ruolo owner, e salta la RLS per
#    lui allo stesso modo.
def richiedi_ruolo_soggetto_a_rls(tabella: str) -> None:
    from django.db import connection

    with connection.cursor() as cur:
        cur.execute(
            """
            SELECT current_user,
                   r.rolsuper,
                   r.rolbypassrls,
                   pg_has_role(current_user, c.relowner, 'USAGE') AS e_owner,
                   c.relrowsecurity
              FROM pg_class c
              JOIN pg_roles r ON r.rolname = current_user
             WHERE c.oid = %s::regclass
            """,
            [tabella],
        )
        riga = cur.fetchone()
    assert riga is not None, f"tabella {tabella} assente"
    ruolo, superuser, bypassrls, e_owner, rls_attiva = riga
    assert rls_attiva, f"{tabella} non ha la RLS attiva: questo test la presuppone"
    motivi = [m for m, v in (("superuser", superuser), ("BYPASSRLS", bypassrls), (f"owner di {tabella}", e_owner)) if v]
    if motivi:
        raise AssertionError(
            f"il ruolo di connessione `{ruolo}` e' {', '.join(motivi)}: SALTA la "
            f"RLS su {tabella} e questo test non puo' provare che qualcosa resti "
            "nascosto. I test sul DB vero girano come l'applicazione "
            "(`zeroerp_app`, NOBYPASSRLS e non owner): DB_USER nel passo di test "
            "— vedi ci-validate.yaml «Django tests» e .env.systemd."
        )


# Scopo: apre il CONTESTO OPERATORE su un cursore, cioe' le due GUC senza le
#        quali ogni tabella sotto RLS risponde ZERO RIGHE. Torna l'id
#        dell'utente su cui il contesto e' stato aperto.
#
# ⭐ ESTRATTO IL 2026-09-09 (regola del 2, ok di Tid): le stesse cinque righe
#    stavano in tre file e2e — `test_lotto_gruppi_ordine`,
#    `test_pull_tutte_fallite_scrittura_reale` e
#    `test_riepilogo_esclude_trattenuti`. Non e' comodita': e' il pezzo la cui
#    assenza NON da' errore, e per questo va scritto una volta sola.
#
# ⛔ PERCHE' LO ZERO E' IL PERICOLO, e non il rosso. Senza contesto le viste di
#    dominio non falliscono: rispondono un insieme VUOTO. Un test che cerca
#    materiale trova zero righe, chiama `skipTest` e si dichiara «ok» —
#    verde per sottrazione, che e' il difetto che questi presidi esistono per
#    non avere.
#
# 🔴 IL GUARD SULLA TRANSAZIONE, ed e' la ragione per cui questa funzione vale
#    piu' delle tre copie che sostituisce. `SET LOCAL` FUORI da un blocco
#    transazionale PostgreSQL lo IGNORA — con un semplice avviso, non un errore.
#    Il contesto non si apre, RLS taglia tutto, e si legge zero credendo di aver
#    misurato. Successo il 2026-09-09 misurando a mano: «zero lotti in totale»
#    su un database che ne aveva 85. Nessuna delle tre copie aveva questo
#    controllo, ed e' esattamente cio' che un building block deve aggiungere:
#    non solo togliere la ripetizione, ma chiudere il modo di sbagliare che la
#    ripetizione lasciava aperto a tutti.
#
# ⚠️ Solleva `SkipTest` quando non c'e' un utente su cui aprirlo — un database
#    senza operatori e' una condizione d'AMBIENTE, non un difetto del codice
#    sotto test. Il guard sulla transazione invece FALLISCE: quello e' un errore
#    di chi scrive il test, e uno skip lo nasconderebbe.
def apri_contesto_operatore(cur) -> int:
    from django.db import connection

    if not connection.in_atomic_block:
        raise AssertionError(
            "apri_contesto_operatore chiamata FUORI da una transazione: "
            "`SET LOCAL` sarebbe ignorato da PostgreSQL, RLS risponderebbe "
            "zero righe e il test misurerebbe il vuoto credendolo un dato. "
            "Avvolgi la chiamata in `with transaction.atomic():`."
        )
    cur.execute("SET LOCAL app.ruolo_applicativo = 'OPERATORE'")
    cur.execute("SELECT id FROM auth_user WHERE is_superuser ORDER BY id LIMIT 1")
    riga = cur.fetchone()
    if riga is None:
        raise unittest.SkipTest("nessun utente su cui aprire il contesto operatore")
    cur.execute("SET LOCAL app.current_user_id = %s", [str(riga[0])])
    return int(riga[0])


# Scopo: apre la transazione di un test sul DB vero e ne REGISTRA l'annullo,
#        che gira sempre: a test finito, fallito, saltato — e anche quando a
#        interrompersi e' il `setUp` stesso. Da chiamare come prima istruzione
#        del `setUp`, prima di qualunque cosa possa sollevare.
#
# ⭐ ESTRATTO IL 2026-10-01 (regola del 2, ok di Tid): la coppia «`atomic` in
#    `setUp`, `set_rollback` + `__exit__` in `tearDown`» stava in sei classi di
#    cinque file — `test_login_credenziale_db`, `test_token_veste_db`,
#    `test_obblighi_e_secondo_fattore_db`, `test_pannello_verbo_db` (due) e
#    `amm_software/.../test_override_oggetti_catalogo_db`.
#
# 🔴 PERCHE' `addCleanup` E NON `tearDown`, ed e' il difetto che le sei copie
#    avevano tutte. Se il `setUp` si interrompe, `unittest` NON chiama
#    `tearDown`: chiama solo i cleanup gia' registrati. Con l'annullo in
#    `tearDown`, uno `SkipTest` sollevato dopo l'`atomic` — per esempio da
#    `apri_contesto_operatore` su un database senza utenti, cioe' quello che la
#    CI ricostruisce da zero — lasciava la transazione APERTA sulla connessione
#    condivisa. Da li' in poi ogni test cadeva su «c'e' gia' una transazione
#    aperta» o «current transaction is aborted»: 274 rossi il 2026-10-01, quasi
#    tutti in test che col DB non c'entravano, e nessuno che indicasse la causa.
def apri_transazione_annullata(test: unittest.TestCase) -> None:
    from django.db import transaction

    blocco = transaction.atomic()
    blocco.__enter__()

    def _annulla() -> None:
        transaction.set_rollback(True)
        blocco.__exit__(None, None, None)

    test.addCleanup(_annulla)


# Scopo: l'eccezione con cui un test esce da un blocco `transaction.atomic()`
#        ANNULLANDOLO, quando la transazione vive dentro il singolo test e non
#        nel `setUp` (per quello c'e' `apri_transazione_annullata`):
#            try:
#                with transaction.atomic(), connection.cursor() as cur:
#                    ...
#                    raise Annulla
#            except Annulla:
#                pass
# ⭐ ESTRATTA IL 2026-10-08 (regola del 2, ok di Tid): stava ricopiata, identica,
#    in 22 file di test di 8 app, e tre file la importavano come nome privato
#    da `anagrafiche/tests/db/test_ricerca_liste_db`.
# ⚠️ E' una classe propria e non un `Exception` generico: un errore VERO
#    sollevato nel blocco non deve essere scambiato per l'annullo voluto.
class Annulla(Exception):
    """Esce dal blocco atomico annullandolo."""


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


# ══════════════════════════════════════════════════════════════════════
#  LA RICERCA LIBERA — ogni colonna accesa trova la sua riga
# ══════════════════════════════════════════════════════════════════════
#
# ⭐ Regola del 2 (ok di Tid, 2026-09-23): nato nel test delle anagrafiche di
#    magazzino, alla seconda lista che voleva la stessa prova. E' la prova di
#    brief-be-ricerca-full-liste-residue §5.4 p.3, resa permanente: i test di
#    servizio mockano il repository e non vedono la SQL, `EXPLAIN` dice che la
#    SQL parte ma non che TROVA.
#
# ⚠️ Le colonne si leggono dal CATALOGO per l'operatore corrente
#    (`ui.fn_lista_colonne_ricerca_full`), non dal test: una colonna accesa
#    domani senza un valore qui fa rosso, invece di restare non provata.

# Scopo: per ogni colonna che il catalogo accende nella lista, `cerca(valore)`
#        deve restituire la riga `riga_id`; un termine che non c'e' da nessuna
#        parte non restituisce niente.
# Param: `valori` = `campo_sorgente -> termine` che sta in quella colonna della
#        riga; `cerca(termine)` torna le righe della lista (dict); `chiave` e' il
#        campo della riga che porta l'id.
# ⚠️ Va chiamata DENTRO la transazione del contesto: senza, il catalogo si legge
#    senza operatore e i permessi di colonna non si applicano.
def verifica_ricerca_colonna_per_colonna(
    test: unittest.TestCase,
    cur,
    lista: str,
    riga_id: object,
    valori: dict[str, str],
    cerca,
    *,
    chiave: str = "id",
) -> None:
    cur.execute("SELECT campo_sorgente FROM ui.fn_lista_colonne_ricerca_full(%s)", [lista])
    accese = {r[0] for r in cur.fetchall()}
    test.assertTrue(accese, f"{lista}: nessuna colonna accesa per l'operatore")
    test.assertFalse(
        accese - valori.keys(),
        f"{lista}: colonne accese senza un valore da cercare: {sorted(accese - valori.keys())}",
    )
    for col in sorted(accese):
        with test.subTest(lista=lista, colonna=col):
            ids = [r[chiave] for r in cerca(valori[col])]
            test.assertIn(riga_id, ids)
    with test.subTest(lista=lista, colonna=None):
        test.assertEqual(list(cerca("zzznessunoqui")), [])
