-- ------------------------------------------------------------
-- SPDX-License-Identifier: AGPL-3.0-or-later
-- pgtap-runner: owner
-- pgtap-runner-motivo: DROP/CREATE TRIGGER su tabelle di anagrafiche. Il test 3
--   chiama dbops.fn_apply_automazione_guard_utility_tipo_ruolo('AUTO', false),
--   che installa i trigger guard leggendo la tabella di configurazione: e' DDL,
--   e per giunta su TUTTE le tabelle configurate, non solo su quella in esame —
--   il primo rosso arrivava infatti da anagrafiche.categorie_clienti_listini,
--   che questo test non nomina. Il ruolo applicativo non ha il privilegio
--   TRIGGER su quelle tabelle e non deve averlo: applicare un'automazione e'
--   un'operazione di migrazione (gira in contesto ci_apply, 90_end), non
--   dell'applicazione. Stessa natura di anagrafiche/test-fn-create-indirizzo-v1.
--   ⚠️ Il marcatore copre SOLO il permesso. Il test 2 e' rimasto rosso anche
--   come owner, ed era un difetto vero: vedi la nota al test 2 piu' sotto.
-- pgTAP test per Zero ERP
--
-- Test: automazione guard utility->tipo_ruolo
--
-- Elenco test:
-- 1) A catalogo (CSV) anagrafiche.emittenti_fiscali_utilities e' configurata e abilitata
-- 2) ...con le colonne che la tabella ha davvero (utility_id, emittente_soggetto_ruolo_id)
-- 3) Ogni riga abilitata nomina colonne che esistono davvero
-- 4) Apply crea trigger con funzione script.trgfn_guard_utility_tipo_ruolo_by_cols
-- 5) Trigger creato risulta BEFORE INSERT/UPDATE sulla tabella target
-- 6) Il seed NON scrive: la configurazione e' un mirror del CSV
--
-- ⭐ RISCRITTO IL 2026-08-18. Prima i test 1 e 2 chiamavano il seed e poi
--    verificavano che la riga ci fosse — cioe' verificavano il seed contro se
--    stesso. Ora la sorgente e' il CSV
--    `80_data/sql/dbops/automazione_guard_utility_tipo_ruolo.csv` (decisione di
--    Tid: i seed girano da CSV; un misto di script e CSV sulla stessa tabella
--    non si applica), i test 1-3 leggono il catalogo e il test 6 presidia che
--    il seed non torni a scriverci.
--    Brief: docs/it/dev/work-done/brief-db-automazione-guard-utility-righe-sfuggite.md
-- ------------------------------------------------------------

-- ⚠️ Transazione, e non e' una formalita'. Il cleanup di questo file sta in
--   coda: col runner vero (pg_prove gira con ON_ERROR_STOP) un fallimento a
--   meta' non ci arriva mai, e i dati di prova restano nel database a rompere
--   la corsa successiva — che vede un rosso non suo.
--   Brief: brief-db-pgtap-runner-rls-baseline §15.3.
BEGIN;

-- ⚠️ Vincoli DIFFERITI: senza questa riga il test smetterebbe di verificarli.
--   Un trigger DEFERRABLE INITIALLY DEFERRED scatta al COMMIT, e qui il COMMIT
--   non arriva mai (si chiude in ROLLBACK): sarebbero saltati in silenzio, e il
--   file diventerebbe verde per sottrazione. Nel DB ce ne sono 365.
--   IMMEDIATE li riporta a scattare a fine di OGNI istruzione — cioe' esatta-
--   mente come si comportavano prima, quando il file girava in autocommit e
--   ogni istruzione era una transazione a se'. In testa e non in coda apposta:
--   in coda scatterebbero tutti insieme DOPO il cleanup, su righe ormai
--   cancellate. Brief: brief-db-pgtap-runner-rls-baseline §17.
SET CONSTRAINTS ALL IMMEDIATE;

-- Contesto applicativo: questo test gira come gira l'applicazione (ruolo
-- OPERATORE + RLS attiva), non come owner. Senza, con FORCE ROW LEVEL
-- SECURITY disattivo l'owner salta la RLS e il test non la esercita mai.
-- Brief: brief-db-pgtap-runner-rls-baseline §8.
DO $ctx$ BEGIN PERFORM script.fn_pgtap_set_contesto_operatore(); END $ctx$;

SELECT plan(6);

-- ⭐ IL SEED NON POPOLA PIU' — riscritto il 2026-08-18.
--   Fino al `20260818-56` questo file chiamava
--   `dbops.fn_seed_automazione_guard_utility_tipo_ruolo(...)` e poi verificava
--   che la riga esistesse: cioe' verificava il seed contro se stesso.
--   Da oggi la configurazione e' un mirror del CSV
--   `80_data/sql/dbops/automazione_guard_utility_tipo_ruolo.csv` (decisione di
--   Tid: i seed girano da CSV, e un misto di script e CSV sulla stessa tabella
--   non si applica). Quindi i test 1-3 leggono il CATALOGO, che e' la
--   sorgente, e il test 6 presidia che il seed non torni a scriverci.
SELECT ok(
  EXISTS (
    SELECT 1
      FROM dbops.automazione_guard_utility_tipo_ruolo a
     WHERE a.schema_name = 'anagrafiche'
       AND a.table_name = 'emittenti_fiscali_utilities'
       AND a.enabled = true
  ),
  'A catalogo (CSV) anagrafiche.emittenti_fiscali_utilities e'' configurata e abilitata'
);

