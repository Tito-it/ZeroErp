# Piano — Residui di orchestrazione e cruscotti vendite

> ## ✅ CHIUSO — 2026-08-09
>
> **Tutti i residui che questo piano tracciava sono stati eseguiti nella stessa giornata in
> cui è stato scritto**: R-1 (BB fan-out + esito parziale del pull, residuo `commessa_cache`
> compreso), R-2 (capitolo guida DDT/resi + correzione della §2.1 che diceva il falso), R-4
> (la voce `scrollable` **ritirata**: non era un residuo — §4.1).
>
> 👉 **L'unica cosa ancora aperta è la validazione in-app**, e vive in
> [brief-be-fan-out-isolato-e-esito-parziale.md](brief-be-fan-out-isolato-e-esito-parziale.md) **§13**,
> che dal 2026-08-09 è il **raccoglitore vivo** dell'intera linea (R-1 + R-3 insieme).
> Questo piano resta come **registro di cosa era aperto e perché**, non come cosa da fare.
>
> ---
>
> **Tipo**: piano esecutivo dei **soli residui** · **Data**: 2026-08-09 · **Owner**: Tid
>
> **Origine**: riallineamento (2026-08-09) di due doc WIP che descrivevano uno stato
> superato dai fatti:
>
> - [analisi-orchestrazione-vendite-simmetrie.md](analisi-orchestrazione-vendite-simmetrie.md)
>   — 2 temi su 3 eseguiti (gap `tipo_doc_fiscale` chiuso, `fn_available_actions_lotto`
>   fatta); resta il §B.
> - [brief-design-fatturazione-due-lenti.md](brief-design-fatturazione-due-lenti.md)
>   — costruzione completata e committata; restano la validazione in-app di 3-ter e un
>   capitolo di guida.
>
> **Perché un doc a sé**: i due brief di provenienza restano le fonti di verità del
> *disegno* (decisioni DL-1..28, conclusioni A/B/C). Questo raccoglie **cosa manca**, con
> l'approfondimento necessario a partire senza rileggerli. Nessuna azione parte da qui
> senza ok di Tid; le voci DB, se emergessero, vanno a brief per il team DB.

---

## 0. Quadro dei residui

| # | Residuo | Tipo | Chi | Blocca? | Stima |
|---|---|---|---|---|---|
| **R-1** | BB fan-out isolato **+ fix esito parziale del pull** | refactor BE + fix | ✅ **ESEGUITO 2026-08-09** — resta validazione in-app + commit (Tid) | no | fatto |
| **R-2** | Guida cruscotti — capitolo DDT/resi/coda accrediti | doc funzionale | agent | no | piccola-media |
| **R-3** | Validazione in-app di 3-ter | verifica | **Tid** | sì per chiudere il due-lenti | — |
| **R-4** | Rinviati con motivazione (1 voce; la 2ª **ritirata**) | minori | — | no | — |

Fuori perimetro ma **collegati**: §5.

---

## 1. R-1 — Il BB di fan-out isolato

**Fonte**: [analisi-orchestrazione-vendite-simmetrie.md](analisi-orchestrazione-vendite-simmetrie.md) §B + §B.1.

> ✅ **Ok Tid 2026-08-09**: si fa il BB, **e** si sistema il pull perché si comporti
> correttamente sul rifiuto parziale (§1.2 D-2, ora **decisa**).
> 👉 Il **brief esecutivo** con il piano di sviluppo è
> [brief-be-fan-out-isolato-e-esito-parziale.md](brief-be-fan-out-isolato-e-esito-parziale.md).
> Quel doc è la fonte operativa; questo resta il quadro dei residui.

### 1.1 Il fatto

Due processi riscrivono a mano la stessa forma — *scopri item → per ognuno isola l'errore →
aggrega gli esiti → logga il run*:

| Fase | `sorgenti → commessa` | `commessa → AF` |
|---|---|---|
| dove | `commesse_push_orchestrator.py` `_run_locked` | `pipeline_step_executor.py` `_handle_pull_attivita_da_commessa_task` |
| discovery | `_resolve_handlers(source_types)` | `commesse_repository.list_commesse_emittibili(...)` |
| isolamento | `try/except` → `HandlerResult` con `errors[]` | `transaction.atomic()` per item + `try/except` → `errors[]` |
| aggregazione | `_compute_stato(results)` → ALL_OK / PARTIAL / … | `if errors and len(errors) == len(commessa_ids): raise` |
| log del run | `PUSH_STARTED`/`PUSH_COMPLETED` + `log_push_run` | `event_log` + `PipelineErrorLogger.log_error` per item |

