-- ------------------------------------------------------------
-- SPDX-License-Identifier: GPL-3.0-or-later
-- pgTAP test per Zero ERP
-- Test: proiezione stato di dominio — D1 seed + guard is_verdetto +
--       resolver vendite + union script.vw_stato_sorgente +
--       pratiche.fn_stato_sorgente (brief-db-proiezione-stato-dominio)
-- ------------------------------------------------------------
-- Indice test (1..31):
-- 1)  Seed D1: DRAFT     -> fase APERTO,    esito NULL,     terminale false
-- 2)  Seed D1: EMESSO    -> fase IN_ATTESA, esito NULL,     terminale false
-- 3)  Seed D1: ACCETTATO -> fase IN_CORSO,  esito POSITIVO, terminale false
-- 4)  Seed D1: ANNULLATO -> fase CHIUSO,    esito NEGATIVO, terminale true
-- 5)  Invariante mappa: nessuno stato terminale fuori da fase CHIUSO
-- 6)  is_verdetto: i 4 esiti strutturali sono verdetti
-- 7)  Guard verdetto: esito inesistente -> errore parlante
-- 8)  Guard verdetto: esito di instradamento (MERCE_PRESENTE) -> errore
--     (skip se il dominio non ha ancora seedato l'esito)
-- 9)  vw_stato_sorgente: riga per il preventivo EMESSO, risolto=true
-- 10) vw_stato_sorgente: al piu' una riga per (tipo, uid)
-- 11) fn_stato_sorgente EMESSO    -> (true, EMESSO, 'Emesso', IN_ATTESA, NULL, false)
-- 12) fn_stato_sorgente ACCETTATO -> (IN_CORSO, POSITIVO)
-- 13) fn_stato_sorgente ANNULLATO -> (CHIUSO, NEGATIVO, terminale true)
-- 14) fn_stato_sorgente tipo senza resolver -> UNKNOWN (risolto=false) senza errore
--     (skip se esiste solo il tipo PREVENTIVO)
-- 15) fn_stato_sorgente uid inesistente su tipo PREVENTIVO -> UNKNOWN (risolto=false)
-- 16) fn_stato_sorgente guard: sorgente_tipo_id NULL -> errore parametri
-- 17) fn_stato_sorgente guard: sorgente_tipo_id 0 -> errore parametri
-- --- Roll-out offerte/ordini/contratti (brief-db-...-rollout) ---
-- 18) Seed D1 OFFERTA: mappa completa (fase/esito/terminale per stato)
-- 19) Seed D1 ORDINE: mappa completa
-- 20) Seed D1 CONTRATTO: mappa completa
-- 21) Invariante terminale=>CHIUSO su offerte+ordini+contratti
-- 22) Guard verdetto attivo su config.stati_doc_offerte
-- 23) Guard verdetto attivo su config.stati_doc_ordini
-- 24) Guard verdetto attivo su config.stati_doc_contratti
-- --- vw_pratica_doc_sorgente: regola d'ancora R1 (§5b) ---
-- 25) Ancora A: pratica mono-doc (ROOT preventivo EMESSO) -> proietta EMESSO
-- 26) Ancora B: ROOT terminale (ANNULLATO) + COLLEGATO vivo (ACCETTATO) ->
--     proietta ACCETTATO (vivo batte terminale)
-- 27) Ancora C [REGRESSIONE prev->commessa]: ROOT risolto (EMESSO) + COLLEGATO
--     non-risolto (fake) -> proietta EMESSO (risolto batte non-risolto)
-- 28) Ancora D: pratica con solo link non-risolto -> risolto=false, stato NULL
-- --- Chiave nel suo tipo (rev 2026-10-05, 20261005-23) ---
-- 29) fn_stato_sorgente: uid MAIUSCOLO del preventivo EMESSO -> UNKNOWN
--     (si accetta solo la forma canonica, come il confronto testuale di prima)
-- 30) fn_stato_sorgente: chiave malformata -> UNKNOWN senza errore (niente 22P02)
-- 31) fn_stato_sorgente: uid di un preventivo col tipo ORDINE_VENDITA (chiave id)
--     -> UNKNOWN
-- rev 2026-10-24 (brief-modello-documento-vendita Q-4): la commessa dei link
--   «non risolti» si costruisce con dbops.fn_pgtap_crea_commessa (prima era «la
--   prima commessa del database») e il soggetto delle pratiche e' il cliente
--   costruito (prima «il primo soggetto per id»): su un database ricostruito
--   da zero nessuno dei due c'e'.
-- rev 2026-10-24 (brief-modello-documento-vendita N-1): i preventivi nascono in
--   bozza e si portano avanti con dbops.fn_pgtap_porta_a_stato (prima nascevano
--   gia' EMESSO/ACCETTATO/ANNULLATO).
-- ------------------------------------------------------------

BEGIN;

-- ⚠️ Vincoli DIFFERITI: senza questa riga il test smetterebbe di verificarli.
--   Un trigger DEFERRABLE INITIALLY DEFERRED scatta al COMMIT, e qui il COMMIT
--   non arriva mai (si chiude in ROLLBACK): sarebbero saltati in silenzio, e il
--   file sarebbe verde per sottrazione. IMMEDIATE li riporta a scattare a fine
--   di ogni istruzione. In testa e non in coda: in coda scatterebbero dopo il
--   cleanup, su righe ormai cancellate.
--   Brief: brief-db-pgtap-runner-rls-baseline §19.
SET CONSTRAINTS ALL IMMEDIATE;

-- Contesto applicativo: questo test gira come gira l'applicazione (ruolo
-- OPERATORE + RLS attiva), non come owner. Senza, con FORCE ROW LEVEL
-- SECURITY disattivo l'owner salta la RLS e il test non la esercita mai.
-- Brief: brief-db-pgtap-runner-rls-baseline §8.
DO $ctx$ BEGIN PERFORM script.fn_pgtap_set_contesto_operatore(); END $ctx$;

