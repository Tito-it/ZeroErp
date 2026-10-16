# Brief BE — Gli utenti di sviluppo: forniti da un verbo, etichettati, mai in produzione

## ⏭️ Chi riparte — aggiornato al 2026-10-16

**Riparte: il team DB col giro 2 del
[brief-db-processi-accensione-per-ambiente](brief-db-processi-accensione-per-ambiente.md) (§5-ter),
che aspettava l'elenco del §7 (decisioni del §7.4 prese). Il BE scrive T-1 quando il giro 2 è applicato.**

| # | Chi | Che cosa | Dove | Aspetta |
| --- | --- | --- | --- | --- |
| 1 | ✅ **Tid + team DB** | Il modello: ambiente immutabile, etichetta sulle radici, verbo che rifiuta in PRODUZIONE | §2 | — |
| 2 | ✅ **team DB** | Giro 1 applicato su dbdev (`SVILUPPO` dichiarato, 2026-10-16 14:20): ambiente e accensione dei processi. Risponde anche a D-1 (§6) | brief DB §5-bis | — |
| 3 | ✅ **BE** | L'elenco di che cosa crea il verbo, chiesto dal brief DB §5-ter | §7 | — |
| 4 | ✅ **Tid** | Le tre decisioni del §7.4: emittenti nuovi dal verbo, `dev.shop` dopo, portale senza contratto (2026-10-16) | §7.4 | — |
| 5 | **team DB** | Giro 2: etichette, verbo del provisioning di sviluppo, presidio, colonna nella lista Operatori | brief DB §5-ter | 4 |
| 6 | **Tid** | Apply del giro 2 su dbdev | — | 5 |
| 7 | **BE** | T-1 … T-4 (di T-2 è già fatto il ritiro del ripiego `tid`) | §4 | 6 |
| 8 | **Tid** | Collaudo: il provisioning da capo su dbdev, il giro degli smoke con `dev.smoke`, poi la disattivazione di `smoke` | §4, T-5 | 7 |
| 9 | **FE** | T-6: il filtro e il badge nella lista Operatori | §4 | 7 |

**Decisioni aperte di Tid: nessuna** (§7.4 deciso il 2026-10-16). Domande aperte al team DB: nessuna (D-1 risposta dal giro 1).

> **Chi scrive:** sessione BE (`dev/backend-tid`), 2026-10-16. **A chi:** il team BE/FE; la §6 al
> team DB.
> **Origine:** proposta di Tid (2026-10-15) di dare agli utenti degli smoke e dello sviluppo una
> nomenclatura standard, sul modello dei ruoli di sistema
> ([brief-db-ruoli-di-sistema](brief-db-ruoli-di-sistema.md) §1). Il modello è stato chiuso con
> il team DB in [brief-db-processi-accensione-per-ambiente](brief-db-processi-accensione-per-ambiente.md) §4-ter (R-2, R-4), decisioni di Tid del
> 2026-10-16.
> **Stato:** 📝 elenco per il giro 2 consegnato e deciso (§7); in attesa del giro 2 DB.

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
