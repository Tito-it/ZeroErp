<!--
  SPDX-License-Identifier: GPL-3.0-or-later
  Copyright (C) 2026 Tid (Michele Carlo Titini)
-->
<script setup>
// Scopo: il drawer di una riga del tab «Altri accessi» (brief-db-be-fe-area-
//        accessi, A-4): chi e' la persona, le sue vesti con lo stato e il
//        soggetto collegato — da cui si apre la scheda che le governa — e le
//        azioni della CREDENZIALE (blocco, secondo fattore).
// ⛔ Le VESTI non si gestiscono da qui: invito, reinvio e disattivazione
//    restano nella scheda del cliente o del fornitore, che ne e' il
//    proprietario. Qui si legge la veste e si va alla sua scheda.
// ⚠️ Niente dettaglio da rileggere: la riga della lista porta gia' tutto
//    (`anagrafiche.vw_accessi_altri`); lo stato della credenziale lo rilegge
//    `CredenzialeAzioni` per conto suo, e dopo un blocco il drawer avvisa la
//    lista (`changed`), che si ricarica.
import { computed } from 'vue'
import { useI18n } from 'vue-i18n'
import Button from 'primevue/button'
import Tag from 'primevue/tag'
import AppDrawer from '../../core/components/AppDrawer.vue'
import { useDrawerClose } from '../../core/composables/useDrawerClose'
import { useInjectReadonly } from '../../core/composables/useReadonlyMode'
import { DRAWER_WIDTH, MANAGE_ICONS } from '../../core/constants'
import { NAV_ICONS } from '../../core/navigation'
import { displayDate, displayTimestamp } from '../../core/utils/date'
import { etichettaRuoloApplicativo } from '../../core/utils/i18nLabel'
import { statoVesteSeverity } from '../../core/utils/severity'
import { destinazioneVeste, useSchedaVeste } from '../composables/useSchedaVeste'
import CredenzialeAzioni from './CredenzialeAzioni.vue'

const props = defineProps({
  visible: { type: Boolean, default: false },
  riga: { type: Object, default: null },
  readonly: { type: Boolean, default: false },
})
const emit = defineEmits(['update:visible', 'changed'])

const { t, te } = useI18n()
const parentReadonly = useInjectReadonly()
const isReadonly = computed(() => props.readonly || parentReadonly.value)
const onClose = useDrawerClose(emit)
const { apriSchedaVeste } = useSchedaVeste()

// Scopo: va alla scheda del soggetto della veste, chiudendo il drawer: la
//        scheda si apre in un'altra pagina, e questo resterebbe davanti.
function vaiAllaScheda(veste) {
  onClose()
  apriSchedaVeste(veste)
}
</script>

<template>
  <!-- Il chrome e' di AppDrawer dal 2026-10-03
       (work-done/analisi-fe-chrome-drawer.md). -->
  <AppDrawer
    :visible="visible"
    :title="riga?.nome_visualizzato || t('amministrazione.accessi.tab_altri')"
    :icon="NAV_ICONS.ACCESSI"
    :action="t('common.view')"
    :width="DRAWER_WIDTH.STANDARD"
    :proteggi-corpo="false"
    :readonly="isReadonly"
    footer="chiudi"
    @update:visible="(v) => emit('update:visible', v)"
  >
    <template v-if="riga">
      <div class="form-grid-2col">
        <div class="form-field">
          <label>{{ t('amministrazione.field_username') }}</label>
          <span class="app-mono">{{ riga.username }}</span>
        </div>
        <div class="form-field">
          <label>{{ t('amministrazione.field_email') }}</label>
          <span>{{ riga.email || '—' }}</span>
        </div>
        <div class="form-field">
          <label>{{ t('amministrazione.field_ultimo_accesso') }}</label>
          <span>{{ riga.ultimo_accesso ? displayTimestamp(riga.ultimo_accesso) : t('amministrazione.mai_entrato') }}</span>
        </div>
      </div>

      <div class="app-drawer-section"><h4>{{ t('amministrazione.accessi.col_vesti') }}</h4></div>
      <p v-if="riga.nessun_accesso" class="app-text-muted">
        {{ t('amministrazione.accessi.nessun_accesso_spiegazione') }}
      </p>
      <ul v-else class="app-accessi-vesti">
        <li v-for="veste in riga.vesti" :key="veste.identita_id">
          <div class="app-accessi-veste-testa">
            <Tag :value="etichettaRuoloApplicativo(t, te, veste.ruolo_applicativo)" severity="info" />
            <Tag :value="t(`auth.stato_veste.${veste.stato}`)" :severity="statoVesteSeverity(veste.stato)" />
            <span>{{ veste.soggetto }}</span>
          </div>
          <small v-if="veste.token_scade_at" class="app-field-hint">
            {{ t('amministrazione.accessi.invito_scade', { quando: displayTimestamp(veste.token_scade_at) }) }}
          </small>
          <small v-if="veste.valido_al" class="app-field-hint">
            {{ t('amministrazione.accessi.veste_valida_al', { quando: displayDate(veste.valido_al) }) }}
          </small>
          <div v-if="destinazioneVeste(veste)">
            <Button
              :label="t('amministrazione.accessi.apri_scheda')"
              :icon="MANAGE_ICONS.VAI_A"
              text size="small"
              class="app-escape"
              @click="vaiAllaScheda(veste)"
            />
          </div>
        </li>
      </ul>

      <CredenzialeAzioni
        :auth-user-id="riga.auth_user_id"
        :readonly="isReadonly"
        @changed="emit('changed')"
      />
    </template>
  </AppDrawer>
</template>

<style scoped>
.app-accessi-vesti {
  list-style: none;
  margin: 0;
  padding: 0;
  display: flex;
  flex-direction: column;
  gap: var(--app-space-sm);
}
.app-accessi-veste-testa {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: var(--app-space-sm);
}
</style>
