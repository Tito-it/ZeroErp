# Brief DB — i registri di numerazione: l'emittente obbligatorio, e il trasloco di DDT, ordini, commessa e resi

> **Destinatario:** team DB (`dev/db-tid`).
>
> **Origine.** È il cantiere che nasce dalle decisioni del 2026-08-30 registrate in
> [analisi-db-numerazione-documenti-e-due-motori](analisi-db-numerazione-documenti-e-due-motori.md).
> Quel documento è l'**analisi** e resta la sede delle ragioni; questo è il
> **piano**. Chi vuole sapere *perché*, torna là.
>
> 🎉 **Stato al 2026-08-31 — CANTIERE CHIUSO LATO DB.** C1 e C2 non hanno più
> changeSet da scrivere, la guida (C2-14) e il debito sul nome (C2-15) sono
> scritti, il vincolo di forma sulla sigla (§5.4) è chiuso, e **tutti i presidi
> sono scritti e verdi** (§6).
>
> *(Superato il paragrafo che stava qui e diceva «i PRESIDI no · restano da
> scrivere 7 presidi su 10». Era vero il pomeriggio del 2026-08-31 e non lo è
> più: i sette sono stati scritti in giornata, in tre file, e girano verdi.)*
>
> ⭐ **Restava una distinzione che vale la pena conservare**, perché è il motivo
> per cui i presidi sono stati scritti: *«nessuna regressione» non è «provato»*.
> Il motore girava già in molti test — **33** portano un DDT a `EMESSO`, **75**
> creano commesse — e la baseline verde dimostrava che non esplode, non blocca e
> non solleva. ⚠️ Ma nessuno **guardava il numero prodotto**: le asserzioni su
> `ddt.numero`, `resi.numero` o sul formato `CMM-<sigla>-<anno>-<9 cifre>` erano
> **zero**. Copertura di esecuzione, non di asserzione.
>
> **Resta fuori dal DB**, ed è tutto:
>
> | | Cosa | Per chi |
> | --- | --- | --- |
> | ⛔ | `E_BA_EMITTENTE_CON_STORIA` passa da **4 a 3** segnaposto; nel `dettaglio` `n_fatture`/`n_commesse` diventano `storia` (array di `{famiglia, descrizione, n}`) e `n_documenti`. ⭐ Il `reason_key` **non** cambia | **BE** |
> | ⚠️ | `ordine` passa a `usa_sequenza = false`: è ciò che `useCodiceField` legge come `isAuto`, quindi una maschera potrebbe invitare a digitare il numero | **FE** |
>
> ⚠️ **«Applicato» qui non è una fonte**: le righe segnate ✅ sono *scritte*, e
> l'apply si chiede a `databasechangelog`, non a questa tabella. Tid ha
> dichiarato applicati i changeSet fino al `20260831-15`.
>
> | | Cosa | Dove |
> | --- | --- | --- |
> | ✅ | **C1-4** — codice errore `E_FATTURA_REGISTRO_EMITTENTE_INCOERENTE` (`TECNICO`) + messaggio `it` (id 1026) | append ai due CSV di `80_data/sql/config/` |
> | ✅ | **C1-3** — `vendite.trgfn_fatture_guard_registro_emittente()` + trigger | `20_code/vendite/20260830-10-…-mctit.yaml` |
> | ✅ | **C1-1** — bonifica dati | ⭐ **non serve**: la ricognizione del §2.1, eseguita da owner il 2026-08-30, ha dato **zero righe** su entrambe le query |
> | ✅ | **C1-2** — `emittente_soggetto_ruolo_id` → `NOT NULL` | `00_schema/vendite/20260830-11-…-mctit.yaml` |
> | ✅ | **C1-5** — la gerarchia di `fn_lookup_registro_id` da 4 livelli a 2 | `20_code/vendite/20260830-12-…-mctit.yaml` |
> | ✅ | I **presidi pgTAP** del §2.3 | `db/pgtap/vendite/test-fatture-guard-registro-emittente.sql` (plan 6) |
> | ⚠️ | **11 fixture pgTAP esistenti riparate** | inserivano un registro **senza emittente**: dopo C1-2 fallivano tutte sul `23502` |
>
> **Cantiere 2 — il modello è scritto** (niente applicato):
>
> | | Cosa | Dove |
> | --- | --- | --- |
> | ✅ | **C2-0** — catalogo `vendite.famiglie_documento` | `00_schema/vendite/20260830-13` |
> | ✅ | **C2-0 (seed)** — le cinque famiglie | `80_data/…/20260830-14` + `sql/vendite/famiglie_documento.csv` |
> | ✅ | **C2-1/2/3** — `famiglia_documento`, `CHECK` condizionato, `UNIQUE` parziale | `00_schema/vendite/20260830-15` |
> | ✅ | **C2-1 (coda)** — la FK verso il catalogo | `90_end/20260830-16` — ⛔ in `90_end` perché `80_data` gira **dopo** `00_schema` |
> | ✅ | **C2-1 (coda)** — riga `dbops.fk_index_policy` | `80_data/…/20260830-17` |
> | ✅ | **C2-4** — il **lettore** `fn_lookup_registro_documento` | `20_code/vendite/20260831-01` |
> | ✅ | **C2-5** — l'**involucro** `fn_get_registro_documento` | `20_code/vendite/20260831-02` |
> | ✅ | **C2-12** — i registri per emittente e famiglia (8 righe) | `80_data/…/20260831-03` |
> | ✅ | **C2-12-bis** — l'emittente **nuovo o riattivato** li prende da sé | `20_code/vendite/20260831-04` — ⭐ lacuna chiusa per decisione di Tid, benché fuori perimetro |
> | ✅ | **C2-6 (1ª metà)** — il limite di emissione vale solo per `FATTURA` | `20_code/vendite/20260831-05` — ⛔ **corregge un'affermazione sbagliata** del `20260830-15` |
> | ✅ | **C2-6/7 (2ª metà)** — il motore agnostico + `E_DOCUMENTO_DATA_ANTERIORE_ULTIMO_NUMERO` | `20_code/vendite/20260831-06` + append ai CSV |
> | ✅ | **C2-8** — il **DDT**: `registro_id`, la `UNIQUE` che lo segue, il generatore | `00_schema/vendite/20260831-07` + `20_code/vendite/20260831-08` + `80_data/…/20260831-09` |
> | ✅ | **C2-9** — gli **ordini**: idem, e `presidia_data_documento` sul catalogo | `00_schema/vendite/20260831-10` e `-11` + `20_code/vendite/20260831-12` e `-13` |
> | ✅ | **C2-10** — i **resi**: idem, momento `CONFERMATO` | `00_schema/vendite/20260831-14` + `20_code/vendite/20260831-15` |
> | ✅ | **C2-11** — la **commessa**: `CMM-<sigla>-<anno>-<9 cifre>` al posto di `CMM-<timestamp>-<md5>` | `20_code/vendite/20260831-16` |
> | ✅ | **C2-13** — le due righe di `sistema_codici` (`ordine` a `usa_sequenza = f`, riga nuova `commessa`) | `80_data/sql/config/sistema_codici.csv` |
> | ✅ | **C2-16** — la «storia» del BA **derivata** dal catalogo, in due funzioni | `20_code/anagrafiche/20260831-17` |
> | ✅ | **C2-18** — il guard sul catalogo (`to_regclass` + `pg_attribute`) | `20_code/vendite/20260831-18` + codice errore `E_FAMIGLIA_DOCUMENTO_RIFERIMENTO_INESISTENTE` |
> | ✅ | **C2-17** — la check e la frase che nomina **quale specie** di documento blocca | `20_code/script/20260831-19` + messaggio `1006` riscritto a **tre** segnaposto |
> | ✅ | I **presidi pgTAP** del C2-18 | `db/pgtap/vendite/test-famiglie-documento-guard-riferimenti.sql` (plan 7) |
> | ⛔ | **C2-9 corretto**: il cancello di monotonia vale sulla **sola** `FATTURA` | CSV `famiglie_documento.csv` + `00_schema/vendite/20260831-20` (la frase) |
> | ✅ | **C2-14** — la guida «quando un numeratore trasloca sui registri» | `dbzero/config/manual/sistema_codici.md` rev 2026-08-31 |
> | ✅ | **C2-15** — il debito sul nome nelle **quattro** sedi | `00_schema/vendite/20260831-21` + doc manuale + §3.8 di questo brief |
> | ✅ | **§5.4** — la sigla dell'emittente ha una **forma**, e il pregresso è bonificato | `00_schema/anagrafiche/20260831-22` + `20_code/anagrafiche/20260831-23` + append ai CSV |
> | ✅ | I **presidi pgTAP** della forma | `db/pgtap/anagrafiche/test-emittenti-fiscali-codice-forma.sql` (plan 8) |
> | ⚠️ | **2 pgTAP esistenti adeguati** alla forma nuova della storia | `anagrafiche/test-ba-cambio-emittente-storia-v1.sql`, `script/test-search-scope-interno-v1.sql` |
>
> ⚠️ **Coda del C1, non prevista dal piano**: il `NOT NULL` ha rotto **11 fixture
> pgTAP** (inserivano un registro senza emittente) e il guard ne ha scoperte
> **altre 40** che sceglievano registro ed emittente con **due pescate
> indipendenti** — che coincidessero era un caso. Riparate tutte, con l'helper
> `script.fn_pgtap_registro_fattura` (`20_code/script/20260830-18`) al posto di
> 40 copie della stessa regola. ⭐ Quattro file che sembravano rotti non lo
> erano: creano la fattura con `fn_get_or_create_fattura_header`, cioè dal
> percorso applicativo — la prova che il guard morde **solo dove la fixture
> scavalca la funzione**.
>
> ⛔ **Nessuna migrazione viene applicata senza richiesta esplicita**, e
> «procedi» non è quella richiesta. I changeSet dal `20260831-16` in poi sono
> scritti ma **non provati**: provarli significa eseguire l'SQL **estratto dallo
> YAML** in `BEGIN; … ROLLBACK;` sul DB di sviluppo, e serve un via libera.
>
> ⛔ **`20260831-17` e `-19` vanno applicati nella STESSA corsa**, e non è
> pignoleria: il primo cambia il `RETURNS TABLE` della storia, il secondo è
> l'unico che sa leggerlo. Fra i due, `script.fn_check_ba_cambio_emittente`
> fallirebbe a runtime — e il primo a scoprirlo sarebbe un operatore che prova a
> togliere un mapping. Il messaggio a tre segnaposto arriva con `80_data`, cioè
> nella stessa corsa.
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
| Cambio emittente del BA | ⛔ **bloccato quando anche un solo documento del BA è già NUMERATO** su un registro — non più solo fatture e commesse (§3.7) |

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

