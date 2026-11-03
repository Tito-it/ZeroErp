-- ------------------------------------------------------------
-- SPDX-License-Identifier: AGPL-3.0-or-later
-- pgTAP test per Zero ERP
-- Test: la riga-onere dell'ordine non si evade, non decide lo stato, non
--   conferma da sola un ordine, non porta date di consegna; le letture di
--   riga la dichiarano.
--   vendite.fn_ordine_ha_residuo_evasione, vendite.fn_ordine_proietta_stato_evasione,
--   vendite.fn_situazione_merce_ordine (e vw_situazione_merce_ordine),
--   vendite.vw_ordini_righe_dettaglio, script.fn_check_ordine_confermabile
--   (letta da vendite.trgfn_ordini_guard_transizione e da
--   script.fn_available_actions_ordine),
--   vendite.trgfn_ordini_righe_guard_onere_senza_data_consegna.
-- ChangeSet: 20261103-22 … -27 (gruppo B del giro 1), -46 (P-2)
-- Brief: brief-db-addebito-trasporto-ordine §7, §8.1, §8.4 (K-2, K-3)
--
-- ⚠️ DIPENDENZE da changeSet di altri scrittori dello stesso giro:
--   · 20261103-16 (script.fn_natura_e_merce) e -17 (l'ammissione: l'onere
--     entra su ordine e bolla): senza, la fixture non scrive la riga-onere;
--   · 20261103-36 (vendite.fn_genera_ddt_da_ordine: l'onere passa intero
--     nella prima bolla, col legame di evasione a quantita' intera). I test
--     11 e 14 lo dichiarano come PREMESSA: se la copia non c'e', sono loro a
--     diventare rossi, e il resto del caso B non dice niente. Scelta: il
--     legame si lascia scrivere alla madre vera e non si imita a mano — una
--     copia scritta qui e la copia della madre si sommerebbero.
-- ------------------------------------------------------------
-- Indice test (plan 30):
--   1) gli oggetti esistono, il trigger e' montato
--   2) i due codici nuovi sono a catalogo, con la loro classe
--  A — ordine CONFERMATO: merce 10 + onere 1; bolla della sola merce
--   3) vw dettaglio, onere: e_onere true, causale dall'articolo
--   4) vw dettaglio, onere: evaso e residuo NULL (prima 0 e 1)
--   5) vw dettaglio, merce: e_onere false, causale NULL, residuo 10
--   6) prima della bolla: residuo (la merce)
--   7) situazione merce per ordine: la sola riga merce
--   8) vw_situazione_merce_ordine: nessuna riga per l'onere
--   9) ⭐ bolla della sola merce, emessa: l'ordine va a EVASO (prima restava
--      PARZIALMENTE_EVASO: l'onere teneva aperto il residuo)
--  10) …e non ha residuo
--  11) PREMESSA (-36): l'onere e' passato in bolla col legame intero
--  12) situazione merce per DDT: l'onere toccato dalla bolla non esce
--  B — il ramo 1: l'unico legame e' quello dell'onere copiato
--  13) bolla in bozza della sola merce: EVASO
--  14) PREMESSA (-36): l'onere ha il suo legame nella bolla in bozza
--  15) ⭐ tolta la merce dalla bolla in bozza: l'ordine torna CONFERMATO
--      (prima PARZIALMENTE_EVASO, con zero merce uscita)
--  C — K-2: un ordine di soli oneri non si conferma
--  16) la check: il primo motivo e' E_ORDINE_CONFERMA_SOLO_ONERI
--  17) …con reason, reason_key e i valori della frase
--  18) la capability: «Conferma» spento col motivo
--  19) il verbo di conferma: rifiutato col codice
--  20) controllo: l'ordine VUOTO non dice «solo oneri» (lo dice la matrice)
--  21) controllo: merce + onere in bozza, nessun motivo
--  D — K-3: la riga-onere non porta date di consegna
--  22) INSERT di un onere con la data confermata: E_RIGA_ONERE_DATA_CONSEGNA
--  23) INSERT di un onere con la data richiesta dal cliente: idem
--  24) UPDATE della sola data su una riga-onere: idem
--  25) controllo: la merce con la data di consegna passa
--  26) UPDATE dell'articolo da merce a onere su una riga con data: idem
--      (la natura la deriva un altro trigger: il guard non e' UPDATE OF)
--  27) controllo: l'onere senza date si modifica (UPDATE di un'altra colonna)
--  28) la forma del montaggio: nessun UPDATE OF, un WHEN sulle date
--  E — P-2 (20261103-46): la maschera dice cio' che il guard rifiuta
--  29) la check della data confermata, sull'onere: primo motivo RIGA_ONERE
--      col codice del guard (prima: [] in bozza, «si cambia»)
--  30) vw dettaglio: data_consegna_confermata_blocco = RIGA_ONERE sull'onere,
--      e la merce non lo riceve
--
-- ⚠️ LE FIXTURE SI COSTRUISCONO: causale e articolo-onere propri (la causale
--   e' 1:1 con l'articolo, quelle del seed hanno gia' il loro), ordini dal
--   builder con le righe, bolle dal builder della bolla da ordine. Le date di
--   consegna stanno dopo la data dell'ordine (il guard delle date contro il
--   documento parla prima, per nome).
-- ------------------------------------------------------------

