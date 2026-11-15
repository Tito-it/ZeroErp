// ------------------------------------------------------------
// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Tid (Michele Carlo Titini)
// Doc: JavaScript
// ------------------------------------------------------------
// Scopo: LA LETTURA DEI MOTIVI DEL CAMBIO DI NATURA di un soggetto, in un
//        posto solo per i due che la fanno: la tendina della natura
//        (`SoggettoForm`, dalle nature proponibili del dettaglio) e l'elenco
//        dei motivi nel drawer (`SoggettoDrawer`, dall'endpoint dei motivi).
//        Brief brief-db-cambio-natura-soggetto §6.0, K-7.
//
// ⭐ I motivi li produce il DB (`anagrafiche.fn_check_cambio_natura_soggetto`),
//    la stessa check del guard che rifiuta il PATCH: qui non si decide niente,
//    si legge `dettaglio.campo` di ciascun motivo.
//
// ⚠️ Un motivo su un CAMPO DELLA RIGA (P.IVA, cliente PA, split payment) non
//    spegne la natura: si toglie correggendo quel campo nello STESSO
//    salvataggio, e il guard vede i valori nuovi. Gli altri (un'altra famiglia,
//    i documenti, i titoli IVA, i dati societari, gli indirizzi) si tolgono
//    fuori da qui, e finche' ci sono la natura resta spenta.
// ⚠️ Un campo della riga BLOCCATO per chi agisce (`non_editable_fields` del
//    dettaglio: la P.IVA scritta la svuota solo un amministratore) dal form non
//    si corregge: il suo motivo spegne la natura come gli altri.
// ------------------------------------------------------------

import { componiBloccoMotivo } from '../../core/utils/bloccoMotivo'

// I campi del soggetto che il motivo puo' indicare e che si correggono nel
// drawer: sono gli argomenti della check oltre alla natura.
export const CAMPI_RIGA_CAMBIO_NATURA = Object.freeze(['partita_iva', 'cliente_pa', 'split_payment'])

const campoDi = (motivo) => motivo?.dettaglio?.campo ?? null

// Il motivo si toglie dal form? Solo se indica un campo della riga che chi
// agisce puo' scrivere.
const siCorreggeNelForm = (motivo, campiBloccati) => {
  const campo = campoDi(motivo)
  return CAMPI_RIGA_CAMBIO_NATURA.includes(campo) && !(campiBloccati ?? []).includes(campo)
}

// Scopo: la natura e' spenta? Vero se almeno un motivo non si toglie dal form.
//        `campiBloccati`: i `non_editable_fields` del dettaglio.
export function naturaSpenta(motivi, campiBloccati = []) {
  return (motivi ?? []).some(m => !siCorreggeNelForm(m, campiBloccati))
}

// Scopo: i campi della riga che i motivi chiedono di correggere (si accendono).
export function campiDaMotivi(motivi) {
  return new Set(
    (motivi ?? []).map(campoDi).filter(c => CAMPI_RIGA_CAMBIO_NATURA.includes(c)),
  )
}

// Scopo: la frase di un motivo. Fail-visible come il BB: senza traduzione si
//        vede il codice macchina.
export function fraseMotivo(t, te, motivo) {
  return componiBloccoMotivo(t, te, {
    reason: motivo?.codice ?? '',
    reasonKey: motivo?.reason_key ?? '',
    dettaglio: motivo?.dettaglio ?? null,
  })
}

// Scopo: il primo motivo che spegne la natura (quello da dire accanto alla
//        voce spenta), o null.
export function primoMotivoBloccante(motivi, campiBloccati = []) {
  return (motivi ?? []).find(m => !siCorreggeNelForm(m, campiBloccati)) ?? null
}
