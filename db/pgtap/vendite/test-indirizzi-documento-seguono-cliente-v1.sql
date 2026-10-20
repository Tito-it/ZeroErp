-- ------------------------------------------------------------
-- SPDX-License-Identifier: GPL-3.0-or-later
-- rev 2026-10-20 (brief-db-grammatica-unica-documenti §13, 2d): test 1 con gli ambiti col codice della sorgente.
-- pgTAP test per Zero ERP
-- ⚠️ rev 2026-10-19 (brief-db-grammatica-unica-documenti, lotto 2a, 20261019-40 … -79):
--   il documento passato ai lettori delle testate, ai legami e ai montaggi del
--   lock e' il codice della sorgente (DDT_VENDITA, ORDINE_VENDITA,
--   OFFERTA_COMMERCIALE, RESO_VENDITA). Restano corti i prefissi delle chiavi
--   (G-8), l'origine dei legami (V7) e l'ambito degli indirizzi (G-6).
--
-- Test: gli indirizzi del documento seguono il cliente. Un indirizzo preso
--   dall'anagrafica e' del cliente del documento; se il cliente cambia in
--   bozza quelli di prima se ne vanno, e lo slot di default si riempie dal
--   cliente nuovo; un indirizzo d'altri non si scrive e non si emette.
--   Brief: docs/it/dev/work-in-progress/brief-db-indirizzi-documento-seguono-il-cliente.md
--   ChangeSet 20261011-43 ... -61.
--
-- ⭐ I soggetti li FABBRICA (dbops.fn_pgtap_crea_emittente_operatore,
--   fn_pgtap_crea_cliente_ba): due clienti, A e B, dello stesso emittente.
--   Ognuno nasce col suo indirizzo di Fatturazione di ruolo, generico (il
--   ruolo cliente lo vuole): e' la fonte del ripiego dello slot CON (il ruolo
--   cliente non ammette indirizzi di Consegna di ruolo).
-- ⚠️ Il caso «riga d'altri gia' scritta» non si costruisce spegnendo il guard
--   (il test gira come app): si sposta in anagrafica l'indirizzo su un'altra
--   fornitura, che e' il terzo modo in cui la riga diventa d'altri (§7.2 c del
--   brief: l'istanza dell'indirizzo d'anagrafica si legge viva).
-- ⚠️ rev 2026-10-19 (R-BE-15, brief-db-processi-accensione-per-ambiente
--   §6.17.1, 20261019-82): l'«altra fornitura» e' una SECONDA fornitura di A,
--   non quella di B. Un indirizzo del ruolo di A sull'istanza di B ora lo
--   rifiuta il guard della tabella (E_ISTANZA_ALTRO_SOGGETTO): il test lo
--   costruiva, ed era proprio il difetto. Il predicato risponde ALTRA_FORNITURA
--   come prima, e la check ha lo stesso motivo.
-- ⚠️ Gli slot di default (test 1) li semina il CSV del mirror 20260711-18:
--   prima dell'apply non ci sono.
--
-- Indice test (1..18):
--   STRUTTURA
--    1) slot di default: CON su cinque ambiti, ripiego FATT; FATTURE e ACQUISTI_DDT senza
--    2) il guard d'origine sulle sei *_indirizzi, il cambio di cliente sulle quattro testate
--    3) i sei gate chiamano la check, i due creatori il building block (sulla forma)
--   IL PREDICATO
--    4) una-tantum, del cliente, altro cliente, altra fornitura, documento senza fornitura
--   DDT
--    5) il building block riempie lo slot CON dal ripiego FATT del cliente
--    6) a slot pieno non scrive niente
--    7) il guard rifiuta una riga d'anagrafica di un altro cliente (E_INDIRIZZO_DOC_NON_DEL_CLIENTE)
--    8) un una-tantum si scrive
--    9) il cliente cambia in bozza: la CON di A se ne va, c'e' quella di B
--   10) un una-tantum resta col cliente che cambia, e il default non lo tocca
--   PREVENTIVO (l'istanza)
--   11) l'indirizzo legato alla fornitura del preventivo vince sul generico
--   12) un indirizzo della fornitura di B, sul preventivo di A: rifiutato
--   13) spostato in anagrafica su un'altra fornitura: la check del preventivo ha il motivo
--   14) e fn_check_preventivo_emettibile lo porta, dopo i prezzi
--   EMISSIONE DDT (D-3)
--   15) la check della bolla ha il motivo 4-bis
--   16) la bolla non si emette: E_INDIRIZZO_DOC_NON_DEL_CLIENTE
--   17) rimesso un indirizzo del cliente, la bolla si emette
--   REVISIONE DELL'OFFERTA (D-4)
--   18) la rev.N+1 porta gli indirizzi della rev.N, slot per slot, origini comprese
-- ------------------------------------------------------------
BEGIN;

