{% include-markdown "it/dbzero/vendite/manual/vw_partite_merce.md" %}
# 🔍 View `vw_partite_merce`

> 📝 **Descrizione**
>
> La PARTITA DI MERCE: una riga per riga di DDT attiva su documento EMESSO in poi, con la riga d'ordine come ORIGINE nullable. rev 2026-09-21 (D14, quarta leva): il conto NON sta piu' qui — sta in vendite.fn_partite_merce(p_ddt_ids, p_ordine_ids), e questa vista ne e' la proiezione senza filtro, fn(NULL, NULL): UN corpo solo (D1). Chi legge PER DOCUMENTO chiama la funzione con un seme e paga la CHIUSURA del documento, non le partite di tutti: fn_list_ddt_da_pushare, fn_ddt_push_diagnosi, BE list_partite_merce. Chi legge tutto (cockpit, le tre viste a valle, i verbi dei resi fino al giro D3) legge la vista. Colonne proiettate per NOME con consegnato::numeric(18,6): un SELECT * perderebbe il typmod in silenzio, e il ritorno sarebbe un DROP a cascata. La regola della chiusura e la sua trappola (chi aggiunge una chiave nuova allarga la chiusura) stanno nel COMMENT della funzione. Storia del conto (rev N6, N7, D14 17-09 e 21-09 terza leva) nel manuale vw_partite_merce.md. security_invoker=on ri-specificato (la reloption non si vede in pg_get_viewdef e un CREATE OR REPLACE la azzera: qui significa far girare la funzione come owner, bypass della RLS, regressione V-1).

> 🔒 **Opzioni di sicurezza**: `security_invoker=on` — reloption non visibile in `pg_get_viewdef`, riportata qui esplicitamente. Va **ri-specificata** in ogni `CREATE OR REPLACE VIEW`, altrimenti PostgreSQL la azzera.

> 🔓 **Sicurezza**: `security_invoker` — le tabelle sotto si leggono con i privilegi e la RLS di chi interroga; owner `zeroerp_owner`.

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE VIEW vendite.vw_partite_merce
WITH (security_invoker=on) AS
SELECT ddt_riga_id,
    ddt_id,
    ddt_uid,
    articolo_id,
    is_composito,
    ordine_riga_id,
    ordine_id,
    origine,
    fatturabile,
    (consegnato)::numeric(18,6) AS consegnato,
    reso,
    in_riconsegna,
    tenuti,
    fatturato_merce,
    fatturato_da_ordine,
    fatturato,
    misurabile,
    differenza,
    stato,
    e_riconsegna,
    sospetto_duplicato_ordine,
    rettificato,
    riconsegna_quota_nuova
   FROM vendite.fn_partite_merce(NULL::bigint[], NULL::bigint[]) p(ddt_riga_id, ddt_id, ddt_uid, articolo_id, is_composito, ordine_riga_id, ordine_id, origine, fatturabile, consegnato, reso, in_riconsegna, tenuti, fatturato_merce, fatturato_da_ordine, fatturato, misurabile, differenza, stato, e_riconsegna, sospetto_duplicato_ordine, rettificato, riconsegna_quota_nuova);
```

</div>


---
{% include-markdown "signature-core.md" %}
