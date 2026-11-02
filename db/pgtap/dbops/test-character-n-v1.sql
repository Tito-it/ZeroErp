-- ------------------------------------------------------------
-- SPDX-License-Identifier: AGPL-3.0-or-later
-- pgtap-contesto: escluso — test STRUTTURALE sul catalogo (pg_attribute,
--   pg_proc, pg_constraint): nessuna tabella sotto RLS viene letta, il
--   contesto operatore non cambierebbe nessuna risposta.
-- pgTAP test per Zero ERP
--
-- Un testo non si riempie di spazi: character(n) non si usa.
--   Brief: brief-db-character-n-spazi-di-riempimento (D-4 e D-5 di Tid,
--   2026-10-10). ChangeSet: 20261010-26 (conversione) ... -36.
--   Regola: linee-guida-sql.md §7e.
--
-- Elenco test (plan 8):
--  1) ⛔ nessuna colonna character(n) fuori dal registro dichiarato
--  2) il registro non e' stantio: ogni sua colonna e' ancora character(n)
--  3) ⛔ nessuna funzione con character in firma o nel risultato fuori dal
--        registro dichiarato
--  4) il registro delle funzioni non e' stantio
--  5) gemello «esiste»: la lente delle colonne vede character(n) (il test 1
--        non e' muto per un catalogo letto male)
--  6) le undici colonne convertite dal 20261010-26 sono varchar, con la
--        STESSA lunghezza di prima (destinatario_fe: varchar(1) dal -37, D-6;
--        magazzino.note.lingua e' uscita col 20261101-17: e' diventata
--        id_lingua, un riferimento a config.lingue, e il suo «non vuoto» non c'e' piu')
--  7) ognuna ha il suo CHECK (forma per la sigla, «non vuoto» per le altre)
--  8) storico: solo le colonne a un carattere della macchina dello storico
--
-- ⭐ PERCHE' UN REGISTRO E NON «ZERO». Le colonne del registro hanno un
--   dominio a lunghezza ESATTA (ISO 3166 a 2 e 3 lettere, ISO 4217, flag a un
--   carattere): li' il padding non puo' nascere. Convertirle non e' stato
--   deciso (brief §2.2). Il registro puo' solo CALARE: una colonna nuova
--   character(n) fa rosso il test 1, e una colonna convertita senza togliere
--   la riga fa rosso il test 2.
--
-- ⭐ LE FUNZIONI. character senza lunghezza vale character(1), e RETURN QUERY
--   pretende il tipo identico: una firma bpchar sopra una colonna varchar (o
--   viceversa) rompe la chiamata a runtime, non al CREATE (caso reale:
--   fn_search_stradario, aprile-agosto 2026). Le funzioni del registro hanno
--   character perche' ancorano con %TYPE una colonna del registro delle
--   colonne (sesso, stato_iso2, esigibilita, status, ...): quando quella
--   colonna si convertira', vanno ricreate e tolte da qui.
--
-- ⚠️ pg_attribute e non information_schema.columns: la vista standard mostra
--   solo le colonne su cui il ruolo connesso ha un privilegio.
-- ⚠️ Fuori dalla lente: gli schemi di sistema, le tabelle e le funzioni delle
--   estensioni (pg_depend 'e'), le partizioni (seguono la madre), gli schemi
--   temporanei. Lo storico ha un test suo (8): le sue tabelle ombra le genera
--   la macchina dello storico, con un vocabolario a un carattere.
-- ------------------------------------------------------------

BEGIN;

SET CONSTRAINTS ALL IMMEDIATE;

SELECT plan(8);

