-- ------------------------------------------------------------
-- SPDX-License-Identifier: AGPL-3.0-or-later
-- pgTAP test per Zero ERP
--
-- Test: l'EREDITATO dei permessi coincide con i resolver, perche' e' la loro
--   sede — script.fn_get_permessi_ereditati_aree / _azioni (20260925-81/-82),
--   chiamati dal passo 4 dei quattro resolver (-83 … -86); l'helper dei
--   profili con PORTALE a priorita' 3 (-80).
--   Brief: brief-db-pgtap-permessi-ereditati (D-1, D-2, D-3).
--
-- Elenco test (plan 27):
--   La forma
--    1) esiste fn_get_permessi_ereditati_aree(integer)
--    2) esiste fn_get_permessi_ereditati_azioni(integer)
--    3) tutte e due LANGUAGE sql BEGIN ATOMIC, STABLE, INVOKER
--    ⚠️ Rev 2026-10-04 (brief-db-permessi-tetto-area, 20261004-53/-55/-56): l'area e'
--       un TETTO anche sull'ereditato (D-2). La catena delle azioni sta ora in
--       script.fn_get_permessi_effettivi_azioni: e' LEI a chiamare il building block
--       dell'ereditato, e i due resolver delle azioni la leggono. Il test 4 segue la
--       sede (cinque funzioni); gli scarti delle azioni confrontano la colonna
--       abilitata_specifica con l'ereditato, e il resolver e la mappa con
--       «ereditato E l'area consente»; il test 13 legge lo specifico (il tetto lo
--       prova test-permessi-tetto-area-v1).
--    4) ⭐ SEDE UNICA: nessuno dei quattro resolver chiama piu'
--       fn_get_profili_accesso_applicabili; ognuno chiama il suo building block
--    5) la premessa dello spareggio determinato: i cinque indici unici
--    6) la fixture e' completa (catalogo, operatori, profili)
--   Fase 1 — profili della sola veste OPERATORE, nessun PORTALE su quella veste
--    7) A (solo REPARTO): l'ereditato delle aree e' esattamente quello del profilo
--    8) … e quello delle azioni
--    9) A: su TUTTE le aree attive resolver e mappa = ereditato, o BLOCCATO dove manca
--   10) A: su TUTTE le azioni attive resolver e mappa = ereditato, o negata dove manca
--   11) B (AD_HOC + REPARTO, livelli diversi): vince l'AD_HOC, anche nel tipo
--   12) … e sulle azioni
--   13) B: un'area e un'azione coperte dal solo REPARTO scendono al REPARTO
--       (lo spareggio e' PER VOCE, non per utente)
--   14) B: su tutto il catalogo nessuno scarto
--   15) C (nessun profilo): ereditato vuoto
--   16) C: BLOCCATO e negata ovunque, nei resolver e nelle mappe
--   Fase 2 — un PORTALE sulla veste OPERATORE, e A diventa anche cliente shop
--   17) il caso esiste: A ha la veste SHOP_CUSTOMER attiva e l'helper SENZA veste
--       raccoglie il profilo shop (e' il difetto del §3 del brief)
--   18) ⭐ D-1: un'area coperta dal SOLO profilo shop non e' ereditata, e il
--       resolver da' BLOCCATO (prima: il livello del profilo shop)
--   19) D-1: area coperta da REPARTO (LETTURA) e profilo shop (TUTTO): LETTURA
--   20) D-1: un'azione abilitata dal solo profilo shop resta negata
--   21) il profilo shop non compare mai nell'ereditato di A
--   22) ⭐ D-3: REPARTO (TUTTO) contro PORTALE sulla veste OPERATORE (LETTURA):
--       vince il reparto, in entrambe le letture
--   23) D-3: un'area del solo PORTALE di veste resta sua (ripiego)
--   24) D-3: sulle azioni, REPARTO negata contro PORTALE abilitata: negata
--   25) l'helper sotto la veste OPERATORE: AD_HOC 1, REPARTO 2, PORTALE 3
--   26) A: su tutto il catalogo nessuno scarto, anche in fase 2
--   Il contesto
--   27) l'ereditato NON dipende dalla veste di chi legge (il pannello lo legge un
--       amministratore): con la sessione in SHOP_CUSTOMER le righe sono le
--       stesse, mentre il resolver risponde BLOCCATO per il suo gate
--
-- Scopo:
--  - Fino al 2026-09-25 lo spareggio «per ogni voce vince il profilo di priorita'
--    piu' bassa» era scritto in cinque posti (due resolver puntuali, due mappe,
--    la query del backend) e il confronto col resolver era stato fatto a mano.
--    Ora e' scritto una volta: il test 4 prova che i resolver non lo riscrivono,
--    i test 9/10/14/26 provano su TUTTO il catalogo che il cablaggio e' giusto
--    (un'area nuova a catalogo entra da sola nel confronto).
--  - ⚠️ Tutto si COSTRUISCE: tre operatori (fn_pgtap_crea_operatore_umano), due
--    unita' organizzative, cinque profili. I binding di veste (OPERATORE e
--    SHOP_CUSTOMER) si scrivono in upsert: il seed ne lega alcune vesti di
--    portale, e il modello ne ammette UNO per veste (uq_profili_accesso_bindings_ruolo).
--    Un binding gia' presente sulla veste OPERATORE si spegne in testa, se c'e':
--    la fase 1 pretende che non ci sia.
--  - Il test 27 cambia la veste di sessione: sta in coda.
-- ------------------------------------------------------------

