# 📘 Documentazione Concettuale – Tabella `storico.comuni`

>  👀 **Vedi anche** 

> Approfondimento Tabelle:  
> - [config.comuni](/dbzero/config/tabelle/comuni)    


La tabella **`storico.comuni`** conserva la cronologia delle modifiche ai comuni presenti in `config.comuni`, garantendo la tracciabilità di inserimenti, aggiornamenti e cancellazioni.

---

## 🎯 Scopo Principale

* **Archiviazione storica**
  Riproduce lo schema di `config.comuni` per mantenere la storia completa di ogni record quando il flag `storicizza` è impostato a **true**.
* **Allineamento con modifiche di struttura**
  Ogni volta che in `config.comuni` viene aggiunta una colonna (es. `provincia_id` nel changelog Liquibase), la stessa modifica viene replicata in `storico.comuni`, assicurando che le due tabelle rimangano coerenti.
* **Trigger automatico**
  La funzione trigger `trgfn_comuni_upd_dlt_storico_comuni` si attiva su operazioni di update o delete in `config.comuni`, trasferendo i dati aggiornati nel record storico.
* **Storicizzazione**
  Il campo `storicizza` se true attiva il trigger per la storicizzazione delle informazioni sulla tabella `storico.comuni`. Il front-end dovrà sempre impostare a true il valore, solo per funzioni administrator si potrà non gestire a true.

---

## 🔄 Meccanismo di Popolamento

* **Replica della struttura**
  `storico.comuni` presenta le stesse colonne di `config.comuni` (inclusi i nuovi campi come `provincia_id`), più i campi di date di validità (se previsti) per tracciare il periodo di efficacia.
* **Trigger di storicizzazione**

  * Il trigger `trgfn_comuni_upd_dlt_storico_comuni` è configurato per attivarsi **before update** e **before delete** su `config.comuni`.
  * Quando un record in `config.comuni` viene modificato o cancellato e il suo flag `storicizza` è **true**, il trigger inserisce un nuovo record in `storico.comuni` con i valori precedenti, inclusi riferimento a `provincia_id`, `stato_id`, `extra_country` e altri campi.
  * Data di inizio validità (`valid_from`) impostata di default al giorno corrente.
  * Stato storico (`A`, `S`, `F`, `D`) per indicare se la via è attiva, soppressa, fusa o divisa.

* **Tag Liquibase per sincronizzazione schema**

  * Ogni cambiamento di schema applicato a `config.comuni` (es. l’aggiunta di `provincia_id`) deve essere replicato su `storico.comuni` tramite un changeSet Liquibase simile a quello mostrato, utilizzando `addColumn`, `createIndex` e `addForeignKeyConstraint` per mantenere la consistenza.

---

## 💡 Vantaggi Operativi

* **Tracciabilità completa**
  Permette di ricostruire l’evoluzione amministrativa dei comuni, analizzando modifiche, abilitazioni/disabilitazioni e variazioni di gerarchie territoriali.
* **Coerenza di schema**
  Poiché ogni modifica a `config.comuni` viene propagata a `storico.comuni` (inclusi nuovi campi come `provincia_id`), i report storici rimangono affidabili senza disallineamenti.
* **Flessibilità di amministrazione**
  L’amministratore può gestire il flag `storicizza` per decidere se una modifica specifica vada preservata nello storico o meno, senza dover intervenire manualmente.

---

> 🧠 **"Uno storico fedele ai cambiamenti dei comuni, con schema sempre allineato e trigger dedicato per una tracciabilità automatica."**
