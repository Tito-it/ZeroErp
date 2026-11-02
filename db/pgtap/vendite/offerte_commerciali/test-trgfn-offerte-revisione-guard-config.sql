-- ------------------------------------------------------------
-- SPDX-License-Identifier: AGPL-3.0-or-later
-- pgTAP test per Zero ERP
--
-- Test: vendite.trgfn_offerte_commerciali_revisione — il guard sull'ARITA' del
--       catalogo (changeSet 20260828-11, segnalazione BE 2026-08-28).
--
--       Il fatto: la funzione risolveva lo stato di superamento con un
--       `SELECT ... INTO`, che NON solleva niente quando non trova la riga —
--       azzera la variabile. Con lo stato assente, l'UPDATE del padre provava a
--       scrivere NULL su una colonna NOT NULL e l'errore arrivava lo stesso, ma
--       era un 23502 di PostgreSQL: nominava una COLONNA mentre la verita' era
--       una riga di catalogo mancante. Non un errore assente — un errore che
--       racconta la storia sbagliata, e manda a cercare il bug dove non e'.
--
--       ⭐ Il guard e' sull'arita', non sulla sola assenza: con DUE stati
--       marcati is_superato, un SELECT INTO senza STRICT ne sceglierebbe uno a
--       caso, in silenzio. Zero e due sono lo stesso difetto — il catalogo non
--       dice quale — e il test li prova entrambi.
--
-- pgtap-runner: owner
-- pgtap-runner-motivo: la fixture deve costruire un CATALOGO rotto (zero, poi
--   due stati con is_superato) — config.stati_doc_offerte non e' scrivibile
--   dall'applicazione, e non deve esserlo. E' la forma 2 del criterio in
--   scripts/testpgtap.sh: il soggetto del test non sta sul percorso
--   applicativo, quindi fingere di essere l'applicazione lo renderebbe muto.
--   ⚠️ Ne discende che questo file NON esercita nessuna policy RLS: la
--   copertura RLS del dominio offerte sta negli altri file della cartella.
--
-- rev 2026-10-26 (brief-modello-documento-vendita §13, giro 9): lo stato
--   dell'offerta dal verbo — i due padri si emettono con
--   dbops.fn_pgtap_porta_a_stato invece dell'UPDATE di stato, che la porta ora
--   rifiuta. Il superamento del padre lo fa ora la proiezione
--   (vendite.fn_offerta_proietta_stato_revisione), che porta lo stesso guard.
--
-- Indice test (1..4):
--   1)  Setup fixture: un'offerta EMESSA revisionabile
--   2)  Catalogo SANO: l'inserimento della revisione porta il padre a SUPERATA
--   3)  Catalogo con ZERO stati di superamento -> E_CONFIG_MANCANTE (P0001),
--       non piu' un 23502 che nomina la colonna
--   4)  Catalogo con DUE stati di superamento -> stesso errore, nessuna scelta
--       silenziosa
-- ------------------------------------------------------------

BEGIN;
-- ⚠️ Vincoli DIFFERITI: senza questa riga i DEFERRABLE INITIALLY DEFERRED non
--   scatterebbero mai (il COMMIT non arriva: si chiude in ROLLBACK) e il file
--   sarebbe verde per sottrazione.
SET CONSTRAINTS ALL IMMEDIATE;

-- Contesto applicativo: presente anche girando da owner. L'identita' la
-- portano le GUC `app.*`, non il ruolo di connessione — e i guard di scope
-- sulle offerte la leggono da li'.
DO $ctx$ BEGIN PERFORM script.fn_pgtap_set_contesto_operatore(); END $ctx$;

SELECT plan(4);

-- ============================================================
-- 1) Fixture: un'offerta portata in EMESSA, pronta a essere revisionata.
-- ============================================================
-- 2026-10-08, brief-db-offerta-emissione-ed-erogazione §F.2: il listino del
--   documento e' della sua utility e del suo emittente (guard nuovo); fixture
--   costruito invece che preso dai dati. Cliente su una utility senza
--   tipi_utenze, legato dal z90 all'emittente di chi agisce; listino e
--   versione ATTIVA dal builder, sulla stessa utility; emittente di chi agisce.
--   ⛔ Cio' che i builder scrivono si legge in un'istruzione SEPARATA.
CREATE TEMP TABLE tmp_gc_cli AS
SELECT * FROM dbops.fn_pgtap_crea_cliente_ba(
    'revisione guard config',
    (SELECT u.id FROM config.utilities u
      WHERE NOT EXISTS (SELECT 1 FROM config.tipi_utenze tu WHERE tu.utility_id = u.id)
      ORDER BY u.id LIMIT 1));

