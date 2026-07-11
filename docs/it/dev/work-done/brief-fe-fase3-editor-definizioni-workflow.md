# Brief FE — Fase 3: editor delle definizioni di workflow versionate (per emittente)

> **Tipo**: brief FE (design + slicing). · **Da**: backend/frontend agent. · **Data**: 2026-07-04.
> **Priorità**: 🟠 media (è il pezzo che rende la «configurazione emittente» completa
> **anche per l'utente**: oggi il BE è pronto ma un fork si può solo pubblicare, non
> personalizzare da UI).
> **Prerequisito**: ✅ BE completo — API documentate in
> [api_definizioni_workflow](../../backend/pratiche/manual/api_definizioni_workflow.md)
> (dettaglio + editing step/figli/archi, anelli 1-5, 40 test verdi, E2E validato).
> **Correlato**: `brief-design-workflow-definizioni-versionate.md` (design-of-record, Fase 3,
> in `work-done/`); `brief-be-fe-step-dominio-e-definizioni-versionate.md` (companion, §FE-2.4
> banner drift); tracker `analisi-pratiche-valutazione-stato.md` **V4**.
>
> **Stato (2026-07-04): ✅ FE-3.1 → FE-3.5 IMPLEMENTATI** (editor completo: ispettore
> read-only + editing step/figli/archi + drift/allinea) + controllo qualità (estrazione
> shell `CollectionEditorPanel` + composable `useEditableCollection`/`useStepOptions`,
> fix watch edit→edit, rimozione codice morto). Verificato lint + compilazione Vite; **non
> committato** (working tree). Dettaglio sotto nella tabella §4.

---

## 1. Scopo

Dare all'admin (super-admin) una UI per **ispezionare** e **modificare la struttura** di
un'edizione di workflow: step, figli per-nodo (canali/handler-eventi/competenze) e archi del
grafo (prerequisiti/formule-tempo/regole-generazione). Chiude il gap V4: oggi da
`DefinizioniWorkflowListView` si può forkare/pubblicare, ma non *editare* il forkato.

## 2. Vincoli dal BE (già enforce, il FE li rispecchia, non li duplica)

- **Editabile solo la BOZZA** (e il preset). PUBBLICATA/RITIRATA per-emittente → **read-only**
  (il BE risponde `TEMPLATE_DEFINIZIONE_CONGELATA`; il FE le mostra in sola lettura, niente
  azioni di edit).
- **Immutabilità, unicità codice, ordine giorni formule, ≤1 BOZZA per scope, cicli
  prerequisiti** → tutti guard/CHECK DB. Il FE non li replica: mostra il banner d'errore
  parlante (envelope `ui_action=show_error_banner`). *Eccezione utile*: mirror leggero
  dell'ordine `giorni_critico < giorni_warning < giorni_esecuzione` per feedback immediato
  (oggi violazione → `E_DATABASE` generico) — pattern `classify` FE mirror del BE.
- Gli **endpoint step** degli archi devono appartenere alla definizione: il FE popola i Select
  di endpoint **solo con gli step dell'edizione corrente** (il BE rifiuta comunque con 404).

## 3. Modello UX proposto (list/drawer-based, no graph-canvas)

Coerente con lo stack BB esistente e **senza nuove dipendenze**. Il canvas a nodi/archi resta
un'eventuale evoluzione V5 (fuori scope qui).

