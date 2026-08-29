# Brief DB — i registri di numerazione: l'emittente obbligatorio, e il trasloco di DDT, ordini, commessa e resi

> **Destinatario:** team DB (`dev/db-tid`).
>
> **Origine.** È il cantiere che nasce dalle decisioni del 2026-08-30 registrate in
> [brief-db-numerazione-commessa-e-periodicita-sistema-codici](brief-db-numerazione-commessa-e-periodicita-sistema-codici.md).
> Quel documento è l'**analisi** e resta la sede delle ragioni; questo è il
> **piano**. Chi vuole sapere *perché*, torna là.
>
> **Stato al 2026-08-30: piano scritto, niente applicato.** Nessun changeSet,
> nessuna migrazione.
>
> ⛔ **Perimetro, e vale per ogni riga di questo piano:**
> **cambia SOLO l'algoritmo di assegnazione del numero.** Per i documenti che
> traslocano non cambia nient'altro — stati, colonne, viste, liste e **momento**
> restano quelli di oggi. Un trasloco è il momento in cui è più facile portarsi
> dietro un «già che ci siamo»: qui non se ne accetta nessuno.
>
> **Correlati:**
> [vendite.registri_fatturazione](/dbzero/vendite/tabelle/registri_fatturazione) ·
> [vendite.fn_get_next_progressivo](/dbzero/vendite/manual/fn_get_next_progressivo) ·
> [vendite.fn_lookup_registro_id](/dbzero/vendite/funzioni/fn_lookup_registro_id) ·
> [vendite.fn_get_pavimento_data_documento](/dbzero/vendite/funzioni/fn_get_pavimento_data_documento) ·
> [config.sistema_codici](/dbzero/config/tabelle/sistema_codici)

---

## 0. Il quadro in una pagina

**Due cantieri, in quest'ordine — e l'ordine è obbligato**, perché portare i
documenti su registri che ammettono ancora l'emittente nullo significherebbe
spendere un cantiere per **allargare** il difetto che l'altro chiude.

| | Cantiere | In una riga |
| --- | --- | --- |
| **1º** | **L'emittente sul registro** | `registri_fatturazione.emittente_soggetto_ruolo_id` diventa `NOT NULL`, e nasce il guard che lega la fattura al registro del **suo** emittente |
| **2º** | **Il trasloco** | `famiglia_documento` sul registro, e **DDT, ordini, commessa e resi** prendono il numero dal motore dei registri invece che dalla propria sequenza |

**Le decisioni già prese** (dettaglio e argomenti nel brief di analisi):

| Voce | Decisione |
| --- | --- |
| L'anno | dalla **data del documento**; per la commessa, che non ce l'ha, è la data di **creazione** (`script.fn_data_operativa()`) — e si **ricalcola quando si assegna il numero** |
| Buchi | ammessi: li ha il motore, li ha sempre avuti la fattura |
| Commessa | va **sui registri**; il codice porta la **sigla dell'emittente** (decisione «A», 2026-08-30) |
| Cifre | **nove** per la commessa |
| Pregresso | ⛔ **nessuna rinumerazione**, per nessun numeratore |
| Momento | **invariato** per tutti: DDT `EMESSO`, resi `CONFERMATO`, ordini `INSERT`, commessa `INSERT` |
| Preventivi, contratti, offerte | ⛔ **fuori dal cantiere**: non si toccano |
| Nome della tabella | **resta** `registri_fatturazione`; il debito è dichiarato |

---

## 1. ⭐ La scoperta che rende il cantiere 2 piccolo

**`config.sistema_codici` non perde il suo ruolo: resta il catalogo dei
FORMATI.** È il punto che decide la dimensione di tutto il resto, e non è
un'invenzione di questo piano — **è quello che il DDT fa già oggi**:

```
-- vendite.trgfn_ddt_gen_numero_emesso, oggi
SELECT prefisso, separatore, lunghezza_numero
  INTO v_prefix, v_sep, v_len
  FROM config.sistema_codici WHERE codice_interno = 'ddt';   -- il FORMATO
v_seq := nextval('vendite.ddt_numero_seq');                  -- il CONTATORE
NEW.numero := v_prefix || v_sep || lpad(v_seq::text, v_len, '0');
```

