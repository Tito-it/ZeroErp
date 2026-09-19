<!--
  SPDX-License-Identifier: GPL-3.0-or-later
  Copyright (C) 2026 Tid (Michele Carlo Titini)
  Doc: Vue
-->
<script setup>
// Scopo: il pannello dei PRESIDI — le viste che devono restare vuote: per
//        ognuna quante righe ha, cosa vuol dire, e le prime.
//
// ⭐ QUALI SIANO LE VISTE NON LO DECIDE NESSUNO DEI DUE LATI: dal 2026-09-10
//    sono quelle che il catalogo `dbops.presidi` marca di natura `ZERO`
//    (decisione di Tid). Prima erano dieci nomi scritti nel backend, e le due
//    sedi già non coincidevano.
// ⭐ LA NATURA DI OGNI PRESIDIO ARRIVA DAL DATABASE, non da un elenco qui. È il
//    commento della vista a dire se «DEVE restare VUOTA» o se è «un registro di
//    DEBITO che deve CALARE»: il backend lo consegna in `descrizione`, e questo
//    componente lo rende. Un elenco di eccezioni scritto nel frontend sarebbe la
//    seconda sede della stessa decisione, e la seconda diverge.
// ⛔ E per la stessa ragione NON c'è nessuna lista di «righe attese» che
//    nasconde i debiti già dichiarati: finché una vista non è mai vuota, si
//    vede che non è mai vuota. Sistemarlo è una richiesta al team DB (DB-2),
//    non un trucco di presentazione.
// ⛔ E un presidio NON LETTO non è uno zero: arriva con `errore` valorizzato e
//    `conteggio` a `null`, e si mostra rosso. Su questa schermata il verde vuol
//    dire «tutto a posto», e dirlo mentre non si è visto niente è il difetto
//    peggiore che possa avere.
// ⚠️ `troncato` dice che le righe mostrate non sono tutte: senza, venti righe su
//    duecento si leggerebbero come «sono venti».
// ⭐ LO SPAZIO LO PRENDE CHI CHIEDE UN OCCHIO (rilievo di Tid, 2026-09-15). Un
//    presidio acceso (righe > 0) o NON LETTO è una scheda intera: descrizione
//    e righe, perché la spiegazione va letta accanto a ciò che spiega. Un
//    presidio a zero è un chip — nome e conteggio — con la descrizione a un
//    click (`PresidioChip`). Prima ogni presidio era una scheda con la
//    descrizione intera, e il numero di presidi lo decide il catalogo DB: a
//    17 viste e ~15.000 caratteri il pannello prendeva tutta la pagina e la
//    lista dei processi finiva ad altezza zero, senza errore.
import { computed } from 'vue'
import { useI18n } from 'vue-i18n'
import Message from 'primevue/message'
import Tag from 'primevue/tag'
import PresidioChip from './PresidioChip.vue'

const { t } = useI18n()

const props = defineProps({
  presidi: { type: Array, default: () => [] },
  loading: { type: Boolean, default: false },
  errore: { type: Boolean, default: false },
})

// ⭐ «Questo presidio chiede un occhio?» lo dice la RIGA (`da_guardare`, dal
//    repository dei presidi): è la stessa domanda che la testata conta con
//    `con_righe` + `non_letti`, e qui si legge, non si ricalcola — un
//    predicato ricopiato nel client sarebbe la seconda sede, e la scheda e il
//    numero potrebbero dire due cose (regola di `api.md`: il backend
//    trasporta, il client non deduce).
const daGuardare = computed(() => props.presidi.filter((p) => p.da_guardare))
const aZero = computed(() => props.presidi.filter((p) => !p.da_guardare))

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
      <div v-for="p in daGuardare" :key="p.vista" class="app-presidio">
        <div class="app-presidio-testa">
          <span class="app-mono app-presidio-nome">{{ p.vista }}</span>
          <!-- ⛔ «NON LETTO» NON È «ZERO RIGHE», ed è l'unica differenza che
               conta su una schermata dove il verde vuol dire «tutto a posto»:
               un presidio che non si è potuto interrogare arriva col conteggio
               a `null` e il suo errore, e si mostra rosso. Renderlo come uno
               zero direbbe «tutto a posto» proprio perché siamo ciechi. -->
          <Tag
            v-if="p.errore"
            :value="t('amministrazione.processi.presidi_non_letto')"
            severity="danger"
          />
          <Tag
            v-else
            :value="String(p.conteggio)"
            :severity="p.conteggio === 0 ? 'success' : 'warn'"
          />
          <span v-if="p.troncato" class="app-presidio-troncato">
            {{ t('amministrazione.processi.presidi_troncato', { n: p.righe.length }) }}
          </span>
          <!-- ⭐ «Non elencabile» e «non c'è niente da elencare» si leggono
               uguali se non lo si dice: la vista ha un perimetro, il conteggio
               arriva dalla funzione che le righe non le restituisce apposta. -->
          <span
            v-else-if="!p.elencabili && p.conteggio > 0"
            class="app-presidio-troncato"
          >
            {{ t('amministrazione.processi.presidi_non_elencabili') }}
          </span>
        </div>

        <p v-if="p.errore" class="app-presidio-errore">{{ p.errore }}</p>

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

      <!-- I presidi a zero, tutti insieme: la striscia dice «questi sono
           coperti e vuoti», e ognuno apre la propria descrizione a un click. -->
      <div v-if="aZero.length" class="app-presidi-zero">
        <span class="app-presidi-zero-label">
          {{ t('amministrazione.processi.presidi_a_zero', { n: aZero.length }) }}
        </span>
        <PresidioChip v-for="p in aZero" :key="p.vista" :presidio="p" />
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
.app-presidio-nome { font-weight: 600; }
.app-presidio-troncato { font-size: 0.8rem; opacity: 0.7; }
.app-presidio-desc { margin: 0.4rem 0 0.6rem; font-size: 0.85rem; opacity: 0.85; }
/* Il motivo per cui un presidio non si è letto: si legge, non si attenua. */
.app-presidio-errore {
  margin: 0.4rem 0 0.2rem;
  font-size: 0.85rem;
  color: var(--app-severity-danger, var(--p-red-400));
}
/* Le tabelle larghe scorrono dentro il proprio contenitore: la pagina non
   scrolla mai in orizzontale. */
.app-presidio-righe { width: 100%; display: block; overflow-x: auto; font-size: 0.8rem; }
.app-presidio-righe th, .app-presidio-righe td {
  text-align: left; padding: 0.2rem 0.5rem; white-space: nowrap;
}
.app-presidio-righe th { opacity: 0.7; font-weight: 500; }
.app-presidi-vuoto { opacity: 0.7; }
.app-presidi-zero {
  display: flex; flex-wrap: wrap; align-items: center; gap: 0.35rem;
}
.app-presidi-zero-label { font-size: 0.85rem; opacity: 0.8; }
</style>
