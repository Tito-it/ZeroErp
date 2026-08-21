## 📘 Documentazione Funzione – `anagrafiche.trgfn_indirizzi_guard_tipo_ruolo_tipi_indirizzo`

> 👀 **Vedi anche**
>
**Tabelle anagrafiche / config:**
>
[`anagrafiche.indirizzi`](/dbzero/anagrafiche/tabelle/indirizzi)
> [`anagrafiche.soggetti_ruoli`](/dbzero/anagrafiche/tabelle/soggetti_ruoli)
> [`config.tipi_ruoli`](/dbzero/config/tabelle/tipi_ruoli)
> [`config.tipi_indirizzi`](/dbzero/config/tabelle/tipi_indirizzi)
> [`config.tipi_ruolo_tipi_indirizzo`](/dbzero/config/tabelle/tipi_ruolo_tipi_indirizzo)
>
**Funzioni / trigger di supporto:**
>
[`script.fn_log_and_raise_error`](/dbzero/script/funzioni/fn_log_and_raise_error)
> (eventuale) [`anagrafiche.fn_get_indirizzo_preferito_*`](/dbzero/anagrafiche/funzioni/)

---
### 🎯 Scopo Principale
(latest review 30-11-25)
La funzione **`anagrafiche.trgfn_indirizzi_guard_tipo_ruolo_tipi_indirizzo`** è una **trigger function di tipo “guard”** che:

* controlla gli **inserimenti / aggiornamenti** sulla tabella
  [`anagrafiche.indirizzi`](/dbzero/anagrafiche/tabelle/indirizzi),
* verificando la coerenza tra:

  * il **tipo ruolo** associato al record (`soggetto_ruolo_id` → `config.tipi_ruoli`), e
  * il **tipo indirizzo** (`tipo_indirizzo_id` → `config.tipi_indirizzi`)

  rispetto alla **matrice di configurazione**:

  * [`config.tipi_ruolo_tipi_indirizzo`](/dbzero/config/tabelle/tipi_ruolo_tipi_indirizzo).

La funzione implementa una logica **adattiva**:

* Se **per un certo `tipo_ruolo` non esistono righe** in `config.tipi_ruolo_tipi_indirizzo`
  ➜ gli indirizzi sono considerati **“liberi”**: si accettano **tutti** i tipi indirizzo.
* Se invece **il `tipo_ruolo` ha una matrice definita**
  ➜ si accettano **solo** i `tipo_indirizzo_id` **esplicitamente configurati**, attivi e nel range di validità.

In caso di violazione, la funzione richiama **`script.fn_log_and_raise_error`** e blocca l’operazione, garantendo che il dato rispetti la configurazione di dominio.

---

### Collegamenti principali

* **Tabelle coinvolte direttamente:**

  * [`anagrafiche.indirizzi`](/dbzero/anagrafiche/tabelle/indirizzi) – tabella su cui è definito il trigger.
  * [`anagrafiche.soggetti_ruoli`](/dbzero/anagrafiche/tabelle/soggetti_ruoli) – contiene il collegamento `soggetto` ⇄ `tipo_ruolo`.
  * [`config.tipi_ruoli`](/dbzero/config/tabelle/tipi_ruoli) – catalogo dei tipi ruolo (CL, FO, GE, ecc.).
  * [`config.tipi_indirizzi`](/dbzero/config/tabelle/tipi_indirizzi) – catalogo dei tipi indirizzo (RES, FATT, FORNITURA, …).
  * [`config.tipi_ruolo_tipi_indirizzo`](/dbzero/config/tabelle/tipi_ruolo_tipi_indirizzo) – matrice ruolo ↔ tipo indirizzo + fallback.

* **Funzioni/trigger di supporto:**

  * [`script.fn_log_and_raise_error`](/dbzero/script/funzioni/fn_log_and_raise_error) – centralizza logging + raise exception.

---

### 🧾 Firma della funzione e trigger associato

**Funzione (schema `anagrafiche`):**

