# Brief DB — magazzino: tutte le scritture passano da un verbo

> **Chi scrive:** team DB (`dev/db-tid`), 2026-10-03. **A chi:** Tid (decisioni,
> §3), poi team DB; 🔵 richieste a BE in §7, da fare nello stesso giro di PR.
>
> **Origine.** La **D-P4** del
> [brief del pannello](../work-done/brief-db-pannello-config-verbo-generico.md)
> (Tid, 2026-09-25): *«`magazzini` e `ubicazioni`: un brief a sé del cantiere
> magazzino, con i loro verbi»*. Quel brief non era mai stato scritto; è emerso
> chiudendo il [brief del modello](../work-done/brief-db-permesso-nel-verbo-di-scrittura.md)
> il 2026-10-03. Il modello sta nella
> [guida dei permessi §7.4](../../guide/architettura-permessi-e-autorizzazioni.md#74-il-permesso-nel-verbo-di-scrittura).
>
> **Stato al 2026-10-03:** 📝 **bozza, cinque decisioni a Tid** (§3). Già fatto in
> questo giro: la dichiarazione «dominio a metà» nella guida del dominio
> (`dbzero/magazzino/_dominio-magazzino.md`, §«La porta»), che la regola chiedeva
> da subito, a prescindere dalle decisioni.
>
> **Perimetro:** le tabelle di `magazzino` che l'applicazione può ancora scrivere
> da sola. ⛔ Fuori: il registro e le causali (già chiusi), `vendite` (brief suo),
> qualunque cambio delle regole di dominio — chi può fare cosa resta identico,
> cambia **dove** si controlla.

---

## 0. In due parole, senza tecnicismi

Il magazzino è il primo dominio che doveva **nascere** con il permesso controllato
dal database: ogni scrittura passa da una funzione che prima guarda se chi agisce
ne ha diritto, e l'applicazione non può scrivere le tabelle da sola. Per il
registro della merce è vero. Per il resto no: oggi l'anagrafica dei magazzini, le
ubicazioni, i lotti e le bozze di inventario e rettifica le scrive il backend
direttamente, e se il backend sbaglia un permesso il database esegue.

Questo brief chiude il resto, così che la sezione «dominio a metà» della guida si
riduca a una riga.

## 1. Il punto di partenza — letto il 2026-10-03

Fatti datati, dalla struttura e dal codice. Descrivono il punto di partenza, non
decidono la forma.

**Chiuse all'app** (loop dei grant `90_end/ci_apply/20260205-41`,
`v_tabelle_sola_lettura_app`): `movimenti`, `valore_giacenza`, `movimenti_attesi`,
`causali`. Il passaggio di un documento interno a `POSTED`, e le righe di un
documento in `CONFIRM`, sono già chiusi dalla GUC transazionale aperta solo dentro
un verbo (D-V1, `script.fn_is_proprietario_tabella`).

**Ancora scrivibili dall'app**, con il loro scrittore di oggi:

| Tabella | Perimetro | Scrittore |
| --- | --- | --- |
| `magazzini` | RLS diretta sull'emittente + guard `trgfn_guard_emittente_scope` | `anagrafiche_magazzino_repository.py`: INSERT, UPDATE per delta (nessun DELETE: si disattiva) |
| `ubicazioni` | RLS via il magazzino (`fn_scope_ef_whitelist_via_magazzino`), **nessun guard di perimetro** | idem |
| `lotti` | nessuna RLS: un lotto è dell'articolo | idem |
| `inventari`, `rettifiche` + righe | RLS via il magazzino | `magazzino_repository.py`, guidato dal registro `FAMIGLIE`: INSERT testata, cambio di stato con `UPDATE`, DELETE testata, INSERT/UPDATE/DELETE righe |
| `trasferimenti` + righe | RLS via il magazzino | nessuno dall'app (solo il verbo di posting) |
| `assets`, `eventi_assets`, le tredici tabelle di note | RLS | nessuno dall'app |

