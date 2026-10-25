-- ------------------------------------------------------------
-- SPDX-License-Identifier: GPL-3.0-or-later
-- rev 2026-10-25 (brief-db-pgtap-reso-costruito, giro D-4): la commessa da dbops.fn_pgtap_crea_commessa (sorgente ROOT), le attivita' da dbops.fn_pgtap_crea_commessa_attivita (sorgente DDT_VENDITA, E-3) e la fattura agganciata da dbops.fn_pgtap_fattura_attivita (pg_temp.agr_fattura resta: compone i due builder per le due partite fatturate); l'ordine a due righe della partita D da dbops.fn_pgtap_crea_ddt_da_ordine con p_righe_ordine (ritirato pg_temp.agr_mk_ordine).
-- rev 2026-10-25 (brief-db-pgtap-reso-costruito): il reso dal builder dbops.fn_pgtap_crea_reso (anche in bozza, e a due righe con p_reso_id); restano scritti a mano l'annullo fn_annulla_reso (il caso: per lui resta concessa conferma_reso), l'ordine a due righe e la commessa con la fattura.
-- rev 2026-10-25 (brief-db-pgtap-bolla-e-reso-costruiti, giro 1): la bolla da ordine dal builder dbops.fn_pgtap_crea_ddt_da_ordine; resta scritto a mano l'ordine a DUE righe della partita D (ordine speciale: la bolla dal builder con p_ordine_id), il reso (giro 2) e la commessa con la fattura, che sono il caso del test.
-- rev 2026-10-20 (brief-db-grammatica-unica-documenti §13, 2e/L2c-1): le chiavi del push col codice della sorgente, composte da script.fn_segment_key dove la forma lo permette (le forme su piu' righe col prefisso lungo); corsia e codice del registro coi codici lunghi.
-- pgTAP test per Zero ERP
-- Test: vendite.fn_annulla_reso — la guardia dell'accredito
--       (E_RESO_ANNULLO_CON_ACCREDITO, changeset 20260819-22)
-- ------------------------------------------------------------
-- ⛔ Prima di 20260819-22 questo file e' ROSSO su 4 test, ed e' il difetto che
--    misura. Corsa del 2026-08-19 senza il changeset (PGTAP_RUNNER=app):
--      1      verde  (la fixture regge: reso confermato, riga in coda)
--      2      have OK, want P0001|E_RESO_ANNULLO_CON_ACCREDITO  <- ⭐ il difetto
--             in due parole: l'annullo RIESCE
--      3      have 1|ANNULLATO, want 1|CONFERMATO  <- conseguenza del 2: il
--             reso e' gia' annullato, con il ponte ancora intero dietro. E'
--             esattamente lo stato che fa uscire una nota di credito per un
--             reso annullato
--      4      died E_RESO_STATO_NON_ANNULLABILE  <- non e' un difetto suo: il
--             reso l'ha gia' annullato il test 2
--      5,6,7  verdi
--      8      have OK, want P0001|...  <- il gemello del 2 sul reso a due righe
--    Con il changeset applicato: 8/8.
--
-- ⛔ E per i test 9..11 (capability, changeset 20260820-12) la corsa «prima» e'
--    10/11, NON 8/11 — misurata il 2026-08-20, e vale la pena scriverlo:
--      9   have true|?|?, want false|RESO_CON_ACCREDITI|...  <- ⭐ l'UNICO che
--          misura il difetto: senza il changeset il bottone e' acceso e muto
--      10  VERDE anche senza  <- l'azione era gia' nell'elenco e
--          can_change_state gia' true: e' un'INVARIANTE, non una misura
--      11  VERDE anche senza  <- senza accredito enabled e' true comunque
--    ⚠️ Non e' un difetto dei test 10 e 11: sono invarianti che devono reggere
--    PRIMA e DOPO, ed e' il loro mestiere accorgersi di una regressione futura
--    (l'azione che sparisce dall'elenco, la capability che non si riabilita).
--    Ma chi legge «tre test nuovi» deve sapere che il difetto lo misura UNO.
--
-- Indice test (1..11):
--   1) fixture A: il reso e' CONFERMATO e la sua riga e' in coda accrediti
--   2) ⭐ registrato l'accredito, fn_annulla_reso RIFIUTA: P0001 e il codice
--      E_RESO_ANNULLO_CON_ACCREDITO nel canale CONSTRAINT
--   3) e non ha cascatato: il ponte e' intero e il reso e' ancora CONFERMATO
--   4) ⭐⭐ annullato l'accredito l'annullo del reso PASSA — l'auto-riparazione
--      di C-3, che e' l'altra meta' del vincolo
--   5) e il reso e' davvero ANNULLATO (il verbo ha fatto il suo mestiere)
--   6) nessuna regressione: un reso CONFERMATO senza accredito si annulla
--   7) guardia inerte su un reso DRAFT: un accredito pretende il CONFERMATO
--   8) ⭐ basta UNA riga di ponte su UNA riga per rifiutare l'INTERO annullo
--   ⭐ 9..11 — LA CAPABILITY, aggiunte il 2026-08-20 (changeset 20260820-12).
--      La guardia da sola lasciava il bottone «annulla» acceso e muto. La regola
--      di casa e' «permesso => nascondi, STATO => disabilita col motivo»
--      (frontend-standards, e ora linee-guida-sql §12): avere un accredito e'
--      uno stato che CAMBIA, quindi il bottone resta a video e spiega.
--   9) capability: l'azione annulla c'e' ma e' DISABILITATA, col motivo giusto
--  10) e can_change_state resta true: il bottone e' grigio, non sparito
--  11) ⭐ annullato l'accredito la capability torna abilitata — l'auto-riparazione
--      del test 4, vista dal lato dell'interfaccia
--
-- ⭐ PERCHE' IL TEST 8 NON USA UN KIT. La proprieta' da verificare e' «una
--    sola riga di ponte basta a rifiutare tutto il documento». Il kit la
--    produce moltiplicando i ponti su UNA riga di reso (una rettifica per
--    componente): la EXISTS la vedrebbe comunque al primo. La forma che
--    davvero mette alla prova la guardia e' l'opposta — un reso con DUE righe
--    di cui UNA SOLA accreditata: li' la EXISTS deve attraversare tutte le
--    righe del reso, ed e' l'unico modo in cui puo' sbagliare.
--
-- ⚠️ COSA QUESTO FILE NON PUO' MISURARE, e va detto invece di sembrare
--    coperto: «la guardia sta prima di qualunque scrittura». Il test 3 rilegge
--    lo stato dopo un rifiuto, ma sia throws_ok sia il nostro helper catturano
--    l'eccezione in una sottotransazione, che annulla comunque le scritture
--    eventuali. Quel test misura quindi l'ESITO (il reso resta usabile, il
--    ponte resta intero), non l'ordine delle istruzioni. L'ordine si legge nel
--    corpo della funzione, dove la EXISTS precede la UPDATE ad ANNULLATO.
--
-- ⚠️ Il codice di dominio si legge dal canale CONSTRAINT dell'eccezione, non
--    dal testo: e' il contratto dichiarato da script.fn_log_and_raise_error
--    («P0001 + CONSTRAINT valorizzato = errore di dominio»). Un throws_like
--    sulla frase legherebbe il test alla formulazione del catalogo, che e'
--    materia dell'operatore e cambia senza che cambi la regola.
--    ⭐ E c'e' un secondo motivo, misurato: cosi' il test e' verde ANCHE prima
--    che il mirror CSV di 80_data carichi la riga del codice nuovo. Il codice
--    esce dal canale strutturato comunque; e' solo la FRASE a ripiegare finche'
--    il catalogo non ha la voce. Un test sul testo sarebbe rosso per un motivo
--    che non c'entra niente con la guardia.
--
-- ⚠️ Il tipo di reso e' RESO_PER_RICONSEGNA (riapre_residuo = true), come
--    nelle fixture gemelle: e' quello che le altre prove di questo cantiere
--    usano, e tiene il file confrontabile con test-rinuncia-gate-accredito-v1.
-- ------------------------------------------------------------

