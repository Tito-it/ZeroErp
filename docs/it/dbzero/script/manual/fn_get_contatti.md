## 📘 Documentazione Concettuale – Funzione `script.fn_get_contatti`

> **Ultimo aggiornamento**: 9 novembre 2026
>
> 👀 **Vedi anche**
>
Approfondimento tabelle:
>
[anagrafiche.soggetti](/dbzero/anagrafiche/tabelle/soggetti)
> [anagrafiche.soggetti_ruoli](/dbzero/anagrafiche/tabelle/soggetti_ruoli)
> [anagrafiche.contatti](/dbzero/anagrafiche/tabelle/contatti)
> [config.tipi_contatti](/dbzero/config/tabelle/tipi_contatti)
> [config.unita_organizzative](/dbzero/config/tabelle/unita_organizzative)
> [anagrafiche.istanze_utilities](/dbzero/anagrafiche/tabelle/istanze_utilities)
>
Approfondimento funzioni:
>
[anagrafiche.trgfn_contatti_set_default_contatto](/dbzero/anagrafiche/funzioni/trgfn_contatti_set_default_contatto)
>
[script.fn_log_and_raise_error](/dbzero/script/funzioni/fn_log_and_raise_error)

La funzione **`script.fn_get_contatti(p_soggetto_id UUID, p_soggetto_ruolo_id BIGINT DEFAULT NULL, p_istanza_utility_id BIGINT DEFAULT NULL, p_tipo_contatto_id INTEGER DEFAULT NULL, p_unita_organizzativa_id INTEGER DEFAULT NULL)`** restituisce **al più un contatto per ciascun `tipo_contatto_id`**, applicando una logica di priorità basata sul **contesto** (soggetto / ruolo / istanza) e privilegiando, a parità di priorità, i contatti marcati come **`is_default = TRUE`**.

È pensata come **punto di accesso generico** per il recupero dei contatti e come base per funzioni più specializzate (ad esempio `script.fn_get_contatto_default`).

---
### 🎯 Scopo Principale
(latest review 25-03-26)
* **Selezione univoca per tipo**
  Per ogni `tipo_contatto_id` vengono restituiti **al più** un record, che rappresenta il contatto “migliore” in base al contesto richiesto.

* **Gerarchia di contesti (priority)**
  I contatti vengono classificati secondo una gerarchia di priorità:

  1. **soggetto + ruolo + istanza**
  2. **soggetto + ruolo** (generico)
  3. **solo soggetto** (fallback generico sul soggetto)

  In questo modo, se esistono contatti specifici per ruolo/utility, vengono preferiti rispetto a quelli generici del soggetto.

* **Preferenza per i contatti default**
  A parità di `priority`, la funzione privilegia i contatti con **`is_default = TRUE`**, lasciando comunque la possibilità di avere contatti non di default per lo stesso tipo.

* **Validazione e logging centralizzato**
  `p_soggetto_id` è **obbligatorio**: se `NULL`, la funzione rifiuta la chiamata prima di leggere un dato, con il codice `E_CONTATTI_SOGGETTO_OBBLIGATORIO` (classe `DATO_ERRATO`, messaggio «Indicare il soggetto di cui leggere i contatti.»), sollevato da `script.fn_log_and_raise_error` col canale `parametro` = `p_soggetto_id`.

* **Base per funzioni specializzate**
  Il risultato di `fn_get_contatti` può essere ulteriormente filtrato (es. solo default, solo un `tipo_contatto_id` specifico) da altre funzioni, evitando di duplicare la logica di fallback in più punti.

---

### Parametri di Input

| Nome                  | Tipo     | Default | Obbligatorio | Descrizione                                                                                                                        |
| --------------------- | -------- | ------- | ------------ | ---------------------------------------------------------------------------------------------------------------------------------- |
| `p_soggetto_id`       | `UUID`   | —       | ✅ Sì         | Identificativo del soggetto. Se `NULL`, la chiamata è rifiutata con `E_CONTATTI_SOGGETTO_OBBLIGATORIO`.                           |
| `p_soggetto_ruolo_id` | `BIGINT` | `NULL`  | ❌ No         | Se valorizzato, consente di privilegiare/filtrare i contatti legati a uno specifico ruolo del soggetto.                            |
| `p_istanza_utility_id` | `BIGINT` | `NULL`  | ❌ No         | Se valorizzato, consente di privilegiare/filtrare i contatti associati a una determinata istanza utility.                         |
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
| `istanza_utility_id` | `BIGINT`  | Eventuale riferimento a una istanza utility (`anagrafiche.istanze_utilities.id`). Può essere `NULL`.                    |
| `nominativo`        | `VARCHAR` | Nominativo del contatto.                                                                                                |
| `email`             | `VARCHAR` | Indirizzo email.                                                                                                        |
| `telefono`          | `VARCHAR` | Numero di telefono fisso.                                                                                               |
| `cellulare`         | `VARCHAR` | Numero di cellulare.                                                                                                    |
| `pec`               | `VARCHAR` | Indirizzo PEC.                                                                                                          |
| `note`              | `TEXT`    | Note libere sul contatto.                                                                                               |
| `is_default`        | `BOOLEAN` | Indica se il contatto è marcato come default all’interno del proprio contesto.                                          |
| `default_context`   | `VARCHAR` | Contesto in cui il contatto è default (`'soggetto'`, `'ruolo'`, `'istanza'`).                                           |

