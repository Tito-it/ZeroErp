-- ------------------------------------------------------------
-- SPDX-License-Identifier: GPL-3.0-or-later
-- pgtap-runner: owner
-- pgtap-runner-motivo: ALTER TABLE … FORCE ROW LEVEL SECURITY, locale alla
--   transazione — e' il FORCE a rendere l'owner soggetto alle policy, perche'
--   `titodb` non e' superuser e non puo' fare SET ROLE. E la fixture costruisce
--   DUE aziende: un operatore dentro un perimetro non potrebbe crearle.
-- pgTAP test FUNZIONALE RLS — i CINQUE satelliti di vendite.fatturazione_lotti
--   Slice 20260910-14..17, brief brief-db-perimetro-emittente-righe-documento.md §11.9
--   Seconda famiglia consegnata dal presidio dbops.vw_rls_perimetro_scoperto.
--
-- Elenco test (plan 12):
--   1) struttura: tutti e cinque hanno la loro policy
--   2) struttura: e la RLS e' ACCESA su tutti e cinque
--   3) ⛔ ogni policy passa dal modo 'lotto' del risolutore (era `_via_lotto`,
--      rev 2026-10-18) e dalla chiave `lotto_id`
--   4) ⭐ LA DECISIONE: il legame lotto-fattura risale dal LOTTO, non dalla
--      fattura — la policy non nomina `fattura_id`
--   5) l'operatore A vede gli esiti del PROPRIO lotto
--   6) ⛔ e non quelli di B — la riparazione
--   7) ⛔ ne' il legame lotto-fattura di B
--   8) ⛔ ne' il diario di B
--   9) ⛔ SCRITTURA: A non puo' appendere una riga di diario al lotto di B
--  10) ⛔ SCRITTURA: ne' un legame lotto-fattura al lotto di B
--  11) ⛔ senza veste applicativa: fail-closed su tutti e cinque
--  12) ⭐ l'adattatore dice il vero: il proprio lotto si', quello di B no
--
-- ────────────────────────────────────────────────────────────────
-- ⛔ IL DIFETTO CHE QUESTO FILE CHIUDE.
--   `vendite.fatturazione_lotti` e' protetta; i suoi cinque satelliti non
--   avevano nessuna policy e `zeroerp_app` ha su tutti SELECT, INSERT, UPDATE e
--   DELETE. Il perimetro si fermava alla testata — e il **diario del lotto**,
--   che nomina documenti e commesse, era leggibile da chiunque.
--   ⚠️ Su `fatturazione_lotti_gruppi` il perimetro lo teneva il backend con il
--   JOIN sulla testata, conteggio compreso. Quella difesa applicativa **resta**
--   e si somma: la RLS non la sostituisce.
--
-- ⛔ IL TEST 3 PRENDE UN REFUSO CHE NON FA RUMORE, e qui e' peggio del solito.
--   `vendite.fatturazione_lotti` nomina il proprio emittente per
--   **soggetto-ruolo** (`emittente_soggetto_ruolo_id`), non per emittente
--   fiscale. Se l'adattatore delegasse alla canonica `fn_scope_ef_whitelist`
--   invece che a `_via_sr`, confronterebbe un id di soggetto-ruolo con una
--   whitelist di id di emittente fiscale: due numerazioni diverse, quindi
--   quasi sempre **zero righe**. ⚠️ Un fail-closed per la ragione sbagliata
--   somiglia moltissimo a una difesa che funziona — e a smascherarlo e' il
--   test 5, che pretende che A veda il PROPRIO. Il verso negativo da solo
--   sarebbe passato.
--
-- ⭐ IL TEST 4 E' LA DECISIONE MESSA PER ISCRITTO.
--   `fatturazione_lotti_fatture` e' l'unica dei cinque con DUE genitori
--   protetti e tutti e due `NOT NULL`. Comanda il **lotto** (decisione di Tid,
--   2026-09-10): quella riga racconta com'e' andato il giro di emissione, non
--   fa parte del documento fattura. ⛔ Agganciarla alla fattura avrebbe portato
--   dentro anche la veste `CLIENTE_PORTALE`, cioe' una modifica funzionale
--   mascherata da cantiere di sicurezza. Il test lo pinna sulla definizione
--   della policy, cosi' il giorno in cui qualcuno la cambia deve cambiare anche
--   questa riga — e leggere perche'.
--
-- ⚠️ COSA QUESTO FILE NON PROVA. Che i cinque siano TUTTI i satelliti: quello
--   lo dice il criterio, in `db/pgtap/rls/test-rls-perimetro-scoperto.sql`.
-- ------------------------------------------------------------

