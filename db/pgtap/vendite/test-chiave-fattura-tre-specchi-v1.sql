-- ------------------------------------------------------------
-- SPDX-License-Identifier: GPL-3.0-or-later
-- pgTAP test per Zero ERP
-- Test: la chiave di aggregazione della fattura e i suoi TRE SPECCHI
--       (piano-db-satelliti-fattura.md §6, fase 3b.5)
-- ------------------------------------------------------------
-- Perche' questo file esiste
--   La regola del §6: «ogni elemento della chiave logica del documento deve
--   comparire, identico, in tre posti — il WHERE del lookup che cerca la
--   fattura esistente, le colonne di testata che la descrivono, e la chiave
--   d'ambito degli arrotondamenti». L'abbiamo incontrata tre volte come
--   correzione isolata (utility_id assente dal WHERE, termine e modalita' non
--   scritti in testata, ambito senza le condizioni di pagamento) prima di
--   accorgerci che era una regola sola. Questo file la presidia una volta per
--   tutte: se domani si aggiunge un decimo discriminante alla chiave e si
--   dimentica uno dei tre posti, il test dice QUALE.
--
--   Chiave e lookup disallineati non degradano: si annullano a vicenda. La
--   chiave separa due documenti, il lookup non li distingue e li rifonde — e
--   non c'e' nessun errore da nessuna parte.
-- ------------------------------------------------------------
-- Indice test
-- 1) Fixture: attivita, lotto e chiave completa
-- 2) La chiave ha esattamente i 9 elementi attesi
-- 3) Specchio 1 — i 9 elementi compaiono nel WHERE del lookup
-- 4) Specchio 2 — i 9 elementi sono colonne di vendite.fatture
-- 5) Specchio 2 — la testata creata porta gli stessi VALORI della chiave
-- 6) Specchio 3 — la chiave d'ambito ha esattamente le 7 colonne attese
-- 7) Idempotenza del lookup: due chiamate, una sola fattura
-- 8) Termine divergente via COMMESSA (D-R end-to-end) -> seconda fattura
-- 9) Utility divergente -> seconda fattura (il bug storico del lookup)
-- 10) Catena, livello COMMESSA: la commessa possiede il termine
-- 11) Catena, livello di fondo: senza nulla a monte -> TP_1RATA
-- 12) Catena, guard: attivita_id non valido -> errore
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

SELECT plan(12);

-- ============================================================
-- 0) Fixture
-- ============================================================
-- Non si crea nulla di anagrafico: si prende un'attivita' esistente e un
-- lotto esistente. Tutto gira dentro BEGIN/ROLLBACK, quindi le fatture create
-- qui non sopravvivono al test e non serve nessuna pulizia — che e' anche il
-- motivo per cui non c'e' un blocco di cleanup da tenere allineato.
CREATE TEMP TABLE tmp_refs_tsp AS
SELECT (SELECT a.id FROM vendite.attivita_fatturabili a
         WHERE a.commessa_id IS NOT NULL ORDER BY a.id LIMIT 1)      AS attivita_id,
       (SELECT a.commessa_id FROM vendite.attivita_fatturabili a
         WHERE a.commessa_id IS NOT NULL ORDER BY a.id LIMIT 1)      AS commessa_id,
       (SELECT fl.id FROM vendite.fatturazione_lotti fl
         ORDER BY fl.id DESC LIMIT 1)                                AS lotto_id;

CREATE TEMP TABLE tmp_chiave_tsp AS
SELECT vendite.fn_build_fattura_key((SELECT attivita_id FROM tmp_refs_tsp)) AS chiave;

-- Gli elementi della chiave, in una tabella: è l'elenco su cui i tre specchi
-- vengono confrontati uno per uno.
CREATE TEMP TABLE tmp_elementi_tsp AS
SELECT k AS nome FROM jsonb_object_keys((SELECT chiave FROM tmp_chiave_tsp)) k;

SELECT ok(
  (SELECT attivita_id IS NOT NULL AND commessa_id IS NOT NULL AND lotto_id IS NOT NULL
     FROM tmp_refs_tsp)
  AND (SELECT count(*) FROM tmp_elementi_tsp) > 0,
  '1) Fixture: attivita con commessa, lotto e chiave costruita'
);

