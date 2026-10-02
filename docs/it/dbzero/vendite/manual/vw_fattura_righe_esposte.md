## 🔍 Documentazione Concettuale – Vista `vendite.vw_fattura_righe_esposte`

> **Versione**: 2026-07-28 (brief-fix-importi-riga-fattura-zero §4.7-bis, D5 ·
> migration `20260728-16`) · rev 2026-10-01: tre modi di esporre un componente
> (brief-db-esposizione-componenti-kit-in-fattura · `20261001-46`)

> **Vedi anche**
>
[vendite.fatture_righe](/dbzero/vendite/tabelle/fatture_righe) — il dettaglio da cui deriva
> [vendite.attivita_fatturabili](/dbzero/vendite/tabelle/attivita_fatturabili) — il livello sotto la riga
> [catalogo.articoli_componenti](/dbzero/catalogo/tabelle/articoli_componenti) — `esposizione_in_fattura`, la regola
> [guida fatturazione](/guide/fatturazione) — §La riga di fattura: aggregazione, importo, esposizione

---

### 🎯 Scopo Principale

Produce **come il documento va rappresentato**, a partire dalle righe che lo
compongono.

⚠️ **Non è «la vista di stampa».** Deve essere letta da **ogni uscita verso
l'esterno**: PDF, XML SDI, portale. Se il PDF mostrasse il kit raggruppato e
l'XML trasmettesse i componenti, avremmo due uscite dello stesso documento che
raccontano dettagli diversi — totali uguali, quindi niente di irregolare, ma una
divergenza che nessuno ha deciso. Chiamarla «di stampa» significherebbe
costruirla già divergente.

Il principio che la governa: **`vendite.fatture_righe` resta il dettaglio** —
tutte le componenti, con articolo, quantità e prezzo propri — e questa vista
produce la **sintesi**. Non esiste un secondo dato da tenere allineato.

---

### Perché una vista e non una tabella

Una tabella materializzata porterebbe tre domande: quando la generi, cosa succede
se la stampa viene rilanciata, cosa se qualcuno tocca le righe dopo. Con la vista
spariscono tutte — fonte unica, nessun momento di generazione, nessuna
idempotenza da garantire. Se un domani il costo lo richiedesse, materializzarla è
banale: la definizione è già qui.

---

### Le tre regole del kit

| Caso | Cosa produce |
|---|---|
| riga **non** di kit (`kit_key IS NULL`) | passa così com'è |
| riga di **kit** | **una riga padre** che porta il totale del kit |
| componenti `NASCOSTO` | **non compaiono**: il loro valore è dentro il totale del padre |
| componenti `DESCRITTIVO` | righe **descrittive** sotto il padre, **senza prezzo né importo**; il valore è dentro il totale del padre |
| componenti `VALORIZZATO` | righe sotto il padre **con quantità, prezzo, sconto e importo suoi**, **fuori** dal totale del padre |

Il modo è `fatture_righe.kit_esposizione`, lo snapshot di
`catalogo.articoli_componenti.esposizione_in_fattura` (rev 2026-10-01,
`20261001-46`; fino a quel giorno era il booleano `kit_esposto_in_fattura`:
`false` → `NASCOSTO`, `true` → `DESCRITTIVO`).

⭐ **Un componente resta sempre legato al suo kit**, anche valorizzato: livello 1,
stessa `kit_key`, stesso `ordinamento` del padre — mai una riga sciolta, come se
fosse stato venduto da solo.

**Il kit senza resto**: se tutti i componenti sono `VALORIZZATO`, la riga padre
resta come **intestazione** con importo e prezzo `NULL` (non zero: zero direbbe
«omaggio»), e i componenti sotto. Con valorizzati e descrittivi insieme, il padre
porta la somma dei descrittivi.

Da cui la proprietà che conta: **il totale del documento non cambia mai al
variare dell'esposizione** — ogni componente sta o nel padre (`NASCOSTO`,
`DESCRITTIVO`) o sulla sua riga (`VALORIZZATO`), mai in tutti e due, mai in
nessuno.

---

### Convenzioni

