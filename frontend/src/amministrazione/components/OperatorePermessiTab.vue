<script setup>
// Scopo: Componente permessi operatore riutilizzabile.
// Sezioni: aree, azioni di processo, oggetti (model), emittenti scope.
// Usato sia dentro i Tabs di OperatoreDrawer sia dal
// drawer dedicato OperatorePermessiDrawer (azione rapida dalla lista).
// Reagisce automaticamente al cambio di authUserId.
//
// ⭐ RISTRUTTURAZIONE 2026-09-05 — le tre tabelle mostrano TUTTE le voci del
//    catalogo, non piu' i soli override. Prima un operatore appena creato
//    apriva tre tabelle VUOTE, da cui non si capiva cosa potesse fare: la
//    schermata mostrava le ECCEZIONI e non lo STATO, mentre il livello che
//    conta nasce da una catena di cinque passi di cui se ne vedeva uno.
//    E' il pattern slot/override gia' adottato sul tab Utilities degli
//    emittenti, qui incarnato dal BB `MatriceOverride`.
// ⛔ NESSUN CAMBIO DI FUNZIONALITA': la semantica dei permessi e' identica.
//    In particolare un'area BLOCCATA continua a NON bloccare le sue azioni di
//    processo — e' un difetto di modello aperto, non lavoro di questa
//    ristrutturazione (analisi-ui-permessi-operatore.md §3).
import { ref, computed, watch, nextTick } from 'vue'
import { useI18n } from 'vue-i18n'
import { useOperatoriStore } from '../stores/operatori'
import { useNotify } from '../../core/composables/useNotify'
import { useLookup } from '../../core/composables/useLookup'
import { useInjectReadonly } from '../../core/composables/useReadonlyMode'
import { MANAGE_ICONS } from '../../core/constants'
import { listAreeFunzionali, listAzioniProcesso, listEmittentiFiscali, getModelOverridesLookup } from '../api/amministrazione'
import { LIVELLO_ACCESSO, buildLivelloOptions, getLivelloLabel } from '../constants'
import MatriceOverride from '../../core/components/MatriceOverride.vue'
import Select from 'primevue/select'
import RadioButton from 'primevue/radiobutton'
import Button from 'primevue/button'
import Message from 'primevue/message'

const { t } = useI18n()
const store = useOperatoriStore()
const notify = useNotify()
// Readonly inject: il tab puo' essere usato dentro OperatoreDrawer in modalita'
// readonly o dentro OperatorePermessiDrawer; in entrambi i casi i pulsanti
// add/save/trash e i Select/ToggleSwitch di riga vanno disattivati.
const isReadonly = useInjectReadonly()

// Lookup via useLookup (non piu' dallo store)
const areeFunzionali = useLookup(listAreeFunzionali, { immediate: true })
const azioniProcesso = useLookup(listAzioniProcesso, { immediate: true })
const modelOverrides = useLookup(getModelOverridesLookup, { immediate: true })
const emittentiFiscali = useLookup(listEmittentiFiscali, { immediate: true })

const props = defineProps({
  authUserId: { type: Number, required: true }
})

const livelloOptions = buildLivelloOptions(t)

// Multi-face auth: flag SUPER_ADMIN dal detail dell'operatore gestito
// (non dal user corrente auth). Se il detail non e' ancora caricato,
// loadAll() lo fetcha. Banner "admin ha accesso totale" guidato da qui.
const isSuperAdmin = computed(() => store.currentOperatore?.is_super_admin === true)

// Stato locale editabile (mantenuto separato dallo store per permettere undo
// logico tra un save e l'altro e per non mutare direttamente lo store).
//
// ⭐ MAPPE indicizzate per chiave, e non piu' array di righe: la lista a video
//    e' il CATALOGO (tutte le aree, tutte le azioni, tutti i model), mentre
//    questi sono i soli override SCRITTI. La presenza della chiave E'
//    l'override; l'assenza e' «vale l'ereditato».
// ⛔ E la distinzione non e' un dettaglio di struttura dati: un livello
//    BLOCCATO **scritto** non e' «nessun override» — batte il profilo del
//    reparto — quindi le due cose non possono collassare in un unico valore.
const overrideAree = ref({})
const overrideAzioni = ref({})
const overrideOggetti = ref({})

