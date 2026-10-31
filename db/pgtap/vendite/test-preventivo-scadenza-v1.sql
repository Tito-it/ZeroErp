-- ------------------------------------------------------------
-- SPDX-License-Identifier: GPL-3.0-or-later
-- pgTAP test per Zero ERP
--
-- Test: la scadenza dei preventivi (EMESSO -> SCADUTO)
--   La colonna scadenza del vocabolario e il suo lettore (20261031-60, -61),
--   la check dell'accettazione (-62) letta dal guard di transizione (-63) e
--   dalla capability (-64), la revisione da SCADUTO (-65), il verbo di
--   chiusura del job delle scadenze (-66) e le sue righe nei due registri del
--   processo (CSV di 80_data). Dal 2026-10-31 (-67, E-4) anche l'emissione
--   con la validita' gia' finita, rifiutata da fn_check_preventivo_emettibile.
--   Brief: brief-db-scadenza-preventivi §8 (E-1 (a), E-2, E-3 (ii), E-4 di Tid,
--   2026-10-31).
--
-- ⭐ Il tempo che passa, in una transazione: con E-4 un preventivo EMESSO con
--   la validita' finita non si puo' piu' emettere cosi', ci si arriva solo
--   perche' il tempo passa. Il test lo emette nel fuso piu' a ovest
--   (Etc/GMT+12, UTC-12) con validita_al = oggi, poi sposta il fuso
--   dell'azienda (SYSTEM_FUSO_ORARIO, come test-data-documento-v1) al piu' a
--   est (Pacific/Kiritimati, UTC+14): fra i due ci sono 26 ore, quindi la data
--   operativa e' sempre almeno il giorno dopo, e la validita' e' finita «ieri».
--
-- Semantica attesa (il contratto, non l'implementazione):
--   - validita_al e' l'ultimo giorno valido: scade dal giorno dopo; NULL non
--     scade mai;
--   - un preventivo EMESSO con la validita' finita non si accetta, anche prima
--     che il job lo porti a SCADUTO (E_PREV_VALIDITA_SCADUTA), e «Accetta» e'
--     spento col motivo; il giorno di validita_al si accetta;
--   - il verbo di chiusura porta a SCADUTO solo gli EMESSI con la validita'
--     finita, e una seconda corsa non cambia niente;
--   - da SCADUTO si crea una revisione, in bozza; da ACCETTATO no;
--   - un preventivo con la validita' gia' finita non si emette
--     (E_PREV_EMISSIONE_VALIDITA_SCADUTA, col campo validita_al), e «Emetti»
--     e' spento col motivo; corretta la data, si emette.
--
-- Elenco test (plan 19):
--   1) la colonna scadenza: il lettore rende SCADUTO per il preventivo, NULL per l'ordine
--   2) il registro delle chiusure ha il preventivo: DOMINIO, EMESSO -> SCADUTO, col verbo
--   3) il processo chiusura_scadenze_daily dichiara il preventivo come bersaglio
--   4) la check: validita' di ieri -> E_PREV_VALIDITA_SCADUTA per primo
--   5) la check: validita' di oggi e NULL -> nessun motivo di validita'
--   6) la capability: «Accetta» spento col motivo VALIDITA_SCADUTA sul preventivo di ieri
--   7) la capability: «Accetta» acceso sul preventivo di oggi
--   8) il guard: l'accettazione del preventivo di ieri e' rifiutata
--   9) il guard: il preventivo di oggi si accetta
--  10) il verbo: porta a SCADUTO il preventivo di ieri
--  11) il verbo: lascia EMESSO il preventivo senza validita'
--  12) il verbo: una seconda corsa non tocca i preventivi del test
--  13) la capability su SCADUTO: «Crea revisione» proposto e acceso
--  14) la revisione da SCADUTO: rev N+1 in bozza, la rev N resta SCADUTO
--  15) la revisione da ACCETTATO resta rifiutata
--  16) E-4, la check dell'emissione: validita' di ieri -> E_PREV_EMISSIONE_VALIDITA_SCADUTA, campo validita_al
--  17) E-4, la capability: «Emetti» spento col motivo VALIDITA_SCADUTA
--  18) E-4, il guard: l'emissione con la validita' finita e' rifiutata
--  19) E-4: corretta la data a oggi, il preventivo si emette
-- ------------------------------------------------------------

BEGIN;

