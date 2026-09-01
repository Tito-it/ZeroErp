## 📘 Documentazione Concettuale – Tabella `vendite.registri_fatturazione_progressivi`

> 👀 **Vedi anche**
>
**Approfondimento tabelle:**
>
• [vendite.registri_fatturazione](/dbzero/vendite/tabelle/registri_fatturazione)  
> • [vendite.fatture](/dbzero/vendite/tabelle/fatture)  
>
### 🎯 Scopo Principale
(latest review 26-01-2026)
`vendite.registri_fatturazione_progressivi` memorizza i **progressivi di numerazione**
per ciascun registro, anno e serie. E` la base per l’assegnazione del
numero documento in fase di emissione.

⚠️ **Aggiornato il 2026-09-01**: la colonna `mese` è stata **tolta** dalla
chiave. Vedi la sezione in fondo.

---

### Campi chiave (semantica)

* **Registro**: `registro_id`.
* **Periodo**: `anno` — ⚠️ è l'anno del **secchio**, non quello del documento:
  vale `0` quando il registro ha `reset_policy = 'NESSUNA'`, cioè quando il
  contatore non riparte mai. L'anno del documento (`fatture.anno`, `ddt.anno`, …)
  è sempre quello solare, e lo compone `vendite.fn_assegna_numero_documento`.
* **Serie**: `serie` (default stringa vuota).
* **Contatore**: `last_numero`.
* **Stato**: `attivo`.

---

### Note operative

* Il vincolo univoco `(registro_id, anno, serie)` impedisce duplicazioni.
  ⭐ **Ogni asse che sta in questa chiave deve poter stare anche nel vincolo di
  unicità del documento** che riceve il numero, o il contatore consegna numeri
  che il documento non sa ospitare — è l'invariante del cantiere della chiave del
  contatore.
* La tabella e` aggiornata dal processo di numerazione (fase emissione).

---

### 🔄 rev 2026-08-25 — `ultima_data`, la memoria della sequenza

Brief: `brief-db-numerazione-data-documento-e-sequenza` (**DB-7**).

Nuova colonna `ultima_data date NULL`: la data del documento a cui è stato dato
**l'ultimo numero uscito da questa riga di contatore**. La scrive
`fn_get_next_progressivo` a ogni numero emesso, con `GREATEST` — **non arretra
mai**, nemmeno se un documento legittimo portasse una data uguale.

#### ⭐ Perché la memoria sta qui e non su `vendite.fatture`

Il cancello di monotonia deve chiedersi *«qual è la data dell'ultimo numero
emesso su questo sezionale?»*. La risposta si potrebbe cercare in
`vendite.fatture` con un `max(data)` — e sarebbe **sbagliato**: quella tabella ha
la RLS (`rls_fatture_ef_whitelist`, `FOR ALL`) e la funzione che numera è
`SECURITY INVOKER`.

Sotto un perimetro emittente ristretto quel `max()` tornerebbe `NULL`, e un
cancello che legge `NULL` dice **«via libera» proprio quando non sa**. Uno zero —
o un `NULL` — non è un dato: è l'assenza di una risposta.

⭐ Questa tabella **non ha RLS** (verificato su `pg_class.relrowsecurity`): il
dato è sempre completo, per chiunque, è `O(1)`, ed è su una riga che il cancello
ha già bloccato con l'advisory lock e il `FOR UPDATE`. Il problema si elimina
alla radice invece di essere aggirato.

#### ℹ️ `NULL` significa «non è ancora successo»

Una riga di contatore nasce **prima** di aver emesso qualcosa
(`fn_get_next_progressivo` la crea con `last_numero = 0`). Il cancello legge
quel `NULL` come «nessun vincolo da rispettare», ed è corretto.

⚠️ Non è lo stesso `NULL` fail-open descritto sopra: lì era «non lo vedo», qui è
«non è ancora successo».

#### ⚠️ Il cancello legge il massimo ATTRAVERSO GLI ANNI

Non il valore della riga dell'anno corrente. Altrimenti un documento retrodatato
al 31/12 dell'anno scorso finirebbe nel contatore dell'anno scorso e passerebbe
indisturbato, **aprendo un numero in un anno già chiuso**.

⭐ Per la stessa ragione l'advisory lock di `fn_get_next_progressivo` ha perso
l'anno dalla chiave: il perimetro del lock deve coincidere con quello del
controllo.

#### ⛔ La `serie` di una riga deve essere quella che il registro USA

`fn_get_next_progressivo` cerca la riga con la serie **risolta**
(`COALESCE(f.serie, r.serie_default, '')`). Se qualcuno rinomina il
`serie_default` di un registro, le righe di contatore restano sulla serie vecchia
e diventano **orfane**: la numerazione successiva non le trova, ne crea una a
zero e riparte da 1 — con `ultima_data` a `NULL`, cioè **senza pavimento**.

📌 Successo davvero il 2026-08-25 sul registro 5. Diagnosi:

```sql
SELECT r.id, r.codice, COALESCE(r.serie_default,'') AS serie_che_usera, rp.serie
  FROM vendite.registri_fatturazione_progressivi rp
  JOIN vendite.registri_fatturazione r ON r.id = rp.registro_id
 WHERE rp.serie <> COALESCE(r.serie_default, '');   -- righe orfane
```

#### 🔴 rev 2026-09-01 — la colonna `mese` è stata TOLTA

> ~~ℹ️ La colonna `mese` resta, ferma a 0. Toglierla vorrebbe dire rifare due
> `UNIQUE`, un `CHECK` e il corpo di `fn_get_next_progressivo` per due byte — e
> il giorno in cui `MENSILE` servisse davvero, la chiave c'è già.~~
>
> 🔴 **Superata.** Quella frase misurava il costo di toglierla e non il costo di
> **tenerla**, che era più alto.

⛔ **Il difetto: una dimensione dormiente in una chiave è ARMATA, non
inutilizzata.** `mese` stava nella chiave del contatore e **in nessun vincolo di
unicità di nessun documento** — verificato su `fatture`, `ddt`, `ordini`, `resi`
e `commesse`. Era innocua solo perché **inchiodata** in due punti: `v_mese := 0`
nella funzione e un `CHECK` che ammetteva il solo `ANNUALE`.

⇒ Il giorno che qualcuno avesse acceso `MENSILE` — cioè fatto proprio la cosa
per cui la colonna esisteva — il contatore sarebbe ripartito da 1 **ogni mese** e
sarebbero collidati **tutti e cinque** i documenti. E a tenerlo chiuso non era un
vincolo: era una **rinuncia**, che si revoca per distrazione.

⭐ **Se un giorno servirà davvero**, l'asse torna **insieme** alla colonna sui
documenti, dichiarato in `vendite.famiglie_documento` come lo è oggi
`colonna_serie`. Cioè il lavoro vero: tenere la colonna qui non lo anticipava.

⭐ **E togliendola è venuto via anche `uq_registri_progressivi_scope`**, che con
quattro colonne `NOT NULL` aveva i `COALESCE` a no-op ed esprimeva la **stessa
chiave** di `uq_regprog_key`. ⚠️ `dbops.vw_duplicate_indexes` non lo vedeva: il
confronto lavora sulle colonne, e lì una chiave era colonne e l'altra
espressioni — *un duplicato nascosto dietro espressioni che non fanno niente è
invisibile proprio al presidio nato per i duplicati.*

Cantiere: `brief-db-registri-numerazione-chiave-del-contatore`, changeSet
`20260901-07` e `20260901-08`.

---

{% include-markdown "signature-core.md" %}
