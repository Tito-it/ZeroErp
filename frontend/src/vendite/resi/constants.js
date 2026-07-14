// Costanti di dominio per i resi di vendita. Stati interni allineati a
// `config.stati_doc_reso.codice_interno` (seed). Macchina a stati:
// DRAFT -> CONFERMATO (+ ANNULLATO). Il `numero` e' NULL in DRAFT, assegnato
// dal trigger DB alla CONFERMA. Conferma e annullo passano SEMPRE dagli
// endpoint dedicati (fn madri DB con effetti: residuo/proiezioni/flip DDT),
// mai da un cambio stato generico.

export const STATO_RESO = Object.freeze({
  DRAFT: 'DRAFT',
  CONFERMATO: 'CONFERMATO',
  ANNULLATO: 'ANNULLATO',
})

// Stato ri-consegna della riga reso: DERIVATO dalla copertura del ponte
// `resi_righe_riconsegne` (nessuna colonna fisica, R1 brief DB).
export const STATO_RICONSEGNA = Object.freeze({
  DA_RICONSEGNARE: 'DA_RICONSEGNARE',
  PARZIALE: 'PARZIALE',
  COMPLETATA: 'COMPLETATA',
})

// Codici interni `config.tipi_reso` (il flag operativo `riapre_residuo`
// arriva dal BE per riga: questi servono solo per i default UI).
export const TIPO_RESO = Object.freeze({
  A_CREDITO: 'RESO_A_CREDITO',
  PER_RICONSEGNA: 'RESO_PER_RICONSEGNA',
})
