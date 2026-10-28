-- ------------------------------------------------------------
-- SPDX-License-Identifier: GPL-3.0-or-later
-- pgTAP test per Zero ERP
--
-- Test: l'offerta sul modello del documento
--   L'azione sulla matrice dell'offerta (20261026-14), il verbo
--   vendite.fn_cambia_stato_offerta con la motivazione (-16), la proiezione
--   dei passaggi di processo della revisione (-17) e i due trigger che la
--   chiamano (-18, -19), il padre superato come legame dell'annullo (-20 …
--   -24), il verbo d'annullo vendite.fn_annulla_offerta (-25), la porta
--   (-26), la capability (-27), la fixture degli stati (-28). Brief:
--   brief-modello-documento-vendita §13 (giro 9; O-1 … O-4 di Tid,
--   2026-10-26).
--
-- Semantica attesa (il contratto, non l'implementazione):
--   - la matrice dell'offerta chiede emetti_offerta sull'emissione e
--     sull'annullo dell'accettata, e su nient'altro (O-1);
--   - chi non ha emetti_offerta non vede «Emetti» e il verbo glielo
--     rifiuta; accetta, rifiuta e l'annullo della bozza non chiedono azioni;
--   - la motivazione (O-3): dove la riga del passaggio la chiede (rifiuto,
--     annulli) senza motivazione, o con una di soli spazi, il verbo rifiuta;
--     quella data si scrive sull'offerta;
--   - i passaggi di processo (superamento, rientro) non si chiedono a mano;
--     li scrive la proiezione, dalle revisioni vive (O-2): una revisione
--     nuova supera il padre; annullare l'ultima revisione viva lo riporta
--     emesso; una revisione su un padre in bozza la rifiuta la matrice;
--   - il padre che torna emesso e' un legame dell'annullo (O-4): senza
--     conferma l'annullo della revisione e' rifiutato, su ogni strada;
--   - la porta: un UPDATE diretto dello stato e' rifiutato.
--
-- Il test 25 (la porta) e' verde anche da owner: l'UPDATE diretto non passa
--   dalla scrittura comune, che sola accende la GUC della porta. Sta in coda
--   perche' tocca l'offerta di un altro test.
--
-- Elenco test (plan 25):
--   1) gli oggetti: verbo, annullo e proiezione DEFINER, porta e avviso montati
--   2) la matrice dell'offerta: emetti_offerta su emissione e annullo dell'accettata
--   3) emetti_offerta a catalogo, attiva
--   4) i trigger della revisione non scrivono piu' lo stato, niente letterale 'EMESSA'
--   5) capability in bozza senza emetti_offerta: «Emetti» non c'e', «Annulla» si'
--   6) il verbo senza emetti_offerta: E_PERMESSO_NEGATO
--   7) capability con emetti_offerta: «Emetti» c'e'
--   8) «Emetti» dal verbo: EMESSA
--   9) un secondo «Emetti»: E_DOC_GIA_NELLO_STATO
--  10) il rifiuto senza motivazione: E_OFFERTA_MOTIVAZIONE_OBBLIGATORIA
--  11) il rifiuto con una motivazione di soli spazi: idem
--  12) il superamento chiesto a mano: E_DOC_PASSAGGIO_DI_PROCESSO
--  13) una revisione nuova: il padre e' SUPERATA (dalla proiezione)
--  14) il legame della revisione: il padre, PROVENIENZA
--  15) l'annullo della revisione dal verbo di stato: E_DOC_ANNULLO_CON_LEGAMI
--  16) l'annullo dal verbo d'annullo senza conferma: E_DOC_ANNULLO_CON_LEGAMI
--  17) l'annullo confermato senza motivazione: E_OFFERTA_MOTIVAZIONE_OBBLIGATORIA
--  18) l'annullo confermato con motivazione: un legame confermato
--  19) la revisione e' ANNULLATA con la sua motivazione, il padre torna EMESSA
--  20) un'offerta senza padre non ha legami
--  21) «Accetta» senza azione e senza motivazione: ACCETTATA
--  22) l'annullo dell'accettata (azione e motivazione): ANNULLATA, nessun legame
--  23) una revisione su un padre in bozza: E_OFFERTA_TRANSIZIONE_NON_AMMESSA
--  24) la fixture porta un'offerta a RIFIUTATA, con la sua motivazione
--  25) UPDATE diretto dello stato: E_DOC_STATO_SOLO_DAL_VERBO
-- ------------------------------------------------------------

