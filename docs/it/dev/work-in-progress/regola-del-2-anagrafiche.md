# Regola del 2 — caccia duplicazioni nel dominio Anagrafiche

> **Data analisi:** 2026-06-03
> **Ambito:** **backend + frontend** del dominio `anagrafiche`
> (`backend/apps/anagrafiche/` + `frontend/src/anagrafiche/`)
> **Profondità:** media
> **Stato:** 🟡 **APERTO — report / mappa di lavoro.** Nessuna estrazione è
> stata fatta. Il documento serve a decidere *se* e *cosa* estrarre, un pezzo
> alla volta, secondo la "regola del 2" (alla seconda occorrenza di uno schema
> si estrae un building block invece di duplicare).

Replica del controllo già fatto su vendite
([regola-del-2-vendite.md](../work-done/regola-del-2-vendite.md)), questa volta
esteso anche al backend perché qui è la superficie maggiore (service /
repository / api) e la regola del 2 morde su helper inline, validator e
resolver — non solo su componenti FE.

## Com'è stata fatta l'analisi

Sweep multi-angolo: 6 agenti di ricerca in parallelo, ciascuno con un angolo
diverso (BE service/validator, BE repository/db, BE api/view, FE
component/drawer, FE store/api, pattern noti del progetto). Hanno prodotto **36
candidati grezzi**. Ogni candidato è poi passato a un **agente "scettico"** che
ha aperto i file alle righe indicate per stabilire se fosse una **vera
duplicazione** o solo una somiglianza apparente. Gli agenti avevano in contesto
i cataloghi BB (BE e FE) per non riproporre estrazioni già fatte.

Come per vendite, il dato importante non è solo "cosa estrarre" ma soprattutto
**cosa NON toccare**: molti pezzi si somigliano nella *forma* (stessa topologia
di drawer, stesso skeleton di lista paginata) ma risolvono problemi diversi, e
unificarli peggiorerebbe la leggibilità.

| | Conteggio |
|---|---|
| Candidati grezzi | 36 |
| Verificati (dopo dedup) | 35 |
| **Confermati duplicazione reale** (al netto delle ri-segnalazioni dello stesso candidato) | **9** |
| Scartati come falsa duplicazione | la maggioranza (~20 temi distinti) |
| Scoperte collaterali (debiti, non duplicazioni) | 2 |

> **Nota di metodo.** Lo sweep multi-angolo ha ri-segnalato alcuni candidati da
> più finder (es. drawer Cliente/Fornitore segnalato 4 volte, store factory 2
> volte con verdetti opposti, lista paginata sia a livello repo sia a livello
> view). Qui sono **consolidati** in un'unica voce con il verdetto risolto. Due
> punti caldi (store factory, `qp_bool_optional` reinventato) sono stati
> ri-verificati a mano sul codice attuale prima di scrivere questo report.

---

## 🟢 Candidati puliti — estrazione consigliata, basso rischio

Occorrenze quasi identiche, differenze trascurabili. È qui che la regola del 2
si applica nel modo più netto.

### V1. Contatto inline (validazione + creazione) — clienti vs fornitori

Lo stesso blocco "classifica payload contatto → se PARTIAL solleva
`E_CONTATTO_INCOMPLETO` → se VALID crea via `crea_contatto` con gli stessi 8
parametri nominativi" è **byte-identico** in due service:

- [clienti_service.py:342-365](../../../../backend/apps/anagrafiche/services/clienti_service.py#L342-L365)
- [fornitori_service.py:135-158](../../../../backend/apps/anagrafiche/services/fornitori_service.py#L135-L158)

Stesso `classify_contatto_payload`, stesso error code, stessa signature. Unica
differenza: il service proprietario. Riconducibile al pattern documentato
`feedback_classify_payload_three_state`.

**Idea di estrazione:** helper condiviso
`anagrafiche/services/contatti_inline_service.py` →
`process_contatto_inline_and_validate(soggetto_id, soggetto_ruolo_id, contatto_data, sogg_repo)`
(EMPTY→noop, PARTIAL→errore, VALID→crea). Sostituisce ~20 righe in entrambi.

### V2. `get_or_create_ruolo_*` — clienti / fornitori / emittenti (repository)

Tre metodi con firma identica che delegano alla **stessa** funzione DB
`script.fn_get_or_create_soggetto_ruolo`, variando solo il codice ruolo
(`'CL'` / `'FO'` / `'EF'`):

- [clienti_repository.py:54-60](../../../../backend/apps/anagrafiche/db/clienti_repository.py#L54-L60)
- [fornitori_repository.py:36-42](../../../../backend/apps/anagrafiche/db/fornitori_repository.py#L36-L42)
- [emittenti_fiscali_repository.py:57-63](../../../../backend/apps/anagrafiche/db/emittenti_fiscali_repository.py#L57-L63)

Sovrapposizione 100%, **3 occorrenze**. Esecuzione, guard (`assert row`) e
ritorno identici.

**Idea di estrazione:** helper modulo-level
`anagrafiche/db/_soggetto_ruolo_helpers.py` →
`get_or_create_soggetto_ruolo(soggetto_id, ruolo_codice)`; i tre repository
diventano wrapper di una riga.

### V3. PATCH di dettaglio con `handle_post_json` + lambda — geo views

Pattern identico `handle_post_json(request, handler=lambda p: GeoService().update_*(pk, p))`,
puramente generico (la lambda cattura `pk` dal closure e delega):

- [views_indirizzi.py:89-90](../../../../backend/apps/anagrafiche/api/views_indirizzi.py#L89-L90)
- [views_regioni.py:75-76](../../../../backend/apps/anagrafiche/api/views_regioni.py#L75-L76)
- [views_province.py:77-78](../../../../backend/apps/anagrafiche/api/views_province.py#L77-L78)

**Idea di estrazione:** helper in `apps/core/api/endpoint_helpers.py` →
`generic_detail_patch_handler(service_instance, method_name, pk)` che ritorna
l'handler. Da valutare se il guadagno (3 lambda → 1 chiamata) vale il livello
d'indirezione: candidato netto ma marginale.

### V4. `onDrawerSaved` — ClientiView vs FornitoriView (FE)

Handler identico al 100%: reset offset → `await fetchList` → se create+id apri
edit, altrimenti chiudi.

- [ClientiView.vue:93-102](../../../../frontend/src/anagrafiche/views/ClientiView.vue#L93-L102)
- [FornitoriView.vue:53-61](../../../../frontend/src/anagrafiche/views/FornitoriView.vue#L53-L61)

**Idea di estrazione:** composable
`frontend/src/core/composables/useDrawerSavedListRefresh.js`.

---

## 🟡 Candidati validi ma con un "ma" — estrazione possibile, serve attenzione

Duplicazione reale, ma con differenze da gestire con cura: estrarre senza
pensarci rischia di nascondere comportamenti diversi o perdere protezioni.

### G1. Store factory Pinia CRUD — clienti / fornitori / soggetti (+ articoli) — **gravità ALTA**

Il candidato più sostanzioso. Quattro store implementano lo **stesso** pattern
CRUD lista (state `items/totalRecords/loading/hasSearched/filters`, `fetchList`
con vincolo min 3 char, `fetchDetail` con `res.data.data`, `create`/`update`
con `emitDataChanged`). Sovrapposizione ~95%, varia solo il set di filtri:

- [stores/clienti.js:9-99](../../../../frontend/src/anagrafiche/stores/clienti.js#L9-L99)
- [stores/fornitori.js:9-99](../../../../frontend/src/anagrafiche/stores/fornitori.js#L9-L99)
- [stores/soggetti.js:11-102](../../../../frontend/src/anagrafiche/stores/soggetti.js#L11-L102)
- [catalogo/stores/articoli.js:8-107](../../../../frontend/src/catalogo/stores/articoli.js#L8-L107) (conferma che il pattern è cross-dominio)

**Idea di estrazione:** factory `frontend/src/core/composables/useCrudListStore.js`
parametrizzata su `storeName`, `apiMethods` (`{listFn, detailFn, createFn, updateFn, ...extras}`),
`tabEntityType`, `defaultFilters`, `extraMethods` (articoli aggiunge `disattiva`/`riattiva`).

> **⚠️ "ma" verificato a mano.** Lo store
> [stores/indirizzi.js](../../../../frontend/src/anagrafiche/stores/indirizzi.js)
> **diverge**: non ha `fetchDetail` (espone solo `fetchList/create/update`) e
> usa filtri diversi. Va **escluso** dalla factory o gestito come variante
> "senza dettaglio" — non forzato dentro il contratto comune. Per questo è 🟡 e
> non 🟢: la factory deve modellare la presenza/assenza opzionale di
> `fetchDetail`. Collegato a `feedback_pinia_userscoped` (ricordarsi il flag
> `userScoped` se la factory tocca dati utente).

### G2. Estrazione campi opzionali payload (`_extract_*_data`) — fornitori vs emittenti

Stesso pattern iterativo "loop su liste hardcoded di campi + include
condizionale via `optional_*`":

- [fornitori_service.py:172-204](../../../../backend/apps/anagrafiche/services/fornitori_service.py#L172-L204) (16 campi)
- [emittenti_fiscali_service.py:129-153](../../../../backend/apps/anagrafiche/services/emittenti_fiscali_service.py#L129-L153) (6 campi)

**Idea di estrazione:** `anagrafiche/services/payload_extractors.py` →
`PayloadFieldExtractor.extract_optional_fields(payload, field_specs={"int_fks":[], "bools":[], "strings":[], "numeric":[], "dates":[]})`.

> **⚠️ "ma":** sono **solo 2 occorrenze reali** (regola del 2 al limite). I due
> candidati `categorie_clienti_service.py` e `categorie_clienti_listini_service.py`
> citati dallo sweep **NON** appartengono allo stesso schema (uno è
> required+optional, l'altro ha cross-field validation `valido_al >= valido_dal`):
> vanno lasciati fuori. Rischio di astrazione prematura se uno dei due diverge —
> dichiarare il disegno e valutare con Tid prima di scrivere.

### G3. `get_*` con guard "not found" (`ErrorManager.require`) — clienti vs fornitori

`entity = repo.get(id); ErrorManager.require(entity is not None, ...); assert; return`
identico:

- [clienti_service.py:100-105](../../../../backend/apps/anagrafiche/services/clienti_service.py#L100-L105)
- [fornitori_service.py:77-82](../../../../backend/apps/anagrafiche/services/fornitori_service.py#L77-L82)

**Idea di estrazione:** helper
`get_entity_require(repo_get_fn, entity_id, error_code, error_message)` (in
`apps/core/services/` o mixin di service).

> **⚠️ "ma":** [categorie_clienti_service.py:119-129](../../../../backend/apps/anagrafiche/services/categorie_clienti_service.py#L119-L129)
> segue lo stesso schema ma aggiunge `guard_positive_int` e `context={...}` →
> **non** rientra nello stesso BB, va tenuto locale.

### G4. Mappatura `IntegrityError` in create — fornitori / emittenti vs clienti — **rischio bug latente**

Fornitori ed emittenti usano `create_with_dedup(...)` che converte **qualsiasi**
`IntegrityError` in un messaggio di duplicato generico; clienti invece matcha il
constraint specifico (`uq_clienti_istanza_utility`) e lascia risalire gli altri:

- [fornitori_service.py:126-132](../../../../backend/apps/anagrafiche/services/fornitori_service.py#L126-L132) (tabella con 2 UNIQUE)
- [emittenti_fiscali_service.py:113-121](../../../../backend/apps/anagrafiche/services/emittenti_fiscali_service.py#L113-L121) (tabella con 3 UNIQUE)
- [clienti_service.py:332-339](../../../../backend/apps/anagrafiche/services/clienti_service.py#L332-L339) (matching esplicito — comportamento corretto)

> **⚠️ Segnalazione (cfr. `feedback_bug_logici_modello`):** l'approccio generico
> di fornitori/emittenti **maschera** una violazione su `codice` (o altra
> colonna UNIQUE) come "duplicato per soggetto" → messaggio fuorviante per
> l'utente. Da verificare/discutere prima dell'estrazione.

**Idea di estrazione:** unificare i tre nel pattern di clienti tramite
`handle_integrity_error_on_create(fn, entity_name, constraint_mappings, re_raise_unmapped=True)`
in `anagrafiche/services/_validators.py` (mappatura per-constraint + fall-through
dei vincoli non mappati).

### G5. `_create_indirizzi_ruolo` — coesione mal posta (non vera duplicazione di codice)

[fornitori_service.py:214-283](../../../../backend/apps/anagrafiche/services/fornitori_service.py#L214-L283)
contiene la logica completa di creazione indirizzi-per-ruolo con auto-clone;
clienti **non la duplica** ma la richiama istanziando `FornitoriService`
([clienti_service.py:370](../../../../backend/apps/anagrafiche/services/clienti_service.py#L370)).
Non è quindi duplicazione di codice, ma uno **smell di coesione**: una
operazione di dominio `soggetto_ruolo` vive in `FornitoriService` e clienti la
raggiunge con un accoppiamento improprio (un service che ne istanzia un altro).

**Idea:** spostare in `SoggettiService` (o in un builder condiviso
`_indirizzi_ruolo_builder.py`) con `tipo_ruolo_codice` parametrico; clienti e
fornitori la richiamano dal posto giusto. Priorità bassa, ma elimina
l'accoppiamento.

---

## 🔴 Casi confermati ma da NON estrarre (falsa duplicazione)

Codice che si somiglia nella forma ma risolve problemi diversi: unificarlo
peggiorerebbe la leggibilità. La verifica avversariale ha aperto i file e
confermato la divergenza.

- **`resolve_filtri_export_label`** (clienti/fornitori/soggetti service) — è il
  *plug-in* domain-specific sopra la coda comune già estratta
  (`build_export_response`, 2026-06-02). Parametri e lookup ortogonali
  (utilities vs stati_cliente vs stati_fornitore vs tipi_soggetto). Generalizzare
  perderebbe type-safety.
- **`list_*` paginata** a livello **repository** *e* **view** (clienti/fornitori/
  soggetti/emittenti) — skeleton SQL/parsing comune ma divergenze profonde:
  scope emittente presente solo in clienti/soggetti, fornitori legge da vista
  materializzata, soggetti fa post-processing `jsonb_agg`. Un `GenericListRepository`
  nasconderebbe questi vincoli.
- **`create_entita`** (dynamic INSERT, clienti/fornitori/emittenti repo) — pattern
  tecnico standard, ma special-expressions e cardinalità colonne (6/14/15)
  radicalmente diverse.
- **`update_entita`** (`_UPDATE_ALLOWED`/`_NULLABLE`, soggetti/fornitori/emittenti
  repo) — soggetti ha alias-mapping e PK UUID con cast; gli altri no.
- **`update_*`** service (clienti vs fornitori) — clienti orchestra logica
  BA/categoria specifica.
- **Parsing param lista** (`optional_int`) su 9 view, **envelope `{"results": ...}`**,
  **parsing query opzionali** (billing_account vs istanze_utility) — convenzioni
  standard di API, non duplicazione di logica.
- **Drawer Cliente vs Fornitore** (segnalato 4 volte: handler soggetto, reset/
  populate, `buildEditablePayload`, watch su `visible`) — topologia di drawer
  identica ma schemi form, composable (`useUtilityDefaultId`/`useLookup` vs
  `useCodiceField`) e flussi BA-driven completamente diversi. **Falso positivo
  classico della regola del 2**: stessa forma, classi di problema diverse.
- **Orchestrazione sotto-drawer nelle View** (Clienti/Fornitori/Soggetti) —
  ClientiView gestisce `istanzaUtilityId` e `contrattiDrawer` che gli altri non
  hanno.
- **`*SearchTable`** (Clienti vs Fornitori) — lo scaffolding vero è **già**
  estratto in `useListaConfigurabilePage` (2026-06-02); il residuo è filtri/
  azioni entity-specific.

---

## ⚠️ Scoperte collaterali (debiti, non duplicazioni regola-del-2)

Emerse durante lo sweep, **verificate a mano**. Non sono duplicazioni tra due
siti, ma vale la pena annotarle:

1. **`views_fornitori.py` reinventa un BB core già esistente.** Il parsing inline
   di `attivo` in [views_fornitori.py:61-64](../../../../backend/apps/anagrafiche/api/views_fornitori.py#L61-L64)
   è **byte-identico** a `qp_bool_optional`
   ([core/api/payload_validators.py:25-28](../../../../backend/apps/core/api/payload_validators.py#L25-L28)).
   Il commento nel codice cita `optional_bool` (che ha `default=False`) senza
   accorgersi che `qp_bool_optional` esiste e fa esattamente quello che serve.
   **Fix:** importare e usare `qp_bool_optional`. Debito a basso rischio, alto
   valore di pulizia.

2. **Caricamento "fantasma" in ClienteDrawer.** `indirizziSoggetto` /
   `loadIndirizziSoggetto` ([ClienteDrawer.vue:188-197](../../../../frontend/src/anagrafiche/components/ClienteDrawer.vue#L188-L197))
   è dichiarato e caricato via API ma **non usato nel template** (nessun `Select`
   lo consuma): residuo di un refactor precedente. Da verificare e rimuovere se
   confermato morto.

---

## Come procedere (proposta)

Nessuna estrazione è stata fatta. Per ogni candidato vale il protocollo della
regola del 2 (`feedback_regola_del_2_estrai_bb`): **dichiarare a chat il disegno
del BB e attendere l'OK di Tid** prima di scrivere codice astratto.

Ordine suggerito per rischio/valore crescente:

1. **Debito #1** (`qp_bool_optional`) — fix immediato, zero controindicazioni.
2. **V2** (`get_or_create_ruolo_*`) e **V1** (contatto inline) — 🟢 netti.
3. **V4** (`onDrawerSaved`) — 🟢 FE netto.
4. **G1** (store factory) — 🟡 ma **gravità alta** per impatto: gestire
   l'esclusione di `indirizzi.js` (variante senza `fetchDetail`).
5. **G4** (IntegrityError) — prima **decidere** sul bug di mascheramento, poi
   estrarre.
6. **G2/G3/G5** — caso per caso, attenzione ai caveat di astrazione prematura.
7. **V3** (PATCH lambda) — marginale, valutare se il guadagno vale l'indirezione.
