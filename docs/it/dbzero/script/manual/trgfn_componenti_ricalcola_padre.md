## 📘 Documentazione Concettuale – Trigger Function `script.trgfn_componenti_ricalcola_padre()`

> 👀 **Vedi anche**
>
> [script.fn_ricalcola_prezzo_padre_da_componenti](/dbzero/script/funzioni/fn_ricalcola_prezzo_padre_da_componenti) — funzione pura chiamata internamente
> [vendite.preventivi_righe_componenti](/dbzero/vendite/tabelle/preventivi_righe_componenti) — prima tabella che la usa

Trigger function **AFTER INSERT OR UPDATE OR DELETE** generica del pattern BoM CASO A. Dopo ogni modifica a un componente, ricalcola `prezzo_unitario` della riga padre come `SUM(figli.prezzo_unitario × coeff_qta_snapshot)` sui figli attivi.

---

### 🎯 Scopo Principale

Mantiene il prezzo della riga padre composita CASO A sempre coerente con i prezzi dei suoi componenti. Il prezzo padre è **derivato, non inserito direttamente**: qualsiasi modifica (INSERT, UPDATE, DELETE) a un componente propaga automaticamente il ricalcolo.

---

### TG_ARGV layout

```
TG_ARGV[0]  schema          (es. 'vendite')
TG_ARGV[1]  tab_padre       (es. 'preventivi_righe')
TG_ARGV[2]  tab_figli       (es. 'preventivi_righe_componenti')
TG_ARGV[3]  col FK figli->padre (es. 'riga_preventivo_id')
```

---

### Logica

Legge l'id della riga padre dalla riga coinvolta (`OLD` per DELETE, `NEW` per INSERT/UPDATE) tramite SQL dinamico su `TG_ARGV[3]`, poi chiama `script.fn_ricalcola_prezzo_padre_da_componenti(...)`.

Ritorna `NULL` (AFTER trigger, valore di ritorno ignorato da PostgreSQL).

---

### Applicazione

- Timing: **AFTER INSERT OR UPDATE OR DELETE**
- Fase: **`_z90_`** (effetto finale)
- Scope: **FOR EACH ROW**
- Trigger name: `trg_<tabella>_z90_ricalcola_padre_ins_upd_dlt`

---

### Note operative

- Il ricalcolo aggiorna `preventivi_righe.prezzo_unitario`, che a sua volta attiva il trigger `_z90_ricalcola_totali` sulla testata preventivo — la catena è intenzionale.
- L'UPDATE sul padre ha un guard (`trgfn_preventivi_righe_guard_pending`) che blocca modifiche struttura se la riga padre è PENDING. Questo caso non dovrebbe mai verificarsi su righe padre CASO A (il prezzo padre non è soggetto a workflow L3 diretto).
