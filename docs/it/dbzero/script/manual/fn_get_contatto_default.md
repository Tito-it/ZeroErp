## 📘 Documentazione Concettuale – Funzione `script.fn_get_contatto_default`

> **Ultimo aggiornamento**: 9 novembre 2026
>
> 👀 **Vedi anche**
>
**Approfondimento tabelle:**  
>
• [anagrafiche.soggetti](/dbzero/anagrafiche/tabelle/soggetti)   
> • [anagrafiche.soggetti_ruoli](/dbzero/anagrafiche/tabelle/soggetti_ruoli)   
> • [anagrafiche.contatti](/dbzero/anagrafiche/tabelle/contatti)   
> • [config.tipi_contatti](/dbzero/config/tabelle/tipi_contatti)   
> • [config.unita_organizzative](/dbzero/config/tabelle/unita_organizzative)
> • [anagrafiche.istanze_utilities](/dbzero/anagrafiche/tabelle/istanze_utilities)
>
**Approfondimento funzioni:**
>
• [`script.fn_get_contatti`](/dbzero/script/funzioni/fn_get_contatti.md)  

---

### 🎯 Scopo principale
(latest review 25-03-26)
La funzione **`script.fn_get_contatto_default`** restituisce **il contatto “di default”** per un determinato **soggetto** e, opzionalmente, per un determinato:

* **ruolo** (`soggetto_ruolo`),
* **utility** (es. specifica fornitura/servizio),
* **tipo di contatto** (categoria opzionale).
* **unita organizzativa** (reparto/ufficio).

La funzione **riutilizza la logica di `script.fn_get_contatti`** per costruire l’elenco di contatti candidati e applica una selezione che garantisce al massimo **un solo record** come contatto di default, secondo priorità ben definite.

È pensata come **entry point semplificato** per tutti i casi in cui l’applicativo o la logica di dominio hanno bisogno di *“un solo contatto principale”* per un certo contesto.

---

### Firma

```sql
CREATE OR REPLACE FUNCTION script.fn_get_contatto_default(
    p_soggetto_id       uuid,
    p_soggetto_ruolo_id bigint  DEFAULT NULL,
    p_istanza_utility_id bigint  DEFAULT NULL,
    p_tipo_contatto_id  integer DEFAULT NULL,
    p_unita_organizzativa_id integer DEFAULT NULL
)
RETURNS TABLE (
    id               bigint,
    tipo_contatto_id integer,
    soggetto_id      uuid,
    soggetto_ruolo_id bigint,
    istanza_utility_id bigint,
    nominativo       varchar,
    email            varchar,
    telefono         varchar,
    cellulare        varchar,
    pec              varchar,
    note             text,
    is_default       boolean,
    default_context  varchar
)
LANGUAGE sql;
```

---

### Parametri di input

| Nome                  | Tipo      | Obbl. | Descrizione                                                                                                          |
| --------------------- | --------- | :---: | -------------------------------------------------------------------------------------------------------------------- |
| `p_soggetto_id`       | `uuid`    |  Sì   | Identificativo del soggetto in `anagrafiche.soggetti`. È il **pivot principale** di ricerca. Se `NULL`, la chiamata è rifiutata da `fn_get_contatti` con `E_CONTATTI_SOGGETTO_OBBLIGATORIO`. |
| `p_soggetto_ruolo_id` | `bigint`  |  No   | Se valorizzato, restringe la ricerca ai contatti legati a **quello specifico ruolo** (`anagrafiche.soggetti_ruoli`). |
| `p_istanza_utility_id` | `bigint` |  No   | Se valorizzato, filtra per una specifica **istanza utility** (`anagrafiche.istanze_utilities`).                      |
| `p_tipo_contatto_id`  | `integer` |  No   | Se valorizzato, limita ai contatti di un certo **tipo** (FK a `config.tipi_contatti`).                               |
| `p_unita_organizzativa_id` | `integer` | No | Se valorizzato, restringe ai contatti del reparto/ufficio (`config.unita_organizzative`). |

