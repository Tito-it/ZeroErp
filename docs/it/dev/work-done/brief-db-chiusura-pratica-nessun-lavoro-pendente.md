# Brief DB — Chiusura pratica generale: "nessun lavoro pendente" (motore configurabile) — **rev. 3**

> **Tipo**: brief DB (cosa serve + design) · **Destinatario**: team DB (`dev/db-tid`) + team BE (`dev/backend-tid`, §6 + §9)
> **Priorità**: 🔴 alta (blocca il percorso PREVENTIVI merce; regola generale del motore)
> **Data**: 2026-07-01 · **Rev. 3** (decisione presa: **niente deferral D2**, si adotta il **bivio-per-esito**; riscrittura del brief `2026-06-30`)
> **Origine**: PRA-0000225 — la pratica si **auto-chiude a SMISTAMENTO**, prima che nascano i
> flussi ordine condizionali (CONFERMA_ORDINE/INVIO_COMMESSA). Vedi
> [analisi-uniformita-pratica-preventivi.md](../work-in-progress/analisi-uniformita-pratica-preventivi.md),
> [piano-be-fe-uniformita-pratica-preventivi.md](../work-in-progress/piano-be-fe-uniformita-pratica-preventivi.md).
>
> **Nota di lettura**: i punti marcati **`⚠️ Δ`** differiscono dal brief iniziale (rev. 1).
> La sintesi completa per il team BE è in **§9**.

---

## ✅ Decisioni prese (2026-07-01)

1. **Il fix di PRA-0000225 è il BIVIO-PER-ESITO** (§3.A), non la creazione on-demand dei
   condizionali. I flussi ordine diventano **obbligatori sul ramo merce** via prerequisiti
   esito-aware; sul ramo servizi sono **ramo morto** e non bloccano. Nessuna corsa contro il
   tempo: il ramo è deciso da un **dato scritto nello stesso istante** in cui SMISTAMENTO si
   chiude.
2. **D2 (auto-chiusura deferita / constraint trigger) NON si fa** (§3.C). Il bivio rende il
   check template-based già sufficiente; il guard `pratica_terminale` resta come **rete
   fail-safe** (fallisce rumoroso, non silenzioso). Il deferral si valuterà **solo** se
   emergerà un dominio che deve creare flussi opzionali via handler e non può usare il bivio.
3. **D1 (invariante "nessun flusso aperto")** resta come **hardening generale del motore**
   (unifica chiusura manuale/auto + intercetta gli opzionali abbandonati). **Non è** ciò che
   sblocca PRA-0000225 (lo fa il bivio): è la "regola generale" che il brief si prefiggeva.

> **🔑 Scoperta chiave che dà forma al bivio (`⚠️ Δ`).** `flussi.esito` ha un CHECK di
> **motore** fisso: `chk_flussi_esito CHECK (esito IN ('POSITIVO','NEGATIVO','PARZIALE',
> 'NON_APPLICABILE'))`. La feature "esiti configurabili" (20260617) ha aggiunto solo `modalita_esito`
> / `esito_default` (il **come**), non nuovi **valori**. Per distinguere il ramo servono esiti
> di dominio (es. `MERCE_PRESENTE`/`SOLO_SERVIZI`): metterli in un CHECK di motore
> **violerebbe il layering** (semantica vendite dentro Anello 2). → la strada pulita è
> **vocabolario esiti configurabile per-template** (motore = meccanismo; valori di ramo nel
> **seed di dominio**). Vedi §3.A.3. È il vero costo DB del bivio: non è "gratis", ma è una
> capability riusabile ed è la naturale evoluzione della esito-config.

---

## 0. Perché è un tema di motore (non un caso vendite)

Le pratiche sono il motore generico per tracciare la maggior parte delle casistiche →
devono avere **rami condizionali** (step che nascono/valgono solo se servono). Con rami
condizionali *terminali*, l'auto-chiusura attuale sbaglia. Serve una **regola di chiusura
generale e data-driven**, valida per ogni tipo prestazione presente e futuro, senza logica
per-caso. (Invariato rispetto a rev. 1.)

## 1. Problema attuale (accertato sul codice vivo)

`fn_check_pratica_chiudibile` chiude quando **non resta alcun template OBBLIGATORIO
bloccante** (`fn_check_chiusura_pratica`: obbligatorio + non completato + percorribile).
Il trigger `trg_flussi_z90_autochiusura_pratica_upd` (AFTER UPDATE OF `stato_id`) la applica
a ogni completamento flusso.

Due difetti con i rami condizionali **modellati come `obbligatorio=false` + creati on-demand**:

1. **Ignora i flussi ISTANZIATI aperti non obbligatori.** Gli step condizionali (es.
   `CONFERMA_ORDINE`, `obbligatorio=false`) non bloccano → la pratica chiude anche se sono
   aperti / stanno per nascere.
