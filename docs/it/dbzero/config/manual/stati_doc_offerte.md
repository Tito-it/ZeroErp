## 📘 Documentazione Concettuale – Tabella `config.stati_doc_offerte`

> **Ultimo aggiornamento**: 8 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [vendite.offerte_commerciali](/dbzero/vendite/tabelle/offerte_commerciali) — l'offerta, che porta lo stato (`stato_doc_offerta_id`)
> * [config.stati_doc_offerte_transizioni](/dbzero/config/tabelle/stati_doc_offerte_transizioni) — i passaggi ammessi fra questi stati
> * [config.esiti_flussi_pratiche](/dbzero/config/tabelle/esiti_flussi_pratiche) — il vocabolario dei verdetti a cui punta `esito`
>
> Approfondimento viste:
>
> * [vendite.vw_offerte_commerciali_lista](/dbzero/vendite/views/vw_offerte_commerciali_lista) — la lista, che espone `is_superata`, `is_abortito` e `is_attiva`
> * [vendite.vw_stato_sorgente_offerta](/dbzero/vendite/views/vw_stato_sorgente_offerta) — la proiezione dello stato per il motore pratiche
>
> Approfondimento funzioni:
>
> * [script.trgfn_doc_stato_iniziale](/dbzero/script/funzioni/trgfn_doc_stato_iniziale) — fa nascere l'offerta nello stato iniziale
> * [script.fn_stato_emissione_id](/dbzero/script/funzioni/fn_stato_emissione_id) — legge lo stato di `emissione`
> * [script.fn_stato_accettazione_id](/dbzero/script/funzioni/fn_stato_accettazione_id) — legge lo stato di `accettazione`
> * [script.fn_stato_abortito_id](/dbzero/script/funzioni/fn_stato_abortito_id) — legge lo stato di annullo (`is_abortito`)
> * [vendite.fn_offerta_proietta_stato_revisione](/dbzero/vendite/funzioni/fn_offerta_proietta_stato_revisione) — mette e toglie il superamento sul padre
> * [script.fn_available_actions_offerta](/dbzero/script/funzioni/fn_available_actions_offerta) — la capability, che legge i flag, `meta` e `pdf_mode`
>
> Guide:
>
> * [Il modello del documento di vendita](/guide/modello-documento-di-vendita) — vocabolario, matrice, nascita, emissione e annullo

---

### 🎯 Scopo Principale

`config.stati_doc_offerte` è il **vocabolario degli stati dell'offerta commerciale**, dalla bozza
all'accettazione, al rifiuto, al superamento da parte di una revisione o all'annullo. Per ogni stato
dice che cosa significa per il resto del sistema: se l'offerta ci nasce, se è emessa, se è accettata,
se è stata rimpiazzata o annullata.

Il codice non riconosce uno stato dal suo nome: lo chiede a una colonna di questa tabella. I
passaggi fra gli stati stanno nella matrice
[`config.stati_doc_offerte_transizioni`](/dbzero/config/tabelle/stati_doc_offerte_transizioni).

---

### Gli stati

| `codice_interno` | Che cosa vuol dire | Marcato da |
| --- | --- | --- |
| `BOZZA` | in preparazione, si modifica | `iniziale` |
| `EMESSA` | proposta al cliente: ha il PDF, la versione di listino è congelata | `emissione` |
| `ACCETTATA` | il cliente ha accettato: da qui il passaggio a contratto e la generazione dell'ordine | `accettazione` |
| `RIFIUTATA` | il cliente ha detto no | `terminale` |
| `SUPERATA` | una revisione successiva l'ha rimpiazzata | `is_superato`, `terminale` |
| `ANNULLATA` | ritirata, in bozza o dopo l'accettazione | `is_abortito`, `terminale` |

`codice_interno` è la chiave stabile e non si modifica (`E_CODICE_NON_MODIFICABILE`). Uno stato
già usato da un'offerta o dalla matrice non si disattiva.

---

### ⭐ Gli stati che hanno un significato si leggono da una colonna

