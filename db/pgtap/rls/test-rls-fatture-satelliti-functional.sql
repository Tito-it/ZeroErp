-- ------------------------------------------------------------
-- SPDX-License-Identifier: GPL-3.0-or-later
-- pgtap-differiti: escluso — la fixture non soddisfa un vincolo DIFFERITO e la
--   ragione e' scritta per esteso piu' sotto. Debito noto (§22.4): quando la
--   fixture viene completata, si toglie questa riga e si rimette il
--   SET CONSTRAINTS ALL IMMEDIATE nel punto in cui l'unita' di lavoro e' completa.
-- pgtap-contesto: escluso — la ragione e' scritta per esteso piu' sotto in
--   questo stesso file. Dichiarazione leggibile dal cancello
--   scripts/guardrail_pgtap_preambolo.py: distingue «escluso apposta» da
--   «dimenticato», che una nota in prosa non fa.
--   ⚠️ Da riguardare: le esclusioni `rls/` furono fatte IN BLOCCO, e almeno
--   una non ne aveva diritto (brief pgtap-runner-rls-baseline §30.2).
-- pgtap-runner: owner
-- pgtap-runner-motivo: ALTER TABLE vendite.fatture_righe / fatture_riepiloghi_iva ENABLE + FORCE ROW
--   LEVEL SECURITY, locale alla transazione: e' il FORCE a rendere l'owner
--   soggetto alle policy.
-- pgTAP test FUNZIONALE RLS — satelliti fattura
--   vendite.fatture_righe + vendite.fatture_riepiloghi_iva
--   (policy ef_whitelist e ba_ownership, changeset 20260729-01..05)
--
-- PERCHE' FUNZIONALE E NON STRUTTURALE. Queste quattro policy sono
-- PRE-ARMATE: proteggono il portale fatture, che ancora non esiste. Una
-- policy mai esercitata sembra funzionare finche' non la si prova, e chi
-- scrivera' il portale si fidera' di lei senza rileggerla. La verifica
-- "applicativa" non arrivera' mai, perche' l'applicazione non c'e': quindi
-- deve arrivare qui.
--
-- MECCANISMO (identico a test-rls-fatture-ef-whitelist-functional.sql):
--   - ENABLE + FORCE ROW LEVEL SECURITY locali alla transazione. FORCE
--     assoggetta anche l'owner (titodb, non-superuser) senza SET ROLE, che
--     titodb non potrebbe fare. Il ROLLBACK finale annulla tutto.
--   - GUC simulati con set_config(..., is_local => true).
--   - Fixture LOW-RISK: usa una fattura ESISTENTE, non ne crea (FK pesanti).
--     Se il DB non ne ha una idonea -> SOFT-SKIP (i test passano banalmente),
--     cosi' la CI su DB senza dati non rompe.
--
-- ⭐ IL TEST CHE CONTA sono il 5 e l'8, non i primi quattro. Verificano
-- l'INVARIANTE su cui poggia tutta la slice: il filtro e' TUTTO-O-NIENTE PER
-- FATTURA. Serve perche' tre funzioni SECURITY INVOKER non leggono le righe,
-- le CONTANO o le SOMMANO — fn_assign_numero_fattura (guard
-- E_FATTURA_SENZA_RIGHE), fn_ricalcola_riepilogo_iva_fattura (ricostruisce il
-- riepilogo) e fn_cleanup_fatture_by_ids. La RLS non da' errore: restituisce
-- MENO RIGHE, e una somma incompleta diventa un riepilogo IVA sbagliato che
-- nessuno segnala. Finche' le policy condividono la funzione di scope della
-- TESTATA, chi vede la fattura vede tutte le sue righe e i conti tornano.
-- Se qualcuno un giorno le facesse divergere, il 5 e l'8 diventerebbero rossi
-- prima che il danno arrivi in un documento fiscale.
--
-- SCRITTURA (test 9-10): dimostra che ef_whitelist e' FOR ALL e non FOR
-- SELECT. Con la sola SELECT ogni scrittura operatore fallirebbe, anche
-- in-scope, e il giro di fatturazione si bloccherebbe all'armamento — e' la
-- lezione dell'Ondata 2 (20260603-16..25), pagata una volta.
-- UPDATE no-op su `meta`: `meta` non e' fra le colonne-input protette dal
-- guard di congelamento (qta, prezzo_unitario, sconto_percentuale, iva_id),
-- ma quel guard rifiuta comunque OGNI scrittura su una fattura oltre
-- DRAFT/EMESSA -> la fixture preferisce una fattura in quegli stati e i due
-- test si auto-skippano se non ne esiste.
--
-- ⚠️ LIMITE DICHIARATO. Di ba_ownership si prova qui la sola direzione di
-- NEGAZIONE (test 12): una veste CLIENTE_PORTALE che NON possiede la fattura
-- non ne vede le righe. La direzione di CONCESSIONE (il cliente vede le
-- proprie) richiede un'identita' portale legata al billing account della
-- fattura — fixture pesante, da aggiungere quando nascera' il primo endpoint
-- portale, che quella catena la costruira' comunque. E' la direzione meno
-- critica: un falso negativo nega un accesso legittimo, un falso positivo
-- espone i dati di un altro cliente.
-- ------------------------------------------------------------
-- Indice test (1..12):
--   1   righe: operatore whitelist VUOTA          -> visibili (accesso globale)
--   2   righe: whitelist = emittente fattura      -> visibili
--   3   righe: whitelist = ALTRO emittente        -> NON visibili
--   4   righe: ruolo non OPERATORE                -> NON visibili (gate)
--   5   ⭐ righe: TUTTO-O-NIENTE — in scope il count RLS = count reale
--   6   riepiloghi: whitelist = emittente         -> visibili
--   7   riepiloghi: whitelist = ALTRO emittente   -> NON visibili
--   8   ⭐ riepiloghi: TUTTO-O-NIENTE
--   9   scrittura in-scope (FOR ALL)              -> 1 riga aggiornata
--  10   scrittura off-scope                       -> 0 righe
--  11   DISABLE RLS (kill-switch)                 -> di nuovo visibili
--  12   veste CLIENTE_PORTALE non proprietaria    -> NON visibili
-- ------------------------------------------------------------

