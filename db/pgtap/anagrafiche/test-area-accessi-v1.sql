-- ------------------------------------------------------------
-- SPDX-License-Identifier: AGPL-3.0-or-later
-- pgTAP test per Zero ERP
--
-- pgtap-runner: owner
-- pgtap-runner-motivo: la fixture costruisce un utente TECNICO
--   (dbops.fn_pgtap_crea_roster_processo: scrive dbops.processi_identita, che il
--   ruolo applicativo non scrive) e, per il test 15, SPEGNE un trigger per
--   costruire la credenziale mista che il guard ora rifiuta: e' DDL. Stesso
--   criterio di script/test-fn-scope-identita-processo.sql.
--
-- Test: l'area «Accessi» — categoria di una credenziale, natura della
--       credenziale, stato di una veste, le viste dei tab «Altri accessi» e
--       «Di sistema», il presidio delle credenziali da sanare
-- ChangeSet: 20261002-20/-21 (fn_veste_di_sistema, fn_categoria_accesso),
--            -23/-24 (guard sulla natura della credenziale), -31
--            (fn_stato_veste), -32 (fn_credenziali), -33/-34 (le due viste),
--            -35 (dbops.vw_credenziali_da_sanare)
-- Brief: brief-db-be-fe-area-accessi, R-DB-A1, R-DB-A2, R-DB-A2-bis, R-DB-2
--
-- Elenco test (plan 17):
--   La categoria (R-DB-A1)
--    1) fn_veste_di_sistema: API_CLIENT o tecnica, nient'altro
--    2) una credenziale per categoria: operatore persona OPERATORE, shop
--       ALTRO, senza vesti ALTRO, utente tecnico SISTEMA, API_CLIENT SISTEMA
--    3) l'operatore SPENTO resta OPERATORE (le vesti spente contano)
--   La natura della credenziale
--    4) API_CLIENT su una credenziale di persona -> E_CREDENZIALE_PERSONA_E_SISTEMA
--    5) SHOP_CUSTOMER su un utente tecnico -> E_CREDENZIALE_PERSONA_E_SISTEMA
--    6) API_CLIENT su un utente tecnico: stessa natura, passa
--   La partizione (A-2)
--    7) ogni credenziale sta in UN tab: altri + sistema + operatori = tutte
--       (la categoria e' un valore solo, quindi i tre insiemi sono disgiunti
--       per costruzione: se la somma torna, non manca nessuno)
--   Lo stato di una veste (A-7)
--    8) ATTIVO, DISATTIVO, PENDING (>= anche a pari now()), NON_SPEDITO (email
--       mai partita), NON_SPEDITO (email di un invito precedente), DISATTIVO
--       (token scaduto o usato)
--    9) il token di un'ALTRA veste della stessa credenziale non conta
--   10) token_scade_at = la scadenza del token pendente, NULL senza
--   Le viste
--   11) «Altri accessi»: la credenziale senza vesti c'e', nessun_accesso,
--       stato NESSUNO, vesti vuote
--   12) «Altri accessi»: la veste porta il suo stato, il riassunto e i
--       cliente_ids come array; operatore e utente tecnico non ci sono
--   13) «Di sistema»: utente tecnico PROCESSO col suo processo e il suo
--       emittente; API_CLIENT senza processo; l'operatore non c'e'
--   Il presidio (R-DB-2)
--   14) NESSUNA_VESTE per la credenziale senza vesti; NON per quella con sole
--       vesti spente (V-3)
--   15) PERSONA_E_SISTEMA per una credenziale mista costruita col guard
--       spento, e la categoria e' SISTEMA (la precedenza dichiarata)
--   Forma
--   16) le tre viste sono security_invoker
--   17) il presidio e' a catalogo in dbops.presidi
-- ------------------------------------------------------------

BEGIN;

-- L'utente tecnico si costruisce PRIMA del contesto (stampo di
-- script/test-fn-scope-identita-processo.sql): crea la sua azienda.
CREATE TEMP TABLE _tec AS
SELECT r.auth_user_id, r.emittente_codice
  FROM dbops.fn_pgtap_crea_roster_processo('send_pending_emails') r;

