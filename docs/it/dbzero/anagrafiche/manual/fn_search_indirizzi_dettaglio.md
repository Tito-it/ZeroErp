#  Documentazione Funzione – `anagrafiche.fn_search_indirizzi_dettaglio`

> 👀 **Vedi anche**
>
> Approfondimenti tabelle:   
>
> * [anagrafiche.indirizzi_dettaglio](/dbzero/anagrafiche/tabelle/indirizzi_dettaglio)   
> * [anagrafiche.indirizzi](/dbzero/anagrafiche/tabelle/indirizzi)   
>
> Approfondimenti funzioni:   
>
> * [`anagrafiche.vw_indirizzi_dettaglio`](/dbzero/anagrafiche/views/vw_indirizzi_dettaglio)

> * Leggere in fondo la nota tecnica.
---

### 🎯 Scopo Principale
(latest review 28-11-25)
La funzione **`anagrafiche.fn_search_indirizzi_dettaglio`** fornisce un **punto unico di ingresso** per la ricerca degli indirizzi di dettaglio normalizzati, appoggiandosi alla vista:

* [`anagrafiche.vw_indirizzi_dettaglio`](/dbzero/anagrafiche/views/vw_indirizzi_dettaglio)

La funzione è progettata per coprire due casi d’uso principali:

1. **Ricerca per indirizzo “fisico”** a partire da `stradario_id` e dai dettagli del civico (civico, estensione, palazzina, scala, piano, interno).
2. **Ricerca fuzzy per indirizzo normalizzato**, usando un pattern case-insensitive su `indirizzo_normalizzato`.

In questo modo si centralizza la logica di ricerca, evitando duplicazioni nei vari punti dell’applicazione (UI, API, script di integrazione, test).

---

###  Collegamenti principali

* **Vista di base**:

  * [`anagrafiche.vw_indirizzi_dettaglio`](/dbzero/anagrafiche/views/vw_indirizzi_dettaglio)

* **Tabelle sottostanti**:

  * [`anagrafiche.indirizzi_dettaglio`](/dbzero/anagrafiche/tabelle/indirizzi_dettaglio)
  * [`config.stradario`](/dbzero/config/tabelle/stradario)

* **Oggetti di supporto**:

  * Vincolo di univocità sugli indirizzi di dettaglio (unique index/constraint su: `stradario_id`, `civico`, `estensione_civico`, `palazzina`, `scala`, `piano`, `interno`).

---

### 隣 Firma della funzione

```sql
CREATE OR REPLACE FUNCTION anagrafiche.fn_search_indirizzi_dettaglio(
    p_stradario_id       integer DEFAULT NULL,
    p_civico             integer DEFAULT NULL,
    p_estensione_civico  text    DEFAULT NULL,
    p_palazzina          text    DEFAULT NULL,
    p_scala              text    DEFAULT NULL,
    p_piano              text    DEFAULT NULL,
    p_interno            text    DEFAULT NULL,
    p_indirizzo_norm     text    DEFAULT NULL,
    p_limit              integer DEFAULT 50
)
RETURNS SETOF anagrafiche.vw_indirizzi_dettaglio
LANGUAGE plpgsql
STABLE
PARALLEL SAFE;
```

La funzione restituisce **righe della vista** `anagrafiche.vw_indirizzi_dettaglio`, quindi espone tutti i campi utili alla ricerca (chiave indirizzo, normalizzato, via, civico, dettagli, geolocalizzazione, audit, ecc.).

---

### 茶 Descrizione parametri

