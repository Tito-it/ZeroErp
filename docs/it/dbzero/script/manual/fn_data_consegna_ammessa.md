## 📘 Documentazione Concettuale – Funzione `script.fn_data_consegna_ammessa()`

> 👀 **Vedi anche**
>
Approfondimento funzioni:
> • [script.fn_doc_date_consegna_anteriori](/dbzero/script/manual/fn_doc_date_consegna_anteriori) — quali colonne sono date di consegna, e il lettore dei due guard
> • [script.trgfn_doc_righe_guard_data_consegna](/dbzero/script/manual/trgfn_doc_righe_guard_data_consegna) — il rifiuto sulla riga
> • [script.trgfn_doc_testata_guard_data_consegna_righe](/dbzero/script/manual/trgfn_doc_testata_guard_data_consegna_righe) — il rifiuto sulla testata
> • [vendite.fn_push_preventivo_a_ordine](/dbzero/vendite/manual/fn_push_preventivo_a_ordine) e [vendite.fn_crea_revisione_preventivo](/dbzero/vendite/manual/fn_crea_revisione_preventivo) — le copie che azzerano
>
Guide: [Gestione Ordini §3.5](/guide/gestione-ordini) · [Gestione Preventivi](/guide/gestione-preventivi)

---

### 🎯 Scopo Principale

(nata il 2026-10-13, dal collaudo)

**Una consegna non viene prima del documento che la prevede.** Sulle righe di
ordine e di preventivo di vendita si salvavano date di consegna anteriori alla
data del documento, dal form di riga e da «Aggiorna date di consegna» in blocco.
Questa funzione è **la regola**, scritta una volta:

| Data di consegna | Data del documento | Risposta |
| --- | --- | --- |
| vuota | qualsiasi | ammessa — vuol dire «nessuna data» |
| uguale | — | ammessa — consegna in giornata |
| successiva | — | ammessa |
| **anteriore** | — | **non ammessa** |
| qualsiasi | vuota | ammessa — senza riferimento non c'è confronto |

L'ultima riga non è un caso delle testate (la loro data è obbligatoria): esiste
per chi chiama senza un documento.

### 🧭 Chi la legge, e cosa fa con la risposta

| Chi | Con una data non ammessa |
| --- | --- |
| il guard di **riga** (ordini, preventivi) | rifiuta: `E_DOC_RIGA_DATA_CONSEGNA_ANTERIORE` |
| il guard di **testata** (ordini, preventivi) | rifiuta lo spostamento della data del documento: `E_DOC_DATA_OLTRE_CONSEGNA_RIGHE` |
| `fn_push_preventivo_a_ordine` | copia la data **vuota** sulla riga d'ordine |
| `fn_crea_revisione_preventivo` | copia la data **vuota** sulla riga della revisione |

⭐ **Perché una funzione per un confronto.** Il confronto è banale, il
significato no: quattro posti rispondono alla stessa domanda. Se un giorno la
regola cambia — un margine di giorni, la consegna in giornata vietata — cambia
qui, e i quattro rispondono uguale.

### ⚖️ Perché le copie azzerano (decisione di Tid, 2026-10-13)

Esempio: un preventivo chiede la consegna per il 5 ottobre e diventa un ordine
il 10. Tre strade:

* **rifiutare** — il preventivo è fuori bozza e la data lì non si correggerebbe
  più: lo smistamento resterebbe fermo, e l'operatore senza rimedio;
* **portarla alla data dell'ordine** — nella colonna «richiesta dal cliente»
  finirebbe una richiesta che il cliente non ha fatto;
* **azzerarla** ✅ — la richiesta vera resta sul documento di partenza, la copia
  nasce in bozza e l'operatore la riscrive.

### ⚠️ Cosa NON fa

* Non confronta le due date di una riga fra loro: confermare *prima* di quanto il
  cliente ha chiesto è una buona notizia, e resta ammesso.
* Non vieta la retrodatazione: si retrodata il documento, e le consegne vengono
  dopo.
* Non è un `CHECK` di tabella: un `CHECK` risponderebbe muto, senza dire quale
  data e rispetto a cosa. La regola parla dai guard, con una frase.

Presidio: `db/pgtap/vendite/test-data-consegna-vs-data-documento-v1.sql`.
