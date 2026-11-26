{% include-markdown "it/dbzero/dbops/manual/fn_pgtap_scrivi_profilo_accesso.md" %}
# ⚙️ Funzione `fn_pgtap_scrivi_profilo_accesso`

```sql
CREATE FUNCTION fn_pgtap_scrivi_profilo_accesso(p_tipo config.tipo_profilo_accesso, p_codice character varying, p_descrizione text, p_aree jsonb, p_azioni jsonb, p_campi jsonb)
```

> 🔓 **Sicurezza**: `SECURITY INVOKER` (default) — gira con i privilegi di chi la chiama; owner `zeroerp_owner`.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION dbops.fn_pgtap_scrivi_profilo_accesso(p_tipo config.tipo_profilo_accesso, p_codice character varying, p_descrizione text, p_aree jsonb DEFAULT NULL::jsonb, p_azioni jsonb DEFAULT NULL::jsonb, p_campi jsonb DEFAULT '{}'::jsonb)
 RETURNS integer
 LANGUAGE plpgsql
AS $function$
-- Scopo: in un pgTAP, scrive un profilo di accesso dal verbo config.fn_scrivi_profilo_accesso, da un SUPER_ADMIN di
--   fixture. Restituisce il risultato del verbo; un rifiuto arriva al test
--   com'e'. Il contesto di prima si rimette, anche in errore.
DECLARE
    v_prima jsonb;  -- il contesto di prima, dalla fixture: nessuna colonna
    v_esito config.profili_accesso.id%TYPE;
BEGIN
    v_prima := dbops.fn_pgtap_entra_come_super_admin('scrivi-profilo-accesso');

    BEGIN
        v_esito := config.fn_scrivi_profilo_accesso(p_tipo, p_codice, p_descrizione, p_aree, p_azioni, p_campi);
    EXCEPTION
        WHEN OTHERS THEN
            PERFORM dbops.fn_pgtap_rimetti_contesto(v_prima);
            RAISE;
    END;

    PERFORM dbops.fn_pgtap_rimetti_contesto(v_prima);

    RETURN v_esito;
END;
$function$

COMMENT ON FUNCTION dbops.fn_pgtap_scrivi_profilo_accesso(p_tipo config.tipo_profilo_accesso, p_codice character varying, p_descrizione text, p_aree jsonb, p_azioni jsonb, p_campi jsonb)
IS 'Builder dei pgTAP: scrive un profilo di accesso dal verbo config.fn_scrivi_profilo_accesso, da un SUPER_ADMIN di fixture (dbops.fn_pgtap_entra_come_super_admin), e rimette il contesto di prima, anche in errore (dbops.fn_pgtap_rimetti_contesto). Argomenti e risultato sono quelli del verbo; un rifiuto del verbo arriva al test com''è.';
```

</div>

---
{% include-markdown "signature-core.md" %}
