-- ------------------------------------------------------------
-- SPDX-License-Identifier: GPL-3.0-or-later
-- pgTAP test per Zero ERP
-- Test: un conto di INCASSO appartiene a UN SOLO soggetto
--
-- Elenco test (plan 10):
--  1) Riferimenti minimi presenti
--  2) Il vincolo esiste, ed e' un'ESCLUSIONE
--  3) Lo stesso conto INCASSO su un SECONDO soggetto e' rifiutato
--  4) ⭐ Lo stesso conto INCASSO sullo STESSO soggetto, a livello di istanza,
--     NON e' rifiutato — il caso che l'indice unico del piano avrebbe vietato
--  5) Con un uso diverso il vincolo non parla: e' parziale
--  6) ⭐ La SECONDA PORTA: il vincolo gemello a livello SOGGETTO esiste
--  7) Lo stesso conto INCASSO su due SOGGETTI diversi e' rifiutato anche li'
--  8) Con un uso diverso la seconda porta tace: e' parziale come la prima
--  9) ⭐ Lo stesso conto sullo stesso soggetto NON e' rifiutato dall'esclusione
-- 10) Assert finale cleanup
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
--  - ⭐ **dal 2026-08-25 le porte sono DUE** (test 6-9). Un conto entra da
--    `soggetti_ruoli_conti_bancari` (ruolo) e da `soggetti_conti_bancari`
--    (soggetto), e fino a quel giorno la regola era scritta solo sulla prima:
--    lo stesso IBAN poteva essere dichiarato di incasso per due aziende
--    diverse dalla seconda, senza che niente lo impedisse. Una garanzia che
--    regge su una porta sola non e' una garanzia: e' una convenzione che
--    nessuno ha ancora infranto.
--
-- Piano: brief-db-posting-e-abbinamento-rata.md
--        §2.3 S3-2 (lotto 6) · §3-bis e §6.16 la seconda porta (lotto 9)
--        Decisione: brief madre D5 · la seconda porta: Tid, 2026-08-25
-- ------------------------------------------------------------

-- ⚠️ 1. TRANSAZIONE.
BEGIN;

-- ⚠️ 2. CONTESTO APPLICATIVO: si gira come gira l'applicazione.
DO $ctx$ BEGIN PERFORM script.fn_pgtap_set_contesto_operatore(); END $ctx$;

-- ⚠️ 3. VINCOLI DIFFERITI.
SET CONSTRAINTS ALL IMMEDIATE;

SELECT plan(10);

-- ============================================================
-- Fixture — un conto nuovo, due soggetti-ruolo, una istanza utility
-- ============================================================
CREATE TEMP TABLE tmp_costanti AS
SELECT 'pgtap_conto_incasso_unico'::text AS test_scope;

-- ⚠️ rev 2026-10-19 (R-BE-15, brief-db-processi-accensione-per-ambiente
--   §6.17.2): i riferimenti si COSTRUISCONO. Prima si pescavano «il primo
--   ruolo» e «la prima istanza» del database, senza legame fra loro: il test 4
--   metteva sul ruolo di un soggetto l'istanza di un altro, cioe' proprio la riga
--   che il guard trgfn_guard_istanza_del_ruolo (20261019-82) ora rifiuta con
--   E_ISTANZA_ALTRO_SOGGETTO. E su un database ricostruito (la CI) la pesca era
--   vuota: il test moriva al primo. Ora due clienti, A e B (soggetti distinti,
--   ognuno col ruolo e la sua istanza), da dbops.fn_pgtap_crea_cliente_ba, e la
--   filiale da dbops.fn_pgtap_crea_filiale_bancaria. L'istanza del test 4 e'
--   quella di A, il soggetto del primo ruolo.
--   ⛔ Cio' che i builder scrivono si legge in un'istruzione SEPARATA.
CREATE TEMP TABLE tmp_cli AS
SELECT 'A' AS lato, c.* FROM dbops.fn_pgtap_crea_cliente_ba('conto incasso unico A') c
UNION ALL
SELECT 'B' AS lato, c.* FROM dbops.fn_pgtap_crea_cliente_ba('conto incasso unico B') c;

CREATE TEMP TABLE tmp_bb AS
SELECT bank_branch_id FROM dbops.fn_pgtap_crea_filiale_bancaria('conto incasso unico');