| Parametro             | Tipo    | Obbligatorio | Descrizione                                                                                  |
| --------------------- | ------- | ------------ | -------------------------------------------------------------------------------------------- |
| `p_stradario_id`      | integer | NO*          | Identificativo dello stradario (via) da usare per una ricerca precisa sull’indirizzo fisico. |
| `p_civico`            | integer | NO           | Numero civico; usato solo se `p_stradario_id` è valorizzato.                                 |
| `p_estensione_civico` | text    | NO           | Estensione civico (es. A, B, bis); usata solo con `p_stradario_id`.                          |
| `p_palazzina`         | text    | NO           | Palazzina o corpo di fabbrica; usata solo con `p_stradario_id`.                              |
| `p_scala`             | text    | NO           | Scala; usata solo con `p_stradario_id`.                                                      |
| `p_piano`             | text    | NO           | Piano; usato solo con `p_stradario_id`.                                                      |
| `p_interno`           | text    | NO           | Interno/unità; usato solo con `p_stradario_id`.                                              |
| `p_indirizzo_norm`    | text    | NO*          | Pattern fuzzy da cercare su `indirizzo_normalizzato` (case-insensitive).                     |
| `p_limit`             | integer | NO           | Limite massimo di righe restituite (default: 50).                                            |

> ⚠️ **Regola di validazione**: è obbligatorio valorizzare **almeno uno** tra:
>
> * `p_stradario_id`, oppure
> * `p_indirizzo_norm` (non vuoto).
>
> Se entrambi sono NULL / vuoti, la funzione solleva un `RAISE EXCEPTION` con messaggio esplicito.

---

###  Logica di funzionamento

  * 1. Normalizzazione del pattern

  Se `p_indirizzo_norm` è valorizzato, la funzione esegue:

  * `btrim(p_indirizzo_norm)` per rimuovere spazi in testa e coda;
  * `NULLIF(..., '')` per trasformare una stringa vuota in `NULL`.

  Il valore normalizzato viene memorizzato in una variabile locale `v_pattern` ed usato per le ricerche fuzzy con:

  ```sql
  UPPER(v.indirizzo_normalizzato) LIKE UPPER('%' || v_pattern || '%')
  ```

  * 2. Validazione dei criteri di ricerca

  Se **sia** `p_stradario_id` che `v_pattern` risultano `NULL`, la funzione interrompe l’esecuzione con:

  ```sql
  RAISE EXCEPTION
      'fn_search_indirizzi_dettaglio: valorizzare almeno p_stradario_id o p_indirizzo_norm (non vuoto)'
      USING HINT = 'Per ricerche fuzzy usare p_indirizzo_norm, per ricerche esatte usare p_stradario_id + dettagli civico.';
  ```

  In questo modo si evitano ricerche non intenzionali sull’intero dataset.

  * 3. Caso A – Ricerca per stradario (indirizzo fisico)

  Se `p_stradario_id` **è valorizzato**, la funzione:

  * interroga la vista `anagrafiche.vw_indirizzi_dettaglio` alias `v`;
  * filtra per `v.stradario_id = p_stradario_id`;
  * applica filtri opzionali sui dettagli civico:

  ```sql
  AND (p_civico IS NULL OR v.civico = p_civico)
  AND (p_estensione_civico IS NULL OR COALESCE(v.estensione_civico, '') = COALESCE(p_estensione_civico, ''))
  AND (p_palazzina IS NULL         OR COALESCE(v.palazzina,        '') = COALESCE(p_palazzina,        ''))
  AND (p_scala IS NULL             OR COALESCE(v.scala,            '') = COALESCE(p_scala,            ''))
  AND (p_piano IS NULL             OR COALESCE(v.piano,            '') = COALESCE(p_piano,            ''))
  AND (p_interno IS NULL           OR COALESCE(v.interno,          '') = COALESCE(p_interno,          ''))
  ```

  * se `v_pattern` è valorizzato, applica **anche** il filtro fuzzy sull’indirizzo normalizzato;
  * restituisce solo righe con `v.attivo = TRUE`;
  * ordina per `v.indirizzo_normalizzato`, `v.indirizzo_dettaglio_id`;
  * applica il limite `p_limit`.

  * 4. Caso B – Ricerca fuzzy per indirizzo normalizzato

  Se `p_stradario_id` è **NULL** ma `v_pattern` è valorizzato, la funzione:

  * interroga la vista `anagrafiche.vw_indirizzi_dettaglio` alias `v`;
  * filtra per `v.attivo = TRUE`;
  * applica la condizione fuzzy su `indirizzo_normalizzato`:

  ```sql
  UPPER(v.indirizzo_normalizzato) LIKE UPPER('%' || v_pattern || '%')
  ```

  * ordina per `v.indirizzo_normalizzato`, `v.indirizzo_dettaglio_id`;
  * applica il limite `p_limit`.