-- ============================================================
-- I due registri dichiarati (aggiornati il 2026-10-10)
-- ============================================================
CREATE TEMP TABLE _registro_colonne (colonna text PRIMARY KEY) ON COMMIT DROP;
INSERT INTO _registro_colonne VALUES
    -- ISO 3166 alpha-2 / alpha-3, ISO 4217
    ('anagrafiche.conti_bancari.paese'),
    ('config.stati.codice_iso2'),
    ('config.stati.codice_iso3'),
    ('config.valute.iso_code'),
    -- codice catastale a due caratteri
    ('anagrafiche.catasto_unita_immobiliari.destinazione_immobile'),
    -- flag e codici a un carattere
    ('anagrafiche.catasto_unita_immobiliari.tipo_accatastamento'),
    ('anagrafiche.clienti.garanzia_tipo'),
    ('anagrafiche.istanze_utilities.proprietario_inquilino'),
    ('anagrafiche.soggetti.cliente_pa'),
    ('anagrafiche.soggetti.sesso'),
    ('anagrafiche.soggetti.split_payment'),
    ('config.conti_contabili.tipo_conto'),
    ('config.stati_cliente.abilita_fattura'),
    ('config.stati_cliente.check_lettura'),
    ('config.stati_cliente.stato_cliente_ia'),
    ('config.tipi_utenze.tipo_pdr_std'),
    ('vendite.fatturazione_lotti_log.status'),
    ('vendite.fatture_log.status'),
    ('vendite.fatture_riepiloghi_iva.esigibilita'),
    ('vendite.fatture_righe.esigibilita'),
    ('vendite.preventivi_riepiloghi_iva.esigibilita');

CREATE TEMP TABLE _registro_funzioni (funzione text PRIMARY KEY) ON COMMIT DROP;
INSERT INTO _registro_funzioni VALUES
    ('anagrafiche.fn_crea_operatore_v2'),      -- p_sesso
    ('anagrafiche.fn_crea_soggetto_pf'),       -- p_sesso, p_stato_iso2
    ('anagrafiche.fn_crea_soggetto_pg'),       -- p_stato_iso2
    ('dbops.fn_admin_merge_comune'),           -- p_event_type
    ('dbops.fn_admin_merge_stradario'),        -- p_event_type
    ('script.fn_esigibilita_iva'),             -- p_cliente_split_payment, esigibilita
    ('script.fn_esigibilita_iva_documento'),   -- esigibilita
    ('script.fn_get_indirizzi_by_ruolo'),      -- stato_iso2
    ('script.fn_get_indirizzo'),               -- stato_iso2
    ('script.fn_get_soggetto_dati_by_ruolo'),  -- sesso
    ('vendite.fn_esigibilita_iva_fattura'),    -- esigibilita
    ('vendite.fn_list_lotto_segnalazioni'),    -- p_livello, livello
    ('vendite.fn_log_pipeline_fase'),          -- p_status
    ('vendite.fn_resolve_iva_riga'),           -- p_paese_*, esigibilita
    ('vendite.fn_resolve_iva_riga_it');        -- esigibilita

-- ============================================================
-- Le lenti
-- ============================================================
CREATE TEMP TABLE _colonne ON COMMIT DROP AS
SELECT n.nspname || '.' || c.relname || '.' || a.attname AS colonna,
       n.nspname                                          AS schema_nome,
       a.attname                                          AS attname,
       a.atttypmod                                        AS typmod
  FROM pg_attribute a
  JOIN pg_class c     ON c.oid = a.attrelid
  JOIN pg_namespace n ON n.oid = c.relnamespace
 WHERE c.relkind IN ('r', 'p')
   AND NOT c.relispartition
   AND a.atttypid = 'bpchar'::regtype
   AND a.attnum > 0 AND NOT a.attisdropped
   AND n.nspname NOT IN ('pg_catalog', 'information_schema')
   AND n.nspname NOT LIKE 'pg\_temp\_%'
   AND n.nspname NOT LIKE 'pg\_toast%'
   AND NOT EXISTS (SELECT 1 FROM pg_depend d
                    WHERE d.classid = 'pg_class'::regclass
                      AND d.objid   = c.oid
                      AND d.deptype = 'e');

