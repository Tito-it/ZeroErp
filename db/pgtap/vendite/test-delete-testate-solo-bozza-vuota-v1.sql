-- ------------------------------------------------------------
-- SPDX-License-Identifier: AGPL-3.0-or-later
-- pgTAP test per Zero ERP
-- Test: le testate di vendita (preventivo, offerta, contratto, ordine, bolla,
--   reso, commessa) si cancellano SOLO da bozza vuota: nello stato iniziale
--   del loro vocabolario e senza contenuto. Il guard
--   vendite.trgfn_doc_guard_delete_solo_bozza, montato BEFORE DELETE.
-- ChangeSet: 20261106-88, -89, -90, -91 (giro T.4); 20261109-25, -26, -27
--   (giro Z.2); codici E_DELETE_DOC_CON_RIGHE, E_DELETE_CONTRATTO_CON_SUCCESSIVI.
-- Brief: brief-db-sorgente-documento-e-riga §7.2 lotto T, giro T.4 (V-4);
--   lotto Z, giro Z.2 (Z2-a … Z2-e)
-- ------------------------------------------------------------
-- Indice test (plan 32):
--   LA FORMA
--    1) il guard e' montato BEFORE DELETE FOR EACH ROW sulle sette testate
--       e sulla bozza email, e su nessun'altra tabella
--    2) e' SECURITY DEFINER, con pg_catalog primo nel search_path
--    3) E_DELETE_DOC_CON_RIGHE e' a catalogo, vivo, CONFLITTO_STATO, con la
--       frase a un segnaposto
--   ORDINE
--    4) in bozza con una riga attiva: E_DELETE_DOC_CON_RIGHE
--    5) ...e l'ordine e la riga ci sono ancora
--    6) tolta la riga, la bozza vuota si cancella
--    7) confermato: E_DELETE_DOC_NON_BOZZA (lo stato si dice prima delle righe)
--   BOLLA
--    8) in bozza con una riga attiva: E_DELETE_DOC_CON_RIGHE
--    9) con la sola riga disattivata e' vuota: si cancella, e la riga la segue
--   RESO (V-4)
--   10) confermato: E_DELETE_DOC_NON_BOZZA
--   11) ...e le righe ci sono ancora
--   12) in bozza con una riga attiva: E_DELETE_DOC_CON_RIGHE
--   13) tolta la riga, la bozza vuota si cancella
--   CONTRATTO (Tid, 2026-11-06)
--   14) in bozza con una riga attiva: E_DELETE_DOC_CON_RIGHE
--   15) in bozza vuota: si cancella
--   LA FRASE
--   16) il rifiuto nomina il documento, senza segnaposti grezzi
--   IL CONTRATTO PRECEDENTE (Tid, 2026-11-07)
--   17) fk_contratti_parent e' ON DELETE NO ACTION: i successori non si staccano
--   18) un contratto in bozza vuota che e' il precedente di un altro non si
--       cancella: E_DELETE_CONTRATTO_CON_SUCCESSIVI, e il successore lo conserva
--   19) l'indice della FK c'e', parziale (parent_contratto_id IS NOT NULL)
--   PREVENTIVO (giro Z.2)
--   20) emesso: E_DELETE_DOC_NON_BOZZA (un DELETE diretto non lo cancella piu')
--   21) in bozza con una riga attiva: E_DELETE_DOC_CON_RIGHE
--   22) tolta la riga, la bozza vuota si cancella
--   OFFERTA (Z2-a, Z2-b): la bozza si chiama BOZZA, la legge il vocabolario
--   23) in bozza con un'eccezione attiva: E_DELETE_DOC_CON_RIGHE
--   24) in bozza senza eccezioni: si cancella
--   25) emessa: E_DELETE_DOC_NON_BOZZA
--   LA REVISIONE CANCELLATA (Z2-d)
--   26) nata la revisione, la madre e' superata
--   27) la revisione in bozza vuota si cancella, e la madre torna emessa
--   COMMESSA (Z2-c)
--   28) in bozza con un'attivita': E_DELETE_DOC_CON_RIGHE
--   29) in bozza col solo documento collegato: E_DELETE_DOC_CON_RIGHE
--   30) in bozza vuota: si cancella
--   31) aperta: E_DELETE_DOC_NON_BOZZA
--   32) la frase nomina la commessa e dice «contenuto», senza segnaposti grezzi
--
-- ⚠️ Il mondo si COSTRUISCE coi builder dbops.fn_pgtap_*: un file che scegliesse
--   i documenti fra quelli esistenti passerebbe a vuoto in CI.
-- ⚠️ Lo stato fuori bozza del contratto non ha un caso qui: la meta' «bozza»
--   della regola e' la stessa funzione, provata su ordine (7) e reso (10), e il
--   montaggio sul contratto e' il test 1.
-- ⚠️ Che il guard veda anche le righe che la RLS nasconderebbe (2) non si
--   costruisce: la policy delle righe risolve l'emittente dalla testata, quindi
--   una riga invisibile di una testata visibile non esiste. Il 2 presidia la
--   postura che rende la regola indipendente da quella policy.
-- ------------------------------------------------------------

