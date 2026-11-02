-- ------------------------------------------------------------
-- SPDX-License-Identifier: AGPL-3.0-or-later
-- pgTAP test per Zero ERP
--
-- Test: chi vede una mail secondo il suo AMBITO — config.email_log,
--   config.email_outbox e il loro satellite config.email_allegato.
-- ChangeSet: 20260925-63..-70 · Brief: brief-db-email-visibilita-per-ambito
--
-- Elenco test (plan 22):
--  1) ⭐ il presupposto: le tre tabelle SUBISCONO la row level security
--  2..4) ⛔ i CHECK: l'ambito promette un pubblico, la colonna che lo nomina c'e'
--  5..8) ✅/⛔ due operatori della stessa azienda: ciascuno vede le proprie
--        OPERATORE e il proprio REPARTO, non quelle del collega
--  9) ⛔ un operatore SENZA reparto non vede le mail di reparto
--  10..11) ✅ il super admin vede tutto
--  12..14) ⭐ il processo send_pending_emails vede e aggiorna le righe del LOG
--          di ogni ambito, dentro le sue aziende; sull'outbox niente, e degli
--          allegati solo quelli agganciati al log (il ramo «log» della policy)
--  15..18) ⛔ WITH CHECK: non si scrive, non si modifica e non si «sposta» una
--          mail fuori dal proprio perimetro
--  19..21) il satellite segue i suoi padri
--  22) ⛔ utente vuoto: niente, anche se il cancello emittente per NULL dice si'
--
-- ────────────────────────────────────────────────────────────────
-- ⭐ I CASI SI COSTRUISCONO, NON SI LEGGONO DAI DATI (regola zero).
--   Due aziende (E1 con l'identita' tecnica del processo, E2 senza operatori),
--   tre operatori umani di E1 — A nel reparto UO1, B nel reparto UO2, C senza
--   reparto — e un super admin. Poi le righe, ognuna scritta dal suo autore
--   attraverso la policy.
--   ⚠️ La riga OPERATORE di A su E2 la scrive il super admin: e' il caso D-1,
--   «l'ho scritta io ma l'azienda non e' piu' nel mio perimetro».
--
-- ⚠️ I rifiuti del WITH CHECK si chiedono come 42501 (15, 16, 18, 21), ed e'
--   giusto: li' la policy E' la cosa provata. I CHECK (2..4) si provano dal
--   super admin, che passa la policy: per chi la subisce il WITH CHECK
--   risponde prima del vincolo.
-- ------------------------------------------------------------

BEGIN;

SET CONSTRAINTS ALL IMMEDIATE;

-- ============================================================
-- Il mondo, PRIMA di aprire il contesto
-- ============================================================
-- E1: l'azienda, con l'identita' tecnica di send_pending_emails nel suo roster.
CREATE TEMP TABLE _e1 AS
SELECT * FROM dbops.fn_pgtap_crea_roster_processo('send_pending_emails');

-- E2: un'altra azienda, che nessuno degli operatori ha in perimetro.
CREATE TEMP TABLE _e2 AS
SELECT * FROM dbops.fn_pgtap_crea_emittente();

-- Gli operatori: ⛔ ogni builder in un'istruzione sua (scrive una saga, e
--   cio' che scrive si legge in un'istruzione separata).
CREATE TEMP TABLE _op (lato text PRIMARY KEY, auth_user_id integer, risorsa_umana_id bigint);
INSERT INTO _op SELECT 'A',  auth_user_id, risorsa_umana_id FROM dbops.fn_pgtap_crea_operatore_umano('email A');
INSERT INTO _op SELECT 'B',  auth_user_id, risorsa_umana_id FROM dbops.fn_pgtap_crea_operatore_umano('email B');
INSERT INTO _op SELECT 'C',  auth_user_id, risorsa_umana_id FROM dbops.fn_pgtap_crea_operatore_umano('email C');
INSERT INTO _op SELECT 'SA', auth_user_id, risorsa_umana_id FROM dbops.fn_pgtap_crea_operatore_umano('email SA', true);
INSERT INTO _op SELECT 'P',  auth_user_id, NULL FROM _e1;

-- A, B e C lavorano per E1 (funzione di dominio: sede unica dello scope).
SELECT script.fn_change_user_emittenti_scope(
           o.auth_user_id, ARRAY[(SELECT emittente_fiscale_id FROM _e1)])
  FROM _op o WHERE o.lato IN ('A', 'B', 'C');

