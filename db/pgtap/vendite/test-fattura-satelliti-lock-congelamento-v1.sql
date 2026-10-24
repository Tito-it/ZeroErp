-- ------------------------------------------------------------
-- SPDX-License-Identifier: GPL-3.0-or-later
-- pgTAP test per Zero ERP
-- Test: vendite.trgfn_fattura_satellite_guard_congelamento (Fase 1.1)
--       montata su fatture_indirizzi e fatture_scadenze (Fase 1.2)
-- Piano: piano-db-satelliti-fattura.md Fase 2.6 / C-11
-- ------------------------------------------------------------
-- Indice test (1..11):
--  1) Cablaggio: 2 trigger BEFORE ROW ins/upd/dlt sulla funzione parametrica
--  2) Fixture: due fatture create (DRAFT e DEFINITIVA)
--  3) DRAFT: INSERT di un indirizzo ammesso
--  4) DRAFT: UPDATE dello snapshot ammesso
--  5) DEFINITIVA: INSERT rifiutato
--  6) Bypass GUC: con la GUC accesa l'INSERT sulla DEFINITIVA passa
--  7) DEFINITIVA: UPDATE rifiutato
--  8) DEFINITIVA: DELETE rifiutato
--  9) Bypass GUC: DELETE ammesso
-- 10) fatture_scadenze: stessa regola, il guard e' montato su entrambe
-- 11) CASCADE dalla testata: i satelliti cadono senza errore (stato NULL)
-- ------------------------------------------------------------
-- rev 2026-10-24 (brief-modello-documento-vendita N-1): le fatture nascono in
--   bozza e la «definitiva» si porta avanti con dbops.fn_pgtap_porta_a_stato
--   (prima nasceva gia' DEFINITIVA). Il paragrafo sotto e' superato.
-- (superato) PERCHE' LE DUE FATTURE NASCONO GIA' NELLO STATO CHE SERVE. Il
-- guard di transizione trgfn_fatture_guard_stato era montato solo su UPDATE,
-- quindi una fattura si poteva inserire direttamente in DEFINITIVA, senza
-- attraversare la matrice (1->2->8). Dal 2026-10-24 un documento nasce solo
-- nello stato iniziale (script.trgfn_doc_stato_iniziale): la matrice si
-- attraversa, e cio' che l'uscita dalla bozza pretende (indirizzo FATT,
-- intestazione) lo scrive la fixture. ⚠️ L'indirizzo FATT si toglie di nuovo
-- in EMESSA (sotto soglia, si puo'): la DEFINITIVA deve arrivare SENZA
-- indirizzi, o l'INSERT dei test 5 e 6 urterebbe l'unicita' per tipo
-- (uq_fatture_indirizzi_uno_per_tipo_) invece del guard.
--
-- PERCHE' IL PRIMO INSERT SULLA DEFINITIVA USA IL BYPASS. Per provare UPDATE e
-- DELETE oltre soglia serve una riga satellite gia' esistente su una fattura
-- congelata -- che per definizione non si puo' creare. La si crea con la GUC
-- di manutenzione accesa, che e' anche il modo in cui il test 6 verifica il
-- bypass: una sola mossa prova la via di servizio e prepara i due test dopo.
--
-- ⚠️ LA GUC SI SPEGNE ESPLICITAMENTE. Dopo il bypass si rimette a 'off': un
-- test che lasciasse la via di servizio aperta dichiarerebbe verdi i due
-- rifiuti successivi senza averli mai provati.
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

SELECT plan(11);

-- ============================================================
-- 1) Cablaggio sul catalogo.
--    tgtype = 31 -> ROW(1) + BEFORE(2) + INSERT(4) + DELETE(8) + UPDATE(16).
-- ============================================================
SELECT is(
  (SELECT count(*)::int
     FROM pg_trigger t
     JOIN pg_class c     ON c.oid = t.tgrelid
     JOIN pg_namespace n ON n.oid = c.relnamespace
     JOIN pg_proc p      ON p.oid = t.tgfoid
    WHERE n.nspname = 'vendite'
      AND c.relname IN ('fatture_scadenze', 'fatture_indirizzi')
      AND p.proname = 'trgfn_fattura_satellite_guard_congelamento'
      AND NOT t.tgisinternal
      AND t.tgtype = 31),
  2,
  '1) guard parametrico montato BEFORE ROW ins/upd/dlt su entrambe le satelliti'
);

-- ============================================================
-- Riferimenti e fixture
-- ============================================================
CREATE TEMP TABLE tmp_refs_lock AS
SELECT
  ba.id                                          AS billing_account_id,
  anagrafiche.fn_get_emittente_fiscale_id(ba.id) AS emittente_soggetto_ruolo_id,
  (SELECT m.registro_id
     FROM vendite.tipi_doc_fiscale_registri m
     JOIN config.tipi_doc_fiscale t ON t.id = m.tipo_doc_fiscale_id
    WHERE t.attivo IS TRUE ORDER BY m.id LIMIT 1) AS registro_id,
  (SELECT m.tipo_doc_fiscale_id
     FROM vendite.tipi_doc_fiscale_registri m
     JOIN config.tipi_doc_fiscale t ON t.id = m.tipo_doc_fiscale_id
    WHERE t.attivo IS TRUE ORDER BY m.id LIMIT 1) AS tipo_doc_fiscale_id,
  (SELECT v.id FROM config.valute v ORDER BY v.id LIMIT 1) AS valuta_id,
  (SELECT s.id FROM config.stati_doc_fiscale s
    WHERE s.codice_interno = 'DRAFT' AND s.attivo IS TRUE)      AS stato_draft_id,
  (SELECT s.id FROM config.stati_doc_fiscale s
    WHERE s.codice_interno = 'DEFINITIVA' AND s.attivo IS TRUE) AS stato_def_id,
  (SELECT id FROM config.tipi_indirizzi WHERE codice_interno = 'FATT') AS fatt_id
FROM anagrafiche.billing_account ba
WHERE anagrafiche.fn_get_emittente_fiscale_id(ba.id) IS NOT NULL
ORDER BY ba.id
LIMIT 1;


-- ⛔ IL REGISTRO SI ALLINEA ALL'EMITTENTE, e prima non lo faceva.
--   La riga sopra sceglieva «un registro qualunque» accanto a un emittente che
--   viene da un'altra parte: che i due coincidessero era un CASO, e dal
--   2026-08-30 vendite.trgfn_fatture_guard_registro_emittente non lo ammette
--   piu'. L'helper risponde con il registro di QUESTO emittente, creandolo se
--   non ce n'e' uno — la riga vive nella transazione del test.
UPDATE tmp_refs_lock SET registro_id = script.fn_pgtap_registro_fattura(emittente_soggetto_ruolo_id);
CREATE TEMP TABLE tmp_fatture_lock AS
WITH ins AS (
  INSERT INTO vendite.fatture (
    registro_id, data, emittente_soggetto_ruolo_id, billing_account_id,
    tipo_doc_fiscale_id, valuta_id, meta
  )
  SELECT r.registro_id, script.fn_data_operativa(), r.emittente_soggetto_ruolo_id,
         r.billing_account_id, r.tipo_doc_fiscale_id, r.valuta_id,
         jsonb_build_object('test', 'pgtap_lock_satelliti', 'caso', v.caso)
    FROM tmp_refs_lock r
   CROSS JOIN (VALUES ('draft'), ('definitiva')) AS v(caso)
  RETURNING id, meta ->> 'caso' AS caso
)
SELECT id, caso FROM ins;

-- La «definitiva» nasce in bozza: per uscirne vuole l'indirizzo FATT e
-- l'intestazione congelata (trgfn_fatture_guard_uscita_draft). Si scrivono,
-- si passa in EMESSA, si TOGLIE l'indirizzo (sotto soglia e' ammesso: vedi in
-- testa) e si arriva in DEFINITIVA, sotto i guard veri.
INSERT INTO vendite.fatture_indirizzi (fattura_id, tipo_indirizzo_id, snapshot)
SELECT f.id, r.fatt_id, '{"via":"Via Emissione pgTAP"}'::jsonb
  FROM tmp_fatture_lock f, tmp_refs_lock r
 WHERE f.caso = 'definitiva';