BEGIN;

SET CONSTRAINTS ALL IMMEDIATE;

-- ⛔ rev 2026-10-13: il mondo si COSTRUISCE (su un DB ricostruito anagrafiche e
--   articoli sono vuoti): azienda + operatore + cliente BA, e il builder apre
--   da se' il contesto su quell'operatore. Niente utente 1 inchiodato.
CREATE TEMP TABLE tmp_mondo_acc AS
SELECT * FROM dbops.fn_pgtap_crea_mondo_cliente('pgTAP annulla reso gate');
-- Il mondo ha gia' aperto il contesto sul suo operatore: la riga lo
--   dichiara (e il guardrail del preambolo la cerca).
DO $ctx$ BEGIN PERFORM script.fn_pgtap_set_contesto_operatore((SELECT auth_user_id FROM tmp_mondo_acc)); END $ctx$;

SELECT plan(11);

-- Dal 2026-09-28 conferma e annullo del reso sono verbi che applicano
-- l'azione conferma_reso (brief-db-magazzino-lotto-3-bis-carico-da-reso, D-3b-f).
-- La conferma la concede il builder del reso; l'annullo e' il caso del test, e
-- l'operatore di fixture non ha azioni: si concede qui.
DO $az$ BEGIN
    PERFORM dbops.fn_pgtap_concedi_azione(
        NULLIF(current_setting('app.current_user_id', true), '')::integer, 'conferma_reso');
