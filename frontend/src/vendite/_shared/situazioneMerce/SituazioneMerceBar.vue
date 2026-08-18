<script setup>
// Scopo: Riga «situazione merce» nei drawer ordine e DDT — il RIASSUNTO IN
// TESTATA deciso al §5.2 del brief pannello: una riga sola che dice SE c'e'
// qualcosa di aperto, e da cui si apre il dettaglio.
//
// Sta sotto `DocumentoCollegamentiBar`, e le due si completano: quella dice
// COSA c'e' collegato («Ordine · 2 DDT · Reso»), questa dice COM'E' ANDATA
// («8 da accreditare · 3 da riconsegnare»). Erano il rilievo in-app di Tid del
// 2026-08-17: *«se si vuole avere la situazione di un ordine non si capisce
// nulla di quello che e' successo»* — cinque schermate per ricostruire una
// storia, e la riga che la riassume non esisteva.
//
// ⭐ PERCHE' IN TESTATA E NON UNA TABELLA SEMPRE VISIBILE (§5.2): su un ordine
// SANO non occupa spazio e non aggiunge rumore; su uno con pendenze si nota
// subito, che e' l'unico momento in cui serve. Sette colonne accanto alle righe
// d'ordine sarebbero una seconda tabella da leggere, e la si smette di guardare.
//
// ⚠️ REGOLA DI SVUOTAMENTO — ed e' l'opposto di quella dei collegamenti. La riga
// NON sparisce quando non c'e' nulla di aperto: mostra «tutto regolare». Il
// §5.2 lo chiede espressamente — «tutto regolare deve essere VISIBILMENTE
// diverso da non ancora calcolato» — e una riga assente e' ambigua fra le due.
// Sparisce solo quando non c'e' NIENTE da raccontare: documento senza merce
// (un DDT in bozza non ha ancora partite, soglia EMESSO) o dati non arrivati.
import { computed, ref } from 'vue'
import { useI18n } from 'vue-i18n'
import Tag from 'primevue/tag'
import SituazioneMerceDialog from './SituazioneMerceDialog.vue'
import { formatQtaMerce as qta, sintesiSituazioneMerce } from './situazioneMerceSintesi'
import { useSituazioneMerce } from './useSituazioneMerce'

const props = defineProps({
  // Path lista API del dominio ('/vendite/ordini' | '/vendite/ddt').
  basePath: { type: String, required: true },
  // Pk di dominio (null in CREATE: nessuna fetch, nessuna riga).
  docId: { type: Number, default: null },
  // Readonly PURO del chiamante (permessi area / split), NON il lock-di-stato
  // del documento: la dialog e' consultiva e deve aprirsi anche su un
  // documento post-DRAFT, che e' il caso normale qui — la merce si muove dopo
  // l'emissione. Stessa ragione di DdtResoDialog.
  readonly: { type: Boolean, default: false },
})

const { t } = useI18n()

// Fetch unica condivisa con la dialog (che non fetcha: si apre istantanea).
const { sezioni, loaded, loading, reload } = useSituazioneMerce(
  () => props.basePath,
  () => props.docId,
)
// I drawer ricaricano dopo un'azione che cambia la merce (evasione, push,
// creazione reso, ri-spedizione): `reload` e' il loro aggancio.
defineExpose({ reload })

const s = computed(() => sintesiSituazioneMerce(sezioni.value))

