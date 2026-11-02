-- ------------------------------------------------------------
-- SPDX-License-Identifier: AGPL-3.0-or-later
-- pgTAP test per Zero ERP
--
-- Test: una mail si tocca solo in bozza — gli allegati
--   (config.trgfn_email_allegato_guard_solo_bozza) e la cancellazione della
--   bozza (vendite.trgfn_doc_guard_delete_solo_bozza, ramo email).
-- ChangeSet: 20260925-71..-74 · Brief: brief-db-email-visibilita-per-ambito §8
--
-- Elenco test (plan 13):
--   1) forma: i due trigger montati, con le funzioni giuste
--   2) catalogo: E_EMAIL_ALLEGATO_NON_BOZZA, CONFLITTO_STATO, vivo
--   3) bozza DRAFT: aggiungere, modificare e togliere un allegato PASSA
--   4) ⭐ bozza READY: l'aggancio al log (solo email_log_id) PASSA
--   5) bozza READY: modificare altro -> rifiutato, verbo «modificare»
--   6) mail SENT: togliere un allegato -> rifiutato, verbo «togliere»
--   7) mail SENT: aggiungere un allegato -> rifiutato, verbo «aggiungere»
--   8) mail SENT: spostare un suo allegato su una bozza DRAFT -> rifiutato
--   9) invio fallito, bozza tornata DRAFT col log: l'allegato si toglie,
--      e il nuovo tentativo lo riaggancia
--  10) un allegato non nasce direttamente sul log, senza bozza
--  11) mail SENT: la bozza non si elimina (E_DELETE_DOC_NON_BOZZA)
--  12) bozza CANCELLED: non si elimina
--  13) bozza DRAFT: si elimina, e i suoi allegati la seguono (il cascade passa)
--
-- ⚠️ I RIFIUTI SI CATTURANO (SQLSTATE + frase + verbo), non con un throws_ok
--   a P0001 nudo: cosi' si asserisce CHI ha rifiutato. La RLS non e' in gioco:
--   ogni riga e' dell'operatore di contesto (OPERATORE, autore lui stesso).
-- ------------------------------------------------------------

BEGIN;

SET CONSTRAINTS ALL IMMEDIATE;

-- Il mondo PRIMA del contesto: un'azienda e il suo operatore.
CREATE TEMP TABLE _az AS SELECT * FROM dbops.fn_pgtap_crea_emittente_operatore();

DO $ctx$
BEGIN
    PERFORM script.fn_pgtap_set_contesto_operatore((SELECT auth_user_id FROM _az));
END $ctx$;

CREATE TEMP TABLE _id (nome text PRIMARY KEY, id bigint);
CREATE TEMP TABLE _esito (caso text PRIMARY KEY, sqlstate text, messaggio text, righe int);

-- Una bozza OPERATORE DRAFT dell'operatore di contesto; lo stato si cambia dopo.
CREATE FUNCTION pg_temp.bozza(p_nome text) RETURNS bigint
LANGUAGE plpgsql AS $$
DECLARE v_id bigint;
BEGIN
    INSERT INTO config.email_outbox
        (destinatario, oggetto, corpo_html, ambito, emittente_fiscale_id, creato_da_user_id)
    VALUES ('pgtap@example.invalid', 'pgtap ' || p_nome, '<p/>', 'OPERATORE',
            (SELECT emittente_fiscale_id FROM _az), (SELECT auth_user_id FROM _az))
    RETURNING id INTO v_id;
    INSERT INTO _id VALUES (p_nome, v_id);
    RETURN v_id;
END $$;

CREATE FUNCTION pg_temp.allegato(p_nome text, p_bozza text) RETURNS bigint
LANGUAGE plpgsql AS $$
DECLARE v_id bigint;
BEGIN
    INSERT INTO config.email_allegato
        (email_outbox_id, nome_file, mime_type, dimensione_bytes, file_path)
    VALUES ((SELECT id FROM _id WHERE nome = p_bozza),
            p_nome || '.pdf', 'application/pdf', 1, 'pgtap/' || p_nome || '.pdf')
    RETURNING id INTO v_id;
    INSERT INTO _id VALUES (p_nome, v_id);
    RETURN v_id;
END $$;

