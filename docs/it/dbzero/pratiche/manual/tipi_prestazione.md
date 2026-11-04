## 📘 Documentazione Concettuale – Tabella `pratiche.tipi_prestazione`

> 👀 **Vedi anche**
>
Approfondimento tabelle:
>
[pratiche.pratiche](/dbzero/pratiche/tabelle/pratiche)
> [pratiche.template_flussi](/dbzero/pratiche/tabelle/template_flussi)
> [pratiche.regole_generazione](/dbzero/pratiche/tabelle/regole_generazione)

---
### 🎯 Scopo Principale
La tabella `pratiche.tipi_prestazione` definisce il **catalogo dei tipi di pratica** gestibili dal sistema. Ogni pratica ha un `tipo_prestazione_id` che ne determina la natura e il workflow applicabile.

---

### Ruolo nel processo

* Definisce **quali pratiche** il sistema puo' gestire (es. "Sopralluogo", "Allacciamento", "Reclamo").
* Ogni tipo e' collegato a uno o piu' **template flussi** che definiscono gli step del workflow.
* Ogni tipo nasce con la sua **definizione workflow preset v1 PUBBLICATA**
  ([workflow_definizioni](workflow_definizioni.md), trigger di
  [bootstrap](trgfn_tipi_prestazione_bootstrap_definizione.md)): il tipo resta
  l'identita' condivisa (reporting), le edizioni ne versionano il workflow.
* Le **regole di generazione cross-pratica** fanno riferimento al tipo_prestazione come destinazione.
* Il campo `categoria` (VARCHAR(50), nullable) consente raggruppamenti liberi (es. "TECNICA", "COMMERCIALE", "AMMINISTRATIVA").

---

### Colonne specifiche

| Colonna | Note |
|---------|------|
| `categoria` | Raggruppamento libero (nullable). Non vincolato da CHECK — flessibilita' operativa. |
| `pre_attivazione` | BOOLEAN NOT NULL DEFAULT true. Se true, il tipo prestazione e' applicabile **prima** dell'attivazione del cliente (billing_account senza data_attivazione). |
| `post_attivazione` | BOOLEAN NOT NULL DEFAULT true. Se true, il tipo prestazione e' applicabile **dopo** l'attivazione del cliente (billing_account con data_attivazione valorizzata). |
| `storicizza` | Se true, le modifiche vengono tracciate in `storico.tipi_prestazione`. |
| `tx_id` | Identificativo transazione per correlazione cross-tabella. |

#### Matrice pre/post attivazione

| `pre_attivazione` | `post_attivazione` | Significato                                                        |
| ----------------- | ------------------ | ------------------------------------------------------------------ |
| true              | true               | Universale — applicabile sempre (default).                         |
| true              | false              | Solo pre-attivazione — esclusa dopo l'attivazione del cliente.     |
| false             | true               | Solo post-attivazione — richiede cliente attivato.                 |
| false             | false              | Interna — prestazione non vincolata al ciclo di vita del cliente.  |

La validazione avviene nel **service Django** (non nel DB) perche' richiede lookup cross-schema su `anagrafiche.billing_account`.

---

### Convenzioni

* Struttura config-like nel schema `pratiche`: `codice` UNIQUE, `codice_interno` UNIQUE + locked, `attivo`, `meta`, audit.
* Trigger standard applicati automaticamente dai runner del framework di automazione (`dbops.fn_run_automations_<tipo>`).

---

{% include-markdown "signature-core.md" %}
