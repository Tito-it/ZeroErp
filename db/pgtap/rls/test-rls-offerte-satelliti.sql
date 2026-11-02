-- ------------------------------------------------------------
-- SPDX-License-Identifier: AGPL-3.0-or-later
-- pgtap-runner: owner
-- pgtap-runner-motivo: ALTER TABLE … FORCE ROW LEVEL SECURITY, locale alla
--   transazione — e' il FORCE a rendere l'owner soggetto alle policy, perche'
--   `titodb` non e' superuser e non puo' fare SET ROLE. E la fixture costruisce
--   DUE aziende: un operatore dentro un perimetro non potrebbe crearle.
-- pgTAP test FUNZIONALE RLS — satelliti di vendite.offerte_commerciali
--   Slice 20260909-47..49, brief brief-db-perimetro-emittente-righe-documento.md
--   ⭐ E' la SESTA e ultima famiglia di documento del brief.
--
-- Elenco test (plan 11):
--   1) struttura: i cinque satelliti hanno la loro policy
--   2) struttura: e la RLS ACCESA — non basta che la policy esista
--   3) l'operatore A vede l'eccezione della PROPRIA offerta
--   4) ⛔ e NON vede quella di B
--   5) ⛔ nemmeno la UTILITY dell'offerta di B
--   6) ⛔ nemmeno la NOTA: la chiave e' `target_id`, non `offerta_id`
--   7) ⛔ SCRITTURA: A non puo' appendere un'eccezione all'offerta di B
--   8) ⛔ senza veste non vede NIENTE — fail-closed
--   9) ⭐ nessuna eccezione visibile la cui OFFERTA non lo e'
--  10) ⚠️ l'adattatore a DUE livelli (eccezione -> offerta) risale davvero
--  11) ⭐ e nemmeno passando dal PADRE partizionato `vendite.note` — la via
--        che aggirava le policy delle partizioni, chiusa dal passo 8
--
-- ────────────────────────────────────────────────────────────────
-- ⭐ IL TEST 11 E' STATO GIRATO IL 2026-09-09, e la storia vale la nota.
--   `note_offerte_commerciali` — come le altre sei `note_*` — e' una PARTIZIONE
--   di `vendite.note`. Quando questa slice nacque, il padre aveva la RLS spenta
--   e `zeroerp_app` tutti i privilegi: la policy del test 6 proteggeva
--   l'accesso DIRETTO, e da `vendite.note` si leggeva tutto lo stesso.
--   Il test 11 ASSERIVA QUEL BUCO — `= 1` — come debito dichiarato, scritto nel
--   verso che si accorge della riparazione.
--   ⭐ Il passo 8 (slice 20260909-72..74) ha chiuso il padre con tre policy che
--   smistano su `target_tipo`, e il test e' diventato rosso: esattamente cio'
--   per cui era stato scritto. E' stato SOSTITUITO con la sua asserzione
--   positiva — «dal padre si vede solo il proprio» — non allargato per farlo
--   tacere. Un test che pinna un sintomo e uno che pretende la riparazione sono
--   due test diversi, e questo e' il secondo.
--
-- ⭐ IL TEST 2 NON E' IL DOPPIONE DEL TEST 1: una policy senza
--   `ENABLE ROW LEVEL SECURITY` sta in `pg_policy` e non filtra niente.
--
-- ⛔ LA FIXTURE SI COSTRUISCE, e per le offerte la catena e' la piu' lunga del
--   brief: `offerte_commerciali` pretende `billing_account_id`,
--   `istanza_utility_id` e **`listino_id`**, tutti NOT NULL — e un listino e' a
--   sua volta scoped per emittente. Quindi ogni mondo ha il suo listino.
--   ⚠️ Il billing account va LEGATO all'emittente (terzo parametro di
--   `fn_pgtap_crea_cliente_ba`, changeSet 20260909-43): senza,
--   `fn_get_emittente_fiscale_pk` non fallisce — ricade sull'emittente di
--   DEFAULT — e il guard `trgfn_offerte_guard_emittente_ba` rifiuta l'offerta.
--
-- ⛔ NIENTE riga di `offerte_commerciali_eccezioni_componenti`: pretende una
--   distinta base, che su un database ricostruito non esiste. Il suo perimetro
--   passa dall'adattatore che il test 10 interroga direttamente.
-- ------------------------------------------------------------

-- ⚠️ Rev 2026-10-07 (brief-db-offerta-emissione-ed-erogazione §C.9, giro B3): la riga
--   deve stare nel PERIMETRO dell'articolo, o il guard BEFORE ROW parla (P0001) prima della
--   RLS che qui si prova. L'articolo e' il primo SENZA tipologia (decide la natura, e la
--   utility del cliente non conta) che ammette UNA_TANTUM/FISSA, chiesto alla sede unica
--   vendite.fn_articolo_erogazioni; l'erogazione era CANONE per caso, ora UNA_TANTUM.

