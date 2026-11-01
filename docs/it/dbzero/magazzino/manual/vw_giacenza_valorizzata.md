## 📘 Documentazione Concettuale – Vista `magazzino.vw_giacenza_valorizzata`

> **Ultimo aggiornamento**: 1 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [magazzino.movimenti](/dbzero/magazzino/tabelle/movimenti) — il registro, da cui viene la quantità
> * [magazzino.valore_giacenza](/dbzero/magazzino/tabelle/valore_giacenza) — la copia del valore
>
> Approfondimento viste:
>
> * [magazzino.vw_giacenza](/dbzero/magazzino/views/vw_giacenza) — la quantità
> * [magazzino.vw_costo_medio](/dbzero/magazzino/views/vw_costo_medio) — il solo costo, con la stessa regola
> * [dbops.vw_magazzino_valore_giacenza_divergente](/dbzero/dbops/views/vw_magazzino_valore_giacenza_divergente) — la spia che dice se copia e registro dissentono
>
> Approfondimento funzioni:
>
> * [magazzino.fn_ricalcola_valore_giacenza](/dbzero/magazzino/funzioni/fn_ricalcola_valore_giacenza) — riscrive la copia dal registro

---

### 🎯 Scopo Principale

**La situazione della giacenza**: per articolo e magazzino, la **quantità** (dal registro),
il **valore** (dalla copia) e il **costo medio** (valore diviso quantità). È la vista che
risponde a «quanto vale il mio magazzino».

---

### ⭐ Due fonti, e una divergenza si vede

Quantità e valore vengono da due fonti diverse, il registro e la copia: se non tornano, la
vista lo mostra invece di nasconderlo.

---

### ⚠️ Prima di sommare, contare i valori vuoti

`valore` e `costo_medio` possono essere vuoti (`NULL`):

* una giacenza con movimenti e senza riga di valore ha il valore vuoto: è un'anomalia da
  guardare, e una somma dei valori la ignorerebbe in silenzio. Prima di sommare va contato
  quante righe hanno il valore vuoto. La spia
  [dbops.vw_magazzino_valore_giacenza_divergente](/dbzero/dbops/views/vw_magazzino_valore_giacenza_divergente)
  dice se la copia e il registro dissentono;
* il costo medio è vuoto quando la quantità è **zero o negativa**, come in
  [vw_costo_medio](/dbzero/magazzino/views/vw_costo_medio): un rapporto fra un valore e una
  quantità sotto zero non è un costo.

---

### Legge con gli occhi di chi interroga

La vista è `security_invoker`: la row level security del registro e dei magazzini passa
attraverso, e un operatore vede i magazzini del **proprio emittente**. Meccanismo comune:
[Linee guida SQL — sezione 10 RLS](/linee-guida-sql#10-row-level-security-rls).

---

### Test

* `db/pgtap/magazzino/test-valore-giacenza-forma-v1.sql` — quantità dal registro, valore
  dalla copia, costo come loro rapporto; a giacenza zero valore zero e costo vuoto; la vista
  è `security_invoker`.

---

### Note di migrazione

* 2026-09-15 — con il Lotto 1 (`brief-db-magazzino-lotto-1-terreno-vuoto`) la quantità si
  legge dal registro. Prima la vista era tautologica: prendeva quantità e valore dallo stesso
  accumulatore e moltiplicava la quantità per il valore diviso la quantità, cioè rileggeva
  la stessa cifra due volte.
* 2026-09-18 — con il Lotto 2 (`brief-db-magazzino-lotto-2-motore`) il costo medio è vuoto
  anche a quantità negativa.

---

{% include-markdown "it/dbzero/magazzino/_dominio-magazzino.md" %}

---

{% include-markdown "signature-core.md" %}
