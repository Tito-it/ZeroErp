-- ------------------------------------------------------------
-- SPDX-License-Identifier: GPL-3.0-or-later
-- pgtap-runner: owner
-- pgtap-runner-motivo: ALTER TABLE … FORCE ROW LEVEL SECURITY, locale alla
--   transazione — e' il FORCE a rendere l'owner soggetto alle policy, perche'
--   `titodb` non e' superuser e non puo' fare SET ROLE. E la fixture costruisce
--   DUE aziende: un operatore dentro un perimetro non potrebbe crearle.
-- pgTAP test FUNZIONALE RLS — vendite.fatture_arrotondamenti_scope
--   Slice 20260911-01..03, brief brief-db-perimetro-emittente-righe-documento.md §11.18
--
-- Elenco test (plan 9):
--   1) struttura: la policy c'e'
--   2) struttura: e la RLS e' ACCESA
--   3) ⛔ la policy usa la rotta DIRETTA `_via_sr` su emittente_soggetto_ruolo_id
--   4) l'operatore A vede la PROPRIA configurazione
--   5) ⛔ e non quella di B — la riparazione
--   6) ⛔ SCRITTURA: A non puo' creare una configurazione per l'emittente di B
--   7) ⛔ senza veste applicativa: fail-closed
--   8) ⭐ A vede ESATTAMENTE una delle due configurazioni costruite
--   9) ⭐ `fn_get_arrotondamento_scope` non trova la configurazione altrui —
--      cioe' il perimetro vale anche per chi legge attraverso la funzione
--
-- ────────────────────────────────────────────────────────────────
-- 🔴 PERCHE' QUESTA SLICE ESISTE, ed e' una correzione di registro.
--   La riga del debito diceva *«va deciso se le sue righe seguano il perimetro
--   dell'emittente o restino leggibili come catalogo: domanda di modello, non
--   armamento»*. ⛔ Ma la tabella porta `emittente_soggetto_ruolo_id` **NOT
--   NULL**: una tabella che nomina il proprio emittente in una colonna
--   obbligatoria ha gia' risposto. Era lavoro pronto.
--   ⚠️ Terza riga di registro che sbaglia, e sempre nel verso che *ferma un
--   cantiere che poteva partire* (le prime due: §11.12).
--
-- ⭐ LA ROTTA E' DIRETTA, non un adattatore: questa tabella non e' il satellite
--   di una testata protetta, porta l'emittente da se' — come `vendite.commesse`,
--   di cui la policy e' la copia parola per parola.
--
-- ⭐ IL TEST 9 GUARDA DA DOVE SI LEGGE DAVVERO. Quattro funzioni usano questa
--   tabella e **nessuna e' `SECURITY DEFINER`**, quindi da oggi leggono sotto
--   RLS. `fn_get_arrotondamento_scope` e' quella che conta: pretende gia'
--   `p_emittente_soggetto_ruolo_id` obbligatorio e ci filtra sopra, quindi nel
--   percorso normale non cambia niente — ma se qualcuno le passasse l'emittente
--   di un'altra azienda, oggi troverebbe la riga e da domani no. E' il buco, ed
--   e' il solo caso in cui il comportamento cambia.
--
-- ⚠️ COSA QUESTO FILE NON PROVA. Che sia l'unica tabella scoperta con questa
--   forma: quello lo dice il criterio, in
--   `db/pgtap/rls/test-rls-perimetro-scoperto.sql`.
--
-- ⭐ PROVATO FACENDOLO FALLIRE (2026-09-11):
--
--   | Mutazione                                   | Chi se ne accorge |
--   | ------------------------------------------- | ----------------- |
--   | senza `ENABLE`                              | test 2 (e la scrittura del 6 passa) |
--   | `_via_efba(…, billing_account_id)` al posto della rotta diretta | test 3 |
--
--   ⚠️ La seconda la prende **solo** il test strutturale, ed e' istruttivo:
--   `_via_efba` sul billing account di B risponde comunque `false`, perche'
--   quel BA e' fuori dal perimetro di A. ⇒ Nel verso negativo la rotta
--   sbagliata *sembra funzionare* — e' il fail-closed per la ragione sbagliata,
--   gia' visto sulla slice `lotti` (§11.9). A separarle e' l'asse su cui
--   filtrano, e quello si legge solo dalla definizione della policy.
-- ------------------------------------------------------------

BEGIN;

SET CONSTRAINTS ALL IMMEDIATE;

SELECT plan(9);

