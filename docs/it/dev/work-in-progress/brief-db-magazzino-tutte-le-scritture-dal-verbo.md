# Brief DB — magazzino: tutte le scritture passano da un verbo

> **⏭️ Chi riparte — aggiornato al 2026-11-21**
>
> **Riparte: team DB**, col P-0 e poi il Lotto 1 (§4), quando Tid dà il via.
>
> | # | Chi | Che cosa | Dove | Aspetta |
> | --- | --- | --- | --- | --- |
> | 1 | Tid | ✅ decisioni prese il 2026-11-21: D-M1 = C, D-M2 = b riformulata, D-M4 = b col gesto, D-M5 = b, D-M6 = b; D-M3 era già fatta. Resta **il via** al Lotto 1 | §3, §3-bis, §4 | — |
> | 2 | team DB | P-0 rifatto sui file, poi P-3 e P-4 (Lotto 1) | §5 | il via |
> | 3 | sessione BE | R-1, R-4 | §7 | 2 |
> | 4 | team DB | P-5 (Lotto 2), poi R-2 al BE | §5, §7 | 3 |
> | 5 | team DB | P-6, archiviazione | §5 | 4 |
>
> Decisioni aperte di Tid: nessuna (resta il via). Da committare: solo questo file (riverifica e
> decisioni del 2026-11-21).
>
> **Brief vicini verificati (2026-11-21):** `work-done/brief-db-processi-accensione-per-ambiente`
> ha costruito, senza citare questo brief, due pezzi del Lotto 1 (§3-bis, punti 1-2);
> `work-in-progress/piano-be-fe-magazzino-lotto-3` e `collaudo-in-app-magazzino-bolla-e-reso`
> rimandano qui per i seriali (asset); `analisi-db-magazzino-carico-e-scarico` e
> `analisi-db-magazzino-aggancio-documento-e-produzione` non toccano la postura. Nessuno copre il tema.
>
> ---
>
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
> **Stato al 2026-10-03** (⚠️ superato: lo stato vivo è il blocco «Chi riparte» in cima):
> 📝 **bozza, cinque decisioni a Tid** (§3). Già fatto in
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

> ⚠️ **Riverificato il 2026-11-21 (§3-bis).** I privilegi dell'app sono quelli della tabella
> qui sotto, ma: il magazzino nasce da `magazzino.fn_crea_magazzino` (BB INVOKER, 2026-10-18),
> non più da `execute_dynamic_insert`; le note sono la madre `magazzino.note` e **nove**
> partizioni, non tredici tabelle; esiste uno scrittore DB che il censimento non aveva
> (`anagrafiche.fn_provisiona_dati_di_sviluppo`).

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

> ⚠️ **D-M2 e D-M3 superate dai fatti del 2026-10-17/18**: si leggono col §3-bis, che le
> riformula. D-M6 è nuova, al §3-bis.

| # | Domanda | Opzioni | Raccomandazione |
| --- | --- | --- | --- |
| **D-M1** ✅ **DECISA da Tid il 2026-11-21: C, in due lotti** | Quanto chiude questo brief | **A** solo `magazzini` e `ubicazioni` (la D-P4 alla lettera) · **B** le tre anagrafiche (+ `lotti`) · **C** tutto il dominio: anagrafiche, documenti interni, e le tabelle senza scrittore chiuse subito | ⭐ **C, in due lotti.** Lotto 1: anagrafiche + chiusura delle tabelle senza scrittore (costa solo una voce nel loop). Lotto 2: i documenti interni. Con A o B la guida resta «a metà» senza una data, ed è il caso che la D-1 voleva evitare |
| **D-M2** | La forma dei verbi delle anagrafiche | **a** un verbo tipizzato per operazione (`fn_crea_magazzino(p_codice, …)`) · **b** un verbo per tabella con i dati in `jsonb`, come `fn_pannello_scrivi` | ⭐ **b.** La modifica è per delta (si scrivono solo i campi mandati), e con parametri tipizzati non si distingue «non mandato» da «messo a vuoto». È la forma che il pannello ha già |
| **D-M3** | Regola del 2: la scrittura dinamica da `jsonb` | **a** copiarla nei verbi di magazzino · **b** estrarre dal pannello un BB in `script` (tabella, id, dati, colonne ammesse → `INSERT`/`UPDATE` con `jsonb_populate_record`) usato dal pannello e dai verbi, ritirando la copia del pannello nello stesso giro | ⭐ **b.** È la seconda occorrenza della stessa logica. Il BB **non** controlla permesso né perimetro: li fa il verbo, prima di chiamarlo |
| **D-M4** ✅ **DECISA da Tid il 2026-11-21: b, una funzione per tabella col gesto (`'crea'`/`'modifica'`)** | Dove stanno le colonne scrivibili delle anagrafiche | **a** restano costanti del backend · **b** una funzione DB per tabella, letta dal verbo e dal backend (stampo di `fn_pannello_colonne_scrivibili`) | ⭐ **b.** Oggi il verbo dovrebbe fidarsi di una lista che sta altrove: due sedi. Le costanti del backend si ritirano nello stesso giro |
| **D-M5** ✅ **DECISA da Tid il 2026-11-21: b** (le tre famiglie, trasferimento compreso) | I documenti interni (Lotto 2): verbi per famiglia o generici | **a** verbi per famiglia (`fn_crea_inventario`, `fn_crea_rettifica`, …) · **b** verbi generici sul registro delle famiglie a DB (crea/modifica/cancella testata, righe, cambio di stato), come fa già `fn_documento_interno_transizioni` | ⭐ **b.** Le famiglie sono tre (inventario, rettifica, trasferimento) con la stessa matrice: è la regola del 2 già superata. ⚠️ Il registro `FAMIGLIE` del backend diventa una seconda sede: il brief del Lotto 2 dirà come si riduce |

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

