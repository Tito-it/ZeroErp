// Scopo: building block preferiti di navigazione — risoluzione, filtro permessi e apertura tab.
import { computed } from 'vue'
import { useI18n } from 'vue-i18n'
import { useRouter } from 'vue-router'
import { useAuthStore } from '../../stores/auth'
import { useNavigationStore } from '../../stores/navigation'
import {
  DOMAINS,
  DOMAIN_MENUS,
  flattenMenu,
  isMenuItemAllowed as isMenuItemAllowedPer,
  resolveNavigationLabel
} from '../navigation'

export function useNavigationFavorites() {
  const { t, te } = useI18n()
  const router = useRouter()
  const auth = useAuthStore()
  const nav = useNavigationStore()

  // Scopo: filtro visibilita' delle voci L2 legato allo store auth. La regola
  // e' il BB `isMenuItemAllowed` di core/navigation, la stessa del router.
  function isMenuItemAllowed(item) {
    return isMenuItemAllowedPer(item, auth)
  }

  // Scopo: trasforma domain/path salvati in localStorage in metadati UI renderizzabili.
  function resolveFavorite(domainKey, path) {
    const domain = DOMAINS.find(item => item.key === domainKey)
    if (!domain || !path) return null
    if (!auth.visibleDomains.some(item => item.key === domainKey)) return null

    const menuItem = flattenMenu(DOMAIN_MENUS[domainKey] || [])
      .find(item => item.to === path)
    if (!menuItem || !isMenuItemAllowed(menuItem)) return null

    const label = resolveNavigationLabel({ domain: domainKey, menuKey: menuItem.key }, t, te) || menuItem.key
    const domainLabel = resolveNavigationLabel({ domain: domainKey }, t, te) || domainKey

    return {
      domain: domainKey,
      path,
      item: menuItem,
      label,
      domainLabel,
      icon: menuItem.icon,
      tooltip: t('nav.preferiti_tooltip_dominio_voce', { dominio: domainLabel, voce: label })
    }
  }

  const visibleFavorites = computed(() =>
    nav.getAllFavorites()
      .map(favorite => resolveFavorite(favorite.domain, favorite.path))
      .filter(Boolean)
  )

  // Scopo: apre il preferito come una normale voce L2, mantenendo tab e sidebar coerenti.
  function navigateToFavorite(favoriteLike) {
    const favorite = favoriteLike?.item
      ? favoriteLike
      : resolveFavorite(favoriteLike?.domain, favoriteLike?.path)
    if (!favorite) return false

    // La scheda la apre il guard del router (unico punto, anche per la
    // sostituzione oltre il limite): qui si naviga e basta.
    nav.setDomain(favorite.domain)
    router.push(favorite.path)
    return true
  }

  // Scopo: riordina solo il sottoinsieme visibile del dominio preservando eventuali preferiti filtrati.
  function reorderVisibleDomainFavorites(domainKey, orderedVisiblePaths) {
    const nextVisible = [...orderedVisiblePaths]
    const visibleSet = new Set(orderedVisiblePaths)
    const merged = nav.getDomainFavorites(domainKey).map(path => {
      if (!visibleSet.has(path)) return path
      return nextVisible.shift()
    })
    nav.reorderFavorites(domainKey, merged)
  }

  return {
    visibleFavorites,
    resolveFavorite,
    isMenuItemAllowed,
    navigateToFavorite,
    reorderVisibleDomainFavorites
  }
}
