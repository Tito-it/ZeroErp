-- ------------------------------------------------------------
-- SPDX-License-Identifier: GPL-3.0-or-later
-- pgTAP test per Zero ERP
-- Test: simmetria del flag fatturazione_immediata su ordini/contratti/DDT
--       + presidio di immutabilita' dopo il push in commessa
-- Brief: brief-db-emissione-fattura-per-documento-sorgente PARTE B (step B6)
-- Changeset coperti: 20260727-01..09
-- rev 2026-10-25 (brief-db-pgtap-bolla-e-reso-costruiti, giro 1): il DDT SPEDITO del test 10 dal builder dbops.fn_pgtap_crea_ddt_da_ordine (trigger SPEDITO, causale VENDITA); restano a mano gli ordini col flag (6-8, 14-17: nessuna bolla, il flag e' il caso), il contratto e il preventivo.
-- rev 2026-10-25 (brief-db-pgtap-reso-costruito, giro D-4): righe e conferma dei due ordini col flag da dbops.fn_pgtap_crea_ordine_con_righe (p_ordine_id, 1 x 10): la testata col flag resta a mano, e' il caso; tolte dai riferimenti le colonne senza lettori (iva, stato confermato dell'ordine, stato accettato del preventivo).
-- rev 2026-10-24 (brief-modello-documento-vendita N-1): i documenti nascono in
--   bozza e si portano avanti con dbops.fn_pgtap_porta_a_stato (prima il
--   preventivo dei test 18-20 nasceva gia' ACCETTATO).
-- rev 2026-10-25 (brief-modello-documento-vendita §8, giro 6): il preventivo dei test 18-20 si emette con una riga (1 x 10) da dbops.fn_pgtap_crea_preventivo_con_righe (p_preventivo_id): l'emissione senza righe e' rifiutata; la testata col flag resta a mano, nessuna attesa conta righe o importi.
-- ------------------------------------------------------------
-- Indice test (1..20):
--  1) colonna fatturazione_immediata presente su vendite.ordini
--  2) colonna fatturazione_immediata presente su vendite.contratti
--  3) colonna fatturazione_immediata presente su vendite.ddt
--  4) le tre colonne sono NOT NULL con DEFAULT false
--  5) G16: nessun documento preesistente e' finito su corsia immediata
--  6) G9:  fn_list_ordini_da_pushare proietta TRUE se il flag e' true
--  7) G9:  fn_list_ordini_da_pushare proietta FALSE se il flag e' false
--  8) G18: prezzo_bloccato resta TRUE sugli ordini in ENTRAMBI i casi
--  9) G9:  fn_list_contratti_da_pushare segue la colonna (data-dependent)
-- 10) G9:  fn_list_ddt_da_pushare segue la colonna (data-dependent)
-- 11) D-6: vendite.attivita_consumi NON ha il flag (scelta di dominio)
-- 12) G10: flag diverso -> due commesse distinte (corsie separate)
-- 13) i 4 trigger di guard sono armati (preventivi/ordini/contratti/ddt)
-- 14) G17: UPDATE del flag su documento NON pushato -> riesce
-- 15) G17: UPDATE del flag su documento GIA' pushato -> bloccato
-- 16) G17: riscrivere lo STESSO valore su doc pushato -> passa (WHEN IS DISTINCT)
-- 17) G17: UPDATE di un'ALTRA colonna su doc pushato -> passa
-- 18) G17: preventivo NON pushato -> UPDATE del flag riesce
-- 19) G17: preventivo GIA' pushato -> UPDATE del flag bloccato (chiave 'uid')
-- 20) G17: preventivo pushato, stesso valore -> passa
-- ------------------------------------------------------------
-- NOTA sui test 18-20 (copertura delle DUE convenzioni di chiave):
--   i test 14-17 provano il guard sugli ORDINI, che hanno
--   config.sorgenti.key_selector = 'id' -> commesse_sorgenti.sorgente_uid
--   contiene id::text (normalizzato da fn_link_commessa_sorgente).
--   I PREVENTIVI hanno key_selector = 'uid' -> la chiave e' l'uuid, senza
--   traduzione. Sono i due rami del CASE dentro il guard: provarne uno solo
--   lascerebbe l'altro scoperto, ed e' esattamente il ramo su cui e' facile
--   sbagliare (vedi guida sorgente-polimorfa §4a).
-- ------------------------------------------------------------
-- NOTA COPERTURA (onesta'): i test 9 e 10 sono **data-dependent** e usano
--   lo skip condizionale. Costruire da zero un contratto o un DDT *pushabile*
--   richiede una fixture molto piu' pesante di quella di un ordine (numero
--   generato, daterange di validita', causale di trasporto fatturabile, stato
--   >= SPEDITO, contatore merce), con alto rischio di fixture fragile. La
--   modifica alle tre funzioni e' la stessa identica riga, ed e' verificata
--   end-to-end sull'ordine (test 6-8): su contratti e DDT si verifica che il
--   valore proiettato SEGUA la colonna quando esiste almeno un documento
--   eleggibile. Se il DB di test non ne ha, i due test dichiarano skip invece
--   di dare un falso verde.
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

