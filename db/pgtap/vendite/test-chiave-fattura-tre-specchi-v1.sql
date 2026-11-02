-- ------------------------------------------------------------
-- SPDX-License-Identifier: AGPL-3.0-or-later
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
-- 2) La chiave ha esattamente gli 11 elementi attesi
-- 3) Specchio 1 — gli 11 elementi compaiono nel WHERE del lookup
-- 4) Specchio 2 — gli 11 elementi sono colonne di vendite.fatture
-- 5) Specchio 2 — la testata creata porta gli stessi VALORI della chiave
-- 6) Specchio 3 — la chiave d'ambito ha esattamente le 7 colonne attese
-- 7) Idempotenza del lookup: due chiamate, una sola fattura
-- 8) Termine divergente via COMMESSA (D-R end-to-end) -> seconda fattura
-- 9) Utility divergente -> seconda fattura (il bug storico del lookup)
-- 10) Catena, livello COMMESSA: la commessa possiede il termine
-- 11) Catena, livello di fondo: senza nulla a monte -> TP_1RATA
-- 12) Catena, guard: attivita_id non valido -> errore
-- rev 2026-10-24 (brief-modello-documento-vendita Q-2/Q-4): attivita' e lotto si
--   COSTRUISCONO. Prima si pescavano «la prima attivita' con commessa» e «l'ultimo
--   lotto DRAFT»: su un database ricostruito da zero non ci sono, e il file moriva
--   nella fixture senza eseguire un'asserzione. Ora la commessa emittibile la fa
--   dbops.fn_pgtap_crea_commessa (che costruisce anche il mondo e apre il contesto),
--   il lotto DRAFT lo apre vendite.fn_create_fatturazione_lotto e l'attivita' nasce
--   dal PULL vero col marchio del lotto.
-- rev 2026-10-24 (brief-modello-documento-vendita R-3/R-4): la sorgente ROOT la
--   scrive il builder della commessa (p_con_sorgente_root), non piu' un INSERT
--   del test; il lotto DRAFT nasce da dbops.fn_pgtap_crea_lotto, del cliente
--   (p_del_cliente) e col tipo documento della riga di commessa, come prima lo
--   faceva la madre chiamata col billing account. Asserzioni invariate.
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
-- pgtap-contesto: escluso — il contesto lo apre dbops.fn_pgtap_crea_commessa (rev
--   2026-10-24), sull'operatore dell'azienda
--   che costruisce (fn_pgtap_crea_mondo_cliente, ramo «nessun contesto»): prima
--   l'azienda, poi il contesto, poi il cliente.
CREATE TEMP TABLE tmp_comm_tsp AS
SELECT * FROM dbops.fn_pgtap_crea_commessa('chiave tre specchi', 'PRONTA_FATTURAZIONE',
                                           p_con_sorgente_root => true);

SELECT plan(12);

-- ============================================================
-- 0) Fixture
-- ============================================================
-- ⭐ Il mondo si costruisce (rev 2026-10-24). Tutto gira dentro BEGIN/ROLLBACK,
-- quindi niente sopravvive al test e non serve nessuna pulizia.
-- ⚠️ Il pull PRETENDE una sorgente ROOT: la scrive il builder
--   (p_con_sorgente_root). La sorgente COMMESSA punta a vendite.commesse con
--   key_selector `id`, quindi l'id della commessa la soddisfa per costruzione.

-- ⚠️ Il lotto dev'essere in DRAFT, e la condizione non e' un dettaglio.
--    `fn_get_or_create_fattura_header` crea la fattura in DRAFT, e un
--    CONSTRAINT TRIGGER DEFERRED pretende che ogni fattura di un lotto
--    abbia lo stesso stato del lotto. 🔴 Il 2026-08-16 un lotto EMESSA pescato
--    con `ORDER BY id DESC` fece diventare rossi tre file insieme: ora il lotto
--    lo da' dbops.fn_pgtap_crea_lotto (madre sotto), nello stato iniziale, del
--    cliente e col tipo documento della riga scritta dal builder.
CREATE TEMP TABLE tmp_lotto_tsp AS
SELECT l.lotto_id
  FROM (SELECT c.billing_account_id, ca.tipo_doc_fiscale_id
          FROM tmp_comm_tsp c
          JOIN vendite.commesse_attivita ca ON ca.id = c.attivita_id) r,
       dbops.fn_pgtap_crea_lotto('chiave tre specchi', 'DRAFT', r.billing_account_id,
                                 r.tipo_doc_fiscale_id, p_del_cliente => true) l;

