## 📘 Documentazione Concettuale – Tabella `catalogo.unita_misura_conversioni`

> 👀 **Vedi anche**
>
> **Approfondimento Tabelle**
> • [`catalogo.unita_misura`](/dbzero/catalogo/tabelle/unita_misura)  
> • [`catalogo.articoli_uom_operativa`](/dbzero/catalogo/tabelle/articoli_uom_operativa)  
>
> **Approfondimento Funzioni**
> • [`catalogo.fn_get_uom_factor`](/dbzero/catalogo/funzioni/fn_get_uom_factor)  

---

### 🎯 Scopo Principale

(latest review 13-01-26)
`catalogo.unita_misura_conversioni` definisce **conversioni globali** tra unita di misura, indipendenti dall’articolo. Serve come **fallback** quando una conversione non e' stata specificata per articolo in `catalogo.articoli_uom_operativa`.

Esempi tipici:
* **SMC → MJ** con fattore standard.
* **kWh → MJ** con fattore standard.

---

### 🔗 Relazioni

| Tipo | Tabella ↔ Campo                             | Descrizione                  |
| ---- | ------------------------------------------- | ---------------------------- |
| FK → | `catalogo.unita_misura(id)` ← `uom_from_id` | Unita di misura sorgente     |
| FK → | `catalogo.unita_misura(id)` ← `uom_to_id`   | Unita di misura destinazione |

---

### 🧱 Struttura logica (campi chiave)

* **Identita**: `id BIGINT` (PK)
* **Direzione conversione**: `uom_from_id`, `uom_to_id`
* **Fattore**: `fattore NUMERIC(18,6)` (moltiplicatore da `from` a `to`)
* **Validita**: `valido_dal`, `valido_al` (NULL = infinito)
* **Stato**: `attivo`
* **Meta/Audit**: `meta`, `data_insert`, `user_insert`, `data_update`, `user_update`

---

### 🚦 Vincoli & Regole

* **Fattore positivo**: `fattore > 0`
* **No auto-conversione**: `uom_from_id <> uom_to_id`
* **Date coerenti**: `valido_al IS NULL OR valido_al > valido_dal`
* **No overlap temporali** sulla stessa coppia `(uom_from_id, uom_to_id)` (EXCLUDE GiST)

---

### 🔁 Workflow di conversione (fallback)

1. **Articolo-specifico**: se esiste una riga attiva e valida in `catalogo.articoli_uom_operativa`, usa `factor_to_base`.
2. **Globale diretto**: se manca la riga articolo, cerca conversione globale `uom_from -> uom_to`.
3. **Globale inverso**: se esiste solo la conversione `uom_to -> uom_from`, applica `1/fattore`.
4. **Se assente**: la funzione ritorna `NULL` (gestione a carico di trigger/applicazione).

---

### 🔎 Esempi d’uso

**1) Conversione globale SMC -> MJ**

```sql
INSERT INTO catalogo.unita_misura_conversioni (
  uom_from_id, uom_to_id, fattore, valido_dal, attivo
)
VALUES (
  :uom_smc_id, :uom_mj_id, 38.2, DATE '2026-01-01', true
);
```

**2) Uso fallback per articolo senza mappatura**

```sql
SELECT catalogo.fn_get_uom_factor(:articolo_id, :uom_mj_id);
```

Se l’articolo non ha una UoM operativa specifica, la funzione usera' la conversione globale.

---

{% include-markdown "signature-core.md" %}

