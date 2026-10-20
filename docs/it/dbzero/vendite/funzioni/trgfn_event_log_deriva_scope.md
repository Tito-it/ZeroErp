# ⚙️ Funzione `trgfn_event_log_deriva_scope`

```sql
CREATE FUNCTION trgfn_event_log_deriva_scope()
```

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION vendite.trgfn_event_log_deriva_scope()
 RETURNS trigger
 LANGUAGE plpgsql
AS $function$
DECLARE
    -- ⚠️ %TYPE su tutto cio' che riflette una colonna
    --    (linee-guida-sql §5). `v_modo` no: e' un letterale
    --    di dispatch.
    v_modo         text;
    v_sr_id        vendite.event_log.emittente_soggetto_ruolo_id%TYPE;
    v_auth_user_id vendite.event_log.auth_user_id%TYPE;
    v_ammessi      text;
BEGIN
    -- =========================================================
    -- Scopo:
    --   Compilare da se' le cose che il database sa e il
    --   chiamante no: DI CHI e' la riga e CHI l'ha scritta.
    --
    -- ⭐ LA REGOLA (D-12):
    --   il diario rifiuta una riga SOLO quando non riesce a dire
    --   di chi e'. Un emittente disattivato o un documento
    --   annullato si registrano lo stesso: il fatto e' accaduto,
    --   e rifiutare la riga distruggerebbe l'unica prova che lo
    --   spiegherebbe. L'attivita' NUOVA su un emittente
    --   disattivato e' gia' bloccata sui documenti.
    --
    -- ⚠️ Non si fida di cio' che passa il chiamante su nessuno
    --   dei due campi: sono fatti del database, e la logica non
    --   si duplica in Python.
    --
    -- ⭐ Rev 2026-09-18 (Passo D): QUANDO SCADE non si calcola
    --   piu' qui. Lo scrive `dbops.trgfn_cleanup_at_alla_nascita`
    --   (trigger _m50_, dopo questo), che legge termine e
    --   colonna base dalla regola CLEANUP_AT: lo stesso BB dei
    --   quattro registri di fatturazione e push. La copia
    --   `vendite.fn_event_log_ttl_days` e' ritirata.
    -- =========================================================

    -- 1. Da che parte si guarda.
    -- ⭐ Rev 2026-08-22 (L4). Qui c'era un CASE scritto a mano con i tre
    --   tipi. Il modo vive adesso nella STESSA RIGA del tipo, in
    --   config.tipi_entita: aggiungere un tipo giornalabile e' un seed,
    --   non tre modifiche coordinate (CHECK + questo CASE + il modo in
    --   fn_resolve_emittente_sr_id). Configurazione e trigger non
    --   possono piu' dissentire, perche' sono lo stesso dato.
    -- ⚠️ NULL qui significa DUE cose, e vanno entrambe rifiutate allo
    --   stesso modo: il tipo non esiste a catalogo, oppure esiste ma NON
    --   e' giornalabile (modo NULL, come TASK_RUN — puntabile da un
    --   errore, senza un padrone da cui derivare il perimetro).
    SELECT te.modo_risoluzione_emittente
      INTO v_modo
      FROM config.tipi_entita te
     WHERE te.codice = NEW.entity_type
       AND (te.obsoleto_dal IS NULL OR te.obsoleto_dal > (SELECT script.fn_data_operativa()));

    -- ⛔ Rev 2026-08-22 (20260822-47). Questo ramo mancava, e la
    --   versione precedente si affidava al CHECK sulla colonna.
    --   Ma i BEFORE ROW girano PRIMA dei CHECK: con un tipo fuori
    --   vocabolario il CASE cadeva a NULL e il risolutore
    --   rispondeva «il modo di risoluzione «» non esiste» —
    --   E_PARAMETRO_INVALIDO, e un messaggio che nomina un
    --   concetto interno al database invece del dato passato.
    --   Il CHECK resta come invariante della colonna; qui si
    --   presidia il PERCORSO.
    IF v_modo IS NULL THEN
        -- ⭐ L'elenco dei tipi ammessi si legge dal CATALOGO, non si
        --   scrive nel messaggio: cosi' la frase resta vera il giorno che
        --   il catalogo cresce. E' il motivo per cui il messaggio 980 e'
        --   passato da uno a due segnaposto nella stessa passata
        --   (arita': due `%s`, due valori nel VARIADIC).
        SELECT string_agg(te.codice, ', ' ORDER BY te.codice)
          INTO v_ammessi
          FROM config.tipi_entita te
         WHERE te.modo_risoluzione_emittente IS NOT NULL
           AND (te.obsoleto_dal IS NULL OR te.obsoleto_dal > (SELECT script.fn_data_operativa()));

        PERFORM script.fn_log_and_raise_error(
            'vendite',
            'trgfn_event_log_deriva_scope',
            'E_EVENT_LOG_ENTITY_TYPE_IGNOTO',
            jsonb_build_object(
                'detail',      'entity_type fuori dal vocabolario del giornale',
                'entity_type', NEW.entity_type,
                'entity_id',   NEW.entity_id,
                'event_code',  NEW.event_code
            ),
            NULL::uuid,
            NEW.entity_type,
            v_ammessi
        );
    END IF;

    -- 2. Di chi e'. La risoluzione gira FUORI dalla row security
    --    (SECURITY DEFINER): «non la vedo» non e' «non esiste».
    v_sr_id := script.fn_resolve_emittente_sr_id(v_modo, NEW.entity_id);

    IF v_sr_id IS NULL THEN
        -- ⛔ L'entita' non esiste: non c'e' modo di dire di chi
        --    sia la riga. Codice DIVERSO dal precedente perche'
        --    il rimedio e' diverso — li' «usa uno dei tre tipi»,
        --    qui «quell'entita' non c'e'».
        PERFORM script.fn_log_and_raise_error(
            'vendite',
            'trgfn_event_log_deriva_scope',
            'E_EVENT_LOG_SCOPE_NON_RISOLTO',
            jsonb_build_object(
                'detail',      'Entita non trovata: perimetro non derivabile',
                'entity_type', NEW.entity_type,
                'entity_id',   NEW.entity_id,
                'event_code',  NEW.event_code
            ),
            NULL::uuid,
            NEW.entity_type,
            NEW.entity_id::text
        );
    END IF;

    NEW.emittente_soggetto_ruolo_id := v_sr_id;

    -- 3. Chi, come numero. `user_insert` (il nome) lo scrive il
    --    trigger di audit leggendo app.jwt_user; qui si tiene
    --    l'id, che regge a un rename. NULL sul canale batch, dove
    --    non c'e' un utente: li' «chi» resta user_insert.
    v_auth_user_id := NULLIF(
        current_setting('app.current_user_id', true), ''
    )::bigint;
    NEW.auth_user_id := v_auth_user_id;

    RETURN NEW;
END
$function$

COMMENT ON FUNCTION vendite.trgfn_event_log_deriva_scope()
IS 'BEFORE INSERT su vendite.event_log: deriva il perimetro dall''entita'' (script.fn_resolve_emittente_sr_id) e scrive auth_user_id dalla GUC. ⭐ LA REGOLA: il diario rifiuta una riga SOLO quando non riesce a dire di chi e''. Un emittente disattivato o un documento annullato si registrano lo stesso. Due rifiuti, due codici, perche'' il rimedio e'' diverso: E_EVENT_LOG_ENTITY_TYPE_IGNOTO (tipo fuori vocabolario) ed E_EVENT_LOG_SCOPE_NON_RISOLTO (entita'' inesistente). ⚠️ Rev 2026-08-22 (20260822-47): il primo ramo mancava e ci si affidava al CHECK sulla colonna — ma i BEFORE ROW girano PRIMA dei CHECK, e l''errore usciva come E_PARAMETRO_INVALIDO «il modo di risoluzione «» non esiste», che nomina un concetto interno al database invece del dato passato. ⭐ Rev 2026-09-18 (Passo D, analisi-osservabilita-log.md): cleanup_at non si calcola piu'' qui — lo scrive dbops.trgfn_cleanup_at_alla_nascita (trigger _m50_, dopo questo), lo stesso BB dei quattro registri di fatturazione e push; vendite.fn_event_log_ttl_days e'' ritirata.';
```

</div>

---
{% include-markdown "signature-core.md" %}