-- ⛔ IL FUSO A OVEST VIENE PRIMA DEL CONTESTO. Su un DB senza un operatore
--   pronto (lo scratch, la CI) il contesto lo COSTRUISCE, e la sua veste nasce
--   con valido_dal = la data operativa di quel momento. Se nascesse nel fuso di
--   casa, il passaggio a ovest porterebbe «oggi» al giorno prima della sua
--   nascita: veste non utilizzabile, perimetro vuoto, e il builder morirebbe
--   su «riga scritta ma non visibile» (il billing account sotto RLS). E' la
--   regola giusta della veste, non un difetto: l'operatore nasce nel giorno
--   piu' vecchio del test. Su dbdev si riusa un operatore gia' esistente, e
--   l'ordine sbagliato passava (rosso solo sullo scratch, 2026-11-01).
UPDATE config.parameters SET default_value = 'Etc/GMT+12' WHERE code = 'SYSTEM_FUSO_ORARIO';

-- Contesto applicativo: il test gira come l'applicazione (ruolo OPERATORE +
-- RLS attiva). Il verbo di chiusura lavora nel perimetro di questo utente.
DO $ctx$ BEGIN PERFORM script.fn_pgtap_set_contesto_operatore(); END $ctx$;

-- ⚠️ Vincoli DIFFERITI: senza questa riga il test smetterebbe di verificarli
--   (brief-db-pgtap-runner-rls-baseline §19).
SET CONSTRAINTS ALL IMMEDIATE;

SELECT plan(19);

-- ============================================================
-- Fixture: preventivi in bozza con la validita' che e' il caso, emessi con una
-- riga dal builder. In bozza la validita' si scrive; fuori bozza e' ferma.
--   - nel fuso a ovest: 'ieri' (validita_al = oggi, che diventa ieri quando
--     il fuso passa a est) e 'senza' (NULL);
--   - nel fuso a est: 'oggi' (validita_al = oggi) e 'bozza', che resta in
--     bozza con validita_al = ieri (il caso di E-4).
-- ============================================================
CREATE TEMP TABLE t_prev (caso text PRIMARY KEY, id bigint);

CREATE OR REPLACE FUNCTION pg_temp.mk(p_caso text, p_validita_al date, p_stato text) RETURNS void AS $$
DECLARE
    v_id bigint;
BEGIN
    SELECT b.preventivo_id INTO v_id
      FROM dbops.fn_pgtap_crea_preventivo('scadenza ' || p_caso, 'DRAFT') b;
    UPDATE vendite.preventivi
       SET validita_dal = script.fn_data_operativa() - 10,
           validita_al  = p_validita_al
     WHERE id = v_id;
    PERFORM dbops.fn_pgtap_crea_preventivo_con_righe('scadenza ' || p_caso, p_stato,
                                                     p_preventivo_id => v_id);
    INSERT INTO t_prev VALUES (p_caso, v_id);
END $$ LANGUAGE plpgsql;

-- (il fuso e' gia' a ovest: impostato prima del contesto, in testa)
DO $mk$ BEGIN PERFORM pg_temp.mk('ieri',  script.fn_data_operativa(), 'EMESSO'); END $mk$;
DO $mk$ BEGIN PERFORM pg_temp.mk('senza', NULL, 'EMESSO'); END $mk$;

-- Il tempo passa: almeno un giorno avanti.
UPDATE config.parameters SET default_value = 'Pacific/Kiritimati' WHERE code = 'SYSTEM_FUSO_ORARIO';
DO $mk$ BEGIN PERFORM pg_temp.mk('oggi',  script.fn_data_operativa(), 'EMESSO'); END $mk$;
DO $mk$ BEGIN PERFORM pg_temp.mk('bozza', script.fn_data_operativa() - 1, 'DRAFT'); END $mk$;

CREATE OR REPLACE FUNCTION pg_temp.stato(p_caso text) RETURNS text AS $$
    SELECT s.codice_interno::text
      FROM vendite.preventivi p
      JOIN config.stati_doc_preventivi s ON s.id = p.stato_doc_preventivo_id
     WHERE p.id = (SELECT id FROM t_prev WHERE caso = p_caso)
$$ LANGUAGE sql STABLE;

CREATE OR REPLACE FUNCTION pg_temp.azione(p_caso text, p_key text) RETURNS jsonb AS $$
    SELECT a
      FROM jsonb_array_elements(
               script.fn_available_actions_preventivo((SELECT id FROM t_prev WHERE caso = p_caso))
               -> 'available_actions') a
     WHERE a ->> 'key' = p_key
$$ LANGUAGE sql STABLE;

