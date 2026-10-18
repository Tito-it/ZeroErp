-- ------------------------------------------------------------
-- SPDX-License-Identifier: GPL-3.0-or-later
-- pgtap-runner: owner
-- pgtap-runner-motivo: ALTER TABLE … FORCE ROW LEVEL SECURITY, locale alla
--   transazione — e' il FORCE a rendere l'owner soggetto alle policy, perche'
--   `titodb` non e' superuser e non puo' fare SET ROLE. E la fixture costruisce
--   DUE aziende con i loro clienti e un'identita' di shop: un operatore dentro
--   un perimetro non potrebbe crearle.
-- pgTAP test FUNZIONALE RLS — anagrafiche.clienti
--   Slice 20260910-38..42, brief brief-db-perimetro-emittente-righe-documento.md §11.17
--   Settima famiglia consegnata dal presidio dbops.vw_rls_perimetro_scoperto.
--
-- Elenco test (plan 13):
--   1) struttura: le TRE policy ci sono — una per veste della testata
--   2) struttura: e la RLS e' ACCESA
--   3) ⛔ la policy shop usa `fn_scope_shop_via_ba`, non la sola proprieta'
--   4) `anagrafiche.vw_pdp` ha security_invoker: la porta di servizio e' chiusa
--   5) OPERATORE: A vede il PROPRIO cliente
--   6) ⛔ e non quello di B
--   7) ⛔ SCRITTURA: A non puo' creare una scheda sul billing account di B
--   8) SHOP: il cliente dello shop vede il proprio, su BA nato dal canale SHOP
--   9) ⛔⭐ e NON vede il proprio su BA nato da ADMIN — la condizione che si
--      sarebbe persa ricopiando la sola proprieta'
--  10) ⛔ ne' il cliente di un ALTRO proprietario
--  11) ⛔ senza veste applicativa: fail-closed
--  12) ⭐ l'adattatore `fn_scope_shop_via_ba` dice il vero nei due versi
--  13) ⭐ delle TRE schede costruite, l'operatore A ne vede esattamente due
--
-- ────────────────────────────────────────────────────────────────
-- ⛔ IL DIFETTO CHE QUESTO FILE CHIUDE.
--   Un cliente e' una faccia del proprio billing account e ne eredita il
--   perimetro. `anagrafiche.billing_account` e' protetta; `anagrafiche.clienti`
--   no, e `zeroerp_app` ci ha SELECT, INSERT, UPDATE e DELETE. ⇒ Ragione
--   sociale, stato, modalita' e termini di pagamento dei clienti di OGNI
--   emittente erano leggibili da qualunque operatore.
--
-- ⭐ TRE POLICY PER QUATTRO POLICY DI TESTATA, ed e' voluto. La regola e' «il
--   satellite rispecchia tutte le VESTI», non «ricopia tutte le policy». La
--   quarta della testata e' un `FOR INSERT` gate-only che esiste perche' il
--   mapping efba nasce da un trigger AFTER INSERT — su `clienti` il billing
--   account esiste gia', quindi la `WITH CHECK` della `FOR ALL` e' valutabile
--   fin dall'INSERT, e copiare quella policy lascerebbe creare schede fuori
--   perimetro. Lo presidia il test 7.
--
-- ⛔⛔ IL CUORE DI QUESTA SLICE E' IL TEST 9, e il resto gli fa da contorno.
--   La testata concede allo SHOP_CUSTOMER **due** condizioni insieme:
--       canale_origine = 'SHOP'   AND   proprieta' dell'identita'
--   La prima si legge da una colonna che sta **sul billing account**, e
--   `clienti` non ce l'ha. Ricopiare la sola proprieta' avrebbe reso il
--   satellite PIU' PERMISSIVO della propria testata — la trappola gia'
--   incontrata su `ordini` al passo 2.
--   ⇒ La fixture costruisce apposta **due clienti dello stesso proprietario**,
--   uno su un BA nato da SHOP e uno su un BA nato da ADMIN. Con l'adattatore
--   giusto se ne vede uno; con la sola proprieta' se ne vedrebbero due.
--   ⚠️ E il verso positivo (test 8) e' altrettanto necessario: senza, una
--   policy che chiudesse TUTTO passerebbe il 9 e il 10 senza fatica.
--
-- ⭐ PROVATO FACENDOLO FALLIRE, non solo passare (2026-09-10):
--
--   | Mutazione                                              | Chi se ne accorge |
--   | ------------------------------------------------------ | ----------------- |
--   | `fn_scope_ba_ownership` al posto di `fn_scope_shop_via_ba` | test 3 e **9**  |
--   | `clienti` senza `ENABLE`                               | test 2            |
--   | `vw_pdp` senza `security_invoker`                      | test 4            |
--   | la policy `INSERT` gate-only della testata RISPECCHIATA | test 1            |
--
--   ⛔ La prima e' il difetto che questa slice esiste per evitare, e il test 9
--   e' l'unico comportamentale che la vede: con la sola proprieta' il cliente
--   dello shop vedrebbe **due** schede invece di una.
--   ⚠️ E una mutazione va guardata in cio' che PRODUCE: la prima stesura di
--   quel replace non matchava per un'indentazione, quindi «nessun test cade»
--   voleva dire «non ho mutato niente». Si verifica il diff, poi si legge
--   l'esito.
--
-- ⚠️ COSA QUESTO FILE NON PROVA. Che `clienti` sia l'unica figlia scoperta di
--   `billing_account`: quello lo dice il criterio, in
--   `db/pgtap/rls/test-rls-perimetro-scoperto.sql`. E non prova niente su
--   `anagrafiche.pdp`, che entra nel perimetro proprio armando questa tabella
--   ed e' dichiarata nel registro come domanda di modello (chiavi nullable nei
--   due versi).
-- ------------------------------------------------------------

