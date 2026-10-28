-- ------------------------------------------------------------
-- SPDX-License-Identifier: GPL-3.0-or-later
-- rev 2026-10-26 (brief-modello-documento-vendita §14, giro 10): test 2, l'annullo «diretto» non e'
--   piu' un UPDATE dello stato (la porta lo ferma prima, E_DOC_STATO_SOLO_DAL_VERBO, e il motivo D-3
--   non si vedrebbe): e' il verbo vendite.fn_annulla_commessa senza conferma dei legami, che prova
--   prima cio' che vieta. L'attesa resta E_COMMESSA_ANNULLA_CON_RIGHE_EMESSE.
-- rev 2026-10-25 (brief-db-pgtap-reso-costruito, giro D-4): la commessa da dbops.fn_pgtap_crea_commessa (sorgente ROOT), la riga della bolla da dbops.fn_pgtap_crea_commessa_attivita (sorgente DDT_VENDITA), la fattura agganciata da dbops.fn_pgtap_fattura_attivita (ritirato il blocco DO $fatt$); il reset a mano con la GUC diventa il verbo vero vendite.fn_cleanup_fatture_by_ids, che rifiuta (E_FATTURE_RIGHE_RETTIFICATE): le sei attese sono riscritte sullo stato del modello (E-4), vedi sotto.
-- rev 2026-10-25 (brief-db-pgtap-reso-costruito): il reso a credito dal builder dbops.fn_pgtap_crea_reso (che concede da se' conferma_reso); resta scritta a mano la commessa con la fattura, che e' il caso del test.
-- rev 2026-10-25 (brief-db-pgtap-bolla-e-reso-costruiti, giro 1): la bolla da ordine dal builder dbops.fn_pgtap_crea_ddt_da_ordine; resta scritto a mano il reso a credito (giro 2) e la commessa con la fattura, che sono il caso del test.
-- rev 2026-10-20 (brief-db-grammatica-unica-documenti §13, 2e/L2c-1): le chiavi del push col codice della sorgente, composte da script.fn_segment_key dove la forma lo permette (le forme su piu' righe col prefisso lungo); corsia e codice del registro coi codici lunghi.
-- ⚠️ rev 2026-10-19 (brief-db-grammatica-unica-documenti, lotto 2b, 20261019-87 … -99):
--   l'origine dei legami della commessa e' il codice della sorgente: DDT_VENDITA per la riga
--   della bolla, RESO_VENDITA per la rettifica (erano DDT e RESO).
-- pgTAP test per Zero ERP
-- Test: annullare una commessa che porta la rettifica di un accredito.
--   vendite.fn_annulla_commessa, vendite.fn_documento_legami('COMMESSA')
--   (origine RESO), script.fn_check_commessa_annullabile (D-3),
--   vendite.fn_cleanup_fatture_by_ids (E_FATTURE_RIGHE_RETTIFICATE).
-- ChangeSet: 20261012-08 … -24
-- Brief: brief-db-annullo-a-valle-riapre-a-monte (D-7; §7.3);
--   brief-db-pgtap-reso-costruito (E-4, giro D-4).
-- ------------------------------------------------------------
-- ⛔ rev 2026-10-25 (E-4): IL FILE PROVA LO STATO CHE IL MODELLO PRODUCE.
--   La rettifica di un accredito nasce nella STESSA commessa della riga
--   fatturata che corregge (vendite.fn_accredita_riga_reso), e quella riga
--   e' EMESSA: finche' lo resta, la commessa non si annulla (D-3). Fino al
--   2026-10-25 il file la riportava NON_EMESSA con uno sgancio scritto a
--   mano; il verbo vero del reset (vendite.fn_cleanup_fatture_by_ids) su una
--   riga gia' rettificata RIFIUTA, e «Riporta da emettere» vuole la riga
--   fuori fattura. Il modello quindi non arriva mai a una commessa annullabile
--   con un accredito vivo: il ramo D-7 (vendite.fn_documento_ritira_legami,
--   ramo RETTIFICA) non lo attraversa questa strada, e le sei attese sono
--   quelle del rifiuto. La catena: ordine -> bolla consegnata -> riga di
--   commessa della bolla (sorgente DDT_VENDITA, come il push) -> emissione ->
--   fattura -> reso a credito -> accredito -> reset rifiutato -> annullo
--   rifiutato.
--
-- Indice test (plan 6):
--   1) fixture: la commessa ha un legame, la rettifica (RESO, con la riga di
--      reso); la riga della bolla e' fatturata, non e' un legame
--   2) l'annullo senza conferma (il verbo) e' rifiutato: E_COMMESSA_ANNULLA_CON_RIGHE_EMESSE
--   3) confermato il legame, il verbo rifiuta lo stesso (D-3)
--   4) il rifiuto non tocca niente: commessa viva, rettifica NON_EMESSA,
--      ponte intero, nessun ACCREDITO_ANNULLATO
--   5) la quota del reso resta accreditata (3 -> 3)
--   6) la riga della bolla resta EMESSA: il reset della fattura rettificata
--      rifiuta (E_FATTURE_RIGHE_RETTIFICATE)
--
-- ⚠️ LE FIXTURE SI COSTRUISCONO coi builder e coi verbi del dominio: nessun
--   documento preso dai dati.
-- ------------------------------------------------------------

