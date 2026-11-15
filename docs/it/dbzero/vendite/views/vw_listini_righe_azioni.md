{% include-markdown "it/dbzero/vendite/manual/vw_listini_righe_azioni.md" %}
# 🔍 View `vw_listini_righe_azioni`

> 📝 **Descrizione**
>
> Le azioni di riga delle righe di listino: una riga per riga (listino_riga_id, listino_versione_id). modifica_blocco_reason / modifica_blocco_reason_key: il primo motivo di script.fn_check_listino_riga_scrivibile per la riga, la stessa fn_check che il guard vendite.trgfn_listini_righe_guard_stato solleva su UPDATE e DELETE (VERSIONE_CHIUSA: la versione e' la storia dei prezzi; VERSIONE_NON_IN_BOZZA: la versione e' il listino in uso; NULL = la riga si modifica e si elimina, cioe' la versione e' in bozza). rettifica_blocco_reason / rettifica_blocco_reason_key: il primo motivo di script.fn_check_listino_riga_rettificabile, la stessa che il verbo vendite.fn_rettifica_riga_listino solleva (VERSIONE_IN_BOZZA: si modifica; VERSIONE_CHIUSA; NON_IN_VIGORE: la versione non e' quella in vigore oggi; RIGA_PROPAGATA: il prezzo e' stato usato da un documento; NULL = il prezzo si rettifica). E' la superficie delle azioni MODIFICA_RIGA_LISTINO e RETTIFICA_RIGA_LISTINO nel registro config.azioni_riga. security_invoker: le sole righe dei listini del proprio perimetro, e i documenti che le citano col perimetro di chi guarda. Si filtra per listino_versione_id o listino_riga_id.

> 🔒 **Opzioni di sicurezza**: `security_invoker=true` — reloption non visibile in `pg_get_viewdef`, riportata qui esplicitamente. Va **ri-specificata** in ogni `CREATE OR REPLACE VIEW`, altrimenti PostgreSQL la azzera.

> 🔓 **Sicurezza**: `security_invoker` — le tabelle sotto si leggono con i privilegi e la RLS di chi interroga; owner `zeroerp_owner`.

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE VIEW vendite.vw_listini_righe_azioni
WITH (security_invoker=true) AS
SELECT lr.id AS listino_riga_id,
    lr.listino_versione_id,
    ((mot.motivi -> 0) ->> 'reason'::text) AS modifica_blocco_reason,
    ((mot.motivi -> 0) ->> 'reason_key'::text) AS modifica_blocco_reason_key,
    ((ret.motivi -> 0) ->> 'reason'::text) AS rettifica_blocco_reason,
    ((ret.motivi -> 0) ->> 'reason_key'::text) AS rettifica_blocco_reason_key
   FROM ((vendite.listini_righe lr
     CROSS JOIN LATERAL ( SELECT script.fn_check_listino_riga_scrivibile(lr.listino_versione_id, lr.id) AS motivi) mot)
     CROSS JOIN LATERAL ( SELECT script.fn_check_listino_riga_rettificabile(lr.id) AS motivi) ret);
```

</div>


---
{% include-markdown "signature-core.md" %}