SELECT plan(20);

-- ============================================================
-- TEST 1-3: le colonne esistono
-- ============================================================
SELECT has_column('vendite', 'ordini', 'fatturazione_immediata',
  '1) vendite.ordini.fatturazione_immediata presente');

SELECT has_column('vendite', 'contratti', 'fatturazione_immediata',
  '2) vendite.contratti.fatturazione_immediata presente');

SELECT has_column('vendite', 'ddt', 'fatturazione_immediata',
  '3) vendite.ddt.fatturazione_immediata presente');

-- ============================================================
-- TEST 4: NOT NULL + DEFAULT false su tutte e tre.
--   Il default e' cio' che garantisce G16: applicare la migration non
--   sposta di corsia nessun documento esistente.
-- ============================================================
SELECT is(
  (
    SELECT count(*)::int
    FROM information_schema.columns c
    WHERE c.table_schema = 'vendite'
      AND c.table_name IN ('ordini', 'contratti', 'ddt')
      AND c.column_name = 'fatturazione_immediata'
      AND c.is_nullable = 'NO'
      AND c.column_default = 'false'
  ),
  3,
  '4) le 3 colonne sono NOT NULL con DEFAULT false'
);

-- ============================================================
-- TEST 5 (G16): non-regressione sui dati preesistenti.
--   Dopo la migration ogni documento gia' in tabella deve valere false:
--   nessuno cambia corsia per effetto dell'aggiunta della colonna.
--   (Il test gira PRIMA delle fixture di questo file, che sono le uniche
--    righe con flag true.)
-- ============================================================
SELECT is(
  (
    SELECT count(*)::int FROM (
      SELECT 1 FROM vendite.ordini    WHERE fatturazione_immediata IS TRUE
      UNION ALL
      SELECT 1 FROM vendite.contratti WHERE fatturazione_immediata IS TRUE
      UNION ALL
      SELECT 1 FROM vendite.ddt       WHERE fatturazione_immediata IS TRUE
    ) x
  ),
  0,
  '5) G16: nessun documento preesistente su corsia immediata'
);

-- ============================================================
-- Riferimenti minimi: il mondo COSTRUITO, dal DB solo il catalogo di seed
-- ============================================================
-- ⛔ rev 2026-10-13: il mondo si COSTRUISCE (su un DB ricostruito anagrafiche e
--   articoli sono vuoti). Prima BA, ruolo, emittente e articolo si pescavano col
--   LIMIT 1: su zeroerp_ci erano NULL e l'ordine moriva sul NOT NULL di
--   soggetto_ruolo_id. Ora un'azienda nuova col suo operatore (contesto aperto
--   su di lui), il cliente legato a lei (dbops.fn_pgtap_crea_mondo_cliente) e un
--   articolo merce non gestito. Modello: test-ddt-magazzino-testata-v1.
CREATE TEMP TABLE _az AS SELECT * FROM dbops.fn_pgtap_crea_emittente_operatore();
DO $ctx$ BEGIN PERFORM script.fn_pgtap_set_contesto_operatore((SELECT auth_user_id FROM _az)); END $ctx$;
CREATE TEMP TABLE _m AS SELECT * FROM dbops.fn_pgtap_crea_mondo_cliente('pgTAP fi simmetria');