-- L'attivita' fatturabile nasce dal PULL vero, col marchio del lotto.
CREATE TEMP TABLE tmp_pull_tsp AS
SELECT * FROM vendite.fn_emit_attivita_fatturabili_da_commessa(
         p_commessa_id   => (SELECT commessa_id FROM tmp_comm_tsp),
         p_emit_batch_id => (SELECT fl.lock_batch_id FROM vendite.fatturazione_lotti fl
                              WHERE fl.id = (SELECT lotto_id FROM tmp_lotto_tsp)));

CREATE TEMP TABLE tmp_refs_tsp AS
SELECT af.id AS attivita_id, af.commessa_id, l.lotto_id
  FROM vendite.attivita_fatturabili af, tmp_lotto_tsp l
 WHERE af.commessa_attivita_id = (SELECT attivita_id FROM tmp_comm_tsp);

CREATE TEMP TABLE tmp_chiave_tsp AS
SELECT vendite.fn_build_fattura_key((SELECT attivita_id FROM tmp_refs_tsp)) AS chiave;

-- Gli elementi della chiave, in una tabella: è l'elenco su cui i tre specchi
-- vengono confrontati uno per uno.
CREATE TEMP TABLE tmp_elementi_tsp AS
SELECT k AS nome FROM jsonb_object_keys((SELECT chiave FROM tmp_chiave_tsp)) k;

SELECT ok(
  (SELECT attivita_id IS NOT NULL AND commessa_id IS NOT NULL AND lotto_id IS NOT NULL
     FROM tmp_refs_tsp)
  AND (SELECT count(*) FROM tmp_refs_tsp) = 1
  AND (SELECT inserted_rows FROM tmp_pull_tsp) = 1
  AND (SELECT count(*) FROM tmp_elementi_tsp) > 0,
  '1) Fixture: attivita con commessa, lotto e chiave costruita'
);

-- ============================================================
-- 1) La forma della chiave
-- ============================================================
-- Non è un test di gusto: è il punto in cui si accorge chi aggiunge un
-- discriminante. Se questo test diventa rosso, i tre sotto vanno riletti.
-- rev 2026-08-18 (brief-design-note-credito-resi N3): due elementi nuovi, e
--   sono proprio il caso per cui questo file esiste.
--     natura_doc_id -> e' cio' che impedisce a un'attivita' di RETTIFICA di
--       finire nella fattura ordinaria: senza, nota di credito e fattura
--       andrebbero sulla stessa testata;
--     serie         -> ⚠️ non era MAI stata scritta dalla INSERT del lookup.
--       Restava NULL e fn_assign_numero_fattura cadeva sul serie_default del
--       registro: calcolarla senza scriverla avrebbe dato alla nota di credito
--       un numero VALIDO nella serie delle fatture — un difetto che non solleva
--       nulla e si scopre guardando un registro IVA.
--   ⭐ Che i test 3 e 4 siano passati SENZA modifiche e' la prova che i tre
--   specchi sono allineati: il WHERE del lookup e le colonne di testata
--   nominano gia' entrambi i nuovi elementi.
SELECT is(
  (SELECT array_agg(nome ORDER BY nome) FROM tmp_elementi_tsp),
  ARRAY['billing_account_id','emittente_soggetto_ruolo_id','modalita_pagamento_id',
        'natura_doc_id','registro_id','reseller_soggetto_ruolo_id','serie',
        'termine_pagamento_id','tipo_doc_fiscale_id','utility_id','valuta_id']::text[],
  '2) La chiave ha esattamente gli 11 elementi attesi'
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
      AND f.natura_doc_id               = (k.chiave->>'natura_doc_id')::bigint
      -- ⚠️ `serie` col confronto NULL-safe: e' nullable, anzi con il sezionale
      --    proprio delle note di credito e' NULL sempre. Con `=` il NULL non
      --    combacia mai e il test sarebbe rosso su ogni documento normale.
      AND f.serie                  IS NOT DISTINCT FROM NULLIF(k.chiave->>'serie','')::varchar
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
