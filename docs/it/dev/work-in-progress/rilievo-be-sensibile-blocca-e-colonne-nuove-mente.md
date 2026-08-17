# Rilievo BE → DB — `sensibile = t` non è un'etichetta: nasconde. E il contatore delle colonne nuove non se ne accorge

> **Tipo**: rilievo al team DB · **Data**: 2026-08-17 · **Da**: BE ·
> **Destinazione**: `dev/db-tid` · **Stato**: due difetti, uno già aggirato lato
> seed, l'altro aperto
>
> **Origine**: applicato il seed di
> [brief-db-dash-competenza-gruppi-cliente-e-ricerca.md](brief-db-dash-competenza-gruppi-cliente-e-ricerca.md)
> §5.4, la colonna **Codice BA compariva** nel pannello «Personalizza colonne» e
> **Id fiscale no** — pur essendo entrambe nel catalogo, entrambe `attivo = t`,
> entrambe sulla stessa lista. Il pannello continuava però a segnalare che
> c'erano colonne nuove. Rilevato in app da Tid.

---

## 1. Difetto A — la premessa di D-4 è falsa

Il brief DB, §4 D-4, dichiara:

> **`sensibile = t` sull'id fiscale**: il flag alimenta il tag nel pannello di
> personalizzazione (`ListaColonneModal.vue`). **Non nasconde nulla —
> etichetta, non protezione**. Se un giorno servisse restringere davvero, la
> sede è `ui.lista_colonna_permesso`, non questo flag.

**Non è così.** `ui.fn_resolve_lista_config` §5 calcola il livello effettivo:

```sql
COALESCE(
  v_permessi ->> (elem ->> 'codice'),
  CASE WHEN lc.sensibile THEN 'BLOCCATO' ELSE 'TUTTO' END
) AS livello_eff
```

…e poche righe dopo:

```sql
WHERE livello_eff <> 'BLOCCATO'
```

Il commento della funzione lo dice a parole: *«sensibile=TRUE senza grant
esplicito: BLOCCATO»*, *«colonne BLOCCATE: rimosse»*.

Quindi `sensibile = t` **senza una riga in `ui.lista_colonna_permesso`** non
mette un tag: **toglie la colonna dalla configurazione risolta**, per chiunque.
Non è nascosta all'operatore sbagliato — è invisibile a tutti, e resta tale
finché qualcuno non semina i grant. È l'esatto opposto di «disponibile e spenta»,
che era l'obiettivo dichiarato di D-4.

⚠️ Fail-closed è la scelta giusta per la funzione. Il difetto è nel **brief**,
non nel DB: ha scelto un flag descrivendone un effetto che quel flag non ha.

### Cosa ho fatto lato seed

Riga 477 del CSV portata a **`sensibile = f`**, e la ragione è che l'obiettivo di
D-4 era la disponibilità, non la protezione. L'identificativo fiscale è il dato
stampato su ogni fattura: se un giorno va davvero ristretto, la sede è
`ui.lista_colonna_permesso` — che è **esattamente ciò che D-4 già diceva**, solo
partendo dal presupposto sbagliato che il flag non bastasse a bloccare.

⛔ **Serve un `liquibase update`** per riallineare la riga: il mirror è
`runOnChange`, ma finché non gira, a DB `sensibile` resta `t` e la colonna resta
invisibile.

**Se invece il team DB ritiene che l'id fiscale vada protetto davvero**, la
strada è l'opposta: riportare `sensibile = t` **e** seminare i grant in
`ui.lista_colonna_permesso` per i profili che devono vederlo — altrimenti si
ottiene una colonna a catalogo che nessuno può accendere. È una decisione di
merito, non tecnica: la lascio a voi. **Non si può però lasciare `t` senza
grant**, che è lo stato di oggi.

---

## 2. Difetto B — `colonne_nuove` conta ciò che poi viene rimosso (APERTO)

Questo è il pezzo che ha reso il sintomo incomprensibile, ed è **nel DB**, non
nel brief.

In `fn_resolve_lista_config` l'ordine è:

| Passo | Cosa fa |
| --- | --- |
| §3 (merge) | aggiunge le colonne di catalogo assenti dal preset, con `visibile = FALSE`, e **conta**: `COUNT(*)::INTEGER INTO v_colonne_nuove` |
| §5 (permessi) | calcola `livello_eff` e **rimuove** le colonne `BLOCCATO` |

`v_colonne_nuove` è calcolato **prima** del filtro e **non viene decrementato**
quando una colonna cade. Il risultato è un `colonne_nuove` che conta anche le
colonne che la funzione stessa ha appena tolto dall'array `colonne`.

**Effetto a video**: il badge del pannello di personalizzazione annuncia colonne
nuove, l'operatore apre, e non ci sono. Non ha modo di capire se sta cercando
male, se è un guasto, o se la colonna esiste e non gli è concessa. Nel caso di
oggi: **due colonne aggiunte, una visibile, e il contatore che continuava a
segnalare** — è il pezzo che ha fatto dire a Tid *«la cosa strana è che mi indica
ancora una personalizzazione colonna ma non vedo la seconda»*.

⚠️ Il difetto è **latente su ogni lista**, non solo su questa: si manifesta
ovunque esista una colonna `sensibile = t` senza grant. Oggi non si vedeva
perché nessuno ne aveva ancora seminata una.

### Le due direzioni possibili

Non scelgo io, ma vanno distinte perché dicono due cose diverse all'operatore:

1. **contare solo ciò che sopravvive** — `colonne_nuove` diventa il numero di
   colonne che l'operatore può davvero accendere. Coerente col badge, che
   promette un'azione possibile;
2. **esporre il perché** — tenere il conteggio pieno e aggiungere un campo
   («N nuove, di cui M non concesse»), così una colonna esistente ma non
   accessibile si distingue da una che non esiste. Più informativo, più lavoro.

La prima chiude il difetto; la seconda chiude anche la domanda *«perché non la
vedo?»*, che è quella che l'operatore si fa davvero.

---

## 3. Nota di metodo

I due difetti hanno la stessa forma, e vale la pena nominarla: **un dato
dichiarato e un dato usato che non coincidono.** Il brief dichiarava un flag
descrittivo e il DB lo usa come cancello; la funzione dichiara un conteggio di
colonne nuove e ne consegna uno che comprende colonne che non consegna. In
entrambi i casi nulla va in errore — semplicemente qualcosa non compare, ed è la
classe di difetto che si scopre solo usando l'applicazione.

---

## 4. Riferimenti

| Cosa | Dove |
| --- | --- |
| Livello effettivo e rimozione delle BLOCCATE | `docs/it/dbzero/ui/funzioni/fn_resolve_lista_config.md` §5 |
| Conteggio colonne nuove (prima del filtro) | stessa funzione, §3 — `INTO v_config_colonne, v_colonne_nuove` |
| Decisione D-4 con la premessa sbagliata | [brief-db-dash-competenza-gruppi-cliente-e-ricerca.md](brief-db-dash-competenza-gruppi-cliente-e-ricerca.md) §4 |
| Riga di seed corretta | `db/changelog/migrations_v2/80_data/sql/ui/lista_colonna.csv`, id 477 |
