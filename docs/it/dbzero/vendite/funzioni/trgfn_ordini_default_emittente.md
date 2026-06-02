{% include-markdown "it/dbzero/vendite/manual/trgfn_ordini_default_emittente.md" %}
# ⚙️ Funzione `trgfn_ordini_default_emittente`

```sql
CREATE FUNCTION trgfn_ordini_default_emittente()
```

**Definizione completa:**

```sql
CREATE OR REPLACE FUNCTION vendite.trgfn_ordini_default_emittente()
 RETURNS trigger
 LANGUAGE plpgsql
AS $function$
DECLARE
  v_user_id_text text;
  v_user_id      integer;
BEGIN
  -- 1) Skip se gia' valorizzato esplicitamente nel payload.
  IF NEW.emittente_fiscale_id IS NOT NULL THEN
    RETURN NEW;
  END IF;

  -- 2) Lettura GUC app.current_user_id (missing_ok=true).
  v_user_id_text := current_setting('app.current_user_id', true);

  IF v_user_id_text IS NULL OR btrim(v_user_id_text) = '' THEN
    PERFORM script.fn_log_and_raise_error(
      'vendite',
      'trgfn_ordini_default_emittente',
      'E_ORDINE_EMITTENTE_NON_RISOLTO',
      jsonb_build_object(
        'detail', 'GUC app.current_user_id vuota e payload senza emittente_fiscale_id',
        'numero_ordine', NEW.numero
      ),
      NULL::uuid,
      concat('GUC vuota, numero=', NEW.numero)
    );
  END IF;

  v_user_id := v_user_id_text::integer;

  -- 3) Resolver operatore -> emittente (NULL per admin globale).
  NEW.emittente_fiscale_id := script.fn_resolve_emittente_for_user(v_user_id);

  IF NEW.emittente_fiscale_id IS NULL THEN
    PERFORM script.fn_log_and_raise_error(
      'vendite',
      'trgfn_ordini_default_emittente',
      'E_ORDINE_EMITTENTE_NON_RISOLTO',
      jsonb_build_object(
        'detail', 'Operatore senza EF assegnato (admin globale): payload deve specificare emittente_fiscale_id',
        'auth_user_id', v_user_id,
        'numero_ordine', NEW.numero
      ),
      NULL::uuid,
      concat('auth_user_id=', v_user_id::text, ', numero=', NEW.numero)
    );
  END IF;

  RETURN NEW;
END
$function$

COMMENT ON FUNCTION vendite.trgfn_ordini_default_emittente()
IS 'BEFORE INSERT trigger fn: setta ordini.emittente_fiscale_id da GUC app.current_user_id via script.fn_resolve_emittente_for_user. Skip se valorizzato esplicitamente. Solleva E_ORDINE_EMITTENTE_NON_RISOLTO se GUC vuota o operatore admin globale senza payload esplicito. Pattern simmetrico a trgfn_contratti_default_emittente.';
```

---
{% include-markdown "signature-core.md" %}