-- ⚠️ 1. TRANSAZIONE. Senza, un fallimento a meta' lascia profili e binding di
--   prova nel catalogo: e un binding sulla veste OPERATORE cambierebbe i
--   permessi di TUTTI gli operatori.
BEGIN;

-- ⚠️ 2. CONTESTO APPLICATIVO. Gira come l'applicazione; i resolver leggono il
--   gate di veste dalla GUC, e la fixture scrive come la scrive il pannello.
DO $ctx$ BEGIN PERFORM script.fn_pgtap_set_contesto_operatore(); END $ctx$;

-- ⚠️ 3. VINCOLI DIFFERITI. Ogni istruzione della fixture e' un'unita' completa
--   (i builder escono IMMEDIATE).
SET CONSTRAINTS ALL IMMEDIATE;

SELECT plan(27);

-- ============================================================
-- Fixture — il catalogo: cinque aree e tre azioni attive, per id
-- ⭐ ORDER BY esplicito: la scelta e' ripetibile.
-- ============================================================
CREATE TEMP TABLE _t_aree AS
SELECT af.id AS area_id, af.schema_db, (row_number() OVER (ORDER BY af.id))::int AS n
  FROM config.aree_funzionali af
 WHERE af.attivo
 ORDER BY af.id
 LIMIT 5;

CREATE TEMP TABLE _t_azioni AS
SELECT ap.id AS azione_id, ap.permission_codename, (row_number() OVER (ORDER BY ap.id))::int AS n
  FROM config.azioni_processo ap
 WHERE ap.attivo
 ORDER BY ap.id
 LIMIT 3;

-- ============================================================
-- Fixture — tre operatori umani (non super admin, nessun override)
--   A: solo REPARTO; poi (fase 2) anche cliente shop
--   B: AD_HOC + REPARTO
--   C: nessun profilo
-- ⛔ Cio' che un builder scrive si legge in un'istruzione SEPARATA.
-- ============================================================
CREATE TEMP TABLE _t_op (sigla text, auth_user_id integer, identita_id bigint, risorsa_umana_id bigint);
INSERT INTO _t_op SELECT 'A', o.auth_user_id, o.identita_id, o.risorsa_umana_id
  FROM dbops.fn_pgtap_crea_operatore_umano('ereditati A') o;
INSERT INTO _t_op SELECT 'B', o.auth_user_id, o.identita_id, o.risorsa_umana_id
  FROM dbops.fn_pgtap_crea_operatore_umano('ereditati B') o;
INSERT INTO _t_op SELECT 'C', o.auth_user_id, o.identita_id, o.risorsa_umana_id
  FROM dbops.fn_pgtap_crea_operatore_umano('ereditati C') o;

CREATE FUNCTION pg_temp.op(p_sigla text) RETURNS integer LANGUAGE sql STABLE
AS $$ SELECT auth_user_id FROM _t_op WHERE sigla = p_sigla $$;
CREATE FUNCTION pg_temp.area(p_n integer) RETURNS varchar LANGUAGE sql STABLE
AS $$ SELECT schema_db FROM _t_aree WHERE n = p_n $$;
CREATE FUNCTION pg_temp.area_id(p_n integer) RETURNS integer LANGUAGE sql STABLE
AS $$ SELECT area_id FROM _t_aree WHERE n = p_n $$;
CREATE FUNCTION pg_temp.azione(p_n integer) RETURNS varchar LANGUAGE sql STABLE
AS $$ SELECT permission_codename FROM _t_azioni WHERE n = p_n $$;
CREATE FUNCTION pg_temp.azione_id(p_n integer) RETURNS integer LANGUAGE sql STABLE
AS $$ SELECT azione_id FROM _t_azioni WHERE n = p_n $$;

