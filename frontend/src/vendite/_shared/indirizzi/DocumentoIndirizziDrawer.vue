<script setup>
// Scopo: Drawer di GESTIONE indirizzi documento (UX v2, brief design §7).
//        Riusa `IndirizziSoggettoDrawer` (context ruolo, cascata
//        istanza→ruolo→soggetto con badge fonte) in modalita' `selectable`:
//        l'operatore sceglie un indirizzo del cliente e "usa questo" lo
//        imposta sul documento. Regola tipo (decisa 2026-07-12):
//        - default = CON (Consegna, standard cross-dominio), fallback FATT;
//        - se il dominio ammette PIU' tipi, dialog "Usa come" (soli ammessi);
//          con un solo tipo (DDT) nessuna domanda.
//        Nel drawer vivono anche: riepilogo degli indirizzi GIA' impostati
//        sul documento (slot #pre-list, con rimozione), "aggiungi indirizzo"
//        anagrafico sul ruolo (nativo del componente riusato) e "indirizzo
//        libero" una-tantum (slot #extra-actions).
//        Righe fonte=soggetto: nessuna riga in `anagrafiche.indirizzi` →
//        impostate come snapshot dai dati mostrati (origine_* assente).

import { computed, ref } from 'vue'
import { useI18n } from 'vue-i18n'
import Button from 'primevue/button'
import InputText from 'primevue/inputtext'
import Message from 'primevue/message'
import Select from 'primevue/select'
import Tag from 'primevue/tag'
import AppDialog from '../../../core/components/AppDialog.vue'
import IndirizziSoggettoDrawer from '../../../anagrafiche/components/IndirizziSoggettoDrawer.vue'
import { useApiHandler } from '../../../core/composables/useApiHandler'
import { useNotify } from '../../../core/composables/useNotify'
import { useConfirmAction } from '../../../core/composables/useConfirmAction'
import { useInjectReadonly } from '../../../core/composables/useReadonlyMode'
import { MANAGE_ICONS, TIPO_RUOLO } from '../../../core/constants'
import IndirizzoProvenienzaTags from './IndirizzoProvenienzaTags.vue'
import { formatSnapshotDisplay, makeIndirizziDocumentoApi, pickTipoDefault } from './documentoIndirizziApi'
import { useFotografiaDialog } from '../../../core/composables/useFotografiaDialog'

const props = defineProps({
  visible: { type: Boolean, default: false },
  // Slug dominio per il basePath API: `/vendite/{dominio}`.
  dominio: { type: String, required: true },
  docId: { type: [Number, null], default: null },
  // soggetto_ruolo del cliente del documento (lista indirizzi anagrafici).
  soggettoRuoloId: { type: [Number, null], default: null },
  istanzaUtilityId: { type: [Number, null], default: null },
  // Tipo ruolo per la matrice tipi dell'"aggiungi indirizzo" anagrafico.
  tipoRuoloCodice: { type: String, default: TIPO_RUOLO.CLIENTE },
  readonly: { type: Boolean, default: false },
  // Stato documento posseduto dalla SEZIONE contenitrice (single source):
  // tipi ammessi + slot impostati. Passati per props → il drawer NON rifetcha
  // (era la doppia GET sezione+drawer). Dopo un save/remove il drawer emette
  // `changed`: la sezione rifetcha e ripassa i props aggiornati.
  tipiAmmessi: { type: Array, default: () => [] },
  indirizzi: { type: Array, default: () => [] },
})
const emit = defineEmits(['update:visible', 'changed'])

const { t } = useI18n()
const { execute, campiErrati } = useApiHandler()
const notify = useNotify()
const { confirmAction } = useConfirmAction()

const parentReadonly = useInjectReadonly()
const isReadonlyEffective = computed(() => props.readonly || parentReadonly.value)

const apiClient = makeIndirizziDocumentoApi(`/vendite/${props.dominio}`)

// Tipo di default: regola condivisa sezione/drawer (pickTipoDefault). Legge
// dai props (stato posseduto dalla sezione), non da una fetch locale.
const tipoDefault = computed(() => pickTipoDefault(props.tipiAmmessi))

async function saveSlot(payload) {
  const res = await execute(() => apiClient.upsert(props.docId, payload))
  if (res !== null) {
    notify.success(t('vendite.indirizzi.salvato'))
    // Refresh via parent: `changed` → la sezione rifetcha e ripassa i props.
    emit('changed')
  }
  return res !== null
}

// ── Selezione dall'elenco cliente ("usa questo") ──
const usaComeVisible = ref(false)
const usaComeTipoId = ref(null)
const rigaSelezionata = ref(null)

function onSelect(riga) {
  if (!tipoDefault.value) return
  rigaSelezionata.value = riga
  if (props.tipiAmmessi.length > 1) {
    // Piu' tipi ammessi: scelta "usa come" con default preselezionato.
    usaComeTipoId.value = tipoDefault.value.tipo_indirizzo_id
    usaComeVisible.value = true
  } else {
    void confermaSelezione(tipoDefault.value.tipo_indirizzo_id)
  }
}

