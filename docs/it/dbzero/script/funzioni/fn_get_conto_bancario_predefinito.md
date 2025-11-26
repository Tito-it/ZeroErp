{% include-markdown "it/dbzero/script/manual/fn_get_conto_bancario_predefinito.md" %}
# ⚙️ Funzione `fn_get_conto_bancario_predefinito`

```sql
CREATE FUNCTION fn_get_conto_bancario_predefinito(p_soggetto_ruolo_id bigint, p_uso character varying)
```

**Definizione completa:**

```sql
CREATE OR REPLACE FUNCTION script.fn_get_conto_bancario_predefinito(p_soggetto_ruolo_id bigint, p_uso character varying)
 RETURNS anagrafiche.vw_conti_bancari_per_ruolo
 LANGUAGE plpgsql
 STABLE
AS $function$
DECLARE
    v_res anagrafiche.vw_conti_bancari_per_ruolo%ROWTYPE;
    v_uso varchar := UPPER(TRIM(COALESCE(p_uso, 'GENERICO')));
BEGIN
    -- 1) Tentativo diretto sull'uso richiesto (normalizzato)
    SELECT *
    INTO v_res
    FROM anagrafiche.vw_conti_bancari_per_ruolo v
    WHERE v.soggetto_ruolo_id = p_soggetto_ruolo_id
    AND v.uso               = v_uso
    LIMIT 1;

    IF v_res.soggetto_ruolo_id IS NOT NULL THEN
        RETURN v_res;
    END IF;

    -- 2) Fallback su GENERICO (solo se uso diverso)
    IF v_uso <> 'GENERICO' THEN
        SELECT *
        INTO v_res
        FROM anagrafiche.vw_conti_bancari_per_ruolo v
        WHERE v.soggetto_ruolo_id = p_soggetto_ruolo_id
        AND v.uso               = 'GENERICO'
        LIMIT 1;

        IF v_res.soggetto_ruolo_id IS NOT NULL THEN
            RETURN v_res;
        END IF;
    END IF;

    -- 3) Nessun conto trovato
    RETURN NULL;
END;
$function$
```

---
{% include-markdown "signature-core.md" %}
