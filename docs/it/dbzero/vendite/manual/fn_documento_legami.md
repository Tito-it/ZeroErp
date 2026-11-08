## 📘 Documentazione Concettuale – Funzione `vendite.fn_documento_legami`

> **Ultimo aggiornamento**: 8 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento viste:
>
> * [vendite.vw_documento_lineage_archi](/dbzero/vendite/views/vw_documento_lineage_archi) — il nome dei documenti
>
> Approfondimento funzioni:
>
> * [vendite.trgfn_doc_guard_annullo_con_legami](/dbzero/vendite/funzioni/trgfn_doc_guard_annullo_con_legami) — l'avviso
> * [vendite.fn_documento_ritira_legami](/dbzero/vendite/funzioni/fn_documento_ritira_legami) — la conferma e il ritiro
> * [vendite.fn_doc_porta_ritiro_ammette](/dbzero/vendite/funzioni/fn_doc_porta_ritiro_ammette) — la porta
> * [script.fn_sorgente_documento](/dbzero/script/funzioni/fn_sorgente_documento) — il BB che risolve il documento dalla provenienza
>
> Guide:
>
> * [Sorgente polimorfa](/guide/sorgente-polimorfa) — il modello della provenienza

---

### 🎯 Scopo Principale

`vendite.fn_documento_legami` risponde a una domanda sola: **«se annullo questo documento, che cosa torna disponibile, e dove?»**. Una riga per legame.

Il documento si nomina col suo codice in `config.sorgenti` (`DDT_VENDITA`, `ORDINE_VENDITA`,
`PREVENTIVO`, `CONTRATTO`, `COMMESSA`, `OFFERTA_COMMERCIALE`), e `origine` è il codice del
documento dall'altra parte, nello stesso vocabolario.

È il **lettore unico** di tre cose che devono contare la stessa cosa:

| Chi lo legge | Per fare cosa |
| --- | --- |
| il guard dell'annullo (avviso) | rifiutare l'annullo diretto e dire quanti legami ci sono |
| il BB del ritiro (verbi di annullo) | controllare la conferma e ritirare |
| il backend | disegnare la finestra di conferma: «riga 1, ordine 12, 10 pz» |

---

### I legami, per documento

| `origine` | `natura` | Da dove | Documento |
| --- | --- | --- | --- |
| `ORDINE_VENDITA` | `CONSUMO` | `ordini_righe_fulfillment` (quantità evasa) | bolla |
| `RESO_VENDITA` | `CONSUMO` | `resi_righe_riconsegne` (quantità del ponte) | bolla |
| `PREVENTIVO` | `CONSUMO` | `ordini_righe.preventivo_riga_id` | ordine |
| `OFFERTA_COMMERCIALE` | **`PROVENIENZA`** | la provenienza `sorgente_*` del documento: tipo `OFFERTA_COMMERCIALE` e la chiave dell'offerta | contratto, ordine |
| `COMMESSA` | `CONSUMO` | righe di commessa `NON_EMESSA` spinte dal documento, cercate con la chiave del documento data dal BB che risolve | bolla, ordine, preventivo, contratto |
| `OFFERTA_COMMERCIALE` | **`PROVENIENZA`** | `offerte_commerciali.revisione_padre_id`: la revisione precedente, superata, che torna emessa | offerta |

#### L'offerta

Annullare l'**ultima revisione viva** di un'offerta fa tornare emessa la revisione
precedente: è un annullo che riapre un altro documento, e la guida del modello (§8)
lo vuole confermato. Il legame è il padre (`origine_id`), di provenienza: non si
ritira niente, il ritorno lo scrive la proiezione
[`vendite.fn_offerta_proietta_stato_revisione`](/dbzero/vendite/funzioni/fn_offerta_proietta_stato_revisione)
dopo l'annullo. Nessun legame se la revisione è già annullata, se il padre non è
superato o se un'altra revisione viva lo tiene superato: l'annullo non riaprirebbe
niente. Il verbo che conferma è [`vendite.fn_annulla_offerta`](/dbzero/vendite/funzioni/fn_annulla_offerta).

#### La commessa

La commessa è **a valle** di tutto ciò che la riempie: i suoi legami sono le sue
righe `NON_EMESSA`, una riga per legame (`riga_id` = la riga di commessa).

| `origine` | `natura` | La riga | All'annullo della commessa |
| --- | --- | --- | --- |
| `PREVENTIVO`, `ORDINE_VENDITA`, `CONTRATTO`, `DDT_VENDITA` | `CONSUMO` | spinta dal documento | si ritira; il documento torna da mandare in commessa |
| `ATTIVITA_CONSUMI` | `CONSUMO` | spinta da un consumo | si ritira; il consumo torna da mandare |
| `RESO_VENDITA` | `CONSUMO` | la rettifica di un accredito (`origine_riga_id` = la riga di reso) | l'accredito si annulla |
| `ONERE` | **`ANNULLO`** | un onere, senza documento a monte | si annulla con la commessa |

Per le righe con una provenienza, `origine` è il codice del tipo com'è in `config.sorgenti`;
`ONERE` non è un tipo di documento, è il nome del legame che non ne ha uno.

