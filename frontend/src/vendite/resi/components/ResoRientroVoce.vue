<!--
  SPDX-License-Identifier: GPL-3.0-or-later
  Copyright (C) 2026 Tid (Michele Carlo Titini)
-->
<script setup>
// Scopo: UNA voce del reso che fa rientrare merce — la riga, o un componente
//        del kit com'era uscito (3-bis D-3b-b/g, piano-be-fe-magazzino-lotto-3
//        B2): quanto deve rientrare e quanto e' gia' rientrato (UoM base), i
//        suoi rientri, e il form per aggiungerne uno. Usata da
//        `ResoRientriSection`.
//
// ⭐ Il rientro si fa da un PRELIEVO d'origine della bolla, che si SCEGLIE:
//    lotto e seriale vengono da lui e si mostrano, non si scelgono (li ha
//    decisi l'uscita). L'ubicazione si chiede solo se il magazzino di rientro
//    `usa_ubicazioni`. Una voce AUTOMATICA (un solo prelievo, proporzione
//    esatta, magazzino senza ubicazioni) non chiede niente: il rientro lo crea
//    il DB alla conferma — salvo che l'operatore scriva un rientro sulla riga,
//    che allora se la prende intera (un kit reso senza un pezzo si dice cosi').
// ⛔ Nessuna regola ricopiata: quadratura, tetto per prelievo, ubicazione li
//    giudica la conferma (`script.fn_check_reso_merce`).
import { ref, computed, onMounted } from 'vue'
import { useI18n } from 'vue-i18n'
import { useApiHandler } from '../../../core/composables/useApiHandler'
import { RISULTATI, useLetturaTreStati } from '../../../core/composables/useLetturaTreStati'
import { MANAGE_ICONS } from '../../../core/constants'
import { formatQuantita, QTA_MAX_DECIMALI } from '../../../core/utils/format'
import { lookupUbicazioni } from '../../../magazzino/api/magazzino'
import { createRientro, deleteRientro } from '../api/resiApi'
import Button from 'primevue/button'
import InputNumber from 'primevue/inputnumber'
import Select from 'primevue/select'
import Tag from 'primevue/tag'

const props = defineProps({
  resoId: { type: Number, required: true },
  voce: { type: Object, required: true },
  // La testata dei rientri: magazzino di rientro e `usa_ubicazioni`.
  testata: { type: Object, required: true },
  // Aggiungere e togliere rientri (bozza, permessi).
  modificabile: { type: Boolean, default: false },
})
const emit = defineEmits(['changed'])
const { t } = useI18n()
const { execute, loading, campiErrati } = useApiHandler()

const qta = computed(() => Number(props.voce.qta))
const rientrata = computed(() => Number(props.voce.rientrata))
// Tre stati, come i prelievi: oltre quanto deve rientrare non e' «da completare».
const copertura = computed(() => {
  if (rientrata.value < qta.value) return 'manca'
  return rientrata.value > qta.value ? 'oltre' : 'completa'
})
const conUbicazione = computed(() => props.testata.magazzino_usa_ubicazioni === true)

const ubicazioni = useLetturaTreStati(lookupUbicazioni, { estrai: RISULTATI, vuoto: [] })
onMounted(() => {
  if (props.modificabile && conUbicazione.value) ubicazioni.carica(props.testata.magazzino_id)
})

// L'etichetta di un prelievo d'origine: quanto era uscito e da dove.
function etichettaOrigine(p) {
  const parti = [
    p.lotto_codice && `${t('vendite.resi.rientri.lotto')} ${p.lotto_codice}`,
    p.asset_seriale && `${t('vendite.resi.rientri.seriale')} ${p.asset_seriale}`,
    p.ubicazione_codice && `${t('vendite.resi.rientri.da_ubicazione')} ${p.ubicazione_codice}`,
  ].filter(Boolean)
  const dove = parti.length ? parti.join(' · ') : t('vendite.resi.rientri.senza_posizione')
  return `${dove} — ${t('vendite.resi.rientri.uscito', { qta: formatQuantita(p.qta), uom: props.voce.uom_codice || '' })}`
}
const opzioniOrigine = computed(() => props.voce.prelievi_origine.map((p) => ({ id: p.id, etichetta: etichettaOrigine(p) })))

