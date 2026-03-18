## 📘 Documentazione Concettuale – Funzione `script.trgfn_guard_utility_tipo_ruolo_by_cols`
### 🎯 Scopo Principale
La funzione **`script.trgfn_guard_utility_tipo_ruolo_by_cols()`** e` una
trigger function generica che applica il controllo utility/ruolo su tabelle
con colonne configurabili.

---

### Argomenti trigger (`TG_ARGV`)

* `TG_ARGV[0]`: nome colonna utility (es. `utility_id`)
* `TG_ARGV[1]`: nome colonna soggetto ruolo (es. `emittente_soggetto_ruolo_id`)

---

### Comportamento

1. legge i valori dalle colonne configurate su `NEW`;
2. risolve il `tipo_ruolo_id` da `anagrafiche.soggetti_ruoli`;
3. chiama `script.fn_guard_utility_tipo_ruolo(...)`.

Se utility/ruolo non sono valorizzati, il controllo viene saltato in quella fase.

---

### Esempio d’uso (creazione trigger)

```sql
CREATE TRIGGER trg_demo_a10_guard_utility_tipo_ruolo_ins_upd
BEFORE INSERT OR UPDATE OF utility_id, soggetto_ruolo_id
ON demo.tabella_ruolo_utility
FOR EACH ROW
EXECUTE FUNCTION script.trgfn_guard_utility_tipo_ruolo_by_cols('utility_id', 'soggetto_ruolo_id');
```
