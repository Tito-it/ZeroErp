-- ------------------------------------------------------------
-- SPDX-License-Identifier: AGPL-3.0-or-later
-- pgTAP test per Zero ERP
--
-- Test: la provenienza del prezzo delle righe di documento (origine, versione
--   e riga di listino, contesto del resolver): il dominio unico delle origini,
--   la coerenza col prezzo, la derivazione e la decadenza, il guard sulla riga
--   di listino, il kit a COMPONENTI.
-- Riferimento: brief-db-provenienza-prezzo-segue-il-prezzo §8 (giro 1),
--   decisione B di Tid (2026-10-09), D-1 … D-3 (2026-11-13);
--   changeSet 20261113-01 … -12.
--
-- Semantica attesa (il contratto, non l'implementazione):
--   - le origini ammesse sono un elenco solo (vendite.fn_origine_prezzo_ammessa),
--     letto dai CHECK di righe, componenti, commessa e attivita' fatturabili;
--   - senza prezzo nessuna provenienza; con un prezzo un'origine; una riga di
--     listino porta la sua versione; MANUALE e COMPONENTI non citano listino
--     (vendite.fn_provenienza_prezzo_coerente, CHECK chk_<t>_provenienza_prezzo);
--   - un prezzo scritto senza origine e' MANUALE;
--   - un prezzo da listino cambiato senza dichiarare una provenienza nuova
--     torna MANUALE, con riga, versione e contesto a NULL; chi scrive prezzo e
--     provenienza nuova nella stessa istruzione la tiene; un cambio che non
--     tocca prezzo, articolo o unita' di misura non la tocca;
--   - la riga di listino citata e' dell'articolo e dell'unita' di misura
--     operativa della riga, dell'azienda del documento, mai di una bozza;
--   - il prezzo del kit scritto dalla somma dei componenti e' COMPONENTI.
--
-- Elenco test (plan 17):
--   1) l'elenco delle origini: sette valori e NULL, nient'altro
--   2) la coerenza, sui casi del modello (funzione pura)
--   3) le colonne nuove sulle dieci tabelle
--   4) i dieci CHECK di coerenza
--   5) i sette CHECK sulle origini leggono l'elenco unico
--   6) i due trigger, montati sulle dieci tabelle (per funzione)
--   7) una riga d'ordine scritta senza provenienza e' MANUALE
--   8) la provenienza da listino dichiarata e coerente passa
--   9) cambio della sola quantita': la provenienza resta
--  10) cambio del solo prezzo: la provenienza decade a MANUALE, senza listino
--  11) prezzo e provenienza nuovi nella stessa istruzione: la provenienza resta
--  12) MANUALE con una riga di listino -> CHECK chk_ordini_righe_provenienza_prezzo
--  13) riga di listino di un altro articolo -> E_ATTIVITA_LISTINO_RIGA_INCOERENTE
--  14) versione di un listino di un'altra azienda -> E_ATTIVITA_LISTINO_EMITTENTE_DIVERSO
--  15) riga di listino di una versione in BOZZA -> E_ATTIVITA_LISTINO_VERSIONE_BOZZA
--  16) il prezzo del kit dalla somma dei componenti e' COMPONENTI, senza listino
--  17) la commessa ammette LISTINO_BUNDLE e COMPONENTI (CHECK sull'elenco unico)
--
-- ⚠️ I rifiuti si asseriscono sul CODICE (dbops.fn_pgtap_codice_errore: il
--   CONSTRAINT_NAME dell'eccezione, o il nome del CHECK), non su un errore
--   qualunque.
-- ⚠️ Il ramo «senza prezzo, nessuna provenienza» del trigger non si prova qui
--   sulla riga d'ordine (prezzo NOT NULL): lo copre il test 2 sulla regola, e
--   le righe di contratto e DDT lo percorrono nei loro test.
-- ------------------------------------------------------------

BEGIN;

SET CONSTRAINTS ALL IMMEDIATE;

SELECT plan(17);

-- ============================================================
-- Fixture
-- ============================================================

-- Due aziende, costruite PRIMA del contesto.
CREATE TEMP TABLE t_mondi AS
SELECT 'MIA'    AS lato, * FROM dbops.fn_pgtap_crea_emittente_operatore()
UNION ALL
SELECT 'ALTRUI' AS lato, * FROM dbops.fn_pgtap_crea_emittente_operatore();

CREATE TEMP TABLE t_u AS
SELECT min(u.id) AS utility_id
  FROM config.utilities u
 WHERE EXISTS (SELECT 1 FROM config.listini_tipologie_utilities ltu
                WHERE ltu.utility_id = u.id AND ltu.attivo);

-- Il listino dell'altra azienda lo crea lei.
DO $ctx$
BEGIN
    PERFORM script.fn_pgtap_set_contesto_operatore(
        (SELECT auth_user_id FROM t_mondi WHERE lato = 'ALTRUI'));
END $ctx$;

CREATE TEMP TABLE t_l_altrui AS
SELECT * FROM dbops.fn_pgtap_crea_listino((SELECT utility_id FROM t_u), 'provenienza altrui');

-- Il contesto del test.
DO $ctx$
BEGIN
    PERFORM script.fn_pgtap_set_contesto_operatore(
        (SELECT auth_user_id FROM t_mondi WHERE lato = 'MIA'));
END $ctx$;

CREATE TEMP TABLE t_l AS
SELECT * FROM dbops.fn_pgtap_crea_listino((SELECT utility_id FROM t_u), 'provenienza');

-- Due articoli della tipologia del listino: a1 sulla riga d'ordine, a2 per la
-- riga di listino «di un altro articolo».
CREATE TEMP TABLE t_art AS
SELECT dbops.fn_pgtap_crea_articolo(
           ('PGT-PPR-' || substr(md5(clock_timestamp()::text), 1, 12))::varchar, false,
           p_listino_tipologia_id => (SELECT tipologia_id FROM t_l)) AS a1,
       dbops.fn_pgtap_crea_articolo(
           ('PGT-PPR-' || substr(md5(clock_timestamp()::text || 'b'), 1, 12))::varchar, false,
           p_listino_tipologia_id => (SELECT tipologia_id FROM t_l)) AS a2;

-- R1 (a1) e R2 (a2) nella versione attiva, nell'unita' di misura dell'articolo.
CREATE TEMP TABLE t_r AS
WITH ins AS (
    INSERT INTO vendite.listini_righe (listino_versione_id, articolo_id, uom_id, prezzo)
    SELECT (SELECT listino_versione_id FROM t_l), a.id, a.uom_id,
           CASE WHEN a.id = (SELECT a1 FROM t_art) THEN 50.00 ELSE 60.00 END
      FROM catalogo.articoli a
     WHERE a.id IN ((SELECT a1 FROM t_art), (SELECT a2 FROM t_art))
    RETURNING id, articolo_id
)
SELECT (SELECT id FROM ins WHERE articolo_id = (SELECT a1 FROM t_art)) AS r1,
       (SELECT id FROM ins WHERE articolo_id = (SELECT a2 FROM t_art)) AS r2;

-- L'ordine, in bozza, con una riga di a1 a 40 (un prezzo trattato).
CREATE TEMP TABLE t_o AS
SELECT * FROM dbops.fn_pgtap_crea_ordine_con_righe(
    'provenienza prezzo', 'DRAFT',
    p_quantita => 2, p_prezzo => 40, p_articolo_id => (SELECT a1 FROM t_art));

CREATE OR REPLACE FUNCTION pg_temp.riga()
RETURNS TABLE(origine varchar, versione bigint, riga bigint, contesto jsonb, prezzo numeric)
LANGUAGE sql AS $f$
    SELECT r.origine_prezzo, r.listino_versione_id, r.listino_riga_id,
           r.prezzo_resolver_context, r.prezzo_unitario
      FROM vendite.ordini_righe r
     WHERE r.id = (SELECT ordine_riga_id FROM t_o);
$f$;

-- ============================================================
-- 1-2) Le due regole, come funzioni pure
-- ============================================================
SELECT is(
    ARRAY(SELECT v FROM unnest(ARRAY['PROMO', 'CONTRATTO_OVERRIDE', 'CONTRATTO_LISTINO', 'CATEGORIA',
                                     'MANUALE', 'LISTINO_BUNDLE', 'COMPONENTI', 'LISTINO', 'manuale',
                                     NULL]) v
           WHERE vendite.fn_origine_prezzo_ammessa(v)),
    ARRAY['PROMO', 'CONTRATTO_OVERRIDE', 'CONTRATTO_LISTINO', 'CATEGORIA',
          'MANUALE', 'LISTINO_BUNDLE', 'COMPONENTI', NULL]::text[],
    '1) le origini ammesse sono sette, piu'' NULL: LISTINO e manuale no'
);

SELECT is(
    ARRAY[
        vendite.fn_provenienza_prezzo_coerente(NULL,         NULL, NULL, NULL),  -- senza prezzo, niente: si
        vendite.fn_provenienza_prezzo_coerente('MANUALE',    NULL, NULL, NULL),  -- senza prezzo, un'origine: no
        vendite.fn_provenienza_prezzo_coerente(NULL,         10,   NULL, NULL),  -- un prezzo senza origine: no
        vendite.fn_provenienza_prezzo_coerente('MANUALE',    10,   NULL, NULL),  -- si
        vendite.fn_provenienza_prezzo_coerente('MANUALE',    10,   1,    NULL),  -- MANUALE con listino: no
        vendite.fn_provenienza_prezzo_coerente('COMPONENTI', 10,   NULL, 1),     -- COMPONENTI con listino: no
        vendite.fn_provenienza_prezzo_coerente('CATEGORIA',  10,   NULL, 1),     -- riga senza versione: no
        vendite.fn_provenienza_prezzo_coerente('CATEGORIA',  10,   1,    1),     -- si
        vendite.fn_provenienza_prezzo_coerente('CATEGORIA',  10,   1,    NULL),  -- la sola versione: si
        vendite.fn_provenienza_prezzo_coerente('LISTINO',    10,   NULL, NULL)   -- fuori elenco: no
    ],
    ARRAY[true, false, false, true, false, false, false, true, true, false],
    '2) coerenza: senza prezzo niente, con un prezzo un''origine, riga con versione, MANUALE e COMPONENTI senza listino'
);

-- ============================================================
-- 3-6) La forma
-- ============================================================
SELECT is(
    (SELECT count(*)::int FROM information_schema.columns c
      WHERE c.table_schema = 'vendite'
        AND (   (c.table_name IN ('preventivi_righe', 'ordini_righe', 'contratti_righe', 'ddt_righe',
                                  'offerte_commerciali_eccezioni')
                 AND c.column_name IN ('origine_prezzo', 'listino_versione_id', 'listino_riga_id',
                                       'prezzo_resolver_context'))
             OR (c.table_name IN ('preventivi_righe_componenti', 'ordini_righe_componenti',
                                  'contratti_righe_componenti', 'ddt_righe_componenti',
                                  'offerte_commerciali_eccezioni_componenti')
                 AND c.column_name IN ('origine_prezzo', 'listino_versione_id', 'listino_riga_id',
                                       'prezzo_resolver_context')))),
    40,
    '3) origine, versione, riga di listino e contesto sulle dieci tabelle'
);

