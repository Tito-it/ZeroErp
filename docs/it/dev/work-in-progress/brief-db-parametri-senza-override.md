# Brief DB — I parametri che non ammettono override

## ⏭️ Chi riparte — aggiornato al 2026-10-24

**Riparte: Tid**, col via allo sviluppo. Le decisioni sono tutte prese (D-1, D-2, D-2-bis il
2026-10-24, §4).

| # | Chi | Che cosa | Dove | Aspetta |
| --- | --- | --- | --- | --- |
| 1 | ✅ team DB | Ricognizione e proposta | §1-§3 | — |
| 2 | ✅ **Tid** | D-1 (la colonna) e D-2 (`login_*`, `tx_id_bypass_enabled`, `attivita_fatturabili_require_commessa` senza override), 2026-10-24 | §4 | 1 |
| 2-bis | ✅ **Tid** | D-2-bis: `dati_societari_default_*` con override per emittente (2026-10-24) | §4 | 1 |
| 3 | team DB | ChangeSet, CSV, pgTAP, guida | §5 | il via |
| 4 | **Tid** | Apply | — | 3 |
| 5 | BE / FE | La lista e il form degli override rispettano la famiglia | §5.2 | 4 |
| 6 | **Tid** | Archiviazione in `work-done/` | — | 5 |

Decisioni aperte di Tid: **nessuna**; manca il via allo sviluppo. Lavoro da committare: questo brief e la guida
[Configurazione e gestione parametri](../../guide/configurazione-e-gestione-parametri.md),
riscritta il 2026-10-24 sullo stato attuale.

**Brief vicini verificati (2026-10-24):** nessuno sul tema. Nominano le stesse tabelle
[valutazione-modello-di-dominio-db](valutazione-modello-di-dominio-db.md) (i timestamp delle due
tabelle, V-1, già chiuso) e
[analisi-pratiche-valutazione-stato](analisi-pratiche-valutazione-stato.md) (gli override come
modello per le definizioni di workflow): parlano d'altro. Il tema nasce dalla verifica della guida
richiesta da Tid il 2026-10-24.

---

## 1. Il problema

`config.parameters` contiene **due famiglie** di parametri, e il modello ne conosce una sola.

* **Con override**: il valore può cambiare per utente, categoria cliente, gruppo, emittente,
  sessione o funzione. Si legge con `script.fn_get_parameter_full`, che applica la cascata.
* **Senza override**: il valore deve essere **uguale per tutti**, perché un override darebbe allo
  stesso documento valori diversi a seconda di chi lo genera. Lo legge dal default la funzione
  che possiede la regola, e la descrizione del parametro lo dichiara: «NON si legge via
  `script.fn_get_parameter_full` e non si sovrascrive in `config.parameter_overrides`».

La seconda famiglia esiste **solo come testo** nella descrizione. Il database non lo sa, e quindi:

1. **un override su un parametro senza override viene accettato e poi ignorato in silenzio.** Chi
   lo scrive crede di aver cambiato il fuso orario per un'azienda, o la soglia di ripresa per un
   utente; il lettore guarda il default e l'override non agisce. Nessun errore, nessun avviso;
2. **la lista della UI admin mente.** `script.fn_list_parameters_for_user` restituisce **tutti** i
   parametri, e per ognuno calcola `resolved_value` con `fn_get_parameter_full`. Su un parametro
   senza override con un override scritto, la lista mostra come «valore effettivo» l'override,
   cioè un valore che nessuno usa;
3. **la famiglia di un parametro si scopre solo leggendo la funzione che lo legge.** Cinque
   parametri letti dal default non lo dichiarano nemmeno nella descrizione (§2.2).

Il caso esiste sul modello: la tabella degli override ammette qualunque `parameter_id`, e la
lista ne mostra tutti. Che oggi su dbdev non ci sia nessun override su questi parametri è un
fatto datato, non un argomento: il difetto è nella porta aperta.

---

## 2. Ricognizione (struttura, 2026-10-24)

### 2.1 Chi legge `config.parameters` senza la cascata

Funzioni che leggono `config.parameters` direttamente, a parte `fn_get_parameter_full`
(censimento su `pg_get_functiondef`, dbdev):

