## 📘 Documentazione Concettuale – Vista `dbops.vw_lotti_congelati_con_errori_da_guardare`

> **Ultimo aggiornamento**: 7 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [vendite.fatturazione_lotti](/dbzero/vendite/tabelle/fatturazione_lotti) — i giri di fatturazione
> * [vendite.fatturazione_lotti_esiti](/dbzero/vendite/tabelle/fatturazione_lotti_esiti) — gli esiti dei documenti del giro
> * [dbops.presidi](/dbzero/dbops/tabelle/presidi) — il catalogo che la iscrive
>
> Approfondimento viste:
>
> * [vendite.vw_lotti_congelati_con_gruppi_in_errore](/dbzero/vendite/views/vw_lotti_congelati_con_gruppi_in_errore) — la sede: definisce la contraddizione
> * [vendite.vw_lotti_fase](/dbzero/vendite/views/vw_lotti_fase) — lo stato fiscale del lotto, l'asse dei due presidi
> * [dbops.vw_lotti_fermi_da_guardare](/dbzero/dbops/views/vw_lotti_fermi_da_guardare) — l'altro presidio dei lotti: il giro pre-fiscale fermo
>
> Approfondimento funzioni:
>
> * [vendite.fn_annulla_lotto_da_draft](/dbzero/vendite/funzioni/fn_annulla_lotto_da_draft) — l'annullo che chiude gli esiti
> * [dbops.fn_conta_presidio](/dbzero/dbops/funzioni/fn_conta_presidio) — il conteggio del digest
>
> Guide:
>
> * [Presidi e registri del debito](/guide/presidi-e-registri-del-debito) — come si legge un presidio che deve restare vuoto

---

### 🎯 Scopo Principale

I lotti di fatturazione **congelati** che contengono documenti in `ERRORE`, qualunque sia lo stato
di esecuzione del giro. Congelato vuol dire che lo stato fiscale del lotto non è più pre-fiscale:
il fiscale è fermo, e quei documenti non sono nati. Deve restare vuota.

---

### ⭐ Un asse solo per i due presidi dei lotti

I due presidi dei lotti si spartiscono lo **stato fiscale**:

| Il lotto | Con un documento in errore lo vede |
| --- | --- |
| pre-fiscale (in bozza) | [dbops.vw_lotti_fermi_da_guardare](/dbzero/dbops/views/vw_lotti_fermi_da_guardare): è un giro fermo, da rilanciare o sciogliere |
| congelato, o con lo stato fiscale ignoto | questa vista: è una contraddizione |

Lo stato di esecuzione del giro (`stato_lotto`) qui è un dato da leggere, non il criterio: un
lotto congelato compare anche se il giro risulta ancora in esecuzione o in errore. Uno stato
fiscale ignoto cade qui, dove un documento in errore resta visibile.

---

### ⭐ È un lettore, non una sede

La contraddizione la definisce `vendite.vw_lotti_congelati_con_gruppi_in_errore`: un lotto
congelato con almeno un esito in `ERRORE`, con quanti sono, il primo e l'ultimo errore, i codici e
lo stato fiscale. Qui si aggiunge solo il codice dell'emittente, per chi arriva dal digest e deve
capire la riga senza aprire il lotto.

---

### ⭐ Le porte

| Porta | Chi la tiene |
| --- | --- |
| un lotto fermo che si dichiara `COMPLETATO` | il database lo rifiuta, col guard di completamento sui lotti |
| un documento marcato `ERRORE` su un lotto già congelato, o un lotto congelato con documenti in errore | nessuno: è ciò che questa vista sorveglia |

Un lotto annullato è congelato, e non compare perché l'annullo gli chiude gli esiti, non perché
qualcuno lo filtri: se gli si riapre un documento in errore, compare.

---

### ⛔ Perimetro `DEFINER`

Le tabelle sotto hanno la row level security e le viste sono `security_invoker`: da una sessione
senza identità risponde zero per cecità. Il digest la conta da proprietario con
`dbops.fn_conta_presidio`; una persona la legge col proprio perimetro. Cadenza `GIORNALIERA`.

⚠️ Sta in `dbops` e non in `vendite`: iscrivere a catalogo una vista di `vendite` porterebbe
l'intero schema nel perimetro del controllo del catalogo dei presidi.

---

### Test

* `db/pgtap/vendite/test-annullamento-chiude-la-vita-v1.sql` — un lotto congelato e completato con
  un documento marcato in errore compare, il conteggio da proprietario lo vede, un lotto annullato
  non compare finché non gli si riapre un documento in errore.
* `db/pgtap/vendite/test-lotti-fermi-verdetto-a-db-v1.sql` — la spartizione: un lotto congelato col
  giro ancora in esecuzione è qui e non fra i fermi; un lotto completato in bozza è fra i fermi e
  non qui; lo stato fiscale ignoto è qui.
* `db/pgtap/vendite/test-lotti-gruppi-esito.sql` — un lotto congelato coi documenti a posto non
  compare, con un documento in errore sì.

---

### Note di migrazione

* 2026-09-23 — nasce, col nome `vw_lotti_chiusi_con_errori_da_guardare`, come presidio a catalogo
  della contraddizione «lotto `COMPLETATO` con documenti in errore», che fino a quel giorno non era
  guardata da nessuno. Lo stesso giorno il database comincia a rifiutare `COMPLETATO` su un lotto
  fermo (`brief-db-annullamento-chiude-la-vita` §9.6).
* 2026-11-07 — l'asse passa dallo stato di esecuzione allo stato fiscale, e la vista prende il nome
  di oggi. Prima un lotto congelato col giro in esecuzione o in errore non lo vedeva nessuno dei due
  presidi, e un lotto completato in bozza lo vedevano tutti e due (`brief-db-revisione-dbops`,
  giro 6).

---

{% include-markdown "signature-core.md" %}
