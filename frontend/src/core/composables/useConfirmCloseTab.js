// Scopo: logica condivisa per chiusura tab con conferma dirty.
// Usato da AppLayout (shortcut Ctrl+W) e ContentTabs (click su X).
import { useRouter } from 'vue-router'
import { useI18n } from 'vue-i18n'
import { useConfirmAction } from './useConfirmAction'
import { useTabsStore } from '../../stores/tabs'

export function useConfirmCloseTab() {
  const router = useRouter()
  const { confirmAction } = useConfirmAction()
  const { t } = useI18n()
  const tabs = useTabsStore()

  function closeTabAndNavigate(tab) {
    const wasActive = tabs.activeTabId === tab.id
    tabs.removeTab(tab.id)
    if (wasActive) {
      const next = tabs.activeTab
      router.push(next ? next.path : '/')
    }
  }

  function closeTab(tab) {
    if (!tab) return

    if (tab.dirty) {
      confirmAction({
        header: t('common.modifiche_non_salvate.titolo'),
        message: t('common.modifiche_non_salvate.messaggio'),
        acceptLabel: t('common.modifiche_non_salvate.chiudi'),
        onAccept: () => closeTabAndNavigate(tab),
      })
      return
    }
    closeTabAndNavigate(tab)
  }

  return { closeTab }
}
