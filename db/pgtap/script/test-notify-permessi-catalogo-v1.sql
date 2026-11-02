-- ------------------------------------------------------------
-- SPDX-License-Identifier: AGPL-3.0-or-later
-- pgTAP test per Zero ERP
--
-- Il catalogo dei permessi avvisa il backend al commit
--   Brief: brief-db-permessi-catalogo-notify-cache (R1-R5, §6.5)
--   ChangeSet: 20_code/script/20261004-87 (R1), -88 (R2), 20_code/config/20261004-89 (R3)
--
-- Elenco test (plan 15):
--  1) script.fn_notify_permessi_catalogo(text) esiste
--  2) la leva manuale: fn_notify_permessi_catalogo('manuale') vive
--  3) p_tabella NULL -> E_PARAMETRO_INVALIDO
--  4) p_tabella vuota -> E_PARAMETRO_INVALIDO
--  5-11) ognuna delle sette tabelle ha UN trigger su trgfn_notify_permessi_catalogo,
--        AFTER, per istruzione, su INSERT/UPDATE/DELETE/TRUNCATE, abilitato
--  12) un'istruzione a zero righe su ogni tabella che il GRANT da' in scrittura a chi esegue
--      (per l'app: sei su sette, aree_funzionali e' in sola lettura): il trigger scatta senza errore
--  13) CONSEGNA: un'istruzione committata per tabella -> esattamente una notifica per tabella,
--      sul canale permessi_catalogo, col nome della tabella nel payload
--  14) un'istruzione ANNULLATA (ROLLBACK) non produce notifiche
--  15) due istruzioni nella stessa transazione -> UNA notifica (il caso del mirror CSV)
--
-- Come si prova la consegna (13-15):
--   NOTIFY parte al COMMIT, e questo file chiude in ROLLBACK: dalla sua transazione la
--   consegna non si vede (il test del cambio di reparto si ferma per questo a lives_ok).
--   Qui si aprono DUE sessioni dblink sul DSN del canale di log
--   (myapp.dblink_log_connection): A fa LISTEN, B scrive in autocommit
--   `UPDATE <tabella> SET id = id WHERE false`. Il trigger per istruzione scatta anche a
--   zero righe: B COMMITTA SENZA CAMBIARE UNA RIGA, e il database resta com'era.
--   ⭐ Niente attese a tempo: dopo ogni fase B emette una SENTINELLA
--   (fn_notify_permessi_catalogo('pgtap-sentinella-N')) e si legge A finche' non arriva.
--   Le notifiche di una sessione arrivano nell'ordine dei commit: tutto cio' che la fase ha
--   prodotto e' arrivato prima della sua sentinella.
--   ⚠️ Dove la seconda sessione non si puo' aprire (su dev il DSN e' service=, che un
--   non-superuser non apre) o B non puo' scrivere sul catalogo, 13-15 vanno in skip() col
--   motivo: e' un limite dichiarato, non un verde.
-- ------------------------------------------------------------

-- ⚠️ 1. TRANSAZIONE: niente resta dietro di se'. Le sessioni dblink committano solo
--   istruzioni a zero righe e notifiche.
BEGIN;

-- ⚠️ 2. CONTESTO APPLICATIVO: i test 2-4 e 12 girano come l'applicazione, che scrive i
--   profili di reparto e quindi attraversa questi trigger.
DO $ctx$ BEGIN PERFORM script.fn_pgtap_set_contesto_operatore(); END $ctx$;

-- ⚠️ 3. VINCOLI DIFFERITI: nessuna fixture a due tempi in questo file.
SET CONSTRAINTS ALL IMMEDIATE;

SELECT plan(15);

-- ============================================================
-- Fixture: le sette tabelle del catalogo (brief §1, §6.1)
-- ============================================================
CREATE TEMP TABLE _t_tabelle (tabella text PRIMARY KEY);
INSERT INTO _t_tabelle VALUES
    ('config.area_model_overrides'),
    ('config.aree_funzionali'),
    ('config.azioni_processo'),
    ('config.profili_accesso'),
    ('config.profili_accesso_aree'),
    ('config.profili_accesso_azioni'),
    ('config.profili_accesso_bindings');

-- ============================================================
-- 1-4. La funzione dell'avviso (R1)
-- ============================================================
SELECT has_function(
    'script', 'fn_notify_permessi_catalogo', ARRAY['text'],
    '1. script.fn_notify_permessi_catalogo(text) esiste'
);

SELECT lives_ok(
    $$SELECT script.fn_notify_permessi_catalogo('manuale')$$,
    '2. La leva manuale vive (la notifica muore col ROLLBACK di questo file)'
);

SELECT throws_like(
    $$SELECT script.fn_notify_permessi_catalogo(NULL)$$,
    '%Parametro non valido%',
    '3. p_tabella NULL -> E_PARAMETRO_INVALIDO'
);

