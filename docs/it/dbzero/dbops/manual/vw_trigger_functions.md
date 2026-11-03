## 📘 Documentazione Concettuale – Vista `dbops.vw_trigger_functions`

> **Ultimo aggiornamento**: 4 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [dbops.presidi](/dbzero/dbops/tabelle/presidi) — il catalogo dei presidi, dove la vista è dichiarata inventario
>
> Approfondimento viste:
>
> * [dbops.vw_function_list](/dbzero/dbops/views/vw_function_list) — le funzioni di `dbops` e `script`
> * [dbops.vw_catalogo_oggetti](/dbzero/dbops/views/vw_catalogo_oggetti) — le relazioni di `dbops` e `script`
>
> Approfondimento funzioni:
>
> * [dbops.fn_find_function_usage](/dbzero/dbops/funzioni/fn_find_function_usage) — i trigger che eseguono una funzione data
>
> Guide:
>
> * [Presidi e registri del debito](/guide/presidi-e-registri-del-debito) — la differenza fra un inventario e un presidio

---

### 🎯 Scopo Principale

L'inventario dei trigger del database: ogni trigger utente, in tutti gli schemi, con la tabella su
cui sta, la funzione che esegue e la definizione completa di quella funzione. È un attrezzo per
leggere, non un presidio.

---

### ⛔ Un inventario non entra in un digest

A database sano la vista ha una riga per trigger, cioè moltissime: la sua non-vuotezza è la
condizione normale. Un elenco che si aprisse con migliaia di righe non sarebbe un allarme, e un
avviso rumoroso viene ignorato al secondo invio: finirebbe come il presidio che voleva salvare. Per
questo è dichiarata **inventario** nel catalogo dei presidi: se mancasse dal catalogo, non si
saprebbe se è un inventario o una dimenticanza.

---

### ⚠️ Si filtra, non si scorre

La vista porta il **corpo intero** di ogni funzione-trigger, e la stessa funzione si ripete per ogni
trigger che la usa. Un'interrogazione senza filtro è pesante: si filtra per schema e tabella, o per
nome della funzione.

La tabella si filtra col solo nome (la colonna `tabella`), e lo schema sta nella colonna `schema`.

⚠️ La vista non porta gli **argomenti** del trigger. I trigger generati dalle automazioni usano spesso
la stessa funzione con argomenti diversi, e il nome del trigger generato può essere troncato e
completato da un'impronta: per distinguerli servono gli argomenti, che la definizione del trigger
riporta e questa vista no.

---

{% include-markdown "signature-core.md" %}
