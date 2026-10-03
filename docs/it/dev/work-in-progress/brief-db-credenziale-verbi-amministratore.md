# Brief BE → DB — Credenziale: il motivo del blocco dal DB e gli utenti di sistema

> **Chi scrive:** backend (`dev/backend-tid`), 2026-10-02. **A chi:** team DB (`dev/db-tid`);
> poi BE/FE (§7).
> **Origine:** le tre richieste rimaste aperte nel
> [brief area Accessi](../work-done/brief-db-be-fe-area-accessi.md) §8.3, che si è chiuso il
> 2026-10-02. Il loro contesto (le viste dei tab, il blocco sulla credenziale, la categoria)
> sta lì.
> **Stato (2026-10-03 sera):** ✅ **parte DB chiusa**: `20261003-01…-04` + tre CSV applicati,
> corsa pgTAP di Tid senza regressioni (§6.5). ✅ **Giro BE/FE scritto il 2026-10-03** (§8,
> `dev/backend-tid`, non committato): test verdi, presidi del cantiere verdi. Il brief si chiude
> col commit.
> R-DB-A6 è **decisa da Tid** (2026-10-02); l'analisi critica del team DB e le tre decisioni che
> ne sono uscite sono al **§5** — ⭐ **da leggere per primo**: correggono la forma della check
> (R-DB-A5) e il perimetro dei verbi (R-DB-A6) scritti nel §2.

## 1. In una riga

Il blocco di una credenziale dice **perché** è spento con un motivo che oggi compone il backend,
non il DB; i verbi dell'amministratore toccano anche gli **utenti di sistema**, che a video sono in
sola lettura; una colonna della lista «Di sistema» non si può ordinare.

## 2. Richieste al team DB

### R-DB-A5 — Il motivo del blocco lo dà il DB

**Oggi.** Il pannello della credenziale spegne «Blocca accesso» sull'ultimo super admin attivo. Il
**predicato** viene dal DB (`script.fn_check_ultimo_super_admin_attivo`, letto dal repository), ma il
**codice** del motivo (`ULTIMO_SUPER_ADMIN`) e la **chiave i18n**
(`amministrazione.accessi.blocca_reason.ultimo_super_admin`) li scrive il backend
(`amm_software/services/accessi_service.py`, debito dichiarato). È la forma che api.md
§«Capability di riga» chiede di non avere: il motivo lo produce la stessa funzione che rifiuta.

> ⚠️ **Superato in due punti dal §5.1**: la check torna l'array dei motivi della §12.5.1 (non
> `reason`/`reason_key` nudi), e la chiama la madre `fn_blocca_credenziale`, **non** il guard.

**Richiesta.** Una `script.fn_check_credenziale_bloccabile(p_auth_user_id)` → `reason`,
`reason_key` (NULL se si può bloccare), sul modello delle altre `fn_check_*`:

* la chiama il guard `trgfn_credenziali_guard_ultimo_super_admin` (o `fn_blocca_credenziale`):
  una regola, due lettori;
* la legge il backend per la capability `can_block` / `block_reason` / `block_reason_key` di
  `GET /amm-software/credenziali/<id>/`;
* i motivi sono **due**, in quest'ordine: `CREDENZIALE_DI_SISTEMA` (R-DB-A6, sotto) e
  `ULTIMO_SUPER_ADMIN`.

### R-DB-A6 — I verbi dell'amministratore rifiutano gli utenti di sistema

**Decisione di Tid (2026-10-02): sì, il DB rifiuta.**

**Oggi.** Le credenziali di categoria `SISTEMA` (`script.fn_categoria_accesso`: l'utente tecnico di
un processo) hanno a video una scheda in sola lettura, senza gesti. Una chiamata diretta all'API però
le blocca o ne tocca il secondo fattore, e bloccarne una **ferma un processo automatico** senza che
il suo pannello lo sappia.

