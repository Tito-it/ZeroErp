# Brief BE/FE — Accessi: la veste revocata e il collaudo delle sessioni per veste

## ⏭️ Chi riparte — aggiornato al 2026-11-26

**Riparte: Tid**, col collaudo a video (§2). D-4 e A-6 sono fatti lato BE/FE il 2026-11-26 (il passo 3b del
[brief DB unico](brief-db-accessi-area-clienti.md) §4.1), da committare.

| # | Chi | Che cosa | Dove | Aspetta |
| --- | --- | --- | --- | --- |
| 0 | Tid | ~~D-R1 … D-R5~~ decise il 2026-11-25 | §1.3 | — |
| 1 | ~~sessione DB~~ | ~~R-4 a DB: il segno, il guard, i verbi~~ costruito il 2026-11-25, applicato il 2026-11-26 (brief DB §2) | brief DB §2 | 0 |
| 2 | ~~team BE/FE~~ | ~~D-4 e A-6 sulla regola consegnata dal DB~~ fatti il 2026-11-26, da committare: «Disabilita» e «Disattiva» revocano, il nuovo invito toglie il segno, il pulsante «Attiva shop» su una veste revocata si ferma con `E_VESTE_REVOCATA` (brief DB §4.1) | brief DB §4.1 | — |
| 3 | Tid | Il collaudo a video di D-5 | §2 | — |
| 4 | team BE/FE | Archiviazione in `work-done/` | §3 | 2, 3 |
| 5 | team BE/FE | Il contesto dei test sul DB vero per la sola transazione: il BB `apri_contesto_su` e i ~30 file che chiamano `script.fn_pgtap_set_contesto_operatore` | §4 | `/arrivi-db` del giro 10-bis |

**Decisioni aperte di Tid:** nessuna in questo brief (D-R1, D-R2, D-R4, D-R5 decise il 2026-11-25, §1.3). La forma della marca
«revocata» la sceglie il DB nel suo brief. La registrazione da sé (D-R3, D-R6 e le decisioni R-1 … R-3 del
2026-11-25) non sta qui: sta in [sviluppo-multi-face-da-completare](sviluppo-multi-face-da-completare.md) §3.6.

> **Chi scrive:** sessione BE (`dev/backend-tid`), 2026-11-25. **A chi:** team BE/FE, Tid; la sessione DB per il
> prerequisito di §1.1.
> **Origine:** il residuo del
> [piano BE/FE accessi](../work-done/2026/piano-be-fe-accessi-credenziale-e-vesti.md), archiviato lo stesso giorno
> dopo la riverifica sul codice: L-0, L-1, L-2, L-3, L-4, L-6, D-3 e D-5 lato codice sono chiusi; restano R-4 (cioè
> D-4 e A-6) e il collaudo a video di D-5. Il **perché** di ogni sigla sta nel piano e
> nell'[analisi](../work-done/2026/analisi-accessi-credenziale-e-vesti.md): qui solo cosa resta.
> **Brief vicini verificati:** [brief-db-revisione-anagrafiche](brief-db-revisione-anagrafiche.md) §17.1 (Tid,
> 2026-11-23) manda il tema T9, gli accessi, in un brief DB nuovo «con R-4 del piano accessi», insieme a S64
> (`fn_stato_veste`: `ATTIVO` vuol dire «accesa» o «utilizzabile») e S67 (la veste dello shop nasce accesa o spenta),
> che è la stessa materia di R-4. Al 2026-11-25 quel brief non è ancora scritto.

---

## 1. R-4 — La revoca dell'admin che tiene (D-4, A-6)

### 1.1 La richiesta al DB

La veste ricorda di essere stata **revocata dall'amministratore** (chi, quando), e la riattivazione self-service la
rifiuta. La regola sta a DB, non nel BE (piano §5 R-4). Va nel brief DB degli accessi (T9), insieme a S67: se la
veste dello shop nasce spenta e si accende da sé, «spenta dalla persona» e «spenta dall'admin» devono distinguersi.

**Stato verificato sul codice il 2026-11-25:**

