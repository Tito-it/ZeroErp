# Brief DB — `DEFAULT_IVA_ID` è l'ultimo parametro che stocca un id, e ora la chiave c'è

> **Destinatario:** team DB (`dev/db-tid`). **Voce unica**, e sblocca la slice
> `F6` del piano
> [brief-be-fe-iva-fase-3-consumatori-risolutore.md](brief-be-fe-iva-fase-3-consumatori-risolutore.md).
>
> 📌 **La richiesta operativa è raccolta con le altre** in
> [brief-db-richieste-aperte-dal-backend.md](brief-db-richieste-aperte-dal-backend.md):
> quello è l'ordine di lavoro, questo è il ragionamento. ⛔ Se le due divergono,
> vale questo — l'elenco rimanda, non ricopia.
>
> **Origine.** Decisione di Tid del 2026-08-31 (`P8` del piano di Fase 3), presa
> a valle di `D28` del cantiere IVA — che è il passo che rende la cosa
> possibile.
>
> **Stato.** 2026-08-31 — verificato sulla **struttura** (`parameters.csv`,
> doc auto-generata di `config.iva`, `linee-guida-sql §6b`). Nessuna misura sui
> dati. Nessun file scritto lato DB.
>
> **Correlati:**
> [config.iva](/dbzero/config/tabelle/iva) ·
> [linee-guida-sql §6b](../../linee-guida-sql.md) ·
> [brief-db-be-iva-risolutore-e-regime-cliente §D28](brief-db-be-iva-risolutore-e-regime-cliente.md)

---

## 1. Il fatto: la guida descrive questa migrazione, e nomina questo parametro

`linee-guida-sql §6b` — *«Riferimenti esterni a tabelle di catalogo (chiave
naturale stabile)»* — porta un **tech debt riconosciuto**, e l'esempio è
letteralmente il nostro:

> *«parametri legacy che oggi stoccano id numerici a tabelle di catalogo che **non
> espongono ancora** una chiave naturale stabile (es. `DEFAULT_IVA_ID` →
> `config.iva.id`). Restano fuori scope del framework finché la tabella target
> non viene dotata della chiave (aggiungere `codice_interno` → il lock
> automatico viene provisionato dal runner → **rinominare il parametro** →
> **aggiungere riga al registry**).»*

⭐ **La condizione sospensiva è caduta.** `D28` (changeSet `20260829-43`) ha dato
a `config.iva` la sua `codice_interno`, con backfill `= codice` e il lock nello
stesso trigger delle due colonne del trattamento. I primi due passi dei quattro
sono **fatti**; restano il terzo e il quarto, che sono DB.

Oggi il seed dice:

```csv
11,DEFAULT_IVA_ID,16,"ID IVA di default per creazione clienti (config.iva.id=16, IVA 22%)",…
```

⛔ Un `16` che vale finché nessuno riseeda `config.iva`. È esattamente ciò che il
principio §6b vieta: *«l'id è dettaglio implementativo soggetto a reseed; la
chiave naturale è il contratto cross-ambiente»*.

---

## 2. La richiesta

| # | Cosa | Nota |
| --- | --- | --- |
| **1** | **Rinominare** il parametro — `DEFAULT_IVA_ID` → `DEFAULT_IVA` | ⚠️ Il suffisso `_ID` diventerebbe una **bugia** appena il valore è un codice, ed è la specie di nome che poi qualcuno rilegge come intero. La guida prescrive proprio «rinominare», non solo cambiare il valore |
| **2** | **Cambiare il valore** da `16` al `codice_interno` corrispondente, e riscrivere la descrizione (che oggi cita `config.iva.id=16`) | La descrizione è la sede in cui il debito è rimasto leggibile: va aggiornata insieme, o afferma il falso |
| **3** | **Riga nel registry** `config.parameter_fk_surrogate`: `code_pattern` EXACT su `DEFAULT_IVA`, target `config.iva.codice_interno` | ⭐ Nessun codice DB nuovo: il dispatcher `trgfn_parameters_fk_surrogate_dispatch` esiste già e da quel momento **valida il valore** — un codice IVA inesistente viene rifiutato con `E_PARAMETER_DEFAULT_VALUE_INVALID` invece di restare a marcire |

📌 **E il registry è il vero guadagno**, più della chiave in sé: oggi nessuno
verifica che quel `16` punti a qualcosa. Con la riga nel registry il parametro
smette di poter mentire.

---

## 3. La metà BE, che va nello stesso giro

⛔ **Non prima**, o il lettore si rompe. Il consumatore è **uno solo**, verificato:
`apps/catalogo/services/catalogo_service.py` (~1422-1441), il form-defaults
dell'**articolo** — che è la domanda giusta a cui quel parametro risponde
(l'aliquota ordinaria della merce, cioè lo stadio A del risolutore).

Oggi fa `ParameterService.get_defaults(["DEFAULT_IVA_ID"])` e casta a intero.
Dopo leggerà `DEFAULT_IVA` e risolverà l'id con
`apps/core/db/_helpers.resolve_config_id_by_codice_interno`, che **esiste già** ed
è il building block previsto per questo.

⚠️ **Il lettore sbagliato è già morto**: fino al 2026-08-29 questo parametro lo
leggeva anche la creazione cliente, ed è caduto con `S1` della Fase 1 (`D7-bis`,
l'IVA non appartiene al cliente). Quello che resta è l'unico corretto — motivo in
più per sistemarlo invece di ritirarlo.

---

## 4. Presidio atteso

* ⭐ **Il test che discrimina, e non è «il parametro si legge»**: con un valore
  che **non esiste** in `config.iva.codice_interno`, il seed deve essere
  **rifiutato** — è ciò che la riga di registry compra, e senza quella prova non
  si sta verificando il registry ma solo il rename;
* il form-defaults dell'articolo continua a proporre la stessa aliquota di prima
  (il rename non deve cambiare il comportamento a video);
* ⚠️ e il **gemello negativo**: cercare `DEFAULT_IVA_ID` per nome nudo in
  `backend/` e nei seed → zero occorrenze. Un rename che lascia indietro un
  lettore non fallisce: legge un parametro che non c'è più e prende il ripiego.

---

## 5. Fuori perimetro, dichiarato

* ⛔ **Il ritiro del parametro.** Era stato ipotizzato dal piano di Fase 1 («se il
  seed vada tolto lo decide il team DB, a Fase 3 chiusa»): la risposta è **no**,
  il parametro serve e resta — cambia solo come referenzia il catalogo;
* 📌 **Gli altri parametri legacy** che stoccano id. La guida dice
  *«migrazione tracciata caso per caso, non bulk»*, e questo brief tratta il caso
  che `D28` ha appena sbloccato. Nessun altro.

---

## 6. Diario

| Data | Cosa |
| --- | --- |
| 2026-08-31 | Brief nato eseguendo `F6` del piano di Fase 3 e scoprendo che la voce **non è BE**: tre passi su quattro sono seed DB, e il piano la classificava come lavoro di backend. ⭐ La condizione che la bloccava è caduta con `D28` del cantiere IVA, che ha dato a `config.iva` la sua `codice_interno` — la guida §6b nominava **questo parametro** come esempio del debito e descriveva **questi quattro passi** come la via d'uscita |
