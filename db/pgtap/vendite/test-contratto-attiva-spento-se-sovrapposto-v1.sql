-- ------------------------------------------------------------
-- SPDX-License-Identifier: GPL-3.0-or-later
-- pgTAP test per Zero ERP
--
-- Test: «Attiva» del contratto si spegne su un contratto VINCOLANTE sovrapposto,
--   e il guard di transizione rifiuta col codice che lo nomina.
--   changeSet 20261020-19 (script.fn_check_contratto_sovrapposto), -20 (capability),
--   -21 (guard). Richiesta BE del 2026-10-19, decisioni D-1/D-2 di Tid in chat.
--
-- Il difetto: su una bozza sovrapposta a un contratto ATTIVO «Attiva» era acceso;
--   premuto, si apriva il dialog della stampa e il rifiuto arrivava solo alla
--   conferma, dall'EXCLUDE ex_contratti_no_overlap (23P01, senza il contratto in
--   conflitto). Ora la capability e il guard leggono la stessa check.
--
-- «Vincolante» = partecipa_overlap_snapshot: non in bozza e non annullato, quindi
--   ATTIVO e anche CESSATO. Una bozza non blocca nessuno.
--
-- ⭐ I soggetti li FABBRICA (fn_pgtap_crea_cliente_ba, fn_pgtap_crea_listino):
--   nessuna pesca dai dati, verde anche su un database ricostruito da zero.
--   Periodi dal 2078 in poi, su clienti nuovi: nessun contratto vero li tocca.
--
-- Fixture (BA1 salvo dove detto, ambito COMMODITY, listino con versione di oggi):
--   INC    ATTIVO   2080-01-01 .. 2080-12-31
--   CES    CESSATO  2078-01-01 .. 2078-12-31
--   PERP   ATTIVO   2085-01-01 .. (perpetuo)
--   B_OVL  DRAFT    2080-06-01 .. 2081-05-31   sopra INC
--   B_DOPO DRAFT    2081-01-01 .. 2081-12-31   periodo libero
--   B_AMB  DRAFT    2080-06-01 .. 2080-09-30   ambito SERVIZI
--   B_IST  DRAFT    2080-06-01 .. 2080-09-30   su BA2 (altra istanza)
--   B_CES  DRAFT    2078-06-01 .. 2079-03-31   sopra CES
--   B_PERP DRAFT    2086-01-01 .. 2086-12-31   sopra PERP
--   B_ESCE DRAFT    2080-07-01 .. 2080-09-30   sopra INC, esce nella stessa istruzione
--   D1, D2 DRAFT    2082 / 2082-06..2082-12    due bozze sovrapposte fra loro
--
-- Indice test (1..20):
--   Forma
--    1) la check esiste con la firma della quintupla (nessun id da escludere)
--    2) capability e guard CHIAMANO la check (la regola sta in un posto solo)
--   Sopra un ATTIVO
--    3) B_OVL: «Attiva» spento
--    4) B_OVL: il motivo e' CONTRATTO_SOVRAPPOSTO, con la sua reason_key e valori [INC]
--    5) B_OVL: l'attivazione e' rifiutata con E_CONTRATTO_OVERLAP_ESISTENTE (P0001, non 23P01)
--    6) B_OVL: il messaggio nomina il contratto in conflitto
--   Accesi
--    7) B_DOPO, periodo diverso: «Attiva» acceso
--    8) B_AMB, ambito diverso: acceso
--    9) B_IST, istanza diversa: acceso
--   10) B_IST: l'attivazione passa
--   La quintupla e' quella di NEW (stessa istruzione)
--   11) B_DOPO spostato sopra INC nello stesso UPDATE che lo attiva: rifiutato col codice
--   12) B_ESCE spostato fuori da INC nello stesso UPDATE che lo attiva: passa
--   Altri vincolanti
--   13) B_CES sopra un CESSATO: spento, valori [CES]
--   14) B_PERP sopra un ATTIVO perpetuo (valido_al NULL): spento, valori [PERP]
--   Bozza su bozza
--   15) D2 sovrapposta alla bozza D1: nasce
--   16) D2: «Attiva» acceso (una bozza non e' vincolante)
--   17) D2: l'attivazione passa
--   18) D1: ora «Attiva» e' spento, e il motivo nomina D2
--   La difesa dura
--   19) un INSERT diretto in ATTIVO sopra INC (nessuna transizione): 23P01 dall'EXCLUDE
--   20) dopo il rifiuto B_OVL e' ancora in bozza
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

SELECT plan(20);

