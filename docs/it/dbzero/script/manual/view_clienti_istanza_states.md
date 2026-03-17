## 📘 Documentazione Concettuale – View `script.view_clienti_istanza_states`

> 👀 **Vedi anche**
>
Approfondimento tabelle:
>
[anagrafiche.istanze_utilities](/dbzero/anagrafiche/tabelle/istanze_utilities)
> [config.stati_cliente](/dbzero/config/tabelle/stati_cliente)
> [script.fn_get_stato_cliente_by_istanza](/dbzero/script/funzioni/fn_get_stato_cliente_by_istanza)

---

### 🎯 Scopo Principale

La view `script.view_clienti_istanza_states` fornisce una **unificazione** delle informazioni di stato di un’istanza di servizio, arricchita con tutti i campi descrittivi della tabella `config.stati_cliente`. Permette di ottenere rapidamente, per ogni record di `istanze_utilities`, lo stato cliente attuale (o predefinito "Istanza") e i relativi dettagli, senza dover eseguire join o fallback manuali.

---

### Definizione della View

```sql
CREATE OR REPLACE VIEW script.view_clienti_istanza_states AS
SELECT
  i.id                        AS istanza_id,
  sc.id                       AS stato_id,
  sc.codice_interno          AS cod_int_stato_cliente,
  sc.descrizione             AS desc_stato_cliente,
  sc.descrizione_breve         AS desc_breve_stato,
  sc.check_lettura            AS check_lettura,
  sc.abilita_fattura          AS abilita_fattura,
  sc.codice            AS stato_cliente,
  sc.stato_cliente_ia         AS stato_cliente_ia,
  sc.data_insert              AS stato_data_insert,
  sc.user_insert              AS stato_user_insert,
  sc.data_update              AS stato_data_update,
  sc.user_update              AS stato_user_update
FROM
  anagrafiche.istanze_utilities i
  JOIN config.stati_cliente sc
    ON sc.id = script.fn_get_stato_cliente_by_istanza(i.id);
```

---

### Colonne Esposte

| Colonna                 | Tipo        | Descrizione                                         |
| ----------------------- | ----------- | --------------------------------------------------- |
| `istanza_id`            | INTEGER     | Identificativo dell’istanza di servizio.            |
| `stato_id`              | INTEGER     | ID dello stato cliente dal catalogo.                |
| `codice_interno`        | CHAR(5)     | Codice interno dello stato (`AT`, `IS`, `CH`, ...). |
| `descrizione            | VARCHAR(80) | Descrizione estesa dello stato.                     |
| `descrizione_breve`     | VARCHAR(20) | Descrizione breve (20 caratteri).                   |
| `check_lettura`         | CHAR(1)     | Flag abilitazione lettura consumi (`S`/`N`).        |
| `abilita_fattura`       | CHAR(1)     | Flag abilitazione fattura (`S`/`N`).                |
| `codice`                | CHAR(2)     | Valore interno non modificabile del tipo stato.     |
| `stato_cliente_ia`      | CHAR(1)     | Stato cliente primario: `I`=Istanza, `A`=Altro.     |
| `stato_data_insert`     | TIMESTAMPTZ | Data di inserimento del record di stato.            |
| `stato_user_insert`     | TEXT        | Utente di inserimento del record di stato.          |
| `stato_data_update`     | TIMESTAMPTZ | Data di ultima modifica del record di stato.        |
| `stato_user_update`     | TEXT        | Utente di ultima modifica del record di stato.      |

---

### Funzionamento Interno

* **Calcolo dello stato**: utilizza `script.fn_get_codice_by_istanza(i.id)` per gestire il fallback tra stato cliente effettivo e stato "Istanza".
* **Join diretto** con `config.stati_cliente` per recuperare tutti i metadata (descrizioni e flag).

---

### Considerazioni e Best Practice

* **Performance**: è fondamentale avere indici su `anagrafiche.clienti.istanza_utility_id` e su `config.stati_cliente.codice_interno` per ottimizzare sia la funzione che il join.
* **Consistenza**: la logica di fallback è centralizzata nella funzione, quindi qualsiasi modifica al codice interno dello stato "Istanza" avrà effetto anche sulla view.
* **Uso in reportistica**: la view è pronta per essere utilizzata in strumenti BI o dashboard, evitando logica condizionale nel front-end.

---

{% include-markdown "signature-core.md" %}
