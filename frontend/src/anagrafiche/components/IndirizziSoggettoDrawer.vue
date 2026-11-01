<script setup>
// Scopo: Drawer dedicato per gestione indirizzi di un soggetto o ruolo.
// Riutilizzabile da: SoggettoDrawer (context='soggetto'), ClienteDrawer (context='ruolo').
// Context 'soggetto': lista piatta + form aggiungi/cambia (via matrice).
// Context 'ruolo': cascata 3 livelli (istanza→ruolo→soggetto) con fonte badge.

import { ref, watch, computed, nextTick } from 'vue'
import { useI18n } from 'vue-i18n'
import { useInjectReadonly } from '../../core/composables/useReadonlyMode'
import { useApiHandler } from '../../core/composables/useApiHandler'
import { useFormInline } from '../../core/composables/useFormInline'
import { useDrawerFormPreserve } from '../../core/composables/useDrawerFormPreserve'
import { useIndirizzoSoggettoForm } from '../composables/useIndirizzoSoggettoForm'
import { raccogliFormInline } from '../composables/raccogliFormInline'
import {
  listSoggettoIndirizzi, createSoggettoIndirizzo, replaceSoggettoIndirizzo,
  listRuoloIndirizzi, createRuoloIndirizzo, deleteRuoloIndirizzo
} from '../api/anagrafiche'
import { lookupMatriceIndirizzi, lookupMatriceIndirizziRuolo } from '../../core/apiCore'
import { DRAWER_WIDTH, MANAGE_ICONS, STATUS_ICONS } from '../../core/constants'
import { NAV_ICONS } from '../../core/navigation'
import { sortByFonte } from '../../core/utils/string'
import IndirizzoSoggettoForm from './IndirizzoSoggettoForm.vue'
import AppDrawer from '../../core/components/AppDrawer.vue'
import FormFooter from '../../core/components/FormFooter.vue'
import Button from 'primevue/button'
import Tag from 'primevue/tag'
import Message from 'primevue/message'

const { t } = useI18n()
const isReadonly = useInjectReadonly()
const { execute, loading, campiErrati } = useApiHandler()
const indirizzo = useIndirizzoSoggettoForm()

// Context 'soggetto' (default) o 'ruolo': determina quale set di API usare.
// Per 'soggetto': soggettoId = soggetto UUID. Per 'ruolo': soggettoId = soggetto_ruolo_id (int).
// istanzaUtilityId: opzionale, usato in context 'ruolo' per cascata a 3 livelli.
const props = defineProps({
  visible: { type: Boolean, default: false },
  soggettoId: { type: [String, Number], default: null },
  tipoSoggettoDettaglioId: { type: Number, default: null },
  context: { type: String, default: 'soggetto' },
  istanzaUtilityId: { type: Number, default: null },
  tipoRuoloCodice: { type: String, default: null },
  // Modalita' SELEZIONE (drawer gestione indirizzi documento): aggiunge per
  // riga l'azione "usa questo" che emette `select(riga)`. I flussi anagrafici
  // esistenti (aggiungi/cambia/elimina) restano invariati. Default off:
  // nessun impatto sui consumatori attuali (ClienteDrawer/SoggettoDrawer).
  selectable: { type: Boolean, default: false },
  selectTooltip: { type: String, default: '' },
})

const isRuolo = computed(() => props.context === 'ruolo')

const emit = defineEmits(['update:visible', 'saved', 'select'])

// Lista indirizzi esistenti
const indirizziList = ref([])
const listLoading = ref(false)
const matriceCompleta = ref([])

