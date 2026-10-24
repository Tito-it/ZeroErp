{% include-markdown "it/dbzero/script/manual/vw_audit_sources.md" %}
# 🔍 View `vw_audit_sources`

> 📝 **Descrizione**
>
> Vista pubblica delle storico audit-abili dal drawer admin. Espone (code, label_key, area_funzionale, storico_table). ⭐ `storico_table` e' entrata il 2026-09-02 e prima non c'era: il backend il nome fisico se lo costruiva concatenando `code`, che e' l'identita' LOGICA della sorgente (ci ordina e ci filtra l'API). Finche' i due coincidono la scorciatoia sembra funzionare; alla prima storico rinominata si separano, e la separazione non da' un avviso — da' un errore a valle su un database ricostruito, che e' esattamente cio' che e' successo con la vecchia storico.risorse_umane_auth_user quando la sua madre fu rinominata (ponte poi ritirato del tutto il 12-09-2026). ⚠️ Chi costruisce un `FROM` dinamico deve leggere QUESTA colonna, mai `code`. ⛔ E chi modifica questa vista usi `CREATE OR REPLACE`: un DROP porterebbe via i GRANT di zeroerp_app e zeroerp_batch_fatturazione, e nessun changeSet li ri-concede.

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE VIEW script.vw_audit_sources AS
SELECT code,
    label_key,
    area_funzionale,
    storico_table
   FROM dbops.audit_sources
  WHERE (attivo = true)
  ORDER BY code;
```

</div>


---
{% include-markdown "signature-core.md" %}
