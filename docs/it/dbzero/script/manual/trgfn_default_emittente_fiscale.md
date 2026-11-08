## Documentazione Concettuale – Trigger Function `script.trgfn_default_emittente_fiscale`

> **Ultimo aggiornamento**: 8 novembre 2026
>
> **Vedi anche**
>
**Tabelle su cui è montata (undici, dal 2026-09-15):**
>
[vendite.ordini](/dbzero/vendite/tabelle/ordini) · [vendite.preventivi](/dbzero/vendite/tabelle/preventivi) · [vendite.contratti](/dbzero/vendite/tabelle/contratti) · [vendite.ddt](/dbzero/vendite/tabelle/ddt) · [vendite.offerte_commerciali](/dbzero/vendite/tabelle/offerte_commerciali)
> [magazzino.magazzini](/dbzero/magazzino/tabelle/magazzini) · [magazzino.assets](/dbzero/magazzino/tabelle/assets)
> [pratiche.pratiche](/dbzero/pratiche/tabelle/pratiche) · [documenti.template_documenti](/dbzero/documenti/tabelle/template_documenti) · [documenti.template_asset](/dbzero/documenti/tabelle/template_asset) · [anagrafiche.soggetti_titoli_iva](/dbzero/anagrafiche/tabelle/soggetti_titoli_iva)
>
**Funzioni correlate:**
>
[script.fn_resolve_emittente_for_user](/dbzero/script/funzioni/fn_resolve_emittente_for_user) — chi risponde «l'emittente di lavoro di questo operatore»
> [script.trgfn_guard_emittente_scope](/dbzero/script/funzioni/trgfn_guard_emittente_scope) — il guard che scatta **dopo**: il default riempie, lo scope giudica
> [vendite.trgfn_commesse_default_emittente](/dbzero/vendite/funzioni/trgfn_commesse_default_emittente) — la sola «default emittente» rimasta per dominio: deriva dal billing account, non dalla sessione, e non è una copia

---
### 🎯 Scopo Principale

> Brief: `brief-db-emittente-di-default-un-bb-solo` (decisione di Tid, 2026-09-15).
> ChangeSet `20260915-36` (la funzione), `-37 … -40` (le quattro copie di vendite
> ritirate), `-42 … -46` (i sette montaggi nuovi).

**Una regola sola, scritta una volta**: *se la riga non dice l'emittente
fiscale, è quello di chi la scrive; se non c'è nessuno da cui dedurlo, la riga
non entra.* Fino al 2026-09-15 la stessa regola era scritta **quattro volte** in
`vendite` (`trgfn_ordini/preventivi/contratti/ddt_default_emittente`: tre copie
esatte e una variante) e **mancava** su altre sette tabelle ancorate su
`emittente_fiscale_id NOT NULL` — fra cui `magazzino.magazzini`, dove un
INSERT dal pannello di amministrazione senza emittente moriva con `23502`.

Il trigger è `BEFORE INSERT, FOR EACH ROW`. Legge la **colonna fissa
`emittente_fiscale_id`** (è il nome su cui poggia il perimetro RLS —
`dbops.vw_rls_perimetro_scoperto`, famiglia `fn_scope_ef_whitelist_*` — e
tutte le tabelle montate la chiamano così) e:

1. **valore esplicito** → non si tocca mai: una scelta dichiarata non si
   sovrascrive;
2. **`SALTA_CON_SORGENTE`** e riga con `sorgente_tipo_id` e una chiave del
   documento d'origine (`sorgente_id` o `sorgente_uid`) → non si tocca: l'emittente è quello del documento padre e lo mette il
   `normalize` a valle (vedi «La regola della sorgente»);
3. **GUC `app.current_user_id` vuota** → nessuno da cui dedurre:
   `LASCIA_NULL` esce, `SOLLEVA` alza `E_EMITTENTE_NON_RISOLTO`;
4. **`fn_resolve_emittente_for_user` risponde NULL** (admin globale senza
   assegnazione, in modalità «tutti gli emittenti») → idem;
