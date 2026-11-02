-- ------------------------------------------------------------
-- SPDX-License-Identifier: AGPL-3.0-or-later
-- ⚠️ rev 2026-10-19 (brief-db-grammatica-unica-documenti, lotto 2a): la finestra di
--   conferma chiede i legami col codice della sorgente (ORDINE_VENDITA, DDT_VENDITA).
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
-- Indice test (1..13):
--   1) Preflight: OGNI stato in fase CHIUSO dei SETTE domini che espongono
--      il campo dichiara nessuna_azione_key (senza, il resto sarebbe vacuo)
--   2) Preventivo: enabled dell'azione «annulla» == verdetto della fn pura,
--      su TUTTA la popolazione (la UI non puo' divergere dal guard)
--   3) Preventivo: quando e' spento, `reasons` riporta i motivi della fn pura
--      e `reason` e' il primo (contratto letto dal BB FE useDrawerActions)
--   4) Ordine: come 2
--   5) Ordine: come 3
--   6) Ordine: `stato_info_key` == quello che lo stato dichiara nel `meta`,
--      su TUTTA la popolazione (null compreso)
--   7) DDT: come 6
--   8) La nota compare ANCHE accanto a un'azione abilitata (ribaltato il
--      2026-08-10 (2): prima asseriva l'opposto)
--   9) Non-regressione: il motivo `requires_righe` sopravvive alla somma dei
--      motivi (era l'unico prima di questo cantiere)
--  10) Preventivo: come 6
--  11) Preventivo CHIUSO: i motivi di push_commessa / genera_ordine non
--      promettono l'accettazione (rev 2026-08-10)
--  12) Ordine ANNULLATO: il motivo del push non promette la conferma
--      (rev 2026-08-10) — soggetto costruito dal percorso legittimo
--  13) Un DDT figlio ANNULLATO non blocca l'annullamento dell'ordine
--      (rev 2026-08-15) — idem, soggetto scelto dalla matrice
--
-- ⚠️ SE IL TEST 2 O IL 4 DIVENTA ROSSO non e' un dettaglio di UI: significa
-- che il bottone e il database non dicono piu' la stessa cosa, cioe' che
-- l'operatore puo' premere qualcosa che verra' rifiutato (o non premere
-- qualcosa che sarebbe lecito). La sede della regola e' UNA — le
-- script.fn_check_*_annullabile — e queste asserzioni sono cio' che impedisce
-- che ne nasca una seconda dentro la capability.
--
-- ------------------------------------------------------------
-- rev 2026-08-10 — DUE MODI IN CUI QUESTO FILE ERA VERDE SENZA PRESIDIARE.
-- Li scrivo perche' sono la ragione per cui il difetto ② del rilievo in-app
-- del 2026-08-10 (barra vuota e muta su ogni preventivo annullato) e'
-- arrivato all'operatore con la suite tutta verde.
--
--   (a) Il preflight contava le chiavi: `= 4`. Un conteggio verifica il
--       lavoro GIA' FATTO e non dice niente sul prossimo stato chiuso che
--       nasce senza la sua chiave. Ora e' una REGOLA: zero stati in fase
--       CHIUSO senza nessuna_azione_key. Resta verde quando una chiave
--       nuova arriva insieme al suo stato, e diventa rosso esattamente
--       quando qualcuno aggiunge uno stato chiuso e si dimentica la nota.
--
--   (b) La popolazione dei «documenti muti» era filtrata da
--       `WHERE meta ? 'nessuna_azione_key'`, cioe' guardava SOLO gli stati
--       che la chiave ce l'avevano gia'. Verificava che il dato seminato
--       arrivasse — mai che ogni documento muto avesse un dato. I quattro
--       stati chiusi del preventivo erano fuori dalla misura per
--       costruzione: il test non poteva vederli. Ora la popolazione e'
--       «tutti i documenti in fase CHIUSO senza azioni vive» e
--       l'asserzione e' una COPERTURA: quanti ricevono la nota su quanti
--       ne hanno diritto.
--
-- ⚠️ E PERCHE' IL PERIMETRO ERA `fase = 'CHIUSO'` E NON «tutti i documenti
--   senza azioni vive», che sembrerebbe piu' severo. Misurato il 2026-08-10:
--   10 preventivi ACCETTATO (fase IN_CORSO, gia' in commessa) non hanno
--   nessuna azione ABILITATA — ma hanno il pulsante «Annulla» SPENTO CON IL
--   MOTIVO, che e' la risposta prevista dalla R3. Pretendere la nota anche
--   la' significherebbe chiedere due spiegazioni per la stessa cosa, e
--   rendere rosso un comportamento corretto. La nota risponde allo stato;
--   il tooltip risponde all'azione negata.
--
-- ------------------------------------------------------------
-- rev 2026-08-10 (2) — LA REGOLA CHE QUESTO FILE PRESIDIAVA E' CAMBIATA.
-- Decisione §5 di Tid: la nota di stato **compare sempre**, anche accanto a
-- un'azione ancora viva; e il campo del blob si chiama ora `stato_info_key`
-- (changeSet 20260810-04/-05/-06). Due conseguenze qui:
--
--   * il **test 8 e' stato RIBALTATO**, non messo in baseline: asseriva «la
--     nota non compare accanto a un bottone vivo», che era il presupposto
--     caduto. Un test che fotografa una scelta diventa rosso quando la
--     scelta cambia — e la risposta giusta e' riscriverlo, perche' la
--     baseline e' un registro di **debito** e qui non c'e' debito;
--   * la popolazione dei test 6/7/10 non ritaglia piu' niente (ne' gli stati
--     con la chiave, ne' i documenti muti): e' **tutta** e l'asserzione e'
--     l'invariante «il valore nel blob e' quello che lo stato dichiara»,
--     che copre nota-presente e nota-assente insieme.
--
-- ⚠️ Il campo del blob e la proprieta' del `meta` hanno da oggi nomi
-- DIVERSI (`stato_info_key` vs `nessuna_azione_key`), e nel file compaiono
-- entrambi: non e' un refuso. La proprieta' non e' stata rinominata perche'
-- scripts/check_i18n_keys.py trova le chiavi seminate per quel nome, e
-- cambiarlo senza toccare il guard lo renderebbe verde per cecita'.
-- ------------------------------------------------------------
-- rev 2026-09-17 — IL BLOB SI CALCOLA UNA VOLTA PER DOCUMENTO.
-- Il file impiegava piu' di 90 secondi come applicazione, cioe' oltre la
-- soglia a cui `pgtap-baseline.sh` uccide un file: copertura ZERO, e un
-- rosso intermittente a seconda del carico della macchina. Il difetto era
-- del TEST: le stesse funzioni STABLE venivano richiamate piu' volte sullo
-- stesso documento — fn_available_actions_preventivo e _ordine QUATTRO
-- volte (_cap_prev/_cap_ord, due colonne di _cap_nota, _cap_vuoti o
-- _cap_chiusi), fn_available_actions_ddt DUE volte (le due colonne di
-- _cap_nota).
--
-- Misurato il 2026-09-17 su dbdev, come zeroerp_app con contesto operatore,
-- UNA chiamata: preventivo ~10 ms, ordine ~29 ms, DDT ~850 ms (33 ms come
-- owner). Il DDT paga vendite.vw_partite_merce: fn_list_ddt_da_pushare e
-- fn_ddt_push_diagnosi la leggono per INTERO anche a p_ddt_id fissato — le
-- CTE materializzate della vista non lasciano passare il filtro sul
-- documento — e sotto RLS la vista costa 22 volte l'owner, perche' la CTE
-- `sospetto` e' un EXISTS correlato che rivaluta le policy riga per riga.
-- Quel costo e' del PRODOTTO (lo paga ogni apertura del drawer DDT) e
-- questo file puo' solo pagarlo una volta invece di due.
--
-- ⭐ Ora il blob di ogni documento sta in `_blob`, calcolato UNA volta
-- dopo aver preso il contesto operatore; tutte le popolazioni (`_cap_*`)
-- si derivano da li'. NON indebolisce nulla: e' lo stesso valore che le
-- asserzioni leggevano, letto una volta invece di quattro. Le fn_check_*
-- (il lato «guard» del confronto) restano chiamate VIVE: sono l'altro
-- termine del paragone, non una copia del blob.
-- ⛔ Restano vive anche le chiamate dei test 12 e 13, che vengono DOPO una
--   mutazione di stato: una copia scattata prima direbbe il mondo di ieri.
-- Pattern: vendite/test-documento-lineage-v1.sql (2026-09-10).
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

SELECT plan(13);

-- ============================================================
-- 1) Preflight: il dato su cui poggia tutto il resto — scritto come
--    REGOLA e non come conteggio (vedi rev 2026-08-10 (a) in testa).
--    Uno stato in fase CHIUSO e' uno stato da cui il documento non
--    riparte: se non dichiara la sua chiave, il giorno in cui un
--    documento ci arriva senza azioni vive la barra resta muta.
--    Il messaggio nomina gli stati inadempienti, cosi' il rosso dice
--    da solo quale riga di quale CSV manca.
-- ============================================================
-- ⚠️ PERIMETRO: i SETTE domini le cui fn_available_actions_* espongono il
--   campo. Erano tre fino al 2026-08-10; i quattro nuovi (contratto, reso,
--   offerta, commessa) sono entrati con `20260811-01`…`-04`. Se questa lista
--   non cresce insieme alle funzioni, la regola smette di vedere il dominio
--   nuovo **restando verde** — la cecita' per costruzione gia' pagata due
--   volte su questo stesso file.
--   `lotto` NON e' qui, ed e' una decisione: usa `config.stati_doc_fiscale`,
--   condivisa con `vendite.fatture`, e la capability della fattura non
--   esiste ancora. Vedi attivita-urgenti-del-10-08 §3.
CREATE TEMP VIEW _stati_chiusi AS
  SELECT 'preventivo'::text AS dominio, codice_interno::text AS codice_interno,
         (meta ? 'nessuna_azione_key') AS dichiara
    FROM config.stati_doc_preventivi WHERE fase = 'CHIUSO' AND attivo IS TRUE
  UNION ALL
  SELECT 'ordine', codice_interno::text, (meta ? 'nessuna_azione_key')
    FROM config.stati_doc_ordini WHERE fase = 'CHIUSO' AND attivo IS TRUE
  UNION ALL
  SELECT 'ddt', codice_interno::text, (meta ? 'nessuna_azione_key')
    FROM config.stati_doc_ddt WHERE fase = 'CHIUSO' AND attivo IS TRUE
  UNION ALL
  SELECT 'contratto', codice_interno::text, (meta ? 'nessuna_azione_key')
    FROM config.stati_doc_contratti WHERE fase = 'CHIUSO' AND attivo IS TRUE
  UNION ALL
  SELECT 'reso', codice_interno::text, (meta ? 'nessuna_azione_key')
    FROM config.stati_doc_reso WHERE fase = 'CHIUSO' AND attivo IS TRUE
  UNION ALL
  SELECT 'offerta', codice_interno::text, (meta ? 'nessuna_azione_key')
    FROM config.stati_doc_offerte WHERE fase = 'CHIUSO' AND attivo IS TRUE
  UNION ALL
  SELECT 'commessa', codice_interno::text, (meta ? 'nessuna_azione_key')
    FROM vendite.stati_commessa WHERE fase = 'CHIUSO' AND attivo IS TRUE;

