-- ------------------------------------------------------------
-- SPDX-License-Identifier: GPL-3.0-or-later
-- Zero ERP — PRESIDIO sui riferimenti morti nelle funzioni
--
-- Brief: docs/it/dev/work-done/brief-db-bonifica-riferimenti-morti.md §5
--
-- Pezzi del presidio (nessuno duplica la logica di un altro):
--   dbops.fn_check_funzioni_riferimenti_morti()   la misura      (20260804-62)
--   dbops.riferimenti_morti_esenzioni             il registro    (20260804-63)
--   dbops.vw_riferimenti_morti_da_sanare          i difetti aperti
--   dbops.vw_riferimenti_morti_rientrati          le voci di troppo (20260804-64)
--   scripts/sql/check_funzioni_riferimenti_morti.sql   lo strumento a mano
--   scripts/sql/guardrail_riferimenti_morti.sql        il gate della CI
--   questo file                                        il gate della suite
--
-- Indice test (7 asserzioni):
--   1. l'estensione plpgsql_check c'e' (senza, i test 2 e 3 fanno skip)
--   1-bis. plpgsql_check ha potuto controllare OGNI funzione (NON_MISURATO)
--   2. nessun difetto REALE/ORFANA fuori dal registro del debito
--   3. nessuna voce RIENTRATA nel registro (il debito deve calare)
--   4. ogni voce del registro ha un motivo scritto
--   5. nessun riferimento morto nei DATI di configurazione
--   6. il conteggio che legge il DIGEST concorda con la misura diretta
--
-- ── PERCHE' ESISTE ──────────────────────────────────────────────────────
--   Il 2026-03-31 due funzioni morte furono **viste**, e lasciate li' con
--   un changeSet che diceva «Da verificare se la funzione va rimossa dal
--   DB». Cinque mesi dopo una delle due ha fatto fallire un migrate.
--   Una segnalazione in un commento non e' un presidio: e' un promemoria
--   che nessuno rilegge. Questo file e' la differenza fra le due cose.
--
--   ⚠️ Il caso `trgfn_preventivi_guard_annullamento` (`20260804-54`) dice
--   perche' serve la suite e non basta la buona volonta': quel guard e'
--   stato scritto e rotto lo **stesso giorno** in cui il controllo lo ha
--   trovato. Senza, sarebbe entrato in servizio parlando arabo esattamente
--   nel momento in cui doveva spiegare un rifiuto.
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

SELECT plan(7);

-- ============================================================
-- 1. L'estensione c'e'?
-- ============================================================
SELECT ok(
  EXISTS (SELECT 1 FROM pg_extension WHERE extname = 'plpgsql_check'),
  'estensione plpgsql_check presente (senza, il presidio non puo'' misurare)'
);

-- ⚠️ La misura si materializza UNA VOLTA: compila ~500 funzioni, e le
--    trigger function una volta per ogni tabella agganciata. I test 2 e 3
--    sono due anti-join sullo stesso dato — passare dalle due viste
--    significherebbe pagarla due volte.
--    Se l'estensione manca la temp table resta vuota: i due test fanno
--    skip esplicito, che e' meglio di un verde che non ha misurato niente.
CREATE TEMP TABLE misura ON COMMIT DROP AS
SELECT *
  FROM dbops.fn_check_funzioni_riferimenti_morti()
 WHERE EXISTS (SELECT 1 FROM pg_extension WHERE extname = 'plpgsql_check');

-- ============================================================
-- 1-bis. 🔴 LO STRUMENTO HA MISURATO? — e va PRIMA dell'asserzione centrale
--
-- ⛔ Se `plpgsql_check` solleva invece di rispondere, il gestore EXCEPTION
--    della misura scrive `error:CHECK-KO:` e la funzione classifica quelle
--    righe come `NON_MISURATO` (changeSet 20260910-36). Di quelle funzioni
--    non si sa NIENTE: il test 2 direbbe «nessun riferimento morto» avendo
--    guardato la meta' delle cose, e il test 3 vedrebbe ogni voce del
--    registro come «rientrata».
-- ⚠️ Fino al 2026-09-10 quella forma cadeva nell'ELSE e usciva come REALE:
--    su dbdev sono state 779 righe su 780 funzioni, con un registro di DUE
--    voci — il test 2 falliva elencando 779 difetti che non esistevano.
--    Brief: brief-db-un-destinatario-per-i-presidi §9.3.
-- ============================================================
SELECT CASE
  WHEN NOT EXISTS (SELECT 1 FROM pg_extension WHERE extname = 'plpgsql_check')
    THEN skip('plpgsql_check assente: misura non eseguibile', 1)
  ELSE is(
    COALESCE((
      SELECT string_agg(x.riga, E'\n  ' ORDER BY x.riga)
        FROM (
          SELECT DISTINCT m.schema_nome || '.' || m.funzione || ' -> ' || m.esito AS riga
            FROM misura m
           WHERE m.classe = 'NON_MISURATO'
        ) x
    ), ''),
    '',
    'plpgsql_check ha potuto controllare OGNI funzione (nessuna NON_MISURATO)'
  )