// I compiti, nell'ordine in cui contano per chi guarda: prima quello che
// costa denaro (accreditare), poi quello che lo incassa (fatturare), poi la
// logistica, infine cio' che va solo GUARDATO.
//
// ⚠️ `fatturato_anticipato` NON e' in questa lista (FE-3): non e' un compito,
// e metterlo qui accanto a «da accreditare» e' esattamente il modo in cui
// tornerebbe a essere letto come tale. Vive nel dettaglio, dichiarato.
const chips = computed(() => {
  const v = s.value
  const out = []
  if (v.daAccreditare > 0) {
    out.push({ key: 'accreditare', severity: 'warn',
               label: t('vendite.situazione_merce.chip_da_accreditare', { n: qta(v.daAccreditare) }) })
  }
  if (v.daFatturare > 0) {
    out.push({ key: 'fatturare', severity: 'info',
               label: t('vendite.situazione_merce.chip_da_fatturare', { n: qta(v.daFatturare) }) })
  }
  if (v.daRiconsegnare > 0) {
    out.push({ key: 'riconsegnare', severity: 'info',
               label: t('vendite.situazione_merce.chip_da_riconsegnare', { n: qta(v.daRiconsegnare) }) })
  }
  if (v.daSpedire > 0) {
    out.push({ key: 'spedire', severity: 'secondary',
               label: t('vendite.situazione_merce.chip_da_spedire', { n: qta(v.daSpedire) }) })
  }
  // FE-1: «non calcolabile» e' rosso, non grigio — deve staccarsi da «tutto
  // regolare» e dal «non si applica», che sono sani.
  if (v.nonMisurabili > 0) {
    out.push({ key: 'non-misurabile', severity: 'danger',
               label: t('vendite.situazione_merce.chip_non_misurabile', { n: v.nonMisurabili }) })
  }
  // FE-2: senza questo chip l'avviso di S6b non esiste per nessuno.
  if (v.sospette > 0) {
    out.push({ key: 'sospette', severity: 'warn',
               label: t('vendite.situazione_merce.chip_sospette', { n: v.sospette }) })
  }
  return out
})

// La riga si mostra solo con dati ARRIVATI e qualcosa da dire. `loaded` e' la
// difesa contro il vuoto positivo: su una fetch fallita non si afferma nulla.
const visibile = computed(() => loaded.value && (s.value.haPendenze || s.value.tuttoRegolare))

const dialogVisible = ref(false)
</script>

<template>
  <div v-if="visibile" class="app-merce-bar">
    <span class="app-merce-label">{{ t('vendite.situazione_merce.etichetta') }}</span>

    <button
      v-if="s.tuttoRegolare"
      type="button"
      class="app-merce-chip"
      v-tooltip.bottom="t('vendite.situazione_merce.apri')"
      @click="dialogVisible = true"
    >
      <Tag severity="success" icon="pi pi-check" :value="t('vendite.situazione_merce.tutto_regolare')" />
    </button>

    <button
      v-for="chip in chips"
      :key="chip.key"
      type="button"
      class="app-merce-chip"
      v-tooltip.bottom="t('vendite.situazione_merce.apri')"
      @click="dialogVisible = true"
    >
      <Tag :severity="chip.severity" :value="chip.label" />
    </button>
  </div>

  <SituazioneMerceDialog
    v-model:visible="dialogVisible"
    :sezioni="sezioni"
    :loading="loading"
    :loaded="loaded"
    :readonly="readonly"
  />
</template>

<style scoped>
.app-merce-bar {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  flex-wrap: wrap;
  margin-top: 0.5rem;
}

/* Glifo, non controllo: l'etichetta arretra (vedi frontend-standards
   §"Glifo vs controllo") — i controlli sono i chip. */
.app-merce-label {
  color: var(--app-text-muted);
  font-size: var(--app-font-size-sm);
}

/* Chip = controllo vero (button), non un Tag con @click: hit-area, focus da
   tastiera e ruolo semantico corretti. Identico ad app-collegamento-chip. */
.app-merce-chip {
  background: none;
  border: 0;
  padding: 0;
  cursor: pointer;
  line-height: 0;
  border-radius: var(--p-border-radius-sm, 4px);
}

.app-merce-chip:focus-visible {
  outline: 2px solid var(--app-icon-color);
  outline-offset: 2px;
}

.app-merce-chip:hover :deep(.p-tag) {
  filter: brightness(0.95);
}
</style>