5. altrimenti `NEW.emittente_fiscale_id := ` l'emittente di lavoro (l'attivo
   di sessione `app.current_emittente_id` se in scope, altrimenti quello
   assegnato in `config.user_emittenti_fiscali`).

---

### Parametri trigger (TG_ARGV)

| Indice | Valore | Descrizione |
| ------ | ------ | ----------- |
| `TG_ARGV[0]` | `'SOLLEVA'` \| `'LASCIA_NULL'` | **Obbligatorio.** Che cosa fare quando dalla sessione non si ricava niente: sollevare `E_EMITTENTE_NON_RISOLTO`, oppure lasciare NULL e far decidere chi viene dopo (un `normalize`, o il `NOT NULL`). |
| `TG_ARGV[1]` | `'SALTA_CON_SORGENTE'` | Facoltativo. Se la riga porta `sorgente_tipo_id` **e** una chiave del documento d'origine (`sorgente_id` o `sorgente_uid`, quella del tipo), il default non scatta. Le colonne si leggono da `to_jsonb(NEW)` in sola lettura: possono non esistere sulla tabella, e una colonna che manca vale vuota. |

Un argomento non ammesso (modo sconosciuto, terzo argomento, `TG_OP` diverso
da `INSERT`) solleva **`E_TRIGGER_ARGOMENTI_INVALIDI`** (`TECNICO`) **al primo
INSERT**: è un difetto di chi installa, e deve morire subito, non tacere.

---

### Dove è montata, e con che argomenti

| Tabella | Argomenti | Note |
| --- | --- | --- |
| `vendite.ordini`, `preventivi`, `contratti` | `('SOLLEVA')` | al posto delle tre copie esatte; comportamento identico, codice unico |
| `vendite.ddt` | `('LASCIA_NULL', 'SALTA_CON_SORGENTE')` | al posto della variante: identica (vedi sotto) |
| `vendite.offerte_commerciali` | `('SOLLEVA')` | era la sorella senza default; il BE lo passa già, il trigger chiude la porta del `23502` |
| `magazzino.magazzini`, `magazzino.assets` | `('SOLLEVA')` | le ancore del perimetro di magazzino (Lotto 1); prerequisito del Lotto 2 |
| `pratiche.pratiche`, `documenti.template_documenti`, `documenti.template_asset`, `anagrafiche.soggetti_titoli_iva` | `('SOLLEVA')` | il BE passa già l'emittente nel payload: nessun comportamento in essere cambia |

**Non** è montata, per decisione, su: `vendite.resi` (eredita dal DDT sorgente
o dal BA nel `normalize`), `documenti.documenti_generati` (il BE lo deriva dal
documento sorgente), `vendite.commesse` (altra colonna, dal BA),
`config.user_emittente_attivo` / `user_emittenti_fiscali` (sono la mappa
stessa). Il pgTAP asserisce **l'elenco esatto**: una tabella montata in più
«per imitazione» fa rosso.

Il nome del trigger è sempre **`trg_<tabella>_a10_default_emittente_ins`** —
sulle quattro di vendite è lo stesso di prima.

---

### L'ordine è il nome

I `BEFORE ROW` scattano in **ordine alfabetico**, e `default_` viene prima di
`guard_` e di `normalize`: il default riempie, poi `trgfn_guard_emittente_scope`
giudica se chi scrive ha quell'emittente nel perimetro, poi il guard BA
verifica la coerenza col cliente. Se un giorno un trigger venisse rinominato
l'ordine cambierebbe in silenzio: il test 8 di
`db/pgtap/script/test-trgfn-default-emittente-fiscale-v1.sql` lo asserisce per
**ogni** tabella montata.

---

### La regola della sorgente (`SALTA_CON_SORGENTE`)

