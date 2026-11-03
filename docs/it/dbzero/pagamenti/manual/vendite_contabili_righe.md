## 📘 Documentazione Concettuale – Tabella `pagamenti.vendite_contabili_righe`

> **Ultimo aggiornamento**: 3 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [pagamenti.vendite_contabili](/dbzero/pagamenti/tabelle/vendite_contabili) — la distinta a cui ogni riga appartiene
> * [pagamenti.vendite_contabili_righe_stati](/dbzero/pagamenti/tabelle/vendite_contabili_righe_stati) — il catalogo degli stati di riga e le sue bandiere
> * [pagamenti.transizioni_stati_contabile_riga](/dbzero/pagamenti/tabelle/transizioni_stati_contabile_riga) — i passaggi di stato ammessi
> * [pagamenti.enti_incasso](/dbzero/pagamenti/tabelle/enti_incasso) — il canale della distinta, che la riga non ripete
> * [vendite.fatture_fondi_fattura_source](/dbzero/vendite/tabelle/fatture_fondi_fattura_source) — l'atto di fondo fattura da cui nasce una riga del giro dei fondi
> * [vendite.fatture_scadenze](/dbzero/vendite/tabelle/fatture_scadenze) — la rata a cui la riga imputa il denaro
>
> Approfondimento viste:
>
> * [pagamenti.vw_rate_fuori_capienza](/dbzero/pagamenti/views/vw_rate_fuori_capienza) — l'elenco delle righe registrate fuori capienza
>
> Approfondimento funzioni:
>
> * [pagamenti.trgfn_vendite_contabili_righe_guard_contenuto](/dbzero/pagamenti/funzioni/trgfn_vendite_contabili_righe_guard_contenuto) — eliminazione e congelamento del contenuto
> * [pagamenti.trgfn_vendite_contabili_righe_guard_rata](/dbzero/pagamenti/funzioni/trgfn_vendite_contabili_righe_guard_rata) — coerenza e capienza della rata
> * [pagamenti.trgfn_vendite_contabili_righe_marca_fondo_eseguito](/dbzero/pagamenti/funzioni/trgfn_vendite_contabili_righe_marca_fondo_eseguito) — porta l'atto di fondo a `ESEGUITO`
> * [script.fn_check_riga_contabile_eliminabile](/dbzero/script/funzioni/fn_check_riga_contabile_eliminabile) — i motivi per cui una riga non si elimina
> * [script.fn_resolve_emittente_fiscale_id](/dbzero/script/funzioni/fn_resolve_emittente_fiscale_id) — il risolutore dell'emittente che la policy interroga
> * [vendite.fn_cancella_fondo_fattura](/dbzero/vendite/funzioni/fn_cancella_fondo_fattura) — l'unico `DELETE` di sistema ammesso
>
> Guide:
>
> * [Gestione dei pagamenti](/guide/gestione-dei-pagamenti) — il modello degli incassi per intero

---

### 🎯 Scopo Principale

La tabella **`pagamenti.vendite_contabili_righe`** contiene le singole somme di denaro dentro
una distinta contabile: ciascuna con il suo stato di lavorazione e, quando è attribuita, la
fattura, il cliente e la rata a cui appartiene.

Il canale e l'ente di provenienza sono della distinta, non della riga. Una riga appartiene
sempre a una distinta, il suo importo non è mai zero, e il suo stato viene dal catalogo
[vendite_contabili_righe_stati](/dbzero/pagamenti/tabelle/vendite_contabili_righe_stati).

---

### Il significato delle colonne che il nome non dice

