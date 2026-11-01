## 📘 Documentazione Concettuale – Vista `magazzino.vw_disponibilita_articolo`

> **Ultimo aggiornamento**: 1 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento viste:
>
> * [magazzino.vw_disponibilita](/dbzero/magazzino/views/vw_disponibilita) — la grana articolo e magazzino, da cui questa somma
> * [magazzino.vw_costo_medio_globale](/dbzero/magazzino/views/vw_costo_medio_globale) — lo stesso «globale = visibile», per il costo

---

### 🎯 Scopo Principale

**La disponibilità di un articolo su tutti i magazzini visibili**: giacenza, quota bloccata e
disponibile sommate da [vw_disponibilita](/dbzero/magazzino/views/vw_disponibilita), più
`n_magazzini`, quanti magazzini concorrono alla somma.

---

### ⭐ «Globale» vuol dire visibile a chi interroga

Dentro l'emittente attivo è tutto: è la row level security dei magazzini a decidere il
perimetro, non un filtro scritto qui, come per
[vw_costo_medio_globale](/dbzero/magazzino/views/vw_costo_medio_globale). La vista è
`security_invoker`.

---

### Test

* `db/pgtap/magazzino/test-vw-disponibilita-v1.sql` — la grana per articolo somma i
  magazzini e li conta; la vista è `security_invoker`.

---

### Note di migrazione

* 2026-09-18 — nasce con il Lotto 2 (`brief-db-magazzino-lotto-2-motore`).

---

{% include-markdown "it/dbzero/magazzino/_dominio-magazzino.md" %}

---

{% include-markdown "signature-core.md" %}
