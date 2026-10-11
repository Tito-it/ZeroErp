<!--
  SPDX-License-Identifier: GPL-3.0-or-later
  Copyright (C) 2026 Tid (Michele Carlo Titini)
-->
<script setup>
// Scopo: LA CONFERMA DELL'ANNULLO DI UN DOCUMENTO CON LEGAMI — bolla, ordine,
//        preventivo, contratto (brief-db-annullo-documento-con-legami R-1).
//        Annullare un documento che ha consumato qualcosa di altri documenti
//        (la merce di un ordine o di un reso, le righe di un preventivo, righe
//        di commessa da emettere) o che nasce da un'offerta riapre quelle
//        cose. Per decisione di Tid non succede in silenzio.
// ⭐ Il giro e' quello di `useForzaturaConfermata` (il chiamante lo possiede):
//    1° tentativo senza dichiarazione -> il DB rifiuta (E_DOC_ANNULLO_CON_LEGAMI,
//    `confirm_and_retry`) -> qui si elencano i legami -> la conferma DICHIARA
//    quanti legami si sono visti (`legami_confermati`). Se nel frattempo sono
//    cambiati il DB chiede di nuovo: arriva una `domanda` NUOVA (identita'
//    diversa) e l'elenco si rilegge.
// ⭐ Regola del 2: e' nato per la bolla (`DdtAnnulloLegamiDialog`, D-8 di
//    brief-db-ddt-righe-evase-dall-ordine) e alla seconda finestra e' diventato
//    questo componente; la copia della bolla si e' ritirata.
// ⛔ Il numero dichiarato e' quello LETTO qui (`GET …/legami/`), mai un valore
//    preso dal messaggio o tenuto da prima: dichiarare cio' che non si e' visto
//    svuoterebbe la conferma. Conta i LEGAMI (`count(*)` del lettore del DB),
//    non le righe del documento: una riga di ri-consegna ne porta due.
// ⭐ Se fra la domanda del DB e la lettura i legami sono spariti (un'altra
//    sessione li ha ritirati), qui si legge ZERO: non c'e' niente da
//    dichiarare, e la conferma ripete SENZA dichiarazione — il documento senza
//    legami il DB lo annulla al primo colpo. Se nel frattempo i legami sono
//    tornati, il DB chiede di nuovo e l'elenco si rilegge.
// ⚠️ Il nome del documento dall'altra parte lo da' il lineage (decisione di
//    Tid): se non lo vede, la riga mostra il solo tipo, senza link.
import { computed, ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import Button from 'primevue/button'
import Message from 'primevue/message'

import AppDialog from '../../../core/components/AppDialog.vue'
import DocumentoDrawerHost from '../../../core/components/DocumentoDrawerHost.vue'
import { useApiHandler } from '../../../core/composables/useApiHandler'
import { useDocumentoDrawer } from '../../../core/composables/useDocumentoDrawer'
import { formatNumber } from '../../../core/utils/format'
import { labelOrCode } from '../../../core/utils/i18nLabel'
import { lineageDocumentoLabel } from '../lineage/lineageLabels'
import { getLegami } from './legamiApi'

const props = defineProps({
  visible: { type: Boolean, default: false },
  // Il path lista del dominio (es. '/vendite/ordini') e l'id del documento.
  basePath: { type: String, required: true },
  docId: { type: Number, required: true },
  // Il nome dell'azione che ha aperto la finestra («Annulla ordine»): titolo e
  // pulsante dicono la stessa parola del pulsante premuto.
  header: { type: String, required: true },
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

// ⚠️ La risposta vale solo per la domanda che l'ha chiesta: se nel frattempo ne
//    e' arrivata una nuova (o la finestra si e' chiusa), quella vecchia si
//    scarta — altrimenti si dichiarerebbe un conteggio letto per un'altra domanda.
watch(() => props.domanda, async (domanda) => {
  dati.value = null
  if (!domanda) return
  const letti = await execute(() => getLegami(props.basePath, props.docId))
  if (props.domanda === domanda) dati.value = letti
}, { immediate: true })

const righe = computed(() => dati.value?.righe ?? [])

// I legami sono spariti dopo la domanda: si annulla senza dichiarare niente.
const senzaLegami = computed(() => dati.value != null && !dati.value.legami)

// Scopo: il documento dall'altra parte, a parole: tipo dal lineage (o, se il
//        lineage non lo vede, dall'origine del legame) e codice.
function documentoLabel(l) {
  const tipo = l.origine_tipo_codice_interno
    ? lineageDocumentoLabel(t, te, l.origine_tipo_codice_interno, null)
    : labelOrCode(t, te, `vendite.annullo_legami.origine_${String(l.origine ?? '').toLowerCase()}`, l.origine)
  return l.origine_codice ? `${tipo} ${l.origine_codice}` : tipo
}

// Scopo: che cosa si riapre, dopo il nome del documento. Tre forme, dalla
//        natura e dalla riga: la PROVENIENZA (l'offerta torna trasformabile),
//        il consumo di una RIGA (quantita' da spedire, righe da ordinare), il
//        consumo SENZA riga (righe di commessa da emettere).
function cosaSiRiapre(l) {
  if (l.natura === 'PROVENIENZA') return t('vendite.annullo_legami.provenienza')
  if (l.riga_nr == null) return t('vendite.annullo_legami.commessa')
  if (l.qta == null) return t('vendite.annullo_legami.riga_senza_qta', { riga: l.riga_nr })
  return t('vendite.annullo_legami.riga', {
    riga: l.riga_nr,
    qta: formatNumber(l.qta, { maximumFractionDigits: 6 }),
  })
}

function apribile(l) {
  return l.origine_tipo_codice_interno != null && l.origine_id != null && l.origine_codice != null
}

// Gesto «vai a»: il drawer del documento dall'altra parte, impilato sopra.
const {
  visible: docDrawerVisible,
  tipo: docDrawerTipo,
  id: docDrawerId,
  apri: apriDocumento,
} = useDocumentoDrawer()

function onConferma() {
  emit('conferma', senzaLegami.value ? {} : { legami_confermati: dati.value.legami })
}
</script>

<template>
  <!-- conferma-uscita: nessuna — non ci sono campi: si conferma o si rinuncia. -->
  <AppDialog
    :visible="visible"
    :header="header"
    width="md"
    :loading="loading || caricamento"
    :save-disabled="!dati"
    :save-label="header"
    save-severity="danger"
    @save="onConferma"
    @cancel="emit('cancel')"
  >
    <div class="form-grid">
      <!-- La frase del DB: nomina gia' il documento e il numero di legami. -->
      <Message v-if="!senzaLegami" severity="warn" :closable="false">{{ domanda?.messaggio }}</Message>
      <!-- La frase del DB non vale piu': i legami che contava non ci sono. -->
      <Message v-else severity="info" :closable="false">
        {{ t('vendite.annullo_legami.nessun_legame') }}
      </Message>

      <div v-if="righe.length" class="form-field">
        <label>{{ t('vendite.annullo_legami.righe') }}</label>
        <ul class="app-annullo-legami-lista">
          <li v-for="(l, i) in righe" :key="`${l.origine}-${l.origine_id}-${l.origine_riga_id}-${i}`">
            <Button v-if="apribile(l)" link class="app-annullo-legami-link"
              :label="documentoLabel(l)"
              v-tooltip.top="t('vendite.lineage.apri_documento')"
              @click="apriDocumento(l.origine_tipo_codice_interno, l.origine_id)" />
            <span v-else>{{ documentoLabel(l) }}</span>
            · {{ cosaSiRiapre(l) }}
          </li>
        </ul>
      </div>

      <small v-if="!senzaLegami" class="app-field-hint">{{ t('vendite.annullo_legami.spiegazione') }}</small>
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

/* Il link del documento resta in linea col testo della riga. */
.app-annullo-legami-link {
  padding: 0;
}
</style>