SELECT plan(31);

-- ============================================================
-- Riferimenti minimi per creare preventivi in pgTAP
-- (pattern test-fn-available-actions-preventivo-v1)
-- ============================================================
-- ⚠️ rev 2026-10-08 (brief-db-istanza-nasce-col-ba, R-2): il preventivo ha
--   sempre il suo billing account, quello della sua coppia (istanza, utility).
--   Fino a quel giorno la coppia si PESCAVA dal primo BA del database e il
--   preventivo nasceva senza BA; ora il BA va scritto, e il guard
--   dell'emittente pretende che sia dell'emittente del documento — cioe' di
--   chi agisce. Il cliente si COSTRUISCE: il builder lega il BA all'emittente
--   dell'operatore in sessione. ⛔ Si legge in un'istruzione SEPARATA.
CREATE TEMP TABLE tmp_cli_pss AS
SELECT * FROM dbops.fn_pgtap_crea_cliente_ba('proiezione stato sorgente');

CREATE TEMP TABLE tmp_refs_pss AS
SELECT
  (SELECT billing_account_id FROM tmp_cli_pss) AS billing_account_id,
  (SELECT istanza_utility_id FROM tmp_cli_pss) AS istanza_utility_id,
  (SELECT utility_id FROM tmp_cli_pss) AS utility_id,
  (SELECT v.id
     FROM config.valute v
    ORDER BY v.id LIMIT 1
  ) AS valuta_id,
  -- ⚠️ L'emittente si DERIVA da chi agisce, non si pesca: da quando le viste
  --   vw_stato_sorgente_* sono security_invoker (20260821-08/-09) le policy
  --   ef_whitelist si applicano anche in lettura, e un documento intestato a un
  --   emittente diverso da quello dell'operatore sarebbe invisibile alla vista.
  --   Oggi i due valori coincidono per caso — un solo emittente ha documenti —
  --   e proprio per questo il test passava: coincidenza, non costruzione.
  script.fn_pgtap_emittente_operatore() AS emittente_fiscale_id,
  (SELECT s.id
     FROM config.sorgenti s
    WHERE s.codice_interno = 'PREVENTIVO' AND s.attivo IS TRUE
    LIMIT 1
  ) AS sorgente_tipo_id,
  (SELECT sd.id FROM config.stati_doc_preventivi sd
    WHERE sd.codice_interno = 'EMESSO' LIMIT 1)    AS stato_emesso_id,
  (SELECT sd.id FROM config.stati_doc_preventivi sd
    WHERE sd.codice_interno = 'ACCETTATO' LIMIT 1) AS stato_accettato_id,
  (SELECT sd.id FROM config.stati_doc_preventivi sd
    WHERE sd.codice_interno = 'ANNULLATO' LIMIT 1) AS stato_annullato_id;