CREATE TEMP TABLE _funzioni ON COMMIT DROP AS
SELECT DISTINCT n.nspname || '.' || p.proname AS funzione
  FROM pg_proc p
  JOIN pg_namespace n ON n.oid = p.pronamespace
 WHERE n.nspname NOT IN ('pg_catalog', 'information_schema', 'public', 'topology', 'pgagent')
   AND n.nspname NOT LIKE 'pg\_%'
   AND NOT EXISTS (SELECT 1 FROM pg_depend d
                    WHERE d.classid = 'pg_proc'::regclass
                      AND d.objid   = p.oid
                      AND d.deptype = 'e')
   AND ('bpchar'::regtype = ANY (p.proargtypes::oid[])
        OR 'bpchar'::regtype = ANY (coalesce(p.proallargtypes, '{}'::oid[]))
        OR p.prorettype = 'bpchar'::regtype);

-- ============================================================
-- 1-2. Colonne
-- ============================================================
SELECT is(
    (SELECT coalesce(string_agg(colonna, ', ' ORDER BY colonna), '')
       FROM _colonne
      WHERE schema_nome <> 'storico'
        AND colonna NOT IN (SELECT colonna FROM _registro_colonne)),
    '',
    '1) nessuna colonna character(n) fuori dal registro: un testo a lunghezza variabile e'' varchar (linee-guida-sql §7e)'
);

SELECT is(
    (SELECT coalesce(string_agg(r.colonna, ', ' ORDER BY r.colonna), '')
       FROM _registro_colonne r
      WHERE r.colonna NOT IN (SELECT colonna FROM _colonne)),
    '',
    '2) il registro delle colonne non e'' stantio: una colonna convertita esce anche dal registro'
);

-- ============================================================
-- 3-4. Funzioni
-- ============================================================
SELECT is(
    (SELECT coalesce(string_agg(funzione, ', ' ORDER BY funzione), '')
       FROM _funzioni
      WHERE funzione NOT IN (SELECT funzione FROM _registro_funzioni)),
    '',
    '3) nessuna funzione con character in firma o nel risultato fuori dal registro'
);

SELECT is(
    (SELECT coalesce(string_agg(r.funzione, ', ' ORDER BY r.funzione), '')
       FROM _registro_funzioni r
      WHERE r.funzione NOT IN (SELECT funzione FROM _funzioni)),
    '',
    '4) il registro delle funzioni non e'' stantio'
);

-- ============================================================
-- 5. La lente vede
-- ============================================================
SELECT ok(
    EXISTS (SELECT 1 FROM _colonne WHERE colonna = 'config.stati.codice_iso2'),
    '5) la lente vede le colonne character(n): config.stati.codice_iso2 c''e'''
);

