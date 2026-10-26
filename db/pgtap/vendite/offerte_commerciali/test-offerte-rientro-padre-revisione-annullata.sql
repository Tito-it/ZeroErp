-- ------------------------------------------------------------
-- SPDX-License-Identifier: GPL-3.0-or-later
-- pgTAP test per Zero ERP
--
-- Test: il RIENTRO del padre quando la revisione che lo superava viene
--       annullata (changeSet 20260828-11/-12/-13, segnalazione BE 2026-08-28).
--
--       Il limite che si chiude: nelle offerte il superamento e' uno STATO, e
--       uno stato non rifluisce. rev1 EMESSA -> crea revisione -> rev1 SUPERATA
--       + rev2 BOZZA -> l'operatore annulla rev2 -> rev1 restava SUPERATA e
--       NESSUNA offerta del lineage risultava attiva: il documento era vivo per
--       il cliente e morto per il sistema. Nei preventivi il caso non esiste
--       perche' li' il superamento e' una relazione e una revisione abortita
--       non rimpiazza nessuno; qui la stessa regola diventa un automatismo.
--
--       ⭐ La meta' che VIETA e' altrettanto in prova (test 7): la transizione
--       SUPERATA->EMESSA e' ora ammessa, quindi senza guard sarebbe una porta
--       aperta per resuscitare un'offerta mentre una revisione viva la sta
--       gia' rimpiazzando — due revisioni vive sullo stesso lineage.
--
--       Fixture (tre lineage indipendenti, costruiti dal test):
--         A) rev1 EMESSA + rev2 BOZZA -> annullo rev2  => rev1 rientra EMESSA
--         B) rev1 EMESSA + rev2 BOZZA (VIVA)           => rientro manuale vietato
--         C) offerta singola BOZZA -> ANNULLATA        => nessun effetto
--
-- rev 2026-10-26 (brief-modello-documento-vendita §13, giro 9): lo stato
--   dell'offerta dal verbo — emissioni con dbops.fn_pgtap_porta_a_stato, annulli
--   con vendite.fn_annulla_offerta (motivazione obbligatoria), invece degli
--   UPDATE di stato che la porta ora rifiuta.
-- ⚠️ Attesa cambiata: test 4-6, il gesto non e' piu' un UPDATE che fa rientrare
--   il padre in silenzio. Con O-4 il padre che torna EMESSA e' un legame
--   dell'annullo della revisione: si annulla con vendite.fn_annulla_offerta
--   confermando 1 legame. Le tre asserzioni sul risultato restano le stesse.
-- ⚠️ Attesa cambiata: test 7, il rientro manuale lo rifiuta il verbo come
--   passaggio di processo (E_DOC_PASSAGGIO_DI_PROCESSO), perche' l'UPDATE
--   diretto non arriva piu' al guard di transizione: lo ferma la porta.
--
-- Indice test (1..9):
--   1)  Struttura: trigger trg_offerte_commerciali_z90_rientro_padre_upd presente
--   2)  Seed: transizione SUPERATA->EMESSA attiva e NON manuale
--   3)  Setup fixture + scope operatore
--   4)  A: annullata la revisione, il padre torna EMESSA
--   5)  A: il lineage ha di nuovo un'offerta attiva (era il difetto)
--   6)  A: il rientro NON riscrive data_emissione
--   7)  B: rientro manuale con una revisione viva -> E_DOC_PASSAGGIO_DI_PROCESSO (dal verbo)
--   8)  C: annullamento di un'offerta senza padre -> nessun rientro, nessun effetto
--   9)  Il codice errore nuovo e' registrato a catalogo, con messaggio
-- ------------------------------------------------------------

BEGIN;
-- ⚠️ Vincoli DIFFERITI: senza questa riga i DEFERRABLE INITIALLY DEFERRED non
--   scatterebbero mai (il COMMIT non arriva: si chiude in ROLLBACK) e il file
--   sarebbe verde per sottrazione.
SET CONSTRAINTS ALL IMMEDIATE;

-- Contesto applicativo: il test gira come gira l'applicazione (OPERATORE + RLS).
DO $ctx$ BEGIN PERFORM script.fn_pgtap_set_contesto_operatore(); END $ctx$;

SELECT plan(9);

