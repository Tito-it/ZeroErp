// Scopo: single source of truth dei livelli della coda lavoro operatore.
// Mappa 1:1 la policy reparto-first dell'assegnazione flusso. Condivisa da
// PraticheCodaLavoro (sezioni espanse) e MieAttivitaPanel (contatori collassati)
// → ordine, label i18n e severity restano coerenti tra le due viste.
//
// Ordine canonico (brief-design-coda-lavoro-mie-attivita §1/§6):
// ASSEGNATO → REPARTO → LIBERO → COMPETENZA (avanzato/opzionale, per ultimo).
export const CODA_LAVORO_LIVELLI = [
  { key: 'ASSEGNATO', labelKey: 'pratiche.coda_assegnati', severity: 'danger' },
  { key: 'REPARTO', labelKey: 'pratiche.coda_reparto', severity: 'secondary' },
  { key: 'LIBERO', labelKey: 'pratiche.coda_libero', severity: 'info' },
  { key: 'COMPETENZA', labelKey: 'pratiche.coda_competenza', severity: 'warn' },
]

// Livelli per cui il flusso e' non assegnato e prendibile dall'operatore
// (coerente con la policy DB fn_prendi_in_carico_flusso): COMPETENZA (skill),
// REPARTO (membro del reparto), LIBERO (presa libera).
export const CODA_LAVORO_PRENDIBILI = ['COMPETENZA', 'REPARTO', 'LIBERO']
