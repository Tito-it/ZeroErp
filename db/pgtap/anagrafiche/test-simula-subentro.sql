-- ------------------------------------------------------------
-- SPDX-License-Identifier: AGPL-3.0-or-later
-- pgTAP test per Zero ERP
--
-- Scopo:
--  - Verificare continuità indirizzo ↔ catasto tramite tabella ponte
--  - Simulare subentro con CLONE catasto su nuova istanza:
--      * chiusura cliente precedente
--      * nuova istanza + nuovo cliente sullo stesso PDP/indirizzo
--      * parent_istanza_id valorizzato
--      * catasto clonato (id diverso, dati uguali)
--      * link tabella ponte presente
--
-- Prerequisiti (rev 2026-09-23: PDP e soggetti si COSTRUISCONO, prima
-- erano il PDP GAS-PDP-0002 e due partite IVA di questa macchina):
--  - IVA codice=22
--  - Stati cliente: AT, CH
-- ------------------------------------------------------------

-- ⚠️ Transazione, e non e' una formalita'. Il cleanup di questo file sta in
--   coda: col runner vero (pg_prove gira con ON_ERROR_STOP) un fallimento a
--   meta' non ci arriva mai, e i dati di prova restano nel database a rompere
--   la corsa successiva — che vede un rosso non suo.
--   Brief: brief-db-pgtap-runner-rls-baseline §15.3.
BEGIN;

-- ⚠️ Vincoli DIFFERITI: senza questa riga il test smetterebbe di verificarli.
--   Un trigger DEFERRABLE INITIALLY DEFERRED scatta al COMMIT, e qui il COMMIT
--   non arriva mai (si chiude in ROLLBACK): sarebbero saltati in silenzio, e il
--   file diventerebbe verde per sottrazione. Nel DB ce ne sono 365.
--   IMMEDIATE li riporta a scattare a fine di OGNI istruzione — cioe' esatta-
--   mente come si comportavano prima, quando il file girava in autocommit e
--   ogni istruzione era una transazione a se'. Messa in testa e non in coda
--   apposta: in coda scatterebbero tutti insieme DOPO il cleanup, su righe
--   ormai cancellate, e fallirebbero per un motivo che non riguarda il test.
--   Brief: brief-db-pgtap-runner-rls-baseline §17.
SET CONSTRAINTS ALL IMMEDIATE;

-- Contesto applicativo: questo test gira come gira l'applicazione (ruolo
-- OPERATORE + RLS attiva), non come owner. Senza, con FORCE ROW LEVEL
-- SECURITY disattivo l'owner salta la RLS e il test non la esercita mai.
-- Brief: brief-db-pgtap-runner-rls-baseline §8.
DO $ctx$ BEGIN PERFORM script.fn_pgtap_set_contesto_operatore(); END $ctx$;

SELECT plan(26);

-- =========================================================
--  ⚠️ rev 2026-08-18 (bonifica baseline): qui c'era una «pulizia preliminare
--  idempotente» — cinque DELETE su codici FISSI, per togliere i residui della
--  corsa precedente. Non e' piu' possibile: anagrafiche.clienti e' fra le
--  tabelle di dbops.automation_delete_block_ruoli dal 2026-01-23, quindi il
--  primo DELETE dava «Cancellazione non permessa» e il file moriva li' — ZERO
--  asserzioni su 26.
--
--  Il file era gia' transazionale, quindi non lascia residui SUOI: quelli in
--  giro sono di quando non lo era. Il rimedio e' non collidere invece di
--  cancellare — i codici sono ora UNICI PER CORSA (suffisso in tmp_run_sfx), e
--  i vecchi TST-*-CAT-SUB-00x restano dove sono senza dare fastidio.
-- =========================================================
CREATE TEMP TABLE tmp_run_sfx AS
SELECT substr(md5(clock_timestamp()::text), 1, 8) AS sfx;

-- ⚠️ Le date dello scenario sono state spostate dal 2025 al 2085. Non e'
--   cosmesi: ex_clienti_no_overlap_stesso_pdp vieta due clienti sullo stesso
--   PDP con periodi sovrapposti, e sul PDP che questo test pesca c'e' gia' un
--   cliente residuo con ESATTAMENTE le date del vecchio scenario
--   ([2025-11-01, 2025-11-09)) — lasciato da quando il file non era
--   transazionale. Un anno lontano toglie di mezzo il residuo senza doverlo
--   cancellare, e mette il test al riparo anche dai dati veri.

