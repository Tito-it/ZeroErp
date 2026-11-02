-- ------------------------------------------------------------
-- SPDX-License-Identifier: AGPL-3.0-or-later
-- pgTAP test per Zero ERP
-- Test: la CANCELLAZIONE di un atto di fondo fattura, e lo stato di NASCITA
--
-- rev 2026-10-24 (brief-modello-documento-vendita N-1): sorgente e figlia
--   congelata nascono in bozza e si portano avanti con
--   dbops.fn_pgtap_porta_a_stato (prima nascevano gia' DEFINITIVA).
-- rev 2026-10-24 (brief-modello-documento-vendita Q-4): cliente, azienda e
--   registro li costruisce dbops.fn_pgtap_crea_mondo_cliente (+
--   script.fn_pgtap_registro_fattura) invece di pescare il primo billing
--   account, che su un database ricostruito non c'e'. Il contesto si apre
--   DOPO, sull'operatore del mondo.
-- rev 2026-10-24 (brief-modello-documento-vendita R-5): le tre fatture le
--   scrive dbops.fn_pgtap_crea_fattura sul cliente del mondo, con minimo e
--   totale alla nascita e lo stato per la matrice; niente piu' INSERT a mano,
--   snapshot in LATERAL e porta_a_stato nel file.
--
-- Elenco test (plan 14):
--  1) Riferimenti minimi presenti
--  2) D-22: un atto non puo' NASCERE gia' ANNULLATO
--  3) D-22: un atto non puo' NASCERE gia' ESEGUITO
--  4) D-22: la nascita DISPONIBILE passa — e' il giro automatico
--  5) ⭐ D-22: la nascita ASSEGNATO passa — il riporto e' il caso da AMMETTERE
--  6) Il predicato dice «si puo'» su un atto la cui figlia e' ancora lavorabile
--  7) La cancellazione toglie l'atto...
--  8) ...e toglie il fondo applicato alla figlia
--  9) ⭐ FIGLIA_CONGELATA: il predicato lo dice quando la figlia e' DEFINITIVA
-- 10) ...e la cancellazione RIFIUTA, con lo SQLSTATE del dominio
-- 11) ⭐ Il bypass di manutenzione spegne la SOLA quarta condizione
-- 12) ATTO_NON_TROVATO: il predicato lo dice su un id che non esiste
-- 13) ...e la cancellazione rifiuta anche li'
-- 14) Assert finale cleanup
--
-- Scopo:
--  - ⭐ il test 5 e' il piu' importante e il meno ovvio: il guard di nascita e'
--    scritto DOPO che il riporto esiste, e il riporto nasce ASSEGNATO. Un guard
--    scritto sulla sola matrice di D-7 — che descriveva la nascita come
--    DISPONIBILE — avrebbe rotto il processo rimborsi. Qui il caso da ammettere
--    e' provato dal lato POSITIVO, non dedotto dall'assenza di un rosso;
--  - ⭐ il test 9 e' il CASO NUOVO del cantiere (G-3), e va COSTRUITO: sui dati
--    di oggi nessun fondo e' assegnato a una fattura congelata, quindi un test
--    che iterasse sulla popolazione passerebbe a vuoto — e passerebbe a vuoto
--    anche in CI, su un database ricostruito da zero;
--  - ⭐ il test 11 presidia la frase «il gesto di una persona e la pulizia di un
--    lotto non sono la stessa porta»: e' la GUC a distinguerle, e se un giorno
--    il bypass spegnesse anche i tre blocchi che parlano di DENARO, un reset
--    cancellerebbe un trasferimento gia' registrato.
--
-- ⛔ UN RAMO DICHIARATO SCOPERTO, e non nascosto fra i verdi. Il predicato
--    distingue la figlia CHE NON SI LEGGE (cancellata, o invisibile sotto la
--    row security) — dove risponde FIGLIA_CONGELATA — dalla figlia che si legge
--    e non ha stato, dove non blocca. Qui si prova solo il secondo caso: il
--    primo pretenderebbe un atto che punta una fattura irraggiungibile, e la FK
--    `fk_fondi_source_fattura_figlia` non lascia costruirlo. La prova di
--    mutazione lo conferma — rendendo quel ramo fail-open nessun test cade.
--    Si chiude quando esistera' una fixture a due emittenti su questo file,
--    come quella di db/pgtap/rls/test-rls-fondi-fattura-source-functional.sql.
--
-- Piano: brief-db-fondo-fattura-ricalcolo-e-governo.md
--        §9.3 D-21/D-22/D-24 · §9.5-a · §9.7 · changeSet 20260831-61/-63/-64/-65
-- ------------------------------------------------------------

