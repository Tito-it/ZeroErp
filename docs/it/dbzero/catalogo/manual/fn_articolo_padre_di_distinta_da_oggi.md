## 📘 Documentazione Concettuale – Funzione `catalogo.fn_articolo_padre_di_distinta_da_oggi`

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
> * [catalogo.fn_articolo_primo_padre_da_oggi](/dbzero/catalogo/funzioni/fn_articolo_primo_padre_da_oggi) — la stessa finestra, dal lato del componente
> * [script.fn_data_operativa](/dbzero/script/funzioni/fn_data_operativa) — il giorno aziendale

---

### 🎯 Scopo Principale

Dice se un articolo è il **padre di una distinta in vigore o futura**: se ha almeno un legame attivo in `catalogo.articoli_componenti`, come prodotto, la cui validità interseca l'intervallo che va dal giorno aziendale in poi. Un articolo NULL non è padre di niente. Un legame scaduto è storia e non conta.

---

### ⭐ Un predicato, due lettori

È la sede unica della condizione. La leggono:

* il check 1 del guard: `is_composito` e `requires_serial` non si cambiano sul padre di una distinta in vigore o futura (`E_BOM_MODIFICA_VIETATA`);
* le due regole gemelle per il form in `dbops.lock_columns_conditional`, che spengono quei due campi.

Il guard rifiuta il salvataggio, la regola spegne il campo prima che l'operatore ci provi. Poiché
chiamano la stessa funzione, rispondono uguale.

---

### ⭐ Anche il futuro, come il lato componente

La finestra è la stessa di `catalogo.fn_articolo_primo_padre_da_oggi`: dal giorno aziendale in poi.
Un padre che ha soltanto legami futuri è già il padre di una distinta, e resta composito: se gli si
potesse togliere `is_composito`, il giorno in cui il legame entra in vigore la distinta avrebbe un
padre che non è un kit, e nessun guard se ne accorgerebbe, perché l'arrivo di una data non scrive
niente sul legame.

---

### Come legge

`LANGUAGE sql` con corpo `BEGIN ATOMIC`: le tabelle che legge stanno in `pg_depend`. `STABLE`,
`SECURITY INVOKER`: la distinta non ha row level security, e la funzione legge con i diritti di chi
chiama.

---

### Test

* `db/pgtap/catalogo/test-distinta-predicati-guard-e-form-v1.sql` — guard e form chiamano i
  predicati, e per i tre flag di struttura rispondono uguale su articoli costruiti.
* `db/pgtap/catalogo/test-distinta-storia-e-ritorni-v1.sql` — un padre con una distinta solo futura
  non perde `is_composito`.

---

### Note di migrazione

* 2026-11-09 — prende il posto di `catalogo.fn_articolo_padre_di_distinta_in_vigore`, che guardava
  solo la distinta in vigore al giorno aziendale e lasciava togliere `is_composito` a un padre con
  legami solo futuri (brief-db-revisione-catalogo, giro 1).

---

{% include-markdown "signature-core.md" %}
