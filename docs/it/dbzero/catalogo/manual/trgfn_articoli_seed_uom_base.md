## 📘 Documentazione Concettuale – Funzione `catalogo.trgfn_articoli_seed_uom_base()`

> 👀 **Vedi anche**
>
Approfondimento tabelle:
> • [catalogo.articoli](/dbzero/catalogo/tabelle/articoli)
> • [catalogo.articoli_uom_operativa](/dbzero/catalogo/tabelle/articoli_uom_operativa)
> • [catalogo.unita_misura](/dbzero/catalogo/tabelle/unita_misura)

---
### 🎯 Scopo Principale

(rev 2026-08-21)

Garantisce che **ogni articolo nasca con la sua unità di misura base già presente** in
`catalogo.articoli_uom_operativa`. Alla creazione dell'articolo inserisce la riga
`is_base = TRUE`, `factor_to_base = 1`, `attivo = TRUE` sull'UoM dichiarata in
`articoli.uom_id`.

Senza questo automatismo l'articolo esisterebbe con una `uom_id` in testata ma senza la
corrispondente riga operativa, e ogni conversione articolo-specifica partirebbe da un
insieme vuoto: non ci sarebbe il fattore 1 su cui poggiare tutti gli altri.

---

### Aggancio

Trigger `trg_articoli_a10_seed_uom_base_ins` — `AFTER INSERT` su `catalogo.articoli`,
`FOR EACH ROW`.

⚠️ Il nome porta il prefisso di fase `_a10_`, riservato per convenzione a guard e blocchi,
ma il trigger è un **seed `AFTER`**, non un guard. È un'incoerenza di naming, non di
comportamento.

---

### Regole applicate

1. `INSERT` in `catalogo.articoli_uom_operativa` con `articolo_id = NEW.id`,
   `uom_id = NEW.uom_id`, `is_base = TRUE`, `factor_to_base = 1`, `attivo = TRUE`.
2. `ON CONFLICT ON CONSTRAINT uq_artuomop_articolo_uom DO NOTHING`: se la coppia
   articolo/UoM esiste già, non succede nulla.
3. `RETURN NULL` — corretto e ininfluente, trattandosi di un trigger `AFTER`.

---

### Perché è idempotente (e perché conta)

Il `DO NOTHING` sul vincolo di unicità rende l'inserimento ripetibile: un re-run di un
import o un seed che ripassa sugli stessi articoli non fallisce e non duplica.

⚠️ Il rovescio: se la riga esiste già ma con valori **diversi** — per esempio
`is_base = FALSE` o `factor_to_base ≠ 1` perché qualcuno l'ha modificata a mano — il
trigger **non la corregge**. `DO NOTHING` non è `DO UPDATE`: l'articolo resta senza una
UoM base valida e il difetto non emerge qui.

---

### Codici errore

Nessuno: la funzione non chiama `script.fn_log_and_raise_error`. Un eventuale fallimento
è una violazione di vincolo grezza sulla tabella figlia.

`articoli.uom_id` è `NOT NULL`, quindi il caso «articolo senza UoM» non arriva mai a
questo trigger: viene fermato prima dal vincolo di colonna.

---

{% include-markdown "signature-core.md" %}
