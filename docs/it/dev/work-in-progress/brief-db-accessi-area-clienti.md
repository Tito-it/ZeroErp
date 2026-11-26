# Brief DB — Gli accessi e l'area clienti: la veste revocata, la veste cliente unica, l'iscrizione da sé

## ⏭️ Chi riparte — aggiornato al 2026-11-26

**Riparte: Tid**, con tre decisioni del giro 2 (D-G2-1 … D-G2-3, §5.1) e il range dei numeri; poi la sessione DB
costruisce il giro 2. In parallelo il team BE/FE col passo 3b (§4). Giro 1 committato il 2026-11-26 (`6440e685d8`).

| # | Chi | Che cosa | Dove | Aspetta |
| --- | --- | --- | --- | --- |
| 1 | team BE/FE | Il passo 3b: lo spegnimento e il reinvito dai verbi DB, i codici nuovi, lo stato `REVOCATA`, il censimento di chi scrive `attivo` | §4 | — |
| 2 | Tid | ~~Il via al giro 2~~ dato il 2026-11-26; D-G2-1 … D-G2-3 e il range dei numeri | §5.1 | — |
| 3 | sessione DB | Giro 2: la costruzione | §5.1 | 2 |
| 4 | sessione DB | Il passo 3c: il ritiro delle scritture dell'app, con «Garanzie ritirate» | §2.4 | 1 |
| 5 | sessione DB | Giri 3-6 (S64, la veste cliente unica, l'iscrizione da sé, il ritiro dei rami shop) | §5 | 4 |

**Decisioni aperte di Tid:** D-G2-1 (la credenziale senza vesti), D-G2-2 (i nomi `_v2`), D-G2-3 (`tecnica` fuori
dall'operatore), §5.1; per i giri successivi restano D-M6 e
D-M9 ([analisi-modello-area-clienti](analisi-modello-area-clienti.md) §7) e l'emittente del cliente iscritto da sé
([sviluppo-multi-face-da-completare](sviluppo-multi-face-da-completare.md) §3.6).
**Da committare:** questo brief (l'analisi del giro 2).

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
  - [ ] 3b — BE passa dai verbi
  - [ ] 3c — DB ritira le scritture dell'app (§2.4), con la sezione «Garanzie ritirate» compilata
- **Fase 4 — Doc**
  - [x] Guida `risorse-umane-e-accessi` (§«La revoca»), guida dei processi automatici, `manual/identita_digitali` — 2026-11-25
  - [x] Doc auto-generata rigenerata dopo l'apply (le quattro funzioni nuove, la tabella, `fn_stato_veste`, `fn_riattiva_utente_tecnico`) — 2026-11-26
  - [ ] A-6 chiuso nel brief BE accessi; riga «Accessi» di `PROJECT_CONTEXT`
- **Giro 2 — Le regole della veste e della sincronizzazione** (§5.1, T9: S5, S6, S22, S59-S63, S65, S66)
  - [x] Il via di Tid — 2026-11-26
  - [x] L'analisi sui corpi vivi (dbdev) — 2026-11-26
  - [ ] D-G2-1 … D-G2-3 e il range dei numeri (Tid)
  - [ ] 2a la sincronizzazione (S59, S5, S60); 2b i guard (S61, S62, S63); 2c i verbi di creazione (S6, S65, S66)
  - [ ] 2d i nomi `_v2` (S22), col passo BE
  - [ ] pgTAP, apply e corsa (Tid)
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
