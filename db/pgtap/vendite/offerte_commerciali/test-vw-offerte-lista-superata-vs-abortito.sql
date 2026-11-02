-- ------------------------------------------------------------
-- SPDX-License-Identifier: AGPL-3.0-or-later
-- pgTAP test per Zero ERP
--
-- Test: vendite.vw_offerte_commerciali_lista — le DUE domande che `is_attiva`
--       teneva insieme sono ora colonne distinte (changeSet 20260828-07 /
--       20260828-10, brief-db-revisione-attiva-due-domande).
--
--       Prima: is_attiva = codice_interno NOT IN ('SUPERATA','ANNULLATA').
--       Due domande in un flag solo:
--         1) «e' l'ultima revisione?» — SUPERATA, scritta sul padre dal trigger
--            di revisione;
--         2) «non e' annullata?»      — ANNULLATA.
--       Non separabili a valle, quindi la lista (che filtra is_attiva IS TRUE di
--       default) non poteva offrire un filtro di stato «Annullata» che
--       restituisse qualcosa — mai, per costruzione.
--
--       Ora le due domande sono `is_superata` e `is_abortito`, dichiarate a
--       catalogo (config.stati_doc_offerte.is_superato / .is_abortito), e
--       is_attiva = NOT is_superata AND NOT is_abortito.
--
--       ⚠️ La riscrittura NON deve cambiare un solo valore: il test 4 lo prova
--       sul CATALOGO, stato per stato, non sui documenti — e' una proprieta'
--       del modello, non della popolazione di oggi.
--
--       Fixture:
--         A) offerta BOZZA -> ANNULLATA, revisione unica
--            -> e' l'ULTIMA revisione (is_superata=F) ma non e' attiva.
--         B) rev.1 EMESSA + INSERT rev.2 (il trigger porta rev.1 a SUPERATA)
--            -> rev.1 is_superata=T / is_abortito=F; rev.2 attiva.
--
-- rev 2026-10-26 (brief-modello-documento-vendita §13, giro 9): lo stato
--   dell'offerta dal verbo — A si annulla con vendite.fn_annulla_offerta, rev.1
--   di B si emette con dbops.fn_pgtap_porta_a_stato, invece degli UPDATE di
--   stato che la porta ora rifiuta.
--
-- Indice test (1..11):
--   1)  Struttura catalogo: config.stati_doc_offerte espone is_superato
--   2)  Catalogo: is_superato=true sul SOLO stato SUPERATA
--   3)  Catalogo: is_abortito=true sul SOLO stato ANNULLATA
--   4)  ⭐ Equivalenza: (NOT is_superato AND NOT is_abortito) coincide, stato per
--       stato, col vecchio letterale NOT IN ('SUPERATA','ANNULLATA')
--   5)  Struttura vista: is_attiva + is_superata + is_abortito + has_next_revisione
--   6)  Setup scope operatore (guard emittente sull'INSERT + viste invoker)
--   7)  A: annullata a revisione unica -> superata=F, abortito=T, attiva=F
--   8)  B rev.1: superata dal trigger -> superata=T, abortito=F, attiva=F
--   9)  B rev.2: la viva del lineage -> superata=F, abortito=F, attiva=T
--   10) Invariante di composizione: is_attiva = NOT is_superata AND NOT is_abortito
--   11) ⭐ I due predicati NON coincidono: «solo l'ultima revisione» rende 2
--       righe, is_attiva ne rende 1 — la differenza e' l'annullata
-- ------------------------------------------------------------

BEGIN;
-- ⚠️ Vincoli DIFFERITI: senza questa riga i DEFERRABLE INITIALLY DEFERRED non
--   scatterebbero mai (il COMMIT non arriva: si chiude in ROLLBACK) e il file
--   sarebbe verde per sottrazione.
SET CONSTRAINTS ALL IMMEDIATE;

-- Contesto applicativo: il test gira come gira l'applicazione (OPERATORE + RLS),
-- non come owner. La vista e' security_invoker=on.
DO $ctx$ BEGIN PERFORM script.fn_pgtap_set_contesto_operatore(); END $ctx$;

SELECT plan(11);

-- ============================================================
-- 1) Struttura catalogo
--    ⚠️ Prima di qualunque asserzione sui valori: se la colonna manca, il resto
--    fallirebbe con «colonna inesistente» e il messaggio non direbbe che il
--    changeSet 20260828-07 non e' applicato.
-- ============================================================
SELECT ok(
    EXISTS (SELECT 1 FROM information_schema.columns c
             WHERE c.table_schema = 'config'
               AND c.table_name   = 'stati_doc_offerte'
               AND c.column_name  = 'is_superato'),
    '1) config.stati_doc_offerte espone is_superato (20260828-07 applicato)'
);

