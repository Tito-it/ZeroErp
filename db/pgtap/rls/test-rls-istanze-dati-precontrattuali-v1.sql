-- ------------------------------------------------------------
-- SPDX-License-Identifier: AGPL-3.0-or-later
-- pgtap-runner: owner
-- pgtap-runner-motivo: ALTER TABLE … FORCE ROW LEVEL SECURITY, locale alla
--   transazione — e' il FORCE a rendere l'owner soggetto alle policy. E la
--   fixture costruisce DUE aziende: un operatore dentro un perimetro non
--   potrebbe crearle. Stesso criterio di rls/test-rls-preventivi-satelliti.
-- pgTAP test FUNZIONALE RLS — anagrafiche.istanze_dati_precontrattuali
--   Brief: brief-db-istanza-nasce-col-ba (§6.13, opzione A di Tid del 2026-10-08)
--
-- Elenco test (plan 8):
--  1) struttura: la policy c'e'
--  2) struttura: e la RLS e' ACCESA — non basta che la policy esista
--  3) struttura: la vista di dettaglio e' security_invoker (non scavalca)
--  4) l'operatore A vede i dati precontrattuali del PROPRIO cliente
--  5) ⛔ e NON quelli del cliente di B
--  6) ⛔ SCRITTURA: A non puo' scrivere dati precontrattuali sulla coppia di
--     un cliente di B (WITH CHECK)
--  7) ⛔ senza veste non vede NIENTE — fail-closed
--  8) il presidio del perimetro RLS non la elenca piu'
--
-- ⭐ La regola e' quella del BA: la policy chiede il perimetro dell'operatore
--   (una volta per istruzione) e l'emittente del BA della coppia, trovato da
--   script.fn_get_ba_id_da_coppia (rev 2026-10-21, 20261021-26: prima
--   script.fn_scope_ef_whitelist_via_coppia leggeva il BA sotto la sua RLS).
--   Il FORCE su anagrafiche.billing_account resta: il risolutore e' DEFINER
--   del proprietario e la scavalca, ed e' cio' che si prova qui — con la RLS
--   del BA accesa, A vede ancora il proprio cliente (4) e non quello di B (5).
-- ⛔ LA FIXTURE SI COSTRUISCE: due aziende (dbops.fn_pgtap_crea_emittente_operatore)
--   e tre clienti col BA legato esplicitamente all'azienda del loro lato.
-- ------------------------------------------------------------

BEGIN;

SET CONSTRAINTS ALL IMMEDIATE;

SELECT plan(8);

-- ============================================================
-- I due mondi e i clienti
-- ============================================================
CREATE TEMP TABLE _mondi AS
SELECT 'A' AS lato, * FROM dbops.fn_pgtap_crea_emittente_operatore()
UNION ALL
SELECT 'B' AS lato, * FROM dbops.fn_pgtap_crea_emittente_operatore();

-- A: un cliente coi suoi dati precontrattuali. B: uno coi dati, uno senza
-- (la coppia su cui A prova a scrivere). ⛔ Si legge separato.
CREATE TEMP TABLE _clienti AS
SELECT x.chiave, m.lato, m.auth_user_id, c.*
  FROM (VALUES ('A', 'A'), ('B', 'B'), ('B2', 'B')) x(chiave, lato)
  JOIN _mondi m ON m.lato = x.lato
  CROSS JOIN LATERAL dbops.fn_pgtap_crea_cliente_ba(
        'RLS dati precontrattuali ' || x.chiave, NULL, m.soggetto_ruolo_id) c;

INSERT INTO anagrafiche.istanze_dati_precontrattuali (istanza_utility_id, utility_id)
SELECT c.istanza_utility_id, c.utility_id
  FROM _clienti c
 WHERE c.chiave IN ('A', 'B');

-- ============================================================
-- 1..3. La struttura
-- ============================================================
SELECT ok(
    EXISTS (SELECT 1 FROM pg_policy
             WHERE polrelid = 'anagrafiche.istanze_dati_precontrattuali'::regclass
               AND polname = 'rls_istanze_dati_precontrattuali_ef_whitelist'),
    '1. la policy rls_istanze_dati_precontrattuali_ef_whitelist c''e'''
);

SELECT ok(
    (SELECT c.relrowsecurity FROM pg_class c
      WHERE c.oid = 'anagrafiche.istanze_dati_precontrattuali'::regclass),
    '2. e la RLS e'' ACCESA, non solo dichiarata'
);