// Fase 2 multi-face: scope dichiarativo. `localScopeMode` e' la radio
// attualmente selezionata; `localEmittenteId` e' l'id selezionato quando
// scope_mode='SINGLE'. Salvataggio costruisce il payload
// `{scope_mode, emittenti_ids}` dal couple.
const localScopeMode = ref('GLOBAL')
const localEmittenteId = ref(null)

// Scopo: Carica tutto lo stato necessario per il componente.
//        Viene chiamato dal watch su authUserId (immediate) e garantisce
//        che currentOperatore, overrideAree/azioni, emittentiScope siano
//        coerenti con l'utente passato.
async function loadAll(userId) {
  if (!userId) return
  const needDetail = store.currentOperatore?.auth_user_id !== userId
  await Promise.all([
    needDetail ? store.fetchDetail(userId) : Promise.resolve(),
    store.fetchOverrideAree(userId),
    store.fetchOverrideAzioni(userId),
    store.fetchOverrideOggetti(userId),
    // La colonna «ereditato»: senza, il pannello direbbe MENO di quello di
    // prima — mostrerebbe 59 righe senza dire da dove viene il loro valore.
    store.fetchPermessiEreditati(userId),
    store.fetchEmittentiScope(userId)
  ])
  syncLocal()
}

watch(() => props.authUserId, loadAll, { immediate: true })

// Chiave di un oggetto override: `app_label.model_name`. Sede unica — la
// stessa stringa indicizza la mappa locale, il lookup dei model riservati e la
// riga del catalogo.
const chiaveOggetto = (o) => `${o.app_label}.${o.model_name}`

function syncLocal() {
  overrideAree.value = Object.fromEntries(
    store.overrideAree.map(a => [a.area_id, { ...a }])
  )
  overrideAzioni.value = Object.fromEntries(
    store.overrideAzioni.map(a => [a.azione_id, { ...a }])
  )
  overrideOggetti.value = Object.fromEntries(
    store.overrideOggetti.map(o => [chiaveOggetto(o), { ...o }])
  )
  localScopeMode.value = store.emittentiScope.scope_mode || 'GLOBAL'
  localEmittenteId.value = (store.emittentiScope.emittenti_ids || [])[0] ?? null
}

// ═══ L'EREDITATO — cosa l'operatore ha GIA' dal profilo ════════════════════
// ⚠️ Voce assente = nessun profilo la copre ⇒ vale il DEFAULT (BLOCCATO per le
//    aree, azione negata). Il `?? ` qui sotto e' quel default, non un ripiego
//    difensivo: e' la quinta regola della catena di risoluzione.
const ereditatoAree = computed(() =>
  Object.fromEntries((store.permessiEreditati.aree || []).map(a => [a.area_id, a]))
)
const ereditatoAzioni = computed(() =>
  Object.fromEntries((store.permessiEreditati.azioni || []).map(a => [a.azione_id, a]))
)

const livelloEreditatoArea = (areaId) =>
  ereditatoAree.value[areaId]?.livello ?? LIVELLO_ACCESSO.BLOCCATO
const abilitataEreditataAzione = (azioneId) =>
  ereditatoAzioni.value[azioneId]?.abilitata ?? false

// Da dove viene il valore ereditato: il nome del profilo, o «default» quando
// nessun profilo copre la voce. ⭐ Distinguere le due cose e' la ragione per
// cui la colonna esiste: «bloccato perche' qualcuno l'ha deciso» e «bloccato
// perche' nessuno ha detto niente» hanno rimedi diversi.
const fonteArea = (areaId) =>
  ereditatoAree.value[areaId]?.profilo_nome ?? t('amministrazione.ereditato_default')
const fonteAzione = (azioneId) =>
  ereditatoAzioni.value[azioneId]?.profilo_nome ?? t('amministrazione.ereditato_default')

// ⚠️ Per un OGGETTO l'ereditato e' il livello della sua AREA, non un livello di
//    profilo: `config.profili_accesso_oggetti` non esiste. La catena e'
//    override oggetto → override area → profilo dell'area → BLOCCATO, quindi
//    qui si guarda prima un eventuale override d'area e poi il suo ereditato.
const livelloEreditatoOggetto = (voce) =>
  overrideAree.value[voce.area_id]?.livello ?? livelloEreditatoArea(voce.area_id)
const fonteOggetto = (voce) =>
  overrideAree.value[voce.area_id]
    ? t('amministrazione.ereditato_da_override_area')
    : t('amministrazione.ereditato_da_area', { area: voce.area_descrizione })

