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

### ⚠️ Due colonne da leggere con cautela

**`num_args` non conta gli argomenti, conta le virgole.** È il numero di pezzi in cui si spezza
l'elenco degli argomenti separandolo sulle virgole. Sbaglia per eccesso quando un valore predefinito
o un tipo contengono una virgola (un numerico con precisione e scala, un array letterale), e per una
funzione senza argomenti è vuoto invece che zero.

**`comment` può non essere il commento della funzione.** La vista cerca il commento solo per
identificativo, senza dire che deve essere il commento di una funzione: il catalogo dei commenti
copre tutti gli oggetti, e un oggetto d'altro tipo con lo stesso identificativo può prestargli il
suo, o raddoppiare la riga.

Per sapere se una funzione ha un commento, o quanti argomenti prende davvero, la fonte affidabile è
la scheda auto-generata della funzione.

---

{% include-markdown "signature-core.md" %}
