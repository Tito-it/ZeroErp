## 📘 Documentazione Concettuale – Tabella `config.stati_doc_reso`

> **Ultimo aggiornamento**: 14 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [vendite.resi](/dbzero/vendite/tabelle/resi) — il reso, che porta lo stato (`stato_doc_reso_id`)
> * [config.transizioni_stati_reso](/dbzero/config/tabelle/transizioni_stati_reso) — i passaggi ammessi fra questi stati
> * [config.stati_doc_ddt](/dbzero/config/tabelle/stati_doc_ddt) — gli stati del DDT, da cui il reso nasce
>
> Approfondimento viste:
>
> * [vendite.vw_stato_sorgente_reso](/dbzero/vendite/views/vw_stato_sorgente_reso) — la proiezione dello stato per il motore pratiche
>
> Approfondimento funzioni:
>
> * [script.trgfn_doc_stato_iniziale](/dbzero/script/funzioni/trgfn_doc_stato_iniziale) — fa nascere il reso nello stato iniziale
> * [vendite.fn_conferma_reso](/dbzero/vendite/funzioni/fn_conferma_reso) — la conferma, che fa da emissione
> * [vendite.fn_annulla_reso](/dbzero/vendite/funzioni/fn_annulla_reso) — l'annullo, che storna gli effetti
> * [script.fn_available_actions_reso](/dbzero/script/funzioni/fn_available_actions_reso) — la capability, che legge `meta`
>
> Guide:
>
> * [Il modello del documento di vendita](/guide/modello-documento-di-vendita) — vocabolario, matrice, nascita e annullo

---

### 🎯 Scopo Principale

`config.stati_doc_reso` è il **vocabolario degli stati del documento di reso**: la bozza, la
conferma che ne applica gli effetti, l'annullo. Per ogni stato dice se il reso ci nasce, se è un
annullo e a che punto è del suo ciclo; i passaggi stanno nella matrice
[`config.transizioni_stati_reso`](/dbzero/config/tabelle/transizioni_stati_reso).

---

### Gli stati

| `codice_interno` | Che cosa vuol dire | Marcato da |
| --- | --- | --- |
| `DRAFT` | bozza: le righe si cambiano, nessun numero | `iniziale` |
| `CONFERMATO` | gli effetti del reso sono applicati e il numero è assegnato | — |
| `ANNULLATO` | il reso è annullato, e gli effetti di una conferma sono stornati | `is_abortito` |

La logica usa sempre `codice_interno`, che non si modifica (`E_CODICE_NON_MODIFICABILE`), mai
`codice`. Uno stato già usato da un reso o dalla matrice non si disattiva.

---

### Le colonne che hanno un significato

* **`iniziale`** — lo stato in cui un reso nasce. Al più uno (indice unico parziale), ed è attivo
  (CHECK). Il trigger
  [`script.trgfn_doc_stato_iniziale`](/dbzero/script/funzioni/trgfn_doc_stato_iniziale) su
  `vendite.resi` mette questo stato quando chi crea non ne dice uno, e rifiuta ogni altro con
  `E_DOC_STATO_INIZIALE_NON_VALIDO`.
* **`is_abortito`** — lo stato di annullo, al più uno e attivo.
* **`fase`** — la posizione sulla scala comune a tutti i documenti (`APERTO`, `IN_ATTESA`,
  `IN_CORSO`, `CHIUSO`): la bozza è aperta, conferma e annullo sono chiusi. Il reso è un ramo
  inverso della genealogia dei documenti, fuori dalla frontiera in avanti.

* **`emissione`** — lo stato in cui il reso è emesso: `CONFERMATO`, a cui si arriva dalla conferma
  (`DRAFT → CONFERMATO`, azione `conferma_reso`). Lì nasce il numero
  ([`vendite.trgfn_resi_gen_numero`](/dbzero/vendite/manual/trgfn_resi_gen_numero)) e da lì la merce è
  rientrata (`script.vw_stati_doc_reso_merce_rientrata`). Al più uno, e attivo.
* **`esito`** e **`terminale`** — come negli altri vocabolari, e la vista
  [`vendite.vw_stato_sorgente_reso`](/dbzero/vendite/views/vw_stato_sorgente_reso) li passa così come
  sono:

| Stato | `esito` | `terminale` |
| --- | --- | --- |
| `DRAFT` | *(nessuno)* | ❌ |
| `CONFERMATO` | `POSITIVO` | ❌ |
| `ANNULLATO` | `NEGATIVO` | ✅ |

⭐ **Il reso confermato non è terminale.** Ha fatto il suo lavoro (esito positivo, fase chiusa), ma
resta annullabile a mano: `CONFERMATO → ANNULLATO` è lo storno. È la stessa regola dell'offerta
accettata. `terminale` vuol dire che dallo stato non esce nessun passaggio a mano, e lo fa rispettare
[`script.trgfn_doc_terminale_senza_uscita_manuale`](/dbzero/script/manual/fn_doc_terminali_con_uscita_manuale).

Il vocabolario non ha le colonne della stampa (`pdf_mode`, `pdf_allow_allegati`): il reso è fuori dal
motore di stampa.

---

### `meta`

**`meta.nessuna_azione_key`** — sugli stati chiusi, la chiave del testo che spiega all'operatore
perché non ci sono azioni. La capability la espone come `stato_info_key`.

Il contenuto di tutte le colonne sta nel CSV `80_data/sql/config/stati_doc_reso.csv`.

---

### Codici errore

* `E_DOC_STATO_INIZIALE_NON_VALIDO` — un reso nuovo chiesto in uno stato diverso dall'iniziale.
* `E_CODICE_NON_MODIFICABILE` — una modifica di `codice_interno`.

---

### Test

* `db/pgtap/script/test-trgfn-doc-stato-iniziale-v1.sql` — uno stato iniziale per vocabolario, attivo, e la nascita.
* `db/pgtap/script/test-doc-verbo-comune-e-porta-v1.sql` — conferma e annullo sul verbo comune, con la porta.
* `db/pgtap/script/test-capability-motivi-e-nessuna-azione-v1.sql` — la spiegazione sugli stati senza azioni.

---

### Note di migrazione

* 2026-07-13 — nasce il vocabolario (brief `brief-db-resi-vendita` §2.1), come copia di quello del
  DDT senza le colonne della stampa; la fase stava allora in `meta.fase`, poi è diventata una
  colonna.
* 2026-10-24 — arriva `iniziale` (brief `brief-modello-documento-vendita`).

---

{% include-markdown "signature-core.md" %}
