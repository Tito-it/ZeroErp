## 📘 Documentazione Concettuale – Funzione `anagrafiche.fn_lookup_utilities_per_ba`

> 👀 **Vedi anche**
>
> **Approfondimento tabelle:**
>
> • [anagrafiche.billing_account](/dbzero/anagrafiche/tabelle/billing_account)  
> • [anagrafiche.emittenti_fiscali](/dbzero/anagrafiche/tabelle/emittenti_fiscali)  
> • [anagrafiche.emittenti_fiscali_billing_account](/dbzero/anagrafiche/tabelle/emittenti_fiscali_billing_account)  
> • [anagrafiche.emittenti_fiscali_utilities](/dbzero/anagrafiche/tabelle/emittenti_fiscali_utilities)  
> • [config.utilities](/dbzero/config/tabelle/utilities)  
> • [config.utilities_tipi_ruolo](/dbzero/config/tabelle/utilities_tipi_ruolo)  
> • [config.tipi_ruoli](/dbzero/config/tabelle/tipi_ruoli)  
>
> **Approfondimento funzioni:**
>
> • [anagrafiche.fn_get_emittente_fiscale_pk](/dbzero/anagrafiche/manual/fn_get_emittente_fiscale_pk)  
> • [script.fn_log_and_raise_error](/dbzero/script/manual/fn_log_and_raise_error)  
>
---

### 🎯 Scopo Principale

(latest review 22-04-2026)
La funzione **`anagrafiche.fn_lookup_utilities_per_ba()`** restituisce le
utility selezionabili per un billing account, incrociando due vincoli:

* il ruolo del soggetto del billing account (`CL`, `FO`, `GE`, `RS`, ...);
* il ruolo **EF** dell'emittente fiscale collegato al billing account.

Le utility ammesse vengono decorate con gli eventuali parametri di override
configurati in `anagrafiche.emittenti_fiscali_utilities`.

---

### Contesto

La funzione supporta le combo "utility per billing account" usate dal backend
e dal frontend dopo il refactor operatore/emittenti. Il suo obiettivo e'
evitare che l'app proponga utility non compatibili con il ruolo del soggetto o
con l'emittente fiscale effettivamente collegato al BA.

La funzione applica una politica ibrida:

* la matrice `config.utilities_tipi_ruolo` decide quali utility sono ammesse;
* i parametri d'importo sono quelli **effettivi**, da
  `anagrafiche.fn_parametri_importo_utility`: la riga di
  `anagrafiche.emittenti_fiscali_utilities` se c'è, altrimenti i valori di sistema
  dell'utility (e la policy generale dell'emittente per il metodo);
* una utility ammessa ma senza override resta visibile, con i parametri di sistema
  (rev 21-10-2026: prima uscivano `NULL`, e un valore di sistema non esisteva).

---

### Input

| Parametro | Tipo | Descrizione |
|-----------|------|-------------|
| `p_billing_account_id` | `anagrafiche.billing_account.id%TYPE` | ID del billing account. Deve essere valorizzato e `> 0`. |
| `p_ruolo_codice_soggetto` | `text` | Codice del ruolo del soggetto del BA, ad esempio `CL`, `FO`, `GE`, `RS`. |

---

### Output

La funzione ritorna una tabella:

| Colonna | Tipo | Descrizione |
|---------|------|-------------|
| `utility_id` | `bigint` | ID della utility ammessa. |
| `codice` | `text` | Codice della utility. |
| `descrizione` | `text` | Descrizione della utility. |
| `is_personalizzata_per_ef` | `boolean` | `true` se esiste una riga override attiva per emittente/utility. |
| `minimo_soglia_min` | `numeric` | Soglia minima configurata sull'override, se presente. |
| `minimo_soglia_max` | `numeric` | Soglia massima configurata sull'override, se presente. |
| `arrotondamento_importi_dec` | `smallint` | Decimali di arrotondamento effettivi: dell'override, se presente, altrimenti di sistema. |
| `metodo_arrotondamento_importi` | `text` | Metodo di arrotondamento effettivo: dell'override, poi la policy generale dell'emittente, poi di sistema. |

