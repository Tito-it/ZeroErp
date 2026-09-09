-- ------------------------------------------------------------
-- SPDX-License-Identifier: GPL-3.0-or-later
-- pgtap-contesto: escluso — il contesto operatore NON si prende dall'helper di
--   sessione: questo file lo COSTRUISCE tre volte, con tre whitelist diverse,
--   ed e' il soggetto stesso del test. Un contesto fissato in testa
--   sovrascriverebbe cio' che i casi stanno provando.
-- pgtap-runner: owner
-- pgtap-runner-motivo: ALTER TABLE vendite.fatture_fondi_fattura_source ENABLE +
--   FORCE ROW LEVEL SECURITY, locale alla transazione: e' il FORCE a rendere
--   l'owner soggetto alle policy, e l'identita' la simulano le GUC app.*, non il
--   ruolo di connessione. La fixture inoltre crea l'atto PRIMA di armare la RLS.
-- pgTAP test FUNZIONALE RLS — vendite.fatture_fondi_fattura_source
--   (policy ef_whitelist e ba_ownership, changeSet 20260831-62 · D-20 / G-2)
--
-- Elenco test (plan 11):
--  1) Riferimenti minimi presenti: l'atto e' costruito, e i due emittenti sono diversi
--  2) whitelist VUOTA                    -> atto NON visibile (fail-closed)
--  3) whitelist = emittente dell'atto    -> visibile
--  4) whitelist = ALTRO emittente        -> NON visibile
--  5) ruolo non OPERATORE                -> NON visibile (il cancello della policy)
--  6) ⭐ ef_whitelist e' FOR ALL: in scope la scrittura passa
--  7) ...e fuori scope non tocca niente
--  8) ⭐ La WITH CHECK legge da NEW: un INSERT in scope PASSA
--  9) ...e un INSERT fuori scope e' rifiutato dalla policy (42501)
-- 10) veste CLIENTE_PORTALE non proprietaria -> NON visibile
-- 11) ⭐ il ruolo del giro notturno ha BYPASSRLS: la RLS non lo ferma
--
-- PERCHE' FUNZIONALE E NON STRUTTURALE. Un test strutturale direbbe che le due
-- policy esistono; non direbbe che si possono ancora SCRIVERE gli atti. ⭐ E' la
-- domanda che conta, perche' su questa tabella scrivono tre percorsi vivi — il
-- giro notturno, il riporto di pagamenti.fn_conferma_sistemazione e il gesto di
-- cancellazione di D-21 — e una policy troppo stretta li fermerebbe tutti.
--
-- ⭐ I TEST CHE CONTANO SONO L'8 E IL 9, e sono qui per un errore gia' pagato:
-- su pagamenti.enti_incasso la WITH CHECK proposta cercava il legame che
-- l'INSERT stesso stava scrivendo, e avrebbe reso la tabella NON SCRIVIBILE.
-- Qui non puo' succedere — emittente_soggetto_ruolo_id e billing_account_id
-- sono in colonna e NOT NULL, quindi la WITH CHECK li legge da NEW — ma «non
-- puo' succedere» e' un ragionamento, e questi due sono la prova.
--
-- ⚠️ UN CONTEGGIO A ZERO NON E' UNA PROVA. La tabella e' vuota sul database di
-- sviluppo: qualunque misura sui dati esistenti darebbe lo stesso numero con e
-- senza policy — verde per sottrazione. Per questo la fixture COSTRUISCE l'atto
-- e lo guarda da due operatori di due emittenti diversi.
--
-- ⚠️ LIMITE DICHIARATO. Di ba_ownership si prova la sola direzione di NEGAZIONE
-- (test 10): una veste CLIENTE_PORTALE che non possiede il billing account non
-- vede l'atto. La direzione di CONCESSIONE pretende un'identita' portale legata
-- a quel billing account — fixture pesante, da aggiungere quando nascera' il
-- primo endpoint portale. E' la direzione meno critica: un falso negativo nega
-- un accesso legittimo, un falso positivo espone i dati di un altro cliente.
--
-- Piano: brief-db-fondo-fattura-ricalcolo-e-governo.md
--        §9.9 (G-2) · §9.3 D-20
-- ------------------------------------------------------------

BEGIN;