-- Tre preventivi fixture: EMESSO / ACCETTATO / ANNULLATO
-- ⚠️ rev 2026-10-24 (brief-modello-documento-vendita N-1): nascono in bozza
--   (lo stato non si scrive: lo mette il trigger della nascita); lo stato
--   VOLUTO si legge dal suffisso del numero e si raggiunge subito sotto con
--   dbops.fn_pgtap_porta_a_stato, per la matrice e sotto i guard veri (senza
--   righe i guard di EMESSO/ACCETTATO/ANNULLATO non trovano motivi).
CREATE TEMP TABLE tmp_prev_pss AS
WITH ins AS (
  INSERT INTO vendite.preventivi (
    numero, rev, billing_account_id, istanza_utility_id, utility_id,
    validita_dal, validita_al, valuta_id,
    data, fatturazione_immediata,
    storicizza, meta, emittente_fiscale_id
  )
  SELECT
    'PGTAP-PSS-' || x.suffisso || '-' || substr(md5(clock_timestamp()::text || x.suffisso), 1, 8),
    0,
    r.billing_account_id, r.istanza_utility_id, r.utility_id,
    DATE '2026-07-01', DATE '2026-07-31', r.valuta_id,
    DATE '2026-07-01', false,
    false, '{"test_scope":"pgtap_proiezione_stato_sorgente"}'::jsonb,
    r.emittente_fiscale_id
  FROM tmp_refs_pss r
  CROSS JOIN (
    SELECT 'EMESSO' AS suffisso
    UNION ALL
    SELECT 'ACCETT'
    UNION ALL
    SELECT 'ANNULL'
  ) x
  RETURNING id, uid, numero
)
SELECT
  i.id,
  (i.uid)::text AS uid,
  CASE split_part(i.numero, '-', 3)
    WHEN 'EMESSO' THEN 'EMESSO'
    WHEN 'ACCETT' THEN 'ACCETTATO'
    WHEN 'ANNULL' THEN 'ANNULLATO'
  END::text AS stato_codice_interno
FROM ins i;

DO $porta$
DECLARE
  r record;
BEGIN
  FOR r IN SELECT p.id, p.stato_codice_interno FROM tmp_prev_pss p ORDER BY p.id LOOP
    PERFORM dbops.fn_pgtap_porta_a_stato('vendite.preventivi', r.id, r.stato_codice_interno);
  END LOOP;
END
$porta$;

-- ============================================================
-- 1-4) Seed D1: la mappa dichiarata dal dominio (criteri §6)
-- ============================================================
SELECT results_eq(
  $$SELECT fase, esito, terminale FROM config.stati_doc_preventivi WHERE codice_interno = 'DRAFT'$$,
  $$VALUES ('APERTO'::varchar, NULL::varchar, false)$$,
  'Seed D1: DRAFT -> APERTO / NULL / non terminale'
);

SELECT results_eq(
  $$SELECT fase, esito, terminale FROM config.stati_doc_preventivi WHERE codice_interno = 'EMESSO'$$,
  $$VALUES ('IN_ATTESA'::varchar, NULL::varchar, false)$$,
  'Seed D1: EMESSO -> IN_ATTESA / NULL / non terminale'
);

SELECT results_eq(
  $$SELECT fase, esito, terminale FROM config.stati_doc_preventivi WHERE codice_interno = 'ACCETTATO'$$,
  $$VALUES ('IN_CORSO'::varchar, 'POSITIVO'::varchar, false)$$,
  'Seed D1: ACCETTATO -> IN_CORSO / POSITIVO / non terminale'
);

SELECT results_eq(
  $$SELECT fase, esito, terminale FROM config.stati_doc_preventivi WHERE codice_interno = 'ANNULLATO'$$,
  $$VALUES ('CHIUSO'::varchar, 'NEGATIVO'::varchar, true)$$,
  'Seed D1: ANNULLATO -> CHIUSO / NEGATIVO / terminale'
);

-- ============================================================
-- 5) Invariante mappa universale: terminale => fase CHIUSO
-- ============================================================
SELECT is(
  (SELECT COUNT(*)::int FROM config.stati_doc_preventivi
    WHERE terminale AND fase <> 'CHIUSO'),
  0,
  'Invariante: nessuno stato terminale fuori da fase CHIUSO'
);

-- ============================================================
-- 6) is_verdetto sui 4 esiti strutturali
-- ============================================================
SELECT is(
  (SELECT COUNT(*)::int FROM config.esiti_flussi_pratiche
    WHERE is_verdetto
      AND codice_interno IN ('POSITIVO', 'NEGATIVO', 'PARZIALE', 'NON_APPLICABILE')),
  4,
  'is_verdetto: i 4 esiti strutturali di motore sono verdetti'
);

-- ============================================================
-- 7-8) Guard verdetto sulla proiezione esito
-- ============================================================
SELECT throws_like(
  $$UPDATE config.stati_doc_preventivi
       SET esito = 'ESITO_INESISTENTE_PGTAP'
     WHERE codice_interno = 'ACCETTATO'$$,
  '%verdetto%',
  'Guard verdetto: esito inesistente bloccato con errore parlante'
);

