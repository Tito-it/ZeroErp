// ------------------------------------------------------------
// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Tid (Michele Carlo Titini)
// Doc: JavaScript
// Scopo: LA MACCHINA DI «RIGHE DA RATE» (D19-d, 2026-09-17): N rate scelte nel
//        picker, un importo per rata proposto dallo spazio, i fatti comuni, il
//        Salva su `POST distinte/{id}/righe/da-rate/` e l'ESITO PARZIALE — le
//        riuscite escono dall'area, le fallite restano col loro motivo e il
//        secondo tempo della capienza PER RIGA.
// Note: ⭐ E' la COMPOSIZIONE di due BB di core, non una macchina nuova:
//       `useSelezioneLista` (il telaio della selezione su lista PAGINATA —
//       attraversa le pagine, pota chi smette di essere selezionabile,
//       `tieniSolo` per l'esito parziale) e `useSelezioneConValore` (la mappa
//       chiave → importo seminata dallo spazio, sovrascrivibile, che diventa
//       il payload). Qui restano le sole cose di DOMINIO: il predicato
//       «selezionabile», la proposta, i fatti comuni, la lettura dell'esito.
//
//       ⭐ SELEZIONABILE = spazio ≠ 0 (Q-B, Tid 2026-09-17), NON > 0: sulla
//       nota di credito lo spazio e' negativo e la rata SI SCEGLIE — il
//       rimborso e' un incasso a segno invertito, e il segno lo porta il
//       numero. Una rata a spazio zero e' «esaurita»: si vede, non si sceglie.
//
//       🔴 IL SECONDO TEMPO E' PER RIGA. Il backend risponde 200 con
//       `esito · creati[] · falliti[]`, e ogni fallita porta l'errore INTERO
//       nella forma dell'envelope (`ui_action` compresa). Le riuscite sono
//       gia' righe del foglio: escono dall'area (`tieniSolo` sulle fallite).
//       Le fallite restano con la FRASE del database; quelle «confermabili»
//       (`ui_action = confirm_and_retry`, la stessa costante di
//       `useForzaturaConfermata`) offrono «Forza» + motivo, e il Salva
//       successivo rimanda le SOLE rimaste con `forzata` dove confermato — un
//       giro nuovo, chiave nuova. Il frontend resta cieco ai codici.
//
//       ⚠️ Lo status e' 200 anche su `PARZIALE`/`ERRORE`: `useApiHandler` non
//       vede nessun errore, quindi i toast dell'esito li decide questo
//       composable, non l'handler.
// ------------------------------------------------------------

