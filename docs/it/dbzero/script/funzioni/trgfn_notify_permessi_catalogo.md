{% include-markdown "it/dbzero/script/manual/trgfn_notify_permessi_catalogo.md" %}
# ⚙️ Funzione `trgfn_notify_permessi_catalogo`

```sql
CREATE FUNCTION trgfn_notify_permessi_catalogo()
```

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION script.trgfn_notify_permessi_catalogo()
 RETURNS trigger
 LANGUAGE plpgsql
AS $function$
-- Scopo: trigger AFTER ... FOR EACH STATEMENT sulle tabelle del catalogo
--   permessi: avvisa il backend che deve svuotare la cache permessi
--   (brief-db-permessi-catalogo-notify-cache). Il nome della tabella lo da'
--   PostgreSQL, non un argomento.
BEGIN
    PERFORM script.fn_notify_permessi_catalogo(
        TG_TABLE_SCHEMA || '.' || TG_TABLE_NAME
    );
    RETURN NULL;   -- AFTER per istruzione: ritorno ignorato
END;
$function$

COMMENT ON FUNCTION script.trgfn_notify_permessi_catalogo()
IS 'Trigger function generica dei trigger z90 AFTER INSERT OR UPDATE OR DELETE OR TRUNCATE FOR EACH STATEMENT sulle tabelle del catalogo permessi (config.azioni_processo, aree_funzionali, area_model_overrides, profili_accesso, profili_accesso_aree, profili_accesso_azioni, profili_accesso_bindings): chiama script.fn_notify_permessi_catalogo(TG_TABLE_SCHEMA.TG_TABLE_NAME), cioe'' NOTIFY permessi_catalogo al commit, e il backend svuota la cache permessi di tutti. Scatta anche su un''istruzione a zero righe: un avviso in piu'', innocuo. Nessun argomento di trigger. INVOKER. Brief: brief-db-permessi-catalogo-notify-cache R2.';
```

</div>

---
{% include-markdown "signature-core.md" %}
