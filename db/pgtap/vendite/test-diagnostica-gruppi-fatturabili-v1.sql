-- ------------------------------------------------------------
-- SPDX-License-Identifier: GPL-3.0-or-later
-- pgTAP test per Zero ERP
--
-- Test: vendite.fn_diagnostica_gruppi_fatturabili (20260815-29)
--       La FOTOGRAFIA di un gruppo fatturabile: quante righe, in che stato, e
--       in che stato e' la testata della commessa.
--       Brief: brief-db-emittibilita-visibile-e-sbloccabile §9 F4.
-- rev 2026-10-24 (brief-modello-documento-vendita N-1): i documenti nascono in bozza e si
--   portano avanti con dbops.fn_pgtap_porta_a_stato (prima le commesse nascevano gia'
--   nello stato bloccato / emittibile).
--
-- Perche' esiste: fino al 2026-08-15 questa query stava in
-- `CommesseRepository.diagnostica_gruppi`, ed era l'ultima copia dei filtri di
-- `fn_list_emittibili_lane` fuori dal database. Il test presidia sia i
-- contatori sia il difetto che la copia Python aveva: aggregava per
-- `gruppo_key` con `min()` / `bool_or()`, e `gruppo_key` per una riga con
-- documento sorgente NON contiene la commessa.
--
-- Fixture costruita dentro il test:
--   CA (stato NON emittibile) -> gruppo GA con sei righe, una per classe
--   CA + CB (stato emittibile) -> gruppo GB condiviso: e' il caso multi-commessa
--
-- Indice test (0..11):
--   0) Precondizioni (riferimenti minimi risolti, due stati contrapposti)
--   1) La funzione esiste
--   2) GA: i contatori per classe di stato
--   3) GA: il bound di competenza separa n_pronte da n_fuori_competenza
--   4) Gruppo sconosciuto: riga presente con n_righe = 0 e commessa NULL
--   5) La descrizione dello stato commessa arriva decodificata
--   6) ⚠️ GB multi-commessa: DUE righe, e la commessa bloccata resta distinguibile
--   7) Chiave con spazi: btrim la normalizza come fa la funzione della chiave
--   8) Input vuoto e NULL: zero righe, nessun errore
--   9) ⚠️ Il guard di riga rifiuta la riga senza tipo documento (il percorso)
--  10) ⚠️ Il CHECK e' VALIDATO e n_senza_tipo_doc non e' piu' fra le colonne
--  11) ⚠️ terne_pronte: la corsia del lavoro pronto, misurata e mai NULL
-- ------------------------------------------------------------

BEGIN;

-- ⚠️ Vincoli DIFFERITI: senza questa riga il test smetterebbe di verificarli.
--   Scattano al COMMIT, e qui il COMMIT non arriva mai (si chiude in ROLLBACK):
--   sarebbero saltati in silenzio, e il file sarebbe verde per sottrazione.
SET CONSTRAINTS ALL IMMEDIATE;

-- Contesto applicativo: il test gira come gira l'applicazione (ruolo OPERATORE
-- + RLS attiva). commesse e commesse_attivita hanno la RLS: senza veste la
-- fixture non vedrebbe nulla e le asserzioni passerebbero per sottrazione.
DO $ctx$ BEGIN PERFORM script.fn_pgtap_set_contesto_operatore(); END $ctx$;

SELECT plan(14);

