-- ------------------------------------------------------------
-- SPDX-License-Identifier: AGPL-3.0-or-later
-- pgTAP test per Zero ERP
--
-- pgtap-runner: owner
-- pgtap-runner-motivo: la fixture semina su dbops.presidi — catalogo che a
--   runtime non scrive nessuno (lo popola il mirror CSV di 80_data) e su cui il
--   ruolo applicativo ha SELECT-only — e crea uno schema e una vista di prova,
--   cioe' DDL. Verificato cercando gli scrittori, non dedotto: e' la stessa
--   situazione, con la stessa motivazione, di test-presidi-debito-dichiarato.sql.
--
-- Test: il catalogo dei presidi, nei DUE versi, e il contatore onesto
-- Brief: brief-db-un-destinatario-per-i-presidi.md §4.1
--
-- Elenco test (plan 11):
--  1) ⭐ la misura non e' degradata: il catalogo esiste e NON e' vuoto
--  2) ⭐ VERSO 1 — ogni vista degli schemi dichiarati e' a catalogo
--  3) ⭐ VERSO 2 — ogni riga del catalogo punta a una vista VIVA
--  4) dove c'e' `colonna_stato`, quella colonna esiste davvero sulla vista
--  5) ogni `registro` dichiarato e' una tabella che esiste
--  6) ⛔ la `nota` e' obbligatoria: una riga senza motivo la rifiuta il DATABASE
--  7) ⛔ una riga CANCELLO senza `presidiato_da` e' rifiutata
--  8) ⛔ fn_conta_presidio su una vista NON a catalogo solleva, e non torna zero
--  9) fn_conta_presidio conta la vista INTERA quando `colonna_stato` e' NULL
-- 10) ⭐ fn_conta_presidio conta «diverso dallo stato atteso»: uno stato NUOVO
--     cade nell'ALLARME, non nel silenzio
-- 11) 🔴 il SECURITY DEFINER ha ancora il proprietario che serve: ogni tabella
--     protetta letta da una vista DEFINER appartiene al proprietario della
--     funzione che conta (dal 2026-10-10 la sede,
--     fn_conta_presidio_per_variante: fn_conta_presidio ne e' la somma, INVOKER)
--
-- ────────────────────────────────────────────────────────────────
-- ⭐ I DUE VERSI VANNO LETTI INSIEME, ed e' il punto del file.
--   Il verso 1 impedisce alla vista successiva di nascere FUORI dal digest —
--   ed e' gia' successo: dbops.vw_rls_perimetro_scoperto e' nata il 2026-09-09,
--   lo stesso giorno in cui il brief ne contava trentuno.
--   Il verso 2 impedisce al catalogo di diventare un elenco di righe che non
--   corrispondono piu' a niente. Senza il secondo, il catalogo puo' solo
--   allungarsi: e' la stessa coppia dei tre versi del cancello dei codici
--   errore, e la stessa ragione.
--
-- ⭐ I test 9 e 10 vanno letti insieme allo stesso modo: sono lo stesso
--   contatore su due domande diverse. Provare solo il 9 lascerebbe passare un
--   filtro che non filtra; provare solo il 10 lascerebbe passare un contatore
--   che filtra sempre.
--
-- ⚠️ La fixture vive in uno SCHEMA SUO e non in `dbops`: se la vista di prova
--   nascesse li', il test 2 la vedrebbe come vista non catalogata e sarebbe
--   rosso per un motivo che non e' un difetto — oppure andrebbe esclusa per
--   nome, che sarebbe un buco nel presidio.
--
-- ── ⚠️ LIMITI DICHIARATI ────────────────────────────────────────
--   · Il test 11 guarda le sole tabelle **gia' in row level security**. Delle
--     tre viste marcate DEFINER ne copre DUE (`vw_eventi_non_dichiarati` ->
--     `vendite.event_log`, `vw_diag_v_clienti_links` ->
--     `anagrafiche.billing_account`), misurato il 2026-09-10. La terza,
--     `vw_af_senza_giro`, oggi NON e' coperta perche'
--     `vendite.attivita_fatturabili` la RLS non ce l'ha ancora — e' il debito
--     dichiarato in `dbops.rls_perimetro_debito`. ⭐ Entrera' da sola nel
--     perimetro il giorno in cui quel debito si salda: il criterio si estende,
--     non va aggiornato a mano.
--   · Ramo negativo provato il 2026-09-10 sostituendo il proprietario atteso:
--     la query segnala entrambe le tabelle. Non e' verde per sottrazione.
--   · ⛔ Cio' che NESSUN test di questo file prova e' il comportamento a
--     runtime del `SECURITY DEFINER` letto **da `zeroerp_app` senza le GUC**:
--     il file gira da owner, e da li' la row level security non si vede.
--     Quello che si asserisce e' che i PRESUPPOSTI ci siano ancora (test 11),
--     che e' la parte che puo' rompersi in silenzio.
-- ------------------------------------------------------------

BEGIN;

DO $ctx$ BEGIN PERFORM script.fn_pgtap_set_contesto_operatore(); END $ctx$;

SET CONSTRAINTS ALL IMMEDIATE;

SELECT plan(11);

-- ============================================================
-- 1) La misura non e' degradata
-- ============================================================
-- ⛔ Va per PRIMO, e non e' burocrazia: il test 2 legge il proprio PERIMETRO
--   dal catalogo, quindi su un catalogo vuoto non guarderebbe nessuna vista e
--   passerebbe a vuoto. Un cancello che passa perche' non ha misurato niente e'
--   peggio di un cancello assente. E' lo stesso test 4 del cancello dei codici
--   errore.
-- ⚠️ La soglia e' «non vuoto» e non un numero: QUANTE righe servano lo dice il
--   test 2 confrontando col database, e un numero scritto qui invecchierebbe
--   alla prima vista nuova — cioe' proprio all'evento che questo file presidia.
SELECT cmp_ok(
    (SELECT count(*) FROM dbops.presidi)::bigint, '>', 0::bigint,
    'test 1 — il catalogo dei presidi non e'' vuoto (misura non degradata)');

