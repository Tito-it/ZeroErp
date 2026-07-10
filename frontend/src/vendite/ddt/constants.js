// Costanti di dominio per i DDT di vendita. Stati interni allineati a
// `config.stati_doc_ddt.codice_interno` (seed). Stessi valori usati dal BE come
// literal in `apps/vendite/services/ddt_service.py`. Mantenere allineato: il BE
// matcha lo `stato_codice_interno` ritornato dalla vista, niente normalizzazione.
// Macchina a stati: DRAFT -> EMESSO -> SPEDITO -> CONSEGNATO (-> RESO) + ANNULLATO.
// Il `numero` e' NULL in DRAFT, assegnato dal trigger DB alla transizione EMESSO.

export const STATO_DDT = Object.freeze({
  DRAFT: 'DRAFT',
  EMESSO: 'EMESSO',
  SPEDITO: 'SPEDITO',
  CONSEGNATO: 'CONSEGNATO',
  RESO: 'RESO',
  ANNULLATO: 'ANNULLATO',
})
