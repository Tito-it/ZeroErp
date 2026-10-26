{% include-markdown "it/dbzero/script/manual/fn_ambiente_installazione.md" %}
# ⚙️ Funzione `fn_ambiente_installazione`

```sql
CREATE FUNCTION fn_ambiente_installazione()
```

> 🔓 **Sicurezza**: `SECURITY INVOKER` (default) — gira con i privilegi di chi la chiama; owner `zeroerp_owner`.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION script.fn_ambiente_installazione()
 RETURNS text
 LANGUAGE plpgsql
 STABLE
AS $function$
DECLARE
    v_ambiente dbops.installazione.ambiente%TYPE;
BEGIN
    -- =========================================================
    -- Scopo:
    --   L'ambiente di questa installazione, per chi DECIDE in
    --   base a lui. Sede unica: chi deve sapere se gira in
    --   sviluppo o in produzione lo chiede qui.
    --
    -- Regole (R-1):
    --   - niente override, niente ripiego;
    --   - assente o fuori vocabolario -> E_CONFIG_MANCANTE:
    --     l'installazione va dichiarata (fase post del
    --     provisioning, -v ambiente=SVILUPPO|PRODUZIONE).
    -- =========================================================
    v_ambiente := script.fn_ambiente_dichiarato();

    IF v_ambiente IS NULL
       OR v_ambiente NOT IN ('SVILUPPO', 'PRODUZIONE') THEN
        PERFORM script.fn_log_and_raise_error(
            'script', 'fn_ambiente_installazione', 'E_CONFIG_MANCANTE',
            jsonb_build_object('configurazione', 'dbops.installazione.ambiente',
                               'valore',         v_ambiente),
            NULL::uuid,
            'l''ambiente dell''installazione (SVILUPPO o PRODUZIONE)');
    END IF;

    RETURN v_ambiente;
END;
$function$

COMMENT ON FUNCTION script.fn_ambiente_installazione()
IS 'L''ambiente di questa installazione, SVILUPPO o PRODUZIONE, per chi DECIDE in base a lui (la sveglia dei processi, il provisioning di sviluppo). Sede unica: chi deve saperlo lo chiede qui. Come script.fn_fuso_operativo(): niente cascata di override, niente ripiego. Valore assente o fuori vocabolario: E_CONFIG_MANCANTE — l''installazione va dichiarata dalla fase post di scripts/sql/provision_zeroerp.sql (-v ambiente=...). Chi DESCRIVE senza decidere usa script.fn_ambiente_dichiarato(), che torna NULL. Brief: brief-db-processi-accensione-per-ambiente (A-1, R-1).';
```

</div>

---
{% include-markdown "signature-core.md" %}