Il trasloco cambia **una riga su tre**: il contatore. Il formato resta dov'è, la
composizione resta dov'è, il momento resta dov'è.

⚠️ **Ne discende una precisazione al brief di analisi**, dove si legge
«`config.sistema_codici` non si tocca»: è vero per la **tabella** e per
`script.fn_generate_codice`, che restano identiche. Il **CSV** invece cambia, di
due righe:

* `ordine` → `usa_sequenza` da `t` a **`f`**: la riga smette di generare e resta
  un formato. ⭐ Il trigger generato e la sua funzione li **smonta da solo**
  `script.trgfn_config_sistema_codici_sync_gen_codice`, che su
  `usa_sequenza <> TRUE` fa `DROP TRIGGER` e `DROP FUNCTION`. Non serve DDL a
  mano. ⚠️ La sequenza `vendite.ordini_numero_seq` **non** viene toccata, ed è
  giusto: è la memoria dei numeri già consumati;
* `commessa` → **riga nuova**, `usa_sequenza = f`, prefisso `CMM`, separatore
  `-`, `lunghezza_numero` **9**. ⛔ Append **a mano** al CSV, mai con
  `csv.writer`. ⚠️ E il mirror `20250813-05` elenca le colonne una per una: qui
  non se ne aggiungono, quindi il loader **non** si tocca.

⛔ **Attenzione al FE, ed è l'unica ricaduta fuori dal DB**: `usa_sequenza` è ciò
che `frontend/src/core/composables/useCodiceField.js` legge come `isAuto`, e
`isEditable = !isAuto`. Portando `ordine` a `f`, una maschera che usasse quel
composable **inviterebbe l'operatore a digitare il numero**. Va verificato prima
di applicare — è la stessa condizione in cui il DDT si trova già oggi, quindi la
risposta esiste già da qualche parte.

---

## 2. Cantiere 1 — L'emittente sul registro

### 2.1 ⛔ Prima del DDL c'è una ricognizione, e non è un dettaglio

`emittente_soggetto_ruolo_id` è nullable **e usato**: `fn_lookup_registro_id` ha
come quarto livello di fallback proprio il registro senza emittente. Prima di
rendere la colonna obbligatoria bisogna sapere, per ogni registro con emittente
`NULL`, **quali emittenti ci hanno scritto sopra**.

⚠️ **Non è una misura che decide il progetto** — il progetto è deciso — è una
misura che serve a **eseguire una bonifica**: dice quante righe di registro
servono e a chi assegnarle, non se farlo.

⛔ **E può portare un caso che il DDL da solo non risolve:** un registro generico
con fatture di **due** emittenti diversi. Quelle fatture sono già numerate e
⛔ **non si ripuntano** — cambiare il registro di una fattura numerata le cambia
il sezionale, cioè l'identità del suo numero. Il registro va assegnato a **uno**
degli emittenti, e le fatture dell'altro restano su un registro che non è del
loro emittente: righe storiche coerenti con sé stesse e incoerenti con la regola
nuova.
⭐ È il motivo per cui il guard del §2.3 deve nascere **`BEFORE INSERT OR UPDATE`
e non come `CHECK` sulla tabella**: un `CHECK` verrebbe validato sul pregresso e
fallirebbe; il trigger presidia il futuro e lascia stare la storia.

### 2.2 I changeSet

| # | Cosa | Note |
| --- | --- | --- |
| **C1-1** | *(dato, a rubinetto chiuso)* Un registro per emittente al posto dei generici, e `UPDATE` dell'emittente sui registri che ne restano privi | forward-only. ⚠️ Nessun ripuntamento di fatture |
| **C1-2** | `ALTER TABLE vendite.registri_fatturazione ALTER COLUMN emittente_soggetto_ruolo_id SET NOT NULL` | ⭐ Da fare con il pattern in due passi — `CHECK (... IS NOT NULL) NOT VALID`, `VALIDATE`, poi `SET NOT NULL` — che evita il lock lungo di uno scan pieno |
| **C1-3** | `vendite.trgfn_fatture_guard_registro_emittente()` + trigger `BEFORE INSERT OR UPDATE` su `vendite.fatture` | ⚠️ `SECURITY DEFINER`: legge `registri_fatturazione`, e un registro invisibile sotto RLS non deve leggersi come «assente» |
| **C1-4** | Nuovo codice errore `E_FATTURA_REGISTRO_EMITTENTE_INCOERENTE`, classe **TECNICO** | ⛔ Solo **append** al CSV `codici_errore.csv`, nessun loader nuovo. Tecnico e non `DATO_ERRATO`: il registro non lo sceglie una persona in un dialog, lo risolve `fn_get_registro_id` |
| **C1-5** | `fn_lookup_registro_id`: potatura dei livelli **2** e **4** dell'`ORDER BY` (quelli con `r.emittente_soggetto_ruolo_id IS NULL`) | ⭐ Firma e `RETURNS TABLE` invariati → `CREATE OR REPLACE` basta, niente `DROP`. ⚠️ Il `WHERE` perde `r.emittente_soggetto_ruolo_id IS NULL OR`: senza, il predicato resterebbe più largo dell'ordinamento |

