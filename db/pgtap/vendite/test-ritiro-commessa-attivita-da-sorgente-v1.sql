-- ------------------------------------------------------------
-- SPDX-License-Identifier: GPL-3.0-or-later
-- rev 2026-10-20 (brief-db-grammatica-unica-documenti §13.5-ter, 2d/2e): chiavi del push e ambito degli indirizzi col codice della sorgente.
-- pgTAP test per Zero ERP
-- Test: il RITIRO delle righe di commessa quando il documento si chiude
--       (brief-db-lavoro-che-non-torna-indietro, lotto L7a / Q-5' strada A)
-- ------------------------------------------------------------
-- A cosa serve, in una frase
--   Il ritiro deve prendere **solo** le righe che nessuno ha ancora emesso, e
--   il freno deve fermare la chiusura finche' ce ne sono di emesse. Sono due
--   meta' della stessa regola, e da sole non valgono: un ritiro che prende
--   tutto svuota una fattura in volo, un freno senza ritiro e' un vicolo cieco.
--
-- ⛔ LA CHIAVE POLIMORFA E' LA COSA CHE SI SBAGLIA (test 7)
--   `vendite.commesse_attivita.sorgente_uid` porta `<testata>.uid::text` per
--   TUTTE le sorgenti; `vendite.commesse_sorgenti.sorgente_uid` invece VARIA
--   (uid per il preventivo, id per l'ordine). Passare la chiave dell'altra
--   tabella **non solleva niente**: ritira zero righe, cioe' un ritiro che non
--   ritira. Il test 7 e' li' per quello.
--
-- ⚠️ FIXTURE COSTRUITE: commessa e tre righe di commessa in tre stati
--   (NON_EMESSA, EMESSA, ANNULLATA) sono INSERITE da questo file, con una
--   chiave sorgente inventata che non collide con niente.
--
-- Indice test
-- 1) Fixture: tre righe della stessa sorgente, in tre stati
-- 2) Il freno vede la riga EMESSA e nomina il suo codice
-- 3) 🔴 Il ritiro prende UNA riga: la sola NON_EMESSA
-- 4) 🔴 La riga EMESSA non e stata toccata
-- 5) La riga gia ANNULLATA non e stata toccata ne ri-loggata
-- 6) 🔴 La traccia e stata scritta, col motivo e lo stato precedente
-- 7) ⛔ Con la chiave sbagliata il ritiro ritira ZERO, e non solleva
-- 8) Il freno tace quando non ci sono piu righe emesse
-- 9) Guard: senza motivo il ritiro e rifiutato (ANNULLATA e irreversibile)
-- 10) Guard: senza chiave sorgente il ritiro e rifiutato
-- ------------------------------------------------------------

BEGIN;

SET CONSTRAINTS ALL IMMEDIATE;

-- Contesto applicativo: il test gira come gira l'applicazione (RLS attiva).
DO $ctx$ BEGIN PERFORM script.fn_pgtap_set_contesto_operatore(); END $ctx$;

SELECT plan(11);

-- ============================================================
-- Fixture
-- ============================================================
CREATE TEMP TABLE tmp_cost_rit AS
SELECT (SELECT s.id FROM config.sorgenti s WHERE s.codice_interno = 'ORDINE_VENDITA') AS sorgente_tipo_id,
       gen_random_uuid()::text                                                        AS sorgente_uid,
       script.fn_pgtap_emittente_sr_operatore()                                       AS emittente_sr_id;

-- rev 2026-10-27 (lotto 4 di D7): la commessa si COSTRUISCE
--   (dbops.fn_pgtap_crea_commessa: cliente, BA dell'azienda di chi agisce e
--   commessa aperta dalla madre, nello stato iniziale). Prima il BA si pescava
--   con LIMIT 1 e la commessa si INSERIVA a mano: da zero il BA non c'era. Le
--   tre righe di commessa restano scritte a mano: sono il caso del test.
CREATE TEMP TABLE tmp_cmm_rit AS
SELECT * FROM dbops.fn_pgtap_crea_commessa('ritiro commessa attivita da sorgente');

