## 📘 Documentazione Concettuale – Vista `vendite.vw_documento_lineage_archi`

> 👀 **Vedi anche**
>
> Approfondimento:
>
> [vendite.vw_documento_lineage_nodi](/dbzero/vendite/views/vw_documento_lineage_nodi)
> [vendite.fn_documento_lineage_sintesi](/dbzero/vendite/funzioni/fn_documento_lineage_sintesi) (era `vw_documento_lineage`, ritirata nel giro B)
> [vendite.fn_documento_lineage](/dbzero/vendite/funzioni/fn_documento_lineage)
> [config/manual/sorgenti.md — Convenzione chiave sorgente](/dbzero/config/manual/sorgenti)

---

### 🎯 Scopo Principale

`vendite.vw_documento_lineage_archi` è il **grafo di genealogia/transito**
dei documenti vendite in forma **normalizzata**: **una riga per arco** (relazione
padre→figlio tra due documenti). È la base da cui derivano sia la summary
`vw_documento_lineage` sia il traversal `fn_documento_lineage`.

Nessun dato nuovo: tutti gli archi sono **ricostruiti** dal modello esistente. Il nodo
target è decorato (stato/fase/is_abortito) tramite `vw_documento_lineage_nodi`.

---

### 🔗 Gli archi (dal design §2)

| Arco | Da → A | Card. | Fonte |
|---|---|---|---|
| **A** | Preventivo → Ordine | 1:1 | `ordini.documento_origine_tipo='PREVENTIVO'/_id` (enum CHECK) |
| **B** | Preventivo → Commessa | 1:1 | `commesse_sorgenti` (sorgente PREVENTIVO) — `ruolo=ruolo_link` |
| **C** | Offerta → Contratto | 1:1 | `contratti.offerta_id` |
| **D** | Offerta → Ordine | 1:1 | `ordini.documento_origine_tipo='OFFERTA'/_id` |
| **E** | Ordine → Commessa | 1:1 | `commesse_sorgenti` (sorgente ORDINE_VENDITA) |
| **F** | Contratto → Commessa | **1:N** | `commesse_sorgenti` (sorgente CONTRATTO) |
| **G** | Commessa → Fattura | **1:N** | `attivita_fatturabili.fattura_riga_id` → `fatture_righe` → `fatture` |
| **H** | Ordine → DDT | **1:N** | `ddt.sorgente_uid`(uuid)=`ordini.uid` (tradotto a `ordini.id`) |
| **R** | DDT → Reso | **1:N** | `resi.sorgente_uid`(uuid)=`ddt.uid` — **ramo INVERSO** |
| **N** | Fattura rettificata → Nota di credito | **1:N** | `fatture_righe.riga_rettificata_id` — **ramo INVERSO** (rev 2026-08-21, sezione in fondo) |
| **S** | Reso → Nota di credito | **1:N** | `resi_righe_accrediti` → `attivita_fatturabili.fattura_riga_id` (rev 2026-08-25, sezione in fondo) |
| **T** | Reso → DDT di ri-consegna | **1:N** | `resi_righe_riconsegne` → `ddt_righe` → `ddt` (rev 2026-08-28, sezione in fondo) |

Le **colonne tipizzate dirette** in uuid (`ddt.sorgente_uid`, `resi.sorgente_uid`) sono
tradotte alla chiave nodo con un JOIN alla tabella target (regola brief §0 Q1). I tipi
sono risolti per `codice_interno` (§6d), mai id letterali.

---

### 📑 Campi chiave esposti

* **Sorgente arco**: `from_tipo_id`, `from_uid`, `from_codice`
* **Destinazione arco**: `to_tipo_id`, `to_uid`, `to_codice`
* **Stato del target** (dal nodo): `to_stato_codice_interno`, `to_fase`, `to_is_abortito`
* **`ruolo`**: `ROOT`/`COLLEGATO` dove esiste (archi da `commesse_sorgenti`), altrimenti NULL
* **`arco`**: lettera diagnostica `A`..`H`, `R`, `N`, `S`, `T`, `U` — **tredici** dal
  2026-08-29 (`U` = DDT → Commessa, la quarta sorgente di commessa)