BEGIN;

SET CONSTRAINTS ALL IMMEDIATE;

SELECT plan(13);

-- ============================================================
-- I due mondi, e nel primo DUE clienti che differiscono solo per il canale
-- ============================================================
CREATE TEMP TABLE _mondi AS
SELECT 'A' AS lato, * FROM dbops.fn_pgtap_crea_emittente_operatore()
UNION ALL
SELECT 'B' AS lato, * FROM dbops.fn_pgtap_crea_emittente_operatore();

-- ⚠️ `fn_pgtap_crea_cliente_ba` costruisce l'istanza, il BILLING ACCOUNT e il
--   legame con l'emittente — **non** la scheda cliente. Le schede le crea
--   questo file, piu' sotto.
-- ⛔ La utility si SCEGLIE, e non e' un dettaglio: con la prima a catalogo
--   (ENERGIA) scatta «PDP obbligatorio per utility 1 (richiede_pdp=true)» e la
--   scheda cliente non nasce. Si usa `BASE`, che non lo richiede — nominata per
--   `codice_interno` e non per id, che e' un numero di seed.
CREATE TEMP TABLE _catalogo AS
SELECT (SELECT u.id FROM config.utilities u
         WHERE u.codice_interno = 'BASE' AND NOT u.richiede_pdp)  AS utility_id,
       (SELECT sc.id FROM config.stati_cliente sc
         WHERE sc.codice_interno = 'AT')                          AS stato_cliente_id;

-- ⚠️ Nascono con `canale_origine = 'ADMIN'`, che e' il default.
CREATE TEMP TABLE _ba AS
SELECT m.lato,
       (dbops.fn_pgtap_crea_cliente_ba('RLSCLI-' || m.lato, c.utility_id,
                                       m.soggetto_ruolo_id)).*
  FROM _mondi m CROSS JOIN _catalogo c;

-- ⛔ IL SECONDO BILLING ACCOUNT DEL MONDO A **NASCE** CON IL CANALE SHOP,
--   e non si puo' fare altrimenti: `canale_origine` e' **immutabile
--   post-INSERT** — c'e' un guard che rifiuta l'UPDATE con «la colonna
--   canale_origine e' immutabile post-INSERT».
-- ⚠️ E gli serve un'ISTANZA UTILITY sua: `uq_billing_instance_utility` e'
--   `UNIQUE (istanza_utility_id, utility_id)`, quindi due billing account non
--   possono condividere la stessa coppia.
-- ⭐ `fittizia = true` e vincoli DIFFERITI: e' la stessa forma che usa
--   `dbops.fn_pgtap_crea_cliente_ba`, perche'
--   `trgfn_istanze_utilities_require_utility_dichiarata` verifica al COMMIT che
--   l'istanza abbia un satellite — con i vincoli IMMEDIATE scatterebbe prima
--   che il billing account possa esistere.
SET CONSTRAINTS ALL DEFERRED;

