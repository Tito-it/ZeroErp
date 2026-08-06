-- ------------------------------------------------------------
-- SPDX-License-Identifier: GPL-3.0-or-later
-- pgTAP test per Zero ERP
--
-- Test: da ogni stato non definitivo di ogni documento deve esistere almeno
--       un'uscita che una PERSONA puo' azionare.
--
-- LA REGOLA, E PERCHE'. Ogni documento vive in uno stato e da li' puo' passare
-- solo agli stati previsti dalla propria matrice di transizioni. Ogni
-- passaggio e' dichiarato automatico (lo fa il sistema quando succede
-- qualcos'altro) oppure manuale (un bottone che qualcuno preme).
--
-- Se da uno stato le uscite sono TUTTE automatiche, il documento dipende da un
-- evento che potrebbe non arrivare mai: push fallito, dato caricato per altra
-- via, documento piu' vecchio del meccanismo che lo sposta. Quando succede,
-- non esiste nessuno che possa sbloccarlo, e l'unica uscita offerta e'
-- distruggere il lavoro. E' il difetto che il brief
-- brief-db-emittibilita-visibile-e-sbloccabile ha trovato sulla commessa in
-- BOZZA; questo test esiste perche' non si ripresenti altrove senza che
-- nessuno se ne accorga.
--
-- Non e' una regola contro l'automatismo: e' una regola sulla via di servizio.
-- L'automatismo resta il percorso normale, il manuale e' cio' che si usa
-- quando il normale non scatta.
--
-- Indice test (1..3):
--   1. Preflight: tutte le matrici di transizione note sono leggibili
--   2. Ogni stato o ha un'uscita manuale ATTIVA, o dichiara perche' non ce
--      l'ha (meta->>'nessuna_azione_key')  ** e' la regola R1 **
--   3. Ogni transizione dichiarata manuale ha i metadati per essere un
--      bottone (action_key + label_key): una manuale senza etichetta non
--      compare nella UI, quindi non e' una via d'uscita davvero
--
-- ⚠️ SE IL TEST 2 DIVENTA ROSSO non significa «correggi subito»: significa
-- «qui serve una decisione». Le risposte legittime sono due, e vanno scritte:
--   (a) lo stato ha una via d'uscita manuale e mancava -> aggiungerla;
--   (b) lo stato e' deliberatamente senza ritorno -> scriverlo, valorizzando
--       meta->>'nessuna_azione_key' sulla riga di stato con la chiave i18n che
--       spiega all'operatore cosa sta succedendo e cosa puo' fare invece.
-- Quello che non e' legittimo e' lasciarlo implicito: un elenco di azioni
-- vuoto e senza motivo e' indistinguibile da un errore di caricamento.
--
-- ⚠️ ELENCO ESPLICITO DELLE MATRICI. Le tabelle sono elencate a mano e non
-- scoperte per convenzione di nome: se domani nasce un documento nuovo, questo
-- test NON lo vede e resta verde. E' un compromesso consapevole — la scoperta
-- automatica su nomi diversi (transizioni_stati_*, stati_doc_*_transizioni)
-- avrebbe portato piu' falsi negativi che copertura. Aggiungere qui la riga
-- quando nasce una matrice nuova fa parte del lavoro.
-- ------------------------------------------------------------

BEGIN;

-- Contesto applicativo: questo test gira come gira l'applicazione (ruolo
-- OPERATORE + RLS attiva), non come owner. Senza, con FORCE ROW LEVEL
-- SECURITY disattivo l'owner salta la RLS e il test non la esercita mai.
-- Brief: brief-db-pgtap-runner-rls-baseline §8.
DO $ctx$ BEGIN PERFORM script.fn_pgtap_set_contesto_operatore(); END $ctx$;

SELECT plan(3);

