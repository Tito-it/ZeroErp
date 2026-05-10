// Scopo: genera Idempotency-Key UUID v4 con fallback per non-secure context.
// `crypto.randomUUID()` richiede secure context (HTTPS o localhost/127.0.0.1):
// in HTTP su IP LAN / hostname custom (setup VSCode SSH + port forward) e' undefined
// e produce TypeError silenzioso se chiamato direttamente. Il fallback usa
// timestamp + Math.random: non e' RFC 4122 ma e' sufficiente come correlation
// id per idempotenza lato BE (chiave opaca, no requisiti crittografici).

// Scopo: ritorna una chiave di idempotenza pronta per header `Idempotency-Key`.
export function generateIdempotencyKey() {
  if (typeof crypto !== 'undefined' && typeof crypto.randomUUID === 'function') {
    return crypto.randomUUID()
  }
  return `${Date.now()}-${Math.random().toString(36).slice(2)}`
}
