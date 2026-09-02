-- ------------------------------------------------------------
-- SPDX-License-Identifier: GPL-3.0-or-later
-- pgtap-runner: owner
-- pgtap-runner-motivo: la fixture CREA un registro di numerazione e ne fa
--   girare il contatore — dato di configurazione, non di operatore — e la
--   funzione sotto esame legge vendite.fatture, che ha la RLS. Da dentro un
--   perimetro il conteggio delle fatture sarebbe parziale e la check
--   risponderebbe «si puo' disattivare» proprio nel caso da bloccare.
-- pgtap-contesto: escluso — discende dal marcatore qui sopra.
-- pgTAP test per Zero ERP
-- Test: script.fn_check_registro_disattivabile  (20260831-38)
--       Richiesta: brief-db-richieste-aperte-dal-backend-2, voce 2
-- ------------------------------------------------------------
-- Elenco test (plan 6):
-- 1) ⭐ Un registro SENZA figli: la check risponde []
-- 2) ⭐ ...e la disattivazione passa davvero (il gemello positivo)
-- 3) ⛔ Con un progressivo vivo: la check nomina HA_PROGRESSIVI
-- 4) ⛔ ...e la disattivazione viene rifiutata (P0001)
-- 5) ⭐ La check e il rifiuto dicono LA STESSA COSA
-- 6) ⭐⭐ STRUTTURALE: la check copre TUTTI i guard montati
--
-- Scopo:
--   ⛔ Su vendite.registri_fatturazione i guard di disattivazione sono SETTE, ed
--   erano TRE fino al 2026-08-31: col trasloco vendite.ddt, ordini e resi hanno
--   guadagnato `registro_id`, e l'automazione ha montato il guard DA SOLA a
--   partire dalla FK — al migrate, senza annunciarlo.
--   ⚠️ Quello che sorprende resta il contatore: un registro che ha numerato
--   anche UN SOLO documento ha una riga di progressivi viva, quindi non si
--   spegne piu'. Il cestino e' percio' quasi sempre indisponibile — e senza un
--   motivo a video l'operatore lo scopre premendo.
--
--   ⭐ IL TEST 2 SERVE QUANTO IL 4: senza il gemello positivo, una check che
--   rispondesse «bloccato» SEMPRE passerebbe il 3 e il 4 esattamente come
--   quella giusta. E' la differenza fra «rifiuta il caso giusto» e «rifiuta
--   tutto».
--
--   ⭐⭐ IL TEST 6 E' IL PRESIDIO CHE CONTA, ed e' al posto di quello che il
--   §12.5.2 chiederebbe. La regola sarebbe «la madre CHIAMA la check», ma qui
--   una madre NON ESISTE: a rifiutare e'
--   dbops.trgfn_prevent_deactivate_if_children, un trigger GENERICO guidato da
--   TG_ARGV e condiviso da tutto il database — farlo chiamare una check
--   specifica dei registri ne romperebbe la genericita' per un caso solo.
--   ⇒ Quello che si puo' presidiare e' l'altra meta': che la check non resti
--   INDIETRO rispetto ai guard. Il test 6 legge da `pg_trigger` quali tabelle
--   figlie bloccano davvero la disattivazione, e le confronta con quelle che la
--   check copre. Il giorno che ne compare una in piu', diventa rosso — invece di
--   lasciare la check a spegnere un cestino che il trigger poi rifiuta.
--
-- ⚠️ COSA QUESTO FILE NON PROVA: la frase tradotta. Le tre `reason_key` sono un
--   debito verso il FE (§12.3) e le presidia scripts/check_i18n_keys.py.
-- ------------------------------------------------------------

BEGIN;

SET CONSTRAINTS ALL IMMEDIATE;

SELECT plan(6);

-- ============================================================
-- Fixture: un registro NUOVO e senza figli
-- ============================================================
-- ⚠️ Si nasce su una `utility_id` valorizzata, e non e' un dettaglio:
--   uq_registri_fatturazione_famiglia_emittente_utility occupa lo slot
--   (famiglia, emittente, utility) e quello «per tutte le utility» e' gia'
--   preso dal provisioning. ⛔ E lo slot NON si libera spegnendo il registro
--   che c'e': quell'indice non filtra su `attivo`.
CREATE TEMP TABLE tmp_crd AS
WITH ins AS (
  INSERT INTO vendite.registri_fatturazione (
      codice, descrizione, emittente_soggetto_ruolo_id,
      famiglia_documento, reset_policy, attivo, utility_id)
  SELECT 'CRD-' || r.emittente_soggetto_ruolo_id::text,
         'Registro pgTAP check disattivabile',
         r.emittente_soggetto_ruolo_id, 'DDT', 'ANNUALE', true,
         (SELECT u.id FROM config.utilities u ORDER BY u.id LIMIT 1)
    FROM vendite.registri_fatturazione r
   WHERE r.famiglia_documento = 'DDT'
     AND r.utility_id IS NULL
     AND r.attivo
   ORDER BY r.id
   LIMIT 1
  RETURNING id
)
SELECT id AS registro_id FROM ins;