-- Matrice unificata: (documento, stato_da, manuale, attivo, + metadati UI).
-- `spiegato` dice se lo stato di partenza DICHIARA perche' non ha uscite
-- manuali, con la chiave i18n meta->>'nessuna_azione_key'. E' la seconda
-- risposta legittima alla regola: o la via d'uscita c'e', o c'e' scritto
-- perche' non c'e'. Quello che non e' ammesso e' il silenzio.
CREATE TEMP VIEW _tr AS
  SELECT 'commessa'::text AS doc, sd.codice_interno::text AS stato_da,
         coalesce((x.meta->>'manuale')::boolean, false) AS manuale, x.attivo,
         x.meta ? 'action_key' AS ha_action_key, x.meta ? 'label_key' AS ha_label_key,
         (sd.meta->>'nessuna_azione_key') IS NOT NULL AS spiegato
    FROM vendite.transizioni_stati_commessa x
    JOIN vendite.stati_commessa sd ON sd.id = x.stato_da_id
  UNION ALL
  SELECT 'contratto', sd.codice_interno::text,
         coalesce((x.meta->>'manuale')::boolean, false), x.attivo,
         x.meta ? 'action_key', x.meta ? 'label_key',
         (sd.meta->>'nessuna_azione_key') IS NOT NULL
    FROM config.transizioni_stati_contratti x
    JOIN config.stati_doc_contratti sd ON sd.id = x.stato_da_id
  UNION ALL
  SELECT 'ordine', sd.codice_interno::text,
         coalesce((x.meta->>'manuale')::boolean, false), x.attivo,
         x.meta ? 'action_key', x.meta ? 'label_key',
         (sd.meta->>'nessuna_azione_key') IS NOT NULL
    FROM config.transizioni_stati_ordini x
    JOIN config.stati_doc_ordini sd ON sd.id = x.stato_da_id
  UNION ALL
  SELECT 'preventivo', sd.codice_interno::text,
         coalesce((x.meta->>'manuale')::boolean, false), x.attivo,
         x.meta ? 'action_key', x.meta ? 'label_key',
         (sd.meta->>'nessuna_azione_key') IS NOT NULL
    FROM config.transizioni_stati_preventivi x
    JOIN config.stati_doc_preventivi sd ON sd.id = x.stato_da_id
  UNION ALL
  SELECT 'ddt', sd.codice_interno::text,
         coalesce((x.meta->>'manuale')::boolean, false), x.attivo,
         x.meta ? 'action_key', x.meta ? 'label_key',
         (sd.meta->>'nessuna_azione_key') IS NOT NULL
    FROM config.transizioni_stati_ddt x
    JOIN config.stati_doc_ddt sd ON sd.id = x.stato_da_id
  UNION ALL
  SELECT 'reso', sd.codice_interno::text,
         coalesce((x.meta->>'manuale')::boolean, false), x.attivo,
         x.meta ? 'action_key', x.meta ? 'label_key',
         (sd.meta->>'nessuna_azione_key') IS NOT NULL
    FROM config.transizioni_stati_reso x
    JOIN config.stati_doc_reso sd ON sd.id = x.stato_da_id
  UNION ALL
  SELECT 'offerta', sd.codice_interno::text,
         coalesce((x.meta->>'manuale')::boolean, false), x.attivo,
         x.meta ? 'action_key', x.meta ? 'label_key',
         (sd.meta->>'nessuna_azione_key') IS NOT NULL
    FROM config.stati_doc_offerte_transizioni x
    JOIN config.stati_doc_offerte sd ON sd.id = x.stato_da_id;

-- ============================================================
-- 1) Preflight: le sette matrici sono tutte rappresentate
-- ============================================================
SELECT is(
    (SELECT count(DISTINCT doc) FROM _tr)::bigint,
    7::bigint,
    '1. Preflight: tutte e sette le matrici di transizione sono leggibili'
);

-- ============================================================
-- 2) R1 — nessuno stato con sole uscite automatiche
--    Uno stato senza NESSUNA uscita attiva e' terminale per costruzione e
--    non entra nel conto: il problema e' avere una via d'uscita che pero'
--    nessuno puo' imboccare.
-- ============================================================
SELECT is(
    (SELECT coalesce(string_agg(doc || '.' || stato_da, ', ' ORDER BY doc, stato_da), '')
       FROM (
            SELECT doc, stato_da
              FROM _tr
             WHERE attivo
             GROUP BY doc, stato_da
            HAVING count(*) FILTER (WHERE manuale) = 0
               AND bool_and(NOT spiegato)
       ) x),
    '',
    '2. R1: ogni stato o ha un''uscita azionabile, o dichiara perche'' non ce l''ha'
);

-- ============================================================
-- 3) Una transizione manuale senza etichetta non e' una via d'uscita
-- ============================================================
SELECT is(
    (SELECT coalesce(string_agg(DISTINCT doc || '.' || stato_da, ', '), '')
       FROM _tr
      WHERE attivo AND manuale AND NOT (ha_action_key AND ha_label_key)),
    '',
    '3. Ogni transizione manuale attiva ha action_key e label_key (e'' un bottone vero)'
);

SELECT * FROM finish();
ROLLBACK;
