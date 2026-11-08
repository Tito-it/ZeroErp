## 📘 Documentazione Concettuale – Funzione `dbops.fn_pgtap_crea_reso`

> **Ultimo aggiornamento**: 8 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [vendite.resi](/dbzero/vendite/tabelle/resi) — la testata che la fixture scrive
> * [vendite.resi_righe](/dbzero/vendite/tabelle/resi_righe) — la riga resa, legata alla riga della bolla e alla riga d'ordine
>
> Approfondimento funzioni:
>
> * [vendite.fn_conferma_reso](/dbzero/vendite/funzioni/fn_conferma_reso) — il verbo che conferma il reso
> * [vendite.fn_annulla_reso](/dbzero/vendite/funzioni/fn_annulla_reso) — il verbo dell'annullo, che resta del test
> * [vendite.trgfn_resi_righe_guard_origine_coerente](/dbzero/vendite/funzioni/trgfn_resi_righe_guard_origine_coerente) — il controllo che giudica la riga resa, onere compreso
> * [script.fn_natura_e_merce](/dbzero/script/funzioni/fn_natura_e_merce) — come la fixture riconosce la riga di merce
> * [dbops.fn_pgtap_crea_ddt_da_ordine](/dbzero/dbops/funzioni/fn_pgtap_crea_ddt_da_ordine) — la bolla consegnata su cui si appoggia, se il test non ne dà una
> * [dbops.fn_pgtap_crea_ddt_riconsegna](/dbzero/dbops/funzioni/fn_pgtap_crea_ddt_riconsegna) — la bolla di ri-consegna dopo un reso per ri-consegna
> * [dbops.fn_pgtap_porta_a_stato](/dbzero/dbops/funzioni/fn_pgtap_porta_a_stato) — la strada per confermarlo
> * [script.fn_doc_stato_id](/dbzero/script/funzioni/fn_doc_stato_id) — lo stato chiesto, per codice, fra i soli attivi
>
> Guide:
>
> * [pgTAP — come si scrive un test](/guide/pgtap-come-si-scrive-un-test) — le fixture e quando usarle

---

### 🎯 Scopo Principale

Un reso su una bolla, nello stato chiesto (di norma **confermato**), in una chiamata sola: la
testata legata alla bolla, la riga legata alla riga della bolla e alla riga d'ordine che essa
evade, e la conferma dal verbo del dominio.

---

### ⭐ Perché esiste

Una ventina di test scrivevano il reso a mano: la testata, la riga con articolo, descrizione,
unità e fattore copiati dalla bolla, la riga d'ordine ricavata dal legame (spesso senza un
ordine dichiarato), l'azione di conferma concessa, il verbo. Le regole del reso — merce
davvero consegnata, quantità che non la supera, conferma che pretende i suoi dati — le
soddisfaceva ogni file da sé. Ora la strada ha una sede.

---

### Che cosa decide la fixture e che cosa decide il dominio

* **La bolla** è quella del test, quella del reso a cui si aggiunge una riga (che deve essere
  ancora in bozza perché la riga entri), o una bolla consegnata costruita da
  [dbops.fn_pgtap_crea_ddt_da_ordine](/dbzero/dbops/funzioni/fn_pgtap_crea_ddt_da_ordine).
  Una bolla del test diversa da quella del reso indicato è un errore.
* **La testata** porta solo i dati del reso: la bolla d'origine (come sorgente) e la data,
  se il test la sceglie; senza, vale il default della colonna. Cliente, azienda, numero, stato
  iniziale e magazzino li mettono i trigger del dominio. Del reso il database non ha una
  funzione di creazione (testata e righe le scrive il backend), quindi la fixture fa gli
  inserimenti come li farebbe il backend. Su un reso esistente la data è la sua, e passarla è
  un errore.
* **La riga** punta alla riga della bolla e alla riga d'ordine del legame (la prima, o quella
  del test; nessuna se la bolla non nasce da un ordine). Articolo, descrizione, unità e
  fattore vengono dalla riga della bolla. La quantità è quella del test, in unità operative,
  e deve essere positiva; di norma è la metà della riga della bolla, arrotondata in su. Il
  tipo si sceglie per codice (di norma `RESO_A_CREDITO`).
