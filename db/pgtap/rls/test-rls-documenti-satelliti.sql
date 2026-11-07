-- ------------------------------------------------------------
-- SPDX-License-Identifier: AGPL-3.0-or-later
-- pgtap-runner: owner
-- pgtap-runner-motivo: ALTER TABLE … FORCE ROW LEVEL SECURITY, locale alla
--   transazione — e' il FORCE a rendere l'owner soggetto alle policy, perche'
--   `titodb` non e' superuser e non puo' fare SET ROLE. E la fixture costruisce
--   DUE aziende con il loro template documentale: un operatore dentro un
--   perimetro non potrebbe crearle.
-- pgTAP test FUNZIONALE RLS — i DUE satelliti di documenti.documenti_generati
--   Slice 20260910-31..34, brief brief-db-perimetro-emittente-righe-documento.md §11.16
--   Sesta famiglia consegnata dal presidio dbops.vw_rls_perimetro_scoperto.
--
-- Elenco test (plan 13):
--   1) struttura: tutti e due hanno la loro policy
--   2) struttura: e la RLS e' ACCESA su tutti e due
--   3) ⛔ tutte e due le policy usano `_via_documento_generato` — contate, non
--      «nessuna sbagliata»
--   4) l'operatore A vede il PROPRIO file generato
--   5) ⛔ e non quello di B — la riparazione
--   6) A vede il PROPRIO evento di generazione
--   7) ⛔ e non quello di B
--   8) ⛔ SCRITTURA: A non puo' appendere un evento al documento di B
--   9) ⛔ SCRITTURA: ne' una riga di file al documento di B
--  10) ⛔ senza veste applicativa: fail-closed su tutti e due
--  11) ⭐ l'adattatore dice il vero nei due versi
--  12) ⭐ il satellite non e' piu' CHIUSO della propria testata: dove si vede il
--      documento si vede anche il suo file
--  13) ⭐ e A puo' scrivere nel PROPRIO — il gemello positivo degli 8 e 9,
--      senza il quale una policy di sola lettura li passerebbe entrambi
--
-- ────────────────────────────────────────────────────────────────
-- ⛔ IL DIFETTO CHE QUESTO FILE CHIUDE, e qui il contenuto e' IL FILE.
--   `documenti.documenti_generati` e' protetta; i due satelliti no, e
--   `zeroerp_app` ha su entrambi SELECT, INSERT, UPDATE e DELETE.
--   ⚠️ `documenti_generati_file` porta `storage_key`, `file_name`, `sha256` e
--   `mime_type`: non sono metadati sopra un documento, sono le **coordinate con
--   cui il documento si recupera**. `documenti_generati_eventi` e' il diario —
--   chi ha generato cosa, quando, con quale esito.
--
-- ⭐ LA RISALITA E' DI UN ANELLO SOLO, ed e' la piu' corta della famiglia:
--     documenti_generati ──(fn_scope_ef_whitelist)──> whitelist operatore
--     eventi / file ──(_via_documento_generato)──> la stessa canonica
--   ⛔ Non `_via_sr` e non `_via_efba`: questa testata nomina l'emittente per
--   **emittente fiscale**. Le tre hanno la stessa firma `(integer, bigint)`,
--   quindi scambiarle **compila e gira** — e confronta due numerazioni diverse,
--   cioe' risponde quasi sempre false. ⚠️ Un fail-closed per la ragione
--   sbagliata somiglia moltissimo a una difesa che funziona (lezione della
--   slice `lotti`, §11.9): a smascherarlo sono i test 4, 6 e 11, che sono i
--   versi POSITIVI.
--
-- ⛔ LE SCRITTURE SI PROVANO CON UN `INSERT`, E NON E' UN DETTAGLIO.
--   `documenti_generati_eventi` e' **append-only** per trigger
--   (`a10_block_update`, `a10_block_delete`) e `documenti_generati_file` ha
--   `a10_protect_file` sull'UPDATE. ⇒ Un test che provasse a modificare una
--   riga altrui sarebbe verde **per il guard**, non per la `WITH CHECK` — cioe'
--   verde senza aver esercitato la policy. I guard difendono l'IMMUTABILITA',
--   la policy difende il PERIMETRO: sono due domande, e questo file fa la
--   seconda.
--
-- ⭐ IL TEST 12 GUARDA IL VERSO CHE NESSUN ALTRO GUARDA. Il rischio di una
--   slice cosi' non e' «vedo troppo»: e' che un satellite risulti piu' CHIUSO
--   della propria testata, cioe' un pannello vuoto senza spiegazione (successo
--   davvero al §11.10). Qui non puo' capitare, perche' l'adattatore delega
--   alla stessa canonica della testata — e il test lo pretende invece di
--   lasciarlo scritto in prosa.
--
-- ⚠️ COSA LA FIXTURE DEVE COSTRUIRSI, e perche'.
--   `documenti.template_documenti` porta `emittente_fiscale_id` **NOT NULL**:
--   il template e' scoped per emittente, come i listini (§11.11). ⇒ Ogni mondo
--   ha il **suo** template e la sua versione, e non ci sono seed per quelle due
--   tabelle — sono dati di macchina.
--   ⭐ Vengono invece dai changelog, e si possono leggere:
--   `documenti.tipi_documento_output` (6 righe), `documenti.tipi_file_documento`
--   (2), `documenti.render_engine_documento` (1) e `config.sorgenti` (15).
--   ⚠️ E i quattro campi del documento devono essere COERENTI fra loro:
--   `trgfn_documenti_generati_check_coerenza` pretende che versione, tipo
--   output, sorgente ed emittente combacino con quelli del template.
--
-- ⚠️ COSA QUESTO FILE NON PROVA. Che i due siano TUTTI i satelliti: quello lo
--   dice il criterio, in `db/pgtap/rls/test-rls-perimetro-scoperto.sql`.
--
-- ⭐ PROVATO FACENDOLO FALLIRE, non solo passare (2026-09-10):
--
--   | Mutazione                                          | Chi se ne accorge  |
--   | -------------------------------------------------- | ------------------ |
--   | `_via_sr` al posto di `_via_documento_generato`     | test 3, **4**, 12  |
--   | `documenti_generati_file` senza `ENABLE`            | test 2, 5, 9, 10   |
--   | la policy del file RINOMINATA                       | test 3             |
--   | `FOR SELECT` invece di `FOR ALL`                    | test 3 e **13**    |
--   | `FOR ALL` con la `WITH CHECK` OMESSA                | test 3 soltanto    |
--
--   ⛔ La quarta e' la ragione per cui il test 13 esiste, e la prima stesura
--   non ce l'aveva: con una policy di sola lettura la RLS e' **deny-all in
--   scrittura**, quindi i test 8 e 9 restano VERDI — «l'INSERT altrui e'
--   rifiutato» e' vero anche quando sarebbe rifiutato pure il PROPRIO.
--   *Un fail-closed su tutto supera ogni prova negativa*: a distinguerlo e' solo
--   il verso positivo.
--   ⭐ La quinta invece **non e' un difetto**, ed e' il motivo per cui sta in
--   tabella: omettere la `WITH CHECK` su un `FOR ALL` non cambia comportamento,
--   perche' PostgreSQL riusa la `USING` (linee-guida-sql §10.6). Cambia solo la
--   forma — e a vederlo e' il test strutturale, che e' il posto giusto.
-- ------------------------------------------------------------

