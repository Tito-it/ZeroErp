# Brief DB — le vie d'uscita per l'operatore

> **Chi scrive:** team DB (`dev/db-tid`), 2026-08-04.
> **A chi:** Tid (decisioni di dominio, già prese) e BE/FE (la metà a video).
> **Da dove nasce:** il presidio `test-transizioni-uscita-manuale-v1.sql`, scritto
> chiudendo [brief-db-emittibilita-visibile-e-sbloccabile.md](brief-db-emittibilita-visibile-e-sbloccabile.md) §7.3.
> Quel test ha trovato **sei stati** da cui un documento non ha nessuna uscita che
> una persona possa azionare.
> **Perché è un brief e non una riga di registro:** un documento fermo senza azioni
> e senza spiegazioni non è un debito tecnico, è un operatore bloccato davanti a uno
> schermo. Verificato: un preventivo in `ACCETTATO` oggi offre **una** sola azione
> (`push_commessa`) e nient'altro — non si annulla, non torna indietro, non si
> corregge.

---

## 1. Le tre regole in gioco

Le prime due vengono dal brief precedente, la terza nasce qui.

> **R1 — da ogni stato con uscite attive deve esistere almeno un'uscita che una
> persona può azionare.** Se sono tutte automatiche, il documento dipende da un
> evento che potrebbe non arrivare mai.

<!-- markdownlint-disable-next-line MD028 -->
> **R2 — chi mostra e chi esegue leggono lo stesso criterio.** Il bottone e il guard
> devono dare lo stesso verdetto, e l'unico modo di garantirlo è che leggano la
> stessa funzione.

<!-- markdownlint-disable-next-line MD028 -->
> **R3 — quando la risposta è «non si può», deve arrivare anche il perché.** Un
> elenco di azioni vuoto è indistinguibile da un errore di caricamento. Un bottone
> spento con la motivazione è meglio di un bottone assente.

R3 è il difetto speculare a quello del brief precedente: là la lista *prometteva*
senza spiegare, qui *nega* senza spiegare. Oggi `fn_available_actions_preventivo`
risponde `can_genera_ordine: false` e basta: un booleano nudo.

## 2. Le decisioni di Tid (2026-08-04)

| Stato | Decisione |
| --- | --- |
| `preventivo ACCETTATO` | **Ripristinare l'annullamento** |
| `preventivo EMESSO` | **Ripristinare l'annullamento**, ma solo in assenza di vincoli verso ordine/commessa |
| `ordine CONFERMATO` | **Ripristinare l'annullamento**, con *tutti* i controlli che lo impediscono (evasioni, DDT…) |
| `ddt CONSEGNATO` | **No** all'annullamento — ma dire all'operatore che la strada è il **reso** |
| `ordine EVASO`, `ordine PARZIALMENTE_EVASO` | Nessuna azione: sono **ricalcoli**. Segnalare cosa succede |
| `ddt RESO` | Idem: la UI deve dire cosa sta accadendo |

Il vincolo «solo se non ci sono legami a valle» è scritto per `EMESSO` ma vale per
entrambi gli stati del preventivo: un preventivo già convertito non si annulla in
nessuno dei due. Una funzione sola, usata da entrambe le transizioni — su `EMESSO`
il vincolo sarà quasi sempre vacuo, ed è giusto così.

## 3. Le due funzioni pure (R1 + R2)

Stesso contratto delle tre sorelle già in casa (`fn_check_commessa_chiudibile`,
`_annullabile`, `_pronta_fatturazione`): `jsonb`, `[]` = lecito, altrimenti array di
`{codice, reason, reason_key, dettaglio}`. Lette **sia** dal guard di transizione
**sia** da `fn_available_actions_*`.

### 3.1 `script.fn_check_preventivo_annullabile(p_preventivo_id)`

| Motivo | Condizione | Codice |
| --- | --- | --- |
| Ordine già generato | esiste un ordine che ha questo preventivo come sorgente | `E_PREV_ORDINE_GIA_GENERATO` *(nuovo)* |
| Già inviato a fatturazione | esiste una riga in `commesse_sorgenti` per questo preventivo | `E_PREV_GIA_IN_COMMESSA` *(esiste)* |

### 3.2 `script.fn_check_ordine_annullabile(p_ordine_id)`

| Motivo | Condizione | Codice |
| --- | --- | --- |
| Merce già uscita | esiste un DDT che ha questo ordine come sorgente | `E_ORD_ANNULLA_CON_DDT` *(nuovo)* |
| Già inviato a fatturazione | esiste una riga in `commesse_sorgenti` per questo ordine | `E_ORD_ANNULLA_IN_COMMESSA` *(nuovo)* |

