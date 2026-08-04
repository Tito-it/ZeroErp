# Brief BE/FE — le vie d'uscita per l'operatore (la metà a video)

> **Chi scrive:** BE/FE (`dev/backend-tid`), 2026-08-04.
> **A chi:** Tid, e per conoscenza al team DB.
> **Da dove nasce:** [brief-db-vie-uscita-operatore.md](brief-db-vie-uscita-operatore.md) §5
> — «BE/FE (loro metà): rendere disponibili i verbi «Annulla» su preventivo e
> ordine; mostrare `reasons` sui bottoni spenti; mostrare `nessuna_azione_key`
> quando la lista è vuota».

---

## 1. In una riga

Il verbo «Annulla» **era già arrivato a video da solo** — è data-driven, e la
riattivazione delle tre transizioni nei CSV è bastata. Quello che mancava, e che
questo giro ha fatto, è **il vocabolario per dire di no**: le policy HTTP dei tre
codici errore nuovi, le otto traduzioni, e il posto dove si scrive «qui non c'è
niente da azionare, ecco cosa fare invece».

## 2. Verificato sul database vivo, non dedotto

Prima di scrivere una riga, le capability sono state interrogate sul DB di
sviluppo (canale di sistema, `system_process_context` — le tabelle documento
hanno RLS e senza GUC un operatore vedrebbe zero righe e concluderebbe il
falso):