-- Due reparti: A nel primo, B nel secondo, C in nessuno.
CREATE TEMP TABLE _uo (lato text PRIMARY KEY, id integer);
DO $uo$
DECLARE
    v_lato text;
    v_cod  config.unita_organizzative.codice%TYPE;
    v_id   config.unita_organizzative.id%TYPE;
BEGIN
    FOREACH v_lato IN ARRAY ARRAY['UO1', 'UO2'] LOOP
        v_cod := 'PGT-' || v_lato || '-' || substr(md5(random()::text), 1, 6);
        INSERT INTO config.unita_organizzative (codice, codice_interno, descrizione)
        VALUES (v_cod, v_cod, 'Reparto pgTAP ' || v_lato)
        RETURNING id INTO v_id;
        INSERT INTO _uo VALUES (v_lato, v_id);
    END LOOP;
END
$uo$;

UPDATE anagrafiche.risorse_umane ru
   SET unita_organizzativa_id = (SELECT id FROM _uo WHERE lato = 'UO1')
 WHERE ru.id = (SELECT risorsa_umana_id FROM _op WHERE lato = 'A');
UPDATE anagrafiche.risorse_umane ru
   SET unita_organizzativa_id = (SELECT id FROM _uo WHERE lato = 'UO2')
 WHERE ru.id = (SELECT risorsa_umana_id FROM _op WHERE lato = 'B');

-- ============================================================
-- Due strumenti
-- ============================================================
-- «Chi sono»: il contesto applicativo di un attore della fixture.
CREATE FUNCTION pg_temp.come(p_lato text) RETURNS integer
LANGUAGE sql AS $$
    SELECT script.fn_pgtap_set_contesto_operatore(
               (SELECT auth_user_id FROM _op WHERE lato = p_lato));
$$;

-- «Come e' andata»: 'ok:<righe toccate>', oppure SQLSTATE[:vincolo].
-- ⭐ Il nome del vincolo, non il solo SQLSTATE: un 23514 lo darebbe
--   qualunque CHECK della tabella.
CREATE FUNCTION pg_temp.esito(p_sql text) RETURNS text
LANGUAGE plpgsql AS $$
DECLARE
    v_n integer;
    v_c text;
BEGIN
    EXECUTE p_sql;
    GET DIAGNOSTICS v_n = ROW_COUNT;
    RETURN 'ok:' || v_n;
EXCEPTION WHEN OTHERS THEN
    GET STACKED DIAGNOSTICS v_c = CONSTRAINT_NAME;
    RETURN SQLSTATE || CASE WHEN v_c <> '' THEN ':' || v_c ELSE '' END;
END
$$;

-- ============================================================
-- Le righe, ognuna scritta dal suo autore ATTRAVERSO la policy
-- ============================================================
-- Contesto applicativo: da qui il file gira come l'applicazione.
DO $ctx$
BEGIN
    PERFORM script.fn_pgtap_set_contesto_operatore(
        (SELECT auth_user_id FROM _op WHERE lato = 'A'));
END $ctx$;

CREATE TEMP TABLE _righe (nome text PRIMARY KEY, tab text, id bigint);

-- Una riga per (autore, tabella, ambito). OPERATORE porta l'autore, REPARTO il
-- reparto dell'autore; tutte su E1 salvo dove detto.
CREATE FUNCTION pg_temp.scrivi(p_nome text, p_tab text, p_autore text,
                               p_ambito text, p_uo text, p_emittente bigint)
RETURNS void LANGUAGE plpgsql AS $$
DECLARE
    v_id        bigint;
    v_creato_da integer := (SELECT auth_user_id FROM _op WHERE lato = p_autore);
    v_uo        integer := (SELECT id FROM _uo WHERE lato = p_uo);
BEGIN
    IF p_tab = 'log' THEN
        INSERT INTO config.email_log
            (destinatario, oggetto, stato, ambito, emittente_fiscale_id,
             unita_organizzativa_id, creato_da_user_id, contesto_json)
        VALUES (lower(p_nome) || '@example.invalid', 'pgtap ' || p_nome, 'FAILED',
                p_ambito, p_emittente, v_uo, v_creato_da, '{}'::jsonb)
        RETURNING id INTO v_id;
    ELSE
        INSERT INTO config.email_outbox
            (destinatario, oggetto, corpo_html, ambito, emittente_fiscale_id,
             unita_organizzativa_id, creato_da_user_id)
        VALUES (lower(p_nome) || '@example.invalid', 'pgtap ' || p_nome, '<p/>',
                p_ambito, p_emittente, v_uo, v_creato_da)
        RETURNING id INTO v_id;
    END IF;
    INSERT INTO _righe VALUES (p_nome, p_tab, v_id);
