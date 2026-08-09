# Piano — Filtri contestuali su `ArticoloLookup`

> **Stato (2026-05-18)**: ✅ **APPLICATO** end-to-end (FE only).
> Tutti i 6 caller cablati, prop legacy `soloComponenti: Boolean` rimossa,
> dead-code intercettazione composito in `VersioneDrawer.onArticoloSelected`
> ripulito, doc BB FE aggiornata. Vedi §9 per riepilogo modifiche.
>
> Sezioni 1-7 conservate come reference di design; checklist §4 spuntata in §9.
>
> **Scope**: solo FE. Niente modifiche DB. Niente modifiche BE (l'endpoint
> `lookup_articoli` supporta già tutti i filtri necessari, vedi §1.2).
>
> **Trigger**: osservazione 2026-05-18 di Tid — i caller `ArticoloLookup`
> nei contesti operativi (preventivi/ordini/contratti AGGIUNTA/listini righe)
> oggi mostrano anche articoli `is_solo_componente=true`, che non sono
> selezionabili in quei contesti per regole di modello. Più in generale
> serve un meccanismo standard per filtrare la combo di ricerca articoli
> in base al contesto d'uso.

---

## 1. Stato attuale

### 1.1 Componente FE — [ArticoloLookup.vue](../../../../frontend/src/core/components/ArticoloLookup.vue)

Espone 2 prop sui filtri:

- `soloAttivi: Boolean` (default `true`) → mappato su query `attivo`. Cablato
  ovunque per default true.
- `soloComponenti: Boolean` (default `undefined`) → mappato su query
  `is_solo_componente`. **Mai cablato in nessun caller.**

Nessuna prop su `is_composito` benché supportata dal BE.

### 1.2 Endpoint BE — [lookup_articoli](../../../../backend/apps/catalogo/services/catalogo_service.py)

`fn_lookup_articoli` accetta già 4 filtri:

- `search` — testuale
- `attivo` — boolean
- `is_composito` — boolean (nullable)
- `is_solo_componente` — boolean (nullable)

Tutti `nullable`: assenza del parametro = no filtro.

### 1.3 Caller verificati (6 punti d'uso)

| Caller | Filtro applicato oggi | Comportamento osservato |
|---|---|---|
| `PreventiviRigaForm` | nessuno | Operatore può selezionare un solo-componente → rotto |
| `ContrattoRigheDrawer` (AGGIUNTA) | nessuno | idem |
| `VersioneDrawer` (riga listino) | nessuno | Compositi selezionabili → intercettati post-selezione (`onArticoloSelected` apre Dialog bundle) — UX a 2 passi |
| `PromoArticoloDrawer` | nessuno | Solo-componenti selezionabili → da decidere se ammessi (vedi §3.5) |
| `ArticoloBomDrawer` (figlio BoM) | nessuno | Compositi selezionabili → no nesting BoM (`§9.2 modello-componenti-bom`) — rotto |
| `TestResolverDialog` (×2 lookup) | nessuno | Admin/dev tool — comportamento accettabile |

### 1.4 Problema di naming della prop attuale

`soloComponenti` ha 3 stati ambigui (`undefined` / `true` / `false`) con
semantiche diverse. Lettura `soloComponenti=false` a freddo non è ovvia:
significa "escludi i solo-componenti", non "mostra tutto".

---

## 2. API target

### 2.1 Nuova prop `filtri` (oggetto)

```vue
<ArticoloLookup
  v-model="obj"
  :filtri="{
    soloComponenti: 'escludi',
    compositi: 'escludi'
  }"
/>
```

**Shape**:

```ts
interface ArticoloLookupFiltri {
  // 'qualsiasi' (default) | 'escludi' (= is_solo_componente=false)
  //                       | 'solo'    (= is_solo_componente=true)
  soloComponenti?: 'qualsiasi' | 'escludi' | 'solo'

  // 'qualsiasi' (default) | 'escludi' (= is_composito=false)
  //                       | 'solo'    (= is_composito=true)
  compositi?: 'qualsiasi' | 'escludi' | 'solo'
}
```

**Default**: `filtri = {}` (= nessun filtro) → mantiene il comportamento
"mostra tutto" per chi non specifica nulla.

**Validazione interna**: se un valore enum è sconosciuto, `console.warn` +
fallback a `'qualsiasi'`. Niente exception (UX dev non blocca runtime).