* **Quantità e UoM della riga padre** (dal 2026-10-02, `20261002-64`) = quelle
  della **riga padre del documento**, congelate su ogni componente alla generazione
  (`fatture_righe.kit_qta`, `kit_uom_id`). Si leggono **componente per componente**
  (le righe dello stesso componente, che la generazione separa anche per prezzo, si
  sommano) e valgono se tutti i componenti dicono lo stesso numero di kit, valorizzati
  compresi: un kit senza resto ha comunque la sua quantità. Se non lo dicono — una
  nota di credito parziale, dove si rende un componente solo — quantità e prezzo
  della riga padre sono `NULL`: il kit lì non ha una quantità, e il caso **non si
  rifiuta**. Fino al 2026-10-01 erano **media** e **max** dei componenti: con
  coefficienti diversi da 1 la media non voleva dire niente (il backend fermava la
  fattura, R10), e in un kit di unità diverse (pezzi, metri, ore) l'unità era una a
  caso.
* **Periodo** (dal 2026-10-02): la riga padre si costruisce anche per
  `competenza_dal`/`competenza_al`, quindi lo stesso kit fatturato su due mesi dà
  **due** righe padre, come un articolo normale. Prima i due periodi finivano nella
  stessa riga, con quantità 1 e prezzo doppio.
* **`riga_nr` della riga padre** = quello del **primo** dei suoi componenti.
* **Importo della riga padre** = **somma** dei componenti **non valorizzati**
  (`NASCOSTO` e `DESCRITTIVO`); `NULL` se non ce ne sono.
* **Prezzo unitario del padre** = derivato, `importo / quantità`. È il prezzo
  *implicito* della riga mostrata, non una lettura dal catalogo: quella può
  essere cambiata dopo l'emissione.
* **Prezzo e importo delle righe descrittive** = `NULL`, non zero. `NULL` dice «questa
  riga non porta importo», zero direbbe «vale zero». Chi somma ottiene comunque
  il totale corretto, perché `SUM` ignora i `NULL`.

---

### Colonne di servizio

| Colonna | A cosa serve |
|---|---|
| `tipo_riga` | `NORMALE` · `KIT_PADRE` · `KIT_COMPONENTE` · `PARTE_PLAFOND` |
| `ordinamento` | il `riga_nr` del capogruppo: tiene i componenti insieme al proprio padre, e le parti insieme alla propria capofila |
| `livello` | `0` padre, riga normale **o parte di plafond**; `1` componente del kit (descrittivo **o valorizzato**) |
| `fatture_righe_id` | la riga sottostante; **`NULL`** sulla riga padre, che è sintetizzata e non esiste come record |
| `riga_capofila_id` | *(dal 2026-08-31)* la capofila di una riga spezzata dal plafond; vuoto su tutte le altre |
| `esposizione` | *(dal 2026-10-01, in coda)* il modo del componente (`DESCRITTIVO` \| `VALORIZZATO`) sulle righe `KIT_COMPONENTE`; `NULL` altrove |
| `competenza_dal`, `competenza_al` | *(dal 2026-10-02, in coda)* il periodo della riga, su ogni riga; sulla riga padre quello del suo gruppo |
| `ha_periodo` | *(dal 2026-10-02, in coda)* `competenza_dal <> competenza_al`: la riga ha un **periodo** da stampare. È la regola unica per PDF, SDI (`DataInizioPeriodo`/`DataFinePeriodo`) e portale; una riga puntuale (`dal = al`) non stampa nulla |
| `kit_riga_nr` | *(dal 2026-10-01, in coda)* il `riga_nr` della riga del kit a cui la riga appartiene, su `KIT_PADRE` e `KIT_COMPONENTE`; `NULL` sulle righe sciolte. È il legame che il tracciato SDI, a linee piatte, dovrà dichiarare: oggi coincide con `ordinamento`, ma `ordinamento` è un ordine, non un riferimento |

⚠️ **Chi somma gli importi somma tutte le righe con importo valorizzato**, a
qualunque livello: dal 2026-10-01 il livello 1 **non** significa più «senza
importo» (un componente valorizzato ha il suo).

Ordinamento canonico: `ORDER BY ordinamento, livello, riga_nr`.

