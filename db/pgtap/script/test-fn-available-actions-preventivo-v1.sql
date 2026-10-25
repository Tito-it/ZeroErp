-- ------------------------------------------------------------
-- SPDX-License-Identifier: GPL-3.0-or-later
-- pgTAP test per Zero ERP
-- Test: script.fn_available_actions_preventivo — meta transizioni e filtro manuale
-- ------------------------------------------------------------
-- Indice test (1..8) — rev 04-08-2026 (ACCETTATO→ANNULLATO RIACCESA dal
-- cantiere «vie d'uscita per l'operatore», 20260804-33/34/35; capability
-- push/ordine gated dal residuo):
-- 1) Preventivo inesistente → NULL
-- 2) Preventivo ACCETTATO (una riga di merce) → 'annulla' + 'genera_ordine'
--    (EVASO automatico escluso; push/genera gated dal residuo). Asserito come
--    insieme di chiavi.
-- 3) Preventivo DRAFT, azione ANNULLATO → key='annulla' valorizzato (regressione bug meta={})
-- 4) Preventivo DRAFT, azione ANNULLATO → label_key='vendite.preventivi.azione_annulla' valorizzato
-- 5) Preventivo ACCETTATO senza righe di commessa → can_push_commessa=false, reason NESSUNA_RIGA_COMMESSA
--    (rev 2026-10-08: il preventivo ha sempre il BA — brief-db-istanza-nasce-col-ba R-2 —
--    e il motivo SENZA_BILLING_ACCOUNT non e' piu' raggiungibile)
-- 6) Preventivo DRAFT → 2 azioni manuali (emetti + annulla)
-- 7) Preventivo DRAFT → tutte le azioni hanno key valorizzato (nessun null da meta={})
-- 8) Guard namespace i18n: label_key (da seed) e reason_key (da capability)
--    iniziano per 'vendite.preventivi.' (20260719-14 + seed)
-- rev 2026-10-24 (brief-modello-documento-vendita N-1): i documenti nascono in
--   bozza e si portano avanti con dbops.fn_pgtap_porta_a_stato (prima il
--   preventivo dei test 2-5 nasceva gia' ACCETTATO).
-- rev 2026-10-25 (brief-modello-documento-vendita §8, giro 6): l'emissione
--   chiede almeno una riga attiva, e il preventivo ACCETTATO «senza righe» non
--   e' piu' uno stato ammesso. La riga (una, di merce, 1 x 10) e lo stato li
--   scrive dbops.fn_pgtap_crea_preventivo_con_righe sulla testata del test.
--   ⚠️ ATTESA DEL TEST 2 CAMBIATA: la riga di merce e' residuo d'ordine e
--   accende genera_ordine (gated dal residuo, come dice il test). Il caso
--   «ACCETTATO senza alcun residuo» il modello non lo da' piu': senza residuo
--   il preventivo va in EVASO, e una riga che non sia ne' merce ne' commessa
--   (natura CONTRATTO) il preventivo non la ammette. I test 5 e 8 non
--   cambiano: righe di commessa non ce ne sono.
-- ------------------------------------------------------------

BEGIN;

-- ⚠️ Vincoli DIFFERITI: senza questa riga il test smetterebbe di verificarli.
--   Un trigger DEFERRABLE INITIALLY DEFERRED scatta al COMMIT, e qui il COMMIT
--   non arriva mai (si chiude in ROLLBACK): sarebbero saltati in silenzio, e il
--   file sarebbe verde per sottrazione. IMMEDIATE li riporta a scattare a fine
--   di ogni istruzione. In testa e non in coda: in coda scatterebbero dopo il
--   cleanup, su righe ormai cancellate.
--   Brief: brief-db-pgtap-runner-rls-baseline §19.
SET CONSTRAINTS ALL IMMEDIATE;

-- Contesto applicativo: questo test gira come gira l'applicazione (ruolo
-- OPERATORE + RLS attiva), non come owner. Senza, con FORCE ROW LEVEL
-- SECURITY disattivo l'owner salta la RLS e il test non la esercita mai.
-- Brief: brief-db-pgtap-runner-rls-baseline §8.
DO $ctx$ BEGIN PERFORM script.fn_pgtap_set_contesto_operatore(); END $ctx$;

SELECT plan(8);

