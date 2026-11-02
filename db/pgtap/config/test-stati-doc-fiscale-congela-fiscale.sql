-- ------------------------------------------------------------
-- SPDX-License-Identifier: AGPL-3.0-or-later
-- pgTAP test per Zero ERP
-- Test: config.stati_doc_fiscale.congela_fiscale (I10 / D15)
--       + vendite.fn_ricalcola_riepilogo_iva_fattura che la legge
-- ------------------------------------------------------------
-- Elenco test (plan 7):
-- 0) riferimenti minimi presenti                       (fixture non muta)
-- 1) congela_fiscale e' NOT NULL
-- 2) il DEFAULT e' true                                (fail-closed)
-- 3) il seed: DRAFT ed EMESSA sono i SOLI a false
-- 4) uno stato NUOVO nasce congelato                   (il default in azione)
-- 5) fattura in DRAFT (seed false) -> il ricalcolo e' AMMESSO
-- 6) ⭐ stesso stato portato a true -> il ricalcolo e' RIFIUTATO
--
-- Scopo:
--   Il cantiere I10 promette UNA cosa: la soglia oltre la quale un documento
--   fiscale e' uno snapshot **non e' piu' una lista di codici dentro una
--   funzione, e' un dato**. Prima viveva come
--   `NOT IN ('DRAFT','EMESSA')` nel corpo di
--   vendite.fn_ricalcola_riepilogo_iva_fattura, e il risolutore IVA (I2) avrebbe
--   avuto bisogno della stessa soglia — cioe' l'avrebbe ricopiata.
--
--   ⭐ IL TEST CHE CONTA E' IL 6, e va letto sapendo perche' esiste: prende uno
--   stato che la lista cablata AMMETTEVA (DRAFT), gli mette congela_fiscale a
--   true, e pretende che il ricalcolo si rifiuti. Se qualcuno rimettesse la
--   lista — o affiancasse un secondo guard cablato — il 6 diventerebbe rosso e
--   nient'altro se ne accorgerebbe. Il 5 e' il suo controllo: senza, un rosso
--   del 6 potrebbe venire da una fixture storta invece che dal guard.
--
--   ⚠️ I test 1-2 NON sono burocrazia sullo schema. Il DEFAULT true e' la
--   decisione di merito di D15: uno stato futuro che nessuno classifica deve
--   RIFIUTARE il ricalcolo (errore parlante) invece di lasciar riscrivere in
--   silenzio uno snapshot fiscale. Un `DEFAULT false` sarebbe passato inosservato
--   in review e avrebbe invertito la direzione di sicurezza.
--
--   Piano: brief-db-be-iva-risolutore-e-regime-cliente.md
--     D15 / I10 · changeSet 20260829-03 (colonna + seed) e -04 (funzione)
-- ------------------------------------------------------------

-- ⚠️ 1. TRANSAZIONE: un fallimento a meta' lascerebbe la fixture nel database.
BEGIN;

-- ⚠️ 2. CONTESTO APPLICATIVO: il test gira come gira l'applicazione
--   (ruolo OPERATORE + RLS attiva), non come owner. Senza, le SELECT della
--   fixture leggerebbero zero righe e il file sarebbe verde per sottrazione.
DO $ctx$ BEGIN PERFORM script.fn_pgtap_set_contesto_operatore(); END $ctx$;

-- ⚠️ 3. VINCOLI DIFFERITI: qui il COMMIT non arriva mai (si chiude in ROLLBACK),
--   quindi senza questa riga i DEFERRABLE non verrebbero mai esercitati.
SET CONSTRAINTS ALL IMMEDIATE;

SELECT plan(7);

-- ============================================================
-- 0) Riferimenti
-- ============================================================
-- ⚠️ Emittente e billing account NON si scelgono in modo indipendente: si parte
--   DALLA configurazione (anagrafiche.emittenti_fiscali_utilities) e si sceglie
--   un BA con quella utility. Prendendo «l'emittente piu' recente» e «il BA piu'
--   recente» la coppia risultante puo' non essere configurata. Stesso partito
--   preso di db/pgtap/vendite/test-ricalcola-riepiloghi-iva.sql, dove il difetto
--   fu trovato il 2026-07-28.
-- ⚠️ Ogni LIMIT 1 ha il suo ORDER BY: senza, quale riga esca dipende dal piano
--   del planner e il test passerebbe a giorni alterni.
CREATE TEMP TABLE tmp_cf_costanti AS
SELECT 'pgtap_congela_fiscale'::text AS test_scope;

