-- ------------------------------------------------------------
-- SPDX-License-Identifier: AGPL-3.0-or-later
-- pgTAP test per Zero ERP
--
-- Test: la riga di listino citata per il prezzo e' coerente con la riga che
--   la cita (vendite.trgfn_attivita_guard_listino_riga, predicato
--   vendite.fn_check_listino_provenienza) e, dal suo lato, non cambia identita'
--   (lock di colonna su vendite.listini_righe).
-- Riferimento: decisione di Tid, 2026-10-15 — «versione e riga di listino di
--   una riga di commessa possono divergere di proposito?» -> «no».
--   changeSet 20261015-20/-21/-22, righe di dbops.automation_lock_columns.
--   rev 2026-10-16 (§6 del brief, secondo giro, 20261016-01…04): la riga di
--   listino porta la sua versione (D-2, CHECK), il listino e' dell'emittente
--   della commessa (D-3), mai un prezzo da una versione in BOZZA (D-4: sulla
--   riga e nel risolutore). Predicato vendite.fn_check_listino_provenienza.
--   Brief: brief-db-coerenza-listino-della-riga-di-commessa.
-- rev 2026-10-26 (brief-modello-documento-vendita §14, giro 10): la commessa
--   va a PRONTA_FATTURAZIONE con dbops.fn_pgtap_porta_a_stato (dal verbo, con
--   l'azione cambia_stato_commessa concessa dalla fixture), non piu' con un
--   UPDATE dello stato, che la porta rifiuta (E_DOC_STATO_SOLO_DAL_VERBO).
-- rev 2026-10-28 (brief-modello-documento-vendita §16, giro 12): la versione in
--   BOZZA dei test 13-14 nasce senza la colonna di stato (una versione nasce BOZZA).
--
-- Semantica attesa (il contratto, non l'implementazione):
--   - una riga di commessa o un'attivita' fatturabile che cita una riga di
--     listino ne ha l'articolo e l'unita' di misura e, la commessa, la
--     versione: altrimenti E_ATTIVITA_LISTINO_RIGA_INCOERENTE;
--   - la versione senza riga e' lecita; la riga senza versione, sulla
--     commessa, no (CHECK chk_commesse_attivita_listino_riga_con_versione);
--   - il listino (della versione, o della riga) e' dell'emittente della
--     commessa: altrimenti E_ATTIVITA_LISTINO_EMITTENTE_DIVERSO, anche con la
--     sola versione;
--   - la versione non e' in BOZZA: altrimenti E_ATTIVITA_LISTINO_VERSIONE_BOZZA;
--     e il risolutore non da' prezzi da una versione preferita in BOZZA
--     (esito E_PREZZO_LISTINO_VERSIONE_BOZZA);
--   - il predicato legge listini e commessa senza la RLS di chi scrive
--     (SECURITY DEFINER con search_path bloccato);
--   - una riga di listino non cambia articolo, unita' di misura o versione:
--     E_LISTINO_RIGA_IDENTITA_IMMUTABILE.
--
-- Elenco test (plan 15):
--   1) il predicato e' SECURITY DEFINER con search_path che comincia da
--      pg_catalog
--   2) il guard e' montato sulle due tabelle, AFTER INSERT OR UPDATE
--   3) coerente: la riga di commessa nasce con R1 (articolo, UoM, versione)
--   4) articolo diverso da quello della riga di listino -> rifiuto
--   5) versione diversa da quella della riga di listino -> rifiuto
--   6) unita' di misura diversa (UPDATE della sola riga di listino) -> rifiuto
--   7) versione tolta, riga di listino che resta: la rifiuta il CHECK (D-2)
--   8) l'attivita' fatturabile emessa porta R1 (coerente, passa)
--   9) attivita' fatturabile spostata su una riga di altra UoM -> rifiuto
--  10) lock: la riga di listino non cambia unita' di misura
--  11) riga di listino di un listino di un'altra azienda -> rifiuto (D-3)
--  12) la sola versione, di un listino di un'altra azienda -> rifiuto (D-3)
--  13) riga di listino di una versione in BOZZA -> rifiuto (D-4)
--  14) risolutore, versione preferita in BOZZA -> esito
--      E_PREZZO_LISTINO_VERSIONE_BOZZA (D-4)
--  15) risolutore, versione preferita ATTIVA -> il prezzo di R1, nessun esito
--
-- ⚠️ I rifiuti si asseriscono sul CODICE (CONSTRAINT_NAME dell'eccezione di
--   script.fn_log_and_raise_error, o il nome del CHECK), non su un errore
--   qualunque.
-- ⚠️ Il test 10 vuole il trigger generato dal lock di colonna: in CI lo crea
--   ci_apply; su dev il job automations_lock_columns (o
--   CALL maintenance.proc_automations_lock_columns_job()).
-- ------------------------------------------------------------