CREATE TEMP TABLE _istanza_shop AS
WITH iu AS (
    INSERT INTO anagrafiche.istanze_utilities (codice, soggetto_id, fittizia)
    SELECT 'RLSCLI-SHOP-' || left(md5(random()::text), 8), b.soggetto_id, TRUE
      FROM _ba b WHERE b.lato = 'A'
    RETURNING id
)
SELECT id AS istanza_utility_id FROM iu;

-- ⭐ Stesso `soggetto_ruolo_id` del primo billing account del mondo A: e' cio'
--   che rende il test 9 una prova sul CANALE e non sul proprietario. Se
--   cambiassero tutti e due, quel test sarebbe verde anche con una policy che
--   guarda la sola proprieta' — cioe' proprio con il difetto che deve scoprire.
-- ⛔ Ma su un'ALTRA utility (rev 2026-10-14, brief-db-cliente-manuale-uno-per-
--   soggetto-e-utility): due clienti attivi dello stesso soggetto, utility e
--   azienda su istanze fittizie sono un doppione (E_CLIENTE_STESSA_CHIAVE). Al
--   test 9 serve lo stesso proprietario con due canali, non la stessa utility.
CREATE TEMP TABLE _ba_shop AS
WITH nuovo AS (
    INSERT INTO anagrafiche.billing_account
        (istanza_utility_id, soggetto_ruolo_id, utility_id, codice,
         categoria_cliente_id, valuta_id, canale_origine)
    SELECT i.istanza_utility_id, ba.soggetto_ruolo_id,
           (SELECT u.id FROM config.utilities u
             WHERE u.richiede_pdp IS FALSE AND u.id <> ba.utility_id
             ORDER BY u.id LIMIT 1),
           left(ba.codice, 40) || '-SHOP', ba.categoria_cliente_id, ba.valuta_id,
           'SHOP'::config.canale_origine
      FROM _istanza_shop i
      CROSS JOIN _ba b
      JOIN anagrafiche.billing_account ba ON ba.id = b.billing_account_id
     WHERE b.lato = 'A'
    RETURNING id, istanza_utility_id, soggetto_ruolo_id
)
SELECT * FROM nuovo;

-- ⚠️ La colonna e' `emittente_soggetto_ruolo_id`, non `emittente_fiscale_id`:
--   il legame emittente-BA e' per SOGGETTO-RUOLO. E' la stessa trappola per cui
--   `anagrafiche.fn_get_emittente_fiscale_id` restituisce un soggetto_ruolo_id.
INSERT INTO anagrafiche.emittenti_fiscali_billing_account
    (emittente_soggetto_ruolo_id, billing_account_id, is_default)
SELECT efba.emittente_soggetto_ruolo_id, s.id, false
  FROM _ba_shop s
  JOIN _ba b ON b.lato = 'A'
  JOIN anagrafiche.emittenti_fiscali_billing_account efba
    ON efba.billing_account_id = b.billing_account_id
ON CONFLICT DO NOTHING;

-- Le TRE schede cliente: A su canale ADMIN, A su canale SHOP, B.
CREATE TEMP TABLE _schede AS
WITH tutti AS (
    SELECT b.lato, 'ADMIN'::text AS canale, b.billing_account_id,
           b.soggetto_ruolo_id, b.istanza_utility_id
      FROM _ba b
    UNION ALL
    SELECT 'A', 'SHOP', s.id, s.soggetto_ruolo_id, s.istanza_utility_id
      FROM _ba_shop s
), ins AS (
    -- ⚠️ Con lo stato attivo serve la data: c'e' un guard che dice «per il
    --   cliente N non e' stata indicata una data apertura ma lo stato e'
    --   attivo». ⛔ La colonna pero' si chiama `data_attivazione`, non
    --   `data_apertura`: il messaggio nomina il concetto, non il campo.
    INSERT INTO anagrafiche.clienti
        (soggetto_ruolo_id, istanza_utility_id, stato_cliente_id,
         billing_account_id, data_attivazione)
    SELECT t.soggetto_ruolo_id, t.istanza_utility_id, c.stato_cliente_id,
           t.billing_account_id, script.fn_data_operativa()
      FROM tutti t CROSS JOIN _catalogo c
    RETURNING id, billing_account_id
)
SELECT t.lato, t.canale, t.billing_account_id, t.soggetto_ruolo_id,
       t.istanza_utility_id, i.id AS cliente_id
  FROM tutti t JOIN ins i ON i.billing_account_id = t.billing_account_id;

