<script setup>
// Scopo: Modale di personalizzazione colonne per <ListaConfigurabile>.
// Permette: toggle visibilita', riordino colonne (▲/▼), edit larghezza,
// reset preferenza utente. Le colonne tipo 'identificatore' e 'azione'
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
import Drawer from 'primevue/drawer'
import Button from 'primevue/button'
import FormFooter from './FormFooter.vue'
import ToggleSwitch from 'primevue/toggleswitch'
import InputNumber from 'primevue/inputnumber'
import Badge from 'primevue/badge'
import Tag from 'primevue/tag'
import { etichettaColonna } from '../utils/i18nLabel'
import { DRAWER_WIDTH } from '../constants'
import { useConfirmAction } from '../composables/useConfirmAction'
import { useDrawerContentReady } from '../composables/useDrawerContentReady'
import { useDrawerFormPreserve, gestoreVisibile } from '../composables/useDrawerFormPreserve'


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

// Contenuto deferito a fine animazione: senza, i figli pesanti si montano
// durante lo slide-in e il drawer «rimbalza» (`feedback_content_ready_after_show`).
// ⛔ Il reset alla chiusura lo fa il composable: NON aggiungerlo nel watch.
const { contentReady, onAfterShow } = useDrawerContentReady(() => props.visible)

const emit = defineEmits(['update:visible', 'apply', 'reset'])
const { t, te } = useI18n()

// Copia locale modificabile della config. Resetata ad ogni open per
// scartare modifiche di una sessione precedente di apertura modale.
const localColonne = ref([])

// Modifiche non salvate: si confronta l'elenco senza `ordine`, che il
// riordino rinumera 1..N (l'ordine lo dice gia' la posizione: spostare e
// rimettere a posto non e' una modifica), e con `visibile` come lo mostra
// il toggle (assente = visibile). Prima del watch immediate (TDZ).
const colonneDaSalvare = computed(() =>
  localColonne.value.map((c) => ({
    codice: c.codice,
    visibile: c.visibile !== false,
    larghezza: c.larghezza ?? null,
  })),
)
const { fissa, chiudiConConferma } =
  useDrawerFormPreserve(colonneDaSalvare, { visibile: () => props.visible })

watch(
  () => [props.visible, props.config],
  ([open]) => {
    if (open && props.config?.colonne) {
      // Deep-clone per non mutare la config del genitore prima di Salva.
      localColonne.value = JSON.parse(JSON.stringify(props.config.colonne))
      fissa()
    }
  },
  { immediate: true },
)

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
function onSave() {
  emit('apply', { colonne: localColonne.value })
}

function onCancel() {
  chiudiConConferma(() => emit('update:visible', false))
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
const suVisibile = gestoreVisibile(emit, onCancel)
</script>

<template>
  <Drawer
    :visible="visible"
    position="right"
    :style="{ width: DRAWER_WIDTH.SIMPLE }"
    :modal="true"
    :dismissable="!loading"
    @update:visible="suVisibile"
    @after-show="onAfterShow"
  >
    <template #header>
      <div class="lista-config-header">
        <h3>{{ t('lista_config.modal_title') }}</h3>
        <Badge
          v-if="colonneNuove > 0"
          :value="colonneNuove"
          severity="info"
          v-tooltip.bottom="t('lista_config.colonne_nuove_tooltip', { count: colonneNuove })"
        />
      </div>
    </template>

    <div v-if="contentReady" class="lista-config-body">
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
              icon="pi pi-arrow-up"
              text
              rounded
              size="small"
              :disabled="gIdx === 0 && i === 0"
              v-tooltip.top="t('lista_config.sposta_su')"
              @click="move(col.codice, 'up')"
            />
            <Button
              icon="pi pi-arrow-down"
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

    <template #footer>
      <div class="lista-config-footer">
        <!-- Reset preferenza: bottone aggiuntivo non standard del pattern
             Annulla/Salva, resta standalone. -->
        <Button
          :label="t('lista_config.reset_preferenza')"
          icon="pi pi-refresh"
          severity="secondary"
          text
          :disabled="loading"
          @click="onReset"
        />
        <div class="lista-config-footer-right">
          <FormFooter
            :loading="loading"
            @cancel="onCancel"
            @save="onSave"
          />
        </div>
      </div>
    </template>
  </Drawer>
</template>

<style scoped>
.lista-config-header {
  display: flex;
  align-items: center;
  gap: 0.5rem;
}
.lista-config-header h3 {
  margin: 0;
}
.lista-config-body {
  display: flex;
  flex-direction: column;
  gap: 1rem;
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
.lista-config-footer {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 0.5rem;
}
.lista-config-footer-right {
  display: flex;
  gap: 0.5rem;
}
</style>