END
$$;

SELECT pg_temp.come('A');
SELECT pg_temp.scrivi('L_A_OP',  'log',    'A', 'OPERATORE', NULL,  (SELECT emittente_fiscale_id FROM _e1));
SELECT pg_temp.scrivi('L_UO1',   'log',    'A', 'REPARTO',   'UO1', (SELECT emittente_fiscale_id FROM _e1));
SELECT pg_temp.scrivi('O_A_OP',  'outbox', 'A', 'OPERATORE', NULL,  (SELECT emittente_fiscale_id FROM _e1));
SELECT pg_temp.scrivi('O_UO1',   'outbox', 'A', 'REPARTO',   'UO1', (SELECT emittente_fiscale_id FROM _e1));

SELECT pg_temp.come('B');
SELECT pg_temp.scrivi('L_B_OP',  'log',    'B', 'OPERATORE', NULL,  (SELECT emittente_fiscale_id FROM _e1));
SELECT pg_temp.scrivi('L_UO2',   'log',    'B', 'REPARTO',   'UO2', (SELECT emittente_fiscale_id FROM _e1));
SELECT pg_temp.scrivi('O_B_OP',  'outbox', 'B', 'OPERATORE', NULL,  (SELECT emittente_fiscale_id FROM _e1));
SELECT pg_temp.scrivi('O_UO2',   'outbox', 'B', 'REPARTO',   'UO2', (SELECT emittente_fiscale_id FROM _e1));

-- D-1: una mail OPERATORE di A, ma su un'azienda che A non ha in perimetro.
SELECT pg_temp.come('SA');
SELECT pg_temp.scrivi('L_A_E2',  'log',    'A', 'OPERATORE', NULL,  (SELECT emittente_fiscale_id FROM _e2));

-- Gli allegati di A: uno sulla bozza, uno sul log.
SELECT pg_temp.come('A');
DO $allegati$
DECLARE
    v_id config.email_allegato.id%TYPE;
BEGIN
    INSERT INTO config.email_allegato
        (email_outbox_id, nome_file, mime_type, dimensione_bytes, file_path)
    VALUES ((SELECT id FROM _righe WHERE nome = 'O_A_OP'),
            'a.pdf', 'application/pdf', 1, 'pgtap/a.pdf')
    RETURNING id INTO v_id;
    INSERT INTO _righe VALUES ('ALL_A_OUT', 'allegato', v_id);

    -- ⚠️ Come nell'applicazione: l'allegato nasce sulla BOZZA e all'invio si
    --   aggancia al log (dal 20260925-74 non si scrive direttamente sul log).
    --   Da qui porta due padri: chi vede solo il log (il processo, test 14)
    --   lo vede per quella strada.
    INSERT INTO config.email_allegato
        (email_outbox_id, nome_file, mime_type, dimensione_bytes, file_path)
    VALUES ((SELECT id FROM _righe WHERE nome = 'O_A_OP'),
            'b.pdf', 'application/pdf', 1, 'pgtap/b.pdf')
    RETURNING id INTO v_id;
    UPDATE config.email_allegato
       SET email_log_id = (SELECT id FROM _righe WHERE nome = 'L_A_OP')
     WHERE id = v_id;
    INSERT INTO _righe VALUES ('ALL_A_LOG', 'allegato', v_id);
END
$allegati$;

-- «Che cosa vede chi guarda», fra le righe della fixture.
CREATE FUNCTION pg_temp.visti(p_tab text) RETURNS text[]
LANGUAGE sql AS $$
    SELECT coalesce(array_agg(r.nome ORDER BY r.nome), '{}')
      FROM _righe r
     WHERE r.tab = p_tab
       AND CASE p_tab
             WHEN 'log'      THEN EXISTS (SELECT 1 FROM config.email_log x      WHERE x.id = r.id)
             WHEN 'outbox'   THEN EXISTS (SELECT 1 FROM config.email_outbox x   WHERE x.id = r.id)
             WHEN 'allegato' THEN EXISTS (SELECT 1 FROM config.email_allegato x WHERE x.id = r.id)
           END;
$$;

SELECT plan(22);

