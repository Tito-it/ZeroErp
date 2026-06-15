## 📘 Documentazione Concettuale – Tabella `pratiche.template_flussi_handler_eventi`

> 👀 **Vedi anche**
>
Approfondimento tabelle:
>
[pratiche.template_flussi](/dbzero/pratiche/tabelle/template_flussi)
> [pratiche.handler_flussi](/dbzero/pratiche/tabelle/handler_flussi)
> [pratiche.template_flussi_prerequisiti](/dbzero/pratiche/tabelle/template_flussi_prerequisiti)

---
### 🎯 Scopo Principale
La tabella `pratiche.template_flussi_handler_eventi` è il **legame data-driven** tra un template di flusso e gli **handler** da eseguire al verificarsi di un **evento** di flusso, **esito-aware**. Generalizza il dispatch handler oltre il solo avvio:

* `evento = 'IN_CORSO'` → **esecuzione automatica** dello step (oggi su [`template_flussi.handler_id`](/dbzero/pratiche/tabelle/template_flussi); vi confluirà in Fase 2 — vedi sotto).
* `evento = 'COMPLETATO'` → **azione di dominio al completamento**, condizionata all'esito (es. `vendita.accetta_preventivo` quando `APPROVAZIONE_CLIENTE` è COMPLETATO con esito `POSITIVO`).

L'esecutore resta un **handler Python** in `HANDLER_MAP` (riuso di [`handler_flussi`](/dbzero/pratiche/tabelle/handler_flussi)): nessun routing di dominio nel frontend, nessun catalogo parallelo.

---

### Ruolo nel processo

* Il dispatch (Django) legge i binding **per template ed evento**: su `IN_CORSO` esegue gli handler di esecuzione step; su `COMPLETATO` esegue gli handler di completamento i cui `esito_richiesto` combacia con l'esito effettivo (`NULL` = qualsiasi esito).
* Un template può avere **più azioni** sullo stesso evento (`sequenza` ne ordina l'esecuzione).
* "Il template **dichiara**, il motore **esegue per dati**": aggiungere una nuova famiglia (offerta, contratto, **ordini, commesse**) o un nuovo evento è **una riga seed**, mai un cambio di schema.

---

### Relazione con il frontend e con l'handler IN_CORSO

* L'azione di completamento è **server-side**: il FE chiama il completamento generico del flusso, il motore esegue il binding. Il FE resta presentazione pura (nessun `COMPLETION_REGISTRY`).
* È un concern **ortogonale** ad [`azioni_ui`](/dbzero/pratiche/tabelle/azioni_ui): `azioni_ui` lancia un drawer **interattivo** su azione dell'operatore; `template_flussi_handler_eventi` esegue automatismi **server-side** su evento di flusso.

---

### Colonne specifiche

| Colonna | Note |
|---------|------|
| `template_flusso_id` | FK → `template_flussi`. Il template a cui si applica il binding. |
| `evento` | VARCHAR(20) CHECK (IN_CORSO, COMPLETATO). Evento di flusso che innesca l'handler. |
| `esito_richiesto` | VARCHAR(20) nullable CHECK (POSITIVO, NEGATIVO, PARZIALE, NON_APPLICABILE). Esito richiesto perché l'handler scatti (rilevante su COMPLETATO). NULL = qualsiasi esito. Stesso vocabolario di `template_flussi_prerequisiti.esito_richiesto` / `chk_flussi_esito`. |
| `handler_id` | FK → `handler_flussi`. L'azione server-side (chiave risolta da HANDLER_MAP). |
| `handler_params` | JSONB DEFAULT '{}'. Parametri per questo binding (per-evento). |
| `sequenza` | INTEGER DEFAULT 0. Ordine se più azioni sullo stesso evento. |
| `attivo` | BOOLEAN DEFAULT true. Disattivazione del binding senza cancellarlo. |

---

### Vincoli

* **CHECK `chk_tfhe_evento`**: `evento` ∈ {IN_CORSO, COMPLETATO}.
* **CHECK `chk_tfhe_esito`**: `esito_richiesto` NULL o ∈ {POSITIVO, NEGATIVO, PARZIALE, NON_APPLICABILE}.
* **UNIQUE `uq_tfhe` (NULLS NOT DISTINCT)**: un solo binding per `(template_flusso_id, evento, esito_richiesto, handler_id)`; `esito_richiesto` NULL trattato come valore unico (no doppioni a esito non valorizzato).
* **FK `fk_tfhe_template_flusso`**: ON DELETE CASCADE (i binding seguono il template).
* **FK `fk_tfhe_handler`**: ON DELETE NO ACTION (non si elimina un handler in uso). Indice non creato (`dbops.fk_index_policy`, `consentito=false`); indice su `template_flusso_id` invece `consentito=true` (access path del dispatch).

---

### Seed corrente

| template | evento | esito | handler |
|---|---|---|---|
| 9003 (APPROVAZIONE_CLIENTE, PREVENTIVI_IMMEDIATA) | COMPLETATO | POSITIVO | `vendita.accetta_preventivo` |
| 9007 (APPROVAZIONE_CLIENTE, PREVENTIVI_DIFFERITA) | COMPLETATO | POSITIVO | `vendita.accetta_preventivo` |

Offerta/contratto/ordini/commesse entreranno come **nuove righe** quando nasceranno i loro flussi.

---

### Migrazione (Fase 1 → Fase 2)

* **Fase 1** (attuale): la tabella ospita **solo** i nuovi eventi (`COMPLETATO`+); `template_flussi.handler_id`/`handler_params` restano **autoritativi** per `IN_CORSO`. Eventi disgiunti → nessuna duplicazione, nessuna rottura del dispatch `CONFERMA`.
* **Fase 2** (futura, DB+BE): backfill di `handler_id`/`handler_params` come righe `evento='IN_CORSO'`; il dispatch BE legge **solo** questa tabella; drop delle colonne legacy su `template_flussi` → **modello unico**.

---

### Convenzioni

* Audit insert-only (`data_insert`, `user_insert`), come la sorella `template_flussi_prerequisiti`.
* Trigger standard applicati automaticamente da `dbops.fn_run_automations()`.

---

{% include-markdown "signature-core.md" %}