BEGIN;

SET CONSTRAINTS ALL IMMEDIATE;

SELECT plan(12);

-- ============================================================
-- I due mondi, un lotto per ciascuno, i cinque satelliti attorno
-- ============================================================
CREATE TEMP TABLE _mondi AS
SELECT 'A' AS lato, * FROM dbops.fn_pgtap_crea_emittente_operatore()
UNION ALL
SELECT 'B' AS lato, * FROM dbops.fn_pgtap_crea_emittente_operatore();

CREATE TEMP TABLE _clienti AS
SELECT m.lato, m.soggetto_ruolo_id AS emittente_sr_id, m.auth_user_id, c.*
  FROM _mondi m
  CROSS JOIN LATERAL dbops.fn_pgtap_crea_cliente_ba(
      'RLS lotti ' || m.lato, NULL, m.soggetto_ruolo_id) c;

-- ⚠️ `vendite.fatture.registro_id` e' NOT NULL: il registro non nasce da solo.
CREATE TEMP TABLE _registri AS
WITH r AS (
    INSERT INTO vendite.registri_fatturazione
        (codice, descrizione, emittente_soggetto_ruolo_id, famiglia_documento)
    SELECT 'PGTAPL' || c.billing_account_id,
           'Registro pgTAP RLS lotti ' || c.lato,
           c.emittente_sr_id, 'FATTURA'
      FROM _clienti c
    RETURNING id, emittente_soggetto_ruolo_id
)
SELECT c.lato, r.id AS registro_id
  FROM r JOIN _clienti c ON c.emittente_sr_id = r.emittente_soggetto_ruolo_id;

-- ⭐ La fattura serve SOLO al legame lotto-fattura, che e' il caso della
--   decisione: senza, il test 4 sarebbe struttura e basta.
CREATE TEMP TABLE _fatture AS
WITH f AS (
    INSERT INTO vendite.fatture
        (registro_id, emittente_soggetto_ruolo_id, billing_account_id)
    SELECT r.registro_id, c.emittente_sr_id, c.billing_account_id
      FROM _clienti c JOIN _registri r ON r.lato = c.lato
    RETURNING id, emittente_soggetto_ruolo_id
)
SELECT c.lato, f.id AS fattura_id
  FROM f JOIN _clienti c ON c.emittente_sr_id = f.emittente_soggetto_ruolo_id;

CREATE TEMP TABLE _lotti AS
WITH l AS (
    INSERT INTO vendite.fatturazione_lotti
        (codice, competenza_mese, tipo_doc_fiscale_id, emittente_soggetto_ruolo_id)
    SELECT 'PGTAP-LOTTO-' || c.lato || '-' || c.billing_account_id,
           date_trunc('month', script.fn_data_operativa())::date,
           (SELECT t.id FROM config.tipi_doc_fiscale t
             WHERE t.attivo ORDER BY t.id LIMIT 1),
           c.emittente_sr_id
      FROM _clienti c
    RETURNING id, emittente_soggetto_ruolo_id
)
SELECT c.lato, l.id AS lotto_id, c.auth_user_id
  FROM l JOIN _clienti c ON c.emittente_sr_id = l.emittente_soggetto_ruolo_id;

-- I cinque satelliti, uno per lato: tutti portano la stessa chiave, quindi la
-- fixture li costruisce tutti — non c'e' nessuno che costi una catena finta.
INSERT INTO vendite.fatturazione_lotti_esiti (lotto_id, gruppo_key, stato_esecuzione)
SELECT l.lotto_id, 'PGTAP-' || l.lato, 'COMPLETED' FROM _lotti l;

INSERT INTO vendite.fatturazione_lotti_gruppi (lotto_id, gruppo_key)
SELECT l.lotto_id, 'PGTAP-' || l.lato FROM _lotti l;

INSERT INTO vendite.fatturazione_lotti_log (lotto_id, messaggio)
SELECT l.lotto_id, 'Diario pgTAP lotto ' || l.lato FROM _lotti l;

INSERT INTO vendite.fatturazione_lotti_task_runs (lotto_id, task_code)
SELECT l.lotto_id, 'PGTAP_TASK' FROM _lotti l;

INSERT INTO vendite.fatturazione_lotti_fatture (lotto_id, fattura_id)
SELECT l.lotto_id, f.fattura_id
  FROM _lotti l JOIN _fatture f ON f.lato = l.lato;

