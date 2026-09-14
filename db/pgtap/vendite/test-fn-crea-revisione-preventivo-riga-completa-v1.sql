-- ------------------------------------------------------------
-- SPDX-License-Identifier: GPL-3.0-or-later
-- pgtap-runner: owner
-- pgtap-runner-motivo: la fixture costruisce un'AZIENDA — emittente fiscale,
--   utente tecnico e identita' digitale (dbops.fn_pgtap_crea_emittente_operatore)
--   — e un operatore dentro un perimetro non crea l'azienda in cui lavora.
--   E' il criterio 2 di scripts/testpgtap.sh. Dal contesto in poi si lavora
--   nei panni dell'operatore costruito.
-- pgTAP test — la RIGA della rev N+1 e' COMPLETA: vendite.fn_crea_revisione_preventivo
--   copia le righe con un elenco ESPLICITO di colonne, e una colonna non
--   nominata non passa (nessun errore: la riga nasce col campo a NULL).
--   E' successo DUE volte in cinque mesi — le marche di approvazione prezzo
--   (20260422-04) e la data di consegna richiesta (20260913-07) — e la
--   seconda volta l'ha trovata il BE, non un test.
--   ChangeSet: 20260914-13 (data di consegna), 20260914-14 (marche di
--   approvazione prezzo, D di Tid). Brief:
--   brief-db-modifiche-certe-ciclo-vendita-e-articolo, sezione 6-quinquies (P-10, P-11).
--
-- Elenco test (plan 8):
--   IL PRESIDIO SULL'ELENCO (prima della fixture: legge pg_attribute e il corpo vivo)
--    1) ⭐ ogni colonna di preventivi_righe e' NOMINATA nell'INSERT della copia righe
--       oppure DICHIARATA esclusa qui sotto, con la ragione
--    2) nessuna esclusione dichiarata e' stantia: la colonna esiste ancora e NON e' nominata
--   LE MARCHE DI APPROVAZIONE PREZZO — percorso reale, fn_crea_revisione_preventivo
--    3) la rev N+1 nasce (rev 1) con le tre righe
--    4) ⭐ la riga APPROVED porta stato e pratica identici sulla rev N+1
--    5) ⭐ la riga PENDING porta stato e pratica identici sulla rev N+1
--    6) la riga senza marca resta senza marca: la revisione non inventa un'approvazione
--    7) la rev N conserva le sue marche: la revisione COPIA, non sposta
--    8) la riga PENDING della rev N+1 e' PROTETTA: cambiare il prezzo e' rifiutato dal guard
--
-- ────────────────────────────────────────────────────────────────
-- ⭐ IL TEST 1 E' IL PRESIDIO CHE MANCAVA. Non prova un valore: prova che
--   l'ELENCO e' completo. La prossima colonna aggiunta a preventivi_righe fa
--   rosso qui finche' qualcuno non decide — o la nomina nella copia, o la
--   dichiara esclusa in _escluse con il perche'. Prima, una colonna nuova si
--   perdeva in silenzio e si scopriva in collaudo.
--   ⚠️ Il perimetro del presidio e' UNA funzione, per nome: se la copia delle
--   righe venisse ESTRATTA in una funzione sua, questo test la perderebbe di
--   vista (memoria: presidio su testo, perimetro = elenco). Chi estrae,
--   aggiorna la query del test 1 nello stesso commit.
--   ⚠️ E le esclusioni sono DICHIARAZIONI, non impostazioni di fabbrica:
--   dichiarare una colonna esclusa zittisce il test 1 per quella colonna. Il
--   test 2 tiene l'elenco onesto (una colonna dichiarata esclusa e poi
--   nominata nella copia e' una dichiarazione stantia, e fa rosso).
--
-- ⭐ I TEST 4-5 SONO PROVATI SUL PERCORSO REALE: chiamano
--   fn_crea_revisione_preventivo e leggono la riga che ne esce. Le marche
--   si copiano 1:1 (come i componenti della stessa funzione e come
--   fn_crea_revisione_offerta, 20260601-05): i gate L3 scattano sull'edit,
--   non alla revisione, quindi lo stato_approvazione_prezzo e' l'unico
--   marcatore persistente di un prezzo fuori policy autorizzato o in attesa.
--   Azzerarlo faceva nascere la rev N+1 con lo stesso prezzo e senza marca.
--
-- ⚠️ IL MONDO SI COSTRUISCE, NON SI CERCA: azienda, cliente con billing
--   account legato a QUELLA azienda, articolo, due pratiche di approvazione
--   (pratiche.fn_crea_pratica, tipo APPROVAZIONE_PREZZO dal catalogo). Cosi'
--   il file misura la stessa cosa su dbdev e in CI — a differenza di
--   test-fn-crea-revisione-preventivo, che pesca dalla popolazione ed e'
--   ERRORE_FIXTURE in baseline-rossi-ci.tsv.
--
-- ⚠️ La riga PENDING si INSERISCE gia' PENDING: il guard
--   trgfn_righe_guard_pending e' BEFORE UPDATE, non INSERT. E' la stessa forma
--   di test-preventivi-approvazione-prezzo.
--
-- ⚠️ I vincoli restano IMMEDIATE dalla riga di preambolo: gli helper della
--   fixture aprono e richiudono da soli la loro finestra differita.
-- ------------------------------------------------------------