-- ============================================================
-- 1) Struttura: il trigger esiste.
--    ⚠️ Prima di ogni asserzione sul comportamento: senza il trigger i test
--    4..6 fallirebbero senza dire che il changeSet non e' applicato.
-- ============================================================
SELECT ok(
    EXISTS (
        SELECT 1
          FROM pg_trigger t
          JOIN pg_class c     ON c.oid = t.tgrelid
          JOIN pg_namespace n ON n.oid = c.relnamespace
         WHERE n.nspname = 'vendite'
           AND c.relname = 'offerte_commerciali'
           AND t.tgname  = 'trg_offerte_commerciali_z90_rientro_padre_upd'
    ),
    '1) trg_offerte_commerciali_z90_rientro_padre_upd presente (20260828-13 applicato)'
);

-- ============================================================
-- 2) Seed: la transizione di rientro esiste, e' attiva e NON e' manuale.
--    Il flag `manuale` governa la visibilita' del pulsante in
--    script.fn_available_actions_offerta: il rientro e' un automatismo, non
--    un gesto che si offre all'operatore.
-- ============================================================
SELECT is(
    (SELECT ROW(t.attivo, COALESCE((t.meta->>'manuale')::boolean, true))::text
       FROM config.stati_doc_offerte_transizioni t
       JOIN config.stati_doc_offerte sda ON sda.id = t.stato_da_id
       JOIN config.stati_doc_offerte sa  ON sa.id  = t.stato_a_id
      WHERE sda.codice_interno = 'SUPERATA'
        AND sa.codice_interno  = 'EMESSA'),
    ROW(true, false)::text,
    '2) transizione SUPERATA->EMESSA seedata, attiva e non manuale'
);

-- ============================================================
-- 3) Setup: contesto fixture + scope operatore (il guard emittente blocca
--    l'INSERT fuori scope, e la vista di lista e' security_invoker).
-- ============================================================
-- 2026-10-08, brief-db-offerta-emissione-ed-erogazione §F.2: il listino del
--   documento e' della sua utility e del suo emittente (guard nuovo); fixture
--   costruito invece che preso dai dati. Cliente DOPO il contesto: il z90 lega
--   il BA all'emittente di chi agisce, lo stesso del listino.
CREATE TEMP TABLE tmp_rp_cli AS
SELECT * FROM dbops.fn_pgtap_crea_cliente_ba(
    'rientro padre revisione annullata',
    (SELECT u.id FROM config.utilities u
      WHERE NOT EXISTS (SELECT 1 FROM config.tipi_utenze tu WHERE tu.utility_id = u.id)
      ORDER BY u.id LIMIT 1));

CREATE TEMP TABLE tmp_rp_lis AS
SELECT * FROM dbops.fn_pgtap_crea_listino(
    (SELECT utility_id FROM tmp_rp_cli), 'rientro padre revisione annullata');

CREATE TEMP TABLE tmp_rp_ctx AS
SELECT
    (SELECT billing_account_id FROM tmp_rp_cli)   AS billing_account_id,
    (SELECT istanza_utility_id FROM tmp_rp_cli)   AS istanza_utility_id,
    (SELECT utility_id FROM tmp_rp_cli)           AS utility_id,
    script.fn_pgtap_emittente_operatore()         AS emittente_fiscale_id,
    (SELECT listino_id FROM tmp_rp_lis)           AS listino_id,
    (SELECT listino_versione_id FROM tmp_rp_lis)  AS listino_versione_id,
    (SELECT id FROM config.stati_doc_offerte WHERE codice_interno = 'BOZZA')     AS stato_bozza_id,
    (SELECT id FROM config.stati_doc_offerte WHERE codice_interno = 'EMESSA')    AS stato_emessa_id,
    (SELECT id FROM config.stati_doc_offerte WHERE codice_interno = 'ANNULLATA') AS stato_annullata_id,
    (SELECT id FROM config.stati_doc_offerte WHERE codice_interno = 'SUPERATA')  AS stato_superata_id;

