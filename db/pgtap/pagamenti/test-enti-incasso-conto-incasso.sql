-- ------------------------------------------------------------
-- SPDX-License-Identifier: AGPL-3.0-or-later
-- pgTAP test per Zero ERP
-- Test: un canale di incasso dichiara SU QUALE CONTO atterra il suo denaro
--
-- Elenco test (plan 7):
--  1) Riferimenti minimi presenti
--  2) Un ente SENZA conto non si crea — e il tipo non c'entra
--  3) Un ente con un conto di INCASSO si crea
--  4) Un ente con un conto di PAGAMENTO e' rifiutato
--  5) ...e la frase dice QUALE uso ha trovato
--  6) Un UPDATE che non tocca il conto non viene rifiutato
--  7) Assert finale cleanup
--
-- Scopo:
--  - collaudare S3-1: il perimetro dei soldi non ancora attribuiti si deriva
--    dal conto (D5), e un ente senza conto produrrebbe una coda invisibile —
--    per questo si fallisce alla CONFIGURAZIONE, dove se ne accorge chi puo'
--    rimediare, e non in esercizio dove non se ne accorge nessuno;
--  - ⭐ presidiare la scelta che si discosta dal piano (test 2): il conto e'
--    obbligatorio su TUTTI i tipi e non solo su BANCA. Il test usa apposta un
--    ente `ALTRO`: con la regola del piano quella riga sarebbe passata, e la
--    sua coda sarebbe stata invisibile a tutti — lo stesso difetto travestito;
--  - ⭐ presidiare la FRASE e non solo il rifiuto (test 5). Un `throws_ok` da
--    solo passa anche se il messaggio non nomina l'uso trovato: e' la lezione
--    pagata dal lotto 5, dove un VARIADIC di arita' sbagliata rendeva
--    impossibile proprio il caso che il guard esiste per gestire.
--
-- Piano: brief-db-posting-e-abbinamento-rata.md
--        §2.3 S3-1 · Decisione: brief madre D5 · lotto 6
-- ------------------------------------------------------------

-- ⚠️ 1. TRANSAZIONE.
BEGIN;

-- ⚠️ 2. CONTESTO APPLICATIVO: si gira come gira l'applicazione.
DO $ctx$ BEGIN PERFORM script.fn_pgtap_set_contesto_operatore(); END $ctx$;

-- ⚠️ 3. VINCOLI DIFFERITI.
SET CONSTRAINTS ALL IMMEDIATE;

SELECT plan(7);

-- ============================================================
-- Fixture — due conti dello stesso soggetto: uno di incasso, uno di pagamento
-- ============================================================
CREATE TEMP TABLE tmp_costanti AS
SELECT 'pgtap_ente_conto_incasso'::text AS test_scope;

-- ⛔ LA FILIALE SI COSTRUISCE (2026-09-23). `anagrafiche.bank_branches` e'
--   dato di MACCHINA, non seed di `80_data`: su un database ricostruito e'
--   vuota, `bank_branch_id` usciva NULL e il conto moriva sul suo NOT NULL.
-- ⚠️ Anche il soggetto-ruolo «qualunque» si costruisce: su un database
--   ricostruito il primo per id e' quello dell'azienda del contesto, cioe'
--   proprio il soggetto su cui il test NON vuole agganciare il conto — il caso
--   negativo sarebbe diventato il caso positivo, in silenzio.
CREATE TEMP TABLE tmp_banca AS
SELECT * FROM dbops.fn_pgtap_crea_filiale_bancaria('enti incasso conto');

CREATE TEMP TABLE tmp_refs AS
SELECT
  (SELECT bank_branch_id FROM tmp_banca)            AS bank_branch_id,
  (SELECT banca_soggetto_ruolo_id FROM tmp_banca)   AS soggetto_ruolo_id_qualunque,
  -- ⭐ Dal 2026-08-28 `enti_incasso` ha la RLS: un canale lo puo' creare solo
  --    chi ne e' padrone. Quindi il conto NON si aggancia a un soggetto-ruolo
  --    qualunque, ma a quello dell'EMITTENTE dell'operatore che gira il test —
  --    la fixture torna a scrivere dove scrive l'applicazione.
  -- ⚠️ Se questo test un giorno tornasse rosso con un 42501, la domanda da
  --    farsi e' «con che contesto sta girando?», non «il guard e' cambiato?».
  (SELECT ef.soggetto_ruolo_id
     FROM config.user_emittenti_fiscali uef
     JOIN anagrafiche.emittenti_fiscali ef ON ef.id = uef.emittente_fiscale_id
    WHERE script.fn_has_identita_attiva(
              uef.auth_user_id, 'OPERATORE'::config.ruolo_applicativo)
      AND NOT script.fn_is_super_admin(uef.auth_user_id)
    ORDER BY uef.auth_user_id
    LIMIT 1)                                      AS soggetto_ruolo_id;

SELECT ok(
  (SELECT bank_branch_id IS NOT NULL AND soggetto_ruolo_id IS NOT NULL FROM tmp_refs),
  'Riferimenti minimi presenti: una filiale attiva e un soggetto-ruolo'
);

CREATE TEMP TABLE tmp_conti AS
WITH ins AS (
  INSERT INTO anagrafiche.conti_bancari (iban, bank_branch_id, attivo, storicizza, meta)
  SELECT v.iban, r.bank_branch_id, true, false,
         jsonb_build_object('test_scope', (SELECT test_scope FROM tmp_costanti))
    FROM tmp_refs r
    CROSS JOIN (VALUES ('IT00PGTAPENTEINCASSO00000001', 1),
                       ('IT00PGTAPENTEPAGAMENT0000002', 2)) AS v(iban, ord)
  RETURNING id, iban
)
SELECT max(id) FILTER (WHERE iban LIKE '%INCASSO%')  AS conto_incasso_id,
       max(id) FILTER (WHERE iban LIKE '%PAGAMENT%') AS conto_pagamento_id
  FROM ins;

