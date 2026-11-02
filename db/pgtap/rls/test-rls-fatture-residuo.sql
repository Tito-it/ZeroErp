-- ------------------------------------------------------------
-- SPDX-License-Identifier: AGPL-3.0-or-later
-- pgtap-runner: owner
-- pgtap-runner-motivo: ALTER TABLE … FORCE ROW LEVEL SECURITY, locale alla
--   transazione — e' il FORCE a rendere l'owner soggetto alle policy, perche'
--   `titodb` non e' superuser e non puo' fare SET ROLE. E la fixture costruisce
--   DUE aziende: un operatore dentro un perimetro non potrebbe crearle.
-- pgTAP test FUNZIONALE RLS — il RESIDUO della famiglia vendite.fatture
--   Slice 20260909-69..71, brief brief-db-perimetro-emittente-righe-documento.md
--   Passo 7: le sette figlie che il §2 del brief dava per protette e non lo erano.
--
-- Elenco test (plan 12):
--   1) struttura: le sette tabelle portano ENTRAMBE le vesti = 14 policy
--   2) struttura: e la RLS ACCESA su tutte e sette
--   3) l'operatore A vede il LOG della propria fattura
--   4) ⛔ e NON vede quello di B
--   5) ⛔ nemmeno la NOTA di B: la chiave e' `target_id`
--   6) ⛔ nemmeno la RETTIFICA di B
--   7) ⛔ nemmeno l'EVENTO SDI di B — il livello due
--   8) ⛔ SCRITTURA: A non puo' appendere un log alla fattura di B
--   9) ⛔ senza veste non vede NIENTE — fail-closed
--  10) ⭐ il CLIENTE DEL PORTALE di A vede il log delle proprie fatture
--  11) ⛔ e NON vede quello delle fatture di un altro cliente
--  12) ⭐ `fatture_rettifiche` ha due genitori: le due fatture condividono
--        l'emittente — invariante di dominio, non decisione della policy
--
-- ────────────────────────────────────────────────────────────────
-- ⭐ PERCHE' QUESTO FILE ESERCITA DUE VESTI, unico del brief.
--   `vendite.fatture` e' l'unica testata con DUE policy: operatore e cliente
--   del portale. Le altre cinque famiglie ne avevano una (o tre, ma tutte
--   riconducibili a un operatore o a un cliente gia' coperto dal caso SHOP).
--   I test 10 e 11 sono li' perche' la regola «il satellite rispecchia TUTTE le
--   vesti della testata» diventi una cosa provata e non una dichiarazione: con
--   la sola veste operatore un cliente del portale smetterebbe di vedere il log
--   e gli esiti SDI delle PROPRIE fatture, e sarebbe una modifica funzionale
--   mascherata da cantiere di sicurezza.
--
-- ⭐ IL TEST 12 E' LA STESSA DOMANDA GIA' POSTA SU `resi_righe`, in un altro
--   punto del modello. `fatture_rettifiche` porta `fattura_id` E
--   `rettificata_id`, entrambe `NOT NULL` verso `vendite.fatture`: il perimetro
--   e' la prima — il documento a cui la riga appartiene — e che le due
--   condividano l'emittente e' un invariante di DOMINIO. Il test lo pretende
--   invece di darlo per buono. ⚠️ Se diventasse rosso il difetto non e' la
--   policy: e' un guard mancante fra la nota di credito e la fattura che
--   rettifica.
--
-- ⛔ IL TEST 2 NON E' IL DOPPIONE DEL TEST 1: una policy senza
--   `ENABLE ROW LEVEL SECURITY` sta in `pg_policy` e non filtra niente.
--
-- ⛔ LA FIXTURE SI COSTRUISCE. Due mondi, e per ciascuno: emittente+operatore,
--   cliente con BA legato, registro di numerazione, DUE fatture (la seconda
--   serve alla rettifica) e i satelliti. In piu' — ed e' l'unica cosa che
--   nessun'altra fixture del brief costruisce — un'IDENTITA' DI PORTALE per il
--   cliente, senza la quale i test 10 e 11 non avrebbero soggetto.
--
-- ⚠️ SEI SATELLITI SU SETTE hanno una riga vera. `fatture_atti` no: pretende
--   anche un `contratto_id` NOT NULL, cioe' un contratto completo — catena che
--   appartiene al passo 5, non a questo. La sua policy e' verificata dai test 1
--   e 2 (struttura e armamento) e usa lo STESSO adattatore
--   `fn_scope_ef_whitelist_via_fattura` delle altre cinque di primo livello,
--   che i test 3-9 esercitano. ⛔ E' una copertura dichiarata, non piena: se un
--   giorno `fatture_atti` cambiasse chiave, qui non se ne accorgerebbe nessuno.
-- ------------------------------------------------------------

BEGIN;

SET CONSTRAINTS ALL IMMEDIATE;

SELECT plan(12);

-- ============================================================
-- I due mondi
-- ============================================================
CREATE TEMP TABLE _mondi AS
SELECT 'A' AS lato, * FROM dbops.fn_pgtap_crea_emittente_operatore()
UNION ALL
SELECT 'B' AS lato, * FROM dbops.fn_pgtap_crea_emittente_operatore();

CREATE TEMP TABLE _clienti AS
SELECT m.lato, m.emittente_fiscale_id, m.soggetto_ruolo_id AS emittente_sr_id, c.*
  FROM _mondi m
  CROSS JOIN LATERAL dbops.fn_pgtap_crea_cliente_ba(
      'RLS fatture ' || m.lato, NULL, m.soggetto_ruolo_id) c;

-- ⚠️ `vendite.fatture.registro_id` e' NOT NULL: il registro non nasce da solo
--   all'INSERT, lo pretende la colonna.
CREATE TEMP TABLE _registri AS
WITH r AS (
    INSERT INTO vendite.registri_fatturazione
        (codice, descrizione, emittente_soggetto_ruolo_id, famiglia_documento)
    SELECT 'PGTAPF' || c.billing_account_id,
           'Registro pgTAP RLS ' || c.lato,
           c.emittente_sr_id, 'FATTURA'
      FROM _clienti c
    RETURNING id, emittente_soggetto_ruolo_id
)
SELECT c.lato, r.id AS registro_id
  FROM r JOIN _clienti c ON c.emittente_sr_id = r.emittente_soggetto_ruolo_id;

-- Due fatture per lato: la seconda rettifica la prima (test 6 e 12).
CREATE TEMP TABLE _fatture AS
WITH f AS (
    INSERT INTO vendite.fatture
        (registro_id, emittente_soggetto_ruolo_id, billing_account_id)
    SELECT r.registro_id, c.emittente_sr_id, c.billing_account_id
      FROM _clienti c JOIN _registri r ON r.lato = c.lato
    UNION ALL
    SELECT r.registro_id, c.emittente_sr_id, c.billing_account_id
      FROM _clienti c JOIN _registri r ON r.lato = c.lato
    RETURNING id, emittente_soggetto_ruolo_id, billing_account_id
)
SELECT c.lato, f.id AS fattura_id, f.billing_account_id,
       row_number() OVER (PARTITION BY c.lato ORDER BY f.id) AS nr
  FROM f JOIN _clienti c ON c.emittente_sr_id = f.emittente_soggetto_ruolo_id;

-- ⭐ L'IDENTITA' DI PORTALE del cliente: senza, i test 10 e 11 non hanno
--   soggetto. `fn_scope_ba_ownership` pretende un'identita' ATTIVA, in veste
--   CLIENTE_PORTALE, il cui `soggetto_ruolo_id` sia quello del BA.
CREATE TEMP TABLE _portale (lato text, identita_id bigint);

DO $portale$
DECLARE
    c    record;
    v_u  integer;
    v_id bigint;
BEGIN
    FOR c IN SELECT lato, soggetto_ruolo_id FROM _clienti LOOP
        INSERT INTO django.auth_user
            (username, password, is_active, is_staff, is_superuser,
             first_name, last_name, email, date_joined)
        VALUES ('_pgtap_rls_fatt_' || c.lato || '_'
                    || substring(md5(clock_timestamp()::text) from 1 for 8),
                '!', true, false, false, '', '', '', now())
        RETURNING id INTO v_u;

        v_id := anagrafiche.fn_crea_veste_portale(v_u, c.soggetto_ruolo_id, 'CLIENTE_PORTALE', true);

        INSERT INTO _portale VALUES (c.lato, v_id);
    END LOOP;
END
$portale$;

-- I satelliti, sulla PRIMA fattura di ogni lato.
INSERT INTO vendite.fatture_log (fattura_id, messaggio)
SELECT f.fattura_id, 'log pgTAP RLS' FROM _fatture f WHERE f.nr = 1;

INSERT INTO vendite.note_fatture (target_tipo, target_id, anchor_tipo, posizione, testo, id_stile)
SELECT 'FATTURA', f.fattura_id, 'DOCUMENTO', 'HEADER', 'Nota pgTAP RLS',
       (SELECT s.id FROM config.note_stili s WHERE s.codice_interno = 'NORMALE')
  FROM _fatture f WHERE f.nr = 1;

INSERT INTO vendite.fatture_fondi_fattura (fattura_id, tipo_fondo_fattura_id, importo)
SELECT f.fattura_id,
       (SELECT t.id FROM vendite.tipi_fondi_fattura t ORDER BY t.id LIMIT 1), 10.00
  FROM _fatture f WHERE f.nr = 1;

CREATE TEMP TABLE _sdi AS
WITH s AS (
    INSERT INTO vendite.fatture_sdi (fattura_id, stato_sdi_id)
    SELECT f.fattura_id, (SELECT st.id FROM config.stati_sdi st ORDER BY st.id LIMIT 1)
      FROM _fatture f WHERE f.nr = 1
    RETURNING id, fattura_id
)
SELECT f.lato, s.id AS sdi_id FROM s JOIN _fatture f ON f.fattura_id = s.fattura_id;

INSERT INTO vendite.fatture_sdi_eventi (fattura_sdi_id)
SELECT s.sdi_id FROM _sdi s;

-- La rettifica: la seconda fattura rettifica la prima, dentro lo stesso mondo.
INSERT INTO vendite.fatture_rettifiche (fattura_id, rettificata_id)
SELECT a.fattura_id, b.fattura_id
  FROM _fatture a JOIN _fatture b ON b.lato = a.lato AND b.nr = 1
 WHERE a.nr = 2;

-- ============================================================
-- 1..2. La struttura: due vesti per tabella, e l'armamento
-- ============================================================
SELECT is(
    (SELECT count(*)::int FROM pg_policies
      WHERE schemaname = 'vendite'
        AND tablename IN ('fatture_atti', 'fatture_fondi_fattura', 'fatture_log',
                          'fatture_rettifiche', 'fatture_sdi', 'note_fatture',
                          'fatture_sdi_eventi')),
    14,
    '1. le sette tabelle portano ENTRAMBE le vesti della testata (7 x 2)'
);

SELECT is(
    (SELECT count(*)::int FROM pg_class c
       JOIN pg_namespace n ON n.oid = c.relnamespace AND n.nspname = 'vendite'
      WHERE c.relname IN ('fatture_atti', 'fatture_fondi_fattura', 'fatture_log',
                          'fatture_rettifiche', 'fatture_sdi', 'note_fatture',
                          'fatture_sdi_eventi')
        AND c.relrowsecurity),
    7,
    '2. e su tutte e sette la RLS e'' ACCESA, non solo dichiarata'
);

-- ============================================================
-- Il perimetro, esercitato
-- ============================================================
ALTER TABLE vendite.fatture             FORCE ROW LEVEL SECURITY;
ALTER TABLE vendite.fatture_log         FORCE ROW LEVEL SECURITY;
ALTER TABLE vendite.note_fatture        FORCE ROW LEVEL SECURITY;
ALTER TABLE vendite.fatture_rettifiche  FORCE ROW LEVEL SECURITY;
ALTER TABLE vendite.fatture_sdi_eventi  FORCE ROW LEVEL SECURITY;

DO $perimetro$
DECLARE
    v_a  record;
    v_b  record;
    v_b2 record;
    v_n  integer;
BEGIN
    SELECT f.*, m.auth_user_id INTO v_a
      FROM _fatture f
      JOIN _clienti c ON c.lato = f.lato
      JOIN _mondi m   ON m.lato = f.lato
     WHERE f.lato = 'A' AND f.nr = 1;
    SELECT f.* INTO v_b  FROM _fatture f WHERE f.lato = 'B' AND f.nr = 1;
    SELECT f.* INTO v_b2 FROM _fatture f WHERE f.lato = 'B' AND f.nr = 2;

    -- ---------- veste OPERATORE ----------
    PERFORM script.fn_pgtap_set_contesto_operatore(v_a.auth_user_id);

    SELECT count(*) INTO v_n FROM vendite.fatture_log l WHERE l.fattura_id = v_a.fattura_id;
    PERFORM set_config('pgtap.log_a', v_n::text, true);
    SELECT count(*) INTO v_n FROM vendite.fatture_log l WHERE l.fattura_id = v_b.fattura_id;
    PERFORM set_config('pgtap.log_b', v_n::text, true);

    SELECT count(*) INTO v_n FROM vendite.note_fatture nf WHERE nf.target_id = v_b.fattura_id;
    PERFORM set_config('pgtap.note_b', v_n::text, true);

    SELECT count(*) INTO v_n FROM vendite.fatture_rettifiche r WHERE r.fattura_id = v_b2.fattura_id;
    PERFORM set_config('pgtap.rett_b', v_n::text, true);

    SELECT count(*) INTO v_n
      FROM vendite.fatture_sdi_eventi e
     WHERE e.fattura_sdi_id IN (SELECT sdi_id FROM _sdi WHERE lato = 'B');
    PERFORM set_config('pgtap.sdi_b', v_n::text, true);

    -- ⭐ L'invariante dei due genitori: nessuna rettifica visibile la cui
    --   fattura RETTIFICATA non lo sia.
    SELECT count(*) INTO v_n
      FROM vendite.fatture_rettifiche r
     WHERE NOT EXISTS (SELECT 1 FROM vendite.fatture f WHERE f.id = r.rettificata_id);
    PERFORM set_config('pgtap.rett_orfane', v_n::text, true);

    -- ⛔ La scrittura sulla fattura altrui.
    BEGIN
        INSERT INTO vendite.fatture_log (fattura_id, messaggio)
        VALUES (v_b.fattura_id, 'intrusione');
        PERFORM set_config('pgtap.scrittura', 'PASSATA', true);
    EXCEPTION WHEN insufficient_privilege OR check_violation THEN
        PERFORM set_config('pgtap.scrittura', 'RIFIUTATA', true);
    END;

    -- ---------- veste CLIENTE_PORTALE ----------
    PERFORM set_config('app.current_user_id', '', true);
    PERFORM set_config('app.ruolo_applicativo', 'CLIENTE_PORTALE', true);
    PERFORM set_config('app.current_identita_id',
                       (SELECT identita_id FROM _portale WHERE lato = 'A')::text, true);

    SELECT count(*) INTO v_n FROM vendite.fatture_log l WHERE l.fattura_id = v_a.fattura_id;
    PERFORM set_config('pgtap.portale_proprio', v_n::text, true);
    SELECT count(*) INTO v_n FROM vendite.fatture_log l WHERE l.fattura_id = v_b.fattura_id;
    PERFORM set_config('pgtap.portale_altrui', v_n::text, true);

    -- ⛔ Nessuna veste: fail-closed.
    PERFORM set_config('app.ruolo_applicativo', '', true);
    PERFORM set_config('app.current_identita_id', '', true);
    SELECT count(*) INTO v_n
      FROM vendite.fatture_log l WHERE l.fattura_id IN (v_a.fattura_id, v_b.fattura_id);
    PERFORM set_config('pgtap.senza_veste', v_n::text, true);
END
$perimetro$;

ALTER TABLE vendite.fatture_sdi_eventi  NO FORCE ROW LEVEL SECURITY;
ALTER TABLE vendite.fatture_rettifiche  NO FORCE ROW LEVEL SECURITY;
ALTER TABLE vendite.note_fatture        NO FORCE ROW LEVEL SECURITY;
ALTER TABLE vendite.fatture_log         NO FORCE ROW LEVEL SECURITY;
ALTER TABLE vendite.fatture             NO FORCE ROW LEVEL SECURITY;

SELECT is(current_setting('pgtap.log_a', true), '1',
          '3. l''operatore A vede il LOG della propria fattura');

SELECT is(current_setting('pgtap.log_b', true), '0',
          '4. e NON vede quello della fattura di un''altra azienda');

SELECT is(current_setting('pgtap.note_b', true), '0',
          '5. nemmeno la NOTA della fattura altrui: la chiave e'' target_id');

SELECT is(current_setting('pgtap.rett_b', true), '0',
          '6. nemmeno la RETTIFICA della fattura altrui');

SELECT is(current_setting('pgtap.sdi_b', true), '0',
          '7. nemmeno l''EVENTO SDI altrui: l''adattatore a due livelli risale');

SELECT is(current_setting('pgtap.scrittura', true), 'RIFIUTATA',
          '8. e non puo'' appendere un log alla fattura altrui (WITH CHECK)');

SELECT is(current_setting('pgtap.senza_veste', true), '0',
          '9. senza veste applicativa non vede niente: fail-closed');

SELECT is(current_setting('pgtap.portale_proprio', true), '1',
          '10. il CLIENTE DEL PORTALE vede il log delle proprie fatture: la seconda veste e'' rispecchiata');

SELECT is(current_setting('pgtap.portale_altrui', true), '0',
          '11. e NON vede quello delle fatture di un altro cliente');

SELECT is(current_setting('pgtap.rett_orfane', true), '0',
          '12. nessuna rettifica visibile la cui fattura RETTIFICATA non lo e'': i due genitori concordano sull''emittente');

SELECT * FROM finish();

ROLLBACK;