-- ============================================================
-- 1) La forma della chiave
-- ============================================================
-- Non è un test di gusto: è il punto in cui si accorge chi aggiunge un
-- discriminante. Se questo test diventa rosso, i tre sotto vanno riletti.
SELECT is(
  (SELECT array_agg(nome ORDER BY nome) FROM tmp_elementi_tsp),
  ARRAY['billing_account_id','emittente_soggetto_ruolo_id','modalita_pagamento_id',
        'registro_id','reseller_soggetto_ruolo_id','termine_pagamento_id',
        'tipo_doc_fiscale_id','utility_id','valuta_id']::text[],
  '2) La chiave ha esattamente i 9 elementi attesi'
);

-- ============================================================
-- 2) Specchio 1 — il WHERE del lookup
-- ============================================================
-- Si legge il sorgente vivo della funzione e si isola il blocco del lookup.
-- È una verifica sul testo, ed è voluta: l'invariante da presidiare è che
-- nessun elemento venga DIMENTICATO, e una dimenticanza non produce un
-- comportamento sbagliato osservabile su tutti i dati — produce due documenti
-- che si fondono solo quando quel particolare elemento diverge.
CREATE TEMP TABLE tmp_lookup_src_tsp AS
WITH def AS (
  SELECT pg_get_functiondef(p.oid) AS src
    FROM pg_proc p JOIN pg_namespace n ON n.oid = p.pronamespace
   WHERE n.nspname = 'vendite' AND p.proname = 'fn_get_or_create_fattura_header'
)
SELECT substring(
         src FROM position('FROM vendite.fatturazione_lotti_fatture lf' IN src)
             FOR  GREATEST(position('ORDER BY f.id LIMIT 1' IN src)
                           - position('FROM vendite.fatturazione_lotti_fatture lf' IN src), 0)
       ) AS blocco
  FROM def;

SELECT is(
  (SELECT count(*)::int FROM tmp_elementi_tsp e
    WHERE (SELECT blocco FROM tmp_lookup_src_tsp) LIKE '%' || e.nome || '%'),
  (SELECT count(*)::int FROM tmp_elementi_tsp),
  '3) Specchio 1: ogni elemento della chiave compare nel WHERE del lookup'
);

-- ============================================================
-- 3) Specchio 2 — le colonne di testata
-- ============================================================
SELECT is(
  (SELECT count(*)::int FROM tmp_elementi_tsp e
     JOIN information_schema.columns c
       ON c.table_schema = 'vendite' AND c.table_name = 'fatture'
      AND c.column_name = e.nome),
  (SELECT count(*)::int FROM tmp_elementi_tsp),
  '4) Specchio 2: ogni elemento della chiave e una colonna di vendite.fatture'
);

-- ============================================================
-- 4) Specchio 2, versione comportamentale
-- ============================================================
-- Le colonne possono esistere e restare vuote: è esattamente com'era prima di
-- 3b.3, con termine e modalita' mai scritti. Qui si crea davvero la fattura e
-- si confronta riga per riga con la chiave.
CREATE TEMP TABLE tmp_fattura_tsp AS
SELECT vendite.fn_get_or_create_fattura_header(
         (SELECT lotto_id FROM tmp_refs_tsp),
         (SELECT attivita_id FROM tmp_refs_tsp)) AS id;

SELECT ok(
  (SELECT f.billing_account_id          = (k.chiave->>'billing_account_id')::bigint
      AND f.tipo_doc_fiscale_id         = (k.chiave->>'tipo_doc_fiscale_id')::bigint
      AND f.valuta_id                   = (k.chiave->>'valuta_id')::int
      AND f.emittente_soggetto_ruolo_id = (k.chiave->>'emittente_soggetto_ruolo_id')::bigint
      AND f.registro_id                 = (k.chiave->>'registro_id')::bigint
      AND f.utility_id             IS NOT DISTINCT FROM (k.chiave->>'utility_id')::int
      AND f.reseller_soggetto_ruolo_id IS NOT DISTINCT FROM (k.chiave->>'reseller_soggetto_ruolo_id')::bigint
      AND f.termine_pagamento_id   IS NOT DISTINCT FROM (k.chiave->>'termine_pagamento_id')::bigint
      AND f.modalita_pagamento_id  IS NOT DISTINCT FROM (k.chiave->>'modalita_pagamento_id')::int
     FROM vendite.fatture f, tmp_chiave_tsp k
    WHERE f.id = (SELECT id FROM tmp_fattura_tsp)),
  '5) Specchio 2: la testata creata porta gli stessi valori della chiave'
);

