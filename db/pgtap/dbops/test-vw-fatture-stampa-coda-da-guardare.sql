-- ------------------------------------------------------------
-- SPDX-License-Identifier: AGPL-3.0-or-later
-- pgTAP test per Zero ERP
--
-- pgtap-runner: owner
-- pgtap-runner-motivo: la fixture deve RETRODATARE `data_update`, e l'audit
--   trigger (trgfn_audit_data_user_generic) lo riporta a now() a ogni
--   scrittura: l'unico modo di scrivere una data nel passato e' spegnere quel
--   trigger dentro la transazione — DDL che solo il proprietario puo' fare, e
--   che il ROLLBACK annulla. Verificato provando: da app la data non si
--   retrodata. ⭐ Che l'operatore la legga col proprio perimetro e' il modello
--   della vista (security_invoker), non l'oggetto di questo file.
--
-- Test: dbops.vw_fatture_stampa_coda_da_guardare — la gemella per la stampa
-- ChangeSet: 20260911-12
-- Brief: brief-db-quattro-processi-senza-presidio §4 · §10.1 (D1, D2)
--
-- Elenco test (plan 6):
--  1) ⛔ ERRORE compare, e il motivo lo dice
--  2) ⛔ IN_CORSO da oltre un'ora compare: il worker e' morto a meta'
--  3) ⛔ PENDING da oltre un'ora compare: IL DRENATORE NON STA GIRANDO
--  4) ✅ PENDING appena accodata NON compare: la soglia esiste davvero
--  5) ✅ IN_CORSO appena presa NON compare
--  6) ⚠️ archiviata non compare: qualcuno l'ha gia' guardata
--
-- ────────────────────────────────────────────────────────────────
-- ⭐ E' IL GEMELLO RIGA PER RIGA di dbops/test-vw-coda-lavori-da-guardare.sql,
--   meno un caso: la stampa non ha ANNULLATO (quattro stati contro cinque).
--   Le due code sono simmetriche per decisione, e lo era anche il buco: il
--   presidio ce l'aveva una sola.
--
-- ⚠️ DATA-DEPENDENT, dichiarato: una riga di coda stampa vuole una FATTURA
--   (FK) nel perimetro dell'operatore, e un vincolo univoco ammette UNA riga
--   viva per fattura — servono QUATTRO fatture libere. Su un database
--   ricostruito da zero non ce ne sono: i sei test si dichiarano con skip()
--   invece di passare a vuoto.
--   ⛔ E lo skip deve essere RAGGIUNGIBILE, che e' il punto in cui i tre
--   fratelli (test-coda-archiviazione, test-rls-fatture-stampa-coda*) cadono
--   in ERRORE_FIXTURE sulla CI: (1) fn_pgtap_emittente_operatore() SOLLEVA su
--   un database senza emittenti, quindi non la si chiama se non ce ne sono;
--   (2) l'audit trigger nasce da ci_apply e sulla CI puo' NON ESISTERE, quindi
--   lo si spegne solo se c'e' (pg_trigger), mai con un DDL a secco.
--
-- ⚠️ `data_update` si scrive a mano, indietro nel tempo: la soglia e' una
--   regola sul dato e si prova sul dato. Non si aspetta un'ora.
-- ------------------------------------------------------------

BEGIN;

DO $ctx$ BEGIN PERFORM script.fn_pgtap_set_contesto_operatore(); END $ctx$;

SET CONSTRAINTS ALL IMMEDIATE;

SELECT plan(6);

-- ============================================================
-- Fixture: quattro fatture libere dell'operatore, sei righe di coda
-- ============================================================
-- ⚠️ Senza un emittente attivo fn_pgtap_emittente_operatore() SOLLEVA. E non
--   basta metterla dentro un CASE in una query: l'helper e' STABLE, e il
--   pianificatore puo' eseguirlo gia' in fase di STIMA della WHERE — prima
--   che la query giri e prima che il CASE decida. ⇒ La chiamata e'
--   PROCEDURALE, dentro un IF: dove il ramo non entra, non viene nemmeno
--   pianificata. Su un database da zero `ids` resta NULL e i test sotto lo
--   dichiarano.
CREATE TEMP TABLE _fat (ids bigint[], tipo_id bigint);

