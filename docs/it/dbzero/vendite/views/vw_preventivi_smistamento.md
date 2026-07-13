{% include-markdown "it/dbzero/vendite/manual/vw_preventivi_smistamento.md" %}
# 🔍 View `vw_preventivi_smistamento`

> 🔒 **Opzioni di sicurezza**: `security_invoker=on` — reloption non visibile in `pg_get_viewdef`, riportata qui esplicitamente. Va **ri-specificata** in ogni `CREATE OR REPLACE VIEW`, altrimenti PostgreSQL la azzera.

```sql
CREATE OR REPLACE VIEW vendite.vw_preventivi_smistamento
WITH (security_invoker=on) AS
SELECT preventivo_id,
    preventivo_uid,
    preventivo_numero,
    count(*) AS righe_totali,
    count(*) FILTER (WHERE ((destinazione_tipo)::text = 'ORDINE'::text)) AS righe_merce,
    count(*) FILTER (WHERE ((destinazione_tipo)::text = 'COMMESSA'::text)) AS righe_servizi,
    count(*) FILTER (WHERE (stato_smistamento = 'A_ORDINE'::text)) AS righe_a_ordine,
    count(*) FILTER (WHERE (stato_smistamento = ANY (ARRAY['IN_COMMESSA'::text, 'EMESSA_AF'::text, 'FATTURATA'::text]))) AS righe_in_commessa,
    count(*) FILTER (WHERE (stato_smistamento = ANY (ARRAY['EMESSA_AF'::text, 'FATTURATA'::text]))) AS righe_emesse_af,
    count(*) FILTER (WHERE (stato_smistamento = 'FATTURATA'::text)) AS righe_fatturate,
    count(*) FILTER (WHERE (stato_smistamento = 'RESIDUA'::text)) AS righe_residue
   FROM vendite.vw_preventivi_smistamento_righe
  GROUP BY preventivo_id, preventivo_uid, preventivo_numero;
```


---
{% include-markdown "signature-core.md" %}
