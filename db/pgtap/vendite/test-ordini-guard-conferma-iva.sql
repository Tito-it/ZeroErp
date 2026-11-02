-- ------------------------------------------------------------
-- SPDX-License-Identifier: AGPL-3.0-or-later
-- rev 2026-10-25 (brief-modello-documento-vendita §9): l'ordine ha la porta sulla colonna di stato e
--   la conferma chiede emetti_ordine. L'azione si concede all'operatore del contesto prima del test 4
--   (senza, la capability nasconde «Conferma» e la reason esce NULL); i test 5 e 6 passano dal
--   verbo vendite.fn_cambia_stato_ordine, che arriva al guard (prima UPDATE diretti, ora fermati
--   dalla porta). Stessi esiti attesi.
-- rev 2026-10-25 (brief-db-pgtap-reso-costruito, giro D-4): la testata in bozza da dbops.fn_pgtap_crea_ordine sul BA costruito (il trigger SPEDITO scritto in bozza); la riga SENZA aliquota resta a mano: e' il caso.
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
--    ⚠️ SKIP motivato dal 2026-10-08: il caso non si costruisce piu' (righe d'ordine solo in bozza)
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
--   Piano: brief-db-be-iva-risolutore-e-regime-cliente.md
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

SELECT plan(9);

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
-- ⛔ rev 2026-10-13: il mondo si COSTRUISCE (su un DB ricostruito anagrafiche e
--   articoli sono vuoti): il cliente fatturabile nasce qui, legato all'azienda
--   di chi agisce, e l'articolo e' merce non gestita a magazzino. Dal DB si
--   legge solo il seed; l'emittente resta DERIVATO dal BA costruito.
CREATE TEMP TABLE tmp_oi_mondo AS
SELECT * FROM dbops.fn_pgtap_crea_mondo_cliente('pgTAP conferma ordine IVA');
CREATE TEMP TABLE tmp_oi_art AS
SELECT dbops.fn_pgtap_crea_articolo('PGT-OCI-V1', false) AS id;

CREATE TEMP TABLE tmp_oi_refs AS
WITH ba AS (
  SELECT m.billing_account_id AS id, m.cliente_soggetto_ruolo_id AS soggetto_ruolo_id
    FROM tmp_oi_mondo m
)
SELECT (SELECT id FROM ba)                                    AS billing_account_id,
       (SELECT soggetto_ruolo_id FROM ba)                     AS soggetto_ruolo_id,
       anagrafiche.fn_get_emittente_fiscale_pk((SELECT id FROM ba)) AS emittente_fiscale_id,
       (SELECT t.id FROM tmp_oi_art t)                        AS articolo_id,
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
-- La testata sola dal builder, in bozza, sul BA costruito (cliente ed emittente
--   derivati dal BA). La riga no: e' il caso, e non deve portare l'aliquota che
--   dbops.fn_pgtap_crea_ordine_con_righe le darebbe.
-- ⚠️ Padre e figlio in DUE istruzioni, non in una CTE sola: le CTE che scrivono
--   condividono la stessa snapshot, e una policy che risolve il perimetro dal
--   padre non lo troverebbe, negando fail-closed.
CREATE TEMP TABLE tmp_oi_ordine AS
SELECT * FROM dbops.fn_pgtap_crea_ordine('ordine_conferma_iva', 'DRAFT',
    (SELECT billing_account_id FROM tmp_oi_refs));

-- Il trigger di fatturazione e' una condizione della bozza.
UPDATE vendite.ordini
   SET fatturazione_trigger = 'SPEDITO'
 WHERE id = (SELECT ordine_id FROM tmp_oi_ordine);

-- La riga nasce SENZA aliquota: e' il caso da provare.
-- ⚠️ `prezzo_unitario` e' NOT NULL su vendite.ordini_righe, quindi ogni riga
--   porta per forza un prezzo: qui la condizione «con prezzo» della regola e'
--   soddisfatta senza doverla costruire.
INSERT INTO vendite.ordini_righe (ordine_id, riga_nr, articolo_id, descrizione,
                                  qta_operativa, quantita, prezzo_unitario,
                                  iva_id, attivo, storicizza, meta)
SELECT (SELECT ordine_id FROM tmp_oi_ordine), 1, r.articolo_id, 'Riga di prova I9',
       2.000000, 2.000000, 100.000000, NULL, true, false,
       jsonb_build_object('test_scope', 'pgtap_ordine_conferma_iva')
  FROM tmp_oi_refs r;

-- ============================================================
-- 1-3) La funzione pura
-- ============================================================
-- Prima il caso SANO: con l'aliquota non ci sono motivi.
UPDATE vendite.ordini_righe
   SET iva_id = (SELECT iva_id FROM tmp_oi_refs)
 WHERE ordine_id = (SELECT ordine_id FROM tmp_oi_ordine);

SELECT is(
    script.fn_check_ordine_confermabile((SELECT ordine_id FROM tmp_oi_ordine)),
    '[]'::jsonb,
    'Riga CON aliquota: nessun motivo ostativo alla conferma'
  );

-- Poi il caso da bloccare.
UPDATE vendite.ordini_righe
   SET iva_id = NULL
 WHERE ordine_id = (SELECT ordine_id FROM tmp_oi_ordine);

SELECT is(
    script.fn_check_ordine_confermabile((SELECT ordine_id FROM tmp_oi_ordine)) -> 0 ->> 'codice',
    'E_ORDINE_RIGA_IVA_MANCANTE',
    'Riga SENZA aliquota: un motivo, ed e'' quello giusto'
  );

