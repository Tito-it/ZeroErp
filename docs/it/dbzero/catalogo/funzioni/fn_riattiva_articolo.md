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
-- Errore: E_ARTICOLO_NOT_FOUND se id NULL o non esiste.
-- Tipi: %TYPE delle colonne target (linee-guida-sql).
DECLARE
    v_fn_name CONSTANT text := 'fn_riattiva_articolo';
    v_rows    integer;
BEGIN
    -- Guard parametro NULL: riconducibile a NOT FOUND.
    IF p_articolo_id IS NULL THEN
        PERFORM script.fn_log_and_raise_error(
            'catalogo',
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
    -- Un riferimento spento (iva, gruppo, tipologia, ecc.)
    -- lo rifiuta dbops.trgfn_child_requires_active_parent
    -- (E_ATTIVO_PADRE_NON_ATTIVO, al COMMIT: trigger differito).
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
                'catalogo',
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
IS 'Riattiva un articolo (attivo = true) senza toccare le righe che dipendono da lui: prima il padre, poi i figli, uno per uno. Idempotente su un articolo gia'' attivo. Id NULL o inesistente: E_ARTICOLO_NOT_FOUND. Un riferimento spento dell''articolo (IVA, gruppo, tipologia, unita'' di misura e gli altri padri della famiglia ATTIVO) lo rifiuta dbops.trgfn_child_requires_active_parent con E_ATTIVO_PADRE_NON_ATTIVO, al COMMIT (trigger differito). La disattivazione e'' un UPDATE diretto, giudicato da dbops.trgfn_prevent_deactivate_if_children.';
```

</div>

---
{% include-markdown "signature-core.md" %}