> ✅ **ESEGUITE da owner il 2026-08-30: entrambe ZERO righe.** Nessun registro
> senza emittente, nessun mapping che ci punti ⇒ **C1-1 non serve**.
> ⚠️ E quello zero **non** è il motivo del `NOT NULL` — il motivo sta sul
> modello (§11) — dice soltanto che l'`ALTER` passa senza bonifica. Il DB di
> sviluppo non è ricostruito da zero: su un'altra installazione i registri
> generici possono esserci, ed è per questo che `20260830-11` porta una
> **preCondition** che ri-conta i `NULL` e ferma il migrate con un messaggio
> leggibile invece di far fallire l'`ALTER` a metà.

#### Le due query della ricognizione — ⛔ da eseguire da OWNER

```sql
-- 1) I registri senza emittente, e CHI ci ha scritto sopra.
--    Una riga per (registro, emittente che ha fatturato li').
--    Piu' righe sullo stesso registro = il caso che il DDL non risolve.
SELECT r.id                                            AS registro_id,
       r.codice                                        AS registro_codice,
       r.attivo,
       f.emittente_soggetto_ruolo_id                   AS emittente,
       count(f.id)                                     AS n_fatture,
       count(f.id) FILTER (WHERE f.numero IS NOT NULL) AS n_numerate,
       min(f.data)                                     AS dal,
       max(f.data)                                     AS al
  FROM vendite.registri_fatturazione r
  LEFT JOIN vendite.fatture f ON f.registro_id = r.id
 WHERE r.emittente_soggetto_ruolo_id IS NULL
 GROUP BY r.id, r.codice, r.attivo, f.emittente_soggetto_ruolo_id
 ORDER BY r.codice, n_fatture DESC;

-- 2) I mapping che puntano a quei registri: sono le righe da duplicare
--    per emittente quando i registri generici si separano.
SELECT r.codice AS registro_codice, m.tipo_doc_fiscale_id, m.natura_doc_id, m.serie
  FROM vendite.tipi_doc_fiscale_registri m
  JOIN vendite.registri_fatturazione r ON r.id = m.registro_id
 WHERE r.emittente_soggetto_ruolo_id IS NULL
 ORDER BY r.codice, m.tipo_doc_fiscale_id, m.natura_doc_id;
```

