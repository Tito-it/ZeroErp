-- ------------------------------------------------------------
-- SPDX-License-Identifier: GPL-3.0-or-later
-- Guardrail CI — il contratto del codice errore strutturato
--   Brief: docs/it/dev/work-in-progress/brief-db-codice-errore-strutturato.md §10
--   Funzione presidiata: script.fn_log_and_raise_error (20260805-05)
--   Registro letto: dbops.messaggi_errore_codici_legacy (20260805-06/07)
--
-- IL CONTRATTO, in una riga:
--   «SQLSTATE P0001 + campo CONSTRAINT valorizzato = errore di dominio, e il
--    contenuto di CONSTRAINT e' il codice di config.messaggi_errore».
--
-- Su quella condizione il backend decide se un errore vale 409, 404, 403 o 400
-- e quale messaggio legge l'operatore. Finche' resta un commento dentro a una
-- funzione, e' una convenzione; qui diventa una regola.
--
-- FALLISCE (RAISE EXCEPTION) se trova:
--   A) un `RAISE ... USING ... CONSTRAINT =` fuori da fn_log_and_raise_error
--   B) un codice di config.messaggi_errore fuori convenzione e non registrato
--      nel debito
--   C) una voce del registro che non corrisponde piu' a nessun codice a seed:
--      il debito e' stato pagato, la riga va tolta
--
-- Uso (read-only, nessuna scrittura):
--   psql "$DB_URL" -v ON_ERROR_STOP=1 -f scripts/sql/guardrail_codice_errore_strutturato.sql
--
-- ── PERCHE' UNO SCRIPT E NON IL pgTAP ────────────────────────────────────
--   Stessa ragione di `guardrail_riferimenti_morti.sql`: la suite pgTAP non
--   gira in CI (girano Liquibase e i test Django). Un `DO` che solleva, e con
--   `ON_ERROR_STOP=1` il passo della CI diventa rosso.
--   I pgTAP di `db/pgtap/script/test-fn-log-and-raise-error-constraint-codice.sql`
--   coprono l'altra meta': che il campo esca valorizzato e col contenuto
--   giusto. Qui si copre che nessun altro lo scriva.
-- ------------------------------------------------------------

\set ON_ERROR_STOP on

DO $guardrail$
DECLARE
    v_mittenti   text;
    v_fuori      text;
    v_pagati     text;
    -- ⚠️ Deve restare IDENTICO al CHECK chk_messaggi_errore_codici_legacy_non_conforme
    --    (20260805-06). Se i due divergono, il registro e il presidio finiscono
    --    per parlare di due insiemi diversi e nessuno se ne accorge.
    c_convenzione CONSTANT text := '^E_[A-Z0-9_]+$';
