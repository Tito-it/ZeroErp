{% include-markdown "it/dbzero/vendite/manual/vw_listini_versioni_azioni.md" %}
# 🔍 View `vw_listini_versioni_azioni`

> 📝 **Descrizione**
>
> Le azioni di riga delle versioni di listino: una riga per versione (versione_id, listino_id). attivazione_blocco_reason / attivazione_blocco_reason_key: il primo motivo di script.fn_check_versione_listino_attivabile (la stessa fn_check che vendite.fn_attiva_versione_listino e il guard di transizione sollevano; NULL = niente vieta l'attivazione). eliminazione_blocco_reason / eliminazione_blocco_reason_key: il primo motivo di script.fn_check_versione_listino_eliminabile (la stessa che vendite.fn_elimina_versione_listino e il guard per stato sollevano: non in bozza, citata da un documento; NULL = si elimina). chiusura_blocco_reason / chiusura_blocco_reason_key: il primo motivo di script.fn_check_versione_listino_chiudibile senza data (non ATTIVA; NULL = «Chiudi» acceso; la fine nel passato la giudica vendite.fn_programma_chiusura_versione_listino con la data scelta). Le scritture della versione si fanno solo in bozza: il primo motivo di script.fn_check_listino_riga_scrivibile senza riga (VERSIONE_CHIUSA, VERSIONE_NON_IN_BOZZA; NULL = si scrive), in quattro azioni con le loro colonne: aggiunta_riga_blocco_reason / _key (una riga nuova, il guard vendite.trgfn_listini_righe_guard_stato), variazione_blocco_reason / _key (la variazione percentuale dei prezzi delle righe, il verbo vendite.fn_varia_prezzi_versione_listino, che la giudica dalla versione anche a righe zero), prezzi_bundle_blocco_reason / _key (i prezzi dei componenti dei kit, il guard vendite.trgfn_listini_righe_comp_guard_immutabilita_v5), periodicita_kit_blocco_reason / _key (la periodicita' dei kit, il guard vendite.trgfn_listini_kit_guard). Il prezzo di una riga della versione in vigore si rettifica: la superficie e' vendite.vw_listini_righe_azioni. «Clona» non ha colonne: si clona da qualunque stato. Lo stato non c'e': chi puo' attivare da quale stato lo dice la riga lista (script.fn_doc_azioni_permesse). E' la superficie delle azioni ATTIVA_VERSIONE_LISTINO, ELIMINA_VERSIONE_LISTINO, CHIUDI_VERSIONE_LISTINO, AGGIUNGI_RIGA_LISTINO, VARIA_PREZZI_LISTINO, PREZZI_BUNDLE_LISTINO e PERIODICITA_KIT_LISTINO nel registro config.azioni_riga. security_invoker: i soli listini del proprio perimetro. Si filtra per listino_id o versione_id.

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
    ((chi.motivi -> 0) ->> 'reason_key'::text) AS chiusura_blocco_reason_key,
    ((rig.motivi -> 0) ->> 'reason'::text) AS aggiunta_riga_blocco_reason,
    ((rig.motivi -> 0) ->> 'reason_key'::text) AS aggiunta_riga_blocco_reason_key,
    ((rig.motivi -> 0) ->> 'reason'::text) AS variazione_blocco_reason,
    ((rig.motivi -> 0) ->> 'reason_key'::text) AS variazione_blocco_reason_key,
    ((rig.motivi -> 0) ->> 'reason'::text) AS prezzi_bundle_blocco_reason,
    ((rig.motivi -> 0) ->> 'reason_key'::text) AS prezzi_bundle_blocco_reason_key,
    ((rig.motivi -> 0) ->> 'reason'::text) AS periodicita_kit_blocco_reason,
    ((rig.motivi -> 0) ->> 'reason_key'::text) AS periodicita_kit_blocco_reason_key
   FROM ((((vendite.listini_versioni lv
     CROSS JOIN LATERAL ( SELECT script.fn_check_versione_listino_attivabile(lv.id) AS motivi) chk)
     CROSS JOIN LATERAL ( SELECT script.fn_check_versione_listino_eliminabile(lv.id) AS motivi) eli)
     CROSS JOIN LATERAL ( SELECT script.fn_check_versione_listino_chiudibile(lv.id) AS motivi) chi)
     CROSS JOIN LATERAL ( SELECT script.fn_check_listino_riga_scrivibile(lv.id) AS motivi) rig);
```

</div>


---
{% include-markdown "signature-core.md" %}
