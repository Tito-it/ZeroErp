## 📘 Documentazione Concettuale – Funzione `script.fn_get_stradario`


> 👀 **Vedi anche**

> Approfondimenti tabelle:  
>
[config.stradario](/dbzero/config/tabelle/stradario)   
>  [config.stradario_generale](/dbzero/config/tabelle/stradario_generale)   
>  [config.toponomastica](/dbzero/config/tabelle/toponomastica)   
>  [config.comuni](/dbzero/config/tabelle/comuni)   
>  [config.province](/dbzero/config/tabelle/province)    
>  [config.codici_postali](/dbzero/config/tabelle/codici_postali)    
>  [config.stati](/dbzero/config/tabelle/stati)   



La funzione **`script.fn_get_stradario(p_comune_id integer DEFAULT NULL, p_indirizzo text DEFAULT '') RETURNS TABLE(...)`** fornisce un metodo centralizzato per la ricerca e il recupero di voci dello stradario, sia a livello di comune specifico che su tutto lo stradario generale.

---
### 🎯 Scopo Principale
* **Ricerca locale per comune**
  Se viene specificato `p_comune_id`, esegue una query filtrata sul comune indicato, restituendo tutte le vie e toponomastiche che contengono la stringa `p_indirizzo` nel loro nome.

* **Ricerca globale**
  Se `p_comune_id` è `NULL`, effettua una ricerca libera su tutto lo stradario generale, restituendo toponomastica e vie corrispondenti a `p_indirizzo`, senza vincoli geografici.

* **Unificazione del risultato**
  In entrambi i casi restituisce un insieme di colonne standard che descrivono in dettaglio la via, il comune, la provincia, lo stato, il codice postale e la descrizione completa.

---

⭐ Con il comune restituisce solo le vie **vive**: una via soppressa (`obsoleto_dal` valorizzata,
fusa in un'altra) non si propone più. Il ramo senza comune legge solo le vie generali.

---

### Parametri di Input


   * `p_comune_id`(integer) ID del comune (`config.comuni.id`) su cui limitare la ricerca; `NULL`       per ricerca globale.

   * `p_indirizzo` (text) Stringa di ricerca da confrontare (case-insensitive) con \`toponomastica.
     descrizione stradario\_generale.descrizione\`.

---

### Logica di Esecuzione

1. **Ricerca filtrata (se `p_comune_id` non è `NULL`)**

   * Joins tra `config.stradario`, `config.stradario_generale`, `config.toponomastica`, `config.comuni`, `config.province`, `config.codici_postali`, `config.stati`.
   * Filtro su `s.comune_id = p_comune_id` e ILIKE su concatenazione di toponomastica e via.
   * Ordinamento per `stradario_generale.descrizione`.

2. **Ricerca libera (se `p_comune_id` è `NULL`)**

   * Query su `config.stradario_generale` e `config.toponomastica` (join a `config.stati`).
   * Nessun riferimento a comuni, province o postali; campi geografici impostati a valori null o vuoti.
   * Ordinamento per `stradario_generale.descrizione`.

---

### Colonne di Output

La funzione restituisce le colonne seguenti in entrambe le modalità di ricerca:

* `stradario_id` (integer): ID della riga in `config.stradario` (o `NULL` per ricerca globale).
* `via_id` (integer): ID in `config.stradario_generale`.
* `toponomastica_id` (integer): ID in `config.toponomastica`.
* `descrizione_toponomastica` (varchar): testo della toponomastica.
* `sigla_stato` (varchar): sigla dello stato di appartenenza.
* `descrizione_via` (varchar): nome esteso della via.
* `descrizione_breve` (varchar): versioni abbreviate o codificate.
* `cod_postale` (char): codice postale (o stringa vuota in ricerca globale).
* `comune` (varchar): nome del comune (o vuoto).
* `provincia` (char): sigla della provincia (o vuoto).
* `geoloc` (geometry): coordinate spaziali del civico o via (o `NULL`).
* `descrizione_completa` (text): concatenazione di toponomastica e via per rapida fruizione.

---

### Vantaggi Operativi

* **Centralizzazione**
  Un’unica funzione PL/pgSQL per gestire ricerche su stradario, evitando duplicazione di query in applicazione.

* **Flessibilità**
  Supporta sia ricerche localizzate per comune sia ricerche generali, semplicemente impostando `p_comune_id`.

* **Consistenza dei dati**
  Garantisce output uniforme, con stesse colonne e formattazione, a prescindere dal contesto di ricerca.

* **Semplicità di manutenzione**
  Modifiche alla logica di join o ai campi restituiti possono essere centralmente aggiornate in un solo punto.

---

> **“Fornire un’interfaccia unica e parametrizzata per le operazioni di ricerca stradale, migliorando coesione, manutenibilità e uniformità dei risultati.”**
