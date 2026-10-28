-- ------------------------------------------------------------
-- SPDX-License-Identifier: GPL-3.0-or-later
-- pgTAP test per Zero ERP
--
-- Test: il contratto citato per il prezzo (contratto_id) da una riga di
--   commessa o da un'attivita' fatturabile e' del billing account della
--   commessa (vendite.trgfn_attivita_guard_contratto, predicato
--   vendite.fn_check_contratto_provenienza).
-- Riferimento: richiesta BE del 2026-10-21 (smoke-group-attivita-contratto,
--   Q-1), decisione di Tid D-1 dello stesso giorno. changeSet
--   20261021-64/-65/-66; codice E_ATTIVITA_CONTRATTO_INCOERENTE.
-- rev 2026-10-26 (brief-modello-documento-vendita §14, giro 10): la commessa
--   va a PRONTA_FATTURAZIONE con dbops.fn_pgtap_porta_a_stato (dal verbo, con
--   l'azione cambia_stato_commessa concessa dalla fixture), non piu' con un
--   UPDATE dello stato, che la porta rifiuta (E_DOC_STATO_SOLO_DAL_VERBO).
--
-- Semantica attesa (il contratto, non l'implementazione):
--   - il prezzo il contratto lo prende da vendite.fn_get_contratto_attivo(BA,
--     utility, data): una riga cita solo un contratto del BA della sua
--     commessa, altrimenti E_ATTIVITA_CONTRATTO_INCOERENTE;
--   - la regola e' sul BILLING ACCOUNT, non sull'emittente: un contratto di un
--     altro cliente della STESSA azienda e' rifiutato come quello di
--     un'azienda diversa;
--   - vale sulle due tabelle: la commessa, dove il valore nasce, e l'attivita'
--     fatturabile, che lo riceve dall'emissione e ha anche l'UPDATE diretto;
--   - il predicato legge contratti e commesse senza la RLS di chi scrive
--     (SECURITY DEFINER con search_path bloccato).
--
-- Elenco test (plan 8):
--   1) il predicato e' SECURITY DEFINER con search_path che comincia da
--      pg_catalog
--   2) il guard e' montato sulle due tabelle, AFTER INSERT OR UPDATE
--   3) riga di commessa con il contratto del BA della commessa: passa
--   4) riga di commessa con il contratto di un altro cliente della stessa
--      azienda -> E_ATTIVITA_CONTRATTO_INCOERENTE
--   5) riga di commessa con il contratto di un'altra azienda -> rifiuto
--   6) l'attivita' fatturabile emessa porta il contratto della riga: passa
--   7) attivita' fatturabile spostata sul contratto di un altro cliente ->
--      E_ATTIVITA_CONTRATTO_INCOERENTE
--   8) il codice e' registrato, classe TECNICO
--
-- ⚠️ I rifiuti si asseriscono sul CODICE (CONSTRAINT_NAME dell'eccezione di
--   script.fn_log_and_raise_error), non su un errore qualunque.
-- ⚠️ Il test 5 come owner non attraversa la RLS: prova la regola, non la
--   lettura sotto policy (quella la dice la forma, test 1).
-- ------------------------------------------------------------

BEGIN;

-- ⚠️ Vincoli DIFFERITI: in testa. Gli helper aprono e RICHIUDONO da se' la
--   finestra dove serve (e' il loro contratto).
SET CONSTRAINTS ALL IMMEDIATE;

-- Il contesto lo aprono i DO qui sotto, una volta per azienda: quella
--   dell'altra azienda per crearne il contratto, poi quella del test.

SELECT plan(8);

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

-- Due aziende, costruite PRIMA del contesto (una seconda azienda si
-- costruisce coi builder atomici, prima del contesto).
CREATE TEMP TABLE t_mondi AS
SELECT 'MIA'    AS lato, * FROM dbops.fn_pgtap_crea_emittente_operatore()
UNION ALL
SELECT 'ALTRUI' AS lato, * FROM dbops.fn_pgtap_crea_emittente_operatore();

-- Il contratto di ALTRUI lo crea ALTRUI, su un suo cliente.
DO $ctx$
BEGIN
    PERFORM script.fn_pgtap_set_contesto_operatore(
        (SELECT auth_user_id FROM t_mondi WHERE lato = 'ALTRUI'));
END $ctx$;

CREATE TEMP TABLE t_k_altrui AS
SELECT * FROM dbops.fn_pgtap_crea_contratto('guard contratto altrui', 'DRAFT');

-- Il contesto di MIA: la commessa del test, il contratto del suo cliente e
-- quello di un ALTRO cliente della stessa azienda.
DO $ctx$
BEGIN
    PERFORM script.fn_pgtap_set_contesto_operatore(
        (SELECT auth_user_id FROM t_mondi WHERE lato = 'MIA'));
END $ctx$;

CREATE TEMP TABLE t_c AS
SELECT * FROM dbops.fn_pgtap_crea_commessa('guard contratto');

CREATE TEMP TABLE t_k AS
SELECT * FROM dbops.fn_pgtap_crea_contratto(
                 'guard contratto', 'ATTIVO', (SELECT billing_account_id FROM t_c));

CREATE TEMP TABLE t_k_altro_cliente AS
SELECT * FROM dbops.fn_pgtap_crea_contratto('guard contratto altro cliente', 'DRAFT');

CREATE TEMP TABLE t_a AS
SELECT a.attivita_id
  FROM t_c c,
       dbops.fn_pgtap_crea_commessa_attivita(p_commessa_id => c.commessa_id) a;

-- ============================================================
-- 1-2) La forma
-- ============================================================
SELECT ok(
    (SELECT p.prosecdef
            AND p.proconfig IS NOT NULL
            AND p.proconfig[1] LIKE 'search_path=pg_catalog%'
       FROM pg_proc p
      WHERE p.oid = 'vendite.fn_check_contratto_provenienza(bigint, bigint)'::regprocedure),
    '1) il predicato e'' SECURITY DEFINER, search_path da pg_catalog (contratti e commesse hanno la RLS)'
);

