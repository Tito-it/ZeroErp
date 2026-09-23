# fn_veste_corrente

### 🎯 Scopo Principale

Restituisce la **veste** della sessione corrente (operatore, cliente del portale, …) per le funzioni che configurano le schermate: liste, dashboard, ricerca libera. La legge dalla variabile di sessione `app.ruolo_applicativo`, che imposta l'autenticazione.

## Schema

`ui`

## Firma

```sql
ui.fn_veste_corrente() RETURNS config.ruolo_applicativo
```

## Risultato

| Variabile di sessione | Risultato |
|---|---|
| un valore valido (es. `OPERATORE`) | quella veste |
| assente o vuota | `NULL` |
| un valore che non è una veste (errore di configurazione) | `NULL`, **senza errore** |

`NULL` significa **«tutte le vesti dell'utente»**: chi lo riceve considera i profili d'accesso di tutte le sue identità. Una schermata non deve smettere di aprirsi per una variabile di sessione scritta male.

⚠️ **È una regola di presentazione, non di permesso.** Le funzioni di `script` che decidono se un accesso è consentito (per esempio `fn_resolve_livello_area`) fanno il contrario: con una veste non riconosciuta **negano**. Questa funzione non va usata per decidere un accesso.

## Caratteristiche

- **STABLE**: non modifica dati.

## Chi la usa

- [`ui.fn_resolve_lista_config`](/dbzero/ui/funzioni/fn_resolve_lista_config)
- [`ui.fn_resolve_dashboard_config`](/dbzero/ui/funzioni/fn_resolve_dashboard_config)
- [`ui.fn_lista_colonne_ricerca_full`](/dbzero/ui/funzioni/fn_lista_colonne_ricerca_full)
