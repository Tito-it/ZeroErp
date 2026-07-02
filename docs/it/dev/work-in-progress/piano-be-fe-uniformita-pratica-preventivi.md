# Piano di sviluppo BE/FE — Uniformità pratica preventivi

> **Tipo**: piano operativo (BE/FE) · **Data**: 2026-06-30 · **Stato**: 🟢 in corso —
> Fasi 0-4 implementate. Ex-blocco auto-chiusura a SMISTAMENTO **RISOLTO** con la regola
> di chiusura "nessun lavoro pendente" (**bivio-per-esito**, motore DB + BE):
> [brief-db-chiusura-pratica-nessun-lavoro-pendente.md](../work-done/brief-db-chiusura-pratica-nessun-lavoro-pendente.md)
> (✅ **DB applicato + pgTAP verde**, ✅ **BE fatto + 1764 test verdi** — brief §11.6, chiuso in work-done).
> 9013/9014 `obbligatorio=true` percorribili solo sul ramo merce via esito `MERCE_PRESENTE` di
> SMISTAMENTO (niente creazione on-demand / chaining). ✅ **Smoke E2E BE verde** (2026-07-01,
> `smoke-test-pratica-preventivi-bivio.sh`, rami MERCE + SOLO_SERVIZI). **Resta solo il FE**
> (item residui sotto).
> **Analisi (il perché)**: [analisi-uniformita-pratica-preventivi.md](analisi-uniformita-pratica-preventivi.md)
> **Prerequisiti DB**: ✅ tutti applicati (catalogo `PREVENTIVI` 9004 + flussi 9009-9014,
> `obsoleto_dal` + lookup/guard) — brief in `work-done`.
>
> **Principio guida**: la pratica **orchestra** ma ogni passo **riusa l'azione/UI del
> programma standalone** (no handler che decide al posto dell'operatore). Tutto ciò che è
> "scorciatoia" va nel **programma base**, ereditato dalla pratica.

---

## 0. Prerequisiti e punti aperti

- **DB pronto**: tipo 9004, flussi 9009-9014, `obsoleto_dal`, `fn_get_lookup_codici`
  (`p_includi_obsoleti DEFAULT true`), guard `E_CATALOGO_OBSOLETO_NUOVA_ISTANZA`.
- 🟡 **Da confermare col DB prima della Fase 3**: prerequisito flusso **`60 ← 50`**
  (INVIO_COMMESSA dopo CONFERMA_ORDINE); oggi è `60 ← 40`. Se il DB lo raddrizza, la Fase 3
  non cambia; se resta `60 ← 40`, la sequenzialità la garantisce comunque la creazione
  on-demand (Fase 2) + lo stato ordine.
- **Componenti standalone riusabili già esistenti** (mappati): `PreventiviDrawer.vue`,
  `PreventiviSmistamentoPanel.vue`, dialog accettazione, azioni ordine (Emetti / push commessa),
  service accettazione + `crea_revisione` + `push_a_ordine`/`push_a_commessa`.

---

## Fase 0 — Quick wins indipendenti (basso rischio, alto valore) — ✅ FATTA

> B6 (BE: `includi_obsoleti` view→service→repo→fn DB; FE: prop `LookupSelect.includiObsoleti`,
> PraticaDrawer create passa `false`) e B7 (policy `E_CATALOGO_OBSOLETO_NUOVA_ISTANZA`→409).
> B8 (cleanup seed smoke `regole_generazione` 9001) resta al team DB (igienico). Test core verdi.

Sblocca subito la selezione del nuovo tipo e chiude i due gap del catalogo obsoleto.

| ID | Layer | Deliverable | Accettazione |
|---|---|---|---|
| B6 | BE core | Passare **`includi_obsoleti=false`** nei lookup di **selezione-per-il-nuovo** dei cataloghi con `obsoleto_dal` (tipo per nuova pratica) | Nuova pratica offre `PREVENTIVI` (9004), non 9002/9003; filtro lista per tipo mostra ancora gli obsoleti |
| B7 | BE/FE | Mappare `E_CATALOGO_OBSOLETO_NUOVA_ISTANZA` (id 500) nel registry errori (messaggio parlante) | Tentata creazione su tipo obsoleto → errore leggibile, non generico |
| B8 | DB seed (igienico, opz.) | Ritirare riga smoke-test `regole_generazione` 9001 → tipo obsoleto | Nessuno smoke inciampa nel guard |

> Nota: B6 è il punto in cui il default DB `true` (mostra tutto) viene ristretto dal chiamante.
> Verificare i call-site del lookup tipo-pratica e distinguere "selezione nuovo" (passa `false`)
> da "filtro lista/storico" (lascia il default).

---

## Fase 1 — Accettazione uniforme (chiude bug competenza + modalità cablata) — ✅ FATTA

> BE (B4): `meta` passthrough nel completamento flusso (`completa_flusso`/
> `avvia_e_completa_flusso` → `dispatch_handler_eventi(extra_meta=...)`, non persistito);
> `accetta_preventivo` legge modalità/competenza da `meta` e le persiste sul preventivo
> (DIFFERITA senza competenza → `E_VENDITA_COMPETENZA_RICHIESTA`; fallback neutro retro-compat).
> FE (F3a): estratto componente condiviso `PreventivoAccettazioneDialog.vue` (riusato da
> `PreventiviDrawer`); `FlussoDrawer` apre la dialog in modo generico via nuovo
> `flussoCompletionRegistry.js`. +5 test handler, firma `meta` nelle api. Test/lint/build verdi.
>
> Review post-sviluppo: estratto `parse_competenza_mese` in `_handler_helpers` (era duplicato
> nei 2 handler); fix fragilità `FlussoDrawer` (reset dialog cachata al cambio flusso).

L'accettazione nella pratica usa lo **stesso dialog** dello standalone; modalità + competenza
si salvano **sul preventivo**. L'event-handler `vendita.accetta_preventivo` su flusso 30 è già
wirato a DB.

| ID | Layer | Deliverable |
|---|---|---|
| B4 | BE vendite | Il path di completamento flusso 30 riusa il **service accettazione standalone** → persiste `fatturazione_immediata` + `competenza_mese` sul preventivo. Rimuove ogni dipendenza da `meta["competenza_fatturazione"]` |
| F3a | FE | Completando APPROVAZIONE_CLIENTE mostra il **dialog accettazione** standalone (toggle immediata + datepicker competenza); passa i dati al completamento flusso |

**Accettazione**: in una pratica, accettare il preventivo chiede modalità/competenza e le salva
sul preventivo; nessun `E_VENDITA_COMPETENZA_RICHIESTA` a valle. (Bug §3.1.2 chiuso.)

---

## Fase 2 — Smistamento via pannello standalone + on-demand 50/60 — ✅ FATTA

> **B1 ✅ (2026-06-30)**: binding DB `vendita.post_smistamento` su SMISTAMENTO
> COMPLETATO/POSITIVO seedato dal team DB; implementato `PostSmistamentoHandler`
> (`apps/vendite/handlers/post_smistamento_handler.py`, registrato in
> `apps.py:ready()`): se lo smistamento ha prodotto un ordine merce, lo aggancia
> alla pratica (`pratiche_sorgenti` COLLEGATO) e crea on-demand CONFERMA_ORDINE +
> INVIO_COMMESSA (template risolti per codice dal percorso, idempotente); se
> tutto-servizi non crea nulla. +4 test handler. Limite noto: aggancia il primo
> ordine (consegne parziali = 1:N) — caso pratica tipico = 1 ordine.

> ✅ **F2a**: il flusso SMISTAMENTO (azione_ui `SMISTAMENTO`) apre lo stesso `PreventiviDrawer`
> sul **ROOT della pratica** (nuovo endpoint BE `GET /vendite/preventivi/root-per-pratica/` +
> `getRootPerPratica` + voce `uiActivityRegistry.SMISTAMENTO`); in ACCETTATO mostra il Pannello
> Smistamento. ✅ **F1**: etichetta "Smista tutto" quando destinazione unica + tutte selezionate
> (il pannello preseleziona già le residue). Test BE 960 + lint/build verdi.
> 🔴 **B1 (in attesa binding DB)**: handler `vendita.post_smistamento` su SMISTAMENTO COMPLETATO
> → aggancia l'ordine alla pratica + crea on-demand 9013/9014 se c'è ordine merce. Brief:
> [brief-db-binding-smistamento-handler.md](../work-done/brief-db-binding-smistamento-handler.md). L'handler BE
> si implementa quando il binding è seedato.

Il flusso SMISTAMENTO (40) apre il **Pannello Smistamento** standalone; lo split usa gli
endpoint esistenti (`genera_ordine` / `push_commessa`). Al completamento, se è nato un ordine
merce, si **creano on-demand** i flussi 50/60.

| ID | Layer | Deliverable |
|---|---|---|
| F1 | FE | **Pannello Smistamento (base)**: pulsante **"Smista tutto"** quando le righe residue hanno **destinazione unica** (riuso standalone + pratica) |
| F2a | FE | Flusso 40 apre lo **stesso** `PreventiviSmistamentoPanel`; chiave azione UI `SMISTAMENTO` nel registry |
| B1 | BE vendite | Al completamento smistamento (event-driven): se è stato prodotto un **ordine merce**, **crea on-demand** i flussi 50/60 (`crea_flusso`); se tutto-servizi, la commessa è già nata e 50/60 non si creano |

**Accettazione**: preventivo misto → l'operatore sceglie le righe (o "Smista tutto" se natura
unica); merce→ordine, servizi→commessa; 50/60 compaiono **solo** se c'è ordine merce.

