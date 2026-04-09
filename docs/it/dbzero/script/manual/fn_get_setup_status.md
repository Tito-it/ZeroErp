# fn_get_setup_status

### Scopo

Restituisce in un singolo `jsonb` lo **stato di setup** del modello operatore ↔ emittente fiscale, pensata per essere chiamata dal frontend (banner di amministrazione operatori) per il pattern **"advise, don't enforce"** introdotto dal refactor del 2026‑04‑08.

Il banner UI legge l'output e, se `operatori_non_assegnati > 0`, mostra un suggerimento informativo all'admin senza bloccare nulla.

## Schema

`script` (cross‑dominio).

## Firma

```sql
script.fn_get_setup_status() RETURNS jsonb
```

Nessun parametro.

## Output

`jsonb` con 5 chiavi:

| Chiave                    | Tipo     | Significato                                                                                  |
| ------------------------- | -------- | -------------------------------------------------------------------------------------------- |
| `emittenti_attivi`        | `bigint` | Numero di emittenti fiscali con `attivo = true`.                                             |
| `operatori_totali`        | `bigint` | Operatori attivi (utente Django attivo + risorsa umana attiva + ruolo non DISABILITATO).     |
| `operatori_assegnati`     | `bigint` | Operatori con almeno una riga in `config.user_emittenti_fiscali`.                            |
| `operatori_admin_globali` | `bigint` | Operatori `ruolo_sistema = ADMIN` **senza** riga in `user_emittenti_fiscali`.                |
| `operatori_non_assegnati` | `bigint` | `max(operatori_totali - operatori_assegnati, 0)`.                                            |

Esempio output:

```json
{
  "emittenti_attivi":         3,
  "operatori_totali":         12,
  "operatori_assegnati":      8,
  "operatori_admin_globali":  1,
  "operatori_non_assegnati":  4
}
```

## Caratteristiche

* **STABLE**, **`LANGUAGE plpgsql`** (wrapper) + singola query CTE interna con `COUNT(*) FILTER` per minimizzare il numero di scan (2 scan totali: uno su `emittenti_fiscali`, uno sul join `risorse_umane_auth_user × django.auth_user × user_emittenti_fiscali`).
* **Perché plpgsql e non sql**: in CI Liquibase gira prima di `python manage.py migrate`, quindi `django.auth_user` non esiste ancora al momento del CREATE. `LANGUAGE sql` parserebbe immediatamente e fallirebbe con `relation does not exist`. `LANGUAGE plpgsql` invece risolve i riferimenti SQL embedded solo al primo invoke (deferred parsing), quando Django ha già completato `migrate`. Il wrapper plpgsql aggiunge solo `BEGIN ... INTO v_result ... RETURN v_result ... END`, la query CTE interna è invariata.
* **Read‑only**: nessun side effect.
* **Reinterpretazione `ADMIN`**: il refactor distingue gli admin globali dagli admin di emittente in base alla **presenza/assenza** di una riga in `user_emittenti_fiscali`. Questa funzione conta solo gli admin globali (assenza di riga), perché sono i candidati naturali per la "promozione" a operatore di emittente.

## Dipendenze

* `anagrafiche.emittenti_fiscali` — conteggio EF attivi
* `anagrafiche.risorse_umane_auth_user` — bridge HR-auth con `ruolo_sistema`
* `django.auth_user` — stato `is_active`
* `config.user_emittenti_fiscali` — associazioni esistenti

## Chi la chiama

* Frontend admin (composable `useSetupStatus()` previsto da [refactor WIP §9.5](/dev/work-in-progress/refactor-operatore-emittenti)) tramite endpoint `GET /api/v1/amm-software/setup-status/`.
* Eventuali job di reportistica diagnostica.

## Esempio

```sql
SELECT script.fn_get_setup_status();
```
