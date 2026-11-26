# Analisi del modello — L'area clienti: una porta sola, l'iscrizione da sé, il documento scelto all'ordine

## ⏭️ Chi riparte — aggiornato al 2026-11-25

**Riparte: la sessione DB**, col via di Tid, nel [brief DB unico](brief-db-accessi-area-clienti.md) (aperto il
2026-11-25), R-4 come primo giro: le decisioni della revoca (D-R1, D-R2, D-R4, D-R5 di
[brief-be-accessi-credenziale-e-vesti](brief-be-accessi-credenziale-e-vesti.md) §1.3; D-R7, D-R8, D-R9 del brief
DB) sono prese il 2026-11-25. Resta aperta D-M9 (§7), che non blocca il primo giro.

| # | Chi | Che cosa | Dove | Aspetta |
| --- | --- | --- | --- | --- |
| 1 | Tid | ~~D-M4 … D-M8, D-R1 … D-R5~~ decise il 2026-11-25; resta D-M9 | §7 | — |
| 2 | sessione DB | Il **brief DB unico** (Tid, 2026-11-25): gli accessi di T9, R-4 come primo giro, poi la veste cliente unica, l'indice per soggetto, l'iscrizione da sé, il ritiro dei rami del canale shop | §5.1, §8 | — |
| 3 | team BE/FE | Una porta clienti, la scelta «per chi», l'iscrizione, il ritiro della porta shop | §5.2, §5.3 | 2 |
| 4 | team BE/FE + doc | La guida multi-face riscritta sul modello nuovo | §6 | 2, 3 |
| 5 | Tid | Il collaudo a video dell'iscrizione e dell'area clienti | — | 3 |

**Decisioni aperte di Tid:** D-M9 (§7); D-R1, D-R2, D-R4, D-R5 nel brief BE degli accessi. Le decisioni di modello
prese il 2026-11-25 sono al §2 e al §7.
**Da committare:** questo documento, e le modifiche dello stesso giorno a
[sviluppo-multi-face-da-completare](sviluppo-multi-face-da-completare.md) §2.3, §3.6 e a
[brief-be-accessi-credenziale-e-vesti](brief-be-accessi-credenziale-e-vesti.md) §1.3.

## 0. Il piano da percorrere

- **Fase 0 — Il modello** (Tid)
  - [x] Iscrizione da sé di privati e partite IVA, con la sola conferma dell'email (R-1 … R-3) — 2026-11-25
  - [x] L'email resta la chiave d'ingresso, il secondo fattore protegge (M-1) — 2026-11-25
  - [x] Il documento si sceglie all'ordine (M-2) — 2026-11-25
  - [x] Una sola porta clienti, la visibilità la decide il soggetto (M-3) — 2026-11-25
  - [x] D-M4, D-M5 (per le aziende), D-M7, D-M8; un brief DB unico con T9 e R-4 — 2026-11-25
  - [ ] D-M9, l'accesso dei privati (§7)
- **Fase 1 — DB** (sessione DB, il brief unico con T9 e R-4)
  - [ ] Censimento completo degli oggetti che leggono la veste shop o il canale come confine (§5.1 è il punto di partenza, non il confine)
  - [ ] La veste cliente unica e l'indice «una veste accesa per credenziale e soggetto»
  - [ ] L'iscrizione da sé come verbo DB, sopra `fn_crea_cliente`
  - [ ] Il ritiro dei rami `SHOP_CUSTOMER` (perimetro, policy, guard), con la sezione «Garanzie ritirate»
  - [ ] R-4, la veste revocata, sulla veste cliente
- **Fase 2 — BE/FE**
  - [ ] Una porta clienti, il login con la scelta «per chi»
  - [ ] L'iscrizione e la conferma dell'email; il pulsante «Attiva shop» ritirato
  - [ ] Il secondo fattore obbligatorio secondo D-M5
  - [ ] Il negozio come funzione dell'area clienti (quando si costruisce)
- **Fase 3 — Doc e collaudo**
  - [ ] La guida multi-face riscritta; le altre guide del §6 coi loro esiti
  - [ ] Il collaudo a video
  - [ ] Archiviazione in `work-done/`