> ℹ️ Tutti i parametri opzionali vengono passati “as-is” a `script.fn_get_contatti`, che incapsula la logica di filtro dettagliata.

---

### Valori restituiti

La funzione restituisce **0 o 1 record** con la stessa struttura di `fn_get_contatti`, ma solo per il contatto considerato *default* nel contesto richiesto.

| Colonna             | Tipo      | Descrizione                                                                                            |
| ------------------- | --------- | ------------------------------------------------------------------------------------------------------ |
| `id`                | `bigint`  | ID del contatto (`anagrafiche.contatti.id`).                                                           |
| `tipo_contatto_id`  | `integer` | Tipo di contatto (FK `config.tipi_contatti.id`).                                                       |
| `soggetto_id`       | `uuid`    | Soggetto di riferimento (`anagrafiche.soggetti.id`).                                                   |
| `soggetto_ruolo_id` | `bigint`  | Ruolo specifico del soggetto, se presente.                                                             |
| `istanza_utility_id` | `bigint` | Istanza utility collegata a questo contatto (`anagrafiche.istanze_utilities.id`). Può essere `NULL`.   |
| `nominativo`        | `varchar` | Nominativo del contatto (persona fisica o label funzionale).                                           |
| `email`             | `varchar` | Email principale.                                                                                      |
| `telefono`          | `varchar` | Numero di telefono fisso.                                                                              |
| `cellulare`         | `varchar` | Numero di cellulare.                                                                                   |
| `pec`               | `varchar` | Indirizzo PEC, se presente.                                                                            |
| `note`              | `text`    | Note libere associabili al contatto.                                                                   |
| `is_default`        | `boolean` | Flag che indica se il contatto è marcato come default nel suo contesto.                                |
| `default_context`   | `varchar` | Eventuale contesto di default (es. “fatturazione”, “tecnico”, ecc.), determinato da `fn_get_contatti`. |

Se non esistono contatti che rispettano i criteri impostati **o nessuno è marcato come `is_default = TRUE`**, la funzione restituisce **zero righe**.

---

### Logica interna

La funzione è implementata come **wrapper SQL** su `script.fn_get_contatti`.

Schema logico semplificato:

```sql
WITH all_candidates AS (
    SELECT *
    FROM script.fn_get_contatti(
        p_soggetto_id,
        p_soggetto_ruolo_id,
        p_istanza_utility_id,
        p_tipo_contatto_id,
        p_unita_organizzativa_id
    )
),
only_default AS (
    SELECT *,
           ROW_NUMBER() OVER (
               ORDER BY
                   CASE WHEN is_default THEN 0 ELSE 1 END,
                   id
           ) AS rn
    FROM all_candidates
    WHERE is_default = TRUE
)
SELECT ...
FROM only_default
WHERE rn = 1;
```

#### Passi principali

1. **Costruzione candidati (`all_candidates`)**

   * Chiama `script.fn_get_contatti(...)` con gli stessi parametri ricevuti.
   * Ottiene tutti i contatti compatibili con il contesto richiesto.

2. **Filtro `is_default` (`only_default`)**

   * Mantiene solo le righe con `is_default = TRUE`.
   * Applica una numerazione con `ROW_NUMBER()` per avere una **priorità deterministica**:

     * prima i record `is_default = TRUE` (CASE nel `ORDER BY`),
     * a parità, il contatto con `id` più basso.

3. **Selezione finale**

   * Restituisce **solo il record con `rn = 1`**, garantendo al massimo **un contatto default**.

> La scelta di usare `ROW_NUMBER()` consente di gestire eventuali **dati sporchi** (più contatti marcati default) senza generare errore, ma scegliendo comunque in modo deterministico.

---

### Dipendenze

**Funzioni:**

