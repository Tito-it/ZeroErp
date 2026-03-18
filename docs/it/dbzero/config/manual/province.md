## 📘 Documentazione Concettuale – Tabella `config.province`

>  👀 **Vedi anche** 

> Approfondimento Tabelle:  
>
[config.stati](/dbzero/config/tabelle/stati)      
> [config.regioni](/dbzero/config/tabelle/regioni) 


La tabella **`config.province`** censisce le province all’interno di uno stato, fornendo informazioni amministrative, codici ISTAT e dati specifici per il calcolo di accise.

---
### 🎯 Scopo Principale
* **Elenco delle province**
  Contiene tutte le province di uno stato (es. in Italia: RM, MI, FI), con sigla e nome descrittivo.

* **Associazione con la regione**
  Il campo `regione_id` collega ogni provincia alla propria regione di appartenenza, garantendo coerenza nella gerarchia geografica.

* **Campo `extra_country` (JSONB)**
  Permette di memorizzare metadati aggiuntivi, il cui contenuto può variare a seconda dello stato:

  * **Italia**: include `codice_istat` (identificativo ISTAT della provincia) e, se previsto, `provincia_accisa_id` per indicare la provincia di riferimento nel calcolo delle accise.
  * **Altri paesi**: può ospitare informazioni analoghe (es. codici statistici locali, dati fiscali specifici, fasce territoriali esenzioni, ecc.).

---

### Vantaggi Operativi

* **Gerarchia geografica coerente**
  Integrando `config.province` con `config.regioni` e `config.stati`, si ottiene una struttura top-down di stati→regioni→province, fondamentale per reportistica territoriale e logistica.

* **Supporto alle accise**
  Il campo `provincia_accisa_id` (presente in `extra_country` per l’Italia) indica quale provincia funge da riferimento per le imposte sulle accise in un’intera regione, semplificando i calcoli fiscali.

* **Flessibilità e adattabilità**
  Grazie a `extra_country` in formato JSONB, è possibile estendere le informazioni di ogni provincia senza modificare lo schema fisico:

  * Esempi: `tax_code_format`, `regional_zone`, `economic_indicator`, ecc.

* **Audit e tracciabilità**
  I trigger associati aggiornano automaticamente `data_update` e `user_update`, garantendo la storia completa delle modifiche dei record.

---

> **"Un elenco strutturato di province, con metadati ISTAT e informazioni fiscali, alla base della gerarchia geografica e dei calcoli di accise in Zero ERP."**
