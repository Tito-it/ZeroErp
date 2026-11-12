-- ------------------------------------------------------------
-- SPDX-License-Identifier: AGPL-3.0-or-later
-- pgTAP test per Zero ERP
--
-- Test: ui.lista_colonna — l'assenza di un testo opzionale e' NULL, mai ''
-- Riferimento: brief-db-lista-colonna-campo-sorgente-null; changeSet
--   90_end/20261112-30 (i cinque CHECK) e il mirror 80_data/20260806-15
--   (nullValue "NULL").
--
-- Semantica attesa (il contratto, non l'implementazione):
--   - su campo_sorgente, etichetta_estesa, formato, gruppo ed
--     etichetta_i18n_key la stringa vuota e' rifiutata, ciascuna dal suo
--     vincolo; una stringa di soli spazi vale come vuota;
--   - NULL passa: e' la forma dell'assenza;
--   - il seed scrive NULL: una colonna azione del catalogo non ha sorgente,
--     e nessuna riga ha piu' la stringa vuota su queste colonne.
--   Le righe di prova si costruiscono qui, con id fuori scala.
--   ⚠️ Il test 9 prova il RISULTATO, non chi lo produce: anche la conversione di
--     20261112-30 porta a NULL le stringhe vuote. Che le scriva il loader col
--     nullValue nuovo si prova col render offline del mirror (brief, §3).
--
-- Elenco test (plan 9):
--   1) i cinque vincoli esistono
--   2) campo_sorgente '' rifiutato da chk_lista_colonna_campo_sorgente_non_vuoto
--   3) etichetta_estesa '' rifiutata dal suo vincolo
--   4) formato '' rifiutato dal suo vincolo
--   5) gruppo '' rifiutato dal suo vincolo
--   6) etichetta_i18n_key '' rifiutata dal suo vincolo
--   7) una stringa di soli spazi vale come vuota
--   8) tutti NULL: la riga entra
--   9) il seed: le colonne azione hanno campo_sorgente NULL, e nessuna riga ha
--      '' sulle cinque colonne
-- ------------------------------------------------------------

BEGIN;
-- Contesto applicativo (preambolo, guardrail_pgtap_preambolo).
DO $ctx$ BEGIN PERFORM script.fn_pgtap_set_contesto_operatore(); END $ctx$;
-- ⚠️ Vincoli DIFFERITI: senza questa riga il test smetterebbe di verificarli.
SET CONSTRAINTS ALL IMMEDIATE;

SELECT plan(9);

-- Una riga di prova: la colonna indicata prende il valore indicato, le altre NULL.
CREATE OR REPLACE FUNCTION pg_temp.riga(p_id integer, p_colonna text, p_valore text)
RETURNS text LANGUAGE sql AS $f$
  SELECT format(
    'INSERT INTO ui.lista_colonna (id, lista_id, codice, etichetta, %1$s, tipo_colonna, '
    '  tipo_dato, ordine_default, user_insert) '
    'SELECT %2$s, min(ld.id), %3$L, %4$L, %5$L, ''informazione'', ''string'', 9990, ''pgtap'' '
    '  FROM ui.lista_definizione ld',
    p_colonna, p_id, 'zz_vuoti_' || p_id, 'Prova testi vuoti', p_valore);
$f$;

SELECT is(
  (SELECT count(*)::int FROM pg_catalog.pg_constraint
    WHERE conrelid = 'ui.lista_colonna'::regclass
      AND contype = 'c'
      AND conname IN ('chk_lista_colonna_campo_sorgente_non_vuoto',
                      'chk_lista_colonna_etichetta_estesa_non_vuota',
                      'chk_lista_colonna_formato_non_vuoto',
                      'chk_lista_colonna_gruppo_non_vuoto',
                      'chk_lista_colonna_etichetta_i18n_key_non_vuota')),
  5,
  '1) i cinque vincoli esistono');

SELECT is(dbops.fn_pgtap_codice_errore(pg_temp.riga(990001, 'campo_sorgente', '')),
          'chk_lista_colonna_campo_sorgente_non_vuoto',
          '2) campo_sorgente vuoto: rifiutato dal suo vincolo');

SELECT is(dbops.fn_pgtap_codice_errore(pg_temp.riga(990002, 'etichetta_estesa', '')),
          'chk_lista_colonna_etichetta_estesa_non_vuota',
          '3) etichetta_estesa vuota: rifiutata dal suo vincolo');

SELECT is(dbops.fn_pgtap_codice_errore(pg_temp.riga(990003, 'formato', '')),
          'chk_lista_colonna_formato_non_vuoto',
          '4) formato vuoto: rifiutato dal suo vincolo');

SELECT is(dbops.fn_pgtap_codice_errore(pg_temp.riga(990004, 'gruppo', '')),
          'chk_lista_colonna_gruppo_non_vuoto',
          '5) gruppo vuoto: rifiutato dal suo vincolo');

SELECT is(dbops.fn_pgtap_codice_errore(pg_temp.riga(990005, 'etichetta_i18n_key', '')),
          'chk_lista_colonna_etichetta_i18n_key_non_vuota',
          '6) etichetta_i18n_key vuota: rifiutata dal suo vincolo');

SELECT is(dbops.fn_pgtap_codice_errore(pg_temp.riga(990006, 'gruppo', '   ')),
          'chk_lista_colonna_gruppo_non_vuoto',
          '7) una stringa di soli spazi vale come vuota');

SELECT is(dbops.fn_pgtap_codice_errore(pg_temp.riga(990007, 'gruppo', NULL)),
          NULL,
          '8) tutti NULL: la riga entra');

-- Il seed e' contratto (80_data): lo si legge, non si conta una popolazione.
SELECT is(
  (SELECT count(*) FILTER (WHERE lc.tipo_colonna = 'azione' AND lc.campo_sorgente IS NOT NULL)
        + count(*) FILTER (WHERE lc.campo_sorgente = '' OR lc.etichetta_estesa = ''
                              OR lc.formato = '' OR lc.gruppo = '' OR lc.etichetta_i18n_key = '')
     FROM ui.lista_colonna lc)::int,
  0,
  '9) il seed: le colonne azione senza sorgente (NULL) e nessuna stringa vuota');

SELECT * FROM finish();
ROLLBACK;