// Modalita' form: null = lista, 'create' = aggiungi, 'edit' = cambia. La
// macchina e' il BB core `useFormInline` (sede unica, ok Tid 2026-09-28).
// ⭐ «Cambia» e' lo stato 'edit' della macchina: il form si apre su un
//    indirizzo esistente. Che il salvataggio lo SOSTITUISCA (replace, o
//    cancella + crea sul ruolo) e' il verbo del dominio, e resta qui. Fino a
//    quel giorno gli stati erano 'new'/'replace'.
const { formMode, formAperto, rigaInModifica, nuovaRiga, apriRiga, chiudiForm, ancoraForm } = useFormInline({
  // D-8: cambiare riga col form modificato chiede (il getter e' letto al clic).
  confermaCambio: (p) => chiudiInlineConConferma(p),
})
// L'indirizzo soggetto da sostituire (in modifica).
const replaceId = computed(() => rigaInModifica.value?.id ?? null)
const replaceLabel = ref('')
const comuneInitialItem = ref(null)

// Modifiche non salvate (BB useDrawerFormPreserve) sul form inline
// dell'indirizzo: conta solo a form aperto, e la fotografia si azzera quando
// torna la lista. Chiudere il drawer o annullare il form con modifiche chiede conferma.
const formIndirizzo = computed(() => raccogliFormInline({ indirizzo }))
const {
  fissa: fissaInline,
  modificato: modificatoInline,
  chiudiConConferma: chiudiInlineConConferma,
} = useDrawerFormPreserve(formIndirizzo, { visibile: () => props.visible && formAperto.value })

// Scopo: Carica indirizzi. In context 'ruolo' l'API ritorna indirizzi_ruolo + indirizzi_soggetto
//        con campo 'fonte'. In context 'soggetto' ritorna lista piatta.
async function loadIndirizzi() {
  if (!props.soggettoId) return
  listLoading.value = true
  try {
    if (isRuolo.value) {
      const listParams = props.istanzaUtilityId ? { istanza_utility_id: props.istanzaUtilityId } : {}
      const res = await listRuoloIndirizzi(props.soggettoId, listParams)
      const payload = res.data?.data
      if (payload?.indirizzi_ruolo) {
        // Il backend gia' include 'fonte' (utility/ruolo/soggetto) nei dict
        indirizziList.value = sortByFonte([
          ...payload.indirizzi_ruolo,
          ...(payload.indirizzi_soggetto || []),
        ])
      } else {
        indirizziList.value = []
      }
    } else {
      const res = await listSoggettoIndirizzi(props.soggettoId)
      const payload = res.data?.data
      const items = payload?.results || payload || []
      // Ordina per tipo indirizzo alfabetico (coerente con context ruolo)
      indirizziList.value = items.sort((a, b) =>
        (a.tipo_indirizzo_descrizione || '').localeCompare(b.tipo_indirizzo_descrizione || '')
      )
    }
  } catch {
    indirizziList.value = []
  } finally {
    listLoading.value = false
  }
}

// Scopo: Carica matrice tipi indirizzo.
//        Context soggetto: matrice filtrata per tipo_soggetto_dettaglio.
//        Context ruolo: matrice per tipo ruolo (tipi ammessi dal trigger guard).
//        Context soggetto: matrice per tipo soggetto dettaglio.
async function loadMatrice() {
  try {
    if (isRuolo.value && props.tipoRuoloCodice) {
      // Matrice filtrata per tipo ruolo — coerente con trigger DB
      const res = await lookupMatriceIndirizziRuolo(props.tipoRuoloCodice)
      matriceCompleta.value = res.data.data.results
    } else if (props.tipoSoggettoDettaglioId) {
      // Matrice filtrata per tipo soggetto dettaglio
      const res = await lookupMatriceIndirizzi(props.tipoSoggettoDettaglioId)
      matriceCompleta.value = res.data.data.results
    }
  } catch {
    matriceCompleta.value = []
  }
}

// Tipi gia' associati (per filtrare in aggiungi)
const tipiEsistenti = computed(() =>
  new Set(indirizziList.value.map(i => i.tipo_indirizzo_codice_interno))
)

// Matrice filtrata: solo tipi non ancora associati (per aggiungi)
const matriceDisponibile = computed(() =>
  matriceCompleta.value.filter(m => !tipiEsistenti.value.has(m.codice))
)

// Tipi obbligatori mancanti
const tipiMancanti = computed(() =>
  matriceCompleta.value.filter(m => m.obbligatorio && !tipiEsistenti.value.has(m.codice))
)