---

## Fase 3 — Ordine→commessa espliciti (merce arriva in commessa) — ✅ FATTA (+ review)

> **Review 2026-06-30 — bug critico corretto**: il guard `trg_flussi_a10_guard_prerequisiti_ins`
> è **BEFORE INSERT** → i prerequisiti sono enforced alla **creazione**. `PostSmistamentoHandler`
> creava sia CONFERMA_ORDINE sia INVIO_COMMESSA → la creazione di INVIO_COMMESSA **falliva**
> (prereq `CONFERMA_ORDINE POSITIVO` non ancora soddisfatto). Corretto: l'handler crea solo i
> flussi a valle **percorribili** (prereq soddisfatti ora) → a smistamento solo CONFERMA_ORDINE;
> INVIO_COMMESSA nasce alla chiusura di CONFERMA_ORDINE (operatore dal percorso, o binding
> opzionale dello stesso handler su 9013 COMPLETATO — vedi brief). Test handler aggiornati.
> Doc API `api_ordini` (per-pratica) aggiornata.

> **F2b + B2/B3 ✅ (2026-06-30)**: i flussi a valle aprono l'**OrdiniDrawer**
> sull'ordine COLLEGATO della pratica (azioni standalone Emetti/push riusate):
> - BE: endpoint `GET /vendite/ordini/per-pratica/` + `ordini_service.get_ordine_per_pratica`
>   + `OrdiniRepository.get_ordine_id_by_pratica` (legge `pratiche_sorgenti` COLLEGATO).
> - FE: voci registry `CONFERMA_ORDINE` (Emetti) e `INVIO_COMMESSA` (push commessa),
>   `requiresExisting` (ordine deve esistere), helper `ordineDrawerProps`/`resolveOrdinePerPratica`,
>   `getOrdinePerPratica`, i18n.
> - **Ritiro handler monolitico** `push_preventivo`: marcato **DEPRECATO** (non più
>   usato dal catalogo 9004; resta registrato per i soli tipi obsoleti 9002/9003
>   storici, rimozione fisica quando saranno eliminati).
>
> Test BE vendite 964 + FE lint/build verdi. **Pendenti**: review critica + doc API
> (`api_ordini` per-pratica) + smoke E2E live.

