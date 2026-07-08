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

  // Nomi mese localizzati: un solo Intl.DateTimeFormat per (anno, locale).
  const nomiMesi = computed(() => {
    const fmt = new Intl.DateTimeFormat(locale.value, { month: 'long' })
    return Array.from({ length: 12 }, (_, m) => fmt.format(new Date(anno.value, m, 1)))
  })

  const competenzaCorrente = computed(
    () => `${anno.value}-${String(meseIdx.value + 1).padStart(2, '0')}-01`
  )

  function selezionaMese(idx) {
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
