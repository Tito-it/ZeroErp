## 📘 Documentazione Funzione – `anagrafiche.trgfn_indirizzi_guard_tipo_ruolo_tipi_indirizzo`

> **Ultimo aggiornamento**: 17 novembre 2026

> 👀 **Vedi anche**
>
**Tabelle anagrafiche / config:**
>
[`anagrafiche.indirizzi`](/dbzero/anagrafiche/tabelle/indirizzi)
> [`anagrafiche.soggetti_ruoli`](/dbzero/anagrafiche/tabelle/soggetti_ruoli)
> [`config.tipi_ruoli`](/dbzero/config/tabelle/tipi_ruoli)
> [`config.tipi_indirizzi`](/dbzero/config/tabelle/tipi_indirizzi)
> [`config.tipi_ruolo_tipi_indirizzo`](/dbzero/config/tabelle/tipi_ruolo_tipi_indirizzo)
> [`config.tipi_soggetto_dettaglio_tipi_indirizzo`](/dbzero/config/tabelle/tipi_soggetto_dettaglio_tipi_indirizzo)
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

Poi guarda la **natura del soggetto** del ruolo (`soggetti.tipo_soggetto_dettaglio_id`): il tipo
di indirizzo deve essere ammesso anche dalla matrice della natura,
[`config.tipi_soggetto_dettaglio_tipi_indirizzo`](/dbzero/config/tabelle/tipi_soggetto_dettaglio_tipi_indirizzo),
con la stessa regola del guard degli indirizzi del soggetto. Un privato non ha una sede legale:
non la può avere né sul soggetto né su un suo ruolo.

In caso di violazione, la funzione richiama **`script.fn_log_and_raise_error`** e blocca l’operazione, garantendo che il dato rispetti la configurazione di dominio.

| Regola violata | Codice | Frase |
| --- | --- | --- |
| il tipo di ruolo non ammette il tipo | `E_TIPO_INDIRIZZO_NON_PERMESSO` | «Il ruolo … non prevede l'indirizzo «…».» |
| la natura del soggetto non ammette il tipo | `E_TIPO_INDIRIZZO_TIPO_SOGGETTO_NON_PERMESSO` | «Il tipo soggetto … non prevede l'indirizzo «…».» |

Il secondo codice è quello del guard del soggetto: la regola e la matrice sono le stesse, e il
contesto dice il layer (`soggetto_ruolo_id`).

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
4️⃣ Chiede al predicato [`fn_tipo_indirizzo_ammesso_per_ruolo`](/dbzero/anagrafiche/funzioni/fn_tipo_indirizzo_ammesso_per_ruolo)
(giorno: `script.fn_data_operativa()`), che è la sede unica della regola:

* nessuna riga di matrice per il tipo di ruolo → indirizzi “liberi”, ammesso;
* altrimenti → ammesso solo se c'è una riga attiva e valida per la coppia.

5️⃣ Chiede al predicato della natura,
[`fn_tipo_indirizzo_ammesso_per_natura`](/dbzero/anagrafiche/funzioni/fn_tipo_indirizzo_ammesso_per_natura),
sulla natura del soggetto del ruolo, con la stessa regola: natura NULL o senza matrice → ammesso.

I due predicati li legge anche la check del tipo sul ruolo
([`fn_check_tipo_indirizzo_ruolo`](/dbzero/anagrafiche/funzioni/fn_check_tipo_indirizzo_ruolo)),
che le madri chiamano prima di scrivere, nello stesso ordine: prima il ruolo, poi la natura. Gli
obbligatori da copiare li dice
[`fn_tipo_indirizzo_obbligatorio_per_ruolo`](/dbzero/anagrafiche/funzioni/fn_tipo_indirizzo_obbligatorio_per_ruolo),
che compone gli stessi due.

⚠️ Il trigger scatta quando si scrive il **tipo** (`INSERT`, `UPDATE OF tipo_indirizzo_id`). La
natura del soggetto cambia dal soggetto, e quel cambio lo giudica
[`fn_check_cambio_natura_soggetto`](/dbzero/anagrafiche/funzioni/fn_check_cambio_natura_soggetto):
un indirizzo del ruolo che la natura nuova non ammette ferma il cambio.

📍 Se nessuna riga valida trovata → chiamata a `script.fn_log_and_raise_error(...)` + `RAISE EXCEPTION`.

---

### Esempi specifici

#### ✔ Esempio valido (matrice esistente)

* `tipo_ruolo = GE`, `tipo_indirizzo = FATT` → ammesso → OK

#### ❌ Esempio non valido

* `tipo_ruolo = GE`, `tipo_indirizzo = RES` → non previsto → errore bloccante
* `tipo_ruolo = FO`, `tipo_indirizzo = SEDELEG`, soggetto privato (`PR`) → il ruolo lo ammette,
  la natura no → `E_TIPO_INDIRIZZO_TIPO_SOGGETTO_NON_PERMESSO`

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

📅 *Aggiornato: 17/11/2026*

{% include-markdown "signature-core.md" %}
 