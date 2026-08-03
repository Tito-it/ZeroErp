# Brief — la ristampa fedele: riprodurre un documento com'era

> **Chi scrive:** team DB (`dev/db-tid`), 2026-08-03.
> **A chi:** BE e FE. ⚠️ **Il lavoro è quasi tutto loro**: lato DB non c'è niente
> da costruire, e §4 spiega perché — è un'informazione, non una scusa.
> **Cos'è:** manca il percorso che ri-produce un documento **come fu emesso**,
> usando la versione di template con cui nacque e il contesto congelato allora.
> Il modello lo prevede e ne conserva tutti gli ingredienti; nessun codice li usa.
> **Stato:** ✅ **CHIUSO il 2026-08-03**, tutto nella stessa giornata: analisi
> del DB al mattino, tre decisioni di §8 prese da Tid, esecuzione BE/FE, e
> l'unica voce tornata al DB — `RISTAMPA_FEDELE` nel vocabolario eventi —
> applicata con `20260803-05`. Brief figlio, chiuso:
> [brief-db-evento-ristampa-fedele.md](brief-db-evento-ristampa-fedele.md).
>
> Definizione di «fatto» (§6): i punti **2 e 3 sono chiusi e presidiati dai
> test**; **1 e 4** sono verifiche a video sul documento vero — il caso
> dell'offerta di maggio resta il modo migliore per esercitarle alla prima
> occasione utile. Non bloccano: il percorso è coperto dal lato del codice
> (nessun `context_builder` invocato, versione pinnata anche OBSOLETA), e
> quello che il PDF aggiungerebbe è la controprova sul dato reale.
>
> Dettaglio dell'esecuzione nella sezione qui sotto.

---

## ✅ Stato di esecuzione — 2026-08-03 (scrive il BE/FE)

