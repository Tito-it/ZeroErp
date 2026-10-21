<script setup>
// Scopo: Vista Configurazione "Modelli documenti — Template" (Tranche L).
//        Pattern coerente con CategorieClientiListView: SearchTable
//        emette `new` / `row-click` -> drawer crea/edit.
//        Sopra la lista, con che cosa stampa ogni azienda
//        (`TemplateRisoluzionePannello`, brief-db-modelli-documento-standard
//        §11 F-1): si rilegge dopo ogni salvataggio, che puo' cambiarlo.
import { ref } from 'vue'
import { useDrawerState } from '../../core/composables/useDrawerState'
import { useReadonlyMode } from '../../core/composables/useReadonlyMode'
import { READONLY_DOMAINS } from '../../core/constants'
import { useTemplateDocumentiStore } from '../stores/templateDocumenti'
import TemplateDocumentiSearchTable from '../components/TemplateDocumentiSearchTable.vue'
import TemplateDocumentoDrawer from '../components/TemplateDocumentoDrawer.vue'
import TemplateRisoluzionePannello from '../components/TemplateRisoluzionePannello.vue'

const drawer = useDrawerState()
const store = useTemplateDocumentiStore()
// Il pannello della risoluzione rilegge quando questo contatore cambia.
const aggiornaRisoluzione = ref(0)

// I template documentali appartengono allo schema/area `documenti`, non
// `config` (la navigazione e' in config solo per UX/raggruppamento).
// L'area BE che enforce i permessi e' `documenti` -> coerentemente il
// readonly e i guard FE devono essere calcolati sulla stessa area.
useReadonlyMode(READONLY_DOMAINS.DOCUMENTI)

async function onDrawerSaved(result) {
  const wasCreate = drawer.state.mode === 'create'
  store.filters.offset = 0
  aggiornaRisoluzione.value += 1
  await store.fetchList()
  if (wasCreate && result?.id) {
    // Dopo il primo save la testata esiste: il drawer resta aperto in edit
    // e mostra la sezione versioni.
    drawer.state.mode = 'edit'
    drawer.state.itemId = result.id
    return
  }
  drawer.close()
}

// Scopo: pubblicata una versione nel drawer: la risoluzione e lo stato dello
//        scarto della lista sono cambiati, il drawer resta dov'e'.
async function onVersionePubblicata() {
  aggiornaRisoluzione.value += 1
  await store.fetchList()
}

// Scopo: «Personalizza» ha creato la copia di uno standard: la lista la
//        mostra, e il drawer passa sulla copia (e' li' che si lavora: la sua
//        prima versione e' una bozza da pubblicare).
async function onPersonalizzato(result) {
  store.filters.offset = 0
  aggiornaRisoluzione.value += 1
  await store.fetchList()
  if (result?.id) {
    drawer.state.mode = 'edit'
    drawer.state.itemId = result.id
  }
}
</script>

<template>
  <div class="app-page">
    <TemplateRisoluzionePannello :aggiorna="aggiornaRisoluzione" />
    <TemplateDocumentiSearchTable
      @new="drawer.openCreate"
      @row-click="(data) => drawer.editRow(data, 'id')"
    />

    <TemplateDocumentoDrawer
      :visible="drawer.state.visible"
      @update:visible="v => drawer.state.visible = v"
      :mode="drawer.state.mode"
      :record-id="drawer.state.itemId"
      @saved="onDrawerSaved"
      @personalizzato="onPersonalizzato"
      @versione-pubblicata="onVersionePubblicata"
      @cancelled="drawer.close"
    />
  </div>
</template>