SELECT is(
    (SELECT coalesce(string_agg(dominio || '.' || codice_interno, ', '
                                ORDER BY dominio, codice_interno), '')
       FROM _stati_chiusi WHERE NOT dichiara),
    '',
    format('1) preflight: ogni stato in fase CHIUSO dichiara nessuna_azione_key (%s stati chiusi in %s domini)',
           (SELECT count(*) FROM _stati_chiusi),
           (SELECT count(DISTINCT dominio) FROM _stati_chiusi)));

-- ------------------------------------------------------------
-- ⭐ IL BLOB, UNA VOLTA PER DOCUMENTO (rev 2026-09-17 in testa). Da qui
-- discendono TUTTE le popolazioni `_cap_*`: i conteggi delle asserzioni e
-- quelli degli skip parlano degli stessi soggetti, e ogni documento paga
-- la propria capability una volta sola.
-- Si popola DOPO il contesto operatore: contiene esattamente cio' che la
-- RLS lascia vedere a quell'operatore. Le tre FK di stato sono NOT NULL,
-- quindi il JOIN al catalogo degli stati non restringe la popolazione.
-- ⛔ Chi aggiunge un'asserzione qui dentro: se legge il blob di un
--   documento NON mutato, lo prende da `_blob`; se lo legge DOPO averlo
--   mutato (test 12 e 13), chiama la funzione viva.
-- ------------------------------------------------------------
CREATE TEMP TABLE _blob AS
SELECT 'preventivo'::text                              AS doc,
       p.id,
       sdp.id                                          AS stato_id,
       sdp.codice_interno::text                        AS stato_cod,
       sdp.fase::text                                  AS fase,
       sdp.meta->>'nessuna_azione_key'                 AS nota_attesa,
       script.fn_available_actions_preventivo(p.id)    AS blob
  FROM vendite.preventivi p
  JOIN config.stati_doc_preventivi sdp ON sdp.id = p.stato_doc_preventivo_id