CREATE TEMP TABLE tmp_refs_fi AS
SELECT
  m.billing_account_id,
  m.utility_id,
  m.cliente_soggetto_ruolo_id AS soggetto_ruolo_id,
  dbops.fn_pgtap_crea_articolo('PGTAP-FI-SIMM', false) AS articolo_id,
  (SELECT v.id FROM config.valute v ORDER BY v.id LIMIT 1) AS valuta_id,
  m.emittente_fiscale_id,
  (SELECT s.id FROM config.stati_doc_ordini s
    WHERE s.codice_interno = 'DRAFT' AND s.attivo IS TRUE ORDER BY s.id LIMIT 1)      AS stato_ord_draft_id,
  (SELECT s.id FROM config.sorgenti s
    WHERE s.codice_interno = 'ORDINE_VENDITA' ORDER BY s.id LIMIT 1) AS sorgente_ordine_id,
  (SELECT s.id FROM config.sorgenti s
    WHERE s.codice_interno = 'PREVENTIVO' ORDER BY s.id LIMIT 1)     AS sorgente_preventivo_id,
  m.istanza_utility_id
FROM _m m;

-- ============================================================
-- FIXTURE: due ordini CONFERMATO nello stesso perimetro,
--   uno con flag true (corsia immediata) e uno con flag false.
--   fatturazione_trigger = 'CONFERMATO' e' il requisito di eleggibilita'
--   al push di fn_list_ordini_da_pushare.
--   La testata col flag, scritto alla nascita, e' il caso: resta a mano.
--   La riga (1 x 10) e la conferma sono la strada dell'ordine: dal builder,
--   sulla testata del test (p_ordine_id).
-- ============================================================
CREATE TEMP TABLE tmp_ord_imm AS
WITH ins AS (
  INSERT INTO vendite.ordini (
    soggetto_ruolo_id, billing_account_id, stato_doc_ordine_id,
    valuta_id, data, fatturazione_trigger, emittente_fiscale_id,
    fatturazione_immediata, storicizza, meta)
  SELECT r.soggetto_ruolo_id, r.billing_account_id, r.stato_ord_draft_id,
         r.valuta_id, DATE '2026-07-01', 'CONFERMATO', r.emittente_fiscale_id,
         true, false,
         jsonb_build_object('test_scope', 'pgtap_fi_simmetria_imm')
  FROM tmp_refs_fi r
  RETURNING id, uid)
SELECT * FROM ins;

CREATE TEMP TABLE tmp_ord_dif AS
WITH ins AS (
  INSERT INTO vendite.ordini (
    soggetto_ruolo_id, billing_account_id, stato_doc_ordine_id,
    valuta_id, data, fatturazione_trigger, emittente_fiscale_id,
    fatturazione_immediata, storicizza, meta)
  SELECT r.soggetto_ruolo_id, r.billing_account_id, r.stato_ord_draft_id,
         r.valuta_id, DATE '2026-07-01', 'CONFERMATO', r.emittente_fiscale_id,
         false, false,
         jsonb_build_object('test_scope', 'pgtap_fi_simmetria_dif')
  FROM tmp_refs_fi r
  RETURNING id, uid)
SELECT * FROM ins;

DO $x$ BEGIN
  PERFORM dbops.fn_pgtap_crea_ordine_con_righe('fi_simmetria imm', 'CONFERMATO',
      p_quantita => 1, p_prezzo => 10, p_articolo_id => (SELECT articolo_id FROM tmp_refs_fi),
      p_ordine_id => (SELECT id FROM tmp_ord_imm));
  PERFORM dbops.fn_pgtap_crea_ordine_con_righe('fi_simmetria dif', 'CONFERMATO',
      p_quantita => 1, p_prezzo => 10, p_articolo_id => (SELECT articolo_id FROM tmp_refs_fi),
      p_ordine_id => (SELECT id FROM tmp_ord_dif));
END $x$;

-- ============================================================
-- TEST 6-7 (G9): il valore proiettato segue la COLONNA.
--   Prima di 20260727-04 la funzione restituiva la costante FALSE per
--   qualunque ordine: il test 6 sarebbe fallito.
-- ============================================================
SELECT is(
  (SELECT bool_and(x.fatturazione_immediata)
     FROM vendite.fn_list_ordini_da_pushare(
            p_ordine_id => (SELECT id FROM tmp_ord_imm)) x),
  true,
  '6) G9: ordine con flag true -> push proietta TRUE'
);

SELECT is(
  (SELECT bool_or(x.fatturazione_immediata)
     FROM vendite.fn_list_ordini_da_pushare(
            p_ordine_id => (SELECT id FROM tmp_ord_dif)) x),
  false,
  '7) G9: ordine con flag false -> push proietta FALSE'
);

