# Brief DB — magazzino: tutte le scritture passano da un verbo

> **⏭️ Chi riparte — aggiornato al 2026-11-22**
>
> **Riparte: team DB** col P-5 (Lotto 2). La R-1 è fatta dalla sessione BE il 2026-11-22
> (repository sui verbi, colonne ammesse lette dal DB, test e smoke verdi) e committata su
> `dev/backend-tid`. La R-4 aspetta che gli oggetti di magazzino entrino a catalogo (Tid, 2026-11-22).
>
> | # | Chi | Che cosa | Dove | Aspetta |
> | --- | --- | --- | --- | --- |
> | 1 | Tid | ✅ decisioni prese (2026-11-21/22): D-M1 = C, D-M2 = b riformulata, D-M4 = b col gesto, D-M5 = b, D-M6 = b, D-M7 = b; D-M3 era già fatta. Il via al Lotto 1 è dato | §3, §3-bis | — |
> | 2 | team DB | ✅ P-0 (§5.1); ✅ P-3 (`20261122-01` … `-08`, §5.2), applicato da Tid il 2026-11-22 con i test verdi | §5 | — |
> | 3 | team DB | ✅ P-4 (`20261122-09` … `-11`, il loop, il provisioning, 2 pgTAP nuovi e 17 adattati, §5.3) | §5.3 | — |
> | 4 | Tid | ✅ apply del P-4, pgTAP verdi col runner (2026-11-22) | §5.3 | — |
> | 4-bis | Tid | ✅ apply di `20261122-12` e `-13` (il cliente del seriale), pgTAP verdi col runner (2026-11-22) | §5.3 | — |
> | 5 | sessione BE | ✅ R-1 (2026-11-22); R-3: nessun codice nuovo da questo brief. ⏳ R-4 non fatta: vuole gli oggetti di magazzino a catalogo (§7, R-4) | §7 | — |
> | 5-bis | Tid | ✅ R-4 «al giorno del catalogo» (2026-11-22): la fa la sessione BE/FE quando le righe `(magazzino, …)` entrano in `area_model_overrides` | §7 | catalogo |
> | 6 | team DB | P-5 (Lotto 2), poi R-2 al BE | §5, §7 | 5 |
> | 7 | team DB | P-6, archiviazione | §5 | 6 |
>
> Decisioni di Tid del 2026-11-22: il controllo di `p_campi` comune ai `fn_crea_*` si estrae **in un
> giro a parte**, dopo la R-1 (§5.2); il debito `%TYPE` del P-3 **resta per ora** (§5.3); il lotto
> diventa dell'azienda, in un brief suo (`brief-db-magazzino-lotto-dell-azienda`); il cliente del
> seriale si controlla subito: `20261122-12` e `-13` applicati, pgTAP verdi (§5.3). Da committare:
> il P-3, il P-4, `-12`, `-13` e questo file.
>
> **Brief vicini verificati (2026-11-21):** `work-done/2026/brief-db-processi-accensione-per-ambiente`
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
> [brief del pannello](../work-done/2026/brief-db-pannello-config-verbo-generico.md)
> (Tid, 2026-09-25): *«`magazzini` e `ubicazioni`: un brief a sé del cantiere
> magazzino, con i loro verbi»*. Quel brief non era mai stato scritto; è emerso
> chiudendo il [brief del modello](../work-done/2026/brief-db-permesso-nel-verbo-di-scrittura.md)
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
rivisto in `20261018-34`) è nato dalla 2b-1 di `work-done/2026/brief-db-processi-accensione-per-ambiente`.
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
⚠️ **Precisato il 2026-11-22**: `config.user_override_oggetti` ha una FK verso
`config.area_model_overrides`, dove nessun oggetto di magazzino è a catalogo. Oggi un override su un
oggetto di magazzino **non si può scrivere**, e il backend e il verbo rispondono uguale (l'area). La
divergenza nasce quando gli oggetti entrano a catalogo: la R-4 resta, per quel giorno.

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

**10. Il controesempio del P-0 (2026-11-22): le tabelle «senza scrittore» uno scrittore ce l'hanno (§5.1).**

| | Opzioni | Proposta |
| --- | --- | --- |
| **D-M7** ✅ **DECISA da Tid il 2026-11-22: b** | **a** il Lotto 1 chiude anagrafiche, note ed `eventi_assets`; `trasferimenti` passa al Lotto 2 coi suoi verbi; `assets` resta aperta, dichiarata nella guida, fino al verbo del primo scrittore (§8) · **b** come a, ma `assets` si chiude nel Lotto 1 con un BB di nascita del seriale (`fn_crea_asset`, stampo `fn_crea_magazzino`) e il suo verbo · **c** si chiude tutto e i test si marcano owner | ⭐ **b.** Il seriale una nascita ce l'ha già, fatta a mano: i pgTAP e il collaudo a video lo inseriscono in SQL. Il BB è meccanico (le regole stanno già nei vincoli e nel guard di perimetro della tabella) e dà al collaudo la strada che non ha. `trasferimenti` al Lotto 2 perché lì nascono i suoi verbi. ⛔ **c** no: il marcatore owner su un soggetto che l'app raggiunge nasconde il difetto (criterio di `testpgtap.sh`) |

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
| P-3 | Colonne ammesse, BB di nascita, verbi delle anagrafiche; guard di perimetro sulle quattro tabelle (D-M6) | ✅ **applicato il 2026-11-22** (§5.2), test verdi. I builder `dbops.fn_pgtap_crea_*` passano al P-4: li rompe la chiusura, si cambiano con lei |
| P-4 | Postura del Lotto 1 nelle tre sedi; builder sui verbi; i pgTAP come app | ✅ **applicato il 2026-11-22** (§5.3), pgTAP verdi col runner |
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

### 5.1 Il P-0 rifatto — 2026-11-22

Letto su dbdev (catalogo) e sui file del ramo. Fatti datati: si rifà se il lavoro slitta.

**Funzioni DB che scrivono le tabelle del Lotto 1**

| Funzione | Sicurezza | Scrive | Dopo la chiusura |
| --- | --- | --- | --- |
| `magazzino.fn_crea_magazzino` | INVOKER (BB) | `magazzini` | la chiama il verbo di nascita; legge le colonne ammesse (D-M4) |
| `dbops.fn_pgtap_crea_magazzino` | INVOKER | `magazzini`, via il BB | come app riceve `42501`: si porta sul verbo (sotto) |
| `anagrafiche.fn_provisiona_dati_di_sviluppo` | DEFINER, solo in SVILUPPO | `magazzini`, via il BB, con `dev.smoke` (super admin) in sessione | non la tocca: resta sul BB. Il suo cancello è l'ambiente, non un permesso d'operatore |
| `magazzino.fn_posta_inventario`, `_rettifica`, `_trasferimento` | DEFINER | lo stato della testata | non le tocca; il guard della D-M6 salta un `UPDATE` che non cambia il magazzino |

Nessuna funzione DB scrive `ubicazioni`, `lotti`, `assets`, `eventi_assets`, le note, né crea un
`trasferimento`. I changeSet girano da proprietario e non sono toccati; i CSV di
`80_data/sql/magazzino/` (tranne `causali`) non li carica nessun changelog.

**pgTAP.** I file che scrivono **direttamente** le tabelle del Lotto 1:

* **come proprietario** (marcatore `pgtap-runner: owner`), non toccati: `dbops/test-presidi-magazzino-grana-v1`,
  `dbops/test-sorgenti-orfane-v1`, `magazzino/test-fn-scrivi-movimento-controlli-v1`,
  `magazzino/test-fn-scrivi-movimento-disponibilita-v1`, `magazzino/test-fn-scrivi-movimento-seriali-v1`,
  `magazzino/test-movimenti-vincoli-v2`, `magazzino/test-sorgente-registro-v1`, `rls/test-rls-magazzino-perimetro-v1`;
* **come app**, da portare sui verbi o sui builder (14):

| File | Tabelle |
| --- | --- |
| `magazzino/test-capability-documenti-interni-v1` | ubicazioni |
| `magazzino/test-ddt-scarico-v1` | lotti |
| `magazzino/test-fn-posta-inventario-v1` | lotti, ubicazioni |
| `magazzino/test-fn-posta-trasferimento-v1` | **trasferimenti e righe**, ubicazioni |
| `magazzino/test-reso-carico-kit-seriali-v1` | **assets**, lotti, ubicazioni |
| `magazzino/test-reso-carico-v1` | lotti |
| `magazzino/test-sorgente-testate-v1` | **assets, eventi_assets, trasferimenti** |
| `magazzino/test-ubicazioni-guard-parent-v1` | ubicazioni |
| `magazzino/test-valore-giacenza-forma-v1` | ubicazioni |
| `script/test-guard-sorgente-v1` | lotti |
| `script/test-sorgente-in-uscita-v1` | lotti |
| `script/test-trgfn-default-emittente-fiscale-v1` | magazzini |
| `vendite/test-ddt-da-ordine-emittente-prima-dei-lettori-v1` | magazzini |
| `vendite/test-ddt-magazzino-testata-v1` | **assets**, magazzini |

* **attraverso `dbops.fn_pgtap_crea_magazzino`**: 29 file, 21 come app. Si cambia il builder, non i file:
  dopo la chiusura chiama il verbo di nascita, che vuole `TUTTO` sull'oggetto. L'operatore costruito non ha
  righe d'area (`BLOCCATO`), e l'override d'oggetto non supera il tetto d'area: il builder apre l'area
  `magazzino` al livello che serve, come `fn_pgtap_concedi_azione` apre quello di un'azione (e si ferma se il
  test ha già chiuso l'area con un suo override). Lo stesso per i builder nuovi di ubicazione e lotto.

**Backend** (richiesta, non lettura: il BE censisce i suoi): `magazzino/db/anagrafiche_magazzino_repository.py`;
nei test `magazzino/tests/db/test_documento_interno_db.py`, `vendite/tests/db/test_ddt_cambia_stato_db.py`,
`backend/scripts/tests/smoke-magazzino-inventario-primo-carico.py`.

**⚠️ Il controesempio alla D-M1.** «Chiudere le tabelle senza scrittore costa solo una voce nel loop» (§3) è
**smentito**. Uno scrittore c'è: i pgTAP come app che fabbricano un seriale (`assets`), un evento o un
trasferimento, per provare cose che l'applicazione fa davvero (il reso di un kit coi seriali, la testata della
bolla, la registrazione di un trasferimento). Chiusa la tabella, il soggetto non si fabbrica più come app, e
nessun verbo lo crea:

| Tabella | Chi la fabbrica oggi come app | Che cosa serve |
| --- | --- | --- |
| `trasferimenti` e righe | `test-fn-posta-trasferimento-v1`, `test-sorgente-testate-v1` | i verbi comuni dei documenti interni (Lotto 2, D-M5) |
| `assets` | `test-reso-carico-kit-seriali-v1`, `test-ddt-magazzino-testata-v1`, `test-sorgente-testate-v1` | un verbo di nascita del seriale; oggi il collaudo a video li inserisce in SQL |
| `eventi_assets` | `test-sorgente-testate-v1` | il soggetto è il guard della sorgente su una testata che solo un verbo scriverebbe: marcatore owner legittimo (forma 3 di `testpgtap.sh`) |

⇒ Decisione a Tid: **D-M7** al §3-bis.

### 5.2 Il P-3 — scritto il 2026-11-22

Tutto in `20_code/magazzino/`. Non applicato.

| changeSet | Che cosa |
| --- | --- |
| `20261122-01` | `fn_magazzini_colonne_ammesse`, `fn_ubicazioni_…`, `fn_lotti_…`, `fn_assets_colonne_ammesse(p_gesto)` (D-M4): `'crea'` e `'modifica'`, in ordine di tabella. Fuori lista: l'emittente e le identità della nascita (`magazzino_id`, `articolo_id`). Il seriale non ha colonne da modificare |
| `20261122-02` | `fn_crea_magazzino` legge la lista `'crea'` al posto della costante `c_ammesse`. Firma e comportamento invariati |
| `20261122-03` … `-05` | i BB di nascita `fn_crea_ubicazione(magazzino, codice, tipo, campi)`, `fn_crea_lotto(articolo, codice, data_arrivo, campi)`, `fn_crea_asset(articolo, seriale, stato, proprietà, campi, emittente)`: INVOKER, stampo `fn_crea_magazzino`, gli obbligatori come argomenti |
| `20261122-06` | i verbi di nascita `fn_aggiungi_magazzino`, `_ubicazione`, `_lotto`, `_asset`: DEFINER, `fn_guard_livello(utente, 'magazzino', '<tabella>', 'TUTTO')` nella prima riga, poi il BB. L'ubicazione in un magazzino fuori perimetro o inesistente: `E_MAG_MAGAZZINO_NON_TROVATO` (no-leak, il predicato di `fn_libera_blocco`) |
| `20261122-07` | i verbi di modifica `fn_modifica_magazzino(id, dati)`, `fn_modifica_ubicazione(magazzino, id, dati)`, `fn_modifica_lotto(id, dati)`: il delta in `jsonb` (una chiave a null svuota, una assente resta), la lista `'modifica'`, la riga letta `FOR UPDATE` nel perimetro, altrimenti il codice «non trovato» che il backend solleva già (`E_MAG_MAGAZZINO_NON_TROVATO`, `E_MAG_UBICAZIONE_NON_TROVATA`, `E_MAG_LOTTO_NON_TROVATO`) |
| `20261122-08` | `trgfn_guard_emittente_scope('magazzino', …)` su `ubicazioni`, `inventari`, `rettifiche` (`magazzino_id`) e `trasferimenti` (`magazzino_id_from`), stampo `trg_<t>_a10_guard_emittente_scope_ins_upd` (D-M6) |