SELECT throws_like(
    $$SELECT script.fn_notify_permessi_catalogo('  ')$$,
    '%Parametro non valido%',
    '4. p_tabella vuota -> E_PARAMETRO_INVALIDO'
);

-- ============================================================
-- 5-11. I sette trigger (R3), cercati per FUNZIONE e tabella, non per nome
-- ============================================================
-- tgtype 60 = INSERT(4) + DELETE(8) + UPDATE(16) + TRUNCATE(32); ROW(1) e BEFORE(2)
-- spenti, cioe' AFTER per istruzione. tgenabled 'O' = abilitato.
CREATE TEMP TABLE _t_trigger AS
SELECT tt.tabella,
       count(t.oid)                                   AS quanti,
       string_agg(t.tgtype::int::text || '/' || t.tgenabled::text, ',') AS forma
  FROM _t_tabelle tt
  LEFT JOIN pg_catalog.pg_trigger t
         ON t.tgrelid = tt.tabella::regclass
        AND NOT t.tgisinternal
        AND t.tgfoid = 'script.trgfn_notify_permessi_catalogo()'::regprocedure
 GROUP BY tt.tabella;

SELECT is(
    (SELECT quanti || ':' || COALESCE(forma, '-') FROM _t_trigger WHERE tabella = x.tabella),
    '1:60/O',
    x.n || '. ' || x.tabella || ': un trigger AFTER per istruzione su I/U/D/TRUNCATE, abilitato'
)
  FROM (SELECT tabella, 4 + row_number() OVER (ORDER BY tabella) AS n FROM _t_tabelle) x
 ORDER BY x.n;

-- ============================================================
-- 12. Il trigger scatta come l'applicazione, senza errore
-- ============================================================
-- ⚠️ Solo le tabelle che il GRANT concede in scrittura a chi esegue. Il perimetro e' il
--   CONTRATTO dei privilegi, non una scelta del test: config.aree_funzionali per l'app e' in
--   sola lettura (la scrivono solo il seed e il migratore), e un UPDATE morirebbe su 42501
--   PRIMA del trigger — un rosso del test, non del trigger (2026-10-04, prima corsa di Tid).
--   Le tabelle escluse qui sono provate dal 13, dove B scrive col DSN del proprietario.
CREATE TEMP TABLE _t_scrivibili AS
SELECT tabella FROM _t_tabelle
 WHERE has_table_privilege(current_user, tabella, 'UPDATE');

SELECT CASE WHEN EXISTS (SELECT 1 FROM _t_scrivibili) THEN
    lives_ok(
        (SELECT string_agg(format('UPDATE %s SET id = id WHERE false', tabella), '; ' ORDER BY tabella)
           FROM _t_scrivibili),
        '12. Un''istruzione a zero righe su ogni tabella che chi esegue puo'' scrivere ('
        || (SELECT string_agg(tabella, ', ' ORDER BY tabella) FROM _t_scrivibili)
        || '): il trigger scatta senza errore'
    )
ELSE
    -- nessuna tabella scrivibile: il test non ha niente da provare, e lo dice in rosso
    fail('12. Chi esegue non puo'' scrivere nessuna delle sette tabelle: il trigger non e'' provato')
END;

-- ============================================================
-- 13-15. La consegna, con due sessioni vere
-- ============================================================
CREATE TEMP TABLE _t_notify (fase int, canale text, tabella text);
CREATE TEMP TABLE _t_dblink AS SELECT false AS provata, ''::text AS motivo;

DO $consegna$
DECLARE
    v_dsn   text := current_setting('myapp.dblink_log_connection', true);
    v_t     text;
    v_fase  int;
    v_giri  int;