BEGIN;

SET CONSTRAINTS ALL IMMEDIATE;

DO $ctx$ BEGIN PERFORM script.fn_pgtap_set_contesto_operatore(); END $ctx$;

SELECT plan(32);

CREATE FUNCTION pg_temp.messaggio(p_sql text) RETURNS text
LANGUAGE plpgsql AS $f$
BEGIN
    EXECUTE p_sql;
    RETURN 'PASSA';
EXCEPTION WHEN OTHERS THEN
    RETURN SQLERRM;
END
$f$;

-- ============================================================
-- LA FORMA
-- ============================================================
-- tgtype: 1 = ROW, 2 = BEFORE, 8 = DELETE; nessun INSERT (4) ne' UPDATE (16).
-- ⚠️ Schema e nome dal catalogo, non da regclass::text: quello omette lo schema
--   quando sta nel search_path di chi lancia (come app, config.email_outbox
--   uscirebbe senza schema).
SELECT is(
    ARRAY(SELECT format('%I.%I', n.nspname, c.relname)
            FROM pg_trigger tg
            JOIN pg_class c     ON c.oid = tg.tgrelid
            JOIN pg_namespace n ON n.oid = c.relnamespace
           WHERE tg.tgfoid = 'vendite.trgfn_doc_guard_delete_solo_bozza()'::regprocedure
             AND NOT tg.tgisinternal
             AND (tg.tgtype & 1) = 1 AND (tg.tgtype & 2) = 2 AND (tg.tgtype & 8) = 8
             AND (tg.tgtype & (4 | 16)) = 0
           ORDER BY 1),
    ARRAY['config.email_outbox', 'vendite.commesse', 'vendite.contratti', 'vendite.ddt',
          'vendite.offerte_commerciali', 'vendite.ordini', 'vendite.preventivi', 'vendite.resi'],
    '1) il guard e'' montato BEFORE DELETE FOR EACH ROW sulle sette testate di vendita e sulla bozza email, e basta');

SELECT ok(
    (SELECT p.prosecdef AND p.proconfig[1] LIKE 'search_path=pg_catalog%'
       FROM pg_proc p WHERE p.oid = 'vendite.trgfn_doc_guard_delete_solo_bozza()'::regprocedure),
    '2) il guard e'' SECURITY DEFINER, con pg_catalog primo nel search_path');

SELECT ok(
    (SELECT c.classe = 'CONFLITTO_STATO' AND c.obsoleto_dal IS NULL
            AND (SELECT count(*) FROM regexp_matches(m.messaggio, '%s', 'g')) = 1
       FROM config.codici_errore c
       JOIN config.messaggi_errore m ON m.codice = c.codice AND m.lingua = 'it'
      WHERE c.codice = 'E_DELETE_DOC_CON_RIGHE'),
    '3) E_DELETE_DOC_CON_RIGHE e'' a catalogo, vivo, CONFLITTO_STATO, con la frase a un segnaposto');