BEGIN;
SET CONSTRAINTS ALL IMMEDIATE;

DO $ctx$ BEGIN PERFORM script.fn_pgtap_set_contesto_operatore(); END $ctx$;

SELECT plan(6);

-- L'operatore di fixture non ha azioni: l'emissione della bolla e' un verbo
-- che le applica (la conferma del reso la concede il suo builder).
DO $az$ BEGIN
    PERFORM dbops.fn_pgtap_concedi_azione(
        NULLIF(current_setting('app.current_user_id', true), '')::integer, 'emetti_ddt');
END $az$;

-- ============================================================
-- Riferimenti — costruiti
-- ============================================================
CREATE TEMP TABLE tmp_acr_cli AS
SELECT * FROM dbops.fn_pgtap_crea_cliente_ba(
    'annullo commessa rettifica',
    (SELECT u.id FROM config.utilities u
      WHERE NOT EXISTS (SELECT 1 FROM config.tipi_utenze tu WHERE tu.utility_id = u.id)
      ORDER BY u.id LIMIT 1));

CREATE TEMP TABLE tmp_acr AS
SELECT
  c.billing_account_id,
  dbops.fn_pgtap_crea_articolo('PGT-ACR-MERCE', false) AS articolo_id
FROM tmp_acr_cli c;

CREATE TEMP TABLE tmp_acr_fix(chiave text PRIMARY KEY, id bigint);
CREATE OR REPLACE FUNCTION pg_temp.acr(p_chiave text) RETURNS bigint
  AS $$ SELECT id FROM tmp_acr_fix WHERE chiave = p_chiave $$ LANGUAGE sql;

-- ============================================================
-- La catena: ordine -> bolla consegnata
-- ============================================================
-- La bolla CONSEGNATA dal builder: 10 a 25, trigger CONSEGNATO, del cliente
-- costruito sopra.
CREATE TEMP TABLE tmp_acr_bolla AS
SELECT * FROM dbops.fn_pgtap_crea_ddt_da_ordine('annullo commessa rettifica',
                  p_billing_account_id   => (SELECT billing_account_id FROM tmp_acr),
                  p_quantita             => 10,
                  p_prezzo               => 25,
                  p_articolo_id          => (SELECT articolo_id FROM tmp_acr),
                  p_fatturazione_trigger => 'CONSEGNATO');
INSERT INTO tmp_acr_fix
SELECT 'ddt', b.ddt_id FROM tmp_acr_bolla b
UNION ALL
SELECT 'ddt_riga', b.ddt_riga_id FROM tmp_acr_bolla b;

