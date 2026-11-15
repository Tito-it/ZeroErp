# 🔍 View `vw_indirizzi_ruolo_azioni`

> 📝 **Descrizione**
>
> Le azioni di riga sugli indirizzi del ruolo: una riga per indirizzo (indirizzo_id, soggetto_ruolo_id, istanza_utility_id). copia_blocco_reason / copia_blocco_reason_key: il primo motivo di anagrafiche.fn_check_copia_indirizzo_ruolo, la check che il verbo anagrafiche.fn_copia_indirizzo_ruolo solleva (NULL = la copia si puo' proporre; l'unico motivo e' NESSUN_TIPO_PROPONIBILE). E' la superficie dell'azione COPIA_INDIRIZZO_RUOLO nel registro config.azioni_riga. security_invoker. Si filtra per soggetto_ruolo_id o indirizzo_id; le colonne dell'indirizzo stanno in anagrafiche.vw_indirizzi_resolved_ruolo (stesso indirizzo_id). Le righe della cascata che vengono dal soggetto non sono qui: la loro azione e' la copia del soggetto, in anagrafiche.vw_indirizzi_soggetti_azioni.

> 🔒 **Opzioni di sicurezza**: `security_invoker=true` — reloption non visibile in `pg_get_viewdef`, riportata qui esplicitamente. Va **ri-specificata** in ogni `CREATE OR REPLACE VIEW`, altrimenti PostgreSQL la azzera.

> 🔓 **Sicurezza**: `security_invoker` — le tabelle sotto si leggono con i privilegi e la RLS di chi interroga; owner `zeroerp_owner`.

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE VIEW anagrafiche.vw_indirizzi_ruolo_azioni
WITH (security_invoker=true) AS
SELECT i.id AS indirizzo_id,
    i.soggetto_ruolo_id,
    i.istanza_utility_id,
    ((chk.motivi -> 0) ->> 'reason'::text) AS copia_blocco_reason,
    ((chk.motivi -> 0) ->> 'reason_key'::text) AS copia_blocco_reason_key
   FROM (anagrafiche.indirizzi i
     CROSS JOIN LATERAL ( SELECT anagrafiche.fn_check_copia_indirizzo_ruolo(i.id) AS motivi) chk);
```

</div>


---
{% include-markdown "signature-core.md" %}