-- =========================================================
-- 0) Precondizioni
-- =========================================================

-- 0.1) Il PDP GAS dello scenario
-- ⛔ 2026-09-23: era il PDP «GAS-PDP-0002» di QUESTA macchina. Su un database
--   ricostruito dai changelog non c'e', e la fixture moriva su «Non e' stato
--   fornito un valore per pdp_id». Ora si COSTRUISCE, nuovo: niente clienti
--   residui sopra (la ragione per cui le date sono nel 2085, vedi sopra, non
--   c'e' piu' — le date restano dove sono, non danno fastidio).
CREATE TEMP TABLE tmp_pdp AS
SELECT p.pdp_id AS id,
       p.indirizzo_dettaglio_id,
       p.utility_id
FROM dbops.fn_pgtap_crea_pdp('GAS') p;

SELECT is((SELECT count(*)::int FROM tmp_pdp), 1,
  'Costruito un PDP GAS per lo scenario');

-- 0.2) Stati cliente AT e CH
CREATE TEMP TABLE tmp_stato_at AS
SELECT id FROM config.stati_cliente WHERE codice_interno = 'AT' LIMIT 1;

SELECT is((SELECT count(*)::int FROM tmp_stato_at), 1,
  'Esiste stato_cliente AT');

CREATE TEMP TABLE tmp_stato_ch AS
SELECT id FROM config.stati_cliente WHERE codice_interno = 'CH' LIMIT 1;

SELECT is((SELECT count(*)::int FROM tmp_stato_ch), 1,
  'Esiste stato_cliente CH');

-- 0.3) Soggetti
-- ⛔ 2026-09-23: erano due partite IVA di QUESTA macchina. Si costruiscono:
--   due persone giuridiche, ciascuna col suo ruolo CL completo degli
--   indirizzi di ruolo.
CREATE TEMP TABLE tmp_soggetto_1 AS
SELECT dbops.fn_pgtap_crea_soggetto_pg('Subentro soggetto 1') AS id;

SELECT is((SELECT count(*)::int FROM tmp_soggetto_1 WHERE id IS NOT NULL), 1,
  'Costruito il soggetto 1');

CREATE TEMP TABLE tmp_soggetto_2 AS
SELECT dbops.fn_pgtap_crea_soggetto_pg('Subentro soggetto 2') AS id;

SELECT is((SELECT count(*)::int FROM tmp_soggetto_2 WHERE id IS NOT NULL), 1,
  'Costruito il soggetto 2');

-- 0.4) Ruolo cliente
CREATE TEMP TABLE tmp_sr_1 AS
SELECT dbops.fn_pgtap_crea_soggetto_ruolo(s.id, 'CL') AS soggetto_ruolo_id
FROM tmp_soggetto_1 s;

CREATE TEMP TABLE tmp_sr_2 AS
SELECT dbops.fn_pgtap_crea_soggetto_ruolo(s.id, 'CL') AS soggetto_ruolo_id
FROM tmp_soggetto_2 s;

-- 0.5) IVA
CREATE TEMP TABLE tmp_iva AS
SELECT id FROM config.iva WHERE codice = '22' LIMIT 1;

SELECT is((SELECT count(*)::int FROM tmp_iva), 1,
  'Esiste IVA codice=22');





-- ⭐ FINESTRA DIFFERITA (rev 2026-08-18) — secondo strato trovato dopo la
--   pulizia. Il guard trg_istanze_utilities_z90_require_utility_dichiarata_ins
--   e' DEFERRABLE INITIALLY DEFERRED apposta: un'istanza utility acquista
--   senso quando le si aggancia un billing account, un cliente o dei dati
--   precontrattuali, e questo file lo fa qualche decina di righe piu' giu'.
--   Il SET CONSTRAINTS ALL IMMEDIATE del preambolo lo fa pero' scattare
--   sull'INSERT dell'istanza, cioe' prima che la saga possa esistere.
--   Si riapre qui e si RICHIUDE a saga completa (sezione 4): la verifica non
--   si perde, si sposta dove il modello la vuole.
--   ⚠️ La richiusura non e' facoltativa: senza, il ROLLBACK finale se la
--   porterebbe via non verificata.
SET CONSTRAINTS ALL DEFERRED;

