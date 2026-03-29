# ⚙️ Funzione `trgfn_pratiche_guard_contesto`

```sql
CREATE FUNCTION trgfn_pratiche_guard_contesto()
```

**Definizione completa:**

```sql
CREATE OR REPLACE FUNCTION pratiche.trgfn_pratiche_guard_contesto()
 RETURNS trigger
 LANGUAGE plpgsql
AS $function$
-- Scopo: validare la coerenza gerarchica del contesto anagrafico
--        sulla pratica: soggetto → ruolo → istanza.
-- Regole:
--   1. istanza_utility_id NOT NULL → soggetto_ruolo_id obbligatorio
--   2. soggetto_ruolo_id NOT NULL → soggetto_id obbligatorio
--   3. soggetto_ruolo_id deve appartenere a soggetto_id
--   4. istanza_utility_id deve appartenere al soggetto_id
DECLARE
    v_soggetto_id_ruolo  anagrafiche.soggetti_ruoli.soggetto_id%TYPE;
    v_soggetto_id_istanza anagrafiche.istanze_utilities.soggetto_id%TYPE;
BEGIN
    -- Regola 1: istanza richiede ruolo
    IF NEW.istanza_utility_id IS NOT NULL AND NEW.soggetto_ruolo_id IS NULL THEN
        PERFORM script.fn_log_and_raise_error(
            'pratiche',
            'pratiche.trgfn_pratiche_guard_contesto',
            'PRATICHE_ISTANZA_SENZA_RUOLO',
            jsonb_build_object(
                'istanza_utility_id', NEW.istanza_utility_id
            ),
            NULL::uuid,
            'istanza_utility_id richiede soggetto_ruolo_id'
        );
    END IF;

    -- Regola 2: ruolo richiede soggetto
    IF NEW.soggetto_ruolo_id IS NOT NULL AND NEW.soggetto_id IS NULL THEN
        PERFORM script.fn_log_and_raise_error(
            'pratiche',
            'pratiche.trgfn_pratiche_guard_contesto',
            'PRATICHE_RUOLO_SENZA_SOGGETTO',
            jsonb_build_object(
                'soggetto_ruolo_id', NEW.soggetto_ruolo_id
            ),
            NULL::uuid,
            NEW.soggetto_ruolo_id::text
        );
    END IF;

    -- Regola 3: ruolo deve appartenere al soggetto
    IF NEW.soggetto_ruolo_id IS NOT NULL THEN
        SELECT sr.soggetto_id INTO v_soggetto_id_ruolo
          FROM anagrafiche.soggetti_ruoli sr
         WHERE sr.id = NEW.soggetto_ruolo_id;

        IF v_soggetto_id_ruolo IS NULL
           OR v_soggetto_id_ruolo IS DISTINCT FROM NEW.soggetto_id THEN
            PERFORM script.fn_log_and_raise_error(
                'pratiche',
                'pratiche.trgfn_pratiche_guard_contesto',
                'PRATICHE_RUOLO_NON_COERENTE',
                jsonb_build_object(
                    'soggetto_ruolo_id', NEW.soggetto_ruolo_id,
                    'soggetto_id', NEW.soggetto_id,
                    'soggetto_id_ruolo', v_soggetto_id_ruolo
                ),
                NULL::uuid,
                NEW.soggetto_ruolo_id::text,
                NEW.soggetto_id::text
            );
        END IF;
    END IF;

    -- Regola 4: istanza deve appartenere al soggetto
    IF NEW.istanza_utility_id IS NOT NULL THEN
        SELECT iu.soggetto_id INTO v_soggetto_id_istanza
          FROM anagrafiche.istanze_utilities iu
         WHERE iu.id = NEW.istanza_utility_id;

        IF v_soggetto_id_istanza IS NULL
           OR v_soggetto_id_istanza IS DISTINCT FROM NEW.soggetto_id THEN
            PERFORM script.fn_log_and_raise_error(
                'pratiche',
                'pratiche.trgfn_pratiche_guard_contesto',
                'PRATICHE_ISTANZA_NON_COERENTE',
                jsonb_build_object(
                    'istanza_utility_id', NEW.istanza_utility_id,
                    'soggetto_id', NEW.soggetto_id,
                    'soggetto_id_istanza', v_soggetto_id_istanza
                ),
                NULL::uuid,
                NEW.istanza_utility_id::text,
                NEW.soggetto_id::text
            );
        END IF;
    END IF;

    RETURN NEW;
END;
$function$

COMMENT ON FUNCTION pratiche.trgfn_pratiche_guard_contesto()
IS 'Guard: coerenza gerarchica contesto anagrafico (soggetto → ruolo → istanza) su pratiche.';
```

---
{% include-markdown "signature-core.md" %}
