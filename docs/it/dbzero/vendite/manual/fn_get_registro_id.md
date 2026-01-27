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
in base al mapping **tipo documento → registro**, considerando utility/emittente se presenti.

---

### 🔍 Parametri di input

| Parametro | Tipo | Descrizione |
| --- | --- | --- |
| `p_tipo_doc_fiscale_id` | `config.tipi_doc_fiscale.id%TYPE` | Tipo documento fiscale. |
| `p_utility_id` | `config.utilities.id%TYPE` | Utility di riferimento (opzionale). |
| `p_emittente_soggetto_ruolo_id` | `anagrafiche.soggetti_ruoli.id%TYPE` | Emittente fiscale (opzionale). |

---

### ✅ Regola applicata

1. tipo_doc + utility + emittente
2. tipo_doc + utility
3. tipo_doc + emittente
4. tipo_doc (generico)
5. Se assente → errore bloccante.

---

### ✅ Note operative

* Funzione pensata per la numerazione e per i processi che richiedono il registro contabile.
* Le varianti sono gestite tramite registri con utility/emittente valorizzati.

---

{% include-markdown "signature-core.md" %}