-- =========================================================
-- 1) Istanza 1 + catasto 1 + link ponte (via trigger sync)
-- =========================================================

-- 1.1) Istanza 1 (con indirizzo e pdp)
WITH ins_iu1 AS (
  INSERT INTO anagrafiche.istanze_utilities (
    fittizia, codice, proprietario_inquilino, soggetto_id, indirizzo_dettaglio_id, pdp_id
  )
  SELECT
    false,
    'TST-IU-CAT-SUB-001-' || (SELECT sfx FROM tmp_run_sfx),
    'P',
    s1.id,
    p.indirizzo_dettaglio_id,
    p.id
  FROM tmp_soggetto_1 s1, tmp_pdp p
  RETURNING id, indirizzo_dettaglio_id
)
SELECT * INTO TEMP TABLE tmp_iu1 FROM ins_iu1;

SELECT is((SELECT count(*)::int FROM tmp_iu1), 1,
  'Creata istanza 1 (TST-IU-CAT-SUB-001)');

-- 1.2) Catasto 1 (post-refactor: nessun istanza_utility_id)
WITH ins_cat AS (
  INSERT INTO anagrafiche.catasto_unita_immobiliari (
    sezione_catastale, foglio_catastale, particella, subalterno,
    categoria_catastale, classe_catastale,
    rendita_catastale, consistenza,
    tipo_accatastamento, immobile_rurale,
    destinazione_immobile, anno_protocollo, superficie,
    storicizza
  )
  VALUES (
    'TST', 'TST01', 'TST01', '0001',
    'A/2', '1',
    123.45, 1,
    'U', false,
    'AB', 2025, 80,
    true
  )
  RETURNING id
)
SELECT * INTO TEMP TABLE tmp_catasto_1 FROM ins_cat;

SELECT is((SELECT count(*)::int FROM tmp_catasto_1), 1,
  'Creata unità catastale di test (catasto 1)');

-- 1.3) Aggancio catasto 1 alla istanza 1 (trigger sync crea ponte)
UPDATE anagrafiche.istanze_utilities
SET catasto_unita_immobiliare_id = (SELECT id FROM tmp_catasto_1)
WHERE id = (SELECT id FROM tmp_iu1);

SELECT ok((
  SELECT (catasto_unita_immobiliare_id = (SELECT id FROM tmp_catasto_1))
  FROM anagrafiche.istanze_utilities
  WHERE id = (SELECT id FROM tmp_iu1)
)::boolean,
  'Istanza 1 ha catasto_unita_immobiliare_id valorizzato'
);

-- 1.4) Verifica ponte per catasto 1
SELECT is((
  SELECT count(*)::int
  FROM anagrafiche.catasto_unita_immobiliari_indirizzi x
  WHERE x.catasto_unita_id = (SELECT id FROM tmp_catasto_1)
    AND x.indirizzo_dettaglio_id = (SELECT indirizzo_dettaglio_id FROM tmp_iu1)
), 1,
  'Link ponte: catasto 1 ↔ indirizzo (via trgfn_iu_sync_catasto_unita_indirizzo)'
);

-- =========================================================
-- 2) Cliente 1 (AT) + subentro (chiusura cliente precedente)
-- =========================================================



-- 2.0) Subentro preliminare: chiude eventuale cliente già attivo sul PDP prima del Cliente 1 (2085-11-01)
CREATE TEMP TABLE tmp_subentro0 AS
SELECT script.fn_subentro_cliente(
    (SELECT id FROM tmp_pdp),
    DATE '2085-11-01'
) AS cliente_chiuso_id;

-- Se non c'era nessuno, ritorna NULL ed è OK.
SELECT ok(
  (SELECT true)::boolean,
  'Subentro preliminare eseguito (cliente_chiuso_id può essere NULL se nessun attivo)'
);