Le righe sono ordinate per `codice`.

---

### Regole

La funzione applica le seguenti regole:

* `p_billing_account_id` e' obbligatorio e deve essere `> 0`.
* `p_ruolo_codice_soggetto` e' obbligatorio e non puo' essere vuoto.
* L'emittente fiscale del BA viene risolto con
  `anagrafiche.fn_get_emittente_fiscale_pk`.
* La utility deve essere ammessa per il ruolo del soggetto del BA.
* La stessa utility deve essere ammessa anche per il ruolo `EF`.
* Le righe di `config.utilities_tipi_ruolo` devono essere attive e valide alla
  data corrente (`valido_dal`/`valido_al`).
* I parametri arrivano da `anagrafiche.fn_parametri_importo_utility`, una riga
  per ogni utility che esiste: senza override la utility resta visibile.

---

### Politica di visibilita'

| Caso | Risultato |
|------|-----------|
| Utility ammessa per ruolo soggetto e ruolo EF, con override attivo | Riga visibile, `is_personalizzata_per_ef = true`, parametri valorizzati. |
| Utility ammessa per ruolo soggetto e ruolo EF, senza override attivo | Riga visibile, `is_personalizzata_per_ef = false`, parametri `NULL`. |
| Utility ammessa solo per il ruolo soggetto | Riga esclusa. |
| Utility ammessa solo per il ruolo EF | Riga esclusa. |
| Ruolo soggetto sconosciuto o senza utility valide | Nessuna riga. |

---

### Errori applicativi

| Codice | Quando viene sollevato |
|--------|------------------------|
| `E_PARAMETRO_INVALIDO` | `p_billing_account_id` e' `NULL`/`<= 0` oppure `p_ruolo_codice_soggetto` e' vuoto. |
| `E_EMITTENTE_DEFAULT_MISSING` | Propagato da `fn_get_emittente_fiscale_pk` quando non e' risolvibile alcun emittente per il BA. |

---

### Dipendenze DB

| Oggetto | Ruolo |
|---------|-------|
| `anagrafiche.fn_get_emittente_fiscale_pk` | Risolve la PK reale dell'emittente fiscale collegato al BA. |
| `anagrafiche.emittenti_fiscali` | Converte la PK emittente nel relativo `soggetto_ruolo_id`. |
| `anagrafiche.emittenti_fiscali_utilities` | Fornisce gli override specifici per coppia emittente/utility. |
| `config.utilities` | Anagrafica delle utility restituite. |
| `config.utilities_tipi_ruolo` | Matrice di ammissibilita' utility/ruolo. |
| `config.tipi_ruoli` | Risolve i codici ruolo del soggetto e il ruolo `EF`. |

---

### Uso backend

La funzione e' pensata per il repository di lookup backend, ad esempio:

* `LookupRepository.list_utilities_per_billing_account(...)`;
* endpoint `GET /api/v1/anagrafiche/billing-account/{id}/utilities/?ruolo=CL`;
* drawer e form UI che devono proporre solo utility coerenti con BA ed
  emittente fiscale.

---

### Esempi d'uso

```sql
-- Utility selezionabili per un BA cliente
SELECT *
FROM anagrafiche.fn_lookup_utilities_per_ba(123, 'CL');

-- Utility selezionabili per un BA fornitore
SELECT *
FROM anagrafiche.fn_lookup_utilities_per_ba(456, 'FO');
```

---

### Note operative

* La funzione e' `STABLE`: legge dati ma non li modifica.
* Il parametro `p_ruolo_codice_soggetto` non viene normalizzato: il chiamante
  deve passare il codice ruolo nella forma prevista da `config.tipi_ruoli`.
* La funzione ritorna zero righe per un ruolo valido ma senza utility
  compatibili; non considera questa condizione un errore.

---

{% include-markdown "signature-core.md" %}