Ognuna di queste colonne marca **al più uno stato** (un indice unico parziale) e lo stato marcato
deve essere **attivo** (un CHECK). Spostare il significato su un altro stato è una cella del CSV, e
tutti i lettori seguono.

* **`iniziale`** — lo stato in cui un'offerta nasce. Il trigger
  [`script.trgfn_doc_stato_iniziale`](/dbzero/script/funzioni/trgfn_doc_stato_iniziale) su
  `vendite.offerte_commerciali` mette questo stato quando chi crea non ne dice uno, e rifiuta ogni
  altro con `E_DOC_STATO_INIZIALE_NON_VALIDO`.
* **`emissione`** — lo stato in cui l'offerta è emessa: ci si arriva solo da «Emetti», che genera
  il PDF; il backend lo rifiuta sul cambio di stato generico. ⚠️ Il numero dell'offerta si assegna
  alla nascita, non all'emissione: è una divergenza dichiarata dalla guida del modello. La leggono la capability
  (le condizioni di «Emetti»), la revisione
  ([`vendite.fn_crea_revisione_offerta`](/dbzero/vendite/funzioni/fn_crea_revisione_offerta)) e il
  rientro del padre, che torna nello stato di emissione quando l'ultima revisione viva è annullata.
* **`accettazione`** — lo stato in cui l'offerta è accettata. La leggono il passaggio a contratto
  ([`vendite.fn_push_offerta_a_contratto`](/dbzero/vendite/funzioni/fn_push_offerta_a_contratto)), la
  generazione dell'ordine
  ([`vendite.fn_genera_ordine_da_offerta`](/dbzero/vendite/funzioni/fn_genera_ordine_da_offerta)) e la
  capability, che spegne il passaggio all'accettazione finché restano prezzi non autorizzati.
* **`is_abortito`** — lo stato di annullo, letto dal verbo d'annullo
  ([`vendite.fn_annulla_offerta`](/dbzero/vendite/funzioni/fn_annulla_offerta)) attraverso
  [`script.fn_stato_abortito_id`](/dbzero/script/funzioni/fn_stato_abortito_id).
* **`is_superato`** — lo stato di superamento: vedi la sezione che segue.

---

### I due assi di chiusura: `is_abortito` e `is_superato`

Un'offerta smette di essere quella «buona» per due ragioni che non hanno niente a che vedere l'una
con l'altra:

| Colonna | Stato marcato | Domanda | Chi porta l'offerta in quello stato |
| --- | --- | --- | --- |
| `is_abortito` | `ANNULLATA` | è stata annullata? | l'operatore, con l'annullo |
| `is_superato` | `SUPERATA` | è stata rimpiazzata da una revisione successiva? | [`vendite.fn_offerta_proietta_stato_revisione`](/dbzero/vendite/funzioni/fn_offerta_proietta_stato_revisione), sul padre, quando nasce la revisione |

Un'offerta è **attiva** quando nessuno dei due è vero: è la colonna `is_attiva` di
[`vendite.vw_offerte_commerciali_lista`](/dbzero/vendite/views/vw_offerte_commerciali_lista), che
espone anche le due metà separate. ⭐ Tenerle separate è ciò che permette di chiedere «solo l'ultima
revisione» senza chiedere anche «e non annullata», e di filtrare la lista sulle offerte annullate.
Finché il significato di `SUPERATA` stava in una coppia di codici dentro la vista, uno stato nuovo
con lo stesso significato non sarebbe entrato nel predicato, e nessun errore l'avrebbe detto.

⚠️ **Dal superamento si rientra.** La matrice ha il passaggio automatico `SUPERATA → EMESSA`: quando
l'ultima revisione viva viene annullata, la stessa proiezione toglie il superamento e il padre torna
operativo. Il guard di transizione lascia uscire dal superamento **solo** se non esiste più una
revisione figlia viva (`E_OFFERTA_RIENTRO_CON_REVISIONE_VIVA`), perché un passaggio ammesso vale per
chiunque scriva, non solo per il trigger che l'ha reso necessario.

