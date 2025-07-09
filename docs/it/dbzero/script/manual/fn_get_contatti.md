## 📘 Documentazione Concettuale – Funzione `script.fn_get_contatti`

> 👀 **Vedi anche**
>
> Approfondimento tabelle:    
> - [anagrafiche.soggetti](/dbzero/anagrafiche/tabelle/soggetti)    
> - [anagrafiche.soggetti_ruoli](/dbzero/anagrafiche/tabelle/soggetti_ruoli)    
> - [anagrafiche.contatti](/dbzero/anagrafiche/tabelle/contatti)    
> - [config.tipi_contatti](/dbzero/config/tabelle/tipi_contatti)    
> - [config.utilities](/dbzero/config/tabelle/utilities)    
>
> Approfondimento funzioni :    
> - [anagrafiche.trgfn_contatti_ins_upd_set_default_contatto](/dbzero/anagrafiche/funzioni/trgfn_contatti_ins_upd_set_default_contatto)     
> - [script.fn_log_and_raise_error](/dbzero/script/funzioni/fn_log_and_raise_error)     


La funzione **`script.fn_get_contatti(p_soggetto_id UUID, p_soggetto_ruolo_id INTEGER DEFAULT NULL, p_utility_id INTEGER DEFAULT NULL, p_tipo_contatto_id INTEGER DEFAULT NULL)`** restituisce un singolo contatto per ogni `tipo_contatto_id`, applicando una logica di priorità basata sul **contesto** e validando i parametri con logging centralizzato.

---

### 🎯 Scopo Principale

* **Selezione univoca per tipo**
  Ottenere il contatto più rilevante per ciascun `tipo_contatto_id` rispetto ai parametri forniti.
* **Gerarchia di contesti**
  Filtra e ordina i contatti in base alla priorità:

  1. **soggetto + ruolo + utility**
  2. **soggetto + ruolo**
  3. **soggetto + utility**
  4. **solo soggetto** (fallback **soggetto** garantisce che, se non esistono contatti per proprietà o utility, si recuperino comunque i contatti generici del soggetto.)
* **Validazione e logging**
  Verifica che `p_soggetto_id` sia valorizzato; in caso contrario utilizza `script.fn_log_and_raise_error` per loggare e sollevare un’eccezione con codice `ERRORE_PARAMETRI`.
* **Centralizzazione della logica**
  La tabella risultante è pensata come unico punto di accesso per il reperimento contatti: consente di applicare filtri successivi (es. solo default, ordini personalizzati, ecc.) senza replicare la logica di fallback in ogni query.

---

### 🔍 Parametri di Input

| Nome                  | Tipo   | Default | Descrizione                                                                   |
| --------------------- | ------ | ------- | ----------------------------------------------------------------------------- |
| `p_soggetto_id`       | `UUID` | —       | **Obbligatorio**: ID del soggetto. Se `NULL`, genera errore centralizzato.    |
| `p_soggetto_ruolo_id` | `INT`  | `NULL`  | If present, filtra i contatti legati a quel ruolo del soggetto.               |
| `p_utility_id`        | `INT`  | `NULL`  | If present, filtra i contatti associati a una specifica utility.              |
| `p_tipo_contatto_id`  | `INT`  | `NULL`  | If present, filtra per un particolare tipo di contatto (es. email, telefono). |

---

### ⚙️ Flusso Logico

1. **Validazione `p_soggetto_id`**
   Se `p_soggetto_id` è `NULL`, attiva il CTE `validate` che chiama:

   ```sql
   script.fn_log_and_raise_error(
     'database',
     'fn_get_contatti',
     'ERRORE_PARAMETRI',
     jsonb_build_object(
       'soggetto_id', p_soggetto_id,
       'soggetto_ruolo_id', p_soggetto_ruolo_id,
       'utility_id', p_utility_id,
       'tipo_contatto_id', p_tipo_contatto_id
     ),
     COALESCE(p_soggetto_id::text,'NULL')
   )
   ```

2. **Costruzione del CTE `candidates`**
   Seleziona da `anagrafiche.contatti` i record matching `p_soggetto_id`, `p_soggetto_ruolo_id`, `p_utility_id`, `p_tipo_contatto_id`, calcolando `priority`:

   ```sql
   CASE
     WHEN c.soggetto_ruolo_id IS NOT DISTINCT FROM p_soggetto_ruolo_id
       AND c.utility_id IS NOT DISTINCT FROM p_utility_id THEN 1
     WHEN c.soggetto_ruolo_id IS NOT DISTINCT FROM p_soggetto_ruolo_id THEN 2
     WHEN c.utility_id IS NOT DISTINCT FROM p_utility_id THEN 3
     ELSE 4
   END AS priority
   ```

3. **Selezione del contatto per tipo**
   Applica:

   ```sql
   ROW_NUMBER() OVER (
     PARTITION BY candidates.tipo_contatto_id
     ORDER BY candidates.priority
   ) AS rn
   ```

   e filtra `WHERE rn = 1`.

4. **Restituzione dei risultati**
   Restituisce le colonne:
   `id`, `tipo_contatto_id`, `soggetto_id`, `soggetto_ruolo_id`, `utility_id`, `nominativo`, `email`, `telefono`, `cellulare`, `pec`, `note`, `is_default`, `default_context`.

---


> 🧠 **“Encapsulare in SQL nativo logica complessa di fallback e validazione semplifica l’uso e la manutenzione.”**
