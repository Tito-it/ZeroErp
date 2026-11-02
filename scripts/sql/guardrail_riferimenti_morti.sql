-- ------------------------------------------------------------
-- SPDX-License-Identifier: AGPL-3.0-or-later
-- Guardrail CI — riferimenti morti nelle funzioni plpgsql
--   Brief: docs/it/dev/work-done/brief-db-bonifica-riferimenti-morti.md §5
--
-- FALLISCE (RAISE EXCEPTION) se trova:
--   A-bis) una funzione che plpgsql_check NON HA POTUTO controllare
--      (classe NON_MISURATO). ⭐ Va per prima: se lo strumento non ha
--      misurato, (A) non sa dire quali difetti ci sono e (B) vedrebbe ogni
--      voce del registro come «rientrata». Dal 2026-09-10, brief §9.3
--   A) un difetto REALE/ORFANA non presente nel registro del debito
--      (dbops.riferimenti_morti_esenzioni)
--   B) una voce del registro che non corrisponde piu' a nessun difetto:
--      il debito e' stato pagato, la riga va tolta
--   C) una riga di configurazione che nomina per stringa una tabella
--      inesistente
--
-- Uso (read-only):
--   psql "$DB_URL" -v ON_ERROR_STOP=1 -f scripts/sql/guardrail_riferimenti_morti.sql
--
-- ── PERCHE' UNO SCRIPT E NON IL pgTAP ────────────────────────────────────
--   La suite pgTAP non gira in CI (solo Liquibase e i test Django). Questo
--   file segue lo stesso schema gia' in uso per
--   `scripts/sql/check_naming_stato_codice.sql`: un `DO` che solleva, e con
--   `ON_ERROR_STOP=1` il passo della CI diventa rosso.
--   Non duplica pero' la logica del pgTAP: entrambi leggono la **stessa**
--   misura e lo **stesso** registro, che vivono nel DB (`20260804-62/63/64`).
--   Qui cambia solo come si riporta l'esito.
--
-- ── ⚠️ SE L'ESTENSIONE MANCA, QUESTO GUARDRAIL NON MISURA ───────────────
--   `plpgsql_check` viene da un pacchetto di sistema
--   (`postgresql-18-plpgsql-check`) che va installato nell'immagine.
--   Senza, il controllo (A) e (B) NON puo' girare: qui si sceglie di
--   **fallire**, non di saltare in silenzio. Un guardrail che passa perche'
--   non ha misurato niente e' peggio di un guardrail assente — da' la
--   sensazione della copertura senza averla, che e' esattamente il modo in
--   cui `test-fn-search-stradario.sql` e' rimasto rosso per mesi sotto
--   un'etichetta sbagliata.
--   Il controllo (C) invece non dipende dall'estensione e gira comunque.
-- ------------------------------------------------------------

\set ON_ERROR_STOP on

DO $guardrail$
DECLARE
    v_da_sanare    text;
    v_rientrati    text;
    v_dati         text;
    v_non_misurate text;
    v_quante       bigint;