**I nomi.** `fn_crea_*` è il BB, senza permesso (lo usano anche il provisioning e i builder);
`fn_aggiungi_*` e `fn_modifica_*` sono i gesti dell'operatore.

**pgTAP nuovi**, verdi in estratto: `magazzino/test-colonne-ammesse-e-nascita-anagrafiche-v1` (22) e
`magazzino/test-verbi-anagrafiche-magazzino-v1` (22, come app: permesso, nascita, modifica, no-leak, forma).
In estratto, coi `-01` … `-08` davanti, invariati: `rls/test-rls-magazzino-perimetro-v1`,
`magazzino/test-fn-posta-trasferimento-v1`, `-inventario-v1`, `-rettifica-v1`, `test-documenti-interni-guard-v1`
(3 rossi già presenti prima), `test-ubicazioni-guard-parent-v1` (1 rosso già presente), `test-capability-documenti-interni-v1`,
`dbops/test-presidi-magazzino-grana-v1`, `test-movimenti-vincoli-v2`, `test-sorgente-testate-v1`,
`test-valore-giacenza-forma-v1`, `test-fn-scrivi-movimento-controlli-v1`, `test-fn-crea-magazzino-v1`.

⚠️ **Il limite della prova.** `prova_changeset.py` gira da proprietario: la RLS non filtra e il guard
della D-M6 lascia passare il proprietario fuori da una DEFINER. La strada dell'app (il guard nuovo
sulle scritture del backend di oggi, il perimetro dei pgTAP come app) si vede solo dopo l'apply, col
runner. I rossi già presenti nei due file sopra sono quelli «da owner, per costruzione»: vanno
riletti nella corsa come app, perché un rosso preesistente può nascondere un'asserzione nuova.

