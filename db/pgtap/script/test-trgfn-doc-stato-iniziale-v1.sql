-- ------------------------------------------------------------
-- SPDX-License-Identifier: GPL-3.0-or-later
-- pgTAP test per Zero ERP
--
-- Test: un documento nasce nel suo stato iniziale
--   BB script.trgfn_doc_stato_iniziale (20261024-10), lettore
--   script.fn_stato_iniziale_id (20261024-09), colonna `iniziale` dei
--   vocabolari (20261024-07), montaggio su vendite e acquisti (20261024-11/-12).
--   Brief: brief-modello-documento-vendita §4-bis/§4-ter (N-1 … N-3, P-1 … P-3
--   di Tid, 2026-10-24).
-- rev 2026-10-28 (brief-modello-documento-vendita §16, giro 12): la versione di
--   listino ha il suo vocabolario (config.stati_doc_listino_versioni) e la
--   nascita (20261028-10), fuori da P-3 finche' non aveva un vocabolario.
-- ⚠️ Attesa cambiata: test 3 e 4 (otto -> nove vocabolari), 5 (la versione di
--   listino nel perimetro atteso: non e' una sorgente DOCUMENTO) e 6 (dieci ->
--   undici testate).
--
-- Semantica attesa (il contratto, non l'implementazione):
--   - ogni vocabolario degli stati delle testate dichiara UNO stato iniziale,
--     attivo; l'indice unico parziale e il CHECK lo presidiano;
--   - ogni testata che ha una FK verso un vocabolario con la colonna
--     `iniziale` monta il BB, con quella colonna e quel vocabolario (il
--     montaggio si ricava dal catalogo, non da un elenco: una testata nuova
--     senza il trigger fa rosso qui);
--   - il trigger della nascita e' il PRIMO BEFORE INSERT della tabella;
--   - stato omesso: lo stato iniziale; stato iniziale: passa; altro stato:
--     E_DOC_STATO_INIZIALE_NON_VALIDO, con la frase che nomina documento e
--     stati come li legge una persona;
--   - montaggio sbagliato, vocabolario senza stato iniziale, lettore chiamato
--     male: E_SCRIPT_CHIAMATA_NON_VALIDA.
--
-- Elenco test (plan 18):
--   1) script.fn_stato_iniziale_id(regclass) esiste
--   2) script.trgfn_doc_stato_iniziale() esiste
--   3) i nove vocabolari hanno uno e un solo stato iniziale, attivo
--   4) i nove vocabolari hanno l'indice unico parziale e il CHECK
--   5) montaggio: ogni testata con FK verso un vocabolario con `iniziale`
--      monta il BB su quella colonna e quel vocabolario, e viceversa
--   6) montaggio: undici testate (otto di vendita, due d'acquisto, la versione di listino)
--   7) il trigger della nascita e' il primo BEFORE INSERT di ogni testata
--   8) il lettore rende lo stato iniziale dichiarato (ordini: DRAFT)
--   9) un ordine creato senza dire lo stato nasce DRAFT
--  10) una commessa creata senza dire lo stato (nessun DEFAULT) nasce BOZZA
--  11) una fattura creata senza dire lo stato nasce DRAFT (colonna NOT NULL)
--  12) stato iniziale esplicito: passa, e lo stato omesso prende l'iniziale
--  13) un preventivo che nasce EMESSO: rifiutato, con la frase dell'operatore
--  14) un ordine d'acquisto che nasce CONFERMATO: rifiutato (acquisti montato)
--  15) lettore con vocabolario NULL: chiamata non valida
--  16) lettore con una tabella senza la colonna iniziale: chiamata non valida
--  17) montaggio con un argomento solo: chiamata non valida
--  18) vocabolario che non dichiara lo stato iniziale: chiamata non valida
-- ------------------------------------------------------------

BEGIN;

DO $ctx$ BEGIN PERFORM script.fn_pgtap_set_contesto_operatore(); END $ctx$;

SET CONSTRAINTS ALL IMMEDIATE;

SELECT plan(18);

-- 1-2) Gli oggetti
SELECT has_function('script', 'fn_stato_iniziale_id', ARRAY['regclass'],
    'script.fn_stato_iniziale_id(regclass) esiste');