BEGIN;

-- ⚠️ Vincoli DIFFERITI: in testa. Gli helper aprono e RICHIUDONO da se' la
--   finestra dove serve (e' il loro contratto).
SET CONSTRAINTS ALL IMMEDIATE;

-- Il contesto lo aprono i DO qui sotto, una volta per azienda: quella
--   dell'altra azienda per crearne il listino, poi quella del test.

SELECT plan(15);

-- ============================================================
-- Fixture
-- ============================================================

-- Due aziende, costruite PRIMA del contesto (fn_pgtap_crea_mondo_cliente: «una
-- seconda azienda si costruisce coi builder atomici, prima del contesto»; con
-- un contesto aperto il mondo usa l'azienda di chi agisce).
CREATE TEMP TABLE t_mondi AS
SELECT 'MIA'    AS lato, * FROM dbops.fn_pgtap_crea_emittente_operatore()
UNION ALL
SELECT 'ALTRUI' AS lato, * FROM dbops.fn_pgtap_crea_emittente_operatore();

-- Una utility che ammette una tipologia di listino (fn_pgtap_crea_listino la
-- pretende).
CREATE TEMP TABLE t_u_altrui AS
SELECT min(u.id) AS utility_id
  FROM config.utilities u
 WHERE EXISTS (SELECT 1 FROM config.listini_tipologie_utilities ltu
                WHERE ltu.utility_id = u.id AND ltu.attivo);

-- Il listino di ALTRUI lo crea ALTRUI (il guard emittente_scope di
-- vendite.listini non ne accetta un altro), con un articolo della sua
-- tipologia e una riga.
DO $ctx$
BEGIN
    PERFORM script.fn_pgtap_set_contesto_operatore(
        (SELECT auth_user_id FROM t_mondi WHERE lato = 'ALTRUI'));
END $ctx$;

CREATE TEMP TABLE t_l_altrui AS
SELECT * FROM dbops.fn_pgtap_crea_listino((SELECT utility_id FROM t_u_altrui), 'riga coerente altrui');

CREATE TEMP TABLE t_art_altrui AS
SELECT dbops.fn_pgtap_crea_articolo(
           ('PGT-GLA-' || substr(md5(clock_timestamp()::text), 1, 12))::varchar, false,
           p_listino_tipologia_id => (SELECT tipologia_id FROM t_l_altrui)) AS a3;

CREATE TEMP TABLE t_r_altrui AS
WITH ins AS (
    INSERT INTO vendite.listini_righe (listino_versione_id, articolo_id, uom_id, prezzo)
    SELECT l.listino_versione_id, a.a3, ar.uom_id, 30.00
      FROM t_l_altrui l, t_art_altrui a
      JOIN catalogo.articoli ar ON ar.id = a.a3
    RETURNING id
)
SELECT id AS r3 FROM ins;

-- Il contesto di MIA, e la commessa del test nel suo mondo; due listini del
-- suo emittente per la sua utility: L (quello del prezzo) e L2 (l'«altra»
-- versione).
DO $ctx$
BEGIN
    PERFORM script.fn_pgtap_set_contesto_operatore(
        (SELECT auth_user_id FROM t_mondi WHERE lato = 'MIA'));
END $ctx$;

CREATE TEMP TABLE t_c AS
SELECT * FROM dbops.fn_pgtap_crea_commessa('listino riga coerente');

CREATE TEMP TABLE t_l AS
SELECT * FROM dbops.fn_pgtap_crea_listino((SELECT utility_id FROM t_c), 'riga coerente');

CREATE TEMP TABLE t_l2 AS
SELECT * FROM dbops.fn_pgtap_crea_listino((SELECT utility_id FROM t_c), 'riga coerente bis');

-- Due articoli della tipologia del listino, nati gia' tipizzati (da usati
-- non la cambierebbero piu').
CREATE TEMP TABLE t_art AS
SELECT dbops.fn_pgtap_crea_articolo(
           ('PGT-GLR-' || substr(md5(clock_timestamp()::text), 1, 12))::varchar, false,
           p_listino_tipologia_id => (SELECT tipologia_id FROM t_l)) AS a1,
       dbops.fn_pgtap_crea_articolo(
           ('PGT-GLR-' || substr(md5(clock_timestamp()::text || 'b'), 1, 12))::varchar, false,
           p_listino_tipologia_id => (SELECT tipologia_id FROM t_l)) AS a2;

-- Tre unita' di misura: quella dell'articolo e due altre.
CREATE TEMP TABLE t_uom AS
SELECT a.uom_id AS u1,
       (SELECT u.id FROM catalogo.unita_misura u
         WHERE u.attivo AND u.id <> a.uom_id ORDER BY u.id LIMIT 1) AS u2,
       (SELECT u.id FROM catalogo.unita_misura u
         WHERE u.attivo AND u.id <> a.uom_id ORDER BY u.id OFFSET 1 LIMIT 1) AS u3
  FROM catalogo.articoli a
 WHERE a.id = (SELECT a1 FROM t_art);

-- ⚠️ 2026-11-10 (brief-db-revisione-catalogo, giro 2-bis, D25/Q24): un prezzo vale in
--   un'unita' che si converte per l'articolo per tutto il periodo della versione
--   (vendite.trgfn_listini_righe_guard_uom_periodo). La seconda unita' si mappa.
INSERT INTO catalogo.articoli_uom_operativa (articolo_id, uom_id, factor_to_base)
SELECT (SELECT a1 FROM t_art), u2, 2 FROM t_uom;

-- R1 e R2: stesso articolo, stessa versione, UoM diverse.
CREATE TEMP TABLE t_r AS
WITH ins AS (
    INSERT INTO vendite.listini_righe (listino_versione_id, articolo_id, uom_id, prezzo)
    VALUES ((SELECT listino_versione_id FROM t_l), (SELECT a1 FROM t_art),
            (SELECT u1 FROM t_uom), 10.00),
           ((SELECT listino_versione_id FROM t_l), (SELECT a1 FROM t_art),
            (SELECT u2 FROM t_uom), 20.00)
    RETURNING id, uom_id
)
SELECT (SELECT id FROM ins WHERE uom_id = (SELECT u1 FROM t_uom)) AS r1,
       (SELECT id FROM ins WHERE uom_id = (SELECT u2 FROM t_uom)) AS r2;

-- ============================================================
-- 1-2) La forma
-- ============================================================
SELECT ok(
    (SELECT p.prosecdef
            AND p.proconfig IS NOT NULL
            AND p.proconfig[1] LIKE 'search_path=pg_catalog%'
       FROM pg_proc p
      WHERE p.oid = 'vendite.fn_check_listino_provenienza(bigint, uuid, bigint, bigint, bigint)'::regprocedure),
    '1) il predicato e'' SECURITY DEFINER, search_path da pg_catalog (listini_righe ha la RLS)'
);

SELECT is(
    (SELECT string_agg(c.relname || ' ' || (t.tgtype & 1 = 1)::text      -- ROW
                                 || ' ' || (t.tgtype & 2 = 0)::text      -- AFTER
                                 || ' ' || (t.tgtype & 4 = 4)::text      -- INSERT
                                 || ' ' || (t.tgtype & 16 = 16)::text,   -- UPDATE
                       ', ' ORDER BY c.relname)
       FROM pg_trigger t
       JOIN pg_class c ON c.oid = t.tgrelid
      WHERE t.tgfoid = 'vendite.trgfn_attivita_guard_listino_riga()'::regprocedure),
    'attivita_fatturabili true true true true, commesse_attivita true true true true',
    '2) il guard e'' montato sulle due tabelle, AFTER INSERT OR UPDATE FOR EACH ROW'
);

-- ============================================================
-- 3) Coerente: nasce con R1
-- ============================================================
CREATE TEMP TABLE t_a AS
SELECT a.attivita_id
  FROM t_c c, t_l l, t_r rr,
       dbops.fn_pgtap_crea_commessa_attivita(
           p_commessa_id         => c.commessa_id,
           p_listino_versione_id => l.listino_versione_id,
           p_listino_riga_id     => rr.r1) a;