END $az$;

CREATE TEMP TABLE tmp_refs_agr AS
SELECT
  m.billing_account_id                         AS billing_account_id,
  -- ⛔ rev 2026-10-13: l'articolo si COSTRUISCE (merce non solo-componente, non
  --   gestito: il test non misura il magazzino) — da zero il catalogo ha solo ONERE_*.
  dbops.fn_pgtap_crea_articolo('PGTAP-ANN-RESO-GATE', false)                  AS articolo_id
-- ⛔ rev 2026-10-13: il BA e' quello del mondo costruito, non il primo del database.
FROM tmp_mondo_acc m;

-- ============================================================
-- Helper di fixture
-- Le partite sono la bolla CONSEGNATA del builder
-- dbops.fn_pgtap_crea_ddt_da_ordine (la partita D con un ordine a due righe,
-- p_righe_ordine). La merce viene FATTURATA (attivita' sul segmento della
-- bolla, emessa, agganciata a una fattura vera, da dbops.fn_pgtap_fattura_attivita):
-- e' la catena che fn_accredita_riga_reso risale per copiare il prezzo.
-- ============================================================

-- ⚠️ ORDER BY esplicito: la n-esima riga del DDT va scelta, non pescata.
CREATE OR REPLACE FUNCTION pg_temp.agr_ddt_riga(p_ddt_id bigint, p_n integer)
RETURNS bigint AS $$
  SELECT dr.id FROM vendite.ddt_righe dr
   WHERE dr.ddt_id = p_ddt_id ORDER BY dr.id OFFSET (p_n - 1) LIMIT 1;
$$ LANGUAGE sql;

-- L'attivita' sul segmento di una riga di bolla (E-3: sorgente DDT_VENDITA),
-- fatturata. Torna la riga di fattura.
CREATE OR REPLACE FUNCTION pg_temp.agr_fattura(p_ddt_uid uuid, p_ddt_riga_id bigint, p_qta numeric, p_prezzo numeric)
RETURNS bigint AS $$
DECLARE v_att bigint; v_riga bigint;
BEGIN
  SELECT a.attivita_id INTO v_att
    FROM dbops.fn_pgtap_crea_commessa_attivita((SELECT commessa_id FROM tmp_com_agr), p_prezzo,
             p_articolo_id      => (SELECT articolo_id FROM tmp_refs_agr),
             p_sorgente_codice  => 'DDT_VENDITA',
             p_sorgente_uid     => p_ddt_uid::text,
             p_sorgente_riga_id => p_ddt_riga_id,
             p_quantita         => p_qta) a;
  SELECT f.fattura_riga_id INTO v_riga
    FROM dbops.fn_pgtap_fattura_attivita('annulla reso gate', ARRAY[v_att]) f;
  RETURN v_riga;
