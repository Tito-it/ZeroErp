# ------------------------------------------------------------
# SPDX-License-Identifier: AGPL-3.0-or-later
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
from dataclasses import dataclass

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


# Scopo: il controllo comune dei BB di contesto: fuori da un blocco atomico
#        FALLISCONO col motivo, prima di scrivere o leggere qualcosa.
#        `SET LOCAL` fuori da una transazione PostgreSQL lo ignora con un
#        avviso, e la RLS risponderebbe zero righe; un builder chiamato fuori
#        lascerebbe nel DB l'utente costruito. Privato: lo chiamano i quattro BB
#        di contesto qui sotto (estratto il 2026-11-27 con `apri_contesto_su`:
#        erano quattro copie del controllo, con quattro messaggi).
def _richiedi_transazione(chi: str) -> None:
    from django.db import connection

    if not connection.in_atomic_block:
        raise AssertionError(
            f"{chi} chiamata FUORI da una transazione: `SET LOCAL` sarebbe "
            "ignorato da PostgreSQL, la RLS risponderebbe zero righe, e cio' che "
            "il test costruisce resterebbe nel DB. Avvolgi la chiamata in "
            "`with transaction.atomic():` o apri la transazione del test con "
            "`apri_transazione_annullata`."
        )


# Scopo: apre il contesto di un utente GIA' SCELTO su un cursore — le due GUC
#        che le policy RLS e i guard dei verbi leggono — per la sola
#        transazione: `apri_contesto_su(cur, auth_user_id) -> auth_user_id`.
#        Per i test che costruiscono il loro operatore (un builder `dbops`,
#        un secondo mondo) o che cambiano operatore a meta' test.
#
# ⭐ ESTRATTO IL 2026-11-27 (regola del 2, ok di Tid il 2026-11-26, brief-be-
#    accessi-credenziale-e-vesti §4): le due righe `SET LOCAL` erano ricopiate
#    in `apri_contesto_operatore`, `apri_super_admin_costruito`,
#    `apri_operatore_con_aree` e in `_agisci` di
#    `test_soggetti_id_fiscale_immutabile_db`, e una trentina di file chiamava
#    al loro posto `script.fn_pgtap_set_contesto_operatore(<id>)`.
#
# 🔴 PERCHE' NON `fn_pgtap_set_contesto_operatore` dai test Django. Quella
#    funzione scrive le GUC per la SESSIONE (`set_config(…, false)`), che nei
#    pgTAP e' giusto: ogni file ha la sua. Dentro un `atomic` annullato una GUC
#    di sessione si annulla anch'essa (provato il 2026-11-27); il rischio vero
#    e' la chiamata FUORI da una transazione: in autocommit il contesto resta
#    sulla connessione, che Django condivide fra i test, e il test dopo gira
#    con l'utente del test prima. Qui `SET LOCAL` lega il contesto alla
#    transazione, e il controllo qui sotto rifiuta di aprirlo fuori — dove
#    PostgreSQL ignorerebbe `SET LOCAL` con un avviso, e la RLS
#    risponderebbe zero righe. Il presidio sui sorgenti sta in
#    `apps/core/tests/test_contesto_test_db_transazionale.py`.
def apri_contesto_su(cur, auth_user_id: int) -> int:
    _richiedi_transazione("apri_contesto_su")
    cur.execute("SET LOCAL app.ruolo_applicativo = 'OPERATORE'")
    cur.execute("SET LOCAL app.current_user_id = %s", [str(auth_user_id)])
    return auth_user_id


# Scopo: il passo di CONTESTO dentro una fixture di `esegui_fixture`: apre il
#        contesto (BB `apri_contesto_su`) sull'`auth_user_id` della tabella
#        temporanea `tabella`, costruita dai passi prima — di solito il mondo
#        di un builder `dbops` (`CREATE TEMP TABLE _mondo AS …`).
#        `ContestoSu("_mondo")` sta nella tupla dove nei pgTAP sta
#        `SELECT script.fn_pgtap_set_contesto_operatore((SELECT auth_user_id
#        FROM _mondo))`: i passi dopo girano gia' col contesto.
@dataclass(frozen=True)
class ContestoSu:
    tabella: str = "_mondo"