BEGIN;

SET CONSTRAINTS ALL IMMEDIATE;

SELECT plan(11);

-- ============================================================
-- I due mondi, ciascuno col suo listino e la sua offerta
-- ============================================================
CREATE TEMP TABLE _mondi AS
SELECT 'A' AS lato, * FROM dbops.fn_pgtap_crea_emittente_operatore()
UNION ALL
SELECT 'B' AS lato, * FROM dbops.fn_pgtap_crea_emittente_operatore();

CREATE TEMP TABLE _clienti AS
SELECT m.lato, m.emittente_fiscale_id, m.soggetto_ruolo_id AS emittente_sr_id, c.*
  FROM _mondi m
  CROSS JOIN LATERAL dbops.fn_pgtap_crea_cliente_ba(
      'RLS offerte ' || m.lato, NULL, m.soggetto_ruolo_id) c;

-- ⚠️ Il listino porta l'emittente come SOGGETTO_RUOLO, non come id fiscale:
--   sono due convenzioni per la stessa azienda e la traduzione e' 1:1.
CREATE TEMP TABLE _listini AS
WITH l AS (
    INSERT INTO vendite.listini
        (codice, descrizione, utility_id, tipologia_id, emittente_soggetto_ruolo_id)
    SELECT 'PGTAPLIS-' || c.lato || '-' || c.billing_account_id,
           'Listino pgTAP RLS offerte ' || c.lato,
           c.utility_id,
           (SELECT t.id FROM config.listini_tipologie t ORDER BY t.id LIMIT 1),
           c.emittente_sr_id
      FROM _clienti c
    RETURNING id, emittente_soggetto_ruolo_id
)
SELECT c.lato, l.id AS listino_id
  FROM l JOIN _clienti c ON c.emittente_sr_id = l.emittente_soggetto_ruolo_id;

CREATE TEMP TABLE _offerte AS
WITH o AS (
    INSERT INTO vendite.offerte_commerciali
        (codice, emittente_fiscale_id, billing_account_id, istanza_utility_id,
         utility_id, listino_id, validita_dal, stato_doc_offerta_id)
    SELECT 'PGTAPOFF-' || c.lato, c.emittente_fiscale_id, c.billing_account_id,
           c.istanza_utility_id, c.utility_id, l.listino_id, script.fn_data_operativa(),
           (SELECT st.id FROM config.stati_doc_offerte st WHERE st.codice_interno = 'BOZZA')
      FROM _clienti c JOIN _listini l ON l.lato = c.lato
    RETURNING id, emittente_fiscale_id
)
SELECT c.lato, o.id AS offerta_id, o.emittente_fiscale_id,
       c.istanza_utility_id, c.utility_id
  FROM o JOIN _clienti c ON c.emittente_fiscale_id = o.emittente_fiscale_id;

-- ⚠️ `AGGIUNTA` pretende un prezzo; `qta_operativa` la pretende
--   `trgfn_qta_from_operativa`, che da li' deriva la quantita'.
-- tipo_erogazione: obbligatoria su OVERRIDE/AGGIUNTA dal 2026-10-04 (brief-db-erogazione-obbligatoria-righe-fatturate).
CREATE TEMP TABLE _ecc AS
WITH e AS (
    INSERT INTO vendite.offerte_commerciali_eccezioni
        (offerta_id, articolo_id, tipo_eccezione, fonte_quantita_attesa,
         prezzo_unitario, qta_operativa, tipo_erogazione)
    SELECT o.offerta_id,
           (SELECT a.id FROM catalogo.articoli a
             WHERE a.listino_tipologia_id IS NULL
               AND EXISTS (SELECT 1 FROM vendite.fn_articolo_erogazioni(a.id) e
                            WHERE e.tipo_erogazione = 'UNA_TANTUM'
                              AND e.fonte_quantita_attesa = 'FISSA')
             ORDER BY a.id LIMIT 1),
           'AGGIUNTA'::vendite.tipo_eccezione_contratto, 'FISSA', 100.00, 1, 'UNA_TANTUM'
      FROM _offerte o
    RETURNING id, offerta_id
)
SELECT o.lato, e.id AS eccezione_id, e.offerta_id
  FROM e JOIN _offerte o ON o.offerta_id = e.offerta_id;

INSERT INTO vendite.offerte_commerciali_utilities (offerta_id, istanza_utility_id, utility_id)
SELECT o.offerta_id, o.istanza_utility_id, o.utility_id FROM _offerte o;