DO $ctx$ BEGIN PERFORM script.fn_pgtap_set_contesto_operatore(); END $ctx$;

SET CONSTRAINTS ALL IMMEDIATE;

SELECT plan(17);

-- ============================================================
-- Fixture
-- ============================================================

-- Una credenziale nuda (nessuna veste), con un nome che non collide.
CREATE OR REPLACE FUNCTION pg_temp.credenziale(p_nome text) RETURNS integer
LANGUAGE plpgsql AS $$
DECLARE v_id integer;
BEGIN
    INSERT INTO django.auth_user (username, password, is_active, is_staff, is_superuser,
                                  first_name, last_name, email, date_joined)
    VALUES ('_pgtap_acc_' || p_nome || '_' || substring(md5(clock_timestamp()::text) FROM 1 FOR 8),
            '!', false, false, false, '', '', '', now())
    RETURNING id INTO v_id;
    RETURN v_id;
END $$;

-- Un token pendente della veste: identita_id nel meta, come lo scrive
-- l'emissione di un invito.
CREATE OR REPLACE FUNCTION pg_temp.token(p_auth_user_id integer, p_identita_id bigint,
                                         p_scadenza timestamptz, p_utilizzato boolean)
RETURNS void LANGUAGE sql AS $$
    INSERT INTO config.token_monouso (token_hash, tipo, auth_user_id, scadenza, utilizzato, meta)
    VALUES (md5(random()::text || clock_timestamp()::text), 'INVITO_PORTALE', p_auth_user_id,
            p_scadenza, p_utilizzato, jsonb_build_object('identita_id', p_identita_id));
$$;

-- L'operatore persona, dal percorso di produzione.
CREATE TEMP TABLE _op AS
SELECT o.auth_user_id, o.identita_id
  FROM dbops.fn_pgtap_crea_operatore_umano('accessi', false) o;

-- Un ruolo cliente su cui appoggiare le vesti di portale e shop.
CREATE TEMP TABLE _cli AS
SELECT c.soggetto_ruolo_id AS sr_id FROM dbops.fn_pgtap_crea_cliente_ba('accessi') c;
SET CONSTRAINTS ALL IMMEDIATE;

-- Le credenziali: c0 senza vesti; c1 shop accesa; c2..c6 cliente portale
-- spente con i casi del token; api con la veste API_CLIENT.
CREATE TEMP TABLE _c (nome text PRIMARY KEY, auth_user_id integer, identita_id bigint);
INSERT INTO _c (nome, auth_user_id)
SELECT n, pg_temp.credenziale(n)
  FROM unnest(ARRAY['c0','c1','c2','c3','c4','c5','c6','api']) n;

CREATE OR REPLACE FUNCTION pg_temp.veste(p_nome text, p_ruolo text, p_attivo boolean) RETURNS void
LANGUAGE plpgsql AS $$
DECLARE v_id bigint;
BEGIN
    INSERT INTO anagrafiche.identita_digitali (soggetto_ruolo_id, auth_user_id, ruolo_applicativo, attivo)
    VALUES ((SELECT sr_id FROM _cli), (SELECT auth_user_id FROM _c WHERE nome = p_nome),
            p_ruolo::config.ruolo_applicativo, p_attivo)
    RETURNING id INTO v_id;
    UPDATE _c SET identita_id = v_id WHERE nome = p_nome;
END $$;

SELECT pg_temp.veste('c1', 'SHOP_CUSTOMER', true);
SELECT pg_temp.veste('c2', 'CLIENTE_PORTALE', false);
SELECT pg_temp.veste('c3', 'CLIENTE_PORTALE', false);
SELECT pg_temp.veste('c4', 'CLIENTE_PORTALE', false);
SELECT pg_temp.veste('c5', 'CLIENTE_PORTALE', false);
SELECT pg_temp.veste('c6', 'CLIENTE_PORTALE', false);
SELECT pg_temp.veste('api', 'API_CLIENT', true);

-- c3: token pendente, email partita nello STESSO now() dell'emissione (>=).
SELECT pg_temp.token(auth_user_id, identita_id, now() + interval '2 days', false) FROM _c WHERE nome = 'c3';
UPDATE anagrafiche.identita_digitali SET invito_inviato_at = now()
 WHERE id = (SELECT identita_id FROM _c WHERE nome = 'c3');
