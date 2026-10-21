-- ------------------------------------------------------------
-- SPDX-License-Identifier: GPL-3.0-or-later
-- pgTAP test per Zero ERP
--
-- Test: il perimetro di chi guarda da controparte, e il suo confronto
--   script.fn_get_identita_sr_perimetro(identita, vesti)
--   script.fn_scope_sr_perimetro(perimetro, soggetto)
--   Brief: brief-db-perimetro-una-volta-famiglie-residue §6 e §8
--   (changeSet 20261021-29; prende il posto di script/test-fn-scope-cliente-ownership,
--   ritirato con fn_scope_cliente_ownership dal 20261021-40).
--
-- Semantica attesa:
--   - il perimetro e' il soggetto dell'identita', se e' in una delle vesti date
--     ed e' utilizzabile oggi; NULL altrimenti (NULL = NESSUNO);
--   - il confronto e' vero solo quando perimetro e soggetto ci sono e coincidono.
-- ⛔ SI COSTRUISCE TUTTO: tre soggetti cliente, tre credenziali, tre vesti
--   (una CLIENTE_PORTALE accesa, una SHOP_CUSTOMER accesa, una CLIENTE_PORTALE
--   spenta). Un'identita' attiva per soggetto: uq_identita_digitali_soggetto_ruolo_attivo.
--
-- Indice test (plan 12):
--    1. precondizione: tre soggetti distinti, costruiti, senza identita'
--    2. identita' inesistente -> NULL
--    3. identita' NULL -> NULL
--    4. identita' spenta -> NULL
--    5. CLIENTE_PORTALE accesa, veste CLIENTE_PORTALE -> il suo soggetto
--    6. SHOP_CUSTOMER accesa, veste SHOP_CUSTOMER -> il suo soggetto
--    7. ⭐ CLIENTE_PORTALE chiesta per la veste SHOP_CUSTOMER -> NULL (la policy
--       passa la veste del proprio gate)
--    8. CLIENTE_PORTALE chiesta per le due vesti di cliente -> il suo soggetto
--    9. il confronto: perimetro = soggetto -> true
--   10. ⛔ il confronto: soggetto di un altro cliente -> false (leak)
--   11. ⛔ il confronto: perimetro NULL (nessuno) -> false, non NULL
--   12. ⛔ il confronto: soggetto NULL -> false, non NULL
-- BEGIN; + rollback a fine file.
-- ------------------------------------------------------------

BEGIN;

-- ⚠️ Vincoli DIFFERITI: scattano al COMMIT, e qui il COMMIT non arriva mai.
SET CONSTRAINTS ALL IMMEDIATE;

-- Contesto applicativo: il test gira come gira l'applicazione (OPERATORE + RLS).
DO $ctx$ BEGIN PERFORM script.fn_pgtap_set_contesto_operatore(); END $ctx$;

SELECT plan(12);

CREATE TEMP TABLE _sr AS
SELECT dbops.fn_pgtap_crea_soggetto_ruolo(
           dbops.fn_pgtap_crea_soggetto_pg('Perimetro controparte pgTAP ' || g), 'CL'::character varying) AS sr_id,
       g AS rn
  FROM generate_series(1, 3) AS g;

SELECT ok(
    (SELECT count(DISTINCT sr_id) FROM _sr) = 3
    AND NOT EXISTS (SELECT 1 FROM anagrafiche.identita_digitali id
                     WHERE id.soggetto_ruolo_id IN (SELECT sr_id FROM _sr)),
    '1. precondizione: tre soggetti distinti, costruiti, senza identita'''
);

-- Le tre vesti, su tre credenziali costruite.
CREATE TEMP TABLE _id (rn int, identita_id bigint);
DO $vesti$
DECLARE
    v_i  int;
    v_au int;
