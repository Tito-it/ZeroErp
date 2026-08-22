-- ------------------------------------------------------------
-- SPDX-License-Identifier: GPL-3.0-or-later
-- pgTAP test per Zero ERP
-- Test: un conto di INCASSO appartiene a UN SOLO soggetto
--
-- Elenco test (plan 6):
--  1) Riferimenti minimi presenti
--  2) Il vincolo esiste, ed e' un'ESCLUSIONE
--  3) Lo stesso conto INCASSO su un SECONDO soggetto e' rifiutato
--  4) ⭐ Lo stesso conto INCASSO sullo STESSO soggetto, a livello di istanza,
--     NON e' rifiutato — il caso che l'indice unico del piano avrebbe vietato
--  5) Con un uso diverso il vincolo non parla: e' parziale
--  6) Assert finale cleanup
--
-- Scopo:
--  - collaudare il pezzo che regge il perimetro degli incassi (S3-2, D5). La
--    regola di dominio — due partite IVA, due conti correnti — era vera nel
--    mondo e ignota al database: appoggiandoci la sicurezza, una riga ambigua
--    diventa un varco silenzioso (due aziende sullo stesso conto, ciascuna vede
--    i soldi dell'altra, e nessun errore da nessuna parte);
--  - ⭐ e presidiare che il vincolo dica ESATTAMENTE la regola, non di piu'
--    (test 4): un indice unico su (conto) WHERE uso = 'INCASSO' avrebbe vietato
--    anche lo stesso conto sullo STESSO soggetto una volta a livello di ruolo e
--    una per istanza utility — configurazione che due indici di questa tabella
--    dichiarano legittima. Un vincolo che vieta piu' della sua regola si scopre
--    il giorno in cui rifiuta qualcosa di giusto.
--
-- Piano: docs/it/dev/work-in-progress/brief-db-posting-e-abbinamento-rata.md
--        §2.3 S3-2 · Decisione: brief madre D5 · lotto 6
-- ------------------------------------------------------------

-- ⚠️ 1. TRANSAZIONE.
BEGIN;

-- ⚠️ 2. CONTESTO APPLICATIVO: si gira come gira l'applicazione.
DO $ctx$ BEGIN PERFORM script.fn_pgtap_set_contesto_operatore(); END $ctx$;

-- ⚠️ 3. VINCOLI DIFFERITI.
SET CONSTRAINTS ALL IMMEDIATE;

SELECT plan(6);

-- ============================================================
-- Fixture — un conto nuovo, due soggetti-ruolo, una istanza utility
-- ============================================================
CREATE TEMP TABLE tmp_costanti AS
SELECT 'pgtap_conto_incasso_unico'::text AS test_scope;

CREATE TEMP TABLE tmp_refs AS
SELECT
  (SELECT b.id FROM anagrafiche.bank_branches b
    WHERE b.attivo IS TRUE ORDER BY b.id LIMIT 1)              AS bank_branch_id,
  (SELECT sr.id FROM anagrafiche.soggetti_ruoli sr
    ORDER BY sr.id LIMIT 1)                                    AS sr_primo,
  (SELECT sr.id FROM anagrafiche.soggetti_ruoli sr
    ORDER BY sr.id OFFSET 1 LIMIT 1)                           AS sr_secondo,
  (SELECT iu.id FROM anagrafiche.istanze_utilities iu
    ORDER BY iu.id LIMIT 1)                                    AS istanza_utility_id;

SELECT ok(
  (SELECT bank_branch_id IS NOT NULL
          AND sr_primo IS NOT NULL
          AND sr_secondo IS NOT NULL
          AND sr_primo <> sr_secondo
          AND istanza_utility_id IS NOT NULL
     FROM tmp_refs),
  'Riferimenti minimi presenti: filiale, due soggetti-ruolo distinti, una istanza utility'
);

-- Il conto su cui si contende.
CREATE TEMP TABLE tmp_conto AS
WITH ins AS (
  INSERT INTO anagrafiche.conti_bancari (iban, bank_branch_id, attivo, storicizza, meta)
  SELECT 'IT00PGTAPINCASSOUNICO0000001', r.bank_branch_id, true, false,
         jsonb_build_object('test_scope', (SELECT test_scope FROM tmp_costanti))
    FROM tmp_refs r
  RETURNING id
)
SELECT id AS conto_id FROM ins;

-- Il legame legittimo: il primo soggetto incassa su quel conto.
INSERT INTO anagrafiche.soggetti_ruoli_conti_bancari
    (soggetto_ruolo_id, conto_bancario_id, uso, predefinito, storicizza, meta)
SELECT r.sr_primo, c.conto_id, 'INCASSO', false, false,
       jsonb_build_object('test_scope', (SELECT test_scope FROM tmp_costanti))
  FROM tmp_refs r CROSS JOIN tmp_conto c;

-- ============================================================
-- 2. Il vincolo esiste, ed e' un'esclusione
-- ============================================================
-- ⚠️ Si asserisce il TIPO, non solo il nome: un indice unico con lo stesso nome
--    passerebbe un controllo di sola esistenza e direbbe una regola diversa.
SELECT is(
  (SELECT con.contype::text
     FROM pg_constraint con
    WHERE con.conrelid = 'anagrafiche.soggetti_ruoli_conti_bancari'::regclass
      AND con.conname = 'ex_src_bancari_conto_incasso_un_solo_soggetto'),
  'x',
  'ex_src_bancari_conto_incasso_un_solo_soggetto esiste ed e'' un vincolo di ESCLUSIONE'
);

-- ============================================================
-- 3. Lo stesso conto INCASSO su un SECONDO soggetto: rifiutato
-- ============================================================
-- ⚠️ SQLSTATE esplicito: 23P01 e' exclusion_violation. Senza, il test
--    accetterebbe qualunque errore — anche il crash di un trigger.
SELECT throws_ok(
  format(
    $sql$INSERT INTO anagrafiche.soggetti_ruoli_conti_bancari
            (soggetto_ruolo_id, conto_bancario_id, uso, predefinito, storicizza)
         VALUES (%s, %s, 'INCASSO', false, false)$sql$,
    r.sr_secondo, c.conto_id
  ),
  '23P01',
  NULL,
  'Lo stesso conto INCASSO su un SECONDO soggetto e'' rifiutato: e'' il varco che D5 chiude'
) FROM tmp_refs r CROSS JOIN tmp_conto c;

-- ============================================================
-- 4. ⭐ Lo STESSO soggetto, a livello di istanza: ACCETTATO
-- ============================================================
-- ⭐ E' il test che distingue il vincolo scritto da quello proposto dal piano.
--    Un unico su (conto_bancario_id) WHERE uso = 'INCASSO' avrebbe rifiutato
--    QUESTA riga — una configurazione che uq_src_bancari_ruolo_conto_uso_no_istanza
--    e uq_src_bancari_ruolo_istanza_conto_uso dichiarano legittima. La regola di
--    dominio nomina DUE colonne: stesso conto E soggetto diverso.
SELECT lives_ok(
  format(
    $sql$INSERT INTO anagrafiche.soggetti_ruoli_conti_bancari
            (soggetto_ruolo_id, conto_bancario_id, uso, predefinito, storicizza,
             istanza_utility_id)
         VALUES (%s, %s, 'INCASSO', false, false, %s)$sql$,
    r.sr_primo, c.conto_id, r.istanza_utility_id
  ),
  'Lo stesso conto INCASSO sullo STESSO soggetto, per una istanza utility, NON e'' rifiutato'
) FROM tmp_refs r CROSS JOIN tmp_conto c;

-- ============================================================
-- 5. Con un uso diverso il vincolo non parla
-- ============================================================
-- Il vincolo e' PARZIALE su uso = 'INCASSO': e' li' che il perimetro si
-- appoggia, e altrove non ha niente da dire.
SELECT lives_ok(
  format(
    $sql$INSERT INTO anagrafiche.soggetti_ruoli_conti_bancari
            (soggetto_ruolo_id, conto_bancario_id, uso, predefinito, storicizza)
         VALUES (%s, %s, 'PAGAMENTO', false, false)$sql$,
    r.sr_secondo, c.conto_id
  ),
  'Lo stesso conto con uso PAGAMENTO su un altro soggetto passa: il vincolo e'' parziale'
) FROM tmp_refs r CROSS JOIN tmp_conto c;

-- ============================================================
-- 6. Cleanup
-- ============================================================
SELECT ok(true, 'Cleanup: la transazione viene annullata, nessun residuo');

SELECT * FROM finish();
ROLLBACK;
