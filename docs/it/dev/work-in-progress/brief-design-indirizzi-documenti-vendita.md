# Brief design — Indirizzi documento generici (pannello, tipologie, cascata)

> **Tipo**: design-of-record · **Data**: 2026-07-11 · **Owner**: Tid
> **Stato**: 🟢 IN CORSO — DB ✅ + BE 5 domini ✅ + FE pilota DDT ✅ + review/hardening ✅ (2026-07-12).
> Aperti: montaggio pannello sugli altri 4 drawer, PDF context builder, form una-tantum evoluto.
> **Origine**: residuo "DdtIndirizziPanel" di [brief-fe-ddt-vendita.md](../work-done/brief-fe-ddt-vendita.md) §10,
> allargato a building block generico per tutti i documenti vendita.
> **Prerequisito bloccante**: [brief-db-indirizzi-documenti-simmetria-e-cascata.md](../work-done/brief-db-indirizzi-documenti-simmetria-e-cascata.md)
> (team DB su `dev/db-tid`). BE/FE partono solo a DB consegnato.

---

## 1. Problema

Il modello DB indirizzi-documento esiste già ed è quasi simmetrico (4 tabelle identiche:
`preventivi_indirizzi`, `ordini_indirizzi`, `fatture_indirizzi`, `ddt_indirizzi` — snapshot
JSONB + `origine_indirizzo_id`/`origine_soggetto_ruolo_id`, UNIQUE uno-per-tipo, trigger
whitelist per ambito). Ma sopra il DB non c'è quasi nulla:

- **BE**: solo PREVENTIVI ha GET/POST indirizzi, e l'upsert accetta lo `snapshot` così
  com'è dal client (nessuna derivazione da `origine_indirizzo_id`).
- **Derivazione a cascata**: inesistente — né alla creazione, né al push
  preventivo→ordine→DDT.
