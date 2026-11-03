## 📘 Documentazione Concettuale – Tabella `storico.parameter_overrides`

> **Ultimo aggiornamento**: 3 novembre 2026
>
> 👀 **Vedi anche**
>
Approfondimento Tabelle:
>
[config.parameter_overrides](/dbzero/config/tabelle/parameter_overrides)
> [storico.parameters](/dbzero/storico/tabelle/parameters)
>
Approfondimento funzioni e trigger:
>
[script.trgfn_storico_generic](/dbzero/script/funzioni/trgfn_storico_generic)
> [dbops.trgfn_tx_id_managed](/dbzero/dbops/funzioni/trgfn_tx_id_managed)

---

La tabella **`storico.parameter_overrides`** memorizza gli snapshot delle modifiche operazioni (INSERT, UPDATE, DELETE) sulla tabella operativa `config.parameter_overrides`. Ogni riga rappresenta lo stato completo di un record di override in un preciso istante, sfruttando il campo JSONB per catturare dinamicamente l’intero contenuto.

---
### 🎯 Scopo Principale
* **Versionamento degli override**
  Catturare ogni modifica ai record di `config.parameter_overrides`, consentendo di risalire allo stato precedente o iniziale di un override.
* **Audit e compliance**
  Archivio immutabile di tutte le operazioni, con metadati di utente e timestamp, per garantire tracciabilità e analisi storiche.

---

### Collegamenti con Altre Tabelle

* **`config.parameter_overrides`**

  * `parameter_override_id` è FK verso `config.parameter_overrides(id)`.
  * **ON UPDATE CASCADE** / **ON DELETE SET NULL**: mantiene la coerenza se la tabella operativa cambia o viene eliminata.
* **Triggers**

  * `trg_parameter_overrides_ins_upd_gen_tx_id`: assegna `tx_id` automatico su INSERT/UPDATE tramite `dbops.trgfn_tx_id_managed()`.

---



### Vantaggi Operativi

* **Cattura automatica delle modifiche**
  Lo snapshot JSONB elimina la necessità di mantenere colonne di audit per ciascun campo modificato.
* **Evoluzione dello schema trasparente**
  Aggiunta o rimozione di colonne in `config.parameter_overrides` non richiede modifiche a `storico.parameter_overrides`.
* **Consistenza e performance**
  FK e indici BTree su `parameter_override_id` assicurano integrità referenziale e query efficienti.
* **Integrazione unificata**
  Utilizzo della stessa funzione generic per storicizzazione (`script.trgfn_storico_generic`) riduce la complessità e mantiene lo stesso pattern per tutte le entità.

---

> **“`storico.parameter_overrides` è l’unico punto di verità per tutte le variazioni sugli override di configurazione: snapshot JSONB, auditing completo e flessibilità di schema in un unico modello.”**
