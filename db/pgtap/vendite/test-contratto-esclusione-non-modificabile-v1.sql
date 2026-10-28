-- ------------------------------------------------------------
-- SPDX-License-Identifier: GPL-3.0-or-later
-- pgTAP test per Zero ERP
-- rev 2026-10-28 (brief-modello-documento-vendita §16, giro 12): la versione PGTAP_CEN_V2 nasce senza stato (BOZZA) e si attiva dalla fixture dbops.fn_pgtap_porta_a_stato, non con l'UPDATE dello stato.
--
-- Test: un'esclusione del contratto non si modifica — si crea (Escludi) e si
--   cancella (Ripristina articolo), e basta. Decisione di Tid del 2026-10-04.
--   Brief: brief-db-contratto-esclusione-non-modificabile (R1, R2, R3, R5).
--   changeSet: 20261004-12 (guard), -13 (trigger), -14 (anteprima); lock di
--   colonna su tipo_eccezione in dbops.automation_lock_columns (R3).
--
-- ⭐ TUTTO COSTRUITO: azienda, cliente, listino, articoli, contratto e righe
--   nascono qui (builder dbops.fn_pgtap_crea_*). Nessuna riga letta dal
--   database: vale anche su un DB ricostruito da zero, come in CI.
--
-- LA FIXTURE — un contratto in bozza su un listino con quattro articoli:
--   A  dal listino, nessuna eccezione   (bersaglio dello spostamento, test 7)
--   B  dal listino, prezzo forzato      -> OVERRIDE, resta modificabile
--   C  dal listino, escluso             -> ESCLUSIONE, l'esaminata
--   D  dal listino, escluso             -> ESCLUSIONE, la si ripristina (DELETE)
--
-- ⛔ COSA PRESIDIA:
--   · l'anteprima non offre MODIFICA sull'esclusione (R1);
--   · ogni colonna di contenuto e' rifiutata, `attivo` e le FK comprese, e il
--     rifiuto parla prima del CHECK sul prezzo (R2, fascia _a05_);
--   · le uscite legittime restano aperte: UPDATE senza cambi, DELETE, e le
--     righe OVERRIDE si modificano come prima (§4 del brief);
--   · il tipo di riga e' immutabile per tutti (R3, lock di colonna).
--
-- Indice test (1..15):
--    1) precondizione: B e' un OVERRIDE, C e D sono ESCLUSIONE
--    2) il trigger e' montato: _a05_, BEFORE UPDATE, per riga, WHEN sul tipo vecchio
--    3) R1: l'anteprima da' all'esclusione il solo RIPRISTINA_ARTICOLO
--    4) R1: l'OVERRIDE conserva MODIFICA
--    5) R2: la quantita' su un'esclusione e' rifiutata
--    6) R2: il prezzo e' rifiutato dal guard, non dal CHECK sul prezzo
--    7) R2: spostare l'esclusione su un altro articolo e' rifiutato
--    8) R2: disattivarla e' rifiutato (lo slot resterebbe occupato)
--    9) R2: il cambio di tipo DA esclusione e' rifiutato col messaggio dell'esclusione
--   10) un UPDATE che non cambia niente passa
--   11) un UPDATE delle sole colonne tecniche passa
--   12) Ripristina articolo (DELETE) passa
--   13) l'OVERRIDE resta modificabile
--   14) R3: il lock su tipo_eccezione e' dichiarato nel registro, col suo codice
--   15) R3: ...e il lock generato rifiuta OVERRIDE -> ESCLUSIONE — skip se non ancora generato
-- ------------------------------------------------------------

BEGIN;
-- Contesto applicativo (preambolo, guardrail_pgtap_preambolo): il builder del
-- mondo lo riapre poi sul suo operatore.
DO $ctx$ BEGIN PERFORM script.fn_pgtap_set_contesto_operatore(); END $ctx$;
-- ⚠️ Vincoli DIFFERITI: senza questa riga il test smetterebbe di verificarli.
SET CONSTRAINTS ALL IMMEDIATE;

SELECT plan(15);

-- ============================================================
-- FIXTURE
-- ============================================================
-- Il mondo apre anche il contesto applicativo (azienda + operatore).
CREATE TEMP TABLE tmp_cen_mondo AS
SELECT * FROM dbops.fn_pgtap_crea_mondo_cliente('esclusione contratto');

-- La versione del builder nasce ATTIVA e finisce nel 2020; quella che copre
-- OGGI si costruisce qui: BOZZA, righe, poi ATTIVA — la strada di un listino vero.
CREATE TEMP TABLE tmp_cen_listino AS
SELECT * FROM dbops.fn_pgtap_crea_listino(
    (SELECT utility_id FROM tmp_cen_mondo), 'esclusione contratto',
    '2020-01-01'::date, '2020-12-31'::date);