-- 1) La colonna e il lettore
SELECT is(
    ARRAY[(SELECT codice_interno::text FROM config.stati_doc_preventivi
            WHERE id = script.fn_stato_scadenza_id('vendite.preventivi'::regclass)),
          COALESCE(script.fn_stato_scadenza_id('vendite.ordini'::regclass)::text, 'NULL')],
    ARRAY['SCADUTO', 'NULL'],
    'la colonna scadenza: il lettore rende SCADUTO per il preventivo, NULL per l''ordine (vocabolario senza la colonna)'
);

-- 2) Il registro delle chiusure
SELECT is(
    (SELECT format('%s|%s|%s|%s|%s|%s', col_stato, col_valido_al, stato_attivo_codice,
                   stato_chiuso_codice, classe, verbo_chiusura)
       FROM dbops.automazione_chiusura_scadenze
      WHERE schema_tabella = 'vendite' AND nome_tabella = 'preventivi' AND attivo),
    'stato_doc_preventivo_id|validita_al|EMESSO|SCADUTO|DOMINIO|vendite.fn_chiudi_preventivi_scaduti',
    'il registro delle chiusure ha il preventivo: DOMINIO, EMESSO -> SCADUTO, col verbo di chiusura'
);

-- 3) Il bersaglio del processo
SELECT is(
    (SELECT format('%s|%s', b.emittente_via, b.emittente_colonna)
       FROM dbops.processi_bersagli b
       JOIN dbops.processi p ON p.id = b.processo_id
      WHERE p.codice = 'chiusura_scadenze_daily'
        AND b.schema_tabella = 'vendite' AND b.nome_tabella = 'preventivi'),
    'fiscale|emittente_fiscale_id',
    'il processo chiusura_scadenze_daily dichiara il preventivo come bersaglio, emittente dalla testata'
);

-- 4) La check, validita' di ieri
SELECT is(
    script.fn_check_preventivo_accettabile((SELECT id FROM t_prev WHERE caso = 'ieri'),
                                           script.fn_data_operativa() - 1) -> 0 ->> 'codice',
    'E_PREV_VALIDITA_SCADUTA',
    'la check: con la validita'' finita ieri il primo motivo e'' E_PREV_VALIDITA_SCADUTA'
);

-- 5) La check, validita' di oggi e senza validita': il parametro decide, non la riga
SELECT is(
    (SELECT count(*)::int
       FROM jsonb_array_elements(
                script.fn_check_preventivo_accettabile((SELECT id FROM t_prev WHERE caso = 'oggi'),
                                                       script.fn_data_operativa())
             || script.fn_check_preventivo_accettabile((SELECT id FROM t_prev WHERE caso = 'oggi'),
                                                       NULL)) m
      WHERE m ->> 'codice' = 'E_PREV_VALIDITA_SCADUTA'),
    0,
    'la check: l''ultimo giorno valido e la validita'' NULL non danno il motivo di validita'''
);

-- 6) La capability, preventivo di ieri
SELECT is(
    (SELECT format('%s|%s', a ->> 'enabled', a ->> 'reason') FROM pg_temp.azione('ieri', 'accetta') a),
    'false|VALIDITA_SCADUTA',
    'la capability: «Accetta» spento col motivo VALIDITA_SCADUTA sul preventivo con la validita'' finita'
);

-- 7) La capability, preventivo di oggi
SELECT is(
    (SELECT a ->> 'enabled' FROM pg_temp.azione('oggi', 'accetta') a),
    'true',
    'la capability: «Accetta» acceso sul preventivo che scade oggi'
);

-- 8) Il guard: ancora EMESSO, ma la validita' e' finita
SELECT throws_like(
    format('SELECT * FROM vendite.fn_cambia_stato_preventivo(%s, ''ACCETTATO'')',
           (SELECT id FROM t_prev WHERE caso = 'ieri')),
    '%non si può accettare: la sua validità è finita il%',
    'il guard: l''accettazione di un preventivo EMESSO con la validita'' finita e'' rifiutata (E_PREV_VALIDITA_SCADUTA)'
);

-- 9) Il guard: il giorno di validita_al si accetta
SELECT lives_ok(
    format('SELECT * FROM vendite.fn_cambia_stato_preventivo(%s, ''ACCETTATO'')',
           (SELECT id FROM t_prev WHERE caso = 'oggi')),
    'il guard: il preventivo che scade oggi si accetta'
);

-- 10-11) Il verbo di chiusura
CREATE TEMP TABLE t_corsa AS SELECT vendite.fn_chiudi_preventivi_scaduti() AS n;

SELECT is(
    pg_temp.stato('ieri'),
    'SCADUTO',
    'il verbo: il preventivo EMESSO con la validita'' finita passa a SCADUTO'
);

