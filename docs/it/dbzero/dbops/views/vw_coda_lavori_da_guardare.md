{% include-markdown "it/dbzero/dbops/manual/vw_coda_lavori_da_guardare.md" %}
# 🔍 View `vw_coda_lavori_da_guardare`

> 📝 **Descrizione**
>
> I lavori di coda (dbops.coda_lavori, non archiviati) che chiedono un occhio, col motivo: falliti (ERRORE, tentativi esauriti), presi e mai chiusi (IN_CORSO con claimed_at oltre un'ora fa: il worker e' morto a meta'), mai presi (PENDING con run_after, o la nascita, oltre un'ora fa: il worker non sta girando). DEVE restare VUOTA. Il terzo motivo e' il meno visibile: un worker spento non produce errori, produce ASSENZA. La soglia di un'ora non viene da una misura ma dal fatto che il drenatore gira di continuo: una soglia dedotta dai tempi di oggi si taglierebbe addosso al carico di oggi. Fuori ANNULLATO (deciso da qualcuno) e archiviato (gia' guardato): un presidio che elenca cio' che qualcuno ha gia' visto smette di essere una lista di cose da fare. security_invoker; il digest conta da proprietario (dbops.fn_conta_presidio, perimetro DEFINER).

> 🔒 **Opzioni di sicurezza**: `security_invoker=true` — reloption non visibile in `pg_get_viewdef`, riportata qui esplicitamente. Va **ri-specificata** in ogni `CREATE OR REPLACE VIEW`, altrimenti PostgreSQL la azzera.

> 🔓 **Sicurezza**: `security_invoker` — le tabelle sotto si leggono con i privilegi e la RLS di chi interroga; owner `zeroerp_owner`.

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE VIEW dbops.vw_coda_lavori_da_guardare
WITH (security_invoker=true) AS
SELECT id,
    uid,
    job_type,
    stato,
    tentativi,
    max_tentativi,
        CASE
            WHEN (stato = 'ERRORE'::text) THEN 'fallito: tentativi esauriti'::text
            WHEN (stato = 'IN_CORSO'::text) THEN 'preso e mai chiuso: il worker e'' morto a meta'''::text
            ELSE 'mai preso: il worker non sta girando'::text
        END AS motivo,
    (now() - COALESCE(claimed_at, run_after, data_insert)) AS da_quanto,
    ultimo_errore,
    scope,
    data_insert
   FROM dbops.coda_lavori c
  WHERE ((NOT archiviato) AND ((stato = 'ERRORE'::text) OR ((stato = 'IN_CORSO'::text) AND (claimed_at < (now() - '01:00:00'::interval))) OR ((stato = 'PENDING'::text) AND (COALESCE(run_after, data_insert) < (now() - '01:00:00'::interval)))));
```

</div>


---
{% include-markdown "signature-core.md" %}
