## 📘 Documentazione Concettuale – Tabella `config.aspetti_beni`

> 👀 **Vedi anche**
>
Approfondimento tabelle:
> • [vendite.ddt](/dbzero/vendite/tabelle/ddt)
> • [config.causali_trasporto](/dbzero/config/tabelle/causali_trasporto)

---
### 🎯 Scopo Principale

(rev 2026-08-21)

Vocabolario dell'**aspetto esteriore dei beni** — bancali, colli, cartoni, fusti, pacchi,
pallet, bobine, rotoli. È il campo che il documento di trasporto deve riportare per descrivere
come la merce si presenta a chi la riceve.

Referenziato da `vendite.ddt.aspetto_bene_id`.

Non è una classificazione merceologica: lo stesso articolo può viaggiare in cartoni una volta
e su pallet un'altra. L'aspetto appartiene alla **spedizione**, non al prodotto — ed è per
questo che sta sul DDT e non sull'articolo.

---

### Vocabolario operativo, e popolato

Misurato il 2026-08-21: **10 righe**. È uno dei pochi vocabolari `config` del gruppo
logistico effettivamente in uso, a differenza di `ambiti` e `tipi_ubicazione`, che
appartengono al magazzino non ancora sviluppato.

---

### Le colonne

`codice` e `descrizione` (`NOT NULL`), `attivo` per la disponibilità, `meta` JSONB per gli
attributi che non meritano una colonna, più l'audit standard.

⚠️ La disattivazione qui è `attivo`, non `obsoleto_dal`. È una differenza rispetto ai cataloghi
più recenti del progetto (`classi_errore`, `codici_errore`), dove si è scelto `obsoleto_dal`
proprio perché `attivo = false` **rompe le istanze già referenziate**: un DDT storico che
puntasse a un aspetto disattivato resterebbe legato a una riga che l'applicazione considera
non selezionabile.

Sul DDT il problema è attenuato — l'aspetto è un dato di stampa, non un vincolo — ma vale la
pena saperlo prima di disattivare una voce usata in passato.

---

{% include-markdown "signature-core.md" %}
