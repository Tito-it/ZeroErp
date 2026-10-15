<script setup>
// Scopo: Autocomplete articolo server-side riutilizzabile cross-dominio.
//
// DUE USI, e non si mescolano:
//
// 1. La RIGA DI UN DOCUMENTO (prop `documento`): righe di preventivo, ordine,
//    bolla, eccezioni di offerta e contratto, versione di listino, distinta
//    (`ARTICOLO` + `articoloPadreId`), promo. Quali articoli ammette la riga
//    lo dice il DB (`catalogo.fn_articoli_ammessi`, la stessa check dei guard):
//    ogni articolo arriva col suo `motivo` (null = ammesso), prima gli ammessi.
//    Un escluso RESTA in elenco, grigio e col motivo sotto: chi cerca un codice
//    preciso sa perche' non lo puo' scegliere. ⛔ Qui la maschera non sceglie
//    filtri: la regola non e' sua (brief-db-articoli-ammessi-per-documento
//    §9.6, Lotto 4). `motiviSelezionabili` dichiara i motivi che NON spengono
//    l'opzione perche' la maschera ha la sua strada per quel caso (la versione
//    di listino propone il composito come bundle: `COMPOSITO_COME_BUNDLE`).
//
// 2. Le CONSULTAZIONI (senza `documento`): filtri della ricerca libera, scelti
//    dal chiamante perche' non sono regole di una riga. Prop `filtri`, shape
//
//      { compositi?: 'qualsiasi' | 'escludi' | 'solo',
//        gestitiAMagazzino?: 'qualsiasi' | 'escludi' | 'solo' }
//
//    'qualsiasi' o assente → nessun parametro; 'escludi' → false; 'solo' →
//    true. Valori sconosciuti → warn console + fallback a 'qualsiasi'.
//    `soloComponenti` ed `escludiDestinazione` sono ritirati il 2026-10-14: li
//    usavano solo le righe di documento, ed erano una copia dei guard.
import { computed, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import { testoMotivi } from '../../core/composables/useDrawerActions'
import { useServerAutocomplete } from '../../core/composables/useServerAutocomplete'
import { useAutocompleteRefineHint } from '../../core/composables/useAutocompleteRefineHint'
import { useLookupDisplayModel } from '../../core/composables/useLookupDisplayModel'
import { lookupArticoli } from '../api/catalogo'
import AutoComplete from 'primevue/autocomplete'

const { t, te } = useI18n()

// Mappa dichiarativa dei filtri ammessi: chiave (camelCase, lato FE) →
// nome parametro query lato BE. Aggiungere qui per estendere a nuovi
// filtri tri-stato (vedi piano `piano-filtri-articolo-lookup.md` §5).
const FILTRI_TRI_STATO = Object.freeze({
  compositi:      'is_composito',
  // R-5 (brief magazzino 2-bis, 2026-09-23): lo passa il picker di riga di
  // inventari e rettifiche — un articolo non gestito a magazzino si salva,
  // ma il piano lo marca NON_POSTABILE e la registrazione rifiuta tutto.
  // ⛔ Assente = nessun filtro: altrove la tendina continua a proporre tutto.
  gestitiAMagazzino: 'gestito_a_magazzino',
})
const FILTRO_VALORI_VALIDI = Object.freeze(['qualsiasi', 'escludi', 'solo'])

// Quante righe chiede il picker, nei due usi: una sede, il BE la tratta come
// tetto (oltre, `troncato` e il suggerimento di affinare).
const LIMITE_RIGHE = 20

const props = defineProps({
  modelValue: { type: Object, default: null },
  filtri: { type: Object, default: () => ({}) },
  soloAttivi: { type: Boolean, default: true },
  // La riga di un documento: codice di config.tipi_entita (PREVENTIVO,
  // ORDINE_VENDITA, DDT_VENDITA, OFFERTA_COMMERCIALE, CONTRATTO,
  // LISTINO_VERSIONE, ARTICOLO, PROMO_ARTICOLO). Con questa prop `filtri` e
  // `soloAttivi` non si usano: propone solo attivi, e li giudica il DB.
  documento: { type: String, default: null },
  // L'id della testata salvata (o della versione di listino): il guard giudica
  // la riga contro la testata salvata, e il picker fa la stessa domanda (A-1).
  documentoId: { type: Number, default: null },
  // Offerta e contratto: AGGIUNTA, OVERRIDE o ESCLUSIONE.
  tipoEccezione: { type: String, default: null },
  // Distinta (`documento` ARTICOLO): il padre.
  articoloPadreId: { type: String, default: null },
  // I `reason` del DB che lasciano l'opzione selezionabile (vedi sopra).
  motiviSelezionabili: { type: Array, default: () => [] },
  placeholder: { type: String, default: null },
  disabled: { type: Boolean, default: false }
})

const emit = defineEmits(['update:modelValue', 'select'])

// Scopo: validazione one-shot di `props.filtri`. Computed → riesegue
// solo al cambio della prop, non a ogni keystroke (no log-spam su valori
// sconosciuti). Emette warn per:
//   - chiavi sconosciute (non in `FILTRI_TRI_STATO`)
//   - valori non in `FILTRO_VALORI_VALIDI`
// Ritorna un map { chiaveFE → valore enum normalizzato } che esclude
// `'qualsiasi'`, valori invalidi e chiavi sconosciute.
const filtriValidati = computed(() => {
  const out = {}
  const raw = props.filtri || {}
  for (const [chiave, valore] of Object.entries(raw)) {
    if (!(chiave in FILTRI_TRI_STATO)) {
      console.warn(
        `[ArticoloLookup] chiave sconosciuta in filtri: '${chiave}'. `
        + `Ammesse: ${Object.keys(FILTRI_TRI_STATO).join(', ')}.`,
      )
      continue
    }
    if (valore === undefined || valore === null || valore === 'qualsiasi') {
      continue
    }
    if (!FILTRO_VALORI_VALIDI.includes(valore)) {
      console.warn(
        `[ArticoloLookup] valore non valido per filtri.${chiave}: `
        + `${JSON.stringify(valore)}. Atteso: ${FILTRO_VALORI_VALIDI.join('|')}.`,
      )
      continue
    }
    out[chiave] = valore
  }
  return out
})

// Scopo: costruisce i query params per lookupArticoli a partire dalla
// query testuale. Riga di documento: il contesto della riga, e nient'altro
// (il BE rifiuta i filtri liberi accanto a `documento`). Consultazione: i
// filtri normalizzati, 'escludi' → false, 'solo' → true.
function _buildLookupParams(query) {
  if (props.documento) {
    const params = { search: query, limit: LIMITE_RIGHE, documento: props.documento }
    if (props.documentoId != null) params.documento_id = props.documentoId
    if (props.tipoEccezione) params.tipo_eccezione = props.tipoEccezione
    if (props.articoloPadreId) params.articolo_padre_id = props.articoloPadreId
    return params
  }
  const params = { search: query, attivo: props.soloAttivi, limit: LIMITE_RIGHE }
  for (const [chiave, valore] of Object.entries(filtriValidati.value)) {
    params[FILTRI_TRI_STATO[chiave]] = (valore === 'solo')
  }
  return params
}

// Scopo: un articolo che il documento non ammette resta in elenco ma non si
// sceglie, salvo che il suo motivo sia fra quelli che la maschera gestisce.
function _escluso(r) {
  return !!r.motivo && !props.motiviSelezionabili.includes(r.motivo.reason)
}

// ⚠️ L'elenco degli articoli e' TAGLIATO dal tetto del lookup (50 lato
//    repository, 20 di default dalla view), e fino al 2026-09-10 chi guardava
//    non aveva modo di saperlo: il backend dichiarava `troncato` e a video non
//    lo leggeva nessuno. Il footer lo dice, con la stessa forma degli altri
//    quattro lookup ricchi — la condizione vive nel composable, non qui.
const { mostrati, daAffinare, onResponse } = useAutocompleteRefineHint()

const ac = useServerAutocomplete(async (query) => {
  return await lookupArticoli(_buildLookupParams(query))
}, {
  minLength: 3,
  transform: (res) => (res.data.data.results ?? res.data.data ?? []).map(r => ({
    ...r,
    _display: buildDisplay(r),
    _escluso: _escluso(r),
    // Il perche' in testo: la sede unica dei motivi (`testoMotivi`, coi
    // `valori` nei segnaposto), la stessa dei pulsanti spenti.
    _motivoTesto: r.motivo ? testoMotivi(t, te, r.motivo) : '',
  })),
  onResponse,
})

// Il contesto della riga e' cambiato (altro documento, altro tipo d'eccezione,
// altro padre): i suggerimenti a video erano giudicati su quello vecchio.
watch(
  () => [props.documento, props.documentoId, props.tipoEccezione, props.articoloPadreId],
  () => { ac.suggestions.value = [] },
)

function buildDisplay(r) {
  if (!r) return ''
  if (r.codice && r.descrizione) return `${r.codice} — ${r.descrizione}`
  return r.codice || r.descrizione || `#${r.id}`
}

// Normalizza il modelValue garantendo `_display` (anti "[object Object]" sui
// restore con sole {id, codice, descrizione}). BB condiviso (B6).
const displayedModel = useLookupDisplayModel(() => props.modelValue, buildDisplay)

function onSelect(event) {
  emit('update:modelValue', event.value)
  emit('select', event.value)
}

function onClear() {
  emit('update:modelValue', null)
}
</script>

<template>
  <AutoComplete
    :modelValue="displayedModel"
    :suggestions="ac.suggestions.value"
    @complete="ac.onSearch"
    @item-select="onSelect"
    @clear="onClear"
    optionLabel="_display"
    optionDisabled="_escluso"
    :placeholder="placeholder || t('catalogo.search_placeholder')"
    :disabled="disabled"
    dropdown
  >
    <template #option="{ option }">
      <div class="app-lookup-option">
        <div class="app-lookup-option__primary">{{ option._display }}</div>
        <div v-if="option._motivoTesto" class="app-lookup-option__meta">{{ option._motivoTesto }}</div>
      </div>
    </template>
    <template #footer v-if="daAffinare">
      <div class="app-lookup-hint">
        {{ t('common.refine_hint_troncato', { shown: mostrati }) }}
      </div>
    </template>
  </AutoComplete>
</template>
