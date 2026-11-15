-- ------------------------------------------------------------
-- SPDX-License-Identifier: AGPL-3.0-or-later
-- pgTAP test per Zero ERP
--
-- Test: la scheda di fornitura di contratto e offerta segue la fornitura del
--   documento. Si prende dai dati precontrattuali della coppia (istanza,
--   utility); se la coppia cambia in bozza si rifa' da capo (D-5), anche se
--   prima non c'era (D-5-bis); la sua coppia e' quella della testata (D-6);
--   alla nascita del contratto le chiavi dell'operatore correggono quella
--   dell'anagrafica invece di collidere (D-7).
--   Brief: docs/it/dev/work-in-progress/brief-db-indirizzi-documento-seguono-il-cliente.md (§8.4)
--   ChangeSet 20261012-34 ... -42.
--
-- ⭐ I soggetti li FABBRICA (dbops.fn_pgtap_crea_emittente_operatore,
--   fn_pgtap_crea_cliente_ba), i dati precontrattuali li scrive qui:
--     A, B  utility SENZA tipi d'uso, ciascuno coi suoi dati (param_2_txt A, B)
--     N     stessa utility, SENZA dati precontrattuali
--     G     utility CON tipi d'uso, con una classe (il tipo d'uso si deriva)
--   Le utility si scelgono dal catalogo per la loro forma (con o senza
--   config.tipi_utenze), non per codice.
-- ⭐ Il caso G e' quello che ha deciso D-6: una FK con cascata avrebbe fatto
--   giudicare la classe vecchia contro la utility nuova.
--
-- Indice test (1..17):
--   STRUTTURA
--    1) il guard della coppia sulle due schede, il cambio di fornitura sulle due testate
--    2) la scheda «dall'anagrafica» ha una sede: chi chiama il BB e il lettore (sulla forma)
--   IL LETTORE
--    3) la scheda di A; quella di G col tipo d'uso derivato dalla classe; N nessuna
--    4) coppia NULL: E_DOC_FORNITURA_PARAMETRO_MANCANTE
--   NASCITA DEL CONTRATTO (D-7)
--    5) senza scheda dell'operatore: quella dell'anagrafica
--    6) con la scheda dell'operatore, su una fornitura che ha i suoi dati: niente collisione, vince l'operatore
--    7) le chiavi che l'operatore non manda restano dell'anagrafica
--    8) su una fornitura senza dati: la scheda dell'operatore e' scritta com'e'
--   CAMBIO DI FORNITURA DEL CONTRATTO (D-5)
--    9) A -> B: la scheda e' quella di B, la correzione dell'operatore non passa
--   10) B -> N: il contratto resta senza scheda
--   11) N -> A: la riceve dall'anagrafica, anche se prima non c'era (D-5-bis)
--   12) A -> G, su un'altra utility: rifiutato, la scheda resta quella di A
--       (rev 2026-10-18: la utility della testata e' ferma sempre, §8.7 del brief)
--   IL GUARD DELLA COPPIA (D-6)
--   13) una scheda con la coppia di un altro cliente: E_DOC_FORNITURA_FUORI_TESTATA
--   14) spostare la coppia di una scheda gia' scritta: E_DOC_FORNITURA_FUORI_TESTATA
--   OFFERTA (D-5, D-5-bis)
--   15) la scheda scritta dall'operatore, A -> B: e' quella di B dall'anagrafica
--   16) un'offerta senza scheda, B -> A: la riceve
--   17) un cambio del solo resto della testata non tocca la scheda
-- ------------------------------------------------------------
BEGIN;

SET CONSTRAINTS ALL IMMEDIATE;

SELECT plan(17);

-- ============================================================
-- FIXTURE
-- ============================================================
CREATE TEMP TABLE _m AS
SELECT * FROM dbops.fn_pgtap_crea_emittente_operatore();

DO $ctx$ BEGIN PERFORM script.fn_pgtap_set_contesto_operatore((SELECT auth_user_id FROM _m)); END $ctx$;