> ⚠️ **Superato in tre punti dal §5.2-§5.4**: il blocco resta possibile **dal server** (D-1),
> `fn_imposta_totp_obbligatorio` rifiuta solo l'**accensione** e `fn_totp_disabilita_device` **non**
> rifiuta (D-2), la classe è `CONFLITTO_STATO` (D-3).

**Richiesta.** I verbi che l'amministratore usa su una credenziale **rifiutano** una credenziale
`SISTEMA` con un codice nuovo, qualunque sia la strada (video, API, script):

| Verbo | Rifiuta | Nota |
| --- | --- | --- |
| `script.fn_blocca_credenziale` | sì | Motivo anche in `fn_check_credenziale_bloccabile` (R-DB-A5) |
| `script.fn_imposta_totp_obbligatorio` | sì | |
| `script.fn_totp_disabilita_device` | sì, quando ad agire è un **altro** (amministratore) | Quando agisce la credenziale stessa la regola non cambia |
| `script.fn_sblocca_credenziale` | **no** | Una credenziale `SISTEMA` bloccata **prima** di questa regola deve potersi sbloccare: l'uscita resta aperta |

Codice proposto: `E_CREDENZIALE_DI_SISTEMA`, classe `NON_PERMESSO` (o quella che il catalogo usa per
«operazione non ammessa su questo oggetto»), in `codici_errore.csv` e `messaggi_errore.csv` (it, con
causa e soluzione). Frase proposta: «Le credenziali di sistema non si modificano da qui.» — causa
«La credenziale è quella di un processo automatico.», soluzione «Usare il pannello del processo.».

La sessione del migratore (`dbops.fn_sessione_del_migratore`), che oggi `fn_totp_disabilita_device`
ammette come uscita d'emergenza (D-T4), è manutenzione del DB e non una strada dell'applicazione:
la regola non la riguarda.

### R-DB-A4 — Lista 105, `emittente_ragione_sociale` ordinabile

`ui.lista_colonna` id 1094 (lista 105, «Di sistema»), `emittente_ragione_sociale`: `ordinabile = t`.
È NUCLEO («ragione sociale»: `gen_seed_lista --verifica-ordinamento` dice KO): chi la accende deve
poterla ordinare. Verificato il 2026-10-02 su `dev/db-tid`: oggi `ordinabile = f`.

## 3. Ordine suggerito

1. R-DB-A6 e R-DB-A5 insieme: la funzione di check nasce con i due motivi.
2. R-DB-A4, indipendente.
3. Apply e corsa pgTAP di Tid.

## 4. Ricadute BE/FE (dopo il DB)

> ⚠️ **Superato dal §7**, che è l'elenco aggiornato dopo lo sviluppo DB.

* **BE**: `accessi_service.get_credenziale` legge `fn_check_credenziale_bloccabile` e smette di
  comporre motivo e chiave (via `_MOTIVO_ULTIMO_SUPER_ADMIN`, `_CHIAVE_ULTIMO_SUPER_ADMIN`);
  `E_CREDENZIALE_DI_SISTEMA` in `error_policies_generated.py` (rigenerato) e ripiego senza
  segnaposto in `error_messages_fallback.py`; `emittente_ragione_sociale` entra in
  `ACCESSI_SISTEMA_ORDER_COLUMNS` (`accessi_repository.py`); test dei rifiuti; doc
  `api_amm_software.md` §1-bis.
* **FE**: chiave i18n del motivo nuovo (se la `reason_key` del DB è nuova); nessun gesto nuovo, la
  scheda «Di sistema» resta in sola lettura.

## 5. Analisi critica del team DB e decisioni (2026-10-03)

### 5.1 La check: la chiama la madre, nella forma §12.5.1

* **Il guard non può chiamarla.** `config.trgfn_credenziali_guard_ultimo_super_admin` è
  `AFTER ROW` e guarda lo stato **dopo**: lì la credenziale bloccata è già «non raggiungibile» e
  `fn_check_ultimo_super_admin_attivo` (stato **prima**) risponderebbe sempre `false`. La chiama
  quindi `fn_blocca_credenziale` prima di scrivere (linee-guida-sql §12.5.2); il guard **resta**
  come rete per due blocchi concorrenti, con la sua primitiva `fn_check_almeno_un_super_admin_attivo`,
  come i due gemelli su binding e identità.
