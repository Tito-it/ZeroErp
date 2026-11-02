-- ------------------------------------------------------------
-- SPDX-License-Identifier: AGPL-3.0-or-later
-- pgtap-runner: owner
-- pgtap-runner-motivo: ALTER TABLE … FORCE ROW LEVEL SECURITY, locale alla
--   transazione — e' il FORCE a rendere l'owner soggetto alle policy, perche'
--   `titodb` non e' superuser e non puo' fare SET ROLE. E la fixture costruisce
--   DUE aziende: un operatore dentro un perimetro non potrebbe crearle.
-- pgTAP test FUNZIONALE RLS — satelliti di vendite.contratti
--   Slice 20260909-44..46, brief brief-db-perimetro-emittente-righe-documento.md
--
-- Elenco test (plan 10):
--   1) struttura: i cinque satelliti hanno la loro policy
--   2) struttura: e la RLS ACCESA — non basta che la policy esista
--   3) l'operatore A vede la riga del PROPRIO contratto
--   4) ⛔ e NON vede quella di B
--   5) ⛔ nemmeno la UTILITY del contratto di B
--   6) ⛔ nemmeno la NOTA: la chiave e' `target_id`, non `contratto_id`
--   7) ⛔ SCRITTURA: A non puo' appendere una riga al contratto di B
--   8) ⛔ senza veste non vede NIENTE — fail-closed
--   9) ⭐ nessuna riga visibile il cui CONTRATTO non lo e'
--  10) ⚠️ l'adattatore a DUE livelli (riga -> contratto) risale davvero
--
-- ────────────────────────────────────────────────────────────────
-- ⭐ QUESTA E' LA PRIMA FAMIGLIA CON IL BILLING ACCOUNT OBBLIGATORIO, ed e' la
--   sola cosa davvero nuova rispetto alle quattro precedenti.
--   `vendite.contratti.billing_account_id` e' `NOT NULL`, e su ogni testata c'e'
--   un guard `trgfn_<documento>_guard_emittente_ba` che pretende
--       emittente_fiscale_id = anagrafiche.fn_get_emittente_fiscale_pk(ba)
--   Con il BA nullo — ddt, resi, preventivi — quel guard esce subito, ed e' il
--   motivo per cui non si era mai visto. Qui morde.
--   ⚠️ E il modo in cui morde e' insidioso: senza una riga in
--   `emittenti_fiscali_billing_account`, `fn_get_emittente_fiscale_pk` NON
--   fallisce — ricade sull'emittente di DEFAULT dell'installazione, cioe'
--   risponde un'altra azienda. La fixture chiede quindi il legame esplicito
--   (terzo parametro di `fn_pgtap_crea_cliente_ba`, changeSet 20260909-43).
--
-- ⭐ IL TEST 2 NON E' IL DOPPIONE DEL TEST 1: una policy senza
--   `ENABLE ROW LEVEL SECURITY` sta in `pg_policy` e non filtra niente. Ne
--   restano tre cosi' in tutto il database.
--
-- ⭐ I TEST 5 E 6 STANNO DOVE LA CHIAVE CAMBIA NOME. Tre satelliti su cinque
--   non si chiamano `<doc>_righe`: `contratti_utilities` e `contratti_indirizzi`
--   risalgono da `contratto_id`, `note_contratto` da `target_id`. Sono i punti
--   in cui un refuso nella policy non farebbe rumore — la tabella resterebbe
--   semplicemente aperta.
--
-- ⛔ NIENTE riga di `contratti_righe_componenti` nella fixture: pretende una
--   distinta base (`catalogo.articoli_componenti`), che su un database
--   ricostruito dai changelog non esiste. Il suo perimetro passa dallo stesso
--   adattatore `_via_contratto_riga` che il test 10 interroga direttamente.
--   *Non serve una riga per chiedere a una funzione se dice il vero.*
-- ------------------------------------------------------------