---

###  Esempi di utilizzo

  * Esempio 1 – Ricerca per stradario + civico

  Ricerca di un indirizzo a partire da un `stradario_id` noto e dal civico:

  ```sql
  SELECT *
  FROM anagrafiche.fn_search_indirizzi_dettaglio(
      p_stradario_id  => 1234,
      p_civico        => 10,
      p_limit         => 20
  );
  ```

  * Esempio 2 – Ricerca per stradario + dettagli completi

  Ricerca più specifica, con palazzina, scala, piano e interno:

  ```sql
  SELECT *
  FROM anagrafiche.fn_search_indirizzi_dettaglio(
      p_stradario_id      => 1234,
      p_civico            => 10,
      p_estensione_civico => 'A',
      p_palazzina         => 'B',
      p_scala             => '1',
      p_piano             => '2',
      p_interno           => '3'
  );
  ```

  * Esempio 3 – Ricerca fuzzy per indirizzo normalizzato

  Ricerca di tutti gli indirizzi che contengono la stringa "FALERIENSE EST":

  ```sql
  SELECT *
  FROM anagrafiche.fn_search_indirizzi_dettaglio(
      p_indirizzo_norm => 'FALERIENSE EST',
      p_limit          => 50
  );
  ```

  * Esempio 4 – Gestione dell’errore per parametri mancanti

  La chiamata seguente solleva un’eccezione perché non fornisce né `p_stradario_id` né `p_indirizzo_norm`:

  ```sql
  SELECT *
  FROM anagrafiche.fn_search_indirizzi_dettaglio();
  ```

  Messaggio atteso:

  > `fn_search_indirizzi_dettaglio: valorizzare almeno p_stradario_id o p_indirizzo_norm (non vuoto)`

---

### ✅ Best practice e raccomandazioni

* Utilizzare questa funzione come **entry point standard** per tutte le ricerche programmatiche sugli indirizzi di dettaglio (UI, API, batch).
* Evitare di replicare logica di filtro direttamente su `anagrafiche.indirizzi_dettaglio` salvo casi particolari; preferire la combinazione:

  * `fn_search_indirizzi_dettaglio` → `vw_indirizzi_dettaglio` → `indirizzi_dettaglio`.
* Tenere sotto controllo il valore di `p_limit` nelle chiamate da interfaccia (es. autocomplete), per evitare elenchi troppo lunghi.
* In caso di ricerche massive o scenari batch particolari, valutare l’uso della vista direttamente con filtri ad hoc.

---

Aggiornato 28-11-2026

 Nota tecnica – Ottimizzazione funzione fn_search_indirizzi_dettaglio


Durante i test pgTAP è emerso che, quando si dispone già di informazioni deterministiche sull’indirizzo (es. stradario_id, civico, ecc.), la presenza del parametro p_indirizzo_norm può generare ricerche non desiderate basate su LIKE.

È stata quindi introdotta una condizione mirata:

IF p_indirizzo_norm IS NOT NULL
   AND v_stradario_id IS NULL  THEN
    v_pattern := NULLIF(btrim(p_indirizzo_norm), '');
ELSE
    v_pattern := NULL;
END IF;

In questo modo:

Se l’indirizzo è identificabile tramite dati strutturati → ignorato il filtro fuzzy su p_indirizzo_norm.

Se invece viene fornita solo la stringa di ricerca (senza ID) → viene applicato il pattern di ricerca.

Questa soluzione risulta coerente con il modello Zero ERP, evita ambiguità e mantiene la funzione ottimizzata sia per uso applicativo che per operazioni di diagnostica/search.

---

{% include-markdown "signature-core.md" %}