- `anagrafiche.identita_digitali` ha `attivo`, `valido_dal`, `valido_al`, `invito_inviato_at`, `meta`: nessuna
  colonna dice che la veste è stata revocata, da chi e quando;
- [ProfileActivateShopView](../../../../backend/apps/portale/api/views.py#L69) (`POST portale/profile/activate-shop/`)
  controlla solo che chi chiama sia `CLIENTE_PORTALE`: un cliente a cui l'admin ha spento la veste shop se la
  riaccende con un clic. È il difetto **A-6**.

### 1.2 Il lavoro BE/FE, quando il DB consegna

Dal piano, §4.3 riga «Revoca (D-4)»:

- disattivare **dall'admin** marca la veste come revocata, con la funzione che il DB consegna;
- `ProfileActivateShopView` rifiuta una veste revocata, col codice del DB (policy generata e ripiego);
- FE: [AttivaAccessoShopButton](../../../../frontend/src/portale/components/AttivaAccessoShopButton.vue) spento col
  motivo, [PortaleAccessoPanel](../../../../frontend/src/portale/components/PortaleAccessoPanel.vue) mostra «revocato»;
- test sul DB vero: l'admin spegne la veste shop → l'attivazione self-service è rifiutata; ~~la persona che se la
  spegne da sé la riaccende~~ ⚠️ il caso non si costruisce: oggi nessuna strada lascia alla persona spegnere la sua
  veste (§1.3). Al suo posto: revocata → nuovo invito dell'admin → il link accende; mai attivata → il pulsante accende.

### 1.3 Analisi critica (sessione DB, 2026-11-25)

Fatti verificati sul codice (lettura del backend fatta dalla sessione DB, solo per verificare il brief):

- **Il pulsante e l'invito accendono con lo stesso verbo.** `ProfileActivateShopView` riaccende la veste esistente
  con `AuthRepository.attiva_identita`, cioè `anagrafiche.fn_accendi_veste`: la stessa funzione del link
  dell'invito. Il DB non sa chi la chiama, quindi «il self-service rifiuta» non si scrive a DB senza un parametro o
  un secondo verbo.
- **Il nuovo invito riusa la riga revocata** (`InvitoPortaleService._ensure_identita` la lascia spenta e la
  accenderà il token).
- **La persona oggi non spegne la sua veste da sola**: l'unica strada è `_disattiva_veste_common`, dell'admin.
- **R-BE6, seconda domanda, confermata**: `PortaleRepository.disattiva_identita` spegne con un `UPDATE` scritto a
  mano. Una veste spenta da un `UPDATE` diretto non porterebbe il segno, e il pulsante la riaccenderebbe.
- **Più vesti spente per la stessa coppia** (ruolo anagrafico, veste) sono ammesse: l'indice unico vale per le
  accese, e `find_identita_portale` prende l'id più alto. Il brief DB dice se il segno vale per la riga o per la
  coppia.
- Lo stato «revocata» va **letto** dal DB per il pulsante e per il pannello: il posto naturale è
  `script.fn_stato_veste`, con uno stato `REVOCATA` (S64, che T9 decide).

La proposta sul modello: un segno esplicito sulla riga (chi, quando) con un `CHECK` «revocata ⇒ spenta»; un guard
della tabella che rifiuta l'accensione finché la veste è revocata (copre `fn_accendi_veste` e ogni `UPDATE`); il
**nuovo invito dell'admin toglie il segno**, nella transazione dell'emissione, così nessun verbo deve riconoscere il
chiamante; lo spegnimento dell'admin passa da un verbo DB, e le due strade BE lasciano l'`UPDATE` a mano.

| # | Decisione | Esito |
| --- | --- | --- |
| D-R1 | Il segno lo toglie il nuovo invito, e il blocco sta in un guard della tabella | ✅ **Tid, 2026-11-25: sì** |
| D-R2 | Vale per tutte le vesti, operatore compreso: porta a DB la D-3 («si riattiva col reinvio») | ✅ **Tid, 2026-11-25: sì** |
| D-R4 | L'app perde la scrittura diretta di `identita_digitali.attivo` (solo dai verbi): senza, il segno ha un buco | ✅ **Tid, 2026-11-25: sì** (nello stesso giro o subito dopo: lo dice il brief DB; con la sezione «Garanzie ritirate» e il censimento dei lettori al BE) |
| D-R5 | R-4 è il primo giro del brief DB, con S64, S67 e R-BE6; S59-S63 vengono dopo, così il BE non aspetta tutto T9 | ✅ **Tid, 2026-11-25: sì.** Il brief DB è unico con il modello dell'area clienti ([analisi-modello-area-clienti](analisi-modello-area-clienti.md) §8) |

D-R3 (il pulsante accende subito o chiede l'email) e D-R6 (la veste shop sta sul ruolo privato della persona, non
sull'azienda) sono della registrazione da sé: [sviluppo-multi-face-da-completare](sviluppo-multi-face-da-completare.md)
§3.6. R-4 non le aspetta: la revoca regge in tutti e due i casi, e anche contro la reiscrizione.

⚠️ **2026-11-25, dopo:** Tid ha deciso una sola porta clienti
([analisi-modello-area-clienti](analisi-modello-area-clienti.md)). D-R3 e D-R6 sono assorbite: il pulsante «Attiva
shop» si **ritira**, quindi **A-6 si chiude per ritiro** e non con un rifiuto in `ProfileActivateShopView`; il lavoro
BE/FE del §1.2 sul pulsante e sul pannello va riletto su quel modello. **R-4 resta**, sulla veste cliente unica e
sull'iscrizione da sé; D-R1, D-R2, D-R4, D-R5 decise da Tid lo stesso giorno (tabella sopra).

### 1.4 Riverifica critica (sessione DB, 2026-11-25)

Rilettura del §1.3 sul catalogo dello scratch e sul codice, a decisioni prese. Le decisioni reggono; cinque punti
della proposta no, così come sono scritti, e il brief DB li deve chiudere.

1. **Riga o coppia non è un dettaglio: decide se la revoca tiene.** Un guard che rifiuta solo l'*accensione* di una
   riga revocata non ferma una **riga nuova**: `attivo` nasce `true` di default, più vesti spente per la stessa
   coppia sono ammesse, e l'iscrizione da sé, l'invito (`_ensure_identita`) e `fn_crea_veste_portale` possono
   inserirne una. Il guard deve coprire anche l'`INSERT`, e la revoca vale per la coppia (credenziale, ruolo
   anagrafico, veste), che col modello nuovo è la chiave dell'indice «per credenziale e soggetto». Da dire anche:
   la revoca è della **credenziale**; un'altra persona dello stesso cliente (D-M7) non ne è toccata.
2. **«Nessun verbo deve riconoscere il chiamante» non regge.** Il token dell'invito lo scrive il BE
   (`TokenRepository`, `INSERT` diretto su `config.token_monouso`): il segno lo toglie quindi un verbo DB che il BE
   chiama nella stessa transazione. Quel verbo lo può chiamare `zeroerp_app` da qualunque strada, anche
   dall'iscrizione da sé, che emette anch'essa un token. Deve controllare **il permesso di chi agisce**, dalle GUC
   della sessione ([contratto-guc-app](../../guide/contratto-guc-app.md)), non da un parametro. D-R1 resta: cambia
   il perché.
3. **D-R4 ha tre buchi in più.** Oggi `zeroerp_app` ha `INSERT`, `UPDATE` su tutte le colonne e `DELETE` sulla
   tabella. Oltre ad `attivo`, l'app non deve poter scrivere **le colonne del segno** (altrimenti lo toglie con un
   `UPDATE`) né **cancellare** una veste revocata (la cancella, e l'iscrizione ne rifà una pulita). Il `DELETE` il BE
   non lo usa (il model è `managed=False` e in sola lettura), ma il grant c'è. Il ritiro si fa dal loop dei grant
   (linee-guida-sql §11.8), non con un `REVOKE` a parte.
4. **Gli scrittori di `attivo` sono più di quelli citati.** BE: `AmmSoftwareRepository.disabilita_operatore`
   (spegnimento dell'operatore, dentro D-R2), `PortaleRepository.disattiva_identita`. DB:
   `anagrafiche.fn_accendi_veste` e `script.fn_riattiva_utente_tecnico`, che riaccende la veste di un utente
   tecnico con un `UPDATE` suo. Con D-R2 («tutte le vesti») il brief DB dice se lo spegnimento di un utente tecnico
   è una revoca e, se sì, se `fn_riattiva_utente_tecnico` è il verbo dell'amministratore che toglie il segno. Chi
   inserisce: `fn_crea_veste_portale`, `fn_crea_risorsa_umana_v2`, `fn_crea_utente_tecnico`, le fabbriche pgTAP.
5. **La revoca serve anche su una veste mai accesa.** L'admin che spegne una veste con l'invito pendente
   (D-5 chiude l'invito) vuole revocare; senza segno, un'iscrizione da sé che ritrova quella riga la accende con la
   conferma dell'email. Il segno lo mette quindi il **verbo** di spegnimento dell'admin, non solo il passaggio
   accesa → spenta.

Due punti minori: il «chi» della revoca non viene dallo storico (`user_update` è il ruolo del database, non la
persona) e va preso dalla GUC dell'utente; in `script.fn_stato_veste` lo stato `REVOCATA` si legge subito dopo
`ATTIVO` (con D-R1 non convive con un invito pendente). Il `CHECK` «revocata ⇒ spenta» si scrive con `num_nulls`
(PG19).

✅ **Fatto il 2026-11-26** (brief DB §4.1): A-6 è chiuso dal guard. I test sul DB vero
(`apps/core/tests/db/test_revoca_veste_db.py`) provano revocata → nuovo invito → il link accende, e revocata → la
veste non si riaccende. Il caso «l'iscrizione si ferma» aspetta il verbo dell'iscrizione, giro 3 del brief DB.

**Ricaduta sul §1.2**, ancora scritto sul pulsante: finché il pulsante non è ritirato il guard lo ferma comunque
(chiama `fn_accendi_veste`), quindi A-6 si chiude **col guard di R-4** e poi sparisce col ritiro. Al BE resta: lo
spegnimento dell'admin col verbo DB (operatore e portale), la policy del codice nuovo, il pannello con «revocato»,
e i test revocata → nuovo invito → il link accende, revocata → l'iscrizione si ferma, invito pendente spento →
l'iscrizione si ferma.

**Guide verificate** (`scripts/guide_coinvolte.py` sugli oggetti del §1.3):
[risorse-umane-e-accessi](../../guide/risorse-umane-e-accessi.md) **coerente** (il rientro dell'operatore passa già
dal reinvio, e l'interruttore «spegne soltanto»: R-4 porta a DB ciò che la guida descrive);
[architettura-multi-face-auth](../../guide/architettura-multi-face-auth.md) **contraddetta** dal modello dell'area
clienti, si riscrive lì (analisi §6); [contratto-guc-app](../../guide/contratto-guc-app.md) da leggere nel giro DB
per il punto 2; [processi-automatici-classe-e-identita](../../guide/processi-automatici-classe-e-identita.md) da
leggere nel giro DB per il punto 4; le altre (permessi, pgTAP, pgAgent, soggetti, `_sincronizzazione-accesso`,
`_ultimo-super-admin`) hanno solo la tabella in comune, esito nel giro DB.

## 2. Il collaudo a video di D-5 — Sessioni per veste

Il codice è chiuso dal 2026-10-02 (piano §4.3-bis, parti 1 e 2): il refresh di una veste spenta è un 401 e chiude
la sessione; «Disabilita» e l'interruttore chiudono le sessioni e gli inviti della **sola** veste spenta. Manca la
prova a video:

| # | Caso | Atteso |
| --- | --- | --- |
| a | Una persona operatore **e** cliente shop, connessa nelle due porte: «Disabilita» (e, a parte, l'interruttore spento) | Al primo rinnovo esce dall'amministrazione, **non** dallo shop |
| b | Un operatore con un invito pendente: «Disabilita» | Il link dell'invito risponde «token non valido» |
| c | Riaccendere la veste dopo lo spegnimento | La vecchia sessione non si riapre: si rientra col login |

Non blocca nulla.

## 3. Alla chiusura

Il brief va in `work-done/` quando D-4 e A-6 sono fatti e il collaudo è eseguito. Il §4 non lo trattiene: se è
ancora aperto, passa come voce in `.codex/PROJECT_CONTEXT.md` § «Aperto». Si aggiornano la riga «Accessi»
di `.codex/PROJECT_CONTEXT.md` e i «⚠️ Difetto noto» delle doc `manual/` che rimandano ad A-6.

## 4. Il contesto dei test sul DB vero, per la sola transazione (revisione del 2026-11-26)

**Il difetto.** `script.fn_pgtap_set_contesto_operatore` scrive le GUC `app.ruolo_applicativo` e
`app.current_user_id` per la **sessione** (`set_config(…, false)`). Nei pgTAP è innocuo: ogni file gira in una
sessione sua. Nei test Django la connessione è **condivisa** fra i test, e le GUC sopravvivono al rollback: il test
dopo gira col contesto di un utente annullato. Un test può essere verde, o rosso, per il contesto lasciato dal
test prima. Trovato estraendo `apri_super_admin_costruito`, la cui prima versione passava da quella funzione e
faceva cadere i test successivi su `E_PERMESSO_NEGATO`.

**Già corretto il 2026-11-26** (da committare col passo 3b): `apri_super_admin_costruito` (nuovo) e
`apri_operatore_con_aree` in `apps/core/tests/db_e2e.py`, e `_agisci` di `test_soggetti_id_fiscale_immutabile_db`,
scrivono le due GUC con `SET LOCAL`.

**Da fare, lato BE** (non è una richiesta al DB: la funzione serve ai pgTAP e lì va bene com'è):

1. **Il BB `apri_contesto_su(cur, auth_user_id) -> int`** in `db_e2e.py` (regola del 2, ok di Tid il 2026-11-26):
   le due righe `SET LOCAL` e il controllo di essere dentro un blocco atomico. Diventa la sede unica di quelle due
   righe, oggi ricopiate in `apri_contesto_operatore`, `apri_super_admin_costruito`, `apri_operatore_con_aree` e
   `_agisci`; i tre BB la chiamano. Voce nel catalogo BB backend e indice rigenerato.
2. **I file che chiamano `script.fn_pgtap_set_contesto_operatore` da soli** passano dal BB. Censimento del
   2026-11-26, da rifare al momento (`grep -rln fn_pgtap_set_contesto_operatore backend/apps --include=*.py`): una
   trentina di file in `pagamenti`, `magazzino`, `documenti`, `catalogo`, `anagrafiche`, `vendite`, `core`.
   ⚠️ Dove la funzione è chiamata **senza** argomento sceglie lei l'operatore, o lo costruisce: lì il BB non basta,
   e il test si costruisce il suo utente (`apri_operatore_con_aree`, `apri_super_admin_costruito`, o un builder).
3. **Un presidio**, perché il difetto non torni: un test che fallisce se un file di test Django chiama
   `fn_pgtap_set_contesto_operatore` (lo stampo dei guard su sorgente che il progetto già usa).
4. Test di tutti i moduli toccati col DB vero, **lanciati insieme**: un contesto che perde si vede solo fra test
   diversi della stessa corsa.

**Aspetta** l'allineamento del push DB del giro 10-bis (`8d349d36b`, «le tabelle che danno l'accesso si scrivono
solo dai verbi del SUPER_ADMIN»), già applicato al DB di sviluppo: tocca proprio i contesti dei test. Con quel
push sono rossi `test_login_credenziale_db` (contesto preso da «il primo operatore attivo», che non è SUPER_ADMIN)
e `test_error_policies_divergenza_db` (DB avanti rispetto a git: non si rigenera prima dell'allineamento). Si
riparte da `/arrivi-db`.

---
{% include-markdown "signature-core.md" %}
