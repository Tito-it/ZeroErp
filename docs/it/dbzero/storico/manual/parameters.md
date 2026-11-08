## 📘 Documentazione Concettuale – Tabella `storico.parameters`

> **Ultimo aggiornamento**: 3 novembre 2026
>
> 👀 **Vedi anche**
>
Approfondimento Tabelle:
>
[config.parameters](/dbzero/config/tabelle/parameters)
> [storico.parameter_overrides](/dbzero/storico/tabelle/parameter_overrides)
>
Approfondimento funzioni e trigger:
>
[script.trgfn_storico_generic](/dbzero/script/funzioni/trgfn_storico_generic)
> [dbops.trgfn_tx_id_managed](/dbzero/dbops/funzioni/trgfn_tx_id_managed)

---

La tabella **`storico.parameters`** conserva gli **snapshot** delle modifiche sulla tabella operativa `config.parameters`. Ogni record storico è un JSONB che cattura lo stato completo del parametro, con informazioni di validità e metadati di audit.

---
### 🎯 Scopo Principale
* **Versionamento dei parametri**
  Registrare ogni modifica (INSERT, UPDATE, DELETE) sui parametri definiti in `config.parameters`, abilitando rollback e analisi storica.
* **Audit e compliance**
  Documentare chi (`user_insert`) e quando (`data_insert`) hanno effettuato le modifiche, mantenendo un registro immutabile.

---

### Collegamenti con Altre Tabelle

* **`config.parameters`**

  * `parameters_id` è l'id di `config.parameters`: una FK **logica**, senza
    vincolo (le FK dello schema `storico` le ha tolte `20250827-02`, così uno
    snapshot sopravvive alla cancellazione della madre).
  * ⚠️ Il nome è quello che l'automazione passa al trigger di storico
    (`<tabella>_id`). Fino al 2026-09-25 un database ricostruito da zero aveva
    `parameter_id`, e ogni UPDATE/DELETE di un parametro storicizzato moriva:
    rinominata da `20260925-26`.
* **Triggers**

  * `trg_parameters_ins_upd_gen_tx_id`: assegna `tx_id` tramite `dbops.trgfn_tx_id_managed` su INSERT/UPDATE.

---


### Vantaggi Operativi

* **Snapshot automatici**
  Non serve gestire manualmente ogni colonna di audit: il JSONB cattura l’intero record.
* **Schema evolutivo**
  Nuove colonne in `config.parameters` non richiedono modifiche in `storico.parameters`.
* **Consistenza e performance**
  L'indice su `parameters_id` rende veloce la chiusura dello snapshot aperto.
* **Uniformità di processo**
  Usa la funzione `script.trgfn_storico_generic` come per tutte le altre entità del progetto, semplificando la manutenzione.

---

> **“`storico.parameters` è la fonte unica per tracciare l’evoluzione dei parametri di sistema: snapshot JSON, auditing completo e integrazione con il modello di storicizzazione unificato di Zero ERP.”**
