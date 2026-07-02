# Analisi — Uniformità pratica ⇄ programma standalone (preventivi/ordini/commesse)

> **Tipo**: analisi di design (non implementativa) · **Data**: 2026-06-29
> **Owner**: Tid · **Stato**: ✅ **CHIUSA** (2026-07-02) — principio applicato; DB+BE+FE fatti, ultimo residuo (handler monolitico) chiuso. (§9 backfill `data_apertura` = rinviato, non-lavoro.)
>
> **Origine**: smoke su pratica `PRA-0000216` (preventivo DIFFERITA, tutta merce).
> A video tutto verde, ma a DB **nessuna commessa**: l'ordine creato è rimasto
> DRAFT. Indagando sono emerse più **divergenze** fra il percorso pratica e il
> programma standalone preventivi.
>
> **Documenti collegati**: [gestione-preventivi.md](../../guide/gestione-preventivi.md)
> (§8 smistamento), [gestione-ordini.md](../../guide/gestione-ordini.md) (§9-§10
> conferma + push commessa), [gestione-pratiche-come-procedere.md](../work-in-progress/gestione-pratiche-come-procedere.md),
> [analisi-pratiche-domini-anello3.md](../work-in-progress/analisi-pratiche-domini-anello3.md) (§5 caso vendite).

---

## 1. Il principio (vincolo di progetto, deciso da Tid)

**La pratica non deve divergere dal programma standalone.** Tutto ciò che il
programma di gestione preventivi (e ordini, commesse, ...) offre come scelta
all'operatore — revisione, selezione righe da smistare, modalità di
fatturazione — la pratica **deve offrirlo allo stesso modo**, riusando le stesse
UI/azioni.

Corollario: eventuali **scorciatoie** (es. saltare la selezione righe quando
sono tutte di una sola natura) si implementano **nel programma base**, così la
pratica le eredita. Mai una scorciatoia che esista solo dentro la pratica: i due
percorsi devono restare **uniformi**, una sola fonte di verità del comportamento.

---

## 2. Come funziona davvero il modello preventivo → ordine → commessa

Dal catalogo ogni articolo porta una **natura di vendita** con destinazione fissa
(congelata sulla riga):

| Natura | Destinazione | Percorso reale |
|---|---|---|
| MERCE | ORDINE | preventivo → **ordine** → *(Emetti = conferma)* → *(Push a commessa)* → fattura |
| SERVIZIO_UNA_TANTUM | COMMESSA | preventivo → **commessa** diretta → fattura |
| SERVIZIO_RICORRENTE | CONTRATTO | bloccato sul preventivo → offerta→contratto |

Punto cruciale: **la merce non va mai diretta in commessa**. Passa da un
**ordine** (documento commerciale reale: numero, PDF di conferma, cliente
bloccato). La commessa della merce è solo il *veicolo di fatturazione* a valle
dell'ordine **confermato** (commessa `tipo=AUTO`). Per la merce servono quindi
**tre atti**, due dei quali sull'ordine (guida ordini §9-§10):
1. smistamento preventivo → ordine `DRAFT`;
2. **Emetti** ordine `DRAFT → CONFERMATO` (+ PDF) — obbligatorio prima del push;
3. **Push a commessa** `CONFERMATO → EVASO` → crea commessa AUTO → fattura.

Nel programma standalone tutte e tre sono passi espliciti dell'operatore.

---

## 3. Mappa delle divergenze (standalone vs pratica)

| Scelta operatore | **Standalone** | **Pratica `PREVENTIVI_DIFFERITA`** | Esito |
|---|---|---|---|
| **Accettazione**: modalità fatturazione + competenza | dialog su EMESSO→ACCETTATO, salvati sul preventivo | accettazione = completare il flusso APPROVAZIONE_CLIENTE (handler `accetta_preventivo`); **nessun dialog** | 🔴 modalità **cablata** nel template (`handler_params={"modalita_fatturazione":"DIFFERITA"}`); competenza **mai chiesta** |
| **Selezione righe** da smistare | *Pannello Smistamento*: checkbox per riga (default tutte le residue), un click "Smista" | handler `push_preventivo` smista **tutto automatico** per natura | 🔴 nessuna scelta; pannello bypassato |
| **Revisione** preventivo | disponibile su EMESSO (`crea_revisione` data-driven) | **non esposta** nel percorso pratica | 🔴 mancante |
| **Merce → ordine → commessa** | passi espliciti sull'ordine (Emetti, Push) | handler crea **solo l'ordine DRAFT**; non lo conferma né lo pusha | 🔴 merce **non arriva in commessa**; ordine resta DRAFT |
| Etichetta flusso CONFERMA | — | "Conferma e **push del preventivo a commessa**" | 🟡 fuorviante per la merce (promette commessa, produce ordine) |

