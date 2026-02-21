# Experiment 3: Security relevance

With Data Facts (checksum), integrity violations are caught deterministically: every checksum mismatch flags tampering.

Without Data Facts, the same corrupt payloads sail through silently; detection depends on luck or downstream failures.

For regulated domains like finance (market data feeds) and healthcare (EHR lab results), silent corruption can trigger bad trades or clinical decisions.

Checksum enforcement via Data Facts converts silent integrity risk into observable, actionable failures.

