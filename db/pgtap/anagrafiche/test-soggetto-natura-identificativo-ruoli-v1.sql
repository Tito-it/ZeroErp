-- ------------------------------------------------------------
-- SPDX-License-Identifier: AGPL-3.0-or-later
-- pgtap-differiti: escluso — le porte di creazione si chiamano qui da sole
--   (S4: la stessa persona come privato e come ditta), e i soggetti che
--   nascono cosi' restano senza indirizzi: con IMMEDIATE i guard di
--   completezza li rifiuterebbero prima dell'asserzione. I builder vengono
--   PRIMA e chiudono la loro finestra; dopo si apre il DEFERRED dichiarato, e
--   l'unico guard al COMMIT che il test prova (forma giuridica e paese, 32) si
--   porta a IMMEDIATE da solo, per nome.
-- pgTAP test per Zero ERP
--
-- Il soggetto: natura, identificativo fiscale, ruoli. Giro 3 (T5) di
--   brief-db-revisione-anagrafiche §20, decisioni di Tid del 2026-11-23.
--   ChangeSet 20261123-48 … -63; codici e frasi nei CSV config/codici_errore e
--   config/messaggi_errore, righe dei lucchetti in dbops/automation_lock_columns.
--
-- Chi agisce: un operatore senza privilegi e un SUPER_ADMIN, costruiti.
--
-- Elenco test (plan 32):
--   struttura
--    1) la normalizzazione (a01) e' il primo trigger BEFORE di soggetti (COLLATE "C")
--    2) il formato si giudica in a10: _ins BEFORE INSERT, _upd BEFORE UPDATE con WHEN; il trigger senza fase e' ritirato
--    3) il guard dell'identificativo e' OF codice_fiscale, partita_iva, stato_id
--    4) soggetti_ruoli: il lucchetto copre soggetto_id e tipo_ruolo_id; il guard della natura e' solo BEFORE INSERT
--    5) dati_societari: il lucchetto copre soggetto_id; il tipo soggetto in a05 solo BEFORE INSERT; la forma non e' OF soggetto_id
--    6) codice e' NOT NULL
--   S4, il doppione lo dice l'indice
--    7) ⭐ la ditta individuale di chi e' gia' privato (stesso CF, P.IVA in piu') nasce
--    8) ⭐ il doppione del privato: E_ADMIN_CF_DUPLICATO, campo codice_fiscale (prima: 23505 o pre-controllo)
--    9) ... e la frase dice «identificativo fiscale»
--   10) ... anche scritto in minuscolo e con gli spazi
--   D-T5-2, la normalizzazione (S20)
--   11) un CF passato in minuscolo e con gli spazi si salva in maiuscolo, senza spazi
--   12) l'operatore che riscrive lo stesso CF in minuscolo non lo cambia: passa
--   13) ... e il valore resta in maiuscolo
--   14) l'operatore che svuota la P.IVA con '': E_SOGGETTO_ID_FISCALE_IMMUTABILE, campo partita_iva
--   15) ⭐ il SUPER_ADMIN che la svuota con spazi: E_PIVA_OBBLIGATORIA (prima la stringa vuota passava)
--   16) ... con la natura nella frase e senza id (S42)
--   D-T5-3 e S43-1, lo stato
--   17) ⭐ l'operatore che porta lo stato a NULL: E_SOGGETTO_ID_FISCALE_IMMUTABILE, campo stato_id
--   18) ⭐ l'operatore che cambia lo stato: lo stesso
--   19) il form dell'operatore spegne stato_id
--   20) ⭐ il SUPER_ADMIN che porta lo stato a NULL: 23502, lo stato proposto non lo rimette
--   S43-2 e S43-3, il formato
--   21) ⭐ un soggetto con un CF non piu' accettato resta modificabile negli altri campi
--   22) ... e cambiarne il CF lo rigiudica: E_CF_NON_VALIDO
--   23) ⭐ una natura inesistente la dice la FK (23503), non un errore tecnico del validatore
--   S43-8
--   24) ragione_sociale_completa con il solo cognome
--   D-T5-1 (S38), la natura
--   25) ⭐ la check: verso nessuna natura, un solo motivo, E_CAMBIO_NATURA_VERSO_NESSUNA
--   26) ⭐ ... e l'UPDATE e' rifiutato anche al SUPER_ADMIN
--   D-T5-4 (S30, S52), il ruolo
--   27) ⭐ il tipo di un ruolo non si cambia: E_SOGGETTO_RUOLO_TIPO_IMMUTABILE
--   28) ⭐ un ruolo non ammesso per la natura: E_RUOLO_NATURA_NON_AMMESSA, campo tipo_ruolo_id
--   29) ... con ruolo e natura nella frase, senza id (S42)
--   S41, i dati societari
--   30) ⭐ senza forma giuridica: E_DATI_SOCIETARI_FORMA_GIURIDICA_OBBLIGATORIA (prima 23502)
--   31) ⭐ a un privato: parla per primo E_DATI_SOCIETARI_TIPO_SOGGETTO_NON_AMMESSO (a05)
--   32) ⭐ il SUPER_ADMIN cambia lo stato della societa': al COMMIT E_FORMA_GIURIDICA_PAESE
--
-- ⛔ NON PROVATI, e dichiarati:
--   * S41-2, due prime scritture concorrenti dei dati societari: serve una
--     seconda sessione. Il lucchetto FOR NO KEY UPDATE si legge nel corpo.
--   * il lucchetto di dati_societari.soggetto_id in azione: l'applicazione non
--     scrive la tabella (nessun UPDATE possibile da qui); se ne prova il
--     montaggio (5).
--   * la bonifica 80_data -63: sul database del test non c'e' nessuna riga da
--     normalizzare; la regola che applica e' quella del trigger (11).
-- ------------------------------------------------------------

