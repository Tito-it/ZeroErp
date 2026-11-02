<!--
  SPDX-License-Identifier: AGPL-3.0-or-later
  Copyright (C) 2026 Tid (Michele Carlo Titini)
-->
<script setup>
// Scopo: la finestra con cui si APRE un blocco manuale su una coppia
//        (articolo, magazzino) della disponibilita' (Lotto 3 R-5, D-L3-j;
//        piano-be-fe-magazzino-lotto-3 C1): quanti pezzi, per chi (un
//        soggetto) o perche' (una nota), e — se servono — da quale lotto,
//        seriale o scaffale.
//
// ⭐ Un blocco e' una PROMESSA: riserva pezzi a qualcuno e ferma gli scarichi
//    degli altri finche' non lo si libera con un atto (M-3).
// ⭐ Per chi o perche': lo pretende il DB (CHECK `per_chi`), e il rifiuto arriva
//    col campo `nota` acceso. Qui lo si DICE prima (l'aiuto sotto i campi), non
//    lo si ricopia come regola sul pulsante.
// ⚠️ Lotto, seriale e scaffale compaiono se il loro lookup propone qualcosa:
//    la riga della disponibilita' non porta i flag dell'articolo ne'
//    `usa_ubicazioni` del magazzino. Se servono e mancano, la posizione la
//    giudica il verbo (`script.fn_check_riga_magazzino`) col suo motivo.
import { computed, ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import InputNumber from 'primevue/inputnumber'
import InputText from 'primevue/inputtext'
import Select from 'primevue/select'

import AppDialog from '../../core/components/AppDialog.vue'
import SoggettoRuoloLookup from '../../core/components/SoggettoRuoloLookup.vue'
import { useApiHandler } from '../../core/composables/useApiHandler'
import { useFotografiaDialog } from '../../core/composables/useFotografiaDialog'
import { RISULTATI, useLetturaTreStati } from '../../core/composables/useLetturaTreStati'
import { QTA_MAX_DECIMALI } from '../../core/utils/format'
import { apriBlocco, lookupAssets, lookupLotti, lookupUbicazioni } from '../api/magazzino'

const props = defineProps({
  visible: { type: Boolean, default: false },
  // La riga della disponibilita': articolo_id/_codice, magazzino_id/_codice.
  riga: { type: Object, default: null },
})
const emit = defineEmits(['update:visible', 'aperto'])
const { t } = useI18n()
const { execute, loading, campiErrati } = useApiHandler()

const lotti = useLetturaTreStati(lookupLotti, { estrai: RISULTATI, vuoto: [] })
const assets = useLetturaTreStati(lookupAssets, { estrai: RISULTATI, vuoto: [] })
const ubicazioni = useLetturaTreStati(lookupUbicazioni, { estrai: RISULTATI, vuoto: [] })

function defaultForm() {
  return { qta: null, soggetto_obj: null, nota: '', lotto_id: null, asset_id: null, ubicazione_id: null }
}
const form = ref(defaultForm())

// Scopo: riazzera il form e rilegge i lookup di posizione a ogni apertura.
watch(() => props.visible, (aperto) => {
  if (!aperto || !props.riga) return
  form.value = defaultForm()
  lotti.carica(props.riga.articolo_id)
  assets.carica(props.riga.articolo_id, props.riga.magazzino_id)
  ubicazioni.carica(props.riga.magazzino_id)
})

const canSave = computed(() => Number(form.value.qta) > 0)

async function onSave() {
  const payload = {
    magazzino_id: props.riga.magazzino_id,
    articolo_id: props.riga.articolo_id,
    qta: form.value.qta,
    soggetto_ruolo_id: form.value.soggetto_obj?.soggetto_ruolo_id ?? null,
    nota: form.value.nota?.trim() || null,
    lotto_id: form.value.lotto_id,
    asset_id: form.value.asset_id,
    ubicazione_id: form.value.ubicazione_id,
  }
  const esito = await execute(() => apriBlocco(payload), { successMessage: t('magazzino.blocchi.aperto') })
  if (esito === null) return
  emit('aperto', esito.blocco_id ?? null)
  emit('update:visible', false)
}

function onCancel() { emit('update:visible', false) }

const fotografia = useFotografiaDialog(() => ({ ...form.value }), { visibile: () => props.visible })
</script>

<template>
  <AppDialog
    :conferma-uscita="fotografia.chiudiConConferma"
    :visible="visible"
    :header="t('magazzino.blocchi.titolo_apri')"
    width="md"
    :loading="loading"
    :save-disabled="!canSave"
    :save-label="t('magazzino.blocchi.apri_conferma')"
    @update:visible="(v) => emit('update:visible', v)"
    @save="onSave"
    @cancel="onCancel"
  >
    <div class="form-grid">
      <p v-if="riga" class="app-text-muted" style="margin: 0;">
        {{ riga.articolo_codice }} · {{ riga.magazzino_codice }}
      </p>
      <div class="form-field">
        <label>{{ t('magazzino.blocchi.campo_qta') }} *</label>
        <InputNumber v-model="form.qta" :min="0" :max-fraction-digits="QTA_MAX_DECIMALI"
                     :invalid="campiErrati.includes('qta')" />
      </div>
      <div class="form-field">
        <label>{{ t('magazzino.blocchi.campo_soggetto') }}</label>
        <SoggettoRuoloLookup solo-con-ruolo v-model="form.soggetto_obj"
                             :invalid="campiErrati.includes('soggetto_ruolo_id')"
                             :placeholder="t('magazzino.blocchi.campo_soggetto')" />
      </div>
      <div class="form-field">
        <label>{{ t('magazzino.blocchi.campo_nota') }}</label>
        <InputText v-model="form.nota" maxlength="500" :invalid="campiErrati.includes('nota')" />
        <small class="app-text-muted">{{ t('magazzino.blocchi.per_chi_aiuto') }}</small>
      </div>
      <div v-if="lotti.dati.value.length" class="form-field">
        <label>{{ t('magazzino.blocchi.campo_lotto') }}</label>
        <Select v-model="form.lotto_id" :options="lotti.dati.value" option-label="codice"
                option-value="id" filter show-clear :invalid="campiErrati.includes('lotto_id')" />
      </div>
      <div v-if="assets.dati.value.length" class="form-field">
        <label>{{ t('magazzino.blocchi.campo_seriale') }}</label>
        <Select v-model="form.asset_id" :options="assets.dati.value" option-label="seriale"
                option-value="id" filter show-clear :invalid="campiErrati.includes('asset_id')" />
      </div>
      <div v-if="ubicazioni.dati.value.length" class="form-field">
        <label>{{ t('magazzino.blocchi.campo_ubicazione') }}</label>
        <Select v-model="form.ubicazione_id" :options="ubicazioni.dati.value" option-label="codice"
                option-value="id" filter show-clear :invalid="campiErrati.includes('ubicazione_id')" />
      </div>
    </div>
  </AppDialog>
</template>
