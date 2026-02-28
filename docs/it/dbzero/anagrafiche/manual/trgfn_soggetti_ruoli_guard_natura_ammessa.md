## 📘 Documentazione Funzione – `anagrafiche.trgfn_soggetti_ruoli_guard_natura_ammessa`

> 👀 **Vedi anche**
>
> **Tabelle anagrafiche / config:**
>
> * [`anagrafiche.soggetti_ruoli`](/dbzero/anagrafiche/tabelle/soggetti_ruoli)
> * [`anagrafiche.soggetti`](/dbzero/anagrafiche/tabelle/soggetti)
> * [`config.tipi_ruoli`](/dbzero/config/tabelle/tipi_ruoli)
> * [`config.tipi_soggetto`](/dbzero/config/tabelle/tipi_soggetto)
> * [`config.tipi_soggetto_dettaglio`](/dbzero/config/tabelle/tipi_soggetto_dettaglio)
> * [`config.tipi_ruoli_nature_ammesse`](/dbzero/config/tabelle/tipi_ruoli_nature_ammesse)
>
> **Funzioni / trigger di supporto:**
>
> * [`script.fn_log_and_raise_error`](/dbzero/script/funzioni/fn_log_and_raise_error)

---

### 🎯 Scopo Principale
(latest review 28-02-26)
La funzione **`anagrafiche.trgfn_soggetti_ruoli_guard_natura_ammessa`** e una **trigger function di tipo "guard"** che:

* controlla gli **inserimenti / aggiornamenti** sulla tabella
  [`anagrafiche.soggetti_ruoli`](/dbzero/anagrafiche/tabelle/soggetti_ruoli),
* verificando la coerenza tra:

  * la **natura del soggetto** (PF, PG, ENC — derivata dalla catena `soggetti.tipo_soggetto_dettaglio_id` → `tipi_soggetto_dettaglio.tipo_soggetto_id`), e
  * il **tipo ruolo** che si sta assegnando

  rispetto alla **matrice di configurazione**:

  * [`config.tipi_ruoli_nature_ammesse`](/dbzero/config/tabelle/tipi_ruoli_nature_ammesse).

La funzione implementa una logica **adattiva** (pattern "matrice assente = libero"):

* Se **per un certo `tipo_ruolo` non esistono righe** in `config.tipi_ruoli_nature_ammesse`
  → le nature sono considerate **"libere"**: si accettano **tutti** i tipi di soggetto.
* Se invece **il `tipo_ruolo` ha una matrice definita**
  → si accettano **solo** le nature **esplicitamente configurate**, attive e nel range di validita.

In caso di violazione, la funzione richiama **`script.fn_log_and_raise_error`** e blocca l'operazione.

---

### 🧱 Collegamenti principali

* **Tabelle coinvolte direttamente:**

  * [`anagrafiche.soggetti_ruoli`](/dbzero/anagrafiche/tabelle/soggetti_ruoli) — tabella su cui e definito il trigger.
  * [`anagrafiche.soggetti`](/dbzero/anagrafiche/tabelle/soggetti) — contiene `tipo_soggetto_dettaglio_id`.
  * [`config.tipi_soggetto_dettaglio`](/dbzero/config/tabelle/tipi_soggetto_dettaglio) — contiene `tipo_soggetto_id` (la natura).
  * [`config.tipi_ruoli`](/dbzero/config/tabelle/tipi_ruoli) — catalogo dei tipi ruolo.
  * [`config.tipi_soggetto`](/dbzero/config/tabelle/tipi_soggetto) — catalogo delle nature (PF, PG, ENC).
  * [`config.tipi_ruoli_nature_ammesse`](/dbzero/config/tabelle/tipi_ruoli_nature_ammesse) — matrice ruolo ↔ natura ammessa.

* **Funzioni di supporto:**

  * [`script.fn_log_and_raise_error`](/dbzero/script/funzioni/fn_log_and_raise_error) — centralizza logging + raise exception.

---

### 🧾 Firma della funzione e trigger associato

**Funzione (schema `anagrafiche`):**

```sql
CREATE OR REPLACE FUNCTION anagrafiche.trgfn_soggetti_ruoli_guard_natura_ammessa()
RETURNS trigger
LANGUAGE plpgsql;
```

**Trigger su `anagrafiche.soggetti_ruoli`:**

