<!--
  SPDX-License-Identifier: AGPL-3.0-or-later
  Copyright (C) 2026 Tid (Michele Carlo Titini)
-->
<script setup>
// Scopo: «COPIA COME…» — la scelta dei tipi in cui copiare un indirizzo (R-4 di
//        brief-db-copia-indirizzo-soggetto, 2026-11-15). I tipi sono quelli del
//        picker del DB (`fn_tipi_indirizzo_proponibili_*`): gli ammessi si
//        scelgono, gli altri restano VISIBILI, spenti con la loro frase (il
//        tipo gia' presente, quello che la natura o il ruolo non prevede).
//        Presentazione sola: chi apre il dialog carica i tipi e chiama il verbo
//        (emit `confirm` con i codici, nell'ordine dell'elenco).
// ⭐ La frase del tipo spento e' la `reason_key` coi `reason_valori` posizionali
//    (`{0}`, `{1}`), dal BB `testoMotivi`: il ripiego senza chiave e' `reason`.
import { computed, ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import Checkbox from 'primevue/checkbox'
import AppDialog from '../../core/components/AppDialog.vue'
import { testoMotivi } from '../../core/composables/useDrawerActions'
import { useFotografiaDialog } from '../../core/composables/useFotografiaDialog'

const props = defineProps({
  visible: { type: Boolean, default: false },
  // Le righe del picker: { codice_interno, descrizione, ammesso, reason, reason_key, reason_valori }.
  tipi: { type: Array, default: () => [] },
  // La descrizione del tipo dell'indirizzo che si copia, per il titolo.
  sorgente: { type: String, default: '' },
  loading: { type: Boolean, default: false },
})
const emit = defineEmits(['update:visible', 'confirm'])

const { t, te } = useI18n()
const scelti = ref([])

// All'apertura nessun tipo scelto: la copia e' un gesto esplicito.
watch(() => props.visible, (v) => { if (v) scelti.value = [] })

// D-14: uscire con dei tipi spuntati chiede (AppDialog `conferma-uscita`). La
// fotografia si prende dopo il reset qui sopra (nextTick del BB).
const fotografia = useFotografiaDialog(() => ({ scelti: [...scelti.value] }), { visibile: () => props.visible })

// La frase dal BB `testoMotivi` (sede unica del perche' di un'azione negata):
// il picker chiama `reason_valori` cio' che il BB legge come `valori`.
function motivo(tipo) {
  if (tipo.ammesso) return ''
  return testoMotivi(t, te, {
    reason: tipo.reason, reason_key: tipo.reason_key, valori: tipo.reason_valori,
  })
}

function onSave() {
  const ordine = props.tipi.map(r => r.codice_interno)
  emit('confirm', ordine.filter(c => scelti.value.includes(c)))
}

const header = computed(() => props.sorgente
  ? t('anagrafiche.indirizzi.copia.titolo_da', { tipo: props.sorgente })
  : t('anagrafiche.indirizzi.copia.titolo'))
</script>

<template>
  <AppDialog
    :conferma-uscita="fotografia.chiudiConConferma"
    :visible="visible"
    :header="header"
    width="sm"
    :loading="loading"
    :save-disabled="scelti.length === 0"
    :save-label="t('anagrafiche.indirizzi.copia.conferma')"
    @update:visible="(v) => emit('update:visible', v)"
    @save="onSave"
  >
    <p class="copia-spiegazione">{{ t('anagrafiche.indirizzi.copia.spiegazione') }}</p>
    <div class="copia-tipi">
      <div v-for="tipo in tipi" :key="tipo.codice_interno" class="copia-tipo">
        <Checkbox
          v-model="scelti"
          :input-id="`copia-${tipo.codice_interno}`"
          :value="tipo.codice_interno"
          :disabled="!tipo.ammesso || loading"
        />
        <label :for="`copia-${tipo.codice_interno}`" :class="{ 'copia-tipo-spento': !tipo.ammesso }">
          {{ tipo.descrizione }}
          <span v-if="!tipo.ammesso" class="copia-tipo-motivo">{{ motivo(tipo) }}</span>
        </label>
      </div>
    </div>
  </AppDialog>
</template>

<style scoped>
.copia-spiegazione {
  margin: 0 0 0.75rem;
}

.copia-tipi {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
}

.copia-tipo {
  display: flex;
  align-items: flex-start;
  gap: 0.5rem;
}

.copia-tipo-spento {
  color: var(--app-text-muted);
}

.copia-tipo-motivo {
  display: block;
  font-size: 0.85em;
}
</style>
