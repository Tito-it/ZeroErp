# Refactor UI Drawer — Azioni in alto + kebab responsive

> Piano operativo per uniformare la posizione e il comportamento responsive
> delle azioni di processo nei drawer (stato, PDF, gestisci sub-entità,
> utility), partendo dal pattern già applicato a `PreventiviDrawer` e
> `ContrattoDrawer`.
>
> Scope: **solo frontend** Vue/PrimeVue. Nessuna modifica DB o backend.
>
> Data: 2026-05-21

---

## Obiettivo

Tutti i drawer di entità con azioni di processo (transizioni di stato data-driven,
PDF, gestisci righe/note, export, ecc.) devono presentare le azioni in un'unica
fascia **in alto**, subito sotto l'header informativo (numero + stato +
badge di contesto), con comportamento responsive **CSS-first**:

| Contesto | Variante |
| --- | --- |
| Desktop `hover` + viewport `>=1024px` | Pulsanti inline con label, severity colorate |
| Tablet / touch / viewport `<1024px` | Solo azioni primarie inline; tutto il resto compresso in un kebab `⋮` con menu popup |

Lo switch è realizzato dalle stesse media query già usate per `RowActionsMenu`
e `PageActionsBar` (`@media (hover: none), (max-width: 1024px)`): il componente
renderizza entrambe le varianti, il CSS ne mostra una sola.

### Perché ora

- Tid ha già migrato a mano `PreventiviDrawer` e `ContrattoDrawer` come pilota:
  i due drawer espongono lo stesso pattern duplicato in CSS scoped e template
  (`.preventivo-drawer-actions` / `.contratto-drawer-actions`). Vanno
  consolidati in un building block prima che il pattern si moltiplichi.
- Su touch/tablet i tooltip non funzionano e una fila di 4-6 pulsanti diventa
  ingestibile (wrap su 2-3 righe, drawer si allunga, form spinto sotto il fold).
- Coerenza con [frontend-standards.md §"Colonna azioni di riga — `RowActionsMenu`"](../../frontend/frontend-standards.md)
  e [§"Azioni Pagina — `PageActionsBar`"](../../frontend/frontend-standards.md):
  stesso modello mentale per operatore e developer.

### Non obiettivi

- Riorganizzare il footer del drawer (rimane `DrawerFooter` con Annulla/Salva).
- Modificare la logica BE `script.fn_available_actions_*` o il payload capabilities.
- Toccare i sub-drawer di lista master-detail (`ContrattoRigheDrawer`,
  `ContrattoNoteDrawer`, ecc.): le loro azioni passano già da `PageActionsBar`.

---

## Building Block proposto: `DrawerActionsBar`

### Collocazione

`src/core/components/DrawerActionsBar.vue` — segue la regola
"componente potenzialmente cross-dominio → `core/components/`"
([frontend-standards.md §"Dove collocare un componente"](../../frontend/frontend-standards.md)).

### API pubblica

```js
// Props
{
  actions: Array,        // azioni (formato sotto)
  disabled: Boolean,     // disabilita tutte le azioni (es. loading globale)
  menuTooltip: String,   // override tooltip kebab (default: common.altre_azioni)
}

// Schema azione (compatibile con PageActionsBar + estensioni drawer)
{
  key: string,              // identificatore univoco
  kind: 'primary' | 'state' | 'manage' | 'secondary',
  label: string,            // testo (i18n)
  tooltip?: string,         // override tooltip (default: label)
  icon: string,             // PrimeIcons o MANAGE_ICONS.*
  severity?: 'primary' | 'warn' | 'danger' | 'info' | 'secondary',
  badge?: number | string,  // counter mostrato sopra l'icona (es. righe_count)
  visible?: boolean,        // default true
  disabled?: boolean,       // default false
  hideWhenReadonly?: boolean, // nasconde in LETTURA
  action?: string,          // codename permesso processo (auth.isActionAllowed)
  command: () => void,
}
```

### Semantica `kind`

| `kind` | Desktop ≥1024px | Mobile/touch | Esempi |
| --- | --- | --- | --- |
| `primary` | Inline con label, **sempre visibile** anche in compact | Inline | Salva-rapido critico, Annulla contratto (DRAFT), Accetta preventivo |
| `state` | Inline con label, severity colorata | Nel kebab popup | Transizioni `availableActions` (Emetti, Cessa, Riapri, ecc.) |
| `manage` | Inline con badge counter | Nel kebab popup | "Gestisci righe (5)", "Gestisci note (3)" |
| `secondary` | Nel kebab popup desktop *anche su desktop* | Nel kebab popup | Export, Anteprima diagnostica, Cronologia |

Differenza rispetto a `PageActionsBar`:

- nel drawer **non c'è azione "+ Nuovo"**: il `primary` è raro e riservato
  ad azioni terminali/critiche che l'operatore deve vedere sempre;
- compare il `kind: 'manage'` con `badge` (es. counter righe) che non esiste
  nelle pagine lista.

