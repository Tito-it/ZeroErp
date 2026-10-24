<script setup>
// Scopo: Drawer crea/modifica listino.
//        In edit: pulsanti per aprire drawer autonomi versioni (eventi al parent).
//        Contenuto deferito a dopo l'animazione per evitare rimbalzi visivi.
import { ref, watch, computed, nextTick } from 'vue'
import { useI18n } from 'vue-i18n'
import { useListiniStore } from '../stores/listini'
import { useApiHandler } from '../../core/composables/useApiHandler'
import { useDrawerFormPreserve } from '../../core/composables/useDrawerFormPreserve'
import { useUtilityDefaultId } from '../../core/composables/useUtilityDefaultId'
import { useAuthStore } from '../../stores/auth'
import { DRAWER_WIDTH } from '../../core/constants'
import { NAV_ICONS } from '../../core/navigation'
import AppDrawer from '../../core/components/AppDrawer.vue'
import UtilityPerRuoloSelect from '../../core/components/UtilityPerRuoloSelect.vue'
import TipologiaListinoSelect from './TipologiaListinoSelect.vue'
import InputText from 'primevue/inputtext'
import ToggleSwitch from 'primevue/toggleswitch'
import Message from 'primevue/message'

const { t } = useI18n()
const store = useListiniStore()
const { execute, loading, campiErrati } = useApiHandler()
const auth = useAuthStore()

// Default utility globale: il parametro DEFAULT_UTILITY stocca un codice_interno
// (framework FK-surrogata, DB 2026-05-02). Il composable risolve a id locale
// via lookup utilities-per-emittente.
const { id: utilityDefaultId, load: loadUtilityDefault } = useUtilityDefaultId()

const props = defineProps({
  visible: Boolean,
  mode: { type: String, default: 'create' },
  listinoId: { type: [Number, null], default: null }
})
const emit = defineEmits(['update:visible', 'saved', 'cancelled'])

const isEdit = computed(() => props.mode === 'edit')
const form = ref({})
// Modifiche non salvate: fotografia a form popolato (creazione o modifica),
// chiudere con modifiche chiede conferma (BB useDrawerFormPreserve).
const { fissa, modificato, chiudiConConferma } = useDrawerFormPreserve(form, { visibile: () => props.visible })
const detail = ref(null)
// ⭐ Il flag non si spegne da qui se il listino ha storia (`ha_storia` lo dice
//    il DB, vendite.fn_listino_ha_storia): si spegne con la fine validita' della
//    versione. Il guard rifiuta solo lo spegnimento (true -> false): un listino
//    con storia gia' spento si riaccende ancora dal toggle.
const attivoBloccato = computed(() => !!(detail.value?.ha_storia && detail.value?.attivo))

// Flag di soppressione reset tipologia durante il caricamento iniziale in edit.
// Evita che il watch su form.value.utility_id azzeri la tipologia che loadDetail
// sta impostando contestualmente a utility_id.
const isLoadingDetail = ref(false)

function defaultForm() {
  return {
    codice: '',
    descrizione: '',
    utility_id: utilityDefaultId.value,
    tipologia_id: null,
    attivo: true,
  }
}

function resetForm() {
  form.value = defaultForm()
  detail.value = null
}

async function loadDetail() {
  if (!props.listinoId) return
  isLoadingDetail.value = true
  try {
    const data = await store.fetchDetail(props.listinoId)
    if (!data) return
    detail.value = data
    form.value = {
      codice: data.codice || '',
      descrizione: data.descrizione || '',
      utility_id: data.utility_id ?? null,
      tipologia_id: data.tipologia_id ?? null,
      attivo: data.attivo ?? true
    }
  } finally {
    // nextTick non serve: il watch e' flush:'post' di default e vedra'
    // entrambe le assegnazioni nello stesso batch con isLoadingDetail true.
    isLoadingDetail.value = false
  }
}

watch(() => props.visible, async (v) => {
  if (!v) return
  // Carica il default utility (parameter + lookup) prima di resetForm:
  // defaultForm() legge utilityDefaultId.value gia' risolto a id locale.
  await loadUtilityDefault()
  if (isEdit.value) {
    await loadDetail()
  } else {
    resetForm()
  }
  // Dopo il nextTick: il watch su utility_id qui sotto puo' ancora scrivere
  // tipologia_id, e la fotografia deve vedere il form com'e' davvero.
  await nextTick()
  fissa()
})

// Scopo: Watch su utility_id — al cambio reale (non al caricamento iniziale),
// azzera la tipologia selezionata. La matrice `config.listini_tipologie_utilities`
// puo' cambiare le tipologie ammesse; un valore residuo porterebbe all'errore
// del trigger DB. La guard `isLoadingDetail` sopprime il reset durante la
// load di un listino esistente (dove utility_id e tipologia_id sono coerenti
// per costruzione).
watch(() => form.value.utility_id, (newVal, oldVal) => {
  if (isLoadingDetail.value) return
  if (newVal === oldVal) return
  form.value.tipologia_id = null
})

