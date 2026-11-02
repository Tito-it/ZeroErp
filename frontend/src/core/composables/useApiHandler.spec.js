// ------------------------------------------------------------
// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Tid (Michele Carlo Titini)
// Doc: JavaScript
// Scopo: Il PRIMO test del frontend (2026-09-09), e sta qui per una ragione
//        precisa: `useApiHandler` e' l'UNICO punto in cui il frontend legge una
//        risposta del backend. `axios` e' importato in un file solo
//        (`core/api.js`), e ogni chiamata di dominio passa di qui.
//        ⇒ Quello che questo file fissa non e' «il composable funziona»: e' il
//        CONTRATTO dell'envelope descritto in `docs/it/dev/api.md` §Envelope —
//        `fields`, `targets`, `ui_action`, `hint`, `message` — cioe' la meta' di
//        lavoro che il backend ha costruito e che a video si perde se qualcuno
//        la rinomina o smette di leggerla.
//        ⭐ `hint` e' entrato il 2026-09-09 (D4) ed e' il caso che dimostra il
//        punto: il campo viaggiava dal database all'envelope da settimane e
//        NESSUNO lo leggeva. Un test che fissa un campo trasportato e non
//        consumato avrebbe presidiato una promessa; questi lo fissano il giorno
//        in cui il toast lo rende.
// Note: ⛔ I collaboratori sono mockati di proposito: `bersagli.js` tira dentro
//        i drawer di vendite e `bersaglioGesto.js` importa il router intero.
//        Provarli qui vorrebbe dire provare loro, non questo.
// ------------------------------------------------------------

import { describe, it, expect, vi, beforeEach } from 'vitest'

// ⚠️ I mock si dichiarano PRIMA dell'import del modulo sotto test: `vi.mock` e'
//    issato, ma le spie devono esistere quando il modulo viene valutato.
const notifiche = {
  success: vi.fn(),
  error: vi.fn(),
  systemError: vi.fn(),
  errorConAzioni: vi.fn(),
}
let azioniFinte = []

vi.mock('../../stores/auth', () => ({ useAuthStore: () => ({ isSuperAdmin: false }) }))
vi.mock('./useNotify', () => ({ useNotify: () => notifiche }))
vi.mock('../bersagli', () => ({
  // Passa-attraverso minimo: qui interessa che il campo `targets` dell'envelope
  // ARRIVI, non come viene risolto (quello e' compito di `bersagli.js`).
  estraiBersagli: (error) => (Array.isArray(error?.targets) ? error.targets : []),
}))
vi.mock('../bersaglioGesto', () => ({ azioniDaBersagli: () => azioniFinte }))
// i18n reale non serve: qui interessa QUALE chiave il messaggio usa.
vi.mock('../i18n', () => ({ default: { global: { t: (chiave) => `t:${chiave}` } } }))

const { useApiHandler } = await import('./useApiHandler')

// Costruisce un errore nella forma in cui axios lo consegna.
function errore(status, body) {
  return { response: { status, data: body } }
}

// Envelope d'errore standard del backend: { error: { code, message, ... } }
function envelope(campi) {
  return { error: { code: 'E_PROVA', message: 'Messaggio dal backend', ...campi } }
}

beforeEach(() => {
  Object.values(notifiche).forEach((f) => f.mockClear())
  azioniFinte = []
})

describe('useApiHandler — successo', () => {
  it('scarta il doppio involucro { data: { data: X } } e restituisce X', async () => {
    const { execute } = useApiHandler()
    const out = await execute(() => Promise.resolve({ data: { data: { id: 7 }, meta: {} } }))
    expect(out).toEqual({ id: 7 })
  })

  it('preserva un payload gia’ scartato (il caso della action di store)', async () => {
    // ⚠️ Regola scritta in `catalogo-building-block-frontend`: `execute` serve
    //    SOLO per risposte axios. Chi passa un payload nudo non deve vederselo
    //    rovinare — questo test fissa quel ripiego.
    const { execute } = useApiHandler()
    const out = await execute(() => Promise.resolve({ id: 7, nome: 'x' }))
    expect(out).toEqual({ id: 7, nome: 'x' })
  })

  it('il toast di successo parte solo se il chiamante lo chiede', async () => {
    const { execute } = useApiHandler()
    await execute(() => Promise.resolve({ data: { data: 1 } }))
    expect(notifiche.success).not.toHaveBeenCalled()
    await execute(() => Promise.resolve({ data: { data: 1 } }), { successMessage: 'fatto' })
    expect(notifiche.success).toHaveBeenCalledWith('fatto')
  })
})