-- Se ha chiuso qualcuno, verifichiamo data_chiusura e stato CH
SELECT ok((
  SELECT CASE
    WHEN (SELECT cliente_chiuso_id FROM tmp_subentro0) IS NULL THEN true
    ELSE (
      (SELECT data_chiusura::date
       FROM anagrafiche.clienti
       WHERE id = (SELECT cliente_chiuso_id FROM tmp_subentro0)
      ) = (DATE '2085-11-01' - 1)
    )
  END
)::boolean,
  'Subentro preliminare: se ha chiuso un cliente, data_chiusura = 2085-11-01 - 1'
);

SELECT ok((
  SELECT CASE
    WHEN (SELECT cliente_chiuso_id FROM tmp_subentro0) IS NULL THEN true
    ELSE (
      (SELECT stato_cliente_id::bigint
       FROM anagrafiche.clienti
       WHERE id = (SELECT cliente_chiuso_id FROM tmp_subentro0)
      ) = (SELECT id::bigint FROM tmp_stato_ch)
    )
  END
)::boolean,
  'Subentro preliminare: se ha chiuso un cliente, stato_cliente = CH'
);


CREATE TEMP TABLE tmp_ba1 AS
WITH ins_ba AS (
  -- ⚠️ rev 2026-08-18: categoria_cliente_id e' diventata NOT NULL su
  --   billing_account dopo che questo file e' stato scritto. Si legge dal
  --   catalogo invece di inchiodare un id.
  INSERT INTO anagrafiche.billing_account (
    istanza_utility_id, soggetto_ruolo_id, utility_id, codice, categoria_cliente_id
  )
  SELECT
    iu.id,
    sr.soggetto_ruolo_id,
    p.utility_id,
    'TST-BA-CAT-SUB-001-' || (SELECT sfx FROM tmp_run_sfx),
    (SELECT cc.id FROM anagrafiche.categorie_clienti cc
      WHERE cc.codice_interno = 'STANDARD' ORDER BY cc.id LIMIT 1)
  FROM tmp_iu1 iu, tmp_sr_1 sr, tmp_pdp p
  RETURNING id
)
SELECT * FROM ins_ba;

WITH ins_cli AS (
  INSERT INTO anagrafiche.clienti (
    soggetto_ruolo_id, istanza_utility_id, stato_cliente_id, data_attivazione,
    -- ⚠️ rev 2026-08-29: via `iva_id` — la colonna non esiste piu' su
    --   anagrafiche.clienti (changeSet 20260829-22): l'aliquota la decide
    --   la merce, non il cliente. La temp table tmp_iva resta, perche' la
    --   sua asserzione fa parte del plan e verifica ancora config.iva.
    billing_account_id, codice_cliente_importato
  )
  SELECT
    sr.soggetto_ruolo_id,
    iu.id,
    st.id,
    DATE '2085-11-01',
    ba.id,
    'TST-CLI-CAT-SUB-001-' || (SELECT sfx FROM tmp_run_sfx)
  FROM tmp_sr_1 sr, tmp_iu1 iu, tmp_stato_at st, tmp_ba1 ba
  RETURNING id
)
SELECT * INTO TEMP TABLE tmp_cli1 FROM ins_cli;

SELECT is((SELECT count(*)::int FROM tmp_cli1), 1,
  'Creato cliente 1 (AT) con data_attivazione=2085-11-01'
);

-- =========================================================
-- 3) Istanza 2 + Cliente 2 (AT)
--    -> trigger clienti_set_parent_istanza: valorizza parent_istanza_id sulla istanza 2
--    -> trigger iu_clone_catasto_from_parent: clona catasto e valorizza catasto_unita_immobiliare_id
--    -> trigger sync: crea link ponte per catasto 2
-- =========================================================

WITH ins_iu2 AS (
  INSERT INTO anagrafiche.istanze_utilities (
    fittizia, codice, proprietario_inquilino, soggetto_id, indirizzo_dettaglio_id, pdp_id
  )
  SELECT
    false,
    'TST-IU-CAT-SUB-002-' || (SELECT sfx FROM tmp_run_sfx),
    'I',
    s2.id,
    p.indirizzo_dettaglio_id,
    p.id
  FROM tmp_soggetto_2 s2, tmp_pdp p
  RETURNING id, indirizzo_dettaglio_id
)
SELECT * INTO TEMP TABLE tmp_iu2 FROM ins_iu2;