// Carica dati quando drawer si apre
watch(() => props.visible, async (val) => {
  if (!val) return
  chiudiForm()
  indirizzo.reset()
  // In context ruolo la matrice non serve (il trigger DB valida i tipi ammessi)
  if (isRuolo.value) {
    await loadIndirizzi()
  } else {
    await Promise.all([loadIndirizzi(), loadMatrice()])
  }
})

// Blocca save se indirizzo da stradario non trovato (centralizzato in useIndirizzoBase).
// Aggiunge condizione locale: non in modalita' libera.
const addressNotFound = computed(() =>
  !indirizzo.isLibera.value && indirizzo.addressNotFound.value
)

// === Azioni ===

async function onStartNew() {
  nuovaRiga()
  comuneInitialItem.value = null
  indirizzo.reset()
  if (isRuolo.value) {
    // In context ruolo: carica matrice se non gia' caricata
    if (matriceCompleta.value.length === 0) {
      await loadMatrice()
    }
    indirizzo.setMatrice(matriceCompleta.value, tipiEsistenti.value)
  } else {
    indirizzo.setMatrice(matriceDisponibile.value)
  }
  fissaInline()
}

async function onStartReplace(ind) {
  apriRiga(ind, async () => {
    replaceLabel.value = ind.tipo_indirizzo_descrizione
    indirizzo.reset()
    // La matrice per il replace ha solo il tipo da sostituire
    indirizzo.setMatrice([{
      codice: ind.tipo_indirizzo_codice_interno,
      descrizione: ind.tipo_indirizzo_descrizione,
      obbligatorio: true,
    }])
    // Pre-popola tutti i campi dall'indirizzo esistente (se normalizzato).
    // withSuppressedChecks evita che il watcher scateni il check duplicato
    // (troverebbe lo stesso indirizzo che stiamo modificando).
    // Imposta l'id dettaglio esistente: evita il messaggio "indirizzo non presente"
    // (addressNotFound controlla existingDettaglioId).
    indirizzo.existingDettaglioId.value = ind.indirizzo_dettaglio_id || null
    indirizzo.withSuppressedChecks(() => {
      if (ind.det_comune_id && ind.stradario_id) {
        comuneInitialItem.value = { id: ind.det_comune_id, descrizione: ind.descrizione_comune }
        indirizzo.form.comune_id = ind.det_comune_id
        indirizzo.form.via_obj = {
          stradario_id: ind.stradario_id,
          indirizzo_normalizzato: ind.stradario_display || ind.indirizzo_display,
        }
        indirizzo.form.civico = ind.civico ?? null
        indirizzo.form.estensione_civico = (ind.estensione_civico || '').replace(/^\//, '')
        indirizzo.form.palazzina = ind.palazzina || ''
        indirizzo.form.scala = ind.scala || ''
        indirizzo.form.piano = ind.piano || ''
        indirizzo.form.interno = ind.interno || ''
      } else {
        comuneInitialItem.value = null
      }
    })
    // Fotografia DOPO i CAP: il watch del comune (useIndirizzoBase) gira dopo
    // `withSuppressedChecks`, azzera il CAP e, se il comune ne ha uno solo, lo
    // reimposta da se' a lookup arrivato. Fissare prima farebbe nascere il form
    // «modificato» senza che l'operatore abbia toccato niente.
    await nextTick()
    if (indirizzo.loadingCap.value) {
      await new Promise((fine) => {
        const stop = watch(indirizzo.loadingCap, (caricando) => {
          if (!caricando) { stop(); fine() }
        })
      })
    }
    if (formMode.value === 'edit' && replaceId.value === ind.id) fissaInline()
  })
}

function onCancelForm() {
  chiudiForm()
  comuneInitialItem.value = null
  indirizzo.reset()
}

async function onSaveForm() {
  const payloads = indirizzo.toPayloadArray()
  if (!payloads.length) return

  let success = true

  if (isRuolo.value && formMode.value === 'edit' && replaceId.value) {
    // Context ruolo + replace: DELETE vecchio + CREATE nuovo (stessa transazione lato server non garantita,
    // ma il tipo resta lo stesso quindi il vincolo UNIQUE non e' violato dopo il delete).
    const payload = payloads[0]
    if (indirizzo.existingDettaglioId.value) {
      payload.indirizzo_dettaglio_id = indirizzo.existingDettaglioId.value
    }
    if (props.istanzaUtilityId) {
      payload.istanza_utility_id = props.istanzaUtilityId
    }
    // Step 1: elimina vecchio
    const deleted = await execute(
      () => deleteRuoloIndirizzo(props.soggettoId, replaceId.value),
      { silent: true }
    )
    if (deleted === null) { success = false } else {
      // Step 2: crea nuovo con stesso tipo
      const result = await execute(
        () => createRuoloIndirizzo(props.soggettoId, payload),
        { successMessage: t('indirizzi.indirizzo_salvato') }
      )
      if (result === null) success = false
    }
  } else if (isRuolo.value) {
    // Context ruolo + new: crea nuovo indirizzo
    const payload = payloads[0]
    if (indirizzo.existingDettaglioId.value) {
      payload.indirizzo_dettaglio_id = indirizzo.existingDettaglioId.value
    }
    if (props.istanzaUtilityId) {
      payload.istanza_utility_id = props.istanzaUtilityId
    }
    const result = await execute(
      () => createRuoloIndirizzo(props.soggettoId, payload),
      { successMessage: t('indirizzi.indirizzo_creato') }
    )
    if (result === null) success = false
  } else if (formMode.value === 'edit') {
    const payload = payloads[0]
    if (indirizzo.existingDettaglioId.value) {
      payload.indirizzo_dettaglio_id = indirizzo.existingDettaglioId.value
    }
    const result = await execute(
      () => replaceSoggettoIndirizzo(props.soggettoId, replaceId.value, payload),
      { successMessage: t('indirizzi.indirizzo_salvato') }
    )
    if (result === null) success = false
  } else {
    for (const p of payloads) {
      const result = await execute(
        () => createSoggettoIndirizzo(props.soggettoId, p),
        { successMessage: t('indirizzi.indirizzo_creato') }
      )
      if (result === null) { success = false; break }
    }
  }

  if (success) {
    chiudiForm()
    indirizzo.reset()
    await loadIndirizzi()
    emit('saved')
  }
}

// Scopo: Elimina indirizzo ruolo (solo context ruolo).
async function onDeleteRuolo(ind) {
  const result = await execute(
    () => deleteRuoloIndirizzo(props.soggettoId, ind.id),
    { successMessage: t('indirizzi.indirizzo_eliminato') }
  )
  if (result !== null) {
    await loadIndirizzi()
    emit('saved')
  }
}

const annullaForm = () => chiudiInlineConConferma(onCancelForm)
</script>

<template>
  <!-- Il chrome e' di AppDrawer dal 2026-10-03
       (work-done/analisi-fe-chrome-drawer.md). -->
  <AppDrawer
    :visible="visible"
    :title="t('indirizzi.indirizzo') + ' - ' + t(`anagrafiche.indirizzo_soggetto.context_${context}`)"
    :icon="NAV_ICONS.INDIRIZZO"
    :action="t('common.edit')"
    :width="DRAWER_WIDTH.STANDARD"
    :modificato="modificatoInline"
    :conferma-uscita="chiudiInlineConConferma"
    :footer="formMode ? 'nessuno' : 'chiudi'"
    @update:visible="(v) => emit('update:visible', v)"
  >
    <!-- Loading -->
    <div v-if="listLoading" class="app-loading">
      <i :class="STATUS_ICONS.CARICAMENTO" />
    </div>

    <!-- Lista indirizzi esistenti (sempre visibile) -->
    <template v-if="!listLoading">
      <!-- Contenuto del caller sopra la lista (es. indirizzi gia' impostati
           sul documento in modalita' selezione). -->
      <slot name="pre-list" />
      <div v-if="indirizziList.length === 0 && !formMode" class="app-empty-state">
        <i :class="MANAGE_ICONS.INDIRIZZI" />
        <p>{{ t('anagrafiche.indirizzo_soggetto.nessun_indirizzo') }}</p>
      </div>

      <div v-else-if="indirizziList.length > 0" class="indirizzi-list">
        <div v-for="ind in indirizziList" :key="ind.id" class="indirizzo-select-row">
        <div
          class="indirizzo-card" :class="{ 'indirizzo-card-soggetto': ind.fonte === 'soggetto', 'indirizzo-card-ruolo': ind.fonte === 'ruolo' || ind.fonte === 'istanza' }">
          <div class="indirizzo-card-content">
            <div class="indirizzo-card-nome">
              <Tag v-if="ind.fonte" :value="ind.fonte === 'soggetto' ? t('common.soggetto') : (ind.fonte === 'istanza' && ind.utility_codice ? ind.utility_codice : t('common.ruolo'))"
                :severity="ind.fonte === 'soggetto' ? 'secondary' : 'info'" />
              <Tag :value="ind.tipo_indirizzo_descrizione" severity="info" />
            </div>
            <div class="indirizzo-card-detail">
              <span class="indirizzo-card-text">{{ ind.indirizzo_display || ind.indirizzo_libero }}</span>
              <span v-if="ind.comune_descrizione || ind.descrizione_comune" class="indirizzo-card-comune">
                {{ ind.comune_descrizione || ind.descrizione_comune }}
                <template v-if="ind.cap || ind.cap_codice"> — {{ ind.cap || ind.cap_codice }}</template>
                <template v-if="ind.provincia_sigla"> ({{ ind.provincia_sigla }})</template>
              </span>
            </div>
          </div>
          <!-- Azioni soggetto: solo Cambia (replace) -->
          <Button
            v-if="!formMode && !isReadonly && !isRuolo"
            :icon="MANAGE_ICONS.EDIT"
            text
            rounded
            size="small"
            class="app-action-btn"
            :title="t('anagrafiche.indirizzo_soggetto.cambia_indirizzo')"
            @click="onStartReplace(ind)"
          />
          <!-- Azioni ruolo: cambia + delete (solo se editabile e non readonly) -->
          <div v-if="!formMode && !isReadonly && isRuolo && ind.fonte !== 'soggetto'" class="indirizzo-card-actions">
            <Button :icon="MANAGE_ICONS.EDIT" text rounded size="small"
              :title="t('anagrafiche.indirizzo_soggetto.cambia_indirizzo')"
              @click="onStartReplace(ind)" />
            <Button :icon="MANAGE_ICONS.DELETE" text rounded size="small"
              class="app-delete-btn" :title="t('common.delete')" @click="onDeleteRuolo(ind)" />
          </div>
        </div>
        <!-- Colonna ESTERNA "Usa" (modalita' selezione documento): fuori
             dalla card per non ereditare l'opacita' dei box soggetto. -->
        <Button
          v-if="selectable && !formMode && !isReadonly"
          :icon="MANAGE_ICONS.SELEZIONA"
          :label="t('anagrafiche.indirizzo_soggetto.usa')"
          outlined
          size="small"
          class="app-action-btn indirizzo-card-usa"
          :title="selectTooltip || t('anagrafiche.indirizzo_soggetto.usa_questo')"
          @click="emit('select', ind)"
        />
        </div>
      </div>

      <!-- Warning tipi mancanti -->
      <div v-if="tipiMancanti.length > 0 && !formMode" class="indirizzi-warning">
        <i :class="STATUS_ICONS.ERRORE" />
        {{ t('anagrafiche.indirizzo_soggetto.tipi_mancanti', { tipi: tipiMancanti.map(t => t.descrizione).join(', ') }) }}
      </div>

      <!-- Pulsante aggiungi (soggetto: se ci sono tipi disponibili, ruolo: sempre, mai in readonly) -->
      <div v-if="!formMode && !isReadonly && (isRuolo || matriceDisponibile.length > 0)" class="mt-05">
        <Button
          :label="t('anagrafiche.indirizzo_soggetto.aggiungi_indirizzo')"
          :icon="MANAGE_ICONS.ADD"
          text
          size="small"
          class="app-action-btn"
          @click="onStartNew"
        />
        <!-- Azioni extra del caller accanto ad "aggiungi" (es. indirizzo
             libero una-tantum in modalita' selezione documento). -->
        <slot name="extra-actions" />
      </div>
    </template>

    <!-- Form (aggiungi o cambia) -->
    <template v-if="formMode">
      <div :ref="ancoraForm" class="app-drawer-section">
        <h4>{{ formMode === 'edit'
          ? t('anagrafiche.indirizzo_soggetto.cambia_indirizzo') + ': ' + replaceLabel
          : t('anagrafiche.indirizzo_soggetto.nuovo_indirizzo')
        }}</h4>
      </div>
      <IndirizzoSoggettoForm
        :campi-errati="campiErrati"
        :form="indirizzo.form"
        :is-libera="indirizzo.isLibera.value"
        @update:is-libera="v => indirizzo.isLibera.value = v"
        :tipi-stato="indirizzo.tipiStato.value"
        :tipi-esistenti="[...tipiEsistenti]"
        :stati-lookup="indirizzo.statiLookup"
        :cap-options="indirizzo.capOptions.value"
        :loading-cap="indirizzo.loadingCap.value"
        :auto-clone="indirizzo.autoClone.value"
        @update:auto-clone="v => indirizzo.autoClone.value = v"
        @switch-tipo="indirizzo.switchTipo"
        :indirizzo-warnings="indirizzo.indirizzoWarnings.value"
        :comune-initial-item="comuneInitialItem"
        :disabled="false"
      />

      <Message v-if="addressNotFound" severity="warn" size="small" class="mt-1">
        {{ t('anagrafiche.indirizzo_soggetto.replace_non_trovato') }}
      </Message>

      <FormFooter
        :loading="loading"
        :disabled="!indirizzo.canSave.value || addressNotFound"
        @save="onSaveForm"
        @cancel="annullaForm"
      />
    </template>
  </AppDrawer>
</template>

<style scoped>
.indirizzi-list {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
}

.indirizzo-card {
  display: flex;
  align-items: center;
  justify-content: space-between;
  border: 1px solid var(--p-surface-200);
  border-radius: var(--p-border-radius-sm, 4px);
  padding: 0.5rem 0.75rem;
}

.indirizzo-card-content {
  display: flex;
  align-items: flex-start;
  gap: 0.5rem;
  flex: 1;
  min-width: 0;
}

.indirizzo-card-detail {
  display: flex;
  flex-direction: column;
  min-width: 0;
}

.indirizzo-card-text {
  font-size: 0.85rem;
  color: var(--app-text-color);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.indirizzo-card-soggetto {
  border-color: var(--app-fonte-soggetto-color);
  opacity: 0.5;
}
.indirizzo-card-ruolo {
  border-color: var(--p-blue-300);
}

.indirizzo-card-nome {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  margin-bottom: 0.25rem;
}

.indirizzo-card-comune {
  font-size: 0.75rem;
  color: var(--app-text-muted);
}

.indirizzo-card-actions {
  display: flex;
  gap: 0.25rem;
  flex-shrink: 0;
}

.indirizzi-warning {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  padding: 0.5rem 0.75rem;
  margin-top: 0.5rem;
  background: var(--p-yellow-50);
  border: 1px solid var(--p-yellow-200);
  border-radius: var(--p-border-radius-sm, 4px);
  font-size: 0.8rem;
  color: var(--p-yellow-700);
}
.indirizzo-select-row {
  display: flex;
  align-items: center;
  gap: 0.5rem;
}
.indirizzo-select-row .indirizzo-card {
  flex: 1 1 auto;
  min-width: 0;
}
.indirizzo-card-usa {
  flex: 0 0 auto;
}
</style>