UNION ALL
SELECT 'ordine', o.id,
       sdo.id, sdo.codice_interno::text, sdo.fase::text,
       sdo.meta->>'nessuna_azione_key',
       script.fn_available_actions_ordine(o.id)
  FROM vendite.ordini o
  JOIN config.stati_doc_ordini sdo ON sdo.id = o.stato_doc_ordine_id
UNION ALL
SELECT 'ddt', d.id,
       sdd.id, sdd.codice_interno::text, sdd.fase::text,
       sdd.meta->>'nessuna_azione_key',
       script.fn_available_actions_ddt(d.id)
  FROM vendite.ddt d
  JOIN config.stati_doc_ddt sdd ON sdd.id = d.stato_doc_ddt_id;

-- ------------------------------------------------------------
-- Popolazioni dell'annullamento: il lato «capability» viene dal blob, il
-- lato «guard» (fn_check_*_annullabile) e' una chiamata VIVA — e' l'altro
-- termine del confronto dei test 2-5, e una copia non confronterebbe nulla.
-- ------------------------------------------------------------
CREATE TEMP TABLE _cap_prev AS
SELECT b.id,
       (a->>'enabled')::boolean                                   AS cap_enabled,
       COALESCE(a->'reasons', '[]'::jsonb)                        AS cap_reasons,
       a->>'reason'                                               AS cap_reason,
       script.fn_check_preventivo_annullabile(b.id)               AS motivi_fn
  FROM _blob b
  CROSS JOIN LATERAL jsonb_array_elements(b.blob->'available_actions') a
 WHERE b.doc = 'preventivo'
   AND a->>'target_state' = 'ANNULLATO';

