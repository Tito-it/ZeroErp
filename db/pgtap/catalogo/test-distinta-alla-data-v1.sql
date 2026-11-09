-- ------------------------------------------------------------
-- SPDX-License-Identifier: AGPL-3.0-or-later
-- pgTAP test per Zero ERP
--
-- La distinta di un padre a una data ha una sede sola.
--   - catalogo.fn_distinta_alla_data: i legami attivi del padre la cui validita
--     contiene la data (i due estremi compresi); con la data NULL nessuno; il
--     planner la espande nel chiamante;
--   - gli init e i preview dei componenti dei documenti la chiamano (qui il
--     preventivo; gli altri quattro hanno lo stesso cambio);
--   - script.trgfn_componenti_guard_coerenza_bom, guard 4: il legame sta nella
--     distinta alla data della testata, quindi anche un legame SPENTO e' rifiutato
--     con E_DOC_COMPONENTE_BOM_NON_VALIDA;
--   - script.fn_check_articolo_riga, motivo KIT_SENZA_COMPONENTI: guarda la
--     distinta da oggi in poi;
--   - catalogo.vw_articoli_dettaglio.has_componenti_alla_data: la distinta di oggi;
--   - nessun corpo di vendite, script, acquisti, magazzino e nessuna vista ricopia
--     il filtro della distinta alla data.
-- Brief: brief-db-revisione-catalogo, giro 1-bis (R2, Q15, Q16).
--
-- Elenco test (plan 17):
--  1)  il BB esiste
--  2)  BB a oggi: il legame aperto e quello che finisce oggi
--  3)  BB all'ultimo giorno del legame finito: anche quello (estremo compreso)
--  4)  BB prima dell'inizio: nessun legame
--  5)  BB al primo giorno del legame futuro: l'aperto e il futuro
--  6)  BB con la data NULL: nessun legame
--  7)  il planner espande il BB nel chiamante (nessun Function Scan)
--  8)  preview del preventivo: i componenti del BB a oggi
--  9)  init del preventivo: due componenti scritti
--  10) init del preventivo: i legami scritti sono quelli del BB
--  11) guard: componente su un legame spento -> E_DOC_COMPONENTE_BOM_NON_VALIDA
--  12) guard: componente su un legame finito -> E_DOC_COMPONENTE_BOM_NON_VALIDA
--  13) guard: UPDATE del prezzo di un componente valido -> passa
--  14) check: kit con la sola distinta passata -> KIT_SENZA_COMPONENTI
--  15) check: kit con la sola distinta futura -> nessun KIT_SENZA_COMPONENTI
--  16) vista: has_componenti_alla_data per il kit, il kit passato, il kit futuro
--  17) presidio: nessun corpo e nessuna vista ricopia il filtro
--
-- Fixture costruita (ROLLBACK finale): tutti gli articoli dal builder, i legami
-- con date relative al giorno aziendale, il preventivo dal builder.
-- ------------------------------------------------------------

BEGIN;

-- Vincoli differiti a fine istruzione: senza, al ROLLBACK non scatterebbero mai.
SET CONSTRAINTS ALL IMMEDIATE;

DO $ctx$ BEGIN PERFORM script.fn_pgtap_set_contesto_operatore(); END $ctx$;

SELECT plan(17);

CREATE TEMP TABLE _t_art AS
SELECT dbops.fn_pgtap_crea_articolo('PGT-DAD-KIT',      p_is_composito => true) AS kit,
       dbops.fn_pgtap_crea_articolo('PGT-DAD-KIT-PASS', p_is_composito => true) AS kit_pass,
       dbops.fn_pgtap_crea_articolo('PGT-DAD-KIT-FUT',  p_is_composito => true) AS kit_fut,
       dbops.fn_pgtap_crea_articolo('PGT-DAD-C1')                               AS c1,
       dbops.fn_pgtap_crea_articolo('PGT-DAD-C2')                               AS c2,
       dbops.fn_pgtap_crea_articolo('PGT-DAD-C3')                               AS c3,
       dbops.fn_pgtap_crea_articolo('PGT-DAD-C4')                               AS c4,
       dbops.fn_pgtap_crea_articolo('PGT-DAD-C5')                               AS c5;