# Il nome della tabella del mondo finisce nel testo della query: si ammette
# solo un identificatore semplice, non una espressione.
_IDENTIFICATORE_RE = re.compile(r"[A-Za-z_][A-Za-z0-9_]*")


# Scopo: esegue in fila i PASSI di una fixture sul DB vero:
#        `esegui_fixture(cur, passi, params=None)`. Un passo e' una stringa
#        SQL (eseguita con `params`, se dati: le fixture col suffisso
#        `%(sfx)s`) oppure un `ContestoSu`, che apre il contesto sull'utente
#        del mondo costruito fin li'.
#
# ⭐ ESTRATTO IL 2026-11-27 (regola del 2, ok di Tid lo stesso giorno, D-C1 di
#    brief-be-accessi-credenziale-e-vesti §4.1): il ciclo `for passo in
#    _FIXTURE: cur.execute(passo)` stava in 38 punti, e diciannove tuple
#    aprivano il contesto con `script.fn_pgtap_set_contesto_operatore`, che
#    scrive le GUC per la SESSIONE. Il passo di contesto e' proprio quello che
#    non deve dipendere da chi scrive il test: qui passa sempre da
#    `apri_contesto_su` (`SET LOCAL`, e il rifiuto fuori da una transazione).
#
# ⛔ La tabella del contesto deve avere UNA riga: zero o piu' righe sono un
#    mondo costruito male, e il test fallisce col motivo invece di aprire il
#    contesto su un utente a caso.
def esegui_fixture(cur, passi, params=None) -> None:
    for passo in passi:
        if isinstance(passo, ContestoSu):
            if not _IDENTIFICATORE_RE.fullmatch(passo.tabella):
                raise AssertionError(f"ContestoSu: tabella non valida {passo.tabella!r}")
            cur.execute(f"SELECT auth_user_id FROM {passo.tabella}")
            righe = cur.fetchall()
            if len(righe) != 1:
                raise AssertionError(
                    f"ContestoSu({passo.tabella!r}): attesa una riga, trovate {len(righe)}"
                )
            apri_contesto_su(cur, int(righe[0][0]))
        elif params is None:
            cur.execute(passo)
        else:
            cur.execute(passo, params)


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
# ⛔ Niente SUPER_ADMIN da qui: il parametro `super_admin` (2026-11-07) e'
#    ritirato il 2026-11-26 (Tid). Prendeva il primo SUPER_ADMIN del DB, e su
#    un DB senza saltava: un test verde senza aver provato niente. Chi vuole
#    un SUPER_ADMIN lo costruisce con `apri_super_admin_costruito`.
# ⛔ E nemmeno per caso (D-AH, 2026-11-26): l'operatore scelto e' il primo che
#    NON e' SUPER_ADMIN. Se gli operatori attivi sono tutti SUPER_ADMIN la
#    funzione FALLISCE col motivo, non salta e non ne consegna uno.
def apri_contesto_operatore(cur) -> int:
    _richiedi_transazione("apri_contesto_operatore")
    # ⭐ Un OPERATORE con la veste attiva, cioe' cio' che il nome promette.
    #    Fino al 2026-11-24 era «il primo `is_superuser`»: un flag che il
    #    database non guarda e che dal D-J non concede niente nemmeno al
    #    backend (brief-db-porte-aperte-dalla-sola-guc §4.7).
    # ⛔ MAI UN SUPER_ADMIN PRESO DAI DATI (D-AH, Tid 2026-11-26,
    #    brief-db-porte-aperte-dalla-sola-guc §14.9). Fino ad allora era «il
    #    primo operatore», e se il primo operatore di dbdev era SUPER_ADMIN un
    #    verbo col guard del SUPER_ADMIN passava: verde per i dati della
    #    macchina, non per la regola. Si prende il primo operatore che NON lo e'
    #    (l'ORDER BY mette in testa i `false`); chi vuole un SUPER_ADMIN lo
    #    costruisce con `apri_super_admin_costruito`.
    #    `fn_is_super_admin` con la GUC del ruolo vuota guarda la credenziale
    #    (`fn_is_super_admin_account`): il contesto si apre DOPO la scelta, col
    #    BB `apri_contesto_su`, che e' anche il controllo sulla transazione.
    cur.execute(
        "SELECT u.id, script.fn_is_super_admin(u.id) AS sa FROM auth_user u"
        " WHERE u.is_active"
        "   AND script.fn_has_identita_attiva(u.id, 'OPERATORE'::config.ruolo_applicativo)"
        " ORDER BY sa, u.id LIMIT 1"
    )
    riga = cur.fetchone()
    if riga is None:
        raise unittest.SkipTest("nessun utente su cui aprire il contesto operatore")
    utente, super_admin = int(riga[0]), bool(riga[1])
    # ⛔ Operatori ci sono, ma sono tutti SUPER_ADMIN: e' un caso diverso dal DB
    #    vuoto, e non si salta. Consegnarne uno rifarebbe il verde per i dati;
    #    saltare nasconderebbe che il test non ha un operatore adatto.
    if super_admin:
        raise AssertionError(
            "apri_contesto_operatore: tutti gli operatori attivi del DB sono "
            f"SUPER_ADMIN (il primo e' {utente}), e un SUPER_ADMIN preso dai dati "
            "non si consegna (D-AH): il test passerebbe per chi e' l'operatore, "
            "non per la regola. Se il test vuole un SUPER_ADMIN usi "
            "`apri_super_admin_costruito`; se vuole dei permessi, "
            "`apri_operatore_con_aree`."
        )
    return apri_contesto_su(cur, utente)


