# Piano DB — satelliti della fattura (indirizzi + piano rate)

> 🟢 **CANTIERE CHIUSO — 2026-08-22.** Il debito documentale del §4-bis è stato
> **scritto**, non trasferito: il documento si archivia.
>
> **Cosa è stato scritto il 22-08** (dettaglio nella tabella del §4-bis, aggiornata):
>
> | Guida | Cosa è entrato |
> | --- | --- |
> | `guide/termini-di-pagamento.md` | **pagina nuova** (in nav): catalogo, catena a 4 livelli, formula del piano rate, il termine che decide **quante fatture** nascono, cosa fare per una condizione fuori standard |
> | `cruscotti-fatturazione.md` | «Rendi definitive» **può rifiutare** (D-K) in §7.1 · nuova **§7.6** con le tre vie d'uscita (riporta in lavorazione / elimina dal lotto / annulla), incluse le due trappole (numero fiscale, fondi già postati) |
> | `fatturazione.md` | sezione **task dello step DRAFT** (snapshot indirizzi + intestazione, guard di uscita) · tabella del seed **corretta** (era ferma a 2 task su 4 e a EMESSA senza scadenze) · `fn_riporta_lotto_a_draft` accanto alla sorella che annulla · caduta del vincolo «solo MASSIVO» |
> | `gestione-degli-indirizzi.md` | nuova sezione **«Gli indirizzi congelati sui documenti»**: chi risolve e chi copia, la fattura che risolve **per istanza**, il congelamento oltre il pre-fiscale, l'indirizzo che non si cancella più |
> | `documenti-e-stampe.md` | il contesto della **fattura** viene dallo snapshot, non letto live: l'esempio con l'indirizzo letto a runtime vale ancora per i preventivi, non per le fatture |
> | `generazione-cliente.md` | nuovo **§3-bis**: il cliente porta i soli riferimenti a catalogo; i due campi liberi sono stati eliminati il 31-07 |
> | `gestione-ordini.md` · `gestione-preventivi.md` | il termine **determina quante fatture nascono** (D-7), come nota nel punto in cui il campo è descritto |
> | `gestione-dei-pagamenti.md` | rimando alla pagina nuova: «chi decide quante rate» non è quella guida |
>
> ⚠️ **La riverifica del 22-08 ha trovato l'intestazione del 04-08 troppo
> generosa**, ed è la ragione per cui questa nota elenca il *contenuto* e non solo
> le spunte: due righe date per ✅ non lo erano. `gestione-degli-indirizzi.md` era
> **fermo al 25-03** e non nominava gli snapshot sui documenti;
> `documenti-e-stampe.md` mostrava ancora l'indirizzo letto live, cioè
> esattamente la riga che doveva cambiare. Anche `fatturazione.md` era ✅ solo a
> metà: la tabella dei task EMESSA era aggiornata, l'«esempio concreto (seed)»
> due schermate più sotto era rimasto indietro di due task.
> *Lezione operativa*: una spunta su una riga di debito documentale va messa
> **rileggendo il file**, non ricordando di averlo toccato — vale come per il
> `databasechangelog`.
>
> ⚠️ **Una riga era già colata via.** La voce «verbo nuovo nel drawer lotto» era
> stata trasferita al
> [piano-db-ritorno-lotto-a-draft.md](piano-db-ritorno-lotto-a-draft.md) §7,
> che è stato **archiviato come chiuso** portandosela dietro non evasa. È stata
> evasa qui, e la riga là è stata marcata.
>
> ---
>
> 🟢 ~~**STATO AL 2026-08-04 — cantiere tecnico CHIUSO, resta solo debito documentale.**~~
> *(superato dal box qui sopra: il debito è stato scritto il 22-08)*
>
> * **Tutte le fasi sono chiuse** (1, 2, 3a, 3b, 4, 4b + cantiere intestazione);
>   la **Fase 6** è stata estratta il 03-08 nel
>   [piano ritorno-lotto-a-draft](piano-db-ritorno-lotto-a-draft.md),
>   **anch'esso chiuso e archiviato** il 04-08 su entrambi i lati (6-A e 6-B).
> * Il **lato applicativo** del §3.5 è finito: le quattro voci che il piano BE/FE
>   teneva nel suo §4-bis (flag `esclusa`, ritorno a DRAFT/eliminazione
>   per-fattura, rinomina D-L, metà applicativa di D-Q) sono state chiuse il
>   04-08. Restano lì **tre decisioni di prodotto**, non lavoro tecnico.
> * ⬜ **L'unico residuo è il §4-bis di questo documento**: le guide utente.
>   Misurato sul contenuto reale il 04-08 — **4 fatte su 9**:
>
>   | Guida | Stato |
>   | --- | --- |
>   | `fatturazione.md` | ✅ numerazione + piano rate + snapshot |
>   | `gestione-dei-pagamenti.md` | ✅ raccordo piano rate ↔ incassi |
>   | `gestione-degli-indirizzi.md` | ✅ snapshot + risoluzione per istanza |
>   | `documenti-e-stampe.md` | ✅ indirizzo dallo snapshot |
>   | `cruscotti-fatturazione.md` | ⬜ precondizioni D-K + i verbi nuovi del drawer lotto |
>   | `generazione-cliente.md` | ⬜ il cliente porta solo `termine_pagamento_id` |
>   | `gestione-ordini.md` · `gestione-preventivi.md` | ⬜ il termine determina **quante** fatture nascono (D-7) |
>   | pagina nuova `config.termini_pagamento` | ⬜ non esiste |
>
>   ✅ **Nessuna guida cita più i campi legacy** `tipo_gg_scadenza_ft` /
>   `nr_giorni_scadenza`: quel rischio è chiuso.
>
> Il documento resta qui finché le 5 righe mancanti non sono scritte o
> trasferite altrove: archiviarlo adesso significherebbe perdere l'unico posto
> in cui quel debito è censito.
>
> ---
>
> **Owner:** DB (`dev/db-tid`) · **Data:** 2026-07-29 · **Stato:** da approvare
> (§2 contiene decisioni bloccanti)
>
> **Copre due brief fratelli**, che descrivono **un solo cantiere**:
> [brief-db-snapshot-indirizzi-fattura.md](brief-db-snapshot-indirizzi-fattura.md) ·
> [brief-db-generazione-scadenze-fattura.md](brief-db-generazione-scadenze-fattura.md)
>
> **Lavoro applicativo a valle:** [piano-be-fe-satelliti-fattura.md](piano-be-fe-satelliti-fattura.md)
>
> **Premessa che cambia il piano:** **non siamo in produzione**. I dati sporchi si
> correggono a mano (AGENTS.md §Workflow Safety), i breaking sono ammessi, e i
> due presidi «transitori» previsti dal piano BE/FE (fallback di ristampa,
> bonifica delle fatture storiche) **non vanno scritti**: §3.8.
>
> Questo documento fa due cose: **§1 verifica criticamente** i due brief contro
> il codice vivo, **§3 organizza il piano**. Le decisioni di dominio restano di
> Tid (§2). I brief restano il design-of-record: le correzioni che questo
> documento propone vanno riportate lì una volta approvate (§5).
>
> 📎 **Annotazioni del BE in coda al documento (§8, 2026-07-30).** Il BE ha
> verificato i perimetri su richiesta di Tid e ha aggiunto una sezione finale con
> le ricadute **di competenza DB**: numeri riverificati (chiude W-3, con **due
> correzioni**), una proposta su D-L, e il riallineamento dei blocchi applicativi.
> Sono annotazioni esterne: **il resto del documento non è stato modificato**.
>
> ⚠️ **Revisione 2026-07-29, seconda sessione.** Nel chiudere le domande aperte
> una alla volta è emersa una **decisione strutturante**: **D-I — un solo
> meccanismo per le condizioni di pagamento** (C-16). Le colonne
> `clienti.tipo_gg_scadenza_ft` / `nr_giorni_scadenza` e
> `fatture.giorni_pagamento` / `fine_mese` **si eliminano**; resta solo
> `termine_pagamento_id`, e `config.termini_pagamento` prende una forma piatta
> (giorni + booleano fine mese). Ne consegue una **Fase 3a** nuova e la
> cancellazione di D-2, D-3, D-4, §4.4-bis, §5.5 e 3 test del brief scadenze.
> Chi legge i brief senza questo documento non lo saprebbe: §5 elenca tutto.

---

## 0. Come è stata fatta la verifica

Contro la doc auto-generata `docs/it/dbzero/` (che riflette gli oggetti **vivi**),
i CSV di seed, le migration `20_code`, i pgTAP e il codice Django. **Non**
sui YAML come fonte di definizione (regola AGENTS.md).

~~⚠️ **Non verificate in questa sessione** le misure che richiedono il DB vivo:
il DB sta su un altro server, sono prese per buone dai brief.~~

✅ **Riverificate dal BE il 2026-07-30** sul DB di sviluppo (§8.1). Quasi tutte
confermate, **due sbagliate** — ed erano nel brief, non misurate da noi:

| Dato | Nei brief | Reale |
|---|---|---|
| `vendite.ordini` | «**0 righe in totale**» | **85 righe**, 7 con termine (1 valore distinto) |
| `vendite.preventivi` | «**0 righe in totale**» | **157 righe**, 19 con termine (1 valore distinto) |

La conclusione di §2-bis del brief scadenze — «D-7 oggi non frammenta niente» —
**regge, ma per un motivo diverso** da quello scritto: non perché i documenti non
esistano (ce ne sono 242), ma perché **il termine è sempre lo stesso** e non c'è
**nessuna attività fatturabile in attesa** (0). Il motivo giusto è più fragile del
motivo sbagliato: basta un secondo termine in catalogo perché la divergenza
diventi possibile.

Ricaduta operativa in **3b.5**. Tutto il resto è stato riletto sul codice.

---

## 1. Verifica critica

### 1.1 Cosa risulta confermato

| # | Affermazione del brief | Esito |
|---|---|---|
| V-1 | `fn_resolve_termini_pagamento` usa `termini_pagamento_id` (plurale) dove le tabelle hanno il singolare | ✅ **confermato** su tutti e tre i rami; e `vendite.contratti` **non ha affatto** colonne di pagamento (il ramo contratto è doppiamente morto) |
| V-2 | Il lookup di `fn_get_or_create_fattura_header` non filtra `utility_id`, e l'INSERT non scrive le condizioni di pagamento | ✅ **confermato**, riletto il corpo vivo |
| V-3 | `fn_build_fattura_key` ritorna 7 elementi con il BA **padre** | ✅ **confermato** |
| V-4 | `vendite.fatture` ha già `giorni_pagamento` (smallint), `fine_mese` (boolean), `termine_pagamento_snapshot` (jsonb), `modalita_pagamento_id` | ✅ **confermato** — §4.4-bis del brief scadenze regge |
| V-5 | Corsia GIORNALIERO/EMESSA (`fatturazione_pipeline` id 2) ha `processi = []` | ✅ **confermato** |
| V-6 | `fatture_indirizzi` è identica alle sorelle, con trigger whitelist fail-closed; nel seed `FATTURE` → `FATT` è già `obbligatorio = true` | ✅ **confermato**. `script.fn_indirizzi_obbligatori_mancanti('FATTURE', …)` **già oggi** segnala `FATT`: manca solo il trigger che la interroga |
| V-7 | `trgfn_fatture_righe_guard_congelamento` è il modello del lock, con bypass GUC | ✅ **confermato**, ed è clonabile *anche* nella parte non ovvia: l'uscita anticipata quando lo stato è NULL è ciò che rende innocua la DELETE in CASCADE dalla testata |
| V-8 | `config.termini_pagamento.unita_intervallo` è morta e incoerente nel seed | ✅ **confermato**: tutte e 4 le righe hanno `unita_intervallo='G'`, comprese quelle con `tipo_offset` `F`/`N` |
| V-9 | La base di ripartizione è `totale_a_pagare`, non `totale_doc` (§5.1) | ✅ **confermato**: `fn_ricalcola_totali_fattura` calcola `totale_a_pagare = totale_doc + fondi + arrotondamenti` |
| V-10 | «Ultimo id occupato» dei CSV di seed: registry 18, task_policy 16 | ✅ **confermato** — ma vedi C-6 |

### 1.2 Rilievi che cambiano il lavoro

#### C-1 🔴 [indirizzi, D-1] La premessa «è la stessa cascata degli altri documenti» è **falsa**

Il brief motiva la risoluzione dall'anagrafica dicendo che è «la stessa cascata
che gli altri documenti applicano alla loro creazione», e che la fattura «è solo
l'ultimo anello che non la eseguiva».

Sul codice, gli altri documenti fanno **l'opposto**: **copiano 1:1 lo snapshot
del documento sorgente**. Testuale, dal corpo di `fn_push_preventivo_a_ordine`:

```sql
-- 4-bis) Cascata indirizzi (D-1): copia 1:1 gli snapshot del
--   preventivo filtrati sui tipi ammessi in ambito ORDINI.
INSERT INTO vendite.ordini_indirizzi (…)
SELECT v_ordine_id, pi.tipo_indirizzo_id, pi.snapshot, …
  FROM vendite.preventivi_indirizzi pi …
```

Idem `fn_genera_ddt_da_ordine` (→ `ddt_indirizzi`), `fn_push_offerta_a_contratto`
(→ `contratti_indirizzi`), `fn_crea_revisione_preventivo`. La risoluzione
dall'anagrafica avviene **solo alla radice** della catena (creazione del
preventivo/offerta, via picker FE + mixin Python).

**La decisione può restare quella** — e ha una motivazione forte che il brief
non usa: una fattura aggrega N sorgenti, e le attività *sourceless* (oneri di
commessa, consumi) **non hanno alcuno snapshot da copiare**, quindi la
risoluzione dall'anagrafica è l'unica regola che copre tutti i casi. Ma va
adottata sapendo che **è una scelta diversa da quella dei fratelli**, e che ha
una conseguenza concreta: la fattura può stampare un indirizzo **diverso** da
quello del DDT/ordine che sta fatturando, se l'anagrafica è cambiata nel
frattempo. Con la motivazione scritta nel brief, questo è un difetto; con la
motivazione giusta, è un comportamento voluto. → **decisione D-A**.

#### C-2 🔴 [indirizzi, §5.1 passo 1] La risoluzione «sul soggetto_ruolo del cliente» è **ambigua**: manca l'istanza

`anagrafiche.indirizzi` ha **due unique parziali**:

```
uq_indirizzi_ruolo_istanza_tipo    (soggetto_ruolo_id, istanza_utility_id, tipo)  WHERE istanza_utility_id IS NOT NULL
uq_indirizzi_ruolo_tipo_no_istanza (soggetto_ruolo_id, tipo)                      WHERE istanza_utility_id IS NULL
```

Cioè: **un soggetto_ruolo può legittimamente avere N indirizzi dello stesso
tipo** — uno per istanza utility, più uno generico. È il modello giusto per un
ERP di utilities: una persona con luce, gas e idrico è **un** soggetto_ruolo con
**tre** istanze, tre BA, tre clienti (l'invariante «1 BA = 1 istanza = 1 cliente»
citato dai brief **non** dice «1 soggetto = 1 istanza»).

Risolvere per `(soggetto_ruolo_id, tipo)` e basta restituisce quindi fino a N
righe: **non-determinismo**, esattamente lo stesso difetto del `LIMIT 1` senza
`ORDER BY` che il brief scadenze giustamente segnala su `clienti` (§4.2).

**Regola da scrivere nel brief:** risolvere con precedenza
`istanza_utility_id = ba.istanza_utility_id`, fallback `istanza_utility_id IS NULL`.
Il BA dà l'istanza; l'attività ce l'ha pure (`attivita_fatturabili.istanza_utility_id`
è `NOT NULL`).

#### C-3 🟠 [indirizzi, D-2] Senza C-2, i tre tipi opzionali sono una funzionalità vuota

`FORNITURA` è, per definizione, l'indirizzo **del punto di fornitura** — cioè
dell'istanza, non della persona. È proprio il caso che la colonna
`indirizzi.istanza_utility_id` esiste per rappresentare. Risolvendo per solo
ruolo, `FORNITURA` non si troverebbe quasi mai, e D-2 («tutti e quattro i tipi»)
produrrebbe in pratica solo `FATT`. Con C-2 applicato, D-2 diventa sensato.

#### C-4 🔴 [scadenze, §4.5] `totale_a_pagare <= 0` → errore: **confonde tre casi diversi**

`totale_a_pagare = totale_doc + fondi + arrotondamenti`, e i fondi sono
**negativi** (acconti, minimi già incassati). Quindi:

| Caso | Significato | Il brief oggi | Cosa serve |
|---|---|---|---|
| `NULL` | task fuori ordine (i totali non ci sono) | errore | ✅ errore `E_SCADENZE_BASE_NON_PRONTA` |
| `= 0` | fattura **interamente coperta** da acconti | errore | ❌ documento **legittimo** → zero rate, log informativo |
| `< 0` | nota di credito / acconto in eccesso | errore | ❌ documento **legittimo** → zero rate, mai raise |

Non è teorico: `chk_fatture_scadenze_importo_pos` è `CHECK (importo >= 0)`, cioè
una rata negativa **è impossibile per vincolo** — il modello ha già deciso che
una nota di credito non ha piano rate. Sollevare un errore critico bloccherebbe
il lotto in EMESSA su un documento corretto. → **decisione D-D**.

#### C-5 🟠 [scadenze, §4.4 pt.6 e §5.3] La formula del generatore non è specificata, e i CHECK esistenti la vincolano più di quanto il brief creda

Il brief chiede un generatore ma non scrive **come si calcola una data**. I dati
per scriverlo ci sono tutti; e un vincolo esistente chiude da solo la «domanda
aperta» §5.3:

```sql
chk_termini_pagamento_intervallo_uso
CHECK ( (tipo_offset IN ('G','F') AND intervallo IS NOT NULL)
     OR (tipo_offset IN ('M','N') AND intervallo IS NULL) )
```

`tipo_offset='M'` **non può portare un intervallo**: «ogni 2 mesi» non è
esprimibile, e nessuna riga del seed usa `M`. Stessa sorte per `ripartizione`:
`LIBERA` non ha tabella figlia (§5.4) e `PROPORZIONALE` non ha base di
proporzione. Sono valori **selezionabili ma non onorabili**.

→ Questo rilievo è stato **superato in meglio** da D-I/D-E (C-16): `tipo_offset`
non viene ristretto, viene **sostituito** da un booleano `fine_mese`, e i due
offset diventano `NOT NULL DEFAULT 0` sempre in **giorni**. Il vincolo contorto
qui sopra sparisce del tutto.

**Formula del generatore nel modello riformato** (copre le 4 righe del seed,
riscritte come da C-16):

```
rata n ∈ 1..numero_rate:
  data_scadenza = fattura.data + primo_offset_giorni + (n-1) * intervallo   -- giorni
  se fine_mese = true  -> la data risultante si sposta a fine mese
  importo = round(base / numero_rate, arrotondamento_decimali) con metodo arrotondamento_metodo;
           la differenza di quadratura va sull'ultima rata
```

Un solo ramo, nessun caso speciale: la «rata unica alla data fattura» è
semplicemente `numero_rate=1, primo_offset=0, intervallo=0, fine_mese=false`.

Nota minore: `numero_rate < 1` è già impossibile
(`chk_termini_pag_numero_rate_pos`), quindi quel ramo di
`E_SCADENZE_TERMINE_INVALIDO` è codice morto. Nel modello riformato l'unico ramo
vivo è `ripartizione` fuori da `UGUALI` — che però il CHECK ristretto rende
inserribile solo aggirando il catalogo. Il guard resta come **seconda linea**.

#### C-6 🔴 [entrambi] Collisione di ID nei seed

I due brief rivendicano **gli stessi id successivi** sugli stessi CSV:
`pipeline_task_registry` («ultimo id 18» in entrambi) e
`fatturazione_pipeline_task_policy` («ultimo id 16» in entrambi). Nessuno dei due
numera `pipeline_task_registry_impl` (ultimo id: **18** anche lì).

Applicati indipendentemente si pestano i piedi. Gli id vanno assegnati **una
volta sola**, qui: §3.1.

#### C-7 🟠 [scadenze, §4.8] L'invariante pgTAP citato **non protegge** la corsia GIORNALIERO

Il brief dice che «esiste un invariante pgTAP che pretende processi non
divergenti fra le due corsie». Il test esiste
(`test-pipeline-definitiva-numerazione-stampa-v1.sql`), ma il suo test 4 è:

```sql
SELECT count(DISTINCT processi) FROM vendite.fatturazione_pipeline
 WHERE stato_doc_fiscale_id = 8 AND attivo   -- solo DEFINITIVA
```

È **limitato allo step DEFINITIVA**. Aggiungere il task a EMESSA MASSIVO senza
toccare la corsia GIORNALIERO **non fa fallire nulla**: la divergenza resterebbe
muta, esattamente com'è muta oggi quella dei fondi e dell'IVA. La decisione su
`processi = []` va presa (→ **D-C**), e l'invariante va **esteso** agli altri
step, altrimenti il prossimo buco lo scopriamo di nuovo per caso.

#### C-8 🟠 [scadenze, D-1 + §4.6] Quando la fattura diventa EMESSA — e cosa vuol dire per il lock

Verificato su `pipeline_runner._execute_pipeline_step`: i task dello step girano
**prima**, e solo dopo si chiama `sync_lotto_fatture_stato` (con commento
esplicito: *«Eseguito DOPO i task dello step»*). Quindi durante lo step EMESSA le
fatture sono ancora in **DRAFT**. Due conseguenze:

1. il lock proposto (soglia `NOT IN ('DRAFT','EMESSA')`) è compatibile con D-1:
   **verificato, non assunto**;
2. `E_SCADENZE_FATTURA_BLOCCATA` può scattare **solo** su rerun/resume dello step
   EMESSA su un lotto già avanzato a DEFINITIVA. Lì un errore per-fattura
   marcherebbe il lotto in errore per una riesecuzione che non ha niente da
   correggere. Meglio: il **wrapper di lotto salta** le fatture oltre soglia
   (log non critico), la **funzione per-fattura solleva** (chi la chiama
   esplicitamente vuole fail-loud). → **decisione D-F**.

#### C-9 🟠 [scadenze, D-7] Il termine entra in chiave, la **modalità** no — e sta nella stessa identica posizione

D-7 si motiva così: «il sistema **permette** di scegliere un termine sul
documento, quindi quel termine **deve** essere rispettato in fattura». Il
sistema permette di scegliere anche la **modalità di pagamento**, e la testata
della fattura ne ha **una** (`fatture.modalita_pagamento_id`):

| Colonna | `clienti` | `ordini` | `preventivi` | `contratti` |
|---|---|---|---|---|
| `termine_pagamento_id` | ✅ | ✅ | ✅ | ❌ (non esiste) |
| `modalita_pagamento_id` | ✅ | ✅ | ❌ | ❌ |

Il ragionamento di irriducibilità di §4.2 («un valore unico che riceve N valori
diversi») vale **identico** per la modalità. Eppure i brief la chiedono in
testata (§4.2 pt.2) e in `meta.modalita_codice` (§4.4 pt.5) **senza dire da dove
viene**: non c'è nessuna catena definita per la modalità. O entra in chiave con
il termine, o si decide che viene solo dal cliente e che la scelta su
`vendite.ordini` viene ignorata — ma va deciso, non lasciato implicito.
→ **decisione D-B: entra**.

Con D-I (C-16) l'elemento aggiunto alla chiave è quindi la **coppia**
`(termine_pagamento_id, modalita_pagamento_id)`: due sole FK, confronto banale.
La tripla/quaterna con `giorni_pagamento`/`fine_mese` non serve più — quelle
colonne di testata **si eliminano**.

