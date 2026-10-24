-- ------------------------------------------------------------
-- SPDX-License-Identifier: GPL-3.0-or-later
-- pgTAP test per Zero ERP
--
-- Test: una riga di contratto o di offerta che si fattura (ogni tipo che non e'
--   ESCLUSIONE: OVERRIDE e AGGIUNTA) dice come si eroga. Decisione di Tid del
--   2026-10-04. Brief: brief-db-erogazione-obbligatoria-righe-fatturate (R1, R2,
--   R3, R5). changeSet: 20261004-30 (CHECK), -31 (guard), -32 (trigger).
--
-- ⭐ TUTTO COSTRUITO: azienda, cliente, listino, articoli, contratto, offerta e
--   righe nascono qui (builder dbops.fn_pgtap_crea_*). Nessuna riga letta dal
--   database: vale anche su un DB ricostruito da zero, come in CI.
--
-- LA FIXTURE — un listino con gli articoli A e C, e l'articolo E fuori listino:
--   contratto in BOZZA:  A -> OVERRIDE, C -> ESCLUSIONE, E -> AGGIUNTA
--   offerta in BOZZA:    gli stessi tre casi
--
-- ⚠️ REV 2026-10-07 (brief-db-offerta-emissione-ed-erogazione §C.9, giro B3, decisione
--   B-R2 di Tid): una riga che NON indica l'erogazione la EREDITA dall'articolo
--   (vendite.fn_articolo_erogazioni), su INSERT. Il guard d'obbligo resta, e morde
--   l'UPDATE che la svuota: e' li' che ora si misurano frase e canali. I test 5, 6, 12,
--   13 (prima: «senza erogazione rifiutato») diventano «la eredita»; 8 e 15 verificano
--   cosa eredita; 10-11 e 17-18 leggono i canali dell'UPDATE.
--
-- ⛔ COSA PRESIDIA:
--   · la regola e' scritta nella struttura delle due tabelle (CHECK), e il
--     guard e' montato sulle due (R1, R2);
--   · OVERRIDE e AGGIUNTA senza erogazione: la ereditano dall'articolo (B-R2);
--   · un UPDATE che toglie l'erogazione e' rifiutato col CODICE e col CAMPO,
--     non col 23514 del CHECK (il guard parla prima);
--   · l'ESCLUSIONE senza erogazione passa, sulle due tabelle;
--   · il lister del push non propone l'esclusione, e legge l'erogazione della
--     riga senza ripiego su CANONE (R4).
--
-- Indice test (1..21):
--    1) CHECK sul contratto: «tutto tranne ESCLUSIONE» vuole l'erogazione
--    2) CHECK sull'offerta: lo stesso
--    3) guard montato sul contratto: _a10_, BEFORE, per riga, INSERT + UPDATE OF
--    4) guard montato sull'offerta: lo stesso
--    5) contratto: OVERRIDE senza erogazione accettato: la eredita
--    6) contratto: AGGIUNTA senza erogazione accettata: la eredita
--    7) contratto: ESCLUSIONE senza erogazione accettata
--    8) contratto: l'OVERRIDE ha ereditato erogazione e fonte di default dell'articolo
--    9) contratto: togliere l'erogazione a un OVERRIDE e' rifiutato
--   10) contratto: canale CONSTRAINT = il codice (UPDATE che svuota)
--   11) contratto: canale COLUMN = tipo_erogazione
--   12) offerta: OVERRIDE senza erogazione accettato: la eredita
--   13) offerta: AGGIUNTA senza erogazione accettata: la eredita
--   14) offerta: ESCLUSIONE senza erogazione accettata
--   15) offerta: l'AGGIUNTA ha ereditato erogazione e fonte di default dell'articolo
--   16) offerta: togliere l'erogazione a un'AGGIUNTA e' rifiutato
--   17) offerta: canale CONSTRAINT = il codice
--   18) offerta: canale COLUMN = tipo_erogazione
--   19) D-2 (20261013-24): l'OVERRIDE con erogazione ereditata CONSUMO non si
--       lista: il push del contratto manda solo le UNA_TANTUM
--   20) R4: l'ESCLUSIONE non si lista (non si fattura)
--   21) l'erogazione dell'OVERRIDE e' quella ereditata e NON e' UNA_TANTUM:
--       e' cio' che rende il 19 un'esclusione per erogazione, non una coincidenza
-- ------------------------------------------------------------