async function confermaSelezione(tipoIndirizzoId) {
  const riga = rigaSelezionata.value
  if (!riga) return
  let payload
  if (riga.fonte === 'soggetto') {
    // Layer soggetto: nessuna riga in anagrafiche.indirizzi → snapshot dai
    // dati risolti mostrati (origine_* assente, come una-tantum).
    payload = {
      tipo_indirizzo_id: tipoIndirizzoId,
      // Provenienza anagrafica soggetto (validata dal BE contro il cliente
      // del documento): distingue il tag "Soggetto" dal vero una-tantum.
      origine_soggetto_ruolo_id: props.soggettoRuoloId,
      snapshot: {
        via: riga.indirizzo_display || riga.indirizzo_libero || '',
        cap: riga.cap || riga.cap_codice || '',
        citta: riga.comune_descrizione || riga.descrizione_comune || '',
        prov: (riga.provincia_sigla || '').trim(),
        // Paese: senza, un indirizzo estero congelato dal picker
        // divergerebbe dallo stesso indirizzo auto-assegnato dal BE
        // (find_snapshot_soggetto_per_tipi include stato_iso2).
        stato: (riga.stato_iso2 || '').trim(),
      },
    }
  } else {
    // Layer ruolo/istanza: aggancio con origine (snapshot server-side, D-5).
    payload = { tipo_indirizzo_id: tipoIndirizzoId, origine_indirizzo_id: riga.id }
  }
  const ok = await saveSlot(payload)
  if (ok) {
    usaComeVisible.value = false
    rigaSelezionata.value = null
  }
}

// ── Indirizzo libero (una-tantum) ──
const liberoVisible = ref(false)
const liberoTipoId = ref(null)
const liberoForm = ref({})

function openLibero() {
  if (!tipoDefault.value) return
  liberoTipoId.value = tipoDefault.value.tipo_indirizzo_id
  // Prefill SOLO se lo slot default e' un vero una-tantum: le righe "da
  // soggetto" (origine_soggetto_ruolo_id valorizzato) restano fuori —
  // prefillarle e risalvare senza origine le riclassificherebbe
  // silenziosamente in una-tantum perdendo la provenienza anagrafica.
  const row = props.indirizzi.find(
    (r) => r.tipo_indirizzo_id === tipoDefault.value.tipo_indirizzo_id
      && !r.origine_indirizzo_id && !r.origine_soggetto_ruolo_id)
  const s = row?.snapshot ?? {}
  liberoForm.value = {
    intestazione: s.intestazione ?? '', via: s.via ?? '', cap: s.cap ?? '',
    citta: s.citta ?? '', prov: s.prov ?? '', stato: s.stato ?? '',
    email: s.email ?? '', telefono: s.telefono ?? '', note: s.note ?? '',
  }
  liberoVisible.value = true
}

const liberoValido = computed(() =>
  Boolean(liberoForm.value.via?.trim() || liberoForm.value.citta?.trim()))

async function confermaLibero() {
  // liberoTipoId e' sempre inizializzato da openLibero (= tipoDefault);
  // la Select lo cambia solo quando i tipi ammessi sono >1.
  const payload = {
    tipo_indirizzo_id: liberoTipoId.value,
    snapshot: { ...liberoForm.value },
  }
  const ok = await saveSlot(payload)
  if (ok) liberoVisible.value = false
}

// ── Rimozione slot impostato ──
function removeSlot(row) {
  confirmAction({
    header: t('vendite.indirizzi.rimuovi'),
    message: t('vendite.indirizzi.conferma_rimozione'),
    danger: true,
    onAccept: async () => {
      const res = await execute(() => apiClient.remove(props.docId, row.id))
      if (res !== null) {
        notify.success(t('vendite.indirizzi.rimosso'))
        // Refresh via parent (come saveSlot): niente GET locale.
        emit('changed')
      }
    },
  })
}

// D-14: uscire dai due dialog con dati inseriti chiede (AppDialog `conferma-uscita`).
const fotoUsaCome = useFotografiaDialog(() => ({ tipo: usaComeTipoId.value }), { visibile: () => usaComeVisible.value })
const fotoLibero = useFotografiaDialog(() => ({ tipo: liberoTipoId.value, ...liberoForm.value }), { visibile: () => liberoVisible.value })
</script>