CREATE FUNCTION pg_temp.log(p_nome text) RETURNS bigint
LANGUAGE plpgsql AS $$
DECLARE v_id bigint;
BEGIN
    INSERT INTO config.email_log
        (destinatario, oggetto, stato, ambito, emittente_fiscale_id, creato_da_user_id)
    VALUES ('pgtap@example.invalid', 'pgtap ' || p_nome, 'FAILED', 'OPERATORE',
            (SELECT emittente_fiscale_id FROM _az), (SELECT auth_user_id FROM _az))
    RETURNING id INTO v_id;
    INSERT INTO _id VALUES (p_nome, v_id);
    RETURN v_id;
END $$;

CREATE FUNCTION pg_temp.stato(p_bozza text, p_stato text) RETURNS void
LANGUAGE sql AS $$
    UPDATE config.email_outbox SET stato = p_stato WHERE id = (SELECT id FROM _id WHERE nome = p_bozza);
$$;

CREATE FUNCTION pg_temp.prova(p_caso text, p_sql text) RETURNS void
LANGUAGE plpgsql AS $$
DECLARE v_n int;
BEGIN
    BEGIN
        EXECUTE p_sql;
        GET DIAGNOSTICS v_n = ROW_COUNT;
        INSERT INTO _esito VALUES (p_caso, NULL, NULL, v_n);
    EXCEPTION WHEN OTHERS THEN
        INSERT INTO _esito VALUES (p_caso, SQLSTATE, SQLERRM, NULL);
    END;
END $$;

-- Il verdetto del guard degli allegati: SQLSTATE di dominio, la frase, il verbo.
CREATE FUNCTION pg_temp.rifiuto(p_caso text, p_verbo text) RETURNS boolean
LANGUAGE sql AS $$
    SELECT coalesce(e.sqlstate = 'P0001'
       AND e.messaggio LIKE '%non e'' piu'' in bozza%'
       AND e.messaggio LIKE '%i suoi allegati si possono ' || p_verbo || ' solo finche''%', false)
      FROM _esito e WHERE e.caso = p_caso
$$;

CREATE FUNCTION pg_temp.passa(p_caso text) RETURNS boolean
LANGUAGE sql AS $$
    SELECT coalesce(e.sqlstate IS NULL AND e.righe = 1, false) FROM _esito e WHERE e.caso = p_caso
$$;

-- Scorciatoia per l'id di un nome della fixture, dentro l'SQL delle prove.
CREATE FUNCTION pg_temp.i(p_nome text) RETURNS bigint
LANGUAGE sql AS $$ SELECT id FROM _id WHERE nome = p_nome $$;

-- ── Le prove ────────────────────────────────────────────────────
-- 3) bozza DRAFT: le tre porte passano
SELECT pg_temp.bozza('B_DRAFT');
SELECT pg_temp.allegato('A_DRAFT', 'B_DRAFT');
SELECT pg_temp.prova('3_ins', format(
    $$INSERT INTO config.email_allegato (email_outbox_id, nome_file, mime_type, dimensione_bytes, file_path)
      VALUES (%s, 'x.pdf', 'application/pdf', 1, 'pgtap/x.pdf')$$, pg_temp.i('B_DRAFT')));
SELECT pg_temp.prova('3_upd', format(
    $$UPDATE config.email_allegato SET nome_file = 'rinominato.pdf' WHERE id = %s$$, pg_temp.i('A_DRAFT')));
SELECT pg_temp.prova('3_dlt', format(
    $$DELETE FROM config.email_allegato WHERE id = %s$$, pg_temp.i('A_DRAFT')));

-- 4..5) bozza READY: l'aggancio passa, il resto no
SELECT pg_temp.bozza('B_INVIO');
SELECT pg_temp.allegato('A_INVIO', 'B_INVIO');
SELECT pg_temp.log('L_INVIO');
SELECT pg_temp.stato('B_INVIO', 'READY');
SELECT pg_temp.prova('4_aggancio', format(
    $$UPDATE config.email_allegato SET email_log_id = %s WHERE id = %s$$,
    pg_temp.i('L_INVIO'), pg_temp.i('A_INVIO')));
SELECT pg_temp.prova('5_ready_upd', format(
    $$UPDATE config.email_allegato SET nome_file = 'dopo.pdf' WHERE id = %s$$, pg_temp.i('A_INVIO')));

