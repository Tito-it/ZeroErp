-- ------------------------------------------------------------
-- SPDX-License-Identifier: GPL-3.0-or-later
-- Zero ERP — PRESIDIO sui riferimenti morti nelle funzioni
--
-- Brief: docs/it/dev/work-in-progress/brief-db-bonifica-riferimenti-morti.md §5
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
-- Indice test (1..5):
--   1. l'estensione plpgsql_check c'e' (senza, i test 2 e 3 fanno skip)
--   2. nessun difetto REALE/ORFANA fuori dal registro del debito
--   3. nessuna voce RIENTRATA nel registro (il debito deve calare)
--   4. ogni voce del registro ha un motivo scritto
--   5. nessun riferimento morto nei DATI di configurazione
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

SELECT plan(5);

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

SELECT * FROM finish();

ROLLBACK;
