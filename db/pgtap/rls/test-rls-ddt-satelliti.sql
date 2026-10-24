-- ------------------------------------------------------------
-- SPDX-License-Identifier: GPL-3.0-or-later
-- pgtap-runner: owner
-- pgtap-runner-motivo: ALTER TABLE … FORCE ROW LEVEL SECURITY, locale alla
--   transazione — e' il FORCE a rendere l'owner soggetto alle policy, perche'
--   `titodb` non e' superuser e non puo' fare SET ROLE. E la fixture costruisce
--   DUE aziende: un operatore dentro un perimetro non potrebbe crearle.
-- pgTAP test FUNZIONALE RLS — satelliti di vendite.ddt
--   Slice 20260909-36..38, brief brief-db-perimetro-emittente-righe-documento.md
--
-- Elenco test (plan 10):
--   1) struttura: i quattro satelliti hanno la loro policy
--   2) struttura: e la RLS ACCESA — non basta che la policy esista
--   3) l'operatore A vede la riga del PROPRIO DDT
--   4) ⛔ e NON vede quella di B
--   5) ⛔ la NOTA di B non si vede: la chiave e' `target_id`, non `ddt_id`
--   6) ⛔ l'INDIRIZZO di B non si vede
--   7) ⛔ SCRITTURA: A non puo' appendere una riga al DDT di B (WITH CHECK)
--   8) ⛔ senza veste non vede NIENTE — fail-closed
--   9) ⭐ il satellite non e' MAI piu' permissivo della testata: nessuna riga
--         visibile il cui DDT non lo sia
--  10) ⚠️ l'adattatore a DUE livelli (riga -> DDT) risale davvero
--
-- ────────────────────────────────────────────────────────────────
-- ⭐ PERCHE' QUESTO TEST E' PIU' CORTO DI QUELLO DEGLI ORDINI.
--   `vendite.ddt` porta UNA veste (`rls_ddt_ef_whitelist`, OPERATORE, FOR ALL),
--   mentre `vendite.ordini` ne portava tre. Non ci sono quindi il caso
--   `CLIENTE_PORTALE` ne' quello `SHOP_CUSTOMER` da rispecchiare: nessuna
--   condizione in piu' che un satellite possa dimenticarsi.
--   ⚠️ Se un domani `vendite.ddt` ricevesse una veste cliente, questo file va
--   allungato nello stesso gesto in cui la policy nasce — altrimenti misura una
--   forma che il documento non ha piu'.
--
-- ⭐ IL TEST 2 NON E' IL DOPPIONE DEL TEST 1. Una policy senza
--   `ENABLE ROW LEVEL SECURITY` sta in `pg_policy` e non filtra niente. Non e'
--   un'ipotesi: il 2026-09-09 `acquisti.ddt`, `acquisti.ordini` e
--   `shop.ricevute` erano esattamente in quello stato, e chi avesse verificato
--   con `EXISTS (SELECT 1 FROM pg_policies …)` avrebbe letto verde.
--
-- ⭐ IL TEST 7 E' L'ALTRA META' DELLA DIFESA. Una policy di sola lettura lascia
--   SCRIVERE fuori perimetro: il `WITH CHECK` e' cio' che impedisce a un
--   operatore di appendere una riga al DDT di un'altra azienda. E' la parte che
--   si dimentica, perche' il sintomo non si vede leggendo.
--
-- ⛔ NESSUNA riga di `ddt_righe_componenti` nella fixture, ed e' una scelta.
--   Un componente pretende `componente_id` verso `catalogo.articoli_componenti`,
--   cioe' una distinta base: su un database ricostruito dai changelog non ce ne
--   sono. Costruirne una e' una catena che non appartiene a questa slice, e
--   usarne una esistente renderebbe il file verde su dbdev e saltato in CI.
--   ⭐ La risalita a due livelli si prova meglio in un altro modo: il test 10
--   interroga direttamente l'adattatore `_via_ddt_riga`, che e' la cosa da
--   verificare. Non serve una riga per chiedere a una funzione se dice il vero.
--
-- ⛔ LA FIXTURE SI COSTRUISCE, non si cerca: due aziende con
--   `dbops.fn_pgtap_crea_emittente_operatore()` e due clienti fatturabili con
--   `dbops.fn_pgtap_crea_cliente_ba()`. Cosi' il file misura la stessa cosa su
--   dbdev e su un database ricostruito dai changelog.
--   ⚠️ Articoli, stati, stili nota e tipi indirizzo si CERCANO, e va bene:
--   stanno in `80_data`, cioe' sono catalogo e ci sono ovunque.
-- ------------------------------------------------------------

