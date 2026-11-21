# Refactor igiene codice — dead code + mutazioni prop nei form

> **Tipo**: documento di pianificazione refactor frontend (igiene codice).
> **Branch di lavoro**: `dev/backend-tid`. **Solo frontend.**
> **Data**: 2026-05-27.
> **Origine**: audit eslint emerso dopo il refactor `FormFooter`/`AppDialog`
> (standardizzazione dialog/footer). L'audit ha rivelato 141 problemi eslint
> nel codebase frontend, in larga parte **pre-esistenti** e scoperti solo
> ora che l'output eslint è stato letto sistematicamente.

---

## ✅ COMPLETATO (2026-05-27)

Entrambi i punti chiusi. **`vue/no-mutating-props`: 82 → 0**; output eslint
frontend completamente pulito (0 problemi di qualsiasi tipo); build verde;
smoke funzionale UI verificato.

Eseguita l'**opzione A** (`defineModel`) su tutti e 7 i form, **un form alla
volta**, con build + conteggio eslint verificati a ogni passo.

**Variante adottata — "sicura" (solo figlio).** I form ricevono un oggetto
`reactive` da un composable (`useContattoForm`, `useSoggettoForm`, …), passato
per riferimento e mutato in-place (mai sostituito intero). Quindi:

- **figlio**: `form` passa da `defineProps` a
  `const form = defineModel('form', { type: Object, required: true })`; i
  riferimenti script `props.form.x` diventano `form.value.x`; il **template
  resta invariato** (il ref auto-unwrappa: `v-model="form.x"` = `form.value.x`).
- **padre**: NESSUNA modifica, resta `:form="x.form"`. Si è deliberatamente
  evitato `v-model:form` sul padre: genererebbe `@update:form="x.form = $event"`,
  che — pur dormiente (il figlio non riassegna mai il model intero) —
  riassegnerebbe l'oggetto in closure del composable desincronizzando
  `reset()`/`validate()`. Nessun vantaggio (oggetto già condiviso per
  riferimento), solo rischio latente → scartato.

Ordine eseguito (errori rimossi): AuthUserForm (4) → ContattoForm (8) →
DatiSocietariForm (9) → ContoBancarioForm (13) → SoggettoForm (13) →
IndirizzoSoggettoForm (15) → PreventiviForm (20). I 4 padri di Contatto/
Indirizzo e tutti gli altri padri sono rimasti invariati.

---

## Stato

L'audit eslint (`npx eslint .`) sul frontend riportava **141 problemi**.
Suddivisi in due nature molto diverse per rischio:

| Categoria | N° iniziale | Stato |
|---|---|---|
| Dead code (`no-unused-vars`, `no-useless-assignment`, direttive `eslint-disable` inutili, slot var inutilizzate) | 59 | ✅ **RISOLTO** (punto 1) |
| Mutazione diretta di prop nei form (`vue/no-mutating-props`) | 82 | ⏳ **questo documento** (punto 2) |

Dopo la pulizia del punto 1, l'output eslint è **82 problemi, tutti
`vue/no-mutating-props`** — il rumore è sparito e ora ogni *nuovo* errore
eslint salta all'occhio invece di perdersi.

### Punto 1 — dead code rimosso (fatto)

Pulizia verificata uno a uno (build verde, nessuna regressione):

- import inutilizzati (`Button`, `Select`, `SearchHint`, `computed`,
  `watch`, `nextTick`, `InputNumber`, `DRAWER_WIDTH`, `lookupCodici`,
  `useApiHandler`, `useDrawerClose`, `useNotify`);
- binding inutilizzati mantenendo la **chiamata** quando ha side-effect
  (`useReadonlyMode(...)` provider, `defineProps(...)` macro);
- funzioni morte (`openBA`, `openUtilities`, `openPermessi` — i row-action
  inlineavano già le chiamate);
- variabili/computed mai letti (`hasBase`, `isPromoScaduta`,
  `nonEditableFields`, `pendingConfirmation`, `notify`, ecc.);
- `catch (e)` → `catch` (optional catch binding) dove `e` inutilizzato;
- `let x = null/raw` → `let x` dove l'inizializzatore era sempre sovrascritto;
- direttive `// eslint-disable-next-line no-console` inutili (la regola
  `no-console` non è attiva → erano warning a vuoto).

Regola operativa adottata: **un "unused" si rimuove solo dopo aver
verificato** che non sia usato via template, `defineExpose`, stringa
dinamica, o che la sua chiamata non abbia side-effect (provider/inject,
macro compiler).

---

## Punto 2 — `vue/no-mutating-props` (82, in 7 file)

### Dove

Tutti e 82 sono concentrati nei **form building block** (`core/components/`
+ un form di dominio):

| N° | File |
|---|---|
| 20 | `vendite/preventivi/components/PreventiviForm.vue` |
| 15 | `core/components/IndirizzoSoggettoForm.vue` |
| 13 | `core/components/ContoBancarioForm.vue` |
| 13 | `core/components/SoggettoForm.vue` |
| 9  | `core/components/DatiSocietariForm.vue` |
| 8  | `core/components/ContattoForm.vue` |
| 4  | `core/components/AuthUserForm.vue` |

### Cos'è il pattern

Questi componenti ricevono un oggetto `form` come **prop** e lo editano per
riferimento, tipicamente via `v-model` sui campi:

```vue
<script setup>
const props = defineProps({ form: { type: Object, required: true } })
</script>
<template>
  <!-- v-model su una proprietà della prop `form` -> mutazione della prop -->
  <Select v-model="form.tipo_contatto_id" ... />
  <InputText v-model="form.email" ... />
</template>
```

