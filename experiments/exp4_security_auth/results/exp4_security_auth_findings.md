# Experiment 4: Security & Auth — Findings

- **Auth success %:** Valid owner and inquiry tokens achieved 100.0% success; expired and malformed tokens correctly rejected (0% success).

- **Mean auth latency:** Valid requests averaged 4.71 ms (gateway + DB simulation); failure paths show similar latency (gateway validates then rejects).

- **Error handling:** Expired tokens produced 50 rejections; malformed tokens produced 50 rejections; behavior is consistent and measurable.

- **Local JWT gateway simulation** confirms that success rate, latency, and failure-mode counts are reproducible and suitable for security metrics in a local, no-cloud setup.