## 3-bis. Riverifica del 2026-11-21 — che cosa è cambiato, e che cosa ne segue

Letto su dbdev (PostgreSQL 19) dalla struttura, dal catalogo e dai file. I privilegi dell'app
sulle tabelle di `magazzino` sono **identici** al §1: nessuna tabella nuova chiusa. È cambiato
ciò che sta intorno, per mano di un altro cantiere.

**1. Il BB della scrittura da `jsonb` esiste già (D-M3 fatta).**
`script.fn_scrivi_riga_da_jsonb(tabella, dati, dove, rileggi_per)` (INVOKER, `20261017-05`,
rivisto in `20261018-34`) è nato dalla 2b-1 di `work-done/brief-db-processi-accensione-per-ambiente`.
Lo usano `config.fn_pannello_scrivi` e la famiglia `fn_crea_*` (contatto, fornitore, cliente, BA,
emittente, veste portale, contratto, magazzino). ⇒ D-M3 non è più una decisione e il P-2 è fatto:
i verbi di magazzino scrivono con quel BB.

**2. Il magazzino ha già un BB di nascita, con una forma sua (D-M2 da riformulare).**
`magazzino.fn_crea_magazzino(codice, descrizione, indirizzo_dettaglio_id, campi jsonb,
emittente_fiscale_id)`, INVOKER (2026-10-18): i `NOT NULL` sono argomenti tipizzati, i facoltativi
stanno in `p_campi`, la chiave fuori elenco risponde `E_CAMPO_NON_AMMESSO`. Il backend la chiama già
(`create_magazzino`). È la forma che Tid ha scelto il 2026-10-17 per tutta la famiglia `fn_crea_*`.
Il `fn_scrivi_magazzino(p_id, p_dati)` del §4, che crea quando `p_id` è vuoto, sarebbe una
**seconda sede della nascita** accanto a `fn_crea_magazzino`. La D-M2 si riformula così:

| | Nascita | Modifica |
| --- | --- | --- |
| ✅ **DECISA da Tid il 2026-11-21** | il verbo DEFINER chiama il BB `fn_crea_*` della tabella (per ubicazione e lotto il BB nasce, stampo `fn_crea_magazzino`) | un verbo per tabella con il delta in `jsonb`, sopra `fn_scrivi_riga_da_jsonb` con `p_dove` |

L'argomento del §3 («non mandato» contro «messo a vuoto») vale per la **modifica**, non per la
nascita, dove un campo assente va al `DEFAULT`.

**3. La lista delle colonne del magazzino sta già in tre posti (D-M4 più stretta).**
`c_ammesse` dentro `fn_crea_magazzino`; `_CAMPI_MADRE_MAGAZZINO` nel repository BE (la **stessa**
lista, cioè la stessa regola copiata); `MAGAZZINI_COLONNE` nel BE (un'altra regola: i campi
modificabili). Le liste sono **due per tabella**, nascita e modifica, e ognuna ha bisogno di una
sede a DB. La D-M4 (b) resta, con due funzioni (o una con il gesto come argomento), e il BB di
nascita legge la sua invece della costante.

**4. Il perimetro in scrittura: nel verbo o sulla tabella (D-M6, nuova).**
`trgfn_guard_emittente_scope` sta su `magazzini` (modo `fiscale`), `assets`, `movimenti`,
`movimenti_attesi`, `valore_giacenza` (modo `magazzino`). **Non** sta su `ubicazioni`, `inventari`,
`rettifiche`, `trasferimenti`: lì c'è la sola RLS, che da proprietario non filtra. Il modo
`magazzino` esiste, e dal 2026-09-18 regge dentro una DEFINER (risolve l'emittente e si ferma su
una riga con un padrone).