CREATE TEMP TABLE tmp_refs_rit AS
SELECT (SELECT billing_account_id FROM tmp_cmm_rit) AS billing_account_id,
       (SELECT utility_id FROM tmp_cmm_rit)         AS utility_id,
       (SELECT istanza_utility_id FROM tmp_cmm_rit) AS istanza_utility_id,
       (SELECT a.id FROM catalogo.articoli a
         WHERE a.attivo IS TRUE AND a.is_composito = FALSE ORDER BY a.id LIMIT 1) AS articolo_id,
       (SELECT u.id FROM catalogo.unita_misura u
         WHERE u.attivo IS TRUE ORDER BY u.id LIMIT 1)  AS uom_id,
       (SELECT t.id FROM config.tipi_doc_fiscale t
         WHERE t.attivo IS TRUE ORDER BY t.id LIMIT 1)  AS tipo_doc_fiscale_id,
       (SELECT v.id FROM config.valute v ORDER BY v.id LIMIT 1) AS valuta_id,
       (SELECT sc.id FROM vendite.stati_commessa sc
         WHERE sc.attivo IS TRUE AND sc.codice_interno <> 'ANNULLATA'
         ORDER BY sc.id LIMIT 1)           AS stato_commessa_id;

CREATE TEMP TABLE tmp_commessa_rit AS
SELECT commessa_id AS id FROM tmp_cmm_rit;

CREATE TEMP TABLE tmp_ca_rit (slot text PRIMARY KEY, attivita_id bigint);

DO $fx$
DECLARE s text;
BEGIN
  FOREACH s IN ARRAY ARRAY['NON_EMESSA', 'EMESSA', 'ANNULLATA'] LOOP
    WITH ins AS (
      INSERT INTO vendite.commesse_attivita (
        commessa_id, segment_key, articolo_id, istanza_utility_id, data_attivita,
        uom_id, quantita, competenza_mese, competenza_dal, competenza_al,
        tipo_doc_fiscale_id, valuta_id, prezzo_snapshot, pricing_mode,
        stato_approvazione, stato_emissione, sorgente_tipo_id, sorgente_uid)
      SELECT (SELECT id FROM tmp_commessa_rit),
             'ORDINE_VENDITA:PGTAP-RIT:' || s || ':' || substr(md5(clock_timestamp()::text), 1, 10),
             r.articolo_id, r.istanza_utility_id, script.fn_data_operativa(), r.uom_id, 1,
             date_trunc('month', script.fn_data_operativa())::date,
             date_trunc('month', script.fn_data_operativa())::date,
             (date_trunc('month', script.fn_data_operativa()) + INTERVAL '1 month - 1 day')::date,
             r.tipo_doc_fiscale_id, r.valuta_id, 10.000000, 'FIXED',
             'BOZZA', s,
             (SELECT sorgente_tipo_id FROM tmp_cost_rit),
             (SELECT sorgente_uid     FROM tmp_cost_rit)
        FROM tmp_refs_rit r
      RETURNING id)
    INSERT INTO tmp_ca_rit(slot, attivita_id) SELECT s, ins.id FROM ins;
  END LOOP;
END
$fx$;

SELECT ok(
  (SELECT count(*) = 3 FROM tmp_ca_rit)
  AND (SELECT count(DISTINCT ca.stato_emissione) = 3
         FROM vendite.commesse_attivita ca JOIN tmp_ca_rit t ON t.attivita_id = ca.id),
  '1) fixture: tre righe della stessa sorgente, in tre stati diversi'
);

-- ============================================================
-- 2) Il freno
-- ============================================================
SELECT is(
  script.fn_check_sorgente_chiudibile(
    (SELECT sorgente_tipo_id FROM tmp_cost_rit),
    (SELECT sorgente_uid     FROM tmp_cost_rit)) -> 0 ->> 'codice',
  'E_SORGENTE_CON_RIGHE_EMESSE',
  '2) il freno vede la riga EMESSA e nomina il suo codice'
);

