-- ------------------------------------------------------------
-- SPDX-License-Identifier: GPL-3.0-or-later
-- pgtap-runner: owner
-- pgtap-runner-motivo: ALTER TABLE … FORCE ROW LEVEL SECURITY, locale alla
--   transazione — e' il FORCE a rendere l'owner soggetto alle policy, perche'
--   `titodb` non e' superuser e non puo' fare SET ROLE. E la fixture costruisce
--   DUE aziende: un operatore dentro un perimetro non potrebbe crearle.
-- pgTAP test FUNZIONALE RLS — i NOVE satelliti di pratiche.pratiche
--   Slice 20260910-01..04, brief brief-db-perimetro-emittente-righe-documento.md §11.7
--   Prima famiglia consegnata dal presidio dbops.vw_rls_perimetro_scoperto.
--
-- Elenco test (plan 12):
--   1) struttura: tutti e nove hanno la loro policy
--   2) struttura: e la RLS e' ACCESA su tutti e nove
--   3) ⛔ ogni policy usa l'adattatore GIUSTO per la propria chiave
--   4) l'operatore A vede il giornale della PROPRIA pratica
--   5) ⛔ e non vede quello di B — la riparazione
--   6) ⛔ e nemmeno il suo FLUSSO
--   7) ⛔ ne' la nota del flusso di B: il secondo livello regge
--   8) ⛔ SCRITTURA: A non puo' appendere una nota alla pratica di B
--   9) ⛔ SCRITTURA: ne' un allegato al flusso di B (secondo livello)
--  10) ⛔ senza veste applicativa: fail-closed su tutti e nove
--  11) ⭐ l'adattatore `_via_flusso` dice il vero anche dove la fixture non
--      arriva (calcoli_tempo): si interroga la funzione, non si fabbrica una
--      catena che non appartiene alla slice
--  12) ⭐ il gemello POSITIVO del 7: A vede la propria nota di flusso — senza,
--      un adattatore sbagliato resterebbe verde sul solo verso negativo
--
-- ────────────────────────────────────────────────────────────────
-- ⛔ IL DIFETTO CHE QUESTO FILE CHIUDE.
--   `pratiche.pratiche` e' protetta da `rls_pratiche_ef_whitelist`; i suoi
--   satelliti non avevano nessuna policy e `zeroerp_app` ha su tutti SELECT,
--   INSERT, UPDATE e DELETE. Il perimetro si fermava alla testata — e il
--   `giornale`, che racconta chi ha fatto cosa, era leggibile da chiunque.
--
-- ⭐ NOVE E NON SETTE, e la differenza l'ha trovata il criterio.
--   Il registro del debito ne dichiarava sette (FK diretta alla testata).
--   `allegati_flussi` e `note_flussi` pendono da `flussi`, che fino a ieri non
--   era protetta: quindi non erano nel perimetro. Armando `flussi` ci
--   sarebbero entrate **al giro dopo**, facendo rosso il presidio su due
--   tabelle mai censite. *Il criterio si estende da solo*, ed e' il motivo per
--   cui questa slice ne arma nove.
--
-- ⛔ IL TEST 3 E' QUELLO CHE NON SI PUO' SALTARE, ed e' il piu' facile da non
--   scrivere. Le due chiavi — `pratica_id` e `flusso_id` — sono entrambe
--   `bigint`: scrivere `_via_pratica` su `note_flussi` **non da' nessun
--   errore**. Passerebbe un id di flusso dove la funzione aspetta una pratica,
--   e la tabella filtrerebbe sulla pratica sbagliata, in silenzio. Un refuso
--   li' non fa rumore: lo si prende leggendo la definizione della policy.
--
-- ⚠️ COSA QUESTO FILE NON PROVA. Che i nove siano TUTTI i satelliti: quello lo
--   dice il criterio, in `db/pgtap/rls/test-rls-perimetro-scoperto.sql`. Qui si
--   prova che i nove armati filtrano davvero.
-- ------------------------------------------------------------

BEGIN;

SET CONSTRAINTS ALL IMMEDIATE;

SELECT plan(12);

-- ============================================================
-- I due mondi, una pratica per ciascuno, e i satelliti attorno
-- ============================================================
CREATE TEMP TABLE _mondi AS
SELECT 'A' AS lato, * FROM dbops.fn_pgtap_crea_emittente_operatore()
UNION ALL
SELECT 'B' AS lato, * FROM dbops.fn_pgtap_crea_emittente_operatore();