SELECT CASE
  WHEN EXISTS (SELECT 1 FROM config.esiti_flussi_pratiche
                WHERE codice_interno = 'MERCE_PRESENTE')
  THEN throws_like(
    $$UPDATE config.stati_doc_preventivi
         SET esito = 'MERCE_PRESENTE'
       WHERE codice_interno = 'ACCETTATO'$$,
    '%verdetto%',
    'Guard verdetto: esito di instradamento (MERCE_PRESENTE) bloccato'
  )
  ELSE skip('MERCE_PRESENTE non seedato in questo DB', 1)
END;

-- ============================================================
-- 9-10) Vista union script.vw_stato_sorgente
-- ============================================================
SELECT ok(
  EXISTS (
    SELECT 1
      FROM script.vw_stato_sorgente v
     WHERE v.sorgente_tipo_id = (SELECT sorgente_tipo_id FROM tmp_refs_pss)
       AND v.sorgente_uid = (SELECT uid FROM tmp_prev_pss WHERE stato_codice_interno = 'EMESSO')
       AND v.risolto
       AND v.fase = 'IN_ATTESA'
  ),
  'vw_stato_sorgente: il preventivo EMESSO proietta risolto=true / IN_ATTESA'
);

SELECT is(
  (SELECT COUNT(*)::int
     FROM script.vw_stato_sorgente v
    WHERE v.sorgente_tipo_id = (SELECT sorgente_tipo_id FROM tmp_refs_pss)
      AND v.sorgente_uid = (SELECT uid FROM tmp_prev_pss WHERE stato_codice_interno = 'EMESSO')),
  1,
  'vw_stato_sorgente: al piu'' una riga per (sorgente_tipo_id, sorgente_uid)'
);

-- ============================================================
-- 11-13) fn_stato_sorgente: descrittore per stato (criteri §6)
-- ============================================================
SELECT results_eq(
  $$SELECT risolto, stato_codice_interno, stato_descrizione, fase, esito, terminale
      FROM pratiche.fn_stato_sorgente(
             (SELECT sorgente_tipo_id FROM tmp_refs_pss),
             (SELECT uid FROM tmp_prev_pss WHERE stato_codice_interno = 'EMESSO'))$$,
  $$VALUES (true, 'EMESSO'::text, 'Emesso'::text, 'IN_ATTESA'::text, NULL::text, false)$$,
  'fn_stato_sorgente EMESSO: risolto / IN_ATTESA / esito NULL / non terminale / descrizione Emesso'
);

SELECT results_eq(
  $$SELECT risolto, fase, esito
      FROM pratiche.fn_stato_sorgente(
             (SELECT sorgente_tipo_id FROM tmp_refs_pss),
             (SELECT uid FROM tmp_prev_pss WHERE stato_codice_interno = 'ACCETTATO'))$$,
  $$VALUES (true, 'IN_CORSO'::text, 'POSITIVO'::text)$$,
  'fn_stato_sorgente ACCETTATO: IN_CORSO / POSITIVO'
);

SELECT results_eq(
  $$SELECT risolto, fase, esito, terminale
      FROM pratiche.fn_stato_sorgente(
             (SELECT sorgente_tipo_id FROM tmp_refs_pss),
             (SELECT uid FROM tmp_prev_pss WHERE stato_codice_interno = 'ANNULLATO'))$$,
  $$VALUES (true, 'CHIUSO'::text, 'NEGATIVO'::text, true)$$,
  'fn_stato_sorgente ANNULLATO: CHIUSO / NEGATIVO / terminale'
);

-- ============================================================
-- 14-15) Degrado con grazia: UNKNOWN senza errore
-- ============================================================
SELECT CASE
  WHEN EXISTS (SELECT 1 FROM config.sorgenti
                WHERE codice_interno <> 'PREVENTIVO' AND attivo IS TRUE)
  THEN results_eq(
    $$SELECT risolto, stato_codice_interno, stato_descrizione, fase, esito, terminale
        FROM pratiche.fn_stato_sorgente(
               (SELECT id FROM config.sorgenti
                 WHERE codice_interno <> 'PREVENTIVO' AND attivo IS TRUE
                 ORDER BY id LIMIT 1),
               (SELECT uid FROM tmp_prev_pss WHERE stato_codice_interno = 'EMESSO'))$$,
    $$VALUES (false, 'UNKNOWN'::text, 'n/d'::text, 'APERTO'::text, NULL::text, false)$$,
    'fn_stato_sorgente: tipo senza resolver -> UNKNOWN (risolto=false) senza errore'
  )
  ELSE skip('nessun tipo sorgente diverso da PREVENTIVO nel DB', 1)