-- ============================================================
-- 2-bis) ⭐ P-1 — LA FRASE RESA, che nessun cancello statico vede
-- ============================================================
-- ⛔ Il difetto che questa riga presidia era VIVO fino al 2026-09-09, e non
--   qui: questo motivo ha DUE chiamanti. vendite.trgfn_doc_guard_chiusura_-
--   sorgente passava il `dettaglio` (il conteggio) ed era corretto; ma
--   script.fn_check_ordine_annullabile lo COMPONE nei propri motivi, e la'
--   vendite.trgfn_ordini_guard_transizione passava per primo NEW.numero —
--   perche' il suo ALTRO codice comincia con «Ordine %s». Annullando un ordine
--   con righe di commessa emesse e senza DDT usciva:
--       «Il documento ha ORD-000123 righe di commessa gia' emesse»
--   ⚠️ Arita' giusta (`format()` ignora i valori in piu'), nessun `W_`, nessun
--   test rosso: i pgTAP di quel sito asseriscono `P0001`, non la frase.
--
-- ⭐ Da qui in avanti i `valori` li emette la check accanto al proprio codice
--   (changeSet 20260909-04), quindi la frase e' la stessa da entrambi i
--   chiamanti. Questo test lo prova RENDENDOLA: e' l'unica verifica che vede
--   l'ORDINE dei valori, che nessun conteggio di segnaposto puo' vedere.
-- ⚠️ Il CASE non e' pignoleria: senza, una check che smettesse di emettere
--   `valori` farebbe alzare 22023 a format() e ABORTIREBBE il file, seppellendo
--   le altre dieci asserzioni. Un presidio deve diventare rosso, non muto.
SELECT matches(
  (WITH v AS (
     SELECT script.fn_check_sorgente_chiudibile(
              (SELECT sorgente_tipo_id FROM tmp_cost_rit),
              (SELECT sorgente_uid     FROM tmp_cost_rit)) -> 0 AS motivo)
   SELECT CASE
            -- ⚠️ `coalesce`, e non un `<>` nudo: con la chiave assente
            --   jsonb_typeof() torna NULL, `NULL <> 'array'` vale NULL — cioe'
            --   NON vero — e il ramo che doveva proteggere non scatta. Il
            --   cancello scritto senza cadeva dritto nel format() che voleva
            --   evitare, e abortiva il file.
            WHEN coalesce(jsonb_typeof(v.motivo -> 'valori'), 'assente') <> 'array'
              THEN '(la check non emette valori)'
            WHEN jsonb_array_length(v.motivo -> 'valori') <> 1
              THEN format('(la check emette %s valori, il messaggio ne chiede 1)',
                          jsonb_array_length(v.motivo -> 'valori'))
            ELSE format(
                   (SELECT m.messaggio FROM config.messaggi_errore m
                     WHERE m.codice = 'E_SORGENTE_CON_RIGHE_EMESSE' AND m.lingua = 'it'),
                   VARIADIC ARRAY(SELECT jsonb_array_elements_text(v.motivo -> 'valori')))
          END
     FROM v),
  '^Il documento ha 1 righe di commessa',
  '2-bis) la frase resa nomina il CONTEGGIO, non l''identificativo del documento'
);

-- ============================================================
-- 3-6) Il ritiro
-- ============================================================
-- ⚠️ Istruzione separata dalle asserzioni: dentro l asserzione la snapshot
--   leggerebbe lo stato PRIMA delle scritture.
CREATE TEMP TABLE tmp_esito_rit AS
SELECT vendite.fn_ritira_commessa_attivita_da_sorgente(
         (SELECT sorgente_tipo_id FROM tmp_cost_rit),
         (SELECT sorgente_uid     FROM tmp_cost_rit),
         'PGTAP: chiusura del documento di origine') AS ritirate;

SELECT is(
  (SELECT ritirate FROM tmp_esito_rit), 1,
  '3) il ritiro prende UNA riga: la sola NON_EMESSA'
);

SELECT is(
  (SELECT ca.stato_emissione FROM vendite.commesse_attivita ca
    WHERE ca.id = (SELECT attivita_id FROM tmp_ca_rit WHERE slot = 'EMESSA')),
  'EMESSA'::character varying,
  '4) la riga EMESSA non e stata toccata: e in volo verso una fattura'
);

SELECT ok(
  (SELECT ca.stato_emissione = 'ANNULLATA' FROM vendite.commesse_attivita ca
    WHERE ca.id = (SELECT attivita_id FROM tmp_ca_rit WHERE slot = 'ANNULLATA'))
  AND NOT EXISTS (
    SELECT 1 FROM vendite.commesse_attivita_log l
     WHERE l.commessa_attivita_id = (SELECT attivita_id FROM tmp_ca_rit WHERE slot = 'ANNULLATA')
       AND l.evento = 'RIGA_RITIRATA_DA_SORGENTE'),
  '5) la riga gia ANNULLATA non e stata toccata ne ri-loggata'
);