END;

-- ============================================================
-- 2. Nessun difetto fuori registro — l'asserzione centrale
--
-- Il messaggio elenca i colpevoli invece di contarli: un test che dice
-- «ci sono 4 difetti» costringe a rilanciare lo strumento a mano per
-- sapere quali.
-- ============================================================
SELECT CASE
  WHEN NOT EXISTS (SELECT 1 FROM pg_extension WHERE extname = 'plpgsql_check')
    THEN skip('plpgsql_check assente: misura non eseguibile', 1)
  ELSE is(
    COALESCE((
      SELECT string_agg(x.riga, E'\n  ' ORDER BY x.riga)
        FROM (
          SELECT DISTINCT m.schema_nome || '.' || m.funzione || ' -> ' || m.esito AS riga
            FROM misura m
           WHERE m.classe IN ('REALE', 'ORFANA')
             AND NOT EXISTS (
                   SELECT 1 FROM dbops.riferimenti_morti_esenzioni e
                    WHERE e.schema_nome = m.schema_nome
                      AND e.funzione    = m.funzione
                      AND m.esito LIKE e.esito_like)
        ) x
    ), ''),
    '',
    'nessun riferimento morto fuori dal registro del debito'
  )
END;

-- ============================================================
-- 3. Il registro non contiene voci rientrate
--
-- ⚠️ E' cio' che rende il registro un DEBITO e non un elenco di eccezioni.
--    Se un difetto registrato non compare piu', la riga va TOLTA: senza
--    questo test il registro puo' solo crescere, e un registro che cresce
--    e basta e' il posto dove i problemi vanno a sparire.
-- ============================================================
SELECT CASE
  WHEN NOT EXISTS (SELECT 1 FROM pg_extension WHERE extname = 'plpgsql_check')
    THEN skip('plpgsql_check assente: misura non eseguibile', 1)
  ELSE is(
    COALESCE((
      SELECT string_agg(e.schema_nome || '.' || e.funzione, ', ' ORDER BY e.funzione)
        FROM dbops.riferimenti_morti_esenzioni e
       WHERE NOT EXISTS (
               SELECT 1 FROM misura m
                WHERE m.classe IN ('REALE', 'ORFANA')
                  AND m.schema_nome = e.schema_nome
                  AND m.funzione    = e.funzione
                  AND m.esito LIKE e.esito_like)
    ), ''),
    '',
    'nessuna voce rientrata nel registro (il difetto e'' risolto: togliere la riga)'
  )
END;

-- ============================================================
-- 4. Ogni voce del registro ha un motivo
--
-- Ridondante col CHECK chk_riferimenti_morti_esenzioni_motivo, e va bene:
-- il CHECK protegge la scrittura, questo protegge dal caso in cui qualcuno
-- droppi il CHECK per far passare una riga. Costa una query su una tabella
-- di poche righe.
-- ============================================================
SELECT is(
  (SELECT count(*) FROM dbops.riferimenti_morti_esenzioni
    WHERE motivo IS NULL OR length(btrim(motivo)) < 40)::int,
  0,
  'ogni voce del registro porta un motivo scritto (>= 40 caratteri)'
);