// Capability esposte dal BE: render condizionale e disable/tooltip.
const allowedScopeModes = computed(() => store.emittentiScope.allowed_scope_modes || ['GLOBAL', 'SINGLE'])
const canChangeScope = computed(() => store.emittentiScope.can_change_scope !== false)
const changeScopeReason = computed(() => store.emittentiScope.change_scope_reason || null)
const scopeModeOptions = computed(() => [
  { value: 'GLOBAL', label: t('amministrazione.scope_mode_global'), disabled: !allowedScopeModes.value.includes('GLOBAL') },
  { value: 'SINGLE', label: t('amministrazione.scope_mode_single'), disabled: !allowedScopeModes.value.includes('SINGLE') },
])

// Pattern: store action gia' unwrappate → chiamata diretta + try/catch.
// useApiHandler.execute() e' SOLO per response axios (feedback_useapihandler_solo_axios).
//
// Helper consolidato per saveAree/Azioni/Oggetti/Emittenti: ogni save ha la
// stessa struttura (guard readonly + chiamata store + notify success +
// catch silente per delegare all'interceptor globale). Estraendo l'helper
// evitiamo la copia-incolla che renderebbe fragile un eventuale fix di pattern.
async function _saveOverride(action, items, afterSuccess) {
  if (isReadonly.value) return
  try {
    await action(props.authUserId, items)
    notify.success(t('notifications.save_success'))
    afterSuccess?.()
  } catch {
    // Errore gestito dall'interceptor axios globale.
  }
}

// ⛔ IL SALVATAGGIO MANDA SOLO LE RIGHE CON OVERRIDE VERO, e i mapper partono
//    dai VALORI delle mappe — mai dalle voci del catalogo.
//    Il `PUT` sostituisce l'intera collezione (`DELETE WHERE auth_user_id` +
//    reinsert): mandare tutte le voci a video materializzerebbe 59 override
//    reali e cambierebbe il comportamento di ogni utente con un profilo, cioe'
//    farebbe per sbaglio il cambio di funzionalita' che questa ristrutturazione
//    esclude. Un BLOCCATO scritto non e' «nessun override»: batte il profilo.
const _toAreaItem = (a) => ({
  area_id: a.area_id,
  livello: a.livello,
  motivo: a.motivo || null,
  valido_dal: a.valido_dal || null,
  valido_al: a.valido_al || null,
})

const _toAzioneItem = (a) => ({
  azione_id: a.azione_id,
  abilitata: a.abilitata,
  motivo: a.motivo || null,
  valido_dal: a.valido_dal || null,
  valido_al: a.valido_al || null,
})

const _toOggettoItem = (o) => ({
  app_label: o.app_label,
  model_name: o.model_name,
  livello: o.livello,
  motivo: o.motivo || null,
  valido_dal: o.valido_dal || null,
  valido_al: o.valido_al || null,
})

const saveAree = () =>
  _saveOverride(store.saveOverrideAree, Object.values(overrideAree.value).map(_toAreaItem))

const saveAzioni = () =>
  _saveOverride(store.saveOverrideAzioni, Object.values(overrideAzioni.value).map(_toAzioneItem))

// Costruzione payload Fase 2: GLOBAL -> emittenti_ids: []; SINGLE -> [id].
// La validazione e' centralizzata sul BE (E_AMM_SCOPE_NON_AMMESSO se SINGLE
// senza emittente). Qui blocchiamo solo lato UX per evitare round-trip.
function _buildScopePayload() {
  if (localScopeMode.value === 'GLOBAL') {
    return { scope_mode: 'GLOBAL', emittenti_ids: [] }
  }
  return { scope_mode: 'SINGLE', emittenti_ids: localEmittenteId.value != null ? [localEmittenteId.value] : [] }
}

const canSaveEmittenti = computed(() => {
  if (!canChangeScope.value) return false
  // Defense-in-depth: la modalita' selezionata deve essere ammessa dal BE.
  // Se in futuro `allowed_scope_modes` venisse ridotto (es. lockdown sul
  // SUPER_ADMIN), evita un round-trip che ritorna E_AMM_SCOPE_NON_AMMESSO.
  if (!allowedScopeModes.value.includes(localScopeMode.value)) return false
  if (localScopeMode.value === 'SINGLE' && localEmittenteId.value == null) return false
  return true
})

