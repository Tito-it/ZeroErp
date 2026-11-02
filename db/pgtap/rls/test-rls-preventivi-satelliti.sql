-- ------------------------------------------------------------
-- SPDX-License-Identifier: AGPL-3.0-or-later
-- pgtap-runner: owner
-- pgtap-runner-motivo: ALTER TABLE … FORCE ROW LEVEL SECURITY, locale alla
--   transazione — e' il FORCE a rendere l'owner soggetto alle policy, perche'
--   `titodb` non e' superuser e non puo' fare SET ROLE. E la fixture costruisce
--   DUE aziende: un operatore dentro un perimetro non potrebbe crearle.
-- pgTAP test FUNZIONALE RLS — satelliti di vendite.preventivi
--   Slice 20260909-27..30, brief brief-db-perimetro-emittente-righe-documento.md
--
-- Elenco test (plan 8):
--  1) struttura: tutti e cinque i satelliti hanno la loro policy
--  2) struttura: e la RLS ACCESA — non basta che la policy esista
--  3) l'operatore A vede la riga del PROPRIO preventivo
--  4) ⛔ e NON vede quella di B
--  5) ⛔ idem sul riepilogo IVA: il filtro non e' solo sulle righe
--  6) ⛔ SCRITTURA: A non puo' appendere una riga al preventivo di B
--  7) ⛔ senza veste non vede NIENTE — fail-closed, non fail-open
--  8) le due viste che leggono i satelliti hanno `security_invoker`
--
-- ────────────────────────────────────────────────────────────────
-- ⭐ IL TEST 2 NON E' UN DOPPIONE DEL TEST 1, ed e' la ragione per cui esiste.
--   Una policy senza `ENABLE ROW LEVEL SECURITY` sta in `pg_policy` e non
--   filtra niente. Non e' un'ipotesi: il 2026-09-09 `acquisti.ddt`,
--   `acquisti.ordini` e `shop.ricevute` erano esattamente in quello stato, e
--   chiunque avesse verificato con `EXISTS (SELECT 1 FROM pg_policies …)`
--   avrebbe letto verde.
--
-- ⭐ IL TEST 6 E' L'ALTRA META' DELLA DIFESA. Una policy `FOR SELECT` lascia
--   SCRIVERE fuori perimetro: il `WITH CHECK` e' cio' che impedisce a un
--   operatore di appendere una riga al preventivo di un'altra azienda. E' la
--   parte che si dimentica, perche' il sintomo non si vede leggendo.
--
-- ⛔ LA FIXTURE SI COSTRUISCE, non si cerca. Il test dei satelliti fattura
--   (test-rls-fatture-satelliti-functional.sql) usa una fattura ESISTENTE e
--   fa soft-skip se non ne trova: su un database ricostruito dai changelog
--   quel file passa senza provare niente. Qui i due mondi li fabbrica
--   `dbops.fn_pgtap_crea_emittente_operatore()` (changeSet 20260909-26), quindi
--   il test misura la stessa cosa su dbdev e in CI.
--   ⚠️ Gli ARTICOLI invece si cercano, e va bene: stanno in `80_data`, cioe'
--   sono catalogo e ci sono ovunque (cinque anche sul database scratch).
-- ------------------------------------------------------------

BEGIN;

SET CONSTRAINTS ALL IMMEDIATE;

SELECT plan(8);

-- ============================================================
-- I due mondi
-- ============================================================
-- ⚠️ `fn_pgtap_crea_emittente_operatore` apre e richiude da sola la finestra
--   dei guard differiti: qui non serve toccarla.
CREATE TEMP TABLE _mondi AS
SELECT 'A' AS lato, * FROM dbops.fn_pgtap_crea_emittente_operatore()
UNION ALL
SELECT 'B' AS lato, * FROM dbops.fn_pgtap_crea_emittente_operatore();

-- Un cliente fatturabile per lato: e' cio' che un preventivo pretende.
-- ⛔ Non basta un soggetto: `trgfn_preventivi_guard_utility_istanza_coerenza`
--   vuole che per la coppia (istanza, utility) esista un billing account.
--   La catena e' una saga con due guard differiti, e la costruisce
--   `dbops.fn_pgtap_crea_cliente_ba` (changeSet 20260909-31).
CREATE TEMP TABLE _clienti AS
SELECT m.lato, m.emittente_fiscale_id, c.*
  FROM _mondi m
  CROSS JOIN LATERAL dbops.fn_pgtap_crea_cliente_ba(
        'RLS preventivi ' || m.lato, NULL, m.soggetto_ruolo_id) c;