* `script.fn_get_contatti(...)` → fornisce l’elenco completo dei contatti candidati, con logica di:

  * filtro per soggetto / ruolo / utility / tipo contatto,
  * priorità dei contatti rispetto alle regole di dominio,
  * arricchimento di campi come `default_context`.

**Tabelle (indirettamente via `fn_get_contatti`):**

* `anagrafiche.soggetti`
* `anagrafiche.soggetti_ruoli`
* `anagrafiche.contatti`
* `config.tipi_contatti`
* `config.unita_organizzative`
* `anagrafiche.istanze_utilities`

---

### Esempi d’uso

#### 1) Contatto default generico per soggetto

```sql
SELECT *
FROM script.fn_get_contatto_default(
    p_soggetto_id => 'aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee'::uuid
);
```

Restituisce il **contatto marcato default** per il soggetto, indipendentemente da ruolo, utility o tipo contatto.

---

#### 2) Contatto default per ruolo specifico

```sql
SELECT *
FROM script.fn_get_contatto_default(
    p_soggetto_id       => 'aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee'::uuid,
    p_soggetto_ruolo_id => 12345
);
```

Utile ad esempio per ottenere il contatto default **del ruolo “Cliente”** o **“Fornitore”** associato allo stesso soggetto.

---

#### 3) Contatto default per utility e tipo contatto

```sql
SELECT *
FROM script.fn_get_contatto_default(
    p_soggetto_id      => 'aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee'::uuid,
    p_soggetto_ruolo_id => 12345,
    p_istanza_utility_id => 10,
    p_tipo_contatto_id  => 2   -- es. "Referente amministrativo"
);
```
  
Permette di recuperare, ad esempio, il **referente amministrativo predefinito** per una certa utility/fornitura.

---

### Best practice e note d’uso

* **Coerenza con `fn_get_contatti`:**

  * ogni modifica alla logica di priorità o filtraggio dei contatti dovrebbe avvenire **in `fn_get_contatti`**, lasciando `fn_get_contatto_default` come semplice wrapper.

* **Dati incoerenti (più default):**

  * se per un dato contesto più contatti risultano marcati `is_default = TRUE`, la funzione **non fallisce**, ma restituisce il contatto con `id` più basso;
  * è comunque consigliabile prevedere **controlli di coerenza** (pgTAP o vincoli applicativi) per garantire che **esista al massimo un default per contesto**.

* **Soggetto mancante:**

  * con `p_soggetto_id` `NULL` la funzione non restituisce zero righe: riceve da
    `script.fn_get_contatti` il rifiuto `E_CONTATTI_SOGGETTO_OBBLIGATORIO` (classe `DATO_ERRATO`,
    messaggio «Indicare il soggetto di cui leggere i contatti.», canale `parametro` = `p_soggetto_id`).

* **Assenza di default:**

  * se non esiste alcun contatto marcato default, la funzione restituisce **0 righe**;
  * lato applicativo, è bene prevedere fallback (es. scegliere fra i candidati non-default o segnalare configurazione incompleta).

* **Estendibilità:**

  * la colonna `default_context` permette di modellare in futuro contesti diversi di default (es. `"fatturazione"`, `"tecnico"`, `"commerciale"`) senza modificare la firma della funzione.

---

### Test

* `db/pgtap/dbops/test-presidi-codici-corpo-leggibile-v1.sql`, test 10 — la chiamata col soggetto
  `NULL` è rifiutata con `E_CONTATTI_SOGGETTO_OBBLIGATORIO`, come quella a `fn_get_contatti`.

---

### Note di migrazione

* 2026-11-09 — la funzione non cambia, ma col soggetto `NULL` riceve il rifiuto di
  `fn_get_contatti`, `E_CONTATTI_SOGGETTO_OBBLIGATORIO`. Prima la validazione di `fn_get_contatti`
  non girava, e anche questa funzione restituiva zero righe in silenzio (`20261110-99`,
  `brief-db-revisione-dbops`, giro 12).

---

{% include-markdown "signature-core.md" %}