**I permessi di oggi, lato backend:** le view delle anagrafiche e dei documenti
dichiarano `area_funzionale = magazzino`, quindi scrivere chiede `TUTTO` su
Magazzino; il solo gesto «Registra» chiede l'azione `registra_magazzino`.

**Le colonne scrivibili** delle anagrafiche stanno oggi in costanti del backend
(`MAGAZZINI_COLONNE`, `UBICAZIONI_COLONNE`, `LOTTI_COLONNE`).

## 2. Il problema, sul modello

1. **Il magazzino non è «nato così»** (D-1 del modello; §7.1, punto 4: *«`REVOKE`
   all'app da subito sulle tabelle di `magazzino` e `acquisti`»*). Un dominio
   nuovo con la porta chiusa sul registro e aperta sul resto è un dominio a metà.
2. **Un errore del backend diventa una scrittura.** Un endpoint con il permesso
   dichiarato male, o un tool dell'assistente legato alla rotta sbagliata, crea un
   magazzino o modifica una bozza di inventario, e il database esegue.
3. **Le tabelle senza scrittore sono aperte per default.** `assets`,
   `trasferimenti`, le note: quando arriverà il loro primo scrittore, troverà la
   porta aperta e potrà scrivere senza verbo.

## 3. Decisioni aperte — a Tid

| # | Domanda | Opzioni | Raccomandazione |
| --- | --- | --- | --- |
| **D-M1** | Quanto chiude questo brief | **A** solo `magazzini` e `ubicazioni` (la D-P4 alla lettera) · **B** le tre anagrafiche (+ `lotti`) · **C** tutto il dominio: anagrafiche, documenti interni, e le tabelle senza scrittore chiuse subito | ⭐ **C, in due lotti.** Lotto 1: anagrafiche + chiusura delle tabelle senza scrittore (costa solo una voce nel loop). Lotto 2: i documenti interni. Con A o B la guida resta «a metà» senza una data, ed è il caso che la D-1 voleva evitare |
| **D-M2** | La forma dei verbi delle anagrafiche | **a** un verbo tipizzato per operazione (`fn_crea_magazzino(p_codice, …)`) · **b** un verbo per tabella con i dati in `jsonb`, come `fn_pannello_scrivi` | ⭐ **b.** La modifica è per delta (si scrivono solo i campi mandati), e con parametri tipizzati non si distingue «non mandato» da «messo a vuoto». È la forma che il pannello ha già |
| **D-M3** | Regola del 2: la scrittura dinamica da `jsonb` | **a** copiarla nei verbi di magazzino · **b** estrarre dal pannello un BB in `script` (tabella, id, dati, colonne ammesse → `INSERT`/`UPDATE` con `jsonb_populate_record`) usato dal pannello e dai verbi, ritirando la copia del pannello nello stesso giro | ⭐ **b.** È la seconda occorrenza della stessa logica. Il BB **non** controlla permesso né perimetro: li fa il verbo, prima di chiamarlo |
| **D-M4** | Dove stanno le colonne scrivibili delle anagrafiche | **a** restano costanti del backend · **b** una funzione DB per tabella, letta dal verbo e dal backend (stampo di `fn_pannello_colonne_scrivibili`) | ⭐ **b.** Oggi il verbo dovrebbe fidarsi di una lista che sta altrove: due sedi. Le costanti del backend si ritirano nello stesso giro |
| **D-M5** | I documenti interni (Lotto 2): verbi per famiglia o generici | **a** verbi per famiglia (`fn_crea_inventario`, `fn_crea_rettifica`, …) · **b** verbi generici sul registro delle famiglie a DB (crea/modifica/cancella testata, righe, cambio di stato), come fa già `fn_documento_interno_transizioni` | ⭐ **b.** Le famiglie sono tre (inventario, rettifica, trasferimento) con la stessa matrice: è la regola del 2 già superata. ⚠️ Il registro `FAMIGLIE` del backend diventa una seconda sede: il brief del Lotto 2 dirà come si riduce |

**Che cosa non è una decisione, perché lo dice già il modello:**

* il permesso delle operazioni semplici è il **livello** sull'oggetto (D-2, D-5):
  ogni verbo chiama `script.fn_guard_livello(utente, 'magazzino', '<tabella>',
  'TUTTO')` nella prima riga. «Registra» resta sull'azione `registra_magazzino`;
* il verbo gira `SECURITY DEFINER` del proprietario, con `search_path` bloccato;
* il **perimetro** lo rimette il verbo, perché da proprietario la RLS non lo
  filtra. Su `magazzini` c'è già il guard `trgfn_guard_emittente_scope`. Su
  `ubicazioni` e sui documenti il verbo chiama lo stesso predicato della policy
  (`fn_scope_ef_whitelist_via_magazzino`), sulla riga prima e dopo; la riga fuori
  perimetro risponde «non trovata» (no-leak), come in `fn_posta_*`;
* la postura nelle tre sedi (linee-guida-sql §11.8): loop dei grant, provisioning,
  changeSet `90_end` per dev.

## 4. Il disegno — da confermare dopo le decisioni

**Lotto 1 — anagrafiche e tabelle senza scrittore** (con C, b, b, b):

* il BB della scrittura dinamica (D-M3), con il pannello che lo adotta;
* `magazzino.fn_*_colonne_scrivibili` per le tre anagrafiche (D-M4);
* i verbi: `magazzino.fn_scrivi_magazzino(p_id, p_dati)`,
  `fn_scrivi_ubicazione(p_magazzino_id, p_id, p_dati)`,
  `fn_scrivi_lotto(p_articolo_id, p_id, p_dati)` — `p_id` vuoto = nuovo, come nel
  pannello. Nessun `DELETE`: si disattiva, come oggi;
* in `v_tabelle_sola_lettura_app`: `magazzini`, `ubicazioni`, `lotti`, e le
  tabelle senza scrittore (`trasferimenti` e righe, `assets`, `eventi_assets`, le
  note).

**Lotto 2 — documenti interni**: i verbi generici della D-M5, poi la chiusura di
`inventari`, `rettifiche` e delle loro righe. Si scrive dopo il Lotto 1, nello
stesso brief.

## 5. I passi

| Passo | Cosa | Note |
| --- | --- | --- |
| **P-0** | Censimento, prima di scrivere | sotto |
| **P-1** | Dichiarazione «dominio a metà» nella guida | ✅ **fatto il 2026-10-03** |
| P-2 | BB della scrittura dinamica, il pannello lo adotta | `20_code/script`, e `fn_pannello_scrivi` riscritto dalla doc auto-gen |
| P-3 | Colonne scrivibili e verbi delle anagrafiche | `20_code/magazzino` |
| P-4 | Postura del Lotto 1 nelle tre sedi | `90_end` + loop + provisioning |
| P-5 | Lotto 2: verbi dei documenti interni e postura | dopo P-4 |
| P-6 | Guida: la sezione «La porta» si riduce a una riga; registro dei BB | alla chiusura |

**P-0, il censimento.** Letto il 2026-10-03, da rifare sui file al momento di
scrivere. File che scrivono **direttamente** le tabelle che si chiudono:

| Tabella | pgTAP | test Django | changelog |
| --- | --- | --- | --- |
| `magazzini` | 7 | 0 | 0 |
| `ubicazioni` | 8 | 2 | 0 |
| `lotti` | 7 | 2 | 0 |
| `inventari` / righe | 22 / 22 | 2 / 0 | 3 / 3 |
| `rettifiche` / righe | 6 / 6 | 0 | 3 / 0 |
| `trasferimenti` / righe | 3 / 3 | 0 | 1 / 0 |
| `assets` | 6 | 0 | 0 |
| `eventi_assets` | 1 | 0 | 2 |

⚠️ La fixture `dbops.fn_pgtap_crea_articolo_e_magazzino` (`20260918-26`) è
**INVOKER**: col runner come app, il suo `INSERT` su `magazzini` riceverà `42501`
dopo la chiusura. È la trappola «ERRORE_FIXTURE in CI»: la fixture si porta sul
verbo (o diventa DEFINER) **nello stesso changeSet** della postura. Lo stesso
vale per ogni pgTAP del censimento che fabbrica i suoi soggetti con un `INSERT`.

## 6. I pgTAP — i casi si fabbricano

Uno per verbo, sullo stampo di `test-fn-pannello-scrivi-v1` e
`test-porta-ledger-v1`:

* senza `TUTTO` sull'oggetto ⇒ `E_PERMESSO_NEGATO`; con `TUTTO` solo su
  Configurazione ⇒ `E_PERMESSO_NEGATO` (il caso che la D-3 voleva chiudere);
* riga di un altro emittente ⇒ «non trovata», anche in modifica; un'ubicazione
  spostata in un magazzino fuori perimetro ⇒ rifiutata;
* campo non scrivibile ⇒ rifiutato col suo nome;
* come app: `INSERT`/`UPDATE … WHERE false` su ogni tabella chiusa ⇒ `42501`
  (asserzioni di privilegio: rosse da owner per costruzione, si leggono col
  runner come app);
* il pannello, dopo l'adozione del BB: la sua suite identica prima e dopo.

## 7. Richieste a BE — nello stesso giro di PR

* **R-1** `anagrafiche_magazzino_repository.py`: le tre `create_*`/`update_*`
  chiamano i verbi invece di `execute_dynamic_insert`/`update`; le costanti
  `*_COLONNE` si ritirano, e il form e la validazione leggono le funzioni DB
  (D-M4). Il 403 dell'endpoint resta (guida §7.4: *il backend chiede, non decide
  due volte*).
