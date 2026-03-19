## 📘 Documentazione Concettuale – Funzione `script.fn_guard_utility_tipo_ruolo`

> 👀 **Vedi anche**
>
**Approfondimento tabelle:**
>
[`config.utilities_tipi_ruolo`](/dbzero/config/manual/utilities_tipi_ruolo)
> [`config.utilities`](/dbzero/config/tabelle/utilities)
> [`config.tipi_ruoli`](/dbzero/config/tabelle/tipi_ruoli)

---
### 🎯 Scopo Principale
(latest review 16-02-2026)
`script.fn_guard_utility_tipo_ruolo` valida la coerenza tra `utility_id` e `tipo_ruolo_id` con semantica:

1. se non esiste una matrice attiva/valida per utility -> **passa** (fail-open);
2. se la matrice esiste -> passa solo se `tipo_ruolo_id` e` tra quelli ammessi.

In caso di mismatch, solleva errore applicativo bloccante.

---

### Firma

```sql
script.fn_guard_utility_tipo_ruolo(
  p_utility_id integer,
  p_tipo_ruolo_id integer,
  p_context text default null
)
returns void
```

---

### Input

* `p_utility_id`: id utility da validare
* `p_tipo_ruolo_id`: id tipo ruolo da validare
* `p_context`: contesto chiamante (opzionale, utile nel logging)

Validazione parametri:

* `p_utility_id` deve essere non null e `> 0`
* `p_tipo_ruolo_id` deve essere non null e `> 0`

---

### Logica

1. verifica esistenza di almeno una riga attiva/valida in `config.utilities_tipi_ruolo` per `p_utility_id`;
2. se non esiste -> `RETURN` (fail-open);
3. se esiste, verifica che esista anche la coppia (`p_utility_id`, `p_tipo_ruolo_id`) attiva/valida;
4. in assenza di match -> errore `"Tipo ruolo non ammesso per utility"`.

---

### Esempi

```sql
-- Caso consentito (nessuna matrice o ruolo ammesso)
SELECT script.fn_guard_utility_tipo_ruolo(2, 1, 'billing_account_insert');

-- Caso bloccato (matrice presente ma ruolo non ammesso)
SELECT script.fn_guard_utility_tipo_ruolo(2, 9, 'billing_account_insert');
```

---

### Note di utilizzo

Funzione pensata per essere richiamata da trigger/servizi nei punti con entrambi i dati disponibili:

* `utility_id`
* `soggetto_ruolo_id` (da cui ricavare `tipo_ruolo_id`)

---

{% include-markdown "signature-core.md" %}
