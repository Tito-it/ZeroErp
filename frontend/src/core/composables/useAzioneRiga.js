// ------------------------------------------------------------
// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Tid (Michele Carlo Titini)
// Doc: JavaScript
// Scopo: Il pulsante di un'AZIONE DI RIGA spento col suo motivo, letto dal
//        registro del DB (`config.azioni_riga`, lookup `azioni-riga`): dato il
//        codice dell'azione, il registro dice QUALI due colonne della riga
//        portano il motivo (`colonna_motivo`, il codice macchina) e la sua
//        chiave i18n (`colonna_motivo_chiave`); da quelle escono lo stato del
//        pulsante e il tooltip.
// Note: ⭐ Nasce col registro (brief-modello-documento-vendita §15.11.2, FE-1;
//        F-5, Q-F5 di Tid, 2026-10-27): un'azione di riga nuova si aggiunge con
//        una riga di registro e la sua vista, senza scrivere un pulsante nuovo.
//        Prima ogni pulsante sapeva a mano come si chiamavano le sue colonne.
//        ⛔ NON ricalcola niente: il motivo lo scrive in riga la stessa
//        `fn_check_*` con cui il database RIFIUTA (linee guida SQL §12.5), e
//        qui si traduce soltanto.
//        ⛔ FAIL-CLOSED: finché il registro non c'è, o se l'azione non vi è
//        iscritta, il pulsante è SPENTO. Un pulsante acceso su colonne che non
//        si sa leggere proporrebbe un gesto che il DB rifiuta.
//        ⚠️ Ma il motivo dice QUALE dei tre casi è, e non sempre «Caricamento...»:
//        in volo; registro non letto (la fetch è fallita, e non riprova da
//        sola: «Caricamento...» resterebbe lì per sempre, una bugia); azione
//        non iscritta o spenta nel registro (letto, ma senza la sua voce).
//        ⭐ `bloccata` si DEDUCE da `motivo`, mai il contrario: non esiste un
//        pulsante spento senza una frase che dica perché (§12 delle linee
//        guida), e i chiamanti che derivano `disabled` dal motivo restano
//        giusti anche durante il caricamento.
//        ⚠️ `labelOrCode`: una chiave che i locales non conoscono ancora mostra
//        il CODICE del motivo, mai il vuoto — il vocabolario dei motivi è del
//        DB ed estensibile, il frontend arriva sempre dopo.
// ------------------------------------------------------------
import { computed } from 'vue'
import { useI18n } from 'vue-i18n'
import { useGlobalLookup } from './useGlobalLookup'
import { lookupAzioniRiga } from '../apiCore'
import { labelOrCode } from '../utils/i18nLabel'

// La chiave della cache condivisa: un registro solo per tutta l'app.
export const CHIAVE_AZIONI_RIGA = 'core.azioni_riga'

// Scopo: le due letture di una riga per l'azione `codice`.
//   - `motivo(riga)`: la frase del motivo, `undefined` quando l'azione è
//     AMMESSA — non stringa vuota, che renderebbe un tooltip senza testo;
//   - `bloccata(riga)`: il pulsante è spento? = c'è un motivo.
//   `pronta` dice se il registro conosce l'azione.
export function useAzioneRiga(codice) {
  const { t, te } = useI18n()
  const { items, loaded, error, load } = useGlobalLookup(CHIAVE_AZIONI_RIGA, lookupAzioniRiga)
  // Una fetch sola per tutta l'app (dedup della cache); l'errore resta
  // nell'`error` condiviso e qui il pulsante resta spento (fail-closed).
  load()?.catch?.(() => { /* errore gia' nella cache condivisa */ })

  const voce = computed(
    () => (items.value ?? []).find((a) => a.codice_interno === codice) ?? null,
  )

  function motivo(riga) {
    const v = voce.value
    if (!v) {
      if (error.value) return t('common.azione_riga_registro_non_letto')
      if (loaded.value) return t('common.azione_riga_non_registrata')
      return t('common.loading')
    }
    const reason = riga?.[v.colonna_motivo]
    if (!reason) return undefined
    return labelOrCode(t, te, riga?.[v.colonna_motivo_chiave], reason)
  }

  const bloccata = (riga) => Boolean(motivo(riga))

  return { bloccata, motivo, pronta: computed(() => voce.value !== null) }
}