-- L'identita' di shop: stessa persona giuridica del cliente A, veste SHOP.
-- ⛔ Con un ACCESSO SUO, non quello dell'operatore di A: l'operatore di
--   fn_pgtap_crea_emittente_operatore e' un utente TECNICO (un processo), e
--   dall'area Accessi il guard trg_identita_digitali_a10_guard_natura_credenziale
--   rifiuta una veste di persona sulla credenziale di un processo. Il test non
--   ha mai avuto bisogno che fossero la stessa credenziale: il contesto shop si
--   da' con app.current_identita_id e app.current_user_id vuoto (test 8-11).
CREATE TEMP TABLE _shop AS
WITH u AS (
    INSERT INTO django.auth_user (username, password, is_active, is_staff, is_superuser,
                                  first_name, last_name, email, date_joined)
    VALUES ('_pgtap_rlscli_shop_' || substring(md5(clock_timestamp()::text) FROM 1 FOR 8),
            '!', true, false, false, '', '', '', now())
    RETURNING id
), i AS (
    SELECT anagrafiche.fn_crea_veste_portale(u.id, b.soggetto_ruolo_id, 'SHOP_CUSTOMER'::config.ruolo_applicativo, true) AS id FROM _ba_shop b CROSS JOIN u)
SELECT id AS identita_id FROM i;

-- ============================================================
-- 1..4. La struttura
-- ============================================================
SELECT is(
    (SELECT count(*)::int FROM pg_policies
      WHERE schemaname = 'anagrafiche' AND tablename = 'clienti'),
    3,
    '1. anagrafiche.clienti ha le tre policy, una per veste della testata'
);

-- ⛔ Si asserisce `relrowsecurity`, non l'esistenza della policy: una policy
--   con la RLS spenta non e' una difesa.
SELECT ok(
    (SELECT c.relrowsecurity FROM pg_class c
       JOIN pg_namespace n ON n.oid = c.relnamespace
      WHERE n.nspname = 'anagrafiche' AND c.relname = 'clienti'),
    '2. e la ROW LEVEL SECURITY e'' accesa'
);

-- ⛔ IL PRESIDIO DELLA CONDIZIONE CHE NON SI POTEVA COPIARE. Si pretende il
--   NOME dell'adattatore: `fn_scope_ba_ownership` da sola compilerebbe, girerebbe
--   e aprirebbe il satellite piu' della testata, in silenzio.
SELECT ok(
    (SELECT position('fn_scope_shop_via_ba(' IN p.qual) > 0
       FROM pg_policies p
      WHERE p.schemaname = 'anagrafiche' AND p.tablename = 'clienti'
        AND p.policyname = 'rls_clienti_shop'),
    '3. la policy shop usa fn_scope_shop_via_ba, non la sola proprieta'''
);

-- ⭐ La porta di servizio: senza security_invoker questa vista leggerebbe
--   `clienti` con gli occhi del proprietario, che la RLS non applica.
SELECT ok(
    EXISTS (SELECT 1 FROM pg_class c, unnest(c.reloptions) opt
             WHERE c.oid = 'anagrafiche.vw_pdp'::regclass
               AND opt IN ('security_invoker=on','security_invoker=true')),
    '4. anagrafiche.vw_pdp ha security_invoker: non aggira il perimetro'
);

