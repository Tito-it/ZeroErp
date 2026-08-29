-- ------------------------------------------------------------
-- SPDX-License-Identifier: GPL-3.0-or-later
-- pgTAP test per Zero ERP
-- Test: script.fn_check_ordine_confermabile + Regola 4 di
--       vendite.trgfn_ordini_guard_transizione + lato lettura
--       script.fn_available_actions_ordine   (I9 / §R-3)
-- ------------------------------------------------------------
-- Elenco test (plan 8):
-- 0) riferimenti minimi presenti                        (fixture non muta)
-- 1) riga CON aliquota -> la fn pura non trova motivi
-- 2) riga SENZA aliquota -> un motivo, col codice giusto
-- 3) il motivo porta il NUMERO di riga nel dettaglio     (frase per una persona)
-- 4) fn_available_actions_ordine: il bottone conferma e' spento, con la reason
-- 5) ⭐ DRAFT->CONFERMATO con riga senza aliquota -> BLOCCA
-- 6) controllo: la stessa transizione con l'aliquota -> PASSA
-- 7) ⭐ il perimetro: EVASO->CONFERMATO con riga senza aliquota -> BLOCCA
--
-- Scopo:
--   Il difetto che I9 chiude e' SILENZIOSO: vendite.vw_ordini_righe_iva_base
--   filtra solo `attivo IS TRUE AND quantita > 0` — non guarda ne' il prezzo ne'
--   l'iva_id — e vw_ordini_riepilogo_iva_dettaglio aggrega da li' con
--   COALESCE(aliquota, 0). Una riga senza aliquota entra quindi nel riepilogo
--   con l'imponibile PIENO e l'imposta a ZERO, su un ordine confermato e
--   stampato. Nessun errore, nessun sintomo: solo un numero sbagliato.
--
--   ⭐ IL TEST 7 E' QUELLO CHE NESSUNO PENSEREBBE DI SCRIVERE, ed e' la
--   differenza fra la Regola 4 e la Regola 2 che le sta accanto. La Regola 2
--   («almeno una riga attiva») vale solo su DRAFT->CONFERMATO; la Regola 4 vale
--   su QUALUNQUE ingresso in CONFERMATO, perche' la matrice ammette il rientro
--   da PARZIALMENTE_EVASO e da EVASO e la vista del riepilogo non sa da dove si
--   arriva. Con un perimetro copiato dalla Regola 2, un ordine che rientra da
--   EVASO passerebbe — e il riepilogo sarebbe storto per la via di servizio.
--
--   ⚠️ Il test 6 non e' un doppione del 5 al contrario: senza, un rosso del 4
--   potrebbe venire dalla fixture (un permesso, un altro guard, la matrice)
--   invece che dalla regola che si vuole provare.
--
--   Piano: docs/it/dev/work-in-progress/brief-db-be-iva-risolutore-e-regime-cliente.md
--     I9 / §R-3 · changeSet 20260829-06 (fn pura), -07 (guard), -08 (capability)
-- ------------------------------------------------------------

-- ⚠️ 1. TRANSAZIONE: senza, un fallimento a meta' lascia la fixture nel database.
BEGIN;

-- ⚠️ 2. CONTESTO APPLICATIVO: il test gira come gira l'applicazione (ruolo
--   OPERATORE + RLS attiva), non come owner. Senza una veste dichiarata le
--   policy sono fail-closed e la fixture leggerebbe zero righe.
DO $ctx$ BEGIN PERFORM script.fn_pgtap_set_contesto_operatore(); END $ctx$;

-- ⚠️ 3. VINCOLI DIFFERITI: qui il COMMIT non arriva mai, quindi senza questa
--   riga i DEFERRABLE non verrebbero esercitati.
SET CONSTRAINTS ALL IMMEDIATE;

SELECT plan(8);

