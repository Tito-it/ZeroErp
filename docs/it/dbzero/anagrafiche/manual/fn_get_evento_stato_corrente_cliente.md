## 📘 Documentazione Concettuale – Funzione `anagrafiche.fn_get_evento_stato_corrente_cliente()`

> 👀 **Vedi anche**
>
Approfondimento tabelle:
> [anagrafiche.clienti](/dbzero/anagrafiche/tabelle/clienti)
> [config.stati_cliente](/dbzero/config/tabelle/stati_cliente)
> [config.messaggi_errore](/dbzero/config/tabelle/messaggi_errore)
>
Approfondimento funzioni:
> [script.fn_log_and_raise_error](/dbzero/script/funzioni/fn_log_and_raise_error)

### 🎯 Scopo Principale

(latest review 28-04-2026)

La funzione **`anagrafiche.fn_get_evento_stato_corrente_cliente(p_cliente_id)`**
ricava l'**ultimo evento** fra sospensione e riattivazione di un cliente,
ritornando data e tipo evento. Centralizza in DB la logica di confronto
`data_sospensione` vs `data_riattivazione` precedentemente computata lato FE
(rimpiazza la computed `dataSospRiattDetail` di `ClienteDrawer.vue`).

Output a **2 colonne** (decisione 28-04-2026):

| Campo | Tipo | Significato |
|---|---|---|
| `data_evento_stato` | `date` | La piu' recente fra sosp/riatt, oppure NULL se nessuna delle due e' valorizzata |
| `tipo_evento` | `text` | `'SOSPENSIONE'` &#124; `'RIATTIVAZIONE'` &#124; NULL |

**Niente label "stato corrente"** (es. `'SOSPESO'`/`'RIATTIVATO'`): sarebbe
ridondante con [`clienti.stato_cliente_id`](/dbzero/anagrafiche/tabelle/clienti)
(workflow gestionale gia' presente). Il caller deriva la label da
`stato_cliente_id` o dal `tipo_evento` ritornato.

### Scope intenzionale: solo sospensione/riattivazione

La tabella [`clienti`](/dbzero/anagrafiche/tabelle/clienti) ha 4 date evento:
`data_attivazione`, `data_sospensione`, `data_riattivazione`,
`data_chiusura`. **Solo le 2 centrali** rientrano nello scope di questa fn:

* `data_attivazione` e' implicita (cliente nato attivo)
* `data_chiusura` rappresenta uno **stato terminale**, non un evento
  ricorrente da mostrare nella detail page
* l'UI mostra "Ultima sospensione/riattivazione del 15/04" — niente piu'

Per altre semantiche (es. "stato terminale CHIUSO") si usa
`stato_cliente_id` o si crea una fn dedicata.

---

### Logica operativa

1. **Guard input**: `p_cliente_id IS NULL OR <= 0` → raise
   `E_PARAMETRO_INVALIDO`.
2. **Lookup**: `SELECT data_sospensione, data_riattivazione FROM
   anagrafiche.clienti WHERE id = p_cliente_id`.
3. **Guard cliente non trovato**: `IF NOT FOUND` → raise
   `E_VALORE_MANCANTE`. Pattern coerente con
   [`vendite.fn_get_commessa_stato`](/dbzero/vendite/funzioni/fn_get_commessa_stato).
4. **Dispatch sui 4 casi** delle date NOT NULL:

| `data_sospensione` | `data_riattivazione` | Output `(data_evento_stato, tipo_evento)` |
|---|---|---|
| NULL | NULL | `(NULL, NULL)` |
| valued | NULL | `(data_sosp, 'SOSPENSIONE')` |
| NULL | valued | `(data_riatt, 'RIATTIVAZIONE')` — caso anomalo, vedi sotto |
| valued > riatt | valued | `(data_sosp, 'SOSPENSIONE')` |
| valued ≤ riatt | valued | `(data_riatt, 'RIATTIVAZIONE')` |

### Caso anomalo: riattivazione senza sospensione

`data_sospensione IS NULL AND data_riattivazione IS NOT NULL` e'
**semanticamente sospetto** (riattivare un cliente mai sospeso). La fn,
essendo di lettura pura, **non valida la consistenza**: ritorna
`(data_riatt, 'RIATTIVAZIONE')` per coerenza formale.

Se serve il guard di consistenza va messo in INSERT/UPDATE su `clienti`
(out of scope di questa fn).

### Pareggio: `data_sospensione = data_riattivazione`

Caso edge (stesso giorno sospeso e riattivato). **Vince RIATTIVAZIONE**:
nel flow normale la riattivazione viene dopo la sospensione; assumiamo che
una eventuale registrazione "stesso giorno" rispecchi la sequenza
operativa (sospeso al mattino, riattivato il pomeriggio).

---

### Errori sollevati

| Codice | Quando |
|---|---|
| `E_PARAMETRO_INVALIDO` | `p_cliente_id IS NULL OR <= 0`. SQLSTATE P0001. |
| `E_VALORE_MANCANTE` | `cliente_id` non esistente in `anagrafiche.clienti`. SQLSTATE P0001. |

---

### Esempi

**1) Cliente mai sospeso ne' riattivato:**

```sql
SELECT * FROM anagrafiche.fn_get_evento_stato_corrente_cliente(42);
-- (NULL, NULL)
```

**2) Cliente sospeso il 01/03/2026, mai riattivato:**

```sql
SELECT * FROM anagrafiche.fn_get_evento_stato_corrente_cliente(42);
-- (2026-03-01, 'SOSPENSIONE')
```

**3) Cliente sospeso 01/03 e riattivato 01/04:**

```sql
SELECT * FROM anagrafiche.fn_get_evento_stato_corrente_cliente(42);
-- (2026-04-01, 'RIATTIVAZIONE')
```

**4) Cliente riattivato 01/04 e poi sospeso di nuovo 15/04:**

```sql
SELECT * FROM anagrafiche.fn_get_evento_stato_corrente_cliente(42);
-- (2026-04-15, 'SOSPENSIONE')
```

**5) Uso in detail page (BE):**

```python
# clienti_service.fetch_detail()
row = cursor.execute(
    "SELECT data_evento_stato, tipo_evento "
    "FROM anagrafiche.fn_get_evento_stato_corrente_cliente(%s)",
    (cliente_id,),
).fetchone()
detail["data_evento_stato"] = row["data_evento_stato"]
detail["tipo_evento_stato"] = row["tipo_evento"]
```

---

### Note operative

* **STABLE PARALLEL SAFE**: la fn legge solo `clienti` (no scrittura), quindi
  PostgreSQL puo' parallelizzarla e cachearla nella stessa query. Non
  IMMUTABLE perche' dipende dallo stato della tabella.
* **Niente `evento_stato_corrente` nel ritorno**: scelta architetturale per
  evitare ridondanza con `stato_cliente_id`. Il BE/FE deriva la label.
* **Niente vista `vw_clienti_con_stato_corrente`**: rinviata. Il caller e' la
  detail page (1 cliente per volta), il costo della fn e' irrilevante. Una
  vista che JOINa la fn sull'intera tabella `clienti` invocherebbe la fn N
  volte — pattern da valutare solo se nasce un caller in lista.
* **Caso anomalo "riatt senza sosp"**: la fn ritorna comunque, non valida.
  Eventuale guard sull'incoerenza dato e' tema separato (trigger sull'INSERT/UPDATE
  di `clienti`, non in scope).

---

{% include-markdown "signature-core.md" %}

---
