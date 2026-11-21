<!--
  SPDX-License-Identifier: AGPL-3.0-or-later
  Copyright (C) 2026 Tid (Michele Carlo Titini)
-->
<script setup>
// Scopo: I due banner del PRESET DI BASE di una configurazione personale
//        (lista o dashboard), come li calcola il resolver del DB:
//        - «preset aggiornato» (DEF-2, `preset_aggiornato`): l'amministratore
//          ha cambiato il contenuto del preset dopo l'ultimo salvataggio
//          dell'utente → «Vedi novita'» / «Ignora» (riallinea lo snapshot);
//          dal giro 1b il banner dice anche QUALI parti sono cambiate
//          (`preset_aggiornato_chiavi`, le chiavi scelte dall'utente);
//        - «base cambiata» (BE7 di brief-db-revisione-ui, giro 1a,
//          `preset_base_cambiato`): la preferenza parte da un preset che non e'
//          piu' quello di oggi (spento, o sostituito da un altro livello) →
//          «Riallinea» (risalvare: il BE ci scrive la base di oggi).
//
// Estratto il 2026-11-20 (regola del 2, ok Tid): era il markup di
// `ListaConfigurabile`, e le dashboard (`HomeView`) prendevano gli stessi due
// banner, gemelli delle liste.
//
// ⭐ I due banner non si sovrappongono per costruzione del DB: con la base
//    cambiata `preset_aggiornato` e' falso. Il componente non lo ri-decide.
// ⚠️ La base cambiata non ha «Ignora»: si chiude solo riallineando.
// ⚠️ I testi li sceglie il chiamante (dicono CHE COSA: la lista, il
//    cruscotto), gia' tradotti.
import { computed } from 'vue'
import { useI18n } from 'vue-i18n'
import Message from 'primevue/message'
import Button from 'primevue/button'
import { MANAGE_ICONS } from '../constants'
import { labelOrCode } from '../utils/i18nLabel'

const props = defineProps({
  // `preset_aggiornato` della risoluzione.
  aggiornato: { type: Boolean, default: false },
  // `preset_aggiornato_chiavi` della risoluzione: le chiavi (`colonne`,
  // `pagina_dimensione`, `widget`, …) il cui contenuto nel preset e' cambiato.
  chiavi: { type: Array, default: () => [] },
  // `preset_base_cambiato` della risoluzione.
  baseCambiato: { type: Boolean, default: false },
  // Le azioni spente (ricarica o salvataggio in corso).
  disabled: { type: Boolean, default: false },
  // { aggiornato, vediNovita, ignora, baseCambiato, riallinea }: testi tradotti.
  testi: { type: Object, required: true },
})

defineEmits(['vedi-novita', 'ignora', 'riallinea'])

const { t, te } = useI18n()

// Le parti cambiate, nella lingua dell'operatore. ⚠️ Il vocabolario delle
// chiavi e' del DB (un giro le aggiunge o le ritira): una chiave senza
// etichetta si mostra col suo codice (`labelOrCode`), mai col path i18n.
// Nessuna chiave = nessuna riga (il banner resta quello di sempre).
const partiCambiate = computed(() => {
  if (!props.chiavi.length) return ''
  const parti = props.chiavi
    .map((c) => labelOrCode(t, te, `common.banner_preset.parte.${c}`, c))
    .join(', ')
  return t('common.banner_preset.parti_cambiate', { parti })
})
</script>

<template>
  <Message
    v-if="aggiornato"
    severity="info"
    :closable="false"
    class="banner-preset"
    data-testid="banner-preset-aggiornato"
  >
    <div class="app-msg-riga">
      <span class="banner-preset__msg">
        {{ testi.aggiornato }}
        <span
          v-if="partiCambiate"
          class="banner-preset__parti"
          data-testid="banner-preset-parti"
        >{{ partiCambiate }}</span>
      </span>
      <Button
        severity="info"
        size="small"
        :label="testi.vediNovita"
        :icon="MANAGE_ICONS.NOVITA"
        :disabled="disabled"
        data-testid="banner-preset-vedi-novita"
        @click="$emit('vedi-novita')"
      />
      <Button
        severity="secondary"
        text
        size="small"
        :label="testi.ignora"
        :disabled="disabled"
        data-testid="banner-preset-ignora"
        @click="$emit('ignora')"
      />
    </div>
  </Message>

  <Message
    v-if="baseCambiato"
    severity="info"
    :closable="false"
    class="banner-preset"
    data-testid="banner-preset-base-cambiato"
  >
    <div class="app-msg-riga">
      <span class="banner-preset__msg">{{ testi.baseCambiato }}</span>
      <Button
        severity="info"
        size="small"
        :label="testi.riallinea"
        :icon="MANAGE_ICONS.RIALLINEA"
        :disabled="disabled"
        data-testid="banner-preset-riallinea"
        @click="$emit('riallinea')"
      />
    </div>
  </Message>
</template>

<style scoped>
.banner-preset {
  margin-bottom: 0.5rem;
}

/* Il testo prende la riga e spinge i pulsanti a destra; stretto, va a capo. */
.banner-preset__msg {
  flex: 1 1 auto;
  min-width: 12rem;
}

/* Le parti cambiate, a capo sotto il messaggio. */
.banner-preset__parti {
  display: block;
  font-weight: 600;
}
</style>
