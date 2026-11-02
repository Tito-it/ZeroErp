-- ------------------------------------------------------------
-- SPDX-License-Identifier: AGPL-3.0-or-later
-- pgtap-runner: owner
-- pgtap-runner-motivo: ALTER TABLE … FORCE ROW LEVEL SECURITY, locale alla
--   transazione — e' il FORCE a rendere l'owner soggetto alle policy, perche'
--   `titodb` non e' superuser e non puo' fare SET ROLE. E la fixture costruisce
--   DUE aziende con i loro canali di incasso: un operatore dentro un perimetro
--   non potrebbe crearle.
-- pgTAP test FUNZIONALE RLS — pagamenti.vendite_contabili_lotti
--   Slice 20260910-18..20, brief brief-db-perimetro-emittente-righe-documento.md §11.10
--
-- Elenco test (plan 11):
--   1) struttura: la policy c'e'
--   2) struttura: e la RLS e' ACCESA
--   3) ⭐ LA DECISIONE: risale da `contabile_id` e NON nomina `lotto_id`
--   4) e passa dall'adattatore gia' in servizio, non da uno nuovo
--   5) l'operatore A vede il manifesto della PROPRIA distinta
--   6) ⛔ e non quello di B — la riparazione
--   7) ⭐ il manifesto di una distinta INTERNA lo vede il SUO emittente (rev 2026-09-15, D3)
--   7-bis) ⭐ ...e non l'altro: la distinta interna non e' piu' di tutti (rev 2026-09-15, D3)
--   8) ⭐ L'INVARIANTE: il satellite non e' mai piu' CHIUSO della sua testata
--   9) ⛔ SCRITTURA: A non puo' appendere al manifesto della distinta di B
--  10) ⛔ senza veste applicativa: fail-closed
--
-- ────────────────────────────────────────────────────────────────
-- ⛔ QUESTA TABELLA ERA UNA DOMANDA, NON UN ARRETRATO.
--   Stava nel registro del debito con scritto *«due perimetri diversi sulla
--   stessa riga, va deciso quale comanda»*: ha due genitori protetti e tutti e
--   due `NOT NULL` — `pagamenti.vendite_contabili` (perimetro di incasso) e
--   `vendite.fatturazione_lotti` (whitelist emittente).
--   ⭐ Comanda la DISTINTA (decisione di Tid, 2026-09-10): la riga dice **quali
--   lotti una distinta raccoglie**, quindi e' il manifesto della distinta.
--
-- ⭐ IL TEST 7 E 8 SONO IL CUORE.
--   ⭐ REV 2026-09-15 (brief distinta-numerata-sul-registro, D3): LA DISTINTA
--   SA DI CHI E'. Fino a quel giorno l'adattatore
--   `fn_scope_ef_whitelist_via_contabile` risolveva l'emittente dal **canale
--   di incasso**, una distinta **interna** (senza canale) rispondeva `false` a
--   tutti mentre la sua TESTATA era visibile a tutti (`ente_incasso_id IS
--   NULL`), e questa policy portava un secondo ramo scritto a mano per non
--   essere piu' chiusa della testata. Ora la testata porta
--   `emittente_soggetto_ruolo_id` (NOT NULL, risolto in una sede sola), il
--   risolutore legge quella colonna (20260915-30), la policy della testata
--   passa di li' (20260915-31) e il secondo ramo e' sparito da questa policy
--   (20260915-32): una distinta interna e' del suo emittente, come il lotto da
--   cui nasce. Il test 7 ha CAMBIATO VERSO — A vede il manifesto della
--   propria interna, B no (7-bis) — e la fixture la crea DICHIARANDO di chi e'.
--   ⚠️ Il test 8 lo dice come invariante e non come caso: *niente che si veda
--     dalla testata resta nascosto nel manifesto*. Cosi' regge anche il giorno
--     in cui nasce un terzo tipo di distinta — ed e' rimasto identico.
--
-- ⚠️ LA FIXTURE COSTRUISCE TUTTA LA CATENA DEL CANALE, e non e' pigrizia:
--   `anagrafiche.bank_branches` **non ha un seed** in `80_data` (una riga sola
--   su sviluppo, creata a mano), quindi su un database ricostruito da zero e'
--   vuota — e `conti_bancari.bank_branch_id` e' `NOT NULL`. Un test che
--   cercasse una filiale esistente sarebbe verde qui e senza materia in CI.
--   ⭐ Il soggetto-ruolo della filiale non entra nella misura: il perimetro si
--   risolve dal LEGAME conto-soggetto, non dalla filiale. E' un bersaglio di FK.
-- ------------------------------------------------------------

