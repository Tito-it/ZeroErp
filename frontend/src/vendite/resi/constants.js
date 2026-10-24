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

// Etichetta NC della coda accrediti (colonna derivata di
// `vw_resi_da_accreditare`, forma contatore): DOVUTA = obbligo (reso a
// credito), FACOLTATIVA = opzione dell'operatore (reso per ri-consegna,
// DL-26). Whitelist speculare a quella BE (`E_RESO_VALIDAZIONE`).
export const ETICHETTA_ACCREDITO = Object.freeze({
  DOVUTA: 'DOVUTA',
  FACOLTATIVA: 'FACOLTATIVA',
})

// Azione di processo che apre le due porte dell'accredito (accredita e
// annulla): stesso codename per le due facce dello stesso atto — due permessi
// distinti si sfilerebbero al primo profilo configurato a mano. Speculare a
// `config.azioni_processo.permission_codename` (id 31).
export const AZIONE_ACCREDITA_RESO = 'accredita_riga_reso'

// Esito del giro massivo di accredito: e' il vocabolario del fan-out del
// backend (`apps/core/services/fan_out.py`), non uno nostro — la severity a
// video si allinea a questi tre e non se ne inventa un quarto.
// ⚠️ NON confondere `ESITO_ACCREDITO.PARZIALE` (una parte delle righe non e'
//    passata) con `STATO_RICONSEGNA.PARZIALE` (copertura ri-consegna a meta'):
//    stessa parola, due domini diversi.
// 📌 Vive qui e non in `core/constants` perche' oggi il report del fan-out lo
//    legge solo questa coda: al secondo dominio che lo legge, si sale.
export const ESITO_ACCREDITO = Object.freeze({
  COMPLETATO: 'COMPLETATO',
  PARZIALE: 'PARZIALE',
  ERRORE: 'ERRORE',
})

// Valori del query param `tab` della vista resi: sono il contratto del
// deep-link (ci arriva il pannello situazione merce), non un dettaglio interno
// della vista — per questo stanno qui e non dentro ResiView.
export const TAB_RESI = Object.freeze({
  LISTA: 'lista',
  DA_ACCREDITARE: 'da-accreditare',
  DA_RICONSEGNARE: 'da-riconsegnare',
})

// Nome della rotta della vista resi (router): lo usa il deep-link dal pannello
// situazione merce.
export const ROUTE_RESI = 'vendite-resi'

// Le colonne della testata che `ResoForm` MOSTRA, per `useTestataDocumento`
// (brief-db-testata-dopo-emissione, R-FE-3): la testata e' modificabile se
// almeno una di queste e' aperta nella capability. ⚠️ Deve dire gli stessi
// campi del form: lo presidia `campiFormTestata.spec.js`, che la confronta
// coi `isLocked('…')` del componente.
export const CAMPI_FORM_TESTATA_RESO = Object.freeze([
  'data',
  'magazzino_id',
])
