-- ------------------------------------------------------------
-- SPDX-License-Identifier: AGPL-3.0-or-later
-- pgTAP test per Zero ERP
-- Test: vendite.vw_fatture_lista — la settima sorella delle viste canoniche
--       (changeSet 20260824-15)
--
-- ⭐ COSA PRESIDIA, in una riga: che la vista **non perda righe** e **non ne
--   aggiunga**. Sono i due modi in cui una vista di lista mente, e nessuno dei
--   due si vede a occhio: una fattura che sparisce non lascia traccia, e una
--   fattura duplicata sembra un dato sbagliato.
--
-- Elenco test (plan 11):
-- 1) la vista esiste ed e' `security_invoker=on`
--    ⛔ E' l'asserzione piu' importante del file. La reloption NON sta nel
--    corpo della vista: un `CREATE OR REPLACE VIEW` che non la ripete la
--    AZZERA in silenzio, e da quel momento la vista legge coi diritti del
--    proprietario — cioe' senza RLS, mostrando a ogni operatore le fatture di
--    tutti. Non c'e' errore, non c'e' avviso: cambia solo cosa si vede.
-- 2) i nomi canonici che il frontend conosce ci sono tutti
-- 3) nessun FAN-OUT: una riga di vista per ogni fattura visibile
-- 4) l'unico JOIN interno resta dimostrabile: `natura_doc_id` NOT NULL + FK
-- 5) e tutti gli altri join sono LEFT (nessun altro INNER nel corpo)
-- 6) fixture: una fattura SENZA stato, utility e valuta compare lo stesso
-- 7) e ci compare con cliente ed emittente fiscale risolti
-- 8) la vista non fa scope per conto suo: le righe sono esattamente quelle
--    che l'operatore vede su vendite.fatture
-- ⭐ rev 2026-09-17 (brief-db-distinta-ricerca-rate §4-bis.2, P-1 / Q-E):
-- 9) numero_documento c'e' ed e' NULL sulla bozza NON numerata — mai la
--    stringa vuota — mentre il registro (che la bozza ha: registro_id e' NOT
--    NULL) e' gia' risolto
-- 10) su una fattura NUMERATA (costruita) numero_documento e' «numero - serie»,
--     dalla sede unica fn_numero_documento_fattura, e il registro e' risolto
-- 11) le sorelle: registro_codice sta ESATTAMENTE su fatture, ddt, ordini, resi —
--     le quattro con registro_id — e su nessun'altra vw_*_lista
--
-- Scopo:
--  - la fattura era l'unico documento del ciclo attivo senza vista canonica;
--    questa vista e' il primo dei tre pezzi (vista, endpoint, rotta) che
--    aprono la strada diretta al documento fiscale.
--  - Brief: piano-migrazione-primevue-5.md §9
--
-- ⚠️ COSA QUESTO FILE **NON** MISURA, e va detto invece di lasciarlo credere:
--   il ramo in cui `anagrafiche.billing_account` e' INVISIBILE all'operatore
--   mentre la fattura NON lo e'. E' il caso per cui quel join e' LEFT — le due
--   tabelle risolvono il perimetro con funzioni diverse
--   (`fn_scope_ef_whitelist_via_efba` contro `fn_scope_ef_whitelist_via_sr`) —
--   ma per esercitarlo servirebbe un secondo perimetro emittente e una sessione
--   fuori scope, cioe' una fixture a due perimetri che e' un file a se'.
--   Il ramo resta presidiato dalla FORMA del codice (test 5) e da questa riga.
--
-- ⛔ LA FIXTURE SI COSTRUISCE, non si cerca (rev 2026-09-17 sera). Fino a quel
--   giorno il file pescava «un billing account con emittente» fra i dati
--   esistenti: su un database ricostruito dai changelog (zeroerp_ci, la CI) le
--   anagrafiche sono a ZERO, la fixture usciva vuota e i test 6-7 e 9-10
--   confrontavano NULL — ASSERZIONE in baseline-rossi-ci.tsv, con i test 3 e
--   8 verdi a vuoto (0 = 0). E la stessa fixture, ricopiata, ha fatto nascere
--   rosso test-vw-fatture-scadenze-lista-v1. Ora: un'azienda col suo operatore
--   (dbops.fn_pgtap_crea_emittente_operatore) PRIMA del contesto, e un cliente
--   fatturabile (dbops.fn_pgtap_crea_cliente_ba) NEL contesto — guida
--   pgtap-come-si-scrive-un-test §«Il mondo si costruisce, non si cerca».
-- ------------------------------------------------------------

BEGIN;

