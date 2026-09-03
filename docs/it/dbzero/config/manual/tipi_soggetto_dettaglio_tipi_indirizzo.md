## 🌱 Documentazione Concettuale – Tabella `config.tipi_soggetto_dettaglio_tipi_indirizzo`

> 👀 **Vedi anche**
>
**Approfondimento tabelle:**
>
[`config.tipi_soggetto_dettaglio`](/dbzero/config/tabelle/tipi_soggetto_dettaglio)   
> [`config.tipi_indirizzi`](/dbzero/config/tabelle/tipi_indirizzi)   
> [`anagrafiche.soggetti`](/dbzero/anagrafiche/tabelle/soggetti)
> [`anagrafiche.indirizzi`](/dbzero/anagrafiche/tabelle/indirizzi)
>
**Funzioni / trigger collegati:**
>
[`anagrafiche.trgfn_indirizzi_guard_tipo_soggetto_dettaglio_tipi_indirizzo`](/dbzero/anagrafiche/funzioni/trgfn_indirizzi_soggetti_guard_tipo_indirizzo) 
> [`script.fn_get_indirizzo`](/dbzero/script/funzioni/fn_get_indirizzo)

---
### 🎯 Scopo Principale
(latest review 19-12-25)
La tabella **`config.tipi_soggetto_dettaglio_tipi_indirizzo`** rappresenta la **matrice di configurazione** che definisce:

* **quali tipi di indirizzo** sono **ammessi** per uno specifico **tipo soggetto dettaglio**
  (es. Persona Fisica, Persona Giuridica, Ente, Condominio, …),
* quali sono **obbligatori**,
* quali possono utilizzare un **fallback** verso un altro tipo di indirizzo.

In pratica, è il punto in cui dichiari:

> “Per questo *tipo soggetto dettaglio*, questi tipi di indirizzo sono permessi, questi sono obbligatori e, se uno manca, può essere sostituito da quest’altro.”

Questa tabella governa quindi:

* la **validazione degli indirizzi** (`anagrafiche.indirizzi`) tramite trigger *guard*,
* la **logica di fallback** utilizzata da funzioni di lookup come `script.fn_get_indirizzo`.

---

### Ruolo nel Modello Dati

Il modello dati che ruota intorno a questa matrice è il seguente:

* `config.tipi_soggetto_dettaglio` → definisce la **natura del soggetto** (persona fisica, giuridica, ente, …)
* `config.tipi_indirizzi` → definisce i **tipi di indirizzo** (RES, DOMFISC, FATT, SEDELEG, …)
* `anagrafiche.soggetti` → istanze reali dei soggetti
* **`config.tipi_soggetto_dettaglio_tipi_indirizzo`** → definisce **quali tipi indirizzo sono validi per quel tipo soggetto dettaglio**
* `anagrafiche.indirizzi` → contiene gli indirizzi effettivi associati al soggetto

Questa tabella consente di:

* evitare combinazioni incoerenti (es. indirizzi non sensati per un certo tipo di soggetto),
* evitare regole hardcoded in trigger o funzioni,
* mantenere le regole come **dati configurabili e versionabili**.

---

### 🧾 Struttura – Attributi principali

| Colonna                      | Tipo        | Obblig. | Descrizione sintetica                                         |
| ---------------------------- | ----------- | ------- | ------------------------------------------------------------- |
| `id`                         | bigint      | Sì      | Chiave primaria tecnica.                                      |
| `tipo_soggetto_dettaglio_id` | bigint      | Sì      | FK → `config.tipi_soggetto_dettaglio.id`.                     |
| `tipo_indirizzo_id`          | integer     | Sì      | FK → `config.tipi_indirizzi.id`. Tipo indirizzo ammesso.      |
| `obbligatorio`               | boolean     | Sì      | Se `TRUE`, almeno un indirizzo di questo tipo è richiesto.    |
| `valido_dal` / `valido_al`   | date        | No      | Finestra temporale di validità della regola.                  |
| `attivo`                     | boolean     | Sì      | Attivazione logica della regola.                              |
| `fallback_tipo_indirizzo_id` | integer     | No      | Tipo indirizzo di fallback (FK → `config.tipi_indirizzi.id`). |
| `meta`                       | jsonb       | Sì      | Metadati estendibili.                                         |
| `user_insert`, `user_update` | text        | Sì      | Audit utente.                                                 |
| `data_insert`, `data_update` | timestamptz | Sì      | Audit temporale.                                              |
| `storicizza`                 | boolean     | Sì      | Integrazione con framework di storicizzazione.                |