SELECT has_function('script', 'trgfn_doc_stato_iniziale', ARRAY[]::text[],
    'script.trgfn_doc_stato_iniziale() esiste');

-- I nove vocabolari delle testate.
CREATE TEMP TABLE t_vocabolari AS
SELECT v::regclass AS voc
  FROM unnest(ARRAY['config.stati_doc_preventivi', 'config.stati_doc_offerte',
                    'config.stati_doc_contratti',  'config.stati_doc_ordini',
                    'config.stati_doc_ddt',        'config.stati_doc_reso',
                    'config.stati_doc_fiscale',    'vendite.stati_commessa',
                    'config.stati_doc_listino_versioni']) AS v;

-- 3) Uno e un solo stato iniziale, attivo, per vocabolario
CREATE TEMP TABLE t_iniziali (voc regclass, n integer, attivi integer);
DO $$
DECLARE
    r record;
BEGIN
    FOR r IN SELECT voc FROM t_vocabolari LOOP
        EXECUTE format(
            'INSERT INTO t_iniziali SELECT %L::regclass, count(*), count(*) FILTER (WHERE s.attivo) FROM %s s WHERE s.iniziale',
            r.voc, r.voc);
    END LOOP;
END $$;

SELECT is(
    (SELECT count(*)::integer FROM t_iniziali WHERE n = 1 AND attivi = 1),
    9,
    'i nove vocabolari hanno uno e un solo stato iniziale, attivo'
);

-- 4) Il presidio dello schema: indice unico parziale e CHECK su tutti e otto
SELECT is(
    (SELECT count(*)::integer
       FROM t_vocabolari v
      WHERE EXISTS (SELECT 1 FROM pg_index i
                     WHERE i.indrelid = v.voc AND i.indisunique
                       AND pg_get_expr(i.indpred, i.indrelid) = 'iniziale')
        AND EXISTS (SELECT 1 FROM pg_constraint c
                     WHERE c.conrelid = v.voc AND c.contype = 'c'
                       -- forma stampata da PostgreSQL: CHECK (((NOT iniziale) OR attivo))
                       AND pg_get_constraintdef(c.oid) = 'CHECK (((NOT iniziale) OR attivo))')),
    9,
    'i nove vocabolari hanno l''indice unico parziale su iniziale e il CHECK «iniziale e'' attivo»'
);

-- Il montaggio atteso, dal catalogo: ogni tabella con una FK a colonna
-- singola verso un vocabolario che ha la colonna `iniziale`, ristretta alle
-- testate dei documenti (config.sorgenti, categoria DOCUMENTO) e alle testate
-- d'acquisto. ⚠️ Le righe dell'ordine hanno anch'esse lo stato: non sono
-- testate e restano fuori dal perimetro di N-2.
CREATE TEMP TABLE t_atteso AS
SELECT c.conrelid AS tab, a.attname::text AS col, c.confrelid AS voc
  FROM pg_constraint c
  JOIN pg_attribute a ON a.attrelid = c.conrelid AND a.attnum = c.conkey[1]
 WHERE c.contype = 'f'
   AND cardinality(c.conkey) = 1
   AND EXISTS (SELECT 1 FROM pg_attribute x
                WHERE x.attrelid = c.confrelid AND x.attname = 'iniziale' AND NOT x.attisdropped)
   AND (c.conrelid IN (SELECT s.target_table FROM config.sorgenti s
                        WHERE s.categoria = 'DOCUMENTO' AND s.target_table IS NOT NULL)
        OR c.conrelid IN ('acquisti.ordini'::regclass, 'acquisti.ddt'::regclass,
                          'vendite.listini_versioni'::regclass));

CREATE TEMP TABLE t_montato AS
SELECT g.tgrelid AS tab, g.tgname::text AS nome,
       (string_to_array(rtrim(encode(g.tgargs, 'escape'), E'\\000'), E'\\000'))[1] AS col,
       to_regclass((string_to_array(rtrim(encode(g.tgargs, 'escape'), E'\\000'), E'\\000'))[2]) AS voc
  FROM pg_trigger g
 WHERE g.tgfoid = 'script.trgfn_doc_stato_iniziale'::regproc
   AND NOT g.tgisinternal;

