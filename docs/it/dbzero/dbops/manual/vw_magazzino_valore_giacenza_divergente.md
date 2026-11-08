## 📘 Documentazione Concettuale – Vista `dbops.vw_magazzino_valore_giacenza_divergente`

> **Ultimo aggiornamento**: 4 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [magazzino.valore_giacenza](/dbzero/magazzino/tabelle/valore_giacenza) — la copia del valore
> * [magazzino.movimenti](/dbzero/magazzino/tabelle/movimenti) — il registro, da cui la ri-somma
> * [dbops.presidi](/dbzero/dbops/tabelle/presidi) — il catalogo che la iscrive
>
> Approfondimento viste:
>
> * [dbops.vw_magazzino_movimenti_senza_costo](/dbzero/dbops/views/vw_magazzino_movimenti_senza_costo) — la gemella sulle entrate senza costo
>
> Approfondimento funzioni:
>
> * [magazzino.fn_scrivi_movimento](/dbzero/magazzino/funzioni/fn_scrivi_movimento) — la primitiva, la sola che scrive registro e copia
> * [magazzino.fn_ricalcola_valore_giacenza](/dbzero/magazzino/funzioni/fn_ricalcola_valore_giacenza) — il rimedio
> * [dbops.fn_conta_presidio](/dbzero/dbops/funzioni/fn_conta_presidio) — il conteggio del digest
>
> Guide:
>
> * [Presidi e registri del debito](/guide/presidi-e-registri-del-debito) — come si legge un presidio che deve restare vuoto

---

### 🎯 Scopo Principale

Le coppie (articolo, magazzino) in cui la **copia** del valore della giacenza e la **ri-somma**
del registro non coincidono. Deve restare vuota.

---

### ⭐ Non prova l'aritmetica: prova che nessuno ha scritto fuori dalla porta

La copia del valore la scrive la primitiva `magazzino.fn_scrivi_movimento`, sommando per ogni
movimento lo stesso arrotondamento (quantità per costo, a sei decimali) che la ri-somma di questa
vista ricalcola: per costruzione coincidono. Una differenza quindi non è un errore di conto: dice
che qualcuno ha scritto il registro o la copia **senza passare dalla primitiva**, che è la sola
scrittrice ammessa.

Un movimento senza costo conta zero nella ri-somma, come nella copia.

---

### Le divergenze che vede

Il confronto è su un'unione completa delle due parti, quindi sono divergenze anche:

* una giacenza con movimenti e **senza** riga di valore;
* una riga di valore **senza** movimenti, che può venire solo da fuori porta.

---

### Il rimedio, e l'altra metà

Il rimedio è `magazzino.fn_ricalcola_valore_giacenza`, che riscrive la copia dalla ri-somma per un
magazzino. L'applicazione ha solo la lettura: il ricalcolo lo esegue il proprietario.

⛔ Ricalcolare chiude la riga ma non la causa: l'altra metà è capire chi ha scritto fuori dalla
porta.

---

### Chi la può vedere

⛔ Perimetro `DEFINER`: la vista è `security_invoker` su tabelle sotto row level security, e da un
percorso senza identità risponderebbe zero per cecità. Il digest la conta da proprietario con
`dbops.fn_conta_presidio`. Cadenza `SETTIMANALE`, chi agisce è lo sviluppo.

Vive in `dbops` e non in `magazzino` perché il catalogo dei presidi pretende a catalogo ogni vista
degli schemi che vi compaiono: una spia dentro `magazzino` avrebbe portato nel perimetro tutte le
viste del dominio.

---

### Test

* `db/pgtap/magazzino/test-valore-giacenza-divergenza-owner-v1.sql` — gira da proprietario: la
  copia toccata fuori porta, o un movimento cancellato fuori porta, accende la riga e il conteggio
  del presidio la vede; il ricalcolo la spegne.
* `db/pgtap/magazzino/test-fn-scrivi-movimento-valore-v1.sql` — dopo i movimenti scritti dalla
  primitiva la vista è vuota, e resta `security_invoker`.

---

### Note di migrazione

* 2026-09-18 — nasce con il Lotto 2 del magazzino (`brief-db-magazzino-lotto-2-motore` §4.4, M-4).
* 2026-09-24 — il ricalcolo non è più eseguibile dall'applicazione (`brief-db-magazzino-verbi-con-permesso`, P-4).

---

{% include-markdown "signature-core.md" %}
