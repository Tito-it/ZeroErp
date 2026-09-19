## 📘 Documentazione Concettuale – Vista `magazzino.vw_giacenza`

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

**La giacenza per articolo e magazzino**: la somma delle quantità del registro. Non esiste
una tabella «giacenze»: la giacenza è **sempre** questa somma, quindi non può divergere dal
registro e non c'è nessun posto dove correggerla di nascosto.

### Perché è corretta senza guardare le causali

La quantità del registro è **firmata** — il guard del verso garantisce che il segno sia
quello della causale — quindi `sum(qta)` è già la giacenza. Applicare il segno anche qui lo
applicherebbe **due volte**: un'uscita −5 con segno −1 diventerebbe +5. Fino al 14-09
questa pagina segnalava che nulla garantiva il verso; dal 15-09 lo garantisce
[trgfn_movimenti_guard_verso](/dbzero/magazzino/funzioni/trgfn_movimenti_guard_verso).

### Che cosa non fa

* nessun filtro di data: la giacenza è quella di oggi, non «a una certa data»;
* nessuna riga per gli articoli mai movimentati;
* nessuna posizione: per quella c'è [vw_giacenza_ubicazione](/dbzero/magazzino/views/vw_giacenza_ubicazione).

### Legge con gli occhi di chi interroga

La vista è `security_invoker`: la RLS del registro e dei magazzini passa attraverso, e un
operatore vede i magazzini del **proprio emittente**. ⚠️ Fino al 14-09 nessuna delle viste
di magazzino lo era. Meccanismo comune: [Linee guida SQL — sezione 10 RLS](/linee-guida-sql#10-row-level-security-rls).

---

{% include-markdown "it/dbzero/magazzino/_dominio-magazzino.md" %}

---

{% include-markdown "signature-core.md" %}
