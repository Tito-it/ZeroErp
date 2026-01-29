## 📘 Documentazione Concettuale – Funzione `vendite.trgfn_attivita_fatturabili_guard_fonte`

> 👀 **Vedi anche**
>
> **Approfondimento tabelle:**
>
> • [vendite.attivita_fatturabili](/dbzero/vendite/tabelle/attivita_fatturabili)  
> • [vendite.articolo_regole_fatturazione](/dbzero/vendite/tabelle/articolo_regole_fatturazione)  
>
---

### 🎯 Scopo Principale

(latest review 29-01-2026)  
La funzione **`vendite.trgfn_attivita_fatturabili_guard_fonte()`** verifica
la coerenza della **fonte quantita** e delle **competenze** per le righe di
`attivita_fatturabili`.

---

### ✅ Regole principali

* La regola di fatturazione per articolo deve esistere.
* La fonte quantita deve essere tra: `TIMESHEET`, `MANUALE`, `FISSA`.
* `competenza_mese` e` alternativa a `competenza_dal/competenza_al`.
* Se uno tra `competenza_dal`/`competenza_al` e` valorizzato, devono esserlo entrambi.
* `competenza_dal` deve essere ≤ `competenza_al` e includere `data_attivita`.

---

### ✅ Output

Nessun output (trigger BEFORE). In caso di incoerenza viene sollevato errore.

---

### 🧪 Esempio (caso non valido)

```sql
INSERT INTO vendite.attivita_fatturabili (
  articolo_id, istanza_utility_id, data_attivita, quantita,
  competenza_dal, competenza_al
)
VALUES (
  :articolo_id, :istanza_id, date '2026-01-10', 1,
  date '2026-02-01', date '2026-01-31'
);
```

---

{% include-markdown "signature-core.md" %}