-- ⛔ L'AZIENDA SI COSTRUISCE, e il contesto e' quello del SUO operatore.
CREATE TEMP TABLE _mondo AS
SELECT m.* FROM dbops.fn_pgtap_crea_emittente_operatore() m;

DO $ctx$ BEGIN PERFORM script.fn_pgtap_set_contesto_operatore(
    (SELECT auth_user_id FROM _mondo)); END $ctx$;

SET CONSTRAINTS ALL IMMEDIATE;

SELECT plan(11);

-- ============================================================
-- 1) ⭐ security_invoker: la reloption che sparisce da sola
-- ============================================================
SELECT is(
  (SELECT coalesce((SELECT string_agg(x, ',' ORDER BY x) FROM unnest(c.reloptions) x), 'ASSENTE')
     FROM pg_class c
     JOIN pg_namespace n ON n.oid = c.relnamespace
    WHERE n.nspname = 'vendite' AND c.relname = 'vw_fatture_lista'),
  'security_invoker=on',
  '1) vendite.vw_fatture_lista e'' security_invoker=on: e'' la RLS di vendite.fatture a mordere'
);

-- ============================================================
-- 2) I NOMI CANONICI — il contratto con il frontend
--    ⚠️ Si asserisce l'insieme dei MANCANTI, non il numero delle colonne: cosi'
--    aggiungere una colonna nuova non fa rosso, toglierne una si'. Un test che
--    conta le colonne diventa un ostacolo alla prima aggiunta legittima, e
--    dopo due volte qualcuno lo allarga e smette di presidiare.
-- ============================================================
SELECT is(
  (SELECT coalesce(string_agg(x, ', ' ORDER BY x), '')
     FROM unnest(ARRAY['id','uid','numero','serie','anno','data',
                       'stato_codice_interno','stato_descrizione','fase',
                       -- ⛔ rev 2026-08-29: `natura_doc_codice` si chiama ora
                       -- `natura_doc_codice_interno` (20260829-02). Il valore viene da
                       -- config.nature_doc_fiscale.codice_interno, la colonna IMMUTABILE,
                       -- e linee-guida-sql §6c vieta `codice_interno AS *_codice`: il nome
                       -- mentiva sulla sorgente e il guardrail CI
                       -- scripts/sql/check_naming_stato_codice.sql era ROSSO su questa
                       -- vista. ⚠️ E' un cambio di CONTRATTO col frontend, voluto e
                       -- concordato: la rinomina a valle e' meccanica.
                       'natura_doc_codice_interno','natura_doc_descrizione',
                       'ragione_sociale_completa','id_fiscale_univoco_cf_piva',
                       'ba_codice','billing_account_id','soggetto_id',
                       'utility_id','utility_codice','utility_descrizione',
                       'emittente_fiscale_id','emittente_fiscale_codice',
                       'emittente_ragione_sociale','emittente_soggetto_ruolo_id',
                       'valuta_id','valuta_codice',
                       'imponibile_tot','imposta_tot','totale_doc','totale_a_pagare',
                       'data_insert','user_insert']) AS x
    WHERE NOT EXISTS (
      SELECT 1 FROM pg_attribute a
       WHERE a.attrelid = 'vendite.vw_fatture_lista'::regclass
         AND a.attnum > 0 AND NOT a.attisdropped AND a.attname = x)),
  '',
  '2) i nomi canonici che il frontend gia'' conosce ci sono tutti'
);

-- ============================================================
-- 3) ⭐ NESSUN FAN-OUT — il difetto che un join 1:N produrrebbe in silenzio.
--    `emittenti_fiscali.soggetto_ruolo_id` ha un vincolo di unicita' e per
--    questo il ponte verso l'emittente non moltiplica: qui si verifica
--    l'EFFETTO, non il vincolo, cosi' il test tiene anche se un domani il
--    ponte cambiasse strada.
-- ============================================================
SELECT is(
  (SELECT count(*) FROM vendite.vw_fatture_lista),
  (SELECT count(*) FROM vendite.fatture),
  '3) una riga di vista per ogni fattura: nessun join moltiplica le righe'
);

-- ============================================================
-- 4) L'UNICO JOIN INTERNO E' DIMOSTRABILE.
--    `config.nature_doc_fiscale` e' in INNER JOIN perche' `natura_doc_id` e'
--    NOT NULL e ha la sua foreign key. ⚠️ Se un domani quella colonna
--    diventasse nullable, l'inner join comincerebbe a far SPARIRE fatture
--    dalla lista — e non lo direbbe nessuno. Questo test e' li' per quello.
-- ============================================================
SELECT is(
  (SELECT (a.attnotnull)::text || '|' ||
          (EXISTS (SELECT 1 FROM pg_constraint k
                    WHERE k.conrelid = 'vendite.fatture'::regclass
                      AND k.contype = 'f'
                      AND a.attnum = ANY (k.conkey)))::text
     FROM pg_attribute a
    WHERE a.attrelid = 'vendite.fatture'::regclass
      AND a.attname = 'natura_doc_id'),
  'true|true',
  '4) natura_doc_id e'' NOT NULL e ha una FK: e'' cio'' che rende sicuro l''unico INNER JOIN'
);