2. **Timing.** Nel path BE `pratiche_service.completa_flusso` ([pratiche_service.py:527-558])
   la sequenza è: `update_stato_flusso(...COMPLETATO)` **e poi** `dispatch_handler_eventi(...)`,
   nella **stessa** `@transaction.atomic`. L'auto-chiusura è un AFTER trigger: **scatta dentro
   la UPDATE (1), prima** che l'handler di dominio (2) crei i flussi a valle on-demand → al
   momento del check quei flussi non esistono ancora.

> **⚠️ Δ 1.1 — la gravità reale è un rollback, non solo una chiusura anticipata.**
> Con la catena `post_smistamento` che crea `pratiche.flussi` a valle, appena l'handler chiama
> `crea_flusso(CONFERMA_ORDINE)` il guard `trgfn_flussi_guard_pratica_terminale` vede la pratica
> **già CHIUSA** e solleva **`PRATICHE_TERMINALE_NUOVO_FLUSSO_BLOCCATO` (490) → rollback**
> dell'intero completamento. SMISTAMENTO non riesce nemmeno a completarsi. Non è cosmetico.

> **⚠️ Δ 1.2 — la scelta di design che elimina entrambi i difetti.** Rev. 1 tentava di
> curarli con la creazione on-demand + timing deferito. Rev. 3 **cambia il modello dei
> condizionali** (bivio, §3.A): i flussi ordine non sono più "opzionali creati dopo" ma
> "obbligatori sul ramo merce". Così il check *template-based* blocca la chiusura **prima** che
> serva creare qualsiasi istanza → il difetto #1 e il difetto #2 non si presentano affatto.

Non è risolvibile con `obbligatorio=true` **secco**: il check è template-based, quindi
bloccherebbe **anche** il ramo tutto-servizi (dove quei flussi non servono mai) → non
chiuderebbe più. La chiave del bivio è rendere l'obbligatorietà **condizionata all'esito**
di SMISTAMENTO (percorribile solo sul ramo merce; ramo morto sui servizi).

## 2. Principio (regola unica, generale)

Una pratica è **chiudibile** quando **non ha più lavoro da fare**. Il motore lo determina con
**due leve data-driven**, entrambe già previste dall'architettura:

- **Percorribilità esito-aware (leva primaria per i condizionali).** Un template
  `obbligatorio=true` con prerequisito esito-aware è **bloccante solo quando è percorribile**;
  sul ramo che non lo attiva è **ramo morto → non blocca** (comportamento già implementato in
  `fn_check_chiusura_pratica`: *"il ramo morto di un bivio non blocca"*).
- **⚠️ Δ 2.1 — Invariante "nessun flusso istanziato aperto" (leva di hardening, D1).** Oltre ai
  template obbligatori bloccanti, **nessun flusso ISTANZIATO deve essere in stato non
  terminale**. Questa regola è un **invariante di transizione → CHIUSA**, enforced sul **guard
  di chiusura** (manuale e auto condividono il predicato), non solo sull'automatismo (vedi
  §3.B). Cattura i casi generali che il bivio non copre (opzionali istanziati e abbandonati).

I rami condizionali si gestiscono **da soli** via percorribilità: se il ramo non serve, i suoi
template sono ramo morto e non bloccano; se serve, sono obbligatori-percorribili e bloccano
finché non fatti. Il flag `chiude_pratica` resta come **override esplicito** (chiusura su
flusso designato).

---

## 3. Cosa serve (DB motore)

### 3.A — BIVIO-PER-ESITO — **il fix di PRA-0000225** *(sostituisce l'on-demand della rev. 1)*

> **⚠️ Δ 3.0 — cambio di modello dei condizionali.** Rev. 1: 9013/9014 `obbligatorio=false`,
> creati on-demand da un handler, con D2 (deferral) + D3 (chaining) a tenere in piedi timing e
> comparsa. Rev. 3: 9013/9014 **`obbligatorio=true`** con prerequisito **esito-aware** che li
> rende percorribili **solo sul ramo merce**. Niente D2, niente chaining handler.

**A.1 — Flip obbligatorietà (seed).** `CONFERMA_ORDINE` (9013) e `INVIO_COMMESSA` (9014)
passano a **`obbligatorio=true`** in `template_flussi` (oggi `false`).

**A.2 — Prerequisiti esito-aware (seed).**

- `9013 ← SMISTAMENTO` con `esito_richiesto = MERCE_PRESENTE` (oggi `9013←9012 POSITIVO`). Nota:
  **`POSITIVO` esce dal vocabolario di SMISTAMENTO** → grep di sicurezza su chi lo attende (a
  oggi solo il binding `post_smistamento`, ripuntato — R3/§10).
- `9014 ← CONFERMA_ORDINE` con `esito_richiesto = POSITIVO` (già a posto: `60←50` applicato da
  `20260630-06`). ⚠️ vedi §4 sulla fragilità `runAlways` di quel fix.

Effetto: sul ramo merce entrambi sono percorribili → bloccano la chiusura (anche **senza**
istanza, perché il check è template-based) finché non completati; sul ramo servizi il prereq
esito non matcha → **ramo morto → non bloccano** → la pratica chiude subito.

