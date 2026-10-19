## Documentazione Concettuale -- Funzione `anagrafiche.fn_crea_soggetto_pg()`

> **Vedi anche**
>
**Approfondimento tabelle:**
>
[anagrafiche.soggetti](/dbzero/anagrafiche/tabelle/soggetti)
> [anagrafiche.contatti](/dbzero/anagrafiche/tabelle/contatti)
> [anagrafiche.dati_societari](/dbzero/anagrafiche/tabelle/dati_societari)
> [config.tipi_soggetto_dettaglio](/dbzero/config/tabelle/tipi_soggetto_dettaglio)
>
**Approfondimento funzioni:**
>
[anagrafiche.fn_crea_soggetto_pf](/dbzero/anagrafiche/manual/fn_crea_soggetto_pf) -- controparte PF
> [script.fn_get_or_create_soggetto_ruolo](/dbzero/script/manual/fn_get_or_create_soggetto_ruolo)
>
**Guide:**
>
[Soggetti e ruoli anagrafici](/guide/soggetti-e-ruoli-anagrafici)
> [Gestione degli indirizzi](/guide/gestione-degli-indirizzi)

---
### 🎯 Scopo Principale
(latest review 20-10-2026)
Building block atomico per la creazione di un soggetto Persona Giuridica
con contatto default obbligatorio e dati societari (se la natura li pretende
o se passati: lo decide
[fn_scrivi_dati_societari_alla_nascita](/dbzero/anagrafiche/manual/fn_scrivi_dati_societari_alla_nascita),
lo stesso BB della porta delle persone fisiche).

Riceve `p_tipo_soggetto_dettaglio_id` perche' societa' ed enti hanno nature
diverse (SP, SC, ENC) — il chiamante deve risolvere il tipo.

⛔ **Una persona fisica non passa da qui** (rev 2026-10-09,
brief-db-sesso-senza-default): una natura base PF — privato (PR) o ditta
individuale (DI) — si rifiuta con `E_SOGGETTO_CREAZIONE_NATURA_ERRATA`. La sua
porta e' [fn_crea_soggetto_pf](/dbzero/anagrafiche/manual/fn_crea_soggetto_pf),
che ne riceve nome, cognome e sesso. Il sesso qui non si scrive: per societa' ed
enti e' `NULL` (`sesso_policy = NONE`).

**Non crea indirizzo:** il chiamante e' responsabile di creare gli indirizzi
obbligatori dalla matrice `config.tipi_soggetto_dettaglio_tipi_indirizzo`
(trigger DEFERRED verifica al COMMIT).

**Non assegna ruoli:** il chiamante usa
`script.fn_get_or_create_soggetto_ruolo` separatamente.

---

### Parametri

| Parametro                      | Tipo                                        | Obbligatorio | Default | Note                                             |
| ------------------------------ | ------------------------------------------- | :----------: | ------- | ------------------------------------------------ |
| `p_ragione_sociale`            | `soggetti.ragione_sociale%TYPE`             |      Si      | —       | Guard nel body.                                  |
| `p_tipo_soggetto_dettaglio_id` | `soggetti.tipo_soggetto_dettaglio_id%TYPE`  |      Si      | —       | ID del tipo (SC, ENC, DI, PA...). Guard > 0.     |
| `p_email`                      | `text`                                      |      Si      | —       | Usata per il contatto default.                   |
| `p_codice_fiscale`             | `soggetti.codice_fiscale%TYPE`              |      No      | `NULL`  | Guard PG decide se obbligatorio. UPPER(TRIM).    |
| `p_partita_iva`                | `soggetti.partita_iva%TYPE`                 |      No      | `NULL`  | Guard PG decide se obbligatoria. UPPER(TRIM).    |
| `p_stato_iso2`                 | `config.stati.codice_iso2%TYPE`             |      No      | `NULL`  | ISO2 per nazionalita'; NULL = lo stato proposto (rev 2026-10-18). |
| `p_forma_giuridica_id`         | `dati_societari.forma_giuridica_id%TYPE`    |      No      | `NULL`  | FK forme_giuridiche.                             |
| `p_id_prov_iscri_rea`          | `dati_societari.id_prov_iscri_rea%TYPE`     |   DS req.    | `NULL`  | Provincia iscrizione REA (FK province).          |
| `p_iscrizione_rea`             | `dati_societari.iscrizione_rea%TYPE`        |   DS req.    | `NULL`  | Numero iscrizione REA.                           |
| `p_capitale_sociale`           | `dati_societari.capitale_sociale%TYPE`      |   DS req.    | `NULL`  | Capitale sociale.                                |
| `p_socio_unico`                | `dati_societari.socio_unico%TYPE`           |      No      | `'SU'`  | Enum: SU (socio unico), SM (plurimo).            |
| `p_liquidazione`               | `dati_societari.liquidazione%TYPE`          |      No      | `'LN'`  | Enum: LN (non in liquid.), LS (in liquid.).      |
| `p_destinatario_fe`            | `dati_societari.destinatario_fe%TYPE`       |   DS req.    | `NULL`  | Canale FE: 'P' = PEC, 'C' = Codice SDI.         |
| `p_pec_fatturazione`           | `dati_societari.pec_fatturazione%TYPE`      |      No      | `NULL`  | PEC fatturazione (unique).                       |
| `p_codice_sdi`                 | `dati_societari.codice_sdi%TYPE`            |      No      | `NULL`  | Codice destinatario SDI (unique).                |
| `p_tipo_contatto_id`           | `config.tipi_contatti.id%TYPE`              |      No      | `NULL`  | NULL = il primo di `config.tipi_contatti`.       |
| `p_data_costituzione`          | `dati_societari.data_costituzione%TYPE`     |      No      | `NULL`  | ⭐ Rev 20261020-02, in coda: prima si perdeva.   |