-- ============================================================
-- 1..4. La struttura, e la decisione
-- ============================================================
SELECT is(
    (SELECT count(DISTINCT p.tablename)::int FROM pg_policies p
      WHERE p.schemaname = 'vendite'
        AND p.tablename IN ('fatturazione_lotti_esiti','fatturazione_lotti_fatture',
                            'fatturazione_lotti_gruppi','fatturazione_lotti_log',
                            'fatturazione_lotti_task_runs')),
    5,
    '1. tutti e cinque i satelliti di vendite.fatturazione_lotti hanno la loro policy'
);

-- ⛔ Si asserisce `relrowsecurity`, non l'esistenza della policy: una policy
--   con la RLS spenta non e' una difesa.
SELECT is(
    (SELECT count(*)::int FROM pg_class c
       JOIN pg_namespace n ON n.oid = c.relnamespace AND n.nspname = 'vendite'
      WHERE c.relname IN ('fatturazione_lotti_esiti','fatturazione_lotti_fatture',
                          'fatturazione_lotti_gruppi','fatturazione_lotti_log',
                          'fatturazione_lotti_task_runs')
        AND c.relrowsecurity),
    5,
    '2. e la ROW LEVEL SECURITY e'' accesa su tutti e cinque'
);

SELECT is_empty(
    $$SELECT p.tablename
        FROM pg_policies p
       WHERE p.schemaname = 'vendite'
         AND p.tablename IN ('fatturazione_lotti_esiti','fatturazione_lotti_fatture',
                             'fatturazione_lotti_gruppi','fatturazione_lotti_log',
                             'fatturazione_lotti_task_runs')
         AND (   position('fn_resolve_emittente_fiscale_id(''lotto''::text' IN p.qual)       = 0
              OR position('fn_resolve_emittente_fiscale_id(''lotto''::text' IN p.with_check) = 0
              OR position('lotto_id' IN p.qual)                              = 0)$$,
    '3. ogni policy passa dal modo lotto del risolutore e dalla chiave lotto_id'
);

-- ⭐ La decisione del 2026-09-10, pinnata dove vive: nella policy.
SELECT is_empty(
    $$SELECT p.tablename
        FROM pg_policies p
       WHERE p.schemaname = 'vendite'
         AND p.tablename  = 'fatturazione_lotti_fatture'
         AND (   position('fattura_id' IN p.qual)       > 0
              OR position('fattura_id' IN p.with_check) > 0)$$,
    '4. il legame lotto-fattura risale dal LOTTO: la sua policy non nomina fattura_id'
);

-- ============================================================
-- Il perimetro, esercitato da dentro
-- ============================================================
ALTER TABLE vendite.fatturazione_lotti              FORCE ROW LEVEL SECURITY;
ALTER TABLE vendite.fatturazione_lotti_esiti        FORCE ROW LEVEL SECURITY;
ALTER TABLE vendite.fatturazione_lotti_fatture      FORCE ROW LEVEL SECURITY;
ALTER TABLE vendite.fatturazione_lotti_gruppi       FORCE ROW LEVEL SECURITY;
ALTER TABLE vendite.fatturazione_lotti_log          FORCE ROW LEVEL SECURITY;
ALTER TABLE vendite.fatturazione_lotti_task_runs    FORCE ROW LEVEL SECURITY;

DO $perimetro$
DECLARE
    v_a record;
    v_b record;
    v_n integer;