CREATE TEMP TABLE tmp_rp_op AS
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
        AND ctx.listino_versione_id IS NOT NULL
        AND ctx.stato_bozza_id IS NOT NULL AND ctx.stato_emessa_id IS NOT NULL
        AND ctx.stato_annullata_id IS NOT NULL AND ctx.stato_superata_id IS NOT NULL
        AND (SELECT user_id FROM tmp_rp_op) IS NOT NULL
       FROM tmp_rp_ctx ctx),
    '3) Fixture context completo (BA, emittente, listino/versione, 4 stati) + operatore non-super'
);

SET LOCAL zeroerp.allow_user_emittente_delete_override = 'on';
DELETE FROM config.user_emittenti_fiscali
 WHERE auth_user_id = (SELECT user_id FROM tmp_rp_op);
SET LOCAL zeroerp.allow_user_emittente_delete_override = '';

INSERT INTO config.user_emittenti_fiscali (auth_user_id, emittente_fiscale_id, meta)
SELECT o.user_id, ctx.emittente_fiscale_id,
       '{"test_scope":"pgtap_rientro_padre"}'::jsonb
  FROM tmp_rp_op o, tmp_rp_ctx ctx;

SELECT set_config('app.current_user_id',
    (SELECT user_id::text FROM tmp_rp_op), true);

-- ============================================================
-- Lineage A: rev1 EMESSA -> rev2 (il trigger porta rev1 a SUPERATA)
-- ============================================================
CREATE TEMP TABLE tmp_rp_a1 AS
WITH ins AS (
    INSERT INTO vendite.offerte_commerciali (
        emittente_fiscale_id, billing_account_id, istanza_utility_id, utility_id,
        listino_id, listino_versione_id, validita_dal, stato_doc_offerta_id,
        revisione_numero, revisione_padre_id)
    SELECT ctx.emittente_fiscale_id, ctx.billing_account_id, ctx.istanza_utility_id,
           ctx.utility_id, ctx.listino_id, ctx.listino_versione_id,
           DATE '2097-01-01', ctx.stato_bozza_id, 1, NULL
      FROM tmp_rp_ctx ctx
    RETURNING id)
SELECT id FROM ins;

-- rev 2026-10-26 (giro 9): l'emissione dal verbo, non con un UPDATE di stato.
SELECT dbops.fn_pgtap_porta_a_stato('vendite.offerte_commerciali', r.id, 'EMESSA')
  FROM tmp_rp_a1 r;

-- ⚠️ data_emissione fissata a un valore DISTINTO da now(): dentro una
--    transazione now() e' costante, quindi confrontare "prima e dopo" senza
--    questo passo sarebbe verde comunque — il test non proverebbe niente.
UPDATE vendite.offerte_commerciali
   SET data_emissione = TIMESTAMPTZ '2097-02-03 08:00:00+01'
 WHERE id = (SELECT id FROM tmp_rp_a1);

CREATE TEMP TABLE tmp_rp_a2 AS
WITH ins AS (
    INSERT INTO vendite.offerte_commerciali (
        emittente_fiscale_id, billing_account_id, istanza_utility_id, utility_id,
        listino_id, listino_versione_id, validita_dal, stato_doc_offerta_id,
        revisione_numero, revisione_padre_id)
    SELECT ctx.emittente_fiscale_id, ctx.billing_account_id, ctx.istanza_utility_id,
           ctx.utility_id, ctx.listino_id, ctx.listino_versione_id,
           DATE '2097-06-01', ctx.stato_bozza_id, 2, a1.id
      FROM tmp_rp_ctx ctx, tmp_rp_a1 a1
    RETURNING id)
SELECT id FROM ins;

-- Il gesto in prova: l'operatore annulla la revisione (BOZZA -> ANNULLATA,
-- l'unica transizione di annullamento che il catalogo ammette).
-- ⚠️ rev 2026-10-26 (giro 9, O-4): il rientro non e' piu' silenzioso. Il padre
--   che torna EMESSA e' un LEGAME dell'annullo (vendite.fn_documento_legami:
--   una riga, PROVENIENZA): l'annullo passa dal verbo vendite.fn_annulla_offerta,
--   che chiede la motivazione e la conferma di quel legame (1).
SELECT vendite.fn_annulla_offerta(a2.id, 'pgTAP: revisione annullata', 1)
  FROM tmp_rp_a2 a2;

