## 📘 Documentazione Concettuale – Vista `dbops.vw_ddt_emessi_senza_scarico`

> **Ultimo aggiornamento**: 8 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [vendite.ddt](/dbzero/vendite/tabelle/ddt) — le bolle che la vista guarda
> * [vendite.ddt_righe_prelievi](/dbzero/vendite/tabelle/ddt_righe_prelievi) — i prelievi, la sorgente dei movimenti
> * [magazzino.movimenti](/dbzero/magazzino/tabelle/movimenti) — il registro dove l'uscita dovrebbe esserci
> * [dbops.presidi](/dbzero/dbops/tabelle/presidi) — il catalogo che la iscrive
>
> Approfondimento viste:
>
> * [script.vw_stati_doc_ddt_merce_partita](/dbzero/script/views/vw_stati_doc_ddt_merce_partita) — la sede della regola «in questo stato la merce è partita»
> * [dbops.vw_resi_confermati_senza_carico](/dbzero/dbops/views/vw_resi_confermati_senza_carico) — la gemella sul verso opposto: il reso senza carico
> * [dbops.vw_ddt_trasferimenti_consegnati_senza_arrivo](/dbzero/dbops/views/vw_ddt_trasferimenti_consegnati_senza_arrivo) — il presidio dell'arrivo, che questa vista non guarda
>
> Approfondimento funzioni:
>
> * [vendite.fn_ddt_muove_merce](/dbzero/vendite/funzioni/fn_ddt_muove_merce) — se la bolla muove merce
> * [vendite.fn_cambia_stato_ddt](/dbzero/vendite/funzioni/fn_cambia_stato_ddt) — il verbo che emette la bolla e chiama il posting
> * [vendite.fn_posta_ddt](/dbzero/vendite/funzioni/fn_posta_ddt) — il posting: un'uscita per prelievo
> * [script.trgfn_doc_stato_solo_dal_verbo](/dbzero/script/funzioni/trgfn_doc_stato_solo_dal_verbo) — la porta: lo stato della bolla cambia solo dal verbo
> * [dbops.fn_conta_presidio](/dbzero/dbops/funzioni/fn_conta_presidio) — il conteggio del digest
>
> Guide:
>
> * [Gestione DDT](/guide/gestione-ddt) — la bolla e il suo scarico
> * [Presidi e registri del debito](/guide/presidi-e-registri-del-debito) — come si legge un presidio che deve restare vuoto
> * [Sorgente polimorfa](/guide/sorgente-polimorfa) — la provenienza del movimento: documento, riga, dettaglio

---

### 🎯 Scopo Principale

Le bolle uscite con la merce **senza** che il registro di magazzino abbia la loro uscita. Deve
restare vuota: una riga è una giacenza che mente.

---

### La regola che presidia

> **Una bolla che ha fatto partire la merce ha la sua uscita a registro.**

Quando una bolla viene emessa, il verbo che ne cambia lo stato scrive nello stesso gesto un
movimento d'uscita per ogni prelievo. Lo stato della bolla, a sua volta, si cambia solo dal
verbo: è la porta. Se questa vista ha una riga, la porta non ha tenuto, e la bolla è uscita
senza che la merce sia uscita dal registro.

⛔ Il rimedio non è scrivere il movimento a mano: è capire da dove è passata l'emissione.

---

### Quando una bolla entra

Servono quattro fatti insieme:

* la bolla è in uno stato in cui **la merce è partita**: uscita dalla bozza e non annullata. La
  regola non è scritta qui ma in `script.vw_stati_doc_ddt_merce_partita`, che la legge dal
  catalogo degli stati: uno stato nuovo dopo l'emissione entra da solo;
* ha un **magazzino**;
* **muove merce**: la sua causale di trasporto corrisponde a una causale di magazzino e almeno una
  voce è gestita a magazzino (`vendite.fn_ddt_muove_merce`);
* **almeno un prelievo** di una sua riga attiva non ha la sua uscita a registro: un movimento
  che viene dalla bolla (`DDT_VENDITA`), da quella riga e da quel prelievo come dettaglio, con
  quantità negativa, che non sia uno storno.

La domanda è **prelievo per prelievo**, come il contratto del posting (un movimento per ogni
prelievo delle righe attive): anche uno scarico parziale si vede. La colonna
`prelievi_senza_scarico` dice quanti prelievi mancano.

Le bolle senza magazzino sono nate prima che la bolla scaricasse il magazzino, e non sono questo
difetto.

---

### ⚠️ Che cosa non vede

**L'arrivo del trasferimento.** Per una bolla di trasferimento guarda solo l'uscita dal
magazzino di partenza, non il carico nel magazzino d'arrivo: quello lo presidia
`dbops.vw_ddt_trasferimenti_consegnati_senza_arrivo`.

---

### ⛔ Perimetro `DEFINER`

Le tabelle sotto hanno la row level security e la vista è `security_invoker`: una persona la
legge col proprio perimetro. Il digest la conta da proprietario con `dbops.fn_conta_presidio` e
riporta il numero, perché da un percorso senza identità risponderebbe zero per cecità.

Cadenza `GIORNALIERA`: una giacenza falsa si propaga a ogni bolla del giorno dopo.

---

### Test

* `db/pgtap/script/test-vw-stati-doc-ddt-merce-partita-v1.sql`, test 8 — la vista legge la regola
  degli stati dal suo building block, senza un elenco di codici.
* `db/pgtap/dbops/test-presidi-magazzino-grana-v1.sql`, test 1-2 — la bolla tutta scaricata non
  compare; tolta l'uscita di un prelievo su due, compare con un prelievo senza scarico.

---

### Note di migrazione

* 2026-09-28 — nasce con il Lotto 3 del magazzino, lo scarico dalla bolla
  (`brief-db-magazzino-lotto-3-scarico-da-ddt`, P-13).
* 2026-10-12 — lo stato che presuppone lo scarico si legge da `script.vw_stati_doc_ddt_merce_partita`
  (`brief-db-date-consegna-righe-in-blocco` §4.1). Prima era un elenco di codici scritto qui, che
  divergeva al primo stato nuovo.
* 2026-10-25 — la porta del registro passa dal guard di transizione della bolla alla porta comune
  `script.trgfn_doc_stato_solo_dal_verbo` (`brief-modello-documento-vendita` §7).
* 2026-11-08 — la domanda passa da «nessuna uscita» a «prelievo per prelievo», e lo scarico
  parziale si vede (nasce la colonna `prelievi_senza_scarico`); il movimento si riconosce dalla
  provenienza del modello (bolla, riga, prelievo come dettaglio) invece che dal tipo
  `DDT_VENDITA_PRELIEVO`, ritirato.

---

{% include-markdown "signature-core.md" %}