describe('useApiHandler — il contratto dell’envelope d’errore', () => {
  it('`fields` diventa `campiErrati`, e i non-stringa vengono scartati', async () => {
    const { execute, campiErrati } = useApiHandler()
    await execute(() => Promise.reject(errore(400, envelope({ fields: ['codice', 42, 'partita_iva'] }))))
    expect(campiErrati.value).toEqual(['codice', 'partita_iva'])
  })

  it('`ui_action` diventa `azioneUi`, e senza il campo resta null', async () => {
    const { execute, azioneUi } = useApiHandler()
    await execute(() => Promise.reject(errore(409, envelope({ ui_action: 'confirm_and_retry' }))))
    expect(azioneUi.value).toBe('confirm_and_retry')
    await execute(() => Promise.reject(errore(400, envelope({}))))
    expect(azioneUi.value).toBeNull()
  })

  it('`targets` diventa `bersagli`', async () => {
    const { execute, bersagli } = useApiHandler()
    const t = [{ type: 'FATTURA', id: '820' }]
    await execute(() => Promise.reject(errore(409, envelope({ targets: t }))))
    expect(bersagli.value).toEqual(t)
  })

  it('il messaggio ha tre ripieghi, nell’ordine dichiarato in api.md', async () => {
    const { execute, messaggioErrore } = useApiHandler()
    await execute(() => Promise.reject(errore(400, { error: { message: 'standard' } })))
    expect(messaggioErrore.value).toBe('standard')
    await execute(() => Promise.reject(errore(400, { error: 'semplificata' })))
    expect(messaggioErrore.value).toBe('semplificata')
    await execute(() => Promise.reject(errore(400, { detail: 'drf' })))
    expect(messaggioErrore.value).toBe('drf')
  })

  // ⭐ 2026-10-01: il 413 arriva da Nginx (corpo HTML, nessun envelope). Il
  //    messaggio deve dire «file troppo grande», non un errore generico; e un
  //    envelope del backend, se c'e', vince sul ripiego.
  it('un 413 senza envelope (Nginx) dice che il file e’ troppo grande', async () => {
    const { execute, messaggioErrore } = useApiHandler()
    await execute(() => Promise.reject(errore(413, '<html>413 Request Entity Too Large</html>')))
    expect(messaggioErrore.value).toBe('t:errors.http_413_file_troppo_grande')
    expect(notifiche.error).toHaveBeenCalledWith('t:errors.http_413_file_troppo_grande', null)
    await execute(() => Promise.reject(errore(413, { error: { message: 'dal backend' } })))
    expect(messaggioErrore.value).toBe('dal backend')
    await execute(() => Promise.reject(errore(400, '<html>altro</html>')))
    expect(messaggioErrore.value).toBeNull()
  })

  it('`hint` diventa `soluzione` — la frase che dice cosa fare adesso', async () => {
    const { execute, soluzione } = useApiHandler()
    const frase = 'Numerare prima i documenti che questo rettifica, poi ripetere.'
    await execute(() => Promise.reject(errore(409, envelope({ hint: frase }))))
    expect(soluzione.value).toBe(frase)
  })

  it('⚠️ una `hint` assente o vuota vale NIENTE, non stringa vuota', async () => {
    // Il backend la omette quando non c'e' — ma un ripiego che si fida di un
    // contratto e' un ripiego che il contratto lo presidia: una stringa vuota
    // che arrivasse fin qui accenderebbe il ramo «c'e' una soluzione» e
    // allungherebbe la durata del toast per una riga che non si vede.
    const { execute, soluzione } = useApiHandler()
    await execute(() => Promise.reject(errore(400, envelope({}))))
    expect(soluzione.value).toBeNull()
    await execute(() => Promise.reject(errore(400, envelope({ hint: '   ' }))))
    expect(soluzione.value).toBeNull()
  })

  it('⭐ `show_retry_dialog` senza `hint`: la soluzione di ripiego dice di riprovare', async () => {
    // Il 409 `E_IDEMPOTENCY_IN_PROGRESS` (il reinvio di un gesto ancora in
    // corso) arriva senza `hint`: senza ripiego l'operatore leggerebbe solo
    // «gia' in elaborazione», senza sapere che riprovare non raddoppia.
    const { execute, soluzione } = useApiHandler()
    await execute(() => Promise.reject(errore(409, envelope({ code: 'E_IDEMPOTENCY_IN_PROGRESS', ui_action: 'show_retry_dialog' }))))
    expect(soluzione.value).toBe('t:errors.soluzione_riprova_fra_poco')
    expect(notifiche.error).toHaveBeenCalledWith('Messaggio dal backend', 't:errors.soluzione_riprova_fra_poco')
  })

  it('⚠️ l’`hint` del backend vince sul ripiego, e un’azione ignota non ne ha', async () => {
    const { execute, soluzione } = useApiHandler()
    await execute(() => Promise.reject(errore(409, envelope({ ui_action: 'show_retry_dialog', hint: 'dal catalogo' }))))
    expect(soluzione.value).toBe('dal catalogo')
    await execute(() => Promise.reject(errore(409, envelope({ ui_action: 'toString' }))))
    expect(soluzione.value).toBeNull()
  })

  it('⚠️ ogni `execute` AZZERA: i campi descrivono l’ultimo errore, non la storia', async () => {
    const { execute, campiErrati, azioneUi, bersagli, messaggioErrore, soluzione } = useApiHandler()
    await execute(() =>
      Promise.reject(
        errore(400, envelope({ fields: ['codice'], ui_action: 'highlight_form_fields', targets: [{ type: 'FATTURA', id: '1' }], hint: 'riprova domani' })),
      ),
    )
    expect(campiErrati.value).toHaveLength(1)
    await execute(() => Promise.resolve({ data: { data: 1 } }))
    expect(campiErrati.value).toEqual([])
    expect(azioneUi.value).toBeNull()
    expect(bersagli.value).toEqual([])
    expect(messaggioErrore.value).toBeNull()
    expect(soluzione.value).toBeNull()
  })

  it('`execute` torna sempre null su errore, qualunque toast sia partito', async () => {
    const { execute } = useApiHandler()
    const out = await execute(() => Promise.reject(errore(500, envelope({}))), { silent: true })
    expect(out).toBeNull()
  })
})