BEGIN;

SET CONSTRAINTS ALL IMMEDIATE;

SELECT plan(11);

-- ============================================================
-- I due mondi, con il loro canale di incasso
-- ============================================================
CREATE TEMP TABLE _mondi AS
SELECT 'A' AS lato, * FROM dbops.fn_pgtap_crea_emittente_operatore()
UNION ALL
SELECT 'B' AS lato, * FROM dbops.fn_pgtap_crea_emittente_operatore();

CREATE TEMP TABLE _catalogo AS
SELECT (SELECT c.id FROM pagamenti.centri_riscossione c
         WHERE c.attivo IS TRUE AND c.codice = 'BANCA'
         ORDER BY c.id LIMIT 1)                                  AS centro_banca,
       (SELECT c.id FROM pagamenti.centri_riscossione c
         WHERE c.attivo IS TRUE AND c.is_fondo_fattura IS TRUE
         ORDER BY c.id LIMIT 1)                                  AS centro_fondo,
       (SELECT s.id FROM pagamenti.vendite_contabili_stati s
         WHERE s.codice_interno = 'BOZZA' ORDER BY s.id LIMIT 1) AS stato_bozza,
       (SELECT t.id FROM config.tipi_doc_fiscale t
         WHERE t.attivo ORDER BY t.id LIMIT 1)                   AS tipo_doc;

-- La filiale: bersaglio di FK per il conto, niente di piu'.
-- ⛔ Ma il suo soggetto-ruolo NON puo' essere quello dell'emittente:
--   `trgfn_bank_guard_ruolo_bank_branches` pretende il ruolo **`BANK_B`** e
--   rifiuta il resto — successo alla prima stesura. ⭐ E il rifiuto e' giusto:
--   una filiale e' una banca, non l'azienda che ci tiene il conto. Si costruisce
--   una banca vera con le fixture condivise.
CREATE TEMP TABLE _banche AS
SELECT m.lato,
       dbops.fn_pgtap_crea_soggetto_ruolo(
           dbops.fn_pgtap_crea_soggetto_pg('Banca pgTAP manifesto ' || m.lato),
           'BANK_B') AS banca_sr_id
  FROM _mondi m;

CREATE TEMP TABLE _filiali AS
WITH b AS (
    INSERT INTO anagrafiche.bank_branches
        (soggetto_ruolo_id, bank_code, branch_code, name)
    SELECT bb.banca_sr_id, 'PGTAP', 'CL' || bb.banca_sr_id,
           'Filiale pgTAP ' || bb.lato
      FROM _banche bb
    RETURNING id, soggetto_ruolo_id
)
SELECT bb.lato, b.id AS branch_id
  FROM b JOIN _banche bb ON bb.banca_sr_id = b.soggetto_ruolo_id;

-- ⭐ Il conto e il suo LEGAME: e' da qui che il perimetro risale all'emittente.
CREATE TEMP TABLE _legami AS
WITH c AS (
    INSERT INTO anagrafiche.conti_bancari (iban, bank_branch_id)
    SELECT 'IT00PGTAPCTBLOTTI' || lpad(f.branch_id::text, 12, '0'), f.branch_id
      FROM _filiali f
    RETURNING id, bank_branch_id
), l AS (
    INSERT INTO anagrafiche.soggetti_ruoli_conti_bancari
        (soggetto_ruolo_id, conto_bancario_id, uso)
    SELECT m.soggetto_ruolo_id, c.id, 'INCASSO'
      FROM c JOIN _filiali f ON f.branch_id = c.bank_branch_id
             JOIN _mondi   m ON m.lato = f.lato
    RETURNING id, soggetto_ruolo_id
)
SELECT m.lato, l.id AS legame_id FROM l JOIN _mondi m ON m.soggetto_ruolo_id = l.soggetto_ruolo_id;