INSERT INTO vendite.offerte_commerciali_indirizzi (offerta_id, tipo_indirizzo_id, snapshot)
SELECT o.offerta_id,
       (SELECT ti.id FROM config.tipi_indirizzi ti WHERE ti.codice_interno = 'FATT'),
       '{"pgtap": true}'::jsonb
  FROM _offerte o;

INSERT INTO vendite.note_offerte_commerciali
    (target_tipo, target_id, anchor_tipo, posizione, testo, id_stile)
SELECT 'OFFERTA_COMMERCIALE', o.offerta_id, 'DOCUMENTO', 'HEADER', 'Nota pgTAP RLS',
       (SELECT s.id FROM config.note_stili s WHERE s.codice_interno = 'NORMALE')
  FROM _offerte o;

-- ============================================================
-- 1..2. La struttura: policy E armamento
-- ============================================================
SELECT is(
    (SELECT count(*)::int FROM pg_policies
      WHERE schemaname = 'vendite'
        AND tablename IN ('offerte_commerciali_eccezioni', 'offerte_commerciali_indirizzi',
                          'offerte_commerciali_utilities', 'note_offerte_commerciali',
                          'offerte_commerciali_eccezioni_componenti')),
    5,
    '1. i cinque satelliti di offerte_commerciali hanno la loro policy'
);

SELECT is(
    (SELECT count(*)::int FROM pg_class c
       JOIN pg_namespace n ON n.oid = c.relnamespace AND n.nspname = 'vendite'
      WHERE c.relname IN ('offerte_commerciali_eccezioni', 'offerte_commerciali_indirizzi',
                          'offerte_commerciali_utilities', 'note_offerte_commerciali',
                          'offerte_commerciali_eccezioni_componenti')
        AND c.relrowsecurity),
    5,
    '2. e su tutti e cinque la RLS e'' ACCESA, non solo dichiarata'
);

-- ============================================================
-- Il perimetro, esercitato
-- ============================================================
ALTER TABLE vendite.offerte_commerciali            FORCE ROW LEVEL SECURITY;
ALTER TABLE vendite.offerte_commerciali_eccezioni  FORCE ROW LEVEL SECURITY;
ALTER TABLE vendite.offerte_commerciali_utilities  FORCE ROW LEVEL SECURITY;
ALTER TABLE vendite.note_offerte_commerciali       FORCE ROW LEVEL SECURITY;
-- ⭐ Anche il PADRE partizionato: senza il FORCE l'owner ne resta esente e il
--   test 11 misurerebbe zero difesa — leggendo tutto e dando la colpa al padre.
ALTER TABLE vendite.note                           FORCE ROW LEVEL SECURITY;

DO $perimetro$
DECLARE
    v_a record;
    v_b record;
    v_n integer;
