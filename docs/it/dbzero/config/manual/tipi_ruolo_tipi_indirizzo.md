## 📘 Documentazione Concettuale – Tabella `config.tipi_ruolo_tipi_indirizzo`

> 👀 **Vedi anche**
>
**Tabelle di dominio:**   
>
[`config.tipi_ruoli`](/dbzero/config/tabelle/tipi_ruoli)   
> [`config.tipi_indirizzi`](/dbzero/config/tabelle/tipi_indirizzi)   
>
**Tabelle anagrafiche collegate:**   
>
[`anagrafiche.soggetti_ruoli`](/dbzero/anagrafiche/tabelle/soggetti_ruoli)   
> [`anagrafiche.indirizzi`](/dbzero/anagrafiche/tabelle/indirizzi)   
>
**Funzioni / trigger collegati:**
>
[`anagrafiche.trgfn_indirizzi_guard_tipo_ruolo_tipi_indirizzo`](/dbzero/anagrafiche/funzioni/trgfn_indirizzi_guard_tipo_ruolo_tipi_indirizzo)   
> [`script.fn_get_indirizzo`](/dbzero/script/funzioni/fn_get_indirizzo)    

---
### 🎯 Scopo Principale
(latest review 19-12-25)
La tabella **`config.tipi_ruolo_tipi_indirizzo`** rappresenta la **matrice di configurazione** che definisce:

* **quali tipi di indirizzo** sono **ammessi** per ogni **tipo di ruolo**
  (es. Gestore, Cliente, Fornitore, …),
* quali sono **obbligatori**,
* quali possono usare un **fallback** su un altro tipo indirizzo.

In pratica, è il punto in cui dichiari:

> “Per il ruolo *Gestore*, questi tipi di indirizzo sono permessi, questi sono obbligatori, e se manca questo tipo usa quest’altro come fallback.”

Questa tabella governa quindi:

* la **validazione** degli indirizzi (`anagrafiche.indirizzi`) tramite trigger *guard*,
* la **logica di fallback** utilizzata da funzioni di lookup come `script.fn_get_indirizzo`.

---

### Ruolo nel Modello Dati

Il modello completo ruota intorno a questa catena:

* `config.tipi_ruoli` → definisce **tipi ruolo** (CL, FO, GE, …)
* `config.tipi_indirizzi` → definisce **tipi indirizzo** (RES, SEDELEG, FATT, FORNITURA, …)
* `anagrafiche.soggetti_ruoli` → collega un soggetto reale a un tipo ruolo
* **`config.tipi_ruolo_tipi_indirizzo`** → dice **quali tipi indirizzo sono validi per quel tipo ruolo**
* `anagrafiche.indirizzi` → contiene gli indirizzi effettivi per `soggetto_ruolo`

Senza questa matrice si avrebbe:

* o libertà totale (rischio di combinazioni incoerenti),
* o regole hardcoded nelle funzioni.

Con `config.tipi_ruolo_tipi_indirizzo`:

* le regole sono **dati di configurazione**, versionabili e modificabili senza toccare il codice,
* la logica applicativa (trigger/funzioni) resta generica e guidata dai dati.

---

### 🧾 Struttura – Attributi principali

| Colonna                      | Tipo        | Obblig. | Descrizione sintetica                                                                |
| ---------------------------- | ----------- | ------- | ------------------------------------------------------------------------------------ |
| `id`                         | bigint      | Sì      | Chiave primaria tecnica.                                                             |
| `tipo_ruolo_id`              | bigint      | Sì      | FK → `config.tipi_ruoli.id`. Identifica il **tipo ruolo** (es. Gestore, Cliente, …). |
| `tipo_indirizzo_id`          | bigint      | Sì      | FK → `config.tipi_indirizzi.id`. Tipo indirizzo ammesso per quel ruolo.              |
| `obbligatorio`               | boolean     | Sì      | Se `TRUE`, il ruolo deve avere almeno un indirizzo di quel tipo.                     |
| `valido_dal` / `valido_al`   | date        | No      | Finestra temporale di validità della regola (permite versioning nel tempo).          |
| `attivo`                     | boolean     | Sì      | Flag di attivazione logica della regola.                                             |
| `fallback_tipo_indirizzo_id` | bigint      | No      | FK → `config.tipi_indirizzi.id`. Tipo indirizzo da usare come **fallback**.          |
| `meta`                       | jsonb       | Sì      | Metadati estendibili (note, flag, configurazioni future).                            |
| `user_insert`, `user_update` | text        | Sì      | Audit utente.                                                                        |
| `data_insert`, `data_update` | timestamptz | Sì      | Audit temporale.                                                                     |
| `storicizza`                 | boolean     | Sì      | Flag per eventuali trigger di storicizzazione.                                       |

**Vincoli principali:**

