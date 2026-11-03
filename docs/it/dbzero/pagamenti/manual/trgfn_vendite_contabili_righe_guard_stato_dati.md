## 📘 Documentazione Concettuale – Trigger function `pagamenti.trgfn_vendite_contabili_righe_guard_stato_dati`

> **Ultimo aggiornamento**: 3 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [pagamenti.vendite_contabili_righe](/dbzero/pagamenti/tabelle/vendite_contabili_righe) — la tabella che custodisce
> * [pagamenti.vendite_contabili_righe_stati](/dbzero/pagamenti/tabelle/vendite_contabili_righe_stati) — la bandiera `richiede_abbinamento`
> * [pagamenti.transizioni_stati_contabile_riga](/dbzero/pagamenti/tabelle/transizioni_stati_contabile_riga) — la metà «percorso» della stessa regola
>
> Approfondimento funzioni:
>
> * [pagamenti.trgfn_vendite_contabili_righe_guard_transizione](/dbzero/pagamenti/funzioni/trgfn_vendite_contabili_righe_guard_transizione) — il guard della metà «percorso»
> * [pagamenti.trgfn_vendite_movimenti_sync_contabile_from_riga](/dbzero/pagamenti/funzioni/trgfn_vendite_movimenti_sync_contabile_from_riga) — il rifiuto più a valle, sul movimento

---

### 🎯 Scopo Principale

Pretende che una riga contabile in uno stato che **richiede l'abbinamento** dica a
quale **fattura** e a quale **cliente** appartiene: sono i due dati da cui nasce il movimento
contabile. Senza, si registrerebbe un incasso che non si sa a chi attribuire.

⭐ È la metà **«bagaglio»** della regola di cui le transizioni sono la metà **«percorso»**: la
matrice dice *quando* si può passare, questo guard dice *a quali condizioni sui dati*.

---

### Quali stati lo pretendono lo dice il catalogo

Quali stati pretendano l'abbinamento **non è scritto qui**: lo dice la bandiera
`richiede_abbinamento` del catalogo
[vendite_contabili_righe_stati](/dbzero/pagamenti/tabelle/vendite_contabili_righe_stati) (vera su
`ABBINATA` e `POSTATA`). È la stessa scelta del guard di transizione, per la stessa ragione: una
regola in una tabella si legge e si cambia senza toccare il codice.

⚠️ **Non era derivabile dalle bandiere che c'erano già**: `ABBINATA` pretende l'abbinamento
e **non è finale**, quindi una condizione costruita su `is_final` l'avrebbe mancata del tutto.

---

### ⚠️ La rata resta fuori, ed è una decisione

Su `ABBINATA` la rata è **facoltativa**: la riga del fondo fattura ha fattura sì e rata no,
perché è un saldo per **trasferimento** e non denaro arrivato su una scadenza. La colonna
`scadenza_id` c'è, e il guard non la guarda: chi lo rilegge non deve credere che manchi un
pezzo. Della rata si occupa
[trgfn_vendite_contabili_righe_guard_rata](/dbzero/pagamenti/funzioni/trgfn_vendite_contabili_righe_guard_rata),
che su una rata senza fattura tace apposta per lasciar parlare questo guard.

---

### ⚠️ Guarda anche l'inserimento

A differenza del guard di transizione, scatta anche quando la riga **nasce**: una riga che nasce
già abbinata senza fattura sarebbe sbagliata dal primo istante.

Il messaggio dice **che cosa manca** in italiano («la fattura», «il cliente», «la fattura e il
cliente»), e il contesto porta il **campo** da evidenziare (la fattura, se manca; altrimenti il
cliente).

---

### Codici errore

* `E_RIGA_CONTABILE_ABBINAMENTO_INCOMPLETO` — lo stato richiede l'abbinamento e manca la
  fattura, il cliente o entrambi. È un dato da compilare, non un conflitto di stato: il contesto
  porta la chiave `campo` perché l'interfaccia possa evidenziarlo.

⚠️ È **distinto** da `E_RIGA_CONTABILE_SENZA_ABBINAMENTO`, che scatta molto più tardi nel
trigger di mirror del movimento
([trgfn_vendite_movimenti_sync_contabile_from_riga](/dbzero/pagamenti/funzioni/trgfn_vendite_movimenti_sync_contabile_from_riga)):
lì è un conflitto di stato perché la riga è già arrivata dov'è, qui è l'operatore che la sta
muovendo adesso.

---

### Test

`db/pgtap/pagamenti/test-righe-contabili-guard-dati.sql` — una riga `DA_ABBINARE` senza fattura
entra, una `ABBINATA` senza fattura o senza cliente è rifiutata, una `ABBINATA` completa entra
senza la rata (il test presidia la decisione: se qualcuno «completasse» il guard con la rata, lo
fermerebbe).

---

### Note di migrazione

* 2026-08-21 — nasce insieme alla bandiera `richiede_abbinamento`, scritto già con la
  rata facoltativa, prima che la colonna `scadenza_id` esistesse.
* 2026-08-22 — arriva la colonna della rata; il guard, come previsto, non viene toccato.

---

{% include-markdown "signature-core.md" %}
