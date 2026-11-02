-- ------------------------------------------------------------
-- SPDX-License-Identifier: AGPL-3.0-or-later
-- pgTAP test per Zero ERP
-- Test: la guardia di congelamento e' UNA sola, e non ha perso nulla fondendosi
--       brief-db-be-iva-risolutore-e-regime-cliente, `D34`
-- ------------------------------------------------------------
-- A cosa serve, in una frase
--   Fondere due funzioni in una e' facile; farlo SENZA perdere per strada il
--   codice errore specifico e' la parte che si sbaglia. Questo file verifica
--   proprio quella.
--
-- ⭐ COM'ERA
--   `trgfn_fatture_righe_guard_congelamento` (28 luglio) e
--   `trgfn_fattura_satellite_guard_congelamento` (30 luglio) erano la STESSA
--   funzione: somiglianza 0.63 sul corpo senza commenti, e differenze in due
--   punti soli — come si trova la fattura, e il codice errore. La seconda e'
--   la generalizzazione della prima, scritta due giorni dopo; nessuno era
--   tornato indietro a riassorbirla.
--
-- ⛔ LA COSA CHE SI PERDE FONDENDO, e che qui si sorveglia
--   Il codice errore. Se le righe si prendessero `E_FATTURA_SATELLITE_CONGELATO`
--   il database continuerebbe a rifiutare la scrittura — quindi NIENTE
--   sembrerebbe rotto — ma il backend commuta su quel codice, e vedrebbe
--   arrivare un errore che non e' il suo. E' un difetto che non fa rumore.
--
-- Indice test
-- 1) La funzione dedicata non esiste piu
-- 2) La guardia generica e montata sulle righe, con ENTRAMBI gli argomenti
-- 3) ⭐ Una riga congelata e ancora rifiutata CON IL SUO messaggio, non quello dei satelliti
-- 4) ⭐ E i satelliti continuano ad avere il LORO: nessuna contaminazione
-- 5) Sotto la soglia si scrive, da entrambe le parti (la guardia non e un muro fisso)
-- ------------------------------------------------------------

BEGIN;

-- ⚠️ Vincoli DIFFERITI: senza questa riga il test smetterebbe di verificarli.
--   Brief: brief-db-pgtap-runner-rls-baseline §19.
SET CONSTRAINTS ALL IMMEDIATE;

-- Contesto applicativo: RLS attiva, come gira l'applicazione.
-- Brief: brief-db-pgtap-runner-rls-baseline §8.
DO $ctx$ BEGIN PERFORM script.fn_pgtap_set_contesto_operatore(); END $ctx$;

SELECT plan(5);

-- ============================================================
-- 1) La funzione dedicata e' sparita
-- ============================================================
SELECT is(
  (SELECT count(*) FROM pg_proc p JOIN pg_namespace n ON n.oid = p.pronamespace
    WHERE n.nspname = 'vendite' AND p.proname = 'trgfn_fatture_righe_guard_congelamento'),
  0::bigint,
  '1) trgfn_fatture_righe_guard_congelamento non esiste piu: riassorbita dalla generica'
);

-- ============================================================
-- 2) La generica e' montata sulle righe, con DUE argomenti
-- ============================================================
-- ⚠️ Si verificano ENTRAMBI gli argomenti, e non solo che il trigger esista:
--   montarlo con il solo `fattura_id` funzionerebbe — la scrittura verrebbe
--   comunque rifiutata — ma con il codice errore SBAGLIATO. Il test 3 lo
--   prenderebbe, questo lo dice prima e con precisione.
-- ⚠️ E si verifica anche il NOME del trigger: i BEFORE ROW scattano in ordine
--   alfabetico, quindi rinominarlo lo sposterebbe rispetto agli altri `a10`
--   sulla stessa tabella.
SELECT is(
  (SELECT t.tgname || ' -> ' || p.proname || ' (' ||
          array_to_string(
            ARRAY(SELECT a FROM unnest(regexp_split_to_array(
                    encode(t.tgargs, 'escape'), '\\000')) a WHERE a <> ''), ', ') || ')'
     FROM pg_trigger t
     JOIN pg_class c ON c.oid = t.tgrelid
     JOIN pg_proc p  ON p.oid = t.tgfoid
    WHERE c.oid = 'vendite.fatture_righe'::regclass
      AND NOT t.tgisinternal
      AND t.tgname = 'trg_fatture_righe_a10_guard_congelamento_ins_upd_dlt'),
  'trg_fatture_righe_a10_guard_congelamento_ins_upd_dlt -> '
  || 'trgfn_fattura_satellite_guard_congelamento (fattura_id, E_FATTURA_RIGA_CONGELATA)',
  '2) la generica e montata sulle righe con la colonna FK E il codice errore'
);

