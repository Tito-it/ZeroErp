-- ------------------------------------------------------------
-- SPDX-License-Identifier: AGPL-3.0-or-later
-- pgTAP test per Zero ERP
--
-- Test: i guard ATTIVO leggono padre e figlie con gli occhi del proprietario
--   del database, non sotto la row security di chi scrive (D51, Q8).
-- Riferimento: brief-db-revisione-dbops, giro 3.
--
-- Semantica attesa (il contratto, non l'implementazione):
--   - il require differito si chiude allo stesso modo qualunque sia il
--     contesto al commit: un padre attivo resta attivo anche per chi non lo
--     vede (prima: «Padre non attivo», un 500);
--   - il block conta anche le figlie che chi spegne il padre non vede: un
--     catalogo usato da un'altra azienda non si spegne (prima: si spegneva);
--   - le due letture rispondono solo per trigger montati su tabelle del
--     proprietario: un trigger costruito dall'applicazione su una TEMP sua,
--     con argomenti a piacere, non legge niente.
--
-- Elenco test (plan 9):
--   1) la premessa: listini sotto RLS non forzata, la tipologia senza RLS
--   2) la premessa del caso: l'operatore di MIA non vede il listino ALTRUI
--   3) D51 require: i differiti si chiudono nei panni di MIA e passano
--   4) D51 block: MIA non spegne la tipologia usata dal listino ALTRUI
--   5) ... e la frase nomina la tabella che blocca
--   6) un require montato dall'applicazione su una TEMP sua: la lettura rifiuta
--   7) ... e il trigger, scattando, non legge niente
--   8) un block montato dall'applicazione su una TEMP sua: la lettura rifiuta
--   9) PRESIDIO: ogni trigger ATTIVO sta su tabelle del proprietario delle
--      due letture, senza FORCE, da tutti e due i lati
--
-- ⚠️ Runner: APPLICATIVO, ed e' il punto. Da owner la row security non c'e':
--   il test 2 e' rosso per costruzione (l'owner vede il listino), i test 3-5
--   sono verdi anche senza la correzione (l'owner vede il padre e le figlie), e
--   i test 6-8 sono rossi (la TEMP e' del proprietario, e le letture la
--   accettano: il montaggio finto nomina una colonna innocua, cosi' da owner si
--   legge e basta). La regola si vede solo come app.
-- ⚠️ La fixture la scrive il SUPER ADMIN, l'unico che puo' costruire un listino
--   di un'altra azienda; poi si torna operatore di MIA (stessa forma di
--   rls/test-rls-listini-ef-whitelist-write).
-- ------------------------------------------------------------

BEGIN;

-- Le tre aziende si costruiscono: MIA (il contesto), ALTRUI (il listino fuori
--   perimetro) e SA, il cui operatore diventa super admin.
CREATE TEMP TABLE _mondi AS
SELECT 'MIA'    AS lato, * FROM dbops.fn_pgtap_crea_emittente_operatore()
UNION ALL
SELECT 'ALTRUI' AS lato, * FROM dbops.fn_pgtap_crea_emittente_operatore()
UNION ALL
SELECT 'SA'     AS lato, * FROM dbops.fn_pgtap_crea_emittente_operatore();

DO $lega$ BEGIN PERFORM config.fn_lega_profilo_identita((SELECT id FROM config.profili_accesso WHERE codice = 'SUPER_ADMIN'), (SELECT identita_id FROM _mondi WHERE lato = 'SA')); END $lega$;

-- ⚠️ I vincoli restano DIFFERITI fino al test 3: e' proprio il loro chiudersi,
--   nei panni di un altro, che si prova.
SET CONSTRAINTS ALL DEFERRED;

DO $ctx$
BEGIN
    PERFORM script.fn_pgtap_set_contesto_operatore(
        (SELECT auth_user_id FROM _mondi WHERE lato = 'MIA'));
END $ctx$;

SELECT plan(9);

-- Il codice di dominio di un rifiuto: fn_log_and_raise_error lo scrive in CONSTRAINT.
CREATE FUNCTION pg_temp.codice_di(p_sql text) RETURNS text
LANGUAGE plpgsql AS $$
DECLARE v_c text;
BEGIN
    EXECUTE p_sql;
    RETURN NULL;
EXCEPTION WHEN SQLSTATE 'P0001' THEN
    GET STACKED DIAGNOSTICS v_c = CONSTRAINT_NAME;
    RETURN v_c;
END $$;

-- ============================================================
-- 1) La premessa
-- ============================================================
SELECT set_eq(
    $$SELECT n.nspname::text, c.relname::text, c.relrowsecurity, c.relforcerowsecurity
        FROM pg_catalog.pg_class c
        JOIN pg_catalog.pg_namespace n ON n.oid = c.relnamespace
       WHERE (n.nspname, c.relname) IN (('vendite', 'listini'), ('vendite', 'listini_versioni'),
                                        ('config', 'listini_tipologie'))$$,
    $$VALUES ('config', 'listini_tipologie', false, false),
             ('vendite', 'listini', true, false),
             ('vendite', 'listini_versioni', true, false)$$,
    '1) premessa: listini e versioni sotto RLS non forzata, la tipologia senza RLS'
);

