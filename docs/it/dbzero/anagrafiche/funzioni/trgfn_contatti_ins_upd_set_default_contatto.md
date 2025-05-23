# Funzione `trgfn_contatti_ins_upd_set_default_contatto`

```sql
CREATE FUNCTION trgfn_contatti_ins_upd_set_default_contatto()
```

**Definizione completa:**

```sql
CREATE OR REPLACE FUNCTION anagrafiche.trgfn_contatti_ins_upd_set_default_contatto()
 RETURNS trigger
 LANGUAGE plpgsql
AS $function$
DECLARE
    cnt INTEGER;
BEGIN
    -- Se il nuovo contatto è già marked default, lasciare com'è
    IF NEW.is_default THEN
        -- Rimuove eventuali altri default preesistenti
        UPDATE anagrafiche.contatti
           SET is_default = FALSE
         WHERE soggetto_id = NEW.soggetto_id
           AND id <> COALESCE(NEW.id, 0)
           AND is_default;
        RETURN NEW;
    END IF;

    -- Controlla se il soggetto ha già un default
    SELECT COUNT(*) INTO cnt
      FROM anagrafiche.contatti
     WHERE soggetto_id = NEW.soggetto_id
       AND is_default;

    -- Se non esiste alcun default, imposta il nuovo contatto come default
    IF cnt = 0 THEN
        NEW.is_default := TRUE;
    END IF;

    RETURN NEW;
END;
$function$
```