SET CONSTRAINTS ALL IMMEDIATE;

SELECT plan(18);

-- ============================================================
-- FIXTURE
-- ============================================================
CREATE TEMP TABLE _m AS
SELECT * FROM dbops.fn_pgtap_crea_emittente_operatore();

DO $ctx$ BEGIN PERFORM script.fn_pgtap_set_contesto_operatore((SELECT auth_user_id FROM _m)); END $ctx$;

CREATE TEMP TABLE _c AS
SELECT 'A' AS lato, c.* FROM dbops.fn_pgtap_crea_cliente_ba('indirizzi A') c
UNION ALL
SELECT 'B' AS lato, c.* FROM dbops.fn_pgtap_crea_cliente_ba('indirizzi B') c;

SET CONSTRAINTS ALL IMMEDIATE;

CREATE TEMP TABLE _k AS
SELECT (SELECT id FROM config.stati_doc_ddt WHERE codice_interno = 'DRAFT')         AS ddt_draft,
       (SELECT id FROM config.stati_doc_ddt WHERE codice_interno = 'EMESSO')        AS ddt_emesso,
       (SELECT id FROM config.stati_doc_preventivi WHERE codice_interno = 'DRAFT')  AS prev_draft,
       (SELECT id FROM config.causali_trasporto WHERE codice = 'CONTO_VISIONE')     AS cv,
       (SELECT id FROM config.tipi_indirizzi WHERE codice_interno = 'CON')          AS ind_con,
       (SELECT id FROM config.tipi_indirizzi WHERE codice_interno = 'FATT')         AS ind_fatt,