-- ============================================================
-- Il mondo
-- ============================================================
CREATE TEMP TABLE _o AS
SELECT ordine_id, ordine_riga_id FROM dbops.fn_pgtap_crea_ordine_con_righe('PGT-T4-OB', 'DRAFT');
CREATE TEMP TABLE _oc AS
SELECT ordine_id FROM dbops.fn_pgtap_crea_ordine_con_righe('PGT-T4-OC', 'CONFERMATO');
CREATE TEMP TABLE _d AS
SELECT ddt_id, ddt_riga_id FROM dbops.fn_pgtap_crea_ddt_senza_ordine('PGT-T4-DB', 'DRAFT');
CREATE TEMP TABLE _rc AS
SELECT reso_id FROM dbops.fn_pgtap_crea_reso('PGT-T4-RC');
CREATE TEMP TABLE _rb AS
SELECT reso_id, resi_riga_id FROM dbops.fn_pgtap_crea_reso('PGT-T4-RB', p_stato_codice_interno => 'DRAFT');
CREATE TEMP TABLE _c AS
SELECT contratto_id FROM dbops.fn_pgtap_crea_contratto('PGT-T4-CB', 'DRAFT');
CREATE TEMP TABLE _cv AS
SELECT contratto_id FROM dbops.fn_pgtap_crea_contratto('PGT-T4-CV', 'DRAFT');
-- Il contratto precedente (in bozza vuota) e il suo successore, che lo dichiara.
CREATE TEMP TABLE _cp AS
SELECT contratto_id FROM dbops.fn_pgtap_crea_contratto('PGT-T4-CP', 'DRAFT');
CREATE TEMP TABLE _cs AS
SELECT contratto_id FROM dbops.fn_pgtap_crea_contratto('PGT-T4-CS', 'DRAFT');
UPDATE vendite.contratti SET parent_contratto_id = (SELECT contratto_id FROM _cp)
 WHERE id = (SELECT contratto_id FROM _cs);

-- La riga del contratto in bozza: un'aggiunta a prezzo dichiarato, come
-- vendite/test-trgfn-doc-righe-lock-fuori-bozza-v1.
INSERT INTO vendite.contratti_righe (contratto_id, articolo_id, tipo_eccezione, prezzo_unitario, qta_operativa, tipo_erogazione)
SELECT (SELECT contratto_id FROM _c), dbops.fn_pgtap_crea_articolo('PGT-T4-ART'), 'AGGIUNTA', 99.00, 1.00, 'UNA_TANTUM';

-- ============================================================
-- ORDINE
-- ============================================================
SELECT is(dbops.fn_pgtap_codice_errore(format('DELETE FROM vendite.ordini WHERE id = %s', (SELECT ordine_id FROM _o))),
    'E_DELETE_DOC_CON_RIGHE',
    '4) ordine in bozza con una riga attiva: E_DELETE_DOC_CON_RIGHE');

SELECT ok(
    EXISTS (SELECT 1 FROM vendite.ordini WHERE id = (SELECT ordine_id FROM _o))
    AND EXISTS (SELECT 1 FROM vendite.ordini_righe WHERE id = (SELECT ordine_riga_id FROM _o)),
    '5) ...e l''ordine e la riga ci sono ancora');

DELETE FROM vendite.ordini_righe WHERE id = (SELECT ordine_riga_id FROM _o);

SELECT is(dbops.fn_pgtap_codice_errore(format('DELETE FROM vendite.ordini WHERE id = %s', (SELECT ordine_id FROM _o))),
    NULL,
    '6) tolta la riga, la bozza vuota si cancella');

SELECT is(dbops.fn_pgtap_codice_errore(format('DELETE FROM vendite.ordini WHERE id = %s', (SELECT ordine_id FROM _oc))),
    'E_DELETE_DOC_NON_BOZZA',
    '7) ordine confermato: E_DELETE_DOC_NON_BOZZA, prima delle righe');

-- ============================================================
-- BOLLA
-- ============================================================
SELECT is(dbops.fn_pgtap_codice_errore(format('DELETE FROM vendite.ddt WHERE id = %s', (SELECT ddt_id FROM _d))),
    'E_DELETE_DOC_CON_RIGHE',
    '8) bolla in bozza con una riga attiva: E_DELETE_DOC_CON_RIGHE');

UPDATE vendite.ddt_righe SET attivo = false WHERE id = (SELECT ddt_riga_id FROM _d);

-- ⚠️ L'esito e il conteggio in due istruzioni: una SELECT sola leggerebbe le
--   righe con lo snapshot preso prima del DELETE che la funzione esegue.
CREATE TEMP TABLE _d_esito AS
SELECT COALESCE(dbops.fn_pgtap_codice_errore(format('DELETE FROM vendite.ddt WHERE id = %s', (SELECT ddt_id FROM _d))), 'PASSA') AS esito;

SELECT is(
    (SELECT esito FROM _d_esito)
      || '|' || (SELECT count(*) FROM vendite.ddt_righe WHERE id = (SELECT ddt_riga_id FROM _d))::text,
    'PASSA|0',
    '9) con la sola riga disattivata la bolla e'' vuota: si cancella, e la riga la segue');

