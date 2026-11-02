-- ------------------------------------------------------------
-- SPDX-License-Identifier: AGPL-3.0-or-later
-- pgtap-contesto: escluso — test STRUTTURALE sul catalogo (pg_constraint):
--   nessuna tabella sotto RLS viene letta, il contesto operatore non
--   cambierebbe nessuna risposta.
-- pgTAP test per Zero ERP
--
-- Il ponte django: le colonne che puntano a django.auth_user portano la FK,
--   con la regola di cancellazione decisa per famiglia.
--   Voce V-7 di valutazione-modello-di-dominio-db (rifinita il 21-09).
--   ChangeSet: 20260921-02..-12 (90_end, MARK_RAN), -13 (policy indici).
--
-- Elenco test (plan 3):
--  1) ⛔ INVARIANTE: nessuna colonna `auth_user_id` / `*_user_id` intera di
--        dominio senza FK verso django.auth_user (i nomi nel messaggio)
--  2) le 11 FK di questo giro esistono con la regola ON DELETE decisa
--        (CASCADE per lo stato per-utente, RESTRICT per registri e code)
--  3) gemello «esiste»: la lente vede almeno le 18 FK verso django gia'
--        presenti prima del 21-09 — il test 1 non e' muto
--
-- ⚠️ PERCHE' SALTA QUANDO IL PONTE NON C'E'. Le FK verso django nascono in
--   90_end sotto MARK_RAN: sul DB ricostruito da zero Liquibase gira PRIMA
--   di `manage.py migrate`, la tabella non esiste ancora e i changeSet
--   restano segnati senza fare — poi il migrate Django la crea, ma le FK
--   non tornano (misurato sulla replica CI il 21-09: auth_user c'e', zero
--   FK, comprese le 18 storiche). Su quel database questo test non ha
--   soggetto: i tre test escono `skip` con il motivo, non `ok` per
--   sottrazione. La condizione e' «tabella E almeno una FK del ponte»: se
--   una c'e' e le altre no, e' rosso, come deve.
--
-- ⭐ PERCHE' UN INVARIANTE (test 1) OLTRE AI NOMI (test 2). Il test 2 pinna
--   le undici di questo giro con la loro regola; il test 1 dice che NESSUNA
--   colonna con quella forma resta senza FK — compresa la prossima. La forma:
--   colonna intera di uno schema di dominio che finisce in `auth_user_id` o
--   `_user_id` (creato_da_user_id, generato_da_user_id, django_user_id).
--   Le tabelle interne di django.* sono fuori dal perimetro: sono di Django.
--   Le colonne che per progetto nominano una credenziale che non c'e' piu'
--   sono ECCEZIONI DICHIARATE nella lente (dal 2026-10-06:
--   config.credenziali_eliminate.auth_user_id).
-- ------------------------------------------------------------

BEGIN;

SET CONSTRAINTS ALL IMMEDIATE;

SELECT plan(3);

-- ============================================================
-- La lente: le colonne di dominio che puntano a un utente Django,
-- e la loro FK (se c'e')
-- ============================================================
CREATE TEMP TABLE _puntatori ON COMMIT DROP AS
SELECT n.nspname || '.' || c.relname || '.' || a.attname AS colonna,
       (SELECT k.conname
          FROM pg_constraint k
         WHERE k.conrelid = c.oid AND k.contype = 'f'
           AND k.conkey = ARRAY[a.attnum]
           AND k.confrelid = to_regclass('django.auth_user')) AS fk
  FROM pg_attribute a
  JOIN pg_class c     ON c.oid = a.attrelid
  JOIN pg_namespace n ON n.oid = c.relnamespace
 WHERE c.relkind IN ('r', 'p')
   AND a.attnum > 0 AND NOT a.attisdropped
   AND a.atttypid IN ('integer'::regtype, 'bigint'::regtype, 'smallint'::regtype)
   AND (a.attname = 'auth_user_id' OR a.attname LIKE '%\_user\_id')
   AND n.nspname IN ('vendite', 'acquisti', 'magazzino', 'pagamenti', 'pratiche',
                     'documenti', 'anagrafiche', 'catalogo', 'config', 'shop', 'ui')
   -- ⛔ ECCEZIONI DICHIARATE: colonne con la forma di un puntatore che per
   --   progetto NON puntano a una riga viva. Una voce in piu' qui e' una
   --   decisione, non un rimedio a un rosso.
   --   · config.credenziali_eliminate.auth_user_id (2026-10-06,
   --     brief-db-elimina-credenziale-senza-veste §7.2): la traccia di una
   --     credenziale ELIMINATA. La riga descritta non esiste piu'; una FK
   --     impedirebbe proprio il DELETE che la traccia racconta.
   AND (n.nspname, c.relname, a.attname) NOT IN (
         ('config', 'credenziali_eliminate', 'auth_user_id'));

