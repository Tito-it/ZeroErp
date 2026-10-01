<script setup>
// Scopo: Profilo portale (§8.6.1). Visualizza i dati base dell'utente
// portale corrente e lo stato dei suoi accessi:
//   - Portale:  sempre ATTIVO (l'utente e' atterrato qui dopo login portale).
//   - Shop:     NON ATTIVO per ora (MVP PR-C), con pulsante di attivazione
//               che oggi chiama lo stub 501 §8.4.3.
//
// Nota: il namespace guard del router garantisce che solo vesti
// CLIENTE_PORTALE/FORNITORE_PORTALE raggiungano questa rotta.
//
// Building block riusati:
//   - useAuthStore: `displayName`, `ruoloApplicativo`, `user`
//   - AttivaAccessoShopButton: orchestrazione stub activate-shop
//   - Tag (PrimeVue) per badge stato

import { computed } from 'vue'
import { useI18n } from 'vue-i18n'
import Card from 'primevue/card'
import AttivoTag from '../../core/components/AttivoTag.vue'
import { useAuthStore } from '../../stores/auth'
import AttivaAccessoShopButton from '../components/AttivaAccessoShopButton.vue'
import { etichettaRuoloApplicativo } from '../../core/utils/i18nLabel'

const { t, te } = useI18n()
const auth = useAuthStore()

const emailAccount = computed(() => auth.user?.utente?.email || '')
const username = computed(() => auth.user?.utente?.username || '')
const ruoloLabel = computed(() => etichettaRuoloApplicativo(t, te, auth.ruoloApplicativo))

// Lista righe "stato accessi" per la card Accessi. Usare un array reso
// il template v-for-friendly ed elimina duplicazione visuale.
// - portale: ATTIVO per costruzione (siamo loggati come portale user).
// - shop:    NON ATTIVO per ora — il /me/ espone solo la veste del JWT
//            corrente (§8.3.6), quindi non possiamo scoprire una eventuale
//            veste SHOP_CUSTOMER secondaria finche' PR-C non aggiunge
//            l'elenco "vesti" al profilo. Flag hardcoded temporaneo.
const accessi = computed(() => [
  {
    key: 'portale',
    labelKey: 'portale.profile.accesso_portale',
    attivo: true
  },
  {
    key: 'shop',
    labelKey: 'portale.profile.accesso_shop',
    attivo: false
  }
])

const shopAttivo = computed(
  () => accessi.value.find(a => a.key === 'shop')?.attivo === true
)
</script>

<template>
  <div class="portale-profile">
    <h1 class="portale-profile__title">{{ t('portale.profile.title') }}</h1>

    <Card class="portale-profile__card">
      <template #title>{{ t('portale.profile.anagrafica_title') }}</template>
      <template #content>
        <dl class="portale-profile__dl">
          <dt>{{ t('portale.profile.nome') }}</dt>
          <dd>{{ auth.displayName || '—' }}</dd>

          <dt>{{ t('portale.profile.username') }}</dt>
          <dd>{{ username || '—' }}</dd>

          <dt>{{ t('portale.profile.email') }}</dt>
          <dd>{{ emailAccount || '—' }}</dd>

          <dt>{{ t('portale.profile.ruolo') }}</dt>
          <dd>{{ ruoloLabel }}</dd>
        </dl>
      </template>
    </Card>

    <Card class="portale-profile__card">
      <template #title>{{ t('portale.profile.accessi_title') }}</template>
      <template #content>
        <div
          v-for="row in accessi"
          :key="row.key"
          class="portale-profile__accesso"
        >
          <span class="portale-profile__accesso-label">
            {{ t(row.labelKey) }}
          </span>
          <AttivoTag
            :active="row.attivo"
            :active-label="t('portale.profile.stato_attivo')"
            :inactive-label="t('portale.profile.stato_non_attivo')"
            inactive-severity="secondary"
          />
        </div>

        <div v-if="!shopAttivo" class="portale-profile__actions">
          <AttivaAccessoShopButton />
          <p class="portale-profile__hint">
            {{ t('portale.profile.activate_shop_hint') }}
          </p>
        </div>
      </template>
    </Card>
  </div>
</template>

<style scoped>
.portale-profile {
  display: flex;
  flex-direction: column;
  gap: 1rem;
  max-width: 680px;
  margin: 0 auto;
  padding: 1rem;
}

.portale-profile__title {
  font-size: 1.3rem;
  font-weight: 600;
  margin: 0 0 0.25rem;
}

.portale-profile__card {
  width: 100%;
}

.portale-profile__dl {
  display: grid;
  grid-template-columns: max-content 1fr;
  gap: 0.35rem 1rem;
  margin: 0;
}

.portale-profile__dl dt {
  font-weight: 600;
  color: var(--app-text-muted, inherit);
}

.portale-profile__dl dd {
  margin: 0;
}

.portale-profile__accesso {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  padding: 0.25rem 0;
}

.portale-profile__accesso-label {
  min-width: 150px;
  font-weight: 500;
}

.portale-profile__actions {
  margin-top: 1rem;
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
}

.portale-profile__hint {
  margin: 0;
  font-size: var(--app-font-size-sm, 0.85rem);
  color: var(--app-text-muted, inherit);
}
</style>