BEGIN;

SELECT plan(32);

-- ============================================================
-- Fixture: le persone, poi i soggetti dei builder (chiudono la loro finestra)
-- ============================================================
CREATE TEMP TABLE _sa AS SELECT * FROM dbops.fn_pgtap_crea_operatore_umano('pgTAP-SA-T5', true);
CREATE TEMP TABLE _op AS SELECT * FROM dbops.fn_pgtap_crea_operatore_umano('pgTAP-OP-T5', false);

DO $ctx$ BEGIN PERFORM script.fn_pgtap_set_contesto_operatore((SELECT auth_user_id FROM _op)); END $ctx$;

CREATE TEMP TABLE _ref AS
SELECT (SELECT id FROM config.tipi_soggetto_dettaglio WHERE codice_interno = 'PR') AS pr,
       (SELECT id FROM config.tipi_soggetto_dettaglio WHERE codice_interno = 'DI') AS di,
       (SELECT min(id) FROM config.stati WHERE codice_iso2 = 'DE')                AS stato_de,
       (SELECT id FROM config.tipi_ruoli WHERE codice_interno = 'VE')              AS ruolo_ve,
       (SELECT id FROM config.tipi_ruoli WHERE codice_interno = 'DI')              AS ruolo_di,
       (SELECT id FROM config.tipi_ruoli WHERE codice_interno = 'EF')              AS ruolo_ef,
       (SELECT max(id) FROM config.tipi_soggetto_dettaglio) + 100000              AS pr_senza_formato;

CREATE TEMP TABLE _sog AS
SELECT dbops.fn_pgtap_crea_soggetto_pf('pgTAP T5 privato')                                   AS privato,
       dbops.fn_pgtap_crea_soggetto_pf('pgTAP T5 ditta', 'pgTAP', (SELECT di FROM _ref))   AS ditta,
       dbops.fn_pgtap_crea_soggetto_pg('pgTAP T5 societa')                                  AS societa;