BEGIN;
-- Contesto applicativo (preambolo, guardrail_pgtap_preambolo): il builder del
-- mondo lo riapre poi sul suo operatore.
DO $ctx$ BEGIN PERFORM script.fn_pgtap_set_contesto_operatore(); END $ctx$;
-- ⚠️ Vincoli DIFFERITI: senza questa riga il test smetterebbe di verificarli.
SET CONSTRAINTS ALL IMMEDIATE;

SELECT plan(21);

-- ============================================================
-- FIXTURE
-- ============================================================
-- Il mondo apre anche il contesto applicativo (azienda + operatore).
CREATE TEMP TABLE tmp_ero_mondo AS
SELECT * FROM dbops.fn_pgtap_crea_mondo_cliente('erogazione obbligatoria');

-- La versione del builder nasce ATTIVA e finisce nel 2020; quella che copre
-- OGGI si costruisce qui: BOZZA, righe, poi ATTIVA — la strada di un listino vero.
CREATE TEMP TABLE tmp_ero_listino AS
SELECT * FROM dbops.fn_pgtap_crea_listino(
    (SELECT utility_id FROM tmp_ero_mondo), 'erogazione obbligatoria',
    '2020-01-01'::date, '2020-12-31'::date);

CREATE TEMP TABLE tmp_ero_ver AS
WITH ins AS (
    INSERT INTO vendite.listini_versioni (listino_id, codice_versione, valido_dal, stato)
    SELECT listino_id, 'PGTAP_ERO_V2', '2021-01-01'::date, 'BOZZA' FROM tmp_ero_listino
    RETURNING id
)
SELECT id FROM ins;

-- Un listino TIPIZZATO accetta solo articoli della sua tipologia: nascono con quella.
CREATE TEMP TABLE tmp_ero_art AS
SELECT v.sigla, dbops.fn_pgtap_crea_articolo('PGTAP-ERO-' || v.sigla,
           p_listino_tipologia_id => (SELECT tipologia_id FROM tmp_ero_listino)) AS id
  FROM (VALUES ('A'), ('C'), ('E')) AS v(sigla);

-- Scopo: id di un articolo della fixture per sigla.
CREATE OR REPLACE FUNCTION pg_temp.art(p_sigla text)
RETURNS uuid LANGUAGE sql STABLE AS $fx$
  SELECT id FROM tmp_ero_art WHERE sigla = p_sigla;
$fx$;

-- A e C a listino; E no: e' l'articolo dell'AGGIUNTA, che sul contratto deve
-- stare fuori listino (guard _a10_guard_aggiunta_fuori_listino).
INSERT INTO vendite.listini_righe (listino_versione_id, articolo_id, uom_id, prezzo)
SELECT (SELECT id FROM tmp_ero_ver), a.id, ar.uom_id, 100.00
  FROM tmp_ero_art a JOIN catalogo.articoli ar ON ar.id = a.id
 WHERE a.sigla IN ('A', 'C');

UPDATE vendite.listini_versioni SET stato = 'ATTIVA' WHERE id = (SELECT id FROM tmp_ero_ver);

-- Il contratto in BOZZA: il rifiuto «fuori bozza» del documento non c'entra.
CREATE TEMP TABLE tmp_ero_contratto AS
WITH ins AS (
    INSERT INTO vendite.contratti (numero, billing_account_id, istanza_utility_id, utility_id,
           stato_doc_contratto_id, listino_id, valido_dal, valido_al)
    SELECT 'PGTAP-ERO-' || substr(gen_random_uuid()::text, 1, 8),
           m.billing_account_id, m.istanza_utility_id, m.utility_id,
           (SELECT id FROM config.stati_doc_contratti WHERE codice_interno = 'DRAFT'),
           (SELECT listino_id FROM tmp_ero_listino),
           script.fn_data_operativa(), script.fn_data_operativa() + 365
      FROM tmp_ero_mondo m
    RETURNING id
)
SELECT id FROM ins;