-- ============================================================
-- 0) Riferimenti minimi
-- ============================================================
-- ⚠️ Niente LIMIT 1 senza ORDER BY. ⚠️ L'emittente si DERIVA dall'operatore:
--   le policy ef_whitelist lo pretendono in scrittura.
CREATE TEMP TABLE tmp_dg_refs AS
SELECT
  (SELECT ba.id FROM anagrafiche.billing_account ba
    WHERE ba.utility_id IS NOT NULL AND ba.istanza_utility_id IS NOT NULL
      AND ba.soggetto_ruolo_id IS NOT NULL ORDER BY ba.id LIMIT 1) AS billing_account_id,
  (SELECT ba.utility_id FROM anagrafiche.billing_account ba
    WHERE ba.utility_id IS NOT NULL AND ba.istanza_utility_id IS NOT NULL
      AND ba.soggetto_ruolo_id IS NOT NULL ORDER BY ba.id LIMIT 1) AS utility_id,
  (SELECT ba.istanza_utility_id FROM anagrafiche.billing_account ba
    WHERE ba.utility_id IS NOT NULL AND ba.istanza_utility_id IS NOT NULL
      AND ba.soggetto_ruolo_id IS NOT NULL ORDER BY ba.id LIMIT 1) AS istanza_utility_id,
  (SELECT a.id FROM catalogo.articoli a
    WHERE a.attivo IS TRUE AND a.is_composito = FALSE ORDER BY a.id LIMIT 1) AS articolo_id,
  (SELECT u.id FROM catalogo.unita_misura u WHERE u.attivo IS TRUE
    ORDER BY u.id LIMIT 1) AS uom_id,
  (SELECT t.id FROM config.tipi_doc_fiscale t WHERE t.attivo IS TRUE
    ORDER BY t.id LIMIT 1) AS tipo_doc_fiscale_id,
  (SELECT v.id FROM config.valute v ORDER BY v.id LIMIT 1) AS valuta_id,
  -- Due stati CONTRAPPOSTI: e' l'asse su cui il difetto della copia Python si
  -- vedeva (bool_or su piu' commesse). Scelti per flag, non per codice: la
  -- semantica sta in `emittibile`, non nel nome.
  (SELECT sc.id FROM vendite.stati_commessa sc
    WHERE sc.attivo IS TRUE AND sc.emittibile IS FALSE
      AND sc.codice_interno <> 'ANNULLATA'
    ORDER BY COALESCE(sc.ordine, 32767), sc.id LIMIT 1) AS stato_bloccato_id,
  (SELECT sc.id FROM vendite.stati_commessa sc
    WHERE sc.attivo IS TRUE AND sc.emittibile IS TRUE
    ORDER BY COALESCE(sc.ordine, 32767), sc.id LIMIT 1) AS stato_emittibile_id,
  script.fn_pgtap_emittente_sr_operatore()                          AS ef_sr,
  (SELECT s.id FROM config.sorgenti s
    WHERE s.codice_interno = 'PREVENTIVO' AND s.attivo IS TRUE
    ORDER BY s.id LIMIT 1) AS sorgente_tipo_id;

CREATE TEMP TABLE tmp_dg_uid AS
SELECT 'GA'::text AS slot, uuidv7()::text AS uid
UNION ALL SELECT 'GB', uuidv7()::text;

SELECT ok(
  (SELECT billing_account_id IS NOT NULL AND articolo_id IS NOT NULL
      AND uom_id IS NOT NULL AND tipo_doc_fiscale_id IS NOT NULL
      AND valuta_id IS NOT NULL AND ef_sr IS NOT NULL
      AND sorgente_tipo_id IS NOT NULL
      AND stato_bloccato_id IS NOT NULL AND stato_emittibile_id IS NOT NULL
      AND stato_bloccato_id <> stato_emittibile_id
     FROM tmp_dg_refs),
  '0. Precondizioni soddisfatte (due stati commessa contrapposti su emittibile)'
);

SELECT ok(
  (SELECT count(*) FROM pg_proc p JOIN pg_namespace n ON n.oid = p.pronamespace
    WHERE n.nspname = 'vendite'
      AND p.proname = 'fn_diagnostica_gruppi_fatturabili') = 1,
  '1. vendite.fn_diagnostica_gruppi_fatturabili esiste'
);

-- ============================================================
-- Fixture: due commesse, stato contrapposto
-- ============================================================
CREATE TEMP TABLE tmp_dg_commessa (slot text, commessa_id bigint);

-- rev 2026-10-24 (brief-modello-documento-vendita N-1): le commesse nascono
--   BOZZA (trigger della nascita) e si portano allo stato voluto con
--   dbops.fn_pgtap_porta_a_stato: CA subito (lo stato bloccato non pretende
--   righe), CB DOPO le sue righe (PRONTA_FATTURAZIONE pretende una riga
--   APPROVATA, fn_check_commessa_pronta_fatturazione).
WITH ins AS (
  INSERT INTO vendite.commesse (codice, billing_account_id, utility_id,
                                emittente_soggetto_ruolo_id)
  SELECT 'PGTAP-DG-CA-' || substr(md5(clock_timestamp()::text), 1, 8),
         r.billing_account_id, r.utility_id, r.ef_sr
    FROM tmp_dg_refs r
  RETURNING id)
INSERT INTO tmp_dg_commessa SELECT 'CA', id FROM ins;
SELECT dbops.fn_pgtap_porta_a_stato('vendite.commesse', c.commessa_id, sc.codice_interno)
  FROM tmp_dg_commessa c, tmp_dg_refs r
  JOIN vendite.stati_commessa sc ON sc.id = r.stato_bloccato_id
 WHERE c.slot = 'CA';

WITH ins AS (
  INSERT INTO vendite.commesse (codice, billing_account_id, utility_id,
                                emittente_soggetto_ruolo_id)
  SELECT 'PGTAP-DG-CB-' || substr(md5(clock_timestamp()::text), 1, 8),
         r.billing_account_id, r.utility_id, r.ef_sr
    FROM tmp_dg_refs r
  RETURNING id)
INSERT INTO tmp_dg_commessa SELECT 'CB', id FROM ins;

-- Helper: una riga di commessa, variando quello che al test serve variare.
-- ⚠️ Il gruppo si sceglie con lo `slot` dell'uid, mai ricostruendo la chiave.
CREATE FUNCTION pg_temp.mk_dg(
  p_commessa_slot text, p_uid_slot text, p_appr varchar, p_emiss varchar,
  p_comp date, p_con_tipo_doc boolean
) RETURNS bigint LANGUAGE sql AS $$
  INSERT INTO vendite.commesse_attivita (
    commessa_id, segment_key, articolo_id, istanza_utility_id, data_attivita,
    uom_id, quantita, competenza_mese, competenza_dal, competenza_al,
    tipo_doc_fiscale_id, valuta_id, prezzo_snapshot, pricing_mode,
    stato_approvazione, stato_emissione, sorgente_tipo_id, sorgente_uid)
  SELECT (SELECT commessa_id FROM tmp_dg_commessa WHERE slot = p_commessa_slot),
         'PGTAP-DG-' || p_uid_slot || '-' || substr(md5(clock_timestamp()::text), 1, 10),
         r.articolo_id, r.istanza_utility_id, p_comp, r.uom_id, 1,
         p_comp, date_trunc('month', p_comp)::date,
         (date_trunc('month', p_comp) + INTERVAL '1 month - 1 day')::date,
         CASE WHEN p_con_tipo_doc THEN r.tipo_doc_fiscale_id ELSE NULL END,
         r.valuta_id, 10.000000, 'FIXED',
         p_appr, p_emiss, r.sorgente_tipo_id,
         (SELECT uid FROM tmp_dg_uid WHERE slot = p_uid_slot)
    FROM tmp_dg_refs r
  RETURNING id;
$$;

-- GA, sei righe sulla commessa BLOCCATA: una per classe della fotografia.
SELECT pg_temp.mk_dg('CA', 'GA', 'APPROVATA', 'EMESSA',     DATE '2082-01-01', true);
SELECT pg_temp.mk_dg('CA', 'GA', 'APPROVATA', 'ANNULLATA',  DATE '2082-01-01', true);
SELECT pg_temp.mk_dg('CA', 'GA', 'RIFIUTATA', 'NON_EMESSA', DATE '2082-01-01', true);
SELECT pg_temp.mk_dg('CA', 'GA', 'BOZZA',     'NON_EMESSA', DATE '2082-01-01', true);
-- pronta entro il bound
SELECT pg_temp.mk_dg('CA', 'GA', 'APPROVATA', 'NON_EMESSA', DATE '2082-01-01', true);
-- pronta ma con competenza SUCCESSIVA al bound: e' la sola classe che dipende
-- dal parametro p_competenza_mese, ed e' il motivo per cui esiste.
SELECT pg_temp.mk_dg('CA', 'GA', 'APPROVATA', 'NON_EMESSA', DATE '2082-03-01', true);

-- GB, lo STESSO documento sorgente su DUE commesse di stato opposto.
SELECT pg_temp.mk_dg('CA', 'GB', 'APPROVATA', 'NON_EMESSA', DATE '2082-01-01', true);
SELECT pg_temp.mk_dg('CB', 'GB', 'APPROVATA', 'NON_EMESSA', DATE '2082-01-01', true);

-- CB ora ha la sua riga APPROVATA: passa allo stato emittibile (rev 2026-10-24).
SELECT dbops.fn_pgtap_porta_a_stato('vendite.commesse', c.commessa_id, sc.codice_interno)
  FROM tmp_dg_commessa c, tmp_dg_refs r
  JOIN vendite.stati_commessa sc ON sc.id = r.stato_emittibile_id
 WHERE c.slot = 'CB';

-- Le chiavi arrivano dalla sola fonte di verita': ricostruirle nel test
-- significherebbe verificare la copia invece dell'originale.
CREATE TEMP TABLE tmp_dg_key AS
SELECT DISTINCT u.slot,
       vendite.fn_build_gruppo_fatturabile_key(
         ca.sorgente_tipo_id, ca.sorgente_uid, ca.commessa_id) AS gruppo_key
  FROM tmp_dg_uid u
  JOIN vendite.commesse_attivita ca ON ca.sorgente_uid = u.uid;

-- La fotografia si calcola UNA volta: le asserzioni parlano della stessa.
CREATE TEMP TABLE tmp_dg_foto AS
SELECT * FROM vendite.fn_diagnostica_gruppi_fatturabili(
  ARRAY(SELECT k.gruppo_key FROM tmp_dg_key k ORDER BY k.slot)
    || ARRAY['PGTAP_GRUPPO_INESISTENTE:0000'],
  DATE '2082-01-01');

-- ============================================================
-- 2-3) I contatori
-- ============================================================
SELECT ok(
  (SELECT f.n_righe = 6
      AND f.n_emesse = 1
      AND f.n_annullate = 1
      AND f.n_rifiutate = 1
      AND f.n_non_approvate = 1
      AND f.commessa_emittibile IS FALSE
     FROM tmp_dg_foto f
    WHERE f.gruppo_key = (SELECT gruppo_key FROM tmp_dg_key WHERE slot = 'GA')),
  '2. GA: sei righe, una per classe (emessa, annullata, rifiutata, non approvata) su commessa bloccata'
);

