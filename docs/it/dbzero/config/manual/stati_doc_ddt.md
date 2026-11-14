## 📘 Documentazione Concettuale – Tabella `config.stati_doc_ddt`

> **Ultimo aggiornamento**: 14 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [vendite.ddt](/dbzero/vendite/tabelle/ddt) — il DDT di vendita, che porta lo stato (`stato_doc_ddt_id`)
> * [acquisti.ddt](/dbzero/acquisti/tabelle/ddt) — il DDT d'acquisto, che usa lo stesso vocabolario
> * [config.transizioni_stati_ddt](/dbzero/config/tabelle/transizioni_stati_ddt) — i passaggi ammessi fra questi stati
> * [config.stati_doc_reso](/dbzero/config/tabelle/stati_doc_reso) — gli stati del reso, che nasce da un DDT consegnato
>
> Approfondimento viste:
>
> * [vendite.vw_stato_sorgente_ddt](/dbzero/vendite/views/vw_stato_sorgente_ddt) — la proiezione dello stato per il motore pratiche
>
> Approfondimento funzioni:
>
> * [script.trgfn_doc_stato_iniziale](/dbzero/script/funzioni/trgfn_doc_stato_iniziale) — fa nascere il DDT nello stato iniziale
> * [script.fn_stato_emissione_id](/dbzero/script/funzioni/fn_stato_emissione_id) — legge lo stato di `emissione`
> * [script.fn_stato_abortito_id](/dbzero/script/funzioni/fn_stato_abortito_id) — legge lo stato di annullo (`is_abortito`)
> * [vendite.fn_cambia_stato_ddt](/dbzero/vendite/funzioni/fn_cambia_stato_ddt) — il verbo di stato del DDT
> * [script.fn_available_actions_ddt](/dbzero/script/funzioni/fn_available_actions_ddt) — la capability, che legge `meta` e `pdf_mode`
>
> Guide:
>
> * [Il modello del documento di vendita](/guide/modello-documento-di-vendita) — vocabolario, matrice, nascita, emissione e annullo

---

### 🎯 Scopo Principale

`config.stati_doc_ddt` è il **vocabolario degli stati del documento di trasporto**, di vendita e
d'acquisto: quali stati esistono e, per ciascuno, che cosa significa per il resto del sistema — se
il DDT ci nasce, se è emesso, se è annullato, a che punto è del suo ciclo.

Il codice non riconosce uno stato dal suo nome: chi ha bisogno di «lo stato di emissione» lo chiede
a una colonna di questa tabella, attraverso il suo lettore. I passaggi fra gli stati stanno nella
matrice [`config.transizioni_stati_ddt`](/dbzero/config/tabelle/transizioni_stati_ddt).

---

### Gli stati

| `codice_interno` | Che cosa vuol dire | Marcato da |
| --- | --- | --- |
| `DRAFT` | bozza: righe, indirizzi e causale si cambiano, nessun numero | `iniziale` |
| `EMESSO` | il DDT è emesso: ha il numero e il PDF, le righe non si cambiano più | `emissione` |
| `SPEDITO` | la merce è in viaggio | — |
| `CONSEGNATO` | la merce è arrivata al cliente; da qui un reso si fa col documento di reso | — |
| `RESO` | la merce è tornata indietro | — |
| `ANNULLATO` | il DDT è annullato | `is_abortito` |

`codice_interno` è la chiave stabile e non si modifica (`E_CODICE_NON_MODIFICABILE`). Uno stato
già usato da un DDT, di vendita o d'acquisto, o da una riga della matrice non si disattiva.

---

### ⭐ Gli stati che hanno un significato si leggono da una colonna

Ognuna di queste colonne marca **al più uno stato** (un indice unico parziale) e lo stato marcato
deve essere **attivo** (un CHECK). Spostare il significato su un altro stato è una cella del CSV, e
tutti i lettori seguono.

* **`iniziale`** — lo stato in cui un DDT nasce. Il trigger
  [`script.trgfn_doc_stato_iniziale`](/dbzero/script/funzioni/trgfn_doc_stato_iniziale), montato su
  `vendite.ddt` e su `acquisti.ddt`, mette questo stato quando chi crea non ne dice uno, e rifiuta
  ogni altro con `E_DOC_STATO_INIZIALE_NON_VALIDO`. Gli altri stati si raggiungono solo coi passaggi,
  dove stanno le condizioni (righe, indirizzi, causale).
