# Brief DB — Ritirare `E_VENDITE_RIGA_GIA_PROPAGATA`

> **Chi scrive:** sessione BE (`dev/backend-tid`), 2026-10-09. **A chi:** team DB
> (`dev/db-tid`).
> **Origine:** chiusura di
> [brief-db-riga-listino-propagata-dalla-commessa](../work-done/brief-db-riga-listino-propagata-dalla-commessa.md)
> (§7). **Decisione:** di Tid, 2026-10-09: la regola «propagata» ha una sede sola,
> il guard DB.
> **Stato:** ⏳ da fare (DB). Il BE è già fatto: niente da attendere.

## 1. Che cosa è cambiato

La rettifica controllata N6 di una riga di listino
(`listini_service.fn_rettifica_controllata_riga`) controllava in Python la stessa
regola di `vendite.trgfn_listini_righe_guard_stato` («una riga di listino citata da
una riga di commessa o da un'attività fatturabile non si modifica») e rifiutava con
un codice suo, `E_VENDITE_RIGA_GIA_PROPAGATA`. Il guard rifiuta con
`E_RIGA_LISTINO_PROPAGATA`, quindi c'erano due sedi e due codici per la stessa
regola.

Dal 2026-10-09 il controllo Python non c'è più
(`ListiniRepository.check_riga_propagata` è stato tolto). Il service scrive, e se
il guard rifiuta porta al chiamante il codice del DB
(`ErrorManager.raise_from_database_error`). L'override UI `show_toast_error` è
passato da `E_VENDITE_RIGA_GIA_PROPAGATA` a `E_RIGA_LISTINO_PROPAGATA`, quindi
l'operatore vede lo stesso toast di prima.

## 2. Richiesta

| # | Cosa |
| --- | --- |
| **R-1** | `E_VENDITE_RIGA_GIA_PROPAGATA` in `80_data/sql/config/codici_errore.csv`: `obsoleto_dal = 2026-10-09` e nota «RITIRATO», sul modello di `E_CONTRATTO_LISTINO_SENZA_VERSIONE_ATTIVA` (anche lì un controllo Python che ripeteva una regola del DB). Il messaggio in `messaggi_errore.csv` resta, perché il diario deve restare leggibile. |

Nessuna funzione DB nomina il codice, quindi niente da toccare in `20_code`.

## 3. Ricaduta BE (dopo la consegna)

Rigenerare `error_policies_generated.py` / `error_messages_fallback.py` **solo**
con il DB allineato a git. ⚠️ Oggi (2026-10-09) il DB di sviluppo è più avanti di
git per altri lavori (sesso, valore numerico non finito): i due presidi di
divergenza sono rossi per quelli, non per questo brief.
