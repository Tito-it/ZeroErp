<!--
  SPDX-License-Identifier: AGPL-3.0-or-later
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
// ⭐ PRIMA COSA FARE, POI COSA VUOL DIRE, POI A CHI TOCCA (brief-db-presidi-
//    cosa-significa-cosa-fare §6, 2026-10-06). Il commento della vista è scritto
//    per chi MANTIENE il presidio; chi legge questa schermata deve AGIRE, e ha
//    due domande sole. Il testo per lui arriva dal catalogo (`azione`,
//    `significato`, `chi_agisce`): la descrizione di prima resta, chiusa, sotto
//    «Dettaglio tecnico». ⛔ Senza testo (presidio non ancora tradotto per chi
//    agisce) si ripiega sulla descrizione aperta, com'era: mai sul vuoto.
// ⭐ PER CAUSA (2026-10-10, brief-db-presidio-processi-testo-per-causa §5.4.3).
//    Dove le righe di un presidio sono guasti diversi, il backend le consegna
//    raggruppate in `cause`, ognuna col suo rimedio e il suo «chi agisce»; il
//    testo del presidio in testa resta, ed è quello neutro. ⭐ Le cause sono
//    TUTTE quelle accese, ognuna col suo `conteggio` (R-2, §6.4.4): anche una
//    causa senza righe fra quelle mostrate, o su una vista che non si elenca.
import { computed } from 'vue'
import { useI18n } from 'vue-i18n'
import Message from 'primevue/message'
import Tag from 'primevue/tag'
import PresidioChip from './PresidioChip.vue'
import { displayDate, displayTimestamp } from '../../core/utils/date'

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

// Scopo: il badge di CHI SPEGNE il presidio, per ognuno dei tre valori del
//        `CHECK chk_presidi_chi_agisce`. La frase e il colore sono
//        presentazione; il valore lo decide il catalogo.
// ⚠️ Un valore che questa mappa non conosce non ha badge, ma l'azione resta a
//    video: il badge aggiunge «a chi tocca», non è la notizia.
const CHI_AGISCE = {
  AMMINISTRATORE: { labelKey: 'amministrazione.processi.chi_agisce.amministratore', severity: 'info' },
  SISTEMISTA: { labelKey: 'amministrazione.processi.chi_agisce.sistemista', severity: 'warn' },
  SVILUPPO: { labelKey: 'amministrazione.processi.chi_agisce.sviluppo', severity: 'secondary' },
}

function chiAgisce(p) {
  return CHI_AGISCE[p.chi_agisce] ?? null
}

// Scopo: c'è il testo per chi agisce? Se sì la descrizione diventa il
//        dettaglio tecnico, chiuso; se no è l'unica spiegazione, e resta aperta.
function haTesto(p) {
  return Boolean(p.azione || p.significato)
}

// Scopo: le righe del presidio PER CAUSA, quando il backend le consegna così
//        (`cause`, brief-db-presidio-processi-testo-per-causa §5.4.3): le righe
//        di quei presidi sono guasti diversi, e il rimedio sta accanto a
//        ciascuno. Senza cause, un gruppo solo con tutte le righe.
// ⛔ Il raggruppamento lo fa il backend: qui non si legge nessuna colonna per
//    nome — quale sia la colonna della causa lo dice il catalogo, e il client
//    non lo sa.
function perCausa(p) {
  return Boolean(p.cause?.length)
}

function gruppiRighe(p) {
  return perCausa(p) ? p.cause : [{ righe: p.righe }]
}

// Scopo: le colonne da mostrare per una riga di presidio. Le viste hanno forme
//        diverse e il pannello non le conosce: si leggono le chiavi che ci sono.
// ⛔ Nessun elenco di colonne per vista: sarebbe un terzo posto in cui la forma
//    di quelle viste è scritta, e si romperebbe alla prima colonna aggiunta.
function colonne(righe) {
  return righe.length ? Object.keys(righe[0]) : []
}

// Scopo: la forma con cui il JSON trasporta un istante (`2026-10-09T13:47:54.044Z`,
//        o con lo scostamento `+02:00`) e un giorno di calendario (`2026-10-09`).
// ⚠️ Le colonne delle viste non hanno un tipo dichiarato qui (forme diverse per
//    vista): il tipo si riconosce dalla FORMA, ed è affidabile perché la
//    scrive il serializzatore del backend. ⛔ Senza fuso non è un istante: una
//    stringa «ingenua» si lascia com'è, invece di leggerla in un fuso inventato.
const ISTANTE = /^\d{4}-\d{2}-\d{2}[T ]\d{2}:\d{2}(:\d{2}(\.\d+)?)?(Z|[+-]\d{2}(:?\d{2})?)$/
const GIORNO = /^\d{4}-\d{2}-\d{2}$/