Una riga senza provenienza è sempre un onere o una rettifica: lo impone il vincolo
`chk_commesse_attivita_senza_sorgente_onere_rettifica`.

⭐ **La natura `ANNULLO`** esiste perché la finestra possa dire «si annulla»
invece di «si riapre»: dietro un onere non c'è niente da riaprire. Per l'avviso
conta come un consumo: rifiuta finché la riga c'è.

`origine_id` viene dal BB che risolve la provenienza,
[`script.fn_sorgente_documento`](/dbzero/script/funzioni/fn_sorgente_documento), sulle colonne
del modello della riga di commessa.
Le commesse già annullate non si filtrano: con l'avviso e il verbo una commessa
annullata non ha più righe `NON_EMESSA` (D-9).

⭐ **Consumo e provenienza.** Il consumo è qualcosa che il documento ha
*occupato* a monte (una quantità dell'ordine, una riga del preventivo, lavoro in
commessa): annullando si **ritira**. La provenienza dice *da dove viene* il
documento: resta sul documento annullato, e l'offerta torna trasformabile
perché l'unicità vale sui soli documenti vivi. Non si ritira, ma si **conferma**
lo stesso: chi annulla deve sapere che l'offerta si riapre.

⚠️ Due cose che **non** sono legami, e perché:

* le righe di commessa `EMESSA`: **bloccano** l'annullo, non chiedono conferma
  ([`trgfn_doc_guard_chiusura_sorgente`](/dbzero/vendite/funzioni/trgfn_doc_guard_chiusura_sorgente),
  via d'uscita «Riporta da emettere»);
* la provenienza da `PREVENTIVO` sulla testata dell'ordine: dal preventivo si
  riaprono le **righe**, che sono già nell'elenco.

---

### Le colonne

* `riga_id`, `riga_nr`: la riga del documento; `NULL` per i legami di testata
  (offerta) e per la commessa vista dal documento, che non porta la riga. Per
  la commessa come documento, `riga_id` è la riga di commessa (`riga_nr` NULL).
* `origine_id`: la testata dall'altra parte (o la commessa); `origine_riga_id`:
  la sua riga (riga d'ordine, di reso, di preventivo, attività di commessa).
* `qta`: la quantità che torna disponibile, dove ha senso.
* ⛔ **Niente etichette**: il nome dei documenti, per il gesto «vai al
  documento», lo dà il lineage (decisione di Tid del 2026-10-11).

---

### ⭐ Perché `SECURITY DEFINER`

Il verbo che conferma gira come proprietario; il guard e la finestra girano come
l'applicazione. Sotto la RLS i legami stanno su tabelle con perimetri propri
(righe di commessa, ordini, resi): un lettore `INVOKER` potrebbe vederne meno
del verbo. Due danni possibili:

* la conferma non tornerebbe mai («hai visto 2, sono 3»);
* peggio, il guard ne vedrebbe **zero** e lascerebbe annullare in silenzio, che
  è proprio il difetto che questo lettore esiste per chiudere.

Il documento lo sceglie chi chiama, che lo sta annullando o mostrando; la
funzione restituisce solo id e quantità dei suoi legami. `EXECUTE` all'app, non
a `PUBLIC`.

---

### Codici errore

| Codice | Quando |
| --- | --- |
| `E_VENDITE_CHIAMATA_NON_VALIDA` | documento sconosciuto o id non valido: un guard montato male deve gridare, non vedere zero legami |

---

### Note operative

* Il backend la legge alla risposta `E_DOC_ANNULLO_CON_LEGAMI` per disegnare la
  finestra, poi chiama il verbo del documento passando **quante righe ha
  mostrato**.
* Test: `db/pgtap/vendite/test-annullo-documento-con-legami-v1.sql`;
  per la commessa `test-annullo-commessa-v1.sql` e
  `test-annullo-commessa-rettifica-v1.sql`.

---

### Note di migrazione

* 2026-10-11 — nasce generalizzando `vendite.fn_ddt_legami` (la sola bolla), che si è ritirata
  (brief-db-annullo-documento-con-legami, D-4).
* 2026-10-12 — la commessa come documento: un legame per riga `NON_EMESSA`; il ramo `MANUALE`
  esce quando il vincolo di tabella impone che una riga senza sorgente sia un onere o una
  rettifica (brief-db-annullo-a-valle-riapre-a-monte).
* 2026-10-19 — `origine` usa i codici di `config.sorgenti` (`ORDINE_VENDITA`, `RESO_VENDITA`,
  `OFFERTA_COMMERCIALE`, `DDT_VENDITA`, `ATTIVITA_CONSUMI`) al posto dei nomi corti di prima.
* 2026-10-26 — l'offerta come documento: la revisione precedente che torna emessa
  (brief-modello-documento-vendita §13, O-4).
* 2026-11-06 — la provenienza dall'offerta si legge da `sorgente_*` di contratto e ordine, non più
  da `vendite.contratti.offerta_id` né da `vendite.ordini.documento_origine_*`, ritirate; la
  chiave del documento e quella della riga di commessa le dà il BB che risolve
  (brief-db-sorgente-documento-e-riga).

---

{% include-markdown "signature-core.md" %}
