{% include-markdown "it/dbzero/dbops/manual/vw_email_da_guardare.md" %}
# 🔍 View `vw_email_da_guardare`

> 📝 **Descrizione**
>
> PRESIDIO: le email che la coda deve a qualcuno da oltre un'ora e che nessuno ha preso in mano. DEVE restare VUOTA. ⭐ Si presidia l'EFFETTO e non lo schedulatore: se send_pending_emails non gira (o gira e non svuota) le email si accumulano qui, e questo prende anche il timer mai installato — che e' esattamente cio' che era successo su backend-dev senza che nessuno se ne accorgesse. ⭐ La definizione di «in coda» NON e' scritta qui: sta in config.vw_email_in_coda, una volta sola, per il cron e per questo presidio; qui c'e' SOLO la soglia. ⚠️ Un'ora non deriva dalla cadenza del cron (5 minuti): una soglia dedotta dai tempi di oggi si taglierebbe addosso al carico di oggi. Il backoff dei RETRY e' rispettato per costruzione, perche' dovuta_dal misura da quando la riga era DOVUTA e non da quando e' nata. ⛔ Perimetro DEFINER a catalogo: email_log ha la RLS e la vista e' security_invoker — una persona la legge col suo perimetro, il digest la CONTA da proprietario con fn_conta_presidio e riporta il numero, mai le righe. Sta in dbops e non in config perche' il catalogo dei presidi legge il perimetro dagli schemi che vi compaiono. Brief: brief-db-quattro-processi-senza-presidio §5.

> 🔒 **Opzioni di sicurezza**: `security_invoker=true` — reloption non visibile in `pg_get_viewdef`, riportata qui esplicitamente. Va **ri-specificata** in ogni `CREATE OR REPLACE VIEW`, altrimenti PostgreSQL la azzera.

> 🔓 **Sicurezza**: `security_invoker` — le tabelle sotto si leggono con i privilegi e la RLS di chi interroga; owner `zeroerp_owner`.

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE VIEW dbops.vw_email_da_guardare
WITH (security_invoker=true) AS
SELECT id,
    destinatario,
    oggetto,
    stato,
    tentativi,
    max_tentativi,
    ambito,
    emittente_fiscale_id,
        CASE
            WHEN ((stato)::text = 'PENDING'::text) THEN 'mai presa in mano: send_pending_emails non sta girando'::text
            ELSE 'ritentativo dovuto e mai eseguito'::text
        END AS motivo,
    (now() - dovuta_dal) AS da_quanto,
    dovuta_dal,
    data_insert
   FROM config.vw_email_in_coda c
  WHERE (dovuta_dal < (now() - '01:00:00'::interval));
```

</div>


---
{% include-markdown "signature-core.md" %}