BEGIN;

DO $ctx$ BEGIN PERFORM script.fn_pgtap_set_contesto_operatore(); END $ctx$;

SET CONSTRAINTS ALL IMMEDIATE;

SELECT plan(25);

-- 1) Gli oggetti e la loro forma
SELECT is(
    (SELECT string_agg(p.proname || ':' || p.prosecdef::text, ' ' ORDER BY p.proname)
       FROM pg_proc p JOIN pg_namespace n ON n.oid = p.pronamespace
      WHERE n.nspname = 'vendite'
        AND p.proname IN ('fn_cambia_stato_offerta', 'fn_annulla_offerta',
                          'fn_offerta_proietta_stato_revisione'))
    || ' porta:' || EXISTS (SELECT 1 FROM pg_trigger t
                             WHERE t.tgrelid = 'vendite.offerte_commerciali'::regclass
                               AND t.tgfoid  = 'script.trgfn_doc_stato_solo_dal_verbo()'::regprocedure
                               AND NOT t.tgisinternal)::text
    || ' avviso:' || EXISTS (SELECT 1 FROM pg_trigger t
                              WHERE t.tgrelid = 'vendite.offerte_commerciali'::regclass
                                AND t.tgfoid  = 'vendite.trgfn_doc_guard_annullo_con_legami()'::regprocedure
                                AND NOT t.tgisinternal)::text,
    'fn_annulla_offerta:true fn_cambia_stato_offerta:true fn_offerta_proietta_stato_revisione:true porta:true avviso:true',
    'verbo, annullo e proiezione sono DEFINER; porta e avviso dell''annullo montati sull''offerta'
);

-- 2) Le azioni sulla matrice dell'offerta (O-1)
SELECT is(
    (SELECT string_agg(sd.codice_interno || '>' || sa.codice_interno || '=' || t.azione_processo_codename,
                       ' ' ORDER BY sd.codice_interno, sa.codice_interno)
       FROM config.stati_doc_offerte_transizioni t
       JOIN config.stati_doc_offerte sd ON sd.id = t.stato_da_id
       JOIN config.stati_doc_offerte sa ON sa.id = t.stato_a_id
      WHERE t.azione_processo_codename IS NOT NULL),
    'ACCETTATA>ANNULLATA=emetti_offerta BOZZA>EMESSA=emetti_offerta',
    'la matrice dell''offerta: emetti_offerta sull''emissione e sull''annullo dell''accettata, nient''altro'
);

-- 3) L'azione a catalogo
SELECT ok(
    EXISTS (SELECT 1 FROM config.azioni_processo a
             WHERE a.permission_codename = 'emetti_offerta' AND a.attivo),
    'emetti_offerta e'' a catalogo, attiva'
);

-- 4) I due trigger della revisione sono chiamanti: nessun UPDATE della
--    testata, nessun letterale dello stato di ritorno.
SELECT is(
    (SELECT string_agg(p.proname, ', ' ORDER BY p.proname)
       FROM pg_proc p
      WHERE p.oid IN ('vendite.trgfn_offerte_commerciali_revisione()'::regprocedure,
                      'vendite.trgfn_offerte_commerciali_rientro_padre()'::regprocedure)
        AND (pg_get_functiondef(p.oid) ~* 'UPDATE\s+vendite\.offerte_commerciali'
             OR pg_get_functiondef(p.oid) ~ $re$'EMESSA'$re$)),
    NULL,
    'i trigger della revisione non scrivono lo stato e non nominano EMESSA: lo fa la proiezione'
);

-- ── Fixture ─────────────────────────────────────────────────────────
-- Cliente su una utility senza tipi_utenze, listino della stessa utility con
-- la versione attiva da oggi, un articolo costruito (fuori listino, quindi
-- AGGIUNTA). Stampo: offerte_commerciali/test_fn_crea_revisione_offerta.
CREATE TEMP TABLE t_cli AS
SELECT * FROM dbops.fn_pgtap_crea_cliente_ba(
    'offerta al modello',
    (SELECT u.id FROM config.utilities u
      WHERE NOT EXISTS (SELECT 1 FROM config.tipi_utenze tu WHERE tu.utility_id = u.id)
      ORDER BY u.id LIMIT 1));