-- ============================================================
-- Fixture — cinque profili e i loro livelli
--   R_A  REPARTO dell'UO di A       aree 1 TUTTO, 2 LETTURA, 3 TUTTO · azioni 1 si', 2 no
--   H_B  AD_HOC sull'identita' di B aree 1 BLOCCATO               · azioni 1 no
--   R_B  REPARTO dell'UO di B       aree 1 TUTTO, 2 LETTURA         · azioni 1 si', 2 si'
--   P_O  PORTALE sulla veste OPERATORE (fase 2)
--                                   aree 3 LETTURA, 5 LETTURA       · azioni 2 si'
--   S_S  PORTALE sulla veste SHOP_CUSTOMER (fase 2)
--                                   aree 2 TUTTO, 4 TUTTO           · azioni 3 si'
-- La sigla viaggia nella descrizione; il codice ha un suffisso largo.
-- ============================================================
CREATE TEMP TABLE _t_prof AS
WITH def(sigla, tipo) AS (
    VALUES ('R_A', 'REPARTO'), ('H_B', 'AD_HOC'), ('R_B', 'REPARTO'),
           ('P_O', 'PORTALE'), ('S_S', 'PORTALE')
), ins AS (
    INSERT INTO config.profili_accesso (tipo, codice, descrizione, attivo)
    SELECT d.tipo::config.tipo_profilo_accesso,
           '_PGTAP_PE_' || d.sigla || '_' || upper(substr(md5(clock_timestamp()::text || d.sigla), 1, 16)),
           'pgTAP permessi ereditati ' || d.sigla,
           true
      FROM def d
    RETURNING id, descrizione
)
SELECT i.id AS profilo_id, replace(i.descrizione, 'pgTAP permessi ereditati ', '') AS sigla
  FROM ins i;

CREATE FUNCTION pg_temp.prof(p_sigla text) RETURNS integer LANGUAGE sql STABLE
AS $$ SELECT profilo_id FROM _t_prof WHERE sigla = p_sigla $$;

INSERT INTO config.profili_accesso_aree (profilo_accesso_id, area_id, livello)
SELECT p.profilo_id, a.area_id, v.livello::config.livello_accesso
  FROM (VALUES ('R_A', 1, 'TUTTO'), ('R_A', 2, 'LETTURA'), ('R_A', 3, 'TUTTO'),
               ('H_B', 1, 'BLOCCATO'),
               ('R_B', 1, 'TUTTO'), ('R_B', 2, 'LETTURA'),
               ('P_O', 3, 'LETTURA'), ('P_O', 5, 'LETTURA'),
               ('S_S', 2, 'TUTTO'), ('S_S', 4, 'TUTTO')) v(sigla, n, livello)
  JOIN _t_prof p ON p.sigla = v.sigla
  JOIN _t_aree a ON a.n = v.n;

INSERT INTO config.profili_accesso_azioni (profilo_accesso_id, azione_id, abilitata)
SELECT p.profilo_id, z.azione_id, v.abilitata
  FROM (VALUES ('R_A', 1, true), ('R_A', 2, false),
               ('H_B', 1, false),
               ('R_B', 1, true), ('R_B', 2, true),
               ('P_O', 2, true),
               ('S_S', 3, true)) v(sigla, n, abilitata)
  JOIN _t_prof p ON p.sigla = v.sigla
  JOIN _t_azioni z ON z.n = v.n;

-- ============================================================
-- Fixture — le unita' organizzative di A e B, e i binding della fase 1
-- ============================================================
CREATE TEMP TABLE _t_uo AS
WITH ins AS (
    INSERT INTO config.unita_organizzative (codice, codice_interno, descrizione)
    SELECT '_PGTAP_PE_UO_' || s || '_' || upper(substr(md5(clock_timestamp()::text || s), 1, 16)),
           '_PGTAP_PE_UO_' || s || '_' || upper(substr(md5(clock_timestamp()::text || s), 1, 16)),
           'pgTAP permessi ereditati UO ' || s
      FROM (VALUES ('A'), ('B')) v(s)
    RETURNING id, descrizione
)
SELECT i.id AS uo_id, replace(i.descrizione, 'pgTAP permessi ereditati UO ', '') AS sigla
  FROM ins i;

UPDATE anagrafiche.risorse_umane ru
   SET unita_organizzativa_id = u.uo_id
  FROM _t_op o
  JOIN _t_uo u ON u.sigla = o.sigla
 WHERE ru.id = o.risorsa_umana_id;

