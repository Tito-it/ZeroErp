## 📘 Documentazione Concettuale – Funzione `vendite.fn_get_anno_registro`

> 👀 **Vedi anche**
>
**Approfondimento tabelle:**
>
• [vendite.registri_fatturazione](/dbzero/vendite/tabelle/registri_fatturazione)   
> • [vendite.registri_fatturazione_progressivi](/dbzero/vendite/tabelle/registri_fatturazione_progressivi)   
> 
**Approfondimento funzioni:**
>
• [vendite.fn_get_next_progressivo](/dbzero/vendite/funzioni/fn_get_next_progressivo)   
>
### 🎯 Scopo Principale
(latest review 26-01-2026)
La funzione **`vendite.fn_get_anno_registro`** calcola l’anno di riferimento
per la numerazione dei registri con `reset_policy = ANNUALE`.

---

### Parametri di input

| Parametro | Tipo | Descrizione               |
| --------- | ---- | ------------------------- |
| `p_data`  | date | Data documento (fattura). |

---

### Regola applicata

* Usa l’**anno solare** della data documento.

---

### Note operative

* La funzione e` pensata per l’assegnazione progressivi in emissione.
* La numerazione va eseguita tramite `vendite.fn_get_next_progressivo`.

---

{% include-markdown "signature-core.md" %}
