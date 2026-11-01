## 📘 Documentazione Concettuale – Vista `magazzino.vw_costo_medio_globale`

> **Ultimo aggiornamento**: 1 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [magazzino.valore_giacenza](/dbzero/magazzino/tabelle/valore_giacenza) — il valore di ogni magazzino
> * [magazzino.movimenti](/dbzero/magazzino/tabelle/movimenti) — il registro, da cui viene la quantità
>
> Approfondimento viste:
>
> * [magazzino.vw_costo_medio](/dbzero/magazzino/views/vw_costo_medio) — lo stesso costo per singolo magazzino
> * [magazzino.vw_giacenza](/dbzero/magazzino/views/vw_giacenza) — la quantità per magazzino che qui si somma
> * [magazzino.vw_disponibilita_articolo](/dbzero/magazzino/views/vw_disponibilita_articolo) — lo stesso «globale = visibile», per la disponibilità

---

### 🎯 Scopo Principale

**Il costo medio di un articolo su tutti i magazzini**: somma dei valori diviso somma delle
quantità, con la quantità dal registro e il valore dalla copia. È una media **ponderata**,
non la media delle medie: un deposito con mille pezzi pesa più di uno con tre.

---

### ⭐ «Tutti i magazzini» vuol dire quelli che chi interroga vede

La vista è `security_invoker`: per un operatore è il costo medio dell'articolo sui magazzini
del **proprio emittente**. È la row level security a decidere il perimetro, non un filtro
scritto qui. Meccanismo comune:
[Linee guida SQL — sezione 10 RLS](/linee-guida-sql#10-row-level-security-rls).

---

### ⚠️ Le stesse avvertenze della vista per magazzino

* Il costo è vuoto (`NULL`) quando la quantità totale è **zero o negativa**, la stessa regola
  di [vw_costo_medio](/dbzero/magazzino/views/vw_costo_medio): con una causale che ammette lo
  stock negativo una somma può scendere sotto zero.
* Un valore anomalo su un singolo deposito qui si diluisce: per trovarlo si guarda la vista
  per magazzino.

---

### Test

* `db/pgtap/magazzino/test-valore-giacenza-forma-v1.sql` — la vista somma quantità e valori
  sui magazzini visibili dell'articolo; è `security_invoker`.

---

### Note di migrazione

* 2026-09-15 — nasce con il Lotto 1 (`brief-db-magazzino-lotto-1-terreno-vuoto`).
* 2026-09-18 — con il Lotto 2 (`brief-db-magazzino-lotto-2-motore`) il costo è vuoto anche a
  quantità negativa, non solo a zero.

---

{% include-markdown "it/dbzero/magazzino/_dominio-magazzino.md" %}

---

{% include-markdown "signature-core.md" %}