BEGIN
    FOR v_i IN 1..3 LOOP
        INSERT INTO django.auth_user (
            username, password, is_active, is_staff, is_superuser,
            first_name, last_name, email, date_joined)
        VALUES ('_pgtap_perim_' || v_i || '_' || substring(md5(clock_timestamp()::text) from 1 for 6),
                '!', true, false, false, '', '', '', now())
        RETURNING id INTO v_au;
        INSERT INTO _id
        SELECT v_i, anagrafiche.fn_crea_veste_portale(
                   v_au, (SELECT sr_id FROM _sr WHERE rn = v_i),
                   CASE v_i WHEN 2 THEN 'SHOP_CUSTOMER' ELSE 'CLIENTE_PORTALE' END::config.ruolo_applicativo,
                   v_i <> 3);
    END LOOP;
END
$vesti$;

-- ============================================================
-- 2..8. Il perimetro
-- ============================================================
SELECT is(script.fn_get_identita_sr_perimetro(
              (SELECT coalesce(max(id), 0) + 999999 FROM anagrafiche.identita_digitali),
              ARRAY['CLIENTE_PORTALE']::config.ruolo_applicativo[]),
          NULL::bigint,
          '2. identita'' inesistente -> NULL');

SELECT is(script.fn_get_identita_sr_perimetro(NULL, ARRAY['CLIENTE_PORTALE']::config.ruolo_applicativo[]),
          NULL::bigint,
          '3. identita'' NULL -> NULL');

SELECT is(script.fn_get_identita_sr_perimetro((SELECT identita_id FROM _id WHERE rn = 3),
                                              ARRAY['CLIENTE_PORTALE']::config.ruolo_applicativo[]),
          NULL::bigint,
          '4. identita'' spenta -> NULL');

SELECT is(script.fn_get_identita_sr_perimetro((SELECT identita_id FROM _id WHERE rn = 1),
                                              ARRAY['CLIENTE_PORTALE']::config.ruolo_applicativo[]),
          (SELECT sr_id FROM _sr WHERE rn = 1),
          '5. CLIENTE_PORTALE accesa, veste CLIENTE_PORTALE -> il suo soggetto');

SELECT is(script.fn_get_identita_sr_perimetro((SELECT identita_id FROM _id WHERE rn = 2),
                                              ARRAY['SHOP_CUSTOMER']::config.ruolo_applicativo[]),
          (SELECT sr_id FROM _sr WHERE rn = 2),
          '6. SHOP_CUSTOMER accesa, veste SHOP_CUSTOMER -> il suo soggetto');

SELECT is(script.fn_get_identita_sr_perimetro((SELECT identita_id FROM _id WHERE rn = 1),
                                              ARRAY['SHOP_CUSTOMER']::config.ruolo_applicativo[]),
          NULL::bigint,
          '7. CLIENTE_PORTALE chiesta per la veste SHOP_CUSTOMER -> NULL');

SELECT is(script.fn_get_identita_sr_perimetro((SELECT identita_id FROM _id WHERE rn = 1),
                                              ARRAY['CLIENTE_PORTALE', 'SHOP_CUSTOMER']::config.ruolo_applicativo[]),
          (SELECT sr_id FROM _sr WHERE rn = 1),
          '8. CLIENTE_PORTALE chiesta per le due vesti di cliente -> il suo soggetto');

-- ============================================================
-- 9..12. Il confronto
-- ============================================================
SELECT is(script.fn_scope_sr_perimetro((SELECT sr_id FROM _sr WHERE rn = 1), (SELECT sr_id FROM _sr WHERE rn = 1)),
          true, '9. il confronto: perimetro = soggetto -> true');

SELECT is(script.fn_scope_sr_perimetro((SELECT sr_id FROM _sr WHERE rn = 1), (SELECT sr_id FROM _sr WHERE rn = 2)),
          false, '10. il confronto: soggetto di un altro cliente -> false');

SELECT is(script.fn_scope_sr_perimetro(NULL, (SELECT sr_id FROM _sr WHERE rn = 1)),
          false, '11. il confronto: perimetro NULL (nessuno) -> false, non NULL');

SELECT is(script.fn_scope_sr_perimetro((SELECT sr_id FROM _sr WHERE rn = 1), NULL),
          false, '12. il confronto: soggetto NULL -> false, non NULL');

SELECT * FROM finish();
ROLLBACK;
