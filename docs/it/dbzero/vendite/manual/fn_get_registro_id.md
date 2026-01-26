## 📘 Documentazione Concettuale – Funzione `vendite.fn_get_registro_id`

> 👀 **Vedi anche**
>
> **Approfondimento tabelle:**
>
> • [config.sorgenti](/dbzero/config/tabelle/sorgenti)  
> • [config.utilities](/dbzero/config/tabelle/utilities)  
> • [vendite.registri_fatturazione](/dbzero/vendite/tabelle/registri_fatturazione)  
>
---

### 🎯 Scopo Principale

(latest review 24-01-2026)
La funzione **`vendite.fn_get_registro_id`** risolve il registro di fatturazione
secondo una regola deterministica: **sorgente → utility → errore**.

---

### 🔍 Parametri di input

| Parametro | Tipo | Descrizione |
| --- | --- | --- |
| `p_sorgente_tipo_id` | `config.sorgenti.id%TYPE` | Sorgente di origine (opzionale). |
| `p_utility_id` | `config.utilities.id%TYPE` | Utility di riferimento (opzionale). |

---

### ✅ Regola applicata

1. Se `config.sorgenti.registro_id` e` valorizzato → usa quello.
2. Altrimenti usa `config.utilities.registro_id`.
3. Se ancora NULL → errore bloccante.

---

### ✅ Note operative

* Funzione pensata per l’alimentazione di `attivita_fatturabili`.
* Garantisce coerenza del registro senza regole implicite.

---

{% include-markdown "signature-core.md" %}
