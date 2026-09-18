## 📘 Documentazione Concettuale – View `dbops.vw_magazzino_movimenti_senza_costo`

> 👀 **Vedi anche**
>
> • [magazzino.movimenti](/dbzero/magazzino/tabelle/movimenti) — `costo_unitario`
> • [magazzino.fn_scrivi_movimento](/dbzero/magazzino/funzioni/fn_scrivi_movimento) — chi decide il costo
>
Guide: [Presidi e registri del debito](/guide/presidi-e-registri-del-debito) · brief `brief-db-magazzino-lotto-2-motore` (§4.4, D-L2-c)

---
### 🎯 Scopo Principale

(rev 2026-09-18 — Lotto 2 del magazzino)

**Le entrate scritte senza un costo**: il primo carico senza valore sulla riga di inventario
e senza una media da ereditare, una rettifica positiva senza media. Un'entrata senza costo
non è un errore: è un fatto dichiarato — il movimento nasce con `costo_unitario` vuoto, il
valore resta com'è e la media si **diluisce**. Le uscite a costo vuoto sono la conseguenza,
non la causa, e non entrano.

Natura `LAVORAZIONE`: una tendenza da guardare, non un guasto — compare nel digest invece di
sparire nella media. Perimetro `DEFINER`, cadenza `SETTIMANALE`. Sta in `dbops` per la stessa
ragione della vista gemella
[vw_magazzino_valore_giacenza_divergente](/dbzero/dbops/views/vw_magazzino_valore_giacenza_divergente).

Presidio: `db/pgtap/magazzino/test-fn-scrivi-movimento-valore-v1.sql` (4).

---

### Storia

* 2026-09-18 — nasce con il Lotto 2 (`20260918-19`).

---

{% include-markdown "signature-core.md" %}
