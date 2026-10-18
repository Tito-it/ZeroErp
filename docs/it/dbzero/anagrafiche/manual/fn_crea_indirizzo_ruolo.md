## 📘 Documentazione Concettuale – Funzione `anagrafiche.fn_crea_indirizzo_ruolo()`

> 👀 **Vedi anche**
>
> [anagrafiche.fn_crea_indirizzi_ruolo](/dbzero/anagrafiche/manual/fn_crea_indirizzi_ruolo) — la plurale, che usa questa
> [anagrafiche.fn_crea_indirizzo_soggetto](/dbzero/anagrafiche/manual/fn_crea_indirizzo_soggetto) — la gemella del soggetto
> [anagrafiche.fn_indirizzo_elemento](/dbzero/anagrafiche/manual/fn_indirizzo_elemento) — la grammatica dell'indirizzo

---

### 🎯 Scopo Principale

(19-10-2026 — R-BE-6 del backend, decisione D-16a di Tid,
`brief-db-processi-accensione-per-ambiente` §6.16)

**Scrive un indirizzo di un ruolo, anche di una singola istanza, e ne restituisce l'id.**

Ogni livello (soggetto e ruolo) ha due madri:

| | Singolare: un indirizzo, l'id | Plurale: più indirizzi, la copia degli obbligatori |
| --- | --- | --- |
| soggetto | `fn_crea_indirizzo_soggetto` | `fn_crea_indirizzi_soggetto` |
| ruolo | **questa** | `fn_crea_indirizzi_ruolo` |

La plurale scrive ogni riga chiamando la singolare: l'inserimento ha una sede sola.

---

### Come si usa

L'indirizzo è un oggetto con la grammatica di
[`fn_indirizzo_elemento`](/dbzero/anagrafiche/manual/fn_indirizzo_elemento): il tipo (per id o
per codice) e l'indirizzo in una delle tre forme (libero, dettaglio già risolto, via da
risolvere). In più, facoltativa, l'**istanza** (`istanza_utility_id`).

⭐ L'istanza la legge questa funzione, non la grammatica comune: un indirizzo di soggetto non ha
istanze, e la grammatica è la stessa per i due livelli.

---

### Che cosa rifiuta

| Caso | Esito |
| --- | --- |
| il ruolo non esiste | `E_SOGGETTO_RUOLO_NON_TROVATO` |
| una chiave che la grammatica non conosce | `E_CAMPO_NON_AMMESSO` |
| un tipo che il ruolo ha già (o che quell'istanza ha già) | il vincolo unico, col suo nome |
| un tipo che il ruolo non ammette, un indirizzo libero incompleto | i controlli della tabella |

⚠️ **Non controlla che l'istanza sia dello stesso soggetto del ruolo.** È una regola della
tabella, che vale anche per le modifiche: andrà in un controllo sulla tabella (trovato il
19-10-2026, non ancora fatto).

---

### Test

`db/pgtap/anagrafiche/test-indirizzi-singolare-e-plurale-v1.sql` (test 3-7).

---

{% include-markdown "signature-core.md" %}