-- ============================================================
-- 5. Riferimenti morti nei DATI di configurazione
--
-- ⚠️ plpgsql_check compila i CORPI: una tabella nominata come stringa in
--    una tabella di configurazione gli e' invisibile — nel corpo che la
--    consuma compare solo come parametro. Il 2026-08-04 questa misura ha
--    trovato config.sistema_codici 'lotti_attivita', che puntava a
--    vendite.attivita_fatturabili_lotti droppata cinque mesi prima: stessa
--    morte delle funzioni, ma nessuno dei due giri del controllo sulle
--    funzioni poteva vederla. (Rimossa da 20260804-50.)
-- ============================================================
SELECT is(
  COALESCE((
    SELECT string_agg(sc.codice_interno || ' -> ' || sc.schema_tabella || '.' || sc.nome_tabella,
                      ', ' ORDER BY sc.codice_interno)
      FROM config.sistema_codici sc
     WHERE sc.nome_tabella IS NOT NULL
       AND to_regclass(sc.schema_tabella || '.' || sc.nome_tabella) IS NULL
  ), ''),
  '',
  'nessuna riga di config.sistema_codici punta a una tabella inesistente'
);

-- ============================================================
-- 6. 🔴 IL CONTEGGIO CHE LEGGE IL DIGEST — quello che il test 1-bis NON vede
--
-- ⛔ Il digest dei presidi non legge questa vista: chiede
--    `dbops.fn_conta_presidio`, che e' SECURITY DEFINER con
--    `search_path = pg_catalog, pg_temp`. Fino al 2026-09-12 la scansione
--    ereditava quel path, e li' non si risolvevano NE' `plpgsql_check_function`
--    (sta in `public`) NE' i riferimenti a `unaccent`, `dblink` e `geometry`
--    dentro le funzioni che compila: ogni funzione usciva `NON_MISURATO`.
--    Misurato quel giorno: il digest riferiva **784** «riferimenti morti»
--    mentre questa stessa vista, letta diretta, rispondeva **0**.
--
-- ⭐ Il test 1-bis non poteva prenderlo, e non per una svista: misura la
--    scansione DIRETTA, cioe' il percorso SANO. Per due giorni e' stato verde
--    su un difetto vivo.
--    *Un presidio che misura il percorso sano non presidia quello in servizio.*
--
-- ⇒ Qui si confrontano i DUE percorsi. Non e' circolare — i due lati girano in
--    contesti di risoluzione diversi, ed e' proprio la differenza fra i due che
--    il difetto produceva.
-- ⚠️ E non pinna un numero: se comparira' un riferimento morto vero, i due lati
--    saliranno INSIEME e questo test restera' verde. A dirlo e' il test 2, che
--    e' il suo mestiere. Qui si asserisce che i due percorsi CONCORDANO.
--
-- ⚠️ Il `DROP TABLE IF EXISTS tmp_raw` non e' pulizia: e' obbligatorio. La
--    scansione lavora su una temp table, e quella creata qui sopra appartiene
--    al ruolo del TEST; `fn_conta_presidio` gira come PROPRIETARIO e il suo
--    `DELETE FROM tmp_raw` prenderebbe `42501 permesso negato` — cioe' un
--    ERRORE, che ferma il file e lascia tutti i test SENZA girare.
-- ⚠️ Costa una seconda scansione completa (~4s): e' il prezzo per misurare il
--    percorso che il digest usa davvero, e non un suo somigliante.
-- ============================================================
-- ⚠️ Il verbo in un'istruzione SUA, prima dell'asserzione: dentro la `SELECT`
--    non si droppa niente, e il `DELETE` della DEFINER arriverebbe comunque su
--    una temp table che non e' sua.
DROP TABLE IF EXISTS tmp_raw;

SELECT CASE
  WHEN NOT EXISTS (SELECT 1 FROM pg_extension WHERE extname = 'plpgsql_check')
    THEN skip('plpgsql_check assente: misura non eseguibile', 1)
  ELSE is(
    dbops.fn_conta_presidio('dbops.vw_riferimenti_morti_da_sanare'),
    (SELECT count(*)
       FROM misura m
      WHERE m.classe IN ('REALE', 'ORFANA', 'NON_MISURATO')
        AND NOT EXISTS (
              SELECT 1 FROM dbops.riferimenti_morti_esenzioni e
               WHERE e.schema_nome = m.schema_nome
                 AND e.funzione    = m.funzione
                 AND m.esito LIKE e.esito_like)),
    'il conteggio che legge il digest (fn_conta_presidio) concorda con la misura diretta'
  )
END;

SELECT * FROM finish();

ROLLBACK;