-- ============================================================
-- Riferimenti minimi per creare preventivi in pgTAP
--
-- rev 2026-09-23 (brief-db-fixture-che-costruiscono-giro-2, lotto 2).
--   Istanza e utility si PESCAVANO dal primo billing account: su un
--   database ricostruito (la CI) non ce n'e' nessuno, e il file moriva al
--   primo INSERT (istanza_utility_id NULL) con zero asserzioni. Ora il
--   cliente viene da dbops.fn_pgtap_crea_mondo_cliente, che con il
--   contesto gia' aperto riusa l'azienda di chi agisce. Istanza e utility
--   escono dalla STESSA riga (prima erano due sotto-select indipendenti).
--   ⛔ Cio' che il builder scrive si legge in un'istruzione SEPARATA.
-- ============================================================
CREATE TEMP TABLE tmp_mondo_aa AS
SELECT * FROM dbops.fn_pgtap_crea_mondo_cliente('cap preventivo');

CREATE TEMP TABLE tmp_refs_aa AS
SELECT
  (SELECT billing_account_id FROM tmp_mondo_aa) AS billing_account_id,
  (SELECT istanza_utility_id FROM tmp_mondo_aa) AS istanza_utility_id,
  (SELECT utility_id FROM tmp_mondo_aa) AS utility_id,
  (SELECT v.id
     FROM config.valute v
    ORDER BY v.id LIMIT 1
  ) AS valuta_id,
  -- ⛔ L'emittente NON si pesca, si DERIVA (2026-09-23, guida pgTAP §5).
  script.fn_pgtap_emittente_operatore() AS emittente_fiscale_id,
  (SELECT s.id
     FROM config.stati_doc_preventivi s
    WHERE s.codice_interno = 'ACCETTATO' AND s.attivo IS TRUE
    LIMIT 1
  ) AS stato_accettato_id,
  (SELECT s.id
     FROM config.stati_doc_preventivi s
    WHERE s.codice_interno = 'DRAFT' AND s.attivo IS TRUE
    LIMIT 1
  ) AS stato_draft_id;

-- Preventivo ACCETTATO (fixture per test 2-5)
-- ⚠️ rev 2026-10-24 (brief-modello-documento-vendita N-1): nasce DRAFT e va ad
--   ACCETTATO (DRAFT -> EMESSO -> ACCETTATO) sotto i guard veri.
-- ⚠️ rev 2026-10-25 (§8, giro 6): con una riga di merce, scritta in bozza da
--   dbops.fn_pgtap_crea_preventivo_con_righe, che poi porta lo stato: senza
--   righe l'emissione e' rifiutata (E_PREV_NESSUNA_RIGA_ATTIVA).
CREATE TEMP TABLE tmp_prev_aa_accettato AS
WITH ins AS (
  INSERT INTO vendite.preventivi (
    numero, rev, billing_account_id, istanza_utility_id, utility_id,
    validita_dal, validita_al, valuta_id,
    stato_doc_preventivo_id, data, fatturazione_immediata,
    storicizza, meta, emittente_fiscale_id
  )
  SELECT
    'PGTAP-AA-ACCT-' || substr(md5(clock_timestamp()::text), 1, 8),
    0,
    r.billing_account_id, r.istanza_utility_id, r.utility_id,
    DATE '2026-06-01', DATE '2026-06-30', r.valuta_id,
    r.stato_draft_id, DATE '2026-06-01', false,
    false, '{"test_scope":"pgtap_fn_available_actions"}'::jsonb,
    r.emittente_fiscale_id
  FROM tmp_refs_aa r
  RETURNING id
)
SELECT * FROM ins;

DO $porta$ BEGIN
  PERFORM dbops.fn_pgtap_crea_preventivo_con_righe('aa accettato', 'ACCETTATO',
            p_preventivo_id => (SELECT id FROM tmp_prev_aa_accettato));
END $porta$;

-- Preventivo DRAFT (fixture per test 6-7)
CREATE TEMP TABLE tmp_prev_aa_draft AS
WITH ins AS (
  INSERT INTO vendite.preventivi (
    numero, rev, billing_account_id, istanza_utility_id, utility_id,
    validita_dal, validita_al, valuta_id,
    stato_doc_preventivo_id, data, fatturazione_immediata,
    storicizza, meta, emittente_fiscale_id
  )
  SELECT
    'PGTAP-AA-DRF-' || substr(md5(clock_timestamp()::text), 1, 8),
    0,
    r.billing_account_id, r.istanza_utility_id, r.utility_id,
    DATE '2026-06-01', DATE '2026-06-30', r.valuta_id,
    r.stato_draft_id, DATE '2026-06-01', false,
    false, '{"test_scope":"pgtap_fn_available_actions","stato":"draft"}'::jsonb,
    r.emittente_fiscale_id
  FROM tmp_refs_aa r
  RETURNING id
)
SELECT * FROM ins;

