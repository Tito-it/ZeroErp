-- ------------------------------------------------------------
-- SPDX-License-Identifier: GPL-3.0-or-later
-- pgTAP test per Zero ERP
--
-- Test: l'istanza nasce e vive col suo billing account; un'istanza, un emittente.
-- Riferimento: brief-db-istanza-nasce-col-ba (R-6; regola di Tid del 2026-10-08,
--   D-2 «per coppia (istanza, utility)», D-4 «un'istanza, un emittente»).
--
-- Semantica attesa (il contratto, non l'implementazione):
--   - un'istanza senza billing account non arriva al COMMIT;
--   - l'ultimo billing account di un'istanza che resta non si cancella, ma
--     istanza e BA se ne vanno insieme;
--   - i dati precontrattuali di una coppia esistono solo col BA della coppia;
--   - il billing account di un preventivo, di un'offerta o di un contratto e'
--     quello della sua coppia, e il preventivo lo ha sempre;
--   - i billing account di un'istanza sono tutti dello stesso emittente;
--   - la coppia (istanza, utility) di un BA non si cambia.
--
-- Elenco test (plan 13):
--    1) istanza senza BA -> E_ISTANZA_SENZA_BA al COMMIT
--    2) istanza + BA nella stessa transazione -> vive
--    3) cancellare l'ultimo BA di un'istanza che resta -> E_ISTANZA_SENZA_BA
--    4) cancellare istanza e BA insieme -> vive
--    5) struttura: i dati precontrattuali hanno la FK composta verso la coppia
--       del BA (fk_idp_billing_account_coppia). Sul catalogo e non per INSERT:
--       sotto RLS il WITH CHECK della policy parla prima della FK (42501)
--    6) dati precontrattuali sulla coppia del BA -> vive
--    7) secondo BA della stessa istanza, stesso emittente -> vive
--    8) preventivo col BA di un'altra coppia -> fk_preventivi_ba_coppia
--    9) preventivo senza BA -> 23502 (il guard dell'emittente lascia parlare il vincolo)
--   10) il secondo BA spostato su un altro emittente -> E_ISTANZA_EMITTENTI_DIVERSI
--   11) la check della coppia: true col BA, false senza
--   12) struttura: le FK composte di offerte e contratti esistono
--   13) lock della coppia del BA -> E_BA_ISTANZA_IMMUTABILE
--       ⚠️ il trigger di lock lo genera l'automazione (dbops.automation_lock_columns)
--       a ci_apply o col job notturno: finche' non c'e', il test fa skip()
--       dichiarato invece di passare a vuoto.
--
-- ⚠️ Non provato qui: lo spostamento del gestore globale
--   (fn_guard_istanza_ba_gestore_globale). Con un operatore in sessione un BA
--   senza collegamento risolve all'emittente di chi agisce (livello 2 di
--   script.fn_get_ba_emittente_sr_id): il caso «uno collegato, uno no» si
--   costruisce nel contesto di un super admin senza azienda, e sta in
--   anagrafiche/test-istanza-ba-gestore-globale-v1.sql (dal 2026-10-10,
--   brief-db-istanza-nasce-col-ba-residui D-4).
-- ------------------------------------------------------------

BEGIN;

-- ⚠️ Vincoli DIFFERITI: in testa. I casi che li vogliono differiti riaprono
--   la finestra da se' e la richiudono per far scattare il controllo.
SET CONSTRAINTS ALL IMMEDIATE;

-- pgtap-contesto: escluso — il contesto lo apre dbops.fn_pgtap_crea_preventivo
--   (mondo con emittente e operatore propri): il preventivo, il BA e il guard
--   dell'emittente devono parlare dello STESSO emittente, quello del mondo.

SELECT plan(13);

-- Il codice di dominio di un errore, letto dal canale CONSTRAINT (contratto
-- P0001 + CONSTRAINT = codice); per gli errori di vincolo, SQLSTATE e nome del
-- vincolo. NULL se non solleva.
CREATE OR REPLACE FUNCTION pg_temp.esito(p_sql text) RETURNS text
LANGUAGE plpgsql AS $$
DECLARE v_s text; v_c text;
BEGIN
    EXECUTE p_sql;
    RETURN NULL;
EXCEPTION WHEN OTHERS THEN
    GET STACKED DIAGNOSTICS v_s = RETURNED_SQLSTATE, v_c = CONSTRAINT_NAME;
    RETURN CASE WHEN v_s = 'P0001' THEN v_c ELSE v_s || ' ' || coalesce(v_c, '') END;
