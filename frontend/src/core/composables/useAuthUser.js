// Scopo: Composable per gestire i campi auth (username, email, password)
// di un nuovo utente. Validazione password match inclusa.

import { reactive, computed } from 'vue'
import { isEmailValid } from '../utils/validators'

// `conPassword: false` quando la password non la sceglie chi compila il form
// (operatore: la sceglie la persona attivando l'invito, regola unica L-3).
export function useAuthUser({ conPassword = true } = {}) {
  const form = reactive({
    username: '',
    email: '',
    password: '',
    password_confirm: ''
  })

  const passwordMatch = computed(
    () => !form.password || form.password === form.password_confirm
  )

  function validate() {
    const errors = []
    if (!form.username.trim()) errors.push('username')
    if (!form.email.trim()) errors.push('email')
    else if (!isEmailValid(form.email)) errors.push('email_format')
    if (conPassword) {
      if (!form.password) errors.push('password')
      if (!passwordMatch.value) errors.push('password_confirm')
    }
    return errors
  }

  function reset() {
    form.username = ''
    form.email = ''
    form.password = ''
    form.password_confirm = ''
  }

  return { form, passwordMatch, validate, reset }
}