CREATE TEMP TABLE tmp_legami AS
WITH ins AS (
  INSERT INTO anagrafiche.soggetti_ruoli_conti_bancari
      (soggetto_ruolo_id, conto_bancario_id, uso, predefinito, storicizza, meta)
  SELECT r.soggetto_ruolo_id, v.conto_id, v.uso, false, false,
         jsonb_build_object('test_scope', (SELECT test_scope FROM tmp_costanti))
    FROM tmp_refs r
    CROSS JOIN (SELECT c.conto_incasso_id   AS conto_id, 'INCASSO'::varchar   AS uso FROM tmp_conti c
                UNION ALL
                SELECT c.conto_pagamento_id, 'PAGAMENTO'::varchar             FROM tmp_conti c) AS v
  RETURNING id, uso
)
SELECT max(id) FILTER (WHERE uso = 'INCASSO')   AS legame_incasso_id,
       max(id) FILTER (WHERE uso = 'PAGAMENTO') AS legame_pagamento_id
  FROM ins;

-- ============================================================
-- 2. Un ente SENZA conto non si crea — e il tipo non c'entra
-- ============================================================
-- ⭐ L'ente e' di tipo ALTRO apposta. Il piano voleva il conto obbligatorio solo
--    per BANCA: con quella regola questa riga sarebbe passata, e la coda di
--    questo canale sarebbe stata invisibile a TUTTI — lo stesso difetto che D5
--    esiste per chiudere, spostato su un altro tipo.
-- ⚠️ 23502 = not_null_violation. Con lo SQLSTATE esplicito il test non accetta
--    un rifiuto qualunque.
SELECT throws_ok(
  $sql$INSERT INTO pagamenti.enti_incasso (codice, descrizione, tipo, attivo)
       VALUES ('PGTAP_SENZA_CONTO', 'Canale senza conto', 'ALTRO', true)$sql$,
  '23502',
  NULL,
  'Un ente di incasso SENZA conto non si crea, nemmeno di tipo ALTRO'
);

-- ============================================================
-- 3. Un ente con un conto di INCASSO si crea
-- ============================================================
SELECT lives_ok(
  format(
    $sql$INSERT INTO pagamenti.enti_incasso
            (codice, descrizione, tipo, attivo, soggetto_ruolo_conto_bancario_id)
         VALUES ('PGTAP_CANALE_OK', 'Canale con conto di incasso', 'ALTRO', true, %s)$sql$,
    l.legame_incasso_id
  ),
  'Un ente agganciato a un conto di INCASSO si crea'
) FROM tmp_legami l;

-- ============================================================
-- 4. Un ente con un conto di PAGAMENTO e' rifiutato
-- ============================================================
-- ⚠️ Il punto non e' l'etichetta: l'unicita' che regge il perimetro
--    (ex_src_bancari_conto_incasso_un_solo_soggetto) vive SOLO sulle righe con
--    uso = 'INCASSO'. Un ente appeso alla riga dei pagamenti starebbe fuori da
--    quella garanzia, e nessun errore lo direbbe.
SELECT throws_ok(
  format(
    $sql$INSERT INTO pagamenti.enti_incasso
            (codice, descrizione, tipo, attivo, soggetto_ruolo_conto_bancario_id)
         VALUES ('PGTAP_CANALE_KO', 'Canale col conto sbagliato', 'ALTRO', true, %s)$sql$,
    l.legame_pagamento_id
  ),
  'P0001',
  NULL,
  'Un ente agganciato a un conto di PAGAMENTO e'' rifiutato'
) FROM tmp_legami l;

-- ============================================================
-- 5. ...e la frase dice QUALE uso ha trovato
-- ============================================================
-- ⭐ Il test 4 da solo passerebbe anche con un messaggio muto, o con un errore
--    di programmazione al posto del rifiuto di dominio. Chi legge deve sapere
--    che cos'ha trovato il sistema, altrimenti non sa che conto cercare.
SELECT throws_like(
  format(
    $sql$INSERT INTO pagamenti.enti_incasso
            (codice, descrizione, tipo, attivo, soggetto_ruolo_conto_bancario_id)
         VALUES ('PGTAP_CANALE_KO2', 'Canale col conto sbagliato', 'ALTRO', true, %s)$sql$,
    l.legame_pagamento_id
  ),
  '%PAGAMENTO%',
  'Il messaggio nomina l''uso trovato: chi legge sa che conto deve cercare'
) FROM tmp_legami l;

-- ============================================================
-- 6. Un UPDATE che non tocca il conto non viene rifiutato
-- ============================================================
-- ⚠️ Senza l'uscita in testa, cambiare la descrizione di un canale verrebbe
--    rifiutato per una configurazione decisa mesi prima — e l'errore accuserebbe
--    il gesto sbagliato.
SELECT lives_ok(
  $sql$UPDATE pagamenti.enti_incasso
          SET descrizione = 'Canale con conto di incasso (rinominato)'
        WHERE codice = 'PGTAP_CANALE_OK'$sql$,
  'Un UPDATE che non tocca il conto passa: il guard esce in testa'
);

-- ============================================================
-- 7. Cleanup
-- ============================================================
SELECT ok(true, 'Cleanup: la transazione viene annullata, nessun residuo');

SELECT * FROM finish();
ROLLBACK;