CREATE TEMP TABLE t_listino AS
SELECT * FROM dbops.fn_pgtap_crea_listino((SELECT utility_id FROM t_cli), 'offerta al modello');

CREATE TEMP TABLE t_art AS
SELECT dbops.fn_pgtap_crea_articolo('PGT-OFF-MOD-1') AS articolo_id;

-- Un'offerta in bozza pronta per l'emissione: testata, fornitura, una riga.
-- Le righe e la fornitura si scrivono solo in bozza.
CREATE FUNCTION pg_temp.t_offerta(p_padre bigint DEFAULT NULL)
RETURNS bigint LANGUAGE plpgsql AS $f$
DECLARE
    v_id bigint;
BEGIN
    INSERT INTO vendite.offerte_commerciali (
        emittente_fiscale_id, billing_account_id, istanza_utility_id, utility_id,
        listino_id, listino_versione_id, validita_dal, revisione_numero, revisione_padre_id)
    SELECT script.fn_pgtap_emittente_operatore(), c.billing_account_id, c.istanza_utility_id, c.utility_id,
           l.listino_id, l.listino_versione_id, DATE '2096-01-01',
           CASE WHEN p_padre IS NULL THEN 1 ELSE 2 END, p_padre
      FROM t_cli c, t_listino l
    RETURNING id INTO v_id;

    IF p_padre IS NULL THEN
        INSERT INTO vendite.offerte_commerciali_utilities (offerta_id, istanza_utility_id, utility_id)
        SELECT v_id, c.istanza_utility_id, c.utility_id FROM t_cli c;

        INSERT INTO vendite.offerte_commerciali_eccezioni (
            offerta_id, articolo_id, tipo_eccezione, tipo_erogazione, fonte_quantita_attesa,
            prezzo_unitario, attivo, qta_operativa)
        SELECT v_id, a.articolo_id, 'AGGIUNTA'::vendite.tipo_eccezione_contratto, 'UNA_TANTUM', 'FISSA',
               50.00, TRUE, 1.00
          FROM t_art a;
    END IF;

    RETURN v_id;
END
$f$;

CREATE TEMP TABLE t_off AS SELECT pg_temp.t_offerta() AS id;

-- 5) Permesso => nascondi
SELECT is(
    (SELECT string_agg(a ->> 'key', ' ' ORDER BY a ->> 'key')
       FROM jsonb_array_elements(script.fn_available_actions_offerta((SELECT id FROM t_off))
                                 -> 'available_actions') a),
    'annulla',
    'capability dell''offerta in bozza senza emetti_offerta: «Emetti» non c''e'', «Annulla» si'''
);

-- 6) Il verbo chiede l'azione della riga
SELECT throws_like(
    format($$SELECT * FROM vendite.fn_cambia_stato_offerta(%s, 'EMESSA', NULL)$$, (SELECT id FROM t_off)),
    'Non hai i permessi per questa operazione%',
    'il verbo dell''offerta senza emetti_offerta: E_PERMESSO_NEGATO'
);

SELECT dbops.fn_pgtap_concedi_azione(current_setting('app.current_user_id')::integer, 'emetti_offerta');

-- 7) Con l'azione «Emetti» c'e'
SELECT is(
    (SELECT string_agg(a ->> 'key', ' ' ORDER BY a ->> 'key')
       FROM jsonb_array_elements(script.fn_available_actions_offerta((SELECT id FROM t_off))
                                 -> 'available_actions') a),
    'annulla emetti',
    'capability dell''offerta in bozza con emetti_offerta: «Emetti» c''e'''
);

-- 8) «Emetti» dal verbo
-- ⚠️ Il verbo in un'istruzione sua: una lettura nella stessa istruzione
--    vedrebbe la fotografia di prima della chiamata.
SELECT * FROM vendite.fn_cambia_stato_offerta((SELECT id FROM t_off), 'EMESSA', NULL);