---

### La quarta regola: la riga spezzata dal plafond

(dal 2026-08-31)

Quando il plafond di una dichiarazione d'intento copre solo una parte di una
riga, quella riga diventa **due righe di fattura** — è un obbligo del formato
elettronico, che ammette una sola aliquota e una sola natura per linea.

Qui le due parti escono **entrambe, ognuna con il proprio importo**, allo
**stesso livello**, con lo **stesso `ordinamento`** (quello della capofila) e con
`tipo_riga` = `PARTE_PLAFOND` sulla seconda.

⛔ **Non è il trattamento del kit, e la differenza è sostanziale.** Il kit
*somma* le sue righe non valorizzate in una sola: farlo qui produrrebbe una linea sola nel file
elettronico, cioè cancellerebbe esattamente la ragione per cui la riga si è
spezzata.

⛔ **E la parte non scende a `livello 1`.** In questa vista `livello 1` significa
*«componente sotto il suo kit»*: la parte staccata dal plafond non è un
componente, è la stessa riga divisa in due, e sta allo stesso livello della
capofila. (Fino al 2026-10-01 `livello 1` voleva dire anche *«senza importo»*, e
chi saltava il livello 1 avrebbe perso il valore della parte; dal 2026-10-01 un
componente valorizzato a livello 1 un importo ce l'ha, e quella lettura non è più
lecita per nessuno.)

⭐ L'`ordinamento` condiviso è ciò che tiene le due parti **adiacenti** anche
quando fra loro finisce un'altra riga dello stesso articolo a prezzo diverso.
Senza, l'operatore leggerebbe due righe con quantità strane in punti diversi del
documento, e niente direbbe che vengono dalla stessa origine.

📌 **Limite dichiarato.** Una riga che è insieme componente di kit *e* parte di
plafond finisce nei rami del kit, non in questo. Non è un buco — il
raggruppamento del kit tiene già conto dell'IVA, quindi due trattamenti diversi
producono due righe padre distinte, che è l'esito corretto — ma lì le due parti
non si vedono come una sola origine. Il caso non è stato costruito perché oggi
il backend non spezza i componenti di kit.

---

### ⚠️ Raggruppamento per IVA

La riga padre è costruita per **(fattura, kit, IVA, billing account
destinatario)** e non per solo (fattura, kit). Se un kit avesse componenti con
aliquote diverse, una riga padre sola non potrebbe rappresentarle e falserebbe il
riepilogo IVA: così se ne ottengono due, che è l'esito corretto. Alla data il
caso non si presenta.

Stessa logica per articolo e descrizione del padre: stanno nel `GROUP BY` e non
in un aggregato. Se per qualche ragione divergessero si otterrebbero due righe
padre invece di una fusione silenziosa — degradazione sicura.

---

### Ruolo nel sistema

È il **contratto verso l'esterno** del documento. Chi produce un'uscita — stampa,
tracciato fiscale, portale cliente — legge questa vista e non `fatture_righe`:
leggere le righe direttamente significa ignorare l'esposizione dei kit e
produrre un documento diverso da quello che gli altri canali mostrano.

---

<!-- rev-2026-09-28-liste-righe -->
### 🔄 rev 2026-09-28 — brief-db-liste-righe-documento

Il CTE `kit` è `NOT MATERIALIZED` (`20260928-43`): letto da due rami, era materializzato e si calcolava su **tutte** le fatture a ogni lettura, senza che il filtro per fattura ci entrasse. Ora il filtro scende fino alle righe (dev, fattura con kit: da 4,8 a 1,75 ms, fatto datato). Righe identiche. ⚠️ Nel ramo dei componenti l'aggregato si rivaluta per componente, sulle sole righe della fattura. La lista delle righe per il drawer è [vw_fattura_righe_lista](/dbzero/vendite/views/vw_fattura_righe_lista), che legge questa vista senza ricalcolarla. ⚠️ Nota di lettura: «`riga_nr` NON cambia» nel COMMENT vuol dire che ogni riga conserva il suo numero di linea; le due parti di una riga spezzata dal plafond hanno numeri diversi (indice unico) e condividono solo `ordinamento`.