**Vincoli principali:**

* `UNIQUE (tipo_soggetto_dettaglio_id, tipo_indirizzo_id)`
  → una combinazione è definita una sola volta.
* `CHECK valido_dal / valido_al`
  → impedisce intervalli temporali incoerenti.
* `CHECK fallback_not_self`
  → il fallback non può riferirsi allo stesso tipo indirizzo.

---

### Regole di Funzionamento

 **1️⃣ Presenza o assenza della matrice**

La logica applicata dai trigger *guard* sugli indirizzi è:

* **Se non esiste alcuna riga** per un dato `tipo_soggetto_dettaglio`
  ➜ nessuna restrizione applicata: **tutti i tipi indirizzo sono ammessi**.

* **Se esiste almeno una riga**
  ➜ la matrice è attiva e:

  * sono ammessi solo i `tipo_indirizzo_id` presenti,
  * la riga deve essere `attivo = TRUE`,
  * la data corrente deve rientrare nell’intervallo di validità.

Questa logica consente una **adozione graduale** delle regole.

---

 **2️⃣ Obbligatorietà**

Quando `obbligatorio = TRUE`, il sistema richiede che:

* per quel soggetto esista **almeno un indirizzo** di quel tipo,
* il controllo è tipicamente effettuato:

  * in fase di validazione applicativa,
  * oppure in processi batch / di consolidamento dati.

---

 **3️⃣ Fallback tra tipi indirizzo**

Il campo `fallback_tipo_indirizzo_id` permette di definire **strategie di recupero** quando un indirizzo richiesto non è presente.

Esempio concettuale per *Persona Giuridica*:

| Tipo soggetto | Tipo indirizzo | Obbligatorio | Fallback |
| ------------- | -------------- | ------------ | -------- |
| PG            | FATT           | TRUE         | NULL     |
| PG            | SEDEOP         | FALSE        | SEDELEG  |
| PG            | SEDELEG        | TRUE         | NULL     |

In questo caso:

* se viene richiesto un indirizzo **SEDEOP** ma non esiste,
* la funzione di lookup può usare **SEDELEG** come alternativa.

> La logica di fallback **non è nel trigger**, ma nelle funzioni di servizio (es. `script.fn_get_indirizzo`).

---

### Esempi d’Uso (concettuali)

 **✔ Persona Fisica**

* Ammessi: RES, DOMFISC, POSTA
* Obbligatori: RES
* Fallback:

  * DOMFISC → RES

 **✔ Persona Giuridica**

* Ammessi: SEDELEG, SEDEOP, FATT
* Obbligatori: SEDELEG, FATT
* Fallback:

  * SEDEOP → SEDELEG

 **✔ Tipo soggetto senza matrice**

* Nessuna riga configurata
* ➜ indirizzi **non vincolati**, utile per migrazioni o onboarding progressivo

---

### Vantaggi Operativi

* **Regole configurabili e versionabili**
* **Separazione netta tra dominio e dati operativi**
* **Supporto a modelli soggetto complessi e reali**
* **Backward compatibility** con dati storici
* **Riutilizzabile** da trigger, API e servizi applicativi

> **"`config.tipi_soggetto_dettaglio_tipi_indirizzo` governa la coerenza degli indirizzi in base alla natura del soggetto, trasformando le regole da codice rigido a configurazione esplicita."**

{% include-markdown "signature-core.md" %}
