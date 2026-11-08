## 📘 Documentazione Concettuale – Tabella `config.stati_flussi_pratiche`

> 👀 **Vedi anche**
>
Approfondimento tabelle:
>
[pratiche.flussi](/dbzero/pratiche/tabelle/flussi)

---
### 🎯 Scopo Principale
La tabella `config.stati_flussi_pratiche` definisce i possibili **stati di un flusso operativo** all'interno di una pratica. Ogni flusso ha esattamente uno stato che ne indica l'avanzamento nel workflow.

---

### Ruolo nel processo

* Governa il ciclo di vita dei flussi: dalla creazione al completamento.
* Il cambio stato viene registrato nel **giornale** con azione `FLUSSO_STATO_CAMBIATO`.
* Al raggiungimento dello stato `COMPLETATO`, se il flusso ha regole di generazione `auto = true`, viene attivata la **generazione cross-pratica** (trigger DB-5).

---

### Valori previsti (seed DB-6)

| codice_interno | Descrizione |
|----------------|-------------|
| `DA_ESEGUIRE` | Flusso creato, in attesa di avvio |
| `IN_CORSO` | Flusso in esecuzione |
| `COMPLETATO` | Flusso terminato (esito registrato) |
| `SOSPESO` | Flusso temporaneamente bloccato |
| `ANNULLATO` | Flusso annullato |
| `ERRORE` | Flusso in errore (handler fallito) |

---

### Convenzioni

* Pattern config standard: `codice`, `codice_interno` locked, `attivo`, `meta`, audit.
* Trigger standard applicati automaticamente dai runner del framework di automazione (`dbops.fn_run_automations_<tipo>`).

---

{% include-markdown "signature-core.md" %}
