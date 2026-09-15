## 📘 Documentazione Concettuale – Vista `magazzino.vw_giacenza_valorizzata`

> 👀 **Vedi anche**
>
Approfondimento tabelle:
> • [magazzino.movimenti](/dbzero/magazzino/tabelle/movimenti) — il registro
> • [magazzino.valore_giacenza](/dbzero/magazzino/tabelle/valore_giacenza) — la copia del valore
>
Le cinque viste: [vw_giacenza](/dbzero/magazzino/views/vw_giacenza) · [vw_giacenza_ubicazione](/dbzero/magazzino/views/vw_giacenza_ubicazione) · [vw_costo_medio](/dbzero/magazzino/views/vw_costo_medio) · [vw_costo_medio_globale](/dbzero/magazzino/views/vw_costo_medio_globale) · [vw_giacenza_valorizzata](/dbzero/magazzino/views/vw_giacenza_valorizzata)
>
Guide: brief `brief-db-magazzino-lotto-1-terreno-vuoto` (§4.8)

---
### 🎯 Scopo Principale

(rev 2026-09-15 — Lotto 1 del magazzino)

**La situazione della giacenza**: per articolo e magazzino, la **quantità** (dal registro),
il **valore** (dalla copia) e il **costo medio** (valore / quantità). È la vista che
risponde a «quanto vale il mio magazzino».

⭐ Fino al 14-09 era tautologica: calcolava `qta × (valore / qta) = valore`, con la quantità
presa dall'accumulatore — la stessa cifra letta due volte. Ora il join è fra **due fonti**, e
una divergenza si vede.

⚠️ `valore` e `costo_medio` possono essere `NULL`: una giacenza con movimenti e senza riga di
valore è un'anomalia da guardare, e `sum(valore)` la ignorerebbe in silenzio. Prima di
sommare va contato quante righe hanno `valore IS NULL`.

### Legge con gli occhi di chi interroga

La vista è `security_invoker`: la RLS del registro e dei magazzini passa attraverso, e un
operatore vede i magazzini del **proprio emittente**. ⚠️ Fino al 14-09 nessuna delle viste
di magazzino lo era. Meccanismo comune: [Linee guida SQL — sezione 10 RLS](/linee-guida-sql#10-row-level-security-rls).

---

{% include-markdown "it/dbzero/magazzino/_dominio-magazzino.md" %}

---

{% include-markdown "signature-core.md" %}
