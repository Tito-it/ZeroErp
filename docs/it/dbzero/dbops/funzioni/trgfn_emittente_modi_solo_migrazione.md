{% include-markdown "it/dbzero/dbops/manual/trgfn_emittente_modi_solo_migrazione.md" %}
# ⚙️ Funzione `trgfn_emittente_modi_solo_migrazione`

```sql
CREATE FUNCTION trgfn_emittente_modi_solo_migrazione()
```

> 🔓 **Sicurezza**: `SECURITY INVOKER` (default) — gira con i privilegi di chi la chiama; owner `zeroerp_owner`.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION dbops.trgfn_emittente_modi_solo_migrazione()
 RETURNS trigger
 LANGUAGE plpgsql
AS $function$
DECLARE
  -- il modo della riga toccata; NULL per il TRUNCATE (trigger di istruzione)
  v_modo dbops.emittente_modi.modo%TYPE;
BEGIN
  -- Scopo: dbops.emittente_modi si scrive solo dal proprietario
  --   della tabella (il migrate, dal seed). INVOKER per
  --   costruzione: script.fn_is_proprietario_tabella guarda chi
  --   esegue l'istruzione.
  IF script.fn_is_proprietario_tabella(TG_RELID) THEN
    IF TG_LEVEL = 'ROW' AND TG_OP <> 'DELETE' THEN
      RETURN NEW;
    END IF;
    RETURN OLD;
  END IF;

  IF TG_LEVEL = 'ROW' THEN
    IF TG_OP = 'DELETE' THEN
      v_modo := OLD.modo;
    ELSE
      v_modo := NEW.modo;
    END IF;
  END IF;

  PERFORM script.fn_log_and_raise_error(
      'dbops',
      'trgfn_emittente_modi_solo_migrazione',
      'E_EMITTENTE_MODI_NON_SCRIVIBILE',
      jsonb_build_object(
          'operazione',   TG_OP,
          'modo',         v_modo,
          'current_user', current_user,
          'detail',       'I modi si dichiarano nel seed emittente_modi.csv e arrivano col migrate'
      ),
      NULL::uuid,
      TG_OP::text
  );
  RETURN NULL;  -- irraggiungibile: la riga sopra solleva
END
$function$

COMMENT ON FUNCTION dbops.trgfn_emittente_modi_solo_migrazione()
IS 'Guard di dbops.emittente_modi (BEFORE INSERT, UPDATE, DELETE di riga e BEFORE TRUNCATE): il registro dei modi lo scrive solo il proprietario della tabella, cioe'' il migrate dal seed emittente_modi.csv (script.fn_is_proprietario_tabella); chiunque altro riceve E_EMITTENTE_MODI_NON_SCRIVIBILE. Dal registro si generano i risolutori dell''emittente, SECURITY DEFINER e letti dalle policy: una riga e'' codice di sicurezza, non configurazione. E'' un trigger e non un permesso perche'' il giro dei grant di ci_apply ri-concede i privilegi sulle tabelle a ogni passata.';
```

</div>

---
{% include-markdown "signature-core.md" %}
