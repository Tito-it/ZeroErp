// Larghezze drawer per tipologia di form
export const DRAWER_WIDTH = {
  SIMPLE: '480px',    // tabelle di lookup, config
  STANDARD: '640px',  // anagrafiche, catalogo
  COMPLEX: '800px'    // pratiche, contratti
}

// Durata toast in millisecondi
export const TOAST_DURATION = {
  SUCCESS: 3000,
  ERROR: 5000,
  SYSTEM_ERROR: 0  // 0 = persistente, chiusura manuale
}

// Paginazione default
export const PAGINATION = {
  DEFAULT_ROWS: 25,
  ROWS_OPTIONS: [10, 25, 50, 100]
}