END $$ LANGUAGE plpgsql;

-- I resi sono del builder dbops.fn_pgtap_crea_reso: confermati, in DRAFT
-- (test 7) o a due righe (test 8, la seconda con p_reso_id).

-- ⭐ L'esito dell'annullo come COPPIA (sqlstate, codice di dominio), letto dal
--    canale CONSTRAINT: e' il contratto di script.fn_log_and_raise_error, e non
--    lega il test alla formulazione del messaggio.
CREATE OR REPLACE FUNCTION pg_temp.agr_esito_annullo(p_reso_id bigint)
RETURNS text AS $$
DECLARE v_cod text;
BEGIN
  PERFORM vendite.fn_annulla_reso(p_reso_id);
  RETURN 'OK';
EXCEPTION WHEN OTHERS THEN
  GET STACKED DIAGNOSTICS v_cod = CONSTRAINT_NAME;
  RETURN SQLSTATE || '|' || COALESCE(NULLIF(v_cod, ''), '-');
END $$ LANGUAGE plpgsql;

-- ============================================================
-- FIXTURE: una commessa sola per tutto il file.
-- ============================================================
CREATE TEMP TABLE tmp_com_agr AS
SELECT c.commessa_id
  FROM dbops.fn_pgtap_crea_commessa('annulla reso gate', NULL,
           (SELECT billing_account_id FROM tmp_refs_agr), p_con_sorgente_root => true) c;

-- ── PARTITA A: consegnati 10 a 25, fatturati 10, resi 3 -> accreditabile ──
CREATE TEMP TABLE tmp_pa AS
SELECT b.ordine_id, b.ddt_id, b.ddt_uid, b.ddt_riga_id
  FROM dbops.fn_pgtap_crea_ddt_da_ordine('annulla reso gate',
           p_billing_account_id   => (SELECT billing_account_id FROM tmp_refs_agr),
           p_quantita             => 10,
           p_prezzo               => 25,
           p_articolo_id          => (SELECT articolo_id FROM tmp_refs_agr),
           p_fatturazione_trigger => 'CONSEGNATO') b;
CREATE TEMP TABLE tmp_pa_riga AS SELECT ddt_riga_id FROM tmp_pa;
CREATE TEMP TABLE tmp_pa_fatt AS
SELECT pg_temp.agr_fattura((SELECT ddt_uid FROM tmp_pa), (SELECT ddt_riga_id FROM tmp_pa_riga),
    10, 25) AS fattura_riga_id;
CREATE TEMP TABLE tmp_reso_a AS
SELECT * FROM dbops.fn_pgtap_crea_reso('annulla reso gate', (SELECT ddt_id FROM tmp_pa), 3,
                                       'RESO_PER_RICONSEGNA',
                                       p_ddt_riga_id => (SELECT ddt_riga_id FROM tmp_pa_riga));

SELECT is(
  (SELECT sdr.codice_interno FROM vendite.resi r
     JOIN config.stati_doc_reso sdr ON sdr.id = r.stato_doc_reso_id
    WHERE r.id = (SELECT reso_id FROM tmp_reso_a))
  || '|' ||
  (SELECT count(*)::int FROM vendite.vw_resi_da_accreditare q
    WHERE q.resi_riga_id = (SELECT resi_riga_id FROM tmp_reso_a))::text,
  'CONFERMATO|1',
  '1) fixture A: il reso e'' CONFERMATO e la sua riga e'' in coda accrediti'
);

-- ============================================================
-- IL VERBO, e poi l'annullo del documento
-- ============================================================
CREATE TEMP TABLE tmp_acc_a AS
SELECT * FROM vendite.fn_accredita_riga_reso((SELECT resi_riga_id FROM tmp_reso_a));

