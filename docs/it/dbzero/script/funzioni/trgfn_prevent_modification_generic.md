{% include-markdown "it/dbzero/script/manual/trgfn_prevent_modification_generic.md" %}
# ⚙️ Funzione `trgfn_prevent_modification_generic`

```sql
CREATE FUNCTION trgfn_prevent_modification_generic()
```

**Definizione completa:**

```sql
CREATE OR REPLACE FUNCTION script.trgfn_prevent_modification_generic()
 RETURNS trigger
 LANGUAGE plpgsql
AS $function$

BEGIN

  PERFORM script.fn_log_and_raise_error(
      'database',
      'trgfn_prevent_parameters_audit_modification',
      'E_TABELLA_OP_NON_CONSENTITA',
      jsonb_build_object(
        'nome_tabella', TG_TABLE_NAME,
        'trigger_op',        TG_OP
      ),
      NULL::uuid,
      TG_TABLE_NAME::text,
      TG_OP::text
    );

  -- rev 2026-08-04 (bonifica riferimenti morti, F6): manca(va) il RETURN.
  --   Oggi la riga sopra solleva sempre, quindi il flusso non ci arriva —
  --   ma «non ci arriva mai» e' una proprieta' di
  --   script.fn_log_and_raise_error, non di questa funzione. Il giorno in
  --   cui quella diventasse non-fatale in qualche ramo, una trigger
  --   function che cade oltre il proprio END solleva 2F005 al posto
  --   dell'errore di dominio. Il RETURN NULL e' anche la risposta giusta
  --   nel merito: BEFORE ROW, l'operazione va annullata.
  RETURN NULL;
END;
$function$

COMMENT ON FUNCTION script.trgfn_prevent_modification_generic()
IS 'Segnala errore su attività non consentite sulle tabelle';
```

---
{% include-markdown "signature-core.md" %}
