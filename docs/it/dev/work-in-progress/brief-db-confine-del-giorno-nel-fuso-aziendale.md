# Brief DB — Il confine del giorno nel fuso dell'azienda

> **Chi scrive:** sessione BE (`dev/backend-tid`), 2026-10-09. **A chi:** team DB; poi BE (§5).
> **Origine:** test CI `test_giornale_trasversale_perimetro.test_il_giornale_mostra_solo_l_emittente_di_chi_legge`,
> rosso a intermittenza.
> **Stato:** 📝 **da fare** — un building block DB (§4), poi l'adozione BE (§5).

## 1. La regola, che il modello ha già

Il giorno di un fatto si legge **nel fuso dell'azienda**, e il fuso è un **dato**:
`config.parameters.SYSTEM_FUSO_ORARIO`. Lo dice già `script.fn_data_operativa()`: «la data di
oggi NEL FUSO DELL'AZIENDA, non in quello della sessione», «mai un ripiego a UTC», fail-loud se il
parametro manca, è vuoto o non è riconosciuto.

Quella funzione risponde a una domanda sola, *che giorno è oggi*. Manca la domanda gemella che
ogni filtro «dal… al…» pone: **quando comincia il giorno D**. Senza un building block, ogni
filtro la risolve da sé, e la risolve nel fuso della **sessione**.

## 2. Il difetto

Un filtro per giorno su una colonna `timestamptz` è scritto così:

```sql
col >= %s::date  AND  col < %s::date + interval '1 day'
```

