## 📘 Documentazione Concettuale – Tabella `storico.stradario`

>  👀 **Vedi anche** 
>
> Approfondimento Tabelle:  
> - [config.stradario](\dbzero\config\tabelle\stradario)    
>
> Approfondimenti funzioni:   
> - [config.trgfn_stradario_upd_dlt_storico_stradario](\dbzero\config\funzioni\trgfn_stradario_upd_dlt_storico_stradario)


La tabella **`storico.stradario`** archivia la cronologia delle modifiche alle vie presenti in `config.stradario`, consentendo di tracciare l’evoluzione degli indirizzi nel tempo.

---

### 🎯 Scopo Principale

* **Storico modifiche**
  Memorizza ogni cambiamento sulle vie (aggiunta, modifica, cancellazione) registrato in `config.stradario`, garantendo la tracciabilità storica.
* **Salvataggio descrizione originaria**
  Include il campo `descrizione_via`, che conserva il testo della via al momento dell’operazione, in modo da mantenere la consistenza storica anche a seguito di rinominazioni.
* **Controllo via flag di storicizzazione**
  Il trigger si attiva solo se il flag `storicizza` nella tabella principale è impostato a **true**, permettendo all’amministratore di scegliere se registrare o meno una determinata modifica.

---

### 🔄 Meccanismo di Popolamento

* **Trigger su `config.stradario`**
  Ogni volta che un record viene aggiornato o cancellato in `config.stradario`, e il flag `storicizza` è **true**, il trigger copia i valori principali nella tabella storica, includendo:

  * Collegamenti ai riferimenti originali (`stradario_id`, `stradario_generale_id`, `comune_id`, `codice_postale_id`).
  * La `descrizione_via` al momento della modifica.
  * Data di inizio validità (`valid_from`) impostata di default al giorno corrente.
  * Stato storico (`A`, `S`, `F`, `D`) per indicare se la via è attiva, soppressa, fusa o divisa.

---

### 💡 Vantaggi Operativi

* **Tracciabilità completa**
  Ogni modifica di indirizzo è immortalata con dettagli significativi, facilitando audit e report storici.
* **Flessibilità di amministrazione**
  L’interfaccia utente deve consentire di attivare/disattivare il flag `storicizza` a seconda delle necessità: l’amministratore può quindi eseguire modifiche senza registrare automaticamente ogni variazione, se desiderato.
* **Analisi storica e reporting**
  Filtri basati sul periodo di validità (`valid_from`, `valid_to`) e sullo stato consentono di ricostruire l’evoluzione di vie e indirizzi per ciascun comune.

---

> 🧠 **"Uno storico robusto delle vie comunali, che conserva la descrizione originale e permette un controllo granulare delle modifiche tramite flag di storicizzazione."**