-- ============================================================
-- 1. Il presupposto
-- ============================================================
-- ⚠️ Senza, ogni «non vede» qui sotto sarebbe verde perche' non succede niente.
SELECT ok(
    row_security_active('config.email_log'::regclass)
    AND row_security_active('config.email_outbox'::regclass)
    AND row_security_active('config.email_allegato'::regclass),
    '1. log, outbox e allegati SUBISCONO la RLS: i test che seguono hanno senso'
);

-- ============================================================
-- 2..4. ⛔ L'ambito promette un pubblico: la colonna che lo nomina c'e'
-- ============================================================
-- Dal super admin, che passa la policy e arriva al vincolo.
SELECT pg_temp.come('SA');

SELECT is(
    pg_temp.esito(format(
        $$INSERT INTO config.email_log (destinatario, oggetto, ambito, emittente_fiscale_id)
          VALUES ('x@example.invalid', 'pgtap', 'OPERATORE', %s)$$,
        (SELECT emittente_fiscale_id FROM _e1))),
    '23514:chk_email_log_operatore_creatore',
    '2. log: una mail OPERATORE senza autore si ferma, sul suo CHECK'
);

SELECT is(
    pg_temp.esito(format(
        $$INSERT INTO config.email_log (destinatario, oggetto, ambito, emittente_fiscale_id)
          VALUES ('x@example.invalid', 'pgtap', 'REPARTO', %s)$$,
        (SELECT emittente_fiscale_id FROM _e1))),
    '23514:chk_email_log_reparto_uo',
    '3. log: una mail di REPARTO senza reparto si ferma, sul suo CHECK'
);

SELECT is(
    pg_temp.esito(format(
        $$INSERT INTO config.email_outbox (destinatario, oggetto, corpo_html, ambito, emittente_fiscale_id)
          VALUES ('x@example.invalid', 'pgtap', '<p/>', 'OPERATORE', %s)$$,
        (SELECT emittente_fiscale_id FROM _e1))),
    '23514:chk_email_outbox_operatore_creatore',
    '4. outbox: una bozza OPERATORE senza proprietario si ferma, sul suo CHECK'
);

-- ============================================================
-- 5..8. Due colleghi della stessa azienda
-- ============================================================
-- ⭐ Il cuore del brief: fino al 2026-09-25 A vedeva anche L_B_OP e L_UO2.
--   E L_A_E2 no, per D-1: e' sua, ma l'azienda non e' nel suo perimetro.
SELECT pg_temp.come('A');
SELECT is(pg_temp.visti('log'), ARRAY['L_A_OP', 'L_UO1'],
    '5. A sul log: la propria OPERATORE e il proprio reparto — non quelle di B, non la sua su un''altra azienda');
SELECT is(pg_temp.visti('outbox'), ARRAY['O_A_OP', 'O_UO1'],
    '6. A sull''outbox: la propria bozza e quella del proprio reparto, non quelle di B');

SELECT pg_temp.come('B');
SELECT is(pg_temp.visti('log'), ARRAY['L_B_OP', 'L_UO2'],
    '7. B sul log: lo specchio di A');
SELECT is(pg_temp.visti('outbox'), ARRAY['O_B_OP', 'O_UO2'],
    '8. B sull''outbox: lo specchio di A');

-- ============================================================
-- 9. ⛔ Senza reparto, niente mail di reparto
-- ============================================================
-- fn_get_uo_id_for_user rende NULL, il confronto non e' vero: fail-closed.
SELECT pg_temp.come('C');
SELECT is(pg_temp.visti('log') || pg_temp.visti('outbox'), '{}'::text[],
    '9. C, stessa azienda ma senza reparto: non vede le mail di REPARTO, ne'' le OPERATORE altrui');

-- ============================================================
-- 10..11. ✅ Il super admin vede tutto
-- ============================================================
SELECT pg_temp.come('SA');
SELECT is(pg_temp.visti('log'), ARRAY['L_A_E2', 'L_A_OP', 'L_B_OP', 'L_UO1', 'L_UO2'],
    '10. il super admin vede ogni mail del log, di ogni ambito e azienda');
SELECT is(pg_temp.visti('outbox'), ARRAY['O_A_OP', 'O_B_OP', 'O_UO1', 'O_UO2'],
    '11. il super admin vede ogni bozza');

-- ============================================================
-- 12..14. ⭐ Il processo: portare e' leggere
-- ============================================================
-- Se questi due test diventano rossi, una mail REPARTO o OPERATORE fallita
-- non viene piu' ritentata, e una coda vuota e' identica a «niente da fare».
SELECT pg_temp.come('P');
SELECT is(pg_temp.visti('log'), ARRAY['L_A_OP', 'L_B_OP', 'L_UO1', 'L_UO2'],
    '12. send_pending_emails vede le mail di ogni ambito della SUA azienda — e non quella di E2 (D-1)');

