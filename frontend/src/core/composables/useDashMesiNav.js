// Scopo: Navigazione anno/mese dei cruscotti fatturazione (pannello 12 mesi +
//        stepper compatto): nomi mese localizzati, selezione mese, cambio
//        anno con clamp sul range accettato dal BE e passo mese ±1 con
//        scavalcamento d'anno. Espone `competenzaCorrente` derivata da
//        (anno, meseIdx) — MAI dall'array dati (che durante un cambio anno
//        contiene ancora l'anno vecchio): le fetch di drill-down restano
//        agganciate al mese che l'utente vede (race-free).
//        Estratto 2026-07-06 (regola del 2, ok Tid) dal telaio comune di
//        DashboardFatturazioneView (ritirata, Fase 3) e
//        DashboardCompetenzaView — oggi unico consumer.
import { computed } from 'vue'
import { useI18n } from 'vue-i18n'
import { nomiMesi as nomiMesiDi } from '../utils/date'

// Range anni accettato dai service dashboard BE (fn_dash_*_mensile):
// clamp locale per non desincronizzare header (anno gia' cambiato) e dati
// (fetch respinta 400).
export const DASH_ANNO_MIN = 2000
export const DASH_ANNO_MAX = 2100

// Scopo: crea la navigazione mesi sopra i ref di store (anno, meseIdx).
// - onMeseChange: reset del drill-down (chiamato a ogni selezione/cambio).
// - onAnnoChange: ricarica dell'aggregata annuale.
// Ritorna { nomiMesi, competenzaCorrente, selezionaMese, cambiaAnno, stepMese }.
export function useDashMesiNav({ anno, meseIdx, onMeseChange, onAnnoChange }) {
  const { locale } = useI18n()

  // Nomi mese localizzati: dal BB `nomiMesi` di `core/utils/date`.
  const nomiMesi = computed(() => nomiMesiDi(locale.value))

  const competenzaCorrente = computed(
    () => `${anno.value}-${String(meseIdx.value + 1).padStart(2, '0')}-01`
  )

  // Scopo: seleziona un mese del pannello 12 mesi.
  //
  // 🔴 RI-CLICCARE IL MESE GIA' SELEZIONATO NON E' UN CAMBIO, e prima lo era.
  //    `meseIdx.value = idx` con lo STESSO valore non fa scattare niente in
  //    Vue — `competenzaCorrente` non cambia, e i watch agganciati a lei
  //    restano fermi — ma `onMeseChange` veniva chiamato lo stesso. Quel
  //    callback AZZERA drill-down ed errori: risultato, il secondo click sullo
  //    stesso mese svuotava le liste e **niente le ricaricava**, perche' il
  //    watch che le ripopola non era scattato.
  //    Difetto visto in app da Tid il 2026-08-24 sul pannello errori: «clicco
  //    agosto, la prima volta mostra gli errori, la seconda la lista si vuota».
  //
  // ⚠️ L'uscita anticipata e' qui e non nel callback perche' e' una proprieta'
  //    della NAVIGAZIONE, non di cio' che il consumer fa dopo: chiunque si
  //    agganci a `onMeseChange` ha lo stesso diritto di non essere svegliato
  //    per un cambio che non e' avvenuto.
  function selezionaMese(idx) {
    if (meseIdx.value === idx) return
    meseIdx.value = idx
    onMeseChange?.()
  }

  function cambiaAnno(delta) {
    const nuovo = anno.value + delta
    if (nuovo < DASH_ANNO_MIN || nuovo > DASH_ANNO_MAX) return
    anno.value = nuovo
    onMeseChange?.()
    onAnnoChange?.()
  }

  // Scopo: passo mese ±1 per lo stepper compatto (piccoli schermi),
  //        scavalcando l'anno ai bordi (dic ▶ = gennaio anno successivo);
  //        ai limiti del range anni il passo si ferma.
  function stepMese(delta) {
    let idx = meseIdx.value + delta
    if (idx > 11) {
      if (anno.value + 1 > DASH_ANNO_MAX) return
      anno.value += 1
      idx = 0
      onAnnoChange?.()
    } else if (idx < 0) {
      if (anno.value - 1 < DASH_ANNO_MIN) return
      anno.value -= 1
      idx = 11
      onAnnoChange?.()
    }
    selezionaMese(idx)
  }

  return { nomiMesi, competenzaCorrente, selezionaMese, cambiaAnno, stepMese }
}
