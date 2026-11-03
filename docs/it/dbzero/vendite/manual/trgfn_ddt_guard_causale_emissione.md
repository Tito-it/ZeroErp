## 📘 Documentazione Concettuale – Funzione `vendite.trgfn_ddt_guard_causale_emissione()`

> **Ultimo aggiornamento**: 3 novembre 2026

> 👀 **Vedi anche**
>
> Tabelle:
> [vendite.ddt](/dbzero/vendite/tabelle/ddt)
> [vendite.ddt_righe](/dbzero/vendite/tabelle/ddt_righe)
> [config.causali_trasporto](/dbzero/config/tabelle/causali_trasporto)
> [vendite.ordini_righe_fulfillment](/dbzero/vendite/tabelle/ordini_righe_fulfillment)
>
> Guard gemello (stesso momento, stessa forma):
> [vendite.trgfn_ddt_guard_indirizzi_obbligatori](trgfn_ddt_guard_indirizzi_obbligatori.md)
>
> Errori:
> [config.messaggi_errore E_DDT_CAUSALE_OBBLIGATORIA (id=544)](/dbzero/config/tabelle/messaggi_errore)
> [config.messaggi_errore E_DDT_PREZZO_NON_RISOLVIBILE (id=545)](/dbzero/config/tabelle/messaggi_errore)
>
> Brief autorevole: `docs/it/dev/work-in-progress/brief-db-fatturazione-ddt-resi.md` §4a

---

### 🎯 Scopo Principale

(rev 2026-08-28)

Blocca l'**emissione** di un DDT (transizione a stato `EMESSO`) quando il documento non
dichiara **perché la merce viaggia**, quando dichiara una vendita ma non ha prezzi con cui
fatturarla, o quando una riga porta un **prezzo senza aliquota**.

> ⚠️ **Il nome nomina la sola causale, ed è rimasto quello di quando il motivo era uno.**
> Oggi il guard è il gate del **valore della riga** in tre facce. Il nome **non si cambia** —
> rinominare una trigger function significa rinominare il trigger, ogni doc auto-generata che la
> cita e ogni pgTAP che la nomina, per un guadagno di sola leggibilità — ma chi legge non deve
> dedurlo: sta scritto qui e nello `Scopo` del corpo.

Applicata dal trigger `trg_ddt_a10_guard_causale_emissione_upd`
(fase `_a10_`, `BEFORE UPDATE OF stato_doc_ddt_id`) — stesso posizionamento del guard
indirizzi.

**Il problema che risolve.** Il DDT ammette per progetto righe senza prezzo (*«solo
trasporto»*: campionature, trasferimenti, conto lavoro). Ma senza una dichiarazione esplicita,
un DDT senza prezzi è ambiguo: è una scelta o una dimenticanza? Il sistema, non sapendolo, lo
avrebbe proposto «da fatturare» con prezzo vuoto. Invece di **inferire** l'intento
dall'assenza di prezzo, lo si fa **dichiarare a monte** con il campo che l'operatore già
compila — la causale di trasporto.

---

### Le tre regole

**R1 — la causale è obbligatoria all'emissione.**
`ddt.causale_trasporto_id` è nullable, ma dall'emissione in poi non è più ammesso: senza
causale il documento resterebbe ambiguo per la fatturazione. In **bozza il NULL resta
legittimo** — la causale si compila prima di emettere, esattamente come l'indirizzo.

> Conseguenza voluta a valle: il lister e i cruscotti **non devono trattare il NULL** in modo
> speciale, perché un DDT senza causale non raggiunge mai uno stato in cui verrebbe guardato.

**R2 — se la causale è fatturabile, ogni riga attiva deve avere un prezzo *risolvibile*.**
Risolvibile significa: prezzo proprio della riga DDT **oppure** ereditato dalla riga d'ordine
via `ordini_righe_fulfillment`. È la stessa `COALESCE` che usano il lister e i cruscotti.

> ⚠️ **Prezzo risolvibile ≠ prezzo presente**: una riga da evasione **senza** prezzo proprio è
> perfettamente legittima, purché l'ordine glielo fornisca. Pretendere il prezzo sulla riga DDT
> bloccherebbe un caso valido — vale per questo guard come per il frontend.
>
> ⚠️ `vw_ddt_righe_iva_base` **non è riusabile** per questo controllo: filtra
> `prezzo_unitario IS NOT NULL`, cioè perde esattamente le righe da esaminare.

