## 📘 Documentazione Concettuale – Vista `vendite.vw_documento_lineage_archi`

> **Ultimo aggiornamento**: 8 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [config.sorgenti](/dbzero/config/tabelle/sorgenti) — i tipi dei nodi e la chiave di ognuno (`key_selector`)
> * [vendite.commesse_sorgenti](/dbzero/vendite/tabelle/commesse_sorgenti) — i link documento → commessa dei rami B, E, F, U
>
> Approfondimento viste:
>
> * [vendite.vw_documento_lineage_nodi](/dbzero/vendite/views/vw_documento_lineage_nodi) — la decorazione dei nodi (stato, fase, abortito)
>
> Approfondimento funzioni:
>
> * [vendite.fn_documento_lineage_archi](/dbzero/vendite/funzioni/fn_documento_lineage_archi) — il corpo, chiamabile per i soli documenti che servono
> * [vendite.fn_documento_lineage_sintesi](/dbzero/vendite/funzioni/fn_documento_lineage_sintesi) — la sintesi per documento (frontiera, transito)
> * [vendite.fn_documento_lineage](/dbzero/vendite/funzioni/fn_documento_lineage) — il traversal
>
> Guide:
>
> * [Sorgente polimorfa — per chi costruisce grafi tra documenti](/guide/sorgente-polimorfa#grafi-tra-documenti) — l'identità del nodo e come si risolve

---

### 🎯 Scopo Principale

`vendite.vw_documento_lineage_archi` è il grafo di genealogia e transito dei documenti di vendita in forma normalizzata: una riga per arco, cioè per relazione padre → figlio fra due documenti.

È la **proiezione** di `vendite.fn_documento_lineage_archi` senza seme: un corpo solo, che
chi vuole una parte del grafo chiama con il seme dei documenti che gli servono; la vista ha le
stesse colonne e gli stessi tipi. È la base della sintesi (`fn_documento_lineage_sintesi`) e
del traversal (`fn_documento_lineage`).

Nessun dato nuovo: tutti gli archi sono **ricostruiti** dal modello esistente. Il nodo di
arrivo è decorato (stato, fase, abortito) da `vw_documento_lineage_nodi`.

---

### 🔗 Gli archi

| Arco | Da → A | Card. | Fonte |
|---|---|---|---|
| **A** | Preventivo → Ordine | 1:1 | la provenienza dell'ordine (`sorgente_*`, tipo `PREVENTIVO`) |
| **B** | Preventivo → Commessa | 1:1 | `commesse_sorgenti` (tipo `PREVENTIVO`), `ruolo` = `ruolo_link` |
| **C** | Offerta → Contratto | 1:1 | la provenienza del contratto (`sorgente_*`, tipo `OFFERTA_COMMERCIALE`) |
| **D** | Offerta → Ordine | 1:1 | la provenienza dell'ordine (`sorgente_*`, tipo `OFFERTA_COMMERCIALE`) |
| **E** | Ordine → Commessa | 1:1 | `commesse_sorgenti` (tipo `ORDINE_VENDITA`) |
| **F** | Contratto → Commessa | **1:N** | `commesse_sorgenti` (tipo `CONTRATTO`) |
| **G** | Commessa → Fattura | **1:N** | `attivita_fatturabili.fattura_riga_id` → `fatture_righe` → `fatture` |
| **H** | Ordine → DDT | **1:N** | la provenienza della bolla (`sorgente_*`, tipo `ORDINE_VENDITA`) |
| **R** | DDT → Reso | **1:N** | la provenienza del reso (`sorgente_*`, tipo `DDT_VENDITA`) — **ramo di ritorno** |
| **N** | Fattura rettificata → Nota di credito | **1:N** | `fatture_righe.riga_rettificata_id` — **ramo di ritorno** |
| **S** | Reso → Nota di credito | **1:N** | `resi_righe_accrediti` → `attivita_fatturabili.fattura_riga_id` |
| **T** | Reso → DDT di ri-consegna | **1:N** | `resi_righe_riconsegne` → `ddt_righe` → `ddt` |
| **U** | DDT → Commessa | **1:N** | `commesse_sorgenti` (tipo `DDT_VENDITA`) |
| **V** | Offerta → sua revisione | 1:1 | `offerte_commerciali.revisione_padre_id` (madre → figlia), non un'origine |

**I rami che leggono una provenienza di testata** (A, C, D, H, R) cercano il documento a monte
con la regola d'incontro del modello: l'id o l'uid del documento, secondo la chiave che la
provenienza porta, sugli indici di `sorgente_id` e `sorgente_uid` di ogni tabella. I tipi sono
risolti per `codice_interno`, mai con id letterali.

**L'identità del nodo** è tipo + chiave del documento in testo, secondo il `key_selector` del
tipo: l'uid per preventivo e offerta, l'id per gli altri.

---

### 📑 Campi chiave esposti

* **Sorgente dell'arco**: `from_tipo_id`, `from_uid`, `from_codice`
* **Destinazione dell'arco**: `to_tipo_id`, `to_uid`, `to_codice`
* **Stato del nodo di arrivo**: `to_stato_codice_interno`, `to_fase`, `to_is_abortito`
* **`ruolo`**: `ROOT` / `COLLEGATO` dove esiste (archi da `commesse_sorgenti`), altrimenti vuoto
* **`arco`**: la lettera diagnostica, quattordici in tutto (`A`…`H`, `R`, `N`, `S`, `T`, `U`, `V`)
* **`is_ramo_inverso`**: vero per i rami di ritorno (`R`, `N`)
* **`rango_origine`**: quale sorgente è «l'origine» quando più archi in avanti entrano nello
  stesso nodo
* **`from_natura_doc_codice_interno`, `to_natura_doc_codice_interno`**: distinguono i due nodi
  `FATTURA` (fattura e nota di credito)

> ⭐ **Il vocabolario delle lettere è CHIUSO, e il presidio è un cricchetto.**
> `db/pgtap/vendite/test-documento-lineage-v1.sql` enumera le lettere ammesse: **ogni arco
> nuovo lo fa fallire apposta**, per costringere chi lo aggiunge a dichiararlo. È l'**unico**
> posto del progetto che enumera le lettere: il frontend, `fn_documento_lineage` e la sintesi
> leggono la proprietà derivata `is_ramo_inverso`, non la lettera.
>
> ⛔ **Chi allarga l'elenco non si ferma lì**: aggiunge anche l'asserzione che dice **cosa
> significa** la lettera nuova (da dove parte, dove arriva, che natura ha), come il file già fa
> per `R`, `N`, `S` e `T`, e le dà un `rango_origine`. Allargare e basta trasforma un cricchetto
> in una formalità.
>
> ⚠️ *Un consumatore che legge la **lettera** è un secondo elenco da tenere allineato a mano.*

---

### Rami di ritorno e avanzamenti

* **Arco R = flusso inverso** (la merce che torna): compare nella genealogia, ma è **escluso
  dalla frontiera in avanti** della sintesi. Il reso non è mai un discendente in avanti di un
  altro documento.
* **Arco G**: `attivita_fatturabili.fattura_riga_id` (vuoto = non ancora fatturata) →
  `DISTINCT` per non duplicare la coppia commessa → fattura.

### ⭐ `is_ramo_inverso` vive qui, una volta sola

Se la lettera del ramo di ritorno fosse scritta a mano in più posti (i filtri della sintesi, il
calcolo del traversal), aggiungere un secondo ramo di ritorno vorrebbe dire ricordarsene ogni
volta, e il posto dimenticato **non darebbe nessun errore**: solo la nota di credito comparsa
come discendente in avanti della fattura, cioè una frontiera diversa su ogni riga di lista.

⚠️ **«Inverso» non vuol dire «all'indietro nel tempo»**: la nota di credito nasce *dopo*. Vuol
dire ramo di **ritorno** (nel reso torna la merce, nella nota torna il valore), e come il reso
non è un avanzamento del flusso.

---

### ⭐ Arco N — Fattura rettificata → Nota di credito

**Da dove si legge, e perché non dall'altra fonte.** Le candidate sono due, e dicono la stessa
cosa ma **non nello stesso momento**:

* `vendite.fatture_rettifiche` — il ponte a livello **documento**, popolato da un task della
  fase DEFINITIVA che gira **dopo** la numerazione;
* `fatture_righe.riga_rettificata_id` — il legame **riga-riga**, scritto alla generazione
  delle righe.

Un grafo costruito sul ponte resterebbe muto proprio nella finestra in cui l'operatore guarda
(la nota esiste, il lotto non è ancora definitivo). È la stessa scelta dell'arco G, che legge
un soft-link e non una tabella ponte.

⚠️ **È un arco fra due nodi dello stesso tipo** (FATTURA → FATTURA). Il traversal regge (ha il
set dei visitati e il tetto di livello), ma un arco X → X non direbbe una genealogia, direbbe un
ciclo: si esclude esplicitamente.

---

### ⭐ Arco S — Reso → Nota di credito

**Il problema che chiude.** Senza S il grafo **si ferma sul reso**: la nota di credito che lo
accredita è legata alla fattura che rettifica (arco N) e alla commessa (arco G), ma non al
reso. I due rami di ritorno, la merce che torna e il valore che torna, non si toccherebbero.

**Il dato non si inventa: si legge.** `vendite.resi_righe_accrediti` registra il fatto
dell'accredito, con chi, quando, quanto e contro cosa: l'arco lo legge, via
`commessa_attivita_id` → `attivita_fatturabili.fattura_riga_id` → fattura.

⭐ **S NON è un ramo di ritorno**, e la decisione è consapevole: «inverso» vuol dire un verso
che il grafo in avanti non deve percorrere; S è invece l'**avanzamento naturale del reso** (la
merce è tornata, adesso si accredita), come H è l'avanzamento dell'ordine. La conseguenza è
voluta: **il reso smette di essere una foglia e prende la nota di credito come frontiera**.