SELECT is(
    (SELECT s.codice_interno FROM vendite.offerte_commerciali o
       JOIN config.stati_doc_offerte s ON s.id = o.stato_doc_offerta_id
      WHERE o.id = (SELECT id FROM t_off)),
    'EMESSA'::varchar,
    '«Emetti» dal verbo: l''offerta e'' EMESSA'
);

-- 9) Lo stato che ha gia'
SELECT throws_like(
    format($$SELECT * FROM vendite.fn_cambia_stato_offerta(%s, 'EMESSA', NULL)$$, (SELECT id FROM t_off)),
    'Il documento è già nello stato%',
    'un secondo «Emetti»: E_DOC_GIA_NELLO_STATO'
);

-- 10) La motivazione del rifiuto (O-3)
SELECT throws_like(
    format($$SELECT * FROM vendite.fn_cambia_stato_offerta(%s, 'RIFIUTATA', NULL)$$, (SELECT id FROM t_off)),
    'Per portare l''offerta%serve una motivazione.',
    'il rifiuto senza motivazione: E_OFFERTA_MOTIVAZIONE_OBBLIGATORIA'
);

-- 11) ... e una di soli spazi e' una motivazione che manca
SELECT throws_like(
    format($$SELECT * FROM vendite.fn_cambia_stato_offerta(%s, 'RIFIUTATA', '   ')$$, (SELECT id FROM t_off)),
    'Per portare l''offerta%serve una motivazione.',
    'il rifiuto con una motivazione di soli spazi: E_OFFERTA_MOTIVAZIONE_OBBLIGATORIA'
);

-- 12) Il superamento non si chiede a mano
SELECT throws_like(
    format($$SELECT * FROM vendite.fn_cambia_stato_offerta(%s, 'SUPERATA', NULL)$$, (SELECT id FROM t_off)),
    'Questo passaggio di stato lo fa il sistema%',
    'il superamento chiesto al verbo: E_DOC_PASSAGGIO_DI_PROCESSO'
);

-- 13) Una revisione nuova supera il padre (la proiezione, dal trigger)
CREATE TEMP TABLE t_rev AS
SELECT vendite.fn_crea_revisione_offerta((SELECT id FROM t_off), 'pgtap') AS id;

SELECT is(
    (SELECT s.codice_interno FROM vendite.offerte_commerciali o
       JOIN config.stati_doc_offerte s ON s.id = o.stato_doc_offerta_id
      WHERE o.id = (SELECT id FROM t_off)),
    'SUPERATA'::varchar,
    'una revisione nuova: il padre e'' SUPERATA'
);

-- 14) Il legame della revisione (O-4)
SELECT is(
    (SELECT string_agg(l.origine || ':' || l.natura || ':' || (l.origine_id = (SELECT id FROM t_off))::text, ' ')
       FROM vendite.fn_documento_legami('OFFERTA_COMMERCIALE', (SELECT id FROM t_rev)) l),
    'OFFERTA_COMMERCIALE:PROVENIENZA:true',
    'il legame della revisione e'' il padre superato, di provenienza'
);

-- 15) L'avviso, sul verbo di stato
SELECT throws_like(
    format($$SELECT * FROM vendite.fn_cambia_stato_offerta(%s, 'ANNULLATA', 'pgTAP')$$, (SELECT id FROM t_rev)),
    'Annullando %',
    'l''annullo della revisione dal verbo di stato, senza conferma: E_DOC_ANNULLO_CON_LEGAMI'
);

-- 16) La conferma che non corrisponde
SELECT throws_like(
    format($$SELECT vendite.fn_annulla_offerta(%s, 'pgTAP', NULL)$$, (SELECT id FROM t_rev)),
    'Annullando %',
    'l''annullo della revisione senza dichiarare i legami: E_DOC_ANNULLO_CON_LEGAMI'
);

-- 17) Confermato, ma senza motivazione
SELECT throws_like(
    format($$SELECT vendite.fn_annulla_offerta(%s, NULL, 1)$$, (SELECT id FROM t_rev)),
    'Per portare l''offerta%serve una motivazione.',
    'l''annullo confermato senza motivazione: E_OFFERTA_MOTIVAZIONE_OBBLIGATORIA'
);

-- 18) Confermato, con la motivazione
SELECT is(
    vendite.fn_annulla_offerta((SELECT id FROM t_rev), '  revisione sbagliata  ', 1),
    1,
    'l''annullo confermato della revisione: un legame confermato'
);