-- ============================================================
-- La commessa, la riga della bolla (con la sua sorgente, come il push),
-- l'emissione e la fattura
-- ============================================================
-- La commessa con la sorgente ROOT (l'emissione la pretende).
CREATE TEMP TABLE tmp_acr_cm AS
SELECT * FROM dbops.fn_pgtap_crea_commessa('annullo commessa rettifica', NULL,
                  (SELECT billing_account_id FROM tmp_acr), p_con_sorgente_root => true);
-- La riga della bolla, con la sua sorgente come la scrive il push (E-3).
CREATE TEMP TABLE tmp_acr_att AS
SELECT * FROM dbops.fn_pgtap_crea_commessa_attivita((SELECT commessa_id FROM tmp_acr_cm), 25,
                  p_articolo_id      => (SELECT articolo_id FROM tmp_acr),
                  p_sorgente_codice  => 'DDT_VENDITA',
                  p_sorgente_uid     => (SELECT ddt_uid FROM tmp_acr_bolla)::text,
                  p_sorgente_riga_id => pg_temp.acr('ddt_riga'),
                  p_quantita         => 10);
-- Emessa e agganciata a una fattura vera in bozza.
CREATE TEMP TABLE tmp_acr_fatt AS
SELECT * FROM dbops.fn_pgtap_fattura_attivita('annullo commessa rettifica',
                  ARRAY[(SELECT attivita_id FROM tmp_acr_att)]);
INSERT INTO tmp_acr_fix
SELECT 'cm', c.commessa_id FROM tmp_acr_cm c
UNION ALL
SELECT 'ca_ddt', a.attivita_id FROM tmp_acr_att a;

-- ============================================================
-- Reso a credito di 3 e il suo accredito: la rettifica nasce nella commessa
-- ============================================================
CREATE TEMP TABLE tmp_acr_reso AS
SELECT * FROM dbops.fn_pgtap_crea_reso('annullo commessa rettifica', pg_temp.acr('ddt'), 3,
                                       p_ddt_riga_id => pg_temp.acr('ddt_riga'));
INSERT INTO tmp_acr_fix
SELECT 'reso', x.reso_id FROM tmp_acr_reso x
UNION ALL
SELECT 'resi_riga', x.resi_riga_id FROM tmp_acr_reso x;

INSERT INTO tmp_acr_fix
SELECT 'ca_ret', a.commessa_attivita_id
  FROM vendite.fn_accredita_riga_reso(pg_temp.acr('resi_riga')) a
 LIMIT 1;

-- ⭐ E-4 (rev 2026-10-25): il reset del lotto si chiede al verbo vero,
--   vendite.fn_cleanup_fatture_by_ids, e il verbo RIFIUTA: la riga della
--   fattura e' gia' rettificata (E_FATTURE_RIGHE_RETTIFICATE). Lo sgancio
--   scritto a mano che c'era qui (UPDATE con la GUC di manutenzione)
--   costruiva uno stato che il modello non produce: la riga fatturata
--   tornata NON_EMESSA con l'accredito vivo. Il file prova ora lo stato che
--   il modello produce.
-- ⚠️ L'esito come coppia (sqlstate, codice di dominio) dal canale CONSTRAINT:
--   l'eccezione si cattura in una sottotransazione, che disfa il tentativo.
CREATE OR REPLACE FUNCTION pg_temp.acr_esito(p_sql text) RETURNS text AS $$
DECLARE v_cod text;
BEGIN
  EXECUTE p_sql;
  RETURN 'OK';
EXCEPTION WHEN OTHERS THEN
  GET STACKED DIAGNOSTICS v_cod = CONSTRAINT_NAME;
  RETURN SQLSTATE || '|' || COALESCE(NULLIF(v_cod, ''), '-');
END $$ LANGUAGE plpgsql;

CREATE TEMP TABLE tmp_acr_reset AS
SELECT pg_temp.acr_esito(format('SELECT * FROM vendite.fn_cleanup_fatture_by_ids(ARRAY[%s]::bigint[], NULL)',
                                (SELECT fattura_id FROM tmp_acr_fatt))) AS esito;

-- ⚠️ ATTESA CAMBIATA (E-4): erano due legami. La riga della bolla e' EMESSA
--   (fatturata), e fn_documento_legami propone solo le righe NON_EMESSA: il
--   legame da ritirare e' uno, la rettifica.
SELECT ok(
  (SELECT count(*) = 1
          AND count(*) FILTER (WHERE l.origine = 'RESO_VENDITA' AND l.natura = 'CONSUMO'
                                 AND l.riga_id = pg_temp.acr('ca_ret')
                                 AND l.origine_id = pg_temp.acr('reso')
                                 AND l.origine_riga_id = pg_temp.acr('resi_riga')) = 1
     FROM vendite.fn_documento_legami('COMMESSA', pg_temp.acr('cm')) l),
  '1) la commessa ha un legame, la rettifica (RESO, con la riga di reso): la riga della bolla e'' fatturata');

-- La quota accreditata prima dell'annullo: la rettifica la porta.
INSERT INTO tmp_acr_fix
SELECT 'accreditato_prima', vendite.fn_resi_riga_accreditato_partita(pg_temp.acr('resi_riga'))::bigint;

-- ⚠️ ATTESA CAMBIATA (E-4): era E_DOC_ANNULLO_CON_LEGAMI. Con la riga
--   fatturata EMESSA scatta prima D-3 (script.fn_check_commessa_annullabile).
-- ⚠️ Giro 10: lo stato non si scrive piu' con un UPDATE (la porta). L'annullo
--   senza conferma dei legami e' il verbo: D-3 viene prima della conferma.
SELECT is(
  pg_temp.acr_esito(format('SELECT vendite.fn_annulla_commessa(%s)', pg_temp.acr('cm'))),
  'P0001|E_COMMESSA_ANNULLA_CON_RIGHE_EMESSE',
  '2) l''annullo senza conferma dei legami e'' rifiutato: la commessa ha una riga gia'' emessa (D-3)');

-- ⚠️ ATTESA CAMBIATA (E-4): il verbo restituiva i due legami. Confermato il
--   legame che c'e', rifiuta lo stesso: una commessa che ha prodotto una
--   fattura non si annulla, e l'accredito resta.
SELECT is(
  pg_temp.acr_esito(format('SELECT vendite.fn_annulla_commessa(%s, 1)', pg_temp.acr('cm'))),
  'P0001|E_COMMESSA_ANNULLA_CON_RIGHE_EMESSE',
  '3) confermato il legame, il verbo rifiuta lo stesso: la riga fatturata e'' emessa (D-3)');

-- ⚠️ ATTESA CAMBIATA (E-4): commessa, rettifica, ponte e registro erano
--   quelli dell'annullo riuscito; ora il rifiuto non ha toccato niente.
SELECT ok(
  (SELECT s.codice_interno <> 'ANNULLATA' FROM vendite.commesse c
     JOIN vendite.stati_commessa s ON s.id = c.stato_commessa_id WHERE c.id = pg_temp.acr('cm'))
  AND (SELECT ca.stato_emissione = 'NON_EMESSA' FROM vendite.commesse_attivita ca
        WHERE ca.id = pg_temp.acr('ca_ret'))
  AND EXISTS (SELECT 1 FROM vendite.resi_righe_accrediti a
               WHERE a.resi_riga_id = pg_temp.acr('resi_riga'))
  AND NOT EXISTS (SELECT 1 FROM vendite.commesse_attivita_log l
                   WHERE l.commessa_attivita_id = pg_temp.acr('ca_ret')
                     AND l.evento = 'ACCREDITO_ANNULLATO'),
  '4) il rifiuto non tocca niente: commessa viva, rettifica da emettere, ponte intero, nessun ACCREDITO_ANNULLATO');

-- ⚠️ ATTESA CAMBIATA (E-4): era 3->0.
SELECT is(
  pg_temp.acr('accreditato_prima') || '->'
    || vendite.fn_resi_riga_accreditato_partita(pg_temp.acr('resi_riga'))::bigint,
  '3->3',
  '5) la quota del reso resta accreditata (3): l''accredito vive con la commessa');

-- ⚠️ ATTESA CAMBIATA (E-4): la riga della bolla era ANNULLATA col segmento
--   LIBERO. Resta EMESSA, perche' il reset della sua fattura rifiuta.
SELECT is(
  (SELECT ca.stato_emissione FROM vendite.commesse_attivita ca
    WHERE ca.id = pg_temp.acr('ca_ddt'))::text
  || '|' || (SELECT esito FROM tmp_acr_reset),
  'EMESSA|P0001|E_FATTURE_RIGHE_RETTIFICATE',
  '6) la riga della bolla resta EMESSA: il reset della sua fattura rettificata rifiuta (E_FATTURE_RIGHE_RETTIFICATE)');

SELECT * FROM finish();
ROLLBACK;
