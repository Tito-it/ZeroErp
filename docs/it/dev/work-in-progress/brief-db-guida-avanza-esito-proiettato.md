# Brief DB — GUIDA (D4): avanzamento milestone su esito proiettato

> **Tipo**: brief DB (spec per il team DB, ramo `dev/db-tid`) · **Data**: 2026-07-06 · **Owner**: Tid
> **Design-of-record**: [brief-design-guida-avanza-esito-proiettato.md](brief-design-guida-avanza-esito-proiettato.md)
> (decisioni adottate §11). **Prerequisito MOSTRA** (D1-D3) già in produzione per PREVENTIVI.
> **Gate implementazione**: dopo validazione E2E in-app di MOSTRA (non blocca il lavoro DB di design/seed su PREVENTIVI).
>
> Il team DB possiede la **DDL esatta** (nomi, tipi, indici, trigger, pgTAP). Questo brief fissa
> **semantica, invarianti e criteri d'accettazione**, non la forma fisica. **Additivo e per-dominio**:
> senza config, comportamento di oggi (nessun avanzamento automatico).

---

## 0. Scopo in una riga

Quando un **documento** raggiunge un **verdetto proiettato** (`fn_stato_sorgente.esito` non-null,
un `is_verdetto=true`), il **milestone** della pratica che *attende* quel documento deve
**avanzare automaticamente** — su **qualsiasi** percorso di scrittura (BE, batch, SQL diretto e
soprattutto **standalone**). Generalizza e **rimpiazza** l'handler per-dominio
`vendita.accetta_preventivo`.

## 1. Contesto (cosa esiste già — non ricrearlo)

- `pratiche.fn_stato_sorgente(sorgente_tipo_id, sorgente_uid)` → descrittore normalizzato
  (`risolto, fase, esito, terminale, …`); `esito` è **sempre** un verdetto (`is_verdetto=true`) o NULL.
- `script.vw_pratica_doc_sorgente` → àncora pratica-level (accende anche i COLLEGATO con
  `flusso_id` NULL).
- `pratiche.pratiche_sorgenti(pratica_id, sorgente_tipo_id, sorgente_uid, ruolo_link, flusso_id, …)`
  → link pratica↔documento.