Verificato ancora vero al 2026-08-09: in `apps/core/services/` non esiste nessun
`run_fan_out`.

> ⚠️ **Ricognizione 2026-08-09 — l'accoppiamento originale era al livello sbagliato.**
> Leggendo il codice per scrivere il brief è emerso che i siti non sono due ma **tre**, e
> che i due della tabella qui sopra **non sono lo stesso livello**:
>
> | Sito | Cos'è | Savepoint per item? |
> |---|---|---|
> | **A** — `_run_locked` | itera sugli **handler** e ne aggrega i report. Ogni handler è *a sua volta* un fan-out | **No**, solo `try/except` |
> | **B** — `BaseSourceHandler._process_rows` | itera sulle **righe** scoperte da `fetch_pushable_rows`: savepoint per riga, contatori `created/updated/skipped` + `errors[]`, poi una **coda batch** fuori dal ciclo | **Sì** |
> | **C** — `_handle_pull_attivita_da_commessa_task` | itera sulle **commesse**: savepoint per commessa, `errors[]` | **Sì** |
>
> Il gemello strutturale di **C** è **B**, non A. A sta un livello sopra: è un
> *aggregatore di fan-out*, e infatti non isola in transazione (lo fanno gli handler
> dentro di sé). Il brief tiene conto di questa correzione — vedi §2 del brief.
>
> **Il fatto più utile emerso**: il vocabolario a tre stati che serve al pull **esiste già
> nel push**. `_compute_stato` restituisce `COMPLETATO` / `PARZIALE` / `ERRORE` da anni. Il
> BB quindi non inventa nessuna policy nuova: **porta al pull la terza parola che il push
> ha già** e che al pull manca.

### 1.2 Le tre decisioni da prendere PRIMA di scrivere codice — ✅ tutte chiuse (2026-08-09)

Questo era il motivo per cui R-1 non era «estrai una funzione e via». Le tre decisioni sono
state prese con Tid il 2026-08-09:

| # | Scelta |
|---|---|
| **D-1** | **Due astrazioni distinte** — `run_fan_out` (lista effimera) e `QueueDrainEngine` (coda durevole), con il confine **scritto in entrambi i file** |
| **D-2** | **Il pull si sistema**: rifiuto parziale → `TaskEsitoParziale` |
| **D-3** | **Run logger dentro il BB**, come protocollo minimo opzionale (start / item_failed / end) |

**D-1 — Convergenza col drain engine della coda.**
`apps/core/services/coda_lavori/drain_engine.py` (`QueueDrainEngine`, luglio 2026) è già
*«claim → per-item best-effort → tally → retry con backoff»*, costruito una volta e
parametrizzato da un `QueueBackend` + una callback `per_item`. Non copre il caso di R-1
(lavora su una **coda persistente** con claim, ownership e ritentativi; qui la lista è
**effimera**, scoperta e consumata una volta), ma è la **terza** apparizione della stessa
forma. Le opzioni:

- **(a) Convergere** — il fan-out diventa un `QueueBackend` in-memory: una sola astrazione,
  ma si trascina claim/ownership/backoff dove non servono, e il fan-out prende una
  dipendenza concettuale dalla coda.
- **(b) Due astrazioni con confine dichiarato** — `run_fan_out` per la lista effimera,
  `QueueDrainEngine` per la coda durevole, e **una riga di doc in entrambe** che dice quando
  si usa l'una e quando l'altra. Più codice, confine leggibile.

Raccomandazione: **(b)**, ma la scelta è di Tid. Quello che **non** va fatto è scrivere il
terzo motore senza rispondere alla domanda: si finisce con tre.

**D-2 — La policy di aggregazione — ✅ DECISA (Tid, 2026-08-09): il pull va sistemato.**
Il pull da commessa solleva **solo se falliscono tutte** le commesse
(`E_PULL_COMMESSA_ALL_FAILED`): un rifiuto **parziale** chiude il `task_run` come
COMPLETATO, e al rilancio dello step il resolver dà **SKIP** — le commesse fallite non
vengono più ritentate e nessuno se ne accorge. Il fratello `snapshot_indirizzi_lotto`, **poche
righe sotto nello stesso file**, fa la cosa giusta: ritorna `TaskEsitoParziale` (task_run in
ERRORE **senza** sollevare), che al rilancio produce RESUME invece di SKIP.