CREATE TEMP TABLE tmp_refs AS
SELECT
  (SELECT bank_branch_id FROM tmp_bb)                          AS bank_branch_id,
  a.soggetto_ruolo_id                                          AS sr_primo,
  b.soggetto_ruolo_id                                          AS sr_secondo,
  a.istanza_utility_id                                         AS istanza_utility_id,
  -- ⚠️ Per la seconda porta servono due SOGGETTI distinti, non due ruoli: il
  --    vincolo gemello nomina il soggetto. I due clienti li danno per
  --    costruzione.
  a.soggetto_id                                                AS sogg_primo,
  b.soggetto_id                                                AS sogg_secondo
  FROM tmp_cli a, tmp_cli b
 WHERE a.lato = 'A' AND b.lato = 'B';

SELECT ok(
  (SELECT bank_branch_id IS NOT NULL
          AND sr_primo IS NOT NULL
          AND sr_secondo IS NOT NULL
          AND sr_primo <> sr_secondo
          AND istanza_utility_id IS NOT NULL
          AND sogg_primo IS NOT NULL
          AND sogg_secondo IS NOT NULL
          AND sogg_primo <> sogg_secondo
     FROM tmp_refs),
  'Riferimenti minimi presenti: filiale, due ruoli e due SOGGETTI distinti, una istanza utility'
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
-- 6-9. ⭐ LA SECONDA PORTA — `anagrafiche.soggetti_conti_bancari`
-- ============================================================
-- 🔴 Un conto entra da DUE porte, e fino al 2026-08-25 la regola era scritta
--    su una sola: dalla seconda lo stesso IBAN poteva essere dichiarato di
--    incasso per due aziende diverse. I quattro test qui sotto sono gli stessi
--    2, 3, 5 e 4 di sopra, ripetuti sull'altra porta — perche' una garanzia
--    vale quanto la porta piu' debole.
SELECT is(
  (SELECT con.contype::text
     FROM pg_constraint con
    WHERE con.conrelid = 'anagrafiche.soggetti_conti_bancari'::regclass
      AND con.conname = 'ex_scb_conto_incasso_un_solo_soggetto'),
  'x',
  'ex_scb_conto_incasso_un_solo_soggetto esiste ed e'' un vincolo di ESCLUSIONE'
);

-- Il legame legittimo sulla seconda porta: il primo soggetto incassa li'.
INSERT INTO anagrafiche.soggetti_conti_bancari
    (soggetto_id, conto_bancario_id, uso, predefinito, verificato, bloccato,
     storicizza, meta)
SELECT r.sogg_primo, c.conto_id, 'INCASSO', false, false, false, false,
       jsonb_build_object('test_scope', (SELECT test_scope FROM tmp_costanti))
  FROM tmp_refs r CROSS JOIN tmp_conto c;

SELECT throws_ok(
  format(
    $sql$INSERT INTO anagrafiche.soggetti_conti_bancari
            (soggetto_id, conto_bancario_id, uso, predefinito, verificato,
             bloccato, storicizza)
         VALUES (%L, %s, 'INCASSO', false, false, false, false)$sql$,
    r.sogg_secondo, c.conto_id
  ),
  '23P01',
  NULL,
  'Lo stesso conto INCASSO su un SECONDO soggetto e'' rifiutato anche dalla porta del soggetto'
) FROM tmp_refs r CROSS JOIN tmp_conto c;

SELECT lives_ok(
  format(
    $sql$INSERT INTO anagrafiche.soggetti_conti_bancari
            (soggetto_id, conto_bancario_id, uso, predefinito, verificato,
             bloccato, storicizza)
         VALUES (%L, %s, 'PAGAMENTO', false, false, false, false)$sql$,
    r.sogg_secondo, c.conto_id
  ),
  'Sulla seconda porta un uso diverso passa: il vincolo e'' parziale come il gemello'
) FROM tmp_refs r CROSS JOIN tmp_conto c;

-- ⭐ E non e' piu' stretto della sua regola: il doppione sullo STESSO soggetto
--    lo rifiuta l'UNIQUE (23505), non l'esclusione. Se rispondesse 23P01, il
--    vincolo vieterebbe piu' di cio' che il dominio dice.
SELECT throws_ok(
  format(
    $sql$INSERT INTO anagrafiche.soggetti_conti_bancari
            (soggetto_id, conto_bancario_id, uso, predefinito, verificato,
             bloccato, storicizza)
         VALUES (%L, %s, 'INCASSO', false, false, false, false)$sql$,
    r.sogg_primo, c.conto_id
  ),
  '23505',
  NULL,
  'Il doppione sullo STESSO soggetto lo ferma l''UNIQUE, non l''esclusione: la regola non e'' allargata'
) FROM tmp_refs r CROSS JOIN tmp_conto c;

-- ============================================================
-- 10. Cleanup
-- ============================================================
SELECT ok(true, 'Cleanup: la transazione viene annullata, nessun residuo');

SELECT * FROM finish();
ROLLBACK;
