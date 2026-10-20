{% include-markdown "it/dbzero/anagrafiche/manual/trgfn_contatti_set_default_contatto.md" %}
# ⚙️ Funzione `trgfn_contatti_set_default_contatto`

```sql
CREATE FUNCTION trgfn_contatti_set_default_contatto()
```

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION anagrafiche.trgfn_contatti_set_default_contatto()
 RETURNS trigger
 LANGUAGE plpgsql
AS $function$
DECLARE
  cnt INTEGER;
  ctx TEXT;
BEGIN
  -- 1) Reset del context
  NEW.default_context := NULL;

  -- 2) Determino il contesto per questo contatto
  ctx := CASE
    WHEN NEW.istanza_utility_id IS NOT NULL THEN 'istanza'
    WHEN NEW.soggetto_ruolo_id  IS NOT NULL THEN 'ruolo'
    ELSE 'soggetto'
  END;

  -- 3) Se il nuovo contatto e marcato default:
  IF NEW.is_default THEN
    UPDATE anagrafiche.contatti
      SET is_default = FALSE,
          default_context = NULL
    WHERE soggetto_id = NEW.soggetto_id
      AND id <> COALESCE(NEW.id, 0)
      AND is_default
      AND default_context = ctx;

    NEW.default_context := ctx;

    IF ctx = 'soggetto' THEN
      UPDATE anagrafiche.soggetti
        SET default_contatto_id = NEW.id
      WHERE id = NEW.soggetto_id;
    END IF;
    RETURN NEW;
  END IF;

  -- 4) Se non esiste ancora alcun default in questo contesto
  SELECT COUNT(*) INTO cnt
    FROM anagrafiche.contatti
  WHERE soggetto_id = NEW.soggetto_id
    AND is_default
    AND default_context = ctx;

  IF cnt = 0 THEN
      NEW.is_default      := TRUE;
      NEW.default_context := ctx;

      IF ctx = 'soggetto' THEN
        UPDATE anagrafiche.soggetti
          SET default_contatto_id = NEW.id
        WHERE id = NEW.soggetto_id;
      END IF;
  END IF;

  RETURN NEW;
END;
$function$

COMMENT ON FUNCTION anagrafiche.trgfn_contatti_set_default_contatto()
IS 'Trigger: imposta il primo contatto come default nel contesto corretto (soggetto|ruolo|istanza). Aggiorna default_contatto_id su soggetti. Ripulisce solo quelli dello stesso contesto.';
```

</div>

---
{% include-markdown "signature-core.md" %}
