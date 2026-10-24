-- ------------------------------------------------------------
-- SPDX-License-Identifier: GPL-3.0-or-later
-- pgTAP test per Zero ERP
--
-- Test: i vocabolari dell'erogazione (giri B1 e B2 del brief
--       brief-db-offerta-emissione-ed-erogazione §C.7, changeSet 20261007-50 … -54).
--
--       config.erogazioni_fonti           — le combinazioni coerenti (erogazione, fonte),
--                                           con la fonte di default per erogazione
--       config.listini_tipologie_erogazioni — cosa ammette ogni tipologia, e il default
--       config.nature_vendita_erogazioni   — cosa ammette ogni natura, e il default
--
--       ⭐ Il test 1 fissa il vocabolario alle combinazioni che i CHECK ritirati
--       ammettevano: il giro B1 non cambia il comportamento, lo rende un dato.
--       I test 2, 4, 5 sono la COMPLETEZZA, che un CHECK non sa dire (e' un vincolo
--       fra righe): senza un default, una riga che non indica la fonte resterebbe
--       senza, e la eredita' del giro B3 non avrebbe niente da dare.
--
-- ⚠️ rev 2026-10-21 (brief-db-offerta-emissione-ed-erogazione §I.1, I-D1 di Tid;
--   20261021-51): DERIVATA_COMPONENTI ritirata, il vocabolario scende da 13 a 9
--   combinazioni (test 1). I componenti seguono la quantita' del padre.
--
-- ⚠️ Legge il SEED, non una popolazione: le tre tabelle sono catalogo
--   (80_data/sql/config/*.csv), identiche su ogni macchina.
--
-- Indice test (1..12):
--   1)  config.erogazioni_fonti = le 9 combinazioni (le 13 dei CHECK ritirati, meno DERIVATA_COMPONENTI)
--   2)  ogni erogazione ha esattamente una fonte di default
--   3)  i default sono quelli del CASE ritirato (CANONE/UNA_TANTUM FISSA, ORARIO MANUALE, CONSUMO LETTURE)
--   4)  ogni tipologia di listino attiva ha esattamente un default
--   5)  ogni natura di vendita attiva ha esattamente un default
--   6)  nessuna natura ammette LETTURE (le letture vengono da una tipologia a contatore)
--   7)  QUOTA_FISSA ammette solo CANONE (B-D4: si eroga a periodo, non a letture)
--   8)  ogni combinazione CANONE di tipologie e nature porta la generazione_canone
--   9)  FK sul vocabolario presente su contratti_righe e offerte_commerciali_eccezioni
--   10) i sei CHECK della matrice sono ritirati
--   11) script.trgfn_righe_default_fonte_qta legge il vocabolario e non ricopia la matrice
--   12) tipologie e nature ammettono solo combinazioni del vocabolario (FK composta)
-- ------------------------------------------------------------

BEGIN;
SET CONSTRAINTS ALL IMMEDIATE;
DO $ctx$ BEGIN PERFORM script.fn_pgtap_set_contesto_operatore(); END $ctx$;

SELECT plan(12);

-- 1) Il vocabolario = le combinazioni dei CHECK ritirati (20261007-54)
SELECT set_eq(
    $$ SELECT tipo_erogazione::text, fonte_quantita_attesa::text FROM config.erogazioni_fonti $$,
    $$ VALUES ('CANONE', 'FISSA'), ('CANONE', 'MANUALE'),
              ('UNA_TANTUM', 'FISSA'), ('UNA_TANTUM', 'MANUALE'),
              ('ORARIO', 'FISSA'), ('ORARIO', 'MANUALE'), ('ORARIO', 'TIMESHEET'),
              ('CONSUMO', 'MANUALE'), ('CONSUMO', 'LETTURE') $$,
    '1) config.erogazioni_fonti = le 9 combinazioni (senza DERIVATA_COMPONENTI, ritirata il 2026-10-21)');

-- 2) Completezza del default per erogazione
SELECT is(
    (SELECT count(*)::int FROM (
        SELECT tipo_erogazione FROM config.erogazioni_fonti
         GROUP BY tipo_erogazione
        HAVING count(*) FILTER (WHERE e_default) <> 1) x),
    0,
    '2) ogni erogazione ha esattamente una fonte di default');

-- 3) I default del CASE ritirato
SELECT set_eq(
    $$ SELECT tipo_erogazione::text, fonte_quantita_attesa::text
         FROM config.erogazioni_fonti WHERE e_default $$,
    $$ VALUES ('CANONE', 'FISSA'), ('UNA_TANTUM', 'FISSA'),
              ('ORARIO', 'MANUALE'), ('CONSUMO', 'LETTURE') $$,
    '3) le fonti di default sono quelle del CASE di trgfn_righe_default_fonte_qta');

-- 4) Completezza del default per tipologia
SELECT is(
    (SELECT count(*)::int FROM config.listini_tipologie lt
      WHERE lt.attivo
        AND (SELECT count(*) FROM config.listini_tipologie_erogazioni e
              WHERE e.tipologia_id = lt.id AND e.e_default) <> 1),
    0,
    '4) ogni tipologia di listino attiva ha esattamente un default');

-- 5) Completezza del default per natura
SELECT is(
    (SELECT count(*)::int FROM config.nature_vendita n
      WHERE n.attivo
        AND (SELECT count(*) FROM config.nature_vendita_erogazioni e
              WHERE e.natura_vendita_id = n.id AND e.e_default) <> 1),
    0,
    '5) ogni natura di vendita attiva ha esattamente un default');

-- 6) Nessuna natura ammette LETTURE
SELECT is(
    (SELECT count(*)::int FROM config.nature_vendita_erogazioni
      WHERE fonte_quantita_attesa = 'LETTURE'),
    0,
    '6) nessuna natura di vendita ammette LETTURE');

-- 7) QUOTA_FISSA: solo a periodo (B-D4)
SELECT set_eq(
    $$ SELECT e.tipo_erogazione::text FROM config.listini_tipologie_erogazioni e
         JOIN config.listini_tipologie lt ON lt.id = e.tipologia_id
        WHERE lt.codice = 'QUOTA_FISSA' $$,
    $$ VALUES ('CANONE') $$,
    '7) QUOTA_FISSA ammette solo CANONE: si eroga a periodo, la fonte non sono le letture');

-- 8) Le righe CANONE portano la generazione_canone (il CHECK delle righe la pretende)
SELECT is(
    (SELECT count(*)::int FROM (
        SELECT generazione_canone FROM config.listini_tipologie_erogazioni WHERE tipo_erogazione = 'CANONE'
        UNION ALL
        SELECT generazione_canone FROM config.nature_vendita_erogazioni WHERE tipo_erogazione = 'CANONE') x
      WHERE x.generazione_canone IS NULL),
    0,
    '8) ogni combinazione CANONE di tipologie e nature porta la generazione_canone');

-- 9) La FK sulle due tabelle gemelle
SELECT is(
    (SELECT count(*)::int FROM pg_constraint c
      WHERE c.contype = 'f'
        AND c.confrelid = 'config.erogazioni_fonti'::regclass
        AND c.conrelid IN ('vendite.contratti_righe'::regclass,
                           'vendite.offerte_commerciali_eccezioni'::regclass)),
    2,
    '9) contratti_righe e offerte_commerciali_eccezioni si legano a config.erogazioni_fonti');

-- 10) I CHECK della matrice non ci sono piu'
SELECT is(
    (SELECT count(*)::int FROM pg_constraint c
      WHERE c.conname IN ('chk_contrighe_tipo_erog', 'chk_contrighe_fonte_qta',
                          'chk_contrighe_coerenza_fonte_erogazione',
                          'chk_offerte_eccezioni_tipo_erog', 'chk_offerte_eccezioni_fonte_qta',
                          'chk_offerte_eccezioni_coerenza_fonte_erogazione')),
    0,
    '10) i sei CHECK della matrice sono ritirati: la sede e'' una');

-- 11) Il trigger della fonte legge il vocabolario, non ricopia la matrice.
--     ⚠️ Presidio sul TESTO, commenti tolti: prende la ricopiatura nella forma
--     che c'era (un ramo CASE sull'erogazione che sceglie una fonte).
SELECT ok(
    (SELECT regexp_replace(p.prosrc, '--[^\n]*', '', 'g') ~ 'config\.erogazioni_fonti'
        AND regexp_replace(p.prosrc, '--[^\n]*', '', 'g') !~ 'WHEN\s+''CONSUMO''\s+THEN'
       FROM pg_proc p
      WHERE p.oid = 'script.trgfn_righe_default_fonte_qta()'::regprocedure),
    '11) script.trgfn_righe_default_fonte_qta legge config.erogazioni_fonti e non ricopia la matrice');

-- 12) Ogni combinazione di tipologie e nature e' coerente: lo garantisce la FK
--     composta, qui si controlla che esista davvero su entrambe le tabelle.
SELECT is(
    (SELECT count(*)::int FROM pg_constraint c
      WHERE c.contype = 'f'
        AND c.confrelid = 'config.erogazioni_fonti'::regclass
        AND c.conrelid IN ('config.listini_tipologie_erogazioni'::regclass,
                           'config.nature_vendita_erogazioni'::regclass)),
    2,
    '12) tipologie e nature ammettono solo combinazioni del vocabolario (FK composta)');

SELECT * FROM finish();
ROLLBACK;