SELECT ok(
  (SELECT f.n_pronte = 1 AND f.n_fuori_competenza = 1
     FROM tmp_dg_foto f
    WHERE f.gruppo_key = (SELECT gruppo_key FROM tmp_dg_key WHERE slot = 'GA')),
  '3. GA: il bound di competenza separa la riga pronta (2082-01) da quella futura (2082-03)'
);

-- ============================================================
-- 4) Gruppo sconosciuto: si dichiara ignoto, non sparisce
-- ============================================================
SELECT ok(
  (SELECT f.n_righe = 0 AND f.commessa_id IS NULL
      AND f.commessa_stato_codice_interno IS NULL
     FROM tmp_dg_foto f
    WHERE f.gruppo_key = 'PGTAP_GRUPPO_INESISTENTE:0000'),
  '4. Gruppo sconosciuto: riga presente con n_righe = 0 e commessa NULL (non sparisce dal risultato)'
);

-- ============================================================
-- 5) La decodifica di display arriva dal DB
-- ============================================================
SELECT ok(
  (SELECT f.commessa_stato_descrizione
          = (SELECT COALESCE(sc.descrizione, sc.codice)
               FROM vendite.stati_commessa sc, tmp_dg_refs r
              WHERE sc.id = r.stato_bloccato_id)
      AND f.commessa_stato_codice_interno
          = (SELECT sc.codice_interno FROM vendite.stati_commessa sc, tmp_dg_refs r
              WHERE sc.id = r.stato_bloccato_id)
     FROM tmp_dg_foto f
    WHERE f.gruppo_key = (SELECT gruppo_key FROM tmp_dg_key WHERE slot = 'GA')),
  '5. Lo stato commessa esce decodificato: codice interno per la logica, descrizione per il video'
);