-- ⚠️ Tutti i cataloghi qui sotto arrivano da 80_data (tipi_prestazione,
--   template_flussi, config.*): esistono anche su un database ricostruito da
--   zero. La fixture non cerca dati di macchina — li COSTRUISCE o li prende
--   dal catalogo, che e' la sola cosa su cui la CI puo' contare.
--
-- ⛔ E il tipo di prestazione NON e' «il primo attivo». Alla nascita di una
--   pratica un trigger PINNA l'edizione di workflow risolta per (tipo,
--   emittente); per un emittente nuovo si ricade sul PRESET. Se quel preset non
--   ha nessuno step, la pratica nasce ma il flusso non si puo' creare — ed e'
--   esattamente cio' che e' successo alla prima stesura, sul primo tipo attivo
--   in ordine di id. ⇒ Si sceglie il tipo il cui preset porta DAVVERO degli
--   step, e la condizione si legge dal catalogo invece di fissare un id.
CREATE TEMP TABLE _pratiche AS
WITH tipo AS (
    SELECT d.tipo_prestazione_id AS id
      FROM pratiche.workflow_definizioni d
      JOIN pratiche.tipi_prestazione tp ON tp.id = d.tipo_prestazione_id
                                       AND tp.attivo
                                       AND tp.obsoleto_dal IS NULL
     WHERE d.emittente_fiscale_id IS NULL
       AND d.stato = 'PUBBLICATA'
       AND EXISTS (SELECT 1 FROM pratiche.template_flussi tf
                    WHERE tf.definizione_id = d.id)
     ORDER BY d.tipo_prestazione_id
     LIMIT 1
), ins AS (
    INSERT INTO pratiche.pratiche
        (emittente_fiscale_id, tipo_prestazione_id, stato_id, priorita_id)
    SELECT m.emittente_fiscale_id,
           (SELECT id FROM tipo),
           (SELECT s.id FROM config.stati_pratiche s WHERE s.codice_interno = 'BOZZA'),
           (SELECT pr.id FROM config.priorita_pratiche pr ORDER BY pr.id LIMIT 1)
      FROM _mondi m
    RETURNING id, emittente_fiscale_id
)
SELECT m.lato, i.id AS pratica_id, m.auth_user_id
  FROM ins i JOIN _mondi m ON m.emittente_fiscale_id = i.emittente_fiscale_id;

-- Il flusso: e' la madre delle due nipoti, quindi la fixture lo vuole.
-- ⚠️ Il template NON si prende «il primo che c'e'»: `trgfn_flussi_guard_definizione`
--   pretende che appartenga all'EDIZIONE di workflow pinnata dalla pratica
--   (`definizione_id`, che il trigger di nascita risolve per tipo+emittente).
--   Un template qualsiasi fa fallire l'INSERT con
--   `E_FLUSSI_TEMPLATE_FUORI_DEFINIZIONE` — successo alla prima stesura.
CREATE TEMP TABLE _flussi AS
WITH ins AS (
    INSERT INTO pratiche.flussi (pratica_id, template_flusso_id, stato_id)
    SELECT p.pratica_id,
           (SELECT tf.id FROM pratiche.template_flussi tf
             WHERE tf.definizione_id = pr.definizione_id
             ORDER BY tf.id LIMIT 1),
           (SELECT sf.id FROM config.stati_flussi_pratiche sf ORDER BY sf.id LIMIT 1)
      FROM _pratiche p
      JOIN pratiche.pratiche pr ON pr.id = p.pratica_id
    RETURNING id, pratica_id
)
SELECT p.lato, i.id AS flusso_id, i.pratica_id
  FROM ins i JOIN _pratiche p ON p.pratica_id = i.pratica_id;

-- Una nota di pratica, una nota di flusso e un allegato di flusso per mondo:
-- coprono le due chiavi, che sono le due cose che si possono sbagliare.
INSERT INTO pratiche.note_pratiche (pratica_id, tipo_nota_id, contenuto)
SELECT p.pratica_id,
       (SELECT tn.id FROM config.tipi_nota tn ORDER BY tn.id LIMIT 1),
       'Nota pgTAP pratica ' || p.lato
  FROM _pratiche p;

INSERT INTO pratiche.note_flussi (flusso_id, tipo_nota_id, contenuto)
SELECT f.flusso_id,
       (SELECT tn.id FROM config.tipi_nota tn ORDER BY tn.id LIMIT 1),
       'Nota pgTAP flusso ' || f.lato
  FROM _flussi f;