END $$;

-- ============================================================
-- Fixture: il mondo (emittente E, operatore in sessione, cliente con BA X
-- sulla coppia (istanza A, utility U), preventivo P in bozza).
-- ⛔ Cio' che il builder scrive si legge in un'istruzione SEPARATA.
-- ============================================================
CREATE TEMP TABLE t_w AS
SELECT * FROM dbops.fn_pgtap_crea_preventivo('istanza nasce col BA');

CREATE TEMP TABLE t_v AS
SELECT (SELECT iu.soggetto_id FROM anagrafiche.istanze_utilities iu
         WHERE iu.id = w.istanza_utility_id)                        AS soggetto_id,
       (SELECT ba.categoria_cliente_id FROM anagrafiche.billing_account ba
         WHERE ba.id = w.billing_account_id)                        AS categoria_id,
       (SELECT u.id FROM config.utilities u
         WHERE u.id <> w.utility_id ORDER BY u.id LIMIT 1)          AS utility_2,
       NULL::bigint AS istanza_b,
       NULL::bigint AS ba_b,
       NULL::bigint AS ba_2
  FROM t_w w;

-- ============================================================
-- 1) Istanza senza BA -> E_ISTANZA_SENZA_BA al COMMIT
-- ============================================================
SELECT is(
    pg_temp.esito($sql$
        DO $c$ BEGIN
            SET CONSTRAINTS ALL DEFERRED;
            INSERT INTO anagrafiche.istanze_utilities (fittizia, proprietario_inquilino, soggetto_id)
            VALUES (true, 'I', (SELECT soggetto_id FROM t_v));
            SET CONSTRAINTS ALL IMMEDIATE;
        END $c$ $sql$),
    'E_ISTANZA_SENZA_BA',
    '1. Istanza senza billing account: al COMMIT E_ISTANZA_SENZA_BA'
);

-- ============================================================
-- 2) Istanza + BA nella stessa transazione -> vive
-- ============================================================
SELECT lives_ok(
    $sql$
    DO $c$
    DECLARE v_ist bigint; v_ba bigint;
    BEGIN
        SET CONSTRAINTS ALL DEFERRED;
        INSERT INTO anagrafiche.istanze_utilities (fittizia, proprietario_inquilino, soggetto_id)
        VALUES (true, 'I', (SELECT soggetto_id FROM t_v))
        RETURNING id INTO v_ist;
        INSERT INTO anagrafiche.billing_account
            (istanza_utility_id, soggetto_ruolo_id, utility_id, categoria_cliente_id)
        SELECT v_ist, w.cliente_soggetto_ruolo_id, w.utility_id, v.categoria_id
          FROM t_w w, t_v v
        RETURNING id INTO v_ba;
        SET CONSTRAINTS ALL IMMEDIATE;
        UPDATE t_v SET istanza_b = v_ist, ba_b = v_ba;
    END $c$
    $sql$,
    '2. Istanza e billing account nella stessa transazione: vive'
);

-- ============================================================
-- 3) Cancellare l'ultimo BA di un'istanza che resta -> E_ISTANZA_SENZA_BA
--    Prima il collegamento all'emittente (FK fk_emittenti_fiscali_billing_account_ba).
-- ============================================================
SELECT is(
    pg_temp.esito($sql$
        DO $c$ BEGIN
            SET CONSTRAINTS ALL DEFERRED;
            DELETE FROM anagrafiche.emittenti_fiscali_billing_account
             WHERE billing_account_id = (SELECT ba_b FROM t_v);
            DELETE FROM anagrafiche.billing_account WHERE id = (SELECT ba_b FROM t_v);
            SET CONSTRAINTS ALL IMMEDIATE;
        END $c$ $sql$),
    'E_ISTANZA_SENZA_BA',
    '3. L''ultimo billing account di un''istanza che resta non si cancella: E_ISTANZA_SENZA_BA'
);