-- 6..8) mail SENT
SELECT pg_temp.stato('B_INVIO', 'SENT');
SELECT pg_temp.prova('6_sent_dlt', format(
    $$DELETE FROM config.email_allegato WHERE id = %s$$, pg_temp.i('A_INVIO')));
SELECT pg_temp.prova('7_sent_ins', format(
    $$INSERT INTO config.email_allegato (email_outbox_id, nome_file, mime_type, dimensione_bytes, file_path)
      VALUES (%s, 'tardi.pdf', 'application/pdf', 1, 'pgtap/tardi.pdf')$$, pg_temp.i('B_INVIO')));
SELECT pg_temp.bozza('B_ALTRA');
SELECT pg_temp.prova('8_sent_sposta', format(
    $$UPDATE config.email_allegato SET email_outbox_id = %s WHERE id = %s$$,
    pg_temp.i('B_ALTRA'), pg_temp.i('A_INVIO')));

-- 9) invio fallito: la bozza torna DRAFT con il log del tentativo
SELECT pg_temp.bozza('B_FALLITA');
SELECT pg_temp.allegato('A_FALLITA_1', 'B_FALLITA');
SELECT pg_temp.allegato('A_FALLITA_2', 'B_FALLITA');
SELECT pg_temp.log('L_FALLITO');
SELECT pg_temp.stato('B_FALLITA', 'READY');
UPDATE config.email_allegato SET email_log_id = pg_temp.i('L_FALLITO')
 WHERE email_outbox_id = pg_temp.i('B_FALLITA');
SELECT pg_temp.stato('B_FALLITA', 'DRAFT');
SELECT pg_temp.prova('9_fallita_dlt', format(
    $$DELETE FROM config.email_allegato WHERE id = %s$$, pg_temp.i('A_FALLITA_1')));
SELECT pg_temp.log('L_RIPROVA');
SELECT pg_temp.stato('B_FALLITA', 'READY');
SELECT pg_temp.prova('9_riaggancio', format(
    $$UPDATE config.email_allegato SET email_log_id = %s WHERE id = %s$$,
    pg_temp.i('L_RIPROVA'), pg_temp.i('A_FALLITA_2')));

-- 10) un allegato non nasce sul log
SELECT pg_temp.prova('10_solo_log', format(
    $$INSERT INTO config.email_allegato (email_log_id, nome_file, mime_type, dimensione_bytes, file_path)
      VALUES (%s, 'storia.pdf', 'application/pdf', 1, 'pgtap/storia.pdf')$$, pg_temp.i('L_INVIO')));

-- 11..13) la bozza stessa
SELECT pg_temp.prova('11_sent_elimina', format(
    $$DELETE FROM config.email_outbox WHERE id = %s$$, pg_temp.i('B_INVIO')));
SELECT pg_temp.bozza('B_ANNULLATA');
SELECT pg_temp.stato('B_ANNULLATA', 'CANCELLED');
SELECT pg_temp.prova('12_cancelled_elimina', format(
    $$DELETE FROM config.email_outbox WHERE id = %s$$, pg_temp.i('B_ANNULLATA')));
SELECT pg_temp.allegato('A_ALTRA', 'B_ALTRA');
SELECT pg_temp.prova('13_draft_elimina', format(
    $$DELETE FROM config.email_outbox WHERE id = %s$$, pg_temp.i('B_ALTRA')));

SELECT plan(13);

-- ============================================================
-- 1..2. Forma e catalogo
-- ============================================================
-- ⚠️ Nomi dal CATALOGO, non da `::regclass::text` / `::regproc::text`: quelli
--   tolgono lo schema quando e' nel search_path, e il runner ha `config` nel
--   suo (rosso alla prima corsa di Tid, 2026-09-25).
SELECT is(
    (SELECT string_agg(nc.nspname || '.' || c.relname || ':' || t.tgname
                       || '->' || np.nspname || '.' || p.proname,
                       ' ' ORDER BY t.tgname)
       FROM pg_trigger t
       JOIN pg_class c      ON c.oid  = t.tgrelid
       JOIN pg_namespace nc ON nc.oid = c.relnamespace
       JOIN pg_proc p       ON p.oid  = t.tgfoid
       JOIN pg_namespace np ON np.oid = p.pronamespace
      WHERE NOT t.tgisinternal
        AND t.tgname IN ('trg_email_outbox_a10_guard_delete_solo_bozza_dlt',
                         'trg_email_allegato_a10_guard_solo_bozza_ins_upd_dlt')),
    'config.email_allegato:trg_email_allegato_a10_guard_solo_bozza_ins_upd_dlt->config.trgfn_email_allegato_guard_solo_bozza '
    || 'config.email_outbox:trg_email_outbox_a10_guard_delete_solo_bozza_dlt->vendite.trgfn_doc_guard_delete_solo_bozza',
    '1. i due trigger sono montati, con le funzioni giuste'
);

