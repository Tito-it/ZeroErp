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
| `tipo_soggetto_id` | `config.tipi_soggetto.id` | codice della macro-tipologia (`PF`, `PG`, `ENC`) |
| `natura_soggetto` | `config.tipi_soggetto.natura_soggetto` | enum `config.natura_soggetto_enum` (`PF`/`PG`/`ENTE`), è il valore da passare al §2. Fino al 2026-10-11 qui usciva `tipi_soggetto.id` (per l'ente `ENC`, non `ENTE`) |
| `cf_obbligatorio`, `piva_obbligatoria` | `tipi_soggetto_dettaglio` | bool |
| `formato_cf`, `formato_piva` | `tipi_soggetto_dettaglio` | formato atteso di CF e P.IVA per il tipo |
| `cliente_pa_ammesso`, `split_payment_ammesso` | `tipi_soggetto_dettaglio` | bool: il form mostra i due flag di regime fiscale solo dove ammessi (la regola la presidia il DB) |
| `dati_societari_policy` | `tipi_soggetto_dettaglio` | enum `config.presenza_policy_enum` (`NONE`/`OPTIONAL`/`REQUIRED`) |
| `sesso_policy` | `tipi_soggetto_dettaglio` | idem: `REQUIRED` asterisco, `OPTIONAL` vuoto ammesso, `NONE` campo nascosto (dal 2026-10-09) |

Ordine per `id`. Tornano **tutte** le righe: `config.tipi_soggetto_dettaglio`
non ha una colonna `attivo`, quindi non c'è un'attività da filtrare.

---

## 2. Tipi ruolo per natura

`GET /api/v1/core/lookup/tipi-ruoli-natura/`

| Parametro | Tipo | Obbligatorio | Descrizione |
|---|---|---|---|
| `natura_soggetto` | string | No | La natura, enum (`natura_soggetto` del §1, es. `ENTE`) |

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
| `tipo_soggetto_dettaglio_id` | int | No | Solo le forme ammesse per quel tipo (matrice `config.forme_giuridiche_tipi_soggetto_dettaglio`, righe attive e valide oggi: predicato del guard `anagrafiche.fn_forma_giuridica_ammessa`). Non numerico → 400 |

Solo forme **attive**. Righe: `id`, `codice` (`fg.codice`: la tabella non ha `codice_interno`),
`descrizione`, `rea_policy`, `capitale_sociale_policy` (i due valori ammessi
li fissano i `CHECK` della tabella), `attivo`. Ordine per descrizione.

---

## 4. Utility per emittente

`GET /api/v1/core/lookup/utilities-per-emittente/`

| Parametro | Tipo | Obbligatorio | Descrizione |
|---|---|---|---|
| `ruolo` | string | No | Codice del tipo ruolo del soggetto (es. `CL`, `FO`), maiuscole indifferenti |

Alimenta la combo «Utility»: le utility ammesse per il ruolo emittente
fiscale (`EF`) in `config.utilities_tipi_ruolo` (riga attiva e valida alla data
operativa), **uguali per ogni operatore**. Con `ruolo`, l'intersezione con le
utility ammesse anche per quel ruolo. «Per emittente», nel nome della rotta, è
il **ruolo** EF, non l'emittente attivo.

⛔ La tabella `anagrafiche.emittenti_fiscali_utilities` **non** filtra: è
opzionale e porta i parametri di fatturazione di una coppia emittente-utility
(fattura minima, arrotondamento del totale), non l'elenco delle utility
dell'emittente — la sola ammissibilità del modello è `utilities_tipi_ruolo`
(changeSet `20260408-01`). Fino al 2026-10-14 la usava come filtro: un
emittente con i parametri della sola luce si vedeva sparire il gas.

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
codice. Tornano tutti i conti del tipo chiesto: `config.conti_contabili` non
ha una colonna `attivo`.

---

## 6. Sistema codici

`GET /api/v1/core/lookup/sistema-codici/`

| Parametro | Tipo | Obbligatorio | Descrizione |
|---|---|---|---|
| `schema` | string | Sì | Schema della tabella |
| `tabella` | string | Sì | Nome della tabella |
| `colonna` | string | No | Colonna del codice, default `codice` |

Dice al form se il codice di un record lo genera il DB o va scritto a mano,
leggendo `config.sistema_codici`. `schema` o `tabella` assenti (o vuoti) →
400 `E_VALIDATION_INPUT`, col nome del parametro nel messaggio (dal
2026-10-14: prima valevano stringa vuota e la risposta era «non
configurato»). `colonna` assente vale `codice`.

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
| `limit` | int | No | Default 20, fra 1 e 100. Non numerico → default |
| `offset` | int | No | Default 0. Non numerico o negativo → 0 |

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
| `E_VALIDATION_INPUT` | 400 | `tipo` dei conti contabili fuori da `A`/`V`; `tipo_soggetto_dettaglio_id` non numerico (per i comuni `limit`/`offset` non numerici ripiegano sul default) |
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