-- ============================================================
-- Fixture
-- ============================================================
CREATE TEMP TABLE tmp_sov_utility AS
SELECT u.id AS utility_id
  FROM config.utilities u
 WHERE NOT EXISTS (SELECT 1 FROM config.tipi_utenze tu WHERE tu.utility_id = u.id)
 ORDER BY u.id
 LIMIT 1;

CREATE TEMP TABLE tmp_sov_ba AS
SELECT 'BA1'::text AS lato, c.billing_account_id, c.istanza_utility_id, c.utility_id
  FROM dbops.fn_pgtap_crea_cliente_ba('attiva sovrapposto 1', (SELECT utility_id FROM tmp_sov_utility)) c
UNION ALL
SELECT 'BA2', c.billing_account_id, c.istanza_utility_id, c.utility_id
  FROM dbops.fn_pgtap_crea_cliente_ba('attiva sovrapposto 2', (SELECT utility_id FROM tmp_sov_utility)) c;

CREATE TEMP TABLE tmp_sov_listino AS
SELECT listino_id FROM dbops.fn_pgtap_crea_listino(
    (SELECT utility_id FROM tmp_sov_utility), 'attiva sovrapposto');

-- Scopo: un contratto modalita' A (listino + variazione globale) nello stato,
--   sul lato e nel periodo chiesti. Ritorna l'id.
CREATE FUNCTION pg_temp.contratto(
    p_numero text, p_stato text, p_lato text, p_dal date, p_al date,
    p_ambito text DEFAULT 'COMMODITY')
RETURNS bigint LANGUAGE sql AS $$
    INSERT INTO vendite.contratti(
        numero, billing_account_id, istanza_utility_id, utility_id, ambito,
        stato_doc_contratto_id, valido_dal, valido_al,
        listino_id, tipo_variazione_globale, valore_variazione_globale)
    SELECT p_numero, ba.billing_account_id, ba.istanza_utility_id, ba.utility_id, p_ambito,
           (SELECT id FROM config.stati_doc_contratti WHERE codice_interno = p_stato),
           p_dal, p_al,
           l.listino_id, 'PERCENTUALE', -10
      FROM tmp_sov_ba ba, tmp_sov_listino l
     WHERE ba.lato = p_lato
    RETURNING id
$$;

-- Scopo: l'azione verso ATTIVO nel blob della capability del contratto.
CREATE FUNCTION pg_temp.azione_attiva(p_numero text)
RETURNS jsonb LANGUAGE sql AS $$
    SELECT a
      FROM vendite.contratti c,
           jsonb_array_elements(script.fn_available_actions_contratto(c.id) -> 'available_actions') a
     WHERE c.numero = p_numero
       AND a ->> 'target_state' = 'ATTIVO'
$$;

-- Scopo: il motivo della sovrapposizione nell'azione verso ATTIVO, in una riga:
--   reason | reason_key | valori. NULL se il motivo non c'e'.
CREATE FUNCTION pg_temp.motivo_sovrapposto(p_numero text)
RETURNS text LANGUAGE sql AS $$
    SELECT concat_ws(' | ', m ->> 'reason', m ->> 'reason_key', (m -> 'valori')::text)
      FROM jsonb_array_elements(pg_temp.azione_attiva(p_numero) -> 'reasons') m
     WHERE m ->> 'reason' = 'CONTRATTO_SOVRAPPOSTO'
$$;

-- Scopo: porta il contratto ad ATTIVO, eventualmente cambiando le date nella
--   STESSA istruzione. Ritorna 'OK' oppure SQLSTATE|codice|messaggio.
CREATE FUNCTION pg_temp.attiva(p_numero text, p_dal date DEFAULT NULL, p_al date DEFAULT NULL)
RETURNS text LANGUAGE plpgsql AS $$
DECLARE
    v_cod text;
    v_msg text;
BEGIN
    UPDATE vendite.contratti
       SET stato_doc_contratto_id = (SELECT id FROM config.stati_doc_contratti WHERE codice_interno = 'ATTIVO'),
           valido_dal = COALESCE(p_dal, valido_dal),
           valido_al  = CASE WHEN p_dal IS NULL THEN valido_al ELSE p_al END
     WHERE numero = p_numero;
    RETURN 'OK';
EXCEPTION WHEN OTHERS THEN
    GET STACKED DIAGNOSTICS v_cod = CONSTRAINT_NAME, v_msg = MESSAGE_TEXT;
    RETURN SQLSTATE || '|' || COALESCE(NULLIF(v_cod, ''), '-') || '|' || v_msg;
END $$;