-- ⛔ LA COPPIA (EMITTENTE, UTILITY) SI COSTRUISCE (2026-09-23). Cercarne una
--   gia' configurata e' lo stesso criterio, ma su un database ricostruito
--   `anagrafiche` e' a zero: la CTE tornava vuota, tutte le colonne
--   uscivano NULL e l'INSERT della fattura moriva su
--   `emittente_soggetto_ruolo_id` NOT NULL — un errore che non nomina ne' la
--   fixture ne' la coppia mancante. Il BB costruisce azienda, operatore e
--   cliente; la riga di configurazione la scrive qui la fixture, perche' e'
--   cio' che un documento fiscale pretende.
-- ⚠️ Tipo documento, stato DRAFT e valuta restano PESCATI: sono seed di
--   `80_data`, ci sono anche da zero — e ognuno ha il suo `ORDER BY`.
CREATE TEMP TABLE tmp_cf_mondo AS
SELECT * FROM dbops.fn_pgtap_crea_mondo_cliente('congela fiscale');

-- ⚠️ `arrotondamento_importi_dec` e `metodo_arrotondamento_importi` sono
--   NOT NULL senza default: la configurazione di una coppia non ha una forma
--   «minima» implicita, la si dichiara. Due decimali HALF_UP e' cio' che
--   portano le righe vive.
INSERT INTO anagrafiche.emittenti_fiscali_utilities
    (emittente_soggetto_ruolo_id, utility_id,
     arrotondamento_importi_dec, metodo_arrotondamento_importi, attivo)
SELECT emittente_soggetto_ruolo_id, utility_id, 2, 'HALF_UP', TRUE FROM tmp_cf_mondo;

CREATE TEMP TABLE tmp_cf_refs AS
SELECT m.emittente_soggetto_ruolo_id,
       m.utility_id,
       m.billing_account_id,
       (SELECT id FROM config.tipi_doc_fiscale
         WHERE attivo IS TRUE ORDER BY id LIMIT 1)   AS tipo_doc_fiscale_id,
       (SELECT id FROM config.stati_doc_fiscale
         WHERE codice_interno = 'DRAFT' ORDER BY id LIMIT 1) AS stato_draft_id,
       (SELECT id FROM config.valute ORDER BY id LIMIT 1)    AS valuta_id
  FROM tmp_cf_mondo m;

SELECT ok(
    (SELECT emittente_soggetto_ruolo_id IS NOT NULL
        AND billing_account_id IS NOT NULL
        AND tipo_doc_fiscale_id IS NOT NULL
        AND stato_draft_id IS NOT NULL
        AND valuta_id IS NOT NULL
       FROM tmp_cf_refs),
    'Riferimenti minimi presenti'
  );

-- ============================================================
-- 1-2) La colonna: NOT NULL e DEFAULT true
-- ============================================================
SELECT col_not_null(
    'config', 'stati_doc_fiscale', 'congela_fiscale',
    'congela_fiscale e'' NOT NULL: uno stato senza risposta non esiste'
  );

-- ⭐ Il DEFAULT e' la decisione di merito di D15, non un dettaglio DDL: uno
--   stato futuro non classificato deve nascere CONGELATO. Si legge da
--   information_schema perche' e'' li'' che vive il default della colonna.
SELECT is(
    (SELECT column_default
       FROM information_schema.columns
      WHERE table_schema = 'config'
        AND table_name   = 'stati_doc_fiscale'
        AND column_name  = 'congela_fiscale'),
    'true',
    'Il DEFAULT e'' true: fail-closed, uno stato non classificato rifiuta il ricalcolo'
  );

-- ============================================================
-- 3) Il seed: DRAFT ed EMESSA sono i SOLI stati che ammettono il ricalcolo
-- ============================================================
-- ⚠️ Si asserisce l'INSIEME, non «DRAFT e' false»: cosi' un settimo stato
--   seminato a false domani fa rosso qui, invece di allargare la finestra di
--   ricalcolo in silenzio.
SELECT set_eq(
    $$SELECT codice_interno FROM config.stati_doc_fiscale WHERE congela_fiscale IS FALSE$$,
    $$VALUES ('DRAFT'), ('EMESSA')$$,
    'Ammettono il ricalcolo SOLO DRAFT ed EMESSA'
  );

-- ============================================================
-- 4) Uno stato NUOVO nasce congelato — il DEFAULT in azione
-- ============================================================
-- ⭐ Non e'' un doppione del test 2: li'' si legge il catalogo, qui si guarda
--   cosa SUCCEDE a una riga scritta da chi non sapeva che la colonna esiste.
--   E'' esattamente il caso che D15 protegge.
-- ⚠️ `chiude_lotto` resta false: un secondo stato con chiude_lotto = true
--   sarebbe respinto dal trigger trg_stati_doc_fiscale_chiude_lotto_guard_iud,
--   e il rosso verrebbe da li'' invece che dal default che si vuole provare.
INSERT INTO config.stati_doc_fiscale
    (codice, descrizione, attivo, ordine, meta, codice_interno,
     applica_lotto, applica_fattura, chiude_lotto, fase, is_abortito)