-- ============================================================
-- Due mondi, una configurazione di arrotondamento a testa
-- ============================================================
CREATE TEMP TABLE _mondi AS
SELECT 'A' AS lato, * FROM dbops.fn_pgtap_crea_emittente_operatore()
UNION ALL
SELECT 'B' AS lato, * FROM dbops.fn_pgtap_crea_emittente_operatore();

-- ⚠️ La utility `BASE` non richiede PDP: con la prima a catalogo il billing
--   account non nascerebbe. Nominata per `codice_interno`, mai per id.
CREATE TEMP TABLE _catalogo AS
SELECT (SELECT u.id  FROM config.utilities u
         WHERE u.codice_interno = 'BASE' AND NOT u.richiede_pdp)      AS utility_id,
       (SELECT t.id  FROM config.tipi_doc_fiscale t ORDER BY t.id LIMIT 1) AS tipo_doc_fiscale_id,
       (SELECT v.id  FROM config.valute v WHERE v.codice = 'EUR')         AS valuta_id;

CREATE TEMP TABLE _ba AS
SELECT m.lato, m.soggetto_ruolo_id AS emittente_sr,
       (dbops.fn_pgtap_crea_cliente_ba('RLSARR-' || m.lato, c.utility_id,
                                       m.soggetto_ruolo_id)).*
  FROM _mondi m CROSS JOIN _catalogo c;

-- ⭐ `emittente_soggetto_ruolo_id` e' la colonna su cui la policy filtra: e'
--   quella dell'emittente del mondo, non quella del cliente.
CREATE TEMP TABLE _scope AS
WITH ins AS (
    INSERT INTO vendite.fatture_arrotondamenti_scope
        (billing_account_id, utility_id, tipo_doc_fiscale_id,
         emittente_soggetto_ruolo_id, valuta_id, saldo_arrotondamento)
    SELECT b.billing_account_id, c.utility_id, c.tipo_doc_fiscale_id,
           b.emittente_sr, c.valuta_id, 0.01
      FROM _ba b CROSS JOIN _catalogo c
    RETURNING id, billing_account_id, emittente_soggetto_ruolo_id
)
SELECT b.lato, i.id AS scope_id, i.billing_account_id, i.emittente_soggetto_ruolo_id
  FROM ins i JOIN _ba b ON b.billing_account_id = i.billing_account_id;

-- ============================================================
-- 1..3. La struttura
-- ============================================================
SELECT is(
    (SELECT count(*)::int FROM pg_policies
      WHERE schemaname = 'vendite' AND tablename = 'fatture_arrotondamenti_scope'),
    1,
    '1. vendite.fatture_arrotondamenti_scope ha la sua policy'
);

-- ⛔ Si asserisce `relrowsecurity`, non l'esistenza della policy: una policy
--   con la RLS spenta non e' una difesa.
SELECT ok(
    (SELECT c.relrowsecurity FROM pg_class c
       JOIN pg_namespace n ON n.oid = c.relnamespace
      WHERE n.nspname = 'vendite' AND c.relname = 'fatture_arrotondamenti_scope'),
    '2. e la ROW LEVEL SECURITY e'' accesa'
);

-- ⛔ La rotta DIRETTA, non un adattatore. Un `_via_efba` sulla chiave del
--   billing account compilerebbe e girerebbe, e filtrerebbe su un asse diverso
--   da quello che la tabella dichiara.
-- ⭐ Rev 2026-10-18 (D-3b-2 giro 1b, 20261018-33): la rotta si legge nel modo di
--   script.fn_resolve_emittente_fiscale_id, non piu' nel nome dell'adattatore.
SELECT ok(
    (SELECT position('fn_resolve_emittente_fiscale_id(''soggetto_ruolo''::text' IN p.qual) > 0
        AND position('emittente_soggetto_ruolo_id'  IN p.qual) > 0
       FROM pg_policies p
      WHERE p.schemaname = 'vendite'
        AND p.tablename  = 'fatture_arrotondamenti_scope'),
    '3. la policy usa la rotta diretta _via_sr su emittente_soggetto_ruolo_id'
);

-- ============================================================
-- Il perimetro, esercitato da dentro
-- ============================================================
ALTER TABLE vendite.fatture_arrotondamenti_scope FORCE ROW LEVEL SECURITY;

DO $perimetro$
DECLARE
    v_a record;
    v_b record;
    v_c record;
    v_n integer;
    v_saldo numeric;
