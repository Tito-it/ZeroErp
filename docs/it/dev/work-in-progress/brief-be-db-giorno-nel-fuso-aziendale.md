# Brief BE + DB — Il «giorno» di un filtro è il giorno dell'azienda, non quello UTC

> **Chi scrive:** sessione BE (`dev/backend-tid`), 2026-10-09. **A chi:** Tid (decisione
> sulla forma, §4), poi team DB (§4 R-1) e BE (§4 R-2…R-4).
> **Origine:** un test sul DB vero rosso a mezzanotte e mezza
> (`test_giornale_trasversale_perimetro` 1), verificato su richiesta di Tid durante L2 di
> [piano-be-type-checker.md](piano-be-type-checker.md) (§5.2). Il test era giusto: il difetto è
> nel filtro.
> **Stato:** 🟡 **deciso** (Tid, 2026-10-09: forma R-1 + R-2 accettata; colonne `date` fuori).
> ⏳ In attesa del team DB per **R-1**; il BE (R-2…R-4) parte alla consegna. Censimento BE
> completato il 2026-10-09 (§2).

## 1. Il difetto

Un filtro «dal giorno X al giorno Y» su una colonna `timestamptz` è scritto, in undici sedi
(§2; questa è la forma più comune), così:

```sql
AND colonna >= %s::date
AND colonna <  %s::date + interval '1 day'
```

Il cast di una `date` a `timestamptz` usa il fuso della **sessione**, e la sessione di Django è
**UTC** (`USE_TZ = True`, nessun `TIME_ZONE` in `DATABASES`). Il «giorno» del filtro va quindi
da mezzanotte a mezzanotte **UTC**, cioè dalle 02:00 alle 02:00 italiane d'estate (01:00
d'inverno):

- fra le 00:00 e le 02:00 locali, «oggi» **non contiene** gli eventi appena scritti, che sono
  ancora nel giorno UTC precedente;
- un filtro «il 5 ottobre» mostra gli eventi dalle 02:00 del 5 alle 02:00 del 6, e non quelli fra
  mezzanotte e le 02:00 del 5.

È **la stessa famiglia** che il DB ha già chiuso per la data documento con
`script.fn_data_operativa()`. Il suo commento lo dice con le stesse parole: «la sessione di
Django è UTC… ogni documento nato fra mezzanotte e le 02:00 locali portava la data del giorno
prima (misurato 2026-08-25: 7 fatture su 18 sfasate)». Il fuso dell'azienda è un **dato**,
`config.parameters.SYSTEM_FUSO_ORARIO`, validato in scrittura e mai una costante nel codice.

⚠️ `settings.TIME_ZONE = 'Europe/Rome'` **non** è la soluzione: sarebbe una seconda copia del
fuso, scritta nel codice, che il giorno in cui il parametro cambia diverge in silenzio.

## 2. Dove sta — censimento del 2026-10-09

Censimento **completato** il 2026-10-09 su tutto `backend/apps` (esclusi i test): ogni
confronto con un parametro `%s::date` / `%s::timestamptz`, e ogni confronto non tipato su una
colonna di istante, classificato col tipo della colonna letto dalla doc auto-generata. Sono **11
sedi in 9 file**, in tre forme. Le colonne `date` (`valido_dal`, `valido_al`, `validita`,
`competenza`, `data_documento`) **non** hanno il difetto e restano fuori (decisione di Tid,
2026-10-09).

**Forma A** — `>= %s::date` / `< %s::date + interval '1 day'` su `timestamptz`:

| Sede | Colonna | Che cosa filtra |
| --- | --- | --- |
| `vendite/db/vendite_repository.py` `list_giornale_trasversale` | `quando` | giornale trasversale (osservabilità) |
| `core/db/dbops_repository.py` (≈ riga 722) | `e.occurred_at` | eventi d'errore del diario |
| `core/db/permissions_audit_repository.py` (≈ riga 146) | `valid_from` | storico dei permessi |
| `pratiche/db/pratiche_repository.py` (≈ riga 301) | `p.data_insert` | lista pratiche |
| `magazzino/db/magazzino_repository.py` (≈ riga 961) | `mv.data_mov` | movimenti di magazzino |
| `core/db/email_repository.py` (≈ riga 639) | `el.data_insert` | log email |

| `amm_software/db/amm_software_repository.py` (≈ righe 1405, 1408) | `valid_from` | storico (amministrazione) — **due forme miste** sullo stesso filtro: `>= %s::timestamptz` e `< %s::date + 1 day` |

**Forma B** — un testo-data castato a `timestamptz` (stesso cast nella sessione UTC), e in più
il confine alto **incluso** (`<=`): l'istante della mezzanotte successiva appartiene a due giorni.