CREATE TEMP TABLE tmp_cen_ver AS
WITH ins AS (
    INSERT INTO vendite.listini_versioni (listino_id, codice_versione, valido_dal)
    SELECT listino_id, 'PGTAP_CEN_V2', '2021-01-01'::date FROM tmp_cen_listino
    RETURNING id
)
SELECT id FROM ins;

-- Un listino TIPIZZATO accetta solo articoli della sua tipologia: nascono in quella.
CREATE TEMP TABLE tmp_cen_art AS
SELECT v.sigla, dbops.fn_pgtap_crea_articolo('PGTAP-CEN-' || v.sigla,
           p_listino_tipologia_id => (SELECT tipologia_id FROM tmp_cen_listino)) AS id
  FROM (VALUES ('A'), ('B'), ('C'), ('D')) AS v(sigla);

-- Scopo: id di un articolo della fixture per sigla.
CREATE OR REPLACE FUNCTION pg_temp.art(p_sigla text)
RETURNS uuid LANGUAGE sql STABLE AS $fx$
  SELECT id FROM tmp_cen_art WHERE sigla = p_sigla;
$fx$;

INSERT INTO vendite.listini_righe (listino_versione_id, articolo_id, uom_id, prezzo)
SELECT (SELECT id FROM tmp_cen_ver), a.id, ar.uom_id, 100.00
  FROM tmp_cen_art a JOIN catalogo.articoli ar ON ar.id = a.id;

SELECT dbops.fn_pgtap_porta_a_stato('vendite.listini_versioni'::regclass, (SELECT id FROM tmp_cen_ver), 'ATTIVA');

-- Il contratto in BOZZA: il rifiuto «fuori bozza» del documento non c'entra.
CREATE TEMP TABLE tmp_cen_contratto AS
WITH ins AS (
    INSERT INTO vendite.contratti (numero, billing_account_id, istanza_utility_id, utility_id,
           stato_doc_contratto_id, listino_id, valido_dal, valido_al)
    SELECT 'PGTAP-CEN-' || substr(gen_random_uuid()::text, 1, 8),
           m.billing_account_id, m.istanza_utility_id, m.utility_id,
           (SELECT id FROM config.stati_doc_contratti WHERE codice_interno = 'DRAFT'),
           (SELECT listino_id FROM tmp_cen_listino),
           script.fn_data_operativa(), script.fn_data_operativa() + 365
      FROM tmp_cen_mondo m
    RETURNING id
)
SELECT id FROM ins;

-- Scopo: la fonte che la riga eredita dall'articolo (la combinazione di default).
CREATE OR REPLACE FUNCTION pg_temp.fonte_default(p_articolo uuid)
RETURNS text LANGUAGE sql STABLE AS $fx$
  SELECT e.fonte_quantita_attesa::text FROM vendite.fn_articolo_erogazioni(p_articolo) e WHERE e.e_default;
$fx$;

-- Scopo: una riga di contratto (eccezione) sull'articolo della sigla.
CREATE OR REPLACE FUNCTION pg_temp.riga(p_sigla text, p_tipo text, p_prezzo numeric)
RETURNS bigint LANGUAGE sql AS $fx$
  INSERT INTO vendite.contratti_righe (contratto_id, articolo_id, tipo_eccezione, prezzo_unitario,
         tipo_erogazione, fonte_quantita_attesa, quantita, qta_operativa, uom_operativa_id)
  SELECT (SELECT id FROM tmp_cen_contratto), a.id, p_tipo::vendite.tipo_eccezione_contratto,
         p_prezzo,
         -- rev 2026-10-04 (brief-db-righe-esclusione-solo-non-si-vende): un'ESCLUSIONE
         -- nasce vuota, senza dati di vendita; le altre righe coi dati di una riga
         -- che si fattura.
         -- rev 2026-10-07 (brief-db-offerta-emissione-ed-erogazione §C.9, giro B3):
         -- erogazione e fonte VUOTE, la riga le eredita dall'articolo (la tipologia
         -- del listino del test). Erano CANONE/FISSA scritte a mano, fuori dal
         -- perimetro di un articolo CONSUMO.
         -- rev 2026-10-07 (§D.4 punto 2, 20261007-28/-30): la quantita' solo se la
         -- fonte ereditata la porta (FISSA); con una fonte a valle resta vuota.
         -- Si chiede alla sede unica, perche' la tipologia e' quella del builder.
         NULL,
         NULL,
         CASE WHEN p_tipo <> 'ESCLUSIONE' AND pg_temp.fonte_default(a.id) = 'FISSA' THEN 1 END,
         CASE WHEN p_tipo <> 'ESCLUSIONE' AND pg_temp.fonte_default(a.id) = 'FISSA' THEN 1 END,
         CASE WHEN p_tipo <> 'ESCLUSIONE' THEN a.uom_id END
    FROM catalogo.articoli a WHERE a.id = pg_temp.art(p_sigla)
  RETURNING id;