### 3.3 ⚠️ La chiave di collegamento è la trappola di questo lavoro

Il progetto ha **due** convenzioni per legare i documenti, e usarne una al posto
dell'altra produce join che non tornano niente **senza errore**:

| Percorso | Chiave | Perché |
| --- | --- | --- |
| Colonne dirette — `ordini.sorgente_uid`, `ddt.sorgente_uid` | **`uuid`**, sempre | la colonna è tipizzata `uuid`: si lega a `preventivi.uid` / `ordini.uid`, mai all'`id` |
| Tabella polimorfa — `commesse_sorgenti.sorgente_uid` | **`text`**, secondo `config.sorgenti.key_selector` | `PREVENTIVO` → `uid::text`; `ORDINE_VENDITA` → `id::text` |

Quindi, nella stessa funzione, il preventivo va cercato **per uid** nella catena
diretta e **per uid::text** in commessa; l'ordine va cercato **per uid** nella catena
diretta e **per id::text** in commessa. Non è una svista da sanare: è la convenzione
documentata, e questo brief la scrive perché chi implementa non la deduca al volo.

I `sorgente_tipo_id` non vanno mai messi come numero: si risolvono con una lookup su
`config.sorgenti.codice_interno`.

> ℹ️ **Da NON riusare, benché il nome inganni.** Esistono già
> `fn_preventivo_ha_residuo_ordine`, `fn_preventivo_ha_residuo_commessa`,
> `fn_ordine_ha_residuo_evasione`. Rispondono a «resta ancora qualcosa da
> convertire?», che **non** è la domanda dell'annullamento: un documento convertito a
> metà ha residuo *e* ha già un figlio a valle. Servirebbe l'opposto, e riusarle
> renderebbe annullabile ciò che è già stato lavorato in parte.

## 4. Il «segnalare» per gli stati che restano chiusi (R3)

Quattro stati restano senza uscita manuale per decisione, non per dimenticanza.
All'operatore va detto **cosa sta succedendo e cosa può fare invece**.

Sede: la colonna `meta` delle tabelle di stato (`config.stati_doc_ordini`,
`stati_doc_ddt`), oggi `{}` su tutte le righe. È dato, non codice: si cambia il testo
senza toccare una funzione, ed è la stessa scelta già fatta per i metadati UI delle
transizioni.

```jsonc
// config.stati_doc_ddt, riga CONSEGNATO
{ "nessuna_azione_key": "vendite.ddt.stato_info.consegnato_usa_reso" }
```

| Stato | Messaggio (chiave i18n, testo al FE) |
| --- | --- |
| `ddt CONSEGNATO` | «La merce è consegnata: per rientrare si registra un **reso**, non si annulla il DDT» |
| `ddt RESO` | «Questo DDT è rientrato con un reso: lo stato lo segue da solo» |
| `ordine EVASO` | «L'ordine è evaso: lo stato si ricalcola dai DDT, non si imposta a mano» |
| `ordine PARZIALMENTE_EVASO` | «Evasione in corso: lo stato si ricalcola a ogni DDT» |

Le `fn_available_actions_*` espongono la chiave quando **non c'è nessuna azione
abilitata**, così il FE ha sempre qualcosa da dire al posto della lista vuota.

## 5. Perimetro

**DB (questo cantiere):** le due funzioni pure, i tre codici errore nuovi, la
riattivazione delle tre transizioni nei CSV, l'aggancio nei due guard e nelle due
`fn_available_actions_*`, il `meta` dei quattro stati, i pgTAP.

**BE/FE (loro metà):** rendere disponibili i verbi «Annulla» su preventivo e ordine;
mostrare `reasons` sui bottoni spenti; mostrare `nessuna_azione_key` quando la lista
è vuota. Nessun testo è hardcodato lato DB: viaggiano chiavi i18n.

> ✅ **Fatta il 2026-08-04** — rendiconto in
> [brief-be-fe-vie-uscita-operatore.md](brief-be-fe-vie-uscita-operatore.md),
> riassunto qui al §8. Due delle tre voci sono già a video; la terza (`reasons`)
> è cablata e aspetta solo il campo dal DB.

### 5.1 Cosa trova il BE, in concreto

Tutto quanto segue è **già nel database** (changeSet `20260804-33/-34/-35` applicati).