-- ⚠️ Rev 2026-10-07 (brief-db-offerta-emissione-ed-erogazione §C.9, giro B3): la riga
--   deve stare nel PERIMETRO dell'articolo, o il guard BEFORE ROW parla (P0001) prima della
--   RLS che qui si prova. L'articolo e' il primo SENZA tipologia (decide la natura, e la
--   utility del cliente non conta) che ammette UNA_TANTUM/FISSA, chiesto alla sede unica
--   vendite.fn_articolo_erogazioni; l'erogazione era CANONE per caso, ora UNA_TANTUM.

BEGIN;

SET CONSTRAINTS ALL IMMEDIATE;

SELECT plan(10);

-- ============================================================
-- I due mondi, e per ciascuno un contratto completo
-- ============================================================
CREATE TEMP TABLE _mondi AS
SELECT 'A' AS lato, * FROM dbops.fn_pgtap_crea_emittente_operatore()
UNION ALL
SELECT 'B' AS lato, * FROM dbops.fn_pgtap_crea_emittente_operatore();

-- ⛔ Il terzo parametro LEGA il billing account all'emittente del suo mondo.
--   Senza, il guard `trgfn_contratti_guard_emittente_ba` rifiuta il contratto:
--   vedi l'intestazione.
CREATE TEMP TABLE _clienti AS
SELECT m.lato, m.emittente_fiscale_id, c.*
  FROM _mondi m
  CROSS JOIN LATERAL dbops.fn_pgtap_crea_cliente_ba(
      'RLS contratti ' || m.lato, NULL, m.soggetto_ruolo_id) c;

-- ⚠️ `validita` NON si nomina: e' GENERATED (PG18).
CREATE TEMP TABLE _contratti AS
WITH x AS (
    INSERT INTO vendite.contratti
        (numero, billing_account_id, istanza_utility_id, utility_id,
         stato_doc_contratto_id, emittente_fiscale_id)
    SELECT 'PGTAPRLS-C-' || c.lato,
           c.billing_account_id, c.istanza_utility_id, c.utility_id,
           (SELECT st.id FROM config.stati_doc_contratti st WHERE st.codice_interno = 'DRAFT'),
           c.emittente_fiscale_id
      FROM _clienti c
    RETURNING id, emittente_fiscale_id
)
SELECT c.lato, x.id AS contratto_id, x.emittente_fiscale_id,
       c.istanza_utility_id, c.utility_id
  FROM x JOIN _clienti c ON c.emittente_fiscale_id = x.emittente_fiscale_id;

-- ⚠️ `AGGIUNTA` pretende un prezzo (`chk_contrighe_prezzo_per_tipo_eccezione`),
--   `ESCLUSIONE` lo pretende NULL: si sceglie il primo perche' una riga con un
--   prezzo e' quella che un operatore altrui non deve leggere.
-- tipo_erogazione: obbligatoria su OVERRIDE/AGGIUNTA dal 2026-10-04 (brief-db-erogazione-obbligatoria-righe-fatturate).
CREATE TEMP TABLE _righe AS
WITH r AS (
    INSERT INTO vendite.contratti_righe
        (contratto_id, articolo_id, fonte_quantita_attesa, tipo_eccezione,
         prezzo_unitario, qta_operativa, tipo_erogazione)
    SELECT k.contratto_id,
           (SELECT a.id FROM catalogo.articoli a
             WHERE a.listino_tipologia_id IS NULL
               AND EXISTS (SELECT 1 FROM vendite.fn_articolo_erogazioni(a.id) e
                            WHERE e.tipo_erogazione = 'UNA_TANTUM'
                              AND e.fonte_quantita_attesa = 'FISSA')
             ORDER BY a.id LIMIT 1),
           'FISSA', 'AGGIUNTA'::vendite.tipo_eccezione_contratto,
           100.00, 1, 'UNA_TANTUM'
      FROM _contratti k
    RETURNING id, contratto_id
)
SELECT k.lato, r.id AS riga_id, r.contratto_id
  FROM r JOIN _contratti k ON k.contratto_id = r.contratto_id;

INSERT INTO vendite.contratti_utilities (contratto_id, istanza_utility_id, utility_id)
SELECT k.contratto_id, k.istanza_utility_id, k.utility_id FROM _contratti k;

