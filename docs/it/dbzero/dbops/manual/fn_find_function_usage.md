## 📘 Documentazione Concettuale – Funzione `dbops.fn_find_function_usage`

> **Ultimo aggiornamento**: 4 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento viste:
>
> * [dbops.vw_function_list](/dbzero/dbops/views/vw_function_list) — l'elenco delle funzioni di `dbops` e `script`
> * [dbops.vw_trigger_functions](/dbzero/dbops/views/vw_trigger_functions) — ogni trigger con la sua funzione
>
> Approfondimento funzioni:
>
> * [dbops.fn_search_column_usage](/dbzero/dbops/funzioni/fn_search_column_usage) — la stessa ricerca, per il nome di una colonna
> * [dbops.fn_find_file_usage](/dbzero/dbops/funzioni/fn_find_file_usage) — chi punta una tabella con una chiave esterna
> * [dbops.fn_corpo_funzione](/dbzero/dbops/funzioni/fn_corpo_funzione) — il corpo senza commenti in cui si cercano le chiamate
>
> Guide:
>
> * [Linee guida SQL — funzioni `BEGIN ATOMIC`](/linee-guida-sql#5c-funzioni-sql-begin-atomic-perche-come-si-cambiano-come-si-cercano) — come si cerca davvero nei corpi

---

### 🎯 Scopo Principale

Dato il nome di una funzione, elenca chi la usa: le funzioni nel cui corpo il nome compare, i
trigger che la eseguono e gli event trigger che la eseguono, con lo schema di ognuno (vuoto per gli
event trigger, che non ne hanno). È un attrezzo da lanciare a mano prima di rinominare o cambiare una
funzione; nessun oggetto del database la chiama.

---

### Il corpo dei chiamanti, senza commenti

Per le funzioni chiamanti la ricerca è sul corpo letto da
[fn_corpo_funzione](/dbzero/dbops/funzioni/fn_corpo_funzione): senza commenti, con i letterali
intatti, e anche per le funzioni SQL scritte con `BEGIN ATOMIC`, il cui sorgente testuale è vuoto.
Una chiamata dentro una `BEGIN ATOMIC` esce; un nome rimasto in un commento non conta come chiamata.

Il parametro è un nome di funzione del catalogo, senza schema e senza argomenti.

---

### ⚠️ Una ricerca testuale, con i suoi punti ciechi

Il nome si cerca nel corpo come **frammento**:

* **un nome contenuto in un altro dà falsi positivi**: cercando una funzione escono anche quelle che
  ne chiamano una con un nome più lungo che la contiene. E il trattino basso, che nei nomi del
  progetto c'è sempre, nella ricerca vale come carattere qualsiasi;
* **una chiamata composta con SQL dinamico**, dove il nome si costruisce a pezzi, non si vede;
* **le viste che la chiamano non compaiono**: la ricerca guarda solo funzioni e trigger.

Per i trigger e gli event trigger il confronto è sul solo nome, **senza schema**: una funzione
omonima in un altro schema dà le stesse righe. Per lo stesso motivo, dall'elenco dei chiamanti sono
escluse tutte le funzioni con quel nome, in qualunque schema, non solo la funzione cercata.

Una risposta vuota, quindi, non prova che la funzione non sia usata.

---

### Test

* `db/pgtap/dbops/test-corpo-funzione-senza-commenti-v1.sql`, test 14-15 — trova un chiamante
  scritto con `BEGIN ATOMIC`; non conta una chiamata rimasta in un commento.

---

### Note di migrazione

* 2026-11-04 — il ramo delle funzioni chiamanti cerca nel corpo di `fn_corpo_funzione` (D15 di
  `brief-db-revisione-dbops`): prima cercava nel sorgente testuale, cieco sulle `BEGIN ATOMIC`, e un
  nome rimasto in un commento contava come chiamata. Il parametro diventa un nome di funzione del
  catalogo, e lo schema restituito prende il tipo dei nomi di schema del catalogo.
* 2026-11-04 — il commento nel database è riscritto (M33 di `brief-db-revisione-dbops`): prima era
  copiato da `fn_find_file_usage` e descriveva le chiavi esterne verso una tabella.

---

{% include-markdown "signature-core.md" %}
