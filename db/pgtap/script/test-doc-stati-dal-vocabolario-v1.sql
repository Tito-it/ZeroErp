-- ------------------------------------------------------------
-- SPDX-License-Identifier: GPL-3.0-or-later
-- pgTAP test per Zero ERP
--
-- Test: gli stati con un significato si leggono dal vocabolario
--   Il lettore comune script.fn_stato_per_colonna_id (20261031-06), i lettori
--   con il nome (emissione e annullo riscritti, 20261031-07/-08; cessazione e
--   accettazione nuovi, 20261031-09/-10), le colonne cessazione e accettazione
--   coi loro vincoli (20261031-05), e i consumatori riscritti nel giro
--   (20261031-11 … -21).
--   Brief: brief-modello-documento-vendita §17 (ok di Tid 2026-10-31).
--
-- Semantica attesa (il contratto, non l'implementazione):
--   - ogni lettore rende l'id dello stato che il vocabolario della testata
--     marca con la sua colonna; NULL dove il vocabolario non ha la colonna
--     (il documento non ha quello stato);
--   - al massimo uno stato marcato per vocabolario, ed e' attivo;
--   - il lettore comune rifiuta una testata fuori mappa e una colonna che non
--     e' boolean (il chiamante e' rotto); una colonna che non c'e' e' NULL;
--   - la marca spostata su un altro stato sposta la risposta: il lettore non
--     ricorda un codice;
--   - R-1: l'offerta da revisionare che non c'e' e' E_OFFERTA_NON_TROVATA.
--
-- Elenco test (plan 13):
--   1) i cinque lettori esistono: STABLE, SECURITY INVOKER
--   2) emissione e annullo: per le otto testate, lo stato marcato dal vocabolario (la riscrittura non cambia le risposte)
--   3) cessazione: il contratto, lo stato marcato; le altre sette testate NULL
--   4) accettazione: preventivo e offerta, lo stato marcato; le altre sei testate NULL
--   5) la marca spostata su un altro stato sposta la risposta
--   6) un secondo stato di cessazione: rifiutato (indice unico parziale)
--   7) uno stato di accettazione spento: rifiutato (CHECK)
--   8) lettore comune: colonna che non c'e' -> NULL
--   9) lettore comune: colonna non boolean -> chiamata non valida
--  10) testata fuori mappa -> chiamata non valida, che nomina il lettore chiamato (non il comune)
--  11) R-1: fn_crea_revisione_offerta su un'offerta che non c'e' -> E_OFFERTA_NON_TROVATA
--  12) presidio sulla forma: i consumatori riscritti non nominano piu' 'CESSATO', 'ACCETTATO', 'ACCETTATA'
--  13) presidio sulla forma: le capability e la revisione dell'offerta non nominano piu' 'EMESSA'/'EMESSO'
--
-- ⚠️ I test 12-13 leggono il corpo, e sono dichiarati presidi sulla forma: il
--   comportamento lo provano i test 2-5 sui lettori e i pgTAP dei documenti
--   (al modello) sui verbi. Restano fuori dall'elenco, per scelta del giro, i
--   guard di transizione (il letterale e' la condizione del passaggio) e
--   vendite.fn_preventivo_proietta_stato_smistamento (ACCETTATO <-> EVASO).
-- ------------------------------------------------------------

BEGIN;

DO $ctx$ BEGIN PERFORM script.fn_pgtap_set_contesto_operatore(); END $ctx$;

SET CONSTRAINTS ALL IMMEDIATE;

SELECT plan(13);

-- 1) Gli oggetti e la loro forma
SELECT is(
    (SELECT string_agg(p.proname || ':' || p.provolatile::text || ':' || p.prosecdef::text, ' ' ORDER BY p.proname)
       FROM pg_proc p JOIN pg_namespace n ON n.oid = p.pronamespace
      WHERE n.nspname = 'script'
        AND p.proname IN ('fn_stato_per_colonna_id', 'fn_stato_emissione_id', 'fn_stato_abortito_id',
                          'fn_stato_cessazione_id', 'fn_stato_accettazione_id')),
    'fn_stato_abortito_id:s:false fn_stato_accettazione_id:s:false fn_stato_cessazione_id:s:false '
    'fn_stato_emissione_id:s:false fn_stato_per_colonna_id:s:false',
    'i cinque lettori esistono: STABLE, SECURITY INVOKER'
);

-- Le otto testate di vendita, col loro vocabolario dalla mappa.
CREATE TEMP TABLE t_testate AS
SELECT t.testata, m.vocabolario
  FROM unnest(ARRAY['vendite.preventivi', 'vendite.offerte_commerciali', 'vendite.contratti',
                    'vendite.ordini', 'vendite.ddt', 'vendite.resi', 'vendite.commesse',
                    'vendite.fatture']::regclass[]) AS t(testata)
 CROSS JOIN LATERAL script.fn_doc_stato_modello(t.testata) m;