END;

SELECT results_eq(
  $$SELECT risolto, stato_codice_interno
      FROM pratiche.fn_stato_sorgente(
             (SELECT sorgente_tipo_id FROM tmp_refs_pss),
             (uuidv7())::text)$$,
  $$VALUES (false, 'UNKNOWN'::text)$$,
  'fn_stato_sorgente: uid inesistente -> UNKNOWN (risolto=false) senza errore'
);

-- ============================================================
-- 16-17) Guard parametri
-- ============================================================
SELECT throws_like(
  $$SELECT * FROM pratiche.fn_stato_sorgente(NULL::bigint, 'abc')$$,
  '%stato sorgente non validi%',
  'fn_stato_sorgente: sorgente_tipo_id NULL -> E_STATO_SORGENTE_PARAM_INVALIDO'
);

SELECT throws_like(
  $$SELECT * FROM pratiche.fn_stato_sorgente(0::bigint, 'abc')$$,
  '%stato sorgente non validi%',
  'fn_stato_sorgente: sorgente_tipo_id 0 -> E_STATO_SORGENTE_PARAM_INVALIDO'
);

-- ============================================================
-- 18-20) Seed D1 dei 3 domini del roll-out: mappa completa ordinata
--        (ORDER BY ordine per confronto deterministico)
-- ============================================================
SELECT results_eq(
  $$SELECT fase, esito, terminale FROM config.stati_doc_offerte ORDER BY ordine$$,
  $$VALUES ('APERTO'::varchar,    NULL::varchar,       false),
          ('IN_ATTESA'::varchar, NULL::varchar,       false),
          ('IN_CORSO'::varchar,  'POSITIVO'::varchar, false),
          ('CHIUSO'::varchar,    'NEGATIVO'::varchar, true),
          ('CHIUSO'::varchar,    'NEGATIVO'::varchar, true),
          ('CHIUSO'::varchar,    'NEGATIVO'::varchar, true)$$,
  '18) Seed D1 OFFERTA: BOZZA/EMESSA/ACCETTATA/RIFIUTATA/SUPERATA/ANNULLATA mappati'
);

-- rev 2026-07-27 (bonifica): aggiunto PARZIALMENTE_EVASO in 3a posizione.
-- Lo stato e' entrato nel seed DOPO la scrittura di questo test e, poiche' il
-- confronto e' posizionale (ORDER BY ordine), aveva sfalsato tutte le righe
-- successive: il test segnalava EVASO come sbagliato quando il seed era giusto.
-- ⚠️ Causa diversa dal guard sorgente polimorfa: era mascherata dal fallimento
-- del fixture, che abortiva prima di arrivare qui.
SELECT results_eq(
  $$SELECT fase, esito, terminale FROM config.stati_doc_ordini ORDER BY ordine$$,
  $$VALUES ('APERTO'::varchar,   NULL::varchar,       false),
          ('IN_CORSO'::varchar, NULL::varchar,       false),
          ('IN_CORSO'::varchar, NULL::varchar,       false),
          ('CHIUSO'::varchar,   'POSITIVO'::varchar, true),
          ('IN_CORSO'::varchar, NULL::varchar,       false),
          ('IN_CORSO'::varchar, NULL::varchar,       false),
          ('IN_CORSO'::varchar, NULL::varchar,       false),
          ('CHIUSO'::varchar,   'NEGATIVO'::varchar, true),
          ('CHIUSO'::varchar,   'POSITIVO'::varchar, true)$$,
  '19) Seed D1 ORDINE: DRAFT/CONFERMATO/PARZIALMENTE_EVASO/EVASO/ALLOCATO/SPEDITO/CONSEGNATO/ANNULLATO/FATTURATO mappati'
);

SELECT results_eq(
  $$SELECT fase, esito, terminale FROM config.stati_doc_contratti ORDER BY ordine$$,
  $$VALUES ('APERTO'::varchar,   NULL::varchar,       false),
          ('IN_CORSO'::varchar, NULL::varchar,       false),
          ('CHIUSO'::varchar,   'POSITIVO'::varchar, true),
          ('CHIUSO'::varchar,   'NEGATIVO'::varchar, true)$$,
  '20) Seed D1 CONTRATTO: DRAFT/ATTIVO/CESSATO/ANNULLATO mappati'
);

