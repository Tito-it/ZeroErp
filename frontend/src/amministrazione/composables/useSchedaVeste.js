// ------------------------------------------------------------
// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Tid (Michele Carlo Titini)
// Doc: JavaScript
// Scopo: Da una VESTE della lista «Altri accessi» alla scheda del soggetto che
//        la governa (brief-db-be-fe-area-accessi, A-4): le vesti cliente e
//        fornitore si invitano, reinviano e disattivano dalla loro scheda in
//        anagrafiche, non dall'amministrazione.
// Note: ⭐ Regola in un posto solo: la usano il kebab della riga e il drawer.
//       ⚠️ `cliente_ids` e' un ARRAY (§7.4 del brief: un soggetto_ruolo puo'
//       avere piu' schede cliente, una per istanza utility). Decisione presa
//       qui: con UNA si apre quella scheda; con piu' d'una (o nessuna) si apre
//       la scheda del SOGGETTO, che le elenca tutte — scegliere un id sarebbe
//       scegliere a caso.
//       Si arriva come dalla ricerca universale: contesto globale + rotta
//       della lista, e la vista apre il drawer dal contesto
//       (frontend-standards §«Ricerca universale → lista filtrata»).
// ------------------------------------------------------------
import { useRouter } from 'vue-router'
import { TIPO_RUOLO } from '../../core/constants'
import { rottaListaTipoRuolo } from '../../core/navigation'
import { useContextStore } from '../../stores/context'

// Scopo: la destinazione di una veste — `{ rotta, tipoRuolo, entitaId }` —
//        o `null` se la veste non ha un soggetto da aprire.
export function destinazioneVeste(veste) {
  if (!veste?.soggetto_id) return null
  const clienti = veste.cliente_ids || []
  if (clienti.length === 1) {
    return { rotta: rottaListaTipoRuolo(TIPO_RUOLO.CLIENTE), tipoRuolo: TIPO_RUOLO.CLIENTE, entitaId: clienti[0] }
  }
  if (veste.fornitore_id) {
    return { rotta: rottaListaTipoRuolo(TIPO_RUOLO.FORNITORE), tipoRuolo: TIPO_RUOLO.FORNITORE, entitaId: veste.fornitore_id }
  }
  return { rotta: rottaListaTipoRuolo(null), tipoRuolo: null, entitaId: null }
}

export function useSchedaVeste() {
  const router = useRouter()
  const ctx = useContextStore()

  // Scopo: apre la scheda del soggetto della veste (cliente, fornitore o
  //        soggetto), impostando il contesto che la lista d'arrivo legge.
  function apriSchedaVeste(veste) {
    const dest = destinazioneVeste(veste)
    if (!dest) return
    ctx.setContext({
      tipo_ruolo_codice: dest.tipoRuolo,
      soggetto_id: veste.soggetto_id,
      soggetto_ruolo_id: veste.soggetto_ruolo_id,
      entita_id: dest.entitaId,
      label: veste.soggetto || '',
    })
    router.push({ name: dest.rotta })
  }

  return { apriSchedaVeste }
}
