## 📘 Documentazione Concettuale – Funzione `dbops.fn_name_from_template`

> **Ultimo aggiornamento**: 9 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [dbops.automation_rules_tbl](/dbzero/dbops/tabelle/automation_rules_tbl) — le regole, con il modello di nome di ciascuna
>
> Approfondimento funzioni:
>
> * [dbops.fn_run_automations_attivo](/dbzero/dbops/funzioni/fn_run_automations_attivo) — uno dei runner che danno il nome ai trigger generati
> * [dbops.fn_run_automations_storico](/dbzero/dbops/funzioni/fn_run_automations_storico) — un altro, per i trigger di storicizzazione
> * [dbops.fn_lock_columns_divergenze](/dbzero/dbops/funzioni/fn_lock_columns_divergenze) — calcola con lei il nome atteso del trigger di lock
> * [dbops.fn_nome_oggetto_dichiarato](/dbzero/dbops/funzioni/fn_nome_oggetto_dichiarato) — il nome dichiarato riga per riga da un registro, che passa da lei solo quando serve
>
> Guide:
>
> * [Automazione DB](/guide/automazione-db) — le regole e i runner che generano i trigger

---

### 🎯 Scopo Principale

Costruisce il nome di un oggetto generato dalle automazioni (un trigger, una funzione, un indice) a
partire da un **modello** con dei segnaposto, e garantisce che il nome finale stia nei 63 caratteri
di PostgreSQL. Lo stesso modello con gli stessi valori dà sempre lo stesso nome.

---

### I segnaposto

| Segnaposto | Diventa |
| --- | --- |
| `{schema}`, `{table}` | lo schema e la tabella su cui si lavora |
| `{parent}`, `{child}` | la tabella padre e la figlia, per le regole sulle chiavi esterne |
| `{fk}` | il nome della chiave esterna |
| `{op}` | l'operazione (inserimento, modifica, cancellazione…) |
| `{fkhash6}` | sei caratteri esadecimali ricavati dal nome della chiave esterna, sempre |
| `{fkhash6_if_long}` | gli stessi sei caratteri, ma **solo se** senza di loro il nome supererebbe i 63 caratteri; altrimenti sparisce |

La funzione non sa se due chiavi esterne darebbero lo stesso nome: è il chiamante a deciderlo. Il
runner ATTIVO, quando due FK darebbero lo stesso nome sulla stessa tabella, le passa il modello con
`{fkhash6}` al posto di `{fkhash6_if_long}`, così l'impronta entra sempre.

Un valore mancante sostituisce il segnaposto con niente; un modello mancante vale come «la sola
tabella». Senza nome di chiave esterna, i due segnaposto dell'impronta restano vuoti.

---

### Come esce il nome

Dopo le sostituzioni i trattini bassi ripetuti si riducono a uno e quelli in testa e in coda
spariscono: un segnaposto vuoto non lascia buchi nel nome.

⚠️ Se il nome è ancora più lungo di 63 caratteri, viene **troncato e completato con un'impronta** di
sei caratteri ricavata dal nome intero. Il risultato è stabile — rigenerare dà lo stesso nome — ma
**non è il nome che si legge nel modello**: chi cerca un trigger generato lo cerca per funzione e
argomenti, non per il nome scritto per esteso, che sul database non esiste.

⭐ **È idempotente sul suo risultato.** Il taglio non lascia un trattino basso in coda prima
dell'impronta, quindi nel nome accorciato non c'è un doppio trattino: un nome già risolto,
ripassato alla funzione come modello, esce uguale.

Per i nomi che un registro dichiara riga per riga (il nome della riga, oppure il template del
registro) la porta resta
[fn_nome_oggetto_dichiarato](/dbzero/dbops/funzioni/fn_nome_oggetto_dichiarato), che lascia
intatto un nome già nei 63 caratteri e chiama questa funzione solo per il resto.

---

### Test

* `db/pgtap/dbops/test-storico-salto-trigger-presente-v1.sql` — calcola con questa funzione, dal
  modello della regola, il nome del trigger di storicizzazione che il runner deve trovare già
  presente.
* `db/pgtap/dbops/test-nomi-e-chiavi-registri-v1.sql` — un nome accorciato, ripassato alla
  funzione, esce uguale; e nessun trigger vivo ha un doppio trattino basso nel nome.

---

### Note di migrazione

* 2026-11-09 — diventa idempotente: prima il taglio a 56 caratteri poteva finire con un trattino
  basso, e col separatore dell'impronta nasceva un doppio `__`; ripassato al modello, quel trattino
  si riduceva a uno e il nome cambiava. Cambiano i nomi lunghi dei trigger che avevano il doppio
  trattino: quelli della regola ATTIVO li rigenera il loro runner, che li riconosce dalla funzione e
  dagli argomenti; quello di audit di `config.forme_giuridiche_tipi_soggetto_dettaglio` lo rinomina
  un changeSet a sé, che si salta dove il nome vecchio non c'è (`20261110-34`, `20261110-35`,
  brief-db-revisione-dbops, giro 10c).

---

{% include-markdown "signature-core.md" %}