-- ============================================================
-- 4) Il padre e' rientrato in EMESSA.
-- ============================================================
SELECT is(
    (SELECT s.codice_interno
       FROM vendite.offerte_commerciali o
       JOIN config.stati_doc_offerte s ON s.id = o.stato_doc_offerta_id
      WHERE o.id = (SELECT id FROM tmp_rp_a1)),
    'EMESSA'::character varying,
    '4) A: annullata la revisione senza successore, il padre torna EMESSA (era SUPERATA)'
);

-- ============================================================
-- 5) ⭐ Il lineage ha di nuovo esattamente un'offerta attiva. E' il difetto
--    segnalato: prima non ne aveva NESSUNA.
-- ============================================================
SELECT is(
    (SELECT ROW(count(*) FILTER (WHERE v.is_attiva),
                count(*) FILTER (WHERE NOT v.is_superata),
                count(*) FILTER (WHERE v.is_abortito))::text
       FROM vendite.vw_offerte_commerciali_lista v
      WHERE v.id IN (SELECT id FROM tmp_rp_a1 UNION ALL SELECT id FROM tmp_rp_a2)),
    ROW(1::bigint, 2::bigint, 1::bigint)::text,
    '5) A: il lineage ha 1 offerta attiva (il padre), nessuna superata, 1 annullata'
);

-- ============================================================
-- 6) Il rientro NON riscrive data_emissione: quella data dice quando
--    l'offerta e' stata mandata al cliente, e non e' oggi.
-- ============================================================
SELECT is(
    (SELECT o.data_emissione
       FROM vendite.offerte_commerciali o
      WHERE o.id = (SELECT id FROM tmp_rp_a1)),
    TIMESTAMPTZ '2097-02-03 08:00:00+01',
    '6) A: data_emissione preservata dal rientro (non riscritta con now())'
);

-- ============================================================
-- Lineage B: rev1 EMESSA + rev2 BOZZA ANCORA VIVA
-- ============================================================
CREATE TEMP TABLE tmp_rp_b1 AS
WITH ins AS (
    INSERT INTO vendite.offerte_commerciali (
        emittente_fiscale_id, billing_account_id, istanza_utility_id, utility_id,
        listino_id, listino_versione_id, validita_dal, stato_doc_offerta_id,
        revisione_numero, revisione_padre_id)
    SELECT ctx.emittente_fiscale_id, ctx.billing_account_id, ctx.istanza_utility_id,
           ctx.utility_id, ctx.listino_id, ctx.listino_versione_id,
           DATE '2098-01-01', ctx.stato_bozza_id, 1, NULL
      FROM tmp_rp_ctx ctx
    RETURNING id)
SELECT id FROM ins;

-- rev 2026-10-26 (giro 9): l'emissione dal verbo, non con un UPDATE di stato.
SELECT dbops.fn_pgtap_porta_a_stato('vendite.offerte_commerciali', r.id, 'EMESSA')
  FROM tmp_rp_b1 r;

INSERT INTO vendite.offerte_commerciali (
    emittente_fiscale_id, billing_account_id, istanza_utility_id, utility_id,
    listino_id, listino_versione_id, validita_dal, stato_doc_offerta_id,
    revisione_numero, revisione_padre_id)
SELECT ctx.emittente_fiscale_id, ctx.billing_account_id, ctx.istanza_utility_id,
       ctx.utility_id, ctx.listino_id, ctx.listino_versione_id,
       DATE '2098-06-01', ctx.stato_bozza_id, 2, b1.id
  FROM tmp_rp_ctx ctx, tmp_rp_b1 b1;

-- ============================================================
-- 7) ⭐ La transizione ora ESISTE, quindi la porta va chiusa da una regola:
--    con una revisione figlia ancora viva il rientro e' rifiutato, da
--    chiunque lo tenti.
--    ⚠️ rev 2026-10-26 (giro 9): un UPDATE di stato lo ferma ormai la porta
--    (E_DOC_STATO_SOLO_DAL_VERBO, P0001 anche lei: throws_ok sul solo SQLSTATE
--    sarebbe verde per la ragione sbagliata). Chi tenta il rientro a mano lo
--    chiede al verbo, e il verbo lo rifiuta perche' SUPERATA -> EMESSA e' un
--    passaggio di PROCESSO (E_DOC_PASSAGGIO_DI_PROCESSO): lo scrive solo la
--    proiezione vendite.fn_offerta_proietta_stato_revisione, che con una
--    revisione viva non lo chiede. La regola E_OFFERTA_RIENTRO_CON_REVISIONE_VIVA
--    resta nel guard di transizione, dietro la porta.
-- ============================================================
SELECT throws_like(
    format(
      $q$SELECT * FROM vendite.fn_cambia_stato_offerta(%s, 'EMESSA', NULL)$q$,
      (SELECT id FROM tmp_rp_b1)
    ),
    '%non si chiede a mano%',
    '7) B: rientro manuale con una revisione viva -> rifiutato dal verbo (E_DOC_PASSAGGIO_DI_PROCESSO)'
);