-- ============================================================
-- 6) ⚠️ IL CASO CHE LA COPIA PYTHON COLLASSAVA.
--    Un gruppo con documento sorgente non contiene la commessa nella chiave.
--    Con `bool_or(commessa_emittibile)` su due commesse di stato opposto la
--    risposta sarebbe stata «emittibile», e la diagnosi avrebbe perso proprio
--    il motivo che deve raccontare. Alla grana (gruppo, commessa) non puo'
--    succedere.
-- ============================================================
SELECT ok(
  (SELECT count(*) = 2
      AND count(*) FILTER (WHERE f.commessa_emittibile IS FALSE) = 1
      AND count(*) FILTER (WHERE f.commessa_emittibile IS TRUE)  = 1
      AND bool_and(f.n_pronte = 1)
     FROM tmp_dg_foto f
    WHERE f.gruppo_key = (SELECT gruppo_key FROM tmp_dg_key WHERE slot = 'GB')),
  '6. GB su due commesse: DUE righe, e la commessa bloccata resta distinguibile da quella emittibile'
);

-- ============================================================
-- 7-8) Normalizzazione e input degeneri
-- ============================================================
SELECT ok(
  (SELECT f.n_righe = 6
     FROM vendite.fn_diagnostica_gruppi_fatturabili(
            ARRAY['  ' || (SELECT gruppo_key FROM tmp_dg_key WHERE slot = 'GA') || '  '],
            DATE '2082-01-01') f),
  '7. Chiave con spazi: btrim la normalizza (senza, filtrerebbe zero righe senza dirlo)'
);

