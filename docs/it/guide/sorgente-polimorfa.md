# Sorgente polimorfa — da quale documento nasce una riga

> **Ultimo aggiornamento**: 8 novembre 2026
>
> **Destinatari**: sviluppatori database e backend, analisti funzionali
>
> **Vedi anche** — schemi DB:
>
> * [config.sorgenti](/dbzero/config/tabelle/sorgenti) — il catalogo dei tipi di documento: tabella, chiave, righe e dettaglio di ognuno
> * [script.vw_stato_sorgente](/dbzero/script/views/vw_stato_sorgente) — lo stato del documento di provenienza, in un vocabolario comune
> * [dbops.vw_sorgenti_orfane](/dbzero/dbops/views/vw_sorgenti_orfane) — le provenienze il cui documento non c'è più; **deve restare vuota**
>
> **Vedi anche** — funzioni e trigger DB:
>
> * [script.fn_sorgente_chiave](/dbzero/script/funzioni/fn_sorgente_chiave) — il BB che scrive: da tipo e chiave, la coppia di colonne giusta
> * [script.trgfn_guard_sorgente](/dbzero/script/funzioni/trgfn_guard_sorgente) — il guard unico: forma, esistenza, riga del documento
> * [script.fn_sorgente_documento](/dbzero/script/funzioni/fn_sorgente_documento) — il BB che risolve: id, uid e numero del documento
> * [script.trgfn_sorgente_in_uscita](/dbzero/script/funzioni/trgfn_sorgente_in_uscita) — che cosa succede ai figli quando si cancella l'origine
> * [script.fn_get_sorgente_emittente_sr_id](/dbzero/script/funzioni/fn_get_sorgente_emittente_sr_id) — chi emette il documento di provenienza
>
> **Vedi anche** — guide correlate:
>
> * [Presidi e registri del debito](/guide/presidi-e-registri-del-debito) — dove è iscritto il presidio degli orfani

---

## 1. Il problema che risolve

