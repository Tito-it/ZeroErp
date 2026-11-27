# Brief DB — Gli accessi e l'area clienti: la veste revocata, la veste cliente unica, l'iscrizione da sé

## ⏭️ Chi riparte — aggiornato al 2026-11-26

**Riparte: la sessione DB col passo 3c** (§2.4), con le richieste del BE al §4.2 (R-3b-1, R-3b-2) e il ritiro di
`fn_crea_operatore_v2`. Il passo 3b è fatto lato BE/FE il 2026-11-26 (§4.1), da committare. Giri 1 e 2 applicati,
verdi e committati il 2026-11-26 (giro 1: `6440e685d8`).

| # | Chi | Che cosa | Dove | Aspetta |
| --- | --- | --- | --- | --- |
| 2 | ~~team BE/FE~~ | ~~Il passo 3b~~ fatto il 2026-11-26, da committare: esiti al §4.1 | §4.1 | — |
| 3 | Tid | Il commit del passo 3b (branch `dev/backend-tid`) | §4.1 | 2 |
| 4 | sessione DB | Il passo 3c (le scritture dell'app), R-3b-1 (lo stato `REVOCATA` nell'aggregato di `vw_accessi_altri`), R-3b-2 (la scrittura di `invito_inviato_at` e i test Django che scrivono `attivo`), il ritiro di `fn_crea_operatore_v2` | §2.4, §4.2, §5.2 | 2 |
| 5 | sessione DB | Giri 3-6 (S64, la veste cliente unica, l'iscrizione da sé, il ritiro dei rami shop) | §5 | 4 |

**Decisioni aperte di Tid:** nessuna per i giri 1 e 2. Per i successivi restano D-M6 e D-M9
([analisi-modello-area-clienti](analisi-modello-area-clienti.md) §7) e l'emittente del cliente iscritto da sé
([sviluppo-multi-face-da-completare](sviluppo-multi-face-da-completare.md) §3.6).
**Da committare:** il passo 3b (BE/FE, doc, brief), sul branch `dev/backend-tid`.

## 0. Il piano da percorrere

- **Fase 0 — Decisioni** (Tid)
  - [x] D-R1, D-R2, D-R4, D-R5 (brief BE accessi §1.3) — 2026-11-25
  - [x] Il brief DB è unico con il modello dell'area clienti, R-4 come primo giro — 2026-11-25
  - [x] D-R7: gli utenti tecnici lasciano il segno, e `fn_riattiva_utente_tecnico` lo toglie (b) — 2026-11-25
  - [x] D-R8: il segno vale per la coppia, non per la riga — 2026-11-25
  - [x] D-R9: il passaggio col BE in tre passi (3a, 3b, 3c) — 2026-11-25
- **Fase 1 — Analisi** (sessione DB)
  - [x] Le sezioni di linee-guida-sql del giro (§5-§5g, §2, §7f, §11.8); linee-guida-trigger per intero — 2026-11-25
  - [x] Le guide del §3.3, con l'esito — 2026-11-25
  - [x] Il censimento di chi scrive e chi legge `identita_digitali.attivo` (§3) — 2026-11-25
  - [x] La forma del controllo del permesso nei verbi (§2.3) — 2026-11-25
- **Fase 2 — Costruzione DB, giro 1**
  - [x] Le colonne del segno e il `CHECK` (`20261125-51`) — 2026-11-25
  - [x] Il guard della tabella e i codici nuovi (`-52`, CSV) — 2026-11-25
  - [x] Il permesso (`-53`), il verbo della revoca (`-54`) e quello del nuovo invito (`-55`) — 2026-11-25
  - [x] `fn_riattiva_utente_tecnico` col super admin e il segno tolto (`-56`, D-R7) — 2026-11-25
  - [x] `script.fn_stato_veste` con `REVOCATA` (`-57`) — 2026-11-25
  - [x] pgTAP che costruisce ogni caso, e il test della riattivazione adeguato (§2.6) — 2026-11-25
  - [x] Apply e corsa dei pgTAP (Tid): verdi — 2026-11-26
- **Fase 3 — Il passaggio col BE**
  - [x] 3a — DB consegna i verbi e la richiesta al BE (§4) — 2026-11-25
  - [x] 3b — BE passa dai verbi (§4.1, da committare) — 2026-11-26
  - [ ] 3c — DB ritira le scritture dell'app (§2.4), con la sezione «Garanzie ritirate» compilata
- **Fase 4 — Doc**
  - [x] Guida `risorse-umane-e-accessi` (§«La revoca»), guida dei processi automatici, `manual/identita_digitali` — 2026-11-25
  - [x] Doc auto-generata rigenerata dopo l'apply (le quattro funzioni nuove, la tabella, `fn_stato_veste`, `fn_riattiva_utente_tecnico`) — 2026-11-26
  - [x] A-6 chiuso nel brief BE accessi; riga «Accessi» di `PROJECT_CONTEXT` — 2026-11-26
- **Giro 2 — Le regole della veste e della sincronizzazione** (§5.1, T9: S5, S6, S22, S59-S63, S65, S66)
  - [x] Il via di Tid — 2026-11-26
  - [x] L'analisi sui corpi vivi (dbdev) — 2026-11-26
  - [x] D-G2-1 … D-G2-3 (Tid: sì alle tre proposte) e il primo numero libero — 2026-11-26
  - [x] 2a la sincronizzazione (S59, S5, S60): `-58`, `-59`, `-60` — 2026-11-26
  - [x] 2b i guard (S61, S62, S63): `-61` … `-66` — 2026-11-26
  - [x] 2c i verbi di creazione (S6, S65, S66) e 2d i nomi (S22): `-67` … `-70` — 2026-11-26
  - [x] La fixture dell'operatore persona (`-71`) e i pgTAP adeguati (§5.2) — 2026-11-26
  - [x] La correzione della fixture col runner app (`-73`) e i due test RLS del giro 10-ter (§5.2) — 2026-11-26
  - [x] Apply e corsa dei pgTAP (Tid): verdi; doc auto-generata rigenerata — 2026-11-26
  - [ ] Il ritiro di `fn_crea_operatore_v2`, quando il BE e i due chiamanti DB sono passati
- **Giri 3-6** (§5)
  - [ ] S64; la veste cliente unica e l'indice per soggetto; l'iscrizione da sé; il ritiro dei rami shop

> **Chi scrive:** sessione DB (`dev/db-tid`), 2026-11-25. **A chi:** Tid; il team BE/FE per il §4.
> **Origine:** T9 di [brief-db-revisione-anagrafiche](brief-db-revisione-anagrafiche.md) §17.1 e R-4 di
> [brief-be-accessi-credenziale-e-vesti](brief-be-accessi-credenziale-e-vesti.md); il modello dei giri successivi
> sta in [analisi-modello-area-clienti](analisi-modello-area-clienti.md). Un brief solo per decisione di Tid
> (2026-11-25).
> **Brief vicini verificati:** i tre dell'origine, che rimandano qui per il lavoro DB;
> [sviluppo-multi-face-da-completare](sviluppo-multi-face-da-completare.md) §3.6 (la registrazione da sé: il giro
> dell'iscrizione la costruisce qui); [sviluppo-portale-shop](sviluppo-portale-shop.md) §1.4 e §3.2 (superati
> dall'analisi, si marcano al giro dell'iscrizione).
> **Guide verificate:** gli esiti di partenza al §3.3; la Fase 1 li completa.

---

## 1. Le decisioni del giro 1

Quelle del 2026-11-25 nel brief BE (§1.3): D-R1 il segno lo toglie il nuovo invito e il blocco sta in un guard
della tabella; D-R2 vale per tutte le vesti; D-R4 l'app perde la scrittura diretta; D-R5 R-4 è il primo giro. In
più, lo stesso giorno:

| # | Decisione |
| --- | --- |
| D-R7 | **Gli utenti tecnici lasciano il segno anche loro**, e `script.fn_riattiva_utente_tecnico` è il verbo dell'amministratore che lo toglie. La regola resta una, senza eccezioni nel guard |
| D-R8 | **Il segno vale per la coppia** (credenziale, ruolo anagrafico, veste): una riga nuova sulla stessa coppia non lo aggira |
| D-R9 | **Il passaggio col BE in tre passi**: il DB consegna i verbi, il BE li usa, il DB ritira le scritture dell'app. Fra il primo e il terzo uno spegnimento fatto con l'`UPDATE` del BE non lascia il segno: si accetta, il sistema non è in produzione |

## 2. Il giro 1 — R-4, la veste revocata (costruito il 2026-11-25)

Il perché di ogni punto sta nel brief BE accessi §1.4; qui ciò che è stato costruito.

| ChangeSet | Che cosa |
| --- | --- |
| `20261125-51` (00_schema) | `revocata_at timestamptz`, `revocata_da_user_id integer` su `anagrafiche.identita_digitali`; `chk_identita_digitali_revoca_coerente`: i due insieme, e revocata ⇒ spenta |
| `-52` | `anagrafiche.trgfn_identita_digitali_guard_revoca`, trigger `trg_identita_digitali_a10_guard_revoca_ins_upd_dlt` |
| `-53` | `anagrafiche.fn_guard_gestione_veste(utente, tipo di veste)`: il permesso, per tipo |
| `-54` | `anagrafiche.fn_revoca_veste(identita_id) → era accesa`: spegne e mette il segno |
| `-55` | `anagrafiche.fn_togli_revoca_veste(identita_id) → ha tolto`: il nuovo invito toglie il segno dalla coppia |
| `-56` | `script.fn_riattiva_utente_tecnico`: `fn_guard_super_admin` in testa, il segno tolto con `-55` prima di riaccendere |
| `-57` | `script.fn_stato_veste`: `REVOCATA` subito dopo `ATTIVO` |
| CSV | `E_VESTE_REVOCATA` (CONFLITTO_STATO), `E_VESTE_REVOCA_SOLO_DAL_VERBO` (TECNICO), `E_VESTE_NON_TROVATA` (NON_TROVATO); messaggi 1544-1546 |

### 2.1 Il segno

«Chi» è la credenziale della sessione (`script.fn_utente_di_sessione`): lo storico non basta, `user_update` porta il
ruolo del database. Senza FK verso `django.auth_user` (§11.9). Una veste già revocata tiene il segno della prima
revoca: il verbo è idempotente.

### 2.2 Il guard

Tre regole, in quest'ordine: (1) il segno si scrive e si toglie solo dal **proprietario della tabella**
(`script.fn_is_proprietario_tabella`, senza GUC: l'app non può aprire la porta da sé), e una veste revocata non si
cancella; (2) una veste revocata non cambia coppia; (3) nessuna veste accesa su una coppia revocata, che arrivi da
`fn_accendi_veste`, da un `UPDATE` o da una riga nuova. La (3) vale anche per il proprietario: chi riapre toglie
prima il segno. La tabella non ha RLS, quindi il guard rilegge le altre righe della coppia da invocante.

### 2.3 Il permesso

Lo decide `anagrafiche.fn_guard_gestione_veste`, con i permessi che il backend chiede oggi alle stesse porte (letti
sul codice il 2026-11-25): `OPERATORE` → `script.fn_guard_super_admin` (amm_software); `CLIENTE_PORTALE` e
`SHOP_CUSTOMER` → `script.fn_guard_livello(…, 'anagrafiche', 'cliente', 'TUTTO')`; `FORNITORE_PORTALE` → lo stesso su
`fornitore`; ogni altro tipo → super admin. I verbi sono `SECURITY DEFINER` col `search_path` fissato, come i verbi
di magazzino. `fn_togli_revoca_veste` chiede il permesso anche quando non c'è niente da togliere.

⚠️ Il perimetro: i verbi ricevono l'id che il backend ha risolto dal cliente o dall'operatore sotto il suo scope,
come l'`UPDATE` di oggi; nessun controllo di perimetro in più a DB.

### 2.4 Le scritture che l'app perde (passo 3c)

`zeroerp_app` ha oggi `INSERT`, `UPDATE` su ogni colonna e `DELETE` su `identita_digitali`. Al passo 3c perde
l'`UPDATE` di `attivo` e delle colonne del segno, e il `DELETE`; si ritira dal loop dei grant (§11.8). Tre cose da
fare nello stesso giro, trovate costruendo il giro 1:

- `anagrafiche.fn_accendi_veste` e `script.fn_riattiva_utente_tecnico` sono INVOKER e scrivono `attivo` da app:
  diventano `SECURITY DEFINER`;
- `attivo` ha `DEFAULT true`: un'`INSERT` dell'app che non lo nomina nasce accesa. Con l'`INSERT` lasciato all'app,
  il default va a `false`, oppure anche la nascita passa dai verbi (`fn_crea_veste_portale` e le fabbriche);
- censire ogni scrittura diretta rimasta nel backend (la richiesta del §4).

⚠️ **I verbi di creazione li porta a DEFINER il giro 10-bis** di
[brief-db-porte-aperte-dalla-sola-guc](../work-done/2026/brief-db-porte-aperte-dalla-sola-guc.md) §14 (D-AD **b**, Tid, 2026-11-26):
`fn_crea_operatore` (e l'involucro `_v2`), `fn_crea_risorsa_umana`, `fn_crea_utente_tecnico`, i verbi dei legami di
profilo, con le fixture pgTAP. Una funzione si riscrive una volta sola: il 3c non li riscrive, li trova già DEFINER.
Qui restano `identita_digitali` (il grant, il default di `attivo`), `fn_accendi_veste`, `fn_riattiva_utente_tecnico`,
`fn_crea_veste_portale` e il ritiro del `_v2`. Se il 3c parte prima del 10-bis, l'ordine lo decide Tid.

### Garanzie ritirate

Nessuna in questo giro: si aggiungono rifiuti, non si tolgono garanzie. Lettori del segno lato DB: il guard e
`script.fn_stato_veste`. Si compila al passo 3c.

### 2.5 Che cosa cambia per chi c'era già

- **`script.fn_riattiva_utente_tecnico` chiede `SUPER_ADMIN` a DB.** Prima lo chiedeva solo il backend (la porta di
  amm_software). Un chiamante che la usava da un operatore qualunque ora riceve `E_PERMESSO_NEGATO`.
- **Lo stato `REVOCATA` è un valore nuovo** di `script.fn_stato_veste`, e quindi di `anagrafiche.vw_accessi_altri`.

### 2.6 La prova (2026-11-25, scratch `zeroerp_ruoli`)

- `scripts/prova_changeset.py` sui sette changeSet: estratto eseguito per intero, catalogo identico dopo il
  `ROLLBACK`. La precondition del `-56` (esiste `fn_togli_revoca_veste`) è falsa sullo scratch perché il `-55` non è
  applicato: all'apply gira dopo il `-55`.
- **`anagrafiche/test-veste-revocata-v1`**: 24/24. ⚠️ **Limite della prova:** sullo scratch l'owner non è membro di
  `zeroerp_app`, e `prova_changeset.py` lancia il pgTAP da owner, dove il guard lo riconosce proprietario: i test 4,
  5 e 16 («l'app scrive il segno da sé») lì sono rossi per costruzione. La corsa da 24/24 è una copia nello
  scratchpad che ridefinisce `fn_is_proprietario_tabella` dentro la transazione annullata e dice «non proprietario»
  solo intorno alle scritture dirette dell'app; i verbi DEFINER restano proprietario. La corsa vera è quella del
  runner di Tid, che il test lo lancia come app.
- **`script/test-fn-riattiva-utente-tecnico`** (runner owner), adeguato: il contesto è un super admin costruito dal
  test; nuovi i casi 7 (senza super admin), 7-bis, 8 (l'utente tecnico revocato), 9 (la riattivazione toglie il
  segno). 10/10.
- **Regressione**, senza e con l'estratto, nessun rosso nuovo: i presidi del catalogo errori
  (`test-catalogo-messaggi-errore-completo`, `test-vw-codici-errore-motivo-nominato`,
  `test-rubinetto-primo-motivo-v1`), `test-comment-al-presente-v1`, `test-riferimenti-morti-v1`,
  `test-security-definer-search-path-v1` e diciotto pgTAP che scrivono le vesti (area accessi, operatore, super
  admin, sync, roster, riattivazione, scope di processo…). Tre hanno un rosso già presente prima dei changeSet, uguale
  dopo: `test-identita-digitali-unique-multi-veste` (rosso in baseline, lo dice la sua pagina), 
  `test-sync-auth-user-is-active-multi-role`, `test-elimina-credenziale-v1`. Tutti e tre girano come app e la prova
  li lancia da owner; la causa del rosso non è indagata, ma è lo stesso test prima e dopo.
- Guardrail statici sui sette file: forme, COMMENT al presente, runOnChange, precondition, trigger generati, grant
  batch, letterali, timestamp: verdi.
- **Apply di Tid su dbdev il 2026-11-26**: i sette changeSet e i CSV; `test-veste-revocata-v1` e
  `test-fn-riattiva-utente-tecnico` verdi dal runner, cioè il primo come app: il limite della prova dello scratch è
  chiuso dalla corsa vera.

## 3. Il censimento (2026-11-25)

### 3.1 Chi scrive `attivo`

| Dove | Chi | Che cosa fa | Dopo il giro 1 |
| --- | --- | --- | --- |
| DB | `anagrafiche.fn_accendi_veste` | accende (invito, pulsante) | il guard la ferma su una coppia revocata |
| DB | `script.fn_riattiva_utente_tecnico` | accende l'utente tecnico | toglie prima il segno, col super admin |
| DB | `anagrafiche.fn_revoca_veste` | spegne e segna | nuovo |
| DB | `fn_crea_veste_portale`, `fn_crea_risorsa_umana_v2`, `fn_crea_utente_tecnico`, `fn_provisiona_dati_di_sviluppo`, le fabbriche pgTAP | inseriscono vesti | il guard rifiuta una veste accesa su una coppia revocata |
| BE | `AmmSoftwareRepository.disabilita_operatore` | spegne l'operatore con un `UPDATE` | passo 3b: `fn_revoca_veste` |
| BE | `PortaleRepository.disattiva_identita` (da `_disattiva_veste_common`) | spegne la veste portale o shop con un `UPDATE`, **solo se era accesa** | passo 3b: `fn_revoca_veste` sempre, anche sulla spenta |
| BE | `AuthRepository.attiva_identita` | accende, via `fn_accendi_veste` | invariato |

Nessun `DELETE` di vesti nel backend (il model `IdentitaDigitale` è `managed=False`, in sola lettura); a DB solo il
backfill di `80_data` del 2026-04-19, da owner.

### 3.2 Chi legge il segno

Il guard e `script.fn_stato_veste` (e da lei `anagrafiche.vw_accessi_altri`).

### 3.3 Le guide

| Guida / nota | Esito |
| --- | --- |
| [risorse-umane-e-accessi](../../guide/risorse-umane-e-accessi.md) | **guida indietro, aggiornata nel giro**: sezione «La revoca», stato `REVOCATA`, cessazione, rientro, tabelle di funzioni e guard; dice che il backend non passa ancora dai verbi |
| [processi-automatici-classe-e-identita](../../guide/processi-automatici-classe-e-identita.md) | **guida indietro, aggiornata**: la riattivazione è del super admin e toglie la revoca |
| [contratto-guc-app](../../guide/contratto-guc-app.md) | coerente: i verbi leggono l'utente da `script.fn_utente_di_sessione` (§4.4) |
| [architettura-permessi-e-autorizzazioni](../../guide/architettura-permessi-e-autorizzazioni.md) | coerente: verbi col guard di permesso in prima riga |
| [architettura-multi-face-auth](../../guide/architettura-multi-face-auth.md) | contraddetta dal modello dell'area clienti: si riscrive coi giri successivi (analisi §6) |
| `pgtap-come-si-scrive-un-test`, `soggetti-e-ruoli-anagrafici`, `processi-pgagent-funzionali`, `automazione-db`, `Messaggi-di-Errore-e-Generazione-Log`, `_sincronizzazione-accesso`, `_ultimo-super-admin` | coerenti: oggetti in comune (la tabella, le fixture, il catalogo), regole che il giro non cambia |
| `manual/identita_digitali` | aggiornata: «La veste revocata non si riaccende», codici, test |

Orfano segnalato dallo script: `dbops.processi_identita`, che nessuna guida cita per nome. Non nasce da questo giro.

## 4. La richiesta al team BE/FE (passo 3b)

I verbi sono consegnati (`20261125-54`, `-55`) e aspettano l'apply. Lato BE:

1. **Lo spegnimento dell'amministratore passa da `anagrafiche.fn_revoca_veste(identita_id)`**, che ritorna se la
   veste era accesa:
   - `AmmSoftwareRepository.disabilita_operatore`, passo 1: al posto dell'`UPDATE … SET attivo = false`;
   - `InvitoPortaleService._disattiva_veste_common`: **sempre**, anche sulla veste già spenta con l'invito pendente
     (oggi spegne solo `if was_active`): è il caso che la revoca deve coprire. `was_active` si legge dal ritorno.
     `PortaleRepository.disattiva_identita` si ritira.
2. **Ogni invito e reinvito dell'amministratore chiama `anagrafiche.fn_togli_revoca_veste(identita_id)`** nella
   transazione in cui scrive il token: operatore (`InvitoOperatoreService.invia_invito`, `reinvia_invito`), cliente,
   fornitore e shop (`InvitoPortaleService`, dopo `_ensure_identita`). Il verbo è idempotente.
3. **I codici nuovi** nelle policy generate: `E_VESTE_REVOCATA` (CONFLITTO_STATO; arriva dal link di un invito
   vecchio, dal pulsante «Attiva shop» finché esiste, e da ogni accensione), `E_VESTE_REVOCA_SOLO_DAL_VERBO`
   (TECNICO), `E_VESTE_NON_TROVATA` (NON_TROVATO).
4. **Lo stato `REVOCATA`** di `script.fn_stato_veste` e di `anagrafiche.vw_accessi_altri`: chi mappa gli stati (lo
   stato accessi di `PortaleRepository`, la lista «Altri accessi», le costanti FE) lo riconosce; il pannello mostra
   «revocato».
5. **`script.fn_riattiva_utente_tecnico` chiede `SUPER_ADMIN` a DB**: la porta di amm_software lo chiede già; i test
   Django che la chiamano girano con un super admin.
6. ⛔ **Censisci chi scrive `anagrafiche.identita_digitali.attivo` e chi cancella vesti**, a partire dal §3.1:
   l'elenco non è chiuso. Ogni scrittura diretta rimasta si porta su un verbo prima del passo 3c, quando l'app
   perde il privilegio; se ne serve uno che non c'è, la richiesta torna al DB tutta insieme.
7. Nel [brief BE accessi](brief-be-accessi-credenziale-e-vesti.md) A-6 si chiude col guard (il pulsante passa da
   `fn_accendi_veste`, che ora rifiuta una veste revocata), e poi sparisce col ritiro del pulsante.

Dal giro 2 (2026-11-26, dopo l'apply di `20261125-58` … `-71`):

8. **`anagrafiche.fn_crea_operatore`** è il nome del verbo; `fn_crea_operatore_v2` resta un involucro con la stessa
   firma finché `AmmSoftwareRepository` non passa al nome nuovo. Poi il DB lo ritira: dite quando.
9. **Una credenziale senza nessuna veste si spegne**: il job e il trigger la portano a `is_active = false`. Il
   management command `sync_auth_user_active` (anche in `--dry-run`) la conta fra le riallineate; la sua doc e i
   test Django che si aspettano una credenziale senza vesti accesa vanno riletti. ⛔ Censite chi crea una
   credenziale senza darle subito una veste (`PortaleRepository.create_auth_user_portale` è la domanda R-BE6): se la
   veste arriva in un'altra transazione, la credenziale si spegne nel mezzo e la riaccende la veste.
10. **I codici nuovi**: `E_VESTE_TECNICA_SOLO_OPERATORE` (TECNICO) e `E_SUPER_ADMIN_SU_VESTE_TECNICA`
    (CONFLITTO_STATO: arriva se dall'amministrazione si dà il profilo SUPER_ADMIN all'utente di un processo).
11. **Le policy generate** nominano ancora `fn_crea_operatore_v2` e `fn_crea_risorsa_umana_v2` nei commenti: si
    rigenerano dal catalogo, che porta i nomi nuovi.

### 4.1 Il piano del BE/FE per il passo 3b (sessione BE, 2026-11-26)

**Regola del 2, ok di Tid il 2026-11-26:**

- **R2-a**: lo spegnimento ha una sede sola, `AuthRepository.revoca_veste(identita_id) → bool` (accanto ad
  `attiva_identita`), che chiama `fn_revoca_veste`; la usano `AmmSoftwareRepository.disabilita_operatore` e
  `InvitoPortaleService._disattiva_veste_common`. `PortaleRepository.disattiva_identita` si ritira.
- **R2-b**: il segno lo toglie `InvitoVeste.emetti`, nella transazione del token: è già il punto unico di ogni
  invito e reinvito (operatore, cliente, fornitore, shop). Le attivazioni dal lato cliente (`ProfileActivateShopView`)
  non lo toglono: è la chiusura di A-6.

| Blocco | Punti §4 | Che cosa |
| --- | --- | --- |
| B0 | — | Indici BB backend e frontend per intero; api.md §Tassonomia errori |
| B1 | 1 | La revoca da R2-a; `_disattiva_veste_common` revoca sempre, `was_active` dal ritorno. Il sync esplicito di `disabilita_operatore` si verifica sul corpo vivo prima di toccarlo |
| B2 | 2 | R2-b |
| B3 | 3, 10, 11 | Policy rigenerate dal catalogo (`genera_error_policies`), ripiego senza `%s` per i codici nuovi |
| B4 | 4 | `REVOCATA`: `STATI_ACCESSO`, filtro e OpenAPI della lista «Altri accessi», mappa di `PortaleRepository`; FE `STATO_VESTE`, severity, i18n, `PortaleAccessoPanel` (su `REVOCATA` «Invia», non «Disattiva»); catalogo FE e indice |
| B5 | 8 | `AmmSoftwareRepository` su `fn_crea_operatore`; poi il DB ritira il `_v2` |
| B6 | 5 | Test Django di `fn_riattiva_utente_tecnico` con un super admin |
| B7 | 9 | `sync_auth_user_active` (doc, test); `create_auth_user_portale` (R-BE6): la veste nasce nella stessa transazione? |
| B8 | 6 | Il censimento di chi scrive `attivo` e cancella vesti, con gli `INSERT` (il `DEFAULT true`, §2.4); verbi mancanti tornano al DB tutti insieme |
| B9 | 7 | A-6 nel brief BE accessi, con il test della veste revocata dal pulsante shop |
| B10 | — | Guide: `risorse-umane-e-accessi` (il BE passa dai verbi); catalogo BB backend (L801, L811) |
| B11 | — | Test dei soli moduli toccati |

**Esiti (sessione BE, 2026-11-26, da committare):**

| Blocco | Esito |
| --- | --- |
| B0 | Letti i due indici; aperte le voci BE L801, L804, L809, L811-L813, L861 e FE L338, L445 |
| B1 | `AuthRepository.revoca_veste` / `togli_revoca_veste` (nuovi, accanto ad `attiva_identita`). `disabilita_operatore`: il passo 1 revoca la veste di `get_veste_operatore_id`; passi 2-3 (rapporto, sync esplicito) invariati. `_disattiva_veste_common` revoca sempre, `disattivato` dal ritorno del verbo, `stato: REVOCATA` in risposta. `PortaleRepository.disattiva_identita` ritirato |
| B2 | `InvitoVeste.emetti` toglie il segno per primo, nella transazione del token. Gli altri inviti non chiamano il verbo da sé |
| B3 | `error_policies_generated.py` rigenerato (DB allineato a git: i sei codici nuovi sono nei CSV committati; uno è `E_OPERATORE_SCOPE_GLOBALE_SOLO_SUPER_ADMIN` del giro 10-ter, entrato con la stessa rigenerazione); ripiego senza `%s` per i sei; i commenti portano i nomi senza `_v2` |
| B4 | `REVOCATA` nella mappa di `PortaleRepository`, in `STATO_VESTE` (FE), rosso in `STATO_VESTE_MAP`, i18n it/en («Revocato»), `PortaleAccessoPanel`: su `REVOCATA` «Invia invito» e niente «Disattiva». ⛔ **Non** nel filtro di «Altri accessi» (Tid, 2026-11-26, dalla revisione): né in `STATI_ACCESSO` né in `STATI_FILTRO` di `AccessiAltriTab`, perché la vista non lo produce ancora (R-3b-1 qui sotto) e il filtro risponderebbe la lista vuota |
| B5 | `AmmSoftwareRepository.crea_operatore` chiama `fn_crea_operatore`; i manuali BE coi nomi nuovi. Nel BE nessuno nomina più `fn_crea_operatore_v2`: il DB lo può ritirare |
| B6 | Niente da adeguare: la porta è un'`AdminAPIView` (SUPER_ADMIN), e nessun test Django chiama la funzione sul DB vero |
| B7 | `sync_auth_user_active`: la testata dice che spegne anche la credenziale senza vesti; i test sono a mock e non ne dipendono. R-BE6: `create_auth_user_portale` gira nella stessa transazione di `_ensure_identita` (`InvitoPortaleService._invia_invito_common`), quindi la credenziale non resta mai senza veste. `AuthRepository.crea_auth_user` non aveva chiamanti fuori dal suo test: ritirato col test (Tid, 2026-11-26) |
| B8 | Il censimento qui sotto, R-3b-2 |
| B9 | A-6 chiuso dal guard nel brief BE accessi; la view «Attiva shop» lo dice nel commento |
| B10 | Guide e cataloghi: §4.3 |
| B11 | Test dei moduli toccati: 380 Django (uno `skip`, R-3b-1; ritirato dalla revisione, vedi R-3b-1) col DB vero acceso, 211 vitest, ruff verde, mypy pulito sui file di codice (i 6 rilievi stanno nei test, che `mypy.ini` esclude, e c'erano già). Nuovo `apps/core/tests/db/test_revoca_veste_db.py` (6 casi costruiti). Adeguati: `test_token_veste_db` (l'emissione vuole una veste vera), `test_operatore_altre_vesti_db` (dopo «Disabilita» l'attivazione passa dal nuovo invito; il contesto dei gesti di spegnimento è un SUPER_ADMIN dichiarato, non «il primo operatore attivo»), `test_accessi_db` (il presidio degli stati legge anche la vista), `test_invito_portale_service`. Dalla revisione: `PortaleAccessoPanel.spec.js` prova i pulsanti su `REVOCATA` e `PENDING` |

### 4.2 Le richieste del BE al DB per il passo 3c (2026-11-26)

- **R-3b-1, `anagrafiche.vw_accessi_altri.stato_accesso` non conosce `REVOCATA`.** Le vesti nel jsonb `vesti` portano
  lo stato giusto, ma l'aggregato «il migliore fra le vesti» ha `ATTIVO`, `PENDING`, `NON_SPEDITO` e poi `ELSE
  'DISATTIVO'`: una credenziale con tutte le vesti revocate risulta `DISATTIVO`, e un filtro `stato_accesso=REVOCATA`
  risponderebbe **la lista vuota, senza errore**. Il presidio BE non lo vedeva, perché leggeva il corpo di
  `fn_stato_veste` e non la vista. Ora la legge. Fino al changeSet `REVOCATA` **resta fuori dal filtro** (Tid,
  2026-11-26): il BE lo rifiuta con un 400, il FE non lo offre. `test_uno_stato_che_la_vista_impara_entra_nel_filtro`
  diventa rosso quando la vista lo produce: allora si aggiunge a `STATI_ACCESSO` (BE) e a `STATI_FILTRO`
  (`AccessiAltriTab`) nello stesso giro, nell'ordine scelto dal DB. La posizione nell'ordine la decide il DB. Proposta: dopo `NON_SPEDITO` e prima di `DISATTIVO`, perché
  una veste spenta senza segno si riapre con un invito come una revocata, ma la revocata dice di più.
- **R-3b-2, il censimento di chi scrive le vesti dal BE** (§4 punto 6). La ricerca copre SQL su più righe e ORM in
  `backend/apps`, fuori dai test. Dopo il 3b:
  - `attivo` e il segno si scrivono **solo dai verbi**: `fn_revoca_veste`, `fn_togli_revoca_veste`,
    `fn_accendi_veste`, `fn_crea_veste_portale`, `fn_crea_operatore`, `fn_riattiva_utente_tecnico`;
  - **nessun `DELETE`** e nessun `INSERT` diretto: la nascita passa da `fn_crea_veste_portale` (invito spento, shop
    acceso) e da `fn_crea_operatore`. Il `DEFAULT true` di `attivo` non tocca il codice applicativo;
  - **resta un `UPDATE` diretto**: `AuthRepository.set_invito_inviato_at`, `SET invito_inviato_at = now()`, che
    filtra su `id` e `auth_user_id`. Non tocca `attivo` né il segno. Se il 3c toglie all'app l'`UPDATE` della
    tabella intera e non per colonna, serve un verbo (`fn_segna_invito_inviato`?);
  - fuori dalla tabella: `disabilita_operatore` scrive ancora `risorse_umane.attivo` e `valido_al` con un `UPDATE`
    diretto, dopo la revoca;
  - ⚠️ **I test Django sul DB vero scrivono `attivo` direttamente** per costruire i casi: `test_accessi_db`,
    `test_operatore_valido_al_db`, `test_login_credenziale_db`, `test_revoca_veste_db`, `test_commessa_testata_db`
    (e `tecnica` in `test_operatori_senza_utenti_tecnici`); con un `INSERT` diretto della veste, spenta,
    `test_token_veste_db` e `test_operatore_altre_vesti_db` (revisione del 2026-11-26). Al 3c si rompono. La strada va decisa insieme: una
    fixture `dbops.fn_pgtap_*` per spegnere e accendere una veste, come per i pgTAP, oppure i verbi.
- **Il ritiro di `fn_crea_operatore_v2`**: il BE è passato (B5). Restano i due chiamanti DB del §5.2.

### 4.3 Guide e cataloghi del passo 3b

`scripts/guide_coinvolte.py` sui file del diff, senza i due file generati dal catalogo errori e senza le traduzioni,
che nominano tutto:

- [risorse-umane-e-accessi](../../guide/risorse-umane-e-accessi.md): **guida indietro, aggiornata**. Il «⚠️ il
  backend non passa ancora dai due verbi» del §«La revoca» ora descrive i punti che passano dai verbi e il pulsante
  shop che si ferma;
- `architettura-multi-face-auth`: resta contraddetta dal modello dell'area clienti, si riscrive coi giri 3-6. Le
  sue righe sulla disattivazione (§8.1) restano vere;
- `architettura-permessi-e-autorizzazioni`, `processi-automatici-classe-e-identita`, `contratto-guc-app`,
  `_sincronizzazione-accesso`, `_ultimo-super-admin`: **coerenti** (i verbi col guard in testa, l'utente dalla
  sessione, la sync dai trigger);
- le altre trenta: oggetti in comune coi repository toccati, che nominano altri domini (clienti, fatturazione,
  pratiche…). Regole invariate, **coerenti**;
- manuali BE aggiornati: `api_invito_portale_shop` (stato `REVOCATA`, la risposta della disattivazione),
  `api_amm_software` (§1.5 «Disabilita» è una revoca, il filtro `stato_accesso`), `api_invito_operatore` (il nome
  nuovo);
- cataloghi BB: BE L801 (`emetti` toglie il segno), L809 (`revoca_veste`, `togli_revoca_veste`), L811, L812
  (`disattiva_identita` ritirato); FE L338, L445 (`REVOCATA`). Indici rigenerati.

## 5. I giri successivi

Il tema T9 di [brief-db-revisione-anagrafiche](brief-db-revisione-anagrafiche.md) (§17.1) porta qui, oltre a R-4,
le segnalazioni S5, S6, S22, S59-S67 e R-BE6; il modello dei giri 3-6 sta in
[analisi-modello-area-clienti](analisi-modello-area-clienti.md) §5.1 e §8. Ogni giro si dettaglia qui quando parte.

### 5.1 Giro 2 — Le regole della veste e della sincronizzazione (analisi del 2026-11-26)

Letto sui corpi vivi di dbdev (`pg_get_functiondef`, `pg_trigger`). Il dettaglio di partenza di ogni voce è nel brief
anagrafiche §16.2-§16.3. Non aspetta il BE, salvo 2d.

**2a — La sincronizzazione di `is_active`**

| # | Fatto sul vivo | Proposta |
| --- | --- | --- |
| S59 | Il trigger di sync della veste è `AFTER INSERT` e `AFTER UPDATE OF attivo, valido_dal, valido_al, ruolo_applicativo, auth_user_id`, e chiama la sync solo su `NEW.auth_user_id`: una veste cancellata, o spostata su un'altra credenziale, lascia la credenziale di prima com'era. `fn_sync_auth_user_is_active` su una credenziale senza vesti la spegne, ma nessuno la chiama; il job guarda solo le credenziali che hanno vesti | il trigger scatta anche sul `DELETE` e, quando la credenziale cambia, sincronizza **tutte e due**; per il job vedi D-G2-1 |
| S60, S5 | Il cambio di `soggetto_ruolo_id` e di `tecnica` della veste non è fra le colonne del trigger; il trigger del rapporto scatta solo su `UPDATE OF attivo, valido_dal, valido_al`, non sull'`INSERT` né sul cambio di `soggetto_ruolo_id` | le colonne entrano; il rapporto sincronizza anche all'`INSERT` e al cambio di ruolo, su tutte e due le credenziali. Il terzo caso di S5 (il soggetto spento) non si raggiunge per costruzione: lo spegnimento del soggetto è bloccato dai suoi `soggetti_ruoli`, e una veste ha sempre un ruolo; si dichiara, non si costruisce |

Il pgTAP `test-sync-auth-user-is-active-multi-role`, rosso in baseline, ha il caso 3 scritto sulla scelta di oggi
(«nessuna modifica» su una credenziale senza vesti): si riscrive con D-G2-1.

**2b — I guard**

| # | Fatto sul vivo | Proposta |
| --- | --- | --- |
| S61 | Il guard dell'ultimo SUPER_ADMIN sulla veste scatta `WHEN` cambiano `attivo` o le date, e dentro esce se non è uno spegnimento o una scadenza. L'invariante che rilegge (`fn_check_almeno_un_super_admin_attivo`, da `fn_identita_super_admin_senza_scadenza`) conosce già veste, rapporto e credenziale bloccata: è il cancello a essere stretto | il trigger scatta anche sul cambio di `auth_user_id`, `soggetto_ruolo_id`, `ruolo_applicativo`, `tecnica`; dentro, se la veste di prima era SUPER_ADMIN, rilegge l'invariante senza filtrare la forma del cambio. Il rapporto: il guard scatta anche sul `DELETE` (la porta di manutenzione) |
| S62 | `trgfn_risorse_umane_guard_identita_attiva` cerca la veste accesa su `NEW.soggetto_ruolo_id` | cerca su `OLD` e `NEW` |
| S63 | Il guard di coerenza legge `tecnica` solo nel ramo `OPERATORE`; nessun controllo sul SUPER_ADMIN di un'identità tecnica; `fn_is_super_admin_account` non esclude `tecnica`. Fatto datato: su dbdev zero vesti tecniche fuori dall'operatore e zero SUPER_ADMIN su una tecnica | D-G2-3 |

**2c — I verbi di creazione**

| # | Fatto sul vivo | Proposta |
| --- | --- | --- |
| S6 | `fn_crea_risorsa_umana_v2(…, p_is_super_admin boolean DEFAULT false, p_attivo boolean DEFAULT true)`: la veste nasce accesa per default, contro la regola «nasce spenta»; `p_is_super_admin` senza credenziale si ignora in silenzio | `p_attivo DEFAULT false` (cambio di default: `CREATE OR REPLACE`, firma invariata; il solo chiamante, `fn_crea_operatore_v2`, lo passa); super admin senza credenziale: un codice |
| S65 | `p_valido_dal` passato `NULL` muore sul NOT NULL del rapporto (23502); chiamata da sola non controlla una veste `OPERATORE` spenta già sulla credenziale | `NULL` ripiega sul giorno operativo, come per la veste; la veste spenta esistente: un codice |
| S66 | `fn_provisiona_dati_di_sviluppo` al rilancio riaccende le vesti ma non rimette il SUPER_ADMIN di `dev.smoke`, le date, il rapporto | il rilancio riallinea anche questi |

**2d — I nomi `_v2` (S22)**: `fn_crea_operatore_v2` e `fn_crea_risorsa_umana_v2` non hanno una versione accanto.
Chiamanti: nel BE `AmmSoftwareRepository` (una chiamata) e le policy generate; nel DB `fn_provisiona_dati_di_sviluppo`
e la fixture `dbops.fn_pgtap_crea_operatore_umano`; i pgTAP (17 file fra BE e pgTAP nominano i due nomi). D-G2-2.

| # | Decisione | Proposta |
| --- | --- | --- |
| D-G2-1 | Una credenziale **senza nessuna veste** resta accesa? Oggi il modello non la ammette (il presidio `vw_credenziali_da_sanare` la dice `NESSUNA_VESTE`) ma il job la lascia accesa | **sì, si spegne**: il trigger quando se ne va l'ultima veste, il job per quelle nate senza (`fn_crea_auth_user` senza veste). Da verificare prima: le credenziali senza veste che servono (un superuser Django, gli account di sviluppo) |
| D-G2-2 | I nomi senza `_v2`, e come si passa | `fn_crea_operatore`, `fn_crea_risorsa_umana`. Il DB crea i nomi nuovi e tiene i `_v2` come involucro sottile finché il BE non passa (lo stesso schema in tre passi di D-R9), poi li ritira |
| D-G2-3 | `tecnica = true` fuori dalla veste `OPERATORE`, e il SUPER_ADMIN su un'identità tecnica | **si rifiutano tutti e due**: il guard di coerenza per il primo, il guard dei binding per il secondo; `fn_is_super_admin_account` esclude `tecnica` |

### 5.2 Giro 2 costruito (2026-11-26)

| ChangeSet | Che cosa |
| --- | --- |
| `20261125-58` | sync della veste: anche sul `DELETE` e sulla credenziale di prima; colonne `soggetto_ruolo_id`, `tecnica` |
| `-59` | sync del rapporto: `INSERT`, `DELETE`, cambio di ruolo, su ogni credenziale con una veste OPERATORE sul ruolo nuovo e di prima |
| `-60` | `fn_sync_auth_user_expired`: anche la credenziale senza vesti (si spegne) |
| `-61` | guard dell'ultimo SUPER_ADMIN sulla veste: anche credenziale, ruolo, tipo, `tecnica` |
| `-62` | guard dell'ultimo SUPER_ADMIN sul rapporto: anche il `DELETE` |
| `-63` | guard del rapporto acceso: anche il ruolo di prima |
| `-64` | guard di coerenza della veste: `tecnica` solo sull'operatore; la veste che diventa tecnica col SUPER_ADMIN |
| `-65` | guard dei binding: il SUPER_ADMIN non si lega a un'identità tecnica |
| `-66` | `fn_is_super_admin_account` esclude `tecnica` |
| `-67` | `fn_crea_risorsa_umana` (nuova): veste spenta per default, SUPER_ADMIN senza credenziale e veste OPERATORE già presente rifiutati, `valido_dal` vuoto ripiega |
| `-68` | `fn_crea_operatore` (nuova, il corpo del `_v2`); `fn_crea_operatore_v2` diventa un involucro `LANGUAGE sql` |
| `-69` | `fn_provisiona_dati_di_sviluppo`: il rilancio rimette soggetto, rapporto, date, revoca e SUPER_ADMIN; chiama `fn_crea_operatore` |
| `-70` | `fn_crea_risorsa_umana_v2` ritirata (nessun chiamante dopo il `-69`) |
| `-71` | `dbops.fn_pgtap_crea_emittente_operatore(…, p_persona)`: l'operatore dell'azienda può essere una persona |
| `-73` | La stessa fixture: con `p_persona` l'azienda entra nel perimetro da `dbops.fn_pgtap_sposta_scope_operatore` (il verbo), non da `script.fn_applica_user_emittenti_scope`, che l'app non esegue. Il `-71` si fermava col runner app con «permesso negato» (corsa di Tid, 2026-11-26); la prova sullo scratch gira da owner e non lo vedeva |
| CSV | `E_VESTE_TECNICA_SOLO_OPERATORE` (TECNICO), `E_SUPER_ADMIN_SU_VESTE_TECNICA` (CONFLITTO_STATO); le note del catalogo coi nomi nuovi |

**Scostamenti dall'analisi.**

- S6 e S65 non si scrivono sul `_v2` e poi si ricopiano: nascono direttamente in `fn_crea_risorsa_umana`, e il `_v2`
  si ritira nello stesso giro, perché i suoi chiamanti sono solo nel database.
- `fn_crea_operatore_v2` resta come involucro: lo chiamano il backend, `fn_crea_primo_amministratore` e la fixture
  `dbops.fn_pgtap_crea_operatore_umano`. I due chiamanti DB passano al nome nuovo nel giro che ritira il `_v2`.
- S61 sull'identità guarda anche `tecnica`: con D-G2-3 una veste SUPER_ADMIN non diventa tecnica, ma il guard
  dell'ultimo amministratore resta la rete.
- **D-G2-3 ha trovato nove pgTAP** che legavano il SUPER_ADMIN all'utente tecnico della fixture
  `fn_pgtap_crea_emittente_operatore`, contro il COMMENT della fixture stessa («non usarlo dove il soggetto è
  l'operatore umano»). La fixture si estende con `p_persona` (`-71`), e in quei test l'operatore che diventa
  SUPER_ADMIN nasce persona. Due test costruivano a mano i casi che ora si rifiutano (un SUPER_ADMIN su un utente
  tecnico, una veste tecnica trasformata in `API_CLIENT`): corretti tenendo il caso che provano.

**La prova** (scratch `zeroerp_ruoli`, 2026-11-26):

- estratto dei quattordici changeSet eseguito per intero; dopo l'estratto la precondition del `-70` vale, ogni nome
  ha una sola firma e i trigger sono montati come previsto;
- `anagrafiche/test-vesti-sync-e-guard-v1` (nuovo): 14/14. I casi 1-9 costruiscono il comportamento; 10-14 sono
  **presidi di forma** (S61, S62, S60, l'esclusione di `tecnica`), perché il caso vero chiede di spegnere ogni altro
  amministratore o di fabbricare una seconda persona col suo ruolo e senza rapporto;
- adeguati: `test-sync-auth-user-is-active-multi-role` (il caso 3 era scritto sulla scelta di prima: era il rosso in
  baseline), i sei test che chiamavano `fn_crea_risorsa_umana_v2`, `test-character-n-v1` (il nome nuovo nel
  registro), `test-fn-get-credenziale-per-email-v1`, `test-profili-accesso-guard-ultimo-super-admin`,
  `test-vw-processi-roster` e i nove della fixture;
- regressione senza e con l'estratto su 52 pgTAP (i 37 del primo elenco, più i test che legano il SUPER_ADMIN o
  usano la fixture): 49 verdi. I tre rossi sono gli stessi prima e dopo: `test-veste-revocata-v1` (il limite della
  prova da owner, §2.6), `test-guard-attivo-occhi-del-proprietario-v1` e `test-rls-listini-ef-whitelist-write`
  (i casi di perimetro, rossi da owner per costruzione: 4 e 2 rossi anche prima delle modifiche);
- guardrail statici sui quattordici file: verdi.

**Guide del giro 2** (`scripts/guide_coinvolte.py` sui quattordici changeSet): `risorse-umane-e-accessi` **guida
indietro, aggiornata** (trigger di sync, job, la sync che non vede solo il tempo, R6 con `tecnica` e SUPER_ADMIN, i
nomi nuovi); `pgtap-come-si-scrive-un-test` e `manual/fn_pgtap_crea_emittente_operatore` **aggiornate**
(`p_persona`); `architettura-permessi-e-autorizzazioni` **aggiornata** (il SUPER_ADMIN è di una persona);
`architettura-multi-face-auth` solo i nomi (resta contraddetta dal modello, si riscrive coi giri 3-6);
`soggetti-e-ruoli-anagrafici`, `gestione-degli-indirizzi` coerenti (oggetti in comune col provisioning, regole
invariate). Le pagine `manual/` di `fn_crea_risorsa_umana` e `fn_crea_operatore` prendono il nome nuovo.
- ⚠️ Rischio dichiarato: su un database nato da zero `script.fn_pgtap_set_contesto_operatore()` costruisce un utente
  tecnico come operatore di contesto. Un test che lo fa SUPER_ADMIN si ferma con `E_SUPER_ADMIN_SU_VESTE_TECNICA`. I
  test che lo fanno li ho cercati per nome; la corsa intera di Tid è la prova.

**L'apply** (Tid, dbdev, 2026-11-26): verde dopo due correzioni che la prova da owner non poteva vedere.

- **L'ordine delle preCondition.** Il provisioning chiedeva `fn_crea_operatore`, che nasceva nel numero dopo:
  l'apply si è fermato. I due file, non ancora applicati, si sono scambiati di numero (`-68` la funzione, `-69` il
  provisioning).
- **Il runner app.** Il ramo `p_persona` del `-71` chiamava `script.fn_applica_user_emittenti_scope`, che l'app non
  esegue: ogni test con `p_persona` si fermava con «permesso negato». Il `-73` passa dal verbo, con
  `dbops.fn_pgtap_sposta_scope_operatore`.
- **Due test RLS del giro 10-ter** (`brief-db-porte-aperte-dalla-sola-guc` §10-ter, sessione parallela):
  `rls/test-rls-fatture-satelliti-functional` e `rls/test-rls-fondi-fattura-source-functional` toglievano l'azienda
  all'operatore per il caso «whitelist vuota», che dal `20261125-74` si rifiuta. Il caso ora è di un secondo operatore
  nato senza azienda, come negli altri tredici file di quel giro.
- Suite pgTAP di Tid: verde. Doc auto-generata rigenerata da Tid.

### Giri 3-6 — Il modello dell'area clienti

1. **S64**: `fn_stato_veste`, che cosa vuol dire `ATTIVO` (proposta del brief anagrafiche: resta «accesa», e la
   lista mostra l'utilizzabilità a parte);
2. **la veste cliente unica** (`CLIENTE`, D-M4) e l'indice «una veste accesa per credenziale e soggetto» (D-M7,
   D-M8); il segno della revoca segue la coppia nuova;
3. **l'iscrizione da sé** come verbo DB, sopra `fn_crea_cliente`, che si ferma su una coppia revocata; aspetta
   l'emittente del cliente iscritto da sé (Tid);
4. **il ritiro dei rami `SHOP_CUSTOMER`**, con la sezione «Garanzie ritirate»; la ricevuta aspetta D-M6.

S67 è chiusa dall'analisi (la veste cliente nasce spenta).

---
{% include-markdown "signature-core.md" %}
