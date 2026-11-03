## 📘 Documentazione Concettuale – Tabella `storico.dati_societari`

> **Ultimo aggiornamento**: 3 novembre 2026
>
> 👀 **Vedi anche**
>
Approfondimento Tabelle:
>
[anagrafiche.dati_societari](/dbzero/anagrafiche/tabelle/dati_societari)
>
Approfondimento funzioni e trigger:
>
[anagrafiche.trgfn_dati_societari_guard_tipo_soggetto](/dbzero/anagrafiche/funzioni/trgfn_dati_societari_guard_tipo_soggetto)
> [script.trgfn_storico_generic](/dbzero/script/funzioni/trgfn_storico_generic)
> [dbops.trgfn_tx_id_managed](/dbzero/dbops/funzioni/trgfn_tx_id_managed)

---

La tabella **`storico.dati_societari`** mantiene lo **storico** delle modifiche ai record di `anagrafiche.dati_societari`. Ogni riga rappresenta uno **snapshot JSONB** dello stato dei dati societari al momento di un’operazione (inserimento, aggiornamento o cancellazione), arricchito con metadati di validità e audit.

---
### 🎯 Scopo Principale
* **Versionamento completo**
  Acquisire snapshot di ogni record di `anagrafiche.dati_societari` per garantire la tracciabilità delle evoluzioni nel tempo.
* **Audit e compliance**
  Conservare informazioni su chi (`user_insert`) e quando (`data_insert`) è stata eseguita l’operazione, nonché su quale transazione di business (`tx_id`).
* **Intervalli di validità**
  Definire periodi di efficacia di ciascuno snapshot con `valid_from` (inclusivo) e `valid_to` (esclusivo), facilitando interrogazioni temporali.

---

### Collegamenti con Altre Tabelle

* **`anagrafiche.dati_societari`**

  * Il campo `dati_societari_id` è una FK verso la tabella operativa.
  * **ON UPDATE CASCADE**: propaga eventuali modifiche alla PK.
  * **ON DELETE SET NULL**: preserva lo snapshot in caso di cancellazione del record sorgente.
* **Triggers**

  * `trg_Z90_storico_dati_societari_upd_dlt` deve seguire la convenzione di naming per essere eseguito per ultimo.
  * Il trigger richiama `script.trgfn_storico_generic('dati_societari_id')`.

---

### Vantaggi Operativi

* **Recupero storico**
  Possibilità di ripristinare lo stato di un record societario a qualsiasi data antecedente.
* **Query temporali**
  Grazie a `valid_from`/`valid_to` è semplice creare viste di tipo Slowly Changing Dimension per BI e reporting.
* **Riduzione complessità**
  L’uso di JSONB elimina la necessità di colonne aggiuntive in tabella di storico quando cambia la struttura di `anagrafiche.dati_societari`.
* **Audit dettaglio**
  Tracciamento preciso dei dati e delle operazioni per finalità di compliance e debug.

---

> **“`storico.dati_societari` è il registro cronologico delle variazioni dei dati societari: snapshot JSON, audit completo e interrogazioni temporali in un’unica tabella.”**