| | Opzioni | Proposta |
| --- | --- | --- |
| **D-M6** ✅ **DECISA da Tid il 2026-11-21: b** | **a** il verbo chiama `fn_scope_ef_whitelist_via_magazzino` sulla riga prima e dopo (§3) · **b** il guard `trgfn_guard_emittente_scope('magazzino', 'magazzino_id')` sulle quattro tabelle, e il verbo tiene solo la lettura no-leak | ⭐ **b.** Con (a) il perimetro in scrittura vive in ogni verbo, e chi scriverà la tabella dopo (il ricevimento degli acquisti, un verbo di provisioning, i verbi degli asset) lo deve ricordare. Con (b) lo dice la tabella a ogni scrittore, come già sul registro. Il caso «ubicazione spostata in un magazzino fuori perimetro» lo copre il guard sul `NEW` |

**5. L'oggetto del permesso: il DB e il BE devono leggere lo stesso.**
`config.tabelle_gestibili` nomina già gli oggetti `(magazzino, magazzini)` e
`(magazzino, ubicazioni)`; nessuna riga di `config.area_model_overrides` per `magazzino`, quindi
l'area si ricava dall'`app_label`. `fn_guard_livello` legge anche l'**override dell'utente
sull'oggetto**; le view BE del magazzino dichiarano solo `area_funzionale`. Con un override
sull'oggetto, i due punti rispondono in due modi diversi. ⇒ R-4 al §7.

**6. Le fixture pgTAP hanno cambiato nome.** `dbops.fn_pgtap_crea_articolo_e_magazzino`
(`20260918-26`) non esiste più. Oggi i soggetti li fanno `dbops.fn_pgtap_crea_magazzino`
(involucro di `fn_crea_magazzino`) e `dbops.fn_pgtap_crea_lotto`, **tutte e due INVOKER**: dopo la
chiusura, col runner come app, ricevono `42501`. L'avvertenza del §5 vale, sui nomi nuovi.
⚠️ Il verbo vuole un operatore col livello: l'operatore costruito non ha righe d'area (è
`BLOCCATO` ovunque), quindi una fixture portata sul verbo deve dare il livello prima.

