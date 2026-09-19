## 📘 Documentazione Concettuale – View `dbops.vw_magazzino_valore_giacenza_divergente`

> 👀 **Vedi anche**
>
> • [magazzino.valore_giacenza](/dbzero/magazzino/tabelle/valore_giacenza) — la copia
> • [magazzino.movimenti](/dbzero/magazzino/tabelle/movimenti) — il registro
> • [magazzino.fn_ricalcola_valore_giacenza](/dbzero/magazzino/funzioni/fn_ricalcola_valore_giacenza) — il rimedio
>
Guide: [Presidi e registri del debito](/guide/presidi-e-registri-del-debito) · brief `brief-db-magazzino-lotto-2-motore` (§4.4, M-4)

---
### 🎯 Scopo Principale

(rev 2026-09-18 — Lotto 2 del magazzino)

**Le coppie (articolo, magazzino) in cui la copia del valore e la ri-somma del registro
differiscono** — compresa una giacenza con movimenti e senza riga di valore, e una riga di
valore senza movimenti.

> ⚠️ **Deve restare a zero righe.** La vista non prova l'aritmetica: la copia somma gli
> stessi arrotondamenti che la primitiva ha scritto, e coincidono per costruzione. Prova che
> **nessuno ha scritto fuori dalla porta** — la sola scrittura ammessa sul registro e sulla
> copia è la primitiva `fn_scrivi_movimento`. Il rimedio è
> [fn_ricalcola_valore_giacenza](/dbzero/magazzino/funzioni/fn_ricalcola_valore_giacenza);
> capire chi ha scritto è l'altra metà.

Vive in `dbops` e non in `magazzino` perché il catalogo dei presidi pretende che ogni vista
dello schema iscritto abbia la sua riga: una spia dentro `magazzino` avrebbe portato le sette
viste di dominio nel perimetro. Natura `ZERO`, perimetro `DEFINER` (è `security_invoker` su
tabelle sotto row level security: letta a presidio da `fn_conta_presidio`), `SETTIMANALE`.

Presidio: `db/pgtap/magazzino/test-valore-giacenza-divergenza-owner-v1.sql`.

---

### Storia

* 2026-09-18 — nasce con il Lotto 2 (`20260918-19`).

---

{% include-markdown "signature-core.md" %}
