## 📘 Documentazione Concettuale – Funzione `anagrafiche.fn_consuma_plafond_titolo_iva_righe`

> **Ultimo aggiornamento**: 22 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [anagrafiche.soggetti_titoli_iva](/dbzero/anagrafiche/tabelle/soggetti_titoli_iva) — il titolo di cui consuma il tetto
> * [anagrafiche.soggetti_titoli_iva_movimenti](/dbzero/anagrafiche/tabelle/soggetti_titoli_iva_movimenti) — il registro in cui scrive
> * [vendite.fatture_righe](/dbzero/vendite/tabelle/fatture_righe) — le righe che consumano
>
> Approfondimento viste:
>
> * [vendite.vw_fattura_righe_esposte](/dbzero/vendite/views/vw_fattura_righe_esposte) — dove una riga spezzata diventa due righe in fattura
>
> Approfondimento funzioni:
>
> * [vendite.fn_resolve_iva_riga](/dbzero/vendite/funzioni/fn_resolve_iva_riga) — dice quale titolo vale su una riga, non quanto copre
> * [anagrafiche.trgfn_soggetti_titoli_iva_movimenti_accumulatore](/dbzero/anagrafiche/funzioni/trgfn_soggetti_titoli_iva_movimenti_accumulatore) — chi riporta il consumato alla somma

---

### 🎯 Scopo Principale

`anagrafiche.fn_consuma_plafond_titolo_iva_righe` consuma il plafond di un titolo IVA per le righe di una fattura
che stanno sotto quel titolo, e dice per ogni riga quanta parte va al titolo e quanta torna all'aliquota ordinaria.
Scrive un movimento di fattura per ogni riga con una quota, col segno della riga.

---

### ⭐ La fattura consuma il suo netto

Le righe positive consumano, le negative (uno sconto, un componente di kit negativo) restituiscono. Una fattura non
consuma più della capienza del titolo e non restituisce più di quanto essa stessa consuma: restituire plafond
consumato da un altro documento è della nota di credito, che quel documento lo nomina.

Per esempio: residuo 500, merce 1000 e sconto −100. Netto 900, coperti 500: la merce va al titolo per 600 e
all'ordinaria per 400, lo sconto va al titolo per −100. Nel registro: +600 e −100, cioè 500.

---

### Come divide

1. **I gruppi.** Le righe con la stessa `kit_key` sono un gruppo: un kit si spezza come un'unità sola, con la
   stessa frazione per tutti i componenti. Una riga fuori da un kit è un gruppo da sola. I gruppi li fa la
   funzione leggendo le righe, nell'ordine di stampa (la loro prima riga): a plafond quasi esaurito, è l'ordine a
   decidere chi resta coperto.
2. **La quota di ogni gruppo**, sul netto. I gruppi negativi si coprono, in ordine, fino a quanto valgono i
   positivi; il negativo che avanza resta all'ordinaria. I gruppi positivi si coprono, in ordine, fino alla
   capienza più quanto hanno restituito i negativi: il primo per intero, poi uno spezzato, poi gli altri
   all'ordinaria. Un gruppo a netto zero (un omaggio nel kit, o +50 e −50) è coperto per intero: non consuma
   niente. La capienza di un titolo già sfondato da una forzatura vale zero, non un numero negativo.
3. **Dentro il gruppo** la frazione è una: ogni riga ne prende la sua parte, arrotondata alla scala del suo
   importo, e il resto dei centesimi va alla riga di valore assoluto più grande dello stesso segno del gruppo (a
   pari merito l'ultima), poi alle successive. Nessuna quota cambia segno né supera il suo importo, e la somma è
   esatta.
4. **Il registro.** Un movimento per riga con quota diversa da zero, col segno della riga: prima tutti i positivi,
   poi i negativi, perché l'accumulatore rifiuta il conto sotto zero a ogni riga scritta.

Gli importi si calcolano alla scala del registro, troncando verso lo zero: ogni quota diventa un movimento, e il
movimento deve essere esattamente la quota. Le frazioni di centesimo di un importo di riga restano all'ordinaria.

Per ogni riga restituisce l'importo, la quota coperta e quella ordinaria (che sommano all'importo), la frazione del
suo gruppo (con cui chi chiama divide anche quantità e numero di kit), il residuo del titolo dopo la fattura e il
movimento scritto.

