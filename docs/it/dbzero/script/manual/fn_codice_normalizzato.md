## 📘 Documentazione Concettuale – Funzione `script.fn_codice_normalizzato`

> **Ultimo aggiornamento**: 4 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento funzioni:
>
> * [script.trgfn_codice_maiuscolo](/dbzero/script/manual/trgfn_codice_maiuscolo) — il trigger che salva il codice in questa forma
> * [dbops.fn_codice_maiuscolo_perimetro](/dbzero/dbops/funzioni/fn_codice_maiuscolo_perimetro) — le tabelle dove il codice è normalizzato
>
> Guide:
>
> * [Framework di automazione DB](/guide/automazione-db) — §4.8, l'automazione CODICE_MAIUSCOLO
> * [Linee guida SQL](/linee-guida-sql) — §8.5, colonne normalizzate e ricerche per codice

---

### 🎯 Scopo Principale

È la **forma di un codice dell'operatore**, scritta in un posto solo: senza spazi ai bordi e in
maiuscolo. La usano:

* il trigger dell'automazione CODICE_MAIUSCOLO, che salva il codice in questa forma;
* il guard di forma della sigla degli emittenti fiscali;
* le funzioni del database che cercano una riga per codice;
* le ricerche esatte per codice del backend.

Nessuno ricopia la formula: due copie della stessa regola prima o poi rispondono in due modi diversi.

---

### La mappatura completa delle maiuscole

Il maiuscolo è quello completo dello standard Unicode, uguale su ogni server: `straße` diventa
`STRASSE` (come lo mostra il browser) e la legatura `ﬁ` diventa `FI`. Il maiuscolo «semplice» del
database lascerebbe la `ß` com'è, e allora `straße` e `STRASSE` sarebbero due codici diversi.

⚠️ Per questo il risultato può essere **più lungo** del testo di partenza. Due conseguenze:

* **chi scrive** passa il codice com'è e lascia normalizzare il trigger, che dice con una frase
  (`E_CODICE_TROPPO_LUNGO_IN_MAIUSCOLO`) se in maiuscolo il codice non ci sta più nel campo;
* **chi cerca** mette la funzione direttamente nel confronto (`WHERE codice =
  script.fn_codice_normalizzato(input)`), senza passare da una variabile del tipo della colonna:
  un valore troppo lungo deve dare «non trovato», non un errore di lunghezza.

`NULL` resta `NULL`.

---

### Perché non ci sono indici su questa funzione

Il codice si salva già normalizzato, e l'indice `UNIQUE` sta sulla colonna. Un indice su un'espressione
con questa funzione non servirebbe, e anzi sarebbe fragile: il maiuscolo Unicode può cambiare per i
caratteri nuovi quando PostgreSQL passa a una versione maggiore con tabelle Unicode aggiornate. Senza
indici costruiti su di lei, quel cambio tocca al più le scritture nuove.

---

### Test

`db/pgtap/script/test-fn-codice-normalizzato-v1.sql`: la forma della funzione, i valori (spazi,
`ß`, legature, `NULL`), e due presidi: le funzioni che cercano un codice del perimetro chiamano
questa funzione, e nessun'altra ricopia la formula.

---

{% include-markdown "signature-core.md" %}