-- ⚠️ Il verbo in un'istruzione SEPARATA dall'asserzione: la snapshot di
--    statement leggerebbe PRIMA delle scritture, e il rosso accuserebbe la
--    funzione invece del test.
CREATE TEMP TABLE tmp_esito_a AS
SELECT pg_temp.agr_esito_annullo((SELECT reso_id FROM tmp_reso_a)) AS esito;

SELECT is(
  (SELECT esito FROM tmp_esito_a),
  'P0001|E_RESO_ANNULLO_CON_ACCREDITO',
  '2) con l''accredito registrato l''annullo del reso e'' RIFIUTATO, col codice giusto'
);

-- 3) Il rifiuto non ha disfatto niente per conto suo: e' il punto 1 della
--    segnalazione BE — «rifiutare, non cascatare». Se la funzione avesse
--    annullato l'accredito da se', il ponte sarebbe vuoto e il reso ANNULLATO.
SELECT is(
  (SELECT count(*)::int FROM vendite.resi_righe rr
     JOIN vendite.resi_righe_accrediti a ON a.resi_riga_id = rr.id
    WHERE rr.reso_id = (SELECT reso_id FROM tmp_reso_a))::text
  || '|' ||
  (SELECT sdr.codice_interno FROM vendite.resi r
     JOIN config.stati_doc_reso sdr ON sdr.id = r.stato_doc_reso_id
    WHERE r.id = (SELECT reso_id FROM tmp_reso_a)),
  '1|CONFERMATO',
  '3) e non ha cascatato: il ponte e'' intero e il reso e'' ancora CONFERMATO'
);

-- ============================================================
-- 4-5) ⭐⭐ L'AUTO-RIPARAZIONE DI C-3.
--   La guardia non sa nulla dell'annullo dell'accredito: si spegne solo
--   perche' quello CANCELLA le righe di ponte. Se un giorno diventasse un
--   soft-delete questi due test diventerebbero rossi — ed e' il loro scopo.
-- ============================================================
SELECT vendite.fn_annulla_accredito_riga_reso(
    (SELECT resi_riga_id FROM tmp_reso_a), 'ci ho ripensato, pgTAP');

SELECT lives_ok(
  format($q$SELECT vendite.fn_annulla_reso(%s)$q$, (SELECT reso_id FROM tmp_reso_a)),
  '4) annullato l''accredito, l''annullo del reso passa: la guardia si auto-ripara'
);

SELECT is(
  (SELECT sdr.codice_interno FROM vendite.resi r
     JOIN config.stati_doc_reso sdr ON sdr.id = r.stato_doc_reso_id
    WHERE r.id = (SELECT reso_id FROM tmp_reso_a)),
  'ANNULLATO',
  '5) e il reso e'' davvero ANNULLATO: il verbo ha fatto il suo mestiere'
);

-- ============================================================
-- 6) NESSUNA REGRESSIONE — reso CONFERMATO, mai accreditato.
--    Partita B a parte: due resi sulla stessa riga di DDT si contendono il
--    guard sull'over-return, che conta anche le bozze.
-- ============================================================
CREATE TEMP TABLE tmp_pb AS
SELECT b.ordine_id, b.ddt_id, b.ddt_uid, b.ddt_riga_id
  FROM dbops.fn_pgtap_crea_ddt_da_ordine('annulla reso gate',
           p_billing_account_id   => (SELECT billing_account_id FROM tmp_refs_agr),
           p_quantita             => 10,
           p_prezzo               => 25,
           p_articolo_id          => (SELECT articolo_id FROM tmp_refs_agr),
           p_fatturazione_trigger => 'CONSEGNATO') b;
CREATE TEMP TABLE tmp_pb_riga AS SELECT ddt_riga_id FROM tmp_pb;
CREATE TEMP TABLE tmp_reso_b AS
SELECT * FROM dbops.fn_pgtap_crea_reso('annulla reso gate', (SELECT ddt_id FROM tmp_pb), 3,
                                       'RESO_PER_RICONSEGNA',
                                       p_ddt_riga_id => (SELECT ddt_riga_id FROM tmp_pb_riga));

