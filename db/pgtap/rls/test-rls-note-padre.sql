-- ------------------------------------------------------------
-- SPDX-License-Identifier: GPL-3.0-or-later
-- pgtap-runner: owner
-- pgtap-runner-motivo: ALTER TABLE … FORCE ROW LEVEL SECURITY, locale alla
--   transazione — e' il FORCE a rendere l'owner soggetto alle policy, perche'
--   `titodb` non e' superuser e non puo' fare SET ROLE. E la fixture costruisce
--   DUE aziende: un operatore dentro un perimetro non potrebbe crearle.
-- pgTAP test FUNZIONALE RLS — il PADRE partizionato vendite.note
--   Slice 20260909-72..74, brief brief-db-perimetro-emittente-righe-documento.md
--   Passo 8, l'ultimo: chiude la via che aggirava le policy delle partizioni.
--
-- Elenco test (plan 9):
--   1) struttura: il padre porta le TRE vesti
--   2) struttura: e la RLS e' ACCESA sul padre e sulla partizione ATTIVITA
--   3) struttura: ora tutte e SETTE le partizioni hanno la loro policy
--   4) ⭐ PRESIDIO: ogni confine di partizione del padre ha un ramo nello
--        smistatore — un tipo nuovo senza ramo fa rosso QUI
--   5) l'operatore A vede DAL PADRE la nota del proprio DDT
--   6) ⛔ e NON vede dal padre quella di B — e' la riparazione
--   7) ⛔ senza veste, dal padre, niente: fail-closed
--   8) ⛔ SCRITTURA dal padre: A non puo' appendere una nota al DDT di B
--   9) ⭐ il padre non e' MAI piu' permissivo della partizione
--
-- ────────────────────────────────────────────────────────────────
-- ⛔ IL DIFETTO CHE QUESTO FILE CHIUDE, misurato il 2026-09-09.
--   Le sette `note_*` sono PARTIZIONI di `vendite.note`. Con `note_ddt` gia'
--   armata dal passo 3, un operatore vedeva UNA riga dalla partizione e DUE dal
--   padre: le policy delle partizioni NON risalgono, e il padre non aveva RLS.
--   ⭐ Seconda misura, quella che ha deciso il progetto: armando il padre SENZA
--   policy propria, il padre risponde ZERO. Quindi non bastava accendere la
--   RLS: serviva una policy sul padre, che smista su `target_tipo`.
--
-- ⭐ IL TEST 4 E' IL PRESIDIO CHE VALE PIU' DI TUTTI, e il suo perimetro non e'
--   un elenco scritto a mano: legge i confini delle partizioni di
--   `vendite.note` e pretende che ognuno compaia come ramo dello smistatore.
--   Rev 2026-10-25 (grammatica unica, lotto 3, 20261025-54): il CHECK
--   chk_note_target_tipo e' ritirato (al suo posto la FK verso
--   config.tipi_entita); i tipi ammessi sono le partizioni, e il routing
--   rifiuta gli altri. Codici della grammatica: DDT -> DDT_VENDITA.
--   Il giorno in cui qualcuno aggiunge un'ottava famiglia di note e non passa
--   di qui, quelle note diventano invisibili dal padre (l'`ELSE false` e'
--   fail-closed) — e questo test diventa rosso e dice perche'. *Il presidio si
--   aggancia al contratto, non alla lista che avevo in mente.*
--
-- ⭐ IL TEST 9 E' L'INVARIANTE DELLA SLICE: il padre non deve essere piu'
--   permissivo di nessuna delle sue partizioni. Si misura confrontando cio' che
--   l'operatore vede dal padre con cio' che vede dalla partizione, sugli stessi
--   documenti.
--
-- ⛔ LA FIXTURE COSTRUISCE DUE MONDI e una nota di DDT per ciascuno: e' la
--   famiglia piu' economica da fabbricare, e il meccanismo del padre e' lo
--   stesso per tutte e sette — il test 4 copre le altre sei per struttura.
-- ------------------------------------------------------------

BEGIN;

SET CONSTRAINTS ALL IMMEDIATE;

SELECT plan(9);

-- ============================================================
-- I due mondi, un DDT per ciascuno, una nota per DDT
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
  CROSS JOIN LATERAL dbops.fn_pgtap_crea_cliente_ba('RLS note padre ' || m.lato, NULL, m.soggetto_ruolo_id) c;

