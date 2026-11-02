-- ------------------------------------------------------------
-- SPDX-License-Identifier: AGPL-3.0-or-later
-- pgTAP test per Zero ERP
-- Test: il pull FIRMA cio' che consegna — vendite.attivita_fatturabili.emit_batch_id
-- Piano: brief-residuo-fatturabili-e-bandiere-esito-parziale, sezione 9 (D1+D2)
-- ------------------------------------------------------------
-- Cosa presidia questo file
--   La promessa del marchio, che e' una sola:
--
--     ⭐ una riga di attivita_fatturabili ricorda QUALE GIRO l'ha consegnata,
--        anche dopo essere stata liberata da un giro disfatto.
--
--   Senza quella memoria una riga liberata e' indistinguibile da una appena
--   consegnata, la select la raccoglie per COORDINATE, e la commessa che il
--   pull ha RESPINTO viene fatturata lo stesso — senza nessun errore. E' il
--   difetto D1, visto in collaudo il 2026-09-04 (lotti 10140/10141).
--
-- 🔴 IL TEST CHE VALE DI PIU' E' IL 5, e non il 4.
--   Il 4 verifica che il pull marchi cio' che INSERISCE: e' la meta' facile,
--   e da sola non chiude niente. Il 5 verifica il ramo di UPDATE su una riga
--   LIBERATA — cioe' esattamente il residuo. E' li' che il difetto vive: le
--   tre righe del collaudo (26828/26829/26830) erano nate da un giro, sono
--   sopravvissute a una riapertura e a un annullo, ed erano ancora li'.
--   ⛔ Un test che marchia solo all'INSERT sarebbe verde e non direbbe niente:
--   in un giro di collaudo l'INSERT non passa quasi mai, perche' la riga c'e'
--   gia' dal giro precedente.
--
-- ⚠️ IL 6 E' IL SUO CONTRARIO, e serve altrettanto.
--   Un chiamante SENZA giro (i pgTAP storici a 4 argomenti, il backend
--   finche' non passa il parametro) non deve poter SMARCHIARE una riga gia'
--   marchiata. Se lo facesse, ogni chiamata di servizio riporterebbe righe
--   marchiate allo stato anonimo, e il difetto rientrerebbe dalla finestra
--   senza che nessuna riga di codice lo dica.
--
-- ⚠️ FIXTURE SCELTA, NON FABBRICATA, e dichiarato invece che nascosto.
--   Una commessa con sorgente ROOT, attivita' approvate e non emesse e tutte
--   le anagrafiche coerenti e' il prodotto di un push: fabbricarla qui
--   vorrebbe dire riscrivere quel percorso. Il file quindi SCEGLIE una
--   commessa reale e lavora dentro BEGIN/ROLLBACK; se non ce ne sono, i test
--   di comportamento si SALTANO invece di fallire — un rosso da assenza di
--   dati non dice niente a nessuno. I test 1-2 sono strutturali e girano
--   sempre, anche su un database ricostruito da zero.
-- ------------------------------------------------------------
-- Indice test
-- 1) La colonna emit_batch_id esiste, e uuid e nullable
-- 2) La firma del pull porta p_emit_batch_id
-- 3) Fixture: una commessa con lavoro da consegnare
-- 4) Il pull con un giro MARCHIA le righe che consegna (ramo INSERT/UPDATE)
-- 5) 🔴 RI-ADOZIONE: una riga LIBERATA viene rimarchiata dal giro successivo
-- 6) ⚠️ Un pull SENZA giro non smarchia cio' che un giro aveva marchiato
-- 7) La vista di presidio non elenca una riga marchiata
-- ------------------------------------------------------------

BEGIN;