INSERT INTO config.profili_accesso_bindings (profilo_accesso_id, unita_organizzativa_id, attivo)
SELECT pg_temp.prof('R_' || u.sigla), u.uo_id, true
  FROM _t_uo u;

DO $lega$
BEGIN
    PERFORM config.fn_lega_profilo_identita(pg_temp.prof('H_B'), o.identita_id) FROM _t_op o
 WHERE o.sigla = 'B';
END
$lega$;

-- La fase 1 pretende che nessun profilo sia legato alla veste OPERATORE: se il
-- catalogo ne avesse uno, si spegne qui (il ROLLBACK lo riaccende).
UPDATE config.profili_accesso_bindings
   SET attivo = false
 WHERE ruolo_applicativo = 'OPERATORE'::config.ruolo_applicativo
   AND attivo;

-- Il confronto su TUTTO il catalogo: quante voci attive in cui resolver o mappa
-- NON dicono l'ereditato (o il default, dove l'ereditato manca).
CREATE FUNCTION pg_temp.scarti_aree(p_user integer) RETURNS integer LANGUAGE sql STABLE AS $$
    SELECT count(*)::integer
      FROM config.aree_funzionali af
      LEFT JOIN script.fn_get_permessi_ereditati_aree(p_user) e ON e.area_id = af.id
     WHERE af.attivo
       AND (   script.fn_resolve_livello_area(p_user, af.schema_db)
                 IS DISTINCT FROM COALESCE(e.livello, 'BLOCCATO'::config.livello_accesso)
            OR (script.fn_get_user_permissions_map(p_user) ->> af.schema_db)
                 IS DISTINCT FROM COALESCE(e.livello, 'BLOCCATO'::config.livello_accesso)::text)
$$;