-- ============================================================
-- 2) Il seed dice esattamente una cosa: SUPERATA e' lo stato di superamento.
-- ============================================================
SELECT is(
    (SELECT string_agg(s.codice_interno, ',' ORDER BY s.codice_interno)
       FROM config.stati_doc_offerte s
      WHERE s.is_superato IS TRUE),
    'SUPERATA',
    '2) is_superato=true sul solo stato SUPERATA'
);

-- ============================================================
-- 3) E l'altro asse resta dov'era (20260714-05).
-- ============================================================
SELECT is(
    (SELECT string_agg(s.codice_interno, ',' ORDER BY s.codice_interno)
       FROM config.stati_doc_offerte s
      WHERE s.is_abortito IS TRUE),
    'ANNULLATA',
    '3) is_abortito=true sul solo stato ANNULLATA'
);

-- ============================================================
-- 4) ⭐ La riscrittura di is_attiva non cambia nulla: si prova sul CATALOGO,
--    stato per stato — proprieta' del modello, non della popolazione.
--    Si asserisce anche che gli stati confrontati siano > 0: uno scarto nullo
--    su zero righe sarebbe verde per sottrazione.
-- ============================================================
SELECT is(
    (SELECT ROW(count(*) > 0,
                count(*) FILTER (WHERE
                    ((NOT s.is_superato) AND (NOT s.is_abortito))
                    IS DISTINCT FROM
                    (s.codice_interno::text <> ALL (ARRAY['SUPERATA','ANNULLATA']))
                ))::text
       FROM config.stati_doc_offerte s),
    ROW(true, 0::bigint)::text,
    '4) (NOT is_superato AND NOT is_abortito) coincide col vecchio NOT IN (''SUPERATA'',''ANNULLATA'') su ogni stato'
);

-- ============================================================
-- 5) Struttura vista
-- ============================================================
SELECT is(
    (SELECT count(*)::int
       FROM information_schema.columns c
      WHERE c.table_schema = 'vendite'
        AND c.table_name   = 'vw_offerte_commerciali_lista'
        AND c.column_name IN ('is_attiva', 'is_superata', 'is_abortito', 'has_next_revisione')),
    4,
    '5) vw_offerte_commerciali_lista espone is_attiva + is_superata + is_abortito + has_next_revisione'
);

-- ============================================================
-- 6) Setup scope operatore. Serve DUE volte: il guard
--    script.trgfn_guard_emittente_scope blocca l'INSERT dei fixture fuori
--    scope, e la vista e' security_invoker (fuori scope non si vedrebbe nulla,
--    e un conteggio a zero passerebbe per «non c'e'»).
-- ============================================================
-- 2026-10-08, brief-db-offerta-emissione-ed-erogazione §F.2: il listino del
--   documento e' della sua utility e del suo emittente (guard nuovo); fixture
--   costruito invece che preso dai dati. Cliente su una utility senza
--   tipi_utenze (evita il guard tipo/classe sui satelliti utilities), legato
--   dal z90 all'emittente di chi agisce (contesto gia' aperto); listino, con la
--   sua versione ATTIVA da oggi, sulla stessa utility.
CREATE TEMP TABLE tmp_osa_cli AS
SELECT * FROM dbops.fn_pgtap_crea_cliente_ba(
    'lista superata vs abortito',
    (SELECT u.id FROM config.utilities u
      WHERE NOT EXISTS (SELECT 1 FROM config.tipi_utenze tu WHERE tu.utility_id = u.id)
      ORDER BY u.id LIMIT 1));

CREATE TEMP TABLE tmp_osa_listino AS
SELECT * FROM dbops.fn_pgtap_crea_listino((SELECT utility_id FROM tmp_osa_cli), 'lista superata vs abortito');

CREATE TEMP TABLE tmp_osa_ctx AS
SELECT
    (SELECT billing_account_id FROM tmp_osa_cli) AS billing_account_id,
    (SELECT istanza_utility_id FROM tmp_osa_cli) AS istanza_utility_id,
    (SELECT utility_id FROM tmp_osa_cli) AS utility_id,
    script.fn_pgtap_emittente_operatore() AS emittente_fiscale_id,
    (SELECT listino_id FROM tmp_osa_listino) AS listino_id,
    (SELECT listino_versione_id FROM tmp_osa_listino) AS listino_versione_id,
    (SELECT id FROM config.stati_doc_offerte WHERE codice_interno = 'BOZZA')     AS stato_bozza_id,
    (SELECT id FROM config.stati_doc_offerte WHERE codice_interno = 'EMESSA')    AS stato_emessa_id,
    (SELECT id FROM config.stati_doc_offerte WHERE codice_interno = 'ANNULLATA') AS stato_annullata_id;