* `UNIQUE (tipo_ruolo_id, tipo_indirizzo_id)`
  → ogni combinazione ruolo/tipo_indirizzo è definita una sola volta.
* `CHECK valido_dal / valido_al`
  → impedisce intervalli invertiti.
* `CHECK fallback_not_self`
  → il fallback non può essere uguale al tipo principale.

---

### Regole di Funzionamento

 **1️⃣ Matrice presente vs assente**

La logica implementata dal *guard* sugli indirizzi è:

* Se **per un dato `tipo_ruolo` NON esistono righe** in `config.tipi_ruolo_tipi_indirizzo`
  ➜ gli indirizzi sono considerati **liberi**:
  **si accettano tutti i tipi indirizzo** (nessuna restrizione dalla matrice).

* Se invece **esiste almeno una riga** per quel `tipo_ruolo`
  ➜ la matrice è attiva e viene applicato il vincolo:
  **si accettano solo i `tipo_indirizzo_id` presenti in tabella**, con:

  * `attivo = TRUE`
  * `valido_dal/valido_al` compatibili con la data corrente.

Questa logica è gestita da:

* [`anagrafiche.trgfn_indirizzi_guard_tipo_ruolo_tipi_indirizzo`](/dbzero/anagrafiche/funzioni/trgfn_indirizzi_guard_tipo_ruolo_tipi_indirizzo)

che blocca l’inserimento/update di indirizzi non coerenti con la matrice.

---

 **2️⃣ Fallback tra tipi indirizzo**

La colonna `fallback_tipo_indirizzo_id` permette di definire **una catena di fallback** per i casi in cui **manca l’indirizzo del tipo richiesto**.

Esempio tipico per il ruolo **Gestore (GE)**:

| tipo_ruolo | tipo_indirizzo | obbligatorio | fallback_tipo_indirizzo |
| ---------- | -------------- | ------------ | ----------------------- |
| GE         | SEDELEG        | TRUE         | NULL                    |
| GE         | SEDEOP         | FALSE        | SEDELEG                 |
| GE         | FATT           | TRUE         | NULL                    |
| GE         | FORNITURA      | FALSE        | SEDEOP                  |

Con questa configurazione:

* se chiedi **SEDEOP** e non esiste un indirizzo SEDEOP,

  * la funzione `script.fn_get_indirizzo` sa che può usare **SEDELEG** come sostituto;
* se chiedi **FORNITURA** e non esiste,

  * può provare prima **FORNITURA**, poi **SEDEOP**, che a sua volta può cadere su **SEDELEG**, in base alla logica implementata.

> La logica di fallback **non** è nel trigger, ma nelle funzioni di lookup/servizio
> (es. `script.fn_get_indirizzo`), che leggono la configurazione dalla matrice.

---

### Esempi d’Uso (concettuali)

 **✔ Ruolo Cliente**

* Ammessi:

  * RES, DOMFISC, FATT, SPED, POSTA
* Obbligatori:

  * FATT (almeno un indirizzo di fatturazione)
* Esempio di fallback:

  * FATT → DOMFISC,
  * SPED → RES

 **✔ Ruolo Gestore**

* Ammessi:

  * SEDELEG, SEDEOP, FATT, FORNITURA
* Obbligatori:

  * SEDELEG, FATT
* Fallback:

  * SEDEOP → SEDELEG
  * FORNITURA → SEDEOP

 **✔ Ruolo senza matrice**

* Nessuna riga in `config.tipi_ruolo_tipi_indirizzo` per quel `tipo_ruolo`
  ➜ indirizzi **non vincolati dalla matrice**, utili in scenari di migrazione/adozione graduale.

---

### Vantaggi Operativi

* **Configurazione centrale delle regole**
  Le regole ruolo ↔ tipi indirizzo sono dati, non codice. Si possono modificare e versionare facilmente.

* **Separazione responsabilità**

  * Lo schema `config` definisce **che cosa è permesso/obbligatorio**.
  * Lo schema `anagrafiche` contiene i dati operativi e applica le regole tramite trigger/funzioni.

* **Supporto a scenari reali complessi**

  * Ruoli che richiedono indirizzi diversi per adempimenti fiscali, logistici, contrattuali.
  * Gestione di fallback coerente (es. usare la sede legale se manca quella operativa).

* **Gradualità e backwards compatibility**

  * Per i ruoli senza configurazione, il sistema continua a funzionare come prima (indirizzi liberi).
  * È possibile introdurre la matrice ruolo per ruolo, senza “rompere” l’esistente.

---

> **"`config.tipi_ruolo_tipi_indirizzo` è la regia delle combinazioni ruolo–indirizzo: decide cosa è ammesso, cosa è obbligatorio e come comportarsi quando un indirizzo manca, lasciando alle funzioni solo il compito di eseguire le regole."**

{% include-markdown "signature-core.md" %}
