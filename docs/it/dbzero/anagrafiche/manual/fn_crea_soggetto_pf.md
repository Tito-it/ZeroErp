## Documentazione Concettuale -- Funzione `anagrafiche.fn_crea_soggetto_pf()`

> **Vedi anche**
>
**Approfondimento tabelle:**
>
[anagrafiche.soggetti](/dbzero/anagrafiche/tabelle/soggetti)
> [anagrafiche.contatti](/dbzero/anagrafiche/tabelle/contatti)
> [config.tipi_soggetto_dettaglio](/dbzero/config/tabelle/tipi_soggetto_dettaglio)
>
**Approfondimento funzioni:**
>
[anagrafiche.fn_crea_operatore_v2](/dbzero/anagrafiche/funzioni/fn_crea_operatore_v2)
> [anagrafiche.fn_crea_risorsa_umana_v2](/dbzero/anagrafiche/funzioni/fn_crea_risorsa_umana_v2)
>
**Guide:**
>
[Soggetti e ruoli anagrafici](/guide/soggetti-e-ruoli-anagrafici)
> [Gestione degli indirizzi](/guide/gestione-degli-indirizzi)

---
### 🎯 Scopo Principale
(latest review 20-10-2026)
Building block atomico per la creazione di un soggetto **persona fisica** —
privato (PR) o ditta individuale (DI) — con contatto default obbligatorio e,
per la ditta individuale, i suoi **dati societari** nella stessa chiamata.

⭐ **Rev 20261020-03** (brief-db-dati-societari-in-creazione, E-1 (a)): la DI
ammette i dati societari (policy `OPTIONAL`) e il form li manda in creazione, ma
fino a questa revisione la porta non li riceveva e la sezione si perdeva in
silenzio. Ora i dieci campi stanno in coda, con gli stessi nomi di
[fn_crea_soggetto_pg](/dbzero/anagrafiche/manual/fn_crea_soggetto_pg), e quando
scriverli lo decide
[fn_scrivi_dati_societari_alla_nascita](/dbzero/anagrafiche/manual/fn_scrivi_dati_societari_alla_nascita),
lo stesso BB delle societa'. Soggetto e sezione nascono insieme o non nascono.

La natura di dettaglio la **sceglie il chiamante** (`p_tipo_soggetto_dettaglio_id`,
obbligatorio): fino al 2026-10-09 era `PR` cablato, e una ditta individuale
scelta nel form nasceva privato, senza partita IVA. Una natura che non e'
persona fisica si rifiuta: societa' ed enti passano da
[fn_crea_soggetto_pg](/dbzero/anagrafiche/manual/fn_crea_soggetto_pg).
`stato_id` si risolve da `config.stati.codice_iso2`.

**Il sesso non ha default.** Passa cosi' com'e': se la natura lo pretende e
manca, lo rifiuta il guard `trgfn_soggetti_guard_sesso_policy`
(`E_SESSO_OBBLIGATORIO`, campo `sesso`). Per il privato e' obbligatorio, per la
ditta individuale facoltativo (`config.tipi_soggetto_dettaglio.sesso_policy`).

**Non crea indirizzo:** il chiamante e' responsabile di creare l'indirizzo
RES se richiesto dalla matrice `config.tipi_soggetto_dettaglio_tipi_indirizzo`
(trigger DEFERRED verifica al COMMIT).

---

### Parametri

