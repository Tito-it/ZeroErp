-- ------------------------------------------------------------
-- SPDX-License-Identifier: GPL-3.0-or-later
-- pgtap-runner: owner
-- pgtap-runner-motivo: ALTER TABLE … FORCE ROW LEVEL SECURITY, locale alla
--   transazione — e' il FORCE a rendere l'owner soggetto alle policy, perche'
--   `titodb` non e' superuser e non puo' fare SET ROLE. E la fixture costruisce
--   DUE aziende con i loro listini: un operatore dentro un perimetro non
--   potrebbe crearle.
-- pgTAP test FUNZIONALE RLS — la catena dei LISTINI
--   Slice 20260910-21..24, brief brief-db-perimetro-emittente-righe-documento.md §11.11
--
-- Elenco test (plan 10):
--   1) struttura: tutte e tre hanno la loro policy
--   2) struttura: e la RLS e' ACCESA su tutte e tre
--   3) ⛔ ogni policy usa l'adattatore della PROPRIA chiave
--   4) l'operatore A vede il prezzo del PROPRIO listino
--   5) ⛔ e non quello di B — la riparazione
--   6) ⛔ ne' l'aggancio categoria-listino di B
--   7) ⭐ ma il PROPRIO aggancio lo vede: il gemello positivo del 6
--   8) ⛔ SCRITTURA: A non puo' scrivere un prezzo nel listino di B
--   9) ⛔ senza veste applicativa: fail-closed su tutte e tre
--  10) ⭐ l'adattatore `_via_listino_versione` dice il vero nei due versi — ed
--      e' anche la copertura di `listini_righe_componenti`, che la fixture non
--      costruisce
--
-- ────────────────────────────────────────────────────────────────
-- ⛔ IL DIFETTO CHE QUESTO FILE CHIUDE, e qui il contenuto sono I PREZZI.
--   `vendite.listini` e `vendite.listini_versioni` sono protette; le righe di
--   listino no, e `zeroerp_app` ha su tutte SELECT, INSERT, UPDATE e DELETE.
--   Il perimetro si fermava alla versione: articolo, unita' di misura e
--   **prezzo** dei listini di ogni emittente passavano di li'.
--
-- ⭐ LA CATENA ERA GIA' MEZZA COSTRUITA, e questa slice aggiunge un anello:
--     listini ──(_via_sr)──> emittente          [gia' protetta]
--     listini_versioni ──(_via_listino)──>      [gia' protetta]
--     listini_righe / _componenti ──(_via_listino_versione)──>  [QUESTA slice]
--     categorie_clienti_listini ──(_via_listino)──>             [QUESTA slice]
--   ⚠️ L'ultima riga e' in `anagrafiche` ma e' un satellite di `vendite.listini`:
--   armare il listino e lasciare aperto chi lo aggancia sposterebbe solo il
--   punto da cui si legge.
--
-- ⛔ IL TEST 3 PRENDE IL REFUSO CHE NON FA RUMORE. Le due chiavi —
--   `listino_versione_id` e `listino_id` — sono entrambe `bigint`, e i due
--   adattatori hanno la stessa firma: scambiarli **non da' nessun errore**.
--   ⚠️ E nel verso NEGATIVO uno scambio sembra funzionare lo stesso (un id di
--   versione letto come id di listino non trova quasi mai un listino, quindi
--   fail-closed). A smascherarlo sono i versi POSITIVI — i test 4 e 7.
--
-- ⚠️ COSA LA FIXTURE NON COSTRUISCE, e perche' e' dichiarato.
--   `listini_righe_componenti` pretende una **distinta base**
--   (`catalogo.articoli_componenti`): 25 righe su sviluppo, **zero** su un
--   database ricostruito, perche' non ha nessun seed. Invece di fabbricare una
--   catena che non appartiene alla slice, il perimetro di quella tabella si
--   prova per **struttura** (test 1-3, stessa chiave e stesso adattatore della
--   riga) e interrogando l'adattatore (test 10). *Non serve una riga per
--   chiedere a una funzione se dice il vero.*
--   ⭐ Il resto viene tutto dal catalogo — `catalogo.articoli`,
--   `catalogo.unita_misura`, `config.utilities`, `config.listini_tipologie`,
--   `anagrafiche.categorie_clienti` hanno un CSV in `80_data`: la fixture si
--   costruisce anche su un database vergine.
-- ------------------------------------------------------------

BEGIN;

SET CONSTRAINTS ALL IMMEDIATE;

SELECT plan(10);

-- ============================================================
-- I due mondi, un listino a testa, con versione, riga e aggancio
-- ============================================================
CREATE TEMP TABLE _mondi AS
SELECT 'A' AS lato, * FROM dbops.fn_pgtap_crea_emittente_operatore()
UNION ALL
SELECT 'B' AS lato, * FROM dbops.fn_pgtap_crea_emittente_operatore();

-- ⛔ L'ARTICOLO SE LO COSTRUISCE, e non e' zelo: `catalogo/articoli.csv` e'
--   **vuoto** (sola intestazione). I 257 articoli del database di sviluppo sono
--   dati di macchina: su un database ricostruito da zero non ce n'e' nessuno, e
--   un test che ne cercasse uno sarebbe verde qui e senza materia in CI. E' la
--   stessa trappola di `anagrafiche.bank_branches`, un'altra tabella.
-- ⭐ `unita_misura`, `utilities`, `listini_tipologie` e `categorie_clienti`
--   vengono invece dai changelog: quelle si possono leggere.
-- ⚠️ E la tipologia NON si sceglie separatamente:
--   `trgfn_listini_righe_guard_tipologia` pretende
--   `articolo.listino_tipologia_id = listino.tipologia_id`, quindi si sceglie
--   UNA tipologia e la si da' a tutti e due — successo alla prima stesura, che
--   prendeva «il primo articolo» e «la prima tipologia» come se fossero
--   indipendenti.
CREATE TEMP TABLE _catalogo AS
WITH scelta AS (
    SELECT (SELECT u.id  FROM config.utilities u
             ORDER BY u.id LIMIT 1)                      AS utility_id,
           (SELECT t.id  FROM config.listini_tipologie t
             ORDER BY t.id LIMIT 1)                      AS tipologia_id,
           (SELECT um.id FROM catalogo.unita_misura um
             ORDER BY um.id LIMIT 1)                     AS uom_id,
           (SELECT cc.id FROM anagrafiche.categorie_clienti cc
             ORDER BY cc.id LIMIT 1)                     AS categoria_id
), art AS (
    INSERT INTO catalogo.articoli
        (codice, descrizione, uom_id, listino_tipologia_id)
    SELECT 'PGTAP-RLS-LST', 'Articolo pgTAP RLS listini', s.uom_id, s.tipologia_id
      FROM scelta s
    RETURNING id
)
SELECT s.utility_id, s.tipologia_id, s.uom_id, s.categoria_id,
       (SELECT id FROM art) AS articolo_id
  FROM scelta s;

CREATE TEMP TABLE _listini AS
WITH l AS (
    INSERT INTO vendite.listini
        (codice, descrizione, utility_id, tipologia_id, emittente_soggetto_ruolo_id)
    SELECT 'PGTAP-LST-' || m.lato || '-' || m.emittente_fiscale_id,
           'Listino pgTAP RLS ' || m.lato,
           (SELECT utility_id FROM _catalogo), (SELECT tipologia_id FROM _catalogo),
           m.soggetto_ruolo_id
      FROM _mondi m
    RETURNING id, emittente_soggetto_ruolo_id
)
SELECT m.lato, l.id AS listino_id, m.soggetto_ruolo_id, m.auth_user_id
  FROM l JOIN _mondi m ON m.soggetto_ruolo_id = l.emittente_soggetto_ruolo_id;

CREATE TEMP TABLE _versioni AS
WITH v AS (
    INSERT INTO vendite.listini_versioni (listino_id, codice_versione, valido_dal)
    SELECT l.listino_id, 'V1', script.fn_data_operativa() FROM _listini l
    RETURNING id, listino_id
)
SELECT l.lato, v.id AS versione_id, v.listino_id
  FROM v JOIN _listini l ON l.listino_id = v.listino_id;

-- Il prezzo: e' il dato che questa slice mette al riparo.
INSERT INTO vendite.listini_righe (listino_versione_id, articolo_id, uom_id, prezzo)
SELECT v.versione_id, c.articolo_id, c.uom_id, 42.0000000000
  FROM _versioni v CROSS JOIN _catalogo c;

-- L'aggancio categoria-listino, che vive in `anagrafiche` ma e' del listino.
INSERT INTO anagrafiche.categorie_clienti_listini
    (categoria_cliente_id, utility_id, emittente_soggetto_ruolo_id, listino_id, valido_dal)
SELECT c.categoria_id, c.utility_id, l.soggetto_ruolo_id, l.listino_id, script.fn_data_operativa()
  FROM _listini l CROSS JOIN _catalogo c;

-- ============================================================
-- 1..3. La struttura
-- ============================================================
SELECT is(
    (SELECT count(*)::int FROM pg_policies p
      WHERE (p.schemaname = 'vendite'
             AND p.tablename IN ('listini_righe', 'listini_righe_componenti'))
         OR (p.schemaname = 'anagrafiche'
             AND p.tablename = 'categorie_clienti_listini')),
    3,
    '1. tutte e tre le tabelle della catena listini hanno la loro policy'
);

-- ⛔ Si asserisce `relrowsecurity`, non l'esistenza della policy: una policy
--   con la RLS spenta non e' una difesa.
SELECT is(
    (SELECT count(*)::int FROM pg_class c
       JOIN pg_namespace n ON n.oid = c.relnamespace
      WHERE c.relrowsecurity
        AND ((n.nspname = 'vendite'
              AND c.relname IN ('listini_righe', 'listini_righe_componenti'))
          OR (n.nspname = 'anagrafiche' AND c.relname = 'categorie_clienti_listini'))),
    3,
    '2. e la ROW LEVEL SECURITY e'' accesa su tutte e tre'
);

-- ⛔ Le due chiavi sono entrambe bigint e i due adattatori hanno la stessa
--   firma: scambiarli compila, gira e filtra sul listino sbagliato.
-- ⭐ Rev 2026-10-18 (D-3b-2 giro 1b, 20261018-33): la rotta si legge nel modo di
--   script.fn_resolve_emittente_fiscale_id, non piu' nel nome dell'adattatore.
SELECT is_empty(
    $$WITH atteso (sch, tab, adattatore) AS (
          VALUES
            ('vendite','listini_righe',            'fn_resolve_emittente_fiscale_id(''listino_versione''::text'),
            ('vendite','listini_righe_componenti', 'fn_resolve_emittente_fiscale_id(''listino_versione''::text'),
            ('anagrafiche','categorie_clienti_listini', 'fn_resolve_emittente_fiscale_id(''listino''::text')
      )
      SELECT a.sch || '.' || a.tab
        FROM atteso a
        JOIN pg_policies p ON p.schemaname = a.sch AND p.tablename = a.tab
       WHERE position(a.adattatore IN p.qual)       = 0
          OR position(a.adattatore IN p.with_check) = 0$$,
    '3. ogni policy usa l''adattatore della propria chiave (versione vs listino)'
);

-- ============================================================
-- Il perimetro, esercitato da dentro
-- ============================================================
-- ⛔ TUTTE, compresa `listini_righe_componenti` che la fixture non popola:
--   senza il FORCE l'owner resta esente e il test 9 conta le righe VERE del
--   database di sviluppo. ⚠️ Su un database ricostruito quella tabella e' vuota
--   e il test sarebbe passato **per sottrazione** — cioe' proprio dove nessuno
--   guarda. E' lo stesso inciampo gia' fatto sulla slice `pratiche`.
ALTER TABLE vendite.listini                       FORCE ROW LEVEL SECURITY;
ALTER TABLE vendite.listini_versioni              FORCE ROW LEVEL SECURITY;
ALTER TABLE vendite.listini_righe                 FORCE ROW LEVEL SECURITY;
ALTER TABLE vendite.listini_righe_componenti      FORCE ROW LEVEL SECURITY;
ALTER TABLE anagrafiche.categorie_clienti_listini FORCE ROW LEVEL SECURITY;

DO $perimetro$
DECLARE
    v_a record;
    v_b record;
    v_n integer;
BEGIN
    SELECT l.*, v.versione_id INTO v_a
      FROM _listini l JOIN _versioni v ON v.listino_id = l.listino_id WHERE l.lato = 'A';
    SELECT l.*, v.versione_id INTO v_b
      FROM _listini l JOIN _versioni v ON v.listino_id = l.listino_id WHERE l.lato = 'B';

    PERFORM script.fn_pgtap_set_contesto_operatore(v_a.auth_user_id);

    -- ⭐ Il PROPRIO. E' il verso che smaschera un adattatore scambiato: nel
    --   verso negativo lo scambio sembra funzionare lo stesso.
    SELECT count(*) INTO v_n FROM vendite.listini_righe r
     WHERE r.listino_versione_id = v_a.versione_id;
    PERFORM set_config('pgtap.righe_a', v_n::text, true);

    SELECT count(*) INTO v_n FROM vendite.listini_righe r
     WHERE r.listino_versione_id = v_b.versione_id;
    PERFORM set_config('pgtap.righe_b', v_n::text, true);

    SELECT count(*) INTO v_n FROM anagrafiche.categorie_clienti_listini x
     WHERE x.listino_id = v_b.listino_id;
    PERFORM set_config('pgtap.aggancio_b', v_n::text, true);

    SELECT count(*) INTO v_n FROM anagrafiche.categorie_clienti_listini x
     WHERE x.listino_id = v_a.listino_id;
    PERFORM set_config('pgtap.aggancio_a', v_n::text, true);

    -- ⛔ SCRITTURA: un prezzo nel listino altrui.
    -- ⚠️ E QUI SI CATTURA ANCHE `raise_exception` (P0001), che negli altri
    --   file della famiglia non serviva. Il motivo e' un fatto, non una
    --   comodita': `vendite.trgfn_listini_righe_guard_tipologia` **non e'
    --   SECURITY DEFINER** e la sua query risale `listini_versioni -> listini`
    --   per confrontare le tipologie. Sotto RLS quella lettura torna ZERO righe,
    --   il `SELECT INTO` lascia le variabili NULL e il guard rifiuta **prima**
    --   della `WITH CHECK` — con un messaggio che parla d'altro: «articolo privo
    --   di listino_tipologia_id».
    --   ⭐ La scrittura e' rifiutata lo stesso, ed e' la proprieta' che questo
    --   test misura. Ma il *motivo* che l'operatore leggerebbe e' fuorviante:
    --   e' la trappola nota del guard che legge sotto row level security, e qui
    --   se ne registra una seconda occorrenza.
    BEGIN
        INSERT INTO vendite.listini_righe (listino_versione_id, articolo_id, uom_id, prezzo)
        SELECT v_b.versione_id, c.articolo_id, c.uom_id, 1.0000000000 FROM _catalogo c;
        PERFORM set_config('pgtap.scrittura', 'PASSATA', true);
    EXCEPTION WHEN insufficient_privilege OR check_violation OR raise_exception THEN
        PERFORM set_config('pgtap.scrittura', 'RIFIUTATA', true);
    END;

    -- ⭐ L'adattatore nei due versi: e' anche la copertura di
    --   listini_righe_componenti, che la fixture non costruisce.
    PERFORM set_config('pgtap.adattatore',
        CASE WHEN     script.fn_scope_ef_whitelist_via_listino_versione(v_a.auth_user_id, v_a.versione_id)
              AND NOT script.fn_scope_ef_whitelist_via_listino_versione(v_a.auth_user_id, v_b.versione_id)
             THEN 'CORRETTO' ELSE 'SBAGLIATO' END, true);

    -- ⛔ Nessuna veste: fail-closed su tutte e tre.
    PERFORM set_config('app.ruolo_applicativo', '', true);
    SELECT (SELECT count(*) FROM vendite.listini_righe)
         + (SELECT count(*) FROM vendite.listini_righe_componenti)
         + (SELECT count(*) FROM anagrafiche.categorie_clienti_listini)
      INTO v_n;
    PERFORM set_config('pgtap.senza_veste', v_n::text, true);
END
$perimetro$;

ALTER TABLE anagrafiche.categorie_clienti_listini NO FORCE ROW LEVEL SECURITY;
ALTER TABLE vendite.listini_righe_componenti      NO FORCE ROW LEVEL SECURITY;
ALTER TABLE vendite.listini_righe                 NO FORCE ROW LEVEL SECURITY;
ALTER TABLE vendite.listini_versioni              NO FORCE ROW LEVEL SECURITY;
ALTER TABLE vendite.listini                       NO FORCE ROW LEVEL SECURITY;

SELECT isnt(current_setting('pgtap.righe_a', true), '0',
            '4. l''operatore A vede il prezzo del PROPRIO listino');

SELECT is(current_setting('pgtap.righe_b', true), '0',
          '5. e non quello del listino di B: i prezzi altrui non si leggono piu''');

SELECT is(current_setting('pgtap.aggancio_b', true), '0',
          '6. ne'' l''aggancio categoria-listino di B');

SELECT isnt(current_setting('pgtap.aggancio_a', true), '0',
            '7. ma il PROPRIO aggancio lo vede: senza questo verso un adattatore scambiato passerebbe');

SELECT is(current_setting('pgtap.scrittura', true), 'RIFIUTATA',
          '8. e non puo'' scrivere un prezzo nel listino di B — oggi a rifiutare e'' il guard, non la WITH CHECK');

SELECT is(current_setting('pgtap.senza_veste', true), '0',
          '9. senza veste applicativa nessuna delle tre risponde: fail-closed');

SELECT is(current_setting('pgtap.adattatore', true), 'CORRETTO',
          '10. l''adattatore _via_listino_versione dice il vero: la propria versione si'', quella di B no');

SELECT * FROM finish();

-- Il ROLLBACK e' la garanzia: comunque vada — verde, rosso, o morto a meta' —
-- questo file non lascia dietro di se' nessun listino e nessuna azienda di prova.
ROLLBACK;
