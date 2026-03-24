## 📘Documentazione Vista – `anagrafiche.vw_conti_bancari_per_ruolo`

> 👀 **Vedi anche**
>
Approfondimento Tabelle:
>
[anagrafiche.conti_bancari](/dbzero/anagrafiche/tabelle/conti_bancari)
> [anagrafiche.soggetti](/dbzero/anagrafiche/tabelle/soggetti)
> [anagrafiche.soggetti_ruoli](/dbzero/anagrafiche/tabelle/soggetti_ruoli)
> [anagrafiche.soggetti_conti_bancari](/dbzero/anagrafiche/tabelle/soggetti_conti_bancari)
> [anagrafiche.soggetti_ruoli_conti_bancari](/dbzero/anagrafiche/tabelle/soggetti_ruoli_conti_bancari)
>
Approfondimento funzioni:
>
[script.fn_get_conto_bancario_predefinito](/dbzero/script/funzioni/fn_get_conto_bancario_predefinito)

La vista **`anagrafiche.vw_conti_bancari_per_ruolo`** espone **tutte le candidate** dei conti bancari per ogni **ruolo di soggetto**, organizzate per **uso** e **utility**, con indicazione della **fonte** (RUOLO o SOGGETTO).

A differenza della versione precedente (che restituiva una sola riga per coppia ruolo/uso tramite `DISTINCT ON`), la vista ora e **flat**: espone tutte le righe candidate con ordinamento di priorita. La **selezione singola** con cascata utility e delegata alla funzione `script.fn_get_conto_bancario_predefinito`.

---
### 🎯 Scopo Principale

(latest review 24-03-26)

* **Vista flat di tutte le candidate per ruolo**
  Espone tutte le righe candidate da entrambi i livelli di legame, con `utility_id` e `utility_codice`:

  * legami a livello **ruolo** (`soggetti_ruoli_conti_bancari`) — con `utility_id` nullable
  * legami a livello **soggetto** (`soggetti_conti_bancari`) — `utility_id` sempre NULL

* **Ordinamento di priorita (non selezione)**
  Le righe sono ordinate per priorita: ruolo+utility > ruolo generico > soggetto, poi predefinito, poi recenza. La vista **non** applica `DISTINCT ON`: restituisce tutte le candidate.

* **Filtro su validita e stato**
  Espone soltanto conti:

  * **attivi** (`conti_bancari.attivo = TRUE`),
  * **non bloccati** a livello di legame (`bloccato = FALSE`),
  * con **validita compatibile con la data odierna** (`valido_dal/valido_al`).

* **Selezione singola delegata alla funzione**
  La scelta del "miglior conto" con cascata utility e uso e responsabilita di `fn_get_conto_bancario_predefinito`.

---

### Struttura logica della vista

La vista è costruita in più passi mediante CTE:

1. **`role_cand` – Candidate di RUOLO**

   Seleziona tutti i legami **a livello ruolo** (`anagrafiche.soggetti_ruoli_conti_bancari`) che rispettano:

   * data odierna compresa tra `valido_dal` e `valido_al` (quando valorizzati),
   * `blocccato = FALSE` (o NULL trattato come FALSE),
   * conto associato `attivo = TRUE` su `anagrafiche.conti_bancari`.

   Campi principali:

   * `soggetto_ruolo_id`
   * `uso`
   * `conto_bancario_id`
   * `soggetto_ruolo_conto_id` (ID del legame ruolo↔conto)
   * `predefinito`
   * `priority = 1` (per dare precedenza ai legami di ruolo)
   * `fonte = 'RUOLO'`

2. **`subj_cand` – Candidate di SOGGETTO**

   Seleziona tutti i legami **a livello soggetto** (`anagrafiche.soggetti_conti_bancari`) compatibili con le stesse regole di validità/blocco/attivazione, “proiettandoli” sul `soggetto_ruolo_id` tramite `anagrafiche.soggetti_ruoli`.

   Campi principali:

   * `soggetto_ruolo_id` (derivato da `soggetti_ruoli`)
   * `uso`
   * `conto_bancario_id`
   * `soggetto_conto_id` (ID del legame soggetto↔conto)
   * `predefinito`
   * `priority = 2` (perché il SOGGETTO è fallback rispetto al RUOLO)
   * `fonte = 'SOGGETTO'`

3. **`candidates` – Unione dei due insiemi**

   Esegue `UNION ALL` tra `role_cand` e `subj_cand`, mantenendo per ogni riga:

   * `soggetto_ruolo_id`, `uso`, `conto_bancario_id`
   * identificativo del legame (`soggetto_ruolo_conto_id` / `soggetto_conto_id`)
   * `predefinito`, `priority`, `valido_dal`, `valido_al`, `data_update`
   * `fonte` (`'RUOLO'` o `'SOGGETTO'`)

4. **JOIN su `config.utilities`** per esporre `utility_codice` accanto a `utility_id`.

5. **Ordinamento finale** (senza `DISTINCT ON`):

   ```sql
   ORDER BY soggetto_ruolo_id, uso,
     CASE
       WHEN fonte = ‘RUOLO’ AND utility_id IS NOT NULL THEN 1
       WHEN fonte = ‘RUOLO’ AND utility_id IS NULL     THEN 2
       WHEN fonte = ‘SOGGETTO’                         THEN 3
     END,
     predefinito DESC,
     data_update DESC
   ```

   Ordine di priorita:

   1. **Ruolo + utility specifica** (massima priorita)
   2. **Ruolo generico** (utility NULL)
   3. **Soggetto** (fallback)
   4. `predefinito DESC` → legame marcato predefinito
   5. `data_update DESC` → piu recente

   La vista restituisce **tutte le righe** ordinate. La selezione "1 riga" e delegata a `fn_get_conto_bancario_predefinito`.