BEGIN
    -- ── (A) un solo mittente autorizzato sul canale CONSTRAINT ──────
    --
    -- Perche' serve: il backend si fida del campo quando SQLSTATE e' P0001.
    -- Ma P0001 e' anche il default di QUALUNQUE `RAISE EXCEPTION` scritto a
    -- mano, e nel DB ce ne sono 135 in 46 funzioni. Il giorno in cui uno di
    -- quelli usasse `USING CONSTRAINT` per dire altro — il nome di un vincolo,
    -- una nota di debug — il backend lo leggerebbe come un codice di dominio e
    -- risolverebbe una policy che non c'entra. Non fallirebbe niente: darebbe
    -- solo la risposta sbagliata.
    --
    -- La ricerca resta dentro allo stesso statement (`[^;]*` fra RAISE e
    -- CONSTRAINT): senza, qualunque funzione che nomina un vincolo per altri
    -- motivi (`EXECUTE format('ALTER TABLE ... ADD CONSTRAINT ...')`) sarebbe
    -- un falso positivo. Verificato il 2026-08-05: 36 funzioni nominano
    -- CONSTRAINT, nessuna di queste viene raccolta.
    SELECT string_agg(n.nspname || '.' || p.proname, E'\n  ' ORDER BY n.nspname, p.proname)
      INTO v_mittenti
      FROM pg_proc p
      JOIN pg_namespace n ON n.oid = p.pronamespace
     WHERE p.prolang = (SELECT oid FROM pg_language WHERE lanname = 'plpgsql')
       AND n.nspname NOT IN ('pg_catalog', 'information_schema')
       AND p.prosrc ~* 'RAISE[^;]*USING[^;]*CONSTRAINT\s*='
       AND NOT (n.nspname = 'script' AND p.proname = 'fn_log_and_raise_error');

    IF v_mittenti IS NOT NULL THEN
        RAISE EXCEPTION
          E'Il canale CONSTRAINT ha piu'' di un mittente:\n  %\n\n'
          'Il campo CONSTRAINT dell''eccezione e'' riservato al CODICE di dominio, e '
          'l''unica sede autorizzata a scriverlo e'' script.fn_log_and_raise_error '
          '(changeSet 20260805-05). Il backend, su SQLSTATE P0001, lo legge come se '
          'fosse un codice di config.messaggi_errore e ci risolve la policy HTTP: se '
          'ci finisce dentro altro, non fallisce niente — risponde sbagliato, che e'' '
          'peggio. Sollevare passando da fn_log_and_raise_error, che oltre al campo '
          'porta anche il messaggio localizzato, causa, soluzione e la riga di log.', v_mittenti;
    END IF;

    -- ── il registro deve esserci: senza, (B) e (C) non misurano ─────
    --
    -- Stessa scelta del guardrail dei riferimenti morti sull'estensione
    -- plpgsql_check: si FALLISCE, non si salta in silenzio. Un presidio che
    -- passa perche' non ha misurato niente e' peggio di un presidio assente,
    -- perche' da' la sensazione della copertura senza averla.
    IF to_regclass('dbops.messaggi_errore_codici_legacy') IS NULL THEN
        RAISE EXCEPTION
          'Registro dbops.messaggi_errore_codici_legacy assente: i controlli (B) e (C) '
          'non possono misurare. Applicare i changeSet 20260805-06 (tabella) e '
          '20260805-07 (le 57 voci). NON si passa in silenzio.';
    END IF;

    -- ── (B) il rubinetto: nessun codice NUOVO fuori convenzione ─────
    --
    -- `docs/it/dev/api.md` dichiara `E_{MODULO}_{TIPO}`. Il presidio pero'
    -- controlla solo il PREFISSO e l'alfabeto, non la forma piena, e la
    -- differenza e' voluta: 13 codici conformi e in uso hanno un solo
    -- underscore (E_DATABASE, E_GENERICO, E_TOKEN, E_PIPELINE...), diversi dei
    -- quali registrati in error_policies.py. Stringere fino alla forma piena
    -- vorrebbe dire un secondo registro da 13 voci per comprare niente:
    -- quello che serve al backend e' il prefisso, perche' e' su quello che
    -- `ErrorPolicyRegistry.resolve` decide 400 invece di 500.
    SELECT string_agg(DISTINCT me.codice, E'\n  ' ORDER BY me.codice)
      INTO v_fuori
      FROM config.messaggi_errore me
     WHERE me.codice !~ c_convenzione
       AND NOT EXISTS (
             SELECT 1 FROM dbops.messaggi_errore_codici_legacy l
              WHERE l.codice = me.codice);

    IF v_fuori IS NOT NULL THEN
        RAISE EXCEPTION
          E'Codici errore fuori convenzione e non registrati:\n  %\n\n'
          'La convenzione e'' E_{MODULO}_{TIPO} (docs/it/dev/api.md). Un codice senza '
          'prefisso E_ arriva al backend ma non trova policy, e la scorciatoia di '
          'ErrorPolicyRegistry.resolve vale solo per i codici E_: tutto il resto cade '
          'su E_GENERICO, cioe'' HTTP 500. Un operatore che tenta una transizione non '
          'ammessa si vedrebbe un errore di server.\n'
          'Due strade: rinominare il codice a E_* (seed CSV + call site + pgTAP che lo '
          'asseriscono), oppure — se e'' un codice che esisteva gia'' prima del presidio — '
          'registrarlo in dbops.messaggi_errore_codici_legacy. La seconda strada e'' per '
          'il debito ereditato del 2026-08-05, NON per i codici nuovi: quelli nascono '
          'giusti.', v_fuori;
    END IF;

    -- ── (C) il debito deve calare ───────────────────────────────────
    --
    -- Simmetrico al controllo (B) del guardrail dei riferimenti morti. Se un
    -- codice registrato viene rinominato a E_* o eliminato, la sua riga nel
    -- registro non serve piu' e va tolta dal CSV
    -- (80_data/sql/dbops/messaggi_errore_codici_legacy.csv). Il seed e'
    -- DELETE + loadData proprio per questo: e' un mirror, non un upsert.
    SELECT string_agg(l.codice, E'\n  ' ORDER BY l.codice)
      INTO v_pagati
      FROM dbops.messaggi_errore_codici_legacy l
     WHERE NOT EXISTS (
             SELECT 1 FROM config.messaggi_errore me
              WHERE me.codice = l.codice);

    IF v_pagati IS NOT NULL THEN
        RAISE EXCEPTION
          E'Voci di troppo nel registro dei codici legacy:\n  %\n\n'
          'Questi codici non esistono piu'' in config.messaggi_errore: sono stati '
          'rinominati o eliminati, cioe'' il debito e'' stato pagato. La riga va TOLTA '
          'da db/changelog/migrations_v2/80_data/sql/dbops/messaggi_errore_codici_legacy.csv '
          '(il loader e'' un mirror: DELETE + loadData, quindi basta togliere la riga). '
          'Non e'' pignoleria — un registro che si puo'' solo allungare smette di essere '
          'un registro e diventa il posto dove i problemi vanno a sparire.', v_pagati;
    END IF;

    RAISE NOTICE 'OK — un solo mittente sul canale CONSTRAINT, nessun codice fuori convenzione non registrato, nessuna voce di troppo nel registro (% registrate).',
        (SELECT count(*) FROM dbops.messaggi_errore_codici_legacy);
END
$guardrail$;
