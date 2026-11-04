## 📘 Documentazione Concettuale – Tabella `config.priorita_pratiche`

> 👀 **Vedi anche**
>
Approfondimento tabelle:
>
[pratiche.pratiche](/dbzero/pratiche/tabelle/pratiche)

---
### 🎯 Scopo Principale
La tabella `config.priorita_pratiche` definisce i **livelli di priorita'** assegnabili alle pratiche. Ogni pratica ha una priorita' obbligatoria che ne influenza l'ordine di lavorazione.

---

### Ruolo nel processo

* Determina l'**ordine di lavorazione** delle pratiche nelle code di lavoro.
* Il cambio priorita' viene registrato nel **giornale** con azione `PRIORITA_CAMBIATA`.
* Il campo `sequenza` (INTEGER NOT NULL) definisce l'ordine numerico: valori piu' bassi = priorita' piu' alta in lista.

---

### Valori previsti (seed DB-6)

| codice_interno | sequenza | Descrizione |
|----------------|----------|-------------|
| `BASSA` | 10 | Priorita' bassa |
| `NORMALE` | 20 | Priorita' standard |
| `ALTA` | 30 | Priorita' elevata |
| `URGENTE` | 40 | Priorita' massima |

---

### Colonne specifiche

* **`sequenza`** (INTEGER NOT NULL): ordinamento numerico per le code di lavoro. Non presente nelle altre tabelle config standard.

---

### Convenzioni

* Pattern config standard + colonna `sequenza`.
* Trigger standard applicati automaticamente dai runner del framework di automazione (`dbops.fn_run_automations_<tipo>`).

---

{% include-markdown "signature-core.md" %}