BEGIN;

SET CONSTRAINTS ALL IMMEDIATE;

SELECT plan(8);

-- ============================================================
-- IL PRESIDIO SULL'ELENCO (prima della fixture: non dipende da nessun dato)
-- ============================================================
-- Le colonne che la copia NON nomina di proposito, con la ragione. E' la
-- dichiarazione: aggiungerne una qui e' una decisione, non una svista.
CREATE TEMP TABLE _escluse (colonna text PRIMARY KEY, ragione text NOT NULL);
INSERT INTO _escluse VALUES
    ('id',                'identity: la rev N+1 ha le sue chiavi'),
    ('data_insert',       'audit: default now(), trigger'),
    ('data_update',       'audit: default now(), trigger'),
    ('tx_id',             'framework tx_id: trgfn_tx_id_managed'),
    ('natura_vendita_id', 'la deriva e la CONGELA dall''articolo trgfn_preventivi_righe_set_natura_vendita (BEFORE INSERT): nominarla scriverebbe un valore sovrascritto');

-- Le colonne NOMINATE nell'INSERT della copia righe, lette dal corpo VIVO:
-- il blocco «INSERT INTO vendite.preventivi_righe ( ... )» della funzione.
-- ⚠️ regexp_replace e non btrim: l'elenco e' su piu' righe, e btrim toglie
--   solo gli spazi — il primo nome di ogni riga restava «\n    preventivo_id».
CREATE TEMP TABLE _nominate AS
SELECT regexp_replace(c, '\s+', '', 'g') AS colonna
  FROM pg_proc p,
       regexp_split_to_table(
           substring(p.prosrc FROM 'INSERT INTO vendite\.preventivi_righe\s*\(([^)]*)\)'),
           ',') AS c
 WHERE p.oid = 'vendite.fn_crea_revisione_preventivo'::regproc
   AND regexp_replace(c, '\s+', '', 'g') <> '';

SELECT is(
    (SELECT COALESCE(string_agg(a.attname::text, ', ' ORDER BY a.attnum), '')
       FROM pg_attribute a
      WHERE a.attrelid = 'vendite.preventivi_righe'::regclass
        AND a.attnum > 0 AND NOT a.attisdropped
        AND a.attname::text NOT IN (SELECT colonna FROM _nominate)
        AND a.attname::text NOT IN (SELECT colonna FROM _escluse)),
    '',
    '1) ogni colonna di preventivi_righe e'' nominata nella copia righe di fn_crea_revisione_preventivo o dichiarata esclusa (con la ragione)'
);

SELECT is(
    (SELECT COALESCE(string_agg(e.colonna || CASE WHEN n.colonna IS NOT NULL THEN ' (nominata)' ELSE ' (non esiste piu'')' END, ', ' ORDER BY e.colonna), '')
       FROM _escluse e
       LEFT JOIN _nominate n ON n.colonna = e.colonna
       LEFT JOIN pg_attribute a
              ON a.attrelid = 'vendite.preventivi_righe'::regclass
             AND a.attname::text = e.colonna AND a.attnum > 0 AND NOT a.attisdropped
      WHERE n.colonna IS NOT NULL OR a.attname IS NULL),
    '',
    '2) nessuna esclusione dichiarata e'' stantia: ognuna e'' ancora una colonna e NON e'' nominata nella copia'
);

-- ============================================================
-- Fixture: il mondo, da owner
-- ============================================================
CREATE TEMP TABLE _mondo AS
SELECT * FROM dbops.fn_pgtap_crea_emittente_operatore();