| Funzione | Parametri | Dichiarato «senza override» nella descrizione? |
| --- | --- | --- |
| `script.fn_fuso_operativo` | `SYSTEM_FUSO_ORARIO` | ✅ sì |
| `dbops.fn_idempotency_prenota` | `SYSTEM_IDEMPOTENZA_IN_CORSO_SECONDI` | ✅ sì |
| `vendite.fn_get_limite_emissione_default` | `VENDITE_LIMITE_EMISSIONE_IMMEDIATA_GIORNI`, `VENDITE_LIMITE_EMISSIONE_DIFFERITA_GIORNO_MESE` | ✅ sì |
| `script.fn_login_parametri` | `login_tetto_credenziale`, `login_attesa_base_secondi`, `login_attesa_max_secondi`, `login_blocco_minuti`, `login_max_tentativi_falliti` | ❌ no |
| `dbops.trgfn_tx_id_managed` | `tx_id_bypass_enabled` | ❌ no |
| `anagrafiche.fn_scrivi_dati_societari` | `dati_societari_default_liquidazione`, `dati_societari_default_socio_unico` | ❌ no |
| `vendite.trgfn_attivita_fatturabili_guard_commessa` | `attivita_fatturabili_require_commessa` | ❌ no |
| `config.trgfn_parameter_overrides_fk_surrogate_dispatch` | — (cerca il codice del parametro padre) | non è una lettura di valore |
| `script.fn_list_parameters_for_user` | — (tutti: è la lista) | non è una lettura di valore |

### 2.2 Che cosa dice il modello sui cinque non dichiarati

Leggono il default e ignorano gli override, come i dichiarati, ma nessuno lo ha scritto. Per
ognuno la domanda è di modello: **il valore può dipendere da chi lavora?**

* `login_*`: la protezione del login vale per la **credenziale**, da qualunque provenienza; un
  override per utente o per sessione renderebbe il tetto diverso per chi attacca. A mio avviso
  **senza override**.
* `tx_id_bypass_enabled`: un interruttore di sistema del trigger `tx_id`. **Senza override.**
* `attivita_fatturabili_require_commessa`: una regola di coerenza dei dati di fatturazione.
  **Senza override.**
* `dati_societari_default_*`: i default proposti quando si scrivono i dati societari di un
  soggetto. Qui un override per **emittente** avrebbe senso (ogni azienda propone i suoi
  default), e allora il difetto sarebbe nel lettore, non nel parametro. **Da decidere** (D-2).

### 2.3 Altri debiti trovati nella stessa lettura

* La descrizione di `DEFAULT_TIPO_SOGGETTO_DETTAGLIO_CL`/`_FO` cita una cascata vecchia
  («user → group → emittente → default», senza la categoria) e un guard ritirato
  (`trgfn_parameters_guard_default_tipo_soggetto_dettaglio`, sostituito dal framework
  FK-surrogata in `20260502-07`). Si corregge nel CSV, nello stesso giro.

---

## 3. Proposta

**La famiglia diventa una colonna del catalogo**, e il database la fa rispettare.

1. `config.parameters.ammette_override boolean NOT NULL`, seminata nel CSV di ogni parametro.
   Senza `DEFAULT` nel modello: un parametro nuovo dichiara la sua famiglia, come oggi dichiara
   il suo valore (si chiede a Tid se per il backfill basta un `DEFAULT` temporaneo, tolto nello
   stesso giro).
2. **Un guard su `config.parameter_overrides`** (BEFORE INSERT/UPDATE OF `parameter_id`)
   rifiuta un override su un parametro con `ammette_override = false`, con un codice nuovo
   `E_PARAMETRO_SENZA_OVERRIDE` (DATO_ERRATO, 400): «Questo parametro vale per tutti e non si
   personalizza», con la soluzione «cambia il valore di default».
3. ⚠️ Il guard vale anche **nel verso opposto**: un parametro che passa da «con» a «senza
   override» mentre ha override vivi lascia override che nessuno legge. Il passaggio si rifiuta
   finché ne esistono (guard su `config.parameters`, UPDATE OF `ammette_override`).