-- 19) La revisione annullata con la sua motivazione; il padre torna emesso
SELECT is(
    (SELECT sr.codice_interno || '|' || r.motivazione_rifiuto || '|' || sp.codice_interno
       FROM vendite.offerte_commerciali r
       JOIN config.stati_doc_offerte sr ON sr.id = r.stato_doc_offerta_id
       JOIN vendite.offerte_commerciali p ON p.id = r.revisione_padre_id
       JOIN config.stati_doc_offerte sp ON sp.id = p.stato_doc_offerta_id
      WHERE r.id = (SELECT id FROM t_rev)),
    'ANNULLATA|revisione sbagliata|EMESSA',
    'la revisione e'' ANNULLATA con la motivazione (senza spazi ai bordi), il padre torna EMESSA'
);

-- 20) Senza padre nessun legame
SELECT is(
    (SELECT count(*)::integer FROM vendite.fn_documento_legami('OFFERTA_COMMERCIALE', (SELECT id FROM t_off))),
    0,
    'un''offerta senza revisione precedente non ha legami'
);

-- 21) «Accetta»: nessuna azione, nessuna motivazione
SELECT * FROM vendite.fn_cambia_stato_offerta((SELECT id FROM t_off), 'ACCETTATA', NULL);

SELECT is(
    (SELECT s.codice_interno FROM vendite.offerte_commerciali o
       JOIN config.stati_doc_offerte s ON s.id = o.stato_doc_offerta_id
      WHERE o.id = (SELECT id FROM t_off)),
    'ACCETTATA'::varchar,
    '«Accetta» dal verbo senza motivazione: ACCETTATA'
);

-- 22) L'annullo dell'accettata: nessun legame
CREATE TEMP TABLE t_ann AS
SELECT vendite.fn_annulla_offerta((SELECT id FROM t_off), 'cliente ritirato', NULL) AS legami;

SELECT is(
    (SELECT a.legami FROM t_ann a)
    || '|' || (SELECT s.codice_interno || '|' || o.motivazione_rifiuto
                 FROM vendite.offerte_commerciali o
                 JOIN config.stati_doc_offerte s ON s.id = o.stato_doc_offerta_id
                WHERE o.id = (SELECT id FROM t_off)),
    '0|ANNULLATA|cliente ritirato',
    'l''annullo dell''accettata (azione e motivazione): ANNULLATA, nessun legame'
);

-- 23) Una revisione su un padre in bozza: il superamento lo rifiuta la
--     matrice (precisazione su O-2, dichiarata in 20261026-17).
CREATE TEMP TABLE t_bozza AS SELECT pg_temp.t_offerta() AS id;

SELECT throws_like(
    format($$SELECT pg_temp.t_offerta(%s)$$, (SELECT id FROM t_bozza)),
    'Transizione di stato dell''offerta non ammessa%',
    'una revisione su un padre in bozza: E_OFFERTA_TRANSIZIONE_NON_AMMESSA'
);

-- 24) La fixture degli stati: il rifiuto con la sua motivazione
CREATE TEMP TABLE t_fix AS
SELECT dbops.fn_pgtap_porta_a_stato('vendite.offerte_commerciali', (SELECT id FROM t_bozza), 'RIFIUTATA') AS stato;

SELECT is(
    (SELECT f.stato FROM t_fix f)
    || '|' || COALESCE((SELECT o.motivazione_rifiuto FROM vendite.offerte_commerciali o
                         WHERE o.id = (SELECT id FROM t_bozza)), 'NULL'),
    'RIFIUTATA|Fixture pgTAP',
    'la fixture porta l''offerta a RIFIUTATA dal verbo, con la motivazione della fixture'
);

-- 25) La porta
SELECT throws_like(
    format($$UPDATE vendite.offerte_commerciali SET stato_doc_offerta_id = %s WHERE id = %s$$,
           script.fn_stato_abortito_id('vendite.offerte_commerciali'::regclass),
           (SELECT id FROM t_bozza)),
    'Lo stato del documento%si cambia solo dalle sue operazioni%',
    'UPDATE diretto dello stato dell''offerta: E_DOC_STATO_SOLO_DAL_VERBO'
);

SELECT * FROM finish();
ROLLBACK;