> ⭐ **Il vocabolario delle lettere è CHIUSO, e il presidio è un cricchetto.**
> `db/pgtap/vendite/test-documento-lineage-v1.sql` asserisce
> `arco NOT IN ('A',…,'T')`: **ogni arco nuovo lo fa fallire apposta**, per costringere chi lo
> aggiunge a dichiararlo. È l'**unico** posto del progetto che enumera le lettere — verificato
> il 2026-08-28: il frontend, `fn_documento_lineage` e la summary leggono tutti la proprietà
> derivata `is_ramo_inverso`, non la lettera.
>
> ⛔ **Chi allarga l'elenco non si ferma lì**: aggiunge anche l'asserzione che dice **cosa
> significa** la lettera nuova — da dove parte, dove arriva, che natura ha — come il file già fa
> per `R`, `N`, `S` e `T`. Allargare e basta trasforma un cricchetto in una formalità, e il
> valore successivo passerebbe senza che nessuno lo guardi.
>
> ⚠️ *Un consumatore che legge la **lettera** è un secondo elenco da tenere allineato a mano.*
> Chi aggiunge un arco lo tenga presente: la forma giusta è leggere una proprietà.

---

### Esempio d'uso

```sql
-- Tutti gli archi uscenti/entranti di un documento (bidirezionale per costruzione).
SELECT arco, from_codice, to_codice, to_fase, ruolo
FROM vendite.vw_documento_lineage_archi
WHERE (from_tipo_id, from_uid) = (:tipo, :uid)     -- uscenti
   OR (to_tipo_id,   to_uid)   = (:tipo, :uid);    -- entranti
```

---

### Note operative

* **Arco R = flusso inverso** (merce che torna): compare nella genealogia, ma è
  **escluso dalla frontiera forward** della summary. Il reso non è mai un discendente
  forward di un altro documento.
* **Arco G**: `attivita_fatturabili.fattura_riga_id` (soft-link a `fatture_righe.id`,
  `NULL` = non ancora fatturata) → `DISTINCT` per non duplicare la coppia commessa→fattura.
* **`security_invoker=on`**: RLS emittente del chiamante (reloption da ri-specificare ad
  ogni `CREATE OR REPLACE`).
* Test: `db/pgtap/vendite/test-documento-lineage-v1.sql`.

---


### ⭐ Arco N — Fattura rettificata → Nota di credito (rev 2026-08-21)

| Arco | Da → A | Card. | Fonte |
|---|---|---|---|
| **N** | Fattura rettificata → Nota di credito | **1:N** | `fatture_righe.riga_rettificata_id` → riga → fattura (`DISTINCT`) |

**Da dove si legge, e perché non dall'altra fonte.** Le candidate erano due, e
dicono la stessa cosa ma **non nello stesso momento**:

* `vendite.fatture_rettifiche` — il ponte a livello **documento**, popolato da un
  task della fase DEFINITIVA che gira **dopo** la numerazione;
* `fatture_righe.riga_rettificata_id` — il legame **riga-riga**, scritto alla
  generazione delle righe.

⚠️ Misurato il 2026-08-21: la prima nota di credito esiste con tre righe
collegate, e `fatture_rettifiche` è **ancora a zero righe** perché il lotto non è
stato reso definitivo. Un grafo costruito sul ponte sarebbe rimasto muto proprio
nella finestra in cui l'operatore guarda. È anche la stessa scelta dell'**arco
G**, che legge un soft-link e non una tabella ponte.

⚠️ **È il primo arco fra due nodi dello stesso tipo** (FATTURA→FATTURA). Il
traversal regge (ha il set dei visitati e il tetto a livello 10), ma un arco
X→X non direbbe una genealogia, direbbe un ciclo: si esclude esplicitamente.

### ⭐ `is_ramo_inverso` vive qui, una volta sola