-- ⚠️ rev 2026-10-08 (brief-db-istanza-nasce-col-ba, R-2): il preventivo ha
--   sempre il BA della sua coppia, e il guard dell'emittente pretende che il
--   BA sia dell'emittente del preventivo: il BA si lega ESPLICITAMENTE
--   all'emittente del suo lato (terzo parametro), non a chi agisce.

CREATE TEMP TABLE _preventivi AS
WITH prev AS (
    INSERT INTO vendite.preventivi
        (numero, billing_account_id, istanza_utility_id, utility_id, stato_doc_preventivo_id, emittente_fiscale_id)
    SELECT 'PGTAPRLS-' || c.lato,
           c.billing_account_id,
           c.istanza_utility_id,
           c.utility_id,
           (SELECT st.id FROM config.stati_doc_preventivi st ORDER BY st.id LIMIT 1),
           c.emittente_fiscale_id
      FROM _clienti c
    RETURNING id, emittente_fiscale_id
)
SELECT c.lato, p.id AS preventivo_id, p.emittente_fiscale_id
  FROM prev p JOIN _clienti c ON c.emittente_fiscale_id = p.emittente_fiscale_id;

-- Una riga e un riepilogo IVA per lato.
INSERT INTO vendite.preventivi_righe (preventivo_id, articolo_id, prezzo_unitario, qta_operativa)
SELECT p.preventivo_id,
       (SELECT a.id FROM catalogo.articoli a ORDER BY a.id LIMIT 1),
       100.00, 1
  FROM _preventivi p;

-- ⚠️ Condizionale: il riepilogo puo' nascere da solo insieme alla riga —
--   `uq_preventivi_r_iva_key` e' UNIQUE su (preventivo, natura, esigibilita,
--   split, iva) coi COALESCE, quindi un secondo inserimento a chiavi nulle
--   collide. Si aggiunge solo se manca, cosi' il test regge sia che il
--   riepilogo sia derivato sia che non lo sia.
INSERT INTO vendite.preventivi_riepiloghi_iva (preventivo_id)
SELECT p.preventivo_id FROM _preventivi p
 WHERE NOT EXISTS (SELECT 1 FROM vendite.preventivi_riepiloghi_iva q
                    WHERE q.preventivo_id = p.preventivo_id);

-- ============================================================
-- 1..2. La struttura: policy E armamento
-- ============================================================
SELECT is(
    (SELECT count(*)::int FROM pg_policies
      WHERE schemaname = 'vendite'
        AND tablename IN ('preventivi_righe', 'preventivi_indirizzi',
                          'preventivi_riepiloghi_iva', 'note_preventivo',
                          'preventivi_righe_componenti')),
    5,
    '1. i cinque satelliti di preventivi hanno la loro policy'
);

-- ⛔ Non e' il doppione del test 1: vedi l'intestazione.
SELECT is(
    (SELECT count(*)::int FROM pg_class c
       JOIN pg_namespace n ON n.oid = c.relnamespace AND n.nspname = 'vendite'
      WHERE c.relname IN ('preventivi_righe', 'preventivi_indirizzi',
                          'preventivi_riepiloghi_iva', 'note_preventivo',
                          'preventivi_righe_componenti')
        AND c.relrowsecurity),
    5,
    '2. e su tutti e cinque la RLS e'' ACCESA, non solo dichiarata'
);

-- ============================================================
-- Il perimetro, esercitato
-- ============================================================
-- FORCE locale alla transazione: senza, l'owner sarebbe esente e il test
-- misurerebbe zero. Il ROLLBACK finale lo annulla.
ALTER TABLE vendite.preventivi                FORCE ROW LEVEL SECURITY;
ALTER TABLE vendite.preventivi_righe          FORCE ROW LEVEL SECURITY;
ALTER TABLE vendite.preventivi_riepiloghi_iva FORCE ROW LEVEL SECURITY;

DO $perimetro$
DECLARE
    v_a record;
    v_b record;
    v_visti_a integer;
    v_visti_b integer;
    v_riep_b  integer;