Molte righe del sistema **nascono da un documento**: la riga d'ordine nasce dalla riga di
un preventivo, la bolla da un ordine, la riga di commessa da un contratto o da un consumo,
il collegamento di una pratica da un preventivo, la stampa da una fattura. Il documento
d'origine può essere di **tipo diverso** e vivere in **tabelle diverse**: una colonna
dedicata per ogni tipo (una per il preventivo, una per l'ordine, una per la bolla…) non
si potrebbe gestire.

La soluzione è una **provenienza universale**: si scrive *che tipo di documento è* e *quale
documento è*, e un catalogo centrale sa dove trovarlo. Le stesse colonne, con lo stesso
significato, su tutte le tabelle.

## 2. Il modello: tipo, documento, riga

Una tabella che dice «nasce da» porta queste colonne, e solo queste:

| Colonna | Che cosa dice |
| --- | --- |
| `sorgente_tipo_id` | il **tipo** del documento, un codice di [`config.sorgenti`](/dbzero/config/tabelle/sorgenti) |
| `sorgente_id` *oppure* `sorgente_uid` | **quale** documento: una sola delle due, quella della chiave del tipo (§3) |
| `sorgente_riga` | la **riga** di quel documento; vuota se la provenienza è il documento intero |
| `sorgente_dettaglio` | il **dettaglio** di quella riga (il prelievo di una bolla, il rientro di un reso), dove serve |

Le regole che tengono insieme il modello:

* **La chiave è sempre quella del documento**, mai quella della riga: `sorgente_id` /
  `sorgente_uid` dicono il documento, `sorgente_riga` dice la riga. Una tabella non mette
  la riga al posto del documento.
* **Una sola forma per tutte le tabelle.** Un `CHECK` per tabella (`chk_<tabella>_sorgente_forma`)
  dice che o le colonne sono tutte vuote (la riga non nasce da nessun documento), o c'è il
  tipo con **una** chiave.
* **I livelli li dichiara il catalogo.** Per ogni tipo `config.sorgenti` dice la tabella del
  documento, quella delle righe e quella del dettaglio, ognuna con la colonna che la lega al
  livello sopra. Se un tipo non ha righe (una mail, un consumo) la riga resta vuota per forza.
* **Unicità solo dove il dominio ha una regola.** Non esiste un vincolo generico «una riga per
  sorgente»: dove il dominio ne ha uno (un'offerta genera al più un ordine vivo, un documento
  sta in una sola commessa aperta), la regola è scritta lì, sulla chiave giusta: un indice
  unico, o la porta che scrive il legame quando la regola guarda anche lo stato.

## 3. La chiave del documento: `id` o `uid`

<a id="la-chiave-del-documento"></a>

Ogni tipo dichiara in `config.sorgenti.key_selector` con quale chiave lo si riconosce:

* **`uid`** — `PREVENTIVO`, `OFFERTA_COMMERCIALE`: la chiave sta in `sorgente_uid`;
* **`id`** — tutti gli altri: la chiave sta in `sorgente_id`.

⛔ **La chiave non si unifica.** Portare tutti i tipi su `id`, o tutti su `uid`, è un'idea
già tornata più volte, e la risposta è no: non si propone, né come raccomandazione né come
opzione. Le due colonne tipizzate rendono la scelta innocua per chi scrive e per chi legge
(nessuno deve sapere quale chiave usa un tipo: lo sanno i BB, §4), mentre cambiarla vorrebbe
dire convertire ogni provenienza salvata. E le chiavi di `config.tipi_entita.key_selector`
rispondono a un'altra domanda (con che chiave si **apre** un documento a video): non è una
divergenza da sanare.

Unificare il **nome del tipo** di documento (un codice solo, quello di `config.sorgenti`) è
un'altra cosa, e si fa.

## 4. I pezzi: chi fa che cosa

Nessuno scrive o legge la provenienza a mano: ogni domanda ha **un** pezzo che risponde.

| Domanda | Chi risponde |
| --- | --- |
| **che cosa scrivo?** (ho un tipo e una chiave qualsiasi, id o uid) | [`script.fn_sorgente_chiave`](/dbzero/script/funzioni/fn_sorgente_chiave) — restituisce la coppia `sorgente_id` / `sorgente_uid` da scrivere, traducendo la chiave dell'altra specie |
| **è giusta?** (al momento di scrivere) | [`script.trgfn_guard_sorgente`](/dbzero/script/funzioni/trgfn_guard_sorgente) — il guard unico, montato su ogni tabella che dice «nasce da» |
| **che documento è?** (id, uid, numero) | [`script.fn_sorgente_documento`](/dbzero/script/funzioni/fn_sorgente_documento) — una riga sempre, mai un errore: una provenienza che non si risolve fa sparire l'azione, non rompe la lista |
| **in che stato è?** | [`script.vw_stato_sorgente`](/dbzero/script/views/vw_stato_sorgente) — lo stato nel vocabolario comune |
| **chi lo emette?** | [`script.fn_get_sorgente_emittente_sr_id`](/dbzero/script/funzioni/fn_get_sorgente_emittente_sr_id) |
| **si può cancellare l'origine?** | [`script.trgfn_sorgente_in_uscita`](/dbzero/script/funzioni/trgfn_sorgente_in_uscita) — il lato «in uscita», la FK che il legame non ha |
| **è rimasto qualcosa di orfano?** | [`dbops.vw_sorgenti_orfane`](/dbzero/dbops/views/vw_sorgenti_orfane) — il presidio, a tre livelli |

### Il guard unico

Il guard controlla, prima la forma e poi l'esistenza: il tipo esiste ed è attivo; c'è una
sola chiave, quella del tipo; il documento esiste ed è visibile a chi scrive; la riga è di
quel documento e il dettaglio di quella riga, nelle tabelle che il catalogo dichiara. Ogni
tabella lo monta con due argomenti:

* il **livello minimo** che la sua provenienza deve raggiungere (`DOCUMENTO`, `RIGA`,
  `DETTAGLIO`): il registro di magazzino, per esempio, vuole sempre il dettaglio di una bolla;
* che cosa succede quando l'origine si cancella (`BLOCCA` o `CANCELLA`), come un `ON DELETE`.

### Il lato «in uscita»

Il guard chiude la porta in ingresso; quando poi qualcuno **cancella** il documento d'origine,
o una sua riga, interviene il lato «in uscita». È montato su ogni tabella che il catalogo
dichiara come documento, righe o dettaglio di un tipo, e guarda le righe che ne dichiarano la
provenienza:

* se un figlio ha dichiarato `BLOCCA`, la cancellazione si ferma (`E_SORG_ORIGINE_REFERENZIATA`,
  col numero dei figli nella frase);
* se ha dichiarato `CANCELLA`, i figli se ne vanno con l'origine.

Prima conta i figli che bloccano, poi cancella: se uno blocca, non si cancella niente. Come una
FK, vede anche i figli che la RLS nasconde a chi cancella. Il montaggio **deriva dal catalogo**:
un tipo nuovo in `config.sorgenti` riceve il suo lato «in uscita» alla migrazione successiva,
senza un changeSet suo.

⚠️ Il lato «in uscita» non decide **se** un documento si può cancellare: quello lo dice la regola
della tabella padre (per le testate di vendita, «si cancella solo la bozza vuota»). Il lato «in
uscita» parla dopo, sui figli.

## 5. Le chiavi in testo: dove esistono, e chi le legge

Le tabelle scrivono la chiave nelle colonne tipizzate. Esistono però chiavi che sono **testo
per costruzione**: i nodi della lineage, la chiave di un gruppo fatturabile (che contiene l'uid
del documento), la chiave che il backend passa ai verbi del push. Quelle si leggono con
[`script.fn_sorgente_documento_da_chiave`](/dbzero/script/funzioni/fn_sorgente_documento_da_chiave),
che riconosce la forma **canonica** (`id::text` o `uuid::text`, con
[`fn_sorgente_chiave_id`](/dbzero/script/funzioni/fn_sorgente_chiave_id) e
[`fn_sorgente_chiave_uuid`](/dbzero/script/funzioni/fn_sorgente_chiave_uuid)) e poi risolve come
il BB che risolve. Una chiave non canonica (zeri davanti, spazi, maiuscole) non si risolve.

## 6. Chi resta fuori, e perché

Il presidio di struttura (un pgTAP in CI) fa rossa ogni tabella che ha `sorgente_id` o
`sorgente_uid` e non monta il guard unico. Fuori dal guard ci sono solo casi **dichiarati**,
ognuno col suo motivo scritto nel perimetro del presidio:

* **`pratiche.reconcile_errori`** — è un log scritto dentro un `EXCEPTION`: un guard d'esistenza
  lo farebbe tacere, e un log rimanda per costruzione anche a documenti che non ci sono più;
* **`vendite.fatture_stampa_coda`** — la sua chiave è una FK vera verso la fattura: esistenza e
  cancellazione le tiene la FK;
* **le tabelle degli acquisti** (`acquisti.ordini`, `ordini_righe`, `ddt`, `ddt_righe`) — non
  sono ancora sul modello: le porta il cantiere degli acquisti, e fino ad allora sono l'unico
  elenco del presidio di struttura.

Non usano queste colonne, per scelta:

* **l'import da un sistema esterno**: avrà una tabella di collegamento propria (canale, tipo di
  record, id esterno in testo), perché un id esterno non è un documento del catalogo;
