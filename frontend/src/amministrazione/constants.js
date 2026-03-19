// Scopo: costanti e helper del modulo Amm. Software.
// Enum allineati ai valori DB (config.ruolo_sistema, config.livello_accesso).
// Builder opzioni per Select centralizzati (zero duplicazione).

// --- Enum ruolo sistema ---
export const RUOLO_SISTEMA = {
  ADMIN: 'ADMIN',
  OPERATIVO: 'OPERATIVO',
  DISABILITATO: 'DISABILITATO'
}

// --- Enum livello accesso ---
export const LIVELLO_ACCESSO = {
  TUTTO: 'TUTTO',
  LETTURA: 'LETTURA',
  BLOCCATO: 'BLOCCATO'
}

// --- Tipo ruolo per SoggettoResolver ---
export const TIPO_RUOLO_CODICE = {
  RIS_UMANA: 'RIS_UMANA'
}

// Scopo: Costruisce le opzioni ruolo per Select.
// includeAll: aggiunge "Tutti" (per filtri lista) e "Disabilitato" (sola lettura).
export function buildRuoloOptions(t, { includeAll = false } = {}) {
  const opts = [
    { label: t('amm.ruolo_admin'), value: RUOLO_SISTEMA.ADMIN },
    { label: t('amm.ruolo_operativo'), value: RUOLO_SISTEMA.OPERATIVO }
  ]
  if (includeAll) {
    opts.unshift({ label: t('amm.ruolo_all'), value: null })
    opts.push({ label: t('amm.ruolo_disabilitato'), value: RUOLO_SISTEMA.DISABILITATO })
  }
  return opts
}

// Scopo: Costruisce le opzioni livello accesso per Select.
export function buildLivelloOptions(t) {
  return [
    { label: t('amm.livello_tutto'), value: LIVELLO_ACCESSO.TUTTO },
    { label: t('amm.livello_lettura'), value: LIVELLO_ACCESSO.LETTURA },
    { label: t('amm.livello_bloccato'), value: LIVELLO_ACCESSO.BLOCCATO }
  ]
}
