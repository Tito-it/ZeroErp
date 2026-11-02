<!--
  SPDX-License-Identifier: AGPL-3.0-or-later
  Copyright (C) 2026 Tid (Michele Carlo Titini)
-->
<script setup>
// Scopo: l'esito del giro di accredito quando NON è andato tutto liscio.
//
// ⭐ PERCHÉ ESISTE (F2). Il verbo è massivo e il backend risponde con un
// report a tre stati: «19 su 20, una segnalata». Un 19-su-20 che non dice
// QUALE non è interpretabile — l'operatore non sa cosa riprovare, e la riga
// rimasta indietro resta in coda senza che nessuno sappia perché. Il toast dà
// il conto; questo dà l'elenco.
//
// ⚠️ Non è un dialog di errore: `PARZIALE` è un esito NORMALE (200). Il verbo
// non emette la nota di credito — registra l'accredito e lo mette nel giro di
// fatturazione — quindi una riga rifiutata non lascia mai mezzo documento:
// lascia una riga che resta in coda.
//
// Consultivo: sola chiusura, nessun verbo. Riprovare significa ri-selezionare
// in lista, dove il gate delle righe è quello vero.
import { computed } from 'vue'
import { useI18n } from 'vue-i18n'
import Column from 'primevue/column'
// DataTable grezza: sono le righe RIFIUTATE del giro appena fatto (`falliti`,
// dal report del verbo), mostrate per intero in un dialog consultivo — non
// paginata, non configurabile, e non sopravvive alla chiusura.
// eslint-disable-next-line no-restricted-imports -- eccezione nel registro DataTable (scripts/datatable.baseline.json)
import DataTable from 'primevue/datatable'
import Tag from 'primevue/tag'
import AppDialog from '../../../core/components/AppDialog.vue'
import { ESITO_ACCREDITO } from '../constants'

const props = defineProps({
  visible: { type: Boolean, required: true },
  // Il report del backend: { esito, totale, ok, accrediti[], falliti[] }.
  esito: { type: Object, default: null },
})
const emit = defineEmits(['update:visible'])

const { t } = useI18n()

const falliti = computed(() => props.esito?.falliti ?? [])
const severity = computed(() => (props.esito?.esito === ESITO_ACCREDITO.PARZIALE ? 'warn' : 'danger'))
</script>

<template>
  <AppDialog
    :visible="visible"
    width="lg"
    :header="t('vendite.resi.accredito_esito_header')"
    close-only
    @update:visible="emit('update:visible', $event)"
    @cancel="emit('update:visible', false)"
  >
    <p style="margin-top: 0;">
      <Tag :severity="severity" :value="esito?.esito" />
      <span style="margin-left: 0.5rem;">
        {{ t('vendite.resi.accredito_esito_riassunto', {
          ok: esito?.ok ?? 0, totale: esito?.totale ?? 0,
        }) }}
      </span>
    </p>

    <DataTable :value="falliti" size="small" class="app-datatable app-datatable--inner"
      data-key="resi_riga_id">
      <Column field="resi_riga_id" :header="t('vendite.resi.accredito_esito_col_riga')"
        style="width: 110px;" />
      <Column field="codice" :header="t('vendite.resi.accredito_esito_col_codice')"
        style="width: 260px;" />
      <!-- Il messaggio arriva dal catalogo errori del database: si mostra così
           com'è, non si riscrive qui — riscriverlo sarebbe una seconda copia
           che diverge alla prima modifica del catalogo. -->
      <Column field="messaggio" :header="t('vendite.resi.accredito_esito_col_messaggio')" />
    </DataTable>
  </AppDialog>
</template>
