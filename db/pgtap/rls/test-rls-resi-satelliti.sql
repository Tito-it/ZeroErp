-- ------------------------------------------------------------
-- SPDX-License-Identifier: AGPL-3.0-or-later
-- pgtap-runner: owner
-- pgtap-runner-motivo: ALTER TABLE … FORCE ROW LEVEL SECURITY, locale alla
--   transazione — e' il FORCE a rendere l'owner soggetto alle policy, perche'
--   `titodb` non e' superuser e non puo' fare SET ROLE. E la fixture costruisce
--   DUE aziende: un operatore dentro un perimetro non potrebbe crearle.
-- pgTAP test FUNZIONALE RLS — satelliti di vendite.resi
--   Slice 20260909-40..42, brief brief-db-perimetro-emittente-righe-documento.md
--
-- Elenco test (plan 10):
--   1) struttura: i quattro satelliti hanno la loro policy
--   2) struttura: e la RLS ACCESA — non basta che la policy esista
--   3) l'operatore A vede la riga del PROPRIO reso
--   4) ⛔ e NON vede quella di B
--   5) ⛔ nemmeno la RINUNCIA appesa alla riga di B — il secondo livello
--   6) ⛔ SCRITTURA: A non puo' appendere una riga al reso di B (WITH CHECK)
--   7) ⛔ senza veste non vede NIENTE — fail-closed
--   8) ⭐ nessuna riga visibile il cui RESO non lo e' (il satellite non e' piu'
--         permissivo della propria testata)
--   9) ⭐⭐ nessuna riga visibile la cui DDT_RIGA non lo e' — l'ALTRO genitore
--  10) ⚠️ l'adattatore a DUE livelli (riga -> reso) risale davvero
--
-- ────────────────────────────────────────────────────────────────
-- ⭐ IL TEST 9 E' LA RAGIONE PER CUI QUESTA FAMIGLIA VIENE DOPO IL DDT.
--   `vendite.resi_righe` ha DUE genitori `NOT NULL`: `reso_id` e `ddt_riga_id`.
--   Il perimetro lo risolve il reso — e' il documento a cui la riga appartiene
--   (brief §6.2) — ma dal 2026-09-09 anche `vendite.ddt_righe` e' in RLS, e la
--   stessa riga e' quindi raggiungibile per due strade.
--   Il brief lasciava aperta una domanda: *esiste un guard che imponga al DDT e
--   al reso di condividere l'emittente?* Questo test la trasforma da opinione in
--   asserzione. Se diventasse rosso, il difetto NON e' la policy: e' il guard
--   mancante. ⚠️ E allora va spezzato in due — uno che pinna il difetto e uno
--   che pretende la riparazione — non allargato per farlo tacere.
--
-- ⭐ IL TEST 2 NON E' IL DOPPIONE DEL TEST 1: una policy senza
--   `ENABLE ROW LEVEL SECURITY` sta in `pg_policy` e non filtra niente. Ne
--   restano tre cosi' in tutto il database (acquisti.ddt, acquisti.ordini,
--   shop.ricevute), quindi non e' un caso teorico.
--
-- ⛔ LA FIXTURE SI COSTRUISCE, e per i resi la catena e' LUNGA: un reso pretende
--   un DDT **consegnato** (`trgfn_resi_guard_ddt_consegnato`), quindi il DDT va
--   portato DRAFT -> EMESSO -> SPEDITO -> CONSEGNATO passando dai suoi guard
--   (causale di trasporto, IVA di riga, indirizzo di consegna). Vale la pena:
--   il file misura la stessa cosa su dbdev e su un database ricostruito dai
--   changelog, invece di cercare un reso che li' non esiste.
--   ⚠️ Il precedente `test-rls-resi-ef-whitelist-write.sql` cerca invece dati
--   esistenti e ha un `EXCEPTION WHEN OTHERS THEN NULL` che lo fa passare a
--   vuoto quando la fixture non si costruisce: e' la forma «verde per
--   sottrazione» che questo file evita apposta.
--
-- ⛔ NIENTE riga di `resi_righe_accrediti` nella fixture: pretende una riga di
--   fattura rettificata e una commessa/attivita', cioe' una catena che non
--   appartiene a questa slice. Il suo perimetro passa dallo stesso adattatore
--   `_via_reso_riga` che il test 10 interroga direttamente. *Non serve una riga
--   per chiedere a una funzione se dice il vero.*
-- rev 2026-10-25 (brief-db-pgtap-reso-costruito, giro D-4): le due bolle CONSEGNATE dal builder dbops.fn_pgtap_crea_ddt_senza_ordine, ciascuna sotto il contesto del suo mondo; della bolla non resta niente a mano.
-- rev 2026-10-25 (brief-db-pgtap-reso-costruito): i due resi con la loro riga dal builder dbops.fn_pgtap_crea_reso, in bozza; restano scritte a mano la rinuncia e la riga d'intrusione del test 6, che sono il caso.
-- rev 2026-10-25 (brief-modello-documento-vendita §7, giro 5): le due bolle a CONSEGNATO con dbops.fn_pgtap_porta_a_stato (i passi col verbo, nel contesto dell'operatore di ciascun mondo), non piu' con UPDATE diretti dello stato che la porta ora rifiuta.
-- ------------------------------------------------------------

BEGIN;

SET CONSTRAINTS ALL IMMEDIATE;

SELECT plan(10);

-- ============================================================
-- I due mondi, e per ciascuno: DDT consegnato -> reso -> riga -> rinuncia
-- ============================================================
CREATE TEMP TABLE _mondi AS
SELECT 'A' AS lato, * FROM dbops.fn_pgtap_crea_emittente_operatore()
UNION ALL
SELECT 'B' AS lato, * FROM dbops.fn_pgtap_crea_emittente_operatore();

CREATE TEMP TABLE _clienti AS
SELECT m.lato, m.emittente_fiscale_id, c.*
  FROM _mondi m
  -- rev 2026-10-09 (brief-db-esecutivi-ba-coppia): il BA legato all'emittente del
  --   mondo. Il documento porta ora il BA, e il guard emittente <-> BA lo guarda.
  CROSS JOIN LATERAL dbops.fn_pgtap_crea_cliente_ba('RLS resi ' || m.lato, NULL, m.soggetto_ruolo_id) c;

-- ⛔ rev 2026-10-13 (brief-db-articoli-ammessi-per-documento, Lotto 3a): l'articolo
--   si COSTRUISCE. Ordine e bolla ammettono solo merce non solo-componente, e
--   su un database ricostruito il catalogo ha solo i cinque ONERE_* (servizi):
--   cercarlo dava NULL e la riga moriva su E_UOM_MISSING. Lo stesso articolo
--   serve alla riga d'intrusione del test 6.
CREATE TEMP TABLE _art AS
SELECT dbops.fn_pgtap_crea_articolo('PGTAP-RLS-RESI-SAT', false) AS id;

-- La bolla CONSEGNATA di ogni mondo, dal builder della bolla senza ordine:
-- causale, indirizzi, riga prezzata (10 a 25, con l'IVA) e i passi della
-- matrice coi verbi. ⛔ Ogni bolla si costruisce sotto il contesto del SUO
-- operatore: la bolla e' dell'azienda di chi agisce, e il BA del suo cliente.
CREATE TEMP TABLE _ddt (lato text, ddt_id bigint, ddt_riga_id bigint);
DO $consegna$
DECLARE m record;
BEGIN
    FOR m IN SELECT x.lato, x.auth_user_id, c.billing_account_id
               FROM _mondi x JOIN _clienti c ON c.lato = x.lato
              ORDER BY x.lato LOOP
        PERFORM script.fn_pgtap_set_contesto_operatore(m.auth_user_id);
        INSERT INTO _ddt
        SELECT m.lato, b.ddt_id, b.ddt_riga_id
          FROM dbops.fn_pgtap_crea_ddt_senza_ordine('RLS resi ' || m.lato,
                   p_billing_account_id => m.billing_account_id,
                   p_articolo_id        => (SELECT id FROM _art)) b;
    END LOOP;
END
$consegna$;

CREATE TEMP TABLE _ddt_righe AS
SELECT d.lato, d.ddt_riga_id, d.ddt_id FROM _ddt d;

-- Il reso di ogni mondo dal builder, in bozza, con una riga da 1 sulla riga
-- della bolla. Destinatario ed emittente li deriva il normalize dalla bolla.
-- ⚠️ `RESO_PER_RICONSEGNA` e non `RESO_A_CREDITO`: la rinuncia si appende SOLO
--   a una riga di tipo ri-consegna (`trgfn_resi_rinunce_guard`), e la rinuncia
--   serve al test 5.
CREATE TEMP TABLE _resi_righe AS
SELECT d.lato, b.resi_riga_id, b.reso_id
  FROM _ddt d
 CROSS JOIN LATERAL dbops.fn_pgtap_crea_reso('RLS resi ' || d.lato, d.ddt_id, 1,
                                             'RESO_PER_RICONSEGNA', 'DRAFT') b;

CREATE TEMP TABLE _resi AS
SELECT rr.lato, r.id AS reso_id, r.emittente_fiscale_id
  FROM _resi_righe rr JOIN vendite.resi r ON r.id = rr.reso_id;

-- ⭐ Una figlia di SECONDO livello costruita davvero: `rinunce` chiede solo la
--   riga e una quantita', quindi il test 5 misura una riga vera invece di
--   fidarsi dell'adattatore.
INSERT INTO vendite.resi_righe_rinunce (resi_riga_id, qta)
SELECT rr.resi_riga_id, 1 FROM _resi_righe rr;

-- ============================================================
-- 1..2. La struttura: policy E armamento
-- ============================================================
SELECT is(
    (SELECT count(*)::int FROM pg_policies
      WHERE schemaname = 'vendite'
        AND tablename IN ('resi_righe', 'resi_righe_accrediti',
                          'resi_righe_riconsegne', 'resi_righe_rinunce')),
    4,
    '1. i quattro satelliti di resi hanno la loro policy'
);

SELECT is(
    (SELECT count(*)::int FROM pg_class c
       JOIN pg_namespace n ON n.oid = c.relnamespace AND n.nspname = 'vendite'
      WHERE c.relname IN ('resi_righe', 'resi_righe_accrediti',
                          'resi_righe_riconsegne', 'resi_righe_rinunce')
        AND c.relrowsecurity),
    4,
    '2. e su tutti e quattro la RLS e'' ACCESA, non solo dichiarata'
);

-- ============================================================
-- Il perimetro, esercitato
-- ============================================================
ALTER TABLE vendite.resi                   FORCE ROW LEVEL SECURITY;
ALTER TABLE vendite.resi_righe             FORCE ROW LEVEL SECURITY;
ALTER TABLE vendite.resi_righe_rinunce     FORCE ROW LEVEL SECURITY;
ALTER TABLE vendite.ddt_righe              FORCE ROW LEVEL SECURITY;

DO $perimetro$
DECLARE
    v_a record;
    v_b record;
    v_n integer;
BEGIN
    SELECT s.*, m.auth_user_id INTO v_a
      FROM _resi s JOIN _mondi m ON m.emittente_fiscale_id = s.emittente_fiscale_id
     WHERE s.lato = 'A';
    SELECT s.* INTO v_b FROM _resi s WHERE s.lato = 'B';

    PERFORM script.fn_pgtap_set_contesto_operatore(v_a.auth_user_id);

    SELECT count(*) INTO v_n FROM vendite.resi_righe r WHERE r.reso_id = v_a.reso_id;
    PERFORM set_config('pgtap.righe_a', v_n::text, true);
    SELECT count(*) INTO v_n FROM vendite.resi_righe r WHERE r.reso_id = v_b.reso_id;
    PERFORM set_config('pgtap.righe_b', v_n::text, true);

    -- Il secondo livello, su una riga vera.
    SELECT count(*) INTO v_n
      FROM vendite.resi_righe_rinunce ri
     WHERE ri.resi_riga_id IN (SELECT resi_riga_id FROM _resi_righe WHERE lato = 'B');
    PERFORM set_config('pgtap.rinunce_b', v_n::text, true);

    -- ⭐ Invariante verso la TESTATA.
    SELECT count(*) INTO v_n
      FROM vendite.resi_righe r
     WHERE NOT EXISTS (SELECT 1 FROM vendite.resi s WHERE s.id = r.reso_id);
    PERFORM set_config('pgtap.orfane_reso', v_n::text, true);

    -- ⭐⭐ Invariante verso l'ALTRO genitore: la riga di DDT da cui la merce
    --   proviene. Se questo conta piu' di zero, DDT e reso hanno emittenti
    --   diversi — ed e' un guard mancante, non una policy da allargare.
    SELECT count(*) INTO v_n
      FROM vendite.resi_righe r
     WHERE NOT EXISTS (SELECT 1 FROM vendite.ddt_righe dr WHERE dr.id = r.ddt_riga_id);
    PERFORM set_config('pgtap.orfane_ddt', v_n::text, true);

    -- La risalita a due livelli, chiesta all'adattatore.
    PERFORM set_config('pgtap.riga2',
        script.fn_scope_ef_whitelist_via_reso_riga(
            v_a.auth_user_id, (SELECT resi_riga_id FROM _resi_righe WHERE lato = 'A'))::text
        || '/' ||
        script.fn_scope_ef_whitelist_via_reso_riga(
            v_a.auth_user_id, (SELECT resi_riga_id FROM _resi_righe WHERE lato = 'B'))::text,
        true);

    -- ⛔ La scrittura sul reso altrui.
    BEGIN
        INSERT INTO vendite.resi_righe
            (reso_id, riga_nr, ddt_riga_id, articolo_id, descrizione,
             quantita, qta_operativa, tipo_reso_id)
        VALUES (v_b.reso_id, 99,
                (SELECT ddt_riga_id FROM _ddt_righe WHERE lato = 'B'),
                (SELECT id FROM _art),
                'intrusione', 1, 1,
                -- ⚠️ `RESO_PER_RICONSEGNA` e non `RESO_A_CREDITO`: la rinuncia si
           --   appende SOLO a una riga di tipo ri-consegna
           --   (`trgfn_resi_rinunce_guard`), e la rinuncia serve al test 5.
           (SELECT tr.id FROM config.tipi_reso tr WHERE tr.codice_interno='RESO_PER_RICONSEGNA'));
        PERFORM set_config('pgtap.scrittura', 'PASSATA', true);
    EXCEPTION WHEN insufficient_privilege OR check_violation THEN
        PERFORM set_config('pgtap.scrittura', 'RIFIUTATA', true);
    END;

    -- ⛔ Nessuna veste: fail-closed.
    PERFORM set_config('app.ruolo_applicativo', '', true);
    SELECT count(*) INTO v_n
      FROM vendite.resi_righe r WHERE r.reso_id IN (v_a.reso_id, v_b.reso_id);
    PERFORM set_config('pgtap.senza_veste', v_n::text, true);
END
$perimetro$;

ALTER TABLE vendite.ddt_righe              NO FORCE ROW LEVEL SECURITY;
ALTER TABLE vendite.resi_righe_rinunce     NO FORCE ROW LEVEL SECURITY;
ALTER TABLE vendite.resi_righe             NO FORCE ROW LEVEL SECURITY;
ALTER TABLE vendite.resi                   NO FORCE ROW LEVEL SECURITY;

SELECT is(current_setting('pgtap.righe_a', true), '1',
          '3. l''operatore A vede la riga del proprio reso');

SELECT is(current_setting('pgtap.righe_b', true), '0',
          '4. e NON vede la riga del reso di un''altra azienda');

SELECT is(current_setting('pgtap.rinunce_b', true), '0',
          '5. nemmeno la RINUNCIA appesa a quella riga: il secondo livello e'' coperto');

SELECT is(current_setting('pgtap.scrittura', true), 'RIFIUTATA',
          '6. e non puo'' appendere una riga al reso altrui (WITH CHECK)');

SELECT is(current_setting('pgtap.senza_veste', true), '0',
          '7. senza veste applicativa non vede niente: fail-closed');

SELECT is(current_setting('pgtap.orfane_reso', true), '0',
          '8. nessuna riga visibile il cui RESO non lo e'': il satellite non e'' piu'' permissivo della testata');

SELECT is(current_setting('pgtap.orfane_ddt', true), '0',
          '9. nessuna riga visibile la cui DDT_RIGA non lo e'': i due genitori concordano sull''emittente');

SELECT is(current_setting('pgtap.riga2', true), 'true/false',
          '10. l''adattatore a due livelli risale davvero: vero sulla riga di A, falso su quella di B');

SELECT * FROM finish();

ROLLBACK;