-- ============================================================
-- RESO (V-4)
-- ============================================================
SELECT is(dbops.fn_pgtap_codice_errore(format('DELETE FROM vendite.resi WHERE id = %s', (SELECT reso_id FROM _rc))),
    'E_DELETE_DOC_NON_BOZZA',
    '10) reso confermato: E_DELETE_DOC_NON_BOZZA');

SELECT ok(EXISTS (SELECT 1 FROM vendite.resi_righe WHERE reso_id = (SELECT reso_id FROM _rc) AND attivo),
    '11) ...e le sue righe ci sono ancora');

SELECT is(dbops.fn_pgtap_codice_errore(format('DELETE FROM vendite.resi WHERE id = %s', (SELECT reso_id FROM _rb))),
    'E_DELETE_DOC_CON_RIGHE',
    '12) reso in bozza con una riga attiva: E_DELETE_DOC_CON_RIGHE');

DELETE FROM vendite.resi_righe WHERE id = (SELECT resi_riga_id FROM _rb);

SELECT is(dbops.fn_pgtap_codice_errore(format('DELETE FROM vendite.resi WHERE id = %s', (SELECT reso_id FROM _rb))),
    NULL,
    '13) tolta la riga, il reso in bozza vuoto si cancella');

-- ============================================================
-- CONTRATTO
-- ============================================================
SELECT is(dbops.fn_pgtap_codice_errore(format('DELETE FROM vendite.contratti WHERE id = %s', (SELECT contratto_id FROM _c))),
    'E_DELETE_DOC_CON_RIGHE',
    '14) contratto in bozza con una riga attiva: E_DELETE_DOC_CON_RIGHE');

SELECT is(dbops.fn_pgtap_codice_errore(format('DELETE FROM vendite.contratti WHERE id = %s', (SELECT contratto_id FROM _cv))),
    NULL,
    '15) contratto in bozza vuoto: si cancella');

-- ============================================================
-- LA FRASE
-- ============================================================
SELECT ok(
    (SELECT m LIKE 'Contratto %ha ancora del contenuto (righe, eccezioni, attività o documenti collegati): si può eliminare solo una bozza vuota.%'
            AND m NOT LIKE '%\%s%'
       FROM pg_temp.messaggio(format('DELETE FROM vendite.contratti WHERE id = %s', (SELECT contratto_id FROM _c))) AS m),
    '16) il rifiuto nomina il documento, senza segnaposti grezzi');

-- ============================================================
-- IL CONTRATTO PRECEDENTE
-- ============================================================
SELECT is(
    (SELECT c.confdeltype::text FROM pg_constraint c
      WHERE c.conname = 'fk_contratti_parent' AND c.conrelid = 'vendite.contratti'::regclass),
    'a',
    '17) fk_contratti_parent e'' ON DELETE NO ACTION: i successori non si staccano in silenzio');

SELECT is(
    COALESCE(dbops.fn_pgtap_codice_errore(format('DELETE FROM vendite.contratti WHERE id = %s', (SELECT contratto_id FROM _cp))), 'PASSA')
      || '|' || (SELECT (c.parent_contratto_id = (SELECT contratto_id FROM _cp))::text
                   FROM vendite.contratti c WHERE c.id = (SELECT contratto_id FROM _cs)),
    'E_DELETE_CONTRATTO_CON_SUCCESSIVI|true',
    '18) il precedente in bozza vuota di un altro contratto non si cancella, e il successore lo conserva');

SELECT ok(
    EXISTS (SELECT 1 FROM pg_index i
             WHERE i.indrelid = 'vendite.contratti'::regclass
               AND i.indexrelid = to_regclass('vendite.ix_contratti_parent_contratto_id')
               AND pg_get_expr(i.indpred, i.indrelid) = '(parent_contratto_id IS NOT NULL)'),
    '19) l''indice della FK c''e'', parziale: guard e controllo referenziale cercano i successori a ogni DELETE');

-- ============================================================
-- PREVENTIVO (giro Z.2)
-- ============================================================
CREATE TEMP TABLE _pe AS
SELECT preventivo_id FROM dbops.fn_pgtap_crea_preventivo_con_righe('PGT-Z2-PE', 'EMESSO');
CREATE TEMP TABLE _pb AS
SELECT preventivo_id, preventivo_riga_id FROM dbops.fn_pgtap_crea_preventivo_con_righe('PGT-Z2-PB', 'DRAFT');

