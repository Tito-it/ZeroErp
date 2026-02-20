{% include-markdown "it/dbzero/maintenance/manual/proc_bump_indirizzi_dettaglio.md" %}
# ⚙️ Procedura `proc_bump_indirizzi_dettaglio`

```sql
CREATE PROCEDURE proc_bump_indirizzi_dettaglio(IN p_stradario_id integer)
```

**Definizione completa:**

```sql
CREATE OR REPLACE PROCEDURE maintenance.proc_bump_indirizzi_dettaglio(IN p_stradario_id integer)
 LANGUAGE plpgsql
AS $procedure$
BEGIN
  -- Abilita manutenzione solo per la sessione corrente
  PERFORM set_config('zeroerp.maintenance_indirizzi_dettaglio', 'on', true);

  UPDATE anagrafiche.indirizzi_dettaglio
  SET stradario_id = stradario_id
  WHERE stradario_id = p_stradario_id;
END;
$procedure$

COMMENT ON PROCEDURE maintenance.proc_bump_indirizzi_dettaglio(IN p_stradario_id integer)
IS 'Procedura di riallineamento indirizzi_dettaglio per cambio stradario_id.';
```

---
{% include-markdown "signature-core.md" %}
