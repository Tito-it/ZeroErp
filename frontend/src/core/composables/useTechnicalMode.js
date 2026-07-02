// Modalita' tecnica (diagnostica super-admin) per le viste runtime delle pratiche.
// Mirror di useReadonlyMode: provider/consumer via provide/inject.
//
// Quando attiva, le viste operatore (PraticaPercorso, FlussoDrawer) ri-espongono
// il "plumbing" del motore — codici, sequenza, stati-macchina, rami — che di
// norma resta nascosto (vista-racconto). E' opt-in e gateata a RUOLO_SISTEMA.ADMIN;
// il default per l'operatore e' sempre spento.
//
// Le viste consumano SOLO il flag: `useInjectTechnicalMode()` → ref(false) di
// default, cosi' dove nessun provider e' montato la vista e' quella operatore.
// Il provider + toggle ADMIN (auth.isSuperAdmin) sono montati in PraticheDashboard.

import { provide, inject, ref } from 'vue'

export const TECHNICAL_KEY = Symbol('appTechnicalMode')

// Provider: condivide ai figli un ref booleano controllato dal chiamante
// (il toggle super-admin, B5). Ritorna il ref per comodita'.
export function provideTechnicalMode(tecnicoRef) {
  provide(TECHNICAL_KEY, tecnicoRef)
  return tecnicoRef
}

// Consumer: default false se nessun provider nell'albero (= vista operatore).
export function useInjectTechnicalMode() {
  return inject(TECHNICAL_KEY, ref(false))
}
