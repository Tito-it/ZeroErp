# Brief di design — Attività UI lanciabile da flusso (data-driven)

> **Tipo**: brief di design (proposta, non specifica di contratto). Richiede l'OK
> di Tid prima di passare a codice/DB ([[feedback_regola_del_2_estrai_bb]],
> [[feedback_no_quick_fix_soluzione_assoluta]]).
> **Data**: 2026-06-14 · **Stato**: PROPOSTA, attende conferma
> **Origine**: PRA-0000171 (2° processo che chiede "eseguire l'attività dentro la
> pratica") → trigger per promuovere il meccanismo da hardcoded a data-driven.

---

## 1. Problema

Il modello ([analisi-pratiche-domini-anello3 §5.8](analisi-pratiche-domini-anello3.md))
prevede che ogni attività di dominio abbia **due punti di ingresso**: autonomo dal
menù **e dentro un flusso di pratica**. Oggi il secondo punto di ingresso è
**implementato ma hardcoded al solo processo PREVENTIVI** nel FE:

- [FlussoDrawer.vue](../../../frontend/src/pratiche/components/FlussoDrawer.vue):
  costanti `TIPO_PREVENTIVI_PREFIX`, `TEMPLATE_PREVENTIVAZIONE`,
  `TEMPLATE_APPROVAZIONE_CLIENTE`; il pulsante "Apri preventivo collegato" è
  visibile solo se `tipo_prestazione_codice` inizia con `PREVENTIVI` **e** il
  template è `PREVENTIVAZIONE`.

Conseguenza: un secondo processo (es. PRA-0000171) che vuole aprire lo **stesso**
drawer preventivi dal suo flusso non lo può fare — il gate non lo riconosce. È il
debito previsto da §1.3 (astrazione promossa **dopo il 2° consumatore**).

## 2. Principio — specchio FE del pattern handler (Pattern B)

Il BE ha già il pattern data-driven per l'**automazione server-side**:
`template_flussi.handler_id` → `handler_flussi.handler_key` → `HANDLER_MAP` Python
(`dispatch_handler` su `IN_CORSO`). Proponiamo il **gemello lato FE** per
l'**attività interattiva** (aprire un drawer di dominio):

> `template_flussi.azione_ui_key` → registry FE `UI_ACTIVITY_REGISTRY` →
> componente/drawer del dominio.

Stesso vocabolario ("un template dichiara, il motore esegue per dati"), zero
hardcoding per tipo_prestazione, ogni futuro processo eredita la capacità
configurando solo il template.

## 3. Modello dati (→ brief al team DB, non eseguito da BE agent)

Su `pratiche.template_flussi`:

- **`azione_ui_key`** `varchar` NULLABLE — codice dell'attività UI da offrire nel
  flusso (es. `APRI_PREVENTIVO`). NULL = nessuna attività interattiva (il flusso
  resta avvia/completa standard). Valore libero validato **per registrazione**
  lato FE (chiave non nel registry → nessun pulsante, fail-safe), non un FK a
  tabella codici (mirror di `handler_key` che è testo, non lookup).
- **(opzionale) `azione_ui_params`** `jsonb` DEFAULT `'{}'` — parametrizzazione
  (mirror `handler_params`), es. modalità di aggancio. Da introdurre solo se serve
  al 2° caso reale (no YAGNI).
- **Seed**: valorizzare `azione_ui_key` sui template dei processi che aprono un
  documento dal flusso. Famiglia documenti confermata (Tid 2026-06-15):
  `APRI_PREVENTIVO`, `APRI_OFFERTA`, `APRI_CONTRATTO`. **Ordini esclusi**: nascono
  solo a valle (push da preventivo/offerta via handler), non si aprono in bianco
  da un flusso → nessuna chiave `APRI_ORDINE`.

> Nessun `NOT NULL`: coerente con §5.8.2 (l'aggancio è sempre opzionale).
>
> **3 consumatori reali (preventivo/offerta/contratto)** → la promozione concentrica
> è ampiamente giustificata (§1.3: astrazione dopo il 2°, qui siamo al 3°).

## 4. Backend (espone il campo, nessuna logica)

I flussi già fanno `LEFT JOIN pratiche.template_flussi tf` e proiettano
`tf.codice`, `tf.handler_id IS NOT NULL AS has_handler`
([pratiche_repository.py:309,369](../../../backend/apps/pratiche/db/pratiche_repository.py#L309)).
Aggiungere `tf.azione_ui_key` (+ params) alle stesse SELECT di `get_flusso`,
`list_flussi` e della query **percorso** (così la roadmap sa quali step hanno
un'attività UI). Zero logica: solo passthrough del campo.

## 5. Frontend (il cuore della generalizzazione)

1. **Registry** `frontend/src/pratiche/uiActivityRegistry.js` — una voce per
   documento della famiglia (preventivo/offerta/contratto):
   ```
   APRI_PREVENTIVO → {
     loadComponent: () => import('.../PreventiviDrawer.vue'),  // lazy, no coupling
     onSaved: (ctx) => collegaPratica(ctx.savedId, { pratica_id: ctx.praticaId }),
     lockFields: ['istanza_utility_id', 'billing_account_id'],  // vedi §5-bis
     requiresActiveClient: false,   // preventivo ammette prospect (BA opzionale)
     label: 'pratiche.flusso_apri_preventivo', icon: 'pi pi-file-edit',
   }
   APRI_OFFERTA  → { ...drawer offerta,  lockFields: ['istanza_utility_id','billing_account_id'], requiresActiveClient: true }
   APRI_CONTRATTO→ { ...drawer contratto, lockFields: ['istanza_utility_id','billing_account_id'], requiresActiveClient: true }
   ```
   Mirror del `HANDLER_MAP` BE: chiave → componente del dominio, import lazy per
   non accoppiare `pratiche → vendite` (stessa cautela del registry handler).
   Ogni voce **dichiara** cosa eredita/blocca (`lockFields`) e se richiede un
   cliente attivo (`requiresActiveClient`): così l'asimmetria tra documenti vive
   nei **dati del registry**, non in `if` sparsi.
2. **FlussoDrawer**: l'azione hardcoded `apri-preventivo` diventa **generica**
   `apri-attivita`, visibile se `flusso.template_azione_ui_key` è valorizzata **e**
   registrata **e** (se `requiresActiveClient`) la pratica ha un cliente attivo
   (BA presente nel contesto pratica, §5-bis); emette `open-attivita` con
   `{ key, praticaId, params }`. Rimosse le 3 costanti PREVENTIVI e il gate
   `isPreventivi`.
3. **PraticheDashboard**: ospita un **host generico** che risolve il componente
   dal registry (un `<component :is>` dinamico) e ne gestisce `onSaved` dal
   registry. Sostituisce l'attuale wiring fisso `PreventiviDrawer` +
   `onOpenPreventivo`.
4. **PraticaPercorso**: lo step con `azione_ui_key` può mostrare un'affordance
   ("Apri preventivo/offerta/contratto") già nella roadmap (nice-to-have).

## 5-bis. Concern accoppiato: eredità + lock di cliente/istanza

Aprendo il documento dalla pratica, **cliente (BA) e istanza** devono arrivare dal
contesto pratica, valorizzati e **bloccati** (non possono divergere). È un concern
distinto ma **paritetico** all'apertura del drawer, e si generalizza sugli stessi
3 documenti. Dettaglio in:

- [brief-db-pratica-preventivo-contesto-cliente.md](brief-db-pratica-preventivo-contesto-cliente.md)
  (prerequisito DB: la pratica espone il contesto cliente risolto — BA + istanza
  coerenti — document-agnostico).
- [brief-fe-pratica-preventivo-cliente-bloccato.md](brief-fe-pratica-preventivo-cliente-bloccato.md)
  (piano FE: pre-fill + lock; per documento i campi da bloccare arrivano da
  `lockFields` del registry).

Asimmetria documenti (verificata 2026-06-15, decisioni Tid):

| Documento | apre dal flusso | eredita/blocca | cliente attivo richiesto |
| --- | --- | --- | --- |
| preventivo | sì (`APRI_PREVENTIVO`) | istanza + BA(opz.) | no (ammette prospect) |
| offerta | sì (`APRI_OFFERTA`) | istanza + BA | **sì** |
| contratto | sì (`APRI_CONTRATTO`) | istanza + BA | **sì** |
| ordine | **no** (push a valle) | BA + utility via push | n/a |

## 6. Scope e confini (concentrico, onesto)

- **In scope**: apertura del drawer di dominio dal flusso per la **famiglia
  preventivo/offerta/contratto** (lancio attività interattiva), con eredità+lock
  cliente/istanza (§5-bis) e gating `requiresActiveClient`.
- **Ordini fuori scope**: nascono dal **push a valle** (handler preventivo/offerta
  → ordine), non si aprono in bianco dal flusso. L'eredità del cliente per gli
  ordini è già garantita dal push esistente, non da questo meccanismo.
- **Fuori scope (axe separato, follow-up)**: il **routing del completamento** verso
  un endpoint di dominio (oggi `APPROVAZIONE_CLIENTE → M2 approvazione-flusso`,
  [FlussoDrawer.vue:129-147](../../../frontend/src/pratiche/components/FlussoDrawer.vue#L129)).
  È un secondo concern data-driven (`template_flussi.completa_endpoint_key` →
  registry FE di completion-handler). **Predisposizione**, non costruito ora: un
  solo consumatore (M2 preventivi) → non ancora maturo (§1.3).

## 7. Cosa NON si rompe

- I drawer standalone (percorso autonomo da menù) invariati (§5.8.2): pre-fill e
  lock scattano **solo** col contesto pratica.
- Il path BE handler (`CONFERMA` server-side) e il push ordini invariati: questo
  brief tocca solo l'**attività interattiva FE**, ortogonale all'automazione.
- Flussi senza `azione_ui_key`: comportamento attuale (solo avvia/completa),
  nessuna regressione.

## 8. Passi (dopo OK Tid)

1. Brief DB per `template_flussi.azione_ui_key` (+ params opz.) + seed sui template
   che aprono un documento (`APRI_PREVENTIVO`/`APRI_OFFERTA`/`APRI_CONTRATTO`) →
   team DB (`dev/db-tid`). In parallelo, il prerequisito cliente/istanza (§5-bis,
   brief DB dedicato).
2. BE: esporre `azione_ui_key` nelle 3 query flusso/percorso (passthrough).
3. FE: registry (3 voci) + FlussoDrawer generico + host dashboard + lock
   cliente/istanza (§5-bis) + (opz.) affordance percorso. Rimozione costanti
   hardcoded.
4. i18n: chiavi `flusso_apri_*` per i 3 documenti (`flusso_apri_preventivo` esiste).

---

*Brief di design — attività UI da flusso data-driven — ZeroERP (2026-06-14).
PROPOSTA in attesa di conferma.*
