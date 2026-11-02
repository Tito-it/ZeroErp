-- ------------------------------------------------------------
-- SPDX-License-Identifier: AGPL-3.0-or-later
-- pgTAP test per Zero ERP
-- Test: vendite.trgfn_registri_fatturazione_guard_forma_numero  (20260901-03)
--       script.fn_check_registro_forma_modificabile             (20260901-02)
--       Piano: brief-be-fe-crud-registri-di-numerazione, sezione 8
-- rev 2026-10-20 (brief-db-grammatica-unica-documenti §13, 2c/2d): la famiglia della bolla e' DDT_VENDITA.
-- ------------------------------------------------------------
-- Elenco test (plan 8):
-- 1) ⭐ Registro che non ha mai numerato: la check risponde []
-- 2) ⭐ ...e il cambio di forma passa davvero (il gemello positivo)
-- 3) ⛔ Dopo il primo numero: la check nomina HA_NUMERATO, e solo quello
-- 4) ⛔ ...e il cambio di prefisso viene rifiutato (P0001)
-- 5) ⭐ La check e il rifiuto dicono LA STESSA COSA
-- 6) ⭐ Il no-op passa: un UPDATE che NOMINA la colonna senza cambiarla
-- 7) ⭐ serie_default resta FUORI dal divieto
-- 8) ⭐⭐ STRUTTURALE (§12.5.2): il guard NON contiene il predicato
--
-- Scopo:
--   ⛔ Dal 2026-08-31 la forma del numero — prefisso, suffisso,
--   lunghezza_numero — vive interamente su vendite.registri_fatturazione, ed
--   e' uscita da config.sistema_codici (che un pannello ce l'ha). Fino al
--   2026-09-01 nessun guard la presidiava: un UPDATE su un registro che aveva
--   gia' numerato passava, e il contatore PROSEGUIVA — quindi il documento
--   successivo usciva con una forma nuova e un numero che continuava la serie
--   vecchia. Nessun vincolo se ne accorge: la coppia (forma, numero) non e'
--   vincolata da nessuna parte.
--   ⭐ E' la stessa specie di difetto riparato dal cantiere del prefisso
--   (difetto A: forma identica, contatore ripartito da 1) presa dal verso
--   opposto.
--
--   ⭐ IL TEST 2 SERVE QUANTO IL 4: senza il gemello positivo, un guard che
--   rifiutasse SEMPRE passerebbe il 3 e il 4 esattamente come quello giusto.
--   E' la differenza fra «rifiuta il caso giusto» e «rifiuta tutto».
--
--   ⭐ IL TEST 6 non e' un dettaglio di efficienza. `BEFORE UPDATE OF` scatta
--   quando lo statement NOMINA la colonna, anche a valore invariato: se il
--   guard non confrontasse i VALORI, il giorno in cui il mirror CSV
--   80_data/sql/vendite/registri_fatturazione.csv guadagnasse queste colonne
--   ogni migrate fallirebbe. E' gia' il motivo per cui serie_default e' rimasta
--   fuori (test 7): quel mirror la riscrive a ogni migrate.
--
--   ⭐⭐ IL TEST 8 E' IL PRESIDIO CHE CONTA. Il §12.5.2 chiede che la madre non
--   riscriva il predicato ma lo CHIAMI, e qui — a differenza della
--   disattivazione, dove a rifiutare e' un trigger GENERICO condiviso da tutto
--   il database — la madre e' nostra e la regola sta scritta in un posto solo.
--   ⚠️ Il presidio giusto NON e' «tooltip e rifiuto coincidono»: proverebbe solo
--   l'oggi. E' «il guard non contiene piu' il predicato», che e' una proprieta'
--   strutturale e non puo' scadere.
--   ⛔ Il confronto si fa sul corpo SENZA COMMENTI: un presidio che cerca una
--   stringa nel sorgente si accende sulla PROSA che spiega il difetto.
--
-- ⚠️ COSA QUESTO FILE NON PROVA: la frase tradotta. La reason_key
--   amministrazione.registri_fatturazione.forma_blocco.ha_numerato e' un debito
--   verso il FE (§12.3) e la presidia scripts/check_i18n_keys.py.
-- ------------------------------------------------------------

BEGIN;

SET CONSTRAINTS ALL IMMEDIATE;

DO $ctx$ BEGIN PERFORM script.fn_pgtap_set_contesto_operatore(); END $ctx$;

SELECT plan(8);

-- ============================================================
-- Fixture: un registro DDT nuovo, con una forma sua e nessun numero
-- ============================================================
-- ⚠️ Si nasce su una `utility_id` valorizzata: lo slot
--   (famiglia, emittente, utility) «per tutte le utility» e' gia' preso dal
--   provisioning, e quell'indice non filtra su `attivo`.
-- ⚠️ E il prefisso e' distintivo di proposito:
--   uq_registri_fatturazione_prefisso_suffisso e' UNIQUE su
--   (emittente, prefisso, suffisso) — riusare un prefisso vivo dell'emittente
--   farebbe fallire la fixture su un vincolo che non c'entra col test.
CREATE TEMP TABLE tmp_frm AS
WITH ins AS (
  INSERT INTO vendite.registri_fatturazione (
      codice, descrizione, emittente_soggetto_ruolo_id,
      famiglia_documento, reset_policy, attivo, utility_id,
      prefisso, suffisso, lunghezza_numero)
  SELECT 'FRM-' || r.emittente_soggetto_ruolo_id::text,
         'Registro pgTAP forma numero',
         r.emittente_soggetto_ruolo_id, 'DDT_VENDITA', 'ANNUALE', true,
         (SELECT u.id FROM config.utilities u ORDER BY u.id LIMIT 1),
         'ZQF', NULL, 7
    FROM vendite.registri_fatturazione r
   WHERE r.famiglia_documento = 'DDT_VENDITA'
     AND r.utility_id IS NULL
     AND r.attivo
   ORDER BY r.id
   LIMIT 1
  RETURNING id
)
SELECT id AS registro_id FROM ins;

