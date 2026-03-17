## 📘 Documentazione Concettuale – Tabella `config.tipi_ruoli_nature_ammesse`

> 👀 **Vedi anche**
>
**Tabelle di dominio:**
>
[`config.tipi_ruoli`](/dbzero/config/tabelle/tipi_ruoli)
> [`config.tipi_soggetto`](/dbzero/config/tabelle/tipi_soggetto)
> [`config.tipi_soggetto_dettaglio`](/dbzero/config/tabelle/tipi_soggetto_dettaglio)
>
**Tabelle anagrafiche collegate:**
>
[`anagrafiche.soggetti`](/dbzero/anagrafiche/tabelle/soggetti)
> [`anagrafiche.soggetti_ruoli`](/dbzero/anagrafiche/tabelle/soggetti_ruoli)
>
**Funzioni / trigger collegati:**
>
[`anagrafiche.trgfn_soggetti_ruoli_guard_natura_ammessa`](/dbzero/anagrafiche/funzioni/trgfn_soggetti_ruoli_guard_natura_ammessa)

---

### 🎯 Scopo Principale
(latest review 28-02-26)
La tabella **`config.tipi_ruoli_nature_ammesse`** rappresenta la **matrice di configurazione** che definisce:

* **quali nature di soggetto** (PF, PG, ENC) sono **ammesse** per ogni **tipo di ruolo**
  (es. Gestore, Cliente, Fornitore, Risorsa Umana, …).

In pratica, è il punto in cui dichiari:

> "Per il ruolo *Gestore*, solo i soggetti di natura *PG* possono essere associati.
> Per il ruolo *Cliente*, sono ammesse le nature *PF*, *PG* e *ENC*."

Questa tabella governa la **validazione** degli inserimenti in `anagrafiche.soggetti_ruoli` tramite il trigger guard:

* [`anagrafiche.trgfn_soggetti_ruoli_guard_natura_ammessa`](/dbzero/anagrafiche/funzioni/trgfn_soggetti_ruoli_guard_natura_ammessa)

---

### Ruolo nel Modello Dati

Il modello completo ruota intorno a questa catena:

* `config.tipi_ruoli` → definisce i **tipi ruolo** (CL, FO, GE, RIS_UMANA, …)
* `config.tipi_soggetto` → definisce le **nature soggetto** (PF, PG, ENC)
* `config.tipi_soggetto_dettaglio` → dettaglio per paese (PR, DI, SC, SP, ENC)
* `anagrafiche.soggetti` → contiene `tipo_soggetto_dettaglio_id` che risale alla natura
* `anagrafiche.soggetti_ruoli` → collega un soggetto reale a un tipo ruolo
* **`config.tipi_ruoli_nature_ammesse`** → dice **quali nature sono valide per quel tipo ruolo**

Senza questa matrice si avrebbe:

* libertà totale: un soggetto PF (persona fisica) potrebbe diventare Gestore o Emittente Fiscale,
* una PG potrebbe essere assegnata come Risorsa Umana.

Con `config.tipi_ruoli_nature_ammesse`:

* le regole sono **dati di configurazione**, versionabili e modificabili senza toccare il codice,
* la logica applicativa (trigger) resta generica e guidata dai dati.

---

### 🧾 Struttura – Attributi principali

| Colonna                      | Tipo        | Obblig. | Descrizione sintetica                                                                     |
| ---------------------------- | ----------- | ------- | ----------------------------------------------------------------------------------------- |
| `id`                         | bigint      | Si      | Chiave primaria tecnica (IDENTITY).                                                       |
| `tipo_ruolo_id`              | integer     | Si      | FK → `config.tipi_ruoli.id`. Identifica il **tipo ruolo** (es. GE, CL, FO, …).           |
| `tipo_soggetto_id`           | varchar     | Si      | FK → `config.tipi_soggetto.id`. Natura ammessa per quel ruolo (PF, PG, ENC).              |
| `attivo`                     | boolean     | Si      | Flag di attivazione logica della regola. Default `true`.                                  |
| `valido_dal` / `valido_al`   | date        | No      | Finestra temporale di validita della regola (permette versioning nel tempo).              |
| `meta`                       | jsonb       | Si      | Metadati estendibili (note, flag, configurazioni future). Default `'{}'`.                 |
| `user_insert`, `user_update` | text        | Si      | Audit utente.                                                                             |
| `data_insert`, `data_update` | timestamptz | Si      | Audit temporale.                                                                          |
| `storicizza`                 | boolean     | Si      | Flag per eventuali trigger di storicizzazione. Default `false`.                           |

**Vincoli principali:**

