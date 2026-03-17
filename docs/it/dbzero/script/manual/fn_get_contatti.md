## 📘 Documentazione Concettuale – Funzione `script.fn_get_contatti`

> 👀 **Vedi anche**
>
Approfondimento tabelle:
>
[anagrafiche.soggetti](/dbzero/anagrafiche/tabelle/soggetti)
> [anagrafiche.soggetti_ruoli](/dbzero/anagrafiche/tabelle/soggetti_ruoli)
> [anagrafiche.contatti](/dbzero/anagrafiche/tabelle/contatti)
> [config.tipi_contatti](/dbzero/config/tabelle/tipi_contatti)
> [config.unita_organizzative](/dbzero/config/tabelle/unita_organizzative)
> [config.utilities](/dbzero/config/tabelle/utilities)
>
Approfondimento funzioni:
>
[anagrafiche.trgfn_contatti_set_default_contatto](/dbzero/anagrafiche/funzioni/trgfn_contatti_set_default_contatto)
>
[script.fn_log_and_raise_error](/dbzero/script/funzioni/fn_log_and_raise_error)

La funzione **`script.fn_get_contatti(p_soggetto_id UUID, p_soggetto_ruolo_id BIGINT DEFAULT NULL, p_utility_id INTEGER DEFAULT NULL, p_tipo_contatto_id INTEGER DEFAULT NULL, p_unita_organizzativa_id INTEGER DEFAULT NULL)`** restituisce **al più un contatto per ciascun `tipo_contatto_id`**, applicando una logica di priorità basata sul **contesto** (soggetto / ruolo / utility) e privilegiando, a parità di priorità, i contatti marcati come **`is_default = TRUE`**.

È pensata come **punto di accesso generico** per il recupero dei contatti e come base per funzioni più specializzate (ad esempio `script.fn_get_contatto_default`).

---

### 🎯 Scopo Principale
(latest review 03-12-25)
* **Selezione univoca per tipo**
  Per ogni `tipo_contatto_id` vengono restituiti **al più** un record, che rappresenta il contatto “migliore” in base al contesto richiesto.

* **Gerarchia di contesti (priority)**
  I contatti vengono classificati secondo una gerarchia di priorità:

  1. **soggetto + ruolo + utility**
  2. **soggetto + ruolo**
  3. **soggetto + utility**
  4. **solo soggetto** (fallback generico sul soggetto)

  In questo modo, se esistono contatti specifici per ruolo/utility, vengono preferiti rispetto a quelli generici del soggetto.

* **Preferenza per i contatti default**
  A parità di `priority`, la funzione privilegia i contatti con **`is_default = TRUE`**, lasciando comunque la possibilità di avere contatti non di default per lo stesso tipo.

* **Validazione e logging centralizzato**
  `p_soggetto_id` è **obbligatorio**: se `NULL`, la funzione demanda a `script.fn_log_and_raise_error` la registrazione dell’errore (`ERRORE_PARAMETRI`) e il lancio dell’eccezione.

* **Base per funzioni specializzate**
  Il risultato di `fn_get_contatti` può essere ulteriormente filtrato (es. solo default, solo un `tipo_contatto_id` specifico) da altre funzioni, evitando di duplicare la logica di fallback in più punti.

---

### Parametri di Input

| Nome                  | Tipo     | Default | Obbligatorio | Descrizione                                                                                                                        |
| --------------------- | -------- | ------- | ------------ | ---------------------------------------------------------------------------------------------------------------------------------- |
| `p_soggetto_id`       | `UUID`   | —       | ✅ Sì         | Identificativo del soggetto. Se `NULL`, viene generato un errore tramite `fn_log_and_raise_error`.                                 |
| `p_soggetto_ruolo_id` | `BIGINT` | `NULL`  | ❌ No         | Se valorizzato, consente di privilegiare/filtrare i contatti legati a uno specifico ruolo del soggetto.                            |
| `p_utility_id`        | `INT`    | `NULL`  | ❌ No         | Se valorizzato, consente di privilegiare/filtrare i contatti associati a una determinata utility/servizio.                         |
| `p_tipo_contatto_id`  | `INT`    | `NULL`  | ❌ No         | Se valorizzato, limita il risultato ai contatti di uno specifico `tipo_contatto`. |
| `p_unita_organizzativa_id` | `INT` | `NULL` | ❌ No | Se valorizzato, privilegia/filtra i contatti legati a una unita organizzativa specifica. |

---

### Valore di Ritorno

La funzione restituisce una **tabella** con le seguenti colonne:

| Colonna             | Tipo      | Descrizione                                                                                                             |
| ------------------- | --------- | ----------------------------------------------------------------------------------------------------------------------- |
| `id`                | `BIGINT`  | Identificativo del contatto in `anagrafiche.contatti`.                                                                  |
| `tipo_contatto_id`  | `INT`     | Riferimento a `config.tipi_contatti` (opzionale).                                                                       |
| `soggetto_id`       | `UUID`    | Riferimento al soggetto (`anagrafiche.soggetti.id`).                                                                    |
| `soggetto_ruolo_id` | `BIGINT`  | Eventuale riferimento al ruolo del soggetto (`anagrafiche.soggetti_ruoli.id`). Può essere `NULL` per contatti generici. |
| `utility_id`        | `INT`     | Eventuale riferimento a una utility/servizio (`config.utilities.id`). Può essere `NULL`.                                |
| `nominativo`        | `VARCHAR` | Nominativo del contatto.                                                                                                |
| `email`             | `VARCHAR` | Indirizzo email.                                                                                                        |
| `telefono`          | `VARCHAR` | Numero di telefono fisso.                                                                                               |
| `cellulare`         | `VARCHAR` | Numero di cellulare.                                                                                                    |
| `pec`               | `VARCHAR` | Indirizzo PEC.                                                                                                          |
| `note`              | `TEXT`    | Note libere sul contatto.                                                                                               |
| `is_default`        | `BOOLEAN` | Indica se il contatto è marcato come default all’interno del proprio contesto.                                          |
| `default_context`   | `VARCHAR` | Contesto in cui il contatto è default (`'soggetto'`, `'ruolo'`, `'utility'`).                                           |