$fx$;

CREATE TEMP TABLE tmp_cen_righe AS
SELECT v.sigla, pg_temp.riga(v.sigla, v.tipo, v.prezzo) AS id
  FROM (VALUES ('B', 'OVERRIDE', 80.00), ('C', 'ESCLUSIONE', NULL), ('D', 'ESCLUSIONE', NULL))
       AS v(sigla, tipo, prezzo);

-- Scopo: id della riga di contratto per sigla.
CREATE OR REPLACE FUNCTION pg_temp.rid(p_sigla text)
RETURNS bigint LANGUAGE sql STABLE AS $fx$
  SELECT id FROM tmp_cen_righe WHERE sigla = p_sigla;
$fx$;

CREATE TEMP TABLE tmp_cen_lista AS
SELECT * FROM vendite.fn_contratto_righe_preview((SELECT id FROM tmp_cen_contratto));

-- ============================================================
-- 1..4 — montaggio e verbi
-- ============================================================
SELECT is(
    (SELECT string_agg(r.sigla || ':' || cr.tipo_eccezione::text, ' ' ORDER BY r.sigla)
       FROM tmp_cen_righe r JOIN vendite.contratti_righe cr ON cr.id = r.id),
    'B:OVERRIDE C:ESCLUSIONE D:ESCLUSIONE',
    '1) precondizione: B e'' un OVERRIDE, C e D sono ESCLUSIONE');

-- Per funzione e per nome: il trigger e' scritto a mano (20261004-13).
-- tgtype: 1 = ROW, 2 = BEFORE, 16 = UPDATE; nessun altro evento.
SELECT ok(
    (SELECT count(*) = 1
            AND bool_and(t.tgtype = (1 | 2 | 16))
            AND bool_and(pg_get_triggerdef(t.oid) LIKE '%WHEN ((old.tipo_eccezione = ''ESCLUSIONE''::vendite.tipo_eccezione_contratto))%')
       FROM pg_trigger t
      WHERE t.tgrelid = 'vendite.contratti_righe'::regclass
        AND NOT t.tgisinternal
        AND t.tgname = 'trg_contratti_righe_a05_guard_esclusione_immutabile_upd'
        -- to_regprocedure: funzione assente = test rosso, non errore che ferma il file.
        -- rev 2026-10-04: la funzione generica per contratto e offerta.
        AND t.tgfoid = to_regprocedure('script.trgfn_righe_guard_esclusione_immutabile()')),
    '2) il guard e'' montato: _a05_, BEFORE UPDATE, per riga, WHEN sul tipo vecchio');

SELECT is(
    (SELECT azioni FROM tmp_cen_lista WHERE articolo_id = pg_temp.art('C') AND origine = 'ESCLUSIONE'),
    ARRAY['RIPRISTINA_ARTICOLO'],
    '3) R1: l''esclusione ha il solo Ripristina articolo, niente Modifica');

SELECT is(
    (SELECT azioni FROM tmp_cen_lista WHERE articolo_id = pg_temp.art('B') AND origine = 'OVERRIDE'),
    ARRAY['MODIFICA', 'RIPRISTINA_LISTINO'],
    '4) R1: il prezzo forzato conserva Modifica');

-- ============================================================
-- 5..9 — il guard: ogni colonna di contenuto e' rifiutata
-- ============================================================
-- ⚠️ Sul TESTO del messaggio a catalogo, non su «un errore qualsiasi»: un
--    rifiuto di altra natura (un vincolo, un altro guard) non deve passare per
--    questo.
SELECT throws_like(
    format($$UPDATE vendite.contratti_righe SET quantita = 2, qta_operativa = 2 WHERE id = %s$$,
           pg_temp.rid('C')),
    '%Un articolo escluso non si modifica%',
    '5) R2: la quantita'' su un''esclusione e'' rifiutata');

-- ⭐ Il caso che dice perche' _a05_: il CHECK chk_contrighe_prezzo_per_tipo_eccezione
--    direbbe «un'esclusione non ha prezzo», cioe' «togli il prezzo e riprova».
SELECT throws_like(
    format($$UPDATE vendite.contratti_righe SET prezzo_unitario = 10 WHERE id = %s$$,
           pg_temp.rid('C')),
    '%Un articolo escluso non si modifica%',
    '6) R2: il prezzo e'' rifiutato dal guard, prima del CHECK sul prezzo');

