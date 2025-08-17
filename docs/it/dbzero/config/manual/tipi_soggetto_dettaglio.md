# 📚 Tabella `config.tipi_soggetto_dettaglio`

> 👀 **Vedi anche**
>
> Approfondimento Tabelle:   
>
> * [config.tipi_soggetto](/dbzero/config/tabelle/tipi_soggetto)      
> * [config.stati](/dbzero/config/tabelle/stati)      
> * [anagrafiche.soggetti](/dbzero/anagrafiche/tabelle/soggetti)  
---

La tabella **`config.tipi_soggetto_dettaglio`** definisce le **tipologie dettagliate** di soggetto (persone fisiche, giuridiche, enti, ecc.) in base al **paese** di appartenenza, specificando i **formati** validi per Codice Fiscale e Partita IVA.

---

### 🎯 Scopo Principale

* **Gestione Internazionale**
  Permette di adattare la validazione di CF/P.IVA alle regole di ciascuno Stato (`stato_iso2`).
* **Estendibilità**
  Il collegamento a `config.tipi_soggetto` garantisce macro-categorie estensibili (Fisico, Giuridico, Ente, …).
* **Controllo Applicativo**
  Centralizza il formato di CF/P.IVA, evitando logiche duplicate nel backend.

---

### 🔍 Collegamenti

* **FK →** `config.tipi_soggetto(tipo_soggetto_id)`
  Definisce la macro-tipologia.
* **FK →** `config.stati(codice_iso2)`
  Specifica il Paese di riferimento per il formato.
* **Estensione su** `anagrafiche.soggetti.tipo_soggetto_dettaglio_id`
  Associa ogni soggetto al dettaglio corretto, eliminata la colonna `tipo_soggetto`, è stato aggiunto in `anagrafiche.soggetti` la colonna `tipo_soggetto_dettaglio_id`.


---

### 💡 Vantaggi Operativi

* Evita hard‑coding dei formati di CF/P.IVA nel codice applicativo.
* Facilita l’aggiunta di nuovi paesi o categorie nominative.
* Garantisce coerenza tra DB e validazione backend.

---