-- ============================================================
-- TEST 8 (G18): prezzo_bloccato NON e' governato dal flag.
--   Sugli ordini e' la costante TRUE. Sui preventivi invece vale
--   COALESCE(fatturazione_immediata, false): quell'accoppiamento e'
--   un'anomalia dei soli preventivi e non va propagata (fatto F11).
--   Se qualcuno "uniformasse" la riga copiandola dal preventivo, qui
--   il valore diventerebbe (true, false) invece di (true, true).
-- ============================================================
SELECT is(
  (
    SELECT bool_and(x.prezzo_bloccato) FROM (
      SELECT prezzo_bloccato FROM vendite.fn_list_ordini_da_pushare(
               p_ordine_id => (SELECT id FROM tmp_ord_imm))
      UNION ALL
      SELECT prezzo_bloccato FROM vendite.fn_list_ordini_da_pushare(
               p_ordine_id => (SELECT id FROM tmp_ord_dif))
    ) x
  ),
  true,
  '8) G18: prezzo_bloccato resta TRUE a prescindere dal flag'
);

-- ============================================================
-- TEST 9-10 (G9 su contratti e DDT): data-dependent.
--   Verifica che il valore proiettato COINCIDA con la colonna del
--   documento, su tutti i documenti eleggibili trovati nel DB.
--   Nessun documento eleggibile -> skip (vedi NOTA COPERTURA in testa).
-- ============================================================
-- ⛔ rev 2026-10-13: i documenti eleggibili si COSTRUISCONO. Con l'azienda
--   nuova del mondo, cercarli «fra quelli del DB» dava zero righe sotto la RLS
--   e i test 9-10 andavano sempre in skip. Si costruiscono quindi, coi verbi
--   del dominio, un contratto ATTIVO con una riga UNA_TANTUM (modello:
--   test-push-contratto-dalla-madre-v1) e un DDT SPEDITO causale VENDITA nato
--   da un ordine con trigger SPEDITO (modello: test-fn-list-ordini-da-pushare-v3,
--   caso 9b). Lo skip resta come ripiego dichiarato: se il dominio smette di
--   renderli eleggibili, il file lo dice.
CREATE TEMP TABLE tmp_ctr_fi AS
WITH ins AS (
  INSERT INTO vendite.contratti (
    numero, billing_account_id, istanza_utility_id, utility_id,
    valido_dal, valido_al, stato_doc_contratto_id, data, meta)
  SELECT 'PGT-FI-' || substr(md5(clock_timestamp()::text), 1, 8),
         r.billing_account_id, r.istanza_utility_id, r.utility_id,
         date_trunc('month', script.fn_data_operativa())::date,
         (date_trunc('month', script.fn_data_operativa()) + interval '1 year - 1 day')::date,
         (SELECT s.id FROM config.stati_doc_contratti s
           WHERE s.codice_interno = 'DRAFT' AND s.attivo IS TRUE ORDER BY s.id LIMIT 1),
         script.fn_data_operativa(),
         jsonb_build_object('test_scope', 'pgtap_fi_simmetria_ctr')
    FROM tmp_refs_fi r
  RETURNING id)
SELECT * FROM ins;

INSERT INTO vendite.contratti_righe (
  contratto_id, articolo_id, prezzo_unitario, tipo_erogazione,
  qta_operativa, quantita, fonte_quantita_attesa, tipo_eccezione, attivo, meta)
SELECT c.id, r.articolo_id, 50, 'UNA_TANTUM',
       1, 1, 'FISSA', 'AGGIUNTA'::vendite.tipo_eccezione_contratto, true,
       jsonb_build_object('test_scope', 'pgtap_fi_simmetria_ctr')
  FROM tmp_ctr_fi c, tmp_refs_fi r;

UPDATE vendite.contratti
   SET stato_doc_contratto_id = (SELECT s.id FROM config.stati_doc_contratti s
                                  WHERE s.codice_interno = 'ATTIVO' AND s.attivo IS TRUE
                                  ORDER BY s.id LIMIT 1)
 WHERE id = (SELECT id FROM tmp_ctr_fi);

-- Il DDT: ordine 1 @10 trigger SPEDITO, bolla SPEDITA causale VENDITA, dal builder.
CREATE TEMP TABLE tmp_ddt_fi AS
SELECT * FROM dbops.fn_pgtap_crea_ddt_da_ordine('fi simmetria DDT', 'SPEDITO',
    (SELECT billing_account_id FROM tmp_refs_fi), p_quantita => 1, p_prezzo => 10,
    p_articolo_id => (SELECT articolo_id FROM tmp_refs_fi),
    p_fatturazione_trigger => 'SPEDITO', p_causale_codice => 'VENDITA');