CREATE TEMP TABLE _ddt AS
WITH d AS (
    -- rev 2026-10-09 (brief-db-esecutivi-ba-coppia): il BA del cliente, non la sola
    --   utility — chk_ddt_ba_utility_insieme vuole tutti e due o nessuno.
    INSERT INTO vendite.ddt
        (destinatario_soggetto_ruolo_id, stato_doc_ddt_id, emittente_fiscale_id, utility_id,
         billing_account_id)
    SELECT c.soggetto_ruolo_id,
           (SELECT st.id FROM config.stati_doc_ddt st WHERE st.codice_interno = 'DRAFT'),
           c.emittente_fiscale_id, c.utility_id, c.billing_account_id
      FROM _clienti c
    RETURNING id, emittente_fiscale_id
)
SELECT c.lato, d.id AS ddt_id
  FROM d JOIN _clienti c ON c.emittente_fiscale_id = d.emittente_fiscale_id;

INSERT INTO vendite.note_ddt (target_tipo, target_id, anchor_tipo, posizione, testo, id_stile)
SELECT 'DDT_VENDITA', d.ddt_id, 'DOCUMENTO', 'HEADER', 'Nota pgTAP padre ' || d.lato,
       (SELECT s.id FROM config.note_stili s WHERE s.codice_interno = 'NORMALE')
  FROM _ddt d;

-- ============================================================
-- 1..3. La struttura
-- ============================================================
SELECT is(
    (SELECT count(*)::int FROM pg_policies
      WHERE schemaname = 'vendite' AND tablename = 'note'),
    3,
    '1. il padre vendite.note porta le TRE vesti (operatore, portale, shop)'
);

SELECT is(
    (SELECT count(*)::int FROM pg_class c
       JOIN pg_namespace n ON n.oid = c.relnamespace AND n.nspname = 'vendite'
      WHERE c.relname IN ('note', 'note_attivita_fatturabili')
        AND c.relrowsecurity),
    2,
    '2. e la RLS e'' ACCESA sul padre e sulla partizione delle attivita'' (ATTIVITA)'
);

-- ⭐ Sette su sette: prima di questa slice `note_attivita_fatturabili` era
--   l'unica senza policy nemmeno sull'accesso diretto.
SELECT is(
    (SELECT count(DISTINCT p.tablename)::int FROM pg_policies p
      WHERE p.schemaname = 'vendite' AND p.tablename LIKE 'note!_%' ESCAPE '!'),
    7,
    '3. tutte e sette le partizioni hanno la loro policy sull''accesso diretto'
);