* `UNIQUE (tipo_ruolo_id, tipo_soggetto_id)`
  → ogni combinazione ruolo/natura e definita una sola volta.
* `CHECK valido_al >= valido_dal` (o NULL)
  → impedisce intervalli invertiti.
* `FK tipo_ruolo_id` → `config.tipi_ruoli(id)` ON DELETE RESTRICT
* `FK tipo_soggetto_id` → `config.tipi_soggetto(id)` ON DELETE RESTRICT

---

### Regole di Funzionamento

 **1️⃣ Matrice presente vs assente**

La logica implementata dal guard su `anagrafiche.soggetti_ruoli` e:

* Se **per un dato `tipo_ruolo` NON esistono righe** in `config.tipi_ruoli_nature_ammesse`
  → le nature sono considerate **libere**:
  **si accettano tutti i tipi di soggetto** (nessuna restrizione dalla matrice).

* Se invece **esiste almeno una riga** per quel `tipo_ruolo`
  → la matrice e attiva e viene applicato il vincolo:
  **si accettano solo i `tipo_soggetto_id` presenti in tabella**, con:

  * `attivo = TRUE`
  * `valido_dal/valido_al` compatibili con la data corrente.

 **2️⃣ Soggetto senza tipo_soggetto_dettaglio**

Se il soggetto ha `tipo_soggetto_dettaglio_id = NULL` e il ruolo ha una matrice configurata,
l'assegnazione viene **bloccata** con errore `E_RUOLO_NATURA_TIPO_DET_NULL`.

Il soggetto deve avere un tipo dettaglio configurato prima di poter ricevere un ruolo vincolato.

---

### Esempi d'Uso (concettuali)

 **✔ Ruolo Gestore (GE)**

* Ammesso: solo **PG**
* Una societa di capitali (SC → PG) puo diventare Gestore → OK
* Un privato (PR → PF) non puo diventare Gestore → BLOCCATO

 **✔ Ruolo Cliente (CL)**

* Ammessi: **PF**, **PG**, **ENC**
* Qualunque natura di soggetto puo essere Cliente → OK per tutti

 **✔ Ruolo Risorsa Umana (RIS_UMANA)**

* Ammesso: solo **PF**
* Un privato (PR → PF) puo essere Risorsa Umana → OK
* Una societa (SC → PG) non puo essere Risorsa Umana → BLOCCATO

 **✔ Ruolo senza matrice**

* Nessuna riga in `config.tipi_ruoli_nature_ammesse` per quel `tipo_ruolo`
  → nature **non vincolate dalla matrice**, utile in scenari di migrazione/adozione graduale.

---

### Seed Data Attuale (19 righe)

| Ruolo          | Nature Ammesse | Note                              |
| -------------- | -------------- | --------------------------------- |
| GE (Gestore)   | PG             | Solo persone giuridiche           |
| EF (Em. Fisc.) | PG             | Solo persone giuridiche           |
| RIS_UMANA      | PF             | Solo persone fisiche              |
| CL (Cliente)   | PF, PG, ENC    | Tutte le nature                   |
| FO (Fornitore) | PF, PG, ENC    | Tutte le nature                   |
| VE (Venditore) | PF, PG         | Fisiche e giuridiche              |
| DI (Distrib.)  | PG             | Solo persone giuridiche           |
| RE (Referente) | PF, PG         | Fisiche e giuridiche              |
| VT (Vettore)   | PF, PG         | Fisiche e giuridiche              |
| BANK (Banca)   | PG, ENC        | Giuridiche ed enti                |
| PSP (Prest.SP) | PG             | Solo persone giuridiche           |

---

### Vantaggi Operativi

* **Configurazione centrale delle regole**
  Le regole ruolo ↔ natura soggetto sono dati, non codice. Si possono modificare e versionare facilmente.

* **Separazione responsabilita**

  * Lo schema `config` definisce **che cosa e permesso**.
  * Lo schema `anagrafiche` contiene i dati operativi e applica le regole tramite trigger.

* **Supporto a scenari reali**

  * Un Gestore deve essere una persona giuridica (societa).
  * Una Risorsa Umana deve essere una persona fisica.
  * Un Cliente puo essere qualunque tipo di soggetto.

* **Gradualita e backwards compatibility**

  * Per i ruoli senza configurazione, il sistema continua a funzionare come prima (nature libere).
  * E possibile introdurre la matrice ruolo per ruolo, senza "rompere" l'esistente.

---

> **"`config.tipi_ruoli_nature_ammesse` e la regia delle combinazioni ruolo–natura soggetto: decide quale tipo di soggetto puo ricoprire un ruolo, lasciando al trigger guard solo il compito di eseguire le regole."**

{% include-markdown "signature-core.md" %}
