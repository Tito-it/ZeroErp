## 📘 Documentazione Concettuale – Tabella `magazzino.valore_giacenza`

> **Ultimo aggiornamento**: 1 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [magazzino.movimenti](/dbzero/magazzino/tabelle/movimenti) — il registro da cui si ricostruisce
>
> Approfondimento viste:
>
> * [magazzino.vw_giacenza](/dbzero/magazzino/views/vw_giacenza) — la quantità
> * [magazzino.vw_costo_medio](/dbzero/magazzino/views/vw_costo_medio) — il costo medio (valore diviso quantità)
> * [magazzino.vw_giacenza_valorizzata](/dbzero/magazzino/views/vw_giacenza_valorizzata) — la situazione
> * [dbops.vw_magazzino_valore_giacenza_divergente](/dbzero/dbops/views/vw_magazzino_valore_giacenza_divergente) — la spia della copia che diverge
>
> Approfondimento funzioni:
>
> * [magazzino.fn_scrivi_movimento](/dbzero/magazzino/funzioni/fn_scrivi_movimento) — tiene aggiornata la copia
> * [magazzino.fn_ricalcola_valore_giacenza](/dbzero/magazzino/funzioni/fn_ricalcola_valore_giacenza) — la rifà dal registro

---

### 🎯 Scopo Principale

**Quanto vale la giacenza** di un articolo in un magazzino. Una riga per coppia
(articolo, magazzino), con il **valore** totale corrente.

È una **copia ricostruibile** del registro, non una fonte: la tiene aggiornata la primitiva
di scrittura ([fn_scrivi_movimento](/dbzero/magazzino/funzioni/fn_scrivi_movimento)), che a
ogni movimento aggiunge al valore la quantità per il costo unitario, arrotondata a sei
decimali; un movimento senza costo aggiunge zero, ma la riga nasce lo stesso. In qualunque
momento la copia si può rifare **ri-sommando** i costi scritti sui movimenti con
[fn_ricalcola_valore_giacenza](/dbzero/magazzino/funzioni/fn_ricalcola_valore_giacenza), con
lo stesso arrotondamento: le entrate al costo del documento, le uscite alla media corrente.
Non è una ri-esecuzione: i costi unitari stanno sul registro, e sommarli basta. La spia
[dbops.vw_magazzino_valore_giacenza_divergente](/dbzero/dbops/views/vw_magazzino_valore_giacenza_divergente)
dice quando copia e registro divergono, cioè quando qualcuno ha scritto fuori dalla porta.

---

### La quantità non sta qui

La quantità vive **solo** nel registro (`vw_giacenza` è la somma dei movimenti); il costo
medio è il valore diviso la quantità, calcolato dalle viste mettendo insieme **due fonti**, e
vale solo con una giacenza positiva. Per questo, se una riga di valore manca per una giacenza
che c'è, la vista lo mostra (`valore` e `costo_medio` vuoti) invece di nasconderlo.

---

### Nessuna nota

Una copia non ha un autore: chi vuole dire qualcosa di un valore di giacenza lo dice
dell'articolo o del magazzino. Il padre `magazzino.note` non ha una partizione per questa
tabella.

---

### Chi può vedere e scrivere

Nel perimetro RLS via magazzino (`rls_valore_giacenza_ef_whitelist`): un operatore vede i
valori dei magazzini del proprio emittente. Meccanismo comune:
[Linee guida SQL — sezione 10](/linee-guida-sql#10-row-level-security-rls).

L'applicazione ha **solo lettura** su questa tabella: la scrivono la primitiva e il
ricalcolo, che girano con i permessi del proprietario. Il guard di scope risale dal magazzino
all'emittente anche qui.

---

### Test

* `db/pgtap/magazzino/test-valore-giacenza-forma-v1.sql` — la forma della tabella e le viste
  su registro e valore, provate sui valori;
* `db/pgtap/magazzino/test-fn-scrivi-movimento-valore-v1.sql` — la copia aggiornata dalla
  primitiva;
* `db/pgtap/magazzino/test-valore-giacenza-divergenza-owner-v1.sql` — la spia della
  divergenza e il ricalcolo.

---

### Note di migrazione

* 2026-09-15 — `brief-db-magazzino-lotto-1-terreno-vuoto` (§4.6; analisi carico e scarico,
  §7-ter, M-4): la tabella si chiamava `costo_medio`. Esce `qta`, che era una seconda giacenza
  da tenere allineata alla prima; entra la FK verso `catalogo.articoli`, che mancava (una riga
  poteva puntare a un articolo inesistente). La partizione `note_costo_medio` è ritirata e `COSTO_MEDIO` esce dai tipi ammessi dal
  padre `magazzino.note`.
* 2026-09-18 — la primitiva (Lotto 2) tiene aggiornata la copia, e l'app passa a sola
  lettura.

---

{% include-markdown "it/dbzero/magazzino/_dominio-magazzino.md" %}

---

{% include-markdown "signature-core.md" %}
