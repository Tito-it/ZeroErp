# Brief — Drawer di visualizzazione fattura

> **Tipo**: brief BE/FE (`dev/backend-tid`) · **Data**: 2026-07-28 · **Owner**: Tid ·
> **Stato**: ⬜ **DA FARE** · **Priorità**: 🟠 MEDIA (buco di consultazione: la
> fattura oggi si vede solo in PDF) ·
> **Prerequisiti DB**: ✅ **nessuno** — vedi §2
>
> **Origine**: richiesta di Tid del 2026-07-28. *«Manca un drawer di
> visualizzazione delle fatture: si dovrebbe vedere a video la fattura in un
> formato simile a quello usato per preventivi, ordini ecc.»*
>
> **Contesto**: non siamo in produzione
> ([[project_no_produzione_solo_sviluppo]]) → breaking secchi ammessi.

---

## 1. Il buco, in una frase

La fattura è l'unico documento del ciclo attivo che **non si può leggere a
video**: esiste come PDF e come righe di una lista, mai come documento.

Dal `LottoDrawer` l'operatore vede numero, cliente, stato e totale — quattro
colonne — e per sapere *cosa c'è dentro* deve scaricare il PDF. Preventivi,
offerte, ordini, contratti e DDT hanno tutti il loro drawer.

---

## 2. La scoperta che cambia il conto della spesa

**Il lettore esiste già, ed è collaudato.** Quattro metodi in
`apps/vendite/db/vendite_repository.py` assemblano esattamente ciò che serve,
con tutte le decodifiche fatte via JOIN:

| Metodo | Cosa restituisce |
| --- | --- |
| `get_fattura_testata(fattura_id)` | testata + cliente + emittente + pagamento + totali, tutto decodificato |
| `list_fattura_righe(fattura_id)` | righe da `vw_fattura_righe_esposte` (kit risolti) |
| `list_fattura_riepilogo_iva(fattura_id)` | riepilogo IVA da tabella reale |
| `list_fattura_scadenze(fattura_id)` | piano rate |

Hanno **un solo consumatore**: il `FatturaDocumentContextBuilder`, cioè il
contesto del PDF. Nessun endpoint li espone.

> **Conseguenza di merito, non solo di costo**: il drawer che pubblica lo stesso
> contesto del PDF mostra a video **la stessa cosa che finisce nel documento
> fiscale**, per costruzione e non per disciplina. È la regola R17 (PDF, XML SDI
> e portale devono raccontare lo stesso documento) applicata a una quarta uscita
> senza doverla presidiare a mano.

**Niente lavoro DB.** Nessuna colonna, nessuna vista, nessuna funzione: tutto
ciò che serve è già in tabella e già letto.

---

## 3. Le informazioni visualizzabili

Inventario completo di ciò che è **disponibile oggi**, per zona del drawer.
Il perimetro effettivo del v1 è in §4.

### 3a. Identità del documento — zona alta

`numero` · `serie` · `anno` · `data` · tipo doc fiscale (codice_interno +
descrizione) · stato doc fiscale (codice_interno + descrizione) ·
`data_contabilizzazione` · `uid`

> ⚠️ **Una fattura in DRAFT ha `numero` NULL**: il numero fiscale si assegna
> alla numerazione, non alla creazione. Il drawer deve renderlo esplicito
> («non numerata»), mai come cella vuota — un campo vuoto in un documento
> fiscale si legge come un dato perso, non come uno stato del processo.

### 3b. Cliente — zona alta

Ragione sociale completa · id fiscale univoco (CF/P.IVA) · indirizzo di
fatturazione risolto e già formattato (tipo `FATT`) · codice billing account ·
utility del servizio (codice + descrizione)

### 3c. Emittente — zona alta

Denominazione · P.IVA · codice fiscale · sede legale formattata (tipo
`SEDELEG`) · codice emittente fiscale

### 3d. Pagamento e scadenze