**Due verbi nuovi diventano disponibili.** `fn_available_actions_preventivo` e
`fn_available_actions_ordine` ora restituiscono l'azione `annulla` (`action_key`,
`label_key`, icona, `requires_confirm`) dagli stati `EMESSO` / `ACCETTATO` del
preventivo e `CONFERMATO` dell'ordine, che prima non la offrivano. Le chiavi i18n da
tradurre sono `vendite.preventivi.azione_annulla` e `vendite.ordini.azione_annulla` —
esistevano già nel `meta`, erano solo irraggiungibili.

**Tre codici errore nuovi**, che l'API può ricevere quando l'annullamento viene
rifiutato dal database. Vanno dichiarati in `error_policies.py`, come da vostro
guardrail:

| Codice | Quando | HTTP suggerito |
| --- | --- | --- |
| `E_PREV_ORDINE_GIA_GENERATO` | il preventivo ha già generato un ordine | 409 |
| `E_ORD_ANNULLA_CON_DDT` | l'ordine ha già DDT collegati | 409 |
| `E_ORD_ANNULLA_IN_COMMESSA` | l'ordine è già stato inviato a fatturazione | 409 |

Il quarto, `E_COMMESSA_EMITTENTE_MANCANTE`, arriva dall'altro cantiere
([emittibilità](brief-db-emittibilita-visibile-e-sbloccabile.md)).

**Chiavi i18n da tradurre lato FE** — nessun testo viene dal DB:

```text
vendite.preventivi.azione_reason.ordine_gia_generato
vendite.preventivi.azione_reason.gia_in_commessa
vendite.ordini.azione_reason.ddt_collegati
vendite.ordini.azione_reason.gia_in_commessa
vendite.ordini.stato_info.evaso
vendite.ordini.stato_info.parzialmente_evaso
vendite.ddt.stato_info.consegnato_usa_reso
vendite.ddt.stato_info.reso
```

**Un dettaglio di tempi.** Le prime quattro chiavi (`azione_reason.*`) arrivano
dentro `reasons` sui bottoni spenti **appena** completiamo l'ultimo passo del §6; le
`stato_info.*` sono già a dato nel `meta` degli stati e usciranno dalle capability
con lo stesso passo. Conviene quindi tradurle tutte insieme, ma non aspettarsi che
compaiano prima.

> ✅ **Tradotte tutte e otto (it + en) il 2026-08-04**, come suggerito. Le tre
> policy errore sono a registro. Vedi §8.

## 6. Definizione di «fatto» — stato al 2026-08-04

- [x] `fn_check_preventivo_annullabile` e `fn_check_ordine_annullabile` — `20260804-33`;
- [x] tre codici errore a catalogo, con `causa` e `soluzione` — id 836–838;
- [x] tre transizioni riattivate — CSV, nessun changeSet (loader `runOnChange`);
- [x] **i guard**, senza i quali la riattivazione sarebbe un danno — `20260804-34` (ordine), `20260804-35` (preventivo);
- [x] `meta` dei quattro stati «chiusi» — CSV `stati_doc_ordini` / `stati_doc_ddt`;
- [x] pgTAP: per ciascuno dei sei stati, o l'azione c'è ed è azionabile, o c'è la spiegazione;
- [x] `test-transizioni-uscita-manuale-v1.sql` **verde 3/3**, e tolto dalla baseline (103 → 102);
- [x] esposizione di `reasons` e `nessuna_azione_key` — `20260804-68` (preventivo), `-69` (ordine), **`-70` (DDT)**. ⚠️ **Questa riga diceva «preventivo / _ordine» e sbagliava il conto**: delle quattro `nessuna_azione_key` seminate, due vivono su stati del **DDT** (CONSEGNATO, RESO). Fermarsi ai due domini nominati avrebbe lasciato metà del lavoro a dato e invisibile — ed è esattamente la riga «DDT CONSEGNATO / RESO: barra vuota e muta» che il BE ha misurato in campo (§8.2);
- [x] consolidamento delle due regole di annullamento (§7.3) — `20260804-73` (la fn pura assorbe il criterio della porta), `-74` (la porta delega); con esso esce di scena `PREV_ANNULLAMENTO_COMMESSA_ATTIVA`, che chiude il §8.3;
- [ ] guard di matrice per il preventivo (§6.2) — **da fare**;
- [ ] storicizzazione del preventivo (§7.2) — **da fare**, resta il prerequisito del guard di matrice.

**Tutto applicato il 2026-08-04**: `20260804-33`, `-34`, `-35`, `-68`, `-69`, `-70`, `-73`, `-74` EXECUTED. Il codice errore nuovo `E_PREV_ANNULLA_COMMESSA_EMESSA` (id 839) è a catalogo: il loader `runOnChange` dei messaggi ha ripescato il CSV da solo (`RERAN`), senza changeSet dedicato.

