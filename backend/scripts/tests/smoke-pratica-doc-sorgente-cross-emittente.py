# ------------------------------------------------------------
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Smoke — l'ancora di `script.vw_pratica_doc_sorgente` su una pratica che
#        punta a un documento di UN ALTRO emittente. E' la risposta alla voce 1
#        del §7 di `docs/it/dev/work-done/brief-db-viste-security-invoker-criterio.md`
#        — era l'ultima voce aperta dopo il changeSet `20260907-04`, ed e' quella
#        che ha chiuso quel brief il 2026-09-07.
# Eseguito via `./manage-env.sh shell < scripts/tests/smoke-pratica-doc-sorgente-cross-emittente.py`
#
# ⭐ LA DOMANDA NON E' «SI VEDE ANCORA QUALCOSA», ed e' il punto del brief.
# Quella vista non nasconde soltanto: **sceglie**. La regola d'ancora ordina su
# `risolto` e `terminale`, cioe' su dati che dal 2026-09-07 sono filtrati dal
# perimetro di chi legge. ⇒ Su una pratica con piu' sorgenti puo' vincerne
# un'altra. E' corretto — non si sceglie un'ancora guardando dati che non si
# possono vedere — ma e' un CAMBIO DI COMPORTAMENTO, non un nascondimento.
#
# ⛔ PERCHE' UNO SMOKE, E PERCHE' FABBRICA IL CASO. Il brief dice che «nessuna
# suite fabbrica oggi quel caso» e propone di guardarlo a video. A video non si
# puo': i campi `doc_*` a livello PRATICA oggi non li rende nessuna schermata
# (l'unico consumatore di `doc_*` e' `PraticaPercorso.vue`, che e' il ramo
# PER-FLUSSO, e la lista pratiche non ha nessuna colonna `doc_*` configurata in
# `ui.lista_colonna`). ⇒ La risposta si legge dalla vista e dal repository che
# la usa. E il caso va COSTRUITO: il modello ammette la divergenza —
# `pratiche_sorgenti` non ha nessun vincolo ne' guard che confronti l'emittente
# del documento con quello della pratica, e `sorgente_uid` e' una chiave
# polimorfa senza FK — ma su dati coerenti non se ne vede traccia.
#
# ⚠️ IL PERIMETRO SI IMPONE CON `app.current_emittente_id`, non con la whitelist
# di un operatore scelto a caso. `script.fn_check_user_emittente_scope` valuta
# quel GUC alla regola 2, PRIMA del bypass super admin: «restringe CHIUNQUE».
# ⇒ TRE perimetri (largo · di casa · estraneo) sullo STESSO utente e sugli
# STESSI dati, cioe' la sola variabile che interessa. Appoggiarsi a
# `config.user_emittenti_fiscali` avrebbe legato l'esito a com'e' configurata
# questa macchina.
#
# ⛔ E IL TEST 2 E' QUELLO CHE PROTEGGE TUTTI GLI ALTRI: se la connessione non
# applicasse la RLS (ruolo owner, `BYPASSRLS`), i tre perimetri direbbero la
# stessa cosa e questo file passerebbe verde **smettendo di verificare**. Li' si
# esce `SENZA_MATERIA`, non si stampa OK.
#
# Rollback-safe: tutto dentro `transaction.atomic()` + `set_rollback(True)`.
# Scrive DUE preventivi (`vendite.preventivi`, uno per emittente, coi loro
# clienti) e QUATTRO righe su `pratiche.pratiche_sorgenti` — due per pratica —
# e annulla tutto.
#
# Indice test (1..7):
#   1. Fixture: super admin, due pratiche dello stesso emittente, i due documenti COSTRUITI
#   2. ⛔ Il perimetro MORDE: l'estraneo sparisce e quello di casa resta
#   3. Costruzione: due pratiche speculari, il ROOT invertito fra le due
#   4. Perimetro LARGO: su entrambe vince il ROOT (nessuno scope in mezzo)
#   5. Perimetro DI CASA: sulla pratica A vince il COLLEGATO di casa
#   6. ⭐ LO SPECCHIO: dal perimetro estraneo la vista NON risponde (dal 2026-09-10 il link e' nel perimetro)
#   7. Il consumatore vero: `get_pratica()` dice la stessa cosa della vista
#
# ⭐ LE DUE PRATICHE SONO SPECULARI, E NON E' SIMMETRIA DECORATIVA. Con una sola
# si dimostra troppo poco: «dal perimetro di casa ha vinto il documento di casa»
# lo direbbe anche una vista che sceglie sempre il COLLEGATO, o che preferisce
# sempre l'emittente di chi legge per un'altra ragione. La pratica B ha il ROOT
# sul documento DI CASA e il COLLEGATO su quello estraneo: letta dal perimetro
# ESTRANEO doveva vincere il COLLEGATO — cioe' l'esatto contrario, sugli stessi
# due documenti. ⇒ Insieme, i test 5 e 6 escludevano ogni regola che non guardi
# chi legge.
# ⛔ DAL 2026-09-10 LO SPECCHIO NON E' PIU' OSSERVABILE, ed e' un fatto del
# modello, non dello smoke: il changeSet `20260910-02` (gemello DB §D2, «il
# dominio documento e' protetto fino ai satelliti») ha messo la RLS su
# `pratiche.pratiche_sorgenti` (`rls_pratiche_sorgenti_ef_whitelist`, via
# `fn_scope_ef_whitelist_via_pratica`). Chi legge dall'emittente estraneo non
# vede i LINK della pratica, quindi la vista non ha piu' niente su cui
# scegliere: risponde NULL. Il test 6 pretende ora quel NULL — la proprieta'
# piu' forte: il perimetro si chiude sul link, non solo nel consumatore.
# ⚠️ La pratica B resta nel fixture, e serve: il test 4 la legge dal perimetro
# largo (vince il ROOT di casa) e il 6 dal perimetro estraneo (niente).
#
# ⭐ PROVATO ANCHE AL CONTRARIO (2026-09-07), perche' un verde non dice niente
# finche' non si sa che cosa lo farebbe diventare rosso. La regressione da
# simulare e' `security_invoker` spento sulla vista: li' girerebbe come il
# proprietario (`titodb`), che dalla RLS e' esente — cioe' ogni perimetro
# ristretto si comporterebbe come quello largo, e nel test 4 e' scritto che
# cosa fa quello largo: vince il ROOT, su entrambe le pratiche.
# ⇒ Riprodotto sostituendo con `None` il `seleziona_emittente(...)` dei test 5
# e 6: diventano rossi «vince il COLLEGATO di casa» e «vince il COLLEGATO
# estraneo», nominandoli.
# ⭐ Dopo il 2026-09-10 il test 6 resta un discriminante, nel verso opposto:
# con `security_invoker` spento la vista vedrebbe i link di TUTTI gli
# emittenti e dal perimetro estraneo RISPONDEREBBE — e «la vista NON risponde»
# diventa rosso.
#
# ⚠️ E il test 2 sarebbe rimasto VERDE: la RLS sulla tabella base non c'entra
# con la reloption della vista. I discriminanti sono il 5 e il 6, non il 2.
# ⛔ La prova NON si e' fatta con un `ALTER VIEW … RESET`, e non per prudenza:
# la connessione e' `zeroerp_app`, la vista e' di `titodb`, quindi non si puo'
# — ed e' giusto cosi'.
# ------------------------------------------------------------
from django.db import connection, transaction

