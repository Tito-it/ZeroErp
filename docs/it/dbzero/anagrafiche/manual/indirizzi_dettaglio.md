
## 📘 Documentazione Concettuale – Tabella `anagrafiche.indirizzi_dettaglio`

> 👀 **Vedi anche**  
> Approfondimento Tabelle:
>  - [config.stradario](/dbzero/config/tabelle/stradario)  
>  - [config.comuni](/dbzero/config/tabelle/comuni)  
>  - [config.province](/dbzero/config/tabelle/province)

La tabella **`anagrafiche.indirizzi_dettaglio`** contiene il dettaglio degli indirizzi civici, collegati a una specifica via (tramite `stradario_id`) e al relativo contesto geografico (comune, provincia, regione, stato). In essa sono memorizzati numeri civici, estensioni, palazzine, interni, piani, dati di geolocalizzazione e un campo di indirizzo normalizzato generato automaticamente.

---

### 🎯 Scopo Principale

* **Dettagliare lo stradario**  
  Associare a ciascuna via (memorizzata in `config.stradario`) le singole unità civiche (numeri civici, estensioni, palazzine, interni, piani), ottenendo così l’indirizzo completo e navigabile.  
* **Geolocalizzazione precisa**  
  Il campo `civic_geoloc` memorizza il punto geografico corrispondente al singolo civico, mentre `street_geoloc` rappresenta la posizione media della via. Questi dati consentono ricerche spaziali e visualizzazioni GIS a livello di civico.  
* **Indirizzo normalizzato**  
  Il campo calcolato `indirizzo_normalizzato` combina via, civico, palazzina, scala, piano e interno in un’unica stringa formattata in modo coerente, facilitando confronti testuali e ricerche full-text.

---

### 🔗 Collegamenti con Altre Tabelle

* **`config.stradario`**  
  - Il campo `stradario_id` (integer) fa riferimento alla chiave primaria di `config.stradario`.  
  - Vincolo referenziale:  
    - **ON UPDATE CASCADE** (se cambia l’ID della via, si propaga automaticamente)  
    - **ON DELETE RESTRICT** (non si può eliminare una via se esistono civici ad essa collegati).  
  - Attraverso `config.stradario`, si risale alla catena gerarchica:  
    1. **Comune** (via → comune)  
    2. **Provincia** (comune → provincia)  
    3. **Regione** (provincia → regione)  
    4. **Stato** (regione → stato)

* **Unicità del dettaglio civico**  
  - Il vincolo `uq_indirizzi_dettaglio_norm` su (`via_norm`, `civico_norm`, `interno`, `piano`, `palazzina`) garantisce che non esistano duplicati logici dello stesso indirizzo normalizzato.

---

### 💡 Vantaggi Operativi

* **Ricostruzione gerarchica completa**  
  Mediante `stradario_id`, è possibile risalire in modo automatico e veloce all’intera struttura geografica (via → comune → provincia → regione → stato) senza duplicare dati.  
* **Precisione nella geolocalizzazione**  
  I campi `civic_geoloc` e `street_geoloc` permettono di visualizzare sia la posizione esatta di un civico sia la posizione media della via su mappe e applicazioni GIS.  
* **Ricerche full-text e uniformità**  
  Il campo `indirizzo_normalizzato` consente di effettuare ricerche testuali uniformi, confrontando stringhe già normalizzate (indipendenti da differenze di formattazione manuale).  
* **Gestione completa delle varianti civiche**  
  Grazie a `estensione_civico`, `palazzina`, `interno` e `scala`, si coprono tutte le possibili varianti di civico (lettere, palazzine multiple, suddivisioni e piani), senza necessità di alterare lo schema.  
* **Integrità e prevenzione duplicati**  
  Il vincolo di unicità `uq_indirizzi_dettaglio_norm` evita la creazione di due record con lo stesso indirizzo normalizzato, mantenendo coerenza e pulizia dei dati.

---

> 🧠 **“Una tabella di dettaglio civico che unisce normalizzazione testuale, geolocalizzazione puntuale e collegamenti gerarchici: il fulcro del sistema di indirizzamento completo in Zero ERP.”**  