-- ⚠️ QUESTO E'' IL TEST CHE HA TROVATO IL DIFETTO, e vale la pena dire cosa
--   diceva: la riga portava `soggetto_ruolo_id`, che su questa tabella **non
--   esiste** — la colonna vera e' `emittente_soggetto_ruolo_id`, ed e' quella
--   che il trigger vivo usava gia'. Configurazione e database dicevano cose
--   diverse, e `fn_apply_*` scartava la riga in silenzio (filtra su
--   `LIKE '%_soggetto_ruolo_id'`, che il nome generico non passa).
--   Non era una fixture rimasta indietro: era la configurazione, ferma al
--   2026-02-16 perche' il seed scriveva con `ON CONFLICT DO NOTHING`.
SELECT ok(
  EXISTS (
    SELECT 1
      FROM dbops.automazione_guard_utility_tipo_ruolo a
     WHERE a.schema_name = 'anagrafiche'
       AND a.table_name = 'emittenti_fiscali_utilities'
       AND a.utility_column = 'utility_id'
       AND a.soggetto_ruolo_column = 'emittente_soggetto_ruolo_id'
  ),
  'Configurazione con le colonne che la tabella ha davvero (utility_id, emittente_soggetto_ruolo_id)'
);

-- ⚠️ E che siano le colonne VERE non e'' un dettaglio del test: se il catalogo
--   nomina una colonna inesistente, `fn_apply_*` salta la riga e nessuno lo
--   dice. Si verifica contro il catalogo di sistema, non contro una costante.
SELECT ok(
  (SELECT bool_and(dbops.fn_col_exists(a.schema_name, a.table_name, c.col))
     FROM dbops.automazione_guard_utility_tipo_ruolo a
     CROSS JOIN LATERAL (VALUES (a.utility_column), (a.soggetto_ruolo_column)) AS c(col)
    WHERE a.enabled = true),
  'Ogni riga abilitata nomina colonne che esistono davvero'
);

SELECT dbops.fn_apply_automazione_guard_utility_tipo_ruolo('AUTO', false);

SELECT ok(
  EXISTS (
    SELECT 1
      FROM pg_trigger t
      JOIN pg_class c ON c.oid = t.tgrelid
      JOIN pg_namespace n ON n.oid = c.relnamespace
      JOIN pg_proc p ON p.oid = t.tgfoid
      JOIN pg_namespace pn ON pn.oid = p.pronamespace
     WHERE n.nspname = 'anagrafiche'
       AND c.relname = 'emittenti_fiscali_utilities'
       AND NOT t.tgisinternal
       AND pn.nspname = 'script'
       AND p.proname = 'trgfn_guard_utility_tipo_ruolo_by_cols'
  ),
  'Apply crea trigger con funzione script.trgfn_guard_utility_tipo_ruolo_by_cols'
);

SELECT ok(
  EXISTS (
    SELECT 1
      FROM pg_trigger t
      JOIN pg_class c ON c.oid = t.tgrelid
      JOIN pg_namespace n ON n.oid = c.relnamespace
     WHERE n.nspname = 'anagrafiche'
       AND c.relname = 'emittenti_fiscali_utilities'
       AND NOT t.tgisinternal
       AND (t.tgtype & 2) = 2
       AND (t.tgtype & 4) = 4
       AND (t.tgtype & 16) = 16
  ),
  'Trigger creato risulta BEFORE INSERT/UPDATE sulla tabella target'
);

-- ============================================================
-- 6) Il seed NON scrive: la configurazione e' un mirror del CSV
-- ============================================================
-- ⚠️ E' il test che presidia la regola, non un dettaglio. La configurazione di
--   questa automazione e' rimasta ferma al 2026-02-16 proprio perche' la
--   scriveva il seed (`ON CONFLICT DO NOTHING`: scritta una volta, mai piu'
--   raddrizzata) mentre lo schema andava avanti — al 2026-08-18 quattro righe
--   su sette descrivevano tabelle che avevano perso `utility_id` o erano state
--   rinominate.
--   ⚠️ Si misura il CONTENUTO, non solo il conteggio: un seed che inserisse e
--   cancellasse, o che riscrivesse una colonna, lascerebbe il conteggio
--   invariato e passerebbe.
CREATE TEMP TABLE _impronta_prima AS
SELECT md5(coalesce(string_agg(
            schema_name || '|' || table_name || '|' || utility_column || '|' ||
            soggetto_ruolo_column || '|' || enabled::text || '|' || exec_mode,
            E'\n' ORDER BY schema_name, table_name), '<vuota>')) AS h
  FROM dbops.automazione_guard_utility_tipo_ruolo;

SELECT dbops.fn_seed_automazione_guard_utility_tipo_ruolo(ARRAY['anagrafiche']);

SELECT is(
    (SELECT md5(coalesce(string_agg(
                schema_name || '|' || table_name || '|' || utility_column || '|' ||
                soggetto_ruolo_column || '|' || enabled::text || '|' || exec_mode,
                E'\n' ORDER BY schema_name, table_name), '<vuota>'))
       FROM dbops.automazione_guard_utility_tipo_ruolo),
    (SELECT h FROM _impronta_prima),
    '6. Chiamare il seed non cambia la configurazione: la sorgente e'' il CSV'
);

SELECT * FROM finish();

-- Il ROLLBACK e' la garanzia: comunque vada — verde, rosso, o morto a meta' —
-- questo file non lascia nulla dietro di se'. Le DELETE del cleanup restano
-- perche' dove sono un'asserzione devono girare davvero.
ROLLBACK;