-- ============================================================
-- Il perimetro, esercitato da dentro
-- ============================================================
-- ⚠️ I vincoli tornano IMMEDIATE prima dell'ALTER: con eventi trigger in
--   sospeso PostgreSQL rifiuta con «non e' possibile effettuare ALTER TABLE
--   perche' ha eventi trigger in sospeso».
-- ⭐ E fa anche una cosa utile: i guard differiti scattano ADESSO, quindi la
--   fixture viene validata prima che il test cominci a misurare. Se qualcosa
--   non torna si vede qui, non fra le asserzioni.
SET CONSTRAINTS ALL IMMEDIATE;

-- ⛔ IL `FORCE` VA SOLO SU `clienti`, E NON E' UNA SEMPLIFICAZIONE.
--   Mettendolo anche su `anagrafiche.billing_account` la corsa muore con
--   «limite di profondita' dello stack superato»: le policy della testata
--   chiamano funzioni che **rileggono la testata**, e con il FORCE quella
--   rilettura riapplica le policy — dentro la valutazione della policy di una
--   figlia il ciclo non si chiude piu'.
--   ⚠️ Provato il 2026-09-10: nessuna delle due vesti lo innesca DA SOLA (una
--   policy per volta, con il FORCE, gira); a innescarlo e' la combinazione.
--   ⭐ E non e' un difetto della slice: nel percorso vero — `zeroerp_app`, che
--   non e' owner — la RLS si applica senza bisogno del FORCE, e leggere
--   `billing_account` in veste shop risponde normalmente (verificato).
--   Il FORCE serve solo a questo file, perche' l'owner sarebbe altrimenti
--   esente.
ALTER TABLE anagrafiche.clienti FORCE ROW LEVEL SECURITY;

DO $perimetro$
DECLARE
    v_a       record;
    v_b       record;
    v_a_admin record;
    v_shop    bigint;
    v_n       integer;
BEGIN
    -- v_a: la scheda sul BA nato da SHOP — v_a_admin: quella sul BA nato da
    -- ADMIN, **stesso proprietario**. E' la coppia su cui poggia il test 9.
    SELECT * INTO v_a       FROM _schede WHERE lato = 'A' AND canale = 'SHOP';
    SELECT * INTO v_a_admin FROM _schede WHERE lato = 'A' AND canale = 'ADMIN';
    SELECT * INTO v_b       FROM _schede WHERE lato = 'B';
    SELECT identita_id INTO v_shop FROM _shop;

    -- ---------- veste OPERATORE ----------
    PERFORM script.fn_pgtap_set_contesto_operatore(
                (SELECT auth_user_id FROM _mondi WHERE lato = 'A'));

    SELECT count(*) INTO v_n FROM anagrafiche.clienti c
     WHERE c.billing_account_id = v_a.billing_account_id;
    PERFORM set_config('pgtap.op_proprio', v_n::text, true);

    SELECT count(*) INTO v_n FROM anagrafiche.clienti c
     WHERE c.billing_account_id = v_b.billing_account_id;
    PERFORM set_config('pgtap.op_altrui', v_n::text, true);

    -- ⛔ SCRITTURA: una scheda cliente sul billing account di B.
    --   E' il caso che la policy `FOR INSERT` gate-only della testata avrebbe
    --   lasciato passare, se l'avessimo ricopiata.
    BEGIN
        INSERT INTO anagrafiche.clienti
            (soggetto_ruolo_id, istanza_utility_id, stato_cliente_id,
             billing_account_id, data_attivazione)
        VALUES (v_b.soggetto_ruolo_id, v_b.istanza_utility_id,
                (SELECT stato_cliente_id FROM _catalogo),
                v_b.billing_account_id, script.fn_data_operativa());
        PERFORM set_config('pgtap.op_scrittura', 'PASSATA', true);
    EXCEPTION WHEN insufficient_privilege OR check_violation OR raise_exception THEN
        PERFORM set_config('pgtap.op_scrittura', 'RIFIUTATA', true);
    END;

    -- ---------- veste SHOP_CUSTOMER ----------
    PERFORM set_config('app.ruolo_applicativo',   'SHOP_CUSTOMER', true);
    PERFORM set_config('app.current_identita_id', v_shop::text,    true);
    PERFORM set_config('app.current_user_id',     '',              true);

    SELECT count(*) INTO v_n FROM anagrafiche.clienti c
     WHERE c.billing_account_id = v_a.billing_account_id;
    PERFORM set_config('pgtap.shop_proprio_shop', v_n::text, true);

    -- ⛔⭐ Stesso proprietario, canale ADMIN: deve restare invisibile.
    SELECT count(*) INTO v_n FROM anagrafiche.clienti c
     WHERE c.billing_account_id = v_a_admin.billing_account_id;
    PERFORM set_config('pgtap.shop_proprio_admin', v_n::text, true);

    SELECT count(*) INTO v_n FROM anagrafiche.clienti c
     WHERE c.billing_account_id = v_b.billing_account_id;
    PERFORM set_config('pgtap.shop_altrui', v_n::text, true);

    -- ⭐ IL CONTEGGIO GLOBALE, e non e' un doppione dei test 5 e 6: quelli
    --   guardano UN billing account per volta, quindi resterebbero verdi anche
    --   se la policy lasciasse passare schede che la fixture non ha nominato.
    --   Qui si conta quante delle TRE costruite l'operatore A vede davvero: le
    --   sue due, non tre.
    -- ⚠️ Denominatore noto e costruito da questo file, non «tutte le righe
    --   della tabella»: su dbdev ce ne sono altre, e il conto non direbbe piu'
    --   niente.
    PERFORM script.fn_pgtap_set_contesto_operatore(
                (SELECT auth_user_id FROM _mondi WHERE lato = 'A'));
    SELECT count(*) INTO v_n
      FROM anagrafiche.clienti c
      JOIN _schede sc ON sc.cliente_id = c.id;
    PERFORM set_config('pgtap.visibili_a', v_n::text, true);

    -- ⭐ L'adattatore nei due versi, interrogato direttamente.
    PERFORM set_config('pgtap.adattatore',
        CASE WHEN     script.fn_scope_shop_via_ba(v_shop, v_a.billing_account_id)
              AND NOT script.fn_scope_shop_via_ba(v_shop, v_a_admin.billing_account_id)
             THEN 'CORRETTO' ELSE 'SBAGLIATO' END, true);

    -- ⛔ Nessuna veste: fail-closed.
    PERFORM set_config('app.ruolo_applicativo', '', true);
    SELECT count(*) INTO v_n FROM anagrafiche.clienti;
    PERFORM set_config('pgtap.senza_veste', v_n::text, true);
