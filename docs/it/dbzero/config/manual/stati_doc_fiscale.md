## 📘 Documentazione Concettuale – Tabella `config.stati_doc_fiscale`

> **Ultimo aggiornamento**: 12 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [vendite.fatture](/dbzero/vendite/tabelle/fatture) — la fattura, che porta lo stato (`stato_doc_fiscale_id`)
> * [vendite.fatturazione_lotti](/dbzero/vendite/tabelle/fatturazione_lotti) — il lotto di fatturazione, che usa lo stesso vocabolario
> * [config.stati_doc_fiscale_transizioni](/dbzero/config/tabelle/stati_doc_fiscale_transizioni) — i passaggi ammessi, distinti fra lotto e fattura
>
> Approfondimento funzioni:
>
> * [script.trgfn_doc_stato_iniziale](/dbzero/script/funzioni/trgfn_doc_stato_iniziale) — fa nascere la fattura nello stato iniziale
> * [vendite.fn_riporta_lotto_a_draft](/dbzero/vendite/funzioni/fn_riporta_lotto_a_draft) — riporta il lotto nello stato iniziale
> * [vendite.trgfn_fatturazione_lotti_guard_stato](/dbzero/vendite/funzioni/trgfn_fatturazione_lotti_guard_stato) — il guard di stato del lotto
> * [vendite.trgfn_fatture_guard_stato](/dbzero/vendite/funzioni/trgfn_fatture_guard_stato) — il guard di stato della fattura
> * [vendite.trgfn_fattura_satellite_guard_congelamento](/dbzero/vendite/funzioni/trgfn_fattura_satellite_guard_congelamento) — la guardia del congelamento, che legge `congela_fiscale`
> * [vendite.fn_ricalcola_riepilogo_iva_fattura](/dbzero/vendite/funzioni/fn_ricalcola_riepilogo_iva_fattura) — il ricalcolo, ammesso solo dove `congela_fiscale` è falso
> * [config.trgfn_stati_doc_fiscale_chiude_lotto_guard](/dbzero/config/funzioni/trgfn_stati_doc_fiscale_chiude_lotto_guard) — esattamente uno stato chiude il lotto
> * [config.fn_get_stati_doc_fiscale](/dbzero/config/funzioni/fn_get_stati_doc_fiscale) — gli stati applicabili al lotto o alla fattura
>
> Guide:
>
> * [Il modello del documento di vendita](/guide/modello-documento-di-vendita) — vocabolario, matrice, nascita; la forma propria della fattura

---

### 🎯 Scopo Principale

`config.stati_doc_fiscale` è il **vocabolario degli stati del ciclo di fatturazione**, condiviso
dalle **fatture** e dai **lotti di fatturazione**: quali stati esistono e, per ciascuno, a chi si
applica, se ci si nasce, se è un annullo, se chiude il lotto e se da lì il documento è uno snapshot
fiscale che non si ricalcola più.

I passaggi fra gli stati stanno nella matrice
[`config.stati_doc_fiscale_transizioni`](/dbzero/config/tabelle/stati_doc_fiscale_transizioni), con
i passaggi solo del lotto e solo della fattura.

---

### Gli stati

| `codice_interno` | Che cosa vuol dire | Marcato da |
| --- | --- | --- |
| `DRAFT` | bozza: si preparano le attività da fatturare, il documento si ricalcola | `iniziale` |
| `EMESSA` | il documento è generato, con tutti i suoi importi ma senza numero; si torna ancora in bozza | — |
| `DEFINITIVA` | il documento è numerato: non si torna indietro | `chiude_lotto`, `congela_fiscale` |
| `INVIATA` | il documento è preparato o inviato sul canale esterno | `congela_fiscale` |
| `REGISTRATA` | la fattura ha concluso il suo giro dopo l'invio (solo fattura) | `congela_fiscale` |
| `ANNULLATA` | il lotto è annullato mentre era in bozza | `is_abortito`, `congela_fiscale` |