BEGIN;
-- ⚠️ QUESTO FILE NON USA `SET CONSTRAINTS ALL IMMEDIATE`, a differenza degli
--   altri, e non e' una dimenticanza.
--   `anagrafiche.soggetti` ha TRE guard DEFERRABLE INITIALLY DEFERRED —
--   indirizzi, contatti, dati societari — e li' la deferralita' e' il CONTRATTO
--   DEL DOMINIO: si crea il soggetto, poi il suo indirizzo, e la completezza si
--   verifica al COMMIT. E' per questo che anagrafiche.fn_crea_soggetto_pf puo'
--   restituire un soggetto ancora incompleto, ed e' cosi' che la usa il backend.
--   Forzare IMMEDIATE pretenderebbe l'indirizzo nell'istante stesso dell'INSERT
--   del soggetto: vieterebbe il pattern che il dominio ha scelto.
--   ⚠️ Resta un buco reale: senza la riga quei guard non vengono esercitati da
--   questo test, e la fixture lascia un soggetto che l'applicazione non
--   potrebbe committare. La correzione vera e' COMPLETARE LA FIXTURE
--   (indirizzo + contatti): allora la riga si rimette e il test verifica sul
--   serio. Brief: brief-db-pgtap-runner-rls-baseline §21.

SELECT plan(12);