-- ============================================================
-- 1/2) ⭐ Senza figli: la check tace, e la disattivazione passa
-- ============================================================
SELECT is(
    (SELECT script.fn_check_registro_disattivabile(t.registro_id) FROM tmp_crd t),
    '[]'::jsonb,
    '1) Un registro senza figli: nessun motivo, il cestino resta acceso');

SELECT lives_ok(
    format('UPDATE vendite.registri_fatturazione SET attivo = false WHERE id = %s',
           (SELECT registro_id FROM tmp_crd)),
    '2) ...e la disattivazione passa davvero');

-- ⚠️ Si riaccende: i test successivi hanno bisogno di un registro vivo, e un
--   registro spento non e' il caso in esame.
UPDATE vendite.registri_fatturazione
   SET attivo = true
 WHERE id = (SELECT registro_id FROM tmp_crd);

-- ============================================================
-- 3/4/5) ⛔ Con un progressivo vivo
-- ============================================================
-- ⭐ Il contatore si fa girare dal MOTORE, non inserendo a mano una riga in
--   registri_fatturazione_progressivi: cosi' il test prova il caso che capita
--   davvero — «e' bastato numerare un documento».
-- ⚠️ Verbo in un'istruzione separata dall'asserzione: fn_get_next_progressivo
--   scrive.
CREATE TEMP TABLE tmp_crd_num AS
SELECT vendite.fn_get_next_progressivo(
           (SELECT registro_id FROM tmp_crd),
           DATE '2101-06-15', NULL, '', NULL, 'DDT') AS numero;

SELECT is(
    (SELECT string_agg(m ->> 'reason', ',' ORDER BY m ->> 'reason')
       FROM tmp_crd t,
            LATERAL jsonb_array_elements(
                script.fn_check_registro_disattivabile(t.registro_id)) m),
    'HA_PROGRESSIVI',
    '3) Con un progressivo vivo la check nomina HA_PROGRESSIVI, e solo quello');

PREPARE crd_disattiva AS
UPDATE vendite.registri_fatturazione SET attivo = false
 WHERE id = (SELECT registro_id FROM tmp_crd);

SELECT throws_ok(
    'EXECUTE crd_disattiva',
    'P0001',
    NULL,
    '4) ...e la disattivazione viene rifiutata');

-- ⭐ Il punto: il tooltip e il rifiuto devono dire LA STESSA COSA. La check
--   nomina la tabella figlia nei `valori`, e il trigger la mette nella frase.
SELECT throws_like(
    'EXECUTE crd_disattiva',
    '%registri_fatturazione_progressivi%',
    '5) La frase del rifiuto nomina la stessa figlia che la check dichiara');

-- ============================================================
-- 6) ⭐⭐ La check copre TUTTI i guard montati — derivato da pg_trigger
-- ============================================================
-- ⛔ E' il presidio che sostituisce quello del §12.5.2, qui inapplicabile: a
--   rifiutare e' un trigger generico, non una madre di dominio. Quello che si
--   puo' garantire e' che la check non resti INDIETRO.
-- ⚠️ Le figlie si leggono dal SECONDO argomento di
--   dbops.trgfn_prevent_deactivate_if_children, che e' il nome della tabella
--   figlia. Se ne comparisse un'ottava, questa riga diventa rossa.
--
-- ⭐ ED E' GIA' SUCCESSO, il 2026-09-02: `vendite.commesse` ha guadagnato
--   `registro_id` (changeSet 20260902-07) e l'automazione ATTIVO ha montato il
--   SETTIMO guard da sola, al migrate. Questa riga e' diventata rossa PRIMA
--   che qualcuno premesse un cestino — che e' tutto il punto. La check ha
--   imparato il motivo con 20260902-12.
-- ⛔ E QUANDO RIACCADE: si aggiunge il motivo alla check, POI si aggiorna
--   l'elenco atteso. Aggiornare solo questa riga farebbe tacere il presidio
--   invece di rispondergli, e lascerebbe il cestino acceso su un registro che
--   il trigger rifiuta.
SELECT is(
    (SELECT string_agg(DISTINCT x.figlia, ',' ORDER BY x.figlia)
       FROM pg_trigger t
       JOIN pg_class     c ON c.oid = t.tgrelid
       JOIN pg_namespace n ON n.oid = c.relnamespace
       CROSS JOIN LATERAL (
           SELECT (regexp_match(pg_get_triggerdef(t.oid),
                                '''[^'']+''\s*,\s*''([^'']+)''')) [1] AS figlia) x
      WHERE NOT t.tgisinternal
        AND n.nspname = 'vendite'
        AND c.relname = 'registri_fatturazione'
        AND pg_get_triggerdef(t.oid) LIKE '%prevent_deactivate_if_children%'),
    'commesse,ddt,fatture,ordini,registri_fatturazione_progressivi,resi,tipi_doc_fiscale_registri',
    '6) I guard di disattivazione montati sono esattamente quelli che la check copre');

SELECT * FROM finish();
ROLLBACK;
