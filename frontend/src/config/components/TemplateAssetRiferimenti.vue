<!--
  SPDX-License-Identifier: AGPL-3.0-or-later
  Copyright (C) 2026 Tid (Michele Carlo Titini)
-->
<script setup>
// Scopo: Gli asset che una versione di template puo' richiamare, accanto
//        all'editor HTML/CSS (brief-be-documenti-risorse-esterne-render-pdf
//        §5.2). Per ogni asset: `codice_interno`, descrizione, miniatura
//        delle immagini, e i pulsanti che inseriscono il riferimento
//        `asset:<codice_interno>` nell'HTML o nel CSS.
//
// ⭐ Mostra SOLO cio' che il render accetta oggi: gli asset dell'emittente del
//    template (nessun livello globale, §4.3) chiesti con `utilizzabili=true`.
//    Il filtro usa la STESSA condizione con cui il backend risolve `asset:`
//    nel render: un asset proposto qui non puo' essere rifiutato alla stampa
//    per scadenza o disattivazione.
// ⚠️ Il riferimento si scrive col `codice_interno`, mai col `codice`: il primo
//    non si modifica (lock del DB), il secondo e' un'etichetta che si rinomina.
// ⚠️ In sola lettura il drawer e' `app-readonly` (nessun click): i pulsanti
//    non si mostrano, il codice resta selezionabile e copiabile a mano.
//
// Non e' una lista configurabile: e' un riquadro di consultazione dentro il
// form della versione, senza colonne da scegliere ne' pagine. Se l'emittente
// ha piu' asset di quanti una pagina ne porta, il riquadro lo DICE invece di
// troncare in silenzio.
import { computed, onBeforeUnmount, ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import Button from 'primevue/button'
import Message from 'primevue/message'
import {
  listTemplateAssetDocumenti,
  miniaturaTemplateAssetDocumento,
} from '../api/templateAssetDocumenti'
import { useApiHandler } from '../../core/composables/useApiHandler'
import { useTabEvents } from '../../core/composables/useTabEvents'
import { TAB_ENTITIES } from '../../core/constants'

const props = defineProps({
  // L'emittente del template (PK `emittenti_fiscali`): il perimetro degli
  // asset che il render gli lascia vedere.
  emittenteFiscaleId: { type: [Number, null], default: null },
  readonly: { type: Boolean, default: false },
})

// `inserisci` → `{ campo: 'html_template' | 'css_template', testo }`: dove
// metterlo (al cursore) lo decide l'editor, che possiede le textarea.
const emit = defineEmits(['inserisci'])

const { t } = useI18n()
const { execute, loading } = useApiHandler()
const { onDataChanged } = useTabEvents()

// La pagina piu' grande che il backend concede (`MAX_LIMIT` di
// `core/api/constants.py`): oltre, il riquadro avvisa (`troncati`).
const PAGINA = 200

const righe = ref([])
const totale = ref(0)
const troncati = computed(() => totale.value > righe.value.length)
// id asset → object URL della miniatura. Gli URL si revocano a ogni
// ricarica e allo smontaggio, o il blob resta in memoria.
const miniature = ref({})
let caricamento = 0

// Scopo: Riferimenti da inserire, decisi dal `mime_type` (immutabile a DB):
//        un CSS si collega o si importa, un'immagine si mostra o fa da
//        sfondo, un PDF si allega. `null` = in quel campo non ha senso.
function riferimenti(asset) {
  const url = `asset:${asset.codice_interno}`
  const mime = asset.mime_type || ''
  if (mime === 'text/css') {
    return { html: `<link rel="stylesheet" href="${url}">`, css: `@import url("${url}");` }
  }
  if (mime.startsWith('image/')) {
    return { html: `<img src="${url}">`, css: `url("${url}")` }
  }
  if (mime === 'application/pdf') {
    return { html: `<link rel="attachment" href="${url}">`, css: null }
  }
  return { html: url, css: null }
}

function revocaMiniature() {
  Object.values(miniature.value).forEach((u) => URL.revokeObjectURL(u))
  miniature.value = {}
}

// Scopo: Carica gli asset utilizzabili dell'emittente, poi le miniature delle
//        immagini. Una ricarica piu' recente scarta i risultati di quella
//        vecchia (token), per non mostrare asset di un altro emittente.
async function carica() {
  const mio = ++caricamento
  revocaMiniature()
  righe.value = []
  totale.value = 0
  if (!props.emittenteFiscaleId) return
  const dati = await execute(() => listTemplateAssetDocumenti({
    emittente_fiscale_id: props.emittenteFiscaleId,
    utilizzabili: true,
    order_by: 'codice_interno',
    order_dir: 'asc',
    limit: PAGINA,
    offset: 0,
  }))
  if (mio !== caricamento || dati === null) return
  righe.value = dati.results ?? []
  totale.value = dati.count ?? righe.value.length
  await caricaMiniature(mio)
}

// Scopo: Le miniature sono un aiuto a riconoscere l'asset, non un dato: una
//        che non arriva lascia il posto vuoto, senza toast.
// ⭐ Dal 2026-10-01 si chiede la MINIATURA (`/miniatura/`, pochi KB e in
//    cache del browser), non il file intero: prima ogni apertura scaricava
//    l'originale di ogni immagine, una alla volta. Le richieste partono
//    insieme; il browser ne limita da solo il numero per server.
async function caricaMiniature(mio) {
  const immagini = righe.value.filter((a) => (a.mime_type || '').startsWith('image/'))
  await Promise.allSettled(immagini.map(async (asset) => {
    const res = await miniaturaTemplateAssetDocumento(asset.id)
    if (mio !== caricamento) return
    miniature.value = { ...miniature.value, [asset.id]: URL.createObjectURL(res.data) }
  }))
}

watch(() => props.emittenteFiscaleId, carica, { immediate: true })
// Un asset caricato o disattivato da un'altra scheda cambia cosa si puo'
// richiamare: si rilegge.
const smettiDiAscoltare = onDataChanged((evento) => {
  if (evento.entityType === TAB_ENTITIES.TEMPLATE_ASSET_DOCUMENTI) carica()
})
onBeforeUnmount(() => {
  smettiDiAscoltare()
  caricamento++
  revocaMiniature()
})
</script>

<template>
  <div class="app-preview-box">
    <div class="riferimenti-intestazione">
      <strong>{{ t('config.modelli_documenti.versioni.asset.titolo') }}</strong>
      <small class="app-text-muted">
        {{ t('config.modelli_documenti.versioni.asset.hint') }}
      </small>
    </div>

    <Message v-if="!props.emittenteFiscaleId" severity="info" :closable="false">
      {{ t('config.modelli_documenti.versioni.asset.senza_emittente') }}
    </Message>
    <small v-else-if="!loading && righe.length === 0" class="app-text-muted">
      {{ t('config.modelli_documenti.versioni.asset.nessuno') }}
    </small>

    <ul v-else class="riferimenti-elenco">
      <li v-for="asset in righe" :key="asset.id" class="riferimenti-riga">
        <span class="riferimenti-miniatura">
          <img v-if="miniature[asset.id]" :src="miniature[asset.id]" :alt="asset.descrizione">
        </span>
        <span class="riferimenti-testo">
          <code>asset:{{ asset.codice_interno }}</code>
          <small class="app-text-muted">{{ asset.descrizione }} · {{ asset.mime_type }}</small>
        </span>
        <span v-if="!props.readonly" class="riferimenti-azioni">
          <Button
            :label="t('config.modelli_documenti.versioni.asset.inserisci_html')"
            size="small" text
            @click="emit('inserisci', { campo: 'html_template', testo: riferimenti(asset).html })"
          />
          <Button
            v-if="riferimenti(asset).css"
            :label="t('config.modelli_documenti.versioni.asset.inserisci_css')"
            size="small" text
            @click="emit('inserisci', { campo: 'css_template', testo: riferimenti(asset).css })"
          />
        </span>
      </li>
    </ul>

    <Message v-if="troncati" severity="warn" :closable="false">
      {{ t('config.modelli_documenti.versioni.asset.troncati', { mostrati: righe.length, totale }) }}
    </Message>
  </div>
</template>

<style scoped>
.riferimenti-intestazione {
  display: flex;
  flex-direction: column;
  gap: 0.15rem;
  margin-bottom: 0.5rem;
}
.riferimenti-elenco {
  list-style: none;
  margin: 0;
  padding: 0;
  display: flex;
  flex-direction: column;
  gap: 0.35rem;
}
.riferimenti-riga {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  flex-wrap: wrap;
}
.riferimenti-miniatura {
  width: 2rem;
  height: 2rem;
  flex: 0 0 2rem;
  display: flex;
  align-items: center;
  justify-content: center;
  border: 1px solid var(--app-border-color);
  border-radius: var(--app-border-radius);
  background: var(--app-surface-bg);
  overflow: hidden;
}
.riferimenti-miniatura img {
  max-width: 100%;
  max-height: 100%;
}
.riferimenti-testo {
  display: flex;
  flex-direction: column;
  flex: 1 1 12rem;
  min-width: 0;
}
.riferimenti-testo code {
  word-break: break-all;
}
.riferimenti-azioni {
  display: flex;
  gap: 0.25rem;
}
</style>