-- Un legame: (padre, componente, inizio, fine, attivo)
CREATE FUNCTION pg_temp.legame(p_padre uuid, p_comp uuid, p_dal date, p_al date, p_attivo boolean DEFAULT true)
 RETURNS uuid
 LANGUAGE sql
AS $f$
    INSERT INTO catalogo.articoli_componenti (prodotto_id, componente_id, coeff_qta, obbligatorio, valido_dal, valido_al, attivo)
    VALUES (p_padre, p_comp, 1, true, p_dal, p_al, p_attivo)
    RETURNING id;
$f$;

-- Il kit: un legame finito, uno aperto, uno futuro, uno spento, uno che finisce oggi.
CREATE TEMP TABLE _t_leg AS
SELECT pg_temp.legame(a.kit, a.c1, script.fn_data_operativa() - 20, script.fn_data_operativa() - 5)  AS finito,
       pg_temp.legame(a.kit, a.c2, script.fn_data_operativa() - 20, NULL)                            AS aperto,
       pg_temp.legame(a.kit, a.c3, script.fn_data_operativa() + 3,  NULL)                            AS futuro,
       pg_temp.legame(a.kit, a.c4, script.fn_data_operativa() - 20, NULL, false)                     AS spento,
       pg_temp.legame(a.kit, a.c5, script.fn_data_operativa() - 20, script.fn_data_operativa())      AS bordo,
       pg_temp.legame(a.kit_pass, a.c1, script.fn_data_operativa() - 20, script.fn_data_operativa() - 1) AS pass,
       pg_temp.legame(a.kit_fut,  a.c1, script.fn_data_operativa() + 1,  NULL)                       AS fut
  FROM _t_art a;

-- I codici dei componenti del BB, in ordine
CREATE FUNCTION pg_temp.bb(p_padre uuid, p_data date)
 RETURNS text
 LANGUAGE sql
AS $f$
    SELECT coalesce(string_agg(a.codice, ',' ORDER BY a.codice), '')
      FROM catalogo.fn_distinta_alla_data(p_padre, p_data) d
      JOIN catalogo.articoli a ON a.id = d.componente_id;
$f$;

-- Il piano di una query, come testo
CREATE FUNCTION pg_temp.piano(p_query text)
 RETURNS text
 LANGUAGE plpgsql
AS $f$
DECLARE
    v_riga record;
    v_out  text := '';
BEGIN
    FOR v_riga IN EXECUTE 'EXPLAIN (COSTS OFF) ' || p_query LOOP
        v_out := v_out || v_riga."QUERY PLAN" || E'\n';
    END LOOP;
    RETURN v_out;
END;
$f$;

-- ============================================================
-- Il BB (1-7)
-- ============================================================
SELECT has_function('catalogo', 'fn_distinta_alla_data', ARRAY['uuid', 'date'],
    '1) catalogo.fn_distinta_alla_data(uuid, date) esiste');

SELECT is(pg_temp.bb((SELECT kit FROM _t_art), script.fn_data_operativa()),
          'PGT-DAD-C2,PGT-DAD-C5',
    '2) a oggi: l''aperto e quello che finisce oggi; non il finito, il futuro, lo spento');

SELECT is(pg_temp.bb((SELECT kit FROM _t_art), script.fn_data_operativa() - 5),
          'PGT-DAD-C1,PGT-DAD-C2,PGT-DAD-C5',
    '3) all''ultimo giorno del legame finito c''e'' anche lui: l''estremo e'' compreso');

SELECT is(pg_temp.bb((SELECT kit FROM _t_art), script.fn_data_operativa() - 21),
          '',
    '4) prima dell''inizio: nessun legame');

SELECT is(pg_temp.bb((SELECT kit FROM _t_art), script.fn_data_operativa() + 3),
          'PGT-DAD-C2,PGT-DAD-C3',
    '5) al primo giorno del futuro: l''aperto e il futuro');