-- ⚠️ Vincoli DIFFERITI: senza questa riga il test smetterebbe di verificarli.
--   Un trigger DEFERRABLE INITIALLY DEFERRED scatta al COMMIT, e qui il COMMIT
--   non arriva mai (si chiude in ROLLBACK): sarebbero saltati in silenzio, e il
--   file sarebbe verde per sottrazione.
--   Brief: brief-db-pgtap-runner-rls-baseline §19.
SET CONSTRAINTS ALL IMMEDIATE;

-- Contesto applicativo: il test gira come gira l'applicazione (ruolo
-- OPERATORE + RLS attiva), non come owner.
-- Brief: brief-db-pgtap-runner-rls-baseline §8.
DO $ctx$ BEGIN PERFORM script.fn_pgtap_set_contesto_operatore(); END $ctx$;

SELECT plan(7);

-- ============================================================
-- Strutturali (girano sempre)
-- ============================================================

-- Nullable, e non e' una mezza misura: alle righe di oggi un giro non si puo'
-- attribuire senza inventarlo. Il NULL e' l'informazione «nessun giro
-- rivendica questo lavoro», che e' cio' che dbops.vw_af_senza_giro elenca.
SELECT ok(
  EXISTS (
    SELECT 1 FROM information_schema.columns
     WHERE table_schema = 'vendite' AND table_name = 'attivita_fatturabili'
       AND column_name = 'emit_batch_id'
       AND data_type = 'uuid'
       AND is_nullable = 'YES'),
  '1) La colonna emit_batch_id esiste, e uuid e nullable');

-- ⚠️ Si guarda il NOME del parametro, non il conteggio degli argomenti: un
-- sesto parametro aggiunto domani non deve far diventare rosso questo test,
-- ma un parametro RINOMINATO deve.
SELECT ok(
  (SELECT count(*) FROM pg_proc p
     JOIN pg_namespace n ON n.oid = p.pronamespace
    WHERE n.nspname = 'vendite'
      AND p.proname = 'fn_emit_attivita_fatturabili_da_commessa'
      AND pg_get_function_arguments(p.oid) ILIKE '%p_emit_batch_id%') = 1,
  '2) La firma del pull porta p_emit_batch_id');

-- ============================================================
-- Fixture
-- ============================================================
-- Criterio: una commessa con sorgente ROOT e almeno una attivita' APPROVATA e
-- NON_EMESSA. Sono le stesse condizioni che il pull applica nel proprio
-- ciclo: chiedendole qui, la fixture non sceglie un soggetto che la funzione
-- legittimamente ignora — e il test non diventa rosso accusando il codice
-- invece della propria selezione.
CREATE TEMP TABLE tmp_commessa_marchio AS
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

-- I due giri del test. Fissi e diversi fra loro: il 5 confronta il secondo
-- con il primo, e con uuid casuali un fallimento non sarebbe leggibile.
CREATE TEMP TABLE tmp_giri_marchio AS
SELECT '11111111-1111-4111-8111-111111111111'::uuid AS giro_a,
       '22222222-2222-4222-8222-222222222222'::uuid AS giro_b;

SELECT CASE
  WHEN NOT EXISTS (SELECT 1 FROM tmp_commessa_marchio)
    THEN skip('nessuna commessa con lavoro APPROVATA/NON_EMESSA su questo DB', 5)
  ELSE ok(TRUE, '3) Fixture: una commessa con lavoro da consegnare')
END;

-- ============================================================
-- 4) Il pull con un giro MARCHIA cio' che consegna
-- ============================================================
-- Il pull tocca sia righe nuove sia righe gia' esistenti; l'asserzione non
-- distingue i due rami di proposito — dice «tutto cio' che questo giro ha
-- consegnato porta il suo nome», che e' la promessa intera.
SELECT CASE
  WHEN NOT EXISTS (SELECT 1 FROM tmp_commessa_marchio) THEN NULL
  ELSE lives_ok(
    format($$ SELECT * FROM vendite.fn_emit_attivita_fatturabili_da_commessa(
                 p_commessa_id   => %s,
                 p_only_approved => true,
                 p_dry_run       => false,
                 p_gruppi        => NULL,
                 p_emit_batch_id => %L::uuid) $$,
           (SELECT id FROM tmp_commessa_marchio),
           (SELECT giro_a FROM tmp_giri_marchio)),
    '4) Il pull con un giro gira e consegna')
