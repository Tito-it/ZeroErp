// Scopo: ⭐ IL GESTO. `bersagli.js` dice DOVE si puo' andare; qui si costruisce
//        il pulsante e si esegue l'andata.
//
// ⭐ PERCHE' E' UN MODULO E NON UN COMPOSABLE. L'ospite del drawer e' UNO SOLO
//    per tutta l'applicazione, montato in `App.vue` accanto a `<Toast />`. Deve
//    esserlo: il toast e' globale — compare sopra qualunque schermata, comprese
//    quelle che un `DocumentoDrawerHost` proprio non ce l'hanno — e un gesto che
//    funziona solo su tre viste su venti non e' un gesto, e' una trappola.
//
// ⛔ LA STRADA CHE NON FUNZIONA e' «il toast naviga, la vista apre»: `FATTURA`
//    una vista non ce l'ha proprio (non esiste `vendite/fatture`, il documento
//    si apre solo in drawer). Bisognerebbe inventarne una col solo scopo di
//    ospitare un pannello.
//
// ⚠️ IMPORT DA `vendite/`: la mappa delle destinazioni vive in `bersagli.js` e
//    riusa il registry dei drawer documento. E' la stessa direzione gia' in uso
//    fra `core/components` e `anagrafiche/` — non una strada nuova.
import { ref } from 'vue'
import i18n from './i18n'
import router from '../router'
import { registraDrawerChiudibile } from './composables/useDrawerChiusuraGlobale'
import { bersagliRisolti } from './bersagli'

// ── L'ospite globale ─────────────────────────────────────────────────────────
// Stessa tripletta di `useDocumentoDrawer` (visible, chiave registry, id): qui
// e' a livello di MODULO invece che di componente, perche' l'istanza e' una.
// ⚠️ Non si riusa `useDocumentoDrawer()` chiamandolo qui: quel composable
// registra la chiusura globale con `onScopeDispose`, e fuori da uno scope si
// registrerebbe senza mai de-registrarsi. Per un singleton e' il comportamento
// giusto — ma va scritto, non ereditato per caso.
export const bersaglioDrawerVisible = ref(false)
export const bersaglioDrawerTipo = ref(null)
export const bersaglioDrawerId = ref(null)

// Scopo: handler `@update:visible` dell'ospite globale.
export function onBersaglioDrawerVisible(v) {
  bersaglioDrawerVisible.value = v
}

// ⭐ Anche l'ospite globale si chiude al cambio di rotta, come tutti gli altri.
// Senza, un drawer aperto da un toast resterebbe davanti alla pagina d'arrivo —
// che e' esattamente il difetto per cui la chiusura globale esiste.
registraDrawerChiudibile(() => {
  if (bersaglioDrawerVisible.value) bersaglioDrawerVisible.value = false
})

// Scopo: Porta l'operatore sul bersaglio. Due modi, e li decide la mappa:
//        un drawer (la maggioranza — un documento si apre, non si "visita")
//        oppure una rotta con deep-link, per le entita' che hanno una lista.
function vaiAl(risolto) {
  if (risolto.drawer) {
    bersaglioDrawerTipo.value = risolto.drawer
    bersaglioDrawerId.value = risolto.id
    bersaglioDrawerVisible.value = true
    return
  }
  if (risolto.rotta) {
    // Due forme, e la mappa dice quale:
    //  · `queryKey` → deep-link `?open=<id>` su una LISTA, che lo legge e poi se
    //    lo ripulisce con `router.replace` (meccanismo gia' in servizio su
    //    `vendite-contratti` e, dal 2026-08-24, su `vendite-lotti`);
    //  · `param`    → rotta con `:id`, per le entita' che hanno una pagina
    //    propria invece di un pannello (l'editor di una definizione workflow).
    const { name, queryKey, param } = risolto.rotta
    router.push(
      param
        ? { name, params: { [param]: risolto.id } }
        : { name, query: { [queryKey]: risolto.id } },
    )
  }
}

// ⚠️ Un identificativo LUNGO non entra in un pulsante. Al 2026-08-24 tutti e
// nove i tipi a catalogo hanno chiave numerica, ma `key_selector` ammette
// ancora `uid`: il giorno che una superficie pubblica indirizzera' cosi',
// «Apri Preventivo 0f8c1d42-9a3b-4c11-8e77-2b6d5a4c9e01» sarebbe un'etichetta
// illeggibile — e il numero, a quel punto, non aggiunge niente a chi legge.
// ⭐ Il guard resta anche se oggi non morde: costa una riga e toglie una
//    domanda a chi aggiungera' quel tipo.
const ID_MAX_IN_ETICHETTA = 12

// Scopo: ⭐ Le AZIONI da mettere nel toast, per i bersagli raggiungibili.
//        Array vuoto = nessun pulsante, e il toast resta quello di prima:
//        e' il degrado dichiarato del §4.3, non un ripiego.
//
//        ⚠️ `authStore` SI PASSA, non si legge qui dentro. Questa funzione viene
//        chiamata anche dal ramo `catch` di `useApiHandler`, cioe' fuori dal
//        `setup()` di un componente: `useAuthStore()` li' dipenderebbe dalla
//        pinia attiva globale — funziona in applicazione e si rompe in un test,
//        che e' la forma peggiore di dipendenza nascosta.
//
//        ⚠️ L'etichetta si compone da `config.tipi_entita.*`, che e' l'indirizzo
//        i18n dichiarato DAL DATABASE nella colonna `etichetta_key`: la parola
//        con cui l'operatore chiama quella cosa la decide il catalogo, non
//        questo file.
export function azioniDaBersagli(bersagli, authStore) {
  const t = i18n.global.t
  return bersagliRisolti(bersagli, authStore).map((risolto) => {
    const entita = t(risolto.etichettaKey)
    return {
      label:
        String(risolto.idEtichetta).length <= ID_MAX_IN_ETICHETTA
          ? t('errors.bersaglio_apri', { entita, id: risolto.idEtichetta })
          : t('errors.bersaglio_apri_senza_id', { entita }),
      icon: 'pi pi-external-link',
      esegui: () => vaiAl(risolto),
    }
  })
}
