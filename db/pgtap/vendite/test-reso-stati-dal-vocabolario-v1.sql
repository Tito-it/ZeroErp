-- ------------------------------------------------------------
-- SPDX-License-Identifier: AGPL-3.0-or-later
-- pgTAP test per Zero ERP
--
-- Test: il reso legge il significato dei suoi stati dal vocabolario, e il reso
--   dalla bolla ha una regola sola.
--   ChangeSet: 20261114-47 (script.fn_check_ddt_rendibile), -48
--   (vendite.trgfn_resi_guard_ddt_consegnato), -49
--   (script.fn_available_actions_ddt, can_genera_reso), -50
--   (script.fn_available_actions_reso), -51 (script.fn_check_reso_merce), -52
--   (vendite.fn_conferma_reso), -53 (vendite.fn_annulla_reso), -54
--   (vendite.fn_genera_ddt_riconsegna), -55 (vendite.fn_chiudi_riconsegna_reso),
--   -56 (vendite.fn_riapri_riconsegna_reso), -57
--   (vendite.trgfn_resi_righe_guard_quantita).
--   Brief: brief-db-stati-documento-dal-vocabolario, giro 6e (S-2, D-RESO).
--
-- Semantica attesa (il contratto, non l'implementazione):
--   - la capability della bolla dice can_genera_reso dalla stessa check da cui
--     il trigger rifiuta il reso;
--   - la capability del reso dice can_edit_righe dal lock delle righe e
--     can_riconsegna dallo stato di emissione, la porta dei tre verbi della
--     riconsegna;
--   - la conferma e l'annullo si rifiutano dove la matrice non ha il passaggio,
--     e l'annullo va verso lo stato che il vocabolario marca is_abortito;
--   - il tetto della quantita' resa somma i resi che non sono nello stato di
--     annullo;
--   - i lettori di significato non nominano DRAFT, CONFERMATO e ANNULLATO, e il
--     trigger del reso dalla bolla non riscrive la regola della check
--     (presidio sulla FORMA, dichiarato tale).
--
-- ⭐ LA MARCA SPOSTATA: le colonne si spostano in transazione su un altro
--   stato, e la risposta deve seguirle. Ogni marca ha il suo contrasto, letto
--   prima dello spostamento, e si rimette al suo posto prima della successiva.
--   Gli indici unici parziali sono immediati: prima si spegne la marca di
--   partenza, poi si accende l'altra.
-- ⭐ I CASI SI COSTRUISCONO, dalle strade dell'applicazione: bolle e resi dai
--   builder (la conferma passa dal verbo), l'annullo da vendite.fn_annulla_reso,
--   la riconsegna dai suoi tre verbi. Nessuno skip.
--
-- Elenco test (plan 14):
--   1) contrasto: can_genera_reso vero sulla bolla consegnata, falso
--      sull'emessa col motivo DDT_NON_CONSEGNATO
--   2) contrasto: il reso dall'emessa si rifiuta (E_RESO_DDT_NON_CONSEGNATO)
--   3) contrasto: can_edit_righe e can_riconsegna in bozza e nel confermato
--   4) contrasto: i tre verbi della riconsegna rifiutano la bozza
--      (E_RESO_NON_CONFERMATO)
--   5) contrasto: l'annullo porta la bozza in ANNULLATO
--   6) contrasto: la conferma dell'annullato si rifiuta
--      (E_RESO_STATO_NON_CONFERMABILE: la matrice non ha il passaggio)
--   7) contrasto: oltre il consegnato il reso si rifiuta
--      (E_RESO_QTA_SUPERA_CONSEGNATO)
--   8) forma: i lettori di significato non nominano DRAFT, CONFERMATO, ANNULLATO
--   9) forma: il trigger del reso dalla bolla non nomina CONSEGNATO e TRASF_OUT
--  10) ⭐ iniziale su CONFERMATO: can_edit_righe falso in bozza, vero nel
--      confermato
--  11) ⭐ emissione su DRAFT: can_riconsegna vero in bozza, falso nel confermato
--  12) ⭐ ... e la ri-spedizione del confermato si rifiuta
--  13) ⭐ is_abortito su DRAFT: l'annullo del confermato va verso DRAFT, che la
--      matrice non ha (E_RESO_STATO_NON_ANNULLABILE)
--  14) ⭐ is_abortito su CONFERMATO: il reso confermato non conta piu' nel tetto
-- ------------------------------------------------------------

BEGIN;