⛔ **La prima query va eseguita da OWNER, non dall'utente applicativo.**
`vendite.fatture` ha la RLS: sotto il perimetro di un operatore il conteggio
tornerebbe **parziale**, e la bonifica verrebbe pianificata su mezza fotografia —
proprio nel caso che conta, quello del registro usato da **due** emittenti, dove
il secondo è per definizione fuori dal perimetro del primo.

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
| **C2-0** | `vendite.famiglie_documento` — il **catalogo delle famiglie**: `codice_interno`, `schema_tabella`, `nome_tabella`, `colonna_numero`, `colonna_billing_account`, `attivo` | ⭐ È ciò che rende derivabile il presidio del §3.7 invece che copiabile. Stessa forma di `config.sistema_codici` |
| **C2-1** | `famiglia_documento` su `registri_fatturazione`, `NOT NULL DEFAULT 'FATTURA'`, **FK** verso `famiglie_documento` | ⭐ Il default vale solo per il pregresso: le righe esistenti **sono** registri di fatturazione. ⭐ FK e non `CHECK`: il vocabolario è un dato, e una famiglia nuova non deve richiedere un `ALTER` |
| **C2-2** | `CHECK` condizionato: `limite_emissione_giorni`, `limite_emissione_giorno_mese` e una `politica_data_documento` diversa da quella neutra sono ammessi **solo** con `famiglia = 'FATTURA'` | ⛔ Per vincolo, non per abitudine: sono regole della fattura differita, e su un DDT non vogliono dire niente |
| **C2-3** | `UNIQUE (famiglia_documento, emittente_soggetto_ruolo_id, utility_id)` — nella forma che ammette `utility_id` nullo | ⭐ È ciò che rende deterministica la risoluzione del §3.2: *un* registro per famiglia, emittente e utility |

⛔ **QUESTO PARAGRAFO ERA SBAGLIATO, ed è stato corretto il 2026-08-31.**

*(Diceva: «su un registro non-`FATTURA` le colonne del limite restano nulle,
quindi `fn_get_pavimento_emissione` non ha pavimento da dare e
`fn_get_pavimento_data_documento` risponde "nessun vincolo" — il cancello si
spegne da sé». **Falso.**)*

`vendite.fn_get_pavimento_emissione` dichiara nel proprio `COMMENT`: *«Torna
SEMPRE una data, mai NULL: il pavimento generale esiste sempre»* — senza
override sul registro i giorni si leggono da `config.parameters`. Misurato il
2026-08-31 su un registro di famiglia `DDT`: pavimento **2026-08-19**, cioè
**attivo**. Un DDT datato più indietro sarebbe stato rifiutato da una regola che
riguarda le fatture.

⭐ **La correzione è il changeSet `20260831-05`**: il limite di emissione si
applica alla sola famiglia `FATTURA`, e la distinzione sta dentro
`fn_get_pavimento_data_documento` — che è **la sede unica** dei due pavimenti.
Metterla nel solo cancello lascerebbe la nascita del documento e la targa del
dialog a proporre un pavimento che poi non si applica: tre risposte diverse alla
stessa domanda.

⚠️ **Il `CHECK` condizionato del `20260830-15` resta giusto** per la sua ragione
— su una famiglia non fiscale quelle colonne non devono essere *valorizzabili*.
Sbagliata era solo la conseguenza che ne traevo. ⛔ E il suo `COMMENT`, già
applicato, porta ancora la frase sbagliata: non si può riscrivere, e la
correzione vive nel `COMMENT` di `fn_get_pavimento_data_documento` e qui.

⭐ **La lezione, che vale oltre questo caso**: «la colonna di override è nulla»
non significa «la regola è spenta». Un default che vive altrove — in
`config.parameters` — non si vede guardando la tabella.

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