-- =========================================================
-- Fixture: fattura esistente CON righe e riepiloghi + 2 emittenti + operatore
-- =========================================================
-- Requisiti della fattura scelta: emittente risolvibile (evita righe legacy
-- con emittente_soggetto_ruolo_id orfano), almeno una riga e almeno un
-- riepilogo IVA. Ordinamento che PREFERISCE DRAFT/EMESSA: sono gli unici
-- stati in cui il guard di congelamento lascia scrivere, e i test 9-10 ne
-- hanno bisogno. Se non ce n'e' nessuna, si ripiega su un'altra e i due test
-- di scrittura si skippano da soli.
CREATE TEMP TABLE _refs AS
WITH f AS (
    SELECT fa.id                          AS fattura_id,
           fa.emittente_soggetto_ruolo_id AS emit_sr,
           ef.id                           AS emit_pk,
           (s.codice_interno IN ('DRAFT', 'EMESSA')) AS scrivibile
      FROM vendite.fatture fa
      JOIN anagrafiche.emittenti_fiscali ef
        ON ef.soggetto_ruolo_id = fa.emittente_soggetto_ruolo_id
      JOIN config.stati_doc_fiscale s
        ON s.id = fa.stato_doc_fiscale_id
     WHERE EXISTS (SELECT 1 FROM vendite.fatture_righe fr WHERE fr.fattura_id = fa.id)
       AND EXISTS (SELECT 1 FROM vendite.fatture_riepiloghi_iva ri WHERE ri.fattura_id = fa.id)
     ORDER BY (s.codice_interno IN ('DRAFT', 'EMESSA')) DESC, fa.id
     LIMIT 1
)
SELECT
    f.fattura_id,
    f.emit_sr,
    f.emit_pk,
    f.scrivibile,
    (SELECT ef.id FROM anagrafiche.emittenti_fiscali ef
      WHERE ef.id <> f.emit_pk
      ORDER BY ef.id LIMIT 1)                       AS other_pk,
    -- Conteggi REALI, presi da owner PRIMA di armare la RLS: sono il metro
    -- dei test 5 e 8. Presi dopo, sarebbero gia' filtrati e il confronto
    -- misurerebbe se' stesso.
    (SELECT count(*) FROM vendite.fatture_righe fr
      WHERE fr.fattura_id = f.fattura_id)           AS n_righe_reali,
    (SELECT count(*) FROM vendite.fatture_riepiloghi_iva ri
      WHERE ri.fattura_id = f.fattura_id)           AS n_riep_reali
  FROM f;

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
    VALUES ('_pgtap_rls_sat_' || substring(md5(clock_timestamp()::text) from 1 for 8),
        '!', true, false, false, '', '', '', now())
    RETURNING id INTO v_uid;

    -- CF/anagrafica identici agli altri test RLS (gia' validati): ogni test
    -- gira in transazione propria con rollback, nessuna collisione.
    v_sog := anagrafiche.fn_crea_soggetto_pf(
        p_cognome           := 'PnzTestScopeEf',
        p_nome              := 'Fdn',
        p_codice_fiscale    := 'PNZFDN78A01L219Y',
        p_email             := 'pgtap_rls_sat_' || substring(md5(clock_timestamp()::text) from 1 for 6) || '@test.local',
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

-- COALESCE garantisce SEMPRE una riga booleana (anche con _refs vuota).
CREATE TEMP TABLE _flags AS
SELECT
  COALESCE((SELECT fattura_id IS NOT NULL AND emit_pk IS NOT NULL AND other_pk IS NOT NULL
              FROM _refs LIMIT 1), false)                              AS prereq,
  COALESCE((SELECT scrivibile FROM _refs LIMIT 1), false)              AS prereq_write;

-- Arma la RLS solo dentro questa transazione (FORCE assoggetta l'owner).
ALTER TABLE vendite.fatture_righe          ENABLE ROW LEVEL SECURITY;
ALTER TABLE vendite.fatture_righe          FORCE  ROW LEVEL SECURITY;
ALTER TABLE vendite.fatture_riepiloghi_iva ENABLE ROW LEVEL SECURITY;
ALTER TABLE vendite.fatture_riepiloghi_iva FORCE  ROW LEVEL SECURITY;

CREATE TEMP TABLE _res (caso text, visibile boolean, n bigint);

-- Helper: imposta la sessione operatore con la whitelist indicata.
-- (procedura locale: evita 10 ripetizioni degli stessi 4 statement)
--
-- ⚠️ L'override sul DELETE non e' decorativo. config.user_emittenti_fiscali e'
-- protetta da trgfn_user_emittenti_fiscali_guard_delete (20260408-17), che
-- ammette la cancellazione SOLO se django.auth_user.is_active = false
-- (cessazione utente) oppure con la GUC di manutenzione. Il test gemello
-- test-rls-fatture-ef-whitelist-functional.sql cancella senza override ed e'
-- per questo rosso in baseline come ERRORE_FIXTURE: fallisce nel fixture,
-- quindi non esegue NESSUNA asserzione e la sua copertura vale zero. Qui
-- l'override c'e', ed e' locale alla transazione.
-- Il parametro e' un DISCRIMINANTE testuale ('none' | 'own' | 'other') e non
-- la PK dell'emittente, perche' PostgreSQL non ammette sottoquery negli
-- argomenti di CALL: passare `(SELECT emit_pk FROM _refs)` fallisce con
-- «non e' possibile usare sottoquery in argomenti CALL». Risolvendo la PK
-- dentro la procedura i punti di chiamata restano letterali — e si leggono
-- anche meglio.
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

-- ---- Caso 1: whitelist VUOTA -> righe visibili (accesso globale) ----
DO $c1$
BEGIN
    IF NOT (SELECT prereq FROM _flags) THEN RETURN; END IF;
    CALL pg_temp.set_op('none');
    INSERT INTO _res SELECT 'c1', EXISTS (
        SELECT 1 FROM vendite.fatture_righe WHERE fattura_id = (SELECT fattura_id FROM _refs)), NULL;
END $c1$;

-- ---- Caso 2 + 5: whitelist = emittente della fattura -> visibili, e TUTTE ----
DO $c2$
BEGIN
    IF NOT (SELECT prereq FROM _flags) THEN RETURN; END IF;
    CALL pg_temp.set_op('own');
    INSERT INTO _res
    SELECT 'c2',
           count(*) > 0,
           count(*)
      FROM vendite.fatture_righe WHERE fattura_id = (SELECT fattura_id FROM _refs);
END $c2$;

-- ---- Caso 3: whitelist = ALTRO emittente -> NON visibili ----
DO $c3$
BEGIN
    IF NOT (SELECT prereq FROM _flags) THEN RETURN; END IF;
    CALL pg_temp.set_op('other');
    INSERT INTO _res SELECT 'c3', EXISTS (
        SELECT 1 FROM vendite.fatture_righe WHERE fattura_id = (SELECT fattura_id FROM _refs)), NULL;
END $c3$;

-- ---- Caso 4: ruolo NON OPERATORE (gate della policy) -> NON visibili ----
DO $c4$
BEGIN
    IF NOT (SELECT prereq FROM _flags) THEN RETURN; END IF;
    CALL pg_temp.set_op('own');
    PERFORM set_config('app.ruolo_applicativo', '', true);
    INSERT INTO _res SELECT 'c4', EXISTS (
        SELECT 1 FROM vendite.fatture_righe WHERE fattura_id = (SELECT fattura_id FROM _refs)), NULL;
END $c4$;

-- ---- Caso 6 + 8: riepiloghi IVA in scope -> visibili, e TUTTI ----
DO $c6$
BEGIN
    IF NOT (SELECT prereq FROM _flags) THEN RETURN; END IF;
    CALL pg_temp.set_op('own');
    INSERT INTO _res
    SELECT 'c6', count(*) > 0, count(*)
      FROM vendite.fatture_riepiloghi_iva WHERE fattura_id = (SELECT fattura_id FROM _refs);
END $c6$;

-- ---- Caso 7: riepiloghi IVA fuori scope -> NON visibili ----
DO $c7$
BEGIN
    IF NOT (SELECT prereq FROM _flags) THEN RETURN; END IF;
    CALL pg_temp.set_op('other');
    INSERT INTO _res SELECT 'c7', EXISTS (
        SELECT 1 FROM vendite.fatture_riepiloghi_iva
         WHERE fattura_id = (SELECT fattura_id FROM _refs)), NULL;
END $c7$;

-- ---- Caso 9: SCRITTURA in-scope -> la policy FOR ALL la consente ----
DO $c9$
DECLARE v_n bigint;
BEGIN
    IF NOT (SELECT prereq AND prereq_write FROM _flags) THEN RETURN; END IF;
    CALL pg_temp.set_op('own');
    -- No-op su `meta`: non tocca le colonne-input del guard di congelamento.
    UPDATE vendite.fatture_righe SET meta = meta
     WHERE fattura_id = (SELECT fattura_id FROM _refs);
    GET DIAGNOSTICS v_n = ROW_COUNT;
    INSERT INTO _res SELECT 'c9', v_n > 0, v_n;
END $c9$;

-- ---- Caso 10: SCRITTURA off-scope -> USING nasconde le righe, 0 aggiornate ----
DO $c10$
DECLARE v_n bigint;
BEGIN
    IF NOT (SELECT prereq AND prereq_write FROM _flags) THEN RETURN; END IF;
    CALL pg_temp.set_op('other');
    UPDATE vendite.fatture_righe SET meta = meta
     WHERE fattura_id = (SELECT fattura_id FROM _refs);
    GET DIAGNOSTICS v_n = ROW_COUNT;
    INSERT INTO _res SELECT 'c10', v_n > 0, v_n;
END $c10$;

-- ---- Caso 12: veste CLIENTE_PORTALE non proprietaria -> NON visibili ----
-- L'identita' e' quella dell'operatore di test, che non possiede alcun
-- billing account: ba_ownership deve negare. Direzione di negazione, cioe'
-- quella che protegge i dati di un altro cliente (vedi limite in testa).
DO $c12$
BEGIN
    IF NOT (SELECT prereq FROM _flags) THEN RETURN; END IF;
    PERFORM set_config('app.ruolo_applicativo', 'CLIENTE_PORTALE', true);
    PERFORM set_config('app.current_identita_id', (SELECT identita_id FROM _op)::text, true);
    PERFORM set_config('app.current_user_id', '', true);
    INSERT INTO _res SELECT 'c12', EXISTS (
        SELECT 1 FROM vendite.fatture_righe WHERE fattura_id = (SELECT fattura_id FROM _refs)), NULL;
    PERFORM set_config('app.current_identita_id', '', true);
END $c12$;

-- ---- Caso 11: DISABLE RLS (kill-switch) -> di nuovo visibili ----
ALTER TABLE vendite.fatture_righe          NO FORCE ROW LEVEL SECURITY;
ALTER TABLE vendite.fatture_righe          DISABLE  ROW LEVEL SECURITY;
ALTER TABLE vendite.fatture_riepiloghi_iva NO FORCE ROW LEVEL SECURITY;
ALTER TABLE vendite.fatture_riepiloghi_iva DISABLE  ROW LEVEL SECURITY;
INSERT INTO _res
SELECT 'c11', EXISTS (
    SELECT 1 FROM vendite.fatture_righe WHERE fattura_id = (SELECT fattura_id FROM _refs)), NULL;

-- =========================================================
-- Asserzioni (soft-skip: NOT prereq -> pass banale)
-- =========================================================
SELECT ok((SELECT NOT prereq FROM _flags) OR     (SELECT visibile FROM _res WHERE caso='c1'),
    '1. righe: operatore whitelist vuota -> visibili (accesso globale)');
SELECT ok((SELECT NOT prereq FROM _flags) OR     (SELECT visibile FROM _res WHERE caso='c2'),
    '2. righe: whitelist = emittente fattura -> visibili');
SELECT ok((SELECT NOT prereq FROM _flags) OR NOT (SELECT visibile FROM _res WHERE caso='c3'),
    '3. righe: whitelist = altro emittente -> NON visibili');
SELECT ok((SELECT NOT prereq FROM _flags) OR NOT (SELECT visibile FROM _res WHERE caso='c4'),
    '4. righe: ruolo non OPERATORE -> NON visibili (gate policy)');

-- ⭐ L'invariante: in scope si vedono TUTTE le righe, non una parte.
SELECT ok((SELECT NOT prereq FROM _flags) OR
          (SELECT n FROM _res WHERE caso='c2') = (SELECT n_righe_reali FROM _refs),
    '5. righe: TUTTO-O-NIENTE — in scope il count sotto RLS = count reale');

SELECT ok((SELECT NOT prereq FROM _flags) OR     (SELECT visibile FROM _res WHERE caso='c6'),
    '6. riepiloghi IVA: whitelist = emittente -> visibili');
SELECT ok((SELECT NOT prereq FROM _flags) OR NOT (SELECT visibile FROM _res WHERE caso='c7'),
    '7. riepiloghi IVA: whitelist = altro emittente -> NON visibili');
SELECT ok((SELECT NOT prereq FROM _flags) OR
          (SELECT n FROM _res WHERE caso='c6') = (SELECT n_riep_reali FROM _refs),
    '8. riepiloghi IVA: TUTTO-O-NIENTE — in scope il count sotto RLS = count reale');

SELECT ok((SELECT NOT (prereq AND prereq_write) FROM _flags) OR
          (SELECT visibile FROM _res WHERE caso='c9'),
    '9. scrittura in-scope -> consentita (la policy e'' FOR ALL, non FOR SELECT)');
SELECT ok((SELECT NOT (prereq AND prereq_write) FROM _flags) OR
          (SELECT n FROM _res WHERE caso='c10') = 0,
    '10. scrittura off-scope -> 0 righe aggiornate (USING le nasconde)');

SELECT ok((SELECT NOT prereq FROM _flags) OR     (SELECT visibile FROM _res WHERE caso='c11'),
    '11. DISABLE RLS (kill-switch) -> righe di nuovo visibili');
SELECT ok((SELECT NOT prereq FROM _flags) OR NOT (SELECT visibile FROM _res WHERE caso='c12'),
    '12. veste CLIENTE_PORTALE non proprietaria -> NON visibili (ba_ownership nega)');

SELECT * FROM finish();
ROLLBACK;
