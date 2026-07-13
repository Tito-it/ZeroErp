{% include-markdown "it/dbzero/vendite/manual/trgfn_ddt_default_emittente.md" %}
# ⚙️ Funzione `trgfn_ddt_default_emittente`

```sql
CREATE FUNCTION trgfn_ddt_default_emittente()
```

**Definizione completa:**

```sql
CREATE OR REPLACE FUNCTION vendite.trgfn_ddt_default_emittente()
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

  -- 2) Skip DDT da evasione: sorgente valorizzata -> l'emittente
  --    si eredita dall'ordine sorgente in trgfn_ddt_normalize.
  IF NEW.sorgente_tipo_id IS NOT NULL AND NEW.sorgente_uid IS NOT NULL THEN
    RETURN NEW;
  END IF;

  -- 3) GUC operatore (missing_ok). Se assente: NON sollevare,
  --    lasciare NULL -> fallback-da-BA in trgfn_ddt_normalize.
  v_user_id_text := current_setting('app.current_user_id', true);
  IF v_user_id_text IS NULL OR btrim(v_user_id_text) = '' THEN
    RETURN NEW;
  END IF;

  v_user_id := v_user_id_text::integer;

  -- 4) Resolver operatore -> emittente. NULL (admin globale)
  --    -> lasciare NULL (no raise): decide il fallback normalize.
  NEW.emittente_fiscale_id := script.fn_resolve_emittente_for_user(v_user_id);

  RETURN NEW;
END
$function$
```

---
{% include-markdown "signature-core.md" %}
