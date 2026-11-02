-- ------------------------------------------------------------
-- SPDX-License-Identifier: AGPL-3.0-or-later
-- pgtap-contesto: escluso — questo file non interroga NESSUN dato di dominio:
--   legge il catalogo di PostgreSQL (pg_class, pg_constraint, pg_policy) e il
--   registro del debito. Un contesto operatore non cambierebbe una riga del
--   risultato, e metterlo darebbe l'impressione che la RLS qui sia esercitata,
--   che sarebbe falso. Le policy si provano nei file test-rls-* accanto.
--   Dichiarazione leggibile dal cancello scripts/guardrail_pgtap_preambolo.py:
--   distingue «escluso apposta» da «dimenticato».
-- pgtap-runner: owner
-- pgtap-runner-motivo: i test 4..8 CREANO tabelle e policy di prova (in
--   transazione, poi annullata) perche' un criterio si prova COSTRUENDO i casi.
--   E' DDL, piu' un CREATE POLICY: il ruolo applicativo non ne fa e non ne deve
--   fare. E' il criterio 1 di scripts/testpgtap.sh, lo stesso del file gemello
--   test-rls-viste-security-invoker.sql.
--
-- pgTAP test ANTI-REGRESSIONE — il PERIMETRO della row level security.
--
-- ChangeSet di riferimento: 20260909-75 (registro), 20260909-76 (vista),
--                           20260909-77 (seed del debito)
-- Brief: brief-db-perimetro-emittente-righe-documento §8 e §10
--
-- Indice test (plan 8):
--   1) ⭐ il criterio vede ancora le DODICI tabelle che il brief aveva misurato
--      — o sono state armate davvero
--   2) ⛔ IL PRESIDIO: nessuna riga fuori da DEBITO_DICHIARATO
--   3) ⭐ ogni criterio ammesso dal CHECK del registro e' un ramo VIVO della
--      vista (perimetro letto dal vincolo, non da un elenco)
--   4) ⛔ una figlia NUOVA di una tabella protetta esce NON_DICHIARATO (COSTRUITO)
--   5) ⭐ e armata davvero (RLS + policy) esce dal perimetro (COSTRUITO)
--   6) ⚠️ una figlia di una tabella NON protetta non entra (COSTRUITO)
--   7) ⛔ una policy con la RLS spenta esce come POLICY_INERTE anche senza
--      nessun padre protetto (COSTRUITO)
--   8) ⛔ una riga di registro che non ha piu' il suo difetto esce
--      DEBITO_ESTINTO (COSTRUITO)
--
-- ────────────────────────────────────────────────────────────────
-- ⛔ IL PROBLEMA, E PERCHE' NON SI VEDE.
--   Una riga che appartiene a una riga protetta e non e' protetta a sua volta
--   non produce nessun errore: produce *piu' righe*. Il sintomo di un perimetro
--   mancante e' **vedere di piu'**, e non c'e' nessuna pagina rotta, nessun log,
--   nessun test che diventa rosso da solo.
--   ⚠️ E la difesa parziale e' peggio dell'assenza, perche' sembra una difesa:
--   fino al 2026-09-09 le sette partizioni di `vendite.note` avevano tutte la
--   loro policy, ed erano tutte aggirabili con un `SELECT` dal padre.
--
-- ⛔ PERCHE' IL PERIMETRO E' UN CRITERIO E NON UN ELENCO.
--   E' la lezione con cui il cantiere si e' chiuso, e l'aveva pagata due volte:
--     * il §2 del brief diceva «fatture: tutte protette». Erano protette le
--       CINQUE che l'elenco nominava; sei figlie dirette e una nipote non
--       c'erano, e sono saltate fuori solo rileggendo il catalogo per FK;
--     * il §10 contava dodici tabelle scoperte. Erano dodici **in vendite**:
--       applicato a tutto il database, lo stesso criterio ne trova trenta.
--   ⇒ *Un elenco scritto a mano ha per perimetro cio' che chi lo scriveva
--     aveva in mente.* Qui il perimetro lo dice `pg_constraint`.
--
-- ⛔ E L'INVARIANTE NON E' «LA VISTA E' VUOTA».
--   Trenta tabelle sono scoperte oggi, ognuna per una ragione che qualcuno ha
--   guardato e scritto in `dbops.rls_perimetro_debito`. Un cancello rosso dal
--   primo giorno viene disattivato, e un presidio spento e' peggio di uno
--   assente. L'invariante verificabile e' **«nessuna riga fuori da
--   DEBITO_DICHIARATO»** — e vale nei due versi:
--     * `NON_DICHIARATO`  = una tabella nuova e' nata scoperta: allarme;
--     * `DEBITO_ESTINTO`  = una riga di registro non ha piu' il suo difetto:
--       va TOLTA dal CSV, o zittisce per sempre una tabella che nel frattempo
--       potrebbe tornare scoperta per un'altra strada. E' il verso in cui un
--       registro marcisce senza che nessuno se ne accorga.
--
-- ⚠️ DICHIARARE UN DEBITO ZITTISCE QUESTO TEST, e va detto qui.
--   Il test 2 tace su tutto cio' che sta nel registro. E' il patto che permette
--   di accendere il cancello subito invece che a bonifica finita — ma vuol dire
--   che il presidio vero, per una riga nuova, sono i test 4..8: provano che il
--   flag e' un GESTO e non l'impostazione di fabbrica.
--
-- ⚠️ COSA QUESTO TEST NON DICE. Che una policy sia scritta bene. Dice che
--   esiste e che viene applicata. Se filtri le righe giuste lo provano i file
--   test-rls-*-satelliti.sql accanto a questo.
-- ------------------------------------------------------------

