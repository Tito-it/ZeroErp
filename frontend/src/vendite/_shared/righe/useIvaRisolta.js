// ------------------------------------------------------------
// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Tid (Michele Carlo Titini)
// ------------------------------------------------------------
// Scopo: l'IVA di una riga di documento, risolta dalla SEDE UNICA.
//   Sostituisce l'auto-fill `form.iva_id = articolo.iva_id` che i tre
//   `*RigaForm` facevano ognuno per conto suo.
//
// ⛔ SOSTITUISCE, NON AFFIANCA. Se il backend risolve e il form continua a
//    copiare dall'articolo ci sono DUE risposte alla stessa domanda — cioe' il
//    difetto di oggi con un pezzo in piu'. L'auto-fill dall'articolo ignora
//    l'uso della fornitura e i titoli documentati del cliente: su un
//    esportatore abituale proponeva l'aliquota piena.
//
// ⚠️ Best-effort di proposito: se l'anteprima non risponde, il campo resta
//    com'e' e si puo' salvare lo stesso. L'autorita' e' il backend al
//    salvataggio, non questa chiamata — che serve a far VEDERE, non a decidere.
//
// Estratto alla 3a occorrenza (regola del 2): preventivi, ordini, DDT.

import { computed, ref, unref } from 'vue'
import { useI18n } from 'vue-i18n'
import { resolveIvaRiga } from '../../api/iva'
import { useFetchVersion } from '../../../core/composables/useFetchVersion'
import { labelOrCode } from '../../../core/utils/i18nLabel'

// ⚠️ `documentoId` si accetta in tutte e tre le forme — getter, ref o valore —
//    perche' i tre form lo hanno in forme diverse e obbligarli a uniformarsi
//    sposterebbe il problema su di loro. Un id letto UNA volta al setup
//    sarebbe sbagliato: il drawer si riusa fra documenti diversi.
function idCorrente(documentoId) {
  return typeof documentoId === 'function' ? documentoId() : unref(documentoId)
}

export function useIvaRisolta({ documentoTipo, documentoId }) {
  const { t, te } = useI18n()
  const ivaOrigine = ref(null)
  const ivaTitoloId = ref(null)
  const ivaNorma = ref(null)
  const loading = ref(false)
  // Anti-race: l'operatore puo' cambiare articolo piu' in fretta di quanto
  // torni la risposta, e la piu' lenta vincerebbe.
  const { tag, isCurrent } = useFetchVersion()

  // Scopo: risolve il trattamento per l'articolo scelto e lo applica al form.
  //   Ritorna l'`iva_id` risolto (o null), gia' scritto in `form.iva_id`.
  async function risolviPer(form, articoloId) {
    if (!articoloId) return null
    const mio = tag()
    loading.value = true
    try {
      const { data } = await resolveIvaRiga({
        articoloId, documentoTipo, documentoId: idCorrente(documentoId),
      })
      if (!isCurrent(mio)) return null
      const p = data?.data || {}
      form.iva_id = p.iva_id ?? null
      ivaOrigine.value = p.origine ?? null
      ivaTitoloId.value = p.titolo_iva_id ?? null
      ivaNorma.value = p.riferimento_normativo ?? null
      return p.iva_id ?? null
    } catch {
      // ⚠️ Silenzioso e non un toast: il salvataggio risolve comunque lato
      //    backend, e un errore qui interromperebbe la compilazione per una
      //    cosa che si sistema da sola. Il campo resta vuoto e l'operatore lo
      //    riempie a mano — che fino a `I6` e' ancora un suo diritto.
      if (isCurrent(mio)) { ivaOrigine.value = null; ivaTitoloId.value = null; ivaNorma.value = null }
      return null
    } finally {
      if (isCurrent(mio)) loading.value = false
    }
  }

  // Scopo: azzera lo stato quando la riga cambia identita' (nuovo articolo,
  //   apertura in edit): un'origine rimasta dalla riga precedente spiegherebbe
  //   un numero che non c'e' piu'.
  function reset() {
    ivaOrigine.value = null
    ivaTitoloId.value = null
    ivaNorma.value = null
  }

  // ⭐ LA LABEL LA COMPONE IL COMPOSABLE, non i tre template. Prima il percorso
  //    i18n era costruito con un template literal in ciascuno dei tre form:
  //    tre copie di una convenzione di naming, e il giorno che cambia il
  //    prefisso ne resta indietro una — muta, perche' `labelOrCode` mostra il
  //    codice grezzo invece di fallire.
  // ⚠️ `labelOrCode` e non `t()` secco: il vocabolario di `origine` e' del DB
  //    ed e' APERTO — un valore nuovo deve comparire come codice, non come
  //    path di chiave.
  const origineLabel = computed(() => (
    ivaOrigine.value
      ? labelOrCode(t, te, `vendite.iva_origine.${ivaOrigine.value}`, ivaOrigine.value)
      : ''
  ))

  return { ivaOrigine, ivaTitoloId, ivaNorma, origineLabel, loading, risolviPer, reset }
}