DO $fat$
DECLARE
    v_sr   bigint;
    v_ids  bigint[];
    v_tipo bigint;
BEGIN
    SELECT s.id INTO v_tipo FROM config.sorgenti s WHERE s.codice_interno = 'FATTURA';

    IF EXISTS (SELECT 1 FROM anagrafiche.emittenti_fiscali WHERE attivo) THEN
        v_sr := script.fn_pgtap_emittente_sr_operatore();
    END IF;

    IF v_sr IS NOT NULL THEN
        SELECT array_agg(q.id ORDER BY q.id) INTO v_ids
          FROM (SELECT f.id
                  FROM vendite.fatture f
                 WHERE f.emittente_soggetto_ruolo_id = v_sr
                   AND NOT EXISTS (SELECT 1 FROM vendite.fatture_stampa_coda c
                                    WHERE c.sorgente_id = f.id
                                      AND c.stato IN ('PENDING', 'IN_CORSO'))
                 ORDER BY f.id
                 LIMIT 4) q;
    END IF;

    INSERT INTO _fat (ids, tipo_id) VALUES (v_ids, v_tipo);
END
$fat$;

-- ⚠️ L'audit trigger riporterebbe data_update a now(): si spegne nella
--   transazione, e il ROLLBACK lo riaccende. E' l'unico DDL del file.
-- ⛔ SOLO SE ESISTE: quel trigger lo genera ci_apply, e sulla CI senza
--   automazioni non c'e'. Un DDL a secco farebbe morire il file prima dello
--   skip — e' la regola «niente DDL su un trigger che nasce da ci_apply».
DO $trg$
BEGIN
    IF EXISTS (SELECT 1 FROM pg_trigger
                WHERE tgrelid = 'vendite.fatture_stampa_coda'::regclass
                  AND tgname  = 'trg_fatture_stampa_coda_audit_data_user_upd') THEN
        ALTER TABLE vendite.fatture_stampa_coda
            DISABLE TRIGGER trg_fatture_stampa_coda_audit_data_user_upd;
    END IF;
END
$trg$;

DO $fixture$
DECLARE
    v_ids  bigint[];
    v_tipo bigint;
BEGIN
    SELECT ids, tipo_id INTO v_ids, v_tipo FROM _fat;
    IF coalesce(array_length(v_ids, 1), 0) < 4 OR v_tipo IS NULL THEN
        RETURN;  -- i test sotto lo dichiarano con skip()
    END IF;
    -- ⭐ Ogni riga porta il proprio nome in ultimo_errore (jsonb, chiave pgtap):
    --   le asserzioni
    --   interrogano il presidio per NOME, cosi' le righe vere gia' presenti
    --   non falsano niente.
    INSERT INTO vendite.fatture_stampa_coda
        (sorgente_tipo_id, sorgente_id, ultimo_errore, stato, tentativi, data_update)
    VALUES
        -- 1) si e' arresa (non viva: puo' condividere la fattura con la 2)
        (v_tipo, v_ids[1], '{"pgtap": "errore"}',           'ERRORE',   5, now()),
        -- 2) presa e mai chiusa: il worker e' morto a meta'
        (v_tipo, v_ids[1], '{"pgtap": "in_corso_stantio"}', 'IN_CORSO', 1, now() - interval '3 hours'),
        -- 3) ⛔ mai presa: nessuno sta drenando la coda
        (v_tipo, v_ids[2], '{"pgtap": "pending_vecchio"}',  'PENDING',  0, now() - interval '3 hours'),
        -- 4) appena accodata: e' normale
        (v_tipo, v_ids[3], '{"pgtap": "pending_fresco"}',   'PENDING',  0, now()),
        -- 5) appena presa: sta lavorando
        (v_tipo, v_ids[4], '{"pgtap": "in_corso_fresco"}',  'IN_CORSO', 1, now());
    -- 6) fallita, ma gia' guardata e messa via
    INSERT INTO vendite.fatture_stampa_coda
        (sorgente_tipo_id, sorgente_id, ultimo_errore, stato, tentativi, data_update,
         archiviato, archiviato_il, archiviato_da)
    VALUES
        (v_tipo, v_ids[1], '{"pgtap": "archiviato"}', 'ERRORE', 5, now(), true, now(), 'pgtap');
