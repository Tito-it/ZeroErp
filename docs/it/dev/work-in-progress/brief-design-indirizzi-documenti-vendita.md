# Brief design — Indirizzi documento generici (pannello, tipologie, cascata)

> **Tipo**: design-of-record · **Data**: 2026-07-11 · **Owner**: Tid · **Stato**: 🟢 DECISO
> **Origine**: residuo "DdtIndirizziPanel" di [brief-fe-ddt-vendita.md](brief-fe-ddt-vendita.md) §10,
> allargato a building block generico per tutti i documenti vendita.
> **Prerequisito bloccante**: [brief-db-indirizzi-documenti-simmetria-e-cascata.md](brief-db-indirizzi-documenti-simmetria-e-cascata.md)
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
Vedi [brief-db-indirizzi-documenti-simmetria-e-cascata.md](brief-db-indirizzi-documenti-simmetria-e-cascata.md):
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

1. **Brief DB** → team DB su `dev/db-tid` (bloccante).
2. BE generico + allineamento preventivi (a DB pronto).
3. FE pannello su **DDT** (pilota: chiude il residuo del brief FE DDT) → poi montaggio
   sugli altri 4 drawer.
4. PDF: verifica che i context builder leggano gli snapshot (DDT in primis).

## 6. Fuori scope

- Indirizzi su commesse/fatturazione batch (le fatture ereditano via pipeline: la
  derivazione ordine/DDT→fattura si affronta nel cantiere fatturazione).
- Editing degli indirizzi **anagrafici** dal documento (si fa dal drawer cliente).
- Geocoding/validazione postale dello snapshot una-tantum.
