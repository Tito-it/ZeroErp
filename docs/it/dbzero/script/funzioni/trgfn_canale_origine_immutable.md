{% include-markdown "it/dbzero/script/manual/trgfn_canale_origine_immutable.md" %}
# ⚙️ Funzione `trgfn_canale_origine_immutable`

```sql
CREATE FUNCTION trgfn_canale_origine_immutable()
```

> 🔓 **Sicurezza**: `SECURITY INVOKER` (default) — gira con i privilegi di chi la chiama; owner `zeroerp_owner`.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION script.trgfn_canale_origine_immutable()
 RETURNS trigger
 LANGUAGE plpgsql
AS $function$
BEGIN
    -- =========================================================
    -- Scopo:
    --   Impedire modifiche alla colonna canale_origine di una
    --   tabella transazionale. La colonna traccia l'origine
    --   del record (ADMIN/PORTALE/SHOP) e deve essere
    --   immutabile: alterazioni retroattive invaliderebbero
    --   la storia e le decisioni RLS basate sul canale.
    --
    -- Regole:
    --   1. Scatta solo se NEW.canale_origine != OLD.canale_origine.
    --      IS DISTINCT FROM per sicurezza (NULL non previsti ma
    --      gestiti).
    --   2. Raise E_CANALE_ORIGINE_IMMUTABILE con context di
    --      schema/tabella per debug.
    -- =========================================================

    IF NEW.canale_origine IS DISTINCT FROM OLD.canale_origine THEN
        PERFORM script.fn_log_and_raise_error(
            TG_TABLE_SCHEMA,
            TG_NAME,
            'E_CANALE_ORIGINE_IMMUTABILE',
            jsonb_build_object(
                'op', TG_OP,
                'schema', TG_TABLE_SCHEMA,
                'tabella', TG_TABLE_NAME,
                'old_canale', OLD.canale_origine,
                'new_canale', NEW.canale_origine
            ),
            NULL::uuid,
            -- ⚠️ ARITA' (2026-08-18): qui c'era una frase gia' composta con
            --   format(), passata come valore UNICO. Il messaggio a catalogo
            --   («Canale origine su %s.%s: ...») di segnaposto ne ha DUE, quindi
            --   format(messaggio, VARIADIC ARRAY[una_frase]) alzava 22023 al
            --   posto del P0001 di dominio.
            --   I due canali (vecchio e nuovo) non spariscono: erano gia' nel
            --   context qui sopra, sotto 'old_canale' e 'new_canale', ed e' li'
            --   che devono stare — il messaggio dice all'operatore COSA non puo'
            --   fare, il context dice al log cos'e' successo.
            TG_TABLE_SCHEMA, TG_TABLE_NAME
        );
    END IF;

    RETURN NEW;
END;
$function$

COMMENT ON FUNCTION script.trgfn_canale_origine_immutable()
IS 'Trigger function generica: blocca UPDATE che modifica la colonna canale_origine. Applicata via UPDATE OF canale_origine su billing_account, vendite.ordini, vendite.fatture. Codice errore E_CANALE_ORIGINE_IMMUTABILE.';
```

</div>

---
{% include-markdown "signature-core.md" %}