UPDATE vendite.fatture
   SET emittente_snapshot = '{"denominazione":"Emittente pgTAP","id_fiscale":"00000000000","sede":{"via":"Via Cedente 1","cap":"83100"}}'::jsonb,
       cliente_snapshot   = '{"denominazione":"Cliente pgTAP","id_fiscale":"11111111111"}'::jsonb
 WHERE id = (SELECT id FROM tmp_fatture_lock WHERE caso = 'definitiva');

SELECT dbops.fn_pgtap_porta_a_stato('vendite.fatture', f.id, 'EMESSA')
  FROM tmp_fatture_lock f WHERE f.caso = 'definitiva';

DELETE FROM vendite.fatture_indirizzi
 WHERE fattura_id = (SELECT id FROM tmp_fatture_lock WHERE caso = 'definitiva');

SELECT dbops.fn_pgtap_porta_a_stato('vendite.fatture', f.id, 'DEFINITIVA')
  FROM tmp_fatture_lock f WHERE f.caso = 'definitiva';

SELECT is(
  (SELECT count(*)::int FROM tmp_fatture_lock), 2,
  '2) fixture: due fatture create (DRAFT e DEFINITIVA)'
);

-- ============================================================
-- 3-4) Sotto soglia: si scrive.
-- ============================================================
SELECT lives_ok(
  format($$ INSERT INTO vendite.fatture_indirizzi (fattura_id, tipo_indirizzo_id, snapshot)
            VALUES (%s, %s, '{"via":"Via Bozza pgTAP"}'::jsonb) $$,
         (SELECT id FROM tmp_fatture_lock WHERE caso = 'draft'),
         (SELECT fatt_id FROM tmp_refs_lock)),
  '3) fattura in DRAFT: INSERT dell''indirizzo ammesso'
);

