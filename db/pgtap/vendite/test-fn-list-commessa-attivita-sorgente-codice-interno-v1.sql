-- ------------------------------------------------------------
-- SPDX-License-Identifier: AGPL-3.0-or-later
-- pgTAP test per Zero ERP
--
-- Test: la lista delle attivita' di commessa apre l'origine dal NOME DEL TIPO
--   (config.sorgenti.codice_interno, G-1) e mostra l'etichetta della sorgente.
--   vendite.fn_list_commessa_attivita              (20261021-20)
--   seed ui.lista_colonna, lista vendite.commesse_attivita, colonna origine_tipo
--   Brief: brief-db-grammatica-unica-documenti (richiesta BE/FE del 2026-10-20).
--
-- Elenco test (plan 7):
--  1) una firma sola (nessun overload dopo il DROP + CREATE)
--  2) la RETURNS TABLE espone sorgente_codice_interno e sorgente_etichetta,
--     e non piu' sorgente_codice
--  3) ⭐⭐ sorgente_codice_interno e' il codice_interno anche quando l'operatore
--     ha cambiato il codice della sorgente
--  4) sorgente_etichetta e' l'etichetta della sorgente
--  5) si ordina per sorgente_etichetta, nei due versi
--  6) ⛔ sorgente_codice e' fuori whitelist: fail-loud (P0001)
--  7) ⭐ INVARIANTE: ogni colonna ordinabile della lista a catalogo e' nella
--     whitelist della funzione
--
-- Scopo:
--  - ⭐ Il 3 e' il motivo del giro. config.sorgenti.codice e' il nome che
--    l'operatore puo' cambiare; il frontend apre il documento d'origine dal
--    valore che riceve, quindi deve essere quello protetto dal lock. Il caso si
--    COSTRUISCE: una sorgente di prova rinominata. Sulle sorgenti seminate oggi
--    i due codici coincidono, e un test sui dati veri passerebbe anche col
--    difetto.
--  - ⭐ Il 7 rende rumorosa la coppia whitelist / seed (la colonna `origine_tipo`
--    cambia campo_sorgente nello stesso giro): un nome ordinabile che la
--    funzione non conosce rompe la lista al primo click, non da' una freccia
--    inerte. Legge il seed di 80_data, che in CI c'e' identico: e' leggere il
--    progetto, non misurare una popolazione.
-- ------------------------------------------------------------

BEGIN;

-- pgtap-contesto: escluso — il contesto lo apre il builder della commessa,
--   chiamato come lo chiamera' un file su un database ricostruito.

SET CONSTRAINTS ALL IMMEDIATE;

SELECT plan(7);

-- ============================================================
-- Fixture
-- ============================================================
CREATE OR REPLACE FUNCTION pg_temp.ordina(p_commessa_id bigint, p_order_by text, p_dir text)
RETURNS bigint
LANGUAGE plpgsql AS $$
DECLARE v_n bigint;
BEGIN
    SELECT count(*) INTO v_n
      FROM vendite.fn_list_commessa_attivita(
               p_commessa_id => p_commessa_id, p_order_by => p_order_by, p_order_dir => p_dir);
    RETURN v_n;
END $$;

-- La commessa (apre il contesto dell'operatore) e un'attivita' approvata.
CREATE TEMP TABLE t_c AS
SELECT * FROM dbops.fn_pgtap_crea_commessa('sorgente codice interno');

CREATE TEMP TABLE t_a AS
SELECT * FROM dbops.fn_pgtap_crea_commessa_attivita((SELECT commessa_id FROM t_c));

-- Una sorgente di prova, poi RINOMINATA: codice ed etichetta sono dell'operatore,
-- codice_interno no (lock trg_sorgenti_a10_lock_columns_upd).
CREATE TEMP TABLE t_s AS
SELECT dbops.fn_pgtap_crea_sorgente('PGTAP_SCI_ORIGINE') AS sorgente_id;

UPDATE config.sorgenti
   SET codice    = 'PGTAP_SCI_NOME_OPERATORE',
       etichetta = 'Origine di prova'
 WHERE id = (SELECT sorgente_id FROM t_s);

-- L'attivita' viene da quella sorgente (la coppia tipo + uid e' completa:
-- chk_commesse_attivita_sorgente_pair). L'uid non risolve un documento: il
-- resolver torna una riga a NULL, e non e' l'oggetto del test.
UPDATE vendite.commesse_attivita
   SET sorgente_tipo_id = (SELECT sorgente_id FROM t_s),
       sorgente_uid     = '999999999'
 WHERE id = (SELECT attivita_id FROM t_a);

-- ⛔ Il verbo in un'istruzione SUA: la lettura nella stessa istruzione delle
--   scritture non le vedrebbe.
CREATE TEMP TABLE t_riga AS
SELECT *
  FROM vendite.fn_list_commessa_attivita(p_commessa_id => (SELECT commessa_id FROM t_c))
 WHERE id = (SELECT attivita_id FROM t_a);

-- ============================================================
-- 1/2) La forma
-- ============================================================
SELECT is(
    (SELECT count(*)::int
       FROM pg_proc p
       JOIN pg_namespace n ON n.oid = p.pronamespace
      WHERE n.nspname = 'vendite' AND p.proname = 'fn_list_commessa_attivita'),
    1,
    '1) fn_list_commessa_attivita: una firma sola');

