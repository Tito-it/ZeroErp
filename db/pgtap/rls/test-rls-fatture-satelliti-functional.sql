-- ------------------------------------------------------------
-- SPDX-License-Identifier: AGPL-3.0-or-later
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
--   - ⭐ Rev 2026-10-07 (brief-db-fixture-rls-documenti-costruiti, giro 3):
--     IL MONDO SI COSTRUISCE. Fino a oggi il file pescava «una fattura con
--     righe e riepiloghi, possibilmente in DRAFT/EMESSA» e «il primo altro
--     emittente», e senza dati andava in SOFT-SKIP: su zeroerp_ci (da zero) i
--     dodici casi passavano senza misurare niente. Ora due aziende costruite —
--     A possiede la fattura, B e' l'estranea — e la fattura di A in DRAFT
--     (dbops.fn_pgtap_crea_fattura) con DUE righe scritte qui e il riepilogo
--     ricalcolato dalla funzione del dominio, tutto PRIMA del FORCE. Se
--     qualcosa non si costruisce il file va ROSSO.
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
-- DRAFT/EMESSA -> la fixture la costruisce in DRAFT.
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
-- Indice test (0..12):
--   0   fixture: fattura di A in DRAFT con due righe e il riepilogo, B e' un'altra azienda
--   1   righe: operatore whitelist VUOTA          -> NON visibili (fail-closed, P-2a)
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
-- ⚠️ Vincoli DIFFERITI: senza questa riga il test smetterebbe di verificarli.
--   Un trigger DEFERRABLE INITIALLY DEFERRED scatta al COMMIT, e qui il COMMIT
--   non arriva mai (si chiude in ROLLBACK): sarebbero saltati in silenzio, e il
--   file sarebbe verde per sottrazione. IMMEDIATE li riporta a scattare a fine
--   di ogni istruzione. In testa e non in coda: in coda scatterebbero dopo il
--   cleanup, su righe ormai cancellate.
-- ⭐ Rev 2026-10-07 (brief-db-veste-utilizzabile): fino a oggi questo file non
--   la aveva, perche' costruiva l'operatore a mano con fn_crea_soggetto_pf e
--   lasciava il soggetto senza indirizzo, contando sul ROLLBACK (§22.4). Ora
--   l'operatore viene dalla madre (dbops.fn_pgtap_crea_operatore_umano), che
--   lo consegna COMPLETO: la riga torna, e i guard del soggetto si esercitano.
SET CONSTRAINTS ALL IMMEDIATE;

SELECT plan(13);

-- =========================================================
-- Fixture: due aziende, la fattura di A con righe e riepilogo
-- =========================================================
-- B prima di tutto, e PRIMA di qualunque contesto: e' un builder atomico.
CREATE TEMP TABLE _b AS
SELECT * FROM dbops.fn_pgtap_crea_emittente_operatore();

-- A: senza contesto aperto, il builder costruisce l'azienda, l'operatore
-- (tecnico), il cliente e la fattura in DRAFT — l'unico stato, con EMESSA, in
-- cui il guard di congelamento lascia scrivere (test 9-10).
CREATE TEMP TABLE _a AS
SELECT * FROM dbops.fn_pgtap_crea_fattura('rls satelliti');

-- DUE righe e non una: il «tutto-o-niente» (5, 8) con una riga sola non
-- distinguerebbe «tutte» da «almeno una».
INSERT INTO vendite.fatture_righe (
    fattura_id, riga_nr, descrizione, qta, prezzo_unitario, imponibile_riga,
    competenza_dal, competenza_al, iva_id)
SELECT a.fattura_id, n, 'Riga pgTAP RLS satelliti ' || n, 1, 10 * n, 10 * n,
       script.fn_data_operativa(), script.fn_data_operativa(),
       (SELECT i.id FROM config.iva i WHERE i.attivo ORDER BY i.id LIMIT 1)
  FROM _a a, generate_series(1, 2) n;

-- Il riepilogo lo scrive la funzione del dominio, non la fixture.
SELECT vendite.fn_ricalcola_riepilogo_iva_fattura((SELECT fattura_id FROM _a));

-- ⚠️ Il builder ha lasciato aperto il contesto del SUO operatore. Qui l'identita'
--   la dichiara ogni caso: si riparte da «nessuno».
SELECT set_config('app.ruolo_applicativo', '', false),
       set_config('app.current_user_id',   '', false);