### 2.2 Mappa FE → BE

| Valore FE | Parametro query | Valore inviato |
|---|---|---|
| `'qualsiasi'` o assente | (non inviato) | — |
| `'escludi'` | `is_solo_componente` o `is_composito` | `false` |
| `'solo'` | `is_solo_componente` o `is_composito` | `true` |

### 2.3 Backward compatibility

Memoria `project_no_produzione_solo_sviluppo`: ZeroErp non in produzione,
breaking change ammessi. La prop legacy `soloComponenti: Boolean` viene
**rimossa**, non deprecata. Tutti i 6 caller riscritti in un singolo
commit. Niente alias temporaneo.

### 2.4 Prop conservate

- `modelValue` (oggetto articolo selezionato)
- `placeholder`
- `disabled`
- `soloAttivi` (default `true`) → resta separata: è una dimensione
  trasversale (soft-delete), non concettualmente parte dei "filtri
  contestuali"

Decisione: tenere `soloAttivi` fuori da `filtri`. Estendibilità simmetrica
(§5) si applica solo ai filtri di dominio.

---

## 3. Matrice cablaggio nei caller

### 3.1 `PreventiviRigaForm`

```vue
<ArticoloLookup
  :model-value="articoloObj"
  :disabled="isEdit"
  :filtri="{ soloComponenti: 'escludi' }"
  :placeholder="t('preventivi.riga_cerca_articolo')"
  @select="onArticoloSelect"
/>
```

**Motivazione**: preventivi vendono articoli "finiti" (standalone o
compositi). I solo-componenti non sono mai unità di vendita.

### 3.2 `ContrattoRigheDrawer` (AGGIUNTA)

```vue
<ArticoloLookup
  v-model="form.articolo_obj"
  @update:modelValue="onArticoloSelected"
  :disabled="formMode === 'edit' || form.tipo_eccezione !== 'AGGIUNTA'"
  :filtri="{ soloComponenti: 'escludi' }"
  :placeholder="t('contratti.select_articolo')"
/>
```

**Motivazione**: AGGIUNTA = articolo fuori-listino. Stesso razionale dei
preventivi. ESCLUSIONE/OVERRIDE non usano `ArticoloLookup` (l'articolo è
già nella riga del listino).

### 3.3 `VersioneDrawer` (riga listino)

```vue
<ArticoloLookup
  v-model="form.articolo_obj"
  @update:modelValue="onArticoloSelected"
  :disabled="formMode === 'edit'"
  :filtri="{ soloComponenti: 'escludi', compositi: 'escludi' }"
/>
```

**Motivazione**:

- `soloComponenti: 'escludi'`: i solo-componenti vivono in
  `listini_righe_componenti` (bundle), non in `listini_righe`.
- `compositi: 'escludi'`: i compositi non hanno una riga propria in
  `listini_righe` (trigger DB `E_LISTINO_RIGA_COMPOSITO_VIETATO`). Oggi
  l'admin può selezionarli e il drawer intercetta il post-select aprendo
  il Dialog bundle. Pre-filtrarli rende il flusso più scorrevole:
  l'admin gestisce i bundle dalla sezione "Prezzi compositi" in cima
  alla lista, non dal lookup riga.

