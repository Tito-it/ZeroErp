## 📘 Documentazione Concettuale – Funzione `dbops.fn_find_file_usage`

> **Ultimo aggiornamento**: 7 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento funzioni:
>
> * [dbops.fn_foreign_keys_info](/dbzero/dbops/funzioni/fn_foreign_keys_info) — la lettura delle chiavi esterne, in entrata e in uscita, da cui prende le righe
> * [dbops.fn_find_function_usage](/dbzero/dbops/funzioni/fn_find_function_usage) — chi usa una funzione
> * [dbops.fn_search_column_usage](/dbzero/dbops/funzioni/fn_search_column_usage) — dove compare il nome di una colonna

---

### 🎯 Scopo Principale

Le chiavi esterne **in entrata** su una tabella: per ogni vincolo che la punta, la tabella figlia,
il nome del vincolo e, colonna per colonna, la colonna figlia e la colonna puntata. È un attrezzo
di analisi d'impatto da lanciare a mano prima di cambiare o cancellare una tabella; nessun oggetto
del database la chiama.

Nonostante il nome, non c'entra con i file: «file» qui sta per tabella.

---

### Che cosa restituisce

Sono le righe in entrata di `dbops.fn_foreign_keys_info`, con i nomi di colonna di questa
funzione: la tabella si passa come `regclass`, col suo schema; una chiave su più colonne dà una
riga per colonna, accoppiate per posizione (`posizione`); `referenced_column` è la colonna puntata,
che può essere una chiave unica diversa dalla primaria. Il trattamento delle tabelle partizionate è
quello di `dbops.fn_foreign_keys_info`.

---

### Test

`dbops/test-fk-info-su-pg-constraint-v1`, test 9: le sue righe sono le entranti di
`dbops.fn_foreign_keys_info`.

---

{% include-markdown "signature-core.md" %}
