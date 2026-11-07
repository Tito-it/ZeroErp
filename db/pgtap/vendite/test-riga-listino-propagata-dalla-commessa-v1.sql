-- ------------------------------------------------------------
-- SPDX-License-Identifier: AGPL-3.0-or-later
-- rev 2026-10-26 (brief-modello-documento-vendita §14, giro 10): il passaggio a PRONTA_FATTURAZIONE del caso 8 non e' piu' un UPDATE della colonna di stato, che la porta ferma (E_DOC_STATO_SOLO_DAL_VERBO): passa da dbops.fn_pgtap_porta_a_stato (il verbo, con l'azione concessa dalla fixture). Attese invariate.
-- pgTAP test per Zero ERP
--
-- Test: la riga di listino che ha dato il prezzo a una commessa e' «propagata»
--   e non si tocca piu' (vendite.trgfn_listini_righe_guard_stato).
-- Riferimento: brief-db-riga-listino-propagata-dalla-commessa (R-1, R-2, R-5;
--   decisione D-1: «propagata» = citata ADESSO).
--
-- rev 2026-10-15: la riga di commessa la scrive il builder
--   dbops.fn_pgtap_crea_commessa_attivita (che chiama la madre), non piu' una
--   copia della chiamata alla madre (regola del 2, richiesta del team BE).
--
-- Semantica attesa (il contratto, non l'implementazione):
--   - la madre del push scrive la riga di listino che le si passa, anche dal
--     batch e anche nel ramo ON CONFLICT;
--   - una riga di listino citata da una riga di commessa, su versione ATTIVA,
--     rifiuta UPDATE e DELETE con E_RIGA_LISTINO_PROPAGATA; una non citata no;
--   - re-push su un'altra riga di listino: la vecchia torna modificabile;
--   - l'emissione porta il legame sull'attivita' fatturabile.
--
-- Elenco test (plan 9):
--   1) una sola fn_upsert_commessa_attivita, ed ha p_listino_riga_id
--   2) il push scrive listino_riga_id = R1
--   3) UPDATE di R1 (citata)  -> E_RIGA_LISTINO_PROPAGATA
--   4) DELETE di R1 (citata)  -> E_RIGA_LISTINO_PROPAGATA
--   5) UPDATE di R2 (non citata) -> passa
--   6) re-push dal BATCH sullo stesso segmento con R2: nessun errore, la riga
--      di commessa cita R2 (ramo ON CONFLICT)
--   7) R1 non e' piu' citata: UPDATE passa (D-1)
--   8) l'emissione porta listino_riga_id = R2 sull'attivita' fatturabile
--   9) UPDATE di R2 (ora citata) -> E_RIGA_LISTINO_PROPAGATA
--
-- ⚠️ I rifiuti si asseriscono sul CODICE (CONSTRAINT_NAME dell'eccezione di
--   script.fn_log_and_raise_error), non su un P0001 qualunque: un throws_ok
--   senza codice passerebbe anche sul guard sbagliato.
-- ------------------------------------------------------------

BEGIN;

