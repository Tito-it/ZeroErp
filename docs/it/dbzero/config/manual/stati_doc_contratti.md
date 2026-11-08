## 📘 Documentazione Concettuale – Tabella `config.stati_doc_contratti`

> **Ultimo aggiornamento**: 8 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [vendite.contratti](/dbzero/vendite/tabelle/contratti) — il documento che porta lo stato (`stato_doc_contratto_id`)
> * [config.transizioni_stati_contratti](/dbzero/config/tabelle/transizioni_stati_contratti) — i passaggi ammessi fra questi stati
> * [config.esiti_flussi_pratiche](/dbzero/config/tabelle/esiti_flussi_pratiche) — il vocabolario dei verdetti a cui punta `esito`
>
> Approfondimento viste:
>
> * [vendite.vw_stato_sorgente_contratto](/dbzero/vendite/views/vw_stato_sorgente_contratto) — la proiezione dello stato per il motore pratiche
>
> Approfondimento funzioni:
>
> * [script.fn_stato_iniziale_id](/dbzero/script/funzioni/fn_stato_iniziale_id) — legge lo stato `iniziale`
> * [script.trgfn_doc_stato_iniziale](/dbzero/script/funzioni/trgfn_doc_stato_iniziale) — fa nascere il contratto nello stato iniziale
> * [script.fn_stato_emissione_id](/dbzero/script/funzioni/fn_stato_emissione_id) — legge lo stato di `emissione` (l'attivazione)
> * [script.fn_stato_cessazione_id](/dbzero/script/funzioni/fn_stato_cessazione_id) — legge lo stato di `cessazione`
> * [script.fn_stato_abortito_id](/dbzero/script/funzioni/fn_stato_abortito_id) — legge lo stato di annullo (`is_abortito`)
> * [vendite.trgfn_doc_snapshot_da_stato](/dbzero/vendite/funzioni/trgfn_doc_snapshot_da_stato) — copia `is_abortito` e `is_bozza` sul contratto
> * [script.fn_available_actions_contratto](/dbzero/script/funzioni/fn_available_actions_contratto) — la capability, che legge `meta` e `pdf_mode`
>
> Guide:
>
> * [Il modello del documento di vendita](/guide/modello-documento-di-vendita) — vocabolario, matrice, nascita, emissione e annullo

---

### 🎯 Scopo Principale

`config.stati_doc_contratti` è il **vocabolario degli stati del contratto commerciale**: quali
stati esistono e, per ciascuno, che cosa significa per il resto del sistema — se il contratto ci
nasce, se è attivo, se è cessato o annullato, se partecipa all'esclusività del periodo.

Il codice non riconosce uno stato dal suo nome: chi ha bisogno di «lo stato in cui il contratto è
attivo» o «lo stato di cessazione» lo chiede a una colonna di questa tabella, attraverso il suo
lettore. I passaggi fra gli stati stanno nella matrice
[`config.transizioni_stati_contratti`](/dbzero/config/tabelle/transizioni_stati_contratti).

---

### Gli stati

| `codice_interno` | Che cosa vuol dire | Marcato da |
| --- | --- | --- |
| `DRAFT` | bozza in costruzione: si modifica tutto; non partecipa all'esclusività del periodo | `iniziale`, `is_bozza` |
| `ATTIVO` | il contratto è in vigore: lo usa il prezzo, si fattura | `emissione` |
| `CESSATO` | il contratto ha finito il suo corso, alla sua data di fine | `cessazione`, `terminale` |
| `ANNULLATO` | la bozza è stata annullata prima dell'attivazione | `is_abortito`, `terminale` |

`codice_interno` è la chiave stabile e non si modifica (`E_CODICE_NON_MODIFICABILE`). Uno stato
già usato da un contratto o da una riga della matrice non si disattiva.

---

### ⭐ Gli stati che hanno un significato si leggono da una colonna

Ognuna di queste colonne marca **al più uno stato** (un indice unico parziale) e lo stato marcato
deve essere **attivo** (un CHECK). Spostare il significato su un altro stato è una cella del CSV, e
tutti i lettori seguono.

* **`iniziale`** — lo stato in cui un contratto nasce. Il trigger
  [`script.trgfn_doc_stato_iniziale`](/dbzero/script/funzioni/trgfn_doc_stato_iniziale) su
  `vendite.contratti` mette questo stato quando chi crea non ne dice uno, e rifiuta ogni altro con
  `E_DOC_STATO_INIZIALE_NON_VALIDO`. Gli altri stati si raggiungono solo coi passaggi.
* **`emissione`** — lo stato in cui il contratto è emesso, cioè **attivato**. Ci si arriva solo da
  «Emetti», che genera il PDF (il numero del contratto si assegna alla nascita, non all'emissione:
  divergenza dichiarata dalla guida del modello). Il backend chiede a
  [`script.fn_doc_azione_passaggio`](/dbzero/script/funzioni/fn_doc_azione_passaggio) se il passaggio
  porta in emissione e, se sì, lo rifiuta sul cambio di stato generico. La leggono anche il job delle
  scadenze e la maturazione degli addebiti, per sapere quali contratti sono in corso.
* **`cessazione`** — lo stato in cui il contratto è cessato. Ci portano il verbo della cessazione
  ([`vendite.fn_cessa_contratto`](/dbzero/vendite/funzioni/fn_cessa_contratto)) e il job delle
  scadenze ([`vendite.fn_cessa_contratti_scaduti`](/dbzero/vendite/funzioni/fn_cessa_contratti_scaduti));
  la leggono la generazione dei canoni
  ([`vendite.fn_contratti_addebiti_maturati`](/dbzero/vendite/funzioni/fn_contratti_addebiti_maturati)),
  il guard di transizione del contratto e i controlli della distinta in `pagamenti`.
* **`is_abortito`** — lo stato di annullo. Lo legge il verbo d'annullo
  ([`vendite.fn_annulla_contratto`](/dbzero/vendite/funzioni/fn_annulla_contratto)) attraverso
  [`script.fn_stato_abortito_id`](/dbzero/script/funzioni/fn_stato_abortito_id).

Il vocabolario del contratto **non ha** la colonna `accettazione`: chiesto al suo lettore, lo stato
di accettazione del contratto è vuoto.

---

### `is_bozza` e `is_abortito` decidono chi partecipa all'esclusività del periodo

Due contratti con lo stesso account di fatturazione, la stessa fornitura e lo stesso ambito non possono avere
periodi di validità che si sovrappongono. Il vincolo (`ex_contratti_no_overlap` su
`vendite.contratti`) non legge questa tabella: legge la colonna calcolata
`partecipa_overlap_snapshot` del contratto, che è vera quando il contratto **non è in bozza e non è
annullato**.

Le due metà arrivano da qui: il trigger
[`vendite.trgfn_doc_snapshot_da_stato`](/dbzero/vendite/funzioni/trgfn_doc_snapshot_da_stato) copia
`is_bozza` e `is_abortito` dello stato sul contratto (`is_draft_snapshot`, `is_abortito_snapshot`) a
ogni scrittura. Una bozza quindi non occupa il periodo, e un'annullata lo libera.

⚠️ `terminale` non sostituisce `is_abortito`: `CESSATO` è terminale ma occupa ancora il suo periodo,
perché è la storia di un contratto che è stato in vigore; `ANNULLATO` è terminale e non lo occupa.

---

### La proiezione per il motore pratiche: `fase`, `esito`, `terminale`

Il motore pratiche non conosce i codici dei contratti: ragiona su una scala comune a tutti i
documenti, che ogni stato dichiara qui.

| `codice_interno` | `fase` | `esito` | `terminale` |
| --- | --- | --- | --- |
| `DRAFT` | `APERTO` | — | no |
| `ATTIVO` | `IN_CORSO` | — | no |
| `CESSATO` | `CHIUSO` | `POSITIVO` | sì |
| `ANNULLATO` | `CHIUSO` | `NEGATIVO` | sì |

* `fase` è obbligatoria e sta nei quattro valori della scala: ogni stato nuovo dichiara la sua.
* `esito` punta a un verdetto di
  [`config.esiti_flussi_pratiche`](/dbzero/config/tabelle/esiti_flussi_pratiche) (lo controlla il
  guard [`config.trgfn_stati_doc_guard_esito_verdetto`](/dbzero/config/funzioni/trgfn_stati_doc_guard_esito_verdetto));
  vuoto vuol dire nessun verdetto.
* `terminale` implica `fase = CHIUSO`.

La proiezione la espone [`vendite.vw_stato_sorgente_contratto`](/dbzero/vendite/views/vw_stato_sorgente_contratto).

---

### `meta` e la stampa

* **`meta.nessuna_azione_key`** — sugli stati chiusi (`CESSATO`, `ANNULLATO`), la chiave del testo
  che spiega all'operatore perché non ci sono azioni. La capability la espone come
  `stato_info_key`: i due nomi sono diversi di proposito, perché il controllo delle chiavi di
  traduzione cerca quelle seminate col nome della proprietà.
* **`pdf_mode`** e **`pdf_allow_allegati`** — che cosa offre il bottone PDF in quello stato:
  l'anteprima in bozza, l'archivio negli altri. Non hanno un default: uno stato nuovo li dichiara.

Il contenuto di tutte le colonne, `meta` compreso, sta nel CSV
`80_data/sql/config/stati_doc_contratti.csv`: si cambia lì, non con un `UPDATE`.

---

### Codici errore

* `E_DOC_STATO_INIZIALE_NON_VALIDO` — un contratto nuovo chiesto in uno stato diverso dall'iniziale.
* `E_CODICE_NON_MODIFICABILE` — una modifica di `codice_interno`.

---

### Test

* `db/pgtap/script/test-trgfn-doc-stato-iniziale-v1.sql` — uno stato iniziale per vocabolario, attivo, e la nascita.
* `db/pgtap/script/test-doc-stati-dal-vocabolario-v1.sql` — i lettori di `emissione`, `cessazione` e degli altri stati marcati.
* `db/pgtap/vendite/test-contratto-al-modello-v1.sql` — il contratto sul modello del documento.
* `db/pgtap/vendite/test-contratto-attiva-spento-se-sovrapposto-v1.sql` — la bozza fuori dall'esclusività del periodo.

---

### Note di migrazione

* 2026-05-28 — nasce la matrice `config.transizioni_stati_contratti`; la chiave `meta.outgoing_action`,
  che descriveva il bottone nello stato sorgente, smette di essere letta ed esce dal CSV.
* 2026-08-06 — il CSV diventa la sede unica di `meta`: i vecchi `UPDATE` che lo scrivevano sono
  spenti, perché su un database ricostruito da zero riportavano in vita le chiavi vecchie.
* 2026-10-24 / 2026-10-31 — arrivano `iniziale`, `emissione` e `cessazione` (brief
  `brief-modello-documento-vendita`): il codice smette di scrivere `'DRAFT'`, `'ATTIVO'`, `'CESSATO'`.

---

{% include-markdown "signature-core.md" %}
