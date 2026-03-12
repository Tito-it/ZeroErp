// Scopo: logica condivisa per chiusura tab con conferma dirty.
// Usato da AppLayout (shortcut Ctrl+W) e ContentTabs (click su X).
import { useRouter } from 'vue-router'
import { useConfirm } from 'primevue/useconfirm'
import { useI18n } from 'vue-i18n'
import { useTabsStore } from '../../stores/tabs'

export function useConfirmCloseTab() {
  const router = useRouter()
  const confirm = useConfirm()
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
      confirm.require({
        message: t('tabs.close_confirm_message'),
        header: t('tabs.close_confirm_title'),
        icon: 'pi pi-exclamation-triangle',
        acceptLabel: t('tabs.close_confirm_accept'),
        rejectLabel: t('tabs.close_confirm_reject'),
        accept: () => closeTabAndNavigate(tab)
      })
      return
    }
    closeTabAndNavigate(tab)
  }

  return { closeTab }
}