-- ⚠️ Vincoli DIFFERITI: in testa. Gli helper aprono e RICHIUDONO da se' la
--   finestra dove serve (e' il loro contratto).
SET CONSTRAINTS ALL IMMEDIATE;

-- pgtap-contesto: escluso — il contesto lo apre il builder della commessa,
--   chiamato come lo chiamera' un file su un database ricostruito.

SELECT plan(9);

-- ============================================================
-- Fixture
-- ============================================================
CREATE OR REPLACE FUNCTION pg_temp.codice_errore(p_sql text) RETURNS text
LANGUAGE plpgsql AS $$
DECLARE v_c text;
BEGIN
    EXECUTE p_sql;
    RETURN NULL;
EXCEPTION WHEN SQLSTATE 'P0001' THEN
    GET STACKED DIAGNOSTICS v_c = CONSTRAINT_NAME;
    RETURN v_c;
END $$;

-- La commessa (apre il contesto dell'operatore) e un listino dello stesso
-- emittente, versione ATTIVA, per l'utility del billing account.
CREATE TEMP TABLE t_c AS
SELECT * FROM dbops.fn_pgtap_crea_commessa('riga listino propagata');

CREATE TEMP TABLE t_l AS
SELECT * FROM dbops.fn_pgtap_crea_listino((SELECT utility_id FROM t_c), 'riga propagata');

-- Un articolo, due righe di listino (UoM diverse: la chiave attiva e'
-- versione + articolo + UoM). INSERT su versione ATTIVA e' ammesso: e' la
-- rettifica controllata. Un listino TIPIZZATO accetta solo articoli della sua
-- tipologia: l'articolo nasce con quella.
CREATE TEMP TABLE t_art AS
SELECT dbops.fn_pgtap_crea_articolo(
           ('PGT-RLP-' || substr(md5(clock_timestamp()::text), 1, 12))::varchar,
           false,
           p_listino_tipologia_id => (SELECT tipologia_id FROM t_l)) AS articolo_id;

CREATE TEMP TABLE t_uom AS
SELECT a.uom_id AS u1,
       (SELECT u.id FROM catalogo.unita_misura u
         WHERE u.attivo AND u.id <> a.uom_id ORDER BY u.id LIMIT 1) AS u2
  FROM catalogo.articoli a
 WHERE a.id = (SELECT articolo_id FROM t_art);

CREATE TEMP TABLE t_r AS
WITH ins AS (
    INSERT INTO vendite.listini_righe (listino_versione_id, articolo_id, uom_id, prezzo)
    VALUES ((SELECT listino_versione_id FROM t_l), (SELECT articolo_id FROM t_art),
            (SELECT u1 FROM t_uom), 10.00),
           ((SELECT listino_versione_id FROM t_l), (SELECT articolo_id FROM t_art),
            (SELECT u2 FROM t_uom), 20.00)
    RETURNING id, uom_id
)
SELECT (SELECT id FROM ins WHERE uom_id = (SELECT u1 FROM t_uom)) AS r1,
       (SELECT id FROM ins WHERE uom_id = (SELECT u2 FROM t_uom)) AS r2;

-- La riga di commessa con la riga R1, dal builder: e' lui a chiamare la madre
-- (dal 2026-10-15, 20261015-23, accetta articolo, versione e riga di listino).
-- Fino a quel giorno questo file chiamava la madre con ~40 argomenti
-- ricopiati: il builder costruiva l'articolo da se', senza la tipologia del
-- listino, e da usato non gliela si poteva piu' dare (guard A-10).
CREATE TEMP TABLE t_a AS
SELECT a.attivita_id
  FROM t_c c, t_l l, t_r rr,
       dbops.fn_pgtap_crea_commessa_attivita(
           p_commessa_id         => c.commessa_id,
           p_prezzo_snapshot     => 10.00,
           p_listino_versione_id => l.listino_versione_id,
           p_listino_riga_id     => rr.r1) a;

-- Il segmento della riga: il re-push dal batch (test 6) lo riusa.
CREATE TEMP TABLE t_seg AS
SELECT ca.segment_key
  FROM vendite.commesse_attivita ca
 WHERE ca.id = (SELECT attivita_id FROM t_a);

-- ============================================================
-- 1) Una sola madre, con il parametro nuovo (nessun overload)
-- ============================================================
SELECT is(
    (SELECT count(*)::integer || ' ' || bool_and('p_listino_riga_id' = ANY (p.proargnames))::text
       FROM pg_proc p JOIN pg_namespace n ON n.oid = p.pronamespace
      WHERE n.nspname = 'vendite' AND p.proname = 'fn_upsert_commessa_attivita'),
    '1 true',
    '1) una sola vendite.fn_upsert_commessa_attivita, con p_listino_riga_id'
);

-- ============================================================
-- 2) Il push scrive il legame
-- ============================================================
SELECT is(
    (SELECT ca.listino_riga_id FROM vendite.commesse_attivita ca
      WHERE ca.id = (SELECT attivita_id FROM t_a)),
    (SELECT r1 FROM t_r),
    '2) la riga di commessa nasce con listino_riga_id = R1'
);

-- ============================================================
-- 3-4) R1 citata: UPDATE e DELETE rifiutati col codice giusto
-- ============================================================
SELECT is(
    pg_temp.codice_errore(format(
        'UPDATE vendite.listini_righe SET prezzo = 11.00 WHERE id = %s', (SELECT r1 FROM t_r))),
    'E_RIGA_LISTINO_PROPAGATA',
    '3) UPDATE della riga di listino citata dalla commessa -> E_RIGA_LISTINO_PROPAGATA'
);

SELECT is(
    pg_temp.codice_errore(format(
        'DELETE FROM vendite.listini_righe WHERE id = %s', (SELECT r1 FROM t_r))),
    'E_RIGA_LISTINO_PROPAGATA',
    '4) DELETE della riga di listino citata dalla commessa -> E_RIGA_LISTINO_PROPAGATA'
);

-- ============================================================
-- 5) R2 non citata: la rettifica controllata passa
-- ============================================================
SELECT lives_ok(
    format('UPDATE vendite.listini_righe SET prezzo = 21.00 WHERE id = %s', (SELECT r2 FROM t_r)),
    '5) UPDATE di una riga di listino NON citata passa (rettifica N6)'
);