**A.3 — ⚠️ Δ Vocabolario esiti configurabile per-template (motore) + valori di ramo nel seed
di dominio.** È il **prerequisito-motore** del bivio e il punto di layering (vedi box in cima):

- **Motore**: l'insieme degli esiti ammessi diventa **configurabile per template** (il valore
  ammesso non è più solo il CHECK globale a 4 valori). Meccanismo: spostare la validazione da
  `chk_flussi_esito` (globale, motore) a una **config per-template** (tabella/allow-list o
  JSONB su `template_flussi`, enforced in `trgfn_flussi_guard_esito_completato`). Naturale
  estensione della esito-config `20260617-*`.
- **Dominio (seed vendite)**: SMISTAMENTO configura i propri esiti di ramo (es.
  `MERCE_PRESENTE` / `SOLO_SERVIZI`). Il motore **non** conosce "merce": vede solo una stringa
  d'esito che il dominio ha dichiarato ammessa per quel template → **layering rispettato**
  (Anello 2 = meccanismo; Anello 3 = valori).

> Se non si vuole introdurre il vocabolario per-template ora, l'unica alternativa "senza
> motore" sarebbe **abusare** un valore generico esistente (es. `PARZIALE` = servizi) → ribasso
> semantico e fragile: **scartato**. Il bivio pulito richiede A.3.

**A.4 — Niente creazione on-demand / niente chaining handler (`⚠️ Δ` — cade il vecchio D3).**
Con 9013/9014 obbligatori-su-ramo, la loro **comparsa** nella roadmap è guidata dai prerequisiti
(`get_percorso` li mostra "percorribili, non istanziati" quando il ramo è attivo). Non serve un
handler che li crei, né il binding-di-chaining su CONFERMA_ORDINE→INVIO_COMMESSA. L'operatore li
avvia dalla roadmap; le **azioni di dominio** (Emetti ordine, push a commessa) restano handler
di completamento su 9013/9014 (come `accetta_preventivo` su APPROVAZIONE_CLIENTE).

### 3.B — D1 — Invariante "nessun flusso aperto" *(hardening generale del motore)*

> **⚠️ Δ 3.1 — scope onesto.** D1 **non** è necessario per sbloccare PRA-0000225 (lo fa il
> bivio: i condizionali sono obbligatori-su-ramo, quindi il guard template-based già li vede).
> D1 è la **regola generale** promessa in §0: unifica chiusura manuale/auto e intercetta i
> flussi **opzionali** (in qualsiasi tipo) istanziati e lasciati aperti. Vale la pena farlo
> insieme al bivio perché è la parte "motore configurabile" del brief, ma è un layer distinto.

**D1.a — Un solo predicato di chiudibilità, due chiamanti.** La condizione "**nessun flusso
istanziato in stato non terminale**" va enforced **sia** dalla chiusura **manuale**
(`trgfn_pratiche_guard_chiusura_flussi` / `fn_check_chiusura_pratica`, errore 485) **sia**
dall'auto-chiusura (`fn_check_pratica_chiudibile`). Preferibile un helper unico riusato dai due
path, così la definizione non diverge (rev. 1 toccava solo l'auto-chiusura → la chiusura
manuale sarebbe rimasta più permissiva).

**D1.b — Stati terminali DERIVATI dai dati, non hardcodati.** "Terminale" = *stato senza
transizioni di stato in uscita attive* in `config.transizioni_stati_flussi_pratiche` — stessa
derivazione auto-mantenuta di `trgfn_flussi_guard_pratica_terminale`. Sul grafo attuale dà
`{COMPLETATO, ANNULLATO}`, e correttamente tratta **ERRORE come NON terminale** (blocca).
Niente lista `codice_interno` cablata.

| Stato | Uscite attive | Terminale? |
|---|---|---|
| DA_ESEGUIRE | →IN_CORSO, →ANNULLATO, →SOSPESO | no (blocca) |
| IN_CORSO | →COMPLETATO, →SOSPESO, →ERRORE | no (blocca) |
| SOSPESO | →IN_CORSO, →DA_ESEGUIRE | no (blocca) |
| ERRORE | →IN_CORSO, →ANNULLATO | no (blocca) |
| **COMPLETATO** | — | **sì** |
| **ANNULLATO** | — | **sì** |

**D1.c — Escludere per ISTANZA il flusso che sta completando.** `fn_check_pratica_chiudibile`
è chiamata anche da `trgfn_flussi_guard_chiusura_prematura` in **BEFORE**: lì il flusso che
completa è ancora `IN_CORSO` (non terminale) → la clausola-istanza **conterebbe se stesso** →
falso blocco. Serve un nuovo **`p_escludi_flusso_id`** (per-istanza) applicato alla
clausola-istanza; il guard passa `NEW.id`, l'auto-chiusura passa `NEW.id` (innocuo). Il
`p_escludi_template_id` esistente resta per la clausola obbligatori-bloccanti.