Con causale **non fatturabile** i prezzi sono irrilevanti: nessun controllo, il documento è
solo trasporto.

Il risultato è che **il prezzo dimenticato diventa un errore all'emissione**, invece di un
documento silenziosamente mal classificato che poi genererebbe attività senza prezzo.

**R3 — una riga che porta un *prezzo* porta anche l'*aliquota*.** (rev 2026-08-28)
Se `prezzo_unitario` è valorizzato e `iva_id` no, l'emissione si ferma. In **bozza il NULL
resta legittimo**, come per la causale in R1: il documento si lavora, e si dichiara completo
quando esce.

> ⭐ **Qui il discrimine è il PREZZO, non la causale — ed è la differenza con R2.**
> R2 si condiziona sulla causale perché un documento che non vende non deve avere un prezzo
> *risolvibile*. Ma se un prezzo **c'è** — e su un conto visione può esserci — quella riga entra
> comunque nel **riepilogo IVA** del documento, che la causale non la guarda affatto: ne
> uscirebbe una riga con **imponibile pieno, codice IVA vuoto e imposta zero**, su un foglio che
> si stampa e si consegna.
>
> > *Un vincolo deve avere lo stesso perimetro del consumatore che protegge.*
>
> ⚠️ E per la stessa ragione R3 guarda `prezzo_unitario` della riga DDT e **non** la `COALESCE`
> col fulfillment che usa R2: una riga dal prezzo solo **derivato** nel riepilogo non entra,
> quindi non ha il difetto — pretendere lì l'aliquota bloccherebbe un documento sano.
>
> ⛔ **Perché non un `NOT NULL` sulla colonna**, che sarebbe la forma ovvia:
> `vendite.ordini_righe.iva_id` è **nullable** e `fn_genera_ddt_da_ordine` la copia tale e
> quale, quindi il vincolo avrebbe fatto **fallire l'evasione di un ordine** con un errore
> tecnico muto, su un percorso che funziona. Il NULL è ammesso lungo tutta la catena: chiudere
> l'ultimo anello sposta il punto di rottura su chi non c'entra. *Un vincolo si mette dove il
> dato si può fornire, non dove il difetto si vede.*

---

### Errori sollevati

| Codice | Quando | Contesto | Nella frase |
|---|---|---|---|
| `E_DDT_CAUSALE_OBBLIGATORIA` (544) | R1: emissione senza causale | `ddt_id`, `numero` | numero DDT |
| `E_DDT_PREZZO_NON_RISOLVIBILE` (545) | R2: causale fatturabile + riga senza prezzo risolvibile | `ddt_id`, `numero`, **`riga_id`** | numero DDT + `riga_id` |
| `E_DDT_RIGA_IVA_MANCANTE` (1009) | R3: riga con prezzo e senza aliquota | `ddt_id`, `numero`, `riga_id`, **`riga_nr`** | numero DDT + **`riga_nr`** |

> ⚠️ **Il codice nuovo mette nella frase il NUMERO di riga, non l'id** — e il gemello (545)
> mette l'id. Non è un'incoerenza rimasta lì per caso: i valori che riempiono i `%s`
> **compongono la frase che una persona legge**, e un id tecnico non si cerca a mano sul
> documento. L'id resta nel contesto, che è il canale di chi diagnostica. ⛔ Il 545 **non** è
> stato «corretto» nello stesso giro: cambiare il testo di un messaggio in servizio dentro un
> changeSet che parla d'altro è un'altra modifica.
>
> ⚠️ `E_DDT_RIGA_IVA_MANCANTE` è **`CONFLITTO_STATO`** (409) come i suoi due gemelli, non
> `DATO_ERRATO`: la richiesta è *«porta il DDT a EMESSO»*, e non c'è un campo **di quella
> richiesta** da correggere — è la situazione del documento a non consentirla. Ne discende che
> nel contesto **non** va la chiave `campo`.

---

### Gli oneri della bolla (rev 2026-11-03)

Dal `20261103-42` (brief-db-addebito-trasporto-ordine §8.3) il guard solleva anche i due motivi sugli
oneri di [`script.fn_check_ddt_emittibile`](/dbzero/script/funzioni/fn_check_ddt_emittibile):