-- ============================================================
-- 2) VERSO 1 — nessuna vista fuori dal catalogo
-- ============================================================
-- ⚠️ Il perimetro si legge DAL CATALOGO (gli schemi che compaiono nella colonna
--   `vista`), non da un LIKE su `dbops.vw_%`: un glob di un livello solo
--   diventa un ramo cieco il giorno in cui un presidio nasce in un altro
--   schema, e quel giorno il presidio tacerebbe proprio sulla vista nuova.
SELECT is(
    coalesce((
        SELECT string_agg(v.nspname || '.' || v.relname, ', ' ORDER BY v.nspname, v.relname)
          FROM (SELECT n.nspname, c.relname
                  FROM pg_class c
                  JOIN pg_namespace n ON n.oid = c.relnamespace
                 WHERE c.relkind = 'v'
                   AND n.nspname IN (SELECT DISTINCT split_part(vista, '.', 1)
                                       FROM dbops.presidi)) v
         WHERE NOT EXISTS (SELECT 1 FROM dbops.presidi p
                            WHERE p.vista = v.nspname || '.' || v.relname)), ''),
    '',
    'test 2 — ogni vista degli schemi dichiarati ha la sua riga in dbops.presidi');

-- ============================================================
-- 3) VERSO 2 — nessuna riga di catalogo senza la sua vista
-- ============================================================
-- ⛔ E' il verso che il brief non chiedeva. Senza, il catalogo puo' solo
--   allungarsi: una vista rinominata o ritirata lascerebbe una riga che nessuno
--   guarda, e il digest continuerebbe a fallire su di essa oppure a saltarla in
--   silenzio.
SELECT is(
    coalesce((
        SELECT string_agg(p.vista, ', ' ORDER BY p.vista)
          FROM dbops.presidi p
         WHERE NOT EXISTS (
                   SELECT 1 FROM pg_class c
                     JOIN pg_namespace n ON n.oid = c.relnamespace
                    WHERE c.relkind = 'v'
                      AND n.nspname = split_part(p.vista, '.', 1)
                      AND c.relname = split_part(p.vista, '.', 2))), ''),
    '',
    'test 3 — ogni riga di dbops.presidi punta a una vista che esiste');

-- ============================================================
-- 4) La colonna di stato dichiarata esiste sulla vista
-- ============================================================
-- ⚠️ Un filtro su una colonna che non c'e' non e' un presidio piu' debole: e'
--   il digest che esplode a runtime, cioe' un presidio che smette di girare.
SELECT is(
    coalesce((
        SELECT string_agg(p.vista || '.' || p.colonna_stato, ', ' ORDER BY p.vista)
          FROM dbops.presidi p
         WHERE p.colonna_stato IS NOT NULL
           AND NOT EXISTS (
                   SELECT 1 FROM pg_attribute a
                     JOIN pg_class c      ON c.oid = a.attrelid
                     JOIN pg_namespace n  ON n.oid = c.relnamespace
                    WHERE n.nspname = split_part(p.vista, '.', 1)
                      AND c.relname = split_part(p.vista, '.', 2)
                      AND a.attname = p.colonna_stato
                      AND a.attnum > 0
                      AND NOT a.attisdropped)), ''),
    '',
    'test 4 — ogni colonna_stato dichiarata esiste sulla sua vista');

-- ============================================================
-- 5) Il registro dichiarato esiste
-- ============================================================
-- ⚠️ Un registro che punta al vuoto e' un'etichetta rassicurante: dice «il
--   debito e' tenuto» e non lo tiene nessuno.
SELECT is(
    coalesce((
        SELECT string_agg(p.registro, ', ' ORDER BY p.registro)
          FROM dbops.presidi p
         WHERE p.registro IS NOT NULL
           AND to_regclass(p.registro) IS NULL), ''),
    '',
    'test 5 — ogni registro dichiarato e'' una relazione che esiste');

-- ============================================================
-- 6) e 7) I due vincoli che il DATABASE deve rifiutare
-- ============================================================
-- ⛔ Non e' un doppione dei CHECK: e' la prova che ci SONO. La guida dei
--   presidi mette «senza un motivo scritto la voce non si aggiunge» fra i
--   vincoli del database e non fra i test, apposta perche' non dipenda da chi
--   si ricorda di lanciare un controllo — quindi la regola che si collauda qui
--   e' che quel vincolo non si possa aggirare.
SELECT throws_ok(
    $$INSERT INTO dbops.presidi (vista, natura, cadenza, perimetro, nota)
      VALUES ('dbops.vw_pgtap_senza_nota', 'INVENTARIO', 'MAI', 'LIBERO', '   ')$$,
    '23514', NULL,
    'test 6 — una riga con la nota vuota e'' rifiutata dal database');

SELECT throws_ok(
    -- ⚠️ chi_agisce valorizzata apposta (2026-10-06): senza, la riga la
    --   rifiuterebbe ANCHE chk_presidi_chi_agisce_se_allarma, e il 23514
    --   passerebbe per il vincolo sbagliato.
    $$INSERT INTO dbops.presidi (vista, natura, cadenza, perimetro, nota, chi_agisce)
      VALUES ('dbops.vw_pgtap_cancello_muto', 'CANCELLO', 'MAI', 'LIBERO',
              'un cancello che non dice dove vive', 'SVILUPPO')$$,
    '23514', NULL,
    'test 7 — una riga CANCELLO senza presidiato_da e'' rifiutata dal database');

-- ============================================================
-- Fixture per i test 8..10 — schema suo, fuori dal perimetro del test 2
-- ============================================================
CREATE SCHEMA pgtap_presidi_fixture;

-- Tre righe con tre stati diversi. Il terzo — CIRCOSTANZA_NUOVA — e' il caso
-- che decide il test 10: non esiste in nessuna vista vera, ed e' li' per
-- rappresentare LO STATO CHE QUALCUNO AGGIUNGERA' DOMANI.
CREATE VIEW pgtap_presidi_fixture.vw_finta AS
SELECT * FROM (VALUES ('DEBITO_DICHIARATO'), ('NON_DICHIARATO'), ('CIRCOSTANZA_NUOVA'))
             AS t(stato);

CREATE VIEW pgtap_presidi_fixture.vw_finta_intera AS
SELECT * FROM (VALUES (1), (2), (3), (4)) AS t(n);

-- ⚠️ Le viste PRIMA delle righe di catalogo: e' l'ordine in cui il test 3
--   pretende che stiano le cose, e una fixture che lo viola insegnerebbe il
--   contrario a chi la copia.
-- ⚠️ chi_agisce dal 2026-10-06: un presidio che si accende deve dire a chi
--   tocca (chk_presidi_chi_agisce_se_allarma, brief-db-presidi-cosa-significa-cosa-fare).
INSERT INTO dbops.presidi (vista, natura, colonna_stato, stato_atteso,
                           cadenza, perimetro, nota, chi_agisce)
VALUES ('pgtap_presidi_fixture.vw_finta', 'ZERO', 'stato', 'DEBITO_DICHIARATO',
        'MAI', 'LIBERO', 'fixture pgTAP del catalogo dei presidi', 'SVILUPPO'),
       ('pgtap_presidi_fixture.vw_finta_intera', 'ZERO', NULL, NULL,
        'MAI', 'LIBERO', 'fixture pgTAP: conteggio della vista intera', 'SVILUPPO');