CREATE TEMP TABLE tmp_gc_listino AS
SELECT * FROM dbops.fn_pgtap_crea_listino(
    (SELECT utility_id FROM tmp_gc_cli), 'revisione guard config');

CREATE TEMP TABLE tmp_gc_ctx AS
SELECT
    (SELECT billing_account_id FROM tmp_gc_cli) AS billing_account_id,
    (SELECT istanza_utility_id FROM tmp_gc_cli) AS istanza_utility_id,
    (SELECT utility_id FROM tmp_gc_cli) AS utility_id,
    script.fn_pgtap_emittente_operatore() AS emittente_fiscale_id,
    (SELECT listino_id FROM tmp_gc_listino) AS listino_id,
    (SELECT listino_versione_id FROM tmp_gc_listino) AS listino_versione_id,
    (SELECT id FROM config.stati_doc_offerte WHERE codice_interno = 'BOZZA')     AS stato_bozza_id,
    (SELECT id FROM config.stati_doc_offerte WHERE codice_interno = 'EMESSA')    AS stato_emessa_id,
    (SELECT id FROM config.stati_doc_offerte WHERE codice_interno = 'ACCETTATA') AS stato_accettata_id,
    (SELECT id FROM config.stati_doc_offerte WHERE codice_interno = 'SUPERATA')  AS stato_superata_id;

CREATE TEMP TABLE tmp_gc_padre AS
WITH ins AS (
    INSERT INTO vendite.offerte_commerciali (
        emittente_fiscale_id, billing_account_id, istanza_utility_id, utility_id,
        listino_id, listino_versione_id, validita_dal, stato_doc_offerta_id,
        revisione_numero, revisione_padre_id)
    SELECT ctx.emittente_fiscale_id, ctx.billing_account_id, ctx.istanza_utility_id,
           ctx.utility_id, ctx.listino_id, ctx.listino_versione_id,
           DATE '2095-01-01', ctx.stato_bozza_id, 1, NULL
      FROM tmp_gc_ctx ctx
    RETURNING id)
SELECT id FROM ins;

-- rev 2026-10-26 (giro 9): l'emissione dal verbo, non con un UPDATE di stato.
SELECT dbops.fn_pgtap_porta_a_stato('vendite.offerte_commerciali', p.id, 'EMESSA')
  FROM tmp_gc_padre p;

SELECT ok(
    (SELECT o.stato_doc_offerta_id = ctx.stato_emessa_id
       FROM vendite.offerte_commerciali o, tmp_gc_ctx ctx
      WHERE o.id = (SELECT id FROM tmp_gc_padre)),
    '1) Fixture: offerta padre in EMESSA, revisionabile'
);

-- ============================================================
-- 2) Catalogo SANO — il caso normale continua a funzionare.
--    ⚠️ Va provato PRIMA di rompere il catalogo: senza, i test 3 e 4 direbbero
--    solo «qualcosa fallisce», non «fallisce PER il catalogo».
-- ============================================================
INSERT INTO vendite.offerte_commerciali (
    emittente_fiscale_id, billing_account_id, istanza_utility_id, utility_id,
    listino_id, listino_versione_id, validita_dal, stato_doc_offerta_id,
    revisione_numero, revisione_padre_id)
SELECT ctx.emittente_fiscale_id, ctx.billing_account_id, ctx.istanza_utility_id,
       ctx.utility_id, ctx.listino_id, ctx.listino_versione_id,
       DATE '2095-06-01', ctx.stato_bozza_id, 2, p.id
  FROM tmp_gc_ctx ctx, tmp_gc_padre p;

SELECT is(
    (SELECT s.codice_interno
       FROM vendite.offerte_commerciali o
       JOIN config.stati_doc_offerte s ON s.id = o.stato_doc_offerta_id
      WHERE o.id = (SELECT id FROM tmp_gc_padre)),
    'SUPERATA'::character varying,
    '2) Catalogo sano: inserita la revisione, il padre passa a SUPERATA'
);

