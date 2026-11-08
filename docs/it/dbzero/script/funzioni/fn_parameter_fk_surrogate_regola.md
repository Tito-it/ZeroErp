{% include-markdown "it/dbzero/script/manual/fn_parameter_fk_surrogate_regola.md" %}
# ⚙️ Funzione `fn_parameter_fk_surrogate_regola`

```sql
CREATE FUNCTION fn_parameter_fk_surrogate_regola(p_code text)
```

> 🔓 **Sicurezza**: `SECURITY INVOKER` (default) — gira con i privilegi di chi la chiama; owner `zeroerp_owner`.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION script.fn_parameter_fk_surrogate_regola(p_code text)
 RETURNS bigint
 LANGUAGE sql
 STABLE
AS $function$
    -- Scopo: l'id della regola del registro che governa un codice di
    --   parametro, al massimo una: EXACT prima di LIKE, poi il pattern piu'
    --   lungo. NULL = nessuna regola. E' la sola sede della scelta: la leggono
    --   la check e il presidio.
    SELECT pfs.id
      FROM config.parameter_fk_surrogate pfs
     WHERE pfs.enabled
       AND (
              (pfs.match_mode = 'EXACT' AND pfs.code_pattern = p_code)
           OR (pfs.match_mode = 'LIKE'  AND p_code LIKE pfs.code_pattern)
       )
     ORDER BY (pfs.match_mode = 'EXACT') DESC, length(pfs.code_pattern) DESC
     LIMIT 1;
$function$

COMMENT ON FUNCTION script.fn_parameter_fk_surrogate_regola(p_code text)
IS 'L''id della regola di config.parameter_fk_surrogate che governa un codice di parametro, al massimo una: fra le regole abilitate che lo prendono, EXACT prima di LIKE, poi il pattern piu'' lungo. NULL = nessuna regola, il parametro non e'' soggetto alla check. E'' la sola sede della scelta: la leggono script.fn_check_parameter_fk_surrogate (i dispatcher dei parametri) e il presidio dbops.vw_parameter_fk_surrogate_dangling, che quindi nominano la stessa regola. Due LIKE della stessa lunghezza che prendono lo stesso codice sono un''ambiguita'' del registro: la scelta fra loro non e'' definita.';
```

</div>

---
{% include-markdown "signature-core.md" %}