BEGIN;

DO $ctx$ BEGIN PERFORM script.fn_pgtap_set_contesto_operatore(); END $ctx$;

SET CONSTRAINTS ALL IMMEDIATE;

SELECT plan(30);

-- La conferma chiede emetti_ordine (permesso => nascondi); l'emissione della
-- bolla emetti_ddt.
DO $az$ BEGIN
  PERFORM dbops.fn_pgtap_concedi_azione(
      NULLIF(current_setting('app.current_user_id', true), '')::integer, 'emetti_ordine');
  PERFORM dbops.fn_pgtap_concedi_azione(
      NULLIF(current_setting('app.current_user_id', true), '')::integer, 'emetti_ddt');
END $az$;

-- ============================================================
-- 1-2) Oggetti e codici
-- ============================================================
SELECT is(
  (SELECT count(*)::int FROM pg_proc p JOIN pg_namespace n ON n.oid = p.pronamespace
    WHERE (n.nspname, p.proname) IN (('script',  'fn_natura_e_merce'),
                                     ('vendite', 'trgfn_ordini_righe_guard_onere_senza_data_consegna')))
  + (SELECT count(*)::int FROM pg_trigger t
      WHERE NOT t.tgisinternal
        AND t.tgrelid = 'vendite.ordini_righe'::regclass
        AND t.tgfoid = 'vendite.trgfn_ordini_righe_guard_onere_senza_data_consegna'::regproc),
  3,
  '1) il BB e il guard esistono, il trigger e'' montato su vendite.ordini_righe');

SELECT is(
  (SELECT string_agg(c.codice || '=' || c.classe, ',' ORDER BY c.codice) FROM config.codici_errore c
    WHERE c.codice IN ('E_ORDINE_CONFERMA_SOLO_ONERI', 'E_RIGA_ONERE_DATA_CONSEGNA')),
  'E_ORDINE_CONFERMA_SOLO_ONERI=CONFLITTO_STATO,E_RIGA_ONERE_DATA_CONSEGNA=DATO_ERRATO',
  '2) i due codici nuovi sono a catalogo, con la loro classe');

-- ============================================================
-- Fixture — COSTRUITE
-- ============================================================
CREATE TEMP TABLE tmp_cau AS
WITH ins AS (
    INSERT INTO config.causali_onere (codice_interno, codice, descrizione)
    VALUES ('PGT_OOE_ONERE', 'PGT_OOE_ONERE', 'Fixture pgTAP: onere sull''ordine')
    RETURNING id
)
SELECT id FROM ins;

-- L'articolo-onere: natura di servizio, non gestito (un onere non e' un bene).
CREATE TEMP TABLE tmp_art AS
SELECT dbops.fn_pgtap_crea_articolo('PGT-OOE-O', false,
           p_natura_vendita_id => (SELECT nv.id FROM config.nature_vendita nv
                                    WHERE nv.codice_interno = 'SERVIZIO_UNA_TANTUM'),
           p_causale_onere_id  => (SELECT id FROM tmp_cau)) AS onere,
       dbops.fn_pgtap_crea_articolo('PGT-OOE-M', false)     AS merce;

CREATE TEMP TABLE tmp_cli AS
SELECT * FROM dbops.fn_pgtap_crea_cliente_ba('pgtap_ordine_onere');

CREATE TEMP TABLE tmp_fix(chiave text PRIMARY KEY, id bigint);