### 2.3 I presidi

* un `INSERT` di fattura su un registro di **un altro** emittente solleva
  `P0001` con quel codice — `throws_ok` **con** SQLSTATE;
* la stessa fattura sul registro **giusto** passa (il gemello positivo, o il test
  non distingue «respinge tutto» da «respinge il caso giusto»);
* `fn_lookup_registro_id` con un emittente che **non ha** registro per quel tipo
  documento risponde `registro_id NULL` — e l'involucro `fn_get_registro_id`
  solleva `E_CONFIG_MANCANTE`. ⭐ È il fail-closed nuovo, e va provato che sia
  **rumoroso**;
* ⚠️ marcare `PGTAP_RUNNER` e motivarlo se owner.

---

## 3. Cantiere 2 — Il trasloco

### 3.1 Il modello: una colonna e un `CHECK` condizionato

| # | Cosa | Note |
| --- | --- | --- |
| **C2-1** | `famiglia_documento text NOT NULL DEFAULT 'FATTURA'` su `registri_fatturazione`, `CHECK IN ('FATTURA','DDT','ORDINE','COMMESSA','RESO')` | ⭐ Il default vale solo per il pregresso: le righe esistenti **sono** registri di fatturazione |
| **C2-2** | `CHECK` condizionato: `limite_emissione_giorni`, `limite_emissione_giorno_mese` e una `politica_data_documento` diversa da quella neutra sono ammessi **solo** con `famiglia = 'FATTURA'` | ⛔ Per vincolo, non per abitudine: sono regole della fattura differita, e su un DDT non vogliono dire niente |
| **C2-3** | `UNIQUE (famiglia_documento, emittente_soggetto_ruolo_id, utility_id)` — nella forma che ammette `utility_id` nullo | ⭐ È ciò che rende deterministica la risoluzione del §3.2: *un* registro per famiglia, emittente e utility |

⭐ **E qui il motore lavora già nel verso giusto senza modifiche:** su un
registro non-`FATTURA` le colonne del limite restano nulle, quindi
`fn_get_pavimento_emissione` non ha pavimento da dare e
`fn_get_pavimento_data_documento` risponde «nessun vincolo» — un caso che quella
funzione **documenta già**. Il cancello di monotonia si spegne da sé dove non
serve, e resta acceso dove serve.

⚠️ **Sul registro `ORDINE` deve restare spento anche il pavimento di sequenza**,
cioè non si scrive `ultima_data`: l'ordine si numera all'`INSERT`, e un ordine in
bozza con una data indietro bloccherebbe tutti gli altri.

### 3.2 La risoluzione del registro

| # | Cosa | Note |
| --- | --- | --- |
| **C2-4** | `vendite.fn_lookup_registro_documento(p_famiglia, p_emittente, p_utility)` — **legge e torna NULL** | ⭐ Non passa da `tipi_doc_fiscale_registri`: quella mappa parte dal tipo documento fiscale, che DDT, ordine, commessa e reso **non hanno**. Qui la chiave è (famiglia, emittente, utility) |
| **C2-5** | `vendite.fn_get_registro_documento(...)` — **involucro che solleva** | ⭐ Stessa coppia lettore/involucro già in casa (`fn_lookup_registro_id` / `fn_get_registro_id`, `fn_get_ba_emittente_sr_id` / `fn_get_emittente_fiscale_id`). Chi **scrive** consuma questo |