È esattamente la riga «aggregazione esito» della tabella §1.1, ed è il **motivo più forte**
per fare R-1: finché la policy sta in ogni handler, diverge in ogni handler. Il BB deve
esporla come parametro con un **default che è quello giusto** (parziale → ERRORE non
sollevato), non lasciarla implicita.

⚠️ Conseguenza da mettere in conto: allineare il pull a `TaskEsitoParziale` è un **cambio di
comportamento**, non un refactor a parità. Va dichiarato e verificato a parte, non nascosto
dentro l'estrazione. Vedi memoria `feedback_pipeline_esito_parziale_ritiro_bandiere`.

**Esito della decisione**: il fix del pull diventa la **Fase 1 del brief**, eseguita e
testata **prima** dell'estrazione del BB, proprio perché è l'unico pezzo che cambia
comportamento — se fosse dentro il refactor, una regressione sarebbe ambigua. Due riscontri
utili emersi in ricognizione:

- **Nessuna azione DB.** Il codice `E_PULL_COMMESSA` è **già seedato**
  (`config/codici_errore.csv` + `messaggi_errore.csv`, policy `DATO_ERRATO`) e si riusa
  così com'è, con lo stesso criterio dello snapshot indirizzi («il motivo dominante reale,
  non un codice sintetico nuovo»). Niente brief al team DB, niente attesa.
- **Il meccanismo `TaskEsitoParziale` è già presidiato** — la classe non compare per nome
  nei test, ma il suo comportamento sì: `test_pipeline_step_executor.py` lo verifica sul
  ramo snapshot (test 28/29) e sul ramo scadenze (32/33), incluso «nessuna eccezione
  propagata». Mancano solo i test **specifici del pull**, che la Fase 1 del brief aggiunge.

**D-3 — Il run log è parte del BB o resta fuori?**
I due siti loggano in modo diverso: il push scrive `PUSH_STARTED`/`PUSH_COMPLETED` +
`log_push_run` (tabella dedicata), il pull scrive `event_log` + `PipelineErrorLogger` per
item. Se il BB inghiotte il logging serve un'interfaccia `run_logger` a due metodi
(start/end) più un canale per-item; se lo lascia fuori, il BB si riduce a
*discovery + isolamento + aggregazione* — più piccolo e più onesto, ma la simmetria del
«log del run» non viene incassata. Propendo per **dentro, ma come protocollo minimo**
(`start(ctx)` / `item_failed(item, exc)` / `end(esito)`), con i due siti che ne forniscono
l'implementazione: è la parte che si dimentica di replicare quando nasce il terzo chiamante.

### 1.3 Forma proposta (dopo D-1/D-2/D-3)

```text
esito = run_fan_out(
    items=<iterabile di discovery>,          # già risolto dal chiamante
    process=<callable(item) -> None>,        # eseguito in savepoint
    isolate=True,                            # transaction.atomic per item
    on_error=<SKIP_E_LOGGA | ABORT>,
    aggregate=<ALL_OK | PARTIAL | ALL_FAIL>, # default: parziale = non-successo
    run_logger=<start / item_failed / end>,
)
```

### 1.4 Vincoli operativi

- **Regola del 2 / caveat anti-astrazione prematura**: estrarre toccando **entrambi** i
  call-site nello stesso intervento, mai da un solo sito vivo (memoria
  `feedback_regola_del_2_estrai_bb`). Se si tocca un sito solo, non è un BB: è una funzione
  privata spostata.
- **Sviluppo concentrico, no YAGNI** (memoria `feedback_concentrico_no_yagni`): i parametri
  vanno progettati per il terzo chiamante, che qui **si sa già chi sarà** — qualunque task
  pipeline che itera su una lista di entità.
- Nessuna azione DB prevista. Se D-2 richiedesse un codice errore nuovo, si passa dal
  registro codici errore, non da un literal.

### 1.5 Definizione di «fatto» — ✅ raggiunta il 2026-08-09

- ✅ `run_fan_out` in `apps/core/services/fan_out.py`, con header e `# Scopo:`. **14 test**
  propri in `apps/core/tests/services/test_fan_out.py`.
