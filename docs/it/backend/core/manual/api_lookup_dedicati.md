# API Lookup dedicati di core (anagrafiche e config)

## Scopo

Descrivere i lookup **dedicati** di `core` che non hanno una pagina propria:
tipi soggetto dettaglio, tipi ruolo per natura, forme giuridiche, utility per
emittente, conti contabili, sistema codici e autocomplete dei comuni.

## Contesto

Sono lookup dedicati e non il generico
([api_lookup_codici.md](api_lookup_codici.md)) perché ciascuno espone colonne
o filtri che il generico non ha (policy di un tipo soggetto, `tipo_conto`, la
matrice utility dell'emittente…). Regola generale: api.md §«Lookup — due
pattern, una regola».

Tratti comuni a tutte le rotte di questa pagina:

- view `DomainAPIView` in `apps/core/api/views_lookup.py`, letture da
  `LookupRepository` (`apps/core/db/lookup_repository.py`);
- **`skip_area_check = True`**: cross-dominio, li usano anagrafiche, vendite,
  catalogo; serve solo l'autenticazione JWT;
- solo `GET`, envelope `{"data": {"results": [...]}}` salvo dove indicato
  (sistema codici è un oggetto, comuni ha anche `count`);
- nessuna paginazione salvo i comuni: tornano l'insieme intero.

## Base URL

```
/api/v1/core/lookup/
```

| Rotta | View | Sezione |
|---|---|---|
| `tipi-soggetto-dettaglio/` | `LookupTipiSoggettoDettaglioView` | 1 |
| `tipi-ruoli-natura/` | `LookupTipiRuoliPerNaturaView` | 2 |
| `forme-giuridiche/` | `LookupFormeGiuridicheView` | 3 |
| `utilities-per-emittente/` | `LookupUtilitiesPerEmittenteView` | 4 |
| `conti-contabili/` | `LookupContiContabiliView` | 5 |
| `sistema-codici/` | `LookupSistemaCodiciView` | 6 |
| `comuni/` | `LookupComuniView` | 7 |

---

## 1. Tipi soggetto dettaglio

`GET /api/v1/core/lookup/tipi-soggetto-dettaglio/` — nessun parametro.

Il frontend lo usa per guidare il form del soggetto: quali campi chiedere e
quali sono obbligatori per il tipo scelto.

| Campo | Fonte | Note |
|---|---|---|
| `id` | `config.tipi_soggetto_dettaglio.id` | |
| `codice_interno`, `descrizione` | idem | |
| `natura_soggetto` | `config.tipi_soggetto.id` | la natura (codice testo), è il valore da passare al §2 |
| `cf_obbligatorio`, `piva_obbligatoria` | `tipi_soggetto_dettaglio` | bool |
| `dati_societari_policy` | `tipi_soggetto_dettaglio` | enum `config.presenza_policy_enum` (`NONE`/`OPTIONAL`/`REQUIRED`) |
| `sesso_policy` | `tipi_soggetto_dettaglio` | idem: `REQUIRED` asterisco, `OPTIONAL` vuoto ammesso, `NONE` campo nascosto (dal 2026-10-09) |

Ordine per `id`. ⚠️ Nessun filtro di attività: tornano **tutte** le righe (il
commento del repository dice «solo attivi», la query no).

---

## 2. Tipi ruolo per natura

`GET /api/v1/core/lookup/tipi-ruoli-natura/`

| Parametro | Tipo | Obbligatorio | Descrizione |
|---|---|---|---|
| `natura_soggetto` | string | No | Codice della natura (`natura_soggetto` del §1) |

Senza parametro: tutti i tipi ruolo. Con la natura: i tipi ruolo che la
matrice `config.tipi_ruoli_nature_ammesse` ammette per quella natura (riga
attiva e valida oggi), **più** i tipi ruolo che nella matrice non hanno
nessuna riga — un ruolo senza restrizioni vale per ogni natura.

Righe: `id`, `codice` (`codice_interno`, o `codice` se manca), `descrizione`;
ordine per descrizione.

---

## 3. Forme giuridiche

`GET /api/v1/core/lookup/forme-giuridiche/`

| Parametro | Tipo | Obbligatorio | Descrizione |
|---|---|---|---|
| `tipo_soggetto_dettaglio_id` | int | No | Solo le forme ammesse per quel tipo (matrice `config.forme_giuridiche_tipi_soggetto_dettaglio`, righe attive). Non numerico → 400 |

Solo forme **attive**. Righe: `id`, `codice` (`codice_interno` o `codice`),
`descrizione`, `rea_policy`, `capitale_sociale_policy` (i due valori ammessi
li fissano i `CHECK` della tabella), `attivo`. Ordine per descrizione.

---

## 4. Utility per emittente

`GET /api/v1/core/lookup/utilities-per-emittente/`

| Parametro | Tipo | Obbligatorio | Descrizione |
|---|---|---|---|
| `ruolo` | string | No | Codice del tipo ruolo del soggetto (es. `CL`, `FO`), maiuscole indifferenti |

Alimenta la combo «Utility». Si parte dalle utility ammesse per il ruolo
emittente (`EF`) in `config.utilities_tipi_ruolo` (riga attiva e valida oggi).
Poi:

- **emittente dell'utente** (risolto con la catena dei parametri,
  `ParameterService.get_emittente_fiscale_id_for_user`): restano le sole utility
  attive nella matrice `anagrafiche.emittenti_fiscali_utilities` di quell'emittente;