#### ⛔ Correzione del 2026-08-31 — il cancello di monotonia vale solo sulla fattura

Il `20260831-11` aveva messo `presidia_data_documento` a `false` sul **solo
ordine**, motivandolo così: *«ha senso su chi si emette — fattura, DDT, reso: la
data la sceglie una **persona**, e una sequenza che torna indietro è un difetto»*.

⛔ **L'argomento è rovesciato.** È proprio perché la data la sceglie una persona che
la **retrodatazione** è un caso d'uso vivo: un DDT per la spedizione di ieri,
inserito stamattina dopo che ne è già uscito uno datato oggi.

⚠️ **E non è stato dedotto, è stato scoperto girando.** Il pgTAP
`test-vw-partite-merce-riconsegna-dopo-nc-v1` è diventato rosso: la ri-consegna
nasce da `fn_genera_ddt_riconsegna(..., p_data)`, e quella data **il backend la
passa dal corpo della richiesta**. ⛔ La conseguenza non è locale alla fixture:
`fn_get_pavimento_sequenza` legge `max(ultima_data)` da
`registri_fatturazione_progressivi`, che è **stato persistente** — emesso un DDT
con la data di oggi, su quel registro nessun DDT con data anteriore passa più.

✅ **Deciso da Tid il 2026-08-31: il cancello vale sulla sola famiglia `FATTURA`.**
È una regola fiscale e vive dove c'è il registro fiscale. ⭐ Ed è anche il
perimetro dichiarato del cantiere: *«cambia SOLO l'algoritmo di assegnazione del
numero»* — il cancello è un **rifiuto** nuovo, non un algoritmo, e su DDT, resi e
commessa il generatore di prima della data non sapeva nulla.

⭐ **L'anno non c'entra e non cambia**: resta quello della data documento
(decisione D-1). Il flag governa il solo pavimento.

⭐ **Il presidio esiste già ed è quello che ha trovato il difetto**: finché
`test-vw-partite-merce-riconsegna-dopo-nc-v1` resta verde, un DDT retrodatato
prende il numero.

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
* **la storia allargata (§3.7)**: un BA con un solo **DDT numerato** non si sposta
  più; lo stesso BA con un DDT **in bozza** si sposta ancora. ⭐ Sono due test
  gemelli, e senza il secondo il primo non distingue «blocca il numerato» da
  «blocca tutto»;
* ⚠️ **cosa i pgTAP non possono provare**: che il cancello stia *sotto* il lock —
  pgTAP è mono-sessione. Si presidia in **review**, come già scritto per
  `fn_get_next_progressivo`.

### 3.7 ✅ La «storia» che blocca il cambio emittente del BA si allarga

> ✅ **DECISO (Tid, 2026-08-30). La regola, in una riga:**
> **lo spostamento di un billing account si blocca quando anche un solo documento
> del BA è già NUMERATO su un registro.**

**Perché entra in questo cantiere e non è un «già che ci siamo».** Oggi
`anagrafiche.fn_get_storia_emittente_ba` conta **fatture e commesse**, e dichiara
nel proprio corpo perché ordini e DDT restano fuori: *«il loro emittente ha un
guard che lo ricontrolla col BA a ogni scrittura, quindi non è una copia
stantia»*. ⛔ **È il trasloco a renderlo falso**: da qui in poi un DDT o un ordine
numerato porta un `registro_id` congelato, e un registro appartiene a **un**
emittente. Un numero non si riscrive: è esattamente ciò che quella funzione
chiama «storia». Se il conteggio non si allarga, il guard ammetterà uno
spostamento che lascia **orfano un documento numerato** — lo stesso difetto muto
che quel guard esiste per impedire, in un punto nuovo.

| # | Cosa | Note |
| --- | --- | --- |
| **C2-16** | `fn_get_storia_emittente_ba` **deriva** dal catalogo invece di elencare: per ogni famiglia attiva, esiste un documento di quel BA con il numero valorizzato? | ⛔ **Solo i numerati**: una bozza non ha congelato niente. ⚠️ Cambia il `RETURNS TABLE` → serve **`DROP`**. ⭐ `EXISTS` per il guard, `count` solo per il messaggio |
| **C2-18** | Guard sul catalogo: schema, tabella e colonne dichiarate **devono esistere** (`pg_attribute`) | ⛔ Senza, una riga sbagliata rompe il guard del BA a runtime invece che al deploy |
| **C2-17** | `script.fn_check_ba_cambio_emittente` e il messaggio d'errore | Il conteggio nel messaggio deve dire **quale specie** di documento blocca, o l'operatore non sa dove guardare |

#### ✅ Fatto il 2026-08-31 — e una conseguenza che il piano non aveva scritto

Le tre righe sopra sono scritte (`20260831-17`, `-18`, `-19`). La forma è quella
decisa: due funzioni — `fn_ba_ha_storia_emittente` (`EXISTS`, esce al primo
documento) e `fn_get_storia_emittente_ba` (una riga per famiglia, solo dove il
conteggio è > 0) — più il guard sul catalogo e la frase composta dalle
`descrizione` del catalogo.

⚠️ **Il perimetro non si è solo allargato: ne è uscita la fattura in BOZZA.** Il
conteggio vecchio era un `count(*)` **senza condizione sul numero**, quindi una
fattura in bozza bloccava; «solo i numerati» la lascia passare. È coerente con la
decisione — *una bozza non ha congelato niente* — ed è il caso per cui la finestra
di correzione esiste. ⛔ **Ma va detto per intero:** una bozza porta già
`emittente_soggetto_ruolo_id`, e su `vendite.fatture` **non** c'è un
`trgfn_*_guard_emittente_ba` che glielo ricontrolli col BA — quindi spostare il BA
la lascerebbe sull'emittente vecchio. Resta una bozza: si cancella e si rifà, e
presidiarla costerebbe la finestra di correzione **per intero**.

