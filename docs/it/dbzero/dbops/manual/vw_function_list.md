## 📘 Documentazione Concettuale – Vista `dbops.vw_function_list`

> **Ultimo aggiornamento**: 4 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [dbops.presidi](/dbzero/dbops/tabelle/presidi) — il catalogo dei presidi, dove la vista è un inventario
>
> Approfondimento viste:
>
> * [dbops.vw_catalogo_oggetti](/dbzero/dbops/views/vw_catalogo_oggetti) — le relazioni degli stessi due schemi
> * [dbops.vw_trigger_functions](/dbzero/dbops/views/vw_trigger_functions) — le funzioni montate come trigger, in tutto il database
>
> Approfondimento funzioni:
>
> * [dbops.fn_find_function_usage](/dbzero/dbops/funzioni/fn_find_function_usage) — chi usa una funzione

---

### 🎯 Scopo Principale

L'elenco delle funzioni e delle procedure degli schemi `dbops` e `script`, una riga per firma: con
l'identificativo che distingue gli overload, gli argomenti, il tipo di ritorno e il commento. È un
attrezzo di consultazione; nel catalogo dei presidi è un inventario che non entra in nessun digest.

---

### Le colonne vengono dal catalogo

**`num_args`** è il numero di argomenti dichiarati della funzione, come lo tiene il catalogo: zero
per una funzione senza argomenti. Conta anche gli argomenti con un valore predefinito.

**`comment`** è il commento della funzione: lo si legge come commento di una funzione, e un oggetto
d'altro tipo non può prestarle il suo né raddoppiare la riga. È vuoto se la funzione non ne ha.

---

### Note di migrazione

* 2026-11-04 — `num_args` e `comment` si leggono dal catalogo. Prima `num_args` contava le
  virgole dell'elenco degli argomenti, e sbagliava con un numerico con precisione e scala o un
  valore predefinito con una virgola, e a zero argomenti era vuoto; `comment` si agganciava al
  catalogo dei commenti per il solo identificativo, e poteva prendere il commento di un altro
  oggetto o raddoppiare la riga (`brief-db-revisione-dbops`).

---

{% include-markdown "signature-core.md" %}