-- ============================================================
-- Lineage C: offerta singola, senza padre. L'annullamento non deve toccare
-- niente e nessuno.
-- ============================================================
CREATE TEMP TABLE tmp_rp_c AS
WITH ins AS (
    INSERT INTO vendite.offerte_commerciali (
        emittente_fiscale_id, billing_account_id, istanza_utility_id, utility_id,
        listino_id, listino_versione_id, validita_dal, stato_doc_offerta_id,
        revisione_numero, revisione_padre_id)
    SELECT ctx.emittente_fiscale_id, ctx.billing_account_id, ctx.istanza_utility_id,
           ctx.utility_id, ctx.listino_id, ctx.listino_versione_id,
           DATE '2099-01-01', ctx.stato_bozza_id, 1, NULL
      FROM tmp_rp_ctx ctx
    RETURNING id)
SELECT id FROM ins;

-- Fotografia degli stati del lineage B PRIMA dell'annullamento di C: nessuno
-- di essi deve muoversi.
CREATE TEMP TABLE tmp_rp_b_ante AS
SELECT o.id, o.stato_doc_offerta_id
  FROM vendite.offerte_commerciali o
 WHERE o.id = (SELECT id FROM tmp_rp_b1)
    OR o.revisione_padre_id = (SELECT id FROM tmp_rp_b1);

-- rev 2026-10-26 (giro 9): l'annullo dal verbo, con la motivazione; nessun
--   legame da confermare (NULL), perche' C non ha padre.
SELECT vendite.fn_annulla_offerta(c.id, 'pgTAP: offerta annullata', NULL)
  FROM tmp_rp_c c;

SELECT is(
    (SELECT ROW(
              -- C e' annullata, e resta l'unica riga toccata
              (SELECT s.codice_interno FROM vendite.offerte_commerciali o
                 JOIN config.stati_doc_offerte s ON s.id = o.stato_doc_offerta_id
                WHERE o.id = (SELECT id FROM tmp_rp_c)),
              -- quante righe del lineage B hanno cambiato stato: zero
              (SELECT count(*) FROM tmp_rp_b_ante a
                 JOIN vendite.offerte_commerciali o ON o.id = a.id
                WHERE o.stato_doc_offerta_id IS DISTINCT FROM a.stato_doc_offerta_id),
              -- e le righe confrontate non sono zero (niente verde per sottrazione)
              (SELECT count(*) FROM tmp_rp_b_ante)
            )::text),
    ROW('ANNULLATA'::character varying, 0::bigint, 2::bigint)::text,
    '8) C: annullata un''offerta senza padre — nessun rientro, 2 righe del lineage B confrontate e immobili'
);

-- ============================================================
-- 9) Il codice nuovo e' a catalogo con il suo messaggio. Un codice non
--    registrato cadrebbe sul fallback 400 del backend, mentre qui la
--    risposta giusta e' 409 (CONFLITTO_STATO).
-- ============================================================
SELECT is(
    (SELECT ROW(c.classe, (m.messaggio IS NOT NULL))::text
       FROM config.codici_errore c
       LEFT JOIN config.messaggi_errore m
              ON m.codice = c.codice AND m.lingua = 'it'
      WHERE c.codice = 'E_OFFERTA_RIENTRO_CON_REVISIONE_VIVA'),
    ROW('CONFLITTO_STATO', true)::text,
    '9) E_OFFERTA_RIENTRO_CON_REVISIONE_VIVA registrato come CONFLITTO_STATO, con messaggio it'
);

SELECT * FROM finish();
ROLLBACK;