-- L'atteso si legge dal vocabolario, colonna per colonna: lo stato marcato,
-- o NULL se la colonna non c'e'. Il conteggio delle testate evita il verde
-- per sottrazione.
CREATE TEMP TABLE t_giro (colonna text, testata regclass, atteso bigint, letto bigint);

DO $giro$
DECLARE
    v_t   record;
    v_col text;
    v_att bigint;
BEGIN
    FOR v_t IN SELECT * FROM t_testate LOOP
        FOREACH v_col IN ARRAY ARRAY['emissione', 'is_abortito', 'cessazione', 'accettazione'] LOOP
            v_att := NULL;
            IF EXISTS (SELECT 1 FROM pg_attribute a
                        WHERE a.attrelid = v_t.vocabolario AND a.attname = v_col
                          AND a.attnum > 0 AND NOT a.attisdropped) THEN
                EXECUTE format('SELECT s.id FROM %s s WHERE s.%I', v_t.vocabolario, v_col) INTO v_att;
            END IF;
            INSERT INTO t_giro VALUES (
                v_col, v_t.testata, v_att,
                CASE v_col
                    WHEN 'emissione'    THEN script.fn_stato_emissione_id(v_t.testata)
                    WHEN 'is_abortito'  THEN script.fn_stato_abortito_id(v_t.testata)
                    WHEN 'cessazione'   THEN script.fn_stato_cessazione_id(v_t.testata)
                    WHEN 'accettazione' THEN script.fn_stato_accettazione_id(v_t.testata)
                END);
        END LOOP;
    END LOOP;
END
$giro$;

-- 2) Emissione e annullo: le risposte di sempre, per le otto testate
SELECT is(
    (SELECT count(*)::integer FROM t_giro
      WHERE colonna IN ('emissione', 'is_abortito') AND letto IS NOT DISTINCT FROM atteso),
    16,
    'emissione e annullo, otto testate: lo stato marcato dal vocabolario (o NULL dove la colonna manca)'
);

-- 3) Cessazione: solo il contratto ce l'ha, ed e' lo stato marcato. Si
--    confrontano OID, mai regclass::text (dipende dal search_path).
SELECT is(
    (SELECT count(*)::integer FROM t_giro
      WHERE colonna = 'cessazione' AND letto IS NOT DISTINCT FROM atteso
        AND ((testata = 'vendite.contratti'::regclass) = (letto IS NOT NULL))),
    8,
    'cessazione: il contratto rende lo stato che il vocabolario marca, le altre sette testate NULL'
);

-- 4) Accettazione: preventivo e offerta, lo stato marcato; gli altri NULL
SELECT is(
    (SELECT count(*)::integer FROM t_giro
      WHERE colonna = 'accettazione' AND letto IS NOT DISTINCT FROM atteso
        AND ((testata IN ('vendite.preventivi'::regclass, 'vendite.offerte_commerciali'::regclass)) = (letto IS NOT NULL))),
    8,
    'accettazione: preventivo e offerta rendono lo stato marcato, le altre sei testate NULL'
);

-- 5) La marca spostata: il lettore segue il vocabolario, non un codice.
--    Uno stato nuovo, attivo, prende la marca d'accettazione dell'offerta.
SAVEPOINT s_sposta;
INSERT INTO config.stati_doc_offerte (id, codice_interno, codice, descrizione, attivo, ordine,
                                      fase, terminale, pdf_mode, pdf_allow_allegati)
VALUES (990731, 'PGTAP_ACCETTATA_ALTRA', 'PGTAP_ACCETTATA_ALTRA', 'pgTAP accettazione spostata', true, 990,
        'IN_CORSO', false, 'ARCHIVE', false);
UPDATE config.stati_doc_offerte SET accettazione = false WHERE accettazione;
UPDATE config.stati_doc_offerte SET accettazione = true WHERE id = 990731;
SELECT is(
    script.fn_stato_accettazione_id('vendite.offerte_commerciali'::regclass),
    990731::bigint,
    'la marca d''accettazione spostata su un altro stato: il lettore rende quello'
);
ROLLBACK TO SAVEPOINT s_sposta;

-- 6) Al massimo uno stato di cessazione
SAVEPOINT s_unico;
SELECT throws_ok(
    $$UPDATE config.stati_doc_contratti SET cessazione = true
       WHERE NOT cessazione AND attivo AND id = (SELECT min(id) FROM config.stati_doc_contratti
                                                  WHERE NOT cessazione AND attivo)$$,
    '23505',
    NULL,
    'un secondo stato di cessazione nel vocabolario: rifiutato (uq_stati_doc_contratti_cessazione)'
);
ROLLBACK TO SAVEPOINT s_unico;