CREATE TEMP TABLE _cap_ord AS
SELECT b.id,
       (a->>'enabled')::boolean                                   AS cap_enabled,
       COALESCE(a->'reasons', '[]'::jsonb)                        AS cap_reasons,
       a->>'reason'                                               AS cap_reason,
       script.fn_check_ordine_annullabile(b.id)                   AS motivi_fn
  FROM _blob b
  CROSS JOIN LATERAL jsonb_array_elements(b.blob->'available_actions') a
 WHERE b.doc = 'ordine'
   AND a->>'target_state' = 'ANNULLATO';

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
-- La nota di stato: popolazione INTERA, nessun filtro.
--
-- ⚠️ DUE RESTRIZIONI SONO STATE TOLTE DA QUI, in due passaggi, e insieme
--   raccontano come si costruisce un presidio che presidia davvero.
--
--   1. Fino al 2026-08-10 (mattina) il filtro era
--      `WHERE meta ? 'nessuna_azione_key'`: la misura guardava SOLO gli stati
--      che la chiave ce l'avevano gia'. Gli stati SENZA chiave — cioe'
--      esattamente quelli da trovare — erano fuori dalla popolazione per
--      costruzione, e il test non poteva accorgersene. Sostituito con un
--      filtro sulla FASE dello stato.
--   2. Dal 2026-08-10 (2) cade anche quello, e con esso il `NOT EXISTS` sulle
--      azioni vive: la nota non e' piu' subordinata alla lista vuota
--      (decisione §5 di Tid), quindi non c'e' piu' nessun sottoinsieme da
--      ritagliare. La popolazione e' **tutti i documenti**, e l'asserzione e'
--      l'invariante piu' forte che si possa scrivere qui:
--
--        il valore nel blob e' SEMPRE quello che lo stato dichiara nel `meta`.
--
--   Cosi' scritta copre entrambe le direzioni in una riga sola: la nota
--   arriva dove e' dichiarata, ed e' assente (null) dove non lo e' — senza
--   bisogno di due asserzioni che possono divergere. `IS NOT DISTINCT FROM`
--   e non `=`: qui il null e' un valore atteso, non un dato mancante.
--
-- ⚠️ IL CAMPO DEL BLOB SI CHIAMA `stato_info_key`, LA PROPRIETA' NEL `meta`
--   RESTA `nessuna_azione_key`. Non e' una dimenticanza: il presidio
--   scripts/check_i18n_keys.py trova le chiavi seminate per QUEL nome
--   (RE_SEED_KEY sui CSV, elenco _PROP_KEY), e rinominarla senza toccare il
--   guard lo renderebbe verde per cecita'. Vedi 20260810-04/-05/-06.
-- ------------------------------------------------------------
-- ⚠️ rev 2026-09-17: le due colonne che leggevano il blob lo richiamavano
--   OGNI volta (due chiamate per documento, e sul DDT erano ~1,7 s a riga):
--   ora leggono `_blob`. La popolazione e' identica — tre domini, tutti i
--   documenti visibili — e cosi' la semantica delle colonne.
CREATE TEMP TABLE _cap_nota AS
SELECT b.doc, b.id, b.fase,
       b.blob->>'stato_info_key'                                            AS nota,
       b.nota_attesa,
       EXISTS (SELECT 1 FROM jsonb_array_elements(b.blob->'available_actions') a
                WHERE COALESCE((a->>'enabled')::boolean, true))              AS ha_azioni_vive
  FROM _blob b;

