<script setup>
// Scopo: Modale di personalizzazione colonne per <ListaConfigurabile>.
// Permette: toggle visibilita', riordino colonne (▲/▼), edit larghezza,
// righe per pagina, reset preferenza utente. Le colonne tipo 'identificatore' e 'azione'
// non sono toggleabili (UI-disabled, tooltip esplicativo).
//
// Pattern: lavora su una copia locale `localConfig`, propaga al composable
// genitore solo a "Salva" — Annulla scarta tutte le modifiche locali.
// Niente drag&drop drag-and-drop: pulsanti ▲/▼ per riordinare (zero
// dipendenze esterne).
//
// Drift risk identificazione "colonne nuove": il BE ritorna solo il
// conteggio aggregato (`colonne_nuove`), non un flag per-colonna.
// Mostriamo il badge globale; future evoluzioni del fn DB potrebbero
// aggiungere `is_new: true` per evidenziare singolarmente.

import { computed, ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import Button from 'primevue/button'
import AppDrawer from './AppDrawer.vue'
import ToggleSwitch from 'primevue/toggleswitch'
import InputNumber from 'primevue/inputnumber'
import Tag from 'primevue/tag'
import Select from 'primevue/select'
import { etichettaColonna } from '../utils/i18nLabel'
import { DRAWER_WIDTH, MANAGE_ICONS } from '../constants'
import { useConfirmAction } from '../composables/useConfirmAction'
import { useDrawerFormPreserve, valoriUguali } from '../composables/useDrawerFormPreserve'
import { misureOpzioni } from '../misurePagina'
import { ORIGINE_PREFERENZA } from '../preferenzaPerChiave'


const { confirmAction } = useConfirmAction()

// Limiti UX per la larghezza colonna in pixel. Coerenti con i tipici
// `larghezza_default` del catalogo (40-300 px) ma con margine ampio per
// colonne future (testi lunghi, json render). Step 20 = scatto naturale.
const _LARGHEZZA_LIMITS = { min: 40, max: 800, step: 20 }

const props = defineProps({
  visible: { type: Boolean, required: true },
  // config corrente (passata dal genitore <ListaConfigurabile>).
  config: { type: Object, default: null },
  // catalogo arricchito (etichetta, gruppo, formato, ecc.).
  catalogo: { type: Object, default: null },
  // count "N nuove colonne disponibili" — badge informativo.
  colonneNuove: { type: Number, default: 0 },
  // Loading lato composable (save/reset in corso).
  loading: { type: Boolean, default: false },
  // Codice lista (per i18n contestuale eventuale).
  codice: { type: String, default: '' },
})


const emit = defineEmits(['update:visible', 'apply', 'reset'])
const { t, te } = useI18n()

// Copia locale modificabile della config. Resetata ad ogni open per
// scartare modifiche di una sessione precedente di apertura modale.
const localColonne = ref([])
// Righe per pagina: la misura SCELTA dall'utente, `null` = «come lo standard»
// (preferenza per chiave, 2026-11-01). Una misura che viene dal preset non e'
// una scelta: il campo parte su «Come lo standard».
const localPagina = ref(null)

// Modifiche non salvate: si confronta l'elenco senza `ordine`, che il
// riordino rinumera 1..N (l'ordine lo dice gia' la posizione: spostare e
// rimettere a posto non e' una modifica), e con `visibile` come lo mostra
// il toggle (assente = visibile). Prima del watch immediate (TDZ).
const statoDaSalvare = computed(() => ({
  colonne: localColonne.value.map((c) => ({
    codice: c.codice,
    visibile: c.visibile !== false,
    larghezza: c.larghezza ?? null,
  })),
  pagina: localPagina.value,
}))
const { fissa, modificato, chiudiConConferma, fotografia } =
  useDrawerFormPreserve(statoDaSalvare, { visibile: () => props.visible })

watch(
  () => [props.visible, props.config],
  ([open]) => {
    if (open && props.config?.colonne) {
      // Deep-clone per non mutare la config del genitore prima di Salva.
      localColonne.value = JSON.parse(JSON.stringify(props.config.colonne))
      localPagina.value = props.config.origine?.pagina_dimensione === ORIGINE_PREFERENZA
        ? props.config.pagina_dimensione
        : null
      fissa()
    }
  },
  { immediate: true },
)

// Le voci di «Righe per pagina»: «Come lo standard (N)» e le misure del
// catalogo (`ui.misure_pagina`), le stesse del paginatore.
// ⚠️ La voce `null` e' anche il placeholder: col valore `null` il Select di
//    PrimeVue mostra il placeholder, non l'etichetta della voce.
const opzioniPagina = computed(() => [
  {
    label: t('lista_config.pagina_standard', { n: props.config?.pagina_dimensione_standard ?? '' }),
    value: null,
  },
  ...misureOpzioni().map((m) => ({ label: String(m), value: m })),
])

// Map metadata catalogo per codice — lookup O(1) durante render.
const catalogoByCodice = computed(() => {
  const map = new Map()
  for (const c of props.catalogo?.colonne ?? []) {
    map.set(c.codice, c)
  }
  return map
})

// Colonne raggruppate per gruppo (preservando ordine corrente delle
// localColonne). Le colonne senza gruppo vanno in un gruppo speciale.
const gruppiOrdinati = computed(() => {
  const buckets = new Map() // gruppo -> {label, gruppo_ordine, colonne[]}
  for (const c of localColonne.value) {
    const meta = catalogoByCodice.value.get(c.codice) || {}
    const gruppo = meta.gruppo || t('lista_config.gruppo_altro')
    const gruppoOrdine = meta.gruppo_ordine ?? 9999
    if (!buckets.has(gruppo)) {
      buckets.set(gruppo, { label: gruppo, ordine: gruppoOrdine, colonne: [] })
    }
    buckets.get(gruppo).colonne.push({ ...c, _meta: meta })
  }
  return [...buckets.values()].sort((a, b) =>
    a.ordine - b.ordine || a.label.localeCompare(b.label),
  )
})

// Scopo: toggleabile = NON identificatore e NON azione.
function isToggleable(meta) {
  const tipo = meta?.tipo_colonna
  return tipo !== 'identificatore' && tipo !== 'azione'
}

// Scopo: aggiorna proprieta' su una colonna specifica. Lavora su
// localColonne (NON sulla config del genitore).
function updateColonna(codice, mutator) {
  const idx = localColonne.value.findIndex((c) => c.codice === codice)
  if (idx >= 0) {
    const next = { ...localColonne.value[idx] }
    mutator(next)
    localColonne.value[idx] = next
  }
}

// Scopo: sposta una colonna su/giu' nell'array localColonne.
//        Riassegna `ordine` linearmente dopo lo swap per mantenere
//        coerente il valore inviato al BE.
function move(codice, direction) {
  const idx = localColonne.value.findIndex((c) => c.codice === codice)
  if (idx < 0) return
  const target = direction === 'up' ? idx - 1 : idx + 1
  if (target < 0 || target >= localColonne.value.length) return
  const arr = [...localColonne.value]
  ;[arr[idx], arr[target]] = [arr[target], arr[idx]]
  // Riassegna ordine lineare 1..N.
  for (let i = 0; i < arr.length; i++) {
    arr[i] = { ...arr[i], ordine: i + 1 }
  }
  localColonne.value = arr
}

// Scopo: salva le modifiche — emit verso il genitore con la nuova
// lista colonne. Il genitore chiama useListaConfig.applyChange + save.
// ⭐ Le colonne si mandano solo se sono cambiate davvero, con lo stesso
//    confronto di `modificato`: la preferenza e' per chiave
//    (`preferenzaPerChiave`), e colonne riscritte uguali — spostate e rimesse
//    a posto, spente e riaccese — sembrerebbero scelte e congelerebbero quelle
//    dello standard a chi ha cambiato solo le righe per pagina.
function onSave() {
  const payload = { pagina_dimensione: localPagina.value }
  if (!fotografia.value || !valoriUguali(statoDaSalvare.value.colonne, fotografia.value.colonne)) {
    payload.colonne = localColonne.value
  }
  emit('apply', payload)
}

// Scopo: reset preferenza utente. Conferma dialog -> emit('reset').
//        Il genitore chiama useListaConfig.reset() che fa DELETE +
//        ricarica la config dalla cascata BE.
function onReset() {
  confirmAction({
    header: t('lista_config.reset_confirm_header'),
    message: t('lista_config.reset_confirm_message'),
    danger: true,
    onAccept: () => {
      emit('reset')
    },
  })
}
</script>

<template>
  <!-- Il chrome e' di AppDrawer dal 2026-10-03
       (work-done/analisi-fe-chrome-drawer.md, D-10): la testata e'
       quella di tutti i drawer, col conteggio delle colonne nuove; il footer
       e' quello del guscio, con «Ripristina» nello slot `#footer-azioni`. Ogni uscita passa dalla
       conferma, l'Annulla compreso (`chiudi` dello slot). -->
  <AppDrawer
    :visible="visible"
    :title="t('lista_config.modal_title')"
    :icon="MANAGE_ICONS.PERSONALIZZA"
    :action="t('common.edit')"
    :width="DRAWER_WIDTH.SIMPLE"
    :proteggi-corpo="false"
    :dismissable="!loading"
    :modificato="modificato"
    :conferma-uscita="chiudiConConferma"
    :conteggio="colonneNuove"
    :conteggio-tooltip="t('lista_config.colonne_nuove_tooltip', { count: colonneNuove })"
    :loading="loading"
    @update:visible="(v) => emit('update:visible', v)"
    @save="onSave"
  >
    <div class="lista-config-body">
      <div class="lista-config-pagina">
        <label for="lista-config-pagina">{{ t('lista_config.pagina_dimensione') }}</label>
        <Select
          v-model="localPagina"
          input-id="lista-config-pagina"
          :options="opzioniPagina"
          option-label="label"
          option-value="value"
          :placeholder="opzioniPagina[0].label"
          class="app-filter-w-md"
          v-tooltip.bottom="t('lista_config.pagina_tooltip')"
        />
      </div>
      <div
        v-for="(gruppo, gIdx) in gruppiOrdinati"
        :key="gruppo.label"
      >
        <h4 class="lista-config-gruppo-label">{{ gruppo.label }}</h4>
        <div
          v-for="(col, i) in gruppo.colonne"
          :key="col.codice"
          class="lista-config-row"
        >
          <ToggleSwitch
            :model-value="col.visibile !== false"
            :disabled="!isToggleable(col._meta)"
            v-tooltip.left="
              isToggleable(col._meta)
                ? null
                : t('lista_config.colonna_obbligatoria')
            "
            @update:model-value="(v) => updateColonna(col.codice, (c) => (c.visibile = v))"
          />
          <div class="lista-config-row-label">
            <!-- ⚠️ NON `col._meta.etichetta`: quella e' l'etichetta italiana
                 del seed, e la modale restava in italiano in qualunque lingua.
                 La chiave i18n arriva sia dalla config sia (dal 2026-08-22) dal
                 catalogo: la sceglie `etichettaColonna`, la stessa funzione che
                 intesta le colonne della tabella — altrimenti la modale e la
                 lista chiamerebbero la stessa colonna in due modi. -->
            <span :title="col._meta?.etichetta_estesa || ''">
              {{ etichettaColonna(t, te, { config: col, meta: col._meta }) }}
            </span>
            <Tag
              v-if="col._meta?.sensibile"
              :value="t('lista_config.tag_sensibile')"
              severity="warning"
            />
          </div>
          <div class="lista-config-row-actions">
            <InputNumber
              :model-value="col.larghezza"
              :placeholder="String(col._meta?.larghezza_default ?? '')"
              :min="_LARGHEZZA_LIMITS.min"
              :max="_LARGHEZZA_LIMITS.max"
              :step="_LARGHEZZA_LIMITS.step"
              show-buttons
              button-layout="horizontal"
              :input-style="{ width: '54px' }"
              v-tooltip.bottom="t('lista_config.larghezza_tooltip')"
              @update:model-value="(v) => updateColonna(col.codice, (c) => (c.larghezza = v ?? null))"
            />
            <Button
              :icon="MANAGE_ICONS.SPOSTA_SU"
              text
              rounded
              size="small"
              :disabled="gIdx === 0 && i === 0"
              v-tooltip.top="t('lista_config.sposta_su')"
              @click="move(col.codice, 'up')"
            />
            <Button
              :icon="MANAGE_ICONS.SPOSTA_GIU"
              text
              rounded
              size="small"
              :disabled="
                gIdx === gruppiOrdinati.length - 1 &&
                i === gruppo.colonne.length - 1
              "
              v-tooltip.top="t('lista_config.sposta_giu')"
              @click="move(col.codice, 'down')"
            />
          </div>
        </div>
      </div>
    </div>

    <!-- «Ripristina» accanto ad Annulla/Salva: lo slot `#footer-azioni` del
         guscio, che tiene footer e uscita (ogni uscita passa dalla conferma). -->
    <template #footer-azioni>
      <Button
        :label="t('lista_config.reset_preferenza')"
        :icon="MANAGE_ICONS.RIPRISTINA_DEFAULT"
        severity="secondary"
        text
        :disabled="loading"
        @click="onReset"
      />
    </template>
  </AppDrawer>
</template>

<style scoped>
.lista-config-body {
  display: flex;
  flex-direction: column;
  gap: 1rem;
}
.lista-config-pagina {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 0.5rem;
}
.lista-config-gruppo-label {
  margin: 0 0 0.25rem 0;
  font-size: var(--app-font-size-sm);
  text-transform: uppercase;
  color: var(--app-text-muted);
}
.lista-config-row {
  display: grid;
  grid-template-columns: auto 1fr auto;
  align-items: center;
  gap: 0.5rem;
  padding: 0.25rem 0;
  border-bottom: 1px solid var(--app-drawer-section-border);
}
.lista-config-row-label {
  display: flex;
  align-items: center;
  gap: 0.25rem;
  min-width: 0;
}
.lista-config-row-label > span {
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
.lista-config-row-actions {
  display: flex;
  align-items: center;
  gap: 0.25rem;
}
</style>
