// ------------------------------------------------------------
// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Tid (Michele Carlo Titini)
// Doc: JavaScript
// Scopo: ⭐ IL CAMBIO DI CLIENTE DI UN DOCUMENTO IN BOZZA SI SALVA SUBITO, CON
//        CONFERMA. Scelto nel form un cliente diverso da quello salvato, il
//        drawer chiede conferma; confermato, scrive il SOLO cliente e ricarica:
//        il DB rifa' indirizzi e scheda di fornitura, e il pannello indirizzi
//        (e il drawer «Indirizzi») mostrano subito quelli del cliente nuovo,
//        correggibili. Annullato, o fallito il salvataggio, il form torna al
//        cliente salvato.
// Note: ⭐ Decisione di Tid (2026-10-19, collaudo di brief-db-indirizzi-
//       documento-seguono-il-cliente §8.8): fino ad allora il cambio di cliente
//       aspettava il Salva, e fino ad allora pannello e «Indirizzi» mostravano
//       gli indirizzi del cliente VECCHIO — fuorviante, e per correggerli si
//       doveva prima salvare. La regola «gli indirizzi seguono il cliente»
//       resta del DB (B-3): qui non si calcola niente, si scrive prima.
//       ⚠️ Le altre modifiche non salvate restano: la ricarica del drawer passa
//       da `useDrawerFormPreserve`, che le rimette sopra il dettaglio nuovo. Per
//       questo NON si chiama `fissa()` prima di ricaricare (le prenderebbe per
//       salvate e le perderebbe). I campi che SEGUONO il cliente (la scheda di
//       fornitura) invece vanno scartati prima (`scartaDipendenti`): rimessi
//       sopra quelli rifatti dal DB, riporterebbero i dati del cliente vecchio.
//       ⚠️ Un solo dialog alla volta: un altro cambio mentre la conferma e'
//       aperta non ne apre un secondo, e alla conferma si scrive il cliente
//       che il form ha in quel momento.
// ------------------------------------------------------------

import { ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import { useConfirmAction } from '../../../core/composables/useConfirmAction'
import { valoriUguali } from '../../../core/composables/useDrawerFormPreserve'
import { ripristinaBillingAccount } from '../../../core/utils/ripristinaLookup'
import { CLIENTE_BA, clienteCambiato } from './clienteCambiato'

// Opzioni:
//   form, detail       ref del form e del dettaglio salvato
//   campi              le colonne che dicono chi e' il cliente (default il BA)
//   colonne            quelle che la scelta del cliente cambia nel form, e che
//                      un annullo riporta al salvato (default: `campi` piu'
//                      l'istanza, che segue il BA)
//   attivo()           il documento esiste e il cliente si cambia ancora
//   payload()          il corpo della scrittura del solo cliente (default:
//                      BA e istanza, la coppia di preventivo, offerta, contratto)
//   salva(payload)     la PATCH (dentro `execute`): ritorna null se fallita
//   ricarica()         rilegge il dettaglio (con `preserva` del drawer)
//   ripristina()       dopo un annullo, oltre al BA (che si ricostruisce da
//                      se', `ripristinaBillingAccount`), gli altri oggetti dei
//                      lookup del cliente salvato (facoltativo: il destinatario
//                      del DDT)
//   scartaDipendenti() prima della ricarica, rimette ai valori salvati i campi
//                      che seguono il cliente (facoltativo: la scheda di
//                      fornitura di offerta e contratto, il destinatario del
//                      DDT col BA)
//   messaggio          la chiave i18n del testo della conferma (default: gli
//                      indirizzi; offerta e contratto nominano anche la scheda).
//                      ⚠️ Scelta esplicita, non dedotta da `scartaDipendenti`:
//                      cio' che si scarta e cio' che si dice sono due cose.
export function useCambioClienteDocumento({
  form, detail, campi = CLIENTE_BA, colonne = [...campi, 'istanza_utility_id'],
  attivo, payload = null, salva, ricarica, ripristina = null, scartaDipendenti = null,
  messaggio = 'vendite.cliente.cambio_messaggio',
}) {
  const { t } = useI18n()
  const { confirmAction } = useConfirmAction()
  const inCorso = ref(false)

  const vuoto = (v) => valoriUguali(v, null)

  // Il form ha un cliente da scrivere: diverso dal salvato, con almeno una
  // colonna valorizzata, e senza colonne TOLTE. ⛔ Un cliente tolto e non
  // ancora sostituito non si salva: si aspetta la scelta successiva. «Tolto»
  // e' una colonna che il salvato ha e il form ha svuotato — anche se un'altra
  // resta piena: sul DDT, tolto il BA, il destinatario resta quello del BA
  // tolto (`DdtForm`), e non e' una scelta dell'operatore. Un DDT nato senza
  // BA che cambia destinatario, invece, non toglie niente e si salva.
  function daSalvare() {
    if (!attivo()) return false
    const f = form.value
    const d = detail.value
    if (campi.every((c) => vuoto(f[c]))) return false
    if (campi.some((c) => !vuoto(d?.[c]) && vuoto(f[c]))) return false
    return clienteCambiato(f, d, campi)
  }

  function corpo() {
    if (payload) return payload()
    return {
      billing_account_id: form.value.billing_account_id,
      istanza_utility_id: form.value.istanza_utility_id,
    }
  }

  function tornaAlSalvato() {
    for (const c of colonne) form.value[c] = detail.value?.[c] ?? null
    form.value.billing_account_obj = null
    ripristinaBillingAccount(form.value, detail.value?.billing_account_id)
    ripristina?.()
  }

  // ⚠️ `finally`: una ricarica che solleva lascerebbe `inCorso` acceso, e da
  //    li' nessun altro cambio di cliente chiederebbe piu' niente.
  async function conferma() {
    try {
      if (!daSalvare()) return
      const esito = await salva(corpo())
      if (esito === null) {
        tornaAlSalvato()
      } else {
        scartaDipendenti?.()
        await ricarica()
      }
    } finally {
      inCorso.value = false
    }
  }

  watch(
    () => campi.map((c) => form.value?.[c]),
    () => {
      if (inCorso.value || !daSalvare()) return
      inCorso.value = true
      let deciso = false
      confirmAction({
        header: t('vendite.cliente.cambio_titolo'),
        message: t(messaggio),
        onAccept: () => { deciso = true; return conferma() },
        // Annulla, X o clic fuori: `onReject` puo' arrivare due volte
        // (reject e chiusura), e mai dopo una conferma.
        onReject: () => {
          if (deciso) return
          deciso = true
          tornaAlSalvato()
          inCorso.value = false
        },
      })
    },
  )

  return { inCorso }
}
