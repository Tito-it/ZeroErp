-- ------------------------------------------------------------
-- SPDX-License-Identifier: GPL-3.0-or-later
-- pgTAP test per Zero ERP
--
-- Passo 7 (P-2b) del cantiere «perimetro emittente»: il flag multi_emittente
-- esiste, non si scrive dall'applicazione, e nasce spento su tutte le liste.
-- Brief: docs/it/dev/work-in-progress/brief-db-perimetro-emittente-liste-e-gerarchia-ba.md §11.5, Q1
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
CREATE TEMP TABLE _t_lista ON COMMIT DROP AS
SELECT ld.id, ld.codice
  FROM ui.lista_definizione ld
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

-- 5) Il registro di debito parte pieno: nessuna lista e' ancora certificata.
--    ⚠️ Quando questo numero cambia deve essere perche' qualcuno ha fatto il
--    lavoro di P-4 su quella lista — e il test 6 lo verifica.
SELECT is(
    (SELECT count(*) FROM ui.lista_definizione WHERE multi_emittente),
    0::bigint,
    '5. nessuna lista dichiara multi_emittente: il registro di debito parte pieno'
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