-- ============================================================
-- 21) Invariante universale terminale => fase CHIUSO sui 3 domini
-- ============================================================
SELECT is(
  (SELECT COUNT(*)::int FROM (
      SELECT 1 FROM config.stati_doc_offerte   WHERE terminale AND fase <> 'CHIUSO'
      UNION ALL
      SELECT 1 FROM config.stati_doc_ordini    WHERE terminale AND fase <> 'CHIUSO'
      UNION ALL
      SELECT 1 FROM config.stati_doc_contratti WHERE terminale AND fase <> 'CHIUSO'
   ) t),
  0,
  '21) Invariante: nessuno stato terminale fuori da CHIUSO (offerte+ordini+contratti)'
);

-- ============================================================
-- 22-24) Guard verdetto agganciato ai 3 domini (esito non-verdetto -> errore)
-- ============================================================
SELECT throws_like(
  $$UPDATE config.stati_doc_offerte
       SET esito = 'ESITO_INESISTENTE_PGTAP'
     WHERE codice_interno = 'ACCETTATA'$$,
  '%verdetto%',
  '22) Guard verdetto attivo su stati_doc_offerte'
);

SELECT throws_like(
  $$UPDATE config.stati_doc_ordini
       SET esito = 'ESITO_INESISTENTE_PGTAP'
     WHERE codice_interno = 'EVASO'$$,
  '%verdetto%',
  '23) Guard verdetto attivo su stati_doc_ordini'
);

SELECT throws_like(
  $$UPDATE config.stati_doc_contratti
       SET esito = 'ESITO_INESISTENTE_PGTAP'
     WHERE codice_interno = 'CESSATO'$$,
  '%verdetto%',
  '24) Guard verdetto attivo su stati_doc_contratti'
);

-- ============================================================
-- Fixture per vw_pratica_doc_sorgente (regola d'ancora R1, §5b).
-- Riusa i preventivi tmp_prev_pss (EMESSO=vivo, ACCETTATO=vivo, ANNULLATO=
-- terminale). I link non-risolti usano un uid fittizio (nessun documento ->
-- nessuna riga in vw_stato_sorgente -> risolto=false). flusso_id NULL: il guard
-- coerenza-flusso scatta solo se valorizzato, e la mappa vw_pratica_doc_sorgente
-- ignora flusso_id (considera tutti i link della pratica).
-- ============================================================
-- rev 2026-10-24 (Q-4): la commessa si COSTRUISCE, sul cliente della fixture
--   e nell'azienda di chi agisce (la madre vendite.fn_get_or_create_commessa).
--   ⛔ Si legge in un'istruzione SEPARATA.
CREATE TEMP TABLE tmp_anc_commessa AS
SELECT * FROM dbops.fn_pgtap_crea_commessa(
  'PSS', NULL, (SELECT billing_account_id FROM tmp_cli_pss));

CREATE TEMP TABLE tmp_anc_refs AS
SELECT
  -- ⚠️ L'emittente si DERIVA da chi agisce, non si pesca: da quando le viste
  --   vw_stato_sorgente_* sono security_invoker (20260821-08/-09) le policy
  --   ef_whitelist si applicano anche in lettura, e un documento intestato a un
  --   emittente diverso da quello dell'operatore sarebbe invisibile alla vista.
  --   Oggi i due valori coincidono per caso — un solo emittente ha documenti —
  --   e proprio per questo il test passava: coincidenza, non costruzione.
  script.fn_pgtap_emittente_operatore() AS emittente_id,
  -- rev 2026-10-24 (Q-4): il cliente costruito, non «il primo soggetto».
  (SELECT soggetto_id FROM tmp_cli_pss)                                        AS soggetto_id,
  (SELECT id FROM config.stati_pratiche WHERE codice_interno = 'APERTA')       AS st_aperta,
  (SELECT id FROM config.priorita_pratiche WHERE codice_interno = 'NORMALE')   AS priorita_id,
  (SELECT id FROM config.sorgenti WHERE codice_interno = 'PREVENTIVO')         AS src_preventivo,
  -- rev 2026-07-27 (bonifica): per i casi "non risolto" serviva una chiave che
  -- il guard sorgente polimorfa accetti ma che vw_stato_sorgente non sappia
  -- risolvere. E' esattamente la COMMESSA: chiave valida (key_selector='id',
  -- riga esistente in vendite.commesse) ma la vista NON ha il ramo commessa
  -- (reperto §5 di brief-db-guard-sorgente-polimorfa: le 19 righe COMMESSA di
  -- pratiche_sorgenti sono a chiave GIUSTA e non risolvono per questo motivo).
  -- Prima si usavano stringhe inventate 'FAKE-UNRESOLVED-*', illegali dal
  -- guard del 2026-07-18 — e il commento diceva gia' "mima la commessa":
  -- ora la mima davvero, invece di falsificarla.
  (SELECT id FROM config.sorgenti WHERE codice_interno = 'COMMESSA')           AS src_commessa,
  -- rev 2026-10-24 (Q-4): la commessa costruita (key_selector 'id'), non
  --   «la prima commessa del database».
  (SELECT commessa_id::text FROM tmp_anc_commessa)                             AS commessa_uid_reale;

