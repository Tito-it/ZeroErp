## 🌱 Documentazione Concettuale – Tabella `config.tipi_indirizzi_allowed`

> 👀 **Vedi anche**
>
> **Approfondimento tabelle:**
>
> * [`config.tipi_indirizzi`](/dbzero/config/tabelle/tipi_indirizzi)
>
> **Tabelle / ambiti operativi (documenti):**
>
> * `vendite.fatture` / righe documento (ambito **FATTURE**)
> * `vendite.ordini` (ambito **ORDINI**)
> * `vendite.ddt` (ambito **DDT**)
> * `vendite.preventivi` (ambito **PREVENTIVI**)
>
> **Da non confondere con:**
>
> * [`config.tipi_soggetto_dettaglio_tipi_indirizzo`](/dbzero/config/tabelle/tipi_soggetto_dettaglio_tipi_indirizzo)
> * [`config.tipi_ruolo_tipi_indirizzo`](/dbzero/config/tabelle/tipi_ruolo_tipi_indirizzo)

---

### 🎯 Scopo Principale
(Ultima review 19-12-25)

La tabella **`config.tipi_indirizzi_allowed`** definisce **quali tipi di indirizzo sono ammessi (e/o obbligatori) all’interno dei documenti**.

✅ Qui l’oggetto non è “che indirizzi può avere un soggetto”, ma:

> “Quando emetto/gestisco un documento (fattura, ordine, DDT, preventivo), quali *tipi di indirizzo* posso usare nei campi indirizzo del documento?”

È quindi una matrice **indirizzo ↔ ambito documento**.

Questa tabella serve soprattutto per:

* **standardizzare** la compilazione degli indirizzi nei documenti,
* prevenire l’uso di tipi indirizzo non previsti (es. RES su una fattura, se non ammesso),
* gestire eventuali controlli di **obbligatorietà** per ambito (es. FATT richiede un indirizzo FATT o equivalente).

---

### 🧩 Ruolo nel Modello Dati

Nel modello Zero ERP esistono **almeno due famiglie di regole** sugli indirizzi:

 **A) Regole “anagrafiche” (soggetti / ruoli)**

Queste stabiliscono **quali tipi indirizzo sono ammessi per un soggetto** (o per il suo ruolo) e come recuperarli.

* `config.tipi_soggetto_dettaglio_tipi_indirizzo`
* `config.tipi_ruolo_tipi_indirizzo`

➡️ Sono regole **sull’anagrafica**.
 
 **B) Regole “documentali” (documenti)**

Queste stabiliscono **quali tipi indirizzo sono ammessi nei documenti**, indipendentemente dal fatto che il soggetto abbia anche altri indirizzi.

* **`config.tipi_indirizzi_allowed`**

➡️ Sono regole **sui documenti**.

> 📌 In pratica: un soggetto potrebbe avere molti indirizzi (RES, DOMFISC, SPED…), ma un certo documento potrebbe accettare solo alcuni tipi (es. FATT + SPED) per evitare errori di processo.

---

### 🧾 Struttura – Attributi principali

| Colonna             | Tipo        | Obblig. | Descrizione sintetica                                                                                              |
| ------------------- | ----------- | ------- | ------------------------------------------------------------------------------------------------------------------ |
| `ambito`            | text        | Sì      | Ambito documento (FATTURE, ORDINI, DDT, PREVENTIVI).                                                               |
| `tipo_indirizzo_id` | integer     | Sì      | FK → `config.tipi_indirizzi.id`. Tipo indirizzo ammesso nell’ambito.                                               |
| `obbligatorio`      | boolean     | Sì      | Se `TRUE`, nell’ambito deve essere presente almeno un indirizzo di quel tipo (se il modello documento lo prevede). |
| `attivo`            | boolean     | Sì      | Abilitazione logica della regola.                                                                                  |
| `data_insert`       | timestamptz | Sì      | Audit temporale inserimento.                                                                                       |
| `user_insert`       | text        | Sì      | Audit utente inserimento.                                                                                          |
| `data_update`       | timestamptz | Sì      | Audit temporale modifica.                                                                                          |
| `user_update`       | text        | Sì      | Audit utente modifica.                                                                                             |

**Chiave primaria:**

* `PRIMARY KEY (ambito, tipo_indirizzo_id)`
  → una combinazione ambito/tipo_indirizzo è definita una sola volta.

**Vincoli principali:**

* `CHECK (ambito IN [...])`
  → garantisce che l’ambito sia uno dei valori previsti (FATTURE, ORDINI, DDT, PREVENTIVI).
* FK su `tipo_indirizzo_id`
  → assicura coerenza col dominio `config.tipi_indirizzi`.

---

### ⚙️ Regole di Funzionamento

 **1️⃣ Ammissibilità per ambito**

Per ogni valore di `ambito`, la tabella elenca i `tipo_indirizzo_id` che:

* possono essere usati nei documenti di quell’ambito,
* solo se `attivo = TRUE`.

Questo abilita controlli del tipo:

* “in FATTURE posso usare solo FATT e SPED”
* “in DDT posso usare solo SPED/FORNITURA”

---

  **2️⃣ Obbligatorietà per ambito**

Quando `obbligatorio = TRUE`, significa che:

* in quell’ambito, un certo tipo indirizzo è considerato **necessario**.

> ⚠️ Nota: l’effettiva applicazione dipende dal modello documento (se esiste una tabella `documento_indirizzi` con più righe, oppure colonne dedicate). In ogni caso, questa tabella è la **fonte configurativa** per decidere cosa validare.

---

### 🔍 Esempi d’Uso (concettuali)

 **✔ Ambito FATTURE**

* Ammessi: FATT, SPED (eventualmente DOMFISC se previsto)
* Obbligatori: FATT

➡️ Riduce ambiguità: una fattura non dovrebbe “prendere” RES se non previsto.

 **✔ Ambito DDT**

* Ammessi: SPED, FORNITURA
* Obbligatori: SPED (se il tuo flusso lo richiede)

➡️ Coerenza logistica: indirizzo consegna sempre valorizzato.

---

### 💡 Vantaggi Operativi

* **Chiarezza**: regole indirizzi sui documenti separate dalle regole sugli indirizzi del soggetto.
* **Riduzione errori**: impedisce compilazioni incoerenti e “scelte libere” non controllate.
* **Configurazione centrale**: cambi le regole senza toccare codice.
* **Supporto multi-documento**: ogni ambito può avere set di tipi indirizzo differenti.

> 🧠 **"`config.tipi_indirizzi_allowed` è la regia dei tipi indirizzo utilizzabili nei documenti: non decide quali indirizzi può avere un soggetto, ma quali indirizzi sono accettati e richiesti nei flussi documentali (fatture, ordini, DDT, preventivi)."**

{% include-markdown "signature-core.md" %}
