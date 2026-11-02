// ------------------------------------------------------------
// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Tid (Michele Carlo Titini)
// Doc: JavaScript
// Scopo: l'azione «Aggiorna date di consegna» della barra del drawer, per
//        ordine e preventivo (brief-db-date-consegna-righe-in-blocco §5, §8):
//        quali colonne si possono scrivere ORA, e il pulsante che apre il
//        dialog — acceso, spento col motivo o assente.
//
// ⭐ L'elenco delle colonne e' l'unica cosa che l'utility sa del documento, e
//    lo passa il drawer (D-4). Ogni colonna dice quando si accende con
//    `attiva()`, scritta dal drawer sulle capability (D-3: la data confermata
//    dell'ordine si scrive in bozza con `can_edit_righe` e dopo la conferma
//    con `can_edit_data_consegna_confermata`, spento in bozza di proposito).
//    Funzioni e non nomi di flag: cosi' il drawer chiama `caps.flag('can_x')`
//    e `npm run guard:capability` confronta quei nomi col contratto del DB.
// ⛔ Nessuna regola di stato scritta qui: le flag le manda il DB, e il
//    rifiuto vero resta dei lock delle righe.
// ⚠️ Nessuna colonna attiva (BF-3): il pulsante si spegne col motivo della
//    prima colonna che ne porta uno (`motivo()`, la frase gia' composta); se
//    nessuna lo porta il pulsante NON compare — come «Nuova riga» fuori bozza.
//    Un pulsante grigio e muto sembrerebbe un difetto.
// ⚠️ Documento senza righe: dove il pulsante comparirebbe, si spegne col suo
//    motivo — non c'e' nessuna riga su cui scrivere la data.
import { computed, ref, unref } from 'vue'
import { useI18n } from 'vue-i18n'
import { MANAGE_ICONS } from '../../../core/constants'

/**
 * @param {Object} opts
 * @param {Array<{colonna: string, labelKey: string, attiva: () => boolean, motivo?: () => string|null}>} opts.colonne
 * @param {Function|Ref<boolean>} opts.readonlyPuro - permessi / split: nasconde
 * @param {Function|Ref<boolean>} opts.presente - il documento c'e' (dettaglio letto)
 * @param {Function|Ref<number>} opts.righe - quante righe ha il documento
 */
export function useDateConsegnaRighe({ colonne, readonlyPuro, presente, righe }) {
  const { t } = useI18n()
  const dialogVisible = ref(false)
  const leggi = (v) => (typeof v === 'function' ? v() : unref(v))

  // Le colonne scrivibili ora, con l'etichetta: quelle che il dialog propone.
  const colonneAttive = computed(() => colonne
    .filter((c) => c.attiva())
    .map((c) => ({ colonna: c.colonna, label: t(c.labelKey) })))

  // Il motivo per cui non se ne scrive nessuna: il primo che una colonna da'.
  function motivoSpento() {
    for (const c of colonne) {
      const motivo = c.motivo?.() || null
      if (motivo) return motivo
    }
    return null
  }

  // L'azione per `DrawerActionsBar`: sempre un array (0 o 1 voce).
  const azione = computed(() => {
    if (leggi(readonlyPuro) || !leggi(presente)) return []
    const scrivibile = colonneAttive.value.length > 0
    const motivoColonne = scrivibile ? null : motivoSpento()
    if (!scrivibile && !motivoColonne) return []
    const conRighe = (leggi(righe) ?? 0) > 0
    const accesa = scrivibile && conRighe
    const motivo = motivoColonne || (conRighe ? null : t('vendite.date_consegna.nessuna_riga'))
    return [{
      key: 'date-consegna',
      kind: 'manage',
      label: t('vendite.date_consegna.azione'),
      icon: MANAGE_ICONS.PROMESSA_CONSEGNA,
      disabled: !accesa,
      tooltip: motivo || undefined,
      command: () => { dialogVisible.value = true },
    }]
  })

  return { dialogVisible, colonneAttive, azione }
}