SELECT is(
    (SELECT count(*)::int FROM pg_constraint k
      WHERE k.contype = 'c'
        AND k.connamespace = 'vendite'::regnamespace
        AND k.conname IN ('chk_preventivi_righe_provenienza_prezzo', 'chk_ordini_righe_provenienza_prezzo',
                          'chk_contratti_righe_provenienza_prezzo', 'chk_ddt_righe_provenienza_prezzo',
                          'chk_offerte_commerciali_eccezioni_provenienza_prezzo',
                          'chk_prevrighe_comp_provenienza_prezzo', 'chk_ordrighe_comp_provenienza_prezzo',
                          'chk_contrighe_comp_provenienza_prezzo', 'chk_ddtrighe_comp_provenienza_prezzo',
                          'chk_oce_comp_provenienza_prezzo')
        AND pg_get_constraintdef(k.oid) LIKE '%fn_provenienza_prezzo_coerente(%'),
    10,
    '4) i dieci CHECK di coerenza chiamano vendite.fn_provenienza_prezzo_coerente'
);

SELECT is(
    (SELECT count(*)::int FROM pg_constraint k
      WHERE k.contype = 'c'
        AND k.connamespace = 'vendite'::regnamespace
        AND k.conname IN ('chk_commesse_attivita_origine_prezzo', 'chk_attivita_fatturabili_origine_prezzo',
                          'chk_prevrighe_comp_origine', 'chk_ordrighe_comp_origine',
                          'chk_ddtrighe_comp_origine', 'chk_contrighe_comp_origine', 'chk_oce_comp_origine')
        AND pg_get_constraintdef(k.oid) LIKE '%fn_origine_prezzo_ammessa(%'),
    7,
    '5) i sette CHECK sulle origini leggono vendite.fn_origine_prezzo_ammessa'
);

