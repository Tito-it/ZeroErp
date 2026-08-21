## 📘 Documentazione Concettuale – Tabella `magazzino.movimenti`

> 👀 **Vedi anche**
>
Approfondimento tabelle:
> • [magazzino.causali](/dbzero/magazzino/tabelle/causali)
> • [magazzino.costo_medio](/dbzero/magazzino/tabelle/costo_medio)
> • [magazzino.magazzini](/dbzero/magazzino/tabelle/magazzini)
>
Approfondimento viste:
> • [magazzino.vw_giacenza](/dbzero/magazzino/views/vw_giacenza)

---
### 🎯 Scopo Principale

(rev 2026-08-21)

**Il libro mastro del magazzino.** È l'unica scrittura che conta: giacenze e valori non sono
dati autonomi, sono **derivati** da qui.

È ciò che rende il magazzino ricostruibile — un saldo che non torna si spiega risalendo ai
movimenti, e non esiste un posto dove «correggere la giacenza» senza lasciare traccia.

Ogni riga porta articolo, magazzino, causale, quantità, costo unitario, data, ed
eventualmente lotto, seriale, ubicazione di partenza e di arrivo.

---

### 🔴 Difetto bloccante: oggi si possono registrare **solo trasferimenti**

```sql
chk_mag_movimenti_da_destinazione_distinti
  CHECK (magazzino_id <> magazzino_id_dest
         AND magazzino_id      IS NOT NULL
         AND magazzino_id_dest IS NOT NULL)
```

Il vincolo pretende che **`magazzino_id_dest` sia sempre valorizzato**. Ma la colonna è
dichiarata **`nullable`**, e un carico da acquisto o uno scarico da vendita **non hanno** un
magazzino di destinazione.

Verificato il 2026-08-21 valutando l'espressione:

| Caso | Il CHECK vale | Esito |
|---|---|---|
| carico semplice (`dest` = `NULL`) | `false` | **RIFIUTATO** |
| trasferimento (`dest` = altro magazzino) | `true` | passa |

⚠️ In PostgreSQL un CHECK passa se è `TRUE` **o** `NULL`; qui la congiunzione con
`IS NOT NULL` lo porta a `FALSE`, non a `NULL`. Il movimento più comune del magazzino — il
carico — **non è inseribile**.

È latente solo perché la tabella è **vuota**: il dominio non è mai stato avviato. Sarebbe il
primo errore al primo giorno di esercizio.

**La forma che esprime l'intenzione** — la destinazione serve ai soli trasferimenti, e quando
c'è dev'essere diversa dall'origine:

```sql
CHECK (magazzino_id_dest IS NULL OR magazzino_id <> magazzino_id_dest)
```

⭐ Non è una forma inventata: è **quella che il vincolo gemello sulle ubicazioni usa già** sulla
stessa tabella (`chk_mag_movimenti_ubi_from_to_diff`). «Se il valore c'è, dev'essere diverso»,
non «il valore ci dev'essere». `magazzino_id` non ha bisogno del proprio `IS NOT NULL`: la
colonna è già dichiarata `NOT NULL`, e ripeterlo nel CHECK è la ridondanza da cui è nato il
difetto.

✅ **Corretto da `00_schema/magazzino/20260821-10`**, e presidiato da
`db/pgtap/magazzino/test-movimenti-vincoli-v1.sql` — che prima non esisteva: **nessun pgTAP
toccava questa tabella**, ed è il motivo per cui il difetto ha potuto restare invisibile.

⚠️ Il changeSet **allarga**: ammette tutto ciò che ammetteva prima, più i movimenti senza
destinazione. Non può quindi invalidare righe esistenti.

---

### ⚠️ Il segno della causale non è legato al segno della quantità

`magazzino.causali.segno` vale `+1` o `-1` (`CARICO_ACQ` +1, `SCARICO_VEN` -1, …), e
`magazzino.vw_giacenza` calcola la giacenza con un puro `sum(qta)`.

Perché il conto torni, `qta` deve quindi arrivare **già firmata**, coerente con la causale. Il
CHECK sulla quantità è `qta <> 0` — non `qta > 0` — il che conferma l'intenzione.

⚠️ Ma **nulla lo garantisce**: nessun vincolo e nessun trigger legano il segno di `qta` al
`segno` della causale. Un `CARICO_ACQ` con `qta = -5` è oggi scrivibile, e farebbe **calare**
la giacenza pur essendo registrato come carico.

Oggi la coerenza è affidata a chi scrive.

⭐ **Le due strade per chiuderlo — un CHECK che leghi i due segni, oppure un trigger che derivi
`qta` — sono discusse in [magazzino.causali](/dbzero/magazzino/tabelle/causali)**, dove vive la
colonna `segno`: lì c'è il confronto fra le due, con le conseguenze di ciascuna per chi scrive
un movimento. Va deciso **prima** del primo movimento reale.

---

### Le reti che invece ci sono

* `chk_mag_movimenti_qta_non_zero` — un movimento a quantità zero non ha significato;
* `chk_mag_movimenti_ubi_from_to_diff` — ubicazione di partenza e arrivo non coincidono
  (⭐ scritto **correttamente** con i `NULL` ammessi: `IS NULL OR ... <> ...`, la forma che
  manca al vincolo sui magazzini);
* quattro guard `require_attivo` su articolo, causale, magazzino e unità di misura;
* `tx_id`, audit e **storicizzazione** (`trg_movimenti_z90_storico_upd_dlt`): il ledger è
  archiviato a ogni modifica.

---

{% include-markdown "it/dbzero/magazzino/_dominio-magazzino.md" %}

---

{% include-markdown "signature-core.md" %}
