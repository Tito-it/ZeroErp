## 📘 Documentazione Concettuale – Tabella `pratiche.tipi_prestazione`

> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [pratiche.pratiche](/dbzero/pratiche/tabelle/pratiche)
> * [pratiche.template_flussi](/dbzero/pratiche/tabelle/template_flussi)
> * [pratiche.regole_generazione](/dbzero/pratiche/tabelle/regole_generazione)

---

### 🎯 Scopo Principale

La tabella `pratiche.tipi_prestazione` definisce il **catalogo dei tipi di pratica** gestibili dal sistema. Ogni pratica ha un `tipo_prestazione_id` che ne determina la natura e il workflow applicabile.

---

### 🧱 Ruolo nel processo

* Definisce **quali pratiche** il sistema puo' gestire (es. "Sopralluogo", "Allacciamento", "Reclamo").
* Ogni tipo e' collegato a uno o piu' **template flussi** che definiscono gli step del workflow.
* Le **regole di generazione cross-pratica** fanno riferimento al tipo_prestazione come destinazione.
* Il campo `categoria` (VARCHAR(50), nullable) consente raggruppamenti liberi (es. "TECNICA", "COMMERCIALE", "AMMINISTRATIVA").

---

### ⚙️ Colonne specifiche

| Colonna | Note |
|---------|------|
| `categoria` | Raggruppamento libero (nullable). Non vincolato da CHECK — flessibilita' operativa. |
| `storicizza` | Se true, le modifiche vengono tracciate in `storico.tipi_prestazione`. |
| `tx_id` | Identificativo transazione per correlazione cross-tabella. |

---

### ✅ Convenzioni

* Struttura config-like nel schema `pratiche`: `codice` UNIQUE, `codice_interno` UNIQUE + locked, `attivo`, `meta`, audit.
* Trigger standard applicati automaticamente da `dbops.fn_run_automations()`.

---

{% include-markdown "signature-core.md" %}