-- ============================================================
-- 6) Re-push dal batch, stesso segmento, riga R2 (ramo ON CONFLICT)
-- ============================================================
CREATE TEMP TABLE t_b AS
SELECT b.*
  FROM t_c c, t_l l, t_art a, t_uom u, t_r rr, t_seg s,
       vendite.fn_batch_upsert_commessa_attivita(jsonb_build_array(jsonb_build_object(
           'commessa_id',                   c.commessa_id,
           'segment_key',                   s.segment_key,
           'articolo_id',                   a.articolo_id,
           'istanza_utility_id',            c.istanza_utility_id,
           'data_attivita',                 script.fn_data_operativa(),
           'uom_id',                        u.u2,
           'quantita',                      1,
           'competenza_mese',               date_trunc('month', script.fn_data_operativa())::date,
           'competenza_dal',                date_trunc('month', script.fn_data_operativa())::date,
           'competenza_al',                 (date_trunc('month', script.fn_data_operativa()) + interval '1 month - 1 day')::date,
           'prezzo_snapshot',               21.00,
           'prezzo_base_snapshot',          21.00,
           'origine_prezzo',                NULL,
           'tipo_variazione_applicata',     NULL,
           'valore_variazione_applicata',   NULL,
           'promo_id',                      NULL,
           'contratto_id',                  NULL,
           'categoria_cliente_id_snapshot', NULL,
           'classe_utenza_id_snapshot',     NULL,
           'listino_versione_id',           l.listino_versione_id,
           'listino_riga_id',               rr.r2,
           'stato_approvazione',            'APPROVATA',
           'stato_emissione',               'NON_EMESSA',
           -- la provenienza della riga che si ri-invia: la stessa (la chiave la nomina)
           'sorgente_tipo_id',              (SELECT ca.sorgente_tipo_id FROM vendite.commesse_attivita ca
                                              WHERE ca.id = (SELECT attivita_id FROM t_a)),
           'sorgente_uid',                  (SELECT COALESCE(ca.sorgente_id::text, ca.sorgente_uid::text)
                                               FROM vendite.commesse_attivita ca
                                              WHERE ca.id = (SELECT attivita_id FROM t_a)),
           'tipo_movimento',                'NORMALE'))) b;

SELECT is(
    (SELECT b.updated || ' ' || b.errors::text || ' ' || ca.listino_riga_id::text
       FROM t_b b, vendite.commesse_attivita ca
      WHERE ca.id = (SELECT attivita_id FROM t_a)),
    '1 [] ' || (SELECT r2 FROM t_r)::text,
    '6) re-push dal batch: aggiorna il segmento senza errori e la riga di commessa cita R2'
);

-- ============================================================
-- 7) D-1: «propagata» = citata ADESSO. R1 torna modificabile
-- ============================================================
SELECT lives_ok(
    format('UPDATE vendite.listini_righe SET prezzo = 12.00 WHERE id = %s', (SELECT r1 FROM t_r)),
    '7) R1 non piu'' citata (nessuna AF emessa la cita): UPDATE passa'
);

-- ============================================================
-- 8) L'emissione porta il legame a valle (R-2)
-- ============================================================
SELECT vendite.fn_link_commessa_sorgente(
    p_commessa_id      => (SELECT commessa_id FROM t_c),
    p_sorgente_tipo_id => (SELECT s.id FROM config.sorgenti s
                            WHERE s.codice_interno = 'COMMESSA' AND s.attivo),
    p_sorgente_uid     => (SELECT commessa_id FROM t_c)::text);

-- Lo stato dal verbo (la porta rifiuta l'UPDATE): la fixture cammina la matrice
-- e concede da se' l'azione cambia_stato_commessa.
SELECT dbops.fn_pgtap_porta_a_stato('vendite.commesse', (SELECT commessa_id FROM t_c), 'PRONTA_FATTURAZIONE');

CREATE TEMP TABLE t_emit AS
SELECT * FROM vendite.fn_emit_attivita_fatturabili_da_commessa(
    p_commessa_id   => (SELECT commessa_id FROM t_c),
    p_only_approved => true,
    p_dry_run       => false);

SELECT is(
    (SELECT af.listino_riga_id FROM vendite.attivita_fatturabili af
      WHERE af.commessa_attivita_id = (SELECT attivita_id FROM t_a)),
    (SELECT r2 FROM t_r),
    '8) l''attivita'' fatturabile emessa porta listino_riga_id = R2'
);

-- ============================================================
-- 9) R2 ora citata: rifiutata
-- ============================================================
SELECT is(
    pg_temp.codice_errore(format(
        'UPDATE vendite.listini_righe SET prezzo = 22.00 WHERE id = %s', (SELECT r2 FROM t_r))),
    'E_RIGA_LISTINO_PROPAGATA',
    '9) UPDATE della riga di listino citata dopo il re-push -> E_RIGA_LISTINO_PROPAGATA'
);

SELECT * FROM finish();
ROLLBACK;