Modalità di pagamento (codice) · termine di pagamento (codice_interno) ·
`giorni_pagamento` · `fine_mese` · **piano rate** da `vendite.fatture_scadenze`
(numero rata, data scadenza, importo)

> La «data scadenza» **non è un campo di testata**: è una o più rate. Su rata
> unica si mostra come data singola; su rate multiple serve la tabellina. Un
> drawer che ne mostrasse solo una mentirebbe sulle fatture rateizzate.

### 3e. Totali — zona alta, blocco a destra

`imponibile_tot` · `imposta_tot` · `bollo_applicato` + `bollo_importo` ·
`arrotondamento_attuale` · `arrotondamento_precedente` · **`totale_doc`** ·
**`totale_a_pagare`** · valuta (`iso_code`) · `tasso_cambio`

> ⚠️ **Non esiste uno sconto di testata.** Il context builder legge
> `testata.get("sconto_tot")`, ma quella colonna in `vendite.fatture` **non
> c'è**: vale sempre `None`, e il template la salta con un `{% if %}`. Lo sconto
> vive solo per riga (`sconto_percentuale`). Una riga «Sconto» nei totali del
> drawer resterebbe vuota per sempre: non va messa.
>
> **`totale_doc` e `totale_a_pagare` vanno mostrati ENTRAMBI.** Divergono quando
> ci sono fondi/acconti applicati (`vendite.fatture_fondi_fattura`): mostrare
> solo il primo lascia l'operatore senza spiegazione del perché il cliente paga
> meno; mostrare solo il secondo perde il totale del documento fiscale.

### 3f. Righe — zona centrale

**Fonte: `vendite.vw_fattura_righe_esposte`, NON la tabella `fatture_righe`.**

Per riga: `riga_nr` · codice + descrizione articolo · descrizione di riga ·
UoM · quantità · prezzo unitario · sconto % · IVA (codice, descrizione,
aliquota) · natura IVA · **imponibile riga**

Più due campi che governano il rendering: `tipo_riga`
(`NORMALE` / `KIT_PADRE` / `KIT_COMPONENTE`) e `livello` (0/1). I **kit** si
rendono come padre col totale e sotto i soli componenti con
`kit_esposto_in_fattura`.

> Usare la vista e non la tabella non è un dettaglio di comodo: è la stessa
> regola R17 di §2. La tabella contiene i componenti *tutti*; la vista è la
> rappresentazione **unica** del documento. Un drawer che leggesse la tabella
> mostrerebbe una fattura diversa da quella stampata.
>
> ⚠️ `id` è **NULL** sulle righe `KIT_PADRE` (non esistono in tabella): non usarlo
> come `data-key` del DataTable senza fallback su `ordinamento`.

### 3g. Riepilogo IVA — zona bassa

Da `vendite.fatture_riepiloghi_iva` (tabella **reale**, già aggregata e
arrotondata dalla pipeline — a differenza degli ordini, che derivano il
riepilogo on-the-fly da una vista): per gruppo IVA/natura/esigibilità/split →
aliquota, codice e descrizione IVA, natura, `esigibilita`, `split_payment`,
imponibile, imposta, arrotondamento.

Lettura pura: **niente ricalcoli lato FE**, mai.

### 3h. Contesto operativo — disponibile, ESCLUSO dal v1 (§4)

`critical` · `canale_origine` (ADMIN/PORTALE/SHOP) · `minimo` · sorgente
polimorfa (`sorgente_tipo_id` + `sorgente_uid`) · registro di fatturazione ·
stato SDI (`fatture_sdi`) · lotto di appartenenza · fondi/acconti ·
`fatture_rettifiche` · `fatture_log` · `meta` jsonb

---

## 4. Perimetro del v1 — decisioni Tid (2026-07-28)

| # | Cosa | Decisione |
| --- | --- | --- |
| 1 | **Note della fattura** | ✅ **SÌ** — pulsante «Gestisci note» che porta nell'apposita area, **riusando il BB esistente** come gli altri documenti |
| 2 | **Pannello «Passaggi»** (lineage) | ❌ **NO** per ora |
| 3 | **Zona contesto operativo** (§3h) | ❌ **NO** per ora — «poi vediamo» |
| 4 | **Pulsante ristampa** | ❌ **NO** nel v1 |