| Sede | Colonna |
| --- | --- |
| `core/db/dbops_repository.py` (≈ righe 629-630) | `executed_at` |
| `core/db/maintenance_repository.py` (≈ righe 93-94) | `started_at` |

**Forma C** — una `date` Python passata **senza cast** e confrontata con un `timestamptz`
(PostgreSQL la promuove nella sessione UTC), col «giorno dopo» calcolato in Python da
`core/services/coda_lavori/gestione_service.py` (`data_a + timedelta(days=1)`, ≈ righe 295, 360):

| Sede | Colonna |
| --- | --- |
| `core/services/coda_lavori/repository.py` (≈ righe 622-625) | `data_insert` (coda lavori) |
| `vendite/db/pipeline_repository.py` (≈ righe 2924-2927) | `c.data_insert` (coda di stampa) |

⚠️ Il censimento è **testuale**: trova le forme che conosce. Non esiste un building block
generico che costruisca filtri data per le liste configurabili (verificato), quindi non c'è una
sede nascosta da cui ne nascono altri; ma una forma scritta diversamente sfuggirebbe. È ciò a cui
serve il presidio di §4 R-4.

⭐ Sono **undici copie** della stessa regola («i confini di un giorno»), in tre forme: la regola
del 2 è scaduta da dieci, ed è il motivo per cui sbagliano tutte allo stesso modo.

## 3. Perché il test lo ha visto e la suite no

`test_giornale_trasversale_perimetro` 1 scrive una riga di diario **adesso** e la cerca filtrando
per `date.today()`, che è la data **locale** del processo. Di giorno il giorno locale e quello UTC
coincidono, e il test è verde. A mezzanotte e mezza no. È un test **giusto** che ha incontrato il
caso: non va reso indipendente dall'orario, va corretto il filtro.

## 4. Proposta (da decidere)

| # | Cosa | Chi |
| --- | --- | --- |
| **R-1** | **Una funzione DB per i confini del giorno aziendale**, gemella di `fn_data_operativa`: per esempio `script.fn_inizio_giorno_operativo(p_data date) RETURNS timestamptz` = `p_data::timestamp AT TIME ZONE <SYSTEM_FUSO_ORARIO>`, con lo stesso fail-loud sul fuso (assente, vuoto, sconosciuto → `E_CONFIG_MANCANTE`) e la stessa lettura del default nudo (mai la cascata di override: lo stesso filtro darebbe righe diverse a utenti diversi). ⚠️ `STABLE`, e attenzione al costo: il fuso va letto **una volta** per query, non per riga (la funzione sta nel `WHERE`, sui due confini, non sulla colonna). | team DB |
| **R-2** | **Un building block BE** per il predicato «colonna nel giorno da… al…» (regola del 2, ok Tid): restituisce il frammento SQL e i parametri, con i confini da R-1 (`colonna >= fn_inizio(da) AND colonna < fn_inizio(a + 1)`). Le undici sedi di §2 passano al BB nello stesso giro. | BE |
| **R-3** | **Test sul DB vero** del BB: un evento scritto alle 00:30 locali di un giorno sta in quel giorno, non nel precedente; ai cambi d'ora (ultima domenica di marzo e di ottobre) il giorno ha 23 o 25 ore. Il caso si **costruisce** con un `timestamptz` esplicito, non aspettando la mezzanotte. | BE |
| **R-4** | **Il presidio**: un test che rifiuti `%s::date` confrontato con una colonna `timestamptz` nei repository (o, meglio, che il BB sia l'unica strada), così la settima copia non nasce. | BE |

✅ **Decisioni di Tid, 2026-10-09:**

1. **Forma accettata**: funzione DB (R-1) + building block BE (R-2), con le copie ritirate nello
   stesso giro (regola del 2, ok Tid). Niente calcolo del fuso in Python.
2. **Confermato**: le colonne `date` restano fuori.

➡️ **Al team DB — R-1.** Il nome e la firma li decide il team DB; il BE ha bisogno di: una
`date` in ingresso, il `timestamptz` dell'inizio di quel giorno nel fuso di
`SYSTEM_FUSO_ORARIO` in uscita, fail-loud come `fn_data_operativa`, e il costo del fuso pagato una
volta per query. Un pgTAP sui cambi d'ora (il giorno di 23 e di 25 ore). Alla consegna, il BE
scrive R-2…R-4 sulle undici sedi di §2.

## 5. Fuori da questo brief

- `test_giornale_trasversale_perimetro` resta com'è: è rosso solo nella finestra notturna, e lo
  diventa verde la correzione del filtro, non una modifica del test.
- Le date **mostrate** (formattazione a video, export) sono un'altra materia: le governa
  `locale_formatters`, e qui non si toccano.
