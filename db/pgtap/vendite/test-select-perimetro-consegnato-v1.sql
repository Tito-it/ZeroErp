-- ------------------------------------------------------------
-- SPDX-License-Identifier: GPL-3.0-or-later
-- pgtap-runner: owner
-- pgtap-runner-motivo: la fixture costruisce un'AZIENDA e un CLIENTE
--   (dbops.fn_pgtap_crea_emittente_operatore + fn_pgtap_crea_cliente_ba), e un
--   operatore dentro un perimetro non puo' crearli: l'INSERT su
--   anagrafiche.billing_account e' un `... RETURNING id`, e la RLS non lascia
--   RILEGGERE una riga il cui legame all'emittente non esiste ancora — lo
--   scrive il trigger z90, cioe' DOPO. Stesso marcatore e stessa ragione dei
--   file gemelli di questo cantiere e dei sei db/pgtap/rls/*-satelliti.sql.
-- pgTAP test per Zero ERP
-- Test: la select fattura solo cio' che il PROPRIO giro ha consegnato
-- Piano: brief-residuo-fatturabili-e-bandiere-esito-parziale, sezione 9 (D1+D2)
-- rev 2026-10-24 (brief-modello-documento-vendita N-1): i documenti nascono in bozza e si
--   portano avanti con dbops.fn_pgtap_porta_a_stato (prima la commessa nasceva gia'
--   nello stato emittibile, PRONTA_FATTURAZIONE).
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
--
-- 🔴 REV 2026-09-09 — QUELLA RIGA QUI SOPRA ERA VERA A META', E IL CONTO E'
--   ARRIVATO. Si fabbricava la CONSEGNA (il pull) ma non il SOGGETTO: la
--   commessa si CERCAVA, `ORDER BY c.id DESC LIMIT 1` fra quelle con lavoro
--   approvato. ⇒ Il file misurava «l'ultima commessa che c'e' oggi», che non e'
--   una cosa che si possa presidiare.
--   ⛔ Il conto: il changeSet 20260909-62 ha insegnato al pull a NON prendere
--   le righe trattenute da un lotto vivo — cioe' ha funzionato — e la commessa
--   piu' recente su dbdev si e' trovata a essere `TRATTENUTA`
--   (`trattenuta_da_lotti = {12406}`). Il pull ha consegnato zero righe, il
--   test 2 e' diventato rosso e i test 3-4-5 sono stati SALTATI: il presidio
--   piu' importante di questo file — il 4 — non ha girato affatto.
--   ⚠️ E su un database ricostruito da zero non c'e' nessuna commessa da
--   trovare: la' saltavano tutti e quattro da sempre, in silenzio.
--   ⇒ Adesso la commessa, la sua sorgente ROOT e la sua riga approvata si
--   COSTRUISCONO, con gli stessi building block dei file gemelli. Il pull
--   resta la primitiva vera: e' cio' che questo file vuole misurare.
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

-- ⛔ Il mondo si costruisce PRIMA di aprire il contesto: dopo, il legame
--   BA→emittente lo scriverebbe anche `trg_billing_account_z90_link_ef_ins` e i
--   due si scontrerebbero su `uq_emittenti_fiscali_ba` (un BA ha ESATTAMENTE un
--   emittente).
CREATE TEMP TABLE tmp_sel_mondo AS
SELECT * FROM dbops.fn_pgtap_crea_emittente_operatore();

CREATE TEMP TABLE tmp_sel_cliente AS
SELECT * FROM dbops.fn_pgtap_crea_cliente_ba(
    'perimetro consegnato', NULL, (SELECT soggetto_ruolo_id FROM tmp_sel_mondo));

-- Contesto applicativo: il test gira come gira l'applicazione, e l'operatore e'
-- quello che ha nel perimetro l'azienda appena creata.
-- Brief: brief-db-pgtap-runner-rls-baseline §8.
DO $ctx$
BEGIN
    PERFORM script.fn_pgtap_set_contesto_operatore(
        (SELECT auth_user_id FROM tmp_sel_mondo));
END $ctx$;

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

-- La commessa si COSTRUISCE: sorgente ROOT (che il pull PRETENDE, o solleva
-- E_VALORE_MANCANTE prima ancora di guardare le righe) e una riga approvata e
-- non ancora emessa.
-- ⚠️ `sorgente_uid` non e' testo libero: un guard lo confronta col
--   `key_selector` del tipo a catalogo E pretende che la riga esista nella
--   target_table. Con la sorgente COMMESSA la target e' vendite.commesse:
--   l'id appena creato la soddisfa per costruzione, anche su un database
--   ricostruito da zero dove non c'e' nessun ordine da citare.
CREATE TEMP TABLE tmp_sel_rif AS
SELECT
  (SELECT m.soggetto_ruolo_id FROM tmp_sel_mondo m)          AS emittente_sr,
  (SELECT c.billing_account_id FROM tmp_sel_cliente c)       AS billing_account_id,
  (SELECT c.utility_id FROM tmp_sel_cliente c)               AS utility_id,
  (SELECT c.istanza_utility_id FROM tmp_sel_cliente c)       AS istanza_utility_id,
  (SELECT a.id FROM catalogo.articoli a
    WHERE a.attivo IS TRUE AND a.is_composito = FALSE ORDER BY a.id LIMIT 1) AS articolo_id,
  (SELECT u.id FROM catalogo.unita_misura u
    WHERE u.attivo IS TRUE ORDER BY u.id LIMIT 1)            AS uom_id,
  (SELECT t.id FROM config.tipi_doc_fiscale t
    WHERE t.attivo IS TRUE ORDER BY t.id LIMIT 1)            AS tipo_doc_fiscale_id,
  (SELECT v.id FROM config.valute v ORDER BY v.id LIMIT 1)   AS valuta_id,
  (SELECT sc.id FROM vendite.stati_commessa sc
    WHERE sc.attivo IS TRUE AND sc.emittibile IS TRUE ORDER BY sc.id LIMIT 1) AS stato_ok,
  (SELECT s.id FROM config.sorgenti s
    WHERE s.codice_interno = 'COMMESSA' AND s.attivo IS TRUE) AS sorgente_id,
  date_trunc('month', script.fn_data_operativa())::date                    AS mese;

CREATE TEMP TABLE tmp_commessa_sel (id bigint);

DO $costruisci$
DECLARE
    v_rif  record;
    v_comm vendite.commesse.id%TYPE;
BEGIN
    SELECT * INTO v_rif FROM tmp_sel_rif;

    -- rev 2026-10-24: la commessa nasce BOZZA (trigger della nascita) e passa
    --   allo stato emittibile DOPO la sua riga APPROVATA, che il passaggio a
    --   PRONTA_FATTURAZIONE pretende (fn_check_commessa_pronta_fatturazione).
    INSERT INTO vendite.commesse (codice, billing_account_id, utility_id,
                                  emittente_soggetto_ruolo_id)
    VALUES ('PGTAP-SEL-' || substr(md5(clock_timestamp()::text), 1, 8),
            v_rif.billing_account_id, v_rif.utility_id, v_rif.emittente_sr)
    RETURNING id INTO v_comm;

    INSERT INTO vendite.commesse_sorgenti
        (commessa_id, sorgente_tipo_id, sorgente_uid, ruolo_link)
    VALUES (v_comm, v_rif.sorgente_id, v_comm::text, 'ROOT');

    INSERT INTO vendite.commesse_attivita (
        commessa_id, segment_key, articolo_id, istanza_utility_id, data_attivita,
        uom_id, quantita, competenza_mese, competenza_dal, competenza_al,
        tipo_doc_fiscale_id, valuta_id, prezzo_snapshot, pricing_mode,
        stato_approvazione, stato_emissione, sorgente_tipo_id, sorgente_uid)
    VALUES (v_comm,
            'PGTAP-SEL-' || substr(md5(clock_timestamp()::text), 1, 12),
            v_rif.articolo_id, v_rif.istanza_utility_id, v_rif.mese,
            v_rif.uom_id, 1, v_rif.mese, v_rif.mese,
            (v_rif.mese + INTERVAL '1 month - 1 day')::date,
            v_rif.tipo_doc_fiscale_id, v_rif.valuta_id, 10.000000, 'FIXED',
            'APPROVATA', 'NON_EMESSA', -- La riga NORMALE ha la sua sorgente (vincolo 20261012-27).
            (SELECT s.id FROM config.sorgenti s WHERE s.codice_interno = 'COMMESSA'), v_comm::text);

    PERFORM dbops.fn_pgtap_porta_a_stato('vendite.commesse', v_comm,
        (SELECT sc.codice_interno FROM vendite.stati_commessa sc WHERE sc.id = v_rif.stato_ok));

    INSERT INTO tmp_commessa_sel VALUES (v_comm);
END
$costruisci$;

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

-- ⭐ Nessuno `skip` qui, e non e' una svista: la commessa la costruisce la
--   fixture, quindi «non c'e' una commessa» non e' piu' una condizione del
--   database — sarebbe una frase falsa. Se il pull non consegna niente questo
--   test dev'essere ROSSO: e' un difetto, non un dato mancante.
SELECT ok((SELECT count(*) FROM tmp_af_sel) > 0,
          '2) Fixture: il pull ha consegnato righe firmandole col giro A');

-- ============================================================
-- 3) Il giro A prende le proprie righe
-- ============================================================
-- ⚠️ `p_lock => false`: si misura la SCELTA, non il lucchetto. Con il lucchetto
--   la prima chiamata marcherebbe le righe e le successive non le vedrebbero
--   piu', e i test 4 e 5 misurerebbero l'effetto della 3.
SELECT CASE
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
