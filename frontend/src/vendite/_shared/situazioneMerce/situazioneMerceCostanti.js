// Costanti del pannello «situazione merce». Il vocabolario di `stato` vive a
// DB (`vw_situazione_merce_ordine` / `vw_partite_merce`, brief partita §9.3):
// qui il suo mirror FE, per la stessa ragione di `STATO_RESO` in
// `resi/constants.js` e degli enum di frontend-standards — un typo in un
// literal (`'DA_FATURARE'`) non rompe niente a runtime: filtra zero righe e il
// riassunto mente in silenzio. L'enum lo rende un errore che si vede.
//
// ⚠️ Il frontend USA questi codici per scegliere frase e colore, mai per
// ri-derivare il verso del saldo (richiesta BE-2): se il DB aggiunge un valore,
// qui si aggiunge una riga — non una regola.

import { SORGENTE_CODES } from '../../../documenti/constants'

export const STATO_MERCE = Object.freeze({
  PAREGGIATA: 'PAREGGIATA',
  DA_FATTURARE: 'DA_FATTURARE',
  DA_ACCREDITARE: 'DA_ACCREDITARE',
  NON_SPEDITA: 'NON_SPEDITA',        // livello ordine: impegnata ma mai spedita
  NON_IMPEGNATA: 'NON_IMPEGNATA',    // livello ordine: ordine sotto soglia CONFERMATO
                                     // o abortito -> `da_spedire` e' NULL (20260818-06)
  NON_FATTURABILE: 'NON_FATTURABILE',
  NON_MISURABILE: 'NON_MISURABILE',
  RICONSEGNA: 'RICONSEGNA',          // solo partite (riga di un DDT di ri-consegna)
})

// Etichetta della coda accrediti (`vw_resi_da_accreditare.etichetta`):
// DOVUTA = obbligo (reso a credito), FACOLTATIVA = opzione dell'operatore
// (reso per ri-consegna, DL-26). Mirror della whitelist BE/DB, gia' speculare
// in `resi/constants.js` (ETICHETTA_ACCREDITO) — qui ri-esposta per non
// importare dal dominio resi dentro un BB `_shared`.
export const ETICHETTA_ACCREDITO_MERCE = Object.freeze({
  DOVUTA: 'DOVUTA',
  FACOLTATIVA: 'FACOLTATIVA',
})

// Il CONTESTO del pannello, dichiarato dal backend (`sezioni.contesto`): dice
// QUALE delle due liste e' il saldo di questo documento.
// ⭐ Dal 2026-08-19 il payload porta `righe_ordine` su ENTRAMBI i lati (il
// pannello mostra sempre i due livelli, rilievo in-app di Tid), quindi il
// contesto NON si puo' piu' dedurre dal fatto che una lista sia vuota. Se lo si
// deducesse male, sul DDT si conterebbe il saldo dell'INTERA riga d'ordine —
// tutte le sue spedizioni — al posto di questa: un numero plausibile e sbagliato.
// ⭐ I valori sono i codici di `config.sorgenti` (dal 2026-10-19,
// brief-db-grammatica-unica-documenti lotto 2a: una grammatica sola per i tipi
// di documento), quindi si leggono da `SORGENTE_CODES` e non si riscrivono.
export const CONTESTO_MERCE = Object.freeze({
  ORDINE: SORGENTE_CODES.ORDINE_VENDITA,
  DDT: SORGENTE_CODES.DDT_VENDITA,
})