SELECT ok(
  (SELECT count(*) FROM vendite.fn_diagnostica_gruppi_fatturabili(ARRAY[]::text[])) = 0
  AND (SELECT count(*) FROM vendite.fn_diagnostica_gruppi_fatturabili(NULL)) = 0,
  '8. Input vuoto o NULL: zero righe e nessun errore (e'' l''identita'', non un guasto)'
);

-- ============================================================
-- 9-10) ⚠️ IL CONTATORE CHE NON C'E' PIU', e perche'.
--    Una riga APPROVATA + NON_EMESSA senza tipo documento e' rifiutata da un
--    guard di riga E da un CHECK di tabella: non puo' esistere. Il contatore
--    `n_senza_tipo_doc` c'era comunque, perche' il CHECK era `NOT VALID` — le
--    righe preesistenti non erano mai state lette, quindi il ramo restava
--    «forse» vivo.
--    Il changeSet 20260815-30 ha validato il vincolo e il 20260815-31 ha tolto
--    il contatore: un ramo che sembra coperto e non lo e' vale meno di zero.
--    Si verifica dal PERCORSO — che il guard fermi la riga — non fabbricando
--    una riga che il database non ammette.
-- ============================================================
SELECT throws_ok(
  $$ SELECT pg_temp.mk_dg('CA', 'GA', 'APPROVATA', 'NON_EMESSA', DATE '2082-01-01', false) $$,
  'P0001', NULL,
  '9. Riga APPROVATA+NON_EMESSA senza tipo documento: il guard di riga la rifiuta (e'' il percorso che rende il contatore irraggiungibile)'
);

-- ⚠️ Il CHECK dev'essere VALIDATO, non solo presente: e'' la meta' che mancava.
--    Senza, il ramo tornerebbe «forse» vivo sulle righe vecchie e il contatore
--    non si sarebbe potuto togliere.
SELECT ok(
  (SELECT convalidated FROM pg_constraint
    WHERE conname = 'chk_commesse_attivita_tipo_doc_emittibile'
      AND conrelid = 'vendite.commesse_attivita'::regclass)
  AND NOT EXISTS (
    SELECT 1 FROM pg_proc p
    JOIN pg_namespace n ON n.oid = p.pronamespace
    WHERE n.nspname = 'vendite'
      AND p.proname = 'fn_diagnostica_gruppi_fatturabili'
      AND 'n_senza_tipo_doc' = ANY (p.proargnames)),
  '10. Il CHECK e'' VALIDATO e n_senza_tipo_doc non e'' piu'' fra le colonne: la garanzia vale su tutte le righe, il ramo morto e'' sparito'
);