-- 5) Montaggio = catalogo, nei due versi
SELECT is(
    (SELECT count(*)::integer FROM (
        (SELECT tab, col, voc FROM t_atteso  EXCEPT SELECT tab, col, voc FROM t_montato)
        UNION ALL
        (SELECT tab, col, voc FROM t_montato EXCEPT SELECT tab, col, voc FROM t_atteso)) d),
    0,
    'ogni testata con un vocabolario degli stati monta il BB su quella colonna e quel vocabolario, e nessun altro montaggio'
);

-- 6) Undici testate: le otto di vendita, le due d'acquisto (P-3), la versione
--    di listino (giro 12)
SELECT is(
    (SELECT count(DISTINCT tab)::integer FROM t_montato),
    11,
    'il BB e'' montato su undici testate: otto di vendita, due d''acquisto, la versione di listino'
);

-- 7) Il primo BEFORE INSERT di ogni testata: chi legge lo stato lo trova gia'
--    deciso (ordine lessicografico dei nomi, linee-guida-trigger).
SELECT is(
    (SELECT count(*)::integer
       FROM t_montato m
      WHERE m.nome <> (SELECT min(g.tgname COLLATE "C")
                         FROM pg_trigger g
                        WHERE g.tgrelid = m.tab AND NOT g.tgisinternal
                          AND (g.tgtype & 1) = 1      -- ROW
                          AND (g.tgtype & 2) = 2      -- BEFORE
                          AND (g.tgtype & 4) = 4)),   -- INSERT
    0,
    'il trigger della nascita e'' il primo BEFORE INSERT di ogni testata'
);

-- 8) Il lettore
SELECT is(
    (SELECT s.codice_interno
       FROM config.stati_doc_ordini s
      WHERE s.id = script.fn_stato_iniziale_id('config.stati_doc_ordini'::regclass)),
    'DRAFT'::character varying,
    'script.fn_stato_iniziale_id rende lo stato iniziale dichiarato (ordini: DRAFT)'
);

-- 9) Stato omesso: un ordine dal builder (che non lo scrive) nasce DRAFT
CREATE TEMP TABLE t_ordine AS
SELECT * FROM dbops.fn_pgtap_crea_ordine('nascita ordine');

SELECT is(
    (SELECT s.codice_interno
       FROM vendite.ordini o
       JOIN config.stati_doc_ordini s ON s.id = o.stato_doc_ordine_id
      WHERE o.id = (SELECT ordine_id FROM t_ordine)),
    'DRAFT'::character varying,
    'un ordine creato senza dire lo stato nasce DRAFT'
);

-- 10) La commessa: nessun DEFAULT sulla colonna, lo stato lo mette il trigger
CREATE TEMP TABLE t_commessa AS
SELECT * FROM dbops.fn_pgtap_crea_commessa('nascita commessa');

SELECT is(
    (SELECT s.codice_interno
       FROM vendite.commesse k
       JOIN vendite.stati_commessa s ON s.id = k.stato_commessa_id
      WHERE k.id = (SELECT commessa_id FROM t_commessa)),
    'BOZZA'::character varying,
    'una commessa creata senza dire lo stato nasce BOZZA (la colonna non ha piu'' DEFAULT)'
);

-- 11) La fattura: colonna NOT NULL, lo stato lo mette il trigger
CREATE TEMP TABLE t_fattura AS
SELECT * FROM dbops.fn_pgtap_crea_fattura('nascita fattura');

SELECT is(
    (SELECT s.codice_interno
       FROM vendite.fatture f
       JOIN config.stati_doc_fiscale s ON s.id = f.stato_doc_fiscale_id
      WHERE f.id = (SELECT fattura_id FROM t_fattura)),
    'DRAFT'::character varying,
    'una fattura creata senza dire lo stato nasce DRAFT'
);

-- 12) Stato iniziale esplicito passa; stato omesso prende l'iniziale. Su una
--     tabella di prova con lo stesso montaggio: il BB non conosce la tabella.
CREATE TEMP TABLE t_doc_prova (n integer, stato_doc_ordine_id bigint);
CREATE TRIGGER trg_t_doc_prova_a05_stato_iniziale_ins
    BEFORE INSERT ON t_doc_prova
    FOR EACH ROW
    EXECUTE FUNCTION script.trgfn_doc_stato_iniziale('stato_doc_ordine_id', 'config.stati_doc_ordini');