-- Il billing account si lega a QUESTA azienda (terzo parametro): da owner il
-- trigger z90 non ha un operatore in sessione da cui derivarlo.
CREATE TEMP TABLE _cliente AS
SELECT c.*
  FROM _mondo m
  CROSS JOIN LATERAL dbops.fn_pgtap_crea_cliente_ba(
      'Revisione riga completa', NULL, m.soggetto_ruolo_id) c;

CREATE TEMP TABLE _articolo AS
WITH a AS (
    INSERT INTO catalogo.articoli (codice, descrizione, uom_id)
    SELECT 'PGTAP-REVRIGA-' || substr(md5(random()::text), 1, 10),
           'Articolo pgTAP revisione riga completa',
           (SELECT um.id FROM catalogo.unita_misura um WHERE um.attivo IS TRUE ORDER BY um.id LIMIT 1)
    RETURNING id
)
SELECT id AS articolo_id FROM a;

-- ⭐ Da qui nei panni dell'operatore costruito: pratiche, preventivo, righe e
--   revisione sono la strada dell'applicazione, e i guard di emittente e la
--   RLS leggono il contesto.
DO $ctx$ BEGIN
    PERFORM script.fn_pgtap_set_contesto_operatore((SELECT auth_user_id FROM _mondo));
END $ctx$;

-- Due pratiche di approvazione prezzo (una per riga marcata), come le crea il
-- BE: pratiche.fn_crea_pratica con il tipo APPROVAZIONE_PREZZO del catalogo,
-- risolto per codice_interno.
CREATE TEMP TABLE _pratiche AS
SELECT x.tag,
       pratiche.fn_crea_pratica(
           m.emittente_fiscale_id,
           (SELECT tp.id FROM pratiche.tipi_prestazione tp WHERE tp.codice_interno = 'APPROVAZIONE_PREZZO'),
           NULL, NULL, NULL, NULL,
           'pgTAP revisione riga completa — ' || x.tag,
           jsonb_build_object('test_scope', 'pgtap_revisione_riga_completa')) AS pratica_id
  FROM _mondo m, (VALUES ('approvata'), ('pendente')) AS x(tag);

-- Preventivo EMESSO: la revisione nasce solo da li'.
CREATE TEMP TABLE _preventivo AS
WITH p AS (
    INSERT INTO vendite.preventivi
        (numero, billing_account_id, istanza_utility_id, utility_id, valuta_id,
         stato_doc_preventivo_id, emittente_fiscale_id, meta)
    SELECT 'PGTAP-REVRIGA-' || substr(md5(random()::text), 1, 8),
           c.billing_account_id, c.istanza_utility_id, c.utility_id,
           (SELECT v.id FROM config.valute v ORDER BY v.id LIMIT 1),
           (SELECT s.id FROM config.stati_doc_preventivi s
             WHERE s.codice_interno = 'EMESSO' AND s.attivo IS TRUE),
           m.emittente_fiscale_id,
           jsonb_build_object('test_scope', 'pgtap_revisione_riga_completa')
      FROM _cliente c, _mondo m
    RETURNING id
)
SELECT id AS preventivo_id FROM p;

-- Tre righe: APPROVED con la sua pratica, PENDING con la sua, e una senza
-- marca. La terza e' il gemello che prova che la revisione non inventa.
-- ⚠️ iva_id esplicito: un trigger di riga chiede l'aliquota.
CREATE TEMP TABLE _righe_prev AS
WITH r AS (
    INSERT INTO vendite.preventivi_righe
        (preventivo_id, articolo_id, prezzo_unitario, qta_operativa, iva_id, ordine,
         stato_approvazione_prezzo, pratica_approvazione_prezzo_id)
    SELECT p.preventivo_id, a.articolo_id, 10.00, 2, i.iva_id, x.ordine,
           x.stato::config.stato_approvazione_prezzo,
           (SELECT pr.pratica_id FROM _pratiche pr WHERE pr.tag = x.tag)
      FROM _preventivo p, _articolo a,
           (SELECT i.id AS iva_id FROM config.iva i WHERE i.attivo IS TRUE ORDER BY i.id LIMIT 1) i,
           (VALUES (1, 'APPROVED', 'approvata'),
                   (2, 'PENDING',  'pendente'),
                   (3, NULL,       NULL)) AS x(ordine, stato, tag)
    RETURNING id, ordine, stato_approvazione_prezzo, pratica_approvazione_prezzo_id
)
SELECT id AS riga_prev_id, ordine, stato_approvazione_prezzo, pratica_approvazione_prezzo_id FROM r;

