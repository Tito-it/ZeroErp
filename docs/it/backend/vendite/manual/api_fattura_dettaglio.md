# API dettaglio fattura (Django)

## Scopo

Esporre via HTTP il **documento fattura completo** per la consultazione a video:
testata (cliente, emittente, pagamento, totali già decodificati), righe,
riepilogo IVA, piano rate e i **contatori dei badge**, in un solo round-trip.

Alimenta il `FatturaDrawer` del frontend — il drawer generico che rende la
fattura leggibile senza scaricare il PDF.

## Contesto

Fino al 2026-07-28 la fattura era l'unico documento del ciclo attivo non
consultabile a video: esisteva come PDF e come quattro colonne nella lista del
`LottoDrawer`.

L'endpoint **non introduce nuove letture**: orchestra i quattro metodi di
`VenditeRepository` che già alimentavano il contesto del PDF.

> **Conseguenza di merito.** Video e stampa mostrano lo stesso documento **per
> costruzione**, non per disciplina: è la regola R17 (PDF, XML SDI e portale
> devono raccontare lo stesso documento) estesa a una quarta uscita senza
> doverla presidiare a mano.

View: `ApiFatturaDetail` (`apps.vendite.api.fatture_views`) →
service `get_fattura_dettaglio` (`apps.vendite.services.vendite_service`).

## Input

- Metodo: `GET`
- Path: `/api/v1/vendite/fatture/<fattura_id>/`
- Header: `Authorization: Bearer <access_token>`
- Nessun query param.

## Output

- `200`: documento completo

```json
{
  "data": {
    "fattura": {
      "id": 7, "uid": "…", "numero": 123, "serie": "A", "anno": 2026,
      "data": "2026-07-01", "data_contabilizzazione": null,
      "tipo_doc_fiscale_codice": "FATTURA", "tipo_doc_fiscale_descrizione": "Fattura",
      "stato_codice_interno": "DEFINITIVA", "stato_descrizione": "Definitiva",
      "emittente_denominazione": "…", "emittente_piva": "…", "emittente_sede": "…",
      "emittente_fiscale_pk": 3,
      "ragione_sociale_completa": "Rossi Mario SRL",
      "id_fiscale_univoco_cf_piva": "…", "cliente_indirizzo": "…", "ba_codice": "BA-000123",
      "utility_codice": "GAS", "pagamento_modalita_codice": "BON",
      "imponibile_tot": "1000.00", "imposta_tot": "220.00",
      "bollo_applicato": false, "bollo_importo": null,
      "arrotondamento_attuale": "0.00",
      "totale_doc": "1220.00", "totale_a_pagare": "1220.00",
      "valuta_codice": "EUR", "tasso_cambio": "1.000000"
    },
    "righe": [
      {
        "riga_key": "R:41", "fatture_righe_id": 41, "tipo_riga": "NORMALE",
        "riga_nr": 1, "ordinamento": 1,
        "articolo_codice": "ART-001", "descrizione": "Canone mensile",
        "uom_codice": "kWh", "quantita": "10.00", "prezzo_unitario": "100.00",
        "sconto_percentuale": null, "iva_codice": "22", "iva_aliquota": "22.00",
        "iva_natura": null, "importo_riga": "1000.00",
        "componenti": null, "componenti_numero": 0
      }
    ],
    "riepilogo_iva": [
      { "iva_aliquota": "22.00", "iva_descrizione": "IVA 22%",
        "esigibilita": "I", "split_payment": false,
        "imponibile": "1000.00", "imposta": "220.00", "arrotondamento": "0.00" }
    ],
    "scadenze": [
      { "numero_rata": 1, "data_scadenza": "2026-08-31", "importo": "1220.00" }
    ],
    "rettifiche": {
      "rettifica": [],
      "rettificata_da": [
        { "verso": "rettificata_da", "id": 9, "numero": 15, "serie": "A", "anno": 2026,
          "data": "2026-07-20", "numero_documento": "15 - A",
          "natura_doc_codice_interno": "NOTA_CREDITO" }
      ]
    },
    "errore_vivo": null,
    "contatori": { "note": 3 }
  },
  "meta": { "request_id": "…" }
}
```

- `400`: `E_VENDITE_VALIDATION` — `fattura_id` non positivo
- `403`: area `vendite` BLOCCATA, oppure oggetto `vendite.fattura` bloccato
- `404`: `E_FATTURA_NON_TROVATA` — inesistente **oppure fuori scope emittente**

## Regole

### Ordine di lettura: la testata è l'unico cancello

