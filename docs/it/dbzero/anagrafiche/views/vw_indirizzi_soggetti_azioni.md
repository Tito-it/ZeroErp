# 🔍 View `vw_indirizzi_soggetti_azioni`

> 📝 **Descrizione**
>
> Le azioni di riga sugli indirizzi del soggetto: una riga per indirizzo (indirizzo_soggetto_id, soggetto_id). copia_blocco_reason / copia_blocco_reason_key: il primo motivo di anagrafiche.fn_check_copia_indirizzo_soggetto, la check che il verbo anagrafiche.fn_copia_indirizzo_soggetto solleva (NULL = la copia si puo' proporre; l'unico motivo e' NESSUN_TIPO_PROPONIBILE). E' la superficie dell'azione COPIA_INDIRIZZO_SOGGETTO nel registro config.azioni_riga. security_invoker. Si filtra per soggetto_id o indirizzo_soggetto_id; le colonne dell'indirizzo stanno in anagrafiche.vw_indirizzi_resolved_soggetto (indirizzo_id = indirizzo_soggetto_id).

> 🔒 **Opzioni di sicurezza**: `security_invoker=true` — reloption non visibile in `pg_get_viewdef`, riportata qui esplicitamente. Va **ri-specificata** in ogni `CREATE OR REPLACE VIEW`, altrimenti PostgreSQL la azzera.

> 🔓 **Sicurezza**: `security_invoker` — le tabelle sotto si leggono con i privilegi e la RLS di chi interroga; owner `zeroerp_owner`.

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE VIEW anagrafiche.vw_indirizzi_soggetti_azioni
WITH (security_invoker=true) AS
SELECT isg.id AS indirizzo_soggetto_id,
    isg.soggetto_id,
    ((chk.motivi -> 0) ->> 'reason'::text) AS copia_blocco_reason,
    ((chk.motivi -> 0) ->> 'reason_key'::text) AS copia_blocco_reason_key
   FROM (anagrafiche.indirizzi_soggetti isg
     CROSS JOIN LATERAL ( SELECT anagrafiche.fn_check_copia_indirizzo_soggetto(isg.id) AS motivi) chk);
```

</div>


---
{% include-markdown "signature-core.md" %}