BEGIN;

SET CONSTRAINTS ALL IMMEDIATE;

SELECT plan(10);

-- ============================================================
-- I due mondi, e un DDT completo per ciascuno
-- ============================================================
-- ⚠️ `fn_pgtap_crea_emittente_operatore` apre e richiude da sola la finestra
--   dei guard differiti: qui non serve toccarla.
CREATE TEMP TABLE _mondi AS
SELECT 'A' AS lato, * FROM dbops.fn_pgtap_crea_emittente_operatore()
UNION ALL
SELECT 'B' AS lato, * FROM dbops.fn_pgtap_crea_emittente_operatore();

CREATE TEMP TABLE _clienti AS
SELECT m.lato, m.emittente_fiscale_id, c.*
  FROM _mondi m
  -- rev 2026-10-09 (brief-db-esecutivi-ba-coppia): il BA legato all'emittente del
  --   mondo. Il documento porta ora il BA, e il guard emittente <-> BA lo guarda.
  CROSS JOIN LATERAL dbops.fn_pgtap_crea_cliente_ba('RLS ddt ' || m.lato, NULL, m.soggetto_ruolo_id) c;

-- ⚠️ Stato `DRAFT` nominato per `codice_interno`, non preso col primo id: a
--   `EMESSO` scatterebbe `trgfn_ddt_gen_numero_emesso`, che pretende un
--   registro di numerazione per l'emittente — roba che questa slice non ha
--   motivo di costruire.
CREATE TEMP TABLE _ddt AS
WITH d AS (
    -- rev 2026-10-09 (brief-db-esecutivi-ba-coppia): il BA del cliente, non la sola
    --   utility — chk_ddt_ba_utility_insieme vuole tutti e due o nessuno.
    INSERT INTO vendite.ddt
        (destinatario_soggetto_ruolo_id, stato_doc_ddt_id, emittente_fiscale_id, utility_id,
         billing_account_id)
    SELECT c.soggetto_ruolo_id,
           (SELECT st.id FROM config.stati_doc_ddt st WHERE st.codice_interno = 'DRAFT'),
           c.emittente_fiscale_id,
           c.utility_id,
           c.billing_account_id
      FROM _clienti c
    RETURNING id, emittente_fiscale_id
)
SELECT c.lato, d.id AS ddt_id, d.emittente_fiscale_id
  FROM d JOIN _clienti c ON c.emittente_fiscale_id = d.emittente_fiscale_id;