- **nessun emittente, o matrice dell'emittente vuota**: nessun filtro
  d'emittente, tornano tutte le utility `EF`. ⚠️ Il secondo caso vale per
  chiunque, non solo per il super admin: un emittente senza nessuna riga in
  matrice vede tutte le utility;
- **`ruolo`**: intersezione con le utility ammesse anche per quel ruolo.

Righe: `id`, `codice`, `codice_interno`, `descrizione`; ordine per
descrizione. Il default lato FE (`useUtilityDefaultId`, parametro
`DEFAULT_UTILITY`) si sceglie dentro questo insieme.

---

## 5. Conti contabili

`GET /api/v1/core/lookup/conti-contabili/`

| Parametro | Tipo | Obbligatorio | Descrizione |
|---|---|---|---|
| `tipo` | string | No | `A` (acquisto) o `V` (vendita), maiuscole indifferenti. Altro valore → 400 `E_VALIDATION_INPUT` |

Lookup dedicato perché espone `tipo_conto`, che il generico non restituisce;
lo usa il drawer dell'articolo per le due combo conto vendita / conto
acquisto. Righe: `id`, `codice`, `descrizione`, `tipo_conto`; ordine per
codice. ⚠️ Nessun filtro di attività.

---

## 6. Sistema codici

`GET /api/v1/core/lookup/sistema-codici/`

| Parametro | Tipo | Obbligatorio | Descrizione |
|---|---|---|---|
| `schema` | string | Sì | Schema della tabella |
| `tabella` | string | Sì | Nome della tabella |
| `colonna` | string | No | Colonna del codice, default `codice` |

Dice al form se il codice di un record lo genera il DB o va scritto a mano,
leggendo `config.sistema_codici`. ⚠️ I due parametri «obbligatori» non sono
controllati: assenti valgono stringa vuota, e la risposta è «non
configurato».

Risposta (oggetto, non lista):

```json
{ "data": { "auto": true, "prefisso": "CL", "separatore": "-", "lunghezza_numero": 6 } }
```

`auto` è `usa_sequenza` della riga. Senza riga per la terna:
`{"data": {"auto": false}}`.

---

## 7. Comuni (autocomplete)

`GET /api/v1/core/lookup/comuni/` — endpoint di ricerca (`is_search_endpoint`,
throttle di ricerca).

| Parametro | Tipo | Obbligatorio | Descrizione |
|---|---|---|---|
| `search` | string | No | Contiene, maiuscole indifferenti, sulla denominazione |
| `limit` | int | No | Default 20, massimo 100 |
| `offset` | int | No | Default 0 |

Risposta:

```json
{ "data": { "count": 7904, "results": [ { "id": 1, "descrizione": "Abano Terme", "provincia_sigla": "PD" } ] } }
```

`count` è il totale della ricerca, non le righe della pagina (BB
`fetch_paged_with_total`). Ordine per descrizione, poi `id`.

---

## Errori

| Codice | HTTP | Quando |
|---|---|---|
| `E_VALIDATION_INPUT` | 400 | `tipo` dei conti contabili fuori da `A`/`V`; `tipo_soggetto_dettaglio_id` o `limit`/`offset` non numerici |
| `E_AUTHENTICATION_FAILED` | 401 | token assente o scaduto |

## Dipendenze DB

| Oggetto | Rotta |
|---|---|
| `config.tipi_soggetto_dettaglio`, `config.tipi_soggetto` | 1 |
| `config.tipi_ruoli`, `config.tipi_ruoli_nature_ammesse` | 2 |
| `config.forme_giuridiche`, `config.forme_giuridiche_tipi_soggetto_dettaglio` | 3 |
| `config.utilities`, `config.utilities_tipi_ruolo`, `config.tipi_ruoli`, `anagrafiche.emittenti_fiscali`, `anagrafiche.emittenti_fiscali_utilities` | 4 |
| `config.conti_contabili` | 5 |
| `config.sistema_codici` | 6 |
| `config.comuni`, `config.province` | 7 |