CREATE TEMP TABLE _refs AS
SELECT
    a.fattura_id,
    a.emittente_soggetto_ruolo_id AS emit_sr,
    a.emittente_fiscale_id        AS emit_pk,
    b.emittente_fiscale_id        AS other_pk,
    -- Conteggi REALI, presi da owner PRIMA di armare la RLS: sono il metro
    -- dei test 5 e 8. Presi dopo, sarebbero gia' filtrati e il confronto
    -- misurerebbe se' stesso.
    (SELECT count(*) FROM vendite.fatture_righe fr
      WHERE fr.fattura_id = a.fattura_id)           AS n_righe_reali,
    (SELECT count(*) FROM vendite.fatture_riepiloghi_iva ri
      WHERE ri.fattura_id = a.fattura_id)           AS n_riep_reali
  FROM _a a, _b b;

SELECT ok(
    (SELECT r.n_righe_reali = 2 AND r.n_riep_reali >= 1 AND r.emit_pk <> r.other_pk
       FROM _refs r),
    '0. Fixture: fattura di A in DRAFT con due righe e il riepilogo, B e'' un''altra azienda');

-- Un operatore umano, dalla madre.
CREATE TEMP TABLE _op (auth_user_id int, soggetto_id uuid, sr_id bigint, identita_id bigint);