**pgTAP del cantiere, sul database aggiornato:**

| Suite | Esito |
| --- | --- |
| `script/test-capability-motivi-e-nessuna-azione-v1.sql` *(nuovo)* | **9/9** |
| `config/test-transizioni-uscita-manuale-v1.sql` | **3/3** |
| `script/test-catalogo-messaggi-errore-completo.sql` | **4/4** |
| 21 suite che toccano le funzioni modificate | **zero variazioni** prima/dopo |

⚠️ Resta **1 rosso** su `vendite/test-fn-cambia-stato-preventivo.sql`, ed è
preesistente e già in `baseline-rossi.tsv`: il test 9 pretende che
`DRAFT → EMESSO` sia vietata con totale zero, cioè fissa una decisione
**ribaltata il 2026-07-16** («un documento a totale zero deve poter essere
emesso»). È lo stesso fenomeno che il §7.4 mette in guardia più sotto: un test
che fotografa la scelta vecchia diventa rosso quando la scelta cambia. Va
riscritto o ritirato, ma è un debito di quel cantiere, non di questo.

### 6.0 Il presidio è diventato la regola, invece di elencare eccezioni

Il test R1 all'inizio era severo e basta: *ogni stato deve avere un'uscita manuale*.
Con le decisioni di Tid è diventato quello che doveva essere fin dall'inizio:

> **o la via d'uscita c'è, o c'è scritto perché non c'è.**

Uno stato senza uscite manuali passa il test **solo se** dichiara
`meta->>'nessuna_azione_key'`, cioè la chiave con cui il frontend spiega
all'operatore cosa sta succedendo. Il silenzio, invece, resta rosso.

Il conto è sceso da sei stati a zero in due passaggi: `preventivo ACCETTATO` e
`ordine CONFERMATO` sono rientrati perché hanno riavuto l'annullamento; gli altri
quattro perché adesso dicono perché non ce l'hanno. Nessuna eccezione registrata a
mano, nessuna allowlist: la regola è una sola e vale per tutti.

### 6.1 Verifiche già fatte (in transazione, prima dell'apply)

| Prova | Esito |
| --- | --- |
| `fn_check_ordine_annullabile` su un ordine con DDT figlio | due motivi: `E_ORD_ANNULLA_CON_DDT`, `E_ORD_ANNULLA_IN_COMMESSA` |
| Ordine **senza** figli a valle → annullamento | passa, come deve |
| Ordine **con** figli, transizione ammessa in matrice → annullamento | **bloccato** dalla Regola 3 col codice giusto |

> ℹ️ Nella prova il messaggio è uscito come `[MESSAGGIO NON DEFINITO: E_ORD_ANNULLA_CON_DDT]`,
> ed è corretto così: i codici viaggiano nel CSV che il loader carica in `80_data`,
> fase che in una transazione di prova non è ancora passata. Dopo il `migrate` il
> messaggio si legge per intero.

<!-- markdownlint-disable-next-line MD028 -->
> ⚠️ **Un errore da non fare nella verifica.** Il primo tentativo sembrava
> funzionare — l'annullamento veniva rifiutato — ma il rifiuto arrivava dalla
> **Regola 1** (transizione non in matrice), perché l'ordine scelto era già `EVASO`.
> La Regola 3 non era stata attraversata affatto. Per verificarla davvero è servito
> un ordine *dal cui stato* `ANNULLATO` fosse raggiungibile. Un ramo si verifica dal
> percorso che lo attraversa, non dal fatto che il risultato sembri quello atteso.

### 6.2 Una scoperta che vale una decisione a parte

**Il preventivo non ha un guard di transizione.** Commessa e ordine hanno un trigger
che legge la matrice e rifiuta ciò che non c'è; il preventivo no: la sua matrice
governa quali bottoni compaiono, non che cosa il database accetta. Un `UPDATE` diretto
sullo stato passa comunque.

Non è un difetto introdotto qui — c'era già — ma significa due cose. La prima è che
riattivare la transizione nel seed, da solo, non avrebbe protetto niente: da qui il
guard nuovo `20260804-35`, volutamente ristretto al **solo annullamento**. La seconda
è che rendere la matrice vincolante anche per il preventivo è la cosa giusta e va
fatta — ma è un guard restrittivo su percorsi che nessuno ha mai verificato contro i
test esistenti, e introdurlo di soppiatto dentro un altro cantiere è il modo migliore
per rompere qualcosa senza capire perché.

**Decisione presa (Tid, 2026-08-04): si fa**, come slice a sé. La misura preliminare
è stata fatta, ed è il §7.

---

## 7. Analisi — quando (e come) vincolare gli stati del preventivo

