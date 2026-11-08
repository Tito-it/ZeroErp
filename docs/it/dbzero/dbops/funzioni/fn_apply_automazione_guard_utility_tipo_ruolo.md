{% include-markdown "it/dbzero/dbops/manual/fn_apply_automazione_guard_utility_tipo_ruolo.md" %}
# ⚙️ Funzione `fn_apply_automazione_guard_utility_tipo_ruolo`

```sql
CREATE FUNCTION fn_apply_automazione_guard_utility_tipo_ruolo(p_exec_mode text, p_dry_run boolean)
```

> 🔓 **Sicurezza**: `SECURITY INVOKER` (default) — gira con i privilegi di chi la chiama; owner `zeroerp_owner`.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION dbops.fn_apply_automazione_guard_utility_tipo_ruolo(p_exec_mode text DEFAULT 'AUTO'::text, p_dry_run boolean DEFAULT false)
 RETURNS void
 LANGUAGE plpgsql
AS $function$
BEGIN
  -- Scopo: la porta storica del guard utility/tipo ruolo, che il primo giro di ci_apply
  --   chiama ancora. Il lavoro lo fa il runner che converge,
  --   dbops.fn_run_automations_guard_utility, su tutto l'ambito: qui non c'e' una seconda
  --   copia della regola.
  PERFORM dbops.fn_run_automations_guard_utility(p_exec_mode, NULL, p_dry_run);
END;
$function$

COMMENT ON FUNCTION dbops.fn_apply_automazione_guard_utility_tipo_ruolo(p_exec_mode text, p_dry_run boolean)
IS 'La porta storica del guard utility/tipo ruolo: chiama dbops.fn_run_automations_guard_utility(p_exec_mode, NULL, p_dry_run), il runner che porta i trigger allo stato di dbops.automazione_guard_utility_tipo_ruolo. Resta perche'' la chiama il primo giro di ci_apply; il processo automations_guard_utility chiama il runner.';
```

</div>

---
{% include-markdown "signature-core.md" %}