-- ⛔ I lotti si costruiscono PRIMA di entrare nei panni di qualcuno.
--   `vendite.fatturazione_lotti` ha un guard di scrittura sullo scope
--   emittente (`trgfn_guard_emittente_scope`), che e' un TRIGGER e scatta anche
--   per l'owner: creare il lotto di A mentre il contesto e' quello di B viene
--   rifiutato — successo alla prima stesura, dopo il giro delle distinte.
-- Un lotto per lato, e i manifesti.
CREATE TEMP TABLE _lotti AS
WITH l AS (
    INSERT INTO vendite.fatturazione_lotti
        (codice, competenza_mese, tipo_doc_fiscale_id, emittente_soggetto_ruolo_id)
    SELECT 'PGTAP-CTBL-LOTTO-' || m.lato || '-' || m.emittente_fiscale_id,
           date_trunc('month', script.fn_data_operativa())::date,
           (SELECT tipo_doc FROM _catalogo),
           m.soggetto_ruolo_id
      FROM _mondi m
    RETURNING id, emittente_soggetto_ruolo_id
)
SELECT m.lato, l.id AS lotto_id
  FROM l JOIN _mondi m ON m.soggetto_ruolo_id = l.emittente_soggetto_ruolo_id;


-- ⚠️ Il canale e la distinta si creano NEL CONTESTO DEL LORO PADRONE: su
--   `pagamenti` c'e' un guard di scrittura sullo scope emittente, e sotto RLS
--   «non lo vedo» diventa «non esiste».
CREATE TEMP TABLE _distinte (lato text, ente_id bigint, distinta_id bigint);

DO $costruisci$
DECLARE
    m       record;
    -- ⚠️ `%TYPE` e non `bigint`: una variabile che riflette una colonna si
    --   ancora alla colonna, o il giorno in cui il tipo cambia questa resta
    --   indietro senza dirlo.
    v_ente  pagamenti.enti_incasso.id%TYPE;
    v_dist  pagamenti.vendite_contabili.id%TYPE;
    v_cat   record;
BEGIN
    SELECT * INTO v_cat FROM _catalogo;
    FOR m IN SELECT mo.lato, mo.auth_user_id, l.legame_id
               FROM _mondi mo JOIN _legami l ON l.lato = mo.lato
              ORDER BY mo.lato
    LOOP
        PERFORM script.fn_pgtap_set_contesto_operatore(m.auth_user_id);

        INSERT INTO pagamenti.enti_incasso
            (codice, descrizione, tipo, attivo,
             soggetto_ruolo_conto_bancario_id, centro_riscossione_id)
        VALUES ('PGTAP_CTBL_' || m.lato || '_' || m.legame_id,
                'Canale pgTAP manifesto lotti', 'ALTRO', true,
                m.legame_id, v_cat.centro_banca)
        RETURNING id INTO v_ente;

        INSERT INTO pagamenti.vendite_contabili
            (codice, centro_riscossione_id, data_contabile, data_registrazione,
             stato_id, ente_incasso_id, origine)
        VALUES ('PGTAP-CTBL-' || m.lato || '-' || m.legame_id,
                v_cat.centro_banca, script.fn_data_operativa(), script.fn_data_operativa(),
                v_cat.stato_bozza, v_ente, 'GENERATA')
        RETURNING id INTO v_dist;

        INSERT INTO _distinte VALUES (m.lato, v_ente, v_dist);
    END LOOP;

    -- ⚠️ Si esce dai panni dell'ultimo: un contesto lasciato addosso farebbe
    --   fallire le righe che seguono con un messaggio che parla di altro.
    PERFORM set_config('app.ruolo_applicativo', '', true);
    PERFORM set_config('app.current_user_id',   '', true);
END
$costruisci$;

-- ⭐ La distinta INTERNA: nessun canale. ⭐ Rev 2026-09-15 (D3): sa di chi e' —
--   qui si dichiara di A, come farebbe la madre dei fondi dal lotto di A. Senza
--   emittente e senza utente in sessione la sede unica rifiuterebbe (livello
--   4): non esiste piu' una distinta «di nessuno».
CREATE TEMP TABLE _interna AS
WITH d AS (
    INSERT INTO pagamenti.vendite_contabili
        (codice, centro_riscossione_id, data_contabile, data_registrazione,
         stato_id, ente_incasso_id, emittente_soggetto_ruolo_id, origine)
    SELECT 'PGTAP-CTBL-INTERNA', c.centro_fondo, script.fn_data_operativa(), script.fn_data_operativa(),
           c.stato_bozza, NULL, (SELECT m.soggetto_ruolo_id FROM _mondi m WHERE m.lato = 'A'),
           'GENERATA'
      FROM _catalogo c
    RETURNING id
)
SELECT id AS distinta_id FROM d;