4. `script.fn_list_parameters_for_user` restituisce `ammette_override` (colonna **in coda** al
   `RETURNS TABLE`: DROP + CREATE; se il BE legge le colonne per posizione o per nome si
   verifica nel censimento di §5.1, non si presume); per i parametri senza
   override le colonne dei livelli restano NULL e `resolved_value` è il default. Il FE non offre
   il form dell'override su quelle righe.
5. Le descrizioni dei parametri non devono più ripetere la regola: la colonna la dice. Il motivo
   (perché questo parametro vale per tutti) resta nella descrizione.

**Alternativa più leggera, che non propongo:** un pgTAP che presidia «nessun override sui
parametri dichiarati senza override», con l'elenco scritto nel test. Trova il difetto dopo, non
lo impedisce; e l'elenco nel test è una seconda copia della famiglia, che diverge dalla prima.

Nessun lettore cambia: chi legge il default continua a leggerlo, chi usa la cascata continua a
usarla. `fn_get_parameter_full` su un parametro senza override restituisce il default, perché
dal punto 2 in poi non può più esistere un override da trovare.

---

## 4. Decisioni di Tid

* ✅ **D-1 — La forma. Decisa da Tid il 2026-10-24: la colonna.** `ammette_override` sul
  catalogo, guard nei due versi, la lista che espone la colonna (§3). Il solo presidio pgTAP è
  scartato.
* ✅ **D-2 — La famiglia di ogni parametro. Decisa da Tid il 2026-10-24, come proposto in
  §2.2:** `login_*`, `tx_id_bypass_enabled` e `attivita_fatturabili_require_commessa` **senza
  override**, insieme ai quattro già dichiarati (`SYSTEM_FUSO_ORARIO`,
  `SYSTEM_IDEMPOTENZA_IN_CORSO_SECONDI`, i due `VENDITE_LIMITE_EMISSIONE_*`). Tutti gli altri
  parametri oggi con override restano tali.
* ✅ **D-2-bis — `dati_societari_default_*`. Decisa da Tid il 2026-10-24: con override per
  emittente.** Sono valori *proposti* a chi compila i dati societari di un soggetto, non regole
  che devono valere uguali per tutti: ogni azienda propone i suoi. Il difetto è quindi nel
  lettore: nello stesso giro `anagrafiche.fn_scrivi_dati_societari` legge i due parametri con
  `script.fn_get_parameter_full`, passando l'emittente del contesto. ⚠️ Da verificare scrivendo:
  da dove la funzione prende l'emittente (parametro, contesto di sessione o soggetto), e che i
  due parametri non siano letti anche dal BE.

---

## 5. Il giro, dopo il via

### 5.1 DB

* `00_schema/config`: la colonna, il backfill dal CSV, il NOT NULL.
* `20_code/config`: i due guard; `fn_list_parameters_for_user` con la colonna in coda.
* `20_code/anagrafiche`: `fn_scrivi_dati_societari` legge `dati_societari_default_*` con la
  cascata e l'emittente (D-2-bis); pgTAP con un override di emittente costruito.
* `80_data`: `ammette_override` in ogni CSV dei parametri; il codice nuovo in `codici_errore.csv`
  e `messaggi_errore.csv` (it/en); le descrizioni di `DEFAULT_TIPO_SOGGETTO_DETTAGLIO_*` (§2.3).
* pgTAP: override rifiutato su un parametro senza override (costruito con un parametro di
  prova); passaggio «con → senza» rifiutato con un override vivo, ammesso senza; la lista
  restituisce la colonna e il default come valore risolto.
* Censimento prima di scrivere: i pgTAP che inseriscono override, i chiamanti di
  `fn_list_parameters_for_user` (BE).
* Guida: la sezione «Due famiglie di parametri tabellari» passa dalla regola scritta alla
  colonna, e l'avviso «il database non impedisce…» si toglie.

### 5.2 Ricaduta BE / FE (da scrivere come richiesta, dopo l'apply)

* La lista dei parametri della UI admin legge `ammette_override` e non offre l'override dove è
  `false`.
* Il nuovo codice arriva dal DB come ogni errore di dominio; rigenerare policy e ripiego dei
  messaggi.