CREATE TEMP TABLE tmp_chk_contratti AS
SELECT count(*)::int AS totali,
       count(*) FILTER (
         WHERE x.fatturazione_immediata IS DISTINCT FROM c.fatturazione_immediata
       )::int AS incoerenti
FROM vendite.fn_list_contratti_da_pushare(p_limit => 50) x
JOIN vendite.contratti c ON c.id = x.contratto_id;

SELECT CASE
  WHEN (SELECT totali FROM tmp_chk_contratti) = 0
    THEN skip('nessun contratto eleggibile al push nel DB di test', 1)
  ELSE is(
    (SELECT incoerenti FROM tmp_chk_contratti), 0,
    '9) G9: fn_list_contratti_da_pushare segue vendite.contratti.fatturazione_immediata'
  )
END;

CREATE TEMP TABLE tmp_chk_ddt AS
SELECT count(*)::int AS totali,
       count(*) FILTER (
         WHERE x.fatturazione_immediata IS DISTINCT FROM d.fatturazione_immediata
       )::int AS incoerenti
FROM vendite.fn_list_ddt_da_pushare(p_limit => 50) x
JOIN vendite.ddt d ON d.id = x.ddt_id;

SELECT CASE
  WHEN (SELECT totali FROM tmp_chk_ddt) = 0
    THEN skip('nessun DDT eleggibile al push nel DB di test', 1)
  ELSE is(
    (SELECT incoerenti FROM tmp_chk_ddt), 0,
    '10) G9: fn_list_ddt_da_pushare segue vendite.ddt.fatturazione_immediata'
  )
END;

-- ============================================================
-- TEST 11 (D-6): i consumi NON hanno il flag, ed e' voluto.
--   Un consumo e' una misura, non un accordo commerciale: la corsia la
--   decide il contratto che lo governa. Se qualcuno aggiungesse la
--   colonna "per simmetria", questo test lo intercetta e obbliga a
--   ridiscutere la decisione invece di subirla.
-- ============================================================
SELECT hasnt_column('vendite', 'attivita_consumi', 'fatturazione_immediata',
  '11) D-6: attivita_consumi NON ha il flag (scelta di dominio, non dimenticanza)');

-- ============================================================
-- TEST 12 (G10): il flag e' parte della chiave di dedup della commessa.
--   Stesso cliente/utility/periodo ma flag diverso -> DUE commesse
--   distinte, quindi due lotti distinti, quindi corsie separate.
--   E' l'invariante che rende effettivo l'instradamento.
-- ============================================================
CREATE TEMP TABLE tmp_comm_fi AS
SELECT
  vendite.fn_get_or_create_commessa(
    p_billing_account_id => (SELECT billing_account_id FROM tmp_refs_fi),
    p_utility_id => (SELECT utility_id FROM tmp_refs_fi),
    p_tipo_commessa => 'AUTO',
    p_policy_fatturazione => 'DA_DOCUMENTO',
    p_fatturazione_immediata => true,
    p_priorita_operativa => 'NORMALE',
    p_competenza_dal => DATE '2026-07-01',
    p_competenza_al => DATE '2026-07-31',
    p_meta => jsonb_build_object('test_scope', 'pgtap_fi_corsia_imm')
  ) AS commessa_imm,
  vendite.fn_get_or_create_commessa(
    p_billing_account_id => (SELECT billing_account_id FROM tmp_refs_fi),
    p_utility_id => (SELECT utility_id FROM tmp_refs_fi),
    p_tipo_commessa => 'AUTO',
    p_policy_fatturazione => 'DA_DOCUMENTO',
    p_fatturazione_immediata => false,
    p_priorita_operativa => 'NORMALE',
    p_competenza_dal => DATE '2026-07-01',
    p_competenza_al => DATE '2026-07-31',
    p_meta => jsonb_build_object('test_scope', 'pgtap_fi_corsia_dif')
  ) AS commessa_dif;

SELECT isnt(
  (SELECT commessa_imm FROM tmp_comm_fi),
  (SELECT commessa_dif FROM tmp_comm_fi),
  '12) G10: flag diverso, stesso perimetro -> due commesse distinte (corsie separate)'
);

