## 📘 Documentazione Concettuale – Funzione `catalogo.fn_articolo_componente_di_distinta_in_vigore`

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

Dice se un articolo è **componente di una distinta in vigore**: se compare come componente in almeno un legame attivo di `catalogo.articoli_componenti` la cui validità contiene il giorno aziendale (`script.fn_data_operativa()`). Un articolo NULL non è componente di niente.

---

### ⭐ Un predicato, due lettori

È la sede unica della condizione. La leggono:

* il check 2 del guard: `is_solo_componente` non si cambia su un componente di una distinta in vigore (`E_BOM_MODIFICA_VIETATA`);
* la regola gemella per il form in `dbops.lock_columns_conditional`, che spegne quel campo.

Il guard rifiuta il salvataggio, la regola spegne il campo prima che l'operatore ci provi. Poiché
chiamano la stessa funzione, rispondono uguale: prima la condizione stava scritta due volte, e le
due copie erano già divergite una volta sul giorno di riferimento.

Guarda solo la distinta **in vigore oggi**. Per un componente di una distinta futura vale la regola del livello unico (`catalogo.fn_articolo_primo_padre_da_oggi`).

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