⛔ **Le fatture continuano a usare la loro risoluzione** (`fn_get_registro_id`,
per tipo documento e natura): non si unifica niente. Sono due strade verso la
stessa tabella, e la ragione è che partono da chiavi diverse.

### 3.3 Il motore reso agnostico

| # | Cosa | Note |
| --- | --- | --- |
| **C2-6** | `fn_get_next_progressivo`: il **ramo d'errore** smette di cercare l'ultima **fattura** per comporre il bersaglio | ⚠️ Il percorso felice non legge già oggi `vendite.fatture`: la competenza arriva come parametro. Cambia solo il ramo d'errore, e i `%TYPE` che riflettono colonne di `fatture` |
| **C2-7** | Codici errore gemelli, neutri sul documento | ⛔ Append al CSV. I due esistenti (`E_FATTURA_DATA_ANTERIORE_ULTIMO_NUMERO`, `E_FATTURA_DATA_OLTRE_LIMITE_EMISSIONE`) **restano intatti**: rinominarli sarebbe rumore su punti di log che nessuno ha chiesto di toccare |

### 3.4 I quattro documenti, uno per uno

Per **ognuno** la modifica ha la stessa forma: si sostituisce il `nextval` con la
chiamata al motore, si risolve il registro, si ri-deriva l'anno. Tutto il resto —
lo stato in cui si numera, la colonna, il formato — resta quello di oggi.

| # | Documento | Cosa cambia | ⛔ La condizione che rompe se dimenticata |
| --- | --- | --- | --- |
| **C2-8** | **DDT** | `vendite.ddt` guadagna `registro_id`; `trgfn_ddt_gen_numero_emesso` chiama il motore; `anno` **ri-derivato** dalla data documento nello stesso statement del numero | `uq_ddt_v_anno_serie_numero` deve guadagnare **`registro_id` nello stesso passo**, e **prima** che esca il primo numero nuovo |
| **C2-9** | **Ordini** | idem, **momento invariato** (`INSERT`) | come sopra su `uq_ordini_v_anno_serie_numero` |
| **C2-10** | **Resi** | idem, momento `CONFERMATO` | `uq_resi_anno_numero` → `(registro_id, anno, numero)` |
| **C2-11** | **Commessa** | `fn_get_or_create_commessa` smette di comporre `CMM-<timestamp>-<md5>` e compone `CMM-<sigla>-<anno>-<numero a 9 cifre>` | ⭐ **Nessuna colonna nuova su `commesse`**: la sigla e l'anno stanno **nella stringa**, quindi `uq_commesse_codice` resta intatta e continua a bastare da sola per trovare una commessa |

**Sulla commessa, tre dettagli che decidono se funziona:**

* la **sigla** viene da `anagrafiche.emittenti_fiscali.codice` — `NOT NULL`,
  `UNIQUE` e **immutabile** (`trgfn_lock_columns`). ⚠️ Ma la sua **forma** non è
  vincolata da nessun `CHECK`: 32 caratteri, e nulla vieta un `-` dentro. **In
  questo cantiere ci va un vincolo di forma**, o un codice commessa smette di
  essere decomponibile a occhio proprio per l'emittente che ha scelto male la
  sigla;
* l'**anno** è quello di `script.fn_data_operativa()` — la commessa nasce e si
  data nello stesso istante;
* ⛔ la commessa **non nasce** se il suo emittente non ha un registro `COMMESSA`.
  È fail-closed, cioè il verso giusto, ma è un comportamento **nuovo** e ferma il
  fan-out di fatturazione: va nel collaudo, non nella sorpresa.

### 3.5 I dati

| # | Cosa | Note |
| --- | --- | --- |
| **C2-12** | Una riga di registro per **ogni emittente** e ogni famiglia che gli serve (`DDT`, `ORDINE`, `COMMESSA`, `RESO`) | ⛔ Va fatto **prima** di accendere i generatori nuovi, o il primo documento fallisce. ⚠️ È dato di installazione, non seed di catalogo: non va in un CSV di `80_data` |
| **C2-13** | Le due righe del CSV `sistema_codici`: `ordine` a `usa_sequenza = f`, riga nuova `commessa` | §1 |

