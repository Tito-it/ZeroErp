## 📘 Documentazione Concettuale – Vista `magazzino.vw_costo_medio`

> **Ultimo aggiornamento**: 1 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [magazzino.valore_giacenza](/dbzero/magazzino/tabelle/valore_giacenza) — il valore, numeratore del costo
> * [magazzino.movimenti](/dbzero/magazzino/tabelle/movimenti) — il registro, da cui viene la quantità
>
> Approfondimento viste:
>
> * [magazzino.vw_giacenza](/dbzero/magazzino/views/vw_giacenza) — la quantità, denominatore del costo
> * [magazzino.vw_giacenza_valorizzata](/dbzero/magazzino/views/vw_giacenza_valorizzata) — quantità, valore e costo insieme
> * [magazzino.vw_costo_medio_globale](/dbzero/magazzino/views/vw_costo_medio_globale) — lo stesso costo su tutti i magazzini
>
> Approfondimento funzioni:
>
> * [magazzino.fn_scrivi_movimento](/dbzero/magazzino/funzioni/fn_scrivi_movimento) — legge qui la media corrente per valorizzare

---

### 🎯 Scopo Principale

**Il costo medio** — un tasso — per articolo e magazzino: il valore della copia
([valore_giacenza](/dbzero/magazzino/tabelle/valore_giacenza)) diviso la quantità del
**registro** ([vw_giacenza](/dbzero/magazzino/views/vw_giacenza)).

Qui c'è il solo tasso: la **situazione** completa (quantità, valore, costo) è
[vw_giacenza_valorizzata](/dbzero/magazzino/views/vw_giacenza_valorizzata).

---

### ⭐ Due fonti, non una letta due volte

La quantità viene dal registro e il valore dalla copia: la vista può quindi mostrare quando i
due non tornano. Una giacenza senza riga di valore ha un costo vuoto (`NULL`): un'anomalia
visibile, non un caso nascosto.

---

### ⚠️ Costo vuoto non vuol dire costo zero

Il costo è vuoto (`NULL`) quando la quantità è **zero o negativa**: con una causale che
ammette lo stock negativo (`consente_stock_negativo`) la giacenza può scendere sotto zero, e
un rapporto fra un valore e una quantità negativa non è un costo. Significa **«costo non
determinabile»**, non «costo zero», e non va trattato come zero in un totale.

---

### ⭐ La sede unica della media corrente

La primitiva [fn_scrivi_movimento](/dbzero/magazzino/funzioni/fn_scrivi_movimento) legge
questa vista dentro il proprio lock per valorizzare ogni uscita e le entrate senza costo: la
regola della media è una sola, non due.

---

### Legge con gli occhi di chi interroga

La vista è `security_invoker`: la row level security del registro e dei magazzini passa
attraverso, e un operatore vede i magazzini del **proprio emittente**. Meccanismo comune:
[Linee guida SQL — sezione 10 RLS](/linee-guida-sql#10-row-level-security-rls).

---

### Test

* `db/pgtap/magazzino/test-valore-giacenza-forma-v1.sql` — il costo è il valore della copia
  diviso la quantità del registro; la vista è `security_invoker`.
* `db/pgtap/magazzino/test-fn-scrivi-movimento-valore-v1.sql` — un'uscita prende la media
  corrente, un'entrata senza costo la eredita.

---

### Note di migrazione

* 2026-09-15 — con il Lotto 1 (`brief-db-magazzino-lotto-1-terreno-vuoto`) la quantità si
  legge dal registro: prima quantità e valore stavano entrambi nell'accumulatore
  `costo_medio` (oggi `valore_giacenza`), e la vista non poteva vedere una divergenza. Nello
  stesso giro perde le colonne di quantità e valore, che passano a `vw_giacenza_valorizzata`,
  e diventa `security_invoker`.
* 2026-09-18 — con il Lotto 2 (`brief-db-magazzino-lotto-2-motore`) il costo è vuoto anche a
  quantità negativa, non solo a zero.

---

{% include-markdown "it/dbzero/magazzino/_dominio-magazzino.md" %}

---

{% include-markdown "signature-core.md" %}
