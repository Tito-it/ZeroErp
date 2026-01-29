## 📘 Documentazione Concettuale – Funzione `vendite.trgfn_attivita_norm_competenza_mese`

> 👀 **Vedi anche**
>
> **Approfondimento tabelle:**
>
> • [vendite.attivita_fatturabili](/dbzero/vendite/tabelle/attivita_fatturabili)  
>
---

### 🎯 Scopo Principale

(latest review 29-01-2026)  
La funzione **`vendite.trgfn_attivita_norm_competenza_mese()`** normalizza
`competenza_mese` al **primo giorno del mese**.

---

### ✅ Regole principali

* Se `competenza_mese` e` valorizzata, viene troncata al primo giorno del mese.
* Nessuna modifica quando `competenza_mese` e` NULL.

---

### ✅ Output

Nessun output (trigger BEFORE). Aggiorna il valore di `competenza_mese`.

---

### 🧪 Esempio

```sql
INSERT INTO vendite.attivita_fatturabili (
  articolo_id, istanza_utility_id, data_attivita, quantita, competenza_mese
)
VALUES (
  :articolo_id, :istanza_id, current_date, 1, date '2026-01-20'
);
-- competenza_mese -> 2026-01-01
```

---

{% include-markdown "signature-core.md" %}