| Parametro          | Tipo                           | Obbligatorio | Default | Note                                             |
| ------------------ | ------------------------------ | :----------: | ------- | ------------------------------------------------ |
| `p_cognome`        | `soggetti.cognome%TYPE`        |      Si      | `NULL`  | Guard nel body.                                  |
| `p_nome`           | `soggetti.nome%TYPE`           |      Si      | `NULL`  | Guard nel body.                                  |
| `p_codice_fiscale` | `soggetti.codice_fiscale%TYPE` |      Si      | `NULL`  | Richiesto da guard PF. Normalizzato UPPER(TRIM). |
| `p_email`          | `text`                         |      Si      | `NULL`  | Usata per il contatto default.                   |
| `p_data_nascita`   | `soggetti.data_nascita%TYPE`   |      No      | `NULL`  |                                                  |
| `p_sesso`          | `soggetti.sesso%TYPE`          | secondo la natura | `NULL` | `M`, `F` o `X` («non si puo' stabilire»). Nessun default: lo decide `sesso_policy` della natura, nel guard. |
| `p_stato_iso2`     | `config.stati.codice_iso2%TYPE` |      No      | `NULL`  | ISO2 per nazionalita'; NULL = lo stato proposto (rev 2026-10-18). |
| `p_comune_nascita_id` | `soggetti.comune_id%TYPE`  |      No      | `NULL`  | Comune di nascita (FK `fk_comuni_config`).       |
| `p_tipo_contatto_id` | `config.tipi_contatti.id%TYPE` | No       | `NULL`  | Fallback: primo di `config.tipi_contatti`.       |
| `p_tipo_soggetto_dettaglio_id` | `config.tipi_soggetto_dettaglio.id%TYPE` | Si | `NULL` | Natura di dettaglio PF: privato (PR) o ditta individuale (DI). Guard nel body. |
| `p_partita_iva`    | `soggetti.partita_iva%TYPE`    | secondo la natura | `NULL` | Per la ditta individuale: la pretende `trgfn_soggetti_guard_cf_piva_obbligatori`. |
| `p_forma_giuridica_id` … `p_data_costituzione` | `dati_societari.<colonna>%TYPE` | No | `NULL` | ⭐ Rev 20261020-03, in coda, nell'ordine di `fn_crea_soggetto_pg`: forma, provincia e numero REA, capitale, socio unico, liquidazione, canale FE, PEC, codice SDI, data di costituzione. Vedi [dati_societari](/dbzero/anagrafiche/manual/dati_societari). |

---

### Valore di ritorno

`anagrafiche.soggetti.id%TYPE` (UUID) -- ID del soggetto creato.

---

### Regole applicate

* **Natura:** `p_tipo_soggetto_dettaglio_id` obbligatorio (`E_ADMIN_VALIDAZIONE`
  se manca o non esiste); una natura base diversa da PF si rifiuta con
  `E_SOGGETTO_CREAZIONE_NATURA_ERRATA` (classe TECNICO: e' il chiamante che ha
  sbagliato funzione).
* **Lookup stato:** risolve `stato_id` da `config.stati` con `codice_iso2`.
  Errore se non trovato: `E_CODICE`.
* **Guard CF univoco:** verifica su `(stato_id, id_fiscale_univoco_cf_piva)`.
  Errore: `E_ADMIN_CF_DUPLICATO`.
* **INSERT soggetto:** con la natura ricevuta, la partita IVA, il sesso cosi'
  com'e', `comune_id = p_comune_nascita_id`, `attivo = true`.
  La FK `fk_comuni_config` verifica automaticamente l'esistenza del comune.
* **INSERT contatto default:** con `nominativo = cognome + nome`,
  `email = p_email`, `is_default = true`.
  Il trigger `trgfn_contatti_set_default_contatto` gestisce automaticamente
  il flag default.
* **Dati societari (rev 20261020-03):** li scrive il BB
  `fn_scrivi_dati_societari_alla_nascita` col verbo `fn_scrivi_dati_societari`,
  se la natura li pretende (`REQUIRED`) o se la sezione c'e' (almeno un campo con
  un valore fra forma, REA, capitale, canale FE, PEC, codice SDI e data; socio
  unico e liquidazione da soli non contano). Per la DI (`OPTIONAL`) senza sezione
  non nasce nessuna riga. Un privato (`NONE`) con la sezione si rifiuta
  (`E_DATI_SOCIETARI_TIPO_SOGGETTO_NON_AMMESSO`): mai scartata in silenzio.
  Forma ammessa, REA, capitale e canale FE li controllano i trigger della tabella.

---

### Trigger coinvolti

| Trigger                                    | Fase          | Effetto                                  |
| ------------------------------------------ | ------------- | ---------------------------------------- |
| `trgfn_soggetti_gen_codice`                | BEFORE INSERT | Genera codice univoco soggetto           |
| `trgfn_soggetti_normalize`                 | BEFORE INSERT | Calcola `ragione_sociale_completa`       |
| `trgfn_soggetti_guard_cf_piva_obbligatori` | BEFORE INSERT | Valida CF/PIVA in base a natura          |
| `trgfn_soggetti_guard_sesso_policy`        | BEFORE INSERT | Sesso obbligatorio, facoltativo o vietato secondo `sesso_policy` |
| `trgfn_soggetti_valida_cf_piva_dispatch`   | BEFORE INSERT | Valida formato CF (16 char)              |
| `trgfn_soggetti_guard_soggetto_contatti`   | DEFERRED      | Verifica almeno 1 contatto al COMMIT     |
| `trgfn_soggetti_guard_indirizzi_required`  | DEFERRED      | Verifica indirizzi obbligatori al COMMIT |
| `trgfn_contatti_set_default_contatto`      | BEFORE INSERT | Auto-imposta `is_default`                |
| `trgfn_dati_societari_guard_tipo_soggetto` | BEFORE INSERT | La natura ammette i dati societari (PR no) |
| `trgfn_dati_societari_guard_forma_giuridica` | BEFORE INSERT | Forma ammessa dalla natura; REA e capitale dalla forma |
| `trgfn_dati_societari_guard_canale_fe`     | BEFORE INSERT | Il canale FE ha il suo recapito          |

---

### Vincoli DEFERRED (responsabilita' del chiamante)

Il trigger `trgfn_soggetti_guard_indirizzi_required` verifica al COMMIT
che il soggetto abbia gli indirizzi obbligatori definiti dalla matrice
`config.tipi_soggetto_dettaglio_tipi_indirizzo`.

Se per la natura (PR o DI) e' configurato l'indirizzo RES come obbligatorio,
il **chiamante deve creare l'indirizzo** prima del COMMIT della transazione.

---

### Riusabilita'

| Orchestratore                   | Uso                                           |
| ------------------------------- | --------------------------------------------- |
| `fn_crea_operatore_v2`          | Crea il soggetto PF (privato, PR) dell'operatore, flusso A |
| backend (`SoggettiService`)     | Crea privati e ditte individuali dal form anagrafico, con la sezione societaria della DI |

---

{% include-markdown "signature-core.md" %}
