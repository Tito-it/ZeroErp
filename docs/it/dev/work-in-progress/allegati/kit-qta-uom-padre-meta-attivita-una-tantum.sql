-- ------------------------------------------------------------
-- SPDX-License-Identifier: GPL-3.0-or-later
-- Zero ERP — correzione dati UNA TANTUM su dbdev (non e' un changeSet)
--
-- Brief: brief-db-bom-flag-quantita-e-kit-in-fattura, §5 R-BE-B5
-- Stampo: esposizione-kit-meta-attivita-una-tantum.sql (stessa forma)
--
-- COSA FA
--   Nel meta delle attivita' di commessa e delle attivita' fatturabili che
--   sono COMPONENTI DI KIT (`componente_di` nel meta) aggiunge le due chiavi
--   del contratto kit che il push scrive dal 2026-10-02 (R-BE-B2):
--       qta_padre     = quantita / coeff_qta, se coeff_qta (del meta) > 0;
--                       altrimenti 1
--       uom_padre_id  = articoli.uom_id dell'articolo padre (`componente_di`)
--   La quantita' padre porta il SEGNO della quantita' (una rettifica e'
--   negativa, D-NC-2): e' la regola che la generazione delle righe verifica.
--   Le chiavi gia' presenti NON si toccano: vince il push.
--
-- QUANDO
--   Al merge del BE che le legge (R-BE-B2). Senza, la generazione di una
--   fattura che contiene un componente di kit gia' in commessa si ferma con
--   E_GROUP_ATTIVITA_INVALID_DATA («componente di kit senza la UoM/quantita'
--   del padre nel meta»): e' voluto, nel codice non c'e' un ripiego.
--
-- ⚠️ LA UOM DEL PADRE E' QUELLA DELL'ARTICOLO, non quella della riga del
--   documento sorgente: il meta non porta la riga padre, e risalirci dal
--   segmento vorrebbe dire una lettura per sorgente. Su dbdev, dati di test,
--   e' la scelta del brief (R-BE-B5). Il push, da qui in avanti, scrive la UoM
--   della riga.
--
-- PERCHE' RIGA PER RIGA
--   Come lo stampo: i trigger «riferimento attivo» rigiudicano la riga a ogni
--   UPDATE, quindi un'attivita' che punta a qualcosa di spento rifiuterebbe
--   l'UPDATE del solo meta. Ogni riga ha il suo savepoint, e quelle che
--   rifiutano sono ELENCATE alla fine, non saltate in silenzio.
--
-- LE ATTIVITA' GIA' FATTURATE SI CORREGGONO ANCHE LORO
--   L'accredito di un reso eredita il meta della riga rettificata: lasciarle
--   senza le chiavi vorrebbe dire note di credito che non si generano. Si usa
--   il bypass di manutenzione del guard (zeroerp.maintenance_reset_lotto_draft),
--   SET LOCAL, solo per questa transazione.
--
-- NON TOCCA vendite.fatture_righe: le righe di kit gia' scritte hanno
--   `kit_qta` dal changeSet 20261002-63 (D-4).
--
-- COME SI LANCIA (da un ruolo che non e' filtrato dalla RLS: superuser o
-- BYPASSRLS — lo script si ferma se non lo e')
--   prova, annulla alla fine:   psql ... -f kit-qta-uom-padre-meta-attivita-una-tantum.sql
--   applica, COMMIT:            psql ... -v applica=1 -f kit-qta-uom-padre-meta-attivita-una-tantum.sql
-- ------------------------------------------------------------

\set ON_ERROR_STOP 1
\if :{?applica}
\else
  \set applica 0
\endif

BEGIN;
SET LOCAL lock_timeout = '5s';
SET LOCAL statement_timeout = '300s';
SET LOCAL zeroerp.maintenance_reset_lotto_draft = 'on';

-- Sotto RLS un ruolo filtrato vedrebbe ZERO righe e lo script direbbe «niente
-- da fare»: uno zero che sembra un esito. Si pretende un ruolo che vede tutto.
DO $chk$
BEGIN
  IF NOT EXISTS (SELECT 1 FROM pg_roles
                  WHERE rolname = current_user AND (rolsuper OR rolbypassrls)) THEN
    RAISE EXCEPTION 'lanciare da un ruolo superuser o BYPASSRLS (ora: %)', current_user;
  END IF;
END $chk$;

\echo '== PRIMA: componenti di kit senza le chiavi del padre'
SELECT 'vendite.commesse_attivita' AS tabella, count(*) AS righe
  FROM vendite.commesse_attivita
 WHERE meta ? 'componente_di' AND NOT (meta ? 'qta_padre' AND meta ? 'uom_padre_id')
UNION ALL
SELECT 'vendite.attivita_fatturabili', count(*)
  FROM vendite.attivita_fatturabili
 WHERE meta ? 'componente_di' AND NOT (meta ? 'qta_padre' AND meta ? 'uom_padre_id');

CREATE TEMP TABLE tmp_meta_rifiutate (tabella text, id bigint, errore text) ON COMMIT DROP;

DO $fix$
DECLARE
  r  record;
  t  text;
BEGIN
  FOREACH t IN ARRAY ARRAY['commesse_attivita', 'attivita_fatturabili'] LOOP
    FOR r IN EXECUTE format(
        'SELECT id FROM vendite.%I
          WHERE meta ? %L AND NOT (meta ? %L AND meta ? %L)
          ORDER BY id', t, 'componente_di', 'qta_padre', 'uom_padre_id')
    LOOP
      BEGIN
        -- Il calcolato sta a SINISTRA del `||`: una chiave gia' presente
        -- (scritta dal push) vince.
        EXECUTE format(
          'UPDATE vendite.%I x
              SET meta = jsonb_strip_nulls(jsonb_build_object(
                           ''qta_padre'',
                           (CASE WHEN (x.meta ->> ''coeff_qta'') ~ ''^[0-9]+(\.[0-9]+)?$''
                                  AND (x.meta ->> ''coeff_qta'')::numeric > 0
                                 THEN trim_scale(x.quantita / (x.meta ->> ''coeff_qta'')::numeric)
                                 ELSE 1::numeric
                            END)::text,
                           ''uom_padre_id'',
                           (SELECT a.uom_id
                              FROM catalogo.articoli a
                             WHERE a.id::text = btrim(x.meta ->> ''componente_di''))))
                         || x.meta
            WHERE x.id = $1', t)
          USING r.id;
      EXCEPTION WHEN OTHERS THEN
        INSERT INTO tmp_meta_rifiutate VALUES (t, r.id, SQLERRM);
      END;
    END LOOP;
  END LOOP;
END $fix$;

\echo '== DOPO: componenti di kit ancora senza le chiavi (attese: solo le rifiutate, o padre inesistente)'
SELECT 'vendite.commesse_attivita' AS tabella, id, meta ->> 'componente_di' AS padre
  FROM vendite.commesse_attivita
 WHERE meta ? 'componente_di' AND NOT (meta ? 'qta_padre' AND meta ? 'uom_padre_id')
UNION ALL
SELECT 'vendite.attivita_fatturabili', id, meta ->> 'componente_di'
  FROM vendite.attivita_fatturabili
 WHERE meta ? 'componente_di' AND NOT (meta ? 'qta_padre' AND meta ? 'uom_padre_id')
 ORDER BY 1, 2;

\echo '== DOPO: segno della quantita padre contro quella del componente (attese: zero righe)'
SELECT 'commesse_attivita' AS tabella, id, quantita, meta ->> 'qta_padre' AS qta_padre
  FROM vendite.commesse_attivita
 WHERE meta ? 'qta_padre' AND quantita <> 0
   AND (meta ->> 'qta_padre')::numeric <> 0
   AND sign(quantita) <> sign((meta ->> 'qta_padre')::numeric)
UNION ALL
SELECT 'attivita_fatturabili', id, quantita, meta ->> 'qta_padre'
  FROM vendite.attivita_fatturabili
 WHERE meta ? 'qta_padre' AND quantita <> 0
   AND (meta ->> 'qta_padre')::numeric <> 0
   AND sign(quantita) <> sign((meta ->> 'qta_padre')::numeric)
 ORDER BY 1, 2;

\echo '== RIFIUTATE (riga per riga, con il motivo): da guardare prima di applicare'
SELECT * FROM tmp_meta_rifiutate ORDER BY tabella, id;

\if :applica
  \echo '== COMMIT'
  COMMIT;
\else
  \echo '== ROLLBACK (prova). Per applicare: -v applica=1'
  ROLLBACK;
\endif