⚠️ **Il filtro sulla riga di fattura valorizzata non è una formalità copiata da G**: un reso
accreditato e non ancora fatturato non ha arco, e lo prende all'emissione.

⛔ **Due strade ovvie che sono sbagliate**, scritte qui perché non vengano riscoperte:

1. **Scrivere il reso nella provenienza della riga di commessa.** La provenienza della riga
   entra nella **chiave di raggruppamento della fatturazione** (letta da dashboard di
   competenza, emissione mirata e gruppi dei lotti): scriverci il reso sposterebbe la rettifica
   in un altro gruppo, cioè in un altro lotto e in un altro documento. Il legame va **letto**,
   non **trasportato**.
2. **Un arco *reso → fattura originale*** via `resi_righe_accrediti.fattura_riga_rettificata_id`,
   che è a un solo join di distanza. Sarebbe in avanti come S, quindi fattura originale e nota
   di credito finirebbero allo stesso livello con lo stesso `pipeline_rank` (sono entrambe nodi
   `FATTURA`) e il pareggio si spezzerebbe sulla chiave del nodo, che è **testo**: la frontiera
   del reso diventerebbe un ordinamento lessicografico. E non serve: **il triangolo si chiude
   già**, reso —S→ nota ←N— fattura originale.

⭐ **Il legame è MOLTI-A-MOLTI, di proposito.** Tutte le rettifiche di una commessa cadono nello
stesso gruppo, quindi due resi diversi sulla stessa commessa producono **una sola** nota di
credito, che può rettificare righe di fatture diverse. Un arco calcolato regge un molti-a-molti
senza sforzo; un puntatore memorizzato no.