Dettaglio d'interfaccia utile: `config.modalita_pagamento` **non ha
`codice_interno`**, solo `codice` (`MP01`…`MP23`, che è già la codifica
FatturaPA `2.4.2.2 ModalitaPagamento`). Quindi `meta.modalita_codice` =
`modalita_pagamento.codice`, ed è una deroga consapevole alla convenzione
«sempre per codice_interno».

#### C-10 🟢 [D-7] Buona notizia che nessuno dei due documenti dice: **il gruppo fatturabile non si spacca**

Il piano BE/FE (§4, Fase 4) teme che «un gruppo con termini misti» si comporti
male e prevede un probabile follow-up. Non serve:
`fn_build_gruppo_fatturabile_key` produce `'<sorgente>:<uid>'` (un **singolo**
documento sorgente) oppure `'MAN:<commessa_id>'` (gli oneri di **una** commessa).
Un gruppo porta quindi **un solo** termine per costruzione: D-7 non può dividerlo
in due. Resta vero che una corsa **sull'intero mese** può produrre più fatture di
prima — ed è quello che lo smoke §3.3 del piano BE/FE deve sorvegliare.

#### C-11 🟠 [entrambi] Il lock si scrive **una volta**, non due

I due brief chiedono lo stesso trigger `_a10_` di congelamento, con la stessa
soglia e lo stesso bypass GUC, su due tabelle diverse. Con
`fatture_riepiloghi_iva` (che pure non ce l'ha) siamo a tre. Regola del 2:
**una** `trgfn_fattura_satellite_guard_congelamento()` parametrica
(`TG_ARGV[0]` = colonna FK, `TG_ARGV[1]` = codice errore), montata N volte —
non tre copie quasi identiche da tenere allineate a mano.

#### C-12 🟠 [indirizzi, §7] `fatture_indirizzi` è l'unica satellite senza **nessun** presidio di scope

| Tabella | RLS | guard scope emittente |
|---|---|---|
| `fatture_scadenze` | ✅ 2 policy | ✅ `trg_…_a10_guard_emittente_scope_ins_upd` |
| `fatture_righe` | ✅ (`20260729-01/02`) | — |
| `fatture_riepiloghi_iva` | ✅ (`20260729-04`) | — |
| **`fatture_indirizzi`** | ❌ | ❌ |

Il brief lo segnala come rischio lato BE; ma la simmetria costa poco e va chiusa
qui, nello stesso cantiere, non quando il consumer sarà già scritto.

#### C-13 🟠 [scadenze, §4.1 vs §4.2] Attenzione a non lasciare **due** risolutori

§4.1 chiede di riparare `fn_resolve_termini_pagamento`; §4.2 sposta la
risoluzione dentro `fn_build_fattura_key`; §4.4 ribadisce che il generatore
«legge e non risolve» proprio per non avere due punti che rispondono sulla
stessa fattura. Se però la funzione riparata resta **in piedi e non chiamata da
`fn_build_fattura_key`**, il secondo risolutore torna a esistere — con una firma
per-fattura che invita a usarlo.

**Regola:** una sola implementazione della catena. O `fn_build_fattura_key`
chiama `fn_resolve_termini_pagamento` (riscritta per lavorare **per attività** e
tornare la tupla), o la funzione viene **eliminata**. Un fix che la lascia
inerte è il modo migliore per ritrovarsela usata fra sei mesi.

#### C-14 🔴 [indirizzi] Il documento «nato da sé» prende **davvero** dall'anagrafica — ma con una catena a **due layer**, e il brief ne conosce solo uno

Domanda di Tid (2026-07-29): *«i fratelli copiano, ma se nascono senza sorgente
prendono da anagrafica, giusto? un ordine che nasce da sé da dove prende gli
indirizzi?»* — **sì**, ed è la conferma che chiude C-1. Ma il come conta:

`ordini_service.py:389` (ordine creato da zero) e `:521` (ordine da preventivo,
come riempitivo se la cascata DB non ha coperto lo slot) chiamano
`auto_assegna_indirizzo_default` (`_indirizzi_documento_helpers.py:149`). Tre
caratteristiche, tutte rilevanti per la fattura:

1. **è Python, non DB, ed è best-effort**: tutto il corpo sta in un
   `try/except Exception` che logga un warning e lascia creare il documento
   senza indirizzo. L'obbligo lo impone solo il guard DB all'emissione;
2. **riempie un solo slot**, il tipo «default» (`CON` se ammesso, altrimenti
   `FATT`, altrimenti il primo dell'ambito) — non tutti i tipi ammessi;
3. **la catena ha due layer**, e il brief indirizzi §5.1 cita solo il primo:

| Layer | Fonte | Cosa scrive |
|---|---|---|
| **RUOLO** | `anagrafiche.indirizzi` | `origine_indirizzo_id` **valorizzato** (riga agganciabile) |
| **SOGGETTO** | `anagrafiche.vw_indirizzi_resolved_soggetto` | `origine_indirizzo_id` **NULL** + `origine_soggetto_ruolo_id` valorizzato — è ciò che distingue «deriva dall'anagrafica del soggetto» dal vero una-tantum digitato |

Tre conseguenze operative:

**(a) Rischio di `E_INDIRIZZO_FATTURA_MANCANTE` falso.** Se il task fattura
guarda solo `vw_indirizzi_resolved_ruolo` (come scritto in §5.1), un cliente il
cui `FATT` vive sul layer SOGGETTO **fa fallire la fattura** — mentre il suo
ordine si era risolto benissimo. Il task deve fare la **stessa** catena a due
layer, non metà.

**(b) Regola del 2: la catena va estratta in DB.** Stiamo per scrivere la
**seconda** implementazione di «risolvi l'indirizzo dall'anagrafica»: la prima è
in Python, nel mixin. Due implementazioni = due risposte alla stessa domanda —
lo stesso difetto che C-13 segnala sul termine. Proposta:

```
script.fn_resolve_indirizzo_documento(p_soggetto_ruolo_id, p_istanza_utility_id, p_tipo_codice)
  -> (snapshot jsonb, origine_indirizzo_id bigint, origine_soggetto_ruolo_id bigint)
```

che incorpora i due layer **più** il filtro per istanza di C-2. La chiama il task
fattura; il helper Python si riduce a invocarla (SQL fuori dal mixin) quando il
BE farà la sua fase.

**(c) C-2 è un difetto anche dell'esistente, non solo del brief.** Il layer
RUOLO oggi ordina così:

```sql
ORDER BY array_position(...), i.istanza_utility_id NULLS FIRST
LIMIT 1
```

cioè **preferisce l'indirizzo generico e ignora l'istanza del documento**, e fra
i per-istanza sceglie a caso. Per un ERP di utilities è il rovescio di ciò che
serve. La funzione unica di (b) lo sistema **anche per i 5 documenti fratelli**.

**(d) La fattura è più esigente dei fratelli.** Sui fratelli l'auto-assegnazione
può permettersi di essere best-effort: c'è un operatore davanti con un pannello.
Nella pipeline di fatturazione non c'è nessuno, e il documento è fiscale: il task
deve essere **deterministico e fail-loud**. Si riusa la **catena**, non la sua
politica d'errore.

#### C-15 🟠 [scadenze, D-3] `G/F/M/N` sono **due domini diversi** con le stesse lettere — e D-3 copre solo metà dei casi

Precisazione di Tid (2026-07-29), verificata: quando il cliente non ha una
condizione «vecchia», si segue **il termine di pagamento**, e la tabella apposita
esiste — è `config.termini_pagamento`, agganciata da
`clienti.termine_pagamento_id` (FK `fk_clienti_termini_pagamento`). Il trigger lo
impone già: con `N` i giorni vengono **azzerati d'ufficio**, quindi la coppia
legacy semplicemente non è valorizzata e la catena scende al livello 2b.

Ma le stesse quattro lettere significano cose diverse nelle due tabelle:

| Tabella | `G` | `F` | **`M`** | `N` |
|---|---|---|---|---|
| `config.termini_pagamento.tipo_offset` | giorni | fine mese | **mesi** | nessun offset |
| `anagrafiche.clienti.tipo_gg_scadenza_ft` | giorni | fine mese | **manuale** | nessuna |

**Omografia da non confondere**: `M` su `tipo_offset` e `M` su `clienti` erano
due decisioni separate con motivi diversi. → **Superata da D-I** (C-16): entrambe
le colonne del cliente vengono eliminate, quindi la domanda su `clienti.M` cade
da sé. Il rilievo resta qui perché è **la motivazione** della riforma: tre posti
che scrivono la stessa cosa in tre modi, con la stessa lettera usata per tre
significati.

**Ricaduta su D-3 del brief**: dice «se il tipo è fine-mese la data si sposta a
fine mese; altrimenti conteggio giorni puri», cioè copre solo `G` e `F` e lascia
il lettore senza risposta su `M` e `N`. Da scrivere: con `M`/`N` la coppia legacy
**non è valorizzata** (il trigger azzera i giorni) → si scende al termine di
pagamento, e poi al default `TP_1RATA`.

> Conferma che la coppia sul cliente è un **residuo**: `anagrafiche.fornitori` ha
> solo `termine_pagamento_id`, nessuna coppia giorni/tipo. Il lato fornitori è
> già passato interamente al meccanismo strutturato.

#### C-16 🔴 [scadenze, tutto il §3-§5] Le condizioni di pagamento sono scritte in **tre grafie diverse** — e due si possono eliminare

Osservazione di Tid (2026-07-29), verificata e adottata come **D-I**. Il modello
dice la stessa cosa in tre modi:

| Dove | Come esprime «giorni + fine mese» | Termine strutturato |
|---|---|---|
| `anagrafiche.clienti` | `tipo_gg_scadenza_ft` (lettera `G/F/M/N`) + `nr_giorni_scadenza` | `termine_pagamento_id` |
| `anagrafiche.fornitori` | `giorni_pagamento` + `fine_mese` (**booleano**) | `termine_pagamento_id` |
| `vendite.fatture` | `giorni_pagamento` + `fine_mese` (booleano) | `termine_pagamento_id` |

⚠️ **Correzione a una mia affermazione precedente**: avevo scritto che i
fornitori usano solo il termine strutturato. Falso — hanno la coppia anche loro,
con nomi diversi (`giorni_pagamento`/`fine_mese`), ed è **usata** dal
`FornitoreDrawer` e dal repository.

**`config.termini_pagamento` sa già esprimere tutto**, e i 4 termini del seed si
riscrivono senza perdite nel modello riformato:

| Termine | `numero_rate` | `primo_offset_giorni` | `intervallo` | `fine_mese` |
|---|---|---|---|---|
| Rata unica (`TP_1RATA`) | 1 | 0 | 0 | false |
| 30 gg | 1 | 30 | 0 | false |
| 30 gg fine mese | 1 | 30 | 0 | **true** |
| 30/60 fine mese | 2 | 30 | 30 | **true** |

**Prova che `M` è indifendibile ovunque**: lo stesso valore significa tre cose
diverse in tre posti — `mesi` in `config.termini_pagamento.tipo_offset`,
`manuale` nella doc manuale di `clienti`, e **`Mese`** a video nel drawer cliente
(`opt_gg_mese`, identico in `it.json` e `en.json`). Un valore su cui database,
documentazione e interfaccia dicono tre cose diverse non è un valore: è un
malinteso con un CHECK intorno.

**Cosa cancella dal lavoro** — è il motivo per cui questa riforma va fatta
*prima* e non *dopo*:

| Sparisce | Perché |
|---|---|
| **D-2** (precedenza alla coppia legacy) | non c'è più una coppia a cui dare precedenza |
| **D-3** (semantica giorni / fine mese sul cliente) | vive nel catalogo, non sul cliente |
| **D-4** (guard di mutua esclusione) + `E_CLIENTI_CONDIZIONI_PAGAMENTO_AMBIGUE` | l'ambiguità non è più possibile **per costruzione**: la colonna che la creava non esiste |
| **D-H** (`M` = manuale sul cliente) | la colonna se ne va e si porta via la domanda |
| **§4.4-bis** (la «contraddizione risolta») | serviva solo a rappresentare il percorso legacy in testata |
| **§5.5** (`fatture.giorni_pagamento` / `fine_mese`) | tornano inutili → si **eliminano**, come chiedeva la prima stesura del brief |
| La tripla/quaterna in chiave | si riduce a `(termine_pagamento_id, modalita_pagamento_id)` |
| 3 pgTAP su 10 del §6 | precedenza D-2, semantica D-3, testata legacy 6-bis: non c'è più niente da testare |
| Il **secondo percorso** del generatore | resta un solo ramo (C-5) |

**Due conseguenze da non nascondere:**

1. **Cambia chi decide le condizioni.** Oggi un operatore scrive «62 giorni»
   direttamente sul cliente; domani deve esistere un termine «62 giorni» nel
   catalogo. È il disegno corretto — le condizioni diventano una tabella
   governata invece di testo libero per cliente — ma se il catalogo è povero
   l'operatore si blocca. **Seminare i termini comuni** (30, 60, 90, 30/60, e le
   versioni fine mese) fa parte del lavoro, non è un contorno.
2. **I fornitori restano fuori scope** (lato acquisti), e resterebbero l'unico
   posto con la vecchia grafia. Da tracciare come debito, non da fare qui.

#### C-17 🟠 [reset lotto] I nomi delle due funzioni di reset **mentono**, e i perimetri sono asimmetrici

Verificate leggendo i corpi vivi:

| Funzione | Cosa promette il nome | Cosa fa |
|---|---|---|
| `fn_reset_lotto_draft` | riporta il lotto in DRAFT | **annulla il lotto**: cancella tutte le fatture e imposta `stato_doc_fiscale = ANNULLATA`, `stato_operativo = CHIUSO`, `stato_lotto = COMPLETATO` |
| `fn_reset_lotto_fattura_draft` | riporta la fattura in DRAFT | **cancella la fattura** e libera le attività; il lotto non lo tocca (pretende che sia **già** DRAFT e ce lo lascia) |

In entrambe «draft» è la **precondizione**, non l'esito. Nessuna delle due porta
niente in DRAFT — la prima fa l'opposto.

**La separazione delle responsabilità però c'è già**, su tre livelli:
`fn_cleanup_fatture_by_ids` è la primitiva di pulizia (azzera fondi, cancella
note/riepiloghi/righe/log/link e la fattura, ripristina le attività); le due
funzioni sopra sono gusci sottili che ci mettono attorno il proprio guard. Non
serve rifattorizzare: serve **rinominare**.

**Asimmetria da sanare**: la funzione globale accetta fatture in DRAFT **o
EMESSA** («pre-fiscali»), quella singola **solo DRAFT**. Senza motivo — semmai
l'operazione singola è la più prudente. E con `fn_guard_lotto_fatture_stato_coerente`
ormai attivo, un lotto DRAFT non dovrebbe avere fatture EMESSA: quel ramo è
probabilmente morto.

> ✅ **Controllo di sicurezza per il nostro cantiere**: `fn_cleanup_fatture_by_ids`
> imposta `zeroerp.maintenance_reset_lotto_draft` come **prima** istruzione, quindi
> i nuovi lock di Fase 1 non romperanno la pulizia. Seconda rete: la primitiva non
> nomina `fatture_scadenze` né `fatture_indirizzi`, che se ne vanno per CASCADE
> quando cade la fattura — a quel punto la riga padre non esiste più e il guard
> esce in testa sullo stato NULL. Entrambe le protezioni servono: se un domani la
> primitiva cancellasse i satelliti **prima** della fattura, resterebbe solo la GUC.

#### C-18 🔴 [transizioni] «Da EMESSA si torna a DRAFT» è dichiarato a metà e **non implementato**

Disegno di Tid (2026-07-30): *EMESSA = documento non modificabile; per correggere
si riporta a DRAFT e si ricalcola*. Verifica sul modello:

- `config.stati_doc_fiscale_transizioni` **contiene** `EMESSA → DRAFT` (riga id 2,
  `ammesso = t`) — ma con **`solo_lotto = t`** e `meta {"tipo_lotto":"MASSIVO"}`:
  vale **solo per il lotto**;
- per la **fattura** la transizione **non è dichiarata**. `trgfn_fatture_guard_stato`
  cerca le righe con `solo_lotto = FALSE` — che sono `1→2`, `2→3`, `2→8`, `8→3`,
  `3→6`. Nessun `2→1`: una fattura che prova a tornare in DRAFT viene respinta con
  `E_LOTTO_PARAMETRO_NON_COERENTE`;
- **nessuna funzione esegue mai quella transizione**: `fn_reset_lotto_draft` (unica
  che tocca lo stato fiscale del lotto) pretende DRAFT e mette ANNULLATA;
  `fn_sync_lotto_fatture_stato` è «solo forward»; `_select_steps` non torna indietro;
- e un ritorno del solo lotto lascerebbe le fatture a EMESSA → al commit scatterebbe
  `fn_guard_lotto_fatture_stato_coerente` (`E_LOTTO_FATTURE_STATO_INCOERENTE`).

**La riga 2 della matrice è quindi inerte**: dichiara legale un'operazione che
nessuno compie e che la controparte lato fattura vieta. → **Fase 6**.

#### C-19 🔴 [numerazione] `fn_assign_numero_fattura` è il collo di bottiglia fiscale, e controlla **una cosa sola**

Domanda di Tid: *a EMESSA la fattura è già numerata?* **No.** Il numero si assegna
nella tappa **DEFINITIVA**, mentre la fattura è ancora EMESSA, e solo a fine tappa
il sync la porta a DEFINITIVA — tutto in una transazione. Commento esplicito in
`_handle_numera_fatture_task`: *«Così la fattura passa per EMESSA(2) prima della
numerazione, evitando il salto 1→8 vietato dalla matrice»*. Conferma indiretta:
l'emissione mirata si ferma a EMESSA per disegno (gate fiscale I-7).

**Conseguenza per la Fase 6**: tornare da EMESSA a DRAFT **non annulla mai un
numero fiscale**, perché a EMESSA il numero non c'è ancora. Il punto di non
ritorno è DEFINITIVA — e infatti dalla `8` la matrice non prevede ritorni.

**Conseguenza per D-K**: il presidio va in `fn_assign_numero_fattura`, non nel
wrapper `fn_numera_fattura_opz_emessa`. Lì esiste già un guard con **esattamente**
la stessa filosofia, aggiunto il 2026-07-28 dopo il caso delle fatture 207 e 208
(definitive e senza righe):

> *«rifiuta con `E_FATTURA_SENZA_RIGHE` una fattura priva di righe, **PRIMA di
> consumare il progressivo** (nextval non fa rollback: fallire dopo lascerebbe
> comunque un buco nella numerazione fiscale). È il punto **UNICO** in cui il
> progressivo viene assegnato — `fn_numera_fattura_opz_emessa` delega qui — quindi
> il presidio vale per qualunque percorso, senza doverli enumerare.»*

D-K non è quindi un'invenzione: è l'**estensione** di una decisione già presa
(`brief-fix-importi-riga-fattura-zero` §4.5 D3), da «niente righe» a «satelliti
incoerenti».

#### C-20 🔴 [arrotondamenti] Il ricalcolo converge, ma **D-7 lo rompe** — e la scomposizione in testata diventa falsa

Sospetto sollevato in revisione (R-1) e **verificato**: il ricalcolo di una
singola fattura **è stabile**. `fatture_arrotondamenti_scope` tiene un saldo
tecnico per ambito (BA, utility, tipo doc, emittente, valuta) e il meccanismo si
autocorregge:

| | saldo prima | raw | totale | `arrotondamento_attuale` | saldo dopo |
|---|---|---|---|---|---|
| 1ª esecuzione | 0 | 100,004 | **100,00** | −0,004 | −0,004 |
| 2ª esecuzione | −0,004 | 100,000 | **100,00** | 0 | −0,004 |
| 3ª | −0,004 | 100,000 | **100,00** | 0 | −0,004 |

Il totale non cambia e il saldo si ferma. **Il sospetto iniziale era infondato**:
il resume di `ricalcola_iva_lotto` e la Fase 6 non sono a rischio per questo.

**Ma la stabilità poggia su una condizione che D-7 toglie.** Oggi *chiave
documento ≡ chiave ambito*, uno a uno: la chiave di aggregazione ha due elementi
in più (`registro_id`, `reseller`) ma sono **determinati** dagli altri
(`fn_get_registro_id(tipo_doc)`, reseller dal BA). Con termine e modalità in
chiave (D-7/D-B), **due fatture dello stesso BA con termini diversi sono
documenti diversi che condividono lo stesso saldo di arrotondamento** — e al
rerun del lotto la prima rilegge un saldo che contiene ormai anche il contributo
della seconda: il suo totale cambia. È esattamente lo scenario che D-7 esiste per
produrre.

**Secondo difetto, già reale oggi.** Al rerun la coppia in testata passa da
`(precedente 0, attuale −0,004)` a `(precedente −0,004, attuale 0)`: il totale
resta giusto ma i due campi **non descrivono più quello che è successo** — la
fattura dichiara un riporto che non ha mai ricevuto. E
`arrotondamento_attuale` **finisce sul documento**
(`fattura_document_context_builder.py:168`).

**Rimedio in due pezzi (D-N):**

1. **chiave dell'ambito = chiave di aggregazione** — toglie la contaminazione
   fra fatture diverse introdotta da D-7;
2. **storno del proprio contributo**: leggere il saldo come
   `saldo_scope − COALESCE(f.arrotondamento_attuale, 0)` quando la fattura ne ha
   già uno. Così il ricalcolo **ripete** il primo invece di convergerci, e la
   testata resta vera. Il riporto fra un mese e l'altro continua a funzionare:
   si storna **solo** il contributo della fattura che si sta ricalcolando.

> 🔁 **È la terza volta che incontriamo lo stesso invariante.** Ogni elemento
> della chiave di aggregazione deve comparire in **tre** posti: il `WHERE` del
> lookup (§4.2 pt.3), la **testata**, e ora l'**ambito di arrotondamento**.
> Va scritto come regola, non come tre correzioni scollegate.

`test-ricalcola-totali-fattura-arrotondamento.sql` ha 6 casi e **nessuno di
riesecuzione**: il test di idempotenza avrebbe risposto in trenta secondi.

#### C-21 🟠 [`esclusa`] È una funzionalità **dormiente**: nessuno la valorizza, cinque punti la interrogano

`fatturazione_lotti_fatture.esclusa` **non viene mai impostata a `true`**:
nessun endpoint, nessuno scrittore Python, nessuna funzione DB.
`fn_get_or_create_fattura_header` la inserisce a `FALSE` e da lì nessuno la tocca.

È invece **letta** da: `fn_lotto_emittente_stati_lf`, `fn_lotto_stato_esecuzione_v2`,
`fn_guard_lotto_fatture_stato_coerente` (una delle sue **due sole eccezioni**),
l'outbox di stampa (*«una riga per ogni fattura non esclusa»*) e il filtro
dell'API fatture. Danno l'impressione che l'esclusione sia gestita.

Conseguenza laterale già vera: **se qualcuno la valorizzasse**, la fattura
verrebbe numerata (`list_fatture_by_lotto` non filtra) ma non stampata — cioè
brucerebbe un progressivo fiscale senza produrre un documento.

E il modo di togliere una fattura da un lotto **esiste già** ed è migliore:
`fn_reset_lotto_fattura_draft`. → **D-M: si elimina il flag.**

#### C-22 🔴 [reset per-fattura] Resettare **una** fattura libera le attività di **tutto** il lotto

`fn_reset_lotto_fattura_draft` chiama
`fn_cleanup_fatture_by_ids(ARRAY[p_fattura_id], v_lock_batch_id)` passando il
`lock_batch_id` **del lotto**. Dentro la primitiva:

```sql
UPDATE vendite.attivita_fatturabili SET lock_in_fatturazione=false, fatturato=false, ...
 WHERE (p_lock_batch_id IS NOT NULL AND lock_batch_id = p_lock_batch_id)   -- ⚠️ TUTTO il lotto
    OR fattura_riga_id = ANY(v_righe_ids);                                  -- solo questa fattura
```

Il primo ramo prende **tutte** le attività del lotto. Nel reset globale è
corretto (libera anche le attività agganciate al batch ma mai diventate riga);
nel reset **per-fattura** è sbagliato: sblocca e smarca come non fatturate le
attività delle altre fatture, che però restano lì.

Rimedio: la funzione per-fattura passa **`NULL`** come `p_lock_batch_id` — il
secondo ramo, da solo, libera esattamente le attività di quella fattura.

⚠️ **Va corretto prima** di estendere la funzione ai lotti EMESSA (D-N-bis),
altrimenti «tolgo una fattura sbagliata» diventa «smonto il lotto».

#### C-23 🔴 [arrotondamenti] Cancellare una fattura **lascia il suo arrotondamento** nel saldo d'ambito

`fn_cleanup_fatture_by_ids` non nomina **mai** `fatture_arrotondamenti_scope`
(zero occorrenze nel corpo). Azzera i fondi, cancella note, riepiloghi, righe,
log, link e la fattura, ripristina le attività — ma il contributo che quella
fattura aveva lasciato nel saldo d'ambito **resta lì**.

Conseguenza: **la fattura successiva dello stesso ambito eredita il riporto di un
documento che non esiste più.** Il saldo non è più il residuo di ciò che è stato
emesso, ma la somma di ciò che è stato emesso *e di ciò che è stato buttato*.

È un difetto **pre-esistente** (vale già per il reset lotto), ma:

- la **Fase 6** lo moltiplica, perché l'estrazione per-fattura (6.5) diventa
  un'operazione ordinaria invece che un caso di manutenzione;
- interagisce male con **D-N**: stiamo per rendere il ricalcolo idempotente
  facendogli stornare il proprio contributo, mentre la **cancellazione non lo
  storna affatto**. Metà del meccanismo sistemato e metà no è peggio di entrambe
  le metà rotte, perché sembra a posto.

→ **D-N pezzo 3**: `fn_cleanup_fatture_by_ids` storna dal saldo d'ambito il
`arrotondamento_attuale` di ogni fattura che cancella, **prima** di cancellarla.

#### C-24 🔴 [ruolo batch] `fatture_indirizzi` **non era nel perimetro** del ruolo di fatturazione

Trovato scrivendo la Fase 1.4 (2026-07-30). Il perimetro DML di
`zeroerp_batch_fatturazione` è dichiarato in
`scripts/sql/provision_db_role_batch_fatturazione.sql` e verificato dal `check_`
gemello. `fatture_scadenze` c'è (`'iud'`), `fatture_riepiloghi_iva` c'è,
`fatture_arrotondamenti_scope` c'è (`'iu'`) — **`fatture_indirizzi` no**.

Non è mai emerso perché **nessun batch ha mai scritto su quella tabella**: è
vuota. Il task di Fase 2 sarebbe il primo, e sarebbe anche il primo a fallire —
**BYPASSRLS salta la RLS, non i GRANT**
([[reference_batch_role_grants_provision_script]]).

Aggiunta `('vendite', 'fatture_indirizzi', 'iu')` a entrambi gli script. Grado
`'iu'` e non `'iud'`: il task fa **upsert** (`ON CONFLICT DO UPDATE`) e non
cancella mai; la pulizia arriva dalla `CASCADE` sulla testata, che non richiede
il privilegio sul figlio.

> Vale come promemoria per ogni tabella nuova che un batch dovrà scrivere: il
> perimetro è **fail-loud per disegno**, quindi il difetto si manifesta al primo
> giro reale e non prima.

---

## 2. Decisioni

### 2.1 Chiuse da Tid il 2026-07-29/31

| # | Decisione | Esito |
|---|---|---|
| **D-T** *(2026-08-02)* | **Annullare un lotto in bozza è una transizione di dominio, non una manutenzione** (da una segnalazione del BE) | ✅ **DECISA: `DRAFT → ANNULLATA` entra nella matrice `config.stati_doc_fiscale_transizioni`, per il lotto e senza vincolo di tipo.** Il difetto segnalato: un lotto DRAFT **senza fatture** non si annullava. La catena, riprodotta: la transizione non era in matrice, e a salvarla c'era la GUC `zeroerp.maintenance_reset_lotto_draft` — che però `fn_annulla_lotto_da_draft` **non accende**: la accende `fn_cleanup_fatture_by_ids`, che però **esce prima di accenderla** quando l'array di fatture è vuoto. Con fatture funzionava per effetto collaterale, a vuoto si bloccava. **Preesistente**, non introdotto dalla rinomina. Scartate le due strade più economiche (spostare il `set_config`, o farlo accendere al chiamante): entrambe lasciano la GUC **portante** per l'unica cosa che quella funzione esiste per fare, e lasciano il chiamante dipendente da un dettaglio interno del chiamato — il giorno che qualcuno riordina il cleanup, l'annullamento si rompe lontano da dove si è toccato. ⚠️ **Vale anche per il GIORNALIERO** (Tid, 2026-08-02): un giro giornaliero interrotto deve poter tornare indietro, quindi la riga **non** è vincolata a `tipo_lotto`. ✅ **Coda chiusa il 2026-08-02**: `20260802-01` toglie il rifiuto dei lotti non MASSIVO da **entrambe** le funzioni di reset, quindi la porta aperta dalla matrice ha ora chi ci passa. Verificato: lotto GIORNALIERO vuoto annullato |
| **D-S** *(2026-08-01)* | **Come fa la testata a portare la `utility_id` che sta in chiave** (emersa scrivendo 3b.3) | ✅ **DECISA: una colonna vera, `vendite.fatture.utility_id`, nullable con FK.** Il lookup non poteva confrontare l'utility perché la fattura **non la porta**: l'unico modo di conoscerla era la deduzione `COALESCE(lotto.utility_id, BA.utility_id)` dentro `fn_ricalcola_totali_fattura`, che però **non riproduce il valore in chiave** — la chiave prende l'utility dal BA dell'**attività** (il figlio), la testata porta il BA della **fattura** (il padre, D-P). Misurato il 2026-08-01: 42 BA di cui **zero con `parent_account_id`**, quindi oggi le due derivazioni coincidono e il difetto è **latente**; si accende al primo BA padre, cioè al presupposto stesso di D-P. Con la colonna sparisce anche una **seconda fonte di verità**: era quella deduzione a scegliere la riga di `emittenti_fiscali_utilities`, cioè **decimali e metodo di arrotondamento** del documento. Scartate: dedurre nel `WHERE` (deriva dal padre, il bug resta e diventa invisibile) e `meta->>'utility_id'` (un elemento di chiave in un jsonb, senza FK né tipo). ⚠️ Ricaduta: il ricalcolo **legge e non deduce**, quindi una fattura creata a mano senza utility cade su `E_CONFIG_MANCANTE` — le tre fixture pgTAP interessate sono state adeguate, **nessun fallback in funzione** |
| **D-R** ⭐ *(2026-08-01)* | **Dove vive il termine di pagamento «personalizzato» di un documento, e dove si spacca** | ✅ **DECISA: la commessa POSSIEDE il termine, e il termine entra nella sua chiave di raggruppamento.** Due colonne su `vendite.commesse` (`termine_pagamento_id`, `modalita_pagamento_id`, nullable) e **una decima dimensione** nella chiave di `fn_get_or_create_commessa`: un documento sorgente con termine diverso **non trova** una commessa riusabile e **ne apre una nuova**. Conseguenze: (1) la commessa ha **un solo** termine per costruzione, quindi a valle la fattura non si spacca mai *dentro* una commessa; (2) **non serve alcun arbitrato** fra le sorgenti — misurato: fino a **32 sorgenti per commessa**, di 4 tipi diversi (47 preventivi, 23 ordini, 3 contratti, 1 DDT) — perché sorgenti con termini diversi semplicemente non si incontrano; (3) la divergenza **si vede al push**, come una commessa in più, invece di comparire mesi dopo come una fattura in più che nessuno sa spiegare. ⚠️ **Il valore va confrontato con `IS NOT DISTINCT FROM`**, come già `competenza_dal/al`: il termine e' NULL nella grande maggioranza dei casi, e con `=` nessun push riuserebbe mai una commessa — moltiplicatore silenzioso. ⚠️ Le due dimensioni vanno **anche** nell'hash dell'advisory lock, o due push concorrenti con termini diversi corrono l'uno sull'altro. Retrocompatibile sul dato attuale: tutte le commesse hanno termine NULL e nessun documento ne porta uno, quindi **il raggruppamento di oggi non cambia** e la dimensione si accende solo al primo uso reale. 🔴 **D-R è effettiva solo se la catena legge la commessa** (trovato il 2026-08-01): `fn_resolve_termini_pagamento` era stata applicata **senza** quel livello, e con le colonne che nessuno legge la separazione pagata a monte tornava in **una fattura sola** col termine del cliente. Rimedio in `20260801-06`, riga **3b.1-fix** del §9 |
| **D-A** | Indirizzi fattura: risoluzione **sempre dall'anagrafica** (mai copia dai documenti sorgente) | ✅ **DECISA**. Confermata anche dal comportamento reale dei fratelli: quando nascono **senza sorgente** risolvono anch'essi dall'anagrafica (C-14). La fattura non è quindi un'eccezione — applica sempre il ramo che i fratelli applicano quando non hanno da chi copiare. ⚠️ La catena da replicare è quella **a due layer** di C-14, non il solo layer RUOLO |
| **D-I** ⭐ | **Un solo meccanismo per le condizioni di pagamento: il termine di pagamento** (C-16) | ✅ **DECISA.** Si eliminano `anagrafiche.clienti.tipo_gg_scadenza_ft` e `nr_giorni_scadenza`: il cliente porta **solo** `termine_pagamento_id`. Chi ha condizioni particolari usa un termine dedicato nel catalogo. Si eliminano di conseguenza `vendite.fatture.giorni_pagamento` e `fine_mese`, che esistevano solo per rappresentare il percorso legacy. È la decisione **strutturante** di questo cantiere: cancella D-2, D-3, D-4, D-H, §4.4-bis, §5.5 e 3 pgTAP |
| **D-E** | Forma di `config.termini_pagamento` | ✅ **DECISA.** `tipo_offset` (lettera `G/M/F/N`) → **sostituito** da `fine_mese boolean NOT NULL DEFAULT false`. `primo_offset_giorni` e `intervallo` diventano **`NOT NULL DEFAULT 0`** e si intendono **sempre in giorni**. Sparisce il CHECK `chk_termini_pagamento_intervallo_uso` (non ha più senso) e con esso ogni semantica del NULL. `ripartizione` → CHECK ricostruito su `IN ('UGUALI')`: `LIBERA` non è un algoritmo mancante ma un **pezzo di modello** mancante (nessuna tabella figlia per percentuali/date per rata), `PROPORZIONALE` non ha una base rispetto a cui essere proporzionale. Colonna `unita_intervallo` **eliminata** (§5.2). Guard `E_SCADENZE_TERMINE_INVALIDO` nel generatore come **seconda linea**. Motivo della scelta «togliere dal dominio» invece di «rifiutare a runtime»: un termine impossibile deve fallire quando si **salva la configurazione**, non settimane dopo durante il giro notturno. ⚠️ CHECK ricostruiti con `DROP IF EXISTS` + `ADD` in changeset **nuovo**, mai editando gli originali mergiati. ⚠️ Se un giorno servirà la rateizzazione **mensile**: si aggiunge allora, e il clamp a fine mese lo dà PostgreSQL nativamente (`date '2026-01-31' + interval '1 month'` = `2026-02-28`) |
| **D-O** *(da R-2)* | Come comporre lo snapshot per il layer **SOGGETTO** degli indirizzi | ✅ **DECISA: si estende `script.fn_snapshot_indirizzo`** con una variante per soggetto (`fn_snapshot_indirizzo_soggetto`). Motivo: quella esistente prende un `p_indirizzo_id` e legge `vw_indirizzi_resolved_ruolo`, ma gli indirizzi di soggetto **non hanno riga** in `anagrafiche.indirizzi` — il mixin Python infatti compone lo snapshot **a mano** per quel layer. Con la variante, la regola D-5 del design-of-record («mai comporre lo snapshot a mano») resta intera e la **composizione ha un solo proprietario**. L'alternativa — accettare l'eccezione — lascerebbe due formati da tenere allineati a mano |
| **D-M** | Il flag `fatturazione_lotti_fatture.esclusa` (C-21) | ✅ **DECISA: si elimina.** È dormiente — nessuno la valorizza, cinque punti la interrogano — e tiene in piedi un secondo modo, non funzionante, di fare ciò che il reset per-fattura fa già meglio. Un flag così è la premessa di un comportamento sbagliato il giorno in cui qualcuno lo valorizza senza conoscerne tutti i lettori. Da toccare: `fn_lotto_emittente_stati_lf`, `fn_lotto_stato_esecuzione_v2`, `fn_guard_lotto_fatture_stato_coerente` (che resta con la sola eccezione `critical`), outbox di stampa, filtro API, `types.py` |
| **D-N** ⭐ | Arrotondamenti: idempotenza e verità della testata (C-20) | ✅ **DECISA, rimedio in due pezzi.** (1) **Chiave dell'ambito = chiave di aggregazione**: `fatture_arrotondamenti_scope` prende anche `termine_pagamento_id` e `modalita_pagamento_id`, altrimenti D-7 fa condividere il saldo a due fatture diverse. (2) **Storno del proprio contributo al ricalcolo**: `fn_ricalcola_totali_fattura` legge `saldo_scope − COALESCE(f.arrotondamento_attuale, 0)`, così il ricalcolo **ripete** il primo invece di convergerci e i campi in testata restano veri — uno dei due va in stampa. (3) 🔴 **Storno alla cancellazione** (C-23): `fn_cleanup_fatture_by_ids` deve stornare dal saldo d'ambito l'`arrotondamento_attuale` di ogni fattura che cancella, **prima** di cancellarla. Senza, il saldo diventa la somma di ciò che è stato emesso *e* di ciò che è stato buttato. I tre pezzi vanno **insieme**: due su tre è peggio di zero, perché sembra a posto |
| **D-N-bis** ⭐ | Estrazione di una fattura da un lotto **EMESSA** | ✅ **DECISA: modello «reperto».** Una o più fatture non numerate si possono **togliere** da un lotto EMESSA: si **stacca** il collegamento al lotto, la fattura passa ad **ANNULLATA** e le sue **attività tornano libere** (il giro successivo produce la fattura giusta). Perché ANNULLATA e non DRAFT: lo stato ha già la semantica esatta — `applica_lotto = false`, `applica_fattura = true`, `is_abortito = true`, fase `CHIUSO` — mentre una DRAFT staccata sarebbe **ambigua** (sembra lavorabile e non lo è, entra nei conteggi delle bozze). Serve l'append della transizione `EMESSA → ANNULLATA` per la **fattura** (oggi la matrice non ce l'ha). La fattura estratta resta come **documentazione**: è l'artefatto diagnostico che dice cosa non andava, e alimenta una lista «estratte» nel cockpit. ⚠️ Non è riprendibile per disegno: il suo contenuto è la fotografia del dato sbagliato, e la correzione avviene **a monte** (commessa, anagrafica) |
| **D-K** ⭐ | Guard di coerenza **prima di consumare il numero fiscale** | ✅ **DECISA.** In `fn_assign_numero_fattura` (non nel wrapper: è il punto UNICO in cui il progressivo si consuma, e `nextval` non fa rollback — C-19), accanto al precedente `E_FATTURA_SENZA_RIGHE`. Blocca con `E_FATTURA_NON_NUMERABILE_INCOERENTE` se: `totale_a_pagare IS NULL` · ci sono righe ma nessun riepilogo IVA · `totale_a_pagare > 0` e nessuna rata o `Σ importo ≠ totale_a_pagare` · `totale_a_pagare <= 0` e ci sono rate (coerente con D-D). Motivo: oggi la numerazione **non controlla nulla** e numererebbe una fattura senza totali, senza IVA e senza rate — è ciò che avrebbe lasciato passare fino allo SDI i documenti della corsia GIORNALIERO (D-C). Non rincorre gli scrittori: verifica il **risultato**, quindi copre anche le cause future e il caso più probabile di tutti (il task scadenze che non ha girato affatto). ⚠️ **Costo reale**: romperà le fixture pgTAP che numerano fatture prive di satelliti — vanno adeguate |
| **D-L** | Le due funzioni di reset lotto (C-17) | ✅ **DECISA su tutti e quattro i punti.** (1) **Si rinomina su ENTRAMBI gli strati** (Tid, 2026-07-30): `fn_reset_lotto_draft` → `fn_annulla_lotto_da_draft`, `fn_reset_lotto_fattura_draft` → `fn_elimina_fattura_draft_da_lotto`, **e i nomi Python si allineano**. Il BE aveva proposto di rinunciare alla rinomina o di farla solo a DB (§8.2): **non accolto** — rinominare un solo strato scambia un disallineamento con uno peggiore, perché un nome che mente ma è coerente ovunque si impara una volta, mentre due nomi diversi per la stessa cosa si sbagliano ogni volta. ⚠️ Il **`task_code`** `reset_lotto_draft` del registry **resta**: è il nome del *task*, non della funzione, e vive nei CSV. Impatto misurato: `ALLOWED_TASK_FUNCTIONS` (`pipeline_repository.py:174`), repository, service, view, pgTAP; il **task_code** `reset_lotto_draft` del registry può restare invariato (è il nome del task, non della funzione). (2) **Sanare l'asimmetria** di perimetro fra la versione globale e quella singola. (3) 🔴 **Correggere l'over-free del `lock_batch_id`** (C-22): la funzione per-fattura deve passare `NULL`, altrimenti resettare **una** fattura libera le attività di **tutto** il lotto. Prerequisito di D-N-bis. (4) Il «ritorno a DRAFT» che il nome evocava **non esiste** e va costruito: → **Fase 6** |
| **D-F** | Rerun della tappa EMESSA su fatture oltre soglia | ✅ **DECISA.** La funzione **per-fattura solleva** `E_SCADENZE_FATTURA_BLOCCATA`; il **wrapper di lotto filtra** su DRAFT/EMESSA e salta le altre con log non critico. Verificato che oggi lo scenario **non è raggiungibile** dal giro automatico (`_select_steps` riparte dallo step corrente in errore o dal successivo, mai indietro): è un presidio, non una riparazione. Si fa comunque perché (a) la per-fattura sarà chiamabile da endpoint e (b) il fratello `fn_ricalcola_riepiloghi_iva_lotto` **non filtra** e la sua per-fattura solleva — quindi se lo scenario diventasse raggiungibile il giro esploderebbe già una riga prima. ⚠️ Nota: quella solleva `E_PARAMETRO_INVALIDO` per un problema di **stato** — codice fuorviante, da allineare quando si tocca quell'area |
| **D-J** | `clienti.termine_pagamento_id` obbligatorio? | ✅ **DECISA: resta nullable**, con fallback al default `TP_1RATA` |
| **D-G** | Bonifiche dei dati esistenti | ✅ **DECISA: non è un cantiere.** Sono **dati di test** ([[project_no_produzione_solo_sviluppo]]): si correggono o si cancellano al momento, senza migration né passi preparatori. I 2 clienti con la coppia legacy si ripuntano al catalogo dentro 3a.4; i clienti con `M` **si contano al momento dell'applicazione** (Tid: probabilmente nessuno); le 7 fatture senza snapshot si cancellano e rigenerano. Nessuna query di bonifica da preparare in anticipo |
| **D-D** | Base di ripartizione `totale_a_pagare` a zero o negativa | ✅ **DECISA**. `NULL` → `E_SCADENZE_BASE_NON_PRONTA` (unico caso che segnala un difetto reale: passi fuori ordine). `= 0` → **nessuna rata, nessun log**: fattura interamente coperta da acconti, situazione normale. `< 0` → **nessuna rata + log NON critico** sulla fattura: un saldo a favore del cliente va visto, perché a volte è corretto e a volte è un fondo configurato male. Motivi: i fondi `F_F_ADD_ACC` sono «addebiti/**accrediti**» e si sottraggono; `fn_ricalcola_totali_fattura` tratta esplicitamente il caso negativo in ogni ramo di arrotondamento (`ELSE -ceil(abs(...))`), quindi è uno stato **previsto** dal modello; `CHECK (importo >= 0)` su `fatture_scadenze` ha già deciso che un documento a credito **non si rateizza**. ⚠️ Un errore critico qui **bloccherebbe il lotto** al primo cliente con acconto capiente. La regola non cambierà con l'arrivo del tipo documento «nota di credito» (oggi `tipo_doc_fiscale` è FRONTOFFICE/BACKOFFICE: la nota di credito **non esiste** come tipo) |
| **D-C** | Corsia GIORNALIERO / step EMESSA (`fatturazione_pipeline` id 2, `processi = []`) | ✅ **DECISA: allineare i `processi` alla corsia MASSIVO** (fondi → IVA → scadenze), **lasciando il `rollback` com'è** — la corsia immediata arriva da sola fino alla numerazione, e una fattura numerata non si resetta: darle un percorso di reset sarebbe offrire un'uscita che il gate fiscale poi nega. **Più**: estendere l'invariante pgTAP a **tutte** le tappe, non solo DEFINITIVA (C-7). Motivo della decisione: la corsia immediata **non ha fermata** (`fatturazione_driver_service.py:55`) e nessun trigger ricalcola IVA/totali — con la tappa vuota emetterebbe **da sola** documenti numerati, stampati e inviati allo SDI senza riepilogo IVA né totali. Non è una corsia che calcola meno: è una corsia che emette documenti invalidi appena qualcuno l'accende |
| **D-Q** ⭐ | Cosa fa il lotto davanti a una fattura **difettosa** (emerso da 2.2) | ✅ **DECISA (Tid, 2026-07-31).** **Lo step si completa sempre**: una fattura difettosa non ferma le altre, che ricevono il loro lavoro per intero. **La fattura resta marcata in errore** — la catena esiste già ed è tutta DB: log `'C'` su `fatture_log` → `fn_sync_fatture_log_critical_lotto` → `fn_resolve_stato_esecuzione` (`critical` → `ERRORE`) su `fatturazione_lotti_fatture`. **Il lotto NON avanza** allo step successivo. Le vie d'uscita sono due: **estrarre il documento** dal lotto (modello D-N-bis) oppure **rilanciare lo stesso step** — ero su DRAFT rilancio DRAFT, ero su EMESSA rieseguo EMESSA. Tre conseguenze operative: **(1)** perché il rilancio funzioni, **ogni task ritira le proprie segnalazioni** quando il problema è risolto (`disabilitato = true` filtrando su `meta->>'source'`, mai quelle altrui) — implementato in 2.2, **da replicare in Fase 4**; senza, si corregge l'anagrafica, si rilancia e la fattura resta in errore per una ragione che non esiste più. Verificato il 2026-07-31: oggi **nessuno** porta `disabilitato` a true, i log critici cadono solo distruggendo la fattura. **(2)** ⚠️ Lo step **corrente riprova**, gli step **a valle saltano**: non è lo stesso filtro, e confonderli significa o impedire la correzione o far arrivare alla numerazione una fattura incoerente. **(3)** 🔴 **Metà applicativa, owner BE**: oggi `lotto_segnalazioni_service` blocca **qualunque** esecuzione in presenza di criticità, quindi vieta anche il rilancio dello stesso step — cioè proprio la via d'uscita. Va distinto «non avanzare» da «non ripartire». È il punto B dell'analisi 6.0, che qui morde prima. ⏭️ Resta aperto cosa fare delle **attività** della fattura in errore (restano agganciate al lotto): stesso terreno di D-N-bis, non blocca la Fase 2 |
| **D-P** | Indirizzi della fattura quando il BA ha un **padre** (punto sollevato scrivendo la 2.1) | ✅ **DECISA (Tid, 2026-07-31): la fattura è del padre, quindi indirizzi del padre.** La testata porta già il BA padre (`fn_build_fattura_key`: `COALESCE(ba.parent_account_id, a.billing_account_id)`) e con esso la sua istanza, che in gerarchia è **fittizia**: esiste per soddisfare il `NOT NULL` del BA, non per descrivere un punto di fornitura reale. 2.1 risolve quindi da `fatture.billing_account_id` **così com'è, senza sapere nulla della gerarchia** — nessun caso speciale da scrivere, e la regola vale identica con e senza padre. Tre conseguenze: **(a)** sul BA padre `FORNITURA` non ci sarà quasi mai, ed è il **caso normale, non un difetto** — solo `FATT` è obbligatorio (`tipi_indirizzi_allowed`, id 8), gli altri tre mancanti danno zero righe e nessun errore; **(b)** se sul padre non esiste un indirizzo legato all'istanza fittizia, la catena scende da sola al generico — è il ramo di fallback già scritto nella 2.0-b, non serve altro; **(c)** il **sotto-dettaglio per figlio** delle fatture utilities (gas/energia), dove vanno esposte la fornitura e l'istanza **reali** di ciascun figlio, **non potrà vivere in `fatture_indirizzi`**: `uq_fatture_indirizzi_uno_per_tipo_` ammette **una sola** `FORNITURA` per fattura. Andrà nel **corpo** del documento (righe / contesto documentale). È la separazione corretta anche per la FatturaPA — la testata è la controparte fiscale, il corpo è il dettaglio tecnico — quindi il vincolo non è un limite da aggirare ma la conferma che la decisione è coerente |
| **D-B** | La **modalità di pagamento** entra nella chiave di aggregazione | ✅ **DECISA: entra.** L'elemento di chiave è la **coppia** `(termine_pagamento_id, modalita_pagamento_id)` — due sole FK, coerenti con la testata e col `WHERE` del lookup (era una quaterna con `giorni_pagamento`/`fine_mese`: D-I le elimina). Catena della modalità: `ordini.modalita_pagamento_id` → `clienti.modalita_pagamento_id` → NULL (nessun default inventato: `config.modalita_pagamento` non ha una riga «default» e sceglierne una arbitrariamente finirebbe sulla FatturaPA) |

### 2.2 Ancora aperte

**Nessuna che blocchi.** Tutte le decisioni sono state chiuse da Tid il 2026-07-29/31.
Resta **parcheggiato** un solo punto, dentro D-Q: che fine fanno le **attività** di
una fattura rimasta in errore dentro un lotto. Non blocca la Fase 2 e vive sullo
stesso terreno di D-N-bis (estrazione), quindi si decide lì.

---

## 3. Piano di sviluppo

Quattro cantieri. L'ordine non è estetico: **indirizzi e scadenze sono
indipendenti**, ma la modifica della chiave (D-7) cambia *quante fatture
nascono* e va isolata, perché è l'unica parte che può rompere l'esistente.

```
FASE 1  fondamenta comuni  ─┬─► FASE 2  INDIRIZZI (step DRAFT)   ─► guard FATT
                            │
                            └─► FASE 3a  RIFORMA condizioni di pagamento (D-I/D-E)
                                    │
                                    └─► FASE 3b  CHIAVE (D-7)  ─► FASE 4  SCADENZE + guard numerazione
                                                                       │
                                                                       ├─► FASE 5  BE/FE
                                                                       └─► FASE 6  RITORNO A DRAFT
```

⚠️ La **Fase 3a è nuova** e nasce da D-I: semplifica il modello *prima* che ci
costruiamo sopra la chiave e il generatore. Farla dopo significherebbe scrivere
due volte la stessa logica — una per il modello vecchio e una per quello nuovo.

### 3.1 Fase 1 — Fondamenta comuni (si scrivono una volta)

| # | Cosa | Note |
|---|---|---|
| 1.1 | `vendite.trgfn_fattura_satellite_guard_congelamento()` **parametrica** | C-11. Clone di `trgfn_fatture_righe_guard_congelamento`, inclusi il bypass GUC `zeroerp.maintenance_reset_lotto_draft` e l'uscita anticipata su stato NULL (che è ciò che rende innocua la DELETE in CASCADE) |
| 1.2 | Montaggio su `fatture_scadenze` e `fatture_indirizzi` | Soglia `NOT IN ('DRAFT','EMESSA')`, per `codice_interno` |
| 1.3 | Codici errore: **solo append** a `80_data/sql/config/messaggi_errore.csv` | Ultimo id occupato: **567**. Nuovi: `E_INDIRIZZO_FATTURA_MANCANTE`, `E_SCADENZE_TERMINE_MANCANTE`, `E_SCADENZE_BASE_NON_PRONTA`, `E_SCADENZE_TERMINE_INVALIDO`, `E_SCADENZE_FATTURA_BLOCCATA`, `E_FATTURA_SATELLITE_CONGELATO`, `E_FATTURA_NON_NUMERABILE_INCOERENTE` (D-K). ~~`E_CLIENTI_CONDIZIONI_PAGAMENTO_AMBIGUE`~~ **non serve più** (D-I: l'ambiguità non è più rappresentabile). **Nessun loader nuovo**: il `runOnChange` esistente ripesca il CSV |
| 1.4 | RLS + guard scope emittente su `fatture_indirizzi` | C-12. Simmetria con le tre satelliti sorelle |

**Allocazione ID seed (C-6), da rispettare in entrambi i cantieri:**

| CSV | INDIRIZZI | SCADENZE |
|---|---|---|
| `dbops/pipeline_task_registry.csv` | id **19** `snapshot_indirizzi_lotto` | id **20** `genera_scadenze_lotto` |
| `dbops/pipeline_task_registry_impl.csv` | id **19** | id **20** |
| `vendite/fatturazione_pipeline_task_policy.csv` | id **17** (pipeline 1), **18** (pipeline 8) | id **19** (pipeline 3), **20** (pipeline 2) |

⚠️ Con D-C la corsia GIORNALIERO/EMESSA (pipeline **2**) va riempita per intero
— non solo con il task scadenze, ma anche con i due fondi e `ricalcola_iva_lotto`
che oggi le mancano. Servono quindi **3 task_policy in più** per la pipeline 2
(`genera_fondi_source_lotto`, `applica_fondi_lotto`, `ricalcola_iva_lotto`,
scope `EMESSA` + `tipo_lotto GIORNALIERO`): id **21-23**. Senza, quei task
girerebbero senza `task_run` né resume.

### 3.2 Fase 2 — Cantiere INDIRIZZI (step DRAFT)

Indipendente da tutto il resto: **si può partire da qui**, ed è il cantiere che
chiude un difetto di conformità fiscale reale (la ristampa che cambia).

| # | Cosa |
|---|---|
| 2.0-a | **`script.fn_snapshot_indirizzo_soggetto(p_soggetto_id, p_tipo_indirizzo_id)`** → `(snapshot jsonb)` (D-O): gemella di `fn_snapshot_indirizzo` per il layer SOGGETTO, che non ha `indirizzo_id` da passare. **Stesso shape canonico**, così la composizione resta con un solo proprietario e la regola D-5 («mai comporre lo snapshot a mano») vale per entrambi i layer |
| 2.0-b | **`script.fn_resolve_indirizzo_documento(p_soggetto_ruolo_id, p_istanza_utility_id, p_tipo_codice)`** → `(snapshot, origine_indirizzo_id, origine_soggetto_ruolo_id)` — **unica** implementazione della catena (C-14b): layer RUOLO (via `fn_snapshot_indirizzo`, `origine_indirizzo_id` valorizzato) poi layer SOGGETTO (via 2.0-a, `origine_indirizzo_id` NULL e `origine_soggetto_ruolo_id` valorizzato), con precedenza `istanza_utility_id = <istanza>` e fallback `IS NULL` (C-2/C-14c) |
| 2.1 | `vendite.fn_snapshot_indirizzi_fattura(p_fattura_id)` → `(inserted_rows, updated_rows)`. Chiama 2.0 per ciascuno dei 4 tipi; `FATT` mancante → `E_INDIRIZZO_FATTURA_MANCANTE` scope FATTURA; `CON`/`FORNITURA`/`RES` mancanti → nessuna riga, nessun errore. **Deterministica e fail-loud**, non best-effort come il helper Python dei fratelli (C-14d) |
| 2.2 | `vendite.fn_snapshot_indirizzi_lotto(p_lotto_id, p_batch_size)` — stessa coppia di `fn_ricalcola_riepiloghi_iva_lotto` |
| 2.3 | Seed: task 19 + impl 19 + `processi` dello step DRAFT su **entrambe** le corsie (pipeline 1 e 8), dopo `generate_fatture_righe`; task_policy 17-18 |
| 2.4 | pgTAP: shape canonico · **risoluzione per istanza** (test nuovo: due istanze dello stesso soggetto con indirizzi diversi → ognuna il suo) · **layer SOGGETTO** (test nuovo: `FATT` assente sul ruolo ma presente sul soggetto → snapshot scritto con `origine_indirizzo_id` NULL e `origine_soggetto_ruolo_id` valorizzato, **nessun** `E_INDIRIZZO_FATTURA_MANCANTE` — C-14a) · più sorgenti → un solo `FATT` · whitelist · idempotenza · seed e posizione |
| 2.5 | **Poi** il guard `FATT` obbligatorio su `vendite.fatture` (modello DDT, `E_INDIRIZZO_DOC_OBBLIGATORIO`) + pgTAP · ⚠️ mai prima di 2.1-2.3 |
| 2.6 | Lock già montato in 1.2 + pgTAP (scrittura oltre EMESSA → errore; percorso reset → ammesso) |

### 3.3-a Fase 3a — Riforma delle condizioni di pagamento (D-I / D-E)

Va **prima** della chiave: è ciò che rende la chiave semplice invece che
complicata. Nessun dato in produzione, quindi si fa netto.

| # | Cosa |
|---|---|
| 3a.1 | **Seminare il catalogo** `config.termini_pagamento` con i termini comuni (30, 60, 90, 30/60, e le versioni fine mese) — append al CSV esistente, loader `runOnChange` già presente. È il prerequisito operativo di tutto il resto: senza catalogo, togliere i giorni dal cliente lascia l'operatore senza strumenti |
| 3a.2 | Riforma di `config.termini_pagamento`: `tipo_offset` → `fine_mese boolean NOT NULL DEFAULT false`; `primo_offset_giorni` e `intervallo` → `NOT NULL DEFAULT 0` (sempre **giorni**); DROP di `unita_intervallo`; DROP di `chk_termini_pagamento_intervallo_uso` e `chk_termini_pagamento_intervallo_range` (quest'ultimo si riscrive su `>= 0`); CHECK `ripartizione IN ('UGUALI')` ricostruito |
| 3a.3 | Riscrittura del **seed** dei 4 termini nella nuova forma (tabella di C-16) |
| 3a.4 | **Migrazione dei clienti**: per ciascuno con la coppia legacy, puntarlo al termine di catalogo equivalente (creandolo in 3a.1 se manca). A mano, sono 2; i clienti con `M` si contano qui, sul momento (D-G: dati di test, nessuna preparazione) |
| 3a.5 | DROP di `anagrafiche.clienti.tipo_gg_scadenza_ft` e `nr_giorni_scadenza`; DROP del trigger `trg_clienti_normalize_giorni_scadenza_ins_upd` e della funzione `trgfn_clienti_normalize_giorni_scadenza`; DROP del CHECK `chk_clienti_tipo_gg_scadenza_ft` |
| 3a.6 | DROP di `vendite.fatture.giorni_pagamento` e `fine_mese` (§5.5: tornano inutili) |
| 3a.7 | **Innesco applicativo**: appena cadono le due colonne, il drawer cliente e la catena BE vanno adeguati. ⚠️ L'elenco dei file **non sta qui**: owner e punti di intervento in [piano BE/FE §4-bis](piano-be-fe-satelliti-fattura.md). *Due elenchi della stessa cosa divergono; uno no* (proposta BE §8.3, accolta). Resta DB: `fn_update_cliente`, che è una funzione SQL |
| 3a.8 | pgTAP: **rimuovere** `test-clienti-normalize-giorni-scadenza-v1.sql` (il trigger non esiste più) e adeguare `create-cliente.sql` e `test-fn-get-evento-stato-corrente-cliente-v1.sql`, che valorizzano le colonne eliminate |
| 3a.9 | Doc: `dbzero/config/manual/termini_pagamento.md` e `dbzero/anagrafiche/manual/trgfn_clienti_normalize_giorni_scadenza.md` (quest'ultima da ritirare) |

⚠️ `nr_giorni_scadenza` e `tipo_gg_scadenza_ft` compaiono anche in
`db/changelog/baseline/` e `legacy/baseline_v2/`: sono **storia**, non si toccano
(memoria: mai modificare changelog mergiati).

⚠️ **Debito tracciato, non fatto qui**: `anagrafiche.fornitori` resta con la
grafia `giorni_pagamento`/`fine_mese` accanto al proprio `termine_pagamento_id`.
È il lato acquisti; va allineato con lo stesso criterio quando ci si lavorerà.

### 3.3-b Fase 3b — Cantiere CHIAVE (D-7): il pezzo rischioso, **da solo**

È l'unica fase che cambia il comportamento dell'esistente. Va applicata e testata
in isolamento, prima di appoggiarci sopra le scadenze.

| # | Cosa |
|---|---|
| 3b.0-a | **Il termine diventa un dato della commessa** (D-R): due colonne su `vendite.commesse` — `termine_pagamento_id`, `modalita_pagamento_id` — nullable con FK. La commessa lo **possiede**, non lo rispecchia: la sorgente lo propone alla nascita e poi esce di scena, quindi non c'è nessuno specchio da tenere in sync |
| 3b.0-b | **La chiave di raggruppamento della commessa passa a 10 dimensioni** (D-R): `fn_get_or_create_commessa` prende i due parametri nuovi e li porta nei suoi **tre specchi** — hash dell'advisory lock, `WHERE` della commessa riusabile, `INSERT`. **Un changeset solo**: toccarne due su tre è peggio che non toccarne nessuno. ⚠️ `IS NOT DISTINCT FROM`, non `=`: il termine è NULL quasi sempre e con l'uguaglianza nessun push riuserebbe più una commessa |
| 3b.0-c | **Guard di immutabilità**: una commessa aperta non può cambiare termine, perché è elemento della propria chiave — le attività già emesse si troverebbero su una chiave che non le descrive più. La risposta corretta è «apri una commessa nuova». Stesso schema degli altri elementi di chiave |
| 3b.1 | **Una sola** implementazione della catena (C-13): `fn_resolve_termini_pagamento` riscritta **per attività** → ritorna la **coppia** `(termine_pagamento_id, modalita_pagamento_id)` (D-B + D-I), oppure eliminata e la catena vive dentro `fn_build_fattura_key`. Fix inclusi: singolare, **rimozione del ramo contratto** (obbligatoria: `vendite.contratti` non ha più colonne di pagamento), filtro `cl.istanza_utility_id = ba.istanza_utility_id` al posto del `LIMIT 1`. Catena a **4 livelli** dopo D-R: documento sorgente → **commessa** → cliente del **BA padre** → default `TP_1RATA`. ⚠️ La modalità ha una catena **più corta**: `ordini` sì, `preventivi` no. ⚠️ Il cliente si risolve dal **BA padre** (Tid, 2026-08-01): la fattura si emette lì, quindi le condizioni sono le sue — prenderle dal BA dell'attività spaccherebbe in N ciò che deve restare una fattura |
| 3b.2 | `fn_build_fattura_key` → aggiunge la coppia agli elementi di chiave |
| 3b.3 | `fn_get_or_create_fattura_header` → **lookup** allineato alla chiave (aggiunge `utility_id` — bug preesistente — e la coppia) e **INSERT** che scrive `termine_pagamento_id` e `modalita_pagamento_id` |
| 3b.4 | ~~Guard D-4 su `anagrafiche.clienti`~~ — **non serve più**: con D-I le due condizioni contraddittorie non sono più rappresentabili |
| 3b.4-bis | **Arrotondamenti, pezzo 1 (D-N)**: `fatture_arrotondamenti_scope` prende `termine_pagamento_id` e `modalita_pagamento_id` in chiave d'ambito. **Va fatto nello stesso changeset della chiave**: separarli lascia una finestra in cui due fatture condividono il saldo (C-20) |
| 3b.4-ter | **Arrotondamenti, pezzo 2 (D-N)**: `fn_ricalcola_totali_fattura` legge `saldo_scope − COALESCE(f.arrotondamento_attuale, 0)` |
| 3b.4-quater | **Arrotondamenti, pezzo 3 (D-N / C-23)**: `fn_cleanup_fatture_by_ids` storna dal saldo d'ambito l'`arrotondamento_attuale` delle fatture che cancella, prima della `DELETE`. ⚠️ Stessa funzione toccata da D-L (over-free del `lock_batch_id`): **coordinare i due interventi** in un changeset solo |
| 3b.5 | pgTAP: **idempotenza del ricalcolo** (due esecuzioni → stesso totale **e stessa scomposizione** `precedente`/`attuale`; il secondo è il test che oggi manca) · **due fatture stesso BA con termini diversi** → saldi d'ambito distinti, e il rerun non sposta i totali · un test **per livello** della catena. ⚠️ **Correzione 2026-07-30**: il livello 1 **ha dati** (7 ordini e 19 preventivi con termine, §8.1) — il brief diceva «0 righe» ed era falso. Ma il termine è **sempre lo stesso**: per testare la **divergenza** serve comunque creare un **secondo termine di catalogo**, che è la vera fixture · due attività stesso BA termini diversi → **due** fatture · termine uguale → **una** · riesecuzione → nessuna terza · **utility diverse → due fatture** (regressione sul bug chiave/lookup) · invariante «ogni elemento della chiave compare nel `WHERE` del lookup» |

⚠️ Da rileggere nello stesso passaggio: `smoke-fatturazione-aggregazione-righe.py`
e i pgTAP che contano le fatture di un lotto, che oggi assumono l'aggregazione
vecchia.

### 3.4 Fase 4 — Cantiere SCADENZE (step EMESSA)

| # | Cosa |
|---|---|
| 4.1 | `vendite.fn_genera_scadenze_fattura(p_fattura_id)` → `(deleted_rows, inserted_rows)`. **Legge e non risolve**: prende `termine_pagamento_id` dalla testata, applica la formula **a ramo unico** di C-5, `DELETE + INSERT`, quadratura sull'ultima rata, `meta.modalita_codice` = `modalita_pagamento.codice`, scrive `termine_pagamento_snapshot`. `termine_pagamento_id IS NULL` → `E_SCADENZE_TERMINE_MANCANTE` (nessuna ambiguità residua da distinguere: D-I). Casi limite secondo D-D |
| 4.2 | `vendite.fn_genera_scadenze_lotto(p_lotto_id, p_batch_size)` — con lo **skip** delle fatture oltre soglia (D-F) |
| 4.3 | Seed: task 20 + impl 20 + `processi` step EMESSA dopo `ricalcola_iva_lotto` su **entrambe** le corsie; **riempimento della pipeline 2** (fondi + IVA + scadenze, D-C) + task_policy 19-23 |
| 4.3-bis | Estensione dell'invariante pgTAP a **tutte** le tappe (oggi copre solo DEFINITIVA — C-7): per ogni `stato_doc_fiscale_id` attivo, `count(DISTINCT processi) = 1` fra le due corsie |
| 4.4 | Doc concettuale da correggere: `dbzero/vendite/manual/fatture_scadenze.md` (base = `totale_a_pagare`, non `totale_doc`); `dbzero/config/manual/termini_pagamento.md` già riscritta in 3a.9 |
| 4.5 | pgTAP: quadratura · ribilanciamento (100,00/3) · `numero_rata` progressivo · `fine_mese = true` (incluso un caso a cavallo d'anno) · `totale_a_pagare = 0` → zero rate **senza** errore · `< 0` → zero rate + log non critico · idempotenza · lock · un test per codice di errore · seed e posizione. ~~Testata legacy (6-bis)~~ **eliminato**: non esiste più un percorso legacy da presidiare (D-I) |

### 3.4-bis Fase 4b — Guard di coerenza alla numerazione (D-K)

| # | Cosa |
|---|---|
| 4b.1 | In `fn_assign_numero_fattura`, **prima** di `fn_get_next_progressivo`: le quattro condizioni di D-K → `E_FATTURA_NON_NUMERABILE_INCOERENTE`. Stesso schema del precedente `E_FATTURA_SENZA_RIGHE` |
| 4b.2 | Codice errore: append a `messaggi_errore.csv` (Fase 1.3) |
| 4b.3 | Adeguare le fixture pgTAP che numerano fatture prive di satelliti — è lavoro reale, e la sua necessità è la prova che il guard serve |
| 4b.4 | pgTAP: una fattura per ciascuna delle quattro condizioni → rifiutata **senza** consumare il progressivo (asserire che il numero successivo non è saltato) |

⚠️ Fino all'applicazione di D-C il guard **bloccherà la corsia GIORNALIERO**. È il
comportamento voluto — meglio ferma che con documenti invalidi allo SDI — e i due
lavori stanno nello stesso cantiere, quindi si accendono insieme.

### 3.5 Fase 5 — BE/FE

Il [piano BE/FE](piano-be-fe-satelliti-fattura.md) resta valido, **meno due cose**
(§3.8) e **più una** (C-10 chiude il follow-up sui gruppi prima di aprirlo).

### 3.6 Fase 6 — Ritorno del lotto a DRAFT (C-18) → **ESTRATTA**

> ➡️ **Dal 2026-08-03 questa fase vive in un documento suo:**
> **[piano-db-ritorno-lotto-a-draft.md](piano-db-ritorno-lotto-a-draft.md)**.
>
> **Perché è uscita.** Stava qui per un vincolo d'ordine (§3.7 punto 6: la pulizia
> dei satelliti al ritorno si scrive quando i satelliti esistono già), non per
> parentela di tema — «satelliti della fattura» sono indirizzi e piano rate,
> quello è **riaprire un lotto**. **Il vincolo è soddisfatto**: Fasi 2 e 4 chiuse.
> E dal 2026-08-03 ha un **movente reale** (la fattura 2263) e un perimetro suo,
> spezzato in due slice.
>
> ⚠️ **Il registro di quel cantiere è il §7 di quel documento**, non il §9 di
> questo: qui non resta nessuna riga da aggiornare. Sono state portate là anche
> le eredità che servivano (C-18, C-19, D-Q, la correzione di 4.2, D-L.2, D-L.3,
> D-M, D-N-bis), che qui restano al loro posto come storia.

### 3.7 Ordine di accensione, non negoziabile

0. ⚠️ **Intreccio con il piano BE** (loro §8.4, accolto): la catena indirizzi
   passa in SQL, e il mixin Python va ripuntato sulla stessa funzione. L'ordine
   **non** è «BE prima» — la funzione deve prima esistere — ma:
   **DB 2.0-a/2.0-b** (crea `fn_snapshot_indirizzo_soggetto` e
   `fn_resolve_indirizzo_documento`) → **BE Fase 0** (ripunta il mixin) →
   **DB 2.1-2.5** e BE Fase 1.
   Se il task fattura partisse mentre il mixin è ancora sulla vecchia catena, i
   cinque documenti fratelli e la fattura risolverebbero **in due modi diversi**
   — cioè esattamente il difetto che C-14b vuole chiudere;
1. task indirizzi (2.1-2.3) → **poi** guard `FATT` (2.5);
2. semina del catalogo termini (3a.1) → **poi** migrazione clienti (3a.4) → **poi**
   DROP delle colonne (3a.5). Invertirli lascia clienti senza condizioni;
3. riforma (Fase 3a) → **poi** chiave (Fase 3b), che dalla riforma dipende;
4. chiave (Fase 3b) → **poi** generatore scadenze (Fase 4), che dalla chiave legge;
5. generatore scadenze (Fase 4) → **poi** guard di numerazione (Fase 4b): acceso
   prima, blocca ogni numerazione perché le rate non esistono ancora;
6. satelliti completi (Fasi 2 e 4) → **poi** ritorno a DRAFT (Fase 6), che deve
   saper ripulire ciò che quelle fasi producono.

### 3.7-bis Verifiche trasversali

**Non le duplichiamo qui**: l'elenco è in
[piano BE/FE §5](piano-be-fe-satelliti-fattura.md) e vale per entrambi i lati
(test Django, `check_i18n_keys.py`, build Vite, smoke rieseguiti). Due elenchi
della stessa cosa divergono — stesso criterio applicato in 3a.7 / 6.6 / 6.7.

Quello che aggiungiamo, perché è specifico del lato DB:

- **`scripts/pgtap-baseline.sh vendite`** prima *e* dopo ogni fase. La suite ha
  rossi preesistenti: senza il confronto non si distingue una regressione da un
  rosso noto, e ci si attribuisce colpe altrui o si mascherano le proprie;
- ⚠️ la baseline è un **registro di debito**: le fasi 3a e 6 **rimuovono** dei
  pgTAP (`test-clienti-normalize-giorni-scadenza-v1.sql`) e ne **adeguano** altri
  (`create-cliente.sql`, le fixture che numerano fatture prive di satelliti). Va
  aggiornata con `--update`, non lasciata a divergere;
- ⚠️ **Contare righe su una tabella con RLS senza il GUC operatore dà ZERO, non
  un errore** (trappola pagata dal BE il 2026-07-31: `vendite.fatture` misurata
  «0 righe» e usata per due decisioni, in realtà **8**). È il modo peggiore di
  sbagliare una misura, perché il fail-closed somiglia a un dato. Vale per
  `vendite.*` e per `anagrafiche.billing_account`; **non** per
  `anagrafiche.indirizzi`, `indirizzi_soggetti` e `soggetti_ruoli`, che RLS non
  ce l'hanno — verificato prima di fidarsi del censimento EF di §10.3 del brief
  intestazione. Prima di usare un conteggio per decidere, chiedersi se quella
  tabella ha RLS;
- **doc auto-gen `dbzero`**: si rigenera dopo ogni fase che tocca funzioni,
  tabelle o viste. È la fonte da cui il prossimo intervento leggerà le
  definizioni: se resta indietro, il prossimo parte da un DDL stale.

### 3.8 Cosa **non** si scrive, perché non siamo in produzione

| Previsto da | Cosa | Perché cade |
|---|---|---|
| piano BE/FE §4 Fase 2 | Fallback «transitorio» del context builder alla vista live per le fatture senza snapshot, + criterio documentato per rimuoverlo | Le 7 fatture storiche si **cancellano e rigenerano**. Scrivere un fallback significa scrivere codice che nasce già da rimuovere |
| piano BE/FE §4 Fase 5 | «Bonifica o esclusione» delle fatture storiche prima di accendere il guard | Idem |
| brief indirizzi §5.3 | «Con dati storici privi di snapshot va valutata una bonifica o l'accensione limitata alle fatture nuove» | Idem |
| brief scadenze §4.3 | Ordine obbligato e concordato per la bonifica dei 2 clienti | Resta la **decisione di dominio** (quale delle due condizioni è quella vera), ma è un `UPDATE` a mano, non un cantiere |

---

## 4. Stima

| Fase | Effort |
|---|---|
| 1 — fondamenta comuni (guard parametrico, codici, RLS, id) | ~mezza giornata |
| 2 — indirizzi (funzioni + seed + guard + 7 pgTAP) | ~1 giornata |
| **3a — riforma condizioni di pagamento (D-I/D-E)** | **~1 giornata** DB + ~mezza BE/FE. **Nuova**, ma si ripaga: toglie il guard D-4, 3 pgTAP e il secondo ramo del generatore |
| 3b — chiave D-7 (3 funzioni + 5 pgTAP) **+ arrotondamenti (D-N)** | ~1,5 giornate (l'ambito di arrotondamento va nello stesso changeset della chiave) |
| 4 — scadenze (2 funzioni + seed + doc + 8 pgTAP) | ~1 giornata (era 1,5: un solo ramo di generazione) |
| **4b — guard numerazione (D-K)** | ~mezza giornata, di cui buona parte è **adeguare le fixture pgTAP** |
| 5 — BE/FE | vedi piano BE/FE, meno il fallback, più il drawer cliente (3a.7) |
| **6 — ritorno a DRAFT + estrazione + rimozione `esclusa`** | **~mezza giornata di analisi (6.0, obbligatoria)** + ~1,5 giornate DB + verbo nel drawer e lista «estratte». Slice a sé, dopo le scadenze. La stima DB è **provvisoria**: dipende da cosa emerge da 6.0 |
| **D-L — rinomina + asimmetria + over-free `lock_batch_id`** | ~3 ore. Il punto 3 è una **correzione**, non una pulizia |

**Saldo della riforma D-I**: circa **+1 giornata** di lavoro nuovo, **−1 giornata**
risparmiata fra 3b e 4, più un modello con una sola grafia invece di tre. A costo
netto quasi nullo, e con il vantaggio che il debito non si accumula.

---

## 4-bis. Guide da aggiornare, per fase

Censimento fatto sul contenuto reale delle 40 guide in `docs/it/guide/`.
**Ogni fase aggiorna la propria documentazione contestualmente**, con due
eccezioni segnate «⏸ fine»: `fatturazione.md` e la pagina nuova sui termini di
pagamento, che conviene scrivere in un passaggio solo alla fine — altrimenti si
riscrive lo stesso capitolo quattro volte.

Due assenze che il censimento fa emergere: **nessuna guida menziona
`tipo_gg_scadenza_ft`/`nr_giorni_scadenza`** (meccanismo mai spiegato, e ora lo
eliminiamo) e **nessuna menziona `fatture_indirizzi`** (meccanismo mai spiegato,
e ora lo accendiamo).

| Guida | Cosa cambia | Fase | Peso | Stato |
|---|---|---|---|---|
| **`fatturazione.md`** (988 righe) | La tabella degli step della pipeline (2 task nuovi + riempimento corsia GIORNALIERO, D-C); la semantica del reset, che cambia con la rinomina D-L e con la Fase 6; da aggiungere piano rate e snapshot indirizzi | ⏸ **fine** | **grosso** | ✅ **22-08** — sezione task DRAFT, tabella del seed corretta, `fn_riporta_lotto_a_draft`, caduta del «solo MASSIVO». (Il piano rate e la §reset erano già entrati il 02-08 e il 04-08) |
| **`config.termini_pagamento` — pagina NUOVA** | Nessuna guida documenta il catalogo dei termini. D-E lo rimodella e D-I lo rende **l'unico** meccanismo delle condizioni di pagamento: diventa un oggetto di primo piano. Ed è anche la guida che serve all'operatore, che ora *deve* passare dal catalogo per un termine fuori standard | ⏸ **fine** | **nuova** | ✅ **22-08** — `guide/termini-di-pagamento.md`, in nav. Non duplica la scheda tecnica `dbzero/config/manual/termini_pagamento.md` (già scritta il 02-08): la guida è per l'operatore e ci rimanda |
| `cruscotti-fatturazione.md` | «Rendi definitive» acquista precondizioni (D-K): non numera più qualunque cosa. La Fase 6 aggiunge un verbo al drawer lotto | 4b, 6 | medio | ✅ **22-08** — §7.1 (D-K) e §7.6 (le tre vie d'uscita). ⚠️ Il verbo del drawer era la riga «trasferita» al cantiere ritorno-a-DRAFT e mai evasa: rientrata qui |
| `gestione-dei-pagamenti.md` | **Non parla affatto di scadenze e piano rate**, perché non esistevano. È la guida che deve spiegarli, e il posto giusto per dire cosa *non* si può ancora fare (riconciliazione rata↔incasso, fuori scope) | 4 | medio | ✅ **02-08** (+ rimando alla pagina nuova il 22-08) |
| `gestione-degli-indirizzi.md` | Spiega bene soggetto vs ruolo — la nostra catena a due layer — ma non dice nulla di **snapshot sui documenti** né della **risoluzione per istanza** (C-2) | 2 | medio | ✅ **22-08** — nuova sezione. ⚠️ Era data per fatta il 04-08: il file era fermo al **25-03** |
| `documenti-e-stampe.md` | Il contesto PDF documentato mostra `"indirizzo": "Via Roma 1, Milano"` letto live: dopo la Fase 2 viene dallo snapshot | 2 | piccolo | ✅ **22-08**. ⚠️ Era data per fatta il 04-08: quell'esempio era ancora lì, intatto |
| `generazione-cliente.md` | Il cliente perde due campi: le condizioni di pagamento vivono solo nel catalogo | 3a | piccolo | ✅ **22-08** — §3-bis |
| `gestione-ordini.md`, `gestione-preventivi.md` | Citano il termine di pagamento sul documento: con D-7 quel termine ora **determina quante fatture nascono**. È un cambio di conseguenze, non di forma | 3b | piccolo ma va detto | ✅ **22-08** |

> ⚠️ **Consuntivo del trasferimento (22-08):** delle due righe passate al
> cantiere estratto, quello ne ha evasa **una** (§reset di `fatturazione.md`,
> il 04-08) e si è archiviato **chiuso** con l'altra ancora aperta. La riga
> superstite — il verbo nuovo nel drawer lotto — è stata scritta qui il 22-08,
> in `cruscotti-fatturazione.md` §7.6. *Trasferire una riga di debito a un
> cantiere che sta per chiudere non la mette al sicuro: la nasconde.*

➡️ **Due righe passano al cantiere estratto** (2026-08-03): `fatturazione.md`
limitatamente alla **semantica del reset** e `cruscotti-fatturazione.md` per il
**verbo nuovo nel drawer lotto** si evadono in
[piano-db-ritorno-lotto-a-draft.md](piano-db-ritorno-lotto-a-draft.md) §7, non
qui. Il resto di `fatturazione.md` (step pipeline, piano rate, snapshot indirizzi)
resta debito **di questo** piano.

Doc auto-gen `dbzero/*/manual/` già previste nel piano: 3a.9 (`termini_pagamento`,
ritiro di `trgfn_clienti_normalize_giorni_scadenza`) e 4.4 (`fatture_scadenze`).

---

## 5. Ricadute sui due brief (da riportare, una volta approvato)

| Brief | § | Modifica |
|---|---|---|
| indirizzi | §4 D-1 | Riscrivere la motivazione (C-1 + C-14): i fratelli **copiano quando hanno da chi**, e risolvono dall'anagrafica quando nascono da sé — la fattura applica **sempre** quel secondo ramo, perché aggrega N sorgenti e le attività sourceless non hanno snapshot da copiare |
| indirizzi | §5.1 | Catena a **due layer** RUOLO→SOGGETTO (C-14) + risoluzione **per istanza** con fallback (C-2), estratte in `script.fn_resolve_indirizzo_documento` (C-14b) |
| indirizzi | §5.3-5.4 | Lock: rimando al guard parametrico comune (C-11); togliere la bonifica storica (§3.8) |
| indirizzi | §5.5 | Id seed fissati (C-6) |
| indirizzi | §7 | RLS/scope non è più «da valutare col consumer»: entra in Fase 1 (C-12) |
| scadenze | §4.1 + §4.2 | Una sola implementazione della catena (C-13) |
| scadenze | §4.2 | L'elemento di chiave è la **coppia** `(termine_pagamento_id, modalita_pagamento_id)` (D-B + D-I) |
| scadenze | **§3 D-2, D-3, D-4** | **Si eliminano**: con D-I la coppia legacy sul cliente non esiste più, quindi non c'è precedenza da stabilire, semantica da definire né ambiguità da presidiare |
| scadenze | **§4.3** | **Si elimina**: niente guard di mutua esclusione, niente `E_CLIENTI_CONDIZIONI_PAGAMENTO_AMBIGUE`. La bonifica dei 2 clienti resta, ma come **migrazione verso il catalogo** (3a.4), non come prerequisito di un guard |
| scadenze | **§4.4-bis** | **Si elimina** insieme a `fatture.giorni_pagamento`/`fine_mese`: la contraddizione che risolveva non può più nascere |
| scadenze | **§5.5** | Si ribalta: le due colonne **si deprecano davvero** (era la risposta della prima stesura, tornata giusta) |
| scadenze | §6 pt. 4, 5, 6-bis | **Si eliminano**: i tre test presidiavano il percorso legacy |
| — | nuovo | Il mixin Python `find_indirizzo_ruolo_per_tipi` va ripuntato su `script.fn_resolve_indirizzo_documento`: oggi preferisce l'indirizzo generico e ignora l'istanza (C-14c). Lavoro BE, ma è **una correzione**, non un refactor estetico |
| scadenze | §4.4 | Scrivere la formula (C-5) |
| scadenze | §4.5 | `totale_a_pagare` 0 / negativo non è errore (C-4); rerun → skip nel wrapper (C-8) |
| scadenze | §4.6 | Verificato: durante lo step EMESSA le fatture sono ancora DRAFT (C-8) |
| scadenze | §4.8 | L'invariante pgTAP citato copre solo DEFINITIVA: va esteso (C-7) |
| scadenze | §5.2-5.4 | `tipo_offset` → booleano `fine_mese`; `unita_intervallo` eliminata; `ripartizione` ristretta a `UGUALI` (D-E) |
| config | `manual/termini_pagamento.md` | Da **riscrivere** sulla nuova forma (3a.9). Nota: delle 4 anomalie che elenca, 3 erano già sanate (`intervallo` nullable, CHECK su `numero_rate` e decimali, lock di `codice_interno`) — la doc era stale |
| anagrafiche | `manual/trgfn_clienti_normalize_giorni_scadenza.md` | Da **ritirare**: il trigger non esiste più (3a.5) |
| — | **nuovo, fuori dai brief** | **Guard di coerenza alla numerazione** (D-K/C-19): oggi `fn_assign_numero_fattura` controlla solo l'assenza di righe. Fase 4b |
| — | **nuovo, fuori dai brief** | **Ritorno del lotto a DRAFT** (C-18): la transizione è dichiarata solo per il lotto ed è inerte. Fase 6 |
| — | **nuovo, fuori dai brief** | **Rinomina delle funzioni di reset**, asimmetria di perimetro e **over-free del `lock_batch_id`** (D-L/C-17/C-22) |
| — | **nuovo, fuori dai brief** | **Arrotondamenti**: l'ambito va allineato alla chiave, e il ricalcolo deve stornare il proprio contributo (D-N/C-20). Senza, D-7 rende i totali non riproducibili |
| — | **nuovo, fuori dai brief** | **Eliminazione del flag `esclusa`** (D-M/C-21) e **estrazione di una fattura da lotto EMESSA** verso ANNULLATA (D-N-bis) |
| piano BE/FE | §4 Fase 4 | Il follow-up sui «gruppi con termini misti» non serve (C-10) |
| piano BE/FE | §4 Fasi 2 e 5 | Cadono fallback e bonifica (§3.8) |

---

## 6. Regola generale emersa: la chiave di aggregazione ha **tre** specchi

L'abbiamo incontrata tre volte, ogni volta come una correzione isolata. È una
regola sola, e va presidiata con un test:

> **Ogni elemento della chiave logica del documento deve comparire, identico, in
> tre posti:** il `WHERE` del **lookup** che cerca la fattura esistente, le
> **colonne di testata** che la descrivono, e la **chiave d'ambito** degli
> arrotondamenti.

| Specchio | Difetto trovato | Dove si corregge |
|---|---|---|
| `WHERE` del lookup | `utility_id` è in chiave ma non nel `WHERE` (§4.2 pt.3) | 3b.3 |
| Colonne di testata | `termine_pagamento_id`/`modalita_pagamento_id` non venivano scritti | 3b.3 |
| Ambito arrotondamenti | non contiene termine e modalità → con D-7 due fatture condividono il saldo (C-20) | 3b.4-bis |

Se domani si aggiungesse un quarto discriminante alla chiave, i posti da toccare
sono questi tre. Il test che lo presidia va scritto una volta e vale per sempre.

---

## 7. Riscontro critico sul piano stesso (2026-07-30)

Passata avversariale richiesta da Tid dopo la chiusura delle decisioni. Le
verifiche hanno prodotto tre rilievi confermati (C-20, C-21, C-22), **due allarmi
rientrati** e alcune debolezze che restano.

### 7.1 Allarmi verificati e rientrati

| | Temevo | Realtà |
|---|---|---|
| Idempotenza del ricalcolo | totali non riproducibili al rerun | **converge** su fattura singola; il problema vero lo introduce D-7 (C-20) |
| Fixture pgTAP dei clienti | `create-cliente.sql` condivisa da decine di test | referenziata **solo** dal file di baseline |
| Storico | il drop delle colonne rompe i mirror | `storico.clienti` e `storico.fatture` sono `snapshot jsonb`: gli snapshot vecchi conservano le chiavi, che è il comportamento corretto |

### 7.2 Debolezze che restano

| # | Debolezza | Mitigazione |
|---|---|---|
| **W-1** | La **Fase 6** è la parte meno istruita: disegnata in pochi scambi, mentre D-I è nata da una verifica su cinque tabelle | ✅ **affrontata**: è nato un passo di **analisi preliminare obbligatoria** con sei punti aperti, di cui uno già deciso (task_run) e uno rinviato (log critici). Il settimo — il saldo d'arrotondamento orfano — ne è uscito ed è diventato D-N pezzo 3. ➡️ **Dal 2026-08-03 quell'analisi vive in [piano-db-ritorno-lotto-a-draft.md](piano-db-ritorno-lotto-a-draft.md) §4**, non più in §3.6 |
| **W-2** | **Nessun criterio di «fatto» per le fasi DB.** La 3a è la fase con più superficie e nessun collaudo end-to-end | ✅ **chiuso dal BE (§8.5)**: gli smoke §3 del piano BE/FE passano dalla **pipeline reale** e coprono anche la 3a — `smoke-fattura-scadenze.py` asserisce già che la testata porti `termine_pagamento_id` e `modalita_pagamento_id` e che le rate quadrino, cioè che la catena **risolva attraverso il catalogo riformato**. Più una asserzione nuova sul vero rischio di 3a.4: **nessun cliente resta senza condizioni** dopo la migrazione |
| **W-3** | **Nessun numero è stato riverificato** | ✅ **chiuso dal BE (§8.1)** — e **aveva ragione di esistere**: due misure erano sbagliate. «0 ordini e 0 preventivi» era in realtà **85 e 157**. La conclusione su D-7 regge ma per un altro motivo, più fragile (§0). I clienti con `M` sono **0**, quindi quella verifica di D-G è chiusa senza lavoro |
| **W-4** | Stime **ottimistiche dove c'è frontend**: «3a ~1 giornata DB» copre nove punti | Trattarle come ordine di grandezza |
| **W-5** | **Undici decisioni in una sessione.** Le prime otto istruite una per una; le ultime sono arrivate quando l'inerzia del «confermo» era già presa | Ciò che è nato da una verifica (D-I, D-K, C-18, C-20) regge meglio di ciò che è stato deciso di slancio |

---

---

## 8. 📎 Annotazioni del BE (2026-07-30)

> **Chi scrive:** BE (`dev/backend-tid`). **Perché:** Tid ha chiesto una verifica
> dei perimetri — *«il DB non si è preso carico di attività che avevamo definito
> BE?»*. Esito: **nessuna sovrapposizione**, nessun doppio lavoro. Questa sezione
> raccoglie solo le ricadute **di competenza DB**; quelle applicative sono state
> recepite nel [piano BE/FE](piano-be-fe-satelliti-fattura.md) (§0, §4-bis, §9).
>
> Sono **annotazioni esterne, aggiunte in coda**: le sezioni §0-§7 di questo
> documento non sono state toccate.

### 8.1 W-3 chiuso: i numeri, riverificati sul DB — con **due correzioni**

W-3 chiedeva di ricontare all'apply. Fatto il **2026-07-30** sul DB di sviluppo,
contesto operatore. I dati confermano quasi tutto, **tranne due**:

| Dato | Nel piano/brief | Verificato 2026-07-30 | |
|---|---|---|---|
| Righe `vendite.fatture_scadenze` | 0 | **0** su 7 fatture | ✅ |
| Fatture con `termine_pagamento_id` / `modalita_pagamento_id` | 0 | **0** e **0** su 7 | ✅ |
| Clienti con coppia legacy (`G`/`F` + giorni) | 2 | **2** su 21 | ✅ |
| Clienti con `tipo_gg_scadenza_ft = 'M'` | «si contano sul momento» (D-G) | **0** | ✅ risolto |
| Clienti con `termine_pagamento_id` | 3 | **3** su 21 | ✅ |
| Clienti con **entrambi** (ambigui) | 2 | **2** — cioè tutti quelli con la coppia | ✅ |
| Termini in catalogo | 4 | **4** | ✅ |
| BA / istanze / clienti | 21 / 21 / 21 | **21 / 21 / 21**, zero condizioni discordanti | ✅ |
| BA figli (`parent_account_id`) | 0 | **0** | ✅ |
| `fatture_indirizzi` (vs sorelle) | 0 (16/10/5/1) | **0** · ddt **16** · ordini **10** · preventivi **5** · contratti **1** · offerte **0** | ✅ |
| Lotti | — | **29, tutti MASSIVO**; nessun GIORNALIERO mai eseguito | ✅ conferma C-7/D-C latente |
| FK satelliti → `vendite.fatture` | CASCADE | **CASCADE** su `fatture_scadenze`, `fatture_indirizzi`, `fatture_righe` | ✅ |
| **`vendite.ordini`** | **«0 righe in totale»** | **85 righe**, di cui **7 con termine** (**1** termine distinto) e 5 con modalità | ❌ **da correggere** |
| **`vendite.preventivi`** | **«0 righe in totale»** | **157 righe**, di cui **19 con termine** (**1** termine distinto) | ❌ **da correggere** |
| Attività fatturabili non ancora fatturate | — | **0** | ℹ️ |

**La conclusione di §2-bis del brief scadenze regge, ma per motivi diversi da
quelli scritti.** «D-7 oggi ha raggio d'azione nullo» era motivato con *«non ci
sono proprio ordini né preventivi»*: falso, ce ne sono 242. La frammentazione
resta però **improbabile sui dati attuali** perché:

1. dei documenti che portano un termine, il termine è **sempre lo stesso**
   (1 valore distinto sugli ordini, 1 sui preventivi) → nessuna divergenza
   possibile fra documenti dello stesso BA;
2. non c'è **nessuna attività fatturabile in attesa** (0), quindi nulla da
   aggregare adesso.

Perché la correzione conta comunque: se quel «0 righe» viene riusato per un'altra
decisione, l'errore si propaga. E cambia **un'attività del piano**: 3b.5 dice
*«il livello 1 non ha dati: la fixture è il lavoro»* — in realtà ci sono 7 ordini
e 19 preventivi con termine su cui appoggiarsi. Per testare la **divergenza** serve
comunque creare un **secondo** termine di catalogo, perché di distinti ce n'è uno.

### 8.2 Proposta su D-L: la rinomina è la parte rinunciabile

D-L contiene tre cose di valore molto diverso:

| Punto | Natura | Lavoro BE indotto |
|---|---|---|
| pt. 3 — **over-free del `lock_batch_id`** (C-22) | 🔴 **bug**: resettare *una* fattura libera le attività di *tutto* il lotto | nessuno |
| pt. 2 — asimmetria di perimetro fra le due funzioni | correzione | nessuno |
| pt. 1 — **rinomina** delle due funzioni | leggibilità | **4 righe obbligatorie** + disallineamento nominale |

Misurato: se rinominate, **devono** seguire `pipeline_repository.py:174`
(`ALLOWED_TASK_FUNCTIONS`), `:1985`, `:2006` e un mock di test — altrimenti il
reset muore con `42883 function does not exist`. Tutto il resto sono **nomi Python
interni** (`pipeline_service.fn_reset_lotto_draft`, import, view, `@patch`),
invisibili al DB: per decisione di Tid **non si rinominano**, quindi resterebbe un
disallineamento («annulla» a DB, «reset» in Python).

> 💡 **Se l'obiettivo è minimizzare il lavoro applicativo, rinunciate al solo
> punto 1.** I punti 2 e 3 — che sono il valore vero, uno dei due è un bug — non
> inducono nessun lavoro BE, e il disallineamento nominale non nasce. La decisione
> è vostra: a noi costa poco in ogni caso, ma «gratis» è meglio di «poco».

### 8.3 Riallineamento dei blocchi applicativi (owner BE)

Quattro voci del piano vivono dentro fasi DB ma sono lavoro applicativo:
**3a.7** (drawer cliente + service/repository/view/error_policies), **6.6**
(filtro API + `types.py`; il resto è DB), **6.7** (verbo `LottoDrawer` + lista
«estratte»), **D-L** (le 4 righe di §8.2).

Non c'è doppio lavoro — nessuna è anche nel piano BE/FE — ma il rischio è
l'opposto: **l'omissione**. Il team DB non tocca i `.vue` né `types.py`; il BE non
apre una fase marcata DB. Ora sono elencate nel piano BE/FE **§4-bis** con owner
esplicito.

> **Proposta**: sostituire in 3a.7 / 6.6 / 6.7 l'elenco dei file applicativi con
> un rimando a quel §4-bis, tenendo qui solo l'innesco («appena cadono le colonne,
> il drawer va adeguato»). Due elenchi della stessa cosa divergono; uno no.

### 8.4 C-14b/c: lo spostamento della catena indirizzi vale più di una riga

`script.fn_resolve_indirizzo_documento` (2.0-b) è la scelta giusta — era la
seconda implementazione della stessa regola, e quella Python ha il difetto reale
di C-14c. Ma §5 la chiude con *«lavoro BE, ma è una correzione»*, e questo
**sottostima l'impatto**: quel mixin è montato su **cinque domini in esercizio**
(preventivi, offerte, ordini, DDT, contratti) e ripuntarlo **cambia quale
indirizzo propongono** — oggi il generico, domani quello dell'istanza.

Nel piano BE/FE è diventata la **Fase 0**, prerequisito di tutto, con ~mezza
giornata e test di regressione sui cinque flussi. Nessuna richiesta al DB: serve
solo che sappiate che **non è una riga**, e che la Fase 0 va **prima** della Fase 2
DB (indirizzi), altrimenti il task fattura girerebbe su una catena diversa da
quella dei fratelli — cioè il problema che C-14b vuole chiudere.

### 8.5 W-2: gli smoke del BE possono collaudare anche la Fase 3a

W-2 nota che le fasi DB non hanno un criterio di «fatto» end-to-end, e che la 3a è
la più esposta. Gli smoke del piano BE/FE §3 passano dalla **pipeline reale** e
possono coprirla senza nulla di nuovo: dopo la riforma,
`smoke-fattura-scadenze.py` asserisce già che la testata porti
`termine_pagamento_id` e `modalita_pagamento_id` e che le rate quadrino — cioè che
la catena **risolva attraverso il catalogo riformato**. Se la 3a ha rotto qualcosa,
lo smoke lo dice.

Aggiungiamo una sola asserzione, che è il vero rischio di 3a.4: **nessun cliente
resta senza condizioni** dopo la migrazione. Un conteggio, non un test complicato.

### 8.6 Chiuso da Tid: due cose che non si fanno

Coerenti con il vostro §3.8, e ora scritte anche nel piano BE/FE §9:

- **le 7 fatture storiche non si rigenerano** con una procedura: sono dati di
  test, se inciampano nel guard `FATT` si cancellano e si rifà un giro. Nessun
  codice, nessun passo di piano, nessuna bonifica;
- **niente fallback** nel context builder, per la stessa ragione.

> Criterio generale che ne emerge: davanti a un dato di test sbagliato la risposta
> è **rifare il dato**, non scrivere codice che lo tollera.

---

## 9. Registro di avanzamento

> **Come si usa.** Ogni passo ha uno stato: ⬜ da fare · 🟡 in corso · ✅ fatto e
> testato · ⛔ bloccato · ⏭️ rinviato. Si aggiorna **qui**, non altrove.
>
> **Uno step si dichiara ✅ solo quando**: changeSet **applicato** + pgTAP del
> passo **verdi** + `pgtap-baseline.sh` senza regressioni + doc auto-gen
> **rigenerata**. Scritto ma non applicato resta 🟡: è la differenza che ci ha già
> ingannato due volte (test verdi su codice morto).
>
> **Convenzioni di changeSet** — `db/changelog/migrations_v2/`, naming
> `YYYYMMDD-NN-<tipo>-<descrizione>-mctit.yaml`, **un changeSet per file**, sempre
> `logicalFilePath`, `runOnChange: false` nello stato committato. La numerazione
> `NN` è una **sequenza globale per data fra tutte le cartelle**: i numeri qui
> sotto si assegnano al momento della scrittura. Ultimo occupato: **20260802-27**.
>
> ⚠️ **Da dove si copia cosa** (le due metà hanno fonti diverse; sbagliarle è un
> errore silenzioso): il **corpo** di una funzione esistente dalla doc auto-gen
> `docs/it/dbzero/` (riflette l'oggetto vivo); la **firma + `RETURNS`**
> dall'**ultimo YAML** che la definisce (l'auto-gen scioglie i `%TYPE`); il
> `COMMENT ON FUNCTION` con i tipi **risolti**.

### Consuntivo

| | |
|---|---|
| **Fasi** | **Fase 1 ✅** · **Fase 2 ✅** (2.5 assorbita da I.4) · **Fase 3a ✅** · **cantiere intestazione ✅** (I.1-I.6, I.5 inclusa dal 2026-08-02) · **Fase 3b ✅** · **Fase 4 ✅ CHIUSA** (4.1-4.5, armamento incluso) · **Fase 4b ✅ CHIUSA** (guard D-K a sei condizioni) · ➡️ **Fase 6 ESTRATTA** il 2026-08-03 in [piano-db-ritorno-lotto-a-draft.md](piano-db-ritorno-lotto-a-draft.md) — **tutte le fasi di questo piano sono chiuse** |
| **changeSet** | **34 scritti e applicati** (`20260730-01`…`-08`, `20260731-01`…`-12`, `20260801-01`…`-10`, `20260802-01`, `-24`, `-25`, `-27`) + 9 codici errore + 2 script di ruolo + seed (task 2.3, catalogo termini, armamento pipeline **entrambe le corsie**, transizione D-T, matrice indirizzi ruolo EF) · **nessuno in sospeso** |
| **pgTAP** | **12 nuovi verdi** — ai 10 precedenti si aggiungono `test-pipeline-processi-invariante-v1` plan 7 (invariante `processi` esteso a tutte le tappe) e `test-numerazione-guard-coerenza-v1` plan 9 (guard D-K) · **13 adeguati** · **1 rimosso** · **3 rientrati dalla baseline** |
| **Doc** | ✅ **11 manuali di funzione scritti** (2026-08-02): 3 scadenze (`fn_resolve_termini_pagamento`, `fn_genera_scadenze_fattura`, `fn_genera_scadenze_lotto`), 5 indirizzi/intestazione (`script.fn_snapshot_indirizzo_soggetto`, `script.fn_resolve_indirizzo_documento`, `fn_snapshot_indirizzi_fattura`, `fn_snapshot_intestazione_fattura`, `fn_snapshot_fattura_lotto`), 3 guard (`trgfn_fattura_satellite_guard_congelamento`, `trgfn_fatture_guard_uscita_draft`, `trgfn_commesse_guard_chiave_immutabile`). ℹ️ **L'aggancio alla pagina auto-gen lo mette il generatore**: misurato 584 pagine con l'include e **solo queste 11 senza**, perché la rigenerazione non è ancora girata — nulla da cablare a mano. ✅ **Guide**: riscritta la sezione numerazione di `guide/fatturazione.md` (descriveva **un solo** guard e ripeteva la motivazione falsa sul `nextval`) e aggiunto a `guide/gestione-dei-pagamenti.md` il raccordo piano rate ↔ incassi, che non nominava le scadenze. ✅ **3a.9** (manuale `termini_pagamento` riscritto) · ✅ **4.4** (manuale `fatture_scadenze` + tabella task in `guide/fatturazione.md`) · ✅ `pratiche/manual/trgfn_sospensioni_giornale.md` riagganciato · ⚠️ i **due orfani** di `trgfn_clienti_normalize_giorni_scadenza` erano **già stati ritirati** da Tid in `c464fe50a`, non da noi · restano le guide del §4-bis · ℹ️ gli **indici** `dbzero/*/index*.md` portano ancora le descrizioni vecchie: si allineano alla rigenerazione, non si editano a mano |
| **Baseline** | ✅ **Passata piena del 2026-08-02 dopo tutti gli apply**: **410 file**, 105 rossi di cui 104 noti. L'**unica** regressione è `ui/test-lista-fornitori-seed` (conta «esattamente 15 colonne attive», il DB ne ha 13) ed è del **filone liste**, non di questo cantiere: il CSV `ui/lista_colonna.csv` è modificato e non committato, e questo cantiere non ha mai toccato `ui/`. ⚠️ È anche l'ennesimo **conteggio nudo** che si rompe senza dire quale colonna manchi |
| **Stato** | analisi chiusa, **20 decisioni** prese. 🎯 **Il cantiere è chiuso su entrambi i lati**: il BE ha registrato il task, aggiunto un guard d'ordine a runtime e prodotto lo **smoke verde** (`smoke-fattura-scadenze.py`, 10 casi + PDF nel caso 9 di `smoke-fatturazione-render-stampa.py`, entrambi con prova di mutazione). I **tre brief DB sono CHIUSI** (scadenze, indirizzi, intestazione). ➡️ **Dal 2026-08-03 la Fase 6 è estratta** in [piano-db-ritorno-lotto-a-draft.md](piano-db-ritorno-lotto-a-draft.md): di **questo** piano resta aperto il **solo debito documentale** delle guide del §4-bis — **4 fatte su 9** alla misura del 2026-08-04 (dettaglio nel box in testa), di cui due righe passavano al cantiere estratto: `fatturazione.md` §reset ✅ evasa lì, `cruscotti-fatturazione.md` ⬜ ancora aperta. Fuori piano, nell'ordine deciso da Tid: **incassi/riconciliazione rata↔incasso**, poi **`2.4 DatiPagamento`**, poi SDI |

### Fase 1 — Fondamenta comuni

| Passo | Stato | changeSet | Note |
|---|---|---|---|
| 1.1 `trgfn_fattura_satellite_guard_congelamento()` parametrica | ✅ **applicata** (2026-07-30) | `20260730-01` | Clone di `trgfn_fatture_righe_guard_congelamento` con bypass GUC e uscita su stato NULL. ⚠️ **Deviazione dal piano**: `TG_ARGV[0]` = colonna FK, **niente `TG_ARGV[1]`** — un codice errore solo (`E_FATTURA_SATELLITE_CONGELATO`), con la tabella nel messaggio e nel payload. Due argomenti dove ne basta uno sono due posti in cui sbagliare il montaggio, e `error_policies.py` mappa un codice solo |
| 1.2 Montaggio su `fatture_scadenze` e `fatture_indirizzi` | ✅ **applicato** (2026-07-30) | `20260730-02` | Due trigger in **un** changeSet: è la stessa regola sulle due tabelle, separarli inviterebbe ad armarne uno e dimenticare l'altro. `fatture_riepiloghi_iva` resta fuori perimetro: la sua riscrittura passa da `fn_ricalcola_riepilogo_iva_fattura`, che la soglia ce l'ha già |
| 1.3 Codici errore (append `messaggi_errore.csv`) | ✅ **applicato** (2026-07-30) | — (solo CSV) | 7 codici, **id 568-574**, nessun loader nuovo: il `runOnChange` esistente ripesca il file |
| 1.4 RLS + guard scope emittente su `fatture_indirizzi` | ✅ **applicato** (2026-07-30) · grant batch aggiunto al provisioning, che **gira in pipeline** (`ci.yaml`). Solo sul DB di sviluppo va rilanciato una volta | `20260730-03`, `-04`, `-05`, `-06` | Policy separate + armamento **isolato**, sul pattern di `20260729-01..05`. 🔴 **Prerequisito trovato ora (C-24)**: `fatture_indirizzi` **non era nel perimetro del ruolo batch** — aggiunta `'iu'` a `provision_db_role_batch_fatturazione.sql` e al `check_`. Senza, il task di Fase 2 fallirebbe: BYPASSRLS salta la RLS, **non i GRANT** |

### Fase 2 — Indirizzi (step DRAFT)

| Passo | Stato | changeSet | Note |
|---|---|---|---|
| 2.0-a `fn_snapshot_indirizzo_soggetto` | ✅ **applicata** (2026-07-31) · ✅ **fix padding applicato** (verificato 2026-07-31 sulla doc auto-gen: `NULLIF(btrim(...))` su tutti e sette i campi, e il `COMMENT` lo cita): `20260731-04` toglie il riempimento a spazi dei campi a larghezza fissa (`province.sigla` è `character(10)`, `stati.codice_iso2` idem) su **entrambe** le gemelle. Segnalato dal BE su giro reale (`"prov": "AV        "`). ⚠️ Il difetto era **noto e rinviato** dal 20260730-07, che sceglieva la parità di shape sulla correttezza: il rinvio è tornato indietro dopo che un documento fiscale l'aveva già congelato | `20260730-07`, `20260731-04` | Chiave `(soggetto_id, tipo)` e **non** un id: la vista soggetto espone un `indirizzo_id` che è la PK di un'**altra** tabella — passarlo alla gemella restituirebbe in silenzio l'indirizzo di ruolo con lo stesso numero. Assenza = zero righe, non errore |
| 2.0-b `fn_resolve_indirizzo_documento` | ✅ **applicata** (2026-07-31, da Tid) | `20260730-08` | Layer RUOLO (con **precedenza per istanza**, poi generico) → layer SOGGETTO. Determinismo dalle due unique parziali: candidati al massimo due, `ORDER BY (istanza IS NULL)` sceglie fra quelli. Assenza = zero righe. 🔴 **Ora che è applicata la Fase 0 del BE è sbloccata e va eseguita PRIMA di 2.1**: finché il mixin non è ripuntato qui, fattura e cinque documenti fratelli risolvono l'indirizzo in due modi diversi (C-14b) |
| 2.1 `fn_snapshot_indirizzi_fattura` | ✅ **applicata e coperta** (2026-07-31): pgTAP di 2.4 verdi | `20260731-01` | ✅ **Fase 0 del BE chiusa senza riserve prima dell'apply** (piano BE/FE §4 Fase 0). Risolve dal BA di **testata**, che in gerarchia è già il **padre**, senza casi speciali: **D-P**. Chiama 2.0-b per i 4 tipi ammessi in ambito `FATTURE` (`tipi_indirizzi_allowed`: **8 `FATT` obbligatorio**, 10 `CON`, 9, 1 `RES`); upsert su `uq_fatture_indirizzi_uno_per_tipo_`, coerente col grado `'iu'` concesso al ruolo batch in 1.4 |
| 2.2 `fn_snapshot_indirizzi_lotto` | ✅ **applicata e coperta** (2026-07-31): `db/pgtap/vendite/test-snapshot-indirizzi-lotto-v1.sql`, `plan(12)` **verdi** — provano **D-Q**, non la scrittura degli indirizzi (già coperta da 2.4): definitiva saltata senza fermare il giro, difettosa marcata mentre le altre proseguono, marcatura fino a `stato_esecuzione = ERRORE`, nota di lotto non critica, **rilancio dello stesso step** che ritira la propria segnalazione e sblocca, ritiro **chirurgico** (una segnalazione di altro task resta), idempotenza | `20260731-02` | **D-F esteso agli indirizzi** (Tid, 2026-07-31): il wrapper **filtra sullo stato prima di scrivere** e per le fatture oltre EMESSA non chiama nemmeno la per-fattura. **Il fallimento di UNA fattura non uccide il giro** (Tid, 2026-07-31): sotto-blocco `BEGIN/EXCEPTION` per fattura, marcatura `'C'` su `fatture_log` — che è ciò che le impedisce di diventare EMESSA — e le altre proseguono, così i clienti incompleti si vedono **tutti in una volta** invece di uno per esecuzione. Si cattura `raise_exception` (P0001), **non** `others`: un guasto di sistema deve continuare a salire. **D-Q** applicata: al successo il task **ritira le proprie** segnalazioni critiche sulla fattura, così il rilancio dello step la riporta a posto; lo step DRAFT **riprova** le fatture in errore e non le filtra (il filtro è degli step a valle). ⚠️ «Salta» non significa «lascia indietro»: una fattura definitiva **non ha lavoro da fare** — il suo snapshot è stato preso in DRAFT ed è quello definitivo. Il giro **non si ferma e non è fallito**, le altre fatture ricevono il loro lavoro completo, lo step si chiude normalmente, e la traccia è un **log non critico**. Il `critical` bloccherebbe l'avanzamento del runner, cioè proprio il blocco che si vuole evitare. Il modello `fn_ricalcola_riepiloghi_iva_lotto` **non** filtra: qui si devia, e la deviazione è voluta |
| 2.3 Seed pipeline DRAFT (corsie 1 e 8) | ✅ **parte inerte applicata** (2026-07-31, verificata dal test 15 di 2.4) · ✅ **armamento applicato** (2026-07-31): nodo in `fatturazione_pipeline.csv` righe 1 e 8, in coda a `generate_fatture_righe`. Confermato dal **test 16 di 2.4 uscito dallo skip e verde**, che è il presidio scritto apposta per questo momento. Sbloccato dalla chiusura dei tre punti BE di D-Q e dalla registrazione del task in `ALLOWED_TASK_FUNCTIONS:176` | — (solo CSV) | ✅ **Inerte**: append ai 3 CSV — `pipeline_task_registry` **19** (`snapshot_indirizzi_lotto`, dominio 1), `pipeline_task_registry_impl` **19** (`snapshot_indirizzi_lotto_default`), `fatturazione_pipeline_task_policy` **17** (pipeline 1, `{"scope":"DRAFT"}`) e **18** (pipeline 8, `+ tipo_lotto GIORNALIERO`), entrambe `annullabile = t`, `resume_mode = RESUME_TASK` (upsert idempotente, nulla di irreversibile). Nessun changeSet: i loader `runOnChange` esistenti ripescano i CSV. Nessun resync di sequenza: le tre tabelle si popolano **solo** da CSV. ⛔ **Armamento** = aggiungere a `fatturazione_pipeline.csv` (righe **1** e **8**), in coda a `generate_fatture_righe`, il nodo `{"task":"snapshot_indirizzi_lotto","fase":"Snapshot indirizzi fattura","params":{"implementation_key":"default"}}` — **solo dopo** i tre punti BE di D-Q. 🔴 **Il seed va in due tempi** (verificato 2026-07-31): il dispatch dei task **non è dinamico** — `pipeline_repository.py:160` tiene la whitelist Python `ALLOWED_TASK_FUNCTIONS`, e `snapshot_indirizzi_lotto` **non c'è**. Parte **inerte** (registry + impl + task_policy): seminabile quando si vuole, non fa partire nulla. Parte di **armamento** (il task nei `processi` dello step DRAFT): solo **dopo** che il BE ha registrato task e handler, altrimenti il lotto muore su un task sconosciuto. Stesso criterio del seed in due gruppi della coda di stampa |
| 2.4 pgTAP indirizzi | ✅ **verdi** (2026-07-31) | `db/pgtap/vendite/test-snapshot-indirizzi-fattura-v1.sql` — `plan(16)` | Copre: fallback generico → **precedenza per istanza** (esercitata aggiungendo l'indirizzo dell'istanza e rilanciando: se l'`ORDER BY` fosse sbagliato lo snapshot non cambierebbe), shape canonico, layer RUOLO/**SOGGETTO**, `FATT` mancante → errore, idempotenza `(0,0)`, un solo `FATT`, whitelist, seed 2.3, posizione (**skip** finché non armato: si accende da sé). **Fixture non distruttiva**: sceglie un BA il cui spazio indirizzi (ruolo **e** soggetto) è vuoto per i tipi ammessi in ambito `FATTURE` — criterio stretto apposta, perché un `RES` o un `FORNITURA` preesistente renderebbe i conteggi dei giri una lotteria sui dati. Non cancella nulla; se nessun BA qualifica, i test si **saltano** invece di fallire. ✅ Verificato sul DB di sviluppo il 2026-07-31: **30 candidati**, quindi il file non degenera in un tutto-skip. Incluso il test del layer SOGGETTO. ⚠️ **Due trappole da fixture segnalate dal BE** (loro §4-ter, misurate il 2026-07-31): **(a)** `CON` **non è inseribile sul ruolo cliente** — è ammesso al solo `tipo_ruolo = 8`, quindi il trigger `trgfn_indirizzi_guard_tipo_ruolo_tipi_indirizzo` respinge la fixture; per esercitarlo serve il layer SOGGETTO; **(b)** un indirizzo **non normalizzato** deve soddisfare `chk_indirizzi_free_requirements`: `indirizzo_libero` + `stato_id` + la terna `(locality, postal_box, administrative_area)`, non il solo testo libero |
| 2.5 Guard `FATT` obbligatorio | ➡️ **assorbito da I.4** | — | Non si scrive due volte: il brief intestazione §3.5 ha allargato il criterio *prima* che 2.5 fosse scritta, quindi il guard nasce già completo — indirizzi **e** intestazione — invece di essere riaperto. Stato e changeSet nella riga **I.4** |
| 2.6 pgTAP lock | ✅ **verdi** (2026-07-31) | `db/pgtap/vendite/test-fattura-satelliti-lock-congelamento-v1.sql` — `plan(11)` | Cablaggio su `pg_catalog` (`tgtype = 31` = BEFORE ROW ins/upd/dlt su **entrambe** le satelliti), scrittura ammessa sotto soglia, rifiutata oltre (INSERT/UPDATE/DELETE), **bypass GUC** in scrittura e in cancellazione, stessa regola su `fatture_scadenze`, e la **DELETE in CASCADE** dalla testata che deve passare (uscita anticipata su stato NULL — senza quel ramo una fattura congelata non sarebbe più cancellabile). Le fatture nascono già nello stato voluto: `trgfn_fatture_guard_stato` è montato solo su UPDATE, quindi non serve attraversare la matrice degli stati per testare un trigger di un'altra tabella |

### Cantiere INTESTAZIONE — snapshot dell'identità fiscale (brief BE 2026-07-31)

> Estensione della Fase 2 chiesta dal BE con
> [brief-db-snapshot-intestazione-fattura.md](brief-db-snapshot-intestazione-fattura.md);
> decisioni e rilievi nella **§10** di quel documento. Percorso critico: sblocca
> la loro Fase 2 (ristampa conforme) **e** il nostro 2.5, che deve nascere già
> col criterio allargato invece di essere riaperto.

| Passo | Stato | changeSet | Note |
|---|---|---|---|
| I.1 Colonne `emittente_snapshot` / `cliente_snapshot` + guard di congelamento | ✅ **applicato** (2026-07-31) | `20260731-05` | In **testata** e non in `fatture_indirizzi`: quella `UNIQUE` renderebbe impossibile avere insieme la sede dell'emittente e quella di un cliente PG. Il guard **non è nuovo**: è il parametrico di 1.1 montato con `TG_ARGV = 'id'` e `UPDATE OF` sulle due colonne — terza volta che C-11 si ripaga |
| I.2 `fn_snapshot_intestazione_fattura` | ✅ **applicata** (2026-07-31) | `20260731-06` | **Sorella**, non estensione (§10.1: i contatori mentirebbero). La sede usa la **stessa catena del cliente** con istanza NULL e tipo `SEDELEG`. Di ogni entità referenziata congela il **valore** e tiene l'id come provenienza: uno snapshot di soli id non è uno snapshot. Tre LEFT JOIN deterministiche per vincolo, nessun `LIMIT 1` |
| I.3 Wrapper: rinomina a `fn_snapshot_fattura_lotto` + chiamata alle due sorelle + contatore `intestazioni_scritte` | ✅ **applicato e verde** (2026-07-31): pgTAP del wrapper adeguato e rieseguito | `20260731-07` | 🔴 **Rompe il BE all'apply**: `ALLOWED_TASK_FUNCTIONS:176` e la query in `run_snapshot_indirizzi_lotto_task` puntano al nome vecchio. Loro selezionano i contatori **per nome**, quindi `intestazioni_scritte` non li tocca finché non vorranno leggerlo. `task_code` invariato (precedente D-L). ⚠️ **Il ritiro delle segnalazioni ora filtra su `meta->>'task'` e non più su `source`**: il source è il nome della funzione e le funzioni si rinominano — è appena successo — mentre il `task_code` è l'identità stabile del passo. Con il filtro vecchio, dopo ogni rinomina il task non riconoscerebbe più le proprie bandiere e smetterebbe di abbassarle |
| I.4 Guard 2.5 col criterio **allargato** | ✅ **applicato e verde** (2026-07-31) | `20260731-11` (fn), `20260731-12` (montaggio) | `vendite.trgfn_fatture_guard_uscita_draft`, `BEFORE UPDATE OF stato_doc_fiscale_id`. Codice errore **575** `E_FATTURA_NON_EMETTIBILE_INCOMPLETA` (append CSV, nessun loader nuovo). pgTAP nuovo `test-fattura-guard-uscita-draft-v1.sql` `plan(11)`. **Assorbe 2.5**. Quattro scelte non ovvie: **(a)** presidia l'**uscita** dalla bozza e non ogni avanzamento — oltre DRAFT il presidio è del guard di congelamento, e allargarlo darebbe una seconda occasione di fallire su un documento già emesso; **(b)** lo stato **abortito è esente**, perché una bozza incompleta deve restare chiudibile (oggi `DRAFT→ANNULLATA` non è in matrice: è la dichiarazione di perimetro, non un ramo vivo); **(c)** **solo UPDATE**, perché l'unico creatore applicativo `fn_get_or_create_fattura_header` inserisce sempre in DRAFT — la porta è chiusa a monte, e montarlo su INSERT romperebbe le fixture che creano fatture direttamente in DEFINITIVA senza chiudere nulla di nuovo; **(d)** **nessun bypass GUC**, a differenza della famiglia: il reset lotto *rientra* nella bozza, non ne esce, quindi il bypass sarebbe una porta di servizio sull'emissione in cambio di nulla. Indirizzi **data-driven** dalla matrice via `script.fn_indirizzi_obbligatori_mancanti` (stesso BB di `fn_check_ddt_emittibile`), non `FATT` cablato. Intestazione verificata per `jsonb_typeof` e **non** per `IS NULL`: `jsonb_strip_nulls` fa arrivare uno snapshot vuoto come `{}`, che un test sul solo NULL dichiarerebbe presente. Il nome ordina **dopo** `guard_stato`: una transizione illegale deve essere respinta *come* transizione, non come documento incompleto (presidiato dal test 11). ⚠️ **Due pgTAP verdi adeguati nello stesso giro** perché attraversano la soglia: `test-guard-lotto-fatture-stato-coerente.sql` e `test-fatture-righe-importo-e-kit-v1.sql` |
| I.5 Seed matrice `EF` | ✅ **applicato e verificato** (2026-08-02) | — (CSV + `20260802-27` resync sequence) | `SEDELEG`, `DOMFISC`, `SEDEOP`, `POSTA`, `RES`, tutti `obbligatorio = false` (§10.3). **Non urgente**: la sede si risolve già dal layer soggetto |
| I.6 pgTAP | ✅ **verde** (2026-08-01) | `db/pgtap/vendite/test-snapshot-intestazione-fattura-v1.sql` — `plan(12)` | Copre tutto il richiesto e due cose in più. **Shape**: chiavi identitarie delle due parti, `billing_account_id` = BA di **testata** (presidio di **D-P**), nessuna chiave a `null` (`jsonb_strip_nulls` mantenuto — è la promessa su cui il guard I.4 si basa per distinguere «assente» da «presente ma vuoto»), e **nessun valore testuale diverso dal proprio `btrim`**, che copre i `character(n)` di oggi *e* quelli che nessuno ha ancora aggiunto. **Catena della sede**: i test 8 e 9 sono una coppia — il 9 da solo passerebbe anche con la sede sul layer RUOLO, cioè il caso banale; è l'8 a dimostrare che quel layer è **vuoto** e quindi che l'unica strada era il fallback sul SOGGETTO. ✅ Misurato sul DB il 2026-08-01: **zero** emittenti hanno la sede sul layer RUOLO, tutti sul SOGGETTO — §10.3 confermato su tutta la popolazione, non su un campione. ⚠️ **Rettifica 2026-08-02**: la prima stesura scriveva «42 emittenti su 42», ma il 42 **non conta gli emittenti** — gli emittenti fiscali sono **2**. Contava le coppie `billing_account → emittente` (oggi 43), che moltiplicano lo stesso emittente per i suoi conti. La metà che importa (zero sul ruolo) resta vera; il numero era da correggere prima che qualcuno lo riusasse per dimensionare qualcosa; perciò la fixture **seleziona** su quella proprietà e il test 2 fallisce rumorosamente se un giorno non ci fossero candidati, invece di scivolare in skip. **Idempotenza**: non basta `scritta = false`, si verifica anche che le due colonne siano rimaste quelle (contatore e colonne possono mentire in modi diversi). **Guard**: rifiuto oltre soglia *e* — test 12 — che un'altra colonna della stessa fattura resti scrivibile, perché un montaggio senza `UPDATE OF` passerebbe il test 11 e congelerebbe in silenzio l'intera testata, contabilizzazione compresa |

### Fase 3a — Riforma condizioni di pagamento

| Passo | Stato | changeSet | Note |
|---|---|---|---|
| 3a.1 Semina catalogo termini | ✅ **applicata** (2026-07-31) | — (solo CSV, loader `runOnChange` esistente) | **5 termini nuovi, id 5-9**: `TP_60G_1R`, `TP_60G_EOM_1R`, `TP_90G_1R`, `TP_90G_EOM_1R`, `TP_30_60_2R` (la versione senza fine mese di quello che c'era). Con i 4 esistenti il catalogo copre 30/60/90, le versioni fine mese e 30/60 in due varianti. ℹ️ Scritti nella grammatica **di oggi** (`tipo_offset` + `unita_intervallo`) perché 3a.2 non è ancora applicata: **3a.3 li riscriverà** insieme agli altri quattro, con la mappatura meccanica di C-16 (`tipo_offset='F'` → `fine_mese=true`). Cinque righe da rifare, nessuna informazione persa |
| 3a.2 Riforma `config.termini_pagamento` | ✅ **applicata** (2026-07-31) · baseline `vendite` senza novità | `20260731-03` | `tipo_offset` → `fine_mese` bool. ⚠️ Il **backfill di `fine_mese` precede la DROP** di `tipo_offset`: invertirli perderebbe l'informazione sulle righe già in tabella, e il ricaricamento del CSV arriva dopo (fase `80_data`). ✅ **Censimento dei consumatori fatto (2026-07-31): non ce ne sono.** `tipo_offset` e `unita_intervallo` non compaiono in **nessun** file di `backend/` o `frontend/src/`, né in alcuna funzione o vista `dbzero`. L'unico punto da adeguare è il pgTAP `test-fattura-utils-critical-termini.sql`, che le valorizza in una `INSERT` di fixture (→ 3a.8). La riforma è quindi molto meno rischiosa di quanto la parola «breaking» suggerisse: **si tocca una colonna che nessuno legge** |
| 3a.3 Riscrittura seed termini | ✅ **applicata** (2026-07-31) | — (CSV + loader) | CSV riscritto nella nuova forma per **tutti e 9** i termini (non 4: la semina di 3a.1 ne ha aggiunti 5), mappatura di C-16 — `tipo_offset='F'` → `fine_mese=t`, `N` → offset a 0. **Loader esteso in place** (`20251019-51`): è `runOnChange`, quindi resta il mirror vivo del CSV; via `unita_intervallo` e `tipo_offset`, dentro `fine_mese`. Tolta anche la voce inerte `storicizza`, che descriveva una colonna inesistente sia nella tabella sia nel CSV |
| 3a.4 Migrazione clienti | ✅ **risultava fatta** (verificato 2026-08-02) | — | ⚠️ Era rimasta ⬜ ma **il lavoro c'era già**: i 3 clienti con termine portano tutti `TP_30G_1R`, che **non è il default** `TP_1RATA` — quindi qualcuno li aveva puntati a mano al termine di catalogo equivalente, come il passo prescriveva («a mano, sono 2»). Le colonne legacy non esistono più (3a.5), quindi la finestra era comunque chiusa: il passo si dichiara fatto sul **dato**, non sulla memoria |
| 3a.5 DROP colonne `clienti` + trigger + CHECK | ✅ **applicata** (2026-07-31) | `20260731-08` (fn), `20260731-09` (DDL) | ⚠️ **Due changeSet, in quest'ordine logico**: prima `fn_update_cliente` senza le due chiavi, poi la DROP. La funzione è plpgsql, quindi la DROP **non la invaliderebbe**: resterebbe creabile e apparentemente sana, e fallirebbe al primo salvataggio di un cliente. Stessa ragione per il trigger `trg_clienti_normalize_giorni_scadenza_ins_upd`, droppato esplicitamente; il `CHECK` invece cade da solo con la colonna. ✅ Perimetro applicativo chiuso dal BE il 2026-07-31 (3a.7): verificato su tutto il repo, le occorrenze rimaste sono **solo commenti** |
| 3a.6 DROP `fatture.giorni_pagamento` / `fine_mese` | ✅ **applicata** (2026-07-31) | `20260731-10` | ✅ **Zero consumatori**, verificato: nessun file Python/Vue/JS, nessuna funzione o vista DB, nessun pgTAP. Erano colonne morte già prima di diventarlo per decisione. ⚠️ Da non confondere con `config.termini_pagamento.fine_mese`, che è **nuova** e opposta di significato |
| 3a.7 Innesco applicativo | ✅ **fatto dal BE** (2026-07-31) | — | drawer cliente, chiavi i18n, `_OPTIONAL`, `_UPDATE_ALLOWED` e la `SELECT` del repository. La metà DB (`fn_update_cliente`) è in 3a.5 |
| 3a.8 pgTAP da rimuovere/adeguare | ✅ **fatto e verde** (2026-07-31) | — | `test-clienti-normalize-giorni-scadenza-v1.sql` **rimosso** (10 test sul trigger che sparisce). `test-fn-get-evento-stato-corrente-cliente-v1.sql`: solo un commento stale, aggiornato. ⚠️ **`create-cliente.sql` è diventato un cantiere a sé** — vedi riga sotto. `test-fattura-utils-critical-termini.sql` era già stato adeguato con 3a.2/3a.3 |
| 3a.8-bis `create-cliente.sql` — fixture riportata al presente | ✅ **verde, fuori baseline** (2026-07-31) | — | Era la **prima riga** di `baseline-rossi.tsv` come `ERRORE_FIXTURE`, e moriva al primo statement: quindi **zero asserzioni eseguite**, e sei difetti nascosti dietro il primo. Convertita da fixture che **committava** a test in `BEGIN/ROLLBACK` — le `DELETE` di pulizia esistevano solo per il commit, e con esse è sparito lo scontro col guard `delete_block_by_guc`: **tolta la causa, non aggirato il sintomo** (nessuna GUC di manutenzione). Gli altri sei erano deriva fra fixture e modello: tipo soggetto `SC` per una persona fisica (guard CF/P.IVA), `categoria_cliente_id` diventata NOT NULL, utility `GAS` che pretende il PDP, vista rinominata in `vw_*`, `clienti.utility_id` mai valorizzata, e **due matrici di indirizzi obbligatori** (soggetto e ruolo, guard distinti su tabelle distinte). Ora risolve **tutto per codice_interno**: niente id indovinati, che era la fragilità di fondo. CF proprio (`PGTPCL00A01H501Y`, generato e verificato con l'algoritmo del check char) per non contendere quello storico. ⚠️ **Debito reso visibile**: il soggetto storico (CF di una persona vera) resta in tabella ma **nessuno lo ricrea più**; `test-contatti-soggetto-cliente.sql` è verde solo perché quel dato è ancora lì. ℹ️ Nella baseline restano **6 fixture `create-*`**, con ogni probabilità rotte dallo stesso guard e curabili allo stesso modo |
| 3a.9 Doc | ✅ **fatta** (2026-08-02) | — | Due manuali: `dbzero/config/manual/termini_pagamento.md` **da riscrivere** sulla forma riformata, e `dbzero/anagrafiche/manual/trgfn_clienti_normalize_giorni_scadenza.md` **da ritirare**. ⚠️ Da ritirare anche la pagina **auto-gen** `anagrafiche/funzioni/trgfn_clienti_normalize_giorni_scadenza.md`: la rigenerazione aggiunge e aggiorna, **non cancella gli orfani**, quindi resta a documentare una funzione che non esiste più |

### Fase 3b — Chiave (D-7) + arrotondamenti

| Passo | Stato | changeSet | Note |
|---|---|---|---|
| 3b.0-a Colonne termine/modalità su `commesse` | ✅ **applicate** (2026-08-01) | `20260801-02` | **D-R**. Nullable + FK verso `config.termini_pagamento` / `modalita_pagamento`. La commessa **possiede** il termine; la sorgente lo propone alla nascita e poi esce di scena — nessuno specchio da tenere in sync |
| 3b.0-b `fn_get_or_create_commessa` a 10 dimensioni | ✅ **applicata** (2026-08-01) | `20260801-02` | **D-R**. I tre specchi (hash advisory lock, `WHERE` del riuso, `INSERT`) nello **stesso** changeSet. ⚠️ `IS NOT DISTINCT FROM`: con `=` il NULL non combacia mai e ogni push aprirebbe una commessa nuova. 🔴 **Trappola trovata scrivendolo, verificata in transazione**: `CREATE OR REPLACE` con due parametri in più **non sostituisce, crea un overload** — e poiché i nuovi hanno un DEFAULT, una chiamata con gli 11 argomenti di prima combacia con entrambe le firme e PostgreSQL rifiuta con «la funzione non è unica». Il push si sarebbe rotto alla **prima** invocazione. Serve la `DROP` esplicita della vecchia firma: verificato dopo l'apply che le firme vive siano **una sola** |
| 3b.0-c Guard immutabilità chiave su commessa con lavoro | ✅ **applicato e coperto** (2026-08-01, da Tid) · pgTAP 3b.5 **verdi** dal 2026-08-01 | `20260801-03` | **D-R** + codice `E_COMMESSA_CHIAVE_IMMUTABILE` (**576**, appeso al CSV, nessun loader nuovo). Soglia = **«ha attività collegate»**, non lo stato: il danno non è che la commessa sia avanzata, è che qualcosa sia stato raggruppato sotto la chiave vecchia. Commessa ancora vuota → modifica ammessa. Riscrivere lo stesso valore → ammesso (`IS DISTINCT FROM`). Bypass GUC `zeroerp.maintenance_reset_lotto_draft` come gli altri guard di dominio. ✅ **Verifica guard-restrittivo**: nessun pgTAP e nessuno scrittore tocca le due colonne — sono nate ieri — e il trigger è ristretto a `UPDATE OF` quelle due, quindi sugli UPDATE esistenti (`fn_cambia_stato_commessa`, i 2 pgTAP su `commesse`) **non si sveglia** |
| 3b.1-fix 🔴 **Alla catena mancava il livello COMMESSA** | ✅ **applicato** (2026-08-01) | `20260801-06` | Trovato riparando il pgTAP di 3b.1. Il piano prescrive **quattro** livelli, la funzione applicata ne aveva **tre**: senza il livello commessa **D-R è inerte** — le colonne messe su `vendite.commesse` non le legge nessuno, e due commesse separate apposta (al prezzo di una commessa in più) tornerebbero in **una fattura sola** col termine del cliente. Misurato: **34 attività su 34 hanno `commessa_id`** e ordini/preventivi sono vuote, quindi il livello mancante era l'unico con qualcosa da dire; `commesse` con termine valorizzato sono **0**, quindi nessun dato è sbagliato **oggi** — si accende al primo push che porta un termine. Sta **prima** del cliente: cambiare le condizioni di un cliente non deve riscrivere quelle delle commesse già aperte. ✅ **Prova e controprova**: con il fix una commessa con `TP_90G_1R` risolve 7, senza risolve 1 (il default). Le coppie risolte su tutte e 34 le attività sono **identiche** prima e dopo. 🔴 **Secondo difetto nella stessa funzione**: un `SELECT ... INTO` che non trova righe mette le variabili a **NULL**, e il livello cliente leggeva direttamente in `v_termine`/`v_modalita` con una JOIN **inner** — un BA padre senza riga cliente avrebbe **cancellato** il termine risolto dal documento sorgente. Ora ogni livello legge in variabili proprie e la fusione è un `COALESCE` in codice: «non ho trovato niente» smette di essere uguale a «ho trovato NULL» |
| 3b.1 Catena unica per attività | ✅ **applicata e completata** (2026-08-01, da Tid) · ⚠️ era **incompleta**, vedi la riga 3b.1-fix qui sopra · pgTAP 3b.5 pendenti | `20260801-01` | ⚠️ **Ricognizione 2026-08-01, tre correzioni al piano**: (1) la funzione viva **era già rotta** — la riforma 3a ha rinominato le colonne al singolare senza adeguarla, e `SELECT ... ARRAY[1]` risponde «la colonna `o.termini_pagamento_id` non esiste». Non se n'era accorto nessuno perché il ramo rotto è **l'unico che nessun test attraversa**: `test-fattura-utils-critical-termini.sql` esercita il fallback (test 9) e il guard (test 10), che stanno a monte e a valle della sorgente — è l'argomento per il «un test per livello» di 3b.5; (2) **il livello 1 non ha dati**: `vendite.ordini` e `vendite.preventivi` hanno **zero righe** e tutte e 34 le attività hanno sorgente COMMESSA, quindi la correzione del 2026-07-30 («7 ordini e 19 preventivi con termine») non vale più su questo DB; (3) **nessun chiamante da adeguare**: verificato che non la invocano né funzioni DB né il backend. ⚠️ **Qui vive il fallback, non nel generatore.** Il BE segnala (2026-07-31) che **19 clienti su 21** hanno `termine_pagamento_id` NULL e teme «zero rate in silenzio». Non serve una decisione nuova: **D-J** l'ha già presa — la colonna resta nullable e la catena scende al default `TP_1RATA`, quindi quei clienti producono **una rata alla data fattura**, non zero. Ma il fallback va scritto **in questa catena** (documento → cliente → `TP_1RATA`): metterlo nel generatore ricreerebbe il secondo risolutore che C-13 esiste per eliminare, e 4.1 dice esplicitamente che il generatore «legge e non risolve». Con la catena giusta, `E_SCADENZE_TERMINE_MANCANTE` resta una seconda linea che non scatta mai |
| 3b.2 `fn_build_fattura_key` + coppia | ✅ **applicata e coperta** (2026-08-01, da Tid) · pgTAP 3b.5 **verdi** dal 2026-08-01 | `20260801-04` | La chiave chiama la catena unica: è **questa** la chiamata che chiude C-13, perché una catena riscritta e mai invocata resta un secondo risolutore in attesa d'uso |
| 3b.3 `fn_get_or_create_fattura_header` lookup + INSERT | ✅ **applicato** (2026-08-01, da Tid) · pgTAP 3b.5 pendenti | `20260801-05` | Chiude il **secondo e terzo specchio** del §6. Il `WHERE` confrontava **sei** elementi contro i **nove** della chiave. Tre cose in un changeSet solo, e la separazione qui non degrada ma **moltiplica i documenti**: nella finestra fra colonna e INSERT nessuna fattura esistente combacerebbe più. 🔴 **`utility_id` è diventata una colonna** (**D-S**): non c'era niente su cui confrontare, e la deduzione esistente partiva dal BA padre mentre la chiave usa il figlio. ⚠️ `IS NOT DISTINCT FROM` sui tre nullable (reseller, utility, modalità) — **terza forma** della stessa trappola dei NULL dopo 3b.0-b (`WHERE`) e 3b.4-bis (indice). La completezza della chiave pretende `utility_id` (`billing_account.utility_id` è NOT NULL: se manca, la chiave è rotta) ma **non** termine e modalità, che possono legittimamente essere assenti. ✅ **Verificato in transazione**: la seconda chiamata ritrova la fattura della prima (lookup e INSERT si specchiano), la testata porta esattamente utility/termine/modalità della chiave, e un termine divergente **apre una seconda fattura** — mentre col codice di oggi la controprova mostra `termine = NULL` in testata e le due **rifuse in una**. Totali invariati sulle 10 fatture esistenti (che però hanno tutte `totale_doc = 0`: prova debole, la vera copertura è 3b.5). ⚠️ **Tre fixture pgTAP adeguate** perché il ricalcolo ora **legge** l'utility invece di dedurla: `test-ricalcola-riepiloghi-iva` (12/12 ✅) e `test-fatture-righe-importo-e-kit-v1` (19/19 ✅) riprovate col changeSet in transazione; `test-ricalcola-totali-fattura-arrotondamento` è **già in baseline** come `ERRORE_FIXTURE` (riga 106) e muore nella fixture prima di arrivarci — adeguata alla cieca, si validerà con la bonifica |
| 3b.4-bis Ambito arrotondamenti = chiave | ✅ **applicata e coperta** (2026-08-01, da Tid) · pgTAP 3b.5 **verdi** dal 2026-08-01 | `20260801-04` | **stesso changeSet** di 3b.2, come prescritto. 🔴 **Trappola dei NULL, forma da indice**: le 5 colonne d'ambito di oggi sono tutte NOT NULL, le due nuove no — e un indice unico considera i NULL **distinti fra loro**. Con la clausola di default ogni ricalcolo con termine NULL avrebbe creato una riga d'ambito nuova, frammentando il saldo **senza errore**. Risolto con `NULLS NOT DISTINCT` (PG15+, siamo su 18) e provato in transazione: con la clausola 1 riga e saldo aggiornato, **senza, 2 righe**. È la gemella della trappola di 3b.0-b, dove la stessa cosa si risolveva con `IS NOT DISTINCT FROM` nel `WHERE` |
| 3b.4-ter Storno al ricalcolo | ✅ **applicata e coperta** (2026-08-01, da Tid) · pgTAP 3b.5 **verdi** dal 2026-08-01 | `20260801-04` | Accorpata: cambiando la firma di get/set dello scope, `fn_ricalcola_totali_fattura` va aggiornata nella stessa transazione o non compila — e D-N dice che i pezzi vanno insieme. Il saldo si legge `− COALESCE(arrotondamento_attuale, 0)`, così la riesecuzione **ripete** il primo calcolo invece di inseguirlo |
| 3b.4-quater Storno alla cancellazione (C-23) **+ D-L pt.3 (C-22)** | ✅ **applicato e verde** (2026-08-01) · ⚠️ resta la **doc auto-gen da rigenerare** (le due funzioni di questo changeSet sono stale) | `20260801-07` | Un changeSet solo, come prescritto: le due correzioni stanno sulla stessa catena (`fn_reset_lotto_fattura_draft` → `fn_cleanup_fatture_by_ids`). **Storno**: la primitiva non nominava mai `fatture_arrotondamenti_scope`, quindi il contributo della fattura cancellata restava nel saldo e la successiva dello stesso ambito ne ereditava il riporto. Con 3b.4-ter già applicato era la metà mancante di D-N. 🔴 **Diventa scrivibile solo ora**: l'ambito ha 7 colonne e una è `utility_id`, che la fattura non portava prima di **D-S**. Tre scelte: **UPDATE e non upsert** (nessuna riga d'ambito ⇒ nessun contributo mai dato; crearla con saldo negativo inventerebbe un debito, quindi `fn_set_arrotondamento_scope` **non** è il BB giusto qui), `IS NOT DISTINCT FROM` sulle due nullable (**quarta forma** della trappola dei NULL della fase), aggregato per ambito (il reset di lotto cancella molte fatture insieme, più d'una sullo stesso ambito). Sta **in testa** alla funzione: nulla oggi tocca i totali prima della DELETE (verificato: `fn_reset_fondi_fattura` non ricalcola, nessun trigger sui figli chiama il ricalcolo), ma leggere le fatture intatte rende la correttezza indipendente da cosa verrà aggiunto dopo. ✅ **Prova e controprova**: fattura con arrotondamento `0,005` e saldo d'ambito `0,005` → dopo la cancellazione **0,000**; col codice di oggi il saldo resta `0,005`, residuo orfano. **C-22**: misurato che cancellando **una** fattura col `lock_batch_id` del lotto si liberano **15 attività** — tutto il batch — contro **0** passando `NULL`. La per-fattura ora passa `NULL` e non legge nemmeno più il `lock_batch_id`: averlo a portata di mano era ciò che ha portato a passarlo. ⏭️ **Non incluso D-L.1** (rinomina delle due funzioni): tocca anche il Python e va concordata col BE |
| 3b.5 pgTAP chiave + idempotenza | ✅ **verdi** (2026-08-01) | `test-chiave-fattura-tre-specchi-v1.sql` `plan(12)` · `test-arrotondamento-ambito-idempotenza-v1.sql` `plan(12)` | **Due file, perché sono due invarianti diverse**: la forma della chiave e il comportamento del saldo. Il primo presidia il **§6** in modo che dica *quale* dei tre specchi manca — elenco degli elementi della chiave confrontato con il `WHERE` del lookup (sul sorgente vivo, isolando il blocco: 635 caratteri su 6079, verificato che non peschi fuori), con le colonne di `vendite.fatture`, e con la unique dell'ambito. Le **due colonne che l'ambito non ha** sono motivate nel file: `registro_id` è funzione pura di `tipo_doc_fiscale_id` e il reseller è determinato dal BA, quindi nessuna delle due discrimina in più — ma l'elenco atteso è scritto per esteso, così chi cambia l'ambito deve passare di lì. Poi idempotenza del lookup, e **due divergenze**: il termine per la **via reale** (si mette sulla commessa e la catena lo raccoglie — copre D-R, catena, chiave e lookup in un colpo) e l'utility, che era il bug storico. Il secondo file copre l'**idempotenza del ricalcolo sulla scomposizione** `precedente`/`attuale` — quello che mancava, e che è la misura che conta perché il totale resta simile anche col meccanismo rotto — la separazione degli ambiti (C-20), lo **storno alla cancellazione** (C-23) e i due rami di C-22. ✅ **Prova di mutazione**: rimuovendo lo storno dal cleanup diventa rosso **solo** il test 8, quindi il file morde dove dice di mordere. ⚠️ Il giro completo di `fn_reset_lotto_fattura_draft` non è esercitabile (pretende un lotto DRAFT e in questo DB non ce ne sono): il test 12 presidia il punto esatto in cui il difetto viveva — che il chiamante passi `NULL`. ℹ️ Livello 1 della catena (documento sorgente) non esercitato: ordini e preventivi sono vuote, detto nel file e non taciuto. ✅ **La fixture che il piano temeva non serve più**: §3.3-b diceva «per testare la divergenza serve creare un secondo termine di catalogo», ma dopo la riforma 3a il catalogo ne ha **9 reali** (3a.1 + 3a.3) e la divergenza si esercita scegliendone due. Il presidio che manca di più è l'**invariante del §6**: ogni elemento della chiave compare, identico, nel `WHERE` del lookup, nelle colonne di testata e nella chiave d'ambito — scritto una volta, vale per ogni discriminante futuro. Da coprire anche i tre casi già provati a mano in 3b.3 (idempotenza del lookup, termine divergente → due fatture, **utility diversa → due fatture**) e l'idempotenza del ricalcolo con la **scomposizione** `precedente`/`attuale`, che è il test che oggi manca |

### Fase 4 / 4b — Scadenze + guard numerazione

| Passo | Stato | changeSet | Note |
|---|---|---|---|
| 4.1 `fn_genera_scadenze_fattura` | ✅ **applicato e verde** (2026-08-01) · pgTAP **14/14** | `20260801-08` · `db/pgtap/vendite/test-genera-scadenze-fattura-v1.sql` `plan(14)` | **LEGGE e non risolve** (C-13): prende `termine_pagamento_id` dalla testata, dove arriva passando dalla chiave (3b.1→3b.2→3b.3). Formula a **ramo unico** dopo D-E, tutto in giorni; l'arrotondamento passa da `script.fn_arrotonda_importo`, il BB unico, invece di essere la terza copia della stessa tabella di CASE. **DELETE+INSERT**, e la DELETE precede i casi a base non positiva: una fattura diventata interamente coperta da acconti deve **perdere** le rate che aveva. I tre casi di **D-D** restano tre: `NULL`→571, `0`→zero rate senza log, `<0`→zero rate + log **non critico**. Oltre soglia → **573** invece di lasciar fallire la DELETE sul guard dei satelliti. 🔴 **Trovato scrivendolo**: la quadratura sull'ultima rata può renderla **negativa** se l'arrotondamento delle prime sovra-alloca (metodo `UP` su basi minuscole) e `chk_fatture_scadenze_importo_pos` la rifiuterebbe con un errore di vincolo illeggibile a metà giro — intercettata prima, con **572**, che è la diagnosi vera: è il termine a essere inconciliabile con quella base, non la fattura. I 9 termini di oggi sono tutti `HALF_UP`/`UGUALI`, quindi è una seconda linea. ✅ **Misurato in transazione**: 15/01+30=14/02; fine mese → 28/02; **a cavallo d'anno** 20/12/2026+30 → 31/01/2027 (il clamp lo fa PostgreSQL, nessuna aritmetica a mano); 100/3 = 33,33+33,33+**33,34** e la somma quadra; rerun `del=3 ins=3` con piano identico. ✅ **Prova di mutazione**: spostando la quadratura via dall'ultima rata diventano rossi **solo** i test 8 e 9. ⚠️ **I test sono nati con la funzione**, non dopo: è la correzione d'ordine decisa chiudendo la 3b |
| 4.2 `fn_genera_scadenze_lotto` | ✅ **applicato** (2026-08-01) | `20260801-09` | Modello `fn_snapshot_fattura_lotto`: filtro in lettura, sotto-blocco per fattura, ritiro delle proprie segnalazioni. Due motivi di salto con **contatori separati** — un `skipped` unico direbbe «cinque saltate» senza distinguere cinque documenti **chiusi** da cinque **rotti**, che per il cockpit sono l'opposto. 🔴 **CORREZIONE AL PIANO, trovata collaudando**: la prescrizione «salta le fatture con `stato_esecuzione = 'ERRORE'`» **crea uno stallo**. Quella colonna non dice «rotta a monte», dice «esiste un log critico attivo», **di qualunque task** (`fn_resolve_stato_esecuzione` la deriva da `has_critical`): quindi lo step che marca una fattura la esclude da sé stesso per sempre, la sua bandiera non può più essere abbassata da chi l'ha alzata, e **«rilanciare lo stesso step» — la via d'uscita di D-Q — smette di funzionare**. Misurato: dopo aver corretto i totali, `lavorate=0` e segnalazione ancora attiva. Il criterio corretto guarda **di chi è** la segnalazione: si salta se c'è un critico attivo di un **altro** task, le proprie si riprovano — ed è ciò che rende raggiungibile il ritiro di D-Q pt.3. Un critico senza `meta->>'task'` conta come altrui: una bandiera che non sappiamo chi abbia alzato non è nostra da abbassare. ✅ **Ricollaudato**: giro 1 la fattura senza totali fallisce e viene marcata; giro 2, corretti i totali, **il rilancio ripara** e ritira la propria bandiera; giro 3, un critico di un altro task la fa saltare. ✅ **pgTAP** `test-genera-scadenze-lotto-v1.sql` `plan(11)` **verdi**, con **prova di mutazione**: rimettendo il filtro prescritto dal piano (`stato_esecuzione = 'ERRORE'`) diventa rosso il **test 7**, che è quello sul rilancio che ripara. ⚠️ **Due stesure di quel test passavano anche col filtro sbagliato**, cioè davano fiducia falsa: lo scenario dello stallo non si formava. La catena vera, misurata: il log critico porta subito `fatture.critical = true`, ma `stato_esecuzione` resta **PENDING** finché il runner non risincronizza; e **nessuna delle due funzioni di sync serve a forzarlo in un test** — `fn_sync_fatture_log_critical_lotto` allinea il flag `critical` e non lo stato di esecuzione, mentre `fn_sync_lotto_fatture_stato` **non è un ricalcolo**: porta le fatture allo stato fiscale del LOTTO, e in una fixture sbatte contro il guard delle transizioni. Nel test la condizione si scrive quindi a mano, isolando il comportamento in esame dall'ingranaggio che lo produce |
| 4.3 Seed EMESSA + riempimento corsia 2 | ✅ **ARMATA** (2026-08-02): nodo `genera_scadenze_lotto` in coda a `ricalcola_iva_lotto` sulla pipeline **3**, e pipeline **2** (era `processi = []`) riempita con gli stessi 4 nodi — `rollback` lasciato vuoto come vuole D-C | — (solo CSV, loader `runOnChange` esistenti) | **Due tempi, stesso criterio di 2.3.** ✅ **Inerte**: `pipeline_task_registry` **20** (`genera_scadenze_lotto`, dominio 1), `pipeline_task_registry_impl` **20** (`genera_scadenze_lotto_default`), `fatturazione_pipeline_task_policy` **19-23** — la 19 sulla corsia MASSIVO (pipeline 3), la 20 su GIORNALIERO (pipeline 2), e le **21-23** che danno alla corsia 2 le policy dei tre task che D-C le assegna. `RESUME_STEP` come le altre policy della corsia EMESSA, ed è coerente con D-Q: la via d'uscita è rilanciare lo **step**. Nulla di irreversibile: sono righe di registro, non fanno partire niente. ⛔ **Armamento** = il nodo `genera_scadenze_lotto` nei `processi` della pipeline 3 (dopo `ricalcola_iva_lotto`) e il **riempimento della pipeline 2** con fondi + IVA + scadenze (D-C). 🔴 **Verificato il 2026-08-01**: `ALLOWED_TASK_FUNCTIONS` (`pipeline_repository.py:160`) **non contiene** `genera_scadenze_lotto` — armare adesso farebbe morire il lotto su un task sconosciuto. Va dopo la registrazione BE, che è il punto in cui la Fase 4 li sblocca davvero |
| 4.3-bis Invariante pgTAP esteso | ✅ **verde** (2026-08-02) | `db/pgtap/vendite/test-pipeline-processi-invariante-v1.sql` — `plan(7)` | Test 1-3 sull'armamento; **4-7 sono l'invariante e sono la parte che vale**, scritti **data-driven** (nessun id elencato → coprono le tappe future): per ogni tappa **una sola variante distinta** di `processi` (C-7 generalizzato — prima valeva solo per la DEFINITIVA, ed è *per questo* che la corsia GIORNALIERO è rimasta vuota senza che nessuno se ne accorgesse); nessuna pipeline attiva con `processi` vuoti; ogni task armato esiste ed è attivo nel registry; ogni `(pipeline, task)` ha la sua policy. ✅ **Prova di mutazione al contrario**: girato PRIMA dell'apply dava **5 rossi parlanti** (1-5), esattamente i punti che l'armamento chiude. ⚠️ **Trappola evitata nel test 3**: confrontare gli *indici* di due task fa **passare** una corsia che ne perda uno del tutto — esce dal confronto invece di violarlo; si contano le corsie che rispettano l'ordine e si confrontano col totale |
| 4.4 Doc | ✅ **fatta** (2026-08-02) | — | Riscritto `dbzero/vendite/manual/fatture_scadenze.md` (aveva `tipo_offset` e `ripartizione` a tre valori, entrambi morti; più due consigli diventati falsi: il lock «opzionale» che ormai è un trigger, e l'idempotenza descritta come raccomandazione quando è una funzione). Aggiunta a `guide/fatturazione.md` la tabella dei 4 task dello step EMESSA con l'ordine 3→4 e il motivo. 🔴 **Correzione di merito**: la guida non era solo stale, **giustificava il difetto** — diceva che lo step EMESSA giornaliero non ha task «perché l'IVA è già calcolata alla nascita del documento», che è falso e *è* la convinzione che ha lasciato vuota quella corsia. La rettifica è lasciata **visibile** invece di riscrivere in silenzio. ⚠️ **Rilievo del BE accolto (2026-08-02)**: l'esempio `100,00 / 3` **non è riproducibile** (catalogo a max 2 rate) e soprattutto suggeriva una direzione che non è generale — con 2 rate `HALF_UP` arrotonda sempre per eccesso, quindi **l'ultima rata riceve MENO**; il verso opposto si vede solo da 3 rate in su. Entrambi i manuali ora portano la tabella misurata |
| 4.5 pgTAP scadenze | ✅ **CHIUSA** (2026-08-02): dei tre residui elencati, **due erano già coperti da test scritti per altro** — il **lock** da `test-fattura-satelliti-lock-congelamento-v1` di 2.6 (verifica esplicitamente la stessa regola su `fatture_scadenze`) e **seed/posizione** dal nuovo invariante di 4.3-bis. Resta solo `E_SCADENZE_TERMINE_INVALIDO` sul ramo `ripartizione`, che il CHECK del catalogo rende irraggiungibile senza aggirarlo: **documentato nel file invece che finto**. Metà fatta insieme a 4.1 (2026-08-01): `test-genera-scadenze-fattura-v1.sql` `plan(14)` copre quadratura, ribilanciamento 100/3, `numero_rata` progressivo, `fine_mese` **incluso il cavallo d'anno**, base a zero e negativa, idempotenza sul **piano intero** (non sul conteggio: un generatore che sbaglia le date le riscriverebbe diverse mantenendo lo stesso numero di righe) e tre codici d'errore su quattro | `db/pgtap/vendite/test-genera-scadenze-fattura-v1.sql` | Restano da coprire, quando i pezzi esistono: il **lock** (4.2), **seed e posizione** in pipeline (4.3), e `E_SCADENZE_TERMINE_INVALIDO` sul ramo `ripartizione`, che il CHECK del catalogo rende inserribile solo aggirandolo — documentato nel file invece di essere finto |
| 4b.1-4b.4 Guard numerazione (D-K) | ✅ **CHIUSA** (2026-08-02) | `20260802-24` · pgTAP `test-numerazione-guard-coerenza-v1.sql` `plan(9)` | **SEI condizioni** (la 6ª aggiunta da Tid) che insieme verificano una **catena continua**: `riepiloghi IVA →(5) totale_doc →(6) totale_a_pagare →(3/4) rate`. La 6ª chiude l'anello di mezzo, l'unico aperto — senza, un **fondo/acconto registrato dopo il ricalcolo** passava indisturbato con rate che quadrano su un totale vecchio. 4b.2 era **già fatto** (codice 574 a seed dalla Fase 1.3). 4b.3: delle 3 fixture che la grep segnalava ne era rotta **una** — la grep sovrastima, misurare. 🔴 **RETTIFICA che vale oltre il cantiere**: la motivazione «il guard sta prima del progressivo perché `nextval` non fa rollback» (dal `20260728-05`, e ripetuta qui nella prima stesura) è **FALSA** — `fn_get_next_progressivo` non usa sequence, è advisory lock + `UPDATE last_numero`, quindi è transazionale e **il buco non si forma**. Il danno vero è l'opposto e **irreversibile**: numero fiscale valido su documento invalido → DEFINITIVA → satelliti congelati → le rate mancanti non si possono più aggiungere. ⚠️ **Rischio residuo tracciato, non affrontato**: nessun trigger `BEFORE DELETE` impedisce di cancellare una fattura già numerata |

### Fase 6 — Ritorno a DRAFT + estrazione → **ESTRATTA (2026-08-03)**

➡️ Cantiere autonomo: **[piano-db-ritorno-lotto-a-draft.md](piano-db-ritorno-lotto-a-draft.md)**,
il cui **§7 è il registro**. Motivo dell'estrazione nella **§3.6** di questo piano.

⚠️ **Qui non resta nessuna riga da aggiornare**: due elenchi della stessa cosa
divergono (§3.7-bis), quindi lo stub non si tiene «per comodità».

### D-L — Funzioni di reset

| Passo | Stato | changeSet | Note |
|---|---|---|---|
| D-L.1 Rinomina (DB **e** Python) | ✅ **chiusa su entrambi gli strati** (2026-08-01): DB applicato, e il BE ha allineato subito dopo come concordato | `20260801-10` | `fn_reset_lotto_draft` → **`fn_annulla_lotto_da_draft`**, `fn_reset_lotto_fattura_draft` → **`fn_elimina_fattura_draft_da_lotto`**. Solo i nomi: i corpi sono quelli di `20260801-07`, C-22 incluso (verificato in transazione che la nuova per-fattura passi ancora `NULL`). **`DROP` esplicita delle vecchie**: crearne di nuove e basta lascerebbe due funzioni identiche, di cui una raggiungibile dal Python per sbaglio — cioè il doppio strato che D-L esiste per togliere. Aggiornato anche il nome che le due dichiarano a `fn_log_and_raise_error`: un errore che si presenta col nome vecchio manda a cercare una funzione inesistente. ⚠️ Il **`task_code`** `reset_lotto_draft` **non si tocca**: è il nome del TASK, vive nei CSV, ed è la stessa distinzione già pagata con lo snapshot. ✅ **Chi muove per primo — l'unica cosa da concordare, e il BE ha risposto** (2026-08-01): «applicate pure, allineo subito dopo». La finestra in cui il task punta a una funzione inesistente è quindi voluta e sorvegliata: era già successa il 2026-07-31 con `fn_snapshot_indirizzi_lotto`. **Adeguati nello stesso giro**: 2 pgTAP, i 2 manuali `dbzero` (rinominati file **e** contenuto, così non diventano orfani), il manuale di `fn_cleanup_fatture_by_ids` che li linkava e la guida `fatturazione.md`. ℹ️ Dopo apply e rigenerazione resteranno da cancellare le 2 pagine auto-gen col nome vecchio: la rigenerazione non toglie gli orfani |
| **D-T** Lotto vuoto non annullabile (segnalazione BE) | ✅ **applicato e verde** (2026-08-02) | — (solo CSV, loader `runOnChange` esistente) | Riga **11** in `stati_doc_fiscale_transizioni.csv`: `DRAFT → ANNULLATA`, `solo_lotto = t`, `meta {}` — quindi **entrambi i tipi di lotto**. ✅ **Riprodotto prima di correggere**: lotto MASSIVO vuoto → `transizione 1→7` bloccata; con la GUC accesa a mano → passa. ✅ **Dopo il seed**: si annulla **senza** GUC, stato `ANNULLATA` / `CHIUSO`. pgTAP `test-annulla-lotto-vuoto-v1.sql` `plan(6)`, verde col seed e **3 rossi parlanti** senza (usa `lives_ok`: una chiamata nuda abortirebbe la transazione e il file morirebbe al terzo test, perdendo proprio le asserzioni che spiegano cosa non ha funzionato). Il test 6 presidia che **non** si sia aperta anche la transizione per le fatture: quella è D-N-bis e resta una decisione a parte. 🔴 **Aperto**: il giornaliero ora può retrocedere per matrice, ma `fn_annulla_lotto_da_draft` lo rifiuta ancora — vedi D-L.2 |
| D-L.2 Asimmetria di perimetro **+ coda di D-T** | ✅ **applicato** (2026-08-02) | `20260802-01` | 🔴 **C-17 sbagliava**: il ramo EMESSA della globale **non è morto**. Il guard di coerenza tollera la fattura disallineata quando è `critical`, e c'è un percorso reale — un lotto EMESSA che **torna a DRAFT** si lascia dietro le critiche, che restano EMESSA (`fn_sync_lotto_fatture_stato` le salta apposta). Misurato: `lotto 489 DRAFT · fattura 632 EMESSA critical` → guard soddisfatto, **globale OK, singola rifiutata**. Quindi si sana **verso l'alto**: sanare verso il basso renderebbe non annullabile un lotto tornato in bozza con dentro una fattura critica, cioè un vicolo cieco nuovo della famiglia di D-T. E il caso è il più utile di tutti: togliere **la singola fattura rotta** invece di annullare il lotto intero. **Perimetro ora identico**: fatture pre-fiscali (DRAFT o EMESSA) e lotti MASSIVO **o GIORNALIERO** su entrambe — aprire il giornaliero solo sulla globale avrebbe sanato un'asimmetria creandone un'altra. **Rinomina**: `fn_elimina_fattura_draft_da_lotto` → **`fn_elimina_fattura_da_lotto_draft`**, perché a dover essere in bozza è il **lotto** e non la fattura; tenere il nome vecchio avrebbe rimesso in circolo un nome che mente un giorno dopo averlo tolto (Tid, 2026-08-02: si fa, non c'è produzione). ✅ Verificato: singola su fattura EMESSA critica → cancellata; lotto GIORNALIERO vuoto → annullato. pgTAP toccati verdi (arrotondamento 12/12, lotto vuoto 6/6, tre specchi 12/12). ⚠️ **Il BE va avvisato**: seconda passata sui nomi, la loro prima è di ieri |
| D-L.3 Over-free `lock_batch_id` (C-22) | ✅ **applicato e verde** (2026-08-01) | `20260801-07` | 🔴 **bug**; prerequisito di 6.5. Accorpato a 3b.4-quater — vedi quella riga per misure e prove |