```sql
CREATE OR REPLACE FUNCTION anagrafiche.trgfn_indirizzi_guard_tipo_ruolo_tipi_indirizzo()
RETURNS trigger
LANGUAGE plpgsql;
```

**Trigger su `anagrafiche.indirizzi`:**

```sql
CREATE OR REPLACE TRIGGER trg_indirizzi_guard_tipo_ruolo_tipi_indirizzo_ins_upd
    BEFORE INSERT OR UPDATE OF tipo_indirizzo_id
    ON anagrafiche.indirizzi
    FOR EACH ROW
    EXECUTE FUNCTION anagrafiche.trgfn_indirizzi_guard_tipo_ruolo_tipi_indirizzo();
```

📌 *Il trigger scatta:*

* *sempre in INSERT*
* *solo in UPDATE se cambia `tipo_indirizzo_id`*

---

### Contesto e parametri logici

Essendo una trigger function, non ha parametri espliciti. Utilizza:

| Elemento                | Descrizione                                                     |
| ----------------------- | --------------------------------------------------------------- |
| `TG_OP`                 | Tipo operazione: INSERT / UPDATE / DELETE                       |
| `NEW`                   | Record nuovo (in INSERT/UPDATE)                                 |
| `OLD`                   | Record precedente (in DELETE/UPDATE)                            |
| `NEW.soggetto_ruolo_id` | Identifica il `tipo_ruolo` tramite `anagrafiche.soggetti_ruoli` |
| `NEW.tipo_indirizzo_id` | Tipo indirizzo (FK verso `config.tipi_indirizzi`)               |
| `NEW.tx_id`             | Identificativo transazione logica (se previsto in tabella)      |

🔎 Se `NEW.soggetto_ruolo_id` o `NEW.tipo_indirizzo_id` sono NULL → **nessun controllo**.

---

### Logica di funzionamento (semplificata)

1️⃣ **DELETE** → nessun controllo.
2️⃣ Se `NEW.soggetto_ruolo_id` *oppure* `NEW.tipo_indirizzo_id` è NULL → `RETURN NEW`.
3️⃣ Recupera il `tipo_ruolo_id` da `anagrafiche.soggetti_ruoli`.
4️⃣ Verifica se esiste almeno una riga in matrice:

* Se **NO** → indirizzi “liberi” → `RETURN NEW`.
* Se **SÌ** → si accetta solo se presente una riga attiva & valida.

📍 Se nessuna riga valida trovata → chiamata a `script.fn_log_and_raise_error(...)` + `RAISE EXCEPTION`.

---

### Esempi specifici

#### ✔ Esempio valido (matrice esistente)

* `tipo_ruolo = GE`, `tipo_indirizzo = FATT` → ammesso → OK

#### ❌ Esempio non valido

* `tipo_ruolo = GE`, `tipo_indirizzo = RES` → non previsto → errore bloccante

#### ✔ Esempio senza matrice

* `tipo_ruolo = XX` (nessuna riga in matrice) → qualunque `tipo_indirizzo_id` → OK

---

### ⚠️ Note Tecniche

* La funzione è **coerente con il pattern “guard”** usato in Zero ERP.
* Non modifica i dati, si limita a validarli.
* La logica di fallback indirizzo *non è gestita qui* → demandata a funzioni applicative (es. `fn_get_indirizzo_preferito`).
* In caso di errore, il messaggio è gestito da `script.fn_log_and_raise_error` che garantisce logging centralizzato.

---

### 🏁 Best Practice

✔ Utilizzare *sempre* questo trigger per mantenere consistenza dei dati anagrafici.
✔ Definire correttamente la matrice per ogni tipo ruolo per evitare inserimenti errati.
✔ Nei test (pgTAP/file di test) validare:

* Inserimento ammesso
* Inserimento non ammesso
* Caso senza matrice

---

📅 *Aggiornato: 30/11/2025*

{% include-markdown "signature-core.md" %}
 