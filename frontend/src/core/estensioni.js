// ------------------------------------------------------------
// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Tid (Michele Carlo Titini)
// Doc: JavaScript
// Scopo: ⭐ I PUNTI DI ESTENSIONE DELLE SCHERMATE — dove un dominio A VALLE
//        aggiunge qualcosa alla schermata di un'entita' A MONTE senza che
//        quella lo nomini (decisione Tid, 2026-09-26, frontend-standards
//        §«Confini fra domini»).
//
//        Il verso lo da' il modello: `magazzino.lotti` punta a
//        `catalogo.articoli`, quindi la scheda articolo NON importa
//        magazzino — offre un punto, e magazzino ci contribuisce la sezione
//        «Lotti» dal suo `iscrizioni.js`.
//
//        Due forme di contributo:
//          · COMPONENTE (sezioni di drawer, badge): `{ chiave, ordine?,
//            componente: () => import(...) }`. Lo monta `<PuntoEstensione>`,
//            che gli passa tutte le prop ricevute: il contributo decide da se'
//            se mostrarsi.
//          · AZIONE DI RIGA (kebab di una lista): `{ chiave, ordine?, label
//            (chiave i18n), icon, visibile?(riga), disabilitato?(riga),
//            tooltip? (chiave i18n), action? (permesso di processo),
//            severity?, allowWhenInactive?, drawer: () => import(...),
//            props(riga, { t }) }`. La costruisce e la apre
//            `useAzioniEstese` + `<EstensioneDrawerHost>`.
//
// ⛔ I NOMI dei punti stanno qui e non si scrivono come literal: un refuso
//    nel nome e' un contributo che non compare, senza nessun errore.
// ------------------------------------------------------------
import { creaPuntiEstensione } from './registri'

export const PUNTI_ESTENSIONE = Object.freeze({
  // Scheda articolo (catalogo): sezioni in fondo al drawer, in modifica.
  ARTICOLO_DRAWER_SEZIONI: 'articolo.drawer.sezioni',
  // Lista articoli (catalogo): voci del kebab di riga.
  ARTICOLO_AZIONI_RIGA: 'articolo.azioni-riga',
  // Lista clienti (anagrafiche): voci del kebab di riga.
  CLIENTE_AZIONI_RIGA: 'cliente.azioni-riga',
  // Anteprima del soggetto (anagrafiche): badge accanto a indirizzi/conti/contatti.
  SOGGETTO_ANTEPRIMA_BADGE: 'soggetto.anteprima.badge',
  // Drawer della fattura (vendite): sezioni in testa alla scheda «Documento».
  FATTURA_DRAWER_SEZIONI: 'fattura.drawer.sezioni',
})

const punti = creaPuntiEstensione('schermate')

// Scopo: un dominio contribuisce a un punto (dal suo `iscrizioni.js`).
export function contribuisci(punto, contributo) {
  if (!Object.values(PUNTI_ESTENSIONE).includes(punto)) {
    throw new Error(`Punto di estensione sconosciuto: «${punto}»`)
  }
  punti.contribuisci(punto, contributo)
}

// Scopo: i contributi di un punto, in ordine.
export function contributi(punto) {
  return punti.contributi(punto)
}

// Scopo: avvia il caricamento dei componenti contribuiti a un punto, senza
//        montarli. Lo chiama il componente che OSPITA il punto, nel suo setup:
//        il drawer ospite monta il contenuto solo a fine animazione
//        (`useDrawerContentReady`), e se il chunk del contributo partisse solo
//        allora la sezione comparirebbe DOPO il resto, spingendolo in basso —
//        il rimbalzo che `contentReady` esiste per evitare. Precaricato durante
//        l'animazione, a `contentReady` il modulo e' gia' in cache.
// Note: un `import()` ripetuto non riscarica niente; un errore qui non si
//       propaga (lo riporta `<PuntoEstensione>` quando prova a montarlo).
export function precaricaPunto(punto) {
  for (const c of contributi(punto)) {
    if (c.componente) c.componente().catch(() => {})
  }
}