---

### Le regole del consumo

* **Chi sceglie il titolo è chi chiama**: risolve ogni gruppo col risolutore nella domanda di consumo (un kit
  sull'articolo padre) e passa qui, in una chiamata, tutte le righe di quel titolo.
* **Le righe** devono essere della fattura passata, capofila (una parte non consuma: il movimento sta sulla
  capofila) e non rettifiche (la loro IVA è quella della riga che rettificano). Un kit si passa intero: a metà, due
  chiamate gli darebbero due frazioni diverse. Nessuna riga assente o ripetuta.
* **Gli importi** passati devono essere quelli delle righe: se una riga è cambiata dopo che chi chiama l'ha letta,
  la chiamata si ferma invece di spezzare un numero che non c'è più.
* **La data** è un parametro e non l'orologio: il lotto può girare il giorno dopo la data documento. Deve cadere
  nella validità del titolo (`E_TITOLO_IVA_CONSUMO_FUORI_VALIDITA`).
* **Il lock**: la riga del titolo si blocca per tutta l'operazione, così due fatture che diventano definitive
  insieme si mettono in fila, e la seconda legge il residuo già aggiornato dalla prima.
* **Un titolo senza tetto** copre tutto e non scrive niente.
* **Idempotenza**: se una delle righe ha già un movimento su questo titolo per questa fattura, la funzione rilegge
  il registro invece di scrivere. La quota di ogni riga è il suo movimento, zero dove non c'è.

Non è il risolutore, che non consuma, e non fa la restituzione della nota di credito.

---

### ⚠️ Che cosa oggi non copre

* **Il titolo non si confronta con la fattura.** La funzione non verifica che il titolo sia del cliente e
  dell'emittente della fattura: un titolo di un altro soggetto consumerebbe il suo plafond per una fattura non
  sua. Lo garantisce chi chiama, che il titolo l'ha avuto dal risolutore.
* **Un titolo spento** non si ferma qui: il consumo si scrive, e lo rifiuta alla conferma dell'operazione il
  controllo del padre attivo sul registro (`E_ATTIVO_PADRE_NON_ATTIVO`).

---

### Codici errore

* `E_TITOLO_IVA_CONSUMO_NON_INVOCABILE` — una chiamata rotta: titolo o fattura non indicati o inesistenti, righe
  assenti, ripetute, di un'altra fattura, non capofila o rettifiche, un kit a metà, importi diversi da quelli delle
  righe, data assente.
* `E_TITOLO_IVA_CONSUMO_FUORI_VALIDITA` — la data del consumo è fuori dalla validità del titolo.

---

### Test

* `db/pgtap/anagrafiche/test-consuma-plafond-titolo-iva-righe-v1.sql` — la frazione unica di un kit, il resto dei
  centesimi, la capienza piena e quella esaurita, il titolo senza tetto, lo sconto e il componente negativo, il kit
  a netto zero, la riga negativa senza positivi, l'ordine di stampa, l'idempotenza, i rifiuti della chiamata.
* `db/pgtap/anagrafiche/test-soggetti-titoli-iva.sql` — il consumo entro la capienza, quello oltre che si spezza,
  la stessa fattura che non consuma due volte, il consumo fuori validità.
* `db/pgtap/anagrafiche/test-soggetti-titoli-iva-due-emittenti.sql` — il consumo su un titolo non tocca quello dello
  stesso soggetto verso un altro emittente.

---

### Note di migrazione

* 2026-10-03 — nasce, per spezzare un kit con una frazione sola.
* 2026-10-04 — il consumo passa al netto della fattura, e prende il posto della forma a una riga
  `fn_consuma_plafond_titolo_iva`, ritirata: chiamata per ogni componente non poteva dare una frazione unica,
  perché il residuo cambiava a ogni chiamata. Con lei esce il movimento di fattura senza riga.

---

{% include-markdown "signature-core.md" %}