-- ============================================================
-- 5) Specchio 3 — la chiave d'ambito degli arrotondamenti
-- ============================================================
-- L'ambito ha 7 colonne e non 9, e i due assenti NON sono una dimenticanza:
--   · `registro_id` e' funzione pura di `tipo_doc_fiscale_id`
--     (fn_get_registro_id), quindi non discrimina niente in piu';
--   · `reseller_soggetto_ruolo_id` e' determinato dal billing account, che
--     nell'ambito c'e' gia'.
-- Se un domani uno dei due smettesse di essere determinato, questo test
-- resterebbe verde a torto: per questo l'elenco atteso e' scritto per esteso,
-- cosi' chi cambia la chiave d'ambito deve passare di qui e rileggere la nota.
SELECT is(
  (SELECT array_agg(a.attname::text ORDER BY a.attname)
     FROM pg_index i
     JOIN pg_class c ON c.oid = i.indexrelid
     JOIN pg_attribute a ON a.attrelid = i.indrelid AND a.attnum = ANY(i.indkey)
    WHERE c.relname = 'uq_fatture_arrotondamenti_scope_key'),
  ARRAY['billing_account_id','emittente_soggetto_ruolo_id','modalita_pagamento_id',
        'termine_pagamento_id','tipo_doc_fiscale_id','utility_id','valuta_id']::text[],
  '6) Specchio 3: la chiave d ambito ha esattamente le 7 colonne attese'
);

-- ============================================================
-- 6) Idempotenza del lookup
-- ============================================================
-- È il test che vale di più del file: se il WHERE non ritrova ciò che la
-- INSERT ha appena scritto, ogni giro del generatore crea un documento nuovo.
SELECT is(
  vendite.fn_get_or_create_fattura_header(
    (SELECT lotto_id FROM tmp_refs_tsp),
    (SELECT attivita_id FROM tmp_refs_tsp)),
  (SELECT id FROM tmp_fattura_tsp),
  '7) Idempotenza: la seconda chiamata ritrova la fattura della prima'
);

-- ============================================================
-- 7) Divergenza del termine, per la via reale (D-R)
-- ============================================================
-- Non si tocca la fattura: si mette un termine sulla COMMESSA e si lascia che
-- la catena lo raccolga. Copre in una volta D-R (la commessa possiede il
-- termine), il livello commessa della catena, la chiave e il lookup.
-- Il bypass GUC serve per il guard di immutabilita' 3b.0-c: la commessa ha
-- lavoro attaccato, ed e' giusto che in esercizio non si possa cambiare.
SELECT set_config('zeroerp.maintenance_reset_lotto_draft', 'on', true);
UPDATE vendite.commesse
   SET termine_pagamento_id = (SELECT tp.id FROM config.termini_pagamento tp
                                WHERE tp.attivo IS TRUE
                                  AND tp.id IS DISTINCT FROM (SELECT (chiave->>'termine_pagamento_id')::bigint FROM tmp_chiave_tsp)
                                ORDER BY tp.id LIMIT 1)
 WHERE id = (SELECT commessa_id FROM tmp_refs_tsp);
SELECT set_config('zeroerp.maintenance_reset_lotto_draft', 'off', true);

SELECT isnt(
  vendite.fn_get_or_create_fattura_header(
    (SELECT lotto_id FROM tmp_refs_tsp),
    (SELECT attivita_id FROM tmp_refs_tsp)),
  (SELECT id FROM tmp_fattura_tsp),
  '8) Termine diverso sulla commessa -> la fattura non si riusa, se ne apre una nuova'
);