INSERT INTO pratiche.allegati_flussi (flusso_id, tipo_allegato_id, nome_file, percorso)
SELECT f.flusso_id,
       (SELECT ta.id FROM config.tipi_allegato ta ORDER BY ta.id LIMIT 1),
       'pgtap-' || f.lato || '.pdf', '/pgtap/' || f.lato
  FROM _flussi f;

-- ============================================================
-- 1..3. La struttura
-- ============================================================
SELECT is(
    (SELECT count(DISTINCT p.tablename)::int FROM pg_policies p
      WHERE p.schemaname = 'pratiche'
        AND p.tablename IN ('allegati_pratiche','calcoli_tempo','flussi','giornale',
                            'note_pratiche','pratiche_sorgenti','sospensioni',
                            'allegati_flussi','note_flussi')),
    9,
    '1. tutti e nove i satelliti di pratiche.pratiche hanno la loro policy'
);

-- ⛔ Si asserisce `relrowsecurity`, non l'esistenza della policy: una policy
--   con la RLS spenta non e' una difesa, ed e' lo stato in cui vivono
--   acquisti.ddt, acquisti.ordini e shop.ricevute.
SELECT is(
    (SELECT count(*)::int FROM pg_class c
       JOIN pg_namespace n ON n.oid = c.relnamespace AND n.nspname = 'pratiche'
      WHERE c.relname IN ('allegati_pratiche','calcoli_tempo','flussi','giornale',
                          'note_pratiche','pratiche_sorgenti','sospensioni',
                          'allegati_flussi','note_flussi')
        AND c.relrowsecurity),
    9,
    '2. e la ROW LEVEL SECURITY e'' accesa su tutti e nove'
);

-- ⛔ IL TEST CHE PRENDE IL REFUSO MUTO. Le due chiavi sono entrambe bigint:
--   `_via_pratica` su una tabella che porta `flusso_id` compilerebbe, girerebbe
--   e filtrerebbe sulla pratica sbagliata. Qui si pretende che ogni policy
--   nomini l'adattatore della PROPRIA chiave.
-- ⭐ Rev 2026-10-18 (D-3b-2 ondata 2, 20261018-50): la rotta si legge nel modo di
--   script.fn_resolve_emittente_fiscale_id, non piu' nel nome dell'adattatore.
SELECT is_empty(
    $$WITH atteso (tab, adattatore) AS (
          VALUES
            ('allegati_pratiche','fn_resolve_emittente_fiscale_id(''pratica''::text'),
            ('calcoli_tempo',    'fn_resolve_emittente_fiscale_id(''pratica''::text'),
            ('flussi',           'fn_resolve_emittente_fiscale_id(''pratica''::text'),
            ('giornale',         'fn_resolve_emittente_fiscale_id(''pratica''::text'),
            ('note_pratiche',    'fn_resolve_emittente_fiscale_id(''pratica''::text'),
            ('pratiche_sorgenti','fn_resolve_emittente_fiscale_id(''pratica''::text'),
            ('sospensioni',      'fn_resolve_emittente_fiscale_id(''pratica''::text'),
            ('allegati_flussi',  'fn_resolve_emittente_fiscale_id(''flusso''::text'),
            ('note_flussi',      'fn_resolve_emittente_fiscale_id(''flusso''::text')
      )
      SELECT a.tab
        FROM atteso a
        JOIN pg_policies p ON p.schemaname = 'pratiche' AND p.tablename = a.tab
       WHERE position(a.adattatore IN p.qual)       = 0
          OR position(a.adattatore IN p.with_check) = 0$$,
    '3. ogni policy usa la rotta della propria chiave (modo pratica vs flusso del risolutore)'
);

