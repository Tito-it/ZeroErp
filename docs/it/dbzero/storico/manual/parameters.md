## 📘 Documentazione Concettuale – Tabella `storico.parameters`

> 👀 **Vedi anche**
>
Approfondimento Tabelle:
>
[config.parameters](/dbzero/config/tabelle/parameters)
> [storico.parameter_overrides](/dbzero/storico/tabelle/parameter_overrides)
>
Approfondimento funzioni e trigger:
>
[script.trgfn_upd_dlt_storico_generic](/dbzero/script/funzioni/trgfn_upd_dlt_storico_generic)
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

  * `parameter_id` è FK verso `config.parameters(id)`.
  * **ON UPDATE CASCADE**, **ON DELETE SET NULL**: mantiene integrità referenziale e non perde lo snapshot in caso di cancellazione.
* **Triggers**

  * `trg_parameters_ins_upd_gen_tx_id`: assegna `tx_id` tramite `dbops.trgfn_tx_id_managed` su INSERT/UPDATE.

---


### Vantaggi Operativi

* **Snapshot automatici**
  Non serve gestire manualmente ogni colonna di audit: il JSONB cattura l’intero record.
* **Schema evolutivo**
  Nuove colonne in `config.parameters` non richiedono modifiche in `storico.parameters`.
* **Consistenza e performance**
  FK e indici su `parameter_id` garantiscono operazioni sicure e veloci.
* **Uniformità di processo**
  Usa la funzione `script.trgfn_upd_dlt_storico_generic` come per tutte le altre entità del progetto, semplificando la manutenzione.

---

> **“`storico.parameters` è la fonte unica per tracciare l’evoluzione dei parametri di sistema: snapshot JSON, auditing completo e integrazione con il modello di storicizzazione unificato di Zero ERP.”**