BEGIN
    -- ── (C) prima, perche' non dipende dall'estensione ──────────────
    SELECT string_agg(sc.codice_interno || ' -> ' || sc.schema_tabella || '.' || sc.nome_tabella,
                      E'\n  ' ORDER BY sc.codice_interno)
      INTO v_dati
      FROM config.sistema_codici sc
     WHERE sc.nome_tabella IS NOT NULL
       AND to_regclass(sc.schema_tabella || '.' || sc.nome_tabella) IS NULL;

    IF v_dati IS NOT NULL THEN
        RAISE EXCEPTION
          E'Riferimenti morti nei DATI di configurazione:\n  %\n\n'
          'Una riga di config.sistema_codici nomina per stringa una tabella che non '
          'esiste. Non e'' un difetto che plpgsql_check possa vedere: compila i corpi, '
          'e li'' il nome arriva come parametro. Va rimossa con un changeSet 80_data '
          '(precedente: 20260804-50).', v_dati;
    END IF;

    -- ── L'estensione serve per (A) e (B) ────────────────────────────
    IF NOT EXISTS (SELECT 1 FROM pg_extension WHERE extname = 'plpgsql_check') THEN
        RAISE EXCEPTION
          'Estensione plpgsql_check assente: il guardrail non puo'' misurare. '
          'Installare il pacchetto postgresql-18-plpgsql-check nell''immagine e '
          'rilanciare il giro provision di Liquibase (changeSet 20260804-36, che e'' '
          'condizionale e si riprende da solo). NON si passa in silenzio: un '
          'guardrail che non misura e non lo dice e'' peggio di uno assente.';
    END IF;

    -- ⚠️ La misura si materializza UNA volta: compila ~500 funzioni.
    --    (A) e (B) sono due anti-join sullo stesso dato; passare dalle due
    --    viste la pagherebbe due volte.
    CREATE TEMP TABLE tmp_misura ON COMMIT DROP AS
    SELECT * FROM dbops.fn_check_funzioni_riferimenti_morti();

    -- ── (A-bis) 🔴 LO STRUMENTO HA MISURATO DAVVERO? ────────────────
    --   Va PRIMA di (A) e (B), e non e' un ordine estetico: se
    --   plpgsql_check ha sollevato invece di rispondere, (A) non sa dire
    --   quali difetti ci sono e (B) vedrebbe OGNI voce del registro come
    --   «rientrata» — due risposte sbagliate con l'aria di essere giuste.
    --
    -- ⛔ Il caso e' successo il 2026-09-10: su dbdev plpgsql_check ha fallito
    --   su quasi ogni funzione e la misura ha prodotto 779 righe su 780. Fino
    --   al changeSet 20260910-36 quelle uscivano come REALE, quindi (A)
    --   sollevava dicendo «779 riferimenti morti»: la diagnosi sbagliata, e
    --   779 cose da cercare che non esistono.
    --
    -- ⭐ La regola era gia' qui sopra, per l'estensione ASSENTE: «NON si passa
    --   in silenzio: un guardrail che non misura e non lo dice e' peggio di
    --   uno assente». Questo e' lo stesso caso — l'estensione c'e' e si rompe —
    --   e fino a oggi aveva l'esito opposto.
    SELECT count(*),
           string_agg(x.riga, E'\n  ' ORDER BY x.riga)
      INTO v_quante, v_non_misurate
      FROM (
        SELECT DISTINCT m.schema_nome || '.' || m.funzione || '  ->  ' || m.esito AS riga
          FROM tmp_misura m
         WHERE m.classe = 'NON_MISURATO'
      ) x;

    IF v_non_misurate IS NOT NULL THEN
        RAISE EXCEPTION
          E'plpgsql_check NON HA POTUTO CONTROLLARE % funzioni:\n  %\n\n'
          'Non e'' un elenco di difetti: e'' lo STRUMENTO che ha sollevato invece di '
          'rispondere, e quindi di quelle funzioni non si sa niente. Il guardrail si '
          'ferma qui di proposito: dire «nessun riferimento morto» dopo aver mancato '
          'la misura sarebbe la cosa peggiore che possa fare. '
          'Da guardare: la versione di plpgsql_check contro quella di PostgreSQL, e il '
          'log del server — se il processo e'' MORTO (segnale 11) il messaggio non '
          'arriva nemmeno qui. Brief: brief-db-un-destinatario-per-i-presidi §9.3.',
          v_quante, v_non_misurate;
    END IF;

    -- ── (A) difetti non registrati ──────────────────────────────────
    SELECT string_agg(x.riga, E'\n  ' ORDER BY x.riga)
      INTO v_da_sanare
      FROM (
        SELECT DISTINCT m.classe || '  ' || m.schema_nome || '.' || m.funzione
                        || '  ->  ' || m.esito AS riga
          FROM tmp_misura m
         WHERE m.classe IN ('REALE', 'ORFANA')
           AND NOT EXISTS (
                 SELECT 1 FROM dbops.riferimenti_morti_esenzioni e
                  WHERE e.schema_nome = m.schema_nome
                    AND e.funzione    = m.funzione
                    AND m.esito LIKE e.esito_like)
      ) x;

    IF v_da_sanare IS NOT NULL THEN
        RAISE EXCEPTION
          E'Riferimenti morti non registrati:\n  %\n\n'
          'Ogni riga e'' una funzione che non compila: tabella o colonna che non '
          'esiste, variabile speciale sbagliata, ramo senza RETURN. Non aspetta la '
          'prima esecuzione per fallire, l''ha gia'' fatto — semplicemente nessuno '
          'l''ha ancora eseguita. Due strade: riparare (e'' quasi sempre una riga), '
          'oppure registrare il debito in dbops.riferimenti_morti_esenzioni CON UN '
          'MOTIVO scritto. Per capire cosa sta succedendo: '
          'psql -f scripts/sql/check_funzioni_riferimenti_morti.sql', v_da_sanare;
    END IF;

    -- ── (B) voci del registro ormai di troppo ───────────────────────
    SELECT string_agg(e.schema_nome || '.' || e.funzione || '  (registrata il ' ||
                      e.data_registrazione || ')', E'\n  ' ORDER BY e.funzione)
      INTO v_rientrati
      FROM dbops.riferimenti_morti_esenzioni e
     WHERE NOT EXISTS (
             SELECT 1 FROM tmp_misura m
              WHERE m.classe IN ('REALE', 'ORFANA')
                AND m.schema_nome = e.schema_nome
                AND m.funzione    = e.funzione
                AND m.esito LIKE e.esito_like);

    IF v_rientrati IS NOT NULL THEN
        RAISE EXCEPTION
          E'Voci di troppo nel registro del debito:\n  %\n\n'
          'Questi difetti non ci sono piu'': la riga va TOLTA dal registro con un '
          'changeSet 80_data. Non e'' pignoleria — un registro che si puo'' solo '
          'allungare smette di essere un registro e diventa il posto dove i problemi '
          'vanno a sparire.', v_rientrati;
    END IF;

    RAISE NOTICE 'OK — nessun riferimento morto fuori registro, nessuna voce di troppo, dati di configurazione puliti.';
END
$guardrail$;