BEGIN;

SET CONSTRAINTS ALL IMMEDIATE;

SELECT plan(13);

-- ============================================================
-- I due mondi, un documento generato a testa, i due satelliti attorno
-- ============================================================
CREATE TEMP TABLE _mondi AS
SELECT 'A' AS lato, * FROM dbops.fn_pgtap_crea_emittente_operatore()
UNION ALL
SELECT 'B' AS lato, * FROM dbops.fn_pgtap_crea_emittente_operatore();

-- ⭐ Tutto da catalogo: queste quattro tabelle hanno un CSV in 80_data, quindi
--   la fixture si costruisce anche su un database vergine.
-- ⚠️ `ORDER BY` su ogni `LIMIT 1`: senza, si scommette su quale riga esce.
CREATE TEMP TABLE _catalogo AS
SELECT (SELECT t.id FROM documenti.tipi_documento_output t
         WHERE t.attivo ORDER BY t.id LIMIT 1)              AS tipo_output_id,
       (SELECT r.id FROM documenti.render_engine_documento r
         WHERE r.attivo ORDER BY r.id LIMIT 1)              AS render_engine_id,
       (SELECT f.id FROM documenti.tipi_file_documento f
         WHERE f.attivo ORDER BY f.id LIMIT 1)              AS file_tipo_id,
       (SELECT s.id FROM config.sorgenti s
         WHERE s.codice_interno = 'FATTURA' AND s.attivo)   AS sorgente_tipo_id;

