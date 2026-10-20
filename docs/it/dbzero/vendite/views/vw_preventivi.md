{% include-markdown "it/dbzero/vendite/manual/vw_preventivi.md" %}
# 🔍 View `vw_preventivi`

> 📝 **Descrizione**
>
> Wrapper di vendite.preventivi con i flag di revisione derivati. Le due domande sono colonne distinte: is_superata (esiste una rev superiore non-abortita che la rimpiazza; il complemento e' «e' l'ultima revisione») e is_abortito (lo stato proprio e' di annullamento). is_attiva = NOT is_abortito AND NOT is_superata: invariata dal 2026-07-08, esattamente una per numero. has_next_revisione = esiste una rev superiore di qualunque stato (abortite comprese). Chi vuole «solo l'ultima revisione» filtra is_superata IS FALSE, non is_attiva. rev 2026-08-28.

> 🔒 **Opzioni di sicurezza**: `security_invoker=on` — reloption non visibile in `pg_get_viewdef`, riportata qui esplicitamente. Va **ri-specificata** in ogni `CREATE OR REPLACE VIEW`, altrimenti PostgreSQL la azzera.

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE VIEW vendite.vw_preventivi
WITH (security_invoker=on) AS
SELECT p.id,
    p.numero,
    p.rev,
    p.billing_account_id,
    p.istanza_utility_id,
    p.utility_id,
    p.validita_dal,
    p.validita_al,
    p.totale_imponibile,
    p.totale_iva,
    p.totale_documento,
    p.valuta_id,
    p.meta,
    p.data_insert,
    p.user_insert,
    p.data_update,
    p.user_update,
    p.competenza_mese,
    p.fatturazione_immediata,
    p.stato_doc_preventivo_id,
    p.data,
    p.termine_pagamento_id,
    p.uid,
    p.storicizza,
    p.tx_id,
    p.emittente_fiscale_id,
    ((NOT d.is_abortito) AND (NOT d.is_superata)) AS is_attiva,
    d.is_superata,
    d.is_abortito,
    d.has_next_revisione
   FROM (vendite.preventivi p
     CROSS JOIN LATERAL ( SELECT (EXISTS ( SELECT 1
                   FROM config.stati_doc_preventivi s0
                  WHERE ((s0.id = p.stato_doc_preventivo_id) AND (s0.is_abortito IS TRUE)))) AS is_abortito,
            (EXISTS ( SELECT 1
                   FROM (vendite.preventivi p2
                     JOIN config.stati_doc_preventivi s2 ON ((s2.id = p2.stato_doc_preventivo_id)))
                  WHERE (((p2.numero)::text = (p.numero)::text) AND (p2.rev > p.rev) AND (s2.is_abortito IS FALSE)))) AS is_superata,
            (EXISTS ( SELECT 1
                   FROM vendite.preventivi p3
                  WHERE (((p3.numero)::text = (p.numero)::text) AND (p3.rev > p.rev)))) AS has_next_revisione) d);
```

</div>


---
{% include-markdown "signature-core.md" %}