| Codice | Quando | Nella frase |
| --- | --- | --- |
| `E_DDT_EMISSIONE_SOLO_ONERI` | righe attive, nessuna di merce (K-2) | il documento |
| `E_DDT_ONERE_NON_FATTURABILE` | un onere che non verrebbe mai fatturato: causale non fatturabile (anche se copiato), o onere senza legame su una bolla di un ordine che fattura alla conferma | documento e numero di riga |

Qui e non nel guard di transizione: è il gate del valore della riga, e il suo LOOP per codice cresce
così. Presidio: `db/pgtap/vendite/test-ddt-onere-emissione-v1.sql`.

---

### Esempio d'uso

```sql
-- Emissione bloccata: manca la causale.
UPDATE vendite.ddt SET stato_doc_ddt_id = <EMESSO> WHERE id = 123;
-- ERRORE: DDT DDT0000123: causale di trasporto obbligatoria per l'emissione.

-- Dichiarando "solo trasporto" l'emissione passa, prezzi o non prezzi.
UPDATE vendite.ddt
   SET causale_trasporto_id = (SELECT id FROM config.causali_trasporto WHERE codice='CAMPIONATURA')
 WHERE id = 123;
```

---

### Note operative

* **Quale causale è fatturabile lo dice il vocabolario**, non il codice:
  `config.causali_trasporto.fatturabile`. Oggi solo `VENDITA` è `true`. I casi ambigui — per
  esempio l'omaggio, che qualcuno fattura a sconto 100% — si risolvono cambiando **una cella di
  seed**, senza toccare questa funzione (stesso pattern di `tipi_reso.riapre_residuo`).
* **Ordine di scatto**: questo guard e quello sugli indirizzi sono entrambi in fase `_a10_` su
  `BEFORE UPDATE OF stato_doc_ddt_id`. Se un documento viola entrambe le condizioni, l'operatore
  vedrà prima l'uno e poi l'altro — comportamento normale dei guard fail-fast, ma da sapere
  quando si legge un errore soltanto.
* **Impatto sulle fixture di test**: qualunque test che porti un DDT a `EMESSO` deve ora
  valorizzare la causale prima della transizione. È il motivo per cui le fixture pgTAP della
  slice assegnano `VENDITA` prima di emettere.
  ⚠️ **Dal 2026-08-28 non basta più**: con R3, una fixture che valorizza il prezzo e non
  l'aliquota non emette. E ⛔ *«DDT di solo trasporto»* sono **due** condizioni, non una —
  causale **non** fatturabile **e** righe **senza** prezzo: con la causale `VENDITA` una riga
  senza prezzo la ferma già R2, con un errore che *sembra* di R3 e non lo è. Costato un rosso
  in fase di scrittura del test.
* **Il predicato non si riscrive qui**: le tre condizioni le valuta
  [`script.fn_check_ddt_emittibile`](/dbzero/script/funzioni/fn_check_ddt_emittibile), che è la
  sorgente unica condivisa con la capability. Questo guard **sceglie** dai motivi ricevuti
  quelli di propria competenza e li solleva. ⚠️ Il `LOOP` non ha un `ELSE`, di proposito: i
  motivi che non riconosce li solleva un altro dei quattro guard di emissione, e un catch-all
  qui farebbe uscire gli indirizzi mancanti con l'area e il nome sbagliati nel log.
* Test: `db/pgtap/vendite/test-ddt-solo-trasporto-causale-v1.sql` (R1, R2) ·
  `db/pgtap/vendite/test-fn-genera-ddt-riconsegna-eredita-v1.sql` asserzioni 13-16 (R3, tutte e
  quattro le combinazioni di causale × prezzo).

---

{% include-markdown "signature-core.md" %}

### Il trasporto non dovuto (rev 2026-11-03)

Dal `20261103-48` solleva anche `E_DDT_TRASPORTO_NON_DOVUTO`, il motivo 3-quater di
`script.fn_check_ddt_emittibile` (`-47`): un onere di causale `TRASPORTO` su una bolla in porto
assegnato o con addebito a terzi. Il ramo serve perché il `LOOP` non ha `ELSE`: senza, il motivo
spegnerebbe il pulsante ma l'emissione passerebbe. Nella frase: il documento, il numero di riga e la
modalità di addebito leggibile.
