## 📘 Documentazione Concettuale – Vista `magazzino.vw_costo_medio_globale`

> 👀 **Vedi anche**
>
> • [magazzino.costo_medio](/dbzero/magazzino/tabelle/costo_medio)
> • [magazzino.vw_costo_medio](/dbzero/magazzino/views/vw_costo_medio)

---
### 🎯 Scopo Principale

(rev 2026-08-21)

Il costo medio dell'articolo **su tutti i magazzini**: `sum(valore) / sum(qta)`.

⭐ È una **media ponderata**, non la media delle medie: somma prima valori e quantità, divide
dopo. Fare `avg(costo_medio)` sui singoli magazzini darebbe un numero diverso e sbagliato —
peserebbe allo stesso modo un deposito con 1000 pezzi e uno con 3.

Serve alla valorizzazione d'insieme e al confronto fra articoli, dove la ripartizione fra
magazzini non conta.

---

### ⚠️ Le stesse avvertenze della vista per magazzino

`sum(qta) = 0` → `costo_medio_globale` è `NULL`, non zero. E poiché somma **tutti** i
magazzini, un valore anomalo su un singolo deposito si diluisce qui invece di saltare
all'occhio: per trovarlo si guarda `vw_costo_medio`, non questa.

---

{% include-markdown "it/dbzero/magazzino/_dominio-magazzino.md" %}

---

{% include-markdown "signature-core.md" %}