SELECT is(
    (SELECT string_agg(x.forma, ', ' ORDER BY x.forma)
       FROM (SELECT DISTINCT
                    p.proname || ' ' || CASE WHEN t.tgtype & 2 = 2 THEN 'BEFORE' ELSE 'AFTER' END
                    || ' ' || (t.tgtype & 1 = 1)::text      -- ROW
                    || ' ' || (t.tgtype & 4 = 4)::text      -- INSERT
                    || ' ' || (t.tgtype & 16 = 16)::text    -- UPDATE
                    || ' x' || (SELECT count(*) FROM pg_trigger t2 WHERE t2.tgfoid = t.tgfoid) AS forma
               FROM pg_trigger t
               JOIN pg_proc p ON p.oid = t.tgfoid
              WHERE p.oid IN ('vendite.trgfn_riga_documento_provenienza_prezzo'::regproc,
                              'vendite.trgfn_riga_documento_guard_listino_provenienza'::regproc)) x),
    'trgfn_riga_documento_guard_listino_provenienza AFTER true true true x10, '
    || 'trgfn_riga_documento_provenienza_prezzo BEFORE true true true x10',
    '6) derivazione BEFORE e guard AFTER, per riga, su INSERT e UPDATE, sulle dieci tabelle'
);

-- ============================================================
-- 7-11) Chi scrive: derivazione e decadenza
-- ============================================================
SELECT is(
    (SELECT origine || '|' || coalesce(versione::text, '-') || '|' || coalesce(riga::text, '-')
       FROM pg_temp.riga()),
    'MANUALE|-|-',
    '7) una riga scritta senza provenienza e'' MANUALE, senza listino'
);