-- c4: token pendente, email mai partita.
SELECT pg_temp.token(auth_user_id, identita_id, now() + interval '2 days', false) FROM _c WHERE nome = 'c4';
-- c5: token pendente, l'email partita e' quella di un invito PRECEDENTE.
SELECT pg_temp.token(auth_user_id, identita_id, now() + interval '2 days', false) FROM _c WHERE nome = 'c5';
UPDATE anagrafiche.identita_digitali SET invito_inviato_at = now() - interval '3 days'
 WHERE id = (SELECT identita_id FROM _c WHERE nome = 'c5');
-- c6: un token scaduto e uno usato: nessuno e' pendente.
SELECT pg_temp.token(auth_user_id, identita_id, now() - interval '1 hour', false) FROM _c WHERE nome = 'c6';
SELECT pg_temp.token(auth_user_id, identita_id, now() + interval '2 days', true)  FROM _c WHERE nome = 'c6';
-- c2: un token pendente sulla credenziale, ma di un'ALTRA veste (c3).
SELECT pg_temp.token((SELECT auth_user_id FROM _c WHERE nome = 'c2'),
                     (SELECT identita_id FROM _c WHERE nome = 'c3'),
                     now() + interval '2 days', false);

-- ============================================================
-- 1-3. La categoria
-- ============================================================
SELECT is(
    script.fn_veste_di_sistema('OPERATORE', false)::text || '|'
    || script.fn_veste_di_sistema('OPERATORE', true)::text || '|'
    || script.fn_veste_di_sistema('API_CLIENT', false)::text || '|'
    || script.fn_veste_di_sistema('SHOP_CUSTOMER', false)::text,
    'false|true|true|false',
    '1) fn_veste_di_sistema: API_CLIENT o tecnica, nient''altro');

SELECT is(
    concat_ws('|',
        script.fn_categoria_accesso((SELECT auth_user_id FROM _op)),
        script.fn_categoria_accesso((SELECT auth_user_id FROM _c WHERE nome = 'c1')),
        script.fn_categoria_accesso((SELECT auth_user_id FROM _c WHERE nome = 'c0')),
        script.fn_categoria_accesso((SELECT auth_user_id FROM _tec)),
        script.fn_categoria_accesso((SELECT auth_user_id FROM _c WHERE nome = 'api'))),
    'OPERATORE|ALTRO|ALTRO|SISTEMA|SISTEMA',
    '2) una categoria per credenziale: operatore, shop, senza vesti, utente tecnico, API_CLIENT');

UPDATE anagrafiche.identita_digitali SET attivo = false
 WHERE id = (SELECT identita_id FROM _op);

SELECT is(
    script.fn_categoria_accesso((SELECT auth_user_id FROM _op)),
    'OPERATORE',
    '3) l''operatore spento resta OPERATORE: le vesti spente contano');

-- ============================================================
-- 4-6. La natura della credenziale
-- ============================================================
SELECT is(
    dbops.fn_pgtap_codice_errore(format(
        $$INSERT INTO anagrafiche.identita_digitali
              (soggetto_ruolo_id, auth_user_id, ruolo_applicativo, attivo)
          VALUES (%s, %s, 'API_CLIENT', false)$$,
        (SELECT sr_id FROM _cli), (SELECT auth_user_id FROM _op))),
    'E_CREDENZIALE_PERSONA_E_SISTEMA',
    '4) API_CLIENT su una credenziale di persona (anche con la veste spenta): rifiutata');

SELECT is(
    dbops.fn_pgtap_codice_errore(format(
        $$INSERT INTO anagrafiche.identita_digitali
              (soggetto_ruolo_id, auth_user_id, ruolo_applicativo, attivo)
          VALUES (%s, %s, 'SHOP_CUSTOMER', false)$$,
        (SELECT sr_id FROM _cli), (SELECT auth_user_id FROM _tec))),
    'E_CREDENZIALE_PERSONA_E_SISTEMA',
    '5) SHOP_CUSTOMER su un utente tecnico: rifiutata');

