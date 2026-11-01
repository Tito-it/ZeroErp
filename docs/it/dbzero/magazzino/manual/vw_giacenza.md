## 📘 Documentazione Concettuale – Vista `magazzino.vw_giacenza`

> **Ultimo aggiornamento**: 1 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [magazzino.movimenti](/dbzero/magazzino/tabelle/movimenti) — il registro che la vista somma
> * [magazzino.valore_giacenza](/dbzero/magazzino/tabelle/valore_giacenza) — il valore, che qui non entra
>
> Approfondimento viste:
>
> * [magazzino.vw_giacenza_ubicazione](/dbzero/magazzino/views/vw_giacenza_ubicazione) — la stessa somma per posizione
> * [magazzino.vw_giacenza_valorizzata](/dbzero/magazzino/views/vw_giacenza_valorizzata) — quantità, valore e costo insieme
> * [magazzino.vw_disponibilita](/dbzero/magazzino/views/vw_disponibilita) — la giacenza insieme ai blocchi aperti
>
> Approfondimento funzioni:
>
> * [magazzino.trgfn_movimenti_guard_verso](/dbzero/magazzino/funzioni/trgfn_movimenti_guard_verso) — garantisce il segno su cui la somma si regge

---

### 🎯 Scopo Principale

**La giacenza per articolo e magazzino**: la somma delle quantità del registro. Non esiste
una tabella «giacenze»: la giacenza è **sempre** questa somma, quindi non può divergere dal
registro e non c'è nessun posto dove correggerla di nascosto.

È la base delle altre viste del dominio: il costo medio, la giacenza valorizzata e la
disponibilità partono tutte da qui.

---

### Perché è corretta senza guardare le causali

La quantità del registro è **firmata**: un'entrata è positiva, un'uscita negativa, e il
guard [trgfn_movimenti_guard_verso](/dbzero/magazzino/funzioni/trgfn_movimenti_guard_verso)
pretende che il segno sia quello della causale. Sommare le quantità dà quindi già la
giacenza. Applicare il segno anche qui lo applicherebbe **due volte**: un'uscita di 5 pezzi
diventerebbe un'entrata di 5.

---

### Che cosa non fa

* nessun filtro di data: la giacenza è quella di oggi, non «a una certa data»;
* nessuna riga per gli articoli mai movimentati;
* nessuna posizione: per quella c'è [vw_giacenza_ubicazione](/dbzero/magazzino/views/vw_giacenza_ubicazione).

---

### Legge con gli occhi di chi interroga

La vista è `security_invoker`: la row level security del registro e dei magazzini passa
attraverso, e un operatore vede i magazzini del **proprio emittente**. Meccanismo comune:
[Linee guida SQL — sezione 10 RLS](/linee-guida-sql#10-row-level-security-rls).

---

### Test

* `db/pgtap/magazzino/test-valore-giacenza-forma-v1.sql` — la giacenza è la somma del
  registro, senza passare dalle causali; la vista è `security_invoker`.

---

### Note di migrazione

* 2026-09-15 — prende la forma di oggi con il Lotto 1 (`brief-db-magazzino-lotto-1-terreno-vuoto`):
  la quantità vive solo nel registro, e il guard del verso ne garantisce il segno. Prima
  nulla garantiva il verso, e nessuna vista di magazzino era `security_invoker`.

---

{% include-markdown "it/dbzero/magazzino/_dominio-magazzino.md" %}

---

{% include-markdown "signature-core.md" %}