SELECT pg_temp.contratto('PGTAP_SOV_INC',    'ATTIVO',  'BA1', DATE '2080-01-01', DATE '2080-12-31');
SELECT pg_temp.contratto('PGTAP_SOV_CES',    'CESSATO', 'BA1', DATE '2078-01-01', DATE '2078-12-31');
SELECT pg_temp.contratto('PGTAP_SOV_PERP',   'ATTIVO',  'BA1', DATE '2085-01-01', NULL);
SELECT pg_temp.contratto('PGTAP_SOV_B_OVL',  'DRAFT',   'BA1', DATE '2080-06-01', DATE '2081-05-31');
SELECT pg_temp.contratto('PGTAP_SOV_B_DOPO', 'DRAFT',   'BA1', DATE '2081-01-01', DATE '2081-12-31');
SELECT pg_temp.contratto('PGTAP_SOV_B_AMB',  'DRAFT',   'BA1', DATE '2080-06-01', DATE '2080-09-30', 'SERVIZI');
SELECT pg_temp.contratto('PGTAP_SOV_B_IST',  'DRAFT',   'BA2', DATE '2080-06-01', DATE '2080-09-30');
SELECT pg_temp.contratto('PGTAP_SOV_B_CES',  'DRAFT',   'BA1', DATE '2078-06-01', DATE '2079-03-31');
SELECT pg_temp.contratto('PGTAP_SOV_B_PERP', 'DRAFT',   'BA1', DATE '2086-01-01', DATE '2086-12-31');
SELECT pg_temp.contratto('PGTAP_SOV_B_ESCE', 'DRAFT',   'BA1', DATE '2080-07-01', DATE '2080-09-30');
SELECT pg_temp.contratto('PGTAP_SOV_D1',     'DRAFT',   'BA1', DATE '2082-01-01', DATE '2082-12-31');

-- ============================================================
-- Forma
-- ============================================================

-- 1) ⚠️ pg_get_function_identity_arguments include i NOMI dei parametri.
SELECT is(
    (SELECT pg_get_function_identity_arguments(p.oid)
       FROM pg_proc p JOIN pg_namespace n ON n.oid = p.pronamespace
      WHERE n.nspname = 'script' AND p.proname = 'fn_check_contratto_sovrapposto'),
    'p_billing_account_id bigint, p_istanza_utility_id bigint, p_utility_id integer, p_ambito character varying, p_valido_dal date, p_valido_al date',
    '1) script.fn_check_contratto_sovrapposto esiste, con la sola quintupla come parametri');