SELECT lives_ok(
    format($$INSERT INTO anagrafiche.identita_digitali
                 (soggetto_ruolo_id, auth_user_id, ruolo_applicativo, attivo)
             VALUES (%s, %s, 'API_CLIENT', false)$$,
           (SELECT sr_id FROM _cli), (SELECT auth_user_id FROM _tec)),
    '6) API_CLIENT su un utente tecnico: due macchine, passa');

-- ============================================================
-- 7. La partizione
-- ============================================================
-- ⭐ Vale per QUALUNQUE popolazione, anche vuota: non conta i dati di oggi,
--   verifica che le tre domande coprano tutto senza sovrapporsi.
SELECT is(
    (SELECT (SELECT count(*) FROM anagrafiche.vw_accessi_altri)
            + (SELECT count(*) FROM anagrafiche.vw_accessi_sistema)
            + (SELECT count(*) FROM script.fn_credenziali() c
                WHERE script.fn_categoria_accesso(c.auth_user_id) = 'OPERATORE'))
        = (SELECT count(*) FROM script.fn_credenziali()),
    true,
    '7) altri + sistema + operatori = tutte le credenziali');

-- ============================================================
-- 8-10. Lo stato di una veste
-- ============================================================
SELECT is(
    (SELECT string_agg(s.stato, '|' ORDER BY c.nome)
       FROM _c c
       CROSS JOIN LATERAL script.fn_stato_veste(c.identita_id) s
      WHERE c.nome IN ('c1','c3','c4','c5','c6')),
    'ATTIVO|PENDING|NON_SPEDITO|NON_SPEDITO|DISATTIVO',
    '8) ATTIVO; PENDING a pari now(); NON_SPEDITO senza email e con l''email di un invito precedente; DISATTIVO con token scaduto o usato');

SELECT is(
    (SELECT s.stato FROM _c c CROSS JOIN LATERAL script.fn_stato_veste(c.identita_id) s
      WHERE c.nome = 'c2'),
    'DISATTIVO',
    '9) il token di un''altra veste della stessa credenziale non conta');

SELECT is(
    (SELECT (s3.token_scade_at > now())::text || '|' || COALESCE(s2.token_scade_at::text, 'NULL')
       FROM script.fn_stato_veste((SELECT identita_id FROM _c WHERE nome = 'c3')) s3,
            script.fn_stato_veste((SELECT identita_id FROM _c WHERE nome = 'c2')) s2),
    'true|NULL',
    '10) token_scade_at: la scadenza del pendente, NULL senza');

-- ============================================================
-- 11-13. Le viste
-- ============================================================
-- ⚠️ `::text` sul booleano: concat_ws (come format('%s')) lo scrive con la
--   forma di uscita del tipo, `t`/`f`, mentre `::text` da' `true`/`false`.
SELECT is(
    (SELECT concat_ws('|', a.nessun_accesso::text, a.stato_accesso, a.vesti::text,
                      COALESCE(a.vesti_elenco, 'NULL'))
       FROM anagrafiche.vw_accessi_altri a
      WHERE a.auth_user_id = (SELECT auth_user_id FROM _c WHERE nome = 'c0')),
    'true|NESSUNO|[]|NULL',
    '11) Altri accessi: la credenziale senza vesti c''e'', nessun_accesso, NESSUNO, vesti vuote');

SELECT is(
    (SELECT concat_ws('|', a.vesti -> 0 ->> 'stato', a.stato_accesso, a.vesti_elenco,
                      jsonb_typeof(a.vesti -> 0 -> 'cliente_ids'),
                      (SELECT count(*) FROM anagrafiche.vw_accessi_altri x
                        WHERE x.auth_user_id IN ((SELECT auth_user_id FROM _op),
                                                 (SELECT auth_user_id FROM _tec))))
       FROM anagrafiche.vw_accessi_altri a
      WHERE a.auth_user_id = (SELECT auth_user_id FROM _c WHERE nome = 'c3')),
    'PENDING|PENDING|CLIENTE_PORTALE|array|0',
    '12) Altri accessi: stato della veste, riassunto, cliente_ids array; operatore e utente tecnico assenti');

