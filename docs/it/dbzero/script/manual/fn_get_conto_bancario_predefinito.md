## 📘 Documentazione Funzione – `script.fn_get_conto_bancario_predefinito(soggetto_ruolo_id, uso)`

> 👀 **Vedi anche**  
>
Approfondimento Tabelle / Vista:  
>
[anagrafiche.conti_bancari](/dbzero/anagrafiche/tabelle/conti_bancari)    
> [anagrafiche.soggetti_ruoli](/dbzero/anagrafiche/tabelle/soggetti_ruoli)    
> [anagrafiche.soggetti_conti_bancari](/dbzero/anagrafiche/tabelle/soggetti_conti_bancari)   
> [anagrafiche.soggetti_ruoli_conti_bancari](/dbzero/anagrafiche/tabelle/soggetti_ruoli_conti_bancari)   
>
Approfondimento vista/funzioni:  
>
[anagrafiche.vw_conti_bancari_per_ruolo](/dbzero/anagrafiche/funzioni/vw_conti_bancari_per_ruolo)   
> [script.fn_get_messaggio](/dbzero/script/funzioni/fn_get_messaggio)   

La funzione **`script.fn_get_conto_bancario_predefinito(soggetto_ruolo_id, uso)`** restituisce, per un determinato **ruolo di soggetto** e un dato **uso del conto** (`INCASSO`, `PAGAMENTO`, `RIMBORSO`, `GENERICO`), **al massimo un conto bancario selezionato**, applicando la logica di priorità e fallback già implementata nella vista **`anagrafiche.vw_conti_bancari_per_ruolo`**.

Se non esiste alcun conto compatibile per l’uso richiesto, la funzione tenta un **fallback automatico** su `uso = 'GENERICO'`. Se nemmeno in questo caso trova un candidato, restituisce `NULL` (nessun conto disponibile).

---

### 🎯 Scopo Principale
(latest review 01-12-25)
* **Incapsulare la logica di selezione del conto**
  Fornisce un punto di accesso unico per ottenere “il conto da usare ora” dato un `soggetto_ruolo_id` e un `uso`, senza dover ripetere join e ordinamenti sulle tabelle sorgenti.

* **Uso semplificato da parte delle query applicative**
  Evita che i moduli di fatturazione, pagamenti, SEPA, ecc. debbano conoscere i dettagli della vista `vw_conti_bancari_per_ruolo`.

* **Fallback automatico su uso GENERICO**
  Quando non esiste un conto specifico per l’uso richiesto (es. `PAGAMENTO`), ma esiste un conto di uso `GENERICO`, la funzione restituisce comunque quest’ultimo come soluzione di ripiego.

---

### 茶 Parametri di input

| Nome                | Tipo      | Obbligatorio | Descrizione                                                                              |
| ------------------- | --------- | ------------ | ---------------------------------------------------------------------------------------- |
| `soggetto_ruolo_id` | `BIGINT`  | Sì           | Identificativo del ruolo (`anagrafiche.soggetti_ruoli.id`) per cui selezionare il conto. |
| `uso`               | `VARCHAR` | Sì           | Uso richiesto del conto: `INCASSO`, `PAGAMENTO`, `RIMBORSO` o `GENERICO`.                |

---

###  Valore di ritorno

La funzione restituisce una **riga della vista** `anagrafiche.vw_conti_bancari_per_ruolo` oppure `NULL`.

In pratica, il tipo di ritorno contiene i seguenti campi:

| Colonna                   | Tipo          | Descrizione                                                                           |
| ------------------------- | ------------- | ------------------------------------------------------------------------------------- |
| `soggetto_ruolo_id`       | `BIGINT`      | Ruolo per cui è stato selezionato il conto.                                           |
| `uso`                     | `VARCHAR`     | Uso con cui il conto è stato selezionato (può coincidere o meno con l’uso richiesto). |
| `conto_bancario_id`       | `BIGINT`      | Riferimento a `anagrafiche.conti_bancari.id`.                                         |
| `soggetto_ruolo_conto_id` | `BIGINT`      | ID del legame ruolo↔conto, se la fonte è `RUOLO`.                                     |
| `soggetto_conto_id`       | `BIGINT`      | ID del legame soggetto↔conto, se la fonte è `SOGGETTO`.                               |
| `fonte`                   | `VARCHAR`     | Origine della selezione: `'RUOLO'` oppure `'SOGGETTO'`.                               |
| `predefinito`             | `BOOLEAN`     | Indica se il legame usato è marcato come predefinito.                                 |
| `valido_dal`              | `DATE`        | Data di inizio validità del legame selezionato.                                       |
| `valido_al`               | `DATE`        | Data di fine validità del legame selezionato (o `NULL` per validità “open-ended”).    |
| `data_update`             | `TIMESTAMPTZ` | Timestamp dell’ultimo aggiornamento del legame usato.                                 |