-- ============================================================
-- 6) Ordine: il valore nel blob e' SEMPRE quello dichiarato dallo stato.
--    Popolazione intera, null compreso: copre in un colpo «la nota arriva
--    dove e' dichiarata» e «non compare dove non lo e'».
-- ============================================================
SELECT CASE WHEN (SELECT count(*) FROM _cap_nota WHERE doc='ordine') = 0
  THEN pass('6) SKIP: nessun ordine nella popolazione visibile')
  ELSE is(
    (SELECT count(*)::int FROM _cap_nota
      WHERE doc='ordine' AND nota IS DISTINCT FROM nota_attesa),
    0,
    format('6) ordine: stato_info_key == meta dello stato su %s documenti (%s con la nota, %s senza — attesi)',
           (SELECT count(*) FROM _cap_nota WHERE doc='ordine'),
           (SELECT count(*) FROM _cap_nota WHERE doc='ordine' AND nota IS NOT NULL),
           (SELECT count(*) FROM _cap_nota WHERE doc='ordine' AND nota IS NULL)))
END;

-- ============================================================
-- 7) DDT: idem. E' la meta' del lavoro che il §6 del brief non nominava.
-- ============================================================
SELECT CASE WHEN (SELECT count(*) FROM _cap_nota WHERE doc='ddt') = 0
  THEN pass('7) SKIP: nessun DDT nella popolazione visibile')
  ELSE is(
    (SELECT count(*)::int FROM _cap_nota
      WHERE doc='ddt' AND nota IS DISTINCT FROM nota_attesa),
    0,
    format('7) ddt: stato_info_key == meta dello stato su %s documenti (%s con la nota, %s senza — attesi)',
           (SELECT count(*) FROM _cap_nota WHERE doc='ddt'),
           (SELECT count(*) FROM _cap_nota WHERE doc='ddt' AND nota IS NOT NULL),
           (SELECT count(*) FROM _cap_nota WHERE doc='ddt' AND nota IS NULL)))
END;

