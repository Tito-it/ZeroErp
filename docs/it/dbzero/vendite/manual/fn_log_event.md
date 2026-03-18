## 📘 Documentazione Concettuale – Funzione `vendite.fn_log_event`

> 👀 **Vedi anche**
>
**Approfondimento tabelle:**
>
• [vendite.event_log](/dbzero/vendite/tabelle/event_log)  
>
### 🎯 Scopo Principale
`vendite.fn_log_event` fornisce un entrypoint unico (DB) per registrare eventi
append-only in `vendite.event_log`, sia da servizi Python sia da funzioni SQL.

---

### Regole principali

* esegue solo `INSERT` su `vendite.event_log`;
* restituisce l'`id` dell'evento inserito;
* `severity` null viene normalizzata a `INFO`;
* `payload` null viene normalizzato a `{}`.

La validazione formale di `severity` resta sul vincolo `CHECK` della tabella.

---

### Esempio d'uso

```sql
SELECT vendite.fn_log_event(
  p_domain => 'PIPELINE',
  p_entity_type => 'LOTTO',
  p_entity_id => 123,
  p_event_code => 'STEP_COMPLETED',
  p_severity => 'INFO',
  p_correlation_id => '11111111-1111-1111-1111-111111111111'::uuid,
  p_actor => 'service:django',
  p_source => 'django',
  p_payload => jsonb_build_object('step', 'DEFINITIVA', 'task', 'numera_fatture')
);
```

---

{% include-markdown "signature-core.md" %}
