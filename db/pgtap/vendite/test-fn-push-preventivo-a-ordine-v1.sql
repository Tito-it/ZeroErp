-- ------------------------------------------------------------
-- SPDX-License-Identifier: AGPL-3.0-or-later
-- pgtap-runner: owner
-- pgtap-runner-motivo: CREATE TRIGGER su vendite.preventivi — fault injection sulla transizione a
--   EVASO, per dimostrare che il push e' atomico. Il ruolo applicativo ha la
--   DML ma non il privilegio TRIGGER, e non deve averlo.
-- rev 2026-10-24 (brief-modello-documento-vendita Q-2/Q-4): i tre preventivi vengono da dbops.fn_pgtap_crea_preventivo (cliente, emittente e testata costruiti, nascita in bozza) e l'articolo MERCE si costruisce con la natura alla nascita; prima billing account, emittente e articolo erano «i primi per id» del database (su uno scratch ricostruito il primo articolo e' un onere, che la natura merce giustamente rifiuta).
-- pgTAP test per Zero ERP
--
-- Test: vendite.fn_push_preventivo_a_ordine — ramo ORDINE dello split preventivo
--       (brief-preventivi-ordini.md D8). Copia le righe MERCE verso un nuovo
--       ordine DRAFT con documento_origine=(PREVENTIVO, id), snapshot prezzi.
--
-- Aggiornato 2026-07-08 (analisi-fix-transazioni #10, migr. 20260708-01):
--   la funzione ora (sezione 8) transita ATOMICAMENTE il preventivo ACCETTATO
--   -> EVASO se non resta residuo su nessun ramo (gate bi-ramo), e accetta un 5°
--   parametro p_flusso_id (D-B, flusso_id sul link COLLEGATO). Prima la
--   transizione EVASO era una chiamata separata (non atomica) del service.
--
-- Scope test: righe NON composite (ramo BoM compositi coperto altrove).
--
-- Indice test (1..8):
--   1) la funzione esiste con 5 parametri (era 4 + p_flusso_id)
--   2) push preventivo ACCETTATO -> ammesso (lives)
--   3) creato un ordine con documento_origine=(PREVENTIVO, id)
--   4) la riga ordine e' collegata alla riga preventivo (preventivo_riga_id)
--   5) il preventivo e' transitato ad EVASO nella STESSA chiamata (fix #10)
--   6) re-push (preventivo ora EVASO) -> E_..._PUSH_STATO_NON_AMMESSO
--   7) preventivo DRAFT -> E_..._PUSH_STATO_NON_AMMESSO
--   8) ATOMICITA': se la transizione EVASO fallisce, l'ordine NON resta creato
--
-- Nota flusso_id (D-B): la valorizzazione di pratiche_sorgenti.flusso_id sul
-- link COLLEGATO (ramo p_pratica_id NOT NULL) e' presidiata dal guard
-- trgfn_pratiche_sorgenti_guard_coerenza_flusso e verificata end-to-end
-- nell'integrazione BE (richiede un contesto pratica+flusso valido, oneroso da
-- riprodurre in isolamento per via dei guard su pratiche.flussi).
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

SELECT plan(11);

-- ============================================================
-- 1) Firma funzione: 5 parametri
-- ============================================================
SELECT ok(
  (SELECT p.pronargs = 5
     FROM pg_proc p
     JOIN pg_namespace n ON n.oid = p.pronamespace
    WHERE n.nspname = 'vendite'
      AND p.proname = 'fn_push_preventivo_a_ordine'
    LIMIT 1),
  '1) vendite.fn_push_preventivo_a_ordine esiste con 5 parametri (+ p_flusso_id)'
);