-- ============================================================
-- 5) E TUTTO IL RESTO E' LEFT. Si legge la forma del corpo: un `JOIN` non
--    preceduto da `LEFT` che non sia quello delle nature e' un join che puo'
--    perdere righe. ⚠️ In particolare `anagrafiche.billing_account`, che ha
--    una RLS propria: li' un inner join toglierebbe dalla lista una fattura
--    che la policy delle fatture lascia passare.
-- ============================================================
SELECT is(
  (SELECT count(*)::int
     FROM regexp_matches(
            pg_get_viewdef('vendite.vw_fatture_lista'::regclass, true),
            '(?<!LEFT )(?<!LEFT OUTER )\mJOIN\M', 'g')),
  1,
  '5) un solo JOIN interno nel corpo della vista: tutti gli altri sono LEFT'
);

-- ============================================================
-- FIXTURE — una fattura con le decodifiche NULLE.
-- ⚠️ Le colonne stato/tipo/utility/valuta sono NULLABLE nello schema: oggi sui
--    dati di sviluppo sono tutte valorizzate, ma la domanda e' «puo'
--    succedere?». Se un domani qualcuno rimettesse quei join in INNER, questa
--    riga sparirebbe dalla vista e il test 6 diventerebbe rosso.
-- ⚠️ Il documento si crea con l'emittente dell'operatore: la RLS e' attiva e
--    una fixture che scrive fuori perimetro non passa la WITH CHECK.
-- ============================================================
-- Il cliente fatturabile, nel contesto dell'operatore: il legame BA -> emittente
-- lo scrive il trigger z90 verso l'emittente di chi agisce.
CREATE TEMP TABLE tmp_cli_vfl AS
SELECT c.* FROM dbops.fn_pgtap_crea_cliente_ba('vw fatture lista') c;

CREATE TEMP TABLE tmp_refs_vfl AS
SELECT
  (SELECT billing_account_id FROM tmp_cli_vfl)         AS billing_account_id,
  m.soggetto_ruolo_id                                  AS emittente_sr_id,
  script.fn_pgtap_registro_fattura(m.soggetto_ruolo_id) AS registro_id,
  config.fn_get_natura_doc_fiscale_id('FATTURA')       AS natura_fattura_id
FROM _mondo m;

-- ⚠️ L'INSERT sta in una CTE e non in un `CREATE TABLE AS INSERT`, che non
--    esiste: il `RETURNING` va comunque letto attraverso la `USING` della
--    policy, ed e' il motivo per cui la fattura nasce con l'emittente
--    dell'operatore e non con uno qualsiasi.
CREATE TEMP TABLE tmp_fatt_nuda AS
WITH ins AS (
    INSERT INTO vendite.fatture
        (registro_id, data, emittente_soggetto_ruolo_id, billing_account_id,
         tasso_cambio, natura_doc_id, meta)
    SELECT r.registro_id, DATE '2026-08-24', r.emittente_sr_id, r.billing_account_id,
           1, r.natura_fattura_id,
           jsonb_build_object('test_scope', 'pgtap_vw_fatture_lista')
      FROM tmp_refs_vfl r
    RETURNING id
)
SELECT id FROM ins;

SELECT is(
  (SELECT (count(*) = 1)::text FROM vendite.vw_fatture_lista v
    WHERE v.id = (SELECT id FROM tmp_fatt_nuda)),
  'true',
  '6) una fattura senza stato, utility e valuta compare lo stesso: i join sono LEFT'
);

-- ============================================================
-- 7) E ci compare con le decodifiche che DEVONO esserci risolte: il cliente
--    (via billing account -> soggetto_ruolo -> soggetto) e l'emittente fiscale
--    (derivato da emittenti_fiscali.soggetto_ruolo_id, che sulla fattura non
--    c'e' come colonna).
-- ============================================================
SELECT is(
  (SELECT (v.ragione_sociale_completa IS NOT NULL)::text || '|' ||
          (v.emittente_fiscale_id IS NOT NULL)::text || '|' ||
          (v.natura_doc_descrizione IS NOT NULL)::text
     FROM vendite.vw_fatture_lista v
    WHERE v.id = (SELECT id FROM tmp_fatt_nuda)),
  'true|true|true',
  '7) cliente, emittente fiscale e natura sono risolti sulla riga'
);