```sql
CREATE OR REPLACE TRIGGER trg_soggetti_ruoli_a10_guard_natura_ammessa_ins_upd
    BEFORE INSERT OR UPDATE OF tipo_ruolo_id
    ON anagrafiche.soggetti_ruoli
    FOR EACH ROW
    EXECUTE FUNCTION anagrafiche.trgfn_soggetti_ruoli_guard_natura_ammessa();
```

📌 *Il trigger scatta:*

* *sempre in INSERT*
* *solo in UPDATE se cambia `tipo_ruolo_id`*

---

### 🧩 Contesto e parametri logici

Essendo una trigger function, non ha parametri espliciti. Utilizza:

| Elemento                         | Descrizione                                                     |
| -------------------------------- | --------------------------------------------------------------- |
| `TG_OP`                          | Tipo operazione: INSERT / UPDATE / DELETE                       |
| `NEW`                            | Record nuovo (in INSERT/UPDATE)                                 |
| `NEW.soggetto_id`                | Identifica il soggetto a cui si assegna il ruolo                |
| `NEW.tipo_ruolo_id`              | Tipo ruolo da assegnare (FK verso `config.tipi_ruoli`)          |

---

### 🔍 Logica di funzionamento (semplificata)

1️⃣ **DELETE** → nessun controllo → `RETURN OLD`.

2️⃣ Recupera `tipo_soggetto_dettaglio_id` dal soggetto (`anagrafiche.soggetti`).

3️⃣ Verifica se esiste almeno una riga in matrice per `NEW.tipo_ruolo_id`:

* Se **NO** → nature "libere" → `RETURN NEW` (nessuna restrizione).

4️⃣ Se la matrice esiste MA `tipo_soggetto_dettaglio_id IS NULL`:

* → errore `E_RUOLO_NATURA_TIPO_DET_NULL`: impossibile verificare la natura del soggetto.

5️⃣ Risale alla natura (`tipo_soggetto_id`) via `config.tipi_soggetto_dettaglio`.

6️⃣ Verifica la presenza di una riga in matrice con:
* `tipo_ruolo_id = NEW.tipo_ruolo_id`
* `tipo_soggetto_id` = natura del soggetto
* `attivo = true`
* `valido_dal/valido_al` compatibili con `CURRENT_DATE`

* Se trovata → `RETURN NEW`.
* Se **non trovata** → errore `E_RUOLO_NATURA_NON_AMMESSA`.

---

### 🧪 Esempi specifici

#### ✔ Esempio valido (natura ammessa)

* Soggetto SC (natura PG) + ruolo GE → matrice prevede GE/PG → **OK**

#### ❌ Esempio non valido (natura non ammessa)

* Soggetto PR (natura PF) + ruolo GE → matrice prevede solo GE/PG → **BLOCCATO**

#### ❌ Esempio non valido (tipo_soggetto_dettaglio mancante)

* Soggetto con `tipo_soggetto_dettaglio_id = NULL` + ruolo GE → matrice esiste per GE → **BLOCCATO** (E_RUOLO_NATURA_TIPO_DET_NULL)

#### ✔ Esempio senza matrice

* Ruolo senza righe in matrice → qualunque natura → **OK**

---

### ⚠️ Note Tecniche

* La funzione e **coerente con il pattern "guard"** usato in Zero ERP (fase `_a10_`, fail-fast).
* Non modifica i dati, si limita a validarli.
* Segue lo stesso pattern di [`trgfn_indirizzi_guard_tipo_ruolo_tipi_indirizzo`](/dbzero/anagrafiche/funzioni/trgfn_indirizzi_guard_tipo_ruolo_tipi_indirizzo) per la logica "matrice assente = libero".
* In caso di errore, il messaggio e gestito da `script.fn_log_and_raise_error` che garantisce logging centralizzato.

---

### 🏁 Best Practice

✔ Configurare la matrice per ogni ruolo che ha vincoli di natura.
✔ Assicurarsi che `tipo_soggetto_dettaglio_id` sia valorizzato sui soggetti prima di assegnare ruoli vincolati.
✔ Nei test (pgTAP) validare:

* Inserimento ammesso (natura corretta)
* Inserimento non ammesso (natura non prevista)
* Caso senza matrice (libero)
* Caso tipo_soggetto_dettaglio mancante (errore)

---

📅 *Aggiornato: 28/02/2026*

{% include-markdown "signature-core.md" %}
