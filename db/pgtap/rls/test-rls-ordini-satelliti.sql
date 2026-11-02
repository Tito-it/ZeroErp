-- ------------------------------------------------------------
-- SPDX-License-Identifier: AGPL-3.0-or-later
-- pgtap-runner: owner
-- pgtap-runner-motivo: ALTER TABLE … FORCE ROW LEVEL SECURITY, locale alla
--   transazione — e' il FORCE a rendere l'owner soggetto alle policy, perche'
--   `titodb` non e' superuser e non puo' fare SET ROLE. E la fixture costruisce
--   DUE aziende: un operatore dentro un perimetro non potrebbe crearle.
-- pgTAP test FUNZIONALE RLS — satelliti di vendite.ordini
-- rev 2026-10-25 (brief-db-pgtap-reso-costruito, giro D-4): l'ordine in bozza con la riga di
--   ciascun mondo da dbops.fn_pgtap_crea_ordine_con_righe (DRAFT, 1 x 100), un'azienda alla
--   volta sotto il contesto del suo operatore; poi il contesto si richiude. Resta a mano la
--   riga 99 «intrusione», che e' il caso del test 5.
--   Slice 20260909-33..35, brief brief-db-perimetro-emittente-righe-documento.md
--
-- Elenco test (plan 9):
--  1) struttura: i cinque satelliti hanno tutte e TRE le vesti della testata
--  2) struttura: e la RLS ACCESA — non basta che la policy esista
--  3) l'operatore A vede la riga del PROPRIO ordine
--  4) ⛔ e NON vede quella di B
--  5) ⛔ SCRITTURA: A non puo' appendere una riga all'ordine di B
--  6) ⛔ senza veste non vede NIENTE — fail-closed
--  7) ⭐ il satellite non e' MAI piu' permissivo della testata: quello che
--        l'operatore vede sulle righe e' un sottoinsieme di cio' che vede
--        sulle testate
--  8) ⭐ la veste SHOP porta DUE condizioni: un ordine posseduto ma di canale
--        ADMIN non si vede
--  9) ⚠️ l'adattatore a DUE livelli (riga -> ordine) risale davvero
--
-- ────────────────────────────────────────────────────────────────
-- ⭐ PERCHE' ORDINI HA UN TEST PIU' LUNGO DI PREVENTIVI.
--   La testata ha TRE policy invece di una, e i satelliti le rispecchiano
--   tutte. Il rischio nuovo non e' «vedo troppo poco»: e' che un satellite
--   risulti PIU' PERMISSIVO della propria testata — per esempio perche' la
--   veste SHOP sul satellite chiede la sola proprieta' e si dimentica il
--   canale. I test 7 e 8 sono li' per quello, e sono la ragione per cui questa
--   famiglia e' stata fatta subito dopo la piu' semplice.
--
-- ⛔ LA FIXTURE SI COSTRUISCE, non si cerca: due aziende con
--   `dbops.fn_pgtap_crea_emittente_operatore()` e due clienti fatturabili con
--   `dbops.fn_pgtap_crea_cliente_ba()`. Cosi' il file misura la stessa cosa su
--   dbdev e su un database ricostruito dai changelog.
-- ------------------------------------------------------------

BEGIN;

SET CONSTRAINTS ALL IMMEDIATE;

SELECT plan(9);

-- ============================================================
-- I due mondi, e un ordine per ciascuno
-- ============================================================
CREATE TEMP TABLE _mondi AS
SELECT 'A' AS lato, * FROM dbops.fn_pgtap_crea_emittente_operatore()
UNION ALL
SELECT 'B' AS lato, * FROM dbops.fn_pgtap_crea_emittente_operatore();

CREATE TEMP TABLE _clienti AS
SELECT m.lato, m.emittente_fiscale_id, c.*
  FROM _mondi m
  -- rev 2026-10-09 (brief-db-esecutivi-ba-coppia): il BA legato all'emittente del
  --   mondo. Il documento porta ora il BA, e il guard emittente <-> BA lo guarda.
  CROSS JOIN LATERAL dbops.fn_pgtap_crea_cliente_ba('RLS ordini ' || m.lato, NULL, m.soggetto_ruolo_id) c;

-- ⚠️ `canale_origine` resta il default ADMIN: serve al test 8, che verifica che
--   la veste SHOP non basti la proprieta'.
-- ⛔ rev 2026-10-13 (brief-db-articoli-ammessi-per-documento, Lotto 3a): l'articolo
--   si COSTRUISCE. Ordine e bolla ammettono solo merce non solo-componente, e
--   su un database ricostruito il catalogo ha solo i cinque ONERE_* (servizi):
--   cercarlo dava NULL e la riga moriva su E_UOM_MISSING.
CREATE TEMP TABLE _art AS
SELECT dbops.fn_pgtap_crea_articolo('PGTAP-RLS-ORD-SAT', false) AS id;