from apps.pratiche.db.pratiche_repository import PraticheRepository

FAIL: list[str] = []


# Scopo: registra l'esito di un caso, con la frase che si legge a colpo d'occhio.
def check(nome: str, ok: bool, dettaglio: str = "") -> None:
    print(f"  [{'OK ' if ok else 'KO '}] {nome}{(' — ' + dettaglio) if dettaglio else ''}")
    if not ok:
        FAIL.append(nome)


# Scopo: un uid corto e leggibile nell'esito.
# ⚠️ La CODA, non la testa: gli uid sono UUIDv7, i primi caratteri sono il
#    timestamp, e due documenti costruiti nello stesso giro li hanno uguali.
def uid_breve(uid: str) -> str:
    return f"…{uid[-8:]}"


# Scopo: seleziona l'emittente "attivo" della sessione. Stringa vuota = nessuna
#        selezione, cioe' il perimetro pieno dell'utente.
# ⚠️ `NULLIF(current_setting(...), '')` e' esattamente come lo legge
#    `fn_check_user_emittente_scope`: il vuoto vale «non ho selezionato niente»,
#    non «emittente zero».
def seleziona_emittente(cur, emittente_id) -> None:
    cur.execute(
        "SELECT set_config('app.current_emittente_id', %s, true)",
        [str(emittente_id) if emittente_id is not None else ""],
    )


