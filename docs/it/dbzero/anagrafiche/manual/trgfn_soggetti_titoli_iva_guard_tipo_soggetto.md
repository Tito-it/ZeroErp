## 📘 Documentazione Concettuale – Trigger function `anagrafiche.trgfn_soggetti_titoli_iva_guard_tipo_soggetto`

> **Ultimo aggiornamento**: 22 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [anagrafiche.soggetti_titoli_iva](/dbzero/anagrafiche/tabelle/soggetti_titoli_iva) — i titoli su cui è montata
> * [config.tipi_titolo_iva_tipi_soggetto_dettaglio](/dbzero/config/tabelle/tipi_titolo_iva_tipi_soggetto_dettaglio) — quali tipi ammette ogni natura
> * [anagrafiche.soggetti](/dbzero/anagrafiche/tabelle/soggetti) — da cui legge la natura del titolare
>
> Approfondimento funzioni:
>
> * [anagrafiche.fn_titolo_iva_vigente](/dbzero/anagrafiche/funzioni/fn_titolo_iva_vigente) — quando un titolo si giudica
> * [anagrafiche.fn_titolo_iva_ammesso](/dbzero/anagrafiche/funzioni/fn_titolo_iva_ammesso) — la domanda che fa
> * [anagrafiche.fn_check_cambio_natura_soggetto](/dbzero/anagrafiche/funzioni/fn_check_cambio_natura_soggetto) — l'altro verso: la natura che cambia sotto un titolo

---

### 🎯 Scopo Principale

`anagrafiche.trgfn_soggetti_titoli_iva_guard_tipo_soggetto` rifiuta un titolo IVA in vigore di un tipo che la
natura del suo titolare non ammette. È il controllo della regola dalla parte del titolo: quando lo si scrive.

---

### Quando giudica

Scatta prima della scrittura del titolo, alla nascita e quando cambiano il tipo, il titolare, `attivo` o
`valido_al`: le colonne che possono rendere in vigore un titolo non ammesso. Riattivare un titolo spento o
prorogarne la data di fine sono scritture che il guard giudica come una nascita.

Le altre colonne non lo svegliano. In particolare `imponibile_utilizzato`, che l'accumulatore riscrive a ogni
movimento di plafond: un consumo in fattura non deve inciampare in una regola di anagrafica.

Un titolo che non è in vigore (spento, o con la data di fine passata) passa senza domande.

---

### Che cosa controlla

* **Il titolare non ha natura**: rifiuto con `E_DATO_FISCALE_SENZA_TIPO_SOGGETTO`. Senza natura non c'è nessun
  tipo ammesso, e il rifiuto dice la causa vera invece di «tipo non ammesso».
* **La natura non ammette il tipo**: rifiuto con `E_TITOLO_IVA_NON_AMMESSO_PER_TIPO_SOGGETTO`, sul campo
  `tipo_titolo_iva_id`, col nome del tipo e della natura.

Se il titolare non esiste il guard tace: lo dice la chiave esterna verso `anagrafiche.soggetti`.

---

### Codici errore

* `E_DATO_FISCALE_SENZA_TIPO_SOGGETTO` — il titolare non ha natura.
* `E_TITOLO_IVA_NON_AMMESSO_PER_TIPO_SOGGETTO` — la natura non ammette il tipo del titolo.

---

### Note di migrazione

* 2026-10-10 — nasce con la matrice delle ammissioni e i suoi predicati.
* 2026-11-14 — il verso opposto, la natura che cambia sotto un titolo, passa da un guard proprio su
  `anagrafiche.soggetti` (`trgfn_soggetti_guard_titoli_iva_ammessi`, ritirato) ai motivi di
  `anagrafiche.fn_check_cambio_natura_soggetto`. Il COMMENT della funzione nomina ancora il guard ritirato.

---

{% include-markdown "it/dbzero/anagrafiche/_titolo-iva-per-natura.md" %}

---

{% include-markdown "signature-core.md" %}
