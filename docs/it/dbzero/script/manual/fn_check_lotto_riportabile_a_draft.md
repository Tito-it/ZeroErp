## 📘 Documentazione Concettuale – Funzione `script.fn_check_lotto_riportabile_a_draft`
### 🎯 Scopo Principale
(latest review 04-08-2026)
Elenca i **motivi che impediscono il ritorno in bozza** di un lotto di fatturazione.
Funzione **pura** (`fn_check_*`): non solleva errori di dominio e non scrive. Ritorna `[]`
quando il ritorno è lecito.

Sede unica della regola, con due consumatori:

1. `vendite.fn_riporta_lotto_a_draft` — solleva il codice del **primo** motivo;
2. `script.fn_available_actions_lotto` — espone l'azione `riporta_a_draft` con
   `enabled = false` e i `reasons` a tooltip.

---

### Perché esiste

È la seconda occorrenza dello stesso difetto del pulsante «Annulla lotto». Il drawer
gatava «Riporta a bozza» con un semplice `!isDraft`, mentre le precondizioni vere sono
tre: su un lotto `DEFINITIVA` il pulsante c'era e falliva.

---

### I motivi, nell'ordine

| # | `reason` | Codice | Quando |
| --- | --- | --- | --- |
| 1 | `STATO_NON_PRE_FISCALE` | `E_LOTTO_NON_RIPORTABILE_A_DRAFT` (800) | Il lotto non è in `DRAFT` né `EMESSA` |
| 2 | `FATTURE_NON_PRE_FISCALI` | `E_LOTTO_FATTURE_NON_PRE_FISCALI` (799) | Almeno una fattura oltre il pre-fiscale |
| 3 | `FATTURE_NUMERATE` | `E_LOTTO_FATTURE_NUMERATE` (801) | Almeno una fattura ha già un numero |

Il motivo 1 esiste perché oltre EMESSA c'è la numerazione, che è il punto di non ritorno
del documento fiscale — non una scelta di questa funzione.

Il motivo 2 è **delegato** a `script.fn_check_lotto_fatture_pre_fiscali`.

---

### ⚠️ Il motivo 3 è ridondante di proposito: non semplificarlo via

A `EMESSA` la fattura non è numerata (C-19), quindi il motivo 1 basterebbe a garantire il
motivo 3. Resta lo stesso, e per una ragione precisa: cancellare una fattura già numerata
aprirebbe un **buco irreversibile** nella numerazione fiscale. Su un danno irreversibile
si guarda il **fatto** (il numero), non lo stato che dovrebbe implicarlo. Un presidio che
si fida di un'implicazione è un presidio che cade il giorno in cui l'implicazione cambia.

---

### Errori sollevati (non di dominio)

* `E_PARAMETRO_INVALIDO` — `lotto_id` assente o `<= 0`.
* `E_LOTTO_NON_TROVATO` — il lotto non esiste.

---

### Output (jsonb)

Array (eventualmente vuoto) di `{ codice, reason, reason_key, dettaglio }`.

---

{% include-markdown "signature-core.md" %}