DO $ctx$ BEGIN PERFORM script.fn_pgtap_set_contesto_operatore(); END $ctx$;

SET CONSTRAINTS ALL IMMEDIATE;

SELECT plan(14);

-- ============================================================
-- Fixture
-- ============================================================
CREATE TEMP TABLE t_ddt (caso text PRIMARY KEY,   -- l'etichetta del test
                         id   bigint);            -- vendite.ddt.id

INSERT INTO t_ddt
SELECT 'consegnata', b.ddt_id FROM dbops.fn_pgtap_crea_ddt_da_ordine('reso dal vocabolario, consegnata') b;
INSERT INTO t_ddt
SELECT 'emessa', b.ddt_id FROM dbops.fn_pgtap_crea_ddt_senza_ordine('reso dal vocabolario, emessa', 'EMESSO') b;
-- Il tetto: cinque pezzi consegnati, tre gia' resi da un reso confermato (la
-- bolla resta CONSEGNATO: il reso non e' totale).
INSERT INTO t_ddt
SELECT 'tetto', b.ddt_id FROM dbops.fn_pgtap_crea_ddt_da_ordine('reso dal vocabolario, tetto', p_quantita => 5) b;

CREATE TEMP TABLE t_reso (caso text PRIMARY KEY,   -- l'etichetta del test
                          id   bigint);            -- vendite.resi.id

INSERT INTO t_reso
SELECT c.caso, r.reso_id
  FROM (VALUES ('bozza', 'DRAFT'), ('confermato', 'CONFERMATO'),
               ('annulla_contrasto', 'DRAFT'), ('annulla_marca', 'CONFERMATO')) c(caso, stato)
 CROSS JOIN LATERAL dbops.fn_pgtap_crea_reso('reso dal vocabolario, ' || c.caso,
                                             p_stato_codice_interno => c.stato) r;

INSERT INTO t_reso
SELECT 'pieno', r.reso_id
  FROM dbops.fn_pgtap_crea_reso('reso dal vocabolario, pieno',
                                (SELECT id FROM t_ddt WHERE caso = 'tetto'), 3) r;

CREATE FUNCTION pg_temp.d(p_caso text)   -- text: l'etichetta del test
RETURNS vendite.ddt.id%TYPE LANGUAGE sql STABLE AS $$
    SELECT id FROM t_ddt WHERE caso = p_caso
$$;

CREATE FUNCTION pg_temp.r(p_caso text)   -- text: l'etichetta del test
RETURNS vendite.resi.id%TYPE LANGUAGE sql STABLE AS $$
    SELECT id FROM t_reso WHERE caso = p_caso
$$;

CREATE FUNCTION pg_temp.cap_ddt(p_caso text, p_chiave text)   -- text: etichetta e chiave del blob
RETURNS text LANGUAGE sql STABLE AS $$                        -- text: un valore del blob jsonb
    SELECT script.fn_available_actions_ddt(pg_temp.d(p_caso)) ->> p_chiave
$$;

CREATE FUNCTION pg_temp.cap(p_caso text, p_chiave text)   -- text: etichetta e chiave del blob
RETURNS text LANGUAGE sql STABLE AS $$                    -- text: un valore del blob jsonb
    SELECT script.fn_available_actions_reso(pg_temp.r(p_caso)) ->> p_chiave
$$;

CREATE FUNCTION pg_temp.stato(p_caso text)   -- text: l'etichetta del test
RETURNS config.stati_doc_reso.codice_interno%TYPE LANGUAGE sql STABLE AS $$
    SELECT s.codice_interno FROM vendite.resi r
      JOIN config.stati_doc_reso s ON s.id = r.stato_doc_reso_id
     WHERE r.id = pg_temp.r(p_caso)
$$;

-- Un verbo sul reso del caso: rende cio' che l'ha rifiutato (NULL se passa).
CREATE FUNCTION pg_temp.verbo(p_verbo text, p_caso text)   -- text: il nome del verbo, l'etichetta
RETURNS text LANGUAGE sql AS $$                            -- text: un codice d'errore, nessuna colonna
    SELECT dbops.fn_pgtap_codice_errore(format('SELECT * FROM %s(%s)', p_verbo, pg_temp.r(p_caso)))
$$;