SELECT is(dbops.fn_pgtap_codice_errore(format('DELETE FROM vendite.preventivi WHERE id = %s', (SELECT preventivo_id FROM _pe))),
    'E_DELETE_DOC_NON_BOZZA',
    '20) preventivo emesso: E_DELETE_DOC_NON_BOZZA, un DELETE diretto non lo cancella piu''');

SELECT is(dbops.fn_pgtap_codice_errore(format('DELETE FROM vendite.preventivi WHERE id = %s', (SELECT preventivo_id FROM _pb))),
    'E_DELETE_DOC_CON_RIGHE',
    '21) preventivo in bozza con una riga attiva: E_DELETE_DOC_CON_RIGHE');

DELETE FROM vendite.preventivi_righe WHERE id = (SELECT preventivo_riga_id FROM _pb);

SELECT is(dbops.fn_pgtap_codice_errore(format('DELETE FROM vendite.preventivi WHERE id = %s', (SELECT preventivo_id FROM _pb))),
    NULL,
    '22) tolta la riga, il preventivo in bozza vuoto si cancella');

-- ============================================================
-- OFFERTA (Z2-a, Z2-b) — stampo: vendite/test-offerta-revisione-nel-lineage-v1
-- ============================================================
SELECT dbops.fn_pgtap_concedi_azione(current_setting('app.current_user_id')::integer, 'emetti_offerta');

CREATE TEMP TABLE _ocli AS
SELECT * FROM dbops.fn_pgtap_crea_cliente_ba(
    'bozza vuota Z.2',
    (SELECT u.id FROM config.utilities u
      WHERE NOT EXISTS (SELECT 1 FROM config.tipi_utenze tu WHERE tu.utility_id = u.id)
      ORDER BY u.id LIMIT 1));

CREATE TEMP TABLE _olist AS
SELECT * FROM dbops.fn_pgtap_crea_listino((SELECT utility_id FROM _ocli), 'bozza vuota Z.2');

-- Tre offerte in bozza: con un'eccezione (la madre, poi emessa), con
-- un'eccezione da cancellare, senza eccezioni.
CREATE TEMP TABLE _off AS
WITH o AS (
    INSERT INTO vendite.offerte_commerciali (
        emittente_fiscale_id, billing_account_id, istanza_utility_id, utility_id,
        listino_id, listino_versione_id, validita_dal, revisione_numero)
    SELECT script.fn_pgtap_emittente_operatore(), c.billing_account_id, c.istanza_utility_id, c.utility_id,
           l.listino_id, l.listino_versione_id, DATE '2096-01-01', 1
      FROM _ocli c, _olist l, generate_series(1, 3)
    RETURNING id
)
SELECT id, row_number() OVER (ORDER BY id) AS k FROM o;

INSERT INTO vendite.offerte_commerciali_utilities (offerta_id, istanza_utility_id, utility_id)
SELECT o.id, c.istanza_utility_id, c.utility_id FROM _off o, _ocli c;

CREATE TEMP TABLE _oart AS
SELECT dbops.fn_pgtap_crea_articolo('PGT-Z2-OFF') AS articolo_id;

INSERT INTO vendite.offerte_commerciali_eccezioni (
    offerta_id, articolo_id, tipo_eccezione, tipo_erogazione, fonte_quantita_attesa,
    prezzo_unitario, attivo, qta_operativa)
SELECT o.id, a.articolo_id, 'AGGIUNTA'::vendite.tipo_eccezione_contratto,
       'UNA_TANTUM', 'FISSA', 50.00, TRUE, 1.00
  FROM _off o, _oart a WHERE o.k IN (1, 2);

SELECT is(dbops.fn_pgtap_codice_errore(format('DELETE FROM vendite.offerte_commerciali WHERE id = %s', (SELECT id FROM _off WHERE k = 2))),
    'E_DELETE_DOC_CON_RIGHE',
    '23) offerta in bozza (BOZZA) con un''eccezione attiva: E_DELETE_DOC_CON_RIGHE');

SELECT is(dbops.fn_pgtap_codice_errore(format('DELETE FROM vendite.offerte_commerciali WHERE id = %s', (SELECT id FROM _off WHERE k = 3))),
    NULL,
    '24) offerta in bozza senza eccezioni: si cancella');

SELECT dbops.fn_pgtap_porta_a_stato('vendite.offerte_commerciali', (SELECT id FROM _off WHERE k = 1), 'EMESSA') AS stato;