BEGIN;
-- ⚠️ Vincoli DIFFERITI: senza questa riga il test smetterebbe di verificarli.
--   Un trigger DEFERRABLE INITIALLY DEFERRED scatta al COMMIT, e qui il COMMIT
--   non arriva mai (si chiude in ROLLBACK): sarebbero saltati in silenzio, e il
--   file sarebbe verde per sottrazione.
SET CONSTRAINTS ALL IMMEDIATE;

SELECT plan(8);

-- ============================================================
-- 1. ⭐ IL CRITERIO NON SI E' RISTRETTO
-- ============================================================
-- ⛔ Le dodici tabelle che il §10 del brief ha misurato il 2026-09-09. Restano
--   scritte qui APPOSTA, ed e' l'unico elenco del file: non e' il perimetro
--   (quello lo decide il criterio), e' la prova che il perimetro non si e'
--   ristretto. Senza, «zero righe non dichiarate» sarebbe compatibile con una
--   rete che ha smesso di pescare.
-- ⭐ E la via d'uscita non e' il criterio stesso — sarebbe circolare — ma un
--   fatto strutturale indipendente: la tabella e' ARMATA davvero, cioe' ha la
--   row level security accesa E almeno una policy. Il giorno in cui il cantiere
--   lotti chiude, quelle cinque righe escono di qui per la ragione giusta.
SELECT is_empty(
    $$WITH misurate (sch, tab) AS (
          VALUES
            -- famiglia lotti
            ('vendite','fatturazione_lotti_esiti'),
            ('vendite','fatturazione_lotti_fatture'),
            ('vendite','fatturazione_lotti_gruppi'),
            ('vendite','fatturazione_lotti_log'),
            ('vendite','fatturazione_lotti_task_runs'),
            -- famiglia attivita' / commesse
            ('vendite','attivita_fatturabili'),
            ('vendite','attivita_consumi'),
            ('vendite','commesse_attivita_log'),
            ('vendite','commesse_sorgenti'),
            -- famiglia listini
            ('vendite','listini_righe'),
            ('vendite','listini_righe_componenti'),
            -- arrotondamenti
            ('vendite','fatture_arrotondamenti_scope')
      ), viva AS (
          SELECT m.sch, m.tab, c.oid
            FROM misurate m
            JOIN pg_namespace n ON n.nspname = m.sch
            JOIN pg_class c ON c.relnamespace = n.oid AND c.relname = m.tab
                           AND c.relkind = ANY (ARRAY['r'::"char", 'p'::"char"])
      )
      SELECT v.sch || '.' || v.tab
        FROM viva v
       WHERE NOT EXISTS (SELECT 1 FROM dbops.vw_rls_perimetro_scoperto w
                          WHERE w.schema_tabella = v.sch
                            AND w.nome_tabella   = v.tab
                            AND w.criterio = 'FIGLIA_DI_TABELLA_PROTETTA')
         AND NOT (   (SELECT c.relrowsecurity FROM pg_class c WHERE c.oid = v.oid)
                 AND EXISTS (SELECT 1 FROM pg_policy p WHERE p.polrelid = v.oid))$$,
    '1. il criterio vede ancora le dodici tabelle misurate dal brief, o sono state armate davvero'
);

