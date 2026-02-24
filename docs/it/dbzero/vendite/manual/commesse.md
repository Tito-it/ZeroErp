## 📘 Documentazione Concettuale – Tabella `vendite.commesse`

> 👀 **Vedi anche**
>
> **Approfondimento tabelle:**
>
> • [vendite.commesse_sorgenti](/dbzero/vendite/tabelle/commesse_sorgenti)  
> • [vendite.commesse_attivita](/dbzero/vendite/tabelle/commesse_attivita)  
>
---

### 🎯 Scopo Principale

La tabella `vendite.commesse` rappresenta la testata di governo del ciclo
`sorgente -> commessa -> attivita_fatturabili`.

Gestisce tipo commessa (`REALE`/`AUTO`), stato lifecycle, policy fatturazione e
contesto BA/utility/emittente.

---

### ✅ Regole principali

* `codice` univoco.
* `stato_commessa` con set canonico:
  * `BOZZA`
  * `APERTA`
  * `IN_ESECUZIONE`
  * `PRONTA_FATTURAZIONE`
  * `CHIUSA`
  * `ANNULLATA`
* `policy_fatturazione` ammessa:
  * `DA_DOCUMENTO`
  * `DA_CONSUNTIVO`
  * `MISTA`
* range `competenza_dal/al` coerente.

---

### 🧩 Utilizzo previsto

* ownership business del ciclo commessa;
* base per assegnazione root source (`commesse_sorgenti`);
* base per emissione snapshot su `attivita_fatturabili`.

---

{% include-markdown "signature-core.md" %}