> **Fatta il 2026-08-04**, prima di scrivere qualunque guard. Il punto di partenza era
> «l'esposizione è larga, prima misuriamo». La misura ha ribaltato la diagnosi: **la
> matrice del preventivo è già rispettata da tutti**, solo non è imposta dal database.

### 7.1 Chi cambia lo stato di un preventivo, davvero

| Scrittore | Passa dalla matrice? |
| --- | --- |
| `vendite.fn_cambia_stato_preventivo` | **sì** — la valida esplicitamente |
| BE (`preventivi_repository.py`) | chiama quella funzione, non fa `UPDATE` |
| `fn_push_preventivo_a_ordine`, `fn_ricalcola_totali_preventivo` | toccano la tabella ma **non la colonna di stato** |

Cercando fra tutte le funzioni plpgsql del database, quelle che aggiornano
`vendite.preventivi.stato_doc_preventivo_id` sono **zero**, tranne la porta. Quindi:

> Oggi nessun percorso vivo fa una transizione fuori matrice.

Questo cambia il verso della decisione. Non stiamo per **restringere** qualcosa che
era libero: stiamo per rendere **vera per costruzione** una regola che oggi è vera per
disciplina. Il rischio di rompere un flusso applicativo è basso; il valore è che la
regola smetta di dipendere dal fatto che tutti si ricordino di passare dalla porta.

⚠️ **Ma il beneficio immediato è modesto, e va detto.** Il guard proteggerebbe solo
gli `UPDATE` diretti: migrazioni, script di manutenzione, codice futuro. È difesa in
profondità, non una falla che si sta chiudendo. Per questo il §7.4 lo mette **dopo**
due cose che valgono di più.

### 7.2 🔴 Il preventivo non ha memoria dei propri stati

`vendite.preventivi` ha il trigger di storicizzazione, ma:

| | |
| --- | --- |
| righe in `storico.preventivi` | **0**, su 163 preventivi |
| preventivi con `storicizza = true` | **0 su 163** |
| tabella in `config.storico_set_storicizza` | **no** |

Le tre cose insieme spiegano lo zero: senza registrazione nel catalogo il flag viene
azzerato dopo il primo `UPDATE`, e qui non è mai stato acceso nemmeno una volta.
Il risultato è che **di un preventivo non si sa quando è stato emesso, accettato o
annullato, né da chi**. Il documento commerciale che apre il ciclo di vendita è
l'unico senza traccia.

Non è un dettaglio, ed è la ragione per cui va chiuso **prima** del guard: se domani
il guard rifiutasse una transizione che qualcuno faceva, non avremmo alcun modo di
ricostruire cosa succedeva prima. Oggi la misura del §7.1 si è potuta fare solo
leggendo il codice, non i dati.

Rimedio: `storicizza` a default `true` sulla tabella, backfill del flag sulle righe
esistenti, registrazione in `config.storico_set_storicizza` — la stessa procedura già
seguita per `config.user_emittente_attivo`.

### 7.3 ✅ Ho introdotto io una seconda regola di annullamento — RISOLTO

> **Chiuso il 2026-08-04** con `20260804-73` (la fn pura assorbe) e `-74` (la
> porta delega). Il testo che segue è la diagnosi come fu scritta; il §9.3
> racconta come è stata risolta, e **perché il criterio della porta è stato
> assorbito e non cancellato** — cosa che alla prima lettura sembrava ovvia e
> non lo era.

Va scritto perché è esattamente l'errore contro cui è nata la regola R2 di questo
brief. Oggi, per la domanda «questo preventivo si può annullare?», esistono **due**
risposte diverse:

| Chi | Criterio |
| --- | --- |
| `fn_cambia_stato_preventivo` (già c'era) | esistono righe in commessa con `stato_emissione = 'EMESSA'`, cercate per `segment_key` che inizia con `PREV:<uid>:R:` |
| `trgfn_preventivi_guard_annullamento` (aggiunto ieri da noi) | esiste un ordine generato **oppure** una riga in `commesse_sorgenti` |

Il secondo è più severo del primo — un preventivo spinto in commessa ma non ancora
emesso oggi passerebbe dalla porta e verrebbe fermato dal trigger — quindi
l'incoerenza non apre buchi, ma produce due messaggi diversi per la stessa
situazione, e un giorno divergeranno sul serio.

**Consolidamento proposto:** `fn_check_preventivo_annullabile` assorbe anche il
criterio della porta (righe già `EMESSA`), diventando un vero superinsieme; la porta
smette di avere la regola in casa e chiama la funzione, come già fa il guard
dell'ordine. Una regola, una sede, un messaggio.

> ℹ️ **Effetto collaterale utile.** La porta solleva
> `PREV_ANNULLAMENTO_COMMESSA_ATTIVA`, un codice **senza prefisso `E_`**. È
> regolarmente a catalogo, quindi nessun danno — ma il presidio
> `test-catalogo-messaggi-errore-completo.sql` cerca solo codici `E_*` e non l'avrebbe
> visto. Allargare la ricerca a qualunque literal maiuscolo produce 31 falsi positivi
> (valori di dominio come `ANNULLATA`, `DELETE`, `CONTRATTO` passati come parametri),
> quindi non è la soluzione: il limite del presidio va **dichiarato**, non finto.
> Consolidando il §7.3 quel codice sparisce da solo.

### 7.4 L'ordine di lavoro che ne esce

> **Aggiornamento 2026-08-04 (sera).** L'ordine è stato eseguito **a partire dal
> punto 2**, non dal punto 1, e la ragione va scritta: davanti al punto 1 c'era
> l'esposizione delle capability (§6, ultima riga), che non compare in questa
> lista perché quando fu scritta sembrava un residuo. Non lo era: era l'unica
> cosa che separava l'operatore dal bottone spento col motivo, e teneva fermi
> BE e FE. Fatta quella, il punto 2 è venuto subito dopo perché chiudeva anche
> il rifiuto illeggibile misurato dalla metà a video (§8.3). **Restano il punto
> 1, il 3 e il 4**, nell'ordine originale — che per loro tre resta valido: la
> storia prima del guard, il guard prima del test che lo fissa.

1. **Storicizzazione del preventivo** (§7.2). ⏳ **Da fare.** Prima del guard di
   matrice: è ciò che rende verificabile qualunque cosa venga dopo, ed è
   indipendente dal resto.
2. ~~**Consolidamento delle due regole di annullamento** (§7.3).~~ ✅ **Fatto il
   2026-08-04**, `20260804-73` + `-74`. Chiudeva un'incoerenza introdotta da noi;
   ha chiuso anche il §8.3 del BE, perché con esso sparisce il codice senza
   prefisso `E_` che il backend non riusciva a tradurre.
3. **Guard di matrice** `trgfn_preventivi_guard_transizione`, sul modello dell'ordine.
   A questo punto è una formalità a basso rischio: sappiamo che nessuno viola la
   matrice, abbiamo la storia per accorgercene se qualcosa cambia, e la regola di
   dominio è già in una funzione pura.
4. **pgTAP** che fissa la matrice come vincolante — e che, come quello dell'ordine,
   diventerà rosso il giorno in cui qualcuno cambierà idea. È il punto.

⚠️ Prima del passo 3, cercare i pgTAP che eseguono transizioni sui preventivi: è
esattamente il controllo che è mancato riattivando `CONFERMATO → ANNULLATO`
sull'ordine, dove un test che *fissava* la decisione vecchia è diventato rosso. Quel
rosso ha fatto il suo mestiere; la prossima volta va previsto, non subito.

---

## 8. Risposta della metà a video (BE/FE, 2026-08-04)

> Scritto da BE/FE su `dev/backend-tid`. Rendiconto completo:
> [brief-be-fe-vie-uscita-operatore.md](brief-be-fe-vie-uscita-operatore.md).
> Qui solo ciò che il team DB deve sapere per chiudere il §6.

### 8.1 Fatto

| Voce del §5 | Stato |
| --- | --- |
| Verbi «Annulla» disponibili | ✅ **Erano già a video**: `available_actions` è data-driven, la riattivazione dei CSV è bastata (conferma inclusa, `requires_confirm` nel `meta`). Zero righe di codice |
| Tre codici errore a `error_policies.py` | ✅ 409 + messaggio d'azione. Verificato: da *400 «Errore di validazione»* a 409 parlante |
| Otto chiavi i18n | ✅ it + en, testi presi dalla tabella §4 |
| `reasons` sui bottoni spenti | ✅ **già supportato** dal building block dal brief guard-righe: si accende da solo quando il campo arriva |
| `nessuna_azione_key` | ✅ prop `infoKey` su `DrawerActionsBar`, cablata su **tutti e otto** i drawer documento vendite (non solo ordine/DDT): il giorno in cui scrivete la chiave su un altro stato, non c'è codice da toccare |

Nessun endpoint nuovo: l'annullamento passa dal cambio stato generico, il target
arriva da `available_actions[].target_state`, il grafo resta solo vostro.

### 8.2 Misurato sulle capability vive (non dedotto)

Interrogate sul DB di sviluppo dal canale di sistema — le tabelle documento hanno
RLS, e senza GUC si legge zero e si conclude il falso:

| Prova | Esito |
| --- | --- |
| preventivo ACCETTATO #1816, EMESSO #535 | `annulla` presente e **abilitata** |
| ordine CONFERMATO #633 | `annulla` presente e **abilitata** |
| preventivi già in commessa #302 / #301 / #299 | `fn_check_preventivo_annullabile` dà `E_PREV_GIA_IN_COMMESSA`, ma il bottone è **acceso**: `reasons` non è nel blob |
| ordine EVASO #5388 | zero azioni e `nessuna_azione_key` **assente dal blob** (è a dato nel `meta`, non ancora esposta) |

Cioè: l'ultima riga aperta del §6 è **l'unica** cosa che separa l'operatore dal
«bottone spento col motivo» invece del rifiuto dopo il click.

### 8.3 Due segnalazioni che vi riguardano

🔴 **Il presidio i18n era cieco su `nessuna_azione_key`.**
`scripts/check_i18n_keys.py` guardava solo `label_key`/`reason_key` e, fra i
seed, solo i file `transizioni_stati_*.csv`. La chiave nuova vive nel `meta`
degli **stati** (`stati_doc_*.csv`): le quattro chiavi erano invisibili al guard,
che restava verde. Esteso a entrambe le dimensioni. Se in futuro introducete una
terza proprietà-indirizzo i18n, va aggiunta lì (`_PROP_KEY`), altrimenti l'errore
torna silenzioso — e nel caso «nessuna azione» è peggio del solito: quando manca
la label di un pulsante resta almeno il pulsante muto, qui non resta niente.

Effetto collaterale: il guard, vedendo di più, ha reso verdi **7 chiavi rosse da
prima** — 4 di `vendite.lotti.azione_reason.*` e 3 di `vendite.commesse.*`
(cantieri azioni-lotto ed emittibilità). Erano motivi ostativi che il DB mandava
e il frontend non sapeva dire. Tradotte.

🔴 **`PREV_ANNULLAMENTO_COMMESSA_ATTIVA` non è leggibile dall'operatore.**
Il vostro §7.3 lo cita come limite dichiarato del presidio catalogo. Lato BE il
costo è più alto di così: l'estrattore di codici applicativi cerca `E_[A-Z]...`,
quindi quel codice **non viene agganciato** e la risposta degrada a `E_DATABASE`
— messaggio generico, dettaglio tecnico nascosto per policy. Provato:

```text
[PREV_ANNULLAMENTO_COMMESSA_ATTIVA] …  ->  E_DATABASE  http=400  "Errore durante l'operazione database."
```

Fino a ieri era teoria (da `ACCETTATO` il preventivo non si annullava affatto);
da oggi è un percorso vivo. **Non l'abbiamo tappato lato BE di proposito**:
allargare la regex fa falsi positivi — lo stesso conto del vostro §7.3 — e
mappare a mano il singolo codice sarebbe una seconda regola di annullamento in un
terzo posto, l'opposto della R2 di questo brief. Il **consolidamento §7.3**, che
avete già deciso, lo chiude alla radice: quel codice sparisce da solo. È un
argomento in più per metterlo prima del guard di matrice nell'ordine del §7.4.

### 8.4 Cosa aspettiamo

1. `reasons` + `nessuna_azione_key` nelle due `fn_available_actions_*` (§6,
   ultima riga aperta) → **niente lavoro FE**, si accendono da soli;
2. consolidamento §7.3 → chiude l'8.3;
3. resta a Tid la validazione in-app dell'annullamento (preventivo da
   EMESSO/ACCETTATO, ordine da CONFERMATO).