Per ogni `tipo_contatto_id`, è restituita **al più una riga** (la “migliore” in base a contesto e default).

---

### Flusso Logico Interno

1. **Validazione di `p_soggetto_id`**
   Se `p_soggetto_id` è `NULL`, un `IF` prima della query invoca `script.fn_log_and_raise_error` con:

   * origine: `database`
   * funzione chiamante: `fn_get_contatti`
   * codice errore: `E_CONTATTI_SOGGETTO_OBBLIGATORIO`
   * contesto: la chiave `parametro` = `p_soggetto_id` (il canale che indica il dato mancante) e gli
     altri parametri ricevuti

   In questo modo tutte le chiamate errate vengono tracciate in modo uniforme.

2. **Costruzione dei candidati (`candidates`)**
   A partire da `anagrafiche.contatti`, sono selezionati i record che:

   * appartengono al soggetto (`c.soggetto_id = p_soggetto_id`)

   * rispettano i filtri di contesto:

     ```sql
     AND (c.soggetto_ruolo_id IS NULL OR c.soggetto_ruolo_id IS NOT DISTINCT FROM p_soggetto_ruolo_id)
     AND (c.istanza_utility_id IS NULL OR c.istanza_utility_id IS NOT DISTINCT FROM p_istanza_utility_id)
     AND (p_tipo_contatto_id IS NULL OR c.tipo_contatto_id  = p_tipo_contatto_id)
     AND (c.unita_organizzativa_id IS NULL OR c.unita_organizzativa_id IS NOT DISTINCT FROM p_unita_organizzativa_id)
     ```

   * viene calcolata una colonna `priority` secondo lo schema:

     ```sql
     CASE
       WHEN c.soggetto_ruolo_id IS NOT DISTINCT FROM p_soggetto_ruolo_id
        AND c.istanza_utility_id IS NOT DISTINCT FROM p_istanza_utility_id
        AND c.istanza_utility_id IS NOT NULL THEN 1                              -- ruolo + istanza
       WHEN c.soggetto_ruolo_id IS NOT DISTINCT FROM p_soggetto_ruolo_id
        AND c.istanza_utility_id IS NULL THEN 2                                  -- ruolo generico
       ELSE 3  -- solo soggetto
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
  p_istanza_utility_id => NULL,
  p_tipo_contatto_id  => NULL
);

-- 2) Contatti per un ruolo specifico (es. referente commerciale del soggetto)
SELECT *
FROM script.fn_get_contatti(
  p_soggetto_id       => '123e4567-e89b-12d3-a456-426614174000',
  p_soggetto_ruolo_id => 10,   -- id in anagrafiche.soggetti_ruoli
  p_istanza_utility_id => NULL,
  p_tipo_contatto_id  => NULL
);

-- 3) Contatto "migliore" per un certo tipo_contatto (es. AMM = Amministrazione)
SELECT *
FROM script.fn_get_contatti(
  p_soggetto_id       => '123e4567-e89b-12d3-a456-426614174000',
  p_soggetto_ruolo_id => NULL,
  p_istanza_utility_id => NULL,
  p_tipo_contatto_id  => 1     -- id di config.tipi_contatti
);
```

---

### Vantaggi Operativi

* **Centralizzazione della logica**: la selezione dei contatti segue regole chiare e riutilizzabili, evitando duplicazioni di `CASE WHEN` e join complesse nelle query applicative.
* **Chiarezza del contesto**: la colonna `default_context` permette di capire rapidamente se un contatto è default per soggetto, ruolo o istanza.
* **Estendibilità**: ulteriori funzioni (es. `script.fn_get_contatto_default`) possono basarsi su `fn_get_contatti`, limitandosi a filtrare ulteriormente i risultati.
* **Compatibilità evolutiva**: l’uso di una funzione dedicata permette di cambiare la strategia di priorità o di aggiungere nuovi contesti senza impattare direttamente le query applicative.

---

### Test

* `db/pgtap/dbops/test-presidi-codici-corpo-leggibile-v1.sql`, test 9 — la chiamata col soggetto
  `NULL` è rifiutata con `E_CONTATTI_SOGGETTO_OBBLIGATORIO`.

---

### Note di migrazione

* 2026-11-09 — il soggetto obbligatorio lo è davvero. Prima la funzione era scritta in SQL e la
  validazione di `p_soggetto_id` stava in un passo della query che nessuno leggeva, quindi non girava:
  con il soggetto `NULL` la funzione restituiva zero righe in silenzio. Il codice era
  `ERRORE_PARAMETRI`, obsoleto dal 2026-08-05, e la rinomina dei codici non l'aveva visto perché i
  presidi sui codici leggevano il solo PL/pgSQL. Ora la funzione è PL/pgSQL, rifiuta il soggetto
  `NULL` con `E_CONTATTI_SOGGETTO_OBBLIGATORIO`, e con un soggetto valido restituisce le stesse righe
  di prima; firma, colonne restituite e permessi non cambiano (`20261110-99`,
  `brief-db-revisione-dbops`, giro 12).

---

{% include-markdown "signature-core.md" %}