CREATE TEMP TABLE tmp_anc_tp AS
WITH ins AS (
  INSERT INTO pratiche.tipi_prestazione (codice, codice_interno, descrizione, attivo)
  VALUES ('TEST_PSS_ANC', 'TEST_PSS_ANC', 'Tipo test proiezione ancora', true)
  ON CONFLICT (codice_interno) DO UPDATE SET descrizione = EXCLUDED.descrizione
  RETURNING id
)
SELECT id AS tp_id FROM ins;

CREATE TEMP TABLE tmp_anc_pa AS
WITH ins AS (
  INSERT INTO pratiche.pratiche (emittente_fiscale_id, tipo_prestazione_id, soggetto_id, stato_id, priorita_id)
  VALUES ((SELECT emittente_id FROM tmp_anc_refs), (SELECT tp_id FROM tmp_anc_tp),
          (SELECT soggetto_id FROM tmp_anc_refs), (SELECT st_aperta FROM tmp_anc_refs),
          (SELECT priorita_id FROM tmp_anc_refs))
  RETURNING id
) SELECT id AS pratica_id FROM ins;

CREATE TEMP TABLE tmp_anc_pb AS
WITH ins AS (
  INSERT INTO pratiche.pratiche (emittente_fiscale_id, tipo_prestazione_id, soggetto_id, stato_id, priorita_id)
  VALUES ((SELECT emittente_id FROM tmp_anc_refs), (SELECT tp_id FROM tmp_anc_tp),
          (SELECT soggetto_id FROM tmp_anc_refs), (SELECT st_aperta FROM tmp_anc_refs),
          (SELECT priorita_id FROM tmp_anc_refs))
  RETURNING id
) SELECT id AS pratica_id FROM ins;

CREATE TEMP TABLE tmp_anc_pc AS
WITH ins AS (
  INSERT INTO pratiche.pratiche (emittente_fiscale_id, tipo_prestazione_id, soggetto_id, stato_id, priorita_id)
  VALUES ((SELECT emittente_id FROM tmp_anc_refs), (SELECT tp_id FROM tmp_anc_tp),
          (SELECT soggetto_id FROM tmp_anc_refs), (SELECT st_aperta FROM tmp_anc_refs),
          (SELECT priorita_id FROM tmp_anc_refs))
  RETURNING id
) SELECT id AS pratica_id FROM ins;

CREATE TEMP TABLE tmp_anc_pd AS
WITH ins AS (
  INSERT INTO pratiche.pratiche (emittente_fiscale_id, tipo_prestazione_id, soggetto_id, stato_id, priorita_id)
  VALUES ((SELECT emittente_id FROM tmp_anc_refs), (SELECT tp_id FROM tmp_anc_tp),
          (SELECT soggetto_id FROM tmp_anc_refs), (SELECT st_aperta FROM tmp_anc_refs),
          (SELECT priorita_id FROM tmp_anc_refs))
  RETURNING id
) SELECT id AS pratica_id FROM ins;

INSERT INTO pratiche.pratiche_sorgenti (pratica_id, sorgente_tipo_id, sorgente_uid, ruolo_link, flusso_id)
VALUES
  -- A) mono ROOT EMESSO (vivo)
  ((SELECT pratica_id FROM tmp_anc_pa), (SELECT src_preventivo FROM tmp_anc_refs),
   (SELECT uid FROM tmp_prev_pss WHERE stato_codice_interno = 'EMESSO'),    'ROOT',      NULL),
  -- B) ROOT ANNULLATO (terminale) + COLLEGATO ACCETTATO (vivo)
  ((SELECT pratica_id FROM tmp_anc_pb), (SELECT src_preventivo FROM tmp_anc_refs),
   (SELECT uid FROM tmp_prev_pss WHERE stato_codice_interno = 'ANNULLATO'), 'ROOT',      NULL),
  ((SELECT pratica_id FROM tmp_anc_pb), (SELECT src_preventivo FROM tmp_anc_refs),
   (SELECT uid FROM tmp_prev_pss WHERE stato_codice_interno = 'ACCETTATO'), 'COLLEGATO', NULL),
  -- C) ROOT EMESSO (risolto) + COLLEGATO COMMESSA (non-risolto: chiave valida,
  --    ma vw_stato_sorgente non ha il ramo commessa)
  ((SELECT pratica_id FROM tmp_anc_pc), (SELECT src_preventivo FROM tmp_anc_refs),
   (SELECT uid FROM tmp_prev_pss WHERE stato_codice_interno = 'EMESSO'),    'ROOT',      NULL),
  ((SELECT pratica_id FROM tmp_anc_pc), (SELECT src_commessa FROM tmp_anc_refs),
   (SELECT commessa_uid_reale FROM tmp_anc_refs),                           'COLLEGATO', NULL),
  -- D) solo ROOT non-risolto (stessa tecnica)
  ((SELECT pratica_id FROM tmp_anc_pd), (SELECT src_commessa FROM tmp_anc_refs),
   (SELECT commessa_uid_reale FROM tmp_anc_refs),                           'ROOT',      NULL);

