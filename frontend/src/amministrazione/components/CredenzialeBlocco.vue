<!--
  SPDX-License-Identifier: GPL-3.0-or-later
  Copyright (C) 2026 Tid (Michele Carlo Titini)
-->
<script setup>
// Scopo: Il blocco dell'amministratore su una CREDENZIALE (brief-db-be-fe-area-
//        accessi, A-4/A-5; piano accessi L-2): lo stato — bloccata il, da chi,
//        perche' — e i due gesti, «Blocca accesso» col motivo e «Sblocca».
// Note: Il blocco vale su tutte le porte (gestionale, portale, shop), non scade
//       e il reset della password non lo toglie; bloccare chiude anche tutte le
//       sessioni aperte. Lo monta `CredenzialeAzioni`, nei drawer dell'operatore
//       e degli altri accessi.
//       ⭐ «Blocca» spento col motivo sull'ultimo SUPER_ADMIN raggiungibile: la
//       capability (`can_block` + `block_reason_key`) arriva dal backend, che la
//       legge dal predicato del DB — il guard lo rifiuterebbe comunque.
//       Permesso ⇒ nascondi: in sola lettura i due gesti non ci sono.
import { computed, ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import Button from 'primevue/button'
import InputText from 'primevue/inputtext'
import Tag from 'primevue/tag'
import AppDialog from '../../core/components/AppDialog.vue'
import { useApiHandler } from '../../core/composables/useApiHandler'
import { useConfirmAction } from '../../core/composables/useConfirmAction'
import { MANAGE_ICONS } from '../../core/constants'
import { displayTimestamp } from '../../core/utils/date'
import { labelOrCode } from '../../core/utils/i18nLabel'
import { bloccaCredenziale, getCredenziale, sbloccaCredenziale } from '../api/amministrazione'

const props = defineProps({
  authUserId: { type: Number, required: true },
  readonly: { type: Boolean, default: false },
})
// `changed`: lo stato della credenziale e' cambiato, la lista dietro e' stantia.
const emit = defineEmits(['changed'])

const { t, te } = useI18n()
const { execute, loading, campiErrati } = useApiHandler()
const { confirmAction } = useConfirmAction()

const cred = ref(null)
const dialogVisibile = ref(false)
const motivo = ref('')

const motivoSpento = computed(() =>
  cred.value && !cred.value.can_block
    ? labelOrCode(t, te, cred.value.block_reason_key, cred.value.block_reason)
    : ''
)

async function carica() {
  const id = props.authUserId
  cred.value = null
  const res = await execute(() => getCredenziale(id))
  // Una risposta arrivata dopo il cambio di credenziale non e' la sua.
  if (res && id === props.authUserId) cred.value = res
}

watch(() => props.authUserId, (id) => { if (id) carica() }, { immediate: true })

function apriBlocca() {
  motivo.value = ''
  dialogVisibile.value = true
}

async function confermaBlocca() {
  const res = await execute(
    () => bloccaCredenziale(props.authUserId, motivo.value),
    { successMessage: t('amministrazione.accessi.bloccata_ok') }
  )
  if (res) {
    cred.value = res
    dialogVisibile.value = false
    emit('changed')
  }
}

function chiediSblocca() {
  confirmAction({
    header: t('amministrazione.accessi.sblocca'),
    message: t('amministrazione.accessi.sblocca_conferma'),
    onAccept: async () => {
      const res = await execute(
        () => sbloccaCredenziale(props.authUserId),
        { successMessage: t('amministrazione.accessi.sbloccata_ok') }
      )
      if (res) {
        cred.value = res
        emit('changed')
      }
    },
  })
}
</script>

<template>
  <div v-if="cred" class="form-field">
    <label>{{ t('amministrazione.accessi.blocco_titolo') }}</label>
    <div class="app-form-inline-toggle">
      <Tag
        :value="cred.bloccata ? t('amministrazione.accessi.bloccata') : t('amministrazione.accessi.non_bloccata')"
        :severity="cred.bloccata ? 'danger' : 'success'"
      />
      <small v-if="cred.bloccata" class="app-field-hint">
        {{ t('amministrazione.accessi.bloccata_dettaglio', {
          quando: displayTimestamp(cred.bloccata_dal),
          chi: cred.bloccata_da || '—',
          motivo: cred.motivo_blocco || '—',
        }) }}
      </small>
    </div>

    <div v-if="!readonly">
      <Button
        v-if="cred.bloccata"
        :label="t('amministrazione.accessi.sblocca')"
        :icon="MANAGE_ICONS.SBLOCCA"
        outlined size="small"
        :loading="loading"
        @click="chiediSblocca"
      />
      <!-- Il tooltip sull'involucro: un `<button disabled>` non emette eventi
           del mouse (frontend-standards, «Il tooltip di un pulsante che puo'
           essere DISABILITATO va sull'involucro»). -->
      <span v-else v-tooltip.top="motivoSpento" class="app-action-tooltip-wrap">
        <Button
          :label="t('amministrazione.accessi.blocca')"
          :icon="MANAGE_ICONS.BLOCCA_ACCESSO"
          severity="danger"
          outlined size="small"
          :disabled="!cred.can_block || loading"
          @click="apriBlocca"
        />
      </span>
    </div>

    <AppDialog
      v-model:visible="dialogVisibile"
      :header="t('amministrazione.accessi.blocca')"
      width="sm"
      :loading="loading"
      :save-disabled="!motivo.trim()"
      :save-label="t('amministrazione.accessi.blocca')"
      save-severity="danger"
      @save="confermaBlocca"
      @cancel="dialogVisibile = false"
    >
      <p>{{ t('amministrazione.accessi.blocca_spiegazione') }}</p>
      <div class="form-field">
        <label for="motivo-blocco">{{ t('amministrazione.accessi.motivo_blocco') }} *</label>
        <InputText
          id="motivo-blocco"
          v-model="motivo"
          :invalid="campiErrati.includes('motivo')"
          fluid
        />
      </div>
    </AppDialog>
  </div>
</template>