-- 🔴 rev 2026-10-13 (brief-db-articoli-ammessi-per-documento D-1/D-2): l'articolo si
--   COSTRUISCE. Prima si pescava dal catalogo (il primo per id, o il piu' recente):
--   il primo per id e' l'onere del seed ONERE_SENZA_CONTRATTO (natura servizio), e
--   da 20261013-42 ordine e bolla portano solo merce. Un articolo costruito ha solo
--   le proprieta' che il test gli da' (merce, non gestito a magazzino).
       dbops.fn_pgtap_crea_articolo('PGT-IDSC-ART', false)                 AS articolo,
       (SELECT v.id FROM config.valute v ORDER BY v.id LIMIT 1)                     AS valuta,
       (SELECT emittente_fiscale_id FROM _m)                                        AS ef;

-- L'indirizzo di Fatturazione di ruolo, generico, di ciascun cliente.
CREATE TEMP TABLE _fatt AS
SELECT c.lato, i.id AS indirizzo_id
  FROM _c c
  JOIN anagrafiche.indirizzi i
    ON i.soggetto_ruolo_id = c.soggetto_ruolo_id
   AND i.tipo_indirizzo_id = (SELECT ind_fatt FROM _k)
   AND i.istanza_utility_id IS NULL;

-- Una bolla CONTO_VISIONE in bozza col BA del cliente e una riga, SENZA
-- indirizzi: lo slot e' il caso del test.
CREATE FUNCTION pg_temp.ddt(p_lato text)
RETURNS bigint LANGUAGE plpgsql AS $f$
DECLARE v_id bigint;
BEGIN
    INSERT INTO vendite.ddt
        (destinatario_soggetto_ruolo_id, billing_account_id, stato_doc_ddt_id,
         emittente_fiscale_id, causale_trasporto_id)
    SELECT c.soggetto_ruolo_id, c.billing_account_id, k.ddt_draft, k.ef, k.cv
      FROM _c c CROSS JOIN _k k WHERE c.lato = p_lato
    RETURNING id INTO v_id;
    INSERT INTO vendite.ddt_righe
        (ddt_id, riga_nr, articolo_id, descrizione, quantita, qta_operativa)
    SELECT v_id, 1, k.articolo, 'Riga pgTAP indirizzi', 1, 1 FROM _k k;
    RETURN v_id;
END $f$;

CREATE TEMP TABLE _d AS
SELECT pg_temp.ddt('A') AS ddt_a,
       pg_temp.ddt('A') AS ddt_ut,
       pg_temp.ddt('A') AS ddt_em;

-- Un preventivo in bozza del cliente A (la coppia BA/istanza del BA).
CREATE TEMP TABLE _p AS
WITH p AS (
    INSERT INTO vendite.preventivi (
        billing_account_id, istanza_utility_id, utility_id,
        validita_dal, validita_al, valuta_id, stato_doc_preventivo_id, emittente_fiscale_id)
    SELECT c.billing_account_id, c.istanza_utility_id, c.utility_id,
           script.fn_data_operativa(), script.fn_data_operativa() + 30,
           k.valuta, k.prev_draft, k.ef
      FROM _c c CROSS JOIN _k k WHERE c.lato = 'A'
    RETURNING id)
SELECT id AS prev_a FROM p;

-- ============================================================
-- STRUTTURA
-- ============================================================
SELECT is(
    (SELECT string_agg(a.ambito || ':' || t.codice_interno || '>' || r.codice_interno, ', ' ORDER BY a.ambito)
       FROM config.tipi_indirizzi_allowed a
       JOIN config.tipi_indirizzi t ON t.id = a.tipo_indirizzo_id
       LEFT JOIN config.tipi_indirizzi r ON r.id = a.ripiego_tipo_indirizzo_id
      WHERE a.slot_default),
    -- rev 2026-10-20 (2d, G-6): gli ambiti sono i codici delle sorgenti
    'CONTRATTO:CON>FATT, DDT_VENDITA:CON>FATT, OFFERTA_COMMERCIALE:CON>FATT, ORDINE_VENDITA:CON>FATT, PREVENTIVO:CON>FATT',
    '1) slot di default CON, ripiego FATT, su cinque ambiti; fattura e DDT d''acquisto senza');

SELECT is(
    (SELECT string_agg(c.relname || '.' || t.tgname, ', ' ORDER BY c.relname)
       FROM pg_trigger t
       JOIN pg_class c ON c.oid = t.tgrelid
       JOIN pg_namespace n ON n.oid = c.relnamespace AND n.nspname = 'vendite'
      WHERE t.tgname LIKE '%\_a10\_guard\_origine\_ins\_upd'
         OR t.tgname LIKE '%\_m50\_indirizzi\_seguono\_cliente\_upd'),
    'contratti.trg_contratti_m50_indirizzi_seguono_cliente_upd, '
    'contratti_indirizzi.trg_contratti_indirizzi_a10_guard_origine_ins_upd, '
    'ddt.trg_ddt_m50_indirizzi_seguono_cliente_upd, '
    'ddt_indirizzi.trg_ddt_indirizzi_a10_guard_origine_ins_upd, '
    'fatture_indirizzi.trg_fatture_indirizzi_a10_guard_origine_ins_upd, '
    'offerte_commerciali.trg_offerte_commerciali_m50_indirizzi_seguono_cliente_upd, '
    'offerte_commerciali_indirizzi.trg_offerte_commerciali_indirizzi_a10_guard_origine_ins_upd, '
    'ordini_indirizzi.trg_ordini_indirizzi_a10_guard_origine_ins_upd, '
    'preventivi.trg_preventivi_m50_indirizzi_seguono_cliente_upd, '
    'preventivi_indirizzi.trg_preventivi_indirizzi_a10_guard_origine_ins_upd',
    '2) guard d''origine sulle sei *_indirizzi, cambio di cliente sulle quattro testate (non l''ordine)');

-- ⚠️ Sulla FORMA, dichiarato: offerta e contratto non hanno qui una fixture
--   che arrivi all'emissione. Si asserisce che i lettori CHIAMANO la check
--   (commenti tolti, nome seguito da «(»), non che la riscrivono.
SELECT is(
    (SELECT string_agg(n.nspname || '.' || p.proname, ', ' ORDER BY n.nspname, p.proname)
       FROM pg_proc p JOIN pg_namespace n ON n.oid = p.pronamespace
      WHERE regexp_replace(p.prosrc, '--[^\n]*', '', 'g')
                ~ '(fn_check_indirizzi_documento_cliente|fn_doc_indirizzo_default)\s*\('
        AND p.proname NOT IN ('fn_check_indirizzi_documento_cliente', 'fn_doc_indirizzo_default')),
    'script.fn_available_actions_contratto, script.fn_available_actions_offerta, '
    'script.fn_check_ddt_emittibile, script.fn_check_preventivo_emettibile, '
    'vendite.fn_create_contratto, vendite.trgfn_contratti_guard_transizione_stato, '
    'vendite.trgfn_doc_indirizzi_seguono_cliente, vendite.trgfn_offerte_commerciali_guard_transizione',
    '3) i gate leggono la check, fn_create_contratto e il cambio di cliente il building block');

-- ============================================================
-- IL PREDICATO
-- ============================================================
SELECT is(
    ARRAY[
      script.fn_indirizzo_documento_fuori_cliente(NULL, NULL,
          (SELECT soggetto_ruolo_id FROM _c WHERE lato = 'A'), NULL),
      script.fn_indirizzo_documento_fuori_cliente((SELECT indirizzo_id FROM _fatt WHERE lato = 'A'), NULL,
          (SELECT soggetto_ruolo_id FROM _c WHERE lato = 'A'), (SELECT istanza_utility_id FROM _c WHERE lato = 'A')),
      script.fn_indirizzo_documento_fuori_cliente(NULL, (SELECT soggetto_ruolo_id FROM _c WHERE lato = 'B'),
          (SELECT soggetto_ruolo_id FROM _c WHERE lato = 'A'), NULL),
      script.fn_indirizzo_documento_fuori_cliente((SELECT indirizzo_id FROM _fatt WHERE lato = 'B'),
          (SELECT soggetto_ruolo_id FROM _c WHERE lato = 'A'),
          (SELECT soggetto_ruolo_id FROM _c WHERE lato = 'A'), NULL),
      script.fn_indirizzo_documento_fuori_cliente(NULL, NULL, NULL, NULL)],
    ARRAY[NULL, NULL, 'ALTRO_CLIENTE', 'ALTRO_CLIENTE', NULL]::text[],
    '4) una-tantum e del cliente: NULL; ruolo d''altri, o indirizzo d''altri sotto il ruolo giusto: ALTRO_CLIENTE');

-- ============================================================
-- DDT
-- ============================================================
-- ⚠️ Il building block si chiama in un'istruzione a se': in un'espressione
--   sola l'ordine di valutazione delle due sottoquery non e' garantito, e la
--   riga si leggerebbe prima che venga scritta.
CREATE TEMP TABLE _r5 AS
SELECT vendite.fn_doc_indirizzo_default('DDT_VENDITA', (SELECT ddt_a FROM _d)) AS scritto;

SELECT is(
    (SELECT scritto::text FROM _r5)
      || ' ' || (SELECT (di.tipo_indirizzo_id = k.ind_con
                         AND di.origine_indirizzo_id = (SELECT indirizzo_id FROM _fatt WHERE lato = 'A')
                         AND di.origine_soggetto_ruolo_id = (SELECT soggetto_ruolo_id FROM _c WHERE lato = 'A'))::text
                   FROM vendite.ddt_indirizzi di CROSS JOIN _k k
                  WHERE di.ddt_id = (SELECT ddt_a FROM _d)),
    'true true',
    '5) il building block riempie la CON dal ripiego: la Fatturazione di ruolo di A');

SELECT is(
    vendite.fn_doc_indirizzo_default('DDT_VENDITA', (SELECT ddt_a FROM _d)),
    false,
    '6) a slot pieno non scrive niente');

SELECT throws_like(
    format('UPDATE vendite.ddt_indirizzi SET origine_indirizzo_id = %s, origine_soggetto_ruolo_id = %s WHERE ddt_id = %s',
           (SELECT indirizzo_id FROM _fatt WHERE lato = 'B'),
           (SELECT soggetto_ruolo_id FROM _c WHERE lato = 'B'),
           (SELECT ddt_a FROM _d)),
    '%non e'' del cliente del documento%',
    '7) un indirizzo d''anagrafica di B sulla bolla di A: E_INDIRIZZO_DOC_NON_DEL_CLIENTE');

SELECT lives_ok(
    format($q$INSERT INTO vendite.ddt_indirizzi (ddt_id, tipo_indirizzo_id, snapshot)
              VALUES (%s, %s, '{"via": "Via dei Terzi 1", "citta": "Roma"}')$q$,
           (SELECT ddt_ut FROM _d), (SELECT ind_con FROM _k)),
    '8) un una-tantum si scrive sempre');

UPDATE vendite.ddt
   SET billing_account_id = (SELECT billing_account_id FROM _c WHERE lato = 'B')
 WHERE id IN ((SELECT ddt_a FROM _d), (SELECT ddt_ut FROM _d));

SELECT is(
    (SELECT string_agg((di.origine_soggetto_ruolo_id = (SELECT soggetto_ruolo_id FROM _c WHERE lato = 'B'))::text
                       || '/' || (di.origine_indirizzo_id = (SELECT indirizzo_id FROM _fatt WHERE lato = 'B'))::text, ',')
       FROM vendite.ddt_indirizzi di WHERE di.ddt_id = (SELECT ddt_a FROM _d)),
    'true/true',
    '9) il cliente diventa B in bozza: la CON di A se ne va, c''e'' quella di B');

SELECT is(
    (SELECT count(*)::text || ' ' || bool_and(di.origine_indirizzo_id IS NULL AND di.origine_soggetto_ruolo_id IS NULL
                                              AND di.snapshot ->> 'via' = 'Via dei Terzi 1')::text
       FROM vendite.ddt_indirizzi di WHERE di.ddt_id = (SELECT ddt_ut FROM _d)),
    '1 true',
    '10) l''una-tantum resta col cliente che cambia, e il default non la sostituisce');

-- ============================================================
-- PREVENTIVO — l'istanza
-- ============================================================
-- A riceve una Fatturazione legata alla fornitura del suo BA.
CREATE TEMP TABLE _ist AS
WITH i AS (
    INSERT INTO anagrafiche.indirizzi (
        soggetto_ruolo_id, tipo_indirizzo_id, istanza_utility_id,
        indirizzo_libero, stato_id, comune_id, codice_postale_id, locality, postal_code)
    -- rev 2026-10-18: i campi della forma dallo stato (Italia: comune e CAP del catalogo)
    SELECT c.soggetto_ruolo_id, k.ind_fatt, c.istanza_utility_id,
           'Via pgTAP fornitura A', st.id,
           f.comune_id, f.codice_postale_id, f.locality, f.postal_code
      FROM _c c CROSS JOIN _k k
     CROSS JOIN (SELECT id FROM config.stati ORDER BY id LIMIT 1) st
     CROSS JOIN LATERAL dbops.fn_pgtap_indirizzo_libero_forma(st.id) f
     WHERE c.lato = 'A'
    RETURNING id)
SELECT id AS fatt_ist_a FROM i;

-- Una seconda fornitura di A (la sua istanza nasce col billing account, dalla
-- madre): l'«altra fornitura» dei test 13-16. Istanza e BA nascono nella
-- stessa istruzione: il guard differito dell'istanza vuole la finestra dei
-- differiti, che IMMEDIATE richiude (e fa da commit dei controlli).
SET CONSTRAINTS ALL DEFERRED;
CREATE TEMP TABLE _ist2 AS
SELECT b.istanza_utility_id AS ist_a2
  FROM _c c
 CROSS JOIN LATERAL anagrafiche.fn_crea_billing_account(
           c.soggetto_ruolo_id, c.utility_id,
           jsonb_build_object('categoria_cliente_id',
                              (SELECT cc.id FROM anagrafiche.categorie_clienti cc
                                WHERE cc.codice_interno = 'STANDARD'))) b
 WHERE c.lato = 'A';
SET CONSTRAINTS ALL IMMEDIATE;

CREATE TEMP TABLE _r11 AS
SELECT vendite.fn_doc_indirizzo_default('PREVENTIVO', (SELECT prev_a FROM _p)) AS scritto;

SELECT is(
    (SELECT scritto::text FROM _r11)
      || ' ' || (SELECT (pi.origine_indirizzo_id = (SELECT fatt_ist_a FROM _ist))::text
                   FROM vendite.preventivi_indirizzi pi
                  WHERE pi.preventivo_id = (SELECT prev_a FROM _p)),
    'true true',
    '11) sul preventivo l''indirizzo della sua fornitura vince sul generico');

SELECT throws_like(
    format($q$INSERT INTO vendite.preventivi_indirizzi
                  (preventivo_id, tipo_indirizzo_id, snapshot, origine_indirizzo_id, origine_soggetto_ruolo_id)
              VALUES (%s, %s, '{"via": "x"}', %s, %s)$q$,
           (SELECT prev_a FROM _p), (SELECT ind_fatt FROM _k),
           (SELECT indirizzo_id FROM _fatt WHERE lato = 'B'),
           (SELECT soggetto_ruolo_id FROM _c WHERE lato = 'B')),
    '%non e'' del cliente del documento%',
    '12) la Fatturazione di B sul preventivo di A: rifiutata');

-- In anagrafica l'indirizzo passa all'altra fornitura di A: la riga del
-- preventivo non e' piu' della sua fornitura, e lo vede solo l'emissione.
UPDATE anagrafiche.indirizzi
   SET istanza_utility_id = (SELECT ist_a2 FROM _ist2)
 WHERE id = (SELECT fatt_ist_a FROM _ist);

SELECT is(
    (SELECT m ->> 'reason' || ' ' || (m -> 'dettaglio' -> 'tipi')::text
       FROM jsonb_array_elements(script.fn_check_indirizzi_documento_cliente('PREVENTIVO', (SELECT prev_a FROM _p))) m),
    'INDIRIZZO_NON_DEL_CLIENTE ["CON"]',
    '13) spostato su un''altra fornitura: la check ha il motivo, sul tipo dello slot');

SELECT ok(
    script.fn_check_preventivo_emettibile((SELECT prev_a FROM _p))
      @> '[{"codice": "E_INDIRIZZO_DOC_NON_DEL_CLIENTE"}]',
    '14) fn_check_preventivo_emettibile porta il motivo (il guard e la capability lo leggono da li'')');

-- ============================================================
-- EMISSIONE DDT (D-3)
-- ============================================================
-- La Fatturazione della fornitura torna ad A; la bolla di A la prende come CON
-- dal default (precedenza all'istanza del suo BA); poi in anagrafica
-- quell'indirizzo passa di nuovo all'altra fornitura di A.
UPDATE anagrafiche.indirizzi
   SET istanza_utility_id = (SELECT istanza_utility_id FROM _c WHERE lato = 'A')
 WHERE id = (SELECT fatt_ist_a FROM _ist);

SELECT vendite.fn_doc_indirizzo_default('DDT_VENDITA', (SELECT ddt_em FROM _d));

UPDATE anagrafiche.indirizzi
   SET istanza_utility_id = (SELECT ist_a2 FROM _ist2)
 WHERE id = (SELECT fatt_ist_a FROM _ist);

SELECT ok(
    (SELECT script.fn_check_ddt_emittibile(d) @> '[{"codice": "E_INDIRIZZO_DOC_NON_DEL_CLIENTE"}]'
       FROM vendite.ddt d WHERE d.id = (SELECT ddt_em FROM _d)),
    '15) la check della bolla ha il motivo 4-bis');

SELECT throws_like(
    format('UPDATE vendite.ddt SET stato_doc_ddt_id = %s WHERE id = %s',
           (SELECT ddt_emesso FROM _k), (SELECT ddt_em FROM _d)),
    '%non e'' del cliente del documento%',
    '16) la bolla non si emette: E_INDIRIZZO_DOC_NON_DEL_CLIENTE dal guard degli indirizzi');

-- Rimesso un indirizzo del cliente (una-tantum, scritto a mano).
UPDATE vendite.ddt_indirizzi
   SET origine_indirizzo_id = NULL, origine_soggetto_ruolo_id = NULL
 WHERE ddt_id = (SELECT ddt_em FROM _d);

SELECT lives_ok(
    format('UPDATE vendite.ddt SET stato_doc_ddt_id = %s WHERE id = %s',
           (SELECT ddt_emesso FROM _k), (SELECT ddt_em FROM _d)),
    '17) con un indirizzo del cliente la bolla si emette');

-- ============================================================
-- REVISIONE DELL'OFFERTA (D-4)
-- ============================================================
-- Un'offerta del cliente A sul listino della sua utility, con due slot: la
-- CON dal default (la Fatturazione della fornitura di A, rimessa su A) e una
-- Residenza una-tantum. Emessa e revisionata (UPDATE diretto: la transizione
-- non e' in esame).
UPDATE anagrafiche.indirizzi
   SET istanza_utility_id = (SELECT istanza_utility_id FROM _c WHERE lato = 'A')
 WHERE id = (SELECT fatt_ist_a FROM _ist);

CREATE TEMP TABLE _l AS
SELECT * FROM dbops.fn_pgtap_crea_listino((SELECT utility_id FROM _c WHERE lato = 'A'), 'indirizzi rev');

CREATE TEMP TABLE _o AS
WITH o AS (
    INSERT INTO vendite.offerte_commerciali
           (emittente_fiscale_id, billing_account_id, istanza_utility_id, utility_id,
            listino_id, validita_dal, validita_al, stato_doc_offerta_id)
    SELECT k.ef, c.billing_account_id, c.istanza_utility_id, c.utility_id,
           l.listino_id, script.fn_data_operativa(), script.fn_data_operativa() + 365,
           (SELECT s.id FROM config.stati_doc_offerte s WHERE s.codice_interno = 'BOZZA')
      FROM _c c CROSS JOIN _k k CROSS JOIN _l l WHERE c.lato = 'A'
    RETURNING id)
SELECT id AS rev1 FROM o;

SELECT vendite.fn_doc_indirizzo_default('OFFERTA_COMMERCIALE', (SELECT rev1 FROM _o));

INSERT INTO vendite.offerte_commerciali_indirizzi (offerta_id, tipo_indirizzo_id, snapshot)
SELECT o.rev1, t.id, '{"via": "Via della Residenza 2", "citta": "Roma"}'
  FROM _o o, config.tipi_indirizzi t WHERE t.codice_interno = 'RES';

UPDATE vendite.offerte_commerciali
   SET stato_doc_offerta_id = (SELECT s.id FROM config.stati_doc_offerte s WHERE s.codice_interno = 'EMESSA')
 WHERE id = (SELECT rev1 FROM _o);

ALTER TABLE _o ADD COLUMN rev2 bigint;
UPDATE _o SET rev2 = vendite.fn_crea_revisione_offerta(rev1, 'pgtap');

-- Scopo: gli indirizzi di un'offerta in una forma confrontabile.
CREATE FUNCTION pg_temp.indirizzi_offerta(p_id bigint)
RETURNS text LANGUAGE sql STABLE AS $f$
  SELECT string_agg(concat_ws('|', t.codice_interno, oi.snapshot::text,
                              coalesce(oi.origine_indirizzo_id::text, '-'),
                              coalesce(oi.origine_soggetto_ruolo_id::text, '-')), ' ; ' ORDER BY t.codice_interno)
    FROM vendite.offerte_commerciali_indirizzi oi
    JOIN config.tipi_indirizzi t ON t.id = oi.tipo_indirizzo_id
   WHERE oi.offerta_id = p_id;
$f$;

SELECT is(
    pg_temp.indirizzi_offerta((SELECT rev2 FROM _o)),
    pg_temp.indirizzi_offerta((SELECT rev1 FROM _o)),
    '18) la revisione dell''offerta porta gli indirizzi della rev.N: CON d''anagrafica e Residenza una-tantum');

SELECT * FROM finish();
ROLLBACK;
