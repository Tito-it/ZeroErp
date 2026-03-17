## 📘 Documentazione Concettuale – Funzione `script.fn_get_stato_cliente_by_istanza`

> 👀 **Vedi anche**
>
Approfondimento tabelle:
>
[anagrafiche.clienti](/dbzero/anagrafiche/tabelle/clienti)  
> [config.stati_cliente](/dbzero/config/tabelle/stati_cliente)   

---

### 🎯 Scopo Principale

Fornire lo **stato cliente** associato a una specifica **istanza di servizio**, restituendo:

1. Il valore `stato_cliente_id` del record `clienti` collegato all’istanza, se presente.
2. In assenza di un record `clienti`, il valore di default corrispondente a **codice_interno = 'IS'** (stato "Istanza").

---


### Parametri

| Parametro      | Tipo    | Descrizione                                                                 |
| -------------- | ------- | --------------------------------------------------------------------------- |
| `p_istanza_id` | INTEGER | Identificativo dell’istanza di servizio di cui recuperare lo stato cliente. |

---

### Valore di Ritorno

* **INTEGER**: `stato_cliente_id` del record cliente relativo all’istanza, o valore di default per lo stato "Istanza" se il cliente non esiste.

---

### Logica Operativa

1. **Recupero stato del cliente**

   ```sql
   (SELECT c.stato_cliente_id
      FROM anagrafiche.clienti c
     WHERE c.istanza_utility_id = p_istanza_id
     LIMIT 1)
   ```

   Se esiste un cliente per quell’istanza, viene restituito il suo `stato_cliente_id`.

2. **Fallback a "Istanza"**

   ```sql
   (SELECT id
      FROM config.stati_cliente
     WHERE codice_interno = 'IS'
     LIMIT 1)
   ```

   Se non esiste un cliente, la funzione ritorna l’`id` del record in `config.stati_cliente` con codice interno 'IS'.

3. **COALESCE** unisce i due SELECT, restituendo il primo valore non NULL.

---

### Esempi di Utilizzo

* **Richiamare lo stato di un’istanza specifica**:

  ```sql
  SELECT script.fn_get_stato_cliente_by_istanza(42);
  ```

* **Usare in una VIEW**:

  ```sql
  CREATE VIEW anagrafiche.view_istanza_state AS
  SELECT i.id AS istanza_id,
         script.fn_get_stato_cliente_by_istanza(i.id) AS stato_id
    FROM anagrafiche.istanze_utilities i;
  ```

---

### Best Practice

* Assicurarsi che esista un indice su `clienti.istanza_utility_id` per ottimizzare la prima subquery.
* Evitare di modificare `codice_interno = 'IS'` senza aggiornare le eventuali query/funzioni che ne fanno riferimento.
* Documentare eventuali nuovi codici stati aggiunti in `config.stati_cliente`.

---