-- ============================================================
-- 1/2) ⭐ Prima del primo numero: la check tace e la forma si cambia
-- ============================================================
SELECT is(
    (SELECT script.fn_check_registro_forma_modificabile(t.registro_id) FROM tmp_frm t),
    '[]'::jsonb,
    '1) Un registro che non ha mai numerato: nessun motivo, la forma e'' libera');

SELECT lives_ok(
    format('UPDATE vendite.registri_fatturazione SET prefisso = ''ZQG'' WHERE id = %s',
           (SELECT registro_id FROM tmp_frm)),
    '2) ...e il cambio di forma passa davvero');

-- ============================================================
-- 3/4/5) ⛔ Dopo il primo numero consegnato
-- ============================================================
-- ⭐ Il contatore si fa girare dal MOTORE, non inserendo a mano una riga in
--   registri_fatturazione_progressivi: cosi' il test prova il caso che capita
--   davvero — «e' bastato numerare un documento».
-- ⚠️ Verbo in un'istruzione SEPARATA dall'asserzione: fn_get_next_progressivo
--   scrive.
-- ⚠️ Data lontana: il pavimento della sequenza rifiuterebbe una data anteriore
--   all'ultima gia' numerata sul registro.
CREATE TEMP TABLE tmp_frm_num AS
SELECT vendite.fn_get_next_progressivo(
           (SELECT registro_id FROM tmp_frm),
           DATE '2101-06-15', NULL, '', NULL, 'DDT_VENDITA') AS numero;

SELECT is(
    (SELECT string_agg(m ->> 'reason', ',' ORDER BY m ->> 'reason')
       FROM tmp_frm t,
            LATERAL jsonb_array_elements(
                script.fn_check_registro_forma_modificabile(t.registro_id)) m),
    'HA_NUMERATO',
    '3) Dopo il primo numero la check nomina HA_NUMERATO, e solo quello');

PREPARE frm_cambia_prefisso AS
UPDATE vendite.registri_fatturazione SET prefisso = 'ZQH'
 WHERE id = (SELECT registro_id FROM tmp_frm);

SELECT throws_ok(
    'EXECUTE frm_cambia_prefisso',
    'P0001',
    NULL,
    '4) ...e il cambio di prefisso viene rifiutato');

-- ⭐ Il punto: il tooltip della maschera e il rifiuto devono dire LA STESSA
--   COSA. La check mette il codice del sezionale nei `valori`, e il messaggio a
--   catalogo lo stampa nel primo %s.
SELECT throws_like(
    'EXECUTE frm_cambia_prefisso',
    '%' || (SELECT r.codice
              FROM vendite.registri_fatturazione r, tmp_frm t
             WHERE r.id = t.registro_id) || '%',
    '5) ...e il rifiuto NOMINA il registro, come la check');

-- ============================================================
-- 6/7) ⭐ Cosa NON deve fermare
-- ============================================================
-- ⚠️ Lo stesso valore che il registro ha gia': lo statement NOMINA la colonna,
--   quindi il trigger scatta — e deve lasciar passare.
SELECT lives_ok(
    format('UPDATE vendite.registri_fatturazione SET prefisso = ''ZQG'' WHERE id = %s',
           (SELECT registro_id FROM tmp_frm)),
    '6) Un UPDATE che nomina la colonna senza cambiarla passa (no-op)');

-- ⛔ serie_default e' FUORI dal divieto, e per due ragioni indipendenti:
--   entra nella chiave del contatore (cambiarla apre una serie nuova che
--   distingue i documenti, ed e' il modo legittimo di aprirne una), e il mirror
--   CSV registri_fatturazione.csv la riscrive a OGNI migrate.
SELECT lives_ok(
    format('UPDATE vendite.registri_fatturazione SET serie_default = ''QQ'' WHERE id = %s',
           (SELECT registro_id FROM tmp_frm)),
    '7) serie_default resta fuori dal divieto');

-- ============================================================
-- 8) ⭐⭐ STRUTTURALE — §12.5.2: il guard CHIAMA, non riscrive
-- ============================================================
-- ⛔ Si guarda il corpo SENZA COMMENTI: la prosa che spiega il difetto nomina
--   le stesse parole del predicato, e un presidio che cercasse nel testo intero
--   diventerebbe rosso per la spiegazione invece che per il codice.
SELECT is(
    (SELECT (src ~ 'fn_check_registro_forma_modificabile')
        AND (src !~* 'last_numero')
        AND (src !~* 'registri_fatturazione_progressivi')
       FROM (SELECT regexp_replace(p.prosrc, '--[^' || chr(10) || ']*', '', 'g') AS src
               FROM pg_proc p
               JOIN pg_namespace n ON n.oid = p.pronamespace
              WHERE n.nspname = 'vendite'
                AND p.proname = 'trgfn_registri_fatturazione_guard_forma_numero') q),
    true,
    '8) Il guard CHIAMA la check e non contiene il predicato (§12.5.2)');

SELECT * FROM finish();

ROLLBACK;