---

### ⭐ Arco T — Reso → DDT di ri-consegna

**Che cosa dice.** Il grafo ha R (la merce che **torna**) e S (il valore che si
**accredita**); T dice che quella merce è **ripartita**. Senza T un reso ri-consegnato
finirebbe come una foglia.

⭐ **T NON è un ramo di ritorno**, per la stessa ragione di S: il ritorno è già avvenuto ed è R;
da lì il reso ha **due modi di andare avanti**, accreditare la merce (S) o ri-consegnarla (T).
`is_ramo_inverso` resta vero per i soli `R` e `N`. Il reso prende il DDT di ri-consegna come
frontiera.

#### ⭐ La fonte è il PONTE, non la provenienza della bolla

L'arco si costruisce da `vendite.resi_righe_riconsegne`, l'aggancio duro che
[`vendite.fn_genera_ddt_riconsegna`](/dbzero/vendite/funzioni/fn_genera_ddt_riconsegna) popola
per **entrambi** i rami. Due conseguenze:

* l'arco copre anche le ri-consegne che nascono da un ordine, che come provenienza dichiarano
  `ORDINE_VENDITA` e il reso non lo nominerebbero mai;
* è una cosa diversa dalla provenienza `RESO_VENDITA` che la bolla di ri-consegna senza ordine
  dichiara: quella dice *chi è il padre* **sul documento** (il campo «Origine», l'azione «apri
  sorgente»), l'arco lo fa *comparire* **nel grafo**.

#### ⚠️ Due figli in avanti, e perché il caso è sicuro

Un reso può essere **in parte accreditato e in parte ri-consegnato**, quindi avere due figli in
avanti. Qui i due figli sono di **tipo diverso**, e i ranghi li separano:

| tipo | `pipeline_rank` |
|---|---:|
| `RESO_VENDITA` | 0 |
| `DDT_VENDITA` | **3** |
| `FATTURA` | **5** |

Il pareggio non può verificarsi. ⛔ **È quella differenza a rendere sicuro il caso**: se un
domani non ci fosse più, il difetto tornerebbe silenzioso. La risposta arriva dal **rango**, che
è struttura, non dal fatto che oggi nessun reso abbia entrambi i figli.

⚠️ **`DISTINCT` obbligatorio**: un reso con più righe ri-consegnate nello stesso DDT produrrebbe
un arco per riga.

---

### ⭐ Arco U — DDT → Commessa

La bolla è una sorgente di commessa come preventivo, ordine e contratto: stessa tabella
`commesse_sorgenti`, stesso `ruolo_link`, stesso perimetro. Senza U le commesse alimentate da una
bolla dichiarerebbero nel grafo di non avere origine, che non è «non lo so» ma un'affermazione
falsa. ⚠️ Anche i consumi (`ATTIVITA_CONSUMI`) sono sorgenti di commessa, ma non sono un nodo del
grafo: per loro non basterebbe un arco, mancherebbe il nodo.

