<!--
  SPDX-License-Identifier: GPL-3.0-or-later
  Copyright (C) 2026 Tid (Michele Carlo Titini)
-->
<script setup>
// Scopo: UNA voce da prelevare della bolla — la riga, o un componente del kit
//        (Lotto 3 D-L3-b/f, piano-be-fe-magazzino-lotto-3 B1): quanto va
//        prelevato e quanto lo e' gia' (UoM base), i suoi prelievi, e il form
//        per aggiungerne uno. Usata da `DdtPrelieviSection`.
//
// ⭐ I campi compaiono solo se servono, dai flag che il backend porta: lotto se
//    l'articolo `requires_lotto`, seriale se `requires_serial` (e allora la
//    quantita' e' 1), ubicazione se il magazzino di partenza `usa_ubicazioni`,
//    ubicazione di arrivo se lo usa quello di arrivo. Una voce AUTOMATICA non
//    chiede niente: il prelievo lo crea il DB all'emissione.
// ⛔ Nessuna regola ricopiata: somma rispetto alla riga, disponibilita', kit,
//    bozza li giudica il DB (il rifiuto arriva come toast col suo motivo).
//    L'ubicazione di arrivo resta modificabile anche dopo l'emissione, fino al
//    CONSEGNATO: lo decide il lock del DB, qui la si offre finche' il drawer
//    non e' in sola lettura.
import { ref, computed, onMounted } from 'vue'
import { useI18n } from 'vue-i18n'
import { useApiHandler } from '../../../core/composables/useApiHandler'
import { RISULTATI, useLetturaTreStati } from '../../../core/composables/useLetturaTreStati'
import { MANAGE_ICONS } from '../../../core/constants'
import { formatQuantita, QTA_MAX_DECIMALI } from '../../../core/utils/format'
import { lookupAssets, lookupLotti, lookupUbicazioni } from '../../../magazzino/api/magazzino'
import { createPrelievo, deletePrelievo, updatePrelievo } from '../api/ddtApi'
import Button from 'primevue/button'
import InputNumber from 'primevue/inputnumber'
import Select from 'primevue/select'
import Tag from 'primevue/tag'

const props = defineProps({
  ddtId: { type: Number, required: true },
  voce: { type: Object, required: true },
  // La testata dei prelievi: magazzini e `usa_ubicazioni`.
  testata: { type: Object, required: true },
  // Aggiungere e togliere prelievi (bozza, permessi).
  modificabile: { type: Boolean, default: false },
  // Scegliere l'ubicazione di arrivo (anche dopo l'emissione: decide il DB).
  arrivoModificabile: { type: Boolean, default: false },
})
const emit = defineEmits(['changed'])
const { t } = useI18n()
const { execute, loading, campiErrati } = useApiHandler()

const qta = computed(() => Number(props.voce.qta))
const prelevata = computed(() => Number(props.voce.prelevata))
// Tre stati, non due: oltre la quantita' della riga NON e' «da completare» (la
// conferma la rifiuta per somma diversa, e aggiungere peggiorerebbe).
const copertura = computed(() => {
  if (prelevata.value < qta.value) return 'manca'
  return prelevata.value > qta.value ? 'oltre' : 'completa'
})
const richiedeLotto = computed(() => props.voce.requires_lotto === true)
const richiedeSeriale = computed(() => props.voce.requires_serial === true)
const conUbicazione = computed(() => props.testata.magazzino_usa_ubicazioni === true)
const conArrivo = computed(() => props.testata.magazzino_arrivo_usa_ubicazioni === true)

// I lookup di posizione, solo se servono (e solo con un magazzino scelto).
const lotti = useLetturaTreStati(lookupLotti, { estrai: RISULTATI, vuoto: [] })
const assets = useLetturaTreStati(lookupAssets, { estrai: RISULTATI, vuoto: [] })
const ubicazioni = useLetturaTreStati(lookupUbicazioni, { estrai: RISULTATI, vuoto: [] })
const ubicazioniArrivo = useLetturaTreStati(lookupUbicazioni, { estrai: RISULTATI, vuoto: [] })

onMounted(() => {
  const servePosizione = props.modificabile && !props.voce.automatico
  if (servePosizione && richiedeLotto.value) lotti.carica(props.voce.articolo_id)
  if (servePosizione && richiedeSeriale.value && props.testata.magazzino_id) {
    assets.carica(props.voce.articolo_id, props.testata.magazzino_id)
  }
  if (servePosizione && conUbicazione.value) ubicazioni.carica(props.testata.magazzino_id)
  if (props.arrivoModificabile && conArrivo.value) ubicazioniArrivo.carica(props.testata.magazzino_arrivo_id)
})

function nuovoForm() {
  const residuo = Math.max(qta.value - prelevata.value, 0)
  return {
    qta: richiedeSeriale.value ? 1 : residuo,
    lotto_id: null,
    asset_id: null,
    ubicazione_id: null,
    ubicazione_arrivo_id: null,
  }
}
const form = ref(nuovoForm())

const canAggiungere = computed(() => props.modificabile && !props.voce.automatico && copertura.value === 'manca')
// Lo scaffale di arrivo si sceglie in una tendina solo se si cambia ancora;
// altrimenti si legge, col codice, accanto alla posizione.
const arrivoInTendina = computed(() => conArrivo.value && props.arrivoModificabile)

async function aggiungi() {
  const payload = {
    qta: form.value.qta,
    ddt_riga_componente_id: props.voce.ddt_riga_componente_id,
    lotto_id: form.value.lotto_id,
    asset_id: form.value.asset_id,
    ubicazione_id: form.value.ubicazione_id,
    ubicazione_arrivo_id: form.value.ubicazione_arrivo_id,
  }
  const res = await execute(
    () => createPrelievo(props.ddtId, props.voce.ddt_riga_id, payload),
    { successMessage: t('vendite.ddt.prelievi.salvato') },
  )
  if (res !== null) {
    form.value = nuovoForm()
    emit('changed')
  }
}

