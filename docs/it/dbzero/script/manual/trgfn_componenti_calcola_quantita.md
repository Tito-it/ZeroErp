## 📘 Documentazione Concettuale – Trigger Function `script.trgfn_componenti_calcola_quantita()`

> 👀 **Vedi anche**
>
> [script.trgfn_componenti_propaga_qta](/dbzero/script/funzioni/trgfn_componenti_propaga_qta) — complementare: propaga cambio quantita padre ai figli esistenti
> [vendite.preventivi_righe_componenti](/dbzero/vendite/tabelle/preventivi_righe_componenti) — prima tabella che la usa

Trigger function **BEFORE INSERT OR UPDATE** sulla tabella figli. Imposta `NEW.quantita = NEW.coeff_qta_snapshot × quantita_riga_padre`. Funzione di defense-in-depth: garantisce che la quantita del componente sia sempre coerente con la riga padre, indipendentemente dal valore inviato dal BE.

---

### 🎯 Scopo Principale

- **Correttezza automatica**: il BE non deve calcolare `quantita` prima dell'INSERT — la invia come placeholder (o come valore calcolato) e il trigger la sovrascrive con il valore corretto.
- **Defense-in-depth**: se il BE invia una quantita inconsistente (bug, refactoring, race condition), il trigger la corregge prima che la riga venga persistita.
- **Complemento a `propaga_qta`**: `calcola_quantita` gestisce il caso INSERT/UPDATE diretto; `propaga_qta` gestisce il caso aggiornamento della quantita padre su figli già esistenti.

---

### TG_ARGV layout

```
TG_ARGV[0]  schema padre        (es. 'vendite')
TG_ARGV[1]  tab_padre           (es. 'preventivi_righe')
TG_ARGV[2]  col FK figli->padre (es. 'riga_preventivo_id')
```

---

### Logica

1. Legge l'id padre da `NEW` tramite dynamic SQL su `TG_ARGV[2]`.
2. Legge `quantita` del padre dalla tabella padre.
3. Imposta `NEW.quantita := NEW.coeff_qta_snapshot × COALESCE(v_qta_padre, 1)`.
4. Ritorna `NEW` (BEFORE trigger, modifica la riga in arrivo).

Il `COALESCE(v_qta_padre, 1)` è un ulteriore guard difensivo: se il padre non viene trovato (situazione teoricamente impossibile per i FK constraint), evita `NULL` nel prodotto.

---

### Applicazione

- Timing: **BEFORE INSERT OR UPDATE**
- Fase: **`_m50_`** (intermedia, dopo `_a10_` guard)
- Scope: **FOR EACH ROW**
- Trigger name: `trg_<tabella>_m50_calcola_quantita_ins_upd`

L'ordine di esecuzione è: guard `_a10_` → calcola quantita `_m50_` → audit → tx_id → poi AFTER trigger.

---

### Note operative

- La fase `_m50_` garantisce che il guard `_a10_guard_bom_coerenza` sia già passato prima del calcolo quantita — la BoM è valida al momento del calcolo.
- Il calcolo sovrascrive sempre il valore fornito: non è una "normalizzazione se diverso" ma una riscrittura incondizionata. Questo è intenzionale — la quantita del componente non è un campo libero.
