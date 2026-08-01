-- ------------------------------------------------------------
-- SPDX-License-Identifier: GPL-3.0-or-later
-- pgTAP test per Zero ERP
-- Test: la denominazione dell'emittente viene dal SOGGETTO, non da
--       anagrafiche.emittenti_fiscali.descrizione
--       (brief-emittente-ragione-sociale-dal-soggetto.md §5 Fase 1.3)
--       changeSet 20260802-20 (6 viste) e 20260802-21 (3 funzioni)
-- ------------------------------------------------------------
-- PERCHE' META' DI QUESTO FILE E' STRUTTURALE E NON DI VALORE.
--   Le 6 viste sono `security_invoker=on`: fuori dal contesto operatore
--   (GUC app.current_user_id vuota) restituiscono ZERO righe, quindi una
--   prova di valore su di esse si limiterebbe a saltare in silenzio.
--   Per quelle la prova che regge sempre e' STRUTTURALE — «la definizione
--   non nomina piu' ef.descrizione».
--
-- ⚠️ AGGIORNATO ALLA FASE 4 (2026-08-02). Nella prima stesura la divergenza
--   fra i due valori si otteneva riscrivendo `descrizione` con una
--   SENTINELLA, ed era il cuore dei due test di valore. Con la colonna
--   DROPPATA (20260802-22) quella divergenza non e' piu' costruibile — e non
--   serve piu': non esiste una seconda sorgente da cui il valore sbagliato
--   possa arrivare. Al suo posto subentra il test 11, `hasnt_column`, che e'
--   la forma definitiva della stessa domanda.
--   I test 1-10 restano pur essendo ormai garantiti dalla DROP: costano
--   nulla e presidiano il caso in cui qualcuno ricrei la colonna e ricominci
--   a leggerla.
-- ------------------------------------------------------------
-- Indice test (1..13):
--  1-6)  le 6 viste vw_*_lista non nominano piu' ef.descrizione
--        (contratti, preventivi, offerte, ordini, ddt, resi)
--  7-9)  le 3 funzioni script.fn_get_* non nominano piu' ef.descrizione
--        (user_emittenti_scope, operatore_detail, user_profile)
-- 10)    fn_get_user_profile non dichiara piu' il %TYPE sulla colonna
--        eliminata: un %TYPE non somiglia a una lettura ma lo e'
-- 11)    la colonna non esiste piu' (Fase 4)
-- 12-13) PROVA DI VALORE: le due funzioni continuano a dare la ragione
--        sociale del soggetto dopo la DROP (nessuna regressione)
-- ------------------------------------------------------------

BEGIN;
SELECT plan(13);

-- ============================================================
-- 1-6) Strutturale: le viste non nominano piu' ef.descrizione
--      pg_get_viewdef conserva gli alias, quindi la stringa
--      'ef.descrizione' compare letteralmente se e' rimasta.
--      ⚠️ Cercare il solo 'descrizione' darebbe falsi positivi:
--      queste viste proiettano anche utility_descrizione,
--      stato_descrizione, causale_trasporto_descrizione...
-- ============================================================
SELECT ok(
    pg_get_viewdef('vendite.vw_contratti_lista'::regclass, true) NOT LIKE '%ef.descrizione%',
    '1) vw_contratti_lista non legge piu'' ef.descrizione');

SELECT ok(
    pg_get_viewdef('vendite.vw_preventivi_lista'::regclass, true) NOT LIKE '%ef.descrizione%',
    '2) vw_preventivi_lista non legge piu'' ef.descrizione');

SELECT ok(
    pg_get_viewdef('vendite.vw_offerte_commerciali_lista'::regclass, true) NOT LIKE '%ef.descrizione%',
    '3) vw_offerte_commerciali_lista non legge piu'' ef.descrizione');

SELECT ok(
    pg_get_viewdef('vendite.vw_ordini_lista'::regclass, true) NOT LIKE '%ef.descrizione%',
    '4) vw_ordini_lista non legge piu'' ef.descrizione');

SELECT ok(
    pg_get_viewdef('vendite.vw_ddt_lista'::regclass, true) NOT LIKE '%ef.descrizione%',
    '5) vw_ddt_lista non legge piu'' ef.descrizione');

SELECT ok(
    pg_get_viewdef('vendite.vw_resi_lista'::regclass, true) NOT LIKE '%ef.descrizione%',
    '6) vw_resi_lista non legge piu'' ef.descrizione');

-- ============================================================
-- 7-10) Strutturale sulle funzioni.
--
-- 🔴 I COMMENTI VANNO TOLTI PRIMA DI CERCARE, e la prima stesura di
--    questo file non lo faceva: 7-10 sono nati ROSSI su una migration
--    corretta, perche' la stringa 'ef.descrizione' sopravviveva nei
--    commenti che SPIEGANO perche' e' stata tolta. Un presidio che
--    grida al lupo si smette di credere come uno che tace.
--
--    Le viste (1-6) sono immuni per costruzione: pg_get_viewdef
--    ricostruisce la definizione dal parse tree e i commenti li perde.
--    `pg_proc.prosrc` no — e' il sorgente letterale, commenti inclusi.
--    Stessa domanda, due fonti che si comportano in modo opposto.
-- ============================================================
CREATE TEMP VIEW tmp_fn_codice AS
SELECT p.proname,
       -- via i commenti di riga: resta il codice, che e' cio' che la
       -- DROP di Fase 4 guardera' davvero
       regexp_replace(p.prosrc, '--[^\n]*', '', 'g') AS codice
  FROM pg_proc p
  JOIN pg_namespace n ON n.oid = p.pronamespace
 WHERE n.nspname = 'script'
   AND p.proname IN ('fn_get_user_emittenti_scope',
                     'fn_get_operatore_detail',
                     'fn_get_user_profile');