INSERT INTO t_doc_prova VALUES
    (1, script.fn_stato_iniziale_id('config.stati_doc_ordini'::regclass)),
    (2, NULL);

SELECT is(
    (SELECT count(*)::integer FROM t_doc_prova
      WHERE stato_doc_ordine_id = script.fn_stato_iniziale_id('config.stati_doc_ordini'::regclass)),
    2,
    'stato iniziale esplicito: passa; stato omesso: prende lo stato iniziale'
);

-- 13) Un preventivo che nasce EMESSO. Il trigger e' il primo: parla prima di
--     ogni altro guard e prima dei NOT NULL, quindi basta la colonna di stato.
SELECT throws_like(
    $$INSERT INTO vendite.preventivi (stato_doc_preventivo_id)
      SELECT s.id FROM config.stati_doc_preventivi s WHERE s.codice_interno = 'EMESSO'$$,
    'Il documento Preventivo non può nascere nello stato Emesso: un documento nuovo nasce in Bozza%',
    'un preventivo che nasce EMESSO e'' rifiutato, con la frase che nomina documento e stati'
);

-- 14) Acquisti montato (P-3): un ordine d'acquisto che nasce CONFERMATO
SELECT throws_like(
    $$INSERT INTO acquisti.ordini (stato_doc_ordine_id)
      SELECT s.id FROM config.stati_doc_ordini s WHERE s.codice_interno = 'CONFERMATO'$$,
    'Il documento Ordine d''acquisto non può nascere nello stato %',
    'un ordine d''acquisto che nasce CONFERMATO e'' rifiutato'
);

-- 15-16) Il lettore chiamato male
SELECT throws_like(
    $$SELECT script.fn_stato_iniziale_id(NULL)$$,
    'Chiamata non valida a script.fn_stato_iniziale_id%',
    'il lettore con vocabolario NULL: chiamata non valida'
);

SELECT throws_like(
    $$SELECT script.fn_stato_iniziale_id('config.sorgenti'::regclass)$$,
    'Chiamata non valida a script.fn_stato_iniziale_id%',
    'il lettore con una tabella senza la colonna iniziale: chiamata non valida'
);

-- 17) Montaggio con un argomento solo
CREATE TEMP TABLE t_doc_montaggio (stato_doc_ordine_id bigint);
CREATE TRIGGER trg_t_doc_montaggio_a05_stato_iniziale_ins
    BEFORE INSERT ON t_doc_montaggio
    FOR EACH ROW
    EXECUTE FUNCTION script.trgfn_doc_stato_iniziale('stato_doc_ordine_id');

SELECT throws_like(
    $$INSERT INTO t_doc_montaggio VALUES (NULL)$$,
    'Chiamata non valida a script.trgfn_doc_stato_iniziale: montaggio%',
    'montaggio con un argomento solo: chiamata non valida'
);

-- 18) Un vocabolario che non dichiara lo stato iniziale ferma ogni nascita
CREATE TEMP TABLE t_voc_muto (id bigint, descrizione text, iniziale boolean NOT NULL DEFAULT false);
INSERT INTO t_voc_muto (id, descrizione) VALUES (1, 'Uno'), (2, 'Due');
CREATE TEMP TABLE t_doc_muto (stato_id bigint);
CREATE TRIGGER trg_t_doc_muto_a05_stato_iniziale_ins
    BEFORE INSERT ON t_doc_muto
    FOR EACH ROW
    EXECUTE FUNCTION script.trgfn_doc_stato_iniziale('stato_id', 'pg_temp.t_voc_muto');

SELECT throws_like(
    $$INSERT INTO t_doc_muto VALUES (NULL)$$,
    'Chiamata non valida a script.trgfn_doc_stato_iniziale: il vocabolario % non dichiara lo stato iniziale%',
    'un vocabolario senza stato iniziale: chiamata non valida che lo nomina'
);

SELECT * FROM finish();
ROLLBACK;
