## 📘 Documentazione Concettuale – Funzione `vendite.fn_get_registro_id`

> 👀 **Vedi anche**
>
> **Approfondimento tabelle:**
>
> • [config.tipi_doc_fiscale](/dbzero/config/tabelle/tipi_doc_fiscale)  
> • [vendite.tipi_doc_fiscale_registri](/dbzero/vendite/manual/tipi_doc_fiscale_registri)  
> • [vendite.registri_fatturazione](/dbzero/vendite/tabelle/registri_fatturazione)  
>
---

### 🎯 Scopo Principale

(latest review 27-01-2026)
La funzione **`vendite.fn_get_registro_id`** risolve il registro di fatturazione
in base al mapping **tipo documento → registro**.

---

### 🔍 Parametri di input

| Parametro | Tipo | Descrizione |
| --- | --- | --- |
| `p_tipo_doc_fiscale_id` | `config.tipi_doc_fiscale.id%TYPE` | Tipo documento fiscale. |

---

### ✅ Regola applicata

1. Se esiste un mapping in `vendite.tipi_doc_fiscale_registri` → usa il `registro_id`.
2. Se assente → errore bloccante.

---

### ✅ Note operative

* Funzione pensata per la numerazione e per i processi che richiedono il registro contabile.
* Evita fallback impliciti: il mapping deve essere configurato in modo esplicito.

---

{% include-markdown "signature-core.md" %}