# Scopo: UN SUPER_ADMIN COSTRUITO, col contesto aperto su di lui:
#        `apri_super_admin_costruito(cur, etichetta="...") -> auth_user_id`.
#        Per i test che passano da un verbo del DB che chiede il SUPER_ADMIN
#        all'utente della sessione (`script.fn_guard_super_admin`, per esempio
#        `anagrafiche.fn_revoca_veste` su una veste operatore).
# Note: estratto il 2026-11-26 (regola del 2, ok Tid) da `test_accessi_db`,
#       `test_revoca_veste_db` e `test_token_veste_db`, che ricopiavano
#       builder + due `SET LOCAL` + controllo; ha preso il posto di
#       `apri_contesto_operatore(cur, super_admin=True)`, ritirato lo stesso
#       giorno.
#       ⭐ A differenza di quel parametro l'utente si COSTRUISCE (`dbops.fn_pgtap_crea_operatore_umano(…, true)`): niente
#       dipende dai SUPER_ADMIN presenti, e non c'e' lo skip che su un database
#       senza amministratori rendeva il test verde senza provare niente.
#       ⚠️ Il contesto si apre per ULTIMO: chi costruisce altri casi lo fa
#       PRIMA di chiamarla, come nei pgTAP (i builder scrivono una saga).
#       Va chiamata dentro una transazione annullata.
def apri_super_admin_costruito(cur, *, etichetta: str) -> int:
    _richiedi_transazione("apri_super_admin_costruito")
    cur.execute("SELECT auth_user_id FROM dbops.fn_pgtap_crea_operatore_umano(%s, true)", [etichetta])
    utente = int(cur.fetchone()[0])
    # ⭐ Il contesto per la sola transazione, dal BB `apri_contesto_su` (il
    #    perche' sta li').
    # ⚠️ Corretto il 2026-11-27: qui c'era scritto che le GUC di SESSIONE
    #    (`set_config(…, false)`, come in `script.fn_pgtap_set_contesto_operatore`)
    #    «sopravvivono al rollback». Provato sul DB di sviluppo: scritte dentro
    #    un `atomic` o un savepoint annullati tornano vuote. Il rosso del
    #    2026-11-26 in `test_operatore_altre_vesti_db` (un test che eredita l'id
    #    di un SUPER_ADMIN annullato) ha un'altra causa, non accertata:
    #    probabilmente un `set_config` fuori transazione.
    apri_contesto_su(cur, utente)
    # ⛔ Un builder che non lega il profilo non deve passare in silenzio: il
    #    test proverebbe E_PERMESSO_NEGATO invece della regola.
    cur.execute("SELECT script.fn_is_super_admin(%s)", [utente])
    if not cur.fetchone()[0]:
        raise AssertionError(f"l'utente costruito {utente} non e' SUPER_ADMIN per il DB")
    return utente


