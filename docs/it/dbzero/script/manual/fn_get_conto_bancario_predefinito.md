## 📘 Documentazione Funzione – `script.fn_get_conto_bancario_predefinito(soggetto_ruolo_id, uso, istanza_utility_id)`

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
[anagrafiche.vw_conti_bancari_per_ruolo](/dbzero/anagrafiche/views/vw_conti_bancari_per_ruolo)   
> [script.fn_get_messaggio](/dbzero/script/funzioni/fn_get_messaggio)   

La funzione **`script.fn_get_conto_bancario_predefinito(soggetto_ruolo_id, uso, istanza_utility_id)`** restituisce, per un determinato **ruolo di soggetto**, un dato **uso del conto** (`INCASSO`, `PAGAMENTO`, `RIMBORSO`, `GENERICO`) e opzionalmente una **istanza utility**, **al massimo un conto bancario selezionato**, applicando una cascata a **7 livelli** sulla vista flat **`anagrafiche.vw_conti_bancari_per_ruolo`**.

La cascata combina due dimensioni: **istanza** (specifica → generico → soggetto) e **uso** (richiesto → GENERICO). Se nessun conto è trovato, restituisce `NULL`.

---
### 🎯 Scopo Principale

(latest review 25-03-26)

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
| `p_soggetto_ruolo_id` | `BIGINT` | Sì | Identificativo del ruolo (`anagrafiche.soggetti_ruoli.id`) per cui selezionare il conto. |
| `p_uso` | `VARCHAR` | Sì | Uso richiesto del conto: `INCASSO`, `PAGAMENTO`, `RIMBORSO` o `GENERICO`. |
| `p_istanza_utility_id` | `BIGINT` | No | ID della istanza utility (`anagrafiche.istanze_utilities.id`). Se valorizzato, il livello ruolo+istanza ha priorità. Se NULL, parte dal livello ruolo generico. |

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

La funzione interroga la vista flat `vw_conti_bancari_per_ruolo` con filtri progressivi:

**FASE A — uso richiesto:**

1. Ruolo + istanza specifica + uso richiesto (solo se `p_istanza_utility_id` valorizzato)
2. Ruolo + istanza NULL + uso richiesto
3. Soggetto + uso richiesto

**FASE B — fallback a uso GENERICO** (solo se uso diverso da GENERICO):

1. Ruolo + istanza specifica + GENERICO (solo se `p_istanza_utility_id` valorizzato)
2. Ruolo + istanza NULL + GENERICO
3. Soggetto + GENERICO

**Nessun conto trovato** → `RETURN NULL`

A ogni livello: `ORDER BY predefinito DESC, data_update DESC LIMIT 1`.

Il chiamante riceve il **miglior conto disponibile** secondo le regole di validita, blocco, priorita istanza e predefinito. In caso di assenza, e responsabilita del chiamante gestire l’errore di dominio.

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
