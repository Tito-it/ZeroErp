// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Tid (Michele Carlo Titini)
// Scopo: Composable adapter per il blob `capabilities` ritornato dal
//        detail BE (Fase 1 refactor frontend vendite + estensioni).
//        Incapsula la lettura di `available_actions[]`, `non_editable_fields[]`,
//        flag `can_*` con isLocked(field) coerente.
//        Mai logica derivata: lookup puro O(1) nei Set, getter computed.
//
// ⛔ IL BLOB STA SOTTO `detail.capabilities`, non fuso nel dettaglio (api.md
//    §«Il blob sta SOTTO `capabilities`», decisione Tid 2026-09-23). Il BB lo
//    legge SOLO da li': nessuna doppia lettura «annidato o piatto» — i sette
//    service di vendite sono stati convertiti nello stesso giro
//    (brief-be-fe-capability-annidata), quindi un ponte non avrebbe avuto
//    niente da traghettare e sarebbe rimasto il posto dove la forma vecchia
//    sopravvive.
//
// ⭐ Motivi, chiavi i18n e ogni altro campo non booleano si leggono da
//    `capabilities` (`capabilities.value.can_x_reason_key`), MAI da
//    `detail.can_x_reason_key`: e' la forma che `npm run guard:capability`
//    riconosce e confronta col contratto del database.
//
//        Consumer: i drawer di preventivi, offerte, contratti, ordini, DDT,
//        resi (editFlag=can_edit_testata) e promo articoli (editFlag=can_update).
import { computed } from 'vue'

/**
 * Ritorna helper reattivi per consumare il blob capabilities di un detail BE.
 *
 * @param {Ref<Object|null>} detailRef - ref al detail BE (puo' essere null in create)
 * @param {Object} [opts]
 * @param {string} [opts.editFlag='can_edit_testata'] - chiave del flag editabilita'
 *   testata. PromoArticoloDrawer usa `can_update`.
 * @returns {{
 *   capabilities: ComputedRef<Object>,
 *   availableActions: ComputedRef<Array>,
 *   nonEditableFields: ComputedRef<Set<string>>,
 *   canEdit: ComputedRef<boolean>,
 *   azioneNegata: (flagKey: string, azione: Object) => Array,
 *   isLocked: (field: string) => boolean,
 *   flag: (key: string) => boolean,
 * }}
 */
export function useEntityCapabilities(detailRef, opts = {}) {
  const { editFlag = 'can_edit_testata' } = opts

  // Il blob intero, `{}` finche' il detail non c'e' (create) o se il BE l'ha
  // consegnato vuoto (capability layer rotto: tutto spento, fail-closed).
  const capabilities = computed(() => detailRef.value?.capabilities ?? {})

  // Azioni disponibili sullo stato corrente (cambio stato + revisione, ecc.).
  // Sempre array (anche se detail null) per rendere safe il v-for nel template.
  // Defense-in-depth: filtra le azioni con `label_key` non valorizzato. Una
  // transizione con `meta.manuale=false` o con `meta` mal popolato non
  // dovrebbe arrivare qui (responsabilita' fn DB + seed `meta`), ma se ci
  // arriva il `t(null)` del template crasha l'intero render. Il filtro
  // degrada silentemente nascondendo il pulsante non renderizzabile.
  const availableActions = computed(() => {
    const raw = capabilities.value.available_actions || []
    return raw.filter((a) => a && typeof a.label_key === 'string' && a.label_key)
  })

  // Set per lookup O(1) di campi non editabili. Pattern allineato ai 3 drawer.
  const nonEditableFields = computed(() => new Set(capabilities.value.non_editable_fields || []))

  // Flag editabilita' principale. `=== true` esplicito per non considerare
  // "truthy" valori come 1 o stringhe (il BE garantisce bool).
  const canEdit = computed(() => capabilities.value[editFlag] === true)

  // Un campo e' "locked" se l'editabilita' globale e' off OPPURE se il campo
  // e' nella whitelist BE (es. `utility_id` sempre immutabile post-create).
  function isLocked(field) {
    return !canEdit.value || nonEditableFields.value.has(field)
  }

  // Getter generico per altri flag boolean (`can_edit_righe`, `can_change_state`,
  // `can_create_revisione`, `can_push_commessa`, ...). Coerente con `=== true`.
  function flag(key) {
    return capabilities.value[key] === true
  }

  // Scopo: l'azione NEGATA di un flag che non e' un'azione di stato (es.
  //        `can_push_commessa`): se il flag e' spento e il blob ne dice il
  //        motivo (`<flag>_reason` / `<flag>_reason_key`), un'entry
  //        `enabled: false` nella stessa forma di `available_actions`, cosi'
  //        il mapper condiviso la rende disabilitata col tooltip. Presentazione
  //        tooltip e non banner: molte cause sono PERMANENTI (Decisione D,
  //        brief-db-ddt-reason-push-catch-all §3).
  //        Sempre array: il chiamante la concatena alle azioni di stato.
  // ⚠️ Flag spento SENZA motivo → nessuna entry: un pulsante spento e muto
  //    sembrerebbe una regola e non si saprebbe perche'.
  // Nato da due copie identiche (DdtDrawer, OrdiniDrawer), regola del 2,
  // 2026-09-23.
  function azioneNegata(flagKey, azione) {
    if (flag(flagKey)) return []
    const reason = capabilities.value[`${flagKey}_reason`] ?? null
    const reasonKey = capabilities.value[`${flagKey}_reason_key`] ?? null
    if (!reason && !reasonKey) return []
    return [{
      target_state: null,
      outlined: false,
      ...azione,
      enabled: false,
      reason,
      reason_key: reasonKey,
    }]
  }

  return {
    capabilities,
    availableActions,
    nonEditableFields,
    canEdit,
    isLocked,
    flag,
    azioneNegata,
  }
}
