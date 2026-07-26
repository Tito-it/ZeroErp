# Brief DB — Bonifica dei pgTAP rotti dal guard sorgente polimorfa

> **Tipo**: brief operativo DB (debito tecnico) · **Target**: `dev/db-tid` ·
> **Data**: 2026-07-26 · **Owner**: Tid
> **Stato**: 🔵 **DA PIANIFICARE** — non urgente, **nessun difetto di prodotto**:
> è la suite di test che è rimasta indietro rispetto a un guard corretto.
> **Priorità**: 🟢 BASSA come rischio, 🟠 MEDIA come **costo ricorrente** (vedi §4).
>
> **Origine**: rilevato ripetutamente durante le slice del 2026-07-24/26
> (porta oneri, guard uscita commessa, chiusura ri-consegna): ogni volta che si
> esegue una batteria di pgTAP su `vendite`, una parte fallisce per **questa
> stessa causa**, estranea alla slice in lavorazione.

---

## 1. Il sintomo

Molti pgTAP di `db/pgtap/vendite/` (stima corrente **~60**, da censire con
precisione — §3) falliscono con:

```text
ERRORE: Chiave sorgente in formato non valido per il key_selector del tipo.
        (atteso uuid, ricevuto SRC-CM-1bc19e109627)
```

Il fallimento avviene **nel fixture**, non in un'asserzione: la transazione
aborta e il file intero risulta rosso (`Bad plan. You planned N tests but ran 0`).

Esempi confermati: `test-commesse-core-functions-v1`, `test-vw-contatore-merce-v1`,
`test-vw-resi-da-accreditare-contatore-v1`, `test-fn-list-ddt-da-pushare-contatore-v1`,
`test-attivita-guardrail-commessa-v1`, `test-vw-dash-backlog-resi-v1`.

## 2. La causa — e perché il guard ha ragione

Il 2026-07-18 è entrato il **guard sorgente polimorfa**
(`script.trgfn_guard_sorgente_polimorfa*`), che verifica che
`sorgente_uid` sia coerente col `key_selector` dichiarato dalla sorgente in
`config.sorgenti`:

| sorgente | `key_selector` | forma attesa di `sorgente_uid` |
| --- | --- | --- |
| `PREVENTIVO`, `OFFERTA_COMMERCIALE` | `uid` | UUID |
| `COMMESSA`, `ORDINE_VENDITA`, `DDT_VENDITA`, `FATTURA`, `RESO_VENDITA`, `ATTIVITA`, `ATTIVITA_CONSUMI`, `CONTRATTO` | `id` | `id::text` |

I fixture rotti costruiscono `sorgente_uid` con **stringhe inventate** del tipo
`'SRC-CM-1bc19e109627'`, `'SRC-ACC-5bd27aa21082'`, `'SRC-LS-f60634625c28'`:
comode quando nessuno controllava, illegali da quando il guard esiste.

**Il guard non è il problema, è la cura**: la chiave polimorfa id-vs-uid è
portante nel modello ([[reference_sorgente_polimorfa_key_selector]]) e prima del
guard era possibile agganciare una riga a una sorgente inesistente. I test
scritti *prima* usavano una libertà che non doveva esistere.

Quindi: **niente da correggere nel prodotto. Va aggiornata la suite.**

## 3. Cosa serve fare

### 3.1 Censimento (primo passo, mezz'ora)

La stima «~60» è di seconda mano e va sostituita con un numero verificato. Su un
campione di 22 file di `db/pgtap/vendite/` ne sono risultati 2 — il rapporto
suggerisce che il totale reale su tutta `db/pgtap/` potrebbe essere **inferiore**
a 60. Comando:

```bash
for f in db/pgtap/*/*.sql; do
  if timeout 60 scripts/testpgtap.sh "$f" 2>&1 | grep -q key_selector; then echo "$f"; fi
done | tee /tmp/pgtap_sorgente_polimorfa.txt
wc -l /tmp/pgtap_sorgente_polimorfa.txt
```

Senza questo elenco non si può stimare il lavoro né dichiararlo finito.

### 3.2 Correzione per file

Per ogni fixture: sostituire la stringa inventata con la **chiave nativa** della
sorgente usata.

- `key_selector = 'id'` → `sorgente_uid = <id_reale>::text` dell'entità
  effettivamente creata dal fixture;
- `key_selector = 'uid'` → l'`uid` reale dell'entità.

⚠️ **Non aggirare il guard** con `SET myapp.bypass_*` o disattivando il trigger:
si perderebbe la copertura proprio sull'invariante che il guard protegge. Il
punto della bonifica è che i fixture diventino **realistici**, non che il
controllo taccia.

### 3.3 Ordine consigliato

Prima i file che coprono aree attive (contatore merce, coda accrediti, dashboard
resi): sono quelli che si ri-eseguono più spesso come non-regressione, quindi
danno il beneficio maggiore. Il resto a seguire.

## 4. Perché conviene farlo, anche se non è urgente

Nessun rischio di prodotto, ma un **costo ricorrente e insidioso**:

1. **Rumore su ogni slice.** Chi esegue una batteria di regressione vede rossi
   che non c'entrano, e ogni volta deve ri-verificare a mano che siano
   preesistenti. È accaduto tre volte in tre giorni.
2. **Rischio di mascheramento — il punto vero.** Un file rosso *nel fixture* non
   esegue **nessuna** asserzione: la copertura di quel file è **zero**, non
   «parziale». Se una modifica futura rompesse davvero qualcosa lì, il test
   sarebbe già rosso e nessuno se ne accorgerebbe. Il debito non è cosmetico:
   sono aree scoperte che *sembrano* coperte.
3. **Abitudine al rosso.** Una suite con 60 rossi noti insegna a ignorare il
   rosso, che è esattamente ciò che i test dovrebbero impedire.

## 5. Fuori perimetro

- Non si tocca il guard né `config.sorgenti`.
- Non si introduce alcun bypass permanente per i test.
- Non è questa la sede per i pgTAP rossi con **altre** cause (es. i fixture che
  non passavano `tipo_doc_fiscale_id` prima del guard `tipo_doc_emittibile`, già
  sanati nelle slice del 2026-07-24, o eventuali altri): il censimento §3.1
  filtra per `key_selector`, e chi trova altro lo annota a parte.

## 6. Riferimenti

- Guard: `script.trgfn_guard_sorgente_polimorfa`, `_tipizzata`, `_testuale`
- Convenzione della chiave: [[reference_sorgente_polimorfa_key_selector]] ·
  `docs/it/dbzero/config/manual/sorgenti.md` §Convenzione chiave sorgente
- Slice che hanno incontrato il problema:
  [brief-db-guard-uscita-commessa-e-capabilities.md](brief-db-guard-uscita-commessa-e-capabilities.md),
  [brief-db-chiusura-riconsegna-reso-definitivo.md](brief-db-chiusura-riconsegna-reso-definitivo.md) §9
- Esempio di fixture corretto (usa la chiave nativa `commessa_id::text` per la
  sorgente `COMMESSA`): `db/pgtap/vendite/test-porta-oneri-giro-completo-v1.sql`
