## 📘 Documentazione Concettuale – Funzione `script.fn_get_parameter_di_sessione()`

> 👀 **Vedi anche**
>
[script.fn_get_parameter_full](/dbzero/script/manual/fn_get_parameter_full) — la cascata degli override
> [config.parameter_overrides](/dbzero/config/tabelle/parameter_overrides)
> [script.fn_stato_proposto_id](/dbzero/script/manual/fn_stato_proposto_id) — il primo lettore

---
### 🎯 Scopo Principale
(18-10-2026 — decisioni D-13a e D-13b di Tid, richiesta del backend R-BE-13 in
`brief-db-processi-accensione-per-ambiente` §6.12)

**Il valore di un parametro, con la cascata degli override e il contesto preso dalla
sessione.** È la stessa cascata di `fn_get_parameter_full` (utente, gruppo, azienda, sessione,
funzione, valore di default); cambia chi fornisce il contesto.

Quando il backend legge un parametro, passa lui chi è l'utente, i suoi gruppi e l'azienda.
Un lettore **dentro il database** (un trigger che completa una riga, una funzione che crea un
soggetto) non riceve niente: il contesto lo ricava questa funzione dalla sessione. Senza di
lei gli override per utente, gruppo e azienda non scatterebbero mai.

---

### Da dove viene ogni livello

| Livello | Da dove | Se manca |
| --- | --- | --- |
| utente | `app.current_user_id` (l'utente Django autenticato) | il livello salta |
| gruppo | i gruppi Django dell'utente | il livello salta |
| azienda | `app.current_emittente_id` (l'azienda attiva della sessione) | il livello salta |
| sessione | `app.session_key` | il livello salta |
| funzione | il secondo argomento: chi chiede (il nome del trigger o della funzione) | il livello salta |
| categoria cliente | — non fa parte della sessione: dipende dal documento | sempre saltato |

⭐ **I gruppi si leggono solo se si può.** La tabella dei gruppi è di Django, che la crea dopo
il database. La funzione la cerca prima nel catalogo e la legge solo se esiste e se il ruolo
che sta lavorando ha il permesso di leggerla. Altrimenti il livello gruppo resta spento,
**senza errore**: i processi automatici non hanno accesso alle tabelle di Django, e il valore
letto così è una proposta, non apre nessun accesso.

---

### Quello che non fa

Non controlla il valore: lo fa chi lo legge, perché solo lui sa che cosa deve essere (per lo
stato proposto: un codice di paese che indichi un solo stato). Se il parametro non è
dichiarato, l'errore è quello di `fn_get_parameter_full`.

---

### Chi la usa

* `script.fn_stato_proposto_id`, lo stato che si propone quando chi scrive non lo dice.

---

### Test

`db/pgtap/script/test-fn-get-parameter-di-sessione-v1.sql`

---

{% include-markdown "signature-core.md" %}
