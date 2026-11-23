{% include-markdown "it/dbzero/config/manual/trgfn_toponomastica_protect_update.md" %}
# ⚙️ Funzione `trgfn_toponomastica_protect_update`

```sql
CREATE FUNCTION trgfn_toponomastica_protect_update()
```

> 🔓 **Sicurezza**: `SECURITY INVOKER` (default) — gira con i privilegi di chi la chiama; owner `zeroerp_owner`.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION config.trgfn_toponomastica_protect_update()
 RETURNS trigger
 LANGUAGE plpgsql
AS $function$
BEGIN
  -- Scopo: la descrizione di un toponimo in uso nello stradario
  --   generale non si cambia a mano.
  --
  -- La porta di manutenzione: GUC accesa E chi scrive e' il
  --   proprietario della tabella (maintenance.proc_bump_toponomastica,
  --   lanciata da zeroerp_owner, che porta la correzione fino agli
  --   indirizzi). ⛔ La sola GUC non basta: l'applicazione la puo'
  --   accendere da se'. Funzione INVOKER: non va resa SECURITY DEFINER.
  IF current_setting('zeroerp.maintenance_toponomastica', true) = 'on'
     AND script.fn_is_proprietario_tabella(TG_RELID) THEN
    RETURN NEW;
  END IF;

  -- Se il record non e' usato in config.stradario_generale, lascio passare
  IF NOT EXISTS (
    SELECT 1
      FROM config.stradario_generale
     WHERE toponomastica_id = OLD.id
  ) THEN
    RETURN NEW;
  END IF;

  -- Se siamo qui, il record e' in uso: controllo ciascuna colonna
  IF OLD.descrizione IS DISTINCT FROM NEW.descrizione THEN
    PERFORM script.fn_log_and_raise_error(
      'database',
      TG_NAME,
      'E_COLONNA_NON_MODIFICABILE',
      jsonb_build_object('column','descrizione','id',OLD.id),
      NULL::uuid,
      'descrizione'
    );
  END IF;
  RETURN NEW;
END;
$function$

COMMENT ON FUNCTION config.trgfn_toponomastica_protect_update()
IS 'Guard BEFORE UPDATE OF descrizione di config.toponomastica: la descrizione di un toponimo in uso nello stradario generale non si cambia a mano (E_COLONNA_NON_MODIFICABILE). Porta di manutenzione: la GUC zeroerp.maintenance_toponomastica accesa e chi scrive proprietario della tabella (maintenance.proc_bump_toponomastica, da zeroerp_owner). La sola GUC non apre.';
```

</div>

---
{% include-markdown "signature-core.md" %}