-- Un reso nuovo, in bozza, sulla bolla del caso: rende cio' che l'ha rifiutato.
CREATE FUNCTION pg_temp.nuovo_reso(p_caso text, p_quantita vendite.resi_righe.quantita%TYPE)
RETURNS text LANGUAGE sql AS $$   -- text: un codice d'errore, nessuna colonna
    SELECT dbops.fn_pgtap_codice_errore(format(
        'SELECT * FROM dbops.fn_pgtap_crea_reso(%L, %s, %s, p_stato_codice_interno => %L)',
        'reso dal vocabolario, nuovo', pg_temp.d(p_caso), p_quantita, 'DRAFT'))
$$;

-- ============================================================
-- 1-7) I contrasti, col vocabolario del seed
-- ============================================================
SELECT is(
    concat_ws(' ', pg_temp.cap_ddt('consegnata', 'can_genera_reso'),
                   pg_temp.cap_ddt('emessa', 'can_genera_reso'),
                   pg_temp.cap_ddt('emessa', 'can_genera_reso_reason'),
                   pg_temp.cap_ddt('emessa', 'can_genera_reso_reason_key')),
    'true false DDT_NON_CONSEGNATO vendite.ddt.genera_reso_reason.non_consegnato',
    '1. contrasto: can_genera_reso vero sulla bolla consegnata, falso sull''emessa col suo motivo'
);

SELECT is(
    pg_temp.nuovo_reso('emessa', 1),
    'E_RESO_DDT_NON_CONSEGNATO',
    '2. contrasto: il reso dall''emessa si rifiuta, e la capability lo diceva'
);

SELECT is(
    concat_ws(' ', pg_temp.cap('bozza', 'can_edit_righe'), pg_temp.cap('confermato', 'can_edit_righe'),
                   pg_temp.cap('bozza', 'can_riconsegna'), pg_temp.cap('confermato', 'can_riconsegna')),
    'true false false true',
    '3. contrasto: can_edit_righe vero in bozza, can_riconsegna vero nel confermato'
);

SELECT is(
    concat_ws(' ', pg_temp.verbo('vendite.fn_genera_ddt_riconsegna', 'bozza'),
                   pg_temp.verbo('vendite.fn_chiudi_riconsegna_reso', 'bozza'),
                   pg_temp.verbo('vendite.fn_riapri_riconsegna_reso', 'bozza')),
    'E_RESO_NON_CONFERMATO E_RESO_NON_CONFERMATO E_RESO_NON_CONFERMATO',
    '4. contrasto: i tre verbi della riconsegna rifiutano la bozza'
);

-- ⚠️ L'annullo in un'istruzione sua: pg_temp.stato e' STABLE, e nella stessa
--   istruzione vedrebbe il reso com'era all'inizio.
CREATE TEMP TABLE t_annullo AS
SELECT COALESCE(pg_temp.verbo('vendite.fn_annulla_reso', 'annulla_contrasto'), 'passa') AS esito;

SELECT is(
    concat_ws('|', (SELECT esito FROM t_annullo), pg_temp.stato('annulla_contrasto')::text),
    'passa|ANNULLATO',
    '5. contrasto: l''annullo porta la bozza nello stato di annullo, ANNULLATO'
);

SELECT is(
    pg_temp.verbo('vendite.fn_conferma_reso', 'annulla_contrasto'),
    'E_RESO_STATO_NON_CONFERMABILE',
    '6. contrasto: la conferma dell''annullato si rifiuta, la matrice non ha il passaggio'
);

SELECT is(
    pg_temp.nuovo_reso('tetto', 3),
    'E_RESO_QTA_SUPERA_CONSEGNATO',
    '7. contrasto: tre pezzi resi su cinque, altri tre sono oltre il consegnato'
);

-- ============================================================
-- 8-9) La forma — presidio sulla FORMA, dichiarato tale
-- ============================================================
-- ⚠️ Prova che i codici non sono scritti nei corpi (commenti tolti), non che
--   il comportamento sia giusto.
SELECT is(
    ARRAY(
        SELECT x.oggetto
          FROM (SELECT n.nspname || '.' || p.proname AS oggetto,
                       regexp_replace(pg_get_functiondef(p.oid), '--[^\n]*', '', 'g') AS testo
                  FROM pg_proc p
                  JOIN pg_namespace n ON n.oid = p.pronamespace
                 WHERE p.oid IN ('script.fn_available_actions_reso(bigint)'::regprocedure,
                                 'script.fn_check_reso_merce(vendite.resi)'::regprocedure,
                                 'vendite.fn_conferma_reso(bigint)'::regprocedure,
                                 'vendite.fn_annulla_reso(bigint)'::regprocedure,
                                 'vendite.fn_genera_ddt_riconsegna(bigint,jsonb,date)'::regprocedure,
                                 'vendite.fn_chiudi_riconsegna_reso(bigint,jsonb,character varying)'::regprocedure,
                                 'vendite.fn_riapri_riconsegna_reso(bigint,jsonb)'::regprocedure,
                                 'vendite.trgfn_resi_righe_guard_quantita()'::regprocedure)) x
         WHERE x.testo ~ '''(DRAFT|CONFERMATO|ANNULLATO)'''
         ORDER BY 1),
    ARRAY[]::text[],
    '8. forma: capability, check, verbi e guard del reso non nominano DRAFT, CONFERMATO, ANNULLATO'
);

