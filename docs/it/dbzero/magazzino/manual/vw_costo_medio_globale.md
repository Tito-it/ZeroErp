## 📘 Documentazione Concettuale – Vista `magazzino.vw_costo_medio_globale`

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

**Il costo medio di un articolo su tutti i magazzini**: somma dei valori diviso somma delle
quantità, con la quantità dal registro e il valore dalla copia. È una media **ponderata**,
non la media delle medie — pesa un deposito con mille pezzi più di uno con tre.

⭐ «Tutti i magazzini» significa **tutti quelli che chi interroga vede**: la vista è
`security_invoker`, quindi per un operatore è il costo medio dell'articolo sui magazzini del
proprio emittente. È la RLS a decidere il perimetro, non un filtro scritto qui.

Le stesse avvertenze della vista per magazzino: `NULL` a quantità zero, e un valore anomalo
su un singolo deposito qui si diluisce — per trovarlo si guarda
[vw_costo_medio](/dbzero/magazzino/views/vw_costo_medio).

### Legge con gli occhi di chi interroga

La vista è `security_invoker`: la RLS del registro e dei magazzini passa attraverso, e un
operatore vede i magazzini del **proprio emittente**. ⚠️ Fino al 14-09 nessuna delle viste
di magazzino lo era. Meccanismo comune: [Linee guida SQL — sezione 10 RLS](/linee-guida-sql#10-row-level-security-rls).

---

{% include-markdown "it/dbzero/magazzino/_dominio-magazzino.md" %}

---

{% include-markdown "signature-core.md" %}