Sul punto 4 la scelta era fra tre strade, tutte praticabili:

- riusare `POST …/documenti/genera/` (sincrono, zero lavoro BE) — ma **non è**
  una ristampa: crea un nuovo `documento_generato` e consuma un progressivo a
  ogni click;
- un endpoint nuovo che accodi la singola fattura in `vendite.fatture_stampa_coda`
  (la semantica vera, simmetrica alla ristampa massiva C-8) — costo: endpoint +
  service + repo, più il guard sul vincolo `uq_fatture_stampa_coda_vivo`;
- **niente**, che è la decisione presa.

Restano nel drawer i due verbi già pronti — «Vedi stampa» e «Documenti
allegati» — e la ristampa massiva resta dov'è, nel `LottoDrawer`.

---

## 5. [BE] Endpoint di dettaglio

`GET /api/v1/vendite/fatture/<fattura_id>/`

Restituisce in **un round-trip** testata + righe + riepilogo IVA + scadenze,
orchestrando i quattro lettori di §2. Nessuna logica nuova: solo composizione.

- View `ApiFatturaDetail` su `DomainAPIView`, `area_funzionale = "vendite"`
- Read-only: nessuna `Idempotency-Key`, nessun `post_permission`
- Il montaggio va in `urls_fatture.py`, che **esiste già** (oggi ha solo le
  rotte `documenti/`)
- Fattura inesistente **o fuori scope** → `404` `E_FATTURA_NOT_FOUND`, indistinguibili
  (nessun leak, come da api.md §Scope emittente)

### 5-bis. Il pezzo non ovvio: la RLS copre la testata, NON i satelliti

Verificato sul DB vivo il 2026-07-28:

| Tabella / vista | RLS | Conseguenza |
| --- | --- | --- |
| `vendite.fatture` | ✅ **ON** — policy `rls_fatture_ef_whitelist` + `rls_fatture_ba_ownership` | una fattura fuori scope **non è leggibile**: 0 righe → 404 gratis |
| `vendite.fatture_righe` | ❌ **OFF** | leggibile da chiunque, conoscendo l'id |
| `vendite.fatture_riepiloghi_iva` | ❌ **OFF** | idem |
| `vendite.note_fatture` | ❌ **OFF** | idem |
| `vendite.fatture_scadenze` | ✅ ON | protetta |
| `vw_fattura_righe_esposte` | `security_invoker=on` … | …ma poggia su `fatture_righe`, che RLS non ha → **nessuna protezione ereditata** |

> ⚠️ **Regola vincolante per il service**: caricare **PRIMA** la testata e
> **fermarsi con 404** se è `None`; solo dopo leggere righe, riepilogo IVA,
> scadenze e note. Invertire l'ordine — o leggere i satelliti in parallelo —
> espone righe e importi di una fattura di un altro emittente a chi indovina un
> intero. La testata è l'**unico** cancello, e vale per ogni consumatore futuro
> di questi lettori.

Difesa in profondità: `VenditeRepository` ha già `_add_scope_emittente`
(usato da `list_lotto_fatture`); l'endpoint può sommarlo alla RLS con
`get_scope_user_id(request)`, coerentemente con la policy di casa «i filtri
applicativi restano e si sommano».

### 5-ter. Nota per il team DB (non blocca questo brief)

`fatture_righe` e `fatture_riepiloghi_iva` **senza RLS** non sono un problema
finché l'unico percorso di lettura passa dalla testata, ma è una difesa che
dipende dalla disciplina di ogni chiamante invece che dalla struttura. Vale la
pena valutare una policy `via_fattura` simmetrica a quella di
`commesse_attivita` (`fn_scope_ef_whitelist_via_commessa`). **Fuori perimetro
qui**: annotato per una valutazione separata.

