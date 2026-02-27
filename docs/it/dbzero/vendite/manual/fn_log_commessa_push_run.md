## 📘 Documentazione Concettuale – Funzione `vendite.fn_log_commessa_push_run`

> 👀 **Vedi anche**
>
> **Approfondimento tabelle:**
>
> • [vendite.commesse_push_log](/dbzero/vendite/tabelle/commesse_push_log)  
>
---

### 🎯 Scopo Principale

`vendite.fn_log_commessa_push_run` registra in modo uniforme il risultato di un
run dell'orchestratore push commesse scrivendo una riga in `commesse_push_log`.

---

### ✅ Regole principali

* valida `stato` (`COMPLETATO | PARZIALE | ERRORE`),
* valida `durata_ms` (se presente, `>= 0`),
* normalizza `stato` in uppercase,
* ritorna l'`id` della riga log inserita.
* user tracciato automaticamente dal trigger audit JWT (`user_insert`).

---

### 🧪 Esempio d’uso

```sql
SELECT vendite.fn_log_commessa_push_run(
  p_dry_run => false,
  p_source_types => ARRAY['HandlerPreventivi', 'HandlerOrdini'],
  p_risultato => jsonb_build_object('HandlerPreventivi', jsonb_build_object('created', 12, 'errors', '[]'::jsonb)),
  p_stato => 'COMPLETATO',
  p_durata_ms => 842
);
```

---

{% include-markdown "signature-core.md" %}