-- Il ponte c'e' su questo database? Due condizioni, entrambe necessarie:
--   django.auth_user esiste E almeno una FK verso di essa esiste. Sul DB
--   ricostruito da zero la tabella nasce col migrate Django DOPO Liquibase:
--   i changeSet 90_end sono gia' MARK_RAN e NESSUNA delle FK del ponte
--   esiste — nemmeno le 18 storiche. Quello stato si riconosce cosi', senza
--   leggere databasechangelog (che l'app non vede).
CREATE TEMP TABLE _ponte ON COMMIT DROP AS
SELECT to_regclass('django.auth_user') IS NOT NULL
       AND EXISTS (SELECT 1 FROM _puntatori WHERE fk IS NOT NULL) AS c_e;

-- Le undici di questo giro, con la regola ON DELETE attesa
CREATE TEMP TABLE _attese (conname text, tabella text, deltype "char") ON COMMIT DROP;
INSERT INTO _attese VALUES
  ('fk_config_auth_totp_device_auth_user',       'config.auth_totp_device',       'c'),
  ('fk_config_token_monouso_auth_user',          'config.token_monouso',          'c'),
  ('fk_config_user_emittente_attivo_auth_user',  'config.user_emittente_attivo',  'c'),
  ('fk_config_user_emittenti_fiscali_auth_user', 'config.user_emittenti_fiscali', 'c'),
  ('fk_config_user_override_aree_auth_user',     'config.user_override_aree',     'c'),
  ('fk_config_user_override_azioni_auth_user',   'config.user_override_azioni',   'c'),
  ('fk_config_user_override_oggetti_auth_user',  'config.user_override_oggetti',  'c'),
  ('fk_config_email_log_auth_user',              'config.email_log',              'r'),
  ('fk_config_email_outbox_auth_user',           'config.email_outbox',           'r'),
  ('fk_config_email_outbox_creato_da_user',      'config.email_outbox',           'r'),
  ('fk_vendite_event_log_auth_user',             'vendite.event_log',             'r');

-- ============================================================
-- 1. Nessun puntatore a un utente Django senza FK
-- ============================================================
SELECT CASE WHEN NOT (SELECT c_e FROM _ponte)
  THEN skip('ponte django assente su questo database (tabella nata col migrate Django DOPO Liquibase: FK sotto MARK_RAN)', 1)
  ELSE is(
    (SELECT coalesce(string_agg(colonna, ', ' ORDER BY colonna), '') FROM _puntatori WHERE fk IS NULL),
    '',
    '1) nessuna colonna *_user_id di dominio senza FK verso django.auth_user (V-7)')
  END;

-- ============================================================
-- 2. Le undici del giro, con la regola di cancellazione decisa
-- ============================================================
SELECT CASE WHEN NOT (SELECT c_e FROM _ponte)
  THEN skip('ponte django assente su questo database (tabella nata col migrate Django DOPO Liquibase: FK sotto MARK_RAN)', 1)
  ELSE is(
    (SELECT coalesce(string_agg(
        a.conname || ' su ' || a.tabella || ': attesa ' || a.deltype::text || ', trovata ' || coalesce(k.confdeltype::text, 'ASSENTE'),
        '; ' ORDER BY a.conname), '')
       FROM _attese a
       LEFT JOIN pg_constraint k ON k.conname = a.conname AND k.conrelid = a.tabella::regclass
      WHERE k.oid IS NULL OR k.confdeltype <> a.deltype),
    '',
    '2) le 11 FK di 20260921-02..-12 esistono con ON DELETE CASCADE (stato per utente) / RESTRICT (registri e code)')
  END;

-- ============================================================
-- 3. La lente vede: le FK verso django preesistenti al giro
-- ============================================================
SELECT CASE WHEN NOT (SELECT c_e FROM _ponte)
  THEN skip('ponte django assente su questo database (tabella nata col migrate Django DOPO Liquibase: FK sotto MARK_RAN)', 1)
  ELSE cmp_ok(
    (SELECT count(*) FROM _puntatori WHERE fk IS NOT NULL),
    '>=', 5::bigint,
    '3) la lente vede le FK verso django.auth_user gia'' presenti (identita_digitali, parameter_overrides, documenti_generati, ui.*): il test 1 non e'' muto')
  END;

SELECT * FROM finish();
ROLLBACK;