---

## 9. Risposta del DB alla metà a video (2026-08-04, sera)

> Scritto dal team DB su `dev/db-tid`, dopo il §8. Chiude le due voci che il
> §8.4 aspettava; la terza (validazione in-app) resta a Tid.

### 9.1 Fatto

| Voce del §8.4 | Stato |
| --- | --- |
| `reasons` + `nessuna_azione_key` nelle capability | ✅ `20260804-68/-69/-70` **applicati**. Non due funzioni ma **tre**: il §6 sottostimava, vedi sopra |
| Consolidamento §7.3 | ✅ `20260804-73/-74` **applicati**, pgTAP verde |
| Validazione in-app | ⏳ resta a Tid |

**Verificato sui documenti che avete misurato**, non su fixture costruite:
i preventivi #302 / #301 / #299 ora danno `enabled=false` con
`reason=GIA_IN_COMMESSA`; #535 e #1816 restano accesi; l'ordine #633 resta
acceso; l'ordine EVASO #5388 espone `nessuna_azione_key =
vendite.ordini.stato_info.evaso`. Le vostre quattro righe del §8.2 sono
tutte ribaltate.

### 9.2 Misurato, non dedotto

Le asserzioni del pgTAP nuovo (`test-capability-motivi-e-nessuna-azione-v1.sql`,
**9/9**) non guardano un documento scelto a mano ma la popolazione intera, e i
conteggi stanno nella descrizione dei test:

| Misura | Esito |
| --- | --- |
| preventivi con azione verso ANNULLATO | 92, `enabled` concorde col verdetto della fn pura su **92/92** |
| di cui bloccati | 12, con `reasons` identico ai motivi della fn pura |
| ordini con azione verso ANNULLATO | 57, concordi **57/57** |
| documenti in stato chiuso senza azioni vive | 27 ordini + 9 DDT, **tutti** ricevono la nota |
| regressione sulle suite toccate | 21 suite, **zero** variazioni prima/dopo |

⚠️ **Un limite dichiarato, non nascosto.** 5 ordini EVASO su 32 **non**
ricevono la nota, perché hanno ancora «Invia a fatturazione» abilitata: la
regola del §4 è «la nota risponde alla lista vuota», e con un bottone vivo la
lista vuota non c'è. È coerente col brief, ma è una decisione che vale la pena
riguardare: se preferite che la nota accompagni sempre lo stato chiuso anche
accanto a un'azione applicativa, è una riga da cambiare in tre funzioni. Nota
a margine: quei 5 ordini esistono perché `test-seed-stati-doc-ordini-evaso-v1.sql`
è rosso in baseline sui test 4 e 6 — EVASO non è più terminale come quel test
afferma, e la reason `ORDINE_GIA_EVASO` non esiste più. Debito preesistente,
non introdotto qui.

⚠️ **Un ramo non misurato.** Il test 5 va in SKIP: oggi non esiste **nessun**
ordine con l'annullamento bloccato, quindi il ramo `reasons` dell'ordine non è
esercitato da nessun soggetto vivo. È lo stesso codice del preventivo, che è
coperto su 12 documenti, ma vale saperlo invece di leggere un verde che non ha
misurato niente.

### 9.3 Due cose che vi riguardano

🔴 **Un nono codice errore, e una nona chiave i18n.** Il consolidamento del
§7.3 non poteva limitarsi a cancellare la regola della porta. Misurato prima di
decidere: 10 preventivi hanno righe già `EMESSA` in commessa e **tutti e 10**
sono anche in `commesse_sorgenti`, quindi il motivo esistente li coprirebbe —
ma la sovrapposizione è un fatto, non una costruzione. `commesse_sorgenti` ha
un solo scrittore, `fn_link_commessa_sorgente`, e **nessuna funzione del
database la chiama**: la scrivete voi, da `commesse_repository.link_sorgente()`,
con una chiamata separata dall'upsert delle attività. Quindi un motivo legge una
*registrazione* fatta da Python e l'altro un *effetto* prodotto dal database:
coincidono finché un solo percorso scrive entrambe le cose. Il criterio della
porta è stato perciò **assorbito come motivo a sé**, non cancellato. Ne
discendono due cose per voi:

| Cosa | Valore |
| --- | --- |
| Codice errore nuovo, da dichiarare in `error_policies.py` (409, come i tre fratelli) | `E_PREV_ANNULLA_COMMESSA_EMESSA` (id 839) |
| Chiave i18n nuova, la nona | `vendite.preventivi.azione_reason.commessa_gia_emessa` |

**Il travaso è già avvenuto**, misurato dopo l'apply: dei 47 preventivi con
l'annullamento bloccato, **10 ricevono ora `E_PREV_ANNULLA_COMMESSA_EMESSA`** e
37 restano su `E_PREV_GIA_IN_COMMESSA`. È un codice più preciso — dice che a
valle esiste una **fattura**, non solo un collegamento — ed è un cambio visibile
all'API: finché non lo dichiarate in `error_policies.py`, quei 10 casi
degradano al generico, esattamente come il codice che questo lavoro ha appena
ritirato.

🟢 **`PREV_ANNULLAMENTO_COMMESSA_ATTIVA` è morto.** Verificato: dopo `-74`,
**zero** funzioni vive in `vendite` e `script` lo sollevano. La riga resta a
catalogo come storia — non si cancella un messaggio che può essere già finito in
un log — ma il degrado a `E_DATABASE` che avete misurato non ha più un percorso
che lo produca. Non serve toccare la regex.
