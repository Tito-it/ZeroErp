# API Contatti Ruolo (Anagrafiche)

## Scopo

Endpoint REST per la gestione dei contatti a livello ruolo con supporto
istanza. Implementa la cascata a 3 livelli: istanza specifica, ruolo generico,
soggetto (fallback readonly).

## Contesto

I contatti risiedono in un'unica tabella `anagrafiche.contatti` con contesto
determinato dai campi nullable: `soggetto_id` (sempre presente),
`soggetto_ruolo_id` (se livello ruolo), `istanza_utility_id` (se specifico istanza).

L'autenticazione avviene tramite token JWT. Le risposte seguono l'envelope
standard `{"data": ..., "meta": {...}}`. Permesso: area `anagrafiche`
(`DomainAPIView`).

## Base URL

```
/api/v1/anagrafiche/ruoli/{soggetto_ruolo_id}/contatti/
```

---

## 1. Lista contatti ruolo (cascata 3 livelli)

Restituisce i contatti del ruolo con cascata per `tipo_contatto_id`.

| | |
|---|---|
| **Metodo** | `GET` |
| **URL** | `/api/v1/anagrafiche/ruoli/{soggetto_ruolo_id}/contatti/` |

### Parametri query

| Parametro | Tipo | Obbligatorio | Descrizione |
|---|---|---|---|
| `istanza_utility_id` | int | No | Se presente, attiva il livello 1 (istanza specifica) |

### Cascata di risoluzione

| Priorita` | Livello | Condizione | `fonte` | Editabile |
|---|---|---|---|---|
| 1 | Istanza | `istanza_utility_id = X` | `istanza` | Si` |
| 2 | Ruolo generico | `istanza_utility_id IS NULL`, tipo non coperto da L1 | `ruolo` | Si` |
| 3 | Soggetto | `soggetto_ruolo_id IS NULL`, tipo non coperto da L1+L2 | `soggetto` | No |

Ai livelli 2 e 3 i contatti con `tipo_contatto_id` NULL sono scartati (non
possono "coprire" un tipo); al livello 1 restano tutti.

### Risposta (200)

```json
{
  "data": {
    "contatti_ruolo": [
      {
        "id": 1,
        "nominativo": "Mario Rossi",
        "email": "mario@example.com",
        "telefono": null,
        "cellulare": "+39 333 1234567",
        "pec": null,
        "note": null,
        "tipo_contatto_id": 1,
        "tipo_contatto_descrizione": "Referente commerciale",
        "unita_organizzativa_id": null,
        "istanza_utility_id": 100,
        "utility_codice": "ELE",
        "fonte": "istanza"
      }
    ],
    "contatti_soggetto": [
      {
        "...": "stessa struttura, fonte='soggetto'"
      }
    ]
  }
}
```

---

## 2. Crea contatto ruolo

| | |
|---|---|
| **Metodo** | `POST` |
| **URL** | `/api/v1/anagrafiche/ruoli/{soggetto_ruolo_id}/contatti/` |

### Body (JSON)

| Campo | Tipo | Obbligatorio | Descrizione |
|---|---|---|---|
| `nominativo` | string | Si | Nome contatto |
| `email` | string | No | Email |
| `telefono` | string | No | Telefono |
| `cellulare` | string | No | Cellulare |
| `pec` | string | No | PEC |
| `tipo_contatto_id` | int | Si | Tipo contatto (uno per tipo sul ruolo, o sul ruolo per istanza) |
| `unita_organizzativa_id` | int | No | Unita' organizzativa |
| `istanza_utility_id` | int | No | Se presente, contatto specifico per istanza |
| `note` | string | No | Note |

La logica sta in `SoggettiService.create_contatto_ruolo` (fino al 2026-10-09
era scritta nella view).

> **Rifiuti (dal 2026-10-09, BB `crea_contatto_validato`)**: il contatto deve
> essere valido (`nominativo` + `tipo_contatto_id`), altrimenti
> `400 E_CONTATTO_INCOMPLETO` con i campi mancanti in `error.fields`. Un
> contatto per tipo: un secondo contatto con lo stesso tipo risponde
> `409 E_ANAG_DUPLICATO` col campo `tipo_contatto_id`. Fino a quella data
> entrambi uscivano come `400 E_DATABASE` generico.

---

## 3. Aggiorna contatto ruolo

| | |
|---|---|
| **Metodo** | `PATCH` |
| **URL** | `/api/v1/anagrafiche/ruoli/{soggetto_ruolo_id}/contatti/{contatto_id}/` |

Ownership check su `soggetto_ruolo_id`.

Chiavi ammesse nel corpo: `nominativo`, `email`, `telefono`, `cellulare`, `pec`,
`tipo_contatto_id`, `unita_organizzativa_id`, `note`. Una chiave fuori elenco
(compreso `istanza_utility_id`) → `400 E_ANAG_VALIDAZIONE`; un corpo vuoto pure
(dal 2026-10-20: prima 404).

Risposta (200): `{"data": {"updated": true}}`. Contatto inesistente o di un
altro ruolo → `404 E_ANAG_NOT_FOUND`.

---

## 4. Elimina contatto ruolo

| | |
|---|---|
| **Metodo** | `DELETE` |
| **URL** | `/api/v1/anagrafiche/ruoli/{soggetto_ruolo_id}/contatti/{contatto_id}/` |

Ownership check su `soggetto_ruolo_id`. Risposta (200): `{"data": {"deleted": true}}`.
Contatto inesistente o di un altro ruolo → `404 E_ANAG_NOT_FOUND`.

---

## Dipendenze DB

| Oggetto | Schema | Tipo | Ruolo |
|---|---|---|---|
| `anagrafiche.contatti` | anagrafiche | tabella | Tabella unica contatti multi-livello |
| `anagrafiche.istanze_utilities` | anagrafiche | tabella | FK istanza_utility_id |
| `config.tipi_contatti` | config | tabella | Lookup tipo contatto |

## Note di migrazione

- Changeset DB: `20260325-01-replace-utility-with-istanza-contatti-mctit.yaml` (schema)
- Changeset DB: `20260325-06-recreate-contatti-chain-istanza-mctit.yaml` (funzioni)
- 3 partial unique index sostituiscono il vecchio `uq_contatti_multilevel`
- `utility_codice` e` esposto: si ricava dall'istanza del contatto (dati
  precontrattuali, altrimenti billing account); NULL per i contatti senza istanza
- Il pattern cascata e` condiviso con indirizzi ruolo e conti bancari ruolo