SELECT is(
    (SELECT ca.listino_riga_id FROM vendite.commesse_attivita ca
      WHERE ca.id = (SELECT attivita_id FROM t_a)),
    (SELECT r1 FROM t_r),
    '3) coerente: la riga di commessa nasce con R1 (articolo, UoM e versione di R1)'
);

-- ============================================================
-- 4-6) Incoerenti: articolo, versione, unita' di misura
-- ============================================================
SELECT is(
    dbops.fn_pgtap_codice_errore(format(
        'SELECT dbops.fn_pgtap_crea_commessa_attivita(p_commessa_id => %s, p_articolo_id => %L::uuid, p_listino_riga_id => %s)',
        (SELECT commessa_id FROM t_c), (SELECT a2 FROM t_art), (SELECT r1 FROM t_r))),
    'E_ATTIVITA_LISTINO_RIGA_INCOERENTE',
    '4) riga di listino di un altro articolo -> E_ATTIVITA_LISTINO_RIGA_INCOERENTE'
);

SELECT is(
    dbops.fn_pgtap_codice_errore(format(
        'SELECT dbops.fn_pgtap_crea_commessa_attivita(p_commessa_id => %s, p_listino_versione_id => %s, p_listino_riga_id => %s)',
        (SELECT commessa_id FROM t_c), (SELECT listino_versione_id FROM t_l2), (SELECT r1 FROM t_r))),
    'E_ATTIVITA_LISTINO_RIGA_INCOERENTE',
    '5) riga di listino di un''altra versione -> E_ATTIVITA_LISTINO_RIGA_INCOERENTE'
);