BEGIN
    SELECT o.*, m.auth_user_id INTO v_a
      FROM _offerte o JOIN _mondi m ON m.emittente_fiscale_id = o.emittente_fiscale_id
     WHERE o.lato = 'A';
    SELECT o.* INTO v_b FROM _offerte o WHERE o.lato = 'B';

    PERFORM script.fn_pgtap_set_contesto_operatore(v_a.auth_user_id);

    SELECT count(*) INTO v_n
      FROM vendite.offerte_commerciali_eccezioni e WHERE e.offerta_id = v_a.offerta_id;
    PERFORM set_config('pgtap.ecc_a', v_n::text, true);

    SELECT count(*) INTO v_n
      FROM vendite.offerte_commerciali_eccezioni e WHERE e.offerta_id = v_b.offerta_id;
    PERFORM set_config('pgtap.ecc_b', v_n::text, true);

    SELECT count(*) INTO v_n
      FROM vendite.offerte_commerciali_utilities u WHERE u.offerta_id = v_b.offerta_id;
    PERFORM set_config('pgtap.util_b', v_n::text, true);

    SELECT count(*) INTO v_n
      FROM vendite.note_offerte_commerciali n WHERE n.target_id = v_b.offerta_id;
    PERFORM set_config('pgtap.note_b', v_n::text, true);

    -- ⭐ La stessa nota, letta dal PADRE partizionato: dal passo 8 il padre ha
    --   le sue policy, quindi qui si deve leggere ZERO come dalla partizione.
    SELECT count(*) INTO v_n
      FROM vendite.note n WHERE n.target_id = v_b.offerta_id AND n.target_tipo = 'OFFERTA_COMMERCIALE';
    PERFORM set_config('pgtap.note_b_dal_padre', v_n::text, true);

    -- ⭐ L'INVARIANTE verso la testata.
    SELECT count(*) INTO v_n
      FROM vendite.offerte_commerciali_eccezioni e
     WHERE NOT EXISTS (SELECT 1 FROM vendite.offerte_commerciali o WHERE o.id = e.offerta_id);
    PERFORM set_config('pgtap.orfane', v_n::text, true);

    PERFORM set_config('pgtap.ecc2',
        script.fn_scope_ef_whitelist_via_offerta_eccezione(
            v_a.auth_user_id, (SELECT eccezione_id FROM _ecc WHERE lato = 'A'))::text
        || '/' ||
        script.fn_scope_ef_whitelist_via_offerta_eccezione(
            v_a.auth_user_id, (SELECT eccezione_id FROM _ecc WHERE lato = 'B'))::text,
        true);

    -- ⛔ La scrittura sull'offerta altrui.
    -- tipo_erogazione: obbligatoria su OVERRIDE/AGGIUNTA dal 2026-10-04 (brief-db-erogazione-obbligatoria-righe-fatturate);
    --   senza, il guard BEFORE ROW parlerebbe (P0001) prima della RLS che qui si prova.
    BEGIN
        INSERT INTO vendite.offerte_commerciali_eccezioni
            (offerta_id, articolo_id, tipo_eccezione, fonte_quantita_attesa,
             prezzo_unitario, qta_operativa, tipo_erogazione)
        VALUES (v_b.offerta_id,
                (SELECT a.id FROM catalogo.articoli a
             WHERE a.listino_tipologia_id IS NULL
               AND EXISTS (SELECT 1 FROM vendite.fn_articolo_erogazioni(a.id) e
                            WHERE e.tipo_erogazione = 'UNA_TANTUM'
                              AND e.fonte_quantita_attesa = 'FISSA')
             ORDER BY a.id LIMIT 1),
                'AGGIUNTA'::vendite.tipo_eccezione_contratto, 'FISSA', 1.00, 1, 'UNA_TANTUM');
        PERFORM set_config('pgtap.scrittura', 'PASSATA', true);
    EXCEPTION WHEN insufficient_privilege OR check_violation THEN
        PERFORM set_config('pgtap.scrittura', 'RIFIUTATA', true);
    END;

    -- ⛔ Nessuna veste: fail-closed.
    PERFORM set_config('app.ruolo_applicativo', '', true);
    SELECT count(*) INTO v_n
      FROM vendite.offerte_commerciali_eccezioni e
     WHERE e.offerta_id IN (v_a.offerta_id, v_b.offerta_id);
    PERFORM set_config('pgtap.senza_veste', v_n::text, true);
END
$perimetro$;

ALTER TABLE vendite.note                           NO FORCE ROW LEVEL SECURITY;
ALTER TABLE vendite.note_offerte_commerciali       NO FORCE ROW LEVEL SECURITY;
ALTER TABLE vendite.offerte_commerciali_utilities  NO FORCE ROW LEVEL SECURITY;
ALTER TABLE vendite.offerte_commerciali_eccezioni  NO FORCE ROW LEVEL SECURITY;
ALTER TABLE vendite.offerte_commerciali            NO FORCE ROW LEVEL SECURITY;

SELECT is(current_setting('pgtap.ecc_a', true), '1',
          '3. l''operatore A vede l''eccezione della propria offerta');

SELECT is(current_setting('pgtap.ecc_b', true), '0',
          '4. e NON vede quella dell''offerta di un''altra azienda');

SELECT is(current_setting('pgtap.util_b', true), '0',
          '5. nemmeno la UTILITY dell''offerta altrui');

SELECT is(current_setting('pgtap.note_b', true), '0',
          '6. nemmeno la NOTA: la chiave e'' target_id, non offerta_id');

SELECT is(current_setting('pgtap.scrittura', true), 'RIFIUTATA',
          '7. e non puo'' appendere un''eccezione all''offerta altrui (WITH CHECK)');

SELECT is(current_setting('pgtap.senza_veste', true), '0',
          '8. senza veste applicativa non vede niente: fail-closed');

SELECT is(current_setting('pgtap.orfane', true), '0',
          '9. nessuna eccezione visibile la cui OFFERTA non lo e'': il satellite non e'' piu'' permissivo della testata');

SELECT is(current_setting('pgtap.ecc2', true), 'true/false',
          '10. l''adattatore a due livelli risale davvero: vero sull''eccezione di A, falso su quella di B');

-- ⭐ Era `= 1` — il buco dichiarato — fino al passo 8, che ha dato al padre
--   partizionato le sue tre policy. Ora e' un'asserzione di difesa.
SELECT is(current_setting('pgtap.note_b_dal_padre', true), '0',
          '11. e nemmeno dal PADRE vendite.note: la via che aggirava le partizioni e'' chiusa');

SELECT * FROM finish();

ROLLBACK;
