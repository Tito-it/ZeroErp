## 📘 Documentazione Concettuale – Tabella `config.stati_doc_ordini`

> **Ultimo aggiornamento**: 14 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [vendite.ordini](/dbzero/vendite/tabelle/ordini) — l'ordine di vendita, che porta lo stato (`stato_doc_ordine_id`)
> * [vendite.ordini_righe](/dbzero/vendite/tabelle/ordini_righe) — le righe, che portano anch'esse uno stato di questo vocabolario
> * [acquisti.ordini](/dbzero/acquisti/tabelle/ordini) — l'ordine d'acquisto, che usa lo stesso vocabolario
> * [config.transizioni_stati_ordini](/dbzero/config/tabelle/transizioni_stati_ordini) — i passaggi ammessi fra questi stati
> * [config.esiti_flussi_pratiche](/dbzero/config/tabelle/esiti_flussi_pratiche) — il vocabolario dei verdetti a cui punta `esito`
>
> Approfondimento viste:
>
> * [vendite.vw_stato_sorgente_ordine](/dbzero/vendite/views/vw_stato_sorgente_ordine) — la proiezione dello stato per il motore pratiche
>
> Approfondimento funzioni:
>
> * [script.trgfn_doc_stato_iniziale](/dbzero/script/funzioni/trgfn_doc_stato_iniziale) — fa nascere l'ordine nello stato iniziale
> * [script.fn_stato_emissione_id](/dbzero/script/funzioni/fn_stato_emissione_id) — legge lo stato di `emissione` (la conferma)
> * [script.fn_stato_abortito_id](/dbzero/script/funzioni/fn_stato_abortito_id) — legge lo stato di annullo (`is_abortito`)
> * [script.fn_available_actions_ordine](/dbzero/script/funzioni/fn_available_actions_ordine) — la capability, che legge `emissione`, `meta` e `pdf_mode`
>
> Guide:
>
> * [Il modello del documento di vendita](/guide/modello-documento-di-vendita) — vocabolario, matrice, nascita, emissione e annullo

---

### 🎯 Scopo Principale

`config.stati_doc_ordini` è il **vocabolario degli stati dell'ordine**, di vendita e d'acquisto:
quali stati esistono e, per ciascuno, che cosa significa per il resto del sistema — se l'ordine ci
nasce, se è confermato, se è evaso in parte o del tutto, se è annullato.

Il codice non riconosce uno stato dal suo nome: chi ha bisogno di «lo stato di conferma» lo chiede
a una colonna di questa tabella. I passaggi fra gli stati stanno nella matrice
[`config.transizioni_stati_ordini`](/dbzero/config/tabelle/transizioni_stati_ordini).

---

### Gli stati

| `codice_interno` | Che cosa vuol dire | Marcato da |
| --- | --- | --- |
| `DRAFT` | bozza, si modifica | `iniziale` |
| `CONFERMATO` | l'ordine è confermato al cliente: è la sua emissione | `emissione` |
| `PARZIALMENTE_EVASO` | le bolle ne hanno evaso una parte | — |
| `EVASO` | le bolle lo hanno evaso del tutto | `terminale` |
| `ANNULLATO` | l'ordine è annullato | `is_abortito`, `terminale` |

L'evasione si muove nei due versi: `CONFERMATO`, `PARZIALMENTE_EVASO` ed `EVASO` si inseguono secondo
le bolle emesse e annullate, coi passaggi automatici che scrive la proiezione delle bolle.

Ogni stato si raggiunge dallo stato iniziale lungo la matrice. Spedizione e consegna sono stati della
bolla, la fatturazione è della commessa e della fattura: l'ordine non li ripete, e il vocabolario
non ha stati che nessun passaggio raggiunge. Lo presidia `config/test-stati-raggiungibili-v1`.

`codice_interno` è la chiave stabile e non si modifica (`E_CODICE_NON_MODIFICABILE`). Uno stato
già usato da un ordine o da una riga, di vendita o d'acquisto, o dalla matrice non si disattiva.

---

### ⭐ Gli stati che hanno un significato si leggono da una colonna

Ognuna di queste colonne marca **al più uno stato** (un indice unico parziale) e lo stato marcato
deve essere **attivo** (un CHECK). Spostare il significato su un altro stato è una cella del CSV, e
tutti i lettori seguono.

