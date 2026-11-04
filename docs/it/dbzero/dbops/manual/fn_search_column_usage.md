## 📘 Documentazione Concettuale – Funzione `dbops.fn_search_column_usage`

> **Ultimo aggiornamento**: 4 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento funzioni:
>
> * [dbops.fn_find_function_usage](/dbzero/dbops/funzioni/fn_find_function_usage) — la stessa ricerca, per il nome di una funzione
> * [dbops.fn_find_file_usage](/dbzero/dbops/funzioni/fn_find_file_usage) — chi punta una tabella con una chiave esterna
>
> Guide:
>
> * [Linee guida SQL — funzioni `BEGIN ATOMIC`](/linee-guida-sql#5c-funzioni-sql-begin-atomic-perche-come-si-cambiano-come-si-cercano) — come si cerca davvero nei corpi

---

### 🎯 Scopo Principale

Dato un nome di colonna (o un frammento), elenca gli oggetti nella cui definizione compare: viste,
viste materializzate, regole, funzioni e vincoli. È un attrezzo di consultazione da lanciare a mano
prima di rinominare o togliere una colonna; nessun oggetto del database la chiama.

---

### ⚠️ Una ricerca testuale, e un ramo che non trova niente

La ricerca è sul testo delle definizioni, senza distinguere maiuscole e minuscole, e il nome si cerca
come frammento: un nome contenuto in un altro dà falsi positivi, e il trattino basso vale come
carattere qualsiasi. La risposta dice dove il nome **compare**, non dove la colonna è usata, e non
dice di quale tabella è la colonna.

Tre punti ciechi:

* **i vincoli non escono mai per il nome della colonna.** Il ramo dei vincoli cerca nella forma
  interna dell'espressione, dove le colonne sono numeri di posizione e non nomi: trova un vincolo
  solo se il frammento cercato coincide per caso con un pezzo di quella forma;
* **le funzioni `LANGUAGE sql` scritte con `BEGIN ATOMIC` non si vedono**: il loro sorgente testuale
  è vuoto;
* **i trigger, gli indici e i valori predefiniti** non sono nel perimetro della ricerca.

Una risposta vuota, quindi, non prova che la colonna non sia usata. Il censimento affidabile delle
dipendenze di una colonna sta nelle dipendenze registrate dal database, non nei testi.

---

{% include-markdown "signature-core.md" %}