* **La coerenza** — quantità oltre il consegnato, origine sbagliata, bolla non consegnata,
  cliente — la giudicano i controlli veri del dominio, non la fixture.
* **Lo stato** lo raggiunge [dbops.fn_pgtap_porta_a_stato](/dbzero/dbops/funzioni/fn_pgtap_porta_a_stato),
  che sul reso passa dal verbo [vendite.fn_conferma_reso](/dbzero/vendite/funzioni/fn_conferma_reso)
  e concede all'operatore in sessione l'azione che la matrice chiede per il passaggio: la
  fixture non nomina nessuna azione.

Restituisce il reso, la riga scritta, la bolla e la sua riga, la riga d'ordine, la quantità
base, il tipo e lo stato.

---

### ⭐ La riga resa, se il test non la sceglie, è la prima di merce

Senza una riga indicata dal test, la fixture rende la **prima riga attiva di merce** della
bolla (per numero di riga), non la prima riga: un onere (il trasporto, le spese) non si
rende, e con l'onere al numero 1 la fixture sbaglierebbe bersaglio. «Merce» si legge sulla
natura congelata della riga, con
[script.fn_natura_e_merce](/dbzero/script/funzioni/fn_natura_e_merce).

Una riga indicata dal test si prende così com'è, onere compreso: è così che il test del
rifiuto la chiede, e il rifiuto lo dà il controllo della riga resa (`E_RESO_RIGA_ONERE`).

---

### ⛔ Che cosa non fa

* **Non annulla**: uno stato abortito si rifiuta prima di costruire. L'annullo è del verbo
  [vendite.fn_annulla_reso](/dbzero/vendite/funzioni/fn_annulla_reso): si chiede il reso in
  bozza o confermato e si annulla dal test.
* **Non scrive i rientri di magazzino** né la bolla di ri-consegna: quella è di
  [dbops.fn_pgtap_crea_ddt_riconsegna](/dbzero/dbops/funzioni/fn_pgtap_crea_ddt_riconsegna).

Uno stato che non esiste o è spento (lo stato chiesto lo traduce
[script.fn_doc_stato_id](/dbzero/script/funzioni/fn_doc_stato_id), fra i soli attivi), un tipo,
una bolla, una riga o un reso che non esistono (o non si vedono) fermano la fixture. Esce con i vincoli **richiusi** (`IMMEDIATE`), come ogni helper di fixture.

---

### Test

* `db/pgtap/dbops/test-fn-pgtap-crea-reso-v1.sql` — il reso di default confermato a credito
  per metà riga; i legami della riga; la testata dal dominio; la bozza; la seconda riga sullo
  stesso reso; il tipo per codice; quantità oltre il consegnato e bolla non consegnata
  rifiutate dai controlli veri; gli errori del chiamante rifiutati.
* `db/pgtap/vendite/test-bolla-onere-partita-reso-v1.sql` — con l'onere al numero 1, la
  fixture senza riga chiesta rende la prima riga di merce; il reso chiesto sull'onere è
  rifiutato con `E_RESO_RIGA_ONERE`.

---

### Note di migrazione

* 2026-10-25 — nasce per raccogliere la strada che i test ricopiavano
  (`brief-db-pgtap-reso-costruito`); lo stesso giorno lo stato passa a
  `dbops.fn_pgtap_porta_a_stato`, che concede l'azione del passaggio (§7.7).
* 2026-11-03 — senza riga chiesta, la riga resa è la prima di merce
  (`brief-db-addebito-trasporto-ordine` §8.1).
* 2026-11-08 — lo stato chiesto si traduce dalla sede, fra i soli attivi, invece che da una copia
  della regola.

---

{% include-markdown "it/dbzero/dbops/_fixture-pgtap.md" %}

---

{% include-markdown "signature-core.md" %}
