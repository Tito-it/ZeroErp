-- ------------------------------------------------------------
-- SPDX-License-Identifier: AGPL-3.0-or-later
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
-- Indice test (1..14):
--  1-6)  le 6 viste vw_*_lista non nominano piu' ef.descrizione
--        (contratti, preventivi, offerte, ordini, ddt, resi)
--  7-9)  le 3 funzioni script.fn_get_* non nominano piu' ef.descrizione
--        (user_emittenti_scope, operatore_detail, user_profile)
-- 10)    fn_get_user_profile non dichiara piu' il %TYPE sulla colonna
--        eliminata: un %TYPE non somiglia a una lettura ma lo e'
-- 11)    la colonna non esiste piu' (Fase 4)
-- 12-14) PROVA DI VALORE sulle TRE funzioni toccate: continuano a dare la
--        ragione sociale del soggetto dopo la DROP (nessuna regressione)
--
-- ⚠️ Il test 14 nasce da un rilievo del BE (2026-08-02): delle tre funzioni
--    modificate, i file dedicati di `fn_get_user_emittenti_scope` e
--    `fn_get_user_profile` sono in `baseline-rossi.tsv` come ERRORE_FIXTURE,
--    e un file che muore nel fixture non esegue NESSUNA asserzione: la sua
--    copertura vale zero, non «parziale». Il rilievo era giusto a meta':
--    `fn_get_user_emittenti_scope` era gia' coperta qui dal test 12, ma
--    `fn_get_user_profile` aveva solo asserzioni strutturali (9 e 10) — ed e'
--    l'unica delle tre che ha davvero CAMBIATO valore, perche' prima leggeva
--    `ef.descrizione` nuda. Era il buco vero. Lo chiude il 14.
-- ------------------------------------------------------------

BEGIN;

-- ⚠️ Vincoli DIFFERITI: senza questa riga il test smetterebbe di verificarli.
--   Un trigger DEFERRABLE INITIALLY DEFERRED scatta al COMMIT, e qui il COMMIT
--   non arriva mai (si chiude in ROLLBACK): sarebbero saltati in silenzio, e il
--   file sarebbe verde per sottrazione. IMMEDIATE li riporta a scattare a fine
--   di ogni istruzione. In testa e non in coda: in coda scatterebbero dopo il
--   cleanup, su righe ormai cancellate.
--   Brief: brief-db-pgtap-runner-rls-baseline §19.
SET CONSTRAINTS ALL IMMEDIATE;

-- Contesto applicativo: questo test gira come gira l'applicazione (ruolo
-- OPERATORE + RLS attiva), non come owner. Senza, con FORCE ROW LEVEL
-- SECURITY disattivo l'owner salta la RLS e il test non la esercita mai.
-- Brief: brief-db-pgtap-runner-rls-baseline §8.
DO $ctx$ BEGIN PERFORM script.fn_pgtap_set_contesto_operatore(); END $ctx$;

SELECT plan(14);

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

-- ============================================================
-- 14) fn_get_user_profile — la terza funzione, e l'unica che ha
--     cambiato VALORE: prima metteva in `emittente_descrizione` la
--     `ef.descrizione` nuda, cioe' l'etichetta interna.
--
--     L'asserzione e' SELF-REFERENZIALE, ed e' per questo che e' forte:
--     il blocco `emittente` del profilo e' costruito come
--         jsonb_build_object(..., 'emittente_descrizione', ...)
--           || fn_get_soggetto_dati_by_ruolo(...)
--     quindi porta nello STESSO oggetto sia quella chiave sia la
--     `ragione_sociale_completa` del soggetto. Era esattamente la
--     patologia del cantiere — due valori diversi sotto due chiavi
--     vicine, e il consumatore che sceglieva. Ora devono coincidere, e
--     il test non dipende da nessun dato esterno per dirlo.
--
--     Il candidato replica i guard della funzione (identita OPERATORE
--     attiva e in finestra, risorsa umana attiva e in finestra): la fn
--     solleva E_ADMIN_VALIDAZIONE su chi non li soddisfa, e un raise
--     qui abortirebbe la transazione facendo morire il file.
-- ============================================================
CREATE TEMP TABLE tmp_ctx_profilo AS
SELECT au.id AS auth_user_id
  FROM django.auth_user au
  JOIN anagrafiche.identita_digitali idg
    ON idg.auth_user_id = au.id
   AND idg.ruolo_applicativo = 'OPERATORE'
   AND idg.attivo IS TRUE
   AND (idg.valido_dal IS NULL OR idg.valido_dal <= script.fn_data_operativa())
   AND (idg.valido_al  IS NULL OR idg.valido_al  >= script.fn_data_operativa())
  JOIN anagrafiche.risorse_umane ru
    ON ru.soggetto_ruolo_id = idg.soggetto_ruolo_id
   AND ru.attivo IS TRUE
   AND (ru.valido_dal IS NULL OR ru.valido_dal <= script.fn_data_operativa())
   AND (ru.valido_al  IS NULL OR ru.valido_al  >= script.fn_data_operativa())
 ORDER BY au.id
 LIMIT 1;

SELECT CASE
    WHEN NOT EXISTS (SELECT 1 FROM tmp_ctx_profilo)
    THEN skip('14) Nessun operatore che soddisfi i guard del profilo — test saltato')
    ELSE is(
        (SELECT p.prof -> 'emittente' ->> 'emittente_descrizione'
           FROM tmp_ctx_profilo c,
                LATERAL (SELECT script.fn_get_user_profile(c.auth_user_id) AS prof) p),
        (SELECT p.prof -> 'emittente' ->> 'ragione_sociale_completa'
           FROM tmp_ctx_profilo c,
                LATERAL (SELECT script.fn_get_user_profile(c.auth_user_id) AS prof) p),
        '14) fn_get_user_profile: emittente_descrizione coincide con la ragione sociale del soggetto')
END;

SELECT * FROM finish();
ROLLBACK;