* **`reason` + `reason_key` non bastano alla madre**: per sollevare le serve il `codice`. La forma
  è quella della §12.5.1 — `'[]'` se si può, altrimenti l'array ordinato
  `{codice, reason, reason_key, dettaglio, valori}` — e la madre ne solleva il primo con
  `script.fn_raise_primo_motivo_se_presente`.
* **`reason_key`**: quella di `ULTIMO_SUPER_ADMIN` è l'indirizzo che il BE usava già
  (`amministrazione.accessi.blocca_reason.ultimo_super_admin`) e non si rinomina; quella di
  `CREDENZIALE_DI_SISTEMA` è **nuova** di sicuro (§7, FE).

### 5.2 D-1 — L'uscita d'emergenza: il blocco dal server (Tid, 2026-10-03)

**Il buco.** La categoria SISTEMA contiene anche gli `API_CLIENT`, che non hanno un processo
(`processo_id` NULL in `vw_accessi_sistema`): il «pannello del processo» della frase proposta per
loro non esiste. E il blocco è il freno di sicurezza per una chiave rubata: con la regola com'era
scritta l'app lo rifiuta, e dal server non passa nemmeno (il verbo vuole un SUPER_ADMIN, senza
l'eccezione del migratore che ha `fn_totp_disabilita_device`). Restava solo un `UPDATE` a mano.

**Decisione.** Dalla **sessione del migratore** (`dbops.fn_sessione_del_migratore`) il motivo
`CREDENZIALE_DI_SISTEMA` si toglie: è la strada d'emergenza, manutenzione e non gesto dell'app.
⚠️ **Diverso da D-T4 in un punto, di proposito**: `fn_guard_super_admin` resta la prima riga anche
dal server. Lì (D-T4) nessun SUPER_ADMIN era raggiungibile; qui uno c'è sempre (anti-lockout), e
`chk_credenziali_blocco` vuole un autore (`bloccata_da NOT NULL`): chi blocca dal server dichiara
in `app.current_user_id` il SUPER_ADMIN che decide. Niente traccia in `dbops.sessioni_utente`
(servirebbe un evento nuovo nel CHECK): la riga del blocco porta già chi, quando e perché.

### 5.3 D-2 — Le uscite restano aperte (Tid, 2026-10-03)

Il principio che il brief applicava allo sblocco vale anche per il secondo fattore: si rifiuta ciò
che **ferma** il processo, non ciò che **rimedia**.

| Verbo | Su una credenziale SISTEMA |
| --- | --- |
| `fn_blocca_credenziale` | rifiuta, salvo dal server (D-1) |
| `fn_imposta_totp_obbligatorio(…, true)` | rifiuta, da ogni strada: una macchina non ha un telefono |
| `fn_imposta_totp_obbligatorio(…, false)` | **passa**: è l'uscita da un obbligo acceso per sbaglio |
| `fn_totp_disabilita_device` | **passa**: su una macchina un device esiste solo per errore |
| `fn_sblocca_credenziale` | passa (come nel §2) |

### 5.4 D-3 — Classe `CONFLITTO_STATO` (Tid, 2026-10-03)

Non `NON_PERMESSO`: chi agisce è SUPER_ADMIN e ha tutti i permessi, il limite sta nella natura
della credenziale. È la classe del motivo accanto (`E_PROFILO_ULTIMO_SUPER_ADMIN`) e di
`E_CONTABILE_ANNULLO_NON_MANUALE`. Frase chiusa; la soluzione vale anche per gli `API_CLIENT` e
nomina la strada del server.

### 5.5 Note che non hanno chiesto una decisione