-- ⚠️ Una stringa sola: le due colonne nuove E la vecchia assente. Con tre
--   asserzioni separate, una funzione che le esponesse tutte e tre passerebbe
--   le prime due.
SELECT is(
    (SELECT string_agg(a, ',' ORDER BY a)
       FROM pg_proc p
       JOIN pg_namespace n ON n.oid = p.pronamespace,
            unnest(p.proargnames) a
      WHERE n.nspname = 'vendite' AND p.proname = 'fn_list_commessa_attivita'
        AND a IN ('sorgente_codice', 'sorgente_codice_interno', 'sorgente_etichetta')),
    'sorgente_codice_interno,sorgente_etichetta',
    '2) La RETURNS TABLE espone sorgente_codice_interno e sorgente_etichetta, non sorgente_codice');

-- ============================================================
-- 3/4) I valori
-- ============================================================
SELECT is(
    (SELECT sorgente_codice_interno FROM t_riga),
    'PGTAP_SCI_ORIGINE'::varchar,
    '3) sorgente_codice_interno e'' il nome del tipo, anche col codice rinominato');

SELECT is(
    (SELECT sorgente_etichetta FROM t_riga),
    'Origine di prova'::varchar,
    '4) sorgente_etichetta e'' l''etichetta della sorgente');

-- ============================================================
-- 5/6) L'ordinamento
-- ============================================================
SELECT is(
    pg_temp.ordina((SELECT commessa_id FROM t_c), 'sorgente_etichetta', 'asc')
      + pg_temp.ordina((SELECT commessa_id FROM t_c), 'sorgente_etichetta', 'desc'),
    2::bigint,
    '5) Si ordina per sorgente_etichetta, nei due versi');

SELECT throws_ok(
    format('SELECT pg_temp.ordina(%s, %L, %L)', (SELECT commessa_id FROM t_c), 'sorgente_codice', 'asc'),
    'P0001',
    NULL,
    '6) sorgente_codice e'' fuori whitelist: fail-loud');

-- ============================================================
-- 7) ⭐ INVARIANTE: il seed ordinabile e' tutto nella whitelist
-- ============================================================
-- ⚠️ Si raccolgono i RIFIUTATI, e un catalogo senza colonne ordinabili ha una
--   risposta sua: senza, il ciclo che non gira passerebbe per «nessun rifiuto»
--   (verde per sottrazione).
CREATE TEMP TABLE t_controllate (campo text, rifiutato boolean);

DO $wl$
DECLARE c text;
BEGIN
    FOR c IN
        SELECT lc.campo_sorgente
          FROM ui.lista_colonna lc
          JOIN ui.lista_definizione d ON d.id = lc.lista_id
         WHERE d.codice = 'vendite.commesse_attivita'
           AND lc.attivo AND lc.ordinabile
           AND NULLIF(btrim(lc.campo_sorgente), '') IS NOT NULL
    LOOP
        BEGIN
            PERFORM pg_temp.ordina((SELECT commessa_id FROM t_c), c, 'asc');
            INSERT INTO t_controllate VALUES (c, false);
        EXCEPTION WHEN SQLSTATE 'P0001' THEN
            INSERT INTO t_controllate VALUES (c, true);
        END;
    END LOOP;
END $wl$;

SELECT is(
    (SELECT CASE WHEN count(*) = 0 THEN 'nessuna colonna ordinabile a catalogo'
                 ELSE COALESCE(string_agg(campo, ',' ORDER BY campo) FILTER (WHERE rifiutato),
                               'nessun rifiuto') END
       FROM t_controllate),
    'nessun rifiuto',
    '7) Ogni colonna ordinabile della lista a catalogo e'' nella whitelist della funzione');

SELECT * FROM finish();

ROLLBACK;