-- ============================================================
-- Il perimetro, esercitato da dentro
-- ============================================================
-- ⛔ TUTTI E NOVE, non solo quelli che la fixture popola. Il test 10 somma le
--   righe visibili su tutte e nove le tabelle: senza `FORCE` l'owner resta
--   esente e conta le righe VERE del database di sviluppo, quindi il test e'
--   rosso qui (successo alla prima stesura) — ma su un database ricostruito da
--   zero quelle tabelle sono vuote e sarebbe passato **per sottrazione**, cioe'
--   smettendo di verificare proprio dove nessuno guarda.
ALTER TABLE pratiche.pratiche          FORCE ROW LEVEL SECURITY;
ALTER TABLE pratiche.giornale          FORCE ROW LEVEL SECURITY;
ALTER TABLE pratiche.flussi            FORCE ROW LEVEL SECURITY;
ALTER TABLE pratiche.note_pratiche     FORCE ROW LEVEL SECURITY;
ALTER TABLE pratiche.note_flussi       FORCE ROW LEVEL SECURITY;
ALTER TABLE pratiche.allegati_flussi   FORCE ROW LEVEL SECURITY;
ALTER TABLE pratiche.allegati_pratiche FORCE ROW LEVEL SECURITY;
ALTER TABLE pratiche.calcoli_tempo     FORCE ROW LEVEL SECURITY;
ALTER TABLE pratiche.pratiche_sorgenti FORCE ROW LEVEL SECURITY;
ALTER TABLE pratiche.sospensioni       FORCE ROW LEVEL SECURITY;

DO $perimetro$
DECLARE
    v_a   record;
    v_b   record;
    v_n   integer;
BEGIN
    SELECT p.*, f.flusso_id INTO v_a
      FROM _pratiche p JOIN _flussi f ON f.pratica_id = p.pratica_id
     WHERE p.lato = 'A';
    SELECT p.*, f.flusso_id INTO v_b
      FROM _pratiche p JOIN _flussi f ON f.pratica_id = p.pratica_id
     WHERE p.lato = 'B';

    PERFORM script.fn_pgtap_set_contesto_operatore(v_a.auth_user_id);

    -- Il proprio giornale (lo scrive il trigger alla nascita della pratica).
    SELECT count(*) INTO v_n FROM pratiche.giornale g WHERE g.pratica_id = v_a.pratica_id;
    PERFORM set_config('pgtap.giornale_a', v_n::text, true);

    -- ⭐ Quello altrui: prima di questa slice qui si leggeva almeno 1.
    SELECT count(*) INTO v_n FROM pratiche.giornale g WHERE g.pratica_id = v_b.pratica_id;
    PERFORM set_config('pgtap.giornale_b', v_n::text, true);

    SELECT count(*) INTO v_n FROM pratiche.flussi f WHERE f.pratica_id = v_b.pratica_id;
    PERFORM set_config('pgtap.flussi_b', v_n::text, true);

    -- Secondo livello: la nota del flusso altrui.
    SELECT count(*) INTO v_n FROM pratiche.note_flussi n WHERE n.flusso_id = v_b.flusso_id;
    PERFORM set_config('pgtap.note_flussi_b', v_n::text, true);

    -- ⭐ E la PROPRIA. Il gemello positivo non e' simmetria per bellezza: con
    --   l'adattatore sbagliato — `_via_pratica` su una chiave di flusso — la
    --   riga di B resta invisibile lo stesso (un flusso_id letto come pratica_id
    --   non trova nessuna pratica, quindi fail-closed), e il test 7 resterebbe
    --   VERDE su una policy rotta. A cadere sarebbe questa: sparirebbe anche la
    --   nota PROPRIA. Provato mutando la policy, 2026-09-10.
    SELECT count(*) INTO v_n FROM pratiche.note_flussi n WHERE n.flusso_id = v_a.flusso_id;
    PERFORM set_config('pgtap.note_flussi_a', v_n::text, true);

    -- ⛔ SCRITTURA sulla pratica altrui (WITH CHECK, primo livello).
    BEGIN
        INSERT INTO pratiche.note_pratiche (pratica_id, tipo_nota_id, contenuto)
        VALUES (v_b.pratica_id,
                (SELECT tn.id FROM config.tipi_nota tn ORDER BY tn.id LIMIT 1),
                'intrusione');
        PERFORM set_config('pgtap.scrittura_nota', 'PASSATA', true);
    EXCEPTION WHEN insufficient_privilege OR check_violation THEN
        PERFORM set_config('pgtap.scrittura_nota', 'RIFIUTATA', true);
    END;

    -- ⛔ SCRITTURA sul flusso altrui (WITH CHECK, secondo livello).
    BEGIN
        INSERT INTO pratiche.allegati_flussi (flusso_id, tipo_allegato_id, nome_file, percorso)
        VALUES (v_b.flusso_id,
                (SELECT ta.id FROM config.tipi_allegato ta ORDER BY ta.id LIMIT 1),
                'intrusione.pdf', '/intrusione');
        PERFORM set_config('pgtap.scrittura_allegato', 'PASSATA', true);
    EXCEPTION WHEN insufficient_privilege OR check_violation THEN
        PERFORM set_config('pgtap.scrittura_allegato', 'RIFIUTATA', true);
    END;

    -- ⭐ L'adattatore di secondo livello, interrogato direttamente. E' la
    --   prova per `calcoli_tempo` e per gli altri satelliti che la fixture non
    --   costruisce: non serve una riga per chiedere a una funzione se dice il
    --   vero, e nominare la cosa da verificare e' piu' forte che contare righe
    --   attorno.
    PERFORM set_config('pgtap.adattatore',
        CASE WHEN     script.fn_scope_ef_whitelist_via_flusso(v_a.auth_user_id, v_a.flusso_id)
              AND NOT script.fn_scope_ef_whitelist_via_flusso(v_a.auth_user_id, v_b.flusso_id)
             THEN 'CORRETTO' ELSE 'SBAGLIATO' END, true);

    -- ⛔ Nessuna veste: fail-closed su tutti e nove.
    PERFORM set_config('app.ruolo_applicativo', '', true);
    SELECT (SELECT count(*) FROM pratiche.giornale)
         + (SELECT count(*) FROM pratiche.flussi)
         + (SELECT count(*) FROM pratiche.note_pratiche)
         + (SELECT count(*) FROM pratiche.note_flussi)
         + (SELECT count(*) FROM pratiche.allegati_flussi)
         + (SELECT count(*) FROM pratiche.allegati_pratiche)
         + (SELECT count(*) FROM pratiche.calcoli_tempo)
         + (SELECT count(*) FROM pratiche.pratiche_sorgenti)
         + (SELECT count(*) FROM pratiche.sospensioni)
      INTO v_n;
    PERFORM set_config('pgtap.senza_veste', v_n::text, true);
