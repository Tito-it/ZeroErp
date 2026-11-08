-- ------------------------------------------------------------
-- SPDX-License-Identifier: AGPL-3.0-or-later
-- pgTAP test per Zero ERP
--
-- pgtap-runner: owner
-- pgtap-runner-motivo: la fixture semina su dbops.processi / processi_bersagli
--   (cataloghi su cui l'app ha SELECT-only: li scrive il mirror CSV) e fa DDL
--   (una tabella di prova con policy, RLS e trigger, per il presidio della difesa).
--
-- Il processo vivo: il ritiro ha una sede sola, la data, e la regola e'
-- script.fn_e_obsoleto (vivo = data vuota o non ancora arrivata).
--   Brief: brief-db-revisione-dbops, giro 9, blocco 9a (§24: D11, Q2, N1, N2;
--   Q14 ⑤ e N3). changeSet 20261109-40 … -47, processi.csv, processi_bersagli.csv.
--
-- I casi si COSTRUISCONO (processi di prova con la data di oggi letta da
-- script.fn_data_operativa): nessun test legge le righe del catalogo per
-- dedurre la regola.
--
-- Elenco test (plan 26):
--   il catalogo
--    1) attivo = false senza data -> chk_processi_ritiro_con_data
--    2) un ritirato con sveglia senza accensione -> chk_processi_accensione
--    3) chk_processi_accensione convalidato
--   la sveglia e la scelta a mano
--    4) ritiro programmato: la sveglia risponde
--    5) ritiro raggiunto oggi: E_PROCESSO_SENZA_SVEGLIA
--    6) attivo = false con ritiro programmato: vivo (la data e' l'unica sede)
--    7) ritiro programmato: la scelta a mano e' ammessa
--    8) ritiro raggiunto: la scelta a mano -> E_PROCESSO_SENZA_SVEGLIA
--    9) la regola sui valori con un ritiro futuro non e' «senza sveglia»
--   il panorama, il roster e i presidi
--   10) il panorama mostra il ritiro programmato
--   11) ... e non il ritiro raggiunto
--   12) ... e mostra il vivo con attivo = false
--   13) vw_processi_dominio_senza_identita vede il ritiro programmato
--   14) ... e non il raggiunto
--   15) vw_processi_dominio_senza_emittente vede il ritiro programmato
--   16) ... e non il raggiunto
--   17) i lettori del ritiro chiamano script.fn_e_obsoleto e non leggono la presenza della data
--   il presidio della difesa (Q14 ⑤, N3)
--   18) tabella con policy e RLS, senza guard: compare (scrittura scoperta)
--   19) un'omonima del guard in un altro schema non e' una difesa
--   20) il guard vero ma disattivato non e' una difesa
--   21) il guard vero, acceso, su INSERT e UPDATE: la tabella esce
--   22) la porta dichiarata DEFINER, con RLS e policy FOR ALL: la tabella esce
--   23) la porta dichiarata ma INVOKER: compare, e il motivo lo dice
--   24) la porta con la RLS spenta: compare
--   25) dbops.coda_lavori (porta dbops.fn_accoda_lavoro) non e' nel presidio
--   26) un processo a ritiro raggiunto non porta i suoi bersagli nel presidio
-- ------------------------------------------------------------

BEGIN;

DO $ctx$ BEGIN PERFORM script.fn_pgtap_set_contesto_operatore(); END $ctx$;

SET CONSTRAINTS ALL IMMEDIATE;

SELECT plan(26);

-- Il CODICE dell'errore viaggia nel canale CONSTRAINT_NAME dell'eccezione
-- P0001 (fn_log_and_raise_error); per un CHECK e' il nome del vincolo.
CREATE OR REPLACE FUNCTION pg_temp.codice_errore(p_sql text) RETURNS text
LANGUAGE plpgsql AS $$
DECLARE v_c text;
BEGIN
    EXECUTE p_sql;
    RETURN NULL;
EXCEPTION WHEN SQLSTATE 'P0001' OR SQLSTATE '23514' THEN
    GET STACKED DIAGNOSTICS v_c = CONSTRAINT_NAME;
    RETURN v_c;
END $$;

-- ============================================================
-- Il catalogo
-- ============================================================
SELECT is(
    pg_temp.codice_errore($$
        INSERT INTO dbops.processi (id, codice, descrizione, classe, canale, attivo,
                                    acceso_in_sviluppo, acceso_in_produzione, spegnibile,
                                    causa_fallimento, accendibile_in_produzione)
        VALUES (9700, 'PGTAP-VIVO-SENZA-DATA', 'spento senza data', 'MANUTENZIONE', 'COMMAND', false,
                true, true, true, 'PROGRAMMA', true)$$),
    'chk_processi_ritiro_con_data',
    '1. attivo = false senza la data del ritiro e'' rifiutato');