-- Un ordine con merce 10 e onere 1, nello stato chiesto; si annotano
-- l'ordine, la riga merce (_m) e la riga-onere (_o).
CREATE OR REPLACE FUNCTION pg_temp.ooe_mk_ordine(p_chiave text, p_stato text)
RETURNS void AS $$
DECLARE v_ord bigint;
BEGIN
  SELECT o.ordine_id INTO v_ord
    FROM dbops.fn_pgtap_crea_ordine_con_righe('pgtap_ordine_onere', p_stato,
           (SELECT c.billing_account_id FROM tmp_cli c),
           p_righe => jsonb_build_array(
               jsonb_build_object('quantita', 10, 'prezzo', 20,
                                  'articolo_id', (SELECT merce FROM tmp_art)),
               jsonb_build_object('quantita', 1,  'prezzo', 50,
                                  'articolo_id', (SELECT onere FROM tmp_art)))) o;
  INSERT INTO tmp_fix
  SELECT p_chiave || '_ord', v_ord
  UNION ALL
  SELECT p_chiave || CASE WHEN r.articolo_id = (SELECT onere FROM tmp_art) THEN '_o' ELSE '_m' END, r.id
    FROM vendite.ordini_righe r
   WHERE r.ordine_id = v_ord;
END $$ LANGUAGE plpgsql;

CREATE OR REPLACE FUNCTION pg_temp.ooe_fix(p_chiave text) RETURNS bigint
  AS $$ SELECT id FROM tmp_fix WHERE chiave = p_chiave $$ LANGUAGE sql;

CREATE OR REPLACE FUNCTION pg_temp.ooe_stato(p_ordine bigint) RETURNS text
  AS $$ SELECT s.codice_interno::text FROM vendite.ordini o
          JOIN config.stati_doc_ordini s ON s.id = o.stato_doc_ordine_id
         WHERE o.id = p_ordine $$ LANGUAGE sql;

-- L'esito di un'istruzione: PASSA, o il codice del rifiuto (P0001 lo porta
-- in CONSTRAINT_NAME), o lo SQLSTATE. Forma di script/test-doc-lock-montaggio-v1.
CREATE OR REPLACE FUNCTION pg_temp.ooe_esito(p_sql text) RETURNS text
LANGUAGE plpgsql AS $f$
DECLARE v_s text; v_c text;
BEGIN
    EXECUTE p_sql;
    RETURN 'PASSA';
EXCEPTION WHEN OTHERS THEN
    GET STACKED DIAGNOSTICS v_s = RETURNED_SQLSTATE, v_c = CONSTRAINT_NAME;
    RETURN CASE WHEN v_s = 'P0001' AND coalesce(v_c, '') <> '' THEN v_c
                ELSE v_s || coalesce(' ' || nullif(v_c, ''), '') END;
END
$f$;

SELECT pg_temp.ooe_mk_ordine('a', 'CONFERMATO');

-- ============================================================
-- A — la bolla della sola merce
-- ============================================================
SELECT is(
  (SELECT d.e_onere::text || '|' || (d.causale_onere_id = (SELECT id FROM tmp_cau))::text
     FROM vendite.vw_ordini_righe_dettaglio d WHERE d.id = pg_temp.ooe_fix('a_o')),
  'true|true',
  '3) vw dettaglio, onere: e_onere true, causale_onere_id dall''articolo');

SELECT is(
  (SELECT coalesce(d.qta_evasa_operativa::text, 'NULL') || '|' || coalesce(d.qta_residua_operativa::text, 'NULL')
     FROM vendite.vw_ordini_righe_dettaglio d WHERE d.id = pg_temp.ooe_fix('a_o')),
  'NULL|NULL',
  '4) vw dettaglio, onere: evaso e residuo NULL (l''onere non si evade; prima 0 e 1)');

SELECT is(
  (SELECT d.e_onere::text || '|' || coalesce(d.causale_onere_id::text, 'NULL') || '|' || d.qta_residua_operativa::numeric(18,2)::text
     FROM vendite.vw_ordini_righe_dettaglio d WHERE d.id = pg_temp.ooe_fix('a_m')),
  'false|NULL|10.00',
  '5) vw dettaglio, merce: e_onere false, causale NULL, residuo 10');

SELECT ok(
  vendite.fn_ordine_ha_residuo_evasione(pg_temp.ooe_fix('a_ord')),
  '6) prima della bolla l''ordine ha residuo: la merce');

