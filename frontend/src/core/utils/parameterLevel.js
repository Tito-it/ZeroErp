// Scopo: Utility condivisa per determinare il livello di provenienza
// di un parametro risolto e il suo severity badge.
// Riusata da ParameterFallback e ImpostazioniSearchTable.

const SEVERITY_MAP = {
  user: 'info',
  group: 'warn',
  emittente: 'success',
  default: 'secondary'
}

export function resolveParameterLevel(parameter) {
  if (parameter.user_value != null) return 'user'
  if (parameter.group_value != null) return 'group'
  if (parameter.emittente_value != null) return 'emittente'
  return 'default'
}

export function parameterLevelSeverity(level) {
  return SEVERITY_MAP[level] || 'secondary'
}