* **`emissione`** — lo stato in cui il DDT è emesso: ci si arriva solo da «Emetti», che produce
  numero e PDF insieme. Il backend chiede a
  [`script.fn_doc_azione_passaggio`](/dbzero/script/funzioni/fn_doc_azione_passaggio) se il passaggio
  porta in emissione e, se sì, lo rifiuta sul cambio di stato generico; il verbo
  [`vendite.fn_cambia_stato_ddt`](/dbzero/vendite/funzioni/fn_cambia_stato_ddt) lo legge per sapere
  quando il passaggio è un'emissione.
* **`is_abortito`** — lo stato di annullo, letto dal verbo di stato attraverso
  [`script.fn_stato_abortito_id`](/dbzero/script/funzioni/fn_stato_abortito_id).

Il vocabolario del DDT **non ha** le colonne `accettazione`, `cessazione` e `scadenza`: chiesti ai
loro lettori, quegli stati sono vuoti.

---

### `fase` e la proiezione per il motore pratiche

Ogni stato dichiara la sua `fase` sulla scala comune a tutti i documenti (`APERTO`, `IN_ATTESA`,
`IN_CORSO`, `CHIUSO`): `DRAFT` è aperto, `EMESSO` e `SPEDITO` sono in corso, `CONSEGNATO`, `RESO` e
`ANNULLATO` sono chiusi. La legge anche la genealogia dei documenti: la frontiera esclude i DDT in
fase chiusa o annullati.

Come preventivi, offerte, ordini e contratti, il vocabolario dichiara **`esito`** e **`terminale`**,
e la vista [`vendite.vw_stato_sorgente_ddt`](/dbzero/vendite/views/vw_stato_sorgente_ddt) li passa
così come sono:

| Stato | `esito` | `terminale` |
| --- | --- | --- |
| `DRAFT`, `EMESSO`, `SPEDITO` | *(nessuno)* | ❌ |
| `CONSEGNATO`, `RESO` | `POSITIVO` | ✅ |
| `ANNULLATO` | `NEGATIVO` | ✅ |

* **`esito`** è un verdetto di
  [`config.esiti_flussi_pratiche`](/dbzero/config/tabelle/esiti_flussi_pratiche), o vuoto (lo controlla
  [`config.trgfn_stati_doc_guard_esito_verdetto`](/dbzero/config/funzioni/trgfn_stati_doc_guard_esito_verdetto)).
  La bolla resa è `POSITIVO`: la merce tornata non è un documento annullato.
* **`terminale`** vuol dire che dallo stato non esce nessun passaggio a mano. Il sistema può ancora
  spostare la bolla coi passaggi di processo (`CONSEGNATO → RESO`). Implica `fase = CHIUSO`; lo fa
  rispettare [`script.trgfn_doc_terminale_senza_uscita_manuale`](/dbzero/script/manual/fn_doc_terminali_con_uscita_manuale).

---

### `meta` e la stampa

* **`meta.nessuna_azione_key`** — sugli stati chiusi, la chiave del testo che spiega all'operatore
  perché non ci sono azioni (per `CONSEGNATO`, che il reso si fa col suo documento). La capability
  la espone come `stato_info_key`.
* **`pdf_mode`** e **`pdf_allow_allegati`** — che cosa offre il bottone PDF in quello stato:
  l'anteprima in bozza, l'archivio negli altri. Non hanno un default: uno stato nuovo li dichiara.

Il contenuto di tutte le colonne sta nel CSV `80_data/sql/config/stati_doc_ddt.csv`.

---

### Codici errore

* `E_DOC_STATO_INIZIALE_NON_VALIDO` — un DDT nuovo chiesto in uno stato diverso dall'iniziale.
* `E_CODICE_NON_MODIFICABILE` — una modifica di `codice_interno`.

---

### Test

* `db/pgtap/script/test-trgfn-doc-stato-iniziale-v1.sql` — uno stato iniziale per vocabolario, attivo, e la nascita su vendite e acquisti.
* `db/pgtap/script/test-doc-lettori-stato-e-preventivo-al-modello-v1.sql` — lo stato di emissione dichiarato nei documenti che si emettono.
* `db/pgtap/config/test-stati-doc-pdf-mode-v1.sql` — `pdf_mode` e `pdf_allow_allegati` obbligatori e senza default.

---

### Note di migrazione

* 2026-10-24 / 2026-10-25 — arrivano `iniziale` ed `emissione` (brief
  `brief-modello-documento-vendita`): il codice smette di scrivere `'DRAFT'` ed `'EMESSO'` per dire
  lo stato in cui si nasce e quello di emissione.

---

{% include-markdown "signature-core.md" %}