END
$perimetro$;

ALTER TABLE anagrafiche.clienti NO FORCE ROW LEVEL SECURITY;

SELECT isnt(current_setting('pgtap.op_proprio', true), '0',
            '5. OPERATORE: A vede il PROPRIO cliente');

SELECT is(current_setting('pgtap.op_altrui', true), '0',
          '6. e non quello di B: le schede cliente altrui non si leggono piu''');

SELECT is(current_setting('pgtap.op_scrittura', true), 'RIFIUTATA',
          '7. ne'' puo'' creare una scheda sul billing account di B (la WITH CHECK della FOR ALL)');

SELECT isnt(current_setting('pgtap.shop_proprio_shop', true), '0',
            '8. SHOP: vede il proprio cliente sul BA nato dal canale SHOP');

SELECT is(current_setting('pgtap.shop_proprio_admin', true), '0',
          '9. ⭐ ma NON il proprio cliente sul BA nato da ADMIN: la seconda condizione della testata tiene');

SELECT is(current_setting('pgtap.shop_altrui', true), '0',
          '10. ne'' il cliente di un altro proprietario');

SELECT is(current_setting('pgtap.senza_veste', true), '0',
          '11. senza veste applicativa non risponde niente: fail-closed');

SELECT is(current_setting('pgtap.adattatore', true), 'CORRETTO',
          '12. fn_scope_shop_via_ba dice il vero: BA da shop si'', BA da admin no');

SELECT is(current_setting('pgtap.visibili_a', true), '2',
          '13. delle TRE schede costruite l''operatore A ne vede esattamente due: le proprie');

SELECT * FROM finish();

-- Il ROLLBACK e' la garanzia: comunque vada — verde, rosso, o morto a meta' —
-- questo file non lascia dietro di se' nessun cliente e nessuna azienda di prova.
ROLLBACK;
