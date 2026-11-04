## 📘 Documentazione Concettuale – Vista `dbops.vw_lotti_chiusi_con_errori_da_guardare`

> **Ultimo aggiornamento**: 4 novembre 2026
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
> * [vendite.vw_lotti_chiusi_con_gruppi_in_errore](/dbzero/vendite/views/vw_lotti_chiusi_con_gruppi_in_errore) — la sede: definisce la contraddizione
> * [vendite.vw_lotti_fase](/dbzero/vendite/views/vw_lotti_fase) — lo stato fiscale del lotto
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

I lotti di fatturazione chiusi `COMPLETATO` che contengono documenti in `ERRORE`. Deve restare
vuota: o il giro è andato bene, o quei documenti non erano suoi.

---

### ⭐ È un lettore, non una sede

La contraddizione la definisce `vendite.vw_lotti_chiusi_con_gruppi_in_errore`: un lotto
`COMPLETATO` con almeno un esito in `ERRORE`, con quanti sono, il primo e l'ultimo errore e i
codici. Qui si aggiungono solo lo stato fiscale del lotto e il codice dell'emittente, per chi
arriva dal digest e deve capire la riga senza aprire il lotto.

---

### ⭐ Le due porte, e quella che resta aperta

| Porta | Chi la tiene |
| --- | --- |
| un lotto fermo che si dichiara `COMPLETATO` | il database lo rifiuta, col guard di completamento sui lotti |
| un documento marcato `ERRORE` su un lotto già `COMPLETATO` | nessuno: è ciò che questa vista sorveglia |

Un lotto annullato non compare perché l'annullo gli chiude gli esiti, non perché qualcuno lo
filtri.

---

### ⚠️ Che cosa non vede

Solo i lotti `COMPLETATO`. Un lotto chiuso fiscalmente ma con un altro stato di esecuzione, con
documenti in errore, non è qui, e non è nemmeno nel presidio dei lotti fermi, che guarda solo i
giri pre-fiscali.

---

### ⛔ Perimetro `DEFINER`

Le tabelle sotto hanno la row level security e le viste sono `security_invoker`: da una sessione
senza identità risponde zero per cecità. Il digest la conta da proprietario con
`dbops.fn_conta_presidio`; una persona la legge col proprio perimetro. Cadenza `GIORNALIERA`.

⚠️ Sta in `dbops` e non in `vendite`: iscrivere a catalogo una vista di `vendite` porterebbe
l'intero schema nel perimetro del controllo del catalogo dei presidi.

---

### Test

* `db/pgtap/vendite/test-annullamento-chiude-la-vita-v1.sql` — il lotto completato con un documento
  in errore compare con il suo stato fiscale, il conteggio da proprietario lo vede, e un lotto
  annullato non compare.

---

### Note di migrazione

* 2026-09-23 — nasce come presidio a catalogo della contraddizione, che fino a quel giorno non era
  guardata da nessuno: un lotto l'aveva presa senza che nessuno lo sentisse. Lo stesso giorno il
  database comincia a rifiutare `COMPLETATO` su un lotto fermo (`brief-db-annullamento-chiude-la-vita`
  §9.6).

---

{% include-markdown "signature-core.md" %}
