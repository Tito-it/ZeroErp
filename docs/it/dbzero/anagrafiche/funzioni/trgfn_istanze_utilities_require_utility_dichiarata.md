# ⚙️ Funzione `trgfn_istanze_utilities_require_utility_dichiarata`

```sql
CREATE FUNCTION trgfn_istanze_utilities_require_utility_dichiarata()
```

**Definizione completa:**

```sql
CREATE OR REPLACE FUNCTION anagrafiche.trgfn_istanze_utilities_require_utility_dichiarata()
 RETURNS trigger
 LANGUAGE plpgsql
AS $function$
BEGIN
  -- Almeno 1 satellite tra BA, IDP, clienti deve esistere
  -- per l'istanza appena inserita (NEW.id).
  IF NOT EXISTS (
    SELECT 1 FROM anagrafiche.billing_account
     WHERE istanza_utility_id = NEW.id
    UNION ALL
    SELECT 1 FROM anagrafiche.istanze_dati_precontrattuali
     WHERE istanza_utility_id = NEW.id
    UNION ALL
    SELECT 1 FROM anagrafiche.clienti
     WHERE istanza_utility_id = NEW.id
  ) THEN
    -- Ultimo arg = valore per il %s del messaggio CSV
    -- (E_ISTANZA_UTILITY_SENZA_UTILITY: %s = breve contesto).
    PERFORM script.fn_log_and_raise_error(
      'anagrafiche',
      'trgfn_istanze_utilities_require_utility_dichiarata',
      'E_ISTANZA_UTILITY_SENZA_UTILITY',
      jsonb_build_object(
        'detail', 'Istanza senza satellite (BA/IDP/cliente) al COMMIT',
        'istanza_utility_id', NEW.id,
        'soggetto_id', NEW.soggetto_id
      ),
      NULL::uuid,
      concat('istanza_utility_id=', NEW.id::text)
    );
  END IF;

  RETURN NULL;
END
$function$

COMMENT ON FUNCTION anagrafiche.trgfn_istanze_utilities_require_utility_dichiarata()
IS 'Constraint trigger function (DEFERRABLE) che valida al COMMIT la presenza di almeno 1 satellite (billing_account, istanze_dati_precontrattuali, clienti) per la nuova istanza. Lista satelliti allineata a script.fn_check_utility_istanza_coerenza.';
```

---
{% include-markdown "signature-core.md" %}
