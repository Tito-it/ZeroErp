# 📘 Documentazione Concettuale – Tabella `config.stati`

>  👀 **Vedi anche** 

> Approfondimento Tabelle:  
> - [config.comuni](../comuni)  
> - [config.stradario](../stradario)       
> - [config.stradario_generale](../stradario_generale)  
> - [config.toponomastica](../toponomastica)  


La tabella **`config.stati`** censisce gli stati (o paesi), fornendo codici ufficiali e metadata utili per la gestione geografica e fiscale all’interno di Zero ERP.

---

## 🎯 Scopo Principale

* **Elenco degli stati/paesi**
  Contiene tutte le nazioni riconosciute, con sigle e codici ISO standard (ISO 3166-1 alpha-2 e alpha-3) e prefisso telefonico internazionale.

* **Codici ufficiali**

  * `sigla_stato`: sigla convenzionale (es. `IT`, `FR`, `DE`).
  * `codice_iso2` e `codice_iso3`: codici ISO 3166-1 per identificazioni univoche nei processi internazionali.

* **Campo `extra_country` (JSONB)**
  Permette di memorizzare informazioni specifiche del paese, estendendo il record con metadati personalizzati.

  * **Italia**: contiene `codice_istat` (utilizzato per statistiche Istat) e `codice_catastale` (necessario per la composizione del codice fiscale).
  * **Altri stati**: può ospitare attributi quali `regolamenti fiscali`, formati di tassazione, fasce climatiche, particolarità valutarie, ecc.

* **Supporto per continent i**
  Il campo `continente` classifica ogni stato nel corrispondente continente (Europa, Asia, Africa, America, Oceania), utile per raggruppamenti e reportistica geografica.

---

## 💡 Vantaggi Operativi

* **Unicità e interoperabilità**
  L’uso di codici ISO2 e ISO3 standard assicura che tutti i riferimenti geografici siano consistenti e compatibili con sistemi esterni (es. servizi di geolocalizzazione, normative fiscali).

* **Flessibilità tramite `extra_country`**
  Grazie al JSONB, ogni stato può avere dettagli personalizzati:

  * In Italia, il codice catastale è essenziale per calcolare correttamente il codice fiscale dei residenti.
  * Per altri paesi potrebbe esserci un campo `vat_format` (formato delle Partite IVA), `tax_rate` (aliquota fiscale standard), `address_format` (formato degli indirizzi), ecc.

* **Strutturazione gerarchica dei dati geografici**
  La tabella `config.stati` è alla base della gerarchia geografica:

  * Viene utilizzata da `config.toponomastica` per collegarsi allo stato di appartenenza della toponomastica.
  * Indirettamente, serve per `config.comuni`, `config.stradario_generale` e `config.stradario`, garantendo coerenza top-down nella gestione degli indirizzi.

* **Audit e tracciabilità**
  Trigger di auditing aggiornano i campi `data_update` e `user_update` automaticamente, mantenendo lo storico delle modifiche ai dati di definitizione dello stato.

---

> 🧠 **"Un catalogo centralizzato degli stati con codici ISO, metadata fiscali e attributi personalizzati, essenziale per la gestione geografica e fiscale globale in Zero ERP."**
