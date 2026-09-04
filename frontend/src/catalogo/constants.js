// Costanti frontend per il dominio catalogo.

export const CATALOGO_LOOKUP_RELS = {
  UOM_TIPI: 'catalogo.uom_tipi',
  UNITA_MISURA: 'catalogo.unita_misura',
}

// Schede della vista «Unita' di misura» (2026-09-04, raggruppamento chiesto da
// Tid: unita', conversioni e tipi sono un soggetto solo e stavano su tre voci
// di menu separate).
//
// ⚠️ Sono un CONTRATTO fra file che non si vedono: le rotte di compatibilita'
//    in `router/index.js` producono il deep-link `?tab=`, la vista lo consuma.
//    Scritte come literal, un refuso non fallisce — la vista aprirebbe la
//    scheda di default e il vecchio indirizzo «Tipi UdM» porterebbe in
//    silenzio sulle unita'.
export const UOM_TABS = Object.freeze({
  UNITA: 'unita',
  CONVERSIONI: 'conversioni',
  TIPI: 'tipi',
})