-- ⭐ Rev 2026-10-07 (brief-db-veste-utilizzabile): l'operatore viene dalla
--   MADRE (dbops.fn_pgtap_crea_operatore_umano: persona fisica completa,
--   risorsa umana, veste OPERATORE accesa come all'invito accettato) e
--   l'emittente gli si da' con la funzione di dominio
--   script.fn_change_user_emittenti_scope. Prima la fixture costruiva
--   soggetto, soggetto_ruolo e veste a mano, senza risorsa umana: uno stato
--   che la madre non produce, e che da D-2 (l'operatore umano vale finche'
--   vale il suo rapporto, script.fn_veste_utilizzabile) non e' piu' un
--   operatore valido. Il builder esce con i vincoli IMMEDIATE: niente piu'
--   finestra differita da riaprire per lui.
INSERT INTO _op
SELECT o.auth_user_id, o.soggetto_id, o.soggetto_ruolo_id, o.identita_id
  FROM dbops.fn_pgtap_crea_operatore_umano('rls satelliti') o;

-- Arma la RLS solo dentro questa transazione (FORCE assoggetta l'owner).
ALTER TABLE vendite.fatture_righe          ENABLE ROW LEVEL SECURITY;
ALTER TABLE vendite.fatture_righe          FORCE  ROW LEVEL SECURITY;
ALTER TABLE vendite.fatture_riepiloghi_iva ENABLE ROW LEVEL SECURITY;
ALTER TABLE vendite.fatture_riepiloghi_iva FORCE  ROW LEVEL SECURITY;

CREATE TEMP TABLE _res (caso text, visibile boolean, n bigint);

-- Helper: imposta la sessione operatore con la whitelist indicata.
-- (procedura locale: evita 10 ripetizioni degli stessi 4 statement)
--
-- ⚠️ Il DELETE sulla whitelist e' protetto da trgfn_user_emittenti_fiscali_guard_delete
--   (solo utente cessato o GUC di manutenzione). Lo si attraversa con la
--   funzione di dominio script.fn_change_user_emittenti_scope, che apre lei
--   l'override: senza, il file fallirebbe nel FIXTURE, cioe' copertura zero.
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

    -- ⭐ Rev 2026-10-07: la whitelist si ripunta con la funzione di dominio,
    --   che apre lei l'override del DELETE (un emittente o nessuno).
    PERFORM script.fn_change_user_emittenti_scope(
        (SELECT auth_user_id FROM _op),
        CASE WHEN v_emit IS NULL THEN '{}'::bigint[] ELSE ARRAY[v_emit] END);

    PERFORM set_config('app.ruolo_applicativo', 'OPERATORE', true);
    PERFORM set_config('app.current_user_id', (SELECT auth_user_id FROM _op)::text, true);
END
$sp$;

-- ---- Caso 1: whitelist VUOTA -> righe NON visibili (fail-closed) ----
-- 🔴 CAMBIATO il 2026-08-18 (changeSet 20260818-11/-12, passo 2 / P-2a del
--    cantiere «perimetro emittente»). Prima questo caso asseriva l'opposto —
--    «whitelist vuota = accesso globale» — che era il fail-OPEN: un operatore
--    configurato a meta' vedeva TUTTI gli emittenti, e non lo sapeva ne' lui
--    ne' nessun altro. P-2a lo ha chiuso: nessuna riga = nessun emittente.
-- ⚠️ Il test non e' stato «riparato»: e' stato riallineato a una decisione.
--    Se un giorno tornasse a passare col vecchio significato, il fail-open e'
--    rientrato.
DO $c1$
BEGIN
    CALL pg_temp.set_op('none');
    INSERT INTO _res SELECT 'c1', EXISTS (
        SELECT 1 FROM vendite.fatture_righe WHERE fattura_id = (SELECT fattura_id FROM _refs)), NULL;
END $c1$;

-- ---- Caso 2 + 5: whitelist = emittente della fattura -> visibili, e TUTTE ----
DO $c2$
BEGIN
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
    CALL pg_temp.set_op('other');
    INSERT INTO _res SELECT 'c3', EXISTS (
        SELECT 1 FROM vendite.fatture_righe WHERE fattura_id = (SELECT fattura_id FROM _refs)), NULL;
END $c3$;

-- ---- Caso 4: ruolo NON OPERATORE (gate della policy) -> NON visibili ----
DO $c4$
BEGIN
    CALL pg_temp.set_op('own');
    PERFORM set_config('app.ruolo_applicativo', '', true);
    INSERT INTO _res SELECT 'c4', EXISTS (
        SELECT 1 FROM vendite.fatture_righe WHERE fattura_id = (SELECT fattura_id FROM _refs)), NULL;
END $c4$;

-- ---- Caso 6 + 8: riepiloghi IVA in scope -> visibili, e TUTTI ----
DO $c6$
BEGIN
    CALL pg_temp.set_op('own');
    INSERT INTO _res
    SELECT 'c6', count(*) > 0, count(*)
      FROM vendite.fatture_riepiloghi_iva WHERE fattura_id = (SELECT fattura_id FROM _refs);
END $c6$;

-- ---- Caso 7: riepiloghi IVA fuori scope -> NON visibili ----
DO $c7$
BEGIN
    CALL pg_temp.set_op('other');
    INSERT INTO _res SELECT 'c7', EXISTS (
        SELECT 1 FROM vendite.fatture_riepiloghi_iva
         WHERE fattura_id = (SELECT fattura_id FROM _refs)), NULL;
END $c7$;

-- ---- Caso 9: SCRITTURA in-scope -> la policy FOR ALL la consente ----
DO $c9$
DECLARE v_n bigint;
BEGIN
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
-- Asserzioni
-- =========================================================
SELECT ok(NOT (SELECT visibile FROM _res WHERE caso='c1'),
    '1. righe: operatore whitelist vuota -> NON visibili (fail-closed, P-2a)');
SELECT ok((SELECT visibile FROM _res WHERE caso='c2'),
    '2. righe: whitelist = emittente fattura -> visibili');
SELECT ok(NOT (SELECT visibile FROM _res WHERE caso='c3'),
    '3. righe: whitelist = altro emittente -> NON visibili');
SELECT ok(NOT (SELECT visibile FROM _res WHERE caso='c4'),
    '4. righe: ruolo non OPERATORE -> NON visibili (gate policy)');

-- ⭐ L'invariante: in scope si vedono TUTTE le righe, non una parte.
SELECT ok((SELECT n FROM _res WHERE caso='c2') = (SELECT n_righe_reali FROM _refs),
    '5. righe: TUTTO-O-NIENTE — in scope il count sotto RLS = count reale');

SELECT ok((SELECT visibile FROM _res WHERE caso='c6'),
    '6. riepiloghi IVA: whitelist = emittente -> visibili');
SELECT ok(NOT (SELECT visibile FROM _res WHERE caso='c7'),
    '7. riepiloghi IVA: whitelist = altro emittente -> NON visibili');
SELECT ok((SELECT n FROM _res WHERE caso='c6') = (SELECT n_riep_reali FROM _refs),
    '8. riepiloghi IVA: TUTTO-O-NIENTE — in scope il count sotto RLS = count reale');

SELECT ok((SELECT visibile FROM _res WHERE caso='c9'),
    '9. scrittura in-scope -> consentita (la policy e'' FOR ALL, non FOR SELECT)');
SELECT ok((SELECT n FROM _res WHERE caso='c10') = 0,
    '10. scrittura off-scope -> 0 righe aggiornate (USING le nasconde)');

SELECT ok((SELECT visibile FROM _res WHERE caso='c11'),
    '11. DISABLE RLS (kill-switch) -> righe di nuovo visibili');
SELECT ok(NOT (SELECT visibile FROM _res WHERE caso='c12'),
    '12. veste CLIENTE_PORTALE non proprietaria -> NON visibili (ba_ownership nega)');

SELECT * FROM finish();
ROLLBACK;