-- ⚠️ 1. TRANSAZIONE.
BEGIN;

-- ⚠️ 2. CONTESTO APPLICATIVO: questo test gira come gira l'applicazione
--   (OPERATORE + RLS attiva), non come owner. Dal changeSet 20260831-62 la
--   tabella degli atti ha le sue policy, e la fixture le attraversa.
--   Il mondo (azienda, operatore, cliente) si costruisce PRIMA, e il contesto
--   si apre sul suo operatore.
CREATE TEMP TABLE tmp_mondo AS
SELECT * FROM dbops.fn_pgtap_crea_mondo_cliente('fondo_cancellazione');

DO $ctx$ BEGIN PERFORM script.fn_pgtap_set_contesto_operatore((SELECT auth_user_id FROM tmp_mondo)); END $ctx$;

-- ⚠️ 3. VINCOLI DIFFERITI: senza, non verrebbero mai esercitati (si chiude in
--   ROLLBACK) e il file sarebbe verde per sottrazione.
SET CONSTRAINTS ALL IMMEDIATE;

SELECT plan(14);

-- ============================================================
-- Fixture — una sorgente e DUE figlie: una lavorabile, una congelata
-- ============================================================
CREATE TEMP TABLE tmp_costanti AS
SELECT 'pgtap_fondo_cancellazione'::text AS test_scope;

-- I riferimenti del documento sono quelli del mondo: il registro e' quello
-- della sua azienda (lo crea se non c'e').
CREATE TEMP TABLE tmp_refs AS
SELECT script.fn_pgtap_registro_fattura(m.emittente_soggetto_ruolo_id)              AS registro_id,
       m.billing_account_id,
       m.utility_id,
       (SELECT id FROM config.tipi_doc_fiscale WHERE attivo IS TRUE ORDER BY id LIMIT 1) AS tipo_doc_fiscale_id,
       (SELECT id FROM config.valute ORDER BY id LIMIT 1)                           AS valuta_id,
       m.emittente_soggetto_ruolo_id,
       (SELECT t.id FROM vendite.tipi_fondi_fattura t
         WHERE t.attivo IS TRUE AND t.codice_interno = 'F_F_ADD_ACC'
         ORDER BY t.id LIMIT 1)                                                     AS tipo_fondo_id,
       (SELECT s.id FROM config.stati_doc_fiscale s
         WHERE s.codice_interno = 'DEFINITIVA' AND s.attivo IS TRUE ORDER BY s.id LIMIT 1) AS stato_definitiva_id,
       (SELECT s.id FROM config.stati_doc_fiscale s
         WHERE s.codice_interno = 'DRAFT' AND s.attivo IS TRUE ORDER BY s.id LIMIT 1)      AS stato_draft_id
  FROM tmp_mondo m;

SELECT ok(
  (SELECT registro_id IS NOT NULL
      AND billing_account_id IS NOT NULL
      AND utility_id IS NOT NULL
      AND tipo_doc_fiscale_id IS NOT NULL
      AND valuta_id IS NOT NULL
      AND emittente_soggetto_ruolo_id IS NOT NULL
      AND tipo_fondo_id IS NOT NULL
      AND stato_definitiva_id IS NOT NULL
      AND stato_draft_id IS NOT NULL
     FROM tmp_refs)
  -- ⚠️ La soglia e' un DATO, non una lista: se un giorno DEFINITIVA smettesse
  --   di congelare, i test 9 e 10 diventerebbero verdi per il motivo sbagliato.
  AND (SELECT s.congela_fiscale FROM config.stati_doc_fiscale s
        WHERE s.id = (SELECT stato_definitiva_id FROM tmp_refs))
  AND NOT (SELECT s.congela_fiscale FROM config.stati_doc_fiscale s
            WHERE s.id = (SELECT stato_draft_id FROM tmp_refs)),
  '1) Riferimenti minimi presenti, e la soglia congela_fiscale dice cio'' che il test assume'
);