**Legenda obbligatorieta':**

- **Si** = guard esplicito nella funzione, errore `E_ADMIN_VALIDAZIONE`
- **No** = sempre opzionale
- **DS req.** = lo pretende la forma giuridica (REA e capitale) o il canale FE
  (PEC o codice SDI), nei trigger di `dati_societari`, quando la sezione si scrive

---

### Valore di ritorno

`anagrafiche.soggetti.id%TYPE` (UUID) -- ID del soggetto creato.

---

### Regole applicate

* **Lookup stato:** risolve `stato_id` da `config.stati` con `codice_iso2`.
  Errore se non trovato: `E_GENERICO`.
* **Verifica tipo soggetto:** verifica esistenza e legge `dati_societari_policy`
  da `config.tipi_soggetto_dettaglio`. Errore se non trovato: `E_ADMIN_VALIDAZIONE`.
* **Guard CF univoco:** se CF fornito, verifica su `(stato_id, id_fiscale_univoco_cf_piva)`.
  Errore: `E_ADMIN_CF_DUPLICATO`.
* **Guard PIVA univoca:** se PIVA fornita, stessa verifica.
  Errore: `E_ADMIN_PIVA_DUPLICATA`.
* **INSERT soggetto:** con `ragione_sociale`, `codice_fiscale`, `partita_iva`,
  `stato_id`, `tipo_soggetto_dettaglio_id`, `attivo = true`.
* **INSERT contatto default:** con `nominativo = ragione_sociale`,
  `email = p_email`, `is_default = true`.
* **Dati societari (rev 20261020-02):** li scrive il BB
  [fn_scrivi_dati_societari_alla_nascita](/dbzero/anagrafiche/manual/fn_scrivi_dati_societari_alla_nascita),
  che decide e poi chiama il verbo `fn_scrivi_dati_societari` (stato intero):
    - `dati_societari_policy = 'REQUIRED'` → sempre;
    - altrimenti, se la sezione c'e': almeno un campo con un valore fra forma,
      REA, capitale, canale FE, PEC, codice SDI e data di costituzione (socio
      unico e liquidazione da soli non contano);
    - ⚠️ una sezione passata a una natura `NONE` non si scarta piu' in silenzio:
      la rifiuta il guard della natura (`E_DATI_SOCIETARI_TIPO_SOGGETTO_NON_AMMESSO`).
  Le regole (forma ammessa, REA e capitale dalla forma, canale FE) stanno nei
  trigger della tabella: niente controlli qui (rev 20261011-01).

---

### Trigger coinvolti

| Trigger                                          | Fase          | Effetto                                       |
| ------------------------------------------------ | ------------- | --------------------------------------------- |
| `trgfn_soggetti_gen_codice`                      | BEFORE INSERT | Genera codice univoco soggetto                |
| `trgfn_soggetti_normalize`                       | BEFORE INSERT | Calcola `ragione_sociale_completa`            |
| `trgfn_soggetti_guard_cf_piva_obbligatori`       | BEFORE INSERT | Valida CF/PIVA in base a natura               |
| `trgfn_soggetti_valida_cf_piva_dispatch`         | BEFORE INSERT | Valida formato CF/PIVA                        |
| `trgfn_soggetti_guard_soggetto_contatti`         | DEFERRED      | Verifica almeno 1 contatto al COMMIT          |
| `trgfn_soggetti_guard_indirizzi_required`        | DEFERRED      | Verifica indirizzi obbligatori al COMMIT      |
| `trgfn_soggetti_guard_dati_societari_required`   | DEFERRED      | Verifica dati societari se REQUIRED al COMMIT |
| `trgfn_contatti_set_default_contatto`            | BEFORE INSERT | Auto-imposta `is_default`                     |
| `trgfn_dati_societari_guard_tipo_soggetto`       | BEFORE INSERT | Verifica tipo soggetto ammesso per DS         |
| `trgfn_dati_societari_guard_forma_giuridica`     | BEFORE INSERT | Verifica forma giuridica valida               |

---

### Vincoli DEFERRED (responsabilita' del chiamante)

Il trigger `trgfn_soggetti_guard_indirizzi_required` verifica al COMMIT
che il soggetto abbia gli indirizzi obbligatori definiti dalla matrice
`config.tipi_soggetto_dettaglio_tipi_indirizzo`.

Il trigger `trgfn_soggetti_guard_dati_societari_required` verifica al COMMIT
che i dati societari esistano se la policy e' REQUIRED.

Il **chiamante deve**:

1. Creare gli indirizzi obbligatori prima del COMMIT
2. Non preoccuparsi dei dati societari se usa questa funzione
   (li crea automaticamente quando la policy lo richiede)

---

### Riusabilita'

| Orchestratore                    | Uso                                           |
| -------------------------------- | --------------------------------------------- |
| (futuro) `fn_crea_cliente_pg`    | Crea soggetto PG per cliente societa'          |
| (futuro) `fn_crea_fornitore_pg`  | Crea soggetto PG per fornitore societa'        |
| (futuro) `fn_crea_emittente`     | Crea soggetto PG per emittente fiscale         |

---

{% include-markdown "signature-core.md" %}