function nuovoForm() {
  return {
    // Con un solo prelievo d'origine la scelta e' gia' fatta.
    ddt_riga_prelievo_id: props.voce.prelievi_origine.length === 1 ? props.voce.prelievi_origine[0].id : null,
    qta: Math.max(qta.value - rientrata.value, 0),
    ubicazione_id: null,
  }
}
const form = ref(nuovoForm())

// Anche una voce automatica si puo' dettagliare: chi scrive un rientro sulla
// riga se la prende intera (vedi in testa).
const canAggiungere = computed(() => props.modificabile && copertura.value === 'manca')

async function aggiungi() {
  const res = await execute(
    () => createRientro(props.resoId, props.voce.resi_riga_id, { ...form.value }),
    { successMessage: t('vendite.resi.rientri.salvato') },
  )
  if (res !== null) {
    form.value = nuovoForm()
    emit('changed')
  }
}

async function togli(rientro) {
  const res = await execute(
    () => deleteRientro(props.resoId, props.voce.resi_riga_id, rientro.id),
    { successMessage: t('vendite.resi.rientri.tolto') },
  )
  if (res !== null) emit('changed')
}

function posizione(r) {
  return [
    r.lotto_codice && `${t('vendite.resi.rientri.lotto')} ${r.lotto_codice}`,
    r.asset_seriale && `${t('vendite.resi.rientri.seriale')} ${r.asset_seriale}`,
    r.ubicazione_codice && `${t('vendite.resi.rientri.in_ubicazione')} ${r.ubicazione_codice}`,
  ].filter(Boolean).join(' · ')
}
</script>

<template>
  <div class="app-voce-merce">
    <div class="app-voce-merce-testa">
      <span>
        <strong>{{ t('vendite.resi.rientri.voce_riga', { nr: voce.riga_nr }) }}</strong>
        · {{ voce.articolo_codice }} — {{ voce.articolo_descrizione }}
        <small v-if="voce.ddt_riga_componente_id" class="app-text-muted">
          ({{ t('vendite.resi.rientri.componente') }})
        </small>
      </span>
      <span class="app-voce-merce-stato">
        <span>{{ t('vendite.resi.rientri.rientrata', {
          rientrata: formatQuantita(rientrata), qta: formatQuantita(qta), uom: voce.uom_codice || '',
        }) }}</span>
        <Tag v-if="voce.automatico" severity="info" :value="t('vendite.resi.rientri.automatico')" />
        <Tag v-else-if="copertura === 'completa'" severity="success" :value="t('vendite.resi.rientri.completo')" />
        <Tag v-else-if="copertura === 'oltre'" severity="danger" :value="t('vendite.resi.rientri.oltre')" />
        <Tag v-else severity="warn" :value="t('vendite.resi.rientri.da_completare')" />
      </span>
    </div>

    <ul v-if="voce.rientri.length" class="app-voce-merce-lista">
      <li v-for="r in voce.rientri" :key="r.id">
        <span>{{ formatQuantita(r.qta) }} {{ voce.uom_codice || '' }}</span>
        <span class="app-text-muted">{{ posizione(r) }}</span>
        <Button v-if="modificabile" :icon="MANAGE_ICONS.DELETE" severity="danger" text rounded
                v-tooltip.bottom="t('vendite.resi.rientri.togli')"
                :aria-label="t('vendite.resi.rientri.togli')"
                :loading="loading" @click="togli(r)" />
      </li>
    </ul>

    <div v-if="canAggiungere" class="app-voce-merce-form">
      <Select v-model="form.ddt_riga_prelievo_id" :options="opzioniOrigine"
              option-label="etichetta" option-value="id"
              :invalid="campiErrati.includes('ddt_riga_prelievo_id')"
              :placeholder="t('vendite.resi.rientri.campo_origine')" />
      <InputNumber v-model="form.qta" :min="0" :max-fraction-digits="QTA_MAX_DECIMALI"
                   :invalid="campiErrati.includes('qta')"
                   :placeholder="t('vendite.resi.rientri.campo_qta')" />
      <Select v-if="conUbicazione" v-model="form.ubicazione_id" :options="ubicazioni.dati.value"
              option-label="codice" option-value="id" filter show-clear
              :loading="ubicazioni.loading.value"
              :placeholder="t('vendite.resi.rientri.campo_ubicazione')" />
      <Button :icon="MANAGE_ICONS.ADD" :label="t('vendite.resi.rientri.aggiungi')"
              class="app-action-btn" :loading="loading" @click="aggiungi" />
    </div>
  </div>
</template>