END
$fixture$;

DO $trg$
BEGIN
    IF EXISTS (SELECT 1 FROM pg_trigger
                WHERE tgrelid = 'vendite.fatture_stampa_coda'::regclass
                  AND tgname  = 'trg_fatture_stampa_coda_audit_data_user_upd') THEN
        ALTER TABLE vendite.fatture_stampa_coda
            ENABLE TRIGGER trg_fatture_stampa_coda_audit_data_user_upd;
    END IF;
END
$trg$;

CREATE TEMP TABLE _costruita AS
SELECT coalesce(array_length(ids, 1), 0) >= 4 AND tipo_id IS NOT NULL AS ok FROM _fat;

-- ============================================================
-- 1..3. ⛔ I tre guasti, e i tre motivi
-- ============================================================
SELECT CASE WHEN NOT (SELECT ok FROM _costruita)
    THEN skip('1. coda stampa: servono 4 fatture libere dell''operatore, non ci sono', 1)
    ELSE is(
        (SELECT motivo FROM dbops.vw_fatture_stampa_coda_da_guardare
          WHERE ultimo_errore ->> 'pgtap' = 'errore'),
        'fallito: tentativi esauriti',
        '1. la stampa fallita compare, e il motivo lo dice')
    END;

SELECT CASE WHEN NOT (SELECT ok FROM _costruita)
    THEN skip('2. coda stampa: servono 4 fatture libere dell''operatore, non ci sono', 1)
    ELSE is(
        (SELECT motivo FROM dbops.vw_fatture_stampa_coda_da_guardare
          WHERE ultimo_errore ->> 'pgtap' = 'in_corso_stantio'),
        'preso e mai chiuso: il worker e'' morto a meta''',
        '2. IN_CORSO da oltre un''ora compare: il worker e'' morto a meta'' (e il reaper non e'' passato)')
    END;

-- ⭐ Il caso che conta di piu' e si vede di meno.
SELECT CASE WHEN NOT (SELECT ok FROM _costruita)
    THEN skip('3. coda stampa: servono 4 fatture libere dell''operatore, non ci sono', 1)
    ELSE is(
        (SELECT motivo FROM dbops.vw_fatture_stampa_coda_da_guardare
          WHERE ultimo_errore ->> 'pgtap' = 'pending_vecchio'),
        'mai preso: il drenatore della stampa non sta girando',
        '3. PENDING da oltre un''ora compare: il drenatore della stampa non sta girando')
    END;

-- ============================================================
-- 4..6. ✅ Cio' che NON deve comparire
-- ============================================================
SELECT CASE WHEN NOT (SELECT ok FROM _costruita)
    THEN skip('4. coda stampa: servono 4 fatture libere dell''operatore, non ci sono', 1)
    ELSE is_empty(
        $$SELECT id FROM dbops.vw_fatture_stampa_coda_da_guardare
           WHERE ultimo_errore ->> 'pgtap' = 'pending_fresco'$$,
        '4. una stampa appena accodata non compare: la soglia esiste davvero')
    END;

SELECT CASE WHEN NOT (SELECT ok FROM _costruita)
    THEN skip('5. coda stampa: servono 4 fatture libere dell''operatore, non ci sono', 1)
    ELSE is_empty(
        $$SELECT id FROM dbops.vw_fatture_stampa_coda_da_guardare
           WHERE ultimo_errore ->> 'pgtap' = 'in_corso_fresco'$$,
        '5. una stampa appena presa non compare: sta lavorando')
    END;

SELECT CASE WHEN NOT (SELECT ok FROM _costruita)
    THEN skip('6. coda stampa: servono 4 fatture libere dell''operatore, non ci sono', 1)
    ELSE is_empty(
        $$SELECT id FROM dbops.vw_fatture_stampa_coda_da_guardare
           WHERE ultimo_errore ->> 'pgtap' = 'archiviato'$$,
        '6. una stampa archiviata non compare: qualcuno l''ha gia'' guardata')
    END;

SELECT * FROM finish();

ROLLBACK;
