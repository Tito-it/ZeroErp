# ⚙️ Funzione `trgfn_event_log_deriva_scope`

```sql
CREATE FUNCTION trgfn_event_log_deriva_scope()
```

**Definizione completa:**

```sql
CREATE OR REPLACE FUNCTION vendite.trgfn_event_log_deriva_scope()
 RETURNS trigger
 LANGUAGE plpgsql
AS $function$
DECLARE
    -- ⚠️ %TYPE su tutto cio' che riflette una colonna
    --    (linee-guida-sql §5). `v_modo` e `v_ttl_days` no: il
    --    primo e' un letterale di dispatch, il secondo esce da
    --    un jsonb (params->>'ttl_days') e non ha una colonna.
    v_modo         text;
    v_sr_id        vendite.event_log.emittente_soggetto_ruolo_id%TYPE;
    v_auth_user_id vendite.event_log.auth_user_id%TYPE;
    v_ttl_days     integer;
BEGIN
    -- =========================================================
    -- Scopo:
    --   Compilare da se' le cose che il database sa e il
    --   chiamante no: DI CHI e' la riga, CHI l'ha scritta, e
    --   quando scade.
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
    --   dei tre campi: sono fatti del database, e la logica non
    --   si duplica in Python.
    -- =========================================================

    -- 1. Da che parte si guarda.
    v_modo := CASE NEW.entity_type
                  WHEN 'LOTTO'    THEN 'lotto'
                  WHEN 'COMMESSA' THEN 'commessa'
                  WHEN 'FATTURA'  THEN 'fattura'
              END;

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
            NEW.entity_type
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

    -- 4. Quando scade. ⭐ Si valorizza QUI e non con
    --    dbops.fn_apply_cleanup_at, che userebbe un UPDATE —
    --    vietato su questa tabella. Effetto voluto: il veto
    --    sull'UPDATE rende la scadenza immutabile.
    v_ttl_days := vendite.fn_event_log_ttl_days();

    IF v_ttl_days IS NOT NULL THEN
        NEW.cleanup_at := COALESCE(NEW.event_time, now())
                          + make_interval(days => v_ttl_days);
    END IF;

    RETURN NEW;
END
$function$

COMMENT ON FUNCTION vendite.trgfn_event_log_deriva_scope()
IS 'BEFORE INSERT su vendite.event_log: deriva il perimetro dall''entita'' (script.fn_resolve_emittente_sr_id), scrive auth_user_id dalla GUC e cleanup_at dal TTL di dbops.automation_rules_tbl. ⭐ LA REGOLA: il diario rifiuta una riga SOLO quando non riesce a dire di chi e''. Un emittente disattivato o un documento annullato si registrano lo stesso. Due rifiuti, due codici, perche'' il rimedio e'' diverso: E_EVENT_LOG_ENTITY_TYPE_IGNOTO (tipo fuori vocabolario) ed E_EVENT_LOG_SCOPE_NON_RISOLTO (entita'' inesistente). ⚠️ Rev 2026-08-22 (20260822-47): il primo ramo mancava e ci si affidava al CHECK sulla colonna — ma i BEFORE ROW girano PRIMA dei CHECK, e l''errore usciva come E_PARAMETRO_INVALIDO «il modo di risoluzione «» non esiste», che nomina un concetto interno al database invece del dato passato.';
```

---
{% include-markdown "signature-core.md" %}
