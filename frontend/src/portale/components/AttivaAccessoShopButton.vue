<script setup>
// Scopo: Pulsante riusabile "Attiva accesso shop" per il profilo portale
// (§8.6.2 + B1 §13.7). Chiama POST /portale/profile/activate-shop/ che
// post-fix resolver multi-veste e' un endpoint reale: crea l'identita
// SHOP_CUSTOMER sullo stesso soggetto_ruolo + auth_user del portale
// corrente, immediatamente attiva (no email/token).
//
// Idempotente lato BE: il backend distingue:
//   - 200 + `activated: true`       -> appena attivata
//   - 200 + `already_active: true`  -> gia' attiva (nessun side-effect)
// In entrambi i casi mostriamo success al user.
//
// Errori 400 specifici (es. fornitore portale, identita su altro user):
// `E_ATTIVAZIONE_SHOP_CROSS`. Toast severity error con messaggio dal BE.

import { ref } from 'vue'
import { useI18n } from 'vue-i18n'
import Button from 'primevue/button'
import { useNotify } from '../../core/composables/useNotify'
import { extractApiError } from '../../core/utils/apiError'
import { attivaAccessoShop } from '../api/portaleProfileApi'

const { t } = useI18n()
const notify = useNotify()

const loading = ref(false)
const activated = ref(false)

const emit = defineEmits(['activated'])

async function onClick() {
  loading.value = true
  try {
    const res = await attivaAccessoShop()
    const data = res?.data?.data || {}
    // Stesso messaggio per `activated` e `already_active`: dall'UX
    // del cliente non c'e' differenza utile (il risultato finale e'
    // identico). Manteniamo l'`emit('activated', data)` per consentire
    // al genitore di refreshare la sezione "stato accessi".
    activated.value = true
    notify.success(t('portale.profile.activate_shop_success'))
    emit('activated', data)
  } catch (err) {
    notify.error(extractApiError(err) || t('portale.profile.activate_shop_error'))
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
    :disabled="activated"
    severity="info"
    outlined
    @click="onClick"
  />
</template>
