// Scopo: Utility condivisa per determinare il livello di provenienza
// di un parametro risolto e il suo severity badge.
// Riusata da ParameterFallback e ImpostazioniSearchTable.
//
// Cascata di risoluzione (post brief DB 2026-05-19, migration 20260519-01):
//   user > categoria_cliente > group > emittente > default
// Livello "categoria_cliente" attivo solo se il chiamante ha passato
// `categoria_cliente_id` (o `billing_account_id`) all'API /settings/.

const SEVERITY_MAP = {
  user: 'info',
  categoria_cliente: 'warn',
  group: 'warn',
  emittente: 'success',
  default: 'secondary'
}

// Ordine di precedenza esplicito: la prima chiave non-null vince.
// Single source of truth per la cascata visualizzata in UI.
const LEVEL_ORDER = ['user', 'categoria_cliente', 'group', 'emittente']

export function resolveParameterLevel(parameter) {
  for (const level of LEVEL_ORDER) {
    if (parameter[`${level}_value`] != null) return level
  }
  return 'default'
}

export function parameterLevelSeverity(level) {
  return SEVERITY_MAP[level] || 'secondary'
}

// Scopo: la famiglia del parametro (`ammette_override` di
// `fn_list_parameters_for_user`, brief-db-parametri-senza-override). Dove e'
// false il DB rifiuta l'override (`E_PARAMETER_OVERRIDE_NON_AMMESSO`): la UI
// non lo offre. ⚠️ Solo `false` lo esclude: un campo che manca e' un difetto
// del contratto, e il rifiuto resta del DB.
export function ammettePersonalizzazione(parameter) {
  return parameter?.ammette_override !== false
}
