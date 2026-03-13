## Documentazione Concettuale -- Funzione `anagrafiche.fn_crea_soggetto_pf()`

> **Vedi anche**
>
> **Approfondimento tabelle:**
>
> * [anagrafiche.soggetti](/dbzero/anagrafiche/tabelle/soggetti)
> * [anagrafiche.contatti](/dbzero/anagrafiche/tabelle/contatti)
> * [config.tipi_soggetto_dettaglio](/dbzero/config/tabelle/tipi_soggetto_dettaglio)
>
> **Approfondimento funzioni:**
>
> * [anagrafiche.fn_crea_operatore](/dbzero/anagrafiche/manual/fn_crea_operatore)
> * [anagrafiche.fn_crea_risorsa_umana](/dbzero/anagrafiche/manual/fn_crea_risorsa_umana)
>
> **Guide:**
>
> * [Soggetti e ruoli anagrafici](/guide/soggetti-e-ruoli-anagrafici)
> * [Gestione degli indirizzi](/guide/gestione-degli-indirizzi)

---

### 🎯 Scopo Principale

(latest review 13-03-2026)
Building block atomico per la creazione di un soggetto Persona Fisica
(natura PR = Privato) con contatto default obbligatorio.

Imposta correttamente `tipo_soggetto_dettaglio_id` tramite lookup su
`config.tipi_soggetto_dettaglio.codice_interno = 'PR'` e `stato_id`
tramite lookup su `config.stati.codice_iso2`.

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
| `p_sesso`          | `soggetti.sesso%TYPE`          |      No      | `'M'`   |                                                  |
| `p_stato_iso2`     | `character varying`            |      No      | `'IT'`  | ISO2 per nazionalita'.                           |

---

### Valore di ritorno

`anagrafiche.soggetti.id%TYPE` (UUID) -- ID del soggetto creato.

---

### Regole applicate

* **Lookup natura PR:** risolve `tipo_soggetto_dettaglio_id` da
  `config.tipi_soggetto_dettaglio` con `codice_interno = 'PR'`.
  Errore se non trovato: `E_GENERICO`.
* **Lookup stato:** risolve `stato_id` da `config.stati` con `codice_iso2`.
  Errore se non trovato: `E_GENERICO`.
* **Guard CF univoco:** verifica su `(stato_id, id_fiscale_univoco_cf_piva)`.
  Errore: `E_ADMIN_CF_DUPLICATO`.
* **INSERT soggetto:** con `tipo_soggetto_dettaglio_id`, `attivo = true`.
* **INSERT contatto default:** con `nominativo = cognome + nome`,
  `email = p_email`, `is_default = true`.
  Il trigger `trgfn_contatti_set_default_contatto` gestisce automaticamente
  il flag default.

---

### Trigger coinvolti

| Trigger                                    | Fase          | Effetto                                  |
| ------------------------------------------ | ------------- | ---------------------------------------- |
| `trgfn_soggetti_gen_codice`                | BEFORE INSERT | Genera codice univoco soggetto           |
| `trgfn_soggetti_normalize`                 | BEFORE INSERT | Calcola `ragione_sociale_completa`       |
| `trgfn_soggetti_guard_cf_piva_obbligatori` | BEFORE INSERT | Valida CF/PIVA in base a natura          |
| `trgfn_soggetti_valida_cf_piva_dispatch`   | BEFORE INSERT | Valida formato CF (16 char)              |
| `trgfn_soggetti_guard_soggetto_contatti`   | DEFERRED      | Verifica almeno 1 contatto al COMMIT     |
| `trgfn_soggetti_guard_indirizzi_required`  | DEFERRED      | Verifica indirizzi obbligatori al COMMIT |
| `trgfn_contatti_set_default_contatto`      | BEFORE INSERT | Auto-imposta `is_default`                |

---

### Vincoli DEFERRED (responsabilita' del chiamante)

Il trigger `trgfn_soggetti_guard_indirizzi_required` verifica al COMMIT
che il soggetto abbia gli indirizzi obbligatori definiti dalla matrice
`config.tipi_soggetto_dettaglio_tipi_indirizzo`.

Se per la natura PR e' configurato l'indirizzo RES come obbligatorio,
il **chiamante deve creare l'indirizzo** prima del COMMIT della transazione.

---

### Riusabilita'

| Orchestratore                   | Uso                                           |
| ------------------------------- | --------------------------------------------- |
| `fn_crea_operatore`             | Crea soggetto PF per operatore                |
| (futuro) `fn_crea_cliente_pf`   | Crea soggetto PF per cliente privato          |
| (futuro) `fn_crea_fornitore_pf` | Crea soggetto PF per fornitore persona fisica |

---

{% include-markdown "signature-core.md" %}
