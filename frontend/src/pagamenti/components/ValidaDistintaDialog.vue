<!--
  SPDX-License-Identifier: AGPL-3.0-or-later
  Copyright (C) 2026 Tid (Michele Carlo Titini)
-->
<script setup>
// Scopo: LA VALIDAZIONE della distinta — «ho finito di inserire, e' pronta da
//        registrare» (D14-a-bis) — coi NUMERI davanti (FE-1, D20-a).
//
// ⭐ Non e' piu' il confirm generico «portare la distinta a VALIDATA?»: chi
//    valida deve vedere che cosa sta dichiarando finito — dichiarato, totale
//    righe, scarto (nei suoi tre esiti: quadra · non quadra · non si applica)
//    e le righe PER STATO, cioe' quante ne restano da guardare, quante sono
//    sospese, quante «non nostre». Il denaro non e' ancora registrato: quello
//    lo fa «Registra», che tiene la sua anteprima.
//
// ⭐ SPENTO COL MOTIVO quando non si puo' (`can_validare = false`): la frase
//    viene dal DATABASE — la STESSA check che il guard chiama per rifiutare
//    (`validazione_blocco_*`, letta col BB `bloccoMotivo`) — quindi cio' che
//    il dialog dice e cio' che il 409 direbbe non possono divergere. ⛔ Nessun
//    `if righe DA_ABBINARE > 0` qui: sarebbe la regola scritta due volte.
//
// ⚠️ Il gesto e' lo stesso `POST …/stato/` di prima: il dialog cambia solo
//    che cosa si vede prima di premere, non che cosa si scrive.
import { computed } from 'vue'
import { useI18n } from 'vue-i18n'
import Message from 'primevue/message'
import Tag from 'primevue/tag'

import AppDialog from '../../core/components/AppDialog.vue'
import { useApiHandler } from '../../core/composables/useApiHandler'
import { motivoBloccoRiga } from '../../core/utils/bloccoMotivo'
import { statoRigaContabileSeverity } from '../../core/utils/severity'
import { cambiaStatoDistinta } from '../api/pagamenti'
import { formatCurrency } from '../../core/utils/format'
import QuadraturaDistinta from './QuadraturaDistinta.vue'

const props = defineProps({
  visible: { type: Boolean, default: false },
  // Il DETTAGLIO della distinta (quadratura, righe per stato, la terna).
  distinta: { type: [Object, null], default: null },
  // Lo stato in cui si entra validando: codice e nome dal CATALOGO, non un
  // letterale — e' quello marcato `is_registrabile`, lo sceglie il drawer.
  statoCodice: { type: [String, null], default: null },
  statoDescrizione: { type: [String, null], default: null },
})
const emit = defineEmits(['update:visible', 'validata'])

const { t, te } = useI18n()
const { execute, loading } = useApiHandler()

// La quadratura a tre esiti e' il BB `QuadraturaDistinta`: la STESSA lettura
// del drawer, per costruzione e non per copia.

const righePerStato = computed(() => props.distinta?.righe_per_stato || [])

// ⭐ «Posso?» lo dice il flag del backend; la frase la compone il BB dalla
//    terna. `null` = il verbo non e' proposto (non dovremmo essere qui).
const bloccata = computed(() => props.distinta?.can_validare === false)
const motivoBlocco = computed(() => (
  bloccata.value ? motivoBloccoRiga(t, te, props.distinta, 'validazione_blocco') : ''
))

async function onValida() {
  if (!props.distinta || !props.statoCodice) return
  const esito = await execute(
    () => cambiaStatoDistinta(props.distinta.id, props.statoCodice),
    { successMessage: t('pagamenti.distinte.stato_cambiato') },
  )
  // ⛔ `!== null`: la regola di tutto il cantiere.
  if (esito === null) return
  emit('validata')
  emit('update:visible', false)
}
</script>

<template>
  <AppDialog
    :visible="visible"
    :header="t('pagamenti.valida.titolo', { stato: statoDescrizione || statoCodice || '' })"
    width="md"
    :loading="loading"
    :save-disabled="!distinta || bloccata"
    :save-label="t('pagamenti.valida.conferma')"
    @update:visible="(v) => emit('update:visible', v)"
    @save="onValida"
    @cancel="emit('update:visible', false)"
  >
    <div v-if="distinta" class="form-grid">
      <!-- Che cosa vuol dire validare: finito di inserire, non registrato. -->
      <Message severity="info" :closable="false" size="small">
        {{ t('pagamenti.valida.spiegazione') }}
      </Message>

      <!-- ⛔ Il motivo per cui NON si puo', dal database. Sta in cima e non in
           un tooltip: chi ha aperto il dialog deve leggere subito che cosa
           manca, non scoprirlo su un pulsante grigio. -->
      <Message v-if="bloccata" severity="warn" :closable="false">
        {{ motivoBlocco }}
      </Message>

      <!-- ══ La quadratura ══ — il BB di dominio, con le righe totali
           (il campo proprio del dialog) nello slot. -->
      <QuadraturaDistinta :distinta="distinta">
        <div class="form-field">
          <label>{{ t('pagamenti.distinte.col_righe_totali') }}</label>
          <span>{{ distinta.righe_totali ?? 0 }}</span>
        </div>
      </QuadraturaDistinta>

      <!-- ══ Le righe per stato ══
           ⭐ E' la fotografia che decide: quante ne restano da guardare,
           quante sospese (hanno un futuro: la tardiva), quante «non nostre».
           Un elenco e non una tabella: sono al piu' quanti sono gli stati del
           catalogo, e non hanno niente da ordinare o esportare. -->
      <div class="app-drawer-section">
        <h4>{{ t('pagamenti.valida.righe_per_stato') }}</h4>
      </div>
      <div v-if="righePerStato.length" class="form-grid-2col">
        <template v-for="voce in righePerStato" :key="voce.stato_codice_interno">
          <div class="form-field">
            <Tag
              :value="voce.stato_descrizione || voce.stato_codice_interno"
              :severity="statoRigaContabileSeverity(voce.stato_codice_interno)"
            />
          </div>
          <div class="form-field">
            <span>
              {{ t('pagamenti.valida.righe_e_importo', {
                n: voce.righe,
                importo: formatCurrency(voce.importo),
              }) }}
            </span>
          </div>
        </template>
      </div>
      <p v-else class="app-text-muted">{{ t('pagamenti.distinte.nessuna_riga') }}</p>
    </div>
  </AppDialog>
</template>