-- ⭐ Le tre fatture le scrive il builder (rev 2026-10-24, R-5): cliente del
--   mondo (terzo parametro), minimo e totale alla NASCITA, e fuori bozza
--   indirizzi, intestazione e matrice, sotto i guard veri. Un builder per
--   istruzione: le tabelle si leggono dopo.

-- La fattura SORGENTE del fondo: definitiva, di minimo, totale 100.
CREATE TEMP TABLE tmp_src AS
SELECT f.fattura_id AS id
  FROM dbops.fn_pgtap_crea_fattura(
         'fondo_cancellazione', 'DEFINITIVA', (SELECT billing_account_id FROM tmp_refs),
         false, false, p_minimo => true, p_totale_a_pagare => 100.00) f;

-- La figlia ANCORA LAVORABILE: DRAFT, quindi i suoi satelliti si toccano.
CREATE TEMP TABLE tmp_figlia_ok AS
SELECT f.fattura_id AS id
  FROM dbops.fn_pgtap_crea_fattura(
         'fondo_cancellazione', 'DRAFT', (SELECT billing_account_id FROM tmp_refs),
         false, false, p_minimo => false, p_totale_a_pagare => 200.00) f;

-- ⭐ La figlia CONGELATA: e' il caso nuovo di G-3, e sui dati di oggi non
--   esiste. Si COSTRUISCE, o il test 9 passerebbe a vuoto.
CREATE TEMP TABLE tmp_figlia_ko AS
SELECT f.fattura_id AS id
  FROM dbops.fn_pgtap_crea_fattura(
         'fondo_cancellazione', 'DEFINITIVA', (SELECT billing_account_id FROM tmp_refs),
         false, false, p_minimo => false, p_totale_a_pagare => 300.00) f;

-- ============================================================
-- D-22 — LO STATO DI NASCITA
-- ============================================================
-- ⚠️ throws_ok SEMPRE con lo SQLSTATE: senza, accetterebbe qualunque errore —
--   compreso un errore di sintassi della fixture.
SELECT throws_ok(
  format($sql$
    INSERT INTO vendite.fatture_fondi_fattura_source (
        fattura_sorgente_id, tipo_fondo_fattura_id, importo, stato,
        billing_account_id, utility_id, tipo_doc_fiscale_id,
        emittente_soggetto_ruolo_id, valuta_id, origine, motivo)
    VALUES (%s, %s, 10.00, 'ANNULLATO', %s, %s, %s, %s, %s, 'MANUALE', 'nascita vietata')
  $sql$,
  (SELECT id FROM tmp_src), (SELECT tipo_fondo_id FROM tmp_refs),
  (SELECT billing_account_id FROM tmp_refs), (SELECT utility_id FROM tmp_refs),
  (SELECT tipo_doc_fiscale_id FROM tmp_refs), (SELECT emittente_soggetto_ruolo_id FROM tmp_refs),
  (SELECT valuta_id FROM tmp_refs)),
  'P0001', NULL,
  '2) D-22: un atto non puo'' nascere gia'' ANNULLATO'
);

SELECT throws_ok(
  format($sql$
    INSERT INTO vendite.fatture_fondi_fattura_source (
        fattura_sorgente_id, tipo_fondo_fattura_id, importo, stato,
        billing_account_id, utility_id, tipo_doc_fiscale_id,
        emittente_soggetto_ruolo_id, valuta_id, origine, motivo)
    VALUES (%s, %s, 10.00, 'ESEGUITO', %s, %s, %s, %s, %s, 'MANUALE', 'nascita vietata')
  $sql$,
  (SELECT id FROM tmp_src), (SELECT tipo_fondo_id FROM tmp_refs),
  (SELECT billing_account_id FROM tmp_refs), (SELECT utility_id FROM tmp_refs),
  (SELECT tipo_doc_fiscale_id FROM tmp_refs), (SELECT emittente_soggetto_ruolo_id FROM tmp_refs),
  (SELECT valuta_id FROM tmp_refs)),
  'P0001', NULL,
  '3) D-22: un atto non puo'' nascere gia'' ESEGUITO'
);

