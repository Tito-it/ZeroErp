{% include-markdown "it/dbzero/pratiche/manual/vw_definizioni_drift.md" %}
# 🔍 View `vw_definizioni_drift`

> 📝 **Descrizione**
>
> Edizioni forkate (emittente-scoped, vive) il cui preset d'origine ha una PUBBLICATA con versione &gt; versione_origine: sono "in drift" rispetto al preset. Alimenta il banner "preset aggiornato" (DEF-2). versioni_indietro = di quante versioni il fork e' rimasto indietro.

> 🔒 **Opzioni di sicurezza**: `security_invoker=true` — reloption non visibile in `pg_get_viewdef`, riportata qui esplicitamente. Va **ri-specificata** in ogni `CREATE OR REPLACE VIEW`, altrimenti PostgreSQL la azzera.

> 🔓 **Sicurezza**: `security_invoker` — le tabelle sotto si leggono con i privilegi e la RLS di chi interroga; owner `zeroerp_owner`.

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE VIEW pratiche.vw_definizioni_drift
WITH (security_invoker=true) AS
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

</div>


---
{% include-markdown "signature-core.md" %}