-- ============================================================
-- 8) 🔄 RIBALTATO il 2026-08-10 (2) — e va detto perche', invece di
--    riscriverlo in silenzio.
--
--    Questo test asseriva l'OPPOSTO: «la nota non deve comparire accanto a
--    un bottone vivo», sul presupposto che dicesse «non c'e' niente da
--    fare». Con la decisione §5 di Tid la nota non dice piu' quello: dice
--    cos'e' successo allo stato, e questo serve anche a chi ha ancora
--    un'azione da fare. Il test fotografava una scelta, la scelta e'
--    cambiata, quindi il test diventa il suo contrario — NON un rosso da
--    mettere in baseline: la baseline e' un registro di debito, e qui non
--    c'e' debito, c'e' una decisione.
--
--    Ora presidia il verso nuovo, che e' l'unico osservabile: fra i
--    documenti in fase CHIUSO che hanno ancora un'azione abilitata, TUTTI
--    devono ricevere la nota. Erano i 5 ordini EVASO che il §9.2 del brief
--    elencava come limite dichiarato — e sono esattamente cio' che la
--    decisione ha voluto sbloccare. Se domani qualcuno rimettesse il
--    `CASE WHEN v_nessuna_azione`, questo test lo prende; il 6/7/10 no,
--    perche' quei 5 sono una minoranza dentro una popolazione che
--    tornerebbe a tornare.
-- ============================================================
SELECT CASE WHEN (SELECT count(*) FROM _cap_nota
                   WHERE fase = 'CHIUSO' AND ha_azioni_vive AND nota_attesa IS NOT NULL) = 0
  THEN pass('8) SKIP: nessun documento in fase CHIUSO con un''azione ancora abilitata (il ramo nuovo non ha soggetti)')
  ELSE is(
    (SELECT count(*)::int FROM _cap_nota
      WHERE fase = 'CHIUSO' AND ha_azioni_vive AND nota_attesa IS NOT NULL
        AND nota IS NULL),
    0,
    format('8) la nota compare ANCHE accanto a un''azione abilitata: %s documenti in fase CHIUSO con azioni vive, tutti con la nota',
           (SELECT count(*) FROM _cap_nota
             WHERE fase = 'CHIUSO' AND ha_azioni_vive AND nota_attesa IS NOT NULL)))
END;

-- ============================================================
-- 9) Non-regressione: il motivo «documento vuoto» non e' stato mangiato
--    dalla somma dei motivi. Era l'unico prima di questo cantiere: se una
--    transizione esige righe e il documento non ne ha, deve restare spenta
--    con la sua reason.
-- ============================================================
CREATE TEMP TABLE _cap_vuoti AS
SELECT b.id,
       (a->>'enabled')::boolean AS cap_enabled,
       a->>'reason'             AS cap_reason
  FROM _blob b
  CROSS JOIN LATERAL jsonb_array_elements(b.blob->'available_actions') a
  JOIN config.transizioni_stati_ordini t
       ON t.stato_da_id = b.stato_id
      AND t.meta->>'action_key' = a->>'key'
 WHERE b.doc = 'ordine'
   AND COALESCE((t.meta->>'requires_righe')::boolean, false)
   AND NOT EXISTS (SELECT 1 FROM vendite.ordini_righe r
                    WHERE r.ordine_id = b.id AND r.attivo IS TRUE);

SELECT CASE WHEN (SELECT count(*) FROM _cap_vuoti) = 0
  THEN pass('9) SKIP: nessun ordine vuoto con transizione requires_righe')
  ELSE is(
    (SELECT count(*)::int FROM _cap_vuoti
      WHERE cap_enabled OR cap_reason IS DISTINCT FROM 'DOCUMENTO_SENZA_RIGHE'),
    0,
    format('9) requires_righe sopravvive alla somma dei motivi, su %s ordini vuoti',
           (SELECT count(*) FROM _cap_vuoti)))
END;

-- ============================================================
-- 10) Preventivo: copertura della nota sugli stati chiusi.
--     E' il difetto ② del rilievo in-app del 2026-08-10: quattro stati
--     chiusi con meta = {} e nessuna riga di codice da cambiare, solo il
--     dato che mancava. Prima di allora questa asserzione non esisteva —
--     ed era la sola cosa che avrebbe potuto trovarlo.
-- ============================================================
SELECT CASE WHEN (SELECT count(*) FROM _cap_nota WHERE doc='preventivo') = 0
  THEN pass('10) SKIP: nessun preventivo nella popolazione visibile')
  ELSE is(
    (SELECT count(*)::int FROM _cap_nota
      WHERE doc='preventivo' AND nota IS DISTINCT FROM nota_attesa),
    0,
    format('10) preventivo: stato_info_key == meta dello stato su %s documenti (%s con la nota, %s senza — attesi)',
           (SELECT count(*) FROM _cap_nota WHERE doc='preventivo'),
           (SELECT count(*) FROM _cap_nota WHERE doc='preventivo' AND nota IS NOT NULL),
           (SELECT count(*) FROM _cap_nota WHERE doc='preventivo' AND nota IS NULL)))
END;