-- ============================================================
-- 2. ⛔ IL PRESIDIO
-- ============================================================
-- In fallimento il messaggio NOMINA le tabelle e dice in quale dei due versi:
-- su un difetto che non ha nessun altro sintomo, sapere QUALE e' meta' del
-- lavoro.
SELECT is(
    (SELECT string_agg(v.stato || ' ' || v.criterio || ' ' ||
                       v.schema_tabella || '.' || v.nome_tabella,
                       ', ' ORDER BY v.stato, v.schema_tabella, v.nome_tabella)
       FROM dbops.vw_rls_perimetro_scoperto v
      WHERE v.stato <> 'DEBITO_DICHIARATO'),
    NULL,
    '2. nessuna tabella scoperta fuori dal registro, e nessuna riga di registro senza piu'' il suo difetto'
);

-- ============================================================
-- I casi costruiti — da qui in giu' si semina
-- ============================================================
-- ⛔ I test 1 e 2 girano PRIMA: dopo queste righe il database contiene apposta
--   una tabella scoperta, e l'ordine non e' un dettaglio.

-- Figlia di una tabella protetta, nuda: deve essere pescata.
CREATE TABLE dbops.pgtap_rls_figlia (
    id           bigint PRIMARY KEY,
    contratto_id bigint NOT NULL REFERENCES vendite.contratti (id)
);

-- Stessa parentela, ma armata davvero: deve USCIRE dal perimetro.
CREATE TABLE dbops.pgtap_rls_figlia_armata (
    id           bigint PRIMARY KEY,
    contratto_id bigint NOT NULL REFERENCES vendite.contratti (id)
);
ALTER TABLE dbops.pgtap_rls_figlia_armata ENABLE ROW LEVEL SECURITY;
CREATE POLICY rls_pgtap_figlia_armata ON dbops.pgtap_rls_figlia_armata
    FOR ALL USING (true) WITH CHECK (true);

-- Figlia di una tabella NON protetta: non deve entrare. Senza questo caso il
-- criterio potrebbe essere «ogni tabella vuole una policy», che e' una regola
-- DIVERSA e sbagliata, e si impara a metterla ovunque per far tacere il test.
CREATE TABLE dbops.pgtap_rls_innocua (
    id          bigint PRIMARY KEY,
    sorgente_id integer NOT NULL REFERENCES config.sorgenti (id)
);

-- Nessun padre protetto, ma una policy che non verra' mai applicata: e' il
-- secondo criterio, e il primo non la vedrebbe mai.
CREATE TABLE dbops.pgtap_rls_policy_inerte (id bigint PRIMARY KEY);
CREATE POLICY rls_pgtap_inerte ON dbops.pgtap_rls_policy_inerte
    FOR SELECT USING (true);

-- ⚠️ Il debito estinto vuole una tabella SUA, e non e' pignoleria: se lo si
--   appoggiasse a una delle altre, il ramo DEBITO_ESTINTO la farebbe ricomparire
--   nella vista e il caso «armata, quindi fuori dal perimetro» non sarebbe piu'
--   distinguibile da «armata, ma il registro la nomina ancora». Un caso
--   costruito che ne inquina un altro prova meno di quanto sembra.
CREATE TABLE dbops.pgtap_rls_debito_pagato (
    id           bigint PRIMARY KEY,
    contratto_id bigint NOT NULL REFERENCES vendite.contratti (id)
);
ALTER TABLE dbops.pgtap_rls_debito_pagato ENABLE ROW LEVEL SECURITY;
CREATE POLICY rls_pgtap_debito_pagato ON dbops.pgtap_rls_debito_pagato
    FOR ALL USING (true) WITH CHECK (true);

INSERT INTO dbops.rls_perimetro_debito
    (id, criterio, schema_tabella, nome_tabella, ragione)
VALUES (999001, 'FIGLIA_DI_TABELLA_PROTETTA', 'dbops', 'pgtap_rls_debito_pagato',
        'Riga di prova del pgTAP: dichiara un debito su una tabella che e'' gia'' armata, per provare il verso DEBITO_ESTINTO del presidio.');

