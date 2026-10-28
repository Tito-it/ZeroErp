{% include-markdown "it/dbzero/anagrafiche/manual/trgfn_risorse_umane_guard_ruolo.md" %}
# ⚙️ Funzione `trgfn_risorse_umane_guard_ruolo`

```sql
CREATE FUNCTION trgfn_risorse_umane_guard_ruolo()
```

> 🔓 **Sicurezza**: `SECURITY INVOKER` (default) — gira con i privilegi di chi la chiama; owner `zeroerp_owner`.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION anagrafiche.trgfn_risorse_umane_guard_ruolo()
 RETURNS trigger
 LANGUAGE plpgsql
AS $function$
DECLARE
    v_soggetto_id uuid;
BEGIN
    -- FUNCTION: 
    --   Ogni volta che inserisco/aggiorno in fornitori, gestisco la
    --   verifica della riga corrispondente in soggetti_ruoli.
    --   alimentando poi in NEW.soggetto_ruolo_id il record finale.

    -- Sostituisco NEW.soggetto_ruolo_id con l'ID vero (esistente),
    -- delegando completamente alla funzione generica:
    NEW.soggetto_ruolo_id := script.fn_guard_soggetto_ruolo(
                            p_soggetto_id       := NULL,
                            p_soggetto_ruolo_id := NEW.soggetto_ruolo_id,
                            p_cd_int_ruolo      := 'RIS_UMANA'
                            );

    SELECT sr.soggetto_id
      INTO v_soggetto_id
      FROM anagrafiche.soggetti_ruoli sr
     WHERE sr.id = NEW.soggetto_ruolo_id;

    IF v_soggetto_id IS DISTINCT FROM NEW.soggetto_id THEN
        PERFORM script.fn_log_and_raise_error(
            'database',
            TG_NAME,
            'E_RISORSA_UMANA_SOGGETTO_MISMATCH',
            jsonb_build_object(
                'campo', 'soggetto_ruolo_id',
                'table', TG_TABLE_NAME,
                'soggetto_id', NEW.soggetto_id,
                'soggetto_id_ruolo', v_soggetto_id
            ),
            NULL::uuid,
            NEW.soggetto_ruolo_id::text
        );
    END IF;

    RETURN NEW;
END;
$function$

COMMENT ON FUNCTION anagrafiche.trgfn_risorse_umane_guard_ruolo()
IS 'Verifica che soggetto_ruolo_id sia di tipo RIS_UMANA.';
```

</div>

---
{% include-markdown "signature-core.md" %}