-- ============================================================
-- Fixture: riferimenti + articolo MERCE non composito
-- ============================================================
-- ⭐ rev 2026-10-24 (Q-2/Q-4): i tre preventivi nascono qui, in bozza, dal
--   builder (azienda dell'operatore, un cliente costruito per ciascuno: il
--   test non dipende dal cliente). ⛔ Cio' che il builder scrive si legge in
--   un'istruzione SEPARATA.
CREATE TEMP TABLE tmp_prev_b AS
SELECT * FROM dbops.fn_pgtap_crea_preventivo('push ordine');
CREATE TEMP TABLE tmp_prev_draft_b AS
SELECT * FROM dbops.fn_pgtap_crea_preventivo('push ordine draft');
CREATE TEMP TABLE tmp_prev_atom_b AS
SELECT * FROM dbops.fn_pgtap_crea_preventivo('push ordine atom');

CREATE TEMP TABLE tmp_refs AS
SELECT
  -- ⛔ rev 2026-10-24: l'articolo si COSTRUISCE, MERCE (destinazione ORDINE)
  --   non composito, con la natura alla nascita. Prima era «il primo per id»
  --   del catalogo, ricollocato a MERCE con un UPDATE: da zero il primo e' un
  --   onere, e un onere non puo' essere merce.
  dbops.fn_pgtap_crea_articolo('PGT-PUSHORD-MERCE', false,
      p_natura_vendita_id => (SELECT id FROM config.nature_vendita
                               WHERE codice_interno = 'MERCE')) AS articolo_id,
  (SELECT s.id FROM config.stati_doc_preventivi s
    WHERE s.codice_interno = 'EVASO' AND s.attivo IS TRUE) AS stato_evaso_id,
  (SELECT i.id FROM config.iva i WHERE i.attivo IS TRUE ORDER BY i.id LIMIT 1) AS iva_id;

-- Preventivo ACCETTATO + 1 riga MERCE (percorso happy).
-- ⚠️ rev 2026-10-08 (brief-db-righe-e-componenti-debiti-residui, D-1): i due
--   preventivi ACCETTATO (happy e atomicita') nascono DRAFT, prendono la riga,
--   poi passano ad ACCETTATO con dbops.fn_pgtap_porta_a_stato — fuori bozza le
--   righe non si scrivono piu' (20261008-91).
CREATE TEMP TABLE tmp_prev AS
SELECT b.preventivo_id AS id, b.preventivo_uid AS uid FROM tmp_prev_b b;

CREATE TEMP TABLE tmp_riga AS
WITH ins AS (
  INSERT INTO vendite.preventivi_righe (
    preventivo_id, articolo_id, qta_operativa, prezzo_unitario, iva_id, attivo, meta)
  SELECT p.id, r.articolo_id, 4.000000, 25.500000, r.iva_id, true,
         jsonb_build_object('test_scope','pgtap_push_ordine')
    FROM tmp_prev p, tmp_refs r
  RETURNING id
)
SELECT * FROM ins;

DO $x$ BEGIN
  PERFORM dbops.fn_pgtap_porta_a_stato('vendite.preventivi', (SELECT id FROM tmp_prev), 'ACCETTATO');
END $x$;

-- Preventivo DRAFT (per test 7).
CREATE TEMP TABLE tmp_prev_draft AS
SELECT b.preventivo_id AS id FROM tmp_prev_draft_b b;

-- Preventivo ACCETTATO + riga MERCE dedicato al test di atomicita' (8).
CREATE TEMP TABLE tmp_prev_atom AS
SELECT b.preventivo_id AS id FROM tmp_prev_atom_b b;

INSERT INTO vendite.preventivi_righe (
    preventivo_id, articolo_id, qta_operativa, prezzo_unitario, iva_id, attivo, meta)
SELECT p.id, r.articolo_id, 2.000000, 10.000000, r.iva_id, true,
       jsonb_build_object('test_scope','pgtap_push_ordine_atom')
  FROM tmp_prev_atom p, tmp_refs r;

DO $x$ BEGIN
  PERFORM dbops.fn_pgtap_porta_a_stato('vendite.preventivi', (SELECT id FROM tmp_prev_atom), 'ACCETTATO');
END $x$;

-- ============================================================
-- 2) Push preventivo ACCETTATO -> ammesso
-- ============================================================
SELECT lives_ok(
  format('SELECT vendite.fn_push_preventivo_a_ordine(%s)',
         (SELECT id FROM tmp_prev)),
  '2) push preventivo ACCETTATO -> ammesso'
);

