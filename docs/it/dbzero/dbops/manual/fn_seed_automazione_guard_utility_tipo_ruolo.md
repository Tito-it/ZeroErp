## 📘 Documentazione Concettuale – Funzione `dbops.fn_seed_automazione_guard_utility_tipo_ruolo`
### 🎯 Scopo Principale
La funzione **`dbops.fn_seed_automazione_guard_utility_tipo_ruolo(p_schemas)`**
popola la tabella di configurazione automazione individuando in modo
automatico le tabelle candidate.

---

### Criteri di rilevazione

* Tabella nell'ambito risolto (`dbops.fn_resolve_scope`).
* Presenza di colonna `utility_id`.
* Presenza di:
  * FK diretta verso `anagrafiche.soggetti_ruoli`, oppure
  * colonna con naming `soggetto_ruolo_id` / `*_soggetto_ruolo_id`.

---

### Comportamento

* Inserisce righe in `dbops.automazione_guard_utility_tipo_ruolo`.
* Non sovrascrive righe gia presenti (`ON CONFLICT DO NOTHING`).

---

### Esempio d’uso

```sql
SELECT dbops.fn_seed_automazione_guard_utility_tipo_ruolo(ARRAY['anagrafiche', 'vendite']);
```