-- Le due forme di utility: senza tipi d'uso, e con tipi d'uso e una classe.
CREATE TEMP TABLE _u AS
SELECT (SELECT u.id FROM config.utilities u
         WHERE NOT EXISTS (SELECT 1 FROM config.tipi_utenze t WHERE t.utility_id = u.id)
         ORDER BY u.id LIMIT 1) AS senza_tipi,
       (SELECT t.utility_id FROM config.classi_utenze cl
          JOIN config.tipi_utenze t ON t.id = cl.tipo_utenza_id
         ORDER BY t.utility_id, cl.id LIMIT 1) AS con_tipi,
       (SELECT cl.id FROM config.classi_utenze cl
          JOIN config.tipi_utenze t ON t.id = cl.tipo_utenza_id
         ORDER BY t.utility_id, cl.id LIMIT 1) AS classe,
       (SELECT cl.tipo_utenza_id FROM config.classi_utenze cl
          JOIN config.tipi_utenze t ON t.id = cl.tipo_utenza_id
         ORDER BY t.utility_id, cl.id LIMIT 1) AS tipo;

CREATE TEMP TABLE _c AS
SELECT 'A' AS lato, c.* FROM dbops.fn_pgtap_crea_cliente_ba('fornitura A', (SELECT senza_tipi FROM _u)) c
UNION ALL
SELECT 'B' AS lato, c.* FROM dbops.fn_pgtap_crea_cliente_ba('fornitura B', (SELECT senza_tipi FROM _u)) c
UNION ALL
SELECT 'N' AS lato, c.* FROM dbops.fn_pgtap_crea_cliente_ba('fornitura N', (SELECT senza_tipi FROM _u)) c
UNION ALL
SELECT 'G' AS lato, c.* FROM dbops.fn_pgtap_crea_cliente_ba('fornitura G', (SELECT con_tipi FROM _u)) c;

SET CONSTRAINTS ALL IMMEDIATE;