SELECT is(
  (SELECT array_agg(s.ordine_riga_id ORDER BY s.ordine_riga_id)
     FROM vendite.fn_situazione_merce_ordine(NULL, ARRAY[pg_temp.ooe_fix('a_ord')]) s),
  ARRAY[pg_temp.ooe_fix('a_m')],
  '7) situazione merce per ordine: esce la sola riga merce');

SELECT is(
  (SELECT count(*)::int FROM vendite.vw_situazione_merce_ordine v
    WHERE v.ordine_riga_id = pg_temp.ooe_fix('a_o')),
  0,
  '8) vw_situazione_merce_ordine: nessuna riga per l''onere');

-- La bolla: il test seleziona la sola merce (l'onere ci entra da se', -36).
CREATE TEMP TABLE tmp_ddt_a AS
SELECT * FROM dbops.fn_pgtap_crea_ddt_da_ordine('pgtap_ordine_onere', 'EMESSO',
           p_ordine_id => pg_temp.ooe_fix('a_ord'),
           p_righe     => jsonb_build_array(jsonb_build_object(
                              'ordine_riga_id', pg_temp.ooe_fix('a_m'), 'qta_da_evadere', 10)));

SELECT is(
  pg_temp.ooe_stato(pg_temp.ooe_fix('a_ord')),
  'EVASO',
  '9) ⭐ bolla della sola merce emessa: l''ordine e'' EVASO (prima PARZIALMENTE_EVASO per sempre)');

SELECT ok(
  NOT vendite.fn_ordine_ha_residuo_evasione(pg_temp.ooe_fix('a_ord')),
  '10) …e non ha residuo: l''onere non lo tiene aperto');

SELECT is(
  (SELECT sum(f.qta_evasa)::numeric(18,2)::text FROM vendite.ordini_righe_fulfillment f
    WHERE f.ordine_riga_id = pg_temp.ooe_fix('a_o')),
  '1.00',
  '11) PREMESSA (20261103-36): l''onere e'' passato nella prima bolla col legame a quantita'' intera');

SELECT is(
  (SELECT array_agg(s.ordine_riga_id ORDER BY s.ordine_riga_id)
     FROM vendite.fn_situazione_merce_ordine(ARRAY[(SELECT ddt_id FROM tmp_ddt_a)], NULL) s),
  ARRAY[pg_temp.ooe_fix('a_m')],
  '12) situazione merce per DDT: l''onere toccato dalla bolla non esce');

-- ============================================================
-- B — il ramo 1 della proiezione
-- ============================================================
SELECT pg_temp.ooe_mk_ordine('b', 'CONFERMATO');

CREATE TEMP TABLE tmp_ddt_b AS
SELECT * FROM dbops.fn_pgtap_crea_ddt_da_ordine('pgtap_ordine_onere', 'DRAFT',
           p_ordine_id => pg_temp.ooe_fix('b_ord'),
           p_righe     => jsonb_build_array(jsonb_build_object(
                              'ordine_riga_id', pg_temp.ooe_fix('b_m'), 'qta_da_evadere', 10)));

SELECT is(
  pg_temp.ooe_stato(pg_temp.ooe_fix('b_ord')),
  'EVASO',
  '13) bolla in bozza della sola merce: l''ordine e'' EVASO');

SELECT is(
  (SELECT count(*)::int FROM vendite.ordini_righe_fulfillment f
     JOIN vendite.ddt_righe dr ON dr.id = f.ddt_riga_id
    WHERE f.ordine_riga_id = pg_temp.ooe_fix('b_o')
      AND dr.ddt_id = (SELECT ddt_id FROM tmp_ddt_b)),
  1,
  '14) PREMESSA (20261103-36): l''onere ha il suo legame nella bolla in bozza');

-- In bozza l'operatore toglie la riga della merce: il legame si ritira, resta
-- quello dell'onere.
DELETE FROM vendite.ddt_righe dr
 WHERE dr.id = (SELECT f.ddt_riga_id FROM vendite.ordini_righe_fulfillment f
                 WHERE f.ordine_riga_id = pg_temp.ooe_fix('b_m'));

SELECT is(
  pg_temp.ooe_stato(pg_temp.ooe_fix('b_ord')),
  'CONFERMATO',
  '15) ⭐ tolta la merce dalla bolla, resta il solo legame dell''onere: l''ordine torna CONFERMATO (prima PARZIALMENTE_EVASO)');