-- La finestra del test: le porte di creazione si chiamano da sole (vedi l'intestazione).
SET CONSTRAINTS ALL DEFERRED;

-- Il codice e la colonna del rifiuto: fn_log_and_raise_error li mette in CONSTRAINT_NAME e
--   COLUMN_NAME; ogni altro errore torna col suo SQLSTATE.
CREATE OR REPLACE FUNCTION pg_temp.rifiuto(p_sql text) RETURNS text
LANGUAGE plpgsql AS $$
DECLARE
    v_c   pg_catalog.pg_constraint.conname%TYPE;
    v_col pg_catalog.pg_attribute.attname%TYPE;
BEGIN
    EXECUTE p_sql;
    RETURN NULL;
EXCEPTION
    WHEN SQLSTATE 'P0001' THEN
        GET STACKED DIAGNOSTICS v_c = CONSTRAINT_NAME, v_col = COLUMN_NAME;
        -- un errore senza campo torna COLUMN_NAME vuoto, non NULL
        RETURN v_c || ' / ' || COALESCE(NULLIF(v_col, ''), '-');
    WHEN OTHERS THEN
        RETURN SQLSTATE || ' ' || SQLERRM;
END $$;

-- La frase che l'operatore legge.
CREATE OR REPLACE FUNCTION pg_temp.frase(p_sql text) RETURNS text
LANGUAGE plpgsql AS $$
BEGIN
    EXECUTE p_sql;
    RETURN NULL;
EXCEPTION WHEN OTHERS THEN
    RETURN SQLERRM;
END $$;

CREATE OR REPLACE FUNCTION pg_temp.agisci(p_auth_user_id integer) RETURNS void
LANGUAGE plpgsql AS $$
BEGIN
    PERFORM script.fn_pgtap_set_contesto_operatore(p_auth_user_id);
END $$;

-- La porta di creazione della persona fisica, coi soli parametri che il test fa variare.
CREATE OR REPLACE FUNCTION pg_temp.crea_pf(
    p_cognome anagrafiche.soggetti.cognome%TYPE,
    p_cf      anagrafiche.soggetti.codice_fiscale%TYPE,
    p_natura  anagrafiche.soggetti.tipo_soggetto_dettaglio_id%TYPE,
    p_piva    anagrafiche.soggetti.partita_iva%TYPE DEFAULT NULL)
RETURNS anagrafiche.soggetti.id%TYPE
LANGUAGE sql AS $$
    SELECT anagrafiche.fn_crea_soggetto_pf(
               p_cognome                    => p_cognome,
               p_nome                       => 'pgTAP',
               p_codice_fiscale             => p_cf,
               p_email                      => 'pgtap@example.com',
               p_sesso                      => 'M',
               p_stato_iso2                 => 'IT',
               p_tipo_soggetto_dettaglio_id => p_natura,
               p_partita_iva                => p_piva);
$$;

CREATE TEMP TABLE _cf AS
SELECT s.codice_fiscale AS privato FROM anagrafiche.soggetti s WHERE s.id = (SELECT privato FROM _sog);

-- ============================================================
-- Struttura
-- ============================================================
SELECT is(
    (SELECT min(g.tgname::text COLLATE "C")
       FROM pg_trigger g
      WHERE g.tgrelid = 'anagrafiche.soggetti'::regclass
        AND NOT g.tgisinternal
        AND (g.tgtype & 2) <> 0     -- BEFORE
        AND (g.tgtype & 1) <> 0),   -- ROW
    'trg_soggetti_a01_normalize_ins_upd',
    '1) la normalizzazione e'' il primo trigger BEFORE di soggetti');

SELECT is(
    (SELECT string_agg(g.tgname || ':' ||
                       CASE WHEN (g.tgtype & 4)  <> 0 THEN 'I' ELSE '' END ||
                       CASE WHEN (g.tgtype & 16) <> 0 THEN 'U' ELSE '' END ||
                       CASE WHEN pg_get_triggerdef(g.oid) LIKE '% WHEN (%' THEN ':when' ELSE '' END,
                       ',' ORDER BY g.tgname)
       FROM pg_trigger g
      WHERE g.tgrelid = 'anagrafiche.soggetti'::regclass
        AND g.tgfoid = 'anagrafiche.trgfn_soggetti_valida_cf_piva_dispatch'::regproc),
    'trg_soggetti_a10_valida_cf_piva_ins:I,trg_soggetti_a10_valida_cf_piva_upd:U:when',
    '2) il formato si giudica in a10: _ins all''INSERT, _upd all''UPDATE con WHEN');

SELECT is(
    (SELECT string_agg(a.attname, ',' ORDER BY a.attname)
       FROM pg_trigger t
       JOIN pg_attribute a ON a.attrelid = t.tgrelid AND a.attnum = ANY (t.tgattr)
      WHERE t.tgrelid = 'anagrafiche.soggetti'::regclass
        AND t.tgfoid = 'anagrafiche.trgfn_soggetti_guard_id_fiscale_immutabile'::regproc),
    'codice_fiscale,partita_iva,stato_id',
    '3) il guard dell''identificativo e'' OF codice_fiscale, partita_iva, stato_id');

SELECT is(
    (SELECT string_agg(x, ',' ORDER BY x) FROM (
        SELECT 'lock:' || a.attname AS x
          FROM pg_trigger t
          JOIN pg_attribute a ON a.attrelid = t.tgrelid AND a.attnum = ANY (t.tgattr)
         WHERE t.tgrelid = 'anagrafiche.soggetti_ruoli'::regclass
           AND t.tgfoid = 'script.trgfn_lock_columns'::regproc
        UNION ALL
        SELECT 'natura:' || t.tgname || ':' ||
               CASE WHEN (t.tgtype & 16) <> 0 THEN 'U' ELSE 'soloI' END
          FROM pg_trigger t
         WHERE t.tgrelid = 'anagrafiche.soggetti_ruoli'::regclass
           AND t.tgfoid = 'anagrafiche.trgfn_soggetti_ruoli_guard_natura_ammessa'::regproc) s),
    'lock:soggetto_id,lock:tipo_ruolo_id,natura:trg_soggetti_ruoli_a10_guard_natura_ammessa_ins:soloI',
    '4) soggetti_ruoli: lucchetto su soggetto e tipo; il guard della natura solo all''INSERT');

SELECT is(
    (SELECT string_agg(x, ',' ORDER BY x) FROM (
        SELECT 'lock:' || a.attname AS x
          FROM pg_trigger t
          JOIN pg_attribute a ON a.attrelid = t.tgrelid AND a.attnum = ANY (t.tgattr)
         WHERE t.tgrelid = 'anagrafiche.dati_societari'::regclass
           AND t.tgfoid = 'script.trgfn_lock_columns'::regproc
        UNION ALL
        SELECT 'tipo:' || t.tgname || ':' ||
               CASE WHEN (t.tgtype & 16) <> 0 THEN 'U' ELSE 'soloI' END
          FROM pg_trigger t
         WHERE t.tgrelid = 'anagrafiche.dati_societari'::regclass
           AND t.tgfoid = 'anagrafiche.trgfn_dati_societari_guard_tipo_soggetto'::regproc
        UNION ALL
        SELECT 'forma_of_soggetto:' || EXISTS (
                   SELECT 1 FROM pg_trigger t
                     JOIN pg_attribute a ON a.attrelid = t.tgrelid AND a.attnum = ANY (t.tgattr)
                    WHERE t.tgrelid = 'anagrafiche.dati_societari'::regclass
                      AND t.tgfoid = 'anagrafiche.trgfn_dati_societari_guard_forma_giuridica'::regproc
                      AND a.attname = 'soggetto_id')::text) s),
    'forma_of_soggetto:false,lock:soggetto_id,tipo:trg_dati_societari_a05_guard_tipo_soggetto_ins:soloI',
    '5) dati_societari: lucchetto sul soggetto, tipo soggetto in a05 all''INSERT, forma non OF soggetto_id');

SELECT col_not_null('anagrafiche', 'soggetti', 'codice', '6) codice e'' NOT NULL');

-- ============================================================
-- S4: il doppione lo dice l'indice
-- ============================================================
CREATE TEMP TABLE _di AS
SELECT pg_temp.crea_pf('pgTAP T5 ditta del privato', (SELECT privato FROM _cf),
                       (SELECT di FROM _ref), dbops.fn_pgtap_piva_libera()) AS id;

SELECT isnt((SELECT id FROM _di), NULL,
    '7) la ditta individuale di chi e'' gia'' privato (stesso CF, P.IVA in piu'') nasce');

SELECT is(
    pg_temp.rifiuto(format($$SELECT pg_temp.crea_pf('pgTAP T5 doppione', %L, %s)$$,
                           (SELECT privato FROM _cf), (SELECT pr FROM _ref))),
    'E_ADMIN_CF_DUPLICATO / codice_fiscale',
    '8) il doppione del privato: E_ADMIN_CF_DUPLICATO, campo codice_fiscale');

SELECT ok(
    pg_temp.frase(format($$SELECT pg_temp.crea_pf('pgTAP T5 doppione', %L, %s)$$,
                         (SELECT privato FROM _cf), (SELECT pr FROM _ref))) LIKE '%identificativo fiscale%',
    '9) ... e la frase dice «identificativo fiscale»');

SELECT is(
    pg_temp.rifiuto(format($$SELECT pg_temp.crea_pf('pgTAP T5 doppione', %L, %s)$$,
                           ' ' || lower((SELECT privato FROM _cf)) || ' ', (SELECT pr FROM _ref))),
    'E_ADMIN_CF_DUPLICATO / codice_fiscale',
    '10) ... anche scritto in minuscolo e con gli spazi');

-- ============================================================
-- D-T5-2: la normalizzazione
-- ============================================================
CREATE TEMP TABLE _norm AS
SELECT dbops.fn_pgtap_cf_libero() AS cf;
CREATE TEMP TABLE _norm_sog AS
SELECT pg_temp.crea_pf('pgTAP T5 minuscolo',
                       '  ' || lower(left((SELECT cf FROM _norm), 8)) || ' ' || lower(substr((SELECT cf FROM _norm), 9)),
                       (SELECT pr FROM _ref)) AS id;

SELECT is(
    (SELECT codice_fiscale FROM anagrafiche.soggetti WHERE id = (SELECT id FROM _norm_sog)),
    (SELECT cf FROM _norm),
    '11) il CF passato in minuscolo e con gli spazi si salva in maiuscolo, senza spazi');

SELECT is(
    pg_temp.rifiuto(format($$UPDATE anagrafiche.soggetti SET codice_fiscale = lower(codice_fiscale) WHERE id = %L$$,
                           (SELECT privato FROM _sog))),
    NULL,
    '12) l''operatore che riscrive lo stesso CF in minuscolo non lo cambia: passa');

SELECT is(
    (SELECT codice_fiscale FROM anagrafiche.soggetti WHERE id = (SELECT privato FROM _sog)),
    (SELECT privato FROM _cf),
    '13) ... e il valore resta in maiuscolo');

SELECT is(
    pg_temp.rifiuto(format($$UPDATE anagrafiche.soggetti SET partita_iva = '' WHERE id = %L$$,
                           (SELECT ditta FROM _sog))),
    'E_SOGGETTO_ID_FISCALE_IMMUTABILE / partita_iva',
    '14) l''operatore che svuota la P.IVA con la stringa vuota: rifiutato come uno svuotamento');

SELECT pg_temp.agisci((SELECT auth_user_id FROM _sa));

SELECT is(
    pg_temp.rifiuto(format($$UPDATE anagrafiche.soggetti SET partita_iva = '   ' WHERE id = %L$$,
                           (SELECT ditta FROM _sog))),
    'E_PIVA_OBBLIGATORIA / partita_iva',
    '15) il SUPER_ADMIN che svuota la P.IVA con gli spazi: E_PIVA_OBBLIGATORIA');

SELECT ok(
    (SELECT f LIKE '%La partita IVA è obbligatoria per il tipo soggetto Persona Fisica - Ditta Individuale%'
            AND f !~ '[0-9a-f]{8}-[0-9a-f]{4}-'
       FROM (SELECT pg_temp.frase(format($$UPDATE anagrafiche.soggetti SET partita_iva = '   ' WHERE id = %L$$,
                                         (SELECT ditta FROM _sog))) AS f) x),
    '16) ... con la natura nella frase e senza id');

-- ============================================================
-- D-T5-3 e S43-1: lo stato
-- ============================================================
SELECT pg_temp.agisci((SELECT auth_user_id FROM _op));

SELECT is(
    pg_temp.rifiuto(format($$UPDATE anagrafiche.soggetti SET stato_id = NULL WHERE id = %L$$,
                           (SELECT privato FROM _sog))),
    'E_SOGGETTO_ID_FISCALE_IMMUTABILE / stato_id',
    '17) l''operatore che porta lo stato a NULL: E_SOGGETTO_ID_FISCALE_IMMUTABILE, campo stato_id');

SELECT is(
    pg_temp.rifiuto(format($$UPDATE anagrafiche.soggetti SET stato_id = %s WHERE id = %L$$,
                           (SELECT stato_de FROM _ref), (SELECT privato FROM _sog))),
    'E_SOGGETTO_ID_FISCALE_IMMUTABILE / stato_id',
    '18) l''operatore che cambia lo stato: lo stesso');

SELECT ok(
    'stato_id' = ANY (dbops.fn_non_editable_fields('anagrafiche', 'soggetti', (SELECT privato FROM _sog)::text)),
    '19) il form dell''operatore spegne stato_id');

SELECT pg_temp.agisci((SELECT auth_user_id FROM _sa));

SELECT ok(
    pg_temp.rifiuto(format($$UPDATE anagrafiche.soggetti SET stato_id = NULL WHERE id = %L$$,
                           (SELECT privato FROM _sog))) LIKE '23502 %',
    '20) il SUPER_ADMIN che porta lo stato a NULL: NOT NULL (23502), lo stato proposto non lo rimette');

-- ============================================================
-- S43-2 e S43-3: il formato
-- ============================================================
-- Una natura di privato che non valida il CF: il soggetto nasce con un CF che, a configurazione
--   cambiata, il validatore non accetta piu' (la configurazione vale alla scrittura).
INSERT INTO config.tipi_soggetto_dettaglio
       (id, tipo_soggetto_id, stato_iso2, codice_interno, descrizione,
        formato_cf, formato_piva, stato_id, dati_societari_policy,
        piva_obbligatoria, cf_obbligatorio, sesso_policy,
        cliente_pa_ammesso, split_payment_ammesso)
SELECT r.pr_senza_formato, pr.tipo_soggetto_id, pr.stato_iso2, 'PGTAPT5', 'Privato pgTAP T5',
       'NON_APPLICABILE', pr.formato_piva, pr.stato_id, pr.dati_societari_policy,
       -- senza formato il CF non puo' essere obbligatorio (chk_tipi_soggetto_dettaglio_cf_obbl_vs_formato)
       pr.piva_obbligatoria, false, pr.sesso_policy,
       pr.cliente_pa_ammesso, pr.split_payment_ammesso
  FROM config.tipi_soggetto_dettaglio pr, _ref r
 WHERE pr.codice_interno = 'PR';

CREATE TEMP TABLE _vecchio AS
SELECT pg_temp.crea_pf('pgTAP T5 CF vecchio', 'NONVALIDO' || substr(md5(clock_timestamp()::text), 1, 7),
                       (SELECT pr_senza_formato FROM _ref)) AS id;

UPDATE config.tipi_soggetto_dettaglio SET formato_cf = 'ALFANUM_16'
 WHERE id = (SELECT pr_senza_formato FROM _ref);

SELECT is(
    pg_temp.rifiuto(format($$UPDATE anagrafiche.soggetti SET nome = 'pgTAP altro nome' WHERE id = %L$$,
                           (SELECT id FROM _vecchio))),
    NULL,
    '21) un soggetto con un CF non piu'' accettato resta modificabile negli altri campi');

SELECT is(
    pg_temp.rifiuto(format($$UPDATE anagrafiche.soggetti SET codice_fiscale = 'ANCORANONVALIDO1' WHERE id = %L$$,
                           (SELECT id FROM _vecchio))),
    'E_CF_NON_VALIDO / codice_fiscale',
    '22) ... e cambiarne il CF lo rigiudica: E_CF_NON_VALIDO');

SELECT ok(
    pg_temp.rifiuto(format($$INSERT INTO anagrafiche.soggetti (cognome, nome, codice_fiscale, tipo_soggetto_dettaglio_id)
                             VALUES ('pgTAP T5', 'natura inesistente', %L, %s)$$,
                           dbops.fn_pgtap_cf_libero(), (SELECT pr_senza_formato FROM _ref) + 1)) LIKE '23503 %',
    '23) una natura inesistente la dice la FK (23503), non il validatore');

-- ============================================================
-- S43-8: il nome per le liste
-- ============================================================
UPDATE anagrafiche.soggetti SET nome = NULL WHERE id = (SELECT id FROM _vecchio);

SELECT is(
    (SELECT ragione_sociale_completa FROM anagrafiche.soggetti WHERE id = (SELECT id FROM _vecchio)),
    'pgTAP T5 CF vecchio',
    '24) ragione_sociale_completa con il solo cognome');

-- ============================================================
-- D-T5-1 (S38): una natura scritta non si svuota
-- ============================================================
SELECT is(
    (SELECT jsonb_agg(m ->> 'codice')
       FROM anagrafiche.soggetti s,
            jsonb_array_elements(
                anagrafiche.fn_check_cambio_natura_soggetto(
                    s.id, NULL, s.partita_iva, s.cliente_pa, s.split_payment)) m
      WHERE s.id = (SELECT ditta FROM _sog)),
    '["E_CAMBIO_NATURA_VERSO_NESSUNA"]'::jsonb,
    '25) verso nessuna natura: un solo motivo, E_CAMBIO_NATURA_VERSO_NESSUNA');

SELECT is(
    pg_temp.rifiuto(format($$UPDATE anagrafiche.soggetti SET tipo_soggetto_dettaglio_id = NULL WHERE id = %L$$,
                           (SELECT ditta FROM _sog))),
    'E_CAMBIO_NATURA_VERSO_NESSUNA / tipo_soggetto_dettaglio_id',
    '26) ... e l''UPDATE e'' rifiutato anche al SUPER_ADMIN');

-- ============================================================
-- D-T5-4 (S30, S52): il ruolo
-- ============================================================
SELECT pg_temp.agisci((SELECT auth_user_id FROM _op));

CREATE TEMP TABLE _ruolo AS
WITH n AS (
    INSERT INTO anagrafiche.soggetti_ruoli (soggetto_id, tipo_ruolo_id)
    VALUES ((SELECT societa FROM _sog), (SELECT ruolo_ve FROM _ref))
    RETURNING id)
SELECT id FROM n;

SELECT is(
    pg_temp.rifiuto(format($$UPDATE anagrafiche.soggetti_ruoli SET tipo_ruolo_id = %s WHERE id = %s$$,
                           (SELECT ruolo_di FROM _ref), (SELECT id FROM _ruolo))),
    'E_SOGGETTO_RUOLO_TIPO_IMMUTABILE / tipo_ruolo_id',
    '27) il tipo di un ruolo non si cambia: E_SOGGETTO_RUOLO_TIPO_IMMUTABILE');

SELECT is(
    pg_temp.rifiuto(format($$INSERT INTO anagrafiche.soggetti_ruoli (soggetto_id, tipo_ruolo_id) VALUES (%L, %s)$$,
                           (SELECT privato FROM _sog), (SELECT ruolo_ef FROM _ref))),
    'E_RUOLO_NATURA_NON_AMMESSA / tipo_ruolo_id',
    '28) un ruolo non ammesso per la natura: E_RUOLO_NATURA_NON_AMMESSA, campo tipo_ruolo_id');

SELECT ok(
    (SELECT f LIKE '%Il ruolo Emittente fiscale non è ammesso per un soggetto di natura Persona Fisica%'
            AND f !~ '[0-9a-f]{8}-[0-9a-f]{4}-'
       FROM (SELECT pg_temp.frase(format($$INSERT INTO anagrafiche.soggetti_ruoli (soggetto_id, tipo_ruolo_id) VALUES (%L, %s)$$,
                                         (SELECT privato FROM _sog), (SELECT ruolo_ef FROM _ref))) AS f) x),
    '29) ... con ruolo e natura nella frase, senza id');

-- ============================================================
-- S41: i dati societari
-- ============================================================
SELECT is(
    pg_temp.rifiuto(format($$SELECT anagrafiche.fn_scrivi_dati_societari(%L, NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL)$$,
                           (SELECT societa FROM _sog))),
    'E_DATI_SOCIETARI_FORMA_GIURIDICA_OBBLIGATORIA / forma_giuridica_id',
    '30) senza forma giuridica: E_DATI_SOCIETARI_FORMA_GIURIDICA_OBBLIGATORIA');

SELECT is(
    pg_temp.rifiuto(format($$SELECT anagrafiche.fn_scrivi_dati_societari(%L, %s, NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL)$$,
                           (SELECT privato FROM _sog),
                           (SELECT ds.forma_giuridica_id FROM anagrafiche.dati_societari ds
                             WHERE ds.soggetto_id = (SELECT societa FROM _sog)))),
    'E_DATI_SOCIETARI_TIPO_SOGGETTO_NON_AMMESSO / -',
    '31) a un privato: parla per primo E_DATI_SOCIETARI_TIPO_SOGGETTO_NON_AMMESSO');

SELECT pg_temp.agisci((SELECT auth_user_id FROM _sa));

SET CONSTRAINTS anagrafiche.trg_soggetti_def_guard_forma_giuridica_natura_upd IMMEDIATE;

SELECT is(
    pg_temp.rifiuto(format($$UPDATE anagrafiche.soggetti SET stato_id = %s WHERE id = %L$$,
                           (SELECT stato_de FROM _ref), (SELECT societa FROM _sog))),
    'E_FORMA_GIURIDICA_PAESE / forma_giuridica_id',
    '32) il SUPER_ADMIN cambia lo stato della societa'': la forma italiana non regge, E_FORMA_GIURIDICA_PAESE');

SELECT * FROM finish();
ROLLBACK;
