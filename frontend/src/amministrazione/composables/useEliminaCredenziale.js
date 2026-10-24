// ------------------------------------------------------------
// SPDX-License-Identifier: GPL-3.0-or-later
// Copyright (C) 2026 Tid (Michele Carlo Titini)
// Doc: JavaScript
// Scopo: «Elimina accesso» su una credenziale senza vesti
//        (brief-db-elimina-credenziale-senza-veste §6): se il gesto e' spento,
//        la frase che spiega perche', la conferma e la chiamata al verbo.
// Note: ⭐ Regola in un posto solo, come `useSchedaVeste`: la usano il kebab
//       della riga di «Altri accessi» e il drawer della stessa riga.
//       ⛔ Il motivo NON si deduce qui: `can_delete` e la terna `delete_*`
//       sono il primo motivo di `script.fn_check_credenziale_eliminabile`, la
//       stessa check con cui il verbo rifiuta. Il pulsante spento e il 409
//       non possono dire due cose diverse; se il client e' stantio, il
//       rifiuto arriva comunque, col suo toast.
// ------------------------------------------------------------
import { useI18n } from 'vue-i18n'
import { useApiHandler } from '../../core/composables/useApiHandler'
import { useConfirmAction } from '../../core/composables/useConfirmAction'
import { useChiaveGesto } from '../../core/composables/useChiaveGesto'
import { bloccoAttivo, bloccoDaRiga, componiBloccoMotivo } from '../../core/utils/bloccoMotivo'
import { eliminaCredenziale } from '../api/amministrazione'

const PREFISSO = 'delete'

export function useEliminaCredenziale() {
  const { t, te } = useI18n()
  const { execute, loading } = useApiHandler()
  const { confirmAction } = useConfirmAction()
  // ⭐ La key del GESTO (`useChiaveGesto`): l'eliminazione e' irreversibile e
  //    la conferma si chiude al clic, quindi il reinvio dopo un timeout passa
  //    da una conferma nuova e deve rimandare la stessa key.
  const gesto = useChiaveGesto()

  // Scopo: il gesto e' spento? Lo dice il flag del backend.
  function eliminaSpenta(riga) {
    return bloccoAttivo(riga, PREFISSO, `can_${PREFISSO}`)
  }

  // Scopo: la frase del motivo, '' se il gesto e' acceso.
  // ⚠️ `dove` (CON_STORIA) arriva come ARRAY di tabelle: la chiave i18n lo
  //    nomina come testo, e `t()` renderebbe un array come JSON.
  function motivoEliminaSpenta(riga) {
    if (!eliminaSpenta(riga)) return ''
    const blocco = bloccoDaRiga(riga, PREFISSO)
    const dove = blocco.dettaglio?.dove
    const dettaglio = Array.isArray(dove) ? { ...blocco.dettaglio, dove: dove.join(', ') } : blocco.dettaglio
    return componiBloccoMotivo(t, te, { ...blocco, dettaglio })
  }

  // Scopo: chiede conferma ed elimina; `onEliminata` solo a gesto riuscito
  //        (chi chiama chiude il drawer e ricarica la lista).
  function chiediElimina(riga, { onEliminata } = {}) {
    if (!riga || eliminaSpenta(riga)) return
    const id = riga.auth_user_id
    confirmAction({
      header: t('amministrazione.accessi.elimina'),
      message: t('amministrazione.accessi.elimina_conferma', { username: riga.username }),
      acceptLabel: t('amministrazione.accessi.elimina'),
      danger: true,
      onAccept: async () => {
        const res = await execute(
          () => gesto.invia({ authUserId: id }, (config) => eliminaCredenziale(id, config)),
          { successMessage: t('amministrazione.accessi.eliminata_ok') },
        )
        if (res !== null) onEliminata?.(id)
      },
    })
  }

  return { loading, eliminaSpenta, motivoEliminaSpenta, chiediElimina }
}