---

## 6. [BE] Cablaggio note FATTURA — BB esistente, zero DB

Verificato il 2026-07-28: **è solo cablaggio**, non c'è nulla da costruire.

- ✅ La partizione `vendite.note_fatture` **esiste** (`FOR VALUES IN ('FATTURA')`)
- ✅ Ha il trigger di validazione `trg_note_fatture_validate_ins_upd` (a differenza
  di `note_attivita_fatturabili`, che ne è priva by design)
- ✅ `"FATTURA"` è **già** in `TARGET_TIPI_AMMESSI` di `PartitionedNoteRepository`

Serve una terza istanza in `apps/vendite/api/note_views.py`, accanto a
PREVENTIVO e CONTRATTO: repo + service factory + le due view dalla factory
`make_note_views`. È il clone dichiarato dal catalogo BB — *«aggiungere
ordini/DDT/fatture/AF = ~10 righe clonate»*.

Endpoint risultanti:

- `GET/POST /api/v1/vendite/fatture/<id>/note/`
- `GET/PATCH/DELETE /api/v1/vendite/fatture/<id>/note/<note_id>/`

> ⚠️ Ordine di montaggio in `urls_fatture.py`: le rotte note vanno registrate
> **prima** di eventuali pattern generici, e comunque il path `<int:sorgente_id>/documenti/`
> esistente non collide (`note/` ≠ `documenti/`).

---

## 7. [FE] Drawer `FatturaDrawer.vue`

Sola lettura, **generico e richiamabile da più punti**, costruito interamente su
BB esistenti.

### 7a. Struttura

```text
DrawerTitle                          "Fattura"
DrawerEntityHeader                   Tag numero/serie · cliente · data
                                     #status → Tag stato (statoDocFiscaleSeverity)
DrawerActionsBar                      [Vedi stampa] [Allegati] [Gestisci note (N)]
── blocco cliente / emittente / pagamento ──   form-grid-2col, sola lettura
── blocco totali ──                             a destra, imponibile/imposta/bollo/
                                                arrotondamento/TOTALE/a pagare
── scadenze ──                        tabellina rate (se > 1) o riga singola
── righe ──                           DataTable app-datatable--inner, kit indentati
── riepilogo IVA ──                   DataTable app-datatable--inner
FormFooter close-only
```

### 7b. BB da riusare — nessun componente nuovo oltre al drawer

| Cosa | BB |
| --- | --- |
| Titolo + badge readonly | `DrawerTitle` |
| Testata documento | `DrawerEntityHeader` (+ slot `#status`) |
| Barra azioni | `DrawerActionsBar` (`kind: 'manage'` con `badge` sul counter note) |
| Stato fiscale colorato | `statoDocFiscaleSeverity` (`core/utils/severity.js`) — **già mappato** |
| Vedi stampa / allegati | `EntityPdfButton` / `PdfDocumentiSorgenteDialog`, `sorgenteCode = 'FATTURA'` |
| Note | `NoteDrawer` + wrapper thin `FatturaNoteDrawer.vue` (~30 righe, clone di `PreventivoNoteDrawer`) via `makeNotesApi('/vendite/fatture/<id>')` |
| Chiusura | `useDrawerClose`, `FormFooter close-only` |
| Apertura fluida | `useDrawerContentReady` (`@after-show`) |
| 404/fuori scope | `useDrawerDetailLoad` → toast + chiusura |
| Importi | `formatCurrency`; date `displayDate` |

Larghezza: `DRAWER_WIDTH.WIDE` (960px) — due tabelle più il blocco totali.

### 7c. Aggancio: kebab delle righe fatture del `LottoDrawer`

Primo consumatore. In [LottoDrawer.vue](../../../frontend/src/vendite/components/LottoDrawer.vue)
la tabella fatture ha già `RowActionsMenu` con `buildFatturaActions(data)`:
si aggiunge una voce «Apri fattura» che apre il drawer su `data.fattura_id`.