### 3.1 Bug/gap concreti accertati

1. **🔴 Merce ferma all'ordine DRAFT (PRA-0000216).** L'handler `CONFERMA_VENDITA`
   per la merce esegue solo `fn_push_preventivo_a_ordine` (ordine DRAFT) e poi
   evade il preventivo. Non c'è Emetti ordine né push ordine→commessa → nessuna
   commessa. Riscontro DB: ordine 143 DRAFT, 0 commesse, preventivo 375 EVASO,
   pratica 290 CHIUSA. *(giornale: `DOMINIO_ORDINE_CREATO` + `DOMINIO_PREVENTIVO_EVASO`,
   nessun `DOMINIO_COMMESSA_CREATA`.)*
2. **🔴 Competenza DIFFERITA mai popolata.** [push_preventivo_handler.py:205-214]
   pretende `meta["competenza_fatturazione"]`, ma il FE pratica non la chiede da
   nessuna parte. Sul caso merce-only il ramo commessa non scatta e non emerge;
   con **righe servizio** in una pratica DIFFERITA la CONFERMA fallirebbe con
   `E_VENDITA_COMPETENZA_RICHIESTA`.
3. **🔴 Revisione non disponibile** nel percorso pratica (lo stesso
   `PreventiviDrawer` non espone `crea_revisione` quando aperto da pratica).
4. **🟡 Descrizione flusso CONFERMA fuorviante** per la merce.

Causa comune: **la pratica reimplementa il workflow in un handler che scavalca le
scelte operatore**, invece di guidare l'operatore alle azioni standalone.

---

## 4. Direzione proposta (uniformità + merce esplicita)

**La pratica orchestra la sequenza, ma ogni passo riusa l'azione/UI standalone.**
Niente più handler monolitico che decide al posto dell'operatore.

| Flusso pratica | Cosa fa (= identico allo standalone) |
|---|---|
| PREVENTIVAZIONE | apre `PreventiviDrawer` (già così) **+ revisione disponibile** come nello standalone |
| APPROVAZIONE_CLIENTE | accettazione con lo **stesso dialog** modalità fatturazione + competenza → salvati sul preventivo (elimina `handler_params` cablati e il gap competenza) |
| SMISTAMENTO | apre lo **stesso Pannello Smistamento** (selezione righe). Merce→ordine, servizi→commessa, selettivi |
| CONFERMA_ORDINE → INVIO_COMMESSA (per la merce) | passi espliciti sull'ordine (Emetti + Push a commessa), come nel programma ordini |

**Scorciatoia uniforme** (richiesta di Tid: saltare la selezione quando non
serve): si implementa **nel Pannello Smistamento standalone** (es. quando tutte
le righe residue hanno un'unica natura, proporre "Smista tutto" senza obbligare
la selezione manuale). Così vale ovunque, pratica inclusa — non una deroga
interna alla pratica.