-- ⛔ Il template e' SCOPED PER EMITTENTE (`emittente_fiscale_id` NOT NULL):
--   uno per mondo, non uno condiviso. E' la stessa forma dei listini (§11.11).
CREATE TEMP TABLE _template AS
WITH t AS (
    INSERT INTO documenti.template_documenti
        (tipo_documento_output_id, codice, codice_interno, descrizione,
         sorgente_tipo_id, context_builder_code, emittente_fiscale_id)
    SELECT c.tipo_output_id,
           ('PGTAP-TPL-' || m.lato || '-' || m.emittente_fiscale_id)::varchar,
           ('PGTAP_TPL_' || m.lato || '_' || m.emittente_fiscale_id)::varchar,
           'Template pgTAP RLS documenti ' || m.lato,
           c.sorgente_tipo_id, 'pgtap.builder'::varchar, m.emittente_fiscale_id
      FROM _mondi m CROSS JOIN _catalogo c
    RETURNING id, emittente_fiscale_id
)
SELECT m.lato, t.id AS template_id, m.emittente_fiscale_id, m.auth_user_id
  FROM t JOIN _mondi m ON m.emittente_fiscale_id = t.emittente_fiscale_id;

CREATE TEMP TABLE _versioni AS
WITH v AS (
    INSERT INTO documenti.template_documenti_versioni
        (template_documento_id, versione, titolo, html_template, render_engine_id,
         versione_contesto)
    SELECT t.template_id, 1, 'Versione pgTAP ' || t.lato,
           '<html>pgtap</html>', c.render_engine_id, 1
      FROM _template t CROSS JOIN _catalogo c
    RETURNING id, template_documento_id
)
SELECT t.lato, v.id AS versione_id, v.template_documento_id AS template_id
  FROM v JOIN _template t ON t.template_id = v.template_documento_id;

-- ⚠️ I quattro campi devono COMBACIARE con quelli del template: lo pretende
--   `trgfn_documenti_generati_check_coerenza` (versione -> template, tipo
--   output, sorgente, emittente). Un solo campo fuori posto e il documento non
--   nasce — con un errore che parla di coerenza, non di perimetro.
-- ⚠️ I tre hash sono `character varying(64)` con un CHECK sulla lunghezza:
--   `encode(sha256(...),'hex')` ne fa esattamente 64.
-- ⭐ La stampa e' di una FATTURA VERA del suo mondo: dal lotto D di
--   brief-db-sorgente-documento-e-riga il guard unico verifica che il documento
--   stampato esista, e la chiave di una fattura e' il suo id (sorgente_id). La
--   fattura la costruisce il builder dentro il contesto dell'operatore del mondo
--   (con un contesto aperto riusa la sua azienda), e la stampa nasce nello
--   stesso contesto: un mondo alla volta.
CREATE TEMP TABLE _documenti
    (lato text, documento_id bigint, emittente_fiscale_id bigint, auth_user_id integer);

DO $stampe$
DECLARE
    v_t       record;
    v_fattura vendite.fatture.id%TYPE;
BEGIN
    FOR v_t IN SELECT * FROM _template ORDER BY lato LOOP
        PERFORM script.fn_pgtap_set_contesto_operatore(v_t.auth_user_id);

        SELECT f.fattura_id INTO v_fattura
          FROM dbops.fn_pgtap_crea_fattura('dg satelliti ' || v_t.lato) f;

        WITH d AS (
            INSERT INTO documenti.documenti_generati
                (tipo_documento_output_id, template_documento_id, template_versione_id,
                 sorgente_tipo_id, sorgente_id, progressivo_sorgente,
                 titolo, nome_file, context_json,
                 context_hash, template_hash, pdf_hash, emittente_fiscale_id)
            SELECT c.tipo_output_id, v_t.template_id, v.versione_id,
                   c.sorgente_tipo_id, v_fattura, 1,
                   'Documento pgTAP RLS ' || v_t.lato,
                   'pgtap-rls-' || v_t.lato || '.pdf',
                   -- _meta.context_version = versione_contesto della versione: lo
                   --   pretende il guard della forma (20260930-20).
                   jsonb_build_object('lato', v_t.lato,
                                      '_meta', jsonb_build_object('context_version', 1)),
                   encode(sha256(('ctx'  || v_t.lato)::bytea), 'hex')::varchar,
                   encode(sha256(('tpl'  || v_t.lato)::bytea), 'hex')::varchar,
                   encode(sha256(('pdf'  || v_t.lato)::bytea), 'hex')::varchar,
                   v_t.emittente_fiscale_id
              FROM _versioni v
              CROSS JOIN _catalogo c
             WHERE v.template_id = v_t.template_id
            RETURNING id
        )
        INSERT INTO _documenti
        SELECT v_t.lato, d.id, v_t.emittente_fiscale_id, v_t.auth_user_id FROM d;
    END LOOP;