-- ============================================================
-- LA REVISIONE, sul percorso reale
-- ============================================================
CREATE TEMP TABLE _rev AS
SELECT r.nuovo_preventivo_id, r.nuova_rev
  FROM vendite.fn_crea_revisione_preventivo((SELECT preventivo_id FROM _preventivo), 'pgtap') r;

-- La riga della rev N+1 si riconosce per `ordine`, che la revisione copia:
-- e' la stessa chiave con cui la funzione rimappa i componenti.
CREATE TEMP TABLE _righe_rev AS
SELECT pr.ordine, pr.stato_approvazione_prezzo, pr.pratica_approvazione_prezzo_id, pr.id AS riga_rev_id
  FROM vendite.preventivi_righe pr
 WHERE pr.preventivo_id = (SELECT nuovo_preventivo_id FROM _rev);

SELECT is(
    (SELECT (SELECT nuova_rev FROM _rev)::text || ' | ' || count(*)::text || ' righe' FROM _righe_rev),
    '1 | 3 righe',
    '3) la rev N+1 e'' nata (rev 1) con le tre righe'
);

SELECT is(
    (SELECT r.stato_approvazione_prezzo::text || '|' || r.pratica_approvazione_prezzo_id::text FROM _righe_rev r WHERE r.ordine = 1),
    'APPROVED|' || (SELECT pratica_id::text FROM _pratiche WHERE tag = 'approvata'),
    '4) la riga APPROVED porta stato e pratica IDENTICI sulla rev N+1: un prezzo approvato resta marcato'
);

SELECT is(
    (SELECT r.stato_approvazione_prezzo::text || '|' || r.pratica_approvazione_prezzo_id::text FROM _righe_rev r WHERE r.ordine = 2),
    'PENDING|' || (SELECT pratica_id::text FROM _pratiche WHERE tag = 'pendente'),
    '5) la riga PENDING porta stato e pratica IDENTICI sulla rev N+1: una richiesta in attesa resta in attesa'
);

SELECT is(
    (SELECT COALESCE(r.stato_approvazione_prezzo::text, 'NULL') || '|' || COALESCE(r.pratica_approvazione_prezzo_id::text, 'NULL')
       FROM _righe_rev r WHERE r.ordine = 3),
    'NULL|NULL',
    '6) la riga senza marca resta senza marca sulla rev N+1: la revisione non inventa un''approvazione'
);

SELECT is(
    (SELECT string_agg(pr.ordine || ':' || COALESCE(pr.stato_approvazione_prezzo::text, 'NULL') || '|' || COALESCE(pr.pratica_approvazione_prezzo_id::text, 'NULL'), ',' ORDER BY pr.ordine)
       FROM vendite.preventivi_righe pr
      WHERE pr.preventivo_id = (SELECT preventivo_id FROM _preventivo)),
    (SELECT string_agg(p.ordine || ':' || COALESCE(p.stato_approvazione_prezzo::text, 'NULL') || '|' || COALESCE(p.pratica_approvazione_prezzo_id::text, 'NULL'), ',' ORDER BY p.ordine)
       FROM _righe_prev p),
    '7) la rev N conserva le sue marche tali e quali: la revisione COPIA, non sposta'
);

-- ============================================================
-- LA MARCA COPIATA FA IL SUO MESTIERE: la riga PENDING della rev N+1 e' congelata
-- ============================================================
-- E' il motivo per cui si copia: senza marca il prezzo fuori policy sarebbe
-- stato modificabile liberamente sulla rev N+1. Il guard e' BEFORE UPDATE
-- (trgfn_righe_guard_pending), e parla con E_RIGA_PREZZO_PENDENTE.
PREPARE cambia_prezzo_pending AS
UPDATE vendite.preventivi_righe
   SET prezzo_unitario = 999
 WHERE id = (SELECT riga_rev_id FROM _righe_rev WHERE ordine = 2);

SELECT throws_like(
    'cambia_prezzo_pending',
    '%in attesa di approvazione prezzo%',
    '8) la riga PENDING della rev N+1 e'' protetta dal guard: cambiare il prezzo e'' rifiutato (E_RIGA_PREZZO_PENDENTE)'
);

SELECT * FROM finish();
ROLLBACK;