- `config.sorgenti(id, target_table regclass, key_selector 'id'|'uid', …)` → registry dei tipi
  sorgente (polimorfismo per la risoluzione dell'uid).
- Avanzamento flusso: la primitiva applicativa è `completa_step_pratica(pratica_id, template_codice,
  esito, user)` (idempotente sui flussi terminali). Il completamento fa `UPDATE pratiche.flussi
  SET stato_id=…(COMPLETATO), esito=…` che **già** fa scattare il trigger DB
  `trgfn_flussi_generazione` (generazione a valle). **Nota**: l'avanzamento GUIDA gira **DB-side**
  → deve replicare lo stesso effetto (transizione a COMPLETATO con l'esito), così la generazione
  a valle scatta come sempre.
- Vocabolario esito: `config.esiti_flussi_pratiche`. Il `esito_richiesto` dei binding e il `esito`
  proiettato sono **entrambi** ristretti ai 4 verdetti → match omogeneo.

## 2. Deliverable

### G1 — Mappa step → sorgente attesa
**Cosa**: dichiarare, sul **template step** (`pratiche.template_flussi`, versionato per definizione),
quale **tipo sorgente** quel milestone attende. Additiva.
- Semantica: `attende_sorgente_tipo_id` (FK → `config.sorgenti.id`, **nullable**; NULL = milestone
  non projection-driven → comportamento di oggi).
- **Deve essere copiata** da `fn_copia_definizione` (fork / nuova-versione): è config di step,
  segue l'edizione. Verificare che la funzione di copia la propaghi.
- Risolve l'ambiguità "quale documento per quale step" anche per i COLLEGATO con `flusso_id` NULL
  (l'àncora per-flusso non basta; la mappa step→sorgente + `vw_pratica_doc_sorgente` sì).

### G2 — Binding di avanzamento *(dedicato, leggero)*
**Cosa**: dichiarare *quando* il milestone avanza sul verdetto proiettato. **Dedicato** (separato
da `template_flussi_handler_eventi`: semantica diversa, non sovraccaricare `chk_tfhe_evento`).
- Semantica minima per riga: `(template_flusso_id, esito_richiesto)` con
  **`esito_richiesto` nullable = "qualsiasi verdetto"**; l'esito di **completamento** del milestone
  = **il verdetto proiettato** (mappatura 1:1, i vocabolari coincidono → nessun remap).
- `esito_richiesto` (se valorizzato) ∈ 4 verdetti (stesso CHECK di `chk_flussi_esito`).
- **Additiva**: senza binding, nessun avanzamento automatico.
- *(Il team valuti se G1+G2 collassano in poche colonne su `template_flussi` o in una tabellina
  dedicata `pratiche.template_flussi_avanzamento_proiezione`; la semantica sopra è vincolante,
  la forma fisica no.)*

### G3 — Detection (trigger generico) + riconciliazione `fn_reconcile_sorgente`
**G3a — `pratiche.fn_reconcile_sorgente(sorgente_tipo_id bigint, sorgente_uid text)`** (SECURITY DEFINER):
1. `d := fn_stato_sorgente(tipo, uid)`; se `d.esito IS NULL` (nessun verdetto) → esci (no-op).
2. Trova le `pratiche_sorgenti` agganciate a `(tipo, uid)`.
3. Per ciascuna pratica, trova i suoi flussi il cui **template step** ha `attende_sorgente_tipo_id
   = tipo` (G1) **e** un binding G2 con `esito_richiesto IS NULL OR = d.esito`.
4. Per quei flussi **non terminali**, transizione a **COMPLETATO con `esito = d.esito`**
   (stesso effetto di `completa_step_pratica` → fa scattare `trgfn_flussi_generazione`).
   **Idempotente** sui terminali (no-op).
5. Scrive il **giornale `DOMINIO_*`** (audit) come fa oggi il percorso accetta — riusando il
   frammento condiviso (debito §5.3): risoluzione ROOT/sorgenti + scrittura giornale.
- **Contesto SISTEMA**: l'avanzamento è automatico → RLS/audit come processo di sistema
  (coerente col pattern batch RLS Path A / `system_process_context` lato BE se invocata da lì).

**G3b — Trigger DB generico** sulla **colonna-stato** delle tabelle documento (per-dominio, seed):
- Fa scattare `fn_reconcile_sorgente(tipo, uid)` **dopo** un cambio-stato del documento
  (AFTER UPDATE OF <colonna_stato>). Generico e parametrico (stile `dbops.trgfn_*`): risolve
  `sorgente_tipo_id` (dal mapping `config.sorgenti.target_table`) e `sorgente_uid`
  (dal `key_selector` id|uid) della riga.
- **Best-effort — vincolo critico**: il documento è **sovrano**. La logica di reconcile deve
  essere racchiusa in un **blocco eccezioni interno** (`BEGIN … EXCEPTION WHEN OTHERS THEN
  <log>; END`) così che **un errore lato pratiche non propaghi mai** e **non faccia rollback** del
  cambio-stato del documento. Loggare l'errore (tabella log job/errori) per osservabilità, non
  abortire.
- **Pilota**: **PREVENTIVI** (`vendite.preventivi`, ROOT con `flusso_id`); poi OFFERTA.

### G4 (roll-out perf) — Indice a espressione per la pushdown del resolver
- La `LEFT JOIN LATERAL` di `vw_stato_sorgente` confronta `sorgente_uid` (text) con la chiave
  nativa castata (`preventivi.uid::text`) → il predicato **non** usa il btree su `uid`.
  Aggiungere un **indice a espressione** `((uid::text))` sulla tabella-documento **per ciascun
  dominio** man mano che entra nel roll-out (nota-roll-out (a), review 2026-07-02).
  *(La nota (c) — àncora condivisa `vw_pratica_doc_sorgente` — è **già fatta**; la (b) — COLLEGATO
  senza `flusso_id` — è risolta da G1 + àncora pratica-level, senza forzare `flusso_id`.)*

## 3. Invarianti / criteri d'accettazione (pgTAP)

1. **Standalone → avanza**: preventivo (ROOT di una pratica) portato ad ACCETTATO **dal suo
   percorso standalone** (fuori pratica) → il flusso milestone che lo attende risulta COMPLETATO
   con esito POSITIVO. *(È il cuore di GUIDA: prima restava aperto.)*
2. **In-pratica → avanza**: stessa transizione fatta in-pratica → stesso esito (i due percorsi
   convergono).
3. **Idempotenza**: reconcile ripetuto (o doc che ritocca lo stato) → nessun doppio avanzamento,
   nessun errore (no-op sui terminali).
4. **Documento sovrano (best-effort)**: se il reconcile fallisce (es. vincolo pratiche), il
   cambio-stato del **documento** **persiste** comunque (nessun rollback); l'errore è loggato.
5. **Additività**: step senza `attende_sorgente_tipo_id`/binding → **nessun** avanzamento
   automatico (comportamento di oggi immutato).
6. **Nessun verdetto → no-op**: doc che proietta `esito IS NULL` (es. EMESSO) → nessun avanzamento.
7. **Copia edizione**: `fn_copia_definizione` propaga G1/G2 alla nuova edizione (fork /
   nuova-versione).
8. **Generazione a valle**: l'avanzamento GUIDA fa scattare `trgfn_flussi_generazione` come il
   completamento manuale.

## 4. Fuori scope (BE, dopo il DB)

- Ritiro di `vendita.accetta_preventivo` (il pulsante «Accetta» in-pratica → servizio standalone
  del doc; il milestone avanza per proiezione). Rimozione del binding handler dedicato.
- Estrazione del frammento condiviso ROOT/sorgenti + giornale (debito §5.3) se serve anche lato BE.
- Seed dei binding G1/G2 per il tipo prestazione PREVENTIVI (config di dominio).

---

*A chiusura: aggiornare §11/§8-D4 del design-of-record e la nota GUIDA in
[brief-design-proiezione-stato-dominio.md](brief-design-proiezione-stato-dominio.md).*