⚠️ **Regola vincolante del service, non stile.** Stato RLS al **2026-07-29**:

| Oggetto | RLS | Effetto |
| --- | --- | --- |
| `vendite.fatture` | ✅ `rls_fatture_ef_whitelist` + `rls_fatture_ba_ownership` | fattura fuori scope → 0 righe → 404 |
| `vendite.fatture_righe` | ✅ `_ef_whitelist` (`FOR ALL`) + `_ba_ownership` (`FOR SELECT`) | dal 2026-07-29 |
| `vendite.fatture_riepiloghi_iva` | ✅ idem | dal 2026-07-29 |
| `vendite.fatture_scadenze` | ✅ | protetta |
| `vendite.note_fatture` | ❌ **assente** | come tutte le partizioni note |
| `vw_fattura_righe_esposte` | `security_invoker=on`, ora poggia su una tabella **con** policy | eredita il filtro |

Il service carica **prima** la testata e **si ferma con 404** se è `None`; solo
dopo legge righe, riepilogo IVA e scadenze.

> **La regola sopravvive al changeset, la sua motivazione si restringe.** Fino
> al 2026-07-28 l'ordine era l'unica cosa che impediva a righe e importi di
> un'altra fattura di uscire dall'endpoint. Ora quelle due tabelle si difendono
> da sole, e l'ordine resta vincolante per due ragioni diverse:
>
> 1. **è il 404 unificato**: senza il cancello si restituirebbe un documento a
>    metà — testata assente e satelliti vuoti — invece di un errore netto;
> 2. **i satelliti protetti sono due, non tutti**: `note_fatture`,
>    `fatture_indirizzi`, `fatture_fondi_fattura`, `fatture_sdi` restano senza
>    policy. Qualunque lettura futura che li aggiunga a questo endpoint è
>    coperta solo dal fatto che si passa prima dalla testata.

Prova empirica della chiusura (`pg_class.reltuples` non è filtrato dalla RLS,
`count(*)` sì — il confronto fra i due dice se una policy morde davvero):

| Tabella | Righe reali | Visibili senza GUC — prima | Visibili senza GUC — dopo |
| --- | --- | --- | --- |
| `vendite.fatture_righe` | 8 | 8 | **0** |
| `vendite.fatture_riepiloghi_iva` | 7 | 7 | **0** |

Nessuna modifica applicativa è stata necessaria: il percorso operatore legge gli
**stessi** risultati di prima su tutte e 7 le fatture di test. Brief chiuso:
[brief-db-rls-satelliti-fattura-portale](../../../dev/work-done/brief-db-rls-satelliti-fattura-portale.md).

