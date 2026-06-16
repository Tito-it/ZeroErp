# Piano FE — Documento dalla pratica: cliente/istanza ereditati e bloccati

> **Tipo**: piano frontend (Vue). **Prerequisito**: dato DB del
> [brief-db-pratica-preventivo-contesto-cliente.md](brief-db-pratica-preventivo-contesto-cliente.md)
> (la pratica espone `billing_account_id` derivato + `istanza_utility_id`).
> **Data**: 2026-06-15 · **Stato**: ✅ **CHIUSO (2026-06-15)** — implementato su
> `PreventiviDrawer`. Estensione a `OffertaDrawer`/`ContrattoDrawer` quando nasceranno
> i loro flussi (concentrico, non lavoro aperto).
>
> **✅ Fatto** (prereq DB consegnato, `f3c4710ca`): `PreventiviDrawer` accetta
> `praticaContext` → pre-compila istanza (+ BA se cliente attivo) e blocca **solo i
> campi passati** (non-null) da subito; `PraticheDashboard` passa il contesto via
> registry. Build+lint verdi.
>
> **🔲 Aperto**: stesso intervento su `OffertaDrawer`/`ContrattoDrawer` (quando
> nasceranno i loro flussi); se il blocco risulta identico sui 3 → estrarre
> composable `usePraticaContextLock` (regola del 2, §3.5). Smoke UI E2E.
>
> **Portata** (Tid 2026-06-15): stessa logica per i 3 documenti aperti dal flusso
> — **preventivo, offerta, contratto**. Gli ordini restano fuori (push a valle).
> Quali campi bloccare per documento arrivano da `lockFields` del registry UI
> (vedi [brief-design-attivita-ui-da-flusso-data-driven §5/§5-bis](brief-design-attivita-ui-da-flusso-data-driven.md)):
> tutti e 3 bloccano `istanza_utility_id` + `billing_account_id`.

## 1. Obiettivo

Aprendo dal flusso pratica il drawer di un documento (preventivo/offerta/
contratto), il **cliente (BA)** e l'**istanza utility** sono precompilati dal
contesto pratica e **non modificabili da subito** (non solo dopo il primo
salvataggio, come oggi). Per offerta/contratto l'azione è offerta **solo** se la
pratica ha un cliente attivo (BA presente — gating `requiresActiveClient`).

## 2. Stato attuale (verificato)

- [PraticheDashboard.vue](../../../frontend/src/pratiche/views/PraticheDashboard.vue):
  apre `<PreventiviDrawer mode="create" :pratica-id="...">` — passa **solo**
  `praticaId`, non cliente/istanza.
- [PreventiviDrawer.vue](../../../frontend/src/vendite/preventivi/components/PreventiviDrawer.vue):
  - `defaultForm()` precompila `istanza/BA` con i default globali, **non** dal
    contesto pratica;
  - `nonEditableFields` blocca `billing_account_id`/`istanza_utility_id` **solo
    da `hasDetail`** (dopo l'auto-save bozza), non dall'apertura;
  - il drawer è **BA-first** (scegli BA → istanza derivata, picker istanza
    nascosto); il caso pratica è **istanza-locked** → inversione da gestire.

## 3. Modifiche FE previste

1. **Dashboard**: oltre a `praticaId`, fornire al drawer il contesto cliente
   risolto della pratica (`billing_account_id`, `istanza_utility_id`) — dal
   dettaglio pratica arricchito (prereq DB). In alternativa, il drawer lo carica
   da sé via `praticaId`; preferibile passarlo (la dashboard ha già la pratica
   selezionata, evita una fetch).
2. **PreventiviDrawer — pre-fill**: quando il contesto pratica è presente,
   `defaultForm()` inizializza `istanza_utility_id` (+ `billing_account_id` se
   non nullo) dal contesto, valorizzando anche gli `_obj` per il restore degli
   AutoComplete ([[feedback_autocomplete_restore]]) — serve il display (codice/
   ragione sociale) dei due lookup, da includere nel dato pratica o risolvere via
   i lookup-by-id esistenti.
3. **PreventiviDrawer — lock da subito**: estendere `nonEditableFields` perché,
   quando il contesto pratica è presente, includa `billing_account_id` +
   `istanza_utility_id` **già dall'apertura** (non solo da `hasDetail`). I picker
   restano visibili ma disabilitati (mostrano il valore ereditato), coerente col
   pattern readonly-per-campo già usato.
4. **Coerenza guard**: il dato pratica (BA, istanza) deve essere una coppia che
   il documento accetta (vedi §3 brief DB), così il blocco non porta a un INSERT
   rifiutato dal guard di coerenza.
5. **OffertaDrawer / ContrattoDrawer — stesso intervento**: i punti 2-3 si
   ripetono identici sui drawer di offerta e contratto. Entrambi hanno già i campi
   `billing_account_id`/`istanza_utility_id` e il pattern readonly-per-campo
   (`nonEditableFields` / capability BE) — **da verificare** la simmetria col
   PreventiviDrawer prima di replicare (regola del 2: se il blocco "pre-fill+lock
   da contesto pratica" è identico sui 3, estrarlo in un composable condiviso,
   es. `usePraticaContextLock`, dichiarando l'estrazione prima di scrivere —
   [[feedback_regola_del_2_estrai_bb]]).

## 4. In/Out scope

- **In scope**: pre-fill + lock di cliente/istanza nei drawer
  preventivo/offerta/contratto aperti dalla pratica.
- **Out**: i percorsi autonomi (documento da menù) restano invariati — pre-fill e
  lock scattano **solo** col contesto pratica.
- **Out**: politica di fatturazione (immediata/differita) — già gestita altrove
  (handler a CONFERMA / config), non c'entra con questo piano.

## 5. Test (smoke UI, alla consegna prereq)

- Apri preventivo da pratica con istanza+BA → i due campi sono valorizzati e
  disabilitati; salvataggio bozza OK, nessun errore di coerenza.
- Apri preventivo da pratica prospect (BA assente) → istanza valorizzata e
  bloccata, BA vuoto (ammesso); salvataggio OK.
- Apri preventivo autonomo (da menù) → campi liberi come oggi (nessuna
  regressione).