`vendite.trgfn_ddt_normalize` eredita l'emittente dall'ordine sorgente con
`COALESCE(NEW.emittente_fiscale_id, o.emittente_fiscale_id)`: **vince ciò che è
già in `NEW`**. Se il default di sessione riempisse la colonna prima, un super
admin con emittente attivo B che evade un ordine di A produrrebbe un DDT di B, e
`script.trgfn_doc_guard_emittente_ba` lo rifiuterebbe. L'argomento dice: *un documento
che nasce da un altro documento eredita l'emittente di quello, non della
sessione.* Non era un dettaglio d'implementazione della vecchia
`trgfn_ddt_default_emittente`: era una regola, e il building block la conserva.

⚠️ Il `normalize` della bolla eredita dall'**ordine**. Una bolla che nasce da
un'altra provenienza (la bolla di riconsegna, che nasce dal reso) non trova lì
il suo emittente: lo porta già chi la scrive (il verbo della riconsegna lo copia
dalla bolla d'origine), e altrimenti lo prende dal billing account, nel ripiego
del `normalize`.

---

### Il codice: `E_EMITTENTE_NON_RISOLTO`

Classe **`DATO_ERRATO`** (400), `campo = emittente_fiscale_id`: chi può
rimediare è una **persona** — scegliere l'emittente in alto, o dichiararlo nella
riga. Il messaggio **non ha segnaposto**: *«Nessun emittente fiscale attivo:
seleziona l'emittente in alto, oppure indicalo esplicitamente nella
richiesta.»* — la diagnostica (GUC vuota / operatore senza assegnazione) sta
nel `context` di `dbops.error_log`, non a video. Le tre copie incollavano
`«GUC vuota, numero=…»` al `%s` della frase per l'operatore.

È **un codice per undici tabelle**, come `E_SCOPE_EMITTENTE`: la condizione è
una, non un accumulo. I tre codici di dominio
`E_ORDINE_/E_PREV_/E_CONTRATTO_EMITTENTE_NON_RISOLTO` sono **ritirati con
`obsoleto_dal = 2026-09-15`** (mai un `DELETE`: il diario deve restare
leggibile); avevano tre nomi e **due `ui_action`** (solo `E_PREV_…` aveva
l'override `highlight_form_fields`). ⚠️ Da non confondere con
`E_FATTURA_EMITTENTE_NON_RISOLTO` e `E_SORG_EMITTENTE_NON_RISOLTO` (`TECNICO`):
là è un documento **già esistente** a non avere l'emittente.

---

### Il ritiro delle copie (2026-09-15)

| Funzione ritirata | Che cos'era | ChangeSet |
| --- | --- | --- |
| `vendite.trgfn_ordini_default_emittente` | copia esatta | `20260915-37` |
| `vendite.trgfn_preventivi_default_emittente` | copia esatta | `20260915-38` |
| `vendite.trgfn_contratti_default_emittente` | copia esatta | `20260915-39` |
| `vendite.trgfn_ddt_default_emittente` | la variante (non solleva, salta con sorgente) | `20260915-40` |

Le loro pagine `manual/` sono cancellate (regola: l'indice è generato, un
moncone resterebbe in elenco). ⭐ Censendo chi si appoggiava al default senza
dirlo è uscito che `vendite.fn_crea_revisione_preventivo` **non copiava**
`emittente_fiscale_id` sulla rev N+1: corretto in `20260915-41` (D3).

---

### Presidio

`db/pgtap/script/test-trgfn-default-emittente-fiscale-v1.sql` (18): la forma
(funzione, copie assenti, catalogo, l'elenco esatto delle montate e delle
escluse, l'ordine alfabetico, i due argomenti di ddt) e il comportamento con
una fixture **costruita** — tre aziende, un super admin, un BA — per i sei
casi: default dall'operatore, esplicito non sovrascritto, attivo di sessione,
sorgente che vince sulla sessione, admin globale senza emittente, GUC vuota,
`LASCIA_NULL`, argomento sbagliato, e la revisione del preventivo (D3).

---

### Note di migrazione

* 2026-11-06 — `SALTA_CON_SORGENTE` riconosce la provenienza da tipo e una
  delle due chiavi del modello (`sorgente_id` o `sorgente_uid`), non più dal
  solo `sorgente_uid` (`brief-db-sorgente-documento-e-riga`).

---
{% include-markdown "signature-core.md" %}