-- ============================================================
-- 8) Divergenza dell'utility
-- ============================================================
-- Qui si agisce sulla fattura e non sull'anagrafica, perche' cambiare
-- l'utility di un billing account e' un'operazione che il modello non prevede.
-- Il bersaglio e' comunque il lookup: era l'elemento che stava in chiave e non
-- nel WHERE, e per anni ha rifuso documenti di utility diverse.
UPDATE vendite.fatture
   SET utility_id = (SELECT u.id FROM config.utilities u
                      WHERE u.id IS DISTINCT FROM (SELECT (chiave->>'utility_id')::int FROM tmp_chiave_tsp)
                      ORDER BY u.id LIMIT 1)
 WHERE id = (SELECT id FROM tmp_fattura_tsp);

SELECT isnt(
  vendite.fn_get_or_create_fattura_header(
    (SELECT lotto_id FROM tmp_refs_tsp),
    (SELECT attivita_id FROM tmp_refs_tsp)),
  (SELECT id FROM tmp_fattura_tsp),
  '9) Utility diversa -> la fattura non si riusa (regressione sul lookup)'
);

-- ============================================================
-- 9) La catena, un test per livello
-- ============================================================
-- Livello 1 (documento sorgente) non e' esercitabile su questo DB: ordini e
-- preventivi sono vuote e tutte le attivita' hanno sorgente COMMESSA. Non si
-- salta in silenzio — lo dice il nome del test 10, che copre il livello
-- immediatamente sotto ed e' quello che oggi porta il dato.
SELECT is(
  (SELECT t.termine_pagamento_id
     FROM vendite.fn_resolve_termini_pagamento((SELECT attivita_id FROM tmp_refs_tsp)) t),
  (SELECT c.termine_pagamento_id FROM vendite.commesse c
    WHERE c.id = (SELECT commessa_id FROM tmp_refs_tsp)),
  '10) Catena livello COMMESSA: la catena restituisce il termine della commessa'
);

-- Tolto il termine dalla commessa, e con il cliente che non ne ha (fixture
-- scelta apposta), la catena deve arrivare in fondo. Se il cliente ne avesse
-- uno, il test si salta invece di misurare il livello sbagliato.
SELECT set_config('zeroerp.maintenance_reset_lotto_draft', 'on', true);
UPDATE vendite.commesse SET termine_pagamento_id = NULL, modalita_pagamento_id = NULL
 WHERE id = (SELECT commessa_id FROM tmp_refs_tsp);
SELECT set_config('zeroerp.maintenance_reset_lotto_draft', 'off', true);

CREATE TEMP TABLE tmp_cliente_tsp AS
SELECT cl.termine_pagamento_id
  FROM vendite.attivita_fatturabili a
  JOIN anagrafiche.billing_account ba  ON ba.id  = a.billing_account_id
  JOIN anagrafiche.billing_account bap ON bap.id = COALESCE(ba.parent_account_id, ba.id)
  JOIN anagrafiche.clienti cl ON cl.istanza_utility_id = bap.istanza_utility_id
 WHERE a.id = (SELECT attivita_id FROM tmp_refs_tsp);

SELECT CASE
  WHEN COALESCE((SELECT termine_pagamento_id FROM tmp_cliente_tsp), 0) <> 0
    THEN skip('il cliente della fixture ha un termine proprio: il livello di fondo non e raggiungibile', 1)
  ELSE is(
    (SELECT t.termine_pagamento_id
       FROM vendite.fn_resolve_termini_pagamento((SELECT attivita_id FROM tmp_refs_tsp)) t),
    (SELECT tp.id FROM config.termini_pagamento tp
      WHERE tp.codice_interno = 'TP_1RATA' AND tp.attivo IS TRUE),
    '11) Catena livello di fondo: senza termine a monte -> TP_1RATA'
  )
END;

SELECT throws_ok(
  $$ SELECT * FROM vendite.fn_resolve_termini_pagamento(-1); $$,
  'P0001',
  NULL,
  '12) Catena: attivita_id non valido -> errore'
);

SELECT * FROM finish();

ROLLBACK;
