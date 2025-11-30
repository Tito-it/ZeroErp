##  Documentazione Concettuale – Vista `anagrafiche.vw_indirizzi_dettaglio`

> 👀 **Vedi anche**
>
> Approfondimenti tabelle:   
>
> * [anagrafiche.indirizzi_dettaglio](/dbzero/anagrafiche/tabelle/indirizzi_dettaglio)   
> * [anagrafiche.indirizzi](/dbzero/anagrafiche/tabelle/indirizzi)   
>
> Approfondimenti funzioni:   
>
> * [anagrafiche.fn_search_indirizzi_dettaglio](/dbzero/anagrafiche/funzioni/fn_search_indirizzi_dettaglio)   

---

### 🎯 Scopo Principale

La vista **`anagrafiche.vw_indirizzi_dettaglio`** fornisce una rappresentazione "comoda" e già arricchita degli indirizzi di dettaglio, a partire dalla tabella sorgente [`anagrafiche.indirizzi_dettaglio`](/dbzero/anagrafiche/tabelle/indirizzi_dettaglio) collegata allo stradario [`config.stradario`](/dbzero/config/tabelle/stradario).

Gli obiettivi principali sono:

* Offrire un **punto unico di lettura** degli indirizzi normalizzati (via, civico, palazzina, scala, piano, interno, note).
* Esporre **informazioni minime di contesto geografico**, come il `comune_id` derivato da `config.stradario`.
* Servire come **base dati per funzioni di ricerca** (es. `anagrafiche.fn_search_indirizzi_dettaglio`) e per componenti UI (autocomplete indirizzo, lookup veloci).
* Ridurre la duplicazione di join ripetitivi su `indirizzi_dettaglio` + `stradario` all’interno del codice SQL applicativo.

La vista è **read‑only** dal punto di vista logico: qualsiasi DML sugli indirizzi deve essere effettuato sulle tabelle di origine.

---

###  Collegamenti principali

* **Tabelle sorgenti**:

  * [`anagrafiche.indirizzi_dettaglio`](/dbzero/anagrafiche/tabelle/indirizzi_dettaglio)
  * [`config.stradario`](/dbzero/config/tabelle/stradario)

* **Funzioni correlate**:

  * [`anagrafiche.fn_search_indirizzi_dettaglio`](/dbzero/anagrafiche/funzioni/fn_search_indirizzi_dettaglio) – funzione di ricerca parametrica che utilizza questa vista come sorgente dati.

* **Oggetti di supporto**:

  * Vincolo di univocità sugli indirizzi di dettaglio (unique index/constraint su combinazione di: `stradario_id`, `civico`, `estensione_civico`, `palazzina`, `scala`, `piano`, `interno`).

---

### 隣 Struttura logica della vista

La vista effettua un join diretto tra:

* `anagrafiche.indirizzi_dettaglio` (alias `idd`)
* `config.stradario` (alias `s`)

esponendo un set di colonne già pronte per ricerche e visualizzazioni.

### Campi esposti