SELECT ok(
    regexp_replace(pg_get_functiondef('vendite.trgfn_resi_guard_ddt_consegnato()'::regprocedure),
                   '--[^\n]*', '', 'g') !~ '''(CONSEGNATO|TRASF_OUT)''',
    '9. forma: il trigger del reso dalla bolla non riscrive la regola della check (nessun CONSEGNATO, TRASF_OUT)'
);

-- ============================================================
-- 10) ⭐ La marca spostata: iniziale su CONFERMATO
-- ============================================================
UPDATE config.stati_doc_reso SET iniziale = false WHERE codice_interno = 'DRAFT';
UPDATE config.stati_doc_reso SET iniziale = true  WHERE codice_interno = 'CONFERMATO';

SELECT is(
    concat_ws(' ', pg_temp.cap('bozza', 'can_edit_righe'), pg_temp.cap('confermato', 'can_edit_righe')),
    'false true',
    '10. con iniziale su CONFERMATO, can_edit_righe e'' falso in bozza e vero nel confermato'
);

UPDATE config.stati_doc_reso SET iniziale = false WHERE codice_interno = 'CONFERMATO';
UPDATE config.stati_doc_reso SET iniziale = true  WHERE codice_interno = 'DRAFT';

-- ============================================================
-- 11-12) ⭐ La marca spostata: emissione su DRAFT
-- ============================================================
UPDATE config.stati_doc_reso SET emissione = false WHERE codice_interno = 'CONFERMATO';
UPDATE config.stati_doc_reso SET emissione = true  WHERE codice_interno = 'DRAFT';

SELECT is(
    concat_ws(' ', pg_temp.cap('bozza', 'can_riconsegna'), pg_temp.cap('confermato', 'can_riconsegna')),
    'true false',
    '11. con emissione su DRAFT, can_riconsegna e'' vero in bozza e falso nel confermato'
);

SELECT is(
    pg_temp.verbo('vendite.fn_genera_ddt_riconsegna', 'confermato'),
    'E_RESO_NON_CONFERMATO',
    '12. ... e la ri-spedizione del confermato si rifiuta: capability e verbo rispondono uguale'
);

UPDATE config.stati_doc_reso SET emissione = false WHERE codice_interno = 'DRAFT';
UPDATE config.stati_doc_reso SET emissione = true  WHERE codice_interno = 'CONFERMATO';

-- ============================================================
-- 13-14) ⭐ La marca spostata: is_abortito
-- ============================================================
UPDATE config.stati_doc_reso SET is_abortito = false WHERE codice_interno = 'ANNULLATO';
UPDATE config.stati_doc_reso SET is_abortito = true  WHERE codice_interno = 'DRAFT';

SELECT is(
    pg_temp.verbo('vendite.fn_annulla_reso', 'annulla_marca'),
    'E_RESO_STATO_NON_ANNULLABILE',
    '13. con is_abortito su DRAFT, l''annullo del confermato va verso DRAFT, che la matrice non ha'
);

UPDATE config.stati_doc_reso SET is_abortito = false WHERE codice_interno = 'DRAFT';
UPDATE config.stati_doc_reso SET is_abortito = true  WHERE codice_interno = 'CONFERMATO';

SELECT is(
    COALESCE(pg_temp.nuovo_reso('tetto', 3), 'passa'),
    'passa',
    '14. con is_abortito su CONFERMATO, il reso confermato non conta piu'' nel tetto: tre pezzi passano'
);

UPDATE config.stati_doc_reso SET is_abortito = false WHERE codice_interno = 'CONFERMATO';
UPDATE config.stati_doc_reso SET is_abortito = true  WHERE codice_interno = 'ANNULLATO';

SELECT * FROM finish();

ROLLBACK;