# Scopo: UN OPERATORE COSTRUITO, col contesto aperto su di lui, senza
#        concessioni: `apri_operatore_costruito(cur, *, sigla=None) ->
#        auth_user_id`. `dbops.fn_pgtap_crea_emittente_operatore(sigla)`
#        (azienda + operatore NON SUPER_ADMIN, legato al suo emittente) e
#        `apri_contesto_su`. `sigla` serve a un secondo mondo nella stessa
#        transazione (l'altro emittente di un test no-leak).
# ⭐ ESTRATTO IL 2026-11-27 (regola del 2, ok di Tid lo stesso giorno): la
#    coppia «builder + contesto» stava in `apri_operatore_con_aree`, in
#    `test_pannello_verbo_db`, nei tre test che chiamavano
#    `fn_pgtap_set_contesto_operatore()` senza argomento e nello smoke
#    `smoke-magazzino-inventario-primo-carico.py`.
# ⚠️ Non e' `apri_contesto_operatore`: quello SCEGLIE un operatore fra quelli
#    della macchina, questo lo COSTRUISCE, e non dipende dai dati presenti.
#    Fallisce fuori da un blocco atomico (prima di costruire: l'operatore
#    resterebbe nel DB).
def apri_operatore_costruito(cur, *, sigla: str | None = None) -> int:
    _richiedi_transazione("apri_operatore_costruito")
    cur.execute("SELECT auth_user_id FROM dbops.fn_pgtap_crea_emittente_operatore(%s::varchar)", [sigla])
    return apri_contesto_su(cur, int(cur.fetchone()[0]))


# Scopo: UN OPERATORE COSTRUITO, col contesto aperto e livello TUTTO sulle
#        aree indicate (per `schema_db`): `apri_operatore_con_aree(cur, aree=
#        ("catalogo", "vendite")) -> auth_user_id`. Per i test che passano dai
#        verbi del DB che chiedono un livello (`script.fn_guard_livello`).
# Note: estratto il 2026-11-11 (regola del 2, ok Tid) da
#       `catalogo/.../test_chiusura_legame_prezzi_db` e
#       `vendite/.../test_listino_uom_compatibile_db`.
#       ⭐ A differenza di `apri_contesto_operatore` l'utente si COSTRUISCE
#       (`dbops.fn_pgtap_crea_emittente_operatore`): niente dipende dagli
#       utenti presenti, e non c'e' nessuno skip possibile.
#       ⭐ Il livello lo concede il builder del DB,
#       `dbops.fn_pgtap_concedi_livello_area` (2026-11-27, giro 10-quater di
#       brief-db-porte-aperte-dalla-sola-guc §15.7): le eccezioni utente sono
#       in sola lettura per l'app, e si scrivono dal verbo del SUPER_ADMIN.
#       Fino ad allora qui c'era un `INSERT … ON CONFLICT` diretto, la copia
#       del builder (regola del 2), e il parametro `motivo`: il builder scrive
#       il suo («Fixture pgTAP»). Un'area che non esiste la rifiuta il builder.
#       ⚠️ Il builder entra come SUPER_ADMIN di fixture e rimette il contesto
#       con `set_config` di sessione: dentro una transazione annullata si
#       annulla anche quello.
#       Va chiamata dentro una transazione annullata.
def apri_operatore_con_aree(cur, *, aree: tuple[str, ...]) -> int:
    if not aree:
        raise AssertionError("apri_operatore_con_aree senza aree: il livello non si alza su niente")
    utente = apri_operatore_costruito(cur)
    for area in aree:
        cur.execute(
            "SELECT dbops.fn_pgtap_concedi_livello_area(%s, %s, 'TUTTO'::config.livello_accesso)",
            [utente, area],
        )
    return utente


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
