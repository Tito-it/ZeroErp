-- ------------------------------------------------------------
-- SPDX-License-Identifier: GPL-3.0-or-later
-- pgTAP test ANTI-REGRESSIONE — security_invoker sulle viste del lotto RLS
--
-- Brief RLS §8 / §11 (trasforma C2 in cancello CI). Le viste DEFINER su
-- tabelle in RLS scavalcano la RLS (RLS cosmetica). Questo test fallisce se
-- una vista del lotto torna DEFINER (security_invoker assente o = off),
-- intercettando la regressione prima dell'ENABLE.
--
-- Riferimento: changeSet 20260601-26 (conversione a security_invoker=on).
--
-- Indice test (1..9): una asserzione per vista.
-- ------------------------------------------------------------

BEGIN;
-- ⚠️ Vincoli DIFFERITI: senza questa riga il test smetterebbe di verificarli.
--   Un trigger DEFERRABLE INITIALLY DEFERRED scatta al COMMIT, e qui il COMMIT
--   non arriva mai (si chiude in ROLLBACK): sarebbero saltati in silenzio, e il
--   file sarebbe verde per sottrazione. IMMEDIATE li riporta a scattare a fine
--   di ogni istruzione. In testa e non in coda: in coda scatterebbero dopo il
--   cleanup, su righe ormai cancellate.
--   Brief: brief-db-pgtap-runner-rls-baseline §19.
SET CONSTRAINTS ALL IMMEDIATE;

SELECT plan(9);

-- Helper: true se la vista ha security_invoker=on nelle reloptions.
CREATE FUNCTION pg_temp.is_invoker(p_sch text, p_nm text)
RETURNS boolean LANGUAGE sql STABLE AS $$
    -- option_value e' memorizzato come 'on' (non 'true'): cast a boolean
    -- per robustezza ('on'/'true'/'1' -> true).
    SELECT COALESCE((
        SELECT ot.option_value::boolean
          FROM pg_class c
          JOIN pg_namespace n ON n.oid = c.relnamespace
          LEFT JOIN LATERAL pg_options_to_table(c.reloptions) ot
            ON ot.option_name = 'security_invoker'
         WHERE n.nspname = p_sch
           AND c.relname = p_nm
    ), false);
$$;

SELECT ok(pg_temp.is_invoker('vendite','vw_preventivi'),
    '1. vendite.vw_preventivi -> security_invoker=on');
SELECT ok(pg_temp.is_invoker('vendite','vw_preventivi_lista'),
    '2. vendite.vw_preventivi_lista -> security_invoker=on');
SELECT ok(pg_temp.is_invoker('vendite','vw_preventivi_pratiche'),
    '3. vendite.vw_preventivi_pratiche -> security_invoker=on');
-- Rename 20260612-05 (brief smistamento): vw_preventivi_stato_fatturazione*
-- -> vw_preventivi_smistamento* (stesse tabelle RLS sottostanti).
SELECT ok(pg_temp.is_invoker('vendite','vw_preventivi_smistamento'),
    '4. vendite.vw_preventivi_smistamento -> security_invoker=on');
SELECT ok(pg_temp.is_invoker('vendite','vw_preventivi_smistamento_righe'),
    '5. vendite.vw_preventivi_smistamento_righe -> security_invoker=on');
SELECT ok(pg_temp.is_invoker('vendite','vw_offerte_commerciali_lista'),
    '6. vendite.vw_offerte_commerciali_lista -> security_invoker=on');
SELECT ok(pg_temp.is_invoker('anagrafiche','vw_clienti_lista'),
    '7. anagrafiche.vw_clienti_lista -> security_invoker=on');
SELECT ok(pg_temp.is_invoker('anagrafiche','vw_clienti_codice_ba'),
    '8. anagrafiche.vw_clienti_codice_ba -> security_invoker=on');
SELECT ok(pg_temp.is_invoker('dbops','vw_diag_v_clienti_links'),
    '9. dbops.vw_diag_v_clienti_links -> security_invoker=on');

SELECT * FROM finish();
ROLLBACK;