const saveEmittenti = () => {
  if (!canSaveEmittenti.value) return
  return _saveOverride(
    store.saveEmittentiScope,
    _buildScopePayload(),
    // Refresh asincrono lista operatori (la `emittenti_descrizione` puo'
    // essere cambiata): dopo il prossimo render frame per non interrompere
    // l'animazione del toast.
    () => nextTick(() => store.fetchList().catch(() => {})),
  )
}

// ═══ I DUE VERBI ══════════════════════════════════════════════════════════
// `set` scrive l'override sulla riga; `reset` lo TOGLIE e la riga torna a
// seguire l'ereditato. ⭐ Non sono la stessa cosa scritta in due modi: un
// override che ripete il valore ereditato CONGELA la riga — da quel momento
// non segue piu' il profilo, quindi il giorno che il reparto cambia livello
// quell'utente resta indietro, e nessuno lo segnala.
function setOverrideArea(areaId, livello) {
  overrideAree.value = {
    ...overrideAree.value,
    [areaId]: { ...(overrideAree.value[areaId] || {}), area_id: areaId, livello },
  }
}

function setOverrideAzione(azioneId, abilitata) {
  overrideAzioni.value = {
    ...overrideAzioni.value,
    [azioneId]: { ...(overrideAzioni.value[azioneId] || {}), azione_id: azioneId, abilitata },
  }
}

function setOverrideOggetto(voce, livello) {
  const k = chiaveOggetto(voce)
  overrideOggetti.value = {
    ...overrideOggetti.value,
    [k]: {
      ...(overrideOggetti.value[k] || {}),
      app_label: voce.app_label,
      model_name: voce.model_name,
      livello,
    },
  }
}

// Rimozione per chiave, con riassegnazione dell'oggetto: mutare in-place con
// `delete` non e' reattivo su un `ref` di oggetto semplice.
function _senzaChiave(mappa, chiave) {
  return Object.fromEntries(
    Object.entries(mappa).filter(([k]) => String(k) !== String(chiave))
  )
}

const resetArea = (areaId) => { overrideAree.value = _senzaChiave(overrideAree.value, areaId) }
const resetAzione = (azioneId) => { overrideAzioni.value = _senzaChiave(overrideAzioni.value, azioneId) }
const resetOggetto = (chiave) => { overrideOggetti.value = _senzaChiave(overrideOggetti.value, chiave) }

// ═══ L'AVVISO: un override che ripete l'ereditato ═════════════════════════
// Non serve a niente e congela la riga. E' il guadagno vero della colonna
// «ereditato»: si vede confrontando due valori che ora sono entrambi in pagina.
const avvisoArea = (area) => {
  const o = overrideAree.value[area.id]
  return o && o.livello === livelloEreditatoArea(area.id)
    ? t('amministrazione.override_ridondante')
    : null
}
const avvisoAzione = (az) => {
  const o = overrideAzioni.value[az.id]
  return o && o.abilitata === abilitataEreditataAzione(az.id)
    ? t('amministrazione.override_ridondante')
    : null
}
const avvisoOggetto = (voce) => {
  const o = overrideOggetti.value[chiaveOggetto(voce)]
  return o && o.livello === livelloEreditatoOggetto(voce)
    ? t('amministrazione.override_ridondante')
    : null
}

// Le VOCI della matrice oggetti: i model configurabili
// (`can_override === true`), piu' quelli che hanno GIA' un override.
// ⛔ Il secondo insieme non e' un di piu': un model diventato riservato dopo
//    che qualcuno gli aveva messo un override sparirebbe dalla vista mentre la
//    sua riga resta scritta e viene RISALVATA a ogni salvataggio — invisibile e
//    viva. Mostrandolo (con il controllo disabilitato e il motivo a tooltip)
//    resta almeno rimovibile.
const vociOggetti = computed(() => {
  const conOverride = new Set(Object.keys(overrideOggetti.value))
  return modelOverrides.items.value
    .filter(m => m.can_override === true || conOverride.has(`${m.app_label}.${m.model_name}`))
    .map(m => ({
      ...m,
      label: `${m.app_label}.${m.model_name}`
    }))
})

// Scopo: Mappa indicizzata `(app_label, model_name) -> {can_override, reason}`
//        per evitare scansioni lineari nelle template cells. Ricomputata
//        solo quando l'array di model cambia.
const modelOverrideIndex = computed(() => {
  const m = new Map()
  for (const row of modelOverrides.items.value) {
    m.set(`${row.app_label}.${row.model_name}`, row)
  }
  return m
})