Prima la lettera `'R'` era scritta a mano in **tre** posti: i due `WHERE` della
summary e il calcolo dentro `fn_documento_lineage`. Aggiungere un secondo ramo
di ritorno voleva dire ricordarsene tre volte — e il posto dimenticato **non
avrebbe dato nessun errore**: solo la nota di credito comparsa come discendente
forward della fattura, cioè una **frontiera diversa su ogni riga di lista**, in
silenzio.

⚠️ **«Inverso» non vuol dire «all'indietro nel tempo»**: la nota di credito nasce
*dopo*. Vuol dire ramo di **ritorno** — nel reso torna la merce, qui torna il
valore — e come il reso non è un avanzamento del flusso.

---

### ⭐ Arco S — Reso → Nota di credito (rev 2026-08-25)

| Arco | Da → A | Card. | Fonte |
|---|---|---|---|
| **S** | Reso → Nota di credito | **1:N** | `resi_righe_accrediti` → `resi_righe` → `resi`, e `commessa_attivita_id` → `attivita_fatturabili.fattura_riga_id` → `fatture_righe` → `fatture` (`DISTINCT`) |

**Il problema che chiude.** Il grafo **si fermava sul reso**: la nota di credito
che lo accredita era già legata alla fattura che rettifica (arco `N`) e alla
commessa (arco `G`), ma **non al reso**. I due rami di ritorno — la merce che
torna e il valore che torna — non si toccavano. Nel drawer del reso l'unica
traccia dell'accredito era `gia_accreditato`, che è una **quantità**, non un
documento.

**Il dato non si inventa: si legge.** `vendite.resi_righe_accrediti` è nata il
2026-08-18 esattamente per reggere questo legame — *«il FATTO, con chi/quando/
quanto/contro cosa»*. Il difetto non era nella scrittura: era che **nessuno la
leggeva**.

⭐ **`S` NON è un ramo di ritorno**, e la decisione è consapevole:
`is_ramo_inverso` resta `arco = ANY (ARRAY['R','N'])`. «Inverso» vuol dire *ramo
di ritorno*, un verso che il grafo forward non deve percorrere; `S` è invece
l'**avanzamento naturale del reso** — la merce è tornata, adesso si accredita —
come `H` è l'avanzamento dell'ordine. La conseguenza è voluta: **il reso smette
di essere una foglia e prende la nota di credito come FRONTIERA**, che è
l'informazione che prima non esisteva da nessuna parte.

⚠️ **Il `WHERE af.fattura_riga_id IS NOT NULL` non è una formalità copiata da
`G`.** Misurato il 2026-08-25: **5 accrediti registrati, 3 con la riga di
fattura** — due resi accreditati e non ancora fatturati non hanno arco, e lo
prenderanno all'emissione.

⛔ **Due strade ovvie che sono sbagliate**, scritte qui perché non vengano
riscoperte:

1. **Scrivere il reso in `commesse_attivita.sorgente_tipo_id/uid`.** Non è un
   campo di provenienza: è la **chiave di raggruppamento della fatturazione**
   (`fn_build_gruppo_fatturabile_key`, letta da dashboard competenza, emissione
   mirata e `fatturazione_lotti_gruppi`). Scriverci il reso sposterebbe la
   rettifica in un altro gruppo, cioè in un altro lotto e in un altro documento.
   Il legame va **letto**, non **trasportato**.
2. **Un dodicesimo arco *reso → fattura originale*** via
   `resi_righe_accrediti.fattura_riga_rettificata_id`, che è a un solo join di
   distanza. Sarebbe **forward** come `S`, quindi fattura originale e nota di
   credito finirebbero allo stesso livello con lo stesso `pipeline_rank` (sono
   entrambe nodi `FATTURA`) e il pareggio si spezzerebbe su `d_uid`, che è
   **testo**: la frontiera del reso diventerebbe un ordinamento lessicografico
   fra `'20024'` e `'835'`. E non serve — **il triangolo si chiude già**:
   `reso —S→ NC ←N— fattura originale`.

