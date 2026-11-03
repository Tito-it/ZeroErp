## 📘 Documentazione Concettuale – Vista `dbops.vw_magazzino_movimenti_senza_costo`

> **Ultimo aggiornamento**: 4 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [magazzino.movimenti](/dbzero/magazzino/tabelle/movimenti) — il registro, e il suo `costo_unitario`
> * [magazzino.valore_giacenza](/dbzero/magazzino/tabelle/valore_giacenza) — il valore che un'entrata senza costo lascia com'è
> * [dbops.presidi](/dbzero/dbops/tabelle/presidi) — il catalogo che la iscrive
>
> Approfondimento viste:
>
> * [magazzino.vw_costo_medio](/dbzero/magazzino/views/vw_costo_medio) — la media che si diluisce
> * [dbops.vw_magazzino_valore_giacenza_divergente](/dbzero/dbops/views/vw_magazzino_valore_giacenza_divergente) — la gemella sul valore
>
> Approfondimento funzioni:
>
> * [magazzino.fn_scrivi_movimento](/dbzero/magazzino/funzioni/fn_scrivi_movimento) — la primitiva, che decide il costo del movimento
> * [dbops.fn_conta_presidio](/dbzero/dbops/funzioni/fn_conta_presidio) — il conteggio del digest
>
> Guide:
>
> * [Presidi e registri del debito](/guide/presidi-e-registri-del-debito) — le nature dei presidi

---

### 🎯 Scopo Principale

Le **entrate** di magazzino scritte senza un costo unitario. Non è un guasto ma una tendenza da
guardare: compare nel digest invece di sparire nella media.

---

### ⭐ Un'entrata senza costo è un fatto dichiarato, non un errore

Un'entrata nasce senza costo quando chi la scrive non ne ha uno e la primitiva non trova una
media da cui ereditarlo: il primo carico di un articolo da un inventario senza valore sulla riga,
una rettifica positiva senza media, il carico di un reso la cui uscita d'origine non aveva costo
quando non c'è nemmeno una media.

Il registro lo accetta: il movimento nasce col costo vuoto, il valore della giacenza resta com'è
e la quantità cresce, quindi la media **si diluisce**. È una scelta del modello, e questa vista è
ciò che impedisce che passi inosservata.

---

### Che cosa entra, e che cosa no

* entrano tutti i movimenti con quantità positiva e costo vuoto, qualunque sia la causale;
* **non** entrano le uscite col costo vuoto: sono la conseguenza (non c'era una media da cui
  uscire), non la causa.

---

### Come si legge il numero

A catalogo ha natura `LAVORAZIONE`, cadenza `SETTIMANALE`: non deve per forza arrivare a zero, si
guarda la tendenza. Chi agisce è l'amministratore, dando un costo agli articoli che entrano senza.

⛔ Perimetro `DEFINER`: la vista è `security_invoker` su tabelle sotto row level security, e da un
percorso senza identità risponderebbe zero per cecità. Il digest la conta da proprietario con
`dbops.fn_conta_presidio`.

Sta in `dbops` per la stessa ragione della gemella: il catalogo dei presidi pretende a catalogo
ogni vista degli schemi che vi compaiono, e una spia in `magazzino` porterebbe dentro tutte le
viste del dominio.

---

### Test

* `db/pgtap/magazzino/test-fn-scrivi-movimento-valore-v1.sql`, test 4 — un'entrata senza costo e
  senza media nasce col costo vuoto, lascia il valore a zero e compare nella vista.

---

### Note di migrazione

* 2026-09-18 — nasce con il Lotto 2 del magazzino (`brief-db-magazzino-lotto-2-motore` §4.4,
  D-L2-c).

---

{% include-markdown "signature-core.md" %}