SELECT ok(
    (SELECT coalesce(c.reloptions, '{}') @> ARRAY['security_invoker=on']
            OR coalesce(c.reloptions, '{}') @> ARRAY['security_invoker=true']
       FROM pg_class c
      WHERE c.oid = 'anagrafiche.vw_istanze_dati_precontrattuali_dettaglio'::regclass),
    '3. la vista di dettaglio e'' security_invoker: non scavalca la RLS'
);

-- ============================================================
-- Il perimetro, esercitato
-- ============================================================
-- FORCE locale alla transazione: senza, l'owner sarebbe esente e il test
-- misurerebbe tutto. Il ROLLBACK finale lo annulla.
ALTER TABLE anagrafiche.billing_account              FORCE ROW LEVEL SECURITY;
ALTER TABLE anagrafiche.istanze_dati_precontrattuali FORCE ROW LEVEL SECURITY;

DO $perimetro$
DECLARE
    v_a  record;
    v_b  record;
    v_b2 record;
    n    integer;
BEGIN
    SELECT * INTO v_a  FROM _clienti WHERE chiave = 'A';
    SELECT * INTO v_b  FROM _clienti WHERE chiave = 'B';
    SELECT * INTO v_b2 FROM _clienti WHERE chiave = 'B2';

    -- La veste dell'operatore A, come la darebbe il middleware.
    PERFORM script.fn_pgtap_set_contesto_operatore(v_a.auth_user_id);

    SELECT count(*) INTO n FROM anagrafiche.istanze_dati_precontrattuali
     WHERE istanza_utility_id = v_a.istanza_utility_id AND utility_id = v_a.utility_id;
    PERFORM set_config('pgtap.visti_a', n::text, true);

    SELECT count(*) INTO n FROM anagrafiche.istanze_dati_precontrattuali
     WHERE istanza_utility_id = v_b.istanza_utility_id AND utility_id = v_b.utility_id;
    PERFORM set_config('pgtap.visti_b', n::text, true);

    -- ⛔ La scrittura sulla coppia di un cliente di B: il WITH CHECK la rifiuta.
    BEGIN
        INSERT INTO anagrafiche.istanze_dati_precontrattuali (istanza_utility_id, utility_id)
        VALUES (v_b2.istanza_utility_id, v_b2.utility_id);
        PERFORM set_config('pgtap.scrittura', 'PASSATA', true);
    EXCEPTION WHEN insufficient_privilege THEN
        PERFORM set_config('pgtap.scrittura', 'RIFIUTATA', true);
    END;

    -- ⛔ Nessuna veste: non deve vedere niente.
    PERFORM set_config('app.ruolo_applicativo', '', true);
    SELECT count(*) INTO n FROM anagrafiche.istanze_dati_precontrattuali
     WHERE (istanza_utility_id, utility_id) IN (
               (v_a.istanza_utility_id, v_a.utility_id),
               (v_b.istanza_utility_id, v_b.utility_id));
    PERFORM set_config('pgtap.senza_veste', n::text, true);
END
$perimetro$;

ALTER TABLE anagrafiche.istanze_dati_precontrattuali NO FORCE ROW LEVEL SECURITY;
ALTER TABLE anagrafiche.billing_account              NO FORCE ROW LEVEL SECURITY;

SELECT is(current_setting('pgtap.visti_a', true), '1',
          '4. l''operatore A vede i dati precontrattuali del proprio cliente');

SELECT is(current_setting('pgtap.visti_b', true), '0',
          '5. e NON quelli del cliente dell''azienda B');

SELECT is(current_setting('pgtap.scrittura', true), 'RIFIUTATA',
          '6. A non scrive dati precontrattuali sulla coppia di un cliente di B (WITH CHECK)');

SELECT is(current_setting('pgtap.senza_veste', true), '0',
          '7. senza veste non vede niente: fail-closed');

-- ============================================================
-- 8. Il presidio del perimetro
-- ============================================================
SELECT is(
    (SELECT count(*)::int FROM dbops.vw_rls_perimetro_scoperto v
      WHERE v.schema_tabella = 'anagrafiche'
        AND v.nome_tabella = 'istanze_dati_precontrattuali'),
    0,
    '8. il presidio del perimetro RLS non elenca piu'' la tabella'
);

SELECT * FROM finish();
ROLLBACK;