<template>
  <IndirizziSoggettoDrawer
    :visible="visible"
    @update:visible="emit('update:visible', $event)"
    context="ruolo"
    :soggetto-id="soggettoRuoloId"
    :istanza-utility-id="istanzaUtilityId"
    :tipo-ruolo-codice="tipoRuoloCodice"
    selectable
    :select-tooltip="t('vendite.indirizzi.usa_questo')"
    @select="onSelect">
    <!-- Riepilogo: indirizzi GIA' impostati su questo documento. -->
    <template #pre-list>
      <div class="app-drawer-section indirizzi-doc-summary">
        <h4>{{ t('vendite.indirizzi.impostati_titolo') }}</h4>
        <Message
          v-if="!indirizzi.length"
          :severity="tipoDefault?.obbligatorio ? 'warn' : 'info'"
          :closable="false">
          {{ tipoDefault?.obbligatorio
            ? t('vendite.indirizzi.mancante_obbligatorio')
            : t('vendite.indirizzi.non_impostato') }}
        </Message>
        <div v-for="row in indirizzi" :key="row.id" class="indirizzi-doc-row">
          <Tag :value="row.tipo_indirizzo_descrizione" severity="info" />
          <span class="indirizzi-doc-display">{{ formatSnapshotDisplay(row) }}</span>
          <!-- Provenienza: BB condiviso con la sezione inline. -->
          <IndirizzoProvenienzaTags :row="row" />
          <Button
            v-if="!isReadonlyEffective"
            :icon="MANAGE_ICONS.DELETE"
            text
            rounded
            size="small"
            class="app-delete-btn"
            :title="t('vendite.indirizzi.rimuovi')"
            @click="removeSlot(row)" />
        </div>
      </div>
    </template>

    <!-- Azione extra accanto ad "aggiungi indirizzo" (anagrafico). -->
    <template #extra-actions>
      <Button
        :label="t('vendite.indirizzi.indirizzo_libero')"
        :icon="MANAGE_ICONS.EDIT"
        text
        size="small"
        class="app-action-btn"
        @click="openLibero" />
    </template>
  </IndirizziSoggettoDrawer>

  <!-- Dialog "Usa come": solo quando il dominio ammette piu' tipi. -->
  <AppDialog
    :conferma-uscita="fotoUsaCome.chiudiConConferma"
    v-model:visible="usaComeVisible"
    :header="t('vendite.indirizzi.usa_come')"
    width="sm"
    :readonly="false"
    :save-disabled="!usaComeTipoId"
    @save="confermaSelezione(usaComeTipoId)">
    <div class="form-field">
      <label>{{ t('vendite.indirizzi.usa_come_tipo') }}</label>
      <Select
        v-model="usaComeTipoId"
        :options="tipiAmmessi"
        option-label="tipo_indirizzo_descrizione"
        option-value="tipo_indirizzo_id"
        class="indirizzi-usa-come-select" />
    </div>
  </AppDialog>

  <!-- Dialog una-tantum: indirizzo occasionale non in anagrafica. -->
  <AppDialog
    :conferma-uscita="fotoLibero.chiudiConConferma"
    v-model:visible="liberoVisible"
    :header="t('vendite.indirizzi.indirizzo_libero')"
    width="md"
    :readonly="false"
    :save-disabled="!liberoValido"
    @save="confermaLibero">
    <div class="form-grid">
      <div v-if="tipiAmmessi.length > 1" class="form-field">
        <label>{{ t('vendite.indirizzi.usa_come_tipo') }}</label>
        <Select
          v-model="liberoTipoId"
          :options="tipiAmmessi"
          option-label="tipo_indirizzo_descrizione"
          option-value="tipo_indirizzo_id"
          class="indirizzi-usa-come-select" />
      </div>
      <div class="form-field">
        <label>{{ t('vendite.indirizzi.field_intestazione') }}</label>
        <InputText v-model="liberoForm.intestazione" />
      </div>
      <div class="form-field">
        <label>{{ t('vendite.indirizzi.field_via') }}</label>
        <InputText v-model="liberoForm.via" />
      </div>
      <div class="form-grid-2col">
        <div class="form-field">
          <label>{{ t('vendite.indirizzi.field_cap') }}</label>
          <InputText v-model="liberoForm.cap" />
        </div>
        <div class="form-field">
          <label>{{ t('vendite.indirizzi.field_citta') }}</label>
          <InputText v-model="liberoForm.citta" />
        </div>
      </div>
      <div class="form-grid-2col">
        <div class="form-field">
          <label>{{ t('vendite.indirizzi.field_prov') }}</label>
          <InputText v-model="liberoForm.prov" />
        </div>
        <div class="form-field">
          <label>{{ t('vendite.indirizzi.field_stato') }}</label>
          <InputText v-model="liberoForm.stato"
            :invalid="campiErrati.includes('stato')" />
        </div>
      </div>
      <div class="form-grid-2col">
        <div class="form-field">
          <label>{{ t('vendite.indirizzi.field_email') }}</label>
          <InputText v-model="liberoForm.email" />
        </div>
        <div class="form-field">
          <label>{{ t('vendite.indirizzi.field_telefono') }}</label>
          <InputText v-model="liberoForm.telefono" />
        </div>
      </div>
      <div class="form-field">
        <label>{{ t('vendite.indirizzi.field_note') }}</label>
        <InputText v-model="liberoForm.note"
          :invalid="campiErrati.includes('note')" />
      </div>
    </div>
  </AppDialog>
</template>

<style scoped>
.indirizzi-doc-summary {
  margin-bottom: 0.75rem;
}
.indirizzi-doc-row {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  padding: 0.25rem 0;
}
.indirizzi-doc-display {
  flex: 1 1 auto;
  min-width: 0;
}
.indirizzi-usa-come-select {
  width: 100%;
}
</style>