-- ============================================================
-- 0) Riferimenti
-- ============================================================
-- ⚠️ L'EMITTENTE NON SI PESCA, SI DERIVA, e qui la catena la impone il guard:
--   vendite.trgfn_ordini_guard_emittente_ba pretende
--   emittente_fiscale_id = anagrafiche.fn_get_emittente_fiscale_pk(billing_account_id).
--   Scegliendo l'emittente per conto proprio il test si fermerebbe su
--   E_ORDINE_EMITTENTE_BA_INCOERENTE, cioe' su un rosso che non c'entra nulla
--   con la regola in prova. Anche `soggetto_ruolo_id` viene dal BA, per lo
--   stesso motivo di coerenza.
-- ⚠️ Il BA si sceglie SOTTO la veste dell'operatore, quindi la RLS ha gia'
--   filtrato: qualunque riga esca e' nel perimetro di chi agisce. ⛔ Non si
--   svuota `app.current_user_id` per allargare la vista — non e' fail-closed, e
--   renderebbe il test cieco proprio sulle policy.
-- ⚠️ Ogni LIMIT 1 ha il suo ORDER BY: senza, quale riga esca dipende dal piano
--   del planner e il test passerebbe a giorni alterni. E il BA si sceglie UNA
--   volta in una CTE: due sotto-select indipendenti potrebbero pescarne due
--   diversi, e id ed emittente non apparterrebbero allo stesso.
CREATE TEMP TABLE tmp_oi_refs AS
WITH ba AS (
  SELECT b.id, b.soggetto_ruolo_id
    FROM anagrafiche.billing_account b
   WHERE b.utility_id IS NOT NULL
     AND b.istanza_utility_id IS NOT NULL
     AND anagrafiche.fn_get_emittente_fiscale_pk(b.id) IS NOT NULL
   ORDER BY b.id
   LIMIT 1
)
SELECT (SELECT id FROM ba)                                    AS billing_account_id,
       (SELECT soggetto_ruolo_id FROM ba)                     AS soggetto_ruolo_id,
       anagrafiche.fn_get_emittente_fiscale_pk((SELECT id FROM ba)) AS emittente_fiscale_id,
       (SELECT a.id FROM catalogo.articoli a
         WHERE a.attivo IS TRUE
           AND COALESCE(a.is_composito, FALSE) IS FALSE
         ORDER BY a.id LIMIT 1)                               AS articolo_id,
       (SELECT v.id FROM config.valute v ORDER BY v.id LIMIT 1) AS valuta_id,
       (SELECT i.id FROM config.iva i
         WHERE i.attivo IS TRUE ORDER BY i.id LIMIT 1)        AS iva_id,
       (SELECT s.id FROM config.stati_doc_ordini s
         WHERE s.codice_interno = 'DRAFT' ORDER BY s.id LIMIT 1)      AS stato_draft_id,
       (SELECT s.id FROM config.stati_doc_ordini s
         WHERE s.codice_interno = 'CONFERMATO' ORDER BY s.id LIMIT 1) AS stato_conf_id,
       (SELECT s.id FROM config.stati_doc_ordini s
         WHERE s.codice_interno = 'EVASO' ORDER BY s.id LIMIT 1)      AS stato_evaso_id;

SELECT ok(
    (SELECT billing_account_id IS NOT NULL AND soggetto_ruolo_id IS NOT NULL
        AND emittente_fiscale_id IS NOT NULL
        AND articolo_id IS NOT NULL AND valuta_id IS NOT NULL AND iva_id IS NOT NULL
        AND stato_draft_id IS NOT NULL AND stato_conf_id IS NOT NULL
        AND stato_evaso_id IS NOT NULL
       FROM tmp_oi_refs),
    'Riferimenti minimi presenti'
  );

-- ============================================================
-- Fixture: un ordine in DRAFT con UNA riga attiva
-- ============================================================
-- ⚠️ Padre e figlio in DUE istruzioni, non in una CTE sola: le CTE che scrivono
--   condividono la stessa snapshot, e una policy che risolve il perimetro dal
--   padre non lo troverebbe, negando fail-closed.
CREATE TEMP TABLE tmp_oi_ordine AS
WITH ins AS (
  INSERT INTO vendite.ordini (soggetto_ruolo_id, billing_account_id,
                              stato_doc_ordine_id, valuta_id, data,
                              fatturazione_trigger, emittente_fiscale_id,
                              storicizza, meta)
  SELECT r.soggetto_ruolo_id, r.billing_account_id, r.stato_draft_id,
         r.valuta_id, current_date, 'SPEDITO', r.emittente_fiscale_id, false,
         jsonb_build_object('test_scope', 'pgtap_ordine_conferma_iva')
    FROM tmp_oi_refs r
  RETURNING id
)
SELECT * FROM ins;

-- La riga nasce SENZA aliquota: e' il caso da provare.
-- ⚠️ `prezzo_unitario` e' NOT NULL su vendite.ordini_righe, quindi ogni riga
--   porta per forza un prezzo: qui la condizione «con prezzo» della regola e'
--   soddisfatta senza doverla costruire.
INSERT INTO vendite.ordini_righe (ordine_id, riga_nr, articolo_id, descrizione,
                                  qta_operativa, quantita, prezzo_unitario,
                                  iva_id, attivo, storicizza, meta)
SELECT (SELECT id FROM tmp_oi_ordine), 1, r.articolo_id, 'Riga di prova I9',
       2.000000, 2.000000, 100.000000, NULL, true, false,
       jsonb_build_object('test_scope', 'pgtap_ordine_conferma_iva')
  FROM tmp_oi_refs r;

-- ============================================================
-- 1-3) La funzione pura
-- ============================================================
-- Prima il caso SANO: con l'aliquota non ci sono motivi.
UPDATE vendite.ordini_righe
   SET iva_id = (SELECT iva_id FROM tmp_oi_refs)
 WHERE ordine_id = (SELECT id FROM tmp_oi_ordine);

SELECT is(
    script.fn_check_ordine_confermabile((SELECT id FROM tmp_oi_ordine)),
    '[]'::jsonb,
    'Riga CON aliquota: nessun motivo ostativo alla conferma'
  );

-- Poi il caso da bloccare.
UPDATE vendite.ordini_righe
   SET iva_id = NULL
 WHERE ordine_id = (SELECT id FROM tmp_oi_ordine);