### 3.C — D2 (auto-chiusura deferita) — **DECISIONE: non si fa**

> **⚠️ Δ 3.2 — rev. 1 proponeva il constraint trigger `DEFERRABLE INITIALLY DEFERRED`. Non lo
> facciamo.** Motivazioni:
>
> - **Il bivio (§3.A) elimina il problema di timing alla radice**: il ramo è deciso da un dato
>   (l'esito) scritto nella **stessa UPDATE** che completa SMISTAMENTO, quindi il check
>   template-based blocca **prima** che serva creare istanze. Nessuna corsa → niente da
>   deferire.
> - **Esiste già una rete fail-safe**: il guard `pratica_terminale` (490). Se un domani
>   qualcuno creasse un flusso a valle su una pratica appena chiusa, **non si perde nulla in
>   silenzio** — parte l'errore 490 → rollback, cioè un fallimento **visibile e precoce** in
>   sviluppo/test.
> - **D2 "di sicurezza" sarebbe peggio del non averlo**: deferendo la chiusura,
>   *maschererebbe* proprio quel fallimento fail-safe, togliendo il segnale che dice "modella
>   questo come bivio". Senza D2 il sistema **fallisce sicuro** (rumoroso), non **pericoloso**
>   (silenzioso, in produzione, con lavoro orfano).
> - **È la parte più rischiosa del disegno** (errori al COMMIT, perdita del filtro
>   `UPDATE OF`, dipendenza dall'assunzione "stessa transazione"): introdurla senza un caso
>   concreto che la richieda è complessità prematura.
>
> **Tripwire da rispettare (regola di motore):** *un condizionale che nasce dopo un
> completamento va modellato come **bivio** (obbligatorio-su-ramo via esito), non creato da un
> handler dopo una chiusura possibile. Se qualcuno lo fa senza bivio, fallisce con 490: quello
> è il segnale di usare il bivio. Il deferral (D2) si introduce **solo** se emergerà un dominio
> che deve davvero creare flussi opzionali via handler e non può usare il bivio — a quel punto,
> con quel caso concreto in mano.*

---

## 4. Interdipendenze, vincoli e dipendenze

- **⚠️ Δ 4.1 — Dipendenza-motore del bivio: vocabolario esiti per-template (§3.A.3).** Il bivio
  pulito **non parte** finché il motore non consente esiti configurabili per template. Sequenza:
  (1) applicare la esito-config `20260617-*` (oggi *scritta, non applicata*); (2) estenderla al
  **vocabolario** per-template; (3) poi il seed di ramo su SMISTAMENTO.
- **⚠️ Δ 4.2 — Fragilità del fix `60←50`.** `20260630-06` ha `runAlways:false` in conflitto col
  proprio commento (che argomenta `runAlways:true`, perché il seed sorgente `20260608-09` è
  `runOnChange:true` e un re-seed riporterebbe `60←40`). Rischio: `9014` torna a dipendere da
  SMISTAMENTO invece che da CONFERMA_ORDINE. **Riallineare `runAlways`/commento** (o assorbire
  il fix nel seed) prima di appoggiarci il bivio.
- **⚠️ Δ 4.3 — Re-binding `post_smistamento` (per-ramo).** Oggi il binding è su SMISTAMENTO
  **COMPLETATO/POSITIVO**. Si ripunta a **`esito_richiesto=MERCE_PRESENTE`** (R3, §10): l'handler
  diventa **merce-only** (retro-aggancio dell'ordine come `pratiche_sorgenti`) e non fa più
  `crea_flusso` a valle (§3.A.4). Lo **split e l'aggancio di entrambi i rami** stanno sui
  **percorsi standalone** (`push_a_ordine`/`push_a_commessa`); l'aggancio **commessa-servizi** va
  spostato su `push_a_commessa` **pratica-aware** (BE) **prima/insieme** al ritiro del monolite,
  altrimenti il per-ramo lo lascia scoperto.
- **⚠️ Δ 4.4 — D1 richiede la via d'uscita `annulla flusso`** (per gli **opzionali** di altri
  tipi, non per PREVENTIVI): un opzionale istanziato e lasciato aperto blocca la chiusura finché
  non portato ad ANNULLATO. Il grafo lo prevede (`DA_ESEGUIRE→ANNULLATO`), ma l'azione va esposta
  in BE/FE.
- **Naming binding**: se in futuro si bindano handler su CONFERMA_ORDINE/INVIO_COMMESSA per le
  azioni di dominio, evitare di riusare il nome `post_smistamento` (fuorviante) → nome neutro.

---

## 5. Criteri di accettazione (scenari PREVENTIVI 9004)

- **Merce**: SMISTAMENTO chiude con esito ramo-merce → 9013/9014 percorribili+obbligatori → la
  pratica **resta APERTA** (anche prima di istanziarli). Completati in ordine (9013 POSITIVO →
  9014 percorribile → 9014 completato), **si chiude**.
- **Tutto-servizi**: SMISTAMENTO chiude con esito ramo-servizi → 9013/9014 **ramo morto** → non
  bloccano, nessun flusso a valle → la pratica **si chiude** subito.
- **Misto**: c'è merce → esito ramo-merce → 9013/9014 dovuti; i servizi vanno a commessa diretta
  (nessun flusso). Chiude solo a INVIO_COMMESSA completato.
- **⚠️ Δ 5.1 — coerenza manuale/auto (D1)**: chiudere **a mano** una pratica con un flusso
  istanziato aperto **fallisce** con lo stesso predicato dell'auto-chiusura.
- **⚠️ Δ 5.2 — via d'uscita (D1)**: annullando (→ANNULLATO) un flusso opzionale aperto, la
  pratica torna chiudibile (auto e manuale).
- **⚠️ Δ 5.3 — fail-safe (niente D2)**: se un flusso a valle venisse creato su pratica chiusa,
  l'errore 490 deve emergere (rollback visibile), non essere mascherato.
- Nessuna regressione sugli altri tipi (→ §8.1).
- pgTAP: merce / servizi / misto + i casi D1 e fail-safe (§8).

## 6. Lato BE (fuori scope DB — lo facciamo noi) — **⚠️ Δ aggiornato**

- **SMISTAMENTO esito = ramo, calcolato dal dominio (non scelto dall'operatore).** L'esito
  (`MERCE_PRESENTE`/`SOLO_SERVIZI`) è **derivato dallo split** (ci sono righe merce?), non
  digitato. Va passato a `completa_flusso(esito=...)` così è scritto **nella stessa UPDATE** che
  completa il flusso (il check template-based lo legge subito). *(Se SMISTAMENTO diventa
  esito-AUTOMATICO/CONTESTUALE, allineare `modalita_esito`.)*
- **Split e aggancio sui percorsi standalone; `post_smistamento` merce-only.** Lo split
  (merce→ordine DRAFT, servizi→commessa) e l'aggancio `pratiche_sorgenti` di **entrambi** i rami
  avvengono nel **pannello smistamento** (`push_a_ordine`/`push_a_commessa`), non nell'handler.
  `post_smistamento` (bindato su `MERCE_PRESENTE`, §4.3) fa solo il **retro-aggancio dell'ordine**
  come `pratiche_sorgenti` COLLEGATO; **non** fa `crea_flusso` a valle (9013/9014 compaiono via
  roadmap/prerequisiti). **BE**: spostare l'aggancio **commessa-servizi** dal monolite a
  `push_a_commessa` **pratica-aware**, prima/insieme al ritiro del monolite.
- **Azioni di dominio su 9013/9014**: Emetti ordine (`DRAFT→CONFERMATO`) su CONFERMA_ORDINE;
  push ordine→commessa su INVIO_COMMESSA (modalità presa dal preventivo). Come handler di
  completamento o azioni standalone aperte dal flusso (uniformità col programma base).
- **`annulla flusso`** (D1, §4.4): esporre la transizione →ANNULLATO per liberare la chiusura
  nei tipi con flussi opzionali.
- **Ritiro handler monolitico `vendita.push_preventivo`**: confermato, non più dispatchato.
- Nessuna logica di chiusura lato BE: la chiusura resta del motore (data-driven).

## 7. Nota di design (configurabilità)

La regola di chiusura resta **guidata dai dati del grafo** (`template_flussi`: obbligatorio +
prerequisiti esito-aware). Rev. 3 fa un passo in più verso il "motore configurabile":

- il **bivio-per-esito** diventa una **capability riusabile** — qualunque dominio futuro con
  divergenze condizionali si modella dichiarando gli **esiti di ramo** (dato) + prerequisiti
  esito-aware, **senza codice motore né inversioni di layering**;
- l'**invariante D1** dà una definizione unica di "chiudibile" per chiusura manuale e auto.

## 8. Test

- **⚠️ Δ 8.1 — riformulare "nessuna regressione".** Oggi una pratica può auto-chiudersi con un
  flusso *opzionale* istanziato aperto; con D1 **non più**. Cambiamento semantico corretto ma
  reale → verificarlo contro il seed (i tipi 9002/9003/9004 non hanno opzionali istanziabili, ma
  va detto). Per i condizionali PREVENTIVI la copertura viene dal **bivio** (obbligatori-su-ramo),
  non da D1.
- **⚠️ Δ 8.2 — aggiornare i test esistenti.** `db/pgtap/pratiche/test-autochiusura-pratica.sql`
  copre il **model B (flusso di chiusura)**: gli assert cambiano con D1.c (esclusione
  per-istanza).
- Nuovi pgTAP: **bivio** (esito merce → 9013/9014 bloccano; esito servizi → ramo morto → chiude);
  catena 9013→9014; D1 (flusso opzionale aperto blocca, annullato sblocca; chiusura manuale con
  flusso aperto → throws); fail-safe 490 (creazione flusso su pratica chiusa → errore, non
  silenzio).

---

## 9. Sintesi delle differenze rispetto al brief iniziale (per il team BE)

> Autoconsistente: cosa cambia dalla rev. 1, cosa impatta il BE, cosa resta. Passala al BE.

### 9.1 Le due decisioni che cambiano il disegno

| Tema | Rev. 1 (brief iniziale) | Rev. 3 (deciso) | Perché |
|---|---|---|---|
| **Fix condizionali** | 9013/9014 `obbligatorio=false`, **creati on-demand** da handler | **Bivio-per-esito**: 9013/9014 **`obbligatorio=true`** + prereq **esito-aware** (percorribili solo sul ramo merce) | Elimina il timing alla radice; il ramo è un dato scritto al completamento di SMISTAMENTO |
| **D2 (deferral)** | Constraint trigger `DEFERRABLE` proposto | **NON si fa** | Il bivio lo rende inutile; il guard 490 è già fail-safe; D2 mascherebbe quel segnale |
| **D3 (chaining handler)** | Bind handler su CONFERMA_ORDINE per **creare** INVIO_COMMESSA | **Cade**: la comparsa dei passi è guidata da roadmap/prerequisiti | Con obbligatori-su-ramo non serve creare on-demand |
| **D1 (no flusso aperto)** | Solo su `fn_check_pratica_chiudibile` (auto) | **Invariante condiviso** (manuale+auto), terminali **data-driven**, nuovo `p_escludi_flusso_id`; **hardening generale, non il fix di PRA-0000225** | Coerenza chiusura; una sola definizione di "chiudibile" |

### 9.2 La dipendenza-motore nuova (impatta la sequenza)

| # | Punto | Cosa deve sapere il BE |
|---|---|---|
| Δ3.A.3 | **Esito ora è un vocabolario di motore fisso** (`chk_flussi_esito`: 4 valori) | Il bivio richiede **esiti configurabili per-template** (valori di ramo nel **seed di dominio**, non nel CHECK). Dipende dall'aver **applicato** la esito-config `20260617-*` (oggi scritta-non-applicata) ed **esteso** al vocabolario per-template |
| Δ4.3 | Re-binding `post_smistamento` (per-ramo) | Ripuntato a **`esito_richiesto=MERCE_PRESENTE`**. Handler **merce-only** (retro-aggancio ordine), niente `crea_flusso`. Split+aggancio di entrambi i rami sui percorsi standalone; **aggancio commessa-servizi → `push_a_commessa` pratica-aware** (BE), prima/insieme al ritiro del monolite |
| Δ4.2 | Fix `60←50` fragile (`runAlways:false` vs commento) | Un re-seed di `20260608-09` può riportare `60←40` → verificare/riallineare prima del bivio |

### 9.3 Cosa cambia concretamente per BE/FE (aggiornato)

- **SMISTAMENTO scrive un esito di ramo calcolato** (`MERCE_PRESENTE`/`SOLO_SERVIZI`), derivato
  dallo split, passato a `completa_flusso(esito=...)`. **Non** è più una scelta operatore
  (POSITIVO).
- **Niente creazione on-demand di 9013/9014** (cade il vecchio B1): compaiono da
  roadmap/prerequisiti. `post_smistamento` si riduce al **retro-aggancio ordine (merce-only)**;
  lo split e l'aggancio commessa-servizi stanno sui percorsi standalone (`push_a_commessa`
  **pratica-aware**).
- **Azioni di dominio** su 9013 (Emetti ordine) e 9014 (push commessa) restano — come
  handler di completamento o azioni standalone del flusso.
- **`annulla flusso`** va esposto (D1) per i tipi con flussi opzionali.
- **Nessun `E_VENDITA_COMPETENZA_RICHIESTA`/modalità cablata**: modalità+competenza sul
  preventivo (già chiuso in Fase 1).

### 9.4 Cosa NON cambia rispetto a rev. 1

- La **diagnosi** (auto-chiusura a SMISTAMENTO prima dei condizionali).
- Il rifiuto di `obbligatorio=true` **secco** (romperebbe il ramo servizi) — il bivio lo rende
  obbligatorio **solo sul ramo**.
- Il layering Anello 2/3 (`pratiche` non legge `vendite`): rispettato mettendo i **valori** di
  ramo nel seed di dominio, non nel motore.
- I criteri merce / tutto-servizi (arricchiti col caso misto).

### 9.5 Sequenza consigliata (per non incastrarsi sulle dipendenze)

1. **Esito-config**: applicare `20260617-*` + estendere al **vocabolario per-template** (motore).
2. **Seed bivio**: esiti di ramo su SMISTAMENTO; `9013 obbligatorio=true` + prereq esito-merce;
   `9014 obbligatorio=true` (prereq `60←50` già ok, ma consolidare §4.2); re-binding
   `post_smistamento` (§4.3).
3. **D1** (hardening generale): invariante condiviso + terminali data-driven + `p_escludi_flusso_id`.
4. **BE**: SMISTAMENTO calcola l'esito; handler ridotto; azioni 9013/9014; `annulla flusso`.
5. **Test**: bivio + D1 + fail-safe + regressioni.

---

## 10. Q&A DB↔BE — decisioni di dettaglio (2026-07-01)

Risposte DB alle domande BE, recepite nel brief.

**R1 — Esiti di ramo.** `MERCE_PRESENTE` / `SOLO_SERVIZI`, dichiarati **solo su SMISTAMENTO
(9012)** nel seed vendite (vocabolario per-template, §3.A.3). `MERCE_PRESENTE` copre
**merce + misto** (bastano due valori). **`POSITIVO` esce** dal vocabolario di SMISTAMENTO →
grep di sicurezza su chi lo attende (a oggi solo il binding, ripuntato in R3). Un esito
negativo/annullo su SMISTAMENTO si aggiunge solo se il flusso può davvero fallire (oggi no).

**R2 — `modalita_esito` di SMISTAMENTO = `MANUALE`.** Non `AUTOMATICO`/`CONTESTUALE`: il guard
`trgfn_template_flussi_guard_modalita_esito` (Inv1) pretende un `esito_default` **fisso** per
ogni modalità ≠ MANUALE, ma qui l'esito **varia** (merce/servizi). `MANUALE` a livello motore
significa *"esito fornito al completamento, nessun default"*: il **BE calcola** l'esito di ramo
dallo split e lo passa a `completa_flusso(esito=...)`; il **FE** per SMISTAMENTO **sopprime il
picker esiti** (la modalità DB non impone alcun picker: lo decide il FE).

**R3 — Binding `post_smistamento` = `esito_richiesto=MERCE_PRESENTE`** (per-ramo). Nota di
coerenza BE recepita: lo **split e l'aggancio di entrambi i rami** stanno sui **percorsi
standalone** (pannello smistamento: `push_a_ordine`/`push_a_commessa`); `post_smistamento` è
**merce-only** (retro-aggancio dell'ordine come `pratiche_sorgenti`).

- **BE**: spostare l'aggancio **commessa-servizi** dal monolite a `push_a_commessa`
  **pratica-aware**, **prima/insieme** al ritiro del monolite (senza, il per-ramo lascia scoperto
  l'aggancio servizi). Rientra nella riduzione dell'handler già prevista: "rimuovi step 4" →
  "rimuovi step 4 **e** sposta l'aggancio commessa nel push servizi".
- **DB**: nessun blocco. Unico check: che `trgfn_pratiche_sorgenti_guard_coerenza_flusso`
  accetti il link **commessa-servizi** creato dal percorso smistamento (ramo servizi, senza i
  flussi 9013/9014). Se il guard pretende un flusso coerente per la sorgente, adeguarlo lato
  guard (unico punto DB toccato, non un blocco).

---

## 11. Stato realizzazione (2026-07-01) — **DB ✅ APPLICATO + TESTATO**

Lato DB completato in 4 increment, **applicati** sul DB e **pgTAP verde**. Resta il BE (§9.3 + §10).

### 11.1 Increment 1 — Vocabolario esiti data-driven (schema)

- `00_schema/config/20260701-01-create-esiti-flussi-pratiche` — crea `config.esiti_flussi_pratiche`
  (gemella di `stati_flussi_pratiche`) + seed dei 4 esiti strutturali.
- `00_schema/pratiche/20260701-02-alter-esito-checks-to-fk` — sostituisce 3 CHECK enum con FK
  verso `esiti_flussi_pratiche(codice_interno)`.

> **⚠️ Δ vs piano (§3.A.3):** il vocabolario NON è stato realizzato estendendo la esito-config
> `20260617-*` "per-template", ma come **tabella-vocabolario globale dedicata**
> (`config.esiti_flussi_pratiche`, FK via `codice_interno`). È **layering-clean** lo stesso (i
> valori di ramo vivono nel **seed di dominio**, non nel motore) ed è più semplice/consistente
> con le altre `config.*`. Lo **scoping per-template** (quali esiti un template può produrre) è
> **rinviato**: non serve alla correttezza (i prerequisiti matchano il valore; l'operatore/BE
> passa l'esito giusto). Ne consegue che la "dipendenza esito-config applicata" di §9.2/§4.1
> **decade**: il bivio non dipende più dalla esito-config.

### 11.2 Increment 2 — Bivio PREVENTIVI (seed)

- `00_schema/pratiche/20260701-03-alter-tfhe-esito-check-to-fk` — **4° CHECK** (`chk_tfhe_esito`
  sul binding) → FK. *(Era mancante nel piano "3 CHECK": censito e aggiunto. `chk_regole_gen_esito`
  resta fuori: vocabolario diverso.)*
- `80_data/.../20260701-04-upsert-config-esiti-flussi-pratiche` (+ CSV `esiti_flussi_pratiche.csv`)
  — seed vocabolario completo (base + `MERCE_PRESENTE`/`SOLO_SERVIZI`), stile loadUpdateData.
- `80_data/.../20260701-05-configura-bivio-preventivi` (runAlways) — 9013/9014 `obbligatorio=true`;
  prereq `9013←SMISTAMENTO` esito→`MERCE_PRESENTE`; consolida `60←50` durevole (supera la
  fragilità `runAlways:false` di 20260630-06); re-binding `post_smistamento`→`MERCE_PRESENTE`.

### 11.3 Increment 3 — D1 hardening (20_code)

- `20260701-06-create-fn-pratica-flussi-aperti` — helper "flussi aperti" (terminali **data-driven**
  da `transizioni_stati_flussi_pratiche`).
- `20260701-07-update-fn-check-pratica-chiudibile-flussi-aperti` — clausola (b) + `p_escludi_flusso_id`.
- `20260701-08-update-trgfn-pratiche-guard-chiusura-flussi-aperti` — chiusura **manuale** rifiuta
  flussi aperti → **errore 501** `PRATICHE_CHIUSURA_FLUSSI_APERTI` (riga in `messaggi_errore.csv`).
- `20260701-09-…guard-chiusura-prematura-escludi-flusso` e `20260701-10-…autochiusura-escludi-flusso`
  — passano `NEW.id` (escludono sé stessi).

### 11.4 Increment 4 — pgTAP

- `db/pgtap/pratiche/test-chiusura-nessun-lavoro-pendente.sql` — **verde (11/11)**: bivio
  merce/servizi/misto, catena 9013→9014, D1 (blocco + annulla + coerenza manuale/auto), fail-safe 490.
- **Da rilanciare (non-regressione):** `db/pgtap/pratiche/test-autochiusura-pratica.sql` (modelli A/B;
  passa grazie all'esclusione `NEW.id` del 09).

### 11.5 Documentazione (manual concettuale)

Aggiornata/creata la doc `manual/` (le pagine auto-gen `funzioni/`/`tabelle/` si rigenerano dal DB):

- **nuove**: `pratiche/manual/fn_pratica_flussi_aperti.md`, `config/manual/esiti_flussi_pratiche.md`;
- **aggiornate**: `fn_check_pratica_chiudibile`, `trgfn_pratiche_guard_chiusura_flussi`,
  `trgfn_flussi_guard_chiusura_prematura`, `trgfn_flussi_autochiusura_pratica`.

### 11.6 Stato BE — **✅ FATTO** (2026-07-01, `dev/backend-tid`)

Tutto il lato BE del bivio (§9.3 + §10) è implementato e **1764 test verdi**; commit fatto.

- ✅ **`ESITI_FLUSSO_AMMESSI`** esteso (`MERCE_PRESENTE`/`SOLO_SERVIZI`), mirror fail-fast del vocabolario DB.
- ✅ **`completa_smistamento`** (`preventivi_service`) + endpoint `POST …/preventivi/{id}/completa-smistamento/`: calcola l'esito di ramo dal dominio (stesso lookup `documento_origine` dell'handler → nessun disallineamento) e completa lo step nella stessa UPDATE.
- ✅ **`post_smistamento` merce-only** (rimosso il `crea_flusso` a valle; retro-aggancio ordine + fail-safe).
- ✅ **`push_a_commessa` pratica-aware** (aggancio commessa-servizi COLLEGATO — gap R3 chiuso).
- ✅ **Azioni 9013/9014**: auto-completamento step su `ordini_service.conferma` (CONFERMA_ORDINE) e `push_a_commessa` ordine (INVIO_COMMESSA), via BB motore estratto **`pratiche_service.completa_step_pratica`** (regola del 2).
- ✅ **Errore 501** `PRATICHE_CHIUSURA_FLUSSI_APERTI` + `E_VENDITA_PREVENTIVO_NON_COLLEGATO` mappati in `error_policies.py`.
- 📄 Doc API aggiornate: `api_preventivi.md` (§14b, §13, §6c), `api_ordini.md` (conferma/push), catalogo BB (sezione Pratiche).

**Rinviato (non serve al percorso PREVENTIVI):** `annulla flusso` (transizione →ANNULLATO) — hardening D1 generale per i tipi con flussi **opzionali** (§4.4/§8.1), non per 9004.

**Residui DB (team `dev/db-tid`):** rilanciare la non-regressione `test-autochiusura-pratica.sql` (§11.4); rigenerare le doc auto-gen dbzero (funzioni + `esiti_flussi_pratiche`).

**Validazione finale:** ✅ smoke E2E **verde** (`smoke-test-pratica-preventivi-bivio.sh`,
rami MERCE + SOLO_SERVIZI) — 2026-07-01. Lo smoke ha scoperto e fatto chiudere due
gap che i test mock non vedevano: (1) BE — `_resolve_pratica_id_da_preventivo`
dipendeva dal `flusso_id` sul link ROOT (fix: risoluzione diretta
`get_pratica_id_by_preventivo_root`); (2) DB — binding `post_smistamento` su
SMISTAMENTO era `attivo=false`, riattivato (brief chiuso
[brief-db-attiva-binding-post-smistamento-bivio.md](brief-db-attiva-binding-post-smistamento-bivio.md)).
