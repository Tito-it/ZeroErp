{% include-markdown "it/dbzero/catalogo/manual/fn_riattiva_articolo.md" %}
# ⚙️ Funzione `fn_riattiva_articolo`

```sql
CREATE FUNCTION fn_riattiva_articolo(p_articolo_id uuid)
```

> 🔓 **Sicurezza**: `SECURITY INVOKER` (default) — gira con i privilegi di chi la chiama; owner `zeroerp_owner`.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION catalogo.fn_riattiva_articolo(p_articolo_id uuid)
 RETURNS void
 LANGUAGE plpgsql
AS $function$
-- Scopo: riattiva un articolo disattivato (UPDATE attivo=true).
--   Pattern "padre prima, figli poi": NON tocca i figli (righe
--   articoli_uom_operativa, BoM dove l'articolo e' componente,
--   ecc.) -- l'admin li riattiva esplicitamente in azioni
--   successive.
-- Idempotente su articolo gia' attivo (no audit spurio).
-- Errore: E_ARTICOLO_NOT_FOUND (404) se id NULL o non esiste.
-- Tipi: %TYPE delle colonne target (linee-guida-sql).
DECLARE
    v_fn_name CONSTANT text := 'fn_riattiva_articolo';
    v_rows    integer;
BEGIN
    -- Guard parametro NULL: riconducibile a NOT FOUND.
    IF p_articolo_id IS NULL THEN
        PERFORM script.fn_log_and_raise_error(
            'database',
            v_fn_name,
            'E_ARTICOLO_NOT_FOUND',
            jsonb_build_object('articolo_id', NULL),
            NULL::uuid,
            'NULL'
        );
    END IF;

    -- UPDATE filtrato su attivo=false: idempotente per
    -- articoli gia' attivi (0 rows aggiornate, no audit
    -- triggers spuri come data_update/user_update/tx_id).
    -- Eventuale fail per parent inattivi (iva, gruppo,
    -- tipologia, ecc.) si propaga dal trigger esistente
    -- trgfn_child_requires_active_parent (E_PARENT_*).
    UPDATE catalogo.articoli
       SET attivo = true
     WHERE id = p_articolo_id
       AND attivo = false;

    GET DIAGNOSTICS v_rows = ROW_COUNT;

    -- 0 rows aggiornate -> due possibilita':
    --   (a) articolo gia' attivo (no-op idempotente, return)
    --   (b) articolo non esiste (raise E_ARTICOLO_NOT_FOUND)
    IF v_rows = 0 THEN
        IF NOT EXISTS (
            SELECT 1 FROM catalogo.articoli
             WHERE id = p_articolo_id
        ) THEN
            PERFORM script.fn_log_and_raise_error(
                'database',
                v_fn_name,
                'E_ARTICOLO_NOT_FOUND',
                jsonb_build_object('articolo_id', p_articolo_id),
                NULL::uuid,
                p_articolo_id::text
            );
        END IF;
        -- (a) no-op, articolo gia' attivo
    END IF;
END;
$function$

COMMENT ON FUNCTION catalogo.fn_riattiva_articolo(p_articolo_id uuid)
IS 'Riattiva un articolo (attivo=true) senza toccare i figli (pattern "padre prima, figli poi"). Idempotente su gia'' attivo, raise E_ARTICOLO_NOT_FOUND (404) se id NULL o inesistente. Disattivazione resta UPDATE diretto, coperto da trgfn_prevent_deactivate_if_children.';
```

</div>

---
{% include-markdown "signature-core.md" %}
