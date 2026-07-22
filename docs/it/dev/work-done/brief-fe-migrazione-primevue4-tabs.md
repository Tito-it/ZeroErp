# Brief FE — Migrazione residui PrimeVue 3 → 4 (`TabView` → `Tabs`, `InputSwitch` → `ToggleSwitch`)

> **Tipo**: brief operativo FE · **Target**: `dev/backend-tid` · **Data**: 2026-07-22
> · **Owner**: Tid · **Stato**: ☐ **DA REALIZZARE** · **Priorità**: 🟡 MEDIA
> (nessuna funzionalità rotta oggi: le due catene CSS convivono. È debito che
> **fa scrivere codice nuovo sbagliato** — vedi §1).
>
> **Perimetro**: SOLO FE. Nessuna modifica BE, DB, API o i18n di contenuto.
> **Contesto**: non siamo in produzione ([[project_no_produzione_solo_sviluppo]])
> → migrazione secca, nessuna compatibilità da mantenere.
> **Origine**: bug 2026-07-22 sui tab della vista «Code di lavoro» (§1).

---

## 1. Perché — non è cosmesi, è la doc che induce in errore

Siamo su **PrimeVue 4.5**, ma 7 view usano ancora `TabView` (PrimeVue 3) e
`frontend-standards.md` **prescriveva `TabView`** come pattern da seguire.
Conseguenza concreta, non ipotetica: la vista «Code di lavoro» (cantiere code) è
stata scritta seguendo quella regola e ha prodotto **due bug in sequenza**:

1. i tab sparivano appena la tabella si popolava — la classe `app-tab-content`,
   documentata per la catena `.p-tabview`, applicata al contenitore `Tabs` (v4)
   comprimeva la `TabList` fuori vista. **Sintomo dipendente dai dati**: chi
   vedeva poche righe non notava nulla, il super admin «perdeva» i tab;