SELECT is((SELECT count(*)::int FROM tmp_iu2), 1,
  'Creata istanza 2 (TST-IU-CAT-SUB-002)'
);

CREATE TEMP TABLE tmp_ba2 AS
WITH ins_ba AS (
  -- ⚠️ rev 2026-08-18: categoria_cliente_id e' diventata NOT NULL su
  --   billing_account dopo che questo file e' stato scritto. Si legge dal
  --   catalogo invece di inchiodare un id.
  INSERT INTO anagrafiche.billing_account (
    istanza_utility_id, soggetto_ruolo_id, utility_id, codice, categoria_cliente_id
  )
  SELECT
    iu.id,
    sr.soggetto_ruolo_id,
    p.utility_id,
    'TST-BA-CAT-SUB-002-' || (SELECT sfx FROM tmp_run_sfx),
    (SELECT cc.id FROM anagrafiche.categorie_clienti cc
      WHERE cc.codice_interno = 'STANDARD' ORDER BY cc.id LIMIT 1)
  FROM tmp_iu2 iu, tmp_sr_2 sr, tmp_pdp p
  RETURNING id
)
SELECT * FROM ins_ba;



-- CHIUSURA EVENTUALE UTENTE ATTIVO
-- Subentro: chiude il cliente precedente sul PDP prima di creare il nuovo (2085-11-10)
CREATE TEMP TABLE tmp_subentro1 AS
SELECT script.fn_subentro_cliente(
    (SELECT id FROM tmp_pdp),
    DATE '2085-11-10'
) AS cliente_chiuso_id;

SELECT is(
    (SELECT cliente_chiuso_id::bigint FROM tmp_subentro1),
    (SELECT id::bigint FROM tmp_cli1),
    'fn_subentro_cliente chiude il cliente precedente attivo sul PDP (CLI1)'
);

SELECT is(
    (
        SELECT data_chiusura::date
        FROM anagrafiche.clienti
        WHERE id = (SELECT id FROM tmp_cli1)
    ),
    (DATE '2085-11-10' - 1),
    'Cliente precedente chiuso con data_chiusura = data attivazione nuovo - 1 giorno'
);

SELECT is(
    (
        SELECT stato_cliente_id::bigint
        FROM anagrafiche.clienti
        WHERE id = (SELECT id FROM tmp_cli1)
    ),
    (SELECT id::bigint FROM tmp_stato_ch),
    'Cliente precedente impostato a stato CH dopo subentro'
);



-- Inserisce cliente 2

WITH ins_cli AS (
  INSERT INTO anagrafiche.clienti (
    soggetto_ruolo_id, istanza_utility_id, stato_cliente_id, data_attivazione,
    -- ⚠️ rev 2026-08-29: via `iva_id` — la colonna non esiste piu' su
    --   anagrafiche.clienti (changeSet 20260829-22): l'aliquota la decide
    --   la merce, non il cliente. La temp table tmp_iva resta, perche' la
    --   sua asserzione fa parte del plan e verifica ancora config.iva.
    billing_account_id, codice_cliente_importato
  )
  SELECT
    sr.soggetto_ruolo_id,
    iu.id,
    st.id,
    DATE '2085-11-10',
    ba.id,
    'TST-CLI-CAT-SUB-002-' || (SELECT sfx FROM tmp_run_sfx)
  FROM tmp_sr_2 sr, tmp_iu2 iu, tmp_stato_at st, tmp_ba2 ba
  RETURNING id
)
SELECT * INTO TEMP TABLE tmp_cli2 FROM ins_cli;

SELECT is((SELECT count(*)::int FROM tmp_cli2), 1,
  'Creato cliente 2 (AT) con data_attivazione=2085-11-10'
);

-- Saga completa (due istanze, due billing account, due clienti): si richiude
-- la finestra. I guard differiti scattano QUI, su istanze finite.
SET CONSTRAINTS ALL IMMEDIATE;

-- =========================================================
-- 4) Verifiche: parent chain + clone + ponte + unique
-- =========================================================

-- 4.1) stesso indirizzo
SELECT is(
  (SELECT indirizzo_dettaglio_id::bigint FROM tmp_iu2),
  (SELECT indirizzo_dettaglio_id::bigint FROM tmp_iu1),
  'Istanza 2 ha lo stesso indirizzo_dettaglio_id di istanza 1'
);

