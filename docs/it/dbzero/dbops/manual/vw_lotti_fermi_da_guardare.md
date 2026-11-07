## 📘 Documentazione Concettuale – Vista `dbops.vw_lotti_fermi_da_guardare`

> **Ultimo aggiornamento**: 7 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [vendite.fatturazione_lotti](/dbzero/vendite/tabelle/fatturazione_lotti) — i giri di fatturazione e la loro azienda
> * [dbops.presidi](/dbzero/dbops/tabelle/presidi) — il catalogo che la iscrive
>
> Approfondimento viste:
>
> * [vendite.vw_lotti_segnalazioni_summary](/dbzero/vendite/views/vw_lotti_segnalazioni_summary) — la sede: da lì vengono «fermo», il motivo e l'orologio
> * [vendite.vw_lotti_fase](/dbzero/vendite/views/vw_lotti_fase) — l'asse pre-fiscale
> * [dbops.vw_lotti_congelati_con_errori_da_guardare](/dbzero/dbops/views/vw_lotti_congelati_con_errori_da_guardare) — l'altro presidio dei lotti: congelato e in errore
> * [dbops.vw_coda_lavori_da_guardare](/dbzero/dbops/views/vw_coda_lavori_da_guardare) — la stessa soglia di un'ora, per la stessa ragione
>
> Approfondimento funzioni:
>
> * [dbops.fn_conta_presidio](/dbzero/dbops/funzioni/fn_conta_presidio) — il conteggio del digest
>
> Guide:
>
> * [Cruscotti della fatturazione](/guide/cruscotti-fatturazione) — il banner del lotto e il pallino
> * [Presidi e registri del debito](/guide/presidi-e-registri-del-debito) — come si legge un presidio che deve restare vuoto

---

### 🎯 Scopo Principale

I giri di fatturazione **pre-fiscali** fermi da oltre un'ora, che nessuno ha rilanciato né
sciolto. Deve restare vuota.

Il banner lo dice a chi **apre** il lotto; questa riga lo dice a chi **non lo apre**: da qui
arriva al digest dei presidi, al pannello dei processi automatici e al pallino della barra in
alto.

---

### ⭐ È un lettore, non una sede

«Fermo», il motivo e il momento da cui il lotto è fermo **non si calcolano qui**: sono le colonne
di `vendite.vw_lotti_segnalazioni_summary`, la stessa riga che il backend legge per il banner.
Questa vista aggiunge due cose soltanto, la spartizione sull'asse pre-fiscale e la soglia: se
domani il verdetto prende un addendo nuovo, il banner e il digest lo vedono **insieme**.

⛔ Un presidio scritto sopra una copia degli addendi avrebbe detto «tutto a posto» mentre il
banner diceva «fermo», al primo addendo aggiunto in un posto solo. La regola sta a DB, una volta.

---

### Che cosa dice una riga

| Colonne | Che cosa dicono |
| --- | --- |
| il lotto, il codice, la competenza, lo stato | il lotto e la sua fase fiscale |
| l'emittente, col codice | l'azienda, il codice per chi legge la riga a mano |
| `motivo` | **quale addendo** lo ferma, con la precedenza del banner: `CRITICHE`, poi `FATTURE_IN_ERRORE`, poi `ESITI_IN_ERRORE` |
| `fermo_da`, `da_quanto` | il fatto più recente che lo ferma, e da quanto |
| i contatori | le critiche vive (della fattura e del lotto), le righe di ponte e gli esiti in errore, i documenti bloccanti e presi in carico: per capire la riga senza aprire il lotto |

---

### ⭐ Solo i lotti pre-fiscali

Un lotto il cui stato fiscale è congelato non è «fermo» in questo senso: lì non si può più
rilanciare. La parte congelata del ciclo la guarda l'altro presidio dei lotti,
`dbops.vw_lotti_congelati_con_errori_da_guardare`: qui «si può ancora agire e nessuno agisce», là «è
congelato e non doveva».

I due presidi leggono **lo stesso asse**, lo stato fiscale, e si spartiscono tutti i lotti: un
lotto pre-fiscale con un documento in errore è qui, qualunque sia lo stato di esecuzione del giro
(anche un giro che risulta `COMPLETATO`); uno congelato è nell'altro. Nessun lotto è guardato da
tutti e due, nessuno da nessuno.

⚠️ Il pre-fiscale è **fail-closed sull'ignoto**: un lotto senza uno stato fiscale risolvibile non
compare qui, perché un presidio che invitasse a rilanciarlo direbbe la cosa sbagliata. Non resta
scoperto: con un documento in errore lo vede l'altro presidio.

---

### ⚠️ Un'ora è una scelta, non una misura

Il rilancio è il gesto di una **persona**, e le viste delle code usano la stessa soglia per la
stessa ragione: un lotto fallito due minuti fa e già in rilancio non è un allarme.

L'orologio è il fatto **più recente** che ferma il lotto. Un rilancio che fallisce di nuovo scrive
un fatto nuovo e riparte l'orologio: la domanda resta «da quanto nessuno ci mette le mani». La
soglia sta **qui**, non nel catalogo dei presidi.

---

### ⛔ Perimetro `DEFINER`

I lotti e le loro figlie hanno la row level security, e la sede è `security_invoker`: da una
sessione **senza identità** questa vista risponde **zero per cecità**, e «zero righe» e «non ho
potuto vedere» si scrivono uguale. Il digest la **conta** da proprietario con
`dbops.fn_conta_presidio` e riporta il numero; una persona la legge col proprio perimetro.

Sta in `dbops` e non in `vendite` perché il catalogo dei presidi pretende a catalogo ogni vista
degli schemi che vi compaiono, e `vendite` porterebbe dentro tutte le sue viste. Cadenza
`GIORNALIERA`: un giro fermo da ieri sera va visto stamattina.

---

### Test

* `db/pgtap/vendite/test-lotti-fermi-verdetto-a-db-v1.sql`, test 15-19 — la soglia nei due versi,
  la spartizione sul pre-fiscale, il `DEFINER` onesto (senza identità la vista è vuota **e** il
  contatore conta la riga costruita), la riga a catalogo.
* `db/pgtap/vendite/test-lotti-fermi-verdetto-a-db-v1.sql`, test 22-24 — l'asse condiviso con
  l'altro presidio: un lotto congelato col giro in esecuzione è là, un lotto completato in bozza è
  qui, lo stato fiscale ignoto è là.
* `db/pgtap/dbops/test-catalogo-presidi-v1.sql` — la riga a catalogo combacia con la vista.

---

### Note di migrazione

* 2026-09-19 — nasce come sorgente «lotto fermo» che mancava all'osservabilità
  (`brief-db-osservabilita-lotto-fermo-r6-indici` §2, `analisi-osservabilita-log` passo C), lettore
  della sede che Tid aveva deciso il 18-09: la regola va a DB. Su dev nasce piena, con giri di prova
  lasciati a metà, e il pregresso non si esclude per farla partire verde.
* 2026-11-07 — l'altro presidio dei lotti passa sullo stesso asse fiscale e diventa
  `vw_lotti_congelati_con_errori_da_guardare`: finisce il buco (congelato non `COMPLETATO`) e il
  doppione (`COMPLETATO` in bozza). Questa vista non cambia (`brief-db-revisione-dbops`, giro 6).

---

{% include-markdown "signature-core.md" %}
