# Brief BE — Gli utenti di sviluppo: forniti da un verbo, etichettati, mai in produzione

## ⏭️ Chi riparte — aggiornato al 2026-10-18

**Riparte: Tid, con le decisioni del [brief-db-modelli-documento-standard](brief-db-modelli-documento-standard.md) §5; il team DB, col listino che non si spegne (§9.5). T-7a è fatto (§9.4); T-7b aspetta i modelli.** Il collaudo T-5 è fatto (2026-10-18, §9): provisioning, `env.sh` e login con
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
| 10 | **Tid → team DB** | I modelli di documento standard: un emittente nuovo emette dal primo giorno | [brief-db-modelli-documento-standard](brief-db-modelli-documento-standard.md) | — |
| 11 | ✅ **BE** | T-7a (2026-10-18): preventivi-componenti e guida-inversione si costruiscono la materia; trovato il listino che non si spegne | §9.4 | — |
| 11-bis | **team DB** | Il guard di disattivazione del listino punta a una tabella eliminata: 500 a ogni spegnimento (R-1, Q-1) | §9.5 | — |
| 12 | **BE** | T-7b: gli smoke che hanno bisogno di un documento emesso; il giro intero con `--update` della baseline | §9.3 | 10 |
| 13 | **Tid** | Archiviazione in `work-done/` | — | 12 |

**Decisioni aperte di Tid: nessuna qui** (§7.4 deciso il 2026-10-16); D-1 … D-3 stanno nel brief dei modelli standard. Domande aperte al team DB: nessuna (D-1 risposta dal giro 1).
✅ **Committato** su `dev/backend-tid` (`08cc15a61`, 2026-10-18; PR #1881): T-1 … T-4, T-6 e la 2b-2. Da committare: il §9 e le correzioni degli smoke del 2026-10-18 (§9.2).

> **Chi scrive:** sessione BE (`dev/backend-tid`), 2026-10-16. **A chi:** il team BE/FE; la §6 al
> team DB.
> **Origine:** proposta di Tid (2026-10-15) di dare agli utenti degli smoke e dello sviluppo una
> nomenclatura standard, sul modello dei ruoli di sistema
> ([brief-db-ruoli-di-sistema](brief-db-ruoli-di-sistema.md) §1). Il modello è stato chiuso con
> il team DB in [brief-db-processi-accensione-per-ambiente](../work-done/brief-db-processi-accensione-per-ambiente.md) §4-ter (R-2, R-4), decisioni di Tid del
> 2026-10-16.
> **Stato:** ✅ T-1 … T-6 fatti (2026-10-18); 🔨 T-7, gli smoke senza i dati di `EMITEST` (§9).

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

Fatti presi dalle risposte del team DB ([brief-db-processi-accensione-per-ambiente](../work-done/brief-db-processi-accensione-per-ambiente.md) §4-ter, 2026-10-16).

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
  ([brief DB §6.0](../work-done/brief-db-processi-accensione-per-ambiente.md)): la sveglia systemd chiede al DB
  con un `ExecCondition` su `maintenance.fn_sveglia_accesa('<processo_codice>')`, «Esegui ora» legge
  la stessa funzione, `abilita` si ritira da `sveglie.json`. È lavoro BE, ma **non di questo brief**:
  sta nel §6 del brief DB, con gli altri sei punti del giro 1.

## 7. Che cosa crea il verbo — l'elenco per il giro 2

> Risponde al [brief DB §5-ter](../work-done/brief-db-processi-accensione-per-ambiente.md): «serve dal BE
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