Opzione scartata (A — "pratica nasconde l'ordine e genera la commessa"):
auto-confermerebbe un documento commerciale reale (l'ordine, con PDF/numero) che
l'operatore non vede mai → perdita di un atto commerciale e divergenza dal
modello. Si preferisce **B (ordine esplicito)**, coerente col flusso standalone.

---

## 5. Decisioni prese (Tid, 2026-06-29)

1. **Smistamento**: la pratica apre lo **stesso Pannello Smistamento** dello
   standalone; in più si aggiunge nel **programma base** una scorciatoia
   **"Smista tutto"** quando le righe residue hanno **un'unica destinazione**
   (es. tutte merce). La comodità vale ovunque, non solo in pratica.
2. **Merce in commessa**: si aggiungono **flussi espliciti di conferma ordine**
   (Emetti ordine + Push a commessa). La merce raggiunge la commessa passando
   per l'ordine, visibile (no auto-nascondi).
3. **Accettazione**: modalità fatturazione + competenza si scelgono nel **dialog
   di accettazione** (come standalone) e si salvano sul **preventivo**; non più
   cablate nel template pratica né attese da `meta`.
4. **Revisione**: **resta** disponibile nella pratica (uniforme); si gestisce
   l'aggancio `pratiche_sorgenti` ROOT → **rev attiva**. La "nuova pratica" resta
   solo per l'abbandono/restart, non per il giro di trattativa.

---

## 6. Principio di layering (correzione del team DB, recepita)

`pratiche` è **Anello 2 (motore generico)**: sa di flussi/esiti/prerequisiti,
**non** sa cosa sia un preventivo, un ordine o la "merce". `vendite` (Anello 3)
**usa** `pratiche`, mai il contrario. Due punti del piano iniziale, se messi nel DB
di `pratiche`, avrebbero forzato `pratiche` a leggere `vendite` → **inversione
vietata**. Vanno quindi spostati nel layer `vendite`/BE:

- **"50/60 solo se c'è ordine merce"** → NON è prerequisito DB (significherebbe
  leggere `vendite.preventivi_righe`): è **istanziazione condizionale** fatta
  dall'handler SMISTAMENTO (vendite), che crea i flussi 50/60 **solo** se ha
  prodotto un ordine merce. Regge perché i flussi nascono **on-demand**
  (`crea_flusso` per singolo template, nessun bulk alla nascita pratica).
- **"following rev attiva"** → la risoluzione `numero → rev attiva` la fa
  `vendite` (proprietario di `vw_preventivi.is_attiva`), non `pratiche`.

## 7. Stato implementazione

### 7.1 DB — ✅ APPLICATO (2026-06-30, commit `a7824db27`)

Riferimenti: [brief-db-pratica-preventivi-tipo-unico-flussi.md](brief-db-pratica-preventivi-tipo-unico-flussi.md)
+ [brief-db-deprecabilita-catalogo-vs-istanze.md](brief-db-deprecabilita-catalogo-vs-istanze.md).

- **Tipo unico `PREVENTIVI` (id 9004)** con catalogo 6 flussi (id 9009-9014):
  RICHIESTA_CLIENTE / PREVENTIVAZIONE (azione APRI_PREVENTIVO) / APPROVAZIONE_CLIENTE
  (event-handler `vendita.accetta_preventivo`) / SMISTAMENTO / CONFERMA_ORDINE
  (`obbligatorio=f`) / INVIO_COMMESSA (`obbligatorio=f`). `handler_id` **vuoto** su
  tutti (l'handler monolitico è ritirato).
- **Ritiro 9002/9003 NON via `attivo=false`** (bloccato dal guard
  `prevent_deactivate_if_children`, corretto) ma via **nuova colonna
  `obsoleto_dal`** su `tipi_prestazione`/`template_flussi`. `attivo` resta true
  (storia intatta); 9002/9003 hanno `obsoleto_dal=2026-06-30`. Pattern riusabile
  cross-dominio ([reference_deprecabilita_catalogo_obsoleto_dal]).
- **Following-rev**: convenzione in `pratiche_sorgenti.meta`
  (`ref_stable_key`=numero, `follow_active`), `sorgente_uid` resta l'uid
  entry-point. Nessuna nuova struttura, nessun trigger; risoluzione a read-time in
  vendite. JSONB finché non emerge il 2° consumatore.

🟡 **Punto da confermare col DB**: i prerequisiti sono `50 ← 40` **e** `60 ← 40`
(entrambi da SMISTAMENTO). Logicamente INVIO_COMMESSA(60) richiede l'ordine
CONFERMATO, output di CONFERMA_ORDINE(50) → atteso **`60 ← 50`**. Mitigato dalla
creazione on-demand BE, ma da raddrizzare per pulizia di modello.

### 7.2 Filtro `obsoleto_dal` — ✅ DB FATTO (2026-06-30, commit `2f8d4f092`)

Implementato come da [brief-db-obsoleto-dal-filtro-lookup-e-guard.md](brief-db-obsoleto-dal-filtro-lookup-e-guard.md)
(`20260630-03/04/05`, pgTAP verde):

- **Selezione** (`dbops.fn_get_lookup_codici`): nuovo 7° parametro
  **`p_includi_obsoleti boolean DEFAULT true`**. Introspezione `obsoleto_dal`
  opzionale (come `attivo`); predicato `(obsoleto_dal IS NULL OR obsoleto_dal > CURRENT_DATE)`
  applicato **solo se il chiamante passa `false`**.
  ⚠️ **Differenza chiave dal piano**: il default è **`true` = mostra tutto**
  (niente regressione silenziosa sui contesti storico/filtro). Quindi **NON è
  vero "BE/FE niente"**: il BE **deve passare `includi_obsoleti=false`** nei
  lookup di **selezione-per-il-nuovo** (es. tipo per nuova pratica), altrimenti i
  tipi obsoleti continuano a comparire. La chiamata posizionale a 6 arg resta
  valida (retro-compat).
- **Guard** (difesa in profondità): trgfn generica
  `dbops.trgfn_child_requires_non_obsolete_parent` + 2 trigger su
  `pratiche.pratiche` (`tipo_prestazione_id`) e `pratiche.flussi`
  (`template_flusso_id`) → creare una nuova istanza su catalogo obsoleto fallisce
  con **`E_CATALOGO_OBSOLETO_NUOVA_ISTANZA`** (id 500). Le istanze storiche e gli
  avanzamenti di lifecycle non sono toccati.
- **Whitelist** `_REL_CONSENTITE`: già include `pratiche.tipi_prestazione` e
  `pratiche.template_flussi` ([dbops_repository.py:107-108]) → ok, nessun lavoro.

### 7.3 BE/FE — DA FARE (dopo i prerequisiti DB)

| # | Layer | Cosa |
|---|---|---|
| B1 | BE vendite | handler **SMISTAMENTO**: split righe + crea on-demand 50/60 **solo se ordine merce** |
| B2 | BE vendite | **push a commessa** ricollocato su **INVIO_COMMESSA** (modalità presa dal **preventivo**, non da `handler_params`) |
| B3 | BE vendite | **CONFERMA_ORDINE**: Emetti ordine (`DRAFT→CONFERMATO`) agganciato al flusso |
| B4 | BE vendite | accettazione (flusso 30) riusa il **service accettazione standalone** → persiste modalità+competenza sul preventivo (chiude bug §3.1.2) |
| B5 | BE vendite | following-rev: popola `meta` (`ref_stable_key`/`follow_active`) all'aggancio + risolutore `numero→rev attiva` |
| B6 | BE core | passare **`includi_obsoleti=false`** nei lookup di **selezione-per-il-nuovo** del tipo pratica (e in generale dei cataloghi con `obsoleto_dal`) — il default DB è `true` (mostra tutto) |
| B7 | BE/FE | mappare il codice errore **`E_CATALOGO_OBSOLETO_NUOVA_ISTANZA`** (id 500) nel registry errori (messaggio parlante) |
| B8 | DB seed (igienico, opz.) | ritirare la riga smoke-test `regole_generazione` 9001 → tipo obsoleto (altrimenti uno smoke futuro inciampa nel guard) |
| F1 | FE | **Pannello Smistamento**: pulsante **"Smista tutto"** quando destinazione unica (riuso pratica+standalone) |
| F2 | FE | pratica: flussi 40/50/60 aprono le **stesse** UI standalone; drawer da pratica **espone revisione** |
| F3 | FE | dialog accettazione nel flusso 30; chiavi azioni UI (SMISTAMENTO/CONFERMA_ORDINE/INVIO_COMMESSA) nel registry; etichette flussi |

Ritiro dell'handler monolitico `vendita.push_preventivo` come parte di B1-B3.
**✅ CHIUSO (2026-07-02) — BE + DB**: BE ha rimosso classe `PushPreventivoHandler` +
registrazione + test (`check` verde, 63 test verdi); DB (pgTAP verdi) ha fatto **solo UPDATE,
zero delete**: unbind `template_flussi.handler_id`, `handler_flussi.attivo=false`,
`obsoleto_dal=2026-06-30` sui tipi (istanze esistenti vive, guard blocca solo le nuove), B8
`regole_generazione` 9001 `attivo=false`. Dettaglio:
[brief-db-ritiro-handler-monolitico-push-preventivo.md](brief-db-ritiro-handler-monolitico-push-preventivo.md).
⚠️ `vendite.fn_push_preventivo_a_ordine` (primitiva copia righe) **intatta**: la usa SMISTAMENTO.

## 8. Bug chiusi da questo intervento

- 🔴 §3.1.1 merce ferma all'ordine DRAFT → flussi 50/60 (B1-B3).
- 🔴 §3.1.2 competenza DIFFERITA mai popolata → scelta spostata al dialog di
  accettazione, persistita sul preventivo (B4).
- 🔴 §3.1.3 revisione assente → riesposta nel drawer da pratica (F2).
- 🟡 §3.1.4 etichetta fuorviante → nuove etichette/azioni flussi (F3).

## 9. Backfill `data_apertura` — non fare

Vedi [nota-be-backfill-data-apertura-pratiche.md]. Su dati test è cosmetica
(`ORDER BY … NULLS LAST` neutralizza); su dati reali la fonte corretta è la
transizione →APERTA del giornale, non `data_insert`. Rinviato.

> Stato: ✅ **CHIUSA (2026-07-02)** — DB + BE + FE fatti; ultimo residuo (ritiro handler
> monolitico `vendita.push_preventivo`) chiuso BE+DB. §9 backfill `data_apertura` rinviato
> (non-lavoro). Archiviato in `work-done/` (link entranti/uscenti aggiornati).
