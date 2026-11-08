## 📘 Documentazione Concettuale – Funzione `catalogo.fn_articolo_padre_di_distinta_in_vigore`

> **Ultimo aggiornamento**: 8 novembre 2026
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
> * [script.fn_data_operativa](/dbzero/script/funzioni/fn_data_operativa) — il giorno aziendale

---

### 🎯 Scopo Principale

Dice se un articolo è il **padre di una distinta in vigore**: se ha almeno un legame attivo in `catalogo.articoli_componenti`, come prodotto, la cui validità contiene il giorno aziendale (`script.fn_data_operativa()`). Un articolo NULL non è padre di niente.

---

### ⭐ Un predicato, due lettori

È la sede unica della condizione. La leggono:

* il check 1 del guard: `is_composito` e `requires_serial` non si cambiano su un padre di una distinta in vigore (`E_BOM_MODIFICA_VIETATA`);
* le due regole gemelle per il form in `dbops.lock_columns_conditional`, che spengono quei due campi.

Il guard rifiuta il salvataggio, la regola spegne il campo prima che l'operatore ci provi. Poiché
chiamano la stessa funzione, rispondono uguale: prima la condizione stava scritta due volte, e le
due copie erano già divergite una volta sul giorno di riferimento.

Guarda solo la distinta **in vigore oggi**: un legame futuro o scaduto non conta. Il passaggio a composito di un componente, che guarda anche il futuro, è un'altra regola (`catalogo.fn_articolo_primo_padre_da_oggi`).

⚠️ Ne segue che un articolo con legami solo futuri non è padre di una distinta in vigore: il guard gli lascia togliere `is_composito` (se nessun documento lo usa), e quei legami entreranno in vigore sotto un articolo che non è più un kit.

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