**7. Uno scrittore DB fuori dal censimento.** `anagrafiche.fn_provisiona_dati_di_sviluppo`
(DEFINER, `EXECUTE` all'app, 2026-10-18) crea i magazzini predefiniti di DEVA e DEVB. Da DEFINER
la chiusura non la tocca; il censimento del P-0 deve dire **con quale guard** la chiama l'app e se
la nascita passa da `fn_crea_magazzino` o dal verbo.

**8. Le note.** Sono la madre `magazzino.note` e nove partizioni (`note_asset`, `note_evento_asset`,
`note_inventario`, `note_inventario_riga`, `note_movimento`, `note_rettifica`,
`note_rettifica_riga`, `note_trasferimento`, `note_trasferimento_riga`). Ogni partizione ha i suoi
privilegi (oggi l'app ha `INSERT` su ciascuna): la postura deve elencare **le partizioni**, non
solo la madre. Nessuno scrittore applicativo di note di magazzino a oggi (il
`PartitionedNoteRepository` del BE non è montato per `magazzino`).

**9. Lotto 2: la provenienza delle testate.** Dal 2026-11-08 (`brief-db-sorgente-documento-e-riga`)
`inventari`, `rettifiche` e `trasferimenti` hanno `trgfn_guard_sorgente('DOCUMENTO', 'BLOCCA')`: i
verbi generici della D-M5 scrivono anche le colonne `sorgente_*`. Le famiglie del registro BE
`FAMIGLIE` sono **due** (inventario, rettifica); il trasferimento non ha scrittore applicativo.
L'argomento della D-M5 non cambia: la matrice delle tre famiglie a DB è una sola.

## 4. Il disegno — deciso il 2026-11-21

**Lotto 1 — anagrafiche e tabelle senza scrittore** (D-M1 C, D-M2 b, D-M4 b, D-M6 b). I nomi
delle funzioni si fissano al P-3, con la convenzione dei verbi esistenti.

* **Colonne ammesse** (D-M4): una funzione per anagrafica (magazzino, ubicazione, lotto) col
  gesto come argomento (`'crea'` / `'modifica'`), che restituisce i campi ammessi. La leggono il
  verbo e il backend. `fn_crea_magazzino` la legge al posto della sua costante `c_ammesse`.
* **Nascita** (D-M2): un verbo DEFINER per anagrafica, con `script.fn_guard_livello(utente,
  'magazzino', '<tabella>', 'TUTTO')` nella prima riga, che chiama il BB di nascita della
  tabella. `fn_crea_magazzino` c'è; `fn_crea_ubicazione` e `fn_crea_lotto` nascono sul suo
  stampo (INVOKER, obbligatori come argomenti, facoltativi in `p_campi`, chiave estranea
  `E_CAMPO_NON_AMMESSO`), e i builder `dbops.fn_pgtap_crea_*` ne diventano involucri nello
  stesso giro.
* **Modifica** (D-M2): un verbo DEFINER per anagrafica, stesso guard, col delta in `jsonb`
  scritto da `script.fn_scrivi_riga_da_jsonb` con `p_dove`. La riga fuori perimetro o assente
  risponde «non trovata» (no-leak). Nessun `DELETE`: si disattiva, come oggi.
* **Perimetro** (D-M6): `script.trgfn_guard_emittente_scope('magazzino', 'magazzino_id')` su
  `ubicazioni`, `inventari`, `rettifiche`, `trasferimenti`. Vale per ogni scrittore, anche per
  il backend di oggi sui documenti interni prima del Lotto 2.
* **Postura**: in `v_tabelle_sola_lettura_app` (tre sedi, §11.8) `magazzini`, `ubicazioni`,
  `lotti`, `trasferimenti` e righe, `assets`, `eventi_assets`, la madre `magazzino.note` e le
  nove partizioni (§3-bis.8).

**Lotto 2 — documenti interni** (D-M5 b): verbi comuni con la famiglia come primo argomento
(crea, modifica, cancella testata; scrivi e togli riga; cambia stato), su un registro delle
famiglie a DB (tabella, tabella righe, colonna di stato, azione o oggetto di permesso), come
`fn_documento_interno_transizioni`. Le tre famiglie entrano tutte, il trasferimento compreso. I
verbi scrivono anche le colonne `sorgente_*` (§3-bis.9). Poi la chiusura di `inventari`,
`rettifiche` e delle loro righe. Il registro `FAMIGLIE` del backend si riduce a ciò che il DB non
sa (segmento di URL, chiavi dei messaggi): il dettaglio si scrive progettando il P-5.

> ⚠️ **Superato il 2026-11-21** dal disegno qui sopra: il primo punto è fatto (§3-bis.1), e i
> `fn_scrivi_*` con `p_id` vuoto = nuovo duplicavano `fn_crea_magazzino` (§3-bis.2).

**Lotto 1 — prima stesura del 2026-10-03** (con C, b, b, b):

* il BB della scrittura dinamica (D-M3), con il pannello che lo adotta;
* `magazzino.fn_*_colonne_scrivibili` per le tre anagrafiche (D-M4);
* i verbi: `magazzino.fn_scrivi_magazzino(p_id, p_dati)`,
  `fn_scrivi_ubicazione(p_magazzino_id, p_id, p_dati)`,
  `fn_scrivi_lotto(p_articolo_id, p_id, p_dati)` — `p_id` vuoto = nuovo, come nel
  pannello. Nessun `DELETE`: si disattiva, come oggi;
* in `v_tabelle_sola_lettura_app`: `magazzini`, `ubicazioni`, `lotti`, e le
  tabelle senza scrittore (`trasferimenti` e righe, `assets`, `eventi_assets`, le
  note).

**Lotto 2 — prima stesura**: i verbi generici della D-M5, poi la chiusura di
`inventari`, `rettifiche` e delle loro righe. Si scrive dopo il Lotto 1, nello
stesso brief.

## 5. I passi

| Passo | Cosa | Note |
| --- | --- | --- |
| **P-0** | Censimento, prima di scrivere | sotto |
| **P-1** | Dichiarazione «dominio a metà» nella guida | ✅ **fatto il 2026-10-03** |
| P-2 | BB della scrittura dinamica, il pannello lo adotta | ✅ **fatto da un altro cantiere** (`script.fn_scrivi_riga_da_jsonb`, `20261017-05`; §3-bis.1) |
| P-3 | Colonne ammesse, BB di nascita, verbi delle anagrafiche; guard di perimetro sulle quattro tabelle (D-M6) | `20_code/magazzino`; builder `dbops.fn_pgtap_crea_*` involucri nello stesso giro |
| P-4 | Postura del Lotto 1 nelle tre sedi | `90_end` + loop + provisioning |
| P-5 | Lotto 2: verbi dei documenti interni e postura | dopo P-4 |
| P-6 | Guida: la sezione «La porta» si riduce a una riga; registro dei BB | alla chiusura |

**P-0, il censimento.** Letto il 2026-10-03, da rifare sui file al momento di
scrivere. ⚠️ Al 2026-11-21 i numeri sono già cambiati (file pgTAP che scrivono direttamente:
`magazzini` 4, `ubicazioni` 8, `lotti` 12, `inventari` 27, `rettifiche` 8, `trasferimenti` 5,
`assets` 7, `eventi_assets` 2) e la fixture citata sotto non esiste più (§3-bis.6). Al
censimento si aggiungono le funzioni DB che scrivono le tabelle (§3-bis.7) e le partizioni delle
note (§3-bis.8). File che scrivono **direttamente** le tabelle che si chiudono:

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
  chiamano i verbi invece di `execute_dynamic_insert`/`update` (e `create_magazzino` il verbo invece di
  `fn_crea_magazzino`); le costanti `*_COLONNE` e `_CAMPI_MADRE_MAGAZZINO` si ritirano, e il form e la validazione leggono le funzioni DB
  (D-M4). Il 403 dell'endpoint resta (guida §7.4: *il backend chiede, non decide
  due volte*).
* **R-2** (Lotto 2) `magazzino_repository.py`: testate, righe e cambio di stato
  dai verbi; il registro `FAMIGLIE` si riduce a ciò che il DB non sa (il brief del
  Lotto 2 lo dirà).
* **R-3** i codici nuovi (se ne nascono) nelle chiavi i18n e nella tassonomia
  degli errori.
* **R-4** (§3-bis.5) le view delle anagrafiche e dei documenti di magazzino dichiarano
  l'**oggetto** che il verbo passa a `fn_guard_livello` (per le anagrafiche
  `(magazzino, magazzini)`, `(magazzino, ubicazioni)`, `(magazzino, lotti)`), così il 403
  dell'endpoint e il rifiuto del verbo leggono la stessa regola, override sull'oggetto compreso.
  Con R-1, il BE **censisce** i propri scrittori e lettori di queste tabelle: l'elenco dei file
  qui sopra è quello noto al DB, non un elenco chiuso.

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
| 2026-11-21 | DB | Riverifica (§3-bis). Privilegi dell'app invariati. Fatti nuovi: `fn_scrivi_riga_da_jsonb` già in uso (D-M3 e P-2 chiusi altrove); `fn_crea_magazzino` già BB di nascita (D-M2 riformulata: nascita sul BB `fn_crea_*`, modifica per delta); lista delle colonne in tre posti (D-M4); guard di perimetro assente su ubicazioni e testate (D-M6 nuova); oggetto del permesso non dichiarato dal BE (R-4); fixture rinominate; `fn_provisiona_dati_di_sviluppo` scrittore non censito; note = madre + 9 partizioni; sorgente delle testate. Testata «Chi riparte» e «Brief vicini» aggiunte |
| 2026-11-21 | Tid | **D-M6 = b**: il perimetro in scrittura lo dice la tabella (`trgfn_guard_emittente_scope('magazzino', 'magazzino_id')` su `ubicazioni`, `inventari`, `rettifiche`, `trasferimenti`); il verbo tiene solo la lettura no-leak |
| 2026-11-21 | Tid | **D-M1 = C, in due lotti**: Lotto 1 anagrafiche + chiusura delle tabelle senza scrittore; Lotto 2 i documenti interni |
| 2026-11-21 | Tid | **D-M2 = b, nella forma del §3-bis.2**: nascita = verbo col guard che chiama il BB `fn_crea_*` della tabella (`fn_crea_magazzino` c'è; nascono `fn_crea_ubicazione`, `fn_crea_lotto`); modifica = verbo per tabella col delta in `jsonb` su `fn_scrivi_riga_da_jsonb`; nessun `DELETE` |
| 2026-11-21 | Tid | **D-M4 = b, una funzione per tabella col gesto** (`'crea'` / `'modifica'`): la leggono il verbo e il backend; `c_ammesse` di `fn_crea_magazzino` e le costanti BE (`*_COLONNE`, `_CAMPI_MADRE_MAGAZZINO`) si ritirano nello stesso giro |
| 2026-11-21 | Tid | **D-M5 = b**: verbi comuni dei documenti interni con la famiglia come argomento, su un registro a DB; le tre famiglie, trasferimento compreso; il registro `FAMIGLIE` del BE si riduce a ciò che il DB non sa. §4 riscritto sul deciso (la prima stesura resta marcata superata); P-3 allargato al guard della D-M6; testata: riparte il team DB, al via |