**Conseguenza implementativa**: il blocco di intercettazione in
`VersioneDrawer.onArticoloSelected` ([VersioneDrawer.vue:216-223](../../../../frontend/src/vendite/components/VersioneDrawer.vue#L216))
diventa dead-code e può essere rimosso. Tenere come safety net per ora
oppure rimuovere subito? Proposta: rimuovere (è dead-code, niente
ridondanza difensiva).

### 3.4 `PromoArticoloDrawer`

```vue
<ArticoloLookup
  v-model="form.articolo_obj"
  :filtri="{ soloComponenti: 'escludi' }"
/>
```

**Motivazione**: promo si applica al padre. Il flag
`vale_in_contesto_padre` (vedi §9.5 `modello-componenti-bom.md`) regola
se la promo padre si riflette anche dentro un bundle, ma la promo non si
crea direttamente su un solo-componente (non c'è scenario di vendita).

**Da rivalidare**: se in futuro esistesse un caso "promo specifica solo
sul componente di un bundle" il filtro andrebbe rilassato. Oggi escluso.

### 3.5 `ArticoloBomDrawer` (figlio della BoM)

```vue
<ArticoloLookup
  :model-value="componenteObj"
  :placeholder="t('catalogo.search_componente')"
  :disabled="isFormReadonly"
  :filtri="{ compositi: 'escludi' }"
  @select="onComponenteSelect"
/>
```

**Motivazione**: il figlio di una BoM non può essere a sua volta
composito (no nesting, vedi `modello-componenti-bom.md §9.2`). I
solo-componenti **devono** essere selezionabili (anzi, sono il caso
target di questo lookup). Quindi `soloComponenti = 'qualsiasi'` (assente).

### 3.6 `TestResolverDialog` (admin/dev tool)

Due lookup nel dialog:

- **Lookup articolo target** (riga 193): nessun filtro → resta libero (tool
  diagnostico, l'admin deve poter testare qualsiasi articolo)
- **Lookup articolo padre contesto** (riga 240): `:filtri="{ compositi: 'solo' }"`
  → il padre contesto bundle è per definizione un articolo composito.
  Già visibile dalla `is_composito=true` mostrata in dropdown? Sì, ma
  filtrare alla sorgente è più chiaro.

---

## 4. Step di implementazione

1. **Estendere `ArticoloLookup.vue`**:
   - Aggiungere prop `filtri: Object` (default `{}`)
   - Rimuovere prop `soloComponenti`
   - Helper interno `_buildLookupParams(filtri)` mappa enum → query BE
   - Validazione enum + warn su valori sconosciuti
2. **Cablare i 6 caller** (§3.1..3.6)
3. **Rimuovere dead-code** in `VersioneDrawer.onArticoloSelected`
   (intercettazione composito post-select) → resta solo il flusso ai
   bundle dalla sezione dedicata
4. **Aggiornare il building block** in
   [catalogo-building-block-frontend.md](../frontend/catalogo-building-block-frontend.md):
   nuova prop `filtri` documentata
5. **Aggiornare CLAUDE/AGENTS** se serve: la decisione di tenere
   `soloAttivi` fuori dai `filtri` va menzionata come pattern (filtri
   contestuali di dominio vs flag trasversali)

---

## 5. Estendibilità futura

L'oggetto `filtri` è progettato per crescere. Filtri prevedibili in futuro:

- `tipologiaId: number | number[]` — filtra per `listino_tipologia_id`,
  utile in promo / listini per restringere al sottoinsieme tipologico
- `utility: 'qualsiasi' | 'commodity' | 'commercio'` o id specifico
- `servizio: 'qualsiasi' | 'escludi' | 'solo'` — se mai sarà introdotto
  `is_servizio`

Quando questi filtri saranno utili a un caller, si aggiungono al shape
senza breaking change su quelli esistenti. Naming convenuto:
- enum tri-stato `'qualsiasi' | 'escludi' | 'solo'` per flag boolean
- camelCase semantico, no prefisso `is_`
- id/array per filtri di scope

---

## 6. Test

### 6.1 Test FE manuali (smoke)

Per ogni caller, verificare:

1. Apertura lookup, digitazione codice/descrizione di un articolo
   filtrato → non appare
2. Stesso articolo cercato in altro contesto senza quel filtro → appare
3. Selezione articolo ammesso → flow normale

### 6.2 Test unitari opzionali

`ArticoloLookup.vue` non ha oggi suite Vitest. Se la si introduce in
futuro, casi minimi:

- prop `filtri` vuota → BE chiamato senza `is_solo_componente`/`is_composito`
- prop `filtri.soloComponenti='escludi'` → BE chiamato con
  `is_solo_componente=false`
- prop `filtri.soloComponenti='solo'` + `filtri.compositi='escludi'` →
  BE chiamato con entrambi (`is_solo_componente=true`,
  `is_composito=false`)
- prop `filtri.soloComponenti='valore_sconosciuto'` → warn console,
  comportamento come `'qualsiasi'`

---

## 7. Stima

1-2 sessioni di lavoro FE:

- Estensione `ArticoloLookup.vue` + tipi/validazione: ~30 min
- Cablaggio 6 caller + cleanup dead-code `VersioneDrawer`: ~45 min
- Aggiornamento doc BB FE + CLAUDE/AGENTS (opzionale): ~30 min
- Smoke manuale 6 contesti: ~30 min

---

## 8. Riferimenti

- [ArticoloLookup.vue](../../../../frontend/src/core/components/ArticoloLookup.vue) — componente target
- [lookup_articoli BE](../../../../backend/apps/catalogo/services/catalogo_service.py) `fn_lookup_articoli`
- [modello-componenti-bom.md](../manual/modello-componenti-bom.md) — regole BoM, ruolo `is_solo_componente`
- [catalogo-building-block-frontend.md](../frontend/catalogo-building-block-frontend.md) — catalogo BB FE
- [gestione-listini.md §5.1](../../guide/gestione-listini.md) — tipologie articolo (futuro filtro `tipologiaId`)

---

## 9. Applicazione (2026-05-18)

### 9.1 Modifiche al componente

- [ArticoloLookup.vue](../../../../frontend/src/core/components/ArticoloLookup.vue):
  - Aggiunta prop `filtri: Object` (default `{}`)
  - Rimossa prop legacy `soloComponenti: Boolean` (breaking change, no compat — dev project)
  - Aggiunti helper interni `_normalizzaTriStato`, `_enumAQueryBool`, `_buildLookupParams`
  - Validazione enum con `console.warn` su valori sconosciuti + fallback a `'qualsiasi'`
  - Costante `FILTRO_VALORI_VALIDI` esposta come tupla applicativa
  - Docstring header del componente aggiornata con esempio prop `filtri`

### 9.2 Cablaggio caller (6 punti)

| Caller | File | Filtri |
| --- | --- | --- |
| `PreventiviRigaForm` | [PreventiviRigaForm.vue:561](../../../../frontend/src/vendite/preventivi/components/PreventiviRigaForm.vue#L561) | `{ soloComponenti: 'escludi' }` |
| `ContrattoRigheDrawer` (AGGIUNTA) | [ContrattoRigheDrawer.vue:1011](../../../../frontend/src/vendite/components/ContrattoRigheDrawer.vue#L1011) | `{ soloComponenti: 'escludi' }` |
| `VersioneDrawer` (riga listino) | [VersioneDrawer.vue:556](../../../../frontend/src/vendite/components/VersioneDrawer.vue#L556) | `{ soloComponenti: 'escludi', compositi: 'escludi' }` |
| `PromoArticoloDrawer` | [PromoArticoloDrawer.vue:351](../../../../frontend/src/vendite/components/PromoArticoloDrawer.vue#L351) | `{ soloComponenti: 'escludi' }` |
| `ArticoloBomDrawer` (figlio BoM) | [ArticoloBomDrawer.vue:620](../../../../frontend/src/catalogo/components/ArticoloBomDrawer.vue#L620) | `{ compositi: 'escludi' }` |
| `TestResolverDialog` (target) | [TestResolverDialog.vue:193](../../../../frontend/src/vendite/components/TestResolverDialog.vue#L193) | nessun filtro (admin tool) |
| `TestResolverDialog` (padre contesto) | [TestResolverDialog.vue:240](../../../../frontend/src/vendite/components/TestResolverDialog.vue#L240) | `{ compositi: 'solo' }` |

### 9.3 Cleanup

- `VersioneDrawer.onArticoloSelected`: rimosso il blocco di intercettazione
  post-selezione composito (`if (item?.is_composito === true) openBundleDialog(item)`).
  Dead-code dopo l'introduzione del pre-filter `compositi: 'escludi'`.
  Commento aggiornato per riflettere il nuovo flusso (bundle via sezione
  "Prezzi compositi" in cima alla lista, non via form riga).

### 9.4 Doc

- [catalogo-building-block-frontend.md:355](../frontend/catalogo-building-block-frontend.md):
  voce `ArticoloLookup` riscritta. Rimossa prop fantasma `voce-utility`
  (non esiste nel codice, doc obsoleta). Aggiornata shape `filtri` +
  lista completa dei 6 caller con i valori cablati.

### 9.5 Backward compat

Nessuna. La prop `soloComponenti` non era cablata in nessun caller,
quindi la rimozione è trasparente operativamente. Lo è anche
formalmente: il commit unico riscrive componente + caller + doc nello
stesso passaggio.

### 9.6 Test

- Build vite verde (verifica regressioni statiche, vedi commit relativo)
- Smoke manuale a carico operatore: 6 contesti elencati in §6.1
