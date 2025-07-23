## 📘 Documentazione Concettuale – Trigger Function `anagrafiche.trgfn_indirizzi_dettaglio_ins_upd_norm_indirizzi_dettaglio()`

> 👀 **Vedi anche**   
>
> Approfondimento tabelle:    
> - [anagrafiche.indirizzi_dettaglio](/dbzero/anagrafiche/tabelle/indirizzi_dettaglio)   
>
> Approfondimento view:    
> - [script.vw_indirizzo_completo](/dbzero/script/view/vw_indirizzo_completo)    

La trigger function **`anagrafiche.trgfn_indirizzi_dettaglio_ins_upd_norm_indirizzi_dettaglio()`** normalizza i dati di indirizzo al momento di **INSERT** o **UPDATE** su **`anagrafiche.indirizzi_dettaglio`**, costruendo campi coerenti e uniformi per via, civico e indirizzo completo.

---

### 🎯 Scopo Principale

* **Uniformità dei dati**: garantire che i campi relativi all’indirizzo (`via_norm`, `civico_norm`, `indirizzo_normalizzato`) rispettino regole di maiuscole, spaziatura e formattazione.
* **Preparazione per ricerche e comparazioni**: offrire valori normalizzati che migliorano le performance di query basate su stringhe (es. ricerche full-text, join su via).
* **Affidabilità**: centralizzare la logica di normalizzazione nel database, evitando differenze tra applicazioni diverse.

---

### 🔍 Parametri e Contesto

* **Trigger**: `BEFORE INSERT OR UPDATE` sulla tabella `anagrafiche.indirizzi_dettaglio`.
* **Campi JOIN**: legge da `script.vw_indirizzo_completo` i campi `tipo_toponimo` e `nome_strada` tramite `id_stradario = NEW.stradario_id`.
* **Campi target**:

  * `via_norm`
  * `civico_norm`
  * `indirizzo_normalizzato`

---

### ⚙️ Flusso di Esecuzione Dettagliato

1. **Normalizzazione della via**

   * Recupera `tipo_toponimo` e `nome_strada` dalla view `script.vw_indirizzo_completo` (query con `INTO STRICT NEW.via_norm`).
   * Applica `TRIM` e `UPPER` alla concatenazione, rimuovendo spazi e uniformando il case.

2. **Normalizzazione del civico**

   * Se `NEW.civico` è valorizzato e diverso da 0, controlla `NEW.estensione_civico`:

     * Aggiunge `/` se mancante e concatena (es. “12/A”).
     * Converte il risultato in maiuscolo.
   * Se `civico` non è specificato, imposta `NEW.civico_norm := 'SNC'` (Senza Numero Civico).

3. **Costruzione dell’indirizzo completo**

   * Concatena `via_norm`, `civico_norm` e, se presenti, `palazzina`, `scala`, `piano`, `interno`, separati da virgola e label (es. “Pal.”, “Scala”).
   * Applica `TRIM` sul risultato per rimuovere spazi superflui.

4. **Restituzione**

   * Ritorna `NEW` con i campi popolati, pronto per essere inserito o aggiornato.

---

### 💡 Vantaggi Operativi

* **Coerenza**: tutti gli indirizzi vengono salvati secondo uno stesso pattern, semplificando validazioni e confronti.
* **Efficienza**: la normalizzazione lato database riduce il carico applicativo e velocizza le query full-text.
* **Modularità**: modifiche al formato (es. aggiunta di nuovi componenti) sono centralizzate nella trigger function senza cambiare il codice applicativo.

---

> 🧠 **“Con `trgfn_indirizzi_dettaglio_ins_upd_norm_indirizzi_dettaglio`, Zero ERP assicura indirizzi coerenti e pronti per ogni esigenza di ricerca o reporting.”**