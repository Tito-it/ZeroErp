-- ------------------------------------------------------------
-- SPDX-License-Identifier: GPL-3.0-or-later
-- Zero ERP — correzione dati UNA TANTUM su dbdev (non e' un changeSet)
--
-- Brief: brief-db-esposizione-componenti-kit-in-fattura, §9.3
--
-- COSA FA
--   Nel meta delle attivita' di commessa e delle attivita' fatturabili la
--   chiave del contratto kit `esposto_in_fattura` (booleano) diventa
--   `esposizione` (codice di config.esposizioni_componente):
--       true            -> DESCRITTIVO   (cio' che il true produceva in fattura)
--       false / assente -> NASCOSTO      (il default del BE era false)
--   Se una riga ha GIA' `esposizione`, vince quella: la chiave vecchia si toglie
--   e basta.
--
-- QUANDO
--   Insieme al merge del BE che legge la chiave nuova (R-BE-2). Prima no: il
--   BE di oggi legge `esposto_in_fattura` e su una riga corretta leggerebbe
--   «assente» = false.
--
-- PERCHE' RIGA PER RIGA
--   I trigger «riferimento attivo» (dbops.trgfn_child_requires_active_parent)
--   rigiudicano la riga a OGNI UPDATE, anche se la FK non cambia: un'attivita'
--   vecchia che punta a un articolo, una riga di listino o un'unita' di misura
--   spenti nel frattempo rifiuterebbe l'UPDATE del solo meta. Un UPDATE unico
--   morirebbe sulla prima; qui ogni riga ha il suo savepoint, e quelle che
--   rifiutano sono ELENCATE alla fine, non saltate in silenzio.
--
-- LE ATTIVITA' GIA' FATTURATE SI CORREGGONO ANCHE LORO
--   L'accredito di un reso (vendite.fn_accredita_riga_reso) eredita il meta
--   della riga rettificata: lasciarle con la chiave vecchia vorrebbe dire note
--   di credito che nascono con la forma vecchia. Il guard
--   trgfn_attivita_fatturabili_guard_fatturato le blocca; si usa il suo bypass
--   di manutenzione (zeroerp.maintenance_reset_lotto_draft), SET LOCAL, solo
--   per questa transazione.
--
-- NON TOCCA vendite.fatture_righe.meta: la fattura legge l'esposizione dalla
--   colonna kit_esposizione (gia' convertita da 20261001-45), e le righe emesse
--   sono intoccabili. Lo script ne conta le righe con la chiave vecchia, solo
--   per informazione.
--
-- COME SI LANCIA (da un ruolo che non e' filtrato dalla RLS: superuser o
-- BYPASSRLS — lo script si ferma se non lo e')
--   prova, annulla alla fine:   psql ... -f esposizione-kit-meta-attivita-una-tantum.sql
--   applica, COMMIT:            psql ... -v applica=1 -f esposizione-kit-meta-attivita-una-tantum.sql
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

\echo '== PRIMA: righe con la chiave vecchia'
SELECT 'vendite.commesse_attivita' AS tabella, count(*) AS righe
  FROM vendite.commesse_attivita WHERE meta ? 'esposto_in_fattura'
UNION ALL
SELECT 'vendite.attivita_fatturabili', count(*)
  FROM vendite.attivita_fatturabili WHERE meta ? 'esposto_in_fattura'
UNION ALL
SELECT 'vendite.fatture_righe (solo informazione, non si tocca)', count(*)
  FROM vendite.fatture_righe WHERE meta ? 'esposto_in_fattura';

CREATE TEMP TABLE tmp_meta_rifiutate (tabella text, id bigint, errore text) ON COMMIT DROP;

DO $fix$
DECLARE
  r  record;
  t  text;
BEGIN
  FOREACH t IN ARRAY ARRAY['commesse_attivita', 'attivita_fatturabili'] LOOP
    FOR r IN EXECUTE format(
        'SELECT id FROM vendite.%I WHERE meta ? %L ORDER BY id', t, 'esposto_in_fattura')
    LOOP
      BEGIN
        EXECUTE format(
          'UPDATE vendite.%I
              SET meta = jsonb_build_object(
                           ''esposizione'',
                           CASE WHEN (meta ->> ''esposto_in_fattura'')::boolean
                                THEN ''DESCRITTIVO'' ELSE ''NASCOSTO'' END)
                         || (meta - ''esposto_in_fattura'')
            WHERE id = $1', t)
          USING r.id;
      EXCEPTION WHEN OTHERS THEN
        INSERT INTO tmp_meta_rifiutate VALUES (t, r.id, SQLERRM);
      END;
    END LOOP;
  END LOOP;
END $fix$;

\echo '== DOPO: righe con la chiave vecchia (attese: solo le rifiutate)'
SELECT 'vendite.commesse_attivita' AS tabella, count(*) AS righe
  FROM vendite.commesse_attivita WHERE meta ? 'esposto_in_fattura'
UNION ALL
SELECT 'vendite.attivita_fatturabili', count(*)
  FROM vendite.attivita_fatturabili WHERE meta ? 'esposto_in_fattura';

\echo '== DOPO: valori di esposizione nel meta (devono essere solo codici a catalogo)'
SELECT x.tabella, x.esposizione, count(*) AS righe,
       (x.esposizione IN (SELECT codice_interno FROM config.esposizioni_componente)) AS a_catalogo
  FROM (SELECT 'commesse_attivita' AS tabella, meta ->> 'esposizione' AS esposizione
          FROM vendite.commesse_attivita WHERE meta ? 'esposizione'
        UNION ALL
        SELECT 'attivita_fatturabili', meta ->> 'esposizione'
          FROM vendite.attivita_fatturabili WHERE meta ? 'esposizione') x
 GROUP BY 1, 2 ORDER BY 1, 2;

\echo '== RIFIUTATE (riga per riga, con il motivo): da guardare prima di applicare'
SELECT * FROM tmp_meta_rifiutate ORDER BY tabella, id;

\if :applica
  \echo '== COMMIT'
  COMMIT;
\else
  \echo '== ROLLBACK (prova). Per applicare: -v applica=1'
  ROLLBACK;
\endif
