# Brief BE — Gli utenti di sviluppo: forniti da un verbo, etichettati, mai in produzione

## ⏭️ Chi riparte — aggiornato al 2026-10-16

**Riparte: il team DB col giro di `brief-db-processi-accensione-per-ambiente` (§5), poi Tid con
l'apply e la dichiarazione di SVILUPPO su dbdev. Il BE aspetta: nessuna riga di codice prima.**

| # | Chi | Che cosa | Dove | Aspetta |
| --- | --- | --- | --- | --- |
| 1 | ✅ **Tid + team DB** | Il modello: ambiente immutabile, etichetta sulle radici, verbo che rifiuta in PRODUZIONE | §2 | — |
| 2 | **team DB** | Risposta alla domanda D-1 (i command headless del backend sono «spegnibili»?) | §6 | niente |
| 3 | **team DB** | Il giro DB: nome del verbo di provisioning, forma dell'etichetta, colonna nella lettura della lista Operatori | §3 | — |
| 4 | **Tid** | Apply su dbdev e fase post di `provision_zeroerp.sql` con `-v ambiente=SVILUPPO` | §3 | 3 |
| 5 | **BE** | T-1 … T-4 (di T-2 è già fatto il ritiro del ripiego `tid`) | §4 | 4 |
| 6 | **Tid** | Collaudo: il provisioning da capo su dbdev, il giro degli smoke con `dev.smoke`, poi la disattivazione di `smoke` | §4, T-5 | 5 |
| 7 | **FE** | T-6: il filtro e il badge nella lista Operatori | §4 | 5 |

**Decisioni aperte di Tid: nessuna.** Domande aperte al team DB: D-1 (§6).

> **Chi scrive:** sessione BE (`dev/backend-tid`), 2026-10-16. **A chi:** il team BE/FE; la §6 al
> team DB.
> **Origine:** proposta di Tid (2026-10-15) di dare agli utenti degli smoke e dello sviluppo una
> nomenclatura standard, sul modello dei ruoli di sistema
> ([brief-db-ruoli-di-sistema](brief-db-ruoli-di-sistema.md) §1). Il modello è stato chiuso con
> il team DB in `brief-db-processi-accensione-per-ambiente` §4-ter (R-2, R-4), decisioni di Tid del
> 2026-10-16.
> **Stato:** ⏸️ in attesa del giro DB.

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

Fatti presi dalle risposte del team DB (`brief-db-processi-accensione-per-ambiente` §4-ter, 2026-10-16).

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
| `dev.shop` | cliente B2C dello shop | il giro dello shop |
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

* **D-1 — I command headless del backend sono «spegnibili»?** Il brief DB parla di accensione dei
  processi per ambiente e di «job spegnibili». Se il perimetro comprende anche i command lanciati da
  cron o systemd (`send_pending_emails`, `run_fatturazione_batch`, `smoke_notturno`, … quelli che
  passano da `registered_job`) e non solo i job pgAgent, è lavoro BE (leggere l'ambiente in
  `registered_job` o nel singolo command) e va scritto nel brief DB come ricaduta sul BE, con quali
  command e quale comportamento in ciascun ambiente.