CREATE TEMP TABLE tmp_osa_op AS
SELECT id.auth_user_id AS user_id
  FROM anagrafiche.identita_digitali id
 WHERE id.ruolo_applicativo = 'OPERATORE'::config.ruolo_applicativo
   AND id.attivo = true
   AND NOT EXISTS (
       SELECT 1 FROM config.profili_accesso_bindings pab
       JOIN config.profili_accesso pa ON pa.id = pab.profilo_accesso_id
       WHERE pab.identita_digitale_id = id.id
         AND pab.attivo = true
         AND pa.tipo = 'SUPER_ADMIN'::config.tipo_profilo_accesso)
 ORDER BY id.id LIMIT 1;

SELECT ok(
    (SELECT ctx.billing_account_id IS NOT NULL
        AND ctx.emittente_fiscale_id IS NOT NULL
        AND ctx.listino_id IS NOT NULL
        AND ctx.listino_versione_id IS NOT NULL
        AND ctx.stato_bozza_id IS NOT NULL
        AND ctx.stato_emessa_id IS NOT NULL
        AND ctx.stato_annullata_id IS NOT NULL
        AND (SELECT user_id FROM tmp_osa_op) IS NOT NULL
       FROM tmp_osa_ctx ctx),
    '6) Fixture context completo (BA, emittente, listino/versione, stati) + operatore non-super'
);

SET LOCAL zeroerp.allow_user_emittente_delete_override = 'on';
DELETE FROM config.user_emittenti_fiscali
 WHERE auth_user_id = (SELECT user_id FROM tmp_osa_op);
SET LOCAL zeroerp.allow_user_emittente_delete_override = '';

INSERT INTO config.user_emittenti_fiscali (auth_user_id, emittente_fiscale_id, meta)
SELECT o.user_id, ctx.emittente_fiscale_id,
       '{"test_scope":"pgtap_offerte_superata_vs_abortito"}'::jsonb
  FROM tmp_osa_op o, tmp_osa_ctx ctx;

SELECT set_config('app.current_user_id',
    (SELECT user_id::text FROM tmp_osa_op), true);

-- ============================================================
-- Fixture A) offerta annullata, revisione unica.
--   La transizione ammessa e' BOZZA -> ANNULLATA (stati_doc_offerte_transizioni):
--   si nasce in BOZZA e si annulla.
-- ============================================================
CREATE TEMP TABLE tmp_osa_a AS
WITH ins AS (
    INSERT INTO vendite.offerte_commerciali (
        emittente_fiscale_id, billing_account_id, istanza_utility_id, utility_id,
        listino_id, listino_versione_id, validita_dal, stato_doc_offerta_id,
        revisione_numero, revisione_padre_id)
    SELECT ctx.emittente_fiscale_id, ctx.billing_account_id, ctx.istanza_utility_id,
           ctx.utility_id, ctx.listino_id, ctx.listino_versione_id,
           DATE '2091-01-01', ctx.stato_bozza_id, 1, NULL
      FROM tmp_osa_ctx ctx
    RETURNING id)
SELECT id FROM ins;

-- rev 2026-10-26 (giro 9): l'annullo dal verbo, con la motivazione; nessun
--   legame da confermare (NULL: revisione unica). La data_annullamento che
--   l'UPDATE scriveva a mano non e' oggetto del test.
SELECT vendite.fn_annulla_offerta(a.id, 'pgTAP: offerta annullata', NULL)
  FROM tmp_osa_a a;

-- ============================================================
-- Fixture B) rev.1 EMESSA + rev.2: il trigger z90 porta rev.1 a SUPERATA.
-- ============================================================
CREATE TEMP TABLE tmp_osa_b1 AS
WITH ins AS (
    INSERT INTO vendite.offerte_commerciali (
        emittente_fiscale_id, billing_account_id, istanza_utility_id, utility_id,
        listino_id, listino_versione_id, validita_dal, stato_doc_offerta_id,
        revisione_numero, revisione_padre_id)
    SELECT ctx.emittente_fiscale_id, ctx.billing_account_id, ctx.istanza_utility_id,
           ctx.utility_id, ctx.listino_id, ctx.listino_versione_id,
           DATE '2092-01-01', ctx.stato_bozza_id, 1, NULL
      FROM tmp_osa_ctx ctx
    RETURNING id)
SELECT id FROM ins;

