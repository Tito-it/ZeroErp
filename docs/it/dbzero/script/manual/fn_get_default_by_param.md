## 📘 Documentazione Concettuale – Funzione `script.fn_get_default_by_param()`

> 👀 **Vedi anche**
>
> Approfondimento Tabelle:
>
> * [config.parameters](/dbzero/config/tabelle/parameters)
> * [config.parameter_overrides](/dbzero/config/tabelle/parameter_overrides)

>
> Approfondimento funzioni:
>
> * [script.fn_get_parameter_full](/dbzero/script/funzioni/fn_get_parameter_full)
> * [script.fn_log_and_raise_error](/dbzero/script/funzioni/fn_log_and_raise_error)

---

### 🎯 Scopo Principale

Recuperare in modo dinamico un valore di **PK** (o altro identificativo) da qualsiasi tabella, basandosi su un **codice parametro**. La funzione:

1. Legge il **valore testuale** del parametro specificato (`p_param_code`) tramite `fn_get_parameter_full`.
2. Esegue una **query dinamica** su `p_table_schema.p_table_name`, filtrando `p_filter_column = parametro_letto`, e restituisce il primo campo della riga (presumibile PK) sempre come TEXT.
3. Se non trova alcun record, registra l’errore e solleva un’eccezione `E_DEFAULT_ERRATO` con `fn_log_and_raise_error`.

---

### 🔗 Collegamenti

* **`script.fn_get_parameter_full`** – recupera il valore di filtro (stringa) dai parametri tabellari.
* **`script.fn_log_and_raise_error`** – gestisce il logging e il sollevamento dell’errore in caso di mancato riscontro.
* **pg_catalog.pg_attribute**, **pg_class**, **pg_namespace** – utilizzati per ricavare dinamicamente il primo attributo (presumibile PK) della tabella target.

---

### 💡 Note Operative

* **Parametri di input**:

  * `p_table_schema`: schema di destinazione (es. `config`).
  * `p_table_name`: nome della tabella (es. `states`).
  * `p_filter_column`: colonna su cui filtrare (es. `codice_iso3`).
  * `p_param_code`: codice parametro da leggere (es. `state_code_iso3`).
  * `p_function_name`: contesto/funzione chiamante, usato nel log.
* **Output**:

  * Ritorna **TEXT** con il valore letto (ID), da castare dal chiamante se serve (INTEGER, UUID, ecc.).
* **Sicurezza**:

  * L’uso di `EXECUTE format(...) USING v_param_val` previene SQL injection sul filtro.
  * Viene sempre restiuito un singolo risultato (`LIMIT 1`).
* **Error handling**:

  * Se la query non restituisce righe, la funzione chiama `fn_log_and_raise_error`, registrando contesto e messaggio personalizzato.
* **Uso consigliato**:

  * Attribuire valori di default a entità che fanno riferimento a codici esterni (es. `state_code_iso2` → `stati.id`).
  * Inserire all’interno di procedure o trigger prima delle operazioni che richiedono il lookup.

---

> 🧠 **“`fn_get_default_by_param` semplifica il recupero dinamico di chiavi primarie basate su parametri di configurazione, garantendo sicurezza, logging e flessibilità schema‐agnostica.”**