* `riferimento_ente` — il riferimento esterno del flusso (CRO, TRN, identificativo
  dell'operazione).
* `motivo_sospeso` — perché la riga **non** è stata lavorata.
* `fondo_source_id` — l'**atto di fondo fattura** da cui la riga nasce. È vuota su ogni riga
  che non viene da un fondo, cioè sulla maggior parte.
* `scadenza_id` — la **rata** a cui il denaro è imputato.
* `forzata` / `motivo_forzatura` — la riga è stata registrata **fuori dalla capienza** della
  rata, e qualcuno l'ha confermato. Il motivo è facoltativo.

⚠️ `motivo_forzatura` e `motivo_sospeso` non si confondono: il secondo dice perché una riga non
è stata lavorata, il primo perché è stata lavorata **lo stesso**.

---

### ⭐ L'abbinamento alla rata vive sulla riga

Non c'è una tabella molti-a-molti fra righe e rate: la riga è già l'unità di allocazione. Chi
paga due rate con un bonifico solo produce **due righe**, che è anche il modo in cui la banca lo
racconta.

⚠️ **`scadenza_id` è facoltativa di proposito.** Ci sono righe che saldano un documento senza
riferirsi a una rata: la riga del fondo fattura è esattamente questa, un saldo per
trasferimento con la fattura e senza la rata. Il guard sui dati dello stato
([trgfn_vendite_contabili_righe_guard_stato_dati](/dbzero/pagamenti/funzioni/trgfn_vendite_contabili_righe_guard_stato_dati))
pretende fattura e cliente, non la rata: non è una svista.

---

### ⭐ `forzata` è il prezzo di una decisione

Che un cliente paghi più del dovuto, o paghi due volte, è un **fatto del mondo**: il database
non lo dichiara impossibile, lo **segnala**, e se qualcuno conferma registra e lascia scritto.
Senza traccia una forzatura sarebbe un modo di *nascondere* denaro, non di registrarlo. L'elenco
a valle è [vw_rate_fuori_capienza](/dbzero/pagamenti/views/vw_rate_fuori_capienza); la regola
sta in [trgfn_vendite_contabili_righe_guard_rata](/dbzero/pagamenti/funzioni/trgfn_vendite_contabili_righe_guard_rata).

---

### ⭐ Il legame con l'atto di fondo è una colonna, non un valore nel `meta`

`fondo_source_id` è una relazione vera: integrità, indice, garanzia che l'atto esista. Il
legame è **portante**, perché l'atto passa a `ESEGUITO` leggendolo
([trgfn_vendite_contabili_righe_marca_fondo_eseguito](/dbzero/pagamenti/funzioni/trgfn_vendite_contabili_righe_marca_fondo_eseguito)):
quando la riga entra in uno stato registrato, l'atto citato diventa una cosa fatta, e lo fa il
trigger, non il chiamante.

⚠️ La chiave esterna è **`NO ACTION`** di proposito: cancellare un atto pretende di aver prima
cancellato le sue righe. È l'ordine che
[vendite.fn_cancella_fondo_fattura](/dbzero/vendite/funzioni/fn_cancella_fondo_fattura), sede
unica dei `DELETE` del giro dei fondi, rispetta (righe contabili, poi fondo applicato, poi
atto). Una chiave differita avrebbe *nascosto* l'ordine invece di dichiararlo.

ℹ️ Da non confondere con l'origine `FONDO_FATTURA` scritta nel `meta`, che resta: quella
dice **da quale processo** nasce la riga, la colonna **a quale atto** appartiene.

---

### ✂️ Una riga si elimina solo da una bozza manuale

Una riga si **elimina** (con `attivo = false`, e il `DELETE` fisico passa dalla stessa
regola) **solo** se la sua distinta è **`MANUALE` in `BOZZA`**. Non è uno stato: `SCARTATA` dice un'altra
cosa, *denaro arrivato, non nostro*, e conta nella quadratura; una riga digitata male su una
bozza non è un fatto, e si toglie.

I motivi del rifiuto li dice
[script.fn_check_riga_contabile_eliminabile](/dbzero/script/funzioni/fn_check_riga_contabile_eliminabile),
che li prende dalla sua metà su distinta
([fn_check_riga_contabile_eliminabile_su_distinta](/dbzero/script/funzioni/fn_check_riga_contabile_eliminabile_su_distinta),
sede unica del predicato), in quest'ordine: distinta annullata, distinta finale, distinta non
manuale, distinta validata. Il guard che li solleva è
[trgfn_vendite_contabili_righe_guard_contenuto](/dbzero/pagamenti/funzioni/trgfn_vendite_contabili_righe_guard_contenuto).
Il backend legge gli stessi motivi per spegnere il cestino col perché: tooltip e rifiuto non
possono divergere.

⚠️ Il `DELETE` ha **un** passaggio legittimo: il giro dei fondi cancella le righe del suo atto
sotto una distinta `GENERATA`, e lo dichiara con la GUC transazionale
`zeroerp.allow_contabile_riga_delete_override`. Non è un permesso: è la madre che dice «sono io»,
dopo aver letto il suo criterio. Il resto sta nella scheda del guard.

---

### 🧊 Sotto una manuale validata i fatti sono fermi, le decisioni no

Sotto una `MANUALE` **validata** il contenuto è **fermo**: niente righe nuove, niente modifiche
ai **fatti** (importo, le tre date, riferimento), niente eliminazioni né spostamenti, finché non
torna in bozza. Le **decisioni** (stato, abbinamento, rata, forzatura, motivi) restano libere:
non toccano la quadratura, e il posting muove lo stato mentre la distinta è ancora validata.

Sotto una distinta **annullata** le righe si leggono soltanto; sotto una **chiusa** si lavorano
ancora, ma non vi entra nessuna riga pronta da registrare. Le due regole stanno in
[trgfn_vendite_contabili_righe_guard_distinta_finale](/dbzero/pagamenti/funzioni/trgfn_vendite_contabili_righe_guard_distinta_finale).

---

### 🔒 Chi la vede: due strade in OR

La policy `rls_vendite_contabili_righe_perimetro_incasso` vale per ogni comando (`FOR ALL`),
apre solo alla veste `OPERATORE` (fail-closed), e ammette una riga per **due strade**, nessuna
ridondante.

| | Strada | Copre |
| --- | --- | --- |
| **1** | l'**emittente della distinta** | la riga `DA_ABBINARE`, che fattura non ha, anche su una distinta senza canale; le righe delle distinte interne |
| **2** | la **fattura** della riga, quando c'è | la riga sul proprio documento finita sulla distinta di un altro |

⭐ **La prima è la ragione per cui il perimetro passa dalla distinta**: con la sola fattura, la
coda «da abbinare» sarebbe invisibile a tutti. La distinta sa di chi è, quindi anche una distinta
senza canale (l'operatore che digita incassi a mano) e una distinta interna (fondo fattura,
compensazione) appartengono al loro emittente, e le loro righe con lei.

⚠️ **La seconda serve a un caso strutturale.** Fa vedere la riga sul proprio documento finita
sulla distinta di un altro, cioè un abbinamento sbagliato: senza, il saldo direbbe che quel
denaro non è arrivato **e non ci sarebbe modo di scoprire perché**. ⭐ E serve
alla **bilancia**: una riga che sparisse dalla propria distinta romperebbe la quadratura col totale
dichiarato, e la verifica darebbe un allarme falso ogni volta.

Entrambe le strade chiedono l'emittente a
[script.fn_resolve_emittente_fiscale_id](/dbzero/script/funzioni/fn_resolve_emittente_fiscale_id)
(dalla distinta e dalla fattura) e lo confrontano col perimetro dell'utente, calcolato una volta
per istruzione.

⭐ **La policy nasconde, i trigger rifiutano.** Due guard di scrittura
([script.trgfn_guard_emittente_scope](/dbzero/script/funzioni/trgfn_guard_emittente_scope)), uno
sulla fattura e uno sulla distinta, perché nessuno dei due copre l'altro: col solo primo il
presidio si accenderebbe *dopo* che il lavoro è finito, col solo secondo si potrebbe abbinare
denaro **proprio** alla fattura **di un altro**.

⚠️ Chi vede una riga dalla fattura **non vede la sua distinta**. I guard delle righe che
giudicano la distinta (`guard_distinta_finale`, la porta 2 di `guard_contenuto`) ne leggono stato
e origine fuori dalla row security, con
[script.fn_get_contabile_stato_origine](/dbzero/script/funzioni/fn_get_contabile_stato_origine):
letta con i diritti di chi scrive, la distinta non ci sarebbe, e il guard lascerebbe passare.

---

### Test

* `db/pgtap/rls/test-rls-pagamenti-perimetro.sql` — il perimetro delle righe: la riga da
  abbinare visibile al suo emittente e non all'altro, la distinta interna e la manuale senza
  canale che seguono la testata, la scrittura sulla distinta di un altro rifiutata.
* `db/pgtap/pagamenti/test-righe-contabili-eliminazione-v1.sql` — eliminazione dalla bozza
  manuale e congelamento sotto la validata.
* `db/pgtap/pagamenti/test-abbinamento-rata.sql` — rata, capienza e forzatura.
* `db/pgtap/vendite/test-fondo-fattura-eseguito.sql` — il legame con l'atto nella colonna
  `fondo_source_id`, e non più nel `meta`.

---

### Note di migrazione

* 2026-08-21 — `fondo_source_id` diventa una colonna con chiave esterna; prima era una stringa
  nel `meta`, senza integrità né indice, e la leggevano già tre funzioni. Il legame è diventato
  portante quando l'atto di fondo ha preso lo stato `ESEGUITO`.
* 2026-08-22 — arrivano `scadenza_id`, `forzata` e `motivo_forzatura` (abbinamento alla rata).
* 2026-08-22 — la row security si accende; lo stesso giorno una terza strada («né documento né
  canale») corregge il rifiuto, in `WITH CHECK`, della riga da abbinare su una distinta manuale
  senza canale.
* 2026-09-14 — eliminazione e congelamento del contenuto.
* 2026-09-15 — la distinta porta il suo emittente: la terza strada è morta per costruzione e viene tolta; la prima strada smette di leggere
  il canale e legge l'emittente della distinta. Una distinta interna, che prima rispondeva
  `false` sulla prima strada, ora è del suo emittente.
* 2026-09-30 — sotto una distinta annullata le righe si leggono soltanto.
* 2026-10-18 — la policy chiede l'emittente al risolutore invece che agli adattatori per riga;
  forma e strade invariate.
* 2026-10-21 — il predicato dell'eliminazione passa nella metà su distinta della check.

---

{% include-markdown "signature-core.md" %}
