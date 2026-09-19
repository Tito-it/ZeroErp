## 📘 Documentazione Concettuale – Vista `magazzino.vw_costo_medio`

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

**Il costo medio** — un tasso — per articolo e magazzino: il valore della copia
([valore_giacenza](/dbzero/magazzino/tabelle/valore_giacenza)) diviso la quantità del
**registro** ([vw_giacenza](/dbzero/magazzino/views/vw_giacenza)).

⭐ Due fonti, non una letta due volte: fino al 14-09 quantità e valore stavano entrambi
nell'accumulatore, e la vista non poteva dire se i due divergevano dal registro. Ora sì:
una giacenza senza riga di valore mostra un costo `NULL` — un'anomalia visibile, non un caso
nascosto.

`NULL` a quantità **zero o negativa** (dal 18-09: con `consente_stock_negativo` la giacenza può
scendere sotto zero e un rapporto fra un valore e una quantità negativa non è un costo):
significa **«costo non determinabile»**, non «costo zero», e non va trattato come zero in un
totale. ⭐ È la **sede unica** della «media corrente»: la primitiva
[fn_scrivi_movimento](/dbzero/magazzino/funzioni/fn_scrivi_movimento) la legge dentro il lock per
valorizzare ogni uscita e le entrate senza costo — una regola sola, non due.

Fino al 14-09 la vista portava anche `qta` e `valore`: oggi la **situazione** completa
(quantità, valore, costo) è [vw_giacenza_valorizzata](/dbzero/magazzino/views/vw_giacenza_valorizzata);
qui c'è il solo tasso.

### Legge con gli occhi di chi interroga

La vista è `security_invoker`: la RLS del registro e dei magazzini passa attraverso, e un
operatore vede i magazzini del **proprio emittente**. ⚠️ Fino al 14-09 nessuna delle viste
di magazzino lo era. Meccanismo comune: [Linee guida SQL — sezione 10 RLS](/linee-guida-sql#10-row-level-security-rls).

---

{% include-markdown "it/dbzero/magazzino/_dominio-magazzino.md" %}

---

{% include-markdown "signature-core.md" %}