* **R-2** (Lotto 2) `magazzino_repository.py`: testate, righe e cambio di stato
  dai verbi; il registro `FAMIGLIE` si riduce a ciò che il DB non sa (il brief del
  Lotto 2 lo dirà).
* **R-3** i codici nuovi (se ne nascono) nelle chiavi i18n e nella tassonomia
  degli errori.

## 8. Che cosa NON entra

| Cosa | Dove |
| --- | --- |
| `vendite`: la bolla e il reso oltre la porta del registro | brief suo, da aprire |
| i verbi degli **asset** e degli eventi | con il loro primo scrittore (D-L2-l): nasceranno come verbi, perché la tabella è già chiusa |
| policy RLS di scrittura sul livello, `FORCE ROW LEVEL SECURITY` | mai (§3 e §6 del brief del modello) |
| l'apply, i pgTAP col runner, il commit | Tid |

## 9. Riferimenti

* [Guida dei permessi §7.4-7.5](../../guide/architettura-permessi-e-autorizzazioni.md#74-il-permesso-nel-verbo-di-scrittura) — il modello.
* [Brief del pannello](../work-done/brief-db-pannello-config-verbo-generico.md), D-P2 (niente RLS nel verbo generico) e D-P4.
* [Verbi con permesso di magazzino](../work-done/brief-db-magazzino-verbi-con-permesso.md) — la forma dei verbi, il perimetro rimesso dal verbo, D-V1.
* [Linee guida SQL](../../linee-guida-sql.md) §10.4 (l'utente dalla GUC), §11.8 (le tre sedi della postura).
* Guida del dominio: `dbzero/magazzino/_dominio-magazzino.md`, §«La porta».

---

## Registro

| Data | Chi | Cosa |
| --- | --- | --- |
| 2026-10-03 | DB | Prima stesura, dalla D-P4 del brief del pannello, emersa chiudendo il brief del modello. Cinque decisioni a Tid con una raccomandazione (C, b, b, b, b). P-1 fatto: dichiarazione «dominio a metà» nella guida di magazzino |