-- ============================================================
-- 3) Ordine creato con documento_origine = (PREVENTIVO, id)
-- ============================================================
SELECT ok(
  EXISTS(SELECT 1 FROM vendite.ordini o
          WHERE o.documento_origine_tipo = 'PREVENTIVO'
            AND o.documento_origine_id = (SELECT id FROM tmp_prev)),
  '3) creato ordine con documento_origine=(PREVENTIVO, id)'
);

-- ============================================================
-- 4) La riga ordine e' collegata alla riga preventivo
-- ============================================================
SELECT is(
  (SELECT count(*) FROM vendite.ordini_righe orr
    WHERE orr.preventivo_riga_id = (SELECT id FROM tmp_riga)),
  1::bigint,
  '4) riga ordine collegata alla riga preventivo (preventivo_riga_id)'
);

-- ============================================================
-- 5) Il preventivo e' transitato ad EVASO nella STESSA chiamata (fix #10)
-- ============================================================
SELECT is(
  (SELECT stato_doc_preventivo_id FROM vendite.preventivi WHERE id = (SELECT id FROM tmp_prev)),
  (SELECT stato_evaso_id FROM tmp_refs),
  '5) preventivo transitato ad EVASO atomicamente (gate bi-ramo, nessun residuo)'
);

-- ============================================================
-- 6) Re-push (preventivo ora EVASO) -> stato non ammesso
-- ============================================================
SELECT throws_like(
  format('SELECT vendite.fn_push_preventivo_a_ordine(%s)',
         (SELECT id FROM tmp_prev)),
  '%ACCETTATO%',
  '6) re-push su preventivo EVASO -> E_VENDITA_PREVENTIVO_PUSH_STATO_NON_AMMESSO'
);

-- ============================================================
-- 7) Preventivo non ACCETTATO (DRAFT) -> stato non ammesso
-- ============================================================
SELECT throws_like(
  format('SELECT vendite.fn_push_preventivo_a_ordine(%s)',
         (SELECT id FROM tmp_prev_draft)),
  '%ACCETTATO%',
  '7) preventivo DRAFT -> E_VENDITA_PREVENTIVO_PUSH_STATO_NON_AMMESSO'
);

-- ============================================================
-- 8) ATOMICITA': la transizione EVASO fallisce (trigger iniettato sull'UPDATE
--    preventivi) => l'ordine appena creato NON deve restare (rollback totale).
-- ============================================================
CREATE FUNCTION pg_temp.pgtap_fail_evaso() RETURNS trigger
    LANGUAGE plpgsql AS $f$
BEGIN
    RAISE EXCEPTION 'pgtap: fallimento iniettato sulla transizione EVASO';
END;
$f$;

-- ⚠️ CREATE/DROP TRIGGER prendono un lock su vendite.preventivi (il DROP
--   ACCESS EXCLUSIVE) tenuto fino al ROLLBACK. Se un'altra sessione ha una
--   transazione aperta che ha letto o scritto preventivi, il test resterebbe
--   in attesa fino al timeout del runner — e intanto metterebbe in coda dietro
--   di se' chiunque usi la tabella, app compresa. Con lock_timeout l'attesa
--   diventa un errore immediato e leggibile («lock timeout»), non uno stallo.
SET LOCAL lock_timeout = '5s';

CREATE TRIGGER zzz_pgtap_fail_evaso
    BEFORE UPDATE ON vendite.preventivi
    FOR EACH ROW EXECUTE FUNCTION pg_temp.pgtap_fail_evaso();

SELECT throws_like(
  format('SELECT vendite.fn_push_preventivo_a_ordine(%s)',
         (SELECT id FROM tmp_prev_atom)),
  '%fallimento iniettato sulla transizione EVASO%',
  '8a) la transizione EVASO fallita fa fallire l''intera chiamata'
);

