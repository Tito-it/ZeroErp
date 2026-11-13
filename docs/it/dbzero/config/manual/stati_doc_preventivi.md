## 📘 Documentazione Concettuale – Tabella `config.stati_doc_preventivi`

> **Ultimo aggiornamento**: 13 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [vendite.preventivi](/dbzero/vendite/tabelle/preventivi) — il preventivo, che porta lo stato (`stato_doc_preventivo_id`)
> * [config.transizioni_stati_preventivi](/dbzero/config/tabelle/transizioni_stati_preventivi) — i passaggi ammessi fra questi stati
> * [config.esiti_flussi_pratiche](/dbzero/config/tabelle/esiti_flussi_pratiche) — il vocabolario dei verdetti a cui punta `esito`
>
> Approfondimento viste:
>
> * [vendite.vw_preventivi](/dbzero/vendite/views/vw_preventivi) — deriva la revisione attiva da `is_abortito`
> * [vendite.vw_stato_sorgente_preventivo](/dbzero/vendite/views/vw_stato_sorgente_preventivo) — la proiezione dello stato per il motore pratiche
>
> Approfondimento funzioni:
>
> * [script.trgfn_doc_stato_iniziale](/dbzero/script/funzioni/trgfn_doc_stato_iniziale) — fa nascere il preventivo nello stato iniziale
> * [script.fn_stato_emissione_id](/dbzero/script/funzioni/fn_stato_emissione_id) — legge lo stato di `emissione`
> * [script.fn_stato_accettazione_id](/dbzero/script/funzioni/fn_stato_accettazione_id) — legge lo stato di `accettazione`
> * [script.fn_stato_scadenza_id](/dbzero/script/funzioni/fn_stato_scadenza_id) — legge lo stato di `scadenza`
> * [script.fn_stato_rifiuto_id](/dbzero/script/funzioni/fn_stato_rifiuto_id) — legge lo stato di `rifiuto`
> * [script.fn_stato_abortito_id](/dbzero/script/funzioni/fn_stato_abortito_id) — legge lo stato di annullo (`is_abortito`)
> * [vendite.fn_chiudi_preventivi_scaduti](/dbzero/vendite/funzioni/fn_chiudi_preventivi_scaduti) — il job delle scadenze
> * [script.fn_available_actions_preventivo](/dbzero/script/funzioni/fn_available_actions_preventivo) — la capability, che legge i flag, `meta` e `pdf_mode`
>
> Guide:
>
> * [Il modello del documento di vendita](/guide/modello-documento-di-vendita) — vocabolario, matrice, nascita, emissione e annullo

---

### 🎯 Scopo Principale

`config.stati_doc_preventivi` è il **vocabolario degli stati del preventivo commerciale**, dalla
bozza all'accettazione, all'evasione, al rifiuto, alla scadenza o all'annullo. Per ogni stato dice
che cosa significa per il resto del sistema: se il preventivo ci nasce, se è emesso, accettato o
scaduto, se la revisione è stata abbandonata.

Il codice non riconosce uno stato dal suo nome: lo chiede a una colonna di questa tabella. I
passaggi fra gli stati stanno nella matrice
[`config.transizioni_stati_preventivi`](/dbzero/config/tabelle/transizioni_stati_preventivi).

---

### Gli stati

| `codice_interno` | Che cosa vuol dire | Marcato da |
| --- | --- | --- |
| `DRAFT` | bozza, si modifica | `iniziale` |
| `EMESSO` | proposto al cliente: ha il numero e il PDF | `emissione` |
| `ACCETTATO` | il cliente ha accettato: da qui la push a commessa e la push a ordine | `accettazione` |
| `EVASO` | lo smistamento verso commessa e ordine lo ha portato a termine | `terminale` |
| `RIFIUTATO` | il cliente ha detto no | `rifiuto`, `terminale` |
| `SCADUTO` | la validità è finita senza una risposta del cliente | `scadenza`, `terminale` |
| `ANNULLATO` | la revisione è stata abbandonata | `is_abortito`, `terminale` |

`ACCETTATO` ed `EVASO` si inseguono nei due versi, coi passaggi automatici che scrive la proiezione
dello smistamento. `codice_interno` è la chiave stabile e non si modifica
(`E_CODICE_NON_MODIFICABILE`). Uno stato già usato da un preventivo o dalla matrice non si
disattiva.

---

### ⭐ Gli stati che hanno un significato si leggono da una colonna

Ognuna di queste colonne marca **al più uno stato** (un indice unico parziale) e lo stato marcato
deve essere **attivo** (un CHECK). Spostare il significato su un altro stato è una cella del CSV, e
tutti i lettori seguono.

* **`iniziale`** — lo stato in cui un preventivo nasce. Il trigger
  [`script.trgfn_doc_stato_iniziale`](/dbzero/script/funzioni/trgfn_doc_stato_iniziale) su
  `vendite.preventivi` mette questo stato quando chi crea non ne dice uno, e rifiuta ogni altro con
  `E_DOC_STATO_INIZIALE_NON_VALIDO`.
* **`emissione`** — lo stato in cui il preventivo è emesso: ci si arriva solo da «Emetti», che
  produce numero e PDF insieme; il backend lo rifiuta sul cambio di stato generico. La leggono il
  guard di transizione
  ([`vendite.trgfn_preventivi_guard_transizione`](/dbzero/vendite/funzioni/trgfn_preventivi_guard_transizione)),
  la capability, la revisione
  ([`vendite.fn_crea_revisione_preventivo`](/dbzero/vendite/funzioni/fn_crea_revisione_preventivo))
  e il job delle scadenze, che chiude solo i preventivi emessi.