-- ============================================================
-- C — K-2: soli oneri
-- ============================================================
INSERT INTO tmp_fix
SELECT 'c_ord', o.ordine_id
  FROM dbops.fn_pgtap_crea_ordine_con_righe('pgtap_ordine_onere', 'DRAFT',
         (SELECT c.billing_account_id FROM tmp_cli c),
         p_righe => jsonb_build_array(jsonb_build_object(
             'quantita', 1, 'prezzo', 50, 'articolo_id', (SELECT onere FROM tmp_art)))) o;

SELECT is(
  script.fn_check_ordine_confermabile(pg_temp.ooe_fix('c_ord')) -> 0 ->> 'codice',
  'E_ORDINE_CONFERMA_SOLO_ONERI',
  '16) la check: il primo motivo di un ordine di soli oneri e'' E_ORDINE_CONFERMA_SOLO_ONERI');

SELECT is(
  (SELECT m ->> 'reason' || '|' || (m ->> 'reason_key') || '|' || jsonb_array_length(m -> 'valori')::text
     FROM (SELECT script.fn_check_ordine_confermabile(pg_temp.ooe_fix('c_ord')) -> 0 AS m) x),
  'ORDINE_SOLO_ONERI|vendite.ordini.azione_reason.solo_oneri|1',
  '17) …con reason, reason_key e un valore per la frase (il numero dell''ordine)');

SELECT is(
  (SELECT a ->> 'reason_key'
     FROM jsonb_array_elements(script.fn_available_actions_ordine(pg_temp.ooe_fix('c_ord')) -> 'available_actions') a
    WHERE a ->> 'target_state' = 'CONFERMATO' AND (a ->> 'enabled')::boolean IS FALSE),
  'vendite.ordini.azione_reason.solo_oneri',
  '18) la capability: «Conferma» spento col motivo dei soli oneri');

SELECT is(
  pg_temp.ooe_esito(format($q$SELECT * FROM vendite.fn_cambia_stato_ordine(%s, 'CONFERMATO')$q$,
                           pg_temp.ooe_fix('c_ord'))),
  'E_ORDINE_CONFERMA_SOLO_ONERI',
  '19) il verbo di conferma rifiuta un ordine di soli oneri (guard di transizione, Regola 4)');

INSERT INTO tmp_fix
SELECT 'vuoto_ord', o.ordine_id
  FROM dbops.fn_pgtap_crea_ordine('pgtap_ordine_onere', 'DRAFT',
         (SELECT c.billing_account_id FROM tmp_cli c)) o;

SELECT is(
  script.fn_check_ordine_confermabile(pg_temp.ooe_fix('vuoto_ord')),
  '[]'::jsonb,
  '20) controllo: l''ordine VUOTO non dice «solo oneri» (lo dice la matrice, E_ORDINE_CONFERMA_SENZA_RIGHE)');

SELECT pg_temp.ooe_mk_ordine('d', 'DRAFT');

SELECT is(
  script.fn_check_ordine_confermabile(pg_temp.ooe_fix('d_ord')),
  '[]'::jsonb,
  '21) controllo: merce + onere in bozza, nessun motivo');

-- ============================================================
-- D — K-3: niente date di consegna sull'onere (ordine d, in bozza)
-- ============================================================
SELECT is(
  pg_temp.ooe_esito(format(
    $q$INSERT INTO vendite.ordini_righe (ordine_id, riga_nr, articolo_id, descrizione,
                                         qta_operativa, quantita, prezzo_unitario, iva_id,
                                         data_consegna_confermata)
       SELECT %1$s, 10, %2$L, 'onere con data', 1, 1, 50, r.iva_id, script.fn_data_operativa() + 30
         FROM vendite.ordini_righe r WHERE r.id = %3$s$q$,
    pg_temp.ooe_fix('d_ord'), (SELECT onere FROM tmp_art), pg_temp.ooe_fix('d_o'))),
  'E_RIGA_ONERE_DATA_CONSEGNA',
  '22) INSERT di un onere con la data di consegna confermata: rifiutato');

