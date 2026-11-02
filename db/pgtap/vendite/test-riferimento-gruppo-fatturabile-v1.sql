-- ------------------------------------------------------------
-- SPDX-License-Identifier: AGPL-3.0-or-later
-- pgTAP test per Zero ERP
--
-- Test: la scheda Critiche smette di far leggere un uuid, e il banner smette
--       di contare allarmi per contare GESTI.
-- ChangeSet: 20260908-31 (split + riferimento), -32 (la lista lo espone e lo
--            ordina), -33 (i tre conteggi del banner)
--
-- Elenco test (plan 16):
--   1) ⭐ ANDATA E RITORNO sulla forma documento: split(build(x)) = x
--   2) ⭐ ANDATA E RITORNO sulla forma sourceless: 'MAN:<commessa>'
--   3) una chiave irriconoscibile da' tre NULL e NON solleva
--   4) una chiave con un secondo ':' non viene TRONCATA in silenzio
--   5) il riferimento di una chiave storta ripiega sulla chiave grezza
--   6) NULL entra e NULL esce: la segnalazione del GIRO non ha documento
--   7) ⭐ il riferimento di un documento vero e' il suo NUMERO, non l'uuid
--   8) la lista espone la colonna `riferimento`
--   9) ...e la riempie sul ramo LOTTO, lasciandola vuota sul giro
--  10) ⭐ ordinando per riferimento le critiche del GIRO stanno in TESTA
--  11) ⛔ `gruppo_key` NON e' ordinabile: la sua colonna e' spenta
--  12) `riferimento` invece si', e non solleva
--  13) ⭐ il banner conta DOCUMENTI, non segnalazioni
--  14) ...e conta a parte le critiche del GIRO, che documenti non sono
--  15) il denominatore viene dagli ESITI, non dal perimetro
--  16) ⚠️ il riferimento coincide con quello della dashboard Competenza
--
-- Scopo:
--   Sulla scheda Critiche il documento di una segnalazione si leggeva come
--   `ORDINE_VENDITA:01a06ce4-35a6-721a-9cd8-9da48bf77626`. La chiave serve al
--   PULSANTE, non all'occhio: ora accanto esce `ORD0036004`.
--
-- ⚠️ TUTTI I CASI SONO COSTRUITI. L'unica cosa presa dai dati e' l'id della
--   sorgente ORDINE_VENDITA, che e' catalogo di seed.
--
-- rev 2026-10-27 (lotto 4 di D7): i casi 7 e 16 erano DATA-DEPENDENT (uno
--   skip motivato su un database senza esiti di lotto ne' righe in dashboard):
--   ora il 7 costruisce un ordine vero (dbops.fn_pgtap_crea_ordine) e ne
--   compone la chiave con fn_build_gruppo_fatturabile_key, il 16 costruisce
--   una commessa con un'attivita' (dbops.fn_pgtap_crea_commessa) e legge la
--   SUA riga di dashboard. Gli skip restano come rete, ma da zero non scattano.
-- ------------------------------------------------------------

BEGIN;

-- ⚠️ Vincoli DIFFERITI: senza questa riga il test smetterebbe di verificarli.
SET CONSTRAINTS ALL IMMEDIATE;

-- Contesto applicativo: questo test gira come gira l'applicazione.
DO $ctx$ BEGIN PERFORM script.fn_pgtap_set_contesto_operatore(); END $ctx$;

SELECT plan(16);

-- ============================================================
-- 1..2 — ⭐ ANDATA E RITORNO, che e' il presidio delle due gemelle
-- ============================================================
-- ⛔ Il prefisso 'MAN' e la forma della chiave sono decisi da
--   fn_build_gruppo_fatturabile_key. Lo splitter li RILEGGE. Nessun occhio
--   puo' garantire che restino allineati: lo garantisce questo giro.
CREATE TEMP TABLE tmp_sorgente AS
SELECT s.id, s.codice_interno
  FROM config.sorgenti s
 WHERE s.codice_interno = 'ORDINE_VENDITA';

SELECT is(
    (SELECT (sp.sorgente_tipo_id::text || '|' || sp.sorgente_uid)
       FROM tmp_sorgente t,
            LATERAL vendite.fn_split_gruppo_fatturabile_key(
                vendite.fn_build_gruppo_fatturabile_key(
                    t.id, 'aaaaaaaa-bbbb-4ccc-8ddd-eeeeeeeeeeee', 42)) sp),
    (SELECT t.id::text || '|aaaaaaaa-bbbb-4ccc-8ddd-eeeeeeeeeeee' FROM tmp_sorgente t),
    '1) andata e ritorno sulla forma DOCUMENTO: split(build(x)) torna la coppia'
);

SELECT is(
    (SELECT sp.commessa_id
       FROM LATERAL vendite.fn_split_gruppo_fatturabile_key(
                vendite.fn_build_gruppo_fatturabile_key(NULL, NULL, 4242)) sp),
    4242::bigint,
    '2) andata e ritorno sulla forma SOURCELESS: MAN: torna la commessa'
);

-- ============================================================
-- 3..5 — lo splitter non rompe mai una lista
-- ============================================================
-- ⚠️ La chiama una LISTA: una chiave storta deve produrre un ripiego, non una
--   lista rotta. Per questo non c'e' nessun throws_ok qui, ed e' voluto.
SELECT ok(
    (SELECT sp.sorgente_tipo_id IS NULL
        AND sp.sorgente_uid IS NULL
        AND sp.commessa_id IS NULL
       FROM vendite.fn_split_gruppo_fatturabile_key('non-e-una-chiave') sp),
    '3) una chiave irriconoscibile da'' tre NULL, e non solleva'
);

-- ⚠️ `substr` e non `split_part`: con split_part l'uid sarebbe stato TRONCATO
--   al secondo ':', in silenzio — e un troncamento silenzioso e' peggio di un
--   ripiego dichiarato.
SELECT is(
    (SELECT sp.sorgente_uid
       FROM tmp_sorgente t,
            LATERAL vendite.fn_split_gruppo_fatturabile_key(
                t.codice_interno || ':pezzo-uno:pezzo-due') sp),
    'pezzo-uno:pezzo-due',
    '4) una chiave con un secondo '':'' non viene troncata in silenzio'
);

SELECT is(
    vendite.fn_riferimento_gruppo_fatturabile('CHIAVE_STORTA:xyz'),
    'CHIAVE_STORTA:xyz',
    '5) il riferimento di una chiave storta ripiega sulla CHIAVE GREZZA'
);

SELECT is(
    vendite.fn_riferimento_gruppo_fatturabile(NULL),
    NULL,
    '6) NULL entra e NULL esce: la segnalazione del GIRO non ha documento'
);

-- ============================================================
-- 7 — ⭐ il verso che conta: un documento vero da' il suo NUMERO
-- ============================================================
-- rev 2026-10-27 (lotto 4 di D7): l'ordine si COSTRUISCE e la chiave si
--   compone dalla gemella vera; prima si pescava l'ultimo esito di lotto con
--   una chiave di documento, e da zero non ce n'era nessuno (skip).
CREATE TEMP TABLE tmp_ordine_rif AS
SELECT * FROM dbops.fn_pgtap_crea_ordine('riferimento gruppo');

CREATE TEMP TABLE tmp_doc_vero AS
SELECT k.gruppo_key,
       (SELECT d.documento_numero
          FROM vendite.fn_split_gruppo_fatturabile_key(k.gruppo_key) sp,
               LATERAL vendite.fn_get_sorgente_documento_ref(
                   sp.sorgente_tipo_id, sp.sorgente_uid) d) AS numero
  FROM tmp_ordine_rif o, tmp_sorgente t,
       LATERAL (SELECT vendite.fn_build_gruppo_fatturabile_key(
                           t.id, o.ordine_uid::text, NULL) AS gruppo_key) k;

SELECT CASE
  WHEN NOT EXISTS (SELECT 1 FROM tmp_doc_vero WHERE numero IS NOT NULL)
    THEN skip('nessun esito di lotto che nomini un documento risolvibile su questo database', 1)
  ELSE is(
    (SELECT vendite.fn_riferimento_gruppo_fatturabile(gruppo_key) FROM tmp_doc_vero),
    (SELECT numero FROM tmp_doc_vero),
    '7) il riferimento di un documento vero e'' il suo NUMERO, non la chiave')
END;

-- ============================================================
-- FIXTURE — un lotto con due documenti e tre critiche
-- ============================================================
-- rev 2026-10-27 (lotto 4 di D7): il lotto si COSTRUISCE
--   (dbops.fn_pgtap_crea_lotto, DRAFT, mese della data operativa, azienda di
--   chi agisce). Prima tipo documento ed emittente si pescavano dall'ultimo
--   lotto del DB: da zero non c'era, e il lotto scritto a mano fuori dal
--   perimetro faceva rifiutare dalla RLS gli esiti qui sotto.
CREATE TEMP TABLE tmp_lotto AS
SELECT l.lotto_id AS id FROM dbops.fn_pgtap_crea_lotto('riferimento') l;

DO $fixture$
DECLARE
    v_lotto vendite.fatturazione_lotti.id%TYPE := (SELECT id FROM tmp_lotto);
BEGIN

    -- Due documenti presi in carico. ⚠️ NESSUNA riga di perimetro: cosi' il
    --   test 15 prova che il denominatore viene dagli ESITI — col perimetro
    --   direbbe «su 0» e nessuno collegherebbe il difetto al seed.
    INSERT INTO vendite.fatturazione_lotti_esiti
        (lotto_id, gruppo_key, stato_esecuzione, errore_codice, errore_messaggio)
    VALUES (v_lotto, 'PGTAP-RIF:alfa', 'ERRORE', 'E_PULL_COMMESSA', 'rotto'),
           (v_lotto, 'PGTAP-RIF:beta', 'ERRORE', 'E_PULL_COMMESSA', 'rotto');

    -- Tre critiche: DUE sullo stesso documento (che resta UN documento fermo),
    -- una del GIRO.
    PERFORM vendite.fn_log_pipeline_fase(
        v_lotto, NULL, 'PGTAP-RIF-1', 'C', 'prima critica di alfa',
        '{}'::jsonb, 'E_PULL_COMMESSA', 'PGTAP-RIF:alfa');
    PERFORM vendite.fn_log_pipeline_fase(
        v_lotto, NULL, 'PGTAP-RIF-2', 'C', 'seconda critica di alfa',
        '{}'::jsonb, 'E_PULL_COMMESSA', 'PGTAP-RIF:alfa');
    PERFORM vendite.fn_log_pipeline_fase(
        v_lotto, NULL, 'PGTAP-RIF-3', 'C', 'emittente non risolto: e'' del giro',
        '{}'::jsonb, 'E_PULL_COMMESSA');
END;
$fixture$;

-- ============================================================
-- 8..12 — la LISTA
-- ============================================================
SELECT has_function(
    'vendite', 'fn_list_lotto_segnalazioni',
    ARRAY['bigint', 'text', 'character', 'boolean', 'boolean',
          'integer', 'integer', 'text', 'text'],
    '8) la lista c''e'' con la firma di sempre: il DROP+CREATE non l''ha spostata'
);

-- ⚠️ Il ripiego sulla chiave e' voluto: `PGTAP-RIF` non e' una sorgente a
--   catalogo, quindi il riferimento resta la chiave — cioe' esattamente cio'
--   che l'operatore vedeva prima. Peggiorare e' impossibile.
SELECT is(
    (SELECT string_agg(COALESCE(s.riferimento, '(giro)'), ',' ORDER BY s.fase)
       FROM vendite.fn_list_lotto_segnalazioni((SELECT id FROM tmp_lotto)) s
      WHERE s.fase LIKE 'PGTAP-RIF-%'),
    'PGTAP-RIF:alfa,PGTAP-RIF:alfa,(giro)',
    '9) il riferimento c''e'' sulle critiche di documento e manca su quella del giro'
);

-- ⭐ IL PUNTO DELLA DECISIONE: le critiche del GIRO stanno in TESTA. In coda,
--   su una lista paginata, l'operatore toglierebbe i documenti uno per uno e
--   il lotto non ripartirebbe lo stesso, per una riga che non ha mai visto.
SELECT is(
    (SELECT s.fase
       FROM vendite.fn_list_lotto_segnalazioni(
                (SELECT id FROM tmp_lotto), p_order_by => 'riferimento',
                p_order_dir => 'asc') s
      WHERE s.fase LIKE 'PGTAP-RIF-%'
      LIMIT 1),
    'PGTAP-RIF-3',
    '10) ordinando per riferimento la critica DEL GIRO sta in TESTA'
);

-- ⛔ La colonna `gruppo_fatturabile` e' spenta a catalogo, quindi non c'e'
--   nessuna freccia da cliccare: offrirla in whitelist sarebbe una capacita'
--   irraggiungibile, e il presidio di gen_seed_lista.py la segnala.
SELECT throws_ok(
    format($$SELECT * FROM vendite.fn_list_lotto_segnalazioni(%s, p_order_by => 'gruppo_key')$$,
           (SELECT id FROM tmp_lotto)),
    'P0001',
    NULL,
    '11) `gruppo_key` non e'' ordinabile: la sua colonna non si vede piu'''
);

SELECT lives_ok(
    format($$SELECT * FROM vendite.fn_list_lotto_segnalazioni(%s, p_order_by => 'riferimento')$$,
           (SELECT id FROM tmp_lotto)),
    '12) `riferimento` invece si'', ed e'' la voce che il seed offre'
);

-- ============================================================
-- 13..15 — il BANNER
-- ============================================================
-- ⭐ Tre critiche vive, ma i GESTI sono due: un documento con due critiche
--   resta un documento solo, e la terza non e' un documento affatto.
SELECT is(
    (SELECT documenti_bloccanti_count
       FROM vendite.fn_get_lotto_segnalazioni_summary((SELECT id FROM tmp_lotto))),
    1::bigint,
    '13) il banner conta DOCUMENTI: due critiche sullo stesso documento fanno uno'
);

SELECT is(
    (SELECT critiche_giro_count
       FROM vendite.fn_get_lotto_segnalazioni_summary((SELECT id FROM tmp_lotto))),
    1::bigint,
    '14) e conta a parte le critiche del GIRO, che documenti non sono'
);

-- ⛔ Il lotto della fixture NON dichiara un perimetro: col perimetro il
--   denominatore sarebbe zero, ed e' il difetto che questo test costruisce.
SELECT is(
    (SELECT documenti_presi_in_carico_count
       FROM vendite.fn_get_lotto_segnalazioni_summary((SELECT id FROM tmp_lotto))),
    2::bigint,
    '15) il denominatore viene dagli ESITI: vale anche sui giri senza perimetro'
);

-- ============================================================
-- 16 — ⚠️ la seconda scrittura, dichiarata e presidiata
-- ============================================================
-- `vw_dash_competenza_gruppi.riferimento` fa la STESSA scala di ripiego, e non
-- chiama questa funzione: la' il LATERAL serve comunque per `documento_id`, e
-- passare dalla chiave vorrebbe dire risolvere due volte per riga.
-- ⚠️ Questo test prova che OGGI coincidono, non che non possano divergere: e'
--   un ripiego dichiarato, non un pareggio.
-- rev 2026-10-27 (lotto 4 di D7): la riga di dashboard si COSTRUISCE (una
--   commessa con un'attivita', dbops.fn_pgtap_crea_commessa) e si legge
--   SOLO quella; prima si pescavano le prime cinque righe visibili, e da zero
--   non ce n'era nessuna (skip).
CREATE TEMP TABLE tmp_commessa_dash AS
SELECT * FROM dbops.fn_pgtap_crea_commessa('riferimento dashboard', NULL, NULL, true);

CREATE TEMP TABLE tmp_dash AS
SELECT g.gruppo_key, g.riferimento
  FROM vendite.vw_dash_competenza_gruppi g
 WHERE g.gruppo_key IS NOT NULL
   AND g.commessa_id = (SELECT commessa_id FROM tmp_commessa_dash);

SELECT CASE
  WHEN NOT EXISTS (SELECT 1 FROM tmp_dash)
    THEN skip('la dashboard Competenza non ha righe visibili all''operatore su questo database', 1)
  ELSE is(
    (SELECT count(*) FROM tmp_dash d
      WHERE vendite.fn_riferimento_gruppo_fatturabile(d.gruppo_key)
            IS DISTINCT FROM d.riferimento),
    0::bigint,
    '16) il riferimento coincide con quello della dashboard Competenza')
END;

SELECT * FROM finish();
ROLLBACK;