SELECT throws_like(
    format($$UPDATE vendite.contratti_righe SET articolo_id = %L WHERE id = %s$$,
           pg_temp.art('A'), pg_temp.rid('C')),
    '%Un articolo escluso non si modifica%',
    '7) R2: spostare l''esclusione su un altro articolo e'' rifiutato');

SELECT throws_like(
    format($$UPDATE vendite.contratti_righe SET attivo = false WHERE id = %s$$,
           pg_temp.rid('C')),
    '%Un articolo escluso non si modifica%',
    '8) R2: disattivarla e'' rifiutato (terrebbe occupato lo slot dell''articolo)');

SELECT throws_like(
    format($$UPDATE vendite.contratti_righe SET tipo_eccezione = 'OVERRIDE', prezzo_unitario = 90 WHERE id = %s$$,
           pg_temp.rid('C')),
    '%Un articolo escluso non si modifica%',
    '9) R2: il cambio di tipo da esclusione parla col messaggio dell''esclusione');

-- ============================================================
-- 10..13 — le uscite legittime restano aperte
-- ============================================================
SELECT lives_ok(
    format($$UPDATE vendite.contratti_righe SET quantita = quantita, tipo_erogazione = tipo_erogazione WHERE id = %s$$,
           pg_temp.rid('C')),
    '10) un UPDATE che non cambia niente passa');

SELECT lives_ok(
    format($$UPDATE vendite.contratti_righe SET data_update = now() - interval '1 minute', user_update = 'pgtap' WHERE id = %s$$,
           pg_temp.rid('C')),
    '11) un UPDATE delle sole colonne tecniche passa');

SELECT lives_ok(
    format($$DELETE FROM vendite.contratti_righe WHERE id = %s$$, pg_temp.rid('D')),
    '12) Ripristina articolo (DELETE) passa');

SELECT lives_ok(
    -- rev 2026-10-07 (§D.4 punto 2): solo il prezzo. La quantita' dipende dalla fonte
    -- ereditata (con una fonte a valle e' vietata), e non e' il soggetto del test.
    format($$UPDATE vendite.contratti_righe SET prezzo_unitario = 70 WHERE id = %s$$,
           pg_temp.rid('B')),
    '13) il prezzo forzato resta modificabile');

-- ============================================================
-- 14..15 — R3: il tipo di riga e' identita'
-- ============================================================
-- ⛔ La sede e' il LOCK DI COLONNA, non un ramo del guard: dal 2026-09-26 il
--   registro e' l'unica sede di un lock (brief-db-lock-di-colonna-fuori-registro).
SELECT is(
    (SELECT string_agg(l.error_code, ' ')
       FROM dbops.automation_lock_columns l
      WHERE l.target_schema = 'vendite'
        AND l.target_table  = 'contratti_righe'
        AND l.column_name   = 'tipo_eccezione'
        AND l.enabled),
    'E_CONTRATTO_RIGA_TIPO_ECCEZIONE_IMMUTABILE',
    '14) R3: tipo_eccezione e'' dichiarato immutabile, col suo codice');

-- Il trigger lo genera l'automazione: si cerca per FUNZIONE e argomenti, mai per nome.
-- OVERRIDE -> ESCLUSIONE col prezzo tolto: nessun guard _a10_ che venga prima del
-- lock ha da dire (B non e' figlio di bundle, non e' in attesa di approvazione).
SELECT CASE
    WHEN EXISTS (SELECT 1 FROM pg_trigger t JOIN pg_proc p ON p.oid = t.tgfoid
                  WHERE t.tgrelid = 'vendite.contratti_righe'::regclass AND NOT t.tgisinternal
                    AND p.proname = 'trgfn_lock_columns'
                    AND pg_get_triggerdef(t.oid) LIKE '%''tipo_eccezione''%')
    THEN throws_like(
        format($$UPDATE vendite.contratti_righe SET tipo_eccezione = 'ESCLUSIONE', prezzo_unitario = NULL WHERE id = %s$$,
               pg_temp.rid('B')),
        '%Il tipo di una riga non si cambia (colonna tipo_eccezione)%',
        '15) R3: il lock generato rifiuta OVERRIDE -> ESCLUSIONE')
    ELSE skip('15) lock su tipo_eccezione non ancora generato (ci_apply / job automations_lock_columns): niente da misurare', 1)
END;

SELECT * FROM finish();
ROLLBACK;