| Colonna                  | Tipo                      | Provenienza                  | Descrizione                                                       |
| ------------------------ | ------------------------- | ---------------------------- | ----------------------------------------------------------------- |
| `indirizzo_dettaglio_id` | `bigint`                  | `idd.id`                     | Identificativo univoco dell’indirizzo di dettaglio.               |
| `stradario_id`           | `integer`                 | `idd.stradario_id`           | Riferimento allo stradario (`config.stradario`).                  |
| `comune_id`              | `integer`                 | `s.comune_id`                | Comune associato allo stradario.                                  |
| `indirizzo_normalizzato` | `text` (generated column) | `idd.indirizzo_normalizzato` | Stringa composta (via, civico, palazzina, scala, piano, interno). |
| `via_norm`               | `text`                    | `idd.via_norm`               | Via normalizzata.                                                 |
| `civico`                 | `integer`                 | `idd.civico`                 | Numero civico.                                                    |
| `estensione_civico`      | `varchar(10)`             | `idd.estensione_civico`      | Estensione civico (es. A, B, bis, ecc.).                          |
| `palazzina`              | `varchar(50)`             | `idd.palazzina`              | Palazzina o corpo di fabbrica.                                    |
| `scala`                  | `varchar(10)`             | `idd.scala`                  | Scala.                                                            |
| `piano`                  | `varchar(10)`             | `idd.piano`                  | Piano.                                                            |
| `interno`                | `varchar(10)`             | `idd.interno`                | Interno o unità.                                                  |
| `altro`                  | `text`                    | `idd.altro`                  | Note libere sull’indirizzo.                                       |
| `civic_geoloc`           | `geometry(Point,4326)`    | `idd.civic_geoloc`           | Geolocalizzazione puntuale del civico.                            |
| `street_geoloc`          | `geometry(Point,4326)`    | `idd.street_geoloc`          | Geolocalizzazione di via/strada.                                  |
| `attivo`                 | `boolean`                 | `idd.attivo`                 | Stato attivo/disattivo dell’indirizzo.                            |
| `storicizza`             | `boolean`                 | `idd.storicizza`             | Flag che abilita la storicizzazione.                              |
| `tx_id`                  | `uuid`                    | `idd.tx_id`                  | Identificativo di transazione logica.                             |
| `data_insert`            | `timestamptz`             | `idd.data_insert`            | Timestamp di inserimento.                                         |
| `user_insert`            | `text`                    | `idd.user_insert`            | Utente che ha effettuato l’inserimento.                           |
| `data_update`            | `timestamptz` #           |
---

###  Modalità d’uso tipiche

  * 1. Ricerca manuale per indirizzo normalizzato

  Utilizzo diretto della vista per ricerche veloci:

  ```sql
  SELECT
      indirizzo_dettaglio_id,
      indirizzo_normalizzato,
      comune_id
  FROM anagrafiche.vw_indirizzi_dettaglio
  WHERE UPPER(indirizzo_normalizzato) LIKE UPPER('%FALERIENSE EST%')
  ORDER BY indirizzo_normalizzato;
  ```

  * 2. Supporto a UI/autocomplete

  La vista è pensata per essere utilizzata da funzioni applicative (es. API REST) che implementano:

  * ricerca per pattern sull’indirizzo normalizzato;
  * limit/pagination;
  * eventuale filtro per `comune_id` o `stradario_id`.

  Esempio:

  ```sql
  SELECT *
  FROM anagrafiche.vw_indirizzi_dettaglio
  WHERE comune_id = :comune_id
    AND UPPER(indirizzo_normalizzato) LIKE UPPER('%' || :pattern || '%')
  ORDER BY indirizzo_normalizzato
  LIMIT 50;
  ```

  * 3. Integrazione con funzioni helper

  La vista è usata come **sorgente dati** dalla funzione:

  ```sql
  SELECT *
  FROM anagrafiche.fn_search_indirizzi_dettaglio(
      p_stradario_id   => :stradario_id,
      p_civico         => :civico,
      p_indirizzo_norm => :pattern,
      p_limit          => 50
  );
  ```

Questo approccio permette di centralizzare la logica di ricerca mantenendo la vista semplice e riutilizzabile.

---

### ✅ Best practice e raccomandazioni

* Utilizzare la vista **solo per SELECT**; qualsiasi operazione di aggiornamento o inserimento va effettuata sulle tabelle base.
* Per ricerche in contesti applicativi, preferire l’uso di **`fn_search_indirizzi_dettaglio`**, che:

  * applica filtri coerenti (es. `attivo = TRUE`),
  * gestisce parametri opzionali e pattern fuzzy,
  * limita il numero di record restituiti.
* La vista può essere estesa in futuro per includere ulteriori metadati (es. descrizioni di comune, provincia, stato) ma va mantenuta leggera e orientata alla ricerca.

---

{% include-markdown "signature-core.md" %}
