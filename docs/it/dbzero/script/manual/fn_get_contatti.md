## 📘 Documentazione Concettuale – Funzione `script.fn_get_contatti`

> 👀 **Vedi anche**
>
> * Trigger `anagrafiche.trgfn_contatti_ins_upd_set_default_contatto`
> * Solo contatti: Tabella `anagrafiche.contatti`

La funzione **`script.fn_get_contatti(p_soggetto_id UUID, p_soggetto_ruolo_id INTEGER DEFAULT NULL, p_utility_id INTEGER DEFAULT NULL, p_tipo_contatto_id INTEGER DEFAULT NULL)`** restituisce un unico contatto per ogni `tipo_contatto_id`, applicando una logica di priorità basata sul **contesto** e validando i parametri con logging centralizzato.

---

### 🎯 Scopo Principale

* **Selezione univoca per tipo**
  Ottenere il contatto più rilevante per ciascun `tipo_contatto_id` rispetto ai parametri forniti.
* **Gerarchia di contesti**
  Filtra e ordina i contatti in base alla priorità:

  1. **soggetto + ruolo + utility**
  2. **soggetto + ruolo**
  3. **soggetto + utility**
  4. **solo soggetto**
* **Validazione e logging**
  Verifica che `p_soggetto_id` sia valorizzato; in caso contrario utilizza `script.fn_log_and_raise_error` per loggare e sollevare un’eccezione con codice `ERRORE_PARAMETRI`.

---

### 🔍 Parametri di Input

| Nome                  | Tipo   | Default | Descrizione                                           |
| --------------------- | ------ | ------- | ----------------------------------------------------- |
| `p_soggetto_id`       | `UUID` | —       | **Obbligatorio**: ID del soggetto. Se `NULL` o vuoto, genera errore centralizzato. |
| `p_soggetto_ruolo_id` | `INT`  | `NULL`  | Se fornito, filtra i contatti legati a quel ruolo.                                 |
| `p_utility_id`        | `INT`  | `NULL`  | Se fornito, filtra i contatti associati a una specifica utility.                   |
| `p_tipo_contatto_id`  | `INT`  | `NULL`  | Se fornito, filtra su un particolare tipo di contatto (es. email, telefono).       |

---

### ⚙️ Flusso Logico

1. **Validazione `p_soggetto_id`**

   ```plpgsql
   IF p_soggetto_id IS NULL OR p_soggetto_id = ''::uuid THEN
     PERFORM script.fn_log_and_raise_error(
       'database',
       'fn_get_contatti',
       'ERRORE_PARAMETRI',
       jsonb_build_object(
         'soggetto_id',       p_soggetto_id,
         'soggetto_ruolo_id', p_soggetto_ruolo_id,
         'utility_id',        p_utility_id,
         'tipo_contatto_id',  p_tipo_contatto_id
       ),
       COALESCE(p_soggetto_id::text, 'NULL')
     );
   END IF;
   ```

   Utilizza `fn_log_and_raise_error` che effettua sia il logging sia il `RAISE EXCEPTION` in caso di parametri non validi.

2. **Costruzione del CTE `candidates`**
   Seleziona da `anagrafiche.contatti` i record con:

   * `soggetto_id = p_soggetto_id`
   * `soggetto_ruolo_id` e `utility_id` corrispondenti ai parametri (o entrambi NULL)
   * `tipo_contatto_id = p_tipo_contatto_id` se specificato
     Aggiunge il campo calcolato `priority`:

   ```sql
   CASE
     WHEN soggetto_ruolo_id IS NOT NULL AND utility_id IS NOT NULL THEN 1
     WHEN soggetto_ruolo_id IS NOT NULL THEN 2
     WHEN utility_id IS NOT NULL THEN 3
     ELSE 4
   END
   ```

3. **Selezione del contatto per tipo**
   Esegue:

   ```sql
   SELECT *, row_number() OVER (
     PARTITION BY tipo_contatto_id
     ORDER BY priority
   ) AS rn
   FROM candidates
   ```

   e filtra `WHERE rn = 1` per restituire solo il record con priorità massima per ciascun tipo.

4. **Restituzione dei risultati**
   Il `RETURN QUERY` restituisce la tabella con le colonne:
   `id`, `tipo_contatto_id`, `soggetto_id`, `soggetto_ruolo_id`, `utility_id`, `nominativo`, `email`, `telefono`, `cellulare`, `pec`, `note`, `is_default`, `default_context`.

---

### 🔗 Colonne di Output

| Nome                | Tipo      | Descrizione                                                          |
| ------------------- | --------- | -------------------------------------------------------------------- |
| `id`                | `INT`     | Chiave primaria del contatto.                                        |
| `tipo_contatto_id`  | `INT`     | Identificatore del tipo di contatto.                                 |
| `soggetto_id`       | `UUID`    | ID del soggetto associato.                                           |
| `soggetto_ruolo_id` | `INT`     | ID della relazione soggetto-ruolo.                                   |
| `utility_id`        | `INT`     | ID della utility, se presente.                                       |
| `nominativo`        | `VARCHAR` | Nome o descrizione del contatto.                                     |
| `email`             | `VARCHAR` | Indirizzo email.                                                     |
| `telefono`          | `VARCHAR` | Recapito telefonico.                                                 |
| `cellulare`         | `VARCHAR` | Numero di cellulare.                                                 |
| `pec`               | `VARCHAR` | Indirizzo PEC.                                                       |
| `note`              | `TEXT`    | Note aggiuntive.                                                     |
| `is_default`        | `BOOLEAN` | Indica se il contatto è predefinito (nell’ambito `default_context`). |
| `default_context`   | `VARCHAR` | Contesto di default (`soggetto`, `ruolo` o `utility`).               |

---

### 💡 Vantaggi Operativi

* **Unica interfaccia di retrieval**
  Evita query multiple nell’applicazione, incapsulando la logica di priorità.
* **Logica di fallback**
  Filtra progressivamente dal contesto più specifico a quello più generico.
* **Validazione robusta**
  Parametri essenziali controllati con logging e management centralizzato degli errori.
* **Scalabilità**
  La funzione si adatta a nuovi contesti o filtri aggiungendo poche righe di logica.

---

### 🔖 Firma SQL Aggiornata

```sql
CREATE OR REPLACE FUNCTION script.fn_get_contatti(
  p_soggetto_id UUID,
  p_soggetto_ruolo_id INTEGER DEFAULT NULL,
  p_utility_id INTEGER DEFAULT NULL,
  p_tipo_contatto_id INTEGER DEFAULT NULL
)
RETURNS TABLE(
  id INTEGER,
  tipo_contatto_id INTEGER,
  soggetto_id UUID,
  soggetto_ruolo_id INTEGER,
  utility_id INTEGER,
  nominativo VARCHAR,
  email VARCHAR,
  telefono VARCHAR,
  cellulare VARCHAR,
  pec VARCHAR,
  note TEXT,
  is_default BOOLEAN,
  default_context VARCHAR
)
LANGUAGE plpgsql AS $function$
-- Implementation as above
$function$;

COMMENT ON FUNCTION script.fn_get_contatti(UUID, INTEGER, INTEGER, INTEGER) IS
  'Restituisce per ogni tipo_contatto_id il contatto con priorità: 
1) soggetto+ruolo+utility, 2) soggetto+ruolo, 3) soggetto+utility, 4) solo soggetto.
Filtra sui parametri passati e valida p_soggetto_id con logging.';
```

> 🧠 **“Centralizzare ricerca e validazione dei contatti in una singola funzione rende l’accesso ai dati più sicuro, efficiente e manutenibile.”**