-- ============================================================
-- 11) ⚠️ `terne_pronte` — la corsia del lavoro ancora pronto.
--    Risposta al §10.6: in un giro parziale con una terna FALLITA, i gruppi di
--    quella terna sono NON_SERVITO e la diagnosi di perimetro attribuirebbe
--    loro una causa sbagliata («verificare emittente e utility»). La corsia non
--    si prevede, si MISURA: sono le tre colonne su cui la lane raggruppa.
--    ⚠️ Due invarianti, e la seconda vale quanto la prima:
--      · `n_pronte > 0` -> la corsia c'e', ed e' quella della commessa/riga;
--      · `n_pronte = 0` -> `[]` e MAI `NULL`: «nessuna corsia» e «non
--        calcolato» devono restare distinguibili.
-- ============================================================
SELECT ok(
  -- GA ha una sola riga pronta entro il bound: una corsia sola, e coincide con
  -- (emittente della commessa, tipo doc della riga, utility della commessa).
  (SELECT f.n_pronte = 1
      AND jsonb_array_length(f.terne_pronte) = 1
      AND f.terne_pronte -> 0 = jsonb_build_object(
            'emittente_soggetto_ruolo_id', (SELECT ef_sr FROM tmp_dg_refs),
            'tipo_doc_fiscale_id',         (SELECT tipo_doc_fiscale_id FROM tmp_dg_refs),
            'utility_id',                  (SELECT utility_id FROM tmp_dg_refs))
     FROM tmp_dg_foto f
    WHERE f.gruppo_key = (SELECT gruppo_key FROM tmp_dg_key WHERE slot = 'GA'))
  AND
  -- Il gruppo sconosciuto non ha niente di pronto: array VUOTO, non NULL.
  (SELECT f.terne_pronte = '[]'::jsonb
     FROM tmp_dg_foto f
    WHERE f.gruppo_key = 'PGTAP_GRUPPO_INESISTENTE:0000')
  AND
  -- Invariante generale sulla fotografia: n_pronte e terne_pronte guardano lo
  -- stesso predicato, quindi non possono contraddirsi.
  (SELECT bool_and(
            f.terne_pronte IS NOT NULL
            AND (f.n_pronte = 0) = (jsonb_array_length(f.terne_pronte) = 0))
     FROM tmp_dg_foto f),
  '11. terne_pronte: la corsia delle righe pronte e'' misurata (non prevista), vuota e mai NULL quando non c''e'' nulla di pronto, e sempre coerente con n_pronte'
);

-- ============================================================
-- Addendum rev 2026-09-09 — la classe TRATTENUTA
-- ============================================================
-- ⭐ Un gruppo in piu', tenuto da un lotto IN GIOCO. Serve ai test 12 e 13.
-- ⛔ E' il caso che questa funzione contava fra i PRONTI: dal 20260909-25 la
--   lane non lo offriva piu', e la fotografia continuava a dire «era pronto».
--   Il backend ne ricavava «verificare emittente e utility della commessa» —
--   due cose giuste da controllare, e non una parola sull'unica che contava.
CREATE TEMP TABLE tmp_dg_trat (commessa_id bigint, gruppo_key text, lotto_id bigint);

DO $addendum$
DECLARE
    v_r    record;
    v_comm vendite.commesse.id%TYPE;
    v_lot  vendite.fatturazione_lotti.id%TYPE;
    v_mese vendite.commesse_attivita.competenza_mese%TYPE;
