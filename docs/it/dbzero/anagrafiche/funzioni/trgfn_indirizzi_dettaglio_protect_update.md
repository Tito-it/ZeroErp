{% include-markdown "it/dbzero/anagrafiche/manual/trgfn_indirizzi_dettaglio_protect_update.md" %}
# ⚙️ Funzione `trgfn_indirizzi_dettaglio_protect_update`

```sql
CREATE FUNCTION trgfn_indirizzi_dettaglio_protect_update()
```

> 🔓 **Sicurezza**: `SECURITY INVOKER` (default) — gira con i privilegi di chi la chiama; owner `zeroerp_owner`.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION anagrafiche.trgfn_indirizzi_dettaglio_protect_update()
 RETURNS trigger
 LANGUAGE plpgsql
AS $function$
BEGIN
  -- Scopo: lo stradario_id di un indirizzo non si cambia a mano.
  --
  -- La porta di manutenzione: GUC accesa E chi scrive e' il
  --   proprietario della tabella (la fusione delle vie,
  --   dbops.fn_admin_merge_stradario, lanciata da zeroerp_owner).
  -- ⛔ La sola GUC non basta: l'applicazione la puo' accendere da
  --   se'. Il BB vede chi scrive perche' questa funzione e'
  --   INVOKER: non va resa SECURITY DEFINER.
  IF current_setting('zeroerp.maintenance_indirizzi_dettaglio', true) = 'on'
     AND script.fn_is_proprietario_tabella(TG_RELID) THEN
    RETURN NEW;
  END IF;

  -- Fuori dalla porta: il cambio di stradario_id si rifiuta.
  IF NEW.stradario_id IS DISTINCT FROM OLD.stradario_id THEN
    PERFORM script.fn_log_and_raise_error(
      'database',
      TG_NAME,
      'E_COLONNA_NON_MODIFICABILE',
      jsonb_build_object('column','stradario_id','id',OLD.id),
      NULL::uuid,
      'stradario_id'
    );
  END IF;

  RETURN NEW;
END;
$function$

COMMENT ON FUNCTION anagrafiche.trgfn_indirizzi_dettaglio_protect_update()
IS 'Guard BEFORE UPDATE di anagrafiche.indirizzi_dettaglio: lo stradario_id non si cambia a mano (E_COLONNA_NON_MODIFICABILE). Porta di manutenzione: la GUC zeroerp.maintenance_indirizzi_dettaglio accesa e chi scrive proprietario della tabella (la fusione delle vie, dbops.fn_admin_merge_stradario, da zeroerp_owner). La sola GUC non apre.';
```

</div>

---
{% include-markdown "signature-core.md" %}