Se non viene trovato alcun conto idoneo né per l’uso richiesto né per `GENERICO`, la funzione restituisce **`NULL`**.

---

### 易 Logica interna (alto livello)

La funzione è implementata in PL/pgSQL con logica simile alla seguente:

1. **Ricerca diretta per l’uso richiesto**

   ```plpgsql
   SELECT *
     INTO v_res
     FROM anagrafiche.vw_conti_bancari_per_ruolo v
    WHERE v.soggetto_ruolo_id = p_soggetto_ruolo_id
      AND v.uso               = p_uso
    LIMIT 1;

   IF v_res.soggetto_ruolo_id IS NOT NULL THEN
       RETURN v_res;
   END IF;
   ```

   * Se esiste almeno un candidato per `(soggetto_ruolo_id, uso)`, viene restituito direttamente.
   * Grazie alla vista, questa riga è già il **miglior candidato** (priorità RUOLO→SOGGETTO, predefinito, recenza).

2. **Fallback su uso `GENERICO`**

   ```plpgsql
   IF p_uso IS DISTINCT FROM 'GENERICO' THEN
       SELECT *
         INTO v_res
         FROM anagrafiche.vw_conti_bancari_per_ruolo v
        WHERE v.soggetto_ruolo_id = p_soggetto_ruolo_id
          AND v.uso               = 'GENERICO'
        LIMIT 1;

       IF v_res.soggetto_ruolo_id IS NOT NULL THEN
           RETURN v_res;
       END IF;
   END IF;
   ```

   * Viene eseguito solo se l’uso richiesto **non è già `GENERICO`**.
   * Se esiste un conto `GENERICO` per il ruolo indicato, viene restituito come soluzione di ripiego.

3. **Nessun conto trovato**

   ```plpgsql
   RETURN NULL;
   ```

   * Viene notificata l’assenza di un conto idoneo lasciando al chiamante la gestione dell’errore di dominio (es. bloccare l’operazione o chiedere all’utente di configurare un conto).

---

### Comportamento funzionale

* **Rispetto della logica RUOLO → SOGGETTO**
  La funzione non replica la logica di priorità tra ruoli e soggetti: la delega interamente alla vista `vw_conti_bancari_per_ruolo`. In questo modo è sufficiente mantenere la logica di selezione in un solo punto.

* **Uso richiesto vs uso effettivo**
  Il campo `uso` restituito dalla funzione può essere:

  * uguale all’uso richiesto (es. chiamata con `PAGAMENTO` → trovato `PAGAMENTO`), oppure
  * `GENERICO`, se è scattato il fallback.

* **Nessun side-effect**
  La funzione è dichiarata tipicamente come `STABLE`: non modifica dati e si limita a leggere la vista. È quindi sicura da usare in join e clausole `SELECT` più complesse.

---

### 🔖  Esempi d’uso

**1. Ottenere il conto di INCASSO per un ruolo**

```sql
SELECT (f).*  -- espande i campi della vista
FROM script.fn_get_conto_bancario_predefinito(:p_soggetto_ruolo_id, 'INCASSO') AS f;
```

**2. Fallback automatico su GENERICO**

```sql
SELECT (f).fonte,
       (f).uso,
       (f).conto_bancario_id
FROM script.fn_get_conto_bancario_predefinito(:p_soggetto_ruolo_id, 'PAGAMENTO') AS f;
```

Se non esiste un conto per `PAGAMENTO` ma esiste un conto `GENERICO`, la funzione restituirà `uso = 'GENERICO'`.

**3. Uso in join per arricchire con IBAN**

```sql
SELECT c.iban,
       c.bic_swift,
       v.*
FROM script.fn_get_conto_bancario_predefinito(:p_soggetto_ruolo_id, 'INCASSO') AS v
JOIN anagrafiche.conti_bancari c
  ON c.id = v.conto_bancario_id;
```

---

## Note di modellazione e best practice

* La funzione presuppone che la **configurazione dei conti** (legami soggetto/ruolo, flag `predefinito`, `bloccato`, `valido_dal/al`, `attivo`) sia già correttamente gestita dalla logica applicativa e dai trigger delle tabelle sorgenti.
* In caso di assenza di risultati (`NULL`), è responsabilità del chiamante decidere se:

  * sollevare un errore applicativo,
  * richiedere all’utente di configurare un conto per il ruolo/uso richiesto,
  * oppure utilizzare una logica alternativa.
* È fortemente consigliato usare questa funzione (o direttamente la vista) come **unico punto di selezione** del conto operativo, per mantenere coerenza in tutti i moduli (fatturazione, SEPA, rimborsi, ecc.).

---

> **In sintesi:**
> `script.fn_get_conto_bancario_predefinito` è il wrapper di dominio sulla vista `vw_conti_bancari_per_ruolo`: dato un ruolo e un uso, restituisce il miglior conto disponibile secondo le regole di validità, blocco e priorità, con fallback automatico su `GENERICO` quando necessario.
