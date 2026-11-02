// ------------------------------------------------------------
// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Tid (Michele Carlo Titini)
// Doc: JavaScript
// Scopo: le AZIONI DI RIGA contribuite a un punto di estensione
//        (`core/estensioni.js`): le voci da aggiungere al kebab della lista,
//        e lo stato del drawer che la voce apre. Il drawer lo monta
//        `<EstensioneDrawerHost>`, nello stesso componente.
//
// ⚠️ Il drawer si carica PRIMA di montarlo e si apre al tick dopo (visible
//    false → true), come fa `DocumentoDrawerHost`: un drawer che nasce gia'
//    visibile non vede la transizione e si apre coi soli default.
// ------------------------------------------------------------
import { markRaw, nextTick, ref } from 'vue'
import { useI18n } from 'vue-i18n'
import { contributi } from '../estensioni'
import { useNotify } from './useNotify'
import { registraDrawerChiudibile } from './useDrawerChiusuraGlobale'

export function useAzioniEstese(punto) {
  const { t } = useI18n()
  const notify = useNotify()
  // { componente, props, visible } del drawer aperto, o null.
  const aperto = ref(null)
  // Aperture concorrenti: vince la piu' recente.
  let seq = 0

  // Scopo: apre il drawer di un contributo sulla riga.
  async function apri(contributo, riga) {
    const mio = ++seq
    let mod
    try {
      mod = await contributo.drawer()
    } catch (e) {
      // Chunk non caricabile (tipicamente: deploy nuovo con la tab vecchia
      // aperta). Senza questo il click sul kebab non fa nulla, in silenzio.
      if (mio === seq) notify.error(t('common.error_loading'))
      console.error(`Azione «${contributo.chiave}»: drawer non caricato`, e)
      return
    }
    if (mio !== seq) return
    aperto.value = { componente: markRaw(mod.default), props: contributo.props(riga, { t }), visible: false }
    await nextTick()
    if (mio === seq && aperto.value) aperto.value.visible = true
  }

  // Scopo: le voci del kebab per una riga, nella forma di `RowActionsMenu`.
  // ⚠️ `action` (il permesso di processo) passa SEMPRE: una voce che lo
  //    dichiarasse e se lo vedesse scartare comparirebbe a chi non ha il
  //    permesso, senza errore. Stesso discorso per gli altri campi del menu.
  function voci(riga) {
    return contributi(punto).map(c => ({
      key: c.chiave,
      label: t(c.label),
      icon: c.icon,
      severity: c.severity,
      action: c.action,
      allowWhenInactive: c.allowWhenInactive,
      visible: c.visibile ? Boolean(c.visibile(riga)) : true,
      disabled: c.disabilitato ? Boolean(c.disabilitato(riga)) : false,
      tooltip: c.tooltip ? t(c.tooltip) : undefined,
      command: () => apri(c, riga),
    }))
  }

  // Scopo: il drawer si apre o si chiude (handler `@update:visible` dell'host).
  function impostaVisibile(v) {
    if (aperto.value) aperto.value.visible = v
  }

  // Un cambio di rotta chiude i drawer aperti (come `useDocumentoDrawer`).
  // Il guard su `visible` evita di riscrivere un ref gia' falso a ogni
  // navigazione.
  registraDrawerChiudibile(() => {
    if (aperto.value?.visible) aperto.value.visible = false
  })

  return { voci, aperto, impostaVisibile }
}
