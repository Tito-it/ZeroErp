## 📘 Documentazione Concettuale – Funzione `dbops.fn_foreign_keys_info`

> **Ultimo aggiornamento**: 7 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento funzioni:
>
> * [dbops.fn_find_file_usage](/dbzero/dbops/funzioni/fn_find_file_usage) — le sole chiavi esterne in entrata, lette da qui
> * [dbops.fn_get_child_fk_col](/dbzero/dbops/funzioni/fn_get_child_fk_col) — la colonna figlia di un vincolo dato

---

### 🎯 Scopo Principale

Le chiavi esterne in cui compare una tabella: quelle **in entrata** (`relazione = 'incoming'`,
altre tabelle che la puntano) e quelle **in uscita** (`'outgoing'`, definite su di lei). Una riga
per colonna della chiave, con il nome del vincolo e la posizione della colonna. È un attrezzo di
consultazione da lanciare a mano, ed è l'unica sede di questa lettura: `dbops.fn_find_file_usage`
ne prende le righe in entrata.

---

### Che cosa restituisce

* **La tabella con il suo schema.** Si passa come `regclass` (`'vendite.fatture'`), e le tabelle
  del risultato escono allo stesso modo: un'omonima in un altro schema non entra.
* **Le colonne accoppiate per posizione.** In una chiave su più colonne la prima colonna della
  figlia va con la prima del padre, la seconda con la seconda, e `posizione` dice quale: un vincolo
  su due colonne dà due righe.
* **La colonna puntata vera**, che può essere una chiave unica diversa dalla chiave primaria.
* **Tutto ciò che c'è**, a prescindere da chi chiama: legge il catalogo di PostgreSQL, non le viste
  di `information_schema` che mostrano solo gli oggetti su cui il ruolo ha privilegi.

---

### Le tabelle partizionate

PostgreSQL ripete una chiave esterna su ogni partizione della tabella che la porta, e su ogni
partizione della tabella puntata. La funzione mostra il vincolo **dichiarato** una volta sola: una
copia che ripete il vincolo dallo stesso lato non è un'altra chiave. Chiesta su una singola
partizione, la funzione mostra le chiavi che la vincolano.

---

### Test

`dbops/test-fk-info-su-pg-constraint-v1`: chiave su due colonne, chiave verso una unica non
primaria, omonima in un altro schema, tabella figlia e tabella padre partizionate.

---

{% include-markdown "signature-core.md" %}