INSERT INTO pagamenti.vendite_contabili_lotti (contabile_id, lotto_id)
SELECT d.distinta_id, l.lotto_id FROM _distinte d JOIN _lotti l ON l.lato = d.lato;

-- Il manifesto della distinta interna punta al lotto di A: cosi' il test 7 non
-- puo' passare "per caso" attraverso il perimetro del lotto.
INSERT INTO pagamenti.vendite_contabili_lotti (contabile_id, lotto_id)
SELECT (SELECT distinta_id FROM _interna), l.lotto_id
  FROM _lotti l WHERE l.lato = 'A';

-- ============================================================
-- 1..4. La struttura, e la decisione
-- ============================================================
SELECT is(
    (SELECT p.permissive || '/' || p.cmd FROM pg_policies p
      WHERE p.schemaname = 'pagamenti' AND p.tablename = 'vendite_contabili_lotti'
        AND p.policyname = 'rls_vendite_contabili_lotti_perimetro_incasso'),
    'PERMISSIVE/ALL',
    '1. la policy c''e'', ed e'' PERMISSIVE e FOR ALL: con la sola SELECT ogni scrittura operatore fallirebbe'
);

SELECT is(
    (SELECT c.relrowsecurity FROM pg_class c
       JOIN pg_namespace n ON n.oid = c.relnamespace AND n.nspname = 'pagamenti'
      WHERE c.relname = 'vendite_contabili_lotti'),
    true,
    '2. e la ROW LEVEL SECURITY e'' accesa: una policy senza ENABLE non filtra niente'
);

-- ⭐ La decisione del 2026-09-10, pinnata dove vive.
SELECT is_empty(
    $$SELECT p.tablename FROM pg_policies p
       WHERE p.schemaname = 'pagamenti' AND p.tablename = 'vendite_contabili_lotti'
         AND (   position('contabile_id' IN p.qual) = 0
              OR position('lotto_id'     IN p.qual) > 0)$$,
    '3. il manifesto risale dalla DISTINTA: la policy nomina contabile_id e non lotto_id'
);

SELECT is_empty(
    $$SELECT p.tablename FROM pg_policies p
       WHERE p.schemaname = 'pagamenti' AND p.tablename = 'vendite_contabili_lotti'
         AND (   position('fn_resolve_emittente_fiscale_id(''contabile''::text' IN p.qual)       = 0
              OR position('fn_resolve_emittente_fiscale_id(''contabile''::text' IN p.with_check) = 0)$$,
    '4. e passa dalla strada gia'' in servizio (il modo contabile del risolutore), non da una nuova'
);

-- ============================================================
-- Il perimetro, esercitato da dentro
-- ============================================================
ALTER TABLE pagamenti.vendite_contabili       FORCE ROW LEVEL SECURITY;
ALTER TABLE pagamenti.vendite_contabili_lotti FORCE ROW LEVEL SECURITY;

DO $perimetro$
DECLARE
    v_a   record;
    v_b   record;
    v_int pagamenti.vendite_contabili.id%TYPE;
    -- `v_n` resta `integer`: e' un CONTEGGIO, non il riflesso di una colonna.
    v_n   integer;