| ID | Layer | Deliverable |
|---|---|---|
| F2b | FE | Flussi 50/60 aprono le **azioni ordine** standalone (Emetti / push a commessa); chiavi `CONFERMA_ORDINE` / `INVIO_COMMESSA` nel registry |
| B3 | BE vendite | **CONFERMA_ORDINE** (50): Emetti ordine `DRAFT→CONFERMATO` (+PDF) agganciato al flusso |
| B2 | BE vendite | **INVIO_COMMESSA** (60): push ordine `CONFERMATO→commessa`, **modalità presa dal preventivo** (non da `handler_params`); giornale `DOMINIO_*` + `pratiche_sorgenti` (ordine/commessa COLLEGATO) |

**Accettazione**: per un preventivo merce, a fine pratica esiste la **commessa** (no più ordine
fermo in DRAFT). (Bug §3.1.1 chiuso.) Verifica DB: catena preventivo EVASO → ordine CONFERMATO/EVASO
→ commessa PRONTA_FATTURAZIONE + giornale `DOMINIO_ORDINE_CREATO`/`DOMINIO_COMMESSA_CREATA`.

> **Ritiro handler monolitico** `vendita.push_preventivo`: a fine Fase 2-3 non è più
> dispatchato da alcun flusso → rimuovere (codice + eventuale binding residuo).