* **Nessun building block nuovo**: la regola «è di sistema» è già `script.fn_categoria_accesso`;
  la check e `fn_imposta_totp_obbligatorio` la **chiamano**, non la riscrivono.
* `fn_categoria_accesso` conta anche le vesti **spente**: una credenziale con la veste di sistema
  spenta resta SISTEMA e viene rifiutata. Coerente con il tab «Di sistema».
* Nessuna tabella letta dalla check ha RLS: il motivo non dipende da chi guarda.
* L'operatore tecnico dei pgTAP esistenti (`_tec` in `test-credenziale-blocco-admin-v1` e
  `test-totp-device-verbi-v1`) è sempre **chi agisce**, mai il bersaglio: nessuna regressione
  attesa, confermato dalla prova (§6.3).

## 6. Sviluppo DB (2026-10-03)

### 6.1 ChangeSet e seed

| File | Cosa |
| --- | --- |
| `20_code/script/20261003-01-create-fn-check-credenziale-bloccabile` | la check (§5.1) |
| `20_code/script/20261003-02-update-fn-blocca-credenziale-chiama-la-check` | la madre chiama la check; il motivo di sistema cade dal server (D-1) |
| `20_code/script/20261003-03-update-fn-imposta-totp-obbligatorio-non-su-sistema` | rifiuta solo l'accensione (D-2) |
| `80_data/sql/config/codici_errore.csv` | `E_CREDENZIALE_DI_SISTEMA`, `CONFLITTO_STATO`; nella nota di `E_AUTH_CHIAMATA_NON_VALIDA` la check nuova |
| `80_data/sql/config/messaggi_errore.csv` | id 1190: «Le credenziali di sistema non si modificano da qui.» |
| `80_data/sql/ui/lista_colonna.csv` | R-DB-A4: riga 1094 `ordinabile = t` (la ricarica il mirror `20260806-15`, nessun changeSet) |

`fn_totp_disabilita_device` e `fn_sblocca_credenziale` **non** cambiano (D-2).

### 6.2 pgTAP

