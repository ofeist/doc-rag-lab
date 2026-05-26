# Shared Corpus Answer Quality - Manual Grading (gpt-5.4-nano)

Corpus: `data/chunks_mixed_multi_slice.jsonl` (P3-16 shared mixed corpus).
Model: `gpt-5.4-nano`, `--max-tokens 900`, temperature omitted.
Grader: manual review of each answer against the AURIX TC3xx source pages.

Grading rules:
- PASS: materially correct and grounded in the provided sources.
- PARTIAL: mostly correct but incomplete, vague, or missing an important part.
- FAIL: wrong, unsupported, or abstains despite sufficient context.

## Summary

| slice | PASS | PARTIAL | FAIL |
| --- | ---: | ---: | ---: |
| memory_map | 10 | 0 | 0 |
| boot_bmhd | 9 | 1 | 0 |
| dma_cache | 10 | 0 | 0 |
| interrupt_routing | 10 | 0 | 0 |
| **total** | **39** | **1** | **0** |

PASS rate: 39/40 = 97.5%. Zero hallucinated/unsupported answers.

## memory_map (bm25_table_boost)

| id | grade | reason / notes |
| --- | --- | --- |
| memory-map-001 | PASS | BBBBE/SPBBE/SRIBE/Access bus-error/allowed definitions correct (p90). |
| memory-map-002 | PASS | Segments 1 and 3-7 + cache-disabled access caveats correct (p90). |
| memory-map-003 | PASS | CPU0 DSPR `7000 0000H-7003 BFFFH`, 240 Kbyte; range/size consistent (p93). |
| memory-map-004 | PASS | CPU0 PSPR `7010 0000H-7010 FFFFH`, 64 Kbyte (p94). |
| memory-map-005 | PASS | PF0-PF5 ranges all correct (p94). |
| memory-map-006 | PASS | Boot ROM `8FFF 0000H-8FFF FFFFH`, Read=Access, Write=SRIBE (p94). |
| memory-map-007 | PASS | DF0 EEPROM/UCB/CFS, DF1 EEPROM ranges internally consistent (p96). |
| memory-map-008 | PASS | seg9 vs seg11 DLMU/LMURAM comparison correct (p94/p96). |
| memory-map-009 | PASS | TC39x alt SOTA seg8: 8000=PF2, 8030=PF3, 8060=PF0, 8090=PF1 (verified vs raw p97). |
| memory-map-010 | PASS | TC38x alt SOTA seg10 mapping matches raw p100 exactly. |

## boot_bmhd (hybrid)

| id | grade | reason / notes |
| --- | --- | --- |
| boot-001 | PASS | CPU0 DSPR 8 kByte / PSPR 1 kByte SSW overwrite correct (p115). |
| boot-002 | PASS | BMHD structure, BMI/PINDIS/HWCFG fields correct (Table 45). |
| boot-003 | PASS | PINDIS bit 0 enable/disable + PROCONTP.BML gating correct. |
| boot-004 | PASS | HWCFG 111=Flash, 110=ABM, 100=Generic BSL, 011=ASC BSL. |
| boot-005 | PARTIAL | Correct on original-vs-copy processing (UCB_BMHDx_ORIG/COPY, status bitfields, BMHDID=B359H, CRC) and honestly flags the context boundary, but retrieval missed expected p119/p120 so the answer does not cover selection among multiple valid BMHDs/copies. Answer quality tracks the known weak retrieval for this question. |
| boot-006 | PASS | HWCFG-pins-vs-BMI conditions (PINDIS, BML, STSTAT.HWCFG[3]) correct. |
| boot-007 | PASS | ABMHD location in PFlash + STADABM definition correct. |
| boot-008 | PASS | CRC over CHKSTART..CHKEND vs CRCRANGE/CRCRANGE_N, CRC32 IEEE 802.3. |
| boot-009 | PASS | No-valid-BMHD handling (Generic BSL install / BOOTMODE_CONFIGURED). |
| boot-010 | PASS | SSW main flow after Startup Mode processing correct. |

## dma_cache (hybrid)

| id | grade | reason / notes |
| --- | --- | --- |
| dma-cache-001 | PASS | PMA0 = data access cacheability register, bit-n semantics (p257). |
| dma-cache-002 | PASS | PMA1 = code access cacheability register (p258). |
| dma-cache-003 | PASS | DSYNC before MTCR, ISYNC after, cache invalidation for coherency. |
| dma-cache-004 | PASS | Non-cacheable segment constraints correct. Retrieval pulled off-slice p91/p92, but the answer grounded only in the dma pages (S2=258, S4=257) - no contamination. |
| dma-cache-005 | PASS | PCACHE 2-way set-assoc; invalidate via PCON1.PCINV over 64 cycles. |
| dma-cache-006 | PASS | PMI has no automatic coherency; software-managed (p312). |
| dma-cache-007 | PASS | PCON0.PCBYP bypass = forced miss, refill without cache update. |
| dma-cache-008 | PASS | Software DMA request via CHCSR.SCH=1, TSR.CH, TREL/TCOUNT (p1442). |
| dma-cache-009 | PASS | Source/dest address generation, ADICR, CHDW, SMF/INCS/DMF offsets. |
| dma-cache-010 | PASS | After channel reset: poll TSR.RST=0, no SCH during reset, restart TCS. |

## interrupt_routing (hybrid)

| id | grade | reason / notes |
| --- | --- | --- |
| irq-001 | PASS | IR schedules service requests to CPU/DMA = service providers (p1364). |
| irq-002 | PASS | SRN = SRC register + interface logic to triggers and arbitration buses. |
| irq-003 | PASS | SRPN bits 7:0, 00H lowest / FFH highest (p1367). |
| irq-004 | PASS | TOS 000=CPU0,001=DMA,010=CPU1,011=CPU2,100=CPU3,101=CPU4,110=CPU5 (verified vs raw p1368). Off-slice p105 retrieved but not used. |
| irq-005 | PASS | Change-TOS/SRPN sequence: SRE=0, check, poll LWSRx, change, re-enable. |
| irq-006 | PASS | ACCEN_CONFIG lower half / ACCEN_SRC_TOSx upper half write protection. |
| irq-007 | PASS | SETR/CLRR set/clear SRR; both=1 no change; reads return 0. |
| irq-008 | PASS | ICU arbitration by SRC.SRPN, highest priority wins. |
| irq-009 | PASS | GPSR nodes = software-interrupt SRNs, 8 per group, no HW trigger. |
| irq-010 | PASS | INT space 0xF0037000-F0037FFF, SRC space 0xF0038000-F0039FFF (p1392). Off-slice p98 retrieved but not used. |

## Notes

- No severe hallucinations. Every answer cited sources and matched the source content.
- The only sub-PASS (boot-005) corresponds to the one question whose expected
  pages were not all retrieved; the answer stayed grounded and flagged its own
  context boundary rather than inventing the missing steps.
- For dma-cache-004, irq-004, irq-010 the shared corpus retrieved a few off-slice
  memory_map pages as low-ranked candidates, but the model grounded its answers in
  the correct slice pages. No cross-slice contamination appeared in any answer.
