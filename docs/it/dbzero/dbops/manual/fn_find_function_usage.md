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
>
> Guide:
>
> * [Linee guida SQL — funzioni `BEGIN ATOMIC`](/linee-guida-sql#5c-funzioni-sql-begin-atomic-perche-come-si-cambiano-come-si-cercano) — come si cerca davvero nei corpi

---

### 🎯 Scopo Principale

Dato il nome di una funzione, elenca chi la usa: le funzioni nel cui sorgente il nome compare, i
trigger che la eseguono e gli event trigger che la eseguono. È un attrezzo da lanciare a mano prima
di rinominare o cambiare una funzione; nessun oggetto del database la chiama.

---

### ⚠️ Una ricerca testuale, con tre punti ciechi

Per le funzioni chiamanti la ricerca è sul **testo** del sorgente, e il nome si cerca come
frammento:

* **le funzioni `LANGUAGE sql` scritte con `BEGIN ATOMIC` non si vedono**: il loro sorgente testuale
  è vuoto, il corpo sta in un'altra forma. Una chiamata dentro una di loro non esce;
* **un nome contenuto in un altro dà falsi positivi**, e il trattino basso, che nei nomi del progetto
  c'è sempre, nella ricerca vale come carattere qualsiasi;
* **le viste che la chiamano non compaiono**: la ricerca guarda solo funzioni e trigger.

Per i trigger e gli event trigger il confronto è sul solo nome, **senza schema**: una funzione
omonima in un altro schema dà le stesse righe. Per lo stesso motivo, dall'elenco dei chiamanti sono
escluse tutte le funzioni con quel nome, in qualunque schema, non solo la funzione cercata.

Una risposta vuota, quindi, non prova che la funzione non sia usata.

---

{% include-markdown "signature-core.md" %}