Per ogni `tipo_contatto_id`, è restituita **al più una riga** (la “migliore” in base a contesto e default).

---

### Flusso Logico Interno

1. **Validazione di `p_soggetto_id`**
   Se `p_soggetto_id` è `NULL`, il CTE `validate` invoca `script.fn_log_and_raise_error` con:

   * origine: `database`
   * funzione chiamante: `fn_get_contatti`
   * codice errore: `ERRORE_PARAMETRI`
   * payload JSON dei parametri ricevuti

   In questo modo tutte le chiamate errate vengono tracciate in modo uniforme.

2. **Costruzione dei candidati (`candidates`)**
   A partire da `anagrafiche.contatti`, sono selezionati i record che:

   * appartengono al soggetto (`c.soggetto_id = p_soggetto_id`)

   * rispettano i filtri di contesto:

     ```sql
     AND (c.soggetto_ruolo_id IS NULL OR c.soggetto_ruolo_id IS NOT DISTINCT FROM p_soggetto_ruolo_id)
     AND (c.utility_id        IS NULL OR c.utility_id        IS NOT DISTINCT FROM p_utility_id)
     AND (p_tipo_contatto_id IS NULL OR c.tipo_contatto_id  = p_tipo_contatto_id)
     AND (c.unita_organizzativa_id IS NULL OR c.unita_organizzativa_id IS NOT DISTINCT FROM p_unita_organizzativa_id)
     ```

   * viene calcolata una colonna `priority` secondo lo schema:

     ```sql
     CASE
       WHEN c.soggetto_ruolo_id IS NOT DISTINCT FROM p_soggetto_ruolo_id
        AND c.utility_id        IS NOT DISTINCT FROM p_utility_id THEN 1  -- ruolo + utility
       WHEN c.soggetto_ruolo_id IS NOT DISTINCT FROM p_soggetto_ruolo_id THEN 2  -- solo ruolo
       WHEN c.utility_id        IS NOT DISTINCT FROM p_utility_id        THEN 3  -- solo utility
       ELSE 4  -- solo soggetto
     END AS priority
     ```

3. **Ranking per tipo di contatto (`ranked`)**
   Per ogni `tipo_contatto_id`, viene calcolato un ordinamento che combina:

   * `priority` (contesto più specifico → più importante)
   * preferenza per i contatti `is_default = TRUE`
   * `id` come tie-breaker stabile

   Esempio di `ORDER BY` utilizzato nella `ROW_NUMBER()`:

   ```sql
   ROW_NUMBER() OVER (
     PARTITION BY candidates.tipo_contatto_id
     ORDER BY
       candidates.priority,
       CASE
         WHEN p_unita_organizzativa_id IS NULL THEN 0
         WHEN candidates.unita_organizzativa_id IS NOT DISTINCT FROM p_unita_organizzativa_id THEN 0
         ELSE 1
       END,
       CASE WHEN candidates.is_default THEN 0 ELSE 1 END,
       candidates.id
   ) AS rn
   ```

4. **Selezione finale**
   La funzione restituisce solo le righe con `rn = 1`, ovvero **il miglior contatto per ciascun `tipo_contatto_id`** rispetto ai parametri indicati.

---

### Esempi di Utilizzo

```sql
-- 1) Tutti i contatti "migliori" per un soggetto
SELECT *
FROM script.fn_get_contatti(
  p_soggetto_id       => '123e4567-e89b-12d3-a456-426614174000',
  p_soggetto_ruolo_id => NULL,
  p_utility_id        => NULL,
  p_tipo_contatto_id  => NULL
);

-- 2) Contatti per un ruolo specifico (es. referente commerciale del soggetto)
SELECT *
FROM script.fn_get_contatti(
  p_soggetto_id       => '123e4567-e89b-12d3-a456-426614174000',
  p_soggetto_ruolo_id => 10,   -- id in anagrafiche.soggetti_ruoli
  p_utility_id        => NULL,
  p_tipo_contatto_id  => NULL
);

-- 3) Contatto "migliore" per un certo tipo_contatto (es. AMM = Amministrazione)
SELECT *
FROM script.fn_get_contatti(
  p_soggetto_id       => '123e4567-e89b-12d3-a456-426614174000',
  p_soggetto_ruolo_id => NULL,
  p_utility_id        => NULL,
  p_tipo_contatto_id  => 1     -- id di config.tipi_contatti
);
```

---

### Vantaggi Operativi

* **Centralizzazione della logica**: la selezione dei contatti segue regole chiare e riutilizzabili, evitando duplicazioni di `CASE WHEN` e join complesse nelle query applicative.
* **Chiarezza del contesto**: la colonna `default_context` permette di capire rapidamente se un contatto è default per soggetto, ruolo o utility.
* **Estendibilità**: ulteriori funzioni (es. `script.fn_get_contatto_default`) possono basarsi su `fn_get_contatti`, limitandosi a filtrare ulteriormente i risultati.
* **Compatibilità evolutiva**: l’uso di una funzione dedicata permette di cambiare la strategia di priorità o di aggiungere nuovi contesti senza impattare direttamente le query applicative.

---

{% include-markdown "signature-core.md" %}
