// Istanza i18n centralizzata — importabile da router e altri moduli non-component.
import { createI18n } from 'vue-i18n'
import it from '../locales/it.json'
import en from '../locales/en.json'

const i18n = createI18n({
  legacy: false,
  locale: 'it',
  fallbackLocale: 'en',
  messages: { it, en }
})

export default i18n
