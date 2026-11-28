# Brief DB — Gli accessi e l'area clienti: la veste revocata, la veste cliente unica, l'iscrizione da sé

## ⏭️ Chi riparte — aggiornato al 2026-11-28

**Riparte: il team BE/FE con B5, il login «per chi» dopo il secondo fattore (§5.5.7, D-BE4-1).** B1-B4 sono fatti, verdi e committati (2026-11-28). D-BE4-1 e D-BE4-2 decise come proposto (Tid, 2026-11-28). I giri 3 e 4 sono applicati, verdi e committati (`9be82d42c`, 2026-11-28). Il piano BE/FE (§5.5.7, 2026-11-28) mette insieme le richieste del §5.4.2 e del §5.5.5, perché riscrivono la stessa lettura della scheda. Poi, col via di Tid, l'iscrizione da sé, che aspetta la proposta sull'emittente. Il passo 3c è chiuso: lato DB il 2026-11-27 (3c-1 e 3c-3
applicati, pgTAP verdi col runner di Tid), lato BE/FE lo stesso giorno (§5.3.10, committato il 2026-11-27).
⛔ **Numeri riservati al 3c: `20261127-01` … `-10`**, tutti usati; il giro 3 usa `-43` e `-44`. Il passo 3b è committato e in
`Tito-dev` (`53420a057`, PR #266).

| # | Chi | Che cosa | Dove | Aspetta |
| --- | --- | --- | --- | --- |
| 1 | ~~Tid~~ | ~~D-3c-1 … D-3c-6, e il via al 3c-1~~: decise come proposto, 2026-11-27 | §5.3.3 | — |
| 2 | ~~team BE/FE~~ | ~~R-3c-1~~ risposta del 2026-11-27, letta dal DB: §5.3.4 | §5.3.4 | — |
| 3 | ~~Tid~~ | ~~apply del 3c-1~~ (`-01` … `-08`), 2026-11-27 | §5.3.7 | — |
| 4 | ~~Tid~~ | ~~apply di `-09`, `-10` e `ci_apply`, pgTAP col runner, doc auto-generata~~: fatto, verde, 2026-11-27 | §5.3.9 | — |
| 5 | ~~Tid~~ | ~~Il commit del giro DB~~: `1405f8ce4` (PR #268) | — | — |
| 6 | ~~team BE/FE~~ | ~~La richiesta unica: il verbo di `invito_inviato_at`, i test Django sulle fixture, `REVOCATA` nel filtro~~: fatta e committata il 2026-11-27 | §5.3.10 | — |
| 7 | ~~Tid~~ | ~~D-G3-1 e il via al giro 3~~: (a), 2026-11-27 | §5.4 | — |
| 8 | ~~sessione DB~~ | ~~Giro 3 (S64): i due changeSet, il pgTAP, la doc, provati sullo scratch~~: 2026-11-27 | §5.4.1 | — |
| 9 | ~~Tid~~ | ~~Apply di `20261127-43`, `-44`; `anagrafiche/test-accessi-altri-veste-utilizzabile-v1` col runner; doc auto-generata~~: fatto, verde, 2026-11-28 | §5.4.1 | — |
| 10 | ~~Tid~~ | ~~Il commit del giro 3, col cancello del testo di catalogo~~: `9be82d42c` | — | — |
| 11 | ~~team BE/FE~~ | ~~La richiesta del giro 3: `utilizzabile` nella lista e nella scheda~~: B1, B3, 2026-11-28 | §5.4.2, §5.5.7 | — |
| 12 | ~~Tid~~ | ~~Il via al giro 4, l'indice per credenziale e soggetto~~: 2026-11-28 | §5.5 | — |
| 13 | ~~Tid~~ | ~~D-G4-1, D-G4-2~~: sì, 2026-11-28 | §5.5.4 | — |
| 14 | ~~sessione DB~~ | ~~Giro 4: changeSet, pgTAP, doc, prova sullo scratch~~: 2026-11-28 | §5.5.6 | — |
| 16 | ~~Tid~~ | ~~Apply di `20261127-48` … `-50` e dei CSV; i pgTAP del §5.5.6 col runner app; doc auto-generata~~: 2026-11-28 | §5.5.6 | — |
| 17 | ~~Tid~~ | ~~Il commit dei giri 3 e 4~~: `9be82d42c` | — | — |
| 18 | ~~Tid~~ | ~~D-BE4-1 (il login «per chi»), D-BE4-2 (l'ordine)~~: come proposto, 2026-11-28 | §5.5.7 | — |
| 19 | ~~team BE/FE~~ | ~~B1-B4, B6, B7: lista, policy, scheda dei referenti, invito, doc, test~~: 2026-11-28 | §5.5.7 | — |
| 20 | ~~Tid~~ | ~~Il commit di B1-B4~~: `529e4d05d`, 2026-11-28 | — | — |
| 15 | team BE/FE | B5: il login «per chi» (D-BE4-1), con la sua doc e i suoi test | §5.5.5 punto 2, §5.5.7 | 20 |

**Decisioni aperte di Tid:** nessuna per i giri 3 e 4 (D-BE4-1, D-BE4-2 decise il 2026-11-28). D-M9 è decisa come proposto (Tid, 2026-11-28). Per i giri successivi restano D-M6
([analisi-modello-area-clienti](analisi-modello-area-clienti.md) §7) e l'emittente del cliente iscritto da sé
([sviluppo-multi-face-da-completare](sviluppo-multi-face-da-completare.md) §3.6).
⚠️ ~~Fino al passaggio del BE l'invito si fermava con `42501` dopo la mail~~: chiuso dal 3c-2 (§5.3.10).
**Da committare:** niente. B1-B4 del §5.5.7 sono committati il 2026-11-28 (`529e4d05d`); i giri 3 e 4 del DB in `9be82d42c`, il 3c in `1405f8ce4`.

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
  - [x] 3b — BE passa dai verbi (§4.1; committato in `53420a057`) — 2026-11-26
  - [x] 3c — analisi critica sul catalogo vivo e piano (§5.3) — 2026-11-27
  - [x] 3c — R-3c-1, la risposta del BE e la lettura del DB (§5.3.4) — 2026-11-27
  - [x] 3c — D-3c-1 … D-3c-6 (Tid: come proposto) e il via al 3c-1 — 2026-11-27
  - [x] 3c-1 — DB: le aggiunte, scritte e provate sullo scratch (§5.3.7) — 2026-11-27
  - [x] 3c-1 — apply (Tid) — 2026-11-27
  - [x] 3c-3 — DB: l'app perde `UPDATE` e `DELETE`, anticipato nel giro (Tid), scritto e provato sullo scratch (§5.3.9) — 2026-11-27
  - [x] 3c-3 — apply di `-09`, `-10` (Tid), pgTAP verdi col runner — 2026-11-27
  - [x] 3c-2 — BE: la richiesta unica del §5.3.8 (§5.3.10, committato) — 2026-11-27
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
  - [x] Il ritiro di `fn_crea_operatore_v2` (`90_end/20261127-06`, §5.3.7) — 2026-11-27
- **Giri 3-6** (§5)
  - [x] Giro 3, S64: analisi e proposta (§5.4) — 2026-11-27
  - [x] Giro 3, S64: D-G3-1 (a) e il via (Tid) — 2026-11-27
  - [x] Giro 3: `-43` la vista, `-44` il COMMENT, il pgTAP, la doc, la prova sullo scratch (§5.4.1) — 2026-11-27
  - [x] Giro 3: apply, pgTAP col runner (Tid), doc auto-generata — 2026-11-28
  - [x] Giro 3: la richiesta al BE/FE (§5.4.2, B1 e B3 del §5.5.7) — 2026-11-28
  - [x] Giro 4, l'indice per credenziale e soggetto: il via (Tid) — 2026-11-28
  - [x] Giro 4: il censimento e la proposta (§5.5) — 2026-11-28
  - [x] Giro 4: D-G4-1, D-G4-2 (Tid: sì) — 2026-11-28
  - [x] Giro 4: `-48` gli indici, `-49` e `-50` i due guard, il codice, i pgTAP (due nuovi o riscritti, quattro riportati sull'operatore), la doc, la prova sullo scratch (§5.5.6) — 2026-11-28
  - [x] Giro 4: apply, pgTAP verdi col runner app, doc auto-generata (Tid) — 2026-11-28
  - [x] Giri 3 e 4: il commit del DB (`9be82d42c`) — 2026-11-28
  - [x] Giri 3 e 4, lato BE/FE: il censimento e il piano unico (§5.5.7) — 2026-11-28
  - [x] Giri 3 e 4, lato BE/FE: D-BE4-1, D-BE4-2 (Tid: come proposto) — 2026-11-28
  - [x] Giro 4, BE/FE: B1-B4, B6, B7 (§5.5.7) — 2026-11-28
  - [ ] Giro 4, BE/FE: B5, il login «per chi» (§5.5.5 punto 2)
  - [ ] l'iscrizione da sé (aspetta l'emittente); la veste cliente unica col ritiro dei rami shop

> **Chi scrive:** sessione DB (`dev/db-tid`), 2026-11-25. **A chi:** Tid; il team BE/FE per il §4.
> **Origine:** T9 di [brief-db-revisione-anagrafiche](brief-db-revisione-anagrafiche.md) §17.1 e R-4 di
> [brief-be-accessi-credenziale-e-vesti](../work-done/2026/brief-be-accessi-credenziale-e-vesti.md); il modello dei giri successivi
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
7. Nel [brief BE accessi](../work-done/2026/brief-be-accessi-credenziale-e-vesti.md) A-6 si chiude col guard (il pulsante passa da
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

### 5.3 Il passo 3c — analisi critica del 2026-11-27

Letto sul catalogo di dbdev il 2026-11-27 (`pg_proc`, `pg_trigger`, `information_schema`), dopo il giro 10-bis di
[brief-db-porte-aperte-dalla-sola-guc](../work-done/2026/brief-db-porte-aperte-dalla-sola-guc.md) (archiviato il
2026-11-27) e dopo il 3b.

#### 5.3.1 Che cosa c'è oggi

| Oggetto | Sul vivo | Che cosa vuol dire per il 3c |
| --- | --- | --- |
| `identita_digitali`, grant di `zeroerp_app` | `SELECT`, `INSERT`, `UPDATE`, `DELETE` su ogni colonna; nessuna voce nel loop `20260205-41` | la postura è ancora tutta da scrivere |
| `attivo` | `DEFAULT true` | contro «la veste nasce spenta» (S67, analisi §4) |
| `fn_accendi_veste` | INVOKER, senza guard, `EXECUTE` all'app; `UPDATE` di `attivo` | senza l'`UPDATE` dell'app si ferma: deve diventare DEFINER |
| `script.fn_riattiva_utente_tecnico` | INVOKER, guard del super admin già in testa (`-56`) | DEFINER, senza altro |
| `fn_crea_veste_portale` | INVOKER, senza guard; scrive con `script.fn_scrivi_riga_da_jsonb` | senza l'`INSERT` dell'app si ferma |
| `fn_crea_operatore`, `fn_crea_utente_tecnico`, `fn_revoca_veste`, `fn_togli_revoca_veste`, `fn_crea_primo_amministratore`, il provisioning | DEFINER | già a posto (10-bis, giro 1) |
| `fn_crea_risorsa_umana`, `script.fn_applica_crea_utente_tecnico` | INVOKER, in `v_fn_riservate` | primitive chiamate solo da DEFINER: a posto |
| `fn_crea_operatore_v2` | in `v_fn_riservate`; `pg_depend` senza dipendenti; ne parla solo un commento nel corpo di `fn_crea_auth_user` | si ritira: nessun chiamante, DB o BE (B5) |
| `vw_accessi_altri.stato_accesso` | `ATTIVO` › `PENDING` › `NON_SPEDITO` › `ELSE 'DISATTIVO'` | R-3b-1 |
| trigger della tabella | solo il guard della revoca legge il proprietario; audit e storico registrano `current_user` | coi verbi DEFINER, `user_update` e lo storico portano `zeroerp_owner` invece di `zeroerp_app` (§5.3.2) |
| pgTAP che scrivono la tabella direttamente | 28 file con `UPDATE` (`attivo`, `valido_al`, `valido_dal`, `invito_inviato_at`, `auth_user_id`), 10 con `INSERT`, 4 con `DELETE` (conteggio del 2026-11-27: dà il costo, non decide la forma) | da separare: chi gira come app si rompe al 3c-3, chi gira da owner no |

#### 5.3.2 Analisi critica

1. **`fn_accendi_veste` è chiamata da una richiesta anonima.** Il link dell'invito arriva senza JWT, e lì le GUC
   d'identità non si toccano ([contratto-guc-app](../../guide/contratto-guc-app.md), «Request anonime»). Un guard
   di permesso come quello della revoca non si può mettere. Portata a DEFINER così com'è, la funzione accende
   qualunque veste spenta e non revocata della credenziale che il BE le passa: è la stessa porta dell'`UPDATE` di
   oggi, spostata dentro un verbo. Il controllo vero è il token, e il token oggi vive tutto nel BE: l'app scrive
   `config.token_monouso` direttamente (`arwd`), e nessuna funzione DB lo consuma. Il modello giusto è un verbo che
   **consuma il token e accende nella stessa riga**. Lo stesso verbo servirebbe alla conferma dell'iscrizione
   (analisi §3.3, passo 5: «l'iscrizione e l'invito sono la stessa cosa vista da due lati»). → D-3c-1.
2. **Il loop dei grant non sa «UPDATE solo di una colonna».** Le forme sono di tabella: sola lettura,
   append-only (`SELECT, INSERT`), senza `DELETE` (§11.8). Togliere `attivo` e lasciare `invito_inviato_at` non si
   scrive nel loop. Le strade sono due: tabella chiusa con un verbo per `invito_inviato_at`, oppure una regola nel
   guard («`attivo` cambia solo dal proprietario»), come per il segno. → D-3c-3, D-3c-4.
3. **Chiudere l'`INSERT` adesso fa riscrivere `fn_crea_veste_portale` due volte.** Il giro della veste cliente
   unica la riscrive comunque (i tipi ammessi cambiano, `SHOP_CUSTOMER` sparisce). Portarla a DEFINER col guard
   adesso, e poi di nuovo, contraddice «una funzione si riscrive una volta sola» (D-AD). C'è anche un dubbio da
   sciogliere: la veste shop «nasce accesa» (R-3b-2) da un'iscrizione dello shop anonima? Se è così il guard di
   gestione la ferma. → D-3c-3, R-3c-1.
4. **R-3b-1: la posizione di `REVOCATA` cambia il significato dell'aggregato.** Il COMMENT della vista dice «il
   migliore fra le vesti». Con la proposta del BE (prima di `DISATTIVO`), una credenziale con una veste revocata e
   una spenta senza segno risulta `REVOCATA`, anche se la seconda si riapre con un invito qualunque: l'aggregato
   smette di dire «il migliore». Messo per ultimo, `REVOCATA` vuol dire «tutte le vesti sono revocate», che è la
   domanda utile al filtro: «chi è stato chiuso dall'amministratore». → D-3c-2.
5. **I test, BE e pgTAP, scrivono la veste per costruire i casi.** Sono la stessa necessità due volte: una fixture
   sola, `dbops`, DEFINER, dietro il cancello dei dati di sviluppo, come la primitiva di D-AE **a**. La usano pgTAP e
   test Django (regola del 2). I test che provano proprio «l'app non scrive» (`test-veste-revocata-v1` 4, 5, 16)
   restano diretti. → D-3c-5.
6. **I verbi DEFINER cambiano chi risulta nell'audit.** `user_update` e lo storico della veste portano
   `zeroerp_owner` dopo un'accensione o una riattivazione. È lo stesso effetto dei verbi del giro 1 e del 10-bis;
   l'utente vero lo dice la GUC. Si censiscono i lettori DB di `identita_digitali.user_update` e dello storico della
   veste nella sezione «Garanzie ritirate».
7. **L'ordine in tre passi resta quello di D-R9**: il DB aggiunge (3c-1), il BE passa (3c-2), il DB chiude (3c-3).
   Una chiusura prima del BE fa rossa la CI: i test Django sul DB vero scrivono `attivo` (R-3b-2).

#### 5.3.3 Decisioni per Tid

| # | Domanda | Proposta |
| --- | --- | --- |
| D-3c-1 | Come si protegge l'accensione dal link? (a) `fn_accendi_veste` DEFINER coi controlli di oggi, limite dichiarato, e il verbo che consuma il token nasce col giro dell'iscrizione; (b) DEFINER, e in più accende solo se la credenziale ha un token d'invito valido e non usato (chiede al BE di accendere prima di segnare il token come usato); (c) adesso il verbo `fn_accetta_invito_veste(token)`, che consuma il token e accende, col BE che riscrive l'accettazione | **(a)**. Il verbo del token si progetta una volta sola, con la conferma dell'iscrizione: il tipo di token, la credenziale che nasce alla conferma, il freno, D-M9 (con un provider la conferma via email non c'è). Il cambio di adesso è la sola testata della funzione |
| D-3c-2 | Dove sta `REVOCATA` nell'aggregato di `vw_accessi_altri`? | **Per ultimo**, dopo `DISATTIVO`: «tutte le vesti sono revocate». La proposta del BE (prima di `DISATTIVO`) toglie all'aggregato il senso di «il migliore» |
| D-3c-3 | La postura della tabella al 3c-3: (a) sola lettura, ogni scrittura da un verbo, `fn_crea_veste_portale` DEFINER col guard già adesso; (b) append-only (`SELECT, INSERT`): l'app perde `UPDATE` e `DELETE` adesso, l'`INSERT` si chiude col giro della veste cliente unica, che riscrive `fn_crea_veste_portale` una volta sola | **(b)**, con `attivo DEFAULT false` subito: un `INSERT` diretto che non lo nomina nasce spento, e uno acceso su una coppia revocata lo ferma già il guard. Resta, dichiarato, l'`INSERT` diretto di una veste accesa su una coppia non revocata, fino al giro della veste cliente |
| D-3c-4 | `invito_inviato_at`: un verbo o una regola nel guard? | **Un verbo**, `anagrafiche.fn_segna_invito_inviato(identita_id)`, DEFINER, con `fn_guard_gestione_veste` sul tipo della veste. Una regola nel guard su `attivo` lascerebbe aperta ogni altra colonna. R-3c-1: copre le quattro vesti, operatore compreso, senza toccare il guard (§5.3.4) |
| D-3c-5 | Come costruiscono le vesti i test, dopo il 3c-3? | **Una fixture `dbops`** (nome da fissare nel giro, per esempio `fn_pgtap_imposta_veste`), DEFINER, col cancello dei dati di sviluppo: stato, date, `invito_inviato_at`. La usano pgTAP e Django. In PRODUZIONE si rifiuta |

#### 5.3.4 La domanda al team BE/FE prima del 3c-1

**R-3c-1.** Per ogni chiamata di `AuthRepository.set_invito_inviato_at` e di `anagrafiche.fn_crea_veste_portale`:
in quale richiesta gira (porta, endpoint), e se c'è un utente in sessione con il permesso di gestire quel tipo di
veste. In particolare: la veste shop che «nasce accesa» (R-3b-2) nasce da un'iscrizione anonima? E il reinvio di un
invito esiste anche dal lato del cliente, senza un amministratore? L'elenco di R-3b-2 è il punto di partenza, non il
confine: se ci sono altri chiamanti, vanno nella risposta.

**La risposta del BE (2026-11-27).** Il censimento copre `backend/apps`, i test sul DB vero, i management command e
i task. Nessun command, task o job chiama i due nomi.

| Chiamata | Da dove | Chi è in sessione | Transazione |
| --- | --- | --- | --- |
| `set_invito_inviato_at` (solo da `InvitoVeste.spedisci`, se la mail è partita) | le porte d'invito e reinvio: cliente portale, shop, fornitore, e **operatore** (`InvitaOperatoreView`, `ReinviaInvitoView`), che R-3b-2 non elencava | un operatore autenticato, con le GUC | dopo il commit del token e dopo la mail, in autocommit |
| `fn_crea_veste_portale`, invito (`_ensure_identita`, `p_attivo = false`) | le tre porte d'invito esterne | un operatore | la stessa del token |
| `fn_crea_veste_portale`, veste shop accesa (`p_attivo = true`) | `ProfileActivateShopView` | **la persona stessa**, con le GUC della sua veste `CLIENTE_PORTALE`; nessun token | — |
| `fn_accendi_veste` dal link (`attiva_veste`) | `AttivazioneView`, `AttivazionePortaleView`, `AttivazioneShopView`, tutte `AllowAny` | nessuno | un solo atomic: prima il token si consuma, poi la password (solo l'invito), poi il verbo; se il verbo torna `false`, il rollback annulla tutto |
| `fn_accendi_veste` senza token | `ProfileActivateShopView`, che riaccende una veste shop spenta | la persona stessa | — |

- Il reinvio dal lato del cliente non esiste. L'iscrizione allo shop senza login (`shop/register/check-email/`) è oggi
  uno stub che risponde 501, in attesa di PR-C. Il BE chiede di prevederla.
- Test sul DB vero che R-3b-2 non elencava: `VestePortaleDbTests` (`test_creazioni_dalle_madri_db.py`) chiama
  `fn_crea_veste_portale` senza contesto operatore. `test_revoca_veste_db` e `test_operatore_altre_vesti_db` chiamano
  `attiva_identita`, con un contesto GUC non verificato.
- Lato DB: `fn_provisiona_dati_di_sviluppo` chiama tutte e due le funzioni. È DEFINER, quindi non le serve niente.

**La lettura del DB.**

1. **Il guard copre già l'operatore.** Per il tipo `OPERATORE`, `fn_guard_gestione_veste` chiama
   `fn_guard_super_admin` dal `-53` (§2.3). È lo stesso controllo dell'`AdminAPIView`. Il verbo di
   `invito_inviato_at` copre le quattro vesti senza toccare il guard. L'autocommit non cambia niente: in sessione c'è
   l'operatore. **D-3c-4 regge.**
2. **D-3c-1 (a) è l'unica delle tre che non rompe niente.** Con la (b) e con la (c), `activate-shop` si fermerebbe,
   perché riaccende senza token. La (a) tiene i due percorsi, il link anonimo e la persona stessa, e la revoca la
   ferma già il guard. L'ordine dell'atomic (il token si consuma, poi si accende, e il `false` annulla tutto) è già la
   forma del verbo che consuma il token: il giro dell'iscrizione lo porta a DB così.
3. **Il ramo «la persona stessa» non si costruisce.** Servirebbe a `activate-shop`, che il modello ritira (analisi
   §3.3: il pulsante lo sostituisce l'iscrizione). Con D-3c-3 (b), `fn_crea_veste_portale` resta INVOKER e l'`INSERT`
   resta all'app fino al giro della veste cliente. `activate-shop` e `VestePortaleDbTests` continuano a funzionare, e
   il `DEFAULT false` non li tocca: tutte e due passano `p_attivo`. **D-3c-3 (b) regge**, con un vincolo
   sull'ordine: l'`INSERT` si chiude **dopo** il ritiro di `activate-shop`, cioè dopo l'iscrizione (D-3c-6).
4. **L'iscrizione anonima la prevede il giro dell'iscrizione**, col verbo che consuma il token (D-3c-1). Il 3c non le
   chiude nessuna strada: l'`INSERT` resta aperto, e `fn_accendi_veste` non chiede un utente.
5. **`test_revoca_veste_db` e `test_operatore_altre_vesti_db`** non si rompono al 3c: con la (a)
   `fn_accendi_veste` non legge il contesto. Si rompono al 3c-3 solo i test che scrivono la tabella direttamente
   (R-3b-2), che passano alla fixture di D-3c-5.

#### 5.3.5 Il piano del 3c, a decisioni prese

**3c-1, DB (aggiunge, non toglie):**

- [x] `vw_accessi_altri`: `REVOCATA` nell'aggregato (D-3c-2), e il COMMENT (`20261127-04`) — 2026-11-27
- [x] `fn_accendi_veste` e `script.fn_riattiva_utente_tecnico` `SECURITY DEFINER`, col `search_path` fissato
      (D-3c-1); `fn_accendi_veste` dichiara nel COMMENT il limite del link anonimo (`-01`, `-02`) — 2026-11-27
- [x] `anagrafiche.fn_segna_invito_inviato` (D-3c-4), senza codici nuovi (`-03`) — 2026-11-27
- [x] la fixture delle vesti, `dbops.fn_pgtap_imposta_veste` (D-3c-5, `-05`) — 2026-11-27
- [x] `attivo DEFAULT false` (D-3c-3, `90_end/-08`), dopo il censimento: il solo scrittore senza `attivo` era
      `script.fn_applica_crea_utente_tecnico`, che lo nomina (`-07`) — 2026-11-27
- [x] il ritiro di `fn_crea_operatore_v2` (`90_end/-06`), la voce di `v_fn_riservate` e del provisioning; il
      commento in `fn_crea_auth_user` resta (`test-riferimenti-morti-v1` non lo vede) — 2026-11-27
- [x] i pgTAP (§5.3.7) — 2026-11-27
- [x] guide e pagine `manual/` (§5.3.7) — 2026-11-27
- [x] la richiesta al BE del 3c-2 (§5.3.8) — 2026-11-27
- [x] apply (Tid) — 2026-11-27; pgTAP verdi col runner, insieme al 3c-3 (§5.3.9); doc auto-generata rigenerata — 2026-11-27

**3c-2, BE/FE:** `set_invito_inviato_at` sul verbo; i test Django sul DB vero (§4.2, R-3b-2) sulla fixture;
`REVOCATA` in `STATI_ACCESSO` e in `STATI_FILTRO` di `AccessiAltriTab`, nell'ordine di D-3c-2 (il presidio
`test_uno_stato_che_la_vista_impara_entra_nel_filtro` diventa rosso all'apply del 3c-1, ed è voluto).

**3c-3, DB (chiude)** — anticipato prima del BE (Tid, 2026-11-27), §5.3.9:

- [x] `identita_digitali` nel loop dei grant, nelle tre sedi di §11.8, con la forma di D-3c-3, e il suo pgTAP di
      postura — 2026-11-27
- [x] i pgTAP che girano come app e scrivono la veste passano alle fixture; restano diretti quelli che provano il
      rifiuto — 2026-11-27
- [x] la sezione «Garanzie ritirate» (§5.3.7, §5.3.9) — 2026-11-27
- [x] `scripts/guide_coinvolte.py` sul diff, con gli esiti — 2026-11-27

#### 5.3.7 Il 3c-1 costruito (2026-11-27)

| ChangeSet | Che cosa |
| --- | --- |
| `20261127-01` (20_code) | `anagrafiche.fn_accendi_veste` SECURITY DEFINER, `search_path` fissato; corpo identico al vivo, COMMENT al presente col limite del link anonimo |
| `-02` (20_code) | `script.fn_riattiva_utente_tecnico` SECURITY DEFINER; corpo identico al vivo |
| `-03` (20_code) | `anagrafiche.fn_segna_invito_inviato(identita_id) → invito_inviato_at`: DEFINER, `fn_guard_gestione_veste` sul tipo |
| `-04` (20_code) | `anagrafiche.vw_accessi_altri`: `… NON_SPEDITO, DISATTIVO, REVOCATA`, l'`ELSE` resta `DISATTIVO`; `security_invoker` ripetuto |
| `-05` (20_code) | `dbops.fn_pgtap_imposta_veste(identita_id, campi jsonb)`: DEFINER col cancello dei dati di sviluppo; `attivo`, `valido_dal`, `valido_al`, `invito_inviato_at` |
| `-06` (90_end) | `DROP` di `fn_crea_operatore_v2`, in 90_end perché il `20261126-25` (HALT) lo conta fra le sette riservate |
| `-07` (20_code) | `script.fn_applica_crea_utente_tecnico`: la veste tecnica nomina `attivo = true` |
| `-08` (90_end) | `identita_digitali.attivo SET DEFAULT false`, in 90_end: da zero i seed di 80_data nascono col default di prima |
| loop `20260205-41`, `provision_zeroerp.sql` | la voce `fn_crea_operatore_v2` tolta da `v_fn_riservate` |

**Scostamenti dal piano.**

- Il censimento del default ha trovato `script.fn_applica_crea_utente_tecnico`, che inseriva la veste tecnica senza
  nominare `attivo`: col solo `SET DEFAULT` gli utenti tecnici nuovi sarebbero nati spenti. Si riscrive (`-07`).
- `p_vesti` di `fn_accendi_veste` resta `config.ruolo_applicativo[]`: `%TYPE[]` è sintassi nel `DECLARE`, non nella
  firma (PG 19, provato il 2026-11-27).

**Garanzie ritirate.**

| Oggetto | Che cosa i lettori davano per scontato | Lettori lato DB |
| --- | --- | --- |
| `identita_digitali.attivo DEFAULT true` | una veste inserita senza nominare `attivo` nasce accesa | `fn_applica_crea_utente_tecnico`: adeguata (`-07`). `fn_crea_risorsa_umana`, `fn_crea_veste_portale`, il provisioning, il backfill `20260419-80` e gli `INSERT` dei pgTAP nominano `attivo`: non ne dipendono |
| `fn_accendi_veste`, `fn_riattiva_utente_tecnico` INVOKER | `user_update` e lo storico della veste, dopo un'accensione, portano il ruolo dell'app | nessuna funzione né vista legge `identita_digitali.user_update` o `user_insert` (catalogo di dbdev, 2026-11-27) |

**La prova** (scratch `zeroerp_ruoli`, 2026-11-27):

- estratto degli otto changeSet eseguito per intero, catalogo identico dopo il `ROLLBACK`; i tre corpi riscritti
  confrontati col `prosrc` vivo: identici, salvo la `INSERT` del `-07`;
- `anagrafiche/test-veste-accensione-invito-fixture-v1` (nuovo): 20/20, da owner. Come per il giro 1, la corsa vera è
  quella del runner di Tid, come app;
- adeguati: `config/test-porta-tabelle-accesso-v1` (sei funzioni riservate, non più sette),
  `anagrafiche/test-vesti-sync-e-guard-v1` (caso 9: i due `_v2` non ci sono più), `dbops/test-character-n-v1` (il
  registro senza il `_v2`);
- regressione senza e con l'estratto su 29 pgTAP (gli oggetti del giro per nome, più i presidi di forma): nessun
  rosso nuovo. Rossi uguali prima e dopo, tutti della corsa da owner: `test-veste-revocata-v1`,
  `test-elimina-credenziale-v1`, `test-porta-tabelle-accesso-v1`, `test-riferimenti-morti-v1`,
  `test-viste-app-solo-select-v1`;
- guardrail statici sui nove file: verdi.

**Guide** (`scripts/guide_coinvolte.py` sui file del giro): `risorse-umane-e-accessi` **guida indietro,
aggiornata** (la veste nasce spenta, l'invito spedito, l'accensione senza permesso, l'ordine dello stato
aggregato); `pgtap-come-si-scrive-un-test` **aggiornata** (la fixture); `manual/identita_digitali`,
`manual/vw_accessi_altri`, `manual/fn_crea_operatore` **aggiornate**; `architettura-multi-face-auth` resta
contraddetta dal modello, si riscrive coi giri successivi; `contratto-guc-app` coerente (l'accensione anonima è
il caso «Request anonime»); `architettura-permessi-e-autorizzazioni`, `processi-automatici-classe-e-identita` coerenti
(verbi col guard, la riattivazione resta del super admin); le altre ventuno hanno in comune oggetti che i corpi
attraversano (emittenti, contatti, processi), con regole invariate: **coerenti**.

#### 5.3.8 La richiesta unica al team BE/FE (dopo l'apply di `-09` e `-10`)

**Chi cambia per primo**: il DB, che aggiunge (3c-1) e chiude (3c-3, anticipato: Tid, 2026-11-27, non c'è produzione). Il BE passa una volta sola, dopo l'apply. ⚠️ Fino ad allora `set_invito_inviato_at` si ferma con `42501` (permesso negato) dopo l'invio della mail, e i test Django che aggiornano o cancellano una veste sono rossi.

1. **`AuthRepository.set_invito_inviato_at` passa da `anagrafiche.fn_segna_invito_inviato(identita_id)`**, che
   ritorna il momento scritto. Permesso per tipo di veste, dall'utente della sessione (`E_PERMESSO_NEGATO`); veste
   assente `E_VESTE_NON_TROVATA`. Nessun codice nuovo.
2. **I test Django sul DB vero che scrivono una veste** con `UPDATE` (lo stato, le date, `invito_inviato_at`)
   passano a `dbops.fn_pgtap_imposta_veste(identita_id, '{"attivo": false}'::jsonb)`: solo le chiavi nominate, una
   chiave a `null` porta la colonna a `NULL`. Colonne ammesse: `attivo`, `valido_dal`, `valido_al`,
   `invito_inviato_at`, `ruolo_applicativo`, `soggetto_ruolo_id`. Per togliere una veste:
   `dbops.fn_pgtap_cancella_veste(identita_id)`. Il segno della revoca passa dai suoi verbi, e una veste revocata le
   fixture non la spostano né la cancellano. L'elenco di R-3b-2 è il punto di partenza: ⛔ **censisci ogni test che
   scrive `anagrafiche.identita_digitali` con `UPDATE` o `DELETE`**: l'app li ha persi tutti e due (`-09`), e
   l'`INSERT` resta. Se a un test serve un'altra colonna, la richiesta torna al DB tutta insieme.
3. **`REVOCATA` in `STATI_ACCESSO` e in `STATI_FILTRO` di `AccessiAltriTab`**, dopo `DISATTIVO`: la vista lo
   produce quando tutte le vesti della credenziale sono revocate. `test_uno_stato_che_la_vista_impara_entra_nel_filtro`
   diventa rosso all'apply, ed è il segnale voluto.
4. **`attivo` nasce `false`**: un `INSERT` di una veste che non nomina `attivo` nasce spento. Il codice BE non ne
   fa (R-3b-2); censisci i test che contano su una veste nata accesa senza dirlo.
5. **`fn_crea_operatore_v2` non c'è più.** Il BE non lo nomina (B5); se le policy generate lo citano ancora, si
   rigenerano.
6. **`user_update` della veste**, dopo un'accensione o una riattivazione, porta il proprietario della tabella e non
   più il ruolo dell'app. ⛔ Censisci chi legge `identita_digitali.user_update` contando sul ruolo dell'app. Lato DB
   non lo legge nessuno.

#### 5.3.9 Il 3c-3 anticipato (2026-11-27)

Tid, 2026-11-27: il 3c-3 non aspetta il BE, il sistema non è in produzione. Il BE passa una volta sola (§5.3.8).

| ChangeSet / sede | Che cosa |
| --- | --- |
| `20261127-09` (90_end) | `zeroerp_app`: `SELECT, INSERT` su `identita_digitali`, `REVOKE UPDATE, DELETE` |
| loop `20260205-41` (ci_apply) | lista nuova `v_tabelle_app_solo_insert`, con lo stesso ramo dei registri append-only: stessa postura, significato diverso (un registro non si cambia mai, le vesti dai verbi) |
| `provision_zeroerp.sql` | blocco «LE VESTI SI CAMBIANO DAI VERBI», `REVOKE UPDATE, DELETE`: l'ultima parola in CI |
| `-10` (20_code) | `dbops.fn_pgtap_imposta_veste` ammette anche `ruolo_applicativo` e `soggetto_ruolo_id`; nasce `dbops.fn_pgtap_cancella_veste`. Tutte e due rifiutano di spostare o cancellare una veste revocata (`E_VESTE_REVOCA_SOLO_DAL_VERBO`): il guard della tabella lo lascia al proprietario, e le fixture lo sono |

**Scostamento da D-3c-5**: la fixture doveva cambiare solo lo stato. Il porting ha trovato quattro casi che
provano i guard della coerenza cambiando la forma della veste (il tipo `DISABILITATO`, la veste `OPERATORE` su un
ruolo non `RIS_UMANA`, il riuso di una credenziale con la veste spostata) e due che tolgono una veste per
costruire il caso dopo. Si allarga la fixture invece di portare quei test al runner owner, che perderebbe le
altre asserzioni fatte come app.

**Garanzie ritirate.**

| Oggetto | Che cosa i lettori davano per scontato | Lettori lato DB |
| --- | --- | --- |
| `UPDATE`, `DELETE` di `zeroerp_app` su `identita_digitali` | l'app scrive la veste direttamente | funzioni: nessuna INVOKER aggiorna o cancella la tabella (catalogo di dbdev, 2026-11-27: chi la aggiorna è DEFINER; le cascate delle FK girano col proprietario). pgTAP che girano come app: 15 file, adeguati (sotto). Lato BE: §5.3.8 |
| la risposta di un `UPDATE` o `DELETE` diretto dell'app | arriva al guard col suo codice (`E_VESTE_REVOCA_SOLO_DAL_VERBO`, `E_VESTE_REVOCATA`) | ora è `42501`; il guard resta la rete del proprietario. `test-veste-revocata-v1` 4, 13, 16 adeguati |

**I pgTAP adeguati** (girano come app): `test-crea-operatore-riusa-credenziale-v1`,
`test-identita-digitali-unique-multi-veste`, `test-risorse-umane-guard-identita-attiva-v1`,
`test-super-admin-senza-scadenza-v1`, `test-sync-auth-user-is-active-multi-role`, `test-veste-operatore-spenta-v1`,
`test-veste-revocata-v1`, `config/test-elimina-credenziale-v1`, `dbops/test-automazione-attivo-eccezioni-v1`,
`script/test-fn-check-operatore-invitabile`, `script/test-fn-get-user-profile-guc-aware`,
`script/test-fn-scope-ef-whitelist`, `script/test-fn-scope-fornitore-ownership`, `script/test-fn-veste-utilizzabile-v1`,
`script/test-trgfn-guard-date-validita-v1`. Le scritture dirette restano solo dove il test prova il rifiuto. Nuovo
`anagrafiche/test-vesti-postura-app-v1` (le tre sedi); `test-veste-accensione-invito-fixture-v1` da 20 a 24 casi
(le fixture del `-10`).

**La prova** (scratch, da owner, i dieci changeSet nell'ordine di fase): estratto eseguito per intero, catalogo
identico dopo il `ROLLBACK`. Su 21 pgTAP nessun rosso nuovo dovuto ai changeSet. Due differenze, della corsa da owner
e attese: in `test-vesti-postura-app-v1` i casi 3 e 4 (da owner l'`UPDATE` passa), in `test-veste-revocata-v1` il
caso 13 (da owner l'`UPDATE` arriva al guard e non al permesso). La corsa vera è quella del runner di Tid, come app.
`test-veste-accensione-invito-fixture-v1` 24/24. Guardrail statici verdi.

**L'apply** (Tid, dbdev, 2026-11-27): `-01` … `-10` e la passata `ci_apply`; l'app ha `SELECT, INSERT` sulle vesti
e nient'altro. **pgTAP verdi col runner di Tid**, cioè come app: i casi che da owner erano rossi per costruzione
(`test-vesti-postura-app-v1` 3-4, `test-veste-revocata-v1` 4, 13, 16) sono provati davvero. Doc auto-generata
rigenerata: le pagine di `fn_segna_invito_inviato`, `fn_pgtap_imposta_veste`, `fn_pgtap_cancella_veste` ci sono, e i
link delle guide risolvono.

**Guide**: `architettura-permessi-e-autorizzazioni` **guida indietro, aggiornata** (`fn_accendi_veste` è un verbo
senza guard dichiarato, le due fixture delle vesti, la lista `v_tabelle_app_solo_insert`); `risorse-umane-e-accessi`,
`pgtap-come-si-scrive-un-test`, `manual/identita_digitali` **aggiornate**; le altre del loop dei grant (che nomina
tutte le tabelle chiuse) hanno regole invariate: **coerenti**.

#### 5.3.10 Il 3c-2 fatto dal BE/FE (sessione BE, 2026-11-27, committato)

| # §5.3.8 | Esito |
| --- | --- |
| 1 | `AuthRepository.segna_invito_inviato(identita_id) → momento scritto`, sul verbo; `set_invito_inviato_at` ritirato. In `InvitoVeste.spedisci` il rifiuto del verbo **non si ingoia**: prima un `UPDATE` senza riga finiva in un warning, ora il verbo scrive o solleva, e il permesso l'ha già chiesto `emetti` (`fn_togli_revoca_veste`) nella stessa richiesta. Mock e test adeguati, uno nuovo («il rifiuto sale») |
| 2 | Censimento in `backend/apps` (SQL su più righe e ORM): nessun `DELETE` di vesti, nessun ORM che scrive (`IdentitaDigitale` è in sola lettura). Sei test passano a `dbops.fn_pgtap_imposta_veste`: `test_login_credenziale_db` (le date), `test_revoca_veste_db` (due), `test_accessi_db`, `test_operatore_valido_al_db` (più righe, con `SELECT … FROM`), `test_commessa_testata_db`. Resta diretto `test_operatori_senza_utenti_tecnici`, che prova il rifiuto: ora pretende `42501`, perché un `DatabaseError` qualsiasi lo renderebbe verde per il privilegio e non per ciò che dice; il guard di `tecnica` lo prova `anagrafiche/test-identita-tecnica`. Nessuna colonna in più chiesta alla fixture |
| 3 | `REVOCATA` in `STATI_ACCESSO` (BE) e in `STATI_FILTRO` di `AccessiAltriTab` (FE), dopo `DISATTIVO` e prima di `NESSUNO`. `STATI_FILTRO` è scritto nell'ordine dell'aggregato e non preso da `STATO_VESTE`, che segue la singola veste (`REVOCATA` subito dopo `ATTIVO`). Il presidio a tempo `test_uno_stato_che_la_vista_impara_entra_nel_filtro` è sostituito da `test_ogni_stato_della_veste_entra_nel_filtro`, che legge gli stati dai rami del `CASE` di `fn_stato_veste` e li confronta con l'elenco; il presidio nell'altro verso (ogni stato del filtro sta nella funzione e nella vista) resta |
| 4 | Ogni `INSERT` diretto di una veste nei test nomina `attivo`: nessuno conta sul default |
| 5 | Nessun nome `_v2` nel BE, nel FE o nelle policy generate |
| 6 | Nessun lettore di `identita_digitali.user_update` nel BE: il campo è solo nel model ORM, che nessuno serializza |

Doc BE: `api_amm_software` (il filtro `stato_accesso` con `REVOCATA`), `api_invito_portale_shop` (chi scrive
`invito_inviato_at`), `api_invito_operatore`; catalogo BB L804 e L812, indice rigenerato.

**Test** (2026-11-27): i moduli toccati, quelli che importano i BB di contesto e `test_token_veste_db`,
`test_operatore_altre_vesti_db`, lanciati insieme col DB vero: 623, un rosso. Il rosso,
`IndirizziSoggettoPluraleDbTests.test_gli_obbligatori_copiati_dal_primo` (manca `FATT`), è rosso anche sul codice
di partenza (`git stash`, stessa corsa): non nasce da qui, e la causa non è indagata. Vitest di `amministrazione` e
`PortaleAccessoPanel`: 109 verdi; ruff verde.

**Guide** (`scripts/guide_coinvolte.py --base HEAD`): `risorse-umane-e-accessi` **coerente** (dice già che
`invito_inviato_at` lo scrive il verbo, e l'ordine dell'aggregato con `REVOCATA` per ultimo);
`architettura-permessi-e-autorizzazioni` e `pgtap-come-si-scrive-un-test` **coerenti** (le fixture delle vesti
«le usano anche i test Django»); le altre 45 hanno in comune solo gli oggetti che i test toccati attraversano
(documenti, magazzino, pagamenti, mail), con regole invariate: **coerenti**. mypy a cricchetto: nessun rilievo nuovo.

#### 5.3.6 I giri 3-6, riletti

- **S64** è piccolo e non aspetta niente: si può fare insieme al 3c-1, se Tid vuole.
- ⚠️ **La veste cliente unica e il ritiro dei rami shop sono lo stesso lavoro.** Fondere `SHOP_CUSTOMER` in
  `CLIENTE` toglie alle vesti shop il filtro del canale (`canale_origine = 'SHOP'` nelle policy, i perimetri
  `fn_scope_note_shop_perimetro`, il modo `ordine_shop`): fatto prima del ritiro, il privato vedrebbe ciò che
  vede il cliente del portale, cioè cambierebbe la visibilità senza volerlo. Il tipo si fonde **insieme** al
  ritiro dei rami, oppure dopo. → **D-3c-6** (proposta: un giro solo, «la veste cliente», che fonde il tipo, ritira
  i rami shop e riscrive `fn_crea_veste_portale` una volta; la ricevuta resta fuori finché D-M6 non è decisa).
  ⚠️ Dalla risposta a R-3c-1: quel giro chiude anche l'`INSERT` dell'app, e lo può fare solo dopo il ritiro di
  `activate-shop`, che scrive la veste dalla persona stessa. L'ordine è quindi: l'iscrizione, poi la veste cliente.
- **L'indice per credenziale e soggetto** (D-M7, D-M8) non dipende dalla fusione: si può fare da solo, prima. Cambia
  il login del BE, che oggi sceglie la veste dal solo tipo («per chi», analisi §9).
- **L'iscrizione da sé** aspetta l'emittente del cliente iscritto da sé e, per la conferma, D-M9. Porta il verbo
  che consuma il token (D-3c-1).

### 5.4 Giro 3 — S64, che cosa vuol dire `ATTIVO` (analisi del 2026-11-27)

Letto sulla doc auto-generata, rigenerata il 2026-11-27 dopo l'ultimo changeSet sui tre oggetti (`20261125-57`,
`20261127-04`).

**Il fatto.** `script.fn_stato_veste` dice `ATTIVO` quando `attivo = true`, e basta. Una veste accesa ma fuori
dalle sue date, col soggetto spento o, per l'operatore umano, col rapporto chiuso è `ATTIVO` nella lista «Altri
accessi» e nello stato accessi della scheda di cliente e fornitore, anche se non apre la porta. La porta la decide
`script.fn_veste_utilizzabile`. Il COMMENT di `fn_stato_veste` («ATTIVO (accesa)») e la guida
[risorse-umane-e-accessi](../../guide/risorse-umane-e-accessi.md) §«Lo stato della veste» (⚠️ «`ATTIVO` legge solo
`attivo`») lo dichiarano già come scelta. Quello che manca è altrove: la lista **non ha modo di mostrare** che la veste
non apre la porta. Il jsonb `vesti` di `vw_accessi_altri` porta `attivo` e le date, ma non l'utilizzabilità. Il
soggetto spento e il rapporto chiuso non si vedono da nessuna parte. La colonna `is_active` dice solo se si apre la
**credenziale**, cioè se almeno una veste è utilizzabile, e arriva con il ritardo del job orario per le date.

**Le strade.**

| | Che cosa | Che cosa cambia per chi legge |
| --- | --- | --- |
| (a) | `ATTIVO` resta «accesa». Il jsonb `vesti` di `vw_accessi_altri` prende `utilizzabile`, letto da `fn_veste_utilizzabile`. L'aggregato `stato_accesso` non cambia | si aggiunge una chiave, non cambia nessun valore. Il FE mostra «accesa, ma oggi non apre la porta» accanto allo stato |
| (b) | uno stato nuovo in `fn_stato_veste` (per esempio `SOSPESA`): la veste accesa che non è utilizzabile. `ATTIVO` vuol dire «apre la porta» | cambia il significato di `ATTIVO` per ogni lettore (lo stato accessi di `PortaleRepository`, il filtro, `STATO_VESTE` del FE, il presidio che confronta i rami del `CASE` col filtro). Lo stato diventa una funzione del tempo, mentre oggi cambia solo con una scrittura |
| (c) | niente: la scelta è già dichiarata, S64 si chiude così | la lista continua a non dire perché una veste accesa non entra |

**Proposta: (a).** Lo stato e l'utilizzabilità rispondono a due domande diverse, e la guida le tiene già separate:
*a che punto è questa veste* e *questa veste apre la porta oggi*. Fonderle, cioè la (b), fa dipendere lo stato
anche dal soggetto, dal rapporto e dal giorno. Non sarebbe più la fotografia del ciclo di vita dell'invito e della
revoca. Con la (a) ognuna resta nella sua sede: `fn_stato_veste` per il ciclo di vita, `fn_veste_utilizzabile` per
la porta. La vista le mette una accanto all'altra.

Il costo è un changeSet `20_code`: `CREATE OR REPLACE VIEW`, con le colonne invariate e una chiave in più nel
jsonb. Poi il COMMENT della vista, la pagina `manual/vw_accessi_altri` e il ⚠️ della guida, che diventa «la lista
lo mostra con `utilizzabile`». Il pgTAP costruisce i tre casi: la veste accesa e scaduta, il soggetto spento, il
rapporto chiuso. Per la scheda di cliente e fornitore, `PortaleRepository` legge `fn_stato_veste` per veste: o il BE
chiama anche `fn_veste_utilizzabile`, oppure il DB espone le due cose insieme. Lo decide la richiesta al BE, quando
il giro parte.

⚠️ Trovato leggendo, senza legame con S64: il COMMENT di `fn_veste_utilizzabile` dice «`CURRENT_DATE` sta nella sua
finestra», ma il corpo confronta con `script.fn_data_operativa()`. Il COMMENT è indietro rispetto al corpo e si
corregge nello stesso giro, col solo `COMMENT ON`.

**Guide** (`scripts/guide_coinvolte.py --oggetti script.fn_stato_veste anagrafiche.vw_accessi_altri
script.fn_veste_utilizzabile`):

- `risorse-umane-e-accessi`: coerente con la (a). Il ⚠️ di §«Lo stato della veste» si aggiorna nel giro;
- `architettura-multi-face-auth`: resta contraddetta dal modello dell'area clienti e si riscrive coi giri della veste
  cliente; S64 non la tocca;
- `_sincronizzazione-accesso`, `_ultimo-super-admin`: coerenti, perché leggono `fn_veste_utilizzabile` e la (a) non
  la cambia.

**D-G3-1 (Tid, 2026-11-27): (a)**, e il COMMENT di `fn_veste_utilizzabile` si corregge nel giro.

#### 5.4.1 Il giro 3 costruito (2026-11-27)

| ChangeSet | Che cosa |
| --- | --- |
| `20261127-43` (20_code) | `anagrafiche.vw_accessi_altri`: ogni voce di `vesti` prende `utilizzabile`, da `script.fn_veste_utilizzabile(idg.id)`. Il corpo è quello del `-04` (uguale al vivo) con la sola chiave nuova. Colonne e aggregato invariati, `security_invoker` ripetuto, COMMENT al presente |
| `-44` (20_code) | `COMMENT ON FUNCTION script.fn_veste_utilizzabile`: la data operativa (`script.fn_data_operativa`) al posto di `CURRENT_DATE`, come nel corpo dal `20261009-49`; via il nome del brief; i lettori riletti sul catalogo, con la vista e `ui.fn_lista_colonne_livello`, che il testo vecchio non nominava. Nessuna fase tardiva scrive questo COMMENT |

**Garanzie ritirate:** nessuna. Si aggiunge una chiave al jsonb, e nessun valore cambia. Per i lettori che
confrontano le chiavi della voce con un elenco chiuso, la richiesta è al §5.4.2.

**La prova** (scratch `zeroerp_ruoli`, 2026-11-27):

- estratto dei due changeSet eseguito per intero, catalogo identico dopo il `ROLLBACK`;
- `anagrafiche/test-accessi-altri-veste-utilizzabile-v1` (nuovo, runner app): 6/6 con l'estratto. Senza, 1/6: passa
  solo il caso 6, cioè il riassunto, che non cambia. I casi sono costruiti: veste accesa e nelle date, scaduta ieri,
  valida da domani, spenta. Non si costruiscono, e il test lo dichiara, il soggetto spento (bloccato dal guard «figli
  prima») e il rapporto chiuso, perché una credenziale con una veste `OPERATORE` non sta in questa vista. La regola
  intera resta di `script/test-fn-veste-utilizzabile-v1`;
- ⚠️ alla corsa di Tid col runner app (2026-11-27), dopo l'apply, il caso 1 è rosso e gli altri verdi. Il caso 1
  cercava `script.fn_veste_utilizzabile(idg.id)` nel testo di `pg_get_viewdef`, che però toglie lo schema se sta
  nel search_path di chi legge. L'app ha `script` nel search_path, l'owner no: la prova, che gira da owner, lo
  vedeva verde. Ora il caso 1 legge `pg_depend`, dalla regola della vista all'OID della funzione. Provato sul dbdev
  da owner e da app, `t` in tutti e due; la stessa query con una funzione che la vista non usa dà `f`;
- ⭐ dallo stesso rosso nasce `scripts/guardrail_pgtap_testo_catalogo.py` (2026-11-28, in CI dopo il preambolo). Il
  difetto era tornato almeno nove volte con la regola scritta nella guida. Il cancello prende tutte le ricadute
  registrate (14 controesempi ricostruiti) e nessuno dei 10 casi giusti: plpgsql verbatim, la tabella di
  `pg_get_triggerdef`, lo schema facoltativo, la descrizione, `pg_catalog`, il nome composto dal catalogo.
  Alla prima corsa su 1172 file ha trovato un difetto vero: il test 21 di `config/test-credenziale-login-v1`
  confrontava `oid::regprocedure::text` con le firme qualificate, e come app non poteva fallire. Ora risolve le firme con
  `to_regprocedure`, col gemello «le nuove esistono», `0 vecchie, 2 nuove` da owner e da app su dbdev. Da
  rilanciare col runner: `config/test-credenziale-login-v1`;
- regressione senza e con l'estratto, senza rossi nuovi: `test-area-accessi-v1` 17/17,
  `test-veste-accensione-invito-fixture-v1` 24/24, `test-fn-veste-utilizzabile-v1` 28/28,
  `test-comment-al-presente-v1` 8/8, `rls/test-rls-viste-security-invoker` 7/7. Restano rossi, uguali prima e dopo,
  i tre già noti della corsa da owner (§5.3.7): `test-elimina-credenziale-v1`, `test-riferimenti-morti-v1`,
  `test-viste-app-solo-select-v1`;
- guardrail statici sui due file: verdi.

**Guide** (`scripts/guide_coinvolte.py` sui tre file):

- `risorse-umane-e-accessi`: **guida indietro, aggiornata**. Il ⚠️ di §«Lo stato della veste» ora dice che la lista
  mostra `utilizzabile` accanto allo stato;
- `manual/vw_accessi_altri` e `manual/fn_veste_utilizzabile`: **aggiornate**. La chiave nuova, il test, «oggi» è la
  data operativa. Nella pagina della vista è stata tolta anche la riga «I permessi», che dava all'app `INSERT`,
  `UPDATE`, `DELETE` sulla vista: era indietro, perché il loop dei grant dà alle viste solo `SELECT`, per tipo
  (linee-guida-sql §6);
- `architettura-multi-face-auth`: resta contraddetta dal modello dell'area clienti e si riscrive coi giri della
  veste cliente. Il giro 3 non la tocca;
- `_sincronizzazione-accesso`, `_ultimo-super-admin`, `pgtap-come-si-scrive-un-test`,
  `architettura-permessi-e-autorizzazioni`: **coerenti**. Leggono `fn_veste_utilizzabile` e le fixture, che non
  cambiano;
- le altre tredici guide e cinque note hanno in comune solo gli oggetti che la fixture e la vista attraversano
  (clienti, soggetti, data operativa), con regole invariate: **coerenti**.
- Orfani dello script: `fn_credenziali`, `fn_credenziale_ha_vesti`, `fn_check_credenziale_eliminabile`,
  `fn_get_totp_device`, `fn_totp_obbligatorio`, nomi del corpo della vista che nessuna guida cita. Non nascono da
  questo giro; segnalati a Tid.

#### 5.4.2 La richiesta al team BE/FE (dopo l'apply di `-43`)

1. **Ogni voce di `vesti` in `anagrafiche.vw_accessi_altri` porta `utilizzabile`** (boolean). La lista «Altri
   accessi» lo mostra accanto allo stato: una veste `ATTIVO` con `utilizzabile = false` è accesa, ma oggi non lascia
   entrare. Il motivo (le date) sta già nella voce, in `valido_dal` e `valido_al`. Lo stato e il filtro
   `stato_accesso` non cambiano.
2. **Lo stato accessi della scheda di cliente e fornitore** (`PortaleRepository`, che legge `script.fn_stato_veste`
   per veste) prende la stessa informazione da `script.fn_veste_utilizzabile(identita_id)`, il BB che il BE chiama già
   al login. Non serve un oggetto DB nuovo. Se al BE ne serve uno, la richiesta torna al DB.
3. ⛔ **Censisci chi legge la voce di `vesti` contando su un elenco chiuso di chiavi**: serializer, OpenAPI, test che
   confrontano la voce intera, il tipo FE della voce. L'elenco qui sopra è il punto di partenza, non il confine.
4. Doc BE: `api_amm_software`, dove descrive la voce della lista; il catalogo BB FE, se la badge dello stato vive in
   un BB.

### 5.5 Giro 4 — L'indice per credenziale e soggetto (analisi del 2026-11-28)

Via di Tid il 2026-11-28. Le decisioni del modello sono già prese il 2026-11-25
([analisi-modello-area-clienti](analisi-modello-area-clienti.md) §7):

- **D-M7**: un'azienda può avere più referenti con l'accesso;
- **D-M8**: un referente può entrare per più soggetti, e la porta dei fornitori segue la stessa regola.

Questo giro le rende possibili nel DB. Non fonde i tipi di veste e non tocca i rami shop: quelli sono il giro della
veste cliente (§5.3.6).

#### 5.5.1 Che cosa c'è oggi (catalogo di dbdev, 2026-11-28)

Gli indici unici sulle vesti accese sono **due**, non uno come dice il §3.2 dell'analisi:

| Indice | Colonne, `WHERE attivo` | Che cosa vieta | Decisione che lo supera |
| --- | --- | --- | --- |
| `uq_identita_digitali_auth_user_ruolo_attivo` | credenziale, tipo | una persona referente di due aziende | D-M8 |
| `uq_identita_digitali_sr_ruolo_attivo` | ruolo anagrafico, tipo | due referenti della stessa azienda | D-M7 |

Tutti e due nascono in `00_schema/anagrafiche/20260420-01`.

#### 5.5.2 Il censimento

**La sessione porta già la veste.** Il claim `identita_id` del token diventa `app.current_identita_id`
([contratto GUC](../../guide/contratto-guc-app.md) §2). Policy, perimetri (`fn_get_identita_sr_perimetro`) e
`fn_veste_utilizzabile` leggono la singola veste: con più vesti dello stesso tipo non cambiano.

**Il segno della revoca segue già la chiave nuova.** `trgfn_identita_digitali_guard_revoca` e
`fn_togli_revoca_veste` usano la terna (credenziale, ruolo anagrafico, tipo), quella che l'indice nuovo rende
unica. Il punto 2 dell'elenco dei giri («il segno della revoca segue la coppia nuova») è quindi già vero.

Le 69 funzioni che leggono `identita_digitali` si dividono così:

| Gruppo | Funzioni | Esito |
| --- | --- | --- |
| Cercano per credenziale con `OPERATORE` scritto (risorse umane, super admin, permessi, scope dei processi, `fn_veste_di_riferimento` coi suoi due chiamanti DB e quello BE) | 24 | non cambiano: l'operatore resta uno per credenziale |
| Cercano per id della veste (`fn_accendi_veste`, `fn_revoca_veste`, `fn_segna_invito_inviato`, `fn_stato_veste`, `fn_veste_utilizzabile`, i perimetri) | — | non cambiano |
| Aggregano tutte le vesti della credenziale (`fn_categoria_accesso`, `fn_credenziale_ha_vesti`, `fn_get_credenziale_per_email`, i sync, `fn_has_identita_attiva`) | — | reggono più vesti: l'esistenza o l'elenco non dipendono dall'unicità |
| Le fixture pgTAP (`dbops.fn_pgtap_*`) | 19 | cercano l'`OPERATORE`, o la veste per id |
| **`script.fn_get_profili_accesso_applicabili`**, e chi la chiama (`ui.fn_lista_colonne_livello`, le mappe dei permessi) | 1 + lettori | ⚠️ **il punto del giro** |

⚠️ **I profili personali e le vesti dei portali.** `fn_get_profili_accesso_applicabili` raccoglie i profili per
(credenziale, tipo). I profili `AD_HOC` e `SUPER_ADMIN` sono però legati alla singola veste. Finché c'è una veste
accesa per tipo, «per credenziale e tipo» e «per veste» coincidono. Con D-M8 smettono di coincidere: un profilo
`AD_HOC` dato alla veste di Rossi Srl varrebbe anche quando la stessa persona entra come privato. Si rompe inoltre
la premessa che `script/test-fn-get-permessi-ereditati-v1` presidia: sotto una veste c'è al più un profilo per
priorità, altrimenti il `DISTINCT ON` sceglie a caso fra due profili alla pari. La guida dei legami
(`config.trgfn_profili_accesso_bindings_guard_coerenza`) oggi non vieta un `AD_HOC` su una veste dei portali.
Fatto datato: i 4 `AD_HOC` e gli 11 `SUPER_ADMIN` di dbdev stanno tutti su vesti `OPERATORE`.

**Il BE** conta sull'unicità in due percorsi:

- **la scheda del cliente o del fornitore e l'invito** (`PortaleRepository.find_identita_portale`,
  `get_stato_identita`): cercano la veste di un ruolo anagrafico per tipo, con `LIMIT 1`. Con D-M7 diventa un
  elenco di referenti;
- **il login** (`AuthRepository.find_veste_utilizzabile_per_ruoli`, `find_identita_per_ruolo`): sceglie la veste
  per credenziale e tipo con `ORDER BY id LIMIT 1`. Con D-M8 serve la scelta «per chi» (analisi §3.2 e §9).

**Chi cambia per primo: il DB.** Togliere i due divieti non rompe il BE di oggi. Una seconda veste accesa dello
stesso tipo la crea solo l'invito, e l'invito controlla prima con `find_identita_portale`. Finché il BE non passa
all'elenco, il comportamento resta quello di oggi.

#### 5.5.3 La proposta

1. **Un indice nuovo, `uq_identita_digitali_credenziale_sr_ruolo_attivo`**, su (credenziale, ruolo anagrafico,
   tipo) `WHERE attivo`: una veste accesa per persona, soggetto e tipo. Vale per ogni tipo. Le tre colonne sono
   `NOT NULL`, quindi `NULLS NOT DISTINCT` non serve (§8.4-bis). Il tipo resta nella chiave finché i tipi cliente
   non sono fusi: oggi la stessa persona ha `CLIENTE_PORTALE` e `SHOP_CUSTOMER` sullo stesso cliente (D-R6). La
   fusione dovrà unire quelle righe prima di nascere.
2. **I due indici di oggi restano, ristretti a `OPERATORE` e `API_CLIENT`** (`AND ruolo_applicativo IN
   ('OPERATORE', 'API_CLIENT')`). Un operatore resta uno per credenziale e uno per persona, e restano veri i 24
   lettori che lo danno per scontato. Il predicato elenca i tipi che **non** cambiano: la fusione dei tipi cliente
   non lo tocca, e un tipo nuovo deve comunque scrivere il suo ramo in `trgfn_identita_digitali_guard_coerenza`
   (`E_RUOLO_APPLICATIVO_NON_GESTITO`). I nomi restano, perché le colonne non cambiano. Il `COMMENT ON INDEX`
   dice la regola nuova.
3. **La guida dei legami rifiuta un profilo personale (`AD_HOC`, `SUPER_ADMIN`) su una veste che non è
   `OPERATORE`**, con un codice nuovo. Così il risolutore dei permessi resta corretto per costruzione. Il profilo
   dei portali è il `PORTALE`, legato al tipo, e la riga «non vede i dati di un altro soggetto» la decide la RLS
   sulla veste della sessione, non il profilo.
4. **I pgTAP:**
   - `anagrafiche/test-identita-digitali-unique-multi-veste` riscritto sui casi del modello: due referenti dello
     stesso cliente, una persona su due clienti, la stessa terna due volte (rifiutata), l'operatore ancora uno per
     credenziale e uno per persona;
   - `script/test-fn-get-permessi-ereditati-v1` con l'indice ristretto e la guida dei legami;
   - un test della guida dei legami.
5. **La doc:** la pagina `manual/` di `identita_digitali`, la guida `architettura-multi-face-auth` (§«Regole di
   dominio», indietro), e il presidio nel `manual/` della guida dei legami.

Nessun dato da bonificare: le vesti accese di oggi rispettano sia gli indici vecchi sia quello nuovo.

**Garanzie ritirate:** «un cliente ha al più un referente per tipo» e «una persona è referente di un solo cliente
per tipo», per i tipi dei portali. Le ritirano D-M7 e D-M8. Chi le dava per scontate è il BE, e la richiesta sta
qui sotto.

#### 5.5.4 Le decisioni del giro (Tid)

| # | Decisione | Proposta |
| --- | --- | --- |
| D-G4-1 | Il perimetro: la regola nuova vale per i portali (`CLIENTE_PORTALE`, `FORNITORE_PORTALE`, `SHOP_CUSTOMER`), mentre `OPERATORE` e `API_CLIENT` restano uno per credenziale e uno per persona? | sì (punti 1-2). ✅ **Tid, 2026-11-28: sì** |
| D-G4-2 | Un profilo personale (`AD_HOC`, `SUPER_ADMIN`) si lega solo a una veste `OPERATORE`? | sì (punto 3). L'alternativa è un risolutore dei permessi per veste invece che per (credenziale, tipo), ma tocca le mappe dei permessi del BE e non serve a nessun caso del modello. ✅ **Tid, 2026-11-28: sì** |

#### 5.5.6 Il giro costruito (2026-11-28)

| ChangeSet | Che cosa |
| --- | --- |
| `00_schema/anagrafiche/20261127-48` | nasce `uq_identita_digitali_credenziale_sr_ruolo_attivo` (credenziale, ruolo anagrafico, tipo `WHERE attivo`); `uq_identita_digitali_auth_user_ruolo_attivo` e `uq_identita_digitali_sr_ruolo_attivo` restano coi loro nomi e colonne, ristretti a `OPERATORE` e `API_CLIENT`. `COMMENT ON INDEX` sui tre |
| `20_code/config/20261127-49` | `config.trgfn_profili_accesso_bindings_guard_coerenza`: un profilo `AD_HOC` o `SUPER_ADMIN` su una veste che non è `OPERATORE` → `E_PROFILO_PERSONALE_SOLO_OPERATORE`, anche per un legame spento (il trigger non scatta su `attivo`) |
| `20_code/anagrafiche/20261127-50` | `anagrafiche.trgfn_identita_digitali_guard_coerenza`, ramo 0-quater: la veste `OPERATORE` che cambia tipo con un profilo personale legato, anche spento → lo stesso codice |
| `80_data/sql/config/codici_errore.csv`, `messaggi_errore.csv` | `E_PROFILO_PERSONALE_SOLO_OPERATORE`, `CONFLITTO_STATO`, messaggio `1571` («Un profilo %s si assegna solo a un operatore, non a una veste %s.») |

⚠️ I numeri sono `20261127-48` … `-50` e non la serie del 28. Lo script dei numeri continua dall'ultima data
usata, senza salti «di cortesia», e l'altra sessione DB aveva occupato fino a `-47`. I corpi di `-49` e `-50`
partono dall'ultima versione del changelog (`20261125-65`, `-64`), confrontata col corpo vivo di dbdev il
2026-11-28: identica. `%TYPE` su ogni variabile nuova (`v_ruolo_veste`, `v_tipo_personale`).

**Garanzie ritirate:** «un cliente ha al più un referente per tipo» e «una persona è referente di un solo cliente
per tipo», per i tipi dei portali (D-M7, D-M8). Nessuna per l'operatore. Una garanzia **nuova**: un profilo
personale sta solo su una veste `OPERATORE` (D-G4-2).

**I pgTAP:**

- `anagrafiche/test-identita-digitali-unique-multi-veste` riscritto sui casi costruiti (plan 9). Prima pescava
  clienti liberi dalla popolazione e saltava i casi se non ne trovava. Ogni caso asserisce l'indice che rifiuta,
  con `dbops.fn_pgtap_codice_errore`;
- `config/test-profilo-personale-solo-operatore-v1`, nuovo (plan 6): i due versi, la frase, il caso ammesso. Gira
  come app coi verbi veri (`fn_scrivi_profilo_accesso`, `fn_lega_profilo_identita`) dal contesto di un super admin
  costruito. Il legame spento non si costruisce (il verbo lo crea acceso), e il test lo dichiara;
- ⚠️ **quattro test erano scritti sul contratto ritirato.** Legavano un profilo `AD_HOC` a una veste
  `CLIENTE_PORTALE`, scelta per non dover costruire una persona fisica. La prova li ha trovati tutti fermati dal
  guard nuovo, e sono riportati su una veste `OPERATORE` della fixture `dbops.fn_pgtap_crea_operatore_umano`, con
  la ragione scritta in testa a ciascuno:
  - `script/test-fn-get-profili-accesso-applicabili`: «il dipendente che è anche cliente», cioè la veste cliente
    col `PORTALE` del seed e la veste operatore con l'`AD_HOC`;
  - `ui/test-ui-catalogo-liste-v1` (casi 27-28): le due vesti si scambiano il posto, e la proprietà provata («la
    veste NULL non allarga») è la stessa;
  - `ui/test-fn-resolve-lista-config` e `ui/test-fn-resolve-dashboard-config`: l'utente è l'operatore, il
    `PORTALE` della cascata è legato al tipo `OPERATORE`, il caso «nessun profilo» indossa una veste che la
    credenziale non ha. Nella dashboard l'area del widget legato ai permessi è una su cui l'operatore risulta
    `BLOCCATO` per il risolutore, non la prima che capita;
- `script/test-fn-get-permessi-ereditati-v1`: il commento della premessa dello spareggio dice ora perché regge.

**La prova** (`scripts/prova_changeset.py`, scratch `zeroerp_ruoli` da owner, `ROLLBACK`, con le due righe di
catalogo inserite da un changeSet di sola prova perché lo script non carica i CSV):

- estratto eseguito per intero; catalogo identico dopo il `ROLLBACK`;
- `test-identita-digitali-unique-multi-veste` 4/9 → **9/9**; `test-profilo-personale-solo-operatore-v1` 1/6 →
  **6/6**;
- i quattro riscritti, con l'estratto: `test-fn-get-profili-accesso-applicabili` 5/5,
  `test-fn-resolve-lista-config` 13/13, `test-fn-resolve-dashboard-config` 12/12, `test-ui-catalogo-liste-v1`
  26/34 come senza. Gli 8 rossi (9, 10, 17, 18, 20, 23, 25, 26) sono i suoi casi «come app», rossi da owner per
  costruzione; i 27-28 toccati sono verdi;
- 24 vicini senza rossi nuovi, fra cui `test-fn-get-permessi-ereditati-v1` 27/27,
  `test-profili-accesso-bindings-guard-coerenza` 9/9, `test-legami-profilo-lega-e-slega-v1` 11/11,
  `test-fn-veste-utilizzabile-v1` 28/28, `test-veste-accensione-invito-fixture-v1` 24/24,
  `test-accessi-altri-veste-utilizzabile-v1` 6/6, `test-area-accessi-v1` 17/17. `test-veste-revocata-v1` si
  interrompe uguale prima e dopo: da owner non vede la veste che il verbo cerca;
- i guardrail statici verdi, compreso quello del testo di catalogo sui due test nuovi.

**Dopo l'apply** (Tid, 2026-11-28): i due test nuovi e i quattro riscritti verdi col runner app; la doc auto-generata rigenerata.

**Le guide** (`scripts/guide_coinvolte.py` sui tre changeSet):

| Guida o nota | Esito |
| --- | --- |
| `architettura-multi-face-auth` | **indietro, aggiornata**: le regole di dominio (una veste per soggetto e tipo; l'operatore uno per credenziale e per persona) e il §4.2 (il profilo personale solo sull'operatore) |
| `architettura-permessi-e-autorizzazioni` | **indietro, aggiornata**: la risoluzione del profilo, il legame `AD_HOC` solo su `OPERATORE` |
| `risorse-umane-e-accessi`, `contratto-guc-app`, `soggetti-e-ruoli-anagrafici`, `_ultimo-super-admin`, `_sincronizzazione-accesso`, `_guard-di-ruolo` | coerenti: parlano della veste per id, del `SUPER_ADMIN` sull'operatore, del ruolo anagrafico |
| le altre dieci | coerenti: citano solo `fn_log_and_raise_error` o `soggetti_ruoli` |

Le pagine `manual/`: `identita_digitali` (gli indici, i test, la nota di migrazione), `profili_accesso_bindings`
e `trgfn_profili_accesso_bindings_guard_coerenza`. Quest'ultima era indietro anche dal giro 2: non nominava il
`SUPER_ADMIN`, la veste tecnica e il codice del profilo assente.

#### 5.5.5 La richiesta al team BE/FE (dopo l'apply)

1. **La scheda del cliente e del fornitore mostra i referenti**, non un referente. `find_identita_portale` e
   `get_stato_identita` passano da «la veste di questo ruolo e tipo» a un elenco, ciascuna voce col suo stato.
   L'invito di un secondo referente non è più un duplicato: lo è solo se la stessa credenziale ha già una veste di
   quel tipo su quel soggetto.
2. **Il login fa scegliere «per chi»** quando le vesti utilizzabili dello stesso tipo sono più d'una
   (`find_veste_utilizzabile_per_ruoli`, `find_identita_per_ruolo`). La veste scelta va nel token come oggi, una
   per volta, e il cambio di soggetto è una sessione nuova o un cambio esplicito di veste (analisi §9).
3. **Censimento chiuso** dei punti del BE e del FE che cercano una veste con (ruolo anagrafico, tipo) o con
   (credenziale, tipo) e prendono la prima riga: i due sopra sono quelli trovati dal DB, ma l'elenco completo lo fa
   il team.
4. **Il codice nuovo `E_PROFILO_PERSONALE_SOLO_OPERATORE`** (`CONFLITTO_STATO`) entra nel generato delle policy
   degli errori (`error_policies_generated.py`).
5. **Il pannello dei profili** (amministrazione software): un profilo `AD_HOC` o `SUPER_ADMIN` si propone solo per
   le vesti `OPERATORE`. Il DB rifiuta le altre con il codice del punto 4.
6. La doc BE dei percorsi toccati.

#### 5.5.7 Il piano del BE/FE per i giri 3 e 4 (sessione BE, 2026-11-28)

Letti gli indici BB backend e frontend per intero; `scripts/guide_coinvolte.py` sui file del piano. Le richieste del
§5.4.2 e del §5.5.5 si fanno in un piano solo, perché il punto 2 del §5.4.2 (l'utilizzabilità nella scheda) e il
punto 1 del §5.5.5 (la scheda con i referenti) riscrivono la stessa lettura, `PortaleRepository.get_stato_identita`:
scritta una volta sola, nasce già come elenco con `utilizzabile` per voce.

**Il censimento (§5.5.5 punto 3, §5.4.2 punto 3), sul codice del 2026-11-28.** La ricerca copre SQL e ORM in
`backend/apps` fuori dai test, e il FE.

| Punto | Che cosa cerca | Esito |
| --- | --- | --- |
| `PortaleRepository.find_identita_portale` | (ruolo anagrafico, tipo), `LIMIT 1` | **cambia**: la usano `_ensure_identita`, `_disattiva_veste_common`, `ProfileActivateShopView` |
| `PortaleRepository.get_stato_identita` | (ruolo anagrafico, tipo), `LIMIT 1` | **cambia**: diventa l'elenco dei referenti (B4) |
| `InvitoPortaleService._ensure_identita` | la veste del ruolo; una veste di un'altra credenziale è un errore («collegata a un altro utente») | **cambia**: è il divieto che D-M7 ritira. Si cerca per (credenziale, ruolo anagrafico, tipo) |
| `InvitoPortaleService._disattiva_veste_common` | la veste del ruolo e tipo | **cambia**: si spegne la veste di **un** referente, per `identita_id` |
| `ProfileActivateShopView` | la veste shop del ruolo della sessione | **cambia**: con due referenti, il secondo troverebbe la veste del primo e si fermerebbe. Si cerca per (credenziale della sessione, ruolo, tipo). Si ritira col giro della veste cliente |
| `AuthRepository.find_veste_utilizzabile_per_ruoli` | (credenziale, tipi della porta), `ORDER BY id LIMIT 1` | **cambia**: il login «per chi» (B5) |
| `AuthRepository.find_identita_per_ruolo` | (credenziale, tipo) | non ne dipende: è già un elenco, e la chiama solo l'invito dell'operatore col tipo `OPERATORE` |
| `PermissionResolver.get_ruolo_applicativo`, ripiego senza GUC | (credenziale), `ORDER BY id LIMIT 1` | non ne dipende: ritorna il **tipo**, che fra due vesti dello stesso tipo è lo stesso |
| `AuthRepository.get_nomi_credenziale` (saluto delle email, firma «invitato da») | (credenziale), l'operatore prima, poi la veste accesa più vecchia | non ne dipende: è il nome della credenziale, non della veste. Il saluto di un referente col nome di un'azienda c'era già con una veste sola |
| `endpoint_helpers`, `amm_software_repository` (`_VESTE_OPERATORE`), `permissions_cache` | la veste `OPERATORE` | non ne dipendono: l'operatore resta uno per credenziale (D-G4-1) |
| FE `PortaleAccessoPanel`, `WebAccessiBadge`, `portaleAdminApi` | una veste per tipo (`portale`, `shop`) | **cambiano** con B4 |
| La voce di `vesti` in `vw_accessi_altri` | BE: `v.*` passato com'è; OpenAPI: un `DictField`; test: nessuno confronta la voce intera; FE: nessun tipo della voce | nessun elenco chiuso di chiavi. `utilizzabile` arriva al FE senza toccare il BE |

**Il punto 5 del §5.5.5 non chiede codice.** Nessun pannello dell'applicazione lega un `AD_HOC`; il `SUPER_ADMIN` lo
lega solo `AmmSoftwareRepository._set_super_admin_binding`, sulla veste `OPERATORE` (`_VESTE_OPERATORE`).

**Regola del 2.** La veste per (credenziale, ruolo anagrafico, tipo) serve a tre punti (`_ensure_identita`,
`ProfileActivateShopView`, e il riuso al reinvio): nasce come metodo unico di `PortaleRepository`, al posto di
`find_identita_portale`, che si ritira. Non c'è una prima copia da estrarre: è la stessa lettura detta una volta.

| Blocco | Punti | Che cosa |
| --- | --- | --- |
| B1 | §5.4.2 1, 4 | «Altri accessi»: la veste accesa con `utilizzabile = false` porta nel badge l'icona e il tooltip «accesa, oggi non lascia entrare»; il drawer lo dice sotto la veste, con le date. OpenAPI e `api_amm_software` nominano `utilizzabile` |
| B2 | §5.5.5 4 | Policy rigenerate dal catalogo, ripiego senza `%s` per `E_PROFILO_PERSONALE_SOLO_OPERATORE` |
| B3 | §5.5.5 1, §5.4.2 2 | `PortaleRepository`: l'elenco dei referenti per (ruolo, tipo), ogni voce con stato (`fn_stato_veste`), `utilizzabile` (`fn_veste_utilizzabile`), credenziale ed email; la veste per (credenziale, ruolo, tipo); `find_identita_portale` ritirato |
| B4 | §5.5.5 1 | `InvitoPortaleService`: `get_stato_accessi_*` rende per tipo l'elenco dei referenti; l'invito di un'email nuova sullo stesso cliente è un referente in più, la stessa credenziale è un reinvio, la veste accesa della stessa credenziale resta l'errore di oggi; la disattivazione prende `identita_id`. FE: `PortaleAccessoPanel` con l'elenco per tipo, le azioni per referente, «Invita un referente»; `WebAccessiBadge`. `ProfileActivateShopView` sulla veste della sessione |
| B5 | §5.5.5 2 | Il login «per chi»: D-BE4-1 |
| B6 | §5.5.5 6 | Guide: `architettura-multi-face-auth` §7.3 («la veste la sceglie l'endpoint» è **indietro**: con D-M8 la sceglie anche la persona) e §8.1 (i referenti, la disattivazione per veste); `risorse-umane-e-accessi` §«Lo stato della veste». Manuali BE: `api_invito_portale_shop`, `api_multi_veste_token`, `api_amm_software`. Catalogo BB BE L326, L814, L816, L817, L818; FE L338 se serve; indici rigenerati |
| B7 | — | Test dei soli moduli toccati, col DB vero per i casi costruiti: due referenti sullo stesso cliente, una persona su due clienti, la veste accesa ma scaduta nella scheda |

**Le decisioni di Tid per il piano:**

| # | Decisione | Proposta |
| --- | --- | --- |
| D-BE4-1 | Come si sceglie «per chi» al login | **dopo la password e dopo il secondo fattore**: se le vesti utilizzabili della porta sono più d'una, la risposta non porta i token ma la scelta, con una sfida firmata (lo stesso BB del secondo fattore) e l'elenco dei soggetti; un secondo passo con la sfida e l'`identita_id` apre la sessione. L'elenco dei soggetti non si mostra a chi ha solo la password. In sessione, «Entra per un altro soggetto» apre una sessione nuova (`sid` nuovo), come il cambio di emittente dell'operatore |
| D-BE4-2 | L'ordine | due commit: **prima B1-B4** (lista, policy, scheda, invito), **poi B5** (il login), che tocca l'ingresso di tutte e due le porte esterne |

✅ **Tid, 2026-11-28: D-BE4-1 e D-BE4-2 come proposto.**

**Esiti di B1-B4, B6, B7 (sessione BE, 2026-11-28, committati).** B5, il login «per chi», è il secondo commit.

| Blocco | Esito |
| --- | --- |
| B1 | `vesteFermaOggi` (FE, `core/utils/veste.js`, nuovo, con lo spec): vero solo per una veste `ATTIVO` con `utilizzabile = false`, e una chiave assente non è un rifiuto. Nato con tre consumatori (il badge di «Altri accessi», `AccessoAltroDrawer`, il pannello della scheda): la veste ferma tiene il colore del suo stato e prende `STATUS_ICONS.BLOCCATO`, il tooltip e la frase `amministrazione.accessi.veste_ferma_oggi`, con le date. OpenAPI della lista e `api_amm_software` nominano `utilizzabile`. Il BE non cambia: passa `v.*` com'è |
| B2 | `error_policies_generated.py` rigenerato: il diff è il solo `E_PROFILO_PERSONALE_SOLO_OPERATORE`, già nel CSV committato (DB allineato a git); ripiego senza `%s` |
| B3 | `PortaleRepository.list_referenti` (l'elenco, con `identita_id` facoltativo per il perimetro) e `find_veste_credenziale` (la terna); `find_identita_portale` e `get_stato_identita` ritirati |
| B4 | `get_stato_accessi_*` rende `{portale: [voce], shop: [voce], email_suggerita}`: elenco vuoto al posto di `NESSUNO`. `_ensure_identita` cerca per credenziale: il guard «collegata a un altro utente» si ritira, perché era il divieto di D-M7. Le tre disattivazioni vogliono `identita_id` nel corpo (`require_positive_int`, 400 `E_VALIDATION_INPUT`); una veste di un altro soggetto o tipo è 404 `E_VESTE_NON_TROVATA` (codice del giro 1). `ProfileActivateShopView` cerca la veste della credenziale della sessione: il suo guard anti-tampering si ritira per la stessa ragione. FE: `PortaleAccessoPanel` riscritto, una sezione ripetuta sui tipi al posto delle due copiate nel template; per referente lo stato, il fermo, «Invia invito» (spenta o revocata), «Reinvia» (invito in volo), «Disattiva»; sotto, «Invita un referente» con l'email del campo. `WebAccessiBadge` conta i referenti accesi. Chiavi i18n nuove (`portale.referenti_nessuno`, `*.btn_invita_referente`); la conferma della disattivazione nomina il referente |
| B6 | Manuale `api_invito_portale_shop` (elenco, corpo della disattivazione, secondo referente, errori); guida `architettura-multi-face-auth` §8.1 (**indietro, aggiornata**: i referenti, la disattivazione per veste); `risorse-umane-e-accessi` §«Lo stato della veste» (**indietro, aggiornata**: la scheda mostra `utilizzabile` per referente); cataloghi BB BE (`PortaleRepository`, `InvitoPortaleService`, `ProfileActivateShopView`) e FE (`vesteFermaOggi`), indici rigenerati. Il §7.3 della multi-face («la veste la sceglie l'endpoint») resta **indietro** fino a B5. Le altre guide di `guide_coinvolte.py` sui file del piano: coerenti (citano gli stessi oggetti con regole che il giro non cambia) |
| B7 | 67 test Django dei moduli toccati, col DB vero (`ZEROERP_TEST_DB_E2E=1`): `test_invito_portale_service` (nuovo: il secondo referente nasce con la sua veste; la disattivazione fuori perimetro è 404), `test_attivazione_portale_view` (la veste shop della persona della sessione; il falso utente diventa un `User` non salvato, perché il BB `utente_autenticato` vuole il tipo vero), `test_accessi_db` (costruiti due referenti accesi sullo stesso cliente, uno valido da domani: `ATTIVO` e `utilizzabile = false`), `test_revoca_veste_db`, `test_accessi_views`, `test_invito_portale_views` (nuovo, dalla `/verifica` del 2026-11-28: le tre view di disattivazione passano `identita_id` dal corpo al service col tipo dell'endpoint, e senza la chiave rispondono 400 senza toccarlo; rosso con la chiave sbagliata in una view); i presidi delle policy (`test_error_policies_classi`, `test_error_policies_divergenza_db`). Vitest: 117 su `amministrazione`, `veste.spec`, e `PortaleAccessoPanel.spec` 10/10 (nuovi: due referenti e «Disattiva» su quello della riga, la veste ferma, l'elenco vuoto). ruff, eslint, mypy (cricchetto: 0 rilievi nuovi) puliti |

### Giri 3-6 — Il modello dell'area clienti

⚠️ L'ordine qui sotto è quello dell'analisi del 2026-11-25; il §5.3.6 propone di unire i punti 2 e 4 (D-3c-6).

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