END
$stampe$;

-- Il diario: chi ha generato cosa, quando, con quale esito.
INSERT INTO documenti.documenti_generati_eventi
    (documento_generato_id, evento_tipo, evento_at, esito, messaggio)
SELECT d.documento_id, 'GENERATO', now(), 'OK', 'Evento pgTAP RLS ' || d.lato
  FROM _documenti d;

-- Il file: e' il dato che questa slice mette al riparo.
INSERT INTO documenti.documenti_generati_file
    (documento_generato_id, file_tipo_id, mime_type, file_name,
     file_size_bytes, storage_key, sha256, ordinamento)
SELECT d.documento_id, c.file_tipo_id, 'application/pdf',
       'pgtap-rls-' || d.lato || '.pdf', 1024,
       'pgtap/rls/' || d.lato || '/documento.pdf',
       encode(sha256(('file' || d.lato)::bytea), 'hex')::varchar, 1
  FROM _documenti d CROSS JOIN _catalogo c;

-- ============================================================
-- 1..3. La struttura
-- ============================================================
SELECT is(
    (SELECT count(DISTINCT p.tablename)::int FROM pg_policies p
      WHERE p.schemaname = 'documenti'
        AND p.tablename IN ('documenti_generati_eventi', 'documenti_generati_file')),
    2,
    '1. tutti e due i satelliti documentali hanno la loro policy'
);

-- ⛔ Si asserisce `relrowsecurity`, non l'esistenza della policy: una policy
--   con la RLS spenta non e' una difesa.
SELECT is(
    (SELECT count(*)::int FROM pg_class c
       JOIN pg_namespace n ON n.oid = c.relnamespace
      WHERE c.relrowsecurity
        AND n.nspname = 'documenti'
        AND c.relname IN ('documenti_generati_eventi', 'documenti_generati_file')),
    2,
    '2. e la ROW LEVEL SECURITY e'' accesa su tutti e due'
);

-- ⛔ Si conta quante sono CORRETTE, non quante sono sbagliate: un `is_empty`
--   sarebbe verde anche il giorno in cui una policy sparisse o cambiasse nome —
--   il join non troverebbe niente, e «nessuna riga cattiva» e' cio' che dice un
--   presidio che non guarda piu' niente. Il denominatore e' scritto: due.
-- ⭐ Rev 2026-10-18 (D-3b-2 ondata 2, 20261018-50): la rotta si legge nel modo di
--   script.fn_resolve_emittente_fiscale_id, non piu' nel nome dell'adattatore.
SELECT is(
    (SELECT count(*)::int
       FROM (VALUES ('documenti_generati_eventi'), ('documenti_generati_file'))
              AS a(tab)
       JOIN pg_policies p
         ON p.schemaname = 'documenti'
        AND p.tablename  = a.tab
        AND p.policyname LIKE '%\_ef\_whitelist'
      WHERE position('fn_resolve_emittente_fiscale_id(''documento_generato''::text' IN p.qual)       > 0
        AND position('fn_resolve_emittente_fiscale_id(''documento_generato''::text' IN p.with_check) > 0),
    2,
    '3. tutte e due le policy di veste operatore passano dal modo documento_generato del risolutore'
);

