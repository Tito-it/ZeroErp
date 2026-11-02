<script setup>
// Scopo: Modale di personalizzazione delle card della dashboard home.
// Permette: toggle visibilita' di ogni widget, riordino (▲/▼), reset
// della preferenza utente. Gemella di <ListaColonneModal> per le liste.
//
// Pattern: lavora su una copia locale, propaga al composable genitore
// solo a "Salva" — Annulla scarta tutte le modifiche locali. Riordino a
// pulsanti e non drag&drop, come per le colonne: zero dipendenze esterne
// e comportamento identico a quello che l'utente gia' conosce.
//
// Il pool mostrato e' `config.widget` cosi' com'e': la fn DB ha gia'
// escluso i widget che l'utente non puo' vedere e incluso quelli nuovi
// (con visibile=false). Qui non si filtra nulla — filtrare di nuovo lato
// FE rischierebbe solo di divergere dalla verita' del BE.

import { computed, ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import Button from 'primevue/button'
import ToggleSwitch from 'primevue/toggleswitch'
import Tag from 'primevue/tag'
import AppDrawer from '../AppDrawer.vue'
import { DRAWER_WIDTH, MANAGE_ICONS } from '../../constants'
import { useConfirmAction } from '../../composables/useConfirmAction'
import { useDrawerFormPreserve } from '../../composables/useDrawerFormPreserve'



const { confirmAction } = useConfirmAction()

const props = defineProps({
  visible: { type: Boolean, required: true },
  // Config corrente della dashboard (dal composable genitore).
  config: { type: Object, default: null },
  // Count "N nuove card disponibili" — badge informativo.
  widgetNuovi: { type: Number, default: 0 },
  // Cap di card mostrabili in home (dal preset risolto).
  dimensioneMax: { type: Number, default: 8 },
  // Loading lato composable (save/reset in corso).
  loading: { type: Boolean, default: false },
})

const emit = defineEmits(['update:visible', 'apply', 'reset'])
const { t, te } = useI18n()

// Copia locale modificabile. Risincronizzata ad ogni apertura per
// scartare modifiche di una sessione precedente.
const localWidget = ref([])

// Modifiche non salvate: si confronta cio' che il Salva manda (codice e
// visibilita', nell'ordine dell'elenco), non `ordine`, che il riordino
// rinumera 1..N — spostare e rimettere a posto non e' una modifica.
// Prima del watch immediate che chiama `fissa()` (TDZ).
const widgetDaSalvare = computed(() =>
  localWidget.value.map(w => ({ codice: w.codice, visibile: Boolean(w.visibile) })),
)
const { fissa, modificato, chiudiConConferma } =
  useDrawerFormPreserve(widgetDaSalvare, { visibile: () => props.visible })

watch(
  () => [props.visible, props.config],
  ([open]) => {
    if (open && Array.isArray(props.config?.widget)) {
      localWidget.value = JSON.parse(JSON.stringify(props.config.widget))
        .sort((a, b) => (a.ordine ?? 0) - (b.ordine ?? 0))
      fissa()
    }
  },
  { immediate: true },
)

// Quante card sono attualmente selezionate come visibili.
const nVisibili = computed(
  () => localWidget.value.filter(w => w.visibile).length,
)

// Superato il cap del preset: l'utente ha selezionato piu' card di
// quante la home ne mostri. Non blocchiamo il salvataggio (la
// preferenza resta valida e il cap potrebbe crescere), ma lo diciamo:
// un troncamento silenzioso si legge come "card sparita".
const oltreCap = computed(
  () => props.dimensioneMax > 0 && nVisibili.value > props.dimensioneMax,
)

// Scopo: etichetta i18n del widget, con fallback sull'etichetta di
//        catalogo quando la traduzione non esiste ancora.
function labelDi(widget) {
  const key = widget?.etichetta_i18n_key
  if (key && te(key)) return t(key)
  return widget?.etichetta || widget?.codice || ''
}

// Scopo: sposta un widget di una posizione e rinumera l'ordine in modo
//        lineare 1..N, cosi' il payload salvato non eredita buchi o i
//        `+10000` che la fn DB assegna ai widget nuovi.
function move(codice, direzione) {
  const idx = localWidget.value.findIndex(w => w.codice === codice)
  if (idx < 0) return
  const target = direzione === 'up' ? idx - 1 : idx + 1
  if (target < 0 || target >= localWidget.value.length) return

  const next = [...localWidget.value]
  ;[next[idx], next[target]] = [next[target], next[idx]]
  localWidget.value = next.map((w, i) => ({ ...w, ordine: i + 1 }))
}

function onSave() {
  // ⭐ Senza modifiche i widget non si mandano: la rinumerazione qui sotto li
  //    farebbe sembrare scelti (`preferenzaPerChiave`) e congelerebbe quelli
  //    dello standard. Il genitore salva lo stesso: resta la preferenza che
  //    c'era, o nessuna.
  if (!modificato.value) {
    emit('apply', {})
    return
  }
  // Rinumerazione difensiva anche senza riordino: garantisce ordini
  // contigui pure quando l'utente ha solo acceso/spento delle card.
  const widget = localWidget.value.map((w, i) => ({
    codice: w.codice,
    ordine: i + 1,
    visibile: Boolean(w.visibile),
  }))
  emit('apply', { widget })
}

function onReset() {
  confirmAction({
    header: t('home.personalizza_reset'),
    message: t('home.personalizza_reset_conferma'),
    onAccept: () => {
      emit('update:visible', false)
      emit('reset')
    },
  })
}
</script>

<template>
  <!-- Il chrome e' di AppDrawer dal 2026-10-03
       (work-done/analisi-fe-chrome-drawer.md, D-10): testata standard
       col conteggio dei widget nuovi, «Ripristina» nello slot `#footer-azioni`.
       Ogni uscita passa dalla conferma, l'Annulla compreso. -->
  <AppDrawer
    :visible="visible"
    :title="t('home.personalizza_titolo')"
    :icon="MANAGE_ICONS.PERSONALIZZA"
    :action="t('common.edit')"
    :width="DRAWER_WIDTH.STANDARD"
    :proteggi-corpo="false"
    :modificato="modificato"
    :conferma-uscita="chiudiConConferma"
    :conteggio="widgetNuovi"
    :loading="loading"
    @update:visible="(v) => emit('update:visible', v)"
    @save="onSave"
  >
    <div class="dash-config-body">
      <p class="dash-config-hint">
        {{ t('home.personalizza_hint', { max: dimensioneMax }) }}
      </p>

      <Tag
        v-if="oltreCap"
        severity="warn"
        :value="t('home.personalizza_oltre_cap', {
          n: nVisibili,
          max: dimensioneMax,
        })"
      />

      <div v-if="localWidget.length === 0" class="dash-config-vuoto">
        {{ t('home.personalizza_nessun_widget') }}
      </div>

      <div
        v-for="(widget, idx) in localWidget"
        :key="widget.codice"
        class="dash-config-row"
      >
        <ToggleSwitch
          v-model="widget.visibile"
          :aria-label="labelDi(widget)"
        />
        <span class="dash-config-row-label">{{ labelDi(widget) }}</span>
        <div class="dash-config-row-actions">
          <Button
            :icon="MANAGE_ICONS.SPOSTA_SU"
            text
            rounded
            :disabled="idx === 0"
            :aria-label="t('home.personalizza_su')"
            @click="move(widget.codice, 'up')"
          />
          <Button
            :icon="MANAGE_ICONS.SPOSTA_GIU"
            text
            rounded
            :disabled="idx === localWidget.length - 1"
            :aria-label="t('home.personalizza_giu')"
            @click="move(widget.codice, 'down')"
          />
        </div>
      </div>
    </div>

    <!-- «Ripristina» accanto ad Annulla/Salva: lo slot `#footer-azioni` del
         guscio, che tiene footer e uscita (ogni uscita passa dalla conferma). -->
    <template #footer-azioni>
      <Button
        :label="t('home.personalizza_reset')"
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
.dash-config-body {
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
}
.dash-config-hint {
  margin: 0;
  font-size: var(--app-font-size-sm);
  color: var(--app-text-muted);
}
.dash-config-vuoto {
  padding: 1rem 0;
  color: var(--app-text-muted);
}
.dash-config-row {
  display: grid;
  grid-template-columns: auto 1fr auto;
  align-items: center;
  gap: 0.5rem;
  padding: 0.25rem 0;
  border-bottom: 1px solid var(--app-drawer-section-border);
}
.dash-config-row-label {
  overflow-wrap: anywhere;
}
.dash-config-row-actions {
  display: flex;
  gap: 0.15rem;
}
</style>