SELECT is(
    (SELECT concat_ws('|',
                (SELECT s.tipo || ':' || s.processo_codice || ':'
                        || (s.emittente_codice = (SELECT emittente_codice FROM _tec))::text
                   FROM anagrafiche.vw_accessi_sistema s
                  WHERE s.auth_user_id = (SELECT auth_user_id FROM _tec)),
                (SELECT s.tipo || ':' || COALESCE(s.processo_codice, 'NULL')
                   FROM anagrafiche.vw_accessi_sistema s
                  WHERE s.auth_user_id = (SELECT auth_user_id FROM _c WHERE nome = 'api')),
                (SELECT count(*) FROM anagrafiche.vw_accessi_sistema s
                  WHERE s.auth_user_id = (SELECT auth_user_id FROM _op)))),
    'PROCESSO:send_pending_emails:true|API_CLIENT:NULL|0',
    '13) Di sistema: utente tecnico col processo e l''emittente, API_CLIENT senza processo, operatore assente');

-- ============================================================
-- 14-15. Il presidio
-- ============================================================
SELECT is(
    (SELECT concat_ws('|',
                (SELECT string_agg(d.motivo, ',') FROM dbops.vw_credenziali_da_sanare d
                  WHERE d.auth_user_id = (SELECT auth_user_id FROM _c WHERE nome = 'c0')),
                (SELECT count(*) FROM dbops.vw_credenziali_da_sanare d
                  WHERE d.auth_user_id = (SELECT auth_user_id FROM _c WHERE nome = 'c2')))),
    'NESSUNA_VESTE|0',
    '14) presidio: NESSUNA_VESTE senza vesti; una credenziale con sole vesti spente non c''e'' (V-3)');

-- ⭐ La credenziale mista si COSTRUISCE: il guard la rifiuta (test 4), quindi
--   si spegne il trigger per la durata di un INSERT, come farebbe una riga
--   nata prima del guard. In transazione: il ROLLBACK lo riaccende.
ALTER TABLE anagrafiche.identita_digitali
    DISABLE TRIGGER trg_identita_digitali_a10_guard_natura_credenziale_ins_upd;
INSERT INTO anagrafiche.identita_digitali (soggetto_ruolo_id, auth_user_id, ruolo_applicativo, attivo)
SELECT sr_id, (SELECT auth_user_id FROM _op), 'API_CLIENT', false FROM _cli;
ALTER TABLE anagrafiche.identita_digitali
    ENABLE TRIGGER trg_identita_digitali_a10_guard_natura_credenziale_ins_upd;

SELECT is(
    (SELECT concat_ws('|',
                (SELECT string_agg(d.motivo, ',') FROM dbops.vw_credenziali_da_sanare d
                  WHERE d.auth_user_id = (SELECT auth_user_id FROM _op)),
                script.fn_categoria_accesso((SELECT auth_user_id FROM _op)))),
    'PERSONA_E_SISTEMA|SISTEMA',
    '15) presidio: PERSONA_E_SISTEMA per la credenziale mista, e la categoria e'' SISTEMA');

-- ============================================================
-- 16-17. Forma
-- ============================================================
SELECT is(
    (SELECT string_agg(n.nspname || '.' || c.relname || '=' ||
                       COALESCE(c.reloptions @> ARRAY['security_invoker=true'], false)::text,
                       ',' ORDER BY n.nspname, c.relname)
       FROM pg_catalog.pg_class c
       JOIN pg_catalog.pg_namespace n ON n.oid = c.relnamespace
      WHERE (n.nspname, c.relname) IN (('anagrafiche', 'vw_accessi_altri'),
                                       ('anagrafiche', 'vw_accessi_sistema'),
                                       ('dbops', 'vw_credenziali_da_sanare'))),
    'anagrafiche.vw_accessi_altri=true,anagrafiche.vw_accessi_sistema=true,dbops.vw_credenziali_da_sanare=true',
    '16) le tre viste sono security_invoker');

SELECT is(
    (SELECT p.natura || '|' || p.perimetro FROM dbops.presidi p
      WHERE p.vista = 'dbops.vw_credenziali_da_sanare' AND p.attivo),
    'ZERO|LIBERO',
    '17) il presidio e'' a catalogo: ZERO, LIBERO');

SELECT * FROM finish();
ROLLBACK;