* **le attività fatturabili**: puntano alla riga di commessa con una FK vera
  (`commessa_attivita_id`), e la provenienza è quella della riga di commessa.

## 7. Aggiungere una tabella che «nasce da»

1. le colonne del §2, nullable, con il `CHECK` di forma;
2. il verbo che scrive la riga ottiene la coppia di colonne da `script.fn_sorgente_chiave`, e non
   la compone da sé;
3. il guard unico montato con il livello minimo e l'azione in cancellazione;
4. l'unicità solo se il dominio ha una regola, sulla chiave giusta;
5. il lato «in uscita» sul documento d'origine non si scrive: lo monta la convergenza dal
   catalogo.

Il presidio di struttura in CI fa rossa la tabella a cui manca il guard.

## 8. Per chi costruisce grafi tra documenti (lineage, legami, proiezione)

<a id="grafi-tra-documenti"></a>

L'identità di un nodo è **tipo + chiave del documento**, come la scrive il modello. Il documento
si risolve con il BB che risolve, non con un join scritto a mano verso la tabella: è lui che sa
quale chiave usa il tipo e dove sta il numero. I resolver di stato da riusare sono
[`script.vw_stato_sorgente`](/dbzero/script/views/vw_stato_sorgente) e le viste
`vendite.vw_stato_sorgente_*` che la compongono.

---

## Area tecnica — esempi

**Scrivere una provenienza** — la coppia di colonne la dà il BB che scrive, qualunque chiave abbia
in mano il chiamante (qui l'uid di un ordine, tipo a chiave `id`: esce in `sorgente_id`):

```sql
SELECT k.sorgente_id, k.sorgente_uid
  FROM script.fn_sorgente_chiave(
         (SELECT id FROM config.sorgenti WHERE codice_interno = 'ORDINE_VENDITA'),
         '01a06ce4-35a6-721a-9cd8-9da48bf77626') k;
```

**Quali tabelle montano il guard unico** — con il livello minimo e l'azione in cancellazione:

```sql
SELECT tabella, livello_minimo, azione_cancellazione, argomenti_validi
  FROM script.fn_sorgente_guard_montaggi()
 ORDER BY 1;
```

**Il catalogo dei tipi** — la chiave, le righe e il dettaglio di ognuno:

```sql
SELECT codice_interno, key_selector, target_table, righe_table, dettaglio_table
  FROM config.sorgenti
 WHERE attivo
 ORDER BY codice_interno;
```

**Le provenienze rimaste orfane** — deve restare vuota:

```sql
SELECT * FROM dbops.vw_sorgenti_orfane;
```

---
{% include-markdown "signature-core.md" %}