// Scopo: valore di cella leggibile — `null` non è «vuoto», è «non si applica».
// ⭐ Un istante si legge nell'ora dell'AZIENDA col BB delle date, come nel
//    digest: fino al 2026-10-10 qui usciva grezzo, in UTC e in ISO.
function cella(valore) {
  if (valore === null || valore === undefined) return '—'
  if (typeof valore === 'boolean') return valore ? t('common.yes') : t('common.no')
  if (typeof valore === 'string') {
    if (ISTANTE.test(valore)) return displayTimestamp(valore)
    if (GIORNO.test(valore)) return displayDate(valore)
  }
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
      <!-- ⭐ Le schede da guardare scorrono DA SOLE: la striscia dei presidi a
           zero sta sotto, fuori dallo scroll. Con uno scroll unico il dettaglio
           di un errore divideva il tetto della sezione col riepilogo, e non si
           leggeva per intero (rilievo di Tid, 2026-10-14). -->
      <div v-if="daGuardare.length" class="app-presidi-schede">
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

          <!-- ⭐ Per chi agisce: prima cosa fare, poi cosa vuol dire, poi a chi
               tocca. -->
          <p v-if="p.azione" class="app-presidio-azione">{{ p.azione }}</p>
          <p v-if="p.significato" class="app-presidio-significato">{{ p.significato }}</p>
          <Tag
            v-if="chiAgisce(p)"
            class="app-presidio-chi"
            :value="t(chiAgisce(p).labelKey)"
            :severity="chiAgisce(p).severity"
          />

          <!-- ⭐ La descrizione è quella che il team DB ha scritto sulla vista,
               per chi mantiene il presidio. Accanto al testo per chi agisce è il
               dettaglio tecnico, chiuso; da sola è l'unica spiegazione, aperta.
               ⚠️ `<details>` nativo: apertura, tastiera e lettore di schermo
               senza una riga di stato da tenere. -->
          <details v-if="p.descrizione && haTesto(p)" class="app-presidio-dettaglio">
            <summary>{{ t('amministrazione.processi.presidi_dettaglio_tecnico') }}</summary>
            <p class="app-presidio-desc">{{ p.descrizione }}</p>
          </details>
          <p v-else-if="p.descrizione" class="app-presidio-desc">{{ p.descrizione }}</p>

          <!-- ⭐ Per causa, quando il presidio le ha: ogni gruppo di righe col
               SUO rimedio e il SUO «chi agisce» sopra. Senza cause, un gruppo
               solo senza titolo: la tabella è la stessa, scritta una volta. -->
          <div
            v-for="(g, gi) in gruppiRighe(p)"
            :key="g.causa ?? `gruppo-${gi}`"
            :class="{ 'app-presidio-causa': perCausa(p) }"
          >
            <template v-if="perCausa(p)">
              <div class="app-presidio-testa">
                <span class="app-mono app-presidio-nome">
                  {{ g.causa ?? t('amministrazione.processi.presidi_causa_non_indicata') }}
                </span>
                <Tag
                  class="app-presidio-causa-conteggio"
                  :value="String(g.conteggio)"
                  severity="warn"
                />
                <Tag
                  v-if="chiAgisce(g)"
                  :value="t(chiAgisce(g).labelKey)"
                  :severity="chiAgisce(g).severity"
                />
                <!-- ⚠️ Le righe mostrate sono un campione del presidio: una causa
                     può averne meno del suo conteggio, anche nessuna. Senza
                     dirlo, tre righe su sette si leggerebbero «sono tre». Su una
                     vista non elencabile lo dice già la testa del presidio. -->
                <span
                  v-if="p.elencabili && g.righe.length < g.conteggio"
                  class="app-presidio-troncato"
                >
                  {{ t('amministrazione.processi.presidi_causa_mostrate', { n: g.righe.length, tot: g.conteggio }) }}
                </span>
              </div>
              <p v-if="g.azione" class="app-presidio-azione">{{ g.azione }}</p>
              <p v-if="g.significato" class="app-presidio-significato">{{ g.significato }}</p>
              <!-- ⛔ Mai il rimedio del presidio al posto di quello della causa:
                   sarebbe il rimedio di un altro guasto. Si dice che manca. -->
              <p v-if="!haTesto(g)" class="app-presidio-troncato">
                {{ t('amministrazione.processi.presidi_causa_senza_testo') }}
              </p>
            </template>
            <table v-if="g.righe.length" class="app-presidio-righe">
              <thead>
                <tr><th v-for="c in colonne(g.righe)" :key="c">{{ c }}</th></tr>
              </thead>
              <tbody>
                <tr v-for="(r, i) in g.righe" :key="i">
                  <td v-for="c in colonne(g.righe)" :key="c">{{ cella(r[c]) }}</td>
                </tr>
              </tbody>
            </table>
          </div>
        </div>
      </div>

      <!-- I presidi a zero, tutti insieme: la striscia dice «questi sono
           coperti e vuoti», e ognuno apre la propria descrizione a un click.
           ⭐ CHIUSA di default (rilievo di Tid, 2026-10-14): e' la parte che non
           chiede niente, e aperta toglieva altezza alla lista dei processi. Il
           numero resta nell'intestazione, quindi chiusa dice gia' quanti sono.
           ⚠️ `<details>` nativo, come il dettaglio tecnico: apertura, tastiera
           e lettore di schermo senza una riga di stato da tenere. -->
      <details v-if="aZero.length" class="app-presidi-zero">
        <summary class="app-presidi-zero-label">
          {{ t('amministrazione.processi.presidi_a_zero', { n: aZero.length }) }}
        </summary>
        <div class="app-presidi-zero-chip">
          <PresidioChip v-for="p in aZero" :key="p.vista" :presidio="p" />
        </div>
      </details>
    </template>
  </div>
</template>

<style scoped>
/* Layout locale del pannello: non è un pattern di pagina, non va in main.css. */
/* Il pannello riempie la scheda «Presidi» della vista: le schede prendono lo
   spazio e scorrono dentro di se', la striscia a zero non cede. */
.app-presidi {
  display: flex; flex-direction: column; gap: 1rem;
  height: 100%; min-height: 0;
}
.app-presidi-schede {
  display: flex; flex-direction: column; gap: 1rem;
  flex: 1 1 auto; min-height: 0; overflow-y: auto;
}
.app-presidio {
  border: 1px solid var(--app-border-color);
  border-radius: var(--p-content-border-radius);
  padding: 0.75rem;
}
.app-presidio-testa { display: flex; flex-wrap: wrap; align-items: center; gap: 0.5rem; }
/* Nomi di vista e di causa sono identificatori lunghi senza spazi. */
.app-presidio-nome { font-weight: 600; overflow-wrap: anywhere; }
.app-presidio-troncato { font-size: 0.8rem; opacity: 0.7; }
.app-presidio-desc { margin: 0.4rem 0 0.6rem; font-size: 0.85rem; opacity: 0.85; }
/* L'azione è la prima cosa che si legge: piena, non attenuata. */
.app-presidio-azione { margin: 0.5rem 0 0.2rem; font-weight: 600; }
.app-presidio-significato { margin: 0 0 0.4rem; font-size: 0.9rem; }
.app-presidio-chi { margin-bottom: 0.4rem; }
/* Un gruppo di righe con la stessa causa: separato dal precedente, il rimedio
   sopra le sue righe. */
.app-presidio-causa {
  margin-top: 0.6rem;
  padding-top: 0.5rem;
  border-top: 1px dashed var(--app-border-color);
}
/* Il conteggio di una causa: cifre a larghezza fissa, perché i gruppi stanno
   uno sotto l'altro e i numeri si confrontano a colpo d'occhio. */
.app-presidio-causa-conteggio { font-variant-numeric: tabular-nums; }
.app-presidio-dettaglio > summary {
  cursor: pointer; font-size: 0.8rem; opacity: 0.7;
}
/* Il motivo per cui un presidio non si è letto: si legge, non si attenua. */
.app-presidio-errore {
  margin: 0.4rem 0 0.2rem;
  font-size: 0.85rem;
  color: var(--app-severity-danger);
  overflow-wrap: anywhere;
}
/* ⭐ Le celle VANNO A CAPO: le colonne le decide la vista, e un valore lungo
   (un messaggio, un percorso) con `nowrap` allargava la tabella fino allo
   scroll orizzontale (rilievo di Tid, 2026-10-14). Restano su una riga le
   intestazioni, che sono nomi di colonna brevi. `overflow-x` resta la rete
   per una tabella di molte colonne. */
.app-presidio-righe {
  width: 100%; display: block; overflow-x: auto; font-size: 0.8rem;
  border-collapse: collapse;
}
.app-presidio-righe th, .app-presidio-righe td {
  text-align: left; vertical-align: top; padding: 0.2rem 0.5rem;
}
.app-presidio-righe th { white-space: nowrap; }
.app-presidio-righe td { overflow-wrap: anywhere; min-width: 6rem; }
.app-presidio-righe th { opacity: 0.7; font-weight: 500; }
.app-presidi-vuoto { opacity: 0.7; }
/* Aperta, la striscia ha un tetto suo: i presidi a zero li conta il catalogo,
   e non devono rubare lo spazio delle schede da guardare. */
.app-presidi-zero { flex: 0 0 auto; }
.app-presidi-zero-label { font-size: 0.85rem; opacity: 0.8; cursor: pointer; }
.app-presidi-zero-chip {
  display: flex; flex-wrap: wrap; align-items: center; gap: 0.35rem;
  margin-top: 0.4rem; max-height: 8rem; overflow-y: auto;
}
</style>