BEGIN
    SELECT * INTO v_a FROM _scope WHERE lato = 'A';
    SELECT * INTO v_b FROM _scope WHERE lato = 'B';
    SELECT * INTO v_c FROM _catalogo;

    PERFORM script.fn_pgtap_set_contesto_operatore(
                (SELECT auth_user_id FROM _mondi WHERE lato = 'A'));

    SELECT count(*) INTO v_n FROM vendite.fatture_arrotondamenti_scope s
     WHERE s.id = v_a.scope_id;
    PERFORM set_config('pgtap.propria', v_n::text, true);

    SELECT count(*) INTO v_n FROM vendite.fatture_arrotondamenti_scope s
     WHERE s.id = v_b.scope_id;
    PERFORM set_config('pgtap.altrui', v_n::text, true);

    -- ⛔ SCRITTURA: una configurazione per l'emittente di B.
    BEGIN
        INSERT INTO vendite.fatture_arrotondamenti_scope
            (billing_account_id, utility_id, tipo_doc_fiscale_id,
             emittente_soggetto_ruolo_id, valuta_id, saldo_arrotondamento)
        VALUES (v_b.billing_account_id, v_c.utility_id, v_c.tipo_doc_fiscale_id,
                v_b.emittente_soggetto_ruolo_id, v_c.valuta_id, 0.05);
        PERFORM set_config('pgtap.scrittura', 'PASSATA', true);
    EXCEPTION WHEN insufficient_privilege OR check_violation OR raise_exception THEN
        PERFORM set_config('pgtap.scrittura', 'RIFIUTATA', true);
    END;

    -- ⭐ Il conteggio sul denominatore COSTRUITO da questo file: su dbdev
    --   esistono altre righe, e «tutte le righe della tabella» non direbbe piu'
    --   niente.
    SELECT count(*) INTO v_n
      FROM vendite.fatture_arrotondamenti_scope s
      JOIN _scope sc ON sc.scope_id = s.id;
    PERFORM set_config('pgtap.visibili', v_n::text, true);

    -- ⭐ E LA STESSA DOMANDA FATTA ALLA FUNZIONE, che e' il modo in cui
    --   l'applicazione legge davvero. Non e' SECURITY DEFINER, quindi da oggi
    --   guarda attraverso la policy.
    -- ⚠️ Sette parametri e ritorna un `numeric`: il saldo. Si asserisce che NON
    --   sia quello di B (0.01) — se lo fosse, il perimetro non varrebbe per chi
    --   legge dalla funzione, che e' il percorso vero.
    SELECT vendite.fn_get_arrotondamento_scope(
               v_b.billing_account_id, v_c.utility_id, v_c.tipo_doc_fiscale_id,
               v_b.emittente_soggetto_ruolo_id, v_c.valuta_id::integer, NULL, NULL)
      INTO v_saldo;
    PERFORM set_config('pgtap.fn_altrui', COALESCE(v_saldo::text, 'NIENTE'), true);

    -- ⛔ Nessuna veste: fail-closed.
    PERFORM set_config('app.ruolo_applicativo', '', true);
    SELECT count(*) INTO v_n FROM vendite.fatture_arrotondamenti_scope;
    PERFORM set_config('pgtap.senza_veste', v_n::text, true);
END
$perimetro$;

ALTER TABLE vendite.fatture_arrotondamenti_scope NO FORCE ROW LEVEL SECURITY;

SELECT isnt(current_setting('pgtap.propria', true), '0',
            '4. l''operatore A vede la PROPRIA configurazione di arrotondamento');

SELECT is(current_setting('pgtap.altrui', true), '0',
          '5. e non quella di B: la configurazione di fatturazione altrui non si legge piu''');

SELECT is(current_setting('pgtap.scrittura', true), 'RIFIUTATA',
          '6. ne'' puo'' crearne una per l''emittente di B (la WITH CHECK)');

SELECT is(current_setting('pgtap.senza_veste', true), '0',
          '7. senza veste applicativa non risponde niente: fail-closed');

SELECT is(current_setting('pgtap.visibili', true), '1',
          '8. delle DUE configurazioni costruite A ne vede esattamente una: la propria');

SELECT isnt(current_setting('pgtap.fn_altrui', true), '0.01',
            '9. e fn_get_arrotondamento_scope non restituisce il saldo di B: il perimetro vale anche per chi legge dalla funzione');

SELECT * FROM finish();

-- Il ROLLBACK e' la garanzia: comunque vada — verde, rosso, o morto a meta' —
-- questo file non lascia dietro di se' nessuna configurazione e nessuna azienda.
ROLLBACK;
