## 📘 Documentazione Concettuale – Funzione `magazzino.fn_ricalcola_valore_giacenza`

> 👀 **Vedi anche**
>
Approfondimento tabelle:
> • [magazzino.valore_giacenza](/dbzero/magazzino/tabelle/valore_giacenza) — la copia che riscrive
> • [magazzino.movimenti](/dbzero/magazzino/tabelle/movimenti) — il registro da cui ri-somma
>
Approfondimento viste:
> • [dbops.vw_magazzino_valore_giacenza_divergente](/dbzero/dbops/views/vw_magazzino_valore_giacenza_divergente) — la spia che dice quando serve
>
Guide: brief `brief-db-magazzino-lotto-2-motore` (§4.4, M-4)

---
### 🎯 Scopo Principale

(rev 2026-09-18 — Lotto 2 del magazzino)

**Riscrive la copia del valore dal registro**, per un magazzino (obbligatorio: un magazzino è
di un emittente, e «un ricalcolo che serve N emittenti li itera, non li somma») e, se si
vuole, per un solo articolo. È una **ri-somma**, mai una ri-esecuzione: i costi scritti sui
movimenti sono fatti, la funzione somma `round(qta × costo, 6)` — lo stesso arrotondamento
della primitiva — e riscrive `valore`. Le copie del magazzino senza movimenti si cancellano:
la primitiva scrive sempre il movimento prima della copia, quindi una copia senza registro
può venire solo da fuori porta. Ritorna, coppia per coppia, il valore prima e dopo.

Gira con i permessi del proprietario (`SECURITY DEFINER`): scrive dove l'applicazione ha solo
lettura. Senza identità in sessione si ferma, come la primitiva: `valore_giacenza` ha il guard
di scope.

**Quando serve**: quando la spia
[vw_magazzino_valore_giacenza_divergente](/dbzero/dbops/views/vw_magazzino_valore_giacenza_divergente)
non è vuota — cioè quando qualcuno ha scritto fuori dalla porta. Il ricalcolo rimette la copia;
capire chi ha scritto è l'altra metà del lavoro.

Presidio: `db/pgtap/magazzino/test-fn-scrivi-movimento-valore-v1.sql` (8-9) e
`test-valore-giacenza-divergenza-owner-v1.sql`.

---

### Storia

* 2026-09-18 — nasce con il Lotto 2 (`20260918-19`).

---

{% include-markdown "it/dbzero/magazzino/_dominio-magazzino.md" %}

---

{% include-markdown "signature-core.md" %}