SELECT is(pg_temp.bb((SELECT kit FROM _t_art), NULL),
          '',
    '6) data NULL: nessun legame, la data non si sottintende');

SELECT unalike(
    pg_temp.piano(format(
        'SELECT d.id FROM catalogo.articoli a, catalogo.fn_distinta_alla_data(a.id, %L::date) d WHERE a.id = %L',
        script.fn_data_operativa(), (SELECT kit FROM _t_art))),
    '%Function Scan%',
    '7) il planner espande il BB nel chiamante');

-- ============================================================
-- Il preventivo: preview e init (8-10)
-- ============================================================
CREATE TEMP TABLE _t_prev AS
SELECT * FROM dbops.fn_pgtap_crea_preventivo('PGT-DAD', 'DRAFT');

-- La riga del kit, in bozza
CREATE FUNCTION pg_temp.riga_kit()
 RETURNS bigint
 LANGUAGE sql
AS $f$
    INSERT INTO vendite.preventivi_righe (preventivo_id, articolo_id, iva_id, prezzo_unitario, qta_operativa)
    SELECT p.preventivo_id, a.kit, ka.iva_id, 10, 1
      FROM _t_prev p, _t_art a
      JOIN catalogo.articoli ka ON ka.id = a.kit
    RETURNING id;
$f$;

CREATE TEMP TABLE _t_riga AS SELECT pg_temp.riga_kit() AS id;

SELECT is(
    (SELECT string_agg(pv.componente_codice, ',' ORDER BY pv.componente_codice)
       FROM _t_prev p,
            vendite.fn_preventivo_riga_componenti_preview(
                (SELECT kit FROM _t_art),
                (SELECT uom_id FROM catalogo.articoli WHERE id = (SELECT kit FROM _t_art)),
                1, script.fn_data_operativa(),
                p.billing_account_id, p.utility_id, p.emittente_soggetto_ruolo_id) pv),
    'PGT-DAD-C2,PGT-DAD-C5',
    '8) preview: i componenti della distinta a oggi');

SELECT is(
    vendite.fn_preventivo_riga_componenti_init(
        (SELECT id FROM _t_riga),
        (SELECT emittente_soggetto_ruolo_id FROM _t_prev),
        script.fn_data_operativa(),
        jsonb_build_object((SELECT c2 FROM _t_art)::text, 5, (SELECT c5 FROM _t_art)::text, 7)),
    2,
    '9) init: due componenti scritti');

SELECT is(
    (SELECT array_agg(prc.articolo_componente_id ORDER BY prc.articolo_componente_id)
       FROM vendite.preventivi_righe_componenti prc
      WHERE prc.riga_preventivo_id = (SELECT id FROM _t_riga)),
    (SELECT array_agg(x ORDER BY x) FROM _t_leg l, unnest(ARRAY[l.aperto, l.bordo]) x),
    '10) init: i legami scritti sono quelli della distinta a oggi');

-- ============================================================
-- Il guard dei componenti di documento (11-13)
-- ============================================================
-- Un componente scritto a mano sulla riga del kit, sul legame dato
CREATE FUNCTION pg_temp.componente_su(p_legame uuid)
 RETURNS text
 LANGUAGE sql
AS $f$
    SELECT format($q$INSERT INTO vendite.preventivi_righe_componenti
                      (riga_preventivo_id, articolo_componente_id, componente_id,
                       coeff_qta_snapshot, quantita, prezzo_unitario, origine_prezzo, uom_operativa_id)
                  SELECT %s, ac.id, ac.componente_id, 1, 1, 5, 'MANUALE', a.uom_id
                    FROM catalogo.articoli_componenti ac
                    JOIN catalogo.articoli a ON a.id = ac.componente_id
                   WHERE ac.id = %L$q$,
                  (SELECT id FROM _t_riga), p_legame);
$f$;