VALUES
    ('PGTAP_CF', 'Stato di prova congela_fiscale', true, 999, '{}'::jsonb, 'PGTAP_CF',
     false, true, false, 'IN_CORSO', false);

SELECT ok(
    (SELECT congela_fiscale
       FROM config.stati_doc_fiscale
      WHERE codice_interno = 'PGTAP_CF'),
    'Uno stato nuovo, scritto senza nominare la colonna, nasce CONGELATO'
  );

-- ============================================================
-- Fixture: registro + fattura in DRAFT
-- ============================================================
CREATE TEMP TABLE tmp_cf_reg AS
WITH ins AS (
  -- ⛔ emittente_soggetto_ruolo_id e' NOT NULL dal 2026-08-30 (C1-2,
  --   20260830-11), e dev'essere lo STESSO delle fatture di questo file:
  --   vendite.trgfn_fatture_guard_registro_emittente rifiuta un documento
  --   sul registro di un altro emittente (C1-3, 20260830-10).
  INSERT INTO vendite.registri_fatturazione (codice, descrizione, reset_policy, attivo,
         emittente_soggetto_ruolo_id, meta)
  SELECT left('REGCF_' || (SELECT test_scope FROM tmp_cf_costanti), 16),
         'Registro test congela_fiscale',
         'ANNUALE',
         true,
         (SELECT emittente_soggetto_ruolo_id FROM tmp_cf_refs),
         jsonb_build_object('test_scope', (SELECT test_scope FROM tmp_cf_costanti))
  RETURNING id
)
SELECT * FROM ins;

-- ⚠️ La fattura NON ha righe, ed e'' voluto: il ricalcolo produce
--   DELETE 0 / INSERT 0, che basta a distinguere «ammesso» da «rifiutato».
--   Aggiungere righe qui vorrebbe dire collaudare l'aritmetica del riepilogo,
--   che ha gia'' il suo test (vendite/test-ricalcola-riepiloghi-iva.sql).
CREATE TEMP TABLE tmp_cf_fattura AS
WITH ins AS (
  INSERT INTO vendite.fatture (
      registro_id, data, emittente_soggetto_ruolo_id, billing_account_id,
      tipo_doc_fiscale_id, stato_doc_fiscale_id, valuta_id, utility_id, meta)
  SELECT (SELECT id FROM tmp_cf_reg),
         script.fn_data_operativa(),
         (SELECT emittente_soggetto_ruolo_id FROM tmp_cf_refs),
         (SELECT billing_account_id          FROM tmp_cf_refs),
         (SELECT tipo_doc_fiscale_id         FROM tmp_cf_refs),
         (SELECT stato_draft_id              FROM tmp_cf_refs),
         (SELECT valuta_id                   FROM tmp_cf_refs),
         (SELECT utility_id                  FROM tmp_cf_refs),
         jsonb_build_object('test_scope', (SELECT test_scope FROM tmp_cf_costanti))
  RETURNING id
)
SELECT * FROM ins;

-- ============================================================
-- 5) Controllo: con il valore di seed (DRAFT = false) il ricalcolo passa
-- ============================================================
-- ⚠️ Serve, e non e'' ridondante: senza, un rosso del test 6 potrebbe venire da
--   una fixture storta (un permesso, un trigger, un riferimento mancante) invece
--   che dal guard che si vuole provare.
SELECT lives_ok(
    format(
      'SELECT * FROM vendite.fn_ricalcola_riepilogo_iva_fattura(%s)',
      (SELECT id FROM tmp_cf_fattura)
    ),
    'DRAFT ha congela_fiscale = false: il ricalcolo e'' ammesso'
  );

-- ============================================================
-- 6) ⭐ Il test decisivo: la funzione OBBEDISCE AL DATO, non a una lista
-- ============================================================
-- Si porta DRAFT — che la lista cablata AMMETTEVA — a congela_fiscale = true.
-- Con il vecchio `NOT IN ('DRAFT','EMESSA')` questa chiamata passerebbe, e il
-- test sarebbe rosso: e'' precisamente cio'' che deve succedere se qualcuno
-- rimette una soglia cablata qui o in un secondo consumatore.
UPDATE config.stati_doc_fiscale
   SET congela_fiscale = true
 WHERE codice_interno = 'DRAFT';

-- ⚠️ SQLSTATE esplicito: `throws_ok(sql, NULL, NULL, ...)` accetterebbe
--   QUALUNQUE errore, compreso un permesso negato che non c'entra niente.
--   P0001 e'' l'errore di dominio sollevato da script.fn_log_and_raise_error.
SELECT throws_ok(
    format(
      'SELECT * FROM vendite.fn_ricalcola_riepilogo_iva_fattura(%s)',
      (SELECT id FROM tmp_cf_fattura)
    ),
    'P0001',
    NULL,
    'DRAFT portato a congela_fiscale = true: il ricalcolo si RIFIUTA'
  );

SELECT * FROM finish();
ROLLBACK;