DROP TRIGGER zzz_pgtap_fail_evaso ON vendite.preventivi;
RESET lock_timeout;

SELECT is(
  (SELECT count(*) FROM vendite.ordini o
    WHERE o.documento_origine_tipo = 'PREVENTIVO'
      AND o.documento_origine_id = (SELECT id FROM tmp_prev_atom)),
  0::bigint,
  '8b) nessun ordine orfano: la creazione e'' stata annullata con la transizione'
);

-- ============================================================
-- 10-11) ⭐ IL BERSAGLIO, E PER UID.
--   ⚠️ CORRETTO IL 2026-08-24 su rilievo del backend: si cita per **ID**, non
--   per uid. Le rotte del preventivo sono <int:preventivo_id> e gli endpoint
--   che accettano un uid sono ZERO — l'uid avrebbe prodotto un pulsante che non
--   apre niente. ⭐ config.tipi_entita.key_selector si MISURA sulle rotte: non
--   si eredita da config.sorgenti, che si chiama uguale ma risponde a un'altra
--   domanda (con quale chiave il lineage collega il documento).
--   ⛔ Il test 11 e' l'altra meta' della regola: su un preventivo che NON
--   esiste il messaggio esce lo stesso ma il bersaglio no — un'offerta, non
--   una promessa.
--   ⚠️ Nella frase resta l'id numerico, ed e' voluto: due canali, due lettori.
--   Brief: brief-db-bersaglio-errore §6 L6.
--   ⚠️ CORRETTO IL 2026-10-05: il test 11 passava `-1`, che si ferma al guard
--   d'ingresso (p_preventivo_id <= 0 -> E_VALIDAZIONE, senza bersaglio) e non
--   arriva mai al ramo «preventivo che non esiste»: verde per il motivo
--   sbagliato. Ora usa un id positivo che nessuna identity raggiunge, e
--   ciascun test asserisce anche il CODICE, cosi' un rifiuto da un altro
--   ramo non puo' piu' farlo passare.
-- ============================================================
CREATE OR REPLACE FUNCTION pg_temp.push_prev_bersaglio(p_prev_id bigint)
RETURNS text AS $fn$
-- ⚠️ `text` esplicito: sono due canali dell'eccezione (codice | bersaglio),
--   non il valore di una colonna.
DECLARE v_codice text;
        v_bers   text;
BEGIN
  PERFORM vendite.fn_push_preventivo_a_ordine(p_prev_id);
  RETURN 'NESSUN ERRORE';
EXCEPTION WHEN OTHERS THEN
  GET STACKED DIAGNOSTICS v_codice = CONSTRAINT_NAME,
                          v_bers   = PG_DATATYPE_NAME;
  RETURN COALESCE(v_codice, '') || '|' || COALESCE(v_bers, '');
END $fn$ LANGUAGE plpgsql;

CREATE TEMP TABLE tmp_prev_bersaglio AS
SELECT pg_temp.push_prev_bersaglio((SELECT id FROM tmp_prev_draft))     AS esistente,
       -- bigint massimo: positivo (supera il guard d'ingresso) e mai assegnato.
       pg_temp.push_prev_bersaglio(9223372036854775807::bigint)         AS inesistente;

SELECT is(
  (SELECT esistente FROM tmp_prev_bersaglio),
  'E_VENDITA_PREVENTIVO_PUSH_STATO_NON_AMMESSO|PREVENTIVO:'
    || (SELECT id FROM tmp_prev_draft)::text,
  '10) il rifiuto porta il bersaglio sul preventivo, e lo cita per ID (non uid)'
);

SELECT is(
  (SELECT inesistente FROM tmp_prev_bersaglio),
  'E_VENDITA_PREVENTIVO_PUSH_STATO_NON_AMMESSO|',
  '11) preventivo inesistente: il messaggio esce, il bersaglio no'
);

SELECT * FROM finish();
ROLLBACK;