-- ============================================================
-- Il perimetro, esercitato da dentro
-- ============================================================
-- ⛔ Anche la TESTATA: l'adattatore la legge, e sotto `zeroerp_app` quella
--   lettura e' filtrata. Lasciarla esente misurerebbe un adattatore piu'
--   generoso di quello vero — e renderebbe muto il test 12.
ALTER TABLE documenti.documenti_generati        FORCE ROW LEVEL SECURITY;
ALTER TABLE documenti.documenti_generati_eventi FORCE ROW LEVEL SECURITY;
ALTER TABLE documenti.documenti_generati_file   FORCE ROW LEVEL SECURITY;

DO $perimetro$
DECLARE
    v_a record;
    v_b record;
    v_c record;
    v_n integer;
BEGIN
    SELECT * INTO v_a FROM _documenti WHERE lato = 'A';
    SELECT * INTO v_b FROM _documenti WHERE lato = 'B';
    SELECT * INTO v_c FROM _catalogo;

    PERFORM script.fn_pgtap_set_contesto_operatore(v_a.auth_user_id);

    -- ⭐ I versi POSITIVI: sono quelli che smascherano un adattatore scambiato,
    --   perche' nel verso negativo lo scambio sembra funzionare lo stesso.
    SELECT count(*) INTO v_n FROM documenti.documenti_generati_file f
     WHERE f.documento_generato_id = v_a.documento_id;
    PERFORM set_config('pgtap.file_a', v_n::text, true);

    SELECT count(*) INTO v_n FROM documenti.documenti_generati_file f
     WHERE f.documento_generato_id = v_b.documento_id;
    PERFORM set_config('pgtap.file_b', v_n::text, true);

    SELECT count(*) INTO v_n FROM documenti.documenti_generati_eventi e
     WHERE e.documento_generato_id = v_a.documento_id;
    PERFORM set_config('pgtap.ev_a', v_n::text, true);

    SELECT count(*) INTO v_n FROM documenti.documenti_generati_eventi e
     WHERE e.documento_generato_id = v_b.documento_id;
    PERFORM set_config('pgtap.ev_b', v_n::text, true);

    -- ⛔ SCRITTURA: un evento sul documento altrui.
    -- ⚠️ Un INSERT, non un UPDATE: la tabella e' append-only per trigger, e un
    --   update sarebbe rifiutato dal guard invece che dalla WITH CHECK — verde
    --   senza aver esercitato la policy.
    BEGIN
        INSERT INTO documenti.documenti_generati_eventi
            (documento_generato_id, evento_tipo, evento_at, esito, messaggio)
        VALUES (v_b.documento_id, 'SCARICATO', now(), 'OK', 'Intrusione pgTAP');
        PERFORM set_config('pgtap.scr_ev', 'PASSATA', true);
    EXCEPTION WHEN insufficient_privilege OR check_violation OR raise_exception THEN
        PERFORM set_config('pgtap.scr_ev', 'RIFIUTATA', true);
    END;

    -- ⛔ SCRITTURA: una riga di file sul documento altrui — cioe' appendere le
    --   coordinate di uno storage al documento di un'altra azienda.
    BEGIN
        INSERT INTO documenti.documenti_generati_file
            (documento_generato_id, file_tipo_id, mime_type, file_name,
             file_size_bytes, storage_key, sha256, ordinamento)
        VALUES (v_b.documento_id, v_c.file_tipo_id, 'application/pdf',
                'intrusione.pdf', 1, 'pgtap/rls/intrusione.pdf',
                encode(sha256('intrusione'::bytea), 'hex')::varchar, 9);
        PERFORM set_config('pgtap.scr_file', 'PASSATA', true);
    EXCEPTION WHEN insufficient_privilege OR check_violation OR raise_exception THEN
        PERFORM set_config('pgtap.scr_file', 'RIFIUTATA', true);
    END;

    -- ⭐ IL GEMELLO POSITIVO DELLA SCRITTURA, e senza di lui i test 8 e 9 sono
    --   verdi per la ragione sbagliata. Trovato mutando la policy da `FOR ALL`
    --   a `FOR SELECT`: senza `WITH CHECK` la RLS e' **deny-all in scrittura**,
    --   quindi «l'INSERT altrui e' rifiutato» resta vero — ma sarebbe rifiutato
    --   anche il PROPRIO, cioe' il satellite piu' chiuso della testata.
    --   *Un fail-closed su tutto supera ogni prova negativa.*
    BEGIN
        INSERT INTO documenti.documenti_generati_eventi
            (documento_generato_id, evento_tipo, evento_at, esito, messaggio)
        VALUES (v_a.documento_id, 'SCARICATO', now(), 'OK', 'Evento proprio pgTAP');
        PERFORM set_config('pgtap.scr_propria', 'PASSATA', true);
    EXCEPTION WHEN insufficient_privilege OR check_violation OR raise_exception THEN
        PERFORM set_config('pgtap.scr_propria', 'RIFIUTATA', true);
    END;

    -- ⭐ L'adattatore nei due versi.
    PERFORM set_config('pgtap.adattatore',
        CASE WHEN     script.fn_scope_ef_whitelist_via_documento_generato(
                          v_a.auth_user_id, v_a.documento_id)
              AND NOT script.fn_scope_ef_whitelist_via_documento_generato(
                          v_a.auth_user_id, v_b.documento_id)
             THEN 'CORRETTO' ELSE 'SBAGLIATO' END, true);

    -- ⭐ Nessun satellite PIU' CHIUSO della propria testata: si contano i
    --   documenti visibili che NON mostrano il proprio file. Deve essere zero.
    --   ⚠️ Il denominatore e' la testata, non il satellite: misurarlo
    --   attraverso il filtro che si sta verificando lo renderebbe muto.
    SELECT count(*) INTO v_n
      FROM documenti.documenti_generati dg
     WHERE dg.id IN (v_a.documento_id, v_b.documento_id)
       AND NOT EXISTS (SELECT 1 FROM documenti.documenti_generati_file f
                        WHERE f.documento_generato_id = dg.id);
    PERFORM set_config('pgtap.orfani', v_n::text, true);

    -- ⛔ Nessuna veste: fail-closed su tutti e due.
    PERFORM set_config('app.ruolo_applicativo', '', true);
    SELECT (SELECT count(*) FROM documenti.documenti_generati_eventi)
         + (SELECT count(*) FROM documenti.documenti_generati_file)
      INTO v_n;
    PERFORM set_config('pgtap.senza_veste', v_n::text, true);