* **`iniziale`** — lo stato in cui un ordine nasce. Il trigger
  [`script.trgfn_doc_stato_iniziale`](/dbzero/script/funzioni/trgfn_doc_stato_iniziale), montato su
  `vendite.ordini` e su `acquisti.ordini`, mette questo stato quando chi crea non ne dice uno, e
  rifiuta ogni altro con `E_DOC_STATO_INIZIALE_NON_VALIDO`. Anche la generazione di un ordine da un
  preventivo lo fa nascere qui, e lo porta avanti coi passaggi.
* **`emissione`** — lo stato in cui l'ordine è emesso, cioè **confermato**. Ci si arriva solo da
  «Emetti», che genera il PDF; il backend lo rifiuta sul cambio di stato generico. ⚠️ Il numero
  dell'ordine si assegna alla nascita, non all'emissione: è una divergenza dichiarata dalla guida del
  modello.
* **`is_abortito`** — lo stato di annullo, letto dal verbo d'annullo
  ([`vendite.fn_annulla_ordine`](/dbzero/vendite/funzioni/fn_annulla_ordine)) attraverso
  [`script.fn_stato_abortito_id`](/dbzero/script/funzioni/fn_stato_abortito_id).

Il vocabolario dell'ordine **non ha** le colonne `accettazione`, `cessazione` e `scadenza`: chiesti
ai loro lettori, quegli stati sono vuoti.

---

### La proiezione per il motore pratiche: `fase`, `esito`, `terminale`

| `codice_interno` | `fase` | `esito` | `terminale` |
| --- | --- | --- | --- |
| `DRAFT` | `APERTO` | — | no |
| `CONFERMATO` | `IN_CORSO` | — | no |
| `PARZIALMENTE_EVASO` | `IN_CORSO` | — | no |
| `EVASO` | `CHIUSO` | `POSITIVO` | sì |
| `ANNULLATO` | `CHIUSO` | `NEGATIVO` | sì |

* `fase` è obbligatoria e sta nei quattro valori della scala: ogni stato nuovo dichiara la sua.
* `esito` punta a un verdetto di
  [`config.esiti_flussi_pratiche`](/dbzero/config/tabelle/esiti_flussi_pratiche) (lo controlla il
  guard [`config.trgfn_stati_doc_guard_esito_verdetto`](/dbzero/config/funzioni/trgfn_stati_doc_guard_esito_verdetto));
  vuoto vuol dire nessun verdetto.
* `terminale` implica `fase = CHIUSO`.

⚠️ **La mappa è centrata sul ciclo di vendita.** Il vocabolario è condiviso con `acquisti.ordini`,
ma la proiezione legge solo `vendite.ordini`. Un resolver per l'ordine d'acquisto dovrà verificare
che la mappa calzi la sua semantica, o valutare un vocabolario suo.

---

### `meta` e la stampa

* **`meta.nessuna_azione_key`** — sugli stati senza azioni per l'operatore (evaso in parte o del
  tutto, fatturato, annullato), la chiave del testo che spiega perché. La capability la espone come
  `stato_info_key`.
* **`pdf_mode`** e **`pdf_allow_allegati`** — che cosa offre il bottone PDF in quello stato:
  l'anteprima in bozza, l'archivio negli altri. Non hanno un default: uno stato nuovo li dichiara.

Il contenuto di tutte le colonne sta nel CSV `80_data/sql/config/stati_doc_ordini.csv`.

---

### Codici errore

* `E_DOC_STATO_INIZIALE_NON_VALIDO` — un ordine nuovo chiesto in uno stato diverso dall'iniziale.
* `E_CODICE_NON_MODIFICABILE` — una modifica di `codice_interno`.

---

### Test

* `db/pgtap/script/test-trgfn-doc-stato-iniziale-v1.sql` — uno stato iniziale per vocabolario, attivo, e la nascita su vendite e acquisti.
* `db/pgtap/script/test-doc-lettori-stato-e-preventivo-al-modello-v1.sql` — lo stato di emissione dichiarato nei documenti che si emettono.
* `db/pgtap/script/test-capability-motivi-e-nessuna-azione-v1.sql` — ogni stato chiuso dichiara `nessuna_azione_key`.

---

### Note di migrazione

* 2026-10-24 / 2026-10-25 — arrivano `iniziale` ed `emissione` (brief
  `brief-modello-documento-vendita`): la conferma diventa l'emissione dell'ordine, e la conferma
  senza PDF è ritirata.

---

{% include-markdown "signature-core.md" %}
