-- ------------------------------------------------------------
-- SPDX-License-Identifier: GPL-3.0-or-later
-- pgTAP test STRUTTURALE — postura di `zeroerp_app` sullo schema `django`
--   django.auth_user · django.auth_user_id_seq · tutte le tabelle dello schema
--
-- Sede della postura: scripts/sql/provision_zeroerp.sql (fase post) (whitelist `_app_schemas`,
--   `django` dentro dal 2026-09-13). Gira DOPO ENTRAMBI i migratori — Liquibase
--   e `manage.py migrate` — in ci-validate.yaml e in scripts/ci-local.sh.
--
-- ⭐ PERCHÉ ESISTE, e non è di oggi. Lo schema `django` lo crea Django
--   (`manage.py migrate`), e per questo era escluso dal provisioning con la
--   dicitura «gestito da Django». Django gestisce il DDL, NON i privilegi:
--   nessun changeSet, nessun passo di Django e nessuno script concedeva a
--   `zeroerp_app` un solo privilegio su `django.auth_user`. Eppure il ruolo
--   applicativo ci passa a ogni login (search_path = django,…) e SEDICI funzioni
--   plpgsql SECURITY INVOKER la leggono e la scrivono — `anagrafiche.fn_crea_auth_user`,
--   `script.fn_crea_utente_tecnico`, `fn_sync_auth_user_is_active`… — cioè ogni
--   creazione di operatore, risorsa umana, utente tecnico, identità.
--   Sul database di sviluppo il privilegio c'era su tutti e 23 gli oggetti,
--   dato A MANO (`zeroerp_app=arwd/titodb`); lo scratch di ci-local.sh lo
--   COPIAVA insieme allo schema (`pg_dump --schema-only` emette le ACL). Su un
--   database ricostruito da zero — la CI — l'app non poteva nemmeno leggerla:
--   47 «permission denied for table auth_user» nel log Postgres della corsa
--   34723456630 (12-09), 23 file morti nel fixture, quasi tutti in
--   `baseline-rossi-ci.tsv` come ERRORE_FIXTURE con la causa mai letta, e
--   cinque «regressioni» il giorno in cui due di loro sono stati riscritti e
--   tre nuovi hanno costruito un operatore. È la forma esatta del `GRANT USAGE`
--   su `maintenance` (2026-09-09): un privilegio che esiste su UNA macchina.
--
-- ⚠️ PERCHÉ GIRA COME L'APPLICAZIONE (runner di default). Il SOGGETTO è
--   `zeroerp_app`: i privilegi che ha e ciò che riesce a fare. Le asserzioni di
--   postura usano `has_*_privilege(ruolo, …)`, che legge il catalogo e non
--   dipende dal ruolo connesso — MAI `information_schema.role_table_grants`,
--   cieco fuori dal ruolo connesso. Le asserzioni di comportamento (9-11)
--   hanno senso SOLO come app: da owner passerebbero tutte.
--
-- ⚠️ IL TEST 8 GUARDA AVANTI, e su dev è rosso finché il provisioning non
--   viene rilanciato. `GRANT … ON ALL TABLES` è una fotografia: copre le
--   tabelle che esistono. Le tabelle che una migration Django FUTURA creerà le
--   copre solo l'`ALTER DEFAULT PRIVILEGES FOR ROLE <chi migra Django>` che
--   il provisioning dichiara per ogni schema della whitelist. Il test la
--   chiede per il proprietario di `django.auth_user` (zeroerp_owner, in ogni
--   ambiente dal 2026-10-15): se manca, il provisioning non e' stato rilanciato
--   dopo che `django` e' entrato in whitelist.
--   Rimedio, una riga:  psql -U postgres -d zeroerp -v fase=post
--     -f scripts/sql/provision_zeroerp.sql
--   Un rosso che dice «il prossimo
--   `manage.py migrate` lascerà l'app fuori dalla tabella nuova» è il mestiere
--   di questo file, non un difetto suo.
--
-- Elenco test (plan 11):
--   POSTURA — django.auth_user, la tabella che sedici funzioni INVOKER attraversano
--    1-3 : SELECT, INSERT, UPDATE concessi (fn_crea_auth_user scrive,
--          fn_sync_auth_user_is_active aggiorna is_active)
--    4   : USAGE su auth_user_id_seq (l'INSERT ha bisogno di nextval)
--   POSTURA — l'intero schema (il search_path dell'app COMINCIA da django)
--    5   : USAGE sullo schema
--    6   : nessuna tabella di `django` senza SELECT, INSERT, UPDATE, DELETE —
--          in caso di rosso stampa quali (stessa postura degli altri 14 schemi),
--          salvo il DELETE su auth_user, tolto il 2026-10-06 e pinnato
--          (brief-db-elimina-credenziale-senza-veste §4.2)
--    7   : nessuna sequenza di `django` senza USAGE
--   POSTURA FUTURA — chi migra Django lascia all'app anche le tabelle nuove
--    8   : ALTER DEFAULT PRIVILEGES del proprietario di auth_user, in schema
--          django, concede SIUD a zeroerp_app (4 privilegi in pg_default_acl)
--   COMPORTAMENTO — quello che l'app riesce a fare davvero
--    9   : SELECT su django.auth_user non solleva (la fixture di 20 file)
--   10   : anagrafiche.fn_crea_auth_user scrive e torna un id > 0 — il
--          percorso esatto dei cinque file rossi del 12-09
--   11   : gemello «esiste»: la riga del 10 è leggibile dall'app
--
-- Read-only: tutto dentro BEGIN;/ROLLBACK;, la riga del test 10 muore col
-- ROLLBACK (su django.auth_user non c'è nessun trigger: niente canale dblink).
-- ------------------------------------------------------------

BEGIN;

-- Contesto applicativo: il file non attraversa tabelle in RLS, ma la riga sta
-- qui perché il preambolo è un contratto (guardrail_pgtap_preambolo). Il
-- helper senza argomento legge config.user_emittenti_fiscali, non
-- django.auth_user: su un database vuoto non solleva.
DO $ctx$ BEGIN PERFORM script.fn_pgtap_set_contesto_operatore(); END $ctx$;

SET CONSTRAINTS ALL IMMEDIATE;

SELECT plan(11);

-- ============================================================
-- POSTURA — django.auth_user
-- ============================================================
SELECT ok(has_table_privilege('zeroerp_app', 'django.auth_user', 'SELECT'),
          '1. zeroerp_app ha SELECT su django.auth_user');
SELECT ok(has_table_privilege('zeroerp_app', 'django.auth_user', 'INSERT'),
          '2. zeroerp_app ha INSERT su django.auth_user (fn_crea_auth_user, fn_crea_utente_tecnico)');
SELECT ok(has_table_privilege('zeroerp_app', 'django.auth_user', 'UPDATE'),
          '3. zeroerp_app ha UPDATE su django.auth_user (fn_sync_auth_user_is_active)');
SELECT ok(has_sequence_privilege('zeroerp_app', 'django.auth_user_id_seq', 'USAGE'),
          '4. zeroerp_app ha USAGE su django.auth_user_id_seq');

-- ============================================================
-- POSTURA — l'intero schema
-- ============================================================
SELECT ok(has_schema_privilege('zeroerp_app', 'django', 'USAGE'),
          '5. zeroerp_app ha USAGE sullo schema django');

-- 6. `is(<elenco>, NULL)`: verde quando l'elenco è vuoto; in rosso pgTAP
--    stampa in «have:» le tabelle scoperte, e per ciascuna cosa manca.
-- ⚠️ La CTE è MATERIALIZED apposta: senza, il planner può valutare
--    `has_*_privilege` PRIMA del filtro su schema e relkind, e la prima
--    toast table del catalogo fa saltare il file («non è una sequenza»,
--    successo scrivendolo). Il filtro deve chiudersi prima della funzione.
WITH tabelle AS MATERIALIZED (
  SELECT c.oid, c.relname
    FROM pg_class c
    JOIN pg_namespace n ON n.oid = c.relnamespace
   WHERE n.nspname = 'django'
     AND c.relkind IN ('r', 'p')
)
SELECT is(
  (SELECT string_agg(
            t.relname || ' [' ||
            concat_ws(',',
              CASE WHEN NOT has_table_privilege('zeroerp_app', t.oid, 'SELECT') THEN 'SELECT' END,
              CASE WHEN NOT has_table_privilege('zeroerp_app', t.oid, 'INSERT') THEN 'INSERT' END,
              CASE WHEN NOT has_table_privilege('zeroerp_app', t.oid, 'UPDATE') THEN 'UPDATE' END,
              CASE WHEN NOT has_table_privilege('zeroerp_app', t.oid, 'DELETE') THEN 'DELETE' END
            ) || ']',
            ', ' ORDER BY t.relname)
     FROM tabelle t
    WHERE NOT (    has_table_privilege('zeroerp_app', t.oid, 'SELECT')
               AND has_table_privilege('zeroerp_app', t.oid, 'INSERT')
               AND has_table_privilege('zeroerp_app', t.oid, 'UPDATE')
               AND has_table_privilege('zeroerp_app', t.oid, 'DELETE'))),
  -- ⭐ Dal 2026-10-06 l'UNICA eccezione dichiarata: il DELETE su auth_user.
  --   Una credenziale si elimina solo da script.fn_elimina_credenziale
  --   (brief-db-elimina-credenziale-senza-veste §4.2; provisioning, blocco
  --   «UNA CREDENZIALE SI ELIMINA SOLO DAL VERBO»). Ogni altra mancanza esce
  --   accanto a questa e fa rosso; e se il DELETE tornasse, rosso lo stesso.
  'auth_user [DELETE]'::text,
  '6. nello schema django all''app manca solo il DELETE su auth_user (la porta e'' il verbo)'
);

WITH sequenze AS MATERIALIZED (
  SELECT c.oid, c.relname
    FROM pg_class c
    JOIN pg_namespace n ON n.oid = c.relnamespace
   WHERE n.nspname = 'django'
     AND c.relkind = 'S'
)
SELECT is(
  (SELECT string_agg(s.relname, ', ' ORDER BY s.relname)
     FROM sequenze s
    WHERE NOT has_sequence_privilege('zeroerp_app', s.oid, 'USAGE')),
  NULL::text,
  '7. nessuna sequenza dello schema django senza USAGE per zeroerp_app'
);

-- ============================================================
-- POSTURA FUTURA — il default di chi migra Django
-- ============================================================
-- Il ruolo che possiede auth_user è quello che ha lanciato `manage.py migrate`,
-- ed è lo stesso che creerà la prossima tabella: il default va letto per LUI,
-- non per un nome fisso (zeroerp in CI e sullo scratch, titodb su dev).
SELECT is(
  (SELECT count(*)
     FROM pg_default_acl d
     JOIN pg_namespace n ON n.oid = d.defaclnamespace
     CROSS JOIN LATERAL aclexplode(d.defaclacl) a
    WHERE n.nspname = 'django'
      AND d.defaclobjtype = 'r'
      AND d.defaclrole = (SELECT c.relowner FROM pg_class c WHERE c.oid = 'django.auth_user'::regclass)
      AND a.grantee = (SELECT r.oid FROM pg_roles r WHERE r.rolname = 'zeroerp_app')
      AND a.privilege_type IN ('SELECT', 'INSERT', 'UPDATE', 'DELETE')),
  4::bigint,
  '8. il proprietario di django.auth_user lascia a zeroerp_app SIUD sulle tabelle FUTURE di django (ALTER DEFAULT PRIVILEGES)'
);

-- ============================================================
-- COMPORTAMENTO — come app, davvero
-- ============================================================
SELECT lives_ok(
  $$SELECT count(*) FROM django.auth_user$$,
  '9. la SELECT su django.auth_user non solleva (è la fixture di venti file)'
);

-- Username ed email usa-e-getta: auth_user ha UNIQUE su entrambi.
CREATE TEMP TABLE _t_postura_django ON COMMIT DROP AS
SELECT 'pgtap_postura_django_' || substr(md5(random()::text), 1, 10) AS username;

SELECT lives_ok(
  $$SELECT anagrafiche.fn_crea_auth_user(
        p_username      => t.username,
        p_email         => t.username || '@pgtap.invalid',
        p_password_hash => '!pgtap-postura-django',
        p_first_name    => 'pgTAP',
        p_last_name     => 'Postura django')
      FROM _t_postura_django t$$,
  '10. anagrafiche.fn_crea_auth_user scrive come zeroerp_app (INSERT + nextval)'
);

SELECT is(
  (SELECT count(*) FROM django.auth_user au JOIN _t_postura_django t ON t.username = au.username),
  1::bigint,
  '11. la riga scritta al 10 è leggibile da zeroerp_app'
);

SELECT * FROM finish();
ROLLBACK;
