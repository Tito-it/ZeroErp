# Brief DB — Le date di validità parlano la lingua del dominio

> **Da leggere per primo: §3, la forma (un'automazione) e §6, cosa si ritira.**
> Origine: [brief-db-fixture-che-costruiscono-giro-2.md](brief-db-fixture-che-costruiscono-giro-2.md)
> §11, dove `anagrafiche/test-risorse-umane` t.6 ha fatto vedere per la prima
> volta chi rifiuta davvero le date invertite. Tid, 2026-09-23: *«farei il
> controllo per le date come hai suggerito»* — il guard di dominio sì;
> sull'automazione *«potremo pensarci … pensiamoci»*.
>
> ⏸️ **Stato 2026-09-23: in riflessione.** Piano scritto, **nessun changeSet**.
> La forma di §3.2 (automazione) è la proposta, non una decisione: §8.

---

## 1. Il difetto, sul modello

Una riga con `valido_dal` e `valido_al` dichiara un periodo, e il periodo ha
una regola sola: **`valido_al` non precede `valido_dal`**. Il modello quella
regola la scrive in **tre modi diversi**, e a seconda della tabella l'operatore
che sbaglia le date legge tre cose diverse:

| Chi rifiuta | Che cosa legge l'operatore |
| --- | --- |
| un **guard di dominio** scritto dentro il guard della tabella | `E_DATA_AL_MINORE_DAL` — «Il valore della data al … è inferiore alla data dal …» |
| il **daterange** della colonna generata `validita`, calcolato **prima** dei `CHECK` | `22000` — «il limite inferiore dell'intervallo dev'essere minore o uguale del limite superiore» |
| un **`CHECK`** (dove `validita` non c'è) | `23514` — la violazione di un vincolo |

⛔ Il secondo caso è il più insidioso: la tabella ha anche il suo `CHECK` sulle
date, e sembra presidiata **da lui**. Non lo è: in **ogni** caso in cui il
`CHECK` fallirebbe (entrambe le date presenti e invertite) il `daterange`
solleva prima, e negli altri il `CHECK` passa. Il `CHECK` oggi non parla mai.

⚠️ **Il `CHECK` non è inutile, e resta** (§5). È la regola **dichiarata**,
leggibile nel catalogo e nella doc, e l'ultima difesa se un giorno
l'espressione di `validita` cambia o la colonna sparisce. Il difetto non è che
ci sia: è che l'operatore legga una frase tecnica.

---

## 2. Il censimento — lettura di struttura (2026-09-23, `zeroerp_ci`)

Tabelle con la coppia `valido_dal`/`valido_al` (`pg_attribute`, esclusi
`storico` e `pg_catalog`): **25**. Questa è una lettura del **progetto**
(colonne, vincoli, trigger), non un conteggio di righe: decide il perimetro.

| Forma | Tabelle | Chi parla oggi |
| --- | --- | --- |
| `validita` generata **+** `CHECK` **+** guard inline | `anagrafiche.billing_account` | il guard (i `BEFORE` girano prima della colonna generata) |
| `validita` generata **+** `CHECK` | `vendite.contratti`, `anagrafiche.risorse_umane`, `resellers_billing_account`, `soggetti_titoli_iva`, `tipi_ruolo_tipi_indirizzo`, `tipi_soggetto_dettaglio_tipi_indirizzo`, `utilities_tipi_ruolo`, `tipi_ruoli_nature_ammesse`, `user_override_aree`, `user_override_oggetti`, `user_override_azioni` | il `daterange` (`22000`) |
| `validita` generata, **nessun** `CHECK` | `catalogo.articoli_componenti`, `catalogo.articoli_uom_operativa`, `catalogo.unita_misura_conversioni`, `vendite.listini_versioni`, `vendite.promo_articoli`, `vendite.listini_righe_componenti`, `categorie_clienti_listini`, `documenti.template_documenti_versioni`, `documenti.template_asset` | il `daterange` (`22000`) |
| **niente** `validita`, `CHECK` **+** guard inline | `soggetti_conti_bancari`, `soggetti_ruoli_conti_bancari` | il guard |
| **niente** `validita`, solo `CHECK` | `forme_giuridiche_tipi_soggetto_dettaglio`, `identita_digitali` | il `CHECK` (`23514`) |

(Senza schema: `anagrafiche` o `config`, come da catalogo.)

⚠️ Il `CHECK` non ha sempre la stessa forma: dove `valido_dal` è nullable
porta anche `valido_dal IS NULL OR …`. Il guard deve avere la stessa
semantica: **si giudica solo quando entrambe le date ci sono**.

---

## 3. La forma — un building block montato da un'automazione

### 3.1 La funzione trigger

`script.trgfn_guard_date_validita()` — generica, senza argomenti: le colonne
si chiamano sempre `valido_dal` e `valido_al`.

* `IF NEW.valido_dal IS NOT NULL AND NEW.valido_al IS NOT NULL AND NEW.valido_al < NEW.valido_dal`
  → `script.fn_log_and_raise_error` con **`E_DATA_AL_MINORE_DAL`** (già
  registrato, classe `DATO_ERRATO`, già usato dalle tre copie);
* contesto: `'campo', 'valido_al'` (il frontend accende quel campo) e la
  tabella da `TG_TABLE_SCHEMA`/`TG_TABLE_NAME`; nella frase le **due date**,
  mai nomi di colonna (linee-guida-sql §5, i tre canali);
* `BEFORE INSERT OR UPDATE OF valido_dal, valido_al`, `FOR EACH ROW`: i
  `BEFORE` girano **prima** del calcolo delle colonne generate (linee-guida-sql
  §7b), quindi parla lui e non il `daterange`.

### 3.2 L'automazione — la regola nasce dalla presenza della coppia

Stesso modello del lock di `codice_interno` (linee-guida-sql §6b: *la sola
presenza della colonna provisiona il lock*): **la sola presenza di
`valido_dal` e `valido_al` monta il guard**. Una tabella nuova con un periodo
nasce presidiata senza che nessuno se ne ricordi — un elenco scritto a mano
invecchierebbe alla prima.

| Pezzo | Dove | Modello da ricalcare |
| --- | --- | --- |
| regola `DATE_VALIDITA` in `dbops.automation_rules_tbl` (`*all`/`*all`, `AUTO`, `name_template` `trg_{table}_a10_date_validita_ins_upd`, `existence_strategy` `BOTH`) | `80_data/sql/dbops/automation_rules_tbl.csv` | riga `LOCK_COLUMNS` |
| `dbops.fn_run_automations_date_validita(p_exec_mode, p_schemas, p_dry_run)` | `20_code/dbops` | `fn_run_automations_lock_columns`: stesso scope (`fn_resolve_scope`, `fn_table_in_scope`), `fn_col_exists` sulle due colonne, dry run, `fn_name_from_template` |
| la parte `DATE_VALIDITA` nel dispatcher `dbops.fn_run_automations` | `20_code/dbops` | le parti `LOCK_COLUMNS`/`ATTIVO` |
| il provisioning **subito**, non alle 21:00 | `90_end` | `20260923-03-provision-lock-iva-e-iva-stati`: un changeSet che chiama la funzione del modulo, così dopo il migrate i trigger ci sono già |
| il giro notturno | `85_pgagent` | il job `automations_lock_columns` (`20260905-08`) — da decidere se un job suo o una parte in più di uno esistente (§8) |

⚠️ **Le regole che valgono per ogni trigger generato**, e che si rompono solo
in CI (linee-guida-sql §11.5, e le schede in memoria):

* nessun `DROP`/`ALTER` incondizionato su questi trigger in `00_schema`/`20_code`:
  li crea l'automazione, su un database da zero ancora non ci sono;
* il nome pieno può superare i 63 caratteri ed essere troncato e hashato: il
  presidio li cerca per **funzione**, mai per nome;
* dopo un `migrate` manuale le automazioni non girano da sole: per questo c'è
  il changeSet di provisioning in `90_end`.

---

## 4. Il presidio — pgTAP

1. **Dinamico, per struttura**: per ogni tabella con la coppia di date esiste un
   trigger che esegue `script.trgfn_guard_date_validita`. Cercato per
   **funzione**, non per nome; e con la lista **letta da `pg_attribute`**, non
   scritta nel test — un presidio che elenca le tabelle è verde anche quando
   ne manca una nuova.
2. **Di comportamento**, su tre tabelle che coprono le tre forme di §2 (una con
   `validita` e `CHECK`, una con `validita` senza `CHECK`, una senza
   `validita`): date invertite → `P0001` con `E_DATA_AL_MINORE_DAL` e campo
   `valido_al`; stesso giorno → passa; una delle due date `NULL` → passa.
3. ⛔ **`anagrafiche/test-risorse-umane` t.6 va aggiornato nello stesso giro.**
   Oggi cattura solo `23514`/`22000` (è il test che ha trovato il difetto); col
   guard l'errore diventa `P0001`, e il suo `EXCEPTION` non lo prenderebbe: il
   file morirebbe. Diventa un `throws_like` sulla frase di `E_DATA_AL_MINORE_DAL`.
4. I pgTAP che oggi aspettano `23514` o `22000` sulle date vanno cercati **tutti**
   prima di scrivere (grep su `valido_al` + `23514`/`22000`/`chk_*_validita`).

---

## 5. Cosa NON entra, e perché

* ⛔ **I `CHECK` restano.** Sono la regola dichiarata e l'ultima difesa (§1).
  Il guard è ciò che parla; il `CHECK` è ciò che tiene se il guard manca.
* ⛔ **«`valido_al` richiede `valido_dal`»** (in `trgfn_billing_account_guard_normalize`)
  resta dov'è: è una regola **di quella tabella** (lì `valido_dal` è
  nullable), non della coppia.
* ⛔ **L'indice unico sul profilo SUPER_ADMIN**: decisione di Tid del
  2026-09-23, *si aspetta*.

---

## 6. Le copie da ritirare — nello STESSO giro

Regola del 2 (`AGENTS.md`): un building block accanto alle copie che
sostituisce è una terza versione della stessa regola. Tre funzioni fanno oggi
il controllo **inline** con `E_DATA_AL_MINORE_DAL`:

| Funzione | Che cosa si toglie | Che cosa resta |
| --- | --- | --- |
| `anagrafiche.trgfn_billing_account_guard_normalize` | il ramo `ELSIF NEW.valido_al < NEW.valido_dal` | il ramo «`valido_al` senza `valido_dal`» |
| `anagrafiche.trgfn_soggetti_conti_bancari_guard` | il blocco «coerenza validità» | il resto del guard |
| `anagrafiche.trgfn_soggetti_ruoli_conti_bancari_guard` | il blocco «coerenza date» | il resto del guard |

⚠️ Corpi **dalla doc auto-gen**, confrontati con il `prosrc` vivo prima di
scrivere: la doc di `trgfn_billing_account_guard_normalize` il 2026-09-23 **non
conteneva** il ramo, il corpo vivo sì — la doc è indietro, e ripartire da lei
farebbe regredire la funzione. Qui si parte dal vivo e si segna il debito.

⚠️ **L'ordine dei due rifiuti su `billing_account`**: il guard generato è
`trg_billing_account_a10_date_validita_ins_upd`, quello esistente
`trg_billing_account_ins_upd_guard_normalize`. Fra `BEFORE ROW` vince l'ordine
alfabetico: va verificato che, con date invertite, a parlare sia quello nuovo
(e che non cambi niente per gli altri rifiuti del guard esistente).

---

## 7. Debiti trovati per strada

* `linee-guida-sql.md` §7c punto 7 cita `script.trgfn_set_validita`, che **non
  esiste** (`pg_proc`, 2026-09-23). La convenzione che descrive (ultimo giorno
  incluso, `[]` canonicalizzato a `[)`) è vera, ma la sede che nomina no.
* Il messaggio di `E_DATA_AL_MINORE_DAL` ha un doppio spazio («inferiore  alla»)
  e nessuna `causa`/`soluzione`: con 25 tabelle che lo useranno, conviene
  completarlo dal CSV del catalogo (non con un `UPDATE`, linee-guida-sql §11.2).

---

## 8. Decisioni aperte per Tid

| # | Decisione | Raccomandata |
| - | --------- | ------------ |
| 1 | Automazione per presenza della coppia, o elenco esplicito delle 25 | ⏸️ **da pensare** (Tid, 23-09). Proposta: **automazione** — una tabella nuova con un periodo nascerebbe presidiata senza che nessuno se ne ricordi, come il lock di `codice_interno` |
| 2 | Codice: riusare `E_DATA_AL_MINORE_DAL` o conirne uno | **riusare**: è registrato, è `DATO_ERRATO`, lo usano già le tre copie, e la frase è quella giusta |
| 3 | Fase del trigger: `a10` o `a05` | **`a10`**: giudica il valore nuovo; `a05` è per i rifiuti che devono precedere gli altri (immutabilità), e qui non è il caso |
| 4 | Il giro notturno: job pgAgent suo o parte di un job esistente | **parte del job del lock** (`automations_lock_columns`): stessa natura (guard da struttura), un job in meno da sorvegliare |
| 5 | Completare `causa`/`soluzione` di `E_DATA_AL_MINORE_DAL` in questo giro | sì, dal CSV |

---

## 9. Ordine di lavoro

1. censimento dei pgTAP che asseriscono `23514`/`22000` sulle date (§4.4);
2. `20_code`: la funzione trigger, il modulo `fn_run_automations_date_validita`,
   il dispatcher;
3. `20_code`: le tre copie ritirate (corpo dal vivo, §6);
4. `80_data`: la regola in `automation_rules_tbl.csv` (+ il messaggio, se §8.5);
5. `90_end`: il provisioning immediato; `85_pgagent`: il giro notturno;
6. pgTAP: il presidio dinamico, quello di comportamento, e `test-risorse-umane` t.6;
7. prova con l'SQL estratto in transazione ritirata, da owner su `zeroerp_ci`
   (che è un database costruito da zero), con i presìdi trasversali
   (riferimenti morti, rubinetto);
8. doc: `linee-guida-sql` §7b/§7c (la regola e la sua sede), il catalogo BB lato
   DB, la guida sui messaggi se cambia il catalogo.

---
{% include-markdown "signature-core.md" %}