-- Rev 2026-10-04 (tetto d'area): lo SPECIFICO e' l'ereditato; resolver e mappa sono
-- l'ereditato sotto il tetto (script.fn_area_consente_azione sul livello dell'area
-- dell'azione, che scarti_aree prova a parte).
CREATE FUNCTION pg_temp.scarti_azioni(p_user integer) RETURNS integer LANGUAGE sql STABLE AS $$
    SELECT count(*)::integer
      FROM config.azioni_processo ap
      JOIN config.aree_funzionali af ON af.id = ap.area_id
      LEFT JOIN script.fn_get_permessi_ereditati_azioni(p_user) e ON e.azione_id = ap.id
      LEFT JOIN script.fn_get_permessi_effettivi_azioni(p_user) x ON x.azione_id = ap.id
     WHERE ap.attivo
       AND (   x.abilitata_specifica IS DISTINCT FROM COALESCE(e.abilitata, false)
            OR script.fn_check_azione_processo(p_user, ap.permission_codename)
                 IS DISTINCT FROM (COALESCE(e.abilitata, false)
                                   AND script.fn_area_consente_azione(
                                           script.fn_resolve_livello_area(p_user, af.schema_db),
                                           ap.livello_minimo_area))
            OR (script.fn_get_user_actions_map(p_user) ->> ap.permission_codename)::boolean
                 IS DISTINCT FROM (COALESCE(e.abilitata, false)
                                   AND script.fn_area_consente_azione(
                                           script.fn_resolve_livello_area(p_user, af.schema_db),
                                           ap.livello_minimo_area)))
$$;

-- ============================================================
-- 1-6 La forma
-- ============================================================
SELECT has_function('script', 'fn_get_permessi_ereditati_aree', ARRAY['integer'],
    '1) esiste script.fn_get_permessi_ereditati_aree(integer)');
SELECT has_function('script', 'fn_get_permessi_ereditati_azioni', ARRAY['integer'],
    '2) esiste script.fn_get_permessi_ereditati_azioni(integer)');

SELECT is(
    (SELECT string_agg(p.proname || ':' || l.lanname || ':' || p.provolatile::text || ':'
                       || p.prosecdef::text || ':' || (p.prosqlbody IS NOT NULL)::text,
                       ' ' ORDER BY p.proname)
       FROM pg_proc p
       JOIN pg_language l ON l.oid = p.prolang
      WHERE p.pronamespace = 'script'::regnamespace
        AND p.proname IN ('fn_get_permessi_ereditati_aree', 'fn_get_permessi_ereditati_azioni')),
    'fn_get_permessi_ereditati_aree:sql:s:false:true fn_get_permessi_ereditati_azioni:sql:s:false:true',
    '3) tutte e due LANGUAGE sql BEGIN ATOMIC, STABLE, INVOKER');

-- ⭐ Il presidio che conta (linee-guida-sql §12.5.2): non «gli esiti coincidono
--   oggi», ma «il passo 4 non e' piu' scritto nei resolver». Commenti tolti,
--   nome seguito da parentesi: la prosa che spiega non accende il test.
SELECT is(
    (SELECT count(*) FILTER (WHERE x.chiama_helper OR NOT x.chiama_bb)::text
            || ' su ' || count(*)::text
       FROM (SELECT regexp_replace(p.prosrc, '--[^\n]*', '', 'g')
                      ~ 'fn_get_profili_accesso_applicabili\s*\(' AS chiama_helper,
                    regexp_replace(p.prosrc, '--[^\n]*', '', 'g')
                      ~ CASE WHEN p.proname IN ('fn_resolve_livello_area', 'fn_get_user_permissions_map')
                             THEN 'script\.fn_get_permessi_ereditati_aree\s*\('
                             WHEN p.proname = 'fn_get_permessi_effettivi_azioni'
                             THEN 'script\.fn_get_permessi_ereditati_azioni\s*\('
                             ELSE 'script\.fn_get_permessi_effettivi_azioni\s*\(' END AS chiama_bb
               FROM pg_proc p
              WHERE p.pronamespace = 'script'::regnamespace
                AND p.proname IN ('fn_resolve_livello_area', 'fn_check_azione_processo',
                                  'fn_get_user_permissions_map', 'fn_get_user_actions_map',
                                  'fn_get_permessi_effettivi_azioni')) x),
    '0 su 5',
    '4) sede unica: i resolver chiamano il building block (le azioni passando dalla catena effettiva) e non riscrivono lo spareggio');

-- La premessa dello spareggio determinato: sotto una veste, al massimo UN
-- profilo per priorita'. Se uno di questi indici cade (o cambia colonne), due
-- profili possono tornare a pari merito e DISTINCT ON sceglie a caso.
SELECT is(
    (SELECT string_agg(v.nome || '(' || COALESCE(k.colonne, '-') || ')', ' ' ORDER BY v.nome)
       FROM (VALUES ('config', 'uq_profili_accesso_bindings_identita'),
                    ('config', 'uq_profili_accesso_bindings_ruolo'),
                    ('config', 'uq_profili_accesso_bindings_uo'),
                    ('anagrafiche', 'uq_risorse_umane_soggetto_ruolo'),
                    ('anagrafiche', 'uq_identita_digitali_auth_user_ruolo_attivo')) v(schema, nome)
       LEFT JOIN LATERAL (
            SELECT string_agg(a.attname::text, ',' ORDER BY k.ord) AS colonne
              FROM pg_class c
              JOIN pg_namespace n ON n.oid = c.relnamespace AND n.nspname = v.schema
              JOIN pg_index i ON i.indexrelid = c.oid AND i.indisunique
              CROSS JOIN LATERAL unnest(i.indkey) WITH ORDINALITY k(attnum, ord)
              JOIN pg_attribute a ON a.attrelid = i.indrelid AND a.attnum = k.attnum
             WHERE c.relname = v.nome) k ON true),
    'uq_identita_digitali_auth_user_ruolo_attivo(auth_user_id,ruolo_applicativo) '
    || 'uq_profili_accesso_bindings_identita(identita_digitale_id) '
    || 'uq_profili_accesso_bindings_ruolo(ruolo_applicativo) '
    || 'uq_profili_accesso_bindings_uo(unita_organizzativa_id) '
    || 'uq_risorse_umane_soggetto_ruolo(soggetto_ruolo_id)',
    '5) premessa: un binding per identita''/veste/UO, una UO per risorsa umana, una identita'' per veste');

SELECT ok(
    (SELECT count(*) FROM _t_aree) = 5
    AND (SELECT count(*) FROM _t_azioni) = 3
    AND (SELECT count(*) FROM _t_op WHERE auth_user_id IS NOT NULL) = 3
    AND (SELECT count(*) FROM _t_prof) = 5
    AND (SELECT count(*) FROM _t_uo) = 2,
    '6) fixture completa: 5 aree e 3 azioni attive a catalogo, 3 operatori, 5 profili, 2 UO');

-- ============================================================
-- 7-16 Fase 1: la sola veste OPERATORE, nessun PORTALE su quella veste
-- ============================================================
SELECT results_eq(
    $$SELECT a.n, e.livello::text, p.sigla, e.profilo_tipo::text
        FROM script.fn_get_permessi_ereditati_aree(pg_temp.op('A')) e
        LEFT JOIN _t_aree a ON a.area_id = e.area_id
        LEFT JOIN _t_prof p ON p.profilo_id = e.profilo_accesso_id
       ORDER BY a.n$$,
    $$VALUES (1, 'TUTTO', 'R_A', 'REPARTO'), (2, 'LETTURA', 'R_A', 'REPARTO'),
             (3, 'TUTTO', 'R_A', 'REPARTO')$$,
    '7) A: l''ereditato delle aree e'' esattamente il suo REPARTO');

SELECT results_eq(
    $$SELECT z.n, e.abilitata, p.sigla, e.profilo_tipo::text
        FROM script.fn_get_permessi_ereditati_azioni(pg_temp.op('A')) e
        LEFT JOIN _t_azioni z ON z.azione_id = e.azione_id
        LEFT JOIN _t_prof p ON p.profilo_id = e.profilo_accesso_id
       ORDER BY z.n$$,
    $$VALUES (1, true, 'R_A', 'REPARTO'), (2, false, 'R_A', 'REPARTO')$$,
    '8) A: l''ereditato delle azioni e'' esattamente il suo REPARTO');

SELECT is(pg_temp.scarti_aree(pg_temp.op('A')), 0,
    '9) A: su tutte le aree attive resolver e mappa = ereditato, o BLOCCATO dove manca');
SELECT is(pg_temp.scarti_azioni(pg_temp.op('A')), 0,
    '10) A: su tutte le azioni attive resolver e mappa = ereditato, o negata dove manca');

SELECT is(
    (SELECT e.livello::text || '/' || e.profilo_tipo::text
       FROM script.fn_get_permessi_ereditati_aree(pg_temp.op('B')) e
      WHERE e.area_id = pg_temp.area_id(1))
    || ' ' || script.fn_resolve_livello_area(pg_temp.op('B'), pg_temp.area(1))::text,
    'BLOCCATO/AD_HOC BLOCCATO',
    '11) B: AD_HOC (BLOCCATO) contro REPARTO (TUTTO) sulla stessa area: vince l''AD_HOC');

SELECT is(
    (SELECT e.abilitata::text || '/' || e.profilo_tipo::text
       FROM script.fn_get_permessi_ereditati_azioni(pg_temp.op('B')) e
      WHERE e.azione_id = pg_temp.azione_id(1))
    || ' ' || script.fn_check_azione_processo(pg_temp.op('B'), pg_temp.azione(1))::text,
    'false/AD_HOC false',
    '12) B: AD_HOC (negata) contro REPARTO (abilitata) sulla stessa azione: vince l''AD_HOC');

SELECT is(
    (SELECT e.livello::text || '/' || e.profilo_tipo::text
       FROM script.fn_get_permessi_ereditati_aree(pg_temp.op('B')) e
      WHERE e.area_id = pg_temp.area_id(2))
    || ' ' || script.fn_resolve_livello_area(pg_temp.op('B'), pg_temp.area(2))::text
    || ' ' || (SELECT e.abilitata::text || '/' || e.profilo_tipo::text
                 FROM script.fn_get_permessi_ereditati_azioni(pg_temp.op('B')) e
                WHERE e.azione_id = pg_temp.azione_id(2))
    || ' ' || (SELECT x.abilitata_specifica::text
                 FROM script.fn_get_permessi_effettivi_azioni(pg_temp.op('B'), pg_temp.azione(2)) x),
    'LETTURA/REPARTO LETTURA true/REPARTO true',
    '13) B: area e azione del solo REPARTO scendono al REPARTO (spareggio per voce, non per utente)');

SELECT is(pg_temp.scarti_aree(pg_temp.op('B')) + pg_temp.scarti_azioni(pg_temp.op('B')), 0,
    '14) B: su tutto il catalogo (aree e azioni) nessuno scarto');

SELECT is(
    (SELECT count(*) FROM script.fn_get_permessi_ereditati_aree(pg_temp.op('C')))
  + (SELECT count(*) FROM script.fn_get_permessi_ereditati_azioni(pg_temp.op('C'))),
    0::bigint,
    '15) C senza profili: ereditato vuoto');

SELECT is(
    (SELECT count(*) FROM config.aree_funzionali af
      WHERE af.attivo
        AND (script.fn_resolve_livello_area(pg_temp.op('C'), af.schema_db) <> 'BLOCCATO'
             OR script.fn_get_user_permissions_map(pg_temp.op('C')) ->> af.schema_db <> 'BLOCCATO'))
  + (SELECT count(*) FROM config.azioni_processo ap
      WHERE ap.attivo
        AND (script.fn_check_azione_processo(pg_temp.op('C'), ap.permission_codename)
             OR (script.fn_get_user_actions_map(pg_temp.op('C')) ->> ap.permission_codename)::boolean)),
    0::bigint,
    '16) C: BLOCCATO e negata ovunque, nei resolver e nelle mappe');

-- ============================================================
-- Fase 2 — un PORTALE sulla veste OPERATORE, e A diventa anche cliente shop
--   I binding di veste in upsert: il modello ne ammette UNO per veste, e il
--   seed ne lega gia' alcune (il ROLLBACK ripristina).
-- ============================================================
INSERT INTO config.profili_accesso_bindings (profilo_accesso_id, ruolo_applicativo, attivo)
VALUES (pg_temp.prof('P_O'), 'OPERATORE'::config.ruolo_applicativo, true),
       (pg_temp.prof('S_S'), 'SHOP_CUSTOMER'::config.ruolo_applicativo, true)
ON CONFLICT (ruolo_applicativo) WHERE ruolo_applicativo IS NOT NULL
DO UPDATE SET profilo_accesso_id = EXCLUDED.profilo_accesso_id,
              attivo             = true;

-- A cliente shop: un ruolo CL costruito, e l'identita' SHOP_CUSTOMER sul suo
-- stesso utente (il guard di coerenza vuole un CL, non la sua persona).
CREATE TEMP TABLE _t_cl_sog AS
SELECT dbops.fn_pgtap_crea_soggetto_pg('Cliente shop pgTAP ereditati') AS soggetto_id;

CREATE TEMP TABLE _t_cl_sr AS
SELECT dbops.fn_pgtap_crea_soggetto_ruolo(t.soggetto_id, 'CL') AS sr_id
  FROM _t_cl_sog t;

-- La veste dal BB anagrafiche.fn_crea_veste_portale (rev 2026-10-18,
-- brief-db-processi-accensione-per-ambiente 2b-1 lotto 6).
DO $veste$
BEGIN
    PERFORM 1 FROM (
        SELECT anagrafiche.fn_crea_veste_portale(pg_temp.op('A'), s.sr_id, 'SHOP_CUSTOMER'::config.ruolo_applicativo, true) FROM _t_cl_sr s
    ) AS v;
END
$veste$;

-- ============================================================
-- 17-21 D-1: i profili delle altre vesti non entrano
-- ============================================================
SELECT ok(
    EXISTS (SELECT 1 FROM anagrafiche.identita_digitali idg
             WHERE idg.auth_user_id = pg_temp.op('A')
               AND idg.ruolo_applicativo = 'SHOP_CUSTOMER'::config.ruolo_applicativo
               AND idg.attivo)
    AND EXISTS (SELECT 1 FROM script.fn_get_profili_accesso_applicabili(pg_temp.op('A')) h
                 WHERE h.profilo_accesso_id = pg_temp.prof('S_S')),
    '17) il caso esiste: A e'' anche cliente shop, e l''helper senza veste raccoglie il profilo shop');

SELECT is(
    COALESCE((SELECT e.livello::text
                FROM script.fn_get_permessi_ereditati_aree(pg_temp.op('A')) e
               WHERE e.area_id = pg_temp.area_id(4)), 'assente')
    || ' ' || script.fn_resolve_livello_area(pg_temp.op('A'), pg_temp.area(4))::text
    || ' ' || (script.fn_get_user_permissions_map(pg_temp.op('A')) ->> pg_temp.area(4)),
    'assente BLOCCATO BLOCCATO',
    '18) D-1: un''area del SOLO profilo shop non e'' ereditata, e il resolver da'' BLOCCATO');

SELECT is(
    (SELECT e.livello::text || '/' || e.profilo_tipo::text
       FROM script.fn_get_permessi_ereditati_aree(pg_temp.op('A')) e
      WHERE e.area_id = pg_temp.area_id(2))
    || ' ' || script.fn_resolve_livello_area(pg_temp.op('A'), pg_temp.area(2))::text,
    'LETTURA/REPARTO LETTURA',
    '19) D-1: REPARTO (LETTURA) e profilo shop (TUTTO) sulla stessa area: LETTURA');

SELECT is(
    COALESCE((SELECT e.abilitata::text
                FROM script.fn_get_permessi_ereditati_azioni(pg_temp.op('A')) e
               WHERE e.azione_id = pg_temp.azione_id(3)), 'assente')
    || ' ' || script.fn_check_azione_processo(pg_temp.op('A'), pg_temp.azione(3))::text
    || ' ' || (script.fn_get_user_actions_map(pg_temp.op('A')) ->> pg_temp.azione(3)),
    'assente false false',
    '20) D-1: un''azione abilitata dal SOLO profilo shop resta negata');

SELECT is(
    (SELECT count(*) FROM script.fn_get_permessi_ereditati_aree(pg_temp.op('A')) e
      WHERE e.profilo_accesso_id = pg_temp.prof('S_S'))
  + (SELECT count(*) FROM script.fn_get_permessi_ereditati_azioni(pg_temp.op('A')) e
      WHERE e.profilo_accesso_id = pg_temp.prof('S_S')),
    0::bigint,
    '21) il profilo shop non compare mai nell''ereditato da operatore');

-- ============================================================
-- 22-25 D-3: il reparto vince sul profilo della veste OPERATORE
-- ============================================================
SELECT is(
    (SELECT e.livello::text || '/' || e.profilo_tipo::text
       FROM script.fn_get_permessi_ereditati_aree(pg_temp.op('A')) e
      WHERE e.area_id = pg_temp.area_id(3))
    || ' ' || script.fn_resolve_livello_area(pg_temp.op('A'), pg_temp.area(3))::text
    || ' ' || (script.fn_get_user_permissions_map(pg_temp.op('A')) ->> pg_temp.area(3)),
    'TUTTO/REPARTO TUTTO TUTTO',
    '22) D-3: REPARTO (TUTTO) contro PORTALE di veste (LETTURA): vince il reparto, in tutte le letture');

SELECT is(
    (SELECT e.livello::text || '/' || e.profilo_tipo::text
       FROM script.fn_get_permessi_ereditati_aree(pg_temp.op('A')) e
      WHERE e.area_id = pg_temp.area_id(5))
    || ' ' || script.fn_resolve_livello_area(pg_temp.op('A'), pg_temp.area(5))::text,
    'LETTURA/PORTALE LETTURA',
    '23) D-3: un''area del solo PORTALE di veste resta sua (e'' il ripiego di gruppo)');

SELECT is(
    (SELECT e.abilitata::text || '/' || e.profilo_tipo::text
       FROM script.fn_get_permessi_ereditati_azioni(pg_temp.op('A')) e
      WHERE e.azione_id = pg_temp.azione_id(2))
    || ' ' || script.fn_check_azione_processo(pg_temp.op('A'), pg_temp.azione(2))::text,
    'false/REPARTO false',
    '24) D-3: REPARTO negata contro PORTALE di veste abilitata: negata');

SELECT results_eq(
    $$SELECT pa.tipo::text, h.priorita::integer
        FROM script.fn_get_profili_accesso_applicabili(
                 pg_temp.op('B'), 'OPERATORE'::config.ruolo_applicativo) h
        JOIN config.profili_accesso pa ON pa.id = h.profilo_accesso_id
       ORDER BY h.priorita$$,
    $$VALUES ('AD_HOC', 1), ('REPARTO', 2), ('PORTALE', 3)$$,
    '25) l''helper sotto la veste OPERATORE: AD_HOC 1, REPARTO 2, PORTALE 3 — un profilo per priorita''');

SELECT is(pg_temp.scarti_aree(pg_temp.op('A')) + pg_temp.scarti_azioni(pg_temp.op('A')), 0,
    '26) A in fase 2: su tutto il catalogo (aree e azioni) nessuno scarto');

-- ============================================================
-- 27 Il contesto (in coda: cambia la veste di sessione)
--   Il pannello permessi lo legge un amministratore sull'operatore scelto:
--   l'ereditato risponde sull'UTENTE PASSATO, non sulla sessione. Il gate di
--   veste e' dei resolver, non del building block.
-- ============================================================
CREATE TEMP TABLE _t_snap AS
SELECT * FROM script.fn_get_permessi_ereditati_aree(pg_temp.op('A'));

SELECT set_config('app.ruolo_applicativo', 'SHOP_CUSTOMER', true);

SELECT is(
    (SELECT count(*) FROM (
         (SELECT * FROM script.fn_get_permessi_ereditati_aree(pg_temp.op('A')) EXCEPT SELECT * FROM _t_snap)
         UNION ALL
         (SELECT * FROM _t_snap EXCEPT SELECT * FROM script.fn_get_permessi_ereditati_aree(pg_temp.op('A')))) d)::text
    || '/' || (SELECT count(*) FROM _t_snap)::text
    || ' ' || script.fn_resolve_livello_area(pg_temp.op('A'), pg_temp.area(1))::text,
    '0/4 BLOCCATO',
    '27) l''ereditato non dipende dalla veste di sessione (4 righe identiche); il resolver si''');

SELECT * FROM finish();
ROLLBACK;
