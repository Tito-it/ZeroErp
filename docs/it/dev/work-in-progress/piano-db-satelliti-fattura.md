# Piano DB — satelliti della fattura (indirizzi + piano rate)

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

⚠️ **Non verificate in questa sessione** le misure che richiedono il DB vivo
(«0 righe in `fatture_scadenze`», «2 clienti con entrambe le condizioni», «21 BA
/ 21 istanze / 21 clienti», «0 ordini e 0 preventivi»): il DB sta su un altro
server. Sono prese per buone dai brief, che le hanno misurate oggi. Tutto il
resto qui sotto è stato riletto sul codice.

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

---

## 2. Decisioni

### 2.1 Chiuse da Tid il 2026-07-29

| # | Decisione | Esito |
|---|---|---|
| **D-A** | Indirizzi fattura: risoluzione **sempre dall'anagrafica** (mai copia dai documenti sorgente) | ✅ **DECISA**. Confermata anche dal comportamento reale dei fratelli: quando nascono **senza sorgente** risolvono anch'essi dall'anagrafica (C-14). La fattura non è quindi un'eccezione — applica sempre il ramo che i fratelli applicano quando non hanno da chi copiare. ⚠️ La catena da replicare è quella **a due layer** di C-14, non il solo layer RUOLO |
| **D-I** ⭐ | **Un solo meccanismo per le condizioni di pagamento: il termine di pagamento** (C-16) | ✅ **DECISA.** Si eliminano `anagrafiche.clienti.tipo_gg_scadenza_ft` e `nr_giorni_scadenza`: il cliente porta **solo** `termine_pagamento_id`. Chi ha condizioni particolari usa un termine dedicato nel catalogo. Si eliminano di conseguenza `vendite.fatture.giorni_pagamento` e `fine_mese`, che esistevano solo per rappresentare il percorso legacy. È la decisione **strutturante** di questo cantiere: cancella D-2, D-3, D-4, D-H, §4.4-bis, §5.5 e 3 pgTAP |
| **D-E** | Forma di `config.termini_pagamento` | ✅ **DECISA.** `tipo_offset` (lettera `G/M/F/N`) → **sostituito** da `fine_mese boolean NOT NULL DEFAULT false`. `primo_offset_giorni` e `intervallo` diventano **`NOT NULL DEFAULT 0`** e si intendono **sempre in giorni**. Sparisce il CHECK `chk_termini_pagamento_intervallo_uso` (non ha più senso) e con esso ogni semantica del NULL. `ripartizione` → CHECK ricostruito su `IN ('UGUALI')`: `LIBERA` non è un algoritmo mancante ma un **pezzo di modello** mancante (nessuna tabella figlia per percentuali/date per rata), `PROPORZIONALE` non ha una base rispetto a cui essere proporzionale. Colonna `unita_intervallo` **eliminata** (§5.2). Guard `E_SCADENZE_TERMINE_INVALIDO` nel generatore come **seconda linea**. Motivo della scelta «togliere dal dominio» invece di «rifiutare a runtime»: un termine impossibile deve fallire quando si **salva la configurazione**, non settimane dopo durante il giro notturno. ⚠️ CHECK ricostruiti con `DROP IF EXISTS` + `ADD` in changeset **nuovo**, mai editando gli originali mergiati. ⚠️ Se un giorno servirà la rateizzazione **mensile**: si aggiunge allora, e il clamp a fine mese lo dà PostgreSQL nativamente (`date '2026-01-31' + interval '1 month'` = `2026-02-28`) |
| **D-O** *(da R-2)* | Come comporre lo snapshot per il layer **SOGGETTO** degli indirizzi | ✅ **DECISA: si estende `script.fn_snapshot_indirizzo`** con una variante per soggetto (`fn_snapshot_indirizzo_soggetto`). Motivo: quella esistente prende un `p_indirizzo_id` e legge `vw_indirizzi_resolved_ruolo`, ma gli indirizzi di soggetto **non hanno riga** in `anagrafiche.indirizzi` — il mixin Python infatti compone lo snapshot **a mano** per quel layer. Con la variante, la regola D-5 del design-of-record («mai comporre lo snapshot a mano») resta intera e la **composizione ha un solo proprietario**. L'alternativa — accettare l'eccezione — lascerebbe due formati da tenere allineati a mano |
| **D-M** | Il flag `fatturazione_lotti_fatture.esclusa` (C-21) | ✅ **DECISA: si elimina.** È dormiente — nessuno la valorizza, cinque punti la interrogano — e tiene in piedi un secondo modo, non funzionante, di fare ciò che il reset per-fattura fa già meglio. Un flag così è la premessa di un comportamento sbagliato il giorno in cui qualcuno lo valorizza senza conoscerne tutti i lettori. Da toccare: `fn_lotto_emittente_stati_lf`, `fn_lotto_stato_esecuzione_v2`, `fn_guard_lotto_fatture_stato_coerente` (che resta con la sola eccezione `critical`), outbox di stampa, filtro API, `types.py` |
| **D-N** ⭐ | Arrotondamenti: idempotenza e verità della testata (C-20) | ✅ **DECISA, rimedio in due pezzi.** (1) **Chiave dell'ambito = chiave di aggregazione**: `fatture_arrotondamenti_scope` prende anche `termine_pagamento_id` e `modalita_pagamento_id`, altrimenti D-7 fa condividere il saldo a due fatture diverse. (2) **Storno del proprio contributo al ricalcolo**: `fn_ricalcola_totali_fattura` legge `saldo_scope − COALESCE(f.arrotondamento_attuale, 0)`, così il ricalcolo **ripete** il primo invece di convergerci e i campi in testata restano veri — uno dei due va in stampa. (3) 🔴 **Storno alla cancellazione** (C-23): `fn_cleanup_fatture_by_ids` deve stornare dal saldo d'ambito l'`arrotondamento_attuale` di ogni fattura che cancella, **prima** di cancellarla. Senza, il saldo diventa la somma di ciò che è stato emesso *e* di ciò che è stato buttato. I tre pezzi vanno **insieme**: due su tre è peggio di zero, perché sembra a posto |
| **D-N-bis** ⭐ | Estrazione di una fattura da un lotto **EMESSA** | ✅ **DECISA: modello «reperto».** Una o più fatture non numerate si possono **togliere** da un lotto EMESSA: si **stacca** il collegamento al lotto, la fattura passa ad **ANNULLATA** e le sue **attività tornano libere** (il giro successivo produce la fattura giusta). Perché ANNULLATA e non DRAFT: lo stato ha già la semantica esatta — `applica_lotto = false`, `applica_fattura = true`, `is_abortito = true`, fase `CHIUSO` — mentre una DRAFT staccata sarebbe **ambigua** (sembra lavorabile e non lo è, entra nei conteggi delle bozze). Serve l'append della transizione `EMESSA → ANNULLATA` per la **fattura** (oggi la matrice non ce l'ha). La fattura estratta resta come **documentazione**: è l'artefatto diagnostico che dice cosa non andava, e alimenta una lista «estratte» nel cockpit. ⚠️ Non è riprendibile per disegno: il suo contenuto è la fotografia del dato sbagliato, e la correzione avviene **a monte** (commessa, anagrafica) |
| **D-K** ⭐ | Guard di coerenza **prima di consumare il numero fiscale** | ✅ **DECISA.** In `fn_assign_numero_fattura` (non nel wrapper: è il punto UNICO in cui il progressivo si consuma, e `nextval` non fa rollback — C-19), accanto al precedente `E_FATTURA_SENZA_RIGHE`. Blocca con `E_FATTURA_NON_NUMERABILE_INCOERENTE` se: `totale_a_pagare IS NULL` · ci sono righe ma nessun riepilogo IVA · `totale_a_pagare > 0` e nessuna rata o `Σ importo ≠ totale_a_pagare` · `totale_a_pagare <= 0` e ci sono rate (coerente con D-D). Motivo: oggi la numerazione **non controlla nulla** e numererebbe una fattura senza totali, senza IVA e senza rate — è ciò che avrebbe lasciato passare fino allo SDI i documenti della corsia GIORNALIERO (D-C). Non rincorre gli scrittori: verifica il **risultato**, quindi copre anche le cause future e il caso più probabile di tutti (il task scadenze che non ha girato affatto). ⚠️ **Costo reale**: romperà le fixture pgTAP che numerano fatture prive di satelliti — vanno adeguate |
| **D-L** | Le due funzioni di reset lotto (C-17) | ✅ **DECISA.** (1) **Rinominare** perché i nomi dicano l'esito: `fn_reset_lotto_draft` → `fn_annulla_lotto_da_draft`, `fn_reset_lotto_fattura_draft` → `fn_elimina_fattura_draft_da_lotto`. Impatto misurato: `ALLOWED_TASK_FUNCTIONS` (`pipeline_repository.py:174`), repository, service, view, pgTAP; il **task_code** `reset_lotto_draft` del registry può restare invariato (è il nome del task, non della funzione). (2) **Sanare l'asimmetria** di perimetro fra la versione globale e quella singola. (3) 🔴 **Correggere l'over-free del `lock_batch_id`** (C-22): la funzione per-fattura deve passare `NULL`, altrimenti resettare **una** fattura libera le attività di **tutto** il lotto. Prerequisito di D-N-bis. (4) Il «ritorno a DRAFT» che il nome evocava **non esiste** e va costruito: → **Fase 6** |
| **D-F** | Rerun della tappa EMESSA su fatture oltre soglia | ✅ **DECISA.** La funzione **per-fattura solleva** `E_SCADENZE_FATTURA_BLOCCATA`; il **wrapper di lotto filtra** su DRAFT/EMESSA e salta le altre con log non critico. Verificato che oggi lo scenario **non è raggiungibile** dal giro automatico (`_select_steps` riparte dallo step corrente in errore o dal successivo, mai indietro): è un presidio, non una riparazione. Si fa comunque perché (a) la per-fattura sarà chiamabile da endpoint e (b) il fratello `fn_ricalcola_riepiloghi_iva_lotto` **non filtra** e la sua per-fattura solleva — quindi se lo scenario diventasse raggiungibile il giro esploderebbe già una riga prima. ⚠️ Nota: quella solleva `E_PARAMETRO_INVALIDO` per un problema di **stato** — codice fuorviante, da allineare quando si tocca quell'area |
| **D-J** | `clienti.termine_pagamento_id` obbligatorio? | ✅ **DECISA: resta nullable**, con fallback al default `TP_1RATA` |
| **D-G** | Bonifiche dei dati esistenti | ✅ **DECISA: non è un cantiere.** Sono **dati di test** ([[project_no_produzione_solo_sviluppo]]): si correggono o si cancellano al momento, senza migration né passi preparatori. I 2 clienti con la coppia legacy si ripuntano al catalogo dentro 3a.4; i clienti con `M` **si contano al momento dell'applicazione** (Tid: probabilmente nessuno); le 7 fatture senza snapshot si cancellano e rigenerano. Nessuna query di bonifica da preparare in anticipo |
| **D-D** | Base di ripartizione `totale_a_pagare` a zero o negativa | ✅ **DECISA**. `NULL` → `E_SCADENZE_BASE_NON_PRONTA` (unico caso che segnala un difetto reale: passi fuori ordine). `= 0` → **nessuna rata, nessun log**: fattura interamente coperta da acconti, situazione normale. `< 0` → **nessuna rata + log NON critico** sulla fattura: un saldo a favore del cliente va visto, perché a volte è corretto e a volte è un fondo configurato male. Motivi: i fondi `F_F_ADD_ACC` sono «addebiti/**accrediti**» e si sottraggono; `fn_ricalcola_totali_fattura` tratta esplicitamente il caso negativo in ogni ramo di arrotondamento (`ELSE -ceil(abs(...))`), quindi è uno stato **previsto** dal modello; `CHECK (importo >= 0)` su `fatture_scadenze` ha già deciso che un documento a credito **non si rateizza**. ⚠️ Un errore critico qui **bloccherebbe il lotto** al primo cliente con acconto capiente. La regola non cambierà con l'arrivo del tipo documento «nota di credito» (oggi `tipo_doc_fiscale` è FRONTOFFICE/BACKOFFICE: la nota di credito **non esiste** come tipo) |
| **D-C** | Corsia GIORNALIERO / step EMESSA (`fatturazione_pipeline` id 2, `processi = []`) | ✅ **DECISA: allineare i `processi` alla corsia MASSIVO** (fondi → IVA → scadenze), **lasciando il `rollback` com'è** — la corsia immediata arriva da sola fino alla numerazione, e una fattura numerata non si resetta: darle un percorso di reset sarebbe offrire un'uscita che il gate fiscale poi nega. **Più**: estendere l'invariante pgTAP a **tutte** le tappe, non solo DEFINITIVA (C-7). Motivo della decisione: la corsia immediata **non ha fermata** (`fatturazione_driver_service.py:55`) e nessun trigger ricalcola IVA/totali — con la tappa vuota emetterebbe **da sola** documenti numerati, stampati e inviati allo SDI senza riepilogo IVA né totali. Non è una corsia che calcola meno: è una corsia che emette documenti invalidi appena qualcuno l'accende |
| **D-B** | La **modalità di pagamento** entra nella chiave di aggregazione | ✅ **DECISA: entra.** L'elemento di chiave è la **coppia** `(termine_pagamento_id, modalita_pagamento_id)` — due sole FK, coerenti con la testata e col `WHERE` del lookup (era una quaterna con `giorni_pagamento`/`fine_mese`: D-I le elimina). Catena della modalità: `ordini.modalita_pagamento_id` → `clienti.modalita_pagamento_id` → NULL (nessun default inventato: `config.modalita_pagamento` non ha una riga «default» e sceglierne una arbitrariamente finirebbe sulla FatturaPA) |

### 2.2 Ancora aperte

**Nessuna.** Tutte le decisioni sono state chiuse da Tid il 2026-07-29/30.

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
| 3a.7 | BE/FE: `ClienteDrawer.vue` (via i due campi + le 4 opzioni `opt_gg_*` e le loro chiavi i18n), `fn_update_cliente`, `clienti_repository`, `clienti_service`, `views_clienti`, `error_policies` |
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
| 3b.1 | **Una sola** implementazione della catena (C-13): `fn_resolve_termini_pagamento` riscritta **per attività** → ritorna la **coppia** `(termine_pagamento_id, modalita_pagamento_id)` (D-B + D-I), oppure eliminata e la catena vive dentro `fn_build_fattura_key`. Fix inclusi: singolare, **rimozione del ramo contratto**, filtro `cl.istanza_utility_id = ba.istanza_utility_id` al posto del `LIMIT 1`. Catena ora a **3 livelli** (era 4: il 2a legacy non esiste più): documento sorgente → cliente → default `TP_1RATA`. ⚠️ La modalità ha una catena **più corta**: `ordini` sì, `preventivi` no |
| 3b.2 | `fn_build_fattura_key` → aggiunge la coppia agli elementi di chiave |
| 3b.3 | `fn_get_or_create_fattura_header` → **lookup** allineato alla chiave (aggiunge `utility_id` — bug preesistente — e la coppia) e **INSERT** che scrive `termine_pagamento_id` e `modalita_pagamento_id` |
| 3b.4 | ~~Guard D-4 su `anagrafiche.clienti`~~ — **non serve più**: con D-I le due condizioni contraddittorie non sono più rappresentabili |
| 3b.4-bis | **Arrotondamenti, pezzo 1 (D-N)**: `fatture_arrotondamenti_scope` prende `termine_pagamento_id` e `modalita_pagamento_id` in chiave d'ambito. **Va fatto nello stesso changeset della chiave**: separarli lascia una finestra in cui due fatture condividono il saldo (C-20) |
| 3b.4-ter | **Arrotondamenti, pezzo 2 (D-N)**: `fn_ricalcola_totali_fattura` legge `saldo_scope − COALESCE(f.arrotondamento_attuale, 0)` |
| 3b.4-quater | **Arrotondamenti, pezzo 3 (D-N / C-23)**: `fn_cleanup_fatture_by_ids` storna dal saldo d'ambito l'`arrotondamento_attuale` delle fatture che cancella, prima della `DELETE`. ⚠️ Stessa funzione toccata da D-L (over-free del `lock_batch_id`): **coordinare i due interventi** in un changeset solo |
| 3b.5 | pgTAP: **idempotenza del ricalcolo** (due esecuzioni → stesso totale **e stessa scomposizione** `precedente`/`attuale`; il secondo è il test che oggi manca) · **due fatture stesso BA con termini diversi** → saldi d'ambito distinti, e il rerun non sposta i totali · un test **per livello** della catena (il livello 1 non ha dati: la fixture è il lavoro) · due attività stesso BA termini diversi → **due** fatture · termine uguale → **una** · riesecuzione → nessuna terza · **utility diverse → due fatture** (regressione sul bug chiave/lookup) · invariante «ogni elemento della chiave compare nel `WHERE` del lookup» |

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

### 3.6 Fase 6 — Ritorno del lotto a DRAFT (C-18)

Slice a sé, **dopo** le scadenze: la pulizia dei satelliti al ritorno si scrive
quando i satelliti esistono già. Realizza il disegno di Tid — *EMESSA = documento
non modificabile; per correggere si riporta a DRAFT e si ricalcola* — che oggi è
dichiarato a metà e non implementato.

Presupposto verificato (C-19): **a EMESSA la fattura non è numerata**, quindi il
ritorno non annulla mai un numero fiscale.

### 6.0 — Analisi preliminare **obbligatoria** (W-1)

> 🔴 **Questa fase descrive un'intenzione, non ancora il lavoro.** I passi
> 6.1-6.8 vanno riscritti **dopo** questa analisi, non durante
> l'implementazione. Stima: ~mezza giornata di lettura
> (`fn_pipeline_task_runtime_support`, gestione dei log critici, stati del lotto).

| # | Da chiarire | Stato |
|---|---|---|
| **A** | **`fatturazione_lotti_task_runs`**: non vengono **mai** cancellati, solo aggiornati d'esito. Tornando a DRAFT restano i record dei task già eseguiti in EMESSA, e `RESUME_STEP`/`RESUME_TASK` si basano su quelli: se li considera completati, il rilancio **salta i task che devono rigirare** | 🔴 **decisione presa (Tid)**: o si **generano task_run nuovi**, o si **resettano correttamente**. Lasciarli com'è non è un'opzione. Quale delle due, si decide con l'analisi |
| **B** | **Log critici della fattura**: `fatture_log` non viene toccato dal ritorno, e il runner blocca l'avanzamento *«con almeno una criticità attiva»*. Un lotto riportato a DRAFT con i log vecchi ancora lì **non riparte mai** | 🟡 rinviato (Tid: «vedremo»), ma va risolto prima che la fase sia dichiarabile finita |
| **C** | **Stati non fiscali del lotto** (`stato_operativo`, `stato_lotto`, `lotto_job_stato`): quali valori dopo il ritorno? E per ripartire da DRAFT servirebbe `is_lotto_in_errore = true`, che è **semanticamente sbagliato** su un lotto riaperto di proposito: serve un terzo meccanismo di ripartenza, non il riuso di quello dell'errore | 🟠 **da verificare prima dello sviluppo** |
| **D** | **Lock sulle attività**: restano bloccate col `lock_batch_id` del lotto? Se sì, `select_attivita` le ritrova prese e va verificata l'idempotenza; se no, vanno sbloccate. E `stato_esecuzione` va riportato a NULL | 🟠 **da verificare prima dello sviluppo** |
| **E** | **Concorrenza**: il runner ha `E_PIPELINE_LOTTO_IN_ESECUZIONE`, la funzione DB del ritorno non controlla nulla | 🟠 **da verificare prima dello sviluppo** |
| **F** | **Due guard dichiarati solo nei test**: il rifiuto su fattura numerata e il perimetro «solo MASSIVO» stanno nel pgTAP 6.8 ma non nei passi 6.2 e 6.5 come guard espliciti | 🟠 **da verificare prima dello sviluppo** |

> ✅ Il settimo punto emerso dall'analisi — il **saldo d'arrotondamento orfano** —
> è uscito dalla Fase 6: è un difetto autonomo, va corretto comunque, ed è
> diventato **D-N pezzo 3** in Fase 3b (C-23).

### 6.1-6.8 — I passi, da riscrivere dopo 6.0

| # | Cosa |
|---|---|
| 6.1 | Seed: append a `stati_doc_fiscale_transizioni.csv` — `EMESSA → DRAFT` con `solo_lotto = f`, `solo_fattura = t`. Il vincolo «solo MASSIVO» è già presidiato altrove: `trgfn_fatture_guard_stato` blocca ogni retrocessione sui lotti GIORNALIERO confrontando `ordine` |
| 6.2 | `vendite.fn_riporta_lotto_a_draft(p_lotto_id)`: riporta **insieme** lotto e fatture nella stessa transazione (il guard di coerenza è un constraint trigger DEFERRED: gli stati intermedi sono leciti, il risultato dev'essere allineato). **Non cancella** le fatture: le riapre |
| 6.3 | Pulizia di ciò che è stato prodotto in EMESSA: `fatture_scadenze` **cancellate**, `fatture_riepiloghi_iva` e totali azzerati, fondi via `fn_reset_fondi_fattura` (esiste già). `fatture_indirizzi` **si lasciano**: sono prodotte in DRAFT e si rigenerano da sole (upsert idempotente) |
| 6.4 | ⚠️ **Il rerun deve ripartire dallo step giusto.** In `_select_steps`, un rilancio su lotto non in errore riparte da `steps[current_index + 1]` — cioè da EMESSA, **saltando la rigenerazione delle righe in DRAFT**. Il ritorno deve lasciare il lotto in una condizione che faccia ripartire da DRAFT, altrimenti l'operatore riporta indietro il documento e poi non riesce a correggerlo |
| 6.5 | **Estrazione per-fattura da lotto EMESSA (D-N-bis)** — l'operazione «togli questa fattura dal giro»: append della transizione `EMESSA → ANNULLATA` per la **fattura**; `vendite.fn_estrai_fattura_da_lotto(p_lotto_id, p_fattura_id)` che (a) rifiuta se la fattura è **numerata**, (b) **stacca** la riga `fatturazione_lotti_fatture`, (c) porta la fattura ad **ANNULLATA**, (d) libera **solo** le sue attività. ⚠️ Dipende dalla correzione dell'over-free (D-L pt.3, C-22): senza, libera quelle di tutto il lotto |
| 6.6 | **Eliminazione del flag `esclusa` (D-M)**: `fn_lotto_emittente_stati_lf`, `fn_lotto_stato_esecuzione_v2`, `fn_guard_lotto_fatture_stato_coerente` (resta la sola eccezione `critical`), outbox di stampa, filtro API, `types.py`. Da fare **qui**, non prima: l'estrazione è ciò che rende il flag definitivamente inutile |
| 6.7 | BE/FE: il verbo nel `LottoDrawer` con la conferma esplicita di cosa si perde, e la **lista «estratte»** nel cockpit — è il promemoria che giustifica il modello «reperto» |
| 6.8 | pgTAP: transizione `EMESSA → DRAFT` ammessa per la fattura · lotto+fatture allineati al commit · scadenze e riepiloghi azzerati · ritorno rifiutato su lotto GIORNALIERO · ritorno rifiutato se **una sola** fattura è numerata · **estrazione**: fattura ad ANNULLATA e staccata, **solo** le sue attività liberate (le altre del lotto restano bloccate — è il test di C-22), estrazione rifiutata su fattura numerata |

### 3.7 Ordine di accensione, non negoziabile

1. task indirizzi (2.1-2.3) → **poi** guard `FATT` (2.5);
2. semina del catalogo termini (3a.1) → **poi** migrazione clienti (3a.4) → **poi**
   DROP delle colonne (3a.5). Invertirli lascia clienti senza condizioni;
3. riforma (Fase 3a) → **poi** chiave (Fase 3b), che dalla riforma dipende;
4. chiave (Fase 3b) → **poi** generatore scadenze (Fase 4), che dalla chiave legge;
5. generatore scadenze (Fase 4) → **poi** guard di numerazione (Fase 4b): acceso
   prima, blocca ogni numerazione perché le rate non esistono ancora;
6. satelliti completi (Fasi 2 e 4) → **poi** ritorno a DRAFT (Fase 6), che deve
   saper ripulire ciò che quelle fasi producono.

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

| Guida | Cosa cambia | Fase | Peso |
|---|---|---|---|
| **`fatturazione.md`** (988 righe) | La tabella degli step della pipeline (2 task nuovi + riempimento corsia GIORNALIERO, D-C); la semantica del reset, che cambia con la rinomina D-L e con la Fase 6; da aggiungere piano rate e snapshot indirizzi | ⏸ **fine** | **grosso** |
| **`config.termini_pagamento` — pagina NUOVA** | Nessuna guida documenta il catalogo dei termini. D-E lo rimodella e D-I lo rende **l'unico** meccanismo delle condizioni di pagamento: diventa un oggetto di primo piano. Ed è anche la guida che serve all'operatore, che ora *deve* passare dal catalogo per un termine fuori standard | ⏸ **fine** | **nuova** |
| `cruscotti-fatturazione.md` | «Rendi definitive» acquista precondizioni (D-K): non numera più qualunque cosa. La Fase 6 aggiunge un verbo al drawer lotto | 4b, 6 | medio |
| `gestione-dei-pagamenti.md` | **Non parla affatto di scadenze e piano rate**, perché non esistevano. È la guida che deve spiegarli, e il posto giusto per dire cosa *non* si può ancora fare (riconciliazione rata↔incasso, fuori scope) | 4 | medio |
| `gestione-degli-indirizzi.md` | Spiega bene soggetto vs ruolo — la nostra catena a due layer — ma non dice nulla di **snapshot sui documenti** né della **risoluzione per istanza** (C-2) | 2 | medio |
| `documenti-e-stampe.md` | Il contesto PDF documentato mostra `"indirizzo": "Via Roma 1, Milano"` letto live: dopo la Fase 2 viene dallo snapshot | 2 | piccolo |
| `generazione-cliente.md` | Il cliente perde due campi: le condizioni di pagamento vivono solo nel catalogo | 3a | piccolo |
| `gestione-ordini.md`, `gestione-preventivi.md` | Citano il termine di pagamento sul documento: con D-7 quel termine ora **determina quante fatture nascono**. È un cambio di conseguenze, non di forma | 3b | piccolo ma va detto |

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
| **W-1** | La **Fase 6** è la parte meno istruita: disegnata in pochi scambi, mentre D-I è nata da una verifica su cinque tabelle | ✅ **affrontata**: §3.6 ha ora un passo **6.0 di analisi preliminare obbligatoria** con sei punti aperti, di cui uno già deciso (task_run) e uno rinviato (log critici). Il settimo — il saldo d'arrotondamento orfano — ne è uscito ed è diventato D-N pezzo 3 |
| **W-2** | **Nessun criterio di «fatto» per le fasi DB.** Il piano BE/FE ha gli smoke di accettazione che passano dalla pipeline reale; qui ci sono i pgTAP, che verificano le funzioni ma non la catena. La 3a è la fase con più superficie e nessun collaudo end-to-end | Definire almeno un collaudo per 3a prima di iniziarla |
| **W-3** | **Nessun numero è stato riverificato**: 0 righe scadenze, 2 clienti legacy, 7 fatture, 0 ordini/preventivi vengono dai brief. Se «2 clienti» fosse «20», la 3a.4 cambia peso | Ricontare all'apply, prima di 3a.4 |
| **W-4** | Stime **ottimistiche dove c'è frontend**: «3a ~1 giornata DB» copre nove punti | Trattarle come ordine di grandezza |
| **W-5** | **Undici decisioni in una sessione.** Le prime otto istruite una per una; le ultime sono arrivate quando l'inerzia del «confermo» era già presa | Ciò che è nato da una verifica (D-I, D-K, C-18, C-20) regge meglio di ciò che è stato deciso di slancio |