-- ============================================================
-- Fixture: una tipologia nuova, e il listino di ALTRUI che la usa
-- ============================================================
-- ⭐ Dal super admin: creare un documento fuori dal proprio perimetro e'
--   esattamente cio' che l'operatore non puo' fare. La versione del listino
--   lascia in sospeso il require differito verso il listino.
DO $fixture$
DECLARE
    v_super      integer;   -- ⚠️ niente %TYPE su django.*
    v_utility    config.utilities.id%TYPE;
    v_tipologia  config.listini_tipologie.id%TYPE;
    v_listino_id vendite.listini.id%TYPE;
BEGIN
    SELECT m.auth_user_id INTO v_super FROM _mondi m WHERE m.lato = 'SA';
    PERFORM script.fn_pgtap_set_contesto_operatore(v_super);

    SELECT u.id INTO v_utility FROM config.utilities u ORDER BY u.id LIMIT 1;

    INSERT INTO config.listini_tipologie (codice, descrizione, e_servizio)
    VALUES ('PGTAP_D51_' || substring(md5(clock_timestamp()::text) from 1 for 6),
            'tipologia di prova: occhi del proprietario', true)
    RETURNING id INTO v_tipologia;

    -- la coppia utility/tipologia la pretende il guard del listino
    INSERT INTO config.listini_tipologie_utilities (utility_id, tipologia_id)
    VALUES (v_utility, v_tipologia);

    INSERT INTO vendite.listini
        (codice, descrizione, utility_id, tipologia_id, emittente_soggetto_ruolo_id)
    VALUES ('PGTAP-D51-' || substring(md5(clock_timestamp()::text) from 1 for 6),
            'listino di un altro emittente, per gli occhi del proprietario',
            v_utility, v_tipologia,
            (SELECT m.soggetto_ruolo_id FROM _mondi m WHERE m.lato = 'ALTRUI'))
    RETURNING id INTO v_listino_id;

    -- ⚠️ `validita` e' una colonna GENERATA: non si scrive.
    INSERT INTO vendite.listini_versioni (listino_id, codice_versione, valido_dal)
    VALUES (v_listino_id, 'V-PGTAP', script.fn_data_operativa());

    -- La riga della matrice si spegne: e' visibile a tutti e il suo block
    --   parlerebbe prima di quello del listino (ordine dei nomi).
    UPDATE config.listini_tipologie_utilities
       SET attivo = false
     WHERE tipologia_id = v_tipologia;

    PERFORM set_config('pgtap.d51_tipologia', v_tipologia::text, true);
    PERFORM set_config('pgtap.d51_listino', v_listino_id::text, true);

    -- Si torna all'operatore di MIA, con i differiti ancora aperti.
    PERFORM script.fn_pgtap_set_contesto_operatore(
        (SELECT m.auth_user_id FROM _mondi m WHERE m.lato = 'MIA'));
END
$fixture$;

-- ============================================================
-- 2-3) Il require differito, chiuso da chi non vede il padre
-- ============================================================
SELECT is(
    (SELECT count(*)::int FROM vendite.listini
      WHERE id = current_setting('pgtap.d51_listino')::bigint),
    0,
    '2) premessa del caso: l''operatore di MIA non vede il listino di ALTRUI'
);

SELECT lives_ok(
    $$SET CONSTRAINTS ALL IMMEDIATE$$,
    '3) D51: i differiti si chiudono nei panni di MIA, e il listino attivo resta attivo anche per chi non lo vede (prima: «Padre non attivo»)'
);

-- ============================================================
-- 4-5) Il block, con una figlia che chi spegne non vede
-- ============================================================
SELECT is(
    pg_temp.codice_di(format(
        $$UPDATE config.listini_tipologie SET attivo = false WHERE id = %s$$,
        current_setting('pgtap.d51_tipologia'))),
    'E_ATTIVO_BLOCK_CHILDREN_ACTIVE',
    '4) D51: MIA non spegne la tipologia usata da un listino attivo di ALTRUI (prima: si spegneva)'
);

SELECT throws_like(
    format($$UPDATE config.listini_tipologie SET attivo = false WHERE id = %s$$,
           current_setting('pgtap.d51_tipologia')),
    '%righe collegate attive in vendite.listini.',
    '5) la frase nomina la tabella che blocca'
);

-- ============================================================
-- 6-8) Un montaggio dell'applicazione non legge niente
-- ============================================================
-- ⛔ Senza il vincolo sul proprietario, una DEFINER con SQL dinamico leggerebbe
--   qualunque colonna di qualunque tabella: bastava un trigger con argomenti a
--   piacere su una TEMP propria.
CREATE TEMP TABLE t_finta (id bigint PRIMARY KEY, x_id bigint);
CREATE TEMP TABLE t_finto_padre (id bigint PRIMARY KEY, attivo boolean NOT NULL DEFAULT true);

