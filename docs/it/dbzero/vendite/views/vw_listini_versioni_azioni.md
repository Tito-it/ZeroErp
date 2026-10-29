{% include-markdown "it/dbzero/vendite/manual/vw_listini_versioni_azioni.md" %}
# 🔍 View `vw_listini_versioni_azioni`

> 📝 **Descrizione**
>
> Le AZIONI DI RIGA delle versioni di listino: una riga per versione (versione_id, listino_id). attivazione_blocco_reason / attivazione_blocco_reason_key: il PRIMO motivo di script.fn_check_versione_listino_attivabile (la stessa fn_check che vendite.fn_attiva_versione_listino e il guard di transizione sollevano; NULL = niente vieta l'attivazione). eliminazione_blocco_reason / eliminazione_blocco_reason_key: il PRIMO motivo di script.fn_check_versione_listino_eliminabile (la stessa che vendite.fn_elimina_versione_listino e il guard per stato sollevano: non in bozza, citata da un documento; NULL = si elimina). chiusura_blocco_reason / chiusura_blocco_reason_key: il PRIMO motivo di script.fn_check_versione_listino_chiudibile senza data (non ATTIVA; NULL = «Chiudi» acceso; la fine nel passato la giudica vendite.fn_programma_chiusura_versione_listino con la data scelta). «Clona» non ha colonne: si clona da qualunque stato. Lo stato non c'e': chi puo' attivare da quale stato lo dice la riga lista (script.fn_doc_azioni_permesse). E' la superficie delle azioni ATTIVA_VERSIONE_LISTINO, ELIMINA_VERSIONE_LISTINO e CHIUDI_VERSIONE_LISTINO nel registro config.azioni_riga. security_invoker: i soli listini del proprio perimetro. Si filtra per listino_id o versione_id. Prima i pulsanti si decidevano nel frontend (conteggio delle righe, stato). Brief: brief-modello-documento-vendita §16 (L-4), §16.11 (E-2) e §16.14 (C-2, C-3, Tid 2026-10-29).

> 🔒 **Opzioni di sicurezza**: `security_invoker=true` — reloption non visibile in `pg_get_viewdef`, riportata qui esplicitamente. Va **ri-specificata** in ogni `CREATE OR REPLACE VIEW`, altrimenti PostgreSQL la azzera.

> 🔓 **Sicurezza**: `security_invoker` — le tabelle sotto si leggono con i privilegi e la RLS di chi interroga; owner `zeroerp_owner`.

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE VIEW vendite.vw_listini_versioni_azioni
WITH (security_invoker=true) AS
SELECT lv.id AS versione_id,
    lv.listino_id,
    ((chk.motivi -> 0) ->> 'reason'::text) AS attivazione_blocco_reason,
    ((chk.motivi -> 0) ->> 'reason_key'::text) AS attivazione_blocco_reason_key,
    ((eli.motivi -> 0) ->> 'reason'::text) AS eliminazione_blocco_reason,
    ((eli.motivi -> 0) ->> 'reason_key'::text) AS eliminazione_blocco_reason_key,
    ((chi.motivi -> 0) ->> 'reason'::text) AS chiusura_blocco_reason,
    ((chi.motivi -> 0) ->> 'reason_key'::text) AS chiusura_blocco_reason_key
   FROM (((vendite.listini_versioni lv
     CROSS JOIN LATERAL ( SELECT script.fn_check_versione_listino_attivabile(lv.id) AS motivi) chk)
     CROSS JOIN LATERAL ( SELECT script.fn_check_versione_listino_eliminabile(lv.id) AS motivi) eli)
     CROSS JOIN LATERAL ( SELECT script.fn_check_versione_listino_chiudibile(lv.id) AS motivi) chi);
```

</div>


---
{% include-markdown "signature-core.md" %}
