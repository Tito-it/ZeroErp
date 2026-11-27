{% include-markdown "it/dbzero/dbops/manual/fn_pgtap_lega_profilo_identita.md" %}
# ⚙️ Funzione `fn_pgtap_lega_profilo_identita`

```sql
CREATE FUNCTION fn_pgtap_lega_profilo_identita(p_profilo_accesso_id integer, p_identita_digitale_id bigint)
```

> 🔓 **Sicurezza**: `SECURITY INVOKER` (default) — gira con i privilegi di chi la chiama; owner `zeroerp_owner`.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION dbops.fn_pgtap_lega_profilo_identita(p_profilo_accesso_id integer, p_identita_digitale_id bigint)
 RETURNS bigint
 LANGUAGE plpgsql
AS $function$
-- Scopo: in un pgTAP, lega un profilo a un'identita' dal verbo config.fn_lega_profilo_identita, da un SUPER_ADMIN di
--   fixture. Restituisce il risultato del verbo; un rifiuto arriva al test
--   com'e'. Il contesto di prima si rimette, anche in errore.
DECLARE
    v_prima jsonb;  -- il contesto di prima, dalla fixture: nessuna colonna
    v_esito config.profili_accesso_bindings.id%TYPE;
BEGIN
    v_prima := dbops.fn_pgtap_entra_come_super_admin('lega-profilo-identita');

    BEGIN
        v_esito := config.fn_lega_profilo_identita(p_profilo_accesso_id, p_identita_digitale_id);
    EXCEPTION
        WHEN OTHERS THEN
            PERFORM dbops.fn_pgtap_rimetti_contesto(v_prima);
            RAISE;
    END;

    PERFORM dbops.fn_pgtap_rimetti_contesto(v_prima);

    RETURN v_esito;
END;
$function$

COMMENT ON FUNCTION dbops.fn_pgtap_lega_profilo_identita(p_profilo_accesso_id integer, p_identita_digitale_id bigint)
IS 'Builder dei pgTAP: lega un''identità digitale a un profilo di accesso dal verbo config.fn_lega_profilo_identita, da un SUPER_ADMIN di fixture (dbops.fn_pgtap_entra_come_super_admin), e rimette il contesto di prima, anche in errore (dbops.fn_pgtap_rimetti_contesto). Argomenti e risultato sono quelli del verbo; un rifiuto del verbo arriva al test com''è.';
```

</div>

---
{% include-markdown "signature-core.md" %}
