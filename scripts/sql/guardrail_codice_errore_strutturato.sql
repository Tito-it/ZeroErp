-- ------------------------------------------------------------
-- SPDX-License-Identifier: AGPL-3.0-or-later
-- Guardrail CI — il contratto del codice errore strutturato
--   Brief: docs/it/dev/work-done/brief-db-codice-errore-strutturato.md §10
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
--   C) una voce del registro che non corrisponde piu' a nessun codice a seed
--      (o il cui codice e' stato ritirato): il debito e' pagato, la riga va tolta
--   D) una funzione viva che solleva un codice RITIRATO (`obsoleto_dal`)
--
-- ── ⚠️ `obsoleto_dal` HA CAMBIATO CASA il 2026-08-07 (changeSet 20260807-13) ──
--   Nasceva su `config.messaggi_errore` (20260805-17), che pero' e' chiavata
--   (codice, lingua): il ritiro era **per lingua**, cioe' si poteva ritirare un
--   codice in italiano e lasciarlo vivo in inglese senza che nulla protestasse.
--   Ora sta su `config.codici_errore`, che ha UNA riga per codice — il ritiro
--   appartiene al codice, non alla frase. I controlli (B), (C), (D) e il
--   riepilogo leggono da li'.
--   Piano: docs/it/dev/work-done/piano-db-classe-codici-errore.md (D-6)
--
-- ── `obsoleto_dal`, dal 2026-08-05 (changeSet 20260805-17) ───────────────
--   Un codice legacy spesso NON si puo' cancellare: `dbops.error_log` ha una FK
--   NOT NULL verso `config.messaggi_errore(id)`, e 46 codici su 53 hanno righe
--   di log. Si ritirano quindi valorizzando `obsoleto_dal` invece di
--   cancellarli — la riga resta, i log restano agganciati, il runtime continua
--   a risolvere il messaggio.
--   ⚠️ Una data FUTURA e' un ritiro programmato: il codice e' ancora in
--   servizio, quindi (B) continua a pretenderlo registrato e (D) non protesta.
--   Tutti i controlli qui sotto guardano `obsoleto_dal <= CURRENT_DATE`.
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
    v_mittenti       text;
    v_fuori          text;
    v_pagati         text;
    v_ritirati_vivi  text;
    v_registro_lock  text;
    v_warning_sollevati text;
    -- ⚠️ Deve restare IDENTICO al CHECK chk_messaggi_errore_codici_legacy_non_conforme
    --    (20260805-06, allargato da 20260805-28). Se i due divergono, il registro
    --    e il presidio finiscono per parlare di due insiemi diversi e nessuno se
    --    ne accorge.
    --
    -- ⚠️ DUE FAMIGLIE, NON UNA: `E_` sono errori e si sollevano; `W_` sono
    --    warning e si scrivono soltanto nel log (es. W_TXID_NOT_REGISTERED, il
    --    cui messaggio comincia con «Warning - »). Allargare la convenzione ai
    --    warning evita di rinominarli in `E_` per far tornare un conteggio,
    --    facendogli dire una cosa falsa — ma apre un buco che il controllo (E)
    --    chiude: un `W_` sollevato arriverebbe al backend, non troverebbe policy
    --    (la scorciatoia di resolve() e' solo per `E_`) e darebbe **HTTP 500**.
    c_convenzione CONSTANT text := '^[EW]_[A-Z0-9_]+$';
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
    --
    -- ⚠️ I codici RITIRATI (`obsoleto_dal` gia' scaduta) escono da questo
    -- controllo: non sono debito da registrare, sono debito **pagato** che non
    -- si e' potuto cancellare per via della FK di error_log. Pretenderli nel
    -- registro impedirebbe al registro di calare, che e' il suo unico scopo.
    --
    -- ── ⚠️ PERCHE' LA CONVENZIONE CONTA — RISCRITTO IL 2026-08-08 ──────
    --   Fino al 2026-08-07 la ragione era: «un codice fuori convenzione non
    --   trova policy, e la scorciatoia di ErrorPolicyRegistry.resolve vale solo
    --   per i codici E_, quindi cade su E_GENERICO = HTTP 500».
    --
    --   ⛔ **Quella ragione e' scaduta.** Dal passo B-5 del piano BE
    --   `error_policies_generated.py` e' GENERATO da config.vw_codici_errore_-
    --   identita e contiene TUTTI i codici a catalogo, non conformi compresi;
    --   `resolve()` cerca prima il nome esatto nel dizionario, e il ripiego sul
    --   prefisso scatta solo se il codice li' NON c'e'. Un codice non conforme
    --   ma a catalogo oggi risolve correttamente.
    --
    --   ⭐ La regola resta, con una ragione piu' stretta e piu' precisa:
    --     1. LA FINESTRA. Fra il seed di un codice nuovo lato DB e la
    --        rigenerazione lato BE il codice non e' nel dizionario, e a decidere
    --        400 invece di 500 resta il PREFISSO. E' una finestra reale: il
    --        codice nasce in un migrate e vive fino al commit del BE.
    --     2. LA SEPARAZIONE E_/W_. `E_` si solleva, `W_` si scrive soltanto nel
    --        diario. Non e' stile: e' il controllo (E) qui sotto, e un `W_`
    --        sollevato arriva all'operatore come un guasto.
    --
    --   La regola non e' cambiata, la sua giustificazione si'. Va tenuta vera:
    --   un presidio che si spiega con un fatto scaduto insegna una cosa falsa, e
    --   chi verifica la spiegazione e la trova sbagliata conclude che il
    --   presidio e' sbagliato. E' lo stesso guasto — la regola tiene, la ragione
    --   marcisce — contro cui e' costruito il cantiere della classe.
    SELECT string_agg(ce.codice, E'\n  ' ORDER BY ce.codice)
      INTO v_fuori
      FROM config.codici_errore ce
     WHERE ce.codice !~ c_convenzione
       AND (ce.obsoleto_dal IS NULL OR ce.obsoleto_dal > CURRENT_DATE)
       AND NOT EXISTS (
             SELECT 1 FROM dbops.messaggi_errore_codici_legacy l
              WHERE l.codice = ce.codice);

    IF v_fuori IS NOT NULL THEN
        RAISE EXCEPTION
          E'Codici errore fuori convenzione e non registrati:\n  %\n\n'
          'La convenzione e'' E_{MODULO}_{TIPO} (docs/it/dev/api.md), con E_ per gli '
          'errori e W_ per i warning.\n'
          'Conta per due ragioni, e la prima e'' una FINESTRA: fra il migrate che crea '
          'il codice e il commit con cui il backend rigenera error_policies_generated.py '
          'il codice non e'' ancora nel dizionario, e in quell''intervallo a decidere 400 '
          'invece di 500 resta il PREFISSO (ErrorPolicyRegistry.resolve ripiega su E_* '
          'per i codici che non trova, e su E_GENERICO — cioe'' HTTP 500 — per tutti gli '
          'altri). Un operatore che tenta una transizione non ammessa si vedrebbe un '
          'errore di server. La seconda ragione e'' la separazione E_/W_: i W_ si '
          'scrivono nel diario e non si sollevano — e'' il controllo (E) qui sotto.\n'
          '⚠️ NON e'' piu'' vero che un codice fuori convenzione «non trova policy»: dal '
          'passo B-5 il dizionario e'' generato dal catalogo e li contiene tutti. Il '
          'rischio e'' la finestra, non lo stato a regime.\n'
          'Due strade: rinominare il codice a E_* (seed CSV + call site + pgTAP che lo '
          'asseriscono), oppure — se e'' un codice che esisteva gia'' prima del presidio — '
          'registrarlo in dbops.messaggi_errore_codici_legacy. La seconda strada e'' per '
          'il debito EREDITATO, NON per i codici nuovi: quelli nascono giusti. E se '
          'quello che hai davanti non e'' un''eccezione ma una FAMIGLIA nuova con una '
          'semantica sua — com''e'' stato per i W_ nel 20260805-28 — la strada giusta e'' '
          'la terza: allargare la convenzione qui sopra, con la ragione nel changeSet. '
          'Una famiglia dentro un registro di eccezioni si perde.', v_fuori;
    END IF;

    -- ── (C) il debito deve calare ───────────────────────────────────
    --
    -- Simmetrico al controllo (B) del guardrail dei riferimenti morti. Se un
    -- codice registrato viene rinominato a E_* o eliminato, la sua riga nel
    -- registro non serve piu' e va tolta dal CSV
    -- (80_data/sql/dbops/messaggi_errore_codici_legacy.csv). Il seed e'
    -- DELETE + loadData proprio per questo: e' un mirror, non un upsert.
    -- Due modi di pagare il debito, ed entrambi contano: il codice non esiste
    -- piu' (cancellato), oppure e' stato RITIRATO con `obsoleto_dal` perche' la
    -- FK di error_log non ne permetteva la cancellazione.
    SELECT string_agg(l.codice || (CASE WHEN ce.codice IS NULL
                                        THEN ' (non piu'' a catalogo)'
                                        ELSE ' (ritirato il ' || ce.obsoleto_dal || ')' END),
                      E'\n  ' ORDER BY l.codice)
      INTO v_pagati
      FROM dbops.messaggi_errore_codici_legacy l
      LEFT JOIN config.codici_errore ce
             ON ce.codice = l.codice
     WHERE ce.codice IS NULL
        OR (ce.obsoleto_dal IS NOT NULL AND ce.obsoleto_dal <= CURRENT_DATE);

    IF v_pagati IS NOT NULL THEN
        RAISE EXCEPTION
          E'Voci di troppo nel registro dei codici legacy:\n  %\n\n'
          'Questi codici sono stati rinominati, eliminati o RITIRATI con obsoleto_dal: '
          'in tutti e tre i casi il debito e'' pagato. La riga va TOLTA da '
          'db/changelog/migrations_v2/80_data/sql/dbops/messaggi_errore_codici_legacy.csv '
          '(il loader e'' un mirror: DELETE + loadData, quindi basta togliere la riga). '
          'Non e'' pignoleria — un registro che si puo'' solo allungare smette di essere '
          'un registro e diventa il posto dove i problemi vanno a sparire.', v_pagati;
    END IF;

    -- ── (D) nessuna funzione viva solleva un codice ritirato ────────
    --
    -- ⚠️ E' il controllo che rende `obsoleto_dal` una promessa mantenuta invece
    -- di un'etichetta. Il ritiro si fa in due mosse — prima si tolgono i call
    -- site, poi si valorizza la data — e senza (D) niente impedirebbe a qualcuno
    -- di rimetterne uno: il codice tornerebbe a girare mentre il catalogo lo
    -- dichiara ritirato, e nessuno se ne accorgerebbe. E' esattamente il punto
    -- cieco del §4-bis della guida sui presidi: un'etichetta rassicurante e'
    -- piu' pericolosa di un errore, perche' nessuno la ricontrolla.
    --
    -- ── ⛔ DUE SUPERFICI, E LA SECONDA E' STATA CIECA PER 49 GIORNI ──
    --
    -- Un codice puo' arrivare a chi solleva in due modi, e fino al 2026-09-23
    -- questo controllo ne guardava UNO:
    --
    --   1. LETTERALE NEL CORPO — `p.prosrc`. E' la forma normale.
    --   2. ARGOMENTO DI UN TRIGGER — `pg_trigger.tgargs`. Quando la funzione di
    --      trigger e' GENERICA (script.trgfn_lock_columns, e non e' l'unica),
    --      il codice non sta in nessun corpo: e' scritto nel CREATE TRIGGER e
    --      arriva come TG_ARGV. In `pg_proc` non c'e'.
    --
    -- ⚠️ Non e' teoria. Il 2026-08-05 il changeSet 20260805-26 ritiro'
    -- CODICE_NON_MODIFICABILE censendo i call site «da pg_proc e non a memoria»
    -- — e corresse il generatore, ma non i trigger gia' generati. Il 2026-09-23
    -- erano **69 trigger su 68 tabelle in 8 schemi** a sollevare un codice
    -- ritirato, con questo controllo VERDE, perche' nessuna funzione plpgsql lo
    -- nominava piu' nel corpo. Bonificati da 90_end/20260923-02; il ramo (2)
    -- qui sotto e' il rubinetto, e senza di lui la stessa cosa si rifa'.
    --
    -- ⚠️ LIMITE CHE RESTA, da conoscere prima di fidarsi del verde: NON vede
    -- (a) i codici passati per espressione — ma quelli escono dai `fn_check_*`,
    -- che ritornano codici `E_*` e quindi non ritirabili per questa strada — e
    -- (b) i codici sollevati dal **Python**: questo e' uno script SQL,
    -- `backend/` non lo puo' leggere. Per quelli il presidio e' il test
    -- `test_error_codes_declared_guardrail` lato BE.
    SELECT string_agg(x.riga, E'\n  ' ORDER BY x.riga)
      INTO v_ritirati_vivi
      FROM (
        -- (1) il letterale nel corpo di una funzione plpgsql
        SELECT DISTINCT ce.codice || '  <-  corpo di ' || n.nspname || '.' || p.proname AS riga
          FROM config.codici_errore ce
          JOIN pg_proc p
            ON p.prosrc LIKE '%' || quote_literal(ce.codice) || '%'
          JOIN pg_namespace n
            ON n.oid = p.pronamespace
         WHERE ce.obsoleto_dal IS NOT NULL
           AND ce.obsoleto_dal <= CURRENT_DATE
           AND p.prolang = (SELECT oid FROM pg_language WHERE lanname = 'plpgsql')
           AND n.nspname NOT IN ('pg_catalog', 'information_schema')

        UNION ALL

        -- (2) l'argomento di un trigger su una funzione GENERICA: il codice non
        --     e' in nessun corpo, e' in pg_trigger.tgargs. Gli argomenti li
        --     legge dbops.fn_trigger_argomenti (dal 2026-09-26, building block:
        --     prima qui c'era una decodifica sua con encode(...,'escape')), e si
        --     confronta per UGUAGLIANZA — non con un LIKE, che su
        --     CODICE_NON_MODIFICABILE aggancerebbe anche E_CODICE_NON_MODIFICABILE,
        --     cioe' il codice VIVO.
        SELECT DISTINCT ce.codice || '  <-  trigger ' || tn.nspname || '.'
               || tc.relname || '.' || t.tgname AS riga
          FROM config.codici_errore ce
          JOIN pg_trigger t
            ON NOT t.tgisinternal
           AND ce.codice = ANY (dbops.fn_trigger_argomenti(t.tgargs))
          JOIN pg_class tc     ON tc.oid = t.tgrelid
          JOIN pg_namespace tn ON tn.oid = tc.relnamespace
         WHERE ce.obsoleto_dal IS NOT NULL
           AND ce.obsoleto_dal <= CURRENT_DATE
           AND tn.nspname NOT IN ('pg_catalog', 'information_schema')
      ) x;

    IF v_ritirati_vivi IS NOT NULL THEN
        RAISE EXCEPTION
          E'Codici RITIRATI ancora sollevati da funzioni vive:\n  %\n\n'
          'La colonna config.codici_errore.obsoleto_dal dichiara questi codici fuori '
          'servizio, ma il DB li solleva ancora. Una delle due cose e'' falsa. '
          'Il ritiro si fa in QUEST''ORDINE: prima si tolgono i call site (changeSet '
          '20_code, sostituendo il codice con quello nuovo `E_*`), poi si valorizza '
          'obsoleto_dal nel CSV config/codici_errore.csv. Se il codice serve ancora, va '
          'rimessa a NULL la data: ritirarlo e continuare a usarlo e'' la forma peggiore '
          'di debito, perche'' sembra pagato.\n'
          '⚠️ Se la riga dice «trigger», il call site NON e'' in un corpo: il codice sta '
          'negli argomenti del CREATE TRIGGER, e per una funzione generica come '
          'script.trgfn_lock_columns quegli argomenti li calcola l''automazione dal suo '
          'registro: quel trigger non si riscrive a mano. Si corregge la riga del '
          'registro (dbops.automation_lock_columns) e si droppa il trigger perche'' '
          'l''automazione lo rifaccia — stampo: 90_end/20260923-02.', v_ritirati_vivi;
    END IF;

    -- ── (E) un codice di WARNING non si solleva, si logga ───────────
    --
    -- ⚠️ E' il prezzo di aver allargato la convenzione ai `W_`. La scorciatoia
    -- di `ErrorPolicyRegistry.resolve` («codice non registrato che comincia per
    -- E_ -> 400») vale SOLO per `E_`: un `W_` che arrivasse al backend cadrebbe
    -- su `E_GENERICO` -> **HTTP 500**. Cioe' il difetto da cui nasce questa
    -- slice, reintrodotto da una regola allentata.
    --
    -- La regola in una riga: **`E_` si solleva, `W_` si scrive nel log.**
    -- `fn_log_error_only` resta lecito per entrambi; `fn_log_and_raise_error` no.
    SELECT string_agg(DISTINCT n.nspname || '.' || p.proname || '  ->  ' || m[1],
                      E'\n  ' ORDER BY n.nspname || '.' || p.proname || '  ->  ' || m[1])
      INTO v_warning_sollevati
      FROM pg_proc p
      JOIN pg_namespace n ON n.oid = p.pronamespace,
      LATERAL regexp_matches(p.prosrc, 'fn_log_and_raise_error[^;]*?''(W_[A-Z0-9_]+)''', 'g') AS m
     WHERE n.nspname NOT IN ('pg_catalog', 'information_schema')
       AND p.prolang = (SELECT oid FROM pg_language WHERE lanname = 'plpgsql');

    IF v_warning_sollevati IS NOT NULL THEN
        RAISE EXCEPTION
          E'Codici di WARNING sollevati come errori:\n  %\n\n'
          'Un codice `W_` puo'' essere scritto nel log (script.fn_log_error_only) ma non '
          'sollevato (script.fn_log_and_raise_error). Sollevato arriva al backend, dove '
          'la scorciatoia di ErrorPolicyRegistry.resolve vale solo per i codici `E_`: '
          'cadrebbe su E_GENERICO, cioe'' **HTTP 500** — un errore di server per quello '
          'che doveva essere un avviso.\n'
          'Due strade: usare fn_log_error_only se e'' davvero un avviso, oppure — se e'' '
          'un errore — dargli un codice `E_` e registrarlo in error_policies.py.', v_warning_sollevati;
    END IF;

    -- ── (F) un solo mittente anche sul canale COLUMN ────────────────
    --
    -- Gemello del controllo (A), e nasce insieme al canale (20260808-04).
    -- Dal 2026-08-08 `COLUMN` porta il NOME DEL CAMPO che l'operatore deve
    -- correggere, e il frontend ci accende un bordo rosso.
    --
    -- ⚠️ Perche' presidiarlo SUBITO, con zero violazioni. Il controllo (A) e'
    -- nato quando CONSTRAINT era gia' in uso, e ha dovuto rincorrere. Qui il
    -- canale e' libero — misurato: 0 mittenti — e un presidio che nasce a zero
    -- non deve mai chiedere a nessuno di sanare un arretrato. E' la stessa
    -- ragione per cui il rubinetto dei codici fuori convenzione fu chiuso
    -- prima di smaltire i 57.
    --
    -- ⚠️ E il modo in cui questo canale rompe e' peggio degli altri: un secondo
    -- mittente non fa fallire niente, fa **evidenziare il campo sbagliato**.
    -- L'operatore viene mandato a correggere un dato che e' giusto, con la
    -- pagina che gliela indica come se fosse sicura.
    SELECT string_agg(n.nspname || '.' || p.proname, E'\n  ' ORDER BY n.nspname, p.proname)
      INTO v_mittenti
      FROM pg_proc p
      JOIN pg_namespace n ON n.oid = p.pronamespace
     WHERE p.prolang = (SELECT oid FROM pg_language WHERE lanname = 'plpgsql')
       AND n.nspname NOT IN ('pg_catalog', 'information_schema')
       AND p.prosrc ~* 'RAISE[^;]*USING[^;]*\mCOLUMN\M\s*='
       AND NOT (n.nspname = 'script' AND p.proname = 'fn_log_and_raise_error');

    IF v_mittenti IS NOT NULL THEN
        RAISE EXCEPTION
          E'Il canale COLUMN ha piu'' di un mittente:\n  %\n\n'
          'Dal 2026-08-08 il campo COLUMN dell''eccezione e'' riservato al NOME DEL CAMPO '
          'che l''operatore deve correggere — contratto «P0001 + COLUMN valorizzato = il '
          'campo da correggere» (changeSet 20260808-04) — e l''unica sede autorizzata a '
          'scriverlo e'' script.fn_log_and_raise_error, che lo prende da '
          'p_context->>''campo''.\n'
          'Il frontend ci accende un bordo rosso sul campo: se ci finisce dentro altro, '
          'non fallisce niente — evidenzia il campo SBAGLIATO, e manda l''operatore a '
          'correggere un dato che e'' giusto. E'' peggio di non evidenziarne nessuno.\n'
          'La strada e'' passare da fn_log_and_raise_error mettendo il nome del campo nel '
          'contesto: jsonb_build_object(''campo'', ''nome_campo'', ...).', v_mittenti;
    END IF;

    -- ── (G) un solo mittente anche sul canale DATATYPE ──────────────
    --
    -- Terzo gemello, e nasce insieme al canale (20260823-02). Dal 2026-08-23
    -- `DATATYPE` porta il BERSAGLIO dell'errore — su quali entita' si
    -- riferisce, nella forma TIPO:id[,TIPO:id] — e il frontend ci disegna un
    -- pulsante «vai al documento».
    --
    -- ⚠️ Nasce a ZERO mittenti, come (F) e a differenza di (A): un presidio che
    -- parte da zero non chiede mai a nessuno di sanare un arretrato.
    --
    -- ⚠️ E il modo in cui questo canale rompe e' il peggiore dei tre. Un
    -- CONSTRAINT sbagliato fa decidere male uno status; un COLUMN sbagliato
    -- evidenzia il campo sbagliato; un DATATYPE sbagliato **porta l'operatore
    -- da un'altra parte** — apre un documento che non c'entra, con la pagina
    -- che gliel'ha proposto come se fosse sicura. Un bersaglio sbagliato e'
    -- peggio di nessun bersaglio, ed e' la ragione per cui la derivazione
    -- automatica dalle chiavi del context e' stata rimandata.
    --
    -- ⚠️ Fuori da P0001 quel campo lo riempie PostgreSQL da se' (le violazioni
    -- di dominio): il contratto vale SOLO dentro P0001, come per CONSTRAINT.
    SELECT string_agg(n.nspname || '.' || p.proname, E'\n  ' ORDER BY n.nspname, p.proname)
      INTO v_mittenti
      FROM pg_proc p
      JOIN pg_namespace n ON n.oid = p.pronamespace
     WHERE p.prolang = (SELECT oid FROM pg_language WHERE lanname = 'plpgsql')
       AND n.nspname NOT IN ('pg_catalog', 'information_schema')
       AND p.prosrc ~* 'RAISE[^;]*USING[^;]*\mDATATYPE\M\s*='
       AND NOT (n.nspname = 'script' AND p.proname = 'fn_log_and_raise_error');

    IF v_mittenti IS NOT NULL THEN
        RAISE EXCEPTION
          E'Il canale DATATYPE ha piu'' di un mittente:\n  %\n\n'
          'Dal 2026-08-23 il campo DATATYPE dell''eccezione e'' riservato al BERSAGLIO '
          'dell''errore — le entita'' a cui si riferisce, nella forma TIPO:id[,TIPO:id] — '
          'contratto «P0001 + DATATYPE valorizzato = il bersaglio» (changeSet '
          '20260823-02), e l''unica sede autorizzata a scriverlo e'' '
          'script.fn_log_and_raise_error, che lo compone da p_context->''bersaglio''.\n'
          'Il frontend ci disegna sopra un pulsante: se ci finisce dentro altro, non '
          'fallisce niente — porta l''operatore su un documento che non c''entra, e '
          'gliel''ha proposto la pagina. E'' peggio di non proporne nessuno.\n'
          'La strada e'' passare da fn_log_and_raise_error mettendo il bersaglio nel '
          'contesto: jsonb_build_object(''bersaglio'', jsonb_build_array('
          'jsonb_build_object(''tipo'', ''FATTURA'', ''id'', v_id::text))).', v_mittenti;
    END IF;

    -- ── (H) il registro dei lock nomina solo codici VIVI ───────────
    --
    -- ⭐ E' il RUBINETTO del difetto che (D) ramo (2) trova a valle. Una riga di
    -- dbops.automation_lock_columns e' un call site DIFFERITO: il codice non
    -- solleva niente finche' l'automazione non genera il trigger, e da quel
    -- momento lo solleva per sempre. Se la riga nomina un codice sbagliato, il
    -- difetto nasce in silenzio e si manifesta mesi dopo, alla prima
    -- rigenerazione — cioe' quando nessuno lo sta piu' guardando.
    --
    -- ⚠️ Misurato il 2026-09-23, prima della bonifica: su 38 righe, **25**
    -- nominavano un codice RITIRATO (CODICE_NON_MODIFICABILE) e **1** un codice
    -- che a catalogo NON ESISTE (EMITTENTE_NON_MODIFICABILE, sfuggito alla
    -- stessa rinomina del 2026-08-05: il vivo e' E_EMITTENTE_NON_MODIFICABILE).
    -- Quella riga era innocua solo perche' il suo trigger non era mai stato
    -- rigenerato: armata, avrebbe risposto «[MESSAGGIO NON DEFINITO]».
    --
    -- ⛔ Non e' una FK, ed e' una scelta: il registro e' un CSV di 80_data e il
    -- catalogo dei codici pure, una FK fra due mirror li legherebbe nell'ordine
    -- di caricamento. Qui il controllo e' a valle, dove costa niente.
    SELECT string_agg(x.riga, E'\n  ' ORDER BY x.riga)
      INTO v_registro_lock
      FROM (
        SELECT l.target_schema || '.' || l.target_table || '.' || l.column_name
               || '  ->  ' || l.error_code || '  ('
               || CASE WHEN ce.codice IS NULL THEN 'non esiste a catalogo'
                       ELSE 'ritirato il ' || ce.obsoleto_dal::text END
               || CASE WHEN l.enabled THEN ', attiva' ELSE ', spenta' END || ')' AS riga
          FROM dbops.automation_lock_columns l
          LEFT JOIN config.codici_errore ce ON ce.codice = l.error_code
         WHERE l.error_code IS NOT NULL
           AND (ce.codice IS NULL
                OR (ce.obsoleto_dal IS NOT NULL AND ce.obsoleto_dal <= CURRENT_DATE))
      ) x;

    IF v_registro_lock IS NOT NULL THEN
        RAISE EXCEPTION
          E'Il registro dei lock nomina codici non vivi:\n  %\n\n'
          'Ogni riga di dbops.automation_lock_columns e'' un call site differito: '
          'l''automazione scrive quel codice negli argomenti del trigger che genera, e da '
          'li'' in poi il lock lo solleva. Un codice assente dal catalogo produce '
          '«[MESSAGGIO NON DEFINITO: ...]» a video; uno ritirato rimette in servizio un '
          'debito dichiarato pagato.\n'
          'Si corregge la riga nel CSV '
          'db/changelog/migrations_v2/80_data/sql/dbops/automation_lock_columns.csv '
          '(mirror runOnChange: si ricarica da solo). ⚠️ E il CSV da solo NON basta se il '
          'trigger esiste gia'': l''automazione crea solo se manca, non confronta gli '
          'argomenti — va droppato perche'' venga rifatto (stampo: 90_end/20260923-02).',
          v_registro_lock;
    END IF;

    RAISE NOTICE 'OK — un solo mittente sui canali CONSTRAINT, COLUMN e DATATYPE, nessun codice fuori convenzione non registrato, nessuna voce di troppo nel registro (% attive), nessun codice ritirato ancora sollevato (% ritirati) ne'' nei corpi ne'' negli argomenti dei % trigger, nessuna delle % righe del registro dei lock nomina un codice non vivo, nessun warning sollevato come errore.',
        (SELECT count(*) FROM dbops.messaggi_errore_codici_legacy),
        (SELECT count(*) FROM config.codici_errore
          WHERE obsoleto_dal IS NOT NULL AND obsoleto_dal <= CURRENT_DATE),
        (SELECT count(*) FROM pg_trigger WHERE NOT tgisinternal),
        (SELECT count(*) FROM dbops.automation_lock_columns);
END
$guardrail$;