SELECT lives_ok(
  format($$ UPDATE vendite.fatture_indirizzi
               SET snapshot = '{"via":"Via Bozza pgTAP 2"}'::jsonb
             WHERE fattura_id = %s $$,
         (SELECT id FROM tmp_fatture_lock WHERE caso = 'draft')),
  '4) fattura in DRAFT: UPDATE dello snapshot ammesso'
);

-- ============================================================
-- 5) Oltre soglia: non si scrive.
-- ============================================================
SELECT throws_ok(
  format($$ INSERT INTO vendite.fatture_indirizzi (fattura_id, tipo_indirizzo_id, snapshot)
            VALUES (%s, %s, '{"via":"Via Definitiva pgTAP"}'::jsonb) $$,
         (SELECT id FROM tmp_fatture_lock WHERE caso = 'definitiva'),
         (SELECT fatt_id FROM tmp_refs_lock)),
  'P0001', NULL,
  '5) fattura in DEFINITIVA: INSERT rifiutato (E_FATTURA_SATELLITE_CONGELATO)'
);

-- ============================================================
-- 6) Bypass di manutenzione: la stessa INSERT passa.
--    E' la via che fn_cleanup_fatture_by_ids apre per il reset lotto.
-- ============================================================
SET zeroerp.maintenance_reset_lotto_draft = 'on';

SELECT lives_ok(
  format($$ INSERT INTO vendite.fatture_indirizzi (fattura_id, tipo_indirizzo_id, snapshot)
            VALUES (%s, %s, '{"via":"Via Definitiva pgTAP"}'::jsonb) $$,
         (SELECT id FROM tmp_fatture_lock WHERE caso = 'definitiva'),
         (SELECT fatt_id FROM tmp_refs_lock)),
  '6) bypass GUC acceso: INSERT sulla DEFINITIVA ammesso'
);

-- ⚠️ Via di servizio richiusa: senza questo i test 7 e 8 sarebbero verdi a vuoto.
SET zeroerp.maintenance_reset_lotto_draft = 'off';

-- ============================================================
-- 7-8) Con la GUC spenta, la riga appena creata e' intoccabile.
-- ============================================================
SELECT throws_ok(
  format($$ UPDATE vendite.fatture_indirizzi
               SET snapshot = '{"via":"Via Cambiata pgTAP"}'::jsonb
             WHERE fattura_id = %s $$,
         (SELECT id FROM tmp_fatture_lock WHERE caso = 'definitiva')),
  'P0001', NULL,
  '7) fattura in DEFINITIVA: UPDATE rifiutato'
);

SELECT throws_ok(
  format($$ DELETE FROM vendite.fatture_indirizzi WHERE fattura_id = %s $$,
         (SELECT id FROM tmp_fatture_lock WHERE caso = 'definitiva')),
  'P0001', NULL,
  '8) fattura in DEFINITIVA: DELETE rifiutato'
);

-- ============================================================
-- 9) Bypass anche in cancellazione: e' cio' che serve al reset lotto.
-- ============================================================
SET zeroerp.maintenance_reset_lotto_draft = 'on';

SELECT lives_ok(
  format($$ DELETE FROM vendite.fatture_indirizzi WHERE fattura_id = %s $$,
         (SELECT id FROM tmp_fatture_lock WHERE caso = 'definitiva')),
  '9) bypass GUC acceso: DELETE sulla DEFINITIVA ammesso'
);

SET zeroerp.maintenance_reset_lotto_draft = 'off';

-- ============================================================
-- 10) La stessa regola vale sull'altra satellite: il guard e' parametrico,
--     ma il montaggio va provato tabella per tabella (C-11).
-- ============================================================
SELECT throws_ok(
  format($$ INSERT INTO vendite.fatture_scadenze
                   (fattura_id, numero_rata, data_scadenza, importo)
            VALUES (%s, 1, script.fn_data_operativa(), 100.00) $$,
         (SELECT id FROM tmp_fatture_lock WHERE caso = 'definitiva')),
  'P0001', NULL,
  '10) fatture_scadenze: INSERT su fattura DEFINITIVA rifiutato'
);

-- ============================================================
-- 11) DELETE della testata: i satelliti se ne vanno in CASCADE e il guard
--     NON deve opporsi. E' l'uscita anticipata sullo stato NULL: quando i
--     figli scattano, la riga padre non esiste piu'. Senza quel ramo, una
--     fattura congelata non sarebbe piu' cancellabile affatto.
-- ============================================================
SET zeroerp.maintenance_reset_lotto_draft = 'on';
INSERT INTO vendite.fatture_indirizzi (fattura_id, tipo_indirizzo_id, snapshot)
SELECT f.id, r.fatt_id, '{"via":"Via Cascade pgTAP"}'::jsonb
  FROM tmp_fatture_lock f, tmp_refs_lock r
 WHERE f.caso = 'definitiva';
SET zeroerp.maintenance_reset_lotto_draft = 'off';

SELECT lives_ok(
  format($$ DELETE FROM vendite.fatture WHERE id = %s $$,
         (SELECT id FROM tmp_fatture_lock WHERE caso = 'definitiva')),
  '11) DELETE della testata: i satelliti cadono in CASCADE senza errore'
);

SELECT * FROM finish();
ROLLBACK;
