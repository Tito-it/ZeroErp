-- ------------------------------------------------------------
-- SPDX-License-Identifier: GPL-3.0-or-later
-- pgTAP test per Zero ERP
--
-- Passo 7 (P-2b) del cantiere «perimetro emittente»: il flag multi_emittente
-- esiste, non si scrive dall'applicazione, e nasce spento su tutte le liste.
-- Brief: brief-db-perimetro-emittente-liste-e-gerarchia-ba.md §11.5, Q1
--
-- Elenco test (plan 9):
--   0) PRECONDIZIONE: il test gira come applicazione, NON come proprietario
--   1) la colonna esiste
--   2) il default e' false (una lista nuova nasce NON certificata)
--   3) * l'applicazione NON puo' accendere il flag        ⬅ lo strato 1
--   4) * l'applicazione non puo' nemmeno crearne una accesa
--   5) il registro di debito parte pieno: nessuna lista e' certificata
--   6) la vista di controllo esiste ed e' a zero righe
--   7) * l'envelope di fn_resolve_lista_config porta la chiave
--   8) * ...e per una lista non certificata vale false
--
-- Scopo:
--  - il 3 e' LO strato 1 di P-2b. Il piano prevedeva un permesso di colonna;
--    e' diventato un trigger perche' il giro dei grant runtime (ci_apply,
--    runOnChange) ri-concede UPDATE di tabella a ogni passata e la revoca non
--    sopravviverebbe. Qui si verifica che il presidio scelto tenga davvero,
--    esercitandolo dal ruolo da cui deve difendere;
--  - il 5 e' il registro di debito: parte da «nessuna lista e' pronta» e deve
--    CALARE. Se un giorno questo test diventa rosso perche' il numero e' salito
--    senza che nessuno abbia fatto il lavoro, e' esattamente il segnale che
--    serve.
--
-- ⚠️ PERCHE' IL TEST DEVE GIRARE COME APPLICAZIONE, e non e' un dettaglio:
--   il guard ammette la scrittura a chi e' (o e' membro del) PROPRIETARIO
--   della tabella. Girando come owner i test 3 e 4 passerebbero la scrittura e
--   il file sarebbe verde per sottrazione — nel modo peggiore, perche'
--   verificherebbe il contrario di quel che dice. Il test 0 lo dichiara
--   esplicitamente invece di darlo per scontato.
-- ------------------------------------------------------------

BEGIN;

DO $ctx$ BEGIN PERFORM script.fn_pgtap_set_contesto_operatore(); END $ctx$;

SET CONSTRAINTS ALL IMMEDIATE;

SELECT plan(9);

-- ============================================================
-- Fixture
-- ============================================================
-- ⚠️ `NOT multi_emittente` non e' pignoleria: il test 8 asserisce che
--   l'envelope risponda `false`, e dal 2026-08-18 il registro ha una lista
--   certificata. Pescare «la prima per id» funzionava finche' erano zero;
--   il giorno in cui la certificata fosse la prima, il test 8 diventerebbe
--   rosso raccontando un difetto che non c'e'. Si sceglie il soggetto per la
--   condizione che rende il caso significativo, non per la posizione.
CREATE TEMP TABLE _t_lista ON COMMIT DROP AS
SELECT ld.id, ld.codice
  FROM ui.lista_definizione ld
 WHERE NOT ld.multi_emittente
 ORDER BY ld.id
 LIMIT 1;

-- ============================================================
-- Asserzioni
-- ============================================================

-- 0) Il presupposto di tutto il file.
SELECT ok(
    NOT pg_has_role(
            current_user,
            (SELECT pg_get_userbyid(c.relowner)
               FROM pg_class c JOIN pg_namespace n ON n.oid = c.relnamespace
              WHERE n.nspname = 'ui' AND c.relname = 'lista_definizione'),
            'USAGE'),
    '0. PRECONDIZIONE: il test gira come APPLICAZIONE, non come proprietario della tabella'
);

SELECT has_column(
    'ui', 'lista_definizione', 'multi_emittente',
    '1. la colonna multi_emittente esiste'
);

SELECT col_default_is(
    'ui', 'lista_definizione', 'multi_emittente', 'false',
    '2. default false: una lista nuova nasce NON certificata'
);

-- 3) * Lo strato 1: l'applicazione non accende il flag.
SELECT throws_like($$
    UPDATE ui.lista_definizione
       SET multi_emittente = true
     WHERE id = (SELECT id FROM _t_lista)
$$, '%non si imposta dall%',
    '3. * l''applicazione NON puo'' accendere il flag (strato 1, Q1)');