DO $finto$
DECLARE
    v_s pg_catalog.pg_namespace.nspname%TYPE :=
        (SELECT n.nspname FROM pg_catalog.pg_namespace n WHERE n.oid = pg_my_temp_schema());
BEGIN
    EXECUTE format($t$CREATE TRIGGER trg_finto_require AFTER INSERT ON %1$I.t_finta FOR EACH ROW
        EXECUTE FUNCTION dbops.trgfn_child_requires_active_parent('config', 'utilities', 'attivo', 'x_id', 'id')$t$, v_s);
    EXECUTE format($t$CREATE TRIGGER trg_finto_block BEFORE UPDATE OF attivo ON %1$I.t_finto_padre FOR EACH ROW
        EXECUTE FUNCTION dbops.trgfn_prevent_deactivate_if_children('config', 'listini_tipologie_utilities', 'utility_id', 'id', 'attivo')$t$, v_s);
END
$finto$;

SELECT is(
    pg_temp.codice_di($$SELECT * FROM dbops.fn_trigger_padre_stato('t_finta'::regclass, 'trg_finto_require', '1')$$),
    'E_DBOPS_CHIAMATA_NON_VALIDA',
    '6) un require montato dall''applicazione su una TEMP sua: la lettura del padre rifiuta'
);

SELECT is(
    pg_temp.codice_di($$INSERT INTO t_finta (id, x_id) VALUES (1, 1)$$),
    'E_DBOPS_CHIAMATA_NON_VALIDA',
    '7) ... e il trigger, scattando, non legge niente'
);

SELECT is(
    pg_temp.codice_di($$SELECT * FROM dbops.fn_trigger_figlie_presenti('t_finto_padre'::regclass, 'trg_finto_block', '1')$$),
    'E_DBOPS_CHIAMATA_NON_VALIDA',
    '8) un block montato dall''applicazione su una TEMP sua: la ricerca delle figlie rifiuta'
);

-- ============================================================
-- 9) Il presidio del proprietario
-- ============================================================
-- ⭐ Le due letture attraversano la row security perche' il loro proprietario
--   e' quello delle tabelle, e la RLS e' abilitata e non forzata. E' una
--   condizione del modello, non una coincidenza: qui si asserisce.
SELECT is_empty(
    $$WITH lettori AS (
          SELECT p.proowner
            FROM pg_catalog.pg_proc p
            JOIN pg_catalog.pg_namespace n ON n.oid = p.pronamespace
           WHERE n.nspname = 'dbops'
             AND p.proname IN ('fn_trigger_padre_stato', 'fn_trigger_figlie_presenti')
      ),
      lati AS (
          SELECT t.tgname, t.tgrelid AS rel
            FROM pg_catalog.pg_trigger t
            JOIN pg_catalog.pg_proc p ON p.oid = t.tgfoid
            JOIN pg_catalog.pg_namespace n ON n.oid = p.pronamespace
           WHERE n.nspname = 'dbops'
             AND p.proname IN ('trgfn_prevent_deactivate_if_children',
                               'trgfn_child_requires_active_parent',
                               'trgfn_child_requires_non_obsolete_parent')
             AND NOT t.tgisinternal
          UNION ALL
          SELECT t.tgname,
                 to_regclass(format('%I.%I', COALESCE(g.figlia_schema, g.padre_schema),
                                             COALESCE(g.figlia_tabella, g.padre_tabella)))
            FROM pg_catalog.pg_trigger t
            JOIN pg_catalog.pg_proc p ON p.oid = t.tgfoid
            JOIN pg_catalog.pg_namespace n ON n.oid = p.pronamespace
            CROSS JOIN LATERAL dbops.fn_trigger_attivo_argomenti(p.proname, dbops.fn_trigger_argomenti(t.tgargs)) g
           WHERE n.nspname = 'dbops'
             AND p.proname IN ('trgfn_prevent_deactivate_if_children',
                               'trgfn_child_requires_active_parent',
                               'trgfn_child_requires_non_obsolete_parent')
             AND NOT t.tgisinternal
             AND g.valido
      )
      SELECT format('%s su %s: proprietario %s, FORCE %s', l.tgname, c.oid::regclass,
                    pg_catalog.pg_get_userbyid(c.relowner), c.relforcerowsecurity)
        FROM lati l
        JOIN pg_catalog.pg_class c ON c.oid = l.rel
       WHERE c.relpersistence <> 't'
         AND (c.relforcerowsecurity
              OR EXISTS (SELECT 1 FROM lettori r WHERE r.proowner <> c.relowner))$$,
    '9) presidio: ogni trigger ATTIVO sta su tabelle del proprietario delle due letture, senza FORCE, da tutti e due i lati'
);

SELECT * FROM finish();
ROLLBACK;