| File | Cosa |
| --- | --- |
| `config/test-credenziale-di-sistema-v1.sql` (nuovo, 16) | la check, il blocco, il secondo fattore, l'ultimo SUPER_ADMIN; ⭐ il test 4 prova che la madre **chiama** la check e non contiene i predicati (§12.5.2). ⚠️ I test 6-7 sono **rossi da owner**: da owner la sessione è il migratore e il blocco passa (D-1) |
| `config/test-credenziale-di-sistema-migratore-v1.sql` (nuovo, 6, `pgtap-runner: owner`) | D-1: dal server senza autore → negato; con il SUPER_ADMIN dichiarato → bloccata; secondo fattore rifiutato anche lì; sblocco |
| `script/test-rubinetto-primo-motivo-v1.sql` | test 5 da 30 a 31 (`fn_blocca_credenziale` sull'helper) |

### 6.3 Prova pre-apply (2026-10-03, scratch `zeroerp_ci`, da owner)

SQL **estratto** dai tre YAML + righe dei due registri errori **simulate** (non prova il loader),
in `BEGIN … ROLLBACK`, poi ogni pgTAP nella stessa transazione:

| pgTAP | Esito |
| --- | --- |
| `test-credenziale-di-sistema-v1` | 14/16 da owner (6-7, attesi); **16/16** con `fn_sessione_del_migratore` simulata a `false` |
| `test-credenziale-di-sistema-migratore-v1` | 6/6 |
| `test-credenziale-blocco-admin-v1` | 16/16 (il 13 ora lo solleva la madre, stesso codice) |
| `test-totp-obbligo-v1` | 15/15 |
| `test-totp-device-verbi-v1` | 27/29: 23b e 25, rossi da owner già dichiarati nel file |
| `test-rubinetto-primo-motivo-v1` | 7/7 (conteggio 31) |

`plpgsql_check` sulle tre funzioni: zero errori; un avviso «STABLE chiama VOLATILE» sulla check
(il `RAISE` del guard di parametro), la stessa forma delle check sorelle
(`fn_check_accredito_annullabile`, `fn_check_documento_interno_registrabile`).
⚠️ Gli avvisi `fk_error_log_messaggio_errore_id` nel log della prova vengono dal seed simulato,
che la connessione dblink del log non vede: dopo l'apply il messaggio è a catalogo.

### 6.4 Dopo l'apply: il presidio del catalogo messaggi (2026-10-03 sera)

`20261003-01…-03` applicati da Tid alle 17:12 (dbdev e scratch). La corsa di
`script/test-catalogo-messaggi-errore-completo.sql` è uscita **rossa al test 7**:
*«E_CREDENZIALE_DI_SISTEMA [it] ← fn_check_credenziale_bloccabile (emette 1, il messaggio ne
chiede 0)»*.

**Non è la regola, è la lettura del sorgente.** Il presidio conta i `valori` di un motivo
cercando, dopo la chiave `'valori'`, la chiamata `jsonb_build_array(` prima del `'codice'`
seguente. Il primo motivo scriveva `'valori', '[]'::jsonb`: nessuna chiamata, e lo scanner
prendeva quella che apre il motivo **successivo** (`v_motivi || jsonb_build_array(jsonb_build_object(…))`),
cioè un argomento. Il valore a runtime era giusto (`[]`).

**Correzione**: `20261003-04-update-fn-check-credenziale-bloccabile-valori-vuoti`, che riscrive i
due `valori` vuoti come `jsonb_build_array()`, la forma delle check sorelle. Il `-01` è applicato e
non si tocca. Prova: `-04` estratto in transazione ritirata sullo scratch →
`test-catalogo-messaggi-errore-completo` 7/7, `test-rubinetto-primo-motivo` 7/7,
`test-credenziale-di-sistema` 14/16 da owner (6-7, attesi). ✅ Applicato il 2026-10-03 alle 17:22.

⚠️ La prova pre-apply del §6.3 non aveva incluso questo presidio: guarda **tutte** le check, non
solo quelle del cantiere, ed è il terzo presidio trasversale da lanciare quando nasce una
`fn_check_*` con motivi.

### 6.5 Apply e corsa pgTAP (2026-10-03)

| ChangeSet | Applicato (dbdev) |
| --- | --- |
| `20261003-01` … `-03` | 2026-10-03 17:12 |
| `20261003-04` | 2026-10-03 17:22 |

Corsa pgTAP di Tid dopo il `-04`: **nessuna regressione**. ⭐ Il debito di casa verso il BE
(motivo e chiave scritti in `accessi_service`) da ora ha la sua sede a DB: il BE può leggerla.

## 7. Richieste a BE/FE (aggiornate al 2026-10-03)

* **BE**
    * `accessi_service.get_credenziale`: `can_block` / `block_reason` / `block_reason_key` dal
      **primo motivo** di `script.fn_check_credenziale_bloccabile(au.id)` (`'[]'` = si può);
      ritirare `_MOTIVO_ULTIMO_SUPER_ADMIN`, `_CHIAVE_ULTIMO_SUPER_ADMIN` e la lettura di
      `fn_check_ultimo_super_admin_attivo` nel repository.
    * `E_CREDENZIALE_DI_SISTEMA` in `error_policies_generated.py` (rigenerato): finché manca, il
      guardrail `test_error_codes_db_policy_guardrail` è rosso. Ripiego senza segnaposto in
      `error_messages_fallback.py`. Classe `CONFLITTO_STATO` → 409.
    * `emittente_ragione_sociale` in `ACCESSI_SISTEMA_ORDER_COLUMNS` **nello stesso giro** del
      seed (R-DB-A4): `gen_seed_lista --verifica-ordinamento` confronta i due lati.
    * Test dei rifiuti: blocco e accensione dell'obbligo su una credenziale SISTEMA → 409;
      spegnere l'obbligo e togliere il device passano.
    * ⚠️ **Fuori dal DB, da valutare**: il **reset password** fatto dall'amministratore su una
      credenziale di sistema passa da `fn_imposta_deve_cambiare_password`, che per costruzione non
      ha guard (la chiamano anche l'utente stesso e il pre-login). Imporre il cambio password a un
      processo lo ferma come un blocco: se l'endpoint lo permette, il rifiuto va nel BE.
    * Doc `api_amm_software.md` §1-bis.
* **FE**
    * ⛔ Chiave i18n **nuova** `amministrazione.accessi.blocca_reason.credenziale_di_sistema`, it
      ed en, **nello stesso giro**: `check_i18n_keys.py` (controllo 4) è rosso da quando la doc
      auto-gen della check viene rigenerata.
    * Nessun gesto nuovo: la scheda «Di sistema» resta in sola lettura.

## 8. Lato BE/FE — cosa è stato scritto (2026-10-03)

| Richiesta del §7 | Stato | Dove |
| --- | --- | --- |
| Capability dal primo motivo della check | ✅ `sql_lateral_primo_motivo("script.fn_check_credenziale_bloccabile(au.id)", "blocco")` nel dettaglio; il service passa la terna com'è. Ritirati `_MOTIVO_ULTIMO_SUPER_ADMIN`, `_CHIAVE_ULTIMO_SUPER_ADMIN` e la lettura di `fn_check_ultimo_super_admin_attivo` | `accessi_repository.py`, `accessi_service.py`; consumer registrato nel catalogo BB |
| `E_CREDENZIALE_DI_SISTEMA` | ✅ policy rigenerata (`CONFLITTO_STATO` → 409) e ripiego senza segnaposto | `error_policies_generated.py`, `error_messages_fallback.py` |
| `emittente_ragione_sociale` ordinabile | ✅ in `ACCESSI_SISTEMA_ORDER_COLUMNS`; `gen_seed_lista --verifica-ordinamento` da 5 liste divergenti a 4 (le 4 rimaste sono di `pagamenti`, preesistenti) | `accessi_repository.py` |
| Test dei rifiuti | ✅ sul DB vero: capability `CREDENZIALE_DI_SISTEMA`, blocco rifiutato e sblocco aperto (`test_accessi_db` 9); obbligo acceso rifiutato, spento e rimozione del device passano (`test_obblighi_e_secondo_fattore_db` 13). Con mock: 409 sul blocco (`test_accessi_views` 11) | |
| Reset password dell'amministratore | ✅ **niente da fare**: nessun endpoint dell'amministratore impone il cambio password a un'altra credenziale. Dal 2026-09-25 l'invito non tocca la password (A-1), e `set_deve_cambiare_password` si chiama solo con `False`, dopo un cambio fatto dalla persona stessa | |
| Doc | ✅ §1-bis.2-1-bis.6 e tabella errori | `api_amm_software.md` |
| FE: chiave i18n | ✅ **c'era già** (it/en, commit `1c51774e7`); `check_i18n_keys.py` pulito | |

⚠️ **Policy rigenerata con dbdev avanti rispetto a git.** Sul catalogo di dbdev
`E_KIT_QUANTITA_DISOMOGENEE` è già ritirato (R-DB-B10 del
[brief della distinta](brief-db-bom-flag-quantita-e-kit-in-fattura.md), non ancora pushato), e la
rigenerazione lo portava fra i ritirati. Quella parte è stata **tolta**: il file corrisponde al CSV
in git, cioè a ciò che la CI genera. Su dbdev, quindi, `genera_error_policies --check` e
`test_error_policies_divergenza_db` restano rossi **solo** per quel codice finché il DB non pusha
R-DB-B10; allora si rigenera.

Test: `apps.amm_software` 220 verdi (5 skip), test delle view 11/11; sul DB vero
`test_accessi_db` + `test_obblighi_e_secondo_fattore_db` 22/22; policy e ripieghi verdi a parte
la divergenza dichiarata sopra; ruff pulito.

---
{% include-markdown "signature-core.md" %}