⭐ **Il legame è MOLTI-A-MOLTI, di proposito.** Tutte le rettifiche di una
commessa cadono nel gruppo `MAN:<commessa>`, quindi due resi diversi sulla stessa
commessa producono **una sola** nota di credito, che può rettificare righe di
fatture diverse. Un arco calcolato regge un molti-a-molti senza sforzo; un
puntatore memorizzato no — ed è la ragione in più per cui la forma giusta è
l'arco. Volere «una nota per reso» costerebbe la chiave di raggruppamento, non
l'arco.

---

### ⛔ La regola del perimetro RLS — vale per OGNI ramo (rev 2026-08-25)

> **Ogni ramo passa dalle tabelle-testata che portano la RLS. Le tabelle-ponte
> non danno perimetro.**

`commesse_sorgenti`, `attivita_fatturabili`, `resi_righe` e
`resi_righe_accrediti` hanno tutte `relrowsecurity = f`: un ramo che si ferma lì
eredita **zero** perimetro, e produce un arco verso un documento che il chiamante
**non può vedere**.

⚠️ **E la decorazione del nodo non salva**: `vw_documento_lineage_nodi` è in
`LEFT JOIN`, quindi la riga dell'arco resterebbe con `from_codice`/`to_codice` a
`NULL` invece di sparire.

Misurato ramo per ramo contro `pg_class.relrowsecurity` il 2026-08-25: **quattro
archi su dieci erano fuori perimetro** — `B`, `E`, `F` (sorgente **e** commessa,
via `commesse_sorgenti`) e `G` (la commessa, saltata da
`attivita_fatturabili`). Chiusi tutti nello stesso `CREATE OR REPLACE VIEW` di
`S`: cinque join in più, tutti su chiave primaria, **zero righe cambiate** sul
dato di oggi.

⛔ **La chiave dei tre rami `B`/`E`/`F` non è la stessa.**
`commesse_sorgenti.sorgente_uid` è **testo polimorfo** e segue la convenzione
`key_selector`: `p.uid::text` per il preventivo, `o.id::text` per l'ordine,
`c.id::text` per il contratto. Un join scritto con la chiave copiata da un altro
ramo **non darebbe errore**: azzererebbe quel gruppo di archi.

⚠️ **Sul dato di sviluppo non si riproduce** — l'operatore di collaudo vede tutte
e 60 le commesse e tutti e 13 i resi, quindi zero archi fuori perimetro. È un
presidio per il giorno in cui un operatore sarà ristretto a un emittente, ed è
il test **38** del pgTAP (che è generale e non parla di `S`).

⚠️ Quel test vale **solo** perché la suite gira come `zeroerp_app` con la RLS
attiva. Con `PGTAP_RUNNER=owner` sarebbe verde per costruzione: **chi lo sposta
lo spegne.**

---

### ⭐ Arco T — Reso → DDT di ri-consegna (rev 2026-08-28)

| Arco | Da → A | Card. | Fonte |
|---|---|---|---|
| **T** | Reso → DDT di ri-consegna | **1:N** | `resi_righe_riconsegne` → `ddt_righe` → `ddt` |

**Cosa mancava.** Il grafo aveva `R` — la merce che **torna** — e `S` — il valore
che si **accredita** — ma non l'arco che dice che quella merce è **ripartita**. Un
reso ri-consegnato finiva come una **foglia**: il viaggio di ritorno non compariva
da nessuna parte, benché il ponte che lo registra esista dal 2026-07.

⭐ **`T` NON è un ramo di ritorno**, e la ragione è la stessa già scritta per `S`:
«inverso» vuol dire ramo di **ritorno**, un verso che il grafo forward non
percorre. Il ritorno è già avvenuto ed è `R`; da lì in poi il reso ha **due modi
di andare avanti** — accreditare la merce (`S`) o ri-consegnarla (`T`). Nessuno dei
due cammina all'indietro. `is_ramo_inverso` resta quindi `arco = ANY (ARRAY['R','N'])`.

La conseguenza è voluta e gemella di quella di `S`: **il reso smette di essere una
foglia e prende il DDT di ri-consegna come FRONTIERA.**

#### ⭐ La sorgente è il PONTE, non `ddt.sorgente_*`