BEGIN
    SELECT l.*, f.fattura_id INTO v_a
      FROM _lotti l JOIN _fatture f ON f.lato = l.lato WHERE l.lato = 'A';
    SELECT l.*, f.fattura_id INTO v_b
      FROM _lotti l JOIN _fatture f ON f.lato = l.lato WHERE l.lato = 'B';

    PERFORM script.fn_pgtap_set_contesto_operatore(v_a.auth_user_id);

    -- ⭐ Il PROPRIO. E' il verso che smaschera l'adattatore sbagliato: con la
    --   canonica al posto di `_via_sr` qui si leggerebbe 0, e i soli test
    --   negativi resterebbero verdi su una policy rotta.
    SELECT count(*) INTO v_n FROM vendite.fatturazione_lotti_esiti e
     WHERE e.lotto_id = v_a.lotto_id;
    PERFORM set_config('pgtap.esiti_a', v_n::text, true);

    SELECT count(*) INTO v_n FROM vendite.fatturazione_lotti_esiti e
     WHERE e.lotto_id = v_b.lotto_id;
    PERFORM set_config('pgtap.esiti_b', v_n::text, true);

    SELECT count(*) INTO v_n FROM vendite.fatturazione_lotti_fatture lf
     WHERE lf.lotto_id = v_b.lotto_id;
    PERFORM set_config('pgtap.legame_b', v_n::text, true);

    SELECT count(*) INTO v_n FROM vendite.fatturazione_lotti_log g
     WHERE g.lotto_id = v_b.lotto_id;
    PERFORM set_config('pgtap.diario_b', v_n::text, true);

    -- ⛔ SCRITTURA sul diario del lotto altrui.
    BEGIN
        INSERT INTO vendite.fatturazione_lotti_log (lotto_id, messaggio)
        VALUES (v_b.lotto_id, 'intrusione');
        PERFORM set_config('pgtap.scrittura_log', 'PASSATA', true);
    EXCEPTION WHEN insufficient_privilege OR check_violation THEN
        PERFORM set_config('pgtap.scrittura_log', 'RIFIUTATA', true);
    END;

    -- ⛔ SCRITTURA del legame lotto-fattura sul lotto altrui: e' il caso della
    --   decisione, guardato dal lato della scrittura.
    BEGIN
        INSERT INTO vendite.fatturazione_lotti_fatture (lotto_id, fattura_id)
        VALUES (v_b.lotto_id, v_a.fattura_id);
        PERFORM set_config('pgtap.scrittura_legame', 'PASSATA', true);
    EXCEPTION WHEN insufficient_privilege OR check_violation THEN
        PERFORM set_config('pgtap.scrittura_legame', 'RIFIUTATA', true);
    END;

    -- ⭐ L'adattatore interrogato direttamente, nei due versi.
    PERFORM set_config('pgtap.adattatore',
        CASE WHEN     script.fn_scope_ef_whitelist_via_lotto(v_a.auth_user_id, v_a.lotto_id)
              AND NOT script.fn_scope_ef_whitelist_via_lotto(v_a.auth_user_id, v_b.lotto_id)
             THEN 'CORRETTO' ELSE 'SBAGLIATO' END, true);

    -- ⛔ Nessuna veste: fail-closed su tutti e cinque.
    PERFORM set_config('app.ruolo_applicativo', '', true);
    SELECT (SELECT count(*) FROM vendite.fatturazione_lotti_esiti)
         + (SELECT count(*) FROM vendite.fatturazione_lotti_fatture)
         + (SELECT count(*) FROM vendite.fatturazione_lotti_gruppi)
         + (SELECT count(*) FROM vendite.fatturazione_lotti_log)
         + (SELECT count(*) FROM vendite.fatturazione_lotti_task_runs)
      INTO v_n;
    PERFORM set_config('pgtap.senza_veste', v_n::text, true);
END
$perimetro$;

ALTER TABLE vendite.fatturazione_lotti_task_runs    NO FORCE ROW LEVEL SECURITY;
ALTER TABLE vendite.fatturazione_lotti_log          NO FORCE ROW LEVEL SECURITY;
ALTER TABLE vendite.fatturazione_lotti_gruppi       NO FORCE ROW LEVEL SECURITY;
ALTER TABLE vendite.fatturazione_lotti_fatture      NO FORCE ROW LEVEL SECURITY;
ALTER TABLE vendite.fatturazione_lotti_esiti        NO FORCE ROW LEVEL SECURITY;
ALTER TABLE vendite.fatturazione_lotti              NO FORCE ROW LEVEL SECURITY;

SELECT isnt(current_setting('pgtap.esiti_a', true), '0',
            '5. l''operatore A vede gli esiti del PROPRIO lotto');

SELECT is(current_setting('pgtap.esiti_b', true), '0',
          '6. e non quelli del lotto di B: la riparazione');

SELECT is(current_setting('pgtap.legame_b', true), '0',
          '7. ne'' il legame lotto-fattura di B');

SELECT is(current_setting('pgtap.diario_b', true), '0',
          '8. ne'' il diario di B, che nomina documenti e commesse di un altro emittente');

SELECT is(current_setting('pgtap.scrittura_log', true), 'RIFIUTATA',
          '9. e non puo'' appendere una riga di diario al lotto di B (WITH CHECK)');

SELECT is(current_setting('pgtap.scrittura_legame', true), 'RIFIUTATA',
          '10. ne'' legare una propria fattura al lotto di B');

SELECT is(current_setting('pgtap.senza_veste', true), '0',
          '11. senza veste applicativa nessuno dei cinque risponde: fail-closed');

SELECT is(current_setting('pgtap.adattatore', true), 'CORRETTO',
          '12. l''adattatore _via_lotto dice il vero: il proprio lotto si'', quello di B no');

SELECT * FROM finish();

-- Il ROLLBACK e' la garanzia: comunque vada — verde, rosso, o morto a meta' —
-- questo file non lascia dietro di se' nessun lotto, nessuna fattura e nessuna
-- azienda di prova.
ROLLBACK;