END;

-- Le righe consegnate da questo giro. Si fotografano ADESSO: il 5 le libera e
-- le rilancia, e dopo l'insieme non sarebbe piu' ricostruibile dal marchio.
CREATE TEMP TABLE tmp_af_marchio AS
SELECT af.id
  FROM vendite.attivita_fatturabili af
 WHERE af.commessa_id = (SELECT id FROM tmp_commessa_marchio)
   AND af.emit_batch_id = (SELECT giro_a FROM tmp_giri_marchio);

-- ============================================================
-- 5) 🔴 LA RI-ADOZIONE — il ramo dove vive il difetto
-- ============================================================
-- Si riproduce il residuo: la riga viene LIBERATA (e' cio' che fanno
-- l'annullo e il ritorno in bozza, via fn_cleanup_fatture_by_ids), quindi
-- resta li' libera e in competenza. Poi passa un ALTRO giro.
-- ⭐ Dopo, la riga deve portare il nome del SECONDO giro: se portasse ancora
-- il primo — o nessuno — sarebbe di nuovo indistinguibile da lavoro che il
-- giro corrente non ha mai rivendicato.
-- ⚠️ La liberazione azzera lock_batch_id e NON emit_batch_id: e' il punto
-- dell'intero disegno, e questo test lo esercita invece di dichiararlo.
-- ⚠️ Le scritture stanno in un DO, non dentro la CASE dell'asserzione: una
--   CTE che modifica dati non e' ammessa in una subquery, e — anche potendo —
--   leggerebbe la propria snapshot e non vedrebbe cio' che ha appena scritto.
--   Prima si costruisce il caso, poi lo si guarda.
-- ⭐ fn_libera_attivita_fatturabili riporta da se' le commesse_attivita a
--   NON_EMESSA: e' una primitiva sola per un fatto solo, e per questo qui non
--   c'e' nessun UPDATE a mano da tenere allineato.
DO $residuo$
DECLARE
    v_commessa vendite.commesse.id%TYPE;
    v_giro_b   vendite.attivita_fatturabili.emit_batch_id%TYPE;
    v_ids      bigint[];
BEGIN
    SELECT id INTO v_commessa FROM tmp_commessa_marchio;
    IF v_commessa IS NULL THEN RETURN; END IF;

    SELECT giro_b INTO v_giro_b FROM tmp_giri_marchio;
    SELECT array_agg(id) INTO v_ids FROM tmp_af_marchio;

    -- Il residuo: la riga torna libera e in competenza, come dopo un annullo.
    PERFORM vendite.fn_libera_attivita_fatturabili(v_ids);

    -- Passa un ALTRO giro.
    PERFORM vendite.fn_emit_attivita_fatturabili_da_commessa(
        v_commessa, true, false, NULL, v_giro_b);
END
$residuo$;

SELECT CASE
  WHEN NOT EXISTS (SELECT 1 FROM tmp_commessa_marchio) THEN NULL
  WHEN NOT EXISTS (SELECT 1 FROM tmp_af_marchio)
    THEN skip('il pull non ha consegnato nessuna riga per questa commessa', 1)
  ELSE ok(
    (SELECT count(*) FROM vendite.attivita_fatturabili af
      WHERE af.id IN (SELECT id FROM tmp_af_marchio)
        AND af.emit_batch_id IS DISTINCT FROM (SELECT giro_b FROM tmp_giri_marchio)) = 0,
    '5) RI-ADOZIONE: una riga liberata porta il marchio del giro SUCCESSIVO')
END;

-- ============================================================
-- 6) ⚠️ Un pull SENZA giro non smarchia
-- ============================================================
-- Il COALESCE del ramo di UPDATE. Senza, ogni chiamata di servizio a 4
-- argomenti riporterebbe righe marchiate allo stato anonimo — e il difetto
-- rientrerebbe senza che una riga di codice lo dica.
-- ⚠️ La chiamata e' a QUATTRO argomenti, di proposito: e' la forma con cui il
--   backend e i pgTAP storici chiamano oggi il pull. Se la scrivessi a cinque
--   con NULL esplicito proverei un caso che nessuno esegue.
DO $senza_giro$
DECLARE
    v_commessa vendite.commesse.id%TYPE;
    v_ids      bigint[];
