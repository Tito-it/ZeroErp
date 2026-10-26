{% include-markdown "it/dbzero/vendite/manual/trgfn_contratti_set_categoria_cliente_snapshot.md" %}
# ⚙️ Funzione `trgfn_contratti_set_categoria_cliente_snapshot`

```sql
CREATE FUNCTION trgfn_contratti_set_categoria_cliente_snapshot()
```

> 🔓 **Sicurezza**: `SECURITY INVOKER` (default) — gira con i privilegi di chi la chiama; owner `zeroerp_owner`.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION vendite.trgfn_contratti_set_categoria_cliente_snapshot()
 RETURNS trigger
 LANGUAGE plpgsql
AS $function$
DECLARE
    v_categoria_id anagrafiche.billing_account.categoria_cliente_id%TYPE;
BEGIN
    -- INSERT: auto-populate da BA se il caller non lo passa.
    IF TG_OP = 'INSERT' AND NEW.categoria_cliente_id_snapshot IS NULL THEN
        SELECT ba.categoria_cliente_id
          INTO v_categoria_id
          FROM anagrafiche.billing_account ba
         WHERE ba.id = NEW.billing_account_id;

        NEW.categoria_cliente_id_snapshot := v_categoria_id;
    END IF;

    -- UPDATE: immutabilita' post-attivazione.
    -- In DRAFT la categoria puo' essere cambiata (es. riclassificazione
    -- BA durante la preparazione del contratto). Fuori da DRAFT e'
    -- congelata: modifica bloccata.
    IF TG_OP = 'UPDATE'
       AND OLD.categoria_cliente_id_snapshot IS DISTINCT FROM NEW.categoria_cliente_id_snapshot
    THEN
        IF (SELECT s.codice_interno
              FROM config.stati_doc_contratti s
             WHERE s.id = NEW.stato_doc_contratto_id) <> 'DRAFT'
        THEN
            -- E_CONTRATTO_CATEGORIA_SNAPSHOT_IMMUTABILE: 1 %s = contratto.
            PERFORM script.fn_log_and_raise_error(
                'vendite',
                TG_NAME,
                'E_CONTRATTO_CATEGORIA_SNAPSHOT_IMMUTABILE',
                jsonb_build_object(
                    'contratto_id', NEW.id,
                    'old_categoria', OLD.categoria_cliente_id_snapshot,
                    'new_categoria', NEW.categoria_cliente_id_snapshot
                ),
                NULL::uuid,
                NEW.id::text
            );
        END IF;
    END IF;

    RETURN NEW;
END
$function$

COMMENT ON FUNCTION vendite.trgfn_contratti_set_categoria_cliente_snapshot()
IS 'Auto-populate categoria_cliente_id_snapshot da BA su INSERT. In UPDATE: modifica ammessa solo in stato DRAFT; fuori da DRAFT il valore e'' congelato (immutabile).';
```

</div>

---
{% include-markdown "signature-core.md" %}
