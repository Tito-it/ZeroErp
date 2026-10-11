<!--
  SPDX-License-Identifier: GPL-3.0-or-later
  Copyright (C) 2026 Tid (Michele Carlo Titini)
-->
<script setup>
// Scopo: LA CONFERMA DELL'ANNULLO DI UNA BOLLA CON LEGAMI (D-8 di
//        brief-db-ddt-righe-evase-dall-ordine, lavorato in
//        brief-db-annullo-documento-con-legami §3). Annullare la bolla ritira i
//        legami delle sue righe con ordini e resi: l'ordine torna da evadere, il
//        reso da ri-consegnare. Per decisione di Tid non succede in silenzio.
// ⭐ Il giro e' quello di `useForzaturaConfermata` (il chiamante lo possiede):
//    1° tentativo senza dichiarazione -> il DB rifiuta (E_DDT_ANNULLO_CON_LEGAMI,
//    `confirm_and_retry`) -> qui si elencano le righe -> la conferma DICHIARA
//    quante righe legate si sono viste (`righe_legate`). Se nel frattempo sono
//    cambiate il DB chiede di nuovo: arriva una `domanda` NUOVA (identita'
//    diversa) e l'elenco si rilegge.
// ⛔ Il numero dichiarato e' quello LETTO qui (`GET …/legami/`), mai un valore
//    preso dal messaggio o tenuto da prima: dichiarare cio' che non si e' visto
//    svuoterebbe la conferma.
// ⭐ Se fra la domanda del DB e la lettura i legami sono spariti (un'altra
//    sessione ha tolto le righe), qui si legge ZERO: non c'e' niente da
//    dichiarare, e la conferma ripete SENZA dichiarazione — la bolla senza
//    legami il DB la annulla al primo colpo. Se nel frattempo i legami sono
//    tornati, il DB chiede di nuovo e l'elenco si rilegge. Prima il pulsante
//    restava spento e l'operatore doveva chiudere e riprovare.
// ⚠️ Le origini sono a livello di testata (il lineage risponde «da quali
//    documenti viene la bolla»): la riga dice solo se e' legata a un ordine o a
//    un reso, il documento si apre dalle origini.
import { computed, ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import Button from 'primevue/button'
import Message from 'primevue/message'

import AppDialog from '../../../../core/components/AppDialog.vue'
import DocumentoDrawerHost from '../../../../core/components/DocumentoDrawerHost.vue'
import { useApiHandler } from '../../../../core/composables/useApiHandler'
import { useDocumentoDrawer } from '../../../../core/composables/useDocumentoDrawer'
import { formatNumber } from '../../../../core/utils/format'
import { labelOrCode } from '../../../../core/utils/i18nLabel'
import { lineageDocumentoLabel } from '../../../_shared/lineage/lineageLabels'
import { getDdtLegami } from '../../api/ddtApi'

const props = defineProps({
  visible: { type: Boolean, default: false },
  ddtId: { type: Number, required: true },
  // La domanda in sospeso di `useForzaturaConfermata` (`{ messaggio }`): una
  // domanda nuova = rileggere.
  domanda: { type: [Object, null], default: null },
  // Il salvataggio in volo e' del chiamante (la conferma ripete la sua chiamata).
  loading: { type: Boolean, default: false },
})
const emit = defineEmits(['conferma', 'cancel'])

const { t, te } = useI18n()
const { execute, loading: caricamento } = useApiHandler()

const dati = ref(null)

watch(() => props.domanda, async (domanda) => {
  dati.value = null
  if (!domanda) return
  dati.value = await execute(() => getDdtLegami(props.ddtId))
}, { immediate: true })

const righe = computed(() => dati.value?.legami ?? [])
const origini = computed(() => dati.value?.origini ?? [])

function origineLabel(origine) {
  return labelOrCode(
    t, te, `vendite.ddt.annullo_legami.origine_${String(origine ?? '').toLowerCase()}`, origine,
  )
}

// Gesto «vai a»: il drawer del documento d'origine, impilato sopra.
const {
  visible: docDrawerVisible,
  tipo: docDrawerTipo,
  id: docDrawerId,
  apri: apriDocumento,
} = useDocumentoDrawer()

// I legami sono spariti dopo la domanda: si annulla senza dichiarare niente.
const senzaLegami = computed(() => dati.value != null && !dati.value.righe_legate)

function onConferma() {
  emit('conferma', senzaLegami.value ? {} : { righe_legate_confermate: dati.value.righe_legate })
}
</script>

<template>
  <!-- conferma-uscita: nessuna — non ci sono campi: si conferma o si rinuncia. -->
  <AppDialog
    :visible="visible"
    :header="t('vendite.ddt.azione_annulla')"
    width="md"
    :loading="loading || caricamento"
    :save-disabled="!dati"
    :save-label="t('vendite.ddt.azione_annulla')"
    save-severity="danger"
    @save="onConferma"
    @cancel="emit('cancel')"
  >
    <div class="form-grid">
      <!-- La frase del DB: nomina gia' la bolla e il numero di righe. -->
      <Message v-if="!senzaLegami" severity="warn" :closable="false">{{ domanda?.messaggio }}</Message>
      <!-- La frase del DB non vale piu': le righe che contava non sono legate. -->
      <Message v-else severity="info" :closable="false">
        {{ t('vendite.ddt.annullo_legami.nessun_legame') }}
      </Message>

      <div v-if="righe.length" class="form-field">
        <label>{{ t('vendite.ddt.annullo_legami.righe') }}</label>
        <ul class="app-annullo-legami-lista">
          <li v-for="l in righe" :key="`${l.ddt_riga_id}-${l.origine}`">
            {{ t('vendite.ddt.annullo_legami.riga', {
              riga: l.riga_nr,
              origine: origineLabel(l.origine),
              qta: formatNumber(l.qta, { maximumFractionDigits: 6 }),
            }) }}
          </li>
        </ul>
      </div>

      <div v-if="origini.length" class="form-field">
        <label>{{ t('vendite.ddt.annullo_legami.origini') }}</label>
        <div class="app-annullo-legami-origini">
          <Button v-for="o in origini" :key="`${o.tipo_codice_interno}-${o.doc_id}`"
            :label="`${lineageDocumentoLabel(t, te, o.tipo_codice_interno, null)} ${o.codice ?? ''}`"
            severity="secondary" size="small" text
            :disabled="o.doc_id == null"
            v-tooltip.top="t('vendite.lineage.apri_documento')"
            @click="apriDocumento(o.tipo_codice_interno, o.doc_id)" />
        </div>
      </div>

      <small v-if="!senzaLegami" class="app-field-hint">{{ t('vendite.ddt.annullo_legami.spiegazione') }}</small>
    </div>
  </AppDialog>

  <DocumentoDrawerHost
    v-model:visible="docDrawerVisible"
    :tipo-codice="docDrawerTipo"
    :doc-id="docDrawerId" />
</template>

<style scoped>
.app-annullo-legami-lista {
  margin: 0;
  padding-left: 1.25rem;
}

.app-annullo-legami-origini {
  display: flex;
  flex-wrap: wrap;
  gap: 0.25rem;
}
</style>