-- ⭐ I DUE STATI AMMESSI, provati dal lato POSITIVO. Un guard si verifica dal
--   percorso che lo attraversa: «non ha dato errore» non e' un'asserzione.
CREATE TEMP TABLE tmp_atto_disp AS
WITH ins AS (
  INSERT INTO vendite.fatture_fondi_fattura_source (
      fattura_sorgente_id, tipo_fondo_fattura_id, importo, stato,
      billing_account_id, utility_id, tipo_doc_fiscale_id,
      emittente_soggetto_ruolo_id, valuta_id, origine, motivo)
  SELECT (SELECT id FROM tmp_src), r.tipo_fondo_id, 10.00, 'DISPONIBILE',
         r.billing_account_id, r.utility_id, r.tipo_doc_fiscale_id,
         r.emittente_soggetto_ruolo_id, r.valuta_id, 'MANUALE', 'nascita disponibile'
    FROM tmp_refs r
  RETURNING id
)
SELECT id AS source_id FROM ins;

SELECT is(
  (SELECT s.stato FROM vendite.fatture_fondi_fattura_source s
    WHERE s.id = (SELECT source_id FROM tmp_atto_disp))::text,
  'DISPONIBILE',
  '4) D-22: la nascita DISPONIBILE passa — e'' il giro automatico'
);

-- ⭐ IL CASO CHE IL GUARD DEVE AMMETTERE, non bloccare: il riporto nasce
--   ASSEGNATO perche' nomina gia' la fattura di destinazione.
CREATE TEMP TABLE tmp_atto_ok AS
WITH ins AS (
  INSERT INTO vendite.fatture_fondi_fattura_source (
      fattura_sorgente_id, tipo_fondo_fattura_id, importo, stato,
      fattura_figlia_id, data_assegnazione, user_assegnazione,
      billing_account_id, utility_id, tipo_doc_fiscale_id,
      emittente_soggetto_ruolo_id, valuta_id, origine, motivo)
  SELECT (SELECT id FROM tmp_src), r.tipo_fondo_id, 20.00, 'ASSEGNATO',
         (SELECT id FROM tmp_figlia_ok), now(), current_user,
         r.billing_account_id, r.utility_id, r.tipo_doc_fiscale_id,
         r.emittente_soggetto_ruolo_id, r.valuta_id, 'MANUALE', 'riporto di prova'
    FROM tmp_refs r
  RETURNING id
)
SELECT id AS source_id FROM ins;

SELECT is(
  (SELECT s.stato FROM vendite.fatture_fondi_fattura_source s
    WHERE s.id = (SELECT source_id FROM tmp_atto_ok))::text,
  'ASSEGNATO',
  '5) ⭐ D-22: la nascita ASSEGNATO passa — il riporto e'' il caso da ammettere'
);

-- Il fondo APPLICATO alla figlia, che la cancellazione deve portarsi via.
INSERT INTO vendite.fatture_fondi_fattura
    (fattura_id, riferimento_fattura_id, tipo_fondo_fattura_id, importo, meta)
SELECT (SELECT id FROM tmp_figlia_ok), (SELECT id FROM tmp_src),
       (SELECT tipo_fondo_id FROM tmp_refs), 20.00,
       jsonb_build_object('test_scope', (SELECT test_scope FROM tmp_costanti));

-- ============================================================
-- D-21 — IL PREDICATO E LA CANCELLAZIONE
-- ============================================================
SELECT is(
  vendite.fn_check_fondo_cancellabile((SELECT source_id FROM tmp_atto_ok)),
  NULL::text,
  '6) Il predicato dice «si puo''» su un atto la cui figlia e'' ancora lavorabile'
);

-- ⚠️ Il VERBO in un'istruzione SEPARATA dall'asserzione: nella stessa, la
--   snapshot di statement leggerebbe PRIMA della scrittura e il test
--   accuserebbe la funzione invece di se stesso.
SELECT * FROM vendite.fn_cancella_fondo_fattura((SELECT source_id FROM tmp_atto_ok));

SELECT ok(
  NOT EXISTS (SELECT 1 FROM vendite.fatture_fondi_fattura_source s
               WHERE s.id = (SELECT source_id FROM tmp_atto_ok)),
  '7) La cancellazione toglie l''atto'
);

