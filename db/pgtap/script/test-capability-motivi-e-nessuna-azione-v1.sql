-- ------------------------------------------------------------
-- SPDX-License-Identifier: GPL-3.0-or-later
-- pgTAP test per Zero ERP
--
-- Test: il PERCHE' arriva davvero all'operatore — le capability espongono i
--       motivi ostativi dell'annullamento e la nota degli stati chiusi.
--       Brief: brief-db-vie-uscita-operatore, §4 (regola R3) e §6 ultima riga.
--
-- PERCHE' QUESTO TEST ESISTE, VISTO CHE CE N'E' GIA' UNO.
-- config/test-transizioni-uscita-manuale-v1.sql verifica che il DATO ci sia:
-- che ogni stato o abbia un'uscita manuale, o dichiari nel `meta` la chiave
-- che spiega perche' non ce l'ha. Quel test era ed e' VERDE — eppure per un
-- giorno intero l'operatore ha visto una barra azioni vuota e muta su ogni
-- DDT consegnato, e il bottone «Annulla» ACCESO su preventivi che il guard
-- avrebbe rifiutato. Il dato c'era; nessuna funzione lo leggeva.
--
-- E' la differenza fra verificare una dichiarazione e verificare il percorso
-- che la attraversa. Il seed e' il primo anello, le fn_available_actions_*
-- sono l'ultimo prima dell'API: finche' nessuno prova l'ultimo, il verde del
-- primo non dice niente sull'operatore. Questo file prova l'ultimo.
--
-- COME SONO SCRITTE LE ASSERZIONI. Non su un documento scelto a mano ma sulla
-- POPOLAZIONE: «quanti violano la regola, su quanti esistono». Una fixture
-- costruita apposta puo' confermare un ramo morto; un conteggio di violazioni
-- su tutti i documenti reali no. Dove la popolazione puo' essere vuota il test
-- fa SKIP esplicito e lo dice: un verde per assenza di soggetti e' un verde
-- che non ha misurato niente, e deve vedersi.
--
-- Indice test (1..9):
--   1) Preflight: le 4 chiavi nessuna_azione_key sono a dato (senza, tutto
--      il resto sarebbe vacuo)
--   2) Preventivo: enabled dell'azione «annulla» == verdetto della fn pura,
--      su TUTTA la popolazione (la UI non puo' divergere dal guard)
--   3) Preventivo: quando e' spento, `reasons` riporta i motivi della fn pura
--      e `reason` e' il primo (contratto letto dal BB FE useDrawerActions)
--   4) Ordine: come 2
--   5) Ordine: come 3
--   6) Ordine EVASO / PARZIALMENTE_EVASO senza azioni vive -> nota esposta
--   7) DDT CONSEGNATO / RESO senza azioni vive -> nota esposta
--   8) Non-regressione: la nota NON compare dove resta un'azione abilitata
--   9) Non-regressione: il motivo `requires_righe` sopravvive alla somma dei
--      motivi (era l'unico prima di questo cantiere)
--
-- ⚠️ SE IL TEST 2 O IL 4 DIVENTA ROSSO non e' un dettaglio di UI: significa
-- che il bottone e il database non dicono piu' la stessa cosa, cioe' che
-- l'operatore puo' premere qualcosa che verra' rifiutato (o non premere
-- qualcosa che sarebbe lecito). La sede della regola e' UNA — le
-- script.fn_check_*_annullabile — e queste asserzioni sono cio' che impedisce
-- che ne nasca una seconda dentro la capability.
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

SELECT plan(9);

-- ============================================================
-- 1) Preflight: il dato su cui poggia tutto il resto.
--    4 chiavi: ordini EVASO / PARZIALMENTE_EVASO, ddt CONSEGNATO / RESO.
-- ============================================================
SELECT is(
    (SELECT count(*)::int FROM (
        SELECT 1 FROM config.stati_doc_ordini WHERE meta ? 'nessuna_azione_key'
        UNION ALL
        SELECT 1 FROM config.stati_doc_ddt    WHERE meta ? 'nessuna_azione_key'
     ) q),
    4,
    '1) preflight: le 4 nessuna_azione_key sono a dato (2 ordini + 2 ddt)');

-- ------------------------------------------------------------
-- Popolazioni: si calcolano UNA volta, cosi' i conteggi delle asserzioni e
-- quelli degli skip parlano degli stessi soggetti.
-- ------------------------------------------------------------
CREATE TEMP TABLE _cap_prev AS
SELECT p.id,
       (a->>'enabled')::boolean                                   AS cap_enabled,
       COALESCE(a->'reasons', '[]'::jsonb)                        AS cap_reasons,
       a->>'reason'                                               AS cap_reason,
       script.fn_check_preventivo_annullabile(p.id)               AS motivi_fn
  FROM vendite.preventivi p
  CROSS JOIN LATERAL jsonb_array_elements(
         script.fn_available_actions_preventivo(p.id)->'available_actions') a
 WHERE a->>'target_state' = 'ANNULLATO';

