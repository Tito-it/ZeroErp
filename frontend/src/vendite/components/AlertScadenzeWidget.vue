<script setup>
// Scopo: Badge dei listini con la versione in vigore IN SCADENZA SENZA
//        SUCCESSORE, nella toolbar della lista listini. Il clic emette
//        `filtra`: chi lo monta applica il filtro `in_scadenza` alla sua lista
//        (D-1 di brief-db-liste-datatable-grezze-secondo-giro, Tid 2026-10-31:
//        il gesto che segue, creare il successore, parte dal listino).
// ⭐ La regola e il preavviso sono del DB (`vendite.fn_listini_in_scadenza_
//    senza_successore`, N dal parametro `LISTINI_SCADENZA_PREAVVISO_GIORNI`):
//    il conteggio e' il totale della lista listini filtrata, una riga.
//    ⛔ Fino al 2026-10-31 il widget aveva un endpoint suo (`alert-scadenze/`),
//    un default di 15 giorni in casa (l'altro era nel backend) e un popover
//    con una `DataTable` che ripeteva la lista: ritirati tutti e tre.
// ⭐ IL NUMERO E LE RIGHE DEVONO COINCIDERE. Il clic accende `in_scadenza`
//    SOPRA i filtri correnti della lista: il badge conta quindi con gli STESSI
//    filtri (`filtri`, li passa chi lo monta: ricerca, utility, tipologia,
//    attivo — senza paginazione, ordinamento e senza `in_scadenza` stesso).
//    ⛔ Fino al 2026-10-31 contava con il solo `in_scadenza`: il badge diceva 5
//    e il clic ne mostrava 2.
// ⭐ Quando si rilegge: alla nascita (una volta), quando cambiano i filtri, e
//    quando chi lo monta lo chiede (`load`, esposto: una versione nuova toglie
//    un listino dal conteggio). ⛔ Non a ogni pagina o ordinamento: il numero
//    non cambia. Le risposte superate si scartano (guard di sequenza): coi
//    filtri che cambiano a raffica vincerebbe l'ultima ad ARRIVARE.
import { computed, ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import { listListini } from '../api/listini'
import Badge from 'primevue/badge'
import Button from 'primevue/button'
import { STATUS_ICONS } from '../../core/constants'
import { eAccessoNegato } from '../../core/utils/apiError'

const props = defineProps({
  // I parametri di filtro della lista che lo monta (`store.paramsFiltro()`),
  // SENZA paginazione, ordinamento e `in_scadenza`: il widget aggiunge il suo.
  filtri: { type: Object, default: () => ({}) },
})
const emit = defineEmits(['filtra'])
const { t } = useI18n()

const count = ref(0)
const loading = ref(false)
// La lettura e' fallita e non ce n'e' una buona da mostrare: il widget lo DICE.
const nonVerificabile = ref(false)
// L'endpoint ha risposto 401/403: l'utente non vede i listini, e il widget
// non si mostra (non e' un errore da segnalare).
const negato = ref(false)
// C'e' stata almeno una lettura buona. ⚠️ Non e' `count > 0`: «letto, zero
// scadenze» e' un valore buono da tenere, «mai letto» no.
const letto = ref(false)

// Scopo: conta i listini in scadenza. ⛔ Su errore NON azzera: fino al
//        2026-10-31 un `catch {}` metteva il conteggio a zero e il widget
//        spariva, cioe' un errore si leggeva come «nessun listino in
//        scadenza» — il caso che il widget esiste per segnalare. Stessa regola
//        dei contatori ambientali (`usePresidiPolling`): 401/403 nasconde, ogni
//        altro errore tiene l'ultimo valore, e senza un valore buono si vede.
// ⚠️ Solo l'ULTIMA lettura partita scrive: una risposta superata (filtri
//    cambiati mentre era in volo) non tocca ne' il numero ne' gli stati.
let sequenza = 0
async function load() {
  const mia = ++sequenza
  loading.value = true
  try {
    const res = await listListini({ ...props.filtri, in_scadenza: true, limit: 1, offset: 0 })
    if (mia !== sequenza) return
    count.value = res.data.data.count || 0
    letto.value = true
    nonVerificabile.value = false
  } catch (err) {
    if (mia !== sequenza) return
    if (eAccessoNegato(err)) negato.value = true
    else nonVerificabile.value = !letto.value
  } finally {
    if (mia === sequenza) loading.value = false
  }
}

// La CHIAVE dei filtri, non l'oggetto: chi lo monta lo ricostruisce a ogni
// giro (una `computed`), e un oggetto nuovo con gli stessi valori non e' un
// filtro cambiato. `immediate`: e' anche la lettura della nascita, l'unica.
const chiaveFiltri = computed(() => JSON.stringify(props.filtri ?? {}))
watch(chiaveFiltri, load, { immediate: true })

// Chi lo monta lo rilegge quando il conteggio puo' cambiare a filtri fermi:
// una versione nuova (il successore) toglie un listino dal conteggio.
defineExpose({ load })
</script>

<template>
  <span v-if="!negato && nonVerificabile" class="alert-scadenze-widget">
    <Button type="button" :icon="STATUS_ICONS.ERRORE" severity="secondary"
      text rounded size="small" :loading="loading"
      v-tooltip.bottom="t('vendite.listini.alert_scadenze_non_verificabili')"
      :aria-label="t('vendite.listini.alert_scadenze_non_verificabili')"
      @click="load" />
  </span>
  <span v-else-if="!negato && count > 0" class="alert-scadenze-widget">
    <Button type="button" severity="warn" text rounded size="small" :loading="loading"
      v-tooltip.bottom="t('vendite.listini.alert_scadenze_filtra')"
      :aria-label="t('vendite.listini.alert_scadenze_filtra')"
      @click="emit('filtra')">
      <template #icon>
        <i :class="STATUS_ICONS.ERRORE" />
        <Badge :value="count" severity="danger" class="alert-scadenze-badge" />
      </template>
    </Button>
  </span>
</template>

<style scoped>
.alert-scadenze-widget {
  position: relative;
  display: inline-flex;
}
.alert-scadenze-badge {
  position: absolute;
  top: -4px;
  right: -4px;
  font-size: 0.65rem;
  min-width: 1.1rem;
  height: 1.1rem;
}
</style>