SELECT lives_ok(
  format($q$SELECT vendite.fn_annulla_reso(%s)$q$, (SELECT reso_id FROM tmp_reso_b)),
  '6) nessuna regressione: un reso CONFERMATO senza accredito si annulla come prima'
);

-- ============================================================
-- 7) GUARDIA INERTE SU UN RESO DRAFT.
--    Un accredito pretende il CONFERMATO (vw_resi_righe_effettive filtra li'),
--    quindi su una bozza la EXISTS non puo' trovare nulla — e l'annullo da
--    DRAFT, che non ha effetti da stornare, deve restare quello di sempre.
-- ============================================================
CREATE TEMP TABLE tmp_pc AS
SELECT b.ordine_id, b.ddt_id, b.ddt_uid, b.ddt_riga_id
  FROM dbops.fn_pgtap_crea_ddt_da_ordine('annulla reso gate',
           p_billing_account_id   => (SELECT billing_account_id FROM tmp_refs_agr),
           p_quantita             => 10,
           p_prezzo               => 25,
           p_articolo_id          => (SELECT articolo_id FROM tmp_refs_agr),
           p_fatturazione_trigger => 'CONSEGNATO') b;
CREATE TEMP TABLE tmp_pc_riga AS SELECT ddt_riga_id FROM tmp_pc;
CREATE TEMP TABLE tmp_reso_c AS
SELECT * FROM dbops.fn_pgtap_crea_reso('annulla reso gate', (SELECT ddt_id FROM tmp_pc), 3,
                                       'RESO_PER_RICONSEGNA', 'DRAFT',
                                       p_ddt_riga_id => (SELECT ddt_riga_id FROM tmp_pc_riga));

CREATE TEMP TABLE tmp_esito_c AS
SELECT pg_temp.agr_esito_annullo((SELECT reso_id FROM tmp_reso_c)) AS esito;

SELECT is(
  (SELECT esito FROM tmp_esito_c),
  'OK',
  '7) guardia inerte su un reso DRAFT: l''annullo da bozza resta quello di sempre'
);

-- ============================================================
-- 8) ⭐ BASTA UNA RIGA DI PONTE PER RIFIUTARE L'INTERO ANNULLO.
--    Partita D con DUE righe: si fattura e si accredita SOLO la prima. La
--    seconda riga di reso non ha (e non puo' avere) accredito. La guardia
--    deve comunque rifiutare, perche' la sua unita' e' il DOCUMENTO.
-- ============================================================
CREATE TEMP TABLE tmp_pd AS
SELECT b.ordine_id, b.ddt_id, b.ddt_uid
  FROM dbops.fn_pgtap_crea_ddt_da_ordine('annulla reso gate',
           p_billing_account_id   => (SELECT billing_account_id FROM tmp_refs_agr),
           p_fatturazione_trigger => 'CONSEGNATO',
           p_data_ordine          => DATE '2026-07-15',
           p_righe_ordine         => jsonb_build_array(
               jsonb_build_object('articolo_id', (SELECT articolo_id FROM tmp_refs_agr), 'quantita', 10, 'prezzo', 25),
               jsonb_build_object('articolo_id', (SELECT articolo_id FROM tmp_refs_agr), 'quantita', 10, 'prezzo', 25))) b;
CREATE TEMP TABLE tmp_pd_righe AS
SELECT pg_temp.agr_ddt_riga((SELECT ddt_id FROM tmp_pd), 1) AS riga1,
       pg_temp.agr_ddt_riga((SELECT ddt_id FROM tmp_pd), 2) AS riga2;
CREATE TEMP TABLE tmp_pd_fatt AS
SELECT pg_temp.agr_fattura((SELECT ddt_uid FROM tmp_pd), (SELECT riga1 FROM tmp_pd_righe),
    10, 25) AS fattura_riga_id;
-- La prima riga in bozza, la seconda aggiunta allo stesso reso, che si conferma.
CREATE TEMP TABLE tmp_reso_d AS
SELECT * FROM dbops.fn_pgtap_crea_reso('annulla reso gate', (SELECT ddt_id FROM tmp_pd), 3,
                                       'RESO_PER_RICONSEGNA', 'DRAFT',
                                       p_ddt_riga_id => (SELECT riga1 FROM tmp_pd_righe));
CREATE TEMP TABLE tmp_reso_d_riga2 AS
SELECT * FROM dbops.fn_pgtap_crea_reso('annulla reso gate', NULL, 3,
                                       'RESO_PER_RICONSEGNA',
                                       p_ddt_riga_id => (SELECT riga2 FROM tmp_pd_righe),
                                       p_reso_id     => (SELECT reso_id FROM tmp_reso_d));

CREATE TEMP TABLE tmp_acc_d AS
SELECT * FROM vendite.fn_accredita_riga_reso((SELECT resi_riga_id FROM tmp_reso_d));

CREATE TEMP TABLE tmp_esito_d AS
SELECT pg_temp.agr_esito_annullo((SELECT reso_id FROM tmp_reso_d)) AS esito;

SELECT is(
  (SELECT esito FROM tmp_esito_d),
  'P0001|E_RESO_ANNULLO_CON_ACCREDITO',
  '8) basta UNA riga accreditata su due per rifiutare l''INTERO annullo del reso'
);

-- ============================================================
-- 9..11) ⭐ LA CAPABILITY DICE LA STESSA COSA DELLA GUARDIA.
--   Se questi tre e i test 2/4 divergessero, l'operatore vedrebbe un bottone
--   acceso e prenderebbe un 409 in faccia — o, peggio, un bottone grigio su un
--   annullo che sarebbe passato. Il predicato e' lo stesso EXISTS, apposta.
-- ============================================================

