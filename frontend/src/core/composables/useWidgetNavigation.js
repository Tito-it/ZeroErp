// Scopo: Grammatica e risoluzione del deep-link dei widget dashboard.
//        Traduce il `deep_link` (jsonb opaco al DB) in una navigazione
//        coerente: apre il tab giusto, sincronizza la sidebar del
//        dominio e naviga — inclusa la query di stato preimpostato.
//
// GRAMMATICA (posseduta dal FE, il DB conserva e restituisce senza
// interpretare — brief DB §3f):
//
//   { "path": "/vendite/dashboard-competenza" }
//   { "path": "/vendite/dashboard-backlog", "query": { "classe": "FERMO" } }
//   { "path": "/vendite/ordini", "query": { "stato": "DRAFT" } }
//
// `path` e' canonico e non `route.name` perche' e' cio' che tutta la
// navigazione dell'app gia' parla: le voci di menu si identificano con
// `to` (path) e i preferiti persistono path. Risolvere per nome
// costringerebbe a un doppio mapping nome->path->voce di menu senza
// alcun guadagno.
//
// `query` e' il pezzo net-new rispetto ai preferiti: quelli persistono
// solo una path stringa e non sanno esprimere uno "stato preimpostato".
// Il campo e' previsto fin da ora anche se i widget v1 (i tre cruscotti)
// non lo usano — cosi' i widget futuri che deep-linkano a liste filtrate
// non richiedono di riaprire ne' la grammatica ne' il seed.
//
// PERMESSI: il filtro autorevole e' lato DB (la fn di risoluzione non
// restituisce nemmeno i widget proibiti). Il controllo qui e' difesa in
// profondita' contro un seed incoerente — un widget che dichiara un'area
// diversa da quella che guarda la rotta di destinazione.

import { useI18n } from 'vue-i18n'
import { useRouter } from 'vue-router'
import { useNavigationStore } from '../../stores/navigation'
import { useNavigationFavorites } from './useNavigationFavorites'
import {
  DOMAINS,
  DOMAIN_MENUS,
  flattenMenu,
  resolveNavigationLabel,
} from '../navigation'

export function useWidgetNavigation() {
  const { t, te } = useI18n()
  const router = useRouter()
  const nav = useNavigationStore()
  const { isMenuItemAllowed } = useNavigationFavorites()

  // Scopo: normalizza un deep_link in `{path, query}`. Tollera il campo
  //        assente o malformato: un widget senza deep-link e' legittimo
  //        (card informativa, es. benvenuto) e non deve rompere nulla.
  function parseDeepLink(deepLink) {
    if (!deepLink || typeof deepLink !== 'object') return null
    const path = typeof deepLink.path === 'string' ? deepLink.path : null
    if (!path) return null
    const query =
      deepLink.query && typeof deepLink.query === 'object' ? deepLink.query : {}
    return { path, query }
  }

  // Scopo: trova la voce di menu (con il suo dominio) che serve la path.
  //        Serve per aprire un tab coerente: etichetta, icona, dominio e
  //        menuKey vengono da li', esattamente come per una voce L2
  //        cliccata a mano.
  // Risultato: {domain, item} | null
  function findMenuTarget(path) {
    for (const domain of DOMAINS) {
      const item = flattenMenu(DOMAIN_MENUS[domain.key] || []).find(
        entry => entry.to === path,
      )
      if (item) return { domain: domain.key, item }
    }
    return null
  }

  // Scopo: risolve un deep_link nei metadati necessari a navigare e a
  //        renderizzare il target (etichetta, icona, dominio).
  // Risultato: {path, fullPath, query, domain, item, label, icon} | null
  //        null = deep-link assente, malformato, non mappato su una voce
  //        di menu, o non permesso: in tutti i casi la card non deve
  //        essere cliccabile.
  function resolveWidgetTarget(deepLink) {
    const parsed = parseDeepLink(deepLink)
    if (!parsed) return null

    const target = findMenuTarget(parsed.path)
    // Nessuna voce di menu per quella path: seed incoerente. Meglio una
    // card non cliccabile che un tab orfano senza dominio ne' etichetta.
    if (!target) return null
    if (!isMenuItemAllowed(target.item)) return null

    const label =
      resolveNavigationLabel(
        { domain: target.domain, menuKey: target.item.key },
        t,
        te,
      ) || target.item.key

    // `fullPath` include la query: e' l'identita' del tab, cosi' due
    // stati preimpostati diversi della stessa lista non si sovrascrivono.
    const fullPath = router.resolve({
      path: parsed.path,
      query: parsed.query,
    }).fullPath

    return {
      path: parsed.path,
      fullPath,
      query: parsed.query,
      domain: target.domain,
      item: target.item,
      label,
      icon: target.item.icon,
    }
  }

  // Scopo: apre il target di un widget come una normale voce di menu,
  //        mantenendo tab e sidebar coerenti. Stessa sequenza di
  //        `navigateToFavorite`, con in piu' il passaggio della query di
  //        stato preimpostato.
  // Risultato: true se ha navigato, false se il target non e'
  //        risolvibile/permesso o se il tab non si e' aperto.
  function navigateToWidget(deepLink) {
    const target = resolveWidgetTarget(deepLink)
    if (!target) return false

    // La scheda la apre il guard del router (unico punto, anche per la
    // sostituzione oltre il limite): qui si naviga e basta.
    nav.setDomain(target.domain)
    router.push(target.fullPath)
    return true
  }

  return {
    parseDeepLink,
    resolveWidgetTarget,
    navigateToWidget,
  }
}