-- ============================================================
-- 4) Istanza e BA se ne vanno insieme -> vive
--    ⚠️ E' l'ultimo uso dell'istanza B: dopo, nel file non c'e' piu'.
-- ============================================================
SELECT lives_ok(
    $sql$
    DO $c$ BEGIN
        SET CONSTRAINTS ALL DEFERRED;
        DELETE FROM anagrafiche.emittenti_fiscali_billing_account
         WHERE billing_account_id = (SELECT ba_b FROM t_v);
        DELETE FROM anagrafiche.billing_account WHERE id = (SELECT ba_b FROM t_v);
        DELETE FROM anagrafiche.istanze_utilities WHERE id = (SELECT istanza_b FROM t_v);
        SET CONSTRAINTS ALL IMMEDIATE;
    END $c$
    $sql$,
    '4. Istanza e billing account cancellati insieme: vive'
);

-- ============================================================
-- 5) Dati precontrattuali su una coppia senza BA -> FK composta
-- ============================================================
-- ⛔ Sulla STRUTTURA, non per INSERT. La tabella ha RLS, e il WITH CHECK
--   della policy (il BA da script.fn_get_ba_id_da_coppia, 20261021-26) vede la coppia
--   solo attraverso un suo BA: PostgreSQL valuta il WITH CHECK all'INSERT,
--   PRIMA della FK, quindi col runner una coppia senza BA esce 42501 e la
--   FK non si raggiunge mai (come owner, senza RLS, darebbe 23503). Pinnare
--   il 42501 sarebbe pinnare il sintomo: la regola e' la FK, e la FK si
--   legge dal catalogo, come il test 12.
-- ⚠️ Colonne per NOME da pg_attribute e non pg_get_constraintdef: quella
--   stampa lo schema secondo il search_path di chi legge.
SELECT is(
    (SELECT string_agg(a.attname || '->' || ra.attname, ',' ORDER BY k.ord)
       FROM pg_constraint c
       CROSS JOIN LATERAL unnest(c.conkey, c.confkey) WITH ORDINALITY AS k(col, rcol, ord)
       JOIN pg_attribute a  ON a.attrelid  = c.conrelid  AND a.attnum  = k.col
       JOIN pg_attribute ra ON ra.attrelid = c.confrelid AND ra.attnum = k.rcol
      WHERE c.contype   = 'f'
        AND c.conrelid  = 'anagrafiche.istanze_dati_precontrattuali'::regclass
        AND c.confrelid = 'anagrafiche.billing_account'::regclass
        AND c.conname   = 'fk_idp_billing_account_coppia'),
    'istanza_utility_id->istanza_utility_id,utility_id->utility_id',
    '5. Dati precontrattuali solo su una coppia con billing account: FK composta fk_idp_billing_account_coppia'
);

-- ============================================================
-- 6) Dati precontrattuali sulla coppia del BA -> vive
-- ============================================================
SELECT lives_ok(
    $sql$
    INSERT INTO anagrafiche.istanze_dati_precontrattuali (istanza_utility_id, utility_id)
    SELECT w.istanza_utility_id, w.utility_id FROM t_w w
    $sql$,
    '6. Dati precontrattuali sulla coppia del billing account: vivono'
);

-- ============================================================
-- 7) Secondo BA della stessa istanza (utility 2), stesso operatore -> vive
-- ============================================================
SELECT lives_ok(
    $sql$
    DO $c$
    DECLARE v_ba bigint;
    BEGIN
        INSERT INTO anagrafiche.billing_account
            (istanza_utility_id, soggetto_ruolo_id, utility_id, categoria_cliente_id)
        SELECT w.istanza_utility_id, w.cliente_soggetto_ruolo_id, v.utility_2, v.categoria_id
          FROM t_w w, t_v v
        RETURNING id INTO v_ba;
        UPDATE t_v SET ba_2 = v_ba;
    END $c$
    $sql$,
    '7. Secondo billing account della stessa istanza, stesso emittente: vive'
);

-- ============================================================
-- 8) Preventivo col BA di un'altra coppia -> FK composta
--    Il BA 2 e' dello stesso emittente (il guard dell'emittente tace) e la
--    coppia del preventivo ha il suo BA (il guard di coerenza tace): parla la FK.
-- ============================================================
SELECT is(
    pg_temp.esito($sql$
        UPDATE vendite.preventivi SET billing_account_id = (SELECT ba_2 FROM t_v)
         WHERE id = (SELECT preventivo_id FROM t_w) $sql$),
    '23503 fk_preventivi_ba_coppia',
    '8. Preventivo col billing account di un''altra coppia: fk_preventivi_ba_coppia'
);

