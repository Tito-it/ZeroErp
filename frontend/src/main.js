import { createApp } from 'vue'
import { createPinia } from 'pinia'
import App from './App.vue'
import router from './router'
import i18n, { loadLocaleMessages, DEFAULT_LOCALE } from './core/i18n'
import { autoResetPlugin } from './core/pinia-plugins/auto-reset'

import PrimeVue from 'primevue/config'
import ToastService from 'primevue/toastservice'
import ConfirmationService from 'primevue/confirmationservice'
import Tooltip from 'primevue/tooltip'
import Aura from '@primeuix/themes/aura'
import 'primeicons/primeicons.css'
import { localeIt } from './core/primevue-locale'
import { installaEscapeSoloInCima } from './core/utils/escapeSoloInCima'
import './assets/theme.css'
import './assets/main.css'
import './assets/auth-pages.css'

const app = createApp(App)

const pinia = createPinia()
pinia.use(autoResetPlugin)
app.use(pinia)
app.use(router)
app.use(PrimeVue, {
  theme: {
    preset: Aura,
    options: {
      darkModeSelector: '.p-dark'
    }
  },
  locale: localeIt,
})
app.use(i18n)
app.use(ToastService)
app.use(ConfirmationService)
app.directive('tooltip', Tooltip)

// ESC chiude solo l'overlay in cima. ⚠️ QUI, prima del mount: i listener su
// `document` si eseguono in ordine di registrazione, e questo deve precedere
// quelli che Drawer e Dialog di PrimeVue agganciano quando si aprono.
installaEscapeSoloInCima()

// Carica la locale attiva (e il fallback, se diverso) PRIMA del mount: le
// traduzioni non sono piu' inline nel bundle, quindi il primo paint deve
// attendere il chunk della locale. Per l'utenza default IT e' un solo
// chunk (~33 KB gzip) e en.json non viene mai scaricato finche' non si
// passa a EN.
async function bootstrap() {
  const active = i18n.global.locale.value
  await loadLocaleMessages(active)
  if (active !== DEFAULT_LOCALE) {
    await loadLocaleMessages(DEFAULT_LOCALE)
  }
  app.mount('#app')
}

bootstrap()