-- ⚠️ IL `SET CONSTRAINTS ALL IMMEDIATE` NON STA QUI IN TESTA, ed e' l'unico
--   file della slice in cui si sposta. Due ragioni, entrambe strutturali:
--     * i vincoli DIFFERITI vanno fatti scattare DOVE L'UNITA' DI LAVORO E'
--       COMPLETA, e qui la prima unita' e' «fattura + atto». Sta subito dopo;
--     * e deve stare PRIMA dell'`ALTER TABLE`: un `ALTER TABLE` su una tabella
--       con eventi trigger in sospeso e' rifiutato da PostgreSQL, e la prima
--       stesura di questo file falliva esattamente li' — nel FIXTURE, che vale
--       copertura ZERO e non «parziale».
--   ⚠️ Il soggetto dell'operatore si crea DOPO, di proposito:
--   anagrafiche.soggetti ha tre guard DEFERRABLE INITIALLY DEFERRED dove la
--   deferralita' e' il CONTRATTO del dominio (si crea il soggetto, poi il suo
--   indirizzo, e la completezza si verifica al COMMIT). Anticipando quella
--   fixture, l'IMMEDIATE pretenderebbe l'indirizzo nell'istante dell'INSERT e
--   vieterebbe il pattern che il dominio ha scelto. ⚠️ Resta un buco
--   dichiarato: quei tre guard, qui, non vengono esercitati — stesso debito del
--   gemello test-rls-fatture-satelliti-functional.sql.

SELECT plan(11);

-- ============================================================
-- Fixture — un atto COSTRUITO, e due emittenti distinti
-- ============================================================
CREATE TEMP TABLE _refs AS
WITH ba AS (
  SELECT b.id, b.utility_id, b.soggetto_ruolo_id
    FROM anagrafiche.billing_account b
   ORDER BY b.data_insert DESC NULLS LAST, b.id DESC
   LIMIT 1
), emit AS (
  SELECT m.emittente_soggetto_ruolo_id AS emit_sr
    FROM anagrafiche.emittenti_fiscali_billing_account m, ba
   WHERE (m.billing_account_id = ba.id OR m.is_default IS TRUE)
   ORDER BY CASE WHEN m.billing_account_id = ba.id THEN 0 ELSE 1 END, m.id
   LIMIT 1
)
SELECT ba.id                AS billing_account_id,
       ba.utility_id        AS utility_id,
       emit.emit_sr         AS emit_sr,
       (SELECT ef.id FROM anagrafiche.emittenti_fiscali ef
         WHERE ef.soggetto_ruolo_id = emit.emit_sr ORDER BY ef.id LIMIT 1)  AS emit_pk,
       (SELECT ef.id FROM anagrafiche.emittenti_fiscali ef
         WHERE ef.soggetto_ruolo_id IS DISTINCT FROM emit.emit_sr
         ORDER BY ef.id LIMIT 1)                                            AS other_pk,
       (SELECT id FROM config.tipi_doc_fiscale WHERE attivo IS TRUE ORDER BY id LIMIT 1) AS tipo_doc_fiscale_id,
       (SELECT id FROM config.valute ORDER BY id LIMIT 1)                   AS valuta_id,
       (SELECT t.id FROM vendite.tipi_fondi_fattura t
         WHERE t.attivo IS TRUE AND t.codice_interno = 'F_F_ADD_ACC'
         ORDER BY t.id LIMIT 1)                                             AS tipo_fondo_id,
       script.fn_pgtap_registro_fattura(anagrafiche.fn_get_emittente_fiscale_id(ba.id)) AS registro_id
  FROM ba, emit;

-- La fattura sorgente e l'atto si creano PRIMA di armare la RLS: da owner senza
-- FORCE nessuna policy filtra, quindi la fixture non deve indovinare la
-- whitelist con cui costruire.
CREATE TEMP TABLE _src AS
WITH ins AS (
  INSERT INTO vendite.fatture (
      registro_id, data, emittente_soggetto_ruolo_id, billing_account_id,
      tipo_doc_fiscale_id, valuta_id, utility_id, minimo, totale_a_pagare, meta)
  SELECT r.registro_id, current_date, r.emit_sr, r.billing_account_id,
         r.tipo_doc_fiscale_id, r.valuta_id, r.utility_id, true, 100.00,
         jsonb_build_object('test_scope', 'pgtap_rls_fondi_source')
    FROM _refs r
  RETURNING id
)
SELECT * FROM ins;