SELECT ok(
  EXISTS (
    SELECT 1 FROM vendite.commesse_attivita_log l
     WHERE l.commessa_attivita_id = (SELECT attivita_id FROM tmp_ca_rit WHERE slot = 'NON_EMESSA')
       AND l.evento = 'RIGA_RITIRATA_DA_SORGENTE'
       AND l.dettaglio ->> 'motivo'           = 'PGTAP: chiusura del documento di origine'
       AND l.dettaglio ->> 'stato_precedente' = 'NON_EMESSA'
       AND l.dettaglio ->> 'sorgente_uid'     = (SELECT sorgente_uid FROM tmp_cost_rit)),
  '6) la traccia e scritta, col motivo e lo stato precedente'
);

-- ============================================================
-- 7) ⛔ La chiave sbagliata non solleva: ritira ZERO
-- ============================================================
-- ⛔ E' il modo silenzioso in cui questo verbo puo' fallire, ed e' il motivo
--   per cui restituisce un conteggio invece di void: chi lo chiama DEVE
--   guardarlo. `commesse_sorgenti` usa una chiave diversa per sorgente, e
--   confonderle non da' nessun errore.
SELECT is(
  vendite.fn_ritira_commessa_attivita_da_sorgente(
    (SELECT sorgente_tipo_id FROM tmp_cost_rit),
    gen_random_uuid()::text,
    'PGTAP: chiave che non corrisponde a niente'),
  0,
  '7) con la chiave sbagliata il ritiro ritira ZERO, e non solleva'
);

-- ============================================================
-- 8) Il freno tace quando non c e piu niente da fermare
-- ============================================================
UPDATE vendite.commesse_attivita
   SET stato_emissione = 'NON_EMESSA'
 WHERE id = (SELECT attivita_id FROM tmp_ca_rit WHERE slot = 'EMESSA');

SELECT is(
  script.fn_check_sorgente_chiudibile(
    (SELECT sorgente_tipo_id FROM tmp_cost_rit),
    (SELECT sorgente_uid     FROM tmp_cost_rit)),
  '[]'::jsonb,
  '8) senza righe emesse il freno tace: il documento si puo chiudere'
);

-- ============================================================
-- 9-10) I guard di parametro
-- ============================================================
CREATE OR REPLACE FUNCTION pg_temp.rit_codice(p_tipo bigint, p_uid text, p_motivo text)
RETURNS text AS $$
DECLARE v_cod text;
BEGIN
  PERFORM vendite.fn_ritira_commessa_attivita_da_sorgente(p_tipo, p_uid, p_motivo);
  RETURN 'NESSUN ERRORE';
EXCEPTION WHEN OTHERS THEN
  GET STACKED DIAGNOSTICS v_cod = CONSTRAINT_NAME;
  RETURN COALESCE(NULLIF(v_cod, ''), 'SQLSTATE:' || SQLSTATE);
END $$ LANGUAGE plpgsql;

-- ⚠️ Il motivo e obbligatorio perche ANNULLATA e IRREVERSIBILE: senza, resta
--   il fatto senza la ragione. E chi chiude il documento non sta guardando la
--   commessa, quindi il ritiro e per lui un effetto a distanza.
SELECT is(
  pg_temp.rit_codice((SELECT sorgente_tipo_id FROM tmp_cost_rit),
                     (SELECT sorgente_uid FROM tmp_cost_rit), '   '),
  'E_RITIRO_SORGENTE_PARAMETRO_MANCANTE',
  '9) senza motivo il ritiro e rifiutato: ANNULLATA e irreversibile'
);

SELECT is(
  pg_temp.rit_codice((SELECT sorgente_tipo_id FROM tmp_cost_rit), NULL, 'PGTAP'),
  'E_RITIRO_SORGENTE_PARAMETRO_MANCANTE',
  '10) senza chiave sorgente il ritiro e rifiutato'
);

SELECT * FROM finish();

ROLLBACK;