// Scopo: Per le righe pre-esistenti che puntano a un model diventato
//        riservato (drift dati storico), risolve la chiave i18n del motivo
//        per mostrarla come tooltip sul Select disabilitato. Lookup O(1)
//        via la mappa indicizzata.
function modelOverrideReason(row) {
  if (!row.app_label || !row.model_name) return null
  const entry = modelOverrideIndex.value.get(`${row.app_label}.${row.model_name}`)
  if (!entry || entry.can_override === true) return null
  return entry.reason ? t(entry.reason) : null
}

const saveOggetti = () =>
  _saveOverride(store.saveOverrideOggetti, Object.values(overrideOggetti.value).map(_toOggettoItem))

// Le tre opzioni di override di un'azione. ⚠️ Un `ToggleSwitch` qui NON basta:
// avrebbe due stati per una realta' che ne ha tre — «abilitata», «negata» e
// «non impostata, vale il profilo» — e il terzo e' quello che si perde.
const azioneOptions = computed(() => [
  { label: t('amministrazione.azione_abilitata'), value: true },
  { label: t('amministrazione.azione_negata'), value: false },
])
</script>

<template>
  <div class="permessi-tab">
    <Message v-if="isSuperAdmin" severity="info" :closable="false" class="mb-3">
      {{ t('amministrazione.admin_full_access') }}
    </Message>

    <p class="app-permessi-nota">{{ t('amministrazione.permessi_nota') }}</p>

    <!-- ═══ AREE FUNZIONALI ═══════════════════════════════════════════════ -->
    <h4>{{ t('amministrazione.override_aree_title') }}</h4>
    <MatriceOverride
      :voci="areeFunzionali.items.value"
      :chiave="a => a.id"
      :overrides="overrideAree"
      :label-voce="t('amministrazione.col_area')"
      :avviso="avvisoArea"
      @reset="resetArea"
    >
      <template #voce="{ voce }">{{ voce.descrizione }}</template>
      <template #ereditato="{ voce }">
        {{ getLivelloLabel(t, livelloEreditatoArea(voce.id)) }}
        <small class="app-permessi-fonte">{{ fonteArea(voce.id) }}</small>
      </template>
      <template #override="{ voce, valore }">
        <Select
          :model-value="valore?.livello ?? null"
          :options="livelloOptions"
          option-label="label"
          option-value="value"
          :placeholder="t('amministrazione.override_non_impostato')"
          class="w-full"
          :disabled="isReadonly"
          @update:model-value="v => setOverrideArea(voce.id, v)"
        />
      </template>
    </MatriceOverride>
    <div v-if="!isReadonly" class="flex justify-end mb-4">
      <Button :label="t('common.save')" :icon="MANAGE_ICONS.CONFIRM" size="small" @click="saveAree" />
    </div>

    <!-- ═══ AZIONI DI PROCESSO ════════════════════════════════════════════ -->
    <h4>{{ t('amministrazione.override_azioni_title') }}</h4>
    <MatriceOverride
      :voci="azioniProcesso.items.value"
      :chiave="a => a.id"
      :overrides="overrideAzioni"
      :label-voce="t('amministrazione.col_azione')"
      :avviso="avvisoAzione"
      ricerca
      :ricerca-placeholder="t('amministrazione.cerca_azione')"
      @reset="resetAzione"
    >
      <template #voce="{ voce }">{{ voce.descrizione }}</template>
      <template #ereditato="{ voce }">
        {{ abilitataEreditataAzione(voce.id) ? t('amministrazione.azione_abilitata') : t('amministrazione.azione_negata') }}
        <small class="app-permessi-fonte">{{ fonteAzione(voce.id) }}</small>
      </template>
      <template #override="{ voce, valore, haOverride }">
        <Select
          :model-value="haOverride ? valore.abilitata : null"
          :options="azioneOptions"
          option-label="label"
          option-value="value"
          :placeholder="t('amministrazione.override_non_impostato')"
          class="w-full"
          :disabled="isReadonly"
          @update:model-value="v => setOverrideAzione(voce.id, v)"
        />
      </template>
    </MatriceOverride>
    <div v-if="!isReadonly" class="flex justify-end mb-4">
      <Button :label="t('common.save')" :icon="MANAGE_ICONS.CONFIRM" size="small" @click="saveAzioni" />
    </div>

    <!-- ═══ OGGETTI (livello model) ═══════════════════════════════════════ -->
    <h4>{{ t('amministrazione.override_oggetti_title') }}</h4>
    <MatriceOverride
      :voci="vociOggetti"
      :chiave="o => `${o.app_label}.${o.model_name}`"
      :overrides="overrideOggetti"
      :label-voce="t('amministrazione.col_model')"
      :avviso="avvisoOggetto"
      ricerca
      :ricerca-placeholder="t('amministrazione.cerca_model')"
      @reset="resetOggetto"
    >
      <template #voce="{ voce }">
        {{ voce.label }}
        <small class="app-permessi-fonte">{{ voce.area_descrizione }}</small>
      </template>
      <template #ereditato="{ voce }">
        {{ getLivelloLabel(t, livelloEreditatoOggetto(voce)) }}
        <small class="app-permessi-fonte">{{ fonteOggetto(voce) }}</small>
      </template>
      <template #override="{ voce, valore }">
        <span v-tooltip.top="modelOverrideReason(voce)" class="block w-full">
          <Select
            :model-value="valore?.livello ?? null"
            :options="livelloOptions"
            option-label="label"
            option-value="value"
            :placeholder="t('amministrazione.override_non_impostato')"
            class="w-full"
            :disabled="isReadonly || !!modelOverrideReason(voce)"
            @update:model-value="v => setOverrideOggetto(voce, v)"
          />
        </span>
      </template>
    </MatriceOverride>
    <div v-if="!isReadonly" class="flex justify-end mb-4">
      <Button :label="t('common.save')" :icon="MANAGE_ICONS.CONFIRM" size="small" @click="saveOggetti" />
    </div>

    <!-- Emittenti Scope (Fase 2 multi-face) -->
    <h4>{{ t('amministrazione.emittenti_scope_title') }}</h4>
    <p class="text-sm text-color-secondary mb-2">{{ t('amministrazione.emittenti_scope_hint') }}</p>

    <!-- Radio scope: GLOBAL/SINGLE. `MULTI` non e' incluso in
         allowed_scope_modes post Q2 (architetturalmente chiuso). -->
    <div
      class="scope-radio-group mb-2"
      v-tooltip.bottom="!canChangeScope ? changeScopeReason : null"
    >
      <div
        v-for="opt in scopeModeOptions"
        :key="opt.value"
        class="scope-radio-row"
      >
        <RadioButton
          v-model="localScopeMode"
          :value="opt.value"
          :input-id="'scope-mode-' + opt.value"
          :disabled="isReadonly || !canChangeScope || opt.disabled"
        />
        <label :for="'scope-mode-' + opt.value" class="scope-radio-label">{{ opt.label }}</label>
      </div>
    </div>

    <!-- Select emittente: visibile solo in SINGLE -->
    <Select
      v-if="localScopeMode === 'SINGLE'"
      v-model="localEmittenteId"
      :options="emittentiFiscali.items.value"
      option-label="ragione_sociale"
      option-value="id"
      :placeholder="t('amministrazione.select_emittenti')"
      show-clear
      class="w-full mb-2"
      :disabled="isReadonly || !canChangeScope"
    />

    <div v-if="!isReadonly" class="flex justify-end">
      <Button
        :label="t('common.save')"
        icon="pi pi-check"
        size="small"
        :disabled="!canSaveEmittenti"
        @click="saveEmittenti"
      />
    </div>
  </div>
</template>

<style scoped>
.permessi-tab {
  padding: 0.5rem 0;
}
h4 {
  margin-bottom: 0.5rem;
  margin-top: 1rem;
}
h4:first-child {
  margin-top: 0;
}
.scope-radio-group {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
}
.scope-radio-row {
  display: flex;
  align-items: center;
  gap: 0.5rem;
}
.scope-radio-label {
  cursor: pointer;
}
.app-permessi-nota {
  font-size: 0.85rem;
  color: var(--app-text-secondary, var(--p-text-muted-color));
  margin-bottom: 0.75rem;
}
/* La fonte del valore ereditato: sta sotto il livello, non accanto — la
   domanda «quanto» viene prima della domanda «da dove». */
.app-permessi-fonte {
  display: block;
  color: var(--app-text-secondary, var(--p-text-muted-color));
}
</style>