SELECT is(
  pg_temp.ooe_esito(format(
    $q$INSERT INTO vendite.ordini_righe (ordine_id, riga_nr, articolo_id, descrizione,
                                         qta_operativa, quantita, prezzo_unitario, iva_id,
                                         data_consegna_richiesta_cliente)
       SELECT %1$s, 11, %2$L, 'onere con data', 1, 1, 50, r.iva_id, script.fn_data_operativa() + 30
         FROM vendite.ordini_righe r WHERE r.id = %3$s$q$,
    pg_temp.ooe_fix('d_ord'), (SELECT onere FROM tmp_art), pg_temp.ooe_fix('d_o'))),
  'E_RIGA_ONERE_DATA_CONSEGNA',
  '23) INSERT di un onere con la data richiesta dal cliente: rifiutato');

SELECT is(
  pg_temp.ooe_esito(format(
    'UPDATE vendite.ordini_righe SET data_consegna_confermata = script.fn_data_operativa() + 30 WHERE id = %s',
    pg_temp.ooe_fix('d_o'))),
  'E_RIGA_ONERE_DATA_CONSEGNA',
  '24) UPDATE della sola data su una riga-onere: rifiutato');

-- La riga merce prende una data (controllo 25), poi si prova a farla onere (26).
SELECT is(
  pg_temp.ooe_esito(format(
    'UPDATE vendite.ordini_righe SET data_consegna_confermata = script.fn_data_operativa() + 30 WHERE id = %s',
    pg_temp.ooe_fix('d_m'))),
  'PASSA',
  '25) controllo: la merce con la data di consegna passa');

SELECT is(
  pg_temp.ooe_esito(format(
    'UPDATE vendite.ordini_righe SET articolo_id = %L WHERE id = %s',
    (SELECT onere FROM tmp_art), pg_temp.ooe_fix('d_m'))),
  'E_RIGA_ONERE_DATA_CONSEGNA',
  '26) UPDATE dell''articolo da merce a onere su una riga con data: rifiutato (la natura la deriva un altro trigger)');

SELECT is(
  pg_temp.ooe_esito(format(
    'UPDATE vendite.ordini_righe SET descrizione = %L WHERE id = %s',
    'onere senza date', pg_temp.ooe_fix('d_o'))),
  'PASSA',
  '27) controllo: l''onere senza date si modifica');

-- ⭐ La forma (linee-guida-trigger «UPDATE OF»): natura_vendita_id la scrive
--   un altro trigger BEFORE al cambio di articolo, quindi niente elenco OF
--   (tgattr vuoto); il WHEN tiene fuori le righe senza date.
SELECT ok(
  (SELECT t.tgattr::text = '' AND t.tgqual IS NOT NULL
          AND pg_get_triggerdef(t.oid) ~ 'BEFORE INSERT OR UPDATE ON vendite\.ordini_righe'
     FROM pg_trigger t
    WHERE NOT t.tgisinternal
      AND t.tgrelid = 'vendite.ordini_righe'::regclass
      AND t.tgfoid = 'vendite.trgfn_ordini_righe_guard_onere_senza_data_consegna'::regproc),
  '28) il montaggio: BEFORE INSERT OR UPDATE senza OF, con un WHEN sulle date');

-- ============================================================
-- E — P-2: la check della data confermata conosce l'onere
-- ============================================================
SELECT is(
  (SELECT (m -> 0 ->> 'reason') || '|' || (m -> 0 ->> 'codice') || '|' || (m -> 0 -> 'dettaglio' ->> 'campo')
     FROM (SELECT script.fn_check_ordine_riga_data_consegna_confermata(pg_temp.ooe_fix('a_o')) AS m) x),
  'RIGA_ONERE|E_RIGA_ONERE_DATA_CONSEGNA|data_consegna_confermata',
  '29) check della data confermata sull''onere: primo motivo RIGA_ONERE, col codice del guard -27');

SELECT is(
  (SELECT o.data_consegna_confermata_blocco || '|'
          || (m.data_consegna_confermata_blocco IS DISTINCT FROM 'RIGA_ONERE')::text
     FROM vendite.vw_ordini_righe_dettaglio o, vendite.vw_ordini_righe_dettaglio m
    WHERE o.id = pg_temp.ooe_fix('a_o') AND m.id = pg_temp.ooe_fix('a_m')),
  'RIGA_ONERE|true',
  '30) vw dettaglio: blocco RIGA_ONERE sull''onere; la merce non lo riceve');

SELECT * FROM finish();
ROLLBACK;