- ✅ **Due** call-site convertiti nello stesso intervento: il pull da commessa e
  `BaseSourceHandler._process_rows`. Il blocco `errors[]` del pull è sparito come logica
  duplicata.
  ⚠️ **`_compute_stato` è rimasto**, e non è un pezzo lasciato a metà: il terzo sito
  (`_run_locked`) è stato **valutato e scartato con motivazione scritta** nel suo docstring
  — è un aggregatore di report, non un fan-out, e ha due semantiche incompatibili (§1.1 e
  §F5 del brief). Questa riga della DoD era formulata prima della ricognizione a codice.
- ✅ Il pull chiude il `task_run` in ERRORE su rifiuto parziale (D-2), con **4 test** che lo
  provano (parziale / tutte ok / tutte fallite / dry-run).
- ✅ Catalogo BB backend aggiornato (nuova sezione «Fan-out isolato») + confine
  `run_fan_out` ↔ `QueueDrainEngine` scritto **in entrambi i file**.
- ✅ Suite verde: **2229 test** (`apps.vendite` 1484 + `apps.core` 745).
- 🟡 **Resta**: validazione in-app e commit — entrambi di Tid.

> Consuntivo completo, con i **quattro scostamenti dichiarati** (incluso un residuo noto su
> `commessa_cache` che ho scelto di NON chiudere qui, e una correzione in più sulla coda del
> batch): §11 del [brief](brief-be-fan-out-isolato-e-esito-parziale.md).

---

## 2. R-2 — Il capitolo mancante della guida cruscotti — ✅ FATTO (2026-08-09)

**Fonte**: [brief-design-fatturazione-due-lenti.md](brief-design-fatturazione-due-lenti.md)
§11 Fase 4 · §6-quater (DL-19..28).

> ✅ **Eseguito il 2026-08-09.** Consuntivo in **§2.4**. La scoperta che ha cambiato il
> lavoro: non era solo materiale mancante — il §2.1 della guida conteneva una **frase
> falsa** («quattro aree»), e andava corretta a prescindere dal resto.

### 2.1 Il fatto

[docs/it/guide/cruscotti-fatturazione.md](../../guide/cruscotti-fatturazione.md) esiste ed è
buona: tre lenti, il concetto comune di «lavoro aperto», §7 «Gestire la fatturazione». Ma è
stata scritta il **2026-07-08** e rivista il **2026-07-22** su un altro asse (i verbi del
cockpit). La slice **3-ter** è entrata **in mezzo**, il 16-19 luglio, e non è mai stata
raccontata: la guida ha **zero occorrenze** di *DDT*, *resi*, *coda accrediti*.

Non è un buco cosmetico. Sono i concetti che un operatore **non può dedurre dalla
schermata**:

| Cosa vede l'operatore | Cosa non può indovinare |
|---|---|
| Card **Ordini** con un valore più basso del totale ordinato | DL-23: l'ordine porta il **residuo da spedire**, non il pieno — ma **solo** se il DDT è il veicolo di billing (`trigger ∈ {SPEDITO, CONSEGNATO}`); con `trigger = CONFERMATO` porta il pieno. Due card apparentemente incoerenti che sono entrambe giuste |
| Un ordine sparito dal Backlog ma presente nel serbatoio | DL-20: motivo `IN_ATTESA_DDT`, 🟢 fisiologico — non è l'ordine a pushare, non c'è nulla da fare su di lui |
| Un DDT in Backlog e non nel serbatoio | DL-22: `CONSEGNATO`/`RESO` sono `fase = CHIUSO`; un DDT dovuto e non pushato **è in ritardo**, non in attesa |
| Un DDT che non compare da nessuna parte | DL-21 emendato: entrano solo i DDT con **ruolo di fatturazione**; gli order-backed a `CONFERMATO` seguono l'ordine. E DL-28: causale non fatturabile → fuori |
| Riga resi con `MERCE_RESA_GIA_FATTURATA` 🟢 | Che è verde **perché nessuna azione esiste oggi** (NC non implementata) — non perché sia a posto. Senza questa frase sembra un falso verde |
| Coda accrediti con numeri negativi | DL-27: è un **contatore** `tenuti − fatturati` e **il segno decide** (positivo → fattura · negativo → accredita · zero → niente) |
| Blocco all'emissione di un DDT | DL-28: causale fatturabile ⇒ ogni riga deve avere un prezzo **risolvibile**; il prezzo dimenticato diventa errore parlante |