CREATE TEMP TABLE _cap_ord AS
SELECT o.id,
       (a->>'enabled')::boolean                                   AS cap_enabled,
       COALESCE(a->'reasons', '[]'::jsonb)                        AS cap_reasons,
       a->>'reason'                                               AS cap_reason,
       script.fn_check_ordine_annullabile(o.id)                   AS motivi_fn
  FROM vendite.ordini o
  CROSS JOIN LATERAL jsonb_array_elements(
         script.fn_available_actions_ordine(o.id)->'available_actions') a
 WHERE a->>'target_state' = 'ANNULLATO';

-- ============================================================
-- 2) Preventivo: capability == guard, su tutta la popolazione.
-- ============================================================
SELECT CASE WHEN (SELECT count(*) FROM _cap_prev) = 0
  THEN pass('2) SKIP: nessun preventivo con azione verso ANNULLATO (nulla da misurare)')
  ELSE is(
    (SELECT count(*)::int FROM _cap_prev
      WHERE cap_enabled IS DISTINCT FROM (jsonb_array_length(motivi_fn) = 0)),
    0,
    format('2) preventivo: enabled == verdetto di fn_check_preventivo_annullabile su %s documenti',
           (SELECT count(*) FROM _cap_prev)))
END;

-- ============================================================
-- 3) Preventivo: i motivi arrivano interi, e il singolare e' il primo.
--    E' il contratto che il BB FE legge (reasons vince, altrimenti reason).
-- ============================================================
SELECT CASE WHEN (SELECT count(*) FROM _cap_prev WHERE NOT cap_enabled) = 0
  THEN pass('3) SKIP: nessun preventivo con annullamento bloccato (nulla da misurare)')
  ELSE is(
    (SELECT count(*)::int FROM _cap_prev
      WHERE NOT cap_enabled
        AND (cap_reasons IS DISTINCT FROM motivi_fn
             OR cap_reason IS DISTINCT FROM (motivi_fn -> 0 ->> 'reason'))),
    0,
    format('3) preventivo: reasons == motivi della fn pura e reason == primo, su %s bloccati',
           (SELECT count(*) FROM _cap_prev WHERE NOT cap_enabled)))
END;

-- ============================================================
-- 4) Ordine: capability == guard.
-- ============================================================
SELECT CASE WHEN (SELECT count(*) FROM _cap_ord) = 0
  THEN pass('4) SKIP: nessun ordine con azione verso ANNULLATO (nulla da misurare)')
  ELSE is(
    (SELECT count(*)::int FROM _cap_ord
      WHERE cap_enabled IS DISTINCT FROM (jsonb_array_length(motivi_fn) = 0)),
    0,
    format('4) ordine: enabled == verdetto di fn_check_ordine_annullabile su %s documenti',
           (SELECT count(*) FROM _cap_ord)))
END;

-- ============================================================
-- 5) Ordine: i motivi arrivano interi.
-- ============================================================
SELECT CASE WHEN (SELECT count(*) FROM _cap_ord WHERE NOT cap_enabled) = 0
  THEN pass('5) SKIP: nessun ordine con annullamento bloccato (nulla da misurare)')
  ELSE is(
    (SELECT count(*)::int FROM _cap_ord
      WHERE NOT cap_enabled
        AND (cap_reasons IS DISTINCT FROM motivi_fn
             OR cap_reason IS DISTINCT FROM (motivi_fn -> 0 ->> 'reason'))),
    0,
    format('5) ordine: reasons == motivi della fn pura e reason == primo, su %s bloccati',
           (SELECT count(*) FROM _cap_ord WHERE NOT cap_enabled)))
END;

-- ------------------------------------------------------------
-- Stati chiusi: i documenti che NON hanno piu' nessuna azione abilitata sono
-- quelli a cui la nota deve arrivare. Chi ha ancora un bottone vivo non entra
-- nel conto — e' la regola del §4: la nota risponde alla lista vuota.
-- ------------------------------------------------------------
CREATE TEMP TABLE _cap_muti AS
SELECT 'ordine'::text AS doc, o.id,
       script.fn_available_actions_ordine(o.id)->>'nessuna_azione_key' AS nota,
       sdo.meta->>'nessuna_azione_key'                                 AS nota_attesa
  FROM vendite.ordini o
  JOIN config.stati_doc_ordini sdo ON sdo.id = o.stato_doc_ordine_id
 WHERE sdo.meta ? 'nessuna_azione_key'
   AND NOT EXISTS (
        SELECT 1 FROM jsonb_array_elements(
                        script.fn_available_actions_ordine(o.id)->'available_actions') a
         WHERE COALESCE((a->>'enabled')::boolean, true))