- **FE**: nessun pannello in nessun drawer; nessun picker "indirizzi del cliente".
- **Tipologie**: `config.tipi_indirizzi_allowed` mai seedata → si vive del fallback
  hardcoded nel trigger, con codici duplicati (SPED vs CON) che rendono impossibile la
  copia 1:1 lungo la catena (il preventivo ammette SPED, l'ordine solo CON).

## 2. Decisioni (chiuse con Tid, 2026-07-11)

| # | Decisione |
|---|---|
| **D-1** | **Derivazione al push, nelle funzioni madre DB** (preventivo→ordine, ordine→DDT evasione, offerta→ordine/contratto): copia degli snapshot dal documento sorgente, filtrata sui tipi ammessi a valle. Il FE non deriva nulla. |
| **D-2** | **Unificazione codici: `CON` è l'unico codice "dove va la merce"**. `SPED` viene ritirato dalle whitelist documento (e dai fallback trigger). Niente tabella di mappatura tra ambiti: la cascata diventa copia semplice filtrata. |
| **D-3** | **Simmetria piena subito**: si aggiungono `offerte_commerciali_indirizzi` e `contratti_indirizzi` con struttura identica alle 4 esistenti (niente "fase 2"). |
| **D-4** | **Indirizzo una-tantum ammesso**: snapshot senza `origine_*` (es. consegna occasionale non censita in anagrafica). Il BE valida la struttura; il FE offre il form geografico riusando i composable esistenti. |
| **D-5** | **Snapshot composto server-side, mai dal client**: funzione DB unica `fn_snapshot_indirizzo(indirizzo_id)` (shape canonico del JSONB) usata sia dalle funzioni di push sia dall'endpoint BE. Il FE nel caso standard manda solo `{tipo_indirizzo_id, origine_indirizzo_id}`. Va allineato anche l'upsert PREVENTIVI esistente (oggi client-side: buco da chiudere). |

## 3. Flusso operatore (target)

1. Nel drawer documento, sezione "Indirizzi": una **riga per ogni tipo ammesso**
   nell'ambito (slot da `config.tipi_indirizzi_allowed`), vuota o valorizzata —
   pattern slot/override già usato per le matrici parametri.
2. Su uno slot vuoto (o "cambia"): **picker** sugli indirizzi predisposti del cliente —
   la cascata istanza→ruolo→soggetto è già esposta da `RuoloIndirizziView`
   (`indirizzo_display` pronto). L'operatore seleziona; il BE congela snapshot + `origine_*`.
3. In alternativa: "indirizzo una-tantum" → form geografico (riuso
   `useIndirizzoBase`/`useIndirizzoSoggettoForm`), snapshot senza `origine_*` (D-4).
4. Alla generazione a valle (ordine da preventivo, DDT da ordine) gli indirizzi
   **arrivano già copiati** dal push DB (D-1); l'operatore li tocca solo se deve cambiarli.
5. Documento emesso = snapshot congelato: modifiche anagrafiche non retroagiscono
   (semantica già oggi documentata, invariata).

## 4. Spacchettamento

### DB (brief separato, bloccante)
Vedi [brief-db-indirizzi-documenti-simmetria-e-cascata.md](../work-done/brief-db-indirizzi-documenti-simmetria-e-cascata.md):
simmetria offerte/contratti, unificazione CON + seed `tipi_indirizzi_allowed`,
`fn_snapshot_indirizzo`, derivazione nelle funzioni di push, fix trigger e tipi colonna, pgTAP.

### BE (brief da generare a DB consegnato)
- Service/repository **indirizzi-documento generico** parametrizzato per dominio
  (ambito, tabella, colonna FK) — stesso pattern factory del refactor documenti-views.
- Endpoint per dominio: `GET/POST/DELETE /vendite/<dominio>/<id>/indirizzi/`.
  POST standard: `{tipo_indirizzo_id, origine_indirizzo_id}` → il BE chiama
  `fn_snapshot_indirizzo` (D-5). POST una-tantum: `{tipo_indirizzo_id, snapshot}` con
  validator struttura (D-4). Allineare l'upsert PREVENTIVI esistente.
- `indirizzi` inclusi nel detail dei documenti (già così per preventivi) e nei
  context builder PDF (il builder DDT ha il TODO esplicito).
- Guard di editabilità coerente con lo stato documento (`can_edit_testata`).

### FE (brief da generare a DB consegnato)
- `_shared/indirizzi/DocumentoIndirizziPanel.vue` + `useDocumentoIndirizzi(api, docId)`
  + `makeIndirizziApi(BASE)` (gemello di `makeComponentiBomApi`).
- `IndirizzoClientePicker.vue`: select/lookup sugli indirizzi del cliente
  (API `listRuoloIndirizzi`, badge fonte istanza/ruolo/soggetto).
- Form una-tantum: riuso `useIndirizzoBase` (form geografico) in modalità snapshot.
- Montaggio nei drawer: Preventivi, Offerte, Ordini, DDT, Contratti (readonly-aware,
  prop `readonly` + `useInjectReadonly` come da standard).
- i18n `vendite.indirizzi.*` condiviso.

## 5. Ordine di lavoro

1. **Brief DB** → team DB su `dev/db-tid` (bloccante). ✅ consegnato e applicato
   (migrations `20260711-15..32`, note team recepite nel brief DB).
2. BE generico + allineamento preventivi (a DB pronto). ✅ 2026-07-12: BB
   `_indirizzi_repo_mixin` + `_indirizzi_documento_helpers` + factory
   `build_indirizzi_documento_views`; endpoint su **tutti e 5 i domini**
   (preventivi riallineati: snapshot ora server-side); guard stato per dominio;
   smoke E2E su DDT (picker/una-tantum/whitelist/guard emissione) + 1092 test.
3. FE pannello su **DDT** (pilota). ✅ 2026-07-12: `_shared/indirizzi/`
   (`DocumentoIndirizziPanel` + `DocumentoIndirizziDrawer` +
   `makeIndirizziDocumentoApi`), agganciato come azione "Indirizzi" nella
   DrawerActionsBar del DdtDrawer (sub-drawer, pattern note), i18n
   `vendite.indirizzi.*`. → resta il montaggio sugli altri 4 drawer
   (a valle della validazione in-app del pilota). **UX superseded da §7**
   (sezione inline + drawer gestione su elenco anagrafico).
4. Review critica + hardening. ✅ 2026-07-12 (8 finder, 18 finding corretti):
   **guard ownership** picker (indirizzo di altro cliente rifiutato), guard
   esistenza/stato centralizzati in `IndirizziDocumentoConfig` (404 su
   documento fantasma, NOT_FOUND su delete), traduzione errori DB uniforme
   sui 5 domini, POST via `handle_post_json`, whitelist valori scalari nello
   snapshot, `coerce_jsonb_dict` promosso in core, AppDialog/`--app-*`/
   `useInjectReadonly` nel pannello, cascata istanza nel picker
   (`istanza_utility_id`), legacy preventivi rimosso. Doc:
   `api_indirizzi_documento.md` + `api_ddt.md` + cataloghi BB aggiornati.
5. PDF: verifica che i context builder leggano gli snapshot (DDT in primis) — **aperto**.

Note aperte:

- Layer **soggetto**: gli indirizzi ereditati non hanno riga in
  `anagrafiche.indirizzi` → "usa questo" su una riga fonte=soggetto li imposta
  come snapshot senza `origine_*` (gestito in §7-F2); l'aggancio pieno
  richiederebbe la promozione a indirizzo di ruolo (eventuale evoluzione).
- Form una-tantum: oggi campi liberi (InputText); evoluzione possibile con
  `useIndirizzoBase` (autocomplete comune/stradario, CAP validato) se si vuole
  qualita' postale anche sugli indirizzi occasionali.

## 6. Fuori scope

- Indirizzi su commesse/fatturazione batch (le fatture ereditano via pipeline: la
  derivazione ordine/DDT→fattura si affronta nel cantiere fatturazione).
- Editing degli indirizzi **anagrafici** dal documento (si fa dal drawer cliente
  — ma vedi §7-F1: l'aggiunta di un NUOVO indirizzo di ruolo e' ammessa dal
  drawer di gestione, riusando il form anagrafico esistente).
- Geocoding/validazione postale dello snapshot una-tantum.

## 7. Piano di sviluppo — UX v2 (decisa con Tid 2026-07-12)

Ripensamento dell'esperienza rispetto al pilota slot-per-tipo (§5.3): il drawer
di gestione diventa un **elenco degli indirizzi del cliente** (mirror di
`IndirizziSoggettoDrawer` sul drawer ruolo) con selezione, e nel drawer
documento compare una **sezione inline col solo indirizzo di default**.
**Nessuna azione DB né BE**: si riusano gli endpoint esistenti.

Decisioni UX (chiuse):

- **Selezione → tipo**: "usa questo" imposta il tipo di default **CON**
  (Consegna, standard cross-dominio), fallback **FATT** se CON non ammesso.
  Se il dominio ammette **piu' tipi**, alla selezione compare la scelta
  *"Usa come: Consegna (default) / Fatturazione / …"* (soli tipi ammessi);
  con un solo tipo (DDT) nessuna domanda.
- **Sezione inline nel drawer documento**: mostra SOLO il default (CON, o FATT
  dove CON non e' ammesso); se mancante → avviso "indirizzo obbligatorio per
  l'emissione" e da li' scatta l'obbligo di scelta. Gli altri tipi impostati
  NON compaiono come righe: solo un contatore discreto "+N altri" (si vedono
  nel drawer di gestione). Pulsante "Indirizzi" DENTRO la sezione (via
  l'azione dalla DrawerActionsBar).
- **Emissione**: nessun disable client-side del pulsante Emetti — l'avviso in
  sezione previene, il guard DB (`E_INDIRIZZO_DOC_OBBLIGATORIO`) resta la
  fonte di verita'.

Fasi FE:

- ✅ **F1 — `IndirizziSoggettoDrawer` selezionabile** (riuso, regola del 2): prop
  `selectable` + evento `select(riga)` con azione per riga "usa questo";
  aggiunta indirizzo di ruolo gia' esistente nel componente (scrive in
  anagrafica → l'indirizzo diventa riusabile). Nessun impatto sui consumatori
  attuali (ClienteDrawer/SoggettoDrawer: prop default false).
- ✅ **F2 — `DocumentoIndirizziDrawer` v2** (orchestratore): ospita l'elenco F1
  (context ruolo, cascata istanza→ruolo→soggetto con badge fonte) + riepilogo
  degli indirizzi gia' impostati sul documento (con rimozione) + pulsante
  "Indirizzo libero" (dialog una-tantum attuale). Alla selezione: scelta
  "usa come" se serve → POST picker (`origine_indirizzo_id`) per righe
  ruolo/istanza; per righe fonte=soggetto (senza riga in
  `anagrafiche.indirizzi`) → POST snapshot dai dati mostrati (una-tantum,
  origine assente — documentato).
- ✅ **F3 — `DocumentoIndirizziSection`** (sezione inline): default compatto +
  "+N altri" + avviso mancante + pulsante "Indirizzi" che apre F2.
- ✅ **F4 — DdtDrawer**: monta la sezione F3 nel corpo (dopo il form testata),
  rimuove l'azione "Indirizzi" dalla barra azioni.
- ✅ **F5 — pulizia**: `DocumentoIndirizziPanel` slot-per-tipo superseded
  (dialog una-tantum riusato in F2); aggiornare catalogo BB FE + doc API
  (riferimenti FE).
- ✅ **F7 — rifiniture dal primo giro in-app (2026-07-12)**: "Usa" come
  colonna ESTERNA ai box (i box soggetto restano opachi/readonly ma
  selezionabili); auto-assegnazione best-effort dello slot default alla
  creazione (`auto_assegna_indirizzo_default`: indirizzo di ruolo CON →
  fallback FATT; DDT standalone + evasione); avviso "indirizzo mancante" nel
  dialog di emissione con **Conferma disabilitata** (l'emissione genera la
  stampa: senza indirizzo il PDF sarebbe scorretto; il guard DB gia' bloccava
  — verificato: nessun DDT era stato emesso senza indirizzo — ma il toast non
  era abbastanza visibile); provenienza tracciata: tag "Soggetto" (layer
  soggetto via origine_soggetto_ruolo_id, validato anti-tampering) distinto da
  "una tantum" (digitato) e "da <tipo>" (ruolo con tipo diverso dallo slot).
- ✅ **F8 — fix dal secondo giro in-app (2026-07-12)**: (a) default prop
  `tipoRuoloCodice` corretto da literal `'CLIENTE'` a `TIPO_RUOLO.CLIENTE`
  (`'CL'`) in sezione+drawer — il literal errato faceva fallire in silenzio la
  matrice tipi dell'"aggiungi indirizzo" (form vuoto); (b) cascata anagrafica a
  3 livelli completa: il detail DDT espone `istanza_utility_id` del BA (JOIN
  repository) e il DdtDrawer la passa alla sezione — senza, gli indirizzi di
  livello istanza (es. aggiunti dal ClienteDrawer/BA) restavano invisibili.
- ✅ **F9 — rollout sugli altri 4 drawer (2026-07-12)**: montata
  `DocumentoIndirizziSection` su PreventiviDrawer/OrdiniDrawer (dopo il form
  testata, con autosave-bozza: visibile a `hasDetail`) e
  OffertaDrawer/ContrattoDrawer (solo EDIT, niente autosave). Detail BE dei 4
  domini estesi con `soggetto_ruolo_id` (+ `istanza_utility_id` per ordini).
  Auto-assegnazione estesa: `crea_preventivo`, `crea_ordine` (copre anche la
  conversione da offerta) + fallback post `fn_push_preventivo_a_ordine`,
  `crea_offerta`, `create_contratto` + fallback post
  `fn_push_offerta_a_contratto` (wrapper pubblico
  `auto_assegna_indirizzo_default_contratto`). Dove la cascata DB copia dalla
  sorgente, l'helper e' solo fallback (salta se lo slot default e' pieno).
- ✅ **F10 — PDF DDT con indirizzo di consegna (2026-07-12)**:
  `DdtDocumentContextBuilder` v2 legge `ddt_indirizzi` → blocco
  `indirizzi.consegna` (slot CON, chiavi fisse per StrictUndefined +
  `display_compatto`); template 76 **versione 2 PUBBLICATA** con blocco
  "Luogo di consegna" nel box destinatario (la fn DB di pubblicazione
  auto-chiude la v1 → OBSOLETA). Verificato live: anteprima con CON stampa
  l'indirizzo, senza CON degrada (blocco omesso, niente errori). Gli altri
  4 builder restano v1 (rollout futuro, tipo per ambito da decidere).
- ✅ **F6 — verifica (2026-07-13)**: validazione in-app di Tid completata su
  DDT + i 4 drawer del rollout F9 — tutto ok. Piano UX v2 CHIUSO.
- ✅ **F11 — seconda review critica (2026-07-13, 8 finder + verifica, 10 fix)**:
  (1) ancora ownership/auto-default per dominio nel mixin
  (`_indirizzi_doc_sr_column`: DDT=destinatario, ordini=sr nativo, LEFT JOIN
  fallback BA — fixa ordine prospect BA NULL e DDT consegna-a-terzi);
  (2) snapshot picker fonte=soggetto ora include `stato` (paese, parita' col
  BE); (3) prefill "indirizzo libero" solo su veri una-tantum (non
  riclassifica piu' le righe "da soggetto"); (4) ripristinato emittente VUOTO
  in create DDT ~~(invariante PR #970)~~ — **SUPERATO 2026-07-13**: il
  riferimento a PR #970 era errato (quella PR e' il riepilogo IVA; la regola
  veniva dall'addendum §15 del brief DB DDT) e Tid ha deciso l'uniformazione
  al modello degli altri domini: **emittente legato allo USER** (prefill FE
  dal profilo + payload create, fallback DB dal BA in `trgfn_ddt_normalize`
  come rete di sicurezza). Vedi
  `work-done/brief-db-ddt-emittente-user-e-etichetta-soggetto.md`
  (CHIUSO: DB realizzato + BE recepito lo stesso giorno); (5) context PDF
  preventivi: proiezione
  stabile indirizzi (fuori le chiavi live-JOIN del drawer, hash invariato);
  (6) `E_TIPO_INDIRIZZO`+`E_INDIRIZZO_DOC_OBBLIGATORIO` registrati in
  error_policies; (7) schema OpenAPI POST factory completato
  (origine_soggetto_ruolo_id); (8) `pickTipoDefault` +
  `IndirizzoProvenienzaTags` condivisi sezione/drawer; (9) `_CONSEGNA_KEYS`
  derivata da `SNAPSHOT_KEYS_ORDERED` (fonte unica); (10) clone
  `coerce_jsonb_dict` di pratiche migrato al BB core. Rimandati (annotati):
  doppia GET sezione/drawer (refactor ownership fetch), registry
  auto-assegnazione per-dominio, semantica istanza BA-vs-documento su
  ordini/DDT (servirebbe colonna DB).