CREATE TEMP TABLE _atto AS
WITH ins AS (
  INSERT INTO vendite.fatture_fondi_fattura_source (
      fattura_sorgente_id, tipo_fondo_fattura_id, importo, stato,
      billing_account_id, utility_id, tipo_doc_fiscale_id,
      emittente_soggetto_ruolo_id, valuta_id, origine, motivo)
  SELECT (SELECT id FROM _src), r.tipo_fondo_id, 10.00, 'DISPONIBILE',
         r.billing_account_id, r.utility_id, r.tipo_doc_fiscale_id,
         r.emit_sr, r.valuta_id, 'MANUALE', 'atto di prova RLS'
    FROM _refs r
  RETURNING id
)
SELECT id AS source_id FROM ins;

-- ⚠️ L'unita' di lavoro «fattura + atto» e' completa: qui i vincoli differiti
--   devono scattare. In coda al file scatterebbero su righe gia' rimosse, e
--   prima dell'ALTER TABLE ci devono stare per forza.
SET CONSTRAINTS ALL IMMEDIATE;

-- COALESCE garantisce SEMPRE una riga booleana (anche con _refs vuota).
CREATE TEMP TABLE _flags AS
SELECT COALESCE((SELECT source_id IS NOT NULL FROM _atto LIMIT 1), false)
       AND COALESCE((SELECT emit_pk IS NOT NULL AND other_pk IS NOT NULL AND emit_pk <> other_pk
                       FROM _refs LIMIT 1), false) AS prereq;

SELECT ok(
  (SELECT prereq FROM _flags),
  '1) Riferimenti minimi presenti: l''atto e'' costruito, e i due emittenti sono diversi'
);

-- ⭐ Arma la RLS solo dentro questa transazione: FORCE assoggetta anche l'owner
--   (titodb, non-superuser) senza SET ROLE, che titodb non potrebbe fare.
--   ⚠️ Il changeSet 20260831-62 fa l'ENABLE ma NON il FORCE, come tutta la
--   famiglia: qui il FORCE e' l'attrezzo del test, non la configurazione.
ALTER TABLE vendite.fatture_fondi_fattura_source ENABLE ROW LEVEL SECURITY;
ALTER TABLE vendite.fatture_fondi_fattura_source FORCE  ROW LEVEL SECURITY;

-- ⚠️ E ORA SI TORNA A `DEFERRED`, ed e' una riga che va letta invece che
--   saltata. `SET CONSTRAINTS ALL IMMEDIATE` vale per il RESTO della
--   transazione, non per l'istruzione che lo precede: lasciandolo acceso, la
--   fixture dell'operatore qui sotto morirebbe sui tre guard di
--   anagrafiche.soggetti, dove la deferralita' e' il CONTRATTO del dominio (si
--   crea il soggetto, poi il suo indirizzo, e la completezza si verifica al
--   COMMIT).
-- ⚠️ Il prezzo e' dichiarato: quei tre guard, in questo file, non vengono
--   esercitati. Non e' una svista ed e' lo stesso debito del gemello
--   test-rls-fatture-satelliti-functional.sql; si chiude COMPLETANDO la
--   fixture (indirizzo + contatti), non togliendo questa riga.
SET CONSTRAINTS ALL DEFERRED;

-- auth_user + soggetto PF + SR RIS_UMANA + identita OPERATORE attiva.
CREATE TEMP TABLE _op (auth_user_id int, soggetto_id uuid, sr_id bigint, identita_id bigint);

DO $fix$
DECLARE
    v_uid int;
    v_sog uuid;
    v_sr  bigint;
    v_idn bigint;
