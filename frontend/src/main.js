import { createApp } from 'vue'
import { createPinia } from 'pinia'
import { createI18n } from 'vue-i18n'
import App from './App.vue'
import router from './router'

import PrimeVue from 'primevue/config'
import Aura from '@primeuix/themes/aura'
import 'primeicons/primeicons.css'

import it from './locales/it.json'
import en from './locales/en.json'

const i18n = createI18n({
  legacy: false,
  locale: 'it',
  fallbackLocale: 'en',
  messages: { it, en }
})

const app = createApp(App)

app.use(createPinia())
app.use(router)
app.use(PrimeVue, {
  theme: {
    preset: Aura
  }
})
app.use(i18n)

app.mount('#app')