-- ============================================================
-- 3. ⭐ I RAMI DELLA VISTA CONTRO IL CHECK DEL REGISTRO
-- ============================================================
-- ⛔ Il perimetro non e' un elenco mio: e' il CHECK di
--   dbops.rls_perimetro_debito. Il giorno in cui qualcuno aggiunge un criterio
--   al vocabolario e non gli da' un ramo nella vista, quel criterio sarebbe
--   dichiarabile e mai prodotto — cioe' un debito che zittisce qualcosa che
--   nessuno misura. Qui diventa rosso e dice quale.
-- ⭐ Gira DOPO i casi costruiti apposta: e' con quelli che entrambi i rami sono
--   abitati per costruzione, invece che per come e' fatto il database di oggi.
-- ⛔ E si guarda SOLO cio' che il criterio produce — `stato <> 'DEBITO_ESTINTO'`.
--   Provato il 2026-09-09 togliendo il ramo POLICY_INERTE dalla vista: senza
--   quel filtro questo test restava VERDE, perche' il ramo del debito estinto
--   ripubblica il `criterio` leggendolo dal REGISTRO. Cioe' il presidio si
--   accontentava della parola scritta nel CSV invece della regola viva — la
--   forma esatta del verde per sottrazione, sul test che esiste per impedirlo.
SELECT is(
    (SELECT count(*)::int
       FROM (
           SELECT unnest(regexp_matches(
                      pg_get_constraintdef(c.oid),
                      '''([A-Z_]+)''::text', 'g')) AS criterio
             FROM pg_constraint c
            WHERE c.conrelid = 'dbops.rls_perimetro_debito'::regclass
              AND c.conname  = 'chk_rls_perimetro_debito_criterio'
       ) v
      WHERE NOT EXISTS (SELECT 1 FROM dbops.vw_rls_perimetro_scoperto w
                         WHERE w.criterio = v.criterio
                           AND w.stato   <> 'DEBITO_ESTINTO')),
    0,
    '3. ogni criterio ammesso dal CHECK del registro e'' un ramo vivo della vista'
);

-- ============================================================
-- 4..8. I cinque casi costruiti, uno per proprieta' e una tabella per caso
-- ============================================================
SELECT is(
    (SELECT v.stato FROM dbops.vw_rls_perimetro_scoperto v
      WHERE v.schema_tabella = 'dbops' AND v.nome_tabella = 'pgtap_rls_figlia'),
    'NON_DICHIARATO',
    '4. una figlia nuova di una tabella protetta esce NON_DICHIARATO: il flag e'' un gesto, non l''impostazione di fabbrica'
);

SELECT is_empty(
    $$SELECT nome_tabella FROM dbops.vw_rls_perimetro_scoperto
       WHERE schema_tabella = 'dbops'
         AND nome_tabella   = 'pgtap_rls_figlia_armata'$$,
    '5. armata davvero (RLS accesa piu'' policy) la stessa figlia esce dal perimetro'
);

SELECT is_empty(
    $$SELECT nome_tabella FROM dbops.vw_rls_perimetro_scoperto
       WHERE schema_tabella = 'dbops' AND nome_tabella = 'pgtap_rls_innocua'$$,
    '6. e NON prende una tabella la cui parentela non e'' protetta: il criterio non e'' «ogni tabella vuole una policy»'
);

SELECT is(
    (SELECT v.criterio || ' ' || v.stato FROM dbops.vw_rls_perimetro_scoperto v
      WHERE v.schema_tabella = 'dbops'
        AND v.nome_tabella   = 'pgtap_rls_policy_inerte'),
    'POLICY_INERTE NON_DICHIARATO',
    '7. una policy con la row level security spenta esce come POLICY_INERTE anche senza nessun padre protetto'
);

SELECT is(
    (SELECT v.stato FROM dbops.vw_rls_perimetro_scoperto v
      WHERE v.schema_tabella = 'dbops'
        AND v.nome_tabella   = 'pgtap_rls_debito_pagato'),
    'DEBITO_ESTINTO',
    '8. una riga di registro che non ha piu'' il suo difetto esce DEBITO_ESTINTO: il registro non puo'' marcire nel verso permissivo'
);

DELETE FROM dbops.rls_perimetro_debito WHERE id = 999001;
DROP TABLE dbops.pgtap_rls_debito_pagato;
DROP TABLE dbops.pgtap_rls_policy_inerte;
DROP TABLE dbops.pgtap_rls_innocua;
DROP TABLE dbops.pgtap_rls_figlia_armata;
DROP TABLE dbops.pgtap_rls_figlia;

SELECT * FROM finish();

-- Il ROLLBACK e' la garanzia: comunque vada — verde, rosso, o morto a meta' —
-- questo file non lascia dietro di se' nessuna tabella, nessuna policy e
-- nessuna riga di registro di prova.
ROLLBACK;