-- ============================================================
-- 8) ⭐ LA VISTA NON FA SCOPE PER CONTO SUO. E' il patto delle sei sorelle:
--    sola denormalizzazione, il perimetro lo fa la RLS. Un filtro nascosto
--    nella vista sarebbe una seconda regola di perimetro accanto alle policy,
--    e le due divergerebbero senza che nessuno se ne accorga.
--    ⚠️ Il confronto e' sugli INSIEMI degli id, non sui conteggi: due insiemi
--    diversi possono avere lo stesso numero di righe.
-- ============================================================
SELECT is(
  (SELECT count(*)::int FROM (
     SELECT id FROM vendite.fatture
     EXCEPT
     SELECT id FROM vendite.vw_fatture_lista
   ) d),
  0,
  '8) nessuna fattura visibile all''operatore manca dalla vista'
);

-- ============================================================
-- 9-10) ⭐ numero_documento e registro (P-1, 20260917-02)
--    Il numero parlante ha UNA sede (fn_numero_documento_fattura) e la lista
--    deve portarlo: un contatore nudo e' ambiguo (fattura 1 e nota di credito 1
--    nello stesso anno). NULL sulla non numerata, mai '' — il consumatore ha il
--    suo ripiego. ⚠️ fatture.registro_id e' NOT NULL: il registro c'e' anche
--    sulla bozza, e la vista lo risolve da subito (il LEFT e' forma, non caso).
-- ============================================================
SELECT is(
  (SELECT (v.numero_documento IS NULL)::text || '|' ||
          (v.registro_codice IS NOT NULL)::text || '|' ||
          (v.registro_descrizione IS NOT NULL)::text
     FROM vendite.vw_fatture_lista v
    WHERE v.id = (SELECT id FROM tmp_fatt_nuda)),
  'true|true|true',
  '9) sulla bozza non numerata numero_documento e'' NULL (non stringa vuota) e il registro e'' gia'' risolto'
);

-- Una fattura NUMERATA, costruita: numero e serie scritti dalla fixture su una
-- bozza (nessun guard di numerazione sull'UPDATE diretto: e' la fixture, non il
-- verbo), col registro della fixture.
UPDATE vendite.fatture
   SET numero = 4242, serie = 'PG', anno = 2026
 WHERE id = (SELECT id FROM tmp_fatt_nuda);

SELECT is(
  (SELECT v.numero_documento || '|' || coalesce(v.registro_codice, '<NULL>')
     FROM vendite.vw_fatture_lista v
    WHERE v.id = (SELECT id FROM tmp_fatt_nuda)),
  (SELECT '4242 - PG|' || r.codice
     FROM vendite.registri_fatturazione r
    WHERE r.id = (SELECT registro_id FROM tmp_refs_vfl)),
  '10) sulla numerata numero_documento e'' «numero - serie» dalla sede unica, e il registro e'' risolto'
);

-- ============================================================
-- 11) ⭐ LE SORELLE (Q-E, Tid 2026-09-17): lo stesso blocco registro_* sta su
--     tutte le viste che un registro ce l'hanno — e solo su quelle. Si
--     asserisce l'INSIEME, nei due versi: una sorella in piu' (contratti,
--     preventivi, offerte non hanno registro_id) o una in meno fa rosso.
-- ============================================================
SELECT is(
  (SELECT string_agg(c.relname, ',' ORDER BY c.relname)
     FROM pg_class c
     JOIN pg_namespace n ON n.oid = c.relnamespace
    WHERE n.nspname = 'vendite' AND c.relkind = 'v' AND c.relname LIKE 'vw\_%\_lista'
      -- ⚠️ vw_fatture_scadenze_lista porta il registro del DOCUMENTO della rata:
      --    non e' una sorella (una riga per rata, nessun `id`), sta fuori dal conto.
      AND c.relname <> 'vw_fatture_scadenze_lista'
      AND EXISTS (SELECT 1 FROM pg_attribute a
                   WHERE a.attrelid = c.oid AND a.attnum > 0 AND NOT a.attisdropped
                     AND a.attname = 'registro_codice')
      AND EXISTS (SELECT 1 FROM pg_attribute a
                   WHERE a.attrelid = c.oid AND a.attnum > 0 AND NOT a.attisdropped
                     AND a.attname = 'registro_descrizione')),
  'vw_ddt_lista,vw_fatture_lista,vw_ordini_lista,vw_resi_lista',
  '11) registro_codice/descrizione stanno esattamente sulle quattro sorelle con registro_id'
);

SELECT * FROM finish();
ROLLBACK;