-- L'offerta in BOZZA, sullo stesso listino.
CREATE TEMP TABLE tmp_ero_offerta AS
WITH ins AS (
    INSERT INTO vendite.offerte_commerciali
           (codice, emittente_fiscale_id, billing_account_id, istanza_utility_id,
            utility_id, listino_id, listino_versione_id, validita_dal, stato_doc_offerta_id)
    SELECT 'PGTAP-ERO-O-' || substr(gen_random_uuid()::text, 1, 8),
           m.emittente_fiscale_id, m.billing_account_id, m.istanza_utility_id,
           m.utility_id, l.listino_id, (SELECT id FROM tmp_ero_ver), script.fn_data_operativa(),
           (SELECT s.id FROM config.stati_doc_offerte s WHERE s.codice_interno = 'BOZZA')
      FROM tmp_ero_mondo m, tmp_ero_listino l
    RETURNING id
)
SELECT id FROM ins;

-- Scopo: l'INSERT di una riga, come testo da dare a throws_like / lives_ok.
--   p_tabella: 'contratto' | 'offerta'. p_erogazione NULL = colonna lasciata vuota.
--   rev 2026-10-04 (brief-db-righe-esclusione-solo-non-si-vende): un'ESCLUSIONE
--   nasce VUOTA — nessun dato di vendita, ne' quantita' ne' fonte: con la regola
--   nuova la quantita' 1 e la fonte FISSA di prima sarebbero rifiutate.
--   ⚠️ L'erogazione passata e' sempre NULL (la riga eredita): la quantita' segue la
--   fonte di default dell'articolo (rev 2026-10-07, §D.4 punto 2).
CREATE OR REPLACE FUNCTION pg_temp.ins_riga(p_tabella text, p_sigla text, p_tipo text,
                                            p_erogazione text)
