{% include-markdown "it/dbzero/vendite/manual/vw_preventivi.md" %}
# 🔍 View `vw_preventivi`

> 🔒 **Opzioni di sicurezza**: `security_invoker=on` — reloption non visibile in `pg_get_viewdef`, riportata qui esplicitamente. Va **ri-specificata** in ogni `CREATE OR REPLACE VIEW`, altrimenti PostgreSQL la azzera.

```sql
CREATE OR REPLACE VIEW vendite.vw_preventivi
WITH (security_invoker=on) AS
SELECT id,
    numero,
    rev,
    billing_account_id,
    istanza_utility_id,
    utility_id,
    validita_dal,
    validita_al,
    totale_imponibile,
    totale_iva,
    totale_documento,
    valuta_id,
    meta,
    data_insert,
    user_insert,
    data_update,
    user_update,
    competenza_mese,
    fatturazione_immediata,
    stato_doc_preventivo_id,
    data,
    termine_pagamento_id,
    uid,
    storicizza,
    tx_id,
    emittente_fiscale_id,
    ((NOT (EXISTS ( SELECT 1
           FROM config.stati_doc_preventivi s0
          WHERE ((s0.id = p.stato_doc_preventivo_id) AND (s0.is_abortito IS TRUE))))) AND (NOT (EXISTS ( SELECT 1
           FROM (vendite.preventivi p2
             JOIN config.stati_doc_preventivi s2 ON ((s2.id = p2.stato_doc_preventivo_id)))
          WHERE (((p2.numero)::text = (p.numero)::text) AND (p2.rev > p.rev) AND (s2.is_abortito IS FALSE)))))) AS is_attiva
   FROM vendite.preventivi p;
```


---
{% include-markdown "signature-core.md" %}
