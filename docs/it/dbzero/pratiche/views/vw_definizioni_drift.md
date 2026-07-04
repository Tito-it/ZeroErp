{% include-markdown "it/dbzero/pratiche/manual/vw_definizioni_drift.md" %}
# 🔍 View `vw_definizioni_drift`

```sql
CREATE OR REPLACE VIEW pratiche.vw_definizioni_drift AS
SELECT f.id AS definizione_id,
    f.tipo_prestazione_id,
    f.emittente_fiscale_id,
    f.versione AS versione_edizione,
    f.stato AS stato_edizione,
    f.versione_origine,
    pc.id AS preset_corrente_id,
    pc.versione AS versione_preset_corrente,
    (pc.versione - f.versione_origine) AS versioni_indietro
   FROM (pratiche.workflow_definizioni f
     JOIN pratiche.workflow_definizioni pc ON (((pc.tipo_prestazione_id = f.tipo_prestazione_id) AND (pc.emittente_fiscale_id IS NULL) AND ((pc.stato)::text = 'PUBBLICATA'::text))))
  WHERE ((f.preset_origine_id IS NOT NULL) AND (f.versione_origine IS NOT NULL) AND (f.emittente_fiscale_id IS NOT NULL) AND ((f.stato)::text = ANY ((ARRAY['BOZZA'::character varying, 'PUBBLICATA'::character varying])::text[])) AND (pc.versione > f.versione_origine));
```


---
{% include-markdown "signature-core.md" %}
