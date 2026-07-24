// Scopo: primo caricamento + freshness per i contenuti dentro <Tabs lazy>
//        sotto KeepAlive (estratto alla 3ª copia, regola del 2:
//        CodaLavoriTab, CodaStampaTab, CodaWorkerStato).
//
// Il problema che risolve (pattern documentato in frontend-standards §Tab-View):
// con `lazy` ogni attivazione del tab è un MOUNT, quindi il primo popolamento
// deve vivere in onMounted — il solo onActivated lascerebbe il tab vuoto al
// cambio tab (l'hook `activated` di un discendente montato DOPO l'attivazione
// della rotta scatta solo alla riattivazione KeepAlive successiva).
// onActivated resta per il rientro rotta; al mount iniziale della rotta
// scatterebbero ENTRAMBI → il flag scarta il doppione (mounted e activated
// girano nello stesso flush, PRIMA della nextTick).
import { nextTick, onActivated, onMounted } from 'vue'

// Scopo: registra il caricamento su mount + riattivazione senza doppio fetch
//        iniziale. Da chiamare in setup (registra hook del ciclo di vita).
export function useLazyTabLoad(load) {
  let primedByMount = false
  onMounted(() => {
    primedByMount = true
    load()
    nextTick(() => { primedByMount = false })
  })
  onActivated(() => {
    if (primedByMount) return
    load()
  })
}
