## 📘 Documentazione Concettuale – Funzione `config.fn_get_stati_doc_fiscale`

> 👀 **Vedi anche**
>
> **Approfondimento tabelle:**
>
> • [config.stati_doc_fiscale](/dbzero/config/tabelle/stati_doc_fiscale)  
> • [config.stati_doc_fiscale_transizioni](/dbzero/config/tabelle/stati_doc_fiscale_transizioni)  
>
---

### 🎯 Scopo Principale

(latest review 24-01-2026)
La funzione **`config.fn_get_stati_doc_fiscale`** restituisce gli stati validi
per **LOTTO** o **FATTURA**, con eventuale filtro sulle **transizioni ammesse**.

---

### 🔍 Parametri di input

| Parametro   | Tipo   | Descrizione |
| ----------- | ------ | ----------- |
| `p_target`  | text   | `LOTTO` oppure `FATTURA`. |
| `p_from_id` | bigint | Stato corrente; se NULL ritorna tutti gli stati applicabili. |

---

### ✅ Note operative

* Usata per UI/servizi che devono mostrare gli stati selezionabili.
* Rispetta `applica_lotto` / `applica_fattura` e le transizioni definite.

---

{% include-markdown "signature-core.md" %}