SELECT is(
    pg_temp.codice_errore($$
        INSERT INTO dbops.processi (id, codice, descrizione, classe, canale, obsoleto_dal,
                                    causa_fallimento)
        VALUES (9700, 'PGTAP-VIVO-SENZA-ACC', 'ritirato senza accensione', 'MANUTENZIONE', 'COMMAND',
                DATE '2026-01-01', 'PROGRAMMA')$$),
    'chk_processi_accensione',
    '2. un processo con sveglia dichiara l''accensione anche da ritirato');

SELECT is(
    (SELECT c.convalidated FROM pg_constraint c
      WHERE c.conrelid = 'dbops.processi'::regclass AND c.conname = 'chk_processi_accensione'),
    true,
    '3. chk_processi_accensione e'' convalidato (90_end/20261109-47)');

-- Tre processi DOMINIO su COMMAND, non spegnibili (la sveglia risponde true
-- qualunque sia l'ambiente), senza identita' ne' bersagli:
--   9701 ritiro programmato (fra 30 giorni), 9702 ritiro raggiunto (oggi),
--   9703 attivo = false con ritiro programmato.
INSERT INTO dbops.processi (id, codice, descrizione, classe, canale, attivo, obsoleto_dal,
                            acceso_in_sviluppo, acceso_in_produzione, spegnibile,
                            causa_fallimento, accendibile_in_produzione)
VALUES (9701, 'PGTAP-VIVO-PROGRAMMATO', 'ritiro programmato', 'DOMINIO', 'COMMAND', true,
        script.fn_data_operativa() + 30, true, true, false, 'PROGRAMMA', true),
       (9702, 'PGTAP-VIVO-RAGGIUNTO', 'ritiro raggiunto oggi', 'DOMINIO', 'COMMAND', true,
        script.fn_data_operativa(), true, true, false, 'PROGRAMMA', true),
       (9703, 'PGTAP-VIVO-SPENTO', 'attivo false, ritiro programmato', 'DOMINIO', 'COMMAND', false,
        script.fn_data_operativa() + 30, true, true, false, 'PROGRAMMA', true);

-- ============================================================
-- La sveglia e la scelta a mano
-- ============================================================
SELECT is(maintenance.fn_sveglia_accesa('PGTAP-VIVO-PROGRAMMATO'), true,
    '4. ritiro programmato: la sveglia risponde fino al suo giorno');

SELECT is(pg_temp.codice_errore($$SELECT maintenance.fn_sveglia_accesa('PGTAP-VIVO-RAGGIUNTO')$$),
    'E_PROCESSO_SENZA_SVEGLIA',
    '5. ritiro raggiunto oggi: senza sveglia');

SELECT is(maintenance.fn_sveglia_accesa('PGTAP-VIVO-SPENTO'), true,
    '6. attivo = false con ritiro programmato: vivo, la data e'' l''unica sede del ritiro');

SELECT is(pg_temp.codice_errore($$SELECT dbops.fn_imposta_accensione_processo(
              'PGTAP-VIVO-PROGRAMMATO', true, 'pgTAP: ritiro programmato')$$),
    NULL,
    '7. ritiro programmato: la scelta a mano e'' ammessa');

SELECT is(pg_temp.codice_errore($$SELECT dbops.fn_imposta_accensione_processo(
              'PGTAP-VIVO-RAGGIUNTO', true, 'pgTAP: ritiro raggiunto')$$),
    'E_PROCESSO_SENZA_SVEGLIA',
    '8. ritiro raggiunto: niente scelta a mano');

SELECT is(dbops.fn_processo_acceso_su_valori('COMMAND', script.fn_data_operativa() + 1,
                                              true, true, false, NULL, 'SVILUPPO', true),
          true,
          '9. la regola sui valori: un ritiro futuro ha la sveglia (default di sviluppo)');

-- ============================================================
-- Il panorama, il roster e i presidi
-- ============================================================
SELECT ok(EXISTS (SELECT 1 FROM dbops.vw_processi_programmazione
                   WHERE processo_codice = 'PGTAP-VIVO-PROGRAMMATO'),
    '10. il panorama mostra il processo a ritiro programmato');

SELECT ok(NOT EXISTS (SELECT 1 FROM dbops.vw_processi_programmazione
                       WHERE processo_codice = 'PGTAP-VIVO-RAGGIUNTO'),
    '11. il panorama non mostra il processo a ritiro raggiunto');

SELECT ok(EXISTS (SELECT 1 FROM dbops.vw_processi_programmazione
                   WHERE processo_codice = 'PGTAP-VIVO-SPENTO'),
    '12. il panorama mostra il vivo con attivo = false');

SELECT ok(EXISTS (SELECT 1 FROM dbops.vw_processi_dominio_senza_identita
                   WHERE processo_codice = 'PGTAP-VIVO-PROGRAMMATO'),
    '13. senza identita'': il ritiro programmato e'' ancora un processo da servire');

SELECT ok(NOT EXISTS (SELECT 1 FROM dbops.vw_processi_dominio_senza_identita
                       WHERE processo_codice = 'PGTAP-VIVO-RAGGIUNTO'),
    '14. senza identita'': il ritiro raggiunto esce');

SELECT ok(EXISTS (SELECT 1 FROM dbops.vw_processi_dominio_senza_emittente
                   WHERE processo_codice = 'PGTAP-VIVO-PROGRAMMATO'),
    '15. senza emittente: il ritiro programmato compare (nessun bersaglio)');

SELECT ok(NOT EXISTS (SELECT 1 FROM dbops.vw_processi_dominio_senza_emittente
                       WHERE processo_codice = 'PGTAP-VIVO-RAGGIUNTO'),
    '16. senza emittente: il ritiro raggiunto esce');

-- ⭐ Il presidio sul testo: i lettori del ritiro leggono la regola, non la
--   presenza della data. dbops.fn_processo_acceso_dichiarato passa il valore
--   alla regola e non ne fa parte.
SELECT is_empty(
    $$WITH lettori (oggetto, testo) AS (
          SELECT p.oid::regprocedure::text,
                 coalesce(p.prosrc, '') || coalesce(pg_get_function_sqlbody(p.oid), '')
            FROM pg_proc p
           WHERE p.oid IN ('dbops.fn_processo_acceso_su_valori'::regproc,
                           'dbops.trgfn_processi_accensione_guard'::regproc,
                           'maintenance.fn_sveglia_accesa'::regproc,
                           'script.fn_crea_utente_tecnico'::regproc,
                           'script.fn_scope_identita_processo'::regproc)
          UNION ALL
          SELECT c.oid::regclass::text, pg_get_viewdef(c.oid)
            FROM pg_class c
           WHERE c.oid IN ('dbops.vw_emittenti_non_serviti'::regclass,
                           'dbops.vw_processi_dominio_senza_difesa'::regclass,
                           'dbops.vw_processi_dominio_senza_emittente'::regclass,
                           'dbops.vw_processi_dominio_senza_identita'::regclass,
                           'dbops.vw_processi_dominio_su_pgagent'::regclass,
                           'dbops.vw_processi_programmazione'::regclass,
                           'dbops.vw_processi_roster'::regclass))
      SELECT oggetto FROM lettori
       WHERE testo !~ 'fn_e_obsoleto'
          OR testo ~* 'obsoleto_dal\)?\s+IS\s+(NOT\s+)?NULL'$$,
    '17. i dodici lettori del ritiro chiamano script.fn_e_obsoleto e non leggono la presenza della data');

-- ============================================================
-- Il presidio della difesa (Q14 ⑤, N3)
-- ============================================================
-- ⚠️ La tabella e' vera (relkind 'r', schema per nome), nasce qui e muore col
--   ROLLBACK: la condizione che il presidio giudica la possiede il test.
CREATE TABLE dbops.pgtap_bersaglio_difesa (
    id                   bigint PRIMARY KEY,
    emittente_fiscale_id bigint
);
CREATE POLICY pgtap_difesa_tutto ON dbops.pgtap_bersaglio_difesa
    FOR ALL USING (true) WITH CHECK (true);
ALTER TABLE dbops.pgtap_bersaglio_difesa ENABLE ROW LEVEL SECURITY;

INSERT INTO dbops.processi (id, codice, descrizione, classe, canale,
                            acceso_in_sviluppo, acceso_in_produzione, spegnibile,
                            causa_fallimento, accendibile_in_produzione)
VALUES (9704, 'PGTAP-VIVO-DIFESA', 'processo con un bersaglio da difendere', 'DOMINIO', 'COMMAND',
        true, true, true, 'PROGRAMMA', true);
INSERT INTO dbops.processi_bersagli (id, processo_id, schema_tabella, nome_tabella,
                                     emittente_via, emittente_colonna, note)
VALUES (9711, 9704, 'dbops', 'pgtap_bersaglio_difesa', 'fiscale', 'emittente_fiscale_id', 'pgTAP'),
       (9712, 9702, 'dbops', 'pgtap_bersaglio_difesa', 'fiscale', 'emittente_fiscale_id', 'pgTAP');

CREATE OR REPLACE FUNCTION pg_temp.manca(p_codice text) RETURNS text
LANGUAGE sql AS $$
    SELECT string_agg(manca, ' | ') FROM dbops.vw_processi_dominio_senza_difesa
     WHERE processo_codice = p_codice
$$;

SELECT is(pg_temp.manca('PGTAP-VIVO-DIFESA'), 'write-guard (scrittura scoperta)',
    '18. policy e RLS senza guard: la scrittura e'' scoperta');

-- Un'omonima del guard in un altro schema.
CREATE FUNCTION dbops.trgfn_guard_emittente_scope() RETURNS trigger
LANGUAGE plpgsql AS $$ BEGIN RETURN NEW; END $$;
CREATE TRIGGER trg_pgtap_omonima BEFORE INSERT OR UPDATE ON dbops.pgtap_bersaglio_difesa
    FOR EACH ROW EXECUTE FUNCTION dbops.trgfn_guard_emittente_scope();

SELECT is(pg_temp.manca('PGTAP-VIVO-DIFESA'), 'write-guard (scrittura scoperta)',
    '19. un''omonima del guard in un altro schema non e'' una difesa');

DROP TRIGGER trg_pgtap_omonima ON dbops.pgtap_bersaglio_difesa;

-- Il guard vero, disattivato (nessuna scrittura lo fa scattare).
CREATE TRIGGER trg_pgtap_guard BEFORE INSERT OR UPDATE ON dbops.pgtap_bersaglio_difesa
    FOR EACH ROW EXECUTE FUNCTION script.trgfn_guard_emittente_scope();
ALTER TABLE dbops.pgtap_bersaglio_difesa DISABLE TRIGGER trg_pgtap_guard;

SELECT is(pg_temp.manca('PGTAP-VIVO-DIFESA'), 'write-guard (scrittura scoperta)',
    '20. il guard vero ma disattivato non e'' una difesa');

ALTER TABLE dbops.pgtap_bersaglio_difesa ENABLE TRIGGER trg_pgtap_guard;

SELECT is(pg_temp.manca('PGTAP-VIVO-DIFESA'), NULL,
    '21. il guard vero, acceso, su INSERT e UPDATE: la tabella esce dal presidio');

DROP TRIGGER trg_pgtap_guard ON dbops.pgtap_bersaglio_difesa;

UPDATE dbops.processi_bersagli SET porta_scrittura = 'dbops.fn_accoda_lavoro' WHERE id = 9711;

SELECT is(pg_temp.manca('PGTAP-VIVO-DIFESA'), NULL,
    '22. la porta DEFINER dichiarata, con RLS e policy FOR ALL: la tabella esce');

UPDATE dbops.processi_bersagli SET porta_scrittura = 'dbops.fn_get_lookup_codici' WHERE id = 9711;

SELECT matches(pg_temp.manca('PGTAP-VIVO-DIFESA'), 'non e'' SECURITY DEFINER',
    '23. una porta INVOKER non e'' una difesa, e il motivo lo dice');

UPDATE dbops.processi_bersagli SET porta_scrittura = 'dbops.fn_accoda_lavoro' WHERE id = 9711;
ALTER TABLE dbops.pgtap_bersaglio_difesa DISABLE ROW LEVEL SECURITY;

SELECT matches(pg_temp.manca('PGTAP-VIVO-DIFESA'), 'ROW LEVEL SECURITY non e'' attiva',
    '24. la porta con la RLS spenta non basta');

SELECT ok(NOT EXISTS (SELECT 1 FROM dbops.vw_processi_dominio_senza_difesa
                       WHERE schema_tabella = 'dbops' AND nome_tabella = 'coda_lavori'),
    '25. dbops.coda_lavori, difesa dalla porta dbops.fn_accoda_lavoro e dalla policy, non e'' nel presidio');

SELECT is(pg_temp.manca('PGTAP-VIVO-RAGGIUNTO'), NULL,
    '26. un processo a ritiro raggiunto non porta i suoi bersagli nel presidio');

SELECT * FROM finish();

ROLLBACK;
