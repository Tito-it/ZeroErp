## 📘 Documentazione Concettuale – Tabella `config.stati`

>  👀 **Vedi anche** 

> Approfondimento Tabelle:  
>
[config.comuni](/dbzero/config/tabelle/comuni)  
> [config.stradario](/dbzero/config/tabelle/stradario)       
> [config.stradario_generale](/dbzero/config/tabelle/stradario_generale)  
> [config.toponomastica](/dbzero/config/tabelle/toponomastica)  


La tabella **`config.stati`** censisce gli stati (o paesi), fornendo codici ufficiali e metadata utili per la gestione geografica e fiscale all’interno di Zero ERP.

---
### 🎯 Scopo Principale
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

* **Catalogo dei comuni completo (`catalogo_comuni_completo`)** — dal 18-10-2026
  Lo stato dichiara se il suo elenco di comuni e CAP è completo. È la proprietà che decide la **forma di un indirizzo libero** in quello stato:

  * **acceso** (oggi l'Italia): comune e CAP si scelgono dall'elenco, e sono obbligatori;
  * **spento**: la forma estera, con la località obbligatoria e il codice postale facoltativo.

  Si **dichiara**, non si deduce dall'esistenza di qualche comune: un elenco caricato a metà (per esempio durante la conversione dei dati di un'azienda) renderebbe obbligatoria una scelta che non si può ancora fare. Quando l'elenco è completo il flag si accende; gli indirizzi già scritti nella forma estera restano validi finché qualcuno non li modifica. Il valore sta in `stati.csv`. Lo applica il guard [`anagrafiche.trgfn_indirizzi_guard_forma_libera`](/dbzero/anagrafiche/manual/trgfn_indirizzi_guard_forma_libera), e il form lo legge per scegliere quale variante mostrare.

* ⚠️ **`codice_iso2` non è univoco, e non deve esserlo**
  L'elenco viene dalla tabella ISTAT degli stati esteri, che tiene anche righe **storiche** dello stesso paese con codici catastali diversi (Armenia, Azerbaigian, Singapore). Per questo uno stato non si cerca mai con un `SELECT … WHERE codice_iso2 = …` che ne prende uno a caso, ma con [`script.fn_stato_id_da_iso2`](/dbzero/script/manual/fn_stato_id_da_iso2), che pretende **una** riga. Al 18-10-2026 molte righe non hanno ancora i codici ISO (due spazi): è un debito di catalogo noto.

---

### Vantaggi Operativi

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

> **"Un catalogo centralizzato degli stati con codici ISO, metadata fiscali e attributi personalizzati, essenziale per la gestione geografica e fiscale globale in Zero ERP."**