-- I dati precontrattuali: A e B senza classe (la loro utility non ha tipi
-- d'uso), G con la classe. N niente.
CREATE TEMP TABLE _idp AS
WITH i AS (
    INSERT INTO anagrafiche.istanze_dati_precontrattuali
           (istanza_utility_id, utility_id, classe_utenza_id, param_1_num, param_2_txt, meta)
    SELECT c.istanza_utility_id, c.utility_id,
           CASE WHEN c.lato = 'G' THEN (SELECT classe FROM _u) END,
           CASE c.lato WHEN 'A' THEN 1 WHEN 'B' THEN 2 ELSE 3 END,
           'PGTAP-' || c.lato,
           jsonb_build_object('pgtap', c.lato)
      FROM _c c WHERE c.lato IN ('A', 'B', 'G')
    RETURNING id, istanza_utility_id)
SELECT c.lato, i.id
  FROM i JOIN _c c ON c.istanza_utility_id = i.istanza_utility_id;

CREATE TEMP TABLE _k AS
SELECT (SELECT emittente_fiscale_id FROM _m)                                        AS ef,
       (SELECT s.id FROM config.stati_doc_offerte s WHERE s.codice_interno = 'BOZZA') AS off_bozza;

-- Scopo: la testata del contratto col cliente del lato, valida per un anno
-- suo: i contratti passano da una fornitura all'altra, e due contratti della
-- stessa fornitura non si sovrappongono (ex_contratti_no_overlap).
CREATE FUNCTION pg_temp.testata(p_lato text, p_anno int)
RETURNS jsonb LANGUAGE sql STABLE AS $f$
  SELECT jsonb_build_object(
           'billing_account_id',   c.billing_account_id,
           'emittente_fiscale_id', (SELECT ef FROM _k),
           'istanza_utility_id',   c.istanza_utility_id,
           'utility_id',           c.utility_id,
           'valido_dal',           make_date(p_anno, 1, 1),
           'valido_al',            make_date(p_anno, 12, 31))
    FROM _c c WHERE c.lato = p_lato;
$f$;

-- Scopo: la scheda di un documento in una forma confrontabile, o '-' se non c'e'.
CREATE FUNCTION pg_temp.scheda(p_tabella text, p_fk text, p_id bigint)
RETURNS text LANGUAGE plpgsql STABLE AS $f$
DECLARE v text;
BEGIN
    EXECUTE format(
        'SELECT concat_ws(''|'', x.istanza_dati_precontrattuali_id, x.classe_utenza_id, x.tipo_utenza_id,'
        '                 x.param_1_num::numeric(18,2), x.param_2_txt) '
        '  FROM vendite.%I x WHERE x.%I = $1', p_tabella, p_fk)
       INTO v USING p_id;
    RETURN COALESCE(v, '-');
END $f$;

-- Scopo: la scheda che l'anagrafica da' al lato, nella stessa forma.
CREATE FUNCTION pg_temp.attesa(p_lato text)
RETURNS text LANGUAGE sql STABLE AS $f$
  SELECT concat_ws('|', i.id,
                   CASE WHEN p_lato = 'G' THEN (SELECT classe FROM _u) END,
                   CASE WHEN p_lato = 'G' THEN (SELECT tipo FROM _u) END,
                   (CASE p_lato WHEN 'A' THEN 1 WHEN 'B' THEN 2 ELSE 3 END)::numeric(18,2),
                   'PGTAP-' || p_lato)
    FROM _idp i WHERE i.lato = p_lato;
$f$;

-- Scopo: sposta il contratto sulla fornitura del lato (UPDATE della testata).
CREATE FUNCTION pg_temp.sposta_contratto(p_id bigint, p_lato text)
RETURNS void LANGUAGE sql AS $f$
  UPDATE vendite.contratti k
     SET billing_account_id = c.billing_account_id,
         istanza_utility_id = c.istanza_utility_id,
         utility_id         = c.utility_id
    FROM _c c
   WHERE c.lato = p_lato AND k.id = p_id;
$f$;

-- ============================================================
-- STRUTTURA
-- ============================================================
SELECT is(
    (SELECT string_agg(c.relname || '.' || t.tgname, ', ' ORDER BY c.relname)
       FROM pg_trigger t
       JOIN pg_class c ON c.oid = t.tgrelid
       JOIN pg_namespace n ON n.oid = c.relnamespace AND n.nspname = 'vendite'
      WHERE t.tgname LIKE '%\_a10\_guard\_coppia\_ins\_upd'
         OR t.tgname LIKE '%\_m50\_fornitura\_segue\_cliente\_upd'),
    'contratti.trg_contratti_m50_fornitura_segue_cliente_upd, '
    'contratti_utilities.trg_contratti_utilities_a10_guard_coppia_ins_upd, '
    'offerte_commerciali.trg_offerte_commerciali_m50_fornitura_segue_cliente_upd, '
    'offerte_commerciali_utilities.trg_offerte_commerciali_utilities_a10_guard_coppia_ins_upd',
    '1) il guard della coppia sulle due schede, il cambio di fornitura sulle due testate');

-- ⚠️ Sulla FORMA, dichiarato: si asserisce che la regola ha UNA sede. Due
--   elenchi fra le funzioni di vendite, commenti tolti: chi CHIAMA il BB o il
--   lettore (nome seguito da «(»), e chi LEGGE la tabella dei precontrattuali
--   (nominata senza «.» dopo: un %TYPE non e' una lettura). Il secondo, tolti
--   il BB e il lettore, e' vuoto: un trigger che ricopiasse la regola ci
--   finirebbe dentro.
CREATE FUNCTION pg_temp.sorgenti(p_re text)
RETURNS text LANGUAGE sql STABLE AS $f$
  SELECT COALESCE(string_agg(p.proname, ', ' ORDER BY p.proname), '-')
    FROM pg_proc p JOIN pg_namespace n ON n.oid = p.pronamespace AND n.nspname = 'vendite'
   WHERE regexp_replace(p.prosrc, '--[^\n]*', '', 'g') ~ p_re
     AND p.proname NOT IN ('fn_doc_fornitura_da_anagrafica', 'fn_get_fornitura_da_anagrafica');
$f$;

SELECT is(
    'chiamano: ' || pg_temp.sorgenti('(fn_doc_fornitura_da_anagrafica|fn_get_fornitura_da_anagrafica)\s*\(')
    || ' | leggono: ' || pg_temp.sorgenti('istanze_dati_precontrattuali\M(?!\.)'),
    'chiamano: trgfn_contratti_snapshot_precontrattuali, trgfn_doc_fornitura_segue_cliente | leggono: -',
    '2) la scheda dall''anagrafica la scrive il BB: i due trigger lo chiamano, nessun altro legge i precontrattuali');

-- ============================================================
-- IL LETTORE
-- ============================================================
SELECT is(
    (SELECT concat_ws('|', f.istanza_dati_precontrattuali_id, f.classe_utenza_id, f.tipo_utenza_id,
                      f.param_1_num::numeric(18,2), f.param_2_txt)
       FROM _c c, vendite.fn_get_fornitura_da_anagrafica(c.istanza_utility_id, c.utility_id) f
      WHERE c.lato = 'A')
    || ' ; ' ||
    (SELECT concat_ws('|', f.istanza_dati_precontrattuali_id, f.classe_utenza_id, f.tipo_utenza_id,
                      f.param_1_num::numeric(18,2), f.param_2_txt)
       FROM _c c, vendite.fn_get_fornitura_da_anagrafica(c.istanza_utility_id, c.utility_id) f
      WHERE c.lato = 'G')
    || ' ; ' ||
    (SELECT count(*)::text
       FROM _c c, vendite.fn_get_fornitura_da_anagrafica(c.istanza_utility_id, c.utility_id) f
      WHERE c.lato = 'N'),
    pg_temp.attesa('A') || ' ; ' || pg_temp.attesa('G') || ' ; 0',
    '3) la scheda di A; quella di G col tipo d''uso derivato dalla classe; N nessuna');

SELECT is(
    dbops.fn_pgtap_codice_errore('SELECT * FROM vendite.fn_get_fornitura_da_anagrafica(NULL, NULL)'),
    'E_DOC_FORNITURA_PARAMETRO_MANCANTE',
    '4) coppia NULL: E_DOC_FORNITURA_PARAMETRO_MANCANTE');

-- ============================================================
-- NASCITA DEL CONTRATTO (D-7)
-- ============================================================
CREATE TEMP TABLE _k1 AS SELECT * FROM vendite.fn_create_contratto(pg_temp.testata('A', 2061), NULL);

SELECT is(
    pg_temp.scheda('contratti_utilities', 'contratto_id', (SELECT contratto_id FROM _k1)),
    pg_temp.attesa('A'),
    '5) senza scheda dell''operatore il contratto nasce con quella dell''anagrafica');

-- Prima del 20261012-42 qui l'INSERT dell'operatore collideva su
-- uq_contratti_utilities_contratto_id: il contratto non si creava.
CREATE TEMP TABLE _k2 AS
SELECT * FROM vendite.fn_create_contratto(
    pg_temp.testata('A', 2062),
    (SELECT jsonb_build_object('istanza_utility_id', c.istanza_utility_id,
                               'utility_id',         c.utility_id,
                               'param_2_txt',        'OPERATORE')
       FROM _c c WHERE c.lato = 'A'));

SELECT is(
    (SELECT param_2_txt FROM vendite.contratti_utilities WHERE contratto_id = (SELECT contratto_id FROM _k2)),
    'OPERATORE',
    '6) su una fornitura coi suoi dati la scheda dell''operatore non collide: vince lui');

SELECT is(
    (SELECT concat_ws('|', cu.istanza_dati_precontrattuali_id, cu.param_1_num::numeric(18,2), cu.meta ->> 'pgtap')
       FROM vendite.contratti_utilities cu WHERE cu.contratto_id = (SELECT contratto_id FROM _k2)),
    (SELECT i.id FROM _idp i WHERE i.lato = 'A') || '|1.00|A',
    '7) le chiavi che l''operatore non manda restano quelle dell''anagrafica');

CREATE TEMP TABLE _k3 AS
SELECT * FROM vendite.fn_create_contratto(
    pg_temp.testata('N', 2063),
    (SELECT jsonb_build_object('istanza_utility_id', c.istanza_utility_id,
                               'utility_id',         c.utility_id,
                               'param_2_txt',        'SOLO OPERATORE')
       FROM _c c WHERE c.lato = 'N'));

SELECT is(
    pg_temp.scheda('contratti_utilities', 'contratto_id', (SELECT contratto_id FROM _k3)),
    'SOLO OPERATORE',
    '8) su una fornitura senza dati la scheda dell''operatore e'' scritta com''e''');

-- ============================================================
-- CAMBIO DI FORNITURA DEL CONTRATTO (D-5)
-- ============================================================
SELECT pg_temp.sposta_contratto((SELECT contratto_id FROM _k2), 'B');

SELECT is(
    pg_temp.scheda('contratti_utilities', 'contratto_id', (SELECT contratto_id FROM _k2)),
    pg_temp.attesa('B'),
    '9) A -> B: la scheda e'' quella di B, la correzione dell''operatore non passa');

SELECT pg_temp.sposta_contratto((SELECT contratto_id FROM _k2), 'N');

SELECT is(
    pg_temp.scheda('contratti_utilities', 'contratto_id', (SELECT contratto_id FROM _k2)),
    '-',
    '10) B -> N: la fornitura nuova non ha dati, il contratto resta senza scheda');

SELECT pg_temp.sposta_contratto((SELECT contratto_id FROM _k2), 'A');

SELECT is(
    pg_temp.scheda('contratti_utilities', 'contratto_id', (SELECT contratto_id FROM _k2)),
    pg_temp.attesa('A'),
    '11) N -> A: la scheda arriva dall''anagrafica anche se prima non c''era (D-5-bis)');

-- ⚠️ Il cambio in un'istruzione a se': pg_temp.scheda e' STABLE e nella
--   stessa istruzione vedrebbe la fotografia di prima del cambio.
-- rev 2026-10-18 (§8.7 del brief): la utility della testata e' ferma
--   sempre, anche in bozza (20261018-67). A -> G cambia utility: il lock di
--   testata lo rifiuta prima che la scheda si muova. Prima il test diceva
--   «la scheda di G»: il caso non e' piu' raggiungibile dalla testata.
CREATE TEMP TABLE _r12 AS
SELECT COALESCE(dbops.fn_pgtap_codice_errore(format('SELECT pg_temp.sposta_contratto(%s, %L)',
                             (SELECT contratto_id FROM _k1), 'G')), 'nessun errore') AS esito;

SELECT is(
    (SELECT esito FROM _r12)
    || ' ' || pg_temp.scheda('contratti_utilities', 'contratto_id', (SELECT contratto_id FROM _k1)),
    'E_DOC_UTILITY_IMMUTABILE ' || pg_temp.attesa('A'),
    '12) A -> G, su un''altra utility: rifiutato (la utility e'' ferma), la scheda resta quella di A');

-- ============================================================
-- IL GUARD DELLA COPPIA (D-6)
-- ============================================================
-- Il contratto di _k3 e' sulla fornitura di N.
DELETE FROM vendite.contratti_utilities WHERE contratto_id = (SELECT contratto_id FROM _k3);

SELECT is(
    dbops.fn_pgtap_codice_errore(format(
        'INSERT INTO vendite.contratti_utilities (contratto_id, istanza_utility_id, utility_id) '
        'SELECT %s, c.istanza_utility_id, c.utility_id FROM _c c WHERE c.lato = %L',
        (SELECT contratto_id FROM _k3), 'B')),
    'E_DOC_FORNITURA_FUORI_TESTATA',
    '13) una scheda con la coppia di un altro cliente: E_DOC_FORNITURA_FUORI_TESTATA');

SELECT is(
    dbops.fn_pgtap_codice_errore(format(
        'UPDATE vendite.contratti_utilities SET istanza_utility_id = (SELECT istanza_utility_id FROM _c WHERE lato = %L) '
        ' WHERE contratto_id = %s',
        'B', (SELECT contratto_id FROM _k2))),
    'E_DOC_FORNITURA_FUORI_TESTATA',
    '14) spostare la coppia di una scheda gia'' scritta: E_DOC_FORNITURA_FUORI_TESTATA');

-- ============================================================
-- OFFERTA (D-5, D-5-bis)
-- ============================================================
CREATE TEMP TABLE _l AS
SELECT * FROM dbops.fn_pgtap_crea_listino((SELECT senza_tipi FROM _u), 'fornitura offerta');

CREATE FUNCTION pg_temp.offerta(p_lato text)
RETURNS bigint LANGUAGE plpgsql AS $f$
DECLARE v_id bigint;
BEGIN
    INSERT INTO vendite.offerte_commerciali
           (emittente_fiscale_id, billing_account_id, istanza_utility_id, utility_id,
            listino_id, validita_dal, validita_al, stato_doc_offerta_id)
    SELECT k.ef, c.billing_account_id, c.istanza_utility_id, c.utility_id,
           l.listino_id, script.fn_data_operativa(), script.fn_data_operativa() + 365, k.off_bozza
      FROM _c c CROSS JOIN _k k CROSS JOIN _l l WHERE c.lato = p_lato
    RETURNING id INTO v_id;
    RETURN v_id;
END $f$;

CREATE FUNCTION pg_temp.sposta_offerta(p_id bigint, p_lato text)
RETURNS void LANGUAGE sql AS $f$
  UPDATE vendite.offerte_commerciali o
     SET billing_account_id = c.billing_account_id,
         istanza_utility_id = c.istanza_utility_id,
         utility_id         = c.utility_id
    FROM _c c
   WHERE c.lato = p_lato AND o.id = p_id;
$f$;

CREATE TEMP TABLE _o AS
SELECT pg_temp.offerta('A') AS con_scheda,
       pg_temp.offerta('B') AS senza_scheda;

-- La scheda dell'offerta la scrive l'operatore (come il backend): niente
-- riferimento ai precontrattuali, un parametro suo.
INSERT INTO vendite.offerte_commerciali_utilities (offerta_id, istanza_utility_id, utility_id, param_2_txt)
SELECT o.con_scheda, c.istanza_utility_id, c.utility_id, 'PROPOSTA'
  FROM _o o, _c c WHERE c.lato = 'A';

SELECT pg_temp.sposta_offerta((SELECT con_scheda FROM _o), 'B');

SELECT is(
    pg_temp.scheda('offerte_commerciali_utilities', 'offerta_id', (SELECT con_scheda FROM _o)),
    pg_temp.attesa('B'),
    '15) la scheda scritta dall''operatore, A -> B: e'' quella di B dall''anagrafica');

SELECT pg_temp.sposta_offerta((SELECT senza_scheda FROM _o), 'A');

SELECT is(
    pg_temp.scheda('offerte_commerciali_utilities', 'offerta_id', (SELECT senza_scheda FROM _o)),
    pg_temp.attesa('A'),
    '16) un''offerta senza scheda, B -> A: la riceve dall''anagrafica (D-5-bis)');

UPDATE vendite.offerte_commerciali_utilities
   SET param_2_txt = 'RITOCCO'
 WHERE offerta_id = (SELECT senza_scheda FROM _o);

UPDATE vendite.offerte_commerciali
   SET validita_al = validita_al + 1
 WHERE id = (SELECT senza_scheda FROM _o);

SELECT is(
    (SELECT param_2_txt FROM vendite.offerte_commerciali_utilities WHERE offerta_id = (SELECT senza_scheda FROM _o)),
    'RITOCCO',
    '17) un cambio della testata che non tocca la fornitura lascia la scheda com''e''');

SELECT * FROM finish();
ROLLBACK;