-- ============================================================
-- 25-28) vw_pratica_doc_sorgente: la regola d'ancora sceglie il doc PIU' VIVO
-- ============================================================
SELECT results_eq(
  $$SELECT stato_codice_interno, risolto, fase
      FROM script.vw_pratica_doc_sorgente
     WHERE pratica_id = (SELECT pratica_id FROM tmp_anc_pa)$$,
  $$VALUES ('EMESSO'::text, true, 'IN_ATTESA'::text)$$,
  '25) Ancora A (mono-doc): proietta il preventivo EMESSO (ROOT)'
);

SELECT results_eq(
  $$SELECT stato_codice_interno, risolto
      FROM script.vw_pratica_doc_sorgente
     WHERE pratica_id = (SELECT pratica_id FROM tmp_anc_pb)$$,
  $$VALUES ('ACCETTATO'::text, true)$$,
  '26) Ancora B: COLLEGATO vivo (ACCETTATO) batte ROOT terminale (ANNULLATO)'
);

SELECT results_eq(
  $$SELECT stato_codice_interno, risolto
      FROM script.vw_pratica_doc_sorgente
     WHERE pratica_id = (SELECT pratica_id FROM tmp_anc_pc)$$,
  $$VALUES ('EMESSO'::text, true)$$,
  '27) Ancora C [regressione prev->commessa]: ROOT risolto (EMESSO) batte COLLEGATO non-risolto'
);

SELECT results_eq(
  $$SELECT stato_codice_interno, risolto
      FROM script.vw_pratica_doc_sorgente
     WHERE pratica_id = (SELECT pratica_id FROM tmp_anc_pd)$$,
  $$VALUES (NULL::text, false)$$,
  '28) Ancora D: solo link non-risolto -> risolto=false, stato NULL (fallback come oggi)'
);

-- ============================================================
-- 29-31) La chiave si cerca nel suo TIPO (rev 2026-10-05, 20261005-23)
--   fn_stato_sorgente non confronta piu' la colonna testuale sorgente_uid ma
--   la chiave nativa (sorgente_chiave_uuid / sorgente_chiave_id), l'unica che
--   sotto RLS arriva all'indice. Questi tre casi fissano l'EQUIVALENZA col
--   confronto testuale di prima, nei punti in cui un cast la romperebbe:
--   una forma non canonica che il cast accetterebbe, una stringa che il cast
--   rifiuterebbe con un errore, una chiave del tipo sbagliato.
-- ============================================================
SELECT results_eq(
  $$SELECT risolto, stato_codice_interno
      FROM pratiche.fn_stato_sorgente(
             (SELECT sorgente_tipo_id FROM tmp_refs_pss),
             upper((SELECT uid FROM tmp_prev_pss WHERE stato_codice_interno = 'EMESSO')))$$,
  $$VALUES (false, 'UNKNOWN'::text)$$,
  '29) uid in forma non canonica (maiuscolo) -> UNKNOWN, come il confronto testuale'
);

SELECT results_eq(
  $$SELECT risolto, stato_codice_interno
      FROM pratiche.fn_stato_sorgente(
             (SELECT sorgente_tipo_id FROM tmp_refs_pss), 'non-un-uid')$$,
  $$VALUES (false, 'UNKNOWN'::text)$$,
  '30) chiave malformata -> UNKNOWN senza errore (nessun cast che esploda)'
);

SELECT results_eq(
  $$SELECT risolto, stato_codice_interno
      FROM pratiche.fn_stato_sorgente(
             (SELECT id FROM config.sorgenti WHERE codice_interno = 'ORDINE_VENDITA'),
             (SELECT uid FROM tmp_prev_pss WHERE stato_codice_interno = 'EMESSO'))$$,
  $$VALUES (false, 'UNKNOWN'::text)$$,
  '31) uid di un preventivo cercato come ORDINE_VENDITA (chiave id) -> UNKNOWN'
);

SELECT * FROM finish();
ROLLBACK;
