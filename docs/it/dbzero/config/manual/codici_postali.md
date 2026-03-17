## 📚 Documentazione Concettuale – Tabella `config.codici_postali`

> 👀 **Vedi anche** 
>
Approfondimento Tabelle:  
>
[config.comuni](/dbzero/config/tabelle/comuni)      
> [config.stradario](/dbzero/config/tabelle/stradario)      
> [config.stradario_generale](/dbzero/config/tabelle/stradario_generale)  

La tabella **`config.codici_postali`** censisce i codici di avviamento postale (postal codes o ZIP codes) associati ai comuni, fornendo l’elenco completo di CAP per ogni città.

---

### 🎯 Scopo Principale

* **Elenco dei codici postali**
  Per ogni comune (city/municipality), memorizza tutti i codici postali (Postal Code o ZIP Code) validi per quell’area geografica.

* **Molti CAP per lo stesso comune**
  Un singolo comune può avere più codici postali (ad esempio diverse frazioni o quartieri). Il campo `comune_id` può quindi comparire in più record con CAP differenti.

* **Associazione con il sistema di strade**
  La relazione tra vie e codici postali avviene tramite la tabella **`config.stradario`**, che collega ogni `via_id` (da `config.stradario_generale`) al `codice_postale_id` corrispondente.

* **Terminologia internazionale**
  Il termine inglese utilizza “Postal Code” in generale, mentre negli Stati Uniti si parla specificamente di “ZIP Code”.

---

### Vantaggi Operativi

* **Copertura capillare del territorio**
  Gestisce più CAP per un solo comune, utile per suddividere zone interne come frazioni, quartieri o uffici postali specifici.

* **Precisione nell’indirizzamento**
  Tramite il collegamento con **`config.stradario`**, assicura che ogni via sia abbinata al CAP corretto, migliorando la consegna della corrispondenza e i servizi logistici.

* **Supporto multiregionale**
  Accoglie diversi formati di codici postali (Italia, USA, altri paesi), permettendo l’uso in contesti internazionali senza modifica del modello dati.

* **Audit e tracciabilità**
  Trigger di auditing aggiornano automaticamente `data_update` e `user_update`, garantendo la storia delle modifiche dei CAP.

---

> **"Una tabella essenziale per associare vie e comuni ai rispettivi codici postali, garantendo indirizzamento preciso e compatibilità internazionale."**