-- 4) * ...ne' crearne una gia' accesa.
SELECT throws_like($$
    INSERT INTO ui.lista_definizione
           (codice, descrizione, schema_dati, attivo, user_insert, multi_emittente)
    VALUES ('tst.p2b.lista_furba', 'Lista che nasce certificata', 'vendite', true, 'pgtap', true)
$$, '%non si imposta dall%',
    '4. * l''applicazione non puo'' nemmeno crearne una gia'' accesa');

-- 5) Il registro di debito. ⭐ Rev 2026-08-18: non e' piu' «zero». Sono le SEI
--    liste del perimetro emittente, accese per decisione di Tid nello stesso
--    giorno (brief §13-ter.5 e §13-ter.7); poi una il 27-08, due il 18-09 e
--    una il 19-09, ciascuna con la sua riga datata nell'elenco qui sotto.
--
--    ⚠️ E va detto qui, perche' e' qui che si legge: sulla PILOTA il flag ha
--    dietro il giro completo (vista + repository + i18n); sulle altre cinque
--    e' stato acceso PRIMA che il backend selezioni la colonna (BE-5), quindi
--    la colonna e' spuntabile e a video resta vuota finche' quel lavoro non
--    arriva. E' una scelta presa a occhi aperti, non un adesivo scappato: non
--    siamo in produzione e il gate serviva a proteggere un utente che qui non
--    c'e'. Il registro torna a significare qualcosa quando BE-5 e' chiusa.
--
--    ⚠️ Si asserisce l'ELENCO, non il conteggio. Un numero dice «sono due» e
--    lascia credere che siano le due giuste; l'elenco dice QUALI, e chi accende
--    un flag deve venire qui a scriverlo. E' il «prezzo del biglietto» reso
--    esplicito: il test non si aggiorna da solo, e non deve.
--
--    ⚠️ Questo test e il 6 misurano cose diverse e servono entrambi: il 6 dice
--    «nessun flag senza la colonna a catalogo» (a macchina, sempre), il 5 dice
--    «nessun flag che un umano non abbia dichiarato qui» — cioe' presidia
--    anche il caso in cui la colonna c'e' ma non porta un valore, che il
--    catalogo non puo' vedere (il difetto di `20260818-61`, vedi
--    test-lista-competenza-gruppi-colonna-emittente-v1 test 6).
SELECT is(
    (SELECT COALESCE(array_agg(ld.codice::text ORDER BY ld.codice), '{}'::text[])
       FROM ui.lista_definizione ld
      WHERE ld.multi_emittente),
    ARRAY[
          -- ⭐ 2026-10-02 — brief-db-be-fe-area-accessi, R-DB-A3: ogni utente
          --   tecnico lavora per UNA azienda (config.user_emittenti_fiscali,
          --   UNIQUE sull'utente), e il tab «Di sistema» le mostra tutte al
          --   super admin. Stampo di anagrafiche.operatori: il biglietto e' la
          --   colonna attiva `emittente_codice` (campo_sorgente
          --   `emittente_codice`), che il test 6 riconosce. Un API_CLIENT senza
          --   perimetro ha la cella vuota, come il super admin fra gli operatori.
          'anagrafiche.accessi_sistema',
          -- ⭐ 2026-09-18 — D-3 di Tid, brief-db-perimetro-emittente-cataloghi-
          --   globali: ogni operatore ha UN emittente, ma la lista ne mescola
          --   di aziende diverse quando il super admin la apre su «Tutti», e
          --   la colonna attiva `emittenti_descrizione` («Emittente fiscale»)
          --   dice per ogni riga a quale azienda appartiene — c'era gia',
          --   quindi il biglietto (test 6) era gia' pagato e mancava solo la
          --   dichiarazione. ⚠️ Il flag e' della LISTA, non dell'operatore:
          --   l'unico attore multi-emittente resta il super admin.
          'anagrafiche.operatori',
          -- ⭐ 2026-09-19 — D-4 di Tid, stesso brief: ogni email e' spedita per
          --   conto di UN emittente (o di nessuno: le righe `SISTEMA`, cella
          --   vuota), e su «Tutti» il super admin ne vede di aziende diverse.
          --   Qui il biglietto e' stato pagato nell'ordine giusto: colonna 872
          --   (`emittente_fiscale`, campo_sorgente `emittente_ragione_sociale`)
          --   nata SPENTA il 18-09, accesa dal backend il 19-09 nello stesso
          --   commit della proiezione (`email_repository.list_logs`, BE-3/BE-4),
          --   e SOLO DOPO il flag — ⚠️ mai il flag prima della colonna, o il
          --   test 6 esce da zero.
          'config.email_log',
          -- ⭐ 2026-09-27 — brief-db-liste-datatable-grezze, riga 4: ogni riga
          --   e' l'override di UN emittente su una riga della matrice utility /
          --   tipi ruolo, e la lista (tab «Utilizzo», pannello di
          --   amministrazione) le mostra di aziende diverse. Il biglietto e'
          --   pagato dalla colonna `emittente_codice` (campo_sorgente
          --   `emittente_codice`, attiva), che il test 6 riconosce.
          'config.utilities_tipi_ruolo_usage',
          -- ⭐ 2026-09-27 — Tid, brief-db-liste-datatable-grezze §8 punto 7:
          --   ogni template e' di UN emittente (`emittente_fiscale_id` NOT
          --   NULL), e la colonna `emittente_ragione_sociale` (id 310, attiva)
          --   c'era gia': il biglietto era pagato, mancava la dichiarazione.
          'documenti.template_documenti',
          -- ⭐ 2026-10-31 — brief-db-liste-datatable-grezze-secondo-giro §2,
          --   riga 1: ogni edizione di workflow e' di UN emittente, e il preset
          --   di sistema di nessuno (`emittente_fiscale_id` NULL), come i
          --   modelli standard di template_documenti. La colonna Emittente
          --   (campo_sorgente `emittente_display`) nasce attiva col seed: il
          --   biglietto e' pagato nello stesso giro della dichiarazione.
          'pratiche.definizioni_workflow',
          -- ⭐ 2026-09-18 — D-5 di Tid, stesso brief: un preset PUO' essere di
          --   un'azienda (`ambito = emittente_fiscale`), e la colonna «Emittente»
          --   (id 873, campo_sorgente `emittente_ragione_sociale`) e' attiva dal
          --   18-09 — il repository `_PRESET_SELECT_SQL` la proiettava gia'
          --   per la colonna calcolata «Riferimento», quindi il biglietto era
          --   gia' pagato e mancava la colonna che il presidio riconosce.
          'ui.lista_preset',
          'vendite.dash_aperto_documenti',
          'vendite.dash_backlog_documenti',
          'vendite.dash_competenza_commesse',
          'vendite.dash_competenza_errori',
          'vendite.dash_competenza_gruppi',
          -- ⭐ 2026-08-27 — certificata dal cantiere «residui in competenza»
          --   (seed `lista_definizione` id 49, commit b543f51fa). Il biglietto
          --   e' stato pagato QUI, che e' il punto di questo test: il flag non
          --   si accende senza che qualcuno venga a dichiararlo.
          --   ✅ Verificato prima di scriverla: la lista porta la colonna
          --   `emittente_fiscale` a catalogo — che e' la condizione meccanica
          --   presidiata dal test 6 — ed e' della stessa famiglia delle altre
          --   quattro `dash_*` gia' certificate, con lo stesso meccanismo di
          --   scope.
          'vendite.dash_competenza_residui',
          'vendite.lotti']::text[],
    '5. le liste certificate multi_emittente sono esattamente quelle dichiarate qui'
);