⚠️ **La firma dell'errore cambia, e il BE lo vede.** `E_BA_EMITTENTE_CON_STORIA`
passa da **quattro** segnaposto a **tre** (cliente, emittente, elenco), e nel
`dettaglio` del 409 spariscono `n_fatture` / `n_commesse` in favore di `storia`
(un array di `{famiglia, descrizione, n}`) e `n_documenti`. ⭐ Il `reason_key`
**non** cambia: la traduzione del frontend resta agganciata dov'era.

⚠️ **Il restringimento è reale e va detto prima**: l'ordine si numera
all'`INSERT`, quindi «ordine numerato» = «ordine», e **il primo ordine chiude la
finestra di correzione** del suo BA. È coerente — quel numero viene dal registro
di quell'emittente — ma la finestra si stringe parecchio. ⭐ È il prezzo della
regola generale, ed è il verso giusto: la finestra esiste per correggere un
cliente *nato* sbagliato, cioè prima che produca documenti.

#### ⭐⭐ Il presidio sta nel CATALOGO, non in un elenco — decisione di Tid, 2026-08-30

*(Superata la versione precedente di questo paragrafo, che diceva «la regola si
scrive in cinque `SELECT`, e serve un pgTAP che verifichi che l'elenco copra tutte
le famiglie». Era il rimedio sbagliato: presidiare una copia invece di non farla.)*

> **Ogni famiglia che ha un registro è per costruzione per-emittente, quindi è
> candidata a bloccare lo spostamento del BA.** Il conteggio non si scrive: **si
> deriva dal catalogo delle famiglie.**

Ne discende una tabellina di vocabolario, e `famiglia_documento` diventa una **FK**
invece di un `CHECK`:

```
vendite.famiglie_documento
  codice_interno            -- FATTURA | DDT | ORDINE | COMMESSA | RESO
  schema_tabella, nome_tabella
  colonna_numero            -- 'numero' … e per la commessa 'codice'
  colonna_billing_account   -- dove sta il BA su quella tabella
  attivo
```

⭐ **È la stessa forma che `config.sistema_codici` usa già** per dire dove vive un
codice (`schema_tabella` / `nome_tabella` / `nome_colonna`): non si inventa un
meccanismo, si riusa quello che il progetto ha già.

⭐ **E il presidio sparisce perché sparisce la divergenza.** Con il conteggio
derivato dal catalogo, il **sesto** documento entra nella regola **il giorno in
cui si registra la sua famiglia** — non c'è nessun elenco parallelo che possa
restare indietro, quindi non c'è niente da tenere allineato. È lo stesso principio
della primitiva di pulizia che scopre le figlie da `pg_constraint`.

**Le cautele, dichiarate:**

* ⚠️ **SQL dinamico dentro un guard.** Gli identificatori vengono dal catalogo:
  vanno passati con `%I`, e la funzione resta `SECURITY DEFINER`. ⛔ Una riga di
  catalogo sbagliata romperebbe il guard **a runtime** invece che al deploy ⇒
  serve un guard sul catalogo stesso, che verifichi su `pg_attribute` che schema,
  tabella e colonne esistano davvero. ⭐ Anche questo è già scritto altrove:
  `script.trgfn_config_sistema_codici_sync_gen_codice` fa esattamente questo
  controllo;
* ⭐ **`EXISTS` sul percorso felice, `count` solo nel ramo d'errore.** Al guard
  serve sapere **se** c'è storia, non quanta; il conteggio serve solo al messaggio,
  cioè quando si è già deciso di rifiutare. È lo stesso schema di
  `fn_get_next_progressivo`, dove il bersaglio si compone solo dopo il rifiuto.
  Senza, si passa da 2 `count` a 5-6 su **ogni** movimento;
* ⚠️ **Il BA è nullable su tre delle cinque tabelle** — verificato: `NOT NULL` su
  `fatture` e `commesse`, **nullable** su `ddt`, `ordini` e `resi`. Il predicato
  derivato deve reggere il `NULL` senza contarlo;
* ⚠️ **La colonna del numero non si chiama uguale ovunque**: `numero` per quattro,
  **`codice`** per la commessa. È esattamente il motivo per cui va dichiarata nel
  catalogo e non dedotta.

### 3.8 La guida

