<!--
  SPDX-License-Identifier: GPL-3.0-or-later
  Copyright (C) 2026 Tid (Michele Carlo Titini)
  Doc: Vue
-->
<script setup>
// Scopo: il pannello dei PRESIDI del cantiere «nessun processo senza
//        operatore»: per ognuno quante righe ha, cosa vuol dire, e le prime.
//
// ⭐ LA NATURA DI OGNI PRESIDIO ARRIVA DAL DATABASE, non da un elenco qui. È il
//    commento della vista a dire se «DEVE restare VUOTA» o se è «un registro di
//    DEBITO che deve CALARE»: il backend lo consegna in `descrizione`, e questo
//    componente lo rende. Un elenco di eccezioni scritto nel frontend sarebbe la
//    seconda sede della stessa decisione, e la seconda diverge.
// ⛔ E per la stessa ragione NON c'è nessuna lista di «righe attese» che
//    nasconde i debiti già dichiarati: finché una vista non è mai vuota, si
//    vede che non è mai vuota. Sistemarlo è una richiesta al team DB (DB-2),
//    non un trucco di presentazione.
// ⚠️ `troncato` dice che le righe mostrate non sono tutte: senza, venti righe su
//    duecento si leggerebbero come «sono venti».
import { useI18n } from 'vue-i18n'
import Message from 'primevue/message'
import Tag from 'primevue/tag'

const { t } = useI18n()

defineProps({
  presidi: { type: Array, default: () => [] },
  loading: { type: Boolean, default: false },
  errore: { type: Boolean, default: false },
})

// Scopo: le colonne da mostrare per una riga di presidio. Le viste hanno forme
//        diverse e il pannello non le conosce: si leggono le chiavi che ci sono.
// ⛔ Nessun elenco di colonne per vista: sarebbe un terzo posto in cui la forma
//    di quelle viste è scritta, e si romperebbe alla prima colonna aggiunta.
function colonne(righe) {
  return righe.length ? Object.keys(righe[0]) : []
}

// Scopo: valore di cella leggibile — `null` non è «vuoto», è «non si applica».
function cella(valore) {
  if (valore === null || valore === undefined) return '—'
  if (typeof valore === 'boolean') return valore ? t('common.yes') : t('common.no')
  return String(valore)
}
</script>

<template>
  <div class="app-presidi">
    <Message v-if="errore" severity="error" :closable="false">
      {{ t('amministrazione.processi.presidi_errore') }}
    </Message>

    <div v-else-if="loading" class="app-presidi-vuoto">
      {{ t('common.loading') }}
    </div>

    <template v-else>
      <div v-for="p in presidi" :key="p.vista" class="app-presidio">
        <div class="app-presidio-testa">
          <span class="app-presidio-nome">{{ p.vista }}</span>
          <Tag
            :value="String(p.conteggio)"
            :severity="p.conteggio === 0 ? 'success' : 'warn'"
          />
          <span v-if="p.troncato" class="app-presidio-troncato">
            {{ t('amministrazione.processi.presidi_troncato', { n: p.righe.length }) }}
          </span>
        </div>

        <!-- ⭐ La descrizione è quella che il team DB ha scritto sulla vista:
             è lì che sta la differenza fra «deve essere zero» e «deve calare». -->
        <p v-if="p.descrizione" class="app-presidio-desc">{{ p.descrizione }}</p>

        <table v-if="p.righe.length" class="app-presidio-righe">
          <thead>
            <tr><th v-for="c in colonne(p.righe)" :key="c">{{ c }}</th></tr>
          </thead>
          <tbody>
            <tr v-for="(r, i) in p.righe" :key="i">
              <td v-for="c in colonne(p.righe)" :key="c">{{ cella(r[c]) }}</td>
            </tr>
          </tbody>
        </table>
      </div>
    </template>
  </div>
</template>

<style scoped>
/* Layout locale del pannello: non è un pattern di pagina, non va in main.css. */
.app-presidi { display: flex; flex-direction: column; gap: 1rem; }
.app-presidio {
  border: 1px solid var(--p-content-border-color);
  border-radius: var(--p-content-border-radius);
  padding: 0.75rem;
}
.app-presidio-testa { display: flex; align-items: center; gap: 0.5rem; }
.app-presidio-nome { font-weight: 600; font-family: monospace; }
.app-presidio-troncato { font-size: 0.8rem; opacity: 0.7; }
.app-presidio-desc { margin: 0.4rem 0 0.6rem; font-size: 0.85rem; opacity: 0.85; }
/* Le tabelle larghe scorrono dentro il proprio contenitore: la pagina non
   scrolla mai in orizzontale. */
.app-presidio-righe { width: 100%; display: block; overflow-x: auto; font-size: 0.8rem; }
.app-presidio-righe th, .app-presidio-righe td {
  text-align: left; padding: 0.2rem 0.5rem; white-space: nowrap;
}
.app-presidio-righe th { opacity: 0.7; font-weight: 500; }
.app-presidi-vuoto { opacity: 0.7; }
</style>