⚠️ `is_superato` esiste **solo qui**, non nel vocabolario dei preventivi: lì il superamento non è
uno stato ma una relazione fra revisioni (`numero`, `rev`), e la deriva `vendite.vw_preventivi`.

---

### La proiezione per il motore pratiche: `fase`, `esito`, `terminale`

| `codice_interno` | `fase` | `esito` | `terminale` |
| --- | --- | --- | --- |
| `BOZZA` | `APERTO` | — | no |
| `EMESSA` | `IN_ATTESA` | — | no |
| `ACCETTATA` | `IN_CORSO` | `POSITIVO` | no |
| `RIFIUTATA` | `CHIUSO` | `NEGATIVO` | sì |
| `SUPERATA` | `CHIUSO` | `NEGATIVO` | sì |
| `ANNULLATA` | `CHIUSO` | `NEGATIVO` | sì |

* `fase` è obbligatoria e sta nei quattro valori della scala: ogni stato nuovo dichiara la sua.
* `esito` punta a un verdetto di
  [`config.esiti_flussi_pratiche`](/dbzero/config/tabelle/esiti_flussi_pratiche) (lo controlla il
  guard [`config.trgfn_stati_doc_guard_esito_verdetto`](/dbzero/config/funzioni/trgfn_stati_doc_guard_esito_verdetto));
  vuoto vuol dire nessun verdetto.
* `terminale` implica `fase = CHIUSO`.

⚠️ La proiezione **non basta** a distinguere i tre modi di chiudere: `RIFIUTATA`, `SUPERATA` e
`ANNULLATA` hanno la stessa `fase`, lo stesso `esito` e sono tutte terminali. Servono `is_abortito` e
`is_superato`.

---

### `meta` e la stampa

* **`meta.nessuna_azione_key`** — sugli stati chiusi, la chiave del testo che spiega all'operatore
  perché non ci sono azioni. La capability la espone come `stato_info_key`.
* **`pdf_mode`** e **`pdf_allow_allegati`** — che cosa offre il bottone PDF in quello stato:
  l'anteprima in bozza, l'archivio negli altri; gli allegati solo sull'offerta emessa. Non hanno un
  default: uno stato nuovo li dichiara.

Il contenuto di tutte le colonne sta nel CSV `80_data/sql/config/stati_doc_offerte.csv`.

---

### Codici errore

* `E_DOC_STATO_INIZIALE_NON_VALIDO` — un'offerta nuova chiesta in uno stato diverso dall'iniziale.
* `E_OFFERTA_RIENTRO_CON_REVISIONE_VIVA` — un'uscita dal superamento mentre una revisione figlia è ancora viva.
* `E_CODICE_NON_MODIFICABILE` — una modifica di `codice_interno`.

---

### Test

* `db/pgtap/vendite/test-offerta-al-modello-v1.sql` — l'offerta sul modello del documento.
* `db/pgtap/script/test-doc-stati-dal-vocabolario-v1.sql` — i lettori di `emissione`, `accettazione` e degli altri stati marcati.
* `db/pgtap/vendite/offerte_commerciali/test-vw-offerte-lista-superata-vs-abortito.sql` — i due assi di chiusura nella lista.
* `db/pgtap/vendite/offerte_commerciali/test-offerte-rientro-padre-revisione-annullata.sql` — il rientro del padre dal superamento.

---

### Note di migrazione

* 2026-08-28 — nasce `is_superato` (brief `brief-db-revisione-attiva-due-domande`): la lista
  scriveva `codice_interno NOT IN ('SUPERATA','ANNULLATA')`, un flag solo per due domande. Nello
  stesso giro nasce il rientro `SUPERATA → EMESSA`.
* 2026-10-24 / 2026-10-26 — arrivano `iniziale` ed `emissione`, e l'offerta passa al modello del
  documento (brief `brief-modello-documento-vendita` §13).
* 2026-10-26 — il superamento lo mette e lo toglie la proiezione delle revisioni, chiamata dai
  trigger della revisione e del rientro del padre.
* 2026-10-31 — arriva `accettazione` (brief `brief-modello-documento-vendita` §17).

---

{% include-markdown "signature-core.md" %}