describe('useApiHandler — quale toast, e quando NON parte', () => {
  it('500 e oltre → toast di sistema', async () => {
    const { execute } = useApiHandler()
    await execute(() => Promise.reject(errore(500, envelope({}))))
    expect(notifiche.systemError).toHaveBeenCalledOnce()
    expect(notifiche.error).not.toHaveBeenCalled()
  })

  it('errore di rete (nessuna response) → toast di sistema', async () => {
    const { execute } = useApiHandler()
    await execute(() => Promise.reject(new Error('Network Error')))
    expect(notifiche.systemError).toHaveBeenCalledOnce()
  })

  it('con dei bersagli raggiungibili → il toast porta il GESTO', async () => {
    // ⚠️ `esegui` e non `run`: e' il nome che il template di `App.vue` invoca.
    azioniFinte = [{ label: 'Apri Fattura 820', esegui: () => {} }]
    const { execute } = useApiHandler()
    await execute(() => Promise.reject(errore(409, envelope({ targets: [{ type: 'FATTURA', id: '820' }] }))))
    expect(notifiche.errorConAzioni).toHaveBeenCalledOnce()
    expect(notifiche.error).not.toHaveBeenCalled()
  })

  it('⛔ bersagli irraggiungibili → nessun pulsante, e il toast di prima', async () => {
    // `azioniDaBersagli` scarta da se' cio' che non si puo' aprire: un array
    // vuoto DEVE degradare al toast normale, mai a un pulsante morto.
    azioniFinte = []
    const { execute } = useApiHandler()
    await execute(() => Promise.reject(errore(409, envelope({ targets: [{ type: 'IGNOTO', id: '1' }] }))))
    expect(notifiche.error).toHaveBeenCalledOnce()
    expect(notifiche.errorConAzioni).not.toHaveBeenCalled()
  })

  it('⭐ la soluzione arriva al toast SOTTO il messaggio, senza che il chiamante la chieda', async () => {
    // ⛔ E' il punto di D4: fino al 2026-09-09 il campo viaggiava e nessuno lo
    // rendeva. Che arrivi qui e' l'unica cosa che lo distingue da una promessa.
    const frase = 'Resettare il lotto, ma la nota si rigenera.'
    const { execute } = useApiHandler()
    await execute(() => Promise.reject(errore(409, envelope({ hint: frase }))))
    expect(notifiche.error).toHaveBeenCalledWith('Messaggio dal backend', frase)
  })

  it('la soluzione viaggia su tutti e tre i rami del toast', async () => {
    const frase = 'Segnalare al supporto citando il request_id.'
    // 1) sistema (500): e' gia' persistente, la frase si aggiunge e basta.
    const h1 = useApiHandler()
    await h1.execute(() => Promise.reject(errore(500, envelope({ hint: frase }))))
    expect(notifiche.systemError).toHaveBeenCalledWith('Messaggio dal backend', frase)
    // 2) con un gesto: la frase sta FRA il testo e i pulsanti.
    azioniFinte = [{ label: 'Apri Fattura 820', esegui: () => {} }]
    const h2 = useApiHandler()
    await h2.execute(() => Promise.reject(errore(409, envelope({ targets: [{ type: 'FATTURA', id: '820' }], hint: frase }))))
    expect(notifiche.errorConAzioni).toHaveBeenCalledWith('Messaggio dal backend', azioniFinte, frase)
  })

  it('⚠️ senza soluzione il toast resta ESATTAMENTE quello di prima', async () => {
    // La non-regressione che conta: la stragrande maggioranza degli errori una
    // soluzione non ce l'ha, e per quelli non deve cambiare niente — ne' il
    // testo ne' la durata (`null` non e' una stringa vuota).
    const { execute } = useApiHandler()
    await execute(() => Promise.reject(errore(400, envelope({}))))
    expect(notifiche.error).toHaveBeenCalledWith('Messaggio dal backend', null)
  })

  it('`silent` spegne il toast ma NON la diagnostica', async () => {
    const { execute, campiErrati, soluzione } = useApiHandler()
    await execute(() => Promise.reject(errore(400, envelope({ fields: ['codice'], hint: 'fai cosi' }))), { silent: true })
    expect(notifiche.error).not.toHaveBeenCalled()
    expect(campiErrati.value).toEqual(['codice'])
    expect(soluzione.value).toBe('fai cosi')
  })

  it('`azioniGestite` → nessun toast, ma solo per l’azione dichiarata', async () => {
    const { execute } = useApiHandler()
    await execute(() => Promise.reject(errore(409, envelope({ ui_action: 'confirm_and_retry' }))), {
      azioniGestite: ['confirm_and_retry'],
    })
    expect(notifiche.error).not.toHaveBeenCalled()
    // Un'altra `ui_action` non e' coperta dalla dichiarazione: il toast riparte.
    await execute(() => Promise.reject(errore(400, envelope({ ui_action: 'show_error_banner' }))), {
      azioniGestite: ['confirm_and_retry'],
    })
    expect(notifiche.error).toHaveBeenCalledOnce()
  })

  it('⚠️ un codice in CODICI_SENZA_TOAST tace, e la lista deve restare cortissima', async () => {
    const { execute } = useApiHandler()
    await execute(() => Promise.reject(errore(400, envelope({ code: 'E_UI_LISTA_EMITTENTE_DA_SCEGLIERE' }))))
    expect(notifiche.error).not.toHaveBeenCalled()
    expect(notifiche.systemError).not.toHaveBeenCalled()
  })

  it('⛔ `CODICI_SENZA_TOAST` e’ un Set: un codice che si chiama come un metodo di Object non passa', async () => {
    // Se fosse un oggetto letterale, `MAPPA['toString']` risulterebbe presente
    // per ereditarieta' dal prototipo e l'errore sparirebbe in silenzio.
    const { execute } = useApiHandler()
    await execute(() => Promise.reject(errore(400, envelope({ code: 'toString' }))))
    expect(notifiche.error).toHaveBeenCalledOnce()
  })
})

describe('useApiHandler — loading', () => {
  it('torna false anche quando la chiamata fallisce', async () => {
    const { execute, loading } = useApiHandler()
    await execute(() => Promise.reject(errore(500, envelope({}))))
    expect(loading.value).toBe(false)
  })
})