-- 6) Il controllo automatico esiste e non ha niente da segnalare.
SELECT is(
    (SELECT count(*) FROM dbops.vw_liste_multi_emittente_non_certificate),
    0::bigint,
    '6. vw_liste_multi_emittente_non_certificate a zero righe (nessun adesivo senza collaudo)'
);

-- 7) * La LETTURA: la chiave c'e' nell'envelope.
--    Additiva: i consumatori che non la leggono non se ne accorgono.
-- ⚠️ jsonb_exists() e non l'operatore `?`: in un file pgTAP letto da psql il
--   `?` va bene, ma il `??` NON e' il suo escape — quello serve a Liquibase,
--   che interpreta `?` come segnaposto. Scritto in forma di funzione la
--   domanda non si pone piu', ne' qui ne' se un giorno il frammento finisce
--   dentro un changeSet.
SELECT ok(
    jsonb_exists(
        ui.fn_resolve_lista_config(
            (SELECT codice FROM _t_lista),
            NULLIF(current_setting('app.current_user_id', true), '')::integer,
            NULL),
        'multi_emittente'),
    '7. * l''envelope di fn_resolve_lista_config porta la chiave multi_emittente'
);

-- 8) * ...e dice la verita': la lista non e' certificata.
SELECT is(
    ui.fn_resolve_lista_config(
        (SELECT codice FROM _t_lista),
        NULLIF(current_setting('app.current_user_id', true), '')::integer,
        NULL
    ) -> 'multi_emittente',
    'false'::jsonb,
    '8. * lista non certificata -> multi_emittente false'
);

-- ============================================================
-- Chiusura
-- ============================================================
SELECT * FROM finish();
ROLLBACK;