-- ============================================================
-- 4. Il presidio: i rami dello smistatore contro i confini delle partizioni
-- ============================================================
-- ⛔ Il perimetro non e' un elenco mio: sono le partizioni della tabella. Se
--   qualcuno aggiunge un target_tipo (una partizione) e non tocca lo
--   smistatore, qui diventa rosso.
-- Rev 2026-10-21 (20261021-25): lo smistatore e' script.fn_scope_note_ef_perimetro,
--   che riceve il perimetro dalla policy (prima fn_scope_note_ef_whitelist).
-- Rev 2026-10-25 (20261025-54): i tipi si leggono dai confini delle partizioni,
--   non piu' dal CHECK, ritirato. ⛔ Zero partizioni vale -1: un padre senza
--   partizioni farebbe verde per sottrazione.
SELECT is(
    (WITH confini AS (
         SELECT (regexp_match(pg_get_expr(c.relpartbound, c.oid), $r$IN \('([^']+)'\)$r$))[1] AS tipo
           FROM pg_inherits i JOIN pg_class c ON c.oid = i.inhrelid
          WHERE i.inhparent = 'vendite.note'::regclass)
     SELECT CASE WHEN (SELECT count(*) FROM confini) = 0 THEN -1
            ELSE (SELECT count(*)::int FROM confini v
                   -- coalesce: uno smistatore che manca e' rosso, non verde per sottrazione.
                   WHERE position('WHEN ''' || v.tipo || '''' IN
                                  coalesce((SELECT p.prosrc FROM pg_proc p
                                              JOIN pg_namespace n ON n.oid = p.pronamespace
                                             WHERE n.nspname = 'script'
                                               AND p.proname = 'fn_scope_note_ef_perimetro'), '')) = 0)
            END),
    0,
    '4. PRESIDIO: ogni confine di partizione del padre ha un ramo nello smistatore'
);

-- ============================================================
-- Il perimetro, esercitato DAL PADRE
-- ============================================================
ALTER TABLE vendite.ddt      FORCE ROW LEVEL SECURITY;
ALTER TABLE vendite.note     FORCE ROW LEVEL SECURITY;
ALTER TABLE vendite.note_ddt FORCE ROW LEVEL SECURITY;

DO $perimetro$
DECLARE
    v_a   record;
    v_b   record;
    v_ids bigint[];
    v_n   integer;
BEGIN
    SELECT d.*, m.auth_user_id INTO v_a
      FROM _ddt d JOIN _mondi m ON m.lato = d.lato WHERE d.lato = 'A';
    SELECT d.* INTO v_b FROM _ddt d WHERE d.lato = 'B';
    SELECT array_agg(ddt_id) INTO v_ids FROM _ddt;

    PERFORM script.fn_pgtap_set_contesto_operatore(v_a.auth_user_id);

    -- DAL PADRE: la propria.
    SELECT count(*) INTO v_n
      FROM vendite.note n WHERE n.target_tipo = 'DDT_VENDITA' AND n.target_id = v_a.ddt_id;
    PERFORM set_config('pgtap.padre_a', v_n::text, true);

    -- ⭐ DAL PADRE: l'altrui. Prima di questa slice qui si leggeva 1.
    SELECT count(*) INTO v_n
      FROM vendite.note n WHERE n.target_tipo = 'DDT_VENDITA' AND n.target_id = v_b.ddt_id;
    PERFORM set_config('pgtap.padre_b', v_n::text, true);

    -- ⭐ L'INVARIANTE: quello che si vede dal padre e' un sottoinsieme di
    --   quello che si vede dalla partizione. Si misura sulla differenza.
    SELECT count(*) INTO v_n
      FROM (SELECT target_id FROM vendite.note
             WHERE target_tipo = 'DDT_VENDITA' AND target_id = ANY(v_ids)
            EXCEPT
            SELECT target_id FROM vendite.note_ddt
             WHERE target_id = ANY(v_ids)) x;
    PERFORM set_config('pgtap.padre_piu_permissivo', v_n::text, true);

    -- ⛔ SCRITTURA dal padre sul documento altrui.
    BEGIN
        INSERT INTO vendite.note
            (target_tipo, target_id, anchor_tipo, posizione, testo, id_stile)
        VALUES ('DDT_VENDITA', v_b.ddt_id, 'DOCUMENTO', 'FOOTER', 'intrusione dal padre',
                (SELECT s.id FROM config.note_stili s WHERE s.codice_interno = 'NORMALE'));
        PERFORM set_config('pgtap.scrittura', 'PASSATA', true);
    EXCEPTION WHEN insufficient_privilege OR check_violation THEN
        PERFORM set_config('pgtap.scrittura', 'RIFIUTATA', true);
    END;

    -- ⛔ Nessuna veste: fail-closed anche dal padre.
    PERFORM set_config('app.ruolo_applicativo', '', true);
    SELECT count(*) INTO v_n
      FROM vendite.note n WHERE n.target_tipo = 'DDT_VENDITA' AND n.target_id = ANY(v_ids);
    PERFORM set_config('pgtap.senza_veste', v_n::text, true);
END
$perimetro$;

ALTER TABLE vendite.note_ddt NO FORCE ROW LEVEL SECURITY;
ALTER TABLE vendite.note     NO FORCE ROW LEVEL SECURITY;
ALTER TABLE vendite.ddt      NO FORCE ROW LEVEL SECURITY;

SELECT is(current_setting('pgtap.padre_a', true), '1',
          '5. dal PADRE l''operatore A vede la nota del proprio DDT');

SELECT is(current_setting('pgtap.padre_b', true), '0',
          '6. e dal PADRE non vede piu'' quella altrui: la via che aggirava le partizioni e'' chiusa');

SELECT is(current_setting('pgtap.senza_veste', true), '0',
          '7. senza veste applicativa, dal padre, niente: fail-closed');

SELECT is(current_setting('pgtap.scrittura', true), 'RIFIUTATA',
          '8. e non puo'' appendere una nota al documento altrui passando dal padre (WITH CHECK)');

SELECT is(current_setting('pgtap.padre_piu_permissivo', true), '0',
          '9. niente e'' visibile dal padre che non lo sia dalla partizione: il padre non e'' piu'' permissivo');

SELECT * FROM finish();

ROLLBACK;