---

### Colonne esposte

| Colonna                   | Tipo          | Descrizione                                                                                 |
| ------------------------- | ------------- | ------------------------------------------------------------------------------------------- |
| `soggetto_ruolo_id`       | `bigint`      | Identificativo del ruolo per cui viene selezionato il conto.                                |
| `uso`                     | `varchar`     | Uso del conto: `INCASSO`, `PAGAMENTO`, `RIMBORSO` o `GENERICO`.                             |
| `conto_bancario_id`       | `bigint`      | Riferimento a `anagrafiche.conti_bancari.id` del conto selezionato.                         |
| `soggetto_ruolo_conto_id` | `bigint`      | ID del legame ruolo↔conto (`soggetti_ruoli_conti_bancari`), se la fonte è `RUOLO`.          |
| `soggetto_conto_id`       | `bigint`      | ID del legame soggetto↔conto (`soggetti_conti_bancari`), se la fonte è `SOGGETTO`.          |
| `utility_id`              | `integer`     | ID della utility (`config.utilities.id`). NULL per legami generici o fonte SOGGETTO.         |
| `utility_codice`          | `varchar`     | Codice della utility (es. `GAS`, `IDRICO`). NULL se `utility_id` è NULL.                    |
| `fonte`                   | `varchar`     | Origine della selezione: `'RUOLO'` oppure `'SOGGETTO'`.                                     |
| `predefinito`             | `boolean`     | Indica se il legame usato è marcato come **predefinito** per quel `(soggetto/ruolo, uso)`.  |
| `valido_dal`              | `date`        | Data di inizio validità del legame selezionato.                                             |
| `valido_al`               | `date`        | Data di fine validità del legame selezionato (può essere `NULL` per validità “open-ended”). |
| `data_update`             | `timestamptz` | Timestamp dell’ultimo aggiornamento del legame usato (utile per la prioritizzazione).       |

---

### Comportamento funzionale

* **Filtro temporale**
  Sono inclusi solo i legami per cui:

  * `valido_dal IS NULL OR valido_dal <= CURRENT_DATE`
  * `valido_al IS NULL OR valido_al >= CURRENT_DATE`

* **Filtro di sicurezza e stato**
  Vengono esclusi:

  * legami con `bloccato = TRUE` (tipicamente per motivi di compliance/AML),
  * conti con `attivo = FALSE` su `anagrafiche.conti_bancari`.

* **Priorità RUOLO → SOGGETTO**
  Se esiste un legame **di ruolo** per `(soggetto_ruolo_id, uso)` che rispetta i criteri sopra, questo sarà sempre preferito rispetto agli eventuali legami di SOGGETTO.

* **Gestione di più candidati**
  In presenza di più legami compatibili (es. più conti per lo stesso uso):

  * viene scelto **prima** il legame con `predefinito = TRUE`;
  * a parità di predefinito, vince il legame con `data_update` più recente.

---

### 🔖 Esempi d’uso

**1. Ottenere il conto d’incasso per un ruolo specifico**

```sql
SELECT *
FROM anagrafiche.vw_conti_bancari_per_ruolo
WHERE soggetto_ruolo_id = :p_soggetto_ruolo_id
  AND uso = 'INCASSO';
```

**2. Ottenere tutti i conti correnti “correnti” per un ruolo (tutti gli usi)**

```sql
SELECT *
FROM anagrafiche.vw_conti_bancari_per_ruolo
WHERE soggetto_ruolo_id = :p_soggetto_ruolo_id;
```

**3. Join con `conti_bancari` per leggere IBAN e dettagli**

```sql
SELECT v.soggetto_ruolo_id,
       v.uso,
       cb.iban,
       cb.bic_swift,
       v.fonte,
       v.predefinito
FROM anagrafiche.vw_conti_bancari_per_ruolo v
JOIN anagrafiche.conti_bancari cb
  ON cb.id = v.conto_bancario_id
WHERE v.soggetto_ruolo_id = :p_soggetto_ruolo_id;
```

---

### Note di modellazione e best practice

* La vista assume che tutta la logica di **normalizzazione e validazione IBAN/BIC**, nonché di **gestione storicizzazione e flag `bloccato`**, sia già gestita a livello di tabelle e trigger (`*_guard`, `*_normalize`).
* È possibile avere **più legami** per lo stesso `(soggetto/ruolo, uso)`; la vista ne espone comunque **uno solo**, seguendo le priorità definite.
* Per l’uso applicativo è consigliato **incapsulare la vista** in funzioni di dominio (come `script.fn_get_conto_bancario_predefinito`) per ridurre la duplicazione di logica nelle query.

---

> **In sintesi:**
> `anagrafiche.vw_conti_bancari_per_ruolo` fornisce una vista già “risolta” del conto da utilizzare per ciascun ruolo e uso, applicando automaticamente le priorità RUOLO → SOGGETTO, la selezione del predefinito e i vincoli di validità, blocco e attivazione.
