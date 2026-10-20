{% include-markdown "it/dbzero/dbops/manual/vw_parameter_fk_surrogate_dangling.md" %}
# 🔍 View `vw_parameter_fk_surrogate_dangling`

> 📝 **Descrizione**
>
> Diagnostica: parametri (default + override) il cui valore non esiste nel target del registry FK-surrogata. Output non vuoto = righe da risolvere manualmente. Sorgente: config.parameters + config.parameter_overrides.

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
     JOIN config.parameter_fk_surrogate pfs ON ((pfs.enabled AND ((((pfs.match_mode)::text = 'EXACT'::text) AND ((pfs.code_pattern)::text = (p.code)::text)) OR (((pfs.match_mode)::text = 'LIKE'::text) AND ((p.code)::text ~~ (pfs.code_pattern)::text))))))
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
     JOIN config.parameter_fk_surrogate pfs ON ((pfs.enabled AND ((((pfs.match_mode)::text = 'EXACT'::text) AND ((pfs.code_pattern)::text = (p.code)::text)) OR (((pfs.match_mode)::text = 'LIKE'::text) AND ((p.code)::text ~~ (pfs.code_pattern)::text))))))
  WHERE ((po.overridden_value IS NOT NULL) AND (NOT script.fn_check_parameter_fk_surrogate((p.code)::text, po.overridden_value)));
```

</div>


---
{% include-markdown "signature-core.md" %}