BEGIN
    SELECT * INTO v_r FROM tmp_dg_refs;
    v_mese := date_trunc('month', script.fn_data_operativa())::date;

    -- rev 2026-10-24: nasce BOZZA, passa allo stato emittibile dopo la riga.
    INSERT INTO vendite.commesse (codice, billing_account_id, utility_id,
                                  emittente_soggetto_ruolo_id)
    VALUES ('PGTAP-DG-TRAT-' || substr(md5(clock_timestamp()::text), 1, 6),
            v_r.billing_account_id, v_r.utility_id, v_r.ef_sr)
    RETURNING id INTO v_comm;

    INSERT INTO vendite.commesse_attivita (
        commessa_id, segment_key, articolo_id, istanza_utility_id, data_attivita,
        uom_id, quantita, competenza_mese, competenza_dal, competenza_al,
        tipo_doc_fiscale_id, valuta_id, prezzo_snapshot, pricing_mode,
        stato_approvazione, stato_emissione, sorgente_tipo_id, sorgente_uid)
    VALUES (v_comm, 'PGTAP-DG-TRAT-' || substr(md5(clock_timestamp()::text), 1, 12),
            v_r.articolo_id, v_r.istanza_utility_id, v_mese,
            v_r.uom_id, 1, v_mese, v_mese,
            (v_mese + INTERVAL '1 month - 1 day')::date,
            v_r.tipo_doc_fiscale_id, v_r.valuta_id, 10.000000, 'FIXED',
            'APPROVATA', 'NON_EMESSA', -- La riga NORMALE ha la sua sorgente (vincolo 20261012-27).
            (SELECT s.id FROM config.sorgenti s WHERE s.codice_interno = 'COMMESSA'), v_comm::text);

    PERFORM dbops.fn_pgtap_porta_a_stato('vendite.commesse', v_comm,
        (SELECT sc.codice_interno FROM vendite.stati_commessa sc WHERE sc.id = v_r.stato_emittibile_id));

    INSERT INTO vendite.fatturazione_lotti
        (codice, competenza_mese, tipo_doc_fiscale_id,
         emittente_soggetto_ruolo_id, stato_doc_fiscale_id)
    VALUES ('PGTAP-DG-LOTTO', v_mese, v_r.tipo_doc_fiscale_id, v_r.ef_sr,
            (SELECT id FROM config.stati_doc_fiscale WHERE codice_interno = 'DRAFT'))
    RETURNING id INTO v_lot;

    INSERT INTO tmp_dg_trat
    VALUES (v_comm, vendite.fn_build_gruppo_fatturabile_key(
                (SELECT s.id FROM config.sorgenti s WHERE s.codice_interno = 'COMMESSA'), v_comm::text, v_comm), v_lot);

    INSERT INTO vendite.fatturazione_lotti_esiti
        (lotto_id, gruppo_key, stato_esecuzione, errore_codice, errore_messaggio)
    SELECT v_lot, t.gruppo_key, 'ERRORE', 'E_PULL_COMMESSA', 'rotto per la prova'
      FROM tmp_dg_trat t;
END;
$addendum$;

CREATE TEMP TABLE tmp_dg_foto_trat AS
  SELECT d.* FROM vendite.fn_diagnostica_gruppi_fatturabili(
                     (SELECT array_agg(gruppo_key) FROM tmp_dg_trat),
                     date_trunc('month', script.fn_data_operativa())::date) d;

-- ============================================================
-- 12) ⭐ La riga TRATTENUTA esce dai pronti ed entra in n_trattenute
-- ============================================================
-- ⛔ E' IL VERSO DELLA CORREZIONE, e va letto insieme al test 3: li' una riga
--   pronta e' contata pronta, qui una trattenuta NON lo e' piu'. Con il solo
--   12 passerebbe anche una funzione che non conta mai niente come pronto.
SELECT results_eq(
  $$ SELECT n_righe, n_pronte, n_trattenute FROM tmp_dg_foto_trat $$,
  $$ VALUES (1::bigint, 0::bigint, 1::bigint) $$,
  '12. una riga trattenuta da un lotto in gioco ESCE da n_pronte ed entra in n_trattenute'
);

-- ============================================================
-- 13) ⭐ E il lotto si NOMINA: «trattenuto» senza dire da cosa non e' azionabile
-- ============================================================
-- ⚠️ `[]` e mai NULL, come terne_pronte: «nessun lotto» e «non calcolato»
--   devono restare distinguibili. Il gruppo GA non e' trattenuto da niente, e
--   la sua colonna deve essere un array VUOTO.
SELECT results_eq(
  $$ SELECT (SELECT (lotti_trattenenti -> 0 ->> 'codice') FROM tmp_dg_foto_trat),
            (SELECT jsonb_array_length(lotti_trattenenti) FROM tmp_dg_foto_trat),
            (SELECT jsonb_array_length(f.lotti_trattenenti) FROM tmp_dg_foto f
              WHERE f.gruppo_key = (SELECT gruppo_key FROM tmp_dg_key WHERE slot = 'GA')) $$,
  $$ VALUES ('PGTAP-DG-LOTTO', 1, 0) $$,
  '13. lotti_trattenenti NOMINA il lotto che trattiene, ed e'' un array vuoto (mai NULL) su un gruppo libero'
);

SELECT * FROM finish();
ROLLBACK;