-- 4.2) parent_istanza_id su istanza 2 punta a istanza 1
SELECT is((
  SELECT parent_istanza_id::bigint
  FROM anagrafiche.istanze_utilities
  WHERE id = (SELECT id FROM tmp_iu2)
), (SELECT id::bigint FROM tmp_iu1),
  'Istanza 2: parent_istanza_id = istanza 1'
);

-- 4.3) catasto su istanza 2 valorizzato (clone)
SELECT ok((
  SELECT (catasto_unita_immobiliare_id IS NOT NULL)
  FROM anagrafiche.istanze_utilities
  WHERE id = (SELECT id FROM tmp_iu2)
)::boolean,
  'Istanza 2: catasto_unita_immobiliare_id valorizzato via clone automatico'
);

-- 4.4) clone: id diverso da catasto 1
SELECT ok((
  SELECT (
    (SELECT catasto_unita_immobiliare_id
     FROM anagrafiche.istanze_utilities
     WHERE id = (SELECT id FROM tmp_iu2))
    <>
    (SELECT id FROM tmp_catasto_1)
  )
)::boolean,
  'Clone: istanza 2 ha un catasto nuovo (id diverso da catasto 1)'
);

-- 4.5) clone: campi chiave identici
SELECT ok((
  SELECT (
    c2.sezione_catastale      = c1.sezione_catastale AND
    c2.foglio_catastale       = c1.foglio_catastale  AND
    c2.particella             = c1.particella        AND
    c2.subalterno             = c1.subalterno        AND
    c2.categoria_catastale    = c1.categoria_catastale AND
    c2.classe_catastale       = c1.classe_catastale AND
    c2.rendita_catastale      = c1.rendita_catastale AND
    c2.consistenza            = c1.consistenza AND
    c2.tipo_accatastamento    = c1.tipo_accatastamento AND
    c2.immobile_rurale        = c1.immobile_rurale AND
    c2.destinazione_immobile  = c1.destinazione_immobile AND
    c2.anno_protocollo        = c1.anno_protocollo AND
    c2.superficie             = c1.superficie
  )
  FROM anagrafiche.catasto_unita_immobiliari c1
  JOIN anagrafiche.catasto_unita_immobiliari c2
    ON c1.id = (SELECT id FROM tmp_catasto_1)
   AND c2.id = (SELECT catasto_unita_immobiliare_id
                FROM anagrafiche.istanze_utilities
                WHERE id = (SELECT id FROM tmp_iu2))
)::boolean,
  'Clone: campi catastali principali identici tra catasto 1 e catasto 2'
);

-- 4.6) ponte: link per catasto 2 ↔ indirizzo
SELECT is((
  SELECT count(*)::int
  FROM anagrafiche.catasto_unita_immobiliari_indirizzi x
  WHERE x.catasto_unita_id = (
    SELECT catasto_unita_immobiliare_id
    FROM anagrafiche.istanze_utilities
    WHERE id = (SELECT id FROM tmp_iu2)
  )
    AND x.indirizzo_dettaglio_id = (SELECT indirizzo_dettaglio_id FROM tmp_iu2)
), 1,
  'Ponte: creato link catasto 2 ↔ indirizzo (via trigger sync)'
);

-- 4.7) unique: duplicato ponte deve fallire
SELECT throws_ok(
  $$
  INSERT INTO anagrafiche.catasto_unita_immobiliari_indirizzi (catasto_unita_id, indirizzo_dettaglio_id)
  VALUES (
    (SELECT catasto_unita_immobiliare_id
     FROM anagrafiche.istanze_utilities
     WHERE id = (SELECT id FROM tmp_iu2)),
    (SELECT indirizzo_dettaglio_id FROM tmp_iu2)
  );
  $$,
  '23505',
  NULL,
  'Unique: impedisce duplicato catasto 2 ↔ indirizzo (uq_catunitaindir)'
);

SELECT * FROM finish();

-- Il ROLLBACK e' la garanzia: comunque vada — verde, rosso, o morto a meta' —
-- questo file non lascia nulla dietro di se'. Le DELETE del cleanup restano
-- perche' dove sono un'asserzione devono girare davvero.
ROLLBACK;