-- ============================================================
-- 11) Preventivo CHIUSO: il motivo non promette l'accettazione.
--     Difetto ① dello stesso rilievo. Su un preventivo EVASO il drawer
--     diceva «sara' disponibile dopo l'accettazione del preventivo» —
--     ed e' evaso PROPRIO perche' e' stato accettato. L'asserzione e' in
--     forma negativa (nessuno stato chiuso espone la reason
--     dell'attesa) perche' e' la bugia a dover essere impossibile: se
--     domani nascesse una terza reason per gli stati chiusi il test
--     resterebbe verde, com'e' giusto, ma `non_accettato` non potra' mai
--     piu' tornare qui.
-- ============================================================
CREATE TEMP TABLE _cap_chiusi AS
SELECT b.id, b.stato_cod AS stato,
       b.blob->>'can_push_commessa_reason_key' AS push_key,
       b.blob->>'can_genera_ordine_reason_key' AS ordine_key
  FROM _blob b
 WHERE b.doc = 'preventivo' AND b.fase = 'CHIUSO';

SELECT CASE WHEN (SELECT count(*) FROM _cap_chiusi) = 0
  THEN pass('11) SKIP: nessun preventivo in fase CHIUSO (ramo non esercitato da nessun soggetto)')
  ELSE is(
    (SELECT count(*)::int FROM _cap_chiusi
      WHERE push_key   LIKE '%.non_accettato'
         OR ordine_key LIKE '%.non_accettato'
         OR push_key   IS NULL
         OR ordine_key IS NULL),
    0,
    format('11) preventivo CHIUSO: nessuno dei %s documenti promette l''accettazione, e nessuno resta senza motivo',
           (SELECT count(*) FROM _cap_chiusi)))
END;

-- ============================================================
-- 12) Ordine ANNULLATO: il motivo del push non promette la conferma.
--     ⚠️ IL SOGGETTO SI COSTRUISCE, e va spiegato perche' qui e'
--     legittimo mentre altrove e' una trappola. Misurato il 2026-08-10:
--     nel database NON esiste un solo ordine ANNULLATO, quindi il ramo
--     nuovo non ha nessun soggetto vivo — un'asserzione sulla
--     popolazione andrebbe in SKIP e non misurerebbe niente. Il ramo
--     non e' pero' morto: ANNULLATO e' raggiungibile, ed e' il cantiere
--     «vie d'uscita» che l'ha reso tale. Quindi il soggetto si porta
--     nello stato attraversando la transizione VERA della matrice
--     (DRAFT -> ANNULLATO, riga attiva), non con un INSERT diretto: e'
--     il percorso reale, e se un guard lo rifiuta il test lo dice
--     invece di aggirarlo. Tutto dentro la transazione che finisce in
--     ROLLBACK.
-- ============================================================
CREATE TEMP TABLE _ord_ann AS
SELECT o.id FROM vendite.ordini o
  JOIN config.stati_doc_ordini s ON s.id = o.stato_doc_ordine_id
 WHERE s.codice_interno = 'DRAFT'
   AND jsonb_array_length(script.fn_check_ordine_annullabile(o.id)) = 0
 ORDER BY o.id
 LIMIT 1;

-- ⭐ rev 2026-10-11 (brief-db-annullo-documento-con-legami, D-1/D-4): un ordine
--   con legami (righe di preventivo, offerta d'origine, righe di commessa
--   NON_EMESSA) non si annulla con l'UPDATE diretto — l'avviso
--   E_DOC_ANNULLO_CON_LEGAMI lo rifiuta. La transizione VERA passa dal verbo,
--   dichiarando i legami letti da vendite.fn_documento_legami, come fa la
--   finestra di conferma; un ordine senza legami ne dichiara zero.
DO $ord$
DECLARE v_ord bigint;
BEGIN
  FOR v_ord IN SELECT id FROM _ord_ann LOOP
    PERFORM vendite.fn_annulla_ordine(
        v_ord,
        (SELECT count(*)::integer FROM vendite.fn_documento_legami('ORDINE_VENDITA', v_ord) l));
  END LOOP;
END $ord$;