-- L'ordine di ciascun mondo, in bozza con una riga: lo costruisce l'operatore
-- della sua azienda, un lato alla volta (il builder verifica che il BA sia
-- dell'azienda di chi agisce).
CREATE TEMP TABLE _ordini (lato text, ordine_id bigint, riga_id bigint,
                           emittente_fiscale_id bigint, soggetto_ruolo_id bigint);

DO $ctx_a$ BEGIN
    PERFORM script.fn_pgtap_set_contesto_operatore((SELECT auth_user_id FROM _mondi WHERE lato = 'A'));
END $ctx_a$;
INSERT INTO _ordini
SELECT 'A', b.ordine_id, b.ordine_riga_id, b.emittente_fiscale_id, b.cliente_soggetto_ruolo_id
  FROM dbops.fn_pgtap_crea_ordine_con_righe('RLS ordini A', 'DRAFT',
           p_billing_account_id   => (SELECT billing_account_id FROM _clienti WHERE lato = 'A'),
           p_fatturazione_trigger => 'CONFERMATO',
           p_articolo_id => (SELECT id FROM _art), p_quantita => 1, p_prezzo => 100) b;

DO $ctx_b$ BEGIN
    PERFORM script.fn_pgtap_set_contesto_operatore((SELECT auth_user_id FROM _mondi WHERE lato = 'B'));
END $ctx_b$;
INSERT INTO _ordini
SELECT 'B', b.ordine_id, b.ordine_riga_id, b.emittente_fiscale_id, b.cliente_soggetto_ruolo_id
  FROM dbops.fn_pgtap_crea_ordine_con_righe('RLS ordini B', 'DRAFT',
           p_billing_account_id   => (SELECT billing_account_id FROM _clienti WHERE lato = 'B'),
           p_fatturazione_trigger => 'CONFERMATO',
           p_articolo_id => (SELECT id FROM _art), p_quantita => 1, p_prezzo => 100) b;

-- Il contesto dell'operatore si richiude: lo riapre il blocco $perimetro$.
DO $ctx_chiuso$ BEGIN
    PERFORM set_config('app.ruolo_applicativo', '', false);
    PERFORM set_config('app.current_user_id', '', false);
END $ctx_chiuso$;

CREATE TEMP TABLE _righe AS SELECT o.lato, o.riga_id, o.ordine_id FROM _ordini o;

-- ⛔ NESSUNA riga di `ordini_righe_componenti` nella fixture, ed e' una scelta.
--   Un componente pretende `componente_id` verso `catalogo.articoli_componenti`,
--   cioe' una distinta base: 25 righe su dbdev, ZERO su un database ricostruito
--   dai changelog. Costruirne una e' una catena che non appartiene a questa
--   slice, e usarne una esistente renderebbe il file verde qui e saltato la'.
--   ⭐ La risalita a due livelli si prova meglio in un altro modo: il test 9
--   interroga direttamente l'adattatore `_via_ordine_riga`, che e' la cosa da
--   verificare. Non serve una riga per chiedere a una funzione se dice il vero.

-- ============================================================
-- 1..2. La struttura: tre vesti per tabella, e l'armamento
-- ============================================================
SELECT is(
    (SELECT count(*)::int FROM pg_policies
      WHERE schemaname = 'vendite'
        AND tablename IN ('ordini_righe', 'ordini_indirizzi', 'note_ordini',
                          'ordini_righe_componenti', 'ordini_righe_fulfillment')),
    15,
    '1. i cinque satelliti portano tutte e tre le vesti della testata'
);

-- ⛔ Non e' il doppione del test 1: una policy senza ENABLE sta in pg_policy e
--   non filtra niente. Succede: tre tabelle del database erano cosi'.
SELECT is(
    (SELECT count(*)::int FROM pg_class c
       JOIN pg_namespace n ON n.oid = c.relnamespace AND n.nspname = 'vendite'
      WHERE c.relname IN ('ordini_righe', 'ordini_indirizzi', 'note_ordini',
                          'ordini_righe_componenti', 'ordini_righe_fulfillment')
        AND c.relrowsecurity),
    5,
    '2. e su tutti e cinque la RLS e'' ACCESA, non solo dichiarata'
);

-- ============================================================
-- Il perimetro, esercitato
-- ============================================================
ALTER TABLE vendite.ordini                   FORCE ROW LEVEL SECURITY;
ALTER TABLE vendite.ordini_righe             FORCE ROW LEVEL SECURITY;
ALTER TABLE vendite.ordini_righe_componenti  FORCE ROW LEVEL SECURITY;

DO $perimetro$
DECLARE
    v_a record;
    v_b record;
    v_n integer;
BEGIN
    SELECT o.*, m.auth_user_id, m.identita_id INTO v_a
      FROM _ordini o JOIN _mondi m ON m.emittente_fiscale_id = o.emittente_fiscale_id
     WHERE o.lato = 'A';
    SELECT o.* INTO v_b FROM _ordini o WHERE o.lato = 'B';

    PERFORM script.fn_pgtap_set_contesto_operatore(v_a.auth_user_id);

    SELECT count(*) INTO v_n FROM vendite.ordini_righe r WHERE r.ordine_id = v_a.ordine_id;
    PERFORM set_config('pgtap.righe_a', v_n::text, true);
    SELECT count(*) INTO v_n FROM vendite.ordini_righe r WHERE r.ordine_id = v_b.ordine_id;
    PERFORM set_config('pgtap.righe_b', v_n::text, true);

    -- ⭐ L'INVARIANTE: il satellite non puo' essere piu' permissivo della
    --   testata. Si misura sulle righe che l'operatore vede il cui ordine,
    --   invece, non vede: devono essere ZERO.
    SELECT count(*) INTO v_n
      FROM vendite.ordini_righe r
     WHERE NOT EXISTS (SELECT 1 FROM vendite.ordini o WHERE o.id = r.ordine_id);
    PERFORM set_config('pgtap.orfane', v_n::text, true);

    -- ⚠️ La risalita a DUE livelli, chiesta all'adattatore invece che alle
    --   righe: e' lui che i componenti useranno, e la sua risposta non dipende
    --   da quali distinte base la macchina contiene.
    PERFORM set_config('pgtap.riga2',
        script.fn_scope_ef_whitelist_via_ordine_riga(
            v_a.auth_user_id, (SELECT riga_id FROM _righe WHERE lato = 'A'))::text
        || '/' ||
        script.fn_scope_ef_whitelist_via_ordine_riga(
            v_a.auth_user_id, (SELECT riga_id FROM _righe WHERE lato = 'B'))::text,
        true);

    -- ⛔ La scrittura sull'ordine altrui.
    BEGIN
        INSERT INTO vendite.ordini_righe
            (ordine_id, riga_nr, articolo_id, descrizione, quantita, qta_operativa, prezzo_unitario)
        VALUES (v_b.ordine_id, 99,
                (SELECT id FROM _art),
                'intrusione', 1, 1, 1.00);
        PERFORM set_config('pgtap.scrittura', 'PASSATA', true);
    EXCEPTION WHEN insufficient_privilege OR check_violation THEN
        PERFORM set_config('pgtap.scrittura', 'RIFIUTATA', true);
    END;

    -- ⭐ La veste SHOP: proprietario dell'ordine, ma canale ADMIN.
    --   La testata pretende ANCHE `canale_origine = 'SHOP'`, quindi il
    --   satellite non deve farsi bastare la proprieta'.
    PERFORM set_config('app.ruolo_applicativo', 'SHOP_CUSTOMER', true);
    PERFORM set_config('app.current_identita_id', v_a.identita_id::text, true);
    PERFORM set_config('app.current_user_id', '', true);
    SELECT count(*) INTO v_n FROM vendite.ordini_righe r WHERE r.ordine_id = v_a.ordine_id;
    PERFORM set_config('pgtap.shop_admin', v_n::text, true);

    -- ⛔ Nessuna veste: fail-closed.
    PERFORM set_config('app.ruolo_applicativo', '', true);
    PERFORM set_config('app.current_identita_id', '', true);
    SELECT count(*) INTO v_n
      FROM vendite.ordini_righe r WHERE r.ordine_id IN (v_a.ordine_id, v_b.ordine_id);
    PERFORM set_config('pgtap.senza_veste', v_n::text, true);
END
$perimetro$;

ALTER TABLE vendite.ordini_righe_componenti  NO FORCE ROW LEVEL SECURITY;
ALTER TABLE vendite.ordini_righe             NO FORCE ROW LEVEL SECURITY;
ALTER TABLE vendite.ordini                   NO FORCE ROW LEVEL SECURITY;

SELECT is(current_setting('pgtap.righe_a', true), '1',
          '3. l''operatore A vede la riga del proprio ordine');

SELECT is(current_setting('pgtap.righe_b', true), '0',
          '4. e NON vede la riga dell''ordine di un''altra azienda');

SELECT is(current_setting('pgtap.scrittura', true), 'RIFIUTATA',
          '5. e non puo'' appendere una riga all''ordine altrui (WITH CHECK)');

SELECT is(current_setting('pgtap.senza_veste', true), '0',
          '6. senza veste applicativa non vede niente: fail-closed');

SELECT is(current_setting('pgtap.orfane', true), '0',
          '7. nessuna riga visibile il cui ORDINE non lo e'': il satellite non e'' piu'' permissivo della testata');

SELECT is(current_setting('pgtap.shop_admin', true), '0',
          '8. veste SHOP su un ordine POSSEDUTO ma di canale ADMIN: non si vede');

SELECT is(current_setting('pgtap.riga2', true), 'true/false',
          '9. l''adattatore a due livelli risale davvero: vero sulla riga di A, falso su quella di B');

SELECT * FROM finish();

ROLLBACK;