Il padre passa un `ref` reattivo e il figlio ci scrive dentro:

```vue
<!-- componente padre (drawer) -->
<ContattoForm :form="contatto.form" :errors="contattoErrors" />
```

### Perché eslint lo segnala (e perché oggi funziona)

`vue/no-mutating-props` è un anti-pattern del *one-way data flow* di Vue:
il figlio non dovrebbe scrivere sulla prop, perché:

- la mutazione **funziona** finché la prop è un oggetto/ref condiviso per
  riferimento (è il caso qui: il padre passa il proprio `ref`, le scritture
  si propagano) — per questo l'app funziona;
- ma il flusso dati è **opaco**: leggendo il padre non si vede *chi* muta
  cosa; un domani, se il padre passasse una copia o un computed, le
  modifiche si perderebbero silenziosamente;
- ostacola refactor e testing del componente in isolamento.

È un **debito tecnico stilistico/architetturale**, non un bug: in
pre-produzione il codice gira correttamente.

### Perché NON va "corretto" con un fix di massa

"Sistemarlo alla regola" significa **cambiare il data-flow** di ogni form.
Farlo frettolosamente (o con un fix automatico, che comunque non esiste per
questa regola) apre regressioni reali:

- il form **non salva più** (le modifiche non risalgono al padre);
- **desincronizzazione** padre/figlio (reattività persa);
- rottura di pattern correlati (`classify()` EMPTY/PARTIAL/VALID dei
  contatti/indirizzi, validazioni, prefill).

Questi form sono il cuore di anagrafiche/preventivi: una regressione qui è
visibile e costosa.

### Opzioni di soluzione

**A. `defineModel` (Vue 3.4+) / `v-model` sull'intero form.**
Il figlio dichiara `const form = defineModel('form')` e il padre fa
`v-model:form="..."`. Il figlio scrive su `form.value.xxx`, l'aggiornamento
risale via evento. Pro: idiomatico, flusso esplicito. Contro: tocca padre +
figlio per ogni form, va verificato campo per campo che la reattività
(specie su oggetti annidati) resti corretta. **Rischio medio**, è il target
"giusto".

**B. clone locale + `emit('update:form', ...)`.**
Il figlio clona la prop in uno stato locale, emette al cambio. Più verboso,
gestione manuale del sync. Sconsigliato rispetto ad A.

**C. accettazione esplicita del pattern (eslint-disable mirato).**
Se la decisione architetturale è tenere il pattern "form per riferimento"
(legittimo per building block fortemente accoppiati al padre), si silenzia
la regola **solo in quei 7 file** con commento che spiega il perché:

```js
/* eslint-disable vue/no-mutating-props --
   Form building block: il padre passa un `form` reattivo e questo
   componente lo edita per riferimento (pattern deliberato, vedi
   refactor-codice-morto.md §"Punto 2"). */
```

Pro: output eslint torna pulito subito, zero rischio runtime, l'intento è
documentato. Contro: cristallizza il pattern (ma è una scelta consapevole).

### Raccomandazione

1. **Breve termine (basso rischio)**: opzione **C** — disable mirato +
   commento nei 7 file. Riporta eslint a **0 problemi**, così l'audit resta
   uno strumento utile (ogni nuovo errore è subito visibile) senza toccare
   codice funzionante.
2. **Medio termine (progetto dedicato)**: opzione **A**, un form alla volta,
   con verifica funzionale (create + edit + validazione) per ciascuno. Da
   pianificare come progetto a sé, **mai** in un commit unico di massa.

L'ordine consigliato per il refactor A (dal più isolato/semplice al più
complesso): `AuthUserForm` (4) → `ContattoForm` (8) → `DatiSocietariForm`
(9) → `ContoBancarioForm` (13) → `SoggettoForm` (13) →
`IndirizzoSoggettoForm` (15) → `PreventiviForm` (20).

### Definition of Done ✅

- [x] decisione: **opzione A** (refactor), variante sicura — solo figlio,
      padre invariato (vedi "✅ COMPLETATO" in cima)
- [x] ogni form migrato a `defineModel`; padre invariato (`:form`)
- [x] smoke funzionale per form: create salva, edit salva, validazione,
      prefill, reattività campi annidati
- [x] eslint frontend a 0 `vue/no-mutating-props` (e 0 problemi totali)
- [x] build verde + nessuna regressione su anagrafiche/preventivi

---

## Cosa NON è questo documento

- Non tocca il dead code (punto 1, già risolto).
- Non impone l'opzione A: la decisione A-vs-C è parte del progetto dedicato.
- Non è un fix di massa: ogni form va trattato e verificato singolarmente.

## Riferimenti

- Regola: [`vue/no-mutating-props`](https://eslint.vuejs.org/rules/no-mutating-props.html)
- Pattern form building block: `docs/it/dev/frontend/catalogo-building-block-frontend.md`
  (sezione "Building block form": `SoggettoForm`, `ContattoForm`, ecc.)
- `defineModel`: Vue 3.4+ — composables form esistenti (`useContattoForm`,
  `useSoggettoForm`, ecc.) restano la fonte dello stato; cambia solo *come*
  il figlio lo riceve/aggiorna.

---

*Refactor igiene codice — ZeroErp, 2026-05-27. Punto 1 (dead code) e Punto 2
(mutazioni prop, opzione A variante sicura) entrambi CHIUSI. Documento
completato e spostato in `docs/it/dev/work-done/`.*
