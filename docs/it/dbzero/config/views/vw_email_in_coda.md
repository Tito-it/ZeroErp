{% include-markdown "it/dbzero/config/manual/vw_email_in_coda.md" %}
# 🔍 View `vw_email_in_coda`

> 📝 **Descrizione**
>
> Le email che send_pending_emails DEVE ancora prendere in mano: PENDING, oppure RETRY/FAILED con tentativi &lt; max_tentativi e prossimo tentativo gia' dovuto (o mai fissato). ⭐ E' la definizione UNICA di «in coda», scritta nel database perche' la leggano in due — il presidio dbops.vw_email_da_guardare e il cron stesso — invece di tenerla in una SELECT Python e in una vista SQL che divergono alla prima modifica. ⛔ Il brief chiedeva PENDING e RETRY: mancavano i FAILED ripescabili, che il cron riprende APPOSTA (e' il recupero quando l'SMTP viene configurato dopo). Il backend l'ha scoperto il 2026-09-11 fidandosi di un commento che li ometteva. ⭐ dovuta_dal = da quando la coda la deve a qualcuno: data_insert per PENDING, COALESCE(prossimo_tentativo, data_insert) per gli altri — il backoff e' legittimo, e una riga col prossimo tentativo fra dieci minuti NON e' in ritardo. ⚠️ NON e' un presidio (nessuna soglia, e sta in config per non portare tutte le viste di config nel perimetro del catalogo dei presidi). security_invoker: ognuno la legge col proprio perimetro. SIMULATA, SENT e i FAILED terminali NON sono in coda. Brief: brief-db-quattro-processi-senza-presidio §10.1.

> 🔒 **Opzioni di sicurezza**: `security_invoker=true` — reloption non visibile in `pg_get_viewdef`, riportata qui esplicitamente. Va **ri-specificata** in ogni `CREATE OR REPLACE VIEW`, altrimenti PostgreSQL la azzera.

> 🔓 **Sicurezza**: `security_invoker` — le tabelle sotto si leggono con i privilegi e la RLS di chi interroga; owner `zeroerp_owner`.

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE VIEW config.vw_email_in_coda
WITH (security_invoker=true) AS
SELECT id,
    destinatario,
    oggetto,
    stato,
    tentativi,
    max_tentativi,
    email_account_id,
    ambito,
    emittente_fiscale_id,
    prossimo_tentativo,
    data_insert,
        CASE
            WHEN ((stato)::text = 'PENDING'::text) THEN data_insert
            ELSE COALESCE(prossimo_tentativo, data_insert)
        END AS dovuta_dal
   FROM config.email_log l
  WHERE (((stato)::text = 'PENDING'::text) OR (((stato)::text = ANY ((ARRAY['FAILED'::character varying, 'RETRY'::character varying])::text[])) AND (tentativi < max_tentativi) AND ((prossimo_tentativo IS NULL) OR (prossimo_tentativo <= now()))));
```

</div>


---
{% include-markdown "signature-core.md" %}