SELECT is(
    dbops.fn_pgtap_codice_errore(format(
        'UPDATE vendite.commesse_attivita SET listino_riga_id = %s WHERE id = %s',
        (SELECT r2 FROM t_r), (SELECT attivita_id FROM t_a))),
    'E_ATTIVITA_LISTINO_RIGA_INCOERENTE',
    '6) riga di listino di un''altra unita'' di misura (UPDATE della sola riga) -> E_ATTIVITA_LISTINO_RIGA_INCOERENTE'
);

-- ============================================================
-- 7) La versione si toglie, la riga resta: non piu' lecito (D-2)
-- ============================================================
SELECT is(
    dbops.fn_pgtap_codice_errore(format(
        'UPDATE vendite.commesse_attivita SET listino_versione_id = NULL WHERE id = %s',
        (SELECT attivita_id FROM t_a))),
    'chk_commesse_attivita_listino_riga_con_versione',
    '7) versione tolta, riga di listino che resta: la rifiuta il CHECK (D-2)'
);

-- ============================================================
-- 8-9) L'attivita' fatturabile
-- ============================================================
SELECT vendite.fn_link_commessa_sorgente(
    p_commessa_id      => (SELECT commessa_id FROM t_c),
    p_sorgente_tipo_id => (SELECT s.id FROM config.sorgenti s
                            WHERE s.codice_interno = 'COMMESSA' AND s.attivo),
    p_sorgente_chiave  => (SELECT commessa_id FROM t_c)::text);

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
    (SELECT af.listino_riga_id FROM vendite.attivita_fatturabili af
      WHERE af.commessa_attivita_id = (SELECT attivita_id FROM t_a)),
    (SELECT r1 FROM t_r),
    '8) l''attivita'' fatturabile emessa porta R1: coerente, passa'
);

SELECT is(
    dbops.fn_pgtap_codice_errore(format(
        'UPDATE vendite.attivita_fatturabili SET listino_riga_id = %s WHERE commessa_attivita_id = %s',
        (SELECT r2 FROM t_r), (SELECT attivita_id FROM t_a))),
    'E_ATTIVITA_LISTINO_RIGA_INCOERENTE',
    '9) attivita'' fatturabile su una riga di listino di altra unita'' di misura -> E_ATTIVITA_LISTINO_RIGA_INCOERENTE'
);

-- ============================================================
-- 10) Il lato della riga di listino: identita' immutabile
-- ============================================================
-- R2 non e' citata (i rifiuti sopra sono tornati indietro): sulla versione
-- ATTIVA il guard di stato la lascerebbe passare, e parla il lock.
SELECT is(
    dbops.fn_pgtap_codice_errore(format(
        'UPDATE vendite.listini_righe SET uom_id = %s WHERE id = %s',
        (SELECT u3 FROM t_uom), (SELECT r2 FROM t_r))),
    'E_LISTINO_RIGA_IDENTITA_IMMUTABILE',
    '10) lock: una riga di listino non cambia unita'' di misura -> E_LISTINO_RIGA_IDENTITA_IMMUTABILE'
);

