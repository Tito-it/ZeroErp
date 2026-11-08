{% include-markdown "it/dbzero/dbops/manual/vw_parameter_fk_surrogate_dangling.md" %}
# 🔍 View `vw_parameter_fk_surrogate_dangling`

> 📝 **Descrizione**
>
> Presidio: parametri (default e override) il cui valore non esiste nel target della regola FK-surrogata che li governa. Una riga per valore, con la regola che lo governa (matched_pattern, matched_mode, target): la sceglie script.fn_parameter_fk_surrogate_regola, la stessa che usa la check, quindi un codice preso da piu' pattern esce una volta sola e col target giusto. Righe = valori da correggere a mano. Sorgenti: config.parameters e config.parameter_overrides.

> 🔐 **Sicurezza**: definer (default delle viste) — le tabelle sotto si leggono con i privilegi dell'owner `zeroerp_owner`, e la RLS che vale e' la sua, non quella di chi interroga.

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE VIEW dbops.vw_parameter_fk_surrogate_dangling AS
SELECT 'parameter'::text AS source,
    p.id AS source_id,
    p.code,
    p.default_value AS value,
    (((((pfs.target_schema)::text || '.'::text) || (pfs.target_table)::text) || '.'::text) || (pfs.target_column)::text) AS target,
    pfs.code_pattern AS matched_pattern,
    pfs.match_mode AS matched_mode
   FROM (config.parameters p
     JOIN config.parameter_fk_surrogate pfs ON ((pfs.id = script.fn_parameter_fk_surrogate_regola((p.code)::text))))
  WHERE ((p.default_value IS NOT NULL) AND (NOT script.fn_check_parameter_fk_surrogate((p.code)::text, p.default_value)))
UNION ALL
 SELECT 'parameter_override'::text AS source,
    po.id AS source_id,
    p.code,
    po.overridden_value AS value,
    (((((pfs.target_schema)::text || '.'::text) || (pfs.target_table)::text) || '.'::text) || (pfs.target_column)::text) AS target,
    pfs.code_pattern AS matched_pattern,
    pfs.match_mode AS matched_mode
   FROM ((config.parameter_overrides po
     JOIN config.parameters p ON ((p.id = po.parameter_id)))
     JOIN config.parameter_fk_surrogate pfs ON ((pfs.id = script.fn_parameter_fk_surrogate_regola((p.code)::text))))
  WHERE ((po.overridden_value IS NOT NULL) AND (NOT script.fn_check_parameter_fk_surrogate((p.code)::text, po.overridden_value)));
```

</div>


---
{% include-markdown "signature-core.md" %}
