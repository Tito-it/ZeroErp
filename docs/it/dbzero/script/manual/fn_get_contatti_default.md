## 📘 Documentazione Concettuale – Funzione `script.fn_get_contatto_default`

> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [anagrafiche.soggetti](/dbzero/anagrafiche/tabelle/soggetti)   
> * [anagrafiche.soggetti_ruoli](/dbzero/anagrafiche/tabelle/soggetti_ruoli)   
> * [anagrafiche.contatti](/dbzero/anagrafiche/tabelle/contatti)   
>
> Approfondimento funzioni:
>
> * [script.fn_get_contatti](/dbzero/script/funzioni/fn_get_contatti)   
> * [anagrafiche.trgfn_contatti_set_default_contatto](/dbzero/anagrafiche/funzioni/trgfn_contatti_set_default_contatto)   
> * [script.fn_log_and_raise_error](/dbzero/script/funzioni/fn_log_and_raise_error)   

La funzione **`script.fn_get_contatto_default(p_soggetto_id UUID, p_soggetto_ruolo_id BIGINT DEFAULT NULL, p_utility_id INTEGER DEFAULT NULL, p_tipo_contatto_id INTEGER DEFAULT NULL, p_unita_organizzativa_id INTEGER DEFAULT NULL)`** restituisce **il contatto di default** relativo al contesto richiesto (soggetto / ruolo / utility), riutilizzando la logica di selezione di `script.fn_get_contatti` e limitandosi ai soli record marcati come `is_default = TRUE`.

A differenza di `fn_get_contatti`, che può restituire **più righe (una per tipo_contatto)**, questa funzione restituisce **al massimo un solo contatto**:

* il contatto considerato di riferimento (default) per il soggetto / ruolo / utility (ed eventualmente tipo_contatto) indicati.

---

### 🎯 Scopo Principale

* **Ottenere il contatto “di riferimento”**
  Fornire un modo semplice e univoco per ottenere il **contatto principale** da utilizzare in un certo contesto (es. contatto predefinito del cliente, contatto principale del ruolo Gestore, ecc.).

* **Riutilizzare la logica di fallback**
  Non reinventa la logica di priorità, ma si appoggia a `script.fn_get_contatti`, che incapsula già le regole di selezione per soggetto/ruolo/utility.

* **Limitare ai soli contatti di default**
  Tra i contatti candidati, considera solo quelli con `is_default = TRUE` (coerenti con il contesto gestito dal trigger `trgfn_contatti_set_default_contatto`).

* **Evitare ambiguità applicative**
  Lato applicazione, evita di dover implementare logiche custom per scegliere “il” contatto giusto: la funzione restituisce 0 o 1 riga, semplificando l’uso in backend/API.

---

### 🧩 Parametri di Input

| Nome                  | Tipo     | Default | Obbligatorio | Descrizione                                                                                                                      |
| --------------------- | -------- | ------- | ------------ | -------------------------------------------------------------------------------------------------------------------------------- |
| `p_soggetto_id`       | `UUID`   | —       | ✅ Sì         | Identificativo del soggetto. Se `NULL`, la validazione è delegata internamente a `fn_get_contatti` / `fn_log_and_raise_error`.   |
| `p_soggetto_ruolo_id` | `BIGINT` | `NULL`  | ❌ No         | Se valorizzato, seleziona il contatto di default relativo a uno specifico ruolo del soggetto (es. ruolo Cliente, Gestore, ecc.). |
| `p_utility_id`        | `INT`    | `NULL`  | ❌ No         | Se valorizzato, specializza il contatto di default per una determinata utility (es. fornitura gas, luce, acqua...).              |
| `p_tipo_contatto_id`  | `INT`    | `NULL`  | ❌ No         | Se valorizzato, restringe il default ad uno specifico `tipo_contatto` (categoria).               |
| `p_unita_organizzativa_id` | `INT` | `NULL` | ❌ No | Se valorizzato, restringe il default al reparto/ufficio (`config.unita_organizzative`). |

> 💡 Se `p_tipo_contatto_id` è `NULL`, la funzione restituisce il **contatto di default principale** per il contesto indicato (soggetto / ruolo / utility). Se è valorizzato, il default è riferito a quella categoria.

---

### 📤 Valore di Ritorno

La funzione restituisce **0 o 1 riga** con la stessa struttura di `fn_get_contatti`:

| Colonna             | Tipo      | Descrizione                                                                    |
| ------------------- | --------- | ------------------------------------------------------------------------------ |
| `id`                | `BIGINT`  | Identificativo del contatto in `anagrafiche.contatti`.                         |
| `tipo_contatto_id`  | `INT`     | Riferimento a `config.tipi_contatti`.                                          |
| `soggetto_id`       | `UUID`    | Riferimento al soggetto (`anagrafiche.soggetti.id`).                           |
| `soggetto_ruolo_id` | `BIGINT`  | Eventuale riferimento al ruolo del soggetto (`anagrafiche.soggetti_ruoli.id`). |
| `utility_id`        | `INT`     | Eventuale riferimento a una utility/servizio (`config.utilities.id`).          |
| `nominativo`        | `VARCHAR` | Nominativo del contatto.                                                       |
| `email`             | `VARCHAR` | Indirizzo email.                                                               |
| `telefono`          | `VARCHAR` | Numero di telefono fisso.                                                      |
| `cellulare`         | `VARCHAR` | Numero di cellulare.                                                           |
| `pec`               | `VARCHAR` | Indirizzo PEC.                                                                 |
| `note`              | `TEXT`    | Note libere sul contatto.                                                      |
| `is_default`        | `BOOLEAN` | Sempre `TRUE` per i record restituiti (per definizione della funzione).        |
| `default_context`   | `VARCHAR` | Contesto in cui il contatto è default (`'soggetto'`, `'ruolo'`, `'utility'`).  |

> 🔎 Se non esiste alcun contatto di default coerente con i parametri, la funzione **restituisce zero righe**: è responsabilità del chiamante decidere se applicare ulteriori fallback (es. usare `fn_get_contatti`) o gestire l’assenza di default.

---

### ⚙️ Flusso Logico Interno

1. **Recupero dei candidati tramite `fn_get_contatti`**
   La funzione, internamente, esegue:

   ```sql
   SELECT *
   FROM script.fn_get_contatti(
       p_soggetto_id,
       p_soggetto_ruolo_id,
       p_utility_id,
       p_tipo_contatto_id,
       p_unita_organizzativa_id
   );
   ```

   In questo modo, l’intera logica di priorità tra soggetto / ruolo / utility resta centralizzata in `fn_get_contatti`.

2. **Filtro sui soli contatti di default (`is_default = TRUE`)**
   Tra i candidati viene applicato un filtro:

   ```sql
   WHERE is_default = TRUE
   ```

   Eventuali contatti non marcati come default vengono scartati.

3. **Scelta del singolo contatto da restituire**
   Se, per qualche motivo (dati sporchi o situazione transitoria), esistono più contatti `is_default = TRUE` nello stesso contesto, viene applicata una `ROW_NUMBER()` con ordinamento:

   ```sql
   ORDER BY
       id
   ```

   in modo da restituire comunque **una sola riga** (la prima in ordine di `id`), evitando errori lato applicazione.

4. **Risultato finale**
   La funzione restituisce la riga con `rn = 1`, se presente. In assenza di contatti di default, la funzione non restituisce alcun record.

---

### 📌 Esempi di Utilizzo

```sql
-- 1) Contatto di default del soggetto (contesto "soggetto")
SELECT *
FROM script.fn_get_contatto_default(
  p_soggetto_id       => '123e4567-e89b-12d3-a456-426614174000',
  p_soggetto_ruolo_id => NULL,
  p_utility_id        => NULL,
  p_tipo_contatto_id  => NULL
);

-- 2) Contatto di default per un ruolo specifico del soggetto (es. ruolo Cliente)
SELECT *
FROM script.fn_get_contatto_default(
  p_soggetto_id       => '123e4567-e89b-12d3-a456-426614174000',
  p_soggetto_ruolo_id => 10,   -- id in anagrafiche.soggetti_ruoli
  p_utility_id        => NULL,
  p_tipo_contatto_id  => NULL
);

-- 3) Contatto di default per un ruolo e un tipo_contatto specifico (es. Amministrazione)
SELECT *
FROM script.fn_get_contatto_default(
  p_soggetto_id       => '123e4567-e89b-12d3-a456-426614174000',
  p_soggetto_ruolo_id => 10,
  p_utility_id        => NULL,
  p_tipo_contatto_id  => 1     -- id di config.tipi_contatti
);

-- 4) Contatto di default per una utility (es. contatto di riferimento per una fornitura specifica)
SELECT *
FROM script.fn_get_contatto_default(
  p_soggetto_id       => '123e4567-e89b-12d3-a456-426614174000',
  p_soggetto_ruolo_id => NULL,
  p_utility_id        => 5,    -- id di config.utilities
  p_tipo_contatto_id  => NULL
);
```

---

### 💡 Vantaggi Operativi

* **API semplice per il “contatto principale”**: semplifica notevolmente la vita a chi implementa servizi o UI che hanno bisogno di “un” contatto di riferimento senza gestire manualmente i fallback.
* **Coerenza con il modello di default**: utilizza il flag `is_default` e il `default_context` impostati dai trigger applicativi, mantenendo allineata la logica DB con le regole di dominio.
* **Riduzione della logica applicativa**: sposta nel database la responsabilità di scegliere il contatto corretto, limitando il codice applicativo a consumare un risultato già normalizzato.
* **Facile estendibilità**: se in futuro cambierà la strategia di selezione del default, sarà sufficiente intervenire su `fn_get_contatti` / `fn_get_contatto_default`, senza modificare le chiamate client.

---

{% include-markdown "signature-core.md" %}