BEGIN
    INSERT INTO django.auth_user (username, password, is_active, is_staff,
        is_superuser, first_name, last_name, email, date_joined)
    VALUES ('_pgtap_rls_fondo_' || substring(md5(clock_timestamp()::text) from 1 for 8),
        '!', true, false, false, '', '', '', now())
    RETURNING id INTO v_uid;

    -- CF/anagrafica identici agli altri test RLS (gia' validati): ogni test
    -- gira in transazione propria con rollback, nessuna collisione.
    v_sog := anagrafiche.fn_crea_soggetto_pf(
        p_cognome           := 'PnzTestScopeEf',
        p_nome              := 'Fdn',
        p_codice_fiscale    := 'PNZFDN78A01L219Y',
        p_email             := 'pgtap_rls_fondo_' || substring(md5(clock_timestamp()::text) from 1 for 6) || '@test.local',
        p_data_nascita      := DATE '1978-01-01',
        p_sesso             := 'M',
        p_stato_iso2        := 'IT',
        p_comune_nascita_id := (SELECT id FROM config.comuni ORDER BY id LIMIT 1),
        p_tipo_contatto_id  := NULL);

    v_sr := script.fn_get_or_create_soggetto_ruolo(
        p_soggetto_id  := v_sog,
        p_cd_int_ruolo := 'RIS_UMANA');

    INSERT INTO anagrafiche.identita_digitali
        (soggetto_ruolo_id, auth_user_id, ruolo_applicativo, attivo)
    VALUES (v_sr, v_uid, 'OPERATORE', true)
    RETURNING id INTO v_idn;

    INSERT INTO _op VALUES (v_uid, v_sog, v_sr, v_idn);
END
$fix$;


CREATE TEMP TABLE _res (caso text, esito boolean, n bigint);

-- Helper: imposta la sessione operatore con la whitelist indicata.
-- ⚠️ L'override sul DELETE non e' decorativo: config.user_emittenti_fiscali e'
--   protetta da trgfn_user_emittenti_fiscali_guard_delete, che ammette la
--   cancellazione solo su utente cessato o con la GUC di manutenzione. Senza,
--   il file fallirebbe nel FIXTURE — e un file che fallisce nel fixture non
--   esegue nessuna asserzione: la sua copertura vale zero, non «parziale».
-- ⚠️ Il parametro e' un discriminante testuale e non la PK: PostgreSQL non
--   ammette sottoquery negli argomenti di CALL.
CREATE OR REPLACE PROCEDURE pg_temp.set_op(p_quale text)
LANGUAGE plpgsql AS $sp$
DECLARE
    v_emit bigint;
BEGIN
    v_emit := CASE p_quale
                  WHEN 'own'   THEN (SELECT emit_pk  FROM _refs)
                  WHEN 'other' THEN (SELECT other_pk FROM _refs)
                  ELSE NULL
              END;

    PERFORM set_config('zeroerp.allow_user_emittente_delete_override', 'on', true);
    DELETE FROM config.user_emittenti_fiscali
     WHERE auth_user_id = (SELECT auth_user_id FROM _op);
    PERFORM set_config('zeroerp.allow_user_emittente_delete_override', '', true);

    IF v_emit IS NOT NULL THEN
        INSERT INTO config.user_emittenti_fiscali (auth_user_id, emittente_fiscale_id)
        VALUES ((SELECT auth_user_id FROM _op), v_emit) ON CONFLICT DO NOTHING;
    END IF;

    PERFORM set_config('app.ruolo_applicativo', 'OPERATORE', true);
    PERFORM set_config('app.current_user_id', (SELECT auth_user_id FROM _op)::text, true);
END
$sp$;

-- ============================================================
-- ⭐ Le asserzioni stanno ACCANTO al loro caso, non tutte in fondo
-- ============================================================
-- ⚠️ Un errore dentro un `DO` interrompe la transazione, e da li' in poi non
--   stampa piu' niente. Con le asserzioni raccolte in coda, un guasto al
--   penultimo caso azzererebbe anche la diagnostica dei primi — «fallisce nel
--   fixture» e «fallisce all'ultimo passo» si leggerebbero uguali. Accanto al
--   caso, invece, quello che ha gia' risposto resta scritto.

-- ---- Caso 2: whitelist VUOTA -> fail-closed ----
DO $c2$
BEGIN
    IF NOT (SELECT prereq FROM _flags) THEN RETURN; END IF;
    CALL pg_temp.set_op('none');
    INSERT INTO _res SELECT 'c2', EXISTS (
        SELECT 1 FROM vendite.fatture_fondi_fattura_source
         WHERE id = (SELECT source_id FROM _atto)), NULL;
END $c2$;

SELECT is(
  (SELECT esito FROM _res WHERE caso = 'c2'), false,
  '2) whitelist VUOTA: l''atto NON e'' visibile (fail-closed)'
);

-- ---- Caso 3: whitelist = emittente dell'atto -> visibile ----
DO $c3$
BEGIN
    IF NOT (SELECT prereq FROM _flags) THEN RETURN; END IF;
    CALL pg_temp.set_op('own');
    INSERT INTO _res SELECT 'c3', EXISTS (
        SELECT 1 FROM vendite.fatture_fondi_fattura_source
         WHERE id = (SELECT source_id FROM _atto)), NULL;
END $c3$;

SELECT is(
  (SELECT esito FROM _res WHERE caso = 'c3'), true,
  '3) whitelist = emittente dell''atto: visibile'
);

-- ---- Caso 4: whitelist = ALTRO emittente -> NON visibile ----
DO $c4$
BEGIN
    IF NOT (SELECT prereq FROM _flags) THEN RETURN; END IF;
    CALL pg_temp.set_op('other');
    INSERT INTO _res SELECT 'c4', EXISTS (
        SELECT 1 FROM vendite.fatture_fondi_fattura_source
         WHERE id = (SELECT source_id FROM _atto)), NULL;
END $c4$;

SELECT is(
  (SELECT esito FROM _res WHERE caso = 'c4'), false,
  '4) whitelist = ALTRO emittente: NON visibile'
);

-- ---- Caso 5: ruolo NON OPERATORE -> il cancello della policy ----
DO $c5$
BEGIN
    IF NOT (SELECT prereq FROM _flags) THEN RETURN; END IF;
    CALL pg_temp.set_op('own');
    PERFORM set_config('app.ruolo_applicativo', '', true);
    INSERT INTO _res SELECT 'c5', EXISTS (
        SELECT 1 FROM vendite.fatture_fondi_fattura_source
         WHERE id = (SELECT source_id FROM _atto)), NULL;
END $c5$;

SELECT is(
  (SELECT esito FROM _res WHERE caso = 'c5'), false,
  '5) ruolo non OPERATORE: NON visibile — e'' il cancello della policy'
);

-- ---- Casi 6 e 7: FOR ALL, non FOR SELECT ----
-- ⚠️ Si scrive `motivo`, che nessun lock di colonna protegge: `importo`,
--   `fattura_sorgente_id`, `tipo_fondo_fattura_id` e `origine` sono immutabili
--   dopo l'INSERT (E_FONDO_ATTO_IMMUTABILE), e usarli farebbe fallire il test
--   per il motivo sbagliato.
DO $c6$
DECLARE v_n bigint;
BEGIN
    IF NOT (SELECT prereq FROM _flags) THEN RETURN; END IF;
    CALL pg_temp.set_op('own');
    WITH upd AS (
        UPDATE vendite.fatture_fondi_fattura_source
           SET motivo = 'atto di prova RLS (in scope)'
         WHERE id = (SELECT source_id FROM _atto)
        RETURNING id)
    SELECT count(*) INTO v_n FROM upd;
    INSERT INTO _res SELECT 'c6', v_n = 1, v_n;
END $c6$;

SELECT is(
  (SELECT esito FROM _res WHERE caso = 'c6'), true,
  '6) ⭐ ef_whitelist e'' FOR ALL: in scope la scrittura passa'
);

DO $c7$
DECLARE v_n bigint;
BEGIN
    IF NOT (SELECT prereq FROM _flags) THEN RETURN; END IF;
    CALL pg_temp.set_op('other');
    WITH upd AS (
        UPDATE vendite.fatture_fondi_fattura_source
           SET motivo = 'atto di prova RLS (fuori scope)'
         WHERE id = (SELECT source_id FROM _atto)
        RETURNING id)
    SELECT count(*) INTO v_n FROM upd;
    INSERT INTO _res SELECT 'c7', v_n = 0, v_n;
END $c7$;

SELECT is(
  (SELECT esito FROM _res WHERE caso = 'c7'), true,
  '7) ...e fuori scope non tocca niente'
);

-- ---- Casi 8 e 9: la WITH CHECK legge da NEW ----
-- ⭐ E' la prova che la tabella resta SCRIVIBILE: se la WITH CHECK cercasse il
--   legame invece di leggerlo dalla riga, l'INSERT in scope fallirebbe e il
--   riporto di pagamenti.fn_conferma_sistemazione si fermerebbe.
DO $c8$
DECLARE v_n bigint;
BEGIN
    IF NOT (SELECT prereq FROM _flags) THEN RETURN; END IF;
    CALL pg_temp.set_op('own');
    WITH ins AS (
        INSERT INTO vendite.fatture_fondi_fattura_source (
            fattura_sorgente_id, tipo_fondo_fattura_id, importo, stato,
            billing_account_id, utility_id, tipo_doc_fiscale_id,
            emittente_soggetto_ruolo_id, valuta_id, origine, motivo)
        SELECT (SELECT id FROM _src), r.tipo_fondo_id, 5.00, 'DISPONIBILE',
               r.billing_account_id, r.utility_id, r.tipo_doc_fiscale_id,
               r.emit_sr, r.valuta_id, 'MANUALE', 'insert in scope'
          FROM _refs r
        RETURNING id)
    SELECT count(*) INTO v_n FROM ins;
    INSERT INTO _res SELECT 'c8', v_n = 1, v_n;
END $c8$;

SELECT is(
  (SELECT esito FROM _res WHERE caso = 'c8'), true,
  '8) ⭐ La WITH CHECK legge da NEW: un INSERT in scope PASSA'
);

-- ---- Caso 9: la WITH CHECK rifiuta fuori scope ----
-- 🔴 IL CONTESTO SI RIMETTE QUI, E NON E' PIGRIZIA. Alla prima stesura questo
--   blocco stava in fondo al file, dopo il caso 10 — che lascia la sessione in
--   veste CLIENTE_PORTALE. L'INSERT falliva davvero, ma per il ruolo sbagliato:
--   il test era VERDE e collaudava una cosa diversa da quella che dichiarava.
--   Con `set_op('other')` l'operatore c'e', ed e' l'EMITTENTE a non tornare.
-- ⚠️ throws_ok con lo SQLSTATE: 42501 e' il rifiuto della POLICY. Senza,
--   passerebbe anche un errore di vincolo, che direbbe un'altra cosa.
CALL pg_temp.set_op('other');

SELECT throws_ok(
  format($sql$
    INSERT INTO vendite.fatture_fondi_fattura_source (
        fattura_sorgente_id, tipo_fondo_fattura_id, importo, stato,
        billing_account_id, utility_id, tipo_doc_fiscale_id,
        emittente_soggetto_ruolo_id, valuta_id, origine, motivo)
    SELECT %s, r.tipo_fondo_id, 5.00, 'DISPONIBILE',
           r.billing_account_id, r.utility_id, r.tipo_doc_fiscale_id,
           r.emit_sr, r.valuta_id, 'MANUALE', 'insert fuori scope'
      FROM _refs r
  $sql$, (SELECT id FROM _src)),
  '42501', NULL,
  '9) ...e un INSERT fuori scope e'' rifiutato dalla policy'
);


-- ---- Caso 10: veste CLIENTE_PORTALE non proprietaria ----
DO $c10$
BEGIN
    IF NOT (SELECT prereq FROM _flags) THEN RETURN; END IF;
    PERFORM set_config('app.ruolo_applicativo', 'CLIENTE_PORTALE', true);
    PERFORM set_config('app.current_identita_id', (SELECT identita_id FROM _op)::text, true);
    INSERT INTO _res SELECT 'c10', EXISTS (
        SELECT 1 FROM vendite.fatture_fondi_fattura_source
         WHERE id = (SELECT source_id FROM _atto)), NULL;
    PERFORM set_config('app.current_identita_id', '', true);
END $c10$;

SELECT is(
  (SELECT esito FROM _res WHERE caso = 'c10'), false,
  '10) veste CLIENTE_PORTALE non proprietaria: NON visibile'
);

-- ---- Caso 11: il giro notturno attraversa ----
-- ⭐ E' la seconda delle tre verifiche che §9.9-d dichiara «da fare, non da
--   dedurre»: fn_genera_fondi_fattura_source e fn_applica_fondi_fattura girano
--   nel contesto batch, e se quel ruolo perdesse BYPASSRLS la RLS appena accesa
--   fermerebbe il giro — e lo si vedrebbe SOLO LA MATTINA DOPO.
-- ⛔ Qui NON c'e' il kill-switch (`NO FORCE`) che hanno i test RLS gemelli, e
--   non e' una dimenticanza: un ALTER TABLE su una tabella con eventi trigger
--   differiti in sospeso — quelli lasciati dall'INSERT del caso 8 — e' rifiutato
--   da PostgreSQL. E qui non serve: il kill-switch esiste per distinguere «la
--   policy filtra» da «la riga non c'e'», e a dirlo basta il caso 3, che la
--   stessa riga la VEDE in scope. Nel gemello sui satelliti serviva perche' li'
--   la fixture usa una fattura ESISTENTE.
SELECT ok(
  (SELECT r.rolbypassrls FROM pg_roles r WHERE r.rolname = 'zeroerp_batch_fatturazione'),
  '11) ⭐ Il giro notturno attraversa: zeroerp_batch_fatturazione ha BYPASSRLS'
);

SELECT * FROM finish();
ROLLBACK;