-- ============================================================
-- 6-7. Le undici colonne del 20261010-26 (la dodicesima, magazzino.note.lingua, e' id_lingua dal 20261101-17)
-- ============================================================
CREATE TEMP TABLE _convertite (colonna text, tipo text, vincolo text, definizione text) ON COMMIT DROP;
INSERT INTO _convertite VALUES
    ('config.province.sigla',                               'character varying(10)',  'chk_province_sigla_forma',                         'CHECK (((sigla)::text ~ ''^[A-Z0-9]{1,10}$''::text))'),
    ('config.province.descrizione',                         'character varying(80)',  'chk_province_descrizione_non_vuota',               'CHECK ((btrim((descrizione)::text) <> ''''::text))'),
    -- D-6 (20261010-37): e' il canale FE, P o C; il «non vuoto» e' diventato il vocabolario
    ('anagrafiche.dati_societari.destinatario_fe',          'character varying(1)',   'chk_dati_societari_destinatario_fe_canale',        'CHECK (((destinatario_fe)::text = ANY ((ARRAY[''P''::character varying, ''C''::character varying])::text[])))'),
    ('anagrafiche.gestori.descrizione',                     'character varying(50)',  'chk_gestori_descrizione_non_vuota',                'CHECK ((btrim((descrizione)::text) <> ''''::text))'),
    ('anagrafiche.gestori.cd_prod_software',                'character varying(20)',  'chk_gestori_cd_prod_software_non_vuoto',           'CHECK ((btrim((cd_prod_software)::text) <> ''''::text))'),
    ('config.ambiti.descrizione',                           'character varying(100)', 'chk_ambiti_descrizione_non_vuota',                 'CHECK ((btrim((descrizione)::text) <> ''''::text))'),
    ('config.stati_cliente.descrizione_breve',              'character varying(20)',  'chk_stati_cliente_descrizione_breve_non_vuota',    'CHECK ((btrim((descrizione_breve)::text) <> ''''::text))'),
    ('anagrafiche.catasto_unita_immobiliari.foglio_catastale',  'character varying(5)', 'chk_catasto_unita_immobiliari_foglio_catastale_non_vuoto',  'CHECK ((btrim((foglio_catastale)::text) <> ''''::text))'),
    ('anagrafiche.catasto_unita_immobiliari.particella',        'character varying(5)', 'chk_catasto_unita_immobiliari_particella_non_vuota',        'CHECK ((btrim((particella)::text) <> ''''::text))'),
    ('anagrafiche.catasto_unita_immobiliari.sezione_catastale', 'character varying(5)', 'chk_catasto_unita_immobiliari_sezione_catastale_non_vuota', 'CHECK ((btrim((sezione_catastale)::text) <> ''''::text))'),
    ('anagrafiche.catasto_unita_immobiliari.subalterno',        'character varying(5)', 'chk_catasto_unita_immobiliari_subalterno_non_vuoto',        'CHECK ((btrim((subalterno)::text) <> ''''::text))');

SELECT is(
    (SELECT coalesce(string_agg(x.colonna || ' e'' ' || coalesce(format_type(a.atttypid, a.atttypmod), 'assente'), ', ' ORDER BY x.colonna), '')
       FROM _convertite x
       LEFT JOIN pg_namespace n ON n.nspname = split_part(x.colonna, '.', 1)
       LEFT JOIN pg_class c     ON c.relnamespace = n.oid AND c.relname = split_part(x.colonna, '.', 2)
       LEFT JOIN pg_attribute a ON a.attrelid = c.oid AND a.attname = split_part(x.colonna, '.', 3) AND NOT a.attisdropped
      WHERE format_type(a.atttypid, a.atttypmod) IS DISTINCT FROM x.tipo),
    '',
    '6) le undici colonne del 20261010-26 sono varchar, con la lunghezza di prima'
);

SELECT is(
    (SELECT coalesce(string_agg(x.vincolo, ', ' ORDER BY x.vincolo), '')
       FROM _convertite x
       LEFT JOIN pg_namespace n ON n.nspname = split_part(x.colonna, '.', 1)
       LEFT JOIN pg_class c     ON c.relnamespace = n.oid AND c.relname = split_part(x.colonna, '.', 2)
       LEFT JOIN pg_constraint k ON k.conrelid = c.oid AND k.conname = x.vincolo AND k.contype = 'c'
      WHERE pg_get_constraintdef(k.oid) IS DISTINCT FROM x.definizione),
    '',
    '7) ognuna ha il suo CHECK, nella forma esatta (sigla: forma; le altre: non vuoto)'
);

-- ============================================================
-- 8. Storico: solo il vocabolario a un carattere della macchina
-- ============================================================
SELECT is(
    (SELECT coalesce(string_agg(colonna, ', ' ORDER BY colonna), '')
       FROM _colonne
      WHERE schema_nome = 'storico'
        AND NOT (attname IN ('change_type', 'tipo_evento', 'tipo_operazione')
                 AND typmod = 5)),   -- character(1): typmod = 1 + VARHDRSZ
    '',
    '8) nello storico solo change_type / tipo_evento / tipo_operazione a un carattere'
);

SELECT * FROM finish();
ROLLBACK;