-- ============================================================
-- 9) Preventivo senza BA -> 23502
-- ============================================================
SELECT is(
    left(pg_temp.esito($sql$
        UPDATE vendite.preventivi SET billing_account_id = NULL
         WHERE id = (SELECT preventivo_id FROM t_w) $sql$), 5),
    '23502',
    '9. Preventivo senza billing account: 23502 (il guard dell''emittente lascia parlare il NOT NULL)'
);

-- ============================================================
-- 10) Il secondo BA spostato su un altro emittente -> E_ISTANZA_EMITTENTI_DIVERSI
-- ============================================================
-- ⛔ Il builder scrive; si legge in un'istruzione SEPARATA.
CREATE TEMP TABLE t_altro AS
SELECT * FROM dbops.fn_pgtap_crea_emittente();

SELECT is(
    pg_temp.esito($sql$
        UPDATE anagrafiche.emittenti_fiscali_billing_account
           SET emittente_soggetto_ruolo_id = (SELECT soggetto_ruolo_id FROM t_altro)
         WHERE billing_account_id = (SELECT ba_2 FROM t_v) $sql$),
    'E_ISTANZA_EMITTENTI_DIVERSI',
    '10. Un billing account dell''istanza su un altro emittente: E_ISTANZA_EMITTENTI_DIVERSI'
);

-- ============================================================
-- 11) La check della coppia: true col BA, false senza
-- ============================================================
SELECT is(
    (SELECT script.fn_check_utility_istanza_coerenza(w.istanza_utility_id, w.utility_id)::text
            || '/' ||
            script.fn_check_utility_istanza_coerenza(
                w.istanza_utility_id,
                (SELECT u.id FROM config.utilities u
                  WHERE NOT EXISTS (SELECT 1 FROM anagrafiche.billing_account b
                                     WHERE b.istanza_utility_id = w.istanza_utility_id
                                       AND b.utility_id = u.id)
                  ORDER BY u.id LIMIT 1))::text
       FROM t_w w),
    'true/false',
    '11. fn_check_utility_istanza_coerenza: true sulla coppia col BA, false su quella senza'
);

-- ============================================================
-- 12) Struttura: le FK composte di offerte e contratti esistono
-- ============================================================
SELECT is(
    (SELECT count(*)::int FROM pg_constraint c
      WHERE c.contype = 'f'
        AND c.confrelid = 'anagrafiche.billing_account'::regclass
        AND (c.conrelid, c.conname) IN (
              ('vendite.offerte_commerciali'::regclass, 'fk_offerte_commerciali_ba_coppia'),
              ('vendite.contratti'::regclass,           'fk_contratti_ba_coppia'))
        AND array_length(c.conkey, 1) = 3),
    2,
    '12. Offerte e contratti: FK composta (billing_account_id, istanza_utility_id, utility_id)'
);

-- ============================================================
-- 13) Lock della coppia del BA -> E_BA_ISTANZA_IMMUTABILE
--     Il trigger lo genera l'automazione: si cerca per funzione e argomenti.
--     Si cambia utility_id del BA 2 (verso quella del BA X): il lock e' BEFORE
--     e parla prima dell'unicita' (istanza, utility). ⚠️ Fino al 2026-10-09 il
--     cambio di istanza_utility_id verso l'istanza di un ALTRO soggetto lo
--     intercettava prima il guard di coerenza (allora in fascia _a10_, g < l),
--     con E_BA_SOGGETTO_INCOERENTE_ISTANZA. Da 20261009-69 il guard e' in
--     _a20_: parla il lock, per ogni cambio (brief-db-esecutivi-ba-coppia, D-7).
-- ============================================================
SELECT CASE
    WHEN EXISTS (
        SELECT 1 FROM pg_trigger t
         WHERE t.tgrelid = 'anagrafiche.billing_account'::regclass
           AND t.tgfoid = 'script.trgfn_lock_columns()'::regprocedure
           AND encode(t.tgargs, 'escape') LIKE '%utility_id%E_BA_ISTANZA_IMMUTABILE%')
    THEN is(
        pg_temp.esito($sql$
            UPDATE anagrafiche.billing_account
               SET utility_id = (SELECT utility_id FROM t_w)
             WHERE id = (SELECT ba_2 FROM t_v) $sql$),
        'E_BA_ISTANZA_IMMUTABILE',
        '13. La coppia del billing account non si cambia: E_BA_ISTANZA_IMMUTABILE')
    ELSE skip('13. lock della coppia del BA non ancora generato da automation_lock_columns (ci_apply o job notturno)', 1)
END;

SELECT * FROM finish();
ROLLBACK;
