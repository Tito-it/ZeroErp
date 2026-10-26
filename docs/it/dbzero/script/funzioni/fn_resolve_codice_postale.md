{% include-markdown "it/dbzero/script/manual/fn_resolve_codice_postale.md" %}
# ⚙️ Funzione `fn_resolve_codice_postale`

```sql
CREATE FUNCTION fn_resolve_codice_postale(p_stradario_id integer, p_comune_id integer)
```

> 🔓 **Sicurezza**: `SECURITY INVOKER` (default) — gira con i privilegi di chi la chiama; owner `zeroerp_owner`.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION script.fn_resolve_codice_postale(p_stradario_id integer DEFAULT NULL::integer, p_comune_id integer DEFAULT NULL::integer)
 RETURNS integer
 LANGUAGE plpgsql
 STABLE PARALLEL SAFE
AS $function$
DECLARE
    v_cap_id  config.codici_postali.id%TYPE;
    v_count   integer;
BEGIN
    -- =========================================================
    -- Scopo:
    --   Risolve il codice_postale_id con logica di fallback:
    --   1. Se stradario_id fornito e valido, prende il CAP
    --      direttamente dallo stradario
    --   2. Se non trovato (o non fornito), e il comune ha
    --      un solo CAP, lo usa come fallback
    --   3. Altrimenti NULL (l'utente sceglie manualmente)
    --
    -- Parametri:
    --   p_stradario_id: stradario di riferimento (opzionale)
    --   p_comune_id:    comune di riferimento (opzionale)
    --
    -- Usato da:
    --   - Frontend (auto-set CAP nel form indirizzo)
    --   - Import batch (risoluzione automatica CAP)
    --
    -- Regole:
    --   - Almeno uno dei due parametri dovrebbe essere fornito
    --   - Se entrambi NULL ritorna NULL
    --   - Se stradario non ha codice_postale_id, tenta fallback
    --   - Fallback comune: solo se il comune ha esattamente 1 CAP
    -- =========================================================

    -- Priorita' 1: CAP dallo stradario (via specifica)
    IF p_stradario_id IS NOT NULL AND p_stradario_id > 0 THEN
        SELECT s.codice_postale_id
          INTO v_cap_id
          FROM config.stradario s
         WHERE s.id = p_stradario_id;

        IF v_cap_id IS NOT NULL THEN
            RETURN v_cap_id;
        END IF;
    END IF;

    -- Priorita' 2: se il comune ha un solo CAP, usalo
    IF p_comune_id IS NOT NULL AND p_comune_id > 0 THEN
        SELECT cp.id, COUNT(*) OVER ()
          INTO v_cap_id, v_count
          FROM config.codici_postali cp
         WHERE cp.comune_id = p_comune_id
         LIMIT 1;

        IF v_count = 1 THEN
            RETURN v_cap_id;
        END IF;
    END IF;

    -- Nessun fallback: l'utente sceglie manualmente
    RETURN NULL;
END;
$function$

COMMENT ON FUNCTION script.fn_resolve_codice_postale(p_stradario_id integer, p_comune_id integer)
IS 'Risolve codice_postale_id: fallback stradario -> comune singolo CAP -> NULL. STABLE, PARALLEL SAFE.';
```

</div>

---
{% include-markdown "signature-core.md" %}