-- 2) Si conta la CHIAMATA (commenti tolti, nome seguito da «(»), non la menzione.
SELECT is(
    (SELECT string_agg(n.nspname || '.' || p.proname, ', ' ORDER BY n.nspname, p.proname)
       FROM pg_proc p JOIN pg_namespace n ON n.oid = p.pronamespace
      WHERE regexp_replace(p.prosrc, '--[^\n]*', '', 'g') ~ 'fn_check_contratto_sovrapposto\s*\('),
    'script.fn_available_actions_contratto, vendite.trgfn_contratti_guard_transizione_stato',
    '2) la check la chiamano la capability e il guard di transizione, e nessun altro');

-- ============================================================
-- Sopra un ATTIVO
-- ============================================================

SELECT is((pg_temp.azione_attiva('PGTAP_SOV_B_OVL') ->> 'enabled')::boolean, false,
    '3) bozza sovrapposta a un ATTIVO: «Attiva» spento');

SELECT is(pg_temp.motivo_sovrapposto('PGTAP_SOV_B_OVL'),
    'CONTRATTO_SOVRAPPOSTO | vendite.contratti.azione_reason.contratto_sovrapposto | ["PGTAP_SOV_INC"]',
    '4) il motivo e'' CONTRATTO_SOVRAPPOSTO e nomina il contratto in conflitto');

CREATE TEMP TABLE tmp_sov_esito AS
SELECT pg_temp.attiva('PGTAP_SOV_B_OVL') AS esito;

SELECT is(split_part((SELECT esito FROM tmp_sov_esito), '|', 1) || '|'
          || split_part((SELECT esito FROM tmp_sov_esito), '|', 2),
    'P0001|E_CONTRATTO_OVERLAP_ESISTENTE',
    '5) l''attivazione e'' rifiutata dal guard col codice registrato, non dal 23P01 dell''EXCLUDE');

SELECT matches((SELECT esito FROM tmp_sov_esito), 'PGTAP_SOV_INC',
    '6) il messaggio nomina il contratto in conflitto');

-- ============================================================
-- Accesi
-- ============================================================

SELECT is((pg_temp.azione_attiva('PGTAP_SOV_B_DOPO') ->> 'enabled')::boolean, true,
    '7) periodo che non si sovrappone: «Attiva» acceso');

SELECT is((pg_temp.azione_attiva('PGTAP_SOV_B_AMB') ->> 'enabled')::boolean, true,
    '8) stesso periodo, ambito diverso: «Attiva» acceso');

SELECT is((pg_temp.azione_attiva('PGTAP_SOV_B_IST') ->> 'enabled')::boolean, true,
    '9) stesso periodo, istanza diversa: «Attiva» acceso');

SELECT is(pg_temp.attiva('PGTAP_SOV_B_IST'), 'OK',
    '10) stesso periodo, istanza diversa: l''attivazione passa');

-- ============================================================
-- La quintupla e' quella di NEW
-- ============================================================
-- ⭐ La prova che vale e' la STESSA istruzione: con la riga riletta per id il
--   guard giudicherebbe le date di ieri, e i due esiti qui sotto si invertirebbero.

SELECT is(split_part(pg_temp.attiva('PGTAP_SOV_B_DOPO', DATE '2080-06-01', DATE '2080-08-31'), '|', 2),
    'E_CONTRATTO_OVERLAP_ESISTENTE',
    '11) spostato sopra INC nello stesso UPDATE che lo attiva: rifiutato col codice');

SELECT is(pg_temp.attiva('PGTAP_SOV_B_ESCE', DATE '2084-01-01', DATE '2084-12-31'), 'OK',
    '12) spostato fuori da INC nello stesso UPDATE che lo attiva: passa');

-- ============================================================
-- Altri vincolanti
-- ============================================================

SELECT is(pg_temp.motivo_sovrapposto('PGTAP_SOV_B_CES'),
    'CONTRATTO_SOVRAPPOSTO | vendite.contratti.azione_reason.contratto_sovrapposto | ["PGTAP_SOV_CES"]',
    '13) sopra un CESSATO: spento, il motivo nomina il cessato (vincolante anche lui)');

SELECT is(pg_temp.motivo_sovrapposto('PGTAP_SOV_B_PERP'),
    'CONTRATTO_SOVRAPPOSTO | vendite.contratti.azione_reason.contratto_sovrapposto | ["PGTAP_SOV_PERP"]',
    '14) sopra un ATTIVO perpetuo (valido_al NULL): spento, il motivo nomina il perpetuo');

-- ============================================================
-- Bozza su bozza
-- ============================================================

SELECT lives_ok(
    $$SELECT pg_temp.contratto('PGTAP_SOV_D2', 'DRAFT', 'BA1', DATE '2082-06-01', DATE '2082-12-31')$$,
    '15) una bozza sovrapposta a un''altra bozza nasce');

SELECT is((pg_temp.azione_attiva('PGTAP_SOV_D2') ->> 'enabled')::boolean, true,
    '16) sovrapposta a una sola bozza: «Attiva» acceso (una bozza non e'' vincolante)');

SELECT is(pg_temp.attiva('PGTAP_SOV_D2'), 'OK',
    '17) sovrapposta a una sola bozza: l''attivazione passa');

SELECT is(pg_temp.motivo_sovrapposto('PGTAP_SOV_D1'),
    'CONTRATTO_SOVRAPPOSTO | vendite.contratti.azione_reason.contratto_sovrapposto | ["PGTAP_SOV_D2"]',
    '18) attivata D2, la bozza D1 ha «Attiva» spento e il motivo nomina D2');

-- ============================================================
-- La difesa dura
-- ============================================================

-- 19) Nessuna transizione, nessun guard: un contratto che NASCE vincolante sopra
--     INC lo ferma l'EXCLUDE, che resta.
SELECT throws_ok(
    $$SELECT pg_temp.contratto('PGTAP_SOV_NATO_ATTIVO', 'ATTIVO', 'BA1', DATE '2080-03-01', DATE '2080-04-30')$$,
    '23P01',
    NULL,
    '19) un INSERT diretto in ATTIVO sopra INC: lo ferma l''EXCLUDE (difesa dura)');

SELECT is(
    (SELECT s.codice_interno::text
       FROM vendite.contratti c
       JOIN config.stati_doc_contratti s ON s.id = c.stato_doc_contratto_id
      WHERE c.numero = 'PGTAP_SOV_B_OVL'),
    'DRAFT',
    '20) dopo il rifiuto la bozza sovrapposta e'' ancora in bozza');

SELECT * FROM finish();
ROLLBACK;