### 2.2 Cosa scrivere

Restando nel registro della guida (linguaggio non tecnico, destinatari operatori):

1. **Nuova sezione «DDT e resi nelle lenti»** dopo §4 (Backlog) — le due aree nuove, i 4
   motivi con il loro colore e il *perché* di quel colore.
2. **Riquadro dentro §5 (Situazione aperta)** — l'ordine al residuo (DL-23), con l'esempio
   numerico: ordine 1.000, spediti 600 → il serbatoio mostra 400 e i 600 vivono sul DDT;
   e il caso `CONFERMATO` in cui mostra 1.000.
3. **Nuova sezione «La coda accrediti»** — il contatore in una frase (*si fattura la merce
   che il cliente tiene in mano alla fine*, DL-26), il segno, e cosa fa l'operatore oggi:
   **niente**, perché la NC non c'è. Dirlo esplicitamente è metà del valore.
4. **Riga in §8 (Note tecniche)** — rimando ai brief in work-done per chi scende.

**Fonti da cui attingere** (tutte in work-done, tutte chiuse):
[brief-db-fatturazione-ddt-resi.md](brief-db-fatturazione-ddt-resi.md) ·
[brief-be-fe-ddt-resi-dashboard.md](brief-be-fe-ddt-resi-dashboard.md) ·
[brief-db-seed-lista-coda-accrediti-contatore.md](brief-db-seed-lista-coda-accrediti-contatore.md).

### 2.3 Definizione di «fatto»

Guida aggiornata, i 4 motivi nominati con il codice esatto che compare a schermo, l'esempio
numerico di DL-23 presente, la frase «oggi non c'è azione» sulla merce già fatturata, build
docs verde.

### 2.4 Consuntivo (2026-08-09)

**Fatto, in `docs/it/guide/cruscotti-fatturazione.md`:**

- ⚠️ **§2.1 corretta, non solo ampliata.** Diceva «il lavoro aperto vive in **quattro
  aree**» elencando `PREVENTIVI → ORDINI → OFFERTE → CONTRATTI`. Ne mancavano **tre**: il
  `DDT` nel serbatoio, `COMMESSE` e `RESI` che compaiono **solo nel Backlog**. Ora c'è
  anche il *perché* di quelle due (la commessa è il traguardo, non un documento che
  aspetta; il reso è flusso inverso e contarlo nel serbatoio sarebbe doppio conteggio).
- **§2.3 corretta**: l'euro vale anche per `DDT` e `COMMESSE`; i `RESI` restano a conteggi
  perché oggi non portano importi. Aggiunto l'avviso che ordini e DDT **non si sommano**.
- **Nuova §4.1** — i motivi di DDT e resi in tabella, nominati con l'**etichetta reale a
  schermo** (presa dall'i18n, non dal codice interno) e con il *perché* di ogni colore. Le
  due domande che nascono guardando l'elenco hanno una risposta scritta: perché un DDT in
  ritardo sta nel Backlog e non nel serbatoio, e perché certi DDT non compaiono affatto.
- **Nuova §5.1** — l'ordine al residuo, coi **due** esempi numerici opposti (400 e 1.000,
  entrambi giusti a seconda di quando quella vendita fattura).
- **Nuova §8 «La coda accrediti»** — dove sta (dentro *Vendite → Resi*, non è una lente),
  il conto in una riga, le due etichette, e la frase che vale metà sezione: **oggi da lì
  non si fa niente**, perché lo strumento non esiste ancora. Note tecniche → §9.
- Diagramma di §6 e intestazione di revisione allineati.

**Scostamenti dal piano di §2.2:**

1. La numerazione della sottosezione degli ordini è **§5.1**, non §5.2: la sezione 5 non
   aveva sottosezioni, quindi una «5.2» senza 5.1 sarebbe stata un salto.
2. **Non ho potuto eseguire il build docs**: `zensical` non è installato in questo ambiente
   (`ModuleNotFoundError`). Ho verificato a mano la coerenza delle **8 tabelle** del file e
   dei riferimenti interni `§N`; il build resta da fare al primo giro utile.