* **`accettazione`** — lo stato in cui il preventivo è accettato. Non chiude il documento: da qui si
  va a `EVASO`. La leggono l'elenco dei preventivi da smistare
  ([`vendite.fn_list_preventivi_da_pushare`](/dbzero/vendite/funzioni/fn_list_preventivi_da_pushare)),
  la push a ordine ([`vendite.fn_push_preventivo_a_ordine`](/dbzero/vendite/funzioni/fn_push_preventivo_a_ordine))
  e la capability.
* **`scadenza`** — lo stato in cui il preventivo è scaduto. Lo scrive il job delle scadenze
  ([`vendite.fn_chiudi_preventivi_scaduti`](/dbzero/vendite/funzioni/fn_chiudi_preventivi_scaduti))
  quando la validità è finita; da qui la revisione ripropone il preventivo.
* **`rifiuto`** — lo stato in cui il cliente ha rifiutato il preventivo. Non è il contrario di
  `accettazione`: `SCADUTO` e `ANNULLATO` hanno anche loro un esito negativo, ma non sono un no del
  cliente. Si legge con [`script.fn_stato_rifiuto_id`](/dbzero/script/funzioni/fn_stato_rifiuto_id);
  il codice del preventivo non lo nomina ancora per significato.
* **`is_abortito`** — la revisione con questo stato è stata abbandonata. Lo legge il verbo d'annullo
  ([`vendite.fn_annulla_preventivo`](/dbzero/vendite/funzioni/fn_annulla_preventivo)) attraverso
  [`script.fn_stato_abortito_id`](/dbzero/script/funzioni/fn_stato_abortito_id), e lo legge
  [`vendite.vw_preventivi`](/dbzero/vendite/views/vw_preventivi) per derivare la revisione attiva:
  quella con la revisione più alta fra le non abbandonate. Nei preventivi il superamento non è uno
  stato, è una relazione fra revisioni.

Il vocabolario del preventivo **non ha** la colonna `cessazione`: chiesto al suo lettore, quello
stato è vuoto.

---

### La proiezione per il motore pratiche: `fase`, `esito`, `terminale`

| `codice_interno` | `fase` | `esito` | `terminale` |
| --- | --- | --- | --- |
| `DRAFT` | `APERTO` | — | no |
| `EMESSO` | `IN_ATTESA` | — | no |
| `ACCETTATO` | `IN_CORSO` | `POSITIVO` | no |
| `EVASO` | `CHIUSO` | `POSITIVO` | sì |
| `RIFIUTATO` | `CHIUSO` | `NEGATIVO` | sì |
| `SCADUTO` | `CHIUSO` | `NEGATIVO` | sì |
| `ANNULLATO` | `CHIUSO` | `NEGATIVO` | sì |

* `fase` è obbligatoria e sta nei quattro valori della scala: ogni stato nuovo dichiara la sua.
* `esito` punta a un verdetto di
  [`config.esiti_flussi_pratiche`](/dbzero/config/tabelle/esiti_flussi_pratiche) (lo controlla il
  guard [`config.trgfn_stati_doc_guard_esito_verdetto`](/dbzero/config/funzioni/trgfn_stati_doc_guard_esito_verdetto));
  vuoto vuol dire nessun verdetto.
* `terminale` implica `fase = CHIUSO`.
* ⚠️ `terminale` **non sostituisce** `is_abortito`: `RIFIUTATO` e `SCADUTO` sono terminali ma non
  abbandonati, perché chiudono la negoziazione, non la singola revisione.
* La proiezione fotografa lo stato memorizzato: il passaggio `EMESSO → SCADUTO` lo scrive il job, e
  fra la fine della validità e il giro del job il preventivo risulta ancora emesso.

---

### `meta` e la stampa

* **`meta.nessuna_azione_key`** — sugli stati chiusi, la chiave del testo che spiega all'operatore
  perché non ci sono azioni. La capability la espone come `stato_info_key`.
* **`pdf_mode`** e **`pdf_allow_allegati`** — che cosa offre il bottone PDF in quello stato:
  l'anteprima in bozza, l'archivio negli altri. Non hanno un default: uno stato nuovo li dichiara.

Il contenuto di tutte le colonne sta nel CSV `80_data/sql/config/stati_doc_preventivi.csv`.

---

### Codici errore

* `E_DOC_STATO_INIZIALE_NON_VALIDO` — un preventivo nuovo chiesto in uno stato diverso dall'iniziale.
* `E_CODICE_NON_MODIFICABILE` — una modifica di `codice_interno`.

---

### Test

* `db/pgtap/script/test-doc-lettori-stato-e-preventivo-al-modello-v1.sql` — lo stato di emissione e il preventivo sul modello del documento.
* `db/pgtap/script/test-doc-stati-dal-vocabolario-v1.sql` — i lettori di `accettazione`, `scadenza` e degli altri stati marcati.
* `db/pgtap/vendite/test-preventivo-scadenza-v1.sql` — la scadenza scritta dal job.
* `db/pgtap/script/test-trgfn-doc-stato-iniziale-v1.sql` — uno stato iniziale per vocabolario, attivo, e la nascita.

---

### Note di migrazione

* 2026-10-24 / 2026-10-25 — arrivano `iniziale` ed `emissione` (brief
  `brief-modello-documento-vendita` §8).
* 2026-10-31 — arrivano `accettazione` (brief `brief-modello-documento-vendita` §17) e `scadenza`
  (brief `brief-db-scadenza-preventivi` §8.1): il codice smette di scrivere `'ACCETTATO'` e
  `'SCADUTO'`.
* 2026-11-13 — arriva `rifiuto` (brief `brief-db-stati-documento-dal-vocabolario`, giro 2).

---

{% include-markdown "signature-core.md" %}