SELECT is(
    (SELECT c.classe || '/' || COALESCE(c.obsoleto_dal::text, 'vivo')
       FROM config.codici_errore c WHERE c.codice = 'E_EMAIL_ALLEGATO_NON_BOZZA'),
    'CONFLITTO_STATO/vivo',
    '2. E_EMAIL_ALLEGATO_NON_BOZZA e'' a catalogo, CONFLITTO_STATO'
);

-- ============================================================
-- 3..10. Gli allegati
-- ============================================================
SELECT ok(pg_temp.passa('3_ins') AND pg_temp.passa('3_upd') AND pg_temp.passa('3_dlt'),
    '3. bozza DRAFT: un allegato si aggiunge, si modifica e si toglie');

-- ⭐ Senza questa eccezione il guard fermerebbe l'invio.
SELECT ok(pg_temp.passa('4_aggancio'),
    '4. bozza READY: l''aggancio al log (solo email_log_id) passa — e'' l''invio');

SELECT ok(pg_temp.rifiuto('5_ready_upd', 'modificare'),
    '5. bozza READY: qualunque altra modifica -> rifiutata, «modificare»');

-- ⭐ Il caso del brief (§6.6): toglierlo cancellerebbe la storia della mail spedita.
SELECT ok(pg_temp.rifiuto('6_sent_dlt', 'togliere'),
    '6. mail spedita: l''allegato non si toglie, «togliere»');

SELECT ok(pg_temp.rifiuto('7_sent_ins', 'aggiungere'),
    '7. mail spedita: non si aggiunge un allegato, «aggiungere»');

SELECT ok(pg_temp.rifiuto('8_sent_sposta', 'modificare'),
    '8. mail spedita: un suo allegato non si sposta su un''altra bozza, anche se in DRAFT');

SELECT ok(pg_temp.passa('9_fallita_dlt') AND pg_temp.passa('9_riaggancio'),
    '9. invio fallito, bozza tornata DRAFT: l''allegato si toglie, e il nuovo tentativo lo riaggancia');

SELECT ok(
    (SELECT coalesce(e.sqlstate = 'P0001'
                     AND e.messaggio LIKE '%registrata nel log, senza bozza%', false)
       FROM _esito e WHERE e.caso = '10_solo_log'),
    '10. un allegato non nasce direttamente sul log: la storia non si scrive a posteriori');

-- ============================================================
-- 11..13. La bozza
-- ============================================================
SELECT ok(
    (SELECT coalesce(e.sqlstate = 'P0001'
                     AND e.messaggio LIKE '%si puo'' eliminare solo finche''%', false)
       FROM _esito e WHERE e.caso = '11_sent_elimina'),
    '11. mail spedita: non si elimina (E_DELETE_DOC_NON_BOZZA) — e con lei nemmeno i suoi allegati');

SELECT ok(
    (SELECT coalesce(e.sqlstate = 'P0001'
                     AND e.messaggio LIKE '%si puo'' eliminare solo finche''%', false)
       FROM _esito e WHERE e.caso = '12_cancelled_elimina'),
    '12. bozza annullata: resta, non si elimina');

SELECT ok(
    pg_temp.passa('13_draft_elimina')
    AND NOT EXISTS (SELECT 1 FROM config.email_allegato WHERE id = pg_temp.i('A_ALTRA')),
    '13. bozza DRAFT: si elimina, e i suoi allegati la seguono (il cascade non e'' fermato)');

SELECT * FROM finish();

ROLLBACK;
