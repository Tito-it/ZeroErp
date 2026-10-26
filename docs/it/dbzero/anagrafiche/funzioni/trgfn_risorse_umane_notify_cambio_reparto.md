{% include-markdown "it/dbzero/anagrafiche/manual/trgfn_risorse_umane_notify_cambio_reparto.md" %}
# ⚙️ Funzione `trgfn_risorse_umane_notify_cambio_reparto`

```sql
CREATE FUNCTION trgfn_risorse_umane_notify_cambio_reparto()
```

> 🔓 **Sicurezza**: `SECURITY INVOKER` (default) — gira con i privilegi di chi la chiama; owner `zeroerp_owner`.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION anagrafiche.trgfn_risorse_umane_notify_cambio_reparto()
 RETURNS trigger
 LANGUAGE plpgsql
AS $function$
BEGIN
-- ------------------------------------------------------------
-- Trigger function: trgfn_risorse_umane_notify_cambio_reparto
--
-- Scopo:
--   Al cambio di unita_organizzativa_id su risorse_umane,
--   emette NOTIFY cambio_reparto con payload JSON tramite
--   fn_notify_cambio_reparto. Il listener backend intercetta
--   la notifica e invalida la cache permessi dell'utente.
--
-- Evento: AFTER UPDATE OF unita_organizzativa_id
-- Tabella: anagrafiche.risorse_umane
-- ------------------------------------------------------------

    PERFORM anagrafiche.fn_notify_cambio_reparto(
        NEW.id,
        OLD.unita_organizzativa_id,
        NEW.unita_organizzativa_id
    );

    RETURN NULL; -- AFTER trigger, ritorno ignorato
END;
$function$

COMMENT ON FUNCTION anagrafiche.trgfn_risorse_umane_notify_cambio_reparto()
IS 'Trigger function: emette NOTIFY cambio_reparto al cambio unita organizzativa della risorsa.';
```

</div>

---
{% include-markdown "signature-core.md" %}