import { computed, ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'

import { useApiHandler } from '../../core/composables/useApiHandler'
import { CONFERMA_E_RIPETI } from '../../core/composables/useForzaturaConfermata'
import { useNotify } from '../../core/composables/useNotify'
import { spazioSaldo } from './useSaldi'
import { useSelezioneConValore } from '../../core/composables/useSelezioneConValore'
import { useSelezioneLista } from '../../core/composables/useSelezioneLista'
import { toDateString, oggiAziendale } from '../../core/utils/date'
import { creaRigheDaRate } from '../api/pagamenti'

const ROW_KEY = 'scadenza_id'

// Scopo: «ESAURITA» = niente spazio su cui scrivere (Q-B). E' il predicato di
//        dominio della rata, in UNA sede: lo legge la macchina (selezionabile,
//        motivo) e lo legge il dialog (il click in singola, il Tag in colonna).
// ⚠️ `=== 0` e non `<= 0`: su una nota di credito lo spazio e' negativo e la
//    rata si sceglie. E `null` («non so») NON e' esaurita: e' non letta.
export function rataEsaurita(riga) {
  return spazioSaldo(riga) === 0
}

// Scopo: i fatti comuni al loro stato di partenza. La data del pagamento
//        nasce OGGI (si sta digitando il denaro di giornata) — come nel form
//        della riga singola, e per la stessa ragione.
function fattiIniziali() {
  return { data_pagamento: oggiAziendale(), data_valuta: null, riferimento_ente: '' }
}

// Params:
//   - contabileId:   getter della distinta su cui scrivere.
//   - righeVisibili: ref delle righe della pagina corrente della lista rate.
//   - abilitata:     ref: la selezione e' offerta (modalita' multipla).
export function useRigheDaRate({ contabileId, righeVisibili, abilitata }) {
  const { t } = useI18n()
  const notify = useNotify()
  const { execute, loading } = useApiHandler()

  // ── il telaio: la selezione attraverso le pagine ────────────────
  const selezionabile = (r) => {
    const spazio = spazioSaldo(r)
    return spazio != null && spazio !== 0
  }
  const telaio = useSelezioneLista({
    righeVisibili,
    abilitata,
    selezionabile,
    motivoNonSelezionabile: (r) => (rataEsaurita(r) ? t('pagamenti.rate.esaurita') : undefined),
    rowKey: ROW_KEY,
  })

  // ── i valori: un importo per rata, proposto dallo spazio ────────
  const importi = useSelezioneConValore({ rowKey: ROW_KEY, proponi: (r) => spazioSaldo(r) })
  watch(telaio.selezione, (righe) => importi.sincronizza(righe))

  // ── i fatti comuni e cio' che resta di un giro ─────────────────
  const fatti = ref(fattiIniziali())
  // scadenza_id → l'errore intero della riga fallita all'ultimo giro.
  const errori = ref({})
  // scadenza_id → true quando l'operatore ha confermato la forzatura.
  const forzature = ref({})
  // scadenza_id → il motivo scritto. ⭐ Vive QUI e non nel dialog, e separato
  // dalla conferma: spegnere e riaccendere «Forza» non deve cancellare la frase
  // appena scritta, e `azzera()` deve azzerare anche lei — un motivo tenuto in
  // un secondo stato nel template sopravviveva alla riapertura del dialog.
  const motivi = ref({})

  const errore = (chiave) => errori.value[chiave] ?? null
  const confermabile = (chiave) => errore(chiave)?.ui_action === CONFERMA_E_RIPETI
  const forzata = (chiave) => Object.hasOwn(forzature.value, chiave)
  const motivoDi = (chiave) => motivi.value[chiave] ?? ''

  // Scopo: la conferma del secondo tempo, per UNA riga: dal prossimo Salva
  //        quella riga viaggia con `forzata` e il motivo scritto per lei.
  function forza(chiave) {
    forzature.value = { ...forzature.value, [chiave]: true }
  }
  function annullaForzatura(chiave) {
    const { [chiave]: _via, ...resto } = forzature.value
    forzature.value = resto
  }
  function impostaMotivo(chiave, testo) {
    motivi.value = { ...motivi.value, [chiave]: testo ?? '' }
  }

  // Scopo: tiene di una mappa per chiave le sole chiavi ancora VIVE (le rate
  //        rimaste in area dopo un giro): errore, conferma e motivo di una
  //        riga che e' passata non servono piu' a niente.
  function soloVive(mappa, vive) {
    return Object.fromEntries(Object.entries(mappa).filter(([k]) => vive.has(Number(k))))
  }

  // Scopo: toglie una rata dall'area (e dalla selezione): e' il cestino.
  function rimuovi(riga) {
    telaio.selezione.value = telaio.selezione.value.filter((r) => r[ROW_KEY] !== riga[ROW_KEY])
  }

  const canSave = computed(
    () => telaio.selezione.value.length > 0
      && importi.incompleti.value.length === 0
      && !loading.value,
  )

  // Scopo: il payload del giro: i fatti comuni + una riga per rata scelta,
  //        con la forzatura dove l'operatore l'ha confermata.
  // ⚠️ Stringa vuota → NULL sul riferimento, come nel form della riga: il
  //    backend normalizza, e `''` a database sarebbe un valore diverso da
  //    «non c'e'».
  function payload() {
    const righe = importi.buildPayload(telaio.selezione.value, (r, importo) => {
      const riga = { scadenza_id: r[ROW_KEY], importo }
      if (forzata(r[ROW_KEY])) {
        riga.forzata = true
        const motivo = motivoDi(r[ROW_KEY]).trim()
        if (motivo) riga.motivo_forzatura = motivo
      }
      return riga
    })
    const p = {
      data_pagamento: toDateString(fatti.value.data_pagamento),
      data_valuta: fatti.value.data_valuta ? toDateString(fatti.value.data_valuta) : null,
      riferimento_ente: fatti.value.riferimento_ente?.trim() || null,
      righe,
    }
    return p
  }

  // Scopo: IL SALVA — un giro; risponde l'esito o `null` se la chiamata e'
  //        fallita (il toast l'ha gia' dato `useApiHandler`).
  // ⭐ Sull'esito: le riuscite ESCONO dall'area (sono gia' righe del foglio),
  //    le fallite restano ciascuna col suo errore, e la forzatura confermata
  //    su una riga che e' passata non serve piu' a niente.
  async function salva() {
    // `execute` consegna gia' il `data` interno dell'envelope: l'esito.
    const esito = await execute(() => creaRigheDaRate(contabileId(), payload()))
    if (esito === null) return null
    const fallite = esito.falliti ?? []
    telaio.tieniSolo(fallite.map((f) => f.scadenza_id))
    const prossimi = {}
    for (const f of fallite) prossimi[f.scadenza_id] = f.errore
    errori.value = prossimi
    // Conferme e motivi restano solo sulle righe ancora in area.
    const vive = new Set(fallite.map((f) => f.scadenza_id))
    forzature.value = soloVive(forzature.value, vive)
    motivi.value = soloVive(motivi.value, vive)
    if (esito.esito === 'COMPLETATO') {
      notify.success(t('pagamenti.rate.create', esito.riuscite, { n: esito.riuscite }))
    } else {
      notify.warn(t('pagamenti.rate.parziale', { riuscite: esito.riuscite, richieste: esito.richieste }))
    }
    return esito
  }

  function azzera() {
    telaio.azzera()
    importi.azzera()
    errori.value = {}
    forzature.value = {}
    motivi.value = {}
    fatti.value = fattiIniziali()
  }

  return {
    // il telaio, per le caselle della lista
    perLista: telaio.perLista,
    selezione: telaio.selezione,
    // i valori
    importoDi: importi.valoreDi,
    impostaImporto: importi.imposta,
    riproponi: importi.riproponi,
    incompleti: importi.incompleti,
    // i fatti comuni
    fatti,
    // l'esito dell'ultimo giro, per riga, e il secondo tempo
    errore, confermabile, forzata, forza, annullaForzatura, motivoDi, impostaMotivo,
    // i verbi
    rimuovi, salva, azzera,
    canSave, loading,
  }
}