BEGIN
    SELECT d.*, m.auth_user_id INTO v_a
      FROM _distinte d JOIN _mondi m ON m.lato = d.lato WHERE d.lato = 'A';
    SELECT d.* INTO v_b FROM _distinte d WHERE d.lato = 'B';
    SELECT distinta_id INTO v_int FROM _interna;

    PERFORM script.fn_pgtap_set_contesto_operatore(v_a.auth_user_id);

    SELECT count(*) INTO v_n FROM pagamenti.vendite_contabili_lotti x
     WHERE x.contabile_id = v_a.distinta_id;
    PERFORM set_config('pgtap.manifesto_a', v_n::text, true);

    SELECT count(*) INTO v_n FROM pagamenti.vendite_contabili_lotti x
     WHERE x.contabile_id = v_b.distinta_id;
    PERFORM set_config('pgtap.manifesto_b', v_n::text, true);

    -- ⭐ La distinta interna e' di A: A ne vede il manifesto.
    SELECT count(*) INTO v_n FROM pagamenti.vendite_contabili_lotti x
     WHERE x.contabile_id = v_int;
    PERFORM set_config('pgtap.manifesto_interna', v_n::text, true);

    -- ⭐ L'INVARIANTE: nessuna distinta visibile ha un manifesto nascosto.
    -- ⛔ La prima stesura chiedeva «quali distinte HANNO un manifesto» con un
    --   `EXISTS` su `vendite_contabili_lotti` — cioe' leggendo ATTRAVERSO la
    --   policy che stava verificando. Con il manifesto nascosto l'`EXISTS` e'
    --   falso, la distinta non entrava nemmeno nel confronto e il test si
    --   auto-neutralizzava: provato togliendo il ramo della distinta interna,
    --   restava VERDE. *Un invariante che si misura attraverso il proprio
    --   filtro non misura niente.*
    -- ⇒ Il denominatore sono le TRE distinte che la fixture ha costruito da
    --   owner, quindi note e non filtrabili. ⚠️ Copertura dichiarata: vale per
    --   queste tre, non per l'intera tabella.
    SELECT count(*) INTO v_n
      FROM (SELECT c.id FROM pagamenti.vendite_contabili c
             WHERE c.id IN (v_a.distinta_id, v_b.distinta_id, v_int)
            EXCEPT
            SELECT x.contabile_id FROM pagamenti.vendite_contabili_lotti x
             WHERE x.contabile_id IN (v_a.distinta_id, v_b.distinta_id, v_int)) z;
    PERFORM set_config('pgtap.piu_chiuso', v_n::text, true);

    -- ⛔ SCRITTURA sul manifesto della distinta altrui.
    BEGIN
        INSERT INTO pagamenti.vendite_contabili_lotti (contabile_id, lotto_id)
        SELECT v_b.distinta_id, l.lotto_id FROM _lotti l WHERE l.lato = 'A';
        PERFORM set_config('pgtap.scrittura', 'PASSATA', true);
    EXCEPTION WHEN insufficient_privilege OR check_violation THEN
        PERFORM set_config('pgtap.scrittura', 'RIFIUTATA', true);
    END;

    -- ⭐ Rev 2026-09-15 (D3): dai panni di B la distinta interna di A — e il suo
    --   manifesto — non si vedono piu'. Prima era «di tutti».
    PERFORM script.fn_pgtap_set_contesto_operatore(
        (SELECT m.auth_user_id FROM _mondi m WHERE m.lato = 'B'));
    SELECT count(*) INTO v_n FROM pagamenti.vendite_contabili_lotti x
     WHERE x.contabile_id = v_int;
    PERFORM set_config('pgtap.manifesto_interna_b', v_n::text, true);

    -- ⛔ Nessuna veste: fail-closed.
    PERFORM set_config('app.ruolo_applicativo', '', true);
    SELECT count(*) INTO v_n FROM pagamenti.vendite_contabili_lotti;
    PERFORM set_config('pgtap.senza_veste', v_n::text, true);
END
$perimetro$;

ALTER TABLE pagamenti.vendite_contabili_lotti NO FORCE ROW LEVEL SECURITY;
ALTER TABLE pagamenti.vendite_contabili       NO FORCE ROW LEVEL SECURITY;

SELECT isnt(current_setting('pgtap.manifesto_a', true), '0',
            '5. l''operatore A vede il manifesto della PROPRIA distinta');

SELECT is(current_setting('pgtap.manifesto_b', true), '0',
          '6. e non quello della distinta di B: la riparazione');

SELECT isnt(current_setting('pgtap.manifesto_interna', true), '0',
            '7. il manifesto di una distinta INTERNA lo vede il SUO emittente: la testata sa di chi e'' (D3)');

SELECT is(current_setting('pgtap.manifesto_interna_b', true), '0',
          '7-bis. ...e non l''altro emittente: la distinta interna non e'' piu'' di tutti (D3)');

SELECT is(current_setting('pgtap.piu_chiuso', true), '0',
          '8. nessuna distinta visibile ha un manifesto nascosto: il satellite non e'' piu'' chiuso della testata');

SELECT is(current_setting('pgtap.scrittura', true), 'RIFIUTATA',
          '9. e non puo'' appendere un lotto al manifesto della distinta di B (WITH CHECK)');

SELECT is(current_setting('pgtap.senza_veste', true), '0',
          '10. senza veste applicativa il manifesto non risponde: fail-closed');

SELECT * FROM finish();

-- Il ROLLBACK e' la garanzia: comunque vada — verde, rosso, o morto a meta' —
-- questo file non lascia dietro di se' nessun canale, nessuna distinta e
-- nessuna azienda di prova.
ROLLBACK;