-- Prima dell'1-bis il legame spento passava il guard e lo fermava il vincolo
-- differito generato, con E_ATTIVO_PADRE_NON_ATTIVO: la frase qui sotto lo distingue.
SELECT throws_like(
    pg_temp.componente_su((SELECT spento FROM _t_leg)),
    '%non e'' valida alla data documento%',
    '11) componente su un legame spento: E_DOC_COMPONENTE_BOM_NON_VALIDA dal guard');

SELECT throws_like(
    pg_temp.componente_su((SELECT finito FROM _t_leg)),
    '%non e'' valida alla data documento%',
    '12) componente su un legame finito: E_DOC_COMPONENTE_BOM_NON_VALIDA');

SELECT lives_ok(
    format($q$UPDATE vendite.preventivi_righe_componenti SET prezzo_unitario = 6
               WHERE riga_preventivo_id = %s AND articolo_componente_id = %L$q$,
           (SELECT id FROM _t_riga), (SELECT aperto FROM _t_leg)),
    '13) UPDATE del prezzo di un componente valido: il guard lo lascia passare');

-- ============================================================
-- La check: il kit senza distinta da oggi in poi (14-15)
-- ============================================================
SELECT ok(
    script.fn_check_articolo_riga('PREVENTIVO', (SELECT preventivo_id FROM _t_prev),
                                  (SELECT kit_pass FROM _t_art))
      @> '[{"reason": "KIT_SENZA_COMPONENTI"}]'::jsonb,
    '14) kit con la sola distinta passata: KIT_SENZA_COMPONENTI');

SELECT ok(
    NOT script.fn_check_articolo_riga('PREVENTIVO', (SELECT preventivo_id FROM _t_prev),
                                      (SELECT kit_fut FROM _t_art))
      @> '[{"reason": "KIT_SENZA_COMPONENTI"}]'::jsonb,
    '15) kit con la sola distinta futura: non e'' un kit senza distinta');

-- ============================================================
-- La vista (16)
-- ============================================================
SELECT is(
    (SELECT string_agg(v.codice || ':' || v.has_componenti_alla_data::text, ',' ORDER BY v.codice)
       FROM catalogo.vw_articoli_dettaglio v
      WHERE v.id IN (SELECT kit FROM _t_art UNION ALL SELECT kit_pass FROM _t_art
                     UNION ALL SELECT kit_fut FROM _t_art)),
    'PGT-DAD-KIT:true,PGT-DAD-KIT-FUT:false,PGT-DAD-KIT-PASS:false',
    '16) has_componenti_alla_data: la distinta di oggi');

-- ============================================================
-- Il presidio: la copia non rientra (17)
-- ============================================================
-- Una query che legge catalogo.articoli_componenti con un alias e poi chiede
-- «alias.validita @>» nella stessa istruzione e' il filtro della distinta alla
-- data scritto a mano. I predicati di catalogo non sono nel perimetro: sono il BB
-- e le domande sorelle (padre da oggi, componente in vigore).
SELECT is(
    (SELECT coalesce(string_agg(nome, ', ' ORDER BY nome), '')
       FROM (SELECT p.oid::regprocedure::text AS nome, pg_get_functiondef(p.oid) AS corpo
               FROM pg_proc p
               JOIN pg_namespace n ON n.oid = p.pronamespace
               JOIN pg_language l ON l.oid = p.prolang
              WHERE n.nspname IN ('vendite', 'script', 'acquisti', 'magazzino')
                AND p.prokind = 'f'
                AND l.lanname IN ('sql', 'plpgsql')
             UNION ALL
             SELECT c.oid::regclass::text, pg_get_viewdef(c.oid)
               FROM pg_class c
               JOIN pg_namespace n ON n.oid = c.relnamespace
              WHERE n.nspname IN ('catalogo', 'vendite', 'script', 'acquisti', 'magazzino')
                AND c.relkind IN ('v', 'm')) o
      WHERE o.corpo ~ 'catalogo\.articoli_componenti\s+(\w+)[^;]*\m\1\.validita\s*@>'),
    '',
    '17) nessun corpo e nessuna vista ricopia il filtro della distinta alla data');

SELECT * FROM finish();
ROLLBACK;