> ⚠️ **Attenzione al drawer-dentro-drawer**: il `FatturaDrawer` si apre sopra il
> `LottoDrawer`. Va verificato in-app che la sovrapposizione PrimeVue non
> nasconda la X di chiusura o non blocchi lo scroll del padre — è il tipo di
> difetto che nessun test coglie. Se dà problemi, l'alternativa nota è aprire il
> secondo drawer **dopo** aver chiuso il primo, o usare `AppDialog` width `xl`.

Consumatori successivi (fuori v1, gratis una volta esistente il drawer):
Dashboard Competenza, ricerca universale, portale clienti.

---

## 8. Cosa NON è in questo brief

- **Modifica della fattura**: il drawer è di sola consultazione. La fattura si
  produce dalla pipeline e oltre EMESSA le righe sono congelate
  (`trgfn_fatture_righe_guard_congelamento`, `E_FATTURA_RIGA_CONGELATA`).
- **Emissione / numerazione / annullamento**: vivono nel cockpit e nel
  `LottoDrawer`, con i loro permessi. Duplicarli qui creerebbe due porte per lo
  stesso verbo.
- **Nota di credito e rettifiche**: atto fiscale con perimetro proprio.
- **Ristampa singola** (§4.4), **Passaggi** (§4.2), **zona contesto operativo**
  (§4.3): esclusi per decisione, non per impossibilità. Tutti e tre sono
  aggiungibili dopo senza rifare nulla.

---

## 9. Piano

| # | Artefatto | Tipo |
| --- | --- | --- |
| **B1** | `vendite_service.get_fattura_dettaglio` — orchestrazione dei 4 lettori, testata-first (§5-bis) | BE nuovo |
| **B2** | `ApiFatturaDetail` + rotta in `urls_fatture.py` | BE nuovo |
| ~~**B3**~~ | ~~codice errore 404~~ — ✅ **non serve**: `E_FATTURA_NON_TROVATA` è già registrato (404, `show_empty_state`) | — |
| **B4** | Terza istanza note in `note_views.py` (FATTURA) + 2 rotte | BE cablaggio |
| **B5** | Test service: 404 fuori scope, testata-first, shape della risposta | BE test |
| **B6** | `docs/it/backend/vendite/manual/api_fattura_dettaglio.md` + riga d'indice in `api.md` | Doc |
| **F1** | `FatturaDrawer.vue` | FE nuovo |
| **F2** | `FatturaNoteDrawer.vue` (wrapper thin su `NoteDrawer`) | FE clone |
| **F3** | `frontend/src/vendite/api/fatture.js` — client (`getFatturaDettaglio`, `makeNotesApi`) | FE nuovo |
| **F4** | Voce «Apri fattura» nel kebab del `LottoDrawer` | FE |
| **F5** | Chiavi i18n it/en sotto `vendite.fatture.*` | FE |

**Verifiche**: suite Django · build Vite · `check_i18n_keys.py` · e la
**validazione in-app di Tid** su una fattura vera, con e senza kit, con rate
multiple — l'unico giro che dimostra che a video c'è ciò che è nel PDF.

---

## 10. Registro

### 2026-07-28 · Analisi e perimetro

Richiesta di Tid. Analisi condotta sul DB vivo e sul codice, non sui brief.

**Tre scoperte che hanno cambiato il brief rispetto alla richiesta iniziale:**

1. **Il lettore esisteva già** (§2): la stima è passata da «costruire la lettura
   di una fattura» a «esporre un contesto già collaudato».
2. **La RLS protegge la testata ma non i satelliti** (§5-bis): da qui la regola
   vincolante «testata prima, 404, poi il resto», che è l'unica cosa
   veramente delicata di tutto l'endpoint.
3. **Lo sconto di testata non esiste** (§3e): il campo che il context builder
   legge non è una colonna. Nel layout dei totali non va previsto.

**Decisioni Tid**: note sì (BB esistente) · Passaggi no · contesto operativo no ·
ristampa no.