-- ============================================================
-- 8) Una vista non a catalogo non si conta: SOLLEVA
-- ============================================================
-- ⛔ Il ramo che conta non e' «torna zero»: sarebbe indistinguibile da una
--   vista sana. E il perimetro del catalogo e' cio' che impedisce a una
--   funzione SECURITY DEFINER di diventare una porta per contare qualunque
--   relazione aggirando la row level security.
-- ⚠️ Con lo SQLSTATE: throws_ok(sql, NULL, NULL) accetta QUALUNQUE errore,
--   compreso un permesso negato che non c'entra niente.
SELECT throws_ok(
    $$SELECT dbops.fn_conta_presidio('dbops.vw_che_non_esiste_affatto')$$,
    'P0001', NULL,
    'test 8 — fn_conta_presidio rifiuta una vista non a catalogo');

-- ============================================================
-- 9) Senza colonna_stato si conta la vista intera
-- ============================================================
SELECT is(
    dbops.fn_conta_presidio('pgtap_presidi_fixture.vw_finta_intera'),
    4::bigint,
    'test 9 — senza colonna_stato fn_conta_presidio conta la vista intera');

-- ============================================================
-- 10) ⭐ «Diverso dallo stato atteso»: lo stato nuovo cade nell'ALLARME
-- ============================================================
-- La vista di prova ha TRE stati: uno atteso (DEBITO_DICHIARATO) e due no.
-- Il secondo — NON_DICHIARATO — e' l'allarme che ci si aspetta.
-- ⭐ Il terzo — CIRCOSTANZA_NUOVA — e' il motivo per cui il catalogo dichiara
--   lo stato ATTESO e non quelli di allarme: con un elenco di allarmi quello
--   stato non ci sarebbe, e cadrebbe nel SILENZIO. Qui deve contare 2, non 1.
--   Se un giorno questo test tornasse 1, qualcuno ha invertito il verso — e
--   avrebbe spento il presidio sugli stati che non aveva previsto.
SELECT is(
    dbops.fn_conta_presidio('pgtap_presidi_fixture.vw_finta'),
    2::bigint,
    'test 10 — si conta cio'' che e'' DIVERSO dallo stato atteso: lo stato nuovo e'' un allarme');

-- ============================================================
-- 11) 🔴 Il SECURITY DEFINER ha ancora il proprietario che serve
-- ============================================================
-- ⛔ E' l'assunto su cui poggia TUTTO il perimetro DEFINER, e oggi e' vero per
--   COINCIDENZA: chi lancia le migrazioni possiede anche le tabelle — `titodb`
--   in sviluppo, `zeroerp` in CI. Sono due ruoli diversi, e la cosa funziona
--   solo perche' in ciascun ambiente il migratore e' anche il proprietario.
--
--   La row level security e' ENABLE senza FORCE su tutte le tabelle protette
--   (misurato il 2026-09-10: 77 in RLS, zero con FORCE), quindi il proprietario
--   la attraversa. Ma il giorno in cui una tabella nascesse sotto un ruolo
--   diverso, `fn_conta_presidio` tornerebbe a leggere ZERO su quella vista —
--   ⛔ cioe' esattamente il difetto che esiste per chiudere, e in silenzio.
--
-- ⭐ Questo test trasforma la coincidenza in un'asserzione: qui non si verifica
--   una convenzione, si verifica che il meccanismo abbia ancora i suoi
--   presupposti.
SELECT is(
    coalesce((
        SELECT string_agg(DISTINCT t.oid::regclass::text || ' (di ' || pg_get_userbyid(t.relowner) || ')', ', ')
          FROM dbops.presidi p
          JOIN pg_class      vc ON vc.oid = (p.vista)::regclass
          JOIN pg_rewrite    rw ON rw.ev_class = vc.oid
          JOIN pg_depend     d  ON d.objid = rw.oid
                               AND d.classid = 'pg_rewrite'::regclass
                               AND d.refclassid = 'pg_class'::regclass
          JOIN pg_class      t  ON t.oid = d.refobjid
         WHERE p.perimetro = 'DEFINER'
           AND p.attivo
           AND t.oid <> vc.oid
           AND t.relrowsecurity                       -- solo cio' che filtra
           AND t.relowner <> (SELECT proowner FROM pg_proc pr
                                JOIN pg_namespace pn ON pn.oid = pr.pronamespace
                               WHERE pn.nspname = 'dbops'
                                 -- ⚠️ dal 2026-10-10 la DEFINER che legge le viste e' la
                                 --   sede del conteggio; fn_conta_presidio e' la sua somma,
                                 --   INVOKER (20261010-41/-42). Nominare la somma qui
                                 --   pinnerebbe il proprietario della funzione sbagliata.
                                 AND pr.proname = 'fn_conta_presidio_per_variante')), ''),
    '',
    'test 11 — ogni tabella protetta letta da una vista DEFINER appartiene al proprietario della sede del conteggio (fn_conta_presidio_per_variante)');

SELECT * FROM finish();
ROLLBACK;