// Scopo: in create l'emittente fiscale e' quello dell'operatore corrente
// (refactor operatore-emittenti: relazione 1-a-1). Gli admin globali non hanno
// un emittente personale e quindi non possono creare listini da questa UI.
// Nota: per listini serve soggettoRuoloId (FK verso soggetti_ruoli),
// NON l'id emittente fiscale (FK diverso).
const canSave = computed(() => {
  const base = !!form.value.codice?.trim()
    && !!form.value.descrizione?.trim()
    && !!form.value.utility_id
    && !!form.value.tipologia_id
  if (!base) return false
  if (isEdit.value) return true
  // In creazione serve l'emittente su cui la sessione scrive: quello
  // dell'operatore o quello scelto dal super admin (ne basta il ruolo).
  return auth.emittenteScritturaSoggettoRuoloId != null
})

async function handleSave() {
  const f = form.value
  if (isEdit.value) {
    const payload = {
      descrizione: f.descrizione?.trim() || '',
      utility_id: f.utility_id,
      tipologia_id: f.tipologia_id,
    }
    // Col flag bloccato non lo si manda: non lo si puo' cambiare da qui.
    if (!attivoBloccato.value) payload.attivo = f.attivo
    const result = await execute(
      () => store.update(props.listinoId, payload),
      { successMessage: t('vendite.listini.listino_salvato') }
    )
    if (result !== null) { fissa(); emit('saved', result); chiudiDopoSalvataggio() }
  } else {
    // emittente_soggetto_ruolo_id: pricing v5 §3.1 — dimensione NOT NULL del
    // listino. FK verso soggetti_ruoli (NON emittenti_fiscali): il RUOLO
    // dell'emittente di scrittura, non la sua PK.
    const payload = {
      codice: f.codice?.trim(),
      descrizione: f.descrizione?.trim(),
      utility_id: f.utility_id,
      tipologia_id: f.tipologia_id,
      emittente_soggetto_ruolo_id: auth.emittenteScritturaSoggettoRuoloId,
    }
    const result = await execute(
      () => store.create(payload),
      { successMessage: t('vendite.listini.listino_creato') }
    )
    if (result !== null) { fissa(); emit('saved', result); chiudiDopoSalvataggio() }
  }
}


// Uscita dopo il salvataggio, diretta (la fotografia e' gia' fissata). ⛔ Non
// chiamarla `close`: in `<script setup>` un `close()` senza dichiarazione
// risolve in silenzio a `window.close()` — e' il difetto trovato il 2026-10-03,
// quando la funzione locale era stata tolta e le chiamate erano rimaste.
function chiudiDopoSalvataggio() {
  emit('update:visible', false)
  emit('cancelled')
}
</script>

<template>
  <!-- Il chrome e' di AppDrawer dal 2026-10-03
       (work-done/analisi-fe-chrome-drawer.md). -->
  <AppDrawer
    :visible="visible"
    :title="t('vendite.listini.listino')"
    :icon="NAV_ICONS.LISTINI"
    :action="isEdit ? t('common.edit') : t('common.new')"
    :width="DRAWER_WIDTH.STANDARD"
    :modificato="modificato"
    :conferma-uscita="chiudiConConferma"
    :loading="loading"
    :save-disabled="!canSave"
    @update:visible="(v) => emit('update:visible', v)"
    @cancel="emit('cancelled')"
    @save="handleSave"
  >
    <!-- Solo in creazione: su quale emittente nasce il listino, o che
         prima va scelto (super admin su «Tutti gli emittenti»). -->
    <Message v-if="!isEdit && auth.emittenteScritturaSoggettoRuoloId == null" severity="warn" :closable="false">
      {{ t('vendite.listini.banner_scegli_emittente') }}
    </Message>
    <Message v-else-if="!isEdit && auth.emittenteScritturaNome" severity="info" :closable="false">
      {{ t('vendite.listini.banner_emittente_corrente', { nome: auth.emittenteScritturaNome }) }}
    </Message>
    <div class="form-grid-2col">
      <div class="form-field">
        <label>{{ t('vendite.listini.field_codice') }} *</label>
        <InputText v-model="form.codice" :disabled="isEdit"
          :invalid="campiErrati.includes('codice')"
        />
      </div>
      <div class="form-field">
        <label>{{ t('vendite.listini.field_utility') }} *</label>
        <UtilityPerRuoloSelect v-model="form.utility_id"
          :placeholder="t('vendite.listini.field_utility')" />
      </div>
    </div>

    <div class="form-grid-2col">
      <div class="form-field">
        <label>{{ t('vendite.listini.field_tipologia') }} *</label>
        <TipologiaListinoSelect v-model="form.tipologia_id"
          :utility-id="form.utility_id" />
      </div>
      <div class="form-field">
        <label>{{ t('vendite.listini.field_descrizione') }} *</label>
        <InputText v-model="form.descrizione"
          :invalid="campiErrati.includes('descrizione')"
        />
      </div>
    </div>

    <!-- ⭐ Un listino con storia si spegne con la fine validità della versione,
         non col flag (`attivoBloccato`). -->
    <div v-if="isEdit" class="form-grid">
      <div class="form-field">
        <label>{{ t('indirizzi.campo_attivo') }}</label>
        <ToggleSwitch v-if="!attivoBloccato" v-model="form.attivo"
          :invalid="campiErrati.includes('attivo')"
        />
        <small v-else class="app-field-hint">{{ t('vendite.listini.attivo_con_storia') }}</small>
      </div>
    </div>
  </AppDrawer>
</template>
