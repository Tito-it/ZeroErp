# API Contatti Ruolo (Anagrafiche)

## Scopo

Endpoint REST per la gestione dei contatti a livello ruolo con supporto
utility. Implementa la cascata a 3 livelli: utility specifica, ruolo generico,
soggetto (fallback readonly).

## Contesto

I contatti risiedono in un'unica tabella `anagrafiche.contatti` con contesto
determinato dai campi nullable: `soggetto_id` (sempre presente),
`soggetto_ruolo_id` (se livello ruolo), `utility_id` (se specifico utility).

L'autenticazione avviene tramite token JWT. Le risposte seguono l'envelope
standard `{"data": ...}`.

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
| `utility_id` | int | No | Se presente, attiva il livello 1 (utility specifica) |

### Cascata di risoluzione

| Priorita` | Livello | Condizione | `fonte` | Editabile |
|---|---|---|---|---|
| 1 | Utility | `utility_id = X` | `utility` | Si` |
| 2 | Ruolo generico | `utility_id IS NULL`, tipo non coperto da L1 | `ruolo` | Si` |
| 3 | Soggetto | `soggetto_ruolo_id IS NULL`, tipo non coperto da L1+L2 | `soggetto` | No |

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
        "utility_id": 5,
        "utility_codice": "GAS",
        "fonte": "utility"
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
| `nominativo` | string | No | Nome contatto |
| `email` | string | No | Email |
| `telefono` | string | No | Telefono |
| `cellulare` | string | No | Cellulare |
| `pec` | string | No | PEC |
| `tipo_contatto_id` | int | Si` | Tipo contatto (NOT NULL) |
| `unita_organizzativa_id` | int | No | Unita` organizzativa |
| `utility_id` | int | No | Se presente, contatto specifico per utility |
| `note` | string | No | Note |

---

## 3. Aggiorna contatto ruolo

| | |
|---|---|
| **Metodo** | `PATCH` |
| **URL** | `/api/v1/anagrafiche/ruoli/{soggetto_ruolo_id}/contatti/{contatto_id}/` |

Ownership check su `soggetto_ruolo_id`.

---

## 4. Elimina contatto ruolo

| | |
|---|---|
| **Metodo** | `DELETE` |
| **URL** | `/api/v1/anagrafiche/ruoli/{soggetto_ruolo_id}/contatti/{contatto_id}/` |

Ownership check su `soggetto_ruolo_id`.

---

## Dipendenze DB

| Oggetto | Schema | Tipo | Ruolo |
|---|---|---|---|
| `anagrafiche.contatti` | anagrafiche | tabella | Tabella unica contatti multi-livello |
| `config.tipi_contatti` | config | tabella | Lookup tipo contatto |
| `config.utilities` | config | tabella | Lookup utility_codice |

## Note di migrazione

- `utility_id` e` stato aggiunto con vincolo UNIQUE multi-livello `uq_contatti_multilevel`
- `tipo_contatto_id` e` NOT NULL (migrazione precedente)
- Il pattern cascata e` condiviso con indirizzi ruolo e conti bancari ruolo