SELECT ok(
    (SELECT codice NOT LIKE '%ef.descrizione%'
       FROM tmp_fn_codice WHERE proname = 'fn_get_user_emittenti_scope'),
    '7) fn_get_user_emittenti_scope non legge piu'' ef.descrizione');

SELECT ok(
    (SELECT codice NOT LIKE '%ef.descrizione%'
       FROM tmp_fn_codice WHERE proname = 'fn_get_operatore_detail'),
    '8) fn_get_operatore_detail non legge piu'' ef.descrizione');

SELECT ok(
    (SELECT codice NOT LIKE '%ef.descrizione%'
       FROM tmp_fn_codice WHERE proname = 'fn_get_user_profile'),
    '9) fn_get_user_profile non legge piu'' ef.descrizione');

-- ============================================================
-- 10) Il %TYPE e' un riferimento alla colonna quanto una SELECT.
--     Lasciato nel DECLARE, la DROP di Fase 4 fallirebbe qui invece
--     che dove la si lancia — e il messaggio non direbbe perche'.
-- ============================================================
SELECT ok(
    (SELECT codice NOT LIKE '%emittenti_fiscali.descrizione%'
       FROM tmp_fn_codice WHERE proname = 'fn_get_user_profile'),
    '10) fn_get_user_profile non dichiara piu'' %TYPE su emittenti_fiscali.descrizione');

-- ============================================================
-- 11) La colonna non c'e' piu'. E' la Fase 4, ed e' anche cio' che
--     rende superflua la sentinella della stesura precedente: senza
--     una seconda sorgente, il valore sbagliato non ha da dove venire.
-- ============================================================
SELECT hasnt_column(
    'anagrafiche', 'emittenti_fiscali', 'descrizione',
    '11) anagrafiche.emittenti_fiscali.descrizione non esiste piu''');

-- Contesto: un utente che ha davvero un emittente in whitelist, e il
-- cui soggetto ha una ragione sociale. Se non esiste, i due test di
-- valore saltano dichiarandolo.
CREATE TEMP TABLE tmp_ctx_emittente AS
SELECT uef.auth_user_id,
       s_ef.ragione_sociale_completa AS attesa
  FROM config.user_emittenti_fiscali uef
  JOIN anagrafiche.emittenti_fiscali ef  ON ef.id = uef.emittente_fiscale_id
  JOIN anagrafiche.soggetti_ruoli   sr_ef ON sr_ef.id = ef.soggetto_ruolo_id
  JOIN anagrafiche.soggetti         s_ef  ON s_ef.id = sr_ef.soggetto_id
 WHERE s_ef.ragione_sociale_completa IS NOT NULL
   AND btrim(s_ef.ragione_sociale_completa) <> ''
 ORDER BY uef.auth_user_id
 LIMIT 1;

-- ============================================================
-- 12) Prova di valore: lo scope emittenti mostra la ragione sociale
--     del soggetto. L'assert e' su UGUAGLIANZA con l'attesa e non su
--     "non vuoto": quest'ultimo lo passerebbe anche un NULL.
-- ============================================================
SELECT CASE
    WHEN NOT EXISTS (SELECT 1 FROM tmp_ctx_emittente)
    THEN skip('12) Nessun operatore con emittente in whitelist — test saltato')
    ELSE is(
        (SELECT sc.emittente_descrizione
           FROM tmp_ctx_emittente c,
                LATERAL script.fn_get_user_emittenti_scope(c.auth_user_id) sc),
        (SELECT attesa FROM tmp_ctx_emittente),
        '12) fn_get_user_emittenti_scope porta la ragione sociale del soggetto')
END;

-- ============================================================
-- 13) Prova di valore sull'aggregato del drawer operatore.
--     `emittenti_descrizione` e' uno string_agg: con un solo
--     emittente in whitelist (UNIQUE su auth_user_id lo garantisce)
--     coincide col valore singolo.
-- ============================================================
SELECT CASE
    WHEN NOT EXISTS (SELECT 1 FROM tmp_ctx_emittente)
    THEN skip('13) Nessun operatore con emittente in whitelist — test saltato')
    ELSE is(
        (SELECT od.emittenti_descrizione
           FROM tmp_ctx_emittente c,
                LATERAL script.fn_get_operatore_detail(c.auth_user_id) od),
        (SELECT attesa FROM tmp_ctx_emittente),
        '13) fn_get_operatore_detail aggrega la ragione sociale del soggetto')
END;

SELECT * FROM finish();
ROLLBACK;