RETURNS text LANGUAGE sql STABLE AS $fx$
  SELECT format(
      CASE WHEN p_tipo = 'ESCLUSIONE' THEN
      $$INSERT INTO vendite.%I (%I, articolo_id, tipo_eccezione, prezzo_unitario, tipo_erogazione)
        SELECT %s, a.id, %L::vendite.tipo_eccezione_contratto, %s, %L
          FROM catalogo.articoli a WHERE a.id = %L$$
      ELSE
      $$INSERT INTO vendite.%I (%I, articolo_id, tipo_eccezione, prezzo_unitario,
               tipo_erogazione, fonte_quantita_attesa, quantita, qta_operativa, uom_operativa_id)
        SELECT %s, a.id, %L::vendite.tipo_eccezione_contratto, %s, %L, NULL, q.qta, q.qta, a.uom_id
          FROM catalogo.articoli a
          -- rev 2026-10-07 (§D.4 punto 2, 20261007-28/-30): la quantita' solo se la
          -- fonte ereditata (il default dell'articolo) la porta; a valle resta vuota.
          CROSS JOIN LATERAL (
              SELECT (SELECT 1 FROM vendite.fn_articolo_erogazioni(a.id) e
                       WHERE e.e_default AND e.fonte_quantita_attesa = 'FISSA') AS qta) q
         WHERE a.id = %L$$
      END,
      CASE p_tabella WHEN 'contratto' THEN 'contratti_righe' ELSE 'offerte_commerciali_eccezioni' END,
      CASE p_tabella WHEN 'contratto' THEN 'contratto_id' ELSE 'offerta_id' END,
      CASE p_tabella WHEN 'contratto' THEN (SELECT id FROM tmp_ero_contratto)
                                      ELSE (SELECT id FROM tmp_ero_offerta) END,
      p_tipo,
      -- il CHECK sul prezzo: ESCLUSIONE senza, le altre con
      CASE p_tipo WHEN 'ESCLUSIONE' THEN 'NULL' ELSE '80.00' END,
      p_erogazione,
      pg_temp.art(p_sigla));
$fx$;

-- Scopo: esegue uno statement che il guard deve rifiutare e ne rende i due
--   canali strutturati (CONSTRAINT = codice, COLUMN = campo). `throws_like`
--   legge solo la frase: un guard che scrivesse la chiave sbagliata nel
--   contesto lascerebbe il canale del campo VUOTO e la frase giusta.
CREATE OR REPLACE FUNCTION pg_temp.canali(p_sql text)
RETURNS text LANGUAGE plpgsql AS $fx$
DECLARE v_cst text; v_col text;
BEGIN
    BEGIN
        EXECUTE p_sql;
        RETURN 'NESSUN ERRORE';
    EXCEPTION WHEN OTHERS THEN
        GET STACKED DIAGNOSTICS v_cst = CONSTRAINT_NAME, v_col = COLUMN_NAME;
        RETURN coalesce(nullif(v_cst, ''), '-') || ' / ' || coalesce(nullif(v_col, ''), '-');
    END;
END;
$fx$;

-- ============================================================
-- 1..4 — la regola nella struttura, e il guard montato
-- ============================================================
-- ⭐ Il CHECK non e' ridondante col guard: presidia le strade che il trigger non
--   percorre (trigger spenti, COPY). Senza questa asserzione, toglierlo
--   passerebbe inosservato: a fermare l'INSERT basterebbe il guard.
SELECT is(
    (SELECT pg_get_constraintdef(c.oid) FROM pg_constraint c
      WHERE c.conrelid = 'vendite.contratti_righe'::regclass
        AND c.conname = 'chk_contrighe_erogazione_per_tipo_eccezione'),
    'CHECK (((tipo_eccezione = ''ESCLUSIONE''::vendite.tipo_eccezione_contratto) OR (tipo_erogazione IS NOT NULL)))',
    '1) CHECK sul contratto: ogni tipo che non e'' ESCLUSIONE vuole l''erogazione');

SELECT is(
    (SELECT pg_get_constraintdef(c.oid) FROM pg_constraint c
      WHERE c.conrelid = 'vendite.offerte_commerciali_eccezioni'::regclass
        AND c.conname = 'chk_offerte_eccezioni_erogazione_per_tipo_eccezione'),
    'CHECK (((tipo_eccezione = ''ESCLUSIONE''::vendite.tipo_eccezione_contratto) OR (tipo_erogazione IS NOT NULL)))',
    '2) CHECK sull''offerta: lo stesso');

-- Per funzione, argomento e nome: i trigger sono scritti a mano (20261004-32).
-- tgtype: 1 = ROW, 2 = BEFORE, 4 = INSERT, 16 = UPDATE.
SELECT ok(
    (SELECT count(*) = 1
            AND bool_and(t.tgtype = (1 | 2 | 4 | 16))
            AND bool_and(pg_get_triggerdef(t.oid) LIKE '%BEFORE INSERT OR UPDATE OF tipo_erogazione, tipo_eccezione%')
            AND bool_and(pg_get_triggerdef(t.oid) LIKE '%(''contratto_id'')')
       FROM pg_trigger t
      WHERE t.tgrelid = 'vendite.contratti_righe'::regclass
        AND NOT t.tgisinternal
        AND t.tgname = 'trg_contratti_righe_a10_guard_erogazione_obbligatoria_ins_upd'
        -- to_regprocedure: funzione assente = test rosso, non errore che ferma il file.
        AND t.tgfoid = to_regprocedure('script.trgfn_righe_guard_erogazione_obbligatoria()')),
    '3) guard montato sul contratto: _a10_, BEFORE INSERT OR UPDATE OF, per riga');

SELECT ok(
    (SELECT count(*) = 1
            AND bool_and(t.tgtype = (1 | 2 | 4 | 16))
            AND bool_and(pg_get_triggerdef(t.oid) LIKE '%BEFORE INSERT OR UPDATE OF tipo_erogazione, tipo_eccezione%')
            AND bool_and(pg_get_triggerdef(t.oid) LIKE '%(''offerta_id'')')
       FROM pg_trigger t
      WHERE t.tgrelid = 'vendite.offerte_commerciali_eccezioni'::regclass
        AND NOT t.tgisinternal
        AND t.tgname = 'trg_offerte_eccezioni_a10_guard_erogazione_obbligatoria_ins_upd'
        AND t.tgfoid = to_regprocedure('script.trgfn_righe_guard_erogazione_obbligatoria()')),
    '4) guard montato sull''offerta: lo stesso');

-- ============================================================
-- 5..11 — contratto
-- ============================================================
-- ⚠️ Sul TESTO del messaggio a catalogo, non su «un errore qualsiasi»: il 23514
--    del CHECK (o un altro guard) non deve passare per questo.
SELECT lives_ok(
    pg_temp.ins_riga('contratto', 'A', 'OVERRIDE', NULL),
    '5) contratto: OVERRIDE senza erogazione accettato: la eredita dall''articolo');

SELECT lives_ok(
    pg_temp.ins_riga('contratto', 'E', 'AGGIUNTA', NULL),
    '6) contratto: AGGIUNTA senza erogazione accettata: la eredita dall''articolo');

SELECT lives_ok(
    pg_temp.ins_riga('contratto', 'C', 'ESCLUSIONE', NULL),
    '7) contratto: ESCLUSIONE senza erogazione accettata (non si fattura)');

SELECT is(
    (SELECT r.tipo_erogazione::text || '/' || r.fonte_quantita_attesa::text
       FROM vendite.contratti_righe r
      WHERE r.contratto_id = (SELECT id FROM tmp_ero_contratto) AND r.articolo_id = pg_temp.art('A')),
    (SELECT e.tipo_erogazione::text || '/' || e.fonte_quantita_attesa::text
       FROM vendite.fn_articolo_erogazioni(pg_temp.art('A')) e WHERE e.e_default),
    '8) contratto: l''OVERRIDE ha ereditato erogazione e fonte di default dell''articolo');

SELECT throws_like(
    format($$UPDATE vendite.contratti_righe SET tipo_erogazione = NULL
              WHERE contratto_id = %s AND articolo_id = %L$$,
           (SELECT id FROM tmp_ero_contratto), pg_temp.art('A')),
    '%Manca il tipo di erogazione%',
    '9) contratto: togliere l''erogazione a un OVERRIDE e'' rifiutato');

CREATE TEMP TABLE tmp_ero_canali_c AS
SELECT pg_temp.canali(format(
    $$UPDATE vendite.contratti_righe SET tipo_erogazione = NULL
       WHERE contratto_id = %s AND articolo_id = %L$$,
    (SELECT id FROM tmp_ero_contratto), pg_temp.art('E'))) AS canali;

SELECT is(
    split_part((SELECT canali FROM tmp_ero_canali_c), ' / ', 1),
    'E_RIGA_EROGAZIONE_OBBLIGATORIA',
    '10) contratto: canale CONSTRAINT = il codice di dominio, non il nome del CHECK');

SELECT is(
    split_part((SELECT canali FROM tmp_ero_canali_c), ' / ', 2),
    'tipo_erogazione',
    '11) contratto: canale COLUMN = il campo da accendere');

-- ============================================================
-- 12..18 — offerta
-- ============================================================
SELECT lives_ok(
    pg_temp.ins_riga('offerta', 'A', 'OVERRIDE', NULL),
    '12) offerta: OVERRIDE senza erogazione accettato: la eredita dall''articolo');

SELECT lives_ok(
    pg_temp.ins_riga('offerta', 'E', 'AGGIUNTA', NULL),
    '13) offerta: AGGIUNTA senza erogazione accettata: la eredita dall''articolo');

SELECT lives_ok(
    pg_temp.ins_riga('offerta', 'C', 'ESCLUSIONE', NULL),
    '14) offerta: ESCLUSIONE senza erogazione accettata');

SELECT is(
    (SELECT r.tipo_erogazione::text || '/' || r.fonte_quantita_attesa::text
       FROM vendite.offerte_commerciali_eccezioni r
      WHERE r.offerta_id = (SELECT id FROM tmp_ero_offerta) AND r.articolo_id = pg_temp.art('E')),
    (SELECT e.tipo_erogazione::text || '/' || e.fonte_quantita_attesa::text
       FROM vendite.fn_articolo_erogazioni(pg_temp.art('E')) e WHERE e.e_default),
    '15) offerta: l''AGGIUNTA ha ereditato erogazione e fonte di default dell''articolo');

SELECT throws_like(
    format($$UPDATE vendite.offerte_commerciali_eccezioni SET tipo_erogazione = NULL
              WHERE offerta_id = %s AND articolo_id = %L$$,
           (SELECT id FROM tmp_ero_offerta), pg_temp.art('E')),
    '%Manca il tipo di erogazione%',
    '16) offerta: togliere l''erogazione a un''AGGIUNTA e'' rifiutato');

CREATE TEMP TABLE tmp_ero_canali_o AS
SELECT pg_temp.canali(format(
    $$UPDATE vendite.offerte_commerciali_eccezioni SET tipo_erogazione = NULL
       WHERE offerta_id = %s AND articolo_id = %L$$,
    (SELECT id FROM tmp_ero_offerta), pg_temp.art('A'))) AS canali;

SELECT is(
    split_part((SELECT canali FROM tmp_ero_canali_o), ' / ', 1),
    'E_RIGA_EROGAZIONE_OBBLIGATORIA',
    '17) offerta: canale CONSTRAINT = il codice di dominio');

SELECT is(
    split_part((SELECT canali FROM tmp_ero_canali_o), ' / ', 2),
    'tipo_erogazione',
    '18) offerta: canale COLUMN = il campo da accendere');

-- ============================================================
-- 19..21 — R4: il lister del push
-- ============================================================
-- Sul contratto restano A (OVERRIDE, test 8) e C (ESCLUSIONE, test 7). Si
-- attiva — la strada di un contratto vero: righe in bozza, poi ATTIVO — e si
-- chiede il push del solo contratto della fixture.
-- ⭐ L'erogazione di A e' quella EREDITATA dalla tipologia del listino (rev
--   2026-10-07), CONSUMO.
-- 🔴 rev 2026-10-13 (20261013-24, D-2 di Tid): il push del contratto manda
--   solo le righe UNA_TANTUM; CANONE, ORARIO e CONSUMO aspettano la loro
--   generazione (brief-db-contratto-righe-periodiche-in-commessa). Il 19 voleva
--   A in lista e il 21 la sua erogazione in meta: ora A non si lista. La
--   proiezione in meta.tipo_erogazione la tengono vendite/test-push-contratto-
--   dalla-madre-v1 (3) e vendite/test-fn-list-contratti-da-pushare-v1 (3, 5).
UPDATE vendite.contratti
   SET stato_doc_contratto_id = (SELECT id FROM config.stati_doc_contratti WHERE codice_interno = 'ATTIVO')
 WHERE id = (SELECT id FROM tmp_ero_contratto);

CREATE TEMP TABLE tmp_ero_push AS
SELECT * FROM vendite.fn_list_contratti_da_pushare(
    NULL, NULL, NULL, (SELECT id FROM tmp_ero_contratto));

SELECT is(
    (SELECT count(*)::int FROM tmp_ero_push WHERE articolo_id = pg_temp.art('A')),
    0,
    '19) D-2: l''OVERRIDE con erogazione ereditata CONSUMO non si lista (solo UNA_TANTUM)');

SELECT is(
    (SELECT count(*)::int FROM tmp_ero_push WHERE articolo_id = pg_temp.art('C')),
    0,
    '20) R4: l''ESCLUSIONE non si lista: non si fattura');

SELECT ok(
    (SELECT r.tipo_erogazione IS NOT NULL AND r.tipo_erogazione::text <> 'UNA_TANTUM'
       FROM vendite.contratti_righe r
      WHERE r.contratto_id = (SELECT id FROM tmp_ero_contratto) AND r.articolo_id = pg_temp.art('A')),
    '21) l''erogazione dell''OVERRIDE e'' quella ereditata, e non e'' UNA_TANTUM: il 19 esclude per erogazione');

SELECT * FROM finish();
ROLLBACK;