| Prova | Esito |
| --- | --- |
| `fn_available_actions_preventivo` su un ACCETTATO (#1816) | `annulla` **presente e abilitata** |
| idem su un EMESSO (#535) | `accetta`, `rifiuta`, **`annulla`**, `crea_revisione` |
| `fn_available_actions_ordine` su un CONFERMATO (#633) | `annulla` **presente e abilitata** |
| `fn_check_*_annullabile` | entrambe le funzioni esistono e rispondono |
| `nessuna_azione_key` nel blob capability | **assente** — è il §6 ancora aperto del brief DB |
| `fn_available_actions_ordine` su un EVASO (#5388) | **zero azioni, nessuna spiegazione** |

Le due righe in grassetto sono la ragione per cui questo brief non chiude il
cantiere: vedi §5.

## 3. Backend — le tre policy

`apps/core/services/error_policies.py`: dichiarati `E_PREV_ORDINE_GIA_GENERATO`,
`E_ORD_ANNULLA_CON_DDT`, `E_ORD_ANNULLA_IN_COMMESSA`, tutti **409** +
`show_error_banner` + messaggio che dice cosa fare («…per farla rientrare si
registra un reso», «…annulla prima le attività in commessa»).

Nient'altro serviva: il codice `E_*` sollevato dal guard DB viene già estratto
dal messaggio PostgreSQL — da `ordini_service._db_errors` per l'ordine, dal
middleware (`ErrorTranslator._extract_app_error_code`) per il preventivo, che
non ha traduttore di dominio. Dichiarare la policy è ciò che trasforma un
generico *400 «Errore di validazione»* in un 409 parlante. Provato:

```text
E_PREV_ORDINE_GIA_GENERATO   http=409   messaggio di dominio
E_ORD_ANNULLA_CON_DDT        http=409   messaggio di dominio
E_ORD_ANNULLA_IN_COMMESSA    http=409   messaggio di dominio
```

**Nessun endpoint nuovo.** L'annullamento passa dal cambio stato generico che
già esiste (`POST /vendite/preventivi/<id>/stato/`, `POST /vendite/ordini/<id>/stato/`):
il target arriva da `available_actions[].target_state`, il service non duplica il
grafo, il guard DB decide. È il modello DB-first applicato: un verbo nuovo non è
codice nuovo, è una riga di matrice.

## 4. Frontend

### 4.1 Il verbo «Annulla»: zero righe di codice

`mapAvailableActionsToDrawerActions` + `DrawerActionsBar` rendono qualunque voce
di `available_actions`; `PreventiviDrawer.onCambiaStato` e `OrdiniDrawer.onAction`
instradano già le transizioni generiche alla conferma + `store.cambiaStato`.
`requires_confirm: true` nei seed → il dialog di conferma c'è. Le due label
(`vendite.preventivi.azione_annulla`, `vendite.ordini.azione_annulla`) erano già
nei locales. **Il pulsante funziona perché il modello è data-driven, non perché
qualcuno l'ha aggiunto.**

Idem per i `reasons` sui bottoni spenti: il building block li rende già (tooltip
multi-riga, `labelOrCode` fail-visible) dal brief guard-righe. Non appena il DB
li esporrà, si accendono.

### 4.2 `nessuna_azione_key` — prop `infoKey` di `DrawerActionsBar`

Il pezzo nuovo. Un'unica prop sul building block, non un blocco copiato negli
otto drawer:

```vue
<DrawerActionsBar :actions="drawerActions" :info-key="detail?.nessuna_azione_key || ''" />
```

- il testo **non** viene dal DB: viaggia solo l'indirizzo i18n, risolto con
  `labelOrCode` (chiave assente → si vede la chiave grezza, mai il vuoto);
- **la barra compare anche a zero azioni** quando c'è la chiave — altrimenti
  l'unica cosa che spiega lo stato sparirebbe proprio nel caso in cui serve.
  Due drawer avevano `v-if="drawerActions.length"` sulla barra
  (`CommessaGestioneDrawer`) o la nascondevano di fatto: il guard è stato esteso;
- resa come nota muted (`.app-drawer-actions-info`), non come banner: è una
  risposta, non un allarme. Convive con le azioni `manage`/`secondary` (note,
  PDF) che restano disponibili anche negli stati chiusi.

Cablata su **tutti e otto** i drawer documento vendite (preventivo, ordine, DDT,
reso, offerta, contratto, commessa, lotto), non sui soli due domini che oggi
hanno il `meta` popolato: il giorno in cui il team DB scrive la chiave su un
altro stato, non c'è codice da toccare. Standard aggiornato in
`frontend-standards.md` §«Azioni Drawer», catalogo BB aggiornato.

### 4.3 Le otto chiavi i18n (it + en)

Tradotte le otto del §5.1 del brief DB. Testi presi dalla tabella §4 del brief:
il DDT consegnato dice di usare il **reso**, l'ordine evaso dice che lo stato
**si ricalcola dai DDT**.

## 5. Cosa resta fermo, e da chi dipende

**Il §6 del brief DB, ultima riga: `reasons` e `nessuna_azione_key` non sono
ancora esposte da `fn_available_actions_preventivo` / `_ordine`.** Conseguenze
oggi in campo, misurate:

| Situazione | Cosa vede l'operatore adesso |
| --- | --- |
| Preventivo già in commessa (es. #302, #301, #299) | «Annulla» **acceso**; il rifiuto arriva a click fatto — ora almeno con un 409 e un messaggio, non con un errore generico |
| Ordine EVASO / PARZIALMENTE_EVASO | Barra azioni **vuota e muta** |
| DDT CONSEGNATO / RESO | Idem |

Il frontend è pronto per tutti e tre: appena le capability portano i campi, i
bottoni si spengono col motivo e le note compaiono. **Non c'è altro lavoro BE/FE
su questo cantiere finché quel passo non è fatto.**

## 6. Due cose trovate strada facendo

### 6.1 🔴 Il presidio i18n era cieco proprio sul caso «nessuna azione»

`scripts/check_i18n_keys.py` esiste per rendere rumorosa una chiave i18n emessa
dal DB e non risolvibile dal frontend. Guardava però solo le proprietà
`label_key`/`reason_key`, e fra i seed solo i file `transizioni_stati_*.csv`.
`nessuna_azione_key` vive nel `meta` degli **stati** (`stati_doc_*.csv`): le
quattro chiavi nuove erano **invisibili al guard**, che restava verde.

È la stessa classe di difetto che il guard esiste per intercettare, e qui era
peggio del solito: quando manca la label di un pulsante resta almeno il pulsante
muto a segnalare che qualcosa c'era; qui non resta niente. Guard esteso a
entrambe le dimensioni (proprietà + famiglia di seed).

Effetto collaterale: il guard, ora che vede di più, ha reso **verdi 7 chiavi che
erano rosse da prima** e che nessuno stava traducendo — 4 di
`vendite.lotti.azione_reason.*` (brief azioni-lotto, BE/FE chiuso ieri) e 3 di
`vendite.commesse.*` (cantiere emittibilità). Erano motivi ostativi che il DB
mandava e il frontend non sapeva dire. Tradotte: costavano una riga l'una e
lasciarle rosse avrebbe reso inservibile il presidio anche per questo cantiere.
Sono **fuori dal perimetro** di questo brief: segnalate qui perché il merito
appartiene ad altri due cantieri.

### 6.2 🔴 Un rifiuto che l'operatore non può leggere

`vendite.fn_cambia_stato_preventivo` solleva `PREV_ANNULLAMENTO_COMMESSA_ATTIVA`
— codice **senza prefisso `E_`**, già noto al team DB (§7.3 del brief DB, dove è
citato come limite dichiarato del presidio catalogo). L'estrattore di codici
applicativi del backend cerca `E_[A-Z]...`: questo codice non lo aggancia, quindi
la risposta degrada a `E_DATABASE` — messaggio generico, dettaglio tecnico
nascosto per policy. Verificato:

```text
[PREV_ANNULLAMENTO_COMMESSA_ATTIVA] …  ->  E_DATABASE  http=400  "Errore durante l'operazione database."
```

Fino a ieri era teoria: dallo stato `ACCETTATO` il preventivo **non si annullava
affatto**. Da oggi che l'annullamento è tornato disponibile, è un percorso vivo:
un preventivo con righe già `EMESSA` in commessa risponde all'operatore con un
errore che non spiega nulla.

**Non l'ho tappato lato BE di proposito.** Allargare la regex ai literal
maiuscoli generici produce falsi positivi (lo stesso conto già fatto nel §7.3 del
brief DB: 31), e mappare a mano il singolo codice sarebbe una seconda regola di
annullamento in un terzo posto — esattamente ciò contro cui nasce la R2 di questo
cantiere. **La soluzione giusta è il consolidamento §7.3 già deciso**:
`fn_check_preventivo_annullabile` assorbe il criterio della porta, e quel codice
sparisce da solo. Fino ad allora il buco resta, ed è scritto qui.

## 7. Definizione di «fatto»

- [x] tre codici errore a policy (409 + messaggio d'azione) — `error_policies.py`;
- [x] verbi «Annulla» verificati end-to-end sulle capability vive (nessun codice necessario);
- [x] prop `infoKey` su `DrawerActionsBar` + CSS + cablaggio sugli 8 drawer vendite;
- [x] 8 chiavi i18n del brief tradotte it/en;
- [x] presidio `check_i18n_keys.py` esteso a `nessuna_azione_key` + `stati_doc_*.csv` — **verde**;
- [x] `vite build` pulito, 689 test core + 1480 test vendite verdi;
- [ ] **validazione in-app di Tid** (annullamento preventivo da EMESSO/ACCETTATO e ordine da CONFERMATO);
- [ ] **attesa DB**: esposizione `reasons` + `nessuna_azione_key` nelle due `fn_available_actions_*` → allora la nota e i bottoni spenti si vedono, senza altro lavoro FE;
- [ ] **attesa DB**: consolidamento §7.3 (chiude il §6.2 qui sopra).