---

### ⭐ `rango_origine`: quale sorgente è l'origine

Quando più archi in avanti entrano nello **stesso** nodo, `rango_origine` dice quale sorgente è
«l'origine»: è una scala di quanto è a monte il documento sorgente (trattativa, impegno,
esecuzione, consegna, ritorno; più basso = più origine). È un numero **scritto**, che si legge,
e non si sposta se il catalogo cambia: ordinare sull'id del tipo vorrebbe dire far decidere a un
id di seed. Le gare vere: sulla fattura vince la commessa (G) sul reso (S); sulla bolla vince
l'ordine (H) sul reso (T). La revisione dell'offerta (V) ha un rango proprio e non è un'origine.

---

### ⛔ La regola del perimetro RLS — vale per OGNI ramo

> **Ogni ramo passa dalle tabelle-testata che portano la RLS. Le tabelle-ponte non danno
> perimetro.**

`commesse_sorgenti`, `attivita_fatturabili`, `resi_righe`, `resi_righe_accrediti`,
`resi_righe_riconsegne` e `ddt_righe` oggi hanno la RLS, per legame col loro documento. La regola
resta: l'arco nasce dal documento che il chiamante vede, non da una riga di collegamento. Un ramo
che si fermasse su una tabella senza perimetro produrrebbe un arco verso un documento che il
chiamante **non può vedere**. I rami N e S arrivano alla fattura dalle sue righe
(`fatture_righe`), che portano lo stesso perimetro della testata.

⚠️ **E la decorazione del nodo non salva**: `vw_documento_lineage_nodi` è in `LEFT JOIN`, quindi
la riga dell'arco resterebbe con `from_codice` / `to_codice` vuoti invece di sparire.

⛔ **La chiave dei rami B, E, F, U non è la stessa.** Il link di commessa porta la chiave del
documento nella colonna del suo tipo: `sorgente_uid` per il preventivo, `sorgente_id` per
ordine, contratto e DDT. Il join verso il documento confronta colonne dello stesso tipo, senza
cast, e resta efficiente anche sotto RLS; un join scritto con la colonna copiata da un altro
ramo **non darebbe errore**, azzererebbe quel gruppo di archi.

⚠️ **Sul dato di sviluppo il difetto non si riproduce** se l'operatore di collaudo vede tutti i
documenti: il presidio vale per il giorno in cui un operatore è ristretto a un emittente. Il
test del pgTAP vale **solo** perché la suite gira come `zeroerp_app` con la RLS attiva: con
`PGTAP_RUNNER=owner` sarebbe verde per costruzione, **chi lo sposta lo spegne.**

---

### Note operative

* **`security_invoker=on`**: la RLS del chiamante si applica; la reloption va ri-specificata a
  ogni ridefinizione della vista.

---

### Test

* `db/pgtap/vendite/test-documento-lineage-v1.sql` — il vocabolario chiuso delle lettere, il
  significato di ogni lettera, il rango d'origine, il perimetro RLS dei rami.

---

### Note di migrazione

* 2026-08-21 — arco N, fattura rettificata → nota di credito.
* 2026-08-25 — arco S, reso → nota di credito; la regola del perimetro RLS chiude i rami B, E, F
  e G, che si fermavano su tabelle-ponte.
* 2026-08-28 — arco T (reso → DDT di ri-consegna, brief-db-ddt-riconsegna-eredita-testata
  §9.4.1), arco U (DDT → commessa) e `rango_origine`, che prima si decideva sull'id del tipo.
* 2026-10-05 — le chiavi di preventivi e ordini dei rami B ed E, allora scritte come testo, e i
  nodi si leggono una volta sola: la vista da circa 380 a circa 90 ms
  (brief-db-liste-documento-lineage-lenta).
* 2026-10-11 — il corpo passa in `vendite.fn_documento_lineage_archi`, chiamabile col seme; la
  vista ne è la proiezione senza seme. Ritirata `vw_documento_lineage`, sostituita da
  `vendite.fn_documento_lineage_sintesi` (brief-db-lineage-seminata-per-chiave §8.3).
* 2026-11-06 — gli archi A, C, D leggono la provenienza `sorgente_*` di ordine e contratto, al
  posto di `vendite.ordini.documento_origine_*` (vocabolario `PREVENTIVO` / `OFFERTA`) e di
  `vendite.contratti.offerta_id`, ritirate (brief-db-sorgente-documento-e-riga).
* 2026-11-07 — i rami B, E, F, U leggono la chiave tipizzata del link di commessa al posto della
  chiave testuale (brief-db-sorgente-documento-e-riga).

---

{% include-markdown "signature-core.md" %}