---

## Fase 4 — Revisione nella pratica (following rev attiva) — ✅ FATTA (no DB)

> **B5 ✅ (2026-06-30, solo BE, nessun DB)**: i resolver del ROOT preventivo
> (`get_preventivo_id_by_pratica_root` / `_by_flusso_root`) ora risolvono
> **numero+emittente → rev ATTIVA** (`vw_preventivi.is_attiva`) invece dell'uid
> agganciato: la pratica segue la revisione viva; annullando una revisione torna
> al predecessore (gratis da `is_attiva`). Reverse (`get_flusso_id_by_preventivo_root`)
> reso robusto: match per numero → qualsiasi rev trova il flusso (emissione di una
> rev successiva auto-completa PREVENTIVAZIONE). Risoluzione a read-time, nessun
> UPDATE/trigger; il numero si deriva dall'uid agganciato → **niente `meta` da
> popolare** (convenzione `ref_stable_key` rinviata, non serve). Verificato live su
> PRA-0000216 (ritorna la rev attiva 375). Test BE 1147 verdi.
>
> **F2c — nessuna modifica necessaria**: `crea_revisione` è **già esposto** nel
> drawer preventivo aperto da pratica (azione data-driven da `available_actions`,
> non filtrata; resa da `mapAvailableActionsToDrawerActions` se non readonly).
> L'analisi §3.1.3 "revisione assente" era imprecisa: il gap reale era il
> following-rev (B5).
>
> Caveat residuo (UX, non bloccante): re-aprire il preventivo per revisionarlo
> dopo che PREVENTIVAZIONE si è auto-completata all'emissione (riapertura di un
> flusso COMPLETATO) — flusso da rifinire separatamente.

| ID | Layer | Deliverable |
|---|---|---|
| F2c | FE | Drawer preventivo aperto da pratica **espone `crea_revisione`** (come standalone) |
| B5 | BE vendite | All'aggancio ROOT popola `pratiche_sorgenti.meta` (`ref_stable_key`=numero, `follow_active=true`); risolutore **`numero → rev attiva`** (via `vw_preventivi.is_attiva`) per "il preventivo della pratica" |

**Accettazione**: creata una revisione di un preventivo agganciato, la pratica mostra la **nuova
rev attiva**; annullata la revisione, torna al predecessore — senza UPDATE del link. (Bug §3.1.3 chiuso.)

---

## Ordine consigliato e dipendenze

1. **Fase 0** (indipendente, subito) — sblocca selezione tipo + errori catalogo.
2. **Fase 1** (accettazione) — fondamenta: modalità/competenza sul preventivo.
3. **Fase 2** (smistamento) — dipende da Fase 1 (preventivo ACCETTATO con dati).
4. **Fase 3** (ordine→commessa) — dipende da Fase 2 (esiste l'ordine merce) + conferma prereq `60←50`.
5. **Fase 4** (revisione) — ortogonale, eseguibile in parallelo dopo Fase 1.

## Verifica finale (smoke E2E pratica preventivi)

Rigiocare il caso PRA-0000216 sul nuovo tipo 9004:
- preventivo **misto** (merce + servizio) → accettazione con dialog → smistamento selettivo →
  ordine confermato + inviato a commessa, servizio in commessa diretta → preventivo EVASO,
  pratica CHIUSA, **commessa presente** a DB.
- preventivo **tutto-merce** → 50/60 presenti, commessa creata.
- preventivo **tutto-servizi** → 50/60 assenti, commessa diretta.
- selezione nuovo tipo: 9002/9003 non offerti; creazione forzata su obsoleto → errore 500.
- revisione dentro pratica → la pratica segue la rev attiva.

> Test BE per ogni fase (no regressioni); build/ESLint FE verdi; smoke E2E come criterio di chiusura.