SELECT is(
    script.fn_check_ordine_confermabile((SELECT id FROM tmp_oi_ordine)) -> 0 ->> 'codice',
    'E_ORDINE_RIGA_IVA_MANCANTE',
    'Riga SENZA aliquota: un motivo, ed e'' quello giusto'
  );

-- ⚠️ Nel dettaglio deve esserci il NUMERO di riga e non solo l'id: e' il valore
--   che finisce nel VARIADIC, cioe' nella frase che legge una persona. Un id
--   tecnico non si cerca a mano su un documento.
SELECT is(
    script.fn_check_ordine_confermabile((SELECT id FROM tmp_oi_ordine))
      -> 0 -> 'dettaglio' ->> 'riga_nr',
    '1',
    'Il motivo porta il NUMERO di riga, non il solo id'
  );

-- ============================================================
-- 4) Il lato lettura: il bottone e' spento, e dice perche'
-- ============================================================
-- ⭐ Se bastasse il guard, l'operatore vedrebbe un bottone ACCESO e prenderebbe
--   un errore al click. Guard e capability devono dire la stessa cosa: e' il
--   motivo per cui leggono la STESSA funzione pura.
-- ⚠️ Si guarda QUI, con l'ordine ancora in DRAFT, e non dopo le transizioni:
--   fn_available_actions_ordine elenca solo le transizioni che la matrice
--   dichiara MANUALI (`meta ? 'action_key'`), e l'unica verso CONFERMATO che
--   ha un action_key e' quella da DRAFT. I rientri da EVASO e da
--   PARZIALMENTE_EVASO sono transizioni di sistema: non hanno bottone, e
--   cercarne la reason avrebbe risposto NULL a prescindere dalla regola.
SELECT is(
    (SELECT a ->> 'reason'
       FROM jsonb_array_elements(
              script.fn_available_actions_ordine((SELECT id FROM tmp_oi_ordine))
                -> 'available_actions') a
      WHERE a ->> 'target_state' = 'CONFERMATO'),
    'RIGA_SENZA_ALIQUOTA',
    'Il bottone conferma e'' spento ed espone la reason della riga senza aliquota'
  );

-- ============================================================
-- 5-6) Il guard: DRAFT -> CONFERMATO
-- ============================================================
-- ⚠️ throws_like e NON throws_ok(...,'P0001'): su questa transizione il guard sa
--   sollevare anche E_ORDINE_CONFERMA_SENZA_RIGHE (Regola 2), e P0001 direbbe
--   solo «e' un errore di dominio», non QUALE. Il discriminante e' la frase.
-- ⚠️ Il pattern non attraversa i segnaposto: «Ordine %s: la riga %s ha un
--   prezzo...» si matcha sul frammento stabile, mai sulla frase intera.
SELECT throws_like(
    format('UPDATE vendite.ordini SET stato_doc_ordine_id = %s WHERE id = %s',
           (SELECT stato_conf_id FROM tmp_oi_refs),
           (SELECT id FROM tmp_oi_ordine)),
    '%prezzo ma nessuna aliquota IVA%',
    'DRAFT->CONFERMATO con una riga senza aliquota: BLOCCA'
  );

-- Controllo: con l'aliquota la stessa identica transizione passa. Senza questo,
-- un rosso del test 4 potrebbe venire dalla fixture invece che dalla regola.
UPDATE vendite.ordini_righe
   SET iva_id = (SELECT iva_id FROM tmp_oi_refs)
 WHERE ordine_id = (SELECT id FROM tmp_oi_ordine);

SELECT lives_ok(
    format('UPDATE vendite.ordini SET stato_doc_ordine_id = %s WHERE id = %s',
           (SELECT stato_conf_id FROM tmp_oi_refs),
           (SELECT id FROM tmp_oi_ordine)),
    'DRAFT->CONFERMATO con l''aliquota: PASSA'
  );

-- ============================================================
-- 7) ⭐ Il perimetro: anche il RIENTRO da EVASO passa dal controllo
-- ============================================================
-- L'ordine e' ora CONFERMATO. Lo si porta a EVASO (transizione lecita), gli si
-- toglie l'aliquota, e si prova a farlo rientrare in CONFERMATO.
-- ⛔ Con un perimetro copiato dalla Regola 2 — che guarda solo
--   DRAFT->CONFERMATO — questa transizione passerebbe, e il riepilogo sarebbe
--   storto per la via di servizio.
UPDATE vendite.ordini
   SET stato_doc_ordine_id = (SELECT stato_evaso_id FROM tmp_oi_refs)
 WHERE id = (SELECT id FROM tmp_oi_ordine);

UPDATE vendite.ordini_righe
   SET iva_id = NULL
 WHERE ordine_id = (SELECT id FROM tmp_oi_ordine);

SELECT throws_like(
    format('UPDATE vendite.ordini SET stato_doc_ordine_id = %s WHERE id = %s',
           (SELECT stato_conf_id FROM tmp_oi_refs),
           (SELECT id FROM tmp_oi_ordine)),
    '%prezzo ma nessuna aliquota IVA%',
    'EVASO->CONFERMATO con una riga senza aliquota: BLOCCA anche al rientro'
  );

SELECT * FROM finish();
ROLLBACK;
