-- ------------------------------------------------------------
-- SPDX-License-Identifier: GPL-3.0-or-later
-- pgTAP test per Zero ERP
-- Test: la select fattura solo cio' che il PROPRIO giro ha consegnato
-- Piano: brief-residuo-fatturabili-e-bandiere-esito-parziale, sezione 9 (D1+D2)
-- ------------------------------------------------------------
-- Cosa presidia questo file
--   La chiusura della crepa D1+D2:
--
--     ⭐ «commessa rifiutata» e «commessa non fatturata» devono tornare a
--        essere la stessa affermazione.
--
--   Fino al 2026-09-04 il perimetro di un giro era «tutto cio' che e' libero e
--   in competenza». Una riga liberata da un giro disfatto era indistinguibile
--   da una appena consegnata dal pull: la commessa RESPINTA finiva in fattura
--   lo stesso, e senza nessun errore — la fattura di troppo e' una fattura
--   normale. Adesso la select sceglie per MARCHIO.
--
-- 🔴 IL TEST CHE VALE DI PIU' E' IL 4.
--   Il 3 dice che un giro prende le proprie righe: e' la meta' facile, e da
--   sola sarebbe verde anche col difetto intatto. Il 4 dice che un ALTRO giro
--   NON le prende — cioe' esattamente il residuo che veniva rastrellato. Se un
--   domani qualcuno togliesse il filtro «perche' non serviva», il 3 resterebbe
--   verde e solo il 4 diventerebbe rosso.
--
-- ⚠️ IL 5 PRESIDIA CIO' CHE NON DEVE CAMBIARE.
--   Una chiamata senza giro — nessun `p_lock_batch_id`, quindi per forza senza
--   lucchetto — non filtra: e' l'anteprima storica, che non fattura niente e
--   non deve smettere di funzionare. Un filtro che si applicasse sempre
--   spegnerebbe le anteprime senza che nessuno l'abbia deciso.
--
-- ⭐ Il soggetto si fabbrica con le primitive vere (il pull, con due giri
--   diversi): il file misura le stesse cose su un database ricostruito da zero.
-- ------------------------------------------------------------
-- Indice test
-- 1) Il filtro e' nel corpo della funzione
-- 2) Fixture: il pull consegna righe firmandole col giro A
-- 3) Il giro A prende le proprie righe
-- 4) 🔴 Il giro B NON prende le righe di A (il residuo non si rastrella piu')
-- 5) ⚠️ Una chiamata senza giro non filtra (l'anteprima storica regge)
-- ------------------------------------------------------------

BEGIN;

-- ⚠️ Vincoli DIFFERITI: senza questa riga il test smetterebbe di verificarli.
--   Brief: brief-db-pgtap-runner-rls-baseline §19.
SET CONSTRAINTS ALL IMMEDIATE;

-- Contesto applicativo: il test gira come gira l'applicazione.
-- Brief: brief-db-pgtap-runner-rls-baseline §8.
DO $ctx$ BEGIN PERFORM script.fn_pgtap_set_contesto_operatore(); END $ctx$;

SELECT plan(5);

-- ============================================================
-- 1) Strutturale
-- ============================================================
SELECT ok(
  (SELECT count(*) FROM pg_proc p
     JOIN pg_namespace n ON n.oid = p.pronamespace
    WHERE n.nspname = 'vendite'
      AND p.proname = 'fn_select_attivita_fatturabili'
      AND p.prosrc LIKE '%emit_batch_id%') = 1,
  '1) Il filtro per marchio e nel corpo della select');

-- ============================================================
-- Fixture — due giri, uno solo dei quali consegna
-- ============================================================
CREATE TEMP TABLE tmp_giri_sel AS
SELECT 'aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa'::uuid AS giro_a,
       'bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb'::uuid AS giro_b;

CREATE TEMP TABLE tmp_commessa_sel AS
SELECT c.id
  FROM vendite.commesse c
 WHERE EXISTS (SELECT 1 FROM vendite.commesse_sorgenti cs
                WHERE cs.commessa_id = c.id AND cs.ruolo_link = 'ROOT')
   AND EXISTS (SELECT 1 FROM vendite.commesse_attivita ca
                WHERE ca.commessa_id = c.id
                  AND ca.stato_emissione = 'NON_EMESSA'
                  AND ca.stato_approvazione = 'APPROVATA')
 ORDER BY c.id DESC
 LIMIT 1;

DO $consegna$
DECLARE
    v_commessa vendite.commesse.id%TYPE;
    v_giro_a   vendite.attivita_fatturabili.emit_batch_id%TYPE;
BEGIN
    SELECT id INTO v_commessa FROM tmp_commessa_sel;
    IF v_commessa IS NULL THEN RETURN; END IF;
    SELECT giro_a INTO v_giro_a FROM tmp_giri_sel;

    PERFORM vendite.fn_emit_attivita_fatturabili_da_commessa(
        v_commessa, true, false, NULL, v_giro_a);