-- ⚠️ Per l'ambito CONTRATTI `config.tipi_indirizzi_allowed` ammette FATT, CON e
--   FORNITURA, nessuno obbligatorio.
INSERT INTO vendite.contratti_indirizzi (contratto_id, tipo_indirizzo_id, snapshot)
SELECT k.contratto_id,
       (SELECT ti.id FROM config.tipi_indirizzi ti WHERE ti.codice_interno = 'FATT'),
       '{"pgtap": true}'::jsonb
  FROM _contratti k;

INSERT INTO vendite.note_contratto
    (target_tipo, target_id, anchor_tipo, posizione, testo, id_stile)
SELECT 'CONTRATTO', k.contratto_id, 'DOCUMENTO', 'HEADER', 'Nota pgTAP RLS',
       (SELECT s.id FROM config.note_stili s WHERE s.codice_interno = 'NORMALE')
  FROM _contratti k;

-- ============================================================
-- 1..2. La struttura: policy E armamento
-- ============================================================
SELECT is(
    (SELECT count(*)::int FROM pg_policies
      WHERE schemaname = 'vendite'
        AND tablename IN ('contratti_righe', 'contratti_indirizzi',
                          'contratti_utilities', 'note_contratto',
                          'contratti_righe_componenti')),
    5,
    '1. i cinque satelliti di contratti hanno la loro policy'
);

SELECT is(
    (SELECT count(*)::int FROM pg_class c
       JOIN pg_namespace n ON n.oid = c.relnamespace AND n.nspname = 'vendite'
      WHERE c.relname IN ('contratti_righe', 'contratti_indirizzi',
                          'contratti_utilities', 'note_contratto',
                          'contratti_righe_componenti')
        AND c.relrowsecurity),
    5,
    '2. e su tutti e cinque la RLS e'' ACCESA, non solo dichiarata'
);

-- ============================================================
-- Il perimetro, esercitato
-- ============================================================
ALTER TABLE vendite.contratti             FORCE ROW LEVEL SECURITY;
ALTER TABLE vendite.contratti_righe       FORCE ROW LEVEL SECURITY;
ALTER TABLE vendite.contratti_utilities   FORCE ROW LEVEL SECURITY;
ALTER TABLE vendite.note_contratto        FORCE ROW LEVEL SECURITY;

DO $perimetro$
DECLARE
    v_a record;
    v_b record;
    v_n integer;
