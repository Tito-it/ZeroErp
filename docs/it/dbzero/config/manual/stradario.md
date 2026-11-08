## 📘 Documentazione Concettuale – Tabella `config.stradario`

> **Ultimo aggiornamento**: 7 novembre 2026

>  👀 **Vedi anche** 
>
Approfondimento Tabelle:  
>
[config.comuni](/dbzero/config/tabelle/comuni)      
> [config.stradario_generale](/dbzero/config/tabelle/stradario_generale)   
> [config.codici_postali](/dbzero/config/tabelle/codici_postali)  
> [storico.stradario](/dbzero/storico/tabelle/stradario)
> 
La tabella **`config.stradario`** definisce la mappa delle vie e strade di ciascun comune, completando il processo di indirizzamento con informazioni di localizzazione e dettagli aggiuntivi.

---
### 🎯 Scopo Principale
(latest review 21-01-2026)
* **Mappa comunale delle vie**
  Contiene l’elenco delle strade e vie di ogni comune, con riferimento al prefisso e al nome forniti da `config.stradario_generale`.
* **Geolocalizzazione**
  Il campo `geoloc` (geometry Point, SRID 4326) consente di associare ogni via a coordinate geografiche per mappe e ricerche spaziali.
* **Associazione CAP**
  Collega ogni via a un codice postale obbligatorio (`codice_postale_id`), gestito nella tabella `config.codici_postali`.
* **Informazioni estese**
  Il campo `meta` (JSONB) permette di memorizzare dati aggiuntivi, come eventuali frazioni, indicazioni o note specifiche.
* **Storicizzazione**
  Il campo `storicizza` se true attiva il trigger per la storicizzazione delle informazioni sulla tabella `storico.stradario`. Il front-end dovrà sempre impostare a true il valore, solo per funzioni administrator si potrà non gestire a true.
  
---

### ⭐ La chiave delle vie vive

In un comune la stessa via generale con lo stesso codice postale c'è **una volta sola fra le vie
vive**: l'indice unico `uq_stradario_comune_stradario_gen_cp` vale solo per le righe senza
`obsoleto_dal`. Una via soppressa ne è fuori, e non collide con la via viva che ne ha preso il
posto. Chi cerca una via da quella terna (comune, via generale, CAP) la cerca fra le vie vive.

La chiave esterna `comune_id` ha il suo indice, `ix_config_stradario_comune_id`: quello unico,
parziale, non copre le vie soppresse.

---

### ⭐ La via soppressa

Quando due vie si fondono (`dbops.fn_admin_merge_stradario`), la via d'origine **resta**, con
`obsoleto_dal` valorizzata al giorno della fusione. Resta perché è la radice della catena delle
trasformazioni (`storico.stradario_trasformazioni`) e lo storico degli indirizzi la nomina ancora.
Ma da quel giorno:

* le ricerche delle vie (`script.fn_search_stradario`, `script.fn_get_stradario`) non la propongono;
* un indirizzo non vi nasce né vi si sposta: lo rifiuta il guard del ritiro su
  `anagrafiche.indirizzi_dettaglio` (`E_CATALOGO_OBSOLETO_NUOVA_ISTANZA`);
* non si fonde più (`E_STRADARIO_SOPPRESSO`);
* se si fondono due comuni, si sposta con le altre vie senza collidere.

La data la scrive solo la fusione, e non è mai oltre la data operativa: una soppressione è un fatto
avvenuto, non un ritiro programmato. Per lo stradario, quindi, «soppressa» vuol dire «data
valorizzata».

---

### Collegamenti con Altre Tabelle

* **`config.comuni`**
  Il campo `comune_id` identifica il comune di appartenenza, instaurando la relazione tra strade e territorio.
* **`config.stradario_generale`**
  Il campo `via_id` fa riferimento al catalogo neutro di prefissi e nomi delle vie.
* **`config.codici_postali`**
  `codice_postale_id` impone il CAP di competenza per ciascuna via.
* **`storico.stradario`**
  `storico` True attiva il trigger per il salvataggio delle informazioni.
---

### Vantaggi Operativi

* **Copertura completa del territorio**
  Permette di mappare ogni strada all’interno del comune, gestendo situazioni di vie duplicate con CAP diversi.
* **Supporto GIS**
  Grazie al campo di geometria, rende disponibili servizi di geocoding, routing e rappresentazione cartografica.
* **Flessibilità di estensione**
  Il JSONB `meta` consente di aggiungere attributi specifici (es. frazioni, note storiche) senza modificare lo schema.
* **Auditing e storicizzazione**
  Trigger automatici mantengono traccia di modifiche e cancellazioni, garantendo consistenza storica dei dati.

---

> **"Una vista dettagliata e georeferenziata delle strade comunali, con CAP obbligatorio e informazioni flessibili per ogni via."**

---

###  Diagramma ER relazioni 


```mermaid
%%{init: {'er': {'layoutDirection': 'TB'}}}%%
erDiagram
    comuni             ||--o{ stradario : has
    stradario_generale ||--o{ stradario : typed_as
    codici_postali     ||--o{ stradario : uses_cap

    comuni             { int id PK }
    stradario_generale { int id PK }
    codici_postali     { int id PK }
    stradario          { int id PK }

```

---

###  Diagramma ER attributi

```mermaid
%%{init: {'er': {'layoutDirection': 'TB'}}}%%
erDiagram
    stradario {
        int       id PK
        int       comune_id FK
        int       stradario_generale_id FK
        point4326 geoloc
        jsonb     meta
        datetime  data_insert
        varchar   user_insert
        datetime  data_update
        varchar   user_update
        int       codice_postale_id FK
        date      obsoleto_dal
        bool      storicizza
        uuid      tx_id
    }

```

---
{% include-markdown "signature-core.md" %}

---