-- ============================================================
-- TEST 13: il presidio e' armato su tutte e quattro le sorgenti che
--   hanno il flag (preventivi incluso: il buco semantico esisteva la'
--   da sempre, non solo sulle colonne nuove).
-- ============================================================
SELECT is(
  (
    SELECT count(*)::int
    FROM pg_trigger t
    JOIN pg_class c     ON c.oid = t.tgrelid
    JOIN pg_namespace n ON n.oid = c.relnamespace
    JOIN pg_proc p      ON p.oid = t.tgfoid
    WHERE n.nspname = 'vendite'
      AND p.proname = 'trgfn_guard_fatturazione_immediata_immutabile'
      AND NOT t.tgisinternal
      AND c.relname IN ('preventivi', 'ordini', 'contratti', 'ddt')
  ),
  4,
  '13) guard armato su preventivi, ordini, contratti, ddt'
);

-- ============================================================
-- TEST 14 (G17): prima del push il flag e' liberamente modificabile.
--   E' il percorso legittimo: si decide la corsia alla creazione o
--   all'accettazione del documento.
-- ============================================================
SELECT lives_ok(
  $$ UPDATE vendite.ordini
        SET fatturazione_immediata = false
      WHERE id = (SELECT id FROM tmp_ord_imm) $$,
  '14) G17: UPDATE del flag su ordine NON pushato -> riesce'
);

-- Ripristina il valore per i test successivi
UPDATE vendite.ordini
   SET fatturazione_immediata = true
 WHERE id = (SELECT id FROM tmp_ord_imm);

-- ============================================================
-- FIXTURE: push dell'ordine in commessa.
--   fn_link_commessa_sorgente NORMALIZZA la chiave: riceve l'uid e
--   scrive id::text, perche' ORDINE_VENDITA ha key_selector='id'.
--   E' esattamente la forma che il guard va a cercare.
-- ============================================================
CREATE TEMP TABLE tmp_link_fi AS
SELECT vendite.fn_link_commessa_sorgente(
  p_commessa_id      => (SELECT commessa_imm FROM tmp_comm_fi),
  p_sorgente_tipo_id => (SELECT sorgente_ordine_id FROM tmp_refs_fi),
  p_sorgente_uid     => (SELECT uid::text FROM tmp_ord_imm),
  p_meta             => jsonb_build_object('test_scope', 'pgtap_fi_simmetria')
) AS link_id;

-- ============================================================
-- TEST 15 (G17): dopo il push il cambio e' respinto.
--   Non e' pignoleria: dopo il push il flag e' GIA' inerte (e' nella
--   chiave di dedup della commessa, e il documento sta in una sola
--   commessa aperta). Senza guard il campo resterebbe editabile a video
--   senza produrre alcun effetto.
--   ⭐ Dal 2026-10-12 (20261012-47, D-14) il blocco vale solo finche' la
--   commessa e' APERTA: il caso «commessa annullata, flag di nuovo
--   modificabile» e' in vendite/test-annullo-commessa-v1 (14c, 14d), che le
--   fixture se le costruisce.
-- ============================================================
SELECT throws_ok(
  $$ UPDATE vendite.ordini
        SET fatturazione_immediata = false
      WHERE id = (SELECT id FROM tmp_ord_imm) $$,
  'P0001', NULL,
  '15) G17: UPDATE del flag su ordine GIA'' pushato -> bloccato'
);

-- ============================================================
-- TEST 16 (G17): riscrivere lo STESSO valore non e' un cambio.
--   Il trigger ha WHEN (NEW IS DISTINCT FROM OLD): serve al percorso di
--   ri-accettazione, che riscrive il flag invariato.
-- ============================================================
SELECT lives_ok(
  $$ UPDATE vendite.ordini
        SET fatturazione_immediata = true
      WHERE id = (SELECT id FROM tmp_ord_imm) $$,
  '16) G17: riscrivere lo stesso valore su ordine pushato -> passa'
);

-- ============================================================
-- TEST 17 (G17): il guard e' chirurgico — UPDATE OF fatturazione_immediata.
--   Non deve interferire con le altre modifiche del documento.
-- ============================================================
SELECT lives_ok(
  $$ UPDATE vendite.ordini
        SET meta = meta || jsonb_build_object('touched', true)
      WHERE id = (SELECT id FROM tmp_ord_imm) $$,
  '17) G17: UPDATE di altra colonna su ordine pushato -> passa'
);