PostgreSQL converte la data in mezzanotte **nel `TimeZone` della sessione**, e le sessioni del
progetto sono due: il **backend in UTC** (Django con `USE_TZ`), psql/Liquibase in Europe/Rome.
L'operatore sceglie le date nel calendario dell'azienda. ⇒ Dal backend il giorno D va da
00:00 UTC a 00:00 UTC, cioè dalle 02:00 alle 02:00 di Roma (dalle 01:00 d'inverno): **ciò che
succede tra mezzanotte e le 2 finisce nel giorno prima**, senza nessun errore. Un filtro «oggi»
alle 00:30 non mostra niente, e il fatto delle 00:30 di ieri risulta di due giorni fa.

⭐ Non dipende dai dati né dalla popolazione: è la struttura del predicato. Vale per ogni
installazione il cui fuso non è UTC, a ogni ora che cade tra la mezzanotte locale e la
mezzanotte UTC.

**Fatto datato (non è il motivo):** il 2026-10-08 i cinque run di CI-Validate partiti tra le
22:54 e le 22:58 UTC (cioè tra le 00:54 e le 00:58 del 9 a Roma) hanno fallito su quel test,
mentre i run delle 12:00, 15:57 e 21:15 UTC dello stesso giorno l'avevano passato. Il test
scrive una riga di diario e chiede il giornale di «oggi»: Django mette `TZ=Europe/Rome` nel
processo (`date.today()` = 9), la sessione DB è in UTC (il 9 parte dalle 00:00 UTC), e la riga
delle 22:58 UTC dell'8 resta fuori. Il test ha ragione, e **non va corretto**: fargli usare la
data UTC lo farebbe tornare verde nascondendo il difetto.

## 3. Dove vive oggi (inventario BE, 2026-10-09)

Tutte colonne `timestamp with time zone` (lette dalla doc auto-generata):

| # | Punto | Colonna | Forma |
| --- | --- | --- | --- |
| 1 | `vendite/db/vendite_repository.py` — giornale trasversale | `script.vw_giornale_entita.quando` | `>= %s::date`, `< %s::date + 1 day` |
| 2 | `core/db/dbops_repository.py` — registro errori | `dbops.error_log.occurred_at` | idem |
| 3 | `core/db/permissions_audit_repository.py` — audit permessi | `storico.*.valid_from` | idem |
| 4 | `amm_software/db/amm_software_repository.py` — storia accessi | `storico.*.valid_from` | `>= %s::timestamptz`, `< %s::date + 1 day` |
| 5 | `core/db/email_repository.py` — log email | `config.email_log.data_insert` | `>= %s::date`, `< %s::date + 1 day` |
| 6 | `pratiche/db/pratiche_repository.py` — lista pratiche | `pratiche.pratiche.data_insert` | idem |
| 7 | `magazzino/db/magazzino_repository.py` — movimenti | `magazzino.movimenti.data_mov` | idem |
| 8 | `catalogo/db/catalogo_repository.py` — lista articoli | `catalogo.articoli.data_insert` | `col::date >= %s` / `<= %s` (il `::date` è nel fuso della sessione) |
| 9 | `core/db/maintenance_repository.py` — log dei job | `maintenance.job_run_log.started_at` | `>= %s::timestamptz`, **`<=`** `+ 1 day` (anche il confine superiore incluso: la mezzanotte del giorno dopo entra) |
| 10 | `core/services/coda_lavori/repository.py` — coda lavori | `data_insert` | `>= %s` / `< %s` con `date` Python (+1 giorno nel service) |
| 11 | `vendite/db/pipeline_repository.py` — coda | `c.data_insert` | idem |

⚠️ Sono le forme **trovate nel backend**. Le stesse vanno cercate nel codice DB (funzioni e
viste che fanno `::date` su un `timestamptz`, o che confrontano un `timestamptz` con una
`date`): quella ricerca spetta al team DB.

## 4. Che cosa si chiede

1. **Un building block**, per esempio `script.fn_inizio_giorno_operativo(p_giorno date) RETURNS
   timestamptz`: la mezzanotte di `p_giorno` nel fuso `SYSTEM_FUSO_ORARIO`
   (`(p_giorno::timestamp) AT TIME ZONE <fuso>`).
   * `STABLE`, come `fn_data_operativa`: valutata una volta per istruzione, il predicato
     `col >= script.fn_inizio_giorno_operativo(%s)` resta servito dagli indici per tempo (P-3).
   * ⭐ **Regola del 2:** la lettura e la validazione del fuso (assente, vuoto, non
     riconosciuto → fail-loud) oggi stanno in `fn_data_operativa`. Con una seconda funzione
     diventano due copie: si estrae la lettura in una sede unica (es.
     `script.fn_fuso_operativo()`) e la usano entrambe, nello stesso giro.
   * NULL in ingresso → NULL in uscita: i filtri sono opzionali (`%s IS NULL OR …`).
2. **pgTAP** che provi il confine **costruendolo**, non leggendo l'ora corrente: un istante alle
   23:30 UTC del giorno D-1 (= 01:30 del giorno D a Roma, fuso del parametro) appartiene al
   giorno D. E il caso d'inverno (offset +1) accanto a quello d'estate (+2): i confini cambiano
   col cambio d'ora.
3. **Il tuo inventario** del §3 lato DB (punto ⚠️ sopra), con l'esito nel brief di risposta.

## 5. Lato BE, quando il §4.1 è applicato

* Gli 11 punti del §3 passano a una forma sola:
  `col >= script.fn_inizio_giorno_operativo(%s)` e
  `col < script.fn_inizio_giorno_operativo(%s + 1)`. ⭐ Regola del 2 anche qui: la coppia di
  condizioni diventa un building block del backend, registrato nel catalogo, invece di undici
  copie della stessa frase.
* Ogni punto con il **suo test** sul DB vero (memoria `feedback_bb_legge_non_trasporta`: un
  building block unifica la lettura, non il trasporto).
* ⛔ Il fuso **non** si calcola in Python da `settings.TIME_ZONE`: sarebbe una seconda copia del
  dato, che diverge da `config.parameters` il giorno in cui uno dei due cambia.
* Il test rosso a intermittenza resta così com'è: torna verde a ogni ora quando il §5 è fatto.
