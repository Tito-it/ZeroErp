# Brief DB — Le funzioni che ripianificano a ogni chiamata

> **Chi scrive:** sessione DB (`dev/db-tid`), 2026-10-10. **A chi:** Tid.
> **Origine:** il debito residuo di
> [brief-db-segment-base-commesse-attivita](../work-done/brief-db-segment-base-commesse-attivita.md)
> (§8), archiviato il 2026-10-10. Voce nel registro: **D26** di
> [migliorie-generali-da-test-valutazione](migliorie-generali-da-test-valutazione.md).
> **Stato (2026-10-10):** ⬜ **aperto, non iniziato.** Due decisioni attese (§3).
> **Ricadute BE/FE:** nessuna prevista.

## 1. Cosa ha insegnato il cantiere da cui nasce

Una funzione plpgsql che chiama con un **parametro** una funzione SQL che si
incorpora (`fn_ddt_push_diagnosi` → `fn_partite_merce` → `fn_af_merce_per_riga`)
esegue una query enorme. In modo `auto` la plancache confronta i costi
**stimati**: il piano generico, col parametro sconosciuto, le sembra più caro, e
lei ripianifica a ogni chiamata — ~13-15 ms di sola pianificazione, con piani
personalizzati spesso anche più lenti da eseguire.

La cura applicata lì: `ALTER FUNCTION … SET plan_cache_mode = force_generic_plan`
sulla funzione plpgsql chiamante (`20261010-83` capability del DDT, `-84` lister
dei DDT da spingere), presidiata dal pgTAP
`script/test-fn-available-actions-ddt-piano-generico-v1`. Fatti datati
(2026-10-10, dbdev come app, 56 DDT): capability 1,42 → ~0,6 s; lister per DDT
1,30 → ~0,48 s.

## 2. I due punti aperti

### 2.1 Le altre funzioni con la stessa forma

Il censimento non è stato fatto: le due funzioni curate sono le sole misurate.
Candidate per costruzione: le funzioni plpgsql che chiamano con un parametro una
funzione `LANGUAGE sql` `BEGIN ATOMIC` grande (diagnosi, partite merce,
situazione merce dell'ordine, le capability degli altri documenti, le altre
`fn_list_*_da_pushare`).
Il metodo, già provato: per ciascuna, un ciclo plpgsql di N chiamate come app in
`auto` e con `force_generic_plan` di sessione — se il generico costa molto meno,
la clausola sulla funzione è la cura; se costa uguale, non serve.
⛔ La clausola non si mette «per igiene»: si mette dove la misura mostra il
difetto, e il presidio la pretende solo lì.

### 2.2 Il lister dei DDT senza filtri

`vendite.fn_list_ddt_da_pushare(NULL, NULL, NULL, NULL)` costa ~1,1 s (dbdev
come app, 2026-10-10), uguale in `auto` e in generico: è la diagnosi di tutti i
DDT in una chiamata, non un problema di plancache. Va profilata come query
(`EXPLAIN ANALYZE` del ramo «tutti») prima di dire se e dove si può migliorare.

## 3. Decisioni attese

* **D-1** — fare il censimento del §2.1, e con che perimetro (tutte le capability
  e i lister, o solo le funzioni che il backend chiama in un ciclo).
* **D-2** — profilare il §2.2 ora, o quando il volume dei DDT lo renderà
  visibile.