-- Un secondo padre, per i due casi rotti (il primo e' ormai SUPERATA).
CREATE TEMP TABLE tmp_gc_padre2 AS
WITH ins AS (
    INSERT INTO vendite.offerte_commerciali (
        emittente_fiscale_id, billing_account_id, istanza_utility_id, utility_id,
        listino_id, listino_versione_id, validita_dal, stato_doc_offerta_id,
        revisione_numero, revisione_padre_id)
    SELECT ctx.emittente_fiscale_id, ctx.billing_account_id, ctx.istanza_utility_id,
           ctx.utility_id, ctx.listino_id, ctx.listino_versione_id,
           DATE '2096-01-01', ctx.stato_bozza_id, 1, NULL
      FROM tmp_gc_ctx ctx
    RETURNING id)
SELECT id FROM ins;

-- rev 2026-10-26 (giro 9): l'emissione dal verbo, non con un UPDATE di stato.
SELECT dbops.fn_pgtap_porta_a_stato('vendite.offerte_commerciali', p.id, 'EMESSA')
  FROM tmp_gc_padre2 p;

-- ============================================================
-- 3) ZERO stati di superamento. Prima: v_stato_superata_id restava NULL e
--    l'UPDATE del padre sbatteva sul NOT NULL (23502, classe 23). Ora:
--    errore di dominio P0001 con E_CONFIG_MANCANTE, che nomina il catalogo.
--    ⚠️ Lo SQLSTATE e' l'asserzione vera: senza, throws_ok accetterebbe anche
--    il 23502 di prima e il test sarebbe verde sul difetto.
-- ============================================================
UPDATE config.stati_doc_offerte SET is_superato = false WHERE is_superato IS TRUE;

SELECT throws_ok(
    format(
      'INSERT INTO vendite.offerte_commerciali (emittente_fiscale_id, billing_account_id,'
      ' istanza_utility_id, utility_id, listino_id, listino_versione_id, validita_dal,'
      ' stato_doc_offerta_id, revisione_numero, revisione_padre_id)'
      ' VALUES (%s, %s, %s, %s, %s, %s, DATE ''2096-06-01'', %s, 2, %s)',
      (SELECT emittente_fiscale_id FROM tmp_gc_ctx),
      (SELECT billing_account_id   FROM tmp_gc_ctx),
      (SELECT istanza_utility_id   FROM tmp_gc_ctx),
      (SELECT utility_id           FROM tmp_gc_ctx),
      (SELECT listino_id           FROM tmp_gc_ctx),
      (SELECT listino_versione_id  FROM tmp_gc_ctx),
      (SELECT stato_bozza_id       FROM tmp_gc_ctx),
      (SELECT id FROM tmp_gc_padre2)
    ),
    'P0001',
    NULL,
    '3) Zero stati is_superato -> errore di dominio (P0001), non il 23502 sulla colonna'
);

-- ============================================================
-- 4) DUE stati di superamento. Senza il guard sull'arita' il trigger
--    sceglierebbe in silenzio, e il padre finirebbe in uno stato deciso
--    dall'ordine delle righe.
-- ============================================================
UPDATE config.stati_doc_offerte SET is_superato = true
 WHERE codice_interno IN ('SUPERATA', 'ACCETTATA');

SELECT throws_ok(
    format(
      'INSERT INTO vendite.offerte_commerciali (emittente_fiscale_id, billing_account_id,'
      ' istanza_utility_id, utility_id, listino_id, listino_versione_id, validita_dal,'
      ' stato_doc_offerta_id, revisione_numero, revisione_padre_id)'
      ' VALUES (%s, %s, %s, %s, %s, %s, DATE ''2096-09-01'', %s, 2, %s)',
      (SELECT emittente_fiscale_id FROM tmp_gc_ctx),
      (SELECT billing_account_id   FROM tmp_gc_ctx),
      (SELECT istanza_utility_id   FROM tmp_gc_ctx),
      (SELECT utility_id           FROM tmp_gc_ctx),
      (SELECT listino_id           FROM tmp_gc_ctx),
      (SELECT listino_versione_id  FROM tmp_gc_ctx),
      (SELECT stato_bozza_id       FROM tmp_gc_ctx),
      (SELECT id FROM tmp_gc_padre2)
    ),
    'P0001',
    NULL,
    '4) Due stati is_superato -> stesso errore di dominio: nessuna scelta silenziosa'
);

SELECT * FROM finish();
ROLLBACK;
