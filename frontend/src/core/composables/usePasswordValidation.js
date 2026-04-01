/**
 * Composable per validazione password client-side.
 * Usato da ChangePasswordView, PasswordResetConfirmView, AttivazioneView.
 * La validazione completa avviene lato backend (4 validator Django).
 */
export function usePasswordValidation() {
  /**
   * Valida password e conferma. Ritorna chiave i18n errore o null se valida.
   * @param {string} password
   * @param {string} confirm
   * @returns {string|null} chiave i18n errore o null
   */
  function validateNewPassword(password, confirm) {
    if (!password || password.length < 8) return 'auth.password_too_short'
    if (password !== confirm) return 'auth.password_mismatch'
    return null
  }

  return { validateNewPassword }
}
