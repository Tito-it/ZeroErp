## 📘 Documentazione Concettuale – Funzione `magazzino.fn_ricalcola_valore_giacenza`

> **Ultimo aggiornamento**: 1 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [magazzino.valore_giacenza](/dbzero/magazzino/tabelle/valore_giacenza) — la copia che riscrive
> * [magazzino.movimenti](/dbzero/magazzino/tabelle/movimenti) — il registro da cui ri-somma
>
> Approfondimento viste:
>
> * [dbops.vw_magazzino_valore_giacenza_divergente](/dbzero/dbops/views/vw_magazzino_valore_giacenza_divergente) — la spia che dice quando serve
>
> Approfondimento funzioni:
>
> * [magazzino.fn_scrivi_movimento](/dbzero/magazzino/funzioni/fn_scrivi_movimento) — la primitiva, che scrive la copia movimento per movimento

---

### 🎯 Scopo Principale

**Riscrive la copia del valore di magazzino dal registro**, per un magazzino e, se si vuole,
per un solo articolo. Ritorna, coppia per coppia, il valore prima e dopo.

---

### Una ri-somma, mai una ri-esecuzione

I costi scritti sui movimenti sono fatti: la funzione non li ricalcola, li somma. Per ogni
movimento il contributo è quantità per costo arrotondato a sei decimali — lo stesso
arrotondamento della primitiva — e un costo mancante vale zero. Così copia e ri-somma
coincidono per costruzione.

Le copie del magazzino senza movimenti si cancellano: la primitiva scrive sempre il movimento
prima della copia, quindi una copia senza registro può venire solo da fuori porta. Nel valore
ritornato, una copia cancellata ha il valore «dopo» vuoto.

---

### Il magazzino è obbligatorio

Un magazzino è di un emittente, e «un ricalcolo che serve N emittenti li itera, non li somma».
Non esiste un ricalcolo di tutto il database in una chiamata.

---

### Gira da proprietario

Gira con i permessi del proprietario delle tabelle, non di un superuser: scrive dove
l'applicazione ha solo lettura. Senza identità in sessione si ferma, come la primitiva:
`valore_giacenza` ha il guard di perimetro.

---

### Quando serve

Quando la spia
[vw_magazzino_valore_giacenza_divergente](/dbzero/dbops/views/vw_magazzino_valore_giacenza_divergente)
non è vuota — cioè quando qualcuno ha scritto fuori dalla porta. Il ricalcolo rimette la copia;
capire chi ha scritto è l'altra metà del lavoro.

---

### Codici errore

* `E_MAG_CHIAMATA_NON_VALIDA` — il magazzino manca o non è un identificativo valido.

---

### Test

`db/pgtap/magazzino/test-fn-scrivi-movimento-valore-v1.sql` (test 8-9) e
`db/pgtap/magazzino/test-valore-giacenza-divergenza-owner-v1.sql`.

---

### Note di migrazione

* 2026-09-18 — nasce con `brief-db-magazzino-lotto-2-motore` (§4.4, M-4).

---

{% include-markdown "it/dbzero/magazzino/_dominio-magazzino.md" %}

---

{% include-markdown "signature-core.md" %}
