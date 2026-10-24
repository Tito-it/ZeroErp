# Brief BE — Gli utenti di sviluppo: forniti da un verbo, etichettati, mai in produzione

## ⏭️ Chi riparte — aggiornato al 2026-10-22

**✅ Chiuso e archiviato in `work-done/` (Tid, 2026-10-22). Nessuno riparte: collaudo del drawer del listino superato, DB in git (#1920), policy rigenerate, smoke 2 noti su 51, tutti e due fuori perimetro (§9.12).** Il collaudo T-5 è fatto (2026-10-18, §9): provisioning, `env.sh` e login con
`dev.smoke` funzionano, `smoke` è disattivato; il giro degli smoke ha trovato un emittente di prova che non sa
emettere (nessun modello di documento) e smoke che vivevano dei dati di `EMITEST`.

⚠️ Due scostamenti dal §7, imposti dal modello (brief DB §5-ter.3): `dev.multiveste` ha il portale sul
**cliente 3** (un ruolo cliente ha una sola veste portale attiva, e il cliente 1 è di `dev.portale1`); gli
utenti dei portali non hanno un PF loro (la veste sta sul ruolo del cliente o del fornitore).

| # | Chi | Che cosa | Dove | Aspetta |
| --- | --- | --- | --- | --- |
| 1 | ✅ **Tid + team DB** | Il modello: ambiente immutabile, etichetta sulle radici, verbo che rifiuta in PRODUZIONE | §2 | — |
| 2 | ✅ **team DB** | Giro 1 applicato su dbdev (`SVILUPPO` dichiarato, 2026-10-16 14:20): ambiente e accensione dei processi. Risponde anche a D-1 (§6) | brief DB §5-bis | — |
| 3 | ✅ **BE** | L'elenco di che cosa crea il verbo, chiesto dal brief DB §5-ter | §7 | — |
| 4 | ✅ **Tid** | Le tre decisioni del §7.4: emittenti nuovi dal verbo, `dev.shop` dopo, portale senza contratto (2026-10-16) | §7.4 | — |
| 5 | ✅ **team DB** | Giro 2: i BB (2b-1), etichette, verbo `anagrafiche.fn_provisiona_dati_di_sviluppo`, presidio (2b-3). La colonna della lista Operatori: `LEFT JOIN dbops.credenziali_di_prova` (T-4) | brief DB §5-ter.2, §5-ter.3 | — |
| 6 | ✅ **Tid** | Apply del giro 2 su dbdev, pgTAP verdi (2026-10-18) | — | — |
| 7 | ✅ **BE** | T-1 … T-4 (2026-10-18, §8) e la 2b-2: il backend crea dalle madri del DB e le sue copie sono ritirate (brief DB §6.10) | §8; brief DB §6.10 | — |
| 8 | ✅ **Tid + BE** | Collaudo T-5: command su dbdev, `env.sh` a `dev.smoke`, giro degli smoke, `smoke` disattivato (2026-10-18). Esito e correzioni in §9 | §9 | — |
| 9 | ✅ **FE** | T-6: il filtro e il badge nella lista Operatori (2026-10-18) | §8 | — |
| 10 | ✅ **Tid → team DB** | I modelli di documento standard: un emittente nuovo emette dal primo giorno. Lato DB chiuso e applicato (2026-10-20); il seguito è il passaggio unico BE/FE di quel brief | [brief-db-modelli-documento-standard](brief-db-modelli-documento-standard.md) §11 | — |
| 11 | ✅ **BE** | T-7a (2026-10-18): preventivi-componenti e guida-inversione si costruiscono la materia; trovato il listino che non si spegne | §9.4 | — |
| 11-bis | ✅ **team DB** | Il guard di disattivazione del listino punta a una tabella eliminata: 500 a ogni spegnimento (R-1, Q-1). Il generatore ritira gli orfani (`20261021-21` … `-23`), provato sullo scratch e su dbdev in transazione | §9.6 | — |
| 11-ter | ✅ **Tid** | Apply di `20261021-21` … `-23` su scratch e dbdev, pgTAP verdi (2026-10-21). Verificato: changeSet `EXECUTED`, generatore agganciato, zero orfani, il trigger su `listini_associazioni` non c'è più | §9.6 | 11-bis |
| 11-quater | ✅ **BE** | Riprova (2026-10-21): 409 di dominio al posto del 500; spenti 10904 e 10905. 10906 e 10907 non si spengono: §9.8 | §9.7 | — |
| 11-quinquies | ✅ **Tid** | Un listino con storia si spegne solo con la fine validità (2026-10-21) | §9.8 | — |
| 11-sexies | ✅ **team DB** | `E_LISTINO_CON_STORIA_NON_SPEGNIBILE`, `vendite.fn_listino_ha_storia`, `valido_al` sempre sulla CHIUSA (2026-10-22) | §9.12 | — |
| 11-septies | ✅ **BE/FE** | `ha_storia` nel dettaglio del listino (letto dal DB); toggle solo senza storia, la nota altrimenti; `attivo` non inviato. Ripiego del codice scritto; la policy aspetta la riga 15 | §9.12 | — |
| 12 | ✅ **BE** | T-7b primo giro: il BB `_smoke_fatturazione.py`, quattro smoke verdi, giro 6 non-verdi su 51 | §9.9 | — |
| 12-bis | ✅ **team DB** | §9.10 corretto (l'emittente si confronta solo se passato); §9.9 `E_FATTURA_RIGA_IVA_MANCANTE` all'ingresso in EMESSA (2026-10-22) | §9.12 | — |
| 12-ter | ✅ **Tid + BE** | Seconda estrazione (ok Tid): la catena, contatore-note e push-termine verdi, 5 non-verdi su 51 | §9.9.1 | — |
| 12-quater | ✅ **BE** | ritorno-lotto verde; il test 9 di scadenze costruito (pipeline fino a DEFINITIVA); rls-emittente-operatore con `dev.emittente` e la sua materia; resi-vendita senza `utility_id`; `--update` della baseline: 2 noti su 51 | §9.12 | — |
| 12-quinquies | ✅ **team DB + BE** | group-attivita-contratto: R-1, R-2, Q-1 del DB, smoke verde (27 OK) | §9.11 | — |
| 12-sexies | ✅ **team DB + BE** | R-3: `fn_pgtap_crea_ordine(…, p_billing_account_id)`; push-termine sul builder, test Django sulla firma nuova | §9.12 | — |
| 14 | ✅ **team DB** | Push su git del giro del 2026-10-22 (#1920, già in `dev/backend-tid`) | §9.12 | — |
| 15 | ✅ **BE** | `genera_error_policies` coi due codici (CONFLITTO_STATO) e i due ripieghi senza `%s`; dalla API lo spegnimento di un listino con storia è 409 sul campo `attivo` | §9.12 | — |
| 16 | ✅ **Tid** | Collaudo a video superato (2026-10-22): drawer di un listino con storia (nota al posto del toggle) e senza (toggle) | §9.12 | — |
| 17 | ✅ **Tid** | Archiviazione in `work-done/` (2026-10-22) | — | — |

**Decisioni aperte di Tid: nessuna.** Domande aperte al team DB: nessuna.
✅ **Committato** su `dev/backend-tid` (`08cc15a61`, 2026-10-18; PR #1881): T-1 … T-4, T-6 e la 2b-2. Da committare: il §9 e le correzioni degli smoke del 2026-10-18 (§9.2); i due giri di T-7b del 2026-10-21 (§9.9, §9.9.1: `_smoke_fatturazione.py`, otto smoke convertiti, `smoke-lotto-capability-reset-fattura.py` e `smoke-test-preventivi-componenti.sh` allineati, catalogo BB); il §9.11 (group-attivita-contratto, policy e ripiego di `E_ATTIVITA_CONTRATTO_INCOERENTE`, contratti-addebito e listini-v5 senza `quantita`). Il §9.12 (2026-10-22): `error_policies_generated.py` ed `error_messages_fallback.py` (i due codici), `listini_repository.py`, `ListinoDrawer.vue`, le due lingue, `test_origine_ordine_sorgente_db.py`, gli smoke scadenze, push-termine, rls-emittente-operatore e resi-vendita, la baseline. **Da committare su `dev/db-tid`** (applicato): `20261021-21` … `-23`, il pgTAP `dbops/test-trigger-attivo-orfani-v1`, le due pagine `manual/` nuove, i manuali di `fn_run_automations_attivo` e `fn_trigger_argomenti`, la guida `automazione-db.md` e questo documento.

> **Chi scrive:** sessione BE (`dev/backend-tid`), 2026-10-16. **A chi:** il team BE/FE; la §6 al
> team DB.
> **Origine:** proposta di Tid (2026-10-15) di dare agli utenti degli smoke e dello sviluppo una
> nomenclatura standard, sul modello dei ruoli di sistema
> ([brief-db-ruoli-di-sistema](brief-db-ruoli-di-sistema.md) §1). Il modello è stato chiuso con
> il team DB in [brief-db-processi-accensione-per-ambiente](brief-db-processi-accensione-per-ambiente.md) §4-ter (R-2, R-4), decisioni di Tid del
> 2026-10-16.
> **Stato:** ✅ chiuso e archiviato il 2026-10-22: T-1 … T-7 fatti, e le risposte del team DB ai §9.5 – 9.11 applicate (§9.12).

## 1. La regola

ZeroERP fornisce un **insieme fisso di utenti di sviluppo**, creati da un solo verbo del database
che **rifiuta di partire in PRODUZIONE**. Servono a chi sviluppa e agli smoke; in un'installazione
di produzione non esistono, nemmeno disattivati.

* **Si riconoscono dall'etichetta, non dal nome.** Il prefisso `dev.` serve a leggerli nelle liste;
  la chiave è l'etichetta che il verbo mette mentre li crea. Un utente chiamato `dev.qualcosa` a mano
  dalla UI non è un utente di sviluppo; uno di sviluppo rinominato lo resta.
* **Le password e le chiavi del secondo fattore non hanno default.** Le genera il provisioning e
  finiscono in `backend/env.sh`, mai nel repo.
* **Si forniscono identità stabili, non stati.** Password scaduta, blocco per tentativi, invito in
  sospeso, disattivazione: li crea il test che li prova, altrimenti il primo giro li consuma.

### 1.1 Perché non `zeroerp_smoke`

La proposta di partenza era di chiamare l'utente degli smoke come i ruoli PostgreSQL. È stata
scartata (Tid, 2026-10-15):

* i ruoli PG hanno nomi fissi perché il database li **scrive per esteso** (grant, policy, presidi):
  sono schema. L'utente degli smoke è una riga di `auth_user` che nessun codice nomina (passa da
  `SMOKE_USER`);
* con lo stesso prefisso i due strati si confondono: nell'audit `user_insert = zeroerp_app` è il
  ruolo PG, `app.jwt_user` l'utente applicativo;
* il lato applicativo ha già la sua convenzione per gli utenti tecnici dei processi,
  `processo@azienda` (`script.fn_crea_utente_tecnico`, categoria SISTEMA). Gli utenti di sviluppo
  non sono utenti tecnici: sono **persone fittizie** con una veste, che entrano via HTTP.

## 2. Il modello (deciso, lato DB)

Fatti presi dalle risposte del team DB ([brief-db-processi-accensione-per-ambiente](brief-db-processi-accensione-per-ambiente.md) §4-ter, 2026-10-16).

| Pezzo | Com'è |
| --- | --- |
| **L'ambiente** | `SVILUPPO` o `PRODUZIONE`, letto da `fn_ambiente_installazione()`. **Immutabile** in tutte e due le direzioni: si scrive una volta, nella fase post di `provision_zeroerp.sql` (`-v ambiente=…`), e un guard rifiuta modifica e cancellazione. Nessun default: il changeSet crea la tabella vuota |
| **Prima della dichiarazione** | `fn_ambiente_installazione()` dà `E_CONFIG_MANCANTE`: il verbo di sviluppo non parte |
| **Una copia della produzione** | resta PRODUZIONE: niente utenti di sviluppo né smoke. Per una diagnosi si entra con un utente nominativo |
| **Il verbo di provisioning** | del DB; rifiuta in PRODUZIONE. Il command BE lo **chiama**, non scrive etichette per conto suo |
| **L'etichetta** | tabella satellite, una riga per credenziale; non si toglie; in PRODUZIONE un guard ne rifiuta la creazione |
| **Le radici etichettate** | ogni credenziale e ogni soggetto creato dal verbo: le persone fittizie, i clienti di prova dei portale, l'emittente di prova. Contratti, BA e documenti si ritrovano dalla radice |
| **La categoria** | invariata: `fn_categoria_accesso` resta SISTEMA / OPERATORE / ALTRO e non legge l'etichetta. Un `dev.lettura` resta OPERATORE, e `get_operatore` lo apre |
| **La lista Operatori** | il DB espone l'etichetta come colonna nella lettura che la lista usa già |
| **L'utente `smoke` di oggi** | non lo si adotta: si crea `dev.smoke` dal verbo, gli script passano a `dev.smoke`, poi `smoke` si **disattiva** (non si cancella: corse, documenti e log lo nominano) |

## 3. Che cosa aspettiamo dal giro DB

| Che cosa | Ci serve per |
| --- | --- |
| Nome e firma del verbo di provisioning; che cosa crea (credenziali, vesti, profili, soggetti, emittente, clienti) e che cosa restituisce | T-1 |
| Se il verbo crea anche il dispositivo del secondo fattore o lo lascia al BE | T-1 |
| La forma dell'etichetta e la colonna nella lettura della lista Operatori | T-4, T-6 |
| Codici errore nuovi (se ci sono): vanno nella policy generata **e** nel ripiego | T-1 |
| L'apply su dbdev e la dichiarazione di SVILUPPO | il collaudo |

## 4. Il lavoro BE/FE

| Lotto | Che cosa | Note |
| --- | --- | --- |
| **T-1** | Management command `provision_utenti_sviluppo`: chiama il verbo del DB (idempotente), configura il secondo fattore **già confermato** per chi lo deve avere (passando da `secondo_fattore_service`, non con una scrittura sua), genera le password, stampa le righe da mettere in `env.sh` | Legge l'ambiente **a ogni corsa** (niente cache di processo, è un command che gira una volta). Su `E_CONFIG_MANCANTE` o PRODUZIONE si ferma e dice perché: il rifiuto vero è del verbo, il command lo anticipa per un messaggio chiaro |
| **T-2** | Smoke bash: `SMOKE_USER=dev.smoke` in `env.sh`. ✅ **Anticipato il 2026-10-16** (non dipende dal DB): tolto il ripiego `tid` in `_smoke_auth.sh` e in `smoke-c9-fatturazione-parte-alta.py`; senza `SMOKE_USER` lo smoke si ferma e lo dice. Presidio `test_https_header` 16 (anche sugli smoke Python) e 18 (il caso dell'utente mancante) | Resta: `env.sh` a `dev.smoke`. Gli smoke RLS che oggi usano un utente preso a caso (`pochi`) passano a `dev.emittente` |
| **T-3** | Runbook [comandi-utili-run-book.md](../infra/comandi-utili-run-book.md) §11: «Ricrearlo» diventa una riga (il command); i 5 passi manuali escono | |
| **T-4** | Lista Operatori (BE): il parametro di filtro sull'etichetta, **lato server** (con la paginazione), attivo di default; la colonna nella risposta | Forma dal giro DB |
| **T-5** | Collaudo (Tid): provisioning da capo su dbdev, `smoke-test-core.sh` e il giro baseline con `dev.smoke`; poi disattivazione di `smoke` | La disattivazione la fa Tid |
| **T-6** | Lista Operatori (FE): filtro «nascondi utenti di prova» attivo di default, badge «di prova» sulle righe | |

### 4.1 Gli utenti

| Utente | Veste / profilo | Che cosa permette di provare |
| --- | --- | --- |
| `dev.smoke` | OPERATORE, SUPER_ADMIN globale, secondo fattore attivo, emittente attivo l'emittente di prova | quello che fa oggi `smoke` |
| `dev.lettura` | OPERATORE, LETTURA su tutte le aree | drawer in sola lettura, `Salva` nascosto, 403 sulle scritture |
| `dev.bloccato` | OPERATORE, un oggetto BLOCCATO (es. `vendite.contratto`) | `AccessoBloccatoPanel`, nessuna chiamata sotto il pannello |
| `dev.emittente` | OPERATORE, un solo emittente in whitelist | RLS: 404 sul dettaglio di un altro emittente |
| `dev.portale1` / `dev.portale2` | CLIENTE_PORTALE su due clienti di prova diversi | gli smoke portale e il controllo che un utente non veda i dati dell'altro: ne servono due |
| `dev.fornitore` | FORNITORE_PORTALE | smoke del portale fornitori |
| ~~`dev.shop`~~ | cliente B2C dello shop | il giro dello shop — **rinviato** (§7.4 D-B) |
| `dev.multiveste` | una credenziale con veste OPERATORE e CLIENTE_PORTALE | token multi-veste, invito su un'altra veste |

Secondo fattore: obbligatorio per `dev.smoke` (SUPER_ADMIN). Per gli altri profili lo si decide
utente per utente, e almeno uno lo deve avere spento: oggi nessuno smoke prova il login senza
secondo passo.

## 5. Vincoli per chi viene dopo

* **Una lettura dell'ambiente in una richiesta web non deve rompere il login.** Fra l'apply e la
  dichiarazione `fn_ambiente_installazione()` dà `E_CONFIG_MANCANTE`. Il command può (e deve)
  fermarsi; un endpoint come `/core/me/` no. Vale per gli usi possibili qui sotto.
* **Usi possibili dell'ambiente, non in questo brief:** gli smoke bash che si rifiutano su
  PRODUZIONE; un'indicazione «ambiente di sviluppo» nella barra in alto del FE.
* ⚠️ **Regola del 2.** La lettura dell'ambiente è la seconda lettura di un valore di sistema con una
  sua funzione DB, senza catena di override e senza ripiego (la prima è
  [fuso_aziendale.py](../../../../backend/apps/core/services/fuso_aziendale.py)). Le due letture
  hanno una differenza dichiarata: il fuso ha la cache di processo, l'ambiente no. L'estrazione di un
  BB comune **non** si fa di iniziativa: la si propone a Tid con T-1 sotto gli occhi.

## 6. Domande al team DB

* ✅ **D-1 — I command headless del backend sono «spegnibili»?** Sì, risposta dal giro 1
  ([brief DB §6.0](brief-db-processi-accensione-per-ambiente.md)): la sveglia systemd chiede al DB
  con un `ExecCondition` su `maintenance.fn_sveglia_accesa('<processo_codice>')`, «Esegui ora» legge
  la stessa funzione, `abilita` si ritira da `sveglie.json`. È lavoro BE, ma **non di questo brief**:
  sta nel §6 del brief DB, con gli altri sei punti del giro 1.

## 7. Che cosa crea il verbo — l'elenco per il giro 2

> Risponde al [brief DB §5-ter](brief-db-processi-accensione-per-ambiente.md): «serve dal BE
> l'elenco di che cosa crea». Fatti datati 2026-10-16, letti dalla doc `dbzero` e dal backend.

### 7.1 Le regole del verbo

* **Idempotente per chiave.** La chiave di ogni radice è il suo codice di prova (lo username per le
  credenziali, la sigla o un codice per i soggetti). Una seconda corsa non duplica: trova la radice
  etichettata e la **riallinea** (vesti accese, profili, whitelist, emittente attivo). Un'omonima
  **senza** etichetta (per esempio un `dev.smoke` creato a mano) è un errore, non un'adozione: solo
  il verbo mette l'etichetta.
* **Il profilo di sola lettura si riallinea a ogni corsa:** LETTURA su **tutte** le righe di
  `aree_funzionali` presenti in quel momento. Un'area nuova entra alla corsa successiva, senza
  toccare il verbo.
* **Le vesti nascono accese.** Niente giro dell'invito: `fn_crea_operatore_v2` le crea spente, il
  verbo le accende come fa oggi il builder pgTAP. L'invito si prova creando un utente apposta, non
  con questi (§1: identità stabili, non stati).
* **Password:** il verbo riceve l'**hash** per username, come `fn_crea_operatore_v2`
  (`p_password_hash`); l'hash Django lo calcola il command. Hash NULL = la password resta quella
  che c'è (una seconda corsa non cambia le password, se non lo si chiede).
* **Il secondo fattore lo fa il BE, dopo il verbo.** Il DB non verifica codici: riceve il segreto
  cifrato (`fn_totp_registra_device`) e il passo di un codice già verificato
  (`fn_totp_conferma_device`). Il command passa da `secondo_fattore_service`, come una persona dalla
  pagina Sicurezza. Il verbo non tocca il secondo fattore.
* **Restituisce** una riga per radice: tipo (credenziale / soggetto), chiave, id, `creata` o
  `riallineata`, e per le credenziali chi deve avere il secondo fattore. Il command la stampa.
* **Riusa i builder dove ci sono** (`dbops.fn_pgtap_crea_emittente`, `fn_pgtap_crea_cliente_ba`,
  `fn_pgtap_cf_libero`, `fn_pgtap_piva_libera`, …), o la loro logica: la scelta è del team DB. Il
  verbo però non è un builder pgTAP: vive dove vive un verbo, e il suo nome non dice `pgtap`.

### 7.2 I soggetti di prova (radici)

| Chiave | Che cos'è | Dati | Perché |
| --- | --- | --- | --- |
| emittente A | soggetto PG + ruolo emittente fiscale, con i registri che nascono da sé | ragione sociale «Emittente di prova A», P.IVA libera, valuta EUR, un magazzino predefinito | l'emittente attivo di `dev.smoke`; la whitelist di `dev.emittente`; i clienti di prova. Sigla: §7.4 D-A |
| emittente B | come A | «Emittente di prova B» | **il secondo serve**: `dev.emittente` deve ricevere 404 sul dettaglio di un dato di B. Con un emittente solo la prova RLS non ha niente da non vedere |
| cliente 1 | soggetto PG + cliente + BA su A | «Cliente di prova 1», P.IVA libera, stato attivo | la veste portale di `dev.portale1` e di `dev.multiveste` |
| cliente 2 | come 1 | «Cliente di prova 2» | la veste portale di `dev.portale2`: il controllo che il portale 1 non veda il 2 |
| cliente B | soggetto PG + cliente + BA su **B** | «Cliente di prova B» | il dato che `dev.emittente` non deve vedere |
| fornitore 1 | soggetto PG con ruolo fornitore | «Fornitore di prova 1» | la veste di `dev.fornitore` |
| le persone | un soggetto PF per credenziale | nome «Dev», cognome = la parte dopo `dev.` (es. «Dev Smoke»), CF libero | «una persona, una credenziale» (D-6) |

### 7.3 Le credenziali (radici)

| Username | Vesti | Profilo e permessi | Emittente | Secondo fattore |
| --- | --- | --- | --- | --- |
| `dev.smoke` | OPERATORE | SUPER_ADMIN (`p_is_super_admin`) | nessuna whitelist (admin globale); **emittente attivo** A | sì (obbligatorio) |
| `dev.lettura` | OPERATORE | profilo `DEV_LETTURA` (AD_HOC, legato all'identità): LETTURA su tutte le aree | whitelist A; attivo A | no |
| `dev.bloccato` | OPERATORE | profilo `DEV_LETTURA` + `user_override_oggetti` `vendite.contratto` = BLOCCATO | whitelist A; attivo A | no |
| `dev.emittente` | OPERATORE | profilo `DEV_OPERATIVO` (AD_HOC): TUTTO su tutte le aree | whitelist **solo A** (`fn_change_user_emittenti_scope`); attivo A | no |
| `dev.portale1` | CLIENTE_PORTALE su cliente 1 | `CLIENTE_PORTALE_STANDARD` (9001, dal ruolo) | — | no |
| `dev.portale2` | CLIENTE_PORTALE su cliente 2 | come sopra | — | no |
| `dev.fornitore` | FORNITORE_PORTALE su fornitore 1 | `FORNITORE_PORTALE_STANDARD` (9002) | — | no |
| `dev.multiveste` | OPERATORE + CLIENTE_PORTALE su cliente 1 | `DEV_LETTURA` sulla veste operatore; 9001 sul portale | whitelist A; attivo A | no |

* I due profili `DEV_*` sono **radici anche loro**? Sono configurazione, non soggetti né
  credenziali: il team DB dica se li etichetta o se li riconosce dal legame con le sole identità
  etichettate.
* Nessun profilo REPARTO o di sola lettura esiste nel seed (fatto del 2026-10-16): per questo il
  verbo li crea suoi, invece di appoggiarsi a un profilo dell'azienda.
* `dev.lettura` e `dev.bloccato` hanno il secondo fattore **spento** apposta: è il giro di login
  senza secondo passo che oggi nessuno smoke prova.

### 7.4 Decisioni di Tid

* ✅ **D-A — L'emittente di prova: nuovo dal verbo, o si adotta `EMITEST`?** **Deciso (Tid, 2026-10-16): due emittenti nuovi dal verbo, `EMITEST` non si adotta.** `EMITEST` (id 44) è nato
  a mano dalla UI e non ha l'etichetta, come `smoke`. Propongo **la stessa strada di `smoke`**: il
  verbo crea i suoi due emittenti (sigle per esempio `DEVA` e `DEVB`) ed `EMITEST` resta com'è, non
  più usato dagli smoke. Motivo di modello, non di comodità: su un'installazione di sviluppo nuova
  (CI, scratch) `EMITEST` non esiste, quindi il verbo deve saperlo creare da zero comunque; adottarlo
  su dbdev sarebbe un secondo percorso che vive solo lì. ⚠️ Effetto da sapere: gli smoke che
  contano su dati già presenti su `EMITEST` (listini, articoli, registri configurati a mano) li
  troveranno vuoti su A, e il collaudo T-5 lo farà vedere.
* ✅ **D-B — `dev.shop` adesso o dopo?** **Deciso (Tid, 2026-10-16): dopo, quando lo shop esiste.** L'app shop è uno stub (gli endpoint di registrazione
  rispondono 501, 2026-10-16). Propongo di **non crearlo ora**: le regole del §7.1 lo accolgono senza
  cambiare forma quando lo shop esiste (una riga in più nell'elenco del verbo).
* ✅ **D-C — I clienti dei portale hanno bisogno di un contratto?** **Deciso (Tid, 2026-10-16): cliente + BA, senza contratto.** Non esiste un builder di contratto.
  Un contratto serve solo se il portale lo mostra già; se no, cliente + BA bastano e il contratto
  entra quando entra la pagina del portale che lo legge. Propongo **cliente + BA, senza contratto**,
  salvo che tu sappia di una pagina del portale che li elenca già.

## 8. Fatto (sessione BE, 2026-10-18)

| Lotto | Che cosa | Dove |
| --- | --- | --- |
| codici | `E_DATI_DI_SVILUPPO_IN_PRODUZIONE`, `E_ETICHETTA_DI_PROVA_IMMUTABILE`, `E_RADICE_DI_PROVA_SENZA_ETICHETTA`: policy rigenerata e ripieghi senza `%s` | `error_policies_generated.py`, `error_messages_fallback.py` |
| T-1 | `manage.py provision_utenti_sviluppo [--nuove-password]`: legge l'ambiente a ogni corsa (non dichiarato o `PRODUZIONE` → si ferma e dice perché), chiama il verbo, genera la password per le credenziali appena create (per tutte con `--nuove-password`) e la passa al verbo come hash Django in una seconda chiamata nella stessa transazione, configura il secondo fattore già confermato di chi lo deve avere (`SecondoFattoreService.configura_confermato`, dentro il contesto della credenziale: il DB vuole che agisca lei), stampa le righe per `env.sh` (`SMOKE_*` per `dev.smoke`, `DEV_<NOME>_PASSWORD` per gli altri) | `anagrafiche/management/commands/provision_utenti_sviluppo.py`, `anagrafiche/db/dati_di_sviluppo_repository.py` |
| T-2 | i commenti degli smoke e di `smoke-baseline.sh` nominano `dev.smoke`; lo smoke RLS si lancia con `dev.emittente`. `env.sh` resta di Tid (riga 8) | `_smoke_auth.sh`, `smoke-test-rls-emittente-operatore.sh` |
| T-3 | run-book §11 riscritto: gli utenti di sviluppo, il command, le variabili | `comandi-utili-run-book.md` |
| T-4 | lista Operatori: colonna `di_prova` (`LEFT JOIN dbops.credenziali_di_prova`) e parametro `includi_di_prova` (strict; assente = nascosti), prima della paginazione e del conteggio | `amm_software_repository.list_operatori`, `OperatoriListView` (BE) |
| T-6 | interruttore «Mostra gli utenti di prova» dentro i filtri (acceso allarga, ed è ciò che il segno conta) e badge «Di prova» nella cella del ruolo | `OperatoriListView.vue`, store `operatori`, locales |

Prove: test sul DB vero `anagrafiche/tests/db/test_provisioning_sviluppo_db` (il command intero in una
transazione annullata: le password stampate aprono le credenziali, il secondo fattore di `dev.smoke` è attivo
con la chiave stampata, la lista nasconde e mostra) e `test_obblighi_e_secondo_fattore_db` 14; unitari del
command (8) e della view; backend `core` + `amm_software` + `anagrafiche` 2738 verdi, frontend 888, lint,
guard, mypy a cricchetto (sanati nello stesso giro due rilievi già in HEAD: `notify_listener` e
`processi_service`).

* **Regola del 2 sulla lettura dell'ambiente (§5): non estratta.** Il command la legge dal lettore che
  descrive (`fn_ambiente_dichiarato`, None se non dichiarato) per dire lui perché si ferma; il fuso usa il
  lettore che solleva, con la cache di processo. Due letture con un significato diverso, non due copie.
* ⚠️ L'emittente di prova A è vuoto: gli smoke che contavano su `EMITEST` lo diranno al collaudo.
* Il secondo fattore di `dev.smoke` si conferma sul passo **precedente** a quello di adesso: nessun codice è
  stato usato davvero, e così il primo login degli smoke, subito dopo, non trova il passo già preso
  (`E_TOTP_PASSO_GIA_USATO`).

## 9. Il collaudo T-5 (Tid + sessione BE, 2026-10-18)

Provisioning su dbdev, righe in `backend/env.sh`, `smoke-baseline.sh` con `dev.smoke`. Il login, il
secondo fattore, `core`, audit, JWT e il resto del perimetro sono verdi. 14 regressioni rispetto alla
baseline, in tre gruppi.

### 9.1 Le cause

| Gruppo | Smoke | Causa |
| --- | --- | --- |
| **A** | clienti, soggetti, contratti-addebito-standard | **non era il collaudo**: gunicorn servì il codice di prima della firma nuova di `anagrafiche.fn_crea_indirizzo_soggetto(uuid, jsonb)` (brief DB accensione §6.11): il master era partito alle 19:24, il repository era cambiato alle 20:29. Dopo `kill -HUP` clienti e soggetti verdi; contratti-addebito passa nel gruppo C |
| **B** | listini-v5 (e preventivi-componenti, già in baseline) | **difetto degli smoke**: prendevano «il primo emittente» della lista `/anagrafiche/emittenti-fiscali/`, che al super admin li mostra tutti. Il guard accetta solo l'emittente attivo (`fn_check_user_emittente_scope`, regola 2, vale anche per il super admin): `E_SCOPE_EMITTENTE` e `E_DOC_EMITTENTE_BA_INCOERENTE`. Verdi per sottrazione finché il primo della lista coincideva con l'attivo di `smoke` |
| **C** | gli altri | **l'emittente di prova A è vuoto** (§7.4 D-A, previsto): nessun modello di documento, nessuna mappa categoria → listino, nessun documento o attività da cui partire |

### 9.2 Corretto (sessione BE, 2026-10-18)

* `_smoke_cliente.sh`: `smoke_emittente_attivo` dà anche `EMITTENTE_ATTIVO_SR_ID` (da `/core/me/`,
  `emittente_attivo.soggetto_ruolo_id`; con `EMITTENTE_ID` di override lo legge dalla lista). Il BB
  esisteva: allargato, non estratto.
* `smoke-test-listini-v5.sh`, `smoke-test-preventivi-componenti.sh`: l'emittente è quello attivo, dal BB.
  Esito: listini-v5 arriva al passo 16 (17 OK, poi il modello del contratto), preventivi-componenti alla
  riga del composito (11 OK, poi la mappa categoria → listino).

### 9.3 Da fare: T-7

**Il difetto di fondo non è degli smoke.** Un emittente nuovo non sa emettere: è il
[brief-db-modelli-documento-standard](brief-db-modelli-documento-standard.md), e risolve da solo gli
smoke che si fermano sul modello. Il resto è materia che ogni smoke si deve costruire da sé, a partire
dalle radici di prova (§1: il verbo dà identità stabili, non dati di lavoro).

| Lotto | Smoke | Che cosa gli manca | Aspetta |
| --- | --- | --- | --- |
| — | preventivi, preventivi-smistamento-ordine, contratti-addebito-standard, listini-v5 (dal passo 16) | il modello di documento: nient'altro | brief modelli |
| **T-7a** | preventivi-componenti | il suo listino e la sua mappa categoria → listino (`SMOKE-*`, come listini-v5 crea la sua categoria) | — |
| **T-7a** | guida-inversione-preventivi | il seed cerca «l'ultimo preventivo visibile» per copiarne la terna: va preso dal cliente del lookup (`smoke_cliente_dal_lookup`) | — |
| **T-7b** | fattura-aggregazione-termini, fattura-indirizzi-snapshot, fattura-scadenze, fatturazione-aggregazione-righe, ritorno-lotto-a-draft | cercano un'attività fatturabile esistente da usare come stampo: se la devono costruire (contratto attivo → push) | brief modelli |
| **T-7b** | fattura-contatore-note | una fattura esistente | brief modelli |
| **T-7b** | push-termine-documento-commessa | un ordine esistente nel perimetro dell'emittente attivo | brief modelli |

⚠️ Niente `--update` della baseline prima della fine di T-7b: registrerebbe come noti dei rossi che hanno
una causa e una correzione.

### 9.4 T-7a fatto (sessione BE, 2026-10-18)

* **Regola del 2 (ok Tid):** `smoke_cliente_del_giro` in `_smoke_cliente.sh`, estratto da
  contratti-addebito (copia ritirata nello stesso giro), secondo consumatore preventivi-componenti.
  Registrato nel catalogo BB backend con l'allargamento di `smoke_emittente_attivo`.
* **preventivi-componenti** ✅ verde, due giri di fila. Materia **stabile**, cercata per codice e
  creata se manca (lo schema di `SMOKE-SERV-UT`): componente `SMOKE-COMP-COMPONENTE`, categoria
  `SMOKE-COMP`, listino `SMOKE-COMP-<emittente>-<utility>` con la riga del componente, mappa
  categoria → listino. **Del giro**: composito e BoM, cliente, preventivo. Tolti i due id di
  articolo scritti nello smoke. Corretti tre difetti nascosti, perché lo smoke non arrivava mai
  oltre il passo 5: il passo 8 mandava `origine_prezzo` (400: lo decide il server); la pulizia
  finale cancellava il preventivo con le righe (409) e spegneva l'articolo via PATCH (400). Ora la
  pulizia è una sola, per il fermo e per la fine.
  Il composito non ha una riga di listino sua (`E_LISTINO_RIGA_COMPOSITO_VIETATO`), e il componente
  non è «solo componente», perché quello non entra in un listino (`E_ARTICOLO_SOLO_COMPONENTE`).
* **guida-inversione-preventivi** ✅ verde: il seed prende la terna dal cliente del lookup e la
  valuta dai default del form, invece di cercare «l'ultimo preventivo visibile».
* **Trovato:** spegnere un listino risponde 500 → §9.5.

**Giro intero dopo T-7a** (2026-10-18 22:46): 9 non-verdi su 51 (erano 20). Restano:
contratti-addebito, preventivi, smistamento-ordine e listini-v5, fermi sul modello di documento
(brief modelli); push-termine, che ora arriva alla fattura e si ferma sul **registro fatture
mancante** di DEVA (`E_CONFIG_MANCANTE`, aggiunto al brief modelli §2); più i sei già in baseline.

⚠️ **I verdi degli smoke Python non sono di T-7a.** Nello stesso pomeriggio un'altra sessione ha
estratto `_smoke_contesto.py` (regola del 2, ok Tid): gli smoke Python aprivano il contesto RLS su
`config.user_emittenti_fiscali LIMIT 1`, cioè su un operatore a caso. Dopo il provisioning poteva
essere `dev.lettura`, che vede solo l'emittente di prova vuoto, e quindi la causa dei loro
SENZA_MATERIA al §9.1 era **anche** questa, non solo DEVA vuoto. Ora aprono il contesto su
`dev.smoke` senza emittente attivo, quindi con il perimetro largo del super admin, e trovano la
materia degli altri emittenti (EMITEST). Sono verdi, ma **contano ancora su dati esistenti**: su un
database nuovo tornano SENZA_MATERIA. T-7b resta per loro, e **niente `--update`** finché non è
chiuso.

### 9.5 Al team DB: un listino non si spegne (trovato da T-7a, 2026-10-18)

**Il caso.** `PATCH /api/v1/vendite/listini/<id>/` con `{"attivo": false}` risponde **500**
`E_ATTIVO_BLOCK_FKCOL_NOT_FOUND` «Colonna FK del figlio non trovata in catalogo». Succede con **ogni**
listino, con o senza figli: il guard scatta prima di guardare i figli. Dalla UI un listino non si
può spegnere.

**La causa** (doc `dbzero`). Su `vendite.listini` ci sono cinque trigger
`dbops.trgfn_prevent_deactivate_if_children`, uno per figlio. Uno è
`('vendite', 'listini_associazioni', 'listino_id', 'id', 'attivo')`, ma `vendite.listini_associazioni`
è stata eliminata il 2026-04-15 (`00_schema/vendite/20260415-05-drop-listini-associazioni-mctit.yaml`;
`to_regclass` NULL su dbdev). La funzione cerca la colonna FK nel catalogo, non la trova e solleva
l'errore. Gli altri quattro figli (`categorie_clienti_listini`, `contratti`, `listini_versioni`,
`offerte_commerciali`) esistono e hanno `listino_id`.

* **R-1** — togliere il trigger orfano. Proponiamo anche una regola: un `DROP TABLE` porta via,
  nello stesso changeSet, i guard dei padri che la nominano come figlia.
* **Q-1** — i guard `trgfn_prevent_deactivate_if_children` e `trgfn_child_requires_active_parent`
  nominano tabelle e colonne **per testo**: un rename o un drop non li aggiorna, e il difetto si
  vede solo quando qualcuno spegne il padre. Vi chiediamo se serve un presidio che verifichi, per
  ogni trigger di queste funzioni, che la tabella e la colonna nominate esistano.

**Ricaduta BE:** nessuna nel codice, perché il service passa l'errore del DB. La riprova è uno
spegnimento dalla API, oppure `listini-v5`, che oggi spegne i suoi `SMK-V5-*` con `dbshell`.
Su dbdev restano accesi quattro listini `SMK-COMP-<epoch>` dei giri di prova di T-7a, con le loro
categorie e una mappa: non pesano su nessun prezzo (ogni categoria è usata solo dal cliente del suo
giro) e si spengono dopo la correzione.

### 9.6 Risposta del team DB (sessione DB, 2026-10-21)

**R-1 — fatto, ma sul generatore e non sul solo trigger.** Era la seconda volta: a giugno lo stesso
difetto con `profili_reparto_*` (`20260610-01`, ripulito una tantum per nome). Chi genera i trigger ATTIVO
(`dbops.fn_run_automations_attivo`) adesso ritira anche quelli rimasti senza figlia, in testa a ogni giro,
accanto al ritiro delle eccezioni:

| ChangeSet | Che cosa |
| --- | --- |
| `20_code/dbops/20261021-21-create-fn-trigger-attivo-orfani` | il lettore unico: i trigger ATTIVO che nominano una tabella o una colonna che non esiste, con motivo e dettaglio |
| `20_code/dbops/20261021-22-create-fn-ritira-attivo-orfani` | il ritiro: toglie `TABELLA_ASSENTE` e `COLONNA_ASSENTE` |
| `20_code/dbops/20261021-23-update-fn-run-automations-attivo-ritira-orfani` | il generatore chiama il ritiro (corpo dalla doc auto-generata, verificato uguale al vivo) |

* ⛔ **Orfano = nome morto, non «FK assente».** Ci sono `require` scritti a mano su chiavi polimorfe,
  senza FK (`note_offerte_commerciali.target_riga_id`): sono legittimi e restano. Il lettore guarda le
  tabelle e le colonne che il corpo del trigger legge, con i default dei due corpi.
* Legge il catalogo per nome, non `information_schema`, che filtra per privilegio: il job vedrebbe
  «assente» una colonna valida.
* **Niente changeSet una tantum** (decisione di Tid, 2026-10-20: non c'è produzione). Su dbdev l'orfano
  dei listini sparisce al primo `automations_attivo` dopo l'apply, oppure con la `CALL` a mano. In CI
  non c'è mai stato: `ci_apply` gira dopo il DROP.
* **La regola proposta** («un DROP TABLE porta via i guard dei padri») **non si adotta** (Tid,
  2026-10-20): il generatore si rimette in ordine da solo, e una regola da ricordare è già stata
  dimenticata due volte.

**Q-1 — sì, per il framework ATTIVO:** `db/pgtap/dbops/test-trigger-attivo-orfani-v1.sql`. Si costruisce i
casi su tabelle TEMP (figlia eliminata, colonna FK eliminata, require polimorfo, trigger con argomenti
insufficienti) e prova lettore, ritiro e aggancio al generatore. Il test 3 è un **presidio** su ciò che
c'è: in CI è verde per costruzione, su dbdev è rosso finché il job non ripulisce. I trigger **scritti a
mano** di altre famiglie che nominano tabelle per testo (`componenti_*`, `note_validate_generic`,
`documento_interno_*`, …) restano fuori (Tid, 2026-10-20). Per controllarli servirebbe dichiarare, per ogni
funzione, che cosa significa ciascun argomento.

**Provato** (2026-10-21), con l'SQL estratto dagli YAML in transazione annullata:

* pgTAP 10/10 sullo scratch; su dbdev 9/10, con il solo test 3 rosso sull'orfano dei listini, come atteso;
* su dbdev lo spegnimento di `SMK-COMP-1792356043`: prima del ritiro `Colonna FK del figlio non trovata in
  catalogo`, dopo il ritiro il rifiuto giusto `E_ATTIVO_BLOCK_CHILDREN_ACTIVE` (il listino ha ancora una
  versione attiva in `vendite.listini_versioni`);
* `plpgsql_check` pulito, `dbops/test-riferimenti-morti-v1` 9/9, guardrail CI verdi.

**Applicato** (Tid, 2026-10-21 00:07) su scratch e dbdev, pgTAP verdi. Verifica della sessione DB sui
due database: i tre changeSet `EXECUTED`, `fn_run_automations_attivo` chiama il ritiro,
`dbops.fn_trigger_attivo_orfani()` vuota, `trg_listini_a10_listini_associazioni_block_deact_upd` sparito.

**Ricaduta BE:** nessuna nel codice. ⚠️ Nella riprova (11-quater) un listino con versioni attive
risponde col rifiuto di dominio «figli prima, padre poi»: si spengono prima le versioni, poi il listino.

### 9.7 La riprova 11-quater (sessione BE, 2026-10-21)

Dalla API, come `dev.smoke`, sui quattro `SMK-COMP-*` di dbdev.

| Listino | Versione | Esito |
| --- | --- | --- |
| 10904 | 20174 BOZZA, nessuna riga | listino spento subito → **409** `E_ATTIVO_BLOCK_CHILDREN_ACTIVE` (era 500); versione spenta, poi listino spento: **200** |
| 10905 | 20175 BOZZA, una riga attiva | riga, versione, listino spenti in quest'ordine: **200** ognuno |
| 10906 | 20176 **ATTIVA**, una riga, mappa categoria attiva | versione: **400** «In stato ATTIVA sono modificabili solo `valido_al`»; listino: 409 |
| 10907 | 20177 **ATTIVA**, una riga | come 10906 |

✅ **R-1 provato**: il 500 non c'è più, il rifiuto è quello di dominio.

### 9.8 Al team DB e a Tid: un listino che ha avuto una versione ATTIVA non si spegne più (trovato da 11-quater)

**Il caso.** La catena «figli prima, padre poi» è listino ← versioni ← righe
(`trgfn_prevent_deactivate_if_children`, doc `dbzero` di `vendite.listini` e `vendite.listini_versioni`).
Una versione ATTIVA o CHIUSA però è **immutabile**: non cambia `attivo`, e non lo cambiano le sue righe.
Il BE lo dice per primo (`_VERSIONE_PATCH_ALLOWED_BY_STATE`: in ATTIVA si cambia solo `valido_al`, in
CHIUSA niente), e sotto ci sono i guard di immutabilità delle righe. In più `commesse_attivita`, `contratti` e
`offerte_commerciali` puntano alla versione e non hanno `attivo`. Per il guard basta che esistano.
Risultato: **un listino che ha avuto anche una sola versione ATTIVA non si spegne in nessun modo**. Il toggle
«Attivo» del `ListinoDrawer` risponde sempre 409, e il rimedio che il messaggio suggerisce
(«disattivare le righe che puntano a questa») non si può eseguire.

Non è un difetto del BE, e il BE non lo aggira: aprire `attivo` sulle versioni ATTIVA aggirerebbe
l'immutabilità del modello. Va deciso che cosa significa **spegnere un listino che ha una storia**:

* **(a)** la storia non blocca: le versioni ATTIVA/CHIUSA non contano come «figli attivi» nel guard del
  listino, e il listino spento non è più proposto né risolto;
* **(b)** spegnere il listino chiude le sue versioni vive (`valido_al`, CHIUSA) in un verbo, e la storia
  resta com'è;
* **(c)** un listino usato non si spegne: si chiude la versione; lo spegnimento ha un suo rifiuto con un
  codice chiaro, e il FE nasconde il toggle quando c'è storia.

Domanda al team DB (Q-2): con (a) o (b), come si scrive il guard generico, che oggi conta solo `attivo`, per
un figlio che ha uno **stato** di storia?

✅ **Decisione di Tid (2026-10-21): un listino che ha una storia si spegne solo con una data di fine
validità.** Al più si usa «chiudi» (la versione CHIUSA), ma sempre con la sua fine validità. Il toggle
`attivo` non è la strada per un listino con storia; resta per quello che non ne ha (BOZZA, come 10904 e
10905). È la (c), con la fine validità come unico spegnimento.

**Al team DB**, da questa decisione:

* il rifiuto dello spegnimento di un listino con storia ha un **codice suo**, che dice di mettere la fine validità
  alla versione, invece di `E_ATTIVO_BLOCK_CHILDREN_ACTIVE` col rimedio «disattivare le righe», che non si
  può eseguire;
* una versione CHIUSA ha sempre `valido_al`: da verificare se il DB lo garantisce già
  (`trgfn_listini_versioni_guard_date_chiusa`), o se va chiuso;
* Q-2 cade: il guard generico non deve imparare lo stato di storia.

**Ricaduta BE/FE, dopo il DB:** il codice nuovo nella policy e nel ripiego; il drawer del listino mostra il
toggle solo a un listino senza storia, e per gli altri rimanda alla fine validità della versione.

**Su dbdev** restano accesi 10906 e 10907: si spengono con la fine validità delle loro versioni. Non pesano su nessun prezzo:
ogni categoria è usata solo dal cliente del suo giro.

### 9.9 T-7b, primo giro (sessione BE, 2026-10-21)

**Il BB (regola del 2, ok Tid):** `scripts/tests/_smoke_fatturazione.py`. `costruisci_base_fatturazione`
costruisce la base della fixture dalle radici di prova: emittente di prova, primo BA di un cliente di prova
legato a lui (riconosciuto dall'etichetta), articolo dal builder del DB con la sua IVA, commessa con termine
e modalità. Prima la base veniva da `ORDER BY a.id DESC LIMIT 1` sulle attività esistenti. Ritirate nello
stesso giro le cinque letture del template e le due copie identiche di `crea_commessa`
(`crea_commessa_di_prova`). In aggregazione-righe il secondo articolo del kit si costruisce
(`crea_articolo_di_prova`): prima veniva preso dal catalogo con `LIMIT 2`, e con lui se n'è andato il ramo
«SKIP 8-10». Registrato nel catalogo BB backend.

Fatto datato (2026-10-21): col contesto sull'emittente di prova le attività fatturabili visibili erano zero.
È la conferma che questi smoke vivevano dei dati di altri emittenti.

| Smoke | Esito |
| --- | --- |
| fattura-scadenze | ✅ verde, 9 OK. ⚠️ resta lo SKIP del test 9 (cerca «un lotto con sole fatture oltre EMESSA» fra i dati esistenti): da costruire, vedi sotto |
| fattura-aggregazione-termini | ✅ verde, 7 OK |
| fattura-indirizzi-snapshot | ✅ verde, 9 OK |
| fatturazione-aggregazione-righe | ✅ verde, 13 OK, kit compreso |
| ritorno-lotto-a-draft | ❌ rosso **sul modello**, §9.10. Resta rosso: è il presidio |
| fattura-contatore-note, push-termine-documento-commessa | ⏳ non toccati, vedi sotto |

**Giro intero** (2026-10-21 21:59, senza `--update`): **6 non-verdi su 51** (erano 9). Le regressioni sono due.
La prima è ritorno-lotto (§9.10). La seconda è `smoke-lotto-capability-reset-fattura.py`, rotto dal rename
`sort_by` → `order_by` di `list_lotto_fatture` (`5d6cb335c`, un altro brief) e mai lanciato dopo: allineato,
verde. È rientrato `smoke-fatturazione-render-stampa.py`.

**Resta di T-7b**, e vuole una seconda estrazione da proporre a Tid (regola del 2). La catena «lotto →
attività fatturabile lockata → righe → fattura» sta copiata, con varianti, in sei smoke: `crea_attivita` è
identica in scadenze e aggregazione-termini, e l'`INSERT INTO vendite.attivita_fatturabili` compare in tutti
e sei. contatore-note ha bisogno di **una fattura**, e il builder `dbops.fn_pgtap_crea_fattura` rifiuta
`dev.smoke`, che è super admin senza whitelist. push-termine ha bisogno di **un ordine** sul cliente di
prova: oggi clona con `INSERT` diretti «l'ultimo ordine visibile». Il test 9 di scadenze ha bisogno di un
lotto con fatture oltre EMESSA. Tutti e tre si costruiscono da quella catena.

#### 9.9.1 Secondo giro: la catena (sessione BE, 2026-10-21, regola del 2, ok Tid)

Nello stesso BB: `crea_lotto_di_prova`, `crea_attivita_lockata`, `crea_attivita_di_commessa`,
`crea_fattura_di_prova`. Ritirati: l'INSERT del lotto in sette smoke (nota-credito-resi compreso), l'INSERT
dell'attività in cinque, `crea_attivita` (identica in due). Resta dov'è l'attività di controllo di
push-termine, che ha un altro significato: non è lockata e sta fuori dal lotto.

| Smoke | Esito |
| --- | --- |
| fattura-contatore-note | ✅ verde, 6 OK: la fattura nasce dal generatore righe vivo (`crea_fattura_di_prova`) |
| push-termine-documento-commessa | ✅ verde, 8 OK: l'ordine nasce dal cliente di prova con un articolo merce costruito, al posto del clone dell'«ultimo ordine visibile» |
| fattura-scadenze, test 9 | ⏳ resta SKIP. «Oltre EMESSA» si raggiunge solo numerando il lotto (`numera_lotto`), che rilancia la pipeline col solo `lotto_id` e cade nel §9.10. Il motivo dello SKIP ora lo dice |
| nota-credito-resi | invariato (verde con due SKIP), lotto dal BB |
| preventivi-componenti | ✅ di nuovo verde. Era rosso per un altro brief: dal 2026-10-20 la creazione del preventivo rifiuta le chiavi fuori contratto, e lo smoke mandava una `data` che il service non aveva mai letto. Tolta |

**Giro intero** (2026-10-21, senza `--update`): **5 non-verdi su 51**. L'unica regressione è ritorno-lotto
(§9.10); gli altri quattro erano già in baseline (preventivi-componenti è rientrato dopo, con un giro mirato).
Rientrati, da togliere dalla baseline al `--update`: render-stampa e preventivi-componenti.

**Fuori da T-7b, trovato nel giro:** `smoke-group-attivita-contratto.py` apre il contesto su «un operatore
attivo qualunque» (`identita_digitali … LIMIT 1`, la stessa apertura che `_smoke_contesto.py` ha ritirato da
dieci smoke). Prende l'attività, il contratto e la fattura fra i dati esistenti. Per costruirli serve una
fixture di contratto, che non c'è: brief suo, o lotto T-7c.

**Trovato (al team DB): una riga di fattura senza IVA è un errore tecnico, non un rifiuto.** Un articolo
senza `iva_id`, su una fornitura senza tipo d'uso, passa la generazione delle righe con `iva_id` NULL: il
resolver dice `origine = 'ASSENTE'` e nessuno si ferma. Il giro si rompe dopo, nel riepilogo IVA, con
`E_PARAMETRO_INVALIDO` «p_iva_id obbligatorio e > 0» da `config.fn_get_aliquota_iva`. Il modello lo
ammette: `catalogo.articoli.iva_id` è nullable, e lo stadio A2 vale solo se c'è un tipo d'uso. Chi
emette deve sentirsi dire quale riga e quale articolo non hanno l'IVA, prima del riepilogo.

### 9.10 Al team DB: il rilancio di un lotto per id prende l'emittente predefinito, non quello del lotto (trovato da T-7b, 2026-10-21)

**Il caso.** Prendiamo un lotto MASSIVO di un emittente che non è il predefinito dell'installazione. Lo si
rilancia col solo `lotto_id` (il FE manda solo quello, sia per «Avanza» sia per il rilancio su ERRORE:
`runLottoPipeline`). Risposta: `Parametro non coerente con lotto esistente: emittente_soggetto_ruolo_id`. Il
lotto non va avanti dal drawer.

**La causa** (doc `dbzero`). `vendite.fn_get_or_create_lotto` chiama
`fn_resolve_lotto_utility_emittente` col BA NULL. Questa risolve `anagrafiche.fn_get_emittente_fiscale_id(NULL)`,
cioè l'emittente predefinito dell'installazione, e il ramo del lotto esistente confronta quell'emittente con
quello del lotto e solleva. Il ripiego sul predefinito ha senso per un lotto **nuovo** senza BA. Per un lotto
**esistente** l'emittente è il suo.

* Su dbdev il predefinito è `PGTAPEF202`, un emittente rimasto da un pgTAP (fatto del 2026-10-21): da
  ripulire, ma è un problema di dati a parte.
* Lo smoke era verde perché «l'ultima attività esistente» stava, per caso, su un lotto del predefinito.
  Ora il lotto è dell'emittente di prova, e il difetto si vede.

**Ricaduta BE:** nessun aggiramento (il runner potrebbe passare l'emittente del lotto, ma la regola è del
DB). `smoke-ritorno-lotto-a-draft.py` resta rosso finché il DB non la corregge.

### 9.11 La risposta del team DB a R-1, R-2 e Q-1, applicata (sessione BE, 2026-10-21)

Chiesto per `smoke-group-attivita-contratto.py` (§9.9.1). Il DB ha risposto nel merge #1918.

| Che cosa | Risposta del DB | Applicato nel BE |
| --- | --- | --- |
| **R-1** | `dbops.fn_pgtap_crea_contratto(p_etichetta, p_stato_codice_interno, p_billing_account_id)`: DRAFT, ATTIVO (con un listino del mondo), ANNULLATO. Il BA dev'essere della stessa azienda di chi agisce | group-attivita-contratto costruisce il contratto ATTIVO sul BA della base |
| **R-2** | i builder leggono l'emittente da `app.current_emittente_id` quando chi agisce è un super admin | contatore-note e group-attivita-contratto prendono la fattura da `fn_pgtap_crea_fattura`. Ritirato `crea_fattura_di_prova` del BB: «una fattura» ha una sede sola, il builder del DB |
| **Q-1** | `contratto_id` (su `commesse_attivita` e `attivita_fatturabili`) è un contratto del BA della commessa, altrimenti `E_ATTIVITA_CONTRATTO_INCOERENTE` (TECNICO) | policy rigenerata (con lei entrano `E_DOC_RIGA_NON_AMMESSA` ed `E_OFFERTA_ANNULLO_CON_DOCUMENTI_VIVI`, già in git); ripiego senza `%s`. Il contratto dello smoke è del BA della commessa delle attività |

**group-attivita-contratto** ✅ verde, 27 OK, tutto costruito: contesto `apri_contesto_smoke`, base, lotto, tre
attività su tre articoli (servono ai test 8-10), contratto e fattura dai builder. Restano fuori dal costruito solo
i cataloghi (stati, nature, UoM). La riga 12-quinquies è chiusa.

**Giro intero** (2026-10-21, senza `--update`): l'unica regressione resta ritorno-lotto (§9.10). Nel giro sono
emerse due regressioni di altri lavori, ora allineate. contratti-addebito-standard e listini-v5 mandavano
`quantita` nella riga di contratto, che ora la rifiuta (modifica in corso, non committata, di
`contratti_service.py`): la calcola il DB da `qta_operativa`, quindi è stata tolta. Tutti e due verdi, e
listini-v5 per intero (prima si fermava al passo 16 sul modello di documento).

**R-3, al team DB (nessuna fretta).** `push-termine-documento-commessa` scrive ancora l'ordine con un INSERT del
BE. `dbops.fn_pgtap_crea_ordine(p_etichetta, p_stato)` crea un mondo nuovo a ogni chiamata, e il test 2 vuole
**due ordini dello stesso cliente**. Vi chiediamo un `p_billing_account_id` facoltativo, come su fattura e
contratto. Termine e modalità li scrive lo smoke in bozza. Con quello l'INSERT si ritira.

### 9.12 La risposta del team DB ai §9.8 – 9.11, applicata (sessione BE, 2026-10-22)

Il DB è in git col #1920. La policy dei due codici è rigenerata (righe 14-15), e lo spegnimento di un listino con
storia risponde 409 sul campo `attivo`.

| Punto | Risposta del DB | Nel BE/FE |
| --- | --- | --- |
| **§9.10** lotto | un lotto esistente si rilancia col solo `lotto_id`: l'emittente si confronta solo se passato. `PGTAPEF202` è l'emittente di prova voluto (Tid), non un residuo | nessun codice. ritorno-lotto ✅ verde. Il test 9 di scadenze ora si **costruisce**: attività marcata col giro su una competenza isolata, e `run_lotto_pipeline_until_done` che crea il lotto, emette e numera fino a DEFINITIVA (9a è la sua precondizione). Niente più SKIP |
| **§9.8** listino | `E_LISTINO_CON_STORIA_NON_SPEGNIBILE` (CONFLITTO_STATO, campo `attivo`); il toggle segue `vendite.fn_listino_ha_storia(listino_id)`; una CHIUSA ha sempre `valido_al` | `listini_repository.get_listino` porta `ha_storia` letto dalla funzione (la regola non è ricopiata in Python). `ListinoDrawer`: il toggle solo senza storia, altrimenti la nota `vendite.listini.attivo_con_storia`, e il salvataggio non manda `attivo`. Provato dalla API: 10904 `ha_storia=false`, 10906 `true`, lo spegnimento di 10906 rifiutato col codice nuovo |
| **§9.9** IVA | la bozza con una riga senza IVA si salva; entrando in EMESSA `E_FATTURA_RIGA_IVA_MANCANTE` (CONFLITTO_STATO), riga e descrizione nel messaggio | nessun codice oltre la policy (riga 15). Il BB degli smoke dà comunque l'IVA all'articolo di prova: la fattura deve emettere |
| **R-3** ordine | `dbops.fn_pgtap_crea_ordine(etichetta, stato, billing_account_id)` | push-termine prende l'ordine dal builder sul BA della base (data, termine e modalità in bozza): ✅ verde, l'INSERT è ritirato. `test_origine_ordine_sorgente_db` sulla firma nuova, verde col DB vero |

**Gli altri due noti, sistemati nello stesso giro:**

* `smoke-test-rls-emittente-operatore.sh` girava come `dev.smoke`, senza whitelist, quindi era sempre «non
  conclusivo». Ora gira come `dev.emittente` (password da `env.sh`). Un setup in-process come `dev.smoke`
  assicura, col builder del DB, un contratto sull'emittente in whitelist e uno sull'altro emittente di prova:
  materia stabile, cercata e creata se manca. Le chiamate HTTP restano di sola lettura. ✅ verde, il 404
  compreso (prima voleva un id passato a mano);
* `smoke-test-resi-vendita.sh`: la creazione dell'ordine rifiuta `utility_id` (contratto della creazione, la
  dà il BA). Tolto: 55 OK. Restano 2 FAIL del dominio dei resi (`can_edit_righe` in DRAFT, coda accrediti),
  che c'erano già e non sono di questo brief.

**Giro intero con `--update`** (2026-10-22 17:52): **2 non-verdi su 51**, nota-credito-resi (SENZA_MATERIA: kit e
seconda riga in coda) e resi-vendita (i 2 FAIL sopra), tutti e due fuori perimetro. Il registro è sceso da 5 a 2.
Test: backend `vendite` sui listini e sul builder dell'ordine (DB vero), `test_https_header`, frontend 958 su 958.