**Entry point** — da `DefinizioniWorkflowListView` (`RowActionsMenu`): su riga BOZZA →
azione **«Modifica struttura»**; su PUBBLICATA/RITIRATA → **«Ispeziona»** (stesso editor in
readonly). Naviga a una **rotta dedicata** `/amm-software/definizioni-workflow/:id`
(l'editor è troppo ricco per un drawer).

**Vista editor** (`DefinizioneEditorView.vue`):
- **Header**: tipo · emittente · versione · `Tag` stato + **banner drift** (§FE-2.4) con
  azione «Allinea al preset» (quando `drift.versioni_indietro > 0`).
- **Readonly gate**: `useReadonlyMode` + `stato !== 'BOZZA'` → l'intero editor in sola lettura
  (`useProvideReadonly` → i figli con `useInjectReadonly`, pattern `feedback_drawer_readonly`).
- **Master-detail step** (BB [`RigheMasterDetailTable`](../../../../frontend/src/core/components/RigheMasterDetailTable.vue)):
  tabella step (sequenza · codice · descrizione · obbligatorio · direzione · modalità esito)
  + form sotto per create/edit dei **campi core**; delete con `useConfirmAction`; riordino
  sequenza via ▲▼ (zero-dep, come `ListaColonneModal`).
- **Dettaglio dello step selezionato** — tab/sezioni sui figli e archi entranti:
  - **Canali / Handler-eventi / Competenze**: sotto-liste attach/detach (form con
    `LookupSelect`: canale `config.canali_pratiche`, handler `pratiche.handler_flussi`,
    unità/risorsa). Pattern master-detail o `EntityFormDrawer` schema-driven.
  - **Prerequisiti** (arco entrante): «questo step richiede [Select step dell'edizione] con
    esito [Select esito]». Create/delete.
- **Sezione archi globali**: **formule-tempo** e **regole-generazione** (collegano coppie di
  step) come liste a livello edizione (da/a via Select step; per le regole, dest cross-edizione
  = Select tipo + step opzionale).
- **Azioni di processo** (`DrawerActionsBar`/`PageActionsBar`, `kind:'state'`): «Pubblica»
  (riusa Slice 1b), «Nuova versione», «Allinea preset».

**Store/API**: estendere `amministrazione/api/definizioniWorkflow.js` con i nuovi endpoint
(dettaglio + step/figli/archi CRUD) e un `definizioneEditor` store per il dettaglio + le
sotto-risorse. Il dettaglio non è una lista paginata → **non** `createCrudStore` diretto; le
sotto-liste possono usare macchine a stati stile `useSoggettoRuoloCollection` /
`RigheMasterDetailTable` (già BB). i18n `definizioni_workflow.*` da estendere.

## 4. Slicing FE (concentrico, rilasciabile anello per anello — mirror del BE)

| Slice | Stato | Contenuto | BE consumato |
|---|---|---|---|
| **FE-3.1 — Ispettore read-only** | ✅ | rotta `/amm-software/definizioni-workflow/:id` + `DefinizioneEditorView` + store `definizioneEditor`: header+drift, lista step, figli+archi read-only. Entry da lista (`RowActionsMenu` «Modifica struttura»/«Ispeziona»). | anelli 1-2 (`GET /definizioni/<id>/`) |
| **FE-3.2 — Editing step** | ✅ | create/edit/delete + riordino ▲▼ (normalizza sequenze) dei campi core (`DefinizioneStepForm`, mirror Inv1/Inv3/Inv4 esito_default). | anello 3 |
| **FE-3.3 — Editing figli per-nodo** | ✅ | attach/detach canali/handler-eventi/competenze (3 tab + composable `useStepFigliCollection`). Risorsa umana da `operatori/` (fetcher LookupSelect). | anello 4 |
| **FE-3.4 — Editing archi** | ✅ | prerequisiti (per step) + formule-tempo (mirror `0<critico<warning<esecuzione`) + regole-generazione. Composable `useArchiCollection`. | anello 5 |
| **FE-3.5 — Drift banner + Allinea (strada A)** | ✅ | banner drift con azione «Allinea al preset» = `fork(preset_corrente, emittente)` → nuova BOZZA copia-fresca, personalizzazioni ri-applicate a mano. | fork (**nessun nuovo BE**) |
| **QA Fase 3** | ✅ | shell `CollectionEditorPanel` + `useEditableCollection` (`buildRowActions`) + `useStepOptions`: de-duplicati toolbar/tabella/azioni/CSS ×6 e stepOptions ×3. **Bug corretti**: (a) `:key=step` sui tab per-step — senza, un form figlio aperto restava agganciato al vecchio step al cambio selezione → save mis-targeted; (b) watch edit→edit riga diversa; (c) reorder ricarica sempre (riconcilia su fallimento parziale); (d) `reloadPreserving` default-param (null=reset vs preserve). Rimosso codice morto `store.stepCodice/stepById`; guard clear esito a lookup non caricato. Review indipendente: payload/TDZ/null-guard verificati OK. | — |

**Scoperte di merito (segnalate a Tid, non bloccanti):**

- **3 vocabolari `esito` distinti**: `esito_default` step → catalogo `config.esiti_flussi_pratiche` (codice_interno); `esito_richiesto` prerequisiti/handler-eventi → `{POSITIVO,NEGATIVO,PARZIALE,NON_APPLICABILE}` (`chk_flussi_esito`); `esito_richiesto` regole-generazione → `{POSITIVO,NEGATIVO,QUALSIASI}`. Candidato a razionalizzazione modello.
- **Regole dest cross-edizione per-step**: la UI offre come step dest solo quelli dell'edizione corrente; un valore cross-edizione esistente si preserva in edit se non lo si tocca, ma non è selezionabile ex-novo (gestibile via id grezzo lato BE).

## 5. Decisioni per l'owner (Tid)

1. **Layout editor**: list/drawer-based (proposto) vs graph-canvas (dep + costo, → V5)?
   *Proposta: list/drawer ora.*
2. **Entry**: rotta dedicata (proposto) vs drawer grande dalla lista? *Proposta: rotta.*
3. **Riordino step**: ▲▼ zero-dep (proposto) vs drag-and-drop (dep)? *Proposta: ▲▼.*
4. **«Allinea al preset»** → ✅ **DECISO: strada A**. "Allinea" = crea una **nuova versione
   dal preset aggiornato** (copia fresca); le personalizzazioni le **ri-applica l'admin a
   mano** confrontando con la vecchia. **Nessun nuovo BE** (riusa fork/nuova-versione). Il
   **merge intelligente** (strada B: innesto automatico dei cambiamenti del preset preservando
   le personalizzazioni + risoluzione conflitti) è una feature grossa → **differita** finché
   non c'è un consumatore reale (più emittenti che divergono e aggiornano spesso).

## 6. Fuori scope

- Graph-canvas visuale (V5).
- Campi step avanzati (handler config/params, azione_ui, chiude_pratica) — servono prima gli
  anelli BE dedicati (rifiniture Slice 2).
- «Scarta BOZZA» (DELETE intera edizione) — azione sibling, mini-brief BE separato.
- **Allineamento con merge intelligente (strada B)** — differito (vedi §5.4).
- Catalogo preset di settore (V3).