-- ============================================================
-- FIXTURE + TEST 18-20: lo stesso presidio sull'ALTRA convenzione di chiave.
--   PREVENTIVO ha key_selector='uid': commesse_sorgenti.sorgente_uid contiene
--   l'uuid, senza la traduzione che fn_link_commessa_sorgente applica agli
--   ordini. E' il secondo ramo del CASE dentro il guard.
-- ============================================================
CREATE TEMP TABLE tmp_prev_fi AS
WITH ins AS (
  INSERT INTO vendite.preventivi (
    numero, rev, billing_account_id, istanza_utility_id, utility_id,
    validita_dal, validita_al, valuta_id, data,
    fatturazione_immediata, storicizza, meta, emittente_fiscale_id)
  SELECT 'PGTAP-FI-SIMM', 0, r.billing_account_id, r.istanza_utility_id, r.utility_id,
         DATE '2080-01-01', DATE '2080-12-31', r.valuta_id,
         DATE '2080-01-01', true, false,
         jsonb_build_object('test_scope', 'pgtap_fi_simmetria_prev'),
         r.emittente_fiscale_id
  FROM tmp_refs_fi r
  RETURNING id, uid)
SELECT * FROM ins;

-- ⚠️ rev 2026-10-24: il preventivo nasce in bozza (lo stato non si scrive: lo
--   mette il trigger della nascita) e va ad ACCETTATO sotto i guard veri.
-- ⚠️ rev 2026-10-25 (§8, giro 6): con una riga (1 x 10) scritta in bozza da
--   dbops.fn_pgtap_crea_preventivo_con_righe, che poi porta lo stato: senza
--   righe l'emissione e' rifiutata (E_PREV_NESSUNA_RIGA_ATTIVA). La testata
--   col flag resta a mano, e' il caso.
DO $porta$ BEGIN
  PERFORM dbops.fn_pgtap_crea_preventivo_con_righe('fi simmetria', 'ACCETTATO',
            p_preventivo_id => (SELECT id FROM tmp_prev_fi));
END $porta$;

-- 18) prima del push: modificabile
SELECT lives_ok(
  $$ UPDATE vendite.preventivi
        SET fatturazione_immediata = false
      WHERE id = (SELECT id FROM tmp_prev_fi) $$,
  '18) G17: UPDATE del flag su preventivo NON pushato -> riesce'
);

UPDATE vendite.preventivi
   SET fatturazione_immediata = true
 WHERE id = (SELECT id FROM tmp_prev_fi);

-- Push del preventivo: qui la chiave resta l'uuid (key_selector='uid'),
-- nessuna traduzione. La commessa e' quella "differita" per non collidere
-- con il link dell'ordine sulla commessa immediata (UNIQUE globale su
-- (sorgente_tipo_id, sorgente_uid) e' comunque per sorgente diversa).
CREATE TEMP TABLE tmp_link_prev_fi AS
SELECT vendite.fn_link_commessa_sorgente(
  p_commessa_id      => (SELECT commessa_dif FROM tmp_comm_fi),
  p_sorgente_tipo_id => (SELECT sorgente_preventivo_id FROM tmp_refs_fi),
  p_sorgente_uid     => (SELECT uid::text FROM tmp_prev_fi),
  p_meta             => jsonb_build_object('test_scope', 'pgtap_fi_simmetria_prev')
) AS link_id;

-- 19) dopo il push: bloccato. Se il guard risolvesse la chiave con id::text
--     invece che con uid::text, qui non troverebbe il link e il test
--     fallirebbe -> e' il controllo positivo sul ramo 'uid'.
SELECT throws_ok(
  $$ UPDATE vendite.preventivi
        SET fatturazione_immediata = false
      WHERE id = (SELECT id FROM tmp_prev_fi) $$,
  'P0001', NULL,
  '19) G17: UPDATE del flag su preventivo GIA'' pushato -> bloccato (chiave uid)'
);

-- 20) stesso valore: nessun cambio, nessun blocco (WHEN IS DISTINCT FROM).
--     E' il percorso di ri-accettazione di un preventivo gia' accettato.
SELECT lives_ok(
  $$ UPDATE vendite.preventivi
        SET fatturazione_immediata = true
      WHERE id = (SELECT id FROM tmp_prev_fi) $$,
  '20) G17: riscrivere lo stesso valore su preventivo pushato -> passa'
);

SELECT * FROM finish();
ROLLBACK;