# Scopo: costruisce un preventivo VERO dell'emittente dato, col suo cliente
#        (builder `fn_pgtap_crea_cliente_ba`, terzo parametro = il
#        soggetto_ruolo dell'emittente a cui legare il BA, letto qui), e ne
#        restituisce (uid, utility_id).
# ⚠️ Il BA si crea DENTRO un emittente (`trgfn_billing_account_guard_admin_globale`:
#    con «Tutti gli emittenti» non si sa a quale associarlo): il perimetro
#    torna largo subito dopo l'INSERT del preventivo.
# ⭐ Lo stato non si scrive: il preventivo nasce nello stato iniziale, e lo
#    mette il DB (`script.trgfn_doc_stato_iniziale`, brief-modello-documento-
#    vendita P-2). Due documenti costruiti qui hanno quindi lo STESSO stato per
#    costruzione — la condizione che rende leggibile il risultato (vedi la
#    fixture).
def crea_preventivo(cur, emittente_id: int, utility_id, etichetta: str):
    cur.execute(
        "SELECT soggetto_ruolo_id FROM anagrafiche.emittenti_fiscali WHERE id = %s",
        [emittente_id],
    )
    emittente_sr = riga_obbligatoria(
        cur, f"emittente {emittente_id} senza soggetto_ruolo.",
    )[0]
    seleziona_emittente(cur, emittente_id)
    cur.execute(
        """
        SELECT billing_account_id, istanza_utility_id, utility_id
          FROM dbops.fn_pgtap_crea_cliente_ba(%s, %s, %s)
        """,
        [etichetta, utility_id, emittente_sr],
    )
    ba, istanza, utility = riga_obbligatoria(
        cur, f"il builder non ha restituito il cliente dell'emittente {emittente_id}.",
    )
    cur.execute(
        """
        INSERT INTO vendite.preventivi
               (billing_account_id, istanza_utility_id, utility_id,
                emittente_fiscale_id)
        VALUES (%s, %s, %s, %s)
        RETURNING uid::text
        """,
        [ba, istanza, utility, emittente_id],
    )
    uid = riga_obbligatoria(cur, "l'INSERT non ha restituito l'uid.")[0]
    seleziona_emittente(cur, None)
    return uid, utility


# Scopo: la riga dell'ancora per una pratica, letta dalla vista nuda.
#        `None` se la vista non ha righe (pratica senza link, o pratica invisibile).
def ancora(cur, pratica_id: int):
    cur.execute(
        """
        SELECT sorgente_uid, ruolo_link, risolto, stato_codice_interno, terminale
          FROM script.vw_pratica_doc_sorgente
         WHERE pratica_id = %s
        """,
        [pratica_id],
    )
    r = cur.fetchone()
    if not r:
        return None
    return {
        "sorgente_uid": str(r[0]),
        "ruolo_link": r[1],
        "risolto": r[2],
        "stato_codice_interno": r[3],
        "terminale": r[4],
    }


# Scopo: appende a una pratica due link dello stesso tipo sorgente, uno `ROOT` e
#        uno `COLLEGATO`. Il caso si costruisce due volte a ruoli invertiti, e
#        una seconda `INSERT` scritta a mano sarebbe la copia che diverge.
# ⚠️ Va chiamata dal perimetro LARGO: il guard unico
#    `script.trgfn_guard_sorgente('DOCUMENTO', 'BLOCCA')` (dal giro P.1 di
#    brief-db-sorgente-documento-e-riga) verifica che il documento esista e
#    gira come l'utente — da un perimetro ristretto rifiuterebbe il documento
#    che quel perimetro non vede, cioe' proprio il caso da provare.
def collega(cur, pratica_id: int, tipo_id: int, uid_root: str, uid_collegato: str) -> None:
    cur.execute(
        """
        INSERT INTO pratiche.pratiche_sorgenti
               (pratica_id, sorgente_tipo_id, sorgente_uid, ruolo_link)
        VALUES (%s, %s, %s, 'ROOT'), (%s, %s, %s, 'COLLEGATO')
        """,
        [pratica_id, tipo_id, uid_root, pratica_id, tipo_id, uid_collegato],
    )


