-- ------------------------------------------------------------
-- SPDX-License-Identifier: AGPL-3.0-or-later
-- pgTAP test per Zero ERP
--
-- Test: ogni stato attivo di un documento si raggiunge dal suo stato iniziale.
--   Brief: brief-db-stati-documento-dal-vocabolario, giro 4 (⑤, S-8, R-3).
--   ChangeSet: 20261114-03 (il ritiro dei quattro stati d'ordine), i CSV di
--   stati_doc_ordini (S-8) e stati_doc_fiscale (R-3, D-ANN).
--
-- Semantica attesa (il contratto, non l'implementazione):
--   - per ogni testata della mappa script.fn_doc_stato_modello, ogni stato
--     attivo del vocabolario si raggiunge dallo stato iniziale lungo righe
--     attive della matrice (a mano o di processo), col filtro della mappa;
--   - nel vocabolario fiscale, condiviso da fattura e lotto, contano per
--     ciascuno gli stati che valgono per lui (applica_fattura, applica_lotto);
--   - uno stato che nessun passaggio raggiunge e' una seconda verita' (S-8): un
--     significato dichiarato che il modello non produce.
--
-- ⚠️ PRESIDIO SULLA FORMA della configurazione (il seed di catalogo), dichiarato
--   tale: legge vocabolari e matrici, non documenti. Perche' non sia verde per
--   sottrazione, i test 2 e 3 COSTRUISCONO il controesempio e verificano che il
--   presidio lo trovi.
-- ⭐ ANNULLATA della fattura (⑩ del brief, D-ANN di Tid, 2026-11-14): la fattura
--   non si annulla (in bozza si cancella, numerata si storna con una nota di
--   credito), e il vocabolario lo dice con applica_fattura = false.
--
-- Elenco test (plan 5):
--   1) le dieci testate: nessuno stato attivo irraggiungibile
--   2) controesempio: uno stato attivo nuovo del reso, senza righe in entrata,
--      e' trovato
--   3) controesempio: spenta l'unica riga che entra nel reso CONFERMATO, lo
--      stato e' trovato
--   4) S-8: ALLOCATO, SPEDITO, CONSEGNATO e FATTURATO non sono piu' stati d'ordine
--   5) R-3 e D-ANN: REGISTRATA non vale per il lotto, ANNULLATA per la fattura
-- ------------------------------------------------------------

BEGIN;

SET CONSTRAINTS ALL IMMEDIATE;

SELECT plan(5);

-- Gli stati attivi della testata che nessun cammino di righe attive porta
-- dallo stato iniziale. Per fattura e lotto, solo gli stati che valgono per
-- quel documento.
CREATE FUNCTION pg_temp.non_raggiunti(p_testata regclass) RETURNS SETOF text
LANGUAGE plpgsql STABLE AS $f$
DECLARE
    m     record;
    v_app text := CASE p_testata
                    WHEN 'vendite.fatture'::regclass            THEN 'AND s.applica_fattura'
                    WHEN 'vendite.fatturazione_lotti'::regclass THEN 'AND s.applica_lotto'
                    ELSE '' END;
BEGIN
    SELECT * INTO m FROM script.fn_doc_stato_modello(p_testata);
    RETURN QUERY EXECUTE format($q$
        WITH RECURSIVE raggiunti(id) AS (
            SELECT s.id FROM %1$s s WHERE s.iniziale
            UNION
            SELECT t.%3$I FROM %2$s t JOIN raggiunti g ON g.id = t.%4$I
             WHERE t.%5$I IS TRUE %6$s)
        SELECT %8$L || ':' || s.codice_interno
          FROM %1$s s
         WHERE s.attivo %7$s
           AND s.id NOT IN (SELECT r.id FROM raggiunti r)
         ORDER BY 1$q$,
        m.vocabolario, m.matrice, m.colonna_a, m.colonna_da, m.colonna_vivo, m.filtro, v_app, p_testata::text);
END
$f$;

CREATE FUNCTION pg_temp.tutte() RETURNS text[]
LANGUAGE sql STABLE AS $f$
    SELECT ARRAY(
        SELECT x
          FROM unnest(ARRAY['vendite.preventivi', 'vendite.offerte_commerciali', 'vendite.contratti',
                            'vendite.ordini', 'vendite.ddt', 'vendite.resi', 'vendite.commesse',
                            'vendite.fatture', 'vendite.fatturazione_lotti',
                            'vendite.listini_versioni']::regclass[]) AS t,
               pg_temp.non_raggiunti(t) AS x
         ORDER BY 1)
$f$;

-- ============================================================
-- 1) La configurazione di oggi
-- ============================================================
SELECT is(
    pg_temp.tutte(),
    ARRAY[]::text[],
    '1. ogni stato attivo di ogni documento si raggiunge dal suo stato iniziale'
);

-- ============================================================
-- 2-3) I controesempi, costruiti
-- ============================================================
INSERT INTO config.stati_doc_reso (codice_interno, codice, descrizione, attivo, ordine, fase)
VALUES ('PGTAP_ISOLATO', 'PGTAP_ISOLATO', 'pgTAP: uno stato senza entrate', true, 99, 'IN_CORSO');

SELECT ok(
    'vendite.resi:PGTAP_ISOLATO' = ANY (pg_temp.tutte()),
    '2. uno stato attivo nuovo del reso, senza righe in entrata, e'' trovato'
);

UPDATE config.transizioni_stati_reso t
   SET attivo = false
  FROM config.stati_doc_reso a
 WHERE a.id = t.stato_a_id
   AND a.codice_interno = 'CONFERMATO';

SELECT ok(
    'vendite.resi:CONFERMATO' = ANY (pg_temp.tutte()),
    '3. spenta l''unica riga che entra nel reso CONFERMATO, lo stato e'' trovato: una riga spenta non e'' un passaggio'
);

-- ============================================================
-- 4-5) S-8 e R-3
-- ============================================================
SELECT is(
    (SELECT count(*)::int FROM config.stati_doc_ordini s
      WHERE s.codice_interno IN ('ALLOCATO', 'SPEDITO', 'CONSEGNATO', 'FATTURATO')),
    0,
    '4. S-8: ALLOCATO, SPEDITO, CONSEGNATO e FATTURATO non sono piu'' stati d''ordine'
);

SELECT is(
    (SELECT string_agg(s.codice_interno || ':' || s.applica_lotto || ':' || s.applica_fattura, ' ' ORDER BY s.codice_interno)
       FROM config.stati_doc_fiscale s WHERE s.codice_interno IN ('ANNULLATA', 'REGISTRATA')),
    'ANNULLATA:true:false REGISTRATA:false:true',
    '5. R-3 e D-ANN: REGISTRATA vale solo per la fattura (un fatto della singola fattura), ANNULLATA solo per il lotto'
);

SELECT * FROM finish();
ROLLBACK;