> ⚠️ **Vincolo da non violare** (team DB): le policy sui satelliti devono
> continuare a decidere **dalla testata**: la chiave è `fattura_id`, risolta
> col modo `fattura` dei risolutori — `script.fn_resolve_emittente_fiscale_id`
> sotto `script.fn_scope_ef_perimetro` (operatore) e
> `script.fn_resolve_controparte_sr_id` sotto `script.fn_scope_sr_perimetro`
> (portale). Forma in vigore dal 2026-10-21; fino ad allora erano gli
> adattatori `fn_scope_ef_whitelist_via_fattura` e
> `fn_scope_ba_ownership_via_fattura` (quest'ultimo ritirato con 20261021-40).
> È ciò che rende il filtro **tutto-o-niente per fattura** e tiene completi il
> `count` di `fn_assign_numero_fattura` e la `SUM` di
> `fn_ricalcola_riepilogo_iva_fattura`. Un criterio proprio o una colonna
> denormalizzata renderebbero possibili le **somme parziali** — e un riepilogo
> IVA parziale non solleva errori: si scrive e basta.

### Scope e permessi

- **Difesa in profondità**: `get_fattura_testata(..., auth_user_id=...)` somma
  un filtro applicativo (`_add_scope_emittente`, convenzione SR) alla RLS.
  `auth_user_id=None` (default) = nessun filtro applicativo — è il percorso del
  motore documentale, che applica lo scope a monte e resta invariato.
- **404 unificato**: inesistente e fuori scope danno la stessa risposta. Un
  errore che li distinguesse confermerebbe l'esistenza di una fattura altrui.
- `model_permission = ("vendite", "fattura")`: il model **è** catalogato in
  `config.area_model_overrides`, quindi un admin può bloccare le fatture come
  singolo oggetto. Senza override il resolver ricade sul livello area.

### Lettura pura

- Nessun ricalcolo: il riepilogo IVA arriva da `vendite.fatture_riepiloghi_iva`,
  tabella **reale** già aggregata e arrotondata dalla pipeline (a differenza
  degli ordini, che lo derivano da una vista on-the-fly).
- Le righe arrivano da `vw_fattura_righe_lista` (dal 2026-09-28, lotto C del
  brief-db-liste-righe-documento), la **stessa vista** della lista a video
  (`GET fatture/<id>/righe/lista/`, [api_righe_documento.md](api_righe_documento.md)):
  il primo livello di `vw_fattura_righe_esposte`, la rappresentazione unica del
  documento che risolve i **kit** — una riga `KIT_PADRE` col totale, con i soli
  componenti esposti **dentro** di lei (`componenti`, jsonb). Ordine del
  documento: `ordinamento, riga_nr, riga_key`.
  ⚠️ La chiave è `riga_key`: `fatture_righe_id` è **NULL** sul padre di un kit,
  che in tabella non esiste. La chiave vera di un componente è il suo
  `fatture_righe_id` dentro `componenti`.
  ⭐ **Dal 2026-09-30 è anche la forma del PDF**: il contesto di stampa della
  fattura è alla forma 2 e legge la stessa vista (`FattureRepository.list_righe`),
  la lettura piatta `VenditeRepository.list_fattura_righe` è ritirata. Stampa
  solo una versione del template che dichiara la forma 2
  (brief-db-documenti-versione-contesto-template §11).
  ⭐ **Dal 2026-10-02 ogni riga porta il suo periodo** — `competenza_dal`,
  `competenza_al` (date, `NOT NULL`) e `ha_periodo`, vero quando `dal ≠ al`: è
  la vista a deciderlo, il client lo mostra e non lo ricalcola. Lo stesso kit
  su due periodi sono **due** righe `KIT_PADRE`. La quantità e l'unità del
  padre sono quelle della **riga padre del documento** (`fatture_righe.kit_qta`,
  `kit_uom_id`), non più media e massimo dei componenti; su un kit i cui
  componenti non dicono lo stesso numero di kit (nota di credito parziale)
  `quantita` e `prezzo_unitario` sono **NULL** e resta l'importo — non è un
  errore. Il contesto di stampa è alla **forma 5** e la stampa la legge solo
  la v7 del template (brief-db-bom-flag-quantita-e-kit-in-fattura, R-BE-B6).
- Nessun verbo di modifica su questo path: la fattura è prodotta dalla pipeline
  e oltre la soglia di congelamento le righe sono congelate a DB
  (`trgfn_fattura_satellite_guard_congelamento`, `E_FATTURA_RIGA_CONGELATA`).
  ⚠️ La soglia è un **dato**, `config.stati_doc_fiscale.congela_fiscale` (oggi
  da `DEFINITIVA` in poi), non una lista di stati scritta a mano: `D33` del
  brief IVA l'ha portata a sede unica. E la guardia sulle righe non è più una
  funzione sua — `D34` l'ha riassorbita nella generica dei satelliti, che
  riceve il codice errore come secondo argomento del trigger: stesso rifiuto,
  stesso messaggio, stesso bypass.

### `rettifiche` — il legame documentale, nei due versi

`{ "rettifica": [...], "rettificata_da": [...] }`: le chiavi sono **sempre** tutte
e due (liste vuote se non c'è legame). `rettifica` = i documenti che **questo**
rettifica (su una nota di credito); `rettificata_da` = i documenti che rettificano
questo. Ogni elemento: `verso`, `id`, `numero`, `serie`, `anno`, `data`,
`numero_documento` (`vendite.fn_numero_documento_fattura`),
`natura_doc_codice_interno`; ordine `anno, numero`. Sorgente
`vendite.fatture_rettifiche`, popolata **dopo** la numerazione (vedi sotto). ⚠️
Letto dopo il cancello della testata: `fatture_rettifiche` non ha RLS.

### `errore_vivo` — il banner d'errore, con una fonte sua *(dal 2026-09-27)*

La riga ERROR **più recente e non ritirata** del giornale del documento (la
stessa forma di una riga della Storia: `cosa`, `etichetta_key`, `quando`, …), o
`null`. Alimenta il banner in testa al `FatturaDrawer`: chi apre una fattura in
errore la apre per quello.

⭐ **Perché sta qui e non nella Storia.** Fino al 2026-09-27 il banner prendeva
«il primo ERROR della pagina della Storia», che era ordinata per gravità. Da
quel giorno la Storia è la lista a catalogo `vendite.giornale`, ordinata dal
preset (`quando desc`) o dall'operatore: il banner avrebbe taciuto appena
l'errore fosse scivolato fuori dalla pagina — un documento in errore che a
video sembra sano, senza nessun errore.

- Lettore: `VenditeRepository.get_giornale_errore_vivo` — lo **stesso corpo**
  `_list_giornale` della Storia (una pagina da una riga, `gravita = 'ERROR'`
  esatto, ritirate escluse), quindi stessa decodifica e stessa regola sulle
  ritirate. ⚠️ La gravità `NULL` resta fuori: è il segnale di un vincolo
  allargato, non un errore del documento.
- ⛔ **Non è una capability** (non dice cosa si può *fare*, dice com'è il
  documento): per questo non sta sotto `capabilities` ma accanto agli altri
  satelliti, **dopo** il cancello della testata — la vista è `security_invoker`.

### `contatori` — i badge senza un secondo round-trip

`contatori` alimenta i badge della barra azioni del drawer. Oggi una sola voce,
`note`: il sub-drawer note è separato e il padre non ne carica la lista, quindi
senza questo campo il badge costerebbe una seconda chiamata all'apertura di ogni
fattura — cioè l'opposto del principio di questo endpoint.

È un **dict e non uno scalare** `note_count` per reggere i prossimi contatori
(documenti generati, allegati) senza cambiare la shape della risposta.

Due punti di merito:

1. **Conteggio dopo il cancello.** `vendite.note_fatture` non ha RLS: un
   `COUNT(*)` su una fattura fuori scope risponderebbe («esiste e ha N note»).
   Non lo fa solo perché il guard di testata ha già chiuso con 404. Presidiato
   da `test_note_non_contate_se_testata_none`.
2. **Stesso perimetro della lista note.** Il conteggio usa
   `PartitionedNoteRepository.count_for_parent`, che non filtra su `visibile` —
   come la lista note esposta dall'API (`include_invisible=True` di default).
   I due numeri coincidono, quindi il badge **non salta** quando il frontend lo
   aggiorna col totale che il sub-drawer restituisce dopo un salvataggio.

> Le istanze repository delle 6 partizioni note vivono in
> `apps/vendite/db/note_repositories.py` (e non nella view): i parametri di
> partizione sono un fatto di accesso ai dati, e un service non può importare da
> `api/` senza invertire i layer.

### Cose che il modello NON ha (e che il consumer non deve aspettarsi)

- **Nessuno sconto di testata**: `sconto_tot` non è una colonna di
  `vendite.fatture`. Lo sconto vive solo per riga (`sconto_percentuale`).
- **La «data scadenza» non è un campo di testata**: è una o più rate in
  `vendite.fatture_scadenze`. Il frontend ne mostra una sintesi (prossima rata
  per data + piano completo in popover, BB `ScadenzeSintesi`).
- **Nessuna imputazione incasso → rata.** `vendite.fatture_scadenze` non ha
  stato di pagamento e `pagamenti.vendite_movimenti` è legato a `fattura_id`,
  **non** a una scadenza: il residuo si conosce solo per fattura
  (`pagamenti.fn_get_saldo_fattura` = `totale_a_pagare − movimenti attivi`).
  Conseguenza per il consumer: **«quale rata è stata pagata» non è una domanda
  a cui il modello sa rispondere.** Su una fattura a 3 rate con un incasso
  parziale non si può dire se il cliente ha saldato la prima o versato un
  acconto sulla terza — quindi niente stati «insoluta/scaduta» derivati dalle
  sole date, che su una fattura già incassata sarebbero falsi. Se servirà
  davvero (solleciti, scadenzario), il prerequisito è **DB**: una imputazione
  incasso→scadenza, non un calcolo applicativo.
- **Una fattura in DRAFT ha `numero` NULL**: il progressivo si assegna alla
  numerazione fiscale. ⚠️ E non solo in DRAFT: fra **emissione e numerazione**
  il documento è EMESSA e ancora senza numero. Un consumer che rende il numero
  come identità del documento deve prevedere il caso — il pannello «Passaggi»
  mostra «(non ancora numerato)», mai una stringa vuota.
- **Nessuna genealogia**: la catena dei documenti a monte e a valle **non** è
  in questa risposta. Ha il suo endpoint,
  [`/vendite/fatture/<id>/passaggi/`](api_lineage_passaggi.md), che il drawer
  chiama a parte (BB `DocumentoCollegamentiBar`, dal 2026-08-21).
  ⚠️ Da non confondere con il blocco «documenti collegati» del drawer, che
  legge `vendite.fatture_rettifiche` — l'indice documentale popolato **dopo** la
  numerazione: nella finestra fra emissione e numerazione quello è vuoto e i
  passaggi no, perché il grafo ricostruisce il legame dalle **righe**.

## Dipendenze DB

- `vendite.fatture` (+ JOIN `billing_account`, `config.tipi_doc_fiscale`,
  `stati_doc_fiscale`, `valute`, `modalita_pagamento`, `termini_pagamento`,
  `utilities`)
- `vendite.fatture_indirizzi` (riga `FATT` → `cliente_indirizzo`)
- `vendite.vw_fattura_righe_lista` (via `FattureRepository.list_righe`)
- `vendite.fatture_rettifiche`
- `vendite.fatture_riepiloghi_iva`
- `vendite.fatture_scadenze`

> **Rev. 2026-07-31 — ristampa conforme (Fase 2 satelliti).** L'intestazione
> delle due parti non si legge più dall'anagrafica viva ma dagli **snapshot
> congelati** allo step DRAFT: `emittente_denominazione`/`emittente_piva`/
> `emittente_cf`/`emittente_sede` derivano da `fatture.emittente_snapshot`;
> `ragione_sociale_completa`/`id_fiscale_univoco_cf_piva`/`ba_codice` da
> `fatture.cliente_snapshot`; `cliente_indirizzo` dalla riga `FATT` di
> `fatture_indirizzi`. Le chiavi del payload sono INVARIATE — è cambiata la
> provenienza. Cadute le JOIN su `emittenti_fiscali`,
> `vw_soggetti_ruoli_dettaglio` e `vw_indirizzi_resolved_ruolo`. Il payload
> espone in aggiunta `emittente_snapshot` e `cliente_snapshot` integrali
> (shape interno non contrattuale, brief intestazione §10.2). Una fattura
> **senza** snapshot (emessa prima della Fase 1) mostra questi campi a NULL:
> **nessun fallback** per decisione (piano BE/FE §9 — dati di test, si
> rigenerano). ⚠️ `billing_account_id`/`ba_codice` nello snapshot cliente sono
> il BA **padre** (D-P), non il conto del consumatore nelle gerarchie.
>
> ⭐ Eccezione voluta (2026-09-27): `emittente_fiscale_pk` è la PK
> dell'emittente **viva**, dalla colonna `emittente_soggetto_ruolo_id` (NOT
> NULL) via `emittenti_fiscali`, non dallo snapshot: serve al cancello di
> perimetro delle liste del drawer (i documenti generati), e in bozza lo
> snapshot può mancare. `emittente_fiscale_id` resta quello dello snapshot.

---

## Note della fattura

Sesto dominio cablato sul building block note partizionate — il contratto
comune (payload, filtri, `Idempotency-Key`, errori, permessi) sta in
[api_note_documento](../../core/manual/api_note_documento.md); qui sotto solo i delta della fattura.

- `GET/POST /api/v1/vendite/fatture/<fattura_id>/note/`
- `GET/PATCH/DELETE /api/v1/vendite/fatture/<fattura_id>/note/<note_id>/`

Partizione `vendite.note_fatture` (`FOR VALUES IN ('FATTURA')`), trigger di
validazione `trg_note_fatture_validate_ins_upd` presente: **solo cablaggio**,
nessuna migration. `FATTURA` è un codice di `config.tipi_entita` (FK del padre
`vendite.note`); fino al 2026-10-25 il backend lo ripeteva nella whitelist
`TARGET_TIPI_AMMESSI`, ritirata col lotto 3 di brief-db-grammatica-unica-documenti.

Note di riga ancorate a `vendite.fatture_righe` via `target_riga_id`.
⚠️ Le righe `KIT_PADRE` non sono ancorabili (non esistono in tabella): il
frontend le esclude dal select riga.

La nota resta scrivibile anche su fattura oltre EMESSA — il congelamento
protegge gli **importi**, non l'annotazione operativa che ci gira intorno.

## Consumer

| Consumer | Stato |
| --- | --- |
| `FatturaDrawer.vue` da kebab righe fatture del `LottoDrawer` | ✅ attivo |
| `FatturaDrawer.vue` dalle **tappe FATTURA** dei pannelli «Passaggi» degli altri domini (via `DocumentoDrawerHost`) | ✅ attivo dal 2026-07-29 |
| Dashboard Competenza, ricerca universale | possibile, nessuna modifica BE |
| Portale clienti | ✅ prerequisito RLS **chiuso** il 2026-07-29. Il cliente vede righe e riepilogo IVA delle **sole** proprie fatture, in **sola lettura** (`FOR SELECT`): niente filtri applicativi sul billing account da aggiungere, e nessun permesso di scrittura da chiedere |
