<script setup>
// Scopo: Pulsante riusabile "Attiva accesso shop" per il profilo portale
// (§8.6.2). Chiama POST /portale/profile/activate-shop/ e gestisce la
// risposta 501 `E_SHOP_NON_DISPONIBILE` come messaggio INFORMATIVO (non
// come errore): UX coerente con il fatto che la funzione arrivera' con
// PR-C. Quando PR-C sbloccherà l'MVP l'endpoint rispondera' 200 e il
// ramo success mostrera' "attivazione avviata, controlla la tua email".
//
// Chiamata diretta (non `useApiHandler.execute`) perche' serve distinguere
// 501 "feature not available" dagli altri errori. Il toast di errore
// automatico di useApiHandler ci darebbe severity error — inappropriato
// per un feature flag noto.

import { ref } from 'vue'
import { useI18n } from 'vue-i18n'
import Button from 'primevue/button'
import { useNotify } from '../../core/composables/useNotify'
import { extractApiError, extractApiErrorCode } from '../../core/utils/apiError'
import { attivaAccessoShop } from '../api/portaleProfileApi'

const { t } = useI18n()
const notify = useNotify()

const loading = ref(false)

// Codice errore dello stub PR-B: risposta 501 dal BE. Stringa condivisa
// con error_policies.py lato BE (§8.4.3). Quando PR-C lo rimuovera',
// anche questo ramo diventera' dead code da rimuovere.
const CODE_NOT_AVAILABLE = 'E_SHOP_NON_DISPONIBILE'

async function onClick() {
  loading.value = true
  try {
    await attivaAccessoShop()
    notify.success(t('portale.profile.activate_shop_success'))
  } catch (err) {
    const code = extractApiErrorCode(err)
    if (code === CODE_NOT_AVAILABLE) {
      // Feature flag: lo trattiamo come info, non errore.
      notify.warn(t('portale.profile.activate_shop_coming_soon'))
    } else {
      notify.error(extractApiError(err) || t('portale.profile.activate_shop_error'))
    }
  } finally {
    loading.value = false
  }
}
</script>

<template>
  <Button
    :label="t('portale.profile.activate_shop_btn')"
    icon="pi pi-shopping-bag"
    :loading="loading"
    severity="info"
    outlined
    @click="onClick"
  />
</template>