SELECT is(
    pg_temp.esito(format(
        $$UPDATE config.email_log SET stato = 'RETRY' WHERE id = %s$$,
        (SELECT id FROM _righe WHERE nome = 'L_B_OP'))),
    'ok:1',
    '13. e ne chiude lo stato: l''UPDATE su una mail OPERATORE altrui passa il WITH CHECK');

SELECT is(pg_temp.visti('outbox') || pg_temp.visti('allegato'), ARRAY['ALL_A_LOG'],
    '14. sull''outbox il processo non vede niente; degli allegati vede solo quello agganciato al log, per la strada del log');

-- ============================================================
-- 15..18. ⛔ WITH CHECK: fuori dal perimetro non si scrive
-- ============================================================
SELECT pg_temp.come('A');

SELECT is(
    pg_temp.esito(format(
        $$INSERT INTO config.email_log
              (destinatario, oggetto, ambito, emittente_fiscale_id, creato_da_user_id)
          VALUES ('x@example.invalid', 'pgtap', 'OPERATORE', %s, %s)$$,
        (SELECT emittente_fiscale_id FROM _e1),
        (SELECT auth_user_id FROM _op WHERE lato = 'B'))),
    '42501',
    '15. A non scrive una mail OPERATORE a nome di B');

SELECT is(
    pg_temp.esito(format(
        $$INSERT INTO config.email_log
              (destinatario, oggetto, ambito, emittente_fiscale_id, unita_organizzativa_id)
          VALUES ('x@example.invalid', 'pgtap', 'REPARTO', %s, %s)$$,
        (SELECT emittente_fiscale_id FROM _e1),
        (SELECT id FROM _uo WHERE lato = 'UO2'))),
    '42501',
    '16. A non scrive una mail per il reparto di B');

-- ⭐ La bozza del collega: prima si poteva modificare e spedire.
SELECT is(
    pg_temp.esito(format(
        $$UPDATE config.email_outbox SET oggetto = 'dirottata' WHERE id = %s$$,
        (SELECT id FROM _righe WHERE nome = 'O_B_OP'))),
    'ok:0',
    '17. A non modifica la bozza OPERATORE di B: per lui non esiste');

SELECT is(
    pg_temp.esito(format(
        $$UPDATE config.email_outbox SET creato_da_user_id = %s WHERE id = %s$$,
        (SELECT auth_user_id FROM _op WHERE lato = 'B'),
        (SELECT id FROM _righe WHERE nome = 'O_A_OP'))),
    '42501',
    '18. A non «regala» la propria bozza a B: la riga uscirebbe dal suo perimetro');

-- ============================================================
-- 19..21. Il satellite segue i padri
-- ============================================================
SELECT is(pg_temp.visti('allegato'), ARRAY['ALL_A_LOG', 'ALL_A_OUT'],
    '19. A vede gli allegati delle proprie mail, dalla bozza e dal log');

SELECT pg_temp.come('B');
SELECT is(pg_temp.visti('allegato'), '{}'::text[],
    '20. B non vede gli allegati delle mail OPERATORE di A');

-- Senza padri non lo vede nessuno: nemmeno il super admin lo scrive.
SELECT pg_temp.come('SA');
SELECT is(
    pg_temp.esito(
        $$INSERT INTO config.email_allegato (nome_file, mime_type, dimensione_bytes, file_path)
          VALUES ('orfano.pdf', 'application/pdf', 1, 'pgtap/orfano.pdf')$$),
    '42501',
    '21. un allegato senza mail non si scrive: nessun padre, nessun pubblico');

-- ============================================================
-- 22. ⛔ Utente vuoto
-- ============================================================
-- ⚠️ fn_check_user_emittente_scope(NULL, …) rispondeva TRUE («job batch») fino
--   al 2026-10-04; oggi risponde FALSE (Q-1 di brief-db-esclusioni-implicite).
--   Nei rami nuovi era comunque in AND con una condizione falsa per NULL.
--   PER ULTIMO: cambia il contesto e non lo rimette.
SELECT set_config('app.current_user_id', '', false);
SELECT is(pg_temp.visti('log') || pg_temp.visti('outbox') || pg_temp.visti('allegato'),
          '{}'::text[],
    '22. ruolo OPERATORE senza utente: nessuna mail e nessun allegato della fixture');

SELECT * FROM finish();

ROLLBACK;
