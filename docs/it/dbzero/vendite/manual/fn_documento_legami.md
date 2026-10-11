## 📘 Documentazione Concettuale – Funzione `vendite.fn_documento_legami`

> 👀 **Vedi anche**
>
**Approfondimento funzioni:**
>
• [vendite.trgfn_doc_guard_annullo_con_legami](/dbzero/vendite/funzioni/trgfn_doc_guard_annullo_con_legami) — l'avviso  
> • [vendite.fn_documento_ritira_legami](/dbzero/vendite/funzioni/fn_documento_ritira_legami) — la conferma e il ritiro  
> • [vendite.fn_doc_porta_ritiro_ammette](/dbzero/vendite/funzioni/fn_doc_porta_ritiro_ammette) — la porta  
> • [vendite.vw_documento_lineage_archi](/dbzero/vendite/views/vw_documento_lineage_archi) — il nome dei documenti  

---

### 🎯 Scopo Principale
(2026-10-11, brief-db-annullo-documento-con-legami, D-4)

Risponde a una domanda sola: **«se annullo questo documento, che cosa torna
disponibile, e dove?»**. Una riga per legame.

È il **lettore unico** di tre cose che devono contare la stessa cosa:

| Chi lo legge | Per fare cosa |
| --- | --- |
| il guard dell'annullo (avviso) | rifiutare l'annullo diretto e dire quanti legami ci sono |
| il BB del ritiro (verbi di annullo) | controllare la conferma e ritirare |
| il backend | disegnare la finestra di conferma: «riga 1, ordine 12, 10 pz» |

Generalizza `vendite.fn_ddt_legami` (la sola bolla), che si è ritirata.

---

### I legami, per documento

| `origine` | `natura` | Da dove | Documento |
| --- | --- | --- | --- |
| `ORDINE` | consumo | `ordini_righe_fulfillment` (quantità evasa) | bolla |
| `RESO` | consumo | `resi_righe_riconsegne` (quantità del ponte) | bolla |
| `PREVENTIVO` | consumo | `ordini_righe.preventivo_riga_id` | ordine |
| `OFFERTA` | **provenienza** | `contratti.offerta_id`, `ordini.documento_origine_*` | contratto, ordine |
| `COMMESSA` | consumo | righe di commessa `NON_EMESSA` spinte dal documento | bolla, ordine, preventivo, contratto |

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
  (offerta) e per la commessa, che non porta la riga.
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
* Test: `db/pgtap/vendite/test-annullo-documento-con-legami-v1.sql`.

---

{% include-markdown "signature-core.md" %}