-- ============================================================
-- TEST 1) Preventivo inesistente → NULL
-- ============================================================
SELECT is(
  script.fn_available_actions_preventivo(-1),
  NULL,
  'fn_available_actions_preventivo(-1): preventivo inesistente → NULL'
);

-- ============================================================
-- TEST 2) Preventivo ACCETTATO (una riga di merce) → 'annulla' + 'genera_ordine'
--
--   rev 04-08-2026 — ⚠️ ATTESA CAMBIATA, e non e' una regressione.
--   Fino al 2026-08-04 questo test pretendeva **0 azioni**, con la nota
--   «ACCETTATO→ANNULLATO disattivata (22-05: annulla solo da DRAFT)».
--   Il cantiere *vie d'uscita per l'operatore* (`20260804-33/34/35`,
--   applicato alle 13:25) ha **riacceso** la transizione: la riga
--   ACCETTATO→ANNULLATO di `config.transizioni_stati_preventivi` e'
--   tornata `attivo = true`, perche' dare all'operatore una via d'uscita
--   da ACCETTATO e' esattamente lo scopo di quel cantiere.
--   Il test era rimasto indietro rispetto alla decisione.
--
--   Restano escluse: ACCETTATO→EVASO (manuale=false) e push_commessa
--   (gated dal residuo di commessa, che con la sola riga di merce non c'e').
--   rev 2026-10-25 (§8, giro 6): genera_ordine ora c'e' — la riga di merce
--   e' residuo d'ordine. Prima il preventivo era vuoto e l'attesa era
--   ["annulla"]: uno stato che il modello non ammette piu'.
--
--   ⚠️ Si asserisce l'INSIEME delle chiavi, non il conteggio: un
--   `= 1` sarebbe passato anche con l'azione sbagliata, e questo test
--   e' gia' stato scavalcato una volta da un cambio di dominio.
-- ============================================================
SELECT is(
  (SELECT coalesce(
            jsonb_agg(elem->>'key' ORDER BY elem->>'key'),
            '[]'::jsonb
          )
     FROM tmp_prev_aa_accettato p,
          jsonb_array_elements(
            script.fn_available_actions_preventivo(p.id)->'available_actions'
          ) AS elem
  ),
  '["annulla", "genera_ordine"]'::jsonb,
  'fn_available_actions_preventivo ACCETTATO con una riga di merce: ''annulla'' e ''genera_ordine'''
);

-- ============================================================
-- TEST 3) Preventivo DRAFT → azione 'annulla' con key valorizzato
--         Regressione diretta del bug meta={}: la CSV aveva meta vuoto
--         (spostata su DRAFT: da ACCETTATO l'annullo non e' piu' ammesso)
-- ============================================================
SELECT ok(
  (SELECT EXISTS (
     SELECT 1
       FROM tmp_prev_aa_draft p,
            jsonb_array_elements(
              script.fn_available_actions_preventivo(p.id)->'available_actions'
            ) AS elem
      WHERE elem->>'key' = 'annulla'
  )),
  'fn_available_actions_preventivo DRAFT: azione key=''annulla'' presente (regressione meta={})'
);

-- ============================================================
-- TEST 4) Preventivo DRAFT → azione 'annulla' con label_key valorizzato
-- ============================================================
SELECT ok(
  (SELECT EXISTS (
     SELECT 1
       FROM tmp_prev_aa_draft p,
            jsonb_array_elements(
              script.fn_available_actions_preventivo(p.id)->'available_actions'
            ) AS elem
      WHERE elem->>'key' = 'annulla'
        AND elem->>'label_key' = 'vendite.preventivi.azione_annulla'
  )),
  'fn_available_actions_preventivo DRAFT: label_key=''vendite.preventivi.azione_annulla'' valorizzato'
);