| # | Cosa |
| --- | --- |
| **C2-14** | In `docs/it/dbzero/config/manual/sistema_codici.md`: **quando spostare un numeratore sui registri** — il criterio (*il periodo il generatore se lo calcola da sé; emittente, serie e un momento diverso dall'`INSERT` arrivano dalla riga*), i tre campanelli in parole d'uso, e la **checklist del trasloco** |
| **C2-15** | Il **debito sul nome** dichiarato nelle quattro sedi: `COMMENT` della tabella, `COMMENT` di `famiglia_documento`, doc manuale, brief |

#### ✅ Fatto il 2026-08-31

**C2-14** — la guida vive in `docs/it/dbzero/config/manual/sistema_codici.md`, rev
2026-08-31: il criterio in una frase, **tre campanelli** (numerazione per azienda,
reset a Capodanno, numero che non esce all'inserimento) più il quarto sulla serie,
il segnale che dice che si sta sbagliando strada, e la **checklist del trasloco**
in sette passi con la `UNIQUE` al secondo posto.

**C2-15 — il debito sul nome, e questa è la quarta sede.**

> ⛔ **La tabella si chiama `registri_fatturazione` e dal 2026-08-31 numera anche
> DDT, ordini, commesse e resi. Il nome NON si cambia in questo cantiere.**

Rinominarla significa rinominare `registri_fatturazione_progressivi`, i trigger,
le funzioni che la interrogano, le viste, i vincoli e le colonne `registro_id`
sparse su cinque tabelle di documento. ⭐ È un cantiere che **non cambia nessun
comportamento** — cioè esattamente quello che non si infila dentro uno che ne
cambia molti, dove un errore di rename si confonderebbe con un errore di trasloco.

⚠️ **La regola di lettura che ne discende**: chi incontra quel nome non deve
dedurne «fattura». La specie si chiede a `famiglia_documento`, e
`fn_get_registro_documento` **rifiuta** la famiglia `FATTURA`, che ha una strada
sua (tipo documento + natura).

Le altre tre sedi: `COMMENT` della tabella (`20260831-21`), `COMMENT` di
`famiglia_documento` (`20260830-15`), doc manuale
`dbzero/vendite/manual/registri_fatturazione.md` rev 2026-08-31.

⚠️ **Due imprecisioni del `20260830-15`, corrette nel `20260831-21`** perché quel
changeSet è applicato e non si riscrive: (a) sosteneva che *«la descrizione della
tabella dice già registri/serie di NUMERAZIONE, era il nome dell'oggetto a essere
rimasto indietro»* — mezza verità, perché diceva anche *«per fatture di vendita»*,
quindi non era solo il nome; (b) rimandava a un **§12.5-bis** di questo brief che
**non esiste**: la sede è questa, il §3.8.

---

## 4. L'ordine, e cosa non entra

**Ordine obbligato:** C1 tutto → C2-0 (il catalogo) → C2-1/2/3 (il modello) → C2-4/5 (la risoluzione) → C2-12 (i
dati) → C2-6/7 (il motore) → C2-8..11 (i documenti, uno alla volta) → C2-13 →
**C2-16/17/18** (la storia del cambio emittente, §3.7) → i presidi → la guida.

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
4. ✅ **RISOLTO il 2026-08-31 — la sigla ha una forma**: `^[A-Z0-9]{2,10}$`,
   vincolo `chk_emittenti_fiscali_codice_forma` (`20260831-22`) più il guard che
   dà la frase (`20260831-23`, `E_EMITTENTE_CODICE_FORMA_NON_VALIDA`).
   ⭐ **Il pregresso si è bonificato**, non si è lasciato fuori: Tid ha deciso il
   2026-08-31 che le sigle esistenti si possono correggere, quindi il vincolo è
   **validato** e non `NOT VALID`. Le due righe misurate — `EMI-TEST` →
   `EMITEST`, `PGTAP-EF-20260126172242554` → `PGTAPEF202` — sono state corrette
   dalla stessa trasformazione, scritta come **regola** e non come due `UPDATE`
   puntuali (il DB di sviluppo non è ricostruito da zero: altrove le righe
   storte saranno altre).
   ⚠️ **Bonifica e vincolo nello stesso changeSet**, e non per comodità:
   `00_schema` gira **prima** di `80_data`, quindi una bonifica messa fra i dati
   arriverebbe *dopo* il vincolo — che fallirebbe sul pregresso, cioè sul caso
   che la bonifica esiste per togliere.
   ⭐ **Il codice è immutabile e si è passati dalla porta**: il bypass
   `zeroerp.allow_lock_columns_override` che `script.trgfn_lock_columns`
   prevede, `LOCAL` e rimesso a `off` in coda — nessun lock smontato.
   ⭐ **Il minuscolo si alza, il trattino si rifiuta**: `acme` → `ACME` (forma
   canonica, ed è la stessa trasformazione della bonifica), mentre `AC-ME` non
   diventa `ACME` da solo — togliere caratteri a un identificatore appena
   scritto è una cosa che chi lo scrive deve sapere.
   ⚠️ **Ricaduta dichiarata**: le commesse già create tengono la sigla vecchia
   nella stringa (⛔ nessuna rinumerazione del pregresso). Non si rompe niente —
   l'unicità è sulla stringa intera — ma la discontinuità è visibile.
   ⚠️ **Una fixture pgTAP riparata**: `test-emittenti-fiscali.sql` generava
   `PGTAP-EF-<ts>`, che il vincolo non ammette più. Le altre tre che creano
   emittenti erano già conformi (`PGTAPGRE`, `PGTAP2EF1`) — verificate **prima**
   di scrivere il vincolo, non dopo.
5. ⚠️ **`ordine` a `usa_sequenza = f`** può accendere il campo numero in una
   maschera che usa `useCodiceField`. Da verificare prima di applicare.
6. ⭐⭐ **Il trasloco tocca la definizione di «storia» del cambio emittente del BA.**
   ✅ **Deciso e portato nel piano al §3.7** — qui resta il ragionamento.
   `anagrafiche.fn_get_storia_emittente_ba` conta **fatture e commesse** e
   dichiara nel proprio corpo perché **ordini e DDT non si contano**: *«il loro
   emittente ha un guard che lo ricontrolla col BA a ogni scrittura, quindi non è
   una copia stantia»*.
   ⛔ **Dopo il trasloco quell'argomento si indebolisce proprio per i documenti
   numerati**: un DDT o un ordine numerato porta un `registro_id` **congelato**, e
   un registro appartiene a **un** emittente (§2). Un numero non si riscrive mai —
   è la definizione stessa di ciò che quella funzione chiama «storia».
   ✅ **Deciso da Tid il 2026-08-30: sì — il DDT numerato blocca lo spostamento del
   BA**, come una fattura. ⚠️ **Solo il numerato**: un DDT in bozza non ha congelato
   niente.
   ⚠️ **Sull'ordine la stessa regola pesa di più**, perché l'ordine si numera
   all'`INSERT`: «ordine numerato» = «ordine», quindi il primo ordine chiude la
   finestra di correzione del suo BA. È coerente (quel numero viene dal registro di
   quell'emittente), ma è un restringimento vero e va detto prima.
   ✅ **DECISO e FATTO**: gli ordini si contano insieme ai DDT — anzi il conteggio
   non elenca più niente, si **deriva** dal catalogo delle famiglie (§3.7,
   changeSet `20260831-17`). *(Superata la riga che stava qui: «resta da decidere
   se contare gli ordini insieme ai DDT».)* Se non ci fossero entrati, il guard
   avrebbe continuato ad ammettere uno spostamento di BA che lascia orfano un
   documento numerato — lo stesso difetto muto che quel guard esiste per impedire,
   in un punto nuovo.
   ⚠️ E il conteggio va fatto **`SECURITY DEFINER`** come l'esistente: sotto RLS la
   storia di un altro emittente è invisibile, e il guard concluderebbe «non c'è
   storia» proprio nel caso da bloccare.


---

## 6. I presidi — scritti il 2026-08-31

| # | Presidio | Dove | Stato |
| --- | --- | --- | --- |
| **P-1** | ⭐ Due emittenti, stesso anno: due numeri «1» che convivono, e i contatori proseguono indipendenti | `vendite/test-registri-motore-trasloco-v1.sql` (2, 3) | ✅ |
| **P-3** | ⭐ Il reset di Capodanno, **seminando** il contatore dell'anno prima a 99 — e l'anno prima resta intatto | idem (4, 5) | ✅ |
| **P-7** | Il lettore tace, l'**involucro** grida; e rifiuta `FATTURA` | idem (6, 7, 8) | ✅ |
| **P-6** | ⭐ I due gemelli: DDT **in bozza** non blocca, DDT **numerato** sì | `anagrafiche/test-ba-storia-solo-numerati-v1.sql` (2, 5) | ✅ |
| **P-5** | ⭐⭐ L'anno segue la **data del documento**, non l'`INSERT` — DDT nato a dicembre 2101, emesso con data gennaio 2102 | `vendite/test-documenti-numerazione-trasloco-v1.sql` (2) | ✅ |
| **P-2** | Registro giusto, anno, forma della stringa | idem — **DDT** (1,2,3), **ordini** (4), **commessa** (5,6) | ⚠️ **parziale** |
| **P-4** | La commessa che **non nasce** senza registro — `throws_ok` con SQLSTATE | idem (7) | ✅ |

**Totale: 3 file nuovi, 24 asserzioni — tutti VERDI il 2026-08-31** (eseguiti da
Tid), più i 3 file già scritti in corso d'opera (C1 plan 6, catalogo plan 7,
forma sigla plan 8).

#### ⚠️ Quattro difetti che i test hanno trovato, e nessuno era nel codice DB

Vale la pena registrarli: sono tutti nelle **fixture**, e tutti della stessa
specie — dedurre invece di leggere.

1. ⛔ **`anagrafiche.fn_get_emittente_fiscale_id` restituisce il
   `soggetto_ruolo_id`, non la PK di `emittenti_fiscali`** (il nome dice
   «fiscale_id»). Agganciarla a `ef.id` non solleva niente: fa **zero righe**, e
   `SELECT * INTO` azzera ogni campo — il test muore molto più avanti su un
   `NOT NULL` che nomina una colonna estranea. Ci si è cascati **due volte**.
2. ⚠️ **`vendite.ordini.stato_doc_ordine_id` è al singolare**, mentre il
   catalogo è `config.stati_doc_ordini` al plurale — e sul DDT invece
   coincidono. L'analogia non regge.
3. ⚠️ **Il guard «figli prima, padre poi»**: un registro non si spegne finché ha
   una riga attiva in `registri_fatturazione_progressivi`. Non è un intralcio da
   aggirare, è il presidio che impedisce di ritirare un sezionale con sotto un
   contatore vivo.
4. ⛔ **`uq_registri_fatturazione_famiglia_emittente_utility` NON filtra su
   `attivo`**: un registro **spento occupa ancora lo slot**. Ne discende un
   fatto di modello che non era scritto da nessuna parte — **«spegni e rifai»
   non è una strada per un registro**: per la stessa terna si riattiva quello
   che c'è. ⭐ Ed è giusto così: se lo slot si liberasse, resterebbero due
   registri storici della stessa famiglia e nessuno saprebbe quale ha numerato
   cosa. 📌 **Da valutare**: dichiararlo nel `COMMENT` dell'indice.

⭐ **La lezione di metodo**: ogni fixture vuole la sua asserzione «la fixture non
mente», e deve **nominare** il campo mancante — un `AND` monolitico dice *che*
manca qualcosa, non *cosa*, e lascia a indovinare. La forma che funziona è un
`LATERAL (VALUES ('campo', t.campo IS NULL), …)` con `string_agg` dei soli
mancanti confrontato con la stringa vuota: il diff di pgTAP stampa i nomi.

### ✅ Il presidio DERIVATO — scritto il 2026-08-31

`vendite/test-identita-documenti-derivata-v1.sql` (plan 5, **verde** il
2026-08-31). ⭐ **Non elenca le tabelle: le legge da `vendite.famiglie_documento`**
— quindi la sesta famiglia entra nel presidio il giorno in cui si registra, e
nessuno deve ricordarsi di aggiungerla.

⭐⭐ **La biforcazione è derivata, non scritta.** L'identità di un documento deve
distinguere due emittenti, e ci sono due modi legittimi: la chiave porta
`registro_id` (fatture, DDT, ordini, resi), oppure la tabella quella colonna non
ce l'ha e l'identità è la **stringa nuda** che porta la sigla dentro di sé
(commessa). Il test sceglie il ramo guardando `pg_attribute`.

| # | Cosa presidia | Tipo |
| --- | --- | --- |
| 1 | Il catalogo non è vuoto e ogni riga punta a una tabella vera | ⭐ gemello anti-muto |
| 2 | L'identità di ogni famiglia **distingue l'emittente** | ⭐⭐ strutturale |
| 3 | Dove esiste `anno`, l'unicità lo contiene | ⭐ strutturale |
| 4 | Chi ha il registro porta **anche l'anno** | ⚠️ dati (complemento) |
| 5 | Niente `serie_default` dove la `serie` non ha casa | ⛔ derivato |

⭐ **I test 2 e 3 sono il presidio vero**: guardano la **struttura**, quindi
valgono a database vuoto, valgono in CI e diventano rossi *prima* che esista il
primo documento sbagliato. Il 4 guarda i dati ed è solo un complemento — da solo
sarebbe il classico «test che conta i cattivi e diventa muto» su tabella vuota.

⭐ **E il 5 chiude la lacuna dei RESI** dichiarata più sopra, senza pagare la
fixture: il vincolo *«un registro `RESO` non deve avere `serie_default`»* è una
regola di **struttura**, e scritta così non nomina i resi — dice «le famiglie la
cui tabella non ha la colonna `serie`», quindi vale anche per la prossima.

#### ⚠️ Due correzioni fatte al primo lancio, e nessuna era un difetto del DB

1. ⛔ **Un test l'avevo inventato.** Pretendevo che «dove c'è la colonna `serie`,
   l'unicità la contiene» — e la fattura lo faceva fallire. Ma la serie *effettiva*
   è `COALESCE(documento.serie, registro.serie_default, '')`: la colonna è un
   **override del registro**, non una dimensione autonoma. Con `registro_id` già in
   chiave, metterci anche la serie è una scelta per-documento, e la chiave della
   fattura risulta più **stretta**, non più larga. Test **rimosso**, con la ragione
   scritta nel file perché nessuno lo riscriva.
2. ⚠️ **Un test segnalava il pregresso**, cioè una decisione: *nessuna
   rinumerazione, per nessun numeratore*. I documenti numerati prima del trasloco
   non hanno registro né anno e non li avranno mai — quel test sarebbe stato
   **rosso per sempre**, e un presidio che nasce rosso non lo guarda più nessuno.
   Riformulato sulla regola vera: **chi è passato dal motore nuovo porta registro e
   anno insieme**; chi il registro non ce l'ha è storia, e si riconosce da lì.

⚠️ **Perché non una colonna generata** (idea valutata il 2026-08-31 e scartata):
le tabelle **non hanno le stesse colonne** — resi non ha `serie`, commesse ha
solo `codice` — quindi una colonna «uniforme» avrebbe nascosto **sette
espressioni diverse sotto un nome comune**, dando l'impressione di una regola
sola dove ce ne sono sette. In più `ADD COLUMN … GENERATED … STORED` riscrive
l'intera tabella, e ogni documento nuovo avrebbe dovuto *ricordarsi* la colonna
— cioè un elenco parallelo, esattamente ciò che il catalogo esiste per evitare.

### ✅ La lacuna dei RESI — chiusa il 2026-08-31

*(Superato il paragrafo che stava qui e dichiarava i resi scoperti.)*

`test-documenti-numerazione-trasloco-v1.sql` passa da **plan 8 a plan 10**: il
reso si crea sul DDT che la fixture costruisce già, si conferma con la **madre**
`vendite.fn_conferma_reso` — non con un `UPDATE` dello stato, così si prova anche
che il trigger sia montato — e si verifica che ne escano numero, registro `RESO`
del proprio emittente, anno dalla data e forma dal catalogo.

⛔ **Spiegando la lacuna è emerso che era peggio del previsto, e vale la pena
scriverlo.** Non era «manca un test end-to-end»: il buco era coperto **due volte
male**.

* i presidi **strutturali** guardano la chiave, non il comportamento;
* il presidio sui **dati** chiede *«chi ha il registro ha anche l'anno»* — e un
  reso nato **senza** registro, cioè esattamente il sintomo di un generatore
  rotto, cade nel ramo del **pregresso** e passa.

⇒ Se `trgfn_resi_gen_numero` avesse smesso di funzionare, **nessun test lo
avrebbe detto**. E si sarebbe rotto in silenzio: il generatore esce in testa se lo
stato non è `CONFERMATO`, quindi basta che quel codice interno cambi o che il
trigger si smonti in un rebuild perché il reso resti **senza numero**, senza
errori e senza rifiuti.

⭐ **La lezione, oltre il caso:** quando un test sui dati ha un ramo di esclusione
— qui il pregresso — quel ramo è anche il **nascondiglio** del difetto che il test
cerca. Il rimedio non è togliere l'esclusione (il pregresso è una decisione), è
provare il caso **dal lato positivo**: non «non ci sono resi rotti», ma «un reso
confermato adesso riceve il numero».

### ⚠️ Quello che i pgTAP non potranno provare

Che il contatore stia **sotto il lock**, cioè che due sessioni concorrenti non
prendano lo stesso numero: pgTAP è mono-sessione. Si presidia in **review** sul
changeSet, come già dichiarato al §3.6.