SELECT CASE WHEN (SELECT count(*) FROM _ord_ann) = 0
  THEN pass('12) SKIP: nessun ordine DRAFT annullabile da cui costruire il soggetto')
  ELSE is(
    (SELECT c.blob->>'can_push_commessa_reason_key'
       FROM _ord_ann x
       CROSS JOIN LATERAL (SELECT script.fn_available_actions_ordine(x.id) AS blob) c),
    'vendite.ordini.push_commessa_reason.annullato',
    '12) ordine ANNULLATO: il motivo del push e'' annullato, non piu'' non_confermato')
END;

-- ============================================================
-- 13) Un DDT figlio ANNULLATO non blocca l'annullamento dell'ordine.
--     Regola simmetrica a quella del preventivo (`20260810-03`), chiusa
--     sull'ordine con `20260815-01`: un documento morto non deve tenere
--     bloccato il padre per sempre e senza uscita.
--
--     ⚠️ IL SOGGETTO SI COSTRUISCE, e si sceglie dalla MATRICE non dai
--     dati. Nel database di sviluppo non esiste un DDT figlio annullato —
--     ma e' una fotografia di dati di test, non un fatto sul dominio:
--     in esercizio annullare un DDT e' ordinario. Il DDT si porta quindi
--     ad ANNULLATO attraversando la transizione VERA, e va scelto fra
--     quelli il cui stato la ammette: il primo tentativo di scrivere
--     questa prova ha preso un DDT da uno stato non ammesso e il guard
--     `trgfn_ddt_guard_transizione` l'ha rifiutato — correttamente.
--
--     L'asserzione e' sul CONTEGGIO che cala, non sulla sparizione del
--     motivo: un ordine puo' avere piu' figli, e quelli vivi devono
--     continuare a bloccare. E' il filtro a essere esercitato.
-- ============================================================
CREATE TEMP TABLE _ddt_ann AS
SELECT o.id AS ordine_id, d.id AS ddt_id,
       (script.fn_check_ordine_annullabile(o.id) -> 0 ->> 'dettaglio')::int AS bloccanti_prima
  FROM vendite.ordini o
  JOIN vendite.ddt d ON d.sorgente_uid = o.uid
  JOIN config.stati_doc_ddt s ON s.id = d.stato_doc_ddt_id
 WHERE EXISTS (SELECT 1 FROM config.transizioni_stati_ddt t
                 JOIN config.stati_doc_ddt sa ON sa.id = t.stato_a_id
                WHERE t.stato_da_id = s.id
                  AND sa.codice_interno = 'ANNULLATO'
                  AND t.attivo)
 ORDER BY o.id, d.id
 LIMIT 1;

-- ⭐ rev 2026-10-11 (brief-db-annullo-documento-con-legami §3, D-8 di
--   brief-db-ddt-righe-evase-dall-ordine): un DDT figlio di un ordine ne porta
--   i legami, e l'annullo diretto e' rifiutato (E_DOC_ANNULLO_CON_LEGAMI). La
--   transizione VERA passa dal verbo, dichiarando i legami letti da
--   vendite.fn_documento_legami (D-4), come fa la finestra di conferma; l'annullo di una
--   bolla emessa chiede l'azione emetti_ddt al verbo di stato.
DO $ann$
DECLARE v_ddt bigint;
BEGIN
  PERFORM dbops.fn_pgtap_concedi_azione(
      NULLIF(current_setting('app.current_user_id', true), '')::integer, 'emetti_ddt');
  FOR v_ddt IN SELECT ddt_id FROM _ddt_ann LOOP
    PERFORM vendite.fn_annulla_ddt(
        v_ddt,
        (SELECT count(*)::integer FROM vendite.fn_documento_legami('DDT_VENDITA', v_ddt) l));
  END LOOP;
END $ann$;

SELECT CASE WHEN (SELECT count(*) FROM _ddt_ann) = 0
  THEN pass('13) SKIP: nessun DDT figlio in uno stato da cui la matrice ammette l''annullamento')
  ELSE is(
    (SELECT COALESCE((script.fn_check_ordine_annullabile(x.ordine_id) -> 0 ->> 'dettaglio')::int, 0)
       FROM _ddt_ann x),
    (SELECT bloccanti_prima - 1 FROM _ddt_ann),
    format('13) il DDT annullato non blocca piu'': i DDT bloccanti scendono da %s a %s',
           (SELECT bloccanti_prima FROM _ddt_ann),
           (SELECT bloccanti_prima - 1 FROM _ddt_ann)))
END;

SELECT * FROM finish();
ROLLBACK;