SELECT is(
    (SELECT string_agg(c.relname || ' ' || (t.tgtype & 1 = 1)::text      -- ROW
                                 || ' ' || (t.tgtype & 2 = 0)::text      -- AFTER
                                 || ' ' || (t.tgtype & 4 = 4)::text      -- INSERT
                                 || ' ' || (t.tgtype & 16 = 16)::text,   -- UPDATE
                       ', ' ORDER BY c.relname)
       FROM pg_trigger t
       JOIN pg_class c ON c.oid = t.tgrelid
      WHERE t.tgfoid = 'vendite.trgfn_attivita_guard_contratto()'::regprocedure),
    'attivita_fatturabili true true true true, commesse_attivita true true true true',
    '2) il guard e'' montato sulle due tabelle, AFTER INSERT OR UPDATE FOR EACH ROW'
);

-- ============================================================
-- 3-5) La riga di commessa
-- ============================================================
UPDATE vendite.commesse_attivita
   SET contratto_id = (SELECT contratto_id FROM t_k)
 WHERE id = (SELECT attivita_id FROM t_a);

SELECT is(
    (SELECT ca.contratto_id FROM vendite.commesse_attivita ca
      WHERE ca.id = (SELECT attivita_id FROM t_a)),
    (SELECT contratto_id FROM t_k),
    '3) il contratto del billing account della commessa: passa'
);

SELECT is(
    pg_temp.codice_errore(format(
        'UPDATE vendite.commesse_attivita SET contratto_id = %s WHERE id = %s',
        (SELECT contratto_id FROM t_k_altro_cliente), (SELECT attivita_id FROM t_a))),
    'E_ATTIVITA_CONTRATTO_INCOERENTE',
    '4) contratto di un altro cliente della STESSA azienda -> E_ATTIVITA_CONTRATTO_INCOERENTE (la regola e'' sul BA, non sull''emittente)'
);

SELECT is(
    pg_temp.codice_errore(format(
        'UPDATE vendite.commesse_attivita SET contratto_id = %s WHERE id = %s',
        (SELECT contratto_id FROM t_k_altrui), (SELECT attivita_id FROM t_a))),
    'E_ATTIVITA_CONTRATTO_INCOERENTE',
    '5) contratto di un''altra azienda -> E_ATTIVITA_CONTRATTO_INCOERENTE'
);

-- ============================================================
-- 6-7) L'attivita' fatturabile
-- ============================================================
SELECT vendite.fn_link_commessa_sorgente(
    p_commessa_id      => (SELECT commessa_id FROM t_c),
    p_sorgente_tipo_id => (SELECT s.id FROM config.sorgenti s
                            WHERE s.codice_interno = 'COMMESSA' AND s.attivo),
    p_sorgente_uid     => (SELECT commessa_id FROM t_c)::text);

-- rev 2026-10-26 (giro 10): lo stato non si scrive piu' (la porta,
-- E_DOC_STATO_SOLO_DAL_VERBO): la fixture cammina la matrice dal verbo e
-- concede da se' l'azione cambia_stato_commessa.
SELECT dbops.fn_pgtap_porta_a_stato('vendite.commesse', (SELECT commessa_id FROM t_c), 'PRONTA_FATTURAZIONE');

CREATE TEMP TABLE t_emit AS
SELECT * FROM vendite.fn_emit_attivita_fatturabili_da_commessa(
    p_commessa_id   => (SELECT commessa_id FROM t_c),
    p_only_approved => true,
    p_dry_run       => false);

SELECT is(
    (SELECT af.contratto_id FROM vendite.attivita_fatturabili af
      WHERE af.commessa_attivita_id = (SELECT attivita_id FROM t_a)),
    (SELECT contratto_id FROM t_k),
    '6) l''attivita'' fatturabile emessa porta il contratto della riga: passa'
);

SELECT is(
    pg_temp.codice_errore(format(
        'UPDATE vendite.attivita_fatturabili SET contratto_id = %s WHERE commessa_attivita_id = %s',
        (SELECT contratto_id FROM t_k_altro_cliente), (SELECT attivita_id FROM t_a))),
    'E_ATTIVITA_CONTRATTO_INCOERENTE',
    '7) attivita'' fatturabile spostata sul contratto di un altro cliente -> E_ATTIVITA_CONTRATTO_INCOERENTE'
);

-- ============================================================
-- 8) Il codice e' registrato
-- ============================================================
SELECT is(
    (SELECT ce.classe::text FROM config.codici_errore ce
      WHERE ce.codice = 'E_ATTIVITA_CONTRATTO_INCOERENTE'),
    'TECNICO',
    '8) E_ATTIVITA_CONTRATTO_INCOERENTE e'' registrato, classe TECNICO (il contratto lo scrive il programma)'
);

SELECT * FROM finish();
ROLLBACK;
