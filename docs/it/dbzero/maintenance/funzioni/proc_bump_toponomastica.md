{% include-markdown "it/dbzero/maintenance/manual/proc_bump_toponomastica.md" %}
# ⚙️ Procedura `proc_bump_toponomastica`

```sql
CREATE PROCEDURE proc_bump_toponomastica(IN p_toponomastica_id integer, IN p_descrizione text)
```

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE PROCEDURE maintenance.proc_bump_toponomastica(IN p_toponomastica_id integer, IN p_descrizione text)
 LANGUAGE plpgsql
AS $procedure$
BEGIN
  -- Abilita manutenzione solo per la sessione corrente
  PERFORM set_config('zeroerp.maintenance_toponomastica', 'on', true);

  UPDATE config.toponomastica
  SET descrizione = p_descrizione
  WHERE id = p_toponomastica_id;
END;
$procedure$

COMMENT ON PROCEDURE maintenance.proc_bump_toponomastica(IN p_toponomastica_id integer, IN p_descrizione text)
IS 'Procedura di riallineamento toponomastica per cambio descrizione.';
```

</div>

---
{% include-markdown "signature-core.md" %}