CREATE TEMP TABLE tmp_cap_d AS
SELECT a->>'key' AS azione,
       (a->>'enabled')::boolean AS enabled,
       a->>'reason'     AS reason,
       a->>'reason_key' AS reason_key
  FROM jsonb_array_elements(
       script.fn_available_actions_reso((SELECT reso_id FROM tmp_reso_d)) -> 'available_actions') a
 WHERE a->>'key' = 'annulla';

SELECT is(
  (SELECT enabled::text || '|' || COALESCE(reason,'?') || '|' || COALESCE(reason_key,'?')
     FROM tmp_cap_d),
  'false|RESO_CON_ACCREDITI|vendite.reso.annulla_reason.con_accrediti',
  '9) capability: l''azione annulla e'' disabilitata col motivo dell''accredito'
);

-- ⚠️ Il punto della decisione, e la ragione per cui NON si e' tolta l'azione
--   dalle ammesse: sparire senza spiegazione e' la variante peggiore.
SELECT is(
  (SELECT count(*)::int FROM tmp_cap_d)::text || '|' ||
  (script.fn_available_actions_reso((SELECT reso_id FROM tmp_reso_d)) ->> 'can_change_state'),
  '1|true',
  '10) l''azione resta NELL''ELENCO e can_change_state resta true: grigia, non sparita'
);

-- ⭐ L'auto-riparazione del test 4, vista dall'interfaccia: la capability non sa
--   nulla dell'annullo dell'accredito, si riabilita solo perche' quello CANCELLA
--   le righe di ponte.
SELECT vendite.fn_annulla_accredito_riga_reso(
    (SELECT resi_riga_id FROM tmp_reso_d), 'ci ho ripensato anche qui, pgTAP');

SELECT is(
  (SELECT (a->>'enabled')::boolean
     FROM jsonb_array_elements(
          script.fn_available_actions_reso((SELECT reso_id FROM tmp_reso_d)) -> 'available_actions') a
    WHERE a->>'key' = 'annulla'),
  true,
  '11) annullato l''accredito la capability torna abilitata (auto-riparazione lato UI)'
);

SELECT * FROM finish();
ROLLBACK;