L'arco si costruisce da `vendite.resi_righe_riconsegne`, l'aggancio duro che
[`fn_genera_ddt_riconsegna`](/dbzero/vendite/funzioni/fn_genera_ddt_riconsegna)
popola per **entrambi** i rami. Due conseguenze, e la seconda ha sorpreso chi
scriveva:

* l'arco copre anche le ri-consegne **order-backed**, che dichiarano
  `ORDINE_VENDITA` e il reso non lo nominerebbero mai;
* **non dipende** dalla revisione che valorizza `ddt.sorgente_tipo_id = RESO_VENDITA`
  sulle sole standalone. Sono **due cose diverse**, non due metà della stessa: quella
  dice *chi è il padre* **sul documento** (il campo «Origine», l'azione «apri
  sorgente»), questa lo fa *comparire* **nel grafo**.

#### ⚠️ Due figli in avanti, e perché il caso è sicuro

Un reso può essere **in parte accreditato e in parte ri-consegnato**, quindi avere
due figli forward. È esattamente il pericolo che la nota dell'arco `S` segnalava —
lì i due figli sarebbero stati **dello stesso tipo** (due nodi FATTURA allo stesso
livello, stesso `pipeline_rank`, e la frontiera decisa sul confronto lessicografico
fra due uid testuali).

Qui i due figli sono di **tipo diverso**, e i ranghi li separano:

| tipo | `pipeline_rank` |
|---|---:|
| `RESO_VENDITA` | 0 |
| `DDT_VENDITA` | **3** |
| `FATTURA` | **5** |

Il pareggio non può verificarsi. ⛔ **È quella differenza a rendere sicuro il caso**:
se un domani non ci fosse più, il difetto tornerebbe silenzioso.

> ⚠️ La risposta arriva dal **rango**, che è struttura. Che oggi *nessun reso abbia
> entrambi i figli* è un fatto datato e non prova niente: zero occorrenze non
> significa che il caso non esiste, significa che non c'è ancora un controesempio.

#### ⚠️ Il perimetro RLS, come per ogni ramo

Il join attraversa `vendite.resi` e `vendite.ddt` — le **testate**, che sono le
tabelle che portano la RLS. Le tre di mezzo (`resi_righe_riconsegne`, `resi_righe`,
`ddt_righe`) hanno `relrowsecurity = f`: un ramo che si fermasse lì produrrebbe un
arco verso un documento che il chiamante non vede, e la decorazione non lo ferma
perché i join ai nodi sono `LEFT`.

⚠️ **`DISTINCT` obbligatorio**: un reso con più righe ri-consegnate nello stesso DDT
produrrebbe un arco per riga.

Piano: `brief-db-ddt-riconsegna-eredita-testata` §9.4.1. Presidio: test **39** del
pgTAP (`T` va da `RESO_VENDITA` a `DDT_VENDITA` ed è un avanzamento).

---

### 🔄 rev 2026-10-05 — tre letture una volta sola

Due rami (preventivo → commessa, ordine → commessa) collegano la commessa al
documento d'origine con una chiave scritta come testo. Con la sicurezza per riga
attiva il database rileggeva **tutta** la tabella dei preventivi, o degli ordini,
per ogni collegamento; e i nodi del grafo si calcolavano due volte. Da
`20261005-21` quelle tre letture si fanno una volta sola: stesse colonne, stesse
righe, la vista da ~380 a ~90 ms (misura come applicazione su dbdev,
2026-10-05). La regola di perimetro qui sopra non cambia: le letture passano
ancora dalle tabelle dei documenti, con i loro permessi.

---

### 🔄 rev 2026-10-11 — la vista è la proiezione di [`fn_documento_lineage_archi`](fn_documento_lineage_archi.md)

Changeset `20261011-66`. Il corpo sta nella funzione, che
si può chiamare **per i soli documenti che servono**; la vista ne è la lettura
«senza seme», con le stesse colonne e gli stessi tipi. Brief:
`brief-db-lineage-seminata-per-chiave` §8.3.

{% include-markdown "signature-core.md" %}
