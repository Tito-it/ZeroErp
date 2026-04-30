// SPDX-License-Identifier: GPL-3.0-or-later
// Copyright (C) 2026 Tid (Michele Carlo Titini)
// Scopo: Composable adapter per i blocchi `capabilities` ritornati dal
//        detail BE (Fase 1 refactor frontend vendite + estensioni).
//        Incapsula la lettura di `available_actions[]`, `non_editable_fields[]`,
//        flag `can_*` con isLocked(field) coerente.
//        Mai logica derivata: lookup puro O(1) nei Set, getter computed.
//
//        Consumer attuali (Fase 4.F2):
//        - PreventiviDrawer (editFlag=can_edit_testata)
//        - ContrattoDrawer  (editFlag=can_edit_testata)
//        - PromoArticoloDrawer (editFlag=can_update)
import { computed } from 'vue'

/**
 * Ritorna helper reattivi per consumare il blob capabilities di un detail BE.
 *
 * @param {Ref<Object|null>} detailRef - ref al detail BE (puo' essere null in create)
 * @param {Object} [opts]
 * @param {string} [opts.editFlag='can_edit_testata'] - chiave del flag editabilita'
 *   testata. PromoArticoloDrawer usa `can_update`.
 * @returns {{
 *   availableActions: ComputedRef<Array>,
 *   nonEditableFields: ComputedRef<Set<string>>,
 *   canEdit: ComputedRef<boolean>,
 *   isLocked: (field: string) => boolean,
 *   flag: (key: string) => boolean,
 * }}
 */
export function useEntityCapabilities(detailRef, opts = {}) {
  const { editFlag = 'can_edit_testata' } = opts

  // Azioni disponibili sullo stato corrente (cambio stato + revisione, ecc.).
  // Sempre array (anche se detail null) per rendere safe il v-for nel template.
  const availableActions = computed(() => detailRef.value?.available_actions || [])

  // Set per lookup O(1) di campi non editabili. Pattern allineato ai 3 drawer.
  const nonEditableFields = computed(() => new Set(detailRef.value?.non_editable_fields || []))

  // Flag editabilita' principale. `=== true` esplicito per non considerare
  // "truthy" valori come 1 o stringhe (il BE garantisce bool).
  const canEdit = computed(() => detailRef.value?.[editFlag] === true)

  // Un campo e' "locked" se l'editabilita' globale e' off OPPURE se il campo
  // e' nella whitelist BE (es. `utility_id` sempre immutabile post-create).
  function isLocked(field) {
    return !canEdit.value || nonEditableFields.value.has(field)
  }

  // Getter generico per altri flag boolean (`can_edit_righe`, `can_change_state`,
  // `can_create_revisione`, `can_push_commessa`, ...). Coerente con `=== true`.
  function flag(key) {
    return detailRef.value?.[key] === true
  }

  return {
    availableActions,
    nonEditableFields,
    canEdit,
    isLocked,
    flag,
  }
}