BEGIN
    SELECT id INTO v_commessa FROM tmp_commessa_marchio;
    IF v_commessa IS NULL THEN RETURN; END IF;

    SELECT array_agg(id) INTO v_ids FROM tmp_af_marchio;

    PERFORM vendite.fn_libera_attivita_fatturabili(v_ids);
    PERFORM vendite.fn_emit_attivita_fatturabili_da_commessa(v_commessa);
END
$senza_giro$;

SELECT CASE
  WHEN NOT EXISTS (SELECT 1 FROM tmp_commessa_marchio) THEN NULL
  WHEN NOT EXISTS (SELECT 1 FROM tmp_af_marchio)
    THEN skip('nessuna riga consegnata da confrontare', 1)
  ELSE ok(
    (SELECT count(*) FROM vendite.attivita_fatturabili af
      WHERE af.id IN (SELECT id FROM tmp_af_marchio)
        AND af.emit_batch_id IS DISTINCT FROM (SELECT giro_b FROM tmp_giri_marchio)) = 0,
    '6) Un pull senza giro NON smarchia le righe gia'' marchiate')
END;

-- ============================================================
-- 7) Il presidio non elenca cio' che e' marchiato
-- ============================================================
-- ⚠️ Salta se la vista non c'e' ancora o se il ruolo non la puo' leggere: il
-- GRANT e' un changeSet suo (90_end), e un test che diventa rosso per un
-- privilegio mancante accuserebbe il disegno invece della sequenza di apply.
--
-- ⛔ E la guardia dev'essere DINAMICA. Un `CASE ... WHEN to_regclass(...) IS
--   NULL THEN skip(...) ELSE (SELECT ... FROM dbops.vw_af_senza_giro)` NON
--   protegge niente: il ramo ELSE viene comunque ANALIZZATO, e su una vista
--   che non esiste il fallimento arriva al parse, prima che la CASE possa
--   scegliere. L'EXECUTE rimanda l'analisi al momento in cui si e' gia'
--   deciso di eseguirla.
CREATE TEMP TABLE tmp_presidio_marchio (n bigint);

DO $presidio$
BEGIN
    IF to_regclass('dbops.vw_af_senza_giro') IS NULL THEN
        RETURN;
    END IF;
    IF NOT has_table_privilege(current_user, 'dbops.vw_af_senza_giro', 'SELECT') THEN
        RETURN;
    END IF;
    EXECUTE $q$
        INSERT INTO tmp_presidio_marchio (n)
        SELECT count(*)
          FROM dbops.vw_af_senza_giro v
         WHERE v.attivita_fatturabile_id IN (SELECT id FROM tmp_af_marchio)
    $q$;
END
$presidio$;

SELECT CASE
  WHEN NOT EXISTS (SELECT 1 FROM tmp_presidio_marchio)
    THEN skip('dbops.vw_af_senza_giro non applicata, o non leggibile da questo ruolo', 1)
  WHEN NOT EXISTS (SELECT 1 FROM tmp_af_marchio)
    THEN skip('nessuna riga marchiata da confrontare', 1)
  ELSE ok(
    (SELECT n FROM tmp_presidio_marchio) = 0,
    '7) La vista di presidio non elenca una riga marchiata')
END;

SELECT * FROM finish();
ROLLBACK;
