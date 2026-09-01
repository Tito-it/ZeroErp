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

⚠️ **Precisazione del 2026-09-01, e serve perché due cose si chiamano «anno».**
Questa funzione risponde a *«che anno è il documento»*, e la risposta è sempre
l'anno solare della sua data. ⛔ **Non decide l'anno del SECCHIO** del contatore:
quello lo sceglie `vendite.fn_get_next_progressivo` leggendo la `reset_policy`
del registro, e sotto `NESSUNA` vale `0`.

⭐ **Per questo la funzione non è stata toccata** quando `reset_policy` è
diventata vera: ha **quattro** chiamanti — `fn_assegna_numero_documento`,
`fn_assign_numero_fattura`, `fn_get_next_progressivo`,
`fn_get_or_create_commessa` — e cambiarle la firma li avrebbe toccati tutti per
un motivo che non li riguarda.

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