BEGIN
    IF v_dsn IS NULL OR btrim(v_dsn) = '' THEN
        UPDATE _t_dblink SET motivo = 'myapp.dblink_log_connection non impostata';
        RETURN;
    END IF;

    BEGIN
        PERFORM dblink_connect('pgtap_notify_a', v_dsn || ' application_name=PGTAP-NOTIFY-A');
        PERFORM dblink_connect('pgtap_notify_b', v_dsn || ' application_name=PGTAP-NOTIFY-B');
    EXCEPTION WHEN OTHERS THEN
        UPDATE _t_dblink SET motivo = 'dblink_connect rifiutato (' || SQLSTATE || '): ' || SQLERRM;
        IF 'pgtap_notify_a' = ANY (COALESCE(dblink_get_connections(), '{}')) THEN
            PERFORM dblink_disconnect('pgtap_notify_a');
        END IF;
        RETURN;
    END;

    BEGIN
        -- ⛔ B aspetta i lock di QUESTA transazione, che aspetta B dentro dblink: uno stallo
        --   fra due sessioni che PostgreSQL non vede. Succede quando il file gira dopo una
        --   DDL sulle sette tabelle nella stessa transazione (la prova pre-apply: CREATE
        --   TRIGGER tiene SHARE ROW EXCLUSIVE). Col lock_timeout B si arrende in 5 s, e
        --   13-15 vanno in skip col motivo invece di appendere la corsa.
        PERFORM dblink_exec('pgtap_notify_b', 'SET lock_timeout = ''5s''');
        PERFORM dblink_exec('pgtap_notify_a', 'LISTEN permessi_catalogo');

        FOR v_fase IN 1..2 LOOP
            IF v_fase = 1 THEN
                -- 13. un'istruzione committata per tabella
                FOR v_t IN SELECT tabella FROM _t_tabelle ORDER BY tabella LOOP
                    PERFORM dblink_exec('pgtap_notify_b',
                                        format('UPDATE %s SET id = id WHERE false', v_t));
                END LOOP;
            ELSE
                -- 14. annullata: niente
                PERFORM dblink_exec('pgtap_notify_b', 'BEGIN');
                PERFORM dblink_exec('pgtap_notify_b',
                                    'UPDATE config.aree_funzionali SET id = id WHERE false');
                PERFORM dblink_exec('pgtap_notify_b', 'ROLLBACK');
                -- 15. due istruzioni, una transazione: una notifica
                PERFORM dblink_exec('pgtap_notify_b', 'BEGIN');
                PERFORM dblink_exec('pgtap_notify_b',
                                    'UPDATE config.azioni_processo SET id = id WHERE false');
                PERFORM dblink_exec('pgtap_notify_b',
                                    'UPDATE config.azioni_processo SET id = id WHERE false');
                PERFORM dblink_exec('pgtap_notify_b', 'COMMIT');
            END IF;

            -- dentro un DO: dblink_exec rifiuta un'istruzione che restituisce righe (2F003)
            PERFORM dblink_exec('pgtap_notify_b',
                format('DO %L', format('BEGIN PERFORM script.fn_notify_permessi_catalogo(%L); END',
                                       'pgtap-sentinella-' || v_fase)));

            v_giri := 0;
            LOOP
                INSERT INTO _t_notify (fase, canale, tabella)
                SELECT v_fase, n.notify_name, (n.extra::jsonb ->> 'tabella')
                  FROM dblink_get_notify('pgtap_notify_a') n;
                EXIT WHEN EXISTS (SELECT 1 FROM _t_notify
                                   WHERE tabella = 'pgtap-sentinella-' || v_fase);
                v_giri := v_giri + 1;
                IF v_giri > 200 THEN   -- 10 s: la sentinella non e' arrivata
                    RAISE EXCEPTION 'sentinella % non arrivata in 10 s', v_fase;
                END IF;
                PERFORM pg_sleep(0.05);
            END LOOP;
        END LOOP;

        UPDATE _t_dblink SET provata = true;
    EXCEPTION WHEN OTHERS THEN
        -- B senza privilegio di scrittura sul catalogo (42501), o sentinella persa:
        -- la consegna non e' provata, e si dice perche'.
        UPDATE _t_dblink SET motivo = 'consegna non provabile (' || SQLSTATE || '): ' || SQLERRM;
    END;

    PERFORM dblink_disconnect('pgtap_notify_a');
    PERFORM dblink_disconnect('pgtap_notify_b');
END
$consegna$;

SELECT CASE WHEN (SELECT provata FROM _t_dblink) THEN
    is(
        (SELECT array_agg(canale || ':' || tabella ORDER BY tabella)
           FROM _t_notify WHERE fase = 1 AND tabella NOT LIKE 'pgtap-sentinella-%'),
        (SELECT array_agg('permessi_catalogo:' || tabella ORDER BY tabella) FROM _t_tabelle),
        '13. Un''istruzione committata per tabella: una notifica ciascuna, canale e tabella giusti'
    )
ELSE
    skip('13. consegna non provata: ' || (SELECT motivo FROM _t_dblink), 1)
END;

SELECT CASE WHEN (SELECT provata FROM _t_dblink) THEN
    is(
        (SELECT count(*)::int FROM _t_notify WHERE fase = 2 AND tabella = 'config.aree_funzionali'),
        0,
        '14. Un''istruzione annullata (ROLLBACK) non produce notifiche'
    )
ELSE
    skip('14. consegna non provata: ' || (SELECT motivo FROM _t_dblink), 1)
END;

SELECT CASE WHEN (SELECT provata FROM _t_dblink) THEN
    is(
        (SELECT count(*)::int FROM _t_notify WHERE fase = 2 AND tabella = 'config.azioni_processo'),
        1,
        '15. Due istruzioni nella stessa transazione: una notifica sola (il caso del mirror CSV)'
    )
ELSE
    skip('15. consegna non provata: ' || (SELECT motivo FROM _t_dblink), 1)
END;

SELECT * FROM finish();

-- Il ROLLBACK e' la garanzia: le sessioni dblink hanno committato solo istruzioni a zero
-- righe e notifiche, e questo file non lascia nulla dietro di se'.
ROLLBACK;