SELECT is(
    ARRAY[pg_temp.stato('senza'), pg_temp.stato('oggi')],
    ARRAY['EMESSO', 'ACCETTATO'],
    'il verbo: il preventivo senza validita'' resta EMESSO, quello accettato resta ACCETTATO'
);

-- 12) Seconda corsa: niente da fare sui preventivi del test
DO $corsa$ BEGIN PERFORM vendite.fn_chiudi_preventivi_scaduti(); END $corsa$;
SELECT is(
    ARRAY[pg_temp.stato('ieri'), pg_temp.stato('senza'), pg_temp.stato('oggi')],
    ARRAY['SCADUTO', 'EMESSO', 'ACCETTATO'],
    'il verbo: una seconda corsa non cambia i preventivi del test'
);

-- 13) La capability su SCADUTO
SELECT is(
    (SELECT a ->> 'enabled' FROM pg_temp.azione('ieri', 'crea_revisione') a),
    'true',
    'la capability su SCADUTO: «Crea revisione» proposto e acceso'
);

-- 14) La revisione da SCADUTO
CREATE TEMP TABLE t_rev AS
SELECT * FROM vendite.fn_crea_revisione_preventivo((SELECT id FROM t_prev WHERE caso = 'ieri'), 'pgtap');

SELECT is(
    -- ⚠️ ::text esplicito: format() di un boolean rende `t`, non `true`.
    (SELECT format('%s|%s', (p.stato_doc_preventivo_id = script.fn_doc_stato_iniziale_id('vendite.preventivi'::regclass))::text,
                   pg_temp.stato('ieri'))
       FROM t_rev r JOIN vendite.preventivi p ON p.id = r.nuovo_preventivo_id),
    'true|SCADUTO',
    'la revisione da SCADUTO: la rev N+1 nasce nello stato iniziale, la rev N resta SCADUTO'
);

-- 15) La revisione da ACCETTATO resta esclusa
SELECT throws_like(
    format('SELECT * FROM vendite.fn_crea_revisione_preventivo(%s, ''pgtap'')',
           (SELECT id FROM t_prev WHERE caso = 'oggi')),
    '%Ammessa solo da un preventivo emesso o scaduto%',
    'la revisione da ACCETTATO resta rifiutata (E_PREV_REVISIONE_STATO_NON_AMMESSO)'
);

-- 16) E-4: la check dell'emissione sul preventivo in bozza con la validita' di ieri
SELECT is(
    (SELECT format('%s|%s', m ->> 'codice', m -> 'dettaglio' ->> 'campo')
       FROM jsonb_array_elements(
                script.fn_check_preventivo_emettibile((SELECT id FROM t_prev WHERE caso = 'bozza'))) m
      WHERE m ->> 'codice' = 'E_PREV_EMISSIONE_VALIDITA_SCADUTA'),
    'E_PREV_EMISSIONE_VALIDITA_SCADUTA|validita_al',
    'E-4, la check dell''emissione: con la validita'' finita ieri il motivo E_PREV_EMISSIONE_VALIDITA_SCADUTA, col campo validita_al'
);

-- 17) E-4: la capability
SELECT is(
    (SELECT format('%s|%s', a ->> 'enabled', a ->> 'reason') FROM pg_temp.azione('bozza', 'emetti') a),
    'false|VALIDITA_SCADUTA',
    'E-4, la capability: «Emetti» spento col motivo VALIDITA_SCADUTA'
);

-- 18) E-4: il guard
SELECT throws_like(
    format('SELECT * FROM vendite.fn_cambia_stato_preventivo(%s, ''EMESSO'')',
           (SELECT id FROM t_prev WHERE caso = 'bozza')),
    '%non si può emettere: la sua validità è finita il%',
    'E-4, il guard: l''emissione con la validita'' finita e'' rifiutata (E_PREV_EMISSIONE_VALIDITA_SCADUTA)'
);

-- 19) E-4: corretta la data (in bozza si puo'), il preventivo si emette
UPDATE vendite.preventivi SET validita_al = script.fn_data_operativa()
 WHERE id = (SELECT id FROM t_prev WHERE caso = 'bozza');
SELECT lives_ok(
    format('SELECT * FROM vendite.fn_cambia_stato_preventivo(%s, ''EMESSO'')',
           (SELECT id FROM t_prev WHERE caso = 'bozza')),
    'E-4: corretta «Valido al» a oggi, il preventivo si emette'
);

SELECT * FROM finish();
ROLLBACK;