Le tre decisioni di §8 sono state prese da Tid e il cantiere è stato eseguito
nella stessa giornata. La previsione del brief si è rivelata esatta: **è stato
corto perché il pezzo difficile c'era già** — `render_pdf(*, template_versione,
context)` aveva davvero la firma giusta (§5.1.2), e nessun motore nuovo è stato
scritto.

### Le decisioni prese

| § | Domanda | Decisione di Tid |
| --- | --- | --- |
| 8.1 | Si conservano i file per tutti? | **Sì.** Il 18-su-153 non è una politica di conservazione: è una **cancellazione errata dei riferimenti** (le 135 righe-indice rimosse il 2026-07-21; i PDF su storage erano intatti). Siamo in test. ➡️ Il percorso 1 resta la strada normale, il 3 la rete di sicurezza — **non va dimensionato per il carico** |
| 8.2 | Che si fa se il `pdf_hash` non combacia? | **Soluzione 1**: «fedele nel contenuto, non nei byte», dichiarato. Niente pinning del motore di render (più forte ma molto più caro) |
| 8.3 | La ristampa lascia traccia? | **Sì** — evento sul documento esistente. È l'unica scrittura del percorso, e non viola §5.1.4 |

### Cosa è stato fatto

**BE** — `DocumentGenerationService.ristampa_fedele(user, documento_id)`:

- legge lo **snapshot congelato** con una lettura dedicata
  (`get_documento_generato_snapshot`: testata + `context_json`, separata dalle
  altre perché il contesto può essere grande e serve solo qui);
- carica la **versione pinnata** con `get_versione_by_id`, che **non filtra per
  stato** — una versione `OBSOLETA` è il caso normale della ristampa fedele, non
  l'eccezione;
- **non invoca alcun context_builder**: il contesto si legge, non si ricostruisce;
- non persiste nulla (§5.1.4 rispettato): l'unica scrittura è l'evento;
- endpoint `GET .../documenti/<documento_id>/ristampa/` dalla **factory
  condivisa**, quindi cablato in un colpo su **tutti e 6** i domini sorgente —
  con un test di presidio che fallisce se un dominio resta indietro;
- il verdetto di fedeltà viaggia nell'header `X-Ristampa-Pdf-Hash-Match`
  (`1`/`0`), perché il corpo della risposta è il PDF.

**§5.1.5 fatto**: il commento di `DocumentoGenera` non dice più «ristampa» —
dice che emette un documento nuovo, e spiega perché il vecchio nome ingannava.

**FE** — le tre azioni sono ora distinte (§5.2):

- «**Scarica originale**» — disabilitata **con la ragione** sui documenti senza
  file, invece di fallire con un `E_NOT_FOUND` generico. Per saperlo serviva un
  dato che la lista non esponeva: aggiunto `has_file_principale` alla proiezione;
- «**Ristampa fedele**» — nuova, con toast di successo se i byte coincidono e di
  **warning** se no («fedele nel contenuto»): entrambi sono esiti positivi;
- «**Genera nuovo documento**» — tolta dal menu di un documento già generato:
  è un'azione della **sorgente**, non del documento, e tenerla lì era metà della
  confusione. Aggiunta anche una colonna *Originale* alla lista, per vedere a
  colpo d'occhio quali documenti hanno il file.

**Test**: 15 sul service + 3 sull'endpoint + 2 di presidio del routing. Quelli
che contano davvero sono i primi tre: presidiano **chi viene chiamato e con
cosa** (versione pinnata sì, `get_versione_pubblicata_attiva` no, nessun
builder), perché è l'unica cosa che distingue una ristampa fedele da un
documento nuovo travestito da vecchio — e guardando il PDF prodotto non si vede.

Suite completa **3485 verdi**, build + lint + i18n puliti.

### Cosa resta

1. 🔴 **La riga al DB** — vedi §5.3 riscritto.
2. ⏳ **La validazione in-app di Tid** sul caso di prova di §6.4: l'offerta di
   maggio deve uscire con la v1 e la chiave `emittente_fiscale.descrizione`.
   È l'unica verifica che il codice non può dare da sé.

Doc dell'API: `docs/it/backend/documenti/manual/api_ristampa_fedele.md`.

---

## 0. Da dove nasce

Dalla domanda di Tid (2026-08-03), durante la verifica della rinomina
dell'alias emittente:

> «se si esegue la ristampa non viene riprodotto il documento originale? il
> modello prevedeva le versioni per fare in modo che fosse riproducibile sempre
> una stampa con quella versione. Nel 2025 avevo un modello, nel 2026 uno nuovo:
> se rifaccio quello del 2025 deve sempre uscire quel modello.»

La verifica dice che **la promessa è giusta e il modello è costruito per
mantenerla — ma oggi nessun percorso la mantiene**.

---

## 1. La promessa, e la prova che è mantenibile

Ogni riga di `documenti.documenti_generati` conserva tutto ciò che serve a
rifare il documento identico:

| Cosa | Copertura misurata |
|---|---|
| `template_versione_id` — la versione **con cui fu stampato** | 153 su 153 |
| `context_json` — i **dati** con cui fu stampato | 153 su 153 |
| `context_hash` · `template_hash` · `pdf_hash` | 153 · 153 · 153 |

🔑 **La prova che i due pezzi combaciano** non è teorica. Un'offerta di maggio
porta questo contesto congelato:

```
doc 22 del 2026-05-28 (template v1) -> chiavi emittente: id, codice, descrizione
```

`descrizione` è esattamente la chiave che la **v1** del template usa
(`offerta.emittente_fiscale.descrizione`). Nel frattempo quel nome è cambiato in
`ragione_sociale` (cantiere emittente, 2026-08-03) e la **v2** usa il nome
nuovo. **Snapshot e versione pinnata sono coerenti fra loro**: renderizzare il
doc 22 con la sua v1 e il suo `context_json` riprodurrebbe l'originale, chiave
vecchia inclusa — mentre ricostruire il contesto oggi produrrebbe un segnaposto.

➡️ Ne discende la **regola portante** di tutto questo brief: la ristampa fedele
usa il contesto **congelato**, mai uno ricostruito. Un contesto ricostruito è un
documento nuovo travestito da vecchio.

---

## 2. Cosa succede oggi — i due percorsi esistenti

### 2.1 `download_documento` — fedele, ma solo se il file c'è

Serve il **file già prodotto** (`documenti_generati_file`): riproduzione byte per
byte, nessun render. È il percorso corretto quando è disponibile.

⚠️ **La persistenza del file è iniziata il 2026-07-21.** Prima di quella data
nessun documento ha il file, e il download risponde `E_NOT_FOUND`.

| Template | generati | con file |
|---|---|---|
| Preventivo | 111 | 5 |
| Ordini vendita | 12 | 4 |
| Fattura | 10 | 6 |
| DDT vendita | 10 | 2 |
| Contratto | 5 | 1 |
| OffertaComm | 5 | **0** |
| **totale** | **153** | **18** |

**135 documenti su 153 non sono oggi riproducibili in alcun modo.**

### 2.2 L'endpoint chiamato «ristampa» — che ristampa non è

`sorgente_documenti_views.py` commenta il proprio POST come «Genera e persiste un
documento PDF dalla sorgente (**ristampa**/archivio)», ma chiama
`genera_documento`, che:

* risolve `_resolve_versione_pubblicata(template_id)` — la versione **pubblicata
  oggi**, non quella di allora;
* ricostruisce il contesto **dai dati correnti**;
* crea un **record nuovo** in `documenti_generati` con un nuovo evento `GENERATO`.

Per un documento del 2025 uscirebbe il modello del 2026 con i dati di oggi:
**esattamente ciò che non deve succedere**. Non è un difetto di quel codice — fa
bene il suo mestiere, che è emettere — è il **nome** a mentire, ed è il nome che
fa credere al chiamante di avere una ristampa.

---

## 3. Il buco: manca il terzo percorso

| # | Percorso | Esiste? |
|---|---|---|
| 1 | Scarica il file originale | ✅ ma solo per 18/153 |
| 2 | Emetti un documento nuovo | ✅ (oggi si chiama «ristampa») |
| 3 | **Rirenderizza l'originale** dalla versione pinnata + contesto congelato | ❌ |

Il terzo è l'unico che mantiene la promessa per i 135 documenti senza file, ed è
anche l'unico modo di verificare che un file salvato sia davvero quello giusto
(confronto con `pdf_hash`).

---

## 4. Perché lato DB non c'è niente da costruire

Non è una delega: è il risultato della verifica. **Gli invarianti su cui la
promessa si regge sono già imposti dal database**, e già presidiati da pgTAP.

| Invariante | Come è imposto |
|---|---|
| Lo snapshot non si riscrive | `trgfn_documenti_generati_protect_snapshot` blocca l'UPDATE di `context_json`, `context_hash`, `template_versione_id`, `template_hash`, `pdf_hash` e delle colonne d'identità |
| Un documento generato non si cancella | `trg_documenti_generati_a10_block_delete_dlt` |
| Una versione **pubblicata** non si modifica | `trg_template_documenti_versioni_a10_protect_pubblicata_upd` |
| Una versione referenziata non si cancella | `trg_template_documenti_versioni_a10_block_delete_protected_dlt` + il guard su `documenti_generati` |
| Il tutto è presidiato | `db/pgtap/documenti/test-documenti-generati.sql`, test **7** (UPDATE `context_json` bloccato) e **8** (UPDATE `template_versione_id` bloccato) |

➡️ **La riproducibilità è già garantita dal modello: manca solo chi la esercita.**
Se durante il cantiere emergesse un invariante scoperto, quello sì tornerebbe al
DB — ma allo stato della misura non ce n'è.

> **Verificato a cantiere fatto (2026-08-03):** nessun invariante scoperto è
> emerso — questa sezione ha retto per intero. L'unica voce tornata al DB
> **non è un invariante** ma un **valore di vocabolario** (`RISTAMPA_FEDELE` nel
> CHECK degli eventi), conseguenza della decisione §8.3 presa dopo che questa
> analisi era stata scritta. Il titolo di questa sezione resta vero nel merito;
> il conto aggiornato è in §5.3.

---

## 5. Le attività, per competenza

### 5.1 BE — il percorso 3 (owner BE, è il grosso)

| # | Attività |
|---|---|
| 5.1.1 | **Servizio `ristampa_fedele(documento_id)`**: legge la riga di `documenti_generati`, carica **la versione pinnata** (`template_versione_id`, anche se `OBSOLETA`) e il **`context_json` congelato**, e chiama il render |
| 5.1.2 | ✅ **Nessun motore nuovo**: `render_service.render_pdf(*, template_versione, context)` ha **già la firma giusta** — prende una versione e un contesto e non se li costruisce. È il pezzo che rende questo cantiere piccolo |
| 5.1.3 | **Verifica di fedeltà**: confrontare il `pdf_hash` del risultato con quello salvato. Se differiscono, **non** è una ristampa fedele e va detto invece che nascosto (un PDF può non essere deterministico: vedi §8.2) |
| 5.1.4 | 🔴 **NON creare un nuovo `documenti_generati`.** La ristampa fedele non è un'emissione: non consuma progressivo, non cambia lo stato della sorgente. Al più registra un **evento** sul documento esistente |
| 5.1.5 | **Rinominare ciò che mente**: il POST di `sorgente_documenti_views` non è una ristampa. Chiamarlo per quello che fa (emissione / nuovo documento) è metà del difetto risolto |

### 5.2 FE — tre azioni che oggi sono confuse (owner FE)

| # | Attività |
|---|---|
| 5.2.1 | Distinguere a video **«Scarica originale»** (percorso 1), **«Ristampa fedele»** (percorso 3) e **«Genera nuovo documento»** (percorso 2). Sono tre cose diverse e oggi la terza si presenta come la prima |
| 5.2.2 | Sui 135 documenti senza file, «Scarica originale» non è disponibile: l'azione va **disabilitata con la ragione**, non lasciata a fallire con un `E_NOT_FOUND` generico |
| 5.2.3 | «Genera nuovo documento» va presentata come un'azione che **produce un documento diverso**, perché lo è |

### 5.3 DB — una riga, emersa dalla decisione §8.3 — ✅ FATTA

> **Aggiornato il 2026-08-03 dal BE/FE.** La §4 resta corretta — gli
> **invarianti** erano e sono tutti già a posto, non c'è niente da costruire lì.
> Quello che è emerso non viene dagli invarianti ma dalla **decisione 8.3**
> («la ristampa lascia traccia»): il valore che serve non esiste nel vocabolario.

✅ **`RISTAMPA_FEDELE` aggiunto al CHECK
`chk_documenti_generati_eventi_evento_tipo`** — applicato dal team DB in
giornata (`20260803-05`), insieme al `COMMENT ON COLUMN` e a un pgTAP che
asserisce il valore nuovo **ammesso con esito `WARN`**. Era chiuso a quattro
valori (`GENERATO`, `SCARICATO`, `STORAGE_ORPHAN`, `ALLEGATO_AGGIUNTO`, da
`20260603-04`). Brief con SQL e verifica, ora chiuso:
[brief-db-evento-ristampa-fedele.md](brief-db-evento-ristampa-fedele.md).

**Non riusiamo `GENERATO`**: sarebbe esattamente la confusione che questo brief
smonta — una ristampa non è un'emissione, e un audit che le mescola non permette
più di distinguerle guardando la timeline.

Su `esito` **non serve nulla**: la ristampa usa `WARN` quando i byte non
coincidono (decisione §8.2), e `WARN` è già nel CHECK `..._esito`
(`OK`/`KO`/`WARN`) con esattamente quel significato.

ℹ️ **Nella finestra fra la consegna BE/FE e l'apply il cantiere ha funzionato
lo stesso**, ed è per disegno: l'INSERT dell'evento è best-effort in
transazione separata — stesso pattern del `SCARICATO` del download — quindi il
CHECK lo rifiutava, il servizio loggava
`documenti.ristampa_fedele.evento_fallito` e il PDF usciva comunque. Era però
un rosso visibile solo nei log, e quelli si smettono di guardare: il motivo per
cui la riga non andava rimandata. **Dall'apply la traccia c'è davvero.**

**Niente seguito su §8.1**: la decisione è «sì, si conservano», e il 18-su-153
si è rivelato una cancellazione errata dei riferimenti in ambiente di test — non
una politica da implementare né dati da correggere.

---

## 6. Definizione di «fatto»

1. Preso un documento **anteriore al 2026-07-21** (nessun file salvato), la
   ristampa fedele produce un PDF **con il template di allora**;
2. su un documento **con** file salvato, il `pdf_hash` della ristampa **coincide**
   con quello registrato — e se non coincide il sistema lo dice;
3. la ristampa fedele **non** aggiunge righe a `documenti_generati`;
4. il caso di prova che chiude il cerchio è l'**offerta di maggio**: deve uscire
   con la v1 del template e la chiave `emittente_fiscale.descrizione`, cioè
   **diversa** da quella che uscirebbe emettendola oggi. Se esce uguale a quella
   di oggi, il percorso sta ricostruendo il contesto invece di leggerlo.

> **Stato al 2026-08-03** (scrive il BE/FE). I punti **2 e 3 sono chiusi e
> presidiati dai test**: il confronto degli hash è dichiarato nella risposta
> (`X-Ristampa-Pdf-Hash-Match`) e la non-persistenza è verificata
> (`create_documento_generato` / `next_progressivo_sorgente` mai chiamati).
> I punti **1 e 4 richiedono l'app**: sono la validazione di Tid, e il 4 è
> quello che conta — se l'offerta di maggio uscisse uguale a quella di oggi, il
> percorso starebbe ricostruendo il contesto invece di leggerlo. I test lo
> escludono dal lato del codice (nessun `context_builder` invocato), ma la
> controprova sul documento vero la dà solo il PDF.

---

## 7. Cosa **non** si chiede

| Cosa | Perché no |
|---|---|
| Rigenerare i file mancanti per i 135 documenti | Sarebbero file **nuovi** spacciati per originali. Se il file non c'è, la verità è che non c'è |
| Correggere la chiave vecchia nella v1 del template | È **storia coerente**: la v1 va con il contesto di allora, che ha quella chiave. Correggerla romperebbe la ristampa fedele invece di aiutarla |
| Toccare `genera_documento` nel merito | Fa bene il suo mestiere: emette. Va solo chiamato col suo nome |
| Nuovi invarianti lato DB | Ci sono già tutti (§4) |

---

## 8. Decisioni ~~aperte~~ — ✅ PRESE DA TID il 2026-08-03

> Le tre risposte sono nel riquadro di stato in testa al documento. Restano qui
> le domande com'erano poste, perché la formulazione spiega **perché** ognuna
> era una decisione e non un dettaglio implementativo.

1. **Si conservano i file per tutti i documenti?** Oggi 18 su 153. Se la risposta
   è sì, il percorso 1 diventa la strada normale e il 3 la rete di sicurezza; se
   è no, il 3 diventa la strada principale e va progettato per reggere il carico.
   È una scelta di **politica di conservazione**, non di implementazione.
   ➡️ **SÌ.** E con una precisazione che cambia la lettura del dato: il 18 su
   153 **non fotografa una politica**, fotografa una cancellazione errata dei
   riferimenti in ambiente di test (i PDF su storage erano intatti). Il numero
   non era una scelta di conservazione mai fatta — era un incidente.
2. **Che si fa se il `pdf_hash` non combacia?** Un renderer può non essere
   deterministico fra versioni della libreria (font, metadati, data di
   produzione). Le due strade sono: dichiarare la ristampa «fedele nel
   contenuto, non nei byte» e confrontare il solo `context_hash`, oppure pinnare
   anche la versione del motore. La prima è onesta e a costo zero; la seconda è
   più forte e più cara.
   ➡️ **Prima strada.** Il verdetto non è nascosto: viaggia nell'header
   `X-Ristampa-Pdf-Hash-Match` e il FE lo traduce in successo o warning —
   **entrambi esiti positivi**. Il `template_hash` viene confrontato in aggiunta:
   se diverge, la versione è stata toccata dopo la generazione (possibile solo
   su BOZZA) e anche questo è dichiarato.
3. **La ristampa fedele lascia traccia?** Un evento sul documento esistente è
   utile per l'audit e non viola §5.1.4 — ma va deciso, perché è l'unica
   scrittura che questo percorso farebbe.
   ➡️ **SÌ**, evento `RISTAMPA_FEDELE` (`OK` / `WARN`) col dettaglio di fedeltà.
   È la decisione che ha fatto emergere l'unica voce rimasta al DB: quel valore
   non è nel CHECK del vocabolario eventi (§5.3).

---

## 9. Nota di metodo

Il buco non è stato trovato leggendo il codice: è stato trovato da una **domanda
di dominio** di Tid su un modello che a video sembrava funzionare. La verifica
tecnica da sola aveva concluso «è solo un problema di documentazione», e per il
perimetro che stava guardando era vero. La domanda ha spostato il perimetro.

È la stessa coppia che aveva fatto emergere il cantiere emittente — un controllo
automatico più una domanda sul modello — e in entrambi i casi **nessuno dei due
da solo bastava**.