### Helper di mapping `useDrawerActions`

In `src/core/composables/useDrawerActions.js`:

```js
// Trasforma availableActions del payload BE in azioni DrawerActionsBar.
// Centralizza la regola "requires_date / requires_confirm / target_state".
export function mapAvailableActionsToDrawerActions({
  availableActions,
  t,
  onAction,    // (action) => void  — handler unificato (gestisce dialog/confirm)
}) {
  return (availableActions.value || []).map(a => ({
    key: a.key || `state-${a.target_state}`,
    kind: 'state',
    label: t(a.label_key),
    icon: a.icon,
    severity: a.severity,
    command: () => onAction(a),
  }))
}
```

I drawer chiamano:

```js
const stateActions = computed(() => mapAvailableActionsToDrawerActions({
  availableActions: caps.availableActions,
  t,
  onAction: onCambiaStato,
}))

const drawerActions = computed(() => [
  ...stateActions.value,
  { key: 'pdf', kind: 'secondary', ... },
  { key: 'manage-righe', kind: 'manage', badge: righeCount.value, ... },
  { key: 'manage-note', kind: 'manage', ... },
])
```

### Slot

- `#prefix` — contenuto prima delle azioni state (es. badge custom)
- `#suffix` — contenuto dopo le azioni state e prima del kebab (es. tag)

Il counter badge per `kind: 'manage'` è incorporato (no slot custom necessario);
riusa la classe `.contratto-drawer-righe-count` rinominata in
`.app-drawer-action-badge` e spostata in `main.css`.

---

## Classi CSS (in `src/assets/main.css`)

| Classe | Scopo |
| --- | --- |
| `app-drawer-actions` | Wrapper barra azioni: flex row, gap 0.4rem, flex-wrap, margin-top 0.5rem |
| `app-drawer-actions-desktop` | Wrapper varianti inline visibili solo `hover + >=1024px` |
| `app-drawer-actions-compact` | Wrapper kebab visibile solo touch o `<1024px` |
| `app-drawer-action-badge` | Counter sopra l'icona pulsante (stile di `.contratto-drawer-righe-count` attuale) |

Le media query sono già definite in `main.css` per `RowActionsMenu` —
estendere lo stesso selettore senza duplicare i breakpoint.

Rimozione (in coda al refactor): `.preventivo-drawer-actions`,
`.preventivo-drawer-header-row`, `.preventivo-drawer-header-info`,
`.preventivo-drawer-header-muted`, `.preventivo-drawer-status`,
`.contratto-drawer-*` da CSS scoped dei due drawer pilota.

> L'header info (Tag numero + data + Tag stato) **resta in `DrawerTitle` o nel
> template del drawer**. Il BB gestisce solo la riga azioni sotto l'header.
> Vedere "Header info" sotto.

---

## Header info — pattern parallelo

Nei due drawer pilota la riga sopra le azioni mostra:

```text
[Tag numero] [Tag rev/forma derivata] [data] ...filler... [Tag stato]
```

Pattern attuale duplicato (`.preventivo-drawer-header-row` /
`.contratto-drawer-header-row`). Lo consolidiamo in un secondo BB più leggero:

`src/core/components/DrawerEntityHeader.vue`

```vue
<DrawerEntityHeader
  :primary-tag="{ value: detail.numero, severity: 'secondary' }"
  :extra-tags="[{ value: detail.rev, severity: 'warn', icon: 'pi pi-history', if: isSuperseded }]"
  :muted="displayDate(detail.data)"
  :status-tag="{ value: detail.stato_descrizione, severity: statoXSeverity(detail.stato_codice) }"
>
  <template #after-primary>
    <!-- contesto pricing badge etc. -->
  </template>
</DrawerEntityHeader>
```

API e CSS minimali (riusa `app-drawer-header-*` come classi pubbliche).
Niente logica: solo layout.

---

## Criterio di applicabilità — quando usare `DrawerActionsBar`

Non tutti i drawer sono candidati alla migrazione. Il pattern uniforme della
barra azioni in alto ha senso solo per una famiglia specifica di drawer.
Tabella di scelta (aggiornata 2026-05-21 post analisi Soggetto/Cliente):

| Pattern drawer | Esempi | Azioni di processo |
| --- | --- | --- |
| **A** — Entità + righe lineari principali | Contratto, Preventivo, Listino-Versione | `DrawerActionsBar` in alto: state + manage righe/note + secondary |
| **B** — Entità + solo state transitions, niente sub-entità centrali | PromoArticolo, VersioneForm (attiva/chiudi/clona) | `DrawerActionsBar` solo per le state actions |
| **C** — Entità foundational con cascate inline obbligatorie | Soggetto | Sezioni inline locali — **NIENTE migrazione** |
| **D** — Entità che poggia su Soggetto, con BB sub-entità dedicato | Cliente, Fornitore | `SoggettoPreviewBadges` per le sub-entità + `DrawerFooter` — **NIENTE migrazione** |
| **E** — Drawer CRUD puri | UnitaMisura, EmailAccount, CategoriaCliente, ecc. | Footer Annulla/Salva soltanto — **NIENTE migrazione** |
| **F** — Drawer di sola lista master-detail inline | ContrattoRigheDrawer, ContattiSoggettoDrawer, ecc. | `PageActionsBar` interno alla lista — **NIENTE migrazione** |

