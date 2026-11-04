## 📘 Documentazione Concettuale – Funzione `dbops.fn_find_file_usage`

> **Ultimo aggiornamento**: 4 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento funzioni:
>
> * [dbops.fn_foreign_keys_info](/dbzero/dbops/funzioni/fn_foreign_keys_info) — la stessa domanda, in entrata e in uscita, letta da `information_schema`
> * [dbops.fn_find_function_usage](/dbzero/dbops/funzioni/fn_find_function_usage) — chi usa una funzione
> * [dbops.fn_search_column_usage](/dbzero/dbops/funzioni/fn_search_column_usage) — dove compare il nome di una colonna

---

### 🎯 Scopo Principale

Le chiavi esterne **in entrata** su una tabella: per ogni vincolo che la punta, la tabella figlia,
la colonna figlia, la tabella indicata e la colonna puntata. È un attrezzo di analisi d'impatto da
lanciare a mano prima di cambiare o cancellare una tabella; nessun oggetto del database la chiama.

Nonostante il nome, non c'entra con i file: «file» qui sta per tabella.

---

### Che cosa restituisce, e dove sbaglia

La tabella si passa come `regclass`, quindi col suo schema, e la risposta legge direttamente il
catalogo di PostgreSQL: vede tutte le chiavi esterne, a prescindere dai privilegi di chi chiama.
`referenced_table` è sempre la tabella passata.

⚠️ **Le chiavi esterne su più colonne escono sbagliate.** La funzione accoppia ogni colonna figlia
con ogni colonna puntata, invece di accoppiarle per posizione: un vincolo su due colonne dà quattro
righe, due delle quali abbinano colonne che non si corrispondono. Per una chiave esterna su una
colonna sola la risposta è giusta.

---

{% include-markdown "signature-core.md" %}