-- ============================================================
-- La materia: una fattura NON congelata con una riga e un satellite
-- ============================================================
CREATE TEMP TABLE tmp_fus AS
SELECT f.id AS fattura_id, f.stato_doc_fiscale_id AS stato_id,
       (SELECT r.id FROM vendite.fatture_righe r
         WHERE r.fattura_id = f.id ORDER BY r.id LIMIT 1)     AS riga_id,
       (SELECT s.id FROM vendite.fatture_scadenze s
         WHERE s.fattura_id = f.id ORDER BY s.id LIMIT 1)     AS scadenza_id
  FROM vendite.fatture f
  JOIN config.stati_doc_fiscale sd ON sd.id = f.stato_doc_fiscale_id
 WHERE sd.congela_fiscale IS FALSE
   AND EXISTS (SELECT 1 FROM vendite.fatture_righe r WHERE r.fattura_id = f.id)
   AND EXISTS (SELECT 1 FROM vendite.fatture_scadenze s WHERE s.fattura_id = f.id)
 ORDER BY f.id
 LIMIT 1;

-- ⚠️ Si congela spostando la COLONNA, non lo stato della fattura:
--   vendite.fatture ha un guard di transizione, e forzarlo proverebbe quello.
UPDATE config.stati_doc_fiscale SET congela_fiscale = true
 WHERE id = (SELECT stato_id FROM tmp_fus);

-- ============================================================
-- 3) ⭐ La riga ha ancora il SUO messaggio
-- ============================================================
-- ⛔ E' il caso per cui esiste questo file. Un `throws_ok` sul solo SQLSTATE
--   sarebbe verde anche col codice dei satelliti: entrambi sollevano `P0001`.
--   Si guarda il MESSAGGIO, che e' legato al codice e non alla funzione.
SELECT throws_like(
  format('UPDATE vendite.fatture_righe SET descrizione = descrizione WHERE id = %s',
         (SELECT riga_id FROM tmp_fus)),
  '%le righe non sono piu%',
  '3) la riga congelata solleva ancora il messaggio DELLE RIGHE, non quello dei satelliti'
);

-- ============================================================
-- 4) ⭐ E i satelliti non si sono presi quello delle righe
-- ============================================================
-- ⚠️ Il gemello del 3, e serve: un parametro sbagliato al contrario — il
--   codice delle righe passato a tutti — darebbe comunque verde il caso 3.
SELECT throws_like(
  format('UPDATE vendite.fatture_scadenze SET data_scadenza = data_scadenza WHERE id = %s',
         (SELECT scadenza_id FROM tmp_fus)),
  '%non e'' piu'' modificabile%',
  '4) il satellite solleva ancora il SUO messaggio: nessuna contaminazione fra i due codici'
);

-- ============================================================
-- 5) Sotto la soglia si scrive, da entrambe le parti
-- ============================================================
-- ⚠️ Una guardia che rifiuta SEMPRE passerebbe i casi 3 e 4. Questo e' il
--   controllo che la soglia sia una soglia e non un muro.
UPDATE config.stati_doc_fiscale SET congela_fiscale = false
 WHERE id = (SELECT stato_id FROM tmp_fus);

SELECT lives_ok(
  format('UPDATE vendite.fatture_righe SET descrizione = descrizione WHERE id = %s;'
      || 'UPDATE vendite.fatture_scadenze SET data_scadenza = data_scadenza WHERE id = %s',
         (SELECT riga_id FROM tmp_fus), (SELECT scadenza_id FROM tmp_fus)),
  '5) tolto il congelamento, riga e satellite tornano scrivibili: e una soglia, non un muro'
);

SELECT * FROM finish();

ROLLBACK;
