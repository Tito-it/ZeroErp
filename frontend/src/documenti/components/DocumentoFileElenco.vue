<!--
  SPDX-License-Identifier: GPL-3.0-or-later
  Copyright (C) 2026 Tid (Michele Carlo Titini)
-->
<script setup>
// Scopo: I FILE di un documento generato (principale + allegati), col download
//        di ciascuno — il dettaglio inline della riga nella lista dei
//        documenti di una sorgente (`DocumentiGeneratiSorgenteList`, slot
//        `row-expansion`).
//
// ⭐ E' UN COMPONENTE E NON UN PEZZO DI TEMPLATE, ed e' cio' che rende lazy la
//    lettura senza pilotare l'espansione: il dettaglio di una riga si MONTA
//    quando la riga si apre, e il montaggio e' il momento in cui i file si
//    chiedono al backend. Fino al 2026-09-27 lo faceva il padre con
//    `@row-expand` e una cache per documento, su una `DataTable` grezza; sul
//    BB di lista l'espansione e' della lista stessa (compresa «Espandi tutte»
//    della testata), e un evento per chevron non basterebbe piu'.
// ⚠️ `versione`: il padre la incrementa dopo aver aggiunto allegati al
//    documento, e un dettaglio gia' aperto rilegge i file — senza, il nuovo
//    allegato comparirebbe solo richiudendo e riaprendo la riga.
import { onMounted, ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import { useDocumentiPerSorgenteStore } from '../stores/documentiPerSorgente'
import { useNotify } from '../../core/composables/useNotify'
import { useApiHandler } from '../../core/composables/useApiHandler'
import { downloadBlob } from '../../core/utils/download'
import { formatSize } from '../../core/utils/format'
import { MANAGE_ICONS } from '../../core/constants'
import Tag from 'primevue/tag'
import Button from 'primevue/button'

const props = defineProps({
  sorgenteCode: { type: String, required: true },
  sorgenteId: { type: Number, required: true },
  documentoId: { type: Number, required: true },
  versione: { type: Number, default: 0 },
})

const { t } = useI18n()
const notify = useNotify()
const { execute } = useApiHandler()
const azioni = useDocumentiPerSorgenteStore()

const files = ref([])
const caricamento = ref(false)

// Scopo: legge i file del documento. Un errore lascia l'elenco vuoto e lo
//        DICE (`execute`).
// ⛔ Fino al 2026-10-23 lo scriveva solo in console, «il toast lo mostra gia'
//    l'interceptor axios»: l'interceptor di `core/api.js` non mostra toast, e
//    l'operatore vedeva un elenco vuoto che sembrava una risposta.
async function carica() {
  caricamento.value = true
  try {
    azioni.setSorgente(props.sorgenteCode, props.sorgenteId)
    const data = await execute(() => azioni.listFiles(props.documentoId))
    files.value = data?.results || []
  } finally {
    caricamento.value = false
  }
}

async function scarica(fileId) {
  try {
    azioni.setSorgente(props.sorgenteCode, props.sorgenteId)
    const { blob, fileName } = await azioni.downloadFile(props.documentoId, fileId)
    downloadBlob(blob, fileName)
  } catch (err) {
    notify.error(t('documenti.genera_pdf.download_error'))
    console.error('downloadFile', err)
  }
}

onMounted(carica)
watch(() => props.versione, carica)
</script>

<template>
  <div class="documento-file-elenco">
    <div v-if="caricamento" class="app-text-muted">
      {{ t('documenti.allegati.files_loading') }}
    </div>
    <ul v-else-if="files.length" class="documento-file-elenco__lista">
      <li v-for="f in files" :key="f.id" class="documento-file-elenco__file">
        <Tag
          :value="f.is_principale
            ? t('documenti.allegati.tipo_principale')
            : t('documenti.allegati.tipo_allegato')"
          :severity="f.is_principale ? 'info' : 'secondary'"
        />
        <span class="documento-file-elenco__nome">{{ f.file_name }}</span>
        <span class="documento-file-elenco__dimensione">{{ formatSize(f.file_size_bytes) }}</span>
        <Button
          :icon="MANAGE_ICONS.DOWNLOAD"
          text
          rounded
          size="small"
          v-tooltip.top="t('documenti.lista.action_download')"
          @click="scarica(f.id)"
        />
      </li>
    </ul>
    <div v-else class="app-text-muted">
      {{ t('documenti.allegati.files_empty') }}
    </div>
  </div>
</template>

<style scoped>
.documento-file-elenco {
  padding: 0.5rem 1rem;
}
.documento-file-elenco__lista {
  list-style: none;
  margin: 0;
  padding: 0;
  display: flex;
  flex-direction: column;
  gap: 0.25rem;
}
.documento-file-elenco__file {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  padding: 0.25rem 0.5rem;
  border: 1px solid var(--app-border-color);
  border-radius: var(--app-border-radius);
}
.documento-file-elenco__nome {
  flex: 1 1 auto;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.documento-file-elenco__dimensione {
  color: var(--app-text-muted);
  font-size: 0.85rem;
}
</style>
