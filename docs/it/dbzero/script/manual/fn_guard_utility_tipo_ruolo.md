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
(latest review 27-11-2026)
`script.fn_guard_utility_tipo_ruolo` valida la coerenza tra `utility_id` e `tipo_ruolo_id`: passa solo
se `config.utilities_tipi_ruolo` ha la coppia con una riga accesa e valida oggi. Un'utility **senza righe**
non è ammessa per **nessun** tipo di ruolo: la matrice è chiusa, come nella tendina
`anagrafiche.fn_lookup_utilities_per_ba`.

In caso di mismatch solleva `E_UTILITY_RUOLO_NON_AMMESSO`.

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

1. verifica che la coppia (`p_utility_id`, `p_tipo_ruolo_id`) abbia una riga accesa e valida alla data
   operativa (`script.fn_data_operativa`);
2. in assenza -> `E_UTILITY_RUOLO_NON_AMMESSO`, anche quando l'utility non ha nessuna riga.

---

### Esempi

```sql
-- Caso consentito (il ruolo ha la sua riga per l'utility)
SELECT script.fn_guard_utility_tipo_ruolo(2, 1, 'billing_account_insert');

-- Caso bloccato (nessuna riga per la coppia, anche se l'utility non ne ha nessuna)
SELECT script.fn_guard_utility_tipo_ruolo(2, 9, 'billing_account_insert');
```

---

### Note di utilizzo

Funzione pensata per essere richiamata da trigger/servizi nei punti con entrambi i dati disponibili:

* `utility_id`
* `soggetto_ruolo_id` (da cui ricavare `tipo_ruolo_id`)

---

{% include-markdown "signature-core.md" %}
