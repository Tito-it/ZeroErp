# API — dashboard configurabile

## Scopo

Servire al frontend **la dashboard di un utente**: quali widget vede, in che
ordine, e con che numeri sopra. Quattro endpoint sotto
`/api/v1/ui/dashboard/{codice}/`, dove `codice` identifica la dashboard (non
l'utente: quello arriva dal token).

## Contesto

La configurazione **non e' un record da leggere**: e' una **cascata risolta a
ogni richiesta**, e la risolve una funzione di database.

```
preferenza utente  →  preset (ruolo → emittente → sistema)  →  catalogo grezzo
```

Sopra la cascata il DB fa altre due cose: **innesta i widget nuovi** comparsi a
catalogo dopo l'ultima scelta dell'utente, e **filtra per permessi**. Un widget
che l'utente non ha diritto di vedere non arriva al client — non arriva
*disabilitato*, non arriva proprio.

⭐ Tutte e quattro le view dichiarano `skip_area_check = True`, ed e' coerente:
la dashboard e' cross-area per definizione. Il perimetro non lo fa la view, lo
fa la funzione DB quando filtra i widget.

## 1. `GET /api/v1/ui/dashboard/{codice}/config/`

La configurazione **effettiva** per l'utente autenticato: l'esito della cascata,
gia' filtrato. E' l'unico endpoint che il FE deve chiamare per sapere cosa
disegnare.

## 2. `GET /api/v1/ui/dashboard/{codice}/contatori/`

I contatori KPI dei widget **visibili**, calcolati in un giro solo.

⛔ **Non accetta chiavi dal client, ed e' una scelta di sicurezza esplicita.** Le
`contatore_key` sono quelle che la funzione DB ha gia' concesso a *questo*
utente: farsele passare da fuori aprirebbe una lettura cross-area — conteggi di
vendite a chi quell'area non ce l'ha. Il fatto che il client sappia gia' quali
widget vede non cambia la sostanza: la lista dei permessi non e' un parametro.

⭐ **Envelope per chiave**: un contatore che fallisce degrada **la sua** card
(`{"valore": null, "ok": false}`) senza oscurare le altre. Una dashboard mezza
piena e' informazione; una dashboard bianca perche' una query e' andata storta e'
un guasto.

Internamente risolve la config **una volta sola** e la passa al service dei
contatori: la funzione DB non viene chiamata due volte per la stessa richiesta.

## 3. `PUT` e `DELETE` `/api/v1/ui/dashboard/{codice}/preferenza/`

| metodo | fa |
|---|---|
| `PUT` | upsert della preferenza utente — body: `widget` (lista di oggetti) e `dimensione_max` (int), entrambi opzionali |
| `DELETE` | cancella la preferenza: la dashboard **torna al preset**, non si svuota |

La `DELETE` e' il «ripristina predefiniti» della UI: senza preferenza la cascata
riparte dal preset di ruolo/emittente/sistema.

## 4. `POST /api/v1/ui/dashboard/{codice}/preferenza/ignore-preset-update/`

Tombstone del banner **«il preset e' stato aggiornato»**: scrive
`preset_aggiornato_ignored_at = NOW()` sulla preferenza dell'utente. Body vuoto
ammesso.

⚠️ Serve perche' i due fatti convivono: l'utente ha personalizzato la sua
dashboard **e** l'amministratore ha cambiato il preset da cui era partita. Il
banner glielo dice; questo endpoint registra che ha scelto di tenersi la sua —
altrimenti l'avviso tornerebbe a ogni caricamento, che e' il modo piu' rapido di
insegnare a ignorare gli avvisi.

## Dove guardare nel codice

| cosa | dove |
|---|---|
| le quattro view | `apps/ui/api/views_dashboard.py` |
| cascata e risoluzione | `apps/ui/services/dashboard_service.py` (`get_dashboard_config`) |
| contatori | `apps/ui/services/dashboard_contatori_service.py` |
| preferenza e tombstone | `apps/ui/services/dashboard_preferenza_service.py` |

Correlate: [api_ui_liste](api_ui_liste.md) (le liste configurabili, stessa
filosofia di cascata) e [api_ui_admin_personalizzazioni](api_ui_admin_personalizzazioni.md)
(il lato amministrativo di preset e permessi).
