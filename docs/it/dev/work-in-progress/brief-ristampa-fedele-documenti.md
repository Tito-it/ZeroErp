# Brief — la ristampa fedele: riprodurre un documento com'era

> **Chi scrive:** team DB (`dev/db-tid`), 2026-08-03.
> **A chi:** BE e FE. ⚠️ **Il lavoro è quasi tutto loro**: lato DB non c'è niente
> da costruire, e §4 spiega perché — è un'informazione, non una scusa.
> **Cos'è:** manca il percorso che ri-produce un documento **come fu emesso**,
> usando la versione di template con cui nacque e il contesto congelato allora.
> Il modello lo prevede e ne conserva tutti gli ingredienti; nessun codice li usa.
> **Stato:** analisi misurata, **nessuna riga scritta**. Serve una decisione su
> §8 prima di aprire il cantiere.

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

### 5.3 DB — niente da costruire (vedi §4)

Resta a carico del DB solo l'eventuale seguito di §8.1, se la decisione sulla
conservazione dei file comportasse un intervento sui dati.

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

---

## 7. Cosa **non** si chiede

| Cosa | Perché no |
|---|---|
| Rigenerare i file mancanti per i 135 documenti | Sarebbero file **nuovi** spacciati per originali. Se il file non c'è, la verità è che non c'è |
| Correggere la chiave vecchia nella v1 del template | È **storia coerente**: la v1 va con il contesto di allora, che ha quella chiave. Correggerla romperebbe la ristampa fedele invece di aiutarla |
| Toccare `genera_documento` nel merito | Fa bene il suo mestiere: emette. Va solo chiamato col suo nome |
| Nuovi invarianti lato DB | Ci sono già tutti (§4) |

---

## 8. Decisioni aperte

1. **Si conservano i file per tutti i documenti?** Oggi 18 su 153. Se la risposta
   è sì, il percorso 1 diventa la strada normale e il 3 la rete di sicurezza; se
   è no, il 3 diventa la strada principale e va progettato per reggere il carico.
   È una scelta di **politica di conservazione**, non di implementazione.
2. **Che si fa se il `pdf_hash` non combacia?** Un renderer può non essere
   deterministico fra versioni della libreria (font, metadati, data di
   produzione). Le due strade sono: dichiarare la ristampa «fedele nel
   contenuto, non nei byte» e confrontare il solo `context_hash`, oppure pinnare
   anche la versione del motore. La prima è onesta e a costo zero; la seconda è
   più forte e più cara.
3. **La ristampa fedele lascia traccia?** Un evento sul documento esistente è
   utile per l'audit e non viola §5.1.4 — ma va deciso, perché è l'unica
   scrittura che questo percorso farebbe.

---

## 9. Nota di metodo

Il buco non è stato trovato leggendo il codice: è stato trovato da una **domanda
di dominio** di Tid su un modello che a video sembrava funzionare. La verifica
tecnica da sola aveva concluso «è solo un problema di documentazione», e per il
perimetro che stava guardando era vero. La domanda ha spostato il perimetro.

È la stessa coppia che aveva fatto emergere il cantiere emittente — un controllo
automatico più una domanda sul modello — e in entrambi i casi **nessuno dei due
da solo bastava**.