**Lasciato apposta**

* le pagine `manual/` delle funzioni nuove e la doc auto-generata: con l'apply (P-6);
* le note di `codici_errore.csv` dei tre codici «non trovato» dicono ancora «lo solleva il backend».
  Il CSV ha modifiche aperte di un'altra sessione: le note si allineano al commit del Lotto 1;
* ✅ **DECISA da Tid il 2026-11-22: sì, in un giro a parte** (dopo la R-1, brief suo): i `fn_crea_*` ripetono tutti lo stesso controllo di `p_campi`
  (è un oggetto; nessuna chiave fuori lista, col nome), in più domini: magazzino, anagrafiche,
  vendite. Con questo giro le copie in magazzino sono quattro. Estrarlo in un BB `script` tocca più
  domini, e la regola del 2 vuole l'ok di Tid. Proposta: un BB `script.fn_guard_campi_ammessi(campi,
  ammesse, porta, chiave)`, con le copie ritirate nello stesso giro, in un giro a parte.

### 5.3 Il P-4 — scritto il 2026-11-22

Il P-3 e il P-4 sono applicati (Tid, 2026-11-22), i pgTAP verdi col runner come app: anche le
asserzioni di privilegio, rosse in estratto per costruzione.

| changeSet / file | Che cosa |
| --- | --- |
| `20_code/dbops/20261122-09` | i builder sui verbi: `fn_pgtap_crea_magazzino(codice, usa_ubicazioni, campi)` (entra `p_campi`, DROP + CREATE: le chiamate a uno e due argomenti restano), e i nuovi `fn_pgtap_crea_ubicazione`, `fn_pgtap_crea_lotto_di_magazzino` (`fn_pgtap_crea_lotto` è il lotto di fatturazione), `fn_pgtap_crea_asset`. Con loro `fn_pgtap_apri_area_per_nascita` e `fn_pgtap_richiudi_area` |
| `90_end/20261122-10` | la postura: a `zeroerp_app` solo `SELECT` su `magazzini`, `ubicazioni`, `lotti`, `assets`, `eventi_assets`, la madre `note` e le nove partizioni |
| loop `90_end/ci_apply/20260205-41`, `scripts/sql/provision_zeroerp.sql` | le altre due sedi, stesso elenco (§11.8) |
| `20_code/magazzino/20261122-11` | il guard sul padre dell'ubicazione legge il padre nel perimetro di chi agisce (sotto) |

**L'area aperta per il tempo della nascita.** Il verbo vuole `TUTTO`, l'operatore costruito è `BLOCCATO`.
Il builder apre l'area con un override d'area (o alza quello che c'è), chiama il verbo e lo rimette com'era.
Il test ritrova i livelli che aveva: un rifiuto per livello si prova prima o dopo la fixture, e la fixture
non lo tocca. È diverso da `fn_pgtap_concedi_azione`, che apre l'area per sempre.

**⚠️ Un difetto trovato portando i test sui verbi, chiuso dal `-11`.** `trgfn_ubicazioni_guard_parent` è
INVOKER e leggeva il padre affidandosi alla RLS. Dentro `fn_aggiungi_ubicazione` e `fn_modifica_ubicazione`
(DEFINER, applicati col P-3) la RLS non filtra, quindi un padre di un'altra azienda veniva trovato. La frase
diceva allora «appartiene al magazzino PGT-UGP-B»: il codice del magazzino altrui. Il padre ora si cerca col
predicato esplicito del perimetro (`fn_scope_ef_whitelist_via_magazzino`, quello dei verbi). La correzione è
provata sul controesempio: senza `-11`, i casi 4 e 5 di `test-ubicazioni-guard-parent-v1` sono rossi con
quella frase; con `-11` sono verdi. Applicato su dbdev il 2026-11-22.

**pgTAP nuovi**

* `magazzino/test-anagrafiche-magazzino-sola-lettura-v1` (14, come app): le tre sedi dicono la stessa cosa,
  i `42501`, i builder (la nascita, l'override rimesso com'era, il verbo nel corpo). In estratto le
  asserzioni 2-9 sono rosse per costruzione (da owner non c'è `42501`); si leggono col runner come app.
* `magazzino/test-sorgente-eventi-assets-v1` (3, **owner**): i casi dell'evento del seriale che erano in
  `test-sorgente-testate-v1` (D-M7 = b). L'evento è chiuso all'app e nessun verbo lo scrive: forma 3 di
  `testpgtap.sh`. Quando l'evento avrà il suo verbo (§8), il marcatore si toglie.

**pgTAP adattati** (17). Le nascite a mano diventano builder; i casi passano dai verbi:

* sui builder: `test-capability-documenti-interni-v1`, `test-ddt-scarico-v1`, `test-fn-posta-inventario-v1`,
  `test-fn-posta-trasferimento-v1` (solo le ubicazioni: il trasferimento resta aperto fino al Lotto 2),
  `test-reso-carico-v1`, `test-reso-carico-kit-seriali-v1`, `test-valore-giacenza-forma-v1`,
  `script/test-guard-sorgente-v1`, `script/test-sorgente-in-uscita-v1`,
  `vendite/test-ddt-da-ordine-emittente-prima-dei-lettori-v1` e `vendite/test-ddt-magazzino-testata-v1` (il
  predefinito si sceglie alla nascita, in `p_campi`), `test-verbi-anagrafiche-magazzino-v1`;
* sui verbi: `test-fn-crea-magazzino-v1` e `test-colonne-ammesse-e-nascita-anagrafiche-v1` (le regole dei BB,
  dalla strada dell'app), `test-ubicazioni-guard-parent-v1`;
* `test-sorgente-testate-v1`: senza i casi dell'evento (sopra). La riga citata del caso 14 la cita una
  rettifica;
* `script/test-trgfn-default-emittente-fiscale-v1`: 10, 12 e 14 dal verbo del magazzino. L'11 (emittente
  esplicito) e il 15 (sessione senza utente) dal magazzino non si raggiungono più, perché il verbo non prende
  l'emittente e senza utente si ferma sul permesso: girano su `vendite.ordini`, montato sullo stesso BB.

**Casi che l'app non può più tentare**, sostituiti, non marcati owner:

* `test-fn-crea-magazzino-v1` 2, «l'emittente indicato»: è la strada del provisioning
  (`fn_provisiona_dati_di_sviluppo`, col suo test). Diventa «l'emittente fra i campi del verbo:
  `E_CAMPO_NON_AMMESSO`»;
* `test-ubicazioni-guard-parent-v1`:
  * 5, «nascita con `parent_id = id`»: il verbo non prende l'id. Il ramo lo prova il 7 in modifica. Al suo
    posto c'è il padre altrui in modifica;
  * 10, «il lucchetto rifiuta il cambio di magazzino»: il verbo non ammette `magazzino_id`, quindi
    `E_CAMPO_NON_AMMESSO`. Il lucchetto resta dichiarato al 9, per lo scrittore diretto.

**La prova in estratto** (coi tre changeSet, da owner sullo scratch). I 46 pgTAP che usano un builder di
magazzino o scrivono le tabelle del Lotto 1 danno lo stesso esito di prima o uno migliore.
`test-ubicazioni-guard-parent-v1` è passato da 1 rosso a 0. Hanno ancora rossi, identici con e senza
estratto:

* `test-blocco-manuale-e-porta-lotto3-v1` (1), `test-documenti-interni-guard-v1` (3) e `test-porta-ledger-v1`
  (4): le asserzioni di privilegio, rosse da owner per costruzione;
* `test-lista-definizione-perimetro-emittente-v1`: si interrompe allo stesso punto, con e senza estratto.

Vanno riletti nella corsa come app.

**⚠️ Debito `%TYPE` del P-3** (visto il 2026-11-22, dopo l'apply). Restano a tipi nudi:

* i `RETURNS bigint` di `fn_crea_*` (`-02` … `-05`) e dei quattro `fn_aggiungi_*` (`-06`);
* le firme dei `DROP` nei rollback (`-01`, `-03` … `-06`);
* `v_estranea text` e `v_ammesse text[]` (nomi di colonna, nessuna colonna di cui siano il riflesso), senza
  il commento che lo dica.

Il DB non cambia (`%TYPE` si risolve allo stesso tipo). Ma i file sono applicati su dbdev: correggerli
cambia il checksum. ✅ **Tid, 2026-11-22: resta così per ora**; si riprende con un changeSet di sola forma
o alla prossima riscrittura di quelle funzioni. Il P-4 (`-09` … `-11`) è ancorato.

**Due fatti emersi, decisi da Tid il 2026-11-22:**

* **il lotto non ha emittente né policy**: è condiviso fra le aziende, come l'articolo. Dentro il verbo di
  modifica, `trgfn_prevent_deactivate_if_children` vede i figli di tutte le aziende, quindi un lotto usato da
  un'altra azienda non si disattiva. Dall'app, sotto RLS, si disattivava.
  ✅ **Tid: «lotto b»**, il lotto è dell'azienda. Si lavora in
  [brief-db-magazzino-lotto-dell-azienda](../work-done/2026/brief-db-magazzino-lotto-dell-azienda.md)
  (chiuso e archiviato il 2026-11-22);
* **`assets.billing_account_id`** (fra i campi della nascita del seriale) non era controllato contro
  l'emittente del seriale. ✅ **Tid: «seriale a»**, il controllo subito. Applicati da Tid il 2026-11-22,
  pgTAP verdi col runner:
  * `20_code/magazzino/20261122-12` monta sul seriale `script.trgfn_doc_guard_emittente_ba`, il BB di
    ordini, contratti, DDT, preventivi, offerte, resi e commesse (`E_DOC_EMITTENTE_BA_INCOERENTE`). Su
    dbdev nessun seriale ha un BA: niente pregresso;
  * `20_code/script/20261122-13`: il BB mette nella frase il codice del BA solo se il BA è nel perimetro
    di chi agisce (`fn_scope_ef_whitelist_via_efba`). Dentro `fn_aggiungi_asset` (DEFINER) la frase dava
    il codice del cliente dell'altra azienda: provato sul controesempio (caso 5 di
    `magazzino/test-assets-guard-emittente-ba-v1`, rosso senza `-13`, verde con). Dall'app la frase non
    cambia. I nomi delle aziende restano: `anagrafiche.soggetti` non ha RLS.

  pgTAP: `magazzino/test-assets-guard-emittente-ba-v1` (5, come app) nuovo;
  `vendite/test-guard-emittente-ba-unico-v1` (il censimento del test 1: otto montaggi). I quindici pgTAP
  che toccano il BB danno lo stesso esito di prima con `-12` e `-13`.

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
  ⚠️ **Dall'apply del P-4 (§5.3) l'app riceve `42501`** su ogni scrittura diretta di `magazzini`,
  `ubicazioni`, `lotti`, `assets`, `eventi_assets` e delle note. L'elenco chiuso, al 2026-11-22:

  | Oggi (BE) | Dopo |
  | --- | --- |
  | `create_magazzino` → `fn_crea_magazzino(codice, descrizione, indirizzo, campi)` | `magazzino.fn_aggiungi_magazzino(codice, descrizione, indirizzo_dettaglio_id, campi jsonb)` → `bigint` |
  | `update_magazzino` → `execute_dynamic_update` | `magazzino.fn_modifica_magazzino(id, dati jsonb)` → `jsonb` (la riga: id e colonne modificabili) |
  | `create_ubicazione` → `execute_dynamic_insert` | `magazzino.fn_aggiungi_ubicazione(magazzino_id, codice, tipo_id, campi jsonb)` → `bigint` |
  | `update_ubicazione` → `UPDATE … WHERE id AND magazzino_id` | `magazzino.fn_modifica_ubicazione(magazzino_id, id, dati jsonb)` → `jsonb` |
  | `create_lotto` → `execute_dynamic_insert` | `magazzino.fn_aggiungi_lotto(articolo_id, codice, data_arrivo, campi jsonb)` → `bigint` |
  | `update_lotto` → `execute_dynamic_update` | `magazzino.fn_modifica_lotto(id, dati jsonb)` → `jsonb` |
  | `MAGAZZINI_COLONNE`, `UBICAZIONI_COLONNE`, `LOTTI_COLONNE`, `_CAMPI_MADRE_MAGAZZINO` | `magazzino.fn_{magazzini,ubicazioni,lotti}_colonne_ammesse('crea' \| 'modifica')` → `text[]` |

  Nella modifica, una chiave assente resta com'è e una chiave a `null` svuota il campo. ⚠️ Il verbo **non**
  normalizza `''`: per svuotare un campo si manda `null`. Codici che il verbo solleva:
  * `E_PERMESSO_NEGATO`: livello sotto `TUTTO` sull'oggetto;
  * `E_CAMPO_NON_AMMESSO`: una chiave fuori lista, col nome;
  * `E_SCRIPT_CHIAMATA_NON_VALIDA`: `dati` non è un oggetto;
  * `E_MAG_MAGAZZINO_NON_TROVATO`, `E_MAG_UBICAZIONE_NON_TROVATA`, `E_MAG_LOTTO_NON_TROVATO`: la riga è
    assente o fuori perimetro. Sono quelli che il BE solleva già.

  I test BE che scrivono le tabelle a mano e riceveranno `42501`: `magazzino/tests/db/test_documento_interno_db.py`,
  `vendite/tests/db/test_ddt_cambia_stato_db.py`, `backend/scripts/tests/smoke-magazzino-inventario-primo-carico.py`.
  `magazzino/tests/db/test_anagrafiche_magazzino_db.py` passa dal repository: si rilegge dopo la R-1. Nessuno
  scrittore BE di seriali, eventi e note (§5.1). Il pannello non scrive magazzini né ubicazioni
  (`config.tabelle_gestibili`: `pannello = false`).
  ✅ **Fatta dalla sessione BE il 2026-11-22.** Il repository chiama i sei verbi; `colonne_ammesse(tabella,
  gesto)` legge `fn_<tabella>_colonne_ammesse`, e le costanti `*_COLONNE` / `_CAMPI_MADRE_MAGAZZINO` sono
  ritirate. Il service tiene il solo trasporto: `campi_per_presenza` con `ammesse` = la lista del DB, e una
  divergenza fra DB e lettori del BE è un `RuntimeError`, non uno scarto (presidio sul DB vero in
  `test_anagrafiche_magazzino_db`, caso 8). Il rifiuto del verbo senza livello è provato (caso 9). Portati sui
  builder: `test_documento_interno_db`, `test_ddt_cambia_stato_db`, `test_magazzino_spento_con_trasferimenti_db`
  e lo smoke del primo carico.
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
  ⏳ **Non fatta (sessione BE, 2026-11-22). ✅ Tid, 2026-11-22: si fa il giorno in cui gli oggetti entrano a catalogo.** Dichiarare `model_permission` sulle view fa
  rosso `test_catalogo_oggetti_rotte`: un oggetto chiesto dal BE deve essere a catalogo
  (`80_data/sql/config/area_model_overrides.csv`), oppure stare in `_IN_ATTESA_DI_CATALOGO` con il FE
  allineato (`READONLY_MODELS` e il readonly per oggetto nei drawer, compreso quello dei lotti dentro il
  drawer dell'articolo). Senza la riga di catalogo la dichiarazione non cambia niente (vale l'area), come dice
  il §3-bis.5. Per farla servono: le righe `(magazzino, magazzini|ubicazioni|lotti)` nel catalogo (DB), il
  perimetro delle rotte nel presidio e `model_permission` (BE), `READONLY_MODELS` e i drawer (FE). Censimento
  BE fatto: gli scrittori sono solo il repository delle anagrafiche; i lettori sono il repository stesso, i
  lookup di riga (`magazzino_repository`) e le proiezioni di bolla e reso (`ddt_repository`,
  `resi_repository`, `LEFT JOIN` per decodifica).

## 8. Che cosa NON entra

| Cosa | Dove |
| --- | --- |
| `vendite`: la bolla e il reso oltre la porta del registro | brief suo, da aprire |
| i verbi degli **asset** e degli eventi | con il loro primo scrittore (D-L2-l): nasceranno come verbi, perché la tabella è già chiusa |
| policy RLS di scrittura sul livello, `FORCE ROW LEVEL SECURITY` | mai (§3 e §6 del brief del modello) |
| l'apply, i pgTAP col runner, il commit | Tid |

## 9. Riferimenti

* [Guida dei permessi §7.4-7.5](../../guide/architettura-permessi-e-autorizzazioni.md#74-il-permesso-nel-verbo-di-scrittura) — il modello.
* [Brief del pannello](../work-done/2026/brief-db-pannello-config-verbo-generico.md), D-P2 (niente RLS nel verbo generico) e D-P4.
* [Verbi con permesso di magazzino](../work-done/2026/brief-db-magazzino-verbi-con-permesso.md) — la forma dei verbi, il perimetro rimesso dal verbo, D-V1.
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
| 2026-11-22 | Tid | Il via al Lotto 1, dal progressivo `20261122-01` |
| 2026-11-22 | DB | **P-0 rifatto** (§5.1): scrittori DB, 14 pgTAP come app da portare sui verbi, 21 attraverso il builder del magazzino (si cambia il builder, che apre l'area al livello che serve), file BE noti. **Smentita** l'ipotesi della D-M1 «le tabelle senza scrittore costano una voce nel loop»: i pgTAP come app fabbricano seriali, eventi e trasferimenti. Nuova **D-M7** a Tid (§3-bis.10) |
| 2026-11-22 | Tid | **D-M7 = b**: nel Lotto 1 si chiudono anagrafiche, note, `eventi_assets` (il suo test va owner, forma 3) e `assets` con un BB di nascita del seriale (`fn_crea_asset`) e il suo verbo; `trasferimenti` e righe passano al Lotto 2 |
| 2026-11-22 | DB | **P-3 scritto** (§5.2): `20261122-01` … `-08` (colonne ammesse, `fn_crea_magazzino` sulla lista, tre BB di nascita, sette verbi, guard di perimetro su quattro tabelle) e due pgTAP, verdi in estratto con tredici pgTAP esistenti invariati. Precisata la R-4 (§3-bis.5: oggi un override su un oggetto di magazzino non si può scrivere). I builder passano al P-4. Una domanda a Tid sull'estrazione del controllo di `p_campi` |
| 2026-11-22 | Tid | P-3 applicato, pgTAP verdi |
| 2026-11-22 | DB | **P-4 scritto** (§5.3): builder sui verbi con l'area aperta per il tempo della nascita (`20261122-09`), postura del Lotto 1 nelle tre sedi (`-10`, loop, provisioning), e il guard del padre dell'ubicazione che legge nel perimetro esplicito (`-11`): dentro i verbi del P-3 la frase nominava il magazzino di un'altra azienda, provato sul controesempio. Due pgTAP nuovi (uno owner, l'evento del seriale), 17 adattati; 46 pgTAP in estratto con esito uguale o migliore. R-1 completata con l'elenco chiuso. Emersi: il debito `%TYPE` del P-3, il lotto condiviso, il BA del seriale |
| 2026-11-22 | Tid | P-4 applicato, pgTAP verdi col runner. Riparte la sessione BE con la R-1 |
| 2026-11-22 | Tid | Estrazione del controllo di `p_campi` (`script.fn_guard_campi_ammessi`): sì, in un giro a parte dopo la R-1. Debito `%TYPE` del P-3: resta per ora |
| 2026-11-22 | Tid + DB | «lotto b»: brief nuovo `brief-db-magazzino-lotto-dell-azienda`. «seriale a»: `20261122-12` (il BB emittente ↔ BA sul seriale) e `-13` (il codice del BA nella frase solo nel perimetro), pgTAP nuovo e censimento aggiornato, da applicare |
| 2026-11-22 | Tid | `20261122-12` e `-13` applicati, pgTAP verdi col runner |
| 2026-11-22 | BE | R-1 fatta: repository delle anagrafiche sui verbi, colonne ammesse dal DB, test sui builder; R-4 non fatta (vuole il catalogo) |
| 2026-11-22 | Tid | R-4 al giorno del catalogo |