-- ⚠️ `qta_operativa` va valorizzata: `trgfn_qta_from_operativa` ne deriva
--   `quantita`, e il CHECK `k_ddt_righe_qta_operativa_pos` la vuole positiva.
-- 🔴 rev 2026-10-13 (brief-db-articoli-ammessi-per-documento D-1/D-2): l'articolo si
--   COSTRUISCE. Prima si pescava dal catalogo (il primo per id, o il piu' recente):
--   il primo per id e' l'onere del seed ONERE_SENZA_CONTRATTO (natura servizio), e
--   da 20261013-42 ordine e bolla portano solo merce. Un articolo costruito ha solo
--   le proprieta' che il test gli da' (merce, non gestito a magazzino).
CREATE TEMP TABLE _art_fix AS
SELECT dbops.fn_pgtap_crea_articolo('PGT-RLSDS-ART', false) AS id;

CREATE TEMP TABLE _righe AS
WITH r AS (
    INSERT INTO vendite.ddt_righe
        (ddt_id, riga_nr, articolo_id, descrizione, quantita, qta_operativa, prezzo_unitario)
    SELECT d.ddt_id, 1,
           (SELECT id FROM _art_fix),
           'Riga pgTAP RLS', 1, 1, 100.00
      FROM _ddt d
    RETURNING id, ddt_id
)
SELECT d.lato, r.id AS riga_id, r.ddt_id FROM r JOIN _ddt d ON d.ddt_id = r.ddt_id;

-- ⭐ Una nota e un indirizzo per lato: sono le due tabelle la cui chiave NON si
--   chiama `ddt_id`, e sono quindi le due in cui un refuso nella policy non
--   farebbe rumore. `note_ddt` risale da `target_id`.
INSERT INTO vendite.note_ddt
    (target_tipo, target_id, anchor_tipo, posizione, testo, id_stile)
SELECT 'DDT', d.ddt_id, 'DOCUMENTO', 'HEADER', 'Nota pgTAP RLS',
       (SELECT s.id FROM config.note_stili s WHERE s.codice_interno = 'NORMALE')
  FROM _ddt d;

-- ⚠️ Per l'ambito DDT `config.tipi_indirizzi_allowed` ammette il solo `CON`.
INSERT INTO vendite.ddt_indirizzi (ddt_id, tipo_indirizzo_id, snapshot)
SELECT d.ddt_id,
       (SELECT ti.id FROM config.tipi_indirizzi ti WHERE ti.codice_interno = 'CON'),
       '{"pgtap": true}'::jsonb
  FROM _ddt d;

-- ============================================================
-- 1..2. La struttura: policy E armamento
-- ============================================================
SELECT is(
    (SELECT count(*)::int FROM pg_policies
      WHERE schemaname = 'vendite'
        AND tablename IN ('ddt_righe', 'ddt_indirizzi', 'note_ddt',
                          'ddt_righe_componenti')),
    4,
    '1. i quattro satelliti di ddt hanno la loro policy'
);

-- ⛔ Non e' il doppione del test 1: vedi l'intestazione.
SELECT is(
    (SELECT count(*)::int FROM pg_class c
       JOIN pg_namespace n ON n.oid = c.relnamespace AND n.nspname = 'vendite'
      WHERE c.relname IN ('ddt_righe', 'ddt_indirizzi', 'note_ddt',
                          'ddt_righe_componenti')
        AND c.relrowsecurity),
    4,
    '2. e su tutti e quattro la RLS e'' ACCESA, non solo dichiarata'
);

-- ============================================================
-- Il perimetro, esercitato
-- ============================================================
-- FORCE locale alla transazione: senza, l'owner sarebbe esente e il test
-- misurerebbe zero. Il ROLLBACK finale lo annulla.
ALTER TABLE vendite.ddt               FORCE ROW LEVEL SECURITY;
ALTER TABLE vendite.ddt_righe         FORCE ROW LEVEL SECURITY;
ALTER TABLE vendite.ddt_indirizzi     FORCE ROW LEVEL SECURITY;
ALTER TABLE vendite.note_ddt          FORCE ROW LEVEL SECURITY;

DO $perimetro$
DECLARE
    v_a record;
    v_b record;
    v_n integer;
BEGIN
    SELECT d.*, m.auth_user_id INTO v_a
      FROM _ddt d JOIN _mondi m ON m.emittente_fiscale_id = d.emittente_fiscale_id
     WHERE d.lato = 'A';
    SELECT d.* INTO v_b FROM _ddt d WHERE d.lato = 'B';

    -- La veste dell'operatore A, come la darebbe il middleware.
    PERFORM script.fn_pgtap_set_contesto_operatore(v_a.auth_user_id);

    SELECT count(*) INTO v_n FROM vendite.ddt_righe r WHERE r.ddt_id = v_a.ddt_id;
    PERFORM set_config('pgtap.righe_a', v_n::text, true);
    SELECT count(*) INTO v_n FROM vendite.ddt_righe r WHERE r.ddt_id = v_b.ddt_id;
    PERFORM set_config('pgtap.righe_b', v_n::text, true);

    SELECT count(*) INTO v_n FROM vendite.note_ddt n WHERE n.target_id = v_b.ddt_id;
    PERFORM set_config('pgtap.note_b', v_n::text, true);

    SELECT count(*) INTO v_n FROM vendite.ddt_indirizzi i WHERE i.ddt_id = v_b.ddt_id;
    PERFORM set_config('pgtap.indirizzi_b', v_n::text, true);

    -- ⭐ L'INVARIANTE: il satellite non puo' essere piu' permissivo della
    --   testata. Si misura sulle righe che l'operatore vede il cui DDT,
    --   invece, non vede: devono essere ZERO.
    SELECT count(*) INTO v_n
      FROM vendite.ddt_righe r
     WHERE NOT EXISTS (SELECT 1 FROM vendite.ddt d WHERE d.id = r.ddt_id);
    PERFORM set_config('pgtap.orfane', v_n::text, true);

    -- ⚠️ La risalita a DUE livelli, chiesta all'adattatore invece che ai
    --   componenti: e' lui che `ddt_righe_componenti` usa, e la sua risposta non
    --   dipende da quali distinte base la macchina contiene.
    PERFORM set_config('pgtap.riga2',
        script.fn_scope_ef_whitelist_via_ddt_riga(
            v_a.auth_user_id, (SELECT riga_id FROM _righe WHERE lato = 'A'))::text
        || '/' ||
        script.fn_scope_ef_whitelist_via_ddt_riga(
            v_a.auth_user_id, (SELECT riga_id FROM _righe WHERE lato = 'B'))::text,
        true);

    -- ⛔ La scrittura sul DDT altrui: deve fermarla il WITH CHECK, non solo
    --   l'invisibilita' in lettura.
    BEGIN
        INSERT INTO vendite.ddt_righe
            (ddt_id, riga_nr, articolo_id, descrizione, quantita, qta_operativa, prezzo_unitario)
        VALUES (v_b.ddt_id, 99,
                (SELECT id FROM _art_fix),
                'intrusione', 1, 1, 1.00);
        PERFORM set_config('pgtap.scrittura', 'PASSATA', true);
    EXCEPTION WHEN insufficient_privilege OR check_violation THEN
        PERFORM set_config('pgtap.scrittura', 'RIFIUTATA', true);
    END;

    -- ⛔ Nessuna veste: la policy e' permissiva e condizionata alla veste,
    --   quindi non deve vedere NIENTE. Il verso sbagliato — vedere tutto —
    --   sarebbe il difetto peggiore e non farebbe rumore.
    PERFORM set_config('app.ruolo_applicativo', '', true);
    SELECT count(*) INTO v_n
      FROM vendite.ddt_righe r WHERE r.ddt_id IN (v_a.ddt_id, v_b.ddt_id);
    PERFORM set_config('pgtap.senza_veste', v_n::text, true);
END
$perimetro$;

ALTER TABLE vendite.note_ddt          NO FORCE ROW LEVEL SECURITY;
ALTER TABLE vendite.ddt_indirizzi     NO FORCE ROW LEVEL SECURITY;
ALTER TABLE vendite.ddt_righe         NO FORCE ROW LEVEL SECURITY;
ALTER TABLE vendite.ddt               NO FORCE ROW LEVEL SECURITY;

SELECT is(current_setting('pgtap.righe_a', true), '1',
          '3. l''operatore A vede la riga del proprio DDT');

SELECT is(current_setting('pgtap.righe_b', true), '0',
          '4. e NON vede la riga del DDT di un''altra azienda');

SELECT is(current_setting('pgtap.note_b', true), '0',
          '5. nemmeno la NOTA del DDT altrui: la chiave e'' target_id, non ddt_id');

SELECT is(current_setting('pgtap.indirizzi_b', true), '0',
          '6. nemmeno l''INDIRIZZO del DDT altrui');

SELECT is(current_setting('pgtap.scrittura', true), 'RIFIUTATA',
          '7. e non puo'' appendere una riga al DDT altrui (WITH CHECK)');

SELECT is(current_setting('pgtap.senza_veste', true), '0',
          '8. senza veste applicativa non vede niente: fail-closed');

SELECT is(current_setting('pgtap.orfane', true), '0',
          '9. nessuna riga visibile il cui DDT non lo e'': il satellite non e'' piu'' permissivo della testata');

SELECT is(current_setting('pgtap.riga2', true), 'true/false',
          '10. l''adattatore a due livelli risale davvero: vero sulla riga di A, falso su quella di B');

SELECT * FROM finish();

ROLLBACK;