END
$perimetro$;

ALTER TABLE pratiche.sospensioni       NO FORCE ROW LEVEL SECURITY;
ALTER TABLE pratiche.pratiche_sorgenti NO FORCE ROW LEVEL SECURITY;
ALTER TABLE pratiche.calcoli_tempo     NO FORCE ROW LEVEL SECURITY;
ALTER TABLE pratiche.allegati_pratiche NO FORCE ROW LEVEL SECURITY;
ALTER TABLE pratiche.allegati_flussi   NO FORCE ROW LEVEL SECURITY;
ALTER TABLE pratiche.note_flussi       NO FORCE ROW LEVEL SECURITY;
ALTER TABLE pratiche.note_pratiche     NO FORCE ROW LEVEL SECURITY;
ALTER TABLE pratiche.flussi            NO FORCE ROW LEVEL SECURITY;
ALTER TABLE pratiche.giornale          NO FORCE ROW LEVEL SECURITY;
ALTER TABLE pratiche.pratiche          NO FORCE ROW LEVEL SECURITY;

SELECT isnt(current_setting('pgtap.giornale_a', true), '0',
            '4. l''operatore A vede il giornale della PROPRIA pratica');

SELECT is(current_setting('pgtap.giornale_b', true), '0',
          '5. e non vede quello della pratica di B: il giornale non racconta piu'' il lavoro altrui');

SELECT is(current_setting('pgtap.flussi_b', true), '0',
          '6. ne'' i flussi della pratica di B');

SELECT is(current_setting('pgtap.note_flussi_b', true), '0',
          '7. ne'' la nota del flusso di B: il secondo livello regge');

SELECT is(current_setting('pgtap.scrittura_nota', true), 'RIFIUTATA',
          '8. e non puo'' appendere una nota alla pratica di B (WITH CHECK)');

SELECT is(current_setting('pgtap.scrittura_allegato', true), 'RIFIUTATA',
          '9. ne'' un allegato al flusso di B: il WITH CHECK regge anche al secondo livello');

SELECT is(current_setting('pgtap.senza_veste', true), '0',
          '10. senza veste applicativa nessuno dei nove risponde: fail-closed');

SELECT is(current_setting('pgtap.adattatore', true), 'CORRETTO',
          '11. l''adattatore _via_flusso dice il vero: il proprio flusso si'', quello di B no');

SELECT isnt(current_setting('pgtap.note_flussi_a', true), '0',
            '12. e A la PROPRIA nota di flusso la vede: il secondo livello non chiude di troppo');

SELECT * FROM finish();

-- Il ROLLBACK e' la garanzia: comunque vada — verde, rosso, o morto a meta' —
-- questo file non lascia dietro di se' nessuna pratica, nessun flusso e nessuna
-- azienda di prova.
ROLLBACK;