-- ⚠️ Nel dettaglio deve esserci il NUMERO di riga e non solo l'id: e' il valore
--   che finisce nel VARIADIC, cioe' nella frase che legge una persona. Un id
--   tecnico non si cerca a mano su un documento.
SELECT is(
    script.fn_check_ordine_confermabile((SELECT ordine_id FROM tmp_oi_ordine))
      -> 0 -> 'dettaglio' ->> 'riga_nr',
    '1',
    'Il motivo porta il NUMERO di riga, non il solo id'
  );

-- ⭐ P-1 — LA FRASE RESA. E' l'unica verifica che vede l'ORDINE dei valori:
--   il ramo C di test-catalogo-messaggi-errore-completo.sql prova che sono
--   TANTI QUANTI i segnaposto, non che siano quelli giusti al posto giusto.
--   Il precedente e' del 2026-09-01 su E_REGISTRO_SERIE_NON_AMMESSA — due
--   valori, due segnaposto, «Registro X1» a video con la serie al posto della
--   famiglia — e nel 2026-09-09 lo stesso difetto e' stato trovato VIVO su due
--   siti di questo cantiere.
-- ⚠️ Si confronta con la frase composta dai valori letti dalla TABELLA: se la
--   check li emettesse invertiti, le due stringhe divergerebbero. Un `matches`
--   su un pezzo di frase non lo vedrebbe.
-- ⚠️ Il CASE con `coalesce` non e' pignoleria: senza, una check che smettesse
--   di emettere `valori` farebbe alzare 22023 a format() e ABORTIREBBE il file.
--   E scritto con un `<>` nudo non guarderebbe niente: `jsonb_typeof(NULL) <>
--   'array'` vale NULL, non vero.
SELECT is(
  (WITH v AS (SELECT script.fn_check_ordine_confermabile((SELECT ordine_id FROM tmp_oi_ordine)) -> 0 AS motivo)
   SELECT CASE
            WHEN coalesce(jsonb_typeof(v.motivo -> 'valori'), 'assente') <> 'array'
              THEN '(la check non emette valori)'
            ELSE format(
                   (SELECT m.messaggio FROM config.messaggi_errore m
                     WHERE m.codice = 'E_ORDINE_RIGA_IVA_MANCANTE' AND m.lingua = 'it'),
                   VARIADIC ARRAY(SELECT jsonb_array_elements_text(v.motivo -> 'valori')))
          END
     FROM v),
  (SELECT format((SELECT m.messaggio FROM config.messaggi_errore m
                     WHERE m.codice = 'E_ORDINE_RIGA_IVA_MANCANTE' AND m.lingua = 'it'),
                 o.numero, '1')
     FROM vendite.ordini o WHERE o.id = (SELECT ordine_id FROM tmp_oi_ordine)),
  'La frase resa nomina il NUMERO dell''ordine e poi la RIGA, in quest''ordine'
  );

-- ============================================================
-- 4) Il lato lettura: il bottone e' spento, e dice perche'
-- ============================================================
-- rev 2026-10-25 (§9): permesso => nascondi. Senza emetti_ordine il bottone non
--   c'e' proprio; con l'azione c'e', ed e' spento dal motivo.
SELECT dbops.fn_pgtap_concedi_azione(current_setting('app.current_user_id')::integer, 'emetti_ordine');
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
              script.fn_available_actions_ordine((SELECT ordine_id FROM tmp_oi_ordine))
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
    format($q$SELECT * FROM vendite.fn_cambia_stato_ordine(%s, 'CONFERMATO')$q$,
           (SELECT ordine_id FROM tmp_oi_ordine)),
    '%prezzo ma nessuna aliquota IVA%',
    'DRAFT->CONFERMATO con una riga senza aliquota: BLOCCA'
  );

-- Controllo: con l'aliquota la stessa identica transizione passa. Senza questo,
-- un rosso del test 4 potrebbe venire dalla fixture invece che dalla regola.
UPDATE vendite.ordini_righe
   SET iva_id = (SELECT iva_id FROM tmp_oi_refs)
 WHERE ordine_id = (SELECT ordine_id FROM tmp_oi_ordine);

SELECT lives_ok(
    format($q$SELECT * FROM vendite.fn_cambia_stato_ordine(%s, 'CONFERMATO')$q$,
           (SELECT ordine_id FROM tmp_oi_ordine)),
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
-- ⚠️ rev 2026-10-08 (brief-db-righe-e-componenti-debiti-residui §4.5, decisione
--   di Tid): SKIP MOTIVATO. Il caso si costruiva togliendo l'aliquota a una
--   riga dell'ordine EVASO; da 20261008-90 le righe d'ordine fuori bozza non si
--   scrivono (E_RIGA_DOC_NON_BOZZA), e in bozza il caso non si prepara: una riga
--   senza aliquota non passa DRAFT->CONFERMATO (test 5 e 6). «EVASO con una riga
--   senza aliquota» non nasce piu' da nessuna porta del modello. La Regola 4 sul
--   rientro RESTA nel guard, come difesa in profondita': il test lo dichiara
--   invece di fingere un caso che il modello non produce, e non passa a vuoto.
SELECT skip(
    'EVASO->CONFERMATO con una riga senza aliquota: caso non costruibile dalle porte '
    'del modello da 20261008-90 (righe d''ordine solo in bozza); la Regola 4 sul '
    'rientro resta nel guard come difesa in profondita''',
    1);

SELECT * FROM finish();
ROLLBACK;