`codice_interno` è la chiave stabile e non si modifica (`E_CODICE_NON_MODIFICABILE`). Uno stato
già usato da una fattura, da un lotto, dalla pipeline di fatturazione o da una riga della matrice
non si disattiva.

---

### A chi si applica uno stato: `applica_fattura` e `applica_lotto`

Lo stesso vocabolario serve due documenti, e i due flag dicono quali stati valgono per ciascuno. Li
legge [`config.fn_get_stati_doc_fiscale`](/dbzero/config/funzioni/fn_get_stati_doc_fiscale), che
elenca gli stati di uno dei due. I guard di stato della fattura e del lotto li controllano sulla
**destinazione** di ogni cambio: uno stato che non si applica al documento si rifiuta
(`E_LOTTO_PARAMETRO_NON_COERENTE`), da qualunque passaggio arrivi.

La nascita non è un cambio di stato. Fattura e lotto nascono entrambi nello stato marcato
`iniziale`, che mette il trigger della nascita senza guardare i due flag: per questo lo stato
iniziale si applica a tutti e due per vincolo (`chk_stati_doc_fiscale_iniziale_applica`).

⚠️ **I flag hanno una seconda sede che deve dire la stessa cosa**: la matrice. Un passaggio del
lotto verso uno stato senza `applica_lotto` esiste nella matrice ma il guard lo rifiuta: il
vocabolario e la matrice dissentono. Lo presidia un pgTAP, in un verso solo (raggiungibile ⇒
flag): uno stato può avere il flag senza che nessun passaggio del lotto lo raggiunga, come oggi
`REGISTRATA`.

---

### ⭐ Gli stati che hanno un significato si leggono da una colonna

* **`iniziale`** — lo stato in cui una fattura nasce. Al più uno per vocabolario (indice unico
  parziale), ed è attivo (CHECK). Il trigger
  [`script.trgfn_doc_stato_iniziale`](/dbzero/script/funzioni/trgfn_doc_stato_iniziale), montato su
  `vendite.fatture`, mette questo stato quando chi crea non ne dice uno, e rifiuta ogni altro con
  `E_DOC_STATO_INIZIALE_NON_VALIDO`. La leggono anche il ritorno in bozza del lotto
  ([`vendite.fn_riporta_lotto_a_draft`](/dbzero/vendite/funzioni/fn_riporta_lotto_a_draft)) e il giro
  della pipeline ([`vendite.fn_lotto_proietta_stato_step`](/dbzero/vendite/funzioni/fn_lotto_proietta_stato_step)),
  che non porta mai un lotto nello stato iniziale: il ritorno in bozza è un verbo.
* **`is_abortito`** — lo stato di annullo, al più uno e attivo. Lo legge l'annullo del lotto in
  bozza ([`vendite.fn_annulla_lotto_da_draft`](/dbzero/vendite/funzioni/fn_annulla_lotto_da_draft)).
  Un lotto fermo per segnalazioni non entra in uno stato congelato **e non abortito**: l'annullo
  resta sempre una via d'uscita.
* **`chiude_lotto`** — lo stato il cui step chiude operativamente il lotto. È **esattamente uno**:
  lo garantisce un trigger differito (`E_CHIUDE_LOTTO_SINGLETON`), che guarda la tabella alla fine
  della transazione.

Il vocabolario fiscale **non ha** la colonna `emissione`: la fattura non si emette da «Emetti», segue
gli step della pipeline di fatturazione, e i pulsanti stanno sul lotto. Non ha nemmeno `esito` e
`terminale`; dichiara la sola `fase` (la scala comune `APERTO`, `IN_ATTESA`, `IN_CORSO`, `CHIUSO`),
che la genealogia dei documenti usa per la frontiera.

---

### ⭐ `congela_fiscale`: la soglia dello snapshot fiscale ha una sede sola

Da uno stato con `congela_fiscale` vero in poi, il documento è uno **snapshot fiscale**: i valori
calcolati — il riepilogo IVA, e dal risolutore IVA anche l'aliquota di riga — non si ricalcolano
più, si rileggono. Con `false` il ricalcolo è ammesso (bozza e lavorazione).

* **Tutti i lettori leggono questa colonna**: il ricalcolo, la guardia del congelamento, la
  generazione delle scadenze, il guard di stato del lotto, i controlli di eliminabilità. Nessuno
  tiene una lista di codici: due definizioni di «congelato» lascerebbero il documento congelato per
  metà sistema e scrivibile per l'altra, senza un errore.
* ⭐ **Il confine è `DEFINITIVA`, non `EMESSA`.** Da `EMESSA` si torna in bozza (il passaggio
  `EMESSA → DRAFT` è nella matrice); da `DEFINITIVA` no.
* ⚠️ **Il default è `true`, e la direzione è una decisione.** Uno stato nuovo che nessuno classifica
  **rifiuta** il ricalcolo con un errore parlante, invece di lasciar riscrivere in silenzio uno
  snapshot fiscale.
* ⛔ **Tre scorciatoie sbagliate.** `fase` non separa niente (`EMESSA` e `DEFINITIVA` sono entrambe
  in corso); `ordine` è ordinamento di presentazione, non un ciclo di vita; `chiude_lotto` coincide
  oggi con il confine ma risponde a un'altra domanda, e il giorno che le due divergono non si
  separano più.
* ⚠️ Il trattamento di uno **stato mancante** non è lo stesso in tutti i lettori: alcuni lasciano
  passare, altri bloccano.

Spostare la soglia è una cella del CSV `80_data/sql/config/stati_doc_fiscale.csv`, che governa tutte
le colonne della tabella.

---

### Codici errore

* `E_DOC_STATO_INIZIALE_NON_VALIDO` — una fattura nuova chiesta in uno stato diverso dall'iniziale.
* `E_CHIUDE_LOTTO_SINGLETON` — alla fine della transazione gli stati con `chiude_lotto` non sono esattamente uno.
* `E_CODICE_NON_MODIFICABILE` — una modifica di `codice_interno`.

---

### Test

* `db/pgtap/config/test-stati-doc-fiscale-applica-lotto-vs-matrice-v1.sql` — ogni stato che la matrice fa raggiungere a un lotto ha `applica_lotto`.
* `db/pgtap/config/test-stati-doc-fiscale-congela-fiscale.sql` — `congela_fiscale` obbligatorio, default `true`, e il ricalcolo che lo segue.
* `db/pgtap/config/test-soglia-congelamento-sede-unica.sql` — nessuna funzione porta più la lista di codici, e la guardia segue la colonna in entrambi i versi.
* `db/pgtap/script/test-trgfn-doc-stato-iniziale-v1.sql` — uno stato iniziale per vocabolario, attivo, e la nascita.
* `db/pgtap/vendite/test-fattura-lotto-al-modello-v1.sql` — lotto e fattura sul modello del documento.

---

### Note di migrazione

* 2026-08-29 / 2026-08-30 — nasce `congela_fiscale` (brief
  `brief-db-be-iva-risolutore-e-regime-cliente`, D15 / I10, D33, D34): la soglia viveva come lista
  `NOT IN ('DRAFT','EMESSA')` in otto funzioni; tutte portate a leggere la colonna, senza cambiare
  comportamento. La guardia di congelamento delle righe fattura è riassorbita in quella dei satelliti.
  Il mirror del CSV è ri-ancorato perché governi anche `fase`, `is_abortito` e `congela_fiscale`.
* 2026-09-12 — `ANNULLATA` riceve `applica_lotto`, che le mancava benché la matrice la facesse
  raggiungere ai lotti; nasce il pgTAP che confronta flag e matrice.
* 2026-10-24 — arriva `iniziale` (brief `brief-modello-documento-vendita`).

---

{% include-markdown "signature-core.md" %}