**Razionale famiglie escluse:**

- **C — Soggetto**: l'entità foundational PF/PG/ENTE richiede in CREATE di
  valorizzare cascate dipendenti (indirizzi comune→via→CAP, contatti, conti)
  prima del save. Le sezioni inline sono **obbligate** dal modello, non scelta UX.
- **D — Cliente/Fornitore**: poggiano sopra Soggetto. In CREATE espongono
  sezioni inline `contatto`/`indirizzo` per il setup iniziale (`v-if="!isEdit"`),
  in EDIT le sub-entità passano da `SoggettoPreviewBadges`
  ([SoggettoPreviewBadges.vue:142-172](../../../../frontend/src/core/components/SoggettoPreviewBadges.vue#L142-L172))
  — una riga di bottoni-badge con counter per indirizzi/conti/contatti/web.
  È già un BB centralizzato (filosofia identica a `DrawerActionsBar`,
  rappresentazione diversa). Se un domani si vorrà uniformare alla kebab
  responsive, sarà un refactor del solo `SoggettoPreviewBadges` — i drawer
  Cliente/Fornitore restano invariati.

---

## Drawer inventario (priorità di migrazione)

### Tier 1 — pilota (✅ FATTO 2026-05-21)

| Drawer | Azioni | Stato |
| --- | --- | --- |
| [PreventiviDrawer.vue](../../../../frontend/src/vendite/preventivi/components/PreventiviDrawer.vue) | state (emetti/accetta/rifiuta/scadi/annulla/evadi), revisione, PDF nel `#suffix`, gestisci note | ✅ Migrato + CSS scoped rimosso |
| [ContrattoDrawer.vue](../../../../frontend/src/vendite/components/ContrattoDrawer.vue) | state (attiva/cessa), annulla DRAFT (fallback), PDF nel `#suffix`, gestisci righe (badge counter), gestisci note | ✅ Migrato + CSS scoped rimosso |

### Tier 2 — pattern A/B (4 drawer)

Restano nel perimetro `DrawerActionsBar` solo i drawer del pattern A (righe
lineari principali) e B (state transitions). Cliente/Fornitore/Soggetto
**riclassificati come esclusi** (vedi sezione "Criterio" sopra).

| Drawer | Pattern | Azioni candidate |
| --- | --- | --- |
| [PromoArticoloDrawer.vue](../../../../frontend/src/vendite/components/PromoArticoloDrawer.vue) | B | state (attiva/cessa), `useEntityCapabilities` già presente |
| [ArticoloDrawer.vue](../../../../frontend/src/catalogo/components/ArticoloDrawer.vue) | A | gestisci UoM, gestisci BoM, gestisci note, disattiva/riattiva — **caso borderline**, vedi nota |
| [VersioneFormDrawer.vue](../../../../frontend/src/vendite/components/VersioneFormDrawer.vue) | A+B | state (attiva/chiudi), clona, gestisci righe |
| [ListinoDrawer.vue](../../../../frontend/src/vendite/components/ListinoDrawer.vue) | A | gestisci versioni, disattiva |

> **ArticoloDrawer caso borderline**: ha più sub-entità di varia natura
> (UoM, BoM, note). Valutare se renderle tutte `kind: 'manage'` in fascia
> azioni in alto, oppure mantenere il pattern attuale (sezioni inline tipo
> Soggetto). Decisione caso-per-caso durante la migrazione.

### Tier 3 — pattern E con eventuali state actions

Drawer CRUD admin: per default niente migrazione (footer Annulla/Salva
soltanto). Eccezione se hanno **realmente** azioni di processo (disattiva /
riattiva / chiudi). Da valutare drawer-per-drawer:

`CategoriaClienteDrawer`, `CategoriaClienteListinoDrawer`, `UtilityTipoRuoloDrawer`,
`TipoRuoloTipoIndirizzoDrawer`, `EmailAccountDrawer`, `EmailTemplateDrawer`,
`ImpostazioniOverrideDrawer`, `TemplateDocumentoDrawer`, `TemplateAssetDrawer`,
`UnitaMisuraDrawer`, `UomTipoDrawer`, `ContrattoUtilityDrawer`,
`FlussoDrawer`, `WebAccessiDrawer`, `ListaPresetDrawer`,
`ListaDefinizioneDrawer`, `ListaColonnaDrawer`, `ListaPresetColonneDrawer`,
`ListaColonnaPermessoDrawer`.

### Esclusi dal refactor

**Pattern C — foundational con cascate inline:**

- [SoggettoDrawer.vue](../../../../frontend/src/anagrafiche/components/SoggettoDrawer.vue)
  — sezioni inline obbligate dal modello (cascate indirizzi/contatti/conti
  pre-save).

**Pattern D — derivato da Soggetto con BB sub-entità dedicato:**

- [ClienteDrawer.vue](../../../../frontend/src/anagrafiche/components/ClienteDrawer.vue)
  — `SoggettoPreviewBadges` per indirizzi/conti/contatti + sezioni inline solo CREATE
- [FornitoreDrawer.vue](../../../../frontend/src/anagrafiche/components/FornitoreDrawer.vue)
  — analogo Cliente

**Pattern F — drawer di sola lista master-detail inline** (header informativo,
lista, form sotto; azioni gestite dal `PageActionsBar` interno):

`ContrattoRigheDrawer`, `ContrattoNoteDrawer`, `PreventivoNoteDrawer`,
`ContattiSoggettoDrawer`, `IndirizziSoggettoDrawer`, `ArticoloUomDrawer`,
`ArticoloBomDrawer`, `UomConversioniDrawer`, `ConversioneUomDrawer`,
`ContrattiBillingAccountDrawer`, `ComuneDrawer`, `ProvinceDrawer`,
`CodiciPostaliDrawer`, `CloneVersioneDrawer`.

---

## Fasi operative

### Fase 0 — Scaffolding BB (✅ FATTO 2026-05-21)

**File creati:**

- [DrawerActionsBar.vue](../../../../frontend/src/core/components/DrawerActionsBar.vue) — BB con `kind` (`primary`/`state`/`manage`/`secondary`) + badge counter + responsive desktop/compact + `app-escape` auto
- [DrawerEntityHeader.vue](../../../../frontend/src/core/components/DrawerEntityHeader.vue) — BB header info (default slot inline + `#status`)
- [useDrawerActions.js](../../../../frontend/src/core/composables/useDrawerActions.js) — helper `mapAvailableActionsToDrawerActions`

**File modificati:**

- [main.css](../../../../frontend/src/assets/main.css) — classi `app-drawer-actions*`, `app-drawer-action-wrap/-badge/-badge-dot`, `app-drawer-header-row/-info/-status/-muted` + toggle responsive nel media query `@media (hover: none), (max-width: 1024px)` esistente
- [catalogo-building-block-frontend.md](../../frontend/catalogo-building-block-frontend.md) — 1 riga composable + 2 righe componenti + 6 righe classi CSS
- [frontend-standards.md](../../frontend/frontend-standards.md) — nuova sezione "Azioni Drawer — `DrawerActionsBar`" (mirror della sezione `RowActionsMenu`/`PageActionsBar`)

**Deliverable:** BB compilano, nessun drawer li consuma ancora, build verde.

### Fase 0.5 — Logica resize/scroll uniforme dei drawer (✅ FATTO 2026-05-21)

Fix scoperto e applicato durante lo smoke Fase 1: i drawer con
`DRAWER_WIDTH` ≥ viewport (es. `WIDE 960px` su schermo 800px) finivano
fuori schermo senza scrollbar orizzontale. Soluzione **globale, zero
migrazione drawer-by-drawer**:

```css
.p-drawer { max-width: 100vw; }                    /* clamp viewport */
.app-drawer-content { min-width: 0; overflow-x: auto; }  /* safety net */
```

Le `DRAWER_WIDTH` (`constants.js`) diventano "richieste massime": sopra
viewport il drawer ha la sua larghezza preferita, sotto soglia riempie lo
schermo. Documentato in [frontend-standards.md §"Larghezze standard"](../../frontend/frontend-standards.md).

### Fase 1 — Migrazione Tier 1 (✅ FATTO 2026-05-21)

Pattern A (entità con righe lineari principali): consolidamento dei 2 pilota
sui nuovi BB.

| Drawer | Risultato |
| --- | --- |
| [ContrattoDrawer.vue](../../../../frontend/src/vendite/components/ContrattoDrawer.vue) | `DrawerEntityHeader` + `DrawerActionsBar` (state da `availableActions` + Annulla DRAFT outlined danger fallback + Gestisci righe con `badge: righeCount` + Gestisci note); PDF nel `#suffix`; chunk: 49.99 → 49.49 kB |
| [PreventiviDrawer.vue](../../../../frontend/src/vendite/preventivi/components/PreventiviDrawer.vue) | `DrawerEntityHeader` (con 3 badge contesto pricing CONTRATTO/CATEGORIA/NONE inline) + `DrawerActionsBar` (state + Nuova revisione + Gestisci note, state nascoste in readonly preservando semantica `v-if="!isReadonly"`); PDF stato-aware nel `#suffix`; chunk: 96.02 → 95.71 kB |

Smoke visivo confermato da Tid: layout coerente sui due drawer, resize a
schermo piccolo OK post-Fase 0.5.

### Fase 2 — Migrazione Tier 2 (pattern A/B)

Censimento corretto post-analisi 2026-05-22: la classificazione iniziale di
Tier 2 (PromoArticolo / VersioneForm / Listino / Articolo) era sbagliata —
solo `ArticoloDrawer` aveva effettivamente Tag stato + state actions in
forma migrabile. Gli altri 3 candidati ipotizzati sono:

| Drawer ipotetico | Cos'è davvero | Pattern | DrawerActionsBar? |
| --- | --- | --- | --- |
| `PromoArticoloDrawer` | form testata promo: state actions governate da `availableActions` BE inline nel form, niente Tag stato in alto da migrare | E | ❌ Fuori scope |
| `VersioneFormDrawer` | drawer di **create rapida** nuova versione listino (3 campi: codice, valido_dal, valido_al) | E (CRUD) | ❌ Fuori scope |
| `VersioneDrawer` | drawer di **gestione righe prezzo** della versione (master-detail inline) | F (sola lista) | ❌ Fuori scope (azioni via `PageActionsBar` interno) |
| `CloneVersioneDrawer` | drawer di **clonazione** versione (form dedicato) | E (CRUD) | ❌ Fuori scope |
| `ListinoDrawer` | drawer testata listino — zero `availableActions`, Tag stato, drawer-actions | E (CRUD puro) | ❌ Fuori scope |
| `ArticoloDrawer` | pattern misto: state in alto + panel inline | A misto | ✅ FATTO 2026-05-21 (Fase 2.A) |

**Conseguenza**: Tier 2 si chiude con la sola **Fase 2.A** (`ArticoloDrawer`).
Le state actions delle versioni listino (attiva/chiudi/clona) vivono come
azioni di riga nella tabella `ListiniView` via `RowActionsMenu` — quello
è già il pattern centralizzato e non richiede `DrawerActionsBar`.

**Fase 2.A — ArticoloDrawer (✅ FATTO 2026-05-21):**
Solo state actions in alto (Tag stato in `#status` + Disattiva/Riattiva in
`DrawerActionsBar`). UoM/BoM/note **restano panel inline** — decisione utente:
la natura eterogenea delle sub-entità (UoM con cascata, BoM con composizione,
note con scope catalogo) giustifica il pattern misto.

**Procedura per ogni drawer Tier 2:**

1. Aggiungere import `DrawerEntityHeader` + `DrawerActionsBar` + (se serve) `mapAvailableActionsToDrawerActions`
2. Costruire `drawerActions` computed (state + eventuali manage + secondary)
3. Sostituire `<div class="x-drawer-header-row">` con `<DrawerEntityHeader>`
4. Sostituire `<div class="x-drawer-actions">` con `<DrawerActionsBar :actions="drawerActions" />`
5. Rimuovere il `<style scoped>` ridondante
6. Verifica visiva in browser

**Smoke checklist (stesso template di Fase 1):**

- Header: identificatore, badge contesto/forma, Tag stato a destra
- Azioni desktop ≥1024px: tutte inline con label
- Azioni mobile <1024px: solo `primary` inline (se presente), resto nel kebab `⋮`
- Counter manage mostra il numero anche su mobile (dot sul kebab + label suffissata "Gestisci X (N)")
- Modalità readonly: `hideWhenReadonly` rispettata
- Click su voce kebab esegue stesso comando del pulsante inline
- `Esc` chiude il menu (PrimeVue Menu default)

### Fase 2.B — Unificazione note articolo al BB partizionato (✅ FATTO 2026-05-21)

Investigazione: lo schema DB `catalogo.note` è gemello di `vendite.note`
(stesso modello partizionato target_tipo/anchor/posizione/seq/...), i
serializer BE `_NOTA_CREATE_REQUEST`/`_NOTA_PATCH_REQUEST` espongono tutti
i campi partition, response shape `{count, results}` identica a quella
attesa da `useNote`. La differenza era **solo URL pattern** (catalogo usa
"split" con DETAIL su `/catalogo/note/<id>/` invece che sotto parent).

**Soluzione FE** (nessun brief DB):

- Esteso `makeNotesApi(basePath, { detailBase })` con opzione `detailBase`
  per coprire il pattern URL "split" di catalogo.
- Aggiunti wrapper `makeArticoloNotesApi(id)` + `makeComponenteNotesApi(articoloId, compId)`
  in `catalogo/api/catalogo.js`.
- `ArticoloNoteDrawer.vue`: riscritto come thin wrapper ~35 righe su `NoteDrawer`
  (era 30 righe wrapper su `CatalogoNoteDrawer`).
- `ArticoloBomDrawer.vue` blocco note: passato da `CatalogoNoteDrawer + listFn/createFn`
  al BB `NoteDrawer + makeComponenteNotesApi`.
- `ArticoloDrawer.vue` `loadNoteRiepilogo`: usa `makeArticoloNotesApi(...).listNote()`.
- **Droppato** `CatalogoNoteDrawer.vue` (247 righe legacy) + 6 funzioni
  legacy in `catalogo.js` (`listArticoloNote`/`createArticoloNota`/`updateNota`/
  `deleteNota`/`listComponenteNote`/`createComponenteNota`).

### Fase 2.B.1 — BE: default anchor_tipo/posizione (✅ FATTO 2026-05-22)

Bug emerso durante lo smoke note articolo: il BE catalogo non applicava
i default `anchor_tipo`/`posizione` come fa vendite via `PartitionedNoteService`.
Il BB FE `NoteDrawer` non li invia (per design — "governati dal BE"), quindi
il CREATE finiva al constraint NOT NULL del DB con `E_CATALOGO_VALIDATION`.

**Fix** in [catalogo_service.py:1178-1216](../../../../backend/apps/catalogo/services/catalogo_service.py#L1178-L1216):

- In `_extract_nota_payload`, alla fine del branch `for_update=False` (CREATE only):
  - `anchor_tipo = 'RIGA' if target_riga_id is not None else 'DOCUMENTO'`
  - `posizione = 'AFTER' if anchor_tipo == 'RIGA' else 'HEADER'`
- Guard coerenza speculare a vendite: `(anchor_tipo == 'RIGA') == (target_riga_id is not None)` → altrimenti `E_CATALOGO_VALIDATION`.
- UPDATE non applica i default (chi vuole cambiarli passa esplicitamente).

**3 test nuovi**: `test_fn_create_nota_articolo_default_documento_header`,
`test_fn_create_nota_componente_default_riga_after`,
`test_fn_create_nota_articolo_anchor_riga_inconsistency`.

### Fase 2.B.2 — BE: alias shape risposta catalogo → pattern partizionato (✅ FATTO 2026-05-22)

Bug emerso allo smoke successivo: lista note mostrava righe vuote e edit/delete
restituivano 404. Causa: la view DB `catalogo.vw_articoli_note` espone le
colonne col prefisso `nota_*` (legacy per evitare ambiguità sul JOIN articolo),
mentre il BB FE `NoteDrawer` legge la shape **vendite** (`id`, `testo_md`,
`anchor_tipo`, ecc. senza prefisso). PrimeVue `data-key="id"` trovava `undefined`,
delete su `/catalogo/note/undefined/` → 404.

**Fix** confined al repo, niente DB touch:

In [catalogo_bom_repository.py](../../../../backend/apps/catalogo/db/catalogo_bom_repository.py):

- `list_note_articolo`, `get_nota_articolo`, `list_note_componente`,
  `get_nota_componente`: alias SQL `vn.nota_id AS id`, `nota_testo_md AS testo_md`,
  `nota_anchor_tipo AS anchor_tipo`, ecc. (16 alias per query). La view DB resta
  invariata; l'alias vive nel repo.
- [ArticoloDrawer.vue](../../../../frontend/src/catalogo/components/ArticoloDrawer.vue) riepilogo note: `:key="n.id"` + `n.testo_md || n.testo` invece dei vecchi `n.nota_id`/`n.nota_testo`.
- Test BE aggiornati alla nuova shape: 75/75 catalogo verdi.

Risultato: **una sola famiglia note FE** (`NoteDrawer` + `useNote` + `makeNotesApi`)
condivisa da preventivi, contratti, articoli, componenti articolo. Aggiungere
una nuova partizione note = wrapper di ~30 righe.

### Fase 2.C — Fluidità apertura drawer (✅ FATTO 2026-05-22)

Problema rilevato durante lo smoke di `PromoArticoloDrawer`: l'apertura
"blocca e riparte" perché `LookupSelect`/`AutoComplete`/`DatePicker` montano
durante l'animazione di slide del Drawer PrimeVue. Pattern `contentReady` +
`onAfterShow` già adottato da 5 drawer pilota ma **duplicato inline**: ogni
drawer ridichiarava `const contentReady = ref(false)`, `function onAfterShow()`
e `contentReady.value = false` nel watch su `visible`. 7 drawer del dominio
vendite mancavano del pattern.

**Soluzione: composable centralizzato** [useDrawerContentReady.js](../../../../frontend/src/core/composables/useDrawerContentReady.js):

```js
import { useDrawerContentReady } from '@/core/composables/useDrawerContentReady'

const { contentReady, onAfterShow } = useDrawerContentReady(() => props.visible)
```

Il composable gestisce automaticamente il reset di `contentReady` a `false`
alla chiusura (watch interno su `visibleSource`). Il chiamante non deve più
toccare `contentReady` nel proprio watch. ~10 righe totali.

**Adozione:**

- Applicato a `PromoArticoloDrawer` (fix percepito: apertura ora fluida).
- Refactor pulizia su `ContrattoDrawer`, `PreventiviDrawer`, `ArticoloDrawer`,
  `ListinoDrawer`, `ConversioneUomDrawer`: sostituiscono il boilerplate
  inline con la singola riga di composable.

**Pattern documentato** in [catalogo-building-block-frontend.md](../../frontend/catalogo-building-block-frontend.md)
sotto Composables → `useDrawerContentReady`. Da applicare ai drawer Tier 2/3
in fase di migrazione (sequenza naturale: insieme alla migrazione azioni).

### Fase 3 — Tier 3 (pattern E con state actions)

**Censimento eseguito 2026-05-22** su 60 drawer totali nel frontend.

**Criteri di ricerca:**

- Uso di `useEntityCapabilities`/`availableActions` (data-driven BE)
- Pulsanti hardcoded `disattiva`/`riattiva`/`attiva`/`cessa`/`chiudi`/`sospendi`/`blocca`/`annulla`/`riapri`/`completa`
- Convenzione i18n `azione_*` + `cambiaStato`
- Tag stato (`<Tag` con `severity` legato a `stato_codice`)

**Risultato — 2 candidati effettivi:**

| Drawer | Stato pattern oggi | Migrazione candidata |
| --- | --- | --- |
| [PraticaDrawer.vue](../../../../frontend/src/pratiche/components/PraticaDrawer.vue) | Tag stato (`statoPraticaSeverity`) + 5 state actions hardcoded: Apri / Sospendi / Riattiva / Chiudi / Annulla — pattern speculare a `ContrattoDrawer` pre-refactor | `DrawerEntityHeader` + `DrawerActionsBar` con 5 `kind:'state'` (severity da derivare per stato target). `useDrawerContentReady` come parte del refactor. |
| [FlussoDrawer.vue](../../../../frontend/src/pratiche/components/FlussoDrawer.vue) | Tag stato (`statoFlussoSeverity`) + azioni condizionali per stato (DA_ESEGUIRE → "Avvia" → IN_CORSO → "Completa"/"Annulla" → COMPLETATO/ANNULLATO/ERRORE). Logica `v-if="stato === STATO_FLUSSO.X"` invece di `v-for availableActions` | `DrawerEntityHeader` + `DrawerActionsBar` con azioni `kind:'state'` filtrate via `visible:` sullo stato corrente. |

**Falsi positivi del grep (NON candidati):**

- `ClienteDrawer`, `FornitoreDrawer`, `SoggettoDrawer`: Tag stato readonly inline nel form, nessuna state transition nel drawer (cambia stato si fa altrove o non esiste). Pattern D già documentato.
- `ListaColonnaDrawer`, `CategoriaClienteListinoDrawer`: il grep matchava `azione_*` come riferimento al concetto di colonna azione / tipo variazione, non come state action.
- `WebAccessiDrawer`: ~36 righe, wrapper sottile su `SoggettoPreviewBadges`, niente state in alto.
- `ContrattiBillingAccountDrawer`, `VersioneDrawer`, `ContrattoRigheDrawer`: pattern F (sola lista master-detail), niente da migrare a `DrawerActionsBar`.

**Conclusione:** Tier 3 si riduce a **2 drawer pratiche**. Il restante (~17 drawer
CRUD admin censiti nel piano originale) ha solo footer Annulla/Salva e va lasciato
com'è. Anche `useDrawerContentReady` può essere applicato in modo opportunistico
a quei drawer più pesanti (es. `EmailTemplateDrawer` con editor markdown), ma è
un fix di fluidità a parte, non parte del refactor azioni.

### Fase 3.A — PraticaDrawer + FlussoDrawer (✅ FATTO 2026-05-22)

Migrazione speculare alla Fase 1: `DrawerEntityHeader` + `DrawerActionsBar` +
`useDrawerContentReady`.

**FlussoDrawer** ([FlussoDrawer.vue](../../../../frontend/src/pratiche/components/FlussoDrawer.vue)):

- `DrawerEntityHeader`: Tag `pratica_codice` + muted `displayTimestamp(data_insert)` + `#status` Tag stato (`statoFlussoSeverity`).
- `DrawerActionsBar` con **1 sola azione**: "Avvia" (`kind:'state'`, severity `info`, visible solo `stato === DA_ESEGUIRE`).
- **"Completa con esito" resta inline** come transizione con dati di processo (richiede esito obbligatorio + note opzionali, pattern `feedback_dialog_cambio_stato_dati_processo` — non comprimibile a `command: () => void`).
- Footer custom Chiudi → `<DrawerFooter close-only />`.
- Build verde, zero impatto sul chiamante `PraticheDashboard.vue` (props/emit invariati).

**PraticaDrawer** ([PraticaDrawer.vue](../../../../frontend/src/pratiche/components/PraticaDrawer.vue)):

- Header + barra azioni in alto al drawer **sopra il TabView** (prima erano dentro il tab Dati come `.pratica-header-row` + `.pratica-actions`).
- `DrawerEntityHeader`: Tag `codice` + `#status` con Tag stato + Tag priorità.
- `DrawerActionsBar` con **5 state actions** condizionali per stato corrente:
  - `BOZZA` → Apri (info)
  - `APERTA` → Sospendi (warn) + Chiudi (success) + Annulla (danger outlined)
  - `SOSPESA` → Riattiva (success) + Chiudi (success) + Annulla (danger outlined)
  - `CHIUSA`/`ANNULLATA` → nessuna (stati terminali)
- Tutte `hideWhenReadonly: true`. Annulla mantiene `confirmAction` dialog.
- Aggiunto wrapper `app-drawer-content` (prima mancava → ora beneficia anche di max-width 100vw + overflow-x della Fase 0.5).
- CSS scoped `.pratica-header-row` + `.pratica-actions` rimossi (~14 righe).

### Fase 4 — Pulizia residui

- [ ] Grep `class="(.*-)?drawer-(header|actions)(-row)?"`, `class="(.*-)?drawer-righe-(action|count)"` deve ritornare zero match (oltre alle classi `app-drawer-*` ufficiali)
- [ ] Grep `<Button.*availableActions` deve ritornare zero match (eccetto dentro `DrawerActionsBar.vue`)
- [ ] Documentazione `frontend-standards.md` aggiornata con la sezione completa
- [ ] Catalogo `catalogo-building-block-frontend.md` con riga su `DrawerActionsBar` + `DrawerEntityHeader` + `useDrawerActions`

---

## Decisioni chiuse (post Fase 0/1)

1. **Severity azioni di stato**: pass-through PrimeVue del payload `availableActions` BE (`primary`/`success`/`warn`/`info`/`danger`/`secondary`). Nessuna logica FE per derivare severity da `target_state`. Confermato.
2. **Badge counter manage**: desktop = badge piccolo nell'angolo del pulsante inline; mobile = dot sul kebab + label suffissata "Gestisci X (N)" nel popup. La somma dei counter di manage eterogenei sarebbe ambigua → dot puro senza numero sul kebab compact. Confermato.
3. **Posizione PDF**: dentro slot `#suffix` di `DrawerActionsBar`. `PreventivoPdfButton`/`ContrattoPdfButton` restano componenti dedicati (dialog conferma rigenerazione, menu stato-aware) non rappresentabili come `command: () => void`. Confermato.
4. **`outlined` esplicito**: aggiunto al formato azione (default `true` per `kind:'manage'`, `false` altrove). Usato in ContrattoDrawer per Annulla DRAFT (`kind:'state'` + `severity:'danger'` + `outlined:true`). Confermato.
5. **Cliente/Fornitore/Soggetto fuori perimetro**: pattern panel/badge dedicato — `SoggettoPreviewBadges` è già un BB centralizzato per le sub-entità. Niente migrazione a `DrawerActionsBar`. Confermato 2026-05-21.
6. **Resize/scroll uniforme**: Fase 0.5 globale via `.p-drawer { max-width: 100vw }` + `.app-drawer-content { overflow-x: auto }`. Nessuna migrazione drawer-by-drawer. Confermato 2026-05-21.

## Decisioni aperte

1. **ArticoloDrawer pattern**: tre sub-entità di natura diversa (UoM, BoM, note). Da decidere durante Fase 2 se renderle tutte `kind:'manage'` in fascia in alto, oppure mantenere sezioni inline tipo Soggetto. Decisione caso-per-caso.
2. **Test FE**: niente Vitest/Jest oggi nel repo. La verifica resta **smoke visivo in browser** + `npm run build` verde. Documentare lo smoke per Tier 1 come riferimento per Tier 2/3.

---

## Rollback

Modifiche atomiche per fase. In caso di regressione:

- Fase 0: drop dei 3 file nuovi + revert classi CSS. Nessun drawer rotto.
- Fase 1/2/3: revert drawer-by-drawer (modifiche confined a `<template>`,
  `<style scoped>` e import di ciascun drawer).

Niente migration DB, niente API change, niente schema endpoint: rollback puro Git.

---

## Riferimenti

- [PageActionsBar.vue](../../../../frontend/src/core/components/PageActionsBar.vue) — modello azioni di pagina (analogo per lista)
- [RowActionsMenu.vue](../../../../frontend/src/core/components/RowActionsMenu.vue) — modello azioni di riga (analogo per DataTable)
- [frontend-standards.md](../../frontend/frontend-standards.md) — sezione `RowActionsMenu` e `PageActionsBar`
- [catalogo-building-block-frontend.md](../../frontend/catalogo-building-block-frontend.md) — catalogo BB esistenti
- Drawer pilota di riferimento: [ContrattoDrawer.vue:524-588](../../../../frontend/src/vendite/components/ContrattoDrawer.vue#L524-L588), [PreventiviDrawer.vue:680-770](../../../../frontend/src/vendite/preventivi/components/PreventiviDrawer.vue#L680-L770)