⭐ **I contatori ripartono da 1**, e i numeri già emessi non li alzano. Non
collidono con i vecchi perché **la forma è diversa** — ⛔ e questa è l'unica cosa
che li separa: chi cambia il formato dei numeri nuovi sta toccando anche la
ragione per cui non collidono con i vecchi.

### 3.6 I presidi

* per **ciascuno** dei quattro: il numero esce dal registro giusto, l'anno è
  quello della data documento, la forma della stringa è quella attesa;
* ⭐ **il reset di Capodanno**, provato **seminando** la riga di contatore
  dell'anno prima e verificando che l'anno corrente riparta da 1. ⚠️ Il tempo non
  si simula: si costruisce il caso;
* ⭐ **due emittenti, stesso anno**: due numeri **1** che convivono perché la
  chiave porta il registro. È il test che prova la condizione «che rompe», e va
  scritto per primo;
* la commessa che **non nasce** senza registro: `throws_ok` con SQLSTATE;
* il DDT creato a dicembre ed emesso a gennaio: l'anno è **quello
  dell'emissione**, non quello dell'`INSERT`;
* ⚠️ **cosa i pgTAP non possono provare**: che il cancello stia *sotto* il lock —
  pgTAP è mono-sessione. Si presidia in **review**, come già scritto per
  `fn_get_next_progressivo`.

### 3.7 La guida

| # | Cosa |
| --- | --- |
| **C2-14** | In `docs/it/dbzero/config/manual/sistema_codici.md`: **quando spostare un numeratore sui registri** — il criterio (*il periodo il generatore se lo calcola da sé; emittente, serie e un momento diverso dall'`INSERT` arrivano dalla riga*), i tre campanelli in parole d'uso, e la **checklist del trasloco** |
| **C2-15** | Il **debito sul nome** dichiarato nelle quattro sedi: `COMMENT` della tabella, `COMMENT` di `famiglia_documento`, doc manuale, brief |

---

## 4. L'ordine, e cosa non entra

**Ordine obbligato:** C1 tutto → C2-1/2/3 (il modello) → C2-4/5 (la risoluzione)
→ C2-12 (i dati) → C2-6/7 (il motore) → C2-8..11 (i documenti, uno alla volta) →
C2-13 → i presidi → la guida.

⚠️ **I documenti si traslocano uno alla volta**, non tutti in un changeSet: se
qualcosa va storto si sa quale. E ognuno porta con sé la propria `UNIQUE`, nello
**stesso** changeSet — mai in due.

⚠️ Numerazione dei file `YYYYMMDD-NN` **globale per data**, non per cartella.
⛔ Negli YAML si cita il **nome** del brief, mai il path `work-in-progress/`.

**Non entra in questo cantiere:**

* ⛔ il **rename** di `registri_fatturazione` — cantiere suo, che non cambia
  nessun comportamento;
* ⛔ il **momento** di preventivi, contratti e offerte, e il loro trasloco;
* ⛔ il **reset annuale** come comportamento nuovo su preventivi/contratti/offerte;
* ⛔ la **rinumerazione** di qualunque pregresso;
* ⛔ qualunque modifica a colonne, stati, viste o liste dei documenti che
  traslocano.

---

## 5. I rischi noti, dichiarati prima

1. ⛔ **La `UNIQUE` in ritardo di un passo** — è l'unico errore che non degrada ma
   **ferma**: `23505` al primo documento dell'anno del secondo emittente, con una
   violazione di indice **senza codice di dominio** che non spiega niente a
   nessuno. Va per prima nella checklist di ogni documento.
2. ⚠️ **Il registro mancante ferma il documento.** È il verso giusto, ma il
   passaggio C2-12 non è opzionale e non è rinviabile.
3. ⚠️ **Il pregresso incoerente del cantiere 1**: le fatture di un emittente su un
   registro assegnato a un altro restano lì. Il guard presidia il futuro; la
   storia va **dichiarata**, non ripulita.
4. ⚠️ **La sigla senza vincolo di forma** rende il codice commessa illeggibile per
   l'emittente che sceglie male. Il vincolo va messo **in questo cantiere**.
5. ⚠️ **`ordine` a `usa_sequenza = f`** può accendere il campo numero in una
   maschera che usa `useCodiceField`. Da verificare prima di applicare.
