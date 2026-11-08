## 📘 Documentazione Concettuale – Vista `dbops.vw_resi_confermati_senza_carico`

> **Ultimo aggiornamento**: 8 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [vendite.resi](/dbzero/vendite/tabelle/resi) — i resi che la vista guarda
> * [vendite.resi_righe_rientri](/dbzero/vendite/tabelle/resi_righe_rientri) — i rientri, la sorgente dei carichi
> * [config.stati_doc_reso](/dbzero/config/tabelle/stati_doc_reso) — gli stati del reso
> * [magazzino.movimenti](/dbzero/magazzino/tabelle/movimenti) — il registro dove il carico dovrebbe esserci
> * [dbops.presidi](/dbzero/dbops/tabelle/presidi) — il catalogo che la iscrive
>
> Approfondimento viste:
>
> * [dbops.vw_ddt_emessi_senza_scarico](/dbzero/dbops/views/vw_ddt_emessi_senza_scarico) — la gemella sul verso opposto: la bolla senza scarico
> * [script.vw_stati_doc_reso_merce_rientrata](/dbzero/script/views/vw_stati_doc_reso_merce_rientrata) — la sede della regola «in questo stato la merce è rientrata»
>
> Approfondimento funzioni:
>
> * [vendite.fn_reso_muove_merce](/dbzero/vendite/funzioni/fn_reso_muove_merce) — se il reso fa rientrare merce
> * [vendite.fn_conferma_reso](/dbzero/vendite/funzioni/fn_conferma_reso) — il verbo che conferma il reso e chiama il posting
> * [vendite.fn_posta_reso](/dbzero/vendite/funzioni/fn_posta_reso) — il posting: un carico per rientro
> * [script.trgfn_doc_stato_solo_dal_verbo](/dbzero/script/funzioni/trgfn_doc_stato_solo_dal_verbo) — la porta: lo stato del reso cambia solo dal verbo
> * [dbops.fn_conta_presidio](/dbzero/dbops/funzioni/fn_conta_presidio) — il conteggio del digest
>
> Guide:
>
> * [Presidi e registri del debito](/guide/presidi-e-registri-del-debito) — come si legge un presidio che deve restare vuoto
> * [Sorgente polimorfa](/guide/sorgente-polimorfa) — la provenienza del movimento: documento, riga, dettaglio

---

### 🎯 Scopo Principale

I resi confermati che fanno rientrare merce **senza** che il registro di magazzino abbia il loro
carico. Deve restare vuota: una riga è merce tornata dal cliente che la giacenza non vede.

---

### La regola che presidia

> **Un reso confermato che fa rientrare merce ha il suo carico a registro.**

Quando un reso viene confermato, il verbo scrive nello stesso gesto un carico per ogni rientro.
Lo stato del reso si cambia solo dal verbo: è la porta. Se questa vista ha una riga, la porta non
ha tenuto.

⛔ Il rimedio non è scrivere il movimento a mano: è capire da dove è passata la conferma.

È la stessa domanda della gemella della bolla, sul verso opposto: un documento ha passato lo stato
che muove merce, e le sue sorgenti non hanno il movimento.

---

### Quando un reso entra

Servono quattro fatti insieme:

* il reso è in uno stato in cui **la merce è rientrata**: uscito dalla bozza e non annullato. La
  regola non è scritta qui ma in `script.vw_stati_doc_reso_merce_rientrata`, che la legge dal
  catalogo degli stati: uno stato nuovo dopo la conferma entra da solo;
* ha un **magazzino**;
* **fa rientrare merce**: almeno una riga attiva viene da una riga di bolla che aveva prelievi
  (`vendite.fn_reso_muove_merce`);
* **almeno un rientro** di una sua riga attiva non ha il suo carico a registro: un movimento che
  viene dal reso (`RESO_VENDITA`), da quella riga e da quel rientro come dettaglio, con quantità
  positiva, che non sia uno storno.

La domanda è **rientro per rientro**, come il contratto del posting (un carico per ogni rientro
delle righe attive): anche un carico parziale si vede. La colonna `rientri_senza_carico` dice
quanti rientri mancano.

I resi confermati prima che il reso caricasse il magazzino non hanno magazzino, e non sono questo
difetto. Un reso annullato non compare: in quello stato la merce non è rientrata.

---

### ⛔ Perimetro `DEFINER`

Le tabelle sotto hanno la row level security e la vista è `security_invoker`: una persona la
legge col proprio perimetro. Il digest la conta da proprietario con `dbops.fn_conta_presidio` e
riporta il numero. Cadenza `GIORNALIERA`, come la gemella.

---

### Test

* `db/pgtap/magazzino/test-reso-carico-v1.sql`, test 17 — un reso confermato dal verbo, col suo
  carico, non compare nella vista.
* `db/pgtap/dbops/test-presidi-magazzino-grana-v1.sql`, test 3-4 e 7 — il reso tutto caricato non
  compare; tolto il carico di un rientro su due, compare con un rientro senza carico; portato in uno
  stato nuovo dopo la conferma, resta nella vista, perché lo stato viene dal building block.

---

### Note di migrazione

* 2026-09-28 — nasce con il Lotto 3-bis del magazzino, il carico dal reso
  (`brief-db-magazzino-lotto-3-bis-carico-da-reso`, P-13).
* 2026-10-25 — la porta del registro passa dal guard di transizione del reso alla porta comune
  `script.trgfn_doc_stato_solo_dal_verbo` (`brief-modello-documento-vendita` §7).
* 2026-11-08 — lo stato si legge da `script.vw_stati_doc_reso_merce_rientrata` invece che dal codice
  `CONFERMATO` scritto qui; la domanda passa da «nessun carico» a «rientro per rientro», e il carico
  parziale si vede (nasce la colonna `rientri_senza_carico`); il movimento si riconosce dalla
  provenienza del modello (reso, riga, rientro come dettaglio) invece che dal tipo
  `RESO_VENDITA_RIENTRO`, ritirato.

---

{% include-markdown "signature-core.md" %}