BEGIN
    SELECT p.*, m.auth_user_id INTO v_a
      FROM _preventivi p JOIN _mondi m ON m.emittente_fiscale_id = p.emittente_fiscale_id
     WHERE p.lato = 'A';
    SELECT p.* INTO v_b FROM _preventivi p WHERE p.lato = 'B';

    -- La veste dell'operatore A, come la darebbe il middleware.
    PERFORM script.fn_pgtap_set_contesto_operatore(v_a.auth_user_id);

    SELECT count(*) INTO v_visti_a
      FROM vendite.preventivi_righe r WHERE r.preventivo_id = v_a.preventivo_id;
    SELECT count(*) INTO v_visti_b
      FROM vendite.preventivi_righe r WHERE r.preventivo_id = v_b.preventivo_id;
    SELECT count(*) INTO v_riep_b
      FROM vendite.preventivi_riepiloghi_iva q WHERE q.preventivo_id = v_b.preventivo_id;

    PERFORM set_config('pgtap.visti_a', v_visti_a::text, true);
    PERFORM set_config('pgtap.visti_b', v_visti_b::text, true);
    PERFORM set_config('pgtap.riep_b',  v_riep_b::text,  true);

    -- ⛔ La scrittura: appendere una riga al preventivo dell'altro deve essere
    --   rifiutata dal WITH CHECK, non solo invisibile in lettura.
    BEGIN
        INSERT INTO vendite.preventivi_righe
            (preventivo_id, articolo_id, prezzo_unitario, qta_operativa)
        VALUES (v_b.preventivo_id,
                (SELECT a.id FROM catalogo.articoli a ORDER BY a.id LIMIT 1),
                1.00, 1);
        PERFORM set_config('pgtap.scrittura', 'PASSATA', true);
    EXCEPTION WHEN insufficient_privilege OR check_violation THEN
        PERFORM set_config('pgtap.scrittura', 'RIFIUTATA', true);
    END;

    -- ⛔ Nessuna veste: la policy e' permissiva e condizionata alla veste,
    --   quindi non deve vedere NIENTE. Il verso sbagliato — vedere tutto —
    --   sarebbe il difetto peggiore e non farebbe rumore.
    PERFORM set_config('app.ruolo_applicativo', '', true);
    SELECT count(*) INTO v_visti_a
      FROM vendite.preventivi_righe r
     WHERE r.preventivo_id IN (v_a.preventivo_id, v_b.preventivo_id);
    PERFORM set_config('pgtap.senza_veste', v_visti_a::text, true);
END
$perimetro$;

ALTER TABLE vendite.preventivi_riepiloghi_iva NO FORCE ROW LEVEL SECURITY;
ALTER TABLE vendite.preventivi_righe          NO FORCE ROW LEVEL SECURITY;
ALTER TABLE vendite.preventivi                NO FORCE ROW LEVEL SECURITY;

SELECT is(current_setting('pgtap.visti_a', true), '1',
          '3. l''operatore A vede la riga del proprio preventivo');

SELECT is(current_setting('pgtap.visti_b', true), '0',
          '4. e NON vede la riga del preventivo di un''altra azienda');

SELECT is(current_setting('pgtap.riep_b', true), '0',
          '5. lo stesso vale per il riepilogo IVA: il filtro non e'' solo sulle righe');

SELECT is(current_setting('pgtap.scrittura', true), 'RIFIUTATA',
          '6. e non puo'' nemmeno APPENDERE una riga al preventivo altrui (WITH CHECK)');

SELECT is(current_setting('pgtap.senza_veste', true), '0',
          '7. senza veste applicativa non vede niente: fail-closed');

-- ============================================================
-- 8. Le viste che leggono i satelliti
-- ============================================================
-- ⚠️ Senza `security_invoker` una vista gira come il proprio owner, che la RLS
--   non la vede: risponderebbe di piu', senza errori e senza pagine rotte.
--   Il presidio generale sta in test-rls-viste-security-invoker.sql; qui si
--   nominano le due che questa slice ha dovuto sistemare.
SELECT is(
    (SELECT count(*)::int FROM pg_class c
       JOIN pg_namespace n ON n.oid = c.relnamespace AND n.nspname = 'vendite'
      WHERE c.relkind = 'v'
        AND c.relname IN ('vw_preventivi_righe_dettaglio',
                          'vw_preventivi_riepilogo_iva_dettaglio')
        AND coalesce(c.reloptions::text, '') LIKE '%security_invoker%'),
    2,
    '8. le due viste sui satelliti hanno security_invoker'
);

SELECT * FROM finish();

ROLLBACK;
