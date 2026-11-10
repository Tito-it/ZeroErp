## 📘 Documentazione Concettuale – Funzione `catalogo.fn_articolo_primo_padre_da_oggi`

> **Ultimo aggiornamento**: 9 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [catalogo.articoli_componenti](/dbzero/catalogo/tabelle/articoli_componenti) — i legami della distinta
> * [dbops.lock_columns_conditional](/dbzero/dbops/tabelle/lock_columns_conditional) — le regole del form che la chiamano
>
> Approfondimento funzioni:
>
> * [catalogo.trgfn_articoli_guard_flags_struttura_bom_attiva](/dbzero/catalogo/funzioni/trgfn_articoli_guard_flags_struttura_bom_attiva) — il guard che la chiama
> * [catalogo.fn_articolo_padre_di_distinta_da_oggi](/dbzero/catalogo/funzioni/fn_articolo_padre_di_distinta_da_oggi) — la stessa finestra, dal lato del padre
> * [script.fn_data_operativa](/dbzero/script/funzioni/fn_data_operativa) — il giorno aziendale

---

### 🎯 Scopo Principale

Il **codice del primo padre**, in ordine di codice, di una distinta in vigore o futura di cui l'articolo è componente: un legame attivo di `catalogo.articoli_componenti` la cui validità interseca l'intervallo che va dal giorno aziendale in poi. NULL se non ce n'è nessuno, o se l'articolo è NULL. Un legame scaduto è storia e non conta.

---

### ⭐ Un predicato, due lettori

È la sede unica della condizione. La leggono:

* il check 3 del guard: un componente non diventa composito, perché la distinta ha un livello solo (`E_BOM_COMPONENTE_DIVENTA_COMPOSITO`); il codice del padre va nel messaggio, che così dice dove guardare;
* la regola gemella per il form in `dbops.lock_columns_conditional`, che spegne `is_composito` su un articolo ancora semplice quando la funzione non dà NULL.

Il guard rifiuta il salvataggio, la regola spegne il campo prima che l'operatore ci provi. Poiché
chiamano la stessa funzione, rispondono uguale: prima la condizione stava scritta due volte, e le
due copie erano già divergite una volta sul giorno di riferimento.

La stessa finestra, dal giorno aziendale in poi, la usa il lato del padre: `catalogo.fn_articolo_padre_di_distinta_da_oggi`, il predicato del check 1. I due lati della distinta guardano lo stesso tempo.

Restituisce un codice e non un sì o un no perché il guard ne ha bisogno nel messaggio: un predicato booleano accanto a questa funzione ripeterebbe lo stesso filtro, e le due copie potrebbero divergere.

---

### Come legge

`LANGUAGE sql` con corpo `BEGIN ATOMIC`: le tabelle che legge stanno in `pg_depend`. `STABLE`,
`SECURITY INVOKER`: la distinta non ha row level security, e la funzione legge con i diritti di chi
chiama.

---

### Test

* `db/pgtap/catalogo/test-distinta-predicati-guard-e-form-v1.sql` — guard e form chiamano i
  predicati, e per i tre flag di struttura rispondono uguale su articoli costruiti (padre, componente
  in vigore, componente di una distinta futura, articolo fuori da ogni distinta).
* `db/pgtap/dbops/test-fn-non-editable-fields-conditional.sql`,
  `db/pgtap/catalogo/test-distinta-un-livello-e-onere-natura-v1.sql` — le regole del form e il
  guard, ciascuno dal suo lato.

---

### Note di migrazione

* 2026-11-08 — nasce dalla condizione che il guard e la sua regola per il form scrivevano ciascuno
  per conto suo (brief-db-revisione-dbops).

---

{% include-markdown "signature-core.md" %}