-- 7) Lo stato di accettazione e' attivo
SAVEPOINT s_attivo;
INSERT INTO config.stati_doc_preventivi (id, codice_interno, codice, descrizione, attivo, ordine,
                                         fase, terminale, pdf_mode, pdf_allow_allegati)
VALUES (990732, 'PGTAP_ACC_SPENTO', 'PGTAP_ACC_SPENTO', 'pgTAP accettazione spenta', false, 991,
        'IN_CORSO', false, 'ARCHIVE', false);
UPDATE config.stati_doc_preventivi SET accettazione = false WHERE accettazione;
SELECT throws_ok(
    $$UPDATE config.stati_doc_preventivi SET accettazione = true WHERE id = 990732$$,
    '23514',
    NULL,
    'uno stato di accettazione spento: rifiutato (chk_stati_doc_preventivi_accettazione_attivo)'
);
ROLLBACK TO SAVEPOINT s_attivo;

-- 8-10) Il lettore comune: i suoi tre confini
SELECT ok(
    script.fn_stato_per_colonna_id('vendite.resi'::regclass, 'accettazione') IS NULL,
    'lettore comune: una colonna che il vocabolario non ha -> NULL (il documento non ha quello stato)'
);

SELECT throws_like(
    $$SELECT script.fn_stato_per_colonna_id('vendite.contratti'::regclass, 'codice_interno')$$,
    'Chiamata non valida a script.fn_stato_per_colonna_id%',
    'lettore comune: una colonna che non e'' boolean -> chiamata non valida'
);

SELECT throws_like(
    $$SELECT script.fn_stato_cessazione_id('config.sorgenti'::regclass)$$,
    'Chiamata non valida a script.fn_stato_cessazione_id%',
    'una tabella fuori dalla mappa -> chiamata non valida, col nome del lettore chiamato (non del comune)'
);

-- 11) R-1: l'offerta che non c'e'. Un id che nessuna sequenza raggiunge.
SELECT throws_like(
    $$SELECT vendite.fn_crea_revisione_offerta(9000000000000000000, NULL)$$,
    'Offerta 9000000000000000000 non trovata.%',
    'fn_crea_revisione_offerta: un''offerta che non c''e'' -> E_OFFERTA_NON_TROVATA (404), non E_PARAMETRO_INVALIDO'
);

-- 12-13) Presidi sulla forma (dichiarati in testa): i letterali ritirati.
SELECT is(
    (SELECT string_agg(n.nspname || '.' || p.proname, ', ' ORDER BY 1)
       FROM pg_proc p JOIN pg_namespace n ON n.oid = p.pronamespace
      WHERE (n.nspname, p.proname) IN (('vendite', 'fn_cessa_contratto'), ('vendite', 'fn_cessa_contratti_scaduti'),
                                       ('vendite', 'fn_contratti_addebiti_maturati'),
                                       ('vendite', 'fn_list_preventivi_da_pushare'),
                                       ('vendite', 'fn_push_preventivo_a_ordine'),
                                       ('vendite', 'fn_push_offerta_a_contratto'),
                                       ('vendite', 'fn_genera_ordine_da_offerta'),
                                       ('script', 'fn_available_actions_preventivo'),
                                       ('script', 'fn_available_actions_offerta'))
        AND regexp_replace(p.prosrc, '--[^\n]*', '', 'g') ~ '''(CESSATO|ACCETTATO|ACCETTATA)'''),
    NULL,
    'i consumatori riscritti non nominano piu'' ''CESSATO'', ''ACCETTATO'', ''ACCETTATA'' (fuori dai commenti)'
);

SELECT is(
    (SELECT string_agg(n.nspname || '.' || p.proname, ', ' ORDER BY 1)
       FROM pg_proc p JOIN pg_namespace n ON n.oid = p.pronamespace
      WHERE (n.nspname, p.proname) IN (('vendite', 'fn_crea_revisione_offerta'),
                                       ('script', 'fn_available_actions_preventivo'),
                                       ('script', 'fn_available_actions_offerta'))
        AND regexp_replace(p.prosrc, '--[^\n]*', '', 'g') ~ '''(EMESSA|EMESSO|ANNULLATO)'''),
    NULL,
    'la revisione dell''offerta e le due capability non nominano piu'' ''EMESSA'', ''EMESSO'', ''ANNULLATO'' (fuori dai commenti)'
);

SELECT * FROM finish();
ROLLBACK;