> **Chi scrive:** sessione DB (`dev/db-tid`), 2026-11-25, su richiesta di Tid. **A chi:** Tid; poi la sessione DB e
> il team BE/FE.
> **Origine:** l'analisi critica di R-4 (la veste revocata) in
> [brief-be-accessi-credenziale-e-vesti](brief-be-accessi-credenziale-e-vesti.md) §1.3. Discutendo come un cliente
> sconosciuto entra nello shop, Tid ha deciso che l'iscrizione è da sé, che il documento lo sceglie il cliente e
> che portale e shop non sono più due porte.
> **Brief vicini verificati:**
>
> - [sviluppo-multi-face-da-completare](sviluppo-multi-face-da-completare.md): ha la registrazione (§2.3) e le
>   decisioni di dominio (§3). Il §3.6 tiene R-1 … R-3; questa analisi è il modello che le contiene, e il §3.6 la
>   rimanda. Il resto del documento (API di dominio, RLS del fornitore) resta lì;
> - [sviluppo-portale-shop](sviluppo-portale-shop.md) §1.4 (registrazione dello shop) e §3.2 (checkout): superati
>   da §3.3 e §3.4 di questa analisi, da marcare al primo giro che li riprende;
> - [brief-be-accessi-credenziale-e-vesti](brief-be-accessi-credenziale-e-vesti.md): R-4 resta valida; A-6 si chiude
>   per ritiro del pulsante (§8);
> - [brief-db-revisione-anagrafiche](brief-db-revisione-anagrafiche.md) §17.1, T9: S67 è superata da questa analisi
>   (§8); S64 no;
> - [piano-autenticazione-provider-esterni-oauth](piano-autenticazione-provider-esterni-oauth.md): l'accesso con
>   Google, Microsoft, Apple. Le sue Q-8 (registrazione autonoma via provider) e Q-9 (il secondo fattore dopo il
>   provider) toccano D-M5 e D-M9; la regola «mai collegare un provider per sola email» (§B.5.2) vale anche qui.
>
> **Guide verificate:** `scripts/guide_coinvolte.py` sugli oggetti del §5.1; gli esiti al §6.

---

## 1. Il problema in poche righe

Oggi un cliente entra in ZeroErp da **due porte diverse**: il portale, pensato per le aziende, e il negozio
online, pensato per i privati. Le due porte hanno due vesti diverse, due login, due regole su che cosa si vede, e
documenti diversi: fatture nel portale, ricevute nel negozio. In più, un cliente che nessuno ha invitato non ha
nessuna strada per entrare: l'iscrizione da sé non esiste.

La separazione è nata il 2026-04-20 per una ragione precisa: **il privato non deve vedere gli acquisti della sua
azienda**. Quella ragione oggi si risolve meglio con l'anagrafica: Mario privato e Rossi Srl sono già **due
soggetti diversi**. Due porte per separarli non servono più, e hanno un costo: ogni regola (iscrizione, revoca,
visibilità, documento) va scritta due volte.

## 2. Le decisioni di Tid — 2026-11-25

| # | Decisione |
| --- | --- |
| R-1 | **Iscrizione libera per il cliente nuovo**, privato o con partita IVA: nascono anagrafica, cliente e accesso spento; l'email di conferma lo accende al primo accesso. Nessun intervento dell'operatore |
| R-2 | **Cliente già in anagrafica**: si aggancia da solo solo se l'email dell'iscrizione è già fra i suoi contatti; altrimenti diventa una richiesta, che l'operatore approva con l'invito |
| R-3 | **La partita IVA iscritta da sé resta «da completare»** e non si fattura finché un operatore non la verifica |
| M-1 | **L'email resta la chiave d'ingresso**: non si aggiunge un nome utente. Contro le password rubate protegge il **secondo fattore** |
| M-2 | **Il documento si sceglie all'ordine**: chi compra per un'azienda riceve la fattura sempre; un privato riceve la ricevuta, e la fattura se la chiede |
| M-3 | **Una sola porta clienti.** Che cosa si vede lo decide il **soggetto**, non il canale; il negozio diventa una funzione dell'area clienti |

Perché M-1 e non un nome utente: il nome utente non è un segreto (se lo assegniamo noi viaggia per email, se lo
sceglie la persona è di solito quello che usa ovunque), e il recupero della password passa comunque dall'email.
Indovinare chi è iscritto è già impedito: il login risponde allo stesso modo che il nome esista o no (R-7 del
piano accessi), e l'iscrizione risponde sempre «ti abbiamo scritto».

## 3. Il modello

### 3.1 I pezzi