-- rev 2026-10-26 (giro 9): l'emissione dal verbo, non con un UPDATE di stato.
SELECT dbops.fn_pgtap_porta_a_stato('vendite.offerte_commerciali', b1.id, 'EMESSA')
  FROM tmp_osa_b1 b1;

CREATE TEMP TABLE tmp_osa_b2 AS
WITH ins AS (
    INSERT INTO vendite.offerte_commerciali (
        emittente_fiscale_id, billing_account_id, istanza_utility_id, utility_id,
        listino_id, listino_versione_id, validita_dal, stato_doc_offerta_id,
        revisione_numero, revisione_padre_id)
    SELECT ctx.emittente_fiscale_id, ctx.billing_account_id, ctx.istanza_utility_id,
           ctx.utility_id, ctx.listino_id, ctx.listino_versione_id,
           DATE '2092-06-01', ctx.stato_bozza_id, 2, b1.id
      FROM tmp_osa_ctx ctx, tmp_osa_b1 b1
    RETURNING id)
SELECT id FROM ins;

-- ============================================================
-- 7) A: e' l'ULTIMA revisione (nessuno l'ha rimpiazzata) e non e' attiva.
--    E' il caso che la lista non riusciva a mostrare con nessun filtro.
-- ============================================================
SELECT is(
    (SELECT ROW(v.is_attiva, v.is_superata, v.is_abortito, v.has_next_revisione)::text
       FROM vendite.vw_offerte_commerciali_lista v
      WHERE v.id = (SELECT id FROM tmp_osa_a)),
    ROW(false, false, true, false)::text,
    '7) A (ANNULLATA, revisione unica): superata=F (e'' l''ultima revisione) e attiva=F (annullata)'
);

-- ============================================================
-- 8) B rev.1: superamento vero, scritto dal trigger.
-- ============================================================
SELECT is(
    (SELECT ROW(v.is_attiva, v.is_superata, v.is_abortito, v.has_next_revisione)::text
       FROM vendite.vw_offerte_commerciali_lista v
      WHERE v.id = (SELECT id FROM tmp_osa_b1)),
    ROW(false, true, false, true)::text,
    '8) B rev.1 (SUPERATA dal trigger): superata=T, abortito=F, attiva=F, has_next=T'
);

-- ============================================================
-- 9) B rev.2: la viva del lineage.
-- ============================================================
SELECT is(
    (SELECT ROW(v.is_attiva, v.is_superata, v.is_abortito, v.has_next_revisione)::text
       FROM vendite.vw_offerte_commerciali_lista v
      WHERE v.id = (SELECT id FROM tmp_osa_b2)),
    ROW(true, false, false, false)::text,
    '9) B rev.2 (BOZZA in cima): attiva=T, superata=F, abortito=F, has_next=F'
);

-- ============================================================
-- 10) Invariante di composizione sui fixture: is_attiva non e' una terza cosa.
-- ============================================================
SELECT is(
    (SELECT ROW(count(*),
                count(*) FILTER (WHERE
                    v.is_attiva IS DISTINCT FROM
                    ((NOT v.is_superata) AND (NOT v.is_abortito))))::text
       FROM vendite.vw_offerte_commerciali_lista v
      WHERE v.id IN (SELECT id FROM tmp_osa_a
                     UNION ALL SELECT id FROM tmp_osa_b1
                     UNION ALL SELECT id FROM tmp_osa_b2)),
    ROW(3::bigint, 0::bigint)::text,
    '10) 3 offerte fixture viste, zero scarti su is_attiva = NOT is_superata AND NOT is_abortito'
);

-- ============================================================
-- 11) ⭐ I due predicati non selezionano lo stesso insieme: «solo l'ultima
--     revisione» tiene A e B rev.2 (2 righe), is_attiva tiene la sola B rev.2.
--     La differenza e' esattamente l'annullata.
-- ============================================================
SELECT is(
    (SELECT ROW(count(*) FILTER (WHERE NOT v.is_superata),
                count(*) FILTER (WHERE v.is_attiva),
                count(*) FILTER (WHERE (NOT v.is_superata) AND v.is_abortito))::text
       FROM vendite.vw_offerte_commerciali_lista v
      WHERE v.id IN (SELECT id FROM tmp_osa_a
                     UNION ALL SELECT id FROM tmp_osa_b1
                     UNION ALL SELECT id FROM tmp_osa_b2)),
    ROW(2::bigint, 1::bigint, 1::bigint)::text,
    '11) «Solo ultima revisione» = 2 righe, is_attiva = 1: la riga di scarto e'' l''annullata non superata'
);

SELECT * FROM finish();
ROLLBACK;