END
$consegna$;

-- Le righe consegnate dal giro A, con le loro coordinate: la select le vuole
-- per competenza e tipo documento, e senza quelle non si puo' interrogare.
CREATE TEMP TABLE tmp_af_sel AS
SELECT af.id, af.competenza_mese, af.tipo_doc_fiscale_id
  FROM vendite.attivita_fatturabili af
 WHERE af.commessa_id = (SELECT id FROM tmp_commessa_sel)
   AND af.emit_batch_id = (SELECT giro_a FROM tmp_giri_sel)
   AND af.fatturato IS FALSE
   AND COALESCE(af.lock_in_fatturazione, false) IS FALSE
   AND af.approvato IS TRUE;

SELECT CASE
  WHEN NOT EXISTS (SELECT 1 FROM tmp_commessa_sel)
    THEN skip('nessuna commessa con lavoro APPROVATA/NON_EMESSA su questo DB', 4)
  ELSE ok((SELECT count(*) FROM tmp_af_sel) > 0,
          '2) Fixture: il pull ha consegnato righe firmandole col giro A')
END;

-- ============================================================
-- 3) Il giro A prende le proprie righe
-- ============================================================
-- ⚠️ `p_lock => false`: si misura la SCELTA, non il lucchetto. Con il lucchetto
--   la prima chiamata marcherebbe le righe e le successive non le vedrebbero
--   piu', e i test 4 e 5 misurerebbero l'effetto della 3.
SELECT CASE
  WHEN NOT EXISTS (SELECT 1 FROM tmp_commessa_sel) THEN NULL
  WHEN NOT EXISTS (SELECT 1 FROM tmp_af_sel)
    THEN skip('il pull non ha consegnato righe eleggibili', 1)
  ELSE is(
    (SELECT count(*)::integer
       FROM vendite.fn_select_attivita_fatturabili(
              p_competenza_mese     => (SELECT max(competenza_mese) FROM tmp_af_sel),
              p_tipo_doc_fiscale_id => (SELECT min(tipo_doc_fiscale_id) FROM tmp_af_sel),
              p_lock_batch_id       => (SELECT giro_a FROM tmp_giri_sel),
              p_lock                => false) s
      WHERE s.id IN (SELECT id FROM tmp_af_sel)),
    (SELECT count(*)::integer FROM tmp_af_sel
      WHERE tipo_doc_fiscale_id = (SELECT min(tipo_doc_fiscale_id) FROM tmp_af_sel)),
    '3) Il giro A prende le proprie righe')
END;

-- ============================================================
-- 4) 🔴 Il giro B non prende le righe di A
-- ============================================================
-- E' il residuo: righe libere, in competenza, con tutte le coordinate giuste —
-- e consegnate a un ALTRO giro. Prima venivano rastrellate; adesso no.
SELECT CASE
  WHEN NOT EXISTS (SELECT 1 FROM tmp_commessa_sel) THEN NULL
  WHEN NOT EXISTS (SELECT 1 FROM tmp_af_sel)
    THEN skip('nessuna riga consegnata da confrontare', 1)
  ELSE is(
    (SELECT count(*)::integer
       FROM vendite.fn_select_attivita_fatturabili(
              p_competenza_mese     => (SELECT max(competenza_mese) FROM tmp_af_sel),
              p_tipo_doc_fiscale_id => (SELECT min(tipo_doc_fiscale_id) FROM tmp_af_sel),
              p_lock_batch_id       => (SELECT giro_b FROM tmp_giri_sel),
              p_lock                => false) s
      WHERE s.id IN (SELECT id FROM tmp_af_sel)),
    0,
    '4) Il giro B NON prende le righe consegnate al giro A')
END;

-- ============================================================
-- 5) ⚠️ Senza giro non si filtra
-- ============================================================
-- L'anteprima storica: nessun `p_lock_batch_id`, quindi nessun lucchetto e
-- nessun documento. Deve continuare a vedere il lavoro, o si spegnerebbe una
-- funzione che nessuno ha chiesto di spegnere.
SELECT CASE
  WHEN NOT EXISTS (SELECT 1 FROM tmp_commessa_sel) THEN NULL
  WHEN NOT EXISTS (SELECT 1 FROM tmp_af_sel)
    THEN skip('nessuna riga consegnata da confrontare', 1)
  ELSE ok(
    (SELECT count(*)
       FROM vendite.fn_select_attivita_fatturabili(
              p_competenza_mese     => (SELECT max(competenza_mese) FROM tmp_af_sel),
              p_tipo_doc_fiscale_id => (SELECT min(tipo_doc_fiscale_id) FROM tmp_af_sel),
              p_lock_batch_id       => NULL,
              p_lock                => false) s
      WHERE s.id IN (SELECT id FROM tmp_af_sel)) > 0,
    '5) Una chiamata senza giro non filtra: lanteprima storica regge')
END;

SELECT * FROM finish();
ROLLBACK;
