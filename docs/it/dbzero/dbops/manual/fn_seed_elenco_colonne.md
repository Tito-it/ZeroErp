## 📘 Documentazione Concettuale – Funzione `dbops.fn_seed_elenco_colonne`

> **Ultimo aggiornamento**: 22 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento funzioni:
>
> * [dbops.fn_seed_primo_impianto_argomenti](/dbzero/dbops/funzioni/fn_seed_primo_impianto_argomenti) — chiamante: la grammatica legge con lei i tre elenchi della forma `COLONNA`
> * [script.trgfn_seed_primo_impianto](/dbzero/script/funzioni/trgfn_seed_primo_impianto) — chiamante: il trigger legge con lei le colonne derivate
>
> Approfondimento tabelle:
>
> * [dbops.automazione_seed_primo_impianto](/dbzero/dbops/tabelle/automazione_seed_primo_impianto) — le colonne del registro da cui nascono gli elenchi

---

### 🎯 Scopo Principale

Un argomento del trigger del seed di primo impianto, nella forma `COLONNA`, è un testo con i nomi
delle colonne separati da virgola: le colonne del software, quelle dell'installazione, le colonne
derivate. Questa funzione lo legge e restituisce l'elenco dei nomi.

La lettura sta in un posto solo perché la fanno in due. La grammatica valida gli elenchi, e il
trigger rilegge le colonne derivate dai suoi argomenti dopo la validazione. Se i due leggessero lo
stesso testo in due modi, il trigger lascerebbe passare colonne diverse da quelle che la grammatica
ha accettato.

---

### Che cosa restituisce

L'elenco dei nomi (`text[]`), nell'ordine in cui sono scritti:

* gli spazi non contano, nemmeno tab e a capo: `' a , b '` dà `{a,b}`;
* le voci vuote si tolgono: `'a,,b,'` dà `{a,b}`;
* un elenco assente (`NULL`), vuoto o fatto di sole virgole dà l'elenco vuoto `{}`, mai `NULL`.

Non controlla i nomi e non solleva: se l'elenco vuoto è ammesso lo decide il chiamante. La
grammatica rifiuta l'elenco vuoto dove la forma lo vuole pieno.

---

### Test

* `db/pgtap/dbops/test-fn-seed-elenco-colonne-v1.sql` — la lettura (spazi, voci vuote, ordine,
  `NULL`), la grammatica che rifiuta un elenco `NULL`, e le due sedi che la chiamano senza
  ricopiarla.

---

### Note di migrazione

* 2026-11-22 — nasce: la lettura che la grammatica e il trigger facevano ciascuno per sé
  (`brief-db-revisione-ui`, giro 7, la regola del 2).

---

{% include-markdown "signature-core.md" %}