3. **Incoerenza di nomi risolta** (ok Tid, vedi §2.5): non era nel piano, era una
   segnalazione.

### 2.5 L'incoerenza «NC dovuta/facoltativa» — risolta

DL-24 impone di **nominare il fatto, non il rimedio**: le note di credito non sono ancora
definite, e un'etichetta non deve pre-decidere quale sarà lo strumento. Il motivo di fermo
rispettava la regola (`MERCE_RESA_GIA_FATTURATA`), le etichette della coda no: dicevano
*«NC dovuta»* / *«NC facoltativa»*.

Corretto nelle **sole etichette utente** (it + en):

| Codice | Prima | Ora |
|---|---|---|
| `DOVUTA` | NC dovuta | **Accredito dovuto** |
| `FACOLTATIVA` | NC facoltativa | **Accredito facoltativo — merce da ri-consegnare** |

⚠️ **I codici non sono stati toccati**, ed è deliberato: `etichetta` è una **colonna della
vista DB** `vendite.vw_resi_da_accreditare`, quindi rinominarla sarebbe un'azione DB da
passare al team. Non serve: i codici parlano dell'**accredito**, non della NC — era solo la
traduzione a introdurre lo strumento. Il perché è scritto nel commento di
`ResiCodaTable.vue`, dove qualcuno potrebbe rimetterci «NC» in buona fede.

---

## 3. R-3 — Validazione in-app di 3-ter (di Tid)

Il codice c'è ed è committato; manca il collaudo con dati veri. Checklist derivata dalle
decisioni, in ordine di rischio:

- **DL-19 — il bug che ha originato la slice**: un DDT che ha **superato** lo stato-trigger
  è ancora eleggibile al push (prima usciva per sempre, senza segnalazione). Prova: DDT
  order-backed con trigger `SPEDITO`, portalo a `CONSEGNATO`, verifica che risulti ancora
  da pushare.
- **DL-28 — gate causale**: DDT con causale fatturabile e una riga senza prezzo risolvibile
  → **blocco parlante** all'emissione, non silenzio. E causale non fatturabile (es.
  CONTO_VISIONE) → fuori dalle card.
- **DL-23 — nessun doppio conteggio**: ordine parzialmente spedito con trigger
  `SPEDITO/CONSEGNATO` → serbatoio mostra il **residuo**; con `CONFERMATO` → mostra il
  **pieno**.
- **DL-27 — il contatore**: reso confermato su merce già fatturata → riga in coda accrediti
  con differenza **negativa**; reso in DRAFT → **non** conta.
- **Card e drill-down**: le due aree nuove (DDT, RESI) si aprono davvero — la whitelist a 7
  aree era fail-closed, senza quella le card non erano drillabili.
- **Lista coda accrediti**: colonne 200-203 e i 3 preset resi, priorità responsive.

Esito atteso: se tutto regge, il due-lenti va in `work-done` (insieme a R-2).

---

## 4. R-4 — Rinviati con motivazione (non sono debito nascosto)

### 4.1 ~~`scrollable` sulle DataTable~~ — ❌ **VOCE RITIRATA (2026-08-09)**

**Non era un residuo: era una lettura sbagliata.** La segnalazione (rilievo di Tid) ha
mandato a verificare gli standard, e il quadro è questo:

- **Lo standard esiste e non lascia niente da decidere** —
  [frontend-standards.md](../frontend/frontend-standards.md) §Pattern lista: *«DataTable
  **sempre** con: `lazy`, `removable-sort`, `striped-rows`, `scrollable`,
  `scrollHeight="flex"`»*. Il layout lo presuppone: *«Il contenuto non scrolla — la
  DataTable gestisce il suo scroll interno»*.
- **È già applicato dove conta, e nel posto giusto: nei building block.** Verificato nel
  codice: `ListaConfigurabile` e `GeoSearchTable` — i due BB da cui passano tutte le liste,
  ricche e semplici — hanno entrambi `scrollable`. Le liste sono conformi **per
  costruzione**, esattamente come impone la regola 6 degli standard («cambi il paginator in
  `useSearchTable` una volta e tutte le liste si aggiornano»). Non c'era niente da
  propagare.
- **Il problema di partenza non si pone**: le liste sono **paginate** (25/pag desktop, 10
  sotto tablet), quindi nessuna tabella cresce senza limite; e lo scroll orizzontale è
  gestito da `useResponsiveColumns`, che ritira le colonne invece di far comparire la barra.