async function togli(prelievo) {
  const res = await execute(
    () => deletePrelievo(props.ddtId, props.voce.ddt_riga_id, prelievo.id),
    { successMessage: t('vendite.ddt.prelievi.tolto') },
  )
  if (res !== null) emit('changed')
}

async function cambiaArrivo(prelievo, ubicazioneArrivoId) {
  const res = await execute(
    () => updatePrelievo(props.ddtId, props.voce.ddt_riga_id, prelievo.id, {
      ubicazione_arrivo_id: ubicazioneArrivoId ?? null,
    }),
    { successMessage: t('vendite.ddt.prelievi.salvato') },
  )
  if (res !== null) emit('changed')
}

// Le parti fisiche di un prelievo, per la riga di sola lettura (lo scaffale di
// arrivo solo quando non sta nella tendina).
function posizione(p) {
  return [
    p.lotto_codice && `${t('vendite.ddt.prelievi.campo_lotto')} ${p.lotto_codice}`,
    p.asset_seriale && `${t('vendite.ddt.prelievi.campo_seriale')} ${p.asset_seriale}`,
    p.ubicazione_codice && `${t('vendite.ddt.prelievi.campo_ubicazione')} ${p.ubicazione_codice}`,
    !arrivoInTendina.value && p.ubicazione_arrivo_codice
      && `${t('vendite.ddt.prelievi.campo_ubicazione_arrivo')} ${p.ubicazione_arrivo_codice}`,
  ].filter(Boolean).join(' · ')
}
</script>

<template>
  <div class="app-voce-merce">
    <div class="app-voce-merce-testa">
      <span>
        <strong>{{ t('vendite.ddt.prelievi.voce_riga', { nr: voce.riga_nr }) }}</strong>
        · {{ voce.articolo_codice }} — {{ voce.articolo_descrizione }}
        <small v-if="voce.ddt_riga_componente_id" class="app-text-muted">
          ({{ t('vendite.ddt.prelievi.componente') }})
        </small>
      </span>
      <span class="app-voce-merce-stato">
        <span>{{ t('vendite.ddt.prelievi.prelevata', {
          prelevata: formatQuantita(prelevata), qta: formatQuantita(qta), uom: voce.uom_codice || '',
        }) }}</span>
        <Tag v-if="voce.automatico && voce.prelievi.length === 0"
             severity="info" :value="t('vendite.ddt.prelievi.automatico')" />
        <Tag v-else-if="copertura === 'completa'" severity="success" :value="t('vendite.ddt.prelievi.completo')" />
        <Tag v-else-if="copertura === 'oltre'" severity="danger" :value="t('vendite.ddt.prelievi.oltre')" />
        <Tag v-else severity="warn" :value="t('vendite.ddt.prelievi.da_completare')" />
      </span>
    </div>

    <ul v-if="voce.prelievi.length" class="app-voce-merce-lista">
      <li v-for="p in voce.prelievi" :key="p.id">
        <span>{{ formatQuantita(p.qta) }} {{ voce.uom_codice || '' }}</span>
        <span class="app-text-muted">{{ posizione(p) }}</span>
        <Select
          v-if="arrivoInTendina"
          :model-value="p.ubicazione_arrivo_id"
          :options="ubicazioniArrivo.dati.value"
          option-label="codice" option-value="id"
          :placeholder="t('vendite.ddt.prelievi.campo_ubicazione_arrivo')"
          :disabled="loading"
          show-clear
          @change="(e) => cambiaArrivo(p, e.value)" />
        <Button v-if="modificabile" :icon="MANAGE_ICONS.DELETE" severity="danger" text rounded
                v-tooltip.bottom="t('vendite.ddt.prelievi.togli')"
                :aria-label="t('vendite.ddt.prelievi.togli')"
                :loading="loading" @click="togli(p)" />
      </li>
    </ul>

    <div v-if="canAggiungere" class="app-voce-merce-form">
      <InputNumber v-if="!richiedeSeriale" v-model="form.qta" :min="0"
                   :max-fraction-digits="QTA_MAX_DECIMALI" :invalid="campiErrati.includes('qta')"
                   :placeholder="t('vendite.ddt.prelievi.campo_qta')" />
      <Select v-if="richiedeLotto" v-model="form.lotto_id" :options="lotti.dati.value"
              option-label="codice" option-value="id" filter show-clear
              :loading="lotti.loading.value"
              :placeholder="t('vendite.ddt.prelievi.campo_lotto')" />
      <Select v-if="richiedeSeriale" v-model="form.asset_id" :options="assets.dati.value"
              option-label="seriale" option-value="id" filter show-clear
              :loading="assets.loading.value"
              :placeholder="t('vendite.ddt.prelievi.campo_seriale')" />
      <Select v-if="conUbicazione" v-model="form.ubicazione_id" :options="ubicazioni.dati.value"
              option-label="codice" option-value="id" filter show-clear
              :loading="ubicazioni.loading.value"
              :placeholder="t('vendite.ddt.prelievi.campo_ubicazione')" />
      <Select v-if="conArrivo" v-model="form.ubicazione_arrivo_id" :options="ubicazioniArrivo.dati.value"
              option-label="codice" option-value="id" filter show-clear
              :placeholder="t('vendite.ddt.prelievi.campo_ubicazione_arrivo')" />
      <Button :icon="MANAGE_ICONS.ADD" :label="t('vendite.ddt.prelievi.aggiungi')"
              class="app-action-btn" :loading="loading" @click="aggiungi" />
    </div>
  </div>
</template>