-- ============================================================
-- 11-12) D-3: il listino e' dell'emittente della commessa
-- ============================================================
-- ⚠️ rev 2026-10-16 (20261016-33): come APP la riga R3 dell'altra azienda e'
--   invisibile sotto la RLS di chi agisce. Il chiamante da' quindi articolo e
--   versione, come fa il backend, e giudica il guard (predicato DEFINER).
--   Senza, il builder si fermava su «nessuna riga» e il guard non veniva mai
--   raggiunto: verde da owner, rosso come app.
SELECT is(
    dbops.fn_pgtap_codice_errore(format(
        'SELECT dbops.fn_pgtap_crea_commessa_attivita(p_commessa_id => %s, p_articolo_id => %L::uuid, p_listino_versione_id => %s, p_listino_riga_id => %s)',
        (SELECT commessa_id FROM t_c), (SELECT a3 FROM t_art_altrui),
        (SELECT listino_versione_id FROM t_l_altrui), (SELECT r3 FROM t_r_altrui))),
    'E_ATTIVITA_LISTINO_EMITTENTE_DIVERSO',
    '11) riga di listino di un listino di un''altra azienda -> E_ATTIVITA_LISTINO_EMITTENTE_DIVERSO'
);

SELECT is(
    dbops.fn_pgtap_codice_errore(format(
        'SELECT dbops.fn_pgtap_crea_commessa_attivita(p_commessa_id => %s, p_articolo_id => %L::uuid, p_listino_versione_id => %s)',
        (SELECT commessa_id FROM t_c), (SELECT a1 FROM t_art), (SELECT listino_versione_id FROM t_l_altrui))),
    'E_ATTIVITA_LISTINO_EMITTENTE_DIVERSO',
    '12) la sola versione, di un listino di un''altra azienda -> E_ATTIVITA_LISTINO_EMITTENTE_DIVERSO'
);

-- ============================================================
-- 13-15) D-4: mai un prezzo da una versione in BOZZA
-- ============================================================
-- Una versione in BOZZA del listino L, nel futuro (non si sovrappone a
-- quella attiva), con la sua riga per a1 nella UoM u1.
CREATE TEMP TABLE t_vb AS
WITH ins AS (
    INSERT INTO vendite.listini_versioni (listino_id, codice_versione, valido_dal)
    SELECT l.listino_id, 'PGT_BOZZA', '2099-01-01'::date FROM t_l l
    RETURNING id
)
SELECT id AS vb FROM ins;

CREATE TEMP TABLE t_rb AS
WITH ins AS (
    INSERT INTO vendite.listini_righe (listino_versione_id, articolo_id, uom_id, prezzo)
    SELECT (SELECT vb FROM t_vb), a.a1, u.u1, 99.00 FROM t_art a, t_uom u
    RETURNING id
)
SELECT id AS rb FROM ins;

SELECT is(
    dbops.fn_pgtap_codice_errore(format(
        'SELECT dbops.fn_pgtap_crea_commessa_attivita(p_commessa_id => %s, p_listino_riga_id => %s)',
        (SELECT commessa_id FROM t_c), (SELECT rb FROM t_rb))),
    'E_ATTIVITA_LISTINO_VERSIONE_BOZZA',
    '13) riga di listino di una versione in BOZZA -> E_ATTIVITA_LISTINO_VERSIONE_BOZZA'
);

SELECT is(
    (SELECT e.esito_codice
       FROM t_c c, t_art a, t_uom u, t_vb v,
            vendite.fn_resolve_prezzo_listino_v2_esito(
                a.a1, u.u1, script.fn_data_operativa(), c.billing_account_id,
                c.utility_id, c.emittente_soggetto_ruolo_id, NULL, NULL, v.vb) e),
    'E_PREZZO_LISTINO_VERSIONE_BOZZA',
    '14) risolutore, versione preferita in BOZZA -> esito E_PREZZO_LISTINO_VERSIONE_BOZZA'
);

SELECT is(
    (SELECT coalesce(e.esito_codice, 'nessun esito') || ' ' || (e.listino_riga_id = rr.r1)::text
       FROM t_c c, t_art a, t_uom u, t_l l, t_r rr,
            vendite.fn_resolve_prezzo_listino_v2_esito(
                a.a1, u.u1, script.fn_data_operativa(), c.billing_account_id,
                c.utility_id, c.emittente_soggetto_ruolo_id, NULL, NULL, l.listino_versione_id) e),
    'nessun esito true',
    '15) risolutore, versione preferita ATTIVA -> la riga R1, nessun esito'
);

SELECT * FROM finish();
ROLLBACK;