UPDATE vendite.ordini_righe
   SET origine_prezzo          = 'CATEGORIA',
       listino_versione_id     = (SELECT listino_versione_id FROM t_l),
       listino_riga_id         = (SELECT r1 FROM t_r),
       prezzo_resolver_context = '{"prezzo_base_snapshot": 50}'::jsonb,
       prezzo_unitario         = 50
 WHERE id = (SELECT ordine_riga_id FROM t_o);

SELECT is(
    (SELECT origine || '|' || (riga = (SELECT r1 FROM t_r))::text FROM pg_temp.riga()),
    'CATEGORIA|true',
    '8) la provenienza da listino dichiarata e coerente passa: CATEGORIA, riga R1'
);

UPDATE vendite.ordini_righe SET qta_operativa = 3
 WHERE id = (SELECT ordine_riga_id FROM t_o);

SELECT is(
    (SELECT origine || '|' || (riga = (SELECT r1 FROM t_r))::text FROM pg_temp.riga()),
    'CATEGORIA|true',
    '9) cambia la sola quantita'': la provenienza resta'
);

UPDATE vendite.ordini_righe SET prezzo_unitario = 45
 WHERE id = (SELECT ordine_riga_id FROM t_o);

SELECT is(
    (SELECT origine || '|' || coalesce(versione::text, '-') || '|' || coalesce(riga::text, '-')
            || '|' || coalesce(contesto::text, '-') || '|' || (prezzo = 45)::text
       FROM pg_temp.riga()),
    'MANUALE|-|-|-|true',
    '10) cambia il solo prezzo: la provenienza decade a MANUALE, senza listino ne'' contesto'
);

UPDATE vendite.ordini_righe
   SET origine_prezzo      = 'CATEGORIA',
       listino_versione_id = (SELECT listino_versione_id FROM t_l),
       listino_riga_id     = (SELECT r1 FROM t_r),
       prezzo_unitario     = 50
 WHERE id = (SELECT ordine_riga_id FROM t_o);

SELECT is(
    (SELECT origine || '|' || (riga = (SELECT r1 FROM t_r))::text || '|' || (prezzo = 50)::text FROM pg_temp.riga()),
    'CATEGORIA|true|true',
    '11) prezzo e provenienza nuovi nella stessa istruzione (riallineamento): la provenienza resta'
);

-- ============================================================
-- 12-15) I rifiuti
-- ============================================================
SELECT is(
    dbops.fn_pgtap_codice_errore(format(
        'UPDATE vendite.ordini_righe SET origine_prezzo = ''MANUALE'' WHERE id = %s',
        (SELECT ordine_riga_id FROM t_o))),
    'chk_ordini_righe_provenienza_prezzo',
    '12) MANUALE che cita ancora la riga di listino -> CHECK chk_ordini_righe_provenienza_prezzo'
);