BEGIN
    SELECT k.*, m.auth_user_id INTO v_a
      FROM _contratti k JOIN _mondi m ON m.emittente_fiscale_id = k.emittente_fiscale_id
     WHERE k.lato = 'A';
    SELECT k.* INTO v_b FROM _contratti k WHERE k.lato = 'B';

    PERFORM script.fn_pgtap_set_contesto_operatore(v_a.auth_user_id);

    SELECT count(*) INTO v_n
      FROM vendite.contratti_righe r WHERE r.contratto_id = v_a.contratto_id;
    PERFORM set_config('pgtap.righe_a', v_n::text, true);

    SELECT count(*) INTO v_n
      FROM vendite.contratti_righe r WHERE r.contratto_id = v_b.contratto_id;
    PERFORM set_config('pgtap.righe_b', v_n::text, true);

    SELECT count(*) INTO v_n
      FROM vendite.contratti_utilities u WHERE u.contratto_id = v_b.contratto_id;
    PERFORM set_config('pgtap.utilities_b', v_n::text, true);

    SELECT count(*) INTO v_n
      FROM vendite.note_contratto nc WHERE nc.target_id = v_b.contratto_id;
    PERFORM set_config('pgtap.note_b', v_n::text, true);

    -- ⭐ L'INVARIANTE: il satellite non puo' essere piu' permissivo della
    --   testata. Righe visibili il cui contratto, invece, non lo e': ZERO.
    SELECT count(*) INTO v_n
      FROM vendite.contratti_righe r
     WHERE NOT EXISTS (SELECT 1 FROM vendite.contratti k WHERE k.id = r.contratto_id);
    PERFORM set_config('pgtap.orfane', v_n::text, true);

    -- La risalita a due livelli, chiesta all'adattatore.
    PERFORM set_config('pgtap.riga2',
        script.fn_scope_ef_whitelist_via_contratto_riga(
            v_a.auth_user_id, (SELECT riga_id FROM _righe WHERE lato = 'A'))::text
        || '/' ||
        script.fn_scope_ef_whitelist_via_contratto_riga(
            v_a.auth_user_id, (SELECT riga_id FROM _righe WHERE lato = 'B'))::text,
        true);

    -- ⛔ La scrittura sul contratto altrui.
    -- tipo_erogazione: obbligatoria su OVERRIDE/AGGIUNTA dal 2026-10-04 (brief-db-erogazione-obbligatoria-righe-fatturate);
    --   senza, il guard BEFORE ROW parlerebbe (P0001) prima della RLS che qui si prova.
    BEGIN
        INSERT INTO vendite.contratti_righe
            (contratto_id, articolo_id, fonte_quantita_attesa, tipo_eccezione,
             prezzo_unitario, qta_operativa, tipo_erogazione)
        VALUES (v_b.contratto_id,
                (SELECT a.id FROM catalogo.articoli a
             WHERE a.listino_tipologia_id IS NULL
               AND EXISTS (SELECT 1 FROM vendite.fn_articolo_erogazioni(a.id) e
                            WHERE e.tipo_erogazione = 'UNA_TANTUM'
                              AND e.fonte_quantita_attesa = 'FISSA')
             ORDER BY a.id LIMIT 1),
                'FISSA', 'AGGIUNTA'::vendite.tipo_eccezione_contratto, 1.00, 1, 'UNA_TANTUM');
        PERFORM set_config('pgtap.scrittura', 'PASSATA', true);
    EXCEPTION WHEN insufficient_privilege OR check_violation THEN
        PERFORM set_config('pgtap.scrittura', 'RIFIUTATA', true);
    END;

    -- ⛔ Nessuna veste: fail-closed.
    PERFORM set_config('app.ruolo_applicativo', '', true);
    SELECT count(*) INTO v_n
      FROM vendite.contratti_righe r
     WHERE r.contratto_id IN (v_a.contratto_id, v_b.contratto_id);
    PERFORM set_config('pgtap.senza_veste', v_n::text, true);
END
$perimetro$;

ALTER TABLE vendite.note_contratto        NO FORCE ROW LEVEL SECURITY;
ALTER TABLE vendite.contratti_utilities   NO FORCE ROW LEVEL SECURITY;
ALTER TABLE vendite.contratti_righe       NO FORCE ROW LEVEL SECURITY;
ALTER TABLE vendite.contratti             NO FORCE ROW LEVEL SECURITY;

SELECT is(current_setting('pgtap.righe_a', true), '1',
          '3. l''operatore A vede la riga del proprio contratto');

SELECT is(current_setting('pgtap.righe_b', true), '0',
          '4. e NON vede la riga del contratto di un''altra azienda');

SELECT is(current_setting('pgtap.utilities_b', true), '0',
          '5. nemmeno la UTILITY del contratto altrui');

SELECT is(current_setting('pgtap.note_b', true), '0',
          '6. nemmeno la NOTA: la chiave e'' target_id, non contratto_id');

SELECT is(current_setting('pgtap.scrittura', true), 'RIFIUTATA',
          '7. e non puo'' appendere una riga al contratto altrui (WITH CHECK)');

SELECT is(current_setting('pgtap.senza_veste', true), '0',
          '8. senza veste applicativa non vede niente: fail-closed');

SELECT is(current_setting('pgtap.orfane', true), '0',
          '9. nessuna riga visibile il cui CONTRATTO non lo e'': il satellite non e'' piu'' permissivo della testata');

SELECT is(current_setting('pgtap.riga2', true), 'true/false',
          '10. l''adattatore a due livelli risale davvero: vero sulla riga di A, falso su quella di B');

SELECT * FROM finish();

ROLLBACK;