SELECT is(dbops.fn_pgtap_codice_errore(format('DELETE FROM vendite.offerte_commerciali WHERE id = %s', (SELECT id FROM _off WHERE k = 1))),
    'E_DELETE_DOC_NON_BOZZA',
    '25) offerta emessa: E_DELETE_DOC_NON_BOZZA');

-- ============================================================
-- LA REVISIONE CANCELLATA (Z2-d)
-- ============================================================
-- Il verbo in un'istruzione sua: in una WHERE girerebbe per ogni riga scandita.
CREATE TEMP TABLE _orev AS
SELECT vendite.fn_crea_revisione_offerta((SELECT id FROM _off WHERE k = 1), NULL) AS id;

SELECT is(
    (SELECT s.is_superato FROM vendite.offerte_commerciali o
       JOIN config.stati_doc_offerte s ON s.id = o.stato_doc_offerta_id
      WHERE o.id = (SELECT id FROM _off WHERE k = 1)),
    true,
    '26) nata la revisione, la madre e'' superata');

-- La revisione e' una bozza: le eccezioni che ha preso dalla madre si
-- disattivano, e la bozza resta vuota.
UPDATE vendite.offerte_commerciali_eccezioni SET attivo = false
 WHERE offerta_id = (SELECT id FROM _orev);

CREATE TEMP TABLE _orev_esito AS
SELECT COALESCE(dbops.fn_pgtap_codice_errore(format('DELETE FROM vendite.offerte_commerciali WHERE id = %s', (SELECT id FROM _orev))), 'PASSA') AS esito;

SELECT is(
    (SELECT esito FROM _orev_esito)
      || '|' || (SELECT s.emissione::text FROM vendite.offerte_commerciali o
                   JOIN config.stati_doc_offerte s ON s.id = o.stato_doc_offerta_id
                  WHERE o.id = (SELECT id FROM _off WHERE k = 1)),
    'PASSA|true',
    '27) la revisione in bozza vuota si cancella, e la madre torna nello stato d''emissione');

-- ============================================================
-- COMMESSA (Z2-c)
-- ============================================================
CREATE TEMP TABLE _ca AS
SELECT commessa_id FROM dbops.fn_pgtap_crea_commessa('PGT-Z2-CA', NULL, NULL, true);
CREATE TEMP TABLE _cl AS
SELECT commessa_id FROM dbops.fn_pgtap_crea_commessa('PGT-Z2-CL', NULL, NULL, false, true);
CREATE TEMP TABLE _cvz AS
SELECT commessa_id FROM dbops.fn_pgtap_crea_commessa('PGT-Z2-CV', NULL, NULL, false);
CREATE TEMP TABLE _cap AS
SELECT commessa_id FROM dbops.fn_pgtap_crea_commessa('PGT-Z2-CP', 'APERTA');

SELECT is(dbops.fn_pgtap_codice_errore(format('DELETE FROM vendite.commesse WHERE id = %s', (SELECT commessa_id FROM _ca))),
    'E_DELETE_DOC_CON_RIGHE',
    '28) commessa in bozza con un''attivita'': E_DELETE_DOC_CON_RIGHE');

SELECT is(dbops.fn_pgtap_codice_errore(format('DELETE FROM vendite.commesse WHERE id = %s', (SELECT commessa_id FROM _cl))),
    'E_DELETE_DOC_CON_RIGHE',
    '29) commessa in bozza col solo documento collegato: E_DELETE_DOC_CON_RIGHE');

SELECT is(dbops.fn_pgtap_codice_errore(format('DELETE FROM vendite.commesse WHERE id = %s', (SELECT commessa_id FROM _cvz))),
    NULL,
    '30) commessa in bozza vuota: si cancella');

SELECT is(dbops.fn_pgtap_codice_errore(format('DELETE FROM vendite.commesse WHERE id = %s', (SELECT commessa_id FROM _cap))),
    'E_DELETE_DOC_NON_BOZZA',
    '31) commessa aperta: E_DELETE_DOC_NON_BOZZA');

SELECT ok(
    (SELECT m LIKE 'Commessa %ha ancora del contenuto%: si può eliminare solo una bozza vuota.%'
            AND m NOT LIKE '%\%s%'
       FROM pg_temp.messaggio(format('DELETE FROM vendite.commesse WHERE id = %s', (SELECT commessa_id FROM _ca))) AS m),
    '32) il rifiuto nomina la commessa e dice «contenuto», senza segnaposti grezzi');

SELECT * FROM finish();
ROLLBACK;