Ogni accesso di un cliente mette insieme gli stessi pezzi, per un privato come per un'azienda:

| Pezzo | Che cos'è | Di chi è |
| --- | --- | --- |
| **Credenziale** | email e password: *chi* entra | sempre di una **persona**, una sola per persona |
| **Soggetto** | l'anagrafica: il privato, oppure l'azienda | di chi compra |
| **Cliente** | «questo soggetto è nostro cliente», con il suo conto di fatturazione | del soggetto |
| **Veste cliente** | la porta che fa entrare quella credenziale **per quel cliente** | lega credenziale e cliente |

- **Privato**: la persona *è* il soggetto.
- **Azienda**: la persona è il **referente**, il soggetto è l'azienda. La credenziale resta della persona; se il
  referente cambia, si dà la veste a un'altra persona e l'azienda non cambia.

### 3.2 Una porta, una veste per ogni cliente

```text
Mario (una credenziale, una email, una password)
 ├─ veste cliente → Mario, privato          vede i suoi ordini, ricevute e fatture
 └─ veste cliente → Rossi Srl (referente)    vede ordini, fatture e scadenze di Rossi Srl

Dopo il login, se le vesti sono più d'una, Mario sceglie «per chi» entra,
come un operatore sceglie l'azienda. Da lì vede solo i dati di quel soggetto.
```

- La **visibilità** la decide il soggetto della veste scelta: tutto ciò che è suo, da qualunque parte sia nato
  (dall'operatore, dall'area clienti, dal negozio).
- Il **negozio** (catalogo, carrello, ordine) è una funzione dell'area clienti, non una porta. Quali clienti la
  vedono è D-M6.
- I **fornitori** restano una porta a sé: è un altro rapporto, con altri dati. La stessa generalizzazione (un
  referente di due fornitori) vale anche per loro, ed è D-M8.

⚠️ **Il punto che il modello di oggi non ammette.** Una credenziale ha oggi al massimo **una** veste cliente
accesa (fatto letto sul catalogo il 2026-11-25: l'indice unico è su credenziale e tipo di veste). Mario non può
quindi essere insieme cliente privato e referente di Rossi Srl, e nemmeno referente di due aziende. Il modello
nuovo chiede che l'unicità sia **per credenziale e soggetto**: una veste accesa per ciascun cliente. Il login, che
oggi sceglie la veste dal solo tipo, deve far scegliere «per chi».

### 3.3 L'iscrizione da sé

Un meccanismo solo, per privati e partite IVA:

```text
1. EMAIL           la persona scrive la sua email
                   → risposta sempre uguale: «ti abbiamo scritto»

2. CHI SEI         privato:  nome, cognome, codice fiscale
                   azienda:  ragione sociale, partita IVA, codice fiscale, sede, SDI o PEC

3. ESISTI GIÀ?     si cerca il soggetto per codice fiscale e partita IVA
                   ├─ no → si crea il soggetto nuovo                        (R-1)
                   └─ sì → l'email è già fra i suoi contatti?
                           ├─ sì → ci si aggancia                           (R-2)
                           └─ no → diventa una RICHIESTA per l'operatore    (R-2)

4. COSA NASCE      il cliente (se non c'è), la credenziale (se l'email non ne ha già una),
                   la veste cliente SPENTA. Azienda: cliente «da completare»  (R-3)

5. CONFERMA        email con un link: chi clicca prova che la casella è sua
                   → la veste si accende → primo accesso

6. DOPO            azienda: l'operatore verifica i dati → fatturabile
```

- **L'email già nota** non crea una seconda credenziale: si aggiunge solo la veste, e il link la accende senza
  chiedere una password nuova. È lo stesso «un clic» che l'invito fa già oggi.
- Per questo il pulsante **«Attiva shop»** del portale **si ritira**: chi è già cliente e vuole entrare anche come
  privato fa l'iscrizione, e il passo 2 mette la veste sul soggetto giusto. Prima la metteva sul cliente del
  portale, cioè sull'azienda.
- **La revoca tiene** (R-4): se ai passi 3 e 4 si ritrova una veste che l'amministratore ha revocato, l'iscrizione
  si ferma. Si torna solo con un nuovo invito dell'operatore.
- **L'iscrizione e l'invito sono la stessa cosa vista da due lati**: l'invito la fa partire l'operatore, che conosce
  già il cliente; l'iscrizione la fa partire la persona. Da «cosa nasce» in poi i passi sono gli stessi.

### 3.4 Il documento si sceglie all'ordine

Il documento dipende da **chi compra**, cioè dal soggetto per cui Mario è entrato:

| Entra per | Documento |
| --- | --- |
| un'azienda (o la sua partita IVA, per l'attività) | **fattura**, sempre: è un obbligo di chi vende, non una scelta |
| sé, da privato | **ricevuta**; la **fattura** col codice fiscale, se la chiede all'ordine |

