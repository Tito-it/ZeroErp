// Helper centralizzato per la classe CSS delle voci nei popup kebab
// (RowActionsMenu e PageActionsBar). Mappa la severity dell'azione
// (`danger` / `primary` / `warn` / `info` / `success` / undefined) sulla
// classe `.app-menu-item-*` corrispondente, in modo che il colore dell'icona
// nel kebab rispecchi quello del pulsante inline equivalente.
//
// I CSS sono in src/assets/main.css (sezione "Voci menu kebab"). Per cambiare
// la palette di un livello, modificare li' le `--app-btn-*` o `--p-*`.

const SEVERITY_TO_MENU_CLASS = {
  danger: 'app-menu-item-danger',
  warn: 'app-menu-item-warn',
  // primary/success = azione positiva (verde, come app-action-btn).
  primary: 'app-menu-item-action',
  success: 'app-menu-item-action',
  // info = gestione neutra (blu, come app-manage-btn).
  info: 'app-menu-item-manage',
}

// Scopo: classe CSS della voce menu per una determinata severity.
// Quando l'azione non ha severity (caso piu' comune in RowActionsMenu),
// si applica `fallback`. Il chiamante sceglie il fallback in base al
// proprio default inline (manage=blu per RowActionsMenu, action=verde
// per PageActionsBar).
export function menuItemClass(severity, fallback = 'app-menu-item-manage') {
  return SEVERITY_TO_MENU_CLASS[severity] || fallback
}