END
$perimetro$;

ALTER TABLE documenti.documenti_generati_file   NO FORCE ROW LEVEL SECURITY;
ALTER TABLE documenti.documenti_generati_eventi NO FORCE ROW LEVEL SECURITY;
ALTER TABLE documenti.documenti_generati        NO FORCE ROW LEVEL SECURITY;

SELECT isnt(current_setting('pgtap.file_a', true), '0',
            '4. l''operatore A vede il PROPRIO file generato');

SELECT is(current_setting('pgtap.file_b', true), '0',
          '5. e non quello di B: le coordinate del PDF altrui non si leggono piu''');

SELECT isnt(current_setting('pgtap.ev_a', true), '0',
            '6. A vede il PROPRIO evento di generazione');

SELECT is(current_setting('pgtap.ev_b', true), '0',
          '7. e non quello di B: il diario di generazione altrui non si legge');

SELECT is(current_setting('pgtap.scr_ev', true), 'RIFIUTATA',
          '8. e non puo'' appendere un evento al documento di B — un INSERT, che i guard di immutabilita'' lasciano passare');

SELECT is(current_setting('pgtap.scr_file', true), 'RIFIUTATA',
          '9. ne'' una riga di file, cioe'' le coordinate di uno storage sul documento di B');

SELECT is(current_setting('pgtap.senza_veste', true), '0',
          '10. senza veste applicativa nessuno dei due risponde: fail-closed');

SELECT is(current_setting('pgtap.adattatore', true), 'CORRETTO',
          '11. l''adattatore _via_documento_generato dice il vero: il proprio documento si'', quello di B no');

SELECT is(current_setting('pgtap.orfani', true), '0',
          '12. nessun documento visibile ha il file nascosto: il satellite non e'' piu'' chiuso della testata');

SELECT is(current_setting('pgtap.scr_propria', true), 'PASSATA',
          '13. ma nel PROPRIO documento A scrive: senza questo verso una policy FOR SELECT passerebbe i test 8 e 9');

SELECT * FROM finish();

-- Il ROLLBACK e' la garanzia: comunque vada — verde, rosso, o morto a meta' —
-- questo file non lascia dietro di se' nessun documento e nessuna azienda di prova.
ROLLBACK;
