## 📘 Documentazione Concettuale – Vista `dbops.vw_catalogo_oggetti`

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
> * [dbops.vw_function_list](/dbzero/dbops/views/vw_function_list) — le funzioni degli stessi due schemi, che qui non compaiono
> * [dbops.vw_trigger_functions](/dbzero/dbops/views/vw_trigger_functions) — i trigger di tutto il database

---

### 🎯 Scopo Principale

L'inventario delle relazioni degli schemi `dbops` e `script`: tabelle, viste, viste materializzate,
indici, sequenze, tabelle esterne e così via, con il tipo, il proprietario e il commento. È un
attrezzo di consultazione: la sua non-vuotezza è la condizione normale, e nel catalogo dei presidi è
iscritta come inventario che non entra in nessun digest.

---

### Che cosa elenca, e che cosa no

Elenca ciò che PostgreSQL registra come **relazione** nei due schemi: ogni tabella, vista, indice,
sequenza. **Le funzioni no**: non sono relazioni, e stanno in `dbops.vw_function_list`.

`tipo_oggetto` è la lettera con cui PostgreSQL classifica la relazione (tabella ordinaria, vista,
vista materializzata, indice, sequenza, tabella esterna, tabella partizionata…). ⚠️
`tipo_descrizione`, nonostante il nome, **non descrive**: ripete la stessa lettera, salvo la tabella
ordinaria che diventa `t` e la sequenza che diventa `s` minuscola.

`descrizione` è il commento della relazione: vuoto vuol dire che l'oggetto non ha un commento, ed è
il modo più rapido per trovare gli oggetti dei due schemi ancora senza descrizione.

---

{% include-markdown "signature-core.md" %}