UNION ALL
SELECT 'ddt', d.id,
       script.fn_available_actions_ddt(d.id)->>'nessuna_azione_key',
       sdd.meta->>'nessuna_azione_key'
  FROM vendite.ddt d
  JOIN config.stati_doc_ddt sdd ON sdd.id = d.stato_doc_ddt_id
 WHERE sdd.meta ? 'nessuna_azione_key'
   AND NOT EXISTS (
        SELECT 1 FROM jsonb_array_elements(
                        script.fn_available_actions_ddt(d.id)->'available_actions') a
         WHERE COALESCE((a->>'enabled')::boolean, true));

-- ============================================================
-- 6) Ordine: la nota arriva, e con la chiave giusta.
-- ============================================================
SELECT CASE WHEN (SELECT count(*) FROM _cap_muti WHERE doc='ordine') = 0
  THEN pass('6) SKIP: nessun ordine in stato chiuso senza azioni vive')
  ELSE is(
    (SELECT count(*)::int FROM _cap_muti
      WHERE doc='ordine' AND nota IS DISTINCT FROM nota_attesa),
    0,
    format('6) ordine: nessuna_azione_key esposta e pari al meta dello stato, su %s documenti muti',
           (SELECT count(*) FROM _cap_muti WHERE doc='ordine')))
END;

-- ============================================================
-- 7) DDT: idem. E' la meta' del lavoro che il §6 del brief non nominava.
-- ============================================================
SELECT CASE WHEN (SELECT count(*) FROM _cap_muti WHERE doc='ddt') = 0
  THEN pass('7) SKIP: nessun DDT in stato chiuso senza azioni vive')
  ELSE is(
    (SELECT count(*)::int FROM _cap_muti
      WHERE doc='ddt' AND nota IS DISTINCT FROM nota_attesa),
    0,
    format('7) ddt: nessuna_azione_key esposta e pari al meta dello stato, su %s documenti muti',
           (SELECT count(*) FROM _cap_muti WHERE doc='ddt')))
END;

-- ============================================================
-- 8) Non-regressione: la nota non deve comparire accanto a un bottone vivo.
--    Se comparisse, l'operatore leggerebbe «non c'e' niente da fare» sopra
--    un'azione che puo' fare — peggio del silenzio.
-- ============================================================
SELECT is(
    (SELECT count(*)::int FROM (
        SELECT 1
          FROM vendite.ordini o
         WHERE script.fn_available_actions_ordine(o.id)->>'nessuna_azione_key' IS NOT NULL
           AND EXISTS (SELECT 1 FROM jsonb_array_elements(
                              script.fn_available_actions_ordine(o.id)->'available_actions') a
                        WHERE COALESCE((a->>'enabled')::boolean, true))
        UNION ALL
        SELECT 1
          FROM vendite.ddt d
         WHERE script.fn_available_actions_ddt(d.id)->>'nessuna_azione_key' IS NOT NULL
           AND EXISTS (SELECT 1 FROM jsonb_array_elements(
                              script.fn_available_actions_ddt(d.id)->'available_actions') a
                        WHERE COALESCE((a->>'enabled')::boolean, true))
     ) q),
    0,
    '8) non-regressione: la nota non compare su documenti con un''azione ancora abilitata');

-- ============================================================
-- 9) Non-regressione: il motivo «documento vuoto» non e' stato mangiato
--    dalla somma dei motivi. Era l'unico prima di questo cantiere: se una
--    transizione esige righe e il documento non ne ha, deve restare spenta
--    con la sua reason.
-- ============================================================
CREATE TEMP TABLE _cap_vuoti AS
SELECT o.id,
       (a->>'enabled')::boolean AS cap_enabled,
       a->>'reason'             AS cap_reason
  FROM vendite.ordini o
  JOIN config.stati_doc_ordini sdo ON sdo.id = o.stato_doc_ordine_id
  CROSS JOIN LATERAL jsonb_array_elements(
         script.fn_available_actions_ordine(o.id)->'available_actions') a
  JOIN config.transizioni_stati_ordini t
       ON t.stato_da_id = o.stato_doc_ordine_id
      AND t.meta->>'action_key' = a->>'key'
 WHERE COALESCE((t.meta->>'requires_righe')::boolean, false)
   AND NOT EXISTS (SELECT 1 FROM vendite.ordini_righe r
                    WHERE r.ordine_id = o.id AND r.attivo IS TRUE);

SELECT CASE WHEN (SELECT count(*) FROM _cap_vuoti) = 0
  THEN pass('9) SKIP: nessun ordine vuoto con transizione requires_righe')
  ELSE is(
    (SELECT count(*)::int FROM _cap_vuoti
      WHERE cap_enabled OR cap_reason IS DISTINCT FROM 'DOCUMENTO_SENZA_RIGHE'),
    0,
    format('9) requires_righe sopravvive alla somma dei motivi, su %s ordini vuoti',
           (SELECT count(*) FROM _cap_vuoti)))
END;

SELECT * FROM finish();
ROLLBACK;
