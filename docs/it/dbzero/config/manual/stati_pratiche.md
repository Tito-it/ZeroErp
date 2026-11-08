## 📘 Documentazione Concettuale – Tabella `config.stati_pratiche`

> 👀 **Vedi anche**
>
Approfondimento tabelle:
>
[pratiche.pratiche](/dbzero/pratiche/tabelle/pratiche)

---
### 🎯 Scopo Principale
La tabella `config.stati_pratiche` definisce i possibili **stati del ciclo di vita** di una pratica. Ogni pratica ha esattamente uno stato, che ne governa le transizioni e le operazioni consentite.

---

### Ruolo nel processo

* Governa le **transizioni di stato** delle pratiche (es. BOZZA → APERTA → CHIUSA).
* Il cambio stato viene registrato nel **giornale** (`pratiche.giornale`) con azione `STATO_CAMBIATO`.
* Le regole di transizione ammesse saranno implementate in DB-5 (guard/trigger).

---

### Valori previsti (seed DB-6)

| codice_interno | Descrizione |
|----------------|-------------|
| `BOZZA` | Pratica in preparazione |
| `APERTA` | Pratica operativa |
| `SOSPESA` | Pratica temporaneamente bloccata |
| `CHIUSA` | Pratica completata |
| `ANNULLATA` | Pratica annullata |

---

### Convenzioni

* Segue il pattern config standard: `codice` UNIQUE, `codice_interno` UNIQUE + locked, `attivo`, `meta`.
* I trigger standard (audit, lock `codice_interno`, protezione `attivo`) sono applicati automaticamente dai runner del framework di automazione (`dbops.fn_run_automations_<tipo>`).

---

{% include-markdown "signature-core.md" %}