SELECT is(
    dbops.fn_pgtap_codice_errore(format(
        'UPDATE vendite.ordini_righe SET listino_riga_id = %s WHERE id = %s',
        (SELECT r2 FROM t_r), (SELECT ordine_riga_id FROM t_o))),
    'E_ATTIVITA_LISTINO_RIGA_INCOERENTE',
    '13) riga di listino di un altro articolo -> E_ATTIVITA_LISTINO_RIGA_INCOERENTE'
);

SELECT is(
    dbops.fn_pgtap_codice_errore(format(
        'UPDATE vendite.ordini_righe SET listino_riga_id = NULL, listino_versione_id = %s WHERE id = %s',
        (SELECT listino_versione_id FROM t_l_altrui), (SELECT ordine_riga_id FROM t_o))),
    'E_ATTIVITA_LISTINO_EMITTENTE_DIVERSO',
    '14) la versione di un listino di un''altra azienda -> E_ATTIVITA_LISTINO_EMITTENTE_DIVERSO'
);

-- Una versione in BOZZA del listino L, nel futuro, con la sua riga per a1.
CREATE TEMP TABLE t_vb AS
WITH ins AS (
    INSERT INTO vendite.listini_versioni (listino_id, codice_versione, valido_dal)
    SELECT l.listino_id, 'PGT_PPR_BOZZA', '2099-01-01'::date FROM t_l l
    RETURNING id
)
SELECT id AS vb FROM ins;

CREATE TEMP TABLE t_rb AS
WITH ins AS (
    INSERT INTO vendite.listini_righe (listino_versione_id, articolo_id, uom_id, prezzo)
    SELECT (SELECT vb FROM t_vb), a.id, a.uom_id, 55.00
      FROM catalogo.articoli a WHERE a.id = (SELECT a1 FROM t_art)
    RETURNING id
)
SELECT id AS rb FROM ins;

SELECT is(
    dbops.fn_pgtap_codice_errore(format(
        'UPDATE vendite.ordini_righe SET listino_versione_id = %s, listino_riga_id = %s WHERE id = %s',
        (SELECT vb FROM t_vb), (SELECT rb FROM t_rb), (SELECT ordine_riga_id FROM t_o))),
    'E_ATTIVITA_LISTINO_VERSIONE_BOZZA',
    '15) riga di listino di una versione in BOZZA -> E_ATTIVITA_LISTINO_VERSIONE_BOZZA'
);

-- ============================================================
-- 16) Il kit: la somma dei componenti e' COMPONENTI
-- ============================================================
-- La riga non ha componenti: la somma vale 0, ed e' comunque la somma.
SELECT script.fn_ricalcola_prezzo_padre_da_componenti(
    'vendite', 'ordini_righe', 'ordini_righe_componenti', 'riga_ordine_id',
    (SELECT ordine_riga_id FROM t_o));

SELECT is(
    (SELECT origine || '|' || coalesce(versione::text, '-') || '|' || coalesce(riga::text, '-')
            || '|' || coalesce(contesto::text, '-') || '|' || (prezzo = 0)::text
       FROM pg_temp.riga()),
    'COMPONENTI|-|-|-|true',
    '16) il prezzo scritto dalla somma dei componenti e'' COMPONENTI, senza listino ne'' contesto'
);

-- ============================================================
-- 17) La commessa ammette le origini dell'elenco unico
-- ============================================================
SELECT ok(
    (SELECT bool_and(vendite.fn_origine_prezzo_ammessa(v))
            AND pg_get_constraintdef(k.oid) LIKE '%fn_origine_prezzo_ammessa(origine_prezzo)%'
       FROM unnest(ARRAY['LISTINO_BUNDLE', 'COMPONENTI']::varchar[]) v,
            pg_constraint k
      WHERE k.conname = 'chk_commesse_attivita_origine_prezzo'
        AND k.conrelid = 'vendite.commesse_attivita'::regclass
      GROUP BY k.oid),
    '17) la riga di commessa ammette LISTINO_BUNDLE e COMPONENTI: il suo CHECK legge l''elenco unico'
);

SELECT * FROM finish();
ROLLBACK;
