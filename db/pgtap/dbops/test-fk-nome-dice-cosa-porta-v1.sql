-- ------------------------------------------------------------
-- SPDX-License-Identifier: AGPL-3.0-or-later
-- pgTAP test per Zero ERP
-- Copyright (C) 2026 Tid (Michele Carlo Titini)
--
-- Rilasciato sotto GNU AGPLv3 o versione successiva.
-- Vedi LICENSE.md per il testo completo della licenza.
-- ------------------------------------------------------------
-- Test: la colonna FK dice che cosa porta. Una FK monocolonna finisce in _id
--   se e solo se la colonna del padre a cui punta porta un id (id, o una
--   colonna che finisce in _id). Vale nei due versi.
--   Regola: linee-guida-sql §2, «La colonna FK dice che cosa porta» (Tid,
--   2026-11-21, D-2 «b» e D-6 del brief brief-db-attivo-fk-senza-suffisso-id).
--
-- ⭐ I nomi storici restano (D-2 «b»): stanno nell'elenco congelato qui sotto,
--   ciascuno col suo motivo. Una FK nuova fuori regola non ci entra: si
--   rinomina la colonna.
-- ⛔ Il predicato e' LIKE '%\_id', col '_' protetto: con il jolly una colonna
--   come «xid» passerebbe per una colonna con _id.
-- ⚠️ Si guardano le FK proprie (conparentid = 0): una FK ereditata da una
--   radice partizionata ha il nome della radice, e senza il filtro l'elenco
--   dovrebbe portare anche le 40 FK delle partizioni delle note.
-- ⚠️ Una FK multicolonna non ha un nome di colonna da giudicare: resta fuori.
-- ⚠️ config.credenziali.bloccata_da punta a django.auth_user, che nasce solo
--   su un database con lo schema django (residuo aperto «Le FK verso
--   django.auth_user non nascono su un'installazione nuova»): in CI manca, e
--   l'elenco lo dichiara.
--
-- Elenco test (plan 2):
--   1) ⭐ nessuna FK fuori regola, nei due versi, fuori dall'elenco congelato
--   2) ogni voce dell'elenco esiste ed e' ancora fuori regola (una FK
--      rinominata esce dall'elenco nello stesso giro)
-- ------------------------------------------------------------
BEGIN;
DO $ctx$ BEGIN PERFORM script.fn_pgtap_set_contesto_operatore(); END $ctx$;
SET CONSTRAINTS ALL IMMEDIATE;

SELECT plan(2);

CREATE TEMP TABLE _elenco (cs text, ct text, col text, puo_mancare boolean, motivo text);
INSERT INTO _elenco VALUES
  ('acquisti',    'note',                 'id_lingua',                     false, 'nome storico, D-2 b'),
  ('acquisti',    'note',                 'id_stile',                      false, 'nome storico, D-2 b'),
  ('catalogo',    'note',                 'id_lingua',                     false, 'nome storico, D-2 b'),
  ('catalogo',    'note',                 'id_stile',                      false, 'nome storico, D-2 b'),
  ('magazzino',   'note',                 'id_lingua',                     false, 'nome storico, D-2 b'),
  ('magazzino',   'note',                 'id_stile',                      false, 'nome storico, D-2 b'),
  ('vendite',     'note',                 'id_lingua',                     false, 'nome storico, D-2 b'),
  ('vendite',     'note',                 'id_stile',                      false, 'nome storico, D-2 b'),
  ('anagrafiche', 'dati_societari',       'id_prov_iscri_rea',             false, 'nome storico, D-2 b'),
  ('config',      'iva',                  'id_iva_split',                  false, 'nome storico, D-2 b'),
  ('config',      'iva_stati',            'assoggettamento_id_override',   false, 'nome storico, D-2 b'),
  ('magazzino',   'eventi_assets',        'magazzino_id_from',             false, 'nome storico, D-2 b'),
  ('magazzino',   'eventi_assets',        'magazzino_id_to',               false, 'nome storico, D-2 b'),
  ('magazzino',   'trasferimenti',        'magazzino_id_from',             false, 'nome storico, D-2 b'),
  ('magazzino',   'trasferimenti',        'magazzino_id_to',               false, 'nome storico, D-2 b'),
  ('magazzino',   'trasferimenti_righe',  'ubicazione_id_da',              false, 'nome storico, D-2 b'),
  ('magazzino',   'trasferimenti_righe',  'ubicazione_id_a',               false, 'nome storico, D-2 b'),
  ('vendite',     'attivita_fatturabili', 'categoria_cliente_id_snapshot', false, 'nome storico, D-2 b'),
  ('vendite',     'attivita_fatturabili', 'classe_utenza_id_snapshot',     false, 'nome storico, D-2 b'),
  ('vendite',     'commesse_attivita',    'categoria_cliente_id_snapshot', false, 'nome storico, D-2 b'),
  ('vendite',     'commesse_attivita',    'classe_utenza_id_snapshot',     false, 'nome storico, D-2 b'),
  ('vendite',     'contratti',            'categoria_cliente_id_snapshot', false, 'nome storico, D-2 b'),
  ('config',      'credenziali',          'bloccata_da',                   true,  'nome storico, D-2 b; la FK nasce solo dove esiste django.auth_user');

-- Le FK monocolonna proprie degli schemi del progetto, con il verdetto.
CREATE TEMP TABLE _fk AS
SELECT n.nspname::text AS cs, r.relname::text AS ct, a.attname::text AS col,
       (lower(pa.attname) = 'id' OR lower(pa.attname) LIKE '%\_id') AS porta_un_id,
       lower(a.attname) LIKE '%\_id'                                AS nome_con_id
  FROM pg_constraint c
  JOIN pg_class r      ON r.oid = c.conrelid
  JOIN pg_namespace n  ON n.oid = r.relnamespace
  JOIN pg_attribute a  ON a.attrelid = c.conrelid  AND a.attnum  = c.conkey[1]
  JOIN pg_attribute pa ON pa.attrelid = c.confrelid AND pa.attnum = c.confkey[1]
 WHERE c.contype = 'f'
   AND cardinality(c.conkey) = 1
   AND c.conparentid = 0
   AND n.nspname NOT IN ('pg_catalog', 'information_schema', 'django', 'public', 'pgagent', 'topology')
   AND n.nspname NOT LIKE 'pg\_%'
   AND n.nspname NOT LIKE 'pgtap%';

SELECT is(
    (SELECT COALESCE(array_agg(f.cs || '.' || f.ct || '.' || f.col ORDER BY 1), '{}'::text[])
       FROM _fk f
      WHERE f.porta_un_id <> f.nome_con_id
        AND NOT EXISTS (SELECT 1 FROM _elenco e WHERE (e.cs, e.ct, e.col) = (f.cs, f.ct, f.col))),
    '{}'::text[],
    '1) nessuna FK fuori regola, nei due versi, fuori dall''elenco congelato');

SELECT is(
    (SELECT COALESCE(array_agg(e.cs || '.' || e.ct || '.' || e.col ORDER BY 1), '{}'::text[])
       FROM _elenco e
       LEFT JOIN _fk f ON (f.cs, f.ct, f.col) = (e.cs, e.ct, e.col)
      WHERE (f.cs IS NULL AND NOT e.puo_mancare)
         OR f.porta_un_id = f.nome_con_id),
    '{}'::text[],
    '2) ogni voce dell''elenco esiste ed e'' ancora fuori regola');

SELECT * FROM finish();
ROLLBACK;