La scelta «per chi» del §3.2 decide già quasi tutto: resta solo la domanda «vuoi la fattura?» al privato. Anche i
prezzi (IVA inclusa per il privato, esclusa per l'azienda) seguono il soggetto, non il canale.

⚠️ La regola fiscale è scritta a grandi linee, e va confermata dal commercialista prima di costruire il checkout:
documento dovuto alla vendita online al privato, fattura su richiesta, tempi.

### 3.5 La sicurezza

- La chiave d'ingresso è l'**email** (M-1, conferma della D-9 del 2026-09-24).
- Il **secondo fattore** è della credenziale e vale per tutte le sue vesti. Esiste già. Quando diventa obbligatorio
  lo dice D-M5.
- Il **freno** contro le iscrizioni automatiche e la **pulizia** delle iscrizioni mai confermate sono parte
  dell'iscrizione, non un'aggiunta successiva.

### 3.6 Che cosa resta del canale

Il canale di origine (operatore, portale, negozio) **resta come dato**: dice da dove è nato un ordine, e serve alle
statistiche e alle regole commerciali. **Non decide più chi vede cosa.** Resta immutabile, come oggi.

## 4. Che cosa revoca, che cosa conferma

| Decisione esistente | Data | Esito |
| --- | --- | --- |
| «Lo shop è un canale B2C autonomo, non vetrina del portale» (decisione 1, `work-done/2026/pr-b-shop-b2c-cambio-modello.md` §1.1) | 2026-04-20 | **revocata** da M-3: il negozio è una funzione dell'area clienti |
| «Un credenziale, più vesti; la veste la sceglie la porta di login» (decisione 2) | 2026-04-20 | **confermata nella prima metà**; la seconda cambia: la porta clienti è una, e la veste si sceglie «per chi» |
| «Il portale vede tutto, lo shop solo lo shop» (decisione 3) | 2026-04-20 | **revocata** da M-3: la visibilità la decide il soggetto |
| «Lo shop emette ricevute, mai fatture; conti separati per canale» (decisione 4) | 2026-04-20 | **revocata** da M-2: il documento si sceglie all'ordine. Le ricevute restano, come documento del privato |
| «Al massimo una veste accesa per credenziale e tipo» (invariante del §1.2 dello stesso documento) | 2026-04-20 | **revocata**: diventa «per credenziale e soggetto» (§3.2) |
| D-9: portale e shop entrano con l'email (`work-done/2026/analisi-accessi-credenziale-e-vesti.md`) | 2026-09-24 | **confermata** da M-1 |
| D-4: «"mai attivata" resta attivabile dal pulsante come oggi» (stessa analisi) | 2026-09-24 | **superata**: il pulsante si ritira (§3.3). La metà sulla revoca resta |
| Guida multi-face §8.2: «chi ha già una credenziale attiva lo shop dal profilo, con conferma via email» | — | **assorbita**: è il passo 5 dell'iscrizione, per tutti |
| S67: la veste dello shop nasce accesa o spenta? (`brief-db-revisione-anagrafiche` §16.3) | 2026-11-22 | **chiusa**: la veste cliente nasce spenta, la accendono la conferma o l'invito |

## 5. Che cosa cambia nel costruito

Fatti letti il 2026-11-25 sulla doc auto-generata e sul codice: sono il **punto di partenza** del censimento, non il
suo confine. Il brief DB e il team BE/FE censiscono i lettori per intero, ciascuno nel suo lato.

### 5.1 DB

| Oggetto | Che cosa fa oggi | Che cosa cambia |
| --- | --- | --- |
| `anagrafiche.identita_digitali`, indice `uq_identita_digitali_auth_user_ruolo_attivo` | una veste accesa per credenziale e tipo | una veste accesa per credenziale e soggetto |
| `anagrafiche.identita_digitali`, indice `uq_identita_digitali_sr_ruolo_attivo` | una veste accesa per cliente e tipo | da rivedere con D-M7 (più referenti per la stessa azienda) |
| il tipo `config.ruolo_applicativo` | `CLIENTE_PORTALE` e `SHOP_CUSTOMER` distinti | una veste cliente sola (il nome è D-M4) |
| `script.fn_scope_ba_ownership` | vede il conto se la veste è cliente o shop; il filtro del canale lo fanno le policy | vede il conto del soggetto della veste, senza canale |
| `script.fn_scope_note_shop_perimetro`, `script.fn_resolve_controparte_sr_id` (modo `ordine_shop`), `script.fn_get_identita_sr_perimetro` | i rami della veste shop | si ritirano o si fondono nel ramo cliente |
| le policy RLS con il ramo shop (filtro `canale_origine = 'SHOP'`) | il confine di visibilità del negozio | si ritira il filtro del canale |
| `anagrafiche.trgfn_identita_digitali_guard_coerenza`, `anagrafiche.fn_crea_veste_portale` | conoscono la veste shop | una veste cliente |
| `shop.ricevute`, `shop.trgfn_ricevute_guard_ba_canale` | la ricevuta vuole un conto del canale shop | la ricevuta è il documento del privato, legata al soggetto (D-M6) |
| `canale_origine` su conti, ordini e fatture, con il guard di immutabilità | dato e confine | solo dato (§3.6) |
| `anagrafiche.fn_crea_cliente` | crea ruolo, conto e cliente | la usa il verbo dell'iscrizione: non se ne scrive un secondo |

### 5.2 Backend (19 file non di test citano la veste o la porta shop, conteggio del 2026-11-25)

La porta di login `/shop/token/` e le viste di attivazione dello shop; la porta portale che diventa la porta
clienti; il serializer del login multi-veste, che oggi sceglie la veste dal tipo e dovrà far scegliere «per chi»; le
classi di permesso per porta; `InvitoVeste` e i template d'invito dello shop; `ProfileActivateShopView` (si ritira);
lo stub `ShopRegisterCheckEmailView` (diventa l'iscrizione).

### 5.3 Frontend (12 file, stesso conteggio)

La scelta del canale nel login; il pulsante `AttivaAccessoShopButton` (si ritira); la lista degli accessi
dell'amministrazione; le costanti e lo store dell'autenticazione; le chiavi i18n. Nasce la scelta «per chi».

### 5.4 Che cosa non cambia

Una persona, una credenziale; l'invito e l'attivazione con un clic; la revoca (R-4); il secondo fattore e il freno
dei tentativi, che sono della credenziale; la porta dei fornitori; la porta degli operatori.

## 6. Le guide

| Guida / nota | Esito |
| --- | --- |
| [architettura-multi-face-auth](../../guide/architettura-multi-face-auth.md) | **contraddetta**: è il cambio di modello deciso al §2. Si riscrive dopo i giri DB e BE (§1, §2.1, §3.1, §5, §6.4, §7, §8, §12) |
| [architettura-permessi-e-autorizzazioni](../../guide/architettura-permessi-e-autorizzazioni.md) | da leggere nel giro DB: le classi di permesso per porta |
| [contratto-guc-app](../../guide/contratto-guc-app.md) | da leggere nel giro DB: la veste e il ruolo arrivano dalle GUC della sessione; con la scelta «per chi» il contratto non dovrebbe cambiare forma, ma va verificato |
| [generazione-cliente](../../guide/generazione-cliente.md) | coerente: l'iscrizione crea il cliente col verbo che la guida descrive |
| [soggetti-e-ruoli-anagrafici](../../guide/soggetti-e-ruoli-anagrafici.md) | coerente, ed è la base del modello: privato e azienda sono due soggetti |
| [risorse-umane-e-accessi](../../guide/risorse-umane-e-accessi.md) | coerente per l'operatore; nomina le vesti esterne, da riallineare col giro |
| `gestione-commesse`, `gestione-delle-istanze-utility`, `processi-pgagent-funzionali`, `pgtap-come-si-scrive-un-test` | un oggetto in comune, da leggere nel giro DB |
| `_sincronizzazione-accesso`, `_ultimo-super-admin` | coerenti: la regola «la credenziale è accesa se almeno una veste è utilizzabile» non cambia |

## 7. Le decisioni ancora aperte

| # | Domanda | Esito |
| --- | --- | --- |
| D-M4 | Il nome della veste cliente unica: si tiene `CLIENTE_PORTALE` o si rinomina? | ✅ **Tid, 2026-11-25: si rinomina, `CLIENTE`** |
| D-M5 | Il secondo fattore è obbligatorio per chi entra per un'azienda? | ✅ **Tid, 2026-11-25: sì.** Il secondo fattore è della credenziale: chi ha anche una veste aziendale lo usa sempre. Per i privati: D-M9 |
| D-M6 | Il negozio lo vedono tutti i clienti dell'area, o solo quelli abilitati? E la ricevuta a che cosa si lega, se non a un conto del canale shop? | da decidere col cantiere del negozio. Il modello qui non lo blocca |
| D-M7 | Un'azienda può avere più referenti con accesso (più vesti accese sullo stesso cliente)? | ✅ **Tid, 2026-11-25: sì.** Oggi l'indice lo vieta |
| D-M8 | La stessa generalizzazione (un referente per più soggetti) vale per la porta dei fornitori? | ✅ **Tid, 2026-11-25: sì**, con lo stesso indice; la porta resta separata |
| D-M9 | **L'accesso sicuro dei privati.** Il secondo fattore lo si impone anche a loro, o si offre l'accesso con Google, Microsoft, Apple? | aperta. **Proposta**: il privato sceglie fra (a) un provider, e allora la sicurezza dell'accesso è del provider (secondo fattore, passkey) e l'email è già verificata, senza la nostra email di conferma; (b) email e password, col secondo fattore **proposto con forza ma non imposto**. Diventa obbligatorio se un giorno si salvano metodi di pagamento. Per le aziende il nostro secondo fattore resta obbligatorio anche dopo il provider (Q-9 del piano OAuth, proposta di aprile). Fatti a sostegno: il pagamento con carta lo conferma la banca (3-D Secure) e i dati della carta non passano da ZeroErp, quindi l'account privato rubato espone dati personali, non pagamenti. L'accesso con Google chiede una dipendenza nuova (`django-allauth`, ok di Tid) e la verifica delle condizioni del provider |
| — | Con più aziende emittenti, sotto quale nasce il cliente iscritto da sé? | già aperta in `sviluppo-multi-face-da-completare` §3.6 |
| — | Un brief DB per il modello e uno per gli accessi (T9), o uno solo? | ✅ **Tid, 2026-11-25: un brief solo**, con R-4 come primo giro |

## 8. Ricadute sugli altri documenti

- [brief-be-accessi-credenziale-e-vesti](brief-be-accessi-credenziale-e-vesti.md): **R-4 resta**, e vale per la
  veste cliente unica e per l'iscrizione. **A-6 si chiude per ritiro**: il pulsante che riaccendeva lo shop non
  esisterà più. Le decisioni D-R1, D-R2, D-R4, D-R5 restano; D-R3 e D-R6 sono assorbite dal §3.3.
- [brief-db-revisione-anagrafiche](brief-db-revisione-anagrafiche.md) §17.1, T9: S67 chiusa da questa analisi
  (§4). Il brief DB degli accessi (T9) e il brief DB del modello sono **un brief solo** (Tid, 2026-11-25), con R-4
  come primo giro.
- [sviluppo-multi-face-da-completare](sviluppo-multi-face-da-completare.md) §3.6: rimanda qui per il modello.
- [sviluppo-portale-shop](sviluppo-portale-shop.md) §1.4 e §3.2: superati dal §3.3 e dal §3.4.

## 9. Rischi

- **Il censimento dei lettori.** Il ramo shop sta in policy, funzioni di perimetro e guard: un lettore dimenticato
  lascia al privato un confine che non c'è più, o glielo toglie dove serviva. Il giro DB lo censisce per intero e
  prova ogni caso con un pgTAP che costruisce le due vesti sulla stessa credenziale.
- **La scelta «per chi».** È il punto dove l'utente può vedere i dati sbagliati: la veste scelta deve arrivare alla
  sessione come oggi, una sola per volta, e ogni cambio di soggetto deve essere una sessione nuova o un cambio
  esplicito di veste.
- **La regola fiscale** del §3.4, da confermare prima del checkout.
- **Il tempo.** Le API di dominio del negozio non sono costruite: è il momento meno costoso per cambiare. Ogni
  pezzo costruito sopra le due vesti, da qui in poi, si rifà.

---
{% include-markdown "signature-core.md" %}