-- ============================================================
-- TEST 5) Preventivo ACCETTATO senza righe di commessa (rev 2026-10-25: una
--         riga di merce, prima nessuna riga) →
--         can_push_commessa=false (rev 12-06-2026: capability con
--         residuo + testata) con reason NESSUNA_RIGA_COMMESSA,
--         can_edit_testata=true (dal 2026-10-10: in ACCETTATO note e
--         competenza si cambiano, D-9/D-10), cliente e termine no. I casi positivi (misto, righe
--         eleggibili) sono in test-fn-preventivo-ha-residuo-commessa-v1.
--         ⚠️ rev 2026-10-08 (brief-db-istanza-nasce-col-ba, R-2): fino a quel
--         giorno il preventivo nasceva anche senza BA e il motivo atteso era
--         SENZA_BILLING_ACCOUNT. Ora il BA c'e' sempre: il motivo e' quello
--         delle righe.
-- ============================================================
SELECT ok(
  (SELECT (script.fn_available_actions_preventivo(p.id)->>'can_push_commessa')::boolean IS FALSE
      AND (script.fn_available_actions_preventivo(p.id)->>'can_push_commessa_reason')
          = 'PREVENTIVO_NESSUNA_RIGA_COMMESSA'
      AND (script.fn_available_actions_preventivo(p.id)->>'can_edit_testata')::boolean IS TRUE
      AND (script.fn_available_actions_preventivo(p.id)->'non_editable_fields') @> '["billing_account_id","termine_pagamento_id"]'
     FROM tmp_prev_aa_accettato p
  ),
  'fn_available_actions_preventivo ACCETTATO senza righe di commessa: can_push_commessa=false, reason NESSUNA_RIGA_COMMESSA'
);

-- ============================================================
-- TEST 6) Preventivo DRAFT → 2 azioni manuali (emetti + annulla)
-- ============================================================
SELECT is(
  (SELECT jsonb_array_length(
           script.fn_available_actions_preventivo(p.id)->'available_actions'
         )
     FROM tmp_prev_aa_draft p
  ),
  2,
  'fn_available_actions_preventivo DRAFT: 2 azioni manuali (emetti + annulla)'
);

-- ============================================================
-- TEST 7) Preventivo DRAFT → tutte le azioni hanno key valorizzato
-- ============================================================
SELECT ok(
  (SELECT bool_and(
           (elem->>'key') IS NOT NULL AND (elem->>'key') <> ''
         )
     FROM tmp_prev_aa_draft p,
          jsonb_array_elements(
            script.fn_available_actions_preventivo(p.id)->'available_actions'
          ) AS elem
  ),
  'fn_available_actions_preventivo DRAFT: tutte le azioni hanno key valorizzato (no null da meta={})'
);

-- ============================================================
-- TEST 8) Guard namespace i18n (20260719-14 + seed).
-- La radice `preventivi.*` e' stata spostata sotto `vendite.preventivi.*`
-- dal FE (brief-i18n-radici-uniformi). Una chiave rimasta piatta non da'
-- errore: da' testo mancante. Qui si copre entrambe le sorgenti che il DB
-- emette: la label_key (dal seed transizioni, via DRAFT) e la reason_key
-- (dal corpo della capability, via ACCETTATO senza righe di commessa e, per
-- genera_ordine, via DRAFT — rev 2026-10-25, §8 giro 6).
-- ============================================================
SELECT ok(
  (SELECT bool_and(k LIKE 'vendite.preventivi.%')
     FROM (
       -- label_key da seed (azioni del DRAFT)
       SELECT elem->>'label_key' AS k
         FROM tmp_prev_aa_draft p,
              jsonb_array_elements(
                script.fn_available_actions_preventivo(p.id)->'available_actions'
              ) AS elem
        WHERE elem->>'label_key' IS NOT NULL
       UNION ALL
       -- reason_key da capability (push + genera_ordine, ACCETTATO senza BA)
       SELECT script.fn_available_actions_preventivo(p.id)->>'can_push_commessa_reason_key'
         FROM tmp_prev_aa_accettato p
       UNION ALL
       SELECT script.fn_available_actions_preventivo(p.id)->>'can_genera_ordine_reason_key'
         FROM tmp_prev_aa_accettato p
       UNION ALL
       -- rev 2026-10-25 (§8, giro 6): sull'ACCETTATO con la riga di merce
       --   genera_ordine e' acceso e il suo reason_key e' NULL (il WHERE lo
       --   scarta). Perche' la guardia non perda quella sorgente, il
       --   reason_key di genera_ordine si legge anche dal DRAFT (non_accettato).
       SELECT script.fn_available_actions_preventivo(p.id)->>'can_genera_ordine_reason_key'
         FROM tmp_prev_aa_draft p
     ) q
    WHERE k IS NOT NULL),
  '8) label_key (seed) e reason_key (capability) sotto vendite.preventivi.*'
);

SELECT * FROM finish();
ROLLBACK;
