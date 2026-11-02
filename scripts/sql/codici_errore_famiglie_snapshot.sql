-- ------------------------------------------------------------
-- SPDX-License-Identifier: AGPL-3.0-or-later
-- Zero ERP — lo SCATTO delle famiglie di condizione per codice errore
--   E' la sorgente unica del presidio B-7. Non stampa niente di piu' di
--   quello che va nel file di baseline: chi confronta legge questo output.
--
-- FORMATO (TSV):  codice <TAB> famiglie_note_ordinate <TAB> n_punti
--
-- ⚠️ SOLO LE FAMIGLIE **NOTE**. `IGNOTO` non e' una famiglia: e' la misura che
--   dichiara di non saper leggere quella guardia. Se entrasse nella baseline,
--   un codice che passa da «non so» a «so» sembrerebbe un peggioramento, e il
--   presidio comincerebbe a mentire dal primo giorno.
--
-- ⚠️ I codici RITIRATI restano fuori: non possono acquistare condizioni nuove.
-- ------------------------------------------------------------
SELECT f.codice,
       array_to_string(ARRAY(SELECT unnest(f.famiglie)
                              EXCEPT SELECT 'IGNOTO'
                              ORDER BY 1), ',') AS famiglie,
       f.n_punti
  FROM dbops.vw_codici_errore_forme_condizione f
  JOIN config.codici_errore c USING (codice)
 WHERE NOT f.solo_ignoto
   AND (c.obsoleto_dal IS NULL OR c.obsoleto_dal > CURRENT_DATE)
 ORDER BY f.codice;