SELECT ok(
  NOT EXISTS (SELECT 1 FROM vendite.fatture_fondi_fattura ff
               WHERE ff.fattura_id = (SELECT id FROM tmp_figlia_ok)
                 AND ff.riferimento_fattura_id = (SELECT id FROM tmp_src)),
  '8) ...e toglie il fondo applicato alla figlia'
);

-- ============================================================
-- G-3 — LA FIGLIA CONGELATA, il caso NUOVO e COSTRUITO
-- ============================================================
CREATE TEMP TABLE tmp_atto_ko AS
WITH ins AS (
  INSERT INTO vendite.fatture_fondi_fattura_source (
      fattura_sorgente_id, tipo_fondo_fattura_id, importo, stato,
      fattura_figlia_id, data_assegnazione, user_assegnazione,
      billing_account_id, utility_id, tipo_doc_fiscale_id,
      emittente_soggetto_ruolo_id, valuta_id, origine, motivo)
  SELECT (SELECT id FROM tmp_src), r.tipo_fondo_id, 30.00, 'ASSEGNATO',
         (SELECT id FROM tmp_figlia_ko), now(), current_user,
         r.billing_account_id, r.utility_id, r.tipo_doc_fiscale_id,
         r.emittente_soggetto_ruolo_id, r.valuta_id, 'MANUALE', 'riporto su figlia congelata'
    FROM tmp_refs r
  RETURNING id
)
SELECT id AS source_id FROM ins;

SELECT is(
  vendite.fn_check_fondo_cancellabile((SELECT source_id FROM tmp_atto_ko)),
  'FIGLIA_CONGELATA',
  '9) ⭐ Il predicato dice FIGLIA_CONGELATA quando la figlia e'' DEFINITIVA'
);

SELECT throws_ok(
  format($sql$SELECT * FROM vendite.fn_cancella_fondo_fattura(%s)$sql$,
         (SELECT source_id FROM tmp_atto_ko)),
  'P0001', NULL,
  '10) ...e la cancellazione RIFIUTA, con lo SQLSTATE del dominio'
);

-- ============================================================
-- ⭐ IL BYPASS DI MANUTENZIONE — due porte, non una
-- ============================================================
-- La GUC spegne la SOLA quarta condizione: e' quello che rende il reset di un
-- lotto una cosa diversa dal gesto di una persona. ⚠️ `true` = locale alla
-- transazione, cosi' non contamina il resto della sessione.
SELECT set_config('zeroerp.maintenance_reset_lotto_draft', 'on', true);

SELECT is(
  vendite.fn_check_fondo_cancellabile((SELECT source_id FROM tmp_atto_ko)),
  NULL::text,
  '11) ⭐ Il bypass di manutenzione spegne la SOLA quarta condizione'
);

SELECT set_config('zeroerp.maintenance_reset_lotto_draft', 'off', true);

-- ============================================================
-- ATTO_NON_TROVATO — «non esiste» e «non e' tuo», indistinguibili
-- ============================================================
-- Un id sicuramente libero: il massimo esistente piu' uno.
CREATE TEMP TABLE tmp_id_libero AS
SELECT COALESCE(max(s.id), 0) + 1000 AS source_id
  FROM vendite.fatture_fondi_fattura_source s;

SELECT is(
  vendite.fn_check_fondo_cancellabile((SELECT source_id FROM tmp_id_libero)),
  'ATTO_NON_TROVATO',
  '12) Il predicato dice ATTO_NON_TROVATO su un id che non esiste'
);

SELECT throws_ok(
  format($sql$SELECT * FROM vendite.fn_cancella_fondo_fattura(%s)$sql$,
         (SELECT source_id FROM tmp_id_libero)),
  'P0001', NULL,
  '13) ...e la cancellazione rifiuta anche li'''
);

-- ============================================================
-- Cleanup
-- ============================================================
DELETE FROM vendite.fatture_fondi_fattura_source s
 WHERE s.fattura_sorgente_id = (SELECT id FROM tmp_src);

SELECT ok(
  NOT EXISTS (SELECT 1 FROM vendite.fatture_fondi_fattura_source s
               WHERE s.fattura_sorgente_id = (SELECT id FROM tmp_src)),
  '14) Cleanup completato'
);

SELECT * FROM finish();
ROLLBACK;
