{% include-markdown "it/dbzero/vendite/manual/vw_preventivi_smistamento.md" %}
# 🔍 View `vw_preventivi_smistamento`

> 📝 **Descrizione**
>
> Aggregata smistamento preventivo: contatori per ramo (merce/servizi, a ordine/in commessa/emesse/fatturate) + righe_residue complessivo per il progress "X/Y smistate -&gt; EVASO" (gate D6). Sostituisce vw_preventivi_stato_fatturazione. ⭐ rev 2026-10-19 (20261019-92, brief-db-grammatica-unica-documenti lotto 2b, G-3 di Tid): ricreata dopo l'allargamento della colonna; il codice di origine o di destinazione e' quello di config.sorgenti (OFFERTA -&gt; OFFERTA_COMMERCIALE, ORDINE -&gt; ORDINE_VENDITA).

> 🔒 **Opzioni di sicurezza**: `security_invoker=on` — reloption non visibile in `pg_get_viewdef`, riportata qui esplicitamente. Va **ri-specificata** in ogni `CREATE OR REPLACE VIEW`, altrimenti PostgreSQL la azzera.

> 🔓 **Sicurezza**: `security_invoker` — le tabelle sotto si leggono con i privilegi e la RLS di chi interroga; owner `zeroerp_owner`.

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE VIEW vendite.vw_preventivi_smistamento
WITH (security_invoker=on) AS
SELECT preventivo_id,
    preventivo_uid,
    preventivo_numero,
    count(*) AS righe_totali,
    count(*) FILTER (WHERE ((destinazione_tipo)::text = 'ORDINE_VENDITA'::text)) AS righe_merce,
    count(*) FILTER (WHERE ((destinazione_tipo)::text = 'COMMESSA'::text)) AS righe_servizi,
    count(*) FILTER (WHERE (stato_smistamento = 'A_ORDINE'::text)) AS righe_a_ordine,
    count(*) FILTER (WHERE (stato_smistamento = ANY (ARRAY['IN_COMMESSA'::text, 'EMESSA_AF'::text, 'FATTURATA'::text]))) AS righe_in_commessa,
    count(*) FILTER (WHERE (stato_smistamento = ANY (ARRAY['EMESSA_AF'::text, 'FATTURATA'::text]))) AS righe_emesse_af,
    count(*) FILTER (WHERE (stato_smistamento = 'FATTURATA'::text)) AS righe_fatturate,
    count(*) FILTER (WHERE (stato_smistamento = 'RESIDUA'::text)) AS righe_residue
   FROM vendite.vw_preventivi_smistamento_righe
  GROUP BY preventivo_id, preventivo_uid, preventivo_numero;
```

</div>


---
{% include-markdown "signature-core.md" %}