2. tolta la classe, il contenuto non scrollava più: la catena flex per `.p-tabs`
   **non esisteva** in `main.css` (c'era solo quella per `.p-tabview`).

Entrambi corretti il 2026-07-22 (catena `.p-tabs` aggiunta, standard riscritto con
`Tabs` come regola e `TabView` marcato legacy). Ma finché il legacy resta:

- convivono **due catene CSS** per la stessa funzione, con classi diverse;
- chi legge il codice esistente trova 7 esempi del pattern deprecato contro 8 del
  nuovo, e non sa quale copiare.

## 2. Perimetro esatto (verificato sul codice, 2026-07-22)

### 2.1 `TabView` → `Tabs` — 7 file, 24 TabPanel

| File | TabPanel |
| --- | --- |
| `anagrafiche/views/IndirizziView.vue` | 7 |
| `pratiche/components/PraticaDrawer.vue` | 6 |
| `amministrazione/views/MatriciListView.vue` | 3 |
| `ui/views/PersonalizzazioniListeTecnicheView.vue` | 2 |
| `ui/views/GestionePersonalizzazioniListeView.vue` | 2 |
| `amministrazione/components/OperatoreDrawer.vue` | 2 |
| `config/views/ConfigurazioneDocumentiView.vue` | 2 |

✅ **La migrazione è meccanica**: nessuno dei 7 usa `activeIndex` né `v-for` su
`TabPanel` (verificato). Non c'è quindi **nessuno stato indice→chiave da
ridisegnare**: si riscrive il template e basta.

### 2.2 `InputSwitch` → `ToggleSwitch` — 3 file

`core/components/dash/DashboardWidgetModal.vue` · `core/components/NoteDrawer.vue`
· `core/components/ListaColonneModal.vue`

### 2.3 Già migrati — non toccare

`Dropdown`, `Calendar`, `OverlayPanel`, `Sidebar`: **0 usi** residui.

## 3. Mappa di migrazione

```vue
<!-- PRIMA (PrimeVue 3) -->
<TabView lazy :key="tabViewKey">
  <TabPanel :header="t('indirizzi.tab_indirizzi')">…</TabPanel>
  <TabPanel :header="t('indirizzi.tab_comuni')">…</TabPanel>
</TabView>

<!-- DOPO (PrimeVue 4) -->
<Tabs value="indirizzi" lazy>
  <TabList>
    <Tab value="indirizzi">{{ t('indirizzi.tab_indirizzi') }}</Tab>
    <Tab value="comuni">{{ t('indirizzi.tab_comuni') }}</Tab>
  </TabList>
  <TabPanels>
    <TabPanel value="indirizzi">…</TabPanel>
    <TabPanel value="comuni">…</TabPanel>
  </TabPanels>
</Tabs>
```

Import: `primevue/tabs`, `primevue/tablist`, `primevue/tab`, `primevue/tabpanels`;
`primevue/tabpanel` **resta invariato** (stesso path in v3 e v4 — per questo la
sola presenza di quell'import non indica legacy: cercare `primevue/tabview`).

Chiavi `value`: **stringhe stabili e parlanti** (`indirizzi`, `comuni`…), mai
indici numerici — sono ciò che rende il tab attivo deep-linkabile in futuro.

## 4. Punti di attenzione (qui si nascondono i difetti)

1. **`tabViewKey` va ELIMINATO, non portato avanti.** Tutti e 7 i file hanno un
   `ref(0)` incrementato per forzare il remount del TabView (in `IndirizziView`
   addirittura `onMounted → nextTick → key++`): è un workaround di un difetto di
   layout di TabView v3. Con `Tabs` il reset del tab attivo si fa assegnando
   `v-model:value` alla chiave del primo tab — niente remount, niente `:key`.
   Portarlo avanti significherebbe trascinare complessità morta.
2. **`lazy` + `onMounted`**: con `lazy` ogni attivazione del tab è un **mount**.
   Il primo caricamento dati va in `onMounted` — il solo `onActivated` NON scatta
   per un discendente montato dopo l'attivazione della rotta, e il tab resta
   vuoto per sempre (bug reale, vedi `CodaLavoriTab.vue`).
3. **`app-tab-content` NON va sul contenitore `<Tabs>`** ma sul div root del
   contenuto dentro ogni `TabPanel` (è la causa del bug §1.1).
4. **DataTable nel tab**: servono `scrollable` + `scroll-height="flex"`, altrimenti
   la catena flex esiste ma la tabella non scrolla.
5. **Drawer**: `PraticaDrawer` e `OperatoreDrawer` hanno i tab **dentro un Drawer**,
   non in `.app-page` → la catena `.app-page > .p-tabs` non li intercetta.
   Verificare l'altezza nel contesto drawer e, se serve, aggiungere la catena
   equivalente in `main.css` (non CSS scoped: sarebbe la 2ª copia).
6. **`ToggleSwitch`**: verificare le prop rispetto a `InputSwitch` (il binding
   `v-model` è equivalente; controllare eventuali `trueValue`/`falseValue`).

## 5. Piano

| # | Step | Stato |
| --- | --- | --- |
| 1 | Migrare le **2 view semplici** (`ConfigurazioneDocumentiView`, `OperatoreDrawer`) come pilota: fissano il pattern e sciolgono il dubbio §4.5 sul drawer | ☐ |
| 2 | Migrare le restanti 5 (`IndirizziView`, `PraticaDrawer`, `MatriciListView`, le 2 `*PersonalizzazioniListe*`) | ☐ |
| 3 | Rimuovere `tabViewKey` (ref + incrementi + `:key`) in tutti e 7 | ☐ |
| 4 | `InputSwitch` → `ToggleSwitch` nei 3 componenti | ☐ |
| 5 | **Eliminare la catena `.app-page > .p-tabview > …`** da `main.css` e la sezione «Legacy» di `frontend-standards.md` | ☐ |
| 6 | Verifica manuale per-schermata (§6) + lint + build | ☐ |

Lo step 5 è possibile **solo dopo** che 1-3 sono completi: la catena `.p-tabview`
serve finché esiste un `TabView`.

## 6. Definition of done

Le tab sono un componente **visivo**: lint e build non ne provano il
funzionamento. Per ognuna delle 7 schermate serve la verifica a mano:

1. i tab si **vedono** e restano fissi anche con la lista piena (è il bug §1.1,
   che si manifesta **solo con abbastanza righe** — provare con dati veri);
2. il contenuto **scrolla** internamente, col paginator visibile in fondo;
3. cambiando tab il contenuto **si carica** (regressione §4.2);
4. il tab attivo si resetta come prima dove era previsto (ex `tabViewKey`);
5. nei due drawer: altezza corretta senza scrollbar doppia.

Chiusura: `grep -rn "primevue/tabview\|primevue/inputswitch" frontend/src` → **0
risultati**, e `grep -c "p-tabview" frontend/src/assets/main.css` → **0**.

## 7. Riferimenti

- Standard aggiornato: `docs/it/dev/frontend/frontend-standards.md` §«Pattern
  Tab-View» (regole v4 + elenco legacy)
- Catena CSS v4: `frontend/src/assets/main.css`, blocco `.app-page > .p-tabs`
- Esempi corretti già in repo: `vendite/resi/views/ResiView.vue`,
  `strumenti/views/CodeLavoroView.vue` (+ `strumenti/components/CodaLavoriTab.vue`
  per il pattern `onMounted`/`onActivated`)
- Origine dei bug: brief cantiere code
  [brief-be-fe-gestione-code-lavori-stampa.md](../work-done/brief-be-fe-gestione-code-lavori-stampa.md)
