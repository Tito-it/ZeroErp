# generazione_service (Django)

## Scopo

Servizio per generazione cross-pratica: regole applicabili, generazione manuale e lookup pratiche generate.

## Contesto

Il modulo vive in `apps/pratiche/services/generazione_service.py`. Gestisce la generazione **manuale** di pratiche (regole con `auto = false`). La generazione **automatica** (regole con `auto = true`) e' gestita interamente dal trigger DB `trgfn_flussi_generazione` al completamento del flusso.

Utilizza due repository:
- `PraticheRepository` per lettura flussi
- `GenerazioneRepository` per regole, generazione e lookup pratiche generate

## Input

- `flusso_id` (`int`, obbligatorio, `> 0`)
- `regola_id` (`int`, obbligatorio per generazione manuale, `> 0`)

## Output

| Funzione | Input | Output | Descrizione |
|---|---|---|---|
| `genera_pratica_manuale(flusso_id, regola_id)` | flusso_id, regola_id (entrambi > 0) | `int` (pratica_id) | Genera pratica manuale invocando `fn_genera_pratica_da_flusso` |
| `get_regole_applicabili(flusso_id)` | flusso_id (> 0) | `list[RegolaGenerazioneRow]` | Regole attive per il template del flusso |
| `get_pratiche_generate(flusso_id)` | flusso_id (> 0) | `list[PraticaRow]` | Pratiche con `flusso_origine_id = flusso_id` |

## Regole

- `genera_pratica_manuale`: wrappata in `@transaction.atomic()`.
- Verifica esistenza flusso prima di generare; se non trovato → `E_FLUSSO_NOT_FOUND`.
- `get_regole_applicabili`: se il flusso non ha `template_flusso_id` → lista vuota.
- Tutte le funzioni validano `flusso_id > 0` e `regola_id > 0`.

## Dipendenze DB

- `pratiche.flussi` (verifica esistenza, lettura template_flusso_id)
- `pratiche.regole_generazione` (regole configurate per template)
- `pratiche.fn_genera_pratica_da_flusso(flusso_id, regola_id)` (generazione effettiva)
- `pratiche.pratiche` (lookup pratiche generate via flusso_origine_id)

## Note di migrazione

- La generazione automatica (`auto = true`) non passa dal backend: e' gestita dal trigger DB `trgfn_flussi_generazione` che si attiva quando `stato_id` cambia a `COMPLETATO` e l'esito corrisponde a `esito_richiesto` della regola.