# Scopo: la riga singola attesa da una query di fixture, con il guard che
#        AGENTS.md pretende dopo ogni `fetchone()`. `motivo` diventa la frase di
#        `SENZA_MATERIA`: una fixture che manca si dichiara, non si scopre tre
#        righe dopo con un `TypeError` su `None`.
def riga_obbligatoria(cur, motivo: str):
    r = cur.fetchone()
    if not r:
        raise SystemExit(f"SENZA_MATERIA: {motivo}")
    return r


with transaction.atomic():
    with connection.cursor() as cur:
        # ── 1. Fixture ────────────────────────────────────────────────────
        print("\n=== 1. Fixture ===")

        # L'utente: un super admin CON un'identita' OPERATORE attiva, cosi' i
        # cinque GUC di contesto sono tutti veri e non inventati.
        # ⚠️ Il super admin non serve a «vedere tutto» per comodita': serve a
        #    rendere il perimetro LARGO deterministico. Con un operatore
        #    qualunque, «largo» dipenderebbe da come e' compilata la whitelist
        #    su QUESTA macchina — cioe' l'esito del test dipenderebbe dai dati.
        cur.execute(
            """
            SELECT i.id, i.auth_user_id, i.soggetto_ruolo_id, u.username
              FROM anagrafiche.identita_digitali i
              JOIN auth_user u ON u.id = i.auth_user_id
             WHERE i.ruolo_applicativo = 'OPERATORE'
               AND i.attivo
               AND script.fn_is_super_admin(i.auth_user_id)
             LIMIT 1
            """
        )
        ident = cur.fetchone()
        if not ident:
            raise SystemExit(
                "SENZA_MATERIA: nessuna identita OPERATORE attiva su un utente "
                "super admin — senza, il perimetro LARGO non e' deterministico."
            )
        for chiave, valore in (
            ("app.current_user_id", str(ident[1])),
            ("app.current_identita_id", str(ident[0])),
            ("app.ruolo_applicativo", "OPERATORE"),
            ("app.soggetto_ruolo_id", str(ident[2])),
            ("app.jwt_user", ident[3]),
        ):
            cur.execute("SELECT set_config(%s, %s, true)", [chiave, valore])
        seleziona_emittente(cur, None)
        check("contesto operatore impostato", True, f"identita {ident[0]}, perimetro largo")

        # Il tipo sorgente. ⛔ Si nomina per `codice_interno`, mai per id.
        cur.execute(
            "SELECT id FROM config.sorgenti "
            " WHERE codice_interno = 'PREVENTIVO' AND attivo IS TRUE"
        )
        sorgente_tipo_id = riga_obbligatoria(
            cur, "config.sorgenti non ha PREVENTIVO attivo."
        )[0]

        # DUE pratiche senza link, dello stesso emittente.
        # ⚠️ Senza sorgenti, o l'ancora la deciderebbero righe che non abbiamo
        #    costruito noi. Due perche' il caso si prova a ruoli invertiti
        #    (vedi l'intestazione): una sola dimostrerebbe troppo poco.
        # ⛔ E DELLO STESSO EMITTENTE, imposto nella query e non sperato: prese
        #    «le prime due» su una macchina multi-emittente potrebbero cadere su
        #    emittenti diversi, e «di casa» vorrebbe dire due cose diverse nei
        #    test 5 e 6. Non fallirebbe: direbbe un'altra cosa, in silenzio.
        cur.execute(
            """
            WITH candidate AS (
                SELECT p.id, p.emittente_fiscale_id
                  FROM pratiche.pratiche p
                 WHERE NOT EXISTS (SELECT 1 FROM pratiche.pratiche_sorgenti ps
                                    WHERE ps.pratica_id = p.id)
            ), scelto AS (
                SELECT emittente_fiscale_id
                  FROM candidate
                 GROUP BY emittente_fiscale_id
                HAVING count(*) >= 2
                 ORDER BY emittente_fiscale_id
                 LIMIT 1
            )
            SELECT c.id, c.emittente_fiscale_id
              FROM candidate c
              JOIN scelto s USING (emittente_fiscale_id)
             ORDER BY c.id
             LIMIT 2
            """
        )
        pratiche = cur.fetchall()
        if len(pratiche) != 2:
            raise SystemExit(
                "SENZA_MATERIA: serve un emittente con almeno DUE pratiche senza "
                "sorgenti; trovate "
                f"{len(pratiche)} pratiche utilizzabili."
            )
        (pratica_a, emittente_casa), (pratica_b, _) = pratiche

        # Il documento DI CASA si costruisce come l'estraneo (sotto): fino al
        # 2026-10-24 si prendeva «il primo preventivo dell'emittente», in
        # qualunque stato, e l'estraneo ne copiava lo stato. Con la regola della
        # nascita (brief-modello-documento-vendita N-1) lo stato non si copia
        # piu': i due documenti nascono entrambi nello stato iniziale.
        uid_casa, utility_id = crea_preventivo(
            cur, emittente_casa, None, "smoke ancora casa",
        )

        # ⛔ IL DOCUMENTO ESTRANEO SI COSTRUISCE, NON SI CERCA — ed e' la parte
        #    che vale piu' del resto. Su questa macchina, il 2026-09-07, un solo
        #    emittente ha preventivi: cercarlo avrebbe dato SENZA_MATERIA, cioe'
        #    copertura ZERO travestita da «qui non capita». ⭐ Ma «oggi non
        #    capita» non e' un fatto sul modello: `pratiche_sorgenti` non ha
        #    nessun vincolo ne' guard che leghi la sorgente all'emittente della
        #    pratica, e `sorgente_uid` e' polimorfa senza FK — quindi il caso
        #    esiste, manca solo un controesempio. Un presidio che aspetta i dati
        #    giusti passa a vuoto su un database ricostruito da zero
        #    (AGENTS.md, corollario sui test).
        # ⭐ E I DUE DOCUMENTI HANNO LO STESSO STATO, che NON e' un caso: e' la
        #    condizione che rende leggibile il risultato (dal 2026-10-24 lo
        #    garantisce la nascita nello stato iniziale, prima la copia). La regola
        #    d'ancora ordina su risolto → non-terminale → ROOT → id; con lo
        #    stesso stato i criteri 1 e 2 pareggiano *dal perimetro largo*, e a
        #    decidere restano solo `risolto` (che dipende da chi legge) e
        #    `ruolo_link`. Con uno stato diverso potrebbe vincere il criterio 2,
        #    e il test misurerebbe la terminalita' invece del perimetro.
        # ⚠️ Il documento estraneo e' un preventivo VERO del suo emittente: dal
        #    2026-10-08 (brief-db-istanza-nasce-col-ba, R-2) `billing_account_id`
        #    e' NOT NULL e legato alla coppia (istanza, utility), e il guard
        #    emittente/BA lo confronta con l'emittente del documento. ⇒ Il cliente
        #    si COSTRUISCE sull'emittente estraneo (builder `fn_pgtap_crea_cliente_ba`,
        #    terzo parametro = l'emittente a cui legare il BA), sulla stessa
        #    utility del preventivo di casa (`crea_preventivo`). Fino al 2026-10-09 qui si clonava la
        #    riga di casa cambiando il solo emittente, con il BA a NULL: il vincolo
        #    nuovo lo rifiuta, ed e' giusto. L'incoerenza che il test prova resta
        #    la stessa — una pratica che punta a un documento di UN ALTRO emittente.
        cur.execute(
            """
            SELECT id FROM anagrafiche.emittenti_fiscali
             WHERE attivo AND id <> %s ORDER BY id LIMIT 1
            """,
            [emittente_casa],
        )
        emittente_estraneo = riga_obbligatoria(
            cur,
            "un solo emittente fiscale attivo — su un'installazione "
            "mono-emittente il caso non e' costruibile.",
        )[0]

        uid_estraneo, _ = crea_preventivo(
            cur, emittente_estraneo, utility_id,
            "smoke ancora cross-emittente",
        )
        check(
            "materia costruita", True,
            f"pratiche {pratica_a} e {pratica_b} (emittente {emittente_casa}), "
            f"documenti creati: di casa e estraneo (emittente {emittente_estraneo})",
        )

        # ── 2. Il perimetro morde ─────────────────────────────────────────
        print("\n=== 2. ⛔ Il perimetro MORDE (senza, tutto il resto e' verde per sottrazione) ===")
        # ⛔ L'estraneo che NON sparisce non e' un rosso, e' assenza di materia:
        #    vorrebbe dire che la connessione non applica la RLS (ruolo owner o
        #    BYPASSRLS), quindi ogni perimetro direbbe la stessa cosa e i test
        #    5 e 6 passerebbero SMETTENDO di verificare.
        seleziona_emittente(cur, emittente_casa)
        cur.execute(
            """
            SELECT count(*) FILTER (WHERE uid::text = %s) AS n_casa,
                   count(*) FILTER (WHERE uid::text = %s) AS n_estraneo
              FROM vendite.preventivi
             WHERE uid::text IN (%s, %s)
            """,
            [uid_casa, uid_estraneo, uid_casa, uid_estraneo],
        )
        n_casa, n_estraneo = riga_obbligatoria(cur, "conteggio di visibilita' vuoto.")
        if n_estraneo != 0:
            raise SystemExit(
                "SENZA_MATERIA: con l'emittente di casa selezionato il preventivo "
                "estraneo e' ancora visibile — la connessione non applica la RLS "
                "(ruolo owner o BYPASSRLS). Ogni perimetro direbbe la stessa cosa "
                "e questo smoke passerebbe SMETTENDO di verificare."
            )
        # ⚠️ E il verso positivo si ASSERISCE: senza, un perimetro che nasconde
        #    TUTTO passerebbe questo test e trascinerebbe i successivi.
        check("il documento di casa resta visibile", n_casa == 1,
              f"casa {n_casa}, estraneo {n_estraneo}")

        # ── 3. Costruzione ────────────────────────────────────────────────
        print("\n=== 3. Costruzione: due pratiche speculari ===")
        # ⭐ I RUOLI SONO INVERTITI FRA LE DUE, ed e' il cuore della prova. Con
        #    `risolto` uguale (perimetro largo) vince il ROOT — criterio 3. ⇒ Su
        #    ciascuna pratica il perimetro largo sceglie il ROOT, e il perimetro
        #    che NON vede quel ROOT deve scegliere l'altro. Due volte, in due
        #    direzioni opposte, sugli stessi due documenti.
        seleziona_emittente(cur, None)
        collega(cur, pratica_a, sorgente_tipo_id, uid_estraneo, uid_casa)
        collega(cur, pratica_b, sorgente_tipo_id, uid_casa, uid_estraneo)
        check("link creati su entrambe", True,
              f"A={pratica_a}: ROOT estraneo · B={pratica_b}: ROOT di casa")

        # ── 4. Perimetro largo ────────────────────────────────────────────
        print("\n=== 4. Perimetro LARGO: su entrambe vince il ROOT ===")
        # ⭐ E' LA RIGA DI PARTENZA CONTRO CUI SI LEGGONO IL 5 E IL 6: senza
        #    scope in mezzo la regola d'ancora si riduce al tiebreak ROOT. Se
        #    questo test fosse rosso, i due seguenti non direbbero niente.
        a_largo_a = ancora(cur, pratica_a)
        a_largo_b = ancora(cur, pratica_b)
        check("la vista risponde su entrambe",
              a_largo_a is not None and a_largo_b is not None)
        if a_largo_a and a_largo_b:
            check("su A vince il ROOT estraneo",
                  a_largo_a["sorgente_uid"] == uid_estraneo,
                  f"scelto {uid_breve(a_largo_a['sorgente_uid'])} ({a_largo_a['ruolo_link']})")
            check("su B vince il ROOT di casa",
                  a_largo_b["sorgente_uid"] == uid_casa,
                  f"scelto {uid_breve(a_largo_b['sorgente_uid'])} ({a_largo_b['ruolo_link']})")
            check("entrambe risolte",
                  a_largo_a["risolto"] is True and a_largo_b["risolto"] is True,
                  f"stato {a_largo_a['stato_codice_interno']}")

        # ── 5. Perimetro ristretto ────────────────────────────────────────
        print("\n=== 5. Perimetro RISTRETTO all'emittente della pratica ===")
        seleziona_emittente(cur, emittente_casa)
        a_casa = ancora(cur, pratica_a)
        check("la vista risponde anche qui", a_casa is not None)
        if a_casa:
            # ⭐ E' LA RISPOSTA ALLA DOMANDA DEL BRIEF: l'ancora CAMBIA, e cambia
            #    nel verso giusto. Il ROOT estraneo perde non perche' sia
            #    nascosto, ma perche' senza il suo descrittore non e' piu'
            #    `risolto` — e il criterio 1 e' risolto-first.
            check("vince il COLLEGATO di casa", a_casa["sorgente_uid"] == uid_casa,
                  f"scelto {uid_breve(a_casa['sorgente_uid'])} ({a_casa['ruolo_link']})")
            check("con il descrittore popolato",
                  a_casa["risolto"] is True
                  and a_casa["stato_codice_interno"] is not None,
                  f"stato {a_casa['stato_codice_interno']}")
            check("⭐ l'ancora e' DIVERSA da quella del perimetro largo",
                  bool(a_largo_a) and a_casa["sorgente_uid"] != a_largo_a["sorgente_uid"],
                  "il cambio di comportamento dichiarato dal brief §3")

        # ── 6. Lo specchio ────────────────────────────────────────────────
        print("\n=== 6. ⭐ LO SPECCHIO: perimetro ESTRANEO sulla pratica a ruoli invertiti ===")
        # ⛔ FINO AL 2026-09-10 QUI SI PRETENDEVA UNA RISPOSTA — «la vista risponde
        #    anche qui, benche' la pratica sia di un altro emittente: non legge
        #    `pratiche.pratiche`» — e sulla pratica speculare doveva vincere il
        #    COLLEGATO estraneo. Dal changeSet `20260910-02` `pratiche_sorgenti`
        #    porta il perimetro da se': chi legge dall'emittente estraneo NON VEDE
        #    i link della pratica, e la vista non ha piu' niente su cui scegliere.
        #    Lo specchio, come verdetto della vista, non e' piu' osservabile — ed
        #    e' la proprieta' piu' forte: il perimetro si chiude sul LINK, non
        #    solo nel consumatore (test 7).
        # ⚠️ Trovato il 2026-09-12 da `smoke-baseline.sh` come regressione: era
        #    lo smoke a essere rimasto indietro rispetto al modello, non il DB.
        seleziona_emittente(cur, emittente_estraneo)
        a_estraneo = ancora(cur, pratica_b)
        check("dal perimetro estraneo la vista NON risponde — il link stesso e' nel perimetro",
              a_estraneo is None,
              "" if a_estraneo is None
              else f"risponde con {uid_breve(a_estraneo['sorgente_uid'])} ({a_estraneo['ruolo_link']})")

        # ── 7. Il consumatore vero ────────────────────────────────────────
        print("\n=== 7. Il consumatore vero: get_pratica() ===")
        # ⚠️ La vista nuda non basta: il backend la legge in LEFT JOIN dentro
        #    `_PRATICA_JOINS`, e un join che sbagliasse l'aggancio direbbe NULL
        #    su una pratica che l'ancora ce l'ha — indistinguibile da «nessun
        #    documento collegato».
        seleziona_emittente(cur, emittente_casa)
        riga = PraticheRepository().get_pratica(pratica_a)
        check("la pratica si legge dal proprio perimetro", riga is not None)
        if riga and a_casa:
            check("il repository porta il descrittore della vista",
                  riga["doc_stato_codice_interno"] == a_casa["stato_codice_interno"]
                  and riga["doc_risolto"] == a_casa["risolto"],
                  f"doc_stato={riga['doc_stato_codice_interno']}, "
                  f"doc_risolto={riga['doc_risolto']}")

        # E dal perimetro dell'emittente ESTRANEO la pratica non esiste
        # affatto: il 404 nasce da `pratiche.pratiche`, non dalla vista — che
        # infatti al test 6 ha risposto.
        seleziona_emittente(cur, emittente_estraneo)
        assente = PraticheRepository().get_pratica(pratica_a)
        check("dal perimetro estraneo la pratica non si vede", assente is None,
              "il rifiuto arriva dalla testata, non da un descrittore vuoto")

    transaction.set_rollback(True)

print(f"\n=== ESITO: {'FALLITO — ' + ', '.join(FAIL) if FAIL else 'TUTTO VERDE'} ===\n")