**Il conteggio di luglio («8 su 10 non lo usa») era su un'altra popolazione**: le tabelle
**annidate** dentro drawer, tab e pannelli — oggi 12 con `app-datatable--inner` e senza
`scrollable`, una con. E lì il non-uso ha un argomento a favore: dentro un drawer che già
scorre, una tabella con altezza fissa produce **due scroll annidati**, peggio di una
tabella che cresce. Infatti lo standard impone `scrollable` alle interne in **un solo
caso**, e per un motivo strutturale — dentro i **tab**, dove senza di esso la catena flex
esiste ma la tabella non scorre e la `TabList` finisce fuori vista (bug reale, 2026-07-22).

→ **Niente task, niente rinvio, niente da ri-misurare.** La voce resta scritta qui perché
sparire senza spiegazione è il modo in cui le non-cose tornano a galla.

### 4.2 Timestamp «in fase da» (DL-17) — rinvio confermato

L'anzianità usa `data_riferimento` (data documento), costo DB zero. Un timestamp di
ingresso-in-fase è rinviato a un'eventuale **v3** della Situazione aperta, e oggi non serve
a nessuno.

---

## 5. Dipendenze fuori perimetro, ma collegate

- **La slice NC (note di credito) non esiste.** Verificato: nessun `NOTA_CREDITO` nel seed
  né nel backend. È il presupposto di `MERCE_RESA_GIA_FATTURATA` 🟢 (DL-24) e il contratto
  posto da DL-27 è già scritto: *la NC deve essere attribuibile alla merce e portare una
  quantità*, altrimenti il contatore non la vede. Quando nascerà, quel vincolo è il primo
  requisito. ⚠️ Da non confondere con
  [sviluppo-rettifiche.md](../work-in-progress/sviluppo-rettifiche.md), che è un'**altra** cosa (note di
  credito/debito da **rettifica prezzi** retroattiva, DB-L4 pricing).
- **`avanza_step` / `rilancia_step`** restano gate del **frontend** per scelta dichiarata:
  il DB non le espone perché il verdetto (step successivo, criticità, distinzione
  avanza/rilancio) vive nel runner Python. È una deroga voluta, non un residuo — ma va
  ricordata se un giorno si vorrà la simmetria piena con le altre
  `fn_available_actions_*`.

---

## 6. Stato e ordine (aggiornato 2026-08-09, fine giornata)

| # | Residuo | Stato |
|---|---|---|
| **R-1** | BB fan-out + fix esito parziale | ✅ **ESEGUITO** — 2234 test verdi, **residuo `commessa_cache` compreso** (chiuso in giornata, §12 del brief). Aperto: validazione in-app + commit (Tid) |
| **R-2** | Capitolo guida DDT/resi/coda accrediti | ✅ **FATTO** — §2.1 **corretta** (diceva il falso), §4.1 / §5.1 / §8 nuove, più l'incoerenza «NC» risolta nelle etichette (§2.5). Resta il **build docs**, non eseguibile qui |
| **R-3** | Validazione in-app di 3-ter | ⬜ **DI TID** — sblocca la chiusura del due-lenti |
| **R-4** | Rinviati con motivazione | 🔸 lo `scrollable` è **ritirato** (non era un residuo: lo standard c'è ed è già nei BB — §4.1); resta il solo timestamp «in fase da», rinviato a una v3 |

**Non resta lavoro mio**: R-1 e R-2 sono eseguiti. Quel che manca sono **due prove in-app**
— la validazione di 3-ter (R-3) e quella dell'esito parziale del pull (R-1) — che conviene
fare nella stessa sessione, perché toccano la stessa area. Per R-1 serve prima un `HUP` al
gunicorn. Più il **commit**, e il **build docs** alla prima occasione.

Quando R-1 e R-3 saranno validati e R-2 scritto, **tre doc si chiudono insieme**:
[analisi-orchestrazione-vendite-simmetrie](analisi-orchestrazione-vendite-simmetrie.md),
[brief-design-fatturazione-due-lenti](brief-design-fatturazione-due-lenti.md) e
[brief-be-fan-out-isolato-e-esito-parziale](brief-be-fan-out-isolato-e-esito-parziale.md)
vanno in `work-done`, e questo piano con loro.
