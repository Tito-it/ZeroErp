// Scopo: Fetch di testata dei cruscotti (riepilogo/aggregata) con guard di
//        versione anti-race: scarta la risposta se nel frattempo e' partito
//        un refresh piu' nuovo (vince l'ultima richiesta, non l'ultima
//        risposta arrivata). Estratto 2026-07-07 (regola del 2, ok Tid):
//        unifica il blocco tag/isCurrent duplicato negli store
//        dashboardBacklog, dashboardAperto e dashboardCompetenza.
//        Complementare a usePagedDashFetch (che copre le sezioni paginate).
import { useFetchVersion } from './useFetchVersion'

// Scopo: crea l'action di fetch guardata per una sezione di testata.
// - fetchFn: (...args) => Promise (axios); gli argomenti di fetchRiepilogo
//   vengono inoltrati (es. anno).
// - onData: (data) => void — riceve l'envelope `data` gia' unwrappato
//   (res.data.data, {} se assente) e applica i campi allo stato del caller.
// Ritorna { fetchRiepilogo, invalidate }: invalidate() scarta le fetch in
// volo senza emetterne di nuove (reset/logout).
export function useDashRiepilogo(fetchFn, onData) {
  const fv = useFetchVersion()

  async function fetchRiepilogo(...args) {
    const t = fv.tag()
    const res = await fetchFn(...args)
    if (!fv.isCurrent(t)) return
    onData(res.data?.data ?? {})
  }

  return { fetchRiepilogo, invalidate: fv.invalidate